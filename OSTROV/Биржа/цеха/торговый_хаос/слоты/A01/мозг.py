# studio/modules/trading/iskra_live.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН ИСКРЫ (A01) — первое звено Совета Биржи
# Версия: 0.1 · Спринт 45 · 2026-06-16
#
# Это МОЗГ прогона, не UI. Каркас (ui_exchange.py) зовёт run_iskra()
# по кнопке «РЫНОК». Шаги:
#   1. поднять контур: взять свежие бары из терминала (через насос)
#   2. посчитать market_data ядром (williams_core, point из терминала)
#   3. дать Искре думать живой моделью: промт forge + WILLIAMS_MATH
#      + market_data + её history_dna (рабочая память прошлого прогона)
#   4. распарсить двухслойный ответ {narrative, signal}
#   5. narrative → отчёт, signal → цифры под аватаром
#   6. сохранить history_dna, обновить статистику Искры
#
# Искра НЕ торгует — она датчик. Её сигнал позже будит цепочку.
# Здесь только Искра. Остальные агенты — следующими шагами.
# ─────────────────────────────────────────────────────────────

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

import sys as _sys
_repo_root_shim = Path(__file__).resolve().parents[6]
_birzha_code_shim = _repo_root_shim / "Биржа"
if str(_birzha_code_shim) not in _sys.path:
    _sys.path.insert(0, str(_birzha_code_shim))

from llm import chat
# ISKRA_FAIR_JUDGEMENT_V1 · суд Искры по делу (pnl_r), не за пустышку

# ЗАКОН КАРТРИДЖА ДЛЯ КОДА: этот файл живёт ПРЯМО В СЛОТЕ, рядом со
# своим промптом и знаниями — не в отдельном дереве репо-кода. Слот
# несёт с собой ВСЁ: слоты/A01/{мозг.py, промпт.md, знания/, данные/}.
_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/A01/
_CEH_DIR     = _SLOT_DIR.parent.parent                     # торговый_хаос/
_REPO        = _CEH_DIR.parents[3]                          # корень репо
_BIRZHA_CODE = _REPO / "Биржа"                              # общий код (движок, llm)

# KLON_DUSHI_V1: пара (цех, слот) — ИЗ ПУТИ мозга, без хардкода личности.
# Контора не ломается: её слоты зовутся «архивариус»/«исполнитель».
_CEH  = _CEH_DIR.name
_SLOT = _SLOT_DIR.name

PROMPT_PATH  = _SLOT_DIR / "промпт.md"
KNOWLEDGE    = _SLOT_DIR / "знания" / "WILLIAMS_MATH.md"
# Точность датчика — личный журнал РОЛИ (Ролик §4.4а), едет со слотом.
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "iskra_stats.json"
# feed_config.json — общий вочлист всех символов/цехов, НЕ личное
# слота. Ему место в общем коде, не в А01.
_SHARED_DATA = _BIRZHA_CODE / "данные"


# ════════════════════════════════════════════════════════════
# ПАМЯТЬ ИСКРЫ — ШТАТНЫЙ trading_state.json (CHAIN_CONTRACT)
# ─────────────────────────────────────────────────────────────
# Контракт: Искра читает prev_t1_status / prev_zero_point_price,
# которые живут в trading_state["iskra"]. Это ЕДИНОЕ место памяти
# цеха — отсюда же её прочитает Морж. Не плодим свой файл.
# Переиспользуем load/save из hooks — один источник правды.
# ════════════════════════════════════════════════════════════

def _load_iskra_memory() -> dict:
    """
    Читает память Искры из штатного trading_state.json.
    Возвращает {t1_status, zero_point_price, history_dna}.
    """
    from hooks import load_trading_state
    tstate = load_trading_state()
    return tstate.get("iskra", {
        "t1_status": "NOT_FOUND", "zero_point_price": None, "history_dna": ""})


