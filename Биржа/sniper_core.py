# Биржа/sniper_core.py
# ─────────────────────────────────────────────────────────────
# МАТЕМАТИКА СНАЙПЕРА — изолированное ядро
# Версия: 0.2 · ЭТАП 2 · разметка + голый прогон, судья — статистика
#
# ЗАКОН (тот же, что у williams_core.py): этот файл не знает про
# Грондхейм, агентов, cartridge. Принимает бары → возвращает уровни.
# Школа Вильямса/Котина осталась ровно как была — этот файл ей не
# сосед по логике, только по папке.
#
# ЧЕСТНО: числа ниже (0.25·ATR, 12-24 бара, 60% тени и т.д.) — не
# доказанный канон, а СТАРТОВЫЕ ГИПОТЕЗЫ из §8 SCALPER_CEH_MASTER.md.
# У Вильямса формулы сверены с исходниками MT5 — эталон есть. Здесь
# эталона нет. ПРАВКА 31.07 (Шеф): судья глазом отменён — он не
# трейдер и не может сказать, правильный уровень или нет ("один так
# разметит, другой по-другому"). Единственный судья — статистика
# голого прогона (Биржа/sniper_backtest.py): работает или нет,
# решают циферки PF/winrate/R, не чьё-то мнение о красоте картинки.
# ─────────────────────────────────────────────────────────────

from pathlib import Path
from typing import Optional
from datetime import datetime

# CSV-чтение то же самое, что у Вильямса — формат MT5-экспорта один
# на весь Город, дублировать парсер незачем.
from williams_core import read_mt5_csv  # noqa: F401 (реэкспорт для удобства CLI)


# ════════════════════════════════════════════════════════════
# ATR — общий термометр для всех уровней школы
# ════════════════════════════════════════════════════════════

def compute_atr(bars: list[dict], period: int = 14) -> list[Optional[float]]:
    """
    ATR — True Range, сглаженный простым SMA (не Wilder — проще для
    старта, при калибровке можно заменить, если Шеф увидит расхождение
    с привычным индикатором в терминале).

    TR[i] = max(high-low, |high-close[i-1]|, |low-close[i-1]|)
    ATR[i] = SMA(TR, period)[i]
    """
    n = len(bars)
    tr: list[float] = [0.0] * n
    for i in range(n):
        if i == 0:
            tr[i] = bars[i]["high"] - bars[i]["low"]
            continue
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        tr[i] = max(h - l, abs(h - pc), abs(l - pc))

    result: list[Optional[float]] = [None] * n
    for i in range(period - 1, n):
        result[i] = sum(tr[i - period + 1:i + 1]) / period
    return result


# ════════════════════════════════════════════════════════════
# ПИВОТ — база для ТИУ. Тот же 5-барный экстремум, что фракталы
# Вильямса (левые >=, правые >), но живёт здесь отдельно: школа
# Снайпера не должна зависеть от чужого ядра для своей математики.
# ════════════════════════════════════════════════════════════

def detect_pivots(bars: list[dict], lookback: int = 2) -> list[dict]:
    """5-барный экстремум (lookback=2 → окно 5, как канон §8 требует)."""
    n = len(bars)
    pivots = []
    for i in range(lookback, n - lookback):
        b = bars[i]
        if all(b["high"] >  bars[i + j]["high"] for j in range(1, lookback + 1)) and \
           all(b["high"] >= bars[i - j]["high"] for j in range(1, lookback + 1)):
            pivots.append({"bar_index": i, "type": "HIGH",
                           "price": round(b["high"], 6), "date": b["date"]})
        if all(b["low"] <  bars[i + j]["low"] for j in range(1, lookback + 1)) and \
           all(b["low"] <= bars[i - j]["low"] for j in range(1, lookback + 1)):
            pivots.append({"bar_index": i, "type": "LOW",
                           "price": round(b["low"], 6), "date": b["date"]})
    return pivots


# ════════════════════════════════════════════════════════════
# ТИУ — Тотальный Импульсный Уровень (H1)
# ════════════════════════════════════════════════════════════

