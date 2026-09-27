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

import json
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

# UBORKA_03_09_V1: _ISKRA и _SENSORS убраны — не читались нигде
# в репо после упразднения Совета 06.08 (кто будит кого, решает
# cartridge_registry). _ARKHIV ниже жив, его не трогаем.

# Архивариус — память, без рынка (сам читает шину). Живёт в конторе.
_ARKHIV = ("A05", "контора", "архивариус", "run_arkhiv")

# ═══════════════════════════════════════════════════════════
# ZAKON_KARTRIDZHA_V1 — СОВЕТ БОЛЬШЕ НЕ ДЕРЖИТ СПИСКА
# ═══════════════════════════════════════════════════════════
# Здесь лежал вбитый список трёх трейдеров. Это было единственное
# место в городе, где Закон Картриджа нарушался: слот несёт с собой
# всё, но Совет звал троих ПОИМЁННО — и новый картридж, сколько его
# ни клади в папку, никто не звал.
#
# Теперь Совет СКАНИРУЕТ цех, как всё прочее в городе сканирует папки.
# Вставил картридж — он в Совете. Вынул — его нет. Хоть три, хоть
# десять.
#
# Как Совет понимает, как звать мозг:
#   1. запись слота в манифесте цеха: «движок» (какую функцию звать)
#      и «ключ» (приставка полей решения);
#   2. записи нет — зовём функцию `run`, ключ выводим из имени слота.
_CEH_TORGOVYY = "торговый_хаос"


def _dver_mozga(brain, skazano: str = "") -> str:
    """Как звать этот мозг. Сказано в манифесте — зовём так."""
    if skazano and getattr(brain, skazano, None):
        return skazano
    if getattr(brain, "run", None):
        return "run"                       # общая дверь картриджа
    est = [n for n in dir(brain)
           if n.startswith("run_") and callable(getattr(brain, n, None))]
    return est[0] if len(est) == 1 else ""


def _treydery(ceh_id: str = _CEH_TORGOVYY) -> list:
    """Кто сегодня за столом. Списка не держим — смотрим цех."""
    korn = _REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh_id
    sloty_dir = korn / "слоты"
    if not sloty_dir.is_dir():
        return []

    skazano = {}
    try:
        m = json.loads((korn / "manifest.json").read_text(encoding="utf-8"))
        for s in m.get("слоты", []) or []:
            if s.get("слот"):
                skazano[s["слот"]] = s
    except Exception:
        pass

    imena = list(skazano) + [d.name for d in sorted(sloty_dir.iterdir())
                             if d.is_dir() and d.name not in skazano]
    out = []
    for slot in imena:
        if not (sloty_dir / slot / "мозг.py").exists():
            continue                       # папка без мозга — не картридж
        zapis = skazano.get(slot, {})
        brain = _slot_brain(ceh_id, slot)
        if brain is None:
            continue
        dver = _dver_mozga(brain, zapis.get("движок", ""))
        if not dver:
            print(f"[СОВЕТ] не понял, как звать {ceh_id}/{slot} — пропускаю. "
                  f"Впиши «движок» в манифест цеха.")
            continue
        klyuch = (zapis.get("ключ") or slot).strip().lower()
        out.append((slot, ceh_id, slot, dver, klyuch))
    return out


def _stol_klyuchi(ceh_id: str = _CEH_TORGOVYY) -> dict:
    """слот -> ключ на столе. Тоже из сканера, не из головы."""
    return {slot: pre for _aid, _c, slot, _fn, pre in _treydery(ceh_id)}

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

# ZAKON_KARTRIDZHA_V1: было вбито {"A06": "brut", ...}. Теперь ключи
# приходят от того же сканера, что и сами трейдеры, — один источник.


