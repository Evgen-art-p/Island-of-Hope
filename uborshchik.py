#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# UBORSHCHIK_V1
# UBORSHCHIK_OSTROVA_V1
"""
УБОРЩИК ОСТРОВА — тот же, что в городе, со списками острова (27.09).
Зовётся рукой УБОРКА на плашке главной; можно и из терминала.

Сверх городского умеет одно: «ЗАСЕЛО В РЕПЕ» — файлы, которые .gitignore
уже велит не класть в репо (кэш питона, старые переезды), но они попали
туда раньше правила. Их он убирает ИЗ РЕПЫ (git rm --cached), а на диске
они остаются как были. Фон острова не трогает.

УБОРЩИК — отделяет работающее от отработавшего. Ничего не удаляет.

    python uborshchik.py --suho     посмотреть, что нашёл (по умолчанию)
    python uborshchik.py --ubrat    перенести найденное в чулан

    python uborshchik.py --ubrat --kopii        только копии .bak/.snesen
    python uborshchik.py --ubrat --patchi       только отработавшие патчи
    python uborshchik.py --ubrat --odnorazovye  только разовые инструменты
    python uborshchik.py --ubrat --otsluzhivshie только заменённое

Запускать из КОРНЯ репо.

ЗАКОН ЭТОГО СКРИПТА

    Не удаляет. Переносит в `_УБОРКА/{дата}/`, сохраняя дорожки, и
    кладёт рядом манифест: что, откуда, какого размера и ПОЧЕМУ. Любой
    файл возвращается на место одной строкой из манифеста.

    По умолчанию — сухой прогон. Убирает только по прямому `--ubrat`.

    Работающее не трогает вообще: движки, кабинеты, мозги, знания,
    паспорта, документы города, данные. Список неприкасаемых — ниже, и
    он проверяется до всякого переноса.

КАК ОН РЕШАЕТ, ЧТО ОТРАБОТАЛО

    ПАТЧИ — по маркеру. Каждый патч, накатываясь, оставляет в целевом
    файле свою метку. Уборщик читает метку из самого патча и ищет её по
    репо. Нашлась — патч сделал дело, его место в чулане. НЕ нашлась —
    патч ещё не накатан, и уборщик его НЕ ТРОГАЕТ, а говорит об этом.
    Правило работает и для будущих патчей, ничего дописывать не надо.

    КОПИИ — по имени: `*.bak*` и `*.snesen`. Это следы патчей, а не
    работа. Оригиналы на месте, история в git.

    РАЗОВЫЕ ИНСТРУМЕНТЫ и ЗАМЕНЁННОЕ — поимённо, с причиной у каждого.
    Наугад тут нельзя, поэтому список короткий и проверяемый.

ЧТО ОН ПОКАЗЫВАЕТ, НО НЕ ТРОГАЕТ

    «Под вопросом» — файлы, которых никто не зовёт: ни импортом, ни по
    имени. Это ПОДОЗРЕНИЕ, а не приговор: скрипт могли запускать руками
    или он ждёт своего часа. Решает Шеф, уборщик только показывает.
"""
import argparse
import ast
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

KOREN = Path(__file__).resolve().parent
CHULAN = KOREN / "_УБОРКА"
YA = Path(__file__).name

# ── куда не заходим вовсе ─────────────────────────────────────
NE_ZAHODIT = {"_ARCHIVE", "_OLD", "_АРХИВ_ЧИСТКИ", "_УБОРКА",
              "_ПЕРЕЕЗД", "_ОТПРАВКА", "_ПРИБЫТИЕ", "фон",
              ".git", ".vscode", "__pycache__", "node_modules"}

# ── папки, которые грузятся ЦЕЛИКОМ, по имени папки ───────────
# `истоки/` и `памяти/` — плагины: обходчик берёт папку и подхватывает
# каждый файл сам. Их никто не импортирует по имени, и это НОРМАЛЬНО:
# так задумано. Без этой оговорки уборщик записал бы их в мёртвые.
PLAGINY = ("истоки", "памяти")