def detect_tiu(bars_h1: list[dict], atr_h1: list[Optional[float]],
              zona_shirina_atr: float = 0.25,
              min_interval_barov: int = 8,
              proboy_atr: float = 0.5) -> list[dict]:
    """
    ТИУ: кластер из ≥2 пивотов в зоне шириной ≤ zona_shirina_atr·ATR(H1),
    интервал между касаниями ≥ min_interval_barov баров H1.
    Статус ПРОБИТ = закрытие H1 за зоной на ≥ proboy_atr·ATR.
    После пробоя — смена полярности (S↔R), уровень живёт дальше как
    противоположный (не умирает — Вильямс учит нас тому же на фрактале).

    Возвращает список уровней: {цена_центр, зона_лоу, зона_хай,
    касаний, первое_касание, последнее_касание, пробит, дата_пробоя,
    полярность_после_пробоя}.
    """
    pivots = detect_pivots(bars_h1, lookback=2)
    if not pivots:
        return []

    urovni = []
    ispolzovano = set()

    for i, p in enumerate(pivots):
        if i in ispolzovano:
            continue
        atr = atr_h1[p["bar_index"]] if p["bar_index"] < len(atr_h1) else None
        if atr is None:
            continue
        zona = zona_shirina_atr * atr

        klaster = [p]
        klaster_idx = {i}
        for j, q in enumerate(pivots[i + 1:], start=i + 1):
            if j in ispolzovano:
                continue
            if q["type"] != p["type"]:
                continue
            if abs(q["price"] - p["price"]) <= zona and \
               (q["bar_index"] - klaster[-1]["bar_index"]) >= min_interval_barov:
                klaster.append(q)
                klaster_idx.add(j)

        if len(klaster) < 2:
            continue
        ispolzovano |= klaster_idx

        tsentr = sum(k["price"] for k in klaster) / len(klaster)
        zona_lo, zona_hi = tsentr - zona / 2, tsentr + zona / 2

        # Ищем пробой — первое закрытие H1 за зоной на нужную глубину,
        # ПОСЛЕ последнего касания кластера.
        posle = klaster[-1]["bar_index"]
        probit = False
        data_proboya = None
        polyarnost_posle = p["type"]  # по умолчанию — не менялась
        for k in range(posle + 1, len(bars_h1)):
            atr_k = atr_h1[k]
            if atr_k is None:
                continue
            close = bars_h1[k]["close"]
            if p["type"] == "HIGH" and close > zona_hi + proboy_atr * atr_k:
                probit = True
                data_proboya = bars_h1[k]["date"]
                polyarnost_posle = "LOW"  # был сопротивлением, стал поддержкой
                break
            if p["type"] == "LOW" and close < zona_lo - proboy_atr * atr_k:
                probit = True
                data_proboya = bars_h1[k]["date"]
                polyarnost_posle = "HIGH"
                break

        urovni.append({
            "тип": "ТИУ",
            "полярность": p["type"],
            "цена_центр": round(tsentr, 6),
            "зона_лоу": round(zona_lo, 6),
            "зона_хай": round(zona_hi, 6),
            "касаний": len(klaster),
            "первое_касание": klaster[0]["date"],
            "последнее_касание": klaster[-1]["date"],
            "пробит": probit,
            "дата_пробоя": data_proboya,
            "полярность_после_пробоя": polyarnost_posle if probit else None,
        })

    return _slit_blizkie_tiu(urovni)


def _slit_blizkie_tiu(urovni: list[dict], mnozhitel_sliyaniya: float = 1.5) -> list[dict]:
    """
    Соседние кластеры ТИУ, чьи центры оказались ближе, чем
    mnozhitel_sliyaniya × (их собственная ширина зоны), — это на
    самом деле ОДИН уровень, просто разметка нашла его дважды через
    разные исходные пивоты. Оставляем более сильный (больше касаний),
    остальное отбрасываем — иначе на реальной истории десятки почти
    одинаковых линий заваливают график сплошной стеной."""
    if not urovni:
        return urovni
    urovni = sorted(urovni, key=lambda u: u["цена_центр"])
    slito: list[dict] = []
    for u in urovni:
        shirina = u["зона_хай"] - u["зона_лоу"]
        slilos = False
        for s in slito:
            shirina_s = s["зона_хай"] - s["зона_лоу"]
            porog = mnozhitel_sliyaniya * max(shirina, shirina_s)
            if abs(u["цена_центр"] - s["цена_центр"]) <= porog:
                if u["касаний"] > s["касаний"]:
                    slito[slito.index(s)] = u
                slilos = True
                break
        if not slilos:
            slito.append(u)
    return slito


# ════════════════════════════════════════════════════════════
# ИУ — Импульсный Уровень (M5)
# ════════════════════════════════════════════════════════════

