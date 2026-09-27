# -*- coding: utf-8 -*-
# RASTYAZHKA_V1
"""
РАСТЯЖКА — показать НУЖНУЮ волну так, чтобы её было видно.

СЛОВА ШЕФА
    «Коррекция созрела — видно, когда саму коррекцию растянешь, весь
    зигзаг на 100-140 баров... И вот волну С от начала до конца в
    диапазон 100-140 вписываешь — и видно совсем хорошо: 3-я волна,
    AO самый, дивергенция, разворотник.»

    «Не всегда ровно по ТФ и ровно количество — поэтому и визуал, и
    математика.»

ЗАКОН ЭТОГО ФАЙЛА
    Растягивает то, что НАЗВАЛИ, и показывает. Не ищет волн, не
    размечает, не советует. Где начало объекта и где конец — говорит
    трейдер: он смотрит, потом считает, а не наоборот.

    Этаж подбирается арифметикой: сколько в куске времени, поделить
    на 120 — вот минут на бар, берём ближайшую ступень лесенки. Ровно
    не выйдет почти никогда, и это нормально: окончательно судит глаз.
"""
from __future__ import annotations

import sys as _sys
from datetime import datetime, timedelta
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

CEL_BAROV = 120          # середина окна 100-140
POLE = 0.15              # поле слева и справа, чтобы видеть подход и выход


def _vremya(s: str):
    import istoriya
    return istoriya.kak_vremya(s)


def podobrat_etazh(minut_v_kuske: float) -> str:
    """Какой этаж растянет кусок примерно на 120 баров."""
    import masshtab
    if minut_v_kuske <= 0:
        return "H4"
    nado = minut_v_kuske / CEL_BAROV
    luchshiy, raznica = "H4", None
    for tf in masshtab.LESTNICA:
        m = masshtab.minut(tf)
        if not m:
            continue
        r = abs(m - nado) / max(m, nado)
        if raznica is None or r < raznica:
            luchshiy, raznica = tf, r
    return luchshiy



# ═══ ETAZH_V_BARAH_V1 ═══
# Календарь врёт: между двумя датами лежат выходные и праздники, а
# рынок в них стоит. Считаем бары краном — единственная честная мера.

def _barov_v_okne(symbol: str, etazh: str, t1, t2):
    """Сколько баров этажа РЕАЛЬНО легло между t1 и t2. None — не дали."""
    import masshtab
    from feed_source import bars as _bars
    m = masshtab.minut(etazh) or 60
    kalendar = max(1.0, (t2 - t1).total_seconds() / 60.0)
    # глубина запроса — по календарю С ЗАПАСОМ: реальных баров всегда
    # МЕНЬШЕ календарных, так что промахнуться можно только в плюс.
    glubina = int(kalendar / m) + 200
    try:
        _probniki, _ = _bars(symbol, etazh, 5)
        if _probniki:
            _posledniy = _vremya(_probniki[-1].get("date", ""))
            if _posledniy and _posledniy > t2:
                glubina += int((_posledniy - t2).total_seconds() / 60 / m)
    except Exception:
        pass
    glubina = max(300, min(glubina, 20000))
    try:
        bs, _ = _bars(symbol, etazh, glubina)
    except Exception:
        return None
    if not bs:
        return None
    n = 0
    for b in bs:
        t = _vremya(b.get("date", ""))
        if t and t1 <= t <= t2:
            n += 1
    return n


def podobrat_etazh_po_baram(symbol: str, t1, t2, nachalnyy: str = ""):
    """Этаж, на котором кусок ЛЯЖЕТ в окно 100-140 баров, и сколько их.

    Возвращает (этаж, баров). Баров None — кран промолчал, тогда
    этаж выбран по старой календарной прикидке, и это честно видно.
    """
    import masshtab
    kalendar = max(1.0, (t2 - t1).total_seconds() / 60.0)
    etazh = (nachalnyy or "").strip().upper()
    if not masshtab.est(etazh):
        etazh = podobrat_etazh(kalendar)   # только первая прикидка
    nizhe, verhe = masshtab.OKNO
    videnye, barov = set(), None
    for _ in range(4):
        if etazh in videnye:
            break
        videnye.add(etazh)
        n = _barov_v_okne(symbol, etazh, t1, t2)
        if not n:
            break
        barov = n
        if nizhe <= n <= verhe:
            break
        # настоящее ТОРГОВОЕ время куска — из настоящих баров
        torgovye = n * (masshtab.minut(etazh) or 60)
        sled = podobrat_etazh(torgovye)
        if not masshtab.est(sled) or sled == etazh:
            break
        etazh = sled
    return etazh, barov


