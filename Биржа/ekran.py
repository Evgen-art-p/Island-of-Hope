# -*- coding: utf-8 -*-
# EDINYY_VYBOR_V1
"""ЭКРАН — единственное место, где живёт выбор города.

Один выбор на всех: инструмент и этаж. Кто последний выбрал — тот и
переписал. Экран показывает его, трейдер по нему работает, вахта его
сторожит, кадр по нему рисуется.

Своих копий больше никто не держит — в этом весь смысл. Если этаж
снова заведётся в двух местах, они разойдутся, и оба будут правы
(вечер 09.09, проверено дорого).

Лежит на диске: переживает перезапуск. Пусто бывает ровно один раз —
до первого выбора.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

_FAYL = Path(__file__).resolve().parent / "данные" / "vybor_ekrana.json"

_PUSTO = {"инструмент": "", "этаж": "", "кто": "", "когда": "",
          "почему": ""}


def _prochitat() -> dict:
    try:
        if _FAYL.is_file():
            d = json.loads(_FAYL.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                out = dict(_PUSTO)
                out.update({k: v for k, v in d.items() if k in out})
                return out
    except Exception as e:
        print(f"[ЭКРАН] не прочитался ({e}) — считаю пустым")
    return dict(_PUSTO)


def vzyat() -> dict:
    """Что сейчас выбрано. Всегда словарь, пустой — значит не выбрано."""
    return _prochitat()


def para() -> tuple:
    """(инструмент, этаж) — коротко, для тех, кому нужна только пара."""
    v = _prochitat()
    return v["инструмент"], v["этаж"]


def est() -> bool:
    v = _prochitat()
    return bool(v["инструмент"] and v["этаж"])


def postavit(instrument: str, etazh: str, kto: str = "",
             pochemu: str = "") -> tuple:
    """Поставить выбор. Возвращает (получилось, что сказать вслух).

    Закон Рычага: у смены выбора есть след — кто повернул, когда и
    зачем. Переезд двигает вахту, значит меняет, когда человека вообще
    будут будить; такое решение должно быть видно и разбираемо.
    """
    instrument = (instrument or "").strip().upper()
    etazh = (etazh or "").strip().upper()
    if not instrument or not etazh:
        return False, "выбор пустой — нужен и инструмент, и этаж"

    bylo = _prochitat()
    if bylo["инструмент"] == instrument and bylo["этаж"] == etazh:
        return True, "тот же выбор, что и был"

    novyy = {"инструмент": instrument, "этаж": etazh,
             "кто": (kto or "").strip(),
             "когда": datetime.now().isoformat(timespec="seconds"),
             "почему": (pochemu or "").strip()}
    try:
        _FAYL.parent.mkdir(parents=True, exist_ok=True)
        vremenno = _FAYL.with_suffix(".json.tmp")
        vremenno.write_text(
            json.dumps(novyy, ensure_ascii=False, indent=2),
            encoding="utf-8")
        vremenno.replace(_FAYL)
    except Exception as e:
        return False, f"выбор не записался: {e}"

    otkuda = f" ({novyy['кто']})" if novyy["кто"] else ""
    prichina = f" — {novyy['почему']}" if novyy["почему"] else ""
    print(f"[ЭКРАН] ▣ выбор: {instrument} {etazh}{otkuda}{prichina}")
    return True, f"выбор: {instrument} {etazh}"


def slovami() -> str:
    """Строка для человека: что стоит и с чьей руки."""
    v = _prochitat()
    if not (v["инструмент"] and v["этаж"]):
        return "выбор не поставлен"
    kto = f" · поставил {v['кто']}" if v["кто"] else ""
    return f"{v['инструмент']} {v['этаж']}{kto}"
