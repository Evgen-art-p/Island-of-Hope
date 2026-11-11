# -*- coding: utf-8 -*-
# VEDENIE_SDELKI_V1 — сделка A08 после входа: город показывает, житель решает и обосновывает
"""
СЛОВО ШЕФА 17.10
    «Город показывает, житель решает и обосновывает каждое решение. Задача —
    сохранить и приумножить прибыль, инструментов полно, входить умеет.»
    «Ордера вокруг разворотника как сейчас не трогай» — заявка и стоп на
    входе прежние. Здесь только то, что ПОСЛЕ входа.

ЧТО ЗДЕСЬ
    blok()        — факты по открытой сделке в задание на баре: прибыль сейчас,
                    лучшее место и сколько от него отдано, где стоп и чем он
                    кончится, противоположные фракталы на рабочем и младшем
                    этаже, доливка по канону, старший этаж (Аллигатор и AO),
                    как исполнитель понимает его руки. Без советов.
    obosnovanie() — рука приказа в сделке: решение без обоснования не
                    принимается; стоп в слабую сторону и долив не в плюсе —
                    сразу ответ фактом (исполнитель их всё равно не примет).
                    Каждое принятое решение — в журнал ведения.
    otchet()      — раздел отчёта: лучшее место сделки, выход, сколько отдано,
                    решения в сделке его словами.

    Город не торгует: ничего не двигает, не доливает и не закрывает за жителя.
    Смотрит только назад — бары не позже текущего бара города.
"""
from __future__ import annotations

import json
import sys as _sys
from datetime import datetime
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))
_KOREN = _BIRZHA.parent

SLOTY = ("A08",)
V_SDELKE = ("HOLD", "MOVE_STOP", "ADD", "CLOSE")
POCHEMU_MIN = 40          # знаков в «почему» — не отписка
DALSHE_MIN = 15           # знаков в «дальше»
RESHENIY_HRANIM = 400
PROGONOV_HRANIM = 40


def _nash(slot) -> bool:
    # MESTA_PO_POMETKE_V1: место уровня «продвинутый новичок» — по пометке в паспорте цеха
    try:
        import mesto_urovnya as _md
        return _md.eto_mesto_urovnya(slot)
    except Exception:
        return str(slot or "").strip().upper() in SLOTY


def _ceh(slot) -> str:
    """MESTA_PO_POMETKE_V1: цех, где стоит место (не всегда торговый_хаос)."""
    try:
        import mesto_urovnya as _md
        return _md.ceh_mesta(slot)
    except Exception:
        return "торговый_хаос"


def _nomer(slot):
    """MESTA_PO_POMETKE_V1: номер счёта места — в его цехе."""
    try:
        import mesto_urovnya as _md
        return _md.nomer_mesta(slot)
    except Exception:
        return {"A06": 100001, "A07": 100002, "A08": 100003}.get(
            str(slot or "").strip().upper())


def _hm():
    import hod_mesyaca as _h
    return _h


def _t16(x) -> str:
    return str(x or "")[:16]


# ── журнал ведения ───────────────────────────────────────────────
def _put(slot) -> Path:
    return (_KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха" / _ceh(slot)
            / "слоты" / str(slot).strip().upper() / "данные" / "ведение.json")


def _chitat(slot) -> dict:
    p = _put(slot)
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception as e:
        # не затираем молча: битый файл — в сторону, рядом
        try:
            kuda = p.with_name(p.name + ".сломан_"
                               + datetime.now().strftime("%Y%m%d_%H%M%S"))
            p.replace(kuda)
            print(f"[ВЕДЕНИЕ] журнал ведения не читался ({e}) — отложен: {kuda.name}")
        except Exception:
            print(f"[ВЕДЕНИЕ] журнал ведения не читается ({e})")
        return {}


def _pisat(slot, d: dict) -> None:
    p = _put(slot)
    try:
        pr = d.get("прогоны") or {}
        while len(pr) > PROGONOV_HRANIM:
            pr.pop(next(iter(pr)))
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
    except Exception as e:
        print(f"[ВЕДЕНИЕ] журнал ведения не записался ({e})")


# ── позиция и числа ──────────────────────────────────────────────
def _magic(slot):
    return _nomer(slot)   # MESTA_PO_POMETKE_V1: номер — в цехе места


def _pozicii(slot, symbol):
    """(основная, ноги) открытой сделки. Тень города, куски и доливки города
    — не его. Нет сделки — (None, [])."""
    moy = _magic(slot)
    sym = str(symbol or "").strip().upper()
    osn, nogi = None, []
    for p in (_hm()._sostoyanie().get("positions") or []):
        if str(p.get("status") or "").upper() != "OPEN" or p.get("manual_close"):
            continue
        if str(p.get("symbol") or "").strip().upper() != sym:
            continue
        if p.get("тень") or p.get("доливка_города") or p.get("_частичное"):
            continue
        if moy is not None and p.get("magic") != moy:
            continue
        if _pole_mesta(p, "нога_места"):
            nogi.append(p)
        elif osn is None:
            osn = p
    return osn, nogi


def _punkt(cena) -> float:
    c = abs(float(cena or 0))
    return 0.01 if c >= 500 else (0.001 if c >= 20 else 0.00001)


def _f(cena) -> str:
    """Цена с числом знаков по её пункту: 1.33421, 151.234, 2034.56."""
    try:
        pt = _punkt(cena)
        z = 5 if pt < 0.0001 else (3 if pt < 0.01 else 2)
        return f"{float(cena):.{z}f}"
    except (TypeError, ValueError):
        return str(cena)


def _bary_do(symbol, tf, do_bara) -> list:
    b = _hm()._bary(symbol, tf) or []
    g = _t16(do_bara)
    return [x for x in b if _t16(x.get("date")) <= g] if g else list(b)


def _cifry(p, symbol, bar) -> dict:
    """Сделка в R от исходного риска: сейчас, лучшее место, когда."""
    long_ = str(p.get("direction") or "").upper() == "LONG"
    sg = 1 if long_ else -1
    e = float(p["entry"])
    s0 = p.get("stop_initial", p.get("stop"))
    r0 = abs(e - float(s0)) if s0 is not None else 0.0
    if r0 <= 0:
        return {}
    tf = str(p.get("timeframe") or "H4").upper()
    b = _bary_do(symbol, tf, bar)
    if not b:
        return {}
    ot = _t16(p.get("opened_at"))
    v_sd = [x for x in b if _t16(x.get("date")) >= ot] if ot else []
    c = float(b[-1]["close"])

    def R(cena):
        return sg * (float(cena) - e) / r0

    r_now, r_max, kogda = R(c), R(c), ""
    if v_sd:
        luch = (max(v_sd, key=lambda x: x["high"]) if long_
                else min(v_sd, key=lambda x: x["low"]))
        r_l = R(luch["high"] if long_ else luch["low"])
        if r_l > r_max:
            r_max, kogda = r_l, _t16(luch.get("date"))
    return {"long": long_, "sg": sg, "e": e, "r0": r0, "tf": tf, "b": b,
            "c": c, "c_bar": _t16(b[-1].get("date")), "R": R,
            "r_now": r_now, "r_max": r_max, "kogda": kogda, "ot": ot}


def _fraktal_protiv(b, long_):
    """Последний подтверждённый противоположный фрактал: для LONG — нижний,
    для SHORT — верхний (средний бар ниже/выше двух слева и двух справа)."""
    b = b[-200:]
    for i in range(len(b) - 3, 1, -1):
        if long_:
            if all(b[i]["low"] < b[i + d]["low"] for d in (-2, -1, 1, 2)):
                return b[i]["low"], _t16(b[i].get("date"))
        else:
            if all(b[i]["high"] > b[i + d]["high"] for d in (-2, -1, 1, 2)):
                return b[i]["high"], _t16(b[i].get("date"))
    return None, ""


# ── старший этаж: Аллигатор и AO ─────────────────────────────────
def _smma(x, n):
    out = [None] * len(x)
    if len(x) < n:
        return out
    s = sum(x[:n]) / n
    out[n - 1] = s
    for i in range(n, len(x)):
        s = (s * (n - 1) + x[i]) / n
        out[i] = s
    return out


def _alligator(b):
    med = [(x["high"] + x["low"]) / 2 for x in b]

    def sdvig(a, k):
        return [None] * k + a[:-k]

    return (sdvig(_smma(med, 13), 8), sdvig(_smma(med, 8), 5),
            sdvig(_smma(med, 5), 3))


def _ao(b):
    try:
        from williams_core import compute_ao_series
        return compute_ao_series([x["high"] for x in b], [x["low"] for x in b])
    except Exception:
        med = [(x["high"] + x["low"]) / 2 for x in b]
        out = [None] * len(b)
        for i in range(33, len(b)):
            out[i] = sum(med[i - 4:i + 1]) / 5 - sum(med[i - 33:i + 1]) / 34
        return out


def starshiy_fakty(symbol, tf, bar) -> str:
    h = _hm()
    e = h.starshiy(tf)
    if not e:
        return ""
    sv = str(h._svecha_mesyaca(symbol, tf, bar) or "")[:10]
    if not sv:   # без закрытой свечи не смотрим: иначе заглянем вперёд
        return f"Старший этаж ({e}): последняя закрытая свеча не определилась — не посчитать."
    b = [x for x in (h._bary(symbol, e) or []) if str(x.get("date") or "")[:10] <= sv]
    if len(b) < 40:
        return f"Старший этаж ({e}): свечей мало — не посчитать."
    jaw, teeth, lips = _alligator(b)
    ao = _ao(b)
    n = len(b)
    pt = _punkt(b[-1]["close"])
    if any(v is None for v in (jaw[-3], teeth[-3], lips[-3], ao[-1], ao[-2])):
        return f"Старший этаж ({e}): линии ещё не считаются — не посчитать."

    def mesto(i):
        c = b[i]["close"]
        ls = (jaw[i], teeth[i], lips[i])
        m = ("над линиями" if c > max(ls) else
             ("под линиями" if c < min(ls) else "между линиями"))
        return m, (c - teeth[i]) / pt

    m0, d0 = mesto(n - 1)
    _m1, d1 = mesto(n - 2)
    _m2, d2 = mesto(n - 3)
    if m0 == "между линиями":
        dv = "в самих линиях"
    else:
        raz = abs(d0) - abs(d2)
        if abs(raz) < 0.1 * max(abs(d2), 1.0):
            dv = "идёт вдоль линий"
        else:
            dv = "уходит от линий" if raz > 0 else "идёт к линиям"
    a0, a1 = ao[-1], ao[-2]
    cvet = "растёт (зелёный)" if a0 > a1 else "падает (красный)"
    znak = "выше нуля" if a0 > 0 else "ниже нуля"
    nol = "через ноль за 8 свечей не переходил"
    for k in range(0, 8):
        x, y = ao[n - 1 - k], ao[n - 2 - k]
        if x is None or y is None:
            break
        if (x > 0) != (y > 0):
            nol = (f"через ноль {'вверх' if x > 0 else 'вниз'} — "
                   + ("на последней свече" if k == 0 else f"{k} св. назад")
                   + f" ({str(b[n - 1 - k].get('date'))[:10]})")
            break
    im = h.imya(e)
    return (f"Старший этаж — {e} ({im}), последняя закрытая свеча {sv}: цена {m0}; "
            f"от зубов (красная линия) по трём последним свечам: {d2:+.0f} → {d1:+.0f} → "
            f"{d0:+.0f} пунктов — {dv}. AO {a0:+.5f}, {cvet}, {znak}; {nol}.\n"
            "Канон (слово Шефа 05.10): от линий или вдоль них — импульс, к линиям — "
            "откат. Что это значит для твоей сделки — решаешь ты.")