def detect_iu(bars_m5: list[dict], atr_m5: list[Optional[float]],
             okno_min: int = 8, okno_max: int = 30,
             box_range_atr: float = 1.8, impuls_telo_atr: float = 1.0,
             zakreplenie_barov: int = 2) -> list[dict]:
    """
    ИУ: коробка = окно okno_min–okno_max баров, range ≤ box_range_atr·ATR(M5).
    Импульс = бар с телом ≥ impuls_telo_atr·ATR, закрытие за коробкой.
    Закрепление = zakreplenie_barov баров без возврата внутрь.
    Граница коробки, которую пробили — и есть уровень ИУ.
    """
    n = len(bars_m5)
    urovni = []
    i = 0
    while i < n - okno_max:
        atr = atr_m5[i + okno_min] if i + okno_min < len(atr_m5) else None
        if atr is None:
            i += 1
            continue

        for okno in range(okno_min, okno_max + 1):
            if i + okno >= n:
                break
            segment = bars_m5[i:i + okno]
            hi = max(b["high"] for b in segment)
            lo = min(b["low"] for b in segment)
            if (hi - lo) > box_range_atr * atr:
                continue  # эта ширина окна не коробка — шире гипотезы

            # ищем импульсный бар СРАЗУ после коробки
            k = i + okno
            if k >= n:
                continue
            bar = bars_m5[k]
            telo = abs(bar["close"] - bar["open"])
            atr_k = atr_m5[k] if k < len(atr_m5) else None
            if atr_k is None or telo < impuls_telo_atr * atr_k:
                continue

            if bar["close"] > hi:
                napravlenie, uroven = "HIGH", hi
            elif bar["close"] < lo:
                napravlenie, uroven = "LOW", lo
            else:
                continue

            # закрепление: N баров подряд без возврата внутрь коробки
            zakrep = True
            for m in range(k + 1, min(k + 1 + zakreplenie_barov, n)):
                if napravlenie == "HIGH" and bars_m5[m]["close"] < hi:
                    zakrep = False
                    break
                if napravlenie == "LOW" and bars_m5[m]["close"] > lo:
                    zakrep = False
                    break

            urovni.append({
                "тип": "ИУ",
                "полярность": napravlenie,
                "уровень": round(uroven, 6),
                "коробка_лоу": round(lo, 6),
                "коробка_хай": round(hi, 6),
                "окно_баров": okno,
                "импульсный_бар_индекс": k,
                "импульсный_бар_дата": bar["date"],
                "закреплён": zakrep,
            })
            i = k + zakreplenie_barov  # не ищем следующую коробку внутри этой же
            break
        else:
            i += 1

    return urovni


# ════════════════════════════════════════════════════════════
# ЗК — Зона Консолидации (ночной флэт)
# ════════════════════════════════════════════════════════════

def _chas_bara(bar: dict) -> Optional[int]:
    """Достаёт час из даты бара — терпимо к паре форматов MT5-экспорта."""
    date_str = bar.get("date", "")
    for fmt in ("%Y.%m.%d %H:%M", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt).hour
        except ValueError:
            continue
    # формат с временем вторым полем через пробел — попытка вручную
    parts = date_str.split(" ")
    if len(parts) >= 2 and ":" in parts[-1]:
        try:
            return int(parts[-1].split(":")[0])
        except ValueError:
            pass
    return None


def detect_zk(bars_h1: list[dict], atr_h1: list[Optional[float]],
             nachalo_chas: int = 0, konets_chas: int = 7,
             shirina_pipsov: Optional[float] = None,
             shirina_atr: float = 0.8, point: Optional[float] = None) -> list[dict]:
    """
    ЗК: ночная сессия (серверное время nachalo_chas–konets_chas включительно).
    Флэт валиден, если ширина ≤ shirina_pipsov (в пунктах, если задано и
    известен point) ИЛИ ≤ shirina_atr·ATR(H1) — выбираем по тому, что
    сработает при калибровке.

    Возвращает по одной ЗК на календарную дату, где нашлась ночная сессия.
    """
    nochi: dict = {}
    for i, b in enumerate(bars_h1):
        chas = _chas_bara(b)
        if chas is None:
            continue
        if nachalo_chas <= chas <= konets_chas:
            data_kalendarnaya = b["date"].split(" ")[0]
            nochi.setdefault(data_kalendarnaya, []).append((i, b))

    urovni = []
    for data, bary in nochi.items():
        idxs = [i for i, _ in bary]
        segment = [b for _, b in bary]
        hi = max(b["high"] for b in segment)
        lo = min(b["low"] for b in segment)
        shirina = hi - lo

        valid_atr = None
        atr_last = atr_h1[idxs[-1]] if idxs[-1] < len(atr_h1) else None
        if atr_last is not None:
            valid_atr = shirina <= shirina_atr * atr_last

        valid_pips = None
        if shirina_pipsov is not None and point:
            valid_pips = shirina <= shirina_pipsov * point

        validen = bool(valid_pips) if valid_pips is not None else bool(valid_atr)

        urovni.append({
            "тип": "ЗК",
            "дата": data,
            "флэт_лоу": round(lo, 6),
            "флэт_хай": round(hi, 6),
            "ширина": round(shirina, 6),
            "валиден_по_atr": valid_atr,
            "валиден_по_пунктам": valid_pips,
            "валиден": validen,
        })

    return urovni


