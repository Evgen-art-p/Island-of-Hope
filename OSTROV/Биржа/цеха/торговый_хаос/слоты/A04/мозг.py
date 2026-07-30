# GRONDHEIM_CITY/Биржа/цеха/торговый_хаос/слоты/A04/мозг.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН ГАНСА (A04) — четвёртое звено Совета Биржи
# Версия: 0.2 · перенос на слотовое шасси (Закон Картриджа для кода)
# Резидент: Ганс · Роль: искатель боли (действительный фрактал)
#
# Ганс — искатель боли. Он видит ОДНУ вещь: действительный фрактал
# относительно Красной линии (Зубы Аллигатора, Teeth). Не волну, не
# тренд, не AO. Фрактал — первый сигнал входа по Котину.
#
# Просыпается от ОБСТАНОВКИ (как Паникёр), наследует этаж Искры (ищет
# фрактал там, где она нашла событие). Статусы Искры/Моржа/Паникёра — фон.
# Действительность фрактала Ганс судит САМ: центр фрактала vs Красная.
#
# ЗАКОН §1f — БЕЗ ГЕЙТА: Ганс ВСЕГДА кладёт факт на стол (есть
# действительный фрактал вне Красной / мёртвый / нет). Никаких ворот,
# никакого entry_trigger=AND. Сенсор сообщает — трейдеры решают.
#
# ЗАКОН КНИЖКИ (HANS_MATH.md): фильтр = КРАСНАЯ (Teeth), не Синяя (Jaw).
# Первоисточник истина. Ганс читает teeth из готового market_data —
# ядро не дёргает, сравнивает два числа, что ядро уже отдало.
#
# Форма — близнец мозга Паникёра (A03): живая модель + штатная память
# + язык датчика + душа города + петля обучения. Без костылей.
# ─────────────────────────────────────────────────────────────

import json
import re
from pathlib import Path
from typing import Optional

# ЗАКОН КАРТРИДЖА ДЛЯ КОДА: файл живёт ПРЯМО В СЛОТЕ, рядом со своим
# промптом и знаниями. Слот несёт с собой всё: слоты/A04/{мозг.py,
# промпт.md, знания/, данные/}.
_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/A04/
_CEH_DIR     = _SLOT_DIR.parent.parent                     # торговый_хаос/
_REPO        = _CEH_DIR.parents[3]                          # корень репо
_BIRZHA_CODE = _REPO / "Биржа"                              # общий код (движок, llm)

# KLON_DUSHI_V1: пара (цех, слот) — ИЗ ПУТИ мозга, без хардкода личности.
# Контора не ломается: её слоты зовутся «архивариус»/«исполнитель».
_CEH  = _CEH_DIR.name
_SLOT = _SLOT_DIR.name

import sys as _sys
if str(_BIRZHA_CODE) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA_CODE))

from llm import chat

PROMPT_PATH  = _SLOT_DIR / "промпт.md"
KNOWLEDGE    = _SLOT_DIR / "знания" / "HANS_MATH.md"   # книга Ганса (фрактал + Красная)
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "hans_stats.json"

# Свежесть фрактала: фрактал из прошлой жизни рынка — мусор, не добыча.
# Центр должен быть в последних N барах от конца ряда.
_FRESH_BARS = 12


# ════════════════════════════════════════════════════════════
# ПАМЯТЬ ГАНСА — ШТАТНЫЙ trading_state.json (шина Биржи)
# ─────────────────────────────────────────────────────────────
# Читает Искру (t1_status + масштаб) — обстановка и этаж.
# Свой триггер (hans) пишет рядом — оттуда его прочитают трейдеры.
# ════════════════════════════════════════════════════════════

def _load_iskra_signal() -> dict:
    """Слышит Искру из шины: статус + масштаб спуска (этаж/сторона)."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("iskra", {
        "t1_status": "NOT_FOUND", "zero_point_price": None,
        "trend_direction": None, "found_timeframe": None})


def _load_morj_signal() -> dict:
    """Слышит Моржа из шины: жив ли рынок (morj_status) — фон."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("morj", {"morj_status": "SLEEPING"})


