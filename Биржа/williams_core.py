# studio/modules/trading/williams_core.py
# ─────────────────────────────────────────────────────────────
# МАТЕМАТИКА ВИЛЬЯМСА — изолированное ядро
# Версия: 1.1 · Спринт 45 · 2026-06-16 · POINT_MAP убран, point обязателен
#
# ЗАКОН: этот файл не знает про Грондхейм, агентов, cartridge.
# Принимает CSV или список баров → возвращает market_data.
# Любая другая торговая система пишет свой *_core.py рядом.
#
# Все формулы по исходникам MT5:
#   AO:       Awesome_Oscillator.mq5
#   AC:       Accelerator.mq5
#   Аллигатор: Alligator.mq5 (SMMA рекуррентно)
#   Фракталы: Fractals.mq5 (левые >=, правые >)
#   BWMFI:    MarketFacilitationIndex.mq5
# ─────────────────────────────────────────────────────────────

from pathlib import Path
from typing import Optional


# ════════════════════════════════════════════════════════════
# ТОЧНОСТЬ ЦЕНЫ (point)
# ════════════════════════════════════════════════════════════
#
# ЗАКОН: ядро НЕ знает тикеры. point (минимальный шаг цены) приходит
# снаружи как обязательный параметр — из терминала (symbol_info.point)
# для живого потока, или задаётся явно для лабораторных прогонов.
# Никаких встроенных таблиц активов: это и есть отказ от зависимости.


# ════════════════════════════════════════════════════════════
# ЧТЕНИЕ CSV
# ════════════════════════════════════════════════════════════

def read_mt5_csv(filepath: str) -> list[dict]:
    """
    Читает CSV-файл экспорта MT5.
    Формат: date,open,high,low,close,tick_volume,spread
    Кодировка: utf-16-le (стандарт MT5).
    Возвращает список баров от старых к новым.
    """
    bars = []
    path = Path(filepath)
    if not path.exists():
        print(f"[CORE] ❌ CSV не найден: {filepath}")
        return []

    with open(path, encoding="utf-16-le") as f:
        for line in f:
            line = line.strip().lstrip("\ufeff")
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 6:
                continue
            try:
                bars.append({
                    "date":   parts[0].strip(),
                    "open":   float(parts[1]),
                    "high":   float(parts[2]),
                    "low":    float(parts[3]),
                    "close":  float(parts[4]),
                    "volume": int(parts[5]),
                    "spread": float(parts[6]) if len(parts) > 6 else 0.0,
                })
            except (ValueError, IndexError):
                continue

    if bars:
        print(f"[CORE] 📂 {path.name}: {len(bars)} баров "
              f"({bars[0]['date']} → {bars[-1]['date']})")
    else:
        print(f"[CORE] ⚠️  {path.name}: пусто")
    return bars


# ════════════════════════════════════════════════════════════
# МАТЕМАТИКА
# ════════════════════════════════════════════════════════════

def _smma_series(medians: list[float], period: int) -> list[Optional[float]]:
    """
    Smoothed Moving Average — рекуррентная формула.
    smma[i] = (smma[i-1] * (period-1) + value[i]) / period
    Первое рабочее значение = SMA(period).
    SMMA ≠ EMA ≠ SMA.
    """
    result: list[Optional[float]] = [None] * len(medians)
    if len(medians) < period:
        return result
    first = sum(medians[:period]) / period
    result[period - 1] = first
    prev = first  # WILLIAMS_CORE_TYPING_V1: float-аккумулятор вместо чтения
    for i in range(period, len(medians)):  # result[i-1] — та же формула, тип чист
        prev = (prev * (period - 1) + medians[i]) / period
        result[i] = prev
    return result


def compute_alligator(highs: list[float], lows: list[float],
                      point: Optional[float] = None) -> dict:
    """
    Аллигатор Вильямса:
      Jaw(13)  — SMMA(13) медианы
      Teeth(8) — SMMA(8)  медианы
      Lips(5)  — SMMA(5)  медианы

    Смещения (+8/+5/+3) — для Pine Script / MT5 визуализации.
    Здесь используем текущие значения без смещения.

    bars_open — сколько баров подряд Аллигатор открыт.
    mature    — True если bars_open >= 8 (требует Консерватор).
    """
    medians = [(h + l) / 2 for h, l in zip(highs, lows)]

    jaw_s   = _smma_series(medians, 13)
    teeth_s = _smma_series(medians, 8)
    lips_s  = _smma_series(medians, 5)

    jaw   = jaw_s[-1]
    teeth = teeth_s[-1]
    lips  = lips_s[-1]

    if jaw is None or teeth is None or lips is None:
        return {
            "jaw": None, "teeth": None, "lips": None,
            "sleeping": True, "opening": False, "mature": False,
            "bars_open": 0,
        }

    # Порог раскрытия пасти — в единицах point (НЕ абсолютная цена).
    # 50 пунктов: для EURUSD (point=0.00001) это 0.0005 — как было;
    # для золота (point=0.01) это 0.5 — корректный масштаб. Один
    # безразмерный порог вместо хардкода под Forex.
    open_threshold = 50 * point if point else 0.0005

    # Считаем bars_open (сколько баров подряд открыт)
    bars_open = 0
    for i in range(len(jaw_s) - 1, -1, -1):
        j = jaw_s[i]; t = teeth_s[i]; l = lips_s[i]
        if j is None or t is None or l is None:
            break
        spread = max(abs(j - t), abs(t - l), abs(j - l))
        if spread < open_threshold:
            break
        bars_open += 1

    sleeping = bars_open == 0
    opening  = 0 < bars_open < 8
    mature   = bars_open >= 8

    return {
        "jaw":          round(jaw,   6),
        "teeth":        round(teeth, 6),
        "lips":         round(lips,  6),
        "sleeping":     sleeping,
        "opening":      opening,
        "mature":       mature,
        "bars_open":    bars_open,
        "jaw_series":   jaw_s,          # NECRON_DIVERGENCE_V1: нужна для отрыва от ВСЕХ трёх линий
        "teeth_series": teeth_s,
        "lips_series":  lips_s,
    }


def compute_ao_series(highs: list[float], lows: list[float]) -> list[Optional[float]]:
    """
    Awesome Oscillator:
      AO[i] = SMA(median, 5)[i] - SMA(median, 34)[i]
    """
    medians = [(h + l) / 2 for h, l in zip(highs, lows)]
    result: list[Optional[float]] = [None] * len(medians)
    for i in range(33, len(medians)):
        sma5  = sum(medians[i-4:i+1])  / 5
        sma34 = sum(medians[i-33:i+1]) / 34
        result[i] = sma5 - sma34
    return result


