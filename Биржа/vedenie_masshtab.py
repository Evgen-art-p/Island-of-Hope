# -*- coding: utf-8 -*-
# VEDENIE_MASSHTAB_V1
"""
Ведение по масштабу импульса — второй уровень, канон главы 7 (Вильямс).

    AO (5/34) меряет волну того порядка, которая занимает 100–140 баров.
    При входе город фиксирует, раз и на всю сделку:
      · начало волны сделки — по вложенной карте на входе: участок D1 внутри
        MN1; если он идёт в сторону сделки — его начало, если против — его край;
      · масштаб — этаж, где импульс, продолжение которого она торгует (прошлый
        участок D1 в сторону сделки), занимает около 120 баров.
    Каждый день — только по закрытым свечам — на этом масштабе:
      · «3 на 5»: после пика третьей AO возвращался к нулю, новый край с более
        слабым AO подтверждён фракталом — конец пятой волны сделки → выход;
      · «5 в 3»: дивер без возврата AO к нулю — конец третьей → держать;
      · дивера нет / край не подтверждён → держать.
    Проверено ценой (07.11, 425 сделок D02/D03 и других мест): лучше выходов
    жителей и любого одного фиксированного этажа; стопов на треть меньше.
"""
from __future__ import annotations

import json
from bisect import bisect_left
from datetime import datetime, timedelta
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
_REPO = _BIRZHA.parent
_ETAZHI = (("W1", 0.2), ("D1", 1.0), ("H4", 6.0), ("H1", 24.0))
_CEL = 120
POMETKA = "ведение_масштаб"
_KESH = {"t": -1e9, "m": set()}


def _d16(s) -> str:
    s = str(s or "").strip().replace("-", ".").replace("T", " ")
    return s[:16] if len(s) > 10 else (s[:10] + " 00:00")


def _ryad(symbol, tf, do: str):
    from feed_source import bars as _bars
    from williams_core import compute_ao_series
    n = {"W1": 1500, "D1": 4000, "H4": 6000, "H1": 6000}.get(tf, 4000)
    b, _pt = _bars(symbol, tf, n)
    S = []
    for x in (b or []):
        d = _d16(x.get("date"))
        if d and d < do:
            S.append((d, float(x["high"]), float(x["low"]), float(x.get("close", x["low"]))))
    A = list(compute_ao_series([x[1] for x in S], [x[2] for x in S])) if S else []
    return S, A


