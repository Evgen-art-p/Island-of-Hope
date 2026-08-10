# studio/modules/trading/feed_source.py
# ─────────────────────────────────────────────────────────────
# ИСТОЧНИК БАРОВ — два крана под одним лицом
# ENGINE_ONE_DOOR_V1 · 2026-06-23 · Брат + Шеф
#
# ЗАКОН (слово Шефа): «есть кнопки режимов, одна включает один
# источник, другая — другой, но читает один движок».
#
# Снаружи источник один: bars(symbol, tf, count) -> (bars, point).
# Внутри — какой кран включён:
#   РЕАЛ   → терминал MT5 (как было, ни байта не меняем)
#   ТЕСТ   → папка test_data/*.csv (вся лесенка этажей из файлов)
#
# Кран переключают КНОПКИ кабинета (real|tester). Они пишут режим
# на общую площадь — trading_state["feed"] — единственный файл правды
# цеха (туда же Искра пишет память). Никакого второго файла-флага.
#
# Движок, Искра, спуск — слепы к крану. Зовут bars() и получают бар.
# MT5 в тестовом режиме НЕ поднимается вообще — кран закрыт.
# ─────────────────────────────────────────────────────────────

from pathlib import Path
from typing import Optional, Tuple

_HERE = Path(__file__).resolve().parent
_TEST_DATA = _HERE / "test_data"


# ════════════════════════════════════════════════════════════
# КАКОЙ КРАН ВКЛЮЧЁН — читаем с площади (trading_state["feed"])
# ════════════════════════════════════════════════════════════

def get_feed_mode() -> dict:
    """
    Читает включённый кран с общей площади.
    Возвращает {"mode": "real"|"tester", "symbol": str|None}.
    По умолчанию РЕАЛ — безопасно: если кнопку не трогали, цех живой.
    """
    try:
        from hooks import load_trading_state
        feed = load_trading_state().get("feed", {}) or {}
        mode = feed.get("mode", "real")
        return {"mode": mode if mode in ("real", "tester") else "real",
                "symbol": feed.get("symbol")}
    except Exception:
        return {"mode": "real", "symbol": None}


def set_feed_mode(mode: str, symbol: Optional[str] = None):
    """
    КНОПКА кабинета зовёт это: включить кран real|tester.
    Пишет на площадь trading_state["feed"]. Реал — кран в терминал,
    тестер — кран в папку. symbol помогает тесту найти файлы актива.
    """
    from hooks import load_trading_state, save_trading_state
    t = load_trading_state()
    t.setdefault("feed", {})
    t["feed"]["mode"] = mode if mode in ("real", "tester") else "real"
    if symbol:
        t["feed"]["symbol"] = symbol
    save_trading_state(t)


# ════════════════════════════════════════════════════════════
# МОСТИК ИМЁН — ТФ цеха → файл MT5 в папке (родной выгруз)
# ════════════════════════════════════════════════════════════
#
# MT5 выгружает периоды по-разному: старшие словом (Daily/Weekly/
# Monthly/Hourly), младшие кодом (H4/M30). Лесенка цеха — кодами
# (MN1/W1/D1/H12...). Мостик переводит код лесенки в кусок имени файла.

_TF_TO_WORD = {
    "MN1": "Monthly", "W1": "Weekly", "D1": "Daily", "H1": "Hourly",
}


def _find_csv(symbol: str, tf: str) -> Optional[Path]:
    """
    Ищет файл этажа в test_data. Пробует оба написания MT5:
    словом (XAUUSDDaily) и кодом (XAUUSDH4, XAUUSD_H4). Возвращает
    путь или None, если этого этажа в папке нет (спуск это поймёт).
    """
    sym = symbol.upper()
    tf_u = tf.upper()
    candidates = []
    # словесное написание старших ТФ
    word = _TF_TO_WORD.get(tf_u)
    if word:
        candidates.append(f"{sym}{word}.csv")
    # кодовое написание (и вариант с подчёркиванием)
    candidates.append(f"{sym}{tf_u}.csv")
    candidates.append(f"{sym}_{tf_u}.csv")
    for name in candidates:
        p = _TEST_DATA / name
        if p.exists():
            return p
    # последний шанс: регистронезависимый перебор папки
    if _TEST_DATA.exists():
        wanted = {c.lower() for c in candidates}
        for f in _TEST_DATA.glob("*.csv"):
            if f.name.lower() in wanted:
                return f
    return None


