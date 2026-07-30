# studio/modules/trading/tester_express.py
# ─────────────────────────────────────────────────────────────
# ЭКСПРЕСС-ТЕСТЕР — живой Совет на истории (CSV), без MT5
# TESTER_EXPRESS_V1 · 2026-06-18
#
# ЧТО ЭТО. Не вторая реализация трейдеров (та разойдётся с живой).
# Это МИКРОФОН: берёт ЖИВЫХ агентов (Искра, Морж, Ганс, Паникёр,
# Архивариус, Брут — те самые *_live.py) и кормит их историей из CSV
# вместо терминала. Печатает ИХ ПОДЛИННЫЕ голоса (narrative) дословно.
# Ни одного слова за них. Тестер — микрофон, не сценарист.
#
# КАК НАХОДИТ. Не Шеф тычет бар (вдруг ошибётся). Кухня САМА ищет:
# крутит историю бар за баром ДЕШЁВОЙ Искрой; на срабатывании Искры
# (DETECTED/CONFIRMED) будит ПОЛНЫЙ Совет на этом баре и печатает их
# разговор. Ловит N срабатываний — стоп. Так проверяется КУХНЯ:
# найдёт ли цех сам то, что по канону должен найти.
#
# КАК КОРМИТ. Монки-патч mt5_feed._fetch на время прогона: вместо
# терминала отдаёт срез CSV до текущего бара (тот же формат (bars,
# point), агенты подмены не замечают). Снял патч — всё как было.
# MT5 не нужен: point берём из таблички для теста (ядро не трогаем).
#
# ЛЕСЕНКА (LADDER_MULTIFLOOR_V1): если в test_data/ нашлись файлы под
# другие этажи символа (M5/M15/.../MN1) — спуск Искры по-настоящему
# спускается по реальным историческим барам каждого этажа, honest
# срез по дате (без забегания вперёд). Каких-то этажей может не
# хватать по длине истории самого экспорта MT5 (M5/M15 короче) —
# тогда спуск честно останавливается там, где данные кончились.
#
# ЗАПУСК (из корня репы):
#   python -m studio.modules.trading.tester_express <csv> <symbol> <tf> [--signals N]
# Пример:
#   python -m studio.modules.trading.tester_express test_data/XAUUSD_H4.csv XAUUSD H4 --signals 1
# ─────────────────────────────────────────────────────────────

import sys
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent   # TESTER_EXPRESS_CARTRIDGE_V1: корень репо, для поиска мозгов
_BRAIN_CACHE: dict = {}


def _slot_brain(ceh_id: str, slot: str):
    """TESTER_EXPRESS_CARTRIDGE_V1: Закон Картриджа для кода — тот же
    механизм, что в ui_torg.py (_slot_brain). Мозг слота живёт в
    GRONDHEIM_CITY/Биржа/цеха/{ceh_id}/слоты/{slot}/мозг.py — не
    захардкожен списком имён, цех сам говорит, что там лежит. Нет
    файла — честная вакансия (None), не ошибка. Кэш на процесс."""
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
# TESTER_TRADE_FEED_V1 · лента сделок: открытие и закрытие видны в кабинете
# TESTER_STERILE_V1 · бэктест по умолчанию НЕ калечит ДНК (--learn чтобы учить)
# TESTER_CLEAN_TABLE_V1 · чистый стол на старте + settle на каждом баре
# TESTER_SETTLE_GAPS_V1 · settle прокатывается по всем барам между кандидатами
# TESTER_SETTLE_FULL_WINDOW_V1 · ведение кормит settle полным окном 300 (честный exit_bell)
# TESTER_TO_CABINET_V1 · кран+caught+развилка/прогресс через on_progress в кабинет


# ── point для теста (ТОЛЬКО здесь, ядро остаётся слепым к тикеру) ──
# Это не возврат POINT_MAP в ядро — это локальный костыль тестера,
# чтобы не поднимать MT5 ради одного числа. Не знаешь свой — кидай --point.
_HANS_TO_BULL_BEAR = {"LONG": "BULL", "SHORT": "BEAR"}  # TRIGGERS_SINHRON_V1


_TEST_POINT = {
    "XAUUSD": 0.01,   "XAGUSD": 0.001,
    "EURUSD": 0.00001, "GBPUSD": 0.00001, "USDJPY": 0.001,
    "AUDUSD": 0.00001, "USDCHF": 0.00001, "USDCAD": 0.00001,
    "BTCUSD": 0.01,   "ETHUSD": 0.01,
}


def _resolve_point(symbol: str, override) -> float:
    if override:
        return float(override)
    p = _TEST_POINT.get(symbol.upper())
    if p is None:
        print(f"⚠️  point для {symbol} неизвестен тестеру. Укажи --point "
              f"(золото 0.01, форекс 0.00001, JPY 0.001).")
        sys.exit(1)
    return p


def _bar(line_dt: str) -> str:
    """Короткая дата бара для лога."""
    return line_dt or "?"


# ── TESTER_CLEAN_TABLE_V1: чистый стол + закрытие позиций в тестере ──
def _clean_table_for_symbol(symbol):
    """Сносит стол прогоняемого символа ПЕРЕД заходом. Бэктест
    начинается с чистого листа: ни чужих позиций, ни старых
    вердиктов. Позиции без поля symbol (старая эпоха) — сносим
    тоже: доверять им нельзя, они из другого прогона/актива."""
    from hooks import (
        load_trading_state, save_trading_state)
    t = load_trading_state()
    sym = (symbol or '').upper()
    before = t.get('positions', []) or []
    # держим только ЧУЖИЕ символы с явной меткой; своё и безымянное сносим
    kept = [p for p in before
            if p.get('symbol') and p.get('symbol', '').upper() != sym]
    dropped = len(before) - len(kept)
    t['positions'] = kept
    # сбрасываем вердикты трейдеров и состояние Искры на чистый лист
    for k in ('brut', 'avan', 'cons'):
        t[k] = {}
    t['iskra'] = {'t1_status': 'NOT_FOUND',
                  'zero_point_price': None, 'history_dna': ''}
    save_trading_state(t)
    if dropped:
        print(f'[TESTER·CLEAN] снёс {dropped} позиций прошлой эпохи '
              f'(символ {sym} и безымянные) — стол чист')
    return dropped


def _settle_bar(window, symbol, timeframe, point):
    """Зовёт hooks._settle_positions на текущем баре — рынок
    закрывает позиции по стопу/колоколу САМ, как в живом
    on_before_run. В тестерном пути этого вызова не было —
    позиции жили вечно. Собираем мини-state с market_data бара."""
    from williams_core import build_market_data
    from hooks import (
        _settle_positions, load_trading_state)
    md = build_market_data(window, symbol=symbol,
                           timeframe=timeframe, point=point)
    if not md:
        return
    positions = load_trading_state().get('positions', []) or []
    if not positions:
        return
    st = {'chain_data': {'market_data': md,
                         'open_positions': positions}}
    try:
        # OTLOZHENNY_ORDER_V1: ПЕРВЫМ ДЕЛОМ — активация заявок.
        # Порядок строг: заявка → активация → трейлинг → закрытие.
        # Иначе стоп потянется у того, кто ещё НЕ ВОШЁЛ.
        try:
            from hooks import _aktivirovat_ordera
            _aktivirovat_ordera(st)
            st['chain_data']['open_positions'] = (
                load_trading_state().get('positions', []) or [])
        except Exception as _ae:
            print(f'[ОРДЕР] ⚠️  {_ae}')

        # VEDENIE_POZICII_V1: СНАЧАЛА тянем стоп за Зубами («сейф»),
        # ПОТОМ проверяем закрытие. Порядок важен: сейф должен
        # успеть сработать РАНЬШЕ, чем рынок дотянется до старого
        # стопа. Это код, не LLM — по канону (гл.10) трейлинг НЕ
        # вопрос вкуса, а закон системы.
        try:
            from hooks import _treyling_za_zubami
            _treyling_za_zubami(st)
            # стоп мог сдвинуться — перечитываем позиции
            st['chain_data']['open_positions'] = (
                load_trading_state().get('positions', []) or [])
        except Exception as _te:
            print(f'[ТРЕЙЛ] ⚠️  {_te}')

        _settle_positions(st)   # закрывает по стопу/колоколу, пишет pnl_r
    except Exception as _e:
        print(f'[TESTER·SETTLE] пропуск ({_e})')


