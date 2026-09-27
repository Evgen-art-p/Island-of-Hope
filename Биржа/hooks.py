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
# ═══════════════════════════════════════════════════════════
# SVOY_STOL_CEHA_V1 — У КАЖДОГО ЦЕХА СВОЙ СТОЛ
# ═══════════════════════════════════════════════════════════
# Стол был один на всю Биржу: `Биржа/данные/trading_state.json`.
# Пока цех один — незаметно. Поставь второй такой же (женский и
# мужской) — и они начнут писать вердикты в одну тетрадь и затирать
# друг друга.
#
# А в манифесте цеха уже давно объявлено своё: `журналы/pnl.jsonl`,
# `журналы/atlas.jsonl`. Задумка была верной, просто код брал общий
# файл. Теперь берёт цеховой.
#
# Цех говорит Совет перед прогоном (`postavit_ceh`). Не сказали —
# работаем по-старому, на общем столе: ничего не ломается.
_OBSHCHIY_DIR = _REPO / "GRONDHEIM_CITY" / "Биржа" / "данные"
STATE_PATH = _OBSHCHIY_DIR / "trading_state.json"      # запасной, общий
PNL_PATH = _OBSHCHIY_DIR / "trading_pnl.jsonl"         # запасной, общий

_TEKUSHCHIY_CEH = ""


def postavit_ceh(ceh_id: str = ""):
    """Чей стол накрываем. Зовётся Советом в начале прогона."""
    global _TEKUSHCHIY_CEH
    _TEKUSHCHIY_CEH = (ceh_id or "").strip()


def _dom_ceha() -> Path:
    if not _TEKUSHCHIY_CEH:
        return _OBSHCHIY_DIR
    return (_REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха" / _TEKUSHCHIY_CEH
            / "данные")


def _put_stola() -> Path:
    """Стол этого цеха. Первый раз — переносим общий, чтобы не начинать
    с чистого листа: открытые позиции и состояние остаются при цехе."""
    d = _dom_ceha()
    p = d / "trading_state.json"
    if not _TEKUSHCHIY_CEH:
        return p
    if not p.exists() and STATE_PATH.exists():
        try:
            d.mkdir(parents=True, exist_ok=True)
            p.write_text(STATE_PATH.read_text(encoding="utf-8"),
                         encoding="utf-8")
            print(f"[СТОЛ] переехал в цех {_TEKUSHCHIY_CEH} "
                  f"(общий остался как был)")
        except Exception as e:
            print(f"[СТОЛ] не смог перенести общий стол: {e}")
    return p


def _put_pnl() -> Path:
    return (_dom_ceha() / "trading_pnl.jsonl") if _TEKUSHCHIY_CEH \
        else PNL_PATH

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
    """Читает рабочую память ЭТОГО цеха. Файла нет — дефолт."""
    p = _put_stola()
    if not p.exists():
        return json.loads(json.dumps(_DEFAULT_STATE))
    # ODNA_YAMA_I_STOL_V1: споткнулись о недописанный — пробуем ещё.
    import time as _time_ch
    for _k_ch in range(3):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _time_ch.sleep(0.1)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[STATE] ⚠️  Повреждён {p.name} ({e}) — дефолт")
        return json.loads(json.dumps(_DEFAULT_STATE))


