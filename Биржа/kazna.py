# -*- coding: utf-8 -*-
# KAZNA_V2
"""
Казначейство Биржи (31.10, слово Шефа).

    «Счёт Биржи — он единый на всю Биржу — 100. Счёт места — сколько место
    принесло — ок. И новый персональный: выдал 100 грондов — он стал счётом
    Биржи, а ушла — что накапало, то осталось; прибыль делится 50/50 после
    ухода.» «Приходит новый житель со своими 100 — так же расчёт, и плюс сумма
    с торговли на счёт Биржи; так со всех мест копится и не сбрасывается;
    потом, когда реал подключим, сбросим.» «Убыток отработает потом.»

КАК УСТРОЕНО (считается с минуты, когда Казначейство открыто)
    Счёт Биржи — один: 100 + взносы работников + вся торговля всех работников
        на всех местах − выплаты ушедшим. Не сбрасывается.
    Личный счёт работника — его доля: устроился на Биржу — из паспорта
        (Balance_GND) уходят 100, это его депозит. Торгует на любых местах,
        перешёл на другое место — счёт с ним. Риск 1% от его баланса.
    Ушёл с Биржи (за час не устроился на другое место Биржи) — расчёт: в
        прибыли — ему депозит + половина прибыли, вторая половина остаётся
        Бирже; в убытке — ему остаток, убыток записан «к отработке».
        Личный счёт уходит в архив. Пришёл снова — снова вносит 100.
    Файлы: GRONDHEIM_CITY/Биржа/казначейство/
        счёт_биржи.json · счета/<Имя>.json (работают) ·
        архив/<Имя>_<дата>.json (закрытые, с расчётом).
    В паспорт город пишет только два движения: −взнос при найме, +выплата при
    уходе (к тому, что там сейчас). Руками в Реестре — можно, не мешает.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
KOREN = _BIRZHA.parent
CITY = KOREN / "GRONDHEIM_CITY"
POSTY = CITY / "посты"
CEHA = CITY / "Биржа" / "цеха"
KAZNA = CITY / "Биржа" / "казначейство"
SCHETA = KAZNA / "счета"
ARHIV = KAZNA / "архив"
BIRZHA_F = KAZNA / "счёт_биржи.json"
KOVCHEG = CITY / "жители" / "ковчег"
POLE = "Balance_GND"
VZNOS = 100.0
START_BIRZHI = 100.0
DOLYA_BIRZHI = 0.5
PEREHOD_MIN = 60          # устроился на другое место Биржи за час — перешёл, не ушёл
_KESH = {}


def _sch():
    import schet as _s
    return _s


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def _pisat_json(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _t(s):
    s = str(s or "").replace("T", " ")[:16]
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except Exception:
        return None


def schet_birzhi_otkryt() -> dict:
    d = _json(BIRZHA_F)
    if not d:
        d = {"старт": START_BIRZHI, "открыт": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "сброс": "когда подключим реал"}
        _pisat_json(BIRZHA_F, d)
    return d


def _posty_birzhi() -> list:
    out = []
    try:
        for d in sorted(POSTY.iterdir()):
            p = _json(d / "пост.json")
            if not p or not p.get("цех"):
                continue
            if p.get("квартал") == "Биржа" or (CEHA / str(p["цех"])).is_dir():
                out.append(p)
    except Exception:
        pass
    return out


def cikly() -> dict:
    """{имя: [цикл]} — цикл работы на Бирже с момента открытия Казначейства.
    Цикл: {с, до ('9999' — работает), сроки: [{цех, слот, magic, …, с, до}]}.
    Переход на другое место Биржи в течение часа — тот же цикл."""
    otkryt = schet_birzhi_otkryt()["открыт"]
    sroki = {}
    for p in _posty_birzhi():
        for imya, a, b in _sch()._sroki(p):
            if b != "9999" and b <= otkryt:
                continue
            sroki.setdefault(imya, []).append({
                "цех": p.get("цех"), "слот": p.get("слот"), "magic": p.get("magic"),
                "прежний_magic": p.get("прежний_magic"),
                "прежний_magic_до": p.get("прежний_magic_до"),
                "с": max(a, otkryt), "до": b})
    out = {}
    for imya, ss in sroki.items():
        ss.sort(key=lambda x: x["с"])
        cs = []
        for s in ss:
            if cs:
                c = cs[-1]
                konec = _t(c["до"]) if c["до"] != "9999" else None
                nach = _t(s["с"])
                if c["до"] == "9999" or (konec and nach and nach - konec <= timedelta(minutes=PEREHOD_MIN)):
                    c["сроки"].append(s)
                    c["до"] = "9999" if s["до"] == "9999" or c["до"] == "9999" else max(c["до"], s["до"])
                    continue
            cs.append({"с": s["с"], "до": s["до"], "сроки": [s]})
        # уволен меньше часа назад — может, переходит: цикл ещё не закрыт
        seychas = datetime.now()
        for c in cs:
            k = _t(c["до"]) if c["до"] != "9999" else None
            c["ждёт"] = bool(k and seychas - k < timedelta(minutes=PEREHOD_MIN))
        out[imya] = cs
    return out


def _pasport(imya):
    p = KOVCHEG / str(imya) / "passport.json"
    return p, (_json(p) if p.is_file() else None)


def _pasport_dobavit(imya, summa: float):
    """К тому, что сейчас в паспорте, прибавить (или вычесть). → (было, стало)."""
    p, d = _pasport(imya)
    if not d:
        return None, None
    try:
        bylo = float(d.get(POLE))
    except (TypeError, ValueError):
        bylo = 0.0
    d[POLE] = round(bylo + summa, 2)
    _pisat_json(p, d)
    return bylo, d[POLE]


def _zapisi(sroki: list) -> list:
    out = []
    for z in _sch()._zhurnal():
        ts16 = str(z.get("ts") or "").replace("T", " ")[:16]
        m = z.get("magic")
        for s in sroki:
            if not (s["с"] <= ts16 < s["до"]):
                continue
            if m is not None and (m == s["magic"] or (
                    m == s["прежний_magic"] and s["прежний_magic_до"]
                    and ts16 < str(s["прежний_magic_до"]))):
                out.append((s["цех"], z))
                break
    out.sort(key=lambda x: str(x[1].get("ts") or ""))
    return out


def poschitat(imya: str, start: float, zapisi: list) -> dict:
    """Как счёт места (schet.poschitat), но сделки — с разных мест Биржи.
    Сделка — записи одного прогона с тем же входом."""
    from bisect import bisect_right
    s_ = _sch()
    starty = {}
    bal = pik = start
    dd = dd_pct = 0.0
    dd_kogda = ""
    sdelki, risk_sd = {}, {}
    for ceh, z in zapisi:
        ts = str(z.get("ts") or "")[:19]
        if ceh not in starty:
            starty[ceh] = s_._starty_progonov(ceh)
        prog = bisect_right(starty[ceh], ts) if starty[ceh] else 0
        k = (ceh, prog, str(z.get("opened_at") or ""), round(float(z.get("entry") or 0), 5))
        if k not in risk_sd:
            risk_sd[k] = bal * s_.RISK
        den = risk_sd[k] * s_._r(z)
        bal += den
        s = sdelki.setdefault(k, {"R": 0.0, "GRD": 0.0, "risk": risk_sd[k], "lot": None,
                                  "symbol": z.get("symbol"), "открыта": k[2],
                                  "вход": z.get("entry"), "сторона": "—", "закрыта": "",
                                  "выход": None, "ts": ""})
        s["R"] += s_._r(z)
        s["GRD"] += den
        s["закрыта"] = str(z.get("closed_at") or "")
        s["выход"] = z.get("exit")
        s["ts"] = str(z.get("ts") or "")
        s["баланс"] = bal
        if s["сторона"] == "—":
            s["сторона"] = s_._storona(z)
        if s["lot"] is None and not z.get("нога") and not z.get("частичное") and s_._r(z):
            try:
                dist = abs(float(z.get("pnl_price")) / s_._r(z))
                if dist > 0:
                    s["lot"] = round(risk_sd[k] / (dist * s_._razmer_lota(z.get("symbol"))), 4)
            except Exception:
                pass
        if bal > pik:
            pik = bal
        if pik - bal > dd:
            dd, dd_pct, dd_kogda = pik - bal, (pik - bal) / pik * 100, s["закрыта"]
    spisok = list(sdelki.values())
    out = {"старт": start, "баланс": bal, "риск_доля": s_.RISK, "риск_GRD": bal * s_.RISK,
           "сделок": len(spisok), "итог_GRD": bal - start,
           "итог_pct": ((bal - start) / start * 100) if start else 0.0,
           "итог_R": sum(s["R"] for s in spisok), "просадка_GRD": dd,
           "просадка_pct": dd_pct, "просадка_когда": dd_kogda, "список": spisok,
           "владелец": imya}
    if not spisok:
        return out
    plus = [s for s in spisok if s["R"] > s_.NOL]
    minus = [s for s in spisok if s["R"] < -s_.NOL]
    zar = sum(s["GRD"] for s in plus)
    pot = -sum(s["GRD"] for s in minus)
    seriya, tek, dl = {"плюс": 0, "минус": 0}, None, 0
    for s in spisok:
        zn = "плюс" if s["R"] > s_.NOL else "минус" if s["R"] < -s_.NOL else None
        dl = dl + 1 if (zn and zn == tek) else (1 if zn else 0)
        tek = zn
        if zn:
            seriya[zn] = max(seriya[zn], dl)
    out.update(в_плюс=len(plus), в_минус=len(minus),
               профит_фактор=(zar / pot) if pot > 0 else None,
               лучшая=max(spisok, key=lambda s: s["R"]),
               худшая=min(spisok, key=lambda s: s["R"]), серии=seriya,
               лот=next((s["lot"] for s in reversed(spisok) if s["lot"] is not None), None))
    return out


def _put_cikla(imya, c, zakryt: bool) -> Path:
    if not zakryt:
        return SCHETA / f"{imya}.json"
    return ARHIV / f"{imya}_{str(c['с'])[:10]}_{str(c['с'])[11:16].replace(':', '')}.json"


def _raschet(depozit: float, balans: float) -> dict:
    pribyl = balans - depozit
    if pribyl > 0:
        dolya = round(pribyl * DOLYA_BIRZHI, 2)
        return {"прибыль": round(pribyl, 2), "выплата": round(balans - dolya, 2),
                "доля_биржи": dolya, "к_отработке": 0.0}
    return {"прибыль": round(pribyl, 2), "выплата": round(max(balans, 0.0), 2),
            "доля_биржи": 0.0, "к_отработке": round(-pribyl, 2)}


def schet_cikla(imya: str, c: dict, pishi: bool = False) -> dict:
    """Личный счёт одного цикла работы. pishi=True — взнос из паспорта при
    открытии, расчёт и выплата в паспорт при закрытии, файл."""
    zakryt = c["до"] != "9999" and not c.get("ждёт")
    put = _put_cikla(imya, c, zakryt)
    staryy = SCHETA / f"{imya}.json"
    d = _json(put) or (_json(staryy) if zakryt and staryy.is_file()
                       and (_json(staryy) or {}).get("с") == c["с"] else None) or {}
    if not d:
        d = {"владелец": imya, "с": c["с"], "депозит": VZNOS, "взнос_списан": False}
    if pishi and not d.get("взнос_списан"):
        _p, pd = _pasport(imya)
        try:
            v_k = float((pd or {}).get(POLE))
        except (TypeError, ValueError):
            v_k = 0.0
        dep = round(min(VZNOS, max(v_k, 0.0)), 2) if pd else VZNOS
        d["депозит"] = dep
        if pd:
            bylo, stalo = _pasport_dobavit(imya, -dep)
            d["паспорт_при_найме"] = {"было": bylo, "стало": stalo}
        d["взнос_списан"] = True
        print(f"[КАЗНА] {imya}: на Биржу — взнос {dep:.2f} GRD из паспорта "
              f"на счёт Биржи")
    sc = poschitat(imya, float(d.get("депозит") or VZNOS), _zapisi(c["сроки"]))
    posl = c["сроки"][-1]
    sc.update({"с": c["с"], "до": c["до"],
               "статус": "ушёл" if zakryt else ("уволен, ждёт перехода" if c.get("ждёт")
                                                 else "в работе"),
               "где": f"{posl['цех']} · {posl['слот']}",
               "места": sorted({f"{s['цех']} · {s['слот']}" for s in c["сроки"]})})
    if zakryt:
        r = d.get("расчёт") or _raschet(float(d.get("депозит") or VZNOS), sc["баланс"])
        sc["расчёт"] = r
    if pishi:
        d.update({"до": c["до"], "статус": sc["статус"], "где": sc["где"], "места": sc["места"],
                  "баланс": round(sc["баланс"], 2), "сделок": sc["сделок"],
                  "итог_GRD": round(sc["итог_GRD"], 2), "итог_R": round(sc["итог_R"], 2),
                  "обновлён": datetime.now().strftime("%Y-%m-%d %H:%M")})
        if zakryt and not d.get("выплачено"):
            r = _raschet(float(d.get("депозит") or VZNOS), sc["баланс"])
            d["расчёт"] = r
            bylo, stalo = _pasport_dobavit(imya, r["выплата"])
            d["выплачено"] = True
            d["паспорт_при_уходе"] = {"было": bylo, "стало": stalo}
            print(f"[КАЗНА] {imya}: уход с Биржи — расчёт: выплата {r['выплата']:.2f} GRD в "
                  f"паспорт, доля Биржи {r['доля_биржи']:.2f}"
                  + (f", к отработке {r['к_отработке']:.2f}" if r["к_отработке"] else ""))
        _pisat_json(put, d)
        if zakryt and staryy.is_file() and staryy != put and (_json(staryy) or {}).get("с") == c["с"]:
            staryy.unlink()
    return sc


def schet_birzhi(cs_vse: dict | None = None) -> dict:
    """Счёт Биржи: 100 + взносы + торговля всех работников − выплаты."""
    sb = schet_birzhi_otkryt()
    cs_vse = cs_vse if cs_vse is not None else {k: [schet_cikla(k, c) for c in v]
                                                for k, v in cikly().items()}
    vznosy = torg = vyplaty = dolya = 0.0
    for scs in cs_vse.values():
        for sc in scs:
            vznosy += sc["старт"]
            torg += sc["итог_GRD"]
            r = sc.get("расчёт")
            if r:
                vyplaty += r["выплата"]
                dolya += r["доля_биржи"]
    bal = float(sb["старт"]) + vznosy + torg - vyplaty
    return {"старт": float(sb["старт"]), "открыт": sb["открыт"], "взносы": vznosy,
            "торговля": torg, "выплаты": vyplaty, "доля_биржи": dolya, "баланс": bal}


def sinhron_vse() -> list:
    """Пересчитать и записать: взносы, расчёты ушедших, файлы. → личные счета."""
    out, vse = [], {}
    for imya, cs in sorted(cikly().items()):
        for c in cs:
            try:
                sc = schet_cikla(imya, c, pishi=True)
                out.append(sc)
                vse.setdefault(imya, []).append(sc)
            except Exception as e:
                print(f"[КАЗНА] {imya}: счёт не пересчитался ({e})")
    try:
        sb = schet_birzhi(vse)
        d = schet_birzhi_otkryt()
        d.update({k: round(v, 2) if isinstance(v, float) else v for k, v in sb.items()},
                 обновлён=datetime.now().strftime("%Y-%m-%d %H:%M"))
        _pisat_json(BIRZHA_F, d)
    except Exception as e:
        print(f"[КАЗНА] счёт Биржи не пересчитался ({e})")
    _KESH.clear()
    return out


def _kto_sidit(ceh, slot) -> str:
    """Кто сидит на месте Биржи — и там, где у места нет номера счёта (контора)."""
    for p in _posty_birzhi():
        if p.get("цех") == ceh and str(p.get("слот")) == str(slot):
            imya = str(((p.get("кто_сидит") or {}).get("имя")) or "")
            if imya:
                return imya
            otkr = [i for i, a, b in _sch()._sroki(p) if b == "9999"]
            return otkr[-1] if otkr else ""
    return ""


def dlya_mesta(ceh, slot) -> dict | None:
    """Личный счёт того, кто сидит на месте (без записи) — для приборов."""
    imya = _sch().zhitel_na_meste(ceh, slot) or _kto_sidit(ceh, slot)   # KAZNA_MESTA_V2
    if not imya:
        return None
    try:
        mt = os.path.getmtime(_sch().ZHURNAL)
    except Exception:
        mt = 0
    k = (imya, mt)
    v = _KESH.get(k)
    if v and time.monotonic() - v[0] < 5:
        return v[1]
    c = next((c for c in reversed(cikly().get(imya) or []) if c["до"] == "9999"), None)
    sc = schet_cikla(imya, c) if c else None
    _KESH.clear()
    _KESH[k] = (time.monotonic(), sc)
    return sc


def vse_scheta() -> list:
    """[(статус, данные)] — работающие, потом архив (свежие первыми)."""
    out = []
    for f in sorted(SCHETA.glob("*.json")) if SCHETA.is_dir() else []:
        d = _json(f)
        if d:
            out.append(("в работе", d))
    for f in sorted(ARHIV.glob("*.json"), reverse=True) if ARHIV.is_dir() else []:
        d = _json(f)
        if d:
            out.append(("в архиве", d))
    return out


# KAZNA_V2 - marker
