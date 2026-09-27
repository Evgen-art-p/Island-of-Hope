# -*- coding: utf-8 -*-
# SVERKA_DIVERA_V1
"""Считает дивер по барам — чтобы слова трейдера было с чем сверить.

Канон Шефа (17.09):
  ГОРБ — три столбика: меньше-БОЛЬШЕ-меньше.
  ЯМА  — три столбика: больше-МЕНЬШЕ-больше.
  Главный — самый большой в поле зрения, не «предыдущий по счёту».

Город СЧИТАЕТ и ПОКАЗЫВАЕТ. Решает трейдер. Здесь нет ни одного
запрета — только числа.
"""

from typing import Optional

BAROV = 140          # столько же, сколько видно на кадре


def gorby(ao: list) -> list:
    """Места и высоты горбов: средний столбик выше обоих соседей."""
    out = []
    for i in range(1, len(ao) - 1):
        a, b, c = ao[i - 1], ao[i], ao[i + 1]
        if a is None or b is None or c is None:
            continue
        if b > a and b > c:
            out.append((i, b))
    return out


def yamy(ao: list) -> list:
    """Места и глубины ям: средний столбик ниже обоих соседей."""
    out = []
    for i in range(1, len(ao) - 1):
        a, b, c = ao[i - 1], ao[i], ao[i + 1]
        if a is None or b is None or c is None:
            continue
        if b < a and b < c:
            out.append((i, b))
    return out


def poschitat(symbol: str, timeframe: str, storona: str) -> dict:
    """Дивер по числам. storona: SHORT — по вершинам, LONG — по впадинам.

    Возвращает {"ok", "est", "slovami", "почему"}.
    ok=False — посчитать не вышло, и это НЕ приговор трейдеру.
    """
    try:
        import sys as _s
        from pathlib import Path as _P
        _p = str(_P(__file__).resolve().parent)
        if _p not in _s.path:
            _s.path.insert(0, _p)
        from feed_source import bars as _bars
        from williams_core import compute_ao_series
    except Exception as e:
        return {"ok": False, "est": None, "slovami": f"нет счёта ({e})"}

    try:
        b, _point = _bars(symbol, timeframe, BAROV + 60)
    except Exception as e:
        return {"ok": False, "est": None, "slovami": f"нет баров ({e})"}
    if not b or len(b) < 60:
        return {"ok": False, "est": None, "slovami": "мало баров"}

    b = b[-(BAROV + 40):]
    highs = [x["high"] for x in b]
    lows = [x["low"] for x in b]
    closes = [x["close"] for x in b]
    ao = compute_ao_series(highs, lows)

    # поле зрения — последние BAROV баров, как на кадре
    n = len(ao)
    start = max(0, n - BAROV)
    vid = list(range(start, n))

    verh = str(storona).upper() == "SHORT"   # шорт — по вершинам
    tochki = gorby(ao) if verh else yamy(ao)
    tochki = [(i, v) for i, v in tochki if i in vid]
    if len(tochki) < 1:
        return {"ok": False, "est": None,
                "slovami": "горбов в поле зрения не нашлось"}

    # DVE_GORKI_V1 — слово Шефа 22.09, по кадру QV32:
    #   один импульс — это отрезок от излома до вершины, «от 0 до 100».
    #   Пока цена не вышла за 100, идёт откат того же импульса и новой
    #   волны нет. Вышла — пошла следующая, и вот тогда на AO стоят ДВЕ
    #   ГОРКИ с ямкой между ними (ямка и есть тот откат). Вторая горка
    #   ниже первой — расхождение. Вниз зеркально: две ямки, горка
    #   между ними, вторая ямка мельче. Горок нет, AO просто ползёт —
    #   сравнивать нечего: они есть этажом ниже, но мы туда не идём.
    return dve_gorki(ao, highs, lows, vid, verh, b)