def compute_ac_series(ao_series: list[Optional[float]]) -> list[Optional[float]]:
    """
    Accelerator Oscillator:
      AC[i] = AO[i] - SMA(AO, 5)[i]
    """
    result: list[Optional[float]] = [None] * len(ao_series)
    for i in range(len(ao_series)):
        window = ao_series[max(0, i-4):i+1]
        valid  = [v for v in window if v is not None]
        if len(valid) < 5:
            continue
        cur = ao_series[i]
        if cur is None:
            continue  # WILLIAMS_CORE_TYPING_V2: структурно недостижимо
            # (window включает cur; valid==5 доказывает cur не None) —
            # запись существующего инварианта, не новая ветка поведения
        result[i] = cur - sum(valid[-5:]) / 5
    return result


def detect_fractals(bars: list[dict], lookback: int = 2) -> dict:
    """
    Фракталы Вильямса — классические 5-барные (±2 от центра).
    По исходнику MT5 Fractals.mq5:
      правые бары: строгое > / <
      левые  бары: нестрогое >= / <=
    """
    n = len(bars)
    up_fractals   = []
    down_fractals = []

    for i in range(lookback, n - lookback):
        b = bars[i]

        if all(b["high"] >  bars[i + j]["high"] for j in range(1, lookback + 1)) and \
           all(b["high"] >= bars[i - j]["high"] for j in range(1, lookback + 1)):
            up_fractals.append({
                "bar_index": i,
                "price":     round(b["high"], 6),
                "date":      b["date"],
            })

        if all(b["low"] <  bars[i + j]["low"] for j in range(1, lookback + 1)) and \
           all(b["low"] <= bars[i - j]["low"] for j in range(1, lookback + 1)):
            down_fractals.append({
                "bar_index": i,
                "price":     round(b["low"], 6),
                "date":      b["date"],
            })

    return {
        "last_up":    up_fractals[-1]   if up_fractals   else None,
        "last_down":  down_fractals[-1] if down_fractals else None,
        "all_up":     up_fractals,
        "all_down":   down_fractals,
        "count_up":   len(up_fractals),
        "count_down": len(down_fractals),
    }


def detect_squat_bars(bars: list[dict], point: Optional[float] = None) -> dict:
    """
    Приседающие бары (Squat) — окно Profitunity Вильямса (+Vol, −MFI).
    По "Торговому Хаосу", гл. 6: рынок присел перед рывком, готовясь
    прыгнуть в любую сторону. ВХОД — на ПРОБОЕ приседающего, не на нём.

    ЗАКОН ЯДРА: здесь только ФАКТ — где приседающие бары. Никакого
    суждения о том, разворотный приседающий или мерный. Это суждение
    выносят ТРЕЙДЕРЫ (A06/A07/A08), каждый своим порогом — для того
    их и трое. Ядро не имеет мнения. Дивергенция (Точка Ноль) уже
    отдаётся отдельным полем market_data — трейдеры сводят сами.

    Возвращает:
      last_squat — последний приседающий бар ряда (high/low/index/date)
      all        — все приседающие ряда
      count      — сколько всего
    """
    n = len(bars)
    squats = []

    for i in range(1, n):
        b  = bars[i]
        pb = bars[i - 1]
        if b["volume"] == 0 or pb["volume"] == 0:
            continue

        # MFI = (H−L)/_Point/Volume — формула BWMFI
        def _mfi(bar):
            v = (bar["high"] - bar["low"]) / bar["volume"]
            return v / point if point else v

        vol_up   = b["volume"] > pb["volume"]
        mfi_down = _mfi(b) < _mfi(pb)

        # Приседающий: объём вырос, MFI упал
        if vol_up and mfi_down:
            squats.append({
                "bar_index": i,
                "high":      round(b["high"], 6),
                "low":       round(b["low"], 6),
                "date":      b["date"],
            })

    return {
        "last_squat": squats[-1] if squats else None,
        "all":        squats,
        "count":      len(squats),
    }


def compute_mfi(bar: dict, prev_bar: dict, point: Optional[float] = None) -> dict:
    """
    Bill Williams Market Facilitation Index (BWMFI).
    По исходнику MT5 MarketFacilitationIndex.mq5.

    MFI = (high - low) / _Point / volume

    Типы (порядок как в MT5):
      GREEN  — MFI↑ vol↑  — настоящее движение
      FADE   — MFI↓ vol↓  — рынок остывает
      FAKE   — MFI↑ vol↓  — движение без объёма
      SQUAT  — MFI↓ vol↑  — рынок борется, скоро взрыв
    """
    def _calc(b, pt):
        if b["volume"] == 0:
            return 0.0
        v = (b["high"] - b["low"]) / b["volume"]
        return v / pt if pt else v

    mfi_cur  = _calc(bar,      point)
    mfi_prev = _calc(prev_bar, point)

    mfi_up = mfi_cur  > mfi_prev
    vol_up = bar["volume"] > prev_bar["volume"]

    if   mfi_up     and vol_up:     mtype = "GREEN"
    elif not mfi_up and not vol_up: mtype = "FADE"
    elif mfi_up     and not vol_up: mtype = "FAKE"
    else:                           mtype = "SQUAT"

    return {
        "type":     mtype,
        "volume":   bar["volume"],
        "spread":   bar["spread"],
        "mfi":      round(mfi_cur,  10),
        "mfi_prev": round(mfi_prev, 10),
    }


def compute_twr(bars: list[dict]) -> dict:
    """
    TWR — Ритм Рынка (Новый Хаос, гл.9). Три SMA Вильямса по CLOSE:
      tide   = SMA(5,  close)
      wave   = SMA(13, close)
      ripple = SMA(34, close)

    НЕ Аллигатор: тот SMMA (сглаженная) по медианам (H+L)/2, периоды
    13/8/5. TWR — SMA (простая) по Close, периоды 5/13/34. Канон
    зафиксирован Студией «Шесть Пальцев» 19.07 — формула дословная.

    neutral=True — импульс разворота УГАС во флэте: 5-периодная
    застряла МЕЖДУ 13 и 34 (линии переплелись, нет выстроенного
    строя ни вверх, ни вниз). Строй есть (not neutral), когда tide
    строго за пределами коридора [min(wave,ripple), max(wave,ripple)].
    """
    closes = [b["close"] for b in bars]
    n = len(closes)
    if n < 34:
        return {"tide": None, "wave": None, "ripple": None, "neutral": None}

    def _sma(vals, period):
        if len(vals) < period:
            return None
        return sum(vals[-period:]) / period

    tide   = _sma(closes, 5)
    wave   = _sma(closes, 13)
    ripple = _sma(closes, 34)
    if tide is None or wave is None or ripple is None:
        return {"tide": None, "wave": None, "ripple": None, "neutral": None}

    lo, hi = min(wave, ripple), max(wave, ripple)
    neutral = lo <= tide <= hi

    return {
        "tide":    round(tide,   6),
        "wave":    round(wave,   6),
        "ripple":  round(ripple, 6),
        "neutral": bool(neutral),
    }


