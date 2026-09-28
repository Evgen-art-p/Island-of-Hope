# -*- coding: utf-8 -*-
# arkhiv_nitochki_1.py — ПАТЧ: ниточки Архива Города, шаг 1
# Маркер: NITOCHKI_POISK_V1
"""
ЧТО ДЕЛАЕТ (слово Шефа 27.09: Архив видит всё, где что-то лежит,
кроме личной памяти; метки жителей — только жителям):

  1. Ниточка «Жители · метки» уходит в чулан — Архив меток не видит.
  2. Ниточка «Склад Архива» смотрит туда, где склад лежит на самом деле
     (GRONDHEIM_CITY/Архив/архив/каталог.json).
  3. «Книги города» видят корень, Академию и Биржа/документы.
  4. Каждая ниточка умеет искать по слову (nayti).
  5. Реестр памятей умеет искать по всем ниточкам сразу (nayti_vezde) —
     будущая рука Хранителя.
  6. В окне «Памяти города» на странице Архива — поле поиска.

Архив по-прежнему ничего к себе не тащит и в дома жителей не ходит.

Запуск: из корня репы (или двойным кликом — окно подождёт Enter).
Повторный запуск ничего не ломает. Копии — рядом, с хвостом .bak_nitochki.
"""
import ast
import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "NITOCHKI_POISK_V1"
BAK = ".bak_nitochki"


# ═══════════════════════════════════════════════════════════
# ГДЕ КОРЕНЬ — ищем сами, руками путь не вбиваем
# ═══════════════════════════════════════════════════════════

def _eto_koren(p: Path) -> bool:
    return (p / "Архив" / "pamyat.py").is_file() and (p / "Архив" / "памяти").is_dir()


def naiti_koren():
    kandidaty = [Path(__file__).resolve().parent, Path.cwd()]
    for k in list(kandidaty):
        kandidaty.extend(list(k.parents)[:3])
    for k in kandidaty:
        if _eto_koren(k):
            return k
    return None


# ═══════════════════════════════════════════════════════════
# НОВОЕ СОДЕРЖИМОЕ НИТОЧЕК
# ═══════════════════════════════════════════════════════════

POISK = r'''# -*- coding: utf-8 -*-
# NITOCHKI_POISK_V1 — общий кусочек для ниточек Архива.
# Имя начинается с подчёркивания: реестр (pamyat.py) такой файл
# ниточкой не считает.
"""Поиск по слову для ниточек Архива.

Все слова запроса должны быть в тексте (регистр не важен, часть слова
тоже годится: «дивер» найдёт «дивергенция»). В ответ — кусок текста
вокруг первого найденного слова, а не вся запись.
"""
from datetime import datetime


def slova(zapros: str) -> list:
    return [s for s in (zapros or "").lower().split() if s]


def podhodit(tekst: str, sl: list) -> bool:
    if not sl:
        return False
    t = (tekst or "").lower()
    return all(s in t for s in sl)


def kusok(tekst: str, sl: list, shir: int = 180) -> str:
    t = " ".join((tekst or "").split())
    if not sl:
        return t[: shir * 2]
    i = t.lower().find(sl[0])
    if i < 0:
        return t[: shir * 2]
    nach = max(0, i - shir)
    kon = min(len(t), i + len(sl[0]) + shir)
    out = t[nach:kon]
    if nach > 0:
        out = "…" + out
    if kon < len(t):
        out = out + "…"
    return out


def vremya(kogda) -> str:
    """Время записи по-человечески: число секунд тоже переводим."""
    try:
        if isinstance(kogda, (int, float)) or (
                isinstance(kogda, str) and kogda.replace(".", "", 1).isdigit()):
            return datetime.fromtimestamp(float(kogda)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return str(kogda or "")[:16]
'''