# ── TESTER_TRADE_FEED_V1: лента сделок (открытие/закрытие в кабинет) ──
# ═══════════════════════════════════════════════════════════
# VEDENIE_POZICII_V1 — ДОЛИВ: БУДИМ ТРЕЙДЕРА НА ФРАКТАЛЕ
# ═══════════════════════════════════════════════════════════
# Канон (гл.8): «каждый новый пробитый фрактал по тренду наращивает
# позицию, пока цена держит сторону Зубов».
#
# Стоп тянет КОД (закон). А долив — РИСК, и тут решает ХАРАКТЕР:
# Илья дольёт агрессивно, Василий откажется. Решение Шефа: гибрид.
#
# ⚠ БУДИМ ОДНОГО ТРЕЙДЕРА, НЕ ВЕСЬ СОВЕТ. И ТОЛЬКО НА ФРАКТАЛЕ —
# не на каждом баре. Иначе разорение: позиция живёт сотни баров.
# Фракталы по тренду редки — цена копеечная.
# ═══════════════════════════════════════════════════════════

_VEDENIE_SLOT = {100001: ("торговый_хаос", "A06", "run_brut"),
                 100002: ("торговый_хаос", "A07", "run_avan"),
                 100003: ("торговый_хаос", "A08", "run_cons")}



# MOST_VEDENIYA_V1: применяем решение хозяина к РЕАЛЬНОЙ позиции ──────
_VEDENIE_PREFIX = {"A06": "brut", "A07": "avan", "A08": "cons"}


def _primenit_vedenie(sid, r, pos_magic, md, out=print):
    """Читает signal разбуженного хозяина и применяет action к позиции
    с magic=pos_magic. MOVE_STOP только в защиту; ADD растит лот +
    тянет стоп в сейф. Возвращает True, если что-то реально изменил."""
    from hooks import load_trading_state, save_trading_state

    sig = (r or {}).get("signal", {}) or {}
    pref = _VEDENIE_PREFIX.get(sid)
    if not pref:
        return False

    action = (sig.get(f"{pref}_action") or "").upper().strip()
    new_stop = sig.get(f"{pref}_new_stop")
    add_lot = sig.get(f"{pref}_add_lot")

    if action not in ("ADD", "MOVE_STOP"):
        # CLOSE_TREYDERA_V1: CLOSE — воля трейдера. Ставим manual_close,
        # settle закроет ВЕСЬ ПАКЕТ по close (причина MANUAL_CLOSE)
        # на следующем баре — раньше стопа и колокола.
        if action == "CLOSE":
            from hooks import load_trading_state, save_trading_state
            _ts = load_trading_state()
            _hit = False
            for _p in _ts.get("positions", []) or []:
                if _p.get("magic") == pos_magic and _p.get("status") == "OPEN":
                    _p["manual_close"] = True
                    _hit = True
            if _hit:
                save_trading_state(_ts)
                out(f"     └─ 🚪 CLOSE: {sid} закрывает пакет своей волей "
                    f"(settle исполнит на след. баре)")
                return True
            out("     └─ 🚪 CLOSE: открытой позиции нет — нечего закрывать")
        return False

    teeth = ((md.get("alligator", {}) or {}).get("teeth"))
    close = ((md.get("price", {}) or {}).get("close"))

    ts = load_trading_state()
    changed = False
    for p in ts.get("positions", []) or []:
        if p.get("magic") != pos_magic or p.get("status") != "OPEN":
            continue
        d = (p.get("direction") or "").upper()
        old_stop = p.get("stop")

        if action == "MOVE_STOP" and new_stop is not None:
            ns = float(new_stop)
            # только в защиту: LONG стоп вверх, SHORT вниз
            ok = ((d == "LONG" and old_stop is not None and ns > old_stop)
                  or (d == "SHORT" and old_stop is not None and ns < old_stop))
            # и не за цену
            if ok and close is not None:
                if d == "LONG" and ns >= close:
                    ok = False
                if d == "SHORT" and ns <= close:
                    ok = False
            if ok:
                p["stop"] = round(ns, 6)
                changed = True
                out(f"     └─ ✋ MOVE_STOP применён: стоп {old_stop} → {p['stop']}")
            else:
                out(f"     └─ ✋ MOVE_STOP отклонён (не в защиту / за цену): {ns}")

        elif action == "ADD" and add_lot is not None:
            try:
                al = float(add_lot)
            except (TypeError, ValueError):
                al = 0.0
            # REVERSE_PYRAMID_DISCIPLINE_V1: реверсивная пирамида СУЖАЕТСЯ кверху.
            # Долив > предыдущей ноги → полный ОТКАЗ + feedback в стол.
            _last_leg = float(p.get("last_leg") or p.get("lot_base")
                              or p.get("lot") or 0.0)
            if al > 0 and _last_leg > 0 and al > _last_leg * 1.0001:
                _pref = _VEDENIE_PREFIX.get(sid)
                if _pref:
                    ts.setdefault(_pref, {})
                    ts[_pref]["vedenie_feedback"] = (
                        f"Долив отклонён: превышен размер предыдущей ноги "
                        f"({al} > {_last_leg}). Реверсивная пирамида только "
                        f"сужается кверху.")
                    changed = True
                out(f"     └─ ⛔ ADD ОТКЛОНЁН: {al} > предыдущей ноги "
                    f"{_last_leg} — дисциплина пирамиды (полный отказ)")
            elif al > 0:
                # PAKET_PYRAMIDA_V1: средневзвешенная цена ПАКЕТА.
                # entry_new = close бара долива (текущая цена входа ноги).
                _lot_old = float(p.get("lot") or 0.0)
                _ea_old = float(p.get("entry_avg", p.get("entry") or 0.0))
                _entry_new = float(close) if close is not None else _ea_old
                _lot_new = _lot_old + al
                if _lot_new > 0:
                    p["entry_avg"] = round(
                        (_ea_old * _lot_old + _entry_new * al) / _lot_new, 6)
                p["lot"] = round(_lot_new, 4)
                # весь пакет за Зубами (§7): тянем стоп в сейф, если Зубы
                # уже прошли вход и стоп ещё не там
                if teeth is not None and old_stop is not None:
                    if d == "LONG" and teeth > old_stop and (close is None or teeth < close):
                        p["stop"] = round(teeth, 6)
                    elif d == "SHORT" and teeth < old_stop and (close is None or teeth > close):
                        p["stop"] = round(teeth, 6)
                p["last_leg"] = round(al, 4)  # REVERSE_PYRAMID_DISCIPLINE_V1: потолок для след. долива
                p["dolivok"] = int(p.get("dolivok", 0)) + 1
                changed = True
                out(f"     └─ 🔺 ADD применён: лот +{al} → {p['lot']}"
                    f" (доливок: {p['dolivok']}), стоп {p.get('stop')}")
            else:
                out("     └─ 🔺 ADD без объёма — гашу (лот не трогаю)")

    if changed:
        save_trading_state(ts)
    return changed