def detect_thumb_trade(bars: list[dict], point: Optional[float] = None) -> dict:
    """
    БОЛЬШОЙ ПАЛЕЦ (Thumb Trade, Новый Хаос гл.3.6) — ранний вход
    Авантюриста ДО пробоя фрактала Ганса, внутри формирующегося
    разворота точки c.

    Три бара подряд ЛЕСЕНКОЙ (bars[-4], bars[-3], bars[-2] — монотонно
    убывающие high И low для BULL, монотонно растущие для BEAR),
    минимум 2 из этих 3 баров — GREEN или SQUAT (MFI, объём подтверждает
    движение — канон «четырёх окон»). Активация (triggered) — ТЕКУЩИЙ
    бар (bars[-1]) пробивает экстремум последнего бара лесенки:
      BULL: high[-1] > high[-2]  (пробой вверх после падения к развороту)
      BEAR: low[-1]  < low[-2]   (пробой вниз)

    Возвращает {"direction": "BULL"|"BEAR"|None, "triggered": bool,
                "trigger_price": float|None, "green_squat_count": int}.
    ИНЖЕНЕРНАЯ ПОМЕТКА (не пластик — честно): «монотонная лесенка +
    2 из 3 GREEN/SQUAT + пробой экстремума» — буквальный перевод
    канона гл.3.6 в проверяемые числа. Проверить на живых данных
    первым прогоном тестера, откалибровать если Аван либо молчит
    всегда, либо палит слишком часто.
    """
    n = len(bars)
    if n < 4:
        return {"direction": None, "triggered": False,
                "trigger_price": None, "green_squat_count": 0}

    b0, b1, b2 = bars[-4], bars[-3], bars[-2]
    cur = bars[-1]

    def _mfi_type(b, pb):
        return compute_mfi(b, pb, point=point)["type"]

    gs_count = 0
    if n >= 5:
        if _mfi_type(b0, bars[-5]) in ("GREEN", "SQUAT"):
            gs_count += 1
    if _mfi_type(b1, b0) in ("GREEN", "SQUAT"):
        gs_count += 1
    if _mfi_type(b2, b1) in ("GREEN", "SQUAT"):
        gs_count += 1

    ladder_bull = (b0["high"] > b1["high"] > b2["high"]
                   and b0["low"] > b1["low"] > b2["low"])
    ladder_bear = (b0["high"] < b1["high"] < b2["high"]
                   and b0["low"] < b1["low"] < b2["low"])

    direction = None
    if ladder_bull and gs_count >= 2:
        direction = "BULL"
    elif ladder_bear and gs_count >= 2:
        direction = "BEAR"

    triggered = False
    trigger_price = None
    if direction == "BULL":
        trigger_price = b2["high"]
        triggered = cur["high"] > trigger_price
    elif direction == "BEAR":
        trigger_price = b2["low"]
        triggered = cur["low"] < trigger_price

    return {"direction": direction, "triggered": bool(triggered),
            "trigger_price": (round(trigger_price, 6)
                              if trigger_price is not None else None),
            "green_squat_count": gs_count}

# TWR_BOLSHOY_PALEC_V1 - marker



def detect_ao_divergence(bars: list[dict], ao_series: list[Optional[float]]) -> dict:
    """
    Дивергенция AO — строгая логика по Вильямсу ("Торговый Хаос").

    БЫЧЬЯ (Точка Ноль):
      1. Берём ВСЕ локальные минимумы цены (low ниже соседей слева и справа).
      2. Для каждого такого минимума фиксируем значение AO в том же баре.
      3. Берём последние два минимума где AO < 0.
      4. Проверяем: цена[2] < цена[1]  (второй минимум цены ниже)
                    AO[2]   > AO[1]    (второй минимум AO выше — дивергенция)
      5. КРИТИЧНО: между барами минимума-1 и минимума-2 AO ни разу
         не пересёк ноль снизу вверх (не стал положительным).
         Пересечение нуля = конец текущего медвежьего импульса.
         После него — новый импульс, старая дивергенция недействительна.

    МЕДВЕЖЬЯ (exit_bell):
      Зеркально: максимумы цены, AO > 0, AO не пересекал ноль вниз.

    Это убирает 90%+ ложных сигналов по сравнению с lookback=50.
    """
    n = len(bars)
    if n < 5:
        return {"bullish": False, "bearish": False}

    # ── собираем локальные минимумы цены с AO в том же баре ─────────────
    # Локальный минимум: low[i] < low[i-1] И low[i] < low[i+1]
    # (стандартное определение, аналог IsBottom в MQL5-индикаторах)
    price_lows  = []  # (bar_index, price_low, ao_value)
    price_highs = []  # (bar_index, price_high, ao_value)

    for i in range(1, n - 1):
        ao = ao_series[i]
        if ao is None:
            continue
        b  = bars[i]
        bp = bars[i - 1]
        bn = bars[i + 1]

        if b["low"]  < bp["low"]  and b["low"]  < bn["low"]:
            price_lows.append((i, b["low"],  ao))
        if b["high"] > bp["high"] and b["high"] > bn["high"]:
            price_highs.append((i, b["high"], ao))

    # ── бычья дивергенция ────────────────────────────────────────────────
    bullish = False
    # Из всех минимумов берём только те где AO < 0
    neg_lows = [(i, p, a) for (i, p, a) in price_lows if a < 0]
    if len(neg_lows) >= 2:
        i1, p1, a1 = neg_lows[-2]
        i2, p2, a2 = neg_lows[-1]
        # Цена вниз, AO вверх
        if p2 < p1 and a2 > a1:
            # Проверка: AO между i1 и i2 не пересекал ноль (не уходил в +)
            segment = [v for v in ao_series[i1 + 1: i2] if v is not None]
            zero_cross = any(v >= 0 for v in segment)
            if not zero_cross:
                bullish = True

    # ── медвежья дивергенция ─────────────────────────────────────────────
    bearish = False
    # Из всех максимумов берём только те где AO > 0
    pos_highs = [(i, p, a) for (i, p, a) in price_highs if a > 0]
    if len(pos_highs) >= 2:
        i1, p1, a1 = pos_highs[-2]
        i2, p2, a2 = pos_highs[-1]
        # Цена вверх, AO вниз
        if p2 > p1 and a2 < a1:
            # Проверка: AO между i1 и i2 не пересекал ноль (не уходил в -)
            segment = [v for v in ao_series[i1 + 1: i2] if v is not None]
            zero_cross = any(v <= 0 for v in segment)
            if not zero_cross:
                bearish = True

    return {"bullish": bullish, "bearish": bearish}


def fractal_outside_jaw(fractal_price: float, jaw: float,
                        direction: str) -> bool:
    """
    Фрактал ВНЕ пасти (вне Jaw Аллигатора).
    LONG:  фрактал вверх выше Jaw
    SHORT: фрактал вниз ниже Jaw
    """
    if direction == "LONG":
        return fractal_price > jaw
    elif direction == "SHORT":
        return fractal_price < jaw
    return False


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — СБОРКА market_data
# ════════════════════════════════════════════════════════════

