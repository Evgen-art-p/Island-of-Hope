# -*- coding: utf-8 -*-
# PERESELENIE_2_V1
"""
ПЕРЕСЕЛЕНИЕ-2 — на Остров едет НЫНЕШНЯЯ Биржа материка (27.09).

Первое переселение (10.08) везло Биржу эпохи Искры и Совета. С тех пор
Биржа переписана: стол, кадр, руки трейдера, знания первого уровня,
кран истории, отчёт. Это переселение везёт её такой, какая она сейчас.

    двойной клик          покажет, что везёт и что убирает, и спросит
    python pereselenie_2.py --sdelat      сделает без вопроса

Класть и запускать — В КОРНЕ ОСТРОВА. Материк найдёт сам.

ЧТО ВЕЗЁМ
    · код Биржи целиком + история котировок (test_data) — ради неё едем;
    · цех торгового хаоса и контору: мозги, промпты, знания (с
      картинками-образцами!), манифесты. БЕЗ прогонов и БЕЗ данных —
      у острова свой счёт;
    · из города — только то, что Биржа реально зовёт: работа, гнёзда,
      ключ жителя, посадка на пост, рука Маяка; двигатель жителя;
    · Маяк (код), sostoyanie.py, БИРЖА.md;
    · учебник рук трейдера — дисциплину «финансы» из Академии;
    · посты Биржи и хранителя Маяка — ПУСТЫМИ, без имён и чужой истории;
    · локации под эти места — только те, которых на острове ещё нет.

ЖИТЕЛЕЙ НЕ ВЕЗЁМ. Места приезжают пустыми, кого сажать — решит Шеф.

ЧТО УБИРАЕМ (в _ПЕРЕЕЗД/<время>/старое — не удаляется)
    · старую Биржу целиком: код (Искра, Совет, огрызки Снайпера) и цеха;
    · старые посты Биржи (если на посту никто не сидит);
    · смотрелки и отработавшие патчи острова;
    · каждый островной файл, на место которого ложится новый.

ЧТО БЕРЕЖЁМ — всё островное: главную, перевозку, Застройщика, причал с
пульсом, запуск острова, фон, свод, локации острова, данные Маяка.

ДВЕРИ: в запуск острова добавляется страница отчёта прогона (кабинет
Биржи на неё ссылается), на главную — дверь «БИРЖА».
"""
import argparse
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
               "_ARCHIVE", "_OLD", "_АРХИВ_ЧИСТКИ", "_УБОРКА", "_ПЕРЕЕЗД"}
KARTINKI = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
TYAZHYOLOE = {".mp3", ".wav", ".zip", ".mp4", ".mov"}

CEHA_BIRZHI = ("торговый_хаос", "контора")
POSTY_SVERH = ("mayak", "khranitel_mayaka")     # хранитель Маяка
CEH_NE_VEZYOM = {"прогоны", "данные"}        # у острова свой счёт

GOROD_MODULI = ("rabota.py", "ui_rabota.py", "gnezda.py",
                "klyuch.py", "rezidenty.py", "ruka_mayaka.py")
KOREN_FAILY = ("sostoyanie.py", "kalibrovka_core.py", "БИРЖА.md")

# что на острове уходит в «старое» целыми папками
STAROE_PAPKI = ("Биржа", "GRONDHEIM_CITY/Биржа")
# смотрелки и отработавшие патчи острова
STAROE_KOREN = ("istoki_pokazat.py", "proverka_kotirovok.py",
                "proverka_stola.py", "proverka_zreniya.py", "rabota_pult.py",
                "stol_pokazat.py", "postavit_glavnuyu.py",
                "postavit_glavnuyu (1).py", "postavit_perevozku.py",
                "postavit_zastroyshchika.py")


# ══════════════════════════════════════════════════════════════
# ГДЕ МАТЕРИК
# ══════════════════════════════════════════════════════════════

def eto_materik(d: Path) -> bool:
    try:
        return (d / "GRONDHEIM_CITY").is_dir() and \
               (d / "Биржа" / "council.py").is_file() and \
               (d / "Биржа" / "stol.py").is_file()
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
                if d.is_dir() and d != OSTROV and eto_materik(d) \
                        and d not in vidno:
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
        if input("это он? [Enter — да, n — нет]: ").strip().lower() in (
                "", "y", "д", "да"):
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
# ЧТО ЕДЕТ
# ══════════════════════════════════════════════════════════════