SDELKI = r'''# -*- coding: utf-8 -*-
"""ПАМЯТЬ: сделки Биржи — атлас случаев и результат по деньгам."""
# NITOCHKI_POISK_V1: поиск по полной записи (nayti)
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import _nitochki_poisk as _p

ИМЯ = "Биржа · сделки"
_D = Path(__file__).resolve().parents[2] / "GRONDHEIM_CITY" / "Биржа" / "данные"


def _faily():
    if not _D.is_dir():
        return []
    return [p for p in _D.glob("*.jsonl")
            if p.name.startswith(("atlas_trading", "trading_pnl"))
            and "archive" not in p.name]


def _kogda(d: dict) -> str:
    return _p.vremya(d.get("ts") or d.get("время") or d.get("когда")
                     or d.get("timestamp") or "")


def _zapisi_faila(f):
    try:
        stroki = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return
    for s in stroki:
        try:
            d = json.loads(s)
        except Exception:
            continue
        if isinstance(d, dict):
            yield d


def est() -> bool:
    return bool(_faily())


def zapisi(predel: int = 200) -> list:
    out = []
    for f in _faily():
        for d in list(_zapisi_faila(f))[-predel:]:
            out.append({
                "когда": _kogda(d),
                "что": (d.get("итог") or d.get("вердикт") or d.get("сигнал")
                        or json.dumps(d, ensure_ascii=False))[:220],
                "откуда": f.name})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]


def nayti(zapros: str, predel: int = 30) -> list:
    sl = _p.slova(zapros)
    if not sl:
        return []
    out = []
    for f in _faily():
        for d in _zapisi_faila(f):
            tekst = json.dumps(d, ensure_ascii=False)
            if _p.podhodit(tekst, sl):
                out.append({"когда": _kogda(d), "что": _p.kusok(tekst, sl),
                            "откуда": f.name})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]
'''

DNEVNIKI = r'''# -*- coding: utf-8 -*-
"""ПАМЯТЬ: дневники рабочих мест — что делал на посту и почему.

Это журнал МЕСТА (как трудовая книжка), не дом жителя. В дома жителей
(папка «жители») Архив не заходит никогда — там личное.
"""
# NITOCHKI_POISK_V1: поиск по полной записи (nayti), дома жителей закрыты
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import _nitochki_poisk as _p

ИМЯ = "Дневники работников"
_CITY = Path(__file__).resolve().parents[2] / "GRONDHEIM_CITY"


def _faily():
    if not _CITY.is_dir():
        return []
    return sorted(p for p in _CITY.rglob("данные/diary_*.jsonl")
                  if "жители" not in p.parts)


def _mesto(f: Path) -> str:
    chasti = f.parts
    return chasti[-3] if len(chasti) > 3 else ""


def _zapisi_faila(f):
    try:
        stroki = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return
    for s in stroki:
        try:
            d = json.loads(s)
        except Exception:
            continue
        if isinstance(d, dict):
            yield d


def _kogda(d: dict) -> str:
    return _p.vremya(d.get("ts") or d.get("когда") or d.get("время") or "")


def est() -> bool:
    return bool(_faily())


def zapisi(predel: int = 200) -> list:
    out = []
    for f in _faily():
        for d in list(_zapisi_faila(f))[-predel:]:
            zapis = d.get("diary_entry") or d
            out.append({
                "когда": _kogda(d),
                "что": (str(zapis.get("action") or zapis.get("что") or "")[:220]
                        or json.dumps(zapis, ensure_ascii=False)[:220]),
                "откуда": f"{_mesto(f)} · {f.name}"})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]


def nayti(zapros: str, predel: int = 30) -> list:
    sl = _p.slova(zapros)
    if not sl:
        return []
    out = []
    for f in _faily():
        for d in _zapisi_faila(f):
            tekst = json.dumps(d, ensure_ascii=False)
            if _p.podhodit(tekst, sl):
                out.append({"когда": _kogda(d), "что": _p.kusok(tekst, sl),
                            "откуда": f"{_mesto(f)} · {f.name}"})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]
'''

