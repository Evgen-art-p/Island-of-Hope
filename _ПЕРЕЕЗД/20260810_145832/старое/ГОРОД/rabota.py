# -*- coding: utf-8 -*-
# STANDART_RABOTY_V1
"""
РАБОТА — единый стандарт мест города.

ЗАКОН ЭТОГО ФАЙЛА
    Место называется ПОСТ, и реестр один: GRONDHEIM_CITY/посты/.
    Пост — полноценный бланк, а не строчка. Кто сидит — написано в
    посте; у жителя в паспорте отметка, чтобы он знал о работе где
    угодно. Разошлись — правда за постом.

    Списков мест здесь нет и не будет: места СКАНИРУЮТСЯ (Закон
    Картриджа — никто не ведёт списков). Появился цех — появились его
    места. Удалил папку — места ушли.

    Четыре руки: zavesti · prinyat · uvolit · snesti.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_GOROD = Path(__file__).resolve().parent
KOREN = _GOROD.parent
CITY = KOREN / "GRONDHEIM_CITY"
POSTY = CITY / "посты"
KOVCHEG = CITY / "жители" / "ковчег"
STUDIA_PUT = _GOROD / "студия_путь.txt"

POLYA_BLANKA = ("название", "локация", "где", "квартал", "цех", "слот",
                "чем_занят", "обязанности", "судья", "требования",
                "условия", "движок")


def _teper() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _chitat(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _pisat(p: Path, d) -> bool:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return True
    except Exception:
        return False


def put_posta(post_id: str) -> Path:
    return POSTY / post_id / "пост.json"


def blank(post_id: str, polya: dict | None = None) -> dict:
    d = {
        "id": post_id,
        "название": "",
        # LOKACIYA_DAYOT_MESTA_V1: место даёт локация, и она у места одна.
        "локация": "",
        "где": "",
        "квартал": "",
        "цех": "",
        "слот": "",
        "чем_занят": "",
        "обязанности": [],
        "судья": "",
        "требования": "",
        "условия": "",
        "движок": "",
        "кто_сидит": None,
        "трудовая_история": [],
        "заведён": _teper(),
    }
    for k, v in (polya or {}).items():
        if k in POLYA_BLANKA and v not in (None, "", []):
            d[k] = v
    if not d["название"]:
        d["название"] = post_id
    return d


def chitat(post_id: str):
    return _chitat(put_posta(post_id))


def id_dlya_slota(ceh: str, slot: str) -> str:
    """Имя поста для места в цехе. Одно правило на весь город, чтобы
    один и тот же слот не завёлся дважды под разными именами."""
    return f"{ceh}__{slot}"


# ─────────────────────────────────────────────────────────────
# СКАНЕР МЕСТ — списков не ведём
# ─────────────────────────────────────────────────────────────

def _studia_koren():
    """Корень старой студии, если Шеф указал путь. Нет — None."""
    try:
        p = Path(STUDIA_PUT.read_text(encoding="utf-8").strip())
        return p if p.exists() else None
    except Exception:
        return None


LOKACII = CITY / "локации"


def lokacii() -> dict:
    """Локации города: id → имя. Списков не держим — читаем папку."""
    out = {}
    if not LOKACII.exists():
        return out
    for d in sorted(LOKACII.iterdir()):
        p = _chitat(d / "passport.json")
        if p is None and not d.is_dir():
            continue
        out[d.name] = (p or {}).get("Official_Name", d.name)
    return out


def kartridzhi() -> list:
    """Картриджи города с их зданием. LOKACIYA_DAYOT_MESTA_V1: манифест
    цеха сам говорит, в каком здании стоит — привязка уже была, просто
    записана со стороны цеха."""
    out = []
    if not CITY.exists():
        return out
    for kv in sorted(CITY.iterdir()):
        ceha = kv / "цеха"
        if not ceha.is_dir():
            continue
        for cd in sorted(ceha.iterdir()):
            mf = cd / "manifest.json"
            if not mf.exists():
                continue
            m = _chitat(mf) or {}
            out.append({"цех": cd.name, "папка_квартала": kv.name,
                        "здание": m.get("здание", ""),
                        "квартал": m.get("квартал", ""),
                        "слоты": m.get("слоты", []) or []})
    return out


def _mesta_novogo_goroda() -> list:
    """Слоты картриджей — вакансии тех ЗДАНИЙ, где картриджи стоят."""
    out = []
    for k in kartridzhi():
        for s in k["слоты"]:
            slot = s.get("слот")
            if slot:
                out.append({"локация": k["здание"] or k["квартал"],
                            "квартал": k["папка_квартала"], "цех": k["цех"],
                            "слот": slot, "роль": s.get("роль", ""),
                            "откуда": "картридж"})
    return out


def _mesta_staroy_studii() -> list:
    """Слоты картриджей старой студии. Путь не указан — пусто."""
    out = []
    koren = _studia_koren()
    if koren is None:
        return out
    mods = koren / "studio" / "modules"
    if not mods.is_dir():
        return out
    for cd in sorted(mods.iterdir()):
        mf = cd / "manifest.json"
        if not mf.exists():
            continue
        m = _chitat(mf) or {}
        vidno = []
        for spisok in (m.get("phases") or {}).values():
            for a in spisok or []:
                if a not in vidno:
                    vidno.append(a)
        for a in vidno:
            out.append({"квартал": "Студия", "цех": cd.name, "слот": a,
                        "роль": "", "откуда": "студия"})
    return out


def mesta() -> list:
    """ВСЕ места города: заведённые посты плюс слоты цехов, у которых
    поста ещё нет. Одно место — одна строка, дублей не бывает: слот
    и пост сходятся по id_dlya_slota."""
    out = []
    vidennye = set()

    if POSTY.exists():
        for d in sorted(POSTY.iterdir()):
            p = _chitat(d / "пост.json")
            if not p:
                continue
            out.append({
                "id": p.get("id", d.name),
                "название": p.get("название", d.name),
                # LOKACIYA_DAYOT_MESTA_V1: место всегда чьё-то. Пусто —
                # значит осиротело, и это надо видеть, а не прятать.
                "локация": p.get("локация") or p.get("где", ""),
                "квартал": p.get("квартал", ""),
                "цех": p.get("цех", ""),
                "слот": p.get("слот", ""),
                "кто_сидит": ((p.get("кто_сидит") or {}).get("имя") or ""),
                "есть_пост": True,
                "откуда": "пост",
            })
            if p.get("цех") and p.get("слот"):
                vidennye.add(id_dlya_slota(p["цех"], p["слот"]))
            vidennye.add(p.get("id", d.name))

    for m in _mesta_novogo_goroda() + _mesta_staroy_studii():
        pid = id_dlya_slota(m["цех"], m["слот"])
        if pid in vidennye:
            continue
        out.append({
            "id": pid,
            "название": m.get("роль") or f'{m["цех"]} · {m["слот"]}',
            "локация": m.get("локация", ""),
            "квартал": m["квартал"], "цех": m["цех"], "слот": m["слот"],
            "кто_сидит": "", "есть_пост": False, "откуда": m["откуда"],
        })
    return out


def po_lokaciyam() -> list:
    """Город глазами локаций: что каждая предлагает.

    LOKACIYA_DAYOT_MESTA_V1: считаем ОТ ЗДАНИЙ. У локации два источника
    мест — картридж, который в ней стоит, и её собственные места
    (ректор, хранитель — без всякого картриджа, так решил Шеф).
    Пусто и там и там — локация честно ничего не предлагает.
    """
    loc = lokacii()
    vse = mesta()
    itog = []
    for lid, imya in loc.items():
        moi = [m for m in vse if (m.get("локация") or "") == lid]
        itog.append({"id": lid, "название": imya, "места": moi,
                     "занято": sum(1 for m in moi if m["кто_сидит"]),
                     "свободно": sum(1 for m in moi if m["есть_пост"]
                                     and not m["кто_сидит"])})
    siroty = [m for m in vse if (m.get("локация") or "") not in loc]
    if siroty:
        itog.append({"id": "", "название": "— без локации —",
                     "места": siroty,
                     "занято": sum(1 for m in siroty if m["кто_сидит"]),
                     "свободно": sum(1 for m in siroty if m["есть_пост"]
                                     and not m["кто_сидит"])})
    return itog


def schet() -> dict:
    v = mesta()
    return {"всего": len(v),
            "с должностью": sum(1 for m in v if m["есть_пост"]),
            "занято": sum(1 for m in v if m["кто_сидит"]),
            "свободно": sum(1 for m in v if m["есть_пост"] and not m["кто_сидит"]),
            "без должности": sum(1 for m in v if not m["есть_пост"])}


# ─────────────────────────────────────────────────────────────
# ЖИТЕЛЬ: дом и отметка
# ─────────────────────────────────────────────────────────────

def dom_zhitelya(imya: str):
    imya = (imya or "").strip()
    if not imya or not KOVCHEG.exists():
        return None
    for p in sorted(KOVCHEG.glob("*/passport.json")):
        d = _chitat(p) or {}
        if (d.get("Official_Name") or p.parent.name).strip() == imya:
            return p.parent
    return None


def _otmetka(imya: str, post: dict | None):
    """Отметка в паспорте: житель знает о работе где угодно. Правды не
    несёт — правда в посте. post=None — гасим."""
    dom = dom_zhitelya(imya)
    if dom is None:
        return False
    pp = dom / "passport.json"
    p = _chitat(pp)
    if p is None:
        return False
    if post is None:
        p.pop("Работа", None)
    else:
        gde = " · ".join(x for x in (post.get("квартал"), post.get("цех"),
                                     post.get("слот")) if x) or post.get("где", "")
        p["Работа"] = {"должность": post.get("название", ""), "где": gde,
                       "пост": post.get("id", ""), "с": _teper(),
                       "_note": ("отметка о работе. Правда о найме — в "
                                 "документе поста; здесь для того, чтобы "
                                 "житель знал о ней где угодно.")}
    return _pisat(pp, p)


# ─────────────────────────────────────────────────────────────
# ЧЕТЫРЕ РУКИ
# ─────────────────────────────────────────────────────────────

def zavesti(post_id: str, polya: dict | None = None) -> tuple:
    """Завести должность. Заведённую не перетираем — дополняем."""
    put = put_posta(post_id)
    d = _chitat(put)
    if d is None:
        d = blank(post_id, polya)
        msg = "должность заведена"
    else:
        for k, v in (polya or {}).items():
            if k in POLYA_BLANKA and v not in (None, "", []) and not d.get(k):
                d[k] = v
        msg = "должность обновлена"
    return (True, msg) if _pisat(put, d) else (False, "не записался")


def obnovit(post_id: str, polya: dict) -> tuple:
    """Переписать поля бланка. Кто сидит и историю не трогаем."""
    put = put_posta(post_id)
    d = _chitat(put)
    if d is None:
        return False, "такой должности нет"
    for k, v in (polya or {}).items():
        if k in POLYA_BLANKA:
            d[k] = v
    return (True, "бланк переписан") if _pisat(put, d) else (False, "не записался")


def prinyat(post_id: str, imya: str, kem: str = "Шеф",
            pochemu: str = "") -> tuple:
    imya = (imya or "").strip()
    if not imya:
        return False, "не сказано, кого принимаем"
    put = put_posta(post_id)
    d = _chitat(put)
    if d is None:
        return False, "у места нет должности — сперва заведи"
    if dom_zhitelya(imya) is None:
        return False, f"жителя «{imya}» в городе не нашёл"
    zanyal = ((d.get("кто_сидит") or {}).get("имя") or "").strip()
    if zanyal == imya:
        return True, f"{imya} и так на этом месте"
    if zanyal:
        return False, f"место занято: {zanyal} — сперва уволь"
    d["кто_сидит"] = {"имя": imya, "с": _teper()}
    d.setdefault("трудовая_история", []).append(
        {"когда": _teper(), "что": "принят", "кто": imya,
         "кем": kem, "почему": pochemu})
    if not _pisat(put, d):
        return False, "документ не записался"
    _otmetka(imya, d)
    return True, f"{imya} принят на «{d.get('название', post_id)}»"


def uvolit(post_id: str, kem: str = "Шеф", pochemu: str = "") -> tuple:
    put = put_posta(post_id)
    d = _chitat(put)
    if d is None:
        return False, "такой должности нет"
    imya = ((d.get("кто_сидит") or {}).get("имя") or "").strip()
    if not imya:
        return True, "место и так свободно"
    d["кто_сидит"] = None
    d.setdefault("трудовая_история", []).append(
        {"когда": _teper(), "что": "уволен", "кто": imya,
         "кем": kem, "почему": pochemu})
    if not _pisat(put, d):
        return False, "документ не записался"
    _otmetka(imya, None)
    return True, f"{imya} уволен, место свободно"


def snesti(post_id: str) -> tuple:
    """Снести должность совсем. Занятую не сносим — сперва уволь."""
    d = chitat(post_id)
    if d is None:
        return False, "такой должности нет"
    if ((d.get("кто_сидит") or {}).get("имя") or "").strip():
        return False, "место занято — сперва уволь"
    try:
        put = put_posta(post_id)
        put.unlink()
        try:
            put.parent.rmdir()
        except OSError:
            pass
        return True, "должность снесена"
    except Exception as e:
        return False, str(e)


def kto_sidit(post_id: str) -> str:
    d = chitat(post_id)
    return ((d or {}).get("кто_сидит") or {}).get("имя", "") if d else ""


def kto_na_slote(ceh: str, slot: str) -> str:
    """Кто сидит на месте цеха. Ищем пост по привязке, а не по имени
    папки: пост мог быть заведён и вручную, с другим id."""
    if not POSTY.exists():
        return ""
    for d in sorted(POSTY.iterdir()):
        p = _chitat(d / "пост.json")
        if not p:
            continue
        if p.get("цех") == ceh and p.get("слот") == slot:
            return ((p.get("кто_сидит") or {}).get("имя") or "").strip()
    return ""


def est_post_na_slote(ceh: str, slot: str) -> bool:
    if not POSTY.exists():
        return False
    for d in sorted(POSTY.iterdir()):
        p = _chitat(d / "пост.json")
        if p and p.get("цех") == ceh and p.get("слот") == slot:
            return True
    return False

# LOKACIYA_DAYOT_MESTA_V1 - marker
