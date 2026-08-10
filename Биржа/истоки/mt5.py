# -*- coding: utf-8 -*-
# ISTOK_MT5_V1
"""
ИСТОК: терминал MetaTrader 5 — живой рынок.

Это обёртка вокруг того, что и раньше делал `mt5_feed`: поднимает
терминал, проверяет, что инструмент виден в обзоре рынка, и тянет
бары. Ничего нового не считает — просто теперь он ИСТОК, то есть
объявляет себя сам и виден в гнезде Маяка.
"""
import sys
from pathlib import Path

ИМЯ = "МТ5 терминал"
КЛЮЧ = "mt5"
РОД = "инструмент"          # горит постоянно, по закону гнёзд

_BIRZHA = Path(__file__).resolve().parent.parent


def _feed():
    if str(_BIRZHA) not in sys.path:
        sys.path.insert(0, str(_BIRZHA))
    import mt5_feed
    return mt5_feed


def zhiv() -> bool:
    """На связи ли терминал. Закрыт — False, и это не ошибка."""
    try:
        f = _feed()
        t = getattr(f, "_terminal", None)
        if t is None:
            return False
        mt5 = t()
        if mt5 is None:
            return False
        ok = bool(mt5.initialize())
        try:
            mt5.shutdown()
        except Exception:
            pass
        return ok
    except Exception:
        return False


def bars(symbol: str, tf: str, count: int = 2000):
    f = _feed()
    for imya in ("bars", "get_bars", "_fetch"):
        fn = getattr(f, imya, None)
        if fn is None:
            continue
        try:
            r = fn(symbol, tf, count)
        except TypeError:
            continue
        if isinstance(r, tuple):
            return r
        return r, None
    return [], None