# ════════════════════════════════════════════════════════════
# УРСТ — Уровень Резкой Смены Тенденции (V-разворот)
# ════════════════════════════════════════════════════════════

def detect_urst(bars_m5: list[dict], atr_m5: list[Optional[float]],
                ten_dolya: float = 0.68, telo_dolya: float = 0.22,
                zakhod_atr: float = 2.2, zakhod_barov: int = 6,
                vykhod_dolya: float = 0.6, vykhod_barov: int = 4) -> list[dict]:
    """
    УРСТ: экстремум-бар с тенью ≥ ten_dolya размаха бара, телом ≤ telo_dolya.
    Заход к экстремуму ≥ zakhod_atr·ATR за ≤ zakhod_barov баров.
    V-выход: возврат ≥ vykhod_dolya захода за ≤ vykhod_barov баров.
    """
    n = len(bars_m5)
    urovni = []

    for i in range(zakhod_barov, n - vykhod_barov):
        b = bars_m5[i]
        razmakh = b["high"] - b["low"]
        if razmakh <= 0:
            continue
        telo = abs(b["close"] - b["open"])
        ten_verkh = b["high"] - max(b["open"], b["close"])
        ten_niz = min(b["open"], b["close"]) - b["low"]

        for storona, ten in (("HIGH", ten_verkh), ("LOW", ten_niz)):
            if ten < ten_dolya * razmakh or telo > telo_dolya * razmakh:
                continue

            nachalo = i - zakhod_barov
            atr_i = atr_m5[i] if i < len(atr_m5) else None
            if atr_i is None:
                continue
            if storona == "HIGH":
                zakhod = b["high"] - min(x["low"] for x in bars_m5[nachalo:i + 1])
            else:
                zakhod = max(x["high"] for x in bars_m5[nachalo:i + 1]) - b["low"]
            if zakhod < zakhod_atr * atr_i:
                continue

            v_vyshel = False
            for k in range(i + 1, min(i + 1 + vykhod_barov, n)):
                if storona == "HIGH":
                    otkat = b["high"] - bars_m5[k]["low"]
                else:
                    otkat = bars_m5[k]["high"] - b["low"]
                if otkat >= vykhod_dolya * zakhod:
                    v_vyshel = True
                    break

            urovni.append({
                "тип": "УРСТ",
                "полярность": storona,
                "цена": round(b["high"] if storona == "HIGH" else b["low"], 6),
                "бар_индекс": i,
                "дата": b["date"],
                "тень_доля_размаха": round(ten / razmakh, 3),
                "v_подтверждён": v_vyshel,
            })

    return urovni


# ════════════════════════════════════════════════════════════
# БПЦ — Блок Пустых Цен (первоисточник, не §8-гипотеза)
# Резкая свеча (или почти без отката), 30-200+ пунктов в зависимости
# от пары — толпа не успела там накопиться. Правило источника: такой
# блок закроется минимум на 90% в течение 1-2 суток, если тренд не
# развернулся. Порог даём в ATR (безразмерно), а не в пунктах — как
# и весь остальной канон в этом файле, живёт на любом инструменте.
# ════════════════════════════════════════════════════════════

def detect_bpz(bars: list[dict], atr: list[Optional[float]],
              min_atr_mnozhitel: float = 3.0,
              min_telo_dolya_razmakha: float = 0.6) -> list[dict]:
    """Блок Пустых Цен: один бар (в первой версии — не группа), чьё
    тело ≥ min_atr_mnozhitel×ATR, почти без теней (тело ≥ 60% размаха
    бара — 'почти без откатов')."""
    n = len(bars)
    bpz = []
    for i in range(1, n):
        a = atr[i]
        if a is None:
            continue
        b = bars[i]
        dvizhenie = b["close"] - b["open"]
        razmakh = b["high"] - b["low"]
        if razmakh <= 0 or abs(dvizhenie) < min_atr_mnozhitel * a:
            continue
        if abs(dvizhenie) / razmakh < min_telo_dolya_razmakha:
            continue  # большие тени — не "чистый" БПЦ, толпа там уже была

        if dvizhenie > 0:
            bpz.append({"тип": "БПЦ", "направление": "UP", "бар_индекс": i,
                       "лоу": round(b["open"], 6), "хай": round(b["close"], 6),
                       "дата": b["date"]})
        else:
            bpz.append({"тип": "БПЦ", "направление": "DOWN", "бар_индекс": i,
                       "лоу": round(b["close"], 6), "хай": round(b["open"], 6),
                       "дата": b["date"]})
    return bpz


