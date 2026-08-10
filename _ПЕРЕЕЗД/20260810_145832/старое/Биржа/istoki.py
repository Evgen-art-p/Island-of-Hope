# -*- coding: utf-8 -*-
# ISTOKI_V_GNEZDAH_V1
"""
ИСТОКИ КОТИРОВОК — сменные, и все видны в гнёздах Маяка.

СЛОВО ШЕФА (07.08): «посмотри маяк и там в гнездо подключи МТ5, с
возможностью ещё подключать».

КАК БЫЛО
    Два крана, вбитых в код: `real` идёт в терминал, `tester` читает
    CSV. Третий источник добавить нельзя, не правя `feed_source.py`.
    И на доске Маяка про них ничего — город не знал, откуда течёт.

КАК СТАЛО
    Исток — просто файл в папке `Биржа/истоки/`. Положил файл — исток
    появился. Ничего нигде не правится: ни списков, ни кода.

    От файла требуется совсем немного:

        ИМЯ = "МТ5 терминал"          как показывать
        КЛЮЧ = "mt5"                   чем опознавать (латиницей)
        РОД = "инструмент"             для гнезда Маяка

        def bars(symbol, tf, count):   вернуть (список_баров, point)
            ...

        def zhiv() -> bool:            необязательно: на связи ли
            ...

    Всё. Больше от истока ничего не ждут.

ГНЁЗДА
    При первом обращении исток втыкается в гнездо Маяка и горит там
    постоянно — как канал или инструмент по закону гнёзд. Гнездо
    всеядно и род списком не проверяет, так что новый вид источника
    воткнётся сам.

    Гнездо ничего не маршрутизирует — оно доска: видно, что подключено
    и чем занято. Работает не гнездо, а то, что внутри.

ЧТО НЕ ЛОМАЕТСЯ
    `bars()` и `get_feed_mode()` остаются теми же по имени и форме —
    кто их зовёт, ничего не заметит. Имена `real` и `tester` остаются
    рабочими: старые кнопки кабинета продолжают переключать.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional, Tuple

_BIRZHA = Path(__file__).resolve().parent
_REPO = _BIRZHA.parent
ISTOKI_DIR = _BIRZHA / "истоки"

# Старые имена кранов — чтобы кабинет и trading_state не переучивать.
STARYE_IMENA = {"real": "mt5", "tester": "csv"}

_KESH: dict = {}


def _zagruzit(f: Path):
    """Открывает файл истока. Не открылся — молча мимо: сломанный
    исток не должен ронять остальные."""
    try:
        spec = importlib.util.spec_from_file_location(f"_istok_{f.stem}", f)
        if spec is None or spec.loader is None:
            return None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        if not hasattr(m, "bars"):
            return None
        return m
    except Exception as e:
        print(f"[ИСТОК] ⚠️  {f.name} не открылся: {e}")
        return None


def vse() -> dict:
    """Все истоки, что лежат в папке: {ключ: модуль}."""
    if _KESH:
        return _KESH
    if not ISTOKI_DIR.exists():
        return {}
    for f in sorted(ISTOKI_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        m = _zagruzit(f)
        if m is None:
            continue
        klyuch = (getattr(m, "КЛЮЧ", "") or f.stem).strip()
        _KESH[klyuch] = m
    return _KESH


def nayti(klyuch: str):
    """Исток по ключу. Понимает и старые имена (real/tester)."""
    klyuch = (klyuch or "").strip()
    klyuch = STARYE_IMENA.get(klyuch, klyuch)
    return vse().get(klyuch)


def spisok() -> list:
    """Что вообще есть — для кабинета и для проверки."""
    out = []
    for k, m in vse().items():
        try:
            zhiv = bool(m.zhiv()) if hasattr(m, "zhiv") else None
        except Exception:
            zhiv = False
        out.append({
            "ключ": k,
            "имя": getattr(m, "ИМЯ", k),
            "род": getattr(m, "РОД", "инструмент"),
            "жив": zhiv,
        })
    return out


def votknut_v_mayak(klyuch: str, chem_zanyat: str = "") -> str:
    """Втыкает исток в гнездо Маяка. Гнёзд нет — молчим, это не беда:
    город может работать и без доски."""
    m = nayti(klyuch)
    if m is None:
        return ""
    try:
        gorod = _REPO / "ГОРОД"
        if str(gorod) not in sys.path:
            sys.path.insert(0, str(gorod))
        import gnezda
        ok, soobsh = gnezda.votknut(
            rod=getattr(m, "РОД", "инструмент"),
            imya=getattr(m, "ИМЯ", klyuch),
            klyuch=f"istok_{klyuch}",
            chto=chem_zanyat or "поток котировок",
            postoyanno=True)
        return soobsh if ok else ""
    except Exception:
        return ""


def bars(klyuch: str, symbol: str, tf: str,
         count: int = 2000) -> Tuple[list, Optional[float]]:
    """Взять бары у истока и отметиться в гнезде.

    Отметка идёт ПОСЛЕ успешного ответа: доска Маяка должна показывать
    то, что правда работает, а не то, что мы попытались открыть.
    """
    m = nayti(klyuch)
    if m is None:
        return [], None
    b, point = m.bars(symbol, tf, count)
    if b:
        votknut_v_mayak(klyuch, f"{symbol} {tf}")
    return b, point