def _mesta() -> set:
    import time
    if time.monotonic() - _KESH["t"] < 30:
        return _KESH["m"]
    m = set()
    try:
        import mesto_urovnya as _mu
        for man in sorted((_REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха").glob("*/manifest.json")):
            try:
                d = json.loads(man.read_text(encoding="utf-8"))
            except Exception:
                continue
            for z in d.get("слоты") or []:
                if str(z.get(POMETKA) or "").strip().lower() in ("да", "true", "1"):
                    n = _mu.nomer_mesta(z.get("слот"), man.parent.name)
                    if n is not None:
                        m.add(int(n))
    except Exception as e:
        print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] места не прочлись ({e})")
    _KESH.update(t=time.monotonic(), m=m)
    return m


def _imena() -> set:
    """Имена мест с пометкой «ведение_масштаб» (D03…)."""
    out = set()
    try:
        for man in sorted((_REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха").glob("*/manifest.json")):
            try:
                d = json.loads(man.read_text(encoding="utf-8"))
            except Exception:
                continue
            for z in d.get("слоты") or []:
                if str(z.get(POMETKA) or "").strip().lower() in ("да", "true", "1"):
                    out.add(str(z.get("слот") or "").strip().upper())
    except Exception:
        pass
    return out


def _etazh(dney) -> str:
    return min(_ETAZHI, key=lambda e: abs(max(1, dney) * e[1] - _CEL))[0]


def zafiksirovat(symbol, poz) -> dict:
    """Начало волны сделки и масштаб — по карте на входе (только бары до входа)."""
    vverh = str(poz.get("direction") or "").upper() == "LONG"
    entry = datetime.strptime(_d16(poz.get("opened_at")), "%Y.%m.%d %H:%M")
    rab = str(poz.get("timeframe") or "D1").upper()
    try:
        import hod_mesyaca as hm
        import struktura_vlozhennaya as sv
        slot = str(poz.get("trader") or "").upper()
        ya = hm._yashchik_chitat(slot, symbol)
        ist = sv._istoriya_na_vhod(ya, entry)
        trend = str((ist or {}).get("ход") or "")
        levels = hm._urovni(symbol, trend, str(ist.get("с") or ""), entry, rab) if ist else None
        if not levels:
            raise ValueError("на дату входа нет истории старшего хода")
        snap = sv._snapshot(symbol, "MN1", levels.get("начало_дата"), trend == "вверх", entry,
                            {}, rab, levels.get("начало_цена"))
        am = sv._at(snap["segments"], entry, allow_prior=True)
        dn = sv._nested_segments(symbol, snap["L"], am, "MN1", "D1", when=entry, cache={},
                                 label_trend=trend)
        ds = (dn or {}).get("segments") or []
        if not ds:
            raise ValueError("карта не дала участков D1")
        ad = sv._at(ds, entry, allow_prior=True)
        i = ds.index(ad)
        po = (ad["to"] > ad["from"]) == vverh
        nach = ad["start"] if po else ad["finish"]
        prev = [s for s in ds[:i + (1 if po else 0)] if (s["to"] > s["from"]) == vverh]
        dl = max([int(s.get("bars") or 1) for s in prev[-2:]] or [1])
        return {"начало": nach.strftime("%Y.%m.%d"), "импульс_дней": dl, "этаж": _etazh(dl),
                "откуда": "по карте при входе"}
    except Exception as e:
        # запас: край последних 10 дней до входа; импульс — от прошлого края до него
        do = entry.strftime("%Y.%m.%d %H:%M")
        D, _ = _ryad(symbol, "D1", do)
        if len(D) < 20:
            return {"ошибка": f"мало свечей ({e})"}
        rng = range(len(D) - 10, len(D))
        k = min(rng, key=lambda x: D[x][2]) if vverh else max(rng, key=lambda x: D[x][1])
        return {"начало": D[k][0][:10], "импульс_дней": 5, "этаж": _etazh(5),
                "откуда": f"карта не дала ({e}); край 10 дней"}


def signal(symbol, nachalo: str, bar: str, vverh: bool, tf: str) -> str:
    """На конец бара города (закрытые свечи): «3 на 5» / «5 в 3» / «дивера нет» /
    «край не подтверждён» / «мало данных»."""
    do = (datetime.strptime(str(bar)[:10].replace("-", "."), "%Y.%m.%d")
          + timedelta(days=1)).strftime("%Y.%m.%d 00:00")
    T, A = _ryad(symbol, tf, do)
    t0 = nachalo[:10] + " 00:00"
    if tf == "W1":
        t0 = (datetime.strptime(nachalo[:10], "%Y.%m.%d") - timedelta(days=7)).strftime("%Y.%m.%d 00:00")
    tt = [x[0] for x in T]
    a0, a1 = bisect_left(tt, t0), len(T)
    seg = [x for x in range(a0, a1) if A[x] is not None]
    if len(seg) < 8:
        return "мало данных"
    H = lambda x: T[x][1]
    Lo = lambda x: T[x][2]
    e = max(seg, key=H) if vverh else min(seg, key=Lo)
    if e + 2 >= a1:
        return "край не подтверждён"
    k = 1 if vverh else 2
    if not all(((T[e][k] > T[e + d][k]) if vverh else (T[e][k] < T[e + d][k]))
               for d in (-2, -1, 1, 2) if a0 <= e + d < a1):
        return "край не подтверждён"
    pre = [x for x in seg if x < e - 2]
    if not pre:
        return "дивера нет"
    p = max(pre, key=lambda x: A[x]) if vverh else min(pre, key=lambda x: A[x])
    if (vverh and A[p] <= 0) or ((not vverh) and A[p] >= 0):
        return "дивера нет"
    ae = max(A[max(a0, e - 2):e + 1]) if vverh else min(A[max(a0, e - 2):e + 1])
    if (vverh and ae >= A[p]) or ((not vverh) and ae <= A[p]):
        return "дивера нет"
    mid = A[p:e + 1]
    return "3 на 5" if (any(v <= 0 for v in mid) if vverh else any(v >= 0 for v in mid)) else "5 в 3"


def stroka(symbol, poz) -> str:
    """Строка жителю в сделке (пусто — место без пометки)."""
    # VEDENIE_MASSHTAB_V2: мозг даёт позицию без номера счёта — узнаём место и по имени
    try:
        _tr = str((poz or {}).get("trader") or "").strip().upper()
        if int((poz or {}).get("magic") or 0) not in _mesta() and _tr not in _imena():
            return ""
    except Exception:
        return ""
    try:
        from hooks import load_trading_state as _lts
        for q in (_lts() or {}).get("positions") or []:
            if (str(q.get("status") or "").upper() == "OPEN" and not q.get("нога")
                    and not q.get("тень")
                    and abs(float(q.get("entry") or 0) - float(poz.get("entry") or 0)) < 1e-6
                    and (str(q.get("trader") or "").upper() == _tr
                         or q.get("magic") == poz.get("magic"))):
                poz = dict(q, **{k: v for k, v in poz.items() if v is not None})
                for k in ("magic", "opened_at", "timeframe", "trader", "direction"):
                    if q.get(k) is not None:
                        poz[k] = q.get(k)
                break
    except Exception:
        pass
    # VEDENIE_MASSHTAB_V4: откат — коррекция, выход по разворотнику; масштаб — только импульс
    try:
        import vedenie_sdelki as _vs4
        _scen = str(_vs4._scenariy(str(poz.get("trader") or ""), symbol,
                                   "LONG" if str(poz.get("direction") or "").upper() == "LONG"
                                   else "SHORT") or "")
    except Exception:
        _scen = ""
    if _scen == "в откат":
        print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] {poz.get('trader')} {poz.get('direction')} {poz.get('entry')}: "
              f"откат — выход по разворотнику, масштаб не считаю")
        return ("ВЕДЕНИЕ ПО МЕСТУ: сделка — ОТКАТ (коррекция против старшего хода). Выход — "
                "встречный разворотный бар с приседающим на рабочем этаже, когда ты в заметном "
                "плюсе. Масштаб импульса для отката не считаю: в коррекции пятой волны нет.")
    try:
        from hooks import load_trading_state, save_trading_state
        t = load_trading_state() or {}
        kl = f"{poz.get('magic')}|{poz.get('entry')}|{poz.get('opened_at')}"
        zap = t.get("ведение_масштаб") or {}
        fx = zap.get(kl)
        if not fx:
            fx = zafiksirovat(symbol, poz)
            zap = {k: v for k, v in zap.items()
                   if any(f"{q.get('magic')}|{q.get('entry')}|{q.get('opened_at')}" == k
                          for q in t.get("positions") or [])}
            zap[kl] = fx
            t["ведение_масштаб"] = zap
            save_trading_state(t)
        if fx.get("ошибка"):
            return f"ВЕДЕНИЕ ПО МАСШТАБУ ИМПУЛЬСА: посчитать не вышло ({fx['ошибка']}) — держи по стопу."
        bar = str((t.get("рынок") or {}).get("бар") or t.get("бар") or "")
        vverh = str(poz.get("direction") or "").upper() == "LONG"
        s = signal(symbol, fx["начало"], bar, vverh, fx["этаж"])
    except Exception as e:
        print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] ⚠️  {poz.get('trader')} {poz.get('entry')}: не посчиталось ({e})")
        return f"ВЕДЕНИЕ ПО МАСШТАБУ ИМПУЛЬСА: посчитать не вышло ({e}) — держи по стопу."
    shapka = (f"ВЕДЕНИЕ ПО МАСШТАБУ ИМПУЛЬСА (канон, гл. 7): волна твоей сделки — с {fx['начало']}; "
              f"импульс, продолжение которого ты торгуешь, — {fx['импульс_дней']} дн. D1 → веду на "
              f"{fx['этаж']} (масштаб зафиксирован при входе, {fx['откуда']}). Сейчас на {fx['этаж']}: ")
    print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] {poz.get('trader')} {poz.get('direction')} {poz.get('entry')}: "
          f"{fx['этаж']} с {fx['начало']} — {s}")
    if s == "3 на 5":
        return shapka + ("дивер «3 на 5» — после пика третьей AO возвращался к нулю, новый край "
                         "с более слабым AO подтверждён фракталом: пятая твоей волны кончилась. "
                         "По канону — ВЫХОД (CLOSE).")
    if s == "5 в 3":
        return shapka + ("дивер «5 в 3» — AO к нулю не возвращался: конец третьей, впереди "
                         "четвёртая и пятая. По канону — ДЕРЖАТЬ, это не выход.")
    if s == "край не подтверждён":
        return shapka + "новый край ещё не подтверждён фракталом. ДЕРЖАТЬ."
    if s == "мало данных":
        return shapka + "свечей пока мало. ДЕРЖАТЬ по стопу."
    return shapka + "дивера нет — волна в силе. ДЕРЖАТЬ."