# ── что не трогаем ни при каких условиях ──────────────────────
# Точки входа и живые двери города. Их «никто не импортирует» — это
# нормально: их запускает Шеф руками, а не код.
NEPRIKASAEMYE = {
    # живые двери ОСТРОВА: запуск, главная, её руки, перевозка, Застройщик,
    # пульс домой, переселение (им остров подтягивает Биржу с материка)
    "ostrov_main.py", "остров.py", "ostrov_puls.py", "ui_ostrov.py",
    "ruki_ostrova.py", "uborshchik.py", "perevozka.py", "ui_perevozka.py",
    "ui_zastroyshchik.py", "pereselenie_2.py", "ubrat_klyuch.py",
    "sostoyanie.py",
}

# ── разовые инструменты: сделали дело, лежат мёртвым весом ────
RAZOVYE = {
    # ключ «./имя» — только корень острова. Бирж­евые файлы здесь не
    # убираем: они зеркало материка, переселение привезёт их снова.
    "./pereselenie.py": "первое переселение (10.08, эпоха Искры) — заменено pereselenie_2.py",
    "./obnovit_doki.py": "разовая правка документов от 13.08 — документы с тех пор переписаны",
}

# батники: у каждого теперь есть кнопка или страница в городе
BATNIKI = {}   # ОСТРОВ.bat и УБРАТЬ_КЛЮЧ.bat — живые

# ── заменённое: работу делает кто-то другой ───────────────────
OTSLUZHIVSHIE = {}


def _vnutri_arhiva(p: Path) -> bool:
    return any(part in NE_ZAHODIT for part in p.parts)


def _vse_faily():
    for p in KOREN.rglob("*"):
        if p.is_file() and not _vnutri_arhiva(p.relative_to(KOREN)):
            yield p


def _tekstovye():
    """Файлы, в которых имеет смысл искать маркеры и упоминания."""
    for p in _vse_faily():
        if p.suffix.lower() in (".py", ".md", ".json", ".txt"):
            try:
                yield p, p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue


# ══════════════════════════════════════════════════════════════
# СБОР
# ══════════════════════════════════════════════════════════════

def sobrat_kopii() -> list:
    """Следы патчей: *.bak* и *.snesen. Оригиналы на месте."""
    out = []
    for p in _vse_faily():
        n = p.name
        if ".bak" in n or n.endswith(".snesen"):
            out.append((p, "копия, оставленная патчем (оригинал на месте)"))
    return out


# METKI_LYUBYE_V1 (27.09): метка патча — не только MARKER. Наши патчи
# зовут её и METKA, и METKA_SV, и MARKER_G — уборщик видел только
# первую форму, и десятки накатанных патчей лежали в корне вечно.
# Теперь берётся любая константа MARKER*/METKA*, из её значения —
# слово вида ЧТО_ТО_V1. Накатан, только если стоят ВСЕ его метки.
# Ищем их в городе, но НЕ в соседних патчах корня: метка, которую
# лишь упомянул другой патч, ещё не значит, что работа сделана.
_METKA_IMYA = re.compile(r'^(?:MARKER|METKA)[A-Z0-9_]*\s*=\s*[\'"]([^\'"\n]+)[\'"]', re.M)
_METKA_ZNAK = re.compile(r'[A-Z][A-Z0-9_]*_V\d+')


def _metki_patcha(src: str) -> list:
    out = []
    for m in _METKA_IMYA.finditer(src):
        z = _METKA_ZNAK.search(m.group(1))
        if z and z.group(0) not in out:
            out.append(z.group(0))
    return out


