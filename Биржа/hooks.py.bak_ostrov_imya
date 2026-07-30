# studio/modules/trading/hooks.py
# ─────────────────────────────────────────────────────────────
# ШЛЮЗ КАРТРИДЖА — Торговый Цех
# Версия: 2.0 · Спринт 43 · 2026-06-09
#
# ЗАКОН: этот файл не знает про математику Вильямса.
# Вся математика — в williams_core.py.
# Здесь только: gate-логика, хуки картриджа, запись в Атлас.
#
# Если в будущем появится order_flow_core.py —
# новый hooks.py будет импортировать оттуда. cartridge.py не заметит.
# ─────────────────────────────────────────────────────────────

import json
import sys
import importlib.util
from datetime import datetime
# ISKRA_FAIR_JUDGEMENT_V1 · суд Искры по pnl_r закрытой сделки
from pathlib import Path
from typing import Optional

from williams_core import build_market_data, read_mt5_csv

# HOOKS_TYPING_V1: тот же _slot_brain, что в ui_torg.py/tester_express.py —
# Закон Картриджа, мозг слота живёт в GRONDHEIM_CITY/Биржа/цеха/.../слоты/.../мозг.py
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_BRAIN_CACHE: dict = {}


def _slot_brain(ceh_id: str, slot: str):
    """Нет файла — честная вакансия (None), не ошибка. Кэш на процесс."""
    key = (ceh_id, slot)
    if key in _BRAIN_CACHE:
        return _BRAIN_CACHE[key]
    brain_path = (_REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh_id
                 / "слоты" / slot / "мозг.py")
    if not brain_path.exists():
        _BRAIN_CACHE[key] = None
        return None
    spec = importlib.util.spec_from_file_location(
        f"_brain_{ceh_id}_{slot}", brain_path)
    if spec is None or spec.loader is None:
        _BRAIN_CACHE[key] = None
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _BRAIN_CACHE[key] = mod
    return mod

# ── Путь к Атласу Ошибок ──────────────────────────────────
ATLAS_PATH = _REPO / "GRONDHEIM_CITY" / "Биржа" / "данные" / "atlas_trading.jsonl"

# ── Рабочая память цеха (Спринт 43) ──────────────────────
# Закрывает две дыры:
#   1. Состояние Искры между прогонами (t1_status — машина состояний)
#   2. Открытые позиции между прогонами (что закрывать по exit_bell)
STATE_PATH = _REPO / "GRONDHEIM_CITY" / "Биржа" / "данные" / "trading_state.json"

# Журнал PnL сделок (НЕ billing_ledger — тот про LLM-расходы)
PNL_PATH = _REPO / "GRONDHEIM_CITY" / "Биржа" / "данные" / "trading_pnl.jsonl"

# Magic numbers — константа КОДА (реальный MT5-мост возьмёт отсюда,
# не из памяти LLM). Промт A09 дублирует таблицу для летописи.
MAGIC_NUMBERS = {"BRUT": 100001, "AVANTURIST": 100002, "KONSERVATOR": 100003}

_DEFAULT_STATE = {
    "version": 1,
    "updated": None,
    "iskra": {
        "t1_status":        "NOT_FOUND",
        "zero_point_price": None,
        "history_dna":      "",
        # TOCHKA_ZHIVA_V1: точка c живёт между барами, не гаснет
        # снимком одного бара. alive — жива ли прямо сейчас.
        # rodilas_na_bare — bar_time последнего обновления/рождения
        # (подпитка той же стороной двигает эту метку вперёд).
        "alive":            False,
        "rodilas_na_bare":  None,
    },
    "positions": [],
}


def load_trading_state() -> dict:
    """Читает рабочую память цеха. Если файла нет — дефолт."""
    if not STATE_PATH.exists():
        return json.loads(json.dumps(_DEFAULT_STATE))
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[STATE] ⚠️  Повреждён trading_state.json ({e}) — дефолт")
        return json.loads(json.dumps(_DEFAULT_STATE))