def _steret_verdikt(slot: str, prichina: str = ""):
    """Стирает вердикт упавшего трейдера со стола. Он молчал — значит
    REJECTED. Старый вердикт с прошлого бара торговать НЕ ИМЕЕТ ПРАВА."""
    key = _stol_klyuchi().get(slot)
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
        # SOVET_CHEREZ_KRAN_V1: спрашиваем бары у КРАНА, а не у
        # терминала напрямую. Кран сам знает, какой режим включён
        # кнопкой: тестер — читает CSV и MT5 не трогает вообще,
        # реал — идёт в терминал, как и раньше.
        #
        # Прежде здесь стоял прямой вызов mt5_feed.pull_bars, который
        # про кран не знает. А он внутри на КАЖДОМ обращении делает
        # mt5.initialize() и следом mt5.shutdown() — поднимает живой
        # терминал и тут же гасит. На сплошном прогоне это сотни
        # циклов «включить-выключить» подряд: терминал терял связь и
        # ругался, хотя история читается из файлов и живой рынок там
        # не нужен вовсе.
        try:
            from feed_source import bars as _kran
            bars, _point = _kran(symbol, timeframe, 300)
        except Exception as _e_kran:
            print(f"[СОВЕТ] кран недоступен ({_e_kran}) — иду прежним путём")
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


def _para_slota(ceh_id: str, slot: str) -> dict:
    """Чем и на каком этаже работает ЭТО место. RABOTA_PO_PARE_V1.

    Один трейдер — один инструмент, свой. Кабинетного «общего» тут
    нет: он и был тем четвёртым, которого никто не выбирал, а
    работали по нему все трое.

    Запасная пара нужна ровно одному случаю — прогону тестера, где
    инструмент задан файлом истории. В живой работе она пустая.
    """
    try:
        import vybor
        r = vybor.rabota_dlya(ceh_id, slot)
        if r.get("готов"):
            return {"symbol": r["инструмент"], "timeframe": r["этаж"],
                    "готов": True, "почему": ""}
        # UBRAT_CHETVERTOGO_V1: запасной пары БОЛЬШЕ НЕТ. Она была
        # задумана «для тестера», но кабинет всегда передавал свою —
        # и запасная срабатывала всегда, подменяя собой всю
        # постройку. Три трейдера получали четвёртый инструмент.
        # Не выбрал — молчит. Молчание честнее подставного рынка.
        return {"symbol": "", "timeframe": "", "готов": False,
                "почему": vybor.pochemu_molchit(ceh_id, slot)}
    except Exception as e:
        return {"symbol": "", "timeframe": "", "готов": False,
                "почему": f"пара не прочиталась ({e})"}


# ═══════════════════════════════════════════════════════════
# KLYUCH_PROBUZHDENIYA_V1 — зовём по ключу, не бар за баром
# ═══════════════════════════════════════════════════════════
# КАНОН_ВХОДА §4.4: у каждого свой факт-ключ, событие, на которое он
# просыпается. Ключа не было, потому что корень — точка ноль — не
# зажигался ни разу с 06.08 (Искра уехала в архив вместе с рукой).
#
# Это НЕ ворота. Ворота (сняты 06.08) судили, годится ли вход, и
# выкашивали 87% честных точек. Ключ не судит ничего: он отвечает
# только на «есть ли на что смотреть». Что делать — решает трейдер,
# глядя на график.
#
# Любой сбой внутри — БУДИМ. Пропустить взгляд из-за нашей ошибки
# хуже, чем лишний раз заплатить за вызов.

_ZHIVYE_STATUSY = ("WATCHING", "PENDING", "OPEN")


def _uslyshat_nablyudenie(slot: str, symbol: str, timeframe: str,
                          skazal: str, verdikt: str) -> None:
    """NABLYUDENIE_V1: услышать слово трейдера про наблюдение.

    НАБЛЮДАЮ: <за чем>  — берём на карандаш, будим дальше
    УХОЖУ               — снимаем
    вход (APPROVED)     — снимаем: дальше ведёт позиция

    Слова нет — ничего не меняем. Молчание не отменяет прежнего
    решения и не заводит нового.
    """
    try:
        import hooks
        tekst = (skazal or "")
        verh = tekst.upper()
        if (verdikt or "").upper() == "APPROVED":
            hooks.snyat_nablyudenie(symbol, timeframe, slot, "вошёл")
            return
        if "УХОЖУ" in verh:
            hooks.snyat_nablyudenie(symbol, timeframe, slot, "сказал УХОЖУ")
            return
        # SLYSHIM_ZHDU_V1: слышим обычную речь, а не только ритуал.
        # В прогоне 21.08 трейдер сказал «жду» почти в каждом из
        # пятнадцати ответов, а ритуальное НАБЛЮДАЮ — дважды. Требовать
        # волшебное слово, когда человек говорит обычное, — это наша
        # неудобная кнопка, а не его невнимательность.
        _ZHDU = ("НАБЛЮДАЮ", "ЖДУ", "ЖДАТЬ", "ПОДОЖДУ", "ДОЖДУСЬ",
                 "ПОКА РАНО", "ЖДЁМ", "ЖДЕМ")
        if any(s in verh for s in _ZHDU):
            za = ""
            for stroka in tekst.splitlines():
                _v = stroka.upper()
                if any(s in _v for s in _ZHDU):
                    za = stroka.split(":", 1)[1] if ":" in stroka else stroka
                    break
            bar = ""
            try:
                bar = str((hooks.load_trading_state().get("рынок") or {})
                          .get("бар") or "")
            except Exception:
                pass
            hooks.vzyat_na_karandash(symbol, timeframe, slot, za, bar)
    except Exception as e:
        print(f"[НАБЛЮДЕНИЕ] слово не разобрано ({e}) — работаем дальше")



