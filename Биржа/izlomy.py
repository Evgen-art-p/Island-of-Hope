# -*- coding: utf-8 -*-
# NEKRON_BUDIT_V1
"""
ИЗЛОМЫ — где рынок ломался по-настоящему.

СЛОВО ШЕФА (02.09), глядя на разметку: «уровень 2 — шикарные точки,
это прям точки ноль». Объяснить словами, чем настоящий экстремум
отличается от заусеницы, он не смог — «вижу и все», — прислал скрин с
красными квадратами. Механика собрана по нему.

ЗАКОН ЭТОГО ФАЙЛА
    Только разметка. Ни входа, ни направления, ни суждения о том,
    годится место или нет. Порогов и подобранных чисел внутри нет
    вовсе — правило безразмерно и одинаково работает на всех этажах.

ЗАДЕРЖКА — ЭТО ПРИРОДА, А НЕ БРАК
    Излом признаётся только когда пришёл следующий фрактал того же
    типа и оказался слабее. Медиана — около десяти баров H4. Из
    ролика про фрактальную геометрию: фракталы не предсказывают, они
    показывают структуру прошлого. Поэтому излом не может быть
    сигналом входа — он говорит ГДЕ, а КОГДА говорит разворотный бар.
"""
from __future__ import annotations

from typing import Optional


def _fraktaly(bars: list) -> list:
    """Фракталы Вильямса одним списком, по порядку баров."""
    try:
        from williams_core import detect_fractals
    except Exception:
        return []
    fr = detect_fractals(bars) or {}
    spisok = []
    for storona, tip in (("all_up", "верх"), ("all_down", "низ")):
        for f in (fr.get(storona) or []):
            i, c = f.get("bar_index"), f.get("price")
            if i is None or c is None:
                continue
            spisok.append({"бар": i, "тип": tip, "цена": c,
                           "дата": f.get("date")})
    spisok.sort(key=lambda x: x["бар"])
    return spisok


def _krayniy(a: dict, b: dict) -> dict:
    """Из двух изломов одного типа — тот, что дальше ушёл."""
    if a["тип"] == "верх":
        return a if a["цена"] >= b["цена"] else b
    return a if a["цена"] <= b["цена"] else b


def uroven_1(spisok: list) -> list:
    """Чередование: в серии одного типа держим самый крайний."""
    itog = []
    for f in spisok:
        if itog and itog[-1]["тип"] == f["тип"]:
            itog[-1] = _krayniy(itog[-1], f)
        else:
            itog.append(dict(f))
    return itog


def uroven_2(ur1: list) -> list:
    """Та же лупа поверх: крайнее ОБОИХ соседей своего типа."""
    itog = []
    for n, f in enumerate(ur1):
        sosedi = [x for m, x in enumerate(ur1)
                  if x["тип"] == f["тип"] and abs(m - n) <= 2 and m != n]
        if not sosedi:
            continue
        if f["тип"] == "верх":
            if all(f["цена"] > s["цена"] for s in sosedi):
                itog.append(dict(f))
        else:
            if all(f["цена"] < s["цена"] for s in sosedi):
                itog.append(dict(f))
    return itog


def izlomy(bars: list, uroven: int = 2) -> list:
    """Изломы указанного уровня на этих барах."""
    if not bars or len(bars) < 12:
        return []
    ur1 = uroven_1(_fraktaly(bars))
    return ur1 if uroven == 1 else uroven_2(ur1)


def dozrel(bars: list) -> Optional[dict]:
    """Излом ур.2, про который стало известно ИМЕННО НА ПОСЛЕДНЕМ баре.

    Момент созревания один и определён точно: излом признаётся, когда
    ДОСТРОИЛСЯ его правый сосед своего типа — то есть на баре
    «сосед + 2» (фракталу нужны два бара справа).

    Так было не сразу. Сперва разметка считалась дважды — до бара и
    включая его, — и что появилось, то и считалось созревшим. Прибор
    ДРЕБЕЗЖАЛ: цепочка чередования достраивается, излом успевал
    выпасть и вернуться, и за год выходило 174 побудки вместо 86
    настоящих изломов. Теперь каждый объявляется один раз.
    """
    if not bars or len(bars) < 14:
        return None
    ur1 = uroven_1(_fraktaly(bars))
    posl = len(bars) - 1
    for n, f in enumerate(ur1):
        if n - 2 < 0 or n + 2 >= len(ur1):
            continue
        lev, prav = ur1[n - 2], ur1[n + 2]
        if prav["бар"] + 2 != posl:      # созревает не сейчас
            continue
        krayneye = (f["цена"] > lev["цена"] and f["цена"] > prav["цена"]
                    if f["тип"] == "верх" else
                    f["цена"] < lev["цена"] and f["цена"] < prav["цена"])
        if krayneye:
            x = dict(f)
            x["баров_назад"] = posl - f["бар"]
            return x
    return None


# NEKRON_BUDIT_V1 - marker