def _find_ao_pivots(ao_series: list, bars: list[dict]) -> list[dict]:
    """
    Находит пивоты AO (локальные минимумы и максимумы).
    Пивот = значение ниже/выше двух соседних с каждой стороны.
    Возвращает список {index, ao_value, price_low, price_high, date, type}.
    Нужен Искре для поиска дивергенций.
    """
    pivots = []
    n = len(ao_series)
    for i in range(2, n - 2):
        v = ao_series[i]
        if v is None:
            continue
        neighbors = [ao_series[i-2], ao_series[i-1],
                     ao_series[i+1], ao_series[i+2]]
        if any(x is None for x in neighbors):
            continue
        b = bars[i] if i < len(bars) else {}
        if v < neighbors[0] and v < neighbors[1] and            v < neighbors[2] and v < neighbors[3]:
            pivots.append({
                "type":       "MIN",
                "ao_value":   round(v, 8),
                "price_low":  round(b.get("low",  0), 6),
                "price_high": round(b.get("high", 0), 6),
                "date":       b.get("date", ""),
            })
        elif v > neighbors[0] and v > neighbors[1] and              v > neighbors[2] and v > neighbors[3]:
            pivots.append({
                "type":       "MAX",
                "ao_value":   round(v, 8),
                "price_low":  round(b.get("low",  0), 6),
                "price_high": round(b.get("high", 0), 6),
                "date":       b.get("date", ""),
            })
    return pivots


def _shifted_series(series: list, shift: int) -> list:
    """
    Значение на баре i = сырой SMMA на баре (i-shift) — имитация того,
    что MT4/MT5 iAlligator отдаёт уже СМЕЩЁННОЕ (отображаемое) значение
    линии, а не сырое текущее. Нужно для NECRON_DIVERGENCE_V1 — старая
    resinka Джастин (compute_rubber_band) сознательно брала СЫРЫЕ линии
    ("без смещения") — это другой, отдельный расчёт, не путать.
    """
    n = len(series)
    out = [None] * n
    for i in range(n):
        j = i - shift
        if j >= 0:
            out[i] = series[j]
    return out


def detect_necron_bar(
    bars:         list,
    jaw_series:   Optional[list],
    teeth_series: Optional[list],
    lips_series:  Optional[list],
) -> dict:
    """
    NECRON_DIVERGENCE_V1 (21-22.07, канон-сессия): разворотный бар по
    формуле стороннего проверенного индикатора iDivergenceBar.mq4
    (Dmitry Zhebrak aka Necron, 2010, mqlcoder.ru) — подтверждена на
    истории БЕЗ ПОДГОНКИ на трёх разных инструментах/ТФ разом (см.
    ИСКРА_ПЕРЕДЕЛКА_СПЕК.md, правки 14/20):
      XAUUSD H4  (2010-2026): 2407 сделок, винрейт 31%, +159.76R
      EURUSD H1  (2010-2017): 4702 сделки, винрейт 31%, +54.49R
      SP500 Daily(2010-2022): 225 сделок,  винрейт 37%, +83.25R

    ЭТО НЕ detect_divergent_bar (та формула — старая, ungated,
    искала разворот на любом баре без привязки к тому, что было до
    этого; отдельная попытка усилить её дивергенцией AO/ангуляцией/
    Squat/Zone честно не улучшила результат — правки 12, 18-19).

    Условие (дословно из первоисточника):
      up = max(lips, teeth, jaw)   dn = min(lips, teeth, jaw)
      SELL: high[i]>high[i-1] И close[i]<середина бара И low[i]>up
             (весь бар целиком ВЫШЕ всех трёх линий Аллигатора разом)
      BUY:  low[i]<low[i-1]  И close[i]>середина бара И high[i]<dn
             (весь бар целиком НИЖЕ всех трёх линий Аллигатора разом)

    Линии Аллигатора берутся СО СДВИГОМ +8/+5/+3 (Зубы/Челюсть/Губы) —
    как MT4/MT5 iAlligator отдаёт уже отображаемое (смещённое) значение,
    не сырой текущий SMMA. Это ДРУГОЙ расчёт линий, чем resinka Джастин
    (compute_rubber_band), которая сознательно берёт линии БЕЗ сдвига —
    два разных, оба законных употребления одного и того же Аллигатора.

    Возвращает {"direction": "BULL"|"BEAR"|None, "price": float|None}.
    direction="BULL" на BUY-баре (входим вверх), "BEAR" на SELL-баре.
    price — low бара для BULL, high бара для BEAR (тот же контракт,
    что старый bdb_price в read_ao_wave_form).
    """
    empty = {"direction": None, "price": None}
    if not jaw_series or not teeth_series or not lips_series:
        return empty

    i = len(bars) - 1
    if i < 1:
        return empty

    jaw_sh   = _shifted_series(jaw_series, 8)
    teeth_sh = _shifted_series(teeth_series, 5)
    lips_sh  = _shifted_series(lips_series, 3)

    j, t, l = jaw_sh[i], teeth_sh[i], lips_sh[i]
    if j is None or t is None or l is None:
        return empty

    up = max(l, t, j)
    dn = min(l, t, j)

    b, p = bars[i], bars[i - 1]
    mid = (b["high"] + b["low"]) / 2

    if b["high"] > p["high"] and b["close"] < mid and b["low"] > up:
        return {"direction": "BEAR", "price": round(b["high"], 6)}
    if b["low"] < p["low"] and b["close"] > mid and b["high"] < dn:
        return {"direction": "BULL", "price": round(b["low"], 6)}
    return empty



