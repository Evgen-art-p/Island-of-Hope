# -*- coding: utf-8 -*-
# UCHEBNIK_DISCIPLINY_V1
"""
УЧЕБНИК — картинки Академии, по всем дисциплинам.

СЛОВА ШЕФА
    «Есть же в Академии архив с картинками, накидать по темам — и
    пусть по запросу получит в работе. Она там с глазами.»
    «Только эти рисунки? В будущем, если материал добавится?»

ЗАКОН ЭТОГО ФАЙЛА
    СКАНИРУЕМ, А НЕ ПОМНИМ. Списка книг здесь нет и не будет: положил
    папку с картинками в дисциплины — она доступна в тот же миг, без
    единой правки. Тот же Закон Картриджа, что у цехов и истоков.

    ТЕМА — ЭТО ДИСЦИПЛИНА, из пути: раздел/предмет. Ярлыки на каждую
    картинку не вешаем: их пришлось бы проставлять руками сейчас и
    для каждой новой книги потом.

    Ищем по АВТОРСКИМ подписям из описи, если она есть. Своих
    толкований не добавляем: показали рисунок — дальше дело смотрящего.
"""
from __future__ import annotations

import re
from pathlib import Path

_KOREN = Path(__file__).resolve().parent.parent
_DISCIPLINY = _KOREN / "GRONDHEIM_CITY" / "Академия" / "дисциплины"
_RASSHIRENIYA = (".jpeg", ".jpg", ".png", ".gif", ".webp")


def _opis_ryadom(papka: Path) -> dict:
    """{имя файла: (глава, подпись)} из ОПИСЬ.md, если она есть.

    Опись необязательна: без неё картинки всё равно видны, просто
    ищутся по имени файла и папке. Новую книгу можно положить без
    описи и пользоваться сразу.
    """
    out, glava = {}, ""
    for imya in ("ОПИСЬ.md", "опись.md", "ОПИСЬ.txt"):
        f = papka / imya
        if not f.exists():
            continue
        for s in f.read_text(encoding="utf-8", errors="replace").splitlines():
            s = s.strip()
            if s.startswith("## "):
                glava = s[3:].strip()
                continue
            m = re.match(r"^-\s+`([^`]+)`\s*(?:\([^)]*\))?\s*—?\s*(.*)$", s)
            if m:
                out[m.group(1).strip()] = (glava, m.group(2).strip())
        break
    return out


def _tema_iz_puti(p: Path) -> tuple:
    """(раздел, предмет) — из того, КУДА положили. Например
    финансы/торговый_хаос или общие_дисциплины/беседы_о_смыслах."""
    try:
        chasti = p.relative_to(_DISCIPLINY).parts
    except Exception:
        return ("", "")
    razdel = chasti[0] if len(chasti) > 0 else ""
    predmet = chasti[1] if len(chasti) > 1 else ""
    return (razdel, predmet)


def vse_kartinki() -> list:
    """[(путь, раздел, предмет, глава, подпись)] — скан всего дерева."""
    if not _DISCIPLINY.exists():
        return []
    opisi: dict = {}
    out = []
    for p in sorted(_DISCIPLINY.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in _RASSHIRENIYA:
            continue
        # опись ищем в папке картинок и на две ступени выше
        podpis, glava = "", ""
        for kandidat in (p.parent, p.parent.parent, p.parent.parent.parent):
            if kandidat in opisi:
                o = opisi[kandidat]
            else:
                o = _opis_ryadom(kandidat)
                opisi[kandidat] = o
            if p.name in o:
                glava, podpis = o[p.name]
                break
        razdel, predmet = _tema_iz_puti(p)
        out.append((p, razdel, predmet, glava, podpis))
    return out


def temy() -> str:
    """Что вообще есть в Академии — по дисциплинам."""
    vse = vse_kartinki()
    if not vse:
        return "картинок в дисциплинах пока нет"
    po_temam: dict = {}
    for _p, razdel, predmet, _g, _po in vse:
        klyuch = f"{razdel} / {predmet}" if predmet else (razdel or "прочее")
        po_temam[klyuch] = po_temam.get(klyuch, 0) + 1
    return "\n".join(f"  · {t} — {n} рисунк(ов)"
                      for t, n in sorted(po_temam.items()))


def nayti(o_chyom: str, skolko: int = 1, tema: str = "") -> list:
    """[(путь, тема, глава, подпись)] по словам запроса.

    tema — сузить до дисциплины («психология», «финансы», имя книги).
    Пусто — ищем везде.
    """
    zapros = (o_chyom or "").strip().lower()
    tema = (tema or "").strip().lower()
    slova = [w for w in re.split(r"[^\wа-яё]+", zapros) if len(w) > 3]
    if not slova and zapros:
        slova = [zapros]

    ocenki = []
    for p, razdel, predmet, glava, podpis in vse_kartinki():
        if tema and tema not in f"{razdel} {predmet}".lower():
            continue
        if not slova:
            ocenki.append((0, p, razdel, predmet, glava, podpis))
            continue
        seno = f"{podpis} {glava} {p.name} {razdel} {predmet}".lower()
        ochki = sum(1 for w in slova if w in seno)
        # авторская подпись весит больше имени файла
        ochki += sum(1 for w in slova if w in podpis.lower())
        if ochki:
            ocenki.append((ochki, p, razdel, predmet, glava, podpis))

    ocenki.sort(key=lambda x: -x[0])
    out = []
    for _o, p, razdel, predmet, glava, podpis in ocenki[:skolko]:
        t = f"{razdel} / {predmet}" if predmet else (razdel or "")
        out.append((p, t, glava, podpis))
    return out


# UCHEBNIK_DISCIPLINY_V1 - marker
