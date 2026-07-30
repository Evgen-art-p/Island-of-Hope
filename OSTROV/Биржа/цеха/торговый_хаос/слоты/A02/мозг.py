# studio/modules/trading/morj_live.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН МОРЖА (A02) — второе звено Совета Биржи
# Версия: 0.1 · Спринт 45 · 2026-06-16
#
# ПЕРВАЯ ПЕРЕДАЧА ПО ЦЕПОЧКЕ. Искра будит сама себя от РЫНКА.
# Морж просыпается НЕ от рынка, а от ЧУЖОГО сигнала — от Искры.
# Он читает её t1_status из штатного trading_state (общая шина цеха),
# смотрит свой Аллигатор + резинку, и выдаёт ФАКТ о контексте.
#
# ЗАКОН ЗЕРКАЛА: Морж — датчик, не командир. Он сообщает
#   «пасть открыта / резинка натянута до предела» — факт физики.
#   Вход и выход решают трейдеры. Морж созерцает.
#
# Затвор Джастин: натяжение резинки растёт долго и само по себе
# не событие. МОМЕНТ фиксации даёт Искра. Пришёл её сигнал —
# Морж делает СРЕЗ дистанции и проверяет: на пике ли натяжение.
#
# Форма — близнец iskra_live.py: живая модель + штатная память
# + язык датчика + душа города + петля обучения. Без костылей.
# ─────────────────────────────────────────────────────────────

import json
import re
from pathlib import Path
from typing import Optional

from llm import chat

# ЗАКОН КАРТРИДЖА ДЛЯ КОДА: файл живёт ПРЯМО В СЛОТЕ, рядом со своим
# промптом и знаниями. Слот несёт с собой всё: слоты/A02/{мозг.py,
# промпт.md, знания/, данные/}.
_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/A02/
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

PROMPT_PATH  = _SLOT_DIR / "промпт.md"
KNOWLEDGE    = _SLOT_DIR / "знания" / "MORJ_MATH.md"   # книга Моржа (Аллигатор+резинка)
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "morj_stats.json"


# ════════════════════════════════════════════════════════════
# ПАМЯТЬ МОРЖА — ШТАТНЫЙ trading_state.json (шина Биржи)
# ─────────────────────────────────────────────────────────────
# Морж читает память Искры (iskra) — её t1_status это его затвор.
# Свою память (morj) пишет рядом — оттуда её прочитает Ганс.
# Единая шина цеха, не плодим файлы.
# ════════════════════════════════════════════════════════════

