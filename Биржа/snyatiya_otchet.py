# -*- coding: utf-8 -*-
# MESYAC_ZAYAVKA_V1 — два раздела отчёта: «Месяц: дивер» и «Снятые заявки»
"""
Отчёт ЗАПИСЫВАЕТ, а не судит. На вход и выход не влияет.

1. МЕСЯЦ: ДИВЕР — ЕГО СЛОВА. жителя просят первой фразой сказать «Месяц: дивер
   есть» или «Месяц: дивера нет». Здесь — что он сказал на каждом месте и менял
   ли ответ на одной и той же картинке месяца (последняя закрытая свеча).
2. СНЯТЫЕ ЗАЯВКИ — ЧТО БЫЛО БЫ. Для каждого CANCEL берём последнюю его заявку
   (цена и стоп из ENTER) и идём по барам после снятия: сработала бы? выбил бы
   стоп? сколько R прошла бы цена? Смотрим не дальше SKOLKO баров. Мерка, не
   сделка: ни выход, ни ведение здесь не считаются.
"""
from __future__ import annotations

import re

SLOTY = ("A08",)
SKOLKO = 140      # сколько баров смотрим после снятия

_EST = re.compile(r"месяц[^.\n]{0,40}?(дивер\s+есть|есть\s+дивер)", re.I)
_NET = re.compile(r"месяц[^.\n]{0,40}?(дивера\s+нет|нет\s+дивера|дивер\s+нет)", re.I)


def _mes_slovo(skazal: str) -> str:
    s = str(skazal or "")
    e, n = _EST.search(s), _NET.search(s)
    if e and n:
        return "есть" if e.start() < n.start() else "нет"
    if e:
        return "есть"
    if n:
        return "нет"
    return ""


def _mesyac(mesta: list) -> list:
    nashi = [(i, m) for i, m in enumerate(mesta, 1)
             if str(m.get("слот") or "") in SLOTY]
    if not nashi:
        return []
    try:
        import cherez_etazh as _che
    except Exception:
        _che = None
    stroki, po_kart = [], {}
    est = net = molchal = 0
    for i, m in nashi:
        sl = _mes_slovo(m.get("сказал"))
        k = ""
        if _che:
            try:
                k = _che.kartinka(str(m.get("инструмент") or ""),
                                  str(m.get("этаж") or ""), m.get("когда_на_рынке"))
            except Exception:
                k = ""
        if sl == "есть":
            est += 1
        elif sl == "нет":
            net += 1
        else:
            molchal += 1
        if sl and k:
            po_kart.setdefault(k, []).append(sl)
        stroki.append(f"| {i} | {m.get('когда_на_рынке', '')} | "
                      f"{m.get('действие', '') or '—'} | {k or '—'} | "
                      f"{sl or 'не назвал'} |")
    prygal = {k: v for k, v in po_kart.items() if len(set(v)) > 1}
    out = ["## Месяц: дивер — его слова (на вход и выход не влияет)", "",
           "Его просят первой фразой сказать «Месяц: дивер есть» или «Месяц: дивера "
           "нет». Здесь — что он сказал и менял ли ответ на одной и той же картинке "
           "месяца. Прав он или нет — по кадрам.", "",
           f"Мест: **{len(nashi)}** · «есть» — {est} · «нет» — {net} · не назвал — "
           f"{molchal} · картинок, где ответ прыгал: **{len(prygal)}**", "",
           "| # | когда | слово | картинка месяца | дивер на месяце |",
           "|---|---|---|---|---|"] + stroki
    if prygal:
        out += ["", "Где прыгал ответ на одной картинке:"]
        for k, v in sorted(prygal.items()):
            out.append(f"- {k}: {' → '.join(v)}")
    out.append("")
    return out


def _bary(sym: str, tf: str) -> list:
    try:
        import istoriya
        return istoriya._vse_bary(sym, tf) or []
    except Exception:
        return []


def _vr(s):
    try:
        import istoriya
        return istoriya.kak_vremya(str(s or "")[:16]) or istoriya.kak_vremya(str(s or "")[:10])
    except Exception:
        return None


