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
    otvet = dve_gorki(ao, highs, lows, vid, verh, b)
    try:   # STARSHIY_PEREVESHIVAET_V1
        otvet = _starshiy_pereveshivaet(otvet, symbol, timeframe, verh)
    except Exception as _e_st:
        print(f"[ДИВЕР] старший этаж не посчитан ({_e_st})")
    return otvet


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

    def _para(g, pervaya=True, start=None):
        """Одна пара от горки g до края. Строка — пары нет, и почему.

        GORB_YAMA_GORB_V1 (слово Шефа 02.10): «ход — откат — новый ход;
        горб — яма — новый горб; толстая или тонкая, принцип один».
        Откат ищется НА AO: самая глубокая яма после горки (для LONG —
        самая высокая горка после ямы). Вторая горка — после неё. Цена
        делится той же ямой: первая половина — до неё, вторая — после.
        Раньше откат искали по самой низкой цене, и в одной паре цена
        смотрела на одно место, а AO на другое (GBPUSD 03.2024: цена —
        в март, AO — в декабрьский горбик внутри третьей).
        """
        a1 = ao[g]
        if p is None or p <= g + 1:
            return f"{imya} {_kogda(g)} у самого края — второй ещё нет"
        posle = range(g + 1, p + 1)
        d = (min(posle, key=lambda k: ao[k]) if verh
             else max(posle, key=lambda k: ao[k]))
        if d >= p:
            return (f"после {_kogda(g)} AO к краю только "
                    f"{'спускается' if verh else 'поднимается'} — второй "
                    f"{'горки' if verh else 'ямки'} ещё нет")
        za = range(d + 1, p + 1)
        k2 = (max(za, key=lambda k: ao[k]) if verh
              else min(za, key=lambda k: ao[k]))

        # настоящая горка (ямка) или та, что ещё растёт у края; склон,
        # по которому AO просто ползёт, точкой не считается
        def _tochka(k):
            if k < p:
                return ((ao[k] > ao[k - 1] and ao[k] > ao[k + 1]) if verh
                        else (ao[k] < ao[k - 1] and ao[k] < ao[k + 1]))
            return (ao[p] > ao[p - 1]) if verh else (ao[p] < ao[p - 1])

        if not _tochka(k2):
            return (f"после ямы {_kogda(d)} AO просто ползёт — второй "
                    f"{'горки' if verh else 'ямки'} нет")
        # цена — САМЫЙ экстремум своей половины (DIVER_PO_EKSTREMUMAM_V2):
        #   первая пара — от начала подъёма AO к горке до ямы;
        #   тонкая — от начала своего хода (после прошлой ямы) до своей.
        _s = g
        while (_s - 1 >= 0 and ao[_s - 1] is not None
               and ((ao[_s - 1] <= ao[_s]) if verh
                    else (ao[_s - 1] >= ao[_s]))):
            _s -= 1
        nachalo = _s if pervaya else (start if start is not None else g)
        do, pos = range(nachalo, d + 1), range(d + 1, p + 1)
        if verh:
            ic1 = max(do, key=lambda k: highs[k])
            ic2 = max(pos, key=lambda k: highs[k])
            kray_vzyat = highs[ic2] > highs[ic1]
            c1, c2 = highs[ic1], highs[ic2]
        else:
            ic1 = min(do, key=lambda k: lows[k])
            ic2 = min(pos, key=lambda k: lows[k])
            kray_vzyat = lows[ic2] < lows[ic1]
            c1, c2 = lows[ic1], lows[ic2]
        a2 = ao[k2]
        sila_slabee = a2 < a1 if verh else a2 > a1
        u_kraya = " (ещё растёт у края)" if k2 == p else ""
        slovami = (f"{_kogda(g)}: AO {a1:.5f}, край цены {c1:.5f} → "
                   f"откат (яма AO) {_kogda(d)} → {_kogda(k2)}{u_kraya}: "
                   f"AO {a2:.5f}, край цены {c2:.5f}")
        prich = []
        if not kray_vzyat:
            prich.append("цена край своего хода не взяла — откат ещё идёт")
        if not sila_slabee:
            prich.append("сила не слабее прежней")
        if prich:
            slovami += " · " + ", ".join(prich)
        return {"est": bool(kray_vzyat and sila_slabee), "slovami": slovami,
                "цена_было": c1, "цена_стало": c2,
                "ao_было": a1, "ao_стало": a2,
                "i_цена_1": ic1, "i_цена_2": ic2,
                "i_ao_1": g, "i_ao_2": k2, "_откат": d}

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
    _start = None
    while True:
        r = _para(g, pervaya=not pary, start=_start)
        if isinstance(r, str):
            if not pary:
                prichina = r
            break
        pary.append(r)
        # GORB_YAMA_GORB_V1: тонкая — внутри нового хода (пятой), после
        # ямы: её самый большой горб и своя пара до края.
        d = r["_откат"]
        vnutri = [(i, v) for i, v in tochki if d < i < p]
        if not vnutri:
            break
        g_new, _ = (max(vnutri, key=lambda t: t[1]) if verh
                    else min(vnutri, key=lambda t: t[1]))
        if g_new <= g:
            break
        g, _start = g_new, d + 1

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

