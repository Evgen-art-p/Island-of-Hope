# -*- coding: utf-8 -*-
# PERESELENIE_3_V1
"""
ПЕРЕСЕЛЕНИЕ-3 — на Остров едет нынешняя Биржа материка (11.11).

Слово Шефа 11.11: «заводим Биржу на острове — пусть гоняет, а сами дома
дальше продолжим с городом»; план переселения — «да».

Второе переселение (27.09) везло Биржу первого уровня. С тех пор: цех
«хаос_дубль» (D01–D03), второй уровень (эталон 10.11), ведение по месту и
по масштабу, волны по канону, замки, снимок места с фактами, казна,
картотека, архивариус, новые отчёты. Это переселение везёт её такой,
какая она сейчас.

    двойной клик          покажет, что везёт и что убирает, и спросит
    python pereselenie_3.py --sdelat      сделает без вопроса

Класть и запускать — В КОРНЕ ОСТРОВА. Материк найдёт сам.

ЧТО ВЕЗЁМ
    · код Биржи целиком + история котировок (test_data);
    · цеха: торговый_хаос, контора, ХАОС_ДУБЛЬ — мозги, бумаги, знания
      (с картинками-образцами), опыт места, альбом волн, паспорта.
      БЕЗ прогонов и БЕЗ данных — у острова свой счёт;
    · из города — то, что Биржа и мозги мест РЕАЛЬНО подключают: список
      собирается чтением кода перед переездом, а не прибит руками;
    · двигатель жителя, Маяк (код), sostoyanie.py, БИРЖА.md;
    · учебник рук трейдера — дисциплину «финансы» (без черновиков);
    · посты Биржи и хранителя Маяка — ПУСТЫМИ, без имён и чужой истории;
    · локации под места — только те, которых на острове ещё нет.

ЖИТЕЛЕЙ НЕ ВЕЗЁМ. Их повезёт перевозка, отдельным шагом.

ЧТО УБИРАЕМ (в _ПЕРЕЕЗД/<время>/старое — не удаляется): каждый островной
файл, на место которого ложится новый. Островное — главную, перевозку,
Застройщика, причал с пульсом, руки острова, фон, свод, данные Маяка,
прогоны и данные острова — не трогаем.

В КОНЦЕ — две проверки на самом острове:
    · всё ли, что подключает Биржа и мозги мест, на острове есть;
    · есть ли история фунта, евро и австралийца на H4, H1, D1, W1, MN1
      и докуда она идёт.
"""
import argparse
import ast
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

OSTROV = Path(__file__).resolve().parent
PEREEZD = OSTROV / "_ПЕРЕЕЗД"

MUSOR_PAPKI = {"__pycache__", ".git", ".vscode", "node_modules",
               "_ARCHIVE", "_OLD", "_АРХИВ_ЧИСТКИ", "_УБОРКА", "_ПЕРЕЕЗД", "_ЧУЛАН"}
KARTINKI = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
TYAZHYOLOE = {".mp3", ".wav", ".zip", ".mp4", ".mov"}

CEHA_BIRZHI = ("торговый_хаос", "контора", "хаос_дубль")
CEHA_TORGOVYE = ("торговый_хаос", "хаос_дубль")
POSTY_SVERH = ("mayak", "khranitel_mayaka")
CEH_NE_VEZYOM = {"прогоны", "данные"}

GOROD_BAZA = ("rabota.py", "ui_rabota.py", "gnezda.py",
              "klyuch.py", "rezidenty.py", "ruka_mayaka.py")
KOREN_FAILY = ("sostoyanie.py", "kalibrovka_core.py", "БИРЖА.md")
PAPKI_MODULEY = ("Биржа", "ГОРОД", "жители", "Маяк", "")   # где ищем модули

PARY = ("GBPUSD", "EURUSD", "AUDUSD")
ETAZHI = ("H4", "H1", "D1", "W1", "MN1")

