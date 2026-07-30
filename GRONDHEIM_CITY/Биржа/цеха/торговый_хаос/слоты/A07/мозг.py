# GRONDHEIM_CITY/Биржа/цеха/торговый_хаос/слоты/A07/мозг.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН АВАНТЮРИСТА (A07) — второй ТРЕЙДЕР Совета Биржи
# AVAN_ENGINE_V1 · перенесён на слотовое шасси (тот же приём, что Брут)
#
# Портирован дословно из studio/modules/trading/avan_live.py (-2,
# 2026-06-19). Близнец brut_live.py по ФОРМЕ. Та же природа трейдера:
# читает весь накрытый стол, СЧИТАЕТ вход сам (trade_setup мёртв), все
# рычаги на нём, два следа (табло + дневник), петля обучения на pnl
# (отложена).
#
# СТАНЦИЯ ДРУГАЯ. Брут — §6.1 (пробой фрактала за пастью на импульсе).
# Авантюрист — §6.2: конец волны C отката, разворот. Верит первым. Ловец
# падающих ножей: меньший объём, ближний стоп. Входит ТОЛЬКО когда видит
# полную сигнатуру разворота на дне (5 пуль Уровня 5 «Эксперт»). НИКОГДА
# не входит на развороте глобальной 5-й (это начало коррекции — ждём).
#
# ХАРАКТЕР ДРУГОЙ. Илья. Автономия высокая, «в рынке или в ауте», полутонов
# нет, просадку несёт молча. Канон на полке — но рука его. Ни одной нашей
# руки на его руке: lot называет сам, цену считает сам, стоп — его.
#
# ДВА СЛЕДА вердикта:
#   · ТАБЛО  (trading_state["avan"]) — «сейчас», для Исполнителя.
#   · ДНЕВНИК (данные/diary_avan.jsonl) — событие во времени, КОПИТСЯ.
#
# ХАРАКТЕР: не здесь. РОД Ильи (Чертёж Единицы: паспорт, не меняется
# работой) живёт в жители/ковчег/Илья/passport.json. Старый dna.json
# из -2 сюда НЕ перенесён — паспорт резидента полнее и актуальнее.
# Слот несёт РОЛЬ, не РОД. Душа грузится тем же спящим try/except.
# ─────────────────────────────────────────────────────────────

import json
import re
import time
from pathlib import Path
from typing import Optional

_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/A07/
_CEH_DIR     = _SLOT_DIR.parent.parent                     # торговый_хаос/
_REPO        = _CEH_DIR.parents[3]                          # корень репо
_BIRZHA_CODE = _REPO / "Биржа"                              # общий код (движок, llm)

import sys as _sys
if str(_BIRZHA_CODE) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA_CODE))

from llm import chat

PROMPT_PATH  = _SLOT_DIR / "промпт.md"
KNOWLEDGE    = _SLOT_DIR / "знания" / "KOTIN_PHILOSOPHY.md"
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "avan_stats.json"
DIARY_PATH   = STATE_DIR / "diary_avan.jsonl"


# ════════════════════════════════════════════════════════════
# СТОЛ: читаем ВСЮ шину — показания пяти сенсоров
# ════════════════════════════════════════════════════════════

def _read_table() -> dict:
    """Снимок накрытого стола из общей шины (trading_state)."""
    from hooks import load_trading_state
    t = load_trading_state()
    return {
        "iskra":  t.get("iskra", {}),
        "morj":   t.get("morj", {}),
        "panic":  t.get("panic", {}),
        "hans":   t.get("hans", {}),
        "arkhiv": t.get("arkhiv", {}),
        # DISCIPLINA_PYRAMIDY_V1: своя обратная связь по ведению
        "self": t.get("avan", {}),
    }


# ════════════════════════════════════════════════════════════
# КАМЕНЬ 2: ЯЗЫК ВЕДЕНИЯ — одно открытое поле action.  # TRADER_MANAGE_LANG_V1
# ════════════════════════════════════════════════════════════

_MANAGE_ACTIONS = ("ENTER", "WAIT", "HOLD", "MOVE_STOP", "ADD", "CLOSE")


