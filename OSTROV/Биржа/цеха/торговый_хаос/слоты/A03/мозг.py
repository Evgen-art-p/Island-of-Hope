# GRONDHEIM_CITY/Биржа/цеха/торговый_хаос/слоты/A03/мозг.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН ПАНИКЁРА (A03) — третье звено Совета Биржи
# Версия: 0.2 · перенос на слотовое шасси (Закон Картриджа для кода)
# Резидент: Паник · Роль: фаза толпы (бывший Паникёр)
#
# Паникёр — измеритель массовой истерии. Он НЕ анализирует — он ЧУВСТВУЕТ
# толпу нутром через структуру: четыре окна Profitunity (объём × эффективность),
# объём, спред. Цена меняется последней — толпа выдаёт себя раньше, в объёме.
#
# Просыпается от ОБСТАНОВКИ (Искра не молчит ИЛИ рынок живой), наследует этаж
# Искры (смотрит толпу там, где она нашла событие). Статусы Искры/Моржа — фон,
# накал толпы Паникёр меряет САМ по окнам MFI.
#
# ЗАКОН ЗЕРКАЛА: Паникёр — датчик настроения, не командир. Даёт обстановку
# (фаза толпы + накал). Трейдеры читают его НАОБОРОТ и решают сами.
#
# Форма — близнец мозга Моржа (A02): живая модель + штатная память
# + язык датчика + душа города + петля обучения. Без костылей.
# ─────────────────────────────────────────────────────────────

import json
import re
from pathlib import Path
from typing import Optional

# ЗАКОН КАРТРИДЖА ДЛЯ КОДА: файл живёт ПРЯМО В СЛОТЕ, рядом со своим
# промптом и знаниями. Слот несёт с собой всё: слоты/A03/{мозг.py,
# промпт.md, знания/, данные/}.
_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/A03/
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
KNOWLEDGE    = _SLOT_DIR / "знания" / "PANIKYOR_MATH.md"   # книга Паникёра (психология толпы)
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "panikyor_stats.json"


# ════════════════════════════════════════════════════════════
# ПАМЯТЬ ПАНИКЁРА — ШТАТНЫЙ trading_state.json (шина Биржи)
# ─────────────────────────────────────────────────────────────
# Читает Искру (t1_status + масштаб) и Моржа (morj_status) — обстановка.
# Свою фазу (panic) пишет рядом — оттуда её прочитает Архивариус и трейдеры.
# ════════════════════════════════════════════════════════════

def _load_iskra_signal() -> dict:
    """Слышит Искру из шины: статус + масштаб спуска (этаж/сторона)."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("iskra", {
        "t1_status": "NOT_FOUND", "zero_point_price": None,
        "trend_direction": None, "found_timeframe": None})


def _load_morj_signal() -> dict:
    """Слышит Моржа из шины: жив ли рынок (morj_status)."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("morj", {"morj_status": "SLEEPING"})


