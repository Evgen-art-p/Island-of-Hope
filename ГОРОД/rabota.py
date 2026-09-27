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
                "чем_занят", "инструмент", "обязанности", "судья",
                "требования", "условия", "движок")


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
        # INSTRUMENT_NAZNACHIT_ILI_SAM_V1: пусто — работник выберет сам
        "инструмент": "",
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
    # KONTORA_NE_KARTRIDZH_V1: два рода, не один. Контора квартала —
    # постоянная служба, лежит отдельной папкой и не вынимается. Цеха —
    # сменные картриджи на полке «цеха». Вид ставим ПО ИМЕНИ ПАПКИ, а не
    # по месту: контора, лежащая по старому адресу, тоже зовётся конторой,
    # и перенос её однажды ничего не сломает.
    out = []
    if not CITY.exists():
        return out
    for kv in sorted(CITY.iterdir()):
        if not kv.is_dir():
            continue
        papki = []
        kontora = kv / "контора"
        if (kontora / "manifest.json").exists():
            papki.append(kontora)
        ceha = kv / "цеха"
        if ceha.is_dir():
            papki += [c for c in sorted(ceha.iterdir())
                      if (c / "manifest.json").exists()]
        for cd in papki:
            m = _chitat(cd / "manifest.json") or {}
            out.append({"цех": cd.name, "папка_квартала": kv.name,
                        "вид": "контора" if cd.name == "контора" else "цех",
                        "папка": str(cd),   # MENEDZHER_KARTRIDZHEY_V1
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
        # MAGIC_PRI_MESTE_V2: кресло получает номер счёта СРАЗУ, при
        # заведении. Потом его никто не выдаёт вручную и не забывает.
        if not d.get("magic"):
            d["magic"] = magic_dlya_slota(d.get("слот") or "")
        msg = "должность заведена"
    else:
        for k, v in (polya or {}).items():
            if k in POLYA_BLANKA and v not in (None, "", []) and not d.get(k):
                d[k] = v
        if not d.get("magic"):      # MAGIC_PRI_MESTE_V2: старым местам тоже
            d["magic"] = magic_dlya_slota(d.get("слот") or "")
        msg = "должность обновлена"
    return (True, msg) if _pisat(put, d) else (False, "не записался")


def zavesti_mesta_kartridzhey() -> tuple:
    """Завести должности всем слотам картриджей. MESTA_ZAVODYATSYA_SAMI_V1.

    Слот в манифесте — уже решение: место есть, и всё про него написано.
    Бланк лишь повторяет эти слова, поэтому заводим сам, а не просим
    Шефа подтвердить написанное.

    Заведённые не трогаем: zavesti() дополняет пустые поля и не
    перетирает занятые. Никого не сажаем — посадка остаётся решением.
    """
    zavedeno, bylo = 0, 0

    # SLOT_NE_DVAZHDY_V1: проверка «место уже заведено?» смотрела на
    # ИМЯ ФАЙЛА (id_dlya_slota), а не на то, что реально записано в
    # должностях. Три места (треугольник Биржи) были заведены давно
    # под старыми именами — их эта проверка не видела и заводила рядом
    # пустого близнеца. Теперь смотрим по факту: цех+слот среди ВСЕХ
    # заведённых должностей, каким бы файлом они ни лежали.
    _zanyatye_slota = set()
    if POSTY.exists():
        for _d in POSTY.iterdir():
            _p = _chitat(_d / "пост.json")
            if _p and _p.get("цех") and _p.get("слот"):
                _zanyatye_slota.add((_p["цех"], _p["слот"]))

    for k in kartridzhi():
        m = _chitat(Path(k["папка"]) / "manifest.json") or {} \
            if k.get("папка") else {}
        for s in (k.get("слоты") or []):
            slot = s.get("слот")
            if not slot:
                continue
            if (k["цех"], slot) in _zanyatye_slota:
                bylo += 1
                continue
            pid = id_dlya_slota(k["цех"], slot)
            rol = s.get("роль", "") or slot
            ok, _ = zavesti(pid, {
                "название": rol,
                "чем_занят": rol,
                "локация": k.get("здание", "") or k.get("квартал", ""),
                "квартал": k.get("папка_квартала", ""),
                "цех": k["цех"],
                "слот": slot,
                "судья": m.get("судья", ""),
            })
            if ok:
                zavedeno += 1
    return zavedeno, bylo


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
    # MAGIC_PRI_MESTE_V2: сел в кресло — работаешь под ЕГО номером.
    _maska_po_postu(imya, d)
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
    # MAGIC_PRI_MESTE_V2: ушёл — номер остался при кресле, а не уехал
    # с человеком. Иначе уволенный продолжает числиться на месте, где
    # уже сидит другой.
    _maska_po_postu(imya, None)
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

# INSTRUMENT_NAZNACHIT_ILI_SAM_V1 - marker


# ── MAGIC_PRI_MESTE_V2: маска работы = проекция ПОСТА ────────
# Правда о найме живёт в посте. Маска жителя её отражает — и должна
# меняться ровно тогда, когда меняется пост.
#
# Раньше prinyat/uvolit маску НЕ ТРОГАЛИ: Нину сажали руками — маска
# заполнилась, Синди и Веру через Страницу Работы — осталась пустой,
# без магика. А уволенный Илья продолжал числиться на A07, где уже
# сидела Синди: судья мог отдать вывод из сделки не тому человеку.
#
# Магик при этом принадлежит КРЕСЛУ, а не жильцу: пересел — номер
# остался за местом и достался новому.
def _maska_po_postu(imya: str, post: dict | None) -> bool:
    """post=None — гасим маску (уволен). Иначе — заполняем из поста."""
    dom = dom_zhitelya(imya)
    if dom is None:
        return False
    mf = dom / "маски" / "работа" / "mask.json"
    mk = _chitat(mf) or {}
    if post is None:
        mk["Workshop_ID"] = ""
        mk["Turbo_Role"] = ""
        mk["magic"] = None
        mk["_активна"] = False
    else:
        mk["Workshop_ID"] = post.get("цех") or post.get("квартал") or ""
        mk["Turbo_Role"] = post.get("слот") or post.get("название") or ""
        mk["magic"] = post.get("magic")
        # реестр берёт ТОЛЬКО активные маски: неактивная = человека по
        # магику не найдут, и вывод судьи повиснет
        mk["_активна"] = True
    try:
        mf.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return _pisat(mf, mk)


def magic_dlya_slota(slot: str) -> int:
    """Номер счёта для КРЕСЛА. Схема из старого тестера, она уже жила
    в городе: A06→100001, A07→100002, A08→100003. Новый слот получает
    следующий свободный, чтобы номера не сталкивались."""
    izvestnye = {"A06": 100001, "A07": 100002, "A08": 100003}
    s = (slot or "").strip().upper()
    if s in izvestnye:
        return izvestnye[s]
    zanyato = set()
    if POSTY.exists():
        for d in POSTY.iterdir():
            p = _chitat(d / "пост.json") or {}
            m = p.get("magic")
            if isinstance(m, int):
                zanyato.add(m)
    n = 100001
    while n in zanyato:
        n += 1
    return n


# MAGIC_PRI_MESTE_V2 - marker

# SLOT_NE_DVAZHDY_V1 - marker
