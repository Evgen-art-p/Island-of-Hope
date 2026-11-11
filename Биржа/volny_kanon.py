# -*- coding: utf-8 -*-
# VOLNY_KANON_V1 (27.10) — счёт волн по канону: факт города в сделке + альбом
"""
СЛОВО ШЕФА 27.10
    «Этот счёт брать, пусть город по нему считает и даёт факт, пусть учится
    видеть волны, на вход не влияет.» «Нужна база с тем, как это выглядит
    фактически, а уже сравнивать при работе.» «Город пишет, что есть, а
    задача — по своему анализу определить, что происходит.»

КАНОН (тот же, что в замере zamer_voln_kanon.py)
    Ход начинается там, где кончился прошлый: для хода вверх — самый низкий
    низ перед текущей высшей вершиной (назад — до первого бара выше неё);
    вниз — зеркально. Считается на этаже, где ход занимает 100–140 баров;
    до полутора раз мимо — «приблизительно», дальше — по нулю не судим.
    Границы волн — канонические фракталы (пять баров, подтверждённые).
    Номера по AO: самый большой горб — третья; впадина перед ней над нулём —
    вторая; горб перед ней — первая; AO ниже нуля после третьей — минимум
    четвёртой; горб ниже третьего при новом крае цены — пятая; горб-горб без
    нуля — волны внутри третьей. Зоны: четвёртая — 38–50% от третьей; пятая —
    от конца четвёртой на 62–100% хода от начала до конца третьей.

ЧТО ЗДЕСЬ
    blok_sdelki(...) — блок «ВОЛНЫ ТВОЕГО ХОДА» для места в сделке: ход, в
    котором едет сделка, его счёт сейчас, по закрытым барам до бара города.
    albom(...) — альбом примеров места (картинки с разметкой по истории).
    Город считает и показывает. Ничего не запрещает и ни к чему не обязывает.
"""
from __future__ import annotations

import bisect
import json
import sys as _sys
from datetime import datetime, timedelta
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))
_TSEHA = _BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха"

NORMA = (100, 140)
DOPUSK = 1.5
ETAZHI = ("W1", "D1", "H12", "H8", "H4", "H1")
MINUT = {"MN1": 43200, "W1": 10080, "D1": 1440, "H12": 720, "H8": 480,
         "H4": 240, "H1": 60}
SKOLKO_BAROV = 3000


def kak_vremya(s):
    s = str(s or "").strip().replace("T", " ")
    for f in ("%Y.%m.%d %H:%M", "%Y.%m.%d", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:16] if " " in s else s[:10], f)
        except ValueError:
            continue
    return None


def mera(n) -> float:
    if not n or n <= 0:
        return 99.0
    if n < NORMA[0]:
        return NORMA[0] / n
    if n > NORMA[1]:
        return n / NORMA[1]
    return 1.0


def _fraktaly(highs, lows, lo, p):
    try:
        import volny_ao as _va
        return _va.fraktaly(highs, lows, lo, p)
    except Exception:
        verh, niz = [], []
        for i in range(max(lo, 2), p - 1):
            h, l = highs[i], lows[i]
            if h > highs[i - 1] and h > highs[i - 2] and h > highs[i + 1] and h > highs[i + 2]:
                verh.append(i)
            if l < lows[i - 1] and l < lows[i - 2] and l < lows[i + 1] and l < lows[i + 2]:
                niz.append(i)
        return verh, niz


def _bar_goroda() -> str:
    try:
        from hooks import load_trading_state
        return str(((load_trading_state() or {}).get("рынок") or {}).get("бар") or "")
    except Exception:
        return ""


class _Lenta:
    """Закрытые бары этажа до бара города: время, цены, AO, фракталы."""

    def __init__(self, symbol, tf):
        from feed_source import bars as _bars
        from williams_core import compute_ao_series
        b, _pt = _bars(symbol, tf, SKOLKO_BAROV)
        b = list(b or [])
        self.point = float(_pt or 0.00001)            # VOLNY_FRAKTALY_V1
        try:
            self.spread_pts = float((b[-1] if b else {}).get("spread") or 0)
        except Exception:
            self.spread_pts = 0.0
        try:
            from hooks import _tolko_zakrytye
            b = _tolko_zakrytye(b)
        except Exception:
            pass
        bar = _bar_goroda()
        if bar:
            b = [x for x in b if str(x.get("date", "")) <= bar]
        b = [(kak_vremya(x.get("date")), x) for x in b]
        b = [(t, x) for t, x in b if t is not None]
        self.tf = tf
        self.t = [t for t, _ in b]
        self.hi = [float(x["high"]) for _, x in b]
        self.lo = [float(x["low"]) for _, x in b]
        self.cl = [float(x.get("close", x["low"])) for _, x in b]   # VOLNY_OPYT_V1
        self.ao = list(compute_ao_series(self.hi, self.lo)) if b else []

    def __len__(self):
        return len(self.t)

    def posle(self, t0):
        return bisect.bisect_left(self.t, t0)

    def storona(self, vverh):
        if vverh:
            K, N, A = self.hi, self.lo, self.ao
        else:
            K = [-x for x in self.lo]
            N = [-x for x in self.hi]
            A = [(-x if x is not None else None) for x in self.ao]
        v, n = _fraktaly(K, N, 0, len(K) - 1)
        return K, N, A, set(v), set(n)


def _vybrat(rng, znach, frakt, bolshe):
    rng = list(rng)
    if not rng:
        return None, False
    fr = [i for i in rng if i in frakt]
    pool = fr or rng
    if bolshe:
        i = max(pool, key=lambda j: (znach[j], j))
    else:
        i = min(pool, key=lambda j: (znach[j], -j))
    return i, bool(fr)