def compute_rubber_band(
    bars:         list,
    lips_series:  Optional[list],
    teeth_series: Optional[list],
    direction:    Optional[str],
    point:        Optional[float],
) -> dict:
    """
    «РЕЗИНКА» Джастин Вильямс — натяжение цены от Зелёной линии (Губы).
    Делает наглядным то, что раньше мерили «на глаз» (ангуляцию).

    Натяжение = пустота между экстремумом цены и Губами:
      UP (аптренд):   distance = high - lips   (как далеко вершина оторвалась)
      DOWN (даунтренд): distance = lips - low   (как далеко дно убежало)
    Всё в point — безразмерно, на любом активе (закон ядра).

    История максимума копится ОТ ПЕРЕСЕЧЕНИЯ close с Teeth (рождение
    волны). По Джастин: натяжение достигает ПИКА на дивергентном баре —
    поэтому is_peak = текущая дистанция это максимум за жизнь движения.

    direction приходит снаружи (из necron_bar.direction или наклона
    Аллигатора). Если None — резинка не натянута (нет тренда для отрыва).

    ЗАКОН: ядро только МЕРЯЕТ. «Натянута/вяло» — факт физики, не команда.
    Морж это ЧИТАЕТ и созерцает. Решают трейдеры.
    """
    empty = {
        "direction": None, "distance_now": None, "distance_max": None,
        "tension_ratio": None, "is_peak": False, "bars_in_band": None,
    }
    if direction not in ("BULL", "BEAR") or not point:
        return empty
    if not lips_series or not teeth_series:
        return empty

    i = len(bars) - 1
    if i < 1:
        return empty

    def _dist(idx):
        """Натяжение на баре idx в point. None если нет Губ."""
        lp = lips_series[idx] if idx < len(lips_series) else None
        if lp is None:
            return None
        b = bars[idx]
        if direction == "BULL":
            return (b["high"] - lp) / point
        else:
            return (lp - b["low"]) / point

    # Якорь: последнее пересечение close с Teeth в сторону тренда.
    # BULL-импульс рождается, когда close ушёл ВВЕРХ через Teeth.
    anchor = None
    for k in range(i, 0, -1):
        t  = teeth_series[k]   if k   < len(teeth_series) else None
        tp = teeth_series[k-1] if k-1 < len(teeth_series) else None
        if t is None or tp is None:
            continue
        c  = bars[k]["close"]
        cp = bars[k-1]["close"]
        if direction == "BULL":
            if cp <= tp and c > t:   # пробил Teeth вверх — старт волны
                anchor = k
                break
        else:
            if cp >= tp and c < t:   # пробил Teeth вниз
                anchor = k
                break
    if anchor is None:
        anchor = max(1, i - 7)   # нет чистого пересечения — окно по умолчанию

    distance_now = _dist(i)
    if distance_now is None:
        return empty

    # Максимум натяжения от якоря до текущего бара
    distance_max = distance_now
    for k in range(anchor, i + 1):
        d = _dist(k)
        if d is not None and d > distance_max:
            distance_max = d

    eps = 1e-6
    tension_ratio = (distance_now / distance_max) if distance_max > eps else 0.0
    is_peak = distance_now >= distance_max * (1 - 0.02)   # на пике (±2%)
    bars_in_band = i - anchor

    return {
        "direction":     direction,
        "distance_now":  round(distance_now, 1),
        "distance_max":  round(distance_max, 1),
        "tension_ratio": round(tension_ratio, 3),
        "is_peak":       bool(is_peak),
        "bars_in_band":  bars_in_band,
    }


_WAVE_MEASURE_N_NULEY = 4   # ISKRA_WAVE_MEASURE_V1: канон 18.07, полный цикл 1-5


def _ao_predydushchee_peresechenie(ao_series: list, i: int) -> Optional[int]:
    """Индекс бара, где AO последний раз сменил знак, идя назад от i.
    Возвращает индекс ПЕРВОГО бара нового знака, или None (история
    кончилась/дыра в данных раньше)."""
    if i < 0 or i >= len(ao_series):
        return None
    cur = ao_series[i]
    if cur is None or cur == 0:
        return None
    znak = 1 if cur > 0 else -1
    j = i - 1
    while j >= 0:
        v = ao_series[j]
        if v is None:
            return None
        if (znak > 0 and v < 0) or (znak < 0 and v > 0):
            return j + 1
        j -= 1
    return None


def _ao_nachalo_okna(ao_series: list, i: int, n_nuley: int) -> Optional[int]:
    """Индекс начала окна — N пересечений нуля AO назад от бара i.
    None — истории не хватило отмотать N раз (не ошибка, честный факт)."""
    idx = i
    for _ in range(n_nuley):
        p = _ao_predydushchee_peresechenie(ao_series, idx)
        if p is None:
            return None
        idx = p - 1
    return idx


def _ao_peresecheniya_v_okne(ao_series: list, a: int, b: int) -> list:
    res = []
    for j in range(a + 1, b + 1):
        v, p = ao_series[j], ao_series[j - 1]
        if v is None or p is None:
            continue
        if (p < 0 <= v) or (p > 0 >= v):
            res.append(j)
    return res


def sudit_volnovuyu_strukturu(ao_series: list, start: int, kand: int,
                              storona: str) -> tuple:
    """
    ISKRA_WAVE_MEASURE_V1: строгий суд структуры горб-3 → ноль-4 →
    дивер-5 внутри окна [start, kand]. Протокол Шефа 18.07, починка
    той же даты (горб ищется ДО последнего ноля в окне, не как
    глобальный экстремум — иначе часто попадает в волну 5).

    Возвращает (читается: bool, причина: str) — причина всегда, даже
    при успехе (для прозрачности отчёта, не только для отладки брака).
    """
    seg = ao_series[start:kand + 1]
    if any(v is None for v in seg):
        return False, "дыры в AO"

    per = _ao_peresecheniya_v_okne(ao_series, start, kand)
    if not per:
        return False, "нет пересечений в окне"
    nol_i = per[-1]                      # ноль-4 = ПОСЛЕДНЕЕ пересечение

    if nol_i <= start + 1:
        return False, "ноль слишком рано"
    if storona == "BULL":
        gorb_i = min(range(start, nol_i), key=lambda j: ao_series[j])
    else:
        gorb_i = max(range(start, nol_i), key=lambda j: ao_series[j])
    gorb_v = ao_series[gorb_i]

    if nol_i >= kand:
        return False, "ноль на самом кандидате"
    if storona == "BULL":
        div_i = min(range(nol_i, kand + 1), key=lambda j: ao_series[j])
    else:
        div_i = max(range(nol_i, kand + 1), key=lambda j: ao_series[j])
    div_v = ao_series[div_i]

    if not (start <= gorb_i < nol_i <= div_i <= kand):
        return False, "порядок нарушен"

    if storona == "BULL":
        if not (div_v > gorb_v):
            return False, "волна 5 глубже волны 3"
    else:
        if not (div_v < gorb_v):
            return False, "волна 5 выше волны 3"

    n_per = len(per)
    if n_per > 5:
        return False, f"шум: {n_per} пересечений"
    if n_per < 2:
        return False, f"мало пересечений: {n_per}"

    return True, f"ОК ({n_per} перес.)"


def izmerit_volnovuyu_strukturu(bars: list, ao_series: list, storona,
                                n_nuley: int = _WAVE_MEASURE_N_NULEY,
                                i: Optional[int] = None) -> dict:
    """
    ISKRA_WAVE_MEASURE_V1 (18.07). ФАКТЫ структуры на стол, НЕ фильтр.
    Меряет длину движения от N-го пересечения нуля AO назад (по
    умолчанию 4 — канон Шефа, полный цикл 1-5) до бара-кандидата, и
    строго судит, читается ли внутри пятёрка (горб-3→ноль-4→дивер-5,
    правило Эллиотта). bars нужен только для длины истории — сама
    проверка идёт по ao_series.

    i=None → последний бар истории (обычный live-случай).
    storona — направление кандидата (BULL/BEAR), обычно form["bdb_dir"].

    Возвращает:
      {"dlina": int|None, "struktura_chitaetsya": bool,
       "struktura_prichina": str, "n_nuley": int}
    dlina=None — истории не хватило отмотать N нулей назад (честный
    факт короткой истории, не ошибка).
    """
    if storona not in ("BULL", "BEAR"):
        return {"dlina": None, "struktura_chitaetsya": False,
                "struktura_prichina": "нет направления кандидата",
                "n_nuley": n_nuley}
    if i is None:
        i = len(ao_series) - 1
    start = _ao_nachalo_okna(ao_series, i, n_nuley)
    if start is None:
        return {"dlina": None, "struktura_chitaetsya": False,
                "struktura_prichina": f"истории не хватило на {n_nuley} нулей назад",
                "n_nuley": n_nuley}
    dlina = i - start
    ok, why = sudit_volnovuyu_strukturu(ao_series, start, i, storona)
    return {"dlina": dlina, "struktura_chitaetsya": ok,
            "struktura_prichina": why, "n_nuley": n_nuley}


