# -*- coding: utf-8 -*-
# patch_ostrov_imya_papki.py — GRONDHEIM_CITY -> OSTROV в движках острова
"""
Семь движков Биржи (скопированных с материка) зашивают в себе имя
папки данных — "GRONDHEIM_CITY". На острове эта папка называется
OSTROV (решение Шефа), поэтому движки её не найдут без правки.

Меняет ВСЕ вхождения строки "GRONDHEIM_CITY" на "OSTROV" — и в путях,
и в комментариях (комментарии тоже должны говорить правду о том, где
что лежит, а не врать про старое имя).

Список файлов и сколько вхождений ожидается (для честной проверки,
что ничего не появилось и не пропало по дороге):
    cartridge_registry.py   — 6
    council.py              — 2
    hooks.py                — 6
    kalibrovka.py           — 1
    rezident_menedzher.py   — 1
    tester_express.py       — 4
    ui_torg.py              — 2

Идемпотентно: если в файле уже нет "GRONDHEIM_CITY" — пропускает
(считает уже применённым для этого файла).

Запуск (из корня Island-of-Hope, там где лежит папка Биржа/):
    python patch_ostrov_imya_papki.py
"""
import ast
import py_compile
import shutil
import sys
from pathlib import Path

STAROE = "GRONDHEIM_CITY"
NOVOE = "OSTROV"

# (файл, ожидаемое число вхождений ДО патча)
FAILY = [
    ("cartridge_registry.py", 6),
    ("council.py", 2),
    ("hooks.py", 6),
    ("kalibrovka.py", 1),
    ("rezident_menedzher.py", 1),
    ("tester_express.py", 4),
    ("ui_torg.py", 2),
]

BIRZHA = Path("Биржа")


def main():
    if not BIRZHA.exists():
        print(f"✗ не нашёл папку {BIRZHA} — запускай из корня Island-of-Hope")
        sys.exit(1)

    vsego_ok = 0
    vsego_propuscheno = 0
    vsego_oshibok = 0

    for imya_faila, ozhidaemo in FAILY:
        target = BIRZHA / imya_faila

        if not target.exists():
            print(f"✗ {imya_faila} — файла нет в {BIRZHA}, пропускаю")
            vsego_oshibok += 1
            continue

        text = target.read_text(encoding="utf-8")
        naydeno = text.count(STAROE)

        if naydeno == 0:
            print(f"✓ {imya_faila} — уже без {STAROE}, пропускаю (уже применено)")
            vsego_propuscheno += 1
            continue

        if naydeno != ozhidaemo:
            print(f"⚠ {imya_faila} — ожидал {ozhidaemo} вхождений, нашёл {naydeno}. "
                  "Файл, видимо, менялся с тех пор, как я его смотрел. "
                  "Патчу этот файл НЕ трогаю — разберись руками, что изменилось.")
            vsego_oshibok += 1
            continue

        backup = target.with_suffix(target.suffix + ".bak_ostrov_imya")
        shutil.copy2(target, backup)

        novyy_text = text.replace(STAROE, NOVOE)

        try:
            ast.parse(novyy_text)
        except SyntaxError as e:
            print(f"✗ {imya_faila} — после замены синтаксическая ошибка: {e}")
            print("  на диск не писал, бэкап можешь удалить.")
            vsego_oshibok += 1
            continue

        target.write_text(novyy_text, encoding="utf-8")

        try:
            py_compile.compile(str(target), doraise=True)
        except py_compile.PyCompileError as e:
            print(f"✗ {imya_faila} — py_compile ругается: {e}")
            print("  откатываю из бэкапа...")
            shutil.copy2(backup, target)
            vsego_oshibok += 1
            continue

        print(f"✓ {imya_faila} — {naydeno} вхождений заменено, py_compile чисто "
              f"(бэкап: {backup.name})")
        vsego_ok += 1

    print(f"\nИтого: пропатчено {vsego_ok}, уже было готово {vsego_propuscheno}, "
          f"проблем {vsego_oshibok}")
    if vsego_oshibok:
        print("Есть проблемные файлы выше — они НЕ тронуты, разберись руками "
              "прежде чем запускать остров.")
    else:
        print("Готово. Все семь движков теперь ищут данные в OSTROV/, не в "
              "GRONDHEIM_CITY/.")


if __name__ == "__main__":
    main()