def rastyanut(symbol: str, s_kogda: str, po_kogda: str = "",
              etazh_podskazka: str = "") -> dict:
    """Растянуть кусок и нарисовать его.

    Возвращает {этаж, баров, кадр, с, по, пояснение}. Кадра нет —
    в «кадр» будет None, а в «пояснение» причина.
    """
    import masshtab
    from feed_source import bars as _bars
    import grafik

    t1 = _vremya(s_kogda)
    t2 = _vremya(po_kogda) if po_kogda else None
    if t1 is None:
        return {"кадр": None,
                "пояснение": f"не понял дату «{s_kogda}» "
                             f"(жду вид 2025.05.05 20:00)"}
    if t2 is None:
        t2 = datetime.now()
    if t2 < t1:
        t1, t2 = t2, t1

    minut = max(1.0, (t2 - t1).total_seconds() / 60.0)
    etazh = (etazh_podskazka or "").strip().upper()
    # ETAZH_V_BARAH_V1: этаж и длина куска — СЧИТАННЫЕ бары, не календарь.
    # Подсказка трейдера уважается: он говорит, на каком этаже смотреть,
    # мы только меряем, сколько там баров вышло.
    etazh, v_kuske = podobrat_etazh_po_baram(symbol, t1, t2, etazh)
    m = masshtab.minut(etazh) or 60
    if not v_kuske:                      # кран промолчал — старая прикидка
        v_kuske = int(minut / m)
    barov = max(60, int(v_kuske * (1 + 2 * POLE)))

    # Сколько баров назад лежит конец куска. Без этого счёта мы
    # просили у крана 400 баров и не дотягивались до прошлого года —
    # а потом МОЛЧА рисовали последние бары вместо запрошенных. Врать
    # картинкой хуже, чем отказать.
    _probniki, point = _bars(symbol, etazh, 5)
    nuzhno = max(400, barov + 60)
    if _probniki:
        _posledniy = _vremya(_probniki[-1].get("date", ""))
        if _posledniy and _posledniy > t2:
            nazad = int((_posledniy - t2).total_seconds() / 60 / m)
            nuzhno = max(nuzhno, nazad + barov + 60)

    bs, point = _bars(symbol, etazh, nuzhno)
    if not bs:
        return {"кадр": None, "этаж": etazh,
                "пояснение": f"котировок {symbol} {etazh} не дали"}

    # оставляем только бары до конца куска — «после» трейдеру видеть
    # незачем, иначе он будет смотреть в будущее
    do_konca = [b for b in bs if (_vremya(b.get("date", "")) or t1) <= t2]
    if not do_konca:
        _pervyy = bs[0].get("date", "?")
        return {"кадр": None, "этаж": etazh,
                "пояснение": (f"до {po_kogda or 'этого места'} не дотянулся: "
                              f"история {symbol} {etazh} начинается с "
                              f"{_pervyy}. Картинку не рисую, чтобы не "
                              f"показать чужой кусок.")}
    bs = do_konca[-barov:]
    if len(bs) < 30:
        return {"кадр": None, "этаж": etazh,
                "пояснение": f"на {etazh} в этом куске всего {len(bs)} "
                             f"баров — мало для картинки"}

    from williams_core import (compute_alligator, compute_ao_series,
                               detect_fractals)
    highs = [x["high"] for x in bs]
    lows = [x["low"] for x in bs]
    put = grafik.narisovat(bs, compute_alligator(highs, lows, point=point),
                           compute_ao_series(highs, lows), symbol, etazh,
                           barov=len(bs), fraktaly=detect_fractals(bs))
    return {"кадр": put, "этаж": etazh, "баров": v_kuske,
            "с": bs[0].get("date"), "по": bs[-1].get("date"),
            "пояснение": (f"кусок занял {v_kuske} баров этажа {etazh} "
                          f"(цель 100-140)")}


# RASTYAZHKA_V1 - marker

# ETAZH_V_BARAH_V1 - marker