# ════════════════════════════════════════════════════════════
# ДВА КРАНА С ОДНИМ ЛИЦОМ
# ════════════════════════════════════════════════════════════

def _bars_from_terminal(symbol: str, tf: str, count: int) -> Tuple[list, Optional[float]]:
    """КРАН РЕАЛ: терминал MT5. Тонкая обёртка над тем, что уже есть."""
    from mt5_feed import _terminal, _fetch
    mt5 = _terminal()
    if mt5 is None:
        return [], None
    return _fetch(mt5, symbol, tf, count)


# FEED_SOURCE_FOLDER_CACHE_V1: кэш полного разбора CSV по абсолютному пути.
# Исторические файлы статичны в рамках одного прогона процесса —
# читаем с диска ОДИН РАЗ, дальше режем хвост из памяти. Без этого
# build_market_data (через global_anchor.global_trend, §12 Котина)
# на КАЖДЫЙ бар сита-1 заново читал и парсил старший этаж целиком —
# на H1 (94 566 баров) это превращало прогон в час+ без единого
# срабатывания (сито-1 не успевало закончить сканирование истории).
_FOLDER_BARS_CACHE: dict = {}


def _bars_from_folder(symbol: str, tf: str, count: int) -> Tuple[list, Optional[float]]:
    """
    КРАН ТЕСТ: папка test_data. Читает CSV нужного этажа, отдаёт
    последние count баров + point из таблички (терминала-то нет).
    MT5 НЕ трогаем — вот вся суть герметичности.

    FEED_SOURCE_FOLDER_CACHE_V1: полный разбор файла кэшируется по абсолютному
    пути — читаем с диска один раз за весь прогон, а не на каждый
    вызов (см. докстроку патча). Хвост (count) режется из кэша.
    """
    from williams_core import read_mt5_csv
    p = _find_csv(symbol, tf)
    if p is None:
        return [], None
    key = str(p.resolve())
    bars = _FOLDER_BARS_CACHE.get(key)
    if bars is None:
        bars = read_mt5_csv(str(p))
        _FOLDER_BARS_CACHE[key] = bars or []
    if not bars:
        return [], None
    point = _test_point(symbol)
    tail = bars[-count:] if count and len(bars) > count else bars
    return tail, point


_TEST_POINTS = {
    "XAUUSD": 0.01, "XAGUSD": 0.001, "EURUSD": 0.00001, "GBPUSD": 0.00001,
    "USDJPY": 0.001, "AUDUSD": 0.00001, "USDCHF": 0.00001, "USDCAD": 0.00001,
    "NZDUSD": 0.00001, "BTCUSD": 0.01, "ETHUSD": 0.01,
}


def _test_point(symbol: str) -> float:
    """Шаг цены для тестового режима (терминал не спросить — он закрыт)."""
    return _TEST_POINTS.get(symbol.upper(), 0.00001)


# ════════════════════════════════════════════════════════════
# ЕДИНОЕ ЛИЦО — движок зовёт только это
# ════════════════════════════════════════════════════════════

def bars(symbol: str, tf: str, count: int = 2000) -> Tuple[list, Optional[float]]:
    """
    ДАЙ БАР на этаже tf. Слепо к крану — смотрит, что включено кнопкой,
    и идёт в терминал ИЛИ в папку. Возвращает (bars, point) в формате
    williams_core. Движок/Искра/спуск зовут ровно это и не знают крана.
    """
    mode = get_feed_mode()["mode"]

    # FEED_CHEREZ_ISTOKI_V1: сперва спрашиваем ИСТОК — файл в папке
    # Биржа/истоки/. Положил туда файл — появился новый источник, эту
    # функцию править не надо. Исток, ответивший барами, втыкается в
    # гнездо Маяка: город видит, откуда течёт.
    try:
        import istoki as _ist
        _b, _p = _ist.bars(mode, symbol, tf, count)
        if _b:
            return _b, _p
    except Exception as _e_ist:
        print(f"[FEED] истоки недоступны ({_e_ist}) — иду прежним путём")

    # Истока нет, он молчит или папку ещё не положили — работаем как
    # работали. Отсутствие нового не должно ломать старое.
    if mode == "tester":
        return _bars_from_folder(symbol, tf, count)
    return _bars_from_terminal(symbol, tf, count)
