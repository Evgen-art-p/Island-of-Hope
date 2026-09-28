# -*- coding: utf-8 -*-
# skaner_goroda.py — СКАНЕР ГОРОДА (глаза Брата, этап 1: факты кодом)
# Маркер: SKANER_GORODA_V4 (V2: прогоны одной строкой; V3: годится и острову;
#          V4: _ПЕРЕЕЗД — как чулан, старые копии не считаются живым кодом)
"""
Обходит весь город и пишет один отчёт простыми словами:
Брат/отчёты/ГОРОД.md  — сам отчёт (всегда свежий)
Брат/отчёты/снимок.json — слепок города, чтобы в следующий раз сказать,
                           что изменилось.

Здесь нет модели и нет догадок — только то, что можно проверить:
файлы, размеры, даты, что объявлено в коде, кто кого зовёт, какие
страницы есть, кто на каком посту, что не собирается и какие данные
битые. Толкование (мнение Брата) — отдельным этапом, рядом, с пометкой.

Чего в отчёте нет никогда:
  • содержимого домов жителей — только что дом есть и сколько в нём файлов;
  • ключей и паролей — файл .env не открывается вовсе;
  • переписки (чатов) — только их число.

Запуск: двойной клик по файлу (он в папке Брат/), окно подождёт Enter.
Или из корня репы: python Брат/skaner_goroda.py
Ничего в городе не меняет, пишет только в Брат/отчёты/.
"""
import ast
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

VERSIYA = "SKANER_GORODA_V4"

# Куда не ходим вовсе (служебное, не город)
_MIMO = {".git", "__pycache__", ".venv", "venv", "env", "node_modules",
         ".mypy_cache", ".pytest_cache", ".idea"}
# Код и тексты
_KOD = {".py"}
_TEKSTY = {".md", ".txt"}
_DANNYE = {".json", ".jsonl"}
_KARTINKI = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
_ZVUK_VIDEO = {".mp3", ".wav", ".ogg", ".mp4", ".webm", ".mov", ".m4a"}

_KLYUCH = re.compile(r"(sk-[A-Za-z0-9_\-]{12,}|tvly-[A-Za-z0-9_\-]{12,}|"
                     r"AIza[0-9A-Za-z_\-]{20,})")
_METKA_PATCHA = re.compile(r"\b[A-Z][A-Z0-9_]{3,}_V\d+\b")


# ═══════════════════════════════════════════════════════════
# ГДЕ КОРЕНЬ
# ═══════════════════════════════════════════════════════════

def naiti_koren():
    kandidaty = [Path(__file__).resolve().parent, Path.cwd()]
    for k in list(kandidaty):
        kandidaty.extend(list(k.parents)[:3])
    for k in kandidaty:
        if ((k / "main.py").is_file() or (k / "ostrov_main.py").is_file()) \
                and (k / "GRONDHEIM_CITY").is_dir():
            return k
    return None


# ═══════════════════════════════════════════════════════════
# МЕЛОЧИ
# ═══════════════════════════════════════════════════════════

def _razmer(n: int) -> str:
    for ed in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or ed == "ГБ":
            return f"{n:.0f} {ed}" if ed == "Б" else f"{n:.1f} {ed}"
        n /= 1024
    return str(n)