# ═══ NEKRON_BUDIT_V1 ═══
# Два повода ВЗГЛЯНУТЬ. Ни один ничего не судит: некрон говорит
# КОГДА (приходит на самом баре), излом ур.2 говорит ГДЕ (дозревает
# позже). Годится место или нет — решает тот, кто смотрит.

# DVE_SVECHI_V1 (слово Шефа 25.09): разворот двумя свечами. Волны
# не зависят от того, как терминал режет бары: первая свеча сделала
# край, вторая закрылась в другую сторону. Склеиваем их в одну
# (открытие первой, закрытие второй, общий край) и проверяем той же
# формулой разворотника.
def _dve_svechi(bs, al) -> str:
    try:
        from williams_core import detect_necron_bar as _dnb
        if not bs or len(bs) < 10:
            return ""
        J = list(al.get("jaw_series") or [])
        T = list(al.get("teeth_series") or [])
        L = list(al.get("lips_series") or [])
        if len(J) < len(bs) or len(T) < len(bs) or len(L) < len(bs):
            return ""
        J, T, L = J[:len(bs)], T[:len(bs)], L[:len(bs)]
        # первая из двух сама была разворотником — её уже будили
        if _dnb(bs[:-1], J[:-1], T[:-1], L[:-1]).get("direction"):
            return ""
        a, b = bs[-2], bs[-1]
        g = {"date": b.get("date"), "open": a["open"],
             "high": max(a["high"], b["high"]),
             "low": min(a["low"], b["low"]), "close": b["close"],
             "volume": (a.get("volume") or 0) + (b.get("volume") or 0)}
        r = _dnb(bs[:-2] + [g], J[:-2] + [J[-1]], T[:-2] + [T[-1]],
                 L[:-2] + [L[-1]])
        if not r.get("direction"):
            return ""
        return (f"разворот двумя свечами {str(a.get('date'))[:16]} + "
                f"{str(b.get('date'))[:16]}: {r['direction']} @ "
                f"{r['price']} — считай их одним разворотником")
    except Exception as _e_dv:
        print(f"[КЛЮЧ] разворот двумя свечами не посчитался: {_e_dv}")
        return ""


