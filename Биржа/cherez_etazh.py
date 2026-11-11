# -*- coding: utf-8 -*-
# CHEREZ_ETAZH_V1 / KOMPAS_OKNO_V1 / OZHIDANIE_V1
"""
ГЛАВНЫЙ ТРЕНД, МОМЕНТ И ОЖИДАНИЕ. Трейдер открывает этаж через один выше
рабочего (для дневки — месяц), смотрит всё окно и называет главный тренд,
момент и — при ENTER и HOLD — что ждёт от сделки: быстро или долго. На вход,
выход и деньги не влияет. Судья НИЧЕГО НЕ СЧИТАЕТ: в отчёте только его
ответы, то, менял ли он их на одной и той же картинке (одна и та же
последняя закрытая свеча этажа), и какое «ожидание» он называет при каком
«моменте». Правильно или нет — смотрит Шеф по кадрам и по сделкам.
"""
from __future__ import annotations

import bisect
import sys as _sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

SLOTY = ("A08",)
LESENKA = ("H1", "H4", "D1", "W1", "MN1")
_LENTY: dict = {}


def etazh_cherez(tf: str) -> str:
    tf = str(tf or "").upper()
    if tf not in LESENKA:
        return ""
    i = LESENKA.index(tf) + 2
    return LESENKA[i] if i < len(LESENKA) else ""


def _vremya(s):
    s = str(s or "").strip()
    for f, n in (("%Y.%m.%d %H:%M", 16), ("%Y.%m.%d", 10)):
        try:
            return datetime.strptime(s[:n], f)
        except ValueError:
            pass
    return None


def _norm_tren(s) -> str:
    s = str(s or "").strip().lower()
    if not s:
        return ""
    if "нет тренд" in s or "внутр" in s or "боков" in s:
        return "нет тренда"
    if "вверх" in s or "up" in s:
        return "вверх"
    if "вниз" in s or "down" in s:
        return "вниз"
    return "не знаю"


def _norm_moment(s) -> str:
    s = str(s or "").strip().lower()
    if not s:
        return ""
    if "откат" in s or "против" in s:
        return "откат против тренда"
    if "по тренд" in s or "по ходу" in s or "импульс" in s:
        return "по тренду"
    return "не знаю"


def _norm_ozh(s) -> str:
    s = str(s or "").strip().lower()
    if not s:
        return ""
    if "быстр" in s or "корот" in s:
        return "быстро"
    if "долг" in s or "дольше" in s:
        return "долго"
    return "не знаю"


def _daty(sym: str, tf: str):
    kl = (sym, tf)
    if kl not in _LENTY:
        try:
            import istoriya
            bs = istoriya._vse_bary(sym, tf) or []
        except Exception:
            bs = []
        _LENTY[kl] = [(_vremya(b.get("date")), str(b.get("date") or "")[:10])
                      for b in bs] or None
    return _LENTY[kl]


def kartinka(sym: str, tf_mesta: str, kogda: str) -> str:
    """Ключ картинки: дата последней ЗАКРЫТОЙ свечи этажа через один.
    Пока она та же — картинка та же. Ничего не оценивает."""
    tf = etazh_cherez(tf_mesta)
    L = _daty(sym, tf) if tf else None
    t = _vremya(kogda)
    if not L or t is None:
        return ""
    ds = [x[0] for x in L]
    i = bisect.bisect_right(ds, t) - 2
    return L[i][1] if i >= 0 else ""


def svodka(mesta: list) -> list:
    nashi = [(i, m) for i, m in enumerate(mesta or [], 1)
             if str(m.get("слот") or "") in SLOTY]
    if not nashi:
        return []
    strok = []
    po_kart = defaultdict(lambda: ([], []))
    perekres = Counter()
    nazv = 0
    for i, m in nashi:
        o = m.get("через_этаж") or {}
        tr = _norm_tren(o.get("через_этаж_ход"))
        mo = _norm_moment(o.get("через_этаж"))
        oz = _norm_ozh(o.get("ожидание"))
        tf = etazh_cherez(str(m.get("этаж") or ""))
        try:
            k = kartinka(str(m.get("инструмент") or ""), str(m.get("этаж") or ""),
                         m.get("когда_на_рынке"))
        except Exception:
            k = ""
        if tr or mo or oz:
            nazv += 1
            if k:
                if tr and tr != "не знаю":
                    po_kart[(tf, k)][0].append(tr)
                if mo and mo != "не знаю":
                    po_kart[(tf, k)][1].append(mo)
        if mo and oz:
            perekres[(mo, oz)] += 1
        strok.append((i, m.get("когда_на_рынке", ""), m.get("действие", ""),
                      tf or "—", k or "—", tr or "—", mo or "—", oz or "—"))
    men_tr = {kk: v[0] for kk, v in po_kart.items() if len(set(v[0])) > 1}
    men_mo = {kk: v[1] for kk, v in po_kart.items() if len(set(v[1])) > 1}
    s = ["## Тренд, момент, ожидание — его ответы (на вход и выход не влияет)", "",
         "Он открывает этаж через один выше рабочего (для дневки — месяц), "
         "смотрит всё окно и называет главный тренд и момент; при ENTER и "
         "HOLD ещё и ожидание — быстро (ход короткий, откат) или долго "
         "(разворот или продолжение тренда). Город ничего не считает и не "
         "судит: тут только ответы, то, менял ли он их на одной и той же "
         "картинке, и какое ожидание при каком моменте. Правильно или нет — "
         "по кадрам и по сделкам.", "",
         f"Мест: **{len(nashi)}** · назвал: **{nazv}** · картинок: "
         f"**{len(po_kart)}** · менял тренд на: **{len(men_tr)}** · менял "
         f"момент на: **{len(men_mo)}**", "",
         "| # | когда | слово | этаж | свеча | тренд | момент | ждёт |",
         "|---|---|---|---|---|---|---|---|"]
    for r in strok:
        s.append("| " + " | ".join(str(x) for x in r) + " |")
    if perekres:
        s += ["", "Какое ожидание при каком моменте:", "",
              "| момент | быстро | долго | не знаю |", "|---|---|---|---|"]
        for mo in ("по тренду", "откат против тренда", "не знаю"):
            if any((mo, o) in perekres for o in ("быстро", "долго", "не знаю")):
                s.append(f"| {mo} | {perekres[(mo, 'быстро')]} | "
                         f"{perekres[(mo, 'долго')]} | {perekres[(mo, 'не знаю')]} |")
    if men_tr or men_mo:
        s += ["", "Где менял ответ на одной картинке:"]
        for (tf, k), v in sorted(men_tr.items()):
            s.append(f"- {tf} {k}, тренд: {' → '.join(v)}")
        for (tf, k), v in sorted(men_mo.items()):
            s.append(f"- {tf} {k}, момент: {' → '.join(v)}")
    s.append("")
    return s


# CHEREZ_ETAZH_V1 - marker
# KOMPAS_OKNO_V1 - marker
# OZHIDANIE_V1 - marker