KNIGI = r'''# -*- coding: utf-8 -*-
"""ПАМЯТЬ: книги города — летопись, чертёж, законы кварталов, документы.

Полки, которые Архив видит (без спуска вглубь): корень города, Академия,
Биржа/документы. В дома жителей, в папку Брата и в чулан Архив не ходит.
"""
# NITOCHKI_POISK_V1: полки шире, поиск внутри текста (nayti)
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import _nitochki_poisk as _p

ИМЯ = "Книги города"
_KOREN = Path(__file__).resolve().parents[2]
_POLKI = [_KOREN, _KOREN / "Академия", _KOREN / "Биржа" / "документы"]
_VIDY = (".md", ".txt")
_NA_KNIGU = 8          # сколько кусков брать из одной книги при поиске


def _faily():
    out = []
    for polka in _POLKI:
        if not polka.is_dir():
            continue
        for p in sorted(polka.iterdir()):
            try:
                if (p.is_file() and p.suffix.lower() in _VIDY
                        and p.stat().st_size > 800):
                    out.append(p)
            except Exception:
                continue
    return out


def _gde(p: Path) -> str:
    try:
        rel = p.relative_to(_KOREN)
    except Exception:
        return p.name
    return "корень города" if str(rel.parent) == "." else str(rel.parent).replace("\\", "/")


def _kogda(p: Path) -> str:
    try:
        return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _tekst(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="cp1251")
        except Exception:
            return ""
    except Exception:
        return ""


def est() -> bool:
    return bool(_faily())


def zapisi(predel: int = 200) -> list:
    out = []
    for f in _faily():
        razmer = f.stat().st_size // 1024
        pervaya = ""
        for s in _tekst(f).splitlines():
            if s.strip() and not s.startswith("#"):
                pervaya = s.strip()[:160]
                break
        out.append({"когда": _kogda(f),
                    "что": f"{f.name} · {razmer} КБ — {pervaya}",
                    "откуда": _gde(f)})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]


def _abzacy(tekst: str):
    """(заголовок раздела, абзац) — абзацы по пустым строкам."""
    razdel = ""
    kusok = []
    for s in tekst.splitlines():
        if s.lstrip().startswith("#"):
            if kusok:
                yield razdel, "\n".join(kusok)
                kusok = []
            razdel = s.strip().lstrip("#").strip()
            continue
        if not s.strip():
            if kusok:
                yield razdel, "\n".join(kusok)
                kusok = []
            continue
        kusok.append(s)
    if kusok:
        yield razdel, "\n".join(kusok)


def nayti(zapros: str, predel: int = 30) -> list:
    sl = _p.slova(zapros)
    if not sl:
        return []
    out = []
    for f in _faily():
        kogda = _kogda(f)
        naydeno = 0
        for razdel, abzac in _abzacy(_tekst(f)):
            if not _p.podhodit(razdel + " " + abzac, sl):
                continue
            gde = f.name + (f" · {razdel[:80]}" if razdel else "")
            out.append({"когда": kogda, "что": _p.kusok(abzac, sl, 220),
                        "откуда": gde})
            naydeno += 1
            if naydeno >= _NA_KNIGU:
                break
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]
'''

MAYAK = r'''# -*- coding: utf-8 -*-
"""ПАМЯТЬ: Маяк — кто и когда откликался с той стороны."""
# NITOCHKI_POISK_V1: поиск по полной записи (nayti)
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import _nitochki_poisk as _p

ИМЯ = "Маяк · пульсы и гнёзда"
_M = Path(__file__).resolve().parents[2] / "Маяк"


def _faily():
    if not _M.is_dir():
        return []
    return sorted(_M.rglob("пульсы.jsonl"))


def _zapisi_faila(f):
    try:
        stroki = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return
    for s in stroki:
        try:
            d = json.loads(s)
        except Exception:
            continue
        if isinstance(d, dict):
            yield d


def est() -> bool:
    return bool(_faily()) or (_M / "острова").is_dir()


def zapisi(predel: int = 200) -> list:
    out = []
    for f in _faily():
        kto = f.parent.name
        for d in list(_zapisi_faila(f))[-predel:]:
            out.append({
                "когда": _p.vremya(d.get("когда") or d.get("time") or ""),
                "что": json.dumps({k: v for k, v in d.items()
                                   if k not in ("когда", "time")},
                                  ensure_ascii=False)[:220],
                "откуда": kto})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]


def nayti(zapros: str, predel: int = 30) -> list:
    sl = _p.slova(zapros)
    if not sl:
        return []
    out = []
    for f in _faily():
        kto = f.parent.name
        for d in _zapisi_faila(f):
            tekst = json.dumps(d, ensure_ascii=False)
            if _p.podhodit(tekst + " " + kto, sl):
                out.append({"когда": _p.vremya(d.get("когда") or d.get("time") or ""),
                            "что": _p.kusok(tekst, sl), "откуда": kto})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]
'''