def schet(K, N, A, VF, NF, S, p):
    """Счёт хода S..p (p — последний закрытый бар) по канону, в перевёрнутых
    рядах (ход всегда «вверх»). → словарь: точки, зоны, сейчас, заметки."""
    r = {"tochki": [("0", S, "dn", S in NF)], "zony": [], "seychas": "", "zametki": []}
    zam = r["zametki"]
    T = max(range(S, p + 1), key=lambda i: (K[i], i))
    r["T"] = T
    rng = [i for i in range(S, p + 1) if A[i] is not None]
    if len(rng) < 20:
        r["seychas"] = "мало баров с AO — счёт не начат"
        return r
    i3 = max(rng, key=lambda i: A[i])
    if A[i3] <= 0:
        r["seychas"] = "третьей ещё нет: AO в сторону хода за ноль не выходил"
        return r
    r["i3"] = i3
    p0 = i3
    while p0 - 1 >= S and A[p0 - 1] is not None and A[p0 - 1] > 0:
        p0 -= 1
    z = next((j for j in range(i3 + 1, p + 1) if A[j] is not None and A[j] < 0), None)

    j2 = None
    doliny = [j for j in range(p0 + 1, i3)
              if A[j - 1] is not None and A[j + 1] is not None and A[j - 1] > A[j] < A[j + 1]]
    if doliny:
        j2 = min(doliny, key=lambda j: A[j])
    if any(A[j] is not None and A[j] > 0 for j in range(S, p0)):
        zam.append("перед горбом третьей AO уже был над нулём и уходил под ноль — по "
                   "канону вторая за ноль не заходит: первая и вторая неясны")
        j2 = None
    elif j2 is None:
        zam.append("впадины над нулём перед третьей нет — первую и вторую по AO не "
                   "разделить (первой «почти не видно»)")

    e1 = e2 = None
    f1 = f2 = False
    if j2 is not None:
        e1, f1 = _vybrat(range(S + 1, j2 + 1), K, VF, True)
    konec3 = (z - 1) if z is not None else p
    e3, f3 = _vybrat(range((e1 + 1) if e1 is not None else S + 1, konec3 + 1), K, VF, True)
    if e1 is not None and e3 is not None:
        e2, f2 = _vybrat(range(e1 + 1, e3), N, NF, False)
        if e2 is None:
            e1 = None
        else:
            r["tochki"] += [("1", e1, "kr", f1), ("2", e2, "dn", f2)]
            if N[e2] <= N[S]:
                zam.append("норма нарушена: вторая ушла за начало первой")
    if e3 is None:
        r["seychas"] = "край третьей не нашёлся — счёт неясен"
        return r
    r["tochki"].append(("3", e3, "kr", f3))
    nach3 = e2 if e2 is not None else S
    L3 = K[e3] - N[nach3]
    Lhod = K[e3] - N[S]

    if z is None:
        posle = [j for j in range(i3 + 1, p)
                 if A[j - 1] is not None and A[j] is not None and A[j + 1] is not None
                 and A[j - 1] > A[j] < A[j + 1]]
        vnutri3 = False
        if posle and posle[0] < p:
            k_do = max(K[S:posle[0] + 1])
            k_posle = max(K[posle[0] + 1:p + 1])
            vnutri3 = k_posle > k_do
        if vnutri3:
            r["seychas"] = ("волны внутри третьей: после горба третьей меньший горб на "
                            "новом крае, а AO к нулю не возвращался — по канону ход ещё в "
                            "третьей")
        else:
            r["seychas"] = ("идёт третья: самый большой горб AO уже стоит, к нулю после "
                            "него AO не возвращался")
        r["vid"] = "третья"
        return r

    kon4 = T if T > e3 else p
    e4, f4 = _vybrat(range(e3 + 1, kon4 + (0 if T > e3 else 1)), N, NF, False)
    if e4 is None:
        r["seychas"] = "AO ушёл ниже нуля после третьей, дно четвёртой ещё не видно"
        r["vid"] = "четвёртая"
        return r
    if L3 > 0:
        r["zony"].append(("4-й (38–50% от третьей)", K[e3] - 0.38 * L3, K[e3] - 0.50 * L3))
    nyrki, bylo = 0, False
    for j in range(i3 + 1, p + 1):
        m = A[j] is not None and A[j] < 0
        if m and not bylo:
            nyrki += 1
        bylo = m
    if A[p] is not None and A[p] < 0:
        r["tochki"].append(("4", e4, "dn", f4))
        r["seychas"] = ("четвёртая: AO после третьей ниже нуля — минимум четвёртой "
                        "выполнен, пятой ещё нет")
        r["vid"] = "четвёртая"
        if nyrki > 1:
            zam.append(f"AO после третьей уходил под ноль {nyrki} раз(а) — четвёртая "
                       "сложная")
        return r
    r["tochki"].append(("4", e4, "dn", f4))
    if Lhod > 0:
        r["zony"].append(("5-й (62–100% хода от конца 4-й)", N[e4] + 0.618 * Lhod,
                          N[e4] + 1.0 * Lhod))
    zl = max(j for j in range(i3 + 1, p + 1) if A[j] is not None and A[j] < 0)
    h5 = max((j for j in range(zl + 1, p + 1) if A[j] is not None),
             key=lambda j: A[j], default=None)
    if T > zl and K[T] > K[e3]:
        r["tochki"].append(("5", T, "kr", T in VF))
        r["vid"] = "пятая"
        if h5 is not None and A[h5] < A[i3]:
            r["seychas"] = ("пятая: новый край цены при горбе AO ниже третьего — "
                            "дивер третьей и пятой")
        else:
            r["seychas"] = ("новый край после четвёртой, но горб AO не ниже третьего — "
                            "дивера третьей и пятой нет")
        if Lhod > 0:
            proshla = (K[T] - N[e4]) / Lhod
            zam.append(f"пятая прошла {proshla * 100:.0f}% длины хода до конца третьей "
                       "(зона 62–100%)")
    else:
        r["vid"] = "пятая идёт"
        r["seychas"] = ("после четвёртой AO снова над нулём, край третьей ещё не взят — "
                        "пятая идёт")
    if nyrki > 1:
        zam.append(f"AO после третьей уходил под ноль {nyrki} раз(а): четвёртая сложная "
                   "или пятая растягивалась")
    if e1 is not None and N[e4] <= K[e1]:
        zam.append("норма нарушена: четвёртая зашла на территорию первой")
    return r


def _nachalo_hoda(L, vverh, ot):
    """Ход сделки: край — крайняя цена с бара ot; начало — самый низкий низ
    (вниз — высокий верх) назад до первого бара за краем."""
    K, N, _A, _v, _n = L.storona(vverh)
    p = len(L) - 1
    T = max(range(ot, p + 1), key=lambda i: (K[i], i))
    k = T - 1
    while k >= 0 and K[k] < K[T]:
        k -= 1
    if T - (k + 1) < 1:
        return None, T
    S = min(range(k + 1, T + 1), key=lambda i: (N[i], -i))
    return S, T


def _fmt(L, i):
    t = L.t[i]
    return t.strftime("%Y.%m.%d") if L.tf in ("W1", "D1", "MN1") else t.strftime("%Y.%m.%d %H:%M")


# VOLNY_VLOZHENNOST_V1 (28.10) — ход сделки и старший ход, вложенность прямо.
# Слово Шефа 28.10: «по канону правильней — это из-за фрактальности, вложенности»;
# «если на вход не влияет — делаем». Ход, в котором житель вошёл, город держит
# на том этаже, где тот впервые лёг в 100–140 баров, и считает до конца сделки.
# Вырос ход — рядом строка старшего хода на своём этаже, по канону.
def _zakrep_chitat(put):
    try:
        return json.loads(Path(put).read_text(encoding="utf-8")) if put else {}
    except Exception:
        return {}


def _zakrep_pisat(put, d):
    if not put:
        return
    try:
        Path(put).parent.mkdir(parents=True, exist_ok=True)
        Path(put).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        print(f"[ВОЛНЫ ПО КАНОНУ] закрепить ход сделки не вышло ({e})")


def _hod_na_etazhe(symbol, tf, t_s, tf0, vverh, lenty):
    L = lenty.get(tf) or _Lenta(symbol, tf)
    lenty[tf] = L
    if len(L) < 60:
        return None
    K, N, A, VF, NF = L.storona(vverh)
    if MINUT.get(tf, 0) > MINUT.get(tf0, 1440):
        # старший этаж: начало — бар, внутри которого лежит начало хода
        S = max(0, L.posle(t_s + timedelta(minutes=1)) - 1)
    else:
        konec_s = t_s + timedelta(minutes=MINUT.get(tf0, 1440))
        vnutri = list(range(L.posle(t_s), L.posle(konec_s))) or [min(L.posle(t_s), len(L) - 1)]
        S = min(vnutri, key=lambda i: (N[i], -i))
    p = len(L) - 1
    r = schet(K, N, A, VF, NF, S, p) if p - S >= 20 else None
    sloman = any(N[i] < N[S] for i in range(S + 1, p + 1))
    return {"L": L, "S": S, "p": p, "r": r, "sloman": sloman, "tf": tf}


