# GRONDHEIM_CITY/Биржа/цеха/контора/слоты/исполнитель/мозг.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ИСПОЛНИТЕЛЬ — Казначей Биржи (штаб конторы), замыкает петлю
# EXECUTOR_ENGINE_V1 · перенесён на слотовое шасси 09.07 (KONTORA_SLOT_V1)
#
# Портирован дословно из studio/modules/trading/executor_live.py (-2,
# 2026-06-19). Не сенсор (кладёт факт), не трейдер (решает).
# Исполнитель ИСПОЛНЯЕТ и ВЕДЁТ ЛЕТОПИСЬ. «Цель вижу. Исполняю.» —
# не судит рынок.
#
# ДВЕ РУКИ РАЗНОЙ ПРИРОДЫ:
#   1. РУКА ОТКРЫВАЮЩАЯ (КОД, до LLM). Читает табло троих трейдеров.
#      Для каждого APPROVED кладёт позицию в trading_state["positions"]
#      ПО ФАКТУ ТАБЛО (direction/entry/stop/lot от трейдера) — не из
#      слов LLM. Деньги не место для галлюцинаций (защита чисел, как у
#      Архивариуса). PAPER-режим. Дисциплина: не дублирует уже открытый
#      magic. Закрытие — НЕ его дело, hooks._settle_positions делает само.
#   2. РУКА-ЛЕТОПИСЕЦ (LLM, его голос). Получает табло + бар, пишет
#      execution_log (его подпись), history_dna (одна строка правды),
#      task_score (честная оценка ДИСЦИПЛИНЫ цеха, не прибыли рынка).
#
# ЗАЩИТА ЧИСЕЛ: позиции в state кладёт КОД из табло. execution_log от
# LLM — летопись, может содержать его взгляд, но на физику не влияет.
#
# ПЕТЛЯ: sensors → traders (табло) → ИСПОЛНИТЕЛЬ (позиции открыты) →
# следующий бар: hooks._settle_positions закрывает по стопу/exit_bell →
# PnL в R. Круг цел.
#
# КОНТОРА, НЕ ЦЕХ (§3 БИРЖА.md, решение 09.07): Исполнитель — служба,
# общая на всю Биржу («хирург, никаких лишних движений» — одинаков
# в любой школе), а не слот одного цеха.
#
# ХАРАКТЕР: не здесь. РОД Сергея (Чертёж Единицы: паспорт, не меняется
# работой) живёт в жители/ковчег/Сергей/passport.json — там же и его
# DNA_Static (Autonomy 0.0, Empathy 0.05 и т.д.). Старый dna.json из -2
# сюда НЕ перенесён — паспорт резидента (создан 07.07) уже несёт то же
# самое и полнее. Слот несёт РОЛЬ (промпт+знания+данные), не РОД. Раньше
# dna.json подмешивался прямо в system-промпт мозга — теперь этот путь
# закрыт: душа приходит одним и тем же способом, что у всех остальных
# слотов (format_soul_for_agent, пока спит — см. заглушку ниже).
# ─────────────────────────────────────────────────────────────

import json
import re
import time
from pathlib import Path
from typing import Optional

# ЗАКОН КАРТРИДЖА ДЛЯ КОДА: файл живёт ПРЯМО В СЛОТЕ, рядом со своим
# промптом. Слот несёт с собой всё: слоты/исполнитель/{мозг.py,
# промпт.md, знания/, данные/}.
_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/исполнитель/
_CEH_DIR     = _SLOT_DIR.parent.parent                     # контора/
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
# ISKRA_FAIR_JUDGEMENT_V1 · позиция помнит точку Искры для суда при закрытии
# EXECUTOR_TRUTH_V1 · ордер считается по action==ENTER, не по verdict==APPROVED

PROMPT_PATH  = _SLOT_DIR / "промпт.md"
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "executor_stats.json"
LOG_PATH     = STATE_DIR / "executor_log.jsonl"   # летопись (КОПИТСЯ)

