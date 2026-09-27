# -*- coding: utf-8 -*-
# GOROD_REZIDENTY_V1 — городской менеджер резидентов
"""
ГОРОДСКИЕ РЕЗИДЕНТЫ · реестр постов

Что это. В городе есть ПОСТЫ — рабочие места, которые существуют
независимо от того, кто их занимает. Библиотекарь Академии. Хронист.
Архиватор. Пост стоит, даже когда он пуст.

ГЛАВНЫЙ ЗАКОН ЭТОГО ФАЙЛА (слово Шефа):
    ЛИЧНОСТЬ НЕ ПРИКРУЧЕНА К РОЛИ.
Пост не знает, кто в нём сидит. Житель не знает, что он «библиотекарь
навсегда». Связь живёт ОТДЕЛЬНО — в файле поста, и меняется в один
приём. Посади другого — движок тот же, голос другой.

    ПОСТ (роль)      — что делают на этом месте. Файл движка.
    ЖИТЕЛЬ (личность) — кто именно там сидит. Паспорт в ковчеге.
    СВЯЗЬ            — {пост}.json, одна строка. Меняется свободно.

И РОД (порода) здесь НЕ проверяется нигде. Рабочее место не
привязано к роду — это прямой закон Шефа. Кто угодно может занять
любой пост, если Брат его туда посадил.

Что НЕ делает: не запускает движки, не думает за них, не держит
списка постов в коде. Посты сканируются с диска (Закон Картриджа) —
завёл папку, пост появился сам.

    GRONDHEIM_CITY/посты/{id}/
        пост.json       ← что за пост: название, где, какой движок
        хранитель.json  ← кто сейчас сидит (нет файла = вакансия)

`шесть·проверено·до·корня`
"""
import json
from pathlib import Path
from datetime import datetime, timezone

_HERE = Path(__file__).resolve().parent      # ГОРОД/
_REPO = _HERE.parent                          # корень репо

POSTY_DIR = _REPO / "GRONDHEIM_CITY" / "посты"
KOVCHEG = _REPO / "GRONDHEIM_CITY" / "жители" / "ковчег"


# ═══════════════════════════════════════════════════════════
# ДИСК — читаем честно, пустое отдаём пустым
# ═══════════════════════════════════════════════════════════

def _read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(p: Path, data) -> bool:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8")
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════
# ПОСТЫ — сканируем, не держим списком
# ═══════════════════════════════════════════════════════════

def list_posty() -> list:
    """Все посты города. Сканируем папку — новый пост появляется сам,
    без правки этого файла (Закон Картриджа).

    Возвращает [{"id", "название", "где", "движок", "житель", "занят"}].
    Постов нет — пустой список, это честное состояние молодого города.
    """
    out = []
    if not POSTY_DIR.exists():
        return out
    for d in sorted(POSTY_DIR.iterdir()):
        if not d.is_dir():
            continue
        m = _read_json(d / "пост.json", {}) or {}
        hr = _read_json(d / "хранитель.json", {}) or {}
        zhitel = hr.get("житель", "") or ""
        out.append({
            "id": d.name,
            "название": m.get("название", d.name),
            "где": m.get("где", ""),
            "движок": m.get("движок", ""),
            "житель": zhitel,
            "занят": bool(zhitel),
        })
    return out


def get_post(post_id: str) -> dict:
    """Один пост по id. Нет такого — пустой словарь, не выдумываем."""
    for p in list_posty():
        if p["id"] == post_id:
            return p
    return {}


