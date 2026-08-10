# -*- coding: utf-8 -*-
# VYBOR_METKOY_V1
"""
ВЫБОР ВХОДА — метка жителя, а не свойство места.

ЗАКОН ЭТОГО ФАЙЛА
    Трейдер выбирает место входа сам, один раз, и носит выбор с собой.
    Хранится он там же, где всё нажитое — в метках жителя (дом/2_метки).
    Поэтому дома, в Академии и на Бирже это ОДИН человек с одной
    позицией, а не три догадки подряд.

    Здесь нет модели и нет UI. Чтение и запись.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
_KOREN = _BIRZHA.parent
for _p in (str(_BIRZHA), str(_KOREN / "жители")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

PATTERN = "выбор_входа"      # ключ метки — по нему её и находим
SLOVO = "ВЫБОР:"             # как трейдер объявляет выбор в разговоре


def _dvizhok_zhitelya(ceh: str, slot: str):
    """Движок того, кто сидит на месте. Пусто — честный None."""
    try:
        from cartridge_registry import resolve_para
        from dvizhok import Dvizhok
    except Exception:
        return None, None
    n = resolve_para(ceh, slot)
    if not n:
        return None, None
    try:
        return Dvizhok(Path(n["папка"])), n
    except Exception:
        return None, n


def chitat(ceh: str, slot: str) -> dict:
    """Последний выбор жителя этого места. Нет — пустой словарь."""
    d, _ = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return {}
    try:
        moi = [m for m in d.metki() if m.get("паттерн") == PATTERN]
    except Exception:
        return {}
    if not moi:
        return {}
    moi.sort(key=lambda x: str(x.get("когда", "")))
    return moi[-1]


def istoriya(ceh: str, slot: str) -> list:
    """Все выборы подряд — видно, передумывал ли и когда."""
    d, _ = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return []
    try:
        moi = [m for m in d.metki() if m.get("паттерн") == PATTERN]
    except Exception:
        return []
    moi.sort(key=lambda x: str(x.get("когда", "")))
    return moi


def zapisat(ceh: str, slot: str, tekst: str) -> tuple:
    """Положить выбор меткой. Старую не стираем: передумал — это тоже
    часть его жизни, и её видно."""
    tekst = (tekst or "").strip()
    if not tekst:
        return False, "пустой выбор"
    d, n = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return False, "на месте никого — некому выбирать"
    prezhniy = chitat(ceh, slot)
    if (prezhniy.get("текст") or "").strip() == tekst:
        return True, "тот же выбор, что и был"
    try:
        from datetime import datetime
        metki = d.metki()
        metki.append({"текст": tekst, "паттерн": PATTERN,
                      "откуда": "решение",
                      "когда": datetime.now().isoformat(timespec="seconds"),
                      "раз": 1})
        d._pisat_etazh(d._metki_path(), metki)
    except Exception as e:
        return False, str(e)
    kto = (n or {}).get("имя", "житель")
    if prezhniy:
        return True, f"{kto} передумал(а): {tekst}"
    return True, f"{kto} выбрал(а): {tekst}"


def poymat(ceh: str, slot: str, otvet: str) -> tuple:
    """Найти в ответе строку «ВЫБОР: …» и положить её меткой.

    Так же, как ловится запрос к архиву: житель объявляет словом, а не
    кнопкой. Ничего не нашли — молчим, это обычный разговор.
    """
    for stroka in (otvet or "").splitlines():
        s = stroka.strip()
        if s.upper().startswith(SLOVO):
            return zapisat(ceh, slot, s[len(SLOVO):].strip())
    return False, ""


def blok_dlya_prompta(ceh: str, slot: str) -> str:
    """Кусок в системную бумагу. Выбор подставляем ОТДЕЛЬНО, а не через
    окно свежих меток: окно маленькое (четыре), выбор из него вымывался
    бы, а он должен стоять всегда."""
    v = chitat(ceh, slot)
    if v:
        return ("\n\n=== ТВОЙ ВЫБОР ВХОДА ===\n"
                f"{v.get('текст','')}\n"
                f"(выбрано тобой {str(v.get('когда',''))[:16]})\n"
                "Это твоё решение, не приказ места. Работаешь по нему: не "
                "твоё место входа — пас, и так и скажи. Передумал(а) — "
                "скажи строкой «ВЫБОР: …», и это запишется как перемена.\n")
    return ("\n\n=== ТВОЙ ВЫБОР ВХОДА ===\n"
            "Своего входа ты ещё не выбрал(а). Три места входа лежат у тебя "
            "в знаниях, рядом, ни одно за тобой не закреплено. Выбери сам(а) "
            "и объяви строкой «ВЫБОР: <какое место входа> — <почему оно "
            "твоё>». Пока выбора нет, работать не по чему: пас честнее "
            "входа наугад.\n")