def _vesti_poziciyu(window, symbol, timeframe, point, out=print):
    """Долив по канону: новый фрактал по тренду → будим ХОЗЯИНА позиции
    (одного!) → он решает ADD / MOVE_STOP / HOLD своим характером.

    Возвращает True, если кого-то будили (для счёта вызовов)."""
    from williams_core import build_market_data
    from hooks import load_trading_state

    positions = [p for p in (load_trading_state().get('positions', []) or [])
                 if p.get('status') == 'OPEN']
    if not positions:
        return False

    md = build_market_data(window, symbol=symbol,
                           timeframe=timeframe, point=point)
    if not md:
        return False

    fr = md.get('fractals', {}) or {}
    allig = md.get('alligator', {}) or {}
    teeth = allig.get('teeth')
    close = (md.get('price', {}) or {}).get('close')
    if teeth is None or close is None:
        return False

    budili = False
    for pos in positions:
        d = (pos.get('direction') or '').upper()

        # ── ТРИГГЕР: свежий фрактал ПО ТРЕНДУ, цена держит сторону Зубов ──
        # Ключи ПРОВЕРЕНЫ НА ДИСКЕ (14.07): build_market_data отдаёт
        #   fractals: {'last_up': {'price':..., 'bar_index':..., 'date':...},
        #              'last_down': {...}, 'count_up':.., 'count_down':..}
        # Первый заход я написал fr.get('up')/fr.get('bull') — ПО ДОГАДКЕ.
        # Долив не сработал бы НИ РАЗУ. Смотреть в код, потом писать.
        if d == 'LONG':
            if close < teeth:          # пирамида мертва (гл.7)
                continue
            f = fr.get('last_up') or {}
            f_price = f.get('price') if isinstance(f, dict) else None
            if not f_price or close <= f_price:   # фрактал ещё не пробит
                continue
        elif d == 'SHORT':
            if close > teeth:
                continue
            f = fr.get('last_down') or {}
            f_price = f.get('price') if isinstance(f, dict) else None
            if not f_price or close >= f_price:
                continue
        else:
            continue

        # тот же фрактал дважды не доливаем
        if pos.get('last_fractal') == f_price:
            continue

        slot = _VEDENIE_SLOT.get(pos.get('magic'))
        if not slot:
            continue
        ceh, sid, fn = slot

        out(f"  🔺 ДОЛИВ? {pos.get('trader')} {d}: фрактал {f_price} пробит, "
            f"цена {close} держит Зубы {round(teeth, 2)} — бужу хозяина")

        try:
            brain = _slot_brain(ceh, sid)
            r = getattr(brain, fn)(symbol=symbol, timeframe=timeframe)
            if not (r or {}).get('ok'):
                continue
            budili = True
            # MOST_VEDENIYA_V1: решение хозяина → РЕАЛЬНАЯ позиция
            try:
                _primenit_vedenie(sid, r, pos.get('magic'), md, out)
            except Exception as _pe:
                out(f'     ⚠️  применение ведения не вышло: {_pe}')

            # пометим фрактал — второй раз по нему не будим
            _ts = load_trading_state()
            for _p in _ts.get('positions', []) or []:
                if _p.get('magic') == pos.get('magic'):
                    _p['last_fractal'] = f_price
            from hooks import save_trading_state
            save_trading_state(_ts)

            nar = (r.get('narrative') or '').strip()
            if nar:
                out(f"     └─ {nar[:200]}")
        except Exception as _e:
            out(f"     ⚠️  ведение не вышло: {_e}")

    return budili


def _table_snapshot():
    """Множество magic открытых позиций сейчас — для сравнения
    до/после (что открылось, что закрылось)."""
    try:
        from hooks import load_trading_state
        return {p.get('magic'): dict(p)
                for p in load_trading_state().get('positions', []) or []
                if p.get('status') == 'OPEN'}
    except Exception:
        return {}


def _read_last_closures(n=10):
    """Последние n закрытых сделок из trading_pnl.jsonl —
    settle уже записал туда pnl_r, closed_at, reason."""
    from pathlib import Path as _P
    import json as _j
    from hooks import PNL_PATH   # TESTER_PNL_PATH_FROM_HOOKS_V1: читаем ТОТ ЖЕ файл, что пишет settle
    p = _P(PNL_PATH)
    if not p.exists():
        return []
    try:
        lines = p.read_text(encoding='utf-8').strip().splitlines()
        out = []
        for ln in lines[-n:]:
            try:
                out.append(_j.loads(ln))
            except Exception:
                pass
        return out
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════
# OTCHET_V_TESTERE_V1 — ЧТО ОНИ НАТОРГОВАЛИ
# ═══════════════════════════════════════════════════════════
# Слово Шефа: «мне отчёт должен в конце показываться, а не скриптами
# ловить». Данные были всегда (trading_pnl.jsonl) — отчёта не было.
# Отчёт не только СЧИТАЕТ, но и СУДИТ по книге Котина (гл.9):
# без пирамиды и трейлинга система математически не может быть
# прибыльной — минус всегда полный, плюс всегда обрезан.
# ═══════════════════════════════════════════════════════════