# VEDENIE_MASSHTAB_V1 - marker
# VEDENIE_MASSHTAB_V2 - marker
# VEDENIE_MASSHTAB_V4 - marker


# ══ VEDENIE_MASSHTAB_V5 — «ход сломан» на этом месте — наблюдение, не выход ══
_stroka_do_v5 = stroka


def stroka(symbol, poz) -> str:   # noqa: F811
    s = _stroka_do_v5(symbol, poz)
    if not s:
        return s
    try:
        import volny_kanon as _vk5
        if str((getattr(_vk5, "POSLEDNEE", {}) or {}).get("сост") or "") == "ход сломан":
            print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] {poz.get('trader')} {poz.get('direction')} "
                  f"{poz.get('entry')}: «ход сломан» — наблюдение, не выход")
            s += (" «Ход сломан» в блоке волн выше и голос прошлых случаев — это наблюдение, "
                  "не выход. На этом месте выход только по месту (откат — встречный "
                  "разворотник с приседающим в заметном плюсе; продолжение и перелом — по "
                  "масштабу импульса) или стоп.")
    except Exception:
        pass
    return s


# VEDENIE_MASSHTAB_V5 - marker


# ══ VEDENIE_SHAG_STARSHE_V1 — масштаб выхода на шаг старше этажа импульса ══
# Только места с пометкой «ведение_шаг_старше: да» (D03). Слово Шефа 10.11.
# Замер: на входах D03 «3 на 5» на D1 +20.4R против +1.5R на H4.
_STARSHE = {"H1": "H4", "H4": "D1", "D1": "W1", "W1": "W1"}
_SHAG_POMETKA = "ведение_шаг_старше"


