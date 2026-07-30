# Биржа/rezident_menedzher.py
# ─────────────────────────────────────────────────────────────
# РЕЗИДЕНТ-МЕНЕДЖЕР — единая дверь к резиденту через его РОЛЬ.
# Решение Шефа 21.07: работа резидента (что он реально ДЕЛАЕТ —
# чистит атлас, считает digest) — функция его РОЛИ (тип+порода+
# ядро+стадия, ЧЕРТЁЖ_ЕДИНИЦЫ.md §1.5.2), не маски-момента.
# «Резидент менеджер должен работать через роль, не через маску».
#
# ЗАКОН КАРТРИДЖА (дословно, ЛЕТОПИСЬ_ГРОНДХЕЙМА.md, 09.07):
#   Мозг слота (мозг.py) живёт РЯДОМ с промптом, в самом слоте.
#   Кабинет грузит его ДИНАМИЧЕСКИ (_slot_brain(цех, слот),
#   importlib по пути), не хардкодит имена модулей.
#
# ПОЧЕМУ ОТДЕЛЬНЫЙ ФАЙЛ, А НЕ ЕЩЁ ОДНА КОПИЯ: _slot_brain уже
# продублирован байт-в-байт в ЧЕТЫРЁХ местах (ui_torg.py,
# tester_express.py, hooks.py, council.py) — ровно та же болезнь,
# от которой лечит nositel.py для души («мостов девять, впишем в
# каждый мозг — через месяц одиннадцать копий, которые разъедутся»).
# Здесь — пятая, но КАНОНИЧЕСКАЯ копия, для НОВЫХ вызовов (действия
# резидентов). Старые четыре не трогаем сейчас — отдельный заход
# (свести все пять к одному источнику), не в этой правке.
#
# ПРАВИЛО (Шеф, 21.07): «только через резидент менеджер» — новые
# действия резидентов (проверить/почистить атлас и всё, что дальше
# родится) вызываются ИСКЛЮЧИТЕЛЬНО через vyzvat() этого файла.
# Никто не лезет в мозг слота напрямую в обход этой двери.
# `шесть·проверено·до·корня`
# ─────────────────────────────────────────────────────────────

import importlib.util
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent      # Биржа/
_REPO = _HERE.parent                          # корень репо
_BRAIN_CACHE: dict = {}


def _slot_brain(ceh_id: str, slot: str):
    """
    Мозг слота по (цех, слот). Нет файла — честная вакансия (None),
    не ошибка. Кэш на процесс (тот же приём, что в hooks.py/ui_torg.py/
    tester_express.py/council.py — байт-в-байт, каноническая копия).
    """
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


def vyzvat(ceh_id: str, slot: str, deistviye: str, **kwargs) -> dict:
    """
    ЕДИНАЯ ДВЕРЬ: позвать резидента (цех, слот) сделать ДЕЙСТВИЕ.

    Резидент делает действие через СВОЮ РОЛЬ — функция с именем
    `deistviye` должна быть определена прямо в его мозг.py (та же
    роль, что несёт СТОЛ+ЗНАНИЯ+ОПЫТ, Чертёж §1.5.2). Резидент-
    менеджер не подменяет и не дублирует эту логику — только находит
    дверь и стучится.

    Возвращает всегда dict — честно, без падений наружу:
      {"ok": True,  "result": <что вернула функция резидента>}
      {"ok": False, "error": "<человеческая причина>"}

    Причины отказа:
      - вакансия (мозг.py ещё не существует в этом слоте)
      - в мозге нет функции с именем deistviye
      - сама функция упала (исключение поймано, не роняет вызывающего)
    """
    brain = _slot_brain(ceh_id, slot)
    if brain is None:
        return {"ok": False,
                "error": f"вакансия: нет мозга в {ceh_id}/{slot}"}

    fn = getattr(brain, deistviye, None)
    if fn is None or not callable(fn):
        return {"ok": False,
                "error": f"{ceh_id}/{slot} не умеет «{deistviye}» "
                         f"(нет такой функции в его мозге)"}

    try:
        result = fn(**kwargs)
    except Exception as e:
        return {"ok": False,
                "error": f"{ceh_id}/{slot} упал на «{deistviye}»: {e}"}

    return {"ok": True, "result": result}