# Магия — паспорта трейдеров (из промта A09, копируется точно)
MAGIC = {"brut": 100001, "avan": 100002, "cons": 100003}
TRADER_NAME = {"brut": "BRUT", "avan": "AVANTURIST", "cons": "KONSERVATOR"}


# ── EXECUTOR_TRUTH_V1: единый критерий «реальный вход» ──
# Камень 2 даёт action: ENTER/HOLD/MOVE_STOP/ADD/CLOSE. Ордер
# отправлен ТОЛЬКО при ENTER. Ведение (MOVE_STOP/ADD/CLOSE/HOLD)
# не ордер. Фоллбэк для старых ответов без action: APPROVED с
# непустыми entry/stop (то есть настоящий вход, а не ведение).
def _is_real_entry(v: dict) -> bool:
    action = (v.get("action") or "").upper().strip()
    if action:
        return action == "ENTER"
    return (v.get("verdict") == "APPROVED"
            and v.get("entry") is not None
            and v.get("stop") is not None
            and v.get("direction") in ("LONG", "SHORT"))


# ════════════════════════════════════════════════════════════
# ТАБЛО: снимок вердиктов троих трейдеров из шины
# ════════════════════════════════════════════════════════════

def _read_traders() -> dict:
    """Вердикты троих из общей шины (trading_state). Факт, не слова LLM."""
    from hooks import load_trading_state
    t = load_trading_state()
    return {
        "brut": t.get("brut", {}),
        "avan": t.get("avan", {}),
        "cons": t.get("cons", {}),
    }


# ════════════════════════════════════════════════════════════
# РУКА ВЕДУЩАЯ (КОД) — исполняет ВЕДЕНИЕ по действию трейдера.  # EXECUTOR_MANAGE_HAND_V1
# ─────────────────────────────────────────────────────────────
# Трейдер назвал action (камень 2): HOLD/MOVE_STOP/ADD/CLOSE.
# Рука находит ЕГО открытую позицию по магику и исполняет буквально.
# Защита чисел: уровни/объёмы — подпись трейдера, не пересказ LLM.
# CLOSE не считает PnL — ставит флаг, _settle закроет единой физикой.
# ════════════════════════════════════════════════════════════

# EXECUTOR_PYRAMID_STOP_DISCIPLINE_V1
def _stop_tightens(direction: str, old_stop, new_stop) -> bool:
    """
    Трейлинг-стоп (первоисточник Уильямса) — только в защитную сторону.
    LONG: новый стоп не ниже старого. SHORT: новый стоп не выше старого.
    Старого стопа нет (первое выставление) — пропускаем как валидное.
    """
    if old_stop is None or new_stop is None:
        return True
    if (direction or "").upper() == "LONG":
        return new_stop >= old_stop
    return new_stop <= old_stop  # SHORT


