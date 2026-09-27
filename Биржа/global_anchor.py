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


# GLUBINA_KOMPASA_V2 ─────────────────────────────────────────
# Память о том, что уже спрашивали. В процессе, не на диске: поднял
# город заново — спросит заново.
_LESENKA = (2000, 500, 200)
_GLUBINA_POMNIM: dict = {}     # (символ, этаж) -> ступень, которая дала бары
_PUSTO_POMNIM: dict = {}       # (символ, этаж) -> когда получили пусто
_PUSTO_ZHIVYOT = 60.0          # секунд молчать, не переспрашивая
_POCHEMU_SKAZALI: set = set()  # KOMPAS_GOVORIT_POCHEMU_V1: один раз на пару


# GLUBINA_KOMPASA_V3 ─────────────────────────────────────────
# Замер Шефа (XAUUSD H1, 1500 баров): 83 с всего, из них 68 — походы
# за барами старшего этажа. 919 обращений к терминалу на 919 баров,
# каждое с MetaTrader5.initialize и переводом двух тысяч дат в строки.
# Старший этаж не должен спрашиваться чаще, чем он меняется: H8 живёт
# восемь часов, а мы дёргали его девятьсот раз подряд.
_BARY_KESH: dict = {}          # (символ, этаж, момент) -> (бары, point, когда)
_KESH_ZHIVYOT = 20.0           # секунд в живом режиме (курсора нет)
_KESH_PREDEL = 8               # больше ответов не храним


def _moment_kursora() -> str:
    """Где стоит курсор истории. В прогоне это пришпиливает память к
    конкретному моменту прошлого — подмены быть не может. В живом
    режиме курсора нет, вернётся пусто."""
    try:
        import istoriya
        return str(istoriya.gde_stoim() or "")
    except Exception:
        return ""


def _sprosit_starshiy(symbol: str, senior: str):
    """Бары старшего этажа. Ступень, которая сработала, запоминаем;
    пустой ответ помним минуту и не переспрашиваем; сами бары держим
    в памяти, пока они не могли измениться."""
    import time
    from feed_source import bars as source_bars

    klyuch = (symbol, senior)

    # ── память о самих барах ──
    kesh_klyuch = (symbol, senior, _moment_kursora())
    est = _BARY_KESH.get(kesh_klyuch)
    if est is not None:
        bary, point, kogda = est
        # момент истории задан — ответ вечен: прошлое не меняется
        if kesh_klyuch[2] or (time.time() - kogda) < _KESH_ZHIVYOT:
            return bary, point

    def _zapomnit(bary, point):
        _BARY_KESH[kesh_klyuch] = (bary, point, time.time())
        while len(_BARY_KESH) > _KESH_PREDEL:
            _BARY_KESH.pop(next(iter(_BARY_KESH)))
        return bary, point
    kogda = _PUSTO_POMNIM.get(klyuch)
    if kogda and (time.time() - kogda) < _PUSTO_ZHIVYOT:
        return [], None

    poryadok = list(_LESENKA)
    znaem = _GLUBINA_POMNIM.get(klyuch)
    if znaem in poryadok:
        poryadok.remove(znaem)
        poryadok.insert(0, znaem)

    for glubina in poryadok:
        sbars, point = source_bars(symbol, senior, count=glubina)
        if sbars:
            _GLUBINA_POMNIM[klyuch] = glubina
            _PUSTO_POMNIM.pop(klyuch, None)
            return _zapomnit(sbars, point)   # GLUBINA_KOMPASA_V3

    _PUSTO_POMNIM[klyuch] = time.time()
    return _zapomnit([], None)               # GLUBINA_KOMPASA_V3


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
    # VODA_NA_STOLE_V1: направление старшего этажа меряется СТРУКТУРОЙ
    # (две вершины и две впадины по фракталу, подтверждение этажом выше),
    # а не веером Аллигатора. Веер соврал на откате в 43% случаев — такой
    # факт трейдеру на стол класть нельзя. Вид ответа прежний, читатели
    # не меняются. Вода не сложилась — вернётся bias=NONE, и это честное
    # «воды нет», а не поломка.
    try:
        import voda as _voda
        _v = _voda.voda_na_stole(symbol, working_tf, as_of_date=as_of_date)
        if _v:
            return _v
    except Exception as _e:
        print(f"[ЯКОРЬ] вода не посчиталась ({_e}) — беру старый веер")

    senior = senior_timeframe(working_tf)
    if senior is None:
        return {"bias": "NONE", "senior_tf": None, "ok": False,
                "why": "рабочий на потолке лесенки — старшего этажа нет"}

    # старшие бары через источник (кран real|tester решает откуда)
    from feed_source import bars as source_bars
    # GLUBINA_KOMPASA_V1: было count=100000 — сто тысяч дневок, четыреста
    # лет. В тестере это значило «весь файл» и работало; живой MetaTrader
    # на такое число отдаёт ПУСТО, и компас пропадал молча, а трейдер
    # оставался без старшей воды. Ниже по коду и так берутся последние
    # 300 баров — больше компасу не нужно никогда.
    # Лесенка посильных глубин: 2000 — умолчание mt5_feed.pull_bars,
    # 200 — то, что терминал отдаёт заведомо. Первый непустой ответ.
    # GLUBINA_KOMPASA_V2: лесенку помним, в пустое не долбимся.
    # V1 перебирала три ступени КАЖДЫЙ раз, а компас считается на
    # каждом баре. Пустой старший этаж стоил трёх обращений вместо
    # одного (в реале — с двумя повторами и снами внутри насоса), и
    # прогон по истории из быстрого стал ползучим.
    sbars, point = _sprosit_starshiy(symbol, senior)
    _syrykh = len(sbars or [])          # KOMPAS_GOVORIT_POCHEMU_V1
    # ОТСЕЧКА БУДУЩЕГО: оставляем только старшие бары ДО даты прогона.
    # Старший бар входит, если его дата <= дате текущего рабочего бара.
    if as_of_date and sbars:
        cut = as_of_date.strip()
        sbars = [b for b in sbars if b.get("date", "") <= cut]
    # берём последние 300 из отсечённого (хватает на Аллигатор + запас)
    if len(sbars) > 300:
        sbars = sbars[-300:]
    # KOMPAS_GOVORIT_POCHEMU_V1: раньше отказ был немым — «не пришёл»,
    # и всё. Теперь видно, на чём споткнулись: источник не дал баров,
    # обрезка по дате прогона съела всё, или их просто мало.
    try:
        _skolko = len(sbars or [])
        _klyuch_zh = (symbol, senior)
        if _skolko < 40 or point is None:
            if _klyuch_zh not in _POCHEMU_SKAZALI:
                _POCHEMU_SKAZALI.add(_klyuch_zh)
                if not _syrykh:
                    _p = "источник не дал ни одного бара"
                elif _skolko == 0:
                    _p = (f"источник дал {_syrykh}, но обрезка по дате "
                          f"{as_of_date} не оставила ни одного")
                elif point is None:
                    _p = f"баров {_skolko}, но цена шага (point) неизвестна"
                else:
                    _p = (f"баров всего {_skolko} — меньше сорока, "
                          f"мерить веер не на чем")
                print(f"[КОМПАС] {symbol} {senior}: {_p}")
    except Exception:
        pass

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

# GLUBINA_KOMPASA_V1 - marker

# GLUBINA_KOMPASA_V2 - marker

# GLUBINA_KOMPASA_V3 - marker

# VODA_NA_STOLE_V1 - marker