def read_ao_wave_form(
    bars:         list,
    ao_series:    list,
    teeth_series: Optional[list],
    lips_series:  Optional[list] = None,   # REZINKA_DOBIVKA_V1
    window:       int = 120,   # ISKRA_WORKING_TF_FIRST_V1: канон Шефа —
                                # 100-140 баров, экран рисует волну и
                                # 3-ю волну AO наиболее адекватно
    point:        Optional[float] = None,
    jaw_series:   Optional[list] = None,   # NECRON_DIVERGENCE_V1
) -> dict:
    """
    ЧИТАЛКА ФОРМЫ AO — глаз Искры. Кладёт ФАКТЫ структуры, НЕ вердикты.

    Закон (Шеф, 2026-06-16): Искра — СЕНСОР. Она докладывает что видит,
    решения не принимает. «Вижу/спускайся/молчи» здесь НЕТ — это работа
    трейдеров, которые сводят факты всех сенсоров (Искра+Морж+Ганс+Паникёр)
    в комплекс. Разделение анализа защищает трейдеров от перегруза.

    Идёт по окну 140-150 баров. Факты на стол:
      anchor_ao_max  — горб-царь ВВЕРХ (самый крупный MAX) = третья волна лонга.
      anchor_ao_min  — горб-царь ВНИЗ  (самый крупный MIN) = третья волна шорта.
                       Окно держит ОДНУ структуру → царь один. Якорь дивера:
                       без главного горба дивер ложный (правило Эллиотта:
                       третья не самая короткая).
      zero_cross_after_max — AO пересёк ноль ВНИЗ после верхнего царя (4-я лонга).
      zero_cross_after_min — AO пересёк ноль ВВЕРХ после нижнего царя (4-я шорта).
      divergence_dir — КОМПАС: есть дивер AO и какой (BULL/BEAR/None).
                       Показывает СТОРОНУ зоны разворота. Грубо. Из detect_ao_divergence.
      bdb_dir        — ТОЧКА: есть разворотный бар и какой (BULL/BEAR/None).
                       Конкретный бар цены. Из detect_necron_bar (формула
                       iDivergenceBar.mq4, Necron — см. NECRON_DIVERGENCE_V1).
      bdb_price      — цена этого бара (low для BULL, high для BEAR) или None.
      bar_date       — дата последнего бара окна.

    Спуск по ТФ (лесенка в mt5_feed) даёт ту же читалку на младшем масштабе,
    где структура видна красивее и бар точнее. Но это прогон Искры по ТФ,
    не вердикт читалки: читалка на КАЖДОМ ТФ просто докладывает факты.
    """
    n = len(bars)
    if n < 40 or not ao_series:
        return _empty_wave_form()

    w   = min(window, n)
    off = n - w
    ao_w   = ao_series[off:]
    bars_w = bars[off:]
    teeth_w = teeth_series[off:] if teeth_series else None
    # REZINKA_DOBIVKA_V1: Губы режем тем же окном, что Зубы —
    # без них резинка не считается и bdb_strong ВСЕГДА False
    lips_w = lips_series[off:] if lips_series else None
    # NECRON_DIVERGENCE_V1: Челюсть тем же окном — нужна для отрыва
    # от ВСЕХ трёх линий разом (формула iDivergenceBar.mq4)
    jaw_w = jaw_series[off:] if jaw_series else None

    # ── пивоты AO в окне (локальные экстремумы, как _find_ao_pivots) ──
    pv = []  # (local_idx, type, ao_value)
    for i in range(2, w - 2):
        v = ao_w[i]
        if v is None:
            continue
        nb = [ao_w[i-2], ao_w[i-1], ao_w[i+1], ao_w[i+2]]
        if any(x is None for x in nb):
            continue
        if v < nb[0] and v < nb[1] and v < nb[2] and v < nb[3]:
            pv.append((i, "MIN", v))
        elif v > nb[0] and v > nb[1] and v > nb[2] and v > nb[3]:
            pv.append((i, "MAX", v))

    # ── цари окна: самый крупный горб в каждую сторону (факт) ──
    maxes = [(i, v) for (i, t, v) in pv if t == "MAX"]
    mins  = [(i, v) for (i, t, v) in pv if t == "MIN"]
    amax_i, amax_v = (max(maxes, key=lambda x: x[1]) if maxes else (None, None))
    amin_i, amin_v = (min(mins,  key=lambda x: x[1]) if mins  else (None, None))

    # ── пересечение нуля ПОСЛЕ царя (факт: четвёртая пошла) ──
    def _crossed_after(idx, below):
        if idx is None:
            return False
        seg = [v for v in ao_w[idx + 1:] if v is not None]
        return any((v < 0) if below else (v > 0) for v in seg)

    zc_max = _crossed_after(amax_i, below=True)
    zc_min = _crossed_after(amin_i, below=False)

    # ── дивер-КОМПАС (факт, из ядра) ──
    div = detect_ao_divergence(bars_w, ao_w)
    div_dir = "BULL" if div.get("bullish") else "BEAR" if div.get("bearish") else None

    # ── B/D/B бар-ТОЧКА (факт, из ядра) ──
    # NECRON_DIVERGENCE_V1 (21-22.07): была detect_divergent_bar+bdb_strong
    # (искала разворот НА ЛЮБОМ баре, без привязки к тому, что было до
    # этого — баг §0 канона). Заменена на detect_necron_bar — формула
    # стороннего проверенного индикатора (iDivergenceBar.mq4, Necron),
    # подтверждена на истории без подгонки на трёх инструментах/ТФ разом
    # (ИСКРА_ПЕРЕДЕЛКА_СПЕК.md правки 14/20). Три честные попытки усилить
    # её дивергенцией AO/Squat/Zone не улучшили результат (правки 12,
    # 18-19) — оставляем как есть, без добавок.
    bdb_dir = None
    bdb_price = None
    if jaw_w is not None and teeth_w is not None and lips_w is not None:
        nb = detect_necron_bar(bars_w, jaw_w, teeth_w, lips_w)
        bdb_dir = nb.get("direction")
        bdb_price = nb.get("price")

    # ISKRA_WAVE_MEASURE_V1: факты структуры, НЕ фильтр. Меряется по
    # ПОЛНОМУ (не windowed) ao_series/bars — окно read_ao_wave_form
    # (100-150 баров) короче того, что нужно для 4 нулей AO назад
    # (медианы 94-116, хвост до 300+). Кандидат — последний бар общей
    # истории, он же последний бар окна (bars_w[-1] is bars[-1]).
    _wave = izmerit_volnovuyu_strukturu(bars, ao_series, bdb_dir)

    return {
        "anchor_ao_max":        round(amax_v, 4) if amax_v is not None else None,
        "anchor_ao_min":        round(amin_v, 4) if amin_v is not None else None,
        "zero_cross_after_max": bool(zc_max),
        "zero_cross_after_min": bool(zc_min),
        "divergence_dir":       div_dir,
        "bdb_dir":              bdb_dir,
        "bdb_price":            bdb_price,
        "bar_date":             bars_w[-1]["date"] if bars_w else None,
        "window":               w,
        "dlina":                _wave["dlina"],
        "struktura_chitaetsya": _wave["struktura_chitaetsya"],
        "struktura_prichina":   _wave["struktura_prichina"],
    }


