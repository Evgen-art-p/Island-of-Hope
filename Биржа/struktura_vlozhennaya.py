# -*- coding: utf-8 -*-
"""Наблюдательная карта вложенной структуры MN1 -> D1 для D03.

Не размечает волны Эллиотта, не ставит торговых меток и не меняет приказы.
Показывает подтверждённые фрактальные участки, их родство и две версии
картины: доступную на входе и уточнённую последующими барами.
"""
from __future__ import annotations

from bisect import bisect_left
from datetime import datetime, timedelta


def _date(s):
    try:
        from volny_kanon import kak_vremya
        return kak_vremya(s)
    except Exception:
        return None


class _Series:
    def __init__(self, tf, t, hi, lo, cl, ao, partial=False):
        self.tf, self.t, self.hi, self.lo, self.cl, self.ao = tf, t, hi, lo, cl, ao
        self.partial = partial


_TF_ORDER = {"MN1": 0, "W1": 1, "D1": 2, "H12": 3, "H8": 4,
             "H4": 5, "H1": 6, "M30": 7, "M15": 8, "M10": 9, "M5": 10}
_CHILD_TF = {"MN1": "D1", "D1": "H4", "H4": "H1",
             "H1": "M30", "M30": "M15", "M15": "M10", "M10": "M5"}


