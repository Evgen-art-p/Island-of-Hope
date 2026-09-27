# studio/modules/trading/mt5_feed.py
# ─────────────────────────────────────────────────────────────
# НАСОС КОТИРОВОК — живой поток из терминала MetaTrader 5
# Версия: 1.0 · Спринт 45 · 2026-06-16
#
# ЗАКОН ЭТОГО ФАЙЛА:
#   · Он НЕ знает математику Вильямса (она в williams_core.py).
#   · Он НЕ знает линзы агентов (они в hooks.py).
#   · Он НЕ знает заранее ни одного тикера и ни одного таймфрейма.
#
#   Его работа — качать бары из терминала и отдавать их дальше.
#   Что качать — написано в state/feed_config.json (watchlist).
#   С какой точностью (point) — спрашивает у самого терминала
#   через symbol_info(symbol).point. Никаких встроенных таблиц.
#
#   Два режима на каждый инструмент watchlist:
#     "data"    — посчитать сводку и записать json (индикатор/дашборд).
#                 Ноль реальных ордеров, ноль LLM.
#     "council" — отдать бары живому Совету (A01–A09) на решение.
#
#   Боевой режим (реальные ордера) по умолчанию ВЫКЛЮЧЕН.
#   Включается только явным флагом live=true в конфиге инструмента.
#   Без него Совет считает и пишет, но руки в рынок не тянет.
# ─────────────────────────────────────────────────────────────

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ── Пути ──────────────────────────────────────────────────────
_HERE        = Path(__file__).resolve().parent
CONFIG_PATH  = _HERE / "state" / "feed_config.json"
STATE_DIR    = _HERE / "state"
OUT_DIR      = _HERE / "state" / "feed_out"   # сюда пишутся сводки режима data

# Таймфреймы MT5: имя → код терминала.
# Это НЕ привязка к активу — это словарь перевода человеческих
# названий ТФ в числовые коды MetaTrader. Любой инструмент торгуется
# на этих же ТФ, поэтому таблица универсальна.
_TF_MAP = {
    "M1": 1, "M5": 5, "M10": 10, "M15": 15, "M30": 30,
    "H1": 16385, "H2": 16386, "H4": 16388, "H8": 16392, "H12": 16396,
    # SVEZHEST_V1: W1 и MN1 были 16409 и 16410 — таких кодов у MT5
    # нет. Недельный и месячный этажи город не получал НИКОГДА,
    # а по ним считается компас: он был слеп по определению.
    "D1": 16408, "W1": 32769, "MN1": 49153,
}

# Конфиг по умолчанию — создаётся при первом запуске, если файла нет.
# Шеф протягивает демо, дальше правит этот json (или кнопки в дашборде).
_DEFAULT_CONFIG = {
    "_comment": "watchlist — что наблюдать. mode: data|council. live: реальные ордера (по умолчанию false).",
    "poll_seconds": 60,
    "history_bars": 2000,
    "watchlist": [
        {"symbol": "XAUUSD", "timeframe": "H4", "mode": "data", "live": False}
    ],
}


# ════════════════════════════════════════════════════════════
# КОНФИГ
# ════════════════════════════════════════════════════════════

