# studio/modules/trading/global_anchor.py
# ─────────────────────────────────────────────────────────────
# ГЛОБАЛЬНЫЙ ЯКОРЬ — фильтр большой воды (§12 Котина "вход в сторону
# глобального тренда"). ENGINE_ONE_DOOR_V1 · 2026-06-23 · Брат + Шеф
#
# ЗАКОН (слово Шефа + книга):
#   · Глобальный тренд считается НЕ из синей рабочего этажа (это была
#     подмена). Он мерится на РЕАЛЬНОМ СТАРШЕМ этаже — рабочий ×5 вверх
#     по лесенке (погрешность ±1 ступень не критична, большая вода та же).
#   · Направление — по ВЕЕРУ Аллигатора старшего этажа (канон: Аллигатор
#     это фильтр направления). Lips>Teeth>Jaw → BULL; наоборот → BEAR;
#     сплелись (спит) → NONE (большой воды нет — фильтр молчит честно).
#   · Аллигатор РАБОЧЕГО не трогаем — он живёт по книжке как есть.
#   · Старшие бары берёт ИСТОЧНИК (feed_source) — кран real|tester сам
#     решает, терминал или папка. Слепо к активу и к источнику.
#
# Одна стрелка на весь стол. Искра, Ганс, трое трейдеров читают ЕЁ как
# глобальный фильтр, перестают разъезжаться по разным небесам.
# ─────────────────────────────────────────────────────────────

from typing import Optional

# Лесенка Шефа — та же, что в mt5_feed (не дублируем смысл, держим копию
# рядом для автономности якоря; шаг считаем по минутам).
_TF_LADDER = ["MN1", "W1", "D1", "H12", "H8", "H4", "H1", "M30", "M15", "M10", "M5"]

# ТФ → минуты (для арифметики ×5). Только этажи лесенки Шефа.
_TF_MINUTES = {
    "MN1": 43200, "W1": 10080, "D1": 1440, "H12": 720, "H8": 480,
    "H4": 240, "H1": 60, "M30": 30, "M15": 15, "M10": 10, "M5": 5,
}

_GLOBAL_MULT = 5   # "примерно впятеро вверх" (слово Шефа)


def senior_timeframe(working_tf: str) -> Optional[str]:
    """
    Старший этаж для рабочего: рабочий в минутах ×5, ближайший этаж
    лесенки СВЕРХУ (с минутами >= цели). Погрешность ±1 ступень не
    критична. Если рабочий уже на потолке (MN1) — старшего нет (None).

    H4(240)×5=1200 → D1(1440). H1(60)×5=300 → H4(240). M15(15)×5=75 → H1.
    """
    tf = (working_tf or "").upper()
    base = _TF_MINUTES.get(tf)
    if base is None:
        return None
    target = base * _GLOBAL_MULT
    # этажи, что СТАРШЕ цели (минут >= target), берём ближайший (минимум из них)
    higher = [(name, m) for name, m in _TF_MINUTES.items() if m >= target]
    if not higher:
        return None   # рабочий уже близок к потолку — старшего нет
    # ближайший сверху = с наименьшими минутами среди тех, что >= target
    name = min(higher, key=lambda x: x[1])[0]
    if name == tf:
        return None   # совпал с рабочим (потолок) — старшего нет
    return name


