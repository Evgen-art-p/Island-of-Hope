# -*- coding: utf-8 -*-
# METRIKI_INVESTORA_V1
"""
Метрики инвестора по жителям-трейдерам (31.10, записка «инвесторы оценивают»).

СЧИТАЕТ ГОРОД, НЕ МОДЕЛЬ. Из журнала города (trading_pnl.jsonl) — те же
правила, что у картотеки: чей номер счёта, кто сидел, какой прогон.

СЕРИЯ — история жителя на одном месте и одной паре (например «D02 · GBPUSD
D1 · 2015–2019»): все его прогоны там склеены в одну. Годы, прогнанные
дважды, не задваиваются: берётся самый свежий прогон, а сделки старых
прогонов, попавшие в его рыночное окно, отбрасываются. Так все жители
считаются на одинаковых данных и одинаковыми правилами.

ЧТО СЧИТАЕТСЯ (R — от риска на входе; % — при риске 1% на сделку):
    итог R и %, сделок и лет, матожидание сделки, доля прибыльных, средний
    выигрыш и убыток, Profit Factor, максимальная просадка и самое долгое
    возвращение к максимуму, серия убытков, худшая сделка, по годам,
    «без трёх лучших», Sharpe и Sortino по месяцам. Выборка меньше 30
    сделок — пометка «выборка мала».
ЧЕГО НЕ СЧИТАЕТ: исполнение против реала, проскальзывание, нарушения
    правил — таких данных нет; на карточке так и пишется.

ВЕДЁТСЯ: после каждого изменения серии — строка в картотека/метрики/<Имя>.jsonl
    (видно, как меняются матожидание и просадка от прогона к прогону).
Доливки (ноги) входят в деньги серии, но не в число сделок.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

RISK_PROC = 1.0          # % капитала на сделку — как в счёте места
VYBORKA_MALA = 30
NOL = 0.005

_BIRZHA = Path(__file__).resolve().parent
KART = _BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "картотека"
PAPKA = KART / "метрики"


def _ks():
    import kartoteka_sbor as _k
    return _k


def _r(rec) -> float:
    try:
        return float(rec.get("pnl_r") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _d(x) -> str:
    return str(x or "").replace("-", ".").replace("T", " ")[:10]


def _zapisi() -> list:
    """[(имя, цех, место, прогон, запись)] — сделки жителей, как у картотеки."""
    ks = _ks()
    posty = ks._posty()
    out = []
    if not ks.ZHURNAL.is_file():
        return out
    starty = {}
    prezh = getattr(ks, "_prezhniy_post", None)
    with open(ks.ZHURNAL, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            ts = str(r.get("ts") or "").replace("T", " ")[:16]
            p = posty.get(r.get("magic")) or (prezh(r.get("magic"), ts) if prezh else None)
            if not p:
                continue
            imya = ks._kto_sidel(ks._sroki(p), ts)
            if not imya:
                continue
            ceh = p["цех"]
            if ceh not in starty:
                starty[ceh] = ks._starty(ceh)
            vremena, nomera = starty[ceh]
            from bisect import bisect_right
            i = bisect_right(vremena, ts) - 1
            if i < 0:
                continue
            out.append((imya, ceh, str(p.get("слот") or ""), nomera[i], r))
    return out


def _serii(zapisi=None) -> dict:
    """{(имя, цех, место, пара, этаж): {прогоны: [...], сделки: [записи]}}."""
    gr = defaultdict(lambda: defaultdict(list))
    for imya, ceh, slot, run, r in (zapisi if zapisi is not None else _zapisi()):
        k = (imya, ceh, slot, str(r.get("symbol") or ""), str(r.get("timeframe") or ""))
        gr[k][run].append(r)
    out = {}
    for k, runs in gr.items():
        okna, vzyato, prinyaty = [], [], []
        for run in sorted(runs, reverse=True):            # свежий прогон главнее
            recs = runs[run]
            ot = min(_d(r.get("opened_at")) for r in recs)
            do = max(_d(r.get("closed_at")) for r in recs)
            svoi = [r for r in recs
                    if not any(a <= _d(r.get("opened_at")) <= b for a, b in okna)]
            if svoi:
                vzyato += svoi
                prinyaty.append(run)
            okna.append((ot, do))
        vzyato.sort(key=lambda r: (_d(r.get("closed_at")), str(r.get("ts") or "")))
        out[k] = {"прогоны": sorted(prinyaty), "сделки": vzyato}
    return out


def metriki(sdelki: list) -> dict:
    """Все показатели по списку записей журнала (по времени закрытия)."""
    osn = [r for r in sdelki if not r.get("нога") and not r.get("частичное")]
    R = [_r(r) for r in sdelki]
    n = len(osn)
    if not n:
        return {}
    itog = sum(R)
    # доливки и куски — к своей сделке: та, в чьё окно (вход…выход) они попали
    okna = [[_d(r.get("opened_at")), _d(r.get("closed_at")), _r(r)] for r in osn]
    for r in sdelki:
        if r.get("нога") or r.get("частичное"):
            d0 = _d(r.get("opened_at"))
            w = next((o for o in okna if o[0] <= d0 <= o[1]), None)
            if w is not None:
                w[2] += _r(r)
            else:
                okna.append([d0, d0, _r(r)])
    po_sdelkam = [o[2] for o in okna]
    s_r = [_r(r) for r in osn]
    win = [x for x in s_r if x > NOL]
    loss = [x for x in s_r if x < -NOL]
    vsego_plus = sum(x for x in R if x > 0)
    vsego_minus = -sum(x for x in R if x < 0)
    eq, pik, pik_d, dd, kogda_dd = 0.0, 0.0, None, 0.0, ""
    dolgo, kriv, seriya, mx_ser, nizhe = 0, [], 0, 0, False
    for r in sdelki:
        x = _r(r)
        eq += x
        d = _d(r.get("closed_at"))
        if pik_d is None:
            pik_d = d
        if eq > pik + 1e-9:
            if nizhe:
                dolgo = max(dolgo, _dney(pik_d, d))
            pik, pik_d, nizhe = eq, d, False
        elif eq < pik - 1e-9:
            nizhe = True
        if eq - pik < dd:
            dd, kogda_dd = eq - pik, d
        kriv.append([d, round(eq, 2), round(eq - pik, 2)])
        if not r.get("нога") and not r.get("частичное"):
            seriya = seriya + 1 if x < -NOL else 0
            mx_ser = max(mx_ser, seriya)
    ne_vernul = nizhe
    if ne_vernul and pik_d and kriv:
        dolgo = max(dolgo, _dney(pik_d, kriv[-1][0]))
    po_godam = defaultdict(float)
    for r in sdelki:
        po_godam[_d(r.get("closed_at"))[:4]] += _r(r)
    luchshie = sorted(po_sdelkam, reverse=True)
    mes = defaultdict(float)
    for r in sdelki:
        mes[_d(r.get("closed_at"))[:7]] += _r(r) * RISK_PROC
    mesyacy = _mesyacy(min(mes), max(mes)) if mes else []
    ryad = [mes.get(m, 0.0) for m in mesyacy]
    sharpe = sortino = None
    if len(ryad) >= 6:
        sr = sum(ryad) / len(ryad)
        sd = math.sqrt(sum((x - sr) ** 2 for x in ryad) / len(ryad))
        dn = math.sqrt(sum(min(0.0, x) ** 2 for x in ryad) / len(ryad))
        sharpe = round(sr / sd * math.sqrt(12), 2) if sd > 0 else None
        sortino = round(sr / dn * math.sqrt(12), 2) if dn > 0 else None
    gody = sorted(po_godam)
    return {
        "сделок": n, "итог_R": round(itog, 2), "итог_проц": round(itog * RISK_PROC, 1),
        "лет": (f"{gody[0]}–{gody[-1]}" if len(gody) > 1 else gody[0]) if gody else "",
        "матожидание": round(itog / n, 2),
        "прибыльных": round(len(win) / n * 100), "в_плюс": len(win), "в_минус": len(loss),
        "ср_выигрыш": round(sum(win) / len(win), 2) if win else None,
        "ср_убыток": round(sum(loss) / len(loss), 2) if loss else None,
        "PF": round(vsego_plus / vsego_minus, 2) if vsego_minus > 0 else None,
        "просадка_R": round(dd, 2), "просадка_когда": kogda_dd,
        "возврат_дней": dolgo, "не_вернул": ne_vernul,
        "серия_убытков": mx_ser, "худшая": round(min(s_r), 2),
        "без_3_лучших": round(itog - sum(luchshie[:3]), 2),
        "sharpe": sharpe, "sortino": sortino,
        "по_годам": [[g, round(po_godam[g], 2)] for g in gody],
        "кривая": kriv,
        "выборка_мала": n < VYBORKA_MALA,
    }


def _dney(a, b) -> int:
    try:
        return (datetime.strptime(b, "%Y.%m.%d") - datetime.strptime(a, "%Y.%m.%d")).days
    except Exception:
        return 0


def _mesyacy(a, b) -> list:
    try:
        y, m = int(a[:4]), int(a[5:7])
        y2, m2 = int(b[:4]), int(b[5:7])
    except Exception:
        return []
    out = []
    while (y, m) <= (y2, m2):
        out.append(f"{y}.{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def _imya_serii(k, m) -> str:
    imya, ceh, slot, sym, tf = k
    return f"{slot} · {sym} {tf} · {m.get('лет', '')}".strip(" ·")


def _vesti(imya, k, m, runs):
    """Строка в картотека/метрики/<Имя>.jsonl — только если серия изменилась."""
    try:
        PAPKA.mkdir(parents=True, exist_ok=True)
        f = PAPKA / f"{imya}.jsonl"
        kl = "|".join(k[1:])
        posl = None
        if f.is_file():
            for ln in f.read_text(encoding="utf-8").splitlines():
                try:
                    z = json.loads(ln)
                except Exception:
                    continue
                if z.get("серия") == kl:
                    posl = z
        sut = {x: m.get(x) for x in ("сделок", "итог_R", "матожидание", "PF", "просадка_R",
                                     "без_3_лучших", "прибыльных", "sharpe", "sortino", "лет")}
        if posl and all(posl.get(x) == v for x, v in sut.items()):
            return
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict({"когда": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                      "серия": kl, "прогон": runs[-1] if runs else ""}, **sut),
                                ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[МЕТРИКИ] не записалось ({e})")


def _istoriya(imya, k) -> list:
    f = PAPKA / f"{imya}.jsonl"
    kl = "|".join(k[1:])
    out = []
    try:
        for ln in f.read_text(encoding="utf-8").splitlines():
            z = json.loads(ln)
            if z.get("серия") == kl:
                out.append([z.get("когда"), z.get("матожидание"), z.get("итог_R")])
    except Exception:
        pass
    return out


def po_zhitelyam(vesti: bool = True) -> dict:
    """{имя: [серия, …]} — свежая серия первой. Серия: {имя, ключ, прогоны, метрики, история}."""
    out = defaultdict(list)
    for k, s in _serii().items():
        m = metriki(s["сделки"])
        if not m:
            continue
        if vesti:
            _vesti(k[0], k, m, s["прогоны"])
        posl_ts = max(str(r.get("ts") or "") for r in s["сделки"])
        out[k[0]].append({"имя": _imya_serii(k, m), "цех": k[1], "место": k[2],
                          "пара": f"{k[3]} {k[4]}".strip(), "прогоны": s["прогоны"],
                          "м": m, "история": _istoriya(k[0], k), "_ts": posl_ts})
    for v in out.values():
        v.sort(key=lambda x: x["_ts"], reverse=True)
    return dict(out)


def svodka_sverhu(dannye: dict) -> list:
    """Кратко для общей страницы: по серии на строку, сгруппировано по месту."""
    rows = []
    for imya, serii in dannye.items():
        for s in serii:
            m = s["м"]
            rows.append({"кто": imya, "серия": s["имя"], "место": s["место"],
                         "сделок": m["сделок"], "R": m["итог_R"], "E": m["матожидание"],
                         "PF": m["PF"], "DD": m["просадка_R"], "b3": m["без_3_лучших"],
                         "мала": m["выборка_мала"]})
    rows.sort(key=lambda x: (x["место"], -x["R"]))
    return rows


def dlya_arhivariusa(ceh: str, slot: str, run: str) -> list:
    """Строки фактов для Арчи: серия этого прогона — до него и после."""
    zap = _zapisi()
    nashi = [z for z in zap if z[1] == ceh and z[2].upper() == str(slot).upper() and z[3] == run]
    if not nashi:
        return []
    imya = nashi[0][0]
    sym = str(nashi[0][4].get("symbol") or "")
    tf = str(nashi[0][4].get("timeframe") or "")
    k = (imya, ceh, nashi[0][2], sym, tf)
    s_posle = _serii(zap).get(k)
    s_do = _serii([z for z in zap if z[3] != run]).get(k)
    if not s_posle:
        return []
    mp = metriki(s_posle["сделки"])
    out = [f"серия {_imya_serii(k, mp)} после этого прогона: сделок {mp['сделок']}, итог "
           f"{mp['итог_R']:+g}R, матожидание {mp['матожидание']:+g}R, Profit Factor "
           f"{mp['PF'] if mp['PF'] is not None else '—'}, просадка {mp['просадка_R']:g}R, "
           f"без трёх лучших сделок {mp['без_3_лучших']:+g}R, прибыльных {mp['прибыльных']}%"]
    if mp["выборка_мала"]:
        out.append(f"выборка серии мала: {mp['сделок']} сделок, для уверенного вывода нужно "
                   f"не меньше {VYBORKA_MALA}")
    if s_do and s_do["сделки"]:
        md = metriki(s_do["сделки"])
        if md:
            out.append(f"та же серия до этого прогона: сделок {md['сделок']}, итог "
                       f"{md['итог_R']:+g}R, матожидание {md['матожидание']:+g}R, Profit Factor "
                       f"{md['PF'] if md['PF'] is not None else '—'}, просадка "
                       f"{md['просадка_R']:g}R, без трёх лучших {md['без_3_лучших']:+g}R")
    else:
        out.append("до этого прогона серии на этом месте у жителя не было")
    return out


# METRIKI_INVESTORA_V1 - marker
