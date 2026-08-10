# Биржа/council.py
# ─────────────────────────────────────────────────────────────
# ЧИСТАЯ БУДИЛКА СОВЕТА — одно место, где оживает девятка.
# ENGINE_ONE_DOOR_V1 · перенесён из -2 (studio/modules/trading/council.py)
#   на новую топологию слотов (Закон Картриджа: _slot_brain).
#
# ЗАКОН (наказ Шефа): одно место пробуждения Совета на ОБА мира.
# Раньше Совет будился в ДВУХ местах руками — в кнопке РЫНОК (с UI)
# и в тестере (своя лестница). Это и был маскарад. Теперь — одна
# лестница, без UI. Реал и тест зовут ЕЁ, отличаясь только источником
# бара (его подал движок снаружи) и тем, куда слать вести (on_event).
#
# Порядок ОДИН-В-ОДИН с кнопкой РЫНОК (ui_torg):
#   Искра → Морж → Паникёр → Ганс → Архивариус
#        → [Брут · Авантюрист · Консерватор] → Исполнитель
#
# Движок НЕ дублирует агентов — зовёт ЖИВЫЕ run_* через _slot_brain.
# Слеп к активу/ТФ.
#
# ── ОТЛИЧИЕ ОТ -2 (топология) ──
# В -2 агенты жили плоско (studio.modules.trading.morj_live) и звались
# через importlib.import_module. В новом городе они живут в слотах цехов
# (Закон Картриджа), и зовутся через _slot_brain(ceh_id, slot).мозг.
# Раскладка «кто в каком цехе/слоте» — единственное, что тут ново.
# Порядок, ворота по спуску, мягкость к сбоям — как в -2, один-в-один.
# ─────────────────────────────────────────────────────────────

import importlib.util
from pathlib import Path
from typing import Optional, Callable

_HERE = Path(__file__).resolve().parent            # Биржа/
_REPO = _HERE.parent                                # корень репо
_BRAIN_CACHE: dict = {}


def _slot_brain(ceh_id: str, slot: str):
    """
    Закон Картриджа для кода — тот же механизм, что в ui_torg.py и
    tester_express.py (_slot_brain, байт-в-байт). Мозг слота живёт в
    GRONDHEIM_CITY/Биржа/цеха/{ceh_id}/слоты/{slot}/мозг.py — не
    захардкожен списком имён. Нет файла — честная вакансия (None),
    не ошибка. Кэш на процесс.
    """
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


# ── РАСКЛАДКА СОВЕТА: кто в каком цехе/слоте ──
# Единственное место правды о том, где живёт каждый агент. Порядок в
# кортежах = порядок пробуждения (после Искры). ceh_id/slot идут в
# _slot_brain, run — имя функции в мозге слота.

# Искра — голова, будится первой отдельно (ворота по её спуску).
_ISKRA = ("торговый_хаос", "A01", "run_iskra")

# сенсоры после Искры — порядок как в кнопке РЫНОК
_SENSORS = [
    ("A02", "торговый_хаос", "A02", "run_morj"),
    ("A03", "торговый_хаос", "A03", "run_panikyor"),
    ("A04", "торговый_хаос", "A04", "run_hans"),
]

# Архивариус — память, без рынка (сам читает шину). Живёт в конторе.
_ARKHIV = ("A05", "контора", "архивариус", "run_arkhiv")

# трое трейдеров за столом
_TRADERS = [
    ("A06", "торговый_хаос", "A06", "run_brut", "brut"),
    ("A07", "торговый_хаос", "A07", "run_avan", "avan"),
    ("A08", "торговый_хаос", "A08", "run_cons", "cons"),
]

# Исполнитель — рука-код, замыкает петлю. Живёт в конторе.
_EXECUTOR = ("A09", "контора", "исполнитель", "run_executor")


# ═══════════════════════════════════════════════════════════
# NET_PRIZRAKOV_V1 — МЁРТВЫЙ АГЕНТ НЕ ТОРГУЕТ
# ═══════════════════════════════════════════════════════════
# Лог Шефа 14.07: Илья упал (OpenRouter вернул пустое тело) — а
# Исполнитель открыл SHORT @1202.44 по его СТАРОМУ вердикту, при том
# что цена на баре была 1367-1387, а компас показывал BULL.
#
# Трейдер пишет вердикт в стол САМ, в конце run_*. Упал раньше — не
# написал — в столе остался прошлый. Живой, с ценами другой эпохи.
#
# ПРАВИЛО: сбой → вердикт ОБНУЛЯЕТСЯ. Молчание — это REJECTED, а не
# согласие. Иначе судья потом впишет Илье «МОЯ ОШИБКА» за решение,
# которого он не принимал — и это отравит его опыт КЛЕВЕТОЙ.
# ═══════════════════════════════════════════════════════════