def _doliv_kanon(symbol, tf, long_) -> str:
    try:
        import volny_ao as _va
        ot = _va.schet_hoda(symbol, tf, long_)
        v = str((ot or {}).get("volna") or "")
        if v in ("первая", "вторая", "третья"):
            return (f"ход в твою сторону по счёту города — {v}: по канону доливать "
                    "можно, пока не прошла четвёртая.")
        if v == "четвёртая" or v.startswith(("пятая", "после пятой")):
            return (f"ход в твою сторону по счёту города — {v.split(',')[0]}: после "
                    "четвёртой по канону не доливают.")
        return "волна хода в твою сторону у города не определилась — считай сам."
    except Exception as e:
        return f"счёт волн не вышел ({e})."


# ── задание на баре ──────────────────────────────────────────────
def blok(slot, symbol, napr=None, bar=None) -> str:
    if not _nash(slot):
        return ""
    try:
        return _blok(slot, symbol, bar)
    except Exception as e:
        print(f"[ВЕДЕНИЕ] факты сделки не собрались ({e})")
        return ""


def _blok(slot, symbol, bar) -> str:
    h = _hm()
    p, nogi = _pozicii(slot, symbol)
    if not p:
        return ""
    bar = bar or h._bar_seychas()
    f = _cifry(p, symbol, bar)
    if not f:
        return ""
    long_, R, tf = f["long"], f["R"], f["tf"]
    stop = float(p.get("stop"))
    L = ["=== ТВОЯ СДЕЛКА — ФАКТЫ ГОРОДА (решаешь ты) ===",
         f"{'LONG' if long_ else 'SHORT'} {symbol} {tf}: вход {_f(f['e'])} "
         f"({f['ot'] or '—'}), исходный риск {f['r0'] / _punkt(f['e']):.0f} пунктов = 1R.",
         f"Сейчас (закрытие {f['c_bar']}: {_f(f['c'])}): {f['r_now']:+.2f}R. "
         f"Лучшее место за сделку: {f['r_max']:+.2f}R"
         + (f" ({f['kogda']})" if f["kogda"] else "")
         + f"; от него отдано {max(0.0, f['r_max'] - f['r_now']):.2f}R.",
         f"Стоп сейчас {_f(stop)}: выбьет — основная позиция закроется на {R(stop):+.2f}R."]
    dola = float(p.get("доля") or 1.0)
    if dola < 0.999:
        L.append(f"Основная позиция открыта долей {dola:g} — часть уже закрыта.")
    if nogi:
        dl = sum(float(x.get("доля") or 0) for x in nogi)
        L.append(f"Доливок открыто: {len(nogi)}, вместе {dl:g} исходной позиции.")
    etazhi = [tf]
    try:
        import volny_ao as _va
        if _va.NIZHE.get(tf):
            etazhi.append(_va.NIZHE[tf])
    except Exception:
        pass
    for et in etazhi:
        bb = f["b"] if et == tf else _bary_do(symbol, et, bar)
        fc, fd = _fraktal_protiv(bb, long_)
        if fc is None:
            L.append(f"Противоположный фрактал на {et}: не нашёл.")
            continue
        za_cenoy = (fc >= f["c"]) if long_ else (fc <= f["c"])
        tuzhe = (fc > stop) if long_ else (fc < stop)
        hv = ("; цена уже за ним — стоп туда не поставить" if za_cenoy else
              ("" if tuzhe else "; он не туже твоего стопа"))
        L.append(f"Последний противоположный фрактал на {et}: {_f(fc)} ({fd}) — стоп за "
                 f"ним дал бы {R(fc):+.2f}R{hv}.")
    L += _hody_blok(symbol, tf, f, bar)   # PROVOZHAYU_V1: ход сделки по фракталам
    L.append("Доливка: " + _doliv_kanon(symbol, tf, long_))
    sf = starshiy_fakty(symbol, tf, bar)
    if sf:
        L.append(sf)
    L.append("Как исполнитель понимает твои руки: MOVE_STOP — только в защитную "
             "сторону, ослабить нельзя; CLOSE с полем «доля» — закрыть часть исходной "
             "позиции (0.5 — половину), без доли — всё; ADD («долить» — доля исходной, "
             "например 0.5) — по закрытию бара, только в плюсе, каждая следующая не "
             "больше прошлой, худший исход сделки по стопу не хуже −1R; «новый_стоп» в "
             "том же приказе подтянет стоп.")
    L.append("Задача — сохранить и приумножить прибыль. Реши на этом баре: HOLD, "
             "MOVE_STOP, CLOSE (всё или долю) или ADD. В «почему» — на какие факты "
             "опираешься; в «дальше» — что должно случиться, чтобы ты сделал следующий "
             "шаг (подтянул стоп, закрыл, долил). Без обоснования рука решение в сделке "
             "не примет.")
    L.append(PROVOZHAYU_TEKST)   # PROVOZHAYU_V1
    L += _marshrut_blok(slot, symbol, p, bar, tf)   # VEDENIE_PO_MARSHRUTU_V1
    return "\n".join(L) + "\n\n"


# ── рука приказа в сделке ────────────────────────────────────────
def obosnovanie(slot, symbol, tf, chto, args) -> str:
    """Пусто — приказ идёт дальше; иначе текст отказа руки (фактом)."""
    if not _nash(slot):
        return ""
    chto = str(chto or "").upper().strip()
    if chto not in V_SDELKE:
        return ""
    try:
        p, _nogi = _pozicii(slot, symbol)
    except Exception as e:
        print(f"[ВЕДЕНИЕ] позиция не нашлась ({e}) — приказ идёт как есть")
        return ""
    if not p:
        return ""        # сделки нет — рука ответит, как раньше
    a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
    _otkaz_m = _marshrut_proverka(slot, symbol, tf, chto, a, p)   # VEDENIE_PO_MARSHRUTU_V1
    if _otkaz_m:
        return _otkaz_m
    poch = str(a.get("почему") or "").strip()
    dalshe = (str(a.get("дальше") or "").strip()
              or str(a.get("ожидание") or "").strip())
    try:
        dolya = float(a.get("доля") or 1.0)
    except (TypeError, ValueError):
        dolya = 1.0
    vsyo = chto == "CLOSE" and dolya >= 0.999
    net = []
    if len(poch) < POCHEMU_MIN:
        net.append("«почему» — на какие факты опираешься")
    if not vsyo and len(dalshe) < DALSHE_MIN:
        net.append("«дальше» — что должно случиться, чтобы ты сделал следующий шаг")
    if net:
        print(f"[ВЕДЕНИЕ] ✗ {slot} {chto}: без обоснования — {'; '.join(net)}")
        return ("Приказ НЕ отдан: решение в сделке — с обоснованием. Не хватает: "
                + "; ".join(net) + ". Факты — в блоке «Твоя сделка». Назови и позови "
                "снова.")
    h = _hm()
    bar = h._bar_seychas()
    f = {}
    try:
        f = _cifry(p, symbol, bar)
    except Exception as e:
        print(f"[ВЕДЕНИЕ] числа сделки не посчитались ({e})")
    long_ = str(p.get("direction") or "").upper() == "LONG"
    stop = p.get("stop")
    ns = a.get("новый_стоп")
    if isinstance(ns, (int, float)) and ns and chto in ("MOVE_STOP", "ADD") \
            and isinstance(stop, (int, float)):
        if (ns < stop) if long_ else (ns > stop):
            print(f"[ВЕДЕНИЕ] ✗ {slot} {chto}: стоп {ns} слабее нынешнего {stop}")
            return (f"Приказ НЕ отдан: стоп {_f(ns)} слабее нынешнего {_f(stop)} — исполнитель "
                    "двигает стоп только в защитную сторону.")
        c = f.get("c")
        if c is not None and ((ns >= c) if long_ else (ns <= c)):
            print(f"[ВЕДЕНИЕ] ✗ {slot} {chto}: стоп {ns} за ценой {c}")
            return (f"Приказ НЕ отдан: стоп {_f(ns)} по ту сторону цены ({_f(c)}) — он "
                    "сработал бы сразу.")
    if chto == "ADD" and f and f.get("r_now", 0) <= 0:
        print(f"[ВЕДЕНИЕ] ✗ {slot} ADD: сделка не в плюсе ({f['r_now']:+.2f}R)")
        return (f"Приказ НЕ отдан: сделка сейчас {f['r_now']:+.2f}R — исполнитель "
                "доливает только в плюсе.")
    try:
        d = _chitat(slot)
        pr_id = h._progon()
        d["последний_прогон"] = pr_id
        ya = d.setdefault("прогоны", {}).setdefault(pr_id, {})
        ya["решения"] = (ya.get("решения") or [])[-(RESHENIY_HRANIM - 1):] + [{
            "бар": bar, "символ": str(symbol).upper(),
            "сделка": f"{_t16(p.get('opened_at'))}|{p.get('entry')}",
            "сторона": "LONG" if long_ else "SHORT", "что": chto,
            "доля": (dolya if chto == "CLOSE" else None),
            "новый_стоп": ns if isinstance(ns, (int, float)) and ns else None,
            "долить": a.get("долить") if chto == "ADD" else None,
            "почему": poch[:1200], "дальше": dalshe[:600],
            "провожаю": (str(a.get("провожаю") or "").strip()[:1000]   # PROVOZHAYU_V1
                         or None),
            "этап": str(a.get("этап") or "").strip()[:400] or None,   # VEDENIE_PO_ZAPISKE_V2: его слова
            "на_младшем": str(a.get("на_младшем") or "").strip()[:1200] or None,
            "первая_волна": str(a.get("первая_волна") or "").strip()[:600] or None,
            "на_рабочем": str(a.get("на_рабочем") or "").strip()[:600] or None,
            "форма_волны": str(a.get("форма_волны") or "").strip()[:400] or None,
            "настроение": str(a.get("настроение") or "").strip()[:600] or None,   # NASTROENIE_SDELKI_V1
            "место": str(a.get("место") or "").strip()[:600] or None,   # VEDENIE_PROSTO_V1
            "место_входа": _scenariy(slot, symbol, "LONG" if long_ else "SHORT"),
            "R_сейчас": round(f["r_now"], 2) if f else None,
            "R_лучшее": round(f["r_max"], 2) if f else None}]
        _pisat(slot, d)
        print(f"[ВЕДЕНИЕ] ✓ {slot} {chto} на {bar}: "
              + (f"{f['r_now']:+.2f}R, лучшее {f['r_max']:+.2f}R" if f else "чисел нет"))
    except Exception as e:
        print(f"[ВЕДЕНИЕ] решение в журнал не легло ({e}) — приказ идёт как есть")
    return ""


# ── отчёт ────────────────────────────────────────────────────────
def otchet(sloty) -> list:
    s = []
    for slot in sloty or []:
        if not _nash(slot):
            continue
        try:
            s += _otchet_slota(slot)
        except Exception as e:
            s += [f"(раздел ведения не собрался: {e})", ""]
    return s