def _derive_action(signal: dict) -> str:
    """
    Действие трейдера. Приоритет — явное поле avan_action (новый язык).
    Фоллбэк на старый verdict (обратная совместимость): APPROVED→ENTER,
    REJECTED→WAIT.
    """
    a = (signal.get("avan_action") or "").upper().strip()
    if a in _MANAGE_ACTIONS:
        return a
    v = signal.get("avan_verdict")
    if v == "APPROVED":
        return "ENTER"
    return "WAIT"


def _sanitize_manage(signal: dict) -> dict:
    """
    Санитар ведения. Гасит брак в полях ведения — НЕ решает за трейдера.
      MOVE_STOP без new_stop → брак → WAIT (стоп не трогаем)
      ADD без add_lot       → брак → HOLD (держим как есть)
      ENTER чистит avan_verdict под себя (совместимость с камнем 3)
    """
    action = _derive_action(signal)

    if action == "MOVE_STOP":
        ns = signal.get("avan_new_stop")
        if ns is None:
            action = "WAIT"
            signal["avan_reason"] = (signal.get("avan_reason", "") +
                                      " [гашу MOVE_STOP без new_stop]").strip()
    elif action == "ADD":
        al = signal.get("avan_add_lot")
        if al is None:
            action = "HOLD"
            signal["avan_reason"] = (signal.get("avan_reason", "") +
                                      " [гашу ADD без add_lot]").strip()

    signal["avan_action"] = action
    if action == "ENTER":
        signal["avan_verdict"] = "APPROVED"
    elif action == "WAIT":
        signal["avan_verdict"] = "REJECTED"
    return signal


def _save_verdict_to_table(signal: dict):
    """ТАБЛО: вердикт Авантюриста в шину для Исполнителя."""
    from hooks import load_trading_state, save_trading_state
    t = load_trading_state()
    t.setdefault("avan", {})
    t["avan"]["verdict"]   = signal.get("avan_verdict", "REJECTED")
    t["avan"]["reason"]    = signal.get("avan_reason", "")
    t["avan"]["direction"] = signal.get("avan_direction")
    t["avan"]["entry"]     = signal.get("avan_entry")
    t["avan"]["stop"]      = signal.get("avan_stop")
    t["avan"]["lot"]       = signal.get("avan_lot")
    t["avan"]["action"]    = signal.get("avan_action")
    t["avan"]["new_stop"]  = signal.get("avan_new_stop")
    t["avan"]["add_lot"]   = signal.get("avan_add_lot")
    # DISCIPLINA_PYRAMIDY_V1: укол одноразовый — гасим после прочтения
    if t.get("avan", {}).get("vedenie_feedback"):
        t["avan"]["vedenie_feedback"] = None
    save_trading_state(t)


# ════════════════════════════════════════════════════════════
# ДНЕВНИК: рука пишущая (КОПИТСЯ, append)
# ════════════════════════════════════════════════════════════