# кто где живёт в столе (проверено на диске: A06/A07/A08 :: мозг.py)
_STOL_KEY = {"A06": "brut", "A07": "avan", "A08": "cons"}


def _steret_verdikt(slot: str, prichina: str = ""):
    """Стирает вердикт упавшего трейдера со стола. Он молчал — значит
    REJECTED. Старый вердикт с прошлого бара торговать НЕ ИМЕЕТ ПРАВА."""
    key = _STOL_KEY.get(slot)
    if not key:
        return
    try:
        from hooks import load_trading_state, save_trading_state
        t = load_trading_state()
        staryi = (t.get(key, {}) or {}).get("verdict")
        t.setdefault(key, {})
        t[key] = {
            "verdict":   "REJECTED",
            "reason":    f"агент не ответил ({prichina[:60]})",
            "direction": None,
            "entry":     None,
            "stop":      None,
            "lot":       None,
            "action":    None,
            "new_stop":  None,
            "add_lot":   None,
        }
        save_trading_state(t)
        if staryi and staryi != "REJECTED":
            print(f"[ПРИЗРАК] 🚫 {slot} упал — стёр его старый вердикт "
                  f"«{staryi}». Мёртвый агент НЕ ТОРГУЕТ.")
        else:
            print(f"[ПРИЗРАК] 🚫 {slot} упал — стол очищен (REJECTED)")
    except Exception as e:
        print(f"[ПРИЗРАК] ⚠️  не смог стереть вердикт {slot}: {e}")


def _call(ceh_id: str, slot: str, fn_name: str, **kw) -> dict:
    """Зовёт живой run_* агента через слот. Любой сбой — мягко, не
    роняем Совет (честная вакансия/ошибка отдаётся как {ok:False})."""
    # NET_PRIZRAKOV_V1: ЛЮБОЙ сбой агента → его вердикт на столе
    # ОБНУЛЯЕТСЯ. Без этого Исполнитель откроет позицию по СТАРОМУ
    # вердикту с прошлого бара — что и случилось 14.07: Илья упал
    # (OpenRouter вернул пустое тело), а SHORT открылся @1202.44 при
    # цене 1367-1387 и компасе BULL. Мёртвый агент НЕ ТОРГУЕТ.
    #
    # Ловим на ВЫХОДЕ: главный случай — не исключение, а мозг,
    # который САМ вернул {"ok": False} из `fn(**kw)`.
    _res = None
    try:
        brain = _slot_brain(ceh_id, slot)
        if brain is None:
            _res = {"ok": False, "error": f"{ceh_id}/{slot}: мозг ещё не в слоте"}
        else:
            fn = getattr(brain, fn_name, None)
            if fn is None:
                _res = {"ok": False, "error": f"{ceh_id}/{slot}: нет {fn_name}"}
            else:
                _res = fn(**kw) or {}
    except Exception as e:
        _res = {"ok": False, "error": f"{fn_name}: {e}"}

    if not (_res or {}).get("ok"):
        _steret_verdikt(slot, str((_res or {}).get("error", "сбой")))

    return _res


# ═══════════════════════════════════════════════════════════
# COUNCIL_GATE_TROYNOY_V1 — дешёвая проверка триггеров Б/В (без LLM)
# ═══════════════════════════════════════════════════════════

_HANS_TO_BULL_BEAR = {"LONG": "BULL", "SHORT": "BEAR"}  # TRIGGERS_SINHRON_V1


def _deshyovaya_proverka_tochki(symbol: str, timeframe: str,
                                window=None, point=None) -> dict:
    """
    Код, без LLM. Строит md (переданным окном ИЛИ тянет бары сама —
    живой режим), спрашивает proverit_tochku() (TOCHKA_ZHIVA_V1) и,
    если точка жива, ищет ДВА дешёвых триггера на ЭТОМ баре:
      фрактал Ганса вне пасти (_hans_breakout, уже есть в hooks.py)
      Большой палец Авантюриста (md["thumb_trade"], TWR_BOLSHOY_PALEC_V1)

    Возвращает {"trigger": bool, "kind": "fractal"|"thumb"|None,
                "napravlenie": str|None, "tochka": {...}}.
    Пустой/недоступный md — честное "нет триггера", не ошибка.
    """
    from hooks import proverit_tochku, _hans_breakout
    from williams_core import build_market_data

    bars = window
    _point = point
    if bars is None:
        from mt5_feed import pull_bars
        bars, _point = pull_bars(symbol, timeframe, 300)

    if not bars or _point is None:
        return {"trigger": False, "kind": None, "napravlenie": None,
                "tochka": {"alive": False, "reason": "нет баров"}}

    md = build_market_data(bars, symbol=symbol, timeframe=timeframe,
                           point=_point)
    if not md:
        return {"trigger": False, "kind": None, "napravlenie": None,
                "tochka": {"alive": False, "reason": "пустой md"}}

    tochka = proverit_tochku(md)
    if not tochka.get("alive"):
        return {"trigger": False, "kind": None, "napravlenie": None,
                "tochka": tochka}

    # TRIGGERS_SINHRON_V1: направление точки — синхронность станций c→1→2.
    # Пробой фрактала/палец в ДРУГУЮ сторону — не наша волна, молчим.
    _napr_tochki = tochka.get("direction")

    # Триггер Б — фрактал Ганса пробит вне пасти на ЭТОМ баре,
    # В ТУ ЖЕ сторону, что и живая точка
    hans_dir = _hans_breakout(md, bars)
    if hans_dir is not None and _HANS_TO_BULL_BEAR.get(hans_dir) == _napr_tochki:
        return {"trigger": True, "kind": "fractal",
                "napravlenie": hans_dir, "tochka": tochka}

    # Триггер В — Большой палец Авантюриста, В ТУ ЖЕ сторону
    thumb = md.get("thumb_trade", {}) or {}
    if thumb.get("triggered") and thumb.get("direction") == _napr_tochki:
        return {"trigger": True, "kind": "thumb",
                "napravlenie": thumb.get("direction"), "tochka": tochka}

    return {"trigger": False, "kind": None, "napravlenie": None,
            "tochka": tochka}