def _otchet_slota(slot) -> list:
    h = _hm()
    hm = h._chitat(slot)
    hpr = h._progon()
    if hpr not in (hm.get("прогоны") or {}):
        hpr = hm.get("последний_прогон")
    d = _chitat(slot)
    vpr = hpr if hpr in (d.get("прогоны") or {}) else d.get("последний_прогон")
    resh = ((d.get("прогоны") or {}).get(vpr) or {}).get("решения") or []
    moy = _magic(slot)
    try:   # ZAKRYTIYA_PROGONA_V1: только сделки этого прогона
        h._PROGON_OTCHETA["id"] = str(hpr or "")
    except Exception:
        pass
    zak = h._zhurnaly_zakrytiy()
    s = ["## Ведение сделок — сохранил и приумножил?", "",
         "Город решения не судит — он мерит: где было лучшее место сделки и где вышел. "
         "«Отдал» — разница. R — от исходного риска, по цене основной позиции; куски "
         "и доливки — в «Книге места».", ""]
    vsego = []
    for sym, yh in (((hm.get("прогоны") or {}).get(hpr)) or {}).items():
        vh = [v for v in (yh.get("входы") or []) if v.get("что") == "ENTER"]
        if not vh:
            continue
        ot = _t16(vh[0].get("бар"))
        glav = [z for z in zak
                if z.get("magic") == moy and not z.get("нога") and not z.get("частичное")
                and not z.get("тень")
                and str(z.get("symbol") or sym).upper() == str(sym).upper()
                and _t16(z.get("opened_at") or z.get("closed_at")) >= ot]
        glav.sort(key=lambda z: str(z.get("opened_at") or ""))
        if not glav:
            continue
        s += [f"**{slot} · {sym}**", "",
              "| вход | сторона | лучшее было | вышел | отдал | чем закрыто | частями | "
              "решения в сделке |", "|---|---|---|---|---|---|---|---|"]
        for z in glav:
            row = _stroka(h, z, sym, resh, zak, moy)
            if row:
                s.append(row[0])
                vsego.append(row[1])
        s.append("")
    vsego = [x for x in vsego if x[0] is not None and x[1] is not None]
    if vsego:
        lb = sum(x[0] for x in vsego)
        vy = sum(x[1] for x in vsego)
        s.append(f"Сумма лучших мест: **{lb:+.2f}R** · сумма выходов: **{vy:+.2f}R** · "
                 f"отдано от лучшего: **{lb - vy:.2f}R** (сделок: {len(vsego)}).")
        s.append("")
    ne_hold = [r for r in resh if r.get("что") != "HOLD"]
    if resh:
        s.append(f"Решений в сделке с обоснованием: **{len(resh)}** (HOLD — "
                 f"{len(resh) - len(ne_hold)}, остальное — {len(ne_hold)}).")
        s.append("")
    if ne_hold:
        s += ["Решения, кроме HOLD — его словами:", "",
              "| бар | что | R тогда | лучшее тогда | почему | дальше |",
              "|---|---|---|---|---|---|"]
        for r in ne_hold[-15:]:
            chto = r.get("что")
            if chto == "CLOSE" and (r.get("доля") or 1) < 0.999:
                chto = f"CLOSE {r.get('доля'):g}"
            elif chto == "MOVE_STOP" and r.get("новый_стоп"):
                chto = f"MOVE_STOP → {r['новый_стоп']}"
            elif chto == "ADD":
                chto = f"ADD {r.get('долить')}"
            s.append(f"| {r.get('бар')} | {chto} | {r.get('R_сейчас')} | "
                     f"{r.get('R_лучшее')} | {_kl(r.get('почему'), 220)} | "
                     f"{_kl(r.get('дальше'), 160)} |")
        s.append("")
    if resh:   # PROVOZHAYU_V1
        s += _provozhal_otchet(h, resh, zak, moy)
        s += _marshrut_otchet(resh)   # VEDENIE_PO_MARSHRUTU_V1
    return s if len(s) > 5 else []


def _kl(t, n) -> str:
    t = " ".join(str(t or "").split()).replace("|", "/")
    return t if len(t) <= n else t[:n - 1] + "…"


def _stroka(h, z, sym, resh, zak, moy):
    try:
        e, x = float(z.get("entry")), float(z.get("exit"))
    except (TypeError, ValueError):
        return None
    st = h.storona_sdelki(z)
    long_ = st == "LONG"
    sg = 1 if long_ else -1
    r_vy = z.get("R_половины")
    if r_vy is None:
        try:
            r_vy = float(z.get("pnl_r")) / float(z.get("доля") or 1.0)
        except (TypeError, ValueError, ZeroDivisionError):
            r_vy = None
    r0 = abs(x - e) / abs(float(r_vy)) if r_vy not in (None, 0) else None
    ot, do = _t16(z.get("opened_at")), _t16(z.get("closed_at"))
    tf = str(z.get("timeframe") or "H4").upper()
    r_lb = None
    if r0:
        b = [y for y in (h._bary(sym, tf) or []) if ot <= _t16(y.get("date")) <= do]
        if b:
            kr = max(y["high"] for y in b) if long_ else min(y["low"] for y in b)
            r_lb = max(sg * (kr - e) / r0, float(r_vy))
    kusky = sum(1 for y in zak if y.get("magic") == moy and y.get("частичное")
                and _t16(y.get("opened_at")) == ot)
    moi = [r for r in resh if str(r.get("сделка") or "").startswith(ot + "|")]
    sch = {}
    for r in moi:
        sch[r.get("что")] = sch.get(r.get("что"), 0) + 1
    tx = " · ".join(f"{k} {v}" for k, v in sorted(sch.items())) or "—"
    otd = (r_lb - float(r_vy)) if (r_lb is not None and r_vy is not None) else None
    pr = {"STOP_LOSS": "стоп", "MANUAL": "сам", "MANUAL_CLOSE": "сам"}.get(str(z.get("close_reason")), str(z.get("close_reason") or "—"))
    row = (f"| {ot} | {st} | " + (f"{r_lb:+.2f}R" if r_lb is not None else "—")
           + " | " + (f"{float(r_vy):+.2f}R" if r_vy is not None else "—")
           + " | " + (f"{otd:.2f}R" if otd is not None else "—")
           + f" | {pr} | {kusky or '—'} | {tx} |")
    return row, (r_lb, float(r_vy) if r_vy is not None else None)


# VEDENIE_SDELKI_V1 - marker

# ZAKRYTIYA_PROGONA_V1 - marker


# ══ PROVOZHAYU_V1 — в сделке провожает ход (только слова) ══════════
# Код размечает ход сделки по фракталам этажа ниже рабочего; житель
# называет роль хода и говорит, сколько ему ещё идти. На решения и деньги
# не влияет. Смотрит только назад — бары не позже текущего бара города.
_NIZHE_ZAPAS = {"MN1": "W1", "W1": "D1", "D1": "H4", "H4": "H1", "H1": "M15"}
HODOV_POKAZYVAEM = 8

PROVOZHAYU_TEKST = (
    "=== ПРОВОЖАЮ ХОД (только слова: на решение и деньги не влияет) ===\n"
    "Ты в сделке — думай не о входе, а о том, сколько ход ещё пройдёт. В том же "
    "приказе (HOLD, MOVE_STOP, ADD или CLOSE) в поле «провожаю» скажи своими "
    "словами:\n"
    "  · что это за ход: ты вошёл в откат против старшего хода или по старшему "
    "ходу — как сделка помечена при входе, пометку не переписывай;\n"
    "  · где он сейчас: первая, третья (горб AO растёт), четвёртая в своём "
    "масштабе, пятая — или не знаю;\n"
    "  · есть ли в конце дивер;\n"
    "  · сколько ему ещё идти и что скажет тебе, что он кончился.\n"
    "Вошёл в откат — провожай сам откат: где он кончится, дивер на младшем. "
    "Вошёл по старшему ходу — провожай новый ход: сложилась ли первая волна, "
    "идёт ли третья, дошло ли до импульса.\n"
    "Опоры хода — в «Ход сделки по фракталам» выше. Решай, как решал; город "
    "потом поставит твои слова рядом с тем, что рынок сделал дальше.")


def polya_shemy() -> dict:
    """Поле руки приказа — для мозга места (одна дверь)."""
    return {"провожаю": {"type": "string", "description": (
        "в сделке, только слова — на решение не влияет: провожаешь ход — что "
        "это за ход (откат или по старшему), где он сейчас (первая, третья, "
        "четвёртая, пятая), дивер в конце, сколько ещё идти и что скажет, "
        "что кончился")}}


def _etazh_nizhe(tf) -> str:
    try:
        import volny_ao as _va
        e = _va.NIZHE.get(tf)
        if e:
            return e
    except Exception:
        pass
    return _NIZHE_ZAPAS.get(str(tf or "").upper(), "")


def _fraktaly(b, s, e) -> list:
    """Подтверждённые фракталы в b[s:e]: у бара справа закрылись два бара."""
    out = []
    for i in range(max(2, s), min(len(b) - 2, e)):
        if all(b[i]["high"] > b[i + d]["high"] for d in (-2, -1, 1, 2)):
            out.append((i, "верх", b[i]["high"]))
        if all(b[i]["low"] < b[i + d]["low"] for d in (-2, -1, 1, 2)):
            out.append((i, "низ", b[i]["low"]))
    return out


def _opory(b, long_, i0) -> list:
    """Край у входа + чередующиеся подтверждённые фракталы после него."""
    lo = max(0, i0 - 12)
    idx = list(range(lo, min(i0, len(b) - 1) + 1)) or [len(b) - 1]
    if long_:
        j = min(idx, key=lambda k: b[k]["low"])
        tochki = [(j, "низ", b[j]["low"])]
    else:
        j = max(idx, key=lambda k: b[k]["high"])
        tochki = [(j, "верх", b[j]["high"])]
    for fr in _fraktaly(b, j + 1, len(b)):
        last = tochki[-1]
        if fr[1] == last[1]:
            if (fr[1] == "верх" and fr[2] > last[2]) or \
                    (fr[1] == "низ" and fr[2] < last[2]):
                tochki[-1] = fr
            continue
        if (fr[1] == "верх" and fr[2] <= last[2]) or \
                (fr[1] == "низ" and fr[2] >= last[2]):
            continue
        tochki.append(fr)
    return tochki


def _ao_slovo(x, pt) -> str:
    return f"{x:+.6f}" if pt < 0.0001 else f"{x:+.3f}"


def _hody_blok(symbol, tf, f, bar) -> list:
    try:
        et = _etazh_nizhe(tf)
        ot = f.get("ot")
        if not et or not ot:
            return []
        b = _bary_do(symbol, et, bar)[-600:]
        if len(b) < 40:
            return [f"Ход сделки по фракталам ({et}): баров мало — не разметить."]
        i0 = next((i for i, x in enumerate(b) if _t16(x.get("date")) >= ot), None)
        if i0 is None:
            return [f"Ход сделки по фракталам ({et}): вход позже последнего бара "
                    "этого этажа — разметить пока нечего."]
        long_, r0 = f["long"], f["r0"]
        pt = _punkt(f["e"])
        ao = _ao(b)
        pts = _opory(b, long_, i0) + [(len(b) - 1, "сейчас", b[-1]["close"])]
        hody = []
        for k in range(1, len(pts)):
            (ia, _ta, pa), (ib, tb, pb) = pts[k - 1], pts[k]
            if ib <= ia:
                continue
            vverh = pb > pa
            seg = [a for a in ao[ia:ib + 1] if a is not None]
            nol = sum(1 for m in range(ia + 1, ib + 1)
                      if ao[m] is not None and ao[m - 1] is not None
                      and (ao[m] > 0) != (ao[m - 1] > 0))
            hody.append({
                "vverh": vverh, "po": vverh == long_, "ia": ia, "ib": ib,
                "pa": pa, "pb": pb, "dl": abs(pb - pa), "sejchas": tb == "сейчас",
                "ao": ((max(seg) if vverh else min(seg)) if seg else None),
                "nol": nol})
        if not hody:
            return []
        L = [f"=== ХОД СДЕЛКИ ПО ФРАКТАЛАМ ({et}) — опоры размечает код, роль "
             "хода называешь ты ===",
             "Опоры — край у входа и подтверждённые фракталы (у каждого справа "
             "уже закрылись два бара; вперёд город не смотрит). Ход — от опоры "
             "до опоры; последний идёт сейчас и фракталом ещё не закрыт."]
        gorby, prev = [], None
        nachalo = max(0, len(hody) - HODOV_POKAZYVAEM)
        for n, x in enumerate(hody, 1):
            svoy = x["ao"] is not None and (x["ao"] > 0) == x["vverh"]
            if x["po"] and svoy:
                gorby.append((n, abs(x["ao"])))
            if n - 1 < nachalo:
                prev = x
                continue
            kuda = "вверх" if x["vverh"] else "вниз"
            chey = "по сделке" if x["po"] else "против сделки"
            da, db = _t16(b[x["ia"]].get("date")), _t16(b[x["ib"]].get("date"))
            s = (f"{n}. {kuda}, {chey}: {da} {_f(x['pa'])} → "
                 + ("сейчас" if x["sejchas"] else db) + f" {_f(x['pb'])} — "
                 f"{x['dl'] / pt:.0f} п. = {x['dl'] / r0:.2f}R, {x['ib'] - x['ia']} бар.")
            if not x["po"] and prev is not None and prev["dl"] > 0:
                s += f"; откат {x['dl'] / prev['dl'] * 100:.0f}% прошлого хода"
            if svoy:
                s += (f"; AO {'горб' if x['vverh'] else 'яма'} "
                      f"{_ao_slovo(x['ao'], pt)}")
                if x["po"] and len(gorby) > 1 and gorby[-1][0] == n:
                    bolshe = max(g for _n, g in gorby[:-1])
                    if x["vverh"]:
                        s += (" — больше всех прежних по сделке" if gorby[-1][1] > bolshe
                              else " — меньше самого большого по сделке")
                    else:
                        s += (" — глубже всех прежних по сделке" if gorby[-1][1] > bolshe
                              else " — мельче самой глубокой по сделке")
            elif x["ao"] is not None:
                s += f"; AO ещё по ту сторону нуля ({_ao_slovo(x['ao'], pt)})"
            if x["nol"]:
                s += f"; AO через ноль {x['nol']} раз"
            if x["sejchas"]:
                s += " (идёт, не закрыт фракталом)"
            L.append(s)
            prev = x
        po = sum(1 for x in hody if x["po"])
        itog = f"Ходов по сделке: {po}, против: {len(hody) - po}."
        if gorby:
            nb = max(gorby, key=lambda g: g[1])[0]
            itog += (f" {'Самый большой горб' if long_ else 'Самая глубокая яма'} AO по сделке — "
                     f"в ходе №{nb}.")
        L.append(itog)
        return L
    except Exception as e:
        print(f"[ПРОВОЖАЮ] ход сделки не разметился ({e})")
        return []