def _otchet_po_sdelkam(sdelki_do: int, out, _emit):
    """Отчёт по сделкам ЭТОГО прогона. Читает trading_pnl.jsonl,
    берёт всё, что дописалось после начала (sdelki_do — сколько было
    ДО старта). Печатает в консоль, в файл разговора и в кабинет."""
    import json as _json
    from collections import defaultdict as _dd
    from pathlib import Path as _P

    _pnl = (_P(__file__).resolve().parent.parent / "GRONDHEIM_CITY" /
            "Биржа" / "данные" / "trading_pnl.jsonl")
    if not _pnl.exists():
        return

    _vse = []
    for _ln in _pnl.read_text(encoding="utf-8").splitlines():
        _ln = _ln.strip()
        if not _ln:
            continue
        try:
            _r = _json.loads(_ln)
            if _r.get("pnl_r") is not None:
                _vse.append(_r)
        except Exception:
            continue

    _s = _vse[sdelki_do:]          # только сделки ЭТОГО прогона
    if not _s:
        out("")
        out("─" * 64)
        out("  ОТЧЁТ: сделок не было. Совет ни разу не дал ENTER.")
        out("─" * 64)
        return

    _plus  = [x for x in _s if x["pnl_r"] > 0]
    _minus = [x for x in _s if x["pnl_r"] <= 0]
    _sp = sum(x["pnl_r"] for x in _plus)
    _sm = abs(sum(x["pnl_r"] for x in _minus))
    _sum = sum(x["pnl_r"] for x in _s)
    _pf = (_sp / _sm) if _sm > 0 else (float("inf") if _sp else 0.0)
    _pfs = "∞" if _pf == float("inf") else f"{_pf:.3f}"
    _wr = len(_plus) / len(_s) * 100

    out("")
    out("═" * 64)
    out("  💰 ОТЧЁТ ПО СДЕЛКАМ")
    out("═" * 64)
    out("")
    out(f"  {'#':>2} {'трейдер':11s} {'напр':5s} {'вход':>9s} "
        f"{'выход':>9s} {'R':>7s}  причина")
    out("  " + "─" * 60)
    for _i, _x in enumerate(_s, 1):
        _r = _x["pnl_r"]
        _z = "🟢" if _r > 0 else "🔴"
        _n = "LONG" if (_x.get("stop") or 0) < (_x.get("entry") or 0) else "SHORT"
        out(f"  {_i:>2} {str(_x.get('trader',''))[:11]:11s} {_n:5s} "
            f"{_x.get('entry','—'):>9} {_x.get('exit','—'):>9} "
            f"{_r:>+7.2f} {_z} {_x.get('close_reason','')}")

    out("")
    out(f"  сделок: {len(_s)}   плюсов: {len(_plus)}   минусов: {len(_minus)}"
        f"   winrate: {_wr:.0f}%")
    out(f"  ИТОГО:  {_sum:+.2f}R      средняя: {_sum/len(_s):+.2f}R/сделку")
    out(f"  PF:     {_pfs}  ({'ПРИБЫЛЬНАЯ' if _pf > 1 else 'УБЫТОЧНАЯ'})")

    # ── по трейдерам ──
    _pt = _dd(list)
    for _x in _s:
        _pt[_x.get("trader", "?")].append(_x["pnl_r"])
    out("")
    out("  ── по трейдерам ──")
    for _t, _rs in sorted(_pt.items()):
        _p2 = [r for r in _rs if r > 0]
        _m2 = abs(sum(r for r in _rs if r <= 0))
        _pf2 = (sum(_p2) / _m2) if _m2 > 0 else (float("inf") if _p2 else 0.0)
        _pf2s = "∞" if _pf2 == float("inf") else f"{_pf2:.2f}"
        out(f"     {str(_t)[:12]:12s} {len(_rs):>2} сдел · "
            f"плюс {len(_p2):>2} · {sum(_rs):>+7.2f}R · PF {_pf2s}")

    # ── как закрывались ──
    _pr = _dd(list)
    for _x in _s:
        _pr[_x.get("close_reason", "?")].append(_x["pnl_r"])
    out("")
    out("  ── как закрывались ──")
    for _rn, _rs in sorted(_pr.items(), key=lambda z: -len(z[1])):
        out(f"     {str(_rn)[:14]:14s} {len(_rs):>2} шт · "
            f"{sum(_rs):>+7.2f}R · средняя {sum(_rs)/len(_rs):+.2f}R")

    # ══════════════════════════════════════════════════════
    # ДИАГНОЗ — по книге Котина, гл.9
    # ══════════════════════════════════════════════════════
    _polny = [x for x in _s if abs(x["pnl_r"] + 1.0) < 0.05]
    _dolya = len(_polny) / len(_s) * 100
    _krup  = [x for x in _s if x["pnl_r"] >= 2.0]

    out("")
    out("  ── ДИАГНОЗ (книга Котина, гл.9) ──")
    out("")
    out(f"     закрытий ровно по −1.0R (стоп не подтянут): "
        f"{len(_polny)}/{len(_s)} ({_dolya:.0f}%)")
    out(f"     сделок ≥ +2.0R (то, что даёт пирамида):     {len(_krup)}")

    # DIAGNOZ_PRAVDA_V1: ведение ПОСТРОЕНО (трейлинг/сейф/мост/пирамида).
    # Диагноз теперь СЧИТАЕТ факт пирамиды, а не приговаривает.
    _s_piram = [x for x in _s if int(x.get("dolivok", 0) or 0) > 0]
    _s_win = [x for x in _s if x["pnl_r"] > 0]
    def _mult(x):
        _lb = x.get("lot_base") or x.get("lot") or 1.0
        try:
            return float(x.get("lot") or _lb) / float(_lb) if _lb else 1.0
        except (TypeError, ZeroDivisionError):
            return 1.0
    _avg_mult = (sum(_mult(x) for x in _s_win) / len(_s_win)) if _s_win else 1.0
    out(f"     сделок с доливом (пирамида сработала):     {len(_s_piram)}")
    out(f"     средний множитель объёма у плюсовых:       {_avg_mult:.2f}x")

    if not _krup and len(_s) >= 4:
        out("")
        if len(_s_piram) == 0:
            out("     ⓘ Доливы НЕ случились ни разу за прогон.")
            out("       Ведение построено (трейлинг/сейф/мост/пакет),")
            out("       но пирамиде НЕ БЫЛО ПОВОДА. Честные причины:")
            out("         • рынок не дал фрактал ПО ТРЕНДУ при живой позиции;")
            out("         • цена ушла в минус сразу — доливать нечего;")
            out("         • хозяин осознанно держал HOLD (осторожность).")
            out("       Это НЕ поломка — это выборка. Нужен объём прогона.")
        else:
            out("     ⓘ Доливы были, но ни один пакет не дал +2R.")
            out("       Смотреть: рано ли обрывался exit_bell, держит ли")
            out("       тренд после долива. Пирамида живая, край ищем.")

    out("═" * 64)

    # ── в кабинет ──
    try:
        _emit({"type": "trades_report",
               "trades": len(_s), "wins": len(_plus), "winrate": round(_wr, 1),
               "sum_r": round(_sum, 2), "pf": (None if _pf == float("inf")
                                               else round(_pf, 3)),
               "full_stops": len(_polny), "big_wins": len(_krup)})
    except Exception:
        pass