def _shag_mesta():
    imena, nomera = set(), set()
    try:
        import mesto_urovnya as _mu_s
    except Exception:
        _mu_s = None
    try:
        for man in sorted((_REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха").glob("*/manifest.json")):
            try:
                d = json.loads(man.read_text(encoding="utf-8"))
            except Exception:
                continue
            for z in d.get("слоты") or []:
                if str(z.get(_SHAG_POMETKA) or "").strip().lower() in ("да", "true", "1"):
                    imena.add(str(z.get("слот") or "").strip().upper())
                    if _mu_s is not None:
                        try:
                            n = _mu_s.nomer_mesta(z.get("слот"), man.parent.name)
                            if n is not None:
                                nomera.add(int(n))
                        except Exception:
                            pass
    except Exception:
        pass
    return imena, nomera


_zafiksirovat_do_shaga = zafiksirovat


def zafiksirovat(symbol, poz) -> dict:   # noqa: F811
    fx = _zafiksirovat_do_shaga(symbol, poz)
    try:
        if not fx or fx.get("ошибка"):
            return fx
        imena, nomera = _shag_mesta()
        tr = str((poz or {}).get("trader") or "").strip().upper()
        try:
            mg = int((poz or {}).get("magic") or 0)
        except Exception:
            mg = 0
        if tr not in imena and mg not in nomera:
            return fx
        e0 = str(fx.get("этаж") or "")
        e1 = _STARSHE.get(e0, e0)
        if e1 != e0:
            fx = dict(fx, этаж=e1,
                      откуда=f"{fx.get('откуда')}; на шаг старше этажа импульса ({e0} → {e1})")
            print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] {tr} {poz.get('direction')} {poz.get('entry')}: "
                  f"масштаб на шаг старше — {e0} → {e1}")
    except Exception as _e_s:
        print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] шаг старше не сработал ({_e_s}) — масштаб как был")
    return fx