def _save_iskra_memory(signal: dict, md: Optional[dict] = None):  # GLOBAL_BIAS_COMPASS_V1
    """
    Пишет память Искры в штатный trading_state.json — туда, откуда
    её прочитает Морж и следующий прогон самой Искры (prev_*).
    """
    from hooks import load_trading_state, save_trading_state
    tstate = load_trading_state()
    tstate.setdefault("iskra", {})
    tstate["iskra"]["t1_status"]        = signal.get("t1_status", "NOT_FOUND")
    tstate["iskra"]["zero_point_price"] = signal.get("zero_point_price")
    tstate["iskra"]["history_dna"]      = signal.get("history_dna", "")
    # ── ISKRA_MEM_V2: два поля спуска v2 — Морж наследует масштаб ──
    # found_timeframe берём из signal (его кладёт user_msg при found).
    # KOMPAS_DOSTAVKA_TREYDERAM_V1: trend_direction = НАПРАВЛЕНИЕ ТОЧКИ
    # (что нашла Искра), НЕ компас. Раньше эти два понятия были
    # принудительно равны (старые ворота требовали bdb_dir==compass),
    # поэтому их можно было путать безнаказанно. Теперь они могут
    # разойтись (точка против компаса — законный факт, не отказ), и
    # путать их — тихо портить данные трейдерам. Компас — ОТДЕЛЬНОЕ
    # поле, из md (живёт только внутри run_iskra, здесь фиксируется
    # на запись). Фоллбэк на global_bias — если дивера-с-якорем не было.
    _td = signal.get("trend_direction")
    if not _td and md:
        _gb = md.get("global_bias")
        if _gb in ("BULL", "BEAR"):
            _td = _gb
    tstate["iskra"]["trend_direction"] = _td
    _descent = (md or {}).get("v2_descent", {})
    tstate["iskra"]["compass"]  = _descent.get("compass")
    tstate["iskra"]["soglasie"] = _descent.get("soglasie")
    # ISKRA_WAVE_MEASURE_DOSTAVKA_V1: тем же путём, что компас — иначе
    # трейдеры факты структуры не увидят вовсе (та же дыра, что была
    # с компасом до KOMPAS_DOSTAVKA_TREYDERAM_V1).
    tstate["iskra"]["dlina"] = _descent.get("dlina")
    tstate["iskra"]["struktura_chitaetsya"] = _descent.get("struktura_chitaetsya")
    tstate["iskra"]["found_timeframe"] = (
        signal.get("found_timeframe") or signal.get("timeframe")
    )
    # ISKRA_ALIVE_V1: точка c родилась — зажигаем alive. Если статус
    # ушёл обратно в NOT_FOUND — гасим сразу, честно (не ждём, пока
    # proverit_tochku поймает слом на следующем баре в тестере/совете).
    _t1 = signal.get("t1_status", "NOT_FOUND")
    if _t1 == "DETECTED":
        tstate["iskra"]["alive"] = True
        tstate["iskra"]["rodilas_na_bare"] = (md or {}).get("bar_time")
    elif _t1 == "NOT_FOUND":
        tstate["iskra"]["alive"] = False
    save_trading_state(tstate)


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА ИСКРЫ — её винрейт как датчика (под аватар)
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    """Накопительная статистика Искры."""
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "detected": 0, "confirmed": 0,
            "annulled": 0, "exit_bells": 0}


def _update_stats(prev_status: str, signal: dict) -> dict:
    """
    Обновляет статистику по переходу статуса.
      DETECTED      → +1 нашла Точку Ноль
      CONFIRMED     → +1 подтвердилась (разворот факт)
      было DETECTED, стало NOT_FOUND → +1 аннулирована
      exit_bell     → +1 колокол выхода
    """
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    new_status = signal.get("t1_status", "NOT_FOUND")

    if new_status == "DETECTED" and prev_status != "DETECTED":
        stats["detected"] = stats.get("detected", 0) + 1
    if new_status == "CONFIRMED" and prev_status != "CONFIRMED":
        stats["confirmed"] = stats.get("confirmed", 0) + 1
    if prev_status == "DETECTED" and new_status == "NOT_FOUND":
        stats["annulled"] = stats.get("annulled", 0) + 1
    if signal.get("exit_bell"):
        stats["exit_bells"] = stats.get("exit_bells", 0) + 1

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ДВУХСЛОЙНОГО ОТВЕТА ИСКРЫ
# ════════════════════════════════════════════════════════════