def dve_gorki(ao: list, highs: list, lows: list, vid: list,
              verh: bool, b: list = None) -> dict:
    """Две горки (две ямки) по ЭКСТРЕМУМАМ, на всех размерах. verh=True — SHORT.

    DVE_GORKI_MATRYOSHKA_V1 + DVE_GORKI_YAMKA_V1 — слово Шефа 23.09: «линии должны тянуться
    по экстремумам, на цене и AO: самый экстремум AO и следующий
    меньше, и смотрим». И по его же скрину USDCNH: после отката пятая
    волна несёт СВОЙ дивер внутри — смотреть на всех размерах.

    Вниз (LONG), вверх зеркально. Одна пара:
      1-я точка AO — самый экстремум;
      откат — самый высокий бар цены после неё, он делит ход надвое;
      2-я точка AO — самое глубокое место AO после отката (если яма у
        края ещё роется — у края, и переедет глубже вместе с ней);
      цена — самый низ до отката и самый низ после него.
    Матрёшка: вторая точка пары становится первой точкой следующей,
    меньшей — и так до края. Первая пара — весь ход, последняя — край.

    Главные ключи ответа — большая пара, как и раньше. Все пары лежат в
    «пары», последняя с расхождением — в «край».
    """
    tochki = gorby(ao) if verh else yamy(ao)
    tochki = [(i, v) for i, v in tochki if i in vid]
    imya = "горка" if verh else "ямка"
    if not tochki:
        return {"ok": True, "est": False,
                "slovami": f"{'горок' if verh else 'ямок'} AO в поле "
                           "зрения нет — сравнивать нечего"}

    def _kogda(i):
        try:
            return str(b[i].get("date", ""))[:16] if b else f"бар {i}"
        except Exception:
            return f"бар {i}"

    p = None
    for _i in range(len(ao) - 1, -1, -1):
        if ao[_i] is not None:
            p = _i
            break

    def _para(g, pervaya=True):
        """Одна пара от точки g до края. Строка — пары нет, и почему."""
        a1 = ao[g]
        if p is None or p <= g + 1:
            return f"{imya} {_kogda(g)} у самого края — второй ещё нет"
        posle = range(g + 1, p + 1)
        t = (min(posle, key=lambda k: lows[k]) if verh
             else max(posle, key=lambda k: highs[k]))
        if t >= p:
            return (f"после {_kogda(g)} цена в откате до самого края — "
                    "второго края ещё нет")
        do, pos = range(g, t + 1), range(t + 1, p + 1)
        # PERVAYA_TOCHKA_CENY_V1 (слово Шефа 24.09): первая точка цены
        # — с того же места, что и горка AO. AO отстаёт от цены, так
        # что край цены — на подъёме к горке (для LONG — на спуске к
        # яме): от ямки AO слева до самой горки. Раньше окно шло до
        # отката цены и хватало чужую, более позднюю вершину.
        _s = g
        while (_s - 1 >= 0 and ao[_s - 1] is not None
               and ((ao[_s - 1] <= ao[_s]) if verh
                    else (ao[_s - 1] >= ao[_s]))):
            _s -= 1
        # PERVAYA_TOCHKA_V2: и вправо — пока AO после горки ещё
        # спускается (для LONG — поднимается), но не дальше отката
        # цены. Вершина цены бывает и ПОСЛЕ горки AO (апрель 2025).
        _e = g
        while (_e + 1 <= t and ao[_e + 1] is not None
               and ((ao[_e + 1] <= ao[_e]) if verh
                    else (ao[_e + 1] >= ao[_e]))):
            _e += 1
        # SVOI_CHISLA_V1: у тонких пар (внутри матрёшки) первая
        # точка цены — по всему отрезку от горки AO до отката:
        # иначе вершина между ними (02.02.2023) выпадала.
        do = range(_s, _e + 1) if pervaya else range(g, t + 1)
        if verh:
            ic1 = max(do, key=lambda k: highs[k])
            ic2 = max(pos, key=lambda k: highs[k])
            kray_vzyat = highs[ic2] > highs[ic1]
            c1, c2 = highs[ic1], highs[ic2]
            k2 = max(pos, key=lambda k: ao[k])
        else:
            ic1 = min(do, key=lambda k: lows[k])
            ic2 = min(pos, key=lambda k: lows[k])
            kray_vzyat = lows[ic2] < lows[ic1]
            c1, c2 = lows[ic1], lows[ic2]
            k2 = min(pos, key=lambda k: ao[k])
        # настоящая горка (ямка) или та, что ещё растёт у края; склон,
        # по которому AO просто ползёт, точкой не считается
        def _tochka(k):
            if k < p:
                return ((ao[k] > ao[k - 1] and ao[k] > ao[k + 1]) if verh
                        else (ao[k] < ao[k - 1] and ao[k] < ao[k + 1]))
            return (ao[p] > ao[p - 1]) if verh else (ao[p] < ao[p - 1])

        # DVE_GORKI_YAMKA_V1 — AO отстаёт от цены: сразу после отката он
        # ещё сползает с первой горки, и «самый высокий AO после отката»
        # оказывается на склоне. Тогда ищем ямку между горками (канон:
        # «две горки, ямка между ними») — самое глубокое место AO от
        # отката до нового края цены, а вторую горку — после неё.
        if not _tochka(k2):
            do_kraya = range(t, ic2 + 1)
            d = (min(do_kraya, key=lambda k: ao[k]) if verh
                 else max(do_kraya, key=lambda k: ao[k]))
            if d < p:
                za = range(d + 1, p + 1)
                k2 = (max(za, key=lambda k: ao[k]) if verh
                      else min(za, key=lambda k: ao[k]))
        a2 = ao[k2]
        tochka = _tochka(k2)
        if not tochka:
            return (f"после отката {_kogda(t)} AO просто ползёт — второй "
                    f"{'горки' if verh else 'ямки'} нет")
        sila_slabee = a2 < a1 if verh else a2 > a1
        u_kraya = " (ещё растёт у края)" if k2 == p else ""
        slovami = (f"{_kogda(g)}: AO {a1:.5f}, край цены {c1:.5f} → "
                   f"откат {_kogda(t)} → {_kogda(k2)}{u_kraya}: "
                   f"AO {a2:.5f}, край цены {c2:.5f}")
        prich = []
        if not kray_vzyat:
            prich.append("цена прежний край не взяла — откат ещё идёт")
        if not sila_slabee:
            prich.append("сила не слабее прежней")
        if prich:
            slovami += " · " + ", ".join(prich)
        return {"est": bool(kray_vzyat and sila_slabee), "slovami": slovami,
                "цена_было": c1, "цена_стало": c2,
                "ao_было": a1, "ao_стало": a2,
                "i_цена_1": ic1, "i_цена_2": ic2,
                "i_ao_1": g, "i_ao_2": k2}

    # матрёшка: от самого экстремума — к краю, каждая пара меньше
    g, _a = (max(tochki, key=lambda t: t[1]) if verh
             else min(tochki, key=lambda t: t[1]))
    # NOVYY_HOD_V1: прежний ход перекрыт — ищем горку в новом. Если
    # после самой высокой горки (самой глубокой ямы) цена ушла за
    # край ВСЕГО поля зрения в обратную сторону, тот ход кончен:
    # сравнивать надо внутри нового, после этого края.
    for _nh in range(6):
        _p_nh = max(i for i in range(len(ao)) if ao[i] is not None)
        _posle_nh = range(g + 1, _p_nh + 1)
        if not _posle_nh:
            break
        _k_nh = (min(_posle_nh, key=lambda k: lows[k]) if verh
                 else max(_posle_nh, key=lambda k: highs[k]))
        _do_nh = range(min(vid) if vid else 0, g + 1)
        _slom = ((lows[_k_nh] < min(lows[k] for k in _do_nh)) if verh
                 else (highs[_k_nh] > max(highs[k] for k in _do_nh)))
        if not _slom:
            break
        _ost_nh = [(i, v) for i, v in tochki if i > _k_nh]
        if not _ost_nh:
            return {"ok": True, "est": False,
                    "slovami": ("прежний ход перекрыт: цена ушла за край "
                                "всего поля зрения — в новом ходу "
                                + ("горок" if verh else "ямок")
                                + " ещё нет"),
                    "пары": [], "край": None}
        g, _a = (max(_ost_nh, key=lambda t: t[1]) if verh
                 else min(_ost_nh, key=lambda t: t[1]))
    pary = []
    prichina = ""
    while True:
        r = _para(g, pervaya=not pary)
        if isinstance(r, str):
            prichina = r
            break
        pary.append(r)
        if r["i_ao_2"] <= g or r["i_ao_2"] >= p:
            break
        g = r["i_ao_2"]

    if not pary:
        return {"ok": True, "est": False, "slovami": f"1-я {imya}: " + prichina,
                "пары": [], "край": None}

    bolshaya = pary[0]
    s_diverom = [x for x in pary if x["est"]]
    kray = s_diverom[-1] if s_diverom else None
    slovami = "весь ход: " + bolshaya["slovami"]
    # TONKAYA_SAMA_V1 (слово Шефа 25.09): тонкая — сама по себе.
    # Большой дивер может быть и за краем экрана; у края он свой.
    if kray is not None and kray is not bolshaya:
        slovami += " || у края: " + kray["slovami"]
    if len(pary) > 1:
        slovami += f" || размеров: {len(pary)}, с расхождением: {len(s_diverom)}"
    # TONKAYA_SAMA_V1: дивер есть, если он есть хоть на одном размере.
    _glavnaya = bolshaya if bolshaya["est"] else kray
    otvet = {"ok": True, "est": _glavnaya is not None, "slovami": slovami,
             "пары": pary, "край": kray}
    if _glavnaya is not None:
        for k in ("цена_было", "цена_стало", "ao_было", "ao_стало",
                  "i_цена_1", "i_цена_2", "i_ao_1", "i_ao_2"):
            otvet[k] = _glavnaya[k]
    return otvet