# DIVER_PO_EKSTREMUMAM_V2 - marker

# GORB_YAMA_GORB_V1 - marker


# ── STARSHIY_PEREVESHIVAET_V1 ─────────────────────────────────────
# Слово Шефа 13.10 (GBPUSD D1, 26.09.2022): «при равном AO старший ТФ
# перевешивает». Цена взяла край своего хода, а новая яма AO у края ВРОВЕНЬ
# с главной — не мельче, но и не заметно глубже (вверх зеркально). На рабочем
# этаже дивер кривой. Тогда решает этаж через один выше (для дневки — месяц):
# есть там дивер — дивер есть. Город считает и показывает, решает трейдер.
STARSHIY_PEREVESHIVAET = True
VROVEN_DOLYA = 0.10    # «вровень»: глубже (выше) главной не больше чем на десятую часть


def _vroven(para: dict, verh: bool) -> bool:
    try:
        c1, c2 = float(para["цена_было"]), float(para["цена_стало"])
        a1, a2 = float(para["ao_было"]), float(para["ao_стало"])
    except (KeyError, TypeError, ValueError):
        return False
    kray = (c2 > c1) if verh else (c2 < c1)
    if not kray or a1 == 0:
        return False
    sverh = (a2 - a1) if verh else (a1 - a2)    # насколько сила у края больше главной
    return 0 <= sverh <= VROVEN_DOLYA * abs(a1)


def _starshiy(symbol: str, timeframe: str, verh: bool):
    from cherez_etazh import etazh_cherez
    from feed_source import bars as _bars
    from williams_core import compute_ao_series
    tf2 = etazh_cherez(timeframe)
    if not tf2:
        return None, ""
    b, _pt = _bars(symbol, tf2, BAROV + 60)
    if not b or len(b) < 50:
        return {"ok": False, "slovami": "мало баров"}, tf2
    b = b[-(BAROV + 40):]
    highs = [x["high"] for x in b]
    lows = [x["low"] for x in b]
    ao = compute_ao_series(highs, lows)
    n = len(ao)
    vid = list(range(max(0, n - BAROV), n))
    return dve_gorki(ao, highs, lows, vid, verh, b), tf2


def _starshiy_pereveshivaet(otvet, symbol, timeframe, verh):
    if not STARSHIY_PEREVESHIVAET or not isinstance(otvet, dict) or otvet.get("est"):
        return otvet
    pary = otvet.get("пары") or []
    if not pary or not _vroven(pary[0], verh):
        return otvet
    st, tf2 = _starshiy(symbol, timeframe, verh)
    otvet = dict(otvet)
    if not st or not st.get("ok"):
        otvet["slovami"] = (str(otvet.get("slovami") or "") +
                            f" || AO у края вровень с главной — старший этаж "
                            f"{tf2 or '—'} посчитать не вышло")
        print(f"[ДИВЕР] ⚖ {symbol} {timeframe}: AO вровень, старший "
              f"{tf2 or '—'} не посчитан ({(st or {}).get('slovami', 'нет этажа')})")
        return otvet
    otvet["старший"] = {"этаж": tf2, "est": bool(st.get("est")),
                        "slovami": st.get("slovami")}
    if st.get("est"):
        otvet["est"] = True
        for k in ("цена_было", "цена_стало", "ao_было", "ao_стало",
                  "i_цена_1", "i_цена_2", "i_ao_1", "i_ao_2"):
            otvet[k] = pary[0][k]
        otvet["slovami"] = (str(otvet.get("slovami") or "") +
                            f" || AO у края вровень с главной — решает старший "
                            f"этаж {tf2}: там дивер ЕСТЬ ({st.get('slovami')})")
        print(f"[ДИВЕР] ⚖ {symbol} {timeframe}: AO вровень — старший {tf2} "
              f"перевешивает: дивер есть")
    else:
        otvet["slovami"] = (str(otvet.get("slovami") or "") +
                            f" || AO у края вровень с главной — старший этаж "
                            f"{tf2}: дивера нет и там")
        print(f"[ДИВЕР] ⚖ {symbol} {timeframe}: AO вровень — старший {tf2}: дивера нет")
    return otvet