def sobrat_patchi(teksty: dict) -> tuple:
    """Патчи, чьи метки уже стоят в городе, — значит отработали.

    Возвращает (отработавшие, не_тронутые)."""
    gotovye, zhdut = [], []
    gde_iskat = {q: t for q, t in teksty.items()
                 if not (q.parent == KOREN and q.suffix == ".py"
                         and q.name not in NEPRIKASAEMYE)}
    for p in sorted(KOREN.glob("*.py")):
        if p.name in NEPRIKASAEMYE:
            continue
        if ("./" + p.name) in RAZOVYE:   # RASKLADKA_27_09_V1: уберётся списком
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        metki = _metki_patcha(src)
        if not metki:
            zhdut.append((p, "меток внутри нет — что это, не знаю; реши сам"))
            continue
        net = [m for m in metki
               if not any(m in t for t in gde_iskat.values())]
        if net:
            zhdut.append((p, f"метки {net[0]} в городе нет — патч ещё НЕ накатан"))
            continue
        gde = sorted({q.name for q, t in gde_iskat.items() if metki[0] in t})
        gotovye.append((p, f"накатан — метка {metki[0][:28]} "
                           f"стоит в {', '.join(gde[:3])}"))
    return gotovye, zhdut


def sobrat_batniki() -> list:
    """Батники, которым в городе нашлась кнопка. Ищем только в корне."""
    out = []
    for imya, prichina in BATNIKI.items():
        p = KOREN / imya
        if p.exists():
            out.append((p, prichina))
    return out


def _po_puti(klyuch: str) -> Path:
    """RASKLADKA_27_09_V1: «./имя» — корень, «Дом/имя» — точно там."""
    return KOREN / (klyuch[2:] if klyuch.startswith("./") else klyuch)


def sobrat_poimenno(spisok: dict) -> list:
    out = []
    # ключ с «/» — точный путь от корня (одноимённые в домах не трогаем)
    for k, prichina in spisok.items():
        if "/" in k:
            p = _po_puti(k)
            if p.is_file() and not _vnutri_arhiva(p.relative_to(KOREN)):
                out.append((p, prichina))
    for p in _vse_faily():
        if p.name in spisok and p.name not in NEPRIKASAEMYE:
            out.append((p, spisok[p.name]))
    return out


def sobrat_pod_voprosom(teksty: dict) -> list:
    """Модули, которых никто не зовёт. ПОКАЗЫВАЕМ, не трогаем."""
    py = [p for p in _vse_faily() if p.suffix == ".py"]
    importy = set()
    for p in py:
        try:
            tree = ast.parse(teksty.get(p, ""))
        except Exception:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    importy.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom) and n.module:
                importy.add(n.module.split(".")[0])
    vsyo = "\n".join(teksty.values())
    out = []
    for p in py:
        if p.name in NEPRIKASAEMYE or p.name == YA:
            continue
        if p.name.startswith(("patch_", "postavit_")):
            continue
        if p.parent == KOREN and _metki_patcha(teksty.get(p, "")):
            continue          # патч с меткой — его судит сбор патчей
        if p.name in RAZOVYE or p.name in OTSLUZHIVSHIE:
            continue
        if str(p.relative_to(KOREN)).replace("\\", "/") in RAZOVYE or \
                ("./" + p.name) in RAZOVYE and p.parent == KOREN:
            continue
        if p.name == "kalibrovka.py":
            continue          # показан отдельно, как недоделка
        if p.stem in importy:
            continue
        if any(part in PLAGINY for part in p.relative_to(KOREN).parts):
            continue          # плагин: грузится по папке, не по имени
        if vsyo.count(p.name) > 1:      # упоминается где-то по имени
            continue
        out.append(p)
    return out


# ══════════════════════════════════════════════════════════════
# ЗАСЕЛО В РЕПЕ — .gitignore велит не класть, а оно уже там
# ══════════════════════════════════════════════════════════════

NE_TROGAT_V_REPE = ("фон/",)   # картинка острова — пусть едет с репой