POSTY = r'''# -*- coding: utf-8 -*-
"""ПАМЯТЬ: трудовые истории мест — кого принимали и за что снимали."""
# NITOCHKI_POISK_V1: поиск (nayti)
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import _nitochki_poisk as _p

ИМЯ = "Трудовые истории мест"
_P = Path(__file__).resolve().parents[2] / "GRONDHEIM_CITY" / "посты"


def est() -> bool:
    return _P.is_dir() and any(_P.glob("*/пост.json"))


def _vse():
    for f in sorted(_P.glob("*/пост.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        nazv = d.get("название", f.parent.name)
        for z in d.get("трудовая_история", []) or []:
            if isinstance(z, dict):
                yield nazv, z


def _stroka(z: dict) -> str:
    pochemu = f" — {z.get('почему')}" if z.get("почему") else ""
    return f"{z.get('что','')}: {z.get('кто','')}{pochemu}"


def zapisi(predel: int = 200) -> list:
    out = [{"когда": str(z.get("когда", ""))[:16], "что": _stroka(z),
            "откуда": nazv} for nazv, z in _vse()]
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]


def nayti(zapros: str, predel: int = 30) -> list:
    sl = _p.slova(zapros)
    if not sl:
        return []
    out = []
    for nazv, z in _vse():
        tekst = f"{nazv} · " + json.dumps(z, ensure_ascii=False)
        if _p.podhodit(tekst, sl):
            out.append({"когда": str(z.get("когда", ""))[:16],
                        "что": _stroka(z), "откуда": nazv})
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]
'''

SKLAD = r'''# -*- coding: utf-8 -*-
"""ПАМЯТЬ: собственный склад Архива — то, что принесли рудой.

Раньше он был единственным. Теперь — одна память среди прочих.
Лежит там же, где его пишет кабинет Архива и Хранитель:
GRONDHEIM_CITY/Архив/архив/каталог.json.
"""
# NITOCHKI_POISK_V1: путь к складу починен, поиск (nayti)
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import _nitochki_poisk as _p

ИМЯ = "Склад Архива"
_K = (Path(__file__).resolve().parents[2] / "GRONDHEIM_CITY" / "Архив"
      / "архив" / "каталог.json")


def est() -> bool:
    return _K.is_file()


def _vse():
    try:
        d = json.loads(_K.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [z for z in (d.get("записи") or []) if isinstance(z, dict)]


def _zapis(z: dict) -> dict:
    return {"когда": str(z.get("когда") or z.get("дата", ""))[:16],
            "что": str(z.get("название") or z.get("что", ""))[:220],
            "откуда": str(z.get("раздел", ""))}


def zapisi(predel: int = 200) -> list:
    out = [_zapis(z) for z in _vse()]
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]


def nayti(zapros: str, predel: int = 30) -> list:
    sl = _p.slova(zapros)
    if not sl:
        return []
    out = []
    for z in _vse():
        seno = " ".join([str(z.get("название", "")), str(z.get("раздел", "")),
                         " ".join(z.get("теги", []) or []),
                         str(z.get("файл", "")), str(z.get("описание", ""))])
        if _p.podhodit(seno, sl):
            r = _zapis(z)
            if z.get("описание"):
                r["что"] = r["что"] + " — " + _p.kusok(str(z["описание"]), sl)
            out.append(r)
    out.sort(key=lambda x: x["когда"], reverse=True)
    return out[:predel]
'''

# Что в ниточке должно быть, чтобы её можно было переписать без спроса
NITOCHKI = [
    # (имя файла, новое содержимое, примета старого файла)
    ("birzha_sdelki.py", SDELKI, 'ИМЯ = "Биржа · сделки"'),
    ("dnevniki.py", DNEVNIKI, 'ИМЯ = "Дневники работников"'),
    ("knigi.py", KNIGI, 'ИМЯ = "Книги города"'),
    ("mayak.py", MAYAK, 'ИМЯ = "Маяк · пульсы и гнёзда"'),
    ("posty.py", POSTY, 'ИМЯ = "Трудовые истории мест"'),
    ("sklad_arkhiva.py", SKLAD, 'ИМЯ = "Склад Архива"'),
]