def _stroki_hoda(h, vverh):
    L, r = h["L"], h["r"]
    imena = {"0": "начало хода", "1": "край первой", "2": "конец второй",
             "3": "край третьей", "4": "дно четвёртой" if vverh else "верх четвёртой",
             "5": "край пятой"}

    def cena(i, tip):
        if tip == "kr":
            return L.hi[i] if vverh else L.lo[i]
        return L.lo[i] if vverh else L.hi[i]
    out = []
    if r is None:
        return [f"  пока короткий (баров — {h['p'] - h['S']}) — считать рано."]
    for nm, i, tip, sf in r["tochki"]:
        out.append(f"  {nm} — {imena.get(nm, nm)}: {cena(i, tip):.5f} ({_fmt(L, i)})"
                   + ("" if sf else ", без подтверждённого фрактала"))
    if r.get("i3") is not None:
        out.append(f"  самый большой горб AO (третья) — {_fmt(L, r['i3'])}.")
    for imya, z1, z2 in r["zony"]:
        a, b = (z1, z2) if vverh else (-z1, -z2)
        out.append(f"  зона {imya}: {min(a, b):.5f}–{max(a, b):.5f}.")
    out.append(f"  сейчас: {r['seychas']}.")
    if r["zametki"]:
        out.append("  заметки: " + "; ".join(r["zametki"]) + ".")
    return out


def _vid(h):
    if h is None or h.get("r") is None:
        return "счёт не начат"
    return h["r"].get("vid") or "счёт неясен"


# VOLNY_LESENKA_V1 (28.10) — лесенка этажей: перерос этаж — счёт этажа заморожен.
# Слово Шефа 28.10: «пробуем». По канону ход, переросший свой этаж (больше
# 140 баров с допуском), там больше не считается: последний честный счёт этого
# этажа город запоминает и больше не трогает. Живой счёт — на этаже, где ход
# сейчас помещается в 100–140. Так закончившееся не превращается обратно.
def _hod_vverh_etazhi():
    return sorted(ETAZHI, key=lambda e: MINUT.get(e, 0))


POSLEDNEE = {}   # VOLNY_OPYT_V1: последнее состояние волн, которое город посчитал


def _kategoriya(h) -> str:
    """Волновая ситуация одним словом — по ней ищутся похожие случаи."""
    if h is None or h.get("r") is None:
        return "счёт не начат"
    r = h["r"]
    s = str(r.get("seychas") or "")
    if s.startswith("пятая: новый край"):
        return "пятая с дивером"
    if "дивера третьей и пятой нет" in s:
        return "пятая без дивера"
    if s.startswith("волны внутри третьей"):
        return "волны внутри третьей"
    return str(r.get("vid") or "счёт неясен")


def blok_sdelki(symbol, poz, rabochiy="D1", zakrep=None) -> tuple:
    """(текст блока, коротко для лога). Только факт, без советов.
    zakrep — файл места, где город помнит лесенку хода сделки."""
    napr = str((poz or {}).get("direction") or "").upper()
    if napr not in ("LONG", "SHORT"):
        return "", ""
    vverh = napr == "LONG"
    hod = "вверх" if vverh else "вниз"
    tf0 = str((poz or {}).get("timeframe") or rabochiy or "D1").upper()
    zag = "=== ВОЛНЫ ТВОЕГО ХОДА — ФАКТ ГОРОДА, ПО КАНОНУ ==="
    hvost = ("Это факт города, не приказ. Что происходит и что делать со сделкой — "
             "решаешь ты, по своему анализу. Как волны выглядят на настоящей истории — "
             "альбом, рукой albom_voln.")
    try:
        L0 = _Lenta(symbol, tf0)
    except Exception as e:
        return (f"{zag}\nГород посчитать не смог (нет баров {tf0}: {e}).", "нет баров")
    if len(L0) < 60:
        return (f"{zag}\nГород посчитать не смог: мало баров {tf0}.", "мало баров")
    t_vh = kak_vremya((poz or {}).get("opened_at"))
    ot = L0.posle(t_vh) if t_vh else max(0, len(L0) - 140)
    ot = max(0, min(ot, len(L0) - 1) - 1)
    S0, _T0 = _nachalo_hoda(L0, vverh, ot)
    if S0 is None:
        return (f"{zag}\nТы в {napr} — твой ход {hod} ещё не начался по барам {tf0} — "
                "считать нечего.\n" + hvost, "хода нет")
    t_s = L0.t[S0]
    nach = t_s.strftime("%Y.%m.%d %H:%M")
    POSLEDNEE.clear()
    POSLEDNEE.update({"сост": "живого счёта нет", "close": L0.cl[-1] if L0.cl else None,
                      "бар": _fmt(L0, len(L0) - 1)})

    try:
        from hooks import load_trading_state as _lts_v
        run = str(((_lts_v() or {}).get("прогон") or {}).get("id") or "")
    except Exception:
        run = ""
    klyuch = f"{run}|{str((poz or {}).get('opened_at') or '')[:16]}|{(poz or {}).get('entry')}"
    pamyat = _zakrep_chitat(zakrep)
    zp = pamyat.get(klyuch)
    smena = ""
    if not isinstance(zp, dict) or "этажи" not in zp:
        zp = {"начало": nach, "этажи": {}}
    elif zp.get("начало") != nach:
        if nach < str(zp.get("начало") or ""):
            smena = (f"Ход вырос: цена взяла прежний край, и начало хода теперь раньше — "
                     f"{nach} (было {zp.get('начало')}). Это ход крупнее; лесенка начата "
                     "заново от его начала.")
        else:
            smena = (f"Прежний ход сломан: цена ушла за его начало ({zp.get('начало')}). "
                     f"Счёт начат заново от {nach}.")
        zp = {"начало": nach, "этажи": {}}

    lenty = {tf0: L0}
    zhivye, verh_gran = [], NORMA[1] * DOPUSK
    for tf in _hod_vverh_etazhi():
        try:
            L = lenty.get(tf) or _Lenta(symbol, tf)
        except Exception:
            continue
        if len(L) < 60 or L.t[0] > t_s:
            continue
        lenty[tf] = L
        n = len(L) - 1 - L.posle(t_s)
        m = mera(n)
        if n > verh_gran:
            if tf in zp["этажи"]:
                zp["этажи"][tf]["закончен"] = True
            continue
        if m > DOPUSK:
            continue            # мелковат — до этого этажа ход ещё не дорос
        h = _hod_na_etazhe(symbol, tf, t_s, tf0, vverh, lenty)
        if h is None or h.get("r") is None:
            continue
        h["m"], h["n"] = m, n
        zhivye.append(h)
        zp["этажи"][tf] = {"вид": _vid(h), "сейчас": h["r"]["seychas"],
                           "бар": _fmt(h["L"], h["p"]), "баров": n, "закончен": False}
    pamyat[klyuch] = zp
    _zakrep_pisat(zakrep, pamyat)

    zhivoy = min(zhivye, key=lambda h: (h["m"], -MINUT.get(h["tf"], 0))) if zhivye else None
    zakoncheny = [(tf, zp["этажи"][tf]) for tf in _hod_vverh_etazhi()
                  if tf in zp["этажи"] and zp["этажи"][tf].get("закончен")]

    _cena0 = (L0.lo if vverh else L0.hi)[S0]
    Ls = [zag, f"Ты в {napr} — твой ход {hod}, начало {_cena0:.5f} ({_fmt(L0, S0)})."]
    if smena:
        Ls.append(smena)
        POSLEDNEE["смена"] = "прежний ход сломан" if "сломан" in smena else "ход вырос"
    if zakoncheny:
        Ls.append("ЛЕСЕНКА — младшие этажи, где ход уже перерос масштаб; их счёт закончен "
                  "и больше не меняется:")
        for tf, z in zakoncheny:
            Ls.append(f"  {tf} — закончен на баре {z.get('бар')}: {z.get('вид')} — "
                      f"{z.get('сейчас')}.")
    kratko = " · ".join(f"{tf} {z.get('вид')} (зак.)" for tf, z in zakoncheny)
    if zhivoy is None:
        Ls.append("ЖИВОГО СЧЁТА СЕЙЧАС НЕТ: ход ни на одном этаже не ложится в 100–140 "
                  "баров" + (" — перерос младший, до старшего ещё не дорос."
                             if zakoncheny else " — он ещё мал.")
                  + " По нулю AO сейчас не судим.")
        kratko = (kratko + " · " if kratko else "") + "живого нет"
    else:
        Ls.append(f"СЕЙЧАС — на {zhivoy['tf']}: баров от начала — {zhivoy['n']}, "
                  + ("масштаб точный." if zhivoy["m"] <= 1.0 + 1e-9 else "масштаб с допуском."))
        if zhivoy.get("sloman"):
            Ls.append("  цена ушла за начало хода — по канону ход сломан.")
        Ls += _stroki_hoda(zhivoy, vverh)
        drugie = [h for h in zhivye if h is not zhivoy]
        for h in drugie:
            Ls.append(f"  (на {h['tf']} ход тоже ещё помещается, баров {h['n']}: {_vid(h)} — "
                      f"{h['r']['seychas']})")
        if zakoncheny:
            Ls.append(f"ВЛОЖЕННОСТЬ: младшие ходы ({', '.join(tf for tf, _ in zakoncheny)}) "
                      f"свой счёт закончили; ход на {zhivoy['tf']} ещё живой — он старше и "
                      "вмещает их.")
        kratko = (kratko + " · " if kratko else "") + f"{zhivoy['tf']} живой: {_vid(zhivoy)}"
        POSLEDNEE["сост"] = _kategoriya(zhivoy)
        POSLEDNEE["этаж"] = zhivoy["tf"]
    Ls.append(hvost)
    return "\n".join(Ls), kratko


