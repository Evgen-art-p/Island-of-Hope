# -*- coding: utf-8 -*-
# RUKA_MAYAKA_V1
"""
РУКА МАЯКА — выход города наружу, одной дверью.

ЗАКОН ЭТОГО ФАЙЛА
    Второго выхода в интернет город не заводит. Внутри зовётся тот же
    `Маяк/mayak.py`, которым пользуются житель дома и Академия — и
    ключ Tavily остаётся в одном месте, и визиты пишутся в один
    журнал Маяка.

    Рука НИЧЕГО не решает: приносит найденное и говорит, откуда оно.
    Не горит Маяк (нет ключа) — так и отвечает. Ссылок не выдумывает:
    выдуманная ссылка хуже отсутствия ответа.

ЦЕНА
    Срабатывает только когда мозг сам позвал. Каждый выход печатается
    строкой [МАЯК] 🔦 — тихих трат быть не должно.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

_GOROD = Path(__file__).resolve().parent
_KOREN = _GOROD.parent
for _p in (str(_KOREN / "Маяк"), str(_KOREN)):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)


def shema() -> list:
    """Описание руки для модели. Сухо: прибор, а не советчик."""
    return [{"type": "function", "function": {
        "name": "sprosit_mayak",
        "description": (
            "Выйти во внешний мир через Маяк Пробуждения и узнать то, "
            "чего ты знать не можешь: свежие новости, текущие события, "
            "сегодняшние данные, чужие публикации. Возвращает найденное "
            "с источниками. Не зови ради того, что и так знаешь."),
        "parameters": {"type": "object", "properties": {
            "запрос": {"type": "string",
                       "description": "что именно узнать, обычными словами"}},
            "required": ["запрос"]}}}]


def _pusto(prichina: str) -> str:
    return f"Маяк не принёс ответа: {prichina}. Ссылки выдумывать не буду."


def sprosit(zapros: str, kto: str = "") -> str:
    """Спросить мир. Всегда возвращает текст — пустой ответ тоже ответ."""
    zapros = (zapros or "").strip()
    if not zapros:
        return _pusto("пустой запрос")
    try:
        import mayak
    except Exception as e:
        return _pusto(f"Маяк недоступен ({e})")
    if hasattr(mayak, "gorit") and not mayak.gorit():
        return _pusto("Маяк не горит — нет ключа TAVILY_KEY в .env")
    try:
        import asyncio
        rez = mayak.poisk(zapros)
        if asyncio.iscoroutine(rez):
            # мозги слотов синхронные — крутим свою петлю
            try:
                petlya = asyncio.get_running_loop()
            except RuntimeError:
                petlya = None
            if petlya and petlya.is_running():
                import concurrent.futures as _cf
                with _cf.ThreadPoolExecutor(max_workers=1) as ex:
                    rez = ex.submit(asyncio.run, rez).result()
            else:
                rez = asyncio.run(rez)
        nashlos = mayak.dlya_promta(rez)
    except Exception as e:
        return _pusto(f"сбой поиска ({e})")

    print(f"[МАЯК] 🔦 {kto or 'кто-то'} спросил мир: «{zapros[:70]}» → "
          f"{len(nashlos)} симв.")
    try:
        mayak.zapisat_vizit(kto or "мозг", zapros, bool(nashlos))
    except Exception:
        pass
    if not nashlos:
        return _pusto("по запросу ничего не нашлось")
    return f"=== МАЯК · найдено снаружи ===\n{nashlos}"


def ruki(kto: str = "") -> dict:
    """{имя: функция} — подмешивается к рукам любого мозга."""
    return {"sprosit_mayak":
            lambda args: sprosit(str(args.get("запрос", "")), kto)}


# RUKA_MAYAKA_V1 - marker