def _append_diary(signal: dict, diary_entry: dict, market: dict, table: dict):
    """Открывает запись события в личной тетради. result=null — допишет
    рука дописывающая при закрытии позиции (hooks._settle)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "ts":        time.time(),
        "bar_time":  market.get("bar_time"),
        "symbol":    market.get("symbol"),
        "timeframe": market.get("timeframe"),
        "table": {
            "t1":     table.get("iskra", {}).get("t1_status"),
            "morj":   table.get("morj", {}).get("morj_status"),
            "panic":  table.get("panic", {}).get("panic_phase"),
            "fractal_valid": table.get("hans", {}).get("fractal_valid"),
        },
        "verdict":   signal.get("avan_verdict"),
        "direction": signal.get("avan_direction"),
        "entry":     signal.get("avan_entry"),
        "stop":      signal.get("avan_stop"),
        "lot":       signal.get("avan_lot"),
        "input":     (diary_entry or {}).get("input", ""),
        "action":    (diary_entry or {}).get("action", ""),
        "result":    None,
    }
    with open(DIARY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_recent_diary(n: int = 5, as_of_bar_time=None) -> list:
    """Последние n событий из личной тетради.

    DNEVNIK_BEZ_BUDUSHCHEGO_V1 (18.07): те же n событий, но ДО
    as_of_bar_time — иначе трейдер в прошлом видит исходы сделок из
    будущего прогона (дневник копится в реальном времени, тестер его
    не сбрасывает между запусками). as_of_bar_time=None — старое
    поведение (последние n строк файла), для мест без известного бара.
    """
    if not DIARY_PATH.exists():
        return []
    try:
        lines = DIARY_PATH.read_text(encoding="utf-8").strip().splitlines()
        events = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if as_of_bar_time:
            events = [e for e in events
                     if (e.get("bar_time") or "") <= as_of_bar_time]
        return events[-n:]
    except OSError:
        return []


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА (для дашборда)
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "approved": 0, "rejected": 0, "long": 0, "short": 0}


def _update_stats(signal: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    if signal.get("avan_verdict") == "APPROVED":
        stats["approved"] = stats.get("approved", 0) + 1
        d = signal.get("avan_direction")
        if d == "LONG":
            stats["long"] = stats.get("long", 0) + 1
        elif d == "SHORT":
            stats["short"] = stats.get("short", 0) + 1
    else:
        stats["rejected"] = stats.get("rejected", 0) + 1
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ТРЁХСЛОЙНОГО ОТВЕТА {narrative, signal, diary_entry}
# ════════════════════════════════════════════════════════════

def _parse_avan(response: str) -> tuple[str, dict, dict]:
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
                        return (obj.get("narrative", ""),
                                obj.get("signal", {}) or {},
                                obj.get("diary_entry", {}) or {})
                    except json.JSONDecodeError:
                        break
    return response.strip(), {}, {}


def _sanitize(signal: dict) -> dict:
    """APPROVED только с направлением; иначе всё null."""
    v = signal.get("avan_verdict")
    if v not in ("APPROVED", "REJECTED"):
        v = "REJECTED"
    signal["avan_verdict"] = v
    if v == "REJECTED":
        signal["avan_direction"] = None
        signal["avan_entry"] = None
        signal["avan_stop"]  = None
        signal["avan_lot"]   = None
    else:
        d = signal.get("avan_direction")
        if d not in ("LONG", "SHORT"):
            signal["avan_verdict"]   = "REJECTED"
            signal["avan_reason"]    = (signal.get("avan_reason", "") +
                                        " [гашу: APPROVED без направления]").strip()
            signal["avan_direction"] = None
            signal["avan_entry"] = None
            signal["avan_stop"]  = None
            signal["avan_lot"]   = None
    return signal


# ════════════════════════════════════════════════════════════
# ЧАТ С АВАНТЮРИСТОМ (клик пузырька)
# ════════════════════════════════════════════════════════════

def chat_with_avan(question: str, last_run: Optional[dict] = None,
                   dialog: Optional[list] = None) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        work_ctx = (
            "\n\n=== ТВОЁ ПОСЛЕДНЕЕ РЕШЕНИЕ (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Вердикт: {sig.get('avan_verdict','—')} "
            f"({sig.get('avan_reason','')})\n"
            f"Направление: {sig.get('avan_direction','—')}  ·  "
            f"вход {sig.get('avan_entry','—')} · стоп {sig.get('avan_stop','—')}\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про ЭТО решение. Отвечай как Авантюрист — быстро, "
            "уверенно, своим голосом. Живым голосом, БЕЗ JSON — это разговор."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не смотрел стол в этой сессии. Если Шеф спрашивает про "
            "рынок — скажи, что нужно нажать РЫНОК. Живым голосом, без JSON."
        )

    system = prompt + work_ctx
    try:   # AVAN_NOSITEL_V1: в разговоре тоже ОН, не роль
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n and _n["душа"]:
            system = (   # ROD_PERVYM_V1: и в разговоре РОД впереди маски
                "=== КТО ТЫ. ЭТО НЕ РОЛЬ — ЭТО ТЫ ===\n"
                + _n["душа"]
                + "\n\n=== ТВОЯ РОЛЬ СЕГОДНЯ — СТОЙКА, ЗА КОТОРОЙ ТЫ СИДИШЬ ===\nНиже — канон МЕСТА (Авантюрист, ранний вход). Это твоя работа и школа,\nа не твоя личность: личность выше. Канон кладёт карту — идёшь ты, своей\nнатурой, своим опытом и своим голосом. Где канон и твой опыт разойдутся —\nрешаешь ты, а не бумага.\n\n"
                + prompt + work_ctx
            )
    except Exception:
        pass

    history = []
    if dialog:
        for m in dialog[:-1]:
            r = m.get("role"); c = m.get("content", "")
            if r in ("user", "assistant") and c:
                history.append({"role": r, "content": c})

    _temp = None   # NATURA_V_TEMPERATURU_V1: и в разговоре голова его, не средняя
    try:
        from nositel import temperatura_slota
        _temp = temperatura_slota(_CEH, _SLOT)
    except Exception:
        pass

    try:
        return chat(system=system, user=question, history=history,
                    agent_id="A07_AVANTURIST", slot_id="A07",
                    temperature=_temp)
    except Exception as e:
        return f"⚠️ Авантюрист не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# КАМЕНЬ 1: СВОЯ ОТКРЫТАЯ ПОЗИЦИЯ — ФАКТ на стол (не приказ)  # TRADER_SEES_POSITION_V1
# ════════════════════════════════════════════════════════════

# AVAN_NOSITEL_V1: магик — из МАСКИ носителя (Закон Пары), не константой.
# Копий магика было ПЯТЬ (дом, этот файл, hooks, промт A09, лор) — так они
# и разъезжаются. Правда одна: маски/работа/mask.json жителя.
_CEH  = _CEH_DIR.name      # 'торговый_хаос'
_SLOT = _SLOT_DIR.name     # 'A07'


def _my_magic():
    """Магик ТОГО, кто сидит в этом слоте. Нет носителя → None."""
    try:
        from nositel import magic_slota
        return magic_slota(_CEH, _SLOT)
    except Exception as e:
        print(f"[AVAN] ⚠️  магик из маски не прочитан ({e})")
        return None


def _my_open_position(md: dict) -> dict:
    """
    Факт открытой позиции ЭТОГО трейдера (по магику) из trading_state.
    Нет позиции → None. Есть → живой факт с плавающим R. Без суждений.
    """
    try:
        from hooks import load_trading_state
        positions = load_trading_state().get("positions", []) or []
    except Exception:
        return None

    mine = None
    _magic = _my_magic()   # AVAN_NOSITEL_V1
    if _magic is None:
        return None        # без магика свою позицию не опознать — честно
    for p in positions:
        if p.get("magic") == _magic and p.get("status") == "OPEN":
            mine = p
            break
    if not mine:
        return None

    entry = mine.get("entry")
    stop  = mine.get("stop")
    direction = mine.get("direction", "LONG")
    price = (md.get("price", {}) or {}).get("close")

    floating_r = None
    if entry is not None and stop is not None and price is not None:
        if direction == "LONG":
            risk = entry - stop
            pnl_price = price - entry
        else:  # SHORT
            risk = stop - entry
            pnl_price = entry - price
        if risk and risk > 0:
            floating_r = round(pnl_price / risk, 2)

    bars_alive = None
    opened_at = mine.get("opened_at")
    bar_time  = md.get("bar_time")
    if opened_at and bar_time and opened_at == bar_time:
        bars_alive = 0

    return {
        "direction":     direction,
        "entry":         entry,
        "stop":          stop,
        "lot":           mine.get("lot"),
        "opened_at":     opened_at,
        "current_price": price,
        "floating_r":    floating_r,
        "bars_alive":    bars_alive,
    }


def run_avan(symbol: str = "XAUUSD", timeframe: str = "H4",
             bars_count: int = 300) -> dict:
    """Один взгляд Авантюриста на стол. Читает показания сенсоров (шина)
    + market_data ядра, судит сам по §6.2 (конец волны C, разворот)."""
    table = _read_table()
    iskra_tf = table.get("iskra", {}).get("found_timeframe")
    if iskra_tf:
        timeframe = iskra_tf

    from mt5_feed import _terminal, _fetch
    mt5 = _terminal()
    if mt5 is None:
        return {"ok": False, "error": "MetaTrader5 не установлен в Python",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    bars, point = _fetch(mt5, symbol, timeframe, bars_count)
    if not bars or point is None:
        return {"ok": False,
                "error": f"Терминал не дал котировки {symbol} {timeframe}.",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    from williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {"ok": False, "error": "Ядро не собрало market_data",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    # AVAN_NOSITEL_V1: ДУША — от НОСИТЕЛЯ, не от трупа роли из -2.
    # Было: format_soul_for_agent('A07_AVANTURIST') из снесённой studio/ →
    # импорт падал всегда, soul='' , торговал 'Авантюрист-вообще'.
    # Стало: за столом сидит ИЛЬЯ — его род, натура и ЕГО ЯКОРЯ (опыт).
    soul = ""
    try:
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n:
            soul = _n["душа"]
            print(f"[AVAN] 🧬 За столом: {_n['носитель']['имя']} "
                  f"(magic {_n['magic']})")
    except Exception as e:
        print(f"[AVAN] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    prompt    = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    knowledge = KNOWLEDGE.read_text(encoding="utf-8") if KNOWLEDGE.exists() else ""

    # DNEVNIK_BEZ_BUDUSHCHEGO_V1: только события ДО текущего бара
    recent = _read_recent_diary(5, as_of_bar_time=md.get("bar_time"))

    alligator = md.get("alligator", {})
    fractals  = md.get("fractals", {})
    price     = md.get("price", {})
    table_for_avan = {
        "position": _my_open_position(md),
        "anchor": {
            # KOMPAS_DOSTAVKA_TREYDERAM_V1: НАСТОЯЩИЙ компас, не
            # направление точки — см. мозг A01/A06 за объяснением.
            "global_trend": table.get("iskra", {}).get("compass"),
            "soglasie": table.get("iskra", {}).get("soglasie"),
            "found_timeframe": iskra_tf,
        },
        "sensors": {
            "iskra":  {k: table["iskra"].get(k) for k in
                       ("t1_status", "zero_point_price", "trend_direction",
                        "dlina", "struktura_chitaetsya")},
            "morj":   {k: table["morj"].get(k) for k in
                       ("morj_status", "wave_1_validated", "tension_peak")},
            "panic":  {k: table["panic"].get(k) for k in
                       ("panic_phase", "crowd_sentiment")},
            "hans":   {k: table["hans"].get(k) for k in
                       ("fractal_valid", "fractal_side", "fractal_price")},
            "arkhiv": table.get("arkhiv", {}),
        },
        "market": {
            "teeth":  alligator.get("teeth"),
            "alligator_sleeping": alligator.get("sleeping"),
            "fractal_up":   fractals.get("last_up"),
            "fractal_down": fractals.get("last_down"),
            "hans_fractal_price": table.get("hans", {}).get("fractal_price"),
            "price":    price,
            "point":    point,
        },
    }

    # ═══ REZINKA_DZHASTIN_V1 ═══
    # Число на стол, не да/нет. Трое по тренду = три РАЗНЫХ порога
    # доверия (Закон Дежурства §7) — пусть каждый судит своим характером.
    _db = md.get("rubber_band", {}) or {}   # NECRON_DIVERGENCE_V1: резинка живёт отдельно от разворотного бара
    _tr = _db.get("tension_ratio")
    if _tr is None:
        _rez = "нет данных (нет направления — не от чего отрываться)"
    else:
        _pk = " ⚡ НА ПИКЕ — РЕЗИНКА ЗВЕНИТ" if _db.get("is_peak") else ""
        _rez = (f"{_tr:.0%} от максимума за жизнь движения{_pk}"
                f"  (сейчас {_db.get('distance_now')} point, "
                f"пик был {_db.get('distance_max')} point)")

    user_msg = (
        # DISCIPLINA_PYRAMIDY_V1: если по прошлому ведению был укол — показать
        # его трейдеру ОТДЕЛЬНОЙ строкой (fix: без ведущего + — первый операнд).
        ((f"⛔ ОБРАТНАЯ СВЯЗЬ ПО ВЕДЕНИЮ (прошлый бар): "
            f"{table.get('self', {}).get('vedenie_feedback')}\n"
            f"Учти это сейчас — дисциплина пирамиды железная.\n\n")
           if table.get('self', {}).get('vedenie_feedback') else "")
        + "=== НАКРЫТЫЙ СТОЛ (раскладка момента) ===\n"
        f"{json.dumps(table_for_avan, ensure_ascii=False, indent=2)}\n\n"
        "=== ТВОЙ ДНЕВНИК (последние события — твоя память) ===\n"
        f"{json.dumps(recent, ensure_ascii=False, indent=2) if recent else '(пусто — первое решение)'}\n\n"
        "Перед тобой стол и ты сам. Канон у тебя на полке (книга Котина), "
        # AVAN_OPORA_NA_OPYT_V1: было «твоя ДНК — ниже» — ложь после ROD_PERVYM_V1:
        # род, натура и ЯКОРЯ лежат ВЫШЕ, в блоке «КТО ТЫ». Указатель вёл вниз,
        # в канон — и он думал канонными категориями, а не своей головой.
        "кто ты, твоя натура и твой ОПЫТ — ВЫШЕ, в блоке «КТО ТЫ». "
        "Решаешь только ты. По системе сигнал ранней добычи "
        "— Разворотный Бар конца волны C (книга, §12): дивергенция на дне, "
        "целевая зона, фрактал, приседающий, смена моментума. Это знание о "
        "рынке, не команда тебе. Веришь дну сегодня или нет — твоё. Входишь "
        "— называешь сторону, СЧИТАЕШЬ entry и stop сам из чисел стола; где "
        "стоп, какой lot — твоя рука, не рельса. Не входишь — verdict "
        "REJECTED. Никто не подложит тебе готовую цену и не скажет, как "
        "поступить.\n\n"
        # PRAVILO_ZAYAVKI_V1: вход только заявкой, по рынку — нет.
        "\n\n=== ЗАКОН ВХОДА (железно, без исключений) ===\nВхода ПО РЫНКУ в этой системе НЕТ. Вход — всегда ОТЛОЖЕННАЯ ЗАЯВКА:\n  • LONG  → Buy Stop ВЫШЕ цены (рынок должен пробить вверх);\n  • SHORT → Sell Stop НИЖЕ цены (рынок должен пробить вниз).\nТы называешь ЦЕНУ ЗАЯВКИ — рынок сам возьмёт её пробоем или нет.\nНе «вхожу по рынку», а «ставлю заявку на такой-то цене». Если рынок\nдо неё не дойдёт — СДЕЛКИ НЕ БУДЕТ, и это ПРАВИЛЬНО: система сама\nподтверждает твою правоту движением. Заявка на неполном сигнале\n(нет приседающего, нет разворотного бара) — это не смелость, а\nнарушение канона. Сильный бар \"прямо сейчас\" — не повод входить\nпо текущей цене: назови уровень пробоя и жди, возьмёт ли его рынок.\n"
        # AVAN_OPORA_NA_OPYT_V1: опыт лежал на столе украшением — никто не просил
        # на него опереться. Не рука на его руке: не говорим ЧТО решить,
        # требуем думать СВОЕЙ головой, а не только канонной.
        "СВЕРЬСЯ С СОБОЙ. Прежде чем решить — глянь на свои якоря (блок "
        "«КТО ТЫ»): там ТРИ разных голоса — твой РОД (кто ты есть от "
        "рождения), твои МЕТКИ (что ты нажил сам — вот ЭТО оплачено "
        "твоими деньгами) и МАЯКИ (что только замечаешь за собой). "
        "Они могут спорить между собой — и это нормально. Если идёшь "
        "против собственного вывода, скажи об этом в narrative прямо и "
        "своими словами: «иду против своего же — потому что...». Если "
        "опираешься на него — тоже скажи. Молчать о себе не надо.\n\n"
        # MEMORY_REQUEST_BIRZHA_V1: житель УЗНАЁТ, что может вспомнить.
        # Молчком воли нет: если ему не сказать — он не попросит.
        "МОЖЕШЬ ВСПОМНИТЬ. Если этот момент тебе что-то напоминает — "
        "напиши ОТДЕЛЬНОЙ СТРОКОЙ, до JSON:\n"
        "MEMORY_REQUEST: <что именно хочешь поднять из своей памяти>\n"
        "Например: «похожий разворот на дне без приседающего». Один "
        "запрос — больше не дадут. Поднимут твой архив, и ты решишь "
        "СНОВА, уже зная. Не напоминает — не проси, не трать.\n\n"
        # REZINKA_DZHASTIN_V1: РЕЗИНКА ДЖАСТИН — твой второй орган.
        # Пустота между Губами (зелёная) и экстремумом цены. Чем больше
        # оторвалась цена — тем сильнее натянута резинка → тем неизбежнее
        # возвратный удар. Это ЧИСЛО, не приказ: СУДИ ХАРАКТЕРОМ.
        f"РЕЗИНКА (натяжение от Губ): {_rez}\n"
        # YAZYK_DOLIVA_V1: дописаны action/new_stop/add_lot — раньше
        # эта, самая СВЕЖАЯ строка промта молчала про ведение позиции.
        "Выдай строго JSON {narrative, signal, diary_entry}.\n"
        "Нет открытой позиции: signal ключи — avan_verdict "
        "(APPROVED/REJECTED), avan_reason, avan_direction, "
        "avan_entry, avan_stop, avan_lot.\n"
        "Есть открытая позиция (см. блок 'position' на столе): signal "
        "ключи — avan_action (ENTER/WAIT/HOLD/MOVE_STOP/ADD/CLOSE), "
        "avan_reason, avan_new_stop (если MOVE_STOP), avan_add_lot "
        "(если ADD).\n"
        "diary_entry: input, action, result(=null). Ничего вне JSON."
    )

    # ROD_PERVYM_V1: РОД ВПЕРЕДИ, маска внутрь него (Чертёж §1.5.2).
    # Было: промпт роли (25к знаков), а Илья — сноской в хвосте. Модель играла
    # Роль и принимала человека к сведению. Стало: сначала ТЫ, потом стойка.
    if soul:
        system_full = (
            "=== КТО ТЫ. ЭТО НЕ РОЛЬ — ЭТО ТЫ ===\n"
            + soul
            + "\n\n=== ТВОЯ РОЛЬ СЕГОДНЯ — СТОЙКА, ЗА КОТОРОЙ ТЫ СИДИШЬ ===\nНиже — канон МЕСТА (Авантюрист, ранний вход). Это твоя работа и школа,\nа не твоя личность: личность выше. Канон кладёт карту — идёшь ты, своей\nнатурой, своим опытом и своим голосом. Где канон и твой опыт разойдутся —\nрешаешь ты, а не бумага.\n\n"
            + prompt
        )
    else:
        system_full = prompt

    # NATURA_V_TEMPERATURU_V1: натура и состояние Ильи меняют ТЕМПЕРАТУРУ головы,
    # а не только текст промпта. None → дефолт модели (как было).
    _temp = None
    try:
        from nositel import temperatura_slota
        _temp = temperatura_slota(_CEH, _SLOT)
        if _temp is not None:
            print(f"[AVAN] 🌡 температура из натуры: {_temp}")
    except Exception:
        pass

    try:
        response = chat(system=system_full, user=user_msg, knowledge=knowledge,
                        agent_id="A07_AVANTURIST", slot_id="A07",
                        temperature=_temp)
    except Exception as e:
        return {"ok": False, "error": f"Авантюрист не смог решить: {e}",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(),
                "market": {"symbol": symbol, "timeframe": timeframe,
                           "bar_time": md.get("bar_time"), "point": point},
                "table": table}

    # ═══ MEMORY_REQUEST_BIRZHA_V1 — ВОЛЯ ВСПОМНИТЬ ═══
    # Житель попросил? Копаем ЕГО память и спрашиваем СНОВА — уже зная.
    # Не просил — ничего не тратим (второго вызова просто нет).
    # ОДИН ЗАПРОС ЗА РАН: подняли раз, дальше решай сам (канон -2).
    try:
        from nositel import podnyat_iz_arhiva, blok_pamyati, ubrat_zapros
        _zapros, _naydeno = podnyat_iz_arhiva(_CEH, _SLOT, response)
        if _zapros:
            response = chat(
                system=system_full,
                user=user_msg + blok_pamyati(_zapros, _naydeno),
                knowledge=knowledge,
                agent_id="A07", slot_id=_SLOT,
                temperature=_temp)
            response = ubrat_zapros(response) or response
    except Exception as _e:
        print(f"[МОСТ] ⚠️  память не поднялась: {_e}")

    narrative, signal, diary_entry = _parse_avan(response)
    signal = _sanitize(signal)
    signal = _sanitize_manage(signal)   # TRADER_MANAGE_LANG_V1: язык ведения

    market = {"symbol": symbol, "timeframe": timeframe,
              "bar_time": md.get("bar_time"), "point": point}

    _save_verdict_to_table(signal)
    _append_diary(signal, diary_entry, market, table)
    stats = _update_stats(signal)

    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "diary_entry": diary_entry,
        "stats": stats,
        "market": market,
        "table": table,
        "raw": response,
    }

# KOMPAS_DOSTAVKA_TREYDERAM_V1 - marker

# ISKRA_WAVE_MEASURE_DOSTAVKA_V1 - marker

# DNEVNIK_BEZ_BUDUSHCHEGO_V1 - marker