def _load_config() -> dict:
    """Читает feed_config.json. Если нет — создаёт дефолтный и возвращает его."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(_DEFAULT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[FEED] 📄 Создан конфиг по умолчанию: {CONFIG_PATH}")
        return json.loads(json.dumps(_DEFAULT_CONFIG))
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[FEED] ⚠️  Конфиг повреждён ({e}) — беру дефолт")
        return json.loads(json.dumps(_DEFAULT_CONFIG))


# ════════════════════════════════════════════════════════════
# ТЕРМИНАЛ — единственное место, где живёт MetaTrader5
# ════════════════════════════════════════════════════════════

def _terminal():
    """
    Возвращает модуль MetaTrader5 или None, если он не установлен.
    Изолируем импорт здесь: на машине без MT5 (например, сервер сборки)
    весь модуль остаётся импортируемым, просто насос не качает.
    """
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5
    except ImportError:
        return None


def _fetch(mt5, symbol: str, tf_name: str, count: int) -> tuple[list, Optional[float]]:
    """
    Тянет из терминала последние `count` баров инструмента + его point.

    Возвращает (bars, point):
      bars  — список баров от старых к новым (формат williams_core).
      point — минимальный шаг цены ИЗ ТЕРМИНАЛА (symbol_info.point).
              Это и есть отказ от встроенной таблицы тикеров: точность
              знает брокер, мы её просто спрашиваем.

    Если что-то не так — ([], None).
    """
    tf_code = _TF_MAP.get(tf_name.upper())
    if tf_code is None:
        print(f"[FEED] ⚠️  Неизвестный таймфрейм '{tf_name}' — пропуск")
        return [], None

    if not mt5.initialize():
        print(f"[FEED] ⚠️  Терминал недоступен (initialize=False)")
        return [], None

    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"[FEED] ⚠️  Символ '{symbol}' не найден в терминале")
            return [], None
        # Убедимся, что инструмент виден в Market Watch (иначе copy_rates пуст)
        if not info.visible:
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
        point = float(info.point) if info and info.point else None

        # SVEZHEST_V1: MT5 отдаёт пусто, пока история этажа не
        # «прокачана» в терминале — особенно на старших. Лечится тем
        # же приёмом, что и везде: выбрать символ в обзор рынка и
        # повторить. Первый заход часто пустой, второй приносит.
        rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, count)
        if rates is None or len(rates) == 0:
            import time as _t
            try:
                mt5.symbol_select(symbol, True)
            except Exception:
                pass
            for _popytka in (1, 2):
                _t.sleep(0.35)
                rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, count)
                if rates is not None and len(rates):
                    print(f"[FEED] {symbol} {tf_name}: пришли со "
                          f"{_popytka + 1}-й попытки "
                          f"(история подкачалась)")
                    break
    finally:
        mt5.shutdown()

    if rates is None or len(rates) == 0:
        print(f"[FEED] ⚠️  Нет котировок: {symbol} {tf_name}")
        return [], point

    bars = []
    for r in rates:
        dt = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
        names = r.dtype.names
        bars.append({
            "date":   dt.strftime("%Y.%m.%d %H:%M"),
            "open":   float(r["open"]),
            "high":   float(r["high"]),
            "low":    float(r["low"]),
            "close":  float(r["close"]),
            "volume": int(r["tick_volume"]),
            "spread": float(r["spread"]) if "spread" in names else 0.0,
        })
    return bars, point


# ════════════════════════════════════════════════════════════
# ЛЕСЕНКА ТАЙМФРЕЙМОВ — спуск Искры v2 (Спринт 45)
# ════════════════════════════════════════════════════════════
#
# ЗАКОН: насос отдаёт ЛЮБОЙ ТФ по запросу — он слеп к активу и ТФ
# (как и весь файл). Он НЕ решает, когда спускаться: это работа Искры
# (iskra_live). Насос — руки, не голова. Здесь только дорога и дверь.

# Маршрут спуска Шефа: НЕ весь справочник MT5, а его человеческий шаг.
# Намеренно пропущены H6/H3/H2/M20/M12 — это выбор крупности, не дыры.
# Дно спуска — M5 ("до 5 минут максимум"): ниже шум съедает волну.
# PARA_MESTA_V1: лесенка переехала в Биржа/masshtab.py —
# ею пользуется не только насос, но и трейдер, и кадр.
# Здесь оставлен только читающий конец, чтобы старые
# вызовы step_down() работали как работали.
try:
    from masshtab import LESTNICA as _TF_LADDER
except Exception:
    _TF_LADDER = ["MN1", "W1", "D1", "H12", "H8", "H4",
                  "H1", "M30", "M15", "M10", "M5"]


def step_up(tf_name: str):
    """Ступень ВВЕРХ по лесенке. Была потеряна: файл
    mt5_feed_с_step_up.py лежал в уборке отдельной копией,
    вместо того чтобы жить рукой здесь."""
    try:
        from masshtab import vyshe
        return vyshe(tf_name)
    except Exception:
        return None


def step_down(tf_name: str):
    """
    Следующая ступень ВНИЗ по лесенке Шефа.
    "H4" -> "H1", "D1" -> "H12". На дне (M5) или вне лесенки -> None.
    Искра зовёт это, когда форма видна, но крупно — нужен масштаб резче.
    """
    tf = (tf_name or "").upper()
    if tf not in _TF_LADDER:
        return None
    i = _TF_LADDER.index(tf)
    if i + 1 >= len(_TF_LADDER):
        return None          # уже на дне — глубже не падаем
    return _TF_LADDER[i + 1]


def pull_bars(symbol: str, timeframe: str, count: int = 2000):
    """
    ДВЕРЬ ДЛЯ ИСКРЫ — разовый запрос баров любого актива на любом ТФ.

    Возвращает (bars, point):
      bars  — список баров от старых к новым (формат williams_core).
      point — минимальный шаг цены из терминала (symbol_info.point).
    При недоступности терминала / неизвестном ТФ -> ([], None).

    В отличие от фонового цикла — НЕ читает watchlist, НЕ пишет файлы,
    НЕ зовёт Совет. Просто: "дай <символ> на <ТФ>". Вот бары.
    Терминал поднимает и закрывает сама _fetch (initialize/shutdown
    внутри неё) — здесь второй раз его не трогаем, чтобы не было
    гонки с фоновым насосом.
    """
    # ENGINE_ONE_DOOR_V1: дверь спрашивает ИСТОЧНИК (feed_source),
    # а не лезет в терминал напрямую. Источник смотрит включённый кран
    # (real|tester) и идёт в терминал ИЛИ в папку test_data. Так спуск
    # Искры в тестовом режиме НЕ поднимает MT5 — берёт этажи из CSV.
    try:
        from feed_source import bars as _source_bars
        return _source_bars(symbol, timeframe, count)
    except Exception as _e:
        print(f"[FEED] ℹ️  источник недоступен ({_e}) — прямой терминал")
        mt5 = _terminal()
        if mt5 is None:
            print("[FEED] ℹ️  MetaTrader5 не установлен — pull_bars простаивает")
            return [], None
        return _fetch(mt5, symbol, timeframe, count)




# ════════════════════════════════════════════════════════════
# ОБРАБОТКА ОДНОГО ИНСТРУМЕНТА
# ════════════════════════════════════════════════════════════

def _handle_instrument(item: dict, history_bars: int):
    """
    Обрабатывает один инструмент из watchlist за один тик насоса.

    item = {"symbol", "timeframe", "mode", "live"}.
    Вся торговая логика — в hooks.py. Здесь только: достать бары,
    отдать в нужный режим. Этот файл остаётся слепым к рынку.
    """
    mt5 = _terminal()
    if mt5 is None:
        print("[FEED] ℹ️  MetaTrader5 не установлен — насос простаивает")
        return

    symbol    = item.get("symbol", "")
    tf_name   = item.get("timeframe", "H4")
    mode      = item.get("mode", "data")
    live      = bool(item.get("live", False))
    if not symbol:
        return

    bars, point = _fetch(mt5, symbol, tf_name, history_bars)
    if not bars or point is None:
        return

    # ── Импортируем мозги ЗДЕСЬ (поздний импорт = нет циклов) ──
    import hooks

    if mode == "council":
        # Живой Совет принимает решение по последнему бару.
        # live прокидывается насквозь: hooks решит, слать ордер или
        # только посчитать (предохранитель боевого режима внутри hooks).
        hooks.run_live_council(bars, symbol, tf_name, point, live=live)
        print(f"[FEED] ⚔️  Совет отработал: {symbol} {tf_name} "
              f"(live={'ДА' if live else 'нет'})")
    else:
        # Режим data: посчитать сводку для индикатора/дашборда. Ноль ордеров.
        summary = hooks.scan_for_feed(bars, symbol, tf_name, point)
        _write_feed_out(symbol, tf_name, summary)
        n = len(summary.get("signals", []))
        live_status = summary.get("live", {}).get("t1_status", "?")
        print(f"[FEED] 📊 {symbol} {tf_name}: {n} сигналов, t1={live_status}")


def _write_feed_out(symbol: str, tf_name: str, summary: dict):
    """
    Пишет сводку режима data в state/feed_out/<symbol>_<tf>.json.
    Это читают дашборд (вкладка Биржа) и — при желании — индикатор MT5.
    Один файл на инструмент: watchlist может расти, файлы не дерутся.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{symbol}_{tf_name}.json"
    payload = {
        "symbol":    symbol,
        "timeframe": tf_name,
        "updated":   datetime.now().isoformat(),
        **summary,
    }
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, separators=(",", ":")),
        encoding="utf-8",
    )