def _load_hans_memory() -> dict:
    """Своя рабочая память Ганса из штатного trading_state."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("hans", {
        "fractal_valid": False, "fractal_side": None,
        "history_dna": ""})


def _save_hans_memory(signal: dict, scale_timeframe: Optional[str] = None):
    """
    Пишет память Ганса в штатный trading_state — туда, откуда её прочитают
    трейдеры (A06/A07/A08, фрактал-уровень как ориентир) и Архивариус (A05).

    КЛЮЧИ:
      fractal_valid    — есть ли ДЕЙСТВИТЕЛЬНЫЙ фрактал вне Красной (bool)
      fractal_side     — LONG / SHORT / None (на какой стороне Красной)
      fractal_price    — цена фрактала (ориентир Buy Stop / Sell Stop для трейдеров)
      absorption_ratio — оценка поглощения 0.0–1.0 (Squat-топливо, фон)
      scale_timeframe  — на каком этаже искал (унаследован от Искры)
      history_dna      — короткий след прогона
    """
    valid_sides = ("LONG", "SHORT")
    side = signal.get("fractal_side")
    if side not in valid_sides:
        side = None

    # absorption в [0,1]
    try:
        absorption = float(signal.get("absorption_ratio", 0.0))
    except (TypeError, ValueError):
        absorption = 0.0
    absorption = max(0.0, min(1.0, absorption))

    from hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    tstate.setdefault("hans", {})
    tstate["hans"]["fractal_valid"]    = bool(signal.get("fractal_valid", False))
    tstate["hans"]["fractal_side"]     = side
    tstate["hans"]["fractal_price"]    = signal.get("fractal_price")
    tstate["hans"]["absorption_ratio"] = absorption
    tstate["hans"]["scale_timeframe"]  = scale_timeframe
    tstate["hans"]["history_dna"]      = signal.get("history_dna", "")
    save_trading_state(tstate)


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА ГАНСА — как часто находит действительный фрактал
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "valid": 0, "dead": 0, "none": 0, "squat_fuel": 0}


def _update_stats(signal: dict) -> dict:
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1

    if signal.get("fractal_valid"):
        stats["valid"] = stats.get("valid", 0) + 1
    elif signal.get("fractal_side") is not None or signal.get("fractal_price") is not None:
        # фрактал был, но по другую сторону Красной / в шуме — мёртвый
        stats["dead"] = stats.get("dead", 0) + 1
    else:
        stats["none"] = stats.get("none", 0) + 1

    if float(signal.get("absorption_ratio", 0.0) or 0.0) >= 0.7:
        stats["squat_fuel"] = stats.get("squat_fuel", 0) + 1

    # Личный журнал РОЛИ едет со слотом — создаём папку, как у соседей.
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ФИЛЬТР КРАСНОЙ ЛИНИИ — ФАКТ ДВИЖКА (не вердикт)
# ─────────────────────────────────────────────────────────────
# Сравнение двух ГОТОВЫХ чисел из market_data:
#   фрактал-цена (centre High/Low) vs Красная линия (teeth).
# Ядро не дёргается — читаем то, что оно уже отдало.
# ════════════════════════════════════════════════════════════

def _read_fractal_facts(md: dict, iskra_dir: Optional[str]) -> dict:
    """
    Достаёт сырые факты фрактала относительно Красной линии.
    Сторону подсказывает компас Искры (trend_direction): BULL → ищем
    up-фрактал выше Красной (LONG), BEAR → down-фрактал ниже (SHORT).
    Если компаса нет — смотрим обе стороны, берём свежайший действительный.

    Возвращает голые факты — суждение «триггер/нет» НЕ выносит (это
    в голове трейдера). Ганс кладёт факт: действителен ли фрактал.
    """
    alligator = md.get("alligator", {})
    teeth     = alligator.get("teeth")        # КРАСНАЯ — готова из ядра
    fractals  = md.get("fractals", {})
    bars_total = md.get("bars_total", 0)
    last_up   = fractals.get("last_up")
    last_down = fractals.get("last_down")

    facts = {
        "teeth": teeth,
        "up":   None,   # {price, fresh, outside_teeth}
        "down": None,
    }
    if teeth is None:
        return facts

    def _pack(fr, side):
        if not fr:
            return None
        price = fr.get("price")
        idx   = fr.get("bar_index")
        fresh = (bars_total - idx) <= _FRESH_BARS if (idx is not None and bars_total) else False
        if side == "up":
            outside = price > teeth      # выше Красной → действителен для LONG
        else:
            outside = price < teeth      # ниже Красной → действителен для SHORT
        return {"price": price, "bar_index": idx,
                "fresh": fresh, "outside_teeth": outside}

    facts["up"]   = _pack(last_up,   "up")
    facts["down"] = _pack(last_down, "down")
    return facts


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ДВУХСЛОЙНОГО ОТВЕТА ГАНСА (как у остальных)
# ════════════════════════════════════════════════════════════

def _parse_hans(response: str) -> tuple[str, dict]:
    cleaned = re.sub(r"```(?:json)?", "", response).strip()
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(cleaned[start:i + 1])
                        return obj.get("narrative", ""), obj.get("signal", {}) or {}
                    except json.JSONDecodeError:
                        break
    return response.strip(), {}


# ════════════════════════════════════════════════════════════
# РАБОЧИЙ РАЗГОВОР С ГАНСОМ (клик пузырька в чате)
# ════════════════════════════════════════════════════════════

def chat_with_hans(question: str, last_run: Optional[dict] = None,
                   dialog: Optional[list] = None) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ СЛЕД (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Действительный фрактал вне Красной: {sig.get('fractal_valid','—')}\n"
            f"Сторона: {sig.get('fractal_side','—')}  ·  "
            f"цена фрактала: {sig.get('fractal_price','—')}\n"
            f"Поглощение: {sig.get('absorption_ratio','—')}\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про ЭТОТ след. Отвечай как Ганс — холодно, "
            "коротко, по своей добыче (фрактал, Красная линия). Охотник у "
            "следа. Живым голосом, БЕЗ JSON — это разговор, не сигнал."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не выходил на след в этой сессии. Если Шеф спрашивает про "
            "рынок — скажи, что нужно нажать РЫНОК. Отвечай живым голосом, без JSON."
        )

    system = prompt + work_ctx
    try:   # KLON_DUSHI_V1: и в разговоре — ОН, не роль
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n and _n["душа"]:
            system = (prompt + "\n\n=== КТО ТЫ (душа носителя) ===\n"
                      + _n["душа"] + "\n\n" + work_ctx)
    except Exception:
        pass

    history = []
    if dialog:
        for m in dialog[:-1]:
            r = m.get("role"); c = m.get("content", "")
            if r in ("user", "assistant") and c:
                history.append({"role": r, "content": c})

    try:
        return chat(system=system, user=question, history=history,
                    agent_id="A04_GANS", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return f"⚠️ Ганс не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — один выход Ганса на след
# ════════════════════════════════════════════════════════════

def run_hans(symbol: str = "XAUUSD", timeframe: str = "H4",
             bars_count: int = 300) -> dict:
    """
    Один выход Ганса на след по свежему бару из терминала.

    Цепочка: РЫНОК → Искра → Морж → Паникёр → Ганс СЛЫШИТ обстановку →
    смотрит фрактал относительно Красной линии (Teeth) → кладёт ФАКТ:
    действительный фрактал вне Красной / мёртвый / нет.

    Наследует этаж Искры (как Морж/Паникёр): ищет фрактал там, где она
    нашла событие. БЕЗ ГЕЙТА — кладёт факт всегда (§1f).

    Возвращает словарь для каркаса (как run_panikyor):
      {ok, error, narrative, signal, stats, market, iskra_status, morj_status}
    """
    # ── 0. Обстановка: слышим Искру и Моржа из шины ──────────
    iskra = _load_iskra_signal()
    morj  = _load_morj_signal()
    iskra_status = iskra.get("t1_status", "NOT_FOUND")
    morj_status  = morj.get("morj_status", "SLEEPING")
    iskra_dir    = iskra.get("trend_direction")   # компас: BULL/BEAR/None
    # Наследуем этаж Искры: фрактал ищем там, где она нашла событие.
    iskra_tf = iskra.get("found_timeframe")
    if iskra_tf:
        print(f"[HANS] 🔗 Наследую масштаб Искры: {timeframe} → {iskra_tf} "
              f"(сторона {iskra_dir or '—'})")
        timeframe = iskra_tf

    # ── 1. Поднять контур: бары + point из терминала ─────────
    from mt5_feed import _terminal, _fetch
    mt5 = _terminal()
    if mt5 is None:
        return {"ok": False, "error": "MetaTrader5 не установлен в Python",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {}, "iskra_status": iskra_status, "morj_status": morj_status}

    bars, point = _fetch(mt5, symbol, timeframe, bars_count)
    if not bars or point is None:
        return {"ok": False,
                "error": f"Терминал не дал котировки {symbol} {timeframe}.",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {}, "iskra_status": iskra_status, "morj_status": morj_status}

    # ── 2. Посчитать market_data ядром (фракталы + teeth внутри) ──
    from williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {"ok": False, "error": "Ядро не собрало market_data",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {}, "iskra_status": iskra_status, "morj_status": morj_status}

    mfi   = md.get("mfi", {})
    squat = md.get("squat", {})
    price = md.get("price", {})

    # Факты фрактала относительно Красной — два готовых числа из ядра.
    fr_facts = _read_fractal_facts(md, iskra_dir)

    # ── 3. Душа города ───────────────────────────────────────
    # KLON_DUSHI_V1: ДУША — от НОСИТЕЛЯ (маска, Закон Пары), не от трупа из -2.
    # Было: format_soul_for_agent из снесённой studio/ — падало ВСЕГДА
    # («No module named studio»), работали голыми. Пара — ИЗ ПУТИ мозга.
    soul = ""
    try:
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n:
            soul = _n["душа"]
            print(f"[HANS] 🧬 За столом: {_n['носитель']['имя']}")
    except Exception as e:
        print(f"[HANS] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    # ── 4. Память Ганса (штатная) ────────────────────────────
    mem = _load_hans_memory()
    prev_valid  = mem.get("fractal_valid", False)
    history_dna = mem.get("history_dna", "")

    prompt    = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    knowledge = KNOWLEDGE.read_text(encoding="utf-8") if KNOWLEDGE.exists() else ""

    # Ганс видит ТОЛЬКО свои органы: фрактал + Красная линия + Squat-топливо.
    # Не Аллигатор целиком (это Морж), не AO (это Искра). Одно число teeth = граница.
    md_for_hans = {
        "symbol":    md.get("symbol"),
        "timeframe": md.get("timeframe"),
        "bar_time":  md.get("bar_time"),
        "teeth":     fr_facts["teeth"],          # КРАСНАЯ — твоя граница
        "fractal_up":   fr_facts["up"],          # {price, fresh, outside_teeth} | None
        "fractal_down": fr_facts["down"],
        "mfi": {
            "type":   mfi.get("type"),           # SQUAT/GREEN/FADE/FAKE — топливо
            "volume": mfi.get("volume"),
        },
        "squat_count": squat.get("count"),
        "price": price,
    }

    user_msg = (
        "=== ОБСТАНОВКА (фон — статусы цепочки) ===\n"
        f"Искра (разворот в структуре): {iskra_status}\n"
        f"Морж (рынок живой/мёртвый): {morj_status}\n"
        f"Компас Искры (сторона разворота): {iskra_dir or '—'}\n"
        "Это фон. Действительность фрактала ты судишь САМ по Красной линии.\n\n"
        "=== ТВОЙ ПРОШЛЫЙ СЛЕД (рабочая память) ===\n"
        f"prev_fractal_valid: {prev_valid}\n"
        f"history_dna: {history_dna or '(пусто — первый выход)'}\n\n"
        "=== ТВОИ ОРГАНЫ (фрактал + Красная линия + топливо) ===\n"
        f"{json.dumps(md_for_hans, ensure_ascii=False, indent=2)}\n\n"
        "Закон: ты ИСКАТЕЛЬ БОЛИ, не командир. Красная линия (teeth) — "
        "твоя единственная граница. Фрактал ДЕЙСТВИТЕЛЕН, только если его "
        "центр вне Красной (up выше / down ниже) И он свежий. По другую "
        "сторону Красной или в шуме — фрактал МЁРТВ. Squat (mfi=SQUAT) — "
        "топливо поглощения, НЕ создаёт и НЕ блокирует действительность. "
        "Ты кладёшь ФАКТ на стол ВСЕГДА — есть действительный фрактал / нет. "
        "Не называешь цену входа и стоп — это трейдеры. Выдай строго "
        "двухслойный JSON {narrative, signal}. signal должен содержать: "
        "fractal_valid (bool — действительный фрактал вне Красной есть?), "
        "fractal_side (LONG/SHORT/null), fractal_price (цена фрактала-ориентира "
        "или null), absorption_ratio (0.0–1.0: SQUAT→0.8–0.9, GREEN→0.5–0.7, "
        "FAKE→0.2–0.4, FADE→0.1–0.3). Ничего вне JSON."
    )

    # ── 5. Ганс думает живой моделью (с душой) ───────────────
    system_full = prompt
    if soul:
        system_full = (
            prompt
            + "\n\n=== ТВОЁ СОСТОЯНИЕ И ПАМЯТЬ (душа) ===\n"
            + soul
            + "\n\n=== ГРАНИЦА ===\n"
            "Настроение красит твой ГОЛОС (narrative) — ты циничный, "
            "холодный, терпелив как снайпер. Но СИГНАЛ (signal) — факт "
            "фрактала и Красной линии. Твоё нетерпение не рисует фрактал "
            "там, где его нет. Чувствуй как хочешь, отражай след честно."
        )

    try:
        response = chat(system=system_full, user=user_msg, knowledge=knowledge,
                        agent_id="A04_GANS", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return {"ok": False, "error": f"Ганс не смог выйти на след: {e}",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {"symbol": symbol, "timeframe": timeframe,
                           "bar_time": md.get("bar_time"), "point": point},
                "iskra_status": iskra_status, "morj_status": morj_status}

    # ── 6. Распарсить, сохранить память и статистику ─────────
    narrative, signal = _parse_hans(response)
    _save_hans_memory(signal, scale_timeframe=timeframe)
    stats = _update_stats(signal)

    # ── 6b. ПЕТЛЯ ОБУЧЕНИЯ — точность следа → ДНК ──────────
    # Ганс учится на честности следа, не на деньгах. Грубый сигнал:
    # сказал «действителен» когда факт движка подтверждает (фрактал
    # есть, свежий, вне Красной) — честный нос. Натянул действительность
    # на мёртвый/несвежий фрактал — соврал. Молчание при пустом столе —
    # не ошибка (нет добычи = честный ноль), петлю не трогаем.
    side = signal.get("fractal_side")
    says_valid = bool(signal.get("fractal_valid"))
    # Факт движка: есть ли реально действительный свежий фрактал в сторону.
    fact_up   = fr_facts.get("up")   or {}
    fact_down = fr_facts.get("down") or {}
    fact_valid = (
        (fact_up.get("outside_teeth") and fact_up.get("fresh")) or
        (fact_down.get("outside_teeth") and fact_down.get("fresh"))
    )
    # MAYATNIK_SNYAT_V1: мёртвый маятник sync_to_dna снят (см. патч-док).
    # Сенсор НЕ качает свою ДНК за «точность» — это НЕ-опыт (Чертёж 4.2).
    # Судья сенсора = РЫНОК: hooks._judge_iskra_by_result →
    # nositel.zapisat_vyvod_pare. Вывод оплачивается деньгами, не сам собой.
    # Не воскрешать: сюда придёт Мост, если петля точности заболит.
    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "stats": stats,
        "iskra_status": iskra_status,
        "morj_status": morj_status,
        "market": {
            "symbol":    symbol,
            "timeframe": timeframe,
            "bar_time":  md.get("bar_time"),
            "point":     point,
        },
        "raw": response,
    }


def _my_temp():
    """KLON_DUSHI_V1: натура и состояние носителя → температура головы.
    stress_to_temperature() в llm.py была МЁРТВОЙ — никто не передавал
    temperature, все думали на дефолте. Натура была буквами в промпте.
    None → дефолт модели (носителя нет — ничего не ломаем)."""
    try:
        from nositel import temperatura_slota
        return temperatura_slota(_CEH, _SLOT)
    except Exception:
        return None