def _manage_positions_from_table(traders: dict) -> list:
    """
    Для каждого трейдера с открытой позицией исполняет его действие
    ведения над trading_state["positions"]. Возвращает список изменений
    (для летописи). Открытие (ENTER) — не здесь, это рука открывающая.

    EXECUTOR_PYRAMID_STOP_DISCIPLINE_V1: стоп двигается только по канону трейлинга
    (никогда не ослабляется), долив идёт формой реверсивной пирамиды
    (со второго — не крупнее предыдущего), долив со стопом в одном
    ходу подтягивает и то, и другое разом.
    """
    from hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    positions = tstate.get("positions", []) or []
    if not positions:
        return []

    changed = []
    dirty = False
    for key in ("brut", "avan", "cons"):
        v = traders.get(key, {})
        action = (v.get("action") or "").upper().strip()
        if action in ("", "ENTER", "WAIT", "HOLD"):
            continue
        magic = MAGIC[key]
        pos = next((p for p in positions
                    if p.get("magic") == magic and p.get("status") == "OPEN"), None)
        if not pos:
            continue

        if action == "MOVE_STOP":
            ns = v.get("new_stop")
            if ns is None:
                continue
            old = pos.get("stop")
            if not _stop_tightens(pos.get("direction"), old, ns):
                changed.append({"trader": TRADER_NAME[key], "action": "MOVE_STOP_REJECTED",
                                "from": old, "attempted": ns,
                                "why": "ослабляет стоп — против канона трейлинга"})
                continue
            pos["stop"] = ns
            dirty = True
            changed.append({"trader": TRADER_NAME[key], "action": "MOVE_STOP",
                            "from": old, "to": ns})

        elif action == "ADD":
            al = v.get("add_lot")
            if al is None or al <= 0:
                continue
            prior_pyramids = pos.get("pyramids", 0)
            last_add = pos.get("last_add_lot")
            if prior_pyramids >= 1 and last_add is not None and al > last_add:
                changed.append({"trader": TRADER_NAME[key], "action": "ADD_REJECTED",
                                "attempted": al, "last_add_lot": last_add,
                                "why": "долив крупнее предыдущего — против формы "
                                       "реверсивной пирамиды (Уильямс)"})
                continue
            old_lot = pos.get("lot") or 0
            pos["lot"] = round(old_lot + al, 4)
            pos["pyramids"] = prior_pyramids + 1
            pos["last_add_lot"] = al
            dirty = True
            add_change = {"trader": TRADER_NAME[key], "action": "ADD",
                          "add_lot": al, "lot_now": pos["lot"]}
            # золотое правило пирамидинга: долив без подтяжки стопа не
            # бывает — если трейдер тем же ходом назвал new_stop, тянем
            # его сюда же, той же проверкой монотонности.
            ns = v.get("new_stop")
            if ns is not None:
                old_stop = pos.get("stop")
                if _stop_tightens(pos.get("direction"), old_stop, ns):
                    pos["stop"] = ns
                    add_change["stop_from"] = old_stop
                    add_change["stop_to"] = ns
                else:
                    add_change["stop_move_rejected"] = ns
            changed.append(add_change)

        elif action == "CLOSE":
            pos["manual_close"] = True
            dirty = True
            changed.append({"trader": TRADER_NAME[key], "action": "CLOSE"})

    if dirty:
        tstate["positions"] = positions
        save_trading_state(tstate)
    return changed


# ── ISKRA_FAIR_JUDGEMENT_V1: точка Искры для суда при закрытии ──
def _iskra_zero_for_judgement():
    """Точка Ноль Искры из шины — позиция уносит её с собой,
    чтобы _settle при закрытии рассудил Искру по делу (pnl_r).
    Нет точки → None (старый путь, суда не будет)."""
    try:
        from hooks import load_trading_state
        isk = load_trading_state().get("iskra", {}) or {}
        return isk.get("zero_point_price")
    except Exception:
        return None