# STARSHIY_PEREVESHIVAET_V1 - marker


# ══ SVECHA_STARSHEGO_V1 — старший этаж с текущей свечой ═══════════════
# Слово Шефа 21.10: «был там на месяце дивер… даже на не закрытой свече».
# Кран старшего этажа отдаёт только закрытые свечи — текущий месяц (неделя)
# выпадал. Город собирает текущую свечу из закрытых баров этажа ниже до
# текущего момента: открытие первого, максимум, минимум, закрытие последнего.
# Вперёд не смотрит: этаж ниже тоже отрезан моментом.
_SVECHA_IZ = {"MN1": "D1", "W1": "D1", "D1": "H4"}


def _klyuch_perioda(tf: str, date) -> str:
    d = str(date or "")
    tf = str(tf or "").upper()
    if tf == "MN1":
        return d[:7]
    if tf == "D1":
        return d[:10]
    if tf == "W1":
        try:
            from datetime import datetime, timedelta
            x = datetime.strptime(d[:10], "%Y.%m.%d")
            return (x - timedelta(days=x.weekday())).strftime("%Y.%m.%d")
        except Exception:
            return d[:10]
    return d[:16]


def bary_so_svechoy(symbol: str, tf: str, n: int = BAROV + 60) -> list:
    """Бары старшего этажа + текущая, ещё не закрытая свеча (если есть)."""
    from feed_source import bars as _bars
    b, _pt = _bars(symbol, tf, n)
    b = list(b or [])
    niz = _SVECHA_IZ.get(str(tf or "").upper())
    if not b or not niz:
        return b
    try:
        m, _pm = _bars(symbol, niz, 400)
    except Exception:
        return b
    k_last = _klyuch_perioda(tf, b[-1].get("date"))
    gruppy = {}
    for x in (m or []):
        k = _klyuch_perioda(tf, x.get("date"))
        if k > k_last:
            gruppy.setdefault(k, []).append(x)
    for k in sorted(gruppy):
        g = gruppy[k]
        data = (k + ".01") if str(tf).upper() == "MN1" else k
        b.append({"date": data, "open": g[0]["open"],
                  "high": max(x["high"] for x in g), "low": min(x["low"] for x in g),
                  "close": g[-1]["close"], "текущая": True})
    return b


def diver_so_svechoy(symbol: str, tf: str, storona: str) -> dict:
    """Дивер старшего этажа с текущей свечой. storona: LONG — по впадинам."""
    try:
        from williams_core import compute_ao_series
        b = bary_so_svechoy(symbol, tf)
    except Exception as e:
        return {"ok": False, "est": None, "slovami": f"нет баров ({e})"}
    if not b or len(b) < 50:
        return {"ok": False, "est": None, "slovami": "мало баров"}
    b = b[-(BAROV + 40):]
    highs = [x["high"] for x in b]
    lows = [x["low"] for x in b]
    ao = compute_ao_series(highs, lows)
    n = len(ao)
    vid = list(range(max(0, n - BAROV), n))
    r = dve_gorki(ao, highs, lows, vid, str(storona).upper() == "SHORT", b)
    if b and b[-1].get("текущая"):
        r["slovami"] = (str(r.get("slovami") or "")
                        + f" · с текущей свечой {tf} ({b[-1]['date']}, ещё не закрыта)")
    return r


def _starshiy(symbol: str, timeframe: str, verh: bool):   # noqa: F811
    """STARSHIY_PEREVESHIVAET_V1 — теперь тоже с текущей свечой старшего этажа."""
    from cherez_etazh import etazh_cherez
    tf2 = etazh_cherez(timeframe)
    if not tf2:
        return None, ""
    return diver_so_svechoy(symbol, tf2, "SHORT" if verh else "LONG"), tf2


# SVECHA_STARSHEGO_V1 - marker