def _parse_iskra(response: str) -> tuple[str, dict]:
    """
    Достаёт из ответа модели {narrative, signal}.
    Искра отвечает JSON по CHAIN_CONTRACT v1.1. Если обёрнут в ```json
    или есть лишний текст — вытаскиваем первый JSON-объект.
    Возвращает (narrative, signal_dict). При сбое — текст как narrative.
    """
    # Снять markdown-обёртку ```json ... ```
    cleaned = re.sub(r"```(?:json)?", "", response).strip()
    # Найти первый сбалансированный JSON-объект
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
                        narrative = obj.get("narrative", "")
                        signal = obj.get("signal", {}) or {}
                        return narrative, signal
                    except json.JSONDecodeError:
                        break
    # Не распарсилось — весь текст как голос, пустой сигнал
    return response.strip(), {}


# ════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — один прогон Искры
# ════════════════════════════════════════════════════════════

def chat_with_iskra(question: str, last_run: Optional[dict] = None,
                    dialog: Optional[list] = None) -> str:
    """
    РАБОЧИЙ разговор с Искрой (клик пузырька + вопрос в чате).

    Она отвечает живым голосом, ЗНАЯ свой последний прогон рынка:
    last_run = {narrative, signal, market}. Это её рабочая память —
    Шеф дёрнул за плечо у монитора, она помнит что секунду назад видела.

    Без обращения к терминалу: болтовня не должна поднимать MT5.
    Если прогона ещё не было — честно отвечает, что рынок не смотрела.
    """
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    # Рабочий контекст последнего прогона — в системный довесок.
    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ ПРОГОН РЫНКА (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Твой статус: {sig.get('t1_status','—')}\n"
            f"Дивергенция: {sig.get('divergence','—')}\n"
            f"Точка Ноль: {sig.get('zero_point_price')}\n"
            f"Колокол выхода: {sig.get('exit_bell')}\n"
            f"Что ты сказала: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ПРОГОНА ===\n\n"
            "Шеф спрашивает тебя про ЭТОТ прогон. Отвечай в рабочем режиме — "
            "конкретно, по своим инструментам, как датчик у монитора. "
            "Живым голосом, БЕЗ JSON — это разговор, не сигнал."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не смотрела рынок в этой сессии (РЫНОК не запускали). "
            "Если Шеф спрашивает про рынок — честно скажи, что нужно нажать "
            "РЫНОК, чтобы ты взглянула на свежий бар. Отвечай живым голосом, без JSON."
        )

    system = prompt + work_ctx

    # Душа города и в разговоре — настроение красит ответ.
    try:   # KLON_DUSHI_V1: и в разговоре — ОН, не роль
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n and _n["душа"]:
            system = (prompt + "\n\n=== КТО ТЫ (душа носителя) ===\n"
                      + _n["душа"] + "\n\n" + work_ctx)
    except Exception:
        pass

    # История диалога без последнего вопроса (он пойдёт как user).
    history = []
    if dialog:
        for m in dialog[:-1]:
            r = m.get("role")
            c = m.get("content", "")
            if r in ("user", "assistant") and c:
                history.append({"role": r, "content": c})

    try:
        return chat(
            system=system,
            user=question,
            history=history,
            agent_id="A01_ISKRA",
            slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return f"⚠️ Искра не смогла ответить: {e}"


# ════════════════════════════════════════════════════════════
# ISKRA_V2_DESCENT — СПУСК ПО ЛЕСЕНКЕ ТФ (Способ 1: штангенциркуль)
# ─────────────────────────────────────────────────────────────
# Слепая геометрия. Ни одного LLM-вызова. Код несёт компас старшего
# этажа в руке и ищет точку B/D/B вниз по лесенке. Живая Искра
# просыпается ПОЗЖE, одним вызовом, чтобы озвучить найденное.
# Закон §1d: сенсор мерит, не судит. Спуск — измерение резкости.
# ════════════════════════════════════════════════════════════

def _start_timeframe(symbol: str, fallback: str) -> str:
    """
    Стартовый (макро) этаж = абсолютная истина для актива.
    Приоритет: feed_config.json (watchlist по symbol). Фоллбэк:
    аргумент вызова (новый актив, которого нет в конфиге).
    Конфиг задаёт реальность — кнопка РЫНОК остаётся гибкой.
    """
    try:
        import json
        cfg_path = _SHARED_DATA / "feed_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            for item in cfg.get("watchlist", []):
                if item.get("symbol") == symbol:
                    tf = item.get("timeframe")
                    if tf:
                        return tf
    except Exception as e:
        print(f"[ISKRA] ℹ️  feed_config не прочитан ({e}) — старт от аргумента")
    return fallback


def _read_form_on(symbol: str, tf: str) -> dict:
    """
    Разовый замер одного этажа: pull_bars → ядро → wave_form.
    Чистый штангенциркуль — пришёл, померил, ушёл. Терминал не дал
    баров → пустая форма (этаж слепой, спуск это поймёт).
    """
    from mt5_feed import pull_bars
    from williams_core import build_market_data, _empty_wave_form

    bars, point = pull_bars(symbol, tf)
    if not bars or point is None:
        return _empty_wave_form()
    md = build_market_data(bars, symbol=symbol, timeframe=tf, point=point)
    if not md:
        return _empty_wave_form()
    return md.get("wave_form", _empty_wave_form())


def _macro_timeframe(fallback: str) -> str:
    """
    KOMPAS_PROSTOY_V1: этаж КОМПАСА — 2 этажа вверх по лесенке от
    рабочего (fallback), 1 если двух нет, сам fallback если он уже
    на самом верху (MN1). НЕ путать с _start_timeframe() — та даёт
    этаж для ПОИСКА ТОЧКИ (working-tf-first, спуск), эта — только
    для ориентира направления. Разные роли, разные источники.
    """
    try:
        from mt5_feed import _TF_LADDER
        tf = (fallback or "").upper()
        if tf in _TF_LADDER:
            i = _TF_LADDER.index(tf)
            if i - 2 >= 0:
                return _TF_LADDER[i - 2]
            if i - 1 >= 0:
                return _TF_LADDER[i - 1]
    except Exception as e:
        print(f"[ISKRA] ℹ️  макро-лесенка не поднялась ({e}) — компас от рабочего")
    return fallback


def _read_alligator_on(symbol: str, tf: str) -> dict:
    """
    KOMPAS_PROSTOY_V1: разовый замер ОДНОГО показателя старшего
    этажа для компаса — Аллигатора (Губы/Зубы/Челюсть). Не полный
    market_data, не wave_form — компасу не нужна точка, только
    направление пасти. Пустой словарь — этаж слепой (спуск это поймёт
    как compass=None, честно).
    """
    from mt5_feed import pull_bars
    from williams_core import build_market_data

    bars, point = pull_bars(symbol, tf)
    if not bars or point is None:
        return {}
    md = build_market_data(bars, symbol=symbol, timeframe=tf, point=point)
    if not md:
        return {}
    return md.get("alligator", {}) or {}


def _compass_from(alligator: dict):
    """
    KOMPAS_PROSTOY_V1 (слово Шефа 20.07): компас — ПРОСТОЕ чтение
    тренда старшего этажа, куда смотрит пасть Аллигатора. НЕ полный
    комплекс дивер+якорь-царь+пересечение нуля — тот ищет ТОЧКУ на
    рабочем этаже (см. _descend), компасу точка не нужна, только
    направление. Раньше компас требовал того же редкого комплекса,
    что и сама точка, — на старшем этаже это совпадало ещё реже.
      Губы > Зубы > Челюсть  -> BULL (пасть смотрит вверх)
      Губы < Зубы < Челюсть  -> BEAR (пасть смотрит вниз)
      иначе (спит/перепутаны/этаж слепой) -> None
    """
    jaw   = alligator.get("jaw")
    teeth = alligator.get("teeth")
    lips  = alligator.get("lips")
    if jaw is None or teeth is None or lips is None:
        return None
    if lips > teeth > jaw:
        return "BULL"
    if lips < teeth < jaw:
        return "BEAR"
    return None


def _soglasie_slovami(soglasie) -> str:
    """KOMPAS_NE_VOROTA_V1: ранг точки относительно компаса, словами
    для промпта. Не вердикт — факт на стол."""
    if soglasie is True:
        return "точка ПО компасу (согласие)"
    if soglasie is False:
        return "точка ПРОТИВ компаса (это не отказ — просто против ветра)"
    return "сверять не с чем"


def _descend(symbol: str, start_tf: str, compass, top_form: dict) -> dict:
    """
    KOMPAS_NE_VOROTA_V1 (слово Шефа 18.07): «компас — он и есть компас,
    для ориентира». Раньше здесь были ШОРЫ: спуск засчитывал точку
    ТОЛЬКО если bdb_dir == compass, иначе шагал глубже до дна M5. Это
    были жёсткие ворота — на живой истории они выкашивали до 87%
    честных точек (замер 18.07: 15 событий без компаса против 2 с ним).

    Теперь спуск ищет ТОЧКУ ЛЮБОГО НАПРАВЛЕНИЯ. Компас снимается
    справочно и кладётся рядом как РАНГ, не как условие прохода:
      soglasie=True  — точка в сторону компаса («золотая»)
      soglasie=False — точка против компаса (спекулятивная, меньшим лотом)
      soglasie=None  — компаса нет вовсе (дивера-с-якорем не было)
    Что делать с этим фактом — решают трейдеры, не Искра. Она сенсор.

    start_tf — этаж старта. top_form — уже снятый слепок (без лишнего
    стука в терминал на первом этаже).

    Возвращает:
      {"found": bool, "timeframe": str|None, "zero_point": float|None,
       "napravlenie": str|None, "soglasie": bool|None}
    """
    from mt5_feed import step_down

    tf   = start_tf
    form = top_form          # старший этаж — по готовому слепку, без стука
    visited = 0
    while tf is not None and visited < 12:   # страховка от бесконечного цикла
        bdb_dir = form.get("bdb_dir")
        if bdb_dir is not None:
            # ТОЧКА ЕСТЬ. Компас не запирает — только судит ранг.
            soglasie = (bdb_dir == compass) if compass else None
            # ISKRA_WAVE_MEASURE_DOSTAVKA_V1: факты структуры с ТОГО ЖЕ
            # этажа, где нашлась точка — не с рабочего, слепки разные.
            return {"found": True, "timeframe": tf,
                    "zero_point": form.get("bdb_price"),
                    "napravlenie": bdb_dir, "soglasie": soglasie,
                    "dlina": form.get("dlina"),
                    "struktura_chitaetsya": form.get("struktura_chitaetsya")}
        nxt = step_down(tf)
        if nxt is None:        # дно M5 — глубже кислорода нет
            break
        tf = nxt
        form = _read_form_on(symbol, tf)   # второй этаж и ниже — стучимся
        visited += 1
    return {"found": False, "timeframe": None, "zero_point": None,
            "napravlenie": None, "soglasie": None,
            "dlina": None, "struktura_chitaetsya": False}


def run_iskra(symbol: str = "XAUUSD", timeframe: str = "H4",
              bars_count: int = 300) -> dict:
    """
    Один живой прогон Искры по свежему бару из терминала.

    Возвращает словарь для каркаса:
      {
        "ok": bool,
        "error": str | None,
        "narrative": str,        # голос Искры → в отчёт
        "signal": dict,          # машина → в цифры под аватаром
        "stats": dict,           # статистика → под аватар
        "market": {symbol, timeframe, bar_time, point},
      }
    """
    # ── 1. Поднять контур: бары + point из терминала ─────────
    # ENGINE_ONE_DOOR_V1: рабочий бар через ИСТОЧНИК (кран real|tester),
    # не через прямой терминал. В тестовом режиме берётся из папки —
    # MT5 не поднимается. Реал-кран идёт в терминал как прежде.
    from mt5_feed import pull_bars
    bars, point = pull_bars(symbol, timeframe, bars_count)
    if not bars or point is None:
        return {"ok": False,
                "error": f"Терминал не дал котировки {symbol} {timeframe}. "
                         f"Открыт ли MetaTrader и виден ли символ?",
                "narrative": "", "signal": {}, "stats": _load_stats(), "market": {}}

    # ── 2. Посчитать market_data ядром ───────────────────────
    from williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {"ok": False, "error": "Ядро не собрало market_data",
                "narrative": "", "signal": {}, "stats": _load_stats(), "market": {}}


    # ── 2b. СПУСК ПО ЛЕСЕНКЕ (Искра v2, штангенциркуль) ──────  # ISKRA_V2_DESCENT
    # Слепая геометрия ДО вдоха Искры. Старт этажа из конфига
    # (фоллбэк — аргумент timeframe). Компас связкой (дивер+якорь).
    # Спуск ленивый: на идеале сверху не шагаем вниз вовсе.
    _start_tf = _start_timeframe(symbol, timeframe)
    _top_form = _read_form_on(symbol, _start_tf)

    # KOMPAS_PROSTOY_V1: компас — ОТДЕЛЬНЫЙ, независимый источник
    # (макро-этаж + простой Аллигатор), НЕ тот же _start_tf/_top_form,
    # что кормит поиск точки ниже (working-tf-first — не трогаем).
    _macro_tf = _macro_timeframe(timeframe)
    _macro_alligator = _read_alligator_on(symbol, _macro_tf)

    # ISKRA_WORKING_TF_FIRST_V1 (слово Шефа): рабочий ТФ — ПРЯМОЙ и
    # ГЛАВНЫЙ источник сигнала. Если на нём самом уже есть B/D/B точка
    # (bdb_dir из wave_form, то же окно 100-140, что и Сито 1) — это
    # находка, БЕЗ всякого обязательного макро-компаса. Раньше макро-
    # компас (дивер+горб-царь+пересечение нуля) был ВОРОТАМИ перед
    # рабочим ТФ — лишний, более редкий фильтр поверх уже пройденного
    # сита. Теперь это ЗАПАСНОЙ путь — доуточнение, не ворота.
    # KOMPAS_NE_VOROTA_V1: компас снимается ВСЕГДА и ВСЕГДА справочно —
    # он ориентир, не замок. Раньше «нет компаса» = «Искре нечего
    # ловить» (спуск даже не начинался), и это было вторыми воротами
    # поверх первых: точку убивало отсутствие ДИВЕРА-С-ЯКОРЕМ, хотя
    # сама точка B/D/B на этаже могла быть. Теперь компас только судит
    # ранг найденной точки (soglasie), а ищем — всегда.
    _compass = _compass_from(_macro_alligator)   # KOMPAS_PROSTOY_V1: с макро-этажа, не с _top_form
    _working_bdb = _top_form.get("bdb_dir")
    if _working_bdb is not None:
        # Точка прямо на рабочем этаже — главный путь, как и было.
        _descent = {"found": True, "timeframe": _start_tf,
                    "zero_point": _top_form.get("bdb_price"),
                    "napravlenie": _working_bdb,
                    "soglasie": (_working_bdb == _compass) if _compass else None,
                    "compass": _compass, "start_tf": _start_tf,
                    # ISKRA_WAVE_MEASURE_DOSTAVKA_V1: факты структуры
                    # с рабочего этажа (тот же слепок, что нашёл точку).
                    "dlina": _top_form.get("dlina"),
                    "struktura_chitaetsya": _top_form.get("struktura_chitaetsya")}
    else:
        # На рабочем пусто — спускаемся и ищем точку ЛЮБОГО направления.
        _res = _descend(symbol, _start_tf, _compass, _top_form)
        _descent = {"found": _res["found"], "timeframe": _res["timeframe"],
                    "zero_point": _res["zero_point"],
                    "napravlenie": _res.get("napravlenie"),
                    "soglasie": _res.get("soglasie"),
                    "compass": _compass, "start_tf": _start_tf,
                    "dlina": _res.get("dlina"),
                    "struktura_chitaetsya": _res.get("struktura_chitaetsya")}
    md["v2_descent"] = _descent
    print(f"[ISKRA] 🪜 Спуск: компас={_descent['compass']} "
          f"старт={_descent['start_tf']} "
          f"найдено={'ДА @' + str(_descent['timeframe']) if _descent['found'] else 'нет'}")

    # ── 3. Собрать контекст для Искры ────────────────────────
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    knowledge = KNOWLEDGE.read_text(encoding="utf-8") if KNOWLEDGE.exists() else ""

    # ДУША ГОРОДА — настроение, ДНК, отношения, память.
    # Искра думает не голым промтом, а со своим характером: устала,
    # на streak'е, поругалась на прогулке — это окрасит её голос.
    # Граница: душа красит NARRATIVE (голос), но SIGNAL остаётся
    # фактом движка. Настроение не создаёт дивергенцию из воздуха.
    # KLON_DUSHI_V1: ДУША — от НОСИТЕЛЯ (маска, Закон Пары), не от трупа из -2.
    # Было: format_soul_for_agent из снесённой studio/ — падало ВСЕГДА
    # («No module named studio»), работали голыми. Пара — ИЗ ПУТИ мозга.
    soul = ""
    try:
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n:
            soul = _n["душа"]
            print(f"[ISKRA] 🧬 За столом: {_n['носитель']['имя']}")
    except Exception as e:
        print(f"[ISKRA] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    # Память из ШТАТНОГО trading_state (CHAIN_CONTRACT: prev_*).
    mem = _load_iskra_memory()
    prev_status     = mem.get("t1_status", "NOT_FOUND")
    prev_zero       = mem.get("zero_point_price")
    history_dna     = mem.get("history_dna", "")

    # market_data Искре — её органы: AO/AC + ГОТОВЫЕ ПИВОТЫ из движка.
    # Пивоты (ao.pivots) движок уже посчитал — Искра не считает глазами
    # по сырой цене, а читает факт. Это синхронизирует голос с движком.
    ao_block = md.get("ao", {})
    md_for_iskra = {
        "symbol":    md.get("symbol"),
        "timeframe": md.get("timeframe"),
        "bar_time":  md.get("bar_time"),
        "ao": {
            "value":        ao_block.get("value"),
            "prev_value":   ao_block.get("prev_value"),
            "crossed_zero": ao_block.get("crossed_zero"),
            "zero_dir":     ao_block.get("zero_dir"),
            "direction":    ao_block.get("direction"),
            "pivots":       ao_block.get("pivots", []),   # ← готовые пивоты
        },
        "ac":            md.get("ac", {}),
        "divergence_ao": md.get("divergence_ao"),   # флаг движка (2 послед. пивота)
        "exit_bell":     md.get("exit_bell"),
        "necron_bar":    md.get("necron_bar", {}),   # NECRON_DIVERGENCE_V1: разворотный бар (Necron)
        "price":         md.get("price", {}),
    }

    user_msg = (
        "=== СПУСК ПО ЛЕСЕНКЕ (Искра v2 — слепая геометрия уже отработала) ===\n"
        f"Точка найдена: "
        f"{('ДА на ' + str(md['v2_descent']['timeframe']) + ', цена ' + str(md['v2_descent']['zero_point']) + ', направление ' + str(md['v2_descent'].get('napravlenie'))) if md.get('v2_descent',{}).get('found') else 'нет — молчи (NOT_FOUND)'}\n"
        f"Компас (ориентир со старшего этажа {md.get('v2_descent',{}).get('start_tf','?')}): "
        f"{md.get('v2_descent',{}).get('compass') or 'компаса нет (дивера-с-якорем не было)'}"
        f" — {_soglasie_slovami(md.get('v2_descent',{}).get('soglasie'))}\n"
        f"Структура (горб-3→ноль-4→дивер-5, длина "
        f"{md.get('v2_descent',{}).get('dlina')} баров): "
        f"{'читается строго' if md.get('v2_descent',{}).get('struktura_chitaetsya') else 'не читается строго — не повод молчать, просто факт слабее'}\n"
        "КОМПАС — ОРИЕНТИР, НЕ ЗАМОК. Он НЕ решает, есть точка или нет, "
        "и НЕ задаёт её направление. Точка против компаса — это НЕ отказ, "
        "это факт с пометкой «против ветра»: положи его на стол как есть, "
        "трейдеры решат сами.\n"
        "Если точка найдена — твой signal t1_status=DETECTED, "
        "trend_direction = НАПРАВЛЕНИЕ ТОЧКИ (не компаса), "
        "zero_point_price=цена. Если не найдена — t1_status=NOT_FOUND. "
        "Озвучь это своим голосом.\n\n"
        "=== ТВОЯ РАБОЧАЯ ПАМЯТЬ (прошлый прогон) ===\n"
        f"prev_t1_status: {prev_status}\n"
        f"prev_zero_point_price: {prev_zero}\n"
        f"history_dna: {history_dna or '(пусто — первый прогон, сравнивать не с чем)'}\n\n"
        "=== MARKET_DATA (свежий бар из терминала) ===\n"
        f"{json.dumps(md_for_iskra, ensure_ascii=False, indent=2)}\n\n"
        "Помни закон: твой t1_status (signal) должен совпадать с флагом "
        "divergence_ao движка. Голос (narrative) может рассуждать шире, "
        "но сигнал — это движок. Выдай строго двухслойный JSON "
        "{narrative, signal} по CHAIN_CONTRACT. Ничего вне JSON."
    )

    # ── 4. Искра думает живой моделью (с душой) ──────────────
    # system = промт-роль + душа города. Душа окрашивает голос,
    # но закон жёсткий: signal = факт движка, настроение не создаёт
    # дивергенцию. Злая Искра звучит резче, но врать о рынке не может.
    system_full = prompt
    if soul:
        system_full = (
            prompt
            + "\n\n=== ТВОЁ СОСТОЯНИЕ И ПАМЯТЬ (душа) ===\n"
            + soul
            + "\n\n=== ГРАНИЦА ===\n"
            "Твоё настроение красит ГОЛОС (narrative) — устала, на streak'е, "
            "поругалась на прогулке. Но СИГНАЛ (signal) — это факт движка. "
            "Злость не рождает дивергенцию, усталость не прячет её. "
            "Чувствуй как хочешь, но отражай рынок честно."
        )
    try:
        response = chat(
            system=system_full,
            user=user_msg,
            knowledge=knowledge,
            agent_id="A01_ISKRA",
            slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return {"ok": False, "error": f"Искра не смогла подумать: {e}",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "market": {"symbol": symbol, "timeframe": timeframe,
                           "bar_time": md.get("bar_time"), "point": point}}

    # ── 5. Распарсить ответ ──────────────────────────────────
    narrative, signal = _parse_iskra(response)

    # ── 6. Сохранить память (штатно) и статистику ────────────
    _save_iskra_memory(signal, md)   # GLOBAL_BIAS_COMPASS_V1: фоллбэк компаса
    stats = _update_stats(prev_status, signal)

    # ── 6b. ПЕТЛЯ ОБУЧЕНИЯ — точность отражения → ДНК ────────
    # Искра учится не на деньгах (это трейдеры), а на ТОЧНОСТИ.
    #   подтвердилась (DETECTED→CONFIRMED) → good_work (streak↑, Light↑)
    #   аннулировалась (DETECTED→NOT_FOUND) → bad_work (streak↓, Stress↑)
    # Так датчик со временем становится точнее — путь к мастерству.
    new_status = signal.get("t1_status", "NOT_FOUND")
    # ISKRA_FAIR_JUDGEMENT_V1: суд по ТОЧНОСТИ — только честная награда.
    # good_work за DETECTED→CONFIRMED остаётся: датчик подтвердил
    # свою же находку, это правда. А bad_work за DETECTED→NOT_FOUND
    # УБРАН: NOT_FOUND часто пустышка (точки не было / спуск молчит),
    # а в тестере prev_status тащится через годы — штраф несправедлив.
    # Наказание за УБЫТОЧНУЮ точку теперь в hooks._settle (по pnl_r) —
    # там видно ДЕЛО: повела точка к прибыли или в минус.
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
        "market": {
            "symbol":   symbol,
            "timeframe": timeframe,
            "bar_time": md.get("bar_time"),
            "point":    point,
        },
        "raw": response,   # на случай если парсинг частичный — для отладки
        "descent": md.get("v2_descent", {"found": False}),  # COUNCIL_BY_DESCENT_V1 факт спуска
    }

# ISKRA_WORKING_TF_FIRST_V1 — маркер идемпотентности


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

# KOMPAS_NE_VOROTA_V1 - marker

# KOMPAS_DOSTAVKA_TREYDERAM_V1 - marker

# ISKRA_WAVE_MEASURE_DOSTAVKA_V1 - marker