# VEDENIE_SHAG_STARSHE_V1 - marker


# ══ POTOLOK_RABOCHIY_V1 — масштаб выхода не старше рабочего, если рабочий H4 и младше ══
# Слово Шефа 10.11. Замеры на H4: «3 на 5» на рабочем +46.9R / +69.4R, на шаг
# старше (D1) −34.3R / +9.1R. Для рабочей дневки шаг на W1 не трогаем.
_LESTNICA_P = ["MN1", "W1", "D1", "H12", "H8", "H4", "H1", "M30", "M15"]


_zafiksirovat_do_potolka = zafiksirovat


def zafiksirovat(symbol, poz) -> dict:   # noqa: F811
    fx = _zafiksirovat_do_potolka(symbol, poz)
    try:
        if not fx or fx.get("ошибка"):
            return fx
        rab = str((poz or {}).get("timeframe") or "D1").upper()
        e = str(fx.get("этаж") or "").upper()
        if rab not in _LESTNICA_P or e not in _LESTNICA_P:
            return fx
        if _LESTNICA_P.index(rab) < _LESTNICA_P.index("H4"):
            return fx                      # рабочий старше H4 (D1…) — как было
        if _LESTNICA_P.index(e) < _LESTNICA_P.index(rab):
            fx = dict(fx, этаж=rab,
                      откуда=f"{fx.get('откуда')}; не старше рабочего ({e} → {rab})")
            print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] {poz.get('trader')} {poz.get('direction')} "
                  f"{poz.get('entry')}: потолок — рабочий этаж, {e} → {rab}")
    except Exception as _e_p:
        print(f"[ВЕДЕНИЕ ПО МАСШТАБУ] потолок не сработал ({_e_p}) — масштаб как был")
    return fx

# POTOLOK_RABOCHIY_V1 - marker


# ══ SNIMOK_I_FAKTY_V1 — строка масштаба с фактами; бары строго до конца бара города ══
# Слово Шефа 10.11: город показывает факты (экстремумы, AO, даты, этаж,
# подтверждение), вывод — помечен как вывод, не приказ.
_RAB_F = {"tf": None}
_FAKTY_F = {"последние": None}
_MIN_TF_F = {"M15": 15, "M30": 30, "H1": 60, "H4": 240, "H8": 480, "H12": 720, "D1": 1440}


def _do_bara_f(bar: str) -> str:
    """Конец бара города: для внутридневного рабочего этажа — бар + длина бара."""
    s = str(bar or "").strip().replace("-", ".")
    rab = str(_RAB_F.get("tf") or "").upper()
    try:
        if len(s) >= 16 and rab in _MIN_TF_F and _MIN_TF_F[rab] < 1440:
            t = datetime.strptime(s[:16], "%Y.%m.%d %H:%M") + timedelta(minutes=_MIN_TF_F[rab])
            return t.strftime("%Y.%m.%d %H:%M")
    except Exception:
        pass
    return (datetime.strptime(s[:10], "%Y.%m.%d") + timedelta(days=1)).strftime("%Y.%m.%d 00:00")


def _ch_f(v) -> str:
    return f"{v:+.5f}" if abs(v) < 1 else f"{v:+.2f}"