# ── альбом места ──────────────────────────────────────────────────
def _papka_alboma(ceh, slot) -> Path:
    return _TSEHA / str(ceh) / "слоты" / str(slot) / "альбом_волн"


def albom(ceh, slot, nomer=None) -> str:
    p = _papka_alboma(ceh, slot)
    try:
        d = json.loads((p / "альбом.json").read_text(encoding="utf-8"))
    except Exception:
        return "Альбома у этого места пока нет."
    pr = d.get("примеры") or []
    if not pr:
        return "Альбом пуст."
    s = str(nomer or "").strip()
    if not s:
        L = ["Альбом волн — разметка города по канону на настоящей истории GBPUSD. "
             "Это не твой рынок, а образцы. Позови снова с номером — покажу картинку."]
        for x in pr:
            L.append(f"{x['номер']}. {x['вид']} — {x['кратко']}")
        return "\n".join(L)
    x = next((x for x in pr if str(x.get("номер")) == s.lstrip("№ ").strip()), None)
    if not x:
        return f"Примера «{s}» нет. Номера: {', '.join(str(y['номер']) for y in pr)}."
    f = p / x["файл"]
    if not f.is_file():
        return f"Картинки примера {x['номер']} нет на месте. Подпись: {x['описание']}"
    return f"[КАДР: {f}] Образец из альбома, не твой рынок. {x['описание']}"


# VOLNY_KANON_V1 - marker
# VOLNY_VLOZHENNOST_V1 - marker
# VOLNY_LESENKA_V1 - marker


# ══ VOLNY_OPYT_V1 — волны в опыте жителя; похожие случаи — на стол в сделке ══
# Слово Шефа 28.10: «мне не дата важна… а похожие ситуации, чтобы видела и
# анализировала с опытом» — «да». На каждом пробуждении в сделке город пишет:
# какая волновая ситуация, сколько R было. В конце прогона — эпизоды жителю
# домой: ситуация (как писал город) → что она сделала → чем кончилось.
# Когда та же ситуация повторяется — рядом её похожие случаи и её осмысления.
_KOVCHEG = _BIRZHA.parent / "GRONDHEIM_CITY" / "жители" / "ковчег"
EPIZODY = "волны_эпизоды.jsonl"         # у места, по каждому пробуждению
OPYT_VOLN = ("опыт", "волны.jsonl")     # у жителя дома
SLUCHAEV = 4


def _jsonl(p) -> list:
    out = []
    try:
        for ln in Path(p).read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def r_seychas(poz, close):
    """R сделки на закрытии бара: от входа, мерой первого риска."""
    try:
        e = float(poz.get("entry"))
        s = float(poz.get("stop_initial") or poz.get("stop"))
        c = float(close)
        if str(poz.get("direction") or "").upper() != "LONG":
            c += float(POSLEDNEE.get("спред") or 0)    # шорт закрывается по Ask
        risk = abs(e - s)
        if risk <= 0:
            return None
        znak = 1 if str(poz.get("direction") or "").upper() == "LONG" else -1
        return round(znak * (c - e) / risk, 3)
    except Exception:
        return None


