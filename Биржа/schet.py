# -*- coding: utf-8 -*-
# SCHET_V1
# SCHET_V2
"""
СЧЁТ МЕСТА В GRD — текущий (со сбросом) и общий; история сделок (22.10).

СЛОВО ШЕФА 22.10
    «Нужно сделать баланс … и лот гнать; пусть в приборах у неё появятся
    строчки: баланс, риск, просадка максимальная, лучшие, худшие и т.д.»
    «Условно валюта GRD.»
    «Копится все прогоны; если обнуляется — то сброс до сотни … а общий
    копится как общий.» История — «список всех её закрытых сделок по счёту».

КАК СЧИТАЕТСЯ
    Сделки у города записаны в R. Счёт переводит их в GRD:
      • старт — 100 GRD;
      • риск — 1% от баланса на момент сделки: риск_GRD = баланс × 1%;
      • итог в GRD = риск_GRD × R (куски и ноги — каждая своей записью);
      • лот = риск_GRD / (расстояние до исходного стопа × размер лота); размер
        лота: пары 100 000, золото 100 (условно: 1 GRD = 1 ед. валюты котировки).
    ТЕКУЩИЙ счёт — с последнего сброса (кнопка «⟲ Сброс» в Приборах) по всем
    прогонам подряд. ОБЩИЙ — за всё время, не сбрасывается. Счёт — у места:
    журнал и отчёты сброс не трогает, он только ставит отметку времени.
    Только считает: на торговлю и решения не влияет, жителю не показывается.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

START = 100.0
RISK = 0.01
VAL = "GRD"
NOL = 0.005

_BIRZHA = Path(__file__).resolve().parent
KOREN = _BIRZHA.parent
CEHA = KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха"
ZHURNAL = KOREN / "GRONDHEIM_CITY" / "Биржа" / "данные" / "trading_pnl.jsonl"
_KESH = {"mtime": None, "zap": []}


# ── журнал ───────────────────────────────────────────────────────
def _zhurnal() -> list:
    try:
        mt = ZHURNAL.stat().st_mtime
    except Exception:
        return []
    if _KESH["mtime"] != mt:
        zap = []
        with open(ZHURNAL, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        zap.append(json.loads(ln))
                    except Exception:
                        pass
        _KESH.update(mtime=mt, zap=zap)
    return _KESH["zap"]


def _nomer(ceh, slot):
    for imya in ("mesto_urovnya", "mesto_dzhema"):
        try:
            m = __import__(imya)
            return m.nomer_mesta(slot, ceh)
        except Exception:
            continue
    return None


def _zapisi(ceh, slot, s: str = "", do: str = "9999") -> list:
    magic = _nomer(ceh, slot)
    if magic is None:
        return []
    return sorted((z for z in _zhurnal()
                   if z.get("magic") == magic and s <= str(z.get("ts") or "")[:19] < do),
                  key=lambda z: str(z.get("ts") or ""))


# ── сброс ────────────────────────────────────────────────────────
def _put_sbrosa(ceh, slot) -> Path:
    return CEHA / ceh / "слоты" / slot / "данные" / "счёт.json"


def sbros_kogda(ceh, slot) -> str:
    try:
        return str(json.loads(_put_sbrosa(ceh, slot).read_text(encoding="utf-8")).get("сброс") or "")
    except Exception:
        return ""


def sbros(ceh, slot) -> str:
    """Текущий счёт места — заново со 100 GRD с этого момента."""
    p = _put_sbrosa(ceh, slot)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    seychas = datetime.now().isoformat(timespec="seconds")
    d["сброс"] = seychas
    d["сбросы"] = (d.get("сбросы") or [])[-49:] + [seychas]
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[СЧЁТ] {ceh}/{slot}: текущий счёт сброшен до {START:.0f} {VAL} ({seychas})")
    return seychas


# ── счёт ─────────────────────────────────────────────────────────
def _r(z) -> float:
    try:
        return float(z.get("pnl_r") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _razmer_lota(symbol: str) -> float:
    s = str(symbol or "").upper()
    return 100.0 if s.startswith(("XAU", "GOLD")) else 100000.0


def _storona(z) -> str:
    try:
        e, x, r = float(z.get("entry")), float(z.get("exit")), _r(z)
        if x == e or abs(r) < 1e-9:
            return "—"
        return "LONG" if (x > e) == (r > 0) else "SHORT"
    except Exception:
        return "—"


def _starty_progonov(ceh) -> list:
    d = CEHA / str(ceh or "") / "прогоны"
    try:
        return sorted(_iso(x.name) for x in d.iterdir() if re.fullmatch(r"\d{8}_\d{6}", x.name))
    except Exception:
        return []


def poschitat(zap: list, start: float = START, ceh=None) -> dict:
    """Сделка — запись(и) одного прогона с тем же входом: один и тот же
    исторический вход в двух прогонах — две разные сделки счёта."""
    from bisect import bisect_right
    starty = _starty_progonov(ceh)
    bal, pik, dd, dd_pct, dd_kogda = start, start, 0.0, 0.0, ""
    sdelki, risk_sd = {}, {}
    for z in zap:
        _ts = str(z.get("ts") or "")[:19]
        _prog = bisect_right(starty, _ts) if starty else 0
        k = (_prog, str(z.get("opened_at") or ""), round(float(z.get("entry") or 0), 5))
        if k not in risk_sd:
            risk_sd[k] = bal * RISK
        den = risk_sd[k] * _r(z)
        bal += den
        s = sdelki.setdefault(k, {"R": 0.0, "GRD": 0.0, "risk": risk_sd[k], "lot": None,
                                  "symbol": z.get("symbol"), "открыта": k[1],
                                  "вход": z.get("entry"), "сторона": "—",
                                  "закрыта": "", "выход": None, "ts": ""})
        s["R"] += _r(z)
        s["GRD"] += den
        s["закрыта"] = str(z.get("closed_at") or "")
        s["выход"] = z.get("exit")
        s["ts"] = str(z.get("ts") or "")
        s["баланс"] = bal
        if s["сторона"] == "—":
            s["сторона"] = _storona(z)
        if s["lot"] is None and not z.get("нога") and not z.get("частичное") and _r(z):
            try:
                dist = abs(float(z.get("pnl_price")) / _r(z))
                if dist > 0:
                    s["lot"] = round(risk_sd[k] / (dist * _razmer_lota(z.get("symbol"))), 4)
            except Exception:
                pass
        if bal > pik:
            pik = bal
        if pik - bal > dd:
            dd, dd_pct, dd_kogda = pik - bal, (pik - bal) / pik * 100, s["закрыта"]
    spisok = list(sdelki.values())
    out = {"старт": start, "баланс": bal, "риск_доля": RISK, "риск_GRD": bal * RISK,
           "сделок": len(spisok), "итог_GRD": bal - start,
           "итог_pct": (bal - start) / start * 100, "итог_R": sum(s["R"] for s in spisok),
           "просадка_GRD": dd, "просадка_pct": dd_pct, "просадка_когда": dd_kogda,
           "список": spisok}
    if not spisok:
        return out
    plus = [s for s in spisok if s["R"] > NOL]
    minus = [s for s in spisok if s["R"] < -NOL]
    zar = sum(s["GRD"] for s in plus)
    pot = -sum(s["GRD"] for s in minus)
    seriya, tek, dl = {"плюс": 0, "минус": 0}, None, 0
    for s in spisok:
        z = "плюс" if s["R"] > NOL else "минус" if s["R"] < -NOL else None
        dl = dl + 1 if (z and z == tek) else (1 if z else 0)
        tek = z
        if z:
            seriya[z] = max(seriya[z], dl)
    out.update(в_плюс=len(plus), в_минус=len(minus),
               профит_фактор=(zar / pot) if pot > 0 else None,
               лучшая=max(spisok, key=lambda s: s["R"]),
               худшая=min(spisok, key=lambda s: s["R"]), серии=seriya,
               лот=next((s["lot"] for s in reversed(spisok) if s["lot"] is not None), None))
    return out


def tekushchiy(ceh, slot) -> dict:
    s = sbros_kogda(ceh, slot)
    sc = poschitat(_zapisi(ceh, slot, s), ceh=ceh)
    sc["с"] = s
    return sc


def obshchiy(ceh, slot) -> dict:
    sc = poschitat(_zapisi(ceh, slot), ceh=ceh)
    sc["с"] = ""
    return sc


def schet(ceh, slot, run_id=None) -> dict:
    """Для старых вызовов: текущий счёт места."""
    return tekushchiy(ceh, slot)


# ── слова ────────────────────────────────────────────────────────
def chislo(x, znak=False) -> str:
    try:
        s = f"{x:+,.2f}" if znak else f"{x:,.2f}"
    except (TypeError, ValueError):
        return "—"
    return s.replace(",", " ").replace("-", "−")


def _pct(x) -> str:
    return f"{x:+.1f}%".replace("-", "−")


def stroki(sc: dict) -> list:
    L = [("БАЛАНС", f"{chislo(sc['баланс'])} {VAL}"
                    + (f" ({_pct(sc['итог_pct'])})" if sc.get("сделок") else "")),
         ("РИСК НА СДЕЛКУ", f"{chislo(sc['риск_GRD'])} {VAL} · {sc['риск_доля'] * 100:.0f}%"
                            + (f" · лот {sc['лот']}" if sc.get("лот") is not None else ""))]
    if not sc.get("сделок"):
        return L + [("СДЕЛОК", "закрытых пока нет")]
    L += [("ПРОСАДКА МАКС.", f"−{chislo(sc['просадка_GRD'])} {VAL} (−{sc['просадка_pct']:.1f}%)"
                             + (f" · {sc['просадка_когда']}" if sc.get("просадка_когда") else "")),
          ("ЛУЧШАЯ / ХУДШАЯ", (f"{sc['лучшая']['R']:+.2f}R ({chislo(sc['лучшая']['GRD'], True)}) / "
                               f"{sc['худшая']['R']:+.2f}R ({chislo(sc['худшая']['GRD'], True)})")
                              .replace("-", "−")),
          ("СЕРИИ ПОДРЯД", f"плюсов {sc['серии']['плюс']} · минусов {sc['серии']['минус']}"),
          ("СДЕЛОК", f"{sc['сделок']} · в плюс {sc['в_плюс']} · в минус {sc['в_минус']}"
                     + (f" · ПФ {sc['профит_фактор']:.2f}" if sc.get("профит_фактор") is not None
                        else ""))]
    return L


def stroka_obshchego(so: dict) -> tuple:
    if not so.get("сделок"):
        return ("ОБЩИЙ СЧЁТ", f"{chislo(so['баланс'])} {VAL} · сделок нет")
    return ("ОБЩИЙ СЧЁТ", f"{chislo(so['баланс'])} {VAL} ({_pct(so['итог_pct'])}) · "
                          f"сделок {so['сделок']} · просадка −{so['просадка_pct']:.1f}%")


def istoriya_html(sc: dict) -> str:
    spisok = sc.get("список") or []
    if not spisok:
        return '<div style="color:rgba(255,255,255,0.45); padding:10px;">закрытых сделок нет</div>'
    td = 'style="padding:4px 8px; border-bottom:1px solid rgba(255,255,255,0.07);"'
    h = ['<div style="overflow:auto; max-height:70vh;"><table style="border-collapse:collapse; '
         'font-family:\'JetBrains Mono\',monospace; font-size:11.5px; color:#e6edf3; width:100%;">',
         "<tr style=\"color:rgba(255,255,255,0.5); text-align:left;\">"
         + "".join(f"<th {td}>{x}</th>" for x in
                   ("№", "вход", "выход", "рынок", "сторона", "цена входа", "цена выхода",
                    "R", VAL, "баланс"))
         + "</tr>"]
    for i, s in enumerate(spisok, 1):
        cv = "#00ff88" if s["R"] > NOL else "#ff5050" if s["R"] < -NOL else "#e6edf3"
        h.append("<tr>" + "".join(f"<td {td}>{x}</td>" for x in (
            i, str(s["открыта"])[:16], str(s["закрыта"])[:16], s.get("symbol") or "—",
            s.get("сторона") or "—", s.get("вход"), s.get("выход"))) +
            f'<td {td} style="color:{cv};">{s["R"]:+.2f}</td>'.replace("-", "−") +
            f'<td {td} style="color:{cv};">{chislo(s["GRD"], True)}</td>' +
            f"<td {td}>{chislo(s.get('баланс'))}</td></tr>")
    h.append("</table></div>")
    return "".join(h)


# ── отчёт прогона ────────────────────────────────────────────────
def _iso(n: str) -> str:
    return f"{n[:4]}-{n[4:6]}-{n[6:8]}T{n[9:11]}:{n[11:13]}:{n[13:15]}"


def _okno_progona(ceh, run_id):
    d = CEHA / ceh / "прогоны"
    imena = sorted(x.name for x in d.iterdir()
                   if re.fullmatch(r"\d{8}_\d{6}", x.name)) if d.is_dir() else []
    if run_id not in imena:
        return None, None
    i = imena.index(run_id)
    return _iso(run_id), (_iso(imena[i + 1]) if i + 1 < len(imena) else "9999")


def razdel_otcheta(ceh: str, slot: str, run_id: str) -> list:
    a, b = _okno_progona(ceh, run_id)
    if not a:
        return []
    sc = tekushchiy(ceh, slot)
    v = [s for s in sc.get("список") or [] if a <= s.get("ts", "")[:19] < b]
    if not v:
        return []
    so = obshchiy(ceh, slot)
    s = [f"## Счёт места {slot} ({VAL})", "",
         f"Старт {chislo(START)} {VAL}, риск {RISK * 100:.0f}% от баланса; итог сделки = риск × R. "
         f"Счёт работника{(' ' + sc['владелец']) if sc.get('владелец') else ''} — с {sc.get('с') or 'начала'}, идёт с ним с места на место (Казначейство); общий — счёт места за всё "
         "время. Считает город, на решения не влияет.", "",
         "| показатель | значение |", "|---|---|",
         f"| вклад этого прогона | {chislo(sum(x['GRD'] for x in v), True)} {VAL} · "
         f"{sum(x['R'] for x in v):+.2f}R · сделок {len(v)} |".replace("-", "−")]
    s += [f"| {a_.lower()} | {b_} |" for a_, b_ in stroki(sc)]
    oa, ob = stroka_obshchego(so)
    s += [f"| {oa.lower()} | {ob} |", ""]
    return s


def dopisat_v_otchet(papka, ceh: str) -> list:
    papka = Path(papka)
    f = papka / "отчёт.md"
    if not f.is_file():
        return []
    t = f.read_text(encoding="utf-8")
    if "## Счёт места" in t:
        return []
    try:
        sloty = sorted({json.loads(s).get("слот") for s in
                        (papka / "места.jsonl").read_text(encoding="utf-8").splitlines()
                        if s.strip()} - {None})
    except Exception:
        sloty = []
    dop, out = [], []
    for sl in sloty:
        r = razdel_otcheta(ceh, sl, papka.name)
        if r:
            dop += r
            out.append(f"{sl}: счёт в отчёте")
    if dop:
        f.write_text(t.rstrip("\n") + "\n\n" + "\n".join(dop) + "\n", encoding="utf-8")
    return out


# SCHET_V2 - marker


# ══ SCHET_V5 — показатели жителя и живая сделка места ══
POSTY = KOREN / "GRONDHEIM_CITY" / "посты"


def _json_f(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def _posty() -> list:
    out = []
    try:
        for d in sorted(POSTY.iterdir()):
            p = _json_f(d / "пост.json")
            if p and isinstance(p.get("magic"), int) and p.get("цех") and p.get("слот"):
                out.append(p)
    except Exception:
        pass
    return out


def zhitel_na_meste(ceh, slot) -> str:
    for p in _posty():
        if p.get("цех") == ceh and str(p.get("слот")) == str(slot):
            return str(((p.get("кто_сидит") or {}).get("имя")) or "")
    return ""


def _sroki(post) -> list:
    sroki, otkryt = [], None
    for z in post.get("трудовая_история") or []:
        t = str(z.get("когда") or "")
        imya = str(z.get("кто") or "").strip()
        if z.get("что") == "принят" and imya:
            otkryt = (imya, t)
        elif z.get("что") == "уволен" and otkryt and otkryt[0] == imya:
            sroki.append((imya, otkryt[1], t))
            otkryt = None
    if otkryt:
        sroki.append((otkryt[0], otkryt[1], "9999"))
    return sroki



# ══ A07_NOMER_GORODA_V1 — прежний номер поста ══
# Пост сменил номер счёта (A07: 100002 → 100014). Сделки под прежним
# номером до минуты смены («прежний_magic_до» в посте) — этого поста.
_PREZH = {"t": -1e9, "d": {}}


def _prezhniy_post(m, ts16):
    import time as _t_ng
    if _t_ng.monotonic() - _PREZH["t"] > 5:
        d = {}
        try:
            for x in sorted(POSTY.iterdir()):
                p = _json_f(x / "пост.json")
                if (p and isinstance(p.get("прежний_magic"), int)
                        and p.get("прежний_magic_до") and p.get("цех") and p.get("слот")):
                    d.setdefault(p["прежний_magic"], []).append(p)
        except Exception:
            pass
        _PREZH.update(t=_t_ng.monotonic(), d=d)
    try:
        m = int(m)
    except Exception:
        return None
    kand = [p for p in _PREZH["d"].get(m, []) if str(ts16) < str(p["прежний_magic_до"])]
    return kand[0] if len(kand) == 1 else None


def sdelki_zhitelya(imya: str) -> list:
    """Её закрытые сделки на любом месте, по истории постов, по порядку."""
    from bisect import bisect_right
    imya = str(imya or "").strip()
    if not imya:
        return []
    posty = {p["magic"]: p for p in _posty()}
    sroki = {m: _sroki(p) for m, p in posty.items()}
    starty = {}
    sd = {}
    for z in sorted(_zhurnal(), key=lambda z: str(z.get("ts") or "")):
        ts16 = str(z.get("ts") or "").replace("T", " ")[:16]
        p = posty.get(z.get("magic")) or _prezhniy_post(z.get("magic"), ts16)   # A07_NOMER_GORODA_V1
        if not p:
            continue
        kto = next((i for i, a, b in _sroki(p) if a <= ts16 < b), None)
        if kto != imya:
            continue
        ceh = p["цех"]
        if ceh not in starty:
            starty[ceh] = _starty_progonov(ceh)
        prog = bisect_right(starty[ceh], str(z.get("ts") or "")[:19])
        k = (ceh, prog, str(z.get("opened_at") or ""), round(float(z.get("entry") or 0), 5))
        s = sd.setdefault(k, {"R": 0.0, "открыта": k[2], "закрыта": "", "symbol": z.get("symbol"),
                              "сторона": _storona(z), "вход": z.get("entry"), "выход": None,
                              "место": f"{ceh}/{p['слот']}"})
        s["R"] += _r(z)
        s["закрыта"] = str(z.get("closed_at") or "")
        s["выход"] = z.get("exit")
        if s["сторона"] == "—":
            s["сторона"] = _storona(z)
    return list(sd.values())


def pokazateli_zhitelya(imya: str) -> dict:
    sp = sdelki_zhitelya(imya)
    out = {"имя": imya, "сделок": len(sp), "список": sp}
    if not sp:
        return out
    cum = pik = dd = 0.0
    for s in sp:
        cum += s["R"]
        pik = max(pik, cum)
        dd = max(dd, pik - cum)
    plus = [s for s in sp if s["R"] > NOL]
    minus = [s for s in sp if s["R"] < -NOL]
    pot = -sum(s["R"] for s in minus)
    seriya, tek, dl = {"плюс": 0, "минус": 0}, None, 0
    for s in sp:
        z = "плюс" if s["R"] > NOL else "минус" if s["R"] < -NOL else None
        dl = dl + 1 if (z and z == tek) else (1 if z else 0)
        tek = z
        if z:
            seriya[z] = max(seriya[z], dl)
    out.update(в_плюс=len(plus), в_минус=len(minus), итог_R=cum, просадка_R=dd,
               лучшая_R=max(s["R"] for s in sp), худшая_R=min(s["R"] for s in sp),
               серии=seriya, профит_фактор=(sum(s["R"] for s in plus) / pot) if pot > 0 else None)
    return out


def _stol(ceh) -> dict:
    return _json_f(CEHA / ceh / "данные" / "trading_state.json") or {}


def _otkrytye(ceh, slot) -> list:
    magic = _nomer(ceh, slot)
    if magic is None:
        return []
    return [p for p in (_stol(ceh).get("positions") or [])
            if str(p.get("status") or "").upper() == "OPEN" and p.get("magic") == magic
            and not p.get("тень")]


def zhivoy_klyuch(ceh, slot) -> tuple:
    """Что меняется в живой сделке: бар города и позиции места."""
    st = _stol(ceh)
    bar = str(((st.get("рынок") or {}).get("бар")) or "")
    return (bar, tuple((p.get("entry"), p.get("stop"), p.get("status")) for p in _otkrytye(ceh, slot)))


def v_sdelke(ceh, slot, balans: float):
    """Открытая сделка места: R сейчас по последнему закрытому бару и ≈ GRD."""
    poz = _otkrytye(ceh, slot)
    if not poz:
        return None
    try:
        from feed_source import bars as _bars
    except Exception:
        return None
    R = 0.0
    n = 0
    for p in poz:
        try:
            e = float(p.get("entry"))
            s0 = float(p.get("stop_initial") if p.get("stop_initial") is not None else p.get("stop"))
            risk = abs(e - s0)
            if risk <= 0:
                continue
            bs, _pt = _bars(p.get("symbol"), str(p.get("timeframe") or "D1"), 3)
            try:
                import hooks as _h
                bs = _h._tolko_zakrytye(bs)
            except Exception:
                pass
            if not bs:
                continue
            cena = float(bs[-1]["close"])
            napr = str(p.get("direction") or "").upper()
            long_ = napr == "LONG" if napr in ("LONG", "SHORT") else e > s0
            R += ((cena - e) if long_ else (e - cena)) / risk
            n += 1
        except Exception:
            continue
    if not n:
        return None
    return {"R": R, "GRD": R * balans * RISK, "сделок": n}


def istoriya_zhitelya_html(pz: dict) -> str:
    sp = pz.get("список") or []
    if not sp:
        return '<div style="color:rgba(255,255,255,0.45); padding:10px;">закрытых сделок нет</div>'
    td = 'style="padding:4px 8px; border-bottom:1px solid rgba(255,255,255,0.07);"'
    h = ['<div style="overflow:auto; max-height:70vh;"><table style="border-collapse:collapse; '
         'font-family:\'JetBrains Mono\',monospace; font-size:11.5px; color:#e6edf3; width:100%;">',
         "<tr style=\"color:rgba(255,255,255,0.5); text-align:left;\">"
         + "".join(f"<th {td}>{x}</th>" for x in
                   ("№", "место", "вход", "выход", "рынок", "сторона", "цена входа",
                    "цена выхода", "R", "итог R"))
         + "</tr>"]
    cum = 0.0
    for i, s in enumerate(sp, 1):
        cum += s["R"]
        cv = "#00ff88" if s["R"] > NOL else "#ff5050" if s["R"] < -NOL else "#e6edf3"
        h.append("<tr>" + "".join(f"<td {td}>{x}</td>" for x in (
            i, s.get("место"), str(s["открыта"])[:16], str(s["закрыта"])[:16],
            s.get("symbol") or "—", s.get("сторона") or "—", s.get("вход"), s.get("выход")))
            + f'<td {td} style="color:{cv};">' + f'{s["R"]:+.2f}'.replace("-", "−") + "</td>"
            + f"<td {td}>" + f"{cum:+.2f}".replace("-", "−") + "</td></tr>")
    h.append("</table></div>")
    return "".join(h)


# SCHET_V5 - marker


# ══ SCHET_PUNKTY_V1 — прибыль в пунктах ══
def _punkt(cena) -> float:
    try:
        c = abs(float(cena))
    except (TypeError, ValueError):
        return 0.00001
    return 0.00001 if c < 20 else (0.001 if c < 500 else 0.01)


def punkty_tekushchego(ceh, slot) -> float:
    """Пункты закрытых сделок текущего счёта места (со сброса)."""
    s = 0.0
    for z in _zapisi(ceh, slot, sbros_kogda(ceh, slot)):
        try:
            s += float(z.get("pnl_price") or 0) / _punkt(z.get("entry"))
        except Exception:
            pass
    return s


def punkty_v_sdelke(ceh, slot) -> float | None:
    """Пункты открытой сделки места сейчас — по последнему закрытому бару."""
    poz = _otkrytye(ceh, slot)
    if not poz:
        return None
    try:
        from feed_source import bars as _bars
    except Exception:
        return None
    s, n = 0.0, 0
    for p in poz:
        try:
            e = float(p.get("entry"))
            s0 = float(p.get("stop_initial") if p.get("stop_initial") is not None else p.get("stop"))
            bs, _pt = _bars(p.get("symbol"), str(p.get("timeframe") or "D1"), 3)
            try:
                import hooks as _h
                bs = _h._tolko_zakrytye(bs)
            except Exception:
                pass
            if not bs:
                continue
            cena = float(bs[-1]["close"])
            napr = str(p.get("direction") or "").upper()
            long_ = napr == "LONG" if napr in ("LONG", "SHORT") else e > s0
            s += ((cena - e) if long_ else (e - cena)) / _punkt(e)
            n += 1
        except Exception:
            continue
    return s if n else None


# SCHET_PUNKTY_V1 - marker


# ══ SCHET_TERMINAL_V1 — показатели места как у терминала: позиции, средства ══
# Слово Шефа 27.10 (по отчёту MT5): «к такому виду нужно стремиться —
# показатели». Маржу «вовсе не показывать»: плеча у нас нет. Т/П и своп —
# прочерк: тейков у нас нет, своп в истории не считается.
def pozicii(ceh, slot) -> list:
    """Открытые позиции места строками терминала (без тени)."""
    poz = _otkrytye(ceh, slot)
    if not poz:
        return []
    try:
        from feed_source import bars as _bars
    except Exception:
        _bars = None
    bal = tekushchiy(ceh, slot)["баланс"]
    risk_grd = bal * RISK
    out = []
    for i, p in enumerate(poz, 1):
        try:
            e = float(p.get("entry"))
            s0 = float(p.get("stop_initial") if p.get("stop_initial") is not None
                       else p.get("stop"))
        except Exception:
            continue
        napr = str(p.get("direction") or "").upper()
        long_ = napr == "LONG" if napr in ("LONG", "SHORT") else e > s0
        cena = None
        if _bars:
            try:
                bs, _pt = _bars(p.get("symbol"), str(p.get("timeframe") or "D1"), 3)
                try:
                    import hooks as _h
                    bs = _h._tolko_zakrytye(bs)
                except Exception:
                    pass
                if bs:
                    cena = float(bs[-1]["close"])
            except Exception:
                cena = None
        risk = abs(e - s0)
        R = (((cena - e) if long_ else (e - cena)) / risk) if (cena is not None and risk > 0) else None
        lot = (round(risk_grd / (risk * _razmer_lota(p.get("symbol"))), 4)
               if risk > 0 else None)
        out.append({"№": i, "символ": p.get("symbol") or "—",
                    "время": str(p.get("opened_at") or "—")[:16],
                    "тип": "buy" if long_ else "sell", "объём": lot, "цена": e,
                    "sl": p.get("stop"), "tp": None, "рыночная": cena, "своп": None,
                    "R": R, "прибыль": (R * risk_grd) if R is not None else None})
    return out


def terminal(ceh, slot) -> dict:
    sc = tekushchiy(ceh, slot)
    pp = pozicii(ceh, slot)
    plav = sum(x["прибыль"] for x in pp if x["прибыль"] is not None)
    return {"баланс": sc["баланс"], "плавающая": plav, "средства": sc["баланс"] + plav,
            "позиции": pp}


def _ch(x, znak=False):
    return "—" if x is None else chislo(x, znak)


def pozicii_html(t: dict) -> str:
    td = 'style="padding:4px 8px; border-bottom:1px solid rgba(255,255,255,0.07);"'
    pp = t.get("позиции") or []
    h = ['<div style="overflow:auto; max-height:70vh;"><table style="border-collapse:collapse; '
         'font-family:\'JetBrains Mono\',monospace; font-size:11.5px; color:#e6edf3; width:100%;">',
         "<tr style=\"color:rgba(255,255,255,0.5); text-align:left;\">"
         + "".join(f"<th {td}>{x}</th>" for x in
                   ("Символ", "Позиция", "Время", "Тип", "Объём", "Цена", "S / L", "T / P",
                    "Рыночная цена", "Своп", "Прибыль", "R"))
         + "</tr>"]
    if not pp:
        h.append(f'<tr><td {td} colspan="12" style="color:rgba(255,255,255,0.5);">'
                 'открытых позиций нет</td></tr>')
    for x in pp:
        cv = ("#00ff88" if (x["прибыль"] or 0) > 0 else "#ff5050"
              if (x["прибыль"] or 0) < 0 else "#e6edf3")
        r_t = "—" if x["R"] is None else f"{x['R']:+.2f}".replace("-", "−")
        h.append("<tr>" + "".join(f"<td {td}>{v}</td>" for v in (
            x["символ"], x["№"], x["время"], x["тип"],
            x["объём"] if x["объём"] is not None else "—", x["цена"],
            x["sl"] if x["sl"] is not None else "—", "—",
            x["рыночная"] if x["рыночная"] is not None else "—", "—"))
            + f'<td {td} style="color:{cv};">{_ch(x["прибыль"], True)}</td>'
            + f'<td {td} style="color:{cv};">{r_t}</td></tr>')
    h.append("</table></div>")
    cv = "#00ff88" if t["плавающая"] > 0 else "#ff5050" if t["плавающая"] < 0 else "#e6edf3"
    h.append('<div style="display:grid; grid-template-columns:auto auto; gap:4px 18px; '
             'justify-content:end; margin-top:10px; font-family:\'JetBrains Mono\',monospace; '
             'font-size:12px; color:#e6edf3;">'
             f'<span>Баланс:</span><b>{chislo(t["баланс"])} {VAL}</b>'
             f'<span>Плавающая прибыль/убыток:</span><b style="color:{cv};">'
             f'{chislo(t["плавающая"], True)} {VAL}</b>'
             f'<span>Средства:</span><b>{chislo(t["средства"])} {VAL}</b></div>')
    return "".join(h)


_istoriya_html_do_terminala = istoriya_html


def istoriya_html(sc: dict) -> str:   # noqa: F811
    """Сделки — с объёмом, как у терминала."""
    spisok = sc.get("список") or []
    if not spisok:
        return _istoriya_html_do_terminala(sc)
    td = 'style="padding:4px 8px; border-bottom:1px solid rgba(255,255,255,0.07);"'
    h = ['<div style="overflow:auto; max-height:70vh;"><table style="border-collapse:collapse; '
         'font-family:\'JetBrains Mono\',monospace; font-size:11.5px; color:#e6edf3; width:100%;">',
         "<tr style=\"color:rgba(255,255,255,0.5); text-align:left;\">"
         + "".join(f"<th {td}>{x}</th>" for x in
                   ("№", "Вход", "Выход", "Символ", "Тип", "Объём", "Цена входа",
                    "Цена выхода", "R", "Прибыль", "Баланс"))
         + "</tr>"]
    for i, s in enumerate(spisok, 1):
        cv = "#00ff88" if s["R"] > NOL else "#ff5050" if s["R"] < -NOL else "#e6edf3"
        tip = {"LONG": "buy", "SHORT": "sell"}.get(s.get("сторона"), "—")
        h.append("<tr>" + "".join(f"<td {td}>{x}</td>" for x in (
            i, str(s["открыта"])[:16], str(s["закрыта"])[:16], s.get("symbol") or "—",
            tip, s.get("lot") if s.get("lot") is not None else "—",
            s.get("вход"), s.get("выход"))) +
            f'<td {td} style="color:{cv};">' + f'{s["R"]:+.2f}'.replace("-", "−") + "</td>"
            + f'<td {td} style="color:{cv};">{chislo(s["GRD"], True)}</td>'
            + f"<td {td}>{chislo(s.get('баланс'))}</td></tr>")
    h.append("</table></div>")
    return "".join(h)


_razdel_otcheta_do_terminala = razdel_otcheta


def razdel_otcheta(ceh: str, slot: str, run_id: str) -> list:   # noqa: F811
    s = list(_razdel_otcheta_do_terminala(ceh, slot, run_id) or [])
    try:
        t = terminal(ceh, slot)
    except Exception:
        return s
    if not s and not t["позиции"]:
        return s
    if not s:
        s = [f"## Счёт места {slot} ({VAL})", ""]
    s += ["### Торговый отчёт места (как у терминала)", "",
          "| Символ | Позиция | Время | Тип | Объём | Цена | S / L | T / P | Рыночная цена "
          "| Своп | Прибыль | R |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    if not t["позиции"]:
        s.append("| открытых позиций на конец прогона нет | | | | | | | | | | | |")
    for x in t["позиции"]:
        s.append(f"| {x['символ']} | {x['№']} | {x['время']} | {x['тип']} | "
                 f"{x['объём'] if x['объём'] is not None else '—'} | {x['цена']} | "
                 f"{x['sl'] if x['sl'] is not None else '—'} | — | "
                 f"{x['рыночная'] if x['рыночная'] is not None else '—'} | — | "
                 f"{_ch(x['прибыль'], True)} | "
                 + ("—" if x["R"] is None else f"{x['R']:+.2f}".replace("-", "−")) + " |")
    s += ["", f"Баланс: **{chislo(t['баланс'])} {VAL}** · Плавающая прибыль/убыток: "
          f"**{chislo(t['плавающая'], True)} {VAL}** · Средства: **{chislo(t['средства'])} {VAL}**",
          ""]
    return s


# SCHET_TERMINAL_V1 - marker


# A07_NOMER_GORODA_V1 - marker


# ══ KAZNA_V1 — «текущий» счёт места → счёт работника, кто сидит на месте ══
# Слово Шефа 31.10. Счёт места (общий) — как был. Никого нет — по-старому.
_tekushchiy_mesta = tekushchiy


def tekushchiy(ceh, slot) -> dict:   # noqa: F811
    try:
        import kazna as _kz
        sc = _kz.dlya_mesta(ceh, slot)
        if sc is not None:
            return sc
    except Exception as e:
        print(f"[КАЗНА] счёт работника не посчитался ({e}) — показываю счёт места")
    return _tekushchiy_mesta(ceh, slot)


# KAZNA_V1 - marker


# ══ KAZNA_MESTA_V2 — пустое место: сколько накапало с нуля ══
# Слово Шефа 31.10. Считается как прежде (риск от 100 + накапавшего),
# показывается накапавшее. На месте работник — его личный счёт, как есть.
_tekushchiy_do_nakapalo = tekushchiy


def tekushchiy(ceh, slot) -> dict:   # noqa: F811
    sc = _tekushchiy_do_nakapalo(ceh, slot)
    if sc.get("владелец"):
        return sc
    sc = dict(sc)
    st = float(sc.get("старт") or START)
    nak = float(sc.get("баланс") or st) - st
    sc["список"] = [dict(x, баланс=float(x.get("баланс") or st) - st)
                    for x in (sc.get("список") or [])]
    sc.update({"баланс": nak, "старт": 0.0, "итог_GRD": nak, "место_накапало": True})
    return sc


# KAZNA_MESTA_V2 - marker


# ══ OBSHCHIY_S_V1 — у общего счёта места может быть начало ══
# Слово Шефа 31.10: «счёт новый» — пересобранное место считает общий счёт с
# минуты пересборки. Начала нет — за всё время, как было.
def obshchiy_nachalo(ceh, slot) -> str:
    try:
        return str(json.loads(_put_sbrosa(ceh, slot).read_text(encoding="utf-8")).get("общий_с") or "")
    except Exception:
        return ""


def obshchiy_s_nachala(ceh, slot, kogda: str, pochemu: str = "") -> str:
    """Поставить начало общего счёта места (один раз; уже есть — не сдвигаю)."""
    p = _put_sbrosa(ceh, slot)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    if d.get("общий_с"):
        return d["общий_с"]
    d["общий_с"] = kogda
    d["общий_с_почему"] = pochemu
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return kogda


_obshchiy_do_nachala = obshchiy


def obshchiy(ceh, slot) -> dict:   # noqa: F811
    s = obshchiy_nachalo(ceh, slot)
    if not s:
        return _obshchiy_do_nachala(ceh, slot)
    sc = poschitat(_zapisi(ceh, slot, s), ceh=ceh)
    sc["с"] = s
    return sc


# OBSHCHIY_S_V1 - marker