# ════════════════════════════════════════════════════════════
# СЕТАПЫ — классификация по §2 SCALPER_CEH_MASTER.md
# ════════════════════════════════════════════════════════════

def klassifitsirovat_setap(bary_posle_urovnya: list[dict], uroven: float,
                           napravlenie: str, vozvrat_barov: int = 3) -> str:
    """
    Три сетапа школы (классифицирует код, не трейдер):
      ПРОБОЙ       — цена закрылась за уровнем и не вернулась
      ЛОЖНЫЙ_ПРОБОЙ — вышла за уровень, вернулась ≤ vozvrat_barov баров
      РЕТЕСТ       — вернулась к уровню после уже случившегося пробоя

    Возвращает одну из строк: "ПРОБОЙ" / "ЛОЖНЫЙ_ПРОБОЙ" / "РЕТЕСТ" / "НЕТ".
    """
    if not bary_posle_urovnya:
        return "НЕТ"

    vyshla = False
    vernulas_do = None
    for idx, b in enumerate(bary_posle_urovnya):
        za_urovnem = (b["close"] > uroven) if napravlenie == "HIGH" else (b["close"] < uroven)
        if za_urovnem:
            vyshla = True
        elif vyshla and vernulas_do is None:
            vernulas_do = idx

    if not vyshla:
        return "НЕТ"
    if vernulas_do is not None and vernulas_do <= vozvrat_barov:
        return "ЛОЖНЫЙ_ПРОБОЙ"
    return "ПРОБОЙ"


# ════════════════════════════════════════════════════════════
# СБОРКА — все уровни разом (для разметки и проверки на глаз)
# ════════════════════════════════════════════════════════════

def build_sniper_map(bars_h1: list[dict], bars_m5: list[dict],
                     point: Optional[float] = None) -> dict:
    """
    Собирает всю карту уровней школы Снайпера. Ничего не решает про
    вход/выход — только разметка, для сверки глазом с настоящим графиком.
    """
    if len(bars_h1) < 40 or len(bars_m5) < 40:
        print(f"[SNIPER] ❌ Недостаточно баров: H1={len(bars_h1)} M5={len(bars_m5)}")
        return {}

    atr_h1 = compute_atr(bars_h1)
    atr_m5 = compute_atr(bars_m5)

    tiu = detect_tiu(bars_h1, atr_h1)
    iu = detect_iu(bars_m5, atr_m5)
    zk = detect_zk(bars_h1, atr_h1, point=point)
    urst = detect_urst(bars_m5, atr_m5)

    print(f"[SNIPER] ТИУ: {len(tiu)} · ИУ: {len(iu)} · "
          f"ЗК: {len(zk)} · УРСТ: {len(urst)}")

    return {"ТИУ": tiu, "ИУ": iu, "ЗК": zk, "УРСТ": urst}


# ════════════════════════════════════════════════════════════
# CLI — быстрая проверка на CSV (та же форма, что у williams_core.py)
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Использование: python sniper_core.py <h1.csv> <m5.csv> [POINT]")
        print("Пример: python sniper_core.py EURUSDH1.csv EURUSDM5.csv 0.00001")
        sys.exit(0)

    h1_path = sys.argv[1]
    m5_path = sys.argv[2]
    point_arg = float(sys.argv[3]) if len(sys.argv) > 3 else 0.00001

    bars_h1 = read_mt5_csv(h1_path)
    bars_m5 = read_mt5_csv(m5_path)

    if bars_h1 and bars_m5:
        karta = build_sniper_map(bars_h1, bars_m5, point=point_arg)
        if karta:
            print("\n=== JSON карта уровней (последние 5 каждого типа) ===")
            urezano = {k: v[-5:] for k, v in karta.items()}
            print(json.dumps(urezano, ensure_ascii=False, indent=2))

# SNIPER_BAZA_V1 — маркер идемпотентности
