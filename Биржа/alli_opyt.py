# -*- coding: utf-8 -*-
# ALLIGATOR_OPYT_V1
"""
АЛЛИГАТОР — опыт на A08: трейдер называет, где он сейчас по Аллигатору,
город рядом пишет, где цена по линиям на самом деле. На вход не влияет.

СЛОВО ШЕФА (05.10)
    «Если цена выше линий и растёт — тренд вверх, зеркально вниз.»
    «Если цена от линий — импульс, если к линиям — откат. Это база.»
    «Пока никаких связок — пусть называют, где они сейчас по аллигатору.»

КАК СЧИТАЕТ ГОРОД (только факт по линиям, со сдвигом, как на кадре)
    направление — закрытие выше всех трёх линий → вверх; ниже всех →
                  вниз; иначе → внутри линий.
    движение    — расстояние закрытия до Зубов сейчас больше, чем три
                  бара назад → импульс (цена уходит от линий); меньше →
                  откат (идёт к линиям).
"""
from __future__ import annotations

import bisect
import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

SLOTY = ()   # BEZ_ALLI_SVOEGO_V1: на A08 убран (07.10), импульс/откат — через этаж
NAZAD = 3
_LENTY: dict = {}


def _norm_daty(d) -> str:
    d = str(d or "").strip()
    return d + " 00:00" if len(d) == 10 else d


def _norm_napr(s) -> str:
    s = str(s or "").strip().lower()
    if not s:
        return ""
    if "внутр" in s or "между" in s or "пасть" in s or "нет" in s:
        return "внутри линий"
    if "вверх" in s or "выше" in s or "up" in s:
        return "вверх"
    if "вниз" in s or "ниже" in s or "down" in s:
        return "вниз"
    return "?"


def _norm_dvizh(s) -> str:
    s = str(s or "").strip().lower()
    if "импульс" in s or "от лини" in s:
        return "импульс"
    if "откат" in s or "к лини" in s:
        return "откат"
    return "?" if s else ""


def _lenta(sym: str, tf: str):
    kl = (sym, tf)
    if kl in _LENTY:
        return _LENTY[kl]
    bs = []
    try:
        import istoriya
        bs = istoriya._vse_bary(sym, tf) or []
    except Exception:
        bs = []
    if not bs:
        _LENTY[kl] = None
        return None
    from williams_core import _smma_series, _shifted_series
    med = [(b["high"] + b["low"]) / 2 for b in bs]
    jaw = _shifted_series(_smma_series(med, 13), 8)
    teeth = _shifted_series(_smma_series(med, 8), 5)
    lips = _shifted_series(_smma_series(med, 5), 3)
    _LENTY[kl] = (bs, [_norm_daty(b.get("date")) for b in bs], jaw, teeth, lips)
    return _LENTY[kl]


def gorod(sym: str, tf: str, kogda: str) -> dict:
    L = _lenta(sym, tf)
    if not L:
        return {}
    bs, daty, jaw, teeth, lips = L
    i = bisect.bisect_right(daty, _norm_daty(kogda)) - 1
    if i < NAZAD or i >= len(bs):
        return {}
    j, t, l = jaw[i], teeth[i], lips[i]
    t0 = teeth[i - NAZAD]
    if None in (j, t, l, t0):
        return {}
    c = bs[i]["close"]
    if c > max(j, t, l):
        napr = "вверх"
    elif c < min(j, t, l):
        napr = "вниз"
    else:
        napr = "внутри линий"
    dvizh = ("импульс" if abs(c - t) > abs(bs[i - NAZAD]["close"] - t0)
             else "откат")
    return {"направление": napr, "движение": dvizh}


def sudit_mesto(m: dict) -> dict:
    a = m.get("аллигатор") or {}
    ee_n = _norm_napr(a.get("аллигатор"))
    ee_d = _norm_dvizh(a.get("движение"))
    try:
        g = gorod(str(m.get("инструмент") or ""), str(m.get("этаж") or ""),
                  m.get("когда_на_рынке"))
    except Exception:
        g = {}
    return {"её_направление": ee_n or "—", "её_движение": ee_d or "—",
            "город_направление": g.get("направление", "—"),
            "город_движение": g.get("движение", "—"),
            "назвала": bool(ee_n or ee_d)}


def svodka(mesta: list) -> list:
    nashi = [(i, m) for i, m in enumerate(mesta or [], 1)
             if str(m.get("слот") or "") in SLOTY]
    if not nashi:
        return []
    rez = [(i, m, sudit_mesto(m)) for i, m in nashi]
    nazv = [x for x in rez if x[2]["назвала"]]

    def _sov(x, k):
        e, g = x[2][f"её_{k}"], x[2][f"город_{k}"]
        return e not in ("—", "?") and g != "—" and e == g

    sn = sum(1 for x in nazv if _sov(x, "направление"))
    sd = sum(1 for x in nazv if _sov(x, "движение"))
    s = ["## Аллигатор — опыт (на вход не влияет)", "",
         "Она называет, где она сейчас по Аллигатору; город рядом пишет, "
         "где цена по линиям на самом деле (линии со сдвигом, как на кадре). "
         "Направление: закрытие выше всех линий — вверх, ниже — вниз, иначе "
         "внутри. Движение: от Зубов дальше, чем три бара назад, — импульс, "
         "ближе — откат.", "",
         f"Мест: **{len(nashi)}** · назвала: **{len(nazv)}** · направление "
         f"совпало с городом: **{sn}** · движение совпало: **{sd}**", "",
         "| # | когда | пара | её направление | город | её движение | город |",
         "|---|---|---|---|---|---|---|"]
    for i, m, r in rez:
        def _z(k):
            e, g = r[f"её_{k}"], r[f"город_{k}"]
            mark = "" if e in ("—", "?") or g == "—" else (" ✓" if e == g else " ✗")
            return f"{e} | {g}{mark}"
        s.append(f"| {i} | {m.get('когда_на_рынке', '')} | "
                 f"{m.get('инструмент', '')} {m.get('этаж', '')} | "
                 f"{_z('направление')} | {_z('движение')} |")
    s.append("")
    return s


# ALLIGATOR_OPYT_V1 - marker
