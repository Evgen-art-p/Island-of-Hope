# -*- coding: utf-8 -*-
# VERNUT_OTCHYOT_V1
"""
ВЕРНУТЬ ОТЧЁТ · страницу положили под его именем

БЕДА. В прогоне: «[ОТЧЁТ] не завёлся (module 'otchyot' has no
attribute 'Otchyot') — прогон пойдёт без записи». Из-за этого ни
одного места не записывается, и страница отчёта пуста.

ПРИЧИНА. В `Биржа/otchyot.py` лежит СТРАНИЦА отчёта (та, что должна
называться `ui_otchyot.py`). Она затёрла модуль записи — тот, в
котором живёт класс `Otchyot`.

Настоящий отчёт цел: он в `Биржа/otchyot.py.bak_zhurnal`, класс на
месте. Страница тоже цела и лежит правильно — `Биржа/ui_otchyot.py`.

ЧТО ДЕЛАЕТ ПАТЧ. Возвращает модуль записи из бэкапа на своё место.
Перед этим убеждается, что там действительно страница, а в бэкапе
действительно класс — вслепую не перезаписывает.

ПОСЛЕ ЭТОГО НАДО НАКАТИТЬ ЗАНОВО `postavit_zhurnal_progona.py`:
бэкап сделан ДО него, в нём ещё нет полей «действие», «цена_входа»,
«стоп_входа». Патч journal встанет на возвращённый файл и допишет их.

КУДА КЛАСТЬ ЭТОТ ФАЙЛ: в корень репы, рядом с main.py.

БЕЗОПАСНОСТЬ: нынешний `otchyot.py` не удаляется — сохраняется как
`otchyot.py.bylo_stranicey`, на случай если я что-то не так понял.

    python vernut_otchyot.py --suho
    python vernut_otchyot.py

`шесть·проверено·до·корня`
"""
import shutil
import sys
from pathlib import Path

SUHO = "--suho" in sys.argv

_REPO = Path(__file__).resolve().parent
OTCH = _REPO / "Биржа" / "otchyot.py"
BAK = _REPO / "Биржа" / "otchyot.py.bak_zhurnal"
STRANICA = _REPO / "Биржа" / "ui_otchyot.py"


def main():
    print()
    print("ВЕРНУТЬ ОТЧЁТ" + ("  · СУХОЙ ПРОГОН" if SUHO else ""))
    print("корень:", _REPO)
    print()

    if not OTCH.exists():
        print("!! Биржа/otchyot.py нет вовсе")
        if BAK.exists():
            print("   бэкап есть — верну его")
        else:
            print("   и бэкапа нет. Останови и скажи мне.")
            return

    tek = OTCH.read_text(encoding="utf-8", errors="ignore") if OTCH.exists() else ""
    if "class Otchyot" in tek:
        print("Отчёт на месте, класс Otchyot есть. Возвращать нечего.")
        if "действие" not in tek:
            print("НО: полей журнала («действие», «цена_входа») нет —")
            print("    накати postavit_zhurnal_progona.py")
        return

    if "page_otchyot" not in tek and tek:
        print("!! в otchyot.py не страница и не отчёт — не трогаю.")
        print("   Покажи мне его начало, разберусь.")
        return

    if not BAK.exists():
        print("!! бэкапа otchyot.py.bak_zhurnal нет — возвращать нечего")
        return
    bak = BAK.read_text(encoding="utf-8", errors="ignore")
    if "class Otchyot" not in bak:
        print("!! в бэкапе нет класса Otchyot — это не тот файл")
        return

    print("  сейчас в otchyot.py: страница (page_otchyot)")
    print("  в бэкапе: настоящий отчёт (class Otchyot)")
    print(f"  страница на своём месте: "
          f"{'да' if STRANICA.exists() else 'НЕТ — положи ui_otchyot.py'}")

    if SUHO:
        print()
        print("Сухой прогон: на диске ничего не изменилось.")
        return

    if OTCH.exists():
        shutil.copy2(OTCH, OTCH.with_suffix(".py.bylo_stranicey"))
    shutil.copy2(BAK, OTCH)
    print()
    print("Готово. Отчёт вернулся на место.")
    print("Прежний файл сохранён как otchyot.py.bylo_stranicey")
    print()
    print("ТЕПЕРЬ НАКАТИ: python postavit_zhurnal_progona.py")
    print("(в возвращённом файле ещё нет полей «действие» и цен)")
    print()


if __name__ == "__main__":
    main()