def _potom(h, r, zak, moy):
    """Что рынок сделал после этих слов: (куда ещё дошла, чем кончилась)."""
    try:
        sd = str(r.get("сделка") or "")
        ot = sd.split("|")[0]
        sym = str(r.get("символ") or "").upper()
        z = next((z for z in zak if z.get("magic") == moy and not z.get("нога")
                  and not z.get("частичное") and not z.get("тень")
                  and _t16(z.get("opened_at")) == ot), None)
        if z is None:
            return "сделка ещё шла", "—"
        e, x = float(z.get("entry")), float(z.get("exit"))
        r_vy = z.get("R_половины")
        if r_vy is None:
            r_vy = float(z.get("pnl_r")) / float(z.get("доля") or 1.0)
        r_vy = float(r_vy)
        if not r_vy:
            return "—", f"{r_vy:+.2f}R"
        r0 = abs(x - e) / abs(r_vy)
        long_ = h.storona_sdelki(z) == "LONG"
        sg = 1 if long_ else -1
        posle = _t16(r.get("бар"))
        do = _t16(z.get("closed_at"))
        tf = str(z.get("timeframe") or "H4").upper()
        b = [y for y in (h._bary(sym or z.get("symbol"), tf) or [])
             if posle < _t16(y.get("date")) <= do]
        if not b:
            return "дальше не шла", f"{r_vy:+.2f}R"
        kr = (max(b, key=lambda y: y["high"]) if long_
              else min(b, key=lambda y: y["low"]))
        rb = sg * ((kr["high"] if long_ else kr["low"]) - e) / r0
        return f"{rb:+.2f}R ({_t16(kr.get('date'))})", f"{r_vy:+.2f}R"
    except Exception as ex:
        return f"не посчиталось ({ex})", "—"


def _provozhal_otchet(h, resh, zak, moy) -> list:
    pr = [r for r in resh if str(r.get("провожаю") or "").strip()]
    s = ["## Провожал ход — что говорил и что было", "",
         "Его слова в сделке: что за ход, где он сейчас, дивер, сколько ещё идти. "
         "Рядом — что рынок сделал после этого бара: куда ещё дошла сделка и чем "
         "кончилась. Город не судит — ставит рядом.", ""]
    if not pr:
        s += [f"Провожающих слов в этом прогоне нет (решений в сделке: {len(resh)}).",
              ""]
        return s
    s += ["| бар | R тогда | провожаю — его словами | после дошла до | вышел |",
          "|---|---|---|---|---|"]
    for r in pr[-20:]:
        dal, vy = _potom(h, r, zak, moy)
        s.append(f"| {r.get('бар')} | {r.get('R_сейчас')} | "
                 f"{_kl(r.get('провожаю'), 260)} | {dal} | {vy} |")
    s.append("")
    return s


# PROVOZHAYU_V1 - marker


# ══ VEDENIE_PO_MARSHRUTU_V1 — ведёт сделку по маршруту, всегда глядя на младший ══
# Записка «Ведение позиции по двум масштабам» (в корне репо). Маршрут — по месту
# входа (пометка при входе, его же история месяца). Решения его; рука лишь
# требует: младший открыт на этом баре, этап маршрута назван, увиденное сказано.
import re as _re_m

MARSHRUT = {
    "А": ("в откат", [
        ("А1", "наблюдаю развитие на младшем"),
        ("А2", "оцениваю структуру отката"),
        ("А3", "жду дивергенцию на младшем — событие для оценки, не команда закрыть"),
        ("А4", "решение по ведению")]),
    "Б": ("по ходу", [
        ("Б1", "жду, пока на младшем сложится первая волна — не объявляю раньше времени"),
        ("Б2", "первая волна сложилась — описываю её по признакам"),
        ("Б3", "наблюдаю структуру до читаемого импульса"),
        ("Б4", "возвращаюсь на рабочий этаж — сверяю младший с общей картиной"),
        ("Б5", "называю форму волны в общей картине"),
        ("Б6", "решение по ведению — заранее не предопределено")]),
}
NA_MLADSHEM_MIN = 20

PROVOZHAYU_TEKST = PROVOZHAYU_TEKST.replace(
    "Решай, как решал; город потом", "Решение — по маршруту ниже; город потом")


def _kod_etapa(t) -> str:
    m = _re_m.search(r"([АAБB])\s*([1-6])", str(t or "").upper())
    if not m:
        return ""
    return {"A": "А", "B": "Б"}.get(m.group(1), m.group(1)) + m.group(2)


def _scenariy(slot, symbol, napr) -> str:
    """Место входа по пометке на входе: «в откат», «по ходу» или «нет»."""
    try:
        ya = _hm()._yashchik_chitat(slot, symbol)
        vh = [v for v in (ya.get("входы") or [])
              if v.get("что") == "ENTER" and v.get("направление") == str(napr).upper()]
        return str(vh[-1].get("это") or "нет") if vh else "нет"
    except Exception:
        return "нет"


def _bukva(scen) -> str:
    return {"в откат": "А", "по ходу": "Б"}.get(scen, "")


def _spisok(bukva) -> str:
    return " → ".join(f"{k} {t}" for k, t in MARSHRUT[bukva][1])


def _smotrel_mladshiy(slot, symbol, tf) -> bool:
    h = _hm()
    sm = h._yashchik_chitat(slot, symbol).get("смотрел") or {}
    if sm.get("бар") != h._bar_seychas():
        return False
    nizhe = set(h._nizhe_rabochego(tf) or []) | {_etazh_nizhe(tf)}
    return any(e in nizhe or e == "растяжка" for e in (sm.get("этажи") or []))


def _marshrut_proverka(slot, symbol, tf, chto, a, p) -> str:
    """Пусто — приказ идёт к прежним проверкам; иначе отказ руки фактом."""
    try:
        long_ = str(p.get("direction") or "").upper() == "LONG"
        scen = _scenariy(slot, symbol, "LONG" if long_ else "SHORT")
        b = _bukva(scen)
        net = []
        kod = _kod_etapa(a.get("этап"))
        if not kod:
            net.append("«этап» — код и название этапа твоего маршрута ("
                       + (_spisok(b) if b else "А1–А4 или Б1–Б6") + ")")
        elif b and kod[0] != b:
            net.append(f"«этап» из твоего маршрута: место входа — {scen}, маршрут {b}: "
                       + _spisok(b))
        if len(str(a.get("на_младшем") or "").strip()) < NA_MLADSHEM_MIN:
            net.append("«на_младшем» — что видишь на младшем этаже сейчас")
        if not _smotrel_mladshiy(slot, symbol, tf):
            net.append(f"открыть младший этаж ({_etazh_nizhe(tf) or 'ниже рабочего'}) "
                       "на этом баре — рукой pokazat_etazh или stol_na_etazhe")
        if net:
            print(f"[МАРШРУТ] ✗ {slot} {chto}: " + "; ".join(net))
            return ("Приказ НЕ отдан: в сделке ты ведёшь по маршруту и на каждом баре "
                    "смотришь младший этаж. Не хватает: " + "; ".join(net)
                    + ". Маршрут и факты — в блоке «Маршрут сделки». Посмотри, назови и "
                    "позови снова.")
    except Exception as e:
        print(f"[МАРШРУТ] проверка не вышла ({e}) — приказ идёт к прежним проверкам")
    return ""


def _etap_seychas(slot, symbol, klyuch):
    """Последний названный этап этой сделки: (код, бар, его слова о младшем)."""
    try:
        d = _chitat(slot)
        pr = (d.get("прогоны") or {}).get(_hm()._progon()) or {}
        for r in reversed(pr.get("решения") or []):
            if r.get("сделка") == klyuch and r.get("этап"):
                return r["этап"], r.get("бар"), r.get("на_младшем") or ""
    except Exception:
        pass
    return "", "", ""


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:
    try:
        long_ = str(p.get("direction") or "").upper() == "LONG"
        scen = _scenariy(slot, symbol, "LONG" if long_ else "SHORT")
        b = _bukva(scen)
        et = _etazh_nizhe(tf) or "младший"
        klyuch = f"{_t16(p.get('opened_at'))}|{p.get('entry')}"
        kod, s_bara, videl = _etap_seychas(slot, symbol, klyuch)
        L = ["=== МАРШРУТ СДЕЛКИ — ведёшь по нему (записка «Ведение позиции по двум масштабам») ==="]
        if b:
            L.append(f"Место входа: {scen} — пометка при входе, по твоей истории старшего "
                     f"хода; задним числом не переписывается. Маршрут {b}:")
            L.append("  " + _spisok(b))
        else:
            L.append("Место входа при входе не определилось (истории старшего хода не было). "
                     "Назови сам по своей истории: в откат — маршрут А (" + _spisok("А")
                     + "); по ходу — маршрут Б (" + _spisok("Б") + ").")
        L.append(f"Ты сейчас: {kod} (с бара {s_bara}; на младшем ты видел: «{_kl(videl, 200)}»)."
                 if kod else f"Этап ещё не назван — начни с {b or 'А'}1.")
        L.append(f"На каждом баре в сделке: 1) открой младший этаж ({et}) рукой "
                 "pokazat_etazh или stol_na_etazhe; 2) в приказе — «этап» (код и что за "
                 "этап) и «на_младшем» — что там видишь. Дальше по маршруту — только по "
                 "тому, что увидел. Без этого рука решение в сделке не примет.")
        if b == "Б":
            L.append("Не объявляй первую волну сложившейся раньше времени. Решение на Б6 "
                     "заранее не предопределено: не «не совпало — закрыть», а по форме "
                     "волны в общей картине.")
        else:
            L.append("Дивергенция на младшем — событие для оценки отката, а не команда "
                     "закрыть при первом появлении. Решение — по твоим правилам выхода.")
        try:
            import sverka_divera as _sd
            r = _sd.poschitat(symbol, et, "SHORT" if long_ else "LONG") or {}
            if r.get("ok"):
                L.append(f"Дивер на {et} у края хода в твою сторону, по счёту города: "
                         + ("ЕСТЬ" if r.get("est") else "нет")
                         + (f" — {_kl(r.get('slovami'), 220)}" if r.get("slovami") else "")
                         + ". Свои числа — твои.")
        except Exception as _e_sd:
            print(f"[МАРШРУТ] дивер младшего не посчитался ({_e_sd})")
        return L
    except Exception as e:
        print(f"[МАРШРУТ] блок не сложился ({e})")
        return []