def _load_panic_memory() -> dict:
    """Своя рабочая память Паникёра из штатного trading_state."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("panic", {
        "panic_phase": "ASLEEP", "action_for_traders": "NEUTRAL",
        "history_dna": ""})


def _save_panic_memory(signal: dict, scale_timeframe: Optional[str] = None):
    """
    Пишет память Паникёра в штатный trading_state — туда, откуда её прочитает
    Архивариус (A05, сигнатура похожести) и трейдеры (panic_phase как фон).

    КЛЮЧИ (CHAIN_CONTRACT v1.9, A03):
      panic_phase        — ASLEEP/DISBELIEF/GREED/TENSION/DECEPTION/PANIC
      crowd_sentiment    — одна фраза толпы (в Атлас)
      action_for_traders — NEUTRAL/HIGH_SKEPTICISM/GREEN_LIGHT_IF_GANS
      scale_timeframe    — на каком этаже мерил (унаследован от Искры) — для Ганса
    """
    valid_phases = ("ASLEEP", "DISBELIEF", "GREED", "TENSION", "DECEPTION", "PANIC")
    phase = signal.get("panic_phase", "ASLEEP")
    if phase not in valid_phases:
        phase = "ASLEEP"

    valid_actions = ("NEUTRAL", "HIGH_SKEPTICISM", "GREEN_LIGHT_IF_GANS")
    action = signal.get("action_for_traders", "NEUTRAL")
    if action not in valid_actions:
        action = "NEUTRAL"

    from hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    tstate.setdefault("panic", {})
    tstate["panic"]["panic_phase"]        = phase
    tstate["panic"]["crowd_sentiment"]    = signal.get("crowd_sentiment", "")
    tstate["panic"]["action_for_traders"] = action
    tstate["panic"]["history_dna"]        = signal.get("history_dna", "")
    tstate["panic"]["scale_timeframe"]    = scale_timeframe
    save_trading_state(tstate)


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА ПАНИКЁРА — его как зеркала толпы
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "asleep": 0, "greed": 0, "tension": 0,
            "deception": 0, "panic": 0, "disbelief": 0}


def _update_stats(signal: dict) -> dict:
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    phase = signal.get("panic_phase", "ASLEEP").lower()
    if phase in stats:
        stats[phase] = stats.get(phase, 0) + 1
    # Личный журнал РОЛИ едет со слотом — создаём папку, как у Моржа.
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ДВУХСЛОЙНОГО ОТВЕТА (как у Искры/Моржа)
# ════════════════════════════════════════════════════════════

def _parse_panic(response: str) -> tuple[str, dict]:
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
# РАБОЧИЙ РАЗГОВОР С ПАНИКЁРОМ (клик пузырька в чате)
# ════════════════════════════════════════════════════════════

def chat_with_panikyor(question: str, last_run: Optional[dict] = None,
                       dialog: Optional[list] = None) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ ЗАМЕР ТОЛПЫ (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Фаза толпы: {sig.get('panic_phase','—')}\n"
            f"Что кричала толпа: {sig.get('crowd_sentiment','—')}\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про ЭТОТ замер. Отвечай как Паникёр — нервно, "
            "живо, по тому что чувствовал в толпе. Живым голосом, БЕЗ JSON."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не мерил толпу в этой сессии. Если Шеф спрашивает про "
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
                    agent_id="A03_PANIKYOR", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return f"⚠️ Паникёр не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — один живой замер толпы
# ════════════════════════════════════════════════════════════

def run_panikyor(symbol: str = "XAUUSD", timeframe: str = "H4",
                 bars_count: int = 300) -> dict:
    """
    Один замер толпы Паникёром по свежему бару из терминала.

    Цепочка: РЫНОК → Искра → Морж → Паникёр СЛЫШИТ обстановку (их статусы) →
    смотрит структуру толпы (окна MFI, объём, спред) → чует фазу истерии.

    Наследует этаж Искры (как Морж): меряет толпу там, где Искра нашла событие.

    Возвращает словарь для каркаса (как run_morj):
      {ok, error, narrative, signal, stats, market, iskra_status, morj_status}
    """
    # ── 0. Обстановка: слышим Искру и Моржа из шины ──────────
    iskra = _load_iskra_signal()
    morj  = _load_morj_signal()
    iskra_status = iskra.get("t1_status", "NOT_FOUND")
    morj_status  = morj.get("morj_status", "SLEEPING")
    # Наследуем этаж Искры: толпу меряем там, где она нашла событие.
    iskra_tf = iskra.get("found_timeframe")
    if iskra_tf:
        print(f"[PANIC] 🔗 Наследую масштаб Искры: {timeframe} → {iskra_tf}")
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

    # ── 2. Посчитать market_data ядром (окна MFI внутри) ─────
    from williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {"ok": False, "error": "Ядро не собрало market_data",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {}, "iskra_status": iskra_status, "morj_status": morj_status}

    mfi   = md.get("mfi", {})
    price = md.get("price", {})

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
            print(f"[PANIC] 🧬 За столом: {_n['носитель']['имя']}")
    except Exception as e:
        print(f"[PANIC] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    # ── 4. Память Паникёра (штатная) ─────────────────────────
    mem = _load_panic_memory()
    prev_phase  = mem.get("panic_phase", "ASLEEP")
    history_dna = mem.get("history_dna", "")

    prompt    = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    knowledge = KNOWLEDGE.read_text(encoding="utf-8") if KNOWLEDGE.exists() else ""

    # Паникёр видит ТОЛЬКО структуру толпы: окна MFI + объём + спред + свечка.
    # Не Аллигатор, не AO — это органы Искры и Моржа.
    md_for_panic = {
        "symbol":    md.get("symbol"),
        "timeframe": md.get("timeframe"),
        "bar_time":  md.get("bar_time"),
        "mfi": {
            "type":   mfi.get("type"),     # GREEN/FADE/FAKE/SQUAT — окно Profitunity
            "volume": mfi.get("volume"),   # масса толпы
            "spread": mfi.get("spread"),   # цена страха
        },
        "price": price,                    # свечка — куда качнуло СЕЙЧАС
    }

    user_msg = (
        "=== ОБСТАНОВКА (фон — статусы Искры и Моржа) ===\n"
        f"Искра (что-то происходит в структуре): {iskra_status}\n"
        f"Морж (рынок живой/мёртвый): {morj_status}\n"
        "Это фон. НАКАЛ толпы ты меряешь САМ по структуре ниже.\n\n"
        "=== ТВОЯ РАБОЧАЯ ПАМЯТЬ (прошлый замер) ===\n"
        f"prev_panic_phase: {prev_phase}\n"
        f"history_dna: {history_dna or '(пусто — первый замер)'}\n\n"
        "=== СТРУКТУРА ТОЛПЫ (твои органы) ===\n"
        f"{json.dumps(md_for_panic, ensure_ascii=False, indent=2)}\n\n"
        "Закон: ты ИЗМЕРИТЕЛЬ ИСТЕРИИ, не командир. Почувствуй фазу толпы "
        "по окну MFI (GREEN=эйфория/SQUAT=истерика напряжения/FAKE=обман/"
        "FADE=скука), объёму (масса толпы) и спреду (страх). Свечка — куда "
        "качнуло сейчас. Выдай строго двухслойный JSON {narrative, signal}: "
        "panic_phase (ASLEEP/DISBELIEF/GREED/TENSION/DECEPTION/PANIC), "
        "crowd_sentiment (фраза толпы), action_for_traders (NEUTRAL/"
        "HIGH_SKEPTICISM/GREEN_LIGHT_IF_GANS). Ничего вне JSON."
    )

    # ── 5. Паникёр чувствует живой моделью (с душой) ─────────
    system_full = prompt
    if soul:
        system_full = (
            prompt
            + "\n\n=== ТВОЁ СОСТОЯНИЕ И ПАМЯТЬ (душа) ===\n"
            + soul
            + "\n\n=== ГРАНИЦА ===\n"
            "Настроение красит твой ГОЛОС (narrative) — ты нервный, бывший "
            "скальпер, у тебя дрожит чашка кофе. Но ФАЗА (signal) — факт "
            "структуры толпы (окно MFI, объём, спред). Твоя личная тревога "
            "не создаёт SQUAT из воздуха. Чувствуй как хочешь, мерь толпу честно."
        )

    try:
        response = chat(system=system_full, user=user_msg, knowledge=knowledge,
                        agent_id="A03_PANIKYOR", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return {"ok": False, "error": f"Паникёр не смог почувствовать: {e}",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {"symbol": symbol, "timeframe": timeframe,
                           "bar_time": md.get("bar_time"), "point": point},
                "iskra_status": iskra_status, "morj_status": morj_status}

    # ── 6. Распарсить, сохранить память и статистику ─────────
    narrative, signal = _parse_panic(response)
    _save_panic_memory(signal, scale_timeframe=timeframe)
    stats = _update_stats(signal)

    # ── 6b. ПЕТЛЯ ОБУЧЕНИЯ — точность зеркала → ДНК ─────────
    # Паникёр учится на честности отражения толпы, не на деньгах.
    # Грубый сигнал: фаза совпала со структурой (GREEN→GREED, SQUAT→TENSION
    # и т.д.) — хорошо отразил. Натянул PANIC на скучный FADE — плохо.
    phase    = signal.get("panic_phase", "ASLEEP")
    mfi_type = mfi.get("type", "")
    coherent = (
        (mfi_type == "GREEN" and phase == "GREED") or
        (mfi_type == "SQUAT" and phase == "TENSION") or
        (mfi_type == "FAKE"  and phase == "DECEPTION") or
        (mfi_type == "FADE"  and phase == "ASLEEP") or
        phase in ("DISBELIEF", "PANIC")   # эти держатся на статусе+свечке, не на окне
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