# ════════════════════════════════════════════════════════════
# ЦИКЛ НАСОСА
# ════════════════════════════════════════════════════════════

def _loop():
    """Бесконечный цикл: каждые poll_seconds обходит весь watchlist."""
    cfg = _load_config()
    poll = int(cfg.get("poll_seconds", 60))
    hist = int(cfg.get("history_bars", 2000))
    watch = cfg.get("watchlist", [])
    print(f"[FEED] ▶ Насос запущен: {len(watch)} инструм., "
          f"каждые {poll}с, история {hist} баров")

    while True:
        try:
            # Перечитываем конфиг каждый круг — Шеф меняет watchlist
            # на лету (или дашборд правит json), перезапуск не нужен.
            cfg   = _load_config()
            poll  = int(cfg.get("poll_seconds", 60))
            hist  = int(cfg.get("history_bars", 2000))
            watch = cfg.get("watchlist", [])
            for item in watch:
                try:
                    _handle_instrument(item, hist)
                except Exception as e:
                    sym = item.get("symbol", "?")
                    print(f"[FEED] ⚠️  Сбой по {sym}: {e}")
        except Exception as e:
            print(f"[FEED] ⚠️  Сбой цикла: {e}")
        time.sleep(poll)


def start_mt5_feed():
    """
    Точка входа для main.py. Запускает насос в фоновом потоке.
    Безопасно вызывать на машине без MT5 — поток просто будет
    простаивать с сообщением, приложение не падает.
    """
    threading.Thread(target=_loop, daemon=True, name="MT5Feed").start()
    print("[FEED] 🚀 Фоновый насос котировок запущен")


# ── Ручной прогон для проверки ───────────────────────────────
if __name__ == "__main__":
    # Один проход по watchlist без бесконечного цикла — для отладки.
    cfg  = _load_config()
    hist = int(cfg.get("history_bars", 2000))
    for it in cfg.get("watchlist", []):
        _handle_instrument(it, hist)

# SVEZHEST_V1 - marker