def _git(*args):
    import subprocess
    return subprocess.run(["git", "-c", "core.quotepath=false", *args],
                          cwd=str(KOREN), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def zaselo_v_repe() -> list:
    """Файлы, которые git хранит, хотя .gitignore их уже закрыл."""
    try:
        r = _git("ls-files", "-ci", "--exclude-standard")
    except Exception:
        return []
    if r.returncode != 0:
        return []
    out = []
    for stroka in r.stdout.splitlines():
        s = stroka.strip().strip('"')
        if s and not s.startswith(NE_TROGAT_V_REPE):
            out.append(s)
    return out


def ubrat_iz_repy(puti: list) -> tuple:
    """git rm --cached: из репы уходит, на диске остаётся."""
    if not puti:
        return True, "нечего"
    ubrano = 0
    for i in range(0, len(puti), 100):
        kusok = puti[i:i + 100]
        r = _git("rm", "-r", "--cached", "--quiet", "--", *kusok)
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or "git не справился").strip()[:300]
        ubrano += len(kusok)
    return True, (f"из репы убрано {ubrano} — на диске всё на месте. "
                  "Отправь изменения в GitHub, как обычно.")


# ══════════════════════════════════════════════════════════════
# ПЕРЕНОС
# ══════════════════════════════════════════════════════════════