def epizody_progona(ceh, slot, run) -> list:
    """[(житель, эпизод)] — по каждой сделке прогона и каждой волновой ситуации в ней."""
    try:
        import opyt_stola as _os
    except Exception:
        return []
    papka = _TSEHA / str(ceh) / "слоты" / str(slot) / "данные"
    probuzh = [z for z in _jsonl(papka / EPIZODY) if z.get("прогон") == run and z.get("сост")]
    if not probuzh:
        return []
    resheniya, videla = {}, {}
    for z in _jsonl(papka / "три_слова.jsonl"):
        if z.get("прогон") == run:
            resheniya[(str(z.get("сделка") or ""), str(z.get("бар") or "")[:10])] = \
                str(z.get("что") or "").upper()
            # VOLNY_GOLOS_V2: что она сама видела на этом баре — её разбор места
            videla[(str(z.get("сделка") or ""), str(z.get("бар") or "")[:10])] = \
                str(z.get("место") or "").strip()
    itogi = {}
    for kto, r in _os.zapisi_progona(ceh, slot, run) or []:
        itogi[str(r.get("открыта") or "")[:16]] = (kto, r)
    po = {}
    for z in sorted(probuzh, key=lambda z: str(z.get("бар") or "")):
        sd = str(z.get("сделка") or "")
        po.setdefault(sd, []).append(z)
    out = []
    for sd, rr in po.items():
        it = itogi.get(sd.split("|")[0][:16])
        if not it:
            continue
        kto, rec = it
        R_itog = rec.get("R")
        videl = {}
        for z in rr:
            st = z.get("сост")
            resh = resheniya.get((sd, str(z.get("бар") or "")[:10]), "")
            _vid_bar = videla.get((sd, str(z.get("бар") or "")[:10]), "")
            v = videl.setdefault(st, {"R_тогда": z.get("R"), "бар": z.get("бар"),
                                      "решение": "держала", "раз": 0, "R_макс": None,
                                      "видела": _vid_bar})
            if not v.get("видела") and _vid_bar:
                v["видела"] = _vid_bar
            v["раз"] += 1
            if isinstance(z.get("R"), (int, float)) and (
                    v["R_макс"] is None or z["R"] > v["R_макс"]):
                v["R_макс"] = z["R"]
            if resh == "CLOSE" and v["решение"] != "закрыла":
                v.update({"решение": "закрыла", "R_тогда": z.get("R"), "бар": z.get("бар"),
                          "видела": _vid_bar or v.get("видела")})
        for st, v in videl.items():
            out.append((kto, {"прогон": run, "цех": ceh, "слот": slot, "сделка": sd,
                              "год": sd[:4], "сторона": rec.get("сторона"),
                              "сост": st, "решение": v["решение"], "бар": v["бар"],
                              "R_тогда": v["R_тогда"], "R_макс": v["R_макс"], "R_итог": R_itog,
                              "пробуждений": v["раз"], "место": rec.get("место"),
                              "видела": (v.get("видела") or "")[:600]}))
    return out


def _fayl_opyta_voln(imya) -> Path:
    return _KOVCHEG / str(imya) / OPYT_VOLN[0] / OPYT_VOLN[1]


def zapisat_iz_progona(papka, ceh) -> list:
    papka = Path(papka)
    try:
        sloty = sorted({json.loads(s).get("слот") for s in
                        (papka / "места.jsonl").read_text(encoding="utf-8").splitlines()
                        if s.strip()} - {None})
    except Exception:
        sloty = []
    out = []
    for sl in sloty:
        try:
            man = json.loads((_TSEHA / str(ceh) / "manifest.json").read_text(encoding="utf-8"))
            z = next((x for x in man.get("слоты") or []
                      if str(x.get("слот") or "").upper() == str(sl).upper()), {})
            if str(z.get("волны") or "").lower() != "по канону":
                continue
        except Exception:
            continue
        po = {}
        for kto, e in epizody_progona(ceh, sl, papka.name):
            po.setdefault(kto, []).append(e)
        for kto, ee in po.items():
            f = _fayl_opyta_voln(kto)
            if not f.parent.parent.is_dir():
                continue
            f.parent.mkdir(parents=True, exist_ok=True)
            uzhe = {(x.get("прогон"), x.get("сделка"), x.get("сост")) for x in _jsonl(f)}
            nov = [e for e in ee if (e["прогон"], e["сделка"], e["сост"]) not in uzhe]
            if nov:
                with open(f, "a", encoding="utf-8") as fh:
                    for e in nov:
                        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            out.append(f"{kto}: волны в опыте — {len(nov)} новых случаев")
    return out


def _osm_sdelki(imya, run, sdelka) -> str:
    try:
        import sys as _s
        g = str(_BIRZHA.parent / "ГОРОД")
        if g not in _s.path:
            _s.path.insert(0, g)
        import osmyslenie as _om
        den = str(sdelka)[:10]
        for r in _om.zapisi_raboty(_KOVCHEG / str(imya)):
            if r.get("прогон") == run and den in str(r.get("ситуация") or ""):
                return str(r.get("осмысление") or "").strip()
    except Exception:
        pass
    return ""


def _r(x):
    try:
        return f"{float(x):+.2f}R".replace("-", "−")
    except Exception:
        return "—"


def pohozhie(imya, sost, god=None, run=None, sdelka=None) -> list:
    """VOLNY_GOLOS_V1: внутренний голос — её прошлые случаи с той же волновой
    ситуацией, её фактами и от первого лица. Скрыта только та же самая сделка
    (повтор того же отрезка), остальное видно — по ситуации, не по дате."""
    if not imya or not sost or sost in ("живого счёта нет", "счёт не начат"):
        return []
    ee = [e for e in _jsonl(_fayl_opyta_voln(imya)) if e.get("сост") == sost]
    if sdelka:
        ee = [e for e in ee if str(e.get("сделка")) != str(sdelka)]
    elif god:
        ee = [e for e in ee if str(e.get("год")) != str(god) and e.get("прогон") != run]
    if not ee:
        return []
    L = [f"ВНУТРЕННИЙ ГОЛОС — мои прошлые случаи, когда город писал «{sost}»:"]
    for e in sorted(ee, key=lambda e: str(e.get("прогон")), reverse=True)[:SLUCHAEV]:
        if e.get("решение") == "держала" and isinstance(e.get("R_макс"), (int, float)):
            s = (f"  · {e.get('год')}, {e.get('сторона') or '—'}: я держала, было до "
                 f"{_r(e.get('R_макс'))} — сделка кончилась {_r(e.get('R_итог'))}.")
        else:
            s = (f"  · {e.get('год')}, {e.get('сторона') or '—'}: я закрыла при "
                 f"{_r(e.get('R_тогда'))}.")
        vid = str(e.get("видела") or "").strip()
        if vid:
            s += f"\n    Тогда я видела: «{vid[:260]}»"
        o = _osm_sdelki(imya, e.get("прогон"), e.get("сделка"))
        if o:
            s += f"\n    После сделки сказала себе: «{o[:200]}»"
        L.append(s)
    L.append("Что я вижу сейчас — и что иначе, чем тогда?")
    return L