def _povod_vzglyada(symbol: str, timeframe: str) -> str:
    """Строка-причина, если на этом баре есть на что взглянуть."""
    try:
        from feed_source import bars as _bars
        from williams_core import compute_alligator, detect_necron_bar
        import izlomy as _izl
        bs, point = _bars(symbol, timeframe, 300)
        try:
            import hooks as _h
            bs = _h._tolko_zakrytye(bs)
        except Exception:
            pass
        if not bs or len(bs) < 60:
            return ""
        _h_ = [b["high"] for b in bs]
        _l_ = [b["low"] for b in bs]
        al = compute_alligator(_h_, _l_, point=point)
        povody = []
        rb = detect_necron_bar(bs, al.get("jaw_series"),
                               al.get("teeth_series"), al.get("lips_series"))
        if rb.get("direction"):
            povody.append(f"разворотный бар {rb['direction']} @ {rb['price']}")
        # DVE_SVECHI_V1: одиночного нет — может, разворот двумя свечами
        elif _dve_svechi(bs, al):
            povody.append(_dve_svechi(bs, al))
        # PRISEDANIE_POSLE_V1 (слово Шефа: окно три бара — и до, и
        # после разворотника). Этот бар — приседающий, а разворотник
        # был бар-два назад без приседающего до и на себе: будим.
        elif len(bs) >= 8:
            try:
                from williams_core import compute_mfi as _mfi_p

                def _sq_p(m):
                    return (_mfi_p(bs[-m], bs[-m - 1], point=point)
                            .get("type") == "SQUAT")

                if _sq_p(1):
                    # TRI_BARA_V2: до трёх баров после разворотника
                    for _k in (1, 2, 3):
                        _n = len(bs) - _k
                        _rbk = detect_necron_bar(
                            bs[:_n], (al.get("jaw_series") or [])[:_n],
                            (al.get("teeth_series") or [])[:_n],
                            (al.get("lips_series") or [])[:_n])
                        if not _rbk.get("direction"):
                            continue
                        _do = any(_sq_p(_k + 1 + j) for j in range(4))
                        _mezhdu = any(_sq_p(j) for j in range(2, _k + 1))
                        if not _do and not _mezhdu:
                            _d_p = str(bs[-(_k + 1)].get("date") or "")[:16]
                            povody.append(
                                f"к разворотнику {_rbk['direction']} {_d_p} "
                                f"@ {_rbk['price']} пришёл приседающий через "
                                f"{_k} бар(а) — в окне трёх баров, считается")
                        break
            except Exception as _e_p:
                print(f"[КЛЮЧ] приседающий после разворотника не "
                      f"посчитался: {_e_p}")
        # KLYUCH_TOLKO_NEKRON_V1: излом больше не будит. Он говорит
        # ГДЕ и дозревает позже — это второй уровень. Трейдера будили
        # изломом «18 баров назад», а он искал разворотный бар на
        # правом краю и рассказывал про него: разбор выходил не про
        # ту картинку. Считаться излом продолжает, будить — нет.
        _ = _izl
        return "; ".join(povody)
    except Exception as _e:
        # Сбой прибора — НЕ повод будить на каждом баре: остальные
        # ключи (заявка, вход, закрытие, события структуры) на месте
        # и сработают сами.
        print(f"[КЛЮЧ] повод взгляда не посчитался: {_e}")
        return ""


