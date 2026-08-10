# -*- coding: utf-8 -*-
# GOROD_GNEZDA_V2 — гнёзда Маяка · универсальные розетки
"""
ГНЁЗДА МАЯКА · десять розеток

Почему именно так (слово Шефа):
    В паспорте Маяка доступ 10, а вмещает без края. Значит Маяк
    НИКОГО НЕ ОТСЕКАЕТ — ни очереди, ни закреплённых мест. Пузырёк
    наверху не «место жителя», как парта в Академии, а СКОЛЬКО ЛУЧЕЙ
    маяк держит разом.

ГНЕЗДО ВСЕЯДНО. Ему всё равно, что воткнули: житель пришёл искать,
пост полез за стены, канал наружу, инструмент, чужой сервис. Разъём
один на всех — потому и «розетка». Род НЕ проверяется списком: появится
завтра вид подключения, которого мы не придумали, — просто воткнётся,
код править не надо. Гнездо хранит только ЧТО в нём и КАКОГО ОНО РОДА;
работать умеет не гнездо, а то, что внутри.

ИМЯ И КЛЮЧ — РАЗНОЕ. Имя видно на экране («Нина»), ключ опознаёт
(«028_NINA»). Два тёзки не спутаются, и один житель не займёт два
луча. Ключа нет — опознаём по имени, но это слабее.

СРОК РАЗНЫЙ, и это тоже слово Шефа:
    • КАНАЛЫ, ИНСТРУМЕНТЫ, СЕРВИСЫ — постоянно. Воткнул и горит.
    • ЖИВЫЕ (житель, пост, Шеф) — на сеанс. Помолчал — гнездо гаснет,
      луч освобождается другому.

Цикла у города нет (тик жмут руками), поэтому живые гаснут не по
таймеру, а честным СКАНОМ: спросили гнёзда — просроченные уже не
показываются. Но ЧТЕНИЕ НЕ ПИШЕТ НА ДИСК: смотреть — не значит менять.
Уборка отдельной рукой, pribrat(), её зовёт кабинет при открытии.

    GRONDHEIM_CITY/посты/mayak/гнёзда.json

Собран из двух черновиков: основа — ключи, всеядность и гашение живых;
добавлено — «чем занят», самостоятельный канал провайдера и чистое
чтение.

`шесть·проверено·до·корня`
"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

_HERE = Path(__file__).resolve().parent      # ГОРОД/
_REPO = _HERE.parent                          # корень репо

GNEZDA_FILE = _REPO / "GRONDHEIM_CITY" / "посты" / "mayak" / "гнёзда.json"

VSEGO = 10                  # лучей разом — доступ из паспорта Маяка
SEANS_MINUT = 30            # сколько живой держит луч без слова

# рода. Список — подсказка, а не запрет: votknut() примет любой.
ROD_KANAL = "канал"         # выход наружу (Tavily и прочие) — постоянно
ROD_ZHIVOY = "живой"        # житель, пост, Шеф — на сеанс
ROD_INSTRUMENT = "инструмент"
ROD_SERVIS = "сервис"

# что держится постоянно, а что гаснет
POSTOYANNYE = {ROD_KANAL, ROD_INSTRUMENT, ROD_SERVIS}


def _now():
    return datetime.now(timezone.utc)


def _iso(dt=None):
    return (dt or _now()).isoformat(timespec="seconds")


def _read() -> dict:
    try:
        return json.loads(GNEZDA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"гнёзда": []}


def _write(data: dict) -> bool:
    try:
        GNEZDA_FILE.parent.mkdir(parents=True, exist_ok=True)
        GNEZDA_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def _postoyannoe(g: dict) -> bool:
    return bool(g.get("постоянно") or g.get("род") in POSTOYANNYE)


def _prosrocheno(g: dict) -> bool:
    """Погас ли живой. Постоянные не гаснут никогда."""
    if _postoyannoe(g):
        return False
    ts = g.get("последний_раз") or g.get("воткнут")
    if not ts:
        return True
    try:
        byl = datetime.fromisoformat(ts)
    except Exception:
        return True
    return _now() - byl > timedelta(minutes=SEANS_MINUT)


# ═══════════════════════════════════════════════════════════
# ЧТЕНИЕ — всегда все десять, и диск при этом не трогаем
# ═══════════════════════════════════════════════════════════

def spisok() -> list:
    """Все десять гнёзд по порядку. Просроченные живые отдаются
    пустыми — розетка не врёт, что кто-то на связи, когда он ушёл.

    ЧТЕНИЕ НЕ ПИШЕТ. Мусор с диска сметает pribrat(), отдельной рукой.

    [{"номер","род","имя","ключ","что","занято","постоянно","тихо_минут","воткнут"}]
    """
    zapisi = _read().get("гнёзда", []) or []

    po_nomeru = {}
    for g in zapisi:
        try:
            n = int(g.get("номер", 0))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= VSEGO and not _prosrocheno(g):
            po_nomeru[n] = g

    out = []
    for n in range(1, VSEGO + 1):
        g = po_nomeru.get(n)
        if not g:
            out.append({"номер": n, "род": "", "имя": "", "ключ": "", "что": "",
                        "занято": False, "постоянно": False,
                        "тихо_минут": 0, "воткнут": ""})
            continue
        tiho = 0
        ts = g.get("последний_раз") or g.get("воткнут")
        if ts:
            try:
                tiho = int((_now() - datetime.fromisoformat(ts)).total_seconds() // 60)
            except Exception:
                tiho = 0
        out.append({
            "номер": n,
            "род": g.get("род", ""),
            "имя": g.get("имя", ""),
            "ключ": g.get("ключ", ""),
            "что": g.get("что", ""),
            "занято": True,
            "постоянно": _postoyannoe(g),
            "тихо_минут": tiho,
            "воткнут": g.get("воткнут", ""),
        })
    return out


def po_poryadku() -> list:
    """Гнёзда для показа: живые → свободные → ПОСТОЯННЫЕ В КОНЕЦ
    (слово Шефа). Слева движение, справа то, что стоит всегда —
    канал не должен теряться среди мигающих сеансов.
    Номера при этом не меняются, меняется только порядок показа."""
    gn = spisok()
    zhivye = [g for g in gn if g["занято"] and not g["постоянно"]]
    pusto = [g for g in gn if not g["занято"]]
    stoyat = [g for g in gn if g["занято"] and g["постоянно"]]
    return zhivye + pusto + stoyat


def gnezdo(nomer: int) -> dict:
    """Одно гнездо по номеру. Нет такого — пустой словарь."""
    for g in spisok():
        if g["номер"] == int(nomer or 0):
            return g
    return {}


def svobodnoe() -> int:
    """Номер первого свободного гнезда. Все заняты — 0."""
    for g in spisok():
        if not g["занято"]:
            return g["номер"]
    return 0


def svobodnyh() -> int:
    """Сколько гнёзд свободно."""
    return sum(1 for g in spisok() if not g["занято"])


def naydti(klyuch: str = "", imya: str = "") -> int:
    """В каком гнезде сидит. Сперва по ключу (надёжно), потом по имени.
    Нет — 0. Нужно, чтобы один и тот же не занял два луча."""
    if not klyuch and not imya:
        return 0
    for g in spisok():
        if not g["занято"]:
            continue
        if klyuch and g["ключ"] == klyuch:
            return g["номер"]
        if not klyuch and imya and g["имя"] == imya:
            return g["номер"]
    return 0


def svodka() -> dict:
    """Коротко: сколько горит, свободно, каких родов."""
    gn = spisok()
    zanyato = [g for g in gn if g["занято"]]
    return {
        "всего": VSEGO,
        "горит": len(zanyato),
        "свободно": VSEGO - len(zanyato),
        "постоянных": len([g for g in zanyato if g["постоянно"]]),
        "живых": len([g for g in zanyato if not g["постоянно"]]),
        "каналов": len([g for g in zanyato if g["род"] == ROD_KANAL]),
    }


# ═══════════════════════════════════════════════════════════
# ЗАПИСЬ — воткнуть, поддержать, вынуть
# ═══════════════════════════════════════════════════════════

def votknut(rod: str, imya: str, klyuch: str = "", chto: str = "",
            nomer: int = 0, postoyanno: bool = None) -> tuple:
    """Воткнуть что-нибудь в гнездо. Род ЛЮБОЙ — гнездо всеядно.

    rod        — канал / живой / инструмент / сервис / что придумаешь
    imya       — как показывать: «Нина», «Tavily»
    klyuch     — чем опознавать: «028_NINA». Пусто — опознаём по имени
    chto       — чем занят: «ищет про Эллиотта». Видно в кабинете
    nomer      — просить конкретное гнездо; 0 — первое свободное
    postoyanno — None: решаем по роду (живой на сеанс, прочие горят)

    Уже воткнут — не плодим второй луч, обновляем срок и «чем занят».
    Чужое гнездо не вышибаем. Возвращает (успех: bool, сообщение: str).
    """
    rod = (rod or "").strip() or ROD_ZHIVOY
    imya = (imya or "").strip()
    if not imya:
        return False, "нечего втыкать — пустое имя"

    # уже горит? — поддержим, второй луч не занимаем
    est = naydti(klyuch, imya)
    if est:
        podderzhat(klyuch, imya, chto)
        return True, f"уже горит в гнезде {est}"

    if postoyanno is None:
        postoyanno = rod in POSTOYANNYE

    if nomer:
        nomer = int(nomer)
        if not (1 <= nomer <= VSEGO):
            return False, f"гнезда {nomer} нет — их всего {VSEGO}"
        if gnezdo(nomer).get("занято"):
            return False, f"гнездо {nomer} занято — чужое не вышибаю"
    else:
        nomer = svobodnoe()
        if not nomer:
            return False, f"все {VSEGO} лучей заняты — маяк на пределе"

    data = _read()
    data.setdefault("гнёзда", []).append({
        "номер": nomer,
        "род": rod,
        "имя": imya,
        "ключ": klyuch,
        "что": chto,
        "постоянно": bool(postoyanno),
        "воткнут": _iso(),
        "последний_раз": _iso(),
    })
    if not _write(data):
        return False, "не записалось на диск"
    return True, f"гнездо {nomer}"


def podderzhat(klyuch: str = "", imya: str = "", chto: str = "") -> bool:
    """Живой подал голос — сеанс продлевается, «чем занят» обновляется.
    Без этого гнездо само погаснет через SEANS_MINUT."""
    if not klyuch and not imya:
        return False
    data = _read()
    tronuli = False
    for g in data.get("гнёзда", []) or []:
        sovpal = ((klyuch and g.get("ключ") == klyuch)
                  or (not klyuch and imya and g.get("имя") == imya))
        if sovpal:
            g["последний_раз"] = _iso()
            if chto:
                g["что"] = chto
            tronuli = True
    return _write(data) if tronuli else False


def vynut(nomer: int = 0, klyuch: str = "", imya: str = "") -> tuple:
    """Освободить гнездо — по номеру, ключу или имени."""
    data = _read()
    bylo = list(data.get("гнёзда", []) or [])
    stalo, snyali = [], ""
    for g in bylo:
        sovpal = ((nomer and int(g.get("номер", 0) or 0) == int(nomer))
                  or (klyuch and g.get("ключ") == klyuch)
                  or (imya and g.get("имя") == imya))
        if sovpal and not snyali:
            snyali = g.get("имя", "?")
            continue
        stalo.append(g)
    if not snyali:
        return False, "в этом гнезде и так пусто"
    data["гнёзда"] = stalo
    if not _write(data):
        return False, "не записалось на диск"
    return True, f"{snyali} — отключён"


def pogasit_zhivyh() -> int:
    """Погасить все живые разом, каналы и железо не трогая.
    Нужно, когда лучи залипли и Шеф хочет чистый маяк."""
    data = _read()
    bylo = list(data.get("гнёзда", []) or [])
    stalo = [g for g in bylo if _postoyannoe(g)]
    if len(stalo) != len(bylo):
        data["гнёзда"] = stalo
        _write(data)
    return len(bylo) - len(stalo)


def pribrat() -> int:
    """Смести с диска погасшие сеансы. Отдельная рука — чтение их и
    так не показывает, а это уборка. Зовётся при открытии кабинета."""
    data = _read()
    bylo = list(data.get("гнёзда", []) or [])
    stalo = [g for g in bylo if not _prosrocheno(g)]
    if len(stalo) != len(bylo):
        data["гнёзда"] = stalo
        _write(data)
    return len(bylo) - len(stalo)


# ═══════════════════════════════════════════════════════════
# ПЕРВЫЙ КАНАЛ — маяк не бывает без выхода наружу
# ═══════════════════════════════════════════════════════════

def zavesti_kanal_provaydera() -> tuple:
    """Ставит провайдера поиска в первое гнездо, если ключ есть и он
    ещё не воткнут. Зовётся при открытии кабинета — канал должен
    стоять сам, его не втыкают руками каждый раз.

    Ключа нет — НЕ втыкаем: тёмный канал в розетке был бы враньём.
    """
    try:
        import mayak
    except ImportError:
        return False, "модуля маяка нет"
    if not mayak.gorit():
        return False, "провайдер без ключа — тёмный канал не втыкаю"
    return votknut(ROD_KANAL, "Tavily", klyuch="tavily",
                   chto="выход во внешний мир", nomer=1, postoyanno=True)


# GOROD_GNEZDA_V2 — маркер идемпотентности
