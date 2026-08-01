# -*- coding: utf-8 -*-
# patch_grondheim_city_imya_papki.py — OSTROV -> GRONDHEIM_CITY
"""
Обратный патч к patch_ostrov_imya_papki.py — тот менял GRONDHEIM_CITY
на OSTROV; сейчас Шеф переименовал папку данных ОБРАТНО в
GRONDHEIM_CITY, а семь движков после того патча всё ещё ищут OSTROV.
Молча ломались — Python не кричит на несуществующую подпапку, просто
list_ceha() и все, кто её зовёт, честно возвращают пусто.

Меняет ВСЕ вхождения строки "OSTROV" на "GRONDHEIM_CITY" в тех же
семи файлах, что патчил прошлый раз — в путях и в комментариях.

Идемпотентно: если в файле уже нет "OSTROV" (как отдельного слова
в контексте пути — проверяем по факту "OSTROV" нет вовсе) — пропускает.

Запуск (из корня Island-of-Hope, там где лежит папка Биржа/):
    python patch_grondheim_city_imya_papki.py
"""
import ast
import py_compile
import shutil
import sys
from pathlib import Path

STAROE = "OSTROV"
NOVOE = "GRONDHEIM_CITY"

FAILY = [
    "cartridge_registry.py",
    "council.py",
    "hooks.py",
    "kalibrovka.py",
    "rezident_menedzher.py",
    "tester_express.py",
    "ui_torg.py",
]

BIRZHA = Path("Биржа")


def main():
    if not BIRZHA.exists():
        print(f"✗ не нашёл папку {BIRZHA} — запускай из корня Island-of-Hope")
        sys.exit(1)

    vsego_ok = 0
    vsego_propuscheno = 0
    vsego_oshibok = 0

    for imya_faila in FAILY:
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

        backup = target.with_suffix(target.suffix + ".bak_grondheim_city_imya")
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
        print("Есть проблемные файлы выше — они НЕ тронуты, разберись руками.")
    else:
        print("Готово. Все семь движков снова ищут данные в GRONDHEIM_CITY/, "
              "как папка и называется сейчас.")


if __name__ == "__main__":
    main()