def _period_bounds(tf, when):
    """Календарные границы свечи MT5, содержащей when."""
    if tf == "MN1":
        lo = when.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        hi = (lo.replace(year=lo.year + 1, month=1) if lo.month == 12
              else lo.replace(month=lo.month + 1))
    elif tf == "D1":
        lo = datetime(when.year, when.month, when.day)
        hi = lo + timedelta(days=1)
    elif tf == "H4":
        lo = when.replace(hour=(when.hour // 4) * 4, minute=0, second=0, microsecond=0)
        hi = lo + timedelta(hours=4)
    elif tf == "H1":
        lo = when.replace(minute=0, second=0, microsecond=0)
        hi = lo + timedelta(hours=1)
    elif tf == "M30":
        lo = when.replace(minute=(when.minute // 30) * 30, second=0, microsecond=0)
        hi = lo + timedelta(minutes=30)
    elif tf == "M15":
        lo = when.replace(minute=(when.minute // 15) * 15, second=0, microsecond=0)
        hi = lo + timedelta(minutes=15)
    elif tf == "M10":
        lo = when.replace(minute=(when.minute // 10) * 10, second=0, microsecond=0)
        hi = lo + timedelta(minutes=10)
    elif tf == "M5":
        lo = when.replace(minute=(when.minute // 5) * 5, second=0, microsecond=0)
        hi = lo + timedelta(minutes=5)
    else:
        raise ValueError(f"Неизвестный этаж: {tf}")
    return lo, hi


def _cut(L, end, tf=None):
    from williams_core import compute_ao_series
    hi, lo, cl = L.hi[:end], L.lo[:end], L.cl[:end]
    ao = list(compute_ao_series(hi, lo)) if hi else []
    return _Series(tf or L.tf, L.t[:end], hi, lo, cl, ao)


def _series(symbol, tf, when=None, cache=None, working_tf="D1"):
    """Срез на входе без входной свечи; старшие незакрытые свечи
    пересобираются из младших баров, доступных строго до её начала."""
    from volny_kanon import _Lenta, _bar_goroda
    cache = cache if cache is not None else {}
    tf = str(tf or "D1").upper()
    working_tf = str(working_tf or "D1").upper()
    base = cache.get(tf)
    if base is None:
        base = _Lenta(symbol, tf)
        cache[tf] = base

    # Текущая картина: сохраняем восстановление текущего MN1 из D1.
    if when is None:
        if tf != "MN1":
            return base
        child = _series(symbol, "D1", None, cache, working_tf)
        if not child.t:
            return base
        period_start, _ = _period_bounds("MN1", child.t[-1])
        parent_end = bisect_left(base.t, period_start)
        ts, hi, lo, cl = (list(base.t[:parent_end]), list(base.hi[:parent_end]),
                          list(base.lo[:parent_end]), list(base.cl[:parent_end]))
        left = bisect_left(child.t, period_start)
        if len(child.t) > left:
            ts.append(period_start)
            hi.append(max(child.hi[left:]))
            lo.append(min(child.lo[left:]))
            cl.append(child.cl[-1])
        from williams_core import compute_ao_series
        ao = list(compute_ao_series(hi, lo)) if hi else []
        bar = str(_bar_goroda() or "")
        partial = bool(ts and bar[:7] == ts[-1].strftime("%Y.%m"))
        return _Series("MN1", ts, hi, lo, cl, ao, partial=partial)

    # Рабочий этаж и все младшие этажи режем по НАЧАЛУ рабочей свечи,
    # а не по точному времени входа. Метка D1-бара — 00:00; вход в 14:00
    # не даёт права читать High/Low всей этой дневной свечи.
    rank, work_rank = _TF_ORDER.get(tf), _TF_ORDER.get(working_tf)
    if rank is None or work_rank is None or rank >= work_rank:
        try:
            cutoff = _period_bounds(working_tf, when)[0]
        except Exception:
            cutoff = when
        end = bisect_left(base.t, cutoff)
        return _cut(base, end, tf)

    # Старший этаж: закрытая история + родительский бар,
    # агрегированный только из младших баров до границы входа.
    child_tf = _CHILD_TF.get(tf)
    if not child_tf:
        try:
            cutoff = _period_bounds(working_tf, when)[0]
        except Exception:
            cutoff = when
        end = bisect_left(base.t, cutoff)
        return _cut(base, end, tf)
    child = _series(symbol, child_tf, when, cache, working_tf)
    period_start, period_end = _period_bounds(tf, when)
    parent_end = bisect_left(base.t, period_start)
    ts, hi, lo, cl = (list(base.t[:parent_end]), list(base.hi[:parent_end]),
                      list(base.lo[:parent_end]), list(base.cl[:parent_end]))
    left = bisect_left(child.t, period_start)
    right = bisect_left(child.t, period_end)
    if right > left:
        ts.append(period_start)  # временная метка агрегированной свечи — начало месяца
        hi.append(max(child.hi[left:right]))
        lo.append(min(child.lo[left:right]))
        cl.append(child.cl[right - 1])
    from williams_core import compute_ao_series
    ao = list(compute_ao_series(hi, lo)) if hi else []
    return _Series(tf, ts, hi, lo, cl, ao, partial=right > left)

def _month(s):
    return str(s or "")[:7]


def _anchor(L, anchor_date, up, anchor_price=None):
    """Ноль MN1 — фактический экстремум из истории старшего хода.

    «с» — месяц, с которого наблюдается ход; это НЕ обязательно дата
    его фактического начала. hod_mesyaca._urovni() отдельно сохраняет
    начало_дата и начало_цена — экстремум за весь период от «с» до бара.
    Для MN1 выбираем месяц фактического экстремума, а не месяц начала
    наблюдения. Цена берётся из истории, если она сохранена.
    """
    d = _date(anchor_date)
    month = d.strftime("%Y.%m") if d is not None else _month(anchor_date)
    ids = [i for i, t in enumerate(L.t) if t.strftime("%Y.%m") == month]
    if not ids:
        return None
    i = ids[0]
    try:
        price = float(anchor_price) if anchor_price is not None else None
    except (TypeError, ValueError):
        price = None
    if up:
        return i, "L", price if price is not None else float(L.lo[i])
    return i, "H", price if price is not None else float(L.hi[i])


def _chain_from_canon(L, start, end, up, zero_price=None):
    """Строит цепочку через тот же zigzag, что и анализ сделки D03."""
    from volny_kanon import fraktaly_kniga, _zigzag

    if start is None or end is None or end <= start:
        return [], False

    # Ориентируем цены так, чтобы направление родительского участка
    # всегда было «вверх». Это ровно преобразование _Lenta.storona().
    if up:
        K, N = L.hi, L.lo
        start_side = "L"
        start_price = float(zero_price) if zero_price is not None else float(L.lo[start])
    else:
        K = [-float(x) for x in L.lo]
        N = [-float(x) for x in L.hi]
        start_side = "H"
        start_price = float(zero_price) if zero_price is not None else float(L.hi[start])

    vf, nf = fraktaly_kniga(K, N, end)

    # Оба плеча пятибарного фрактала должны находиться внутри участка.
    # Внешние фракталы не могут влиять на цепочку дочернего сегмента.
    vf = {i for i in vf if start + 2 <= i <= end - 2}
    nf = {i for i in nf if start + 2 <= i <= end - 2}

    zigzag = _zigzag(K, N, vf, nf, start, end)
    points = [{"i": start, "side": start_side, "price": start_price,
               "confirmed": False, "zero": True}]

    # _zigzag начинает с нижней стороны ориентированного хода ("n").
    # Если первая точка сместилась, канон продлил начало: ноль пробит.
    # Сохраняем прежнее поведение карты — не строим цепочку за пробитым нулём.
    if not zigzag or zigzag[0][0] != start:
        return points, True

    for i, vid in zigzag[1:]:
        if up:
            side = "H" if vid == "v" else "L"
        else:
            side = "L" if vid == "v" else "H"
        price = float(L.hi[i] if side == "H" else L.lo[i])
        points.append({"i": i, "side": side, "price": price,
                       "confirmed": True})

    return points, False


def _chain(L, start, end, up, zero_price=None):
    """Цепочка подтверждённых фракталов от фактической нулевой цены."""
    return _chain_from_canon(L, start, end, up, zero_price)


def _segments(L, points, end, include_live_close=True):
    # KARTA_HOD_V2: последний перелом, который цена потом прошла в его же
    # сторону (вершину — выше, впадину — ниже), уже не перелом: ход
    # продолжился, считаем от предыдущей точки до нового края.
    points = list(points)
    while len(points) > 1 and end > points[-1]["i"]:
        p = points[-1]
        rng = range(p["i"] + 1, end + 1)
        if p["side"] == "H" and any(L.hi[j] > p["price"] for j in rng):
            points.pop()
        elif p["side"] == "L" and any(L.lo[j] < p["price"] for j in rng):
            points.pop()
        else:
            break
    out = []
    for a, b in zip(points, points[1:]):
        direction = "вверх" if b["price"] > a["price"] else "вниз"
        out.append({"a": a["i"], "b": b["i"], "from": a["price"],
                    "to": b["price"], "direction": direction,
                    "confirmed": bool(b.get("confirmed")),
                    "start": L.t[a["i"]], "finish": L.t[b["i"]]})
    if points and end > points[-1]["i"]:
        last = points[-1]
        lo, hi = last["i"], end + 1
        if last["side"] == "H":
            i = min(range(lo, hi), key=lambda j: L.lo[j])
            price = float(L.lo[i])
        else:
            i = max(range(lo, hi), key=lambda j: L.hi[j])
            price = float(L.hi[i])
        if i > last["i"] and price != last["price"]:
            direction = "вверх" if price > last["price"] else "вниз"
            out.append({"a": last["i"], "b": i, "from": last["price"],
                        "to": price, "direction": direction,
                        "confirmed": False, "start": L.t[last["i"]],
                        "finish": L.t[i], "live": True, "i_end": i == end})   # KARTA_HOD_V1
        # После экстремума показываем и незавершённое движение к последнему
        # закрытому бару. Иначе карта застревает на старом краю.
        if include_live_close:
            close = float(L.cl[end])
            if close != price:
                direction = "вверх" if close > price else "вниз"
                out.append({"a": i, "b": end, "from": price,
                            "to": close, "direction": direction,
                            "confirmed": False, "start": L.t[i],
                            "finish": L.t[end], "live": True, "live_close": True})
    for s in out:
        vals = [abs(float(L.ao[j])) for j in range(s["a"], s["b"] + 1)
                if j < len(L.ao) and L.ao[j] is not None]
        s["ao_peak"] = max(vals) if vals else None
        s["bars"] = max(0, s["b"] - s["a"])
    return out


def _label_segments(segments, trend):
    counter = 0
    previous_impulse = None
    for s in segments:
        s["relation"] = "по старшему ходу" if s["direction"] == trend else "против старшего хода"
        s["pullback_no"] = None
        s["retracement_pct"] = None
        size = abs(s["to"] - s["from"])
        if s["direction"] == trend:
            previous_impulse = size
        else:
            if s["confirmed"]:
                counter += 1
                s["pullback_no"] = counter
            else:
                s["candidate_pullback_no"] = counter + 1
            if previous_impulse and previous_impulse > 0:
                s["retracement_pct"] = size / previous_impulse * 100
    return segments


def _at(segments, when, allow_prior=False):
    if not segments or when is None:
        return None
    # При совпадении границ выбираем более новый (внутренний) участок.
    # KARTA_HOD_V1: шевеление внутри одной свечи (от края к закрытию той же
    # свечи) — не участок: активным остаётся сам ход до формирующегося края.
    zhivye = [s for s in segments
              if not (s.get("live_close") and s.get("bars") == 0)] or segments
    for s in reversed(zhivye):
        if s["start"] <= when <= s["finish"]:
            return s
    last = zhivye[-1]
    # Снимок на входе уже обрезан до входной свечи. Поэтому последний
    # доступный участок — именно известный контекст, даже если его дата
    # на один или несколько торговых баров раньше времени входа.
    if allow_prior and when >= last["finish"]:
        return last
    # Время входа может быть позже временной метки последнего бара,
    # но относиться к той же календарной свече.
    if when.date() == last["finish"].date() and when >= last["finish"]:
        return last
    # Для снимка «сейчас» не выдаём старый участок за активный после разрыва.
    return None


def _vnutri_svechi(snap) -> str:
    """KARTA_HOD_V1: движение внутри текущей свечи — отдельной припиской."""
    try:
        segs = (snap or {}).get("segments") or []
        s = segs[-1] if segs else None
        if not (s and s.get("live_close") and s.get("bars") == 0):
            return ""
        hod = next((x for x in reversed(segs[:-1]) if x.get("live")), None)
        pct = (abs(s["to"] - s["from"]) / abs(hod["to"] - hod["from"]) * 100
               if hod and hod["to"] != hod["from"] else None)
        return (f"; внутри текущей свечи цена отошла от края {s['from']:.5f} к "
                f"{s['to']:.5f}" + (f" ({pct:.0f}% хода)" if pct is not None else "")
                + " — это движение внутри одного бара, не участок")
    except Exception:
        return ""


def _fmt_seg(L, s, parent=None):
    if not s:
        return "участок не определён"
    rel = s["relation"]
    if parent:
        rel += (" · по родительскому участку" if s["direction"] == parent["direction"]
                else " · против родительского участка")
    tail = " · формируется, край не подтверждён" if not s["confirmed"] else ""
    if s.get("pullback_no"):
        rel += f" · противоход №{s['pullback_no']}"
    elif s.get("candidate_pullback_no"):
        rel += f" · возможный противоход №{s['candidate_pullback_no']} (ещё не подтверждён)"
    retr = (f" · возврат {s['retracement_pct']:.0f}% предыдущего попутного участка"
            if s.get("retracement_pct") is not None else "")
    ao = f" · пик |AO| {s['ao_peak']:.5f}" if s.get("ao_peak") is not None else ""
    duration = ("внутри одного бара" if s.get("bars") == 0 and s.get("live_close")
                else f"{s['bars']} баров")
    return (f"{s['start']:%Y.%m.%d} → {s['finish']:%Y.%m.%d}: "
            f"{s['from']:.5f} → {s['to']:.5f}; {rel}{retr} · {duration}{ao}{tail}")


def _snapshot(symbol, tf, anchor_date, up, when, cache=None, working_tf="D1",
              anchor_price=None):
    L = _series(symbol, tf, when, cache, working_tf)
    end = len(L.t) - 1
    if end < 5:
        return None
    anchor = _anchor(L, anchor_date, up, anchor_price)
    if not anchor:
        return None
    start, _side, zero_price = anchor
    if start >= end:
        return None
    points, broken = _chain(L, start, end, up, zero_price)
    if up:
        broken = broken or any(L.lo[i] < zero_price for i in range(start + 1, end + 1))
    else:
        broken = broken or any(L.hi[i] > zero_price for i in range(start + 1, end + 1))
    segs = _label_segments(_segments(L, points, end), "вверх" if up else "вниз")
    return {"L": L, "start": start, "zero": zero_price, "points": points,
            "segments": segs, "broken": broken, "end": end}


def _child_period(child, parent_time, parent_tf):
    """Индексы баров дочернего этажа внутри одного родительского бара."""
    if parent_tf == "MN1":
        lo = parent_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if lo.month == 12:
            hi = lo.replace(year=lo.year + 1, month=1)
        else:
            hi = lo.replace(month=lo.month + 1)
    elif parent_tf == "D1":
        lo = datetime(parent_time.year, parent_time.month, parent_time.day)
        hi = lo + timedelta(days=1)
    else:
        raise ValueError(f"Неизвестный родительский этаж: {parent_tf}")
    return bisect_left(child.t, lo), bisect_left(child.t, hi)


def _map_pivot(parent, parent_i, side, child, parent_tf, live_end=False):
    """Переносит только ценовой экстремум родительского бара на младший этаж.

    Для MN1 ищется экстремум среди D1-баров этого месяца; для D1 —
    среди H4-баров этого дня. Время открытия свечи не принимается за
    время самого экстремума.
    """
    if parent_i is None or parent_i < 0 or parent_i >= len(parent.t):
        return None
    left, right = _child_period(child, parent.t[parent_i], parent_tf)
    if right <= left:
        return None
    ids = range(left, right)
    # Конец незавершённого родительского участка — последний доступный
    # дочерний бар, а не максимум/минимум всей родительской свечи.
    if live_end:
        return right - 1
    if side == "L":
        return min(ids, key=lambda i: (float(child.lo[i]), i))
    return max(ids, key=lambda i: (float(child.hi[i]), -i))


def _chain_window(L, start, end, up):
    """Цепочка канонических фракталов строго внутри [start, end]."""
    return _chain_from_canon(L, start, end, up)


def _nested_segments(symbol, parent_L, parent_seg, parent_tf, child_tf,
                     when=None, cache=None, label_trend=None, working_tf="D1"):
    """Пересчитывает дочернюю структуру заново внутри одного сегмента родителя."""
    if not parent_L or not parent_seg:
        return None
    try:
        child = _series(symbol, child_tf, when, cache, working_tf)
    except Exception as e:
        return {"L": None, "segments": [], "broken": False, "error": str(e)}
    direction = parent_seg["direction"]
    up = direction == "вверх"
    start_side, finish_side = (("L", "H") if up else ("H", "L"))
    start_i = _map_pivot(parent_L, parent_seg["a"], start_side, child, parent_tf)
    finish_i = _map_pivot(parent_L, parent_seg["b"], finish_side, child, parent_tf,
                           live_end=bool(parent_seg.get("live_close") or parent_seg.get("i_end")))
    if start_i is None:
        return {"L": child, "segments": [], "broken": False,
                "error": f"не найдена дочерняя свеча для начала родителя ({child_tf})"}
    if finish_i is None:
        return {"L": child, "segments": [], "broken": False,
                "error": f"не найдена дочерняя свеча для конца родителя ({child_tf})"}
    if finish_i == start_i:
        return {"L": child, "segments": [], "broken": False,
                "error": (f"обе границы родителя попали в одну свечу {child_tf}; "
                          "порядок экстремумов внутри неё неизвестен")}
    if finish_i < start_i:
        return {"L": child, "segments": [], "broken": False,
                "error": (f"конец родителя сопоставлен раньше начала на {child_tf}; "
                          "вложенный участок не строю")}
    points, broken = _chain_window(child, start_i, finish_i, up)
    trend = label_trend or direction
    segments = _label_segments(
        _segments(child, points, finish_i,
                  include_live_close=bool(parent_seg.get('live_close') or parent_seg.get('i_end'))), trend)
    return {"L": child, "segments": segments, "broken": broken,
            "start": start_i, "end": finish_i, "error": None}


def _d1_h4_lines(symbol, d1_snap, mn1_parent, when, cache, active_d1, side, working_tf="D1"):
    """Кратко показывает H4 только внутри выбранного активного D1-сегмента."""
    if not d1_snap or not d1_snap.get("L"):
        return ["H4: D1-родитель не определён."], None, None
    if not active_d1:
        return ["H4: активный D1-участок не определён — вложенность не назначаю."], None, None

    h4 = _nested_segments(symbol, d1_snap["L"], active_d1, "D1", "H4",
                          when=when, cache=cache,
                          label_trend=active_d1["direction"], working_tf=working_tf)
    if h4 is None:
        return ["H4: дочерний участок не определён."], None, None
    if h4.get("error"):
        return ["H4: " + h4["error"] + "."], None, h4

    hs = h4.get("segments") or []
    if h4.get("broken"):
        lines = ["H4: ноль дочерней структуры нарушен; активный участок не назначаю."]
        if hs:
            lines.append("Последний рассчитанный H4 (только геометрия): "
                         + _fmt_seg(h4["L"], hs[-1], active_d1))
        return lines, None, h4
    if not hs:
        return ["H4: внутри выбранного D1 пока нет различимого участка."], None, h4

    active_time = when
    if active_time is None and h4.get("L") is not None:
        active_time = h4["L"].t[h4["end"]]
    active_h4 = _at(hs, active_time, allow_prior=when is not None)
    lines = []
    if h4.get("broken"):
        lines.append("H4: ноль дочерней структуры нарушен; участок ниже показан только как наблюдаемая геометрия.")
    if active_h4:
        lines.append("H4 внутри выбранного D1: " + _fmt_seg(h4["L"], active_h4, active_d1))
        rel = "по H4-участку" if active_h4["direction"] == side else "против H4-участка"
        lines.append(f"Сторона позиции {side} — {rel}.")
    else:
        lines.append("H4: на момент среза активный участок не установлен; последний рассчитанный: "
                     + _fmt_seg(h4["L"], hs[-1], active_d1))
    return lines, active_h4, h4


def _istoriya_na_vhod(ya, entry):
    """Восстанавливает слова старшего хода, известные до входной свечи.

    Текущая запись может быть результатом более поздних пересмотров.
    Идём по журналу назад и возвращаем состояние до событий даты входа.
    Если дата первого появления истории не сохранена или она не раньше
    входа, прошлое состояние нельзя доказать — возвращаем отказ.
    """
    current = (ya or {}).get("история") or {}
    created = _date(current.get("создана"))
    if created is None or created.date() >= entry.date():
        return None
    state = dict(current)
    for event in reversed((ya or {}).get("журнал") or []):
        event_time = _date(event.get("бар"))
        if event_time is None:
            return None
        # Дневная свеча входа исключена целиком: события её даты
        # не должны менять картину, доступную на входе.
        if event_time.date() >= entry.date():
            before = event.get("было")
            if not isinstance(before, dict) or not before:
                return None
            for key in ("ход", "делает", "с"):
                if key in before:
                    state[key] = before[key]
    return state


def blok(symbol, poz, rabochiy="D1"):
    """Наблюдательная цепочка MN1 → D1 → H4; не торговый сигнал."""
    try:
        import hod_mesyaca as hm
        slot = str((poz or {}).get("trader") or "").upper()
        if slot != "D03":
            return ""
        ya = hm._yashchik_chitat(slot, symbol)
        ist = (ya.get("история") or {})
        trend = str(ist.get("ход") or "")
        anchor_date = ist.get("начало_дата") or ist.get("с")
        anchor_price = ist.get("начало_цена")
        entry = _date((poz or {}).get("opened_at"))
        working_tf = str((poz or {}).get("timeframe") or rabochiy or "D1").upper()
        if entry is None:
            return "ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: время входа не разобрано."
        current_history_valid = trend in ("вверх", "вниз") and bool(anchor_date)

        # Отдельно восстанавливаем слова старшего хода на дату входа.
        # Уровни точки ноль пересчитываем только по барам ДО входной даты.
        entry_ist = _istoriya_na_vhod(ya, entry)
        if not entry_ist:
            return ("ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: исходную историю на дату входа "
                    "доказательно восстановить нельзя (нет даты создания или полного журнала). "
                    "Снимок не подменяю нынешней историей.")
        entry_trend = str(entry_ist.get("ход") or "")
        entry_start = str(entry_ist.get("с") or "")
        if entry_trend not in ("вверх", "вниз") or not entry_start:
            return ("ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: на дату входа нет подтверждённого "
                    "направления и начала старшего хода.")
        entry_levels = hm._urovni(symbol, entry_trend, entry_start, entry, working_tf)
        if not entry_levels:
            return ("ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: точку ноль на дату входа "
                    "не удалось восстановить по барам до входной свечи.")
        entry_anchor_date = entry_levels.get("начало_дата")
        entry_anchor_price = entry_levels.get("начало_цена")
        if not entry_anchor_date or entry_anchor_price is None:
            return ("ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: историческая точка ноль "
                    "неполная; снимок не строю.")
        up = trend == "вверх"
        entry_up = entry_trend == "вверх"

        # В тестере есть два независимых указателя времени:
        # текущий бар рынка и курсор машины времени (feed.мoment).
        # feed_source сначала режет CSV машинным курсором, поэтому более
        # поздняя отметка рынка не вернёт уже отрезанные бары.
        try:
            from feed_source import get_feed_mode
            _tester_mode = (get_feed_mode() or {}).get("mode") == "tester"
        except Exception:
            _tester_mode = False

        try:
            from volny_kanon import _bar_goroda
            _market_mark = _bar_goroda()
        except Exception:
            _market_mark = ""
        _market_cutoff = _date(_market_mark)

        _machine_cutoff = None
        if _tester_mode:
            try:
                import istoriya
                _machine_cutoff = _date(istoriya.gde_stoim())
            except Exception:
                pass

        if _tester_mode and _machine_cutoff is not None and _machine_cutoff < entry:
            return (
                "ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: машина времени ограничивает "
                f"источник датой {_machine_cutoff:%Y.%m.%d %H:%M}, что раньше "
                f"входа {entry:%Y.%m.%d %H:%M}. Снимок на момент входа "
                "по доступным данным восстановить нельзя."
            )
        if _market_cutoff is not None and _market_cutoff < entry:
            return (
                "ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: отметка текущего бара рынка "
                f"{_market_cutoff:%Y.%m.%d %H:%M} раньше времени входа "
                f"{entry:%Y.%m.%d %H:%M}. Источник не содержит данных до входа."
            )

        current_cutoff_machine_limited = False
        current_cutoff_fallback = False
        if (_tester_mode and _machine_cutoff is not None
                and (_market_cutoff is None or _machine_cutoff < _market_cutoff)):
            current_cutoff = _machine_cutoff
            current_cutoff_machine_limited = True
        else:
            current_cutoff = _market_cutoff or _machine_cutoff

        if current_cutoff is None:
            # Без временной отметки безопаснее показать снимок на входе,
            # чем случайно прочитать будущие бары из полного CSV.
            current_cutoff = entry
            current_cutoff_fallback = True

        cache_entry, cache_now = {}, {}
        at_m = _snapshot(symbol, "MN1", entry_anchor_date, entry_up, entry, cache_entry,
                         working_tf, entry_anchor_price)
        now_m = (_snapshot(symbol, "MN1", anchor_date, up, current_cutoff, cache_now,
                           working_tf, anchor_price) if current_history_valid else None)
        if not at_m:
            return ("ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4: данных от исторической месячной точки ноль "
                    "на входе недостаточно; входную структуру не устанавливаю.")

        # Текущая история могла законно смениться на «нет хода» или потерять
        # подтверждённую точку ноль. Это не должно стирать доказуемый снимок входа.
        if not now_m:
            entry_parent = (None if at_m["broken"] else
                            _at(at_m["segments"], entry, allow_prior=True))
            entry_d1 = _nested_segments(symbol, at_m["L"], entry_parent, "MN1", "D1",
                                        when=entry, cache=cache_entry,
                                        label_trend=entry_trend, working_tf=working_tf)
            entry_d1_segments = (entry_d1 or {}).get("segments") or []
            entry_child = (None if (entry_d1 or {}).get("broken") else
                           _at(entry_d1_segments, entry, allow_prior=True))
            side = ("вверх" if str((poz or {}).get("direction") or "").upper() == "LONG"
                    else "вниз")
            entry_relation = ("по движению участка" if entry_parent and entry_parent["direction"] == side
                              else "против движения участка" if entry_parent else "не определено")
            entry_d1_relation = ("по D1-участку" if entry_child and entry_child["direction"] == side
                                 else "против D1-участка" if entry_child else "не определено")
            lines = [
                f"=== ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4 · рабочий ТФ {working_tf} ===",
                f"Снимок на входе: {entry:%Y.%m.%d %H:%M}; входная свеча {working_tf} исключена.",
                "",
                "НА ВХОДЕ — одна ветка вложенности:",
                "  MN1: " + _fmt_seg(at_m["L"], entry_parent) + _vnutri_svechi(at_m),
                "  D1 внутри этого MN1: " + _fmt_seg((entry_d1 or {}).get("L"), entry_child, entry_parent),
            ]
            entry_h4_lines, _, _ = _d1_h4_lines(
                symbol, entry_d1, entry_parent, entry, cache_entry, entry_child, side, working_tf)
            lines.extend("  " + x for x in entry_h4_lines)
            lines.append(f"  Позиция {side}: MN1 — {entry_relation}; D1 — {entry_d1_relation}.")
            lines.append("")
            lines.append("СЕЙЧАС: текущий старший ход не имеет подтверждённого направления/точки ноль "
                         "либо для текущего среза недостаточно данных. Текущую структуру не додумываю.")
            lines.append("Карта ничего не приказывает.")
            return "\n".join(lines)

        # Если ноль MN1 пройден или цепочка не подтверждена, не назначаем
        # активного родителя и не строим от него дочерние этажи.
        entry_parent = (None if at_m["broken"] else
                        _at(at_m["segments"], entry, allow_prior=True))
        current_time = current_cutoff or now_m["L"].t[now_m["end"]]
        current_parent = (None if now_m["broken"] else
                          _at(now_m["segments"], current_time, allow_prior=current_cutoff is not None))
        side = ("вверх" if str((poz or {}).get("direction") or "").upper() == "LONG"
                else "вниз")

        # D1 не строится от месячной точки ноль: он заново считается
        # внутри границ конкретного MN1-сегмента.
        entry_d1 = _nested_segments(symbol, at_m["L"], entry_parent, "MN1", "D1",
                                    when=entry, cache=cache_entry, label_trend=entry_trend, working_tf=working_tf)
        current_d1 = _nested_segments(symbol, now_m["L"], current_parent, "MN1", "D1",
                                      when=current_cutoff, cache=cache_now, label_trend=trend, working_tf=working_tf)
        entry_d1_segments = (entry_d1 or {}).get("segments") or []
        current_d1_segments = (current_d1 or {}).get("segments") or []
        entry_child = (None if (entry_d1 or {}).get("broken") else
                       _at(entry_d1_segments, entry, allow_prior=True))
        current_child = (None if (current_d1 or {}).get("broken") else
                         _at(current_d1_segments, current_time, allow_prior=current_cutoff is not None))

        entry_relation = ("по движению участка" if entry_parent and entry_parent["direction"] == side
                          else "против движения участка" if entry_parent else "не определено")
        current_relation = ("по движению участка" if current_parent and current_parent["direction"] == side
                            else "против движения участка" if current_parent else "не определено")
        entry_d1_relation = ("по D1-участку" if entry_child and entry_child["direction"] == side
                             else "против D1-участка" if entry_child else "не определено")
        current_d1_relation = ("по D1-участку" if current_child and current_child["direction"] == side
                               else "против D1-участка" if current_child else "не определено")

        lines = [
            f"=== ВЛОЖЕННАЯ КАРТА MN1 → D1 → H4 · рабочий ТФ {working_tf} ===",
            f"Снимок на входе: {entry:%Y.%m.%d %H:%M}; входная свеча {working_tf} исключена.",
            (f"Снимок сейчас: до {current_cutoff:%Y.%m.%d %H:%M} (ограничение машины времени)."
             if current_cutoff_machine_limited else
             "Снимок сейчас: отметка бара недоступна, показан безопасный срез на входе."
             if current_cutoff_fallback else
             f"Снимок сейчас: до {current_cutoff:%Y.%m.%d %H:%M}; текущая свеча исключена."),
            "",
            "НА ВХОДЕ — одна ветка вложенности:",
            "  MN1: " + _fmt_seg(at_m["L"], entry_parent) + _vnutri_svechi(at_m),
            "  D1 внутри этого MN1: " + _fmt_seg((entry_d1 or {}).get("L"), entry_child, entry_parent),
        ]
        entry_h4_lines, entry_h4, entry_h4_snap = _d1_h4_lines(
            symbol, entry_d1, entry_parent, entry, cache_entry, entry_child, side, working_tf)
        lines.extend("  " + x for x in entry_h4_lines)
        lines.append(f"  Позиция {side}: MN1 — {entry_relation}; D1 — {entry_d1_relation}.")

        lines.extend([
            "",
            "СЕЙЧАС — та же вложенная ветка на текущем срезе:",
            "  MN1: " + _fmt_seg(now_m["L"], current_parent) + _vnutri_svechi(now_m),
            "  D1 внутри этого MN1: " + _fmt_seg((current_d1 or {}).get("L"), current_child, current_parent),
        ])
        current_h4_lines, current_h4, current_h4_snap = _d1_h4_lines(
            symbol, current_d1, current_parent, current_cutoff, cache_now, current_child, side, working_tf)
        lines.extend("  " + x for x in current_h4_lines)
        lines.append(f"  Позиция {side}: MN1 — {current_relation}; D1 — {current_d1_relation}.")

        # Нарушенные нули и несопоставленные границы — отдельные статусы,
        # а не примечания в конце длинного описания.
        statuses = []
        if at_m["broken"]:
            statuses.append("на входе MN1: исходный ноль пройден; родительская структура требует переоценки")
        if now_m["broken"]:
            statuses.append("сейчас MN1: исходный ноль пройден; текущая родительская структура не подтверждена")
        if entry_d1 and entry_d1.get("broken"):
            statuses.append("на входе D1: дочерняя цепочка не начинается от границы MN1")
        if current_d1 and current_d1.get("broken"):
            statuses.append("сейчас D1: дочерняя цепочка не начинается от границы MN1")
        if entry_h4_snap and entry_h4_snap.get("broken"):
            statuses.append("на входе H4: дочерняя цепочка не начинается от границы D1")
        if current_h4_snap and current_h4_snap.get("broken"):
            statuses.append("сейчас H4: дочерняя цепочка не начинается от границы D1")
        for label, snap in (("на входе D1", entry_d1), ("сейчас D1", current_d1),
                            ("на входе H4", entry_h4_snap), ("сейчас H4", current_h4_snap)):
            if snap and snap.get("error"):
                statuses.append(f"{label}: {snap['error']}")
        if statuses:
            lines.append("")
            lines.append("СТАТУСЫ СТРУКТУРЫ:")
            lines.extend("  НЕ ПОДТВЕРЖДЕНО: " + x + "." for x in statuses)

        if entry_parent and entry_parent.get("pullback_no"):
            lines.append(f"На входе MN1 — подтверждённый противоход №{entry_parent['pullback_no']}.")
        elif entry_parent and entry_parent.get("candidate_pullback_no"):
            lines.append(f"На входе MN1 — возможный противоход №{entry_parent['candidate_pullback_no']}, поворот ещё не подтверждён.")
        lines.append("Границы H4 действуют только внутри своего D1; границы D1 — только внутри своего MN1.")
        lines.append("Карта ничего не приказывает.")
        return "\n".join(lines)
    except Exception as e:
        print(f"[ВЛОЖЕННАЯ КАРТА] не посчиталась ({e})")
        return ""


# KARTA_HOD_V1 - marker


# KARTA_HOD_V2 - marker