def signal(symbol, nachalo: str, bar: str, vverh: bool, tf: str) -> str:   # noqa: F811
    """Тот же счёт, что был, но с фактами в _FAKTY_F и барами до конца бара города."""
    F = {"этаж": tf, "с": str(nachalo)[:10]}
    _FAKTY_F["последние"] = F
    do = _do_bara_f(bar)
    F["бары_до"] = do
    T, A = _ryad(symbol, tf, do)
    t0 = nachalo[:10] + " 00:00"
    if tf == "W1":
        t0 = (datetime.strptime(nachalo[:10], "%Y.%m.%d") - timedelta(days=7)).strftime("%Y.%m.%d 00:00")
    tt = [x[0] for x in T]
    a0, a1 = bisect_left(tt, t0), len(T)
    seg = [x for x in range(a0, a1) if A[x] is not None]
    F["баров"] = len(seg)
    if len(seg) < 8:
        F["вывод"] = "мало данных"
        return "мало данных"
    k = 1 if vverh else 2
    e = max(seg, key=lambda x: T[x][1]) if vverh else min(seg, key=lambda x: T[x][2])
    F["край"] = (T[e][k], T[e][0])
    pod = (e + 2 < a1) and all(((T[e][k] > T[e + d][k]) if vverh else (T[e][k] < T[e + d][k]))
                               for d in (-2, -1, 1, 2) if a0 <= e + d < a1)
    F["край_подтверждён"] = pod
    pre = [x for x in seg if x < e - 2]
    p = (max(pre, key=lambda x: A[x]) if vverh else min(pre, key=lambda x: A[x])) if pre else None
    if p is not None:
        F["горб"] = (A[p], T[p][0], T[p][k])
    okno = list(range(max(a0, e - 2), e + 1))
    ie = (max(okno, key=lambda x: A[x] if A[x] is not None else -9) if vverh
          else min(okno, key=lambda x: A[x] if A[x] is not None else 9))
    if A[ie] is not None:
        F["ao_у_края"] = (A[ie], T[ie][0])
    if p is not None:
        nol = next((x for x in range(p, e + 1) if A[x] is not None
                    and ((A[x] <= 0) if vverh else (A[x] >= 0))), None)
        F["ноль"] = T[nol][0] if nol is not None else None
    if not pod:
        F["вывод"] = "край не подтверждён"
        return "край не подтверждён"
    if p is None or (vverh and A[p] <= 0) or ((not vverh) and A[p] >= 0):
        F["вывод"] = "дивера нет"
        return "дивера нет"
    ae = A[ie]
    if ae is None or (vverh and ae >= A[p]) or ((not vverh) and ae <= A[p]):
        F["вывод"] = "дивера нет"
        return "дивера нет"
    s = "3 на 5" if F.get("ноль") else "5 в 3"
    F["вывод"] = s
    return s


def fakty_slovami(F: dict, vverh: bool) -> str:
    if not F:
        return ""
    g, ya = ("горб", "вершина") if vverh else ("яма", "впадина")
    L = [f"этаж {F.get('этаж')}, участок с {F.get('с')} ({F.get('баров')} бар., бары до {F.get('бары_до')})"]
    if F.get("край"):
        c, d = F["край"]
        L.append(f"край хода — {ya} {c} ({d}), фракталом подтверждён: "
                 + ("да" if F.get("край_подтверждён") else "НЕТ"))
    if F.get("горб"):
        a, d, c = F["горб"]
        L.append(f"самый сильный {g} AO до края: {_ch_f(a)} ({d}, цена {c})")
    if F.get("ao_у_края"):
        a, d = F["ao_у_края"]
        L.append(f"AO у края: {_ch_f(a)} ({d})")
    if "ноль" in F:
        L.append("между ними AO через ноль: " + (f"да ({F['ноль']})" if F["ноль"] else "нет"))
    return "; ".join(L) + f". Вывод города: {F.get('вывод')}."


_stroka_do_faktov = stroka


def stroka(symbol, poz) -> str:   # noqa: F811
    tf = str((poz or {}).get("timeframe") or "").upper()
    if not tf:
        try:
            from hooks import load_trading_state as _lts_f
            for q in (_lts_f() or {}).get("positions") or []:
                if abs(float(q.get("entry") or 0) - float((poz or {}).get("entry") or 0)) < 1e-6:
                    tf = str(q.get("timeframe") or "").upper()
                    break
        except Exception:
            pass
    _RAB_F["tf"] = tf or None
    _FAKTY_F["последние"] = None
    s = _stroka_do_faktov(symbol, poz)
    F = _FAKTY_F.get("последние")
    if s and F and "ВЕДЕНИЕ ПО МАСШТАБУ ИМПУЛЬСА" in s:
        vverh = str((poz or {}).get("direction") or "").upper() == "LONG"
        s += (" ФАКТЫ ГОРОДА: " + fakty_slovami(F, vverh) + " Это вывод города, не приказ: "
              "если читаешь иначе — назови свои числа (край хода, сильный горб и AO у края, "
              "ноль между ними) в «почему».")
    return s

# SNIMOK_I_FAKTY_V1 - marker