def _marshrut_otchet(resh) -> list:
    rr = [r for r in resh if r.get("этап") or r.get("на_младшем")]
    s = ["## Маршрут сделки — этапы и что видел на младшем", "",
         "По записке «Ведение позиции по двум масштабам»: в откат — А1…А4, по ходу — "
         "Б1…Б6. Его этапы и слова о младшем, по барам. Город не судит.", ""]
    if not rr:
        return s + [f"Этапов в этом прогоне не названо (решений в сделке: {len(resh)}).", ""]
    s += ["| бар | сделка | место входа | этап | что решил | на младшем — его словами |",
          "|---|---|---|---|---|---|"]
    for r in rr[-30:]:
        s.append(f"| {r.get('бар')} | {str(r.get('сделка') or '').split('|')[0]} | "
                 f"{r.get('место_входа') or '—'} | {r.get('этап') or '—'} | "
                 f"{r.get('что')} | {_kl(r.get('на_младшем'), 220)} |")
    s.append("")
    return s


_polya_shemy_do_marshruta = polya_shemy


def polya_shemy() -> dict:   # noqa: F811
    d = dict(_polya_shemy_do_marshruta())
    d["этап"] = {"type": "string", "description": (
        "в сделке, обязательно: этап маршрута по месту входа — в откат: А1 наблюдаю, "
        "А2 оцениваю структуру, А3 жду дивергенцию, А4 решение; по ходу: Б1 жду первую "
        "волну, Б2 описываю первую волну, Б3 до импульса, Б4 сверяю с рабочим, Б5 форма "
        "волны, Б6 решение. Код и коротко что за этап")}
    d["на_младшем"] = {"type": "string", "description": (
        "в сделке, обязательно: что ты видишь на младшем этаже сейчас — открой его "
        "рукой на этом баре и скажи своими словами")}
    return d


# VEDENIE_PO_MARSHRUTU_V1 - marker


