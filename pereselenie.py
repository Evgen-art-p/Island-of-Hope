#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PERESELENIE_V2
"""
ПЕРЕСЕЛЕНИЕ — везём на остров БИРЖУ и её людей. Город остаётся дома.

    python pereselenie.py             найдёт материк сам и покажет
    python pereselenie.py --sdelat    сделает

Запускать ИЗ КОРНЯ ОСТРОВА. По умолчанию — только показ.
Путей прописывать не надо: скрипт ищет материк по соседним папкам.

ЧТО ВЕЗЁМ (по слову Шефа)

    · БИРЖУ С ВАКАНСИЯМИ — цех торгового хаоса и контору, с мозгами,
      бумагой, знаниями и манифестами. Места едут ПУСТЫМИ: кто на них
      сядет, решишь на месте;
    · СВОЙ МАЯК, не один причал. На острове он такой же, как на
      материке: гнёзда, доска, хранитель. Через него и подключается
      МТ5 — исток втыкается в гнездо и там горит, видно, откуда течёт;
    · ХРАНИТЕЛЯ МАЯКА — пустым постом. Место есть, человека нет;
    · страницу работы с локациями и ролями — своя, островная;
    · локации, которые эти места дают: здание Биржи, квартал и Маяк.
      Вакансию обеспечивает локация, без её паспорта места повиснут
      ничьими.

ЖИТЕЛЕЙ НЕ ВЕЗЁМ

    Ни одного. Слово Шефа: жителей берём с материка — тогда, когда
    решим кого. Остров получает пустые вакансии и ждёт людей.

    Посты приезжают очищенными: без имён и без чужой трудовой истории.
    Материковая работа человека — материковая; на острове у него будет
    своя запись, с первого дня.

ЧЕГО НЕ ВЕЗЁМ ЕЩЁ

    Кабинет Брата, Страницу Жизни, Академию, Архив, Хексагон, карту,
    прочие локации. Это материк: там учат, рожают, помнят и правят.
    Остров — рабочее место, а не второй город.

    Не везём и торговую историю материка: дневники, статистику, атлас,
    позиции. У острова свой счёт и своя судьба.

ЧТО КЛАДЁТ СВЕРХУ

    `ostrov_main.py` — свой лёгкий запуск. Городского `main.py` здесь
    нет и не нужно: он поднимает кабинеты, которых мы не везём.
    Остров открывает две двери: кабинет Биржи и страницу работы.
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

BEREZHYOM = {".git", ".gitignore", ".gitattributes", "README.md",
             "OSTROV_NADEZHDY.md", "ostrov_puls.py", "_ПЕРЕЕЗД",
             Path(__file__).name}

MUSOR_PAPKI = {"__pycache__", ".git", ".vscode", "node_modules",
               "_ARCHIVE", "_OLD", "_АРХИВ_ЧИСТКИ", "_УБОРКА", "_ПЕРЕЕЗД"}

# у жителя везём только то, чем он ЕСТЬ. Прочитанное, чаты и склады —
# материковая кухня, острову она не работает.
ZHITEL_NE_VEZYOM = {"прочитано", "чаты", "академия_чаты", "ректор_чаты",
                    "руда", "медиа", "архив"}
TYAZHYOLOE = {".mp3", ".wav", ".zip", ".mp4", ".mov", ".jpeg", ".jpg",
              ".png", ".webp", ".gif"}

CEHA_BIRZHI = ("торговый_хаос", "контора")
# посты, которые едут сверх цеховых: у Маяка свой хранитель, и место
# ему нужно даже пустым — иначе доска будет без хозяина навсегда.
POSTY_SVERH = ("khranitel_mayaka",)


OSTROV_MAIN = '''# -*- coding: utf-8 -*-
# OSTROV_MAIN_V1
"""
ОСТРОВ — лёгкий запуск. Две двери, и обе рабочие.

    python ostrov_main.py