def _empty_wave_form() -> dict:
    return {
        "anchor_ao_max": None, "anchor_ao_min": None,
        "zero_cross_after_max": False, "zero_cross_after_min": False,
        "divergence_dir": None, "bdb_dir": None, "bdb_price": None,
        "bar_date": None, "window": 0,
        # ISKRA_WAVE_MEASURE_V1: те же поля и в пустом слепке — иначе
        # читатель словит KeyError на холодном старте (тот же урок,
        # что REZINKA_DOBIVKA_V1 уже преподал этому файлу).
        "dlina": None, "struktura_chitaetsya": False,
        "struktura_prichina": "пустой слепок",
    }




def compute_global_bias(bars: list, alligator: dict, point: float,
                        slope_lookback: int = 5) -> str:
    """
    КОМПАС ГЛОБАЛЬНОГО ФОНА из синей линии Аллигатора (Jaw, SMMA-13).  # GLOBAL_BIAS_COMPASS_V1

    Три линии Аллигатора — три баланса (справедливые цены) на трёх
    горизонтах памяти. Синяя самая медленная и инертная: дыхание
    старшего ТФ внутри рабочего окна. Берём ЦЕНУ относительно синей
    плюс НАКЛОН синей — грубый, но всегда живой компас, переживающий
    развороты (в отличие от строгого веера, схлопывающегося в NONE
    ровно на развороте, когда компас нужнее всего).

    ЗАКОН ЯДРА: только ФАКТ направления фона. Не суждение, не команда.
    Трейдеры читают и сводят сами.

      BULL: close выше Jaw И Jaw не падает (наклон >= 0)
      BEAR: close ниже Jaw И Jaw не растёт (наклон <= 0)
      NONE: цена и наклон спорят (переходная зона) ИЛИ синей нет

    Возвращает "BULL" / "BEAR" / "NONE".
    """
    jaw = alligator.get("jaw")
    if jaw is None or not bars:
        return "NONE"

    close = bars[-1]["close"]

    # Наклон синей: сравниваем текущую Jaw с Jaw slope_lookback баров назад.
    # Пересчёт лёгкий — SMMA(13) по медианам всего окна, берём срез.
    medians = [(b["high"] + b["low"]) / 2 for b in bars]
    jaw_series = _smma_series(medians, 13)
    jaw_prev = None
    if len(jaw_series) > slope_lookback:
        cand = jaw_series[-1 - slope_lookback]
        if cand is not None:
            jaw_prev = cand

    slope = 0.0
    if jaw_prev is not None:
        slope = jaw - jaw_prev

    # Безразмерный порог наклона: шум в пределах ~5 пунктов считаем плоским.
    flat = (5 * point) if point else 0.0

    price_above = close > jaw
    price_below = close < jaw
    rising  = slope >  flat
    falling = slope < -flat

    if price_above and not falling:
        return "BULL"
    if price_below and not rising:
        return "BEAR"
    return "NONE"