# ══ VEDENIE_PO_ZAPISKE_V2 — ведение словами записки; рука требует только младший ══
# Записка «Ведение позиции по двум масштабам» — в корне репо. Коды этапов и
# отказ за «не тот этап» сняты: записка — не конвейер. Слово Шефа — в сделке
# он всегда смотрит младший этаж; только это рука и требует.
def _vedenie_po_zapiske(slot) -> bool:
    """Место само говорит в паспорте цеха: «ведение»: «по двум масштабам»."""
    try:
        import json as _js_z
        man = _js_z.loads((_KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха" / _ceh(slot)
                           / "manifest.json").read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper():
                return str(z.get("ведение") or "").strip().lower() == "по двум масштабам"
    except Exception:
        pass
    return False


SCENARIY_A = (
    "Сценарий отката (ты торгуешь сам откат против старшего хода): на младшем "
    "этаже следишь за развитием структуры и ждёшь дивергенцию как значимое "
    "событие для оценки дальнейшего ведения. Дивергенция здесь — элемент "
    "наблюдения, а не команда закрыть при первом её появлении; действие — по "
    "твоим правилам выхода.")
SCENARIY_B = (
    "Сценарий входа в конце отката по старшему ходу: на младшем этаже ждёшь, "
    "пока первая волна действительно сформируется, и описываешь её — не "
    "объявляешь её завершённой раньше времени; следишь дальше за структурой до "
    "читаемого импульса; потом возвращаешься на рабочий этаж, сверяешь младший с "
    "общей картиной и своим старшим ходом, определяешь форму волны — и только "
    "тогда решаешь, как вести. Решение заранее не предопределено: это не «не "
    "совпало — закрыть».")


def _marshrut_proverka(slot, symbol, tf, chto, a, p) -> str:   # noqa: F811
    """Пусто — приказ идёт к прежним проверкам; иначе отказ руки фактом."""
    if not _vedenie_po_zapiske(slot):
        return ""
    try:
        net = []
        if len(str(a.get("на_младшем") or "").strip()) < NA_MLADSHEM_MIN:
            net.append("«на_младшем» — что видишь на младшем этаже сейчас")
        if not _smotrel_mladshiy(slot, symbol, tf):
            net.append(f"открыть младший этаж ({_etazh_nizhe(tf) or 'ниже рабочего'}) "
                       "на этом баре — рукой pokazat_etazh или stol_na_etazhe")
        if net:
            print(f"[ВЕДЕНИЕ] ✗ {slot} {chto}: младший — " + "; ".join(net))
            return ("Приказ НЕ отдан: в сделке ты всегда смотришь и младший этаж. "
                    "Не хватает: " + "; ".join(net) + ". Посмотри, скажи и позови снова.")
    except Exception as e:
        print(f"[ВЕДЕНИЕ] проверка младшего не вышла ({e}) — приказ идёт дальше")
    return ""


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    if not _vedenie_po_zapiske(slot):
        return []
    try:
        long_ = str(p.get("direction") or "").upper() == "LONG"
        scen = _scenariy(slot, symbol, "LONG" if long_ else "SHORT")
        et = _etazh_nizhe(tf) or "младший"
        klyuch = f"{_t16(p.get('opened_at'))}|{p.get('entry')}"
        slova, s_bara, videl = _etap_seychas(slot, symbol, klyuch)
        L = ["=== ВЕДЕНИЕ ПО ДВУМ МАСШТАБАМ (записка «Ведение позиции по двум масштабам») ==="]
        if scen == "в откат":
            L += [f"Место входа: в откат — пометка при входе, по твоей истории старшего "
                  "хода; задним числом не переписывается.", SCENARIY_A]
        elif scen == "по ходу":
            L += [f"Место входа: по ходу — пометка при входе, по твоей истории старшего "
                  "хода; задним числом не переписывается.", SCENARIY_B]
        else:
            L += ["Место входа при входе не определилось (истории старшего хода не было) "
                  "— определи сам по своей истории, какой из двух случаев твой:",
                  SCENARIY_A, SCENARIY_B]
        L.append(f"Где ты по этим шагам — в прошлый раз (бар {s_bara}): «{_kl(slova, 220)}»; "
                 f"на младшем видел: «{_kl(videl, 200)}»." if slova or videl
                 else "По шагам своего сценария ты в этой сделке ещё не говорил.")
        L.append(f"На каждом баре в сделке открой младший этаж ({et}) рукой pokazat_etazh "
                 "или stol_na_etazhe и скажи в приказе: «на_младшем» — что там видишь; "
                 "«этап» — где ты сейчас по шагам своего сценария, своими словами. "
                 "Признал первую волну сформированной — «первая_волна»: где и по каким "
                 "признакам. Вернулся на рабочий этаж — «на_рабочем»: что увидел. "
                 "Определил форму волны — «форма_волны». Без взгляда на младший рука "
                 "решение в сделке не примет.")
        return L
    except Exception as e:
        print(f"[ВЕДЕНИЕ] блок по записке не сложился ({e})")
        return []


def _marshrut_otchet(resh) -> list:   # noqa: F811
    rr = [r for r in resh if r.get("этап") or r.get("на_младшем")]
    s = ["## Ведение по двум масштабам — его слова по барам", "",
         "По записке: что он знал на младшем и когда, где признал первую волну, что "
         "увидел на рабочем, какую форму назвал, что решил. Что было потом — в "
         "«Провожал ход» и «Ведение сделок». Город не судит.", ""]
    if not rr:
        return []
    s += ["| бар | сделка | место входа | что решил | где по шагам | на младшем | "
          "первая волна · на рабочем · форма |", "|---|---|---|---|---|---|---|"]
    for r in rr[-30:]:
        dop = " · ".join(x for x in (
            f"первая волна: {_kl(r.get('первая_волна'), 120)}" if r.get("первая_волна") else "",
            f"на рабочем: {_kl(r.get('на_рабочем'), 120)}" if r.get("на_рабочем") else "",
            f"форма: {_kl(r.get('форма_волны'), 80)}" if r.get("форма_волны") else "") if x) or "—"
        s.append(f"| {r.get('бар')} | {str(r.get('сделка') or '').split('|')[0]} | "
                 f"{r.get('место_входа') or '—'} | {r.get('что')} | "
                 f"{_kl(r.get('этап_слова') or r.get('этап'), 120)} | "
                 f"{_kl(r.get('на_младшем'), 200)} | {dop} |")
    s.append("")
    return s


def polya_shemy() -> dict:   # noqa: F811
    d = dict(_polya_shemy_do_marshruta())
    d["на_младшем"] = {"type": "string", "description": (
        "в сделке: что ты видишь на младшем этаже сейчас — открой его рукой на "
        "этом баре и скажи своими словами")}
    d["этап"] = {"type": "string", "description": (
        "в сделке: где ты сейчас по шагам своего сценария (откат — следишь за "
        "структурой, ждёшь дивергенцию; по ходу — первая волна, импульс, сверка с "
        "рабочим, форма волны), своими словами")}
    d["первая_волна"] = {"type": "string", "description": (
        "если признал первую волну на младшем сформированной — где и по каким признакам")}
    d["на_рабочем"] = {"type": "string", "description": (
        "если вернулся на рабочий этаж сверить картину — что увидел")}
    d["форма_волны"] = {"type": "string", "description": (
        "если определил форму волны в общей картине — какую и почему")}
    return d


# VEDENIE_PO_ZAPISKE_V2 - marker
# VEDENIE_PO_ZAPISKE_V3 - marker


# ══ NASTROENIE_SDELKI_V1 — настроение сделки: месячный дивер и третья волна ══
# Слово Шефа 20.10 — в шапке патча nastroenie_sdelki.py. Город даёт факты,
# настроение и третью волну называет он сам. Решения — его.
NASTROENIE_TEKST = (
    "Как читать (слово Шефа):\n"
    "  · Есть месячный дивер — долгое настроение: даёшь движению пространство, "
    "ждёшь возможного перелома старшего импульса. Локальное истощение само по себе "
    "ещё не причина торопиться с выходом.\n"
    "  · Месячного дивера нет — смотришь на структуру своего хода: была ли уже "
    "третья волна (самый большой горб или яма AO; переход через ноль к четвёртой "
    "точно видно только на масштабе 100–140 баров). Если была — сильная импульсная "
    "часть уже могла пройти, движение может быть ближе к завершению.\n"
    "  · Разбудил разворотник на рабочем — смотри, где ты в этой структуре, а не "
    "выходи автоматически по одному локальному признаку.\n"
    "  · Вошёл в откат (против месяца, месячного дивера нет) — ведёшь по младшему "
    "этажу: дивер там — повод выйти. По ходу или на переломе — ведёшь на рабочем.")
GORB_OKNO = (100, 140)


def _chislo_ao(v) -> str:
    return f"{v:+.5f}" if abs(v) < 1 else f"{v:+.2f}"


def _etazh_mesyaca(tf) -> str:
    try:
        from cherez_etazh import etazh_cherez
        return etazh_cherez(tf) or ""
    except Exception:
        return ""


def _nastroenie_fakt(slot, symbol, p, tf) -> dict:
    """Факт входа: дивер на этаже через один выше, против прежнего хода.
    Считается один раз — при первом взгляде на сделку — и лежит в журнале."""
    klyuch = f"{_t16(p.get('opened_at'))}|{p.get('entry')}"
    try:
        d = _chitat(slot)
        pr = d.setdefault("прогоны", {}).setdefault(_hm()._progon() or "живая", {})
        nas = pr.setdefault("настроение", {})
        if klyuch in nas:
            return nas[klyuch]
    except Exception:
        d, nas = None, None
    et2 = _etazh_mesyaca(tf)
    napr = "LONG" if str(p.get("direction") or "").upper() == "LONG" else "SHORT"
    fakt = {"этаж": et2, "дивер": None, "словами": "этаж выше не определился"}
    if et2:
        try:
            import sverka_divera as _sd
            r = _sd.poschitat(symbol, et2, napr) or {}
            fakt = {"этаж": et2, "дивер": bool(r.get("est")) if r.get("ok") else None,
                    "словами": str(r.get("slovami") or "")[:400]}
        except Exception as e:
            fakt = {"этаж": et2, "дивер": None, "словами": f"не посчитался ({e})"}
    if nas is not None:
        try:
            nas[klyuch] = fakt
            _pisat(slot, d)
        except Exception as e:
            print(f"[НАСТРОЕНИЕ] факт входа не записался ({e})")
    return fakt


def _start_hoda(symbol, tf, p) -> str:
    """Начало хода, который торгуем: край против сделки у входа на рабочем."""
    try:
        from feed_source import bars as _bars
        bs, _pt = _bars(symbol, tf, 400)
        ot = _t16(p.get("opened_at"))
        i0 = next((i for i, x in enumerate(bs) if _t16(x.get("date")) >= ot), len(bs) - 1)
        kusok = bs[max(0, i0 - 12): i0 + 1] or bs[-1:]
        long_ = str(p.get("direction") or "").upper() == "LONG"
        kray = (min(kusok, key=lambda x: x["low"]) if long_
                else max(kusok, key=lambda x: x["high"]))
        return _t16(kray.get("date"))
    except Exception:
        return _t16(p.get("opened_at"))


def _gorby_hoda(symbol, tf, p) -> str:
    """Горбы (ямы) AO в сторону сделки с начала хода — на масштабе, где ход
    занимает ~100–140 баров. Только факты: где, какой величины, был ли ноль."""
    try:
        from feed_source import bars as _bars
        from williams_core import compute_ao_series
        start = _start_hoda(symbol, tf, p)
        etazhi = [tf] + [e for e in (_hm()._nizhe_rabochego(tf) or []) if e != tf]
        luchshiy = None
        for e in etazhi:
            try:
                bs, _pt = _bars(symbol, e, 700)
            except Exception:
                continue
            if not bs or len(bs) < 60:
                continue
            idx = [i for i, x in enumerate(bs) if _t16(x.get("date")) >= start]
            if not idx:
                continue
            n = len(idx)
            mera = 0 if GORB_OKNO[0] <= n <= GORB_OKNO[1] else min(
                abs(n - GORB_OKNO[0]), abs(n - GORB_OKNO[1]))
            if luchshiy is None or mera < luchshiy[0]:
                luchshiy = (mera, e, bs, idx)
            if mera == 0:
                break
        if luchshiy is None:
            return "горбы AO посчитать не на чем — баров нет"
        _m, e, bs, idx = luchshiy
        ao = compute_ao_series([x["high"] for x in bs], [x["low"] for x in bs])
        long_ = str(p.get("direction") or "").upper() == "LONG"
        nazv = "горбы" if long_ else "ямы"
        svoy = (lambda v: v is not None and v > 0) if long_ else (lambda v: v is not None and v < 0)
        runs, cur = [], None
        for i in idx:
            v = ao[i] if i < len(ao) else None
            if svoy(v):
                if cur is None:
                    cur = {"с": i, "по": i, "край": i}
                cur["по"] = i
                if abs(ao[i]) > abs(ao[cur["край"]]):
                    cur["край"] = i
            elif cur is not None:
                runs.append(cur)
                cur = None
        idet = cur is not None
        if cur is not None:
            runs.append(cur)
        okno = (f"{len(idx)} бар." + ("" if GORB_OKNO[0] <= len(idx) <= GORB_OKNO[1]
                                       else " — не в окне 100–140: переход через ноль "
                                            "к четвёртой здесь может не показаться"))
        if not runs:
            return (f"Масштаб {e}: ход с {start} — {okno}. {nazv.capitalize()} AO в сторону "
                    "сделки с начала хода пока нет.")
        big = max(range(len(runs)), key=lambda k: abs(ao[runs[k]["край"]]))
        sp = []
        for k, r in enumerate(runs, 1):
            kon = "идёт" if (idet and k == len(runs)) else _t16(bs[r["по"]].get("date"))
            sp.append(f"{k}) {_t16(bs[r['с']].get('date'))} — {kon}, край "
                      f"{_chislo_ao(ao[r['край']])} ({_t16(bs[r['край']].get('date'))})")
        posle = ("идёт сейчас" if (idet and big == len(runs) - 1)
                 else "после него AO уходил через ноль")
        return (f"Масштаб {e}: ход с {start} — {okno}. {nazv.capitalize()} AO в сторону "
                f"сделки: " + "; ".join(sp) + f". Самый большой — №{big + 1}, {posle}.")
    except Exception as ex:
        print(f"[НАСТРОЕНИЕ] горбы не посчитались ({ex})")
        return ""


def _vedet_po_mladshemu(slot, symbol, p, tf) -> bool:
    """Против месяца и месячного дивера нет — ведение по младшему (слово Шефа)."""
    long_ = str(p.get("direction") or "").upper() == "LONG"
    scen = _scenariy(slot, symbol, "LONG" if long_ else "SHORT")
    fakt = _nastroenie_fakt(slot, symbol, p, tf)
    return scen == "в откат" and fakt.get("дивер") is not True


def _marshrut_proverka(slot, symbol, tf, chto, a, p) -> str:   # noqa: F811
    if not _vedenie_po_zapiske(slot):
        return ""
    try:
        if not _vedet_po_mladshemu(slot, symbol, p, tf):
            return ""
        net = []
        if len(str(a.get("на_младшем") or "").strip()) < NA_MLADSHEM_MIN:
            net.append("«на_младшем» — что видишь на младшем этаже сейчас")
        if not _smotrel_mladshiy(slot, symbol, tf):
            net.append(f"открыть младший этаж ({_etazh_nizhe(tf) or 'ниже рабочего'}) "
                       "на этом баре — рукой pokazat_etazh или stol_na_etazhe")
        if net:
            print(f"[ВЕДЕНИЕ] ✗ {slot} {chto}: откат без месячного дивера — " + "; ".join(net))
            return ("Приказ НЕ отдан: ты в откате против месяца, месячного дивера нет — "
                    "ведёшь по младшему этажу. Не хватает: " + "; ".join(net)
                    + ". Посмотри, скажи и позови снова.")
    except Exception as e:
        print(f"[ВЕДЕНИЕ] проверка не вышла ({e}) — приказ идёт дальше")
    return ""


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    if not _vedenie_po_zapiske(slot):
        return []
    try:
        long_ = str(p.get("direction") or "").upper() == "LONG"
        scen = _scenariy(slot, symbol, "LONG" if long_ else "SHORT")
        fakt = _nastroenie_fakt(slot, symbol, p, tf)
        et2 = fakt.get("этаж") or "этаж выше"
        dv = fakt.get("дивер")
        L = ["=== НАСТРОЕНИЕ СДЕЛКИ ===",
             f"Место входа: {scen} (пометка при входе, по твоей истории старшего хода).",
             f"Дивер на {et2} при входе, против прежнего хода, по счёту города: "
             + ("ЕСТЬ" if dv is True else "нет" if dv is False else "не посчитался")
             + (f" — {_kl(fakt.get('словами'), 260)}" if fakt.get("словами") else "")
             + ". Это факт входа, он не меняется."]
        g = _gorby_hoda(symbol, tf, p)
        if g:
            L.append("Твой ход: " + g + " Какая это волна — называешь ты.")
        L.append(NASTROENIE_TEKST)
        if _vedet_po_mladshemu(slot, symbol, p, tf):
            L.append(f"Сейчас твой случай — откат без месячного дивера: на каждом "
                     f"пробуждении открой младший этаж ({_etazh_nizhe(tf) or 'ниже рабочего'}) "
                     "рукой pokazat_etazh или stol_na_etazhe и скажи в «на_младшем», что "
                     "там видишь. Без этого рука решение в сделке не примет.")
        L.append("В приказе скажи «настроение» — какое у сделки настроение и почему, "
                 "была ли уже третья волна и где, своими словами.")
        return L
    except Exception as e:
        print(f"[НАСТРОЕНИЕ] блок не сложился ({e})")
        return []


_marshrut_otchet_do_nastroeniya = _marshrut_otchet


def _marshrut_otchet(resh) -> list:   # noqa: F811
    rr = [r for r in resh if r.get("настроение")]
    s = list(_marshrut_otchet_do_nastroeniya(resh) or [])
    if not rr:
        return s
    s += ["## Настроение сделки — его слова по барам", "",
          "| бар | сделка | место входа | что решил | настроение — его словами |",
          "|---|---|---|---|---|"]
    for r in rr[-30:]:
        s.append(f"| {r.get('бар')} | {str(r.get('сделка') or '').split('|')[0]} | "
                 f"{r.get('место_входа') or '—'} | {r.get('что')} | "
                 f"{_kl(r.get('настроение'), 260)} |")
    s.append("")
    return s


_polya_shemy_do_nastroeniya = polya_shemy


def polya_shemy() -> dict:   # noqa: F811
    d = dict(_polya_shemy_do_nastroeniya())
    d["настроение"] = {"type": "string", "description": (
        "в сделке: настроение сделки и почему — есть ли месячный дивер (долгое "
        "настроение) или смотришь по третьей волне своего хода (была ли уже и где), "
        "своими словами")}
    return d


# NASTROENIE_SDELKI_V1 - marker


# ══ ETAZH_VMESTO_MESYACA_V1 — в словах настоящий старший этаж места ══
# Расчёт всегда шёл от рабочего этажа (этаж через один выше — etazh_cherez),
# а в словах стояло «месячный». Теперь слова говорят тот этаж, что посчитан.
def _slova_etazha(s: str, et2: str) -> str:
    et2 = et2 or "старшем этаже"
    for old, new in (("Есть месячный дивер", f"Есть дивер на {et2}"),
                     ("Месячного дивера нет", f"Дивера на {et2} нет"),
                     ("месячного дивера нет", f"дивера на {et2} нет"),
                     ("без месячного дивера", f"без дивера на {et2}"),
                     ("месячного дивера", f"дивера на {et2}"),
                     ("месячный дивер", f"дивер на {et2}"),
                     ("против месяца", "против старшего хода")):
        s = s.replace(old, new)
    return s


_marshrut_blok_s_mesyacem = _marshrut_blok


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    et2 = _etazh_mesyaca(tf)
    return [_slova_etazha(x, et2) for x in (_marshrut_blok_s_mesyacem(slot, symbol, p, bar, tf) or [])]


_marshrut_proverka_s_mesyacem = _marshrut_proverka


def _marshrut_proverka(slot, symbol, tf, chto, a, p) -> str:   # noqa: F811
    return _slova_etazha(_marshrut_proverka_s_mesyacem(slot, symbol, tf, chto, a, p) or "",
                         _etazh_mesyaca(tf))


_polya_shemy_s_mesyacem = polya_shemy


def polya_shemy() -> dict:   # noqa: F811
    d = dict(_polya_shemy_s_mesyacem())
    if "настроение" in d:
        d["настроение"] = {"type": "string", "description": (
            "в сделке: настроение сделки и почему — есть ли дивер на старшем этаже "
            "(через один выше рабочего: долгое настроение) или смотришь по третьей "
            "волне своего хода (была ли уже и где), своими словами")}
    return d


# ETAZH_VMESTO_MESYACA_V1 - marker


# ══ MESTO_BEZ_IMENI_V1 — поле места: новое имя, старые записи читаются ══
def _pole_mesta(d, imya):
    try:
        import mesto_urovnya as _mu_p
        return _mu_p.pole(d, imya)
    except Exception:
        return (d or {}).get(imya)


# MESTO_BEZ_IMENI_V1 - marker


# ══ SVECHA_STARSHEGO_V1 — дивер старшего этажа: с текущей свечой, на каждом пробуждении ══
def _nastroenie_fakt(slot, symbol, p, tf) -> dict:   # noqa: F811
    et2 = _etazh_mesyaca(tf)
    napr = "LONG" if str(p.get("direction") or "").upper() == "LONG" else "SHORT"
    fakt = {"этаж": et2, "дивер": None, "словами": "этаж выше не определился"}
    if et2:
        try:
            import sverka_divera as _sd
            r = _sd.diver_so_svechoy(symbol, et2, napr) or {}
            fakt = {"этаж": et2, "дивер": bool(r.get("est")) if r.get("ok") else None,
                    "словами": str(r.get("slovami") or "")[:400]}
        except Exception as e:
            fakt = {"этаж": et2, "дивер": None, "словами": f"не посчитался ({e})"}
    try:
        klyuch = f"{_t16(p.get('opened_at'))}|{p.get('entry')}"
        d = _chitat(slot)
        pr = d.setdefault("прогоны", {}).setdefault(_hm()._progon() or "живая", {})
        nas = pr.setdefault("настроение", {})
        bylo = nas.get(klyuch) or {}
        fakt["при_входе"] = bylo.get("при_входе", bylo.get("дивер", fakt.get("дивер")))
        if fakt.get("дивер") is True:
            fakt["с_бара"] = bylo.get("с_бара") or _hm()._bar_seychas()
        nas[klyuch] = fakt
        _pisat(slot, d)
    except Exception as e:
        print(f"[НАСТРОЕНИЕ] факт не записался ({e})")
    return fakt


_marshrut_blok_do_svechi = _marshrut_blok


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    L = list(_marshrut_blok_do_svechi(slot, symbol, p, bar, tf) or [])
    if not L:
        return L
    try:
        f = _nastroenie_fakt(slot, symbol, p, tf)
        kogda = (f"есть с бара {f['с_бара']}" if f.get("дивер") is True and f.get("с_бара")
                 else "пока нет")
        out = []
        for x in L:
            x = x.replace(" при входе, против прежнего хода,", ", против прежнего хода "
                          "(с текущей, ещё не закрытой свечой),")
            x = x.replace("Это факт входа, он не меняется.",
                          f"Считается на каждом пробуждении: {kogda}.")
            out.append(x)
        return out
    except Exception as e:
        print(f"[НАСТРОЕНИЕ] слова о диверах не поправились ({e})")
        return L


# SVECHA_STARSHEGO_V1 - marker


# ══ NA_PERELOME_V1 — место входа «на переломе», если на старшем дивер против хода ══
_scenariy_do_pereloma = _scenariy


def _scenariy(slot, symbol, napr) -> str:   # noqa: F811
    s = _scenariy_do_pereloma(slot, symbol, napr)
    if s != "в откат":
        return s
    try:
        h = _hm()
        if hasattr(h, "_na_perelome") and h._na_perelome(slot, symbol, napr)[0]:
            return "на переломе"
    except Exception as e:
        print(f"[ВЕДЕНИЕ] перелом не посчитался ({e}) — «в откат»")
    return s


_marshrut_blok_do_pereloma = _marshrut_blok


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    L = list(_marshrut_blok_do_pereloma(slot, symbol, p, bar, tf) or [])
    try:
        long_ = str(p.get("direction") or "").upper() == "LONG"
        if L and _scenariy(slot, symbol, "LONG" if long_ else "SHORT") == "на переломе":
            et2 = _etazh_mesyaca(tf) or "старшем этаже"
            vst = (f"На переломе: ты вошёл против старшего хода, но на {et2} дивер у "
                   "нового края против него — может начинаться новый ход. Ведёшь на "
                   "рабочем этаже, ждёшь дивер на рабочем; «выходить быстро на "
                   "младшем» — правило отката, здесь оно не твоё. Решаешь ты.")
            i = next((k for k, x in enumerate(L) if x.startswith("Место входа:")), 0)
            L.insert(i + 1, vst)
    except Exception as e:
        print(f"[ВЕДЕНИЕ] слова о переломе не легли ({e})")
    return L


# NA_PERELOME_V1 - marker


# ══ POSLE_PERELOMA_V1 — место входа «после перелома» ══
_scenariy_do_posle = _scenariy


def _scenariy(slot, symbol, napr) -> str:   # noqa: F811
    try:
        h = _hm()
        if hasattr(h, "posle_pereloma") and h.posle_pereloma(slot, symbol, napr):
            return "после перелома"
    except Exception as e:
        print(f"[ВЕДЕНИЕ] «после перелома» не посчиталось ({e})")
    return _scenariy_do_posle(slot, symbol, napr)


_marshrut_blok_do_posle = _marshrut_blok


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    L = list(_marshrut_blok_do_posle(slot, symbol, p, bar, tf) or [])
    try:
        long_ = str(p.get("direction") or "").upper() == "LONG"
        if L and _scenariy(slot, symbol, "LONG" if long_ else "SHORT") == "после перелома":
            vst = ("После перелома: ты входила в откат, но старший ход по факту развернулся "
                   "в твою сторону. Теперь это сделка по старшему ходу — главная: держат, "
                   "пока старший ход идёт; ведёшь на рабочем, ждёшь дивер на рабочем. "
                   "Первоначальная пометка «в откат» здесь больше не правило. Решаешь ты.")
            i = next((k for k, x in enumerate(L) if x.startswith("Место входа:")), 0)
            L.insert(i + 1, vst)
    except Exception as e:
        print(f"[ВЕДЕНИЕ] слова «после перелома» не легли ({e})")
    return L


# POSLE_PERELOMA_V1 - marker


# ══ OTKAT_TRETYA_V1 — правило отката в «Настроении сделки» ══
_OTKAT_STAROE = "ведёшь по младшему этажу: дивер там — повод выйти."
_OTKAT_NOVOE = ("смотришь младший этаж на каждом пробуждении; дивер там — повод выйти, но "
                "только когда третья волна твоего хода уже прошла; пока не прошла — держишь, "
                "даже если младший развернулся.")
if _OTKAT_STAROE in NASTROENIE_TEKST:
    NASTROENIE_TEKST = NASTROENIE_TEKST.replace(_OTKAT_STAROE, _OTKAT_NOVOE)
else:
    print("[ВЕДЕНИЕ] OTKAT_TRETYA_V1: строку отката в настроении не нашёл — дописываю")
    NASTROENIE_TEKST = NASTROENIE_TEKST + "\n  · Откат: " + _OTKAT_NOVOE


# OTKAT_TRETYA_V1 - marker


# ══ VEDENIE_PROSTO_V1 — ведение просто; в сделке всегда старший и младший этажи ══
# Слово Шефа 22.10. Откат — до разворотника против сделки на рабочем; по ходу,
# на переломе, после перелома — до дивера против сделки на рабочем. В сделке на
# каждом пробуждении — старший и младший этажи рукой и «место». Перед входом —
# ничего. Решения её.
_LESENKA_P = ["M1", "M5", "M15", "M30", "H1", "H2", "H3", "H4", "H6", "H8", "H12",
              "D1", "W1", "MN1"]


def _vyshe_nizhe(tf):
    tf = str(tf or "").upper()
    if tf not in _LESENKA_P:
        return set(), set()
    i = _LESENKA_P.index(tf)
    return set(_LESENKA_P[i + 1:]), set(_LESENKA_P[:i])


def _smotrel_etazhi(slot, symbol, tf) -> tuple:
    """(старший смотрела?, младший смотрела?) — на этом баре, рукой."""
    try:
        h = _hm()
        sm = h._yashchik_chitat(slot, symbol).get("смотрел") or {}
        if sm.get("бар") != h._bar_seychas():
            return False, False
        vyshe, nizhe = _vyshe_nizhe(tf)
        et = set(sm.get("этажи") or [])
        return bool(et & vyshe), bool(et & nizhe or "растяжка" in et)
    except Exception:
        return False, False


def _fakty_rabochego(symbol, tf, long_) -> tuple:
    """(дата разворотника против или None, дивер против: True/False/None)."""
    try:
        from feed_source import bars as _bars
        from williams_core import (compute_alligator, compute_ao_series, vse_necron)
        import sverka_divera as _sd
        bs, point = _bars(symbol, tf, 400)
        try:
            import hooks as _h
            bs = _h._tolko_zakrytye(bs)
        except Exception:
            pass
        if not bs or len(bs) < 40:
            return None, None
        hi = [b["high"] for b in bs]
        lo = [b["low"] for b in bs]
        n = len(bs)
        al = compute_alligator(hi, lo, point=point)
        nec = {r["i"]: r["сторона"] for r in vse_necron(
            bs, al.get("jaw_series"), al.get("teeth_series"), al.get("lips_series"),
            s=max(1, n - 8))}
        protiv = "BEAR" if long_ else "BULL"
        i_nec = next((i for i in range(n - 1, n - 4, -1) if nec.get(i) == protiv), None)
        ao = compute_ao_series(hi, lo)
        a = max(0, n - 300)
        ao_o = ao[a:]
        r = _sd.dve_gorki(ao_o, hi[a:], lo[a:], list(range(max(0, len(ao_o) - 140), len(ao_o))),
                          protiv == "BEAR", bs[a:]) or {}
        return (str(bs[i_nec].get("date"))[:10] if i_nec is not None else None,
                bool(r.get("est")) if r.get("ok", True) else None)
    except Exception as e:
        print(f"[ВЕДЕНИЕ] факты рабочего не посчитались ({e})")
        return None, None


def _pravilo(scen) -> str:
    return ("держишь до разворотника против сделки на рабочем этаже — по нему выходишь"
            if scen == "в откат" else
            "держишь до дивера против сделки на рабочем этаже — по нему выходишь")


def _marshrut_proverka(slot, symbol, tf, chto, a, p) -> str:   # noqa: F811
    if not _vedenie_po_zapiske(slot):
        return ""
    try:
        st, ml = _smotrel_etazhi(slot, symbol, tf)
        net = []
        if not st:
            net.append(f"открыть старший этаж ({_etazh_mesyaca(tf) or 'выше рабочего'}) рукой "
                       "на этом баре")
        if not ml:
            net.append(f"открыть младший этаж ({_etazh_nizhe(tf) or 'ниже рабочего'}) рукой "
                       "на этом баре")
        if len(str(a.get("место") or "").strip()) < 5:
            net.append("«место» — где ты в этой сделке: откат, по ходу или перелом, и почему")
        if net:
            print(f"[ВЕДЕНИЕ] ✗ {slot} {chto}: " + "; ".join(net))
            return ("Приказ НЕ отдан: в сделке ты всегда смотришь этажи и знаешь, где ты. "
                    "Не хватает: " + "; ".join(net) + ". Посмотри, скажи и позови снова.")
    except Exception as e:
        print(f"[ВЕДЕНИЕ] проверка этажей не вышла ({e}) — приказ идёт дальше")
    return ""


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    if not _vedenie_po_zapiske(slot):
        return []
    try:
        long_ = str(p.get("direction") or "").upper() == "LONG"
        scen = _scenariy(slot, symbol, "LONG" if long_ else "SHORT")
        et2 = _etazh_mesyaca(tf) or "старший"
        et = _etazh_nizhe(tf) or "младший"
        nec, div = _fakty_rabochego(symbol, tf, long_)
        return ["=== ВЕДЕНИЕ (слово Шефа: просто) ===",
                f"Место сделки — пометка города: {scen}.",
                "Правило: откат — держишь до разворотника против сделки на рабочем этаже, "
                "по нему выходишь. По ходу, на переломе, после перелома — держишь до дивера "
                f"против сделки на рабочем этаже, по нему выходишь. Твоё сейчас: {_pravilo(scen)}.",
                f"Рабочий {tf} сейчас: разворотник против сделки — "
                + (f"ЕСТЬ ({nec})" if nec else "нет")
                + " · дивер против сделки — "
                + ("ЕСТЬ" if div else "нет" if div is False else "не посчитался") + ".",
                f"На этом пробуждении: открой рукой старший ({et2}) и младший ({et}) этажи "
                "(pokazat_etazh или stol_na_etazhe) и скажи в приказе «место» — где ты: "
                "откат, по ходу или перелом, и почему. Без этого рука решение в сделке не примет."]
    except Exception as e:
        print(f"[ВЕДЕНИЕ] блок не сложился ({e})")
        return []


def _marshrut_otchet(resh) -> list:   # noqa: F811
    rr = [r for r in resh if r.get("место")]
    if not rr:
        return []
    s = ["## Ведение — где она и что решила", "",
         "Её «место» рядом с пометкой города. Правило: откат — до разворотника против на "
         "рабочем; по ходу/перелом — до дивера против на рабочем.", "",
         "| бар | сделка | пометка города | что решил | её «место» |", "|---|---|---|---|---|"]
    for r in rr[-40:]:
        s.append(f"| {r.get('бар')} | {str(r.get('сделка') or '').split('|')[0]} | "
                 f"{r.get('место_входа') or '—'} | {r.get('что')} | {_kl(r.get('место'), 240)} |")
    s.append("")
    return s


_polya_shemy_do_prosto = polya_shemy


def polya_shemy() -> dict:   # noqa: F811
    d = dict(_polya_shemy_do_prosto())
    d["место"] = {"type": "string", "description": (
        "в сделке, обязательно: где ты сейчас — откат, по ходу или перелом, и почему "
        "(посмотрев старший и младший этажи)")}
    return d


# VEDENIE_PROSTO_V1 - marker


# ══ OTKAT_DO_SOSEDEY_V1 — поля руки как до 20.10 (слово Шефа 23.10) ══
try:
    polya_shemy = _polya_shemy_do_marshruta   # noqa: F811
except NameError:
    pass


# OTKAT_DO_SOSEDEY_V1 - marker


# ══ OPYT_STOLA_V1 — на столе в сделке: её опыт для её места ══
_marshrut_blok_do_opyta = _marshrut_blok


def _marshrut_blok(slot, symbol, p, bar, tf) -> list:   # noqa: F811
    L = list(_marshrut_blok_do_opyta(slot, symbol, p, bar, tf) or [])
    try:
        import opyt_stola as _os
        ceh = _ceh(slot)
        if not _os.vklyucheno(ceh, slot):
            return L
        try:
            from cartridge_registry import resolve_para
            imya = (resolve_para(ceh, slot) or {}).get("имя") or ""
        except Exception:
            imya = ""
        if not imya:
            return L
        napr = "LONG" if str(p.get("direction") or "").upper() == "LONG" else "SHORT"
        vh = (_hm()._yashchik_chitat(slot, symbol).get("входы")) or []
        mesto = _os._mesto(vh, napr, p.get("opened_at"))
        god, run = None, None
        try:
            from hooks import load_trading_state
            run = ((load_trading_state() or {}).get("прогон") or {}).get("id")
            if run:
                god = str(bar or _hm()._bar_seychas() or "")[:4]
        except Exception:
            pass
        L += _os.stroki_stola(imya, mesto,
                              _os.perezahod_li(ceh, slot, napr, p.get("opened_at")),
                              god if god and god.isdigit() else None, run)
    except Exception as e:
        print(f"[ОПЫТ] стол опыта не сложился ({e})")
    return L


# OPYT_STOLA_V1 - marker


# ══ SNIMOK_I_FAKTY_V1 — снимок места с фактами при входе; расхождения — в отчёт ══
# Слово Шефа 10.11. Только места с пометкой «снимок_и_факты»: «да». Без замков.
def _pometka_sf(slot) -> bool:
    try:
        man = json.loads((_KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха" / _ceh(slot)
                          / "manifest.json").read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper():
                return str(z.get("снимок_и_факты") or "").strip().lower() in ("да", "true", "1")
    except Exception:
        pass
    return False


def _diver_starshego_sf(symbol, tf, napr) -> dict:
    """Дивер на старшем: подтверждённый (закрытые свечи) и предварительный (с текущей)."""
    et2 = _etazh_mesyaca(tf) or ""
    out = {"этаж": et2}
    if not et2:
        return out
    try:
        import sverka_divera as _sd_f
        r = _sd_f.poschitat(symbol, et2, napr) or {}
        out["подтверждённый"] = bool(r.get("est")) if r.get("ok") else None
        out["подтверждённый_словами"] = str(r.get("slovami") or "")[:300]
    except Exception as e:
        out["подтверждённый_словами"] = f"не посчитался ({e})"
    try:
        import sverka_divera as _sd_f2
        if hasattr(_sd_f2, "diver_so_svechoy"):
            r = _sd_f2.diver_so_svechoy(symbol, et2, napr) or {}
            out["предварительный"] = bool(r.get("est")) if r.get("ok") else None
            out["предварительный_словами"] = str(r.get("slovami") or "")[:300]
    except Exception as e:
        out["предварительный_словами"] = f"не посчитался ({e})"
    return out


def _da_net_sf(v) -> str:
    return "ЕСТЬ" if v is True else ("нет" if v is False else "не посчитался")


def _klyuch_sf(p) -> str:
    return f"{_t16(p.get('opened_at'))}|{p.get('entry')}"


_scenariy_do_snimka = _scenariy


def _scenariy(slot, symbol, napr) -> str:   # noqa: F811
    if not _pometka_sf(slot):
        return _scenariy_do_snimka(slot, symbol, napr)
    try:
        p, _n = _pozicii(slot, symbol)
    except Exception:
        p = None
    if not p or str(p.get("direction") or "").upper() != str(napr or "").upper():
        return _scenariy_do_snimka(slot, symbol, napr)
    try:
        d = _chitat(slot)
        pr = d.setdefault("прогоны", {}).setdefault(_hm()._progon() or "живая", {})
        sn = pr.setdefault("снимок_при_входе", {})
        kl = _klyuch_sf(p)
        if kl in sn:
            return sn[kl].get("место") or _scenariy_do_snimka(slot, symbol, napr)
        s = _scenariy_do_snimka(slot, symbol, napr)
        tf = str(p.get("timeframe") or "D1").upper()
        fakty = _diver_starshego_sf(symbol, tf, napr)
        vh = {}
        try:
            vv = [v for v in (_hm()._yashchik_chitat(slot, symbol).get("входы") or [])
                  if v.get("что") == "ENTER" and v.get("направление") == str(napr).upper()]
            vh = vv[-1] if vv else {}
        except Exception:
            pass
        sn[kl] = {"место": s, "бар": _hm()._bar_seychas(), "старший": fakty,
                  "старший_ход": {k: vh.get(k) for k in ("старший_ход", "старший_делает",
                                                         "старший_с") if vh.get(k)}}
        _pisat(slot, d)
        print(f"[ВЕДЕНИЕ] {slot} {napr} {p.get('entry')}: снимок при входе — {s}; дивер на "
              f"{fakty.get('этаж')}: подтверждённый {_da_net_sf(fakty.get('подтверждённый'))}, "
              f"предварительный {_da_net_sf(fakty.get('предварительный'))}")
        return s
    except Exception as e:
        print(f"[ВЕДЕНИЕ] снимок при входе не записался ({e}) — место как было")
        return _scenariy_do_snimka(slot, symbol, napr)


_blok_do_snimka = blok


def blok(slot, symbol, napr=None, bar=None) -> str:   # noqa: F811
    s = _blok_do_snimka(slot, symbol, napr=napr, bar=bar)
    if not s or not _pometka_sf(slot):
        return s
    try:
        p, _n = _pozicii(slot, symbol)
        if not p:
            return s
        nap = "LONG" if str(p.get("direction") or "").upper() == "LONG" else "SHORT"
        mesto = _scenariy(slot, symbol, nap)
        pr = (_chitat(slot).get("прогоны") or {}).get(_hm()._progon() or "живая") or {}
        sn = (pr.get("снимок_при_входе") or {}).get(_klyuch_sf(p)) or {}
        f0 = sn.get("старший") or {}
        tf = str(p.get("timeframe") or "D1").upper()
        f1 = _diver_starshego_sf(symbol, tf, nap)
        sh = sn.get("старший_ход") or {}
        L = ["=== МЕСТО СДЕЛКИ — СНИМОК ПРИ ВХОДЕ (факты, место — вывод) ===",
             f"Место: {mesto} — записано при входе (бар {sn.get('бар') or '—'}), до закрытия "
             "сделки не меняется."]
        if sh:
            L.append("Старший ход при входе (твои слова): " + ", ".join(f"{k}: {v}" for k, v in sh.items()) + ".")
        L.append(f"Дивер на {f0.get('этаж') or 'старшем'} при входе: подтверждённый (закрытые "
                 f"свечи) — {_da_net_sf(f0.get('подтверждённый'))}"
                 + (f" ({_kl(f0.get('подтверждённый_словами'), 200)})" if f0.get('подтверждённый_словами') else "")
                 + f"; предварительный (с незакрытой свечой) — {_da_net_sf(f0.get('предварительный'))}.")
        L.append(f"Дивер на {f1.get('этаж') or 'старшем'} сейчас: подтверждённый — "
                 f"{_da_net_sf(f1.get('подтверждённый'))}; предварительный — "
                 f"{_da_net_sf(f1.get('предварительный'))}. Предварительный может смениться до "
                 "закрытия свечи — это не повод переписывать место.")
        return s + "\n".join(L) + "\n\n"
    except Exception as e:
        print(f"[ВЕДЕНИЕ] снимок в блок не лёг ({e})")
        return s


_obosnovanie_do_rashozhdeniy = obosnovanie


def obosnovanie(slot, symbol, tf, chto, args) -> str:   # noqa: F811
    otkaz = _obosnovanie_do_rashozhdeniy(slot, symbol, tf, chto, args)
    if otkaz or str(chto or "").upper().strip() != "CLOSE" or not _pometka_sf(slot):
        return otkaz
    try:
        p, _n = _pozicii(slot, symbol)
        if not p:
            return otkaz
        nap = "LONG" if str(p.get("direction") or "").upper() == "LONG" else "SHORT"
        mesto = _scenariy(slot, symbol, nap)
        if mesto == "в откат":
            return otkaz
        import vedenie_masshtab as _vm_r
        stroka_g = _vm_r.stroka(symbol, dict(p, trader=slot)) or ""
        F = getattr(_vm_r, "_FAKTY_F", {}).get("последние") or {}
        if F.get("вывод") == "3 на 5":
            return otkaz
        a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
        d = _chitat(slot)
        pr = d.setdefault("прогоны", {}).setdefault(_hm()._progon() or "живая", {})
        pr["расхождения"] = (pr.get("расхождения") or [])[-199:] + [{
            "бар": _hm()._bar_seychas(), "сделка": _klyuch_sf(p), "сторона": nap,
            "место": mesto, "она": str(a.get("почему") or "")[:1200],
            "город_вывод": F.get("вывод"),
            "город_факты": (_vm_r.fakty_slovami(F, nap == "LONG")
                            if hasattr(_vm_r, "fakty_slovami") else stroka_g[-600:])}]
        _pisat(slot, d)
        print(f"[ВЕДЕНИЕ] ≠ {slot} CLOSE при месте «{mesto}»: город — «{F.get('вывод')}»; "
              "расхождение записано (не запрет)")
    except Exception as e:
        print(f"[ВЕДЕНИЕ] расхождение не записалось ({e})")
    return otkaz


_otchet_do_rashozhdeniy = otchet


def otchet(sloty) -> list:   # noqa: F811
    s = list(_otchet_do_rashozhdeniy(sloty) or [])
    for slot in sloty or []:
        try:
            if not _pometka_sf(slot):
                continue
            d = _chitat(slot)
            pid = _hm()._progon()
            pr = (d.get("прогоны") or {}).get(pid) or (d.get("прогоны") or {}).get(
                d.get("последний_прогон")) or {}
            rr = pr.get("расхождения") or []
            s += ["## Расхождения с городом — она закрыла, город не видел «3 на 5»", "",
                  "Не судим заранее: рядом её основание и факты города. Разбираем — кто "
                  "сравнивал не тот участок.", ""]
            if not rr:
                s += ["Расхождений в этом прогоне нет.", ""]
                continue
            s += ["| бар | сделка | место | вывод города | факты города | её «почему» |",
                  "|---|---|---|---|---|---|"]
            for r in rr[-30:]:
                s.append(f"| {r.get('бар')} | {str(r.get('сделка') or '').split('|')[0]} | "
                         f"{r.get('место')} | {r.get('город_вывод')} | "
                         f"{_kl(r.get('город_факты'), 400)} | {_kl(r.get('она'), 400)} |")
            s.append("")
        except Exception as e:
            s += [f"(раздел расхождений не собрался: {e})", ""]
    return s

# SNIMOK_I_FAKTY_V1 - marker