Городского main.py здесь нет нарочно: он поднимает кабинет Брата,
Страницу Жизни, Академию и карту — всего этого на острове не держим.
Остров — рабочее место: кабинет Биржи и страница работы.

    /        главная — фон, стеклянная плашка, двери
    /torg    кабинет Биржи — стол, кадр, разговор, РЫНОК и ВАХТА
    /rabota  места и локации — принять, уволить, поправить бланк
    /mayak   доска Маяка — гнёзда, связь с материком, откуда течёт МТ5

Главная ставится отдельно: postavit_glavnuyu.py. Пока её нет — корень
кидает в кабинет, чтобы дверь не была глухой.
"""
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent
for _p in (KOREN, KOREN / "Биржа", KOREN / "ГОРОД", KOREN / "жители",
           KOREN / "Маяк"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from nicegui import ui   # noqa: E402

from ui_torg import page_torg      # noqa: E402
from ui_rabota import page_rabota  # noqa: E402
from ui_mayak import page_mayak    # noqa: E402


@ui.page("/")
def _dom():
    ui.navigate.to("/torg")


@ui.page("/torg")
def _torg0():
    page_torg()


@ui.page("/torg/{tseh_id}")
def _torg(tseh_id: str = "торговый_хаос"):
    page_torg(tseh_id)


@ui.page("/rabota")
def _rabota():
    page_rabota()


@ui.page("/mayak")
def _mayak():
    page_mayak()


if __name__ in {"__main__", "__mp_main__"}:
    print("ОСТРОВ: кабинет /torg, работа /rabota, маяк /mayak")
    ui.run(title="Остров Надежды", port=8080, show=False, reload=False)
'''


def _musor(otn: Path) -> bool:
    if any(part in MUSOR_PAPKI for part in otn.parts):
        return True
    n = otn.name
    return ".bak" in n or n.endswith((".snesen", ".pyc", ".log")) or n == ".env"


def eto_materik(d: Path) -> bool:
    try:
        return (d / "GRONDHEIM_CITY").is_dir() and \
               (d / "Биржа" / "council.py").is_file()
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
        print(f"x по этому пути города нет: {d}")
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
    print(f"x по этому пути города нет: {d}")
    return None


# ══════════════════════════════════════════════════════════════
# КТО И ЧТО ЕДЕТ
# ══════════════════════════════════════════════════════════════

def lyudi_birzhi(materik: Path) -> set:
    """Кто сидит на местах Биржи. Спрашиваем два источника: посты
    (нынешняя правда) и маски (старый порядок) — чтобы не забыть
    никого, кто уже работает."""
    imena = set()
    posty = materik / "GRONDHEIM_CITY" / "посты"
    if posty.is_dir():
        for d in posty.iterdir():
            f = d / "пост.json"
            if not f.is_file():
                continue
            try:
                p = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if p.get("цех") in CEHA_BIRZHI:
                kto = ((p.get("кто_сидит") or {}).get("имя") or "").strip()
                if kto:
                    imena.add(kto)
    kovcheg = materik / "GRONDHEIM_CITY" / "жители" / "ковчег"
    if kovcheg.is_dir():
        for d in kovcheg.iterdir():
            mf = d / "маски" / "работа" / "mask.json"
            if not mf.is_file():
                continue
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                continue
            if m.get("Workshop_ID") in CEHA_BIRZHI:
                imya = d.name
                pp = d / "passport.json"
                if pp.is_file():
                    try:
                        imya = json.loads(pp.read_text(
                            encoding="utf-8")).get("Official_Name", d.name)
                    except Exception:
                        pass
                imena.add(str(imya).strip())
    return imena


def zdaniya_birzhi(materik: Path) -> set:
    """Локации, в которых стоят цеха Биржи."""
    ids = set()
    ceha = materik / "GRONDHEIM_CITY" / "Биржа" / "цеха"
    if not ceha.is_dir():
        return ids
    for d in ceha.iterdir():
        f = d / "manifest.json"
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


def sobrat(materik: Path, s_dannymi: bool) -> list:
    plan, seen = [], set()

    def vzyat(p: Path):
        if not p.is_file():
            return
        otn = p.relative_to(materik)
        if _musor(otn) or otn in seen:
            return
        if not s_dannymi and "данные" in [x.lower() for x in otn.parts]:
            return
        seen.add(otn)
        plan.append((p, otn))

    for p in (materik / "Биржа").rglob("*.py"):
        vzyat(p)
    for imya in ("rabota.py", "ui_rabota.py", "gnezda.py"):
        vzyat(materik / "ГОРОД" / imya)
    vzyat(materik / "жители" / "dvizhok.py")
    # Маяк целиком: гнёзда, доска, хранитель, причал — свой, как дома
    for p in (materik / "Маяк").rglob("*"):
        if p.is_file() and p.suffix.lower() in (".py", ".md"):
            vzyat(p)
    for imya in ("rabota_pult.py", "proverka_kotirovok.py",
                 "proverka_stola.py", "proverka_zreniya.py",
                 "stol_pokazat.py", "istoki_pokazat.py", "sostoyanie.py",
                 "БИРЖА.md"):
        vzyat(materik / imya)
    for ceh in CEHA_BIRZHI:
        d = materik / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() not in TYAZHYOLOE:
                    vzyat(p)
    # локации, которые дают эти места: здания цехов и дом Маяка
    for lid in zdaniya_birzhi(materik) | lokacii_postov(materik):
        d = materik / "GRONDHEIM_CITY" / "локации" / lid
        if d.is_dir():
            for q in d.rglob("*"):
                if q.is_file() and q.suffix.lower() not in TYAZHYOLOE:
                    vzyat(q)
    # ЖИТЕЛЕЙ НЕ ВЕЗЁМ — слово Шефа. Их берём с материка потом.
    return plan


def posty_ostrova(materik: Path) -> list:
    """Посты, которые едут: цеховые вакансии Биржи плюс хранитель Маяка.

    Едут ОЧИЩЕННЫМИ: без имени сидящего и без чужой трудовой истории.
    Материковая работа человека остаётся материковой; на острове у него
    начнётся своя запись, с первого дня."""
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
        if p.get("цех") not in CEHA_BIRZHI and d.name not in POSTY_SVERH:
            continue
        p["кто_сидит"] = None
        p["трудовая_история"] = []
        p["_note_ostrov"] = ("вакансия острова. Приехала с материка пустой: "
                             "имена и трудовая история там и остались.")
        out.append((d.name, p))
    return out


def lokacii_postov(materik: Path) -> set:
    """Локации, на которые ссылаются едущие посты."""
    return {(p.get("локация") or p.get("где") or "").strip()
            for _, p in posty_ostrova(materik)} - {""}


def ubrat_staroe(sdelat: bool, kuda: Path) -> list:
    ushlo = []
    for p in sorted(OSTROV.iterdir()):
        if p.name in BEREZHYOM:
            continue
        faily = [q for q in p.rglob("*") if q.is_file()] if p.is_dir() else [p]
        ushlo += [str(q.relative_to(OSTROV)) for q in faily]
        if sdelat:
            cel = kuda / "старое" / p.relative_to(OSTROV)
            cel.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(cel))
    return ushlo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--materik", default="")
    ap.add_argument("--sdelat", action="store_true")
    ap.add_argument("--s-dannymi", action="store_true",
                    help="везти и торговую историю материка")
    a = ap.parse_args()

    print("=" * 66)
    print("ПЕРЕСЕЛЕНИЕ · Биржа и её люди" +
          ("" if a.sdelat else "   [СУХОЙ ПРОГОН]"))
    print("=" * 66)

    materik = nayti_materik(a.materik)
    if materik is None:
        return 1
    if materik == OSTROV:
        print("x материк и остров — одна папка. Так нельзя.")
        return 1
    if not (OSTROV / "OSTROV_NADEZHDY.md").exists() and \
            not (OSTROV / "ostrov_puls.py").exists() and any(OSTROV.iterdir()):
        print("x не вижу островных примет, а папка не пустая.")
        print("  Кладу скрипт в корень ОСТРОВА и запускаю оттуда.")
        return 1

    posty = posty_ostrova(materik)
    plan = sobrat(materik, a.s_dannymi)
    if not plan:
        print("x с материка нечего везти — проверь путь")
        return 1

    kuda = PEREEZD / datetime.now().strftime("%Y%m%d_%H%M%S")
    ushlo = ubrat_staroe(a.sdelat, kuda)

    print(f"\n── УБИРАЮ СТАРОЕ — {len(ushlo)} файлов ──")
    print("   берегу: README.md, OSTROV_NADEZHDY.md, ostrov_puls.py, .git")

    ves = sum(p.stat().st_size for p, _ in plan) / 1024 / 1024
    print(f"\n── ВЕЗУ — {len(plan)} файлов, {ves:.1f} МБ ──")
    po = {}
    for _, otn in plan:
        klyuch = "/".join(otn.parts[:3]) if otn.parts[0] == "GRONDHEIM_CITY" \
            else otn.parts[0]
        po[klyuch] = po.get(klyuch, 0) + 1
    for k in sorted(po):
        print(f"   {k:<46} {po[k]}")
    print(f"\n── ВАКАНСИИ, ПУСТЫЕ — {len(posty)} ──")
    for imya, telo in posty:
        gde = telo.get("цех") or telo.get("локация") or ""
        print(f"   {telo.get('название', imya):<32} {gde}")
    if not posty:
        print("   постов не нашёл — проверь, заведён ли стандарт работы")

    print("\n── НЕ ВЕЗУ ──")
    print("   ЖИТЕЛЕЙ — ни одного. Их берём с материка, когда решишь кого")
    print("   кабинет Брата, Страницу Жизни, Академию, Архив, карту,")
    print("   прочие локации — это материк")
    print("   торговую историю материка" +
          ("   [везу, ты просил]" if a.s_dannymi else ""))

    if not a.sdelat:
        print("\n" + "-" * 66)
        print("Это был показ. Сделать: python pereselenie.py --sdelat")
        return 0

    for p, otn in plan:
        cel = OSTROV / otn
        cel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, cel)
    for imya, telo in posty:
        cel = OSTROV / "GRONDHEIM_CITY" / "посты" / imya / "пост.json"
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps(telo, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    (OSTROV / "ostrov_main.py").write_text(OSTROV_MAIN, encoding="utf-8")

    kuda.mkdir(parents=True, exist_ok=True)
    (kuda / "манифест.json").write_text(json.dumps({
        "когда": datetime.now().isoformat(timespec="seconds"),
        "материк": str(materik),
        "вакансии": [imya for imya, _ in posty],
        "убрано": ushlo, "завезено": [str(o) for _, o in plan],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "-" * 66)
    print(f"+ убрано {len(ushlo)}, завезено {len(plan)}, "
          f"вакансий {len(posty)}, положен ostrov_main.py")
    print(f"  старое лежит в {kuda.relative_to(OSTROV)}/старое — не удалено")
    print("\nДальше руками:")
    print("  1. положи .env с ключом модели;")
    print("  2. поставь MetaTrader и залогинь счёт ОСТРОВА;")
    print("  3. python proverka_kotirovok.py")
    print("  4. python ostrov_main.py — /torg, /rabota, /mayak")
    print("  5. людей везём отдельно, когда решишь кого сажать")
    return 0


if __name__ == "__main__":
    _kod = main()
    if sys.platform == "win32" and len(sys.argv) == 1:
        try:
            input("\nготово. Enter — закрыть окно.")
        except Exception:
            pass
    sys.exit(_kod)
