# -*- coding: utf-8 -*-
# GOROD_KLYUCH_V1 · KLYUCH_V_SLEDAH_V1 — ключ клетки
"""
КЛЮЧ · одно место на весь город

Ключ клетки — ОТПЕЧАТОК ПЕЧАТИ СОЗДАТЕЛЯ (_Creator_Seal_Hash из
паспорта). Посчитан один раз, при рождении, из печати — и не
пересчитывается никогда. Имя может повториться (Илья может быть
три), номер могут переставить — а печать у каждого своя.

ЧТО КЛЮЧ ДЕЛАЕТ: находит. Назови ключ — получишь, кто это.
ЧЕГО НЕ ДЕЛАЕТ: не хранит ничего, ничего не открывает и не пускает.
Что кому можно — решают веса и области, не ключ.

И отдельно, закон из реестра картриджей, он в силе: ключ отвечает
на вопрос «КТО ЭТО» и никогда на «кем он работает». Роль по-прежнему
решает пара и маска.

    import klyuch
    klyuch.klyuch_zhitelya("Илья")   -> "bc9dd782..."
    klyuch.kto("bc9dd782...")        -> "Илья"
    klyuch.pasport("bc9dd782...")    -> паспорт словарём
    klyuch.dom("bc9dd782...")        -> папка жителя
    klyuch.vse()                     -> [{имя, ключ, id}, ...]

Список берётся с диска при каждом обращении (Закон Картриджа —
реестра в коде не держим). Кто завёлся в ковчеге — тот и найдётся.

`шесть·проверено·до·корня`
"""
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent      # ГОРОД/
_REPO = _HERE.parent
KOVCHEG = _REPO / "GRONDHEIM_CITY" / "жители" / "ковчег"
KATALOG = _REPO / "00_REGISTRY_NFT" / "catalog.json"

POLE_KLYUCHA = "_Creator_Seal_Hash"


def _chitat(p: Path):
    for kod in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return json.loads(p.read_text(encoding=kod))
        except Exception:
            continue
    return None


def _zhiteli() -> list:
    """Все жители ковчега с их ключами. Нет паспорта — нет жителя."""
    out = []
    if not KOVCHEG.exists():
        return out
    for d in sorted(KOVCHEG.iterdir()):
        if not d.is_dir():
            continue
        p = d / "passport.json"
        if not p.exists():
            continue
        pasp = _chitat(p) or {}
        k = pasp.get(POLE_KLYUCHA, "")
        if not k:
            continue
        out.append({
            "имя": pasp.get("Official_Name") or d.name,
            "папка": d.name,
            "ключ": k,
            "id": pasp.get("ID_Object", ""),
            "дом": d,
        })
    return out


def vse() -> list:
    """Список всех: имя, ключ, id. Без домов — для показа."""
    return [{"имя": z["имя"], "ключ": z["ключ"], "id": z["id"]}
            for z in _zhiteli()]


def klyuch_zhitelya(imya: str) -> str:
    """Ключ по имени. Нет такого — пустая строка, честно.

    Имя пока однозначно (все девятнадцать разные). Заведётся второй
    с тем же именем — эта функция станет неоднозначной, и тогда
    звать нужно будет уже по ключу. Здесь это не прячется.
    """
    if not imya:
        return ""
    for z in _zhiteli():
        if imya in (z["имя"], z["папка"]):
            return z["ключ"]
    return ""


def odnoimenniki(imya: str) -> list:
    """Все, кто носит это имя. Больше одного — имя перестало быть
    адресом, зовите по ключу."""
    return [z["ключ"] for z in _zhiteli()
            if imya in (z["имя"], z["папка"])]


def kto(k: str) -> str:
    """Имя по ключу. Нет такого ключа — пустая строка."""
    if not k:
        return ""
    for z in _zhiteli():
        if z["ключ"] == k:
            return z["имя"]
    return ""


def dom(k: str):
    """Папка жителя по ключу. Нет — None."""
    for z in _zhiteli():
        if z["ключ"] == k:
            return z["дом"]
    return None


def pasport(k: str) -> dict:
    """Паспорт по ключу. Нет — пустой словарь."""
    d = dom(k)
    if d is None:
        return {}
    return _chitat(d / "passport.json") or {}


def mesta() -> list:
    """Места города из каталога: у них тоже есть ключи."""
    kat = _chitat(KATALOG)
    if not isinstance(kat, list):
        return []
    return [{"имя": x.get("Official_Name", ""),
             "ключ": x.get(POLE_KLYUCHA, ""),
             "id": x.get("ID_Object", "")}
            for x in kat if x.get("Object_Type_Class") == "location"]


if __name__ == "__main__":
    print("ЖИТЕЛИ:")
    for z in vse():
        print(f"  {z['имя']:12} {z['ключ'][:16]}  {z['id']}")
    print()
    print("МЕСТА:")
    for m in mesta():
        print(f"  {m['имя']:24} {m['ключ'][:16]}  {m['id']}")