def _snyat_stol_vhoda() -> dict:
    """SLEPOK_ISPOLNITELYA_V1 — СЛЕПОК СТОЛА на баре ВХОДА.

    Позиция уносит с собой показания всех четырёх сенсоров — те, что
    они дали ИМЕННО НА ЭТОМ БАРЕ. Стол перетирается каждый бар, а
    сделка живёт десятки баров: судить Моржа по чужому бару — клевета.

    Исполнитель ходит ПОСЛЕДНИМ (после сенсоров и трейдеров), значит
    в tstate сейчас лежат показания этого самого бара. Свежие.

    Формат — байт в байт как ждёт судья (hooks._sudit_sensorov):
    он читает pos["стол_входа"][key], где key ∈ iskra/morj/panic/hans.
    Пустой слепок = судья молча выходит и ЧЕРНОВИК НЕ РОЖДАЕТСЯ.
    """
    try:
        from hooks import load_trading_state
        t = load_trading_state()
    except Exception as e:
        print(f"[СЛЕПОК] ⚠️  не снял стол: {e}")
        return {}

    isk = t.get("iskra", {}) or {}
    mrj = t.get("morj",  {}) or {}
    pnk = t.get("panic", {}) or {}
    hns = t.get("hans",  {}) or {}

    # компас: без него не понять, звала ли Вера В СТОРОНУ сделки —
    # BULL зовёт в LONG, но НЕ зовёт в SHORT
    kompas = (isk.get("trend_direction")
              or mrj.get("inherited_dir")
              or isk.get("global_bias"))

    stol = {
        "iskra": {
            "t1_status":        isk.get("t1_status"),
            "zero_point_price": isk.get("zero_point_price"),
            "trend_direction":  kompas,
        },
        "morj": {
            "morj_status":      mrj.get("morj_status"),
            "wave_1_validated": mrj.get("wave_1_validated"),
            "tension_peak":     mrj.get("tension_peak"),
        },
        "panic": {
            "panic_phase":      pnk.get("panic_phase"),
        },
        "hans": {
            "fractal_valid":    hns.get("fractal_valid"),
            "fractal_side":     hns.get("fractal_side"),
            "fractal_price":    hns.get("fractal_price"),
        },
    }
    print(f"[СЛЕПОК] 📸 стол снят: искра={stol['iskra']['t1_status']} "
          f"морж={stol['morj']['morj_status']} "
          f"паник={stol['panic']['panic_phase']} "
          f"ганс={stol['hans']['fractal_valid']} компас={kompas}")
    return stol


def _open_positions_from_table(traders: dict, market: dict) -> list:
    """
    Для каждого APPROVED-трейдера кладёт позицию в trading_state["positions"]
    ПО ФАКТУ ТАБЛО. Возвращает список открытых в этот ход (для летописи).

    Защита чисел: direction/entry/stop/lot берём из табло трейдера —
    это его подпись, не пересказ LLM. Дисциплина: не открываем дубль
    того же magic, если он уже висит открытым.
    """
    from hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    tstate.setdefault("positions", [])
    open_magics = {p.get("magic") for p in tstate["positions"]
                   if p.get("status") == "OPEN"}

    bar_time = market.get("bar_time", "")
    opened = []
    for key in ("brut", "avan", "cons"):
        v = traders.get(key, {})
        if not _is_real_entry(v):
            continue
        magic = MAGIC[key]
        if magic in open_magics:
            continue
        direction = v.get("direction")
        entry     = v.get("entry")
        stop      = v.get("stop")
        if direction not in ("LONG", "SHORT") or entry is None or stop is None:
            continue
        # ═══ OTLOZHENNY_ORDER_V1 ═══
        # Трейдер сказал «Buy Stop 1248.22» — это ЗАЯВКА НА ПРОБОЙ,
        # а не сделка. Раньше код открывал МГНОВЕННО по названной
        # цене — даже если рынок туда НИКОГДА не дошёл. Половина
        # сделок была ФАНТОМАМИ (67% стопов ровно по −1.0R: вошли
        # «на пробое», которого не было → цена сразу против).
        #
        # Теперь: PENDING. Ждёт, пока рынок сам возьмёт (канон гл.8:
        # «Buy Stop на 1 тик выше high фрактального бара»).
        #
        # ⚠ Рыночный вход (цена ≈ текущая) активируется тем же
        # механизмом на ЭТОМ ЖЕ баре: high/low его накроют.
        # Отложка не мешает войти по рынку — она мешает войти
        # ТУДА, КУДА РЫНОК НЕ ХОДИЛ.
        pos = {
            "trader":    TRADER_NAME[key],
            "magic":     magic,
            "direction": direction,
            "entry":     entry,
            "stop":      stop,
            "tp":        None,
            "lot":       v.get("lot"),
            "status":    "PENDING",   # OTLOZHENNY_ORDER_V1
            "_ждёт_с":   bar_time,
            "_ждёт_баров": 0,
            "mode":      "PAPER",
            "opened_at": bar_time,
            "pnl":       None,
            "iskra_zero_point": _iskra_zero_for_judgement(),
            # SLEPOK_ISPOLNITELYA_V1: позиция уносит С СОБОЙ показания
            # сенсоров на баре ВХОДА. Без этого судья сенсоров молча
            # выходит на КАЖДОЙ сделке → черновик не рождается →
            # МЕТКА НЕ РОДИТСЯ НИКОГДА. Это был последний перекрытый
            # кран: труба построена, вода шла, а на выходе — ничего.
            "стол_входа": _snyat_stol_vhoda(),
        }
        tstate["positions"].append(pos)
        opened.append(pos)   # OTLOZHENNY_ORDER_V1: это ЗАЯВКА

    if opened:
        save_trading_state(tstate)
    return opened