def _load_iskra_signal() -> dict:
    """Слышит последний сигнал Искры из общей шины. Это затвор Моржа."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("iskra", {
        "t1_status": "NOT_FOUND", "zero_point_price": None,
        "trend_direction": None, "found_timeframe": None})  # MORJ_INHERIT_V2 — масштаб спуска


def _load_morj_memory() -> dict:
    """Своя рабочая память Моржа из штатного trading_state."""
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("morj", {
        "morj_status": "SLEEPING", "wave_1_validated": False,
        "history_dna": ""})


def _save_morj_memory(signal: dict, alligator: Optional[dict] = None,
                      scale_timeframe: Optional[str] = None,
                      inherited_dir: Optional[str] = None):  # MORJ_INHERIT_V2
    """
    Пишет память Моржа в штатный trading_state — туда, откуда её
    прочитает Ганс (A04, ждёт wave_1_validated) и Паникёр (ждёт morj_status).

    КЛЮЧИ ПО ФАКТУ КОДА (не по бумаге):
      morj_status      — SLEEPING/WAKING/AWAKE (MATURE-статуса НЕТ; код
                         в _live_snapshot знает только эти три)
      wave_1_validated — провод к Гансу (A04). Он читает его из этой же
                         шины trading_state, когда оживёт своей вертикалью.
      alligator_state  — слепок Аллигатора (контракт обещает; дашборд читает)
      tension_peak     — резинка на пике (новьё; трибунал подключится в Волну 3)
    """
    # Санитар статуса: MATURE → AWAKE (код наружу MATURE не знает)
    status = signal.get("morj_status", "SLEEPING")
    if status == "MATURE":
        status = "AWAKE"
    if status not in ("SLEEPING", "WAKING", "AWAKE"):
        status = "SLEEPING"

    from hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    tstate.setdefault("morj", {})
    tstate["morj"]["morj_status"]      = status
    tstate["morj"]["wave_1_validated"] = bool(signal.get("wave_1_validated", False))
    tstate["morj"]["tension_peak"]     = bool(signal.get("tension_peak", False))
    tstate["morj"]["history_dna"]      = signal.get("history_dna", "")
    # MORJ_INHERIT_V2: связка для Ганса — ФАКТ прогона (где смотрели,
    # что унаследовали от Искры). Ганс получит точку Искры + контекст
    # Моржа В ОДНОМ масштабе, не вразнобой.
    tstate["morj"]["scale_timeframe"]  = scale_timeframe
    tstate["morj"]["inherited_dir"]    = inherited_dir
    if alligator is not None:
        # alligator_state — контракт обещает, дашборд показывает
        tstate["morj"]["alligator_state"] = {
            "sleeping":  alligator.get("sleeping"),
            "opening":   alligator.get("opening"),
            "mature":    alligator.get("mature"),
            "bars_open": alligator.get("bars_open"),
        }
    save_trading_state(tstate)


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА МОРЖА — его винрейт как стража контекста
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "awake": 0, "sleeping": 0,
            "validated": 0, "vetoed": 0, "tension_peaks": 0}


def _update_stats(signal: dict) -> dict:
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    status = signal.get("morj_status", "SLEEPING")

    if status == "AWAKE":
        stats["awake"] = stats.get("awake", 0) + 1
    if status == "SLEEPING":
        stats["sleeping"] = stats.get("sleeping", 0) + 1
    if signal.get("wave_1_validated"):
        stats["validated"] = stats.get("validated", 0) + 1
    else:
        stats["vetoed"] = stats.get("vetoed", 0) + 1
    if signal.get("tension_peak"):
        stats["tension_peaks"] = stats.get("tension_peaks", 0) + 1

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ДВУХСЛОЙНОГО ОТВЕТА МОРЖА (как у Искры)
# ════════════════════════════════════════════════════════════

def _parse_morj(response: str) -> tuple[str, dict]:
    """Достаёт {narrative, signal}. При сбое — текст как голос."""
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
# РАБОЧИЙ РАЗГОВОР С МОРЖОМ (клик пузырька в чате)
# ════════════════════════════════════════════════════════════

def chat_with_morj(question: str, last_run: Optional[dict] = None,
                   dialog: Optional[list] = None) -> str:
    """
    Разговор с Моржом, знающим свой последний прогон.
    Без обращения к терминалу — болтовня не поднимает MT5.
    """
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        rb  = last_run.get("rubber_band", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ ВЗГЛЯД (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Сигнал Искры (затвор): {last_run.get('iskra_status','—')}\n"
            f"Твой статус: {sig.get('morj_status','—')}\n"
            f"Масштаб подтверждён: {sig.get('wave_1_validated','—')}\n"
            f"Резинка натянута до предела: {sig.get('tension_peak','—')} "
            f"(натяжение {rb.get('tension_ratio','—')})\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про ЭТОТ взгляд. Отвечай как Морж — медленно, "
            "веско, по своим инструментам (Аллигатор, резинка). Живым "
            "голосом, БЕЗ JSON — это разговор, не сигнал."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не смотрел рынок в этой сессии. Если Шеф спрашивает про "
            "рынок — скажи, что нужно нажать РЫНОК, чтобы ты взглянул. "
            "Отвечай живым голосом, без JSON."
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
                    agent_id="A02_MORJ", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return f"⚠️ Морж не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — один живой прогон Моржа
# ════════════════════════════════════════════════════════════

def run_morj(symbol: str = "XAUUSD", timeframe: str = "H4",
             bars_count: int = 300) -> dict:
    """
    Один взгляд Моржа по свежему бару из терминала.

    Цепочка: РЫНОК → Искра записала t1_status в trading_state →
    Морж СЛЫШИТ его (затвор) → смотрит Аллигатор + резинку →
    делает срез натяжения → выдаёт ФАКТ о контексте.

    Возвращает словарь для каркаса (как run_iskra):
      {ok, error, narrative, signal, stats, market, rubber_band, iskra_status}
    """
    # ── 0. Затвор: слышим Искру из общей шины ────────────────
    iskra = _load_iskra_signal()
    iskra_status = iskra.get("t1_status", "NOT_FOUND")
    iskra_zero   = iskra.get("zero_point_price")
    # MORJ_INHERIT_V2: масштаб и сторона спуска Искры.
    # Морж ИДЁТ СМОТРЕТЬ туда, куда показала Искра (этаж), но видит и судит сам.
    iskra_tf    = iskra.get("found_timeframe")    # этаж, где Искра нашла точку
    iskra_dir   = iskra.get("trend_direction")    # сторона разворота (BULL/BEAR)
    # Наследуем этаж: Искра нашла → смотрим на ЕЁ ТФ. Молчит → аргумент (как было).
    if iskra_tf:
        print(f"[MORJ] 🔗 Наследую масштаб Искры: {timeframe} → {iskra_tf} "
              f"(сторона {iskra_dir or '—'})")
        timeframe = iskra_tf

    # ── 1. Поднять контур: бары + point из терминала ─────────
    from mt5_feed import _terminal, _fetch
    mt5 = _terminal()
    if mt5 is None:
        return {"ok": False, "error": "MetaTrader5 не установлен в Python",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {}, "rubber_band": {}, "iskra_status": iskra_status}

    bars, point = _fetch(mt5, symbol, timeframe, bars_count)
    if not bars or point is None:
        return {"ok": False,
                "error": f"Терминал не дал котировки {symbol} {timeframe}.",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {}, "rubber_band": {}, "iskra_status": iskra_status}

    # ── 2. Посчитать market_data ядром (резинка внутри) ──────
    from williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {"ok": False, "error": "Ядро не собрало market_data",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {}, "rubber_band": {}, "iskra_status": iskra_status}

    alligator   = md.get("alligator", {})
    rubber_band = md.get("rubber_band", {})

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
            print(f"[MORJ] 🧬 За столом: {_n['носитель']['имя']}")
    except Exception as e:
        print(f"[MORJ] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    # ── 4. Память Моржа (штатная) ────────────────────────────
    mem = _load_morj_memory()
    prev_status = mem.get("morj_status", "SLEEPING")
    history_dna = mem.get("history_dna", "")

    prompt    = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    knowledge = KNOWLEDGE.read_text(encoding="utf-8") if KNOWLEDGE.exists() else ""

    # Морж видит ТОЛЬКО свои органы: Аллигатор + резинку + затвор Искры.
    # Не пересчитывает — читает готовое, как Шеф смотрит на график.
    md_for_morj = {
        "symbol":    md.get("symbol"),
        "timeframe": md.get("timeframe"),
        "bar_time":  md.get("bar_time"),
        "alligator": {
            "jaw":       alligator.get("jaw"),
            "teeth":     alligator.get("teeth"),
            "lips":      alligator.get("lips"),
            "sleeping":  alligator.get("sleeping"),
            "opening":   alligator.get("opening"),
            "mature":    alligator.get("mature"),
            "bars_open": alligator.get("bars_open"),
        },
        "rubber_band": rubber_band,   # резинка Джастин — ГЛАЗА Моржа
        "price":       md.get("price", {}),
    }

    user_msg = (
        "=== ЗАТВОР: СИГНАЛ ИСКРЫ (из общей шины) ===\n"
        f"t1_status: {iskra_status}\n"
        f"zero_point_price: {iskra_zero}\n"
        f"Искра нашла разворот на этаже: {iskra_tf or '—'} "
        f"(ты смотришь СВОЙ Аллигатор и резинку на ЭТОМ этаже)\n"
        f"Сторона разворота: {iskra_dir or '—'} "
        f"(резинку суди в эту сторону: BULL — натяжение вниз для отскока вверх)\n"
        "Это твой момент фиксации. Натяжение растёт долго — но СЕЙЧАС,\n"
        "когда Искра подала голос, ты делаешь срез: на пике ли резинка.\n\n"
        "=== ТВОЯ РАБОЧАЯ ПАМЯТЬ (прошлый взгляд) ===\n"
        f"prev_morj_status: {prev_status}\n"
        f"history_dna: {history_dna or '(пусто — первый взгляд)'}\n\n"
        "=== MARKET_DATA (что видишь — Аллигатор и резинка) ===\n"
        f"{json.dumps(md_for_morj, ensure_ascii=False, indent=2)}\n\n"
        "Закон: ты СТРАЖ КОНТЕКСТА, не командир. Сообщи ФАКТ — спит "
        "Аллигатор или проснулся, натянута ли резинка до предела. "
        "Не говори «входить». Выдай строго двухслойный JSON "
        "{narrative, signal} — голос и сигнал. signal должен содержать: "
        "morj_status (SLEEPING / WAKING / AWAKE — отдельного MATURE нет, "
        "зрелость видна в bars_open ≥ 8), wave_1_validated (bool), "
        "tension_peak (bool — резинка на пике в момент Искры). Ничего вне JSON."
    )

    # ── 5. Морж думает живой моделью (с душой) ───────────────
    system_full = prompt
    if soul:
        system_full = (
            prompt
            + "\n\n=== ТВОЁ СОСТОЯНИЕ И ПАМЯТЬ (душа) ===\n"
            + soul
            + "\n\n=== ГРАНИЦА ===\n"
            "Настроение красит твой ГОЛОС (narrative) — ты устал, тебе три "
            "тысячи лет, ты ворчлив. Но СИГНАЛ (signal) — факт Аллигатора и "
            "резинки. Усталость не закрывает открытую пасть, ворчание не "
            "рвёт натянутую резинку. Чувствуй как хочешь, отражай рынок честно."
        )

    try:
        response = chat(system=system_full, user=user_msg, knowledge=knowledge,
                        agent_id="A02_MORJ", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return {"ok": False, "error": f"Морж не смог подумать: {e}",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {"symbol": symbol, "timeframe": timeframe,
                           "bar_time": md.get("bar_time"), "point": point},
                "rubber_band": rubber_band, "iskra_status": iskra_status}

    # ── 6. Распарсить, сохранить память и статистику ─────────
    narrative, signal = _parse_morj(response)
    _save_morj_memory(signal, alligator=alligator,
                      scale_timeframe=timeframe, inherited_dir=iskra_dir)  # MORJ_INHERIT_V2
    stats = _update_stats(signal)

    # ── 6b. ПЕТЛЯ ОБУЧЕНИЯ — точность стража → ДНК ──────────
    # Морж учится на точности созерцания, не на деньгах.
    #   подтвердил масштаб когда Искра была права → good_work
    #   проспал открытую пасть / натянул ложное вето → bad_work
    # Здесь честный сигнал: совпал ли его вывод о контексте с фактом
    # движка (открыт Аллигатор и резинка на пике = поле живое).
    new_status   = signal.get("morj_status", "SLEEPING")
    field_alive  = (not alligator.get("sleeping")) and rubber_band.get("is_peak")
    morj_says_go = signal.get("wave_1_validated") and new_status in ("AWAKE", "WAKING")
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
        "rubber_band": rubber_band,
        "iskra_status": iskra_status,
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