def save_trading_state(tstate: dict):
    """Сохраняет рабочую память ЭТОГО цеха."""
    p = _put_stola()
    p.parent.mkdir(parents=True, exist_ok=True)
    tstate["updated"] = datetime.now().isoformat()
    # ODNA_YAMA_I_STOL_V1: пишем во временный файл и подменяем одним
    # махом — недописанного стола не увидит ни страница, ни прогон.
    _tekst_st = json.dumps(tstate, ensure_ascii=False, indent=2)
    _tmp_st = p.with_name(p.name + ".tmp")
    try:
        import os as _os_st, time as _time_st
        _tmp_st.write_text(_tekst_st, encoding="utf-8")
        for _k_st in range(10):
            try:
                _os_st.replace(_tmp_st, p)
                break
            except PermissionError:
                _time_st.sleep(0.05)
        else:
            p.write_text(_tekst_st, encoding="utf-8")
    except Exception:
        p.write_text(_tekst_st, encoding="utf-8")
    print(f"[STATE] 💾 стол сохранён ({_TEKUSHCHIY_CEH or 'общий'}): "
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

def proverit_tochku(md: dict, para: str = "") -> dict:
    # TOCHKA_ROZHDAETSYA_V1: para — чья это точка («SYMBOL TF»).
    # Пусто — старый общий блок, ничего из прежнего не ломается.
    """
    Кодовая (без LLM) проверка живости точки c на текущем баре.
    Читает/пишет trading_state["iskra"]. Зовётся на КАЖДОМ баре
    между кандидатами (тем же местом, что _settle_bar/_vesti_poziciyu
    в tester_express.py — дёшево на пустом столе).

    Возвращает {"alive": bool, "reason": str, "changed": bool}.
    "changed" — точка поменяла состояние на этом баре (для ленты).
    """
    tstate = load_trading_state()
    isk = _blok_tochki(tstate, para)   # TOCHKA_ROZHDAETSYA_V1
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
    # MFI_ORIENTIR_NE_SIGNAL_V1 (05.09): было условием — новый некрон
    # той же стороны без GREEN/SQUAT проваливался в структурный слом,
    # хотя сам факт нового более глубокого некрона уже делает его
    # новой версией точки (живой пример «квадрата» 17-19.08 — оба
    # некрона честно прошли формулу, MFI при этом ни при чём). Слово
    # Шефа: «MFI — ориентир, не сигнал». Убрано как ворота; MFI
    # остаётся в reason фактом на столе, не условием жизни точки.
    if wf.get("bdb_dir") == napr:
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
                    "reason": f"подпитка (MFI {mfi_type}): точка обновлена → {novaya_zp}",
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
        # TOCHKA_DO_SLOMA_V1: смерть по ритму СНЯТА.
        # Слово Шефа: сколько поймано точек — столько и должно быть от
        # них волн, от истинных. Значит исходов два: цена ушла за точку
        # (не истинная) или ждём её волну сколько надо. Третьего нет.
        # А это правило («3 бара нейтрали») — наше выдуманное число,
        # его нет ни у Вильямса, ни у Котина, ни в каноне. Оно убивало
        # 31 точку из 89 — треть, и все они могли оказаться истинными.
        # Нейтраль остаётся ПОКАЗАНИЕМ: счётчик считается и лежит в
        # столе, трейдер видит, что ритм замер, и решает сам.
        if False:
            isk["alive"] = False
            isk["neutral_bars_count"] = 0
            save_trading_state(tstate)
            return {"alive": False,
                    "reason": f"TWR нейтрален {_n} бар(а) подряд — ритм угас во флэте",
                    "changed": True, "direction": napr}   # TOCHKA_NAPRAVLENIE_V1
        save_trading_state(tstate)
        return {"alive": True,
                "reason": f"TWR нейтрален {_n} бар(а) — жива, ритм замер",
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


# UBORKA_03_09_V1: on_before_run() убрана — старый CSV/webhook-путь,
# ни одного вызова по репо с 14.08 (бары идут через
# rynok_novyy_bar). # {MARKER} - marker


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
    # ZUBY_SO_SDVIGOM_V2: ряд Зубов в market_data не доезжает —
    # там только числа. Ядро (ALLIGATOR_SO_SDVIGOM_V1) уже отдаёт
    # Зубы СО СДВИГОМ — те, что под свечой. Их и берём.
    teeth = allig.get("teeth")
    # ZAYAVKA_I_SEYF_V1: сейф — когда пасть открыта и линии в ряд.
    _jaw = allig.get("jaw")
    _lips = allig.get("lips")
    close = (md.get("price", {}) or {}).get("close")
    if teeth is None or close is None:
        if positions and close is not None:
            print("[ТРЕЙЛ] ⚠️  Зубов со сдвигом нет — стоп не тяну")
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
        # POCHINIT_SCHYOT_R_V1: вторая защита — для позиций,
        # открытых раньше патча. Запоминаем стоп ДО того, как
        # сдвинем его: потом восстановить будет неоткуда.
        pos.setdefault("stop_initial", old)

        if direction == "LONG":
            # цена ушла под Зубы — пирамида мертва, стоп не тянем
            # (её добьёт _settle_positions по стопу или колоколу)
            if close < teeth:
                continue
            # ZAYAVKA_I_SEYF_V1 (слово Шефа 23.09): в болтанке сейфа
            # нет. Тянем, только когда линии в ряд вверх и цена
            # над ними: Губы > Зубы > Челюсть, цена выше Губ.
            if not (_lips is not None and _jaw is not None
                    and _lips > teeth > _jaw and close > _lips):
                if teeth > old:
                    print(f"[ТРЕЙЛ] ⏸ {pos.get('trader')} LONG: линии "
                          f"не в ряд — болтанка, стоп стоит {old}")
                continue
            novy = teeth
            if novy <= old:          # только в защиту
                continue
            if novy >= close:        # стоп не может быть выше цены
                continue
        elif direction == "SHORT":
            if close > teeth:
                continue
            # ZAYAVKA_I_SEYF_V1: зеркально — Губы < Зубы < Челюсть,
            # цена ниже Губ.
            if not (_lips is not None and _jaw is not None
                    and _lips < teeth < _jaw and close < _lips):
                if teeth < old:
                    print(f"[ТРЕЙЛ] ⏸ {pos.get('trader')} SHORT: линии "
                          f"не в ряд — болтанка, стоп стоит {old}")
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
# PEREEZD_NA_NEKRON_NE_FRAKTAL_V1: окно "рядом" для приседающего —
# в барах. Не высечено в камне, можно поправить и перезапустить патч.
# PRISEDANIE_PRAVDA_V1 (слово Шефа 23.09): три бара — разворотник и
# два до него. Было 3 — это четыре бара (0..3).
# TRI_BARA_V2 (слово Шефа 25.09): три бара до разворотника.
_OKNO_BAROV_PRISED = 3

_CHASY_ETAZHA = {
    "M1": 1 / 60, "M5": 5 / 60, "M10": 10 / 60, "M15": 15 / 60,
    "M30": 0.5, "H1": 1, "H2": 2, "H4": 4, "H8": 8, "H12": 12,
    "D1": 24, "W1": 24 * 7,
}


def _prisel_ryadom(md, okno_barov=_OKNO_BAROV_PRISED):
    """Приседающий на этом баре или в пределах последних `okno_barov`
    баров до него — MFI.md: дорожка не обязана стоять прямо на
    Некроне, важно что рынок готовился рядом."""
    last = (md.get("squat") or {}).get("last_squat") or {}
    if not last:
        return False
    try:
        from datetime import datetime
        fmt = "%Y.%m.%d %H:%M"
        t_bar = datetime.strptime(str(md.get("bar_time")), fmt)
        t_sq = datetime.strptime(str(last.get("date")), fmt)
    except Exception:
        return True  # даты не сравнились — не блокируем зря
    chas = _CHASY_ETAZHA.get(str(md.get("timeframe") or "H1").upper(), 1)
    if chas <= 0:
        return True
    razn_barov = (t_bar - t_sq).total_seconds() / 3600 / chas
    return 0 <= razn_barov <= okno_barov


def _pereezd_zayavki(pos, md):
    """Проверяет PENDING-заявку против НОВОГО РАЗВОРОТНИКА (Некрона),
    не голого фрактала — окружаем бар, а не геометрическую точку.

    Переезд требует ТУ ЖЕ тройку, что и вход — без сравнения
    "дальше/лучше" (по книге любой новый сигнал сносит старый):
      1. Некрон в сторону сделки.
      2. AO-дивер в сторону сделки.
      3. Приседающий рядом (на этом баре или в последних барах).

    Возвращает:
      "MOVED"   — переехала на новый разворотник (pos обновлён);
      "CANCEL"  — цена вернулась к старту, сигнал мёртв (снять);
      None      — ничего, ждём дальше.
    """
    d = (pos.get("direction") or "").upper()
    price = md.get("price", {}) or {}
    close = price.get("close")
    cur_high = price.get("high")
    cur_low = price.get("low")
    point = md.get("point") or 0.01
    sp_pts = (md.get("mfi", {}) or {}).get("spread")
    sp = (float(sp_pts) * float(point)) if sp_pts is not None else 0.0

    if close is None:
        return None

    necron = md.get("necron_bar") or {}
    necron_dir = necron.get("direction")
    necron_price = necron.get("price")

    if d == "LONG":
        start = pos.get("signal_start")
        if start is not None and close < start:
            return "CANCEL"

        # PEREEZD_BEZ_SRAVNENIYA_V1 (15.09, Шеф): книга не требует
        # сравнения "дальше/лучше" — любой новый сигнал того же
        # направления сносит старый ордер. Если новый Некрон окажется
        # менее выгодным (ближе к цене) — рынок и так возьмёт его
        # раньше, сравнивать незачем.
        if (necron_dir == "BULL" and necron_price is not None
                and md.get("divergence_ao")
                and _prisel_ryadom(md)):
            if cur_high is not None:
                pos["entry"] = round(cur_high + 2 * sp, 6)   # Buy Stop + 2 спреда
            pos["stop"] = round(necron_price, 6)             # под низ Некрона
            pos["stop_initial"] = pos["stop"]
            pos["signal_start"] = necron_price
            pos["entry_fractal_price"] = necron_price
            pos["_ждёт_баров"] = 0
            return "MOVED"

    elif d == "SHORT":
        start = pos.get("signal_start")
        if start is not None and close > start:
            return "CANCEL"

        if (necron_dir == "BEAR" and necron_price is not None
                and md.get("exit_bell")
                and _prisel_ryadom(md)):
            if cur_low is not None:
                pos["entry"] = round(cur_low - sp, 6)        # Sell Stop − 1 спред
            pos["stop"] = round(necron_price, 6)             # над high Некрона
            pos["stop_initial"] = pos["stop"]
            pos["signal_start"] = necron_price
            pos["entry_fractal_price"] = necron_price
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

    _bar_sym = str(md.get("symbol", "") or "").strip().upper()
    for pos in live:
        # RABOTA_PO_PARE_V1: заявку берёт ТОЛЬКО её собственный рынок.
        # Иначе заявка Синди по золоту ждала бы, пока до неё дойдёт
        # евро, и умирала бы «протухшей» на живом сигнале.
        _psym = (pos.get("symbol") or "").strip().upper()
        if _bar_sym and _psym and _psym != _bar_sym:
            ostalis.append(pos)
            continue
        # UBRAT_CHETVERTOGO_V1: симметрия с закрытием. Заявка без
        # инструмента (открыта до 14.08) НЕ активируется чужим баром:
        # в логе 15.08 такая заявка по 0.708 «активировалась» баром
        # евро по 1.15 и стала позицией, которую закрытие потом
        # трогать отказалось. Защита в одной руке из двух хуже, чем
        # никакой — она плодит вечные позиции.
        if _bar_sym and not _psym:
            print(f"[ОРДЕР] ⚠️  {pos.get('trader')} без инструмента "
                  f"(открыта до 14.08) — не активирую баром {_bar_sym}. "
                  f"Решение по старым заявкам за Шефом.")
            ostalis.append(pos)
            continue
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

        # ZAYAVKA_SLED_BAR_V1: на баре своего рождения заявка не
        # активируется. Уровни сняты С ЭТОГО бара — он накрывает их по
        # построению, и «рынок дошёл» получалось само собой, в тот же
        # миг, когда ордер поставили. А следом бар накрывал и стоп:
        # 24.08 обе сделки умерли ровно так, минус R по арифметике, а
        # не по рынку. Отложка ждёт БУДУЩЕГО движения; бар, по
        # которому считали, — прошлое.
        _rodilas_na = str(pos.get("_ждёт_с") or "")
        if _rodilas_na and _rodilas_na == str(bar_time or ""):
            print(f"[ОРДЕР] ⏳ {pos.get('trader')} {d} @ {entry} — "
                  f"поставлен на этом баре, ждёт следующего")
            ostalis.append(pos)
            continue

        srabotal = ((d == "LONG"  and high >= entry) or
                    (d == "SHORT" and low  <= entry))

        if srabotal:
            pos["status"] = "OPEN"
            pos["opened_at"] = bar_time      # ВРЕМЯ РЕАЛЬНОГО ВХОДА
            # POCHINIT_SCHYOT_R_V1: запоминаем риск НА ВХОДЕ.
            # Без этого поля счёт брал ТЕКУЩИЙ стоп — и после
            # трейлинга любой стоп-аут писался как −1.0R, хотя
            # реально терялось три пункта вместо восьмидесяти.
            # В миг входа текущий стоп И ЕСТЬ первоначальный.
            if pos.get("stop") is not None:
                pos.setdefault("stop_initial", pos["stop"])
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

        # не сработал — считаем, сколько ждёт.
        # ZAYAVKA_ZHDYOT_BARY_V1: считаем БАРЫ, а не вызовы. Прогон
        # зовёт рыночный шаг из двух мест, и на части баров он
        # срабатывает дважды — заявка старела вдвое быстрее.
        # «Десять баров» оказывались пятью: место 33 (13.02.2024)
        # сняли на пятом баре, а цена дошла до заявки на шестом.
        # Теперь прибавляем, только когда сменился бар.
        if pos.get("_ждёт_бар_время") != bar_time:
            zhdyot = pos.get("_ждёт_баров", 0) + 1
            pos["_ждёт_баров"] = zhdyot
            pos["_ждёт_бар_время"] = bar_time
        else:
            zhdyot = pos.get("_ждёт_баров", 0)
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


# ════════════════════════════════════════════════════════════
# VNUTRI_BARA_V1 — вход и стоп в одном баре: заглянуть внутрь.
# ════════════════════════════════════════════════════════════
# Слово Шефа 24.09 («уже хочу»). Заявка сработала и стоп задет в ОДНОЙ
# свече рабочего этажа — по самой свече не видно, что было раньше.
# Город брал худший вариант. Теперь смотрит младший этаж из
# test_data (M15, если нет — H1): где сработала заявка и был ли стоп
# задет ПОСЛЕ этого до конца свечи. Младшая свеча, где задеты и вход,
# и стоп сразу, — по-прежнему худший вариант. Данных нет — как раньше.
_VNUTRI_KESH: dict = {}


def _vnutri_bara(symbol, timeframe, bar_time, direction, entry, stop):
    """→ ("стоп", когда) | ("живёт", когда_вход) | (None, почему)."""
    try:
        from datetime import datetime as _dtv, timedelta as _tdv
        from bisect import bisect_left as _bl
        from feed_source import _find_csv as _fcsv
        from williams_core import read_mt5_csv as _rcsv
    except Exception as e:
        return None, f"нечем смотреть ({e})"
    minut = {"H1": 60, "H2": 120, "H4": 240, "H6": 360, "H8": 480,
             "H12": 720, "D1": 1440}.get(str(timeframe or "").upper())
    if not minut or entry is None or stop is None:
        return None, "этаж не тот"
    try:
        t0 = _dtv.strptime(str(bar_time)[:16], "%Y.%m.%d %H:%M")
    except Exception:
        return None, "время бара не читается"
    t1 = t0 + _tdv(minutes=minut)
    s0, s1 = t0.strftime("%Y.%m.%d %H:%M"), t1.strftime("%Y.%m.%d %H:%M")
    long_ = str(direction).upper() == "LONG"
    for mlad, m_min in (("M15", 15), ("H1", 60)):
        if m_min >= minut:
            continue
        try:
            put = _fcsv(symbol, mlad)
        except Exception:
            put = None
        if not put:
            continue
        kl = str(put)
        if kl not in _VNUTRI_KESH:
            try:
                _b = _rcsv(kl)
                _VNUTRI_KESH[kl] = (_b, [str(x.get("date")) for x in _b])
            except Exception:
                continue
        bars, daty = _VNUTRI_KESH[kl]
        i = _bl(daty, s0)
        vn = []
        while i < len(bars) and daty[i] < s1:
            vn.append(bars[i])
            i += 1
        if not vn:
            continue
        aktiv = None
        for b in vn:
            vh = (b["high"] >= entry) if long_ else (b["low"] <= entry)
            st = (b["low"] <= stop) if long_ else (b["high"] >= stop)
            if aktiv is None:
                if not vh:
                    continue
                aktiv = b["date"]
                if st:
                    return "стоп", f"{mlad} {b['date']} (вход и стоп в одной {mlad})"
                continue
            if st:
                return "стоп", f"{mlad} {b['date']}"
        if aktiv is None:
            return None, f"{mlad}: вход внутри свечи не найден"
        return "живёт", f"{mlad}: вход {aktiv}, стоп до конца свечи не задет"
    return None, "младшего этажа за это время нет"


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
        # RABOTA_PO_PARE_V1: ЧЕЙ БАР ПРИШЁЛ. Трое трейдеров — три
        # разных инструмента, а стол цеха один. Позиция по золоту не
        # имеет никакого отношения к барам евро: её нельзя ни закрыть
        # по чужому стопу, ни записать в журнал чужим символом.
        _psym = (pos.get("symbol") or "").strip().upper()
        if _psym and symbol and _psym != str(symbol).strip().upper():
            still_open.append(pos)
            continue
        if not _psym:
            print(f"[SETTLE] ⚠️  позиция {pos.get('trader')} без инструмента "
                  f"(открыта до 14.08) — не сужу её чужим баром {symbol}. "
                  f"Решение по старым позициям за Шефом.")
            still_open.append(pos)
            continue
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
        # VNUTRI_BARA_V1: заявка сработала на ЭТОЙ же свече, и стоп
        # тоже задет — смотрим внутрь по младшему этажу.
        if (reason == "STOP_LOSS"
                and str(pos.get("opened_at") or "") == str(bar_time)):
            _vv, _kak = _vnutri_bara(symbol, timeframe, bar_time,
                                     direction, entry, stop)
            if _vv == "живёт":
                exit_price, reason = None, None
                print(f"[ВНУТРИ БАРА] 🔍 {pos.get('trader')} {direction}: "
                      f"{_kak} — позиция живёт")
            elif _vv == "стоп":
                print(f"[ВНУТРИ БАРА] 🔍 {pos.get('trader')} {direction}: "
                      f"вошла, стоп задет {_kak} — выбило честно")
            else:
                print(f"[ВНУТРИ БАРА] 🔍 {pos.get('trader')} {direction}: "
                      f"{_kak} — беру худший вариант")
        # KOLOKOL_I_PERESTANOVKA_V1: колокол — по стороне сделки.
        # Медвежье расхождение (exit_bell) кончает ход ВВЕРХ — это
        # выход для LONG. Для SHORT выход — бычье (divergence_ao).
        # Раньше колокол закрывал и SHORT по медвежьему — то есть
        # по сигналу в ЕГО пользу.
        # KOLOKOL_BUDIT_V1 (слово Шефа 24.09): колокол больше НЕ
        # закрывает сам. Он звенит на двух соседних бугорках и почти
        # всегда; когда Синди выходила сама — выходила лучше кода.
        # Теперь колокол только БУДИТ трейдера — на баре, где начал
        # звонить. Пока звонит подряд — повторно не будит.
        if reason is None and close is not None:
            _zvon = ((direction == "LONG" and bell)
                     or (direction == "SHORT"
                         and bool(md.get("divergence_ao"))))
            if _zvon and not pos.get("_колокол_звенел"):
                pos["колокол"] = bar_time
                print(f"[КОЛОКОЛ] 🔔 {pos.get('trader')} {direction}: "
                      f"звонит — будим трейдера, решает она")
            pos["_колокол_звенел"] = bool(_zvon)

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

        # TRI_POPYTKI_V1: выбило стоп — попытка засчитана. Слово Шефа:
        # «не попала, ждёт следующий разворотник, так три раза; после
        # третьего думает, то ли она делает». Счётчик живёт при точке:
        # новая точка — новый счёт с нуля. Город не запрещает четвёртый
        # вход, он только говорит вслух то, что трейдер и сам заметил.
        if reason == "STOP_LOSS":
            try:
                _t = load_trading_state()
                _isk = _blok_tochki(
                    _t, _para_tochki(pos.get("symbol") or symbol,
                                     md.get("timeframe") or ""))
                _isk["попыток"] = int(_isk.get("попыток") or 0) + 1
                # SVOI_SDELKI_VIDNO_V1: рядом со счётчиком — сами
                # исходы. Счётчик говорит «которая по счёту», а это —
                # «чем кончились прошлые». Не запрет: три попытки его
                # право, и четвёртая тоже не заказана. Просто человек
                # приходит на структуру и ВИДИТ, что уже пробовал, —
                # без того, чтобы догадаться спросить память.
                # Живёт при точке и гаснет вместе с ней: новая
                # структура — чистый лист, чужих граблей не наследуем.
                _ish = list(_isk.get("исходы") or [])
                _ish.append({
                    "попытка": _isk["попыток"],
                    "чем": "стоп",
                    "цена": pos.get("stop"),
                    "вход": pos.get("entry"),
                    "куда": pos.get("direction"),
                    "бар": md.get("bar_time"),
                })
                _isk["исходы"] = _ish[-3:]     # больше трёх незачем
                save_trading_state(_t)
                print(f"[ПОПЫТКА] ✗ стоп выбил · попытка "
                      f"{_isk['попыток']} на этой структуре")
            except Exception as _ep:
                print(f"[ПОПЫТКА] не сосчиталась ({_ep}) — работаем дальше")

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

    # KOLOKOL_PAMYAT_V1: метку колокола — в стол, даже если на баре
    # ничего не закрылось. Иначе она пропадала: Синди не будили,
    # а «звенел ли в прошлый бар» терялось и звон шёл каждый бар.
    if not closed and any("_колокол_звенел" in _q for _q in still_open):
        try:
            _tk = load_trading_state()
            for _p in _tk.get("positions") or []:
                for _q in still_open:
                    if ((_p.get("magic"), _p.get("entry"),
                         _p.get("opened_at"))
                            == (_q.get("magic"), _q.get("entry"),
                                _q.get("opened_at"))):
                        for _kk in ("колокол", "_колокол_звенел"):
                            if _kk in _q:
                                _p[_kk] = _q[_kk]
            save_trading_state(_tk)
        except Exception as _e_kp:
            print(f"[КОЛОКОЛ] метку сохранить не вышло ({_e_kp})")
    if closed:
        chain["open_positions"] = still_open
        tstate = load_trading_state()
        tstate["positions"] = still_open
        # POZICIYA_NE_KAZHDYY_BAR_V1: последнее закрытие — в стол, чтобы
        # ключ мог позвать трейдера ровно на том баре, где сделка
        # кончилась. Раньше закрытия жили только в журнале, и город
        # молчал о самом важном.
        _p = closed[-1]
        tstate["последнее_закрытие"] = {
            "бар": _p.get("closed_at"),
            "symbol": _p.get("symbol"),
            "причина": _p.get("close_reason"),
            "выход": _p.get("exit"),
            "pnl": _p.get("pnl_price"),
        }
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
        # SUDYA_BEZ_PRIZRAKOV_V1: сперва спрашиваем, есть ли место.
        # Сенсоров убрали 06.08 вместе с Искрой — папок A01…A04 в цехе
        # нет, постов тоже. А таблица их всё перечисляла, и после
        # КАЖДОЙ сделки два готовых вывода уходили в пустоту:
        # «дописано: False, слот пуст». Таблицу не трогаем: заведёшь
        # сенсоры снова — заработает само.
        _est = _slot_sushchestvuet("торговый_хаос")
        _prizraki = [s for s in SENSOR_SLOTS.values() if not _est(s)]
        if _prizraki:
            print(f"[МАЯК] мест нет, пропускаю: {', '.join(_prizraki)}")
        for key, slot in SENSOR_SLOTS.items():
            if not _est(slot):
                continue
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
    # AC_VON_V1: AC убран из города — печатать нечего
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

# SVOY_STOL_CEHA_V1 - marker


# ═══════════════════════════════════════════════════════════
# РЫНОК СУДИТ ПЕРВЫМ (RUKA_RYNKA_V1)
# ═══════════════════════════════════════════════════════════
# Обе руки ниже были написаны давно и работали — но их перестал
# звать кто бы то ни было, когда 06.08 ушёл старый путь Совета
# вместе с Искрой. Заявка висела вечно, позиция не закрывалась
# никогда, журнал сделок не рос, судья молчал.
#
# Это ФИЗИКА, а не суждение: рынок делает своё дело до того, как
# кто-то за столом откроет рот. Поэтому рука зовётся первым шагом
# wake_council — раньше Архивариуса и раньше трейдеров.
# ═══════════════════════════════════════════════════════════
# TOCHKA_ROZHDAETSYA_V1 — точку ноль зажигает КОД, а не Искра
# ═══════════════════════════════════════════════════════════
# proverit_tochku (TOCHKA_ZHIVA_V1) умела ВЕСТИ точку между барами,
# но зажигала её только Искра (слоты/A01/мозг.py, ISKRA_ALIVE_V1).
# Слот уехал в архив 06.08 — и alive=True не ставил больше никто.
# Точка вечно мертва, разворотник на столе живёт одну свечу, мерить
# от него откат нечем.
#
# Слово Шефа: «разворотник и есть точка; увидел разворотник и смотрю
# от него же волну 1». Но бар истинен НЕ сам по себе: КАНОН_ВХОДА
# §2.1 (модуль 6.2) — разворотник это пункт ЧЕТВЁРТЫЙ, печать в зоне
# конца волны, а не поиск по всему графику. Зону меряет линейка по AO
# (izmerit_volnovuyu_strukturu, 18.07): горб третьей → переход нуля →
# дивергенция пятой. Её ответ — поле struktura_chitaetsya.
# Рамку 100-140 не берём: окно — не фильтр (§5к-5п).
#
# Это ПОКАЗАНИЕ, а не решение: координата с датой, как фрактал или
# зона. Что она значит — судит трейдер.

def _para_tochki(symbol: str, timeframe: str) -> str:
    """Имя ячейки на полке. У точки должно быть имя пары — иначе
    сосед по цеху подменит её своей."""
    s = (symbol or "").strip().upper()
    tf = (timeframe or "").strip().upper()
    return f"{s} {tf}".strip()


def _blok_tochki(tstate: dict, para: str = "") -> dict:
    """Ячейка точки. Пары нет — старый общий блок `iskra` (так зовут
    те, кто был написан до полки). Пара есть — своя ячейка."""
    if not para:
        return tstate.setdefault("iskra", {})
    return tstate.setdefault("точки", {}).setdefault(para, {})


# ═══════════════════════════════════════════════════════════
# NABLYUDENIE_V1 — «беру на карандаш», второй ключ пробуждения
# ═══════════════════════════════════════════════════════════
# Слово Шефа: «увидел, похоже, проверил — наблюдай, если видишь, что
# вот-вот твой сигнал». Трейдер, которому родившаяся точка не его
# момент, больше не теряет увиденное: он говорит НАБЛЮДАЮ, и город
# будит его дальше, пока он сам не скажет УХОЖУ или не войдёт.
#
# Снимает наблюдение ТОЛЬКО трейдер. Код не гасит его ни при сломе
# точки, ни по числу баров: слом он увидит сам и скажет.

def nablyudenie(symbol: str = "", timeframe: str = "",
                slot: str = "") -> dict:
    """Что трейдер взял на карандаш по этой паре. Пусто — не наблюдает."""
    try:
        t = load_trading_state()
        para = _para_tochki(symbol, timeframe)
        return ((t.get("наблюдения") or {}).get(para) or {}).get(slot) or {}
    except Exception:
        return {}


def vzyat_na_karandash(symbol: str, timeframe: str, slot: str,
                       za_chem: str = "", bar: str = "") -> None:
    """Трейдер сказал НАБЛЮДАЮ. Запоминаем — за чем и с какого бара."""
    try:
        t = load_trading_state()
        para = _para_tochki(symbol, timeframe)
        polka = t.setdefault("наблюдения", {}).setdefault(para, {})
        bylo = polka.get(slot) or {}
        polka[slot] = {
            "за_чем": (za_chem or "").strip()[:400],
            "с_бара": bylo.get("с_бара") or bar,
            "последний_бар": bar,
        }
        save_trading_state(t)
        if not bylo:
            print(f"[НАБЛЮДЕНИЕ] 👁 {slot} взял на карандаш {para}")
    except Exception as e:
        print(f"[НАБЛЮДЕНИЕ] записать не вышло ({e}) — работаем дальше")


def snyat_nablyudenie(symbol: str = "", timeframe: str = "",
                      slot: str = "", pochemu: str = "") -> bool:
    """Трейдер сказал УХОЖУ (или вошёл). Наблюдение снимается."""
    try:
        t = load_trading_state()
        para = _para_tochki(symbol, timeframe)
        polka = (t.get("наблюдения") or {}).get(para) or {}
        if slot not in polka:
            return False
        polka.pop(slot, None)
        save_trading_state(t)
        print(f"[НАБЛЮДЕНИЕ] ✕ {slot} снял наблюдение по {para}"
              + (f": {pochemu}" if pochemu else ""))
        return True
    except Exception as e:
        print(f"[НАБЛЮДЕНИЕ] снять не вышло ({e}) — работаем дальше")
        return False


def zabyt_tochku(symbol: str = "", timeframe: str = "") -> bool:
    """TOCHKA_NE_TASHCHITSYA_V1: стереть точку по паре.

    Нужна прогону по истории: он ПРЫГАЕТ от места к месту через недели
    и месяцы, а точка живёт между вызовами (в реале так и надо — город
    идёт баром за баром). Без чистки на новое место приезжает точка,
    рождённая полгода назад: заново не родится, а проверка тут же
    похоронит её структурным сломом — и трейдера не позовут там, где
    стоит честный разворотник.

    Ничего не судит и никого не будит. Просто чистая доска.
    """
    try:
        t = load_trading_state()
        para = _para_tochki(symbol, timeframe)
        polka = t.get("точки") or {}
        bylo = bool((polka.get(para) or {}).get("alive"))
        if para in polka:
            polka.pop(para, None)
            t["точки"] = polka
        # NABLYUDENIE_V1: прогон прыгнул — вчерашнее наблюдение к новому
        # месту отношения не имеет. В живом городе эта рука не зовётся.
        (t.get("наблюдения") or {}).pop(para, None)
        save_trading_state(t)
        return bylo
    except Exception as e:
        print(f"[ТОЧКА] забыть не вышло ({e}) — работаем дальше")
        return False


# ═══════════════════════════════════════════════════════════
# VEDENIE_FRAKTALY_V1 — стоп на два фрактала назад
# ═══════════════════════════════════════════════════════════
# «РЫНОЧНЫЙ ФРАКТАЛ», §4.2: «Стоп-лосс перемещается на уровень,
# расположенный на два фрактала назад в противоположном направлении.
# Это позволяет плыть по течению и защищает прибыль при развороте.»
#
# Ни порогов, ни процентов. Только фракталы, которые и так считаются.
# Стоп ходит ТОЛЬКО в сторону прибыли — назад никогда.

def _vesti_stopy(md: dict) -> int:
    """Подтянуть стопы открытых позиций. Возвращает, сколько сдвинуто.

    Это не решение о сделке, а исполнение правила, которое трейдер
    принял, когда входил. Потому и делается кодом, без вопросов.
    """
    try:
        fr = (md or {}).get("fractals") or {}
        verh = list(fr.get("all_up") or [])
        niz = list(fr.get("all_down") or [])
        _bar_sym = str((md or {}).get("symbol", "") or "").strip().upper()

        t = load_trading_state()
        sdvinuto = 0
        for pos in (t.get("positions") or []):
            if pos.get("status") not in ("OPEN", "WATCHING"):
                continue
            _psym = (pos.get("symbol") or "").strip().upper()
            if _psym and _bar_sym and _psym != _bar_sym:
                continue          # чужой рынок — не наше дело
            napr = (pos.get("direction") or "").upper()
            stop = pos.get("stop")
            if stop is None:
                continue
            # два фрактала назад в ПРОТИВОПОЛОЖНОМ направлении
            if napr == "LONG":
                if len(niz) < 2:
                    continue
                novyy = niz[-2].get("price")
                dvigat = novyy is not None and novyy > stop
            elif napr == "SHORT":
                if len(verh) < 2:
                    continue
                novyy = verh[-2].get("price")
                dvigat = novyy is not None and novyy < stop
            else:
                continue
            if not dvigat:
                continue          # назад стоп не ходит
            pos["stop"] = novyy
            pos["stop_vedyot"] = "два фрактала назад"
            sdvinuto += 1
            print(f"[ВЕДЕНИЕ] ⇢ {napr} {pos.get('entry')} · "
                  f"стоп {stop} → {novyy} (2 фрактала назад)")
        if sdvinuto:
            save_trading_state(t)
        return sdvinuto
    except Exception as e:
        print(f"[ВЕДЕНИЕ] стопы не подтянулись ({e}) — позиции целы")
        return 0


def _vesti_tochku(md: dict, symbol: str = "", timeframe: str = "") -> dict:
    """Родить точку ноль или вести уже рождённую. Код, без LLM.

    Зовётся на каждом баре из rynok_novyy_bar. Никогда не падает:
    в худшем случае отдаёт {"alive": False}.
    """
    para = _para_tochki(symbol, timeframe)
    try:
        wf = md.get("wave_form") or {}
        napr = wf.get("bdb_dir")
        cena = wf.get("bdb_price")
        price = md.get("price") or {}
        bar = md.get("bar_time")

        t = load_trading_state()
        isk = _blok_tochki(t, para)

        # ODIN_BAR_ODNO_RESHENIE_V1: один бар — одно решение.
        # Рука рынка на одном баре зовётся дважды: молчаливым шагом
        # прогона и потом внутри Совета. В прогоне 20.08 из-за этого
        # пропал первый в истории конец волны 1: первый заход его
        # отметил, второй зашёл заново, увидел отметку, провалился в
        # блок рождения — и точка родилась поверх события, стерев его.
        # Оба решения по отдельности верны, но принимать их дважды об
        # одном баре нельзя.
        if bar and str(isk.get("reshali_na_bare") or "") == str(bar):
            return dict(isk.get("otvet_bara") or {"alive": bool(isk.get("alive"))})

        def _zapomnit_otvet(otvet: dict) -> dict:
            """Запомнить решение этого бара и отдать его как есть."""
            try:
                t2 = load_trading_state()
                isk2 = _blok_tochki(t2, para)
                isk2["reshali_na_bare"] = str(bar or "")
                isk2["otvet_bara"] = dict(otvet)
                save_trading_state(t2)
            except Exception:
                pass
            return otvet
        zhiva = bool(isk.get("alive"))
        storona = isk.get("trend_direction")

        # VERSHINA_NE_NIZHE_KRAYA_V1: вершина не может быть НИЖЕ того,
        # куда цена потом дошла.
        #
        # Конец волны 1 ставит разворотный бар — так в каноне, это не
        # трогаем. Но проверялась эта отметка только ДРУГИМ разворотным
        # баром (NOVAYA_MAKUSHKA_V1). Если цена идёт дальше и обратных
        # разворотников не даёт, вершина остаётся внизу, хотя рынок её
        # давно прошёл. Глазом это видно сразу, у кода проверки не было.
        #
        # Край после точки код и так копит каждый бар — самый дальний
        # экстремум с рождения точки, «та самая макушка волны 1». Здесь
        # просто сверяем два числа, которые уже лежат рядом. Ни порогов,
        # ни допусков, ни новых данных.
        #
        # Переезд ≠ «волна кончилась заново» (KRAY_VOLNY_V1): волна как
        # раз продолжается. Событий трейдеру не добавляем, не будим.
        if (zhiva and isk.get("konec_volny_1")
                and not isk.get("konec_volny_2")):
            _kv = isk.get("konec_volny_1") or {}
            _vershina = _kv.get("цена")
            _kray = isk.get("kray_posle")
            if _vershina is not None and _kray is not None:
                try:
                    _dalshe = (_kray > _vershina if storona == "BULL"
                               else _kray < _vershina)
                except TypeError:
                    _dalshe = False
                if _dalshe:
                    _kv["цена"] = _kray
                    _kv["бар"] = bar
                    _kv["баров_от_точки"] = int(isk.get("barov_s_tochki") or 0)
                    _kv["сдвинулась_ценой"] = True
                    isk["konec_volny_1"] = _kv
                    save_trading_state(t)
                    _slovo = "вершина" if storona == "BULL" else "дно"
                    print(f"[ВОЛНА 1] ↗ {para}: {_slovo} подтянулась "
                          f"{_vershina} → {_kray} (цена ушла дальше)")

        # ── разворотник на этом баре: рождение или ведение ──
        # Рождаем ТОЛЬКО в зоне конца волны (модуль 6.2, пункты 1-2):
        # бар без читаемой структуры — середина движения, не конец.
        # KONEC_VOLNY_2_V1: разворотник В СТОРОНУ точки, пришедший
        # ПОСЛЕ отмеченной макушки, — это конец отката, а не подпитка.
        # КАНОН §4.1: волна 2 сама маленький зигзаг, и её конец ловится
        # той же механикой РБ, только этажом мельче и без требования
        # яркой ангуляции. Различает подпитку и откат одно: была
        # макушка или нет. Ни порогов, ни новых чисел.
        # До макушки всё по-старому — такой бар углубляет точку
        # (TOCHKA_ZHIVA_V1), и это верно: волна ещё не пошла.
        if (zhiva and napr in ("BULL", "BEAR") and storona == napr
                and cena is not None and isk.get("konec_volny_1")
                and not isk.get("konec_volny_2")):
            _kv1 = isk.get("konec_volny_1") or {}
            _ot_makushki = (int(isk.get("barov_s_tochki") or 0)
                            - int(_kv1.get("баров_от_точки") or 0))
            isk["konec_volny_2"] = {
                "цена": cena, "бар": bar,
                "баров_от_макушки": max(0, _ot_makushki),
            }
            save_trading_state(t)
            _slovo = "вершины" if storona == "BULL" else "дна"
            _n = int(isk.get("нога") or 1)   # NOGI_SCHYOTNYE_V1
            isk["konec_volny_2"]["нога"] = _n
            save_trading_state(t)
            print(f"[ОТКАТ] ↩ {para}: кончился @ {cena} · бар {bar} "
                  f"· {max(0, _ot_makushki)} бар(ов) от {_slovo} "
                  f"· нога {_n}")
            return _zapomnit_otvet({"alive": True, "konec_volny_2": True,
                                    "direction": storona})

        # KONEC_VOLNY_1_V1: разворотник в ОБРАТНУЮ сторону внутри живой
        # точки — это не новое начало, а конец первой волны от неё,
        # если структура позади укладывается ПОСЛЕ точки. По
        # фрактальности волна 1 — сама пятиволновка, и конец её пятой
        # ловится тем же прибором, что и сама точка.
        # Сравниваем два числа, которые уже считаются: сколько баров
        # живёт точка и сколько баров у структуры. Ни допусков, ни
        # рамок по длине: волна задаёт этажи, а не этажи волну.
        # NOVAYA_MAKUSHKA_V1: макушка уже стоит, а пришёл ещё один
        # разворотник против точки. Слово Шефа: «значит новая макушка».
        # Волна 1 просто тянется дальше — точку рвать нельзя, иначе
        # откат ждать не от чего (так терялась половина: до отката
        # доживало 47% волн).
        # Переезжает макушка только если экстремум ушёл ДАЛЬШЕ прежнего:
        # чистое сравнение двух цен, без порогов. Не ушёл — молчим, это
        # уже ход отката, а не новая вершина.
        if (zhiva and napr in ("BULL", "BEAR") and storona != napr
                and cena is not None and wf.get("struktura_chitaetsya")
                and isk.get("konec_volny_1")
                and not isk.get("konec_volny_2")):
            _bylo = (isk.get("konec_volny_1") or {}).get("цена")
            _dalshe = (_bylo is None
                       or (cena > _bylo if storona == "BULL" else cena < _bylo))
            if _dalshe:
                isk["konec_volny_1"] = {
                    "цена": cena, "бар": bar, "сторона": napr,
                    "структура": wf.get("dlina") or 0,
                    "баров_от_точки": int(isk.get("barov_s_tochki") or 0),
                    "сдвинулась": True,   # KRAY_VOLNY_V1: не первый раз
                }
                isk["kray_posle"] = cena
                save_trading_state(t)
                # KRAY_VOLNY_V1: край, а не «макушка» — на медвежьей
                # структуре это дно. И переезд ≠ конец: волна как раз
                # продолжается, трейдер на «кончилась» честно спорил.
                _slovo = "вершина" if storona == "BULL" else "дно"
                _okonchanie = "ась" if storona == "BULL" else "ось"
                print(f"[ВОЛНА 1] ⛰ {para}: {_slovo} сдвинул{_okonchanie} "
                      f"{_bylo} → {cena} · бар {bar}")
                return _zapomnit_otvet({"alive": True, "konec_volny_1": True,
                                        "kray_sdvinulsya": True,
                                        "direction": storona})
            # не дальше прежней — это ход отката, ничего не трогаем
            return _zapomnit_otvet(proverit_tochku(md, para))

        # NOGI_SCHYOTNYE_V1: макушка и откат уже отмечены, а пришёл
        # ещё один разворотник против точки. От точки до точки идёт
        # пятиволновка (слово Шефа 26.08): после отката начинается
        # следующая нога, у неё своя макушка и свой откат — той же
        # механикой, тем же баром. Раньше это событие пропадало:
        # оба гнезда заняты, и точка молчала до слома, хотя внутри
        # неё проходили ещё две волны со своими шансами на вход.
        #
        # Номер ноги — ФАКТ, а не разметка. Третья это волна или
        # пятая, решает трейдер: он смотрит.
        if (zhiva and napr in ("BULL", "BEAR") and storona != napr
                and cena is not None and isk.get("konec_volny_1")
                and isk.get("konec_volny_2")):
            _n = int(isk.get("нога") or 1) + 1
            isk["нога"] = _n
            isk["konec_volny_1"] = {
                "цена": cena, "бар": bar, "сторона": napr,
                "структура": wf.get("dlina") or 0,
                "баров_от_точки": int(isk.get("barov_s_tochki") or 0),
                "нога": _n,
            }
            isk["konec_volny_2"] = None
            isk["kray_posle"] = cena
            # три попытки — право на ОДНОМ сигнале; следующий откат
            # будет новым сигналом, счёт начинается заново
            isk["попыток"] = 0
            save_trading_state(t)
            _slovo = "вершина" if storona == "BULL" else "дно"
            print(f"[ВОЛНА {_n}] ⛰ {para}: нога {_n} кончилась @ {cena} "
                  f"· бар {bar} · {_slovo} новой ноги от той же точки")
            return _zapomnit_otvet({"alive": True, "konec_volny_1": True,
                                    "нога": _n, "direction": storona})

        if (zhiva and napr in ("BULL", "BEAR") and storona != napr
                and cena is not None
                and not isk.get("konec_volny_1")):
            # VOLNA_V_MASSHTABE_V1: условия «пятёрка читается» здесь
            # БОЛЬШЕ НЕТ. Оно судило не нашу волну: линейка отматывает
            # четыре нуля AO назад от текущего бара, и замер 22.08
            # показал, что её длина одинакова на всех этажах (71-102
            # бара везде) — то есть она меряет своё окно, а не волну от
            # точки. Двадцать восемь срабатываний из шестидесяти девяти
            # были совпадением, а не суждением.
            #
            # Теперь волна меряется В СВОЁМ МАСШТАБЕ (глава 7: волна
            # должна занять 100-140 баров, иначе прибор смотрит чужой
            # уровень), а вместо приговора «годится / не годится» на
            # стол ложатся ЧИСЛА: сколько баров, на каком этаже,
            # читается ли пятёрка, сколько пуль сошлось. Что это
            # значит — решает трейдер.
            _dlina = wf.get("dlina") or 0
            _prozhito = int(isk.get("barov_s_tochki") or 0)
            _izm, _puli = {}, {}
            try:
                import pyat_pul as _pp
                _izm = _pp.merit_volnu(
                    symbol, timeframe,
                    str(isk.get("rodilas_na_bare") or ""), str(bar or ""),
                    storona)
                _puli = _pp.pyat_pul(md, storona)
            except Exception as _epp:
                print(f"[ВОЛНА 1] масштаб не померен ({_epp}) — "
                      f"отмечаю без него")
            if True:
                isk["konec_volny_1"] = {
                    "цена": cena, "бар": bar, "сторона": napr,
                    "структура": _dlina,
                    "баров_от_точки": _prozhito,
                    # VOLNA_V_MASSHTABE_V1: волна в своём масштабе
                    "этаж_волны": _izm.get("этаж"),
                    "баров_на_этаже": _izm.get("баров"),
                    "в_окне_100_140": _izm.get("в_окне"),
                    "пятёрка": _izm.get("читается"),
                    "пятёрка_почему": _izm.get("почему"),
                    "пуль_сошлось": _puli.get("сошлось"),
                    "пуль_посчитано": _puli.get("посчитано"),
                    "пули": _puli.get("пули"),
                }
                save_trading_state(t)
                _hvost = ""
                if _izm:
                    _hvost = (f" · волна {_izm.get('баров')} бар. на "
                              f"{_izm.get('этаж')}"
                              f", пятёрка: "
                              f"{'да' if _izm.get('читается') else 'нет'}")
                if _puli:
                    _hvost += (f", пуль {_puli.get('сошлось')}"
                               f"/{_puli.get('посчитано')}")
                print(f"[ВОЛНА 1] ⛰ {para}: кончилась @ {cena} · бар {bar} "
                      f"· {_prozhito} бар(ов) от точки{_hvost}")
                return _zapomnit_otvet({"alive": True, "konec_volny_1": True,
                                        "direction": storona})

        if napr in ("BULL", "BEAR") and cena is not None                 and wf.get("struktura_chitaetsya"):
            # ODNA_TOCHKA_ZA_RAZ_V1: пока жива старая — новая не родится.
            # Было `(not zhiva) or storona != napr`: живая точка не
            # мешала, и любой разворотник против неё объявлял себя новым
            # началом, стирая её волну 1, откат и счётчик попыток.
            # Отсюда 33 точки в год вместо 3-5 и 74 пустые структуры из
            # 87 — точка не доживала до собственной волны.
            #
            # Слово Шефа (25.08): точка ноль — конец коррекции СТАРШЕГО
            # порядка, ОДНА на движение, не переезжает. Всё, что внутри,
            # это её волны и откаты, они доживают до слома.
            #
            # Исходов у точки по-прежнему ДВА, третьего не заводим:
            # структурный слом по Close (proverit_tochku) или её волна.
            # Замер: точек 33 → 5.8 в год, ног 8 → 18, жизнь 4 → 6 баров.
            if not zhiva:
                # KONEC_VOLNY_1_V1: сюда обратный разворотник попадает
                # только если конец волны 1 уже был отмечен или его
                # структура НЕ уложилась после точки — тогда это правда
                # новое начало, а не макушка первой волны.
                isk["alive"] = True
                isk["trend_direction"] = napr
                isk["zero_point_price"] = cena
                isk["rodilas_na_bare"] = bar
                isk["t1_status"] = "DETECTED"
                isk["neutral_bars_count"] = 0
                isk["barov_s_tochki"] = 0
                isk["kray_posle"] = cena
                isk["struktura_pozadi"] = wf.get("dlina")
                # KONEC_VOLNY_1_V2: новая точка — новая жизнь. Без этой
                # строки отметка о конце волны 1 оставалась от ПРОШЛОЙ
                # точки и навсегда запирала событие: за 1.8 года срабатывало
                # ровно один раз, хотя обратных разворотников было девять.
                isk["konec_volny_1"] = None
                isk["konec_volny_2"] = None   # KONEC_VOLNY_2_V1
                isk["попыток"] = 0            # TRI_POPYTKI_V1
                isk["нога"] = 0               # NOGI_SCHYOTNYE_V1
                save_trading_state(t)
                print(f"[ТОЧКА] ✦ {para}: родилась {napr} @ {cena} · "
                      f"бар {bar} · структура позади: "
                      f"{wf.get('dlina')} бар.")
                return _zapomnit_otvet({"alive": True, "rodilas": True,
                                        "direction": napr})
            elif storona != napr:
                # ODNA_TOCHKA_ZA_RAZ_V1: разворотник против живой точки,
                # который не стал ни концом волны 1, ни концом отката
                # (оба блока стоят выше и возвращают сами). Раньше он
                # рождал новую точку поверх живой. Теперь — строка в
                # ленту и ведение прежней: волна ещё идёт.
                print(f"[ТОЧКА] · {para}: жива {storona} @ "
                      f"{isk.get('zero_point_price')} — разворотник "
                      f"{napr} @ {cena} новой не делает (бар {bar})")
            # та же сторона и точка жива — ведёт proverit_tochku:
            # там подпитка GREEN/SQUAT и структурный слом.

        res = proverit_tochku(md, para)

        # ── пока жива, копим два СЫРЫХ числа: край после точки
        # (та самая макушка волны 1) и сколько баров прошло ──
        if res.get("alive"):
            t = load_trading_state()
            isk = _blok_tochki(t, para)
            isk["barov_s_tochki"] = int(isk.get("barov_s_tochki", 0) or 0) + 1
            kray = isk.get("kray_posle")
            zp = isk.get("zero_point_price")
            napr2 = isk.get("trend_direction")
            hi, lo = price.get("high"), price.get("low")
            if napr2 == "BULL" and hi is not None:
                isk["kray_posle"] = hi if kray is None else max(kray, hi)
            elif napr2 == "BEAR" and lo is not None:
                isk["kray_posle"] = lo if kray is None else min(kray, lo)
            if isk.get("kray_posle") is None and zp is not None:
                isk["kray_posle"] = zp
            save_trading_state(t)
        elif res.get("changed"):
            print(f"[ТОЧКА] ✕ {para}: погасла — {res.get('reason')}")
        return _zapomnit_otvet(res)
    except Exception as e:
        print(f"[ТОЧКА] ⚠️  не рассужена ({e}) — бар цел, работаем дальше")
        return {"alive": False, "reason": f"сбой: {e}", "changed": False}


# ═══════════════════════════════════════════════════════════
# TOLKO_ZAKRYTYE_V1 — решаем по ЗАКРЫТЫМ барам, не по идущей свече
# ═══════════════════════════════════════════════════════════
# MetaTrader отдаёт с нулевой позиции формирующуюся свечу. Пока она
# живёт (у H4 — четыре часа), её закрытие ходит туда-сюда, а вместе с
# ним появляется и пропадает разворотный бар. Шеф поймал это глазом
# 20.08: три запуска подряд по одному бару дали C=1.16739, 1.16754,
# 1.1675 — и «РАЗВОРОТНЫЙ БАР: BEAR», которого к закрытию могло не
# остаться.
#
# В прогоне по истории это запрещено с самого начала: курсор отдаёт
# только закрытые бары, иначе город видел бы будущее. Здесь тот же
# закон для реала.

def _tolko_zakrytye(bars: list) -> list:
    """В РЕАЛЕ отбросить последний, ещё идущий бар. В ТЕСТЕРЕ не
    трогать: там за честность отвечает курсор истории."""
    try:
        from feed_source import get_feed_mode
        if (get_feed_mode() or {}).get("mode") != "real":
            return bars
    except Exception:
        return bars
    if bars and len(bars) > 1:
        return bars[:-1]
    return bars


def rynok_novyy_bar(symbol: str, timeframe: str,
                    window=None, point=None) -> dict:
    """Рассудить новый бар: что взято, что закрыто.

    Бары берутся ОБЩИМ краном (feed_source) — тем же, из которого
    рисуется кадр и смотрит трейдер. Второго источника не заводим:
    режим РЕАЛ/ТЕСТЕР переключается в одном месте и действует на всех.

    Порядок внутри бара — сперва активация заявок, потом закрытие.
    Консервативно: заявка, взятая на этом баре, может на нём же
    выбить стоп, и мы считаем именно так, а не как удобнее.

    Возвращает {"активировано": N, "закрыто": M, "позиций": K} —
    сводку для ленты кабинета. Ничего не решает и никого не судит.
    """
    itog = {"активировано": 0, "закрыто": 0, "позиций": 0, "причина": ""}

    bars, _p = window, point
    if not bars:
        try:
            from feed_source import bars as _src_bars
            bars, _p = _src_bars(symbol, timeframe, 300)
            bars = _tolko_zakrytye(bars)   # TOLKO_ZAKRYTYE_V1
        except Exception as e:
            itog["причина"] = f"кран молчит: {e}"
            return itog
    if point is not None:
        _p = point
    if window:
        # TOLKO_ZAKRYTYE_V1: окно пришло снаружи (кабинет/прогон) — в
        # реале в нём тоже сидит идущая свеча, режем и её.
        bars = _tolko_zakrytye(bars)
    if not bars:
        itog["причина"] = "нет баров"
        return itog

    md = build_market_data(bars[-300:], symbol=symbol,
                           timeframe=timeframe, point=_p)
    if not md:
        itog["причина"] = "williams_core вернул пусто"
        return itog

    # SVEZHEST_V1: отмечаем, на каком баре город стоит сейчас, —
    # по этой отметке Исполнитель отличает свежий вердикт от вчерашнего.
    try:
        _t_bar = load_trading_state()
        _t_bar.setdefault("рынок", {})["бар"] = str(md.get("bar_time") or "")
        save_trading_state(_t_bar)
    except Exception as _eb:
        print(f"[РЫНОК] отметку бара не поставил: {_eb}")

    state = {"chain_data": {"market_data": md}}
    cd = state["chain_data"]
    # Подушка безопасности Вильямса — экстремум второго бара назад.
    if len(bars) >= 3:
        cd["_bar_back2_low"] = bars[-3].get("low")
        cd["_bar_back2_high"] = bars[-3].get("high")

    # 1. заявки: рынок взял — становится позицией
    bylo = len(load_trading_state().get("positions", []) or [])
    _otkrytyh_do = sum(1 for p in (load_trading_state().get("positions") or [])
                       if p.get("status") not in ("WATCHING", "PENDING"))
    try:
        _aktivirovat_ordera(state)
    except Exception as e:
        print(f"[РЫНОК] ⚠️  заявки не рассудились: {e}")

    # 2. закрытие: стоп / колокол / воля трейдера
    t = load_trading_state()
    cd["open_positions"] = t.get("positions", []) or []
    _otkrytyh_posle_akt = sum(1 for p in cd["open_positions"]
                              if p.get("status") not in ("WATCHING", "PENDING"))
    # ВАЖНО: _settle_positions переписывает cd["open_positions"] тем же
    # словарём (chain — это и есть cd). Считать по нему ПОСЛЕ вызова
    # нельзя — он уже новый. Запоминаем число ДО.
    _bylo_v_stole = len(cd["open_positions"])
    # VKLYUCHIT_TREYLING_V1: тянем стоп за Зубами ДО проверки
    # стопов — так обещано в докстринге самой функции: «чтобы
    # сейф успел сработать раньше, чем рынок дотянется до
    # старого стопа».
    #
    # Функция была написана и НИКЕМ НЕ ВЫЗЫВАЛАСЬ: ни одной
    # строчки [ТРЕЙЛ] за все прогоны. А на замере по 64 входам
    # она дала −6.1R против −15.3R у фракталов своего этажа и
    # −46.4R у неподвижного стопа. Лучшее ведение лежало
    # выключенным.
    try:
        _treyling_za_zubami(state)
    except Exception as e:
        print(f"[РЫНОК] ⚠️  стоп не подтянулся ({e}) — иду дальше")
    try:
        _settle_positions(state)
    except Exception as e:
        print(f"[РЫНОК] ⚠️  позиции не закрылись: {e}")

    stalo = load_trading_state().get("positions", []) or []
    itog["активировано"] = max(0, _otkrytyh_posle_akt - _otkrytyh_do)
    itog["закрыто"] = max(0, _bylo_v_stole - len(stalo))
    itog["позиций"] = len(stalo)

    # VEDENIE_FRAKTALY_V1: подтянуть стопы по фракталам. После
    # закрытия — чтобы бар судил позицию тем стопом, с которым она в
    # этот бар вошла, а не подтянутым задним числом.
    _vesti_stopy(md)

    # TOCHKA_ROZHDAETSYA_V1: точка ноль — после физики, до трейдеров.
    # Разворотник и есть точка; дальше её ведёт proverit_tochku.
    _vesti_tochku(md, symbol, timeframe)

    if itog["активировано"] or itog["закрыто"]:
        print(f"[РЫНОК] 📊 бар {md.get('bar_time', '')} · "
              f"взято {itog['активировано']}, закрыто {itog['закрыто']}, "
              f"в работе {itog['позиций']} (было {bylo})")
    return itog


# RUKA_RYNKA_V1 - marker

# RABOTA_PO_PARE_V1 - marker

# UBRAT_CHETVERTOGO_V1 - marker

# SVEZHEST_V1 - marker

# TOCHKA_ROZHDAETSYA_V1 - marker

# TOLKO_ZAKRYTYE_V1 - marker

# TOCHKA_NE_TASHCHITSYA_V1 - marker

# NABLYUDENIE_V1 - marker

# KONEC_VOLNY_1_V1 - marker

# KONEC_VOLNY_1_V2 - marker

# TOCHKA_DO_SLOMA_V1 - marker

# ODIN_BAR_ODNO_RESHENIE_V1 - marker

# KONEC_VOLNY_2_V1 - marker

# NOVAYA_MAKUSHKA_V1 - marker

# KRAY_VOLNY_V1 - marker

# TRI_POPYTKI_V1 - marker

# VEDENIE_FRAKTALY_V1 - marker

# POZICIYA_NE_KAZHDYY_BAR_V1 - marker

# VOLNA_V_MASSHTABE_V1 - marker

# ZAYAVKA_SLED_BAR_V1 - marker


# ══════════════════════════════════════════════════════════════
# SUDYA_BEZ_PRIZRAKOV_V1 — есть ли такое место в цехе
# ══════════════════════════════════════════════════════════════

def _slot_sushchestvuet(ceh: str):
    """Вернёт проверялку: есть ли у цеха такой слот НА ДИСКЕ.

    Спрашиваем папку, а не маски и не посты: маска переживает
    упразднение места (так было и с магиком Локи), а пост у сенсоров
    не заводили вовсе. Папка со слотом — то, что есть или чего нет.

    Список считаем ОДИН раз на сделку и держим в замыкании: судья
    ходит по четырём сенсорам, и лазить на диск четырежды незачем.
    """
    imena = set()
    try:
        from pathlib import Path as _P
        _koren = _P(__file__).resolve().parent.parent / "GRONDHEIM_CITY"
        _d = _koren / "Биржа" / "цеха" / ceh / "слоты"
        if _d.is_dir():
            imena = {p.name for p in _d.iterdir() if p.is_dir()}
    except Exception as e:
        print(f"[МАЯК] слоты цеха не прочлись ({e}) — сужу как раньше")
        return lambda _s: True          # не знаем — не мешаем
    if not imena:
        return lambda _s: True
    return lambda s: s in imena

# SUDYA_BEZ_PRIZRAKOV_V1 - marker

# SVOI_SDELKI_VIDNO_V1 - marker

# ODNA_TOCHKA_ZA_RAZ_V1 - marker

# NOGI_SCHYOTNYE_V1 - marker

# VERSHINA_NE_NIZHE_KRAYA_V1 - marker

# AC_VON_V1 - marker