def _data(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _chitat(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="cp1251")
        except Exception:
            return ""
    except Exception:
        return ""


def _bez_klyuchey(t: str) -> str:
    return _KLYUCH.sub("[ключ скрыт]", t)


def _odna_stroka(t: str, n: int = 160) -> str:
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _eto_bak(p: Path) -> bool:
    return ".bak" in p.name


# Кладовые: там лежат старые копии, а не живой город. Код, документы и
# данные оттуда в отчёт не идут (в общем счёте файлов они есть).
_KLADOVYE = ("_ЧУЛАН", "_ПЕРЕЕЗД")


def _v_kladovoy(rel: str) -> bool:
    return rel.split("/", 1)[0] in _KLADOVYE


def _progony(rel: str):
    """Для файла внутри папки «прогоны»: (путь до «прогоны», имя прогона).
    Иначе None. Прогонов десятки, в отчёте они идут одной строкой."""
    ch = rel.split("/")
    if "прогоны" in ch:
        i = ch.index("прогоны")
        if i + 1 < len(ch) - 1:
            return "/".join(ch[: i + 1]), ch[i + 1]
    return None


def _svodka_progonov(spisok) -> list:
    """spisok: [(rel, size, mtime)] → строки «N прогонов, с … по …»."""
    gruppy = defaultdict(lambda: {"прогоны": set(), "файлов": 0, "вес": 0, "m": 0.0})
    for r, s, m in spisok:
        pr = _progony(r)
        if not pr:
            continue
        g = gruppy[pr[0]]
        g["прогоны"].add(pr[1])
        g["файлов"] += 1
        g["вес"] += s
        g["m"] = max(g["m"], m)
    out = []
    for papka, g in sorted(gruppy.items()):
        imena = sorted(g["прогоны"])
        out.append(f"`{papka}/` — {len(imena)} прогонов, {g['файлов']} файлов, "
                   f"{_razmer(g['вес'])}; первый `{imena[0]}`, последний "
                   f"`{imena[-1]}` (изменён {_data(g['m'])})")
    return out


# ═══════════════════════════════════════════════════════════
# ОБХОД
# ═══════════════════════════════════════════════════════════

class Gorod:
    def __init__(self, koren: Path):
        self.k = koren
        self.faily = []          # (путь от корня, Path, размер, mtime)
        self.doma = {}           # имя жителя -> {"файлов":n, "этажи":[...], "чатов":n}
        self.env_est = False

    def rel(self, p: Path) -> str:
        return str(p.relative_to(self.k)).replace("\\", "/")

    def dom_zhitelya(self, p: Path):
        """Имя жителя, если файл лежит в его доме, иначе None."""
        ch = p.relative_to(self.k).parts
        if (len(ch) >= 4 and ch[0] == "GRONDHEIM_CITY" and ch[1] == "жители"
                and ch[2] == "ковчег"):
            return ch[3]
        return None

    def oboyti(self):
        stek = [self.k]
        while stek:
            d = stek.pop()
            try:
                vnutri = list(d.iterdir())
            except Exception:
                continue
            for p in vnutri:
                if p.name in _MIMO:
                    continue
                if p.is_dir():
                    stek.append(p)
                    continue
                if p.name == ".env":
                    self.env_est = True
                    continue            # ключи не трогаем вовсе
                try:
                    st = p.stat()
                except Exception:
                    continue
                zhitel = self.dom_zhitelya(p)
                if zhitel:
                    dom = self.doma.setdefault(zhitel, {"файлов": 0, "этажи": set(),
                                                        "чатов": 0, "размер": 0})
                    dom["файлов"] += 1
                    dom["размер"] += st.st_size
                    chasti = p.relative_to(self.k).parts
                    if len(chasti) > 5:
                        dom["этажи"].add(chasti[4])
                    if "чат" in p.name:
                        dom["чатов"] += 1
                self.faily.append((self.rel(p), p, st.st_size, st.st_mtime))
        self.faily.sort(key=lambda x: x[0])


# ═══════════════════════════════════════════════════════════
# КОД
# ═══════════════════════════════════════════════════════════

def razobrat_kod(g: Gorod):
    """По каждому .py: описание, строки, метки патчей, что объявлено,
    кого зовёт, собирается ли."""
    kod = [(r, p, s, m) for r, p, s, m in g.faily
           if p.suffix == ".py" and not _eto_bak(p) and not _v_kladovoy(r)
           and not g.dom_zhitelya(p)]
    po_imeni = defaultdict(list)
    for r, p, s, m in kod:
        po_imeni[p.stem].append(r)
    # Файл, названный как стандартный модуль Python (например csv.py):
    # «import csv» у других почти всегда про стандартный модуль,
    # поэтому связь по такому имени не считаем — только отмечаем.
    std = set(getattr(sys, "stdlib_module_names", ()))
    svoi = {imya for imya in po_imeni if imya not in std}

    svedeniya = {}
    for r, p, s, m in kod:
        tekst = _chitat(p)
        info = {"строк": tekst.count("\n") + 1, "размер": s, "mtime": m,
                "описание": "", "метки": [], "функций": 0, "классов": 0,
                "зовёт": set(), "сам_запускается": "__main__" in tekst,
                "грузит_по_пути": "spec_from_file_location" in tekst,
                "страницы": [], "ошибка": ""}
        info["метки"] = sorted(set(_METKA_PATCHA.findall(tekst)))
        for i, stroka in enumerate(tekst.splitlines(), 1):
            mm = re.search(r'@ui\.page\(\s*["\']([^"\']+)["\']', stroka)
            if mm and not stroka.lstrip().startswith("#"):
                info["страницы"].append((mm.group(1), i))
        try:
            derevo = ast.parse(tekst)
        except SyntaxError as e:
            info["ошибка"] = f"строка {e.lineno}: {e.msg}"
            svedeniya[r] = info
            continue
        doc = ast.get_docstring(derevo) or ""
        if not doc:
            # описание часто лежит комментарием в первых строках
            kom = [s.lstrip("# ").strip() for s in tekst.splitlines()[:8]
                   if s.startswith("#") and not s.startswith("#!")
                   and "coding" not in s]
            doc = " ".join(k for k in kom if k)
        doc = re.sub(r"[─━═—\-=]{4,}", " ", doc)
        info["описание"] = _odna_stroka(_bez_klyuchey(doc), 180)
        for uzel in ast.walk(derevo):
            if isinstance(uzel, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info["функций"] += 1
            elif isinstance(uzel, ast.ClassDef):
                info["классов"] += 1
            elif isinstance(uzel, ast.Import):
                for a in uzel.names:
                    for chast in a.name.split("."):
                        if chast in svoi and chast != p.stem:
                            info["зовёт"].add(chast)
            elif isinstance(uzel, ast.ImportFrom):
                imena = (uzel.module or "").split(".") + [a.name for a in uzel.names]
                for chast in imena:
                    if chast in svoi and chast != p.stem:
                        info["зовёт"].add(chast)
        svedeniya[r] = info

    # обратная связь: кто зовёт этот файл
    zovut = defaultdict(set)
    for r, info in svedeniya.items():
        for imya in info["зовёт"]:
            zovut[imya].add(Path(r).stem)
    return svedeniya, zovut, po_imeni


# ═══════════════════════════════════════════════════════════
# ЛЮДИ, ПОСТЫ, МЕСТА
# ═══════════════════════════════════════════════════════════

def posty(g: Gorod) -> list:
    out = []
    for f in sorted((g.k / "GRONDHEIM_CITY" / "посты").glob("*/пост.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            out.append({"название": f.parent.name, "кто": "?", "где": "",
                        "битый": True})
            continue
        kto = d.get("кто_сидит")
        imya = kto.get("имя", "?") if isinstance(kto, dict) else ""
        s = kto.get("с", "") if isinstance(kto, dict) else ""
        mesto = " · ".join(x for x in [d.get("квартал", ""), d.get("цех", ""),
                                       d.get("слот", "")] if x)
        out.append({"название": d.get("название", f.parent.name), "кто": imya,
                    "с": str(s)[:10], "где": mesto or d.get("локация", ""),
                    "битый": False})
    return out


def mesta(g: Gorod) -> list:
    out = []
    for d in sorted((g.k / "GRONDHEIM_CITY" / "локации").iterdir()
                    if (g.k / "GRONDHEIM_CITY" / "локации").is_dir() else []):
        if not d.is_dir():
            continue
        imya = ""
        pas = d / "passport.json"
        if pas.is_file():
            try:
                imya = json.loads(pas.read_text(encoding="utf-8")).get("Official_Name", "")
            except Exception:
                imya = "(паспорт не читается)"
        out.append((d.name, imya))
    return out


# ═══════════════════════════════════════════════════════════
# ДАННЫЕ И ТЕКСТЫ
# ═══════════════════════════════════════════════════════════

def proverit_dannye(g: Gorod):
    """Все .json/.jsonl вне домов жителей и чулана: целы ли."""
    bitye = []
    krupnye = []
    for r, p, s, m in g.faily:
        if p.suffix not in _DANNYE or g.dom_zhitelya(p) or _v_kladovoy(r) \
                or _eto_bak(p):
            continue
        if p.suffix == ".json":
            if s > 30 * 1024 * 1024:
                continue
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                bitye.append((r, _odna_stroka(str(e), 90)))
            krupnye.append((r, s, m, None))
        else:
            vsego = plohih = 0
            try:
                with p.open(encoding="utf-8", errors="replace") as fh:
                    for stroka in fh:
                        if not stroka.strip():
                            continue
                        vsego += 1
                        try:
                            json.loads(stroka)
                        except Exception:
                            plohih += 1
            except Exception as e:
                bitye.append((r, _odna_stroka(str(e), 90)))
            if plohih:
                bitye.append((r, f"{plohih} битых строк из {vsego}"))
            krupnye.append((r, s, m, vsego))
    krupnye.sort(key=lambda x: -x[1])
    return bitye, krupnye


def zagolovki(p: Path, n: int = 8) -> list:
    out = []
    for s in _chitat(p).splitlines():
        if s.startswith("## ") or s.startswith("# "):
            out.append(_odna_stroka(_bez_klyuchey(s.lstrip("#").strip()), 90))
            if len(out) >= n:
                break
    return out


# ═══════════════════════════════════════════════════════════
# СНИМОК И РАЗНИЦА
# ═══════════════════════════════════════════════════════════

def _otpechatok(p: Path, s: int) -> str:
    if s > 20 * 1024 * 1024:
        return f"size:{s}"
    try:
        return hashlib.sha1(p.read_bytes()).hexdigest()[:16]
    except Exception:
        return f"size:{s}"


def snyat_snimok(g: Gorod) -> dict:
    return {r: _otpechatok(p, s) for r, p, s, m in g.faily}


def raznitsa(staryy: dict, novyy: dict, g: Gorod):
    novye = sorted(set(novyy) - set(staryy))
    ushli = sorted(set(staryy) - set(novyy))
    menyalis = sorted(r for r in set(novyy) & set(staryy) if novyy[r] != staryy[r])

    def razlozhit(spisok):
        obshchee, doma = [], Counter()
        for r in spisok:
            ch = r.split("/")
            if len(ch) >= 4 and ch[0] == "GRONDHEIM_CITY" and ch[1] == "жители" \
                    and ch[2] == "ковчег":
                doma[ch[3]] += 1      # в домах — только число, без имён файлов
            else:
                obshchee.append(r)
        return obshchee, doma

    return razlozhit(novye), razlozhit(ushli), razlozhit(menyalis)


# ═══════════════════════════════════════════════════════════
# ОТЧЁТ
# ═══════════════════════════════════════════════════════════

def napisat(g: Gorod, snimok_star: dict, snimok_nov: dict, kogda_star: str) -> str:
    L = []
    w = L.append
    seychas = datetime.now().strftime("%Y-%m-%d %H:%M")
    kod, zovut, po_imeni = razobrat_kod(g)
    bitye, krupnye = proverit_dannye(g)

    ostrov = (g.k / "ostrov_main.py").is_file() and not (g.k / "main.py").is_file()
    vhod = "ostrov_main.py" if ostrov else "main.py"
    w(f"# Отчёт об острове {g.k.name}" if ostrov else "# Отчёт о городе Грондхейм")
    w("")
    w(f"*Снят: {seychas} · сканер Брата ({VERSIYA}) · корень: `{g.k.name}`*")
    w("")
    w("## Как читать этот отчёт")
    w("")
    w("Грондхейм — город на Python, где живут цифровые жители: у каждого есть "
      "паспорт, память и работа. Город растёт руками его хозяина (Шефа) и "
      "Брата — помощника-архитектора. Этот отчёт — карта для любого, "
      "кто пришёл помочь: человека или модели.")
    w("")
    if ostrov:
        w("Это остров — отдельный мир за Маяком, клон части города (здесь — "
          "Биржа). С материком он связан пульсом через Маяк.")
        w("")
    w("Всё ниже собрано кодом, без модели и без догадок: файлы, размеры, даты, "
      "что объявлено в коде, кто кого зовёт. Где факт не значит вывода, это "
      "сказано рядом. Мнения здесь нет — оно пишется отдельно.")
    w("")
    w("Чего здесь нет никогда: содержимого домов жителей (только что дом есть "
      "и сколько в нём файлов), ключей и паролей (файл `.env` не открывался), "
      "текстов переписки (только их число). Дом жителя — его личное.")
    w("")

    # ── 1. Город одним взглядом
    vsego = len(g.faily)
    ves = sum(s for _, _, s, _ in g.faily)
    vidy = Counter()
    for r, p, s, m in g.faily:
        suf = p.suffix.lower()
        vid = ("код" if suf in _KOD else "тексты" if suf in _TEKSTY else
               "данные" if suf in _DANNYE else "картинки" if suf in _KARTINKI else
               "звук и видео" if suf in _ZVUK_VIDEO else "прочее")
        if _eto_bak(p):
            vid = "запасные копии (.bak)"
        vidy[vid] += 1
    strok_koda = sum(i["строк"] for i in kod.values())
    w("## 1. Город одним взглядом")
    w("")
    w(f"Файлов: **{vsego}**, вес: **{_razmer(ves)}**. "
      f"Кода: **{len(kod)}** файлов, **{strok_koda}** строк.")
    w("")
    w("| что | файлов |")
    w("|---|---|")
    for vid, n in vidy.most_common():
        w(f"| {vid} | {n} |")
    w("")
    kvartaly = defaultdict(lambda: [0, 0, 0.0])
    for r, p, s, m in g.faily:
        kv = r.split("/")[0] if "/" in r else "(корень)"
        k = kvartaly[kv]
        k[0] += 1
        k[1] += s
        k[2] = max(k[2], m)
    w("**Кварталы (папки верхнего уровня):**")
    w("")
    w("| папка | файлов | вес | последнее изменение | что это (из её README) |")
    w("|---|---|---|---|---|")
    for kv in sorted(kvartaly):
        n, s, m = kvartaly[kv]
        readme = g.k / kv / "README.md"
        pro = ""
        if readme.is_file():
            for s2 in _chitat(readme).splitlines():
                if s2.strip() and not s2.startswith("#"):
                    pro = _odna_stroka(s2, 80)
                    break
        w(f"| `{kv}` | {n} | {_razmer(s)} | {_data(m)} | {pro} |")
    w("")
    if g.env_est:
        w("Файл ключей `.env` есть — не открывался.")
        w("")

    # ── 2. Люди
    w("## 2. Люди")
    w("")
    w("Жители живут в `GRONDHEIM_CITY/жители/ковчег/<имя>/`. Их дома — личное: "
      "здесь только число файлов и какие этажи памяти заведены.")
    w("")
    pst = posty(g)
    na_postu = defaultdict(list)
    for p_ in pst:
        if p_["кто"]:
            na_postu[p_["кто"]].append(p_["название"])
    w("| житель | работа (пост) | этажи дома | файлов | переписок |")
    w("|---|---|---|---|---|")
    for imya in sorted(g.doma):
        d = g.doma[imya]
        etazhi = ", ".join(sorted(d["этажи"])) or "—"
        rab = "; ".join(na_postu.get(imya, [])) or "—"
        w(f"| {imya} | {rab} | {_odna_stroka(etazhi, 70)} | {d['файлов']} | {d['чатов']} |")
    w("")
    w("**Посты (рабочие места):**")
    w("")
    w("| пост | где | кто сидит | с |")
    w("|---|---|---|---|")
    for p_ in pst:
        kto = p_["кто"] or "*пусто*"
        if p_["битый"]:
            kto = "⚠ пост.json не читается"
        w(f"| {p_['название']} | {p_['где']} | {kto} | {p_.get('с','')} |")
    w("")
    mst = mesta(g)
    if mst:
        w("**Места (локации):** " + "; ".join(
            f"`{i}` {n}".strip() for i, n in mst))
        w("")

    # ── 3. Двери
    w("## 3. Двери — страницы города")
    w("")
    w(f"Запускается файлом `{vhod}`. Страницы (адреса в браузере) и где "
      "они объявлены:")
    w("")
    stranitsy = defaultdict(list)
    for r, info in kod.items():
        for adres, stroka in info["страницы"]:
            stranitsy[adres].append(f"{r}:{stroka}")
    w("| адрес | где объявлен |")
    w("|---|---|")
    for adres in sorted(stranitsy):
        w(f"| `{adres}` | {', '.join(stranitsy[adres])} |")
    w("")

    # ── 4. Код по кварталам
    w("## 4. Код")
    w("")
    w("По каждому файлу: строки, описание из его шапки, метки патчей "
      "(следы того, какие правки на нём стоят), кого он зовёт и кто зовёт его. "
      "«Никто не зовёт по имени» — ещё не значит «мёртвый»: файл может "
      "грузиться по пути (так устроены мозги мест и ниточки Архива) или "
      "запускаться сам.")
    w("")
    po_kvartalu = defaultdict(list)
    for r in sorted(kod):
        kv = r.split("/")[0] if "/" in r else "(корень)"
        po_kvartalu[kv].append(r)
    for kv in sorted(po_kvartalu):
        w(f"### `{kv}`")
        w("")
        for r in po_kvartalu[kv]:
            i = kod[r]
            stem = Path(r).stem
            priznaki = []
            if i["сам_запускается"]:
                priznaki.append("запускается сам")
            if i["грузит_по_пути"]:
                priznaki.append("грузит файлы по пути")
            if i["страницы"]:
                priznaki.append("страницы: " + ", ".join(a for a, _ in i["страницы"]))
            if stem in set(getattr(sys, "stdlib_module_names", ())):
                priznaki.append(f"имя как у стандартного модуля Python ({stem}) — "
                                "связи по имени не считаются")
            if len(po_imeni[stem]) > 1:
                priznaki.append(f"тёзки: {len(po_imeni[stem])} файла с именем {stem}.py")
            w(f"- **`{r}`** — {i['строк']} строк, изменён {_data(i['mtime'])}")
            if i["ошибка"]:
                w(f"  - ⚠ **НЕ СОБИРАЕТСЯ** — {i['ошибка']}")
            if i["описание"]:
                w(f"  - {i['описание']}")
            if priznaki:
                w(f"  - {'; '.join(priznaki)}")
            if i["зовёт"]:
                w(f"  - зовёт: {', '.join(sorted(i['зовёт']))}")
            kto = sorted(zovut.get(stem, set()))
            if kto:
                w(f"  - его зовут: {', '.join(kto)}")
            elif not i["сам_запускается"] and not i["страницы"]:
                w("  - никто не зовёт по имени")
            if i["метки"]:
                pokaz = i["метки"][:6]
                hvost = f" и ещё {len(i['метки']) - 6}" if len(i["метки"]) > 6 else ""
                w(f"  - метки патчей ({len(i['метки'])}): {', '.join(pokaz)}{hvost}")
        w("")

    # ── 5. Книги и документы
    w("## 5. Книги и документы")
    w("")
    teksty = [(r, p, s, m) for r, p, s, m in g.faily
              if p.suffix.lower() in _TEKSTY and not g.dom_zhitelya(p)
              and not _v_kladovoy(r) and not _eto_bak(p)]
    svodka = _svodka_progonov([(r, s, m) for r, p, s, m in teksty])
    teksty = [x for x in teksty if not _progony(x[0])]
    po_papke = defaultdict(list)
    for t in teksty:
        po_papke[str(Path(t[0]).parent).replace("\\", "/")].append(t)
    w("Документы города — с разделами. Тексты внутри `GRONDHEIM_CITY` "
      "(знания мест, курсы, образцы, прогоны) — одной строкой на папку, "
      "с именами файлов.")
    w("")
    for papka in sorted(po_papke):
        spisok = po_papke[papka]
        imya_p = "корень города" if papka == "." else papka
        if len(spisok) > 10 or papka.startswith("GRONDHEIM_CITY"):
            s = sum(x[2] for x in spisok)
            m = max(x[3] for x in spisok)
            imena = [Path(x[0]).name for x in spisok]
            pokaz = ", ".join(imena[:12]) + (f" …и ещё {len(imena) - 12}"
                                             if len(imena) > 12 else "")
            w(f"- `{imya_p}/` — {len(spisok)} текстов, {_razmer(s)}, "
              f"последний {_data(m)}: {pokaz}")
            continue
        for r, p, s, m in spisok:
            if s < 300:
                continue
            z = zagolovki(p) if p.suffix.lower() == ".md" else []
            w(f"- **`{r}`** — {_razmer(s)}, изменён {_data(m)}")
            if z:
                w(f"  - разделы: {' · '.join(z)}")
    for s_ in svodka:
        w(f"- Прогоны (отчёты и логи): {s_}")
    w("")

    # ── 6. Данные
    w("## 6. Данные")
    w("")
    w("Файлы данных вне домов жителей и вне прогонов, самые крупные:")
    w("")
    w("| файл | вес | записей | изменён |")
    w("|---|---|---|---|")
    svodka_d = _svodka_progonov([(r, s, m) for r, s, m, n in krupnye])
    krupnye = [x for x in krupnye if not _progony(x[0])]
    for r, s, m, n in krupnye[:25]:
        w(f"| `{r}` | {_razmer(s)} | {n if n is not None else '—'} | {_data(m)} |")
    w("")
    for s_ in svodka_d:
        w(f"Данные прогонов: {s_}")
        w("")

    # ── 7. Приметы неладного
    w("## 7. Приметы неладного (только факты)")
    w("")
    nesobr = [(r, i["ошибка"]) for r, i in kod.items() if i["ошибка"]]
    if nesobr:
        w("**Код, который не собирается:**")
        for r, o in nesobr:
            w(f"- `{r}` — {o}")
    else:
        w("- Весь код собирается (синтаксических ошибок нет).")
    if bitye:
        w("")
        w("**Битые данные:**")
        for r, o in bitye:
            w(f"- `{r}` — {o}")
    else:
        w("- Битых файлов данных не найдено.")
    baki = Counter(str(Path(r).parent).replace("\\", "/") for r, p, s, m in g.faily
                   if _eto_bak(p) and not _v_kladovoy(r))
    if baki:
        w("")
        w(f"**Запасные копии (.bak) вне чулана:** {sum(baki.values())} — "
          + "; ".join(f"`{k}` {v}" for k, v in baki.most_common(8)))
    w("")

    # ── 8. Что изменилось
    w("## 8. Что изменилось с прошлого снимка")
    w("")
    if not snimok_star:
        w("Прошлого снимка нет — это первый. В следующий раз здесь будет "
          "список новых, ушедших и изменённых файлов.")
    else:
        (nov, nov_d), (ush, ush_d), (izm, izm_d) = raznitsa(snimok_star, snimok_nov, g)
        w(f"Прошлый снимок: {kogda_star}. Новых: {len(nov) + sum(nov_d.values())}, "
          f"ушло: {len(ush) + sum(ush_d.values())}, "
          f"изменилось: {len(izm) + sum(izm_d.values())}.")
        for zag, spisok, doma in (("Новые", nov, nov_d), ("Ушли", ush, ush_d),
                                  ("Изменились", izm, izm_d)):
            if not spisok and not doma:
                continue
            w("")
            w(f"**{zag}:**")
            for r in spisok[:60]:
                w(f"- `{r}`")
            if len(spisok) > 60:
                w(f"- …и ещё {len(spisok) - 60}")
            if doma:
                w("- в домах жителей (только число): "
                  + ", ".join(f"{k} {v}" for k, v in sorted(doma.items())))
    w("")
    w("---")
    w("*Карта, а не земля: перед правкой любого файла смотри сам файл.*")
    return "\n".join(L) + "\n"


# ═══════════════════════════════════════════════════════════

def main():
    koren = naiti_koren()
    if koren is None:
        print("✗ Не нашёл корень (нужны main.py или ostrov_main.py и GRONDHEIM_CITY).")
        return
    papka = koren / "Брат" / "отчёты"
    papka.mkdir(parents=True, exist_ok=True)
    put_snimka = papka / "снимок.json"

    print(f"Корень {'острова' if (koren / 'ostrov_main.py').is_file() and not (koren / 'main.py').is_file() else 'города'}: {koren}")
    print("Обхожу город…")
    g = Gorod(koren)
    g.oboyti()
    # сам отчёт и снимок в отчёт не входят
    g.faily = [f for f in g.faily if not f[0].startswith("Брат/отчёты/")]
    print(f"  файлов: {len(g.faily)}, жителей: {len(g.doma)}")

    staryy, kogda_star = {}, ""
    if put_snimka.is_file():
        try:
            d = json.loads(put_snimka.read_text(encoding="utf-8"))
            staryy, kogda_star = d.get("файлы", {}), d.get("когда", "")
        except Exception:
            print("  прошлый снимок не читается — сравнение пропущу")

    print("Снимаю слепок…")
    novyy = snyat_snimok(g)
    print("Пишу отчёт…")
    tekst = napisat(g, staryy, novyy, kogda_star)

    (papka / "ГОРОД.md").write_text(tekst, encoding="utf-8")
    put_snimka.write_text(json.dumps(
        {"когда": datetime.now().strftime("%Y-%m-%d %H:%M"), "версия": VERSIYA,
         "файлы": novyy}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"\n✓ Отчёт: {papka / 'ГОРОД.md'}  ({_razmer(len(tekst.encode('utf-8')))})")
    print(f"✓ Снимок: {put_snimka}")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            input("\nEnter — закрыть окно")
        except EOFError:
            pass