# ══ VOLNY_KOROTKO_V1 — волны жителю одной строкой; подробности — в лог ══
# Слово Шефа 28.10: «про волны конечно муть… я вообще не понимаю, что он там
# смотрит» — «пробуем»: факт города одной строкой, простыня — в лог.
# VOLNY_SVOYSTVA_V1 (28.10) — не номер, а свойства волны: какая она и что обычно дальше.
# Слово Шефа 28.10: «не столько важен счёт, 5 или 10, а важны свойства — например
# третья: как выглядит, почему, куда ходит». Источник — книга второго уровня
# (Вильямс, гл. 7, «Характеристики различных волн»), своими словами, без добавок.
_SVOYSTVA = {
    "третья": (
        "третья",
        "круче первой — цена идёт быстрее, иногда почти вертикально; самый выгодный "
        "участок хода, AO на своём самом большом горбе. По длине обычно от 1 до 1.62 "
        "длины первой, чаще около 1.62; короче первой бывает крайне редко.",
        "четвёртая — взятие прибыли. Конец третьей ищут по признакам: дивер, целевая "
        "зона, фрактал, приседающий, смена моментума."),
    "волны внутри третьей": (
        "третья растягивается — внутри неё свои пять волн меньшего масштаба",
        "конец пятой внутри неё и будет концом третьей; сам ход не кончился.",
        "после конца третьей — четвёртая."),
    "четвёртая": (
        "четвёртая",
        "волна взятия прибыли, а не новых входов: обычно дольше и мельче второй, "
        "сила и моментум падают. Если вторая была простой (зигзаг), четвёртая — "
        "сложная, боковая (флэт, треугольник) — чередование. Большинство обманных "
        "рывков бывает именно здесь. Чаще всего откатывает 38–50% третьей и по "
        "правилу не заходит за вершину первой.",
        "пятая — от конца четвёртой."),
    "пятая идёт": (
        "пятая",
        "последний шанс обновить край: без размаха третьей, наклон положе; опытные "
        "забирают прибыль, новички ещё входят. Её цель — зона: от конца четвёртой "
        "на 62–100% хода от начала до конца третьей.",
        "после пятой — коррекция a-b-c."),
    "пятая с дивером": (
        "пятая, и AO ниже горба третьей — дивер",
        "последний рывок хода, без размаха третьей; дивер между третьей и пятой — "
        "один из признаков конца (вместе с целевой зоной, фракталом, приседающим, "
        "сменой моментума).",
        "коррекция a-b-c: «b» обычно не больше 62% от «a», «c» — сильная, как "
        "третья, только против хода."),
    "пятая без дивера": (
        "новый край после четвёртой, но AO не ниже горба третьей",
        "признака конца — дивера между третьей и пятой — пока нет; движение может "
        "ещё тянуться.",
        "конец пятой ищут по признакам: дивер, целевая зона, фрактал, приседающий."),
    "живого счёта нет": (
        "ход сейчас не ложится в 100–140 баров",
        "волны не номерую — по нулю AO на этом масштабе не сужу.",
        ""),
}


def blok_sdelki_polnyy(*a, **kw):
    return _blok_sdelki_lesenka(*a, **kw)


_blok_sdelki_lesenka = blok_sdelki


def blok_sdelki(symbol, poz, rabochiy="D1", zakrep=None) -> tuple:   # noqa: F811
    POSLEDNEE.clear()
    polnyy, kratko = _blok_sdelki_lesenka(symbol, poz, rabochiy, zakrep)
    if not polnyy:
        return polnyy, kratko
    for s in polnyy.splitlines():
        print(f"[ВОЛНЫ ПОДРОБНО] {s}")
    sost = POSLEDNEE.get("сост")
    if not sost:
        return "ВОЛНЫ ТВОЕГО ХОДА (факт города): посчитать не вышло.", kratko
    imya, kakaya, dalshe = _SVOYSTVA.get(sost, (sost, "", ""))
    gde = f", ход на {POSLEDNEE['этаж']}" if POSLEDNEE.get("этаж") else ""
    smena = f" ({POSLEDNEE['смена']})" if POSLEDNEE.get("смена") else ""
    L = [f"ВОЛНЫ ТВОЕГО ХОДА (факт города): сейчас {imya}{gde}{smena}."]
    if kakaya:
        L.append(f"Какая она: {kakaya}")
    if dalshe:
        L.append(f"Что обычно дальше: {dalshe}")
    L.append("Факт и свойства из книги, не приказ.")
    return "\n".join(L), kratko


# VOLNY_OPYT_V1 - marker
# VOLNY_GOLOS_V1 - marker
# VOLNY_KOROTKO_V1 - marker
# VOLNY_SVOYSTVA_V1 - marker
# VOLNY_GOLOS_V2 - marker


# ══ VOLNY_FRAKTALY_V1 (28.10) — рывки и откаты по фракталам: наблюдение отдельно ══
# Слово Шефа 28.10: «путает счёт… это только наша разметка, а не факт… упростить» —
# «импульс–откат и свойства»; глава 8 — «да». Поправки Софии — «да»: наблюдение,
# толкование и решение раздельно; стоп не трогать (по канону стоит с входа);
# рычаг — мера, а не «сигнал жив»; фрактал — по книге; этаж — этаж сделки.
_TOLKOVANIE_FR = {
    "рывок, сила растёт": (
        "движение может набирать силу — по книге моментум похож на катящийся мяч, "
        "пока не встретит сопротивление сильнее себя."),
    "рывок, сила слабеет": (
        "новый край при меньшей силе — расхождение; по книге это может быть "
        "признаком истощения движения."),
    "отрезок без нового края": (
        "по книге каждый фрактал — смена поведения: рынок снова пошёл по сделке, но "
        "края сделки этот отрезок не обновил."),
    "откат мелкий": (
        "неглубокий откат; по книге после рывка рынок обычно откатывает — мелкий "
        "откат может быть паузой в движении."),
    "откат средний": (
        "откат 38–62% — по книге обычная глубина коррекции; пауза это или разворот, "
        "по одной глубине не определить."),
    "откат глубокий": (
        "откат больше 62% — рынок вернул большую часть рывка; по книге долгий "
        "глубокий откат с AO за нулём бывает при взятии прибыли."),
    "цена за началом рывка": (
        "по книге (рычаг): цена вернула весь размах последнего рывка — рычаг этого "
        "движения израсходован."),
    "внутренний отрезок возвращён": (
        "цена вернула начало последнего внутреннего плеча. Это факт о локальном "
        "движении, но само по себе он не доказывает слом родительского хода."),
    "ход сломан": (
        "рынок вернул весь размах хода, в котором ты вошла."),
}


def fraktaly_kniga(highs, lows, p):
    """Фрактал по книге (гл. 8): средний бар выше двух баров слева и двух справа;
    бар на одной высоте со средним в счёт не идёт (тогда нужно больше баров).
    РЕШЕНИЕ РЕАЛИЗАЦИИ (не требование книги): из равных вершин — в том числе
    разделённых одним баром — фракталом считается первая."""
    def odin(vals, i, bolshe):
        x = vals[i]

        def nizhe(y):
            return y < x if bolshe else y > x
        # слева: два ниже; равный слева — фрактал у него, не у нас
        n, j = 0, i - 1
        while j >= 0 and n < 2:
            if vals[j] == x:
                return False
            if not nizhe(vals[j]):
                return False
            n += 1
            j -= 1
        if n < 2:
            return False
        # справа: два ниже; равные пропускаем
        n, j = 0, i + 1
        while j <= p and n < 2:
            if vals[j] == x:
                j += 1
                continue
            if not nizhe(vals[j]):
                return False
            n += 1
            j += 1
        return n >= 2
    verh = {i for i in range(2, p + 1) if odin(highs, i, True)}
    niz = {i for i in range(2, p + 1) if odin(lows, i, False)}
    return verh, niz


def _zigzag(K, N, VF, NF, S, p):
    """Чередование подтверждённых фракталов от начала хода: [(i, 'v'|'n')]."""
    tochki = [(S, "n")]
    for i in sorted({j for j in VF if S < j <= p} | {j for j in NF if S < j <= p}):
        vid = "v" if i in VF else "n"
        if i in VF and i in NF:
            vid = "v" if K[i] >= K[tochki[-1][0]] else "n"
        if tochki[-1][1] == vid:
            pr = tochki[-1][0]
            if (vid == "v" and K[i] >= K[pr]) or (vid == "n" and N[i] <= N[pr]):
                tochki[-1] = (i, vid)
        else:
            tochki.append((i, vid))
    return tochki