def run_tester(csv_path: str, symbol: str, timeframe: str,
               n_signals: int = 1, point_override=None,
               warmup: int = 60, loose: bool = False,
               on_progress=None, should_stop=None,  # TESTER_HANDLES_V1
               learn: bool = False):  # TESTER_STERILE_V1: умолчание — смотреть
    from williams_core import read_mt5_csv, build_market_data
    import mt5_feed

    # РУЛЬ (биржа слушает ход / прерывает перебор).  # TESTER_HANDLES_V1
    def _emit(msg):
        if on_progress:
            try:
                on_progress(msg)
            except Exception:
                pass
    def _stop_requested():
        if should_stop:
            try:
                return bool(should_stop())
            except Exception:
                return False
        return False

    def _emit_report(agent, narrative, status="", result=None):  # TESTER_REPORTS_V1
        """
        Структурный отчёт агента наружу — биржа разложит по аватарам.

        result (опционально) — ПОЛНЫЙ словарь run_* агента (signal,
        market, stats, ...). Раньше сюда шёл только narrative/status —
        кабинет не мог восстановить *_last_run после ТЕСТЕРА, и чат
        с агентом сразу после тестового прогона честно, но неверно по
        сути отвечал "рынок не запускали". Теперь result прокидывается
        и в кабинете идёт в ту же _apply_agent_result, что использует
        и РЫНОК — один источник правды для памяти чата.
        """
        if on_progress and narrative:
            try:
                msg = {"type": "report", "agent": agent,
                       "narrative": str(narrative).strip(), "status": status}
                if result is not None:
                    msg["result"] = result
                on_progress(msg)
            except Exception:
                pass

    point = _resolve_point(symbol, point_override)

    full_path = csv_path if Path(csv_path).is_absolute() else str(_HERE / csv_path)
    if not Path(full_path).exists():
        # пробуем ещё от корня запуска
        if Path(csv_path).exists():
            full_path = csv_path
        else:
            print(f"❌ CSV не найден: {csv_path}")
            sys.exit(1)

    bars_all = read_mt5_csv(full_path)
    if not bars_all:
        print(f"❌ CSV пуст или не прочитан: {full_path}")
        sys.exit(1)

    # ── МНОГОЭТАЖНАЯ ЛЕСЕНКА (LADDER_MULTIFLOOR_V1) ──────────
    # Раньше тестер был заперт на одном этаже (тот, что явно передан
    # в --csv): step_down всегда None, спуск не мог опуститься глубже
    # загруженного файла, даже если по канону должен был. Шеф выгрузил
    # test_data/ с ПОЛНЫМ комплектом (M5..MN1) — грузим все, что
    # нашлись, чтобы лесенка спускалась по НАСТОЯЩИМ историческим
    # барам, не упираясь в потолок одного файла.
    #
    # Поиск файла под каждый этаж переиспользует feed_source._find_csv
    # (то же самое угадывание имени — словом для старших ТФ, кодом для
    # младших) — не плодим вторую логику поиска файлов в репо.
    import bisect
    try:
        from feed_source import _find_csv as _ffs_find_csv
    except ImportError:
        _ffs_find_csv = None
    try:
        from mt5_feed import _TF_LADDER as _MT5_LADDER
    except ImportError:
        _MT5_LADDER = None
    _TF_LADDER = _MT5_LADDER or ["MN1", "W1", "D1", "H12", "H8", "H4",
                                  "H1", "M30", "M15", "M10", "M5"]

    _floors: dict = {timeframe.upper(): bars_all}   # главный этаж уже на руках
    if _ffs_find_csv is not None:
        for _tf in _TF_LADDER:
            if _tf in _floors:
                continue
            _p = _ffs_find_csv(symbol, _tf)
            if _p is None:
                continue
            _b = read_mt5_csv(str(_p))
            if _b:
                _floors[_tf] = _b
    print(f"[TESTER] 🪜 этажи лесенки в наличии: {sorted(_floors.keys())}")

    # PERF_LADDER_DATES_CACHE_V1: список дат КАЖДОГО этажа считаем
    # ОДИН РАЗ здесь, не на каждый вызов _bars_as_of. Раньше пересборка
    # (list comprehension по 100 000 строк для M5/M15/M30/M10) шла на
    # КАЖДЫЙ вызов — а вызовов тысячи (каждый кандидат сита × каждый
    # шаг спуска по лестнице). Итог — тестер практически завис.
    # bisect не может работать напрямую по списку словарей, поэтому
    # держим отдельный параллельный список дат-строк на этаж.
    _floor_dates: dict = {tf: [b["date"] for b in bs] for tf, bs in _floors.items()}

    def _bars_as_of(tf_name: str, cutoff_date: str, count: int):
        """
        Честный срез этажа tf_name НЕ ПОЗЖЕ cutoff_date — без забегания
        вперёд. Даты MT5 (YYYY.MM.DD[ HH:MM]) сравниваются как строки:
        формат фикс-ширины, лексикографический порядок = хронологический.
        Текущий ФОРМИРУЮЩИЙСЯ бар старшего этажа (дата без времени,
        совпадает с сегодняшней датой cutoff) КОРРЕКТНО включается —
        так же ведёт себя живой терминал (текущая свеча видна, пока
        не закрылась). Этаж не покрывает эту дату (M5/M15 короче
        историей) → честно пусто — лесенка/step_down поймут это как
        честную вакансию этажа, не как ошибку.

        Даты берём из ГОТОВОГО кэша (_floor_dates), не пересобираем.
        """
        key = (tf_name or timeframe).upper()
        floor = _floors.get(key)
        if not floor:
            return [], None
        dates = _floor_dates[key]
        idx = bisect.bisect_right(dates, cutoff_date)
        if idx == 0:
            return [], None
        start = max(0, idx - count) if count else 0
        return floor[start:idx], point

    total = len(bars_all)
    # TESTER_CLEAN_TABLE_V1: чистим стол прогоняемого символа ПЕРЕД заходом
    _clean_table_for_symbol(symbol)
    print("═" * 64)
    print(f"  ЭКСПРЕСС-ТЕСТЕР · {symbol} {timeframe} · {total} баров")
    print(f"  point={point} · ловлю срабатываний Искры: {n_signals}")
    print(f"  кухня сама ищет — я только микрофон")
    print("═" * 64)

    # OTCHET_V_TESTERE_V1: сколько сделок было ДО прогона — чтобы
    # отчёт показал только ЭТОТ прогон, а не всю историю журнала.
    try:
        import json as _jj
        _pnl_p = (Path(__file__).resolve().parent.parent / "GRONDHEIM_CITY" /
                  "Биржа" / "данные" / "trading_pnl.jsonl")
        _sdelok_do = 0
        if _pnl_p.exists():
            for _l in _pnl_p.read_text(encoding="utf-8").splitlines():
                if _l.strip():
                    try:
                        if _jj.loads(_l).get("pnl_r") is not None:
                            _sdelok_do += 1
                    except Exception:
                        pass
    except Exception:
        _sdelok_do = 0

    # HRONIKI_PAPKA_V1: отчёты уходят в ОТДЕЛЬНУЮ папку хроники,
    # не в test_data к котировкам. Медийщики берут летопись отсюда.
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _hroniki_dir = _HERE / "хроники"
    _hroniki_dir.mkdir(parents=True, exist_ok=True)
    report_path = _hroniki_dir / f"{Path(full_path).stem}_tester_{stamp}.txt"
    report = open(report_path, "w", encoding="utf-8")

    def out(line=""):
        print(line)
        report.write(line + "\n")

    # TESTER_TRADE_FEED_V1: лента сделок в кабинет+консоль+файл
    _pnl_seen = {"n": len(_read_last_closures(9999))}
    def _feed_opened(pos):
        _d = pos.get('direction', '?')
        _t = pos.get('trader', '?')
        _e = pos.get('entry')
        line = f"🟢 ОТКРЫТА: {_t} {_d} @ {_e}"
        out("  " + line)
        _emit({"type": "trade", "kind": "open", "text": line})
    def _feed_check_closures(cur_bar_i):
        # читаем новые закрытия с прошлой проверки и шлём ленту
        all_cl = _read_last_closures(9999)
        new = all_cl[_pnl_seen['n']:]
        _pnl_seen['n'] = len(all_cl)
        for rec in new:
            _t = rec.get('trader', '?')
            _r = rec.get('pnl_r')
            _reason = rec.get('close_reason', '?')
            _opened = rec.get('opened_at', '?')
            _closed = rec.get('closed_at', '?')
            _rstr = (f"{'+' if (_r or 0) >= 0 else ''}{_r}R"
                     if _r is not None else '—')
            line = (f"🔴 ЗАКРЫТА: {_t} {_rstr} ({_reason}) · "
                    f"{_opened} → {_closed}")
            out("  " + line)
            _emit({"type": "trade", "kind": "close", "text": line})

    # ── КРАН: подменяем _fetch на честный срез нужного ЭТАЖА ──
    # LADDER_MULTIFLOOR_V1: раньше отдавали срез ЕДИНСТВЕННОГО
    # загруженного файла, игнорируя tf_name целиком (один CSV = один
    # этаж). Теперь смотрим, какой этаж просят, и берём его из
    # _floors (если он в наличии) — срез честный, по дате текущего
    # "сейчас" (см. _bars_as_of выше), без забегания вперёд.
    state = {"cursor": warmup}

    def _fake_fetch(mt5, sym, tf_name, count):
        cutoff = bars_all[state["cursor"]]["date"]
        return _bars_as_of(tf_name or timeframe, cutoff, count)

    # _terminal вернёт не-None заглушку, чтобы агенты прошли проверку
    # "if mt5 is None" и дошли до _fetch (который мы подменили).
    class _FakeMT5:  # достаточно, чтобы быть "не None"
        pass

    # ── TESTER_STERILE_V1: стерильность — бэктест не калечит ДНК ──
    # learn=False (умолчание): глушим петлю обучения на время
    # прогона. Агенты думают, сделки считаются, но sync_to_dna
    # не мутирует живую ДНК. learn=True — учебный прогон.
    try:
        import studio.grondheim_memory as _gm  # type: ignore[import]  # TESTER_EXPRESS_SOUL_IGNORE_V1: намеренно — см. except ниже
    except ImportError:
        # Новый город: studio.grondheim_memory (душа агентов) ещё не
        # перенесена для торговых агентов — честная заглушка вместо
        # падения. sync_to_dna и так вызывается через try/except в
        # каждом *_live.py, так что учебная петля просто молчит.
        class _NoSoulShim:
            def sync_to_dna(self, *a, **k):
                pass
        _gm = _NoSoulShim()
        print('[TESTER] ℹ️  studio.grondheim_memory не найдена (новый город) — '
              'петля обучения ДНК молчит, прогон честно идёт без неё')
    _orig_sync = _gm.sync_to_dna
    if not learn:
        _gm.sync_to_dna = lambda *a, **k: None   # заглушка-микрофон
        print('[TESTER] 🧪 стерильный прогон: ДНК агентов НЕ мутирует '
              '(--learn чтобы учить)')
    else:
        print('[TESTER] 🎓 учебный прогон: ДНК агентов мутирует, как в реале')

    # ── TESTER_STERILE_OPYT_V1: НОГА ОПЫТА подчиняется тому же рубильнику ──
    # hooks._judge_trader_by_result пишет вывод из сделки в ЖИВОЙ паспорт
    # жителя (Anchor_Points + заряд) через nositel.zapisat_vyvod. Это мимо
    # заглушки sync_to_dna выше — значит стерильный прогон молча калечил бы
    # Илью: его пять рождённых якорей вытеснялись бы тестовыми выводами.
    # Глушим тем же рубильником. ЧИТАЮЩИЙ конец (душа в промпте) не трогаем —
    # чтение безвредно, трейдер и в стерильном прогоне сидит за столом собой.
    try:
        import nositel as _nos
    except Exception as _e:
        _nos = None
        print(f'[TESTER] ℹ️  мост к носителю не поднялся ({_e})')
    _orig_vyvod = _nos.zapisat_vyvod if _nos is not None else None
    if _nos is not None:
        # SUD_SENSOROV_V2: ОДИН рубильник на всю запись в живых жителей — трейдеры И
        # сенсоры. Раньше глушился только zapisat_vyvod, и сенсоры писали бы
        # МИМО стерильности, калеча Веру с Моржом на обычном бэктесте.
        _nos.UCHIT = bool(learn)
    if _nos is not None and not learn:
        _nos.zapisat_vyvod = (lambda *a, **k:
                              {'дописано': False, 'причина': 'стерильный прогон'})
        print('[TESTER] 🧪 стерильно: нога Опыта молчит — '
              'паспорта жителей НЕ трогаем (--learn чтобы учить)')
    elif _nos is not None:
        print('[TESTER] 🎓 учебно: нога Опыта пишет — '
              'якоря жителей будут расти, заряд качаться')

    orig_fetch = mt5_feed._fetch
    orig_term  = mt5_feed._terminal
    orig_pull  = mt5_feed.pull_bars     # TESTER_TO_CABINET_V1
    orig_step  = mt5_feed.step_down     # TESTER_TO_CABINET_V1
    mt5_feed._fetch    = _fake_fetch
    mt5_feed._terminal = lambda: _FakeMT5()

    # ── ГЕРМЕТИЧНЫЙ КРАН (TESTER_TO_CABINET_V1) ──────────────
    # Спуск Искры (_read_form_on) берёт бары через pull_bars, не
    # через _fetch. Накрываем и её: тот же честный срез по дате.
    #
    # LADDER_MULTIFLOOR_V1: step_down теперь НЕ заперт наглухо —
    # спускается по настоящей лесенке (_TF_LADDER), но ЧЕСТНО: этаж
    # существует для спуска ТОЛЬКО если на него нашёлся файл И этот
    # файл покрывает текущую историческую дату (M5/M15 короче
    # историей — до 2025/2022 их считай нет, спуск остановится
    # на последнем этаже, что реально существовал в тот момент).
    def _fake_pull(sym, tf_name, count=2000):
        return _fake_fetch(None, sym, tf_name, count)

    def _multi_step_down(tf_name):
        tf = (tf_name or "").upper()
        if tf not in _TF_LADDER:
            return None
        i = _TF_LADDER.index(tf)
        if i + 1 >= len(_TF_LADDER):
            return None
        next_tf = _TF_LADDER[i + 1]
        cutoff = bars_all[state["cursor"]]["date"]
        probe, _ = _bars_as_of(next_tf, cutoff, 1)
        if not probe:
            return None   # этажа нет ИЛИ он не покрывает эту дату — честно
        return next_tf

    mt5_feed.pull_bars = _fake_pull
    mt5_feed.step_down = _multi_step_down

    caught = 0
    scanned = 0
    found_cnt = 0          # TESTER_TO_CABINET_V1: у скольких спуск нашёл точку
    _last_settled = warmup - 1   # TESTER_SETTLE_GAPS_V1: докуда докатан settle
    try:
        # Проверка, что мозг Искры на месте (Совет её зовёт внутри
        # council.wake_council — единая дверь). Сито-1 ниже Искру-LLM
        # не трогает: оно чистое ядро (build_market_data), без модели.
        if _slot_brain("торговый_хаос", "A01") is None:
            raise RuntimeError("мозг A01 (Искра) ещё не в слоте")

        # ════════════════════════════════════════════════════
        # SITO_SLIYANIE_V1 — ЕДИНЫЙ СКВОЗНОЙ ПРОХОД
        # ─────────────────────────────────────────────────────
        # §5р.6 диагноз: Сито-1 (весь проход целиком) → Сито-2 (второй
        # проход по готовому списку) калечили память точки — точка c
        # не может помнить себя «из будущего» второго прохода. Теперь
        # ОДИН хронологический проход, бар за баром, как живой рынок:
        #   1. ведение (settle/долив) — как раньше, каждый бар
        #   2. дешёвая проверка ядром (без LLM): либо СВЕЖИЙ спуск на
        #      ЭТОМ баре (старый критерий Сита-1: bdb_strong/bdb_dir),
        #      либо точка ЖИВА (TOCHKA_ZHIVA_V1) И на этом баре пробит
        #      фрактал Ганса ИЛИ сработал Большой палец Авантюриста
        #      (TWR_BOLSHOY_PALEC_V1) — три триггера Совета один-в-один
        #      с COUNCIL_GATE_TROYNOY_V1 внутри council.wake_council.
        #   3. только если триггер сработал — зовём council.wake_council
        #      (единая дверь, ENGINE_ONE_DOOR_V1), передаём ей уже
        #      посчитанное окно/point, чтобы не тянуть дважды.
        # ════════════════════════════════════════════════════
        from hooks import proverit_tochku, _hans_breakout, proverit_nogu

        out("🔀 Единый сквозной проход (SITO_SLIYANIE_V1): "
            "бар за баром, память точки живёт между барами...")
        out("")

        for i in range(warmup, total):
            if _stop_requested():   # TESTER_HANDLES_V1: кнопка СТОП биржи
                out(f"⏸ СТОП по команде Шефа — прошёл бар {i} из {total}.")
                break

            # CURSOR_FIX_V1: "честный кран" (_fake_fetch/_fake_pull/
            # _multi_step_down) режет историю ПО ЭТОЙ переменной, не по
            # аргументам вызова. Без неё Искра внутри себя (её собственный
            # pull_bars при спуске по лесенке) видела бы всегда один и тот
            # же (самый первый) момент истории — потерялась при слиянии
            # Сита-1/Сита-2, возвращаю на каждом баре.
            state["cursor"] = i

            # ── ведение: на КАЖДОМ баре, не только между кандидатами ──
            # TESTER_SETTLE_FULL_WINDOW_V1: полное окно 300 баров.
            _settle_bar(bars_all[max(0, i - 299):i + 1], symbol, timeframe, point)
            try:
                _vesti_poziciyu(bars_all[max(0, i - 299):i + 1],
                                symbol, timeframe, point, out)
            except Exception as _ve:
                print(f'[ВЕДЕНИЕ] ⚠️  {_ve}')
            _last_settled = i
            _feed_check_closures(i)   # TESTER_TRADE_FEED_V1: лента закрытий

            # ── дешёвая проверка ядром (без LLM, микросекунды) ──
            end = i + 1
            start = max(0, end - 120)   # ISKRA_WORKING_TF_FIRST_V1: канон
            window = bars_all[start:end]
            md = build_market_data(window, symbol=symbol,
                                   timeframe=timeframe, point=point)
            if not md:
                continue

            # NECRON_DIVERGENCE_V1: "divergent_bar"/bdb_strong снята
            # целиком — разворотный бар теперь только formula Necron,
            # одно условие без деления на "кандидат"/"подтверждённый".
            # loose/strict больше не различаются НА ЭТОМ гейте (флаг
            # --loose оставлен в интерфейсе — может пригодиться другим
            # ситам позже, здесь просто не на что ему опираться).
            wf = md.get("wave_form", {})
            strong = wf.get("bdb_dir")
            side = wf.get("bdb_dir") or "?"

            # SITO_SLIYANIE_V1: триггеры Б/В — точка жива И фрактал/палец
            # на ЭТОМ баре. Считаем ОДИН РАЗ здесь (md уже посчитан) —
            # wake_council сделает ту же проверку внутри себя как
            # подтверждение, но решение «звать ли вообще» — здесь,
            # дёшево, без лишнего похода в pull_bars.
            _cheap_trigger = None
            _tochka = proverit_tochku(md)
            if _tochka.get("changed"):   # TOCHKA_LOG_V1: видно, когда точка родилась/умерла/подпиталась
                _bd_log = bars_all[i].get("date", "?")
                print(f"[ТОЧКА] бар {i} ({_bd_log}): "
                      f"{'жива' if _tochka.get('alive') else 'МЕРТВА'} — "
                      f"{_tochka.get('reason','?')}")

            # ZIGZAG_CORE_V1: наблюдатель ног — параллельно, ничего не гейтит
            _noga_ev = proverit_nogu(md)
            if _noga_ev:
                print(f"[НОГА] бар {i} ({bars_all[i].get('date','?')}): "
                      f"{_noga_ev.get('event')} — {_noga_ev}")
            if _tochka.get("alive"):
                # TRIGGERS_SINHRON_V1: синхронность — пробой/палец должен
                # смотреть в ТУ ЖЕ сторону, что и живая точка.
                _napr_tochki = _tochka.get("direction")
                _hd = _hans_breakout(md, window)
                if _hd is not None and _HANS_TO_BULL_BEAR.get(_hd) == _napr_tochki:
                    _cheap_trigger = ("fractal", _hd)
                else:
                    _thumb = md.get("thumb_trade", {}) or {}
                    if (_thumb.get("triggered")
                            and _thumb.get("direction") == _napr_tochki):
                        _cheap_trigger = ("thumb", _thumb.get("direction"))

            if not strong and not _cheap_trigger:
                continue   # тихий бар — идём дальше, ведение уже сделано

            scanned += 1
            bd = bars_all[i].get("date", "?")
            if _cheap_trigger:
                side = _cheap_trigger[1] or side
                _povod = f"живая точка + {_cheap_trigger[0]}"
            else:
                _povod = "свежий спуск ядра"
            _emit(f"кандидат {scanned} · бар {i} ({_povod})")

            _table_before = set(_table_snapshot().keys())   # TESTER_TRADE_FEED_V1
            # ── ЕДИНАЯ ДВЕРЬ СОВЕТА (ENGINE_ONE_DOOR_V1) ──
            import council

            _found_flag = {"found": True}   # спуск/триггер подтверждён Советом?

            def _on_council_event(ev):
                etype = ev.get("type")
                if etype == "council_idle":
                    _found_flag["found"] = False
                    _d = ev.get("descent", {}) or {}
                    _msg = (f"кандидат {scanned} ({bd}, {side}): "
                            f"спуск не нашёл точку (компас={_d.get('compass')})")
                    print("  " + _msg + " — пропускаю")
                    _emit({"type": "progress", "text": _msg})
                    return
                if etype == "council_triggered_by_point":
                    _msg = (f"кандидат {scanned} ({bd}): Совет разбужен "
                            f"дешёвым триггером {ev.get('kind')} на живой точке")
                    print("  " + _msg)
                    _emit({"type": "progress", "text": _msg})
                    return
                if etype != "agent":
                    return
                aid = ev.get("id")
                r = ev.get("result", {}) or {}
                narrative = (ev.get("narrative", "") or "").strip()
                if not r.get("ok"):
                    # KRIK_ISKRY_V1: Искра была ЕДИНСТВЕННОЙ, чей сбой
                    # молча проглатывался (if aid != "A01"). Из-за этого её
                    # исключение не видели НИ РАЗУ: Совет расходился с
                    # «спуск не нашёл точку», хотя спуск как раз нашёл, а
                    # упало ПОЗЖЕ — при сборке ответа. Кричим за всех.
                    _icon = {"A01": "✴️", "A02": "🦭", "A03": "😱", "A04": "🎯",
                             "A05": "📚", "A06": "🪨", "A07": "⚡",
                             "A08": "🛡", "A09": "📋"}.get(aid, "•")
                    out(f"  {_icon} {aid}: СБОЙ — {r.get('error','?')}")
                    out("")
                    return

                if aid == "A01":
                    _t1 = (r.get("signal", {}) or {}).get("t1_status", "NOT_FOUND")
                    out("")
                    out("🎯 " + "─" * 60)
                    out(f"🎯 бар {i} ({bd}) — ИСКРА: {_t1}")
                    out("🎯 " + "─" * 60)
                    out("")
                    out(f"  ✴️ ИСКРА:\n     {narrative}")
                    _emit_report("A01", narrative, _t1, result=r)
                    out("")
                elif aid == "A02":
                    out(f"  🦭 МОРЖ:\n     {narrative}")
                    _emit_report("A02", narrative, result=r)
                    out("")
                elif aid == "A03":
                    out(f"  😱 ПАНИКЁР:\n     {narrative}")
                    _emit_report("A03", narrative, result=r)
                    out("")
                elif aid == "A04":
                    out(f"  🎯 ГАНС:\n     {narrative}")
                    _emit_report("A04", narrative, result=r)
                    out("")
                elif aid == "A05":
                    out(f"  📚 АРХИВАРИУС:\n     {narrative}")
                    _emit_report("A05", narrative, result=r)
                    out("")
                elif aid == "A06":
                    out(f"  🪨 БРУТ:\n     {narrative}")
                    _emit_report("A06", narrative, result=r)
                    bs = r.get("signal", {}) or {}
                    v = bs.get("brut_verdict", "—")
                    if v == "APPROVED":
                        out(f"     └─ ВЕРДИКТ: {v} {bs.get('brut_direction','')} "
                            f"вход {bs.get('brut_entry','—')} · "
                            f"стоп {bs.get('brut_stop','—')} · "
                            f"лот {bs.get('brut_lot','—')}")
                    else:
                        out(f"     └─ ВЕРДИКТ: {v} ({bs.get('brut_reason','')})")
                    de = r.get("diary_entry", {}) or {}
                    if de:
                        out(f"     └─ в дневник: {de.get('action','').strip()}")
                    out("")
                elif aid == "A07":
                    out(f"  ⚡ АВАНТЮРИСТ:\n     {narrative}")
                    _emit_report("A07", narrative, result=r)
                    avs = r.get("signal", {}) or {}
                    vv = avs.get("avan_verdict", "—")
                    if vv == "APPROVED":
                        out(f"     └─ ВЕРДИКТ: {vv} {avs.get('avan_direction','')} "
                            f"вход {avs.get('avan_entry','—')} · "
                            f"стоп {avs.get('avan_stop','—')} · "
                            f"лот {avs.get('avan_lot','—')}")
                    else:
                        out(f"     └─ ВЕРДИКТ: {vv} ({avs.get('avan_reason','')})")
                    out("")
                elif aid == "A08":
                    out(f"  🛡 КОНСЕРВАТОР:\n     {narrative}")
                    _emit_report("A08", narrative, result=r)
                    cos = r.get("signal", {}) or {}
                    vc = cos.get("cons_verdict", "—")
                    if vc == "APPROVED":
                        out(f"     └─ ВЕРДИКТ: {vc} {cos.get('cons_direction','')} "
                            f"вход {cos.get('cons_entry','—')} · "
                            f"стоп {cos.get('cons_stop','—')} · "
                            f"лот {cos.get('cons_lot','—')}")
                    else:
                        out(f"     └─ ВЕРДИКТ: {vc} ({cos.get('cons_reason','')})")
                    out("")
                elif aid == "A09":
                    esig = r.get("signal", {}) or {}
                    fdna = esig.get("final_dna", {}) or {}
                    out(f"  📋 ИСПОЛНИТЕЛЬ: ордеров "
                        f"{fdna.get('orders_sent','—')} из 3 · "
                        f"task_score {fdna.get('task_score','—')}")
                    _emit_report("A09",
                        esig.get("history_dna", "") or
                        f"ордеров {fdna.get('orders_sent','—')} из 3",
                        result=r)
                    if esig.get("history_dna"):
                        out(f"     └─ летопись: {esig.get('history_dna','').strip()}")
                    out("")

            _summary = council.wake_council(symbol, timeframe,
                                            on_event=_on_council_event,
                                            window=window, point=point)

            # Ни спуск, ни дешёвый триггер не подтвердились Советом
            # (Искра живьём судит строже ядра) → следующий бар.
            if not _found_flag["found"] or _summary.get("idle"):
                continue
            found_cnt += 1   # TESTER_TO_CABINET_V1: триггер долетел до Совета

            # TESTER_TRADE_FEED_V1: лента открытий — что появилось на столе
            # после того, как Исполнитель отработал внутри wake_council.
            try:
                _now = _table_snapshot()
                for _m, _p in _now.items():
                    if _m not in _table_before:
                        _feed_opened(_p)
            except Exception:
                pass
            # TESTER_CLEAN_TABLE_V1: метим свежие позиции символом (для Шага 2)
            try:
                from hooks import (
                    load_trading_state, save_trading_state)
                _ts = load_trading_state()
                _dirty = False
                for _p in _ts.get('positions', []) or []:
                    if not _p.get('symbol'):
                        _p['symbol'] = symbol
                        _dirty = True
                if _dirty:
                    save_trading_state(_ts)
            except Exception:
                pass

            caught += 1   # TESTER_TO_CABINET_V1: Совет собрался и отработал
            if caught >= n_signals:
                out(f"✓ поймал {caught} срабатываний из {scanned} "
                    f"проверенных кандидатов — стоп.")
                break
        else:
            if scanned == 0:
                hint = ("" if loose else
                        " Попробуй мягче: добавь флаг --loose "
                        "(ловит B/D/B без жёсткой ангуляции 5-7 баров).")
                out("\n⚠️ Ни ядро, ни память живой точки не дали ни одного "
                    f"триггера на всей истории.{hint} Модель почти не звали "
                    "— честный ответ кухни.")
            else:
                out(f"\n⚠️ прошёл всю историю ({total - warmup} баров), "
                    f"проверено кандидатов: {scanned}, живая Искра/Совет "
                    f"подтвердили {caught} (искал {n_signals}). Честный "
                    f"ответ кухни.")

        # TESTER_SETTLE_TAIL_V1 · Брат + Шеф · ХВОСТ СЕССИИ
        # Последняя из N пойманных сделок открывается на последнем
        # кандидате, а цикл рвётся по n_signals раньше, чем рынок дошёл
        # до её стопа/колокола. Досеттливаем: ведём открытые позиции
        # бар-за-баром от последнего кандидата вперёд, пока все не
        # закроются (или пока не кончится история). Физика и лента — те
        # же, что в основном цикле. _settle_bar дёшев на пустом столе.
        if _table_snapshot():
            out("")
            out("🔚 Досеттливаю хвост: веду открытые позиции до закрытия...")
            for _b in range(_last_settled + 1, total):
                _settle_bar(bars_all[max(0, _b - 299):_b + 1],
                            symbol, timeframe, point)
                _last_settled = _b
                _feed_check_closures(_b)
                if not _table_snapshot():
                    out(f"✓ хвост закрыт на баре {_b}.")
                    break
            else:
                out(f"⚠️ хвост докатан до конца истории (бар {total - 1}) — "
                    f"часть позиций не встретила стоп/колокол в этом окне.")

    finally:
        # ── снимаем весь кран: всё как было (TESTER_TO_CABINET_V1) ──
        _gm.sync_to_dna = _orig_sync   # TESTER_STERILE_V1: вернуть обучение
        if _nos is not None and _orig_vyvod is not None:
            _nos.zapisat_vyvod = _orig_vyvod   # TESTER_STERILE_OPYT_V1: вернуть ногу Опыта
        mt5_feed._fetch    = orig_fetch
        mt5_feed._terminal = orig_term
        mt5_feed.pull_bars = orig_pull
        mt5_feed.step_down = orig_step
        report.close()

    # OTCHET_V_TESTERE_V1: ОТЧЁТ — сам, в конце. Слово Шефа:
    # «мне отчёт должен в конце показываться, а не скриптами ловить».
    try:
        _otchet_po_sdelkam(_sdelok_do, print, _emit)
    except Exception as _e:
        print(f"⚠️  отчёт не собрался: {_e}")

    # ── РАЗВИЛКА (TESTER_TO_CABINET_V1) — в кабинет через on_progress + в консоль ──
    # SITO_SLIYANIE_V1: "candidates" списком больше не существует (слито
    # в один проход) — считаем через "scanned" (сколько раз триггер вообще
    # сработал за весь проход, спуском ИЛИ памятью точки).
    _verdict = (f"РАЗВИЛКА · триггеров за проход: {scanned} · "
                f"долетело до Совета: {found_cnt} · Совет собрался: {caught}")
    if found_cnt == 0:
        _hint = ("Совет молчит — ни спуск, ни память живой точки не долетели "
                 "до Совета. Триггеры есть, ворота исправны: редок "
                 "дивер-компас/фрактал/палец. Следующий шаг — "
                 "подключить global_bias (синюю) к спуску.")
    else:
        _hint = f"Триггер долетел до Совета {found_cnt} раз — ворота работают."
    _emit({"type": "verdict", "text": _verdict, "hint": _hint,
           "candidates": scanned, "found": found_cnt, "council": caught})
    print("")
    print("─" * 64)
    print("  " + _verdict)
    print("  → " + _hint)
    print("─" * 64)
    print("")
    print(f"📄 полный разговор записан: {report_path}")
    print("═" * 64)