SHTAMP = Path("Биржа") / "_переселение_3.txt"
SHTAMP_2 = Path("Биржа") / "_переселение_2.txt"


# ══════════════════════════════════════════════════════════════
# ГДЕ МАТЕРИК
# ══════════════════════════════════════════════════════════════

def eto_materik(d: Path) -> bool:
    try:
        return ((d / "GRONDHEIM_CITY").is_dir()
                and (d / "Биржа" / "council.py").is_file()
                and (d / "Биржа" / "vedenie_sdelki.py").is_file()
                and (d / "GRONDHEIM_CITY" / "Биржа" / "цеха" / "хаос_дубль").is_dir())
    except Exception:
        return False


def _kandidaty():
    vidno, gde = [], []
    dom = Path.home()
    korni = [OSTROV.parent, OSTROV.parent.parent, dom,
             dom / "Desktop", dom / "Documents", dom / "Рабочий стол",
             dom / "Документы",
             Path("C:/") if sys.platform == "win32" else None]
    for k in korni:
        if k is None or not k.exists() or k in gde:
            continue
        gde.append(k)
        try:
            for d in k.iterdir():
                if d.is_dir() and d != OSTROV and eto_materik(d) and d not in vidno:
                    vidno.append(d)
        except Exception:
            continue
    return vidno


def nayti_materik(skazan: str):
    if skazan:
        d = Path(skazan.strip().strip('"').strip("'")).expanduser().resolve()
        if eto_materik(d):
            return d
        print(f"x по этому пути нынешнего города нет: {d}")
        return None
    nashli = _kandidaty()
    if len(nashli) == 1:
        d = nashli[0]
        print(f"\nнашёл материк: {d}")
        if input("это он? [Enter — да, n — нет]: ").strip().lower() in ("", "y", "д", "да"):
            return d
        nashli = []
    if len(nashli) > 1:
        print("\nнашёл несколько городов:")
        for i, d in enumerate(nashli, 1):
            print(f"   {i}. {d}")
        o = input("который материк? [цифра, Enter — отмена]: ").strip()
        if o.isdigit() and 1 <= int(o) <= len(nashli):
            return nashli[int(o) - 1]
        print("отменил")
        return None
    print("\nсам не нашёл. Перетащи папку материка мышкой в это окно")
    print("и нажми Enter (или вставь путь):")
    o = input("> ").strip().strip('"').strip("'")
    if not o:
        print("отменил")
        return None
    d = Path(o).expanduser().resolve()
    if eto_materik(d):
        return d
    print(f"x по этому пути нынешнего города нет: {d}")
    return None


# ══════════════════════════════════════════════════════════════
# ЧТЕНИЕ КОДА: какие модули подключаются
# ══════════════════════════════════════════════════════════════