def _porog_ceny(L) -> float:
    """Спред и один тик — меньше этого «прошла начало» не считаем (спред,
    проскальзывание). Спред — как у города (SPRED_ZDRAVYY), иначе пункты × тик."""
    sp = 0.0
    try:
        import hooks as _h_sp
        sp = float(_h_sp._spred_zdravyy_cena(L.spread_pts, L.point) or 0)
    except Exception:
        sp = float(L.spread_pts or 0) * float(L.point or 0)
    return sp + float(L.point or 0)


def _bar_vhoda(L, N, ot, poz, vverh):
    """Начало сделки — разворотный бар, за которым стоит её стоп: из баров у
    входа — тот, чей край ближе всего к стопу. Стопа нет — бар перед входом."""
    try:
        st = float((poz or {}).get("stop_initial") or (poz or {}).get("stop"))
        nst = st if vverh else -st
        return min(range(max(0, ot - 5), ot + 1), key=lambda j: (abs(N[j] - nst), -j))
    except Exception:
        return max(0, ot - 1)


def blok_sdelki_fraktaly(symbol, poz, rabochiy="D1"):
    """(текст, кратко). Наблюдение — толкование — решение, на этаже сделки."""
    POSLEDNEE.clear()
    napr = str((poz or {}).get("direction") or "").upper()
    if napr not in ("LONG", "SHORT"):
        return "", ""
    vverh = napr == "LONG"
    tf0 = str((poz or {}).get("timeframe") or rabochiy or "D1").upper()
    zag = f"ВОЛНЫ ТВОЕГО ХОДА (факты по фракталам, {tf0}):"
    resh = ("Решение — твоё: относительно места сделки (как взяла — так и ведёшь; "
            "место меняется, только если реально изменился старший), с учётом своего опыта.")
    try:
        L = _Lenta(symbol, tf0)
    except Exception as e:
        return f"{zag} посчитать не вышло ({e}).", "нет баров"
    if len(L) < 60:
        return f"{zag} мало баров.", "мало баров"
    K, N, A, _vf, _nf = L.storona(vverh)
    p = len(L) - 1
    VF, NF = fraktaly_kniga(K, N, p)
    # Контекст ДО входа показываем отдельно от счёта сделки.
    # Только подтверждённые фракталы рабочего этажа; никаких автоматических номеров волн.
    VF0, NF0 = fraktaly_kniga(L.hi, L.lo, p)
    t_vh = kak_vremya((poz or {}).get("opened_at"))
    ot = L.posle(t_vh) if t_vh else max(0, p - 140)
    ot = max(0, min(ot, p))
    S = _bar_vhoda(L, N, ot, poz, vverh)
    porog = _porog_ceny(L)

    # Опорный D1-отрезок расчёта сделки. Это не родительский сегмент MN1→D1.
    # Номеров волн здесь нет: только начало и текущий край родительского движения.
    S0, T0 = _nachalo_hoda(L, vverh, ot)
    roditel_est = S0 is not None and T0 is not None and S0 <= T0

    def cena_v(x):
        return x if vverh else -x

    POSLEDNEE.update({"close": L.cl[-1] if L.cl else None, "бар": _fmt(L, p),
                      "этаж": tf0, "спред": max(0.0, porog - float(L.point or 0)),
                      "запас": "спред+тик" if L.spread_pts else "только тик"})
    if not L.spread_pts:
        print(f"[ФРАКТАЛЫ ПОДРОБНО] запас — только тик: спреда в истории {tf0} нет")
    if min(N[S + 1:p + 1] or [N[S]]) < N[S] - porog:
        POSLEDNEE["сост"] = "ход сломан"
        t = (f"{zag}\nНаблюдение: цена прошла начало сделки — край разворотного бара "
             f"{cena_v(N[S]):.5f} ({_fmt(L, S)}) — больше чем на спред и тик.\n"
             f"Толкование (из книги, может не совпасть): {_TOLKOVANIE_FR['ход сломан']}\n{resh}")
        return t, "ход сломан"

    zz = _zigzag(K, N, VF, NF, S, p)
    # все попутные отрезки: от каждого нижнего фрактала до следующего верхнего
    legs = []
    for k in range(1, len(zz)):
        i, vid = zz[k]
        if vid == "v":
            legs.append({"nach": zz[k - 1][0], "kray": i})
    posl_t, posl_vid = zz[-1]
    if posl_vid == "n":
        hv = [j for j in range(posl_t + 1, p + 1)]
        if hv:
            T = max(hv, key=lambda j: (K[j], j))
            if K[T] > N[posl_t]:
                legs.append({"nach": posl_t, "kray": T, "idyot": True})
    else:
        hv = [j for j in range(posl_t + 1, p + 1) if K[j] > K[posl_t]]
        if hv:
            legs[-1]["kray"] = max(hv, key=lambda j: (K[j], j))
    if not legs:
        T = max(range(S, p + 1), key=lambda j: (K[j], j))
        legs.append({"nach": S, "kray": T, "idyot": True})
    maks = K[S]
    for lg in legs:
        lg["razmah"] = K[lg["kray"]] - N[lg["nach"]]
        lg["sila"] = max((A[j] for j in range(lg["nach"], lg["kray"] + 1) if A[j] is not None),
                         default=None)
        lg["obnovil"] = K[lg["kray"]] > maks
        maks = max(maks, K[lg["kray"]])
    posl = legs[-1]
    pred = legs[-2] if len(legs) > 1 else None
    oslab = (pred is not None and posl["sila"] is not None and pred["sila"] is not None
             and posl["sila"] < pred["sila"])
    bez_kraya = p - posl["kray"]
    dlina = posl["razmah"]
    cl = L.cl[p] if vverh else -L.cl[p]
    otdal = max(0.0, (K[posl["kray"]] - cl) / dlina) if dlina > 0 else 0.0
    # Проход начала последнего локального плеча и проход начала родительского
    # хода — разные события. Только второе означает слом родительского движения.
    za_nachalom_vnutrennego = any(
        N[j] < N[posl["nach"]] - porog
        for j in range(posl["kray"] + 1, p + 1))
    za_nachalom_roditelskogo = bool(roditel_est and any(
        N[j] < N[S0] - porog for j in range(S0 + 1, p + 1)))
    ao_za_nol = any(A[j] is not None and A[j] < 0 for j in range(posl["kray"], p + 1))

    # S0 найден от опорной точки расчёта сделки, а не от родительской
    # границы MN1→D1. Его проход нельзя объявлять сломом всего родительского хода.
    if za_nachalom_roditelskogo or za_nachalom_vnutrennego:
        sost = "внутренний отрезок возвращён"
    elif bez_kraya <= 2 and not posl["obnovil"]:
        sost = "отрезок без нового края"
    elif bez_kraya <= 2:
        sost = "рывок, сила слабеет" if oslab else "рывок, сила растёт"
    elif otdal < 0.38:
        sost = "откат мелкий"
    elif otdal <= 0.62:
        sost = "откат средний"
    else:
        sost = "откат глубокий"
    POSLEDNEE["сост"] = sost

    nab = []
    if roditel_est:
        razmah_roditelskogo = K[T0] - N[S0]
        otdal_roditelskogo = (max(0.0, (K[T0] - cl) / razmah_roditelskogo)
                              if razmah_roditelskogo > 0 else 0.0)
        nab.append(
            f"Опорный D1-отрезок сделки: начало {cena_v(N[S0]):.5f} "
            f"({_fmt(L, S0)}), текущий край {cena_v(K[T0]):.5f} "
            f"({_fmt(L, T0)}); возврат от края составил "
            f"{otdal_roditelskogo * 100:.0f}% размаха этого отрезка. "
            + ("Начало этого опорного отрезка пройдено."
               if za_nachalom_roditelskogo else
               "Начало этого опорного отрезка НЕ пройдено.")
        )
    else:
        nab.append(
            "Опорный D1-отрезок не удалось надёжно установить; локальные плечи "
            "после начала сделки нельзя считать границей всего D1-хода."
        )
    nab.append("Этот D1-отрезок — рабочая опора расчёта сделки, не родительский сегмент MN1→D1; "
               "иерархия месячных и дневных участков приведена во вложенной карте.")

    vnutrennie = []
    for lg in legs:
        i0, i1 = lg["nach"], lg["kray"]
        p0 = L.lo[i0] if vverh else L.hi[i0]
        p1 = L.hi[i1] if vverh else L.lo[i1]
        vnutrennie.append(
            f"{_fmt(L, i0)} {p0:.5f} → {_fmt(L, i1)} {p1:.5f}"
        )
    if vnutrennie:
        nab.append(
            "Локальные попутные плечи после входа (внутренний счёт, "
            "не отдельные родительские отрезки): " + "; ".join(vnutrennie) + "."
        )

    # Последние подтверждённые фрактальные точки до входа дают Ильве
    # предысторию рабочего D1-движения. Это не начало хода и не разметка волн.
    okno = max(2, S - 140)
    tochki_do = ([(i, "вершина", L.hi[i]) for i in VF0 if okno <= i < S]
                 + [(i, "впадина", L.lo[i]) for i in NF0 if okno <= i < S])
    tochki_do.sort(key=lambda x: x[0])
    if tochki_do:
        poslednie = tochki_do[-8:]
        stroka_do = "; ".join(
            f"{vid} {cena:.5f} ({_fmt(L, i)})" for i, vid, cena in poslednie)
        nab.append(f"Контекст {tf0} до входа — последние подтверждённые фракталы "
                   f"за окно до 140 баров: {stroka_do}. Это только точки графика, "
                   "не номера волн и не доказательство начала/конца хода.")
    else:
        nab.append(f"Контекст {tf0} до входа: в окне до 140 баров нет подтверждённых "
                   "фрактальных точек; положение внутри полного хода не установлено.")
    if sost.startswith("рывок") or sost == "отрезок без нового края":
        nab.append(f"сейчас попутный отрезок по сделке — край {cena_v(K[posl['kray']]):.5f} "
                   f"({_fmt(L, posl['kray'])})"
                   + ("; это новый край сделки" if posl["obnovil"] else
                      "; край сделки он не обновил") + ".")
    else:
        nab.append(f"сейчас откат — {bez_kraya} бар(ов) от вершины последнего попутного "
                   f"отрезка {cena_v(K[posl['kray']]):.5f} ({_fmt(L, posl['kray'])}); цена "
                   f"отдала {otdal * 100:.0f}% этого отрезка"
                   + ("; AO уходил за ноль" if ao_za_nol else "; AO за ноль не уходил") + ".")
        if za_nachalom_vnutrennego:
            nab.append(
                f"цена прошла начало последнего ВНУТРЕННЕГО плеча "
                f"{cena_v(N[posl['nach']]):.5f} больше чем на спред и тик; "
                "это не означает, что пройдено начало старшего MN1-хода."
            )
        else:
            nab.append(
                f"начало последнего внутреннего плеча — "
                f"{cena_v(N[posl['nach']]):.5f}; до него цена не доходила "
                "(с учётом спреда)."
            )
    if pred is not None:
        nab.append("против предыдущего попутного отрезка: размах "
                   + ("больше" if posl["razmah"] >= pred["razmah"] else "меньше")
                   + ", сила по AO "
                   + ("—" if posl["sila"] is None or pred["sila"] is None else
                      ("сильнее" if posl["sila"] >= pred["sila"] else "слабее")) + ".")
    nab.append(f"попутных отрезков с входа: {len(legs)}, из них обновили край сделки: "
               f"{sum(1 for x in legs if x['obnovil'])}.")
    nab = [nab[0]] + [s[:1].upper() + s[1:] for s in nab[1:]]
    Ls = [zag, "Наблюдение: " + " ".join(nab),
          f"Толкование (из книги, может не совпасть): {_TOLKOVANIE_FR[sost]}", resh]
    # VLOZHENNAYA_KARTA_MN1_D1_V1: отдельное наблюдение для D03.
    # Карта не участвует в выборе HOLD/CLOSE/доливки и не меняет вход.
    try:
        import struktura_vlozhennaya as _sv
        _karta = _sv.blok(symbol, poz, tf0)
        if _karta:
            Ls.insert(-1, _karta)
    except Exception as _e_sv:
        print(f"[ВЛОЖЕННАЯ КАРТА] блок не добавился ({_e_sv})")

    kratko = f"{tf0} {sost} · отрезков {len(legs)}" + (
        f" · отдала {otdal * 100:.0f}%" if sost.startswith(("откат", "цена")) else "")
    for s in Ls:
        print(f"[ФРАКТАЛЫ ПОДРОБНО] {s}")
    return "\n".join(Ls), kratko