# COUNCIL_GATE_TROYNOY_V1 - marker


def wake_council(symbol: str, timeframe: str,
                 on_event: Optional[Callable] = None,
                 window=None, point=None) -> dict:
    """
    ОЧЕРЁДНОСТЬ РАБОТЫ на текущем баре. Имя осталось прежним, чтобы
    кабинет и тестер звали как звали, но собрания больше нет.

    SOVET_BEZ_SENSOROV_V1 (решение Шефа 06.08). Было: Искра будила
    себя от рынка, её СПУСК был воротами — не нашёл точку, все
    расходятся. Сенсоры уехали в архив, значит спуска нет никогда, и
    ворота не открылись бы ни разу: трейдеры не проснулись бы вообще.

    Стало: ворот нет и сенсоров нет. Каждый трейдер накрывает себе
    стол сам (Биржа/stol.py) и сам решает — смотреть ему тут или
    расходиться. Право промолчать переехало туда, где ему место: к
    тому, кого этому учили, а не в замок на чужом сигнале.

    symbol/timeframe — паспорт, течёт в каждого. on_event(dict) —
    вести наружу (лента кабинета/тестера), может быть None.

    Возвращает ту же сводку, что и раньше: кто что сказал плюс полные
    результаты каждого (в results, чтобы UI обновил свои панели).
    Позиции открывает Исполнитель (рука-код), закрывает _settle на
    следующем баре — здесь их не трогают.
    """
    def _emit(ev):
        if on_event:
            try:
                on_event(ev)
            except Exception:
                pass

    summary = {"woke": [], "verdicts": {}, "orders": None,
               "idle": False, "results": {}}

    # ── сенсоров больше нет ───────────────────────────────────
    # Искра, Морж, Паникёр и Ганс стали математикой и уехали из цеха.
    # Их работу делает Биржа/stol.py — каждый трейдер зовёт его сам,
    # внутри своего мозга. Будить тут некого.

    # ── Архивариус (память, без рынка — сам читает шину) ──
    aid, ceh, slot, fn = _ARKHIV
    ra = _call(ceh, slot, fn)
    summary["woke"].append(aid)
    summary["results"][aid] = ra
    _emit({"type": "agent", "id": aid, "ok": ra.get("ok"),
           "result": ra, "narrative": ra.get("narrative", "")})

    # ── трое трейдеров ──
    for aid, ceh, slot, fn, pre in _TRADERS:
        r = _call(ceh, slot, fn, symbol=symbol, timeframe=timeframe)
        summary["woke"].append(aid)
        summary["results"][aid] = r
        sig = r.get("signal", {}) or {}
        summary["verdicts"][aid] = sig.get(f"{pre}_verdict")
        _emit({"type": "agent", "id": aid, "ok": r.get("ok"),
               "result": r, "verdict": sig.get(f"{pre}_verdict"),
               "narrative": r.get("narrative", "")})

    # ── Исполнитель (рука-код открывает по табло) ──
    aid, ceh, slot, fn = _EXECUTOR
    rex = _call(ceh, slot, fn, symbol=symbol, timeframe=timeframe)
    summary["woke"].append(aid)
    summary["results"][aid] = rex
    esig = rex.get("signal", {}) or {}
    summary["orders"] = (esig.get("final_dna", {}) or {}).get("orders_sent")
    _emit({"type": "agent", "id": aid, "ok": rex.get("ok"),
           "result": rex, "orders": summary["orders"],
           "narrative": rex.get("narrative", "")})

    return summary