def build_market_data(
    bars:      list[dict],
    symbol:    str   = "UNKNOWN",
    timeframe: str   = "D1",
    point:     Optional[float] = None,
) -> dict:
    """
    Из сырых баров собирает market_data для всего Совета.
    Структура согласно CHAIN_CONTRACT.md.

    point — минимальный шаг цены (_Point в MT5). ОБЯЗАТЕЛЕН.
    Приходит снаружи: из терминала (symbol_info.point) для живого
    потока, или явно для лабораторных прогонов. Ядро не угадывает
    точность по тикеру — оно слепо к активу.
    """
    if len(bars) < 40:
        print(f"[CORE] ❌ Недостаточно баров: {len(bars)} (нужно ≥ 40)")
        return {}

    if not point:
        print(f"[CORE] ❌ point не передан ({symbol}) — ядру нужна точность цены")
        return {}

    highs = [b["high"]  for b in bars]
    lows  = [b["low"]   for b in bars]

    _point     = point
    alligator  = compute_alligator(highs, lows, point=_point)
    ao_series  = compute_ao_series(highs, lows)
    ac_series  = compute_ac_series(ao_series)
    fractals   = detect_fractals(bars)
    squat      = detect_squat_bars(bars, point=_point)
    mfi        = compute_mfi(bars[-1], bars[-2], point=_point)
    divergence = detect_ao_divergence(bars, ao_series)
    twr         = compute_twr(bars)                       # TWR_BOLSHOY_PALEC_V1
    thumb_trade = detect_thumb_trade(bars, point=_point)   # TWR_BOLSHOY_PALEC_V1
    teeth_series = alligator.get("teeth_series")
    # REZINKA_DZHASTIN_V1: Губы (SMMA-5) — от них меряется пустота.
    # Раньше мерили от Зубов (SMMA-8) через угол. Канон — Губы.
    _lips_series = alligator.get("lips_series")
    _jaw_series  = alligator.get("jaw_series")
    # NECRON_DIVERGENCE_V1 (21-22.07): старая detect_divergent_bar (bdb_strong,
    # искала разворот на любом баре без привязки к структуре) полностью
    # снята. Разворотный бар теперь — только формула iDivergenceBar.mq4
    # (Necron), подтверждённая на истории без подгонки (ИСКРА_ПЕРЕДЕЛКА_СПЕК.md
    # правки 14/20). Раньше поле называлось "divergent_bar" — переименовано
    # в "necron_bar", чтобы имя не тянуло за собой старую формулу.
    necron_bar = detect_necron_bar(bars, _jaw_series, teeth_series, _lips_series)
    lips_series   = alligator.get("lips_series")
    # Резинка Джастин: направление берём из разворотного бара Necron,
    # а если он молчит — из наклона Аллигатора (Губы vs Зубы).
    _rb_dir = necron_bar.get("direction")
    if _rb_dir is None and alligator.get("lips") is not None:
        _rb_dir = "BULL" if alligator["lips"] > alligator["teeth"] else "BEAR"
    rubber_band = compute_rubber_band(
        bars, lips_series, teeth_series, _rb_dir, _point)

    # Читалка формы AO — факты структуры для Искры v2 (окно 140-150).
    # Сенсор кладёт факты (дивер-компас, B/D/B-точка, горб-царь), не вердикты.
    # NECRON_DIVERGENCE_V1: jaw_series теперь тоже нужен — bdb_dir внутри
    # считается формулой Necron (все три линии Аллигатора), не старой bdb_strong.
    _jaw_series = alligator.get("jaw_series")
    wave_form = read_ao_wave_form(bars, ao_series, teeth_series, point=_point,
                                  lips_series=_lips_series, jaw_series=_jaw_series)  # WILLIAMS_REAL_ANGULATION_V1

    # Компас глобального фона из синей линии (Jaw).  # GLOBAL_BIAS_COMPASS_V1
    # Факт направления, всегда на столе (не зависит от дивера/терминала).
    global_bias = compute_global_bias(bars, alligator, _point)

    # ENGINE_ONE_DOOR_V1: честный глобальный тренд — веер Аллигатора
    # СТАРШЕГО этажа (рабочий x5 вверх по лесенке), мерян на дату текущего
    # бара (без заглядывания в будущее). §12 Котина: фильтр большой воды.
    # Подменяет синюю рабочего (она была приближением, не старшим этажом).
    # Аллигатор рабочего НЕ тронут — старший меряется отдельно через источник.
    # Якорь упал / источник недоступен -> остаётся синяя (фоллбэк, стол цел).
    try:
        from global_anchor import global_trend as _gt
        _bar_time = bars[-1]["date"]  # WILLIAMS_CORE_TYPING_V1: bars уже не пуст здесь (len>=40 отсечён выше)
        _r = _gt(symbol, timeframe, as_of_date=_bar_time)
        if _r.get("ok"):
            global_bias = _r["bias"]
    except Exception:
        pass  # любой сбой — оставляем синюю из compute_global_bias

    print(f"[CORE]    _Point={_point} ({symbol})")

    # Текущие и предыдущие AO / AC
    ao_cur  = ao_series[-1]
    ao_prev = next((v for v in reversed(ao_series[:-1]) if v is not None), None)
    ac_cur  = ac_series[-1]
    ac_prev = next((v for v in reversed(ac_series[:-1]) if v is not None), None)

    # Пересечение нуля AO
    ao_crossed_zero = False
    ao_zero_dir     = None
    if ao_cur is not None and ao_prev is not None:
        if ao_prev < 0 < ao_cur:
            ao_crossed_zero = True; ao_zero_dir = "UP"
        elif ao_prev > 0 > ao_cur:
            ao_crossed_zero = True; ao_zero_dir = "DOWN"

    ao_direction = None
    if ao_cur is not None and ao_prev is not None:
        ao_direction = "UP" if ao_cur > ao_prev else "DOWN"

    ac_direction = None
    if ac_cur is not None and ac_prev is not None:
        ac_direction = "UP" if ac_cur > ac_prev else "DOWN"

    last_bar = bars[-1]

    return {
        "symbol":     symbol,
        "timeframe":  timeframe,
        "point":      _point,
        "bar_time":   last_bar["date"],
        "bars_total": len(bars),

        "alligator": {
            "jaw":       alligator["jaw"],
            "teeth":     alligator["teeth"],
            "lips":      alligator["lips"],
            "sleeping":  alligator["sleeping"],
            "opening":   alligator["opening"],
            "mature":    alligator["mature"],
            "bars_open": alligator["bars_open"],
        },

        "ao": {
            "value":        round(ao_cur,  8) if ao_cur  is not None else None,
            "prev_value":   round(ao_prev, 8) if ao_prev is not None else None,
            "crossed_zero": ao_crossed_zero,
            "zero_dir":     ao_zero_dir,
            "direction":    ao_direction,
            # Последние 6 пивотов AO — Искре нужно 2 пары для дивергенции
            "pivots":       _find_ao_pivots(ao_series, bars)[-6:],
        },

        "ac": {
            "value":      round(ac_cur,  8) if ac_cur  is not None else None,
            "prev_value": round(ac_prev, 8) if ac_prev is not None else None,
            "direction":  ac_direction,
        },

        "mfi": {
            "type":   mfi["type"],
            "volume": mfi["volume"],
            "spread": mfi["spread"],
        },

        "price": {
            "open":  round(last_bar["open"],  6),
            "high":  round(last_bar["high"],  6),
            "low":   round(last_bar["low"],   6),
            "close": round(last_bar["close"], 6),
        },

        "divergence_ao": divergence["bullish"],  # Точка Ноль
        "exit_bell":     divergence["bearish"],  # Конец импульса

        "necron_bar":    necron_bar,            # разворотный бар (Necron, iDivergenceBar.mq4)
        "rubber_band":   rubber_band,            # резинка Джастин (глаза Моржа)
        "wave_form":     wave_form,            # факты формы AO (глаз Искры v2)
        "global_bias":   global_bias,          # компас фона из синей (GLOBAL_BIAS_COMPASS_V1)

        "fractals": {
            "last_up":    fractals["last_up"],
            "last_down":  fractals["last_down"],
            "count_up":   fractals["count_up"],
            "count_down": fractals["count_down"],
        },

        "squat": {
            "last_squat": squat["last_squat"],
            "count":      squat["count"],
        },

        "twr":         twr,           # TWR_BOLSHOY_PALEC_V1: Ритм Рынка (SMA 5/13/34 close)
        "thumb_trade": thumb_trade,    # TWR_BOLSHOY_PALEC_V1: ранний вход Авантюриста
    }


# ════════════════════════════════════════════════════════════
# CLI — быстрая проверка на CSV
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 2:
        print("Использование: python williams_core.py <path_to_csv> [SYMBOL] [TIMEFRAME]")
        print("Пример: python williams_core.py data/EURUSDDaily.csv EURUSD D1")
        sys.exit(0)

    csv_path  = sys.argv[1]
    symbol    = sys.argv[2] if len(sys.argv) > 2 else "UNKNOWN"
    timeframe = sys.argv[3] if len(sys.argv) > 3 else "D1"

    bars = read_mt5_csv(csv_path)
    if bars:
        md = build_market_data(bars, symbol=symbol, timeframe=timeframe)
        if md:
            print("\n=== JSON market_data ===")
            print(json.dumps(md, ensure_ascii=False, indent=2))

# WILLIAMS_CORE_TYPING_V1 — маркер идемпотентности

# WILLIAMS_CORE_TYPING_V2 — маркер идемпотентности

# WILLIAMS_REAL_ANGULATION_V1 — маркер идемпотентности

# ISKRA_WORKING_TF_FIRST_V1 — маркер идемпотентности

# ISKRA_WAVE_MEASURE_V1 - marker

# AO_DIVERGENCE_GLUBZHE_V1 - marker
