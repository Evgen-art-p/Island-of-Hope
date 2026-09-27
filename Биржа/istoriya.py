# -*- coding: utf-8 -*-
# MASHINA_VREMENI_V1
"""
МАШИНА ВРЕМЕНИ — где город «сейчас находится» в истории.

ЗАЧЕМ
    Чтобы ходить по прошлому как по живому рынку: остановиться в
    любой точке, посмотреть кадр, спросить трейдера, шагнуть дальше.
    Так набивается глаз — и Шефу, и трейдеру.

ЗАКОН ЭТОГО ФАЙЛА
    Момент — ОДИН на город и лежит на общей площади цеха, рядом с
    режимом крана (trading_state["feed"]). Второго места правды нет:
    иначе кадр покажет одно, стол посчитает другое.

    Момент действует ТОЛЬКО в тестерном режиме. В реале его нет и
    быть не может — там время идёт само.
"""
from __future__ import annotations

import sys as _sys
from datetime import datetime, timedelta
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

FORMAT = "%Y.%m.%d %H:%M"


def _plosh():
    from hooks import load_trading_state
    return (load_trading_state().get("feed") or {})


def gde_stoim() -> str:
    """Момент истории строкой «2026.06.23 19:00». Пусто — конца
    истории, то есть как было до машины времени."""
    return (_plosh().get("момент") or "").strip()


def postavit(moment) -> str:
    """Поставить город в точку истории. Пусто — снять курсор."""
    from hooks import load_trading_state, save_trading_state
    if isinstance(moment, datetime):
        moment = moment.strftime(FORMAT)
    moment = (moment or "").strip()
    t = load_trading_state()
    t.setdefault("feed", {})
    if moment:
        t["feed"]["момент"] = moment
    else:
        t["feed"].pop("момент", None)
    save_trading_state(t)
    return moment


def kak_vremya(s: str):
    """Строку бара — во время. Дневки и выше приходят без часов."""
    s = (s or "").strip()
    for f in (FORMAT, "%Y.%m.%d", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f)
        except ValueError:
            continue
    return None


def _vse_bary(symbol: str, etazh: str) -> list:
    """ВСЕ бары файла, мимо курсора.

    Важно: спрашивать их у крана нельзя — кран уже обрезан этим же
    курсором, и шаг вперёд упирался бы в собственный край, откатывая
    момент назад. Курсор должен смотреть на полную ленту, а обрезает
    он только то, что видят трейдер и кадр.
    """
    import feed_source as fs
    from williams_core import read_mt5_csv
    p = fs._find_csv(symbol, etazh)
    if p is None:
        return []
    klyuch = str(p.resolve())
    bars = fs._FOLDER_BARS_CACHE.get(klyuch)
    if bars is None:
        bars = read_mt5_csv(str(p)) or []
        fs._FOLDER_BARS_CACHE[klyuch] = bars
    return bars


def shag(etazh: str, skolko: int = 1, symbol: str = "") -> str:
    """Шагнуть на N баров ЭТОГО этажа вперёд (или назад, если минус).

    Шагаем не по календарю, а по реальным барам файла: в выходные и
    праздники рынка нет, и календарный шаг увёл бы в пустоту.
    """
    seychas = gde_stoim()
    sym = symbol or (_plosh().get("symbol") or "")
    if not sym:
        return seychas
    vse = _vse_bary(sym, etazh)
    if not vse:
        return seychas
    daty = [b.get("date", "") for b in vse]
    if not seychas:
        i = len(daty) - 1
    else:
        i = -1
        for j, d in enumerate(daty):
            if d <= seychas:
                i = j
            else:
                break
        if i < 0:
            i = 0
    j = max(0, min(len(daty) - 1, i + skolko))
    return postavit(daty[j])


def dokuda_est(symbol: str, etazh: str) -> tuple:
    """(первый бар, последний бар) этажа в файле — границы прогулки.
    Тоже по полной ленте, мимо курсора."""
    vse = _vse_bary(symbol, etazh)
    if not vse:
        return "", ""
    return vse[0].get("date", ""), vse[-1].get("date", "")


def zakryt_li(data_bara: str, etazh: str, moment: str) -> bool:
    """Закрыт ли бар этажа к моменту.

    Главная честность машины времени: бар, который ещё идёт, отдавать
    нельзя — в нём цены, которых в этот момент никто не знал.
    """
    if not moment:
        return True
    import masshtab
    t0 = kak_vremya(data_bara)
    tm = kak_vremya(moment)
    if t0 is None or tm is None:
        return str(data_bara) <= str(moment)
    m = masshtab.minut(etazh)
    if not m:
        return t0 <= tm
    return t0 + timedelta(minutes=m) <= tm + timedelta(minutes=1)


# MASHINA_VREMENI_V1 - marker