def _chto_bylo_by(sym, tf, kogda, vh, st):
    """Идём по барам ПОСЛЕ снятия. Возвращает строку-итог и R (или None)."""
    bary = _bary(sym, tf)
    t0 = _vr(kogda)
    if not bary or t0 is None:
        return "баров нет — не посчитать", None
    dlin = st < vh
    risk = abs(vh - st)
    if not risk:
        return "риск ноль — не посчитать", None
    posle = [b for b in bary if (_vr(b.get("date")) or t0) > t0][:SKOLKO]
    if not posle:
        return "после снятия баров нет", None
    vzyal = None
    luchshe = 0.0
    for b in posle:
        h, l = float(b["high"]), float(b["low"])
        d = str(b.get("date") or "")[:16]
        if vzyal is None:
            za_stop = (l <= st) if dlin else (h >= st)
            dostal = (h >= vh) if dlin else (l <= vh)
            if za_stop and not dostal:
                return (f"цена ушла за стоп {d}, не взяв заявку — снял "
                        f"по делу, сценарий сломан"), 0.0
            if dostal:
                vzyal = d
                if za_stop:    # в одном баре и взяла, и выбила — считаем стоп
                    return f"сработала бы {d} и в тот же бар выбил бы стоп", -1.0
                luchshe = max(luchshe, ((h - vh) if dlin else (vh - l)) / risk)
            continue
        if (l <= st) if dlin else (h >= st):
            return (f"сработала бы {vzyal}, стоп выбил бы {d}; лучшее по дороге "
                    f"+{luchshe:.2f}R"), luchshe
        luchshe = max(luchshe, ((h - vh) if dlin else (vh - l)) / risk)
    if vzyal is None:
        return f"за {len(posle)} баров не сработала бы", 0.0
    return (f"сработала бы {vzyal}; за {len(posle)} баров стоп не тронут, "
            f"лучшее +{luchshe:.2f}R"), luchshe


def _snyatiya(mesta: list) -> list:
    poslednyaya = {}
    stroki = []
    for i, m in enumerate(mesta, 1):
        if str(m.get("слот") or "") not in SLOTY:
            continue
        para = (str(m.get("инструмент") or ""), str(m.get("этаж") or ""))
        d = str(m.get("действие") or "").upper()
        if d == "ENTER" and m.get("цена_входа") and m.get("стоп_входа"):
            poslednyaya[para] = (i, m)
            continue
        if d != "CANCEL":
            continue
        z = poslednyaya.get(para)
        if not z:
            stroki.append(f"| {i} | {m.get('когда_на_рынке', '')} | — | — | "
                          f"заявку снятия не нашёл |")
            continue
        j, e = z
        try:
            vh, st = float(e["цена_входа"]), float(e["стоп_входа"])
        except (TypeError, ValueError):
            continue
        itog, _r = _chto_bylo_by(para[0], para[1], m.get("когда_на_рынке"), vh, st)
        stroki.append(f"| {i} | {m.get('когда_на_рынке', '')} | "
                      f"{'LONG' if st < vh else 'SHORT'} {vh} / стоп {st} "
                      f"(место {j}) | {(m.get('сказал') or '')[:90]} | {itog} |")
    if not stroki:
        return []
    return ["## Снятые заявки — что было бы (мерка, не сделка)", "",
            f"Для каждой снятой заявки — идём по барам после снятия (не дальше "
            f"{SKOLKO}): сработала бы, выбил бы стоп, сколько R прошла бы цена до "
            f"стопа. Ведение и выход не считаются.", "",
            "| # | снял | заявка | его слова | что было бы |",
            "|---|---|---|---|---|"] + stroki + [""]


def svodka(mesta: list) -> list:
    mesta = mesta or []
    out = []
    # CHISTYY_OTCHYOT_V1: раздел «Месяц: дивер» снят — эту фразу у жителя больше
    # не просят (14.10, история хода месяца); функция _mesyac осталась в файле.
    try:
        out += _snyatiya(mesta)
    except Exception as e:
        out += [f"_(раздел «Снятые заявки» не сложился: {e})_", ""]
    return out


# MESYAC_ZAYAVKA_V1 - marker

# CHISTYY_OTCHYOT_V1 - marker