def global_trend(symbol: str, working_tf: str,
                 as_of_date: Optional[str] = None) -> dict:
    """
    Глобальный фильтр для стола. Берёт старший этаж через ИСТОЧНИК,
    мерит ВЕЕР Аллигатора там (канон: фильтр направления).

    as_of_date — дата текущего бара прогона ("YYYY.MM.DD" или с временем).
    Старшие бары обрезаются по ней — якорь НЕ заглядывает в будущее
    (закон тестера: видим только то, что видел бы реал в тот момент).
    None → берём всю историю (живой реал на последнем баре).

    Возвращает:
      {"bias": "BULL"|"BEAR"|"NONE", "senior_tf": str|None, "ok": bool}

    bias=NONE — старший Аллигатор спит (боковик): большой воды нет.
    Это честный факт, не ошибка — трейдеры узнают, что фильтра нет.
    """
    senior = senior_timeframe(working_tf)
    if senior is None:
        return {"bias": "NONE", "senior_tf": None, "ok": False,
                "why": "рабочий на потолке лесенки — старшего этажа нет"}

    # старшие бары через источник (кран real|tester решает откуда)
    from feed_source import bars as source_bars
    sbars, point = source_bars(symbol, senior, count=100000)
    # ОТСЕЧКА БУДУЩЕГО: оставляем только старшие бары ДО даты прогона.
    # Старший бар входит, если его дата <= дате текущего рабочего бара.
    if as_of_date and sbars:
        cut = as_of_date.strip()
        sbars = [b for b in sbars if b.get("date", "") <= cut]
    # берём последние 300 из отсечённого (хватает на Аллигатор + запас)
    if len(sbars) > 300:
        sbars = sbars[-300:]
    if not sbars or point is None or len(sbars) < 40:
        return {"bias": "NONE", "senior_tf": senior, "ok": False,
                "why": f"старший этаж {senior} не дал баров"}

    # ВЕЕР Аллигатора старшего этажа (канон: фильтр направления).
    # Аллигатор рабочего НЕ трогаем — тут отдельный замер на старших барах.
    from williams_core import compute_alligator
    al = compute_alligator([b["high"] for b in sbars],
                           [b["low"] for b in sbars], point=point)

    if al.get("sleeping"):
        return {"bias": "NONE", "senior_tf": senior, "ok": True,
                "why": "Аллигатор старшего спит — большой воды нет"}

    jaw, teeth, lips = al.get("jaw"), al.get("teeth"), al.get("lips")
    if jaw is None or teeth is None or lips is None:
        return {"bias": "NONE", "senior_tf": senior, "ok": False,
                "why": "Аллигатор старшего не собрался"}

    # Веер: Губы>Зубы>Челюсть → бычий; зеркально → медвежий.
    if lips > teeth > jaw:
        bias = "BULL"
    elif lips < teeth < jaw:
        bias = "BEAR"
    else:
        bias = "NONE"   # линии не выстроены веером — тренд неясен

    return {"bias": bias, "senior_tf": senior, "ok": True,
            "alligator": {"jaw": jaw, "teeth": teeth, "lips": lips,
                          "bars_open": al.get("bars_open")}}


# ════════════════════════════════════════════════════════════
# ВКЛАДЧИК — кладёт честный global_bias (×5) на стол, поверх кривого
# ════════════════════════════════════════════════════════════

def apply_global_bias(market_data: dict, symbol: str, working_tf: str) -> dict:
    """
    ТИХАЯ ПОДМЕНА: берёт собранный ядром market_data и заменяет поле
    global_bias честным трендом со старшего этажа (×5 вверх), мерянным
    на дату ТЕКУЩЕГО бара (market_data["bar_time"]) — без заглядывания
    в будущее.

    Поле то же (global_bias) — трейдеры читают как читали. Меняется
    только содержимое: было «синяя рабочего» (кривое), стало «веер
    Аллигатора старшего этажа» (честное, §12 Котина — фильтр большой воды).

    Кладёт ещё global_bias_tf (на каком старшем этаже мерян) — для
    прозрачности, трейдеры/отчёт могут показать. Старое значение НЕ
    теряем молча: при сбое якоря оставляем что было (откат на ядро).

    Возвращает тот же market_data (мутирует и отдаёт для удобства).
    """
    if not market_data:
        return market_data
    bar_time = market_data.get("bar_time")
    try:
        r = global_trend(symbol, working_tf, as_of_date=bar_time)
        if r.get("ok"):
            market_data["global_bias"]    = r["bias"]        # честный ветер ×5
            market_data["global_bias_tf"] = r.get("senior_tf")
        # если ok=False (старший этаж не дал баров) — оставляем кривой
        # global_bias из ядра как фоллбэк, не роняем стол.
    except Exception as e:
        print(f"[ANCHOR] global_bias не подменён ({e}) — оставлен ядерный")
    return market_data

# GLOBAL_ANCHOR_TYPING_V1 — маркер идемпотентности