def _klyuch_probuzhdeniya(symbol: str, timeframe: str,
                          slot: str = "") -> dict:
    """Есть ли повод звать того, кто работает этой парой."""
    try:
        import hooks
        t = hooks.load_trading_state()

        # Будим на РОЖДЕНИИ точки, а не каждый бар, пока она жива.
        # Слово Шефа (20.08): «Нине важно решить сначала, истинный ли
        # он; если да — математика пусть ведёт. Откат не случится ни на
        # втором, ни на третьем, ни даже на десятом баре».
        tch = hooks._blok_tochki(t, hooks._para_tochki(symbol, timeframe))
        bar_goroda = str(((t.get("рынок") or {}).get("бар")) or "")
        _ = slot   # KONEC_VOLNY_1_V1: наблюдение больше не ключ

        # NEKRON_BUDIT_V1: сперва — есть ли на что ВЗГЛЯНУТЬ. Раньше
        # первым стояло рождение точки ноль, то есть наша разметка
        # решала, откроет ли человек график. Отбор числами закрыт
        # шестью замерами — ворот здесь больше нет.
        _vz = _povod_vzglyada(symbol, timeframe)
        if _vz:
            return {"будим": True, "почему": _vz}
        rodilas = str(tch.get("rodilas_na_bare") or "")
        if tch.get("alive") and bar_goroda and rodilas == bar_goroda                 and not tch.get("barov_s_tochki"):
            return {"будим": False,      # KLYUCH_TOLKO_NEKRON_V1
                    "почему": f"точка родилась: {tch.get('trend_direction')} @ "
                              f"{tch.get('zero_point_price')}"}

        # POZICIYA_NE_KAZHDYY_BAR_V1: заявка и позиция будят по
        # СОБЫТИЮ, а не по факту существования. Раньше открытая позиция
        # звала каждый бар — одна сделка на десять дней стоила шестьдесят
        # оплаченных взглядов. Стоп ведёт код по фракталам, смотреть
        # каждую свечу человеку не за чем: побарный мониторинг — ошибка
        # большинства трейдеров (слово Шефа).
        sym = (symbol or "").strip().upper()
        for p in (t.get("positions") or []):
            if p.get("status") not in _ZHIVYE_STATUSY:
                continue
            psym = (p.get("symbol") or "").strip().upper()
            # инструмента в записи нет (старая позиция) — считаем своей
            if psym and sym and psym != sym:
                continue
            _st = p.get("status")
            if _st in ("WATCHING", "PENDING"):
                return {"будим": True,
                        "почему": f"своя {_st} — заявка ещё висит"}
            # открылась на ЭТОМ баре — вошёл, надо сказать
            if bar_goroda and str(p.get("opened_at") or "") == bar_goroda:
                return {"будим": True,
                        "почему": f"вошёл @ {p.get('entry')} — позиция открыта"}
            # KOLOKOL_BUDIT_V1: колокол начал звонить на этом баре —
            # будим. Закрывать или держать — решает трейдер.
            if bar_goroda and str(p.get("колокол") or "") == bar_goroda:
                _dk = str(p.get("direction") or "LONG").upper()
                _chto_k = ("медвежье расхождение AO — ход вверх "
                           "выдыхается" if _dk == "LONG" else
                           "бычье расхождение AO — ход вниз выдыхается")
                return {"будим": True,
                        "почему": f"звонит колокол: {_chto_k}. Реши "
                                  f"сама — держать или закрыть"}
            # просто стоит открытой — молчим, стоп ведёт код

        # закрылась на этом баре — чем кончилось
        _z = t.get("последнее_закрытие") or {}
        if (_z and bar_goroda
                and str(_z.get("бар") or "") == bar_goroda):
            _zsym = (_z.get("symbol") or "").strip().upper()
            if not (_zsym and sym and _zsym != sym):
                return {"будим": True,
                        "почему": f"сделка закрылась: {_z.get('причина')} "
                                  f"@ {_z.get('выход')}"}

        # KONEC_VOLNY_1_V1: второе СОБЫТИЕ, ради которого всё. Волна 1
        # от точки кончилась — значит есть от чего ждать откат. Слово
        # Шефа: побарный мониторинг — ошибка большинства трейдеров;
        # трейдер ждёт событие, а не пялится в каждую свечу.
        kv = tch.get("konec_volny_1") or {}
        if kv and str(kv.get("бар") or "") == bar_goroda and bar_goroda:
            # KRAY_VOLNY_V1: первый раз — кончилась; дальше край просто
            # сдвинулся, и волна продолжается. Разные события — разные
            # слова, иначе трейдер спорит с ключом и он прав.
            _st = tch.get("trend_direction")
            _kray = "вершина" if _st == "BULL" else "дно"
            _ok = "лась" if _st == "BULL" else "лось"
            # PEREEZD_VERSHINY_TIKHIY_V1: переезд края — НЕ СОБЫТИЕ.
            #
            # Вершина подтягивается за ценой (VERSHINA_NE_NIZHE_KRAYA_V1)
            # и в сильном импульсе едет чуть не каждый бар. Раньше на
            # каждый такой переезд будили обоих трейдеров — шесть побудок
            # подряд там, где волна просто продолжается. Каждая побудка —
            # запрос к модели за деньги Шефа, а трейдеру показать нечего:
            # он отвечал «откат слишком мелкий, жду».
            #
            # Слово Шефа, записанное строкой выше: трейдер ждёт СОБЫТИЕ,
            # а не пялится в каждую свечу. Край, который ползёт за ценой,
            # событием не является — состояние обновляется молча, на
            # столе всегда свежая вершина, глубина отката честная.
            #
            # Событие впереди своё: откат кончился (KONEC_VOLNY_2_V1).
            # Вот тогда и позовём.
            if kv.get("сдвинулась"):
                return {"будим": False,
                        "почему": f"{_kray} волны 1 переехал{'а' if _st == 'BULL' else 'о'} "
                                  f"на {kv.get('цена')} — волна идёт, "
                                  f"событие впереди"}
            return {"будим": False,      # KLYUCH_TOLKO_NEKRON_V1
                    "почему": f"волна 1 кончилась, {_kray} @ "
                              f"{kv.get('цена')} "
                              f"({kv.get('баров_от_точки')} бар. от точки)"}

        # KONEC_VOLNY_2_V1: третье событие — откат к первой волне
        # кончился. Момент того, кто работает третье место.
        kv2 = tch.get("konec_volny_2") or {}
        if kv2 and str(kv2.get("бар") or "") == bar_goroda and bar_goroda:
            return {"будим": False,      # KLYUCH_TOLKO_NEKRON_V1
                    "почему": f"откат кончился @ {kv2.get('цена')} "
                              f"({kv2.get('баров_от_макушки')} бар. от "
                              f"{'вершины' if tch.get('trend_direction') == 'BULL' else 'дна'})"}

        # «Наблюдаю» само по себе дверь НЕ открывает: пока трейдер
        # следит, город считает молча и бесплатно.
        return {"будим": False, "почему": "точки нет, события нет, "
                                          "позиции нет"}
    except Exception as e:
        return {"будим": True, "почему": f"ключ не сработал ({e}) — зову"}


