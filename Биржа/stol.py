# -*- coding: utf-8 -*-
# STOL_KODOM_V1
"""
СТОЛ ТРЕЙДЕРА, НАКРЫТЫЙ КОДОМ.

Раньше стол накрывали четыре живых сенсора: Искра клала разворотный
бар, Морж — пасть и натяжение, Паникёр — фазу толпы, Ганс — фрактал.
По решению Шефа (06.08) сенсоры стали математикой и уехали из цеха.
Этот файл делает их работу — без голосов и без вызовов модели.

ГДЕ ОН ЛЕЖИТ И ПОЧЕМУ ЗДЕСЬ
    В папке `Биржа/`, рядом с `williams_core.py` и `grafik.py`.
    Математика НИЧЬЯ: она не принадлежит слоту и не носит характера.
    Слот несёт роль и зовёт математику — так велит канон.

ЧТО ОН ГАРАНТИРУЕТ
    Те же имена полей, что клали сенсоры. Мозг трейдера подмены не
    замечает: читает как читал, только теперь ему не надо ждать,
    пока кто-то проснётся и накроет.

ЧЕГО ОН НАРОЧНО НЕ ДЕЛАЕТ

    Не интерпретирует. Сенсор-голос переводил объём в «жадность» и
    «недоверие» — код так не умеет и не должен: он кладёт ФАКТ
    (GREEN/FADE/FAKE/SQUAT), а что это значит, решает трейдер. Это и
    было решением Шефа: сенсор докладывает, трейдер судит.

    Не спускается по этажам. Спуск был работой Искры-диспетчера; по
    новому порядку направление приходит СВЕРХУ (со старшего этажа), а
    работаем на том, что задан. Никто больше не ищет бар «где-нибудь».

    Не решает за трейдера и не ставит порогов. Ни одного числа,
    которого нет в источниках.

    STOL_BEZ_VYVODOV_V1 (слово Шефа 07.08): «то, что ты посчитал код
    готовый, он не будет работать». И это верно: если код нашёл
    разворотный бар, посчитал согласие с водой и объявил фрактал
    действительным — трейдеру остаётся кивнуть. Выбирать нечего,
    смотреть незачем, и получается бот с характером.

    Поэтому граница проведена так:

      ПОКАЗАНИЕ ПРИБОРА — остаётся. Где стоят линии и в каком они
        порядке, спит пасть или нет, какое значение у гистограммы и
        растёт ли она, где последние фракталы, какое окно объёма,
        какое натяжение, куда смотрит старший Аллигатор.

      ВЫВОД — убран. «Разворотный бар найден», «согласен с водой»,
        «фрактал действителен», «структура читается». Это уже
        суждения, и делать их трейдеру.

    Приборы лежат в ключе «приборы». Старые ключи сенсоров остаются
    пустыми — их читает мозг, и пустота там честная: сенсоров нет.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in sys.path:
    sys.path.insert(0, str(_BIRZHA))


# ─────────────────────────────────────────────────────────────
# ПУСТОЙ СТОЛ — тот же по форме, что и накрытый
# ─────────────────────────────────────────────────────────────
# Читатель не должен ловить KeyError на холодном старте: пустой стол
# отличается от накрытого значениями, а не набором полей.

def pustoy(self_key: str = "brut") -> dict:
    return {
        "iskra": {"t1_status": "NOT_FOUND", "zero_point_price": None,
                  "trend_direction": None, "dlina": None,
                  "struktura_chitaetsya": False,
                  "compass": None, "soglasie": None,
                  "found_timeframe": None},
        "morj": {"morj_status": "SLEEPING", "wave_1_validated": False,
                 "tension_peak": False, "tension_ratio": None},
        "panic": {"panic_phase": None, "crowd_sentiment": None},
        "hans": {"fractal_valid": False, "fractal_side": None,
                 "fractal_price": None},
        "arkhiv": {},
        "self": {},
        "приборы": {},
    }


def _status_alligatora(al: dict) -> str:
    """Словарь Моржа, слово в слово как он его писал."""
    if al.get("sleeping"):
        return "SLEEPING"
    if al.get("mature"):
        return "MATURE"
    if al.get("opening"):
        return "WAKING"
    return "AWAKE"


def nakryt(symbol: str, timeframe: str,
           md: Optional[dict] = None,
           bars: Optional[list] = None,
           point: Optional[float] = None,
           self_key: str = "brut") -> dict:
    """Накрывает стол по факту рынка. Не падает никогда — в худшем
    случае отдаёт пустой стол той же формы.

    md/bars/point можно передать, если вызывающий их уже посчитал —
    тогда второй раз считать не будем.
    """
    stol = pustoy(self_key)

    # справка Архивариуса и своя обратная связь по ведению остаются
    # с шины: Архивариус живой и кладёт сам, а «self» пишет сам трейдер
    try:
        from hooks import load_trading_state
        t = load_trading_state()
        stol["arkhiv"] = t.get("arkhiv", {}) or {}
        stol["self"] = t.get(self_key, {}) or {}
    except Exception:
        pass

    try:
        if md is None:
            from feed_source import bars as source_bars
            from williams_core import build_market_data
            if bars is None:
                bars, point = source_bars(symbol, timeframe, count=400)
            if not bars or len(bars) < 42:
                return stol
            md = build_market_data(bars, symbol=symbol,
                                   timeframe=timeframe, point=point)
        if not md:
            return stol
    except Exception:
        return stol

    al = md.get("alligator", {}) or {}
    nb = md.get("necron_bar", {}) or {}
    rb = md.get("rubber_band", {}) or {}
    wf = md.get("wave_form", {}) or {}
    fr = md.get("fractals", {}) or {}
    mfi = md.get("mfi", {}) or {}

    # ── КОМПАС: направление СО СТАРШЕГО этажа ────────────────
    # Порядок Шефа (04.08): первым идёт большая вода, и берётся она
    # своим инструментом на своём масштабе. Раньше компас наследовал
    # этаж Искры — то есть был эхом сигнала, а не проверкой.
    compass = None
    try:
        from global_anchor import global_trend
        st = global_trend(symbol, timeframe,
                          as_of_date=(md.get("bar_time")))
        b = (st or {}).get("bias")
        compass = b if b in ("BULL", "BEAR") else None
    except Exception:
        compass = None
    if compass is None:
        gb = md.get("global_bias")
        compass = gb if gb in ("BULL", "BEAR") else None

    napravlenie = nb.get("direction")

    # STOL_BEZ_VYVODOV_V1: сигнала здесь БОЛЬШЕ НЕТ. Разворотный бар,
    # согласие с водой и «структура читается» были выводами кода —
    # теперь их делает трейдер, глядя на картинку. Остаются компас
    # (показание старшего Аллигатора — факт рынка, а не решение) и
    # этаж, на котором работаем.
    stol["iskra"] = {
        "t1_status": None,
        "trend_direction": None,
        "zero_point_price": None,
        "dlina": None,
        "struktura_chitaetsya": None,
        "compass": compass,
        "soglasie": None,
        "found_timeframe": timeframe,
    }

    stol["morj"] = {
        "morj_status": _status_alligatora(al),   # состояние пасти — факт
        "wave_1_validated": None,                # был вывод, убран
        "tension_peak": bool(rb.get("is_peak")),
        "tension_ratio": rb.get("tension_ratio"),
    }

    stol["panic"] = {
        # ФАКТ окна Вильямса, а не пересказ настроения
        "panic_phase": mfi.get("type"),
        "crowd_sentiment": None,
    }

    # STOL_BEZ_VYVODOV_V1: «действительный фрактал» был выводом — какой
    # из двух годится, решает тот, кто выбрал себе вход. Отдаём ОБА как
    # координаты на графике.
    stol["hans"] = {
        "fractal_valid": None,
        "fractal_side": None,
        "fractal_price": None,
    }

    # ── ПРИБОРЫ: голые показания, без единого суждения ────────
    ao = md.get("ao", {}) or {}
    stol["приборы"] = {
        "старший_аллигатор": compass,          # куда смотрит большая вода
        "этаж": timeframe,
        "аллигатор": {
            "челюсть": al.get("jaw"), "зубы": al.get("teeth"),
            "губы": al.get("lips"),
            "спит": al.get("sleeping"),
            "баров_открыт": al.get("bars_open"),
        },
        "ao": {
            "значение": ao.get("value"), "прошлое": ao.get("prev_value"),
            "растёт": ao.get("direction"),
            "перешёл_ноль": ao.get("crossed_zero"),
        },
        "фракталы": {"вверх": fr.get("last_up"), "вниз": fr.get("last_down")},
        "объём_окно": mfi.get("type"),
        "натяжение": {"сейчас": rb.get("distance_now"),
                      "пик": rb.get("distance_max"),
                      "доля_от_пика": rb.get("tension_ratio")},
        "цена": md.get("price"),
        "бар": md.get("bar_time"),
    }

    return stol


def slovami(stol: dict) -> str:
    """Приборы человеку — для кабинета и для проверки без модели.

    Ни одного вывода: только показания. Что они значат — говорит тот,
    кто смотрит.
    """
    p = stol.get("приборы", {}) or {}
    al = p.get("аллигатор", {}) or {}
    ao = p.get("ao", {}) or {}
    fr = p.get("фракталы", {}) or {}
    nt = p.get("натяжение", {}) or {}
    c = p.get("цена", {}) or {}
    L = [
        f"старший Аллигатор: {p.get('старший_аллигатор') or '—'}   "
        f"этаж: {p.get('этаж') or '—'}",
        f"Аллигатор: челюсть {al.get('челюсть')}  зубы {al.get('зубы')}  "
        f"губы {al.get('губы')}   спит: {al.get('спит')}   "
        f"открыт баров: {al.get('баров_открыт')}",
        f"AO: {ao.get('значение')} (было {ao.get('прошлое')})   "
        f"растёт: {ao.get('растёт')}   перешёл ноль: {ao.get('перешёл_ноль')}",
        f"фракталы: вверх {(fr.get('вверх') or {}).get('price')}   "
        f"вниз {(fr.get('вниз') or {}).get('price')}",
        f"объём (окно): {p.get('объём_окно') or '—'}",
        f"натяжение от губ: {nt.get('сейчас')} п. (пик {nt.get('пик')}, "
        f"доля {nt.get('доля_от_пика')})",
        f"цена: O={c.get('open')} H={c.get('high')} L={c.get('low')} "
        f"C={c.get('close')}   бар: {p.get('бар')}",
    ]
    return "\n".join(f"— {x}" for x in L)


if __name__ == "__main__":
    # Проверка без модели и без денег: python stol.py EURUSD H1
    s = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    tf = sys.argv[2] if len(sys.argv) > 2 else "H1"
    print(f"Стол {s} {tf}:\n")
    print(slovami(nakryt(s, tf)))
