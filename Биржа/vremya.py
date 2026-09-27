# -*- coding: utf-8 -*-
# VREMYA_GORODA_V1
"""
ЧАСЫ ГОРОДА — одни на всех.

ЗАКОН ЭТОГО ФАЙЛА
    Время на рынке не совпадает ни с часами машины, ни с UTC: у
    брокера свой сервер, и его пояс — не наше дело выбирать, а наше
    дело УЗНАТЬ. Поэтому здесь ничего не настраивается руками.
    Спросили терминал один раз при запуске — дальше знаем.

    Сессии живут ЗДЕСЬ (SESSII_V_CHASAH_V1, 27.09): переехали из
    kalibrovka.py, когда калибровка ушла в чулан. Таблица одна на
    город — других мнений о том, когда открыта Европа, нет.
"""
from __future__ import annotations

import sys as _sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

MSK = timezone(timedelta(hours=3))      # Москва круглый год, перевода нет

# Узнанный сдвиг сервера от UTC, в часах. None — ещё не спрашивали.
_SDVIG: float | None = None
_OTKUDA: str = ""


def zabyt():
    """Забыть узнанное — спросим терминал заново (перевод часов,
    сменили брокера, подняли терминал позже города)."""
    global _SDVIG, _OTKUDA
    _SDVIG, _OTKUDA = None, ""


def _sprosit_terminal() -> tuple:
    """(сдвиг в часах, откуда). Терминала нет — (None, причина).

    Как узнаём: берём время последнего тика по любому живому
    инструменту. Терминал отдаёт его в СВОЁМ времени, а часы машины
    знают настоящий UTC. Разница между ними и есть пояс брокера.
    Округляем до получаса — поясов в дробных минутах не бывает, а
    задержка тика на секунды не должна двигать ответ.
    """
    try:
        from mt5_feed import _terminal
        mt5 = _terminal()
    except Exception as e:
        return None, f"MetaTrader5 не импортируется ({e})"
    if mt5 is None:
        return None, "MetaTrader5 не установлен"
    if not mt5.initialize():
        return None, "терминал не отвечает"
    try:
        vse = mt5.symbols_get() or []
        imena = [s.name for s in vse if getattr(s, "visible", False)]
        if not imena:
            imena = [s.name for s in vse][:5]
        for imya in imena[:10]:
            tick = mt5.symbol_info_tick(imya)
            t = getattr(tick, "time", 0) if tick else 0
            if not t:
                continue
            seychas_utc = datetime.now(timezone.utc).timestamp()
            chasov = (float(t) - seychas_utc) / 3600.0
            # получас — самая мелкая единица поясов
            sdvig = round(chasov * 2) / 2
            if -14 <= sdvig <= 14:
                return sdvig, f"терминал ({imya})"
        return None, "терминал на связи, но тиков не отдал"
    except Exception as e:
        return None, f"сбой опроса ({e})"
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def sdvig_servera() -> tuple:
    """(сдвиг в часах или None, откуда узнали). Спрашиваем ОДИН раз."""
    global _SDVIG, _OTKUDA
    if _SDVIG is None and not _OTKUDA:
        _SDVIG, prichina = _sprosit_terminal()
        _OTKUDA = prichina if _SDVIG is None else prichina
        if _SDVIG is None:
            print(f"[ВРЕМЯ] ⚠️  сервер не спросили: {prichina}. "
                  f"Показываю МСК по часам машины.")
        else:
            znak = "+" if _SDVIG >= 0 else ""
            print(f"[ВРЕМЯ] 🕒 пояс сервера узнан сам: UTC{znak}{_SDVIG:g} "
                  f"({prichina})")
    return _SDVIG, _OTKUDA


# SESSII_V_CHASAH_V1: торговые сессии по UTC-часу (как были в kalibrovka)
_SESSII = [
    {"id": "asia",    "имя": "Азия",    "открытие": 0,  "закрытие": 9},
    {"id": "europe",  "имя": "Европа",  "открытие": 8,  "закрытие": 17},
    {"id": "america", "имя": "Америка", "открытие": 13, "закрытие": 22},
]


def sessii_seychas(now_utc: datetime | None = None) -> list:
    """Какие сессии открыты прямо сейчас. Таблица — выше, своя."""
    now = now_utc or datetime.now(timezone.utc)
    tablica = _SESSII
    h = now.hour
    return [s["имя"] for s in tablica
            if s.get("открытие", 0) <= h < s.get("закрытие", 0)]


def seychas() -> dict:
    """Одна дверь ко времени. Всё, что городу нужно знать про час.

    {utc, msk, server, сдвиг, откуда, терминальное (bool), сессии,
     строка}
    """
    utc = datetime.now(timezone.utc)
    sdvig, otkuda = sdvig_servera()
    server = utc + timedelta(hours=sdvig) if sdvig is not None else None
    idut = sessii_seychas(utc)
    return {
        "utc": utc,
        "msk": utc.astimezone(MSK),
        "server": server,
        "сдвиг": sdvig,
        "откуда": otkuda,
        "терминальное": sdvig is not None,
        "сессии": idut,
        "строка": stroka(),
    }


def stroka() -> str:
    """Строка для хедера кабинета. Коротко и без вранья."""
    utc = datetime.now(timezone.utc)
    msk = utc.astimezone(MSK)
    sdvig, otkuda = sdvig_servera()
    kuski = [f"МСК {msk:%H:%M}"]
    if sdvig is not None:
        server = utc + timedelta(hours=sdvig)
        znak = "+" if sdvig >= 0 else ""
        kuski.append(f"сервер {server:%H:%M} (UTC{znak}{sdvig:g})")
    else:
        kuski.append("сервер не спросили")
    idut = sessii_seychas(utc)
    kuski.append(" + ".join(idut) if idut else "рынок спит")
    return "🕒 " + " · ".join(kuski)


if __name__ == "__main__":
    d = seychas()
    print(d["строка"])
    print(f"  UTC:    {d['utc']:%Y-%m-%d %H:%M}")
    print(f"  МСК:    {d['msk']:%Y-%m-%d %H:%M}")
    print(f"  сервер: "
          + (f"{d['server']:%Y-%m-%d %H:%M}" if d["server"] else "—"))
    print(f"  откуда: {d['откуда'] or '—'}")
    print(f"  сессии: {', '.join(d['сессии']) or 'рынок спит'}")

# VREMYA_GORODA_V1 - marker
