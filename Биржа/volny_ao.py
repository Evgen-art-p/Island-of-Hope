# -*- coding: utf-8 -*-
# VOLNY_AO_V1 — счёт волн по AO (второй уровень, первый шаг)
"""
КАНОН (Вильямс, «Торговый хаос», уровень второй, глава о волнах Эллиота;
слово Шефа 30.09: «по AO точно определяем волну 3 — самый большой горб, от
неё противоположный ход — волна 4, потом меньший горб — волна 5»;
14.10: «канон истина, равняемся на канон»)

  Счёт ведётся на 100–140 барах — у нас поле зрения 140, как на кадре.
  • Третья волна — самый большой горб (самая глубокая яма) AO в поле зрения.
  • Минимум для четвёртой выполнен, когда после пика третьей AO пересёк ноль.
  • Пятая — после этого AO вернулся на прежнюю сторону, цена ушла за край
    третьей, а горб меньше: дивер между третьей и пятой. Здесь конец хода.
  • Дивер без возврата AO к нулю — пятая внутри большой третьей: ход ещё
    продолжится. Принять её за конец всего хода — самая частая ошибка.
  • Зона конца четвёртой — обычно 38–50% от третьей (по цене).
  • МАСШТАБ (слово Шефа 14.10, и так у Вильямса): по нулю счёт верен, только
    когда весь ход занимает 100–140 баров. Ход короче — AO меряет волну
    старшего порядка: горка-ямка-горка без перехода через ноль там обычная
    пятая этого хода, а не ловушка. Тогда считаем этажом ниже, если там ход
    ложится в 100–140; не ложится нигде — по нулю не судим, дивер как обычно.

ЧТО ЗДЕСЬ
  Город СЧИТАЕТ и ПОКАЗЫВАЕТ. Ничего не запрещает: решает трейдер.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

BAROV = 140
MASSHTAB = (100, 140)       # столько баров должен занимать ход для счёта по нулю
NIZHE = {"MN1": "W1", "W1": "D1", "D1": "H4", "H4": "H1"}


def _znak(x) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def _oblast(ao, i, lo, hi):
    """Сплошной участок AO того же знака, что ao[i], в пределах [lo, hi]."""
    z = _znak(ao[i])
    a = i
    while a - 1 >= lo and ao[a - 1] is not None and _znak(ao[a - 1]) == z:
        a -= 1
    b = i
    while b + 1 <= hi and ao[b + 1] is not None and _znak(ao[b + 1]) == z:
        b += 1
    return a, b


def schet_po_baram(highs, lows, ao, dates=None, barov=BAROV, ot_bara=None,
                   znak=None) -> dict:
    """Счёт волн по готовым рядам. Вся логика — здесь (её и проверяем).
    ot_bara/znak — для счёта этажом ниже: только этот ход и его сторона."""
    n = len(ao)
    nach = max(0, n - barov) if ot_bara is None else max(0, ot_bara)
    idx = [i for i in range(nach, n) if ao[i] is not None]
    if len(idx) < 40:
        return {"ok": False, "slovami": "мало баров для счёта волн"}
    lo, p = idx[0], idx[-1]

    def kogda(i):
        try:
            return str(dates[i])[:10] if dates else f"бар {i}"
        except Exception:
            return f"бар {i}"

    i3 = (max(idx, key=lambda k: abs(ao[k])) if znak is None
          else max(idx, key=lambda k: znak * ao[k]))
    s = _znak(ao[i3])
    if s == 0:
        return {"ok": False, "slovami": "AO в поле зрения пустой"}
    vverh = s > 0
    hod = "вверх" if vverh else "вниз"
    a3 = ao[i3]
    r0, r1 = _oblast(ao, i3, lo, p)

    def kray(rng, verh):
        rng = list(rng)
        if not rng:
            return None, None
        # при равных ценах — более поздний бар (ближе к ходу)
        k = (max(rng, key=lambda j: (highs[j], j)) if verh
             else min(rng, key=lambda j: (lows[j], -j)))
        return k, (highs[k] if verh else lows[k])

    # начало третьей: противоположный край от начала прошлого участка
    # (там кончилась вторая) до начала участка третьей
    if r0 - 1 >= lo:
        q0, _q1 = _oblast(ao, r0 - 1, lo, p)
    else:
        q0 = lo
    i_nach, c_nach = kray(range(q0, r0 + 1), not vverh)
    # цена у пика AO (обычно на 1–5 баров раньше пика) — для «пятой внутри
    # третьей»; край всей третьей — самый край её участка (вместе с пятой
    # внутри неё): от него меряют четвёртую и с ним сравнивают пятую
    i_k3, c_k3 = kray(range(r0, min(i3 + 2, p) + 1), vverh)
    i_e3, c_e3 = kray(range(r0, r1 + 1), vverh)
    u_kraya_okna = r0 <= lo + 2
    # начало всего хода (точка, откуда пошла первая): шаг назад через
    # участок второй и участок первой — там противоположный край цены
    b0 = q0
    if b0 - 1 >= lo:
        w0, _w1 = _oblast(ao, b0 - 1, lo, p)
        b0 = w0
        if b0 - 1 >= lo:
            x0, _x1 = _oblast(ao, b0 - 1, lo, p)
            b0 = x0
    i_hod0, c_hod0 = kray(range(b0, r0 + 1), not vverh)
    barov_hoda = p - i_hod0 if i_hod0 is not None else 0
    # PYAT_PUL_V1: край первой — от начала хода до дна второй (если первая
    # с второй в поле зрения): нужен для правил «четвёртая не на территории
    # первой» и «третья не самая короткая»
    i_k1, c_k1 = (kray(range(i_hod0, i_nach + 1), vverh)
                  if (i_hod0 is not None and i_nach is not None and i_nach > i_hod0 + 1)
                  else (None, None))
    ot = {"ok": True, "ход": hod, "сторона": s, "ao3": a3, "дата3": kogda(i3),
          "начало_хода": round(c_hod0, 5) if c_hod0 is not None else None,
          "дата_начала_хода": kogda(i_hod0) if i_hod0 is not None else "",
          "баров_хода": barov_hoda,
          "масштаб_верный": barov_hoda >= MASSHTAB[0] or i_hod0 is not None and i_hod0 <= lo + 2,
          "цена3": round(c_k3, 5), "дата_цены3": kogda(i_k3), "начало3": round(c_nach, 5),
          "дата_начала3": kogda(i_nach), "у_края_окна": u_kraya_okna,
          "kray1": round(c_k1, 5) if c_k1 is not None else None,
          "data_kraya1": kogda(i_k1) if i_k1 is not None else "",
          "nachalo1": round(c_hod0, 5) if c_hod0 is not None else None}

    def za(c, etalon, verh):
        return (c > etalon) if verh else (c < etalon)

    # ── участок третьей ещё идёт: AO через ноль не ходил ──
    if r1 >= p:
        i_pos, c_pos = kray(range(min(i3 + 2, p) + 1, p + 1), vverh)
        if i_pos is not None and za(c_pos, c_k3, vverh):
            a_pos = max((ao[k] for k in range(i3 + 1, p + 1)), key=abs)
            ot.update(volna="пятая внутри третьей", cherez_nol=False,
                      tsena_dalshe=round(c_pos, 5), data_dalshe=kogda(i_pos), ao_dalshe=a_pos)
        else:
            ot.update(volna="третья", cherez_nol=False)
        return ot

    # ── AO пересёк ноль после третьей: минимум для четвёртой ──
    m0, m1 = _oblast(ao, r1 + 1, lo, p)
    ot.update(cherez_nol=True, data_nolya=kogda(r1 + 1),
              kray3=round(c_e3, 5), data_kraya3=kogda(i_e3))
    i4, c4 = kray(range(r1 + 1, (m1 if m1 < p else p) + 1), not vverh)
    dlina3 = abs(c_e3 - c_nach) if (c_e3 is not None and c_nach is not None) else 0
    if dlina3:
        z38 = c_e3 - s * 0.38 * dlina3
        z50 = c_e3 - s * 0.50 * dlina3
        glub = abs(c_e3 - c4) / dlina3 if c4 is not None else None
        ot.update(zona=(z38, z50), glubina4=glub, tsena4=round(c4, 5), data4=kogda(i4))
    # цена ушла за начало третьей — это уже не четвёртая
    if c4 is not None and c_nach is not None and za(c4, c_nach, not vverh):
        ot.update(volna="счёт сломан: цена ушла за начало третьей")
        return ot
    ot["kray3_tochno"] = c_e3
    # ── дальше — участки AO по очереди (VOLNY_AO_V4): пятая может растянуться.
    # Участок на стороне третьей, где цена взяла край хода, — пятая (если
    # раньше уже была пятая — значит, она растянулась). Коррекция после
    # пятой — «после пятой», пока цена не ушла за её край.
    kray_hoda = c_e3
    pyataya = None                  # (бар края, цена, горб AO)
    rastyazh = 0
    nol2 = None
    korr = None                     # край последней коррекции (бар, цена)
    nach5 = None                    # откуда пошла пятая — край коррекции перед ней
    znak_posl = -s
    k = r1 + 1
    while k <= p:
        g0, g1 = _oblast(ao, k, lo, p)
        g1c = min(g1, p)
        if _znak(ao[k]) == s:
            ik, ck = kray(range(g0, g1c + 1), vverh)
            ak = max((ao[x] for x in range(g0, g1c + 1)), key=abs)
            if ck is not None and za(ck, kray_hoda, vverh):
                if pyataya is not None and pyataya[0] < g0:
                    rastyazh += 1
                if pyataya is None or pyataya[0] < g0:
                    nach5 = korr
                pyataya = (ik, ck, ak)
                kray_hoda = ck
        else:
            ik, ck = kray(range(g0, g1c + 1), not vverh)
            if ck is not None and c_nach is not None and za(ck, c_nach, not vverh):
                ot.update(volna="счёт сломан: цена ушла за начало третьей")
                return ot
            if pyataya is not None:
                nol2 = g0
            korr = (ik, ck)
        znak_posl = s if _znak(ao[k]) == s else -s
        k = g1 + 1
    if pyataya is not None:
        i5, c5, a5 = pyataya
        ot.update(tsena5=round(c5, 5), data5=kogda(i5), ao5=a5, vzyal_kray=True,
                  rastyanulas=rastyazh)
        if nach5 is not None:
            ot.update(nachalo5=round(nach5[1], 5), data_nachala5=kogda(nach5[0]))
    if znak_posl == s:
        if pyataya is not None and pyataya[0] >= _oblast(ao, p, lo, p)[0]:
            ot.update(volna="пятая, край третьей взят, горб меньше — дивер"
                      + (f" (пятая растянулась: {rastyazh + 1}-й край)" if rastyazh else ""))
        elif pyataya is not None and nol2 is not None:
            # пятая уже была, после неё AO сходил через ноль, а этот подъём
            # её край не взял — это отскок после пятой, не новая пятая
            ot.update(volna="после пятой: AO снова через ноль (отскок ниже края пятой)",
                      data_nolya2=kogda(nol2))
        else:
            ot.update(volna="пятая идёт, край хода ещё не взят")
        return ot
    if pyataya is not None:
        ot.update(volna="после пятой: AO снова через ноль", data_nolya2=kogda(nol2))
    else:
        ot.update(volna="четвёртая")
    return ot


def _bary_ao(symbol, timeframe, n):
    from feed_source import bars as _bars
    from williams_core import compute_ao_series
    b, _pt = _bars(symbol, timeframe, n)
    if not b or len(b) < 80:
        return None
    highs = [x["high"] for x in b]
    lows = [x["low"] for x in b]
    return b, highs, lows, compute_ao_series(highs, lows)


def fraktaly(highs, lows, lo, p):
    """Фракталы Вильямса, ПОДТВЕРЖДЁННЫЕ к бару p: средний бар строго выше
    (ниже) двух слева и двух справа. Фрактал на баре i виден только когда
    i + 2 <= p — то есть после двух закрытых баров справа (без заглядывания
    вперёд). Равные цены — не фрактал (ждём ясного)."""
    verh, niz = [], []
    for i in range(max(lo, 2), p - 1):
        if i + 2 > p:
            break
        h = highs[i]
        if h > highs[i - 1] and h > highs[i - 2] and h > highs[i + 1] and h > highs[i + 2]:
            verh.append(i)
        l = lows[i]
        if l < lows[i - 1] and l < lows[i - 2] and l < lows[i + 1] and l < lows[i + 2]:
            niz.append(i)
    return verh, niz


def _hod_seychas(highs, lows, vverh, lo, p):
    """Ход в сторону vverh, который кончается сейчас — по подтверждённым
    фракталам (HOD_PO_FRAKTALAM_V3).

    ПРАВИЛО (для подъёма; снижение — зеркально):
      • Непробитая вершина — подтверждённый верхний фрактал, выше которого
        после него не торговал ни один ЗАКРЫТЫЙ бар.
      • Ограничитель хода H — самая свежая непробитая вершина, после которой
        уже есть подтверждённый нижний фрактал; если после самой свежей
        непробитой вершины нижнего фрактала ещё нет — ход только что
        кончился на ней, и ограничитель — следующая, более старая.
      • Начало хода S — самый низкий подтверждённый нижний фрактал после H
        (до вершины хода); при равных — более поздний.
      • Слияние: закрытый бар поторговал выше H — H пробита, ограничителем
        становится следующая непробитая вершина, и начало уходит назад.
        Пересчёт — только по закрытым барам.
    → {"начало": S, "край": E, "огр": H или None} либо None."""
    verh, niz = fraktaly(highs, lows, lo, p)
    if vverh:
        top, bot, cena_t, cena_b = verh, niz, highs, lows
        nad = lambda a, b: a > b
    else:
        top, bot, cena_t, cena_b = niz, verh, lows, highs
        nad = lambda a, b: a < b
    def ekstr_posle(i):
        r = range(i + 1, p + 1)
        if not len(r):
            return None
        return (max(cena_t[x] for x in r) if vverh else min(cena_t[x] for x in r))
    neprob = [u for u in top
              if ekstr_posle(u) is None or nad(cena_t[u], ekstr_posle(u))]
    neprob.sort(reverse=True)                       # самые свежие — первыми

    def nachalo(ot, do):
        kand = [b for b in bot if ot < b < do]
        if not kand:
            return None
        return (min(kand, key=lambda b: (cena_b[b], -b)) if vverh
                else max(kand, key=lambda b: (cena_b[b], b)))

    def kray(ot, do):
        r = range(ot, do + 1)
        return (max(r, key=lambda x: (highs[x], x)) if vverh
                else min(r, key=lambda x: (lows[x], -x)))

    if neprob:
        h1 = neprob[0]
        s = nachalo(h1, p + 1)
        if s is not None:                            # ход идёт после h1
            return {"начало": s, "край": kray(s, p), "огр": h1}
        h2 = neprob[1] if len(neprob) > 1 else None  # ход кончился на h1
        s = nachalo(h2 if h2 is not None else lo - 1, h1)
        if s is not None:
            return {"начало": s, "край": kray(s, p), "огр": h2}
        return None
    s = nachalo(lo - 1, p + 1)                       # непробитых вершин в окне нет
    if s is None:
        return None
    return {"начало": s, "край": kray(s, p), "огр": None}


def _norm_data(x) -> str:
    x = str(x or "")
    return x if len(x) > 10 else (x[:10] + " 00:00")


# ── ЭТАЖ ПОБЛИЖЕ (ETAZH_POBLIZHE_V1) ─────────────────────────────
# Слово Шефа 16.10: «на H4 48 баров, на H1 192 — H1 значит сформирована,
# почему не посмотреть, сколько влезет»; «в MT5 и другие этажи есть — пусть
# ловит какой поближе». Город берёт этаж лесенки, где ход ближе всего к
# 100–140 барам. В норме — точный счёт; до полутора раз мимо нормы —
# «приблизительно» (так и пишет); дальше — прочерк.
DOPUSK = 1.5
_KANDIDATY = ("D1", "H12", "H8", "H4", "H1", "M30", "M15")


def _mera(n) -> float:
    """Насколько ход мимо 100–140: 1.0 — в норме, больше — во столько раз мимо."""
    if not isinstance(n, int) or n <= 0:
        return 99.0
    if n < MASSHTAB[0]:
        return MASSHTAB[0] / n
    if n > MASSHTAB[1]:
        return n / MASSHTAB[1]
    return 1.0


def _niz_etazhi(tf) -> list:
    """Этажи-кандидаты: рабочий и всё ниже него в коридоре трейдера."""
    try:
        import masshtab as _ms
        lest = list(_ms.LESTNICA)
    except Exception:
        lest = ["MN1", "W1", "D1", "H12", "H8", "H4", "H1", "M30", "M15", "M10", "M5"]
    tf = str(tf or "").upper()
    if tf not in lest:
        return [tf]
    i = lest.index(tf)
    return [tf] + [x for x in lest[i + 1:] if x in _KANDIDATY]


def vybrat_etazh(symbol, data0, rabochiy, barov_rab, tolko_nizhe=False):
    """Где ход (от даты data0 до сейчас) ближе всего к 100–140 барам.
    → (этаж, баров, мера, пробовали)."""
    probovali = []
    luchshiy = None
    for tf in _niz_etazhi(rabochiy):
        if tolko_nizhe and tf == str(rabochiy).upper():
            continue
        if tf == str(rabochiy).upper() and barov_rab is not None:
            n = barov_rab
        else:
            try:
                r = _bary_ao(symbol, tf, 3000)
            except Exception:
                r = None
            if not r:
                continue
            bb = r[0]
            idx = next((i for i, x in enumerate(bb)
                        if _norm_data(x.get("date")) >= data0), None)
            if idx is None or idx == 0:
                continue                # начало хода раньше всех баров этажа
            n = len(bb) - 1 - idx
        m = _mera(n)
        probovali.append((tf, n))
        if luchshiy is None or m < luchshiy[2] - 1e-9:
            luchshiy = (tf, n, m)
        if m > 3 and luchshiy and n > MASSHTAB[1]:
            break                        # ниже будет только длиннее
    if luchshiy is None:
        return None, None, 99.0, probovali
    return luchshiy[0], luchshiy[1], luchshiy[2], probovali


def _okno(symbol, tf, n=BAROV + 60):
    r = _bary_ao(symbol, tf, n)
    if not r:
        return None
    b, highs, lows, ao = r
    m = BAROV + 40
    return b[-m:], highs[-m:], lows[-m:], ao[-m:]


def schet_hoda(symbol: str, timeframe: str, vverh: bool) -> dict:
    """Счёт ТОГО хода в сторону vverh, который кончается сейчас.
    Масштаб: ход в 100–140 баров — считаем здесь; короче — этажом ниже, если
    там ложится; не ложится нигде — по нулю не судим."""
    hod = "вверх" if vverh else "вниз"
    try:
        w = _okno(symbol, timeframe)
    except Exception as e:
        return {"ok": False, "slovami": f"нет баров ({e})"}
    if not w:
        return {"ok": False, "slovami": "мало баров"}
    b, highs, lows, ao = w
    n = len(b)
    lo, p = max(0, n - BAROV), n - 1
    hs = _hod_seychas(highs, lows, vverh, lo, p)
    if not hs:
        return {"ok": True, "нет_хода": True, "ход": hod, "этаж": timeframe}
    o, e = hs["начало"], hs["край"]
    barov = p - o
    data0 = _norm_data(b[o].get("date"))
    data1 = _norm_data(b[o + 1].get("date")) if o + 1 < n else "9999"
    nach = round(lows[o] if vverh else highs[o], 5)
    ogr = hs.get("огр")
    baza = {"ход": hod, "этаж": timeframe, "баров_хода": barov,
            "начало_хода": nach, "дата_начала_хода": str(b[o].get("date") or ""),
            "огр": (round(highs[ogr] if vverh else lows[ogr], 5) if ogr is not None else None),
            "дата_огр": (str(b[ogr].get("date") or "") if ogr is not None else "")}
    znak = 1 if vverh else -1
    etazh, n_et, mera, probovali = vybrat_etazh(symbol, data0, timeframe, barov)
    if etazh is None or mera > DOPUSK:
        baza.update(ok=True, volna=None, ne_lozhitsya=True, probovali=probovali)
        return baza
    primerno = mera > 1.0 + 1e-9
    if etazh == str(timeframe).upper():
        ot = schet_po_baram(highs, lows, ao, [x.get("date") for x in b],
                            ot_bara=o, znak=znak)
        ot.update(baza)
        ot["масштаб_верный"] = True
    else:
        # точное начало — внутри бара рабочего этажа, где ход начался
        try:
            r = _bary_ao(symbol, etazh, 3000)
        except Exception:
            r = None
        if not r:
            baza.update(ok=True, volna=None, ne_lozhitsya=True, probovali=probovali)
            return baza
        bb, hh, ll = r[0], r[1], r[2]
        vnutri = [i for i, x in enumerate(bb)
                  if data0 <= _norm_data(x.get("date")) < data1]
        if vnutri:
            idx = (min(vnutri, key=lambda i: (ll[i], -i)) if vverh
                   else max(vnutri, key=lambda i: (hh[i], i)))
            d_tochno = _norm_data(bb[idx].get("date"))
        else:
            d_tochno = data0
        ot = _na_etazhe(symbol, etazh, d_tochno, znak, n=3000)
        ot.update({"ход": hod, "начало_хода": nach,
                   "дата_начала_хода": baza["дата_начала_хода"],
                   "огр": baza["огр"], "дата_огр": baza["дата_огр"]})
        ot["масштаб_с"] = {"этаж": timeframe, "баров": barov,
                           "этаж_счёта": etazh, "баров_там": n_et}
    if primerno:
        ot["примерно"] = {"этаж": etazh, "баров": n_et,
                          "как": "крупноват" if n_et > MASSHTAB[1] else "мелковат"}
    ot["пробовали"] = probovali
    return ot


def _na_etazhe(symbol, tf, data0=None, znak=None, n=600):
    try:
        r = _bary_ao(symbol, tf, BAROV + 60 if data0 is None else n)
    except Exception as e:
        return {"ok": False, "slovami": f"нет баров ({e})"}
    if not r:
        return {"ok": False, "slovami": "мало баров"}
    b, highs, lows, ao = r
    if data0 is None:
        k = BAROV + 40
        b, highs, lows, ao = b[-k:], highs[-k:], lows[-k:], ao[-k:]
        ot = schet_po_baram(highs, lows, ao, [x.get("date") for x in b])
    else:
        i0 = next((i for i, x in enumerate(b)
                   if _norm_data(x.get("date")) >= data0), 0)
        ot = schet_po_baram(highs, lows, ao, [x.get("date") for x in b],
                            ot_bara=i0, znak=znak)
        ot["масштаб_верный"] = True
    ot["этаж"] = tf
    return ot


def bolshoy(symbol: str, timeframe: str) -> dict:
    """Большой ход в окне (самый большой горб AO) — для входа по ходу:
    дошёл ли он до своей четвёртой."""
    try:
        return _na_etazhe(symbol, timeframe)
    except Exception as e:
        return {"ok": False, "slovami": f"нет счёта ({e})"}


def schet(symbol: str, timeframe: str) -> dict:
    """Старое имя: подъём (для SHORT), если его край свежее, иначе снижение."""
    up = schet_hoda(symbol, timeframe, True)
    dn = schet_hoda(symbol, timeframe, False)
    if up.get("нет_хода"):
        return dn
    if dn.get("нет_хода"):
        return up
    return up if str(up.get("дата_начала_хода")) >= str(dn.get("дата_начала_хода")) else dn


def mladshiy(symbol: str, timeframe: str, vverh: bool, cur=None) -> dict:
    """MLADSHIY_ETAZH_V1 — пятая рабочего хода на младшем этаже.
    Слово Шефа 16.10: «когда разворотник на рабочем, на младшем видно может,
    что это третья и пятая в третьей». Только когда рабочий счёт говорит
    «пятая»: город берёт саму пятую (от края коррекции перед ней) и считает
    её этажом ниже — с тем же правилом масштаба. → {"кончик": да/нет/None,
    "этаж": ..., "текст": ...} или {} (младший тут ничего не добавит)."""
    cur = cur if cur is not None else schet_hoda(symbol, timeframe, vverh)
    if not cur.get("ok") or cur.get("нет_хода") or cur.get("ne_lozhitsya"):
        return {}
    # ход мог быть посчитан не на рабочем, а на этаже поближе — пятую
    # тогда считаем ниже ТОГО этажа
    base_tf = (cur.get("масштаб_с") or {}).get("этаж_счёта") or timeframe
    v = str(cur.get("volna") or "")
    if not v.startswith("пятая, край"):
        return {}
    d5 = str(cur.get("data_nachala5") or "")
    if not d5:
        return {}
    d5 = _norm_data(d5)
    jtf, n, mera, _pr = vybrat_etazh(symbol, d5, base_tf, None, tolko_nizhe=True)
    if not jtf:
        return {}
    if mera > DOPUSK:
        return {"кончик": None, "этаж": jtf,
                "текст": f"пятая рабочего хода ближе всего к норме на {jtf} — {n} "
                         f"баров: не ложится, по нулю не судим (прочерк)"}
    try:
        r = _bary_ao(symbol, jtf, 3000)
    except Exception:
        r = None
    if not r:
        return {}
    b, highs, lows, ao = r
    i0 = next((i for i, x in enumerate(b) if _norm_data(x.get("date")) >= d5), None)
    if i0 is None or i0 == 0:
        return {}
    okno = range(i0, min(i0 + 8, len(b)))
    i0 = (min(okno, key=lambda i: (lows[i], -i)) if vverh
          else max(okno, key=lambda i: (highs[i], i)))
    n = len(b) - 1 - i0
    prim = (f", масштаб {'крупноват' if n > MASSHTAB[1] else 'мелковат'} — "
            f"счёт приблизительный") if _mera(n) > 1.0 + 1e-9 else ""
    ot = schet_po_baram(highs, lows, ao, [x.get("date") for x in b],
                        ot_bara=i0, znak=1 if vverh else -1)
    w = str(ot.get("volna") or "")
    if w.startswith("пятая, край") or w.startswith("после пятой"):
        return {"кончик": True, "этаж": jtf,
                "текст": f"пятая рабочего хода на {jtf} ({n} баров{prim}) — внутри неё "
                         f"пятая с дивером: КОНЧИК, разворот точный"}
    if not w or w.startswith("счёт сломан"):
        return {"кончик": None, "этаж": jtf,
                "текст": f"пятая рабочего хода на {jtf} ({n} баров{prim}): счёт не сложился (прочерк)"}
    return {"кончик": False, "этаж": jtf,
            "текст": f"пятая рабочего хода на {jtf} ({n} баров{prim}) — внутри неё {w}: "
                     f"кончика ещё нет, пятая тянется — рано"}


# ══ PYAT_PUL_V1 — цель пятой, правила, пять пуль ══════════════════
# Вильямс, «Торговый хаос», второй уровень: конец тренда почти всегда
# убивают «пять волшебных пуль» — 1) дивергенция, 2) цена в целевой зоне,
# 3) фрактал на вершине (внизу), 4) приседающий — один из трёх самых
# высоких (низких) баров, 5) смена импульса (AO против своей сигнальной).
# Слово Шефа 17.10: «делай пять пуль, как в каноне»; дивер — по AO: «MFI
# на одной свече силу показывает, AO — на волне, по сути одно и то же».
# «Рынки не идеальные»: город считает и показывает, не судит.
def cel_pyatoy(ot) -> dict:
    """Цель пятой по Вильямсу: от конца четвёртой (коррекции перед пятой),
    0.618–1.0 длины хода от начала до конца третьей."""
    if not ot or not ot.get("ok"):
        return {}
    nach = ot.get("начало_хода") if ot.get("начало_хода") is not None else ot.get("nachalo1")
    k3 = ot.get("kray3_tochno", ot.get("kray3"))
    baza = ot.get("nachalo5") if ot.get("nachalo5") is not None else ot.get("tsena4")
    if nach is None or k3 is None or baza is None:
        return {}
    L = abs(float(k3) - float(nach))
    if L <= 0:
        return {}
    s = 1 if ot.get("сторона", 0) > 0 else -1
    z1, z2 = baza + s * 0.618 * L, baza + s * 1.0 * L
    c5 = ot.get("tsena5")
    proshla = (abs(float(c5) - float(baza)) / L) if c5 is not None else None
    return {"zona": (round(z1, 5), round(z2, 5)), "proshla": proshla,
            "v_zone": proshla is not None and 0.618 <= proshla,
            "za_zonoy": proshla is not None and proshla > 1.0}


def pravila(ot) -> list:
    """Нормы Эллиота, которые считаются точно. Нарушена — не приговор
    (рынок не идеален), а повод посмотреть счёт внимательнее."""
    out = []
    if not ot or not ot.get("ok"):
        return out
    s = 1 if ot.get("сторона", 0) > 0 else -1
    n1, k1 = ot.get("nachalo1"), ot.get("kray1")
    n3, k3 = ot.get("начало3"), ot.get("kray3_tochno", ot.get("kray3"))
    if n1 is not None and n3 is not None and (n3 - n1) * s < 0:
        out.append("вторая ушла за начало первой — это не импульс, счёт неверен")
    if k1 is not None:
        for c4 in (ot.get("tsena4"), ot.get("nachalo5")):
            if c4 is not None and (c4 - k1) * s < 0:
                out.append("коррекция зашла на территорию первой — это не импульс "
                           "(или конечная диагональ)")
                break
        if n1 is not None and n3 is not None and k3 is not None:
            L1, L3 = abs(k1 - n1), abs(k3 - n3)
            L5 = (abs(ot["tsena5"] - ot["nachalo5"])
                  if ot.get("tsena5") is not None and ot.get("nachalo5") is not None else None)
            if L3 < L1 and (L5 is None or L3 < L5):
                out.append("третья вышла самой короткой — так не бывает, счёт сомнителен")
    return out


def pyat_pul(symbol: str, timeframe: str, vverh: bool, ot=None) -> dict:
    """Пять пуль у края хода в сторону vverh (подъём — вершина, снижение — дно)
    на рабочем этаже, по закрытым барам."""
    ot = ot if ot is not None else schet_hoda(symbol, timeframe, vverh)
    rez = {"дивер": None, "цель": None, "фрактал": None, "приседающий": None,
           "импульс": None, "слова": {}}
    try:
        w = _okno(symbol, timeframe)
    except Exception:
        w = None
    if not w:
        return rez
    b, highs, lows, ao = w
    p = len(b) - 1
    okno = range(max(0, p - 9), p + 1)
    e = (max(okno, key=lambda j: (highs[j], j)) if vverh
         else min(okno, key=lambda j: (lows[j], -j)))
    # 1. дивер — счёт города по AO
    try:
        import sverka_divera as _sd
        d = _sd.poschitat(symbol, timeframe, "SHORT" if vverh else "LONG") or {}
        rez["дивер"] = bool(d.get("est")) if d.get("ok") else None
    except Exception:
        rez["дивер"] = None
    # 2. цель пятой
    cz = cel_pyatoy(ot) if str(ot.get("volna") or "").startswith(("пятая", "после пятой")) else {}
    if cz.get("proshla") is not None:
        rez["цель"] = bool(cz.get("v_zone"))
        rez["слова"]["цель"] = (f"пятая прошла {cz['proshla'] * 100:.0f}% цели "
                                f"(зона {cz['zona'][0]}–{cz['zona'][1]})")
    else:
        rez["слова"]["цель"] = "пятой нет — цели нет"
        rez["цель"] = False if ot.get("ok") and ot.get("volna") else None
    # 3. фрактал на крае
    if e + 2 > p:
        rez["фрактал"] = False
        rez["слова"]["фрактал"] = "на крае ещё не подтверждён (нужно 2 закрытых бара справа)"
    else:
        h, l = highs, lows
        if vverh:
            ok = all(h[e] > h[e + k] for k in (1, 2)) and all(h[e] > h[e - k] for k in (1, 2) if e - k >= 0)
        else:
            ok = all(l[e] < l[e + k] for k in (1, 2)) and all(l[e] < l[e - k] for k in (1, 2) if e - k >= 0)
        rez["фрактал"] = bool(ok)
        rez["слова"]["фрактал"] = "подтверждён на крае" if ok else "на крае фрактала нет"
    # 4. приседающий среди трёх самых высоких (низких) баров у края
    try:
        tri = sorted(okno, key=lambda j: highs[j], reverse=True)[:3] if vverh \
            else sorted(okno, key=lambda j: lows[j])[:3]
        def prised(j):
            if j < 1:
                return False
            v, pv = b[j].get("volume") or 0, b[j - 1].get("volume") or 0
            if not v or not pv:
                return False
            m, pm = (highs[j] - lows[j]) / v, (highs[j - 1] - lows[j - 1]) / pv
            return v > pv and m < pm
        est = [j for j in tri if prised(j)]
        rez["приседающий"] = bool(est)
        rez["слова"]["приседающий"] = ("есть среди трёх крайних баров" if est
                                       else "среди трёх крайних баров нет")
    except Exception:
        rez["приседающий"] = None
    # 5. смена импульса: AO против своей сигнальной (средняя AO за 5 баров)
    try:
        hv = [x for x in ao[-5:] if x is not None]
        if len(hv) == 5 and ao[-1] is not None:
            sig = sum(hv) / 5
            rez["импульс"] = (ao[-1] < sig) if vverh else (ao[-1] > sig)
            rez["слова"]["импульс"] = ("AO ушёл под сигнальную" if vverh else "AO поднялся над сигнальной") \
                if rez["импульс"] else ("AO ещё над сигнальной" if vverh else "AO ещё под сигнальной")
    except Exception:
        rez["импульс"] = None
    rez["сошлось"] = sum(1 for k in ("дивер", "цель", "фрактал", "приседающий", "импульс")
                         if rez.get(k) is True)
    rez["посчитано"] = sum(1 for k in ("дивер", "цель", "фрактал", "приседающий", "импульс")
                           if rez.get(k) is not None)
    rez["правила"] = pravila(ot)
    return rez


def pyat_pul_slovami(pp: dict, kray="вершина") -> str:
    if not pp:
        return "пять пуль не посчитать"
    zn = lambda x: "✓" if x is True else ("✗" if x is False else "—")
    sl = pp.get("слова") or {}
    t = (f"Пять пуль конца хода ({kray}): сошлось {pp.get('сошлось', 0)} из "
         f"{pp.get('посчитано', 0)} — дивер {zn(pp.get('дивер'))}; цель "
         f"{zn(pp.get('цель'))} ({sl.get('цель', '—')}); фрактал {zn(pp.get('фрактал'))} "
         f"({sl.get('фрактал', '—')}); приседающий {zn(pp.get('приседающий'))} "
         f"({sl.get('приседающий', '—')}); импульс {zn(pp.get('импульс'))} "
         f"({sl.get('импульс', '—')}).")
    if pp.get("правила"):
        t += " Нормы волн: " + "; ".join(pp["правила"]) + "."
    t += " Рынок не идеален: это показания, не приговор."
    return t


def _v_pyatoy(ot) -> bool:
    v = str((ot or {}).get("volna") or "")
    return v.startswith("пятая, край") or v.startswith("после пятой")


def osnovanie_razvorota(cur):
    """Разворот хода: да — у него пятая; нет — третья/четвёртая/пятая идёт/
    пятая внутри третьей; None — ход не определился, масштаб не лёг или счёт
    сломан (прочерк, не запрет)."""
    if not cur or not cur.get("ok") or cur.get("нет_хода") or not cur.get("volna"):
        return None
    if str(cur.get("volna")).startswith("счёт сломан"):
        return None
    return _v_pyatoy(cur)


def osnovanie_po_hodu(big, napr):
    """Конец отката по большому ходу: да — вход в его сторону, и он в
    четвёртой (или пятая только началась); нет — вход в его сторону, но он не
    в четвёртой; None — вход не в его сторону или счёт не сложился."""
    if not big or not big.get("ok") or not big.get("volna"):
        return None
    v = str(big.get("volna"))
    if v.startswith("счёт сломан"):
        return None
    if (str(napr).upper() == "LONG") != (big.get("сторона", 0) > 0):
        return None
    return v == "четвёртая" or v.startswith("пятая идёт")


def ocenka_vhoda(symbol: str, timeframe: str, napravlenie: str) -> dict:
    """Два основания — раздельно (V3): разворот хода, который вход
    разворачивает (SHORT — подъём, LONG — снижение), и конец отката по
    большому ходу. Единого «да» нет."""
    napr = str(napravlenie or "").upper()
    if napr not in ("LONG", "SHORT"):
        return {}
    cur = schet_hoda(symbol, timeframe, napr == "SHORT")
    big = bolshoy(symbol, timeframe)
    try:
        ml = mladshiy(symbol, timeframe, napr == "SHORT", cur)
    except Exception:
        ml = {}
    return {"разворот": osnovanie_razvorota(cur), "ход": cur,
            "по_ходу": osnovanie_po_hodu(big, napr), "большой": big,
            "младший": ml}


def razvorot_po_kanonu(ot: dict, napravlenie: str):
    """Старое имя (V1/V2): только основание «разворот»."""
    return osnovanie_razvorota(ot)


def kratko(ot) -> str:
    """Одна строка про ход: откуда, масштаб, волна — без лишнего."""
    if not ot or not ot.get("ok"):
        return f"не посчитать ({(ot or {}).get('slovami', '')})"
    if ot.get("нет_хода"):
        return "хода не определить (нет подтверждённого фрактала начала) — прочерк"
    hod = ot.get("ход")
    t = f"от {ot.get('начало_хода')} ({ot.get('дата_начала_хода')})"
    if ot.get("огр") is not None:
        t += f", до непробитой {'вершины' if hod == 'вверх' else 'ямы'} {ot.get('огр')}"
    ms = ot.get("масштаб_с")
    if ot.get("ne_lozhitsya"):
        pr = ", ".join(f"{e} — {n}" for e, n in (ot.get("probovali") or []))
        return t + f"; баров: {pr} — в 100–140 не ложится, по нулю не судим (прочерк)."
    if ms:
        t += f"; на {ms['этаж']} {ms['баров']} баров — считаю на {ms['этаж_счёта']} ({ms['баров_там']})"
    else:
        t += f"; {ot.get('баров_хода')} баров на {ot.get('этаж')}"
    pm = ot.get("примерно")
    if pm:
        t += (f" — масштаб {pm['как']} ({pm['баров']} баров при норме 100–140), "
              f"счёт ПРИБЛИЗИТЕЛЬНЫЙ")
    v = str(ot.get("volna") or "")
    if v.startswith("пятая, край"):
        return (t + ": ПЯТАЯ — край третьей взят, горб меньше. Разворот здесь законен."
                + (" Пятая уже растягивалась: это не первый её край — растянется "
                   "ещё раз, будет стоп." if "растянулась" in v else ""))
    if v.startswith("после пятой"):
        return t + ": ПОСЛЕ ПЯТОЙ — AO снова через ноль, ход, скорее всего, кончился."
    if v == "пятая внутри третьей":
        return t + ": ПЯТАЯ ВНУТРИ ТРЕТЬЕЙ — AO к нулю не возвращался. Разворот не здесь."
    if v == "третья":
        return t + ": ТРЕТЬЯ идёт. Разворот не здесь."
    if v == "четвёртая":
        return t + ": ЧЕТВЁРТАЯ (AO сходил через ноль) — пятой ещё нет. Разворот не здесь."
    if v.startswith("пятая идёт"):
        return t + ": ПЯТАЯ идёт, край третьей не взят. Разворот не здесь."
    if v.startswith("счёт сломан"):
        return t + ": счёт сломан — прочерк."
    return t + f": {v or 'прочерк'}."


def slovami(ot: dict, tf: str = "") -> str:
    if not ot or not ot.get("ok"):
        return f"счёт волн не вышел — {(ot or {}).get('slovami', '')}"
    if ot.get("нет_хода"):
        return "Ясного хода к краю сейчас нет — считать нечего."
    hod = ot["ход"]
    protiv = "LONG" if hod == "вниз" else "SHORT"
    if ot.get("ne_lozhitsya"):
        pr = ", ".join(f"на {e} — {n}" for e, n in (ot.get("probovali") or []))
        return (f"Ход {hod} от {ot.get('начало_хода')} ({ot.get('дата_начала_хода')}): "
                f"баров {pr}. Для счёта по нулю нужно 100–140 — не ложится ни на "
                f"одном этаже. "
                f"По нулю здесь не судим: горка-ямка-горка без перехода через ноль "
                f"на таком ходе — обычная пятая. Дивер — как всегда, по двум горкам.")
    L = []
    ms = ot.get("масштаб_с")
    if ms:
        L.append(f"Ход на {ms['этаж']} короткий ({ms['баров']} баров) — считаю этажом "
                 f"ниже, на {ms['этаж_счёта']}: там он занимает {ms['баров_там']} баров.")
    else:
        L.append(f"Ход {hod} от {ot.get('начало_хода')} ({ot.get('дата_начала_хода')}) — "
                 f"{ot.get('баров_хода')} баров: масштаб для счёта по нулю верный.")
    L += [f"Третья волна — ход {hod.upper()}: "
         f"{'самый большой горб' if hod == 'вверх' else 'самая глубокая яма'} AO "
         f"{ot['дата3']} ({ot['ao3']:.5f}), цена у пика {ot['цена3']} "
         f"({ot['дата_цены3']}); началась от {ot['начало3']} ({ot['дата_начала3']})."]
    if ot.get("у_края_окна"):
        L.append("(Этот горб у левого края окна — начало третьей может быть за кадром.)")
    v = ot.get("volna", "")
    if not ot.get("cherez_nol"):
        L.append("После неё AO через ноль: НЕ ходил.")
        if v == "пятая внутри третьей":
            L.append(f"Сейчас: ПЯТАЯ ВНУТРИ ТРЕТЬЕЙ — цена ушла дальше ({ot['tsena_dalshe']}, "
                     f"{ot['data_dalshe']}) с меньшим горбом, но AO к нулю не возвращался. "
                     f"По канону это ещё третья: ход продолжится, разворот против него "
                     f"({protiv}) — не здесь.")
        else:
            L.append(f"Сейчас: ТРЕТЬЯ идёт. Разворот против неё ({protiv}) — не здесь.")
        return "\n".join(L)
    L.append(f"Край всей третьей — {ot.get('kray3')} ({ot.get('data_kraya3')}). "
             f"После неё AO через ноль: ДА, {ot['data_nolya']} — минимум для "
             f"четвёртой выполнен.")
    if ot.get("zona"):
        z1, z2 = ot["zona"]
        gl = ot.get("glubina4")
        L.append(f"Четвёртая дошла до {ot.get('tsena4')} ({ot.get('data4')})"
                 + (f" — {gl * 100:.0f}% от третьей" if gl is not None else "")
                 + f"; обычная зона конца четвёртой — 38–50%: {z1:.5f}–{z2:.5f}.")
    if v.startswith("счёт сломан"):
        L.append("Сейчас: СЧЁТ СЛОМАН — цена ушла за начало третьей; это уже не "
                 "четвёртая, а новый ход. Считай заново по картинке.")
    elif v == "четвёртая":
        L.append(f"Сейчас: ЧЕТВЁРТАЯ. Её конец — вход по ходу ({hod}) "
                 "с разворотником и дивером отката.")
    elif v.startswith("пятая, край"):
        L.append(f"Сейчас: ПЯТАЯ — цена ушла за край третьей ({ot['tsena5']}, "
                 f"{ot['data5']}), горб AO меньше ({ot['ao5']:.5f} против "
                 f"{ot['ao3']:.5f}) — дивер третьей и пятой. Конец хода по канону "
                 f"здесь: разворот ({protiv}) законен при трёх условиях.")
    elif v.startswith("пятая идёт"):
        L.append("Сейчас: ПЯТАЯ идёт, край третьей ещё не взят — конца хода нет.")
    elif v.startswith("после пятой"):
        L.append(f"Сейчас: ПОСЛЕ ПЯТОЙ — AO снова через ноль ({ot.get('data_nolya2')}): "
                 f"ход {hod}, скорее всего, кончился.")
    return "\n".join(L)


def blok(symbol, tf) -> str:
    up = schet_hoda(symbol, tf, True)
    dn = schet_hoda(symbol, tf, False)
    big = bolshoy(symbol, tf)
    L = ["=== СЧЁТ ВОЛН ПО AO (город; факт, не приказ) ==="]
    for imya_s, hod_s, vv in (("для SHORT подъём", up, True), ("для LONG снижение", dn, False)):
        L.append(f"Разворот — {imya_s}: " + kratko(hod_s))
        try:
            ml = mladshiy(symbol, tf, vv, hod_s)
        except Exception:
            ml = {}
        if ml.get("текст"):
            L.append(f"  ↳ младший ({ml['этаж']}): {ml['текст']}.")
    if big.get("ok") and big.get("volna"):
        v = str(big.get("volna"))
        if v == "четвёртая":
            z = big.get("zona")
            L.append(f"По ходу — большой ход в окне {big['ход']}: ЧЕТВЁРТАЯ (AO сходил "
                     f"через ноль {big.get('data_nolya')})"
                     + (f", зона её конца 38–50%: {z[0]:.5f}–{z[1]:.5f}" if z else "")
                     + f". Конец этого отката — вход по ходу ({big['ход']}).")
        else:
            L.append(f"По ходу — большой ход в окне {big['ход']}: {v}; "
                     "конца отката по нему сейчас нет.")
    L.append("Два основания разные: разворот — в пятой того хода, который "
             "разворачиваешь; по ходу — конец четвёртой большого хода. Начало хода — "
             "по подтверждённым фракталам. Прочерк — основание не определилось, это "
             "не запрет. Решаешь ты.")
    return "\n".join(L) + "\n\n"


# VOLNY_AO_V1 - marker
# VOLNY_AO_V2 - marker
# VOLNY_AO_V3 - marker
# VOLNY_AO_V4 - marker
# MLADSHIY_ETAZH_V1 - marker
# ETAZH_POBLIZHE_V1 - marker
# PYAT_PUL_V1 - marker
