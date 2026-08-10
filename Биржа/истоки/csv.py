# -*- coding: utf-8 -*-
# ISTOK_CSV_V1
"""
ИСТОК: папка с файлами истории — тестер.

Та же работа, что делал кран `tester`: ищет CSV по символу и этажу в
`Биржа/test_data` и читает его. Данные статичны — это НЕ живой рынок,
и на кадре это видно по датам.
"""
import sys
from pathlib import Path

ИМЯ = "История (CSV)"
КЛЮЧ = "csv"
РОД = "сервис"

_BIRZHA = Path(__file__).resolve().parent.parent


def zhiv() -> bool:
    d = _BIRZHA / "test_data"
    return d.exists() and any(d.glob("*.csv"))


def bars(symbol: str, tf: str, count: int = 2000):
    if str(_BIRZHA) not in sys.path:
        sys.path.insert(0, str(_BIRZHA))
    import feed_source
    fn = getattr(feed_source, "_bars_from_folder", None)
    if fn is None:
        return [], None
    return fn(symbol, tf, count)