# ════════════════════════════════════════════════════════════
# ЛЕТОПИСЬ (КОПИТСЯ, append) — рука пишущая history_dna
# ════════════════════════════════════════════════════════════

def _append_log(signal: dict, market: dict, opened: list):
    """Открывает запись Совета в летописи Исполнителя (КОПИТСЯ)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "ts":          time.time(),
        "bar_time":    market.get("bar_time"),
        "symbol":      market.get("symbol"),
        "timeframe":   market.get("timeframe"),
        "execution_log": signal.get("execution_log", []),
        "final_dna":   signal.get("final_dna", {}),
        "history_dna": signal.get("history_dna", ""),
        "opened_now":  [{"trader": p["trader"], "direction": p["direction"],
                         "entry": p["entry"], "stop": p["stop"]} for p in opened],
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА (для дашборда)
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "orders_sent": 0, "orders_skip": 0}


def _update_stats(opened: list, traders: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    approved = sum(1 for k in ("brut", "avan", "cons")
                   if _is_real_entry(traders.get(k, {})))
    stats["orders_sent"] = stats.get("orders_sent", 0) + len(opened)
    stats["orders_skip"] = stats.get("orders_skip", 0) + (3 - approved)
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ДВУХСЛОЙНОГО ОТВЕТА {narrative, signal}
# ════════════════════════════════════════════════════════════

def _parse_executor(response: str) -> tuple[str, dict]:
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
                                obj.get("signal", {}) or {})
                    except json.JSONDecodeError:
                        break
    return response.strip(), {}


def _build_execution_log_facts(traders: dict) -> list:
    """
    КОД собирает правдивый execution_log из ТАБЛО — эталон, по которому
    сверяется летопись LLM (защита чисел). Это факт, не пересказ.
    """
    log = []
    for key in ("brut", "avan", "cons"):
        v = traders.get(key, {})
        approved = _is_real_entry(v)
        # VASILY_ISP_WATCH_V1: засада Консерватора — своя природа.
        # WATCH не APPROVED и не REJECTED: трейдер назвал координаты и
        # ждёт созревания структуры. Доносим action + опору, чтобы
        # приёмник (hooks._persist_trading_state) родил WATCHING.
        _action = (v.get("action") or "").upper().strip()
        _is_watch = (_action == "WATCH")
        log.append({
            "trader":  TRADER_NAME[key],
            "magic":   MAGIC[key],
            "action":  _action or None,
            "verdict": "APPROVED" if approved else "REJECTED",
            "direction": (v.get("direction")
                          if (approved or _is_watch) else None),
            "entry":   (v.get("entry") if (approved or _is_watch) else None),
            "stop":    (v.get("stop") if (approved or _is_watch) else None),
            "lot":     (v.get("lot") if (approved or _is_watch) else None),
            # координата засады — только у Васи, только при WATCH
            "watch_opora": (v.get("watch_opora") if _is_watch else None),
            "status":  "PAPER" if (approved or _is_watch) else "SKIPPED",
            "pnl":     None,
        })
    return log


def _sanitize(signal: dict, traders: dict) -> dict:
    """
    ЗАЩИТА ЧИСЕЛ: execution_log в signal перетираем фактами из табло —
    Исполнитель «исполняет буквально», его смертный грех врать в числах.
    Код-факт всегда побеждает слова LLM. history_dna/task_score —
    оставляем его (это его суждение о дисциплине, не числа).
    """
    facts = _build_execution_log_facts(traders)
    signal["execution_log"] = facts
    sent = sum(1 for o in facts if o["verdict"] == "APPROVED")
    fd = signal.get("final_dna", {}) or {}
    fd["orders_sent"] = sent
    fd["orders_skip"] = 3 - sent
    signal["final_dna"] = fd
    return signal


# ════════════════════════════════════════════════════════════
# ЧАТ С ИСПОЛНИТЕЛЕМ (клик пузырька)
# ════════════════════════════════════════════════════════════

def chat_with_executor(question: str, last_run: Optional[dict] = None,
                       dialog: Optional[list] = None) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        hist = sig.get("history_dna", "")
        fd   = sig.get("final_dna", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ СОВЕТ (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Ордеров: {fd.get('orders_sent','—')} из 3 · "
            f"task_score: {fd.get('task_score','—')}\n"
            f"Летопись: {hist}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про ЭТОТ Совет. Отвечай как Исполнитель — "
            "нейтрально, точно, фактами. Живым голосом, БЕЗ JSON."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не исполнял в этой сессии. Если Шеф спрашивает про "
            "ордера — скажи, что нужен прогон РЫНОК. Живым голосом, без JSON."
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
                    agent_id="A09_ISPOLNITEL", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return f"⚠️ Исполнитель не смог ответить: {e}"


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — Исполнитель замыкает петлю
# ════════════════════════════════════════════════════════════

def run_executor(symbol: str = "XAUUSD", timeframe: str = "H4") -> dict:
    """
    Один ход Исполнителя. Читает табло троих → КОД открывает позиции по
    факту → LLM пишет летопись. Не смотрит рынок своим органом, не решает.

    Возвращает (как движки): {ok, error, narrative, signal, stats, market}.
    """
    # ── 1. Табло троих + контекст бара ───────────────────────
    traders = _read_traders()

    from hooks import load_trading_state
    tstate = load_trading_state()
    iskra_tf = tstate.get("iskra", {}).get("found_timeframe") or timeframe

    market = {"symbol": symbol, "timeframe": iskra_tf, "bar_time": ""}
    try:
        from mt5_feed import _terminal, _fetch
        from williams_core import build_market_data
        mt5 = _terminal()
        if mt5 is not None:
            bars, point = _fetch(mt5, symbol, iskra_tf, 300)
            if bars and point is not None:
                md = build_market_data(bars, symbol=symbol,
                                       timeframe=iskra_tf, point=point)
                if md:
                    market["bar_time"]  = md.get("bar_time", "")
                    market["timeframe"] = iskra_tf
    except Exception as e:
        print(f"[EXECUTOR] ⚠️  bar_time не поднялся ({e}) — летопись без точного бара")

    # ── 2. РУКА ОТКРЫВАЮЩАЯ (КОД) — позиции по факту табло ────
    opened = _open_positions_from_table(traders, market)
    # КАМЕНЬ 3: рука ведущая — исполняет HOLD/MOVE_STOP/ADD/CLOSE.  # EXECUTOR_MANAGE_HAND_V1
    managed = _manage_positions_from_table(traders)
    if managed:
        print(f'[EXECUTOR] ✋ ведение: {managed}')

    # ── 3. Душа (пока спит, как у всех — try/except, не роняет цикл) ──
    # KLON_DUSHI_V1: ДУША — от НОСИТЕЛЯ (маска, Закон Пары), не от трупа из -2.
    # Было: format_soul_for_agent из снесённой studio/ — падало ВСЕГДА
    # («No module named studio»), работали голыми. Пара — ИЗ ПУТИ мозга.
    soul = ""
    try:
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n:
            soul = _n["душа"]
            print(f"[EXECUTOR] 🧬 За столом: {_n['носитель']['имя']}")
    except Exception as e:
        print(f"[EXECUTOR] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    # ── 4. РАСКЛАДКА для летописца — табло + что код уже открыл ─
    facts = _build_execution_log_facts(traders)
    table_for_exec = {
        "traders": {
            "brut": {k: traders["brut"].get(k) for k in
                     ("verdict", "reason", "direction", "entry", "stop", "lot")},
            "avan": {k: traders["avan"].get(k) for k in
                     ("verdict", "reason", "direction", "entry", "stop", "lot")},
            "cons": {k: traders["cons"].get(k) for k in
                     ("verdict", "reason", "direction", "entry", "stop", "lot")},
        },
        "magic":        MAGIC,
        "facts_log":    facts,
        "opened_now":   len(opened),
        "open_positions": tstate.get("positions", []),
        "iskra_t1":     tstate.get("iskra", {}).get("t1_status"),
        "market":       market,
    }

    user_msg = (
        "=== ТАБЛО СОВЕТА (вердикты троих трейдеров — ФАКТ) ===\n"
        f"{json.dumps(table_for_exec, ensure_ascii=False, indent=2)}\n\n"
        "Ты — Исполнитель. Ты НЕ судишь рынок и НЕ считаешь PnL (это код). "
        "Код уже открыл позиции по факту табло (PAPER). Твоя работа: "
        "собрать execution_log (бери числа ТОЧНО из табло — facts_log тебе "
        "эталон, никогда не путай magic), написать history_dna — ОДНУ строку "
        "правды об этом Совете без интерпретаций, и поставить task_score — "
        "честную оценку ДИСЦИПЛИНЫ цеха (не прибыли: потолок 6.0; все трое "
        "REJECTED с внятными причинами — тоже хорошая работа, цех сэкономил). "
        "Выдай строго JSON {narrative, signal}. signal: execution_log, "
        "final_dna (symbol, timeframe, bar_time, t1_status, orders_sent, "
        "orders_skip, task_score), history_dna, deliverables. Ничего вне JSON."
    )

    system_full = prompt
    if soul:
        system_full += "\n\n=== ТВОЁ СОСТОЯНИЕ (душа) ===\n" + soul

    try:
        response = chat(system=system_full, user=user_msg,
                        agent_id="A09_ISPOLNITEL", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        # LLM упал — но позиции УЖЕ открыты кодом (петля цела). Летопись
        # соберём из фактов, без голоса.
        facts_sig = {"execution_log": facts,
                     "final_dna": {"symbol": market["symbol"],
                                   "timeframe": market["timeframe"],
                                   "bar_time": market["bar_time"],
                                   "t1_status": tstate.get("iskra", {}).get("t1_status"),
                                   "orders_sent": len(opened),
                                   "orders_skip": 3 - len(opened),
                                   "task_score": None},
                     "history_dna": "", "deliverables": []}
        _append_log(facts_sig, market, opened)
        stats = _update_stats(opened, traders)
        return {"ok": True, "error": f"летопись без голоса (LLM: {e})",
                "narrative": f"Ордеров: {len(opened)} из 3. Исполнено.",
                "signal": facts_sig, "stats": stats, "market": market}

    # ── 5. Парс + защита чисел + летопись ────────────────────
    narrative, signal = _parse_executor(response)
    signal = _sanitize(signal, traders)

    _append_log(signal, market, opened)
    stats = _update_stats(opened, traders)

    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "stats": stats,
        "market": market,
        "opened": opened,
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

# VASILY_ISP_WATCH_V1 — маркер идемпотентности