def perenesti(nahodki: list, ubrat: bool) -> dict:
    if not nahodki:
        return {}
    kuda = CHULAN / datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = []
    _bylo = set()   # RASKLADKA_27_09_V1: один файл — один переезд
    for p, prichina in nahodki:
        if p in _bylo or not p.exists():
            continue
        _bylo.add(p)
        otn = p.relative_to(KOREN)
        zapis = {"откуда": str(otn), "размер": p.stat().st_size,
                 "почему": prichina}
        if ubrat:
            cel = kuda / otn
            cel.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(cel))
            zapis["куда"] = str(cel.relative_to(KOREN))
        manifest.append(zapis)
    if ubrat:
        (kuda / "манифест.json").write_text(
            json.dumps({"когда": datetime.now().isoformat(timespec="seconds"),
                        "всего": len(manifest), "файлы": manifest},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        (kuda / "КАК_ВЕРНУТЬ.txt").write_text(
            "Ничего не удалено — всё лежит здесь, дорожки сохранены.\n"
            "Вернуть один файл: скопировать его отсюда обратно по пути\n"
            "из поля «откуда» в манифест.json.\n"
            "Вернуть всё: скопировать содержимое этой папки в корень репо\n"
            "с сохранением дорожек (манифест и эту записку не копировать).\n",
            encoding="utf-8")
    return {"папка": kuda, "манифест": manifest}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ubrat", action="store_true",
                    help="реально перенести (без него — только показ)")
    ap.add_argument("--suho", action="store_true", help="только показать")
    ap.add_argument("--kopii", action="store_true")
    ap.add_argument("--patchi", action="store_true")
    ap.add_argument("--odnorazovye", action="store_true")
    ap.add_argument("--otsluzhivshie", action="store_true")
    a = ap.parse_args()

    if not (KOREN / "GRONDHEIM_CITY").exists():
        print("x не вижу GRONDHEIM_CITY — запускай из КОРНЯ репо")
        return 1

    vybrany = any([a.kopii, a.patchi, a.odnorazovye, a.otsluzhivshie])
    hochu = {
        "копии": a.kopii or not vybrany,
        "патчи": a.patchi or not vybrany,
        "разовые": a.odnorazovye or not vybrany,
        "заменённое": a.otsluzhivshie or not vybrany,
    }
    ubrat = a.ubrat and not a.suho

    print("=" * 66)
    print("УБОРЩИК" + ("" if ubrat else "   [СУХОЙ ПРОГОН — ничего не трогаю]"))
    print("=" * 66)

    teksty = dict(_tekstovye())
    gotovye, zhdut = sobrat_patchi(teksty)

    gruppy = []
    if hochu["копии"]:
        gruppy.append(("КОПИИ, ОСТАВЛЕННЫЕ ПАТЧАМИ", sobrat_kopii()))
    if hochu["патчи"]:
        gruppy.append(("ПАТЧИ, КОТОРЫЕ УЖЕ ОТРАБОТАЛИ", gotovye))
    if hochu["разовые"]:
        gruppy.append(("РАЗОВЫЕ ИНСТРУМЕНТЫ", sobrat_poimenno(RAZOVYE)))
    if hochu["заменённое"]:
        gruppy.append(("ЗАМЕНЁННОЕ ДРУГИМ", sobrat_poimenno(OTSLUZHIVSHIE)))
        gruppy.append(("БАТНИКИ, У КОТОРЫХ ЕСТЬ КНОПКА", sobrat_batniki()))

    nahodki = []
    for imya, spisok in gruppy:
        print(f"\n── {imya} — {len(spisok)} ──")
        for p, prichina in sorted(spisok, key=lambda x: str(x[0])):
            print(f"   {p.relative_to(KOREN)}")
            print(f"      · {prichina}")
        nahodki += spisok

    if zhdut:
        print(f"\n── ПАТЧИ, КОТОРЫЕ НЕ ТРОГАЮ — {len(zhdut)} ──")
        for p, prichina in zhdut:
            print(f"   {p.name}\n      · {prichina}")

    # не мусор, а НЕДОДЕЛКА: задумка живёт в манифесте цеха, кода никто
    # не зовёт. Такое не выбрасывают — про такое напоминают.
    NEDODELKI = {}
    nedodelano = [p for p in _vse_faily() if p.name in NEDODELKI]
    if nedodelano:
        print(f"\n── НЕ ПОДКЛЮЧЕНО (показываю, НЕ трогаю) — "
              f"{len(nedodelano)} ──")
        print("   Это не мусор. Это задумка, до которой руки не дошли.")
        for p in sorted(nedodelano, key=str):
            print(f"   {p.relative_to(KOREN)}")
            print(f"      · {NEDODELKI[p.name]}")

    pod_voprosom = sobrat_pod_voprosom(teksty)
    if pod_voprosom:
        print(f"\n── ПОД ВОПРОСОМ (показываю, НЕ трогаю) — "
              f"{len(pod_voprosom)} ──")
        print("   Их никто не зовёт ни импортом, ни по имени. Это подозрение,")
        print("   а не приговор: реши сам, нужны они или нет.")
        print("   (плагины из папок вроде истоки/ сюда НЕ попадают — они")
        print("    грузятся по папке, и это задумано)")
        for p in sorted(pod_voprosom, key=str):
            print(f"   {p.relative_to(KOREN)}")

    zaselo = zaselo_v_repe()
    if zaselo:
        print(f"\n── ЗАСЕЛО В РЕПЕ (на диске не трогаю) — {len(zaselo)} ──")
        for s in zaselo[:30]:
            print(f"   {s}")
        if len(zaselo) > 30:
            print(f"   … и ещё {len(zaselo) - 30}")
        if ubrat:
            print("   " + ubrat_iz_repy(zaselo)[1])

    print("\n" + "-" * 66)
    if not nahodki:
        print("Убирать нечего — чисто.")
        return 0

    itog = sum(p.stat().st_size for p, _ in nahodki) / 1024
    print(f"Всего к уборке: {len(nahodki)} файлов, {itog:.0f} КБ")

    if not ubrat:
        print("\nЭто был показ. Убрать по-настоящему:")
        print("    python uborshchik.py --ubrat")
        print("Ничего не удаляется — всё переедет в _УБОРКА/ с манифестом.")
        return 0

    res = perenesti(nahodki, True)
    print(f"\n+ перенесено в {res['папка'].relative_to(KOREN)}")
    print("  рядом лежат манифест.json и КАК_ВЕРНУТЬ.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())