# ═══════════════════════════════════════════════════════════
# ДОБАВКА В РЕЕСТР (Архив/pamyat.py)
# ═══════════════════════════════════════════════════════════

PAMYAT_DOBAVKA = r'''

# NITOCHKI_POISK_V1 — один поиск по всем ниточкам сразу.
# Это будущая рука Хранителя Архива: «найди везде». Личной памяти
# среди ниточек нет, поэтому и в поиск она не попадёт.
def nayti_vezde(zapros: str, predel: int = 20) -> list:
    """[{ключ, имя, найдено: [{когда, что, откуда}]}] — только те ниточки,
    где что-то нашлось. Ниточка без своего поиска — ищем в её последних
    записях по тексту. Сломанная ниточка не роняет весь поиск."""
    zapros = (zapros or "").strip()
    if not zapros:
        return []
    sl = [s for s in zapros.lower().split() if s]
    out = []
    for p in vse():
        m = p["модуль"]
        try:
            if hasattr(m, "nayti"):
                naydeno = m.nayti(zapros, predel)
            else:
                naydeno = [z for z in m.zapisi(1000)
                           if all(s in (str(z.get("что", "")) + " "
                                        + str(z.get("откуда", ""))).lower()
                                  for s in sl)][:predel]
        except Exception as e:
            naydeno = [{"когда": "", "что": f"ниточка не ответила: {e}",
                        "откуда": ""}]
        if naydeno:
            out.append({"ключ": p["ключ"], "имя": p["имя"], "найдено": naydeno})
    return out
'''


# ═══════════════════════════════════════════════════════════
# ДОБАВКА НА СТРАНИЦУ АРХИВА (Архив/ui_arkhiv.py)
# ═══════════════════════════════════════════════════════════

UI_YAKOR = '''            for p in spisok:
                ui.button(p["имя"], on_click=lambda p=p: _otkryt(p)).props('''

UI_VSTAVKA = '''            # NITOCHKI_POISK_V1: поиск по всем памятям города сразу
            _pole = ui.input(placeholder="найти по всем памятям…").props(
                "dense outlined dark").style(
                "width:100%; margin-bottom:6px;")

            def _iskat():
                q = (_pole.value or "").strip()
                if not q:
                    ui.notify("Напиши, что искать", color="warning")
                    return
                try:
                    gruppy = _pam.nayti_vezde(q, 20)
                except Exception as e:
                    ui.notify(f"⚠ поиск не удался: {e}", color="negative")
                    return
                stroki = [f"# 🔎 {q}", ""]
                if not gruppy:
                    stroki.append("*нигде не нашлось — ни в одной памяти города*")
                for g in gruppy:
                    stroki.append(f'## {g["имя"]} — {len(g["найдено"])}')
                    stroki.append("")
                    for z in g["найдено"]:
                        kogda = z.get("когда") or "—"
                        otkuda = (f'  ·  `{z.get("откуда","")}`'
                                  if z.get("откуда") else "")
                        stroki.append(f'**{kogda}**{otkuda}  \\n{z.get("что","")}')
                        stroki.append("")
                update_viewer("\\n".join(stroki))
                dlg.close()

            _pole.on("keydown.enter", lambda: _iskat())
            ui.button("🔎 искать везде", on_click=_iskat).props(
                "flat no-caps").style(
                "width:100%; padding:8px 12px; border-radius:8px; "
                "margin-bottom:12px; font-size:0.8rem; "
                "color:rgba(201,168,76,0.95); "
                "background:rgba(201,168,76,0.10);")

'''


# ═══════════════════════════════════════════════════════════
# РАБОТА
# ═══════════════════════════════════════════════════════════

def _kopiya(p: Path):
    k = p.with_name(p.name + BAK)
    if not k.exists():
        shutil.copy2(p, k)
    return k


def _zapisat_proveriv(p: Path, tekst: str) -> bool:
    """Пишем, только если Python понимает текст; после записи — компиляция.
    Не прошло — возвращаем старое из копии."""
    try:
        ast.parse(tekst)
    except SyntaxError as e:
        print(f"   ✗ {p.name}: текст не собрался ({e}) — не пишу")
        return False
    staroe = p.read_text(encoding="utf-8") if p.exists() else None
    p.write_text(tekst, encoding="utf-8")
    try:
        py_compile.compile(str(p), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"   ✗ {p.name}: не компилируется ({e}) — возвращаю как было")
        if staroe is None:
            p.unlink()
        else:
            p.write_text(staroe, encoding="utf-8")
        return False
    return True