def blok_sdelki(symbol, poz, rabochiy="D1", zakrep=None) -> tuple:   # noqa: F811
    return blok_sdelki_fraktaly(symbol, poz, rabochiy)


def albom(ceh, slot, nomer=None) -> str:   # noqa: F811
    return ("Альбом волн с номерами снят: номера — толкование. Город показывает "
            "наблюдения по фракталам: рывки, откаты, размах, силу по AO.")


# VOLNY_FRAKTALY_V1 - marker


# ══ VEDENIE_MASSHTAB_V1 — в сделке: строка «ведение по масштабу импульса» ══
# Только на местах с пометкой «ведение_масштаб: да» (D03). Считает город,
# решает житель. Канон гл. 7: AO меряет волну в 100–140 баров.
_blok_do_masshtaba = blok_sdelki_fraktaly


def blok_sdelki_fraktaly(symbol, poz, rabochiy="D1"):   # noqa: F811
    r = _blok_do_masshtaba(symbol, poz, rabochiy)
    try:
        import vedenie_masshtab as _vm
        s = _vm.stroka(symbol, poz)
        if s:
            if isinstance(r, tuple):
                tekst, kratko = r
                tekst = (str(tekst).rstrip() + "\n" + s) if tekst else s
                return tekst, kratko
            return (str(r).rstrip() + "\n" + s) if r else s
    except Exception as e:
        print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] не посчиталось ({e})")
    return r


# VEDENIE_MASSHTAB_V1 - marker