def _musor(otn: Path) -> bool:
    if any(part in MUSOR_PAPKI for part in otn.parts):
        return True
    n = otn.name
    return (".bak" in n or n.endswith((".snesen", ".pyc", ".log",
                                       ".perenesen", ".bylo_stranicey"))
            or n == ".env")


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
        # контора бывает и у Студии (монтажёр, приёмщик) — берём только
        # биржевую: по кварталу
        birzhevoy = p.get("цех") == "торговый_хаос" or (
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


def sobrat(materik: Path, posty: list) -> list:
    plan, seen = [], set()

    def vzyat(p: Path):
        if not p.is_file():
            return
        otn = p.relative_to(materik)
        if _musor(otn) or otn in seen:
            return
        seen.add(otn)
        plan.append((p, otn))

    # 1. код Биржи + история котировок + учебный режим
    birzha = materik / "Биржа"
    for p in birzha.rglob("*.py"):
        vzyat(p)
    for p in (birzha / "test_data").glob("*.csv"):
        vzyat(p)
    vzyat(birzha / "учебный_режим.txt")

    # 2. город — только то, что Биржа зовёт
    for imya in GOROD_MODULI:
        vzyat(materik / "ГОРОД" / imya)
    vzyat(materik / "жители" / "dvizhok.py")

    # 3. Маяк — только код верхнего уровня (данные острова свои)
    for p in (materik / "Маяк").glob("*"):
        if p.is_file() and p.suffix.lower() in (".py", ".md"):
            vzyat(p)

    # 4. корень
    for imya in KOREN_FAILY:
        vzyat(materik / imya)

    # 5. цеха Биржи: мозги, промпты, знания (с образцами), манифесты
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
            if suf in KARTINKI and "знания" not in chasti:
                continue
            vzyat(p)

    # 6. учебник рук трейдера — дисциплина «финансы»
    fin = materik / "GRONDHEIM_CITY" / "Академия" / "дисциплины" / "финансы"
    if fin.is_dir():
        for p in fin.rglob("*"):
            if p.is_file() and p.suffix.lower() not in TYAZHYOLOE:
                vzyat(p)
    vzyat(materik / "GRONDHEIM_CITY" / "Академия" / "дисциплины" / "README.md")

    # 7. локации под места — только те, которых на острове нет
    for lid in zdaniya_birzhi(materik) | lokacii_postov(posty):
        d = materik / "GRONDHEIM_CITY" / "локации" / lid
        if not d.is_dir() or (OSTROV / "GRONDHEIM_CITY" / "локации" / lid).exists():
            continue
        for q in d.rglob("*"):
            if q.is_file() and q.suffix.lower() not in TYAZHYOLOE:
                vzyat(q)
    return plan


# ══════════════════════════════════════════════════════════════
# ЧТО УХОДИТ В СТАРОЕ
# ══════════════════════════════════════════════════════════════

def staroe(plan: list, posty: list) -> list:
    """Список путей острова (относительных), которые уедут в «старое»."""
    out, seen = [], set()

    def dobavit(otn: Path):
        if otn in seen or not (OSTROV / otn).exists():
            return
        # не дублируем то, что уже внутри уходящей папки
        if any(str(otn).replace("\\", "/").startswith(p + "/")
               for p in STAROE_PAPKI):
            return
        seen.add(otn)
        out.append(otn)

    # старую Биржу — целиком, только если она ещё старой эпохи (без стола).
    # Повторный запуск новую не трогает: меняются лишь отличающиеся файлы,
    # а свои прогоны и данные острова остаются на месте.
    if not novaya_epoha():
        for p in STAROE_PAPKI:
            dobavit(Path(p))
    for imya in STAROE_KOREN:
        dobavit(Path(imya))
    for p in OSTROV.glob("ostrov_main.py.bak*"):
        if not p.name.endswith("_pereselenie2"):   # свой бэкап не гоняем
            dobavit(Path(p.name))
    for src, otn in plan:                    # на чьё место ляжет новое
        if not odinakovy(src, otn):
            dobavit(otn)
    for imya, telo in posty:                 # старые пустые посты
        f = OSTROV / "GRONDHEIM_CITY" / "посты" / imya / "пост.json"
        if f.exists() and not _zanyat(f) and not _post_takoy_zhe(f, telo):
            dobavit(f.relative_to(OSTROV))
    return out


SHTAMP = Path("Биржа") / "_переселение_2.txt"


def novaya_epoha() -> bool:
    """Остров уже переселён этим скриптом — на нём стоит штамп."""
    return (OSTROV / SHTAMP).exists()


def _v_uhodyashchey(otn: Path) -> bool:
    if novaya_epoha():
        return False
    s = str(otn).replace("\\", "/")
    return any(s == p or s.startswith(p + "/") for p in STAROE_PAPKI)


def odinakovy(src: Path, otn: Path) -> bool:
    """На острове уже лежит ровно такой же файл — везти незачем."""
    import filecmp
    cel = OSTROV / otn
    if _v_uhodyashchey(otn):          # папка всё равно уезжает в «старое»
        return False
    try:
        return cel.is_file() and filecmp.cmp(src, cel, shallow=True)
    except Exception:
        return False


def _post_takoy_zhe(f: Path, telo: dict) -> bool:
    try:
        return json.loads(f.read_text(encoding="utf-8")) == telo
    except Exception:
        return False


def _zanyat(f: Path) -> bool:
    try:
        p = json.loads(f.read_text(encoding="utf-8"))
        return bool(((p.get("кто_сидит") or {}).get("имя") or "").strip())
    except Exception:
        return False


def _faylov(otn: Path) -> int:
    p = OSTROV / otn
    return sum(1 for q in p.rglob("*") if q.is_file()) if p.is_dir() else 1


# ══════════════════════════════════════════════════════════════
# ДВЕРИ ОСТРОВА
# ══════════════════════════════════════════════════════════════

METKA_DVERI = "OSTROV_DVERI_OTCHYOTA_V1"
MAIN_OLD = '@ui.page("/mayak")\ndef _mayak():\n    page_mayak()\n'
MAIN_NEW = '''# OSTROV_DVERI_OTCHYOTA_V1: отчёт прогона (кабинет Биржи ведёт сюда)
# и «← Город» из кабинета — на острове это главная острова.
from ui_otchyot import page_otchyot   # noqa: E402


@ui.page("/otchyot")
def _otchyot0():
    page_otchyot()


@ui.page("/otchyot/{ceh}")
def _otchyot1(ceh: str = "торговый_хаос"):
    page_otchyot(ceh)


@ui.page("/otchyot/{ceh}/{papka}")
def _otchyot2(ceh: str = "торговый_хаос", papka: str = ""):
    page_otchyot(ceh, papka)


@ui.page("/grondheim")
def _gorod():
    page_ostrov()


''' + MAIN_OLD
RUN_OLD = 'ui.run(title="Остров Надежды", port=8080, show=False, reload=False)'
RUN_NEW = ('ui.run(title="Остров Надежды", port=8080, show=False, reload=False,\n'
           '           storage_secret="ostrov")')
GLAV_OLD = ('for nadpis, kuda in (("МАЯК", "/mayak"), ("РАБОТА", "/rabota"),')
GLAV_NEW = ('for nadpis, kuda in (("БИРЖА", "/torg"),  # OSTROV_DVER_BIRZHI_V1\n'
            '                                 ("МАЯК", "/mayak"), ("РАБОТА", "/rabota"),')


def _pravka(put: Path, metka: str, zameny: list) -> str:
    if not put.exists():
        return "файла нет — пропускаю"
    syroy = put.read_bytes().decode("utf-8")
    crlf = "\r\n" in syroy
    t = syroy.replace("\r\n", "\n")
    if metka in t:
        return "уже стоит"
    for old, new in zameny:
        if t.count(old) != 1:
            return "не нашёл, куда вставить — оставил как есть (скажи Брату)"
        t = t.replace(old, new, 1)
    import ast
    ast.parse(t)
    shutil.copy2(put, put.with_suffix(put.suffix + ".bak_pereselenie2"))
    put.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
    return "поставлено"


# ══════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--materik", default="")
    ap.add_argument("--sdelat", action="store_true")
    a = ap.parse_args()
    dvoynoy_klik = len(sys.argv) == 1

    print("=" * 66)
    print("ПЕРЕСЕЛЕНИЕ-2 · нынешняя Биржа материка на Остров")
    print("=" * 66)

    if not (OSTROV / "OSTROV_NADEZHDY.md").exists() and \
            not (OSTROV / "ostrov_main.py").exists():
        print("x не вижу островных примет. Положи меня в КОРЕНЬ ОСТРОВА.")
        return 1
    materik = nayti_materik(a.materik)
    if materik is None:
        return 1
    if materik == OSTROV:
        print("x материк и остров — одна папка. Так нельзя.")
        return 1

    posty = posty_ostrova(materik)
    plan = sobrat(materik, posty)
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
    if not plan and not ukhodit and not posty_menyat:
        print("\nОстров уже в порядке — всё на месте, везти нечего.")
        return 0

    n_star = sum(_faylov(o) for o in ukhodit)
    print(f"\n── УХОДИТ В «СТАРОЕ» — {n_star} файлов ──")
    for o in ukhodit:
        if (OSTROV / o).is_dir() or len(o.parts) == 1:
            print(f"   {str(o):<46} {_faylov(o)}")
    melkie = [o for o in ukhodit
              if not ((OSTROV / o).is_dir() or len(o.parts) == 1)]
    if melkie:
        print(f"   + {len(melkie)} островных файлов, на чьё место ляжет новое")

    ves = sum(p.stat().st_size for p, _ in plan) / 1024 / 1024
    print(f"\n── ВЕЗУ — {len(plan)} файлов, {ves:.1f} МБ ──")
    po = {}
    for _, otn in plan:
        if otn.parts[0] == "GRONDHEIM_CITY":
            k = "/".join(otn.parts[:3])
        elif otn.parts[0] == "Биржа" and len(otn.parts) > 2:
            k = "/".join(otn.parts[:2])
        else:
            k = otn.parts[0]
        po[k] = po.get(k, 0) + 1
    for k in sorted(po):
        print(f"   {k:<46} {po[k]}")
    obrazcy = [o for _, o in plan if "образцы" in o.parts
               and o.suffix.lower() in KARTINKI]
    print(f"   (картинок-образцов в знаниях: {len(obrazcy)})")

    print(f"\n── ВАКАНСИИ, ПУСТЫЕ — {len(posty)} ──")
    for imya, telo in posty:
        f = OSTROV / "GRONDHEIM_CITY" / "посты" / imya / "пост.json"
        pom = "   [на острове занят — не трогаю]" if f.exists() and _zanyat(f) else ""
        print(f"   {telo.get('название', imya):<34} {telo.get('слот') or ''}{pom}")

    print("\n── БЕРЕГУ ──")
    print("   главную, перевозку, Застройщика, причал и пульс, запуск острова,")
    print("   фон, свод, локации острова, данные Маяка")
    print("\n── НЕ ВЕЗУ ──")
    print("   жителей (места пустые), Брата, Страницу Жизни, Архив,")
    print("   Академию кроме «финансов», прогоны и торговую историю материка,")
    print("   ключ .env")

    if not a.sdelat:
        if not dvoynoy_klik:
            print("\nЭто был показ. Сделать: python pereselenie_2.py --sdelat")
            return 0
        o = input("\nВезти? [да — везу, Enter — отмена]: ").strip().lower()
        if o not in ("да", "д", "y", "yes"):
            print("отменил, ничего не тронуто")
            return 0

    kuda = PEREEZD / datetime.now().strftime("%Y%m%d_%H%M%S")
    _i = 1
    while kuda.exists():                     # два запуска в одну секунду
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
        cel.write_text(json.dumps(telo, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    d1 = _pravka(OSTROV / "ostrov_main.py", METKA_DVERI,
                 [(MAIN_OLD, MAIN_NEW), (RUN_OLD, RUN_NEW)])
    d2 = _pravka(OSTROV / "ui_ostrov.py", "OSTROV_DVER_BIRZHI_V1",
                 [(GLAV_OLD, GLAV_NEW)])

    (OSTROV / SHTAMP).write_text(
        f"Остров переселён pereselenie_2.py {datetime.now():%d.%m.%Y %H:%M}\n"
        f"с материка: {materik}\n"
        "Пока этот штамп лежит, повторный запуск меняет только отличающиеся\n"
        "файлы и не трогает прогоны и данные острова.\n", encoding="utf-8")
    kuda.mkdir(parents=True, exist_ok=True)
    (kuda / "манифест.json").write_text(json.dumps({
        "когда": datetime.now().isoformat(timespec="seconds"),
        "что": "переселение-2: нынешняя Биржа материка",
        "материк": str(materik),
        "вакансии": [imya for imya, _ in posty],
        "убрано_в_старое": [str(o) for o in ukhodit],
        "завезено": [str(o) for _, o in plan],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "-" * 66)
    print(f"+ в «старое» {n_star}, завезено {len(plan)}, вакансий {len(posty)}")
    print(f"  двери отчёта в запуске острова: {d1}")
    print(f"  дверь «БИРЖА» на главной: {d2}")
    print(f"  старое лежит в {kuda.relative_to(OSTROV)}/старое — не удалено")
    print("\nДальше:")
    print("  1. положи в корень острова .env с ключом модели;")
    print("  2. подними остров (ОСТРОВ.bat) → дверь БИРЖА;")
    print("  3. места пустые — кого сажать, решим отдельно.")
    return 0


if __name__ == "__main__":
    try:
        _kod = main()
    except Exception as e:
        print(f"\nx сорвалось: {e}\n  Скинь это окно Брату.")
        _kod = 1
    if sys.platform == "win32" and len(sys.argv) == 1:
        try:
            input("\nEnter — закрыть окно.")
        except Exception:
            pass
    sys.exit(_kod)