def main():
    koren = naiti_koren()
    if koren is None:
        print("✗ Не нашёл корень города (нет Архив/pamyat.py рядом).")
        print("  Положи патч в корень репы и запусти оттуда.")
        return
    print(f"Корень города: {koren}\n")

    arkhiv = koren / "Архив"
    pamyati = arkhiv / "памяти"
    oshibki = 0

    # 0. общий кусочек поиска
    p = pamyati / "_nitochki_poisk.py"
    if p.exists() and MARKER in p.read_text(encoding="utf-8"):
        print("• поиск для ниточек — уже стоит")
    elif _zapisat_proveriv(p, POISK):
        print("✓ поиск для ниточек — положен (Архив/памяти/_nitochki_poisk.py)")
    else:
        oshibki += 1

    # 1. метки жителей — в чулан
    p = pamyati / "zhiteli.py"
    if p.exists():
        chulan = koren / "_ЧУЛАН" / "старое" / "arkhiv_nitochki_1"
        chulan.mkdir(parents=True, exist_ok=True)
        kuda = chulan / "zhiteli.py"
        if kuda.exists():
            kuda = chulan / f"zhiteli_{datetime.now():%Y%m%d_%H%M%S}.py"
        shutil.move(str(p), str(kuda))
        print("✓ «Жители · метки» — убрана в чулан: метки только жителям")
    else:
        print("• «Жители · метки» — уже убрана")

    # 2-4. ниточки
    for imya, novoe, primeta in NITOCHKI:
        p = pamyati / imya
        if not p.exists():
            if _zapisat_proveriv(p, novoe):
                print(f"✓ {imya} — не было, положена новая")
            else:
                oshibki += 1
            continue
        staroe = p.read_text(encoding="utf-8")
        if MARKER in staroe:
            print(f"• {imya} — уже с поиском")
            continue
        if primeta not in staroe:
            print(f"✗ {imya} — не похожа на ту, что я знаю, не трогаю "
                  f"(нет строки {primeta})")
            oshibki += 1
            continue
        _kopiya(p)
        if _zapisat_proveriv(p, novoe):
            print(f"✓ {imya} — переписана, умеет искать")
        else:
            oshibki += 1

    # 5. реестр — поиск везде
    p = arkhiv / "pamyat.py"
    tekst = p.read_text(encoding="utf-8")
    if MARKER in tekst:
        print("• pamyat.py — поиск везде уже стоит")
    elif "def vse(" not in tekst:
        print("✗ pamyat.py — не нашёл в нём vse(), не трогаю")
        oshibki += 1
    else:
        _kopiya(p)
        if _zapisat_proveriv(p, tekst.rstrip() + "\n" + PAMYAT_DOBAVKA):
            print("✓ pamyat.py — умеет искать по всем ниточкам сразу")
        else:
            oshibki += 1

    # 6. страница Архива — поле поиска
    p = arkhiv / "ui_arkhiv.py"
    tekst = p.read_text(encoding="utf-8")
    if MARKER in tekst:
        print("• ui_arkhiv.py — поле поиска уже стоит")
    else:
        skolko = tekst.count(UI_YAKOR)
        if skolko != 1:
            print(f"✗ ui_arkhiv.py — место для поля поиска найдено {skolko} раз "
                  "(нужно ровно 1), не трогаю")
            oshibki += 1
        else:
            _kopiya(p)
            novoe = tekst.replace(UI_YAKOR, UI_VSTAVKA + UI_YAKOR, 1)
            if _zapisat_proveriv(p, novoe):
                print("✓ ui_arkhiv.py — в окне «Памяти города» поле поиска")
            else:
                oshibki += 1

    print()
    if oshibki:
        print(f"Готово с замечаниями: {oshibki}. Пришли Брату, что выше.")
    else:
        print("Готово. Перезапусти город → Архив → «Памяти города» → поиск.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            input("\nEnter — закрыть окно")
        except EOFError:
            pass