def importy(fp: Path) -> set:
    """Имена верхнего уровня всего, что файл подключает (и внутри функций)."""
    try:
        tree = ast.parse(fp.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            out.add(n.module.split(".")[0])
    return out


def nayti_modul(koren: Path, imya: str):
    for papka in PAPKI_MODULEY:
        p = (koren / papka / f"{imya}.py") if papka else (koren / f"{imya}.py")
        if p.is_file():
            return p
    return None


def mozgi(koren: Path) -> list:
    out = []
    ceha = koren / "GRONDHEIM_CITY" / "Биржа" / "цеха"
    for ceh in CEHA_BIRZHI:
        out += sorted((ceha / ceh).glob("слоты/*/мозг.py"))
    return out


def nuzhnye_moduli(materik: Path) -> set:
    """Модули материка (вне папки Биржа), которые Биржа и мозги тянут — с хвостом."""
    nado, ochered, vidno = set(), [], set()
    for p in sorted((materik / "Биржа").glob("*.py")) + mozgi(materik) + \
            [materik / "жители" / "dvizhok.py"]:
        ochered.append(p)
    for p in [materik / "ГОРОД" / imya for imya in GOROD_BAZA] + [materik / "жители" / "dvizhok.py"]:
        if p.is_file():
            nado.add(p)
            ochered.append(p)
    while ochered:
        fp = ochered.pop()
        if fp in vidno:
            continue
        vidno.add(fp)
        for imya in importy(fp):
            p = nayti_modul(materik, imya)
            if p is None or p.parent == materik / "Биржа":
                continue
            if p.name in ("main.py",) or p.name.startswith(("patch_", "PATCH_", "zamer_")):
                continue
            if p not in nado:
                nado.add(p)
                ochered.append(p)
    return nado


# ══════════════════════════════════════════════════════════════
# ЧТО ЕДЕТ
# ══════════════════════════════════════════════════════════════

def _musor(otn: Path) -> bool:
    if any(part in MUSOR_PAPKI for part in otn.parts):
        return True
    n = otn.name
    return (".bak" in n or n.endswith((".snesen", ".pyc", ".log", ".perenesen",
                                       ".bylo_stranicey", ".bylo")) or n == ".env")


def zdaniya_birzhi(materik: Path) -> set:
    ids = set()
    ceha = materik / "GRONDHEIM_CITY" / "Биржа" / "цеха"
    for ceh in CEHA_BIRZHI:
        f = ceha / ceh / "manifest.json"
        if not f.is_file():
            continue
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for k in ("здание", "квартал"):
            if m.get(k):
                ids.add(m[k])
    return ids


def posty_ostrova(materik: Path) -> list:
    """Посты Биржи и хранителя Маяка — ОЧИЩЕННЫМИ."""
    out = []
    posty = materik / "GRONDHEIM_CITY" / "посты"
    if not posty.is_dir():
        return out
    for d in sorted(posty.iterdir()):
        f = d / "пост.json"
        if not f.is_file():
            continue
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        birzhevoy = p.get("цех") in CEHA_TORGOVYE or (
            p.get("цех") == "контора" and p.get("квартал") == "Биржа")
        if not birzhevoy and d.name not in POSTY_SVERH:
            continue
        p["кто_сидит"] = None
        p["трудовая_история"] = []
        p["_note_ostrov"] = ("вакансия острова. Приехала с материка пустой: "
                             "имена и трудовая история там и остались.")
        out.append((d.name, p))
    return out


def lokacii_postov(posty: list) -> set:
    return {(p.get("локация") or "").strip() for _, p in posty} - {""}


def sobrat(materik: Path, posty: list):
    plan, seen = [], set()

    def vzyat(p: Path):
        if not p.is_file():
            return
        otn = p.relative_to(materik)
        if _musor(otn) or otn in seen:
            return
        seen.add(otn)
        plan.append((p, otn))

    birzha = materik / "Биржа"
    for p in birzha.glob("*.py"):
        vzyat(p)
    for p in (birzha / "test_data").glob("*.csv"):
        vzyat(p)
    vzyat(birzha / "учебный_режим.txt")

    moduli = nuzhnye_moduli(materik)
    for p in sorted(moduli):
        vzyat(p)

    for p in (materik / "Маяк").glob("*"):
        if p.is_file() and p.suffix.lower() in (".py", ".md"):
            vzyat(p)
    for imya in KOREN_FAILY:
        vzyat(materik / imya)

    for ceh in CEHA_BIRZHI:
        d = materik / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            chasti = p.relative_to(d).parts
            if any(c in CEH_NE_VEZYOM for c in chasti[:-1]):
                continue
            suf = p.suffix.lower()
            if suf in TYAZHYOLOE:
                continue
            if suf in KARTINKI and "знания" not in chasti and "альбом_волн" not in chasti:
                continue
            vzyat(p)

    fin = materik / "GRONDHEIM_CITY" / "Академия" / "дисциплины" / "финансы"
    if fin.is_dir():
        for p in fin.rglob("*"):
            if p.is_file() and p.suffix.lower() not in TYAZHYOLOE \
                    and "_черновики" not in p.parts:
                vzyat(p)
    vzyat(materik / "GRONDHEIM_CITY" / "Академия" / "дисциплины" / "README.md")

    for lid in zdaniya_birzhi(materik) | lokacii_postov(posty):
        d = materik / "GRONDHEIM_CITY" / "локации" / lid
        if not d.is_dir() or (OSTROV / "GRONDHEIM_CITY" / "локации" / lid).exists():
            continue
        for q in d.rglob("*"):
            if q.is_file() and q.suffix.lower() not in TYAZHYOLOE:
                vzyat(q)
    return plan, moduli


# ══════════════════════════════════════════════════════════════
# ЧТО УХОДИТ В СТАРОЕ
# ══════════════════════════════════════════════════════════════

def odinakovy(src: Path, otn: Path) -> bool:
    import filecmp
    cel = OSTROV / otn
    try:
        return cel.is_file() and filecmp.cmp(src, cel, shallow=False)
    except Exception:
        return False


def _zanyat(f: Path) -> bool:
    try:
        p = json.loads(f.read_text(encoding="utf-8"))
        return bool(((p.get("кто_сидит") or {}).get("имя") or "").strip())
    except Exception:
        return False


def _post_takoy_zhe(f: Path, telo: dict) -> bool:
    try:
        return json.loads(f.read_text(encoding="utf-8")) == telo
    except Exception:
        return False


def staroe(plan: list, posty: list) -> list:
    out, seen = [], set()

    def dobavit(otn: Path):
        if otn in seen or not (OSTROV / otn).exists():
            return
        seen.add(otn)
        out.append(otn)

    for src, otn in plan:
        if not odinakovy(src, otn):
            dobavit(otn)
    for imya, telo in posty:
        f = OSTROV / "GRONDHEIM_CITY" / "посты" / imya / "пост.json"
        if f.exists() and not _zanyat(f) and not _post_takoy_zhe(f, telo):
            dobavit(f.relative_to(OSTROV))
    return out


# ══════════════════════════════════════════════════════════════
# ПРОВЕРКИ НА ОСТРОВЕ
# ══════════════════════════════════════════════════════════════

def proverka_moduley() -> list:
    """Что подключает Биржа острова и мозги мест — и чего на острове нет."""
    net = {}
    fajly = sorted((OSTROV / "Биржа").glob("*.py")) + mozgi(OSTROV)
    for fp in fajly:
        for imya in importy(fp):
            if nayti_modul(OSTROV, imya) or imya in sys.builtin_module_names:
                continue
            try:
                if importlib.util.find_spec(imya) is not None:
                    continue
            except Exception:
                pass
            net.setdefault(imya, set()).add(fp.relative_to(OSTROV).as_posix())
    return sorted(net.items())


def _poslednyaya_data(fp: Path) -> str:
    try:
        with open(fp, "rb") as f:
            f.seek(0, 2)
            n = f.tell()
            f.seek(max(0, n - 400))
            hvost = f.read().decode("utf-8", "replace").strip().splitlines()
        stroka = hvost[-1] if hvost else ""
        return stroka.replace("\t", ",").replace(";", ",").split(",")[0][:16]
    except Exception:
        return "?"


def proverka_istorii() -> list:
    td = OSTROV / "Биржа" / "test_data"
    out = []
    for sym in PARY:
        for tf in ETAZHI:
            kand = [p for p in td.glob(f"*{sym}*.csv")
                    if tf in p.stem.upper().replace(sym, "", 1)
                    and not (tf == "H1" and "H12" in p.stem.upper())
                    and not (tf == "D1" and "D10" in p.stem.upper())
                    and not (tf == "W1" and "W10" in p.stem.upper())]
            if kand:
                p = sorted(kand, key=lambda q: q.stat().st_size)[-1]
                out.append((sym, tf, p.name, _poslednyaya_data(p)))
            else:
                out.append((sym, tf, None, ""))
    return out


# ══════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--materik", default="")
    ap.add_argument("--sdelat", action="store_true")
    a = ap.parse_args()
    dvoynoy_klik = len(sys.argv) == 1

    print("=" * 66)
    print("ПЕРЕСЕЛЕНИЕ-3 · нынешняя Биржа материка на Остров (с хаос_дубль)")
    print("=" * 66)

    if not (OSTROV / "OSTROV_NADEZHDY.md").exists() and not (OSTROV / "ostrov_main.py").exists():
        print("x не вижу островных примет. Положи меня в КОРЕНЬ ОСТРОВА.")
        return 1
    materik = nayti_materik(a.materik)
    if materik is None:
        return 1
    if materik == OSTROV:
        print("x материк и остров — одна папка. Так нельзя.")
        return 1

    posty = posty_ostrova(materik)
    plan, moduli = sobrat(materik, posty)
    if not plan:
        print("x с материка нечего везти — проверь путь")
        return 1
    ukhodit = staroe(plan, posty)
    uzhe = {otn for src, otn in plan if odinakovy(src, otn)}
    plan = [(src, otn) for src, otn in plan if otn not in uzhe]
    if uzhe:
        print(f"\n(уже на острове и не менялось: {len(uzhe)} файлов — не трогаю)")
    posty_menyat = [i for i, t in posty if not (
        (OSTROV / "GRONDHEIM_CITY" / "посты" / i / "пост.json").exists() and (
            _zanyat(OSTROV / "GRONDHEIM_CITY" / "посты" / i / "пост.json") or
            _post_takoy_zhe(OSTROV / "GRONDHEIM_CITY" / "посты" / i / "пост.json", t)))]

    print("\n── ИЗ ГОРОДА — ТО, ЧТО БИРЖА И МОЗГИ ПОДКЛЮЧАЮТ ──")
    for p in sorted(moduli):
        print(f"   {p.relative_to(materik).as_posix()}")

    if not plan and not ukhodit and not posty_menyat:
        print("\nОстров уже в порядке — везти нечего.")
    else:
        print(f"\n── УХОДИТ В «СТАРОЕ» — {len(ukhodit)} файлов (на их место ляжет новое) ──")
        ves = sum(p.stat().st_size for p, _ in plan) / 1024 / 1024
        print(f"\n── ВЕЗУ — {len(plan)} файлов, {ves:.1f} МБ ──")
        po = {}
        for _, otn in plan:
            if otn.parts[0] == "GRONDHEIM_CITY":
                k = "/".join(otn.parts[:4]) if "цеха" in otn.parts else "/".join(otn.parts[:3])
            elif otn.parts[0] == "Биржа" and len(otn.parts) > 2:
                k = "/".join(otn.parts[:2])
            else:
                k = otn.parts[0]
            po[k] = po.get(k, 0) + 1
        for k in sorted(po):
            print(f"   {k:<56} {po[k]}")
        print(f"\n── ВАКАНСИИ, ПУСТЫЕ — {len(posty)} ──")
        for imya, telo in posty:
            f = OSTROV / "GRONDHEIM_CITY" / "посты" / imya / "пост.json"
            pom = "   [на острове занят — не трогаю]" if f.exists() and _zanyat(f) else ""
            print(f"   {telo.get('название', imya):<40} {telo.get('слот') or ''}{pom}")
        print("\n── БЕРЕГУ ──")
        print("   главную, перевозку, Застройщика, причал и пульс, руки острова, фон, свод,")
        print("   локации острова, данные Маяка, прогоны и данные острова")
        print("\n── НЕ ВЕЗУ ──")
        print("   жителей (места пустые), Брата, Страницу Жизни, Архив, Академию кроме")
        print("   «финансов», прогоны и торговую историю материка, ключ .env")

        if not a.sdelat:
            if not dvoynoy_klik:
                print("\nЭто был показ. Сделать: python pereselenie_3.py --sdelat")
                return 0
            o = input("\nВезти? [да — везу, Enter — отмена]: ").strip().lower()
            if o not in ("да", "д", "y", "yes"):
                print("отменил, ничего не тронуто")
                return 0

        kuda = PEREEZD / datetime.now().strftime("%Y%m%d_%H%M%S")
        _i = 1
        while kuda.exists():
            _i += 1
            kuda = PEREEZD / (datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{_i}")
        for otn in ukhodit:
            cel = kuda / "старое" / otn
            cel.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(OSTROV / otn), str(cel))
        for p, otn in plan:
            cel = OSTROV / otn
            cel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, cel)
        for imya, telo in posty:
            cel = OSTROV / "GRONDHEIM_CITY" / "посты" / imya / "пост.json"
            if cel.exists() and (_zanyat(cel) or _post_takoy_zhe(cel, telo)):
                continue
            cel.parent.mkdir(parents=True, exist_ok=True)
            cel.write_text(json.dumps(telo, ensure_ascii=False, indent=2), encoding="utf-8")
        (OSTROV / SHTAMP).write_text(
            f"Остров переселён pereselenie_3.py {datetime.now():%d.%m.%Y %H:%M}\n"
            f"с материка: {materik}\nПовторный запуск меняет только отличающиеся файлы и\n"
            "не трогает прогоны и данные острова.\n", encoding="utf-8")
        kuda.mkdir(parents=True, exist_ok=True)
        (kuda / "манифест.json").write_text(json.dumps({
            "когда": datetime.now().isoformat(timespec="seconds"),
            "что": "переселение-3: нынешняя Биржа материка с хаос_дубль",
            "материк": str(materik),
            "модули_города": [p.relative_to(materik).as_posix() for p in sorted(moduli)],
            "вакансии": [imya for imya, _ in posty],
            "убрано_в_старое": [str(o) for o in ukhodit],
            "завезено": [str(o) for _, o in plan],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n" + "-" * 66)
        print(f"+ в «старое» {len(ukhodit)}, завезено {len(plan)}, вакансий {len(posty)}")
        print(f"  старое лежит в {kuda.relative_to(OSTROV)}/старое — не удалено")

    # ── проверки на острове ──
    print("\n" + "=" * 66)
    print("ПРОВЕРКА 1 · всё ли, что подключает Биржа и мозги мест, на острове есть")
    net = proverka_moduley()
    if not net:
        print("   ✓ всё на месте")
    else:
        for imya, kto in net:
            print(f"   ✗ {imya}  — зовут: {', '.join(sorted(kto)[:4])}")
        print("   (это может быть и библиотека Python, которой нет в этом окне, —")
        print("    скинь список Брату, разберём)")

    print("\nПРОВЕРКА 2 · история котировок на острове (до какой даты)")
    for sym, tf, imya, data in proverka_istorii():
        if imya:
            ok = "✓" if data >= "2025.12" or data >= "2025-12" else "·"
            print(f"   {ok} {sym} {tf:<4} {imya:<30} до {data}")
        else:
            print(f"   ✗ {sym} {tf:<4} — файла нет")
    print("   ✓ — история доходит до конца 2025 года, · — кончается раньше")

    print("\nДальше:")
    print("  1. .env с ключом модели на острове — тот же, что дома;")
    print("  2. подними остров (ОСТРОВ.bat) → дверь БИРЖА — места пустые;")
    print("  3. жители — перевозкой, отдельным шагом (первый — «космонавт»).")
    return 0


if __name__ == "__main__":
    try:
        _kod = main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nx сорвалось: {e}\n  Скинь это окно Брату.")
        _kod = 1
    if sys.platform == "win32" and len(sys.argv) == 1:
        try:
            input("\nEnter — закрыть окно.")
        except Exception:
            pass
    sys.exit(_kod)

# PERESELENIE_3_V1 - marker