def _finish(report, report_path):
    """Ранний выход: отчёт закроет finally в run_tester. Здесь только метка."""
    print("")
    print(f"📄 отчёт записан: {report_path}")
    return


def main():
    ap = argparse.ArgumentParser(
        description="Экспресс-тестер: живой Совет на истории CSV (без MT5)")
    ap.add_argument("csv",    help="путь к CSV (формат MT5)")
    ap.add_argument("symbol", help="тикер (XAUUSD, EURUSD...)")
    ap.add_argument("tf",     help="таймфрейм этого CSV (H4, D1...)")
    ap.add_argument("--signals", type=int, default=1,
                    help="сколько срабатываний Искры поймать (по умолч. 1)")
    ap.add_argument("--point", default=None,
                    help="шаг цены, если тестер не знает тикер")
    ap.add_argument("--warmup", type=int, default=60,
                    help="сколько баров пропустить на разгон индикаторов")
    ap.add_argument("--loose", action="store_true",
                    help="мягкое сито (сейчас не влияет на разворотный бар — "
                         "формула Necron одна на оба режима; оставлен на будущее)")
    ap.add_argument("--learn", action="store_true",   # TESTER_STERILE_V1
                    help="учебный прогон: ДНК агентов мутирует "
                         "(по умолчанию стерильно — смотрим, не калеча)")
    args = ap.parse_args()

    run_tester(args.csv, args.symbol, args.tf,
               n_signals=args.signals, point_override=args.point,
               warmup=args.warmup, loose=args.loose,
               learn=args.learn)   # TESTER_STERILE_V1


if __name__ == "__main__":
    main()

# TESTER_EXPRESS_CARTRIDGE_V1 — маркер идемпотентности

# TESTER_EXPRESS_SOUL_IGNORE_V1 — маркер идемпотентности

# ISKRA_WORKING_TF_FIRST_V1 — маркер идемпотентности

# TESTER_ISKRA_BD_FIX_V1 — маркер идемпотентности