def wake_council(symbol: str = "", timeframe: str = "",
                 on_event: Optional[Callable] = None,
                 window=None, point=None,
                 ceh_id: str = _CEH_TORGOVYY) -> dict:
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

    # SVOY_STOL_CEHA_V1: сказать столу, чей цех сегодня работает —
    # чтобы стол и позиции легли к нему, а не в общую тетрадь.
    try:
        import hooks as _h
        if hasattr(_h, "postavit_ceh"):
            _h.postavit_ceh(ceh_id)
    except Exception:
        pass

    # ── РЫНОК СУДИТ ПЕРВЫМ (RUKA_RYNKA_V1) ──────────────────
    # Физика раньше мнений: что рынок взял и что закрыл, решается до
    # того, как за столом кто-то откроет рот. Без этого шага заявка
    # висела вечно, а позиция не закрывалась никогда — обе руки в
    # hooks.py были целы, но их не звал никто с 06.08.
    _sudil = set()   # RABOTA_PO_PARE_V1: какие рынки уже рассудили
    # RABOTA_PO_PARE_V1: у каждого свой рынок, значит и судить надо
    # каждый рынок отдельно — своим баром. Пары повторяются редко, но
    # если двое работают одним инструментом на одном этаже, второй
    # раз не судим.
    _za_stolom = _treydery(ceh_id)
    _pary = {}
    for _aid, _c, _slot, _fn, _pre in _za_stolom:
        _p = _para_slota(ceh_id, _slot)   # UBRAT_CHETVERTOGO_V1
        _pary[_slot] = _p
        if not _p["готов"]:
            # VYBOR_NE_PRI_MESTE_V1: сюда попадает и пустое место —
            # и попадает ДО того, как рынок будет рассужен его парой.
            # Раньше вакансия с инструментом из поста доводила дело до
            # ключа и падала уже в мозге («носителя нет»), успев
            # посчитать чужой рынок и родить точку в общем столе.
            print(f"[СОВЕТ] 🤐 {_slot} молчит: {_p['почему']}")
            _emit({"type": "молчит", "slot": _slot, "почему": _p["почему"]})
            continue
        _klyuch = (_p["symbol"], _p["timeframe"])
        if _klyuch in _sudil:
            continue
        _sudil.add(_klyuch)
        try:
            import hooks as _hr
            _rynok = _hr.rynok_novyy_bar(
                _p["symbol"], _p["timeframe"],
                window=window if _klyuch == (symbol, timeframe) else None,
                point=point if _klyuch == (symbol, timeframe) else None)
            # окно передаём только если кабинет прислал бары ИМЕННО
            # этой пары; иначе рука сама возьмёт из крана — свои.
            if _rynok.get("активировано") or _rynok.get("закрыто"):
                _emit({"type": "рынок", "рынок": _p["symbol"],
                       "этаж": _p["timeframe"], **_rynok})
        except Exception as _er:
            print(f"[РЫНОК] ⚠️  {_p['symbol']} {_p['timeframe']} "
                  f"не рассужен: {_er}")

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

    # ── трейдеры: сколько картриджей в цехе, столько и зовём ──
    if not _za_stolom:
        print("[СОВЕТ] в цехе нет ни одного картриджа с мозгом")
    for aid, ceh, slot, fn, pre in _za_stolom:
        # RABOTA_PO_PARE_V1: каждому — ЕГО инструмент и ЕГО этаж.
        _p = _pary.get(slot) or _para_slota(ceh_id, slot)
        if not _p["готов"]:
            summary["verdicts"][aid] = None
            summary["results"][aid] = {"ok": False, "error": _p["почему"],
                                       "молчит": True}
            continue
        # KLYUCH_PROBUZHDENIYA_V1: зовём по ключу, не бар за баром.
        _k = _klyuch_probuzhdeniya(_p["symbol"], _p["timeframe"], slot)
        if not _k["будим"]:
            print(f"[КЛЮЧ] 🔒 {slot} спит: {_k['почему']}")
            summary["verdicts"][aid] = None
            summary["results"][aid] = {"ok": False, "спит": True,
                                       "error": _k["почему"]}
            _emit({"type": "спит", "slot": slot, "почему": _k["почему"]})
            continue
        print(f"[КЛЮЧ] 🔑 {slot}: {_k['почему']}")
        print(f"[СОВЕТ] 👤 {slot}: {_p['symbol']} {_p['timeframe']}")
        # POVOD_VIDEN_V1: повод больше не остаётся в логе — трейдер
        # должен знать, что именно его разбудило. Иначе он сочиняет
        # себе ожидание бара, который уже случился.
        r = _call(ceh, slot, fn,
                  symbol=_p["symbol"], timeframe=_p["timeframe"],
                  povod=_k.get("почему", ""))
        summary["woke"].append(aid)
        summary["results"][aid] = r
        sig = r.get("signal", {}) or {}
        # NABLYUDENIE_V1: ловим слово трейдера — НАБЛЮДАЮ / УХОЖУ.
        _uslyshat_nablyudenie(slot, _p["symbol"], _p["timeframe"],
                              r.get("narrative", ""),
                              sig.get(f"{pre}_verdict"))
        summary["verdicts"][aid] = sig.get(f"{pre}_verdict")
        _emit({"type": "agent", "id": aid, "ok": r.get("ok"),
               "result": r, "verdict": sig.get(f"{pre}_verdict"),
               "narrative": r.get("narrative", "")})

    # ── Исполнитель (рука-код открывает по табло) ──
    aid, ceh, slot, fn = _EXECUTOR
    # OTPERET_V1: контора торгует не по инструменту — ей нужен стол
    # цеха, а не чей-то этаж. Кабинет своей пары больше не имеет, и
    # пустое доезжало до крана: «[FEED] Неизвестный таймфрейм ''».
    # Пары нет — берём ту, по которой реально работали в этот проход.
    _sym_i, _tf_i = symbol, timeframe
    if not (_sym_i and _tf_i):
        for _p_i in _pary.values():
            if _p_i.get("готов"):
                _sym_i, _tf_i = _p_i["symbol"], _p_i["timeframe"]
                break
    rex = _call(ceh, slot, fn, symbol=_sym_i, timeframe=_tf_i)
    summary["woke"].append(aid)
    summary["results"][aid] = rex
    esig = rex.get("signal", {}) or {}
    summary["orders"] = (esig.get("final_dna", {}) or {}).get("orders_sent")
    _emit({"type": "agent", "id": aid, "ok": rex.get("ok"),
           "result": rex, "orders": summary["orders"],
           "narrative": rex.get("narrative", "")})

    return summary

# ZAKON_KARTRIDZHA_V1 - marker

# SVOY_STOL_CEHA_V1 - marker

# RABOTA_PO_PARE_V1 - marker

# UBRAT_CHETVERTOGO_V1 - marker

# OTPERET_V1 - marker

# KLYUCH_PROBUZHDENIYA_V1 - marker

# NABLYUDENIE_V1 - marker

# KONEC_VOLNY_1_V1 - marker

# SLYSHIM_ZHDU_V1 - marker

# KONEC_VOLNY_2_V1 - marker

# KRAY_VOLNY_V1 - marker

# POZICIYA_NE_KAZHDYY_BAR_V1 - marker

# VYBOR_NE_PRI_MESTE_V1 - marker

# SOVET_CHEREZ_KRAN_V1 - marker

# PEREEZD_VERSHINY_TIKHIY_V1 - marker

# NEKRON_BUDIT_V1 - marker

# UBORKA_03_09_V1 - marker