def zavesti_post(post_id: str, nazvanie: str, gde: str = "",
                 dvizhok: str = "") -> tuple:
    """Заводит пост на диске. Уже есть — не трогаем (идемпотентно).

    dvizhok — имя модуля, который умеет работать на этом посту
    (например "bibliotekar"). Пусто — пост есть, работы пока нет.
    Возвращает (успех: bool, сообщение: str).
    """
    d = POSTY_DIR / post_id
    mf = d / "пост.json"
    if mf.exists():
        return True, "пост уже заведён"
    ok = _write_json(mf, {
        "id": post_id,
        "название": nazvanie,
        "где": gde,
        "движок": dvizhok,
        "заведён": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return (True, "пост заведён") if ok else (False, "не записался на диск")


# ═══════════════════════════════════════════════════════════
# СВЯЗЬ ПОСТ ↔ ЖИТЕЛЬ — отдельно от обоих
# ═══════════════════════════════════════════════════════════

# POST_V_PASPORTE_V1 — ПРАВДА О ПОСТЕ ЖИВЁТ В ПАСПОРТЕ ЖИТЕЛЯ
#
# Было: связь в посты/{id}/хранитель.json, сбоку от обоих. Житель не
# знал, что он на посту, — работу ему подкладывали снаружи на время
# разговора. Ректор не знал, что он ректор.
#
# Стало: в паспорте поле "Посты" — список того, что житель сейчас
# делает. Душа, стол и память читают паспорт и так, значит работу
# видят сами. Одна правда, одно место.
#
# Это НЕ «прикрутить личность к роли» (закон Шефа в шапке файла в
# силе). Пост в паспорте — состояние, а не порода: сняли с поста,
# строка ушла, житель прежний. Чертёж §1.5.2б: роль живёт внутри Рода.
POLE_POSTY = "Посты"


def _pasport_put(imya: str):
    """Путь к паспорту жителя. Нет жителя — None."""
    d = KOVCHEG / imya
    p = d / "passport.json"
    return p if p.exists() else None


def _posty_zhitelya(imya: str) -> list:
    p = _pasport_put(imya)
    if p is None:
        return []
    spisok = (_read_json(p, {}) or {}).get(POLE_POSTY, [])
    return spisok if isinstance(spisok, list) else []


def _zapisat_posty(imya: str, spisok: list) -> bool:
    """Кладёт список постов в паспорт, НЕ трогая остальное. Паспорт
    перечитывается прямо перед записью — рядом может работать движок."""
    p = _pasport_put(imya)
    if p is None:
        return False
    pasport = _read_json(p, None)
    if not isinstance(pasport, dict):
        return False
    if spisok:
        pasport[POLE_POSTY] = spisok
    else:
        pasport.pop(POLE_POSTY, None)   # пустой список не держим
    return _write_json(p, pasport)


def perenesti_posty() -> int:
    """Разовый переезд старых хранитель.json в паспорта. Зовётся сам
    при первом обращении к постам, вручную не нужен.

    Старый файл НЕ удаляем — переименовываем в .перенесено, чтобы
    никто случайно не прочитал устаревшую правду, но и не потерять.
    """
    if not POSTY_DIR.exists():
        return 0
    pereehalo = 0
    for d in sorted(POSTY_DIR.iterdir()):
        f = d / "хранитель.json"
        if not f.is_dir() and f.exists():
            imya = (_read_json(f, {}) or {}).get("житель", "")
            if imya and _pasport_put(imya) is not None:
                spisok = _posty_zhitelya(imya)
                if not any(x.get("пост") == d.name for x in spisok
                           if isinstance(x, dict)):
                    spisok.append({
                        "пост": d.name,
                        "с": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    })
                    _zapisat_posty(imya, spisok)
                    pereehalo += 1
            try:
                f.rename(d / "хранитель.json.перенесено")
            except Exception:
                pass
    return pereehalo


_perenos_sdelan = False


def _perenos_odin_raz():
    global _perenos_sdelan
    if not _perenos_sdelan:
        _perenos_sdelan = True
        try:
            perenesti_posty()
        except Exception:
            pass   # переезд не должен ронять город


def posadit(post_id: str, imya_zhitelya: str, zid: str = "") -> tuple:
    """Сажает жителя на пост. Род НЕ проверяется — закон Шефа.
    Пост занят другим — честно сменяем, но возвращаем, кто был,
    чтобы вызывающий мог сказать это вслух (не тайком).

    POST_V_PASPORTE_V1: пишем в паспорт. Заодно снимаем прежнего —
    иначе два паспорта заявят один пост, и никто не заметит.

    Возвращает (успех: bool, сообщение: str).
    """
    _perenos_odin_raz()
    d = POSTY_DIR / post_id
    if not (d / "пост.json").exists():
        return False, f"поста «{post_id}» нет — сначала заведи"
    if _pasport_put(imya_zhitelya) is None:
        return False, f"жителя «{imya_zhitelya}» нет в ковчеге"

    byl = kto_na_postu(post_id)
    if byl and byl != imya_zhitelya:
        # снимаем прежнего явно: одна правда, дублей не заводим
        _zapisat_posty(byl, [x for x in _posty_zhitelya(byl)
                             if not (isinstance(x, dict)
                                     and x.get("пост") == post_id)])

    spisok = [x for x in _posty_zhitelya(imya_zhitelya)
              if not (isinstance(x, dict) and x.get("пост") == post_id)]
    spisok.append({
        "пост": post_id,
        "id": zid,
        "с": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    if not _zapisat_posty(imya_zhitelya, spisok):
        return False, "не записался в паспорт"
    if byl and byl != imya_zhitelya:
        return True, f"сменил(а) на посту: {byl}"
    return True, "на посту"


def snyat(post_id: str) -> tuple:
    """Освобождает пост. Пост остаётся, вакансия открыта."""
    _perenos_odin_raz()
    imya = kto_na_postu(post_id)
    if not imya:
        return True, "пост и так свободен"
    ok = _zapisat_posty(imya, [x for x in _posty_zhitelya(imya)
                               if not (isinstance(x, dict)
                                       and x.get("пост") == post_id)])
    return (True, "пост освобождён") if ok else (False, "паспорт не записался")


def kto_na_postu(post_id: str) -> str:
    """Имя того, кто сейчас на посту. Пусто — вакансия.

    POST_V_PASPORTE_V1: смотрим паспорта. Ковчег маленький, обход
    дешёвый, зато правда одна и врать нечему.
    """
    _perenos_odin_raz()
    vse = kto_na_postu_vse(post_id)
    return vse[0] if vse else ""


def kto_na_postu_vse(post_id: str) -> list:
    """Все, кто заявил этот пост. В норме ноль или один. Двое —
    рассинхрон, и его лучше увидеть, чем спрятать: кабинет может
    показать это Шефу."""
    if not KOVCHEG.exists():
        return []
    out = []
    for d in sorted(KOVCHEG.iterdir()):
        if not d.is_dir():
            continue
        for x in _posty_zhitelya(d.name):
            if isinstance(x, dict) and x.get("пост") == post_id:
                out.append(d.name)
                break
    return out


def dom_zhitelya(imya: str) -> Path | None:
    """Дом жителя по имени. Нет — None. Нужен, чтобы движок поста
    поднял ЛИЧНОСТЬ того, кто сидит: паспорт, натуру, память."""
    if not imya:
        return None
    d = KOVCHEG / imya
    return d if (d / "passport.json").exists() else None


def lichnost_na_postu(post_id: str) -> tuple:
    """Личность того, кто на посту: (паспорт: dict, дом: Path) или
    (None, None), если пост пуст или дом не найден.

    ЭТО И ЕСТЬ РАЗВЯЗКА личности и роли: движок поста зовёт эту
    функцию и получает ЧЕЛОВЕКА. Кто это — движку всё равно, он
    одинаково работает с любым.
    """
    imya = kto_na_postu(post_id)
    dom = dom_zhitelya(imya)
    if dom is None:
        return None, None
    return _read_json(dom / "passport.json", {}), dom


# ═══════════════════════════════════════════════════════════
# ДУША — общий сбор личности, один способ на весь город
# ═══════════════════════════════════════════════════════════

def sobrat_dushu(p: dict) -> str:
    """Личность жителя словами — для системного промпта.
    Тот же набор полей, что кабинет жителя показывает Шефу
    (один способ на город). Пустые поля пропускаем.

    ВАЖНО: здесь НЕТ ни слова о работе, посте или роли. Это чистая
    личность. Роль приклеивает движок поста — своим текстом, сверху.
    """
    if not p:
        return ""
    imya = p.get("Official_Name", "житель")
    s = (f"Ты — {imya}, житель Грондхейма. Говоришь от первого лица, "
         f"живым голосом, не как ассистент.\n")
    for polе, podpis in (
        ("Core_Phrase",      "Твоё ядро (коронная фраза)"),
        ("Hidden_History",   "Твоя скрытая история"),
        ("Sensory_Response", "Как ты чувствуешь мир"),
        ("Anchor_Points",    "Твои незыблемые якоря"),
        ("Hidden_Taste",     "Твой скрытый вкус"),
        ("Pull_Vector",      "Тебя тянет к"),
        ("домашний_промпт",  "Твой дом, который ты носишь в себе всегда"),
    ):
        v = p.get(polе)
        if v:
            s += f"{podpis}: {v}\n"
    dna = p.get("DNA_Static", {}) or {}
    if isinstance(dna, dict) and dna:
        s += ("Твоя натура (черты характера): "
              + " · ".join(f"{k.split('_')[0]} {v}" for k, v in dna.items())
              + "\n")
    try:
        z = float(p.get("_charge", 0.0) or 0.0)
        s += (f"Сейчас твоё внутреннее состояние: {z:+.2f} "
              f"(от -1 до 1). Не называй это числом — просто веди себя в тон.\n")
    except (TypeError, ValueError):
        pass
    return s


# GOROD_REZIDENTY_V1 — маркер идемпотентности