def save_trading_state(tstate: dict):
    """Сохраняет рабочую память цеха."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tstate["updated"] = datetime.now().isoformat()
    STATE_PATH.write_text(
        json.dumps(tstate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[STATE] 💾 trading_state сохранён: "
          f"t1={tstate['iskra']['t1_status']}, "
          f"позиций={len(tstate['positions'])}")


# ════════════════════════════════════════════════════════════
# GATE — логика цеха (знает про агентов, не знает про Вильямса)
# ════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# TOCHKA_ZHIVA_V1 — точка c живёт между барами (§5р.6)
# ═══════════════════════════════════════════════════════════
# Три станции канона (c → 1 → 2) разнесены во времени (дни на D1).
# Раньше "found" Искры было снимком ТЕКУЩЕГО бара — точка гасла
# раньше, чем реально доходило дело до фрактала Ганса, и Совет на
# станцию «1» просто не просыпался (Ганса никто не спрашивал).
#
# Теперь точка ХРАНИТСЯ в trading_state["iskra"] и живёт, пока не
# умрёт по одному из двух честных признаков:
#   1. СТРУКТУРНЫЙ СЛОМ — цена пробила zero_point_price против
#      направления (дно/потолок разворота пробит вглубь).
#   2. TWR НЕЙТРАЛЕН — 5-периодная SMA(close) застряла между 13 и 34
#      (Новый Хаос гл.9) — импульс разворота угас во флэте.
# Подпитка той же стороной: новый BDB туда же направление +
# GREEN/SQUAT бар подтверждения → точка НЕ умирает, только
# zero_point_price/таймер обновляются (новая энергия того же знака).
#
# Код, без LLM — экономим токены Шефа на каждом баре.
# ═══════════════════════════════════════════════════════════

def proverit_tochku(md: dict) -> dict:
    """
    Кодовая (без LLM) проверка живости точки c на текущем баре.
    Читает/пишет trading_state["iskra"]. Зовётся на КАЖДОМ баре
    между кандидатами (тем же местом, что _settle_bar/_vesti_poziciyu
    в tester_express.py — дёшево на пустом столе).

    Возвращает {"alive": bool, "reason": str, "changed": bool}.
    "changed" — точка поменяла состояние на этом баре (для ленты).
    """
    tstate = load_trading_state()
    isk = tstate.setdefault("iskra", {})
    alive = bool(isk.get("alive"))
    zp    = isk.get("zero_point_price")
    napr  = isk.get("trend_direction") or isk.get("napravlenie")

    if not alive or zp is None or napr not in ("BULL", "BEAR"):
        return {"alive": False, "reason": "точки нет", "changed": False, "direction": None}   # TOCHKA_NAPRAVLENIE_V1

    price = md.get("price", {}) or {}
    low   = price.get("low")
    high  = price.get("high")
    close = price.get("close")   # KALIBROVKA_POROGA_V1: слом — строго по Close
    twr   = md.get("twr", {}) or {}
    # NECRON_DIVERGENCE_V1: "divergent_bar"/bdb_strong снята целиком —
    # направление разворотного бара теперь читаем из wave_form.bdb_dir.
    wf    = md.get("wave_form", {}) or {}
    mfi_type = (md.get("mfi", {}) or {}).get("type")

    # ── 1. подпитка той же стороной — ПРОВЕРЯЕТСЯ ПЕРВОЙ ──
    # Порядок важен (найдено тестом при отладке патча): пробой
    # zero_point_price свежим баром той же стороны с GREEN/SQUAT —
    # это НЕ слом, это новая, более глубокая версия ТОЙ ЖЕ точки.
    # Слом — только когда пробой ничем не подтверждён.
    if wf.get("bdb_dir") == napr and mfi_type in ("GREEN", "SQUAT"):
        novaya_zp = None
        if napr == "BULL" and low is not None:
            novaya_zp = min(zp, low)      # новое, более глубокое дно
        elif napr == "BEAR" and high is not None:
            novaya_zp = max(zp, high)     # новый, более высокий потолок
        if novaya_zp is not None and novaya_zp != zp:
            isk["zero_point_price"] = novaya_zp
            isk["rodilas_na_bare"]  = md.get("bar_time")
            save_trading_state(tstate)
            return {"alive": True,
                    "reason": f"подпитка {mfi_type}: точка обновлена → {novaya_zp}",
                    "changed": True, "direction": napr}   # TOCHKA_NAPRAVLENIE_V1

    # ── 2. структурный слом — СТРОГО ПО CLOSE (KALIBROVKA_POROGA_V1):
    # тень (High/Low) может кольнуть уровень и вернуться — это шум
    # дикого рынка, не слом структуры. Слом — только если ЗАКРЫТИЕ
    # бара ушло за zero_point_price против направления точки.
    slomana = False
    if napr == "BULL" and close is not None and close < zp:
        slomana = True
    elif napr == "BEAR" and close is not None and close > zp:
        slomana = True
    if slomana:
        isk["alive"] = False
        isk["neutral_bars_count"] = 0   # KALIBROVKA_POROGA_V1: точка умерла — счётчик обнулить
        save_trading_state(tstate)
        return {"alive": False,
                "reason": f"структурный слом (close): цена закрылась за {zp}",
                "changed": True, "direction": napr}   # TOCHKA_NAPRAVLENIE_V1

    # ── 3. TWR нейтрален — требует 3 БАРА ПОДРЯД
    # (KALIBROVKA_POROGA_V1): один нейтральный бар — обычная заминка,
    # не повод хоронить структуру. Смерть — только если Ритм держит
    # нейтраль 3 бара(ов) подряд. Любой выход из нейтрали
    # (свежий строй появился) — счётчик сбрасывается в ноль.
    if twr.get("neutral") is True:
        _n = int(isk.get("neutral_bars_count", 0) or 0) + 1
        isk["neutral_bars_count"] = _n
        if _n >= 3:
            isk["alive"] = False
            isk["neutral_bars_count"] = 0
            save_trading_state(tstate)
            return {"alive": False,
                    "reason": f"TWR нейтрален {_n} бар(а) подряд — ритм угас во флэте",
                    "changed": True, "direction": napr}   # TOCHKA_NAPRAVLENIE_V1
        save_trading_state(tstate)
        return {"alive": True,
                "reason": f"TWR нейтрален {_n}/3 — ещё жива, считаю",
                "changed": False, "direction": napr}
    else:
        if isk.get("neutral_bars_count"):
            isk["neutral_bars_count"] = 0   # строй вернулся — счётчик сброшен
            save_trading_state(tstate)

    return {"alive": True, "reason": "жива", "changed": False, "direction": napr}   # TOCHKA_NAPRAVLENIE_V1

# TOCHKA_ZHIVA_V1 - marker


# ═══════════════════════════════════════════════════════════
# ZIGZAG_CORE_V1 — наблюдатель ног зигзага A-B-C (20.07)
# ═══════════════════════════════════════════════════════════
# Параллельный слой поверх TOCHKA_ZHIVA_V1, НИЧЕГО не гейтит и не
# подменяет. Курс Шефа 20.07: не отсекать флэт порогом N — строить
# саму волну (нога A → B → попытка C → подтверждённая C → архив),
# так, что флэт исключает себя сам (C на флэте никогда не
# подтверждается). Пока это НАБЛЮДАТЕЛЬ: событие ложится в
# trading_state["zigzag"] и в консоль, Искра его пока не читает —
# следующий шаг (когда канон будет готов) решит, использовать ли
# C_CONFIRMED как ворота её поиска разворота.
#
# Честный no-op при любой накладке (модуль не найден/данные не те) —
# наблюдатель не имеет права уронить торговый цикл.
# ═══════════════════════════════════════════════════════════

def proverit_nogu(md: dict) -> Optional[dict]:
    """
    Один шаг автомата ног (zigzag_core.on_bar_md) на баре md. Читает/
    пишет trading_state["zigzag"] — тем же приёмом, что proverit_tochku
    держит trading_state["iskra"]. Возвращает событие (dict) или None.
    """
    try:
        from zigzag_core import ZigzagTracker, on_bar_md
    except Exception:
        return None
    try:
        tstate = load_trading_state()
        zstate = tstate.get("zigzag") or ZigzagTracker.novoye_sostoyanie()
        event = on_bar_md(zstate, md)
        tstate["zigzag"] = zstate
        save_trading_state(tstate)
        return event
    except Exception as e:
        print(f"[НОГА] ⚠️  наблюдатель ног не сработал ({e}) — торговый цикл цел")
        return None

# ZIGZAG_CORE_V1 - marker


def gate_hans(chain_data: dict) -> bool:
    """
    GATE 1 — A04 Ганс запускается только если:
      t1_status == "CONFIRMED"
      wave_1_validated == true

    Возвращает True если Ганс проходит.
    """
    t1    = chain_data.get("t1_status", "NOT_FOUND")
    wave1 = chain_data.get("wave_1_validated", False)
    result = (t1 == "CONFIRMED" and wave1 is True)
    if not result:
        print(f"[GATE] 🚫 Ганс заблокирован: t1={t1}, wave_1={wave1}")
    else:
        print(f"[GATE] ✅ Ганс проходит: t1={t1}, wave_1={wave1}")
    return result


# ════════════════════════════════════════════════════════════
# ХУКИ КАРТРИДЖА
# ════════════════════════════════════════════════════════════

def on_before_run(state: dict) -> dict:
    """
    Вызывается перед стартом цепочки.
    Идёт в williams_core → забирает market_data → кладёт в chain_data.

    Параметры из state["settings"]:
      csv_path:   путь к CSV файлу (ШАГ 1 — бэктест)
      symbol:     тикер ("EURUSD", "XAUUSD", ...)
      timeframe:  таймфрейм ("D1", "H4", "H1", ...)
      bars_limit: сколько последних баров брать (0 = все)
      point:      _Point override (опционально)
    """
    settings   = state.get("settings", {})
    csv_path   = settings.get("csv_path", "")
    symbol     = settings.get("symbol",    "UNKNOWN")
    timeframe  = settings.get("timeframe", "D1")
    bars_limit = int(settings.get("bars_limit", 0))
    point      = float(settings["point"]) if settings.get("point") else None

    print(f"\n[TRADING] ⚔️  Военный Совет запускается")
    print(f"[TRADING]    Символ: {symbol} | ТФ: {timeframe}")

    # ── Рабочая память цеха: загружаем ПЕРЕД любым режимом ──
    tstate = load_trading_state()
    cd = state.setdefault("chain_data", {})
    cd["history_dna"]          = tstate["iskra"].get("history_dna", "")
    cd["prev_t1_status"]       = tstate["iskra"].get("t1_status", "NOT_FOUND")
    cd["prev_zero_point_price"] = tstate["iskra"].get("zero_point_price")
    cd["open_positions"]       = tstate.get("positions", [])
    if cd["open_positions"]:
        print(f"[STATE] 📂 Открытых позиций: {len(cd['open_positions'])}")
    if cd["prev_t1_status"] != "NOT_FOUND":
        print(f"[STATE] 📂 Искра помнит: t1={cd['prev_t1_status']}, "
              f"Точка Ноль={cd['prev_zero_point_price']}")

    if csv_path:
        bars = read_mt5_csv(csv_path)
        if bars_limit > 0:
            bars = bars[-bars_limit:]
    else:
        # market_data уже передан напрямую (webhook / MT5 polling)
        if state.get("chain_data", {}).get("market_data"):
            print("[TRADING] 📡 market_data получен напрямую (webhook режим)")
            return state
        print("[TRADING] ⚠️  csv_path не задан и market_data отсутствует")
        return state

    if not bars:
        print("[TRADING] ❌ Нет данных — Совет не стартует")
        return state

    market_data = build_market_data(bars, symbol=symbol,
                                    timeframe=timeframe, point=point)
    if not market_data:
        print("[TRADING] ❌ williams_core вернул пустой результат")
        return state

    state.setdefault("chain_data", {})["market_data"] = market_data
    # history_dna уже загружен из trading_state.json выше

    # Подушка безопасности Вильямса: экстремум второго бара назад.
    # Кладём в chain_data, чтобы _prepare_trade_setup взял оттуда.
    cd = state.setdefault("chain_data", {})
    if len(bars) >= 3:
        cd["_bar_back2_low"]  = bars[-3]["low"]
        cd["_bar_back2_high"] = bars[-3]["high"]

    _settle_positions(state)          # закрытие позиций — стоп / exit_bell
    _print_market_summary(market_data)

    # ZIGZAG_CORE_V1: наблюдатель ног — параллельно, ничего не гейтит
    _noga_ev = proverit_nogu(market_data)
    if _noga_ev:
        print(f"[НОГА] {_noga_ev.get('event')}: {_noga_ev}")

    return state


def on_before_agent(state: dict, agent_id: str) -> dict:
    """
    Вызывается перед каждым агентом.
    Реализует GATE 1 — блокировку Ганса.
    """
    if agent_id == "A05":
        _prepare_atlas_digest(state)
        _prepare_trade_setup(state)
        # ARKHIV_KAK_INFORMACIYA_V1: выжимка Архива — В СТОЛ, как ИНФОРМАЦИЯ.
        # Не приказ, не фильтр входа — трейдер сам решает, весить ли
        # её (тот же принцип, что и у сенсоров: вводная, не команда).
        try:
            _dig = (state.get("chain_data", {}) or {}).get("atlas_digest", {}) or {}
            if _dig:
                _ts = load_trading_state()
                _ts["arkhiv"] = {
                    "sample_size":        _dig.get("sample_size"),
                    "closed_trades":      _dig.get("closed_trades"),
                    "success_rate":       _dig.get("success_rate"),
                    "top_failure_reason": _dig.get("top_failure_reason"),
                    "confidence":         _dig.get("arkhiv_confidence"),
                }
                save_trading_state(_ts)
        except Exception as _ae:
            print(f"[ARKHIV] ⚠️  выжимка не легла в стол: {_ae}")

    if agent_id == "A04":
        chain = state.get("chain_data", {})
        if not gate_hans(chain):
            state.setdefault("chain_data", {}).update({
                "entry_trigger":     False,
                "fractal_detected":  False,
                "fractal_outside_jaw": False,
                "absorption_ratio":  None,
            })
            state["_skip_agent"] = True
            print("[GATE] ⏭  A04 Ганс пропущен")

    # Живое состояние трейдера перед Трибуналом
    if agent_id in ("A06", "A07", "A08"):
        _prepare_trader_state(state, agent_id)

    return state


def on_after_agent(state: dict, agent_id: str, result: dict) -> dict:
    """
    Вызывается после каждого агента.
    Реализует GATE 2 — хард-стоп если все трое отказали.
    """
    if agent_id == "A09":
        results = state.get("results", {})
        brut_v  = _extract_verdict(results.get("A06", {}), "brut_verdict")
        avan_v  = _extract_verdict(results.get("A07", {}), "avan_verdict")
        cons_v  = _extract_verdict(results.get("A08", {}), "cons_verdict")

        # ── Сохраняем рабочую память цеха (ДО любого stop) ──
        _persist_trading_state(state)

        # ── Каждый REJECTED — в Атлас (Архивариусу нужны отказы) ──
        _log_rejections(state)

        all_rejected = all(
            v == "REJECTED" for v in [brut_v, avan_v, cons_v] if v is not None
        )

        if all_rejected:
            print("[TRADING] 🛑 ХАРД-СТОП: все трое отказали")
            _write_atlas({
                "event":  "HARD_STOP",
                "reason": "all_traders_rejected",
                "brut":   brut_v,
                "avan":   avan_v,
                "cons":   cons_v,
                "market": state.get("chain_data", {}).get("market_data", {}),
            })
            return {"action": "stop"}

    return {}


# ════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ════════════════════════════════════════════════════════════

def _log_rejections(state: dict):
    """
    Пишет в Атлас запись по КАЖДОМУ одиночному REJECTED —
    с полной сигнатурой Совета (CHAIN_CONTRACT v1.3).
    HARD_STOP (все трое) пишется отдельно в on_after_agent.
    Без этих записей Архивариус слеп к причинам отказов.
    """
    results = state.get("results", {})
    chain   = state.get("chain_data", {})
    md      = chain.get("market_data", {})

    traders = [
        ("A06", "BRUT",        "brut_verdict", "brut_reason"),
        ("A07", "AVANTURIST",  "avan_verdict", "avan_reason"),
        ("A08", "KONSERVATOR", "cons_verdict", "cons_reason"),
    ]

    verdicts = {}
    for aid, name, v_key, r_key in traders:
        out = (results.get(aid, {}).get("meta", {}) or {}) \
            .get("my_output", {}) or {}
        verdicts[name] = (out.get(v_key), out.get(r_key))

    # Если все трое REJECTED — HARD_STOP запишет их сам, не дублируем
    if all(v == "REJECTED" for v, _ in verdicts.values()):
        return

    for name, (verdict, reason) in verdicts.items():
        if verdict != "REJECTED":
            continue
        _write_atlas({
            "event":         "TRADER_REJECTED",
            "trader":        name,
            "verdict":       "REJECTED",
            "reason":        reason or "unknown",
            "symbol":        md.get("symbol"),
            "timeframe":     md.get("timeframe"),
            "bar_time":      md.get("bar_time"),
            "t1_status":     chain.get("t1_status"),
            "morj_status":   chain.get("morj_status"),
            "panic_phase":   chain.get("panic_phase"),
            "fractal_valid": chain.get("fractal_valid"),  # ARKHIV_REJ_PATCHED
            "pnl":           None,
        })
        print(f"[ATLAS] 📝 Отказ записан: {name} — {reason}")


# ═══════════════════════════════════════════════════════════
# VEDENIE_POZICII_V1 — ТРЕЙЛИНГ ЗА ЗУБАМИ («СЕЙФ»)
# ═══════════════════════════════════════════════════════════
# Канон (KOTIN_PHILOSOPHY.md):
#   гл.7: «Зубы (Teeth, красная линия) — ГРАНИЦА ПИРАМИДЫ ДОЛИВОК.
#          Пока цена выше Зубов (для лонга) — пирамида жива.
#          Пробой Зубов вниз = смерть пирамиды.»
#   гл.9: «трейлинг-стоп всей пирамиды за линией Аллигатора
#          («сейф», риск→0)»
#   гл.10: «Стоп системы. НЕ ЛИЧНЫЙ. Если двигать произвольно —
#          это другая система, не Котин.»
#
# ⇒ Трейлинг — НЕ ВОПРОС ВКУСА. Это ЗАКОН, и его исполняет КОД,
#   на каждом баре, без единого вызова LLM. Трейдер тут не решает.
#   (Решение Шефа: гибрид. Стоп — код. Долив — характер.)
#
# Стоп двигается ТОЛЬКО В ЗАЩИТУ (монотонно). Никогда обратно —
# ослабить стоп значит перестать быть Котиным.
# ═══════════════════════════════════════════════════════════

def _treyling_za_zubami(state: dict):
    """Тянет стоп всей пирамиды за Зубами (Teeth). Зовётся КАЖДЫЙ БАР,
    ДО проверки стопа — чтобы «сейф» успел сработать раньше, чем
    рынок дотянется до старого стопа.

    LONG:  стоп подтягивается вверх к Зубам (но не выше цены).
    SHORT: стоп подтягивается вниз к Зубам.

    Только в защитную сторону. Ослабление — молча игнорируем
    (по канону это уже не Котин)."""
    chain = state.get("chain_data", {})
    md    = chain.get("market_data", {})
    positions = chain.get("open_positions", []) or []
    if not positions or not md:
        return

    allig = md.get("alligator", {}) or {}
    teeth = allig.get("teeth")
    close = (md.get("price", {}) or {}).get("close")
    if teeth is None or close is None:
        return

    tstate = load_trading_state()
    live = tstate.get("positions", []) or []
    dirty = False

    for pos in live:
        if pos.get("status") != "OPEN":
            continue
        direction = (pos.get("direction") or "").upper()
        old = pos.get("stop")
        entry = pos.get("entry")
        if old is None or entry is None:
            continue

        if direction == "LONG":
            # цена ушла под Зубы — пирамида мертва, стоп не тянем
            # (её добьёт _settle_positions по стопу или колоколу)
            if close < teeth:
                continue
            novy = teeth
            if novy <= old:          # только в защиту
                continue
            if novy >= close:        # стоп не может быть выше цены
                continue
        elif direction == "SHORT":
            if close > teeth:
                continue
            novy = teeth
            if novy >= old:
                continue
            if novy <= close:
                continue
        else:
            continue

        # СЕЙФ: момент, когда риск стал НУЛЕВЫМ или отрицательным
        v_seyfe = ((direction == "LONG"  and old < entry <= novy) or
                   (direction == "SHORT" and old > entry >= novy))

        pos["stop"] = round(novy, 6)
        pos["trailed"] = pos.get("trailed", 0) + 1
        dirty = True

        if v_seyfe:
            print(f"[СЕЙФ] 🔒 {pos.get('trader')} {direction}: стоп "
                  f"{old} → {novy} — РИСК ОБНУЛЁН (за Зубами)")
        else:
            print(f"[ТРЕЙЛ] ⬆ {pos.get('trader')} {direction}: стоп "
                  f"{old} → {novy} (за Зубами)")

    if dirty:
        tstate["positions"] = live
        save_trading_state(tstate)


# ═══════════════════════════════════════════════════════════
# RUKA_DOPISYVAYUSHCHAYA_V1 — ДНЕВНИК УЗНАЁТ ИСХОД
# ═══════════════════════════════════════════════════════════
# Трейдер при входе писал в тетрадь `result: None` и в докстринге своей
# же функции обещал: «допишет РУКА ДОПИСЫВАЮЩАЯ при закрытии позиции
# (hooks._settle)».
#
# РУКИ НЕ БЫЛО. Ни разу. Дневник копил НАМЕРЕНИЯ, а не ОПЫТ:
# «вошёл LONG @1247.36» — и всё. Чем кончилось — неизвестно.
#
# А это ХУЖЕ пустого дневника: прошлое решение подкрепляет само себя
# фактом существования. «Я так уже делал» звучит доводом — хотя в
# прошлый раз стоило −1.0R.
#
# Теперь при закрытии позиции исход возвращается в тетрадь хозяина.
# ═══════════════════════════════════════════════════════════

# Тетради живут в слотах цехов (проверено на диске 14.07):
#   торговый_хаос/слоты/A06/данные/diary_brut.jsonl
#   торговый_хаос/слоты/A07/данные/diary_avan.jsonl
#   торговый_хаос/слоты/A08/данные/diary_cons.jsonl
_DIARY_OF = {
    "BRUT":        ("A06", "diary_brut.jsonl"),
    "AVANTURIST":  ("A07", "diary_avan.jsonl"),
    "KONSERVATOR": ("A08", "diary_cons.jsonl"),
}


def _dopisat_v_dnevnik(trader: str, entry, pnl_r, reason: str, bar_time=None):
    """Возвращает ИСХОД в тетрадь трейдера.

    Ищет запись с тем же `entry` и пустым `result` (сверху вниз — берём
    САМУЮ СВЕЖУЮ, если вдруг он входил по той же цене дважды).
    Не нашёл — молчим: значит вход был не через дневник (ручной,
    старый прогон), и врать в тетрадь нельзя.
    """
    slot = _DIARY_OF.get((trader or "").upper())
    if not slot or entry is None or pnl_r is None:
        return False

    sid, fname = slot
    path = (_REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха" / "торговый_хаос"
            / "слоты" / sid / "данные" / fname)
    if not path.exists():
        return False

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False

    itog = {
        "pnl_r":  round(float(pnl_r), 4),
        "reason": reason,
        "closed_at": bar_time,
        "оценка": ("плюс" if pnl_r > 0 else
                   "полный стоп" if abs(pnl_r + 1.0) < 0.05 else "минус"),
    }

    # снизу вверх — самая свежая незакрытая запись с этим входом
    for i in range(len(lines) - 1, -1, -1):
        ln = lines[i].strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if rec.get("result") is not None:
            continue
        e = rec.get("entry")
        if e is None:
            continue
        try:
            if abs(float(e) - float(entry)) > 1e-6:
                continue
        except Exception:
            continue

        rec["result"] = itog
        lines[i] = json.dumps(rec, ensure_ascii=False)
        try:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as ex:
            print(f"[ТЕТРАДЬ] ⚠️  не записал ({trader}): {ex}")
            return False

        znak = "🟢" if pnl_r > 0 else "🔴"
        print(f"[ТЕТРАДЬ] ✍️  {trader}: вход {entry} → "
              f"{pnl_r:+.2f}R ({reason}) {znak} — исход вписан")
        return True

    # записи нет — это не ошибка, просто вход был не через дневник
    return False


# ═══════════════════════════════════════════════════════════
# OTLOZHENNY_ORDER_V1 — ЗАЯВКА ЖДЁТ ПРОБОЯ
# ═══════════════════════════════════════════════════════════
# Вопрос Шефа: «сделки как открываются? с рынка или по отложенным?»
# Открывались МГНОВЕННО, по названной цене. Никакой отложки.
#
# А трейдеры ВСЕ говорят «Buy Stop», «Sell Stop», «жду активации».
# Книга гл.8: «BUY STOP на 1 тик выше high фрактального бара».
#
# ⇒ Половина сделок была ФАНТОМАМИ: вход по цене, до которой рынок
#   не дошёл. Открылись «на пробое», которого не было → цена сразу
#   против → стоп за один бар. Отсюда 67% закрытий ровно по −1.0R.
#
# Теперь заявка рождается PENDING и ЖДЁТ, пока рынок сам её возьмёт.
# ═══════════════════════════════════════════════════════════

ORDER_EXPIRE_BARS = 10   # не пробил за 10 баров — структура протухла



# PEREEZD_ZAYAVKI_V1: переезд заявки за новым фракталом (Вильямс) ──────
def _pereezd_zayavki(pos, md):
    """Проверяет PENDING-заявку против текущей структуры фракталов.
    Возвращает:
      "MOVED"   — переехала на новый фрактал (pos обновлён на месте);
      "CANCEL"  — цена вернулась к старту, сигнал мёртв (снять);
      None      — ничего, ждём дальше.
    Спред-поправка та же, что при рождении.
    """
    d = (pos.get("direction") or "").upper()
    fr = md.get("fractals", {}) or {}
    price = md.get("price", {}) or {}
    close = price.get("close")
    point = md.get("point") or 0.01
    sp_pts = (md.get("mfi", {}) or {}).get("spread")
    sp = (float(sp_pts) * float(point)) if sp_pts is not None else 0.0
    punkt = 10 * float(point or 0.01)  # PUNKT_OT_POINT_V1: пункт = 10×point

    if close is None:
        return None

    if d == "LONG":
        up = fr.get("last_up") or {}
        down = fr.get("last_down") or {}
        up_px = up.get("price") if isinstance(up, dict) else None
        up_idx = up.get("bar_index") if isinstance(up, dict) else None
        down_px = down.get("price") if isinstance(down, dict) else None

        # 2. возврат к старту сигнала — снять
        start = pos.get("signal_start")
        if start is not None and close < start:
            return "CANCEL"

        # 1. новый ВЕРХНИЙ фрактал (другой bar_index) ВЫШЕ прежнего → переезд
        old_idx = pos.get("entry_fractal_idx")
        old_px = pos.get("entry_fractal_price")
        if (up_px is not None and up_idx is not None
                and up_idx != old_idx
                and (old_px is None or up_px > old_px)):
            pos["entry"] = round(up_px + 2 * sp, 6)          # Buy Stop + спред
            if down_px is not None:
                pos["stop"] = round(down_px, 6)              # под новый низ
                pos["stop_initial"] = pos["stop"]            # R от новой опоры
                pos["signal_start"] = down_px                # новый старт сигнала
            pos["entry_fractal_price"] = up_px
            pos["entry_fractal_idx"] = up_idx
            pos["_ждёт_баров"] = 0                            # счётчик сброшен
            return "MOVED"

    elif d == "SHORT":
        up = fr.get("last_up") or {}
        down = fr.get("last_down") or {}
        down_px = down.get("price") if isinstance(down, dict) else None
        down_idx = down.get("bar_index") if isinstance(down, dict) else None
        up_px = up.get("price") if isinstance(up, dict) else None

        start = pos.get("signal_start")
        if start is not None and close > start:
            return "CANCEL"

        old_idx = pos.get("entry_fractal_idx")
        old_px = pos.get("entry_fractal_price")
        if (down_px is not None and down_idx is not None
                and down_idx != old_idx
                and (old_px is None or down_px < old_px)):
            pos["entry"] = round(down_px - 3 * punkt, 6)     # Sell Stop − 3 пункта
            if up_px is not None:
                pos["stop"] = round(up_px + 2 * sp, 6)       # над новым верхом
                pos["stop_initial"] = pos["stop"]
                pos["signal_start"] = up_px
            pos["entry_fractal_price"] = down_px
            pos["entry_fractal_idx"] = down_idx
            pos["_ждёт_баров"] = 0
            return "MOVED"

    return None


def _zapomnit_fraktal_starta(order, chain):
    """При рождении PENDING: запоминаем фрактал входа и старт
    сигнала (противоположный фрактал) — опоры для переезда."""
    d = (order.get("direction") or "").upper()
    md = chain.get("market_data", {}) or {}
    fr = md.get("fractals", {}) or {}
    up = fr.get("last_up") or {}
    down = fr.get("last_down") or {}
    if d == "LONG":
        f = up if isinstance(up, dict) else {}
        opp = down if isinstance(down, dict) else {}
    else:
        f = down if isinstance(down, dict) else {}
        opp = up if isinstance(up, dict) else {}
    return {
        "entry_fractal_price": f.get("price"),
        "entry_fractal_idx":   f.get("bar_index"),
        "signal_start":        opp.get("price"),
    }


# ═══════════════════════════════════════════════════════════
# VASILY_ZASADA_V1 — ЗАСАДА КОНСЕРВАТОРА (наблюдение по условию)
# ═══════════════════════════════════════════════════════════
# §5з.8 Летописи: у Васи (A08, magic 100003) нет аналога отложки.
# Брут ждёт ЦЕНУ (PENDING), Вася ждёт УСЛОВИЕ СТРУКТУРЫ (WATCHING).
# Две фазы (строгий отскок — Консерватор берёт по скидке, канон §12):
#   wait_wave1    → Морж подтвердил волну 1 (wave_1_validated)
#   wait_pullback → цена КОСНУЛАСЬ опоры И след. бар ЗАКРЫЛСЯ обратно
#                   по тренду (подтверждённый отскок, не падающий нож)
# Оба перехода — КОД, ноль LLM. Вася уже назвал координаты на WATCH.

VASILY_WATCH_EXPIRE_BARS = 20   # засада живёт дольше заявки: структура
                                # зреет медленнее, чем пробивается фрактал


def _rodit_nablyudenie_vasily(order: dict, chain: dict) -> dict:
    """Рождение WATCHING-записи из вердикта Васи с action=WATCH.
    Координаты (direction/опора/entry/stop) назвал он сам — код только
    раскладывает их в позицию-наблюдение. Опоры/стопа нет → None-запись
    (её отсеет _persist_trading_state как пустую засаду)."""
    d = (order.get("direction") or "").upper()
    opora = order.get("watch_opora")
    entry = order.get("entry")
    stop = order.get("stop")
    md = chain.get("market_data", {}) or {}
    return {
        "trader":     order.get("trader"),
        "magic":      order.get("magic"),
        "direction":  d,
        "status":     "WATCHING",
        "watch_phase": "wait_wave1",   # фаза 1: ждём Моржа
        "watch_opora": opora,          # цена опоры (фрактал/Зубы)
        "entry":      entry,           # Buy/Sell Stop ПОСЛЕ отскока
        "stop":       stop,
        "stop_initial": stop,          # R от названного стопа
        "lot":        order.get("lot"),
        "tp":         None,
        "_watch_с":   md.get("bar_time", ""),
        "_watch_баров": 0,
        "_kasanie":   False,           # фаза 2: коснулись ли опоры
        "mode":       order.get("status", "PAPER"),
        "opened_at":  None,            # входа ещё нет
        "pnl":        None,
        "entry_bias": md.get("global_bias"),
    }


def _proverit_otkat_vasily(pos: dict, md: dict) -> str:
    """Двухфазный детектор созревания засады Васи. Возвращает:
      "RIPE"   — структура созрела, засаду пора переводить в PENDING;
      "CANCEL" — структура сломалась (цена ушла за опору не туда);
      None     — ждём дальше.

    Фаза 1 (wait_wave1): Морж подтвердил волну 1 → переходим в фазу 2.
      Источник — chain-слепок стола ЭТОГО бара (тот же, что читают
      соседи). wave_1_validated живёт в morj-показании.
    Фаза 2 (wait_pullback): СТРОГИЙ отскок —
      LONG:  low <= опора (коснулись) И на след. баре close > опора
      SHORT: high >= опора (коснулись) И на след. баре close < опора
      Касание и подтверждение — РАЗНЫЕ бары (флаг _kasanie переносит
      факт касания в следующий бар)."""
    d = (pos.get("direction") or "").upper()
    opora = pos.get("watch_opora")
    price = md.get("price", {}) or {}
    close = price.get("close")
    high = price.get("high")
    low = price.get("low")
    if opora is None or close is None:
        return None

    phase = pos.get("watch_phase", "wait_wave1")

    # ── ФАЗА 1: ждём подтверждения волны 1 Моржом ──
    if phase == "wait_wave1":
        morj = md.get("morj", {}) or {}
        # морж-показание может приезжать как флаг в market_data или в
        # выделенном под-словаре — читаем оба честно
        wave1 = (morj.get("wave_1_validated")
                 if isinstance(morj, dict) else None)
        if wave1 is None:
            wave1 = md.get("wave_1_validated")
        if wave1:
            pos["watch_phase"] = "wait_pullback"
            print(f"[ЗАСАДА] 🌊 {pos.get('trader')} {d}: Морж подтвердил "
                  f"волну 1 → жду отката к опоре {opora}")
        return None   # даже если перешли — отскок проверяем со след. бара

    # ── ФАЗА 2: строгий отскок от опоры ──
    if phase == "wait_pullback":
        # структура сломалась: цена пробила опору НАСКВОЗЬ против входа
        # (для LONG опора снизу — уход глубоко ниже = слом; для SHORT наоборот)
        if d == "LONG":
            # был ли уже факт касания на прошлом баре?
            if pos.get("_kasanie"):
                if close > opora:
                    return "RIPE"        # отскочили и закрылись выше — зрело
                # ещё под опорой — держим касание, ждём закрытие выше
                # но если ушли глубоко (>2 «пункта» ниже) — слом
            # касание на ЭТОМ баре?
            if low is not None and low <= opora:
                pos["_kasanie"] = True
                if close > opora:
                    return "RIPE"        # коснулись И тут же закрылись выше
        elif d == "SHORT":
            if pos.get("_kasanie"):
                if close < opora:
                    return "RIPE"
            if high is not None and high >= opora:
                pos["_kasanie"] = True
                if close < opora:
                    return "RIPE"
        return None

    return None


def _aktivirovat_ordera(state: dict):
    """Отложенные заявки: активируем те, что рынок ПРОБИЛ; отменяем
    протухшие. Зовётся КАЖДЫЙ БАР, ДО трейлинга и ДО закрытия.

    LONG  (Buy Stop, entry ВЫШЕ цены):  high >= entry → сработал
    SHORT (Sell Stop, entry НИЖЕ цены): low  <= entry → сработал

    Активированная заявка становится OPEN и с этого мига живёт как
    позиция: её ведут, судят, она дышит. Неактивированная — НЕ СДЕЛКА,
    и опыта с неё нет. Честно."""
    chain = state.get("chain_data", {})
    md    = chain.get("market_data", {})
    if not md:
        return

    price = md.get("price", {}) or {}
    high  = price.get("high")
    low   = price.get("low")
    bar_time = md.get("bar_time")
    if high is None or low is None:
        return

    tstate = load_trading_state()
    live = tstate.get("positions", []) or []
    dirty = False
    ostalis = []

    for pos in live:
        # VASILY_ZASADA_V1: засада Консерватора — своя ветка, до PENDING.
        if pos.get("status") == "WATCHING":
            _sostoyanie = _proverit_otkat_vasily(pos, md)
            if _sostoyanie == "RIPE":
                # структура созрела → засада становится обычной заявкой,
                # дальше её ведёт та же машинерия, что и Брута
                pos["status"] = "PENDING"
                pos.pop("watch_phase", None)
                pos.pop("_kasanie", None)
                pos["_ждёт_баров"] = 0
                dirty = True
                print(f"[ЗАСАДА] ✅ {pos.get('trader')} {pos.get('direction')} "
                      f"СОЗРЕЛА @ опора {pos.get('watch_opora')} → PENDING "
                      f"@ {pos.get('entry')} (волна 1 + отскок)")
                ostalis.append(pos)
                continue
            if _sostoyanie == "CANCEL":
                print(f"[ЗАСАДА] 🚫 {pos.get('trader')} "
                      f"{pos.get('direction')} снята — структура сломалась")
                dirty = True
                continue
            # ждём дальше — считаем возраст засады
            _vozrast = pos.get("_watch_баров", 0) + 1
            pos["_watch_баров"] = _vozrast
            dirty = True
            if _vozrast >= VASILY_WATCH_EXPIRE_BARS:
                print(f"[ЗАСАДА] 🚫 {pos.get('trader')} снята — "
                      f"структура не созрела за {VASILY_WATCH_EXPIRE_BARS} "
                      f"баров (протухла)")
                continue
            ostalis.append(pos)
            continue
        if pos.get("status") != "PENDING":
            ostalis.append(pos)
            continue

        d = (pos.get("direction") or "").upper()
        entry = pos.get("entry")
        if entry is None:
            ostalis.append(pos)
            continue

        srabotal = ((d == "LONG"  and high >= entry) or
                    (d == "SHORT" and low  <= entry))

        if srabotal:
            pos["status"] = "OPEN"
            pos["opened_at"] = bar_time      # ВРЕМЯ РЕАЛЬНОГО ВХОДА
            pos.pop("_ждёт_с", None)
            pos.pop("_ждёт_баров", None)
            dirty = True
            print(f"[ОРДЕР] ⚡ {pos.get('trader')} {d} АКТИВИРОВАН @ {entry} "
                  f"— рынок дошёл (H={high} L={low})")
            ostalis.append(pos)
            continue

        # PEREEZD_ZAYAVKI_V1: не пробил — сверяем со СТРУКТУРОЙ (Вильямс).
        _pz = _pereezd_zayavki(pos, md)
        if _pz == "CANCEL":
            print(f"[ОРДЕР] 🚫 {pos.get('trader')} {d} @ {entry} ОТМЕНЁН "
                  f"— цена вернулась к старту сигнала (Вильямс)")
            dirty = True
            continue          # снять заявку совсем
        if _pz == "MOVED":
            print(f"[ОРДЕР] 🔄 {pos.get('trader')} {d} ПЕРЕЕХАЛ @ "
                  f"{pos.get('entry')} — новый фрактал по тренду, стоп "
                  f"{pos.get('stop')} (Вильямс §8)")
            dirty = True
            ostalis.append(pos)
            continue          # PENDING на новом уровне

        # не сработал — считаем, сколько ждёт
        zhdyot = pos.get("_ждёт_баров", 0) + 1
        pos["_ждёт_баров"] = zhdyot
        dirty = True

        if zhdyot >= ORDER_EXPIRE_BARS:
            print(f"[ОРДЕР] 🚫 {pos.get('trader')} {d} @ {entry} ОТМЕНЁН — "
                  f"не пробит за {ORDER_EXPIRE_BARS} баров, структура "
                  f"протухла")
            continue          # выбрасываем — в ostalis не кладём

        ostalis.append(pos)

    if dirty:
        tstate["positions"] = ostalis
        save_trading_state(tstate)



# OTLOZHKA_SPREAD_V2: отложка + поправка на спред ────────────────────
def _spread_price(chain: dict) -> float:
    """Живой спред В ЦЕНЕ из бара терминала.
    spread приходит в пунктах (целое из MT5), point — размер тика."""
    md = chain.get("market_data", {}) or {}
    point = md.get("point") or 0.01
    spread_pts = (md.get("mfi", {}) or {}).get("spread")
    if spread_pts is None:
        spread_pts = 0.0
    return float(spread_pts) * float(point)


def _otlozhka_entry_stop(order: dict, chain: dict):
    """(entry, stop) с поправкой на спред по стороне сделки.
    Трейдер посчитал сырой entry/stop от СВОЕГО бара — добавляем зазор.

    LONG  (Buy Stop, по Ask):  entry = high + 2*спред; стоп снизу — как есть.
    SHORT (Sell Stop, по Bid): entry = low - 3 пункта; стоп сверху + 2*спред.
    Нет сырых чисел — возвращаем как пришло (не выдумываем).
    """
    d = (order.get("direction") or "").upper()
    entry = order.get("entry")
    stop = order.get("stop")
    md = chain.get("market_data", {}) or {}
    price = md.get("price", {}) or {}
    high = price.get("high")
    low = price.get("low")
    sp = _spread_price(chain)
    point = md.get("point") or 0.01  # POINT_NE_OPREDELEN_V1: было не
    # определено — NameError на КАЖДОМ вызове, падало безусловно
    punkt = 10 * float(point or 0.01)  # PUNKT_OT_POINT_V1: пункт = 10×point (любой инструмент)

    # ENTRY_NE_SLIPAETSYA_V1: спред добавляется К СОБСТВЕННОМУ входу
    # трейдера (entry уже посчитан ИМ по ЕГО канону — фрактал/
    # разворотный бар/откат), а не заменяется общим high/low бара
    # Совета. Иначе разные трейдеры на одном баре сливались бы в
    # одну цену — так и было найдено (три верда LONG = один entry).
    if d == "LONG":
        if entry is not None:
            entry = round(entry + 2 * sp, 6)     # Buy Stop, по Ask
        # стоп снизу по Bid — спред не мешает
    elif d == "SHORT":
        if entry is not None:
            entry = round(entry - 3 * punkt, 6)  # Sell Stop, запас 3 пункта
        if stop is not None:
            stop = round(stop + 2 * sp, 6)       # стоп сверху по Ask

    # ZAYAVKA_PRINT_FIX_V1: печать заявки — ПОТЕРЯНА при переписывании
    # v1->v2, вернул. Первый шаг ведения должен быть виден в консоли.
    print(f"[ОРДЕР] 📌 {order.get('trader')} {d} @ {entry} — "
          f"ЗАЯВКА поставлена (спред={sp:.2f}), ждём пробоя")

    return entry, stop


def _settle_positions(state: dict):
    """
    ЗАКРЫТИЕ позиций — физика, считает КОД (не LLM).
    Вызывается на каждом новом баре ДО Совета: рынок закрывает
    позиции независимо от решений агентов.

    Правила (LONG, v1):
      1. low <= stop      → закрыто по стопу, exit = stop
      2. exit_bell == true → закрыта ВСЯ пирамида, exit = close
         (выход всем объёмом — кусочничество ломает матожидание)

    Допущение D1/H4 paper: внутри бара сначала проверяется стоп
    (консервативно — худший сценарий первым).

    PnL:
      pnl_price = exit - entry            (ценовые единицы)
      pnl_r     = pnl_price / (entry - stop)   (результат в R —
                  главная метрика бэктеста)

    Журнал: economy/data/trading_pnl.jsonl (append-only) + Атлас.
    trading_state.json обновляется немедленно.
    """
    chain = state.get("chain_data", {})
    md    = chain.get("market_data", {})
    positions = chain.get("open_positions", []) or []
    if not positions or not md:
        return

    low       = md.get("price", {}).get("low")
    high      = md.get("price", {}).get("high")
    close     = md.get("price", {}).get("close")
    bell      = bool(md.get("exit_bell"))
    bar_time  = md.get("bar_time", "")
    symbol    = md.get("symbol", "")
    timeframe = md.get("timeframe", "")

    still_open, closed = [], []
    for pos in positions:
        # VASILY_ZASADA_V1: засада/заявка — не открытая позиция, закрывать
        # нечего (у WATCHING координаты входа заданы, но входа ещё НЕ БЫЛО).
        if pos.get("status") in ("WATCHING", "PENDING"):
            still_open.append(pos)
            continue
        entry = pos.get("entry")
        stop  = pos.get("stop")
        direction = pos.get("direction", "LONG")  # legacy позиции = LONG
        if entry is None or stop is None:
            still_open.append(pos)
            continue

        exit_price, reason = None, None
        # КАМЕНЬ 3: воля трейдера (CLOSE) — раньше стопа и колокола.  # EXECUTOR_MANAGE_HAND_V1
        if pos.get("manual_close") and close is not None:
            exit_price, reason = close, "MANUAL_CLOSE"
        # Стоп — зеркально по направлению
        if reason is None and direction == "LONG" and low is not None and low <= stop:
            exit_price, reason = stop, "STOP_LOSS"
        elif reason is None and direction == "SHORT" and high is not None and high >= stop:
            exit_price, reason = stop, "STOP_LOSS"
        elif reason is None and bell and close is not None:
            exit_price, reason = close, "EXIT_BELL"

        if exit_price is None:
            still_open.append(pos)
            continue

        # PnL зеркально: для шорта прибыль когда цена УПАЛА (entry > exit)
        # STOP_INITIAL_R_V1: R считается от ПЕРВОГО стопа, а не текущего.
        # Трейлинг двигает стоп в прибыль → |entry-stop| текущего
        # уходил в минус → risk<0 → pnl_r=None. R — мера риска НА ВХОДЕ.
        # PAKET_PYRAMIDA_V1: ПАКЕТНЫЙ расчёт пирамиды (вариант А).
        # risk0 — первоначальный риск ПЕРВОЙ ноги (entry vs stop_initial),
        # неизменен. pnl — от СРЕДНЕЙ цены пакета × множитель объёма
        # (lot/lot_base). Одиночная сделка: ea==entry, lot==lot_base →
        # формула вырождается в старую, ничего не меняется.
        stop_r    = pos.get("stop_initial", stop)  # первый стоп (неизменен)
        ea        = pos.get("entry_avg", entry)    # средняя цена пакета
        lot_base  = pos.get("lot_base") or pos.get("lot") or 1.0
        lot_full  = pos.get("lot") or lot_base
        try:
            mult = float(lot_full) / float(lot_base) if lot_base else 1.0
        except (TypeError, ZeroDivisionError):
            mult = 1.0
        if direction == "LONG":
            risk      = entry - stop_r          # риск от ПЕРВОЙ ноги
            pnl_price = round((exit_price - ea) * mult, 6)
        else:  # SHORT
            risk      = stop_r - entry
            pnl_price = round((ea - exit_price) * mult, 6)
        if risk <= 0:
            # DIAGNOSTIKA_NONE_R_V1: риск обнулился — печатаем ВСЁ для
            # диагноза за один взгляд, не полчаса реконструкции.
            print(
                f"[МАЯК] ⚠️  RISK<=0 → pnl_r=None. Разбор:\n"
                f"  trader={pos.get('trader')} dir={direction} "
                f"entry={entry} stop(текущий)={stop}\n"
                f"  stop_initial(сырое из pos)={pos.get('stop_initial')}"
                f" (None → поля НЕТ, позиция СТАРАЯ, без патча)\n"
                f"  stop_r(использован)={stop_r}  risk={risk}\n"
                f"  entry_avg={pos.get('entry_avg')} "
                f"lot_base={pos.get('lot_base')} lot={pos.get('lot')}\n"
                f"  trailed={pos.get('trailed')} "
                f"dolivok={pos.get('dolivok')} "
                f"entry_fractal_idx={pos.get('entry_fractal_idx')} "
                f"(если есть — была активна отложка/переезд)"
            )
        pnl_r     = round(pnl_price / risk, 4) if risk > 0 else None

        record = {
            "ts":         datetime.now().isoformat(),
            "closed_at":  bar_time,
            "symbol":     symbol,
            "timeframe":  timeframe,
            "trader":     pos.get("trader"),
            "magic":      pos.get("magic"),
            "entry":      entry,
            "stop":       stop,
            "exit":       exit_price,
            "lot":        pos.get("lot"),
            # DIAGNOZ_PRAVDA_V1: следы пирамиды в записи — отчёт увидит доливы
            "lot_base":   pos.get("lot_base"),
            "dolivok":    pos.get("dolivok", 0),
            "mode":       pos.get("mode", "PAPER"),
            "opened_at":  pos.get("opened_at"),
            "close_reason": reason,
            "pnl_price":  pnl_price,
            "pnl_r":      pnl_r,
        }
        closed.append(record)

        PNL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PNL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # RUKA_DOPISYVAYUSHCHAYA_V1: ИСХОД — обратно в тетрадь
        # хозяина. Без этого он читает свои прошлые входы и НЕ
        # ЗНАЕТ, чем они кончились: «я так уже делал» звучит
        # доводом, хотя стоило −1.0R. Дневник без результата —
        # список намерений, а не опыт.
        try:
            _dopisat_v_dnevnik(pos.get("trader"), entry,
                               pnl_r, reason, bar_time)
        except Exception as _de:
            print(f"[ТЕТРАДЬ] ⚠️  {_de}")

        # ARKHIV_SIGNATURA_ISHODA_V1: сигнатура сенсоров НА МОМЕНТ ВХОДА,
        # разворачиваем из "стол_входа" (уже хранится на позиции) —
        # без неё закрытые сделки никогда не совпадали ни с одним
        # запросом Архивариуса (у них не было полей для сравнения).
        _svh = pos.get("стол_входа") or {}
        _write_atlas({
            "event":       "POSITION_CLOSED",
            "trader":      pos.get("trader"),
            "close_reason": reason,
            "pnl":         pnl_price,
            "pnl_r":       pnl_r,
            "symbol":      symbol,
            "timeframe":   timeframe,
            "t1_status":     (_svh.get("iskra") or {}).get("t1_status"),
            "morj_status":   (_svh.get("morj") or {}).get("morj_status"),
            "panic_phase":   (_svh.get("panic") or {}).get("panic_phase"),
            "fractal_valid": (_svh.get("hans") or {}).get("fractal_valid"),
        })

        # РУКА КЛАДУЩАЯ (ARKHIV_HAND_GIVING): тяжёлая сделка (|pnl_r|>=2R)
        # → урок в память города через Оле. Рутина (<2R) — только Атлас.
        # Безопасно: Оле упала → сделка уже записана, цикл цел.
        _arkhiv_to_city(record)
        # ISKRA_FAIR_JUDGEMENT_V1: СУД ИСКРЫ ПО ДЕЛУ — по pnl_r закрытой сделки.
        _judge_iskra_by_result(pos, pnl_r)
        # ENGINE_ONE_DOOR_V1: СУД ТРЕЙДЕРА — он решил входить, он отвечает.
        # Минус ПРОТИВ ветра → bad_work. По ветру/штиль → честный минус.
        _judge_trader_by_result(pos, pnl_r)
        print(f"[SETTLE] {'🔔' if reason == 'EXIT_BELL' else '🛑'} "
              f"{pos.get('trader')} закрыт ({reason}): "
              f"pnl={pnl_price} ({pnl_r}R)")

    if closed:
        chain["open_positions"] = still_open
        tstate = load_trading_state()
        tstate["positions"] = still_open
        save_trading_state(tstate)
        print(f"[SETTLE] 📒 Закрыто: {len(closed)}, осталось: {len(still_open)}")


def _prepare_trade_setup(state: dict):
    """
    Готовит цены входа/стопа для Трибунала. СЧИТАЕТ КОД — трейдеры
    читают setup как ФАКТ рынка. Суждение "входить или нет" — за ними.

    Канон Котина/Вильямса ("Торговый Хаос", гл. 6):
      ВХОД   = ПРОБОЙ приседающего (Squat = +Vol, −MFI).
               LONG:  Buy Stop  над high приседающего + тик
               SHORT: Sell Stop под low  приседающего − тик
      НАПРАВЛЕНИЕ определяется сигналом Искры:
               divergence_ao=True → LONG  (Точка Ноль, "родится новый")
               exit_bell=True     → SHORT (5-я волна выдохлась)
               иначе              → setup пустой (нет ставки)
      СТОП   = подушка безопасности Вильямса — экстремум второго
               бара назад + один тик, в сторону против сделки.
               Это защита от "пьяного рынка", а не точка входа.
      TP     = None — фикс-тейка у Вильямса нет, выход по exit_bell
               всем объёмом (в _settle_positions).

    ЗАКОН ЯДРА: ничего не решаем за трейдеров. Разворотный приседающий
    или мерный, брать или не брать — это их работа, для того их и трое.
    Здесь только цены. Если приседающего нет — entry=None, трейдеры
    вернут REJECTED с причиной NO_SQUAT.
    """
    chain = state.get("chain_data", {})
    md    = chain.get("market_data", {})

    sq_block = md.get("squat", {}) or {}
    squat    = sq_block.get("last_squat")
    bullish  = bool(md.get("divergence_ao"))
    bearish  = bool(md.get("exit_bell"))
    price_lo = md.get("price", {}).get("low")
    price_hi = md.get("price", {}).get("high")

    # ── Направление по Искре ─────────────────────────────────
    if bullish and not bearish:
        direction = "LONG"
    elif bearish and not bullish:
        direction = "SHORT"
    else:
        direction = None  # нет разворотного контекста — нет setup

    # ── Тик (минимальный шаг цены) ───────────────────────────
    # Приходит ИЗ ТЕРМИНАЛА вместе с market_data (md["point"]).
    # Никаких встроенных таблиц тикеров: точность знает брокер.
    # Fallback на крайний случай, если point не дошёл (старый CSV-путь).
    tick = md.get("point") or 0.00001

    # ── Вход: пробой приседающего ────────────────────────────
    entry = None
    if squat and direction == "LONG":
        entry = round(squat["high"] + tick, 6)
    elif squat and direction == "SHORT":
        entry = round(squat["low"] - tick, 6)

    # ── Стоп: подушка безопасности (экстремум 2-го бара назад) ─
    # Канон: второй бар назад от рассматриваемого, со старшего ТФ.
    # У нас в market_data только один ТФ — берём 2-й бар назад
    # текущего ТФ как ближайшую к канону аппроксимацию. По-настоящему
    # двухтаймфреймовая подушка ляжет, когда hooks начнёт читать HTF.
    stop = None
    bars2_low  = chain.get("_bar_back2_low")
    bars2_high = chain.get("_bar_back2_high")
    if direction == "LONG" and bars2_low is not None:
        stop = round(bars2_low - tick, 6)
    elif direction == "SHORT" and bars2_high is not None:
        stop = round(bars2_high + tick, 6)
    # Fallback: пока on_before_run не положит _bar_back2_* —
    # используем текущий low/high как грубую защиту, чтобы
    # setup не был совсем пустым на первом прогоне после патча.
    if stop is None:
        if direction == "LONG" and price_lo is not None:
            stop = round(price_lo - tick, 6)
        elif direction == "SHORT" and price_hi is not None:
            stop = round(price_hi + tick, 6)

    chain["trade_setup"] = {
        "direction":    direction,
        "entry":        entry,
        "stop":         stop,
        "tp":           None,
        "lot_fraction": 0.33,
        "source":       "squat" if squat else None,
    }
    if entry is None:
        print(f"[SETUP] ⛔ нет setup: "
              f"squat={'есть' if squat else 'нет'}, "
              f"искра={direction or 'NOT_FOUND'}")
    else:
        print(f"[SETUP] 🎯 {direction}: entry={entry}, stop={stop}, "
              f"tp=None (exit_bell), вход по приседающему")


def _prepare_atlas_digest(state: dict):
    """
    Готовит выжимку из Атласа Ошибок для A05 Архивариуса.
    ЧИСЛА СЧИТАЕТ КОД — Архивариус-LLM только интерпретирует.

    Сигнатура похожести: (t1_status, morj_status, panic_phase, entry_trigger).
    success_rate — доля pnl > 0 среди ЗАКРЫТЫХ сделок выборки.
    """
    chain = state.get("chain_data", {})
    # ARKHIV_DIGEST_PATCHED · сигнатура = сумма 4 сенсоров (не один Ганс)
    signature = {
        "t1_status":     chain.get("t1_status"),
        "morj_status":   chain.get("morj_status"),
        "panic_phase":   chain.get("panic_phase"),
        "fractal_valid": chain.get("fractal_valid"),
    }
    # Считает движок Архивариуса — один источник правды для
    # кода и LLM. Внутри: правильная сигнатура + arkhiv_confidence.
    try:
        _b_arkhiv = _slot_brain("контора", "архивариус")
        if _b_arkhiv is None:
            raise RuntimeError("мозг архивариуса ещё не в слоте")
        chain["atlas_digest"] = _b_arkhiv.build_digest(signature)
        print(f"[ATLAS] 📖 Digest (движок): "
              f"sample={chain['atlas_digest']['sample_size']}, "
              f"conf={chain['atlas_digest']['arkhiv_confidence']}")
        return
    except Exception as _e:
        print(f"[ATLAS] ⚠️  движок недоступен ({_e}) — старый расчёт")

    matches = []
    if ATLAS_PATH.exists():
        with open(ATLAS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entry = rec.get("entry", rec)
                if all(entry.get(k) == v for k, v in signature.items()
                       if v is not None):
                    matches.append(entry)

    closed   = [m for m in matches if m.get("pnl") is not None]
    wins     = [m for m in closed if (m.get("pnl") or 0) > 0]
    success  = round(len(wins) / len(closed), 4) if closed else 0.0

    # Самая частая причина среди отказов/убытков
    reasons: dict[str, int] = {}
    for m in matches:
        r = m.get("reason")
        if r and (m.get("verdict") == "REJECTED" or (m.get("pnl") or 0) < 0):
            reasons[r] = reasons.get(r, 0) + 1
    top_reason = max(reasons, key=lambda k: reasons[k]) if reasons else "none"  # HOOKS_TYPING_V2

    chain["atlas_digest"] = {
        "sample_size":        len(matches),
        "closed_trades":      len(closed),
        "success_rate":       success,
        "top_failure_reason": top_reason,
        "recent_cases":       matches[-5:],
    }
    print(f"[ATLAS] 📖 Digest для A05: sample={len(matches)}, "
          f"closed={len(closed)}, success={success}")


def _persist_trading_state(state: dict):
    """
    Собирает из результатов прогона то что должно пережить прогон:
      — состояние Искры (t1_status, zero_point_price, history_dna)
      — открытые позиции (из execution_log A09)
    И сохраняет в trading_state.json.

    Логика закрытия позиций (по exit_bell / стопу) — ШАГ 8,
    промт Исполнителя. Здесь только хранение.
    """
    results = state.get("results", {})
    chain   = state.get("chain_data", {})
    tstate  = load_trading_state()

    # ── Состояние Искры ──
    iskra_out = (results.get("A01", {}).get("meta", {}) or {}) \
        .get("my_output", {}) or {}
    if iskra_out:
        tstate["iskra"]["t1_status"] = \
            iskra_out.get("t1_status", tstate["iskra"]["t1_status"])
        tstate["iskra"]["zero_point_price"] = \
            iskra_out.get("zero_point_price",
                          tstate["iskra"]["zero_point_price"])
        if iskra_out.get("history_dna"):
            tstate["iskra"]["history_dna"] = iskra_out["history_dna"]
    elif chain.get("t1_status"):
        # fallback: Искра писала прямо в chain_data
        tstate["iskra"]["t1_status"] = chain["t1_status"]
        if chain.get("zero_point_price") is not None:
            tstate["iskra"]["zero_point_price"] = chain["zero_point_price"]
        if chain.get("history_dna"):
            tstate["iskra"]["history_dna"] = chain["history_dna"]

    # ── Открытые позиции: новые APPROVED из execution_log ──
    a09_out = (results.get("A09", {}).get("meta", {}) or {}) \
        .get("my_output", {}) or {}
    exec_log = a09_out.get("execution_log", []) or []
    bar_time = chain.get("market_data", {}).get("bar_time", "")

    # VASILY_ZASADA_V1: засада Консерватора рождается ДО обычных входов.
    # action==WATCH → WATCHING-запись (наблюдение по условию, не заявка).
    for order in exec_log:
        if (order.get("action") or "").upper() != "WATCH":
            continue
        if order.get("magic") != 100003:   # только Консерватор (A08)
            continue
        _nabl = _rodit_nablyudenie_vasily(order, chain)
        # пустая засада (нет опоры/стопа) — не рождаем, это болтовня
        if _nabl.get("watch_opora") is None or _nabl.get("stop") is None:
            print(f"[ЗАСАДА] ⚠️  {order.get('trader')} назвал WATCH без "
                  f"опоры/стопа — засада пуста, отклонена")
            continue
        # дубль засады того же магика не плодим
        _est = any(p.get("magic") == _nabl.get("magic")
                   and p.get("status") == "WATCHING"
                   for p in tstate.get("positions", []))
        if _est:
            continue
        tstate.setdefault("positions", []).append(_nabl)
        print(f"[ЗАСАДА] 👁  {order.get('trader')} {_nabl['direction']} встал "
              f"в засаду: опора {_nabl['watch_opora']}, вход {_nabl['entry']}, "
              f"стоп {_nabl['stop']} (ждёт волну 1 + отскок)")

    for order in exec_log:
        if order.get("verdict") != "APPROVED":
            continue
        if order.get("status") not in ("PAPER", "LIVE"):
            continue
        tstate["positions"].append({
            "trader":    order.get("trader"),
            "magic":     order.get("magic"),
            "direction": order.get("direction"),   # FIX: было потеряно — шорт закрывался как лонг
            # OTLOZHKA_SPREAD_V2: entry/stop с поправкой на спред.
            # LONG: high+2спреда (по Ask). SHORT: low-0.30, стоп+2спреда.
            # stop_initial = спред-поправленный стоп (R от реального стопа).
            **dict(zip(("entry", "stop", "stop_initial"),
                      (lambda es: (es[0], es[1], es[1]))(
                          _otlozhka_entry_stop(order, chain)))),
            "tp":        order.get("tp"),
            "lot":       order.get("lot"),
            # PAKET_PYRAMIDA_V1: поля ПАКЕТА пирамиды. entry_avg —
            # средневзвешенная цена входа (растёт при ADD). lot_base —
            # объём первой ноги (для множителя R). Одиночная сделка:
            # entry_avg==entry, lot==lot_base → расчёт как раньше.
            **dict(zip(("entry_avg", "lot_base"),
                      (lambda es: (es[0], order.get("lot")))(
                          _otlozhka_entry_stop(order, chain)))),
            # OTLOZHKA_SPREAD_V2: ВСЕГДА отложка. Ждём пробоя, никто не
            # входит по рынку. opened_at поставит _aktivirovat_ordera
            # в миг реального пробоя (время ИСТИННОГО входа).
            "status":    "PENDING",
            "_ждёт_баров": 0,
            # PEREEZD_ZAYAVKI_V1: заявка помнит, ОТ КАКОГО фрактала родилась,
            # и старт сигнала (противоположный фрактал) — для переезда/снятия.
            **_zapomnit_fraktal_starta(order, chain),
            "mode":      order.get("status"),       # PAPER | LIVE
            # ENGINE_ONE_DOOR_V1: позиция запоминает ВЕТЕР входа (global_bias
            # на баре входа). На закрытии суд трейдера сверит: по ветру или против.
            "entry_bias": chain.get("market_data", {}).get("global_bias"),
            # SUD_SENSOROV_V2 · SLEPOK_IZ_CHAIN_V1: СЛЕПОК СТОЛА — показания
            # всех четырёх сенсоров на баре ВХОДА. Стол перетирается каждый
            # бар: судить сенсора по чужому бару было бы клеветой.
            #
            # ИСТОЧНИК — chain_data, НЕ tstate. tstate = load_trading_state()
            # это СТАРЫЙ ФАЙЛ С ДИСКА (в _DEFAULT_STATE есть только "iskra",
            # ключей morj/panic/hans там нет вовсе) — слепок приезжал пустым,
            # и судья сенсоров молча выходил на 28 сделках подряд.
            # chain_data — то, чем Совет ДУМАЛ на этом баре. Ровно оттуда
            # берут соседи: _log_rejections и _prepare_atlas_digest.
            "стол_входа": {
                "iskra": {
                    "t1_status":        chain.get("t1_status"),
                    "zero_point_price": chain.get("zero_point_price"),
                    # компас: без него не понять, звала ли Вера В СТОРОНУ
                    # сделки (BULL зовёт в LONG, но НЕ зовёт в SHORT)
                    "trend_direction":  (chain.get("market_data", {}) or {})
                                        .get("global_bias"),
                },
                "morj": {
                    "morj_status":      chain.get("morj_status"),
                    "wave_1_validated": chain.get("wave_1_validated"),
                },
                "panic": {
                    "panic_phase":      chain.get("panic_phase"),
                },
                "hans": {
                    "fractal_valid":    chain.get("fractal_valid"),
                    # сторона фрактала — та же логика, что у компаса Веры
                    "fractal_side":     chain.get("hans_direction")
                                        or chain.get("fractal_side"),
                    "fractal_price":    chain.get("fractal_price"),
                },
            },
            "pnl":       None,
        })

    save_trading_state(tstate)


def _extract_verdict(agent_result: dict, key: str) -> Optional[str]:
    """Извлекает вердикт из результата агента."""
    if not agent_result:
        return None
    meta   = agent_result.get("meta", {}) or {}
    my_out = meta.get("my_output", {}) or {}
    return my_out.get(key) or agent_result.get("text", "")[:10] or None


# ════════════════════════════════════════════════════════════
# РУКА КЛАДУЩАЯ (ARKHIV_HAND_GIVING) — тяжёлое → память города
# ─────────────────────────────────────────────────────────────
# Архивариус — Оле Торгового Квартала. Крупная сделка (|pnl_r|>=2R)
# не оседает только в тетради цеха — урок ложится в вечную память
# города через Оле (remember). Рутина (<2R) остаётся в Атласе.
# Зов Оле безопасен: упала → торговый цикл цел.
# ════════════════════════════════════════════════════════════

# Порог веса: крупный ход. Ниже — рутина, в город не идёт.
_HEAVY_R = 2.0


def _arkhiv_to_city(record: dict):
    """
    РУКА КЛАДУЩАЯ — не построена в этом городе.

    В старом мире (-2) тяжёлая сделка (|pnl_r|>=2R) уходила в
    городскую память через Олю (studio.memory_tools.remember).
    В Грондхейме городская память (Оля) решением 03.07 пока НЕ
    строится ("каждый держит свой архив сам" — Летопись §4а).
    Честный no-op, не притворяется рабочей трубой, не зовёт то,
    чего на диске нет. Когда городская память будет решена
    строиться — сюда ляжет новый вызов, не заглушка.
    """
    return


def _judge_iskra_by_result(pos: dict, pnl_r):
    """
    СУД СЕНСОРОВ — их нога Опыта. Построена.   # SUD_SENSOROV_V2

    (Имя историческое: судит теперь ВСЕХ ЧЕТВЕРЫХ — Веру, Моржа, Паникёра,
    Ганса. Зовётся из _settle_positions на каждой закрытой сделке; сигнатуру
    ради имени не ломаем.)

    Слово Шефа: опыт сенсора — это КАК ОН РАБОТАЕТ НАД СВОИМИ ОШИБКАМИ.
    Он не теряет денег — он промахивается СЛОВОМ. Судит его исход, до
    которого он сам не дожил: сделка трейдера, случившаяся после его слова.

    Судит КОД, не LLM (числа не галлюцинируют). «Звал» — значит показание
    тянуло В СТОРОНУ сделки (компас Веры, сторона фрактала Ганса, фаза
    толпы). Молчал и сделка в минус — не его промах, в опыт не идёт.

    Это НЕ старый sync_to_dna: тот качал ДНК за «хорошую работу» — маятник,
    который Чертёж (Гл.4.2) зовёт НЕ-опытом. Здесь — вывод СЛОВАМИ, который
    сенсор прочтёт перед следующим баром и сможет с ним спорить.

    Упадёт — торговый цикл цел, сделка в журнале записана.
    """
    # MAYAK_SENSOROV_V1 — ВРЕМЕННЫЙ МАЯЧОК (снять после разбора)
    print(f"[МАЯК] судья сенсоров вызван: pnl_r={pnl_r}, "
          f"trader={pos.get('trader')}, dir={pos.get('direction')}")
    print(f"[МАЯК] ключи позиции: {list(pos.keys())}")
    stol = pos.get("стол_входа") or {}
    print(f"[МАЯК] стол_входа: {stol}")
    if not stol or pnl_r is None:
        print("[МАЯК] ⛔ ВЫХОД: слепка нет или pnl_r=None")
        return
    try:
        import sys as _s
        from pathlib import Path as _P
        _b = str(_P(__file__).resolve().parent)
        if _b not in _s.path:
            _s.path.insert(0, _b)
        from nositel import SENSOR_SLOTS, sudit_sensora, zapisat_vyvod_pare
        import nositel as _nmod
        print(f"[МАЯК] nositel загружен. UCHIT={getattr(_nmod, 'UCHIT', 'НЕТ ПОЛЯ')}")

        direction = pos.get("direction")
        bar = pos.get("opened_at") or ""

        # В якорь сенсора должен лечь ЧЕЛОВЕК, а не роль: Вера помнит, что
        # вошёл ИЛЬЯ, а не «Avanturist». Мост уже умеет: magic → носитель.
        trader = pos.get("trader") or ""
        try:
            from cartridge_registry import resolve_by_magic
            _t = resolve_by_magic(pos.get("magic"))
            if _t and _t.get("имя"):
                trader = _t["имя"]
        except Exception:
            pass

        from nositel import _zval, dyhnut_slovom   # MAYAK_SENSOROV_V1
        for key, slot in SENSOR_SLOTS.items():
            pokazanie = stol.get(key) or {}
            zval = _zval(key, pokazanie, direction)
            vyvod = sudit_sensora(key, pokazanie, direction, pnl_r, trader, bar)
            print(f"[МАЯК] {slot} {key}: показание={pokazanie} "
                  f"звал={zval} вывод={'ЕСТЬ' if vyvod else 'пусто'}")
            if vyvod:
                r = zapisat_vyvod_pare("торговый_хаос", slot, vyvod, pnl_r=pnl_r)
                print(f"[МАЯК] {slot} ЗАПИСЬ → {r}")
                continue
            if zval:
                r = dyhnut_slovom("торговый_хаос", slot, pnl_r)
                print(f"[МАЯК] {slot} ДЫХАНИЕ → {r}")
            else:
                print(f"[МАЯК] {slot} молчал — не судим, не дышит")
    except Exception as e:
        print(f"[СУД] ⚠️  суд сенсоров не сработал ({e}) — сделка в журнале цела")
    return

def _judge_trader_by_result(pos: dict, pnl_r):
    """
    СУД ТРЕЙДЕРА — НОГА ОПЫТА. Построена.   # JUDGE_TRADER_NOSITEL_V1

    Рынок рассудил (Чертёж: САМЫЙ чистый судья, без апелляций) — вывод
    оседает в НОСИТЕЛЯ, не в труп роли из -2:
        magic позиции → resolve_by_magic → житель (Илья/Брут/Василий)
        → вывод по Котину → в ЕГО ЖЕ Anchor_Points (лимит 7-10)

    Это НЕ старый маятник sync_to_dna: тот качал состояние по факту
    (Чертёж Гл.4.2 прямо зовёт его НЕ-опытом, «обучение первого уровня,
    без понимания»). Здесь — ВЫВОД словами, который трейдер прочтёт
    перед следующей сделкой и сможет с ним спорить.

    ОПЫТ ≠ ПАМЯТЬ (Чертёж): факт КАЖДОЙ сделки уже лёг в pnl.jsonl и в
    дневник роли — это память. В якоря (их всего 7-10) идёт только
    значимое: минус ПРОТИВ ветра (тот самый систематический стоп) и
    любая крайность |pnl_r| >= 2R. Рутина в опыт не лезет.

    pnl.jsonl эта функция не трогает. Упадёт — торговый цикл цел.
    """
    try:
        import sys as _s
        from pathlib import Path as _P
        _b = str(_P(__file__).resolve().parent)
        if _b not in _s.path:
            _s.path.insert(0, _b)
        from nositel import (sudit_po_kotinu, zapisat_vyvod,
                             dyhnut_sdelkoy)   # DYHANIE_SDELKI_V1

        vyvod = sudit_po_kotinu(
            pos.get("direction"),
            pos.get("entry_bias"),      # ветер на баре ВХОДА (уже в позиции)
            pnl_r,
            pos.get("close_reason"),
            pos.get("opened_at"),
        )
        if not vyvod:
            # DYHANIE_SDELKI_V1: РУТИНА — в ОПЫТ не идёт (якорей 7-10, это не
            # журнал), но ЗАРЯД обязан двинуться: Чертёж Гл.4.4 — «единичное
            # событие меняет заряд, не фильтр». Раньше здесь стоял голый
            # return, и человек терял деньги, НИЧЕГО НЕ ЧУВСТВУЯ.
            dyhnut_sdelkoy(pos.get("magic"), pnl_r)
            return
        # значимая сделка: вдох уже внутри zapisat_vyvod — двойного нет
        zapisat_vyvod(pos.get("magic"), vyvod, pnl_r=pnl_r)
    except Exception as e:
        print(f"[СУД] ⚠️  нога Опыта не сработала ({e}) — сделка в журнале цела")
    return



def _write_atlas(entry: dict):
    """Записывает событие в Атлас Ошибок."""
    ATLAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now().isoformat(), "entry": entry}
    with open(ATLAS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[ATLAS] 📝 Записано: {entry.get('event', '?')}")


def _print_market_summary(md: dict):
    """Печатает краткую сводку market_data в консоль."""
    print(f"\n[TRADING] 📊 РЫНОЧНАЯ СВОДКА {md['symbol']} {md['timeframe']}")
    print(f"  Бар:      {md['bar_time']}")
    p = md["price"]
    print(f"  Цена:     O={p['open']} H={p['high']} L={p['low']} C={p['close']}")
    al = md["alligator"]
    state_str = ("СПИТ" if al["sleeping"] else
                 "MATURE" if al["mature"] else f"открыт {al['bars_open']} баров")
    print(f"  Аллигатор: Jaw={al['jaw']} Teeth={al['teeth']} "
          f"Lips={al['lips']} [{state_str}]")
    ao = md["ao"]
    print(f"  AO:       {ao['value']} (prev={ao['prev_value']}) "
          f"dir={ao['direction']} zero={ao['crossed_zero']}")
    ac = md["ac"]
    print(f"  AC:       {ac['value']} dir={ac['direction']}")
    print(f"  MFI:      {md['mfi']['type']} vol={md['mfi']['volume']}")
    print(f"  Фракталы: ▲{md['fractals']['count_up']} ▼{md['fractals']['count_down']}")
    if md["divergence_ao"]: print("  ⚡ ДИВЕРГЕНЦИЯ AO (бычья) — Точка Ноль!")
    if md["exit_bell"]:     print("  🔔 EXIT BELL — импульс выдохся")
    print()


def _calc_missed_moves(trader_name: str, all_records: list) -> dict:
    """
    Пропущенные движения трейдера.

    Смотрим все записи PnL — если в тот же момент другой трейдер
    взял прибыль, а этот не участвовал (нет записи с тем же
    opened_at) — это пропуск.

    Возвращает: {"count": N, "last_symbol": "XAUUSD",
                 "last_r": 2.0, "last_date": "..."}
    """
    if not all_records:
        return {"count": 0}

    # Группируем по opened_at — момент когда был сигнал
    by_moment = {}
    for rec in all_records:
        moment = rec.get("opened_at", "")
        if not moment:
            continue
        if moment not in by_moment:
            by_moment[moment] = []
        by_moment[moment].append(rec)

    missed = []
    for moment, recs in by_moment.items():
        # Участвовал ли наш трейдер в этом моменте
        our = [r for r in recs if r.get("trader") == trader_name]
        others = [r for r in recs
                  if r.get("trader") != trader_name
                  and (r.get("pnl_r") or 0) > 1.0]  # другой взял > 1R

        if not our and others:
            # Наш не участвовал, другой взял прибыль
            best = max(others, key=lambda r: r.get("pnl_r", 0))
            missed.append({
                "symbol":  best.get("symbol", "?"),
                "pnl_r":   best.get("pnl_r", 0),
                "trader":  best.get("trader", "?"),
                "date":    moment[:16] if moment else "?",
            })

    if not missed:
        return {"count": 0}

    last = missed[-1]
    return {
        "count":       len(missed),
        "last_symbol": last["symbol"],
        "last_r":      last["pnl_r"],
        "last_trader": last["trader"],
        "last_date":   last["date"],
    }


def _prepare_trader_state(state: dict, agent_id: str):
    """
    Читает trading_pnl.jsonl и собирает живое состояние
    конкретного трейдера перед его вызовом.

    Факты:
      — последние 5 сделок в R
      — серия убытков/побед подряд
      — итог последних 10 в R
      — пропущенные движения (другие взяли, ты нет)

    Никаких условий — трейдер читает и сам решает.
    """
    trader_name = {
        "A06": "BRUT",
        "A07": "AVANTURIST",
        "A08": "KONSERVATOR",
    }.get(agent_id)
    if not trader_name:
        return

    cd = state.setdefault("chain_data", {})

    if not PNL_PATH.exists():
        cd["trader_state"] = "Торговой истории нет. Первый сигнал."
        return

    # Читаем ВСЕ записи (нужны для пропущенных движений)
    all_records = []
    our_records = []
    try:
        with open(PNL_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("pnl_r") is not None:
                        all_records.append(rec)
                        if rec.get("trader") == trader_name:
                            our_records.append(rec)
                except json.JSONDecodeError:
                    continue
    except OSError:
        cd["trader_state"] = "Не могу прочитать журнал сделок."
        return

    if not our_records:
        cd["trader_state"] = f"Сделок {trader_name} в журнале нет. Чистый старт."
        return

    last10 = our_records[-10:]
    last5  = our_records[-5:]

    # Серия убытков подряд
    consecutive_loss = 0
    for rec in reversed(our_records):
        if (rec.get("pnl_r") or 0) < 0:
            consecutive_loss += 1
        else:
            break

    # Серия побед подряд
    consecutive_win = 0
    for rec in reversed(our_records):
        if (rec.get("pnl_r") or 0) > 0:
            consecutive_win += 1
        else:
            break

    total_r_10 = round(sum(r.get("pnl_r", 0) for r in last10), 2)

    last5_str = "  ".join(
        f"{'+' if r.get('pnl_r', 0) > 0 else ''}{r.get('pnl_r', 0)}R"
        f"({r.get('close_reason', '?')})"
        for r in last5
    )

    last_ts      = our_records[-1].get("closed_at") or our_records[-1].get("ts", "")
    total_trades = len(our_records)

    lines = [
        f"Последние 5 сделок: {last5_str}",
        f"Итог последних 10: {'+' if total_r_10 >= 0 else ''}{total_r_10}R",
        f"Всего сделок в журнале: {total_trades}",
        f"Последняя сделка: {last_ts[:16] if last_ts else 'неизвестно'}",
    ]

    if consecutive_loss >= 2:
        lines.append(f"Серия убытков подряд: {consecutive_loss}")
    if consecutive_win >= 2:
        lines.append(f"Серия побед подряд: {consecutive_win}")

    # ── Пропущенные движения ──────────────────────────────
    missed = _calc_missed_moves(trader_name, all_records)
    if missed.get("count", 0) > 0:
        lines.append(
            f"Сильных движений без тебя: {missed['count']}"
        )
        lines.append(
            f"Последний пропуск: {missed['last_symbol']} "
            f"+{missed['last_r']}R — взял {missed['last_trader']} "
            f"({missed['last_date']})"
        )

    cd["trader_state"] = "\n".join(lines)
    print(f"[STATE] 📊 {agent_id}: {consecutive_loss} убытков подряд, "
          f"итог 10: {total_r_10}R, пропущено: {missed.get('count', 0)}")



# ════════════════════════════════════════════════════════════
# ЖИВОЙ ПОТОК ИЗ MT5 — линзы агентов и точки входа для насоса
# ─────────────────────────────────────────────────────────────
# Сюда переехали мозги из main.py: интерпретация рыночных фактов
# через линзы агентов (Искра / Морж / Ганс / Паникёр). Это их
# законное место — шлюз между ядром и Советом. Насос (mt5_feed.py)
# знает только две публичные функции отсюда:
#     scan_for_feed()     — режим data  (сводка для дашборда/индикатора)
#     run_live_council()  — режим council (живой Совет A01–A09)
# ════════════════════════════════════════════════════════════

def _suppress(fn, *a, **kw):
    """Глушит print() ядра при пакетном сканировании истории."""
    import io, sys
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return fn(*a, **kw)
    finally:
        sys.stdout = old


def _hans_breakout(md: dict, window: list) -> Optional[str]:
    """
    Линза Ганса: ПРОБОЙ фрактала вне пасти (момент удара, не координата).
      LONG:  верхний фрактал был выше Jaw, и close пересёк его уровень
             снизу вверх на этом баре (close[-2] < fp <= close[-1]).
      SHORT: нижний фрактал был ниже Jaw, close пересёк сверху вниз.
    Возвращает "LONG" / "SHORT" / None.

    Формирование фрактала — лишь координата. Сигнал рождается в момент
    пробоя: рынок принял решение, Волна 3 жива.
    """
    jaw = md.get("alligator", {}).get("jaw")
    if jaw is None or len(window) < 2:
        return None
    up   = md.get("fractals", {}).get("last_up")
    down = md.get("fractals", {}).get("last_down")
    c_prev = window[-2]["close"]
    c_cur  = window[-1]["close"]
    if up and up.get("price", 0) > jaw:
        fp = up["price"]
        if c_prev < fp <= c_cur:
            return "LONG"
    if down and down.get("price", 0) < jaw:
        fp = down["price"]
        if c_prev > fp >= c_cur:
            return "SHORT"
    return None


def _panic_phase(mfi_type: str) -> str:
    """Линза Паникёра: фаза толпы по типу MFI."""
    return {
        "SQUAT": "LIQUIDATION",
        "GREEN": "FOMO",
        "FADE":  "DISBELIEF",
    }.get(mfi_type, "NEUTRAL")


def scan_for_feed(bars: list, symbol: str, timeframe: str, point: float) -> dict:
    """
    РЕЖИМ DATA — пакетное сканирование истории для индикатора/дашборда.
    Ноль реальных ордеров. Ноль LLM. Только факты ядра через линзы агентов.

    point ОБЯЗАТЕЛЕН и приходит из терминала (symbol_info.point).
    Возвращает {"signals": [...], "live": {...}} — насос пишет это в json.
    """
    signals = []
    prev_sleeping = True

    for i in range(40, len(bars)):
        window = bars[max(0, i - 199):i + 1]
        md = _suppress(build_market_data, window,
                       symbol=symbol, timeframe=timeframe, point=point)
        if not md:
            continue

        # NECRON_DIVERGENCE_V1: "divergent_bar" (старая bdb_strong) снята
        # целиком. Разворотный бар теперь читаем из wave_form.bdb_dir —
        # то же поле, что использует живой спуск Искры. "bdb_candidate"
        # больше не существует как отдельное понятие (новая формула не
        # различает кандидата и подтверждённого — либо сошлось всё сразу,
        # либо нет), поле оставлено в сигнале как синоним bdb_strong,
        # чтобы не ломать формат для читателей дашборда.
        wf       = md.get("wave_form", {})
        sleeping = bool(md.get("alligator", {}).get("sleeping", True))
        ao       = md.get("ao", {})

        # Искра
        bdb_strong    = bool(wf.get("bdb_dir"))
        bdb_candidate = bdb_strong
        direction     = wf.get("bdb_dir")
        confirmed     = bool(ao.get("crossed_zero") and ao.get("zero_dir") == "UP")

        # Морж: только что проснулся
        alligator_wake = (not sleeping and prev_sleeping)

        # Ганс: пробой фрактала вне пасти
        hans = _hans_breakout(md, window)
        fractal_outside = (hans is not None)

        # Паникёр
        panic_phase = _panic_phase(md.get("mfi", {}).get("type", ""))

        prev_sleeping = sleeping

        # Значимый бар = есть хоть один РЕДКИЙ событийный сигнал.
        any_flag = (bdb_strong or confirmed or alligator_wake or fractal_outside)
        if not any_flag:
            continue

        entry_price = stop_price = None
        if bdb_strong:
            entry_price = round(bars[i]["high"] + point, 6)
            stop_price  = round(bars[i]["low"]  - point, 6)

        signals.append({
            "date":                bars[i]["date"],
            "bar_index":           i,
            "bdb_strong":          bdb_strong,
            "bdb_candidate":       bdb_candidate,
            "bdb_direction":       direction,
            "confirmed":           confirmed,
            "alligator_wake":      alligator_wake,
            "alligator_sleeping":  sleeping,
            "fractal_outside_jaw": fractal_outside,
            "hans_direction":      hans,
            "panic_phase":         panic_phase,
            "exit_bell":           bool(md.get("exit_bell")),
            "entry_price":         entry_price,
            "stop_price":          stop_price,
        })

    live = _live_snapshot(bars, symbol, timeframe, point)
    return {"signals": signals, "live": live}


def _live_snapshot(bars: list, symbol: str, timeframe: str, point: float) -> dict:
    """
    Снимок текущего состояния рынка по последним барам (для дашборда).
    Свод статусов агентов на самом свежем баре. Без ордеров, без LLM.
    """
    md = _suppress(build_market_data, bars[-200:],
                   symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {}
    ao = md.get("ao", {})
    al = md.get("alligator", {})
    return {
        "t1_status":   "CONFIRMED" if (ao.get("crossed_zero") and md.get("divergence_ao"))
                       else "DETECTED" if md.get("divergence_ao") else "NOT_FOUND",
        "morj_status": "AWAKE"   if al.get("mature")
                       else "WAKING" if not al.get("sleeping")
                       else "SLEEPING",
        "divergence":  bool(md.get("divergence_ao")),
        "exit_bell":   bool(md.get("exit_bell")),
        "bar_time":    md.get("bar_time", ""),
        "alligator":   al,
    }


def run_live_council(bars: list, symbol: str, timeframe: str,
                     point: float, live: bool = False) -> dict:
    """
    РЕЖИМ COUNCIL — отдать последний бар живому Совету (A01–A09).

    ПРЕДОХРАНИТЕЛЬ БОЕВОГО РЕЖИМА:
      live=False (по умолчанию) — Совет считает и пишет в Атлас/журнал,
                                  но РЕАЛЬНЫЕ ордера в терминал НЕ идут.
      live=True                 — разрешён боевой выход в рынок.
    Закон Студии: ни одного реального ордера, пока край не доказан.
    Поэтому боевой режим включается только явным флагом в конфиге.

    Сейчас собирается market_data и состояние, прокидывается флаг live.
    Подключение прогона цепочки cartridge.py — следующим заходом, когда
    родим A02–A09 через Страницу Жизни. Пока это безопасная заглушка:
    она считает рынок и фиксирует намерение, но не торгует.
    """
    md = build_market_data(bars[-200:], symbol=symbol,
                           timeframe=timeframe, point=point)
    if not md:
        print("[COUNCIL] ❌ Пустой market_data — Совет не стартует")
        return {}

    if not live:
        print(f"[COUNCIL] 🔒 Безопасный режим (live=false): "
              f"{symbol} {timeframe} посчитан, ордера НЕ отправлены")
    else:
        print(f"[COUNCIL] 🔴 БОЕВОЙ режим (live=true): {symbol} {timeframe}")

    # Снимок для дашборда — полезен в обоих режимах
    snapshot = _live_snapshot(bars, symbol, timeframe, point)
    return {"market_data": md, "live_mode": live, "snapshot": snapshot}

# HOOKS_TYPING_V1 — маркер идемпотентности

# HOOKS_TYPING_V2 — маркер идемпотентности

# MEMORY_PATHS_V1 — маркер идемпотентности

# BIRZHA_CLEAN_MEMORY_V2 — маркер идемпотентности

# VASILY_ZASADA_V1 — маркер идемпотентности
