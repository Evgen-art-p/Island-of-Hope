#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# OSTROV_ODNA_KNOPKA_V1
"""
ОСТРОВ · одна кнопка

Запускается двойным щелчком по `ОСТРОВ.bat`. Больше ничего делать не
надо: ни команд, ни путей, ни порядка запусков.

ПЕРВЫЙ РАЗ он сам:
    · проверит библиотеки и доставит, чего не хватает;
    · перевезёт Биржу с материка (материк найдёт сам, спросит — тот ли);
    · поставит главную страницу;
    · заведёт папку `фон/` под картинку;
    · поднимет остров и откроет браузер.

ДАЛЬШЕ он просто поднимает остров и открывает браузер.

Закрыть остров — закрыть чёрное окно или нажать в нём Ctrl+C.
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

KOREN = Path(__file__).resolve().parent
PORT = 8080

BIBLIOTEKI = [
    ("nicegui", "nicegui"),
    ("matplotlib", "matplotlib"),
    ("httpx", "httpx"),
    ("dotenv", "python-dotenv"),
    ("requests", "requests"),
]
# MetaTrader5 ставится только на Windows — на другом он и не нужен
if sys.platform == "win32":
    BIBLIOTEKI.append(("MetaTrader5", "MetaTrader5"))


def skazat(s=""):
    print(s, flush=True)


def cherta():
    skazat("=" * 60)


def est(imya: str) -> bool:
    try:
        __import__(imya)
        return True
    except Exception:
        return False


def postavit_biblioteki() -> bool:
    nado = [paket for modul, paket in BIBLIOTEKI if not est(modul)]
    if not nado:
        skazat("  библиотеки на месте")
        return True
    skazat(f"  не хватает: {', '.join(nado)}")
    skazat("  ставлю (это может занять пару минут)...")
    for paket in nado:
        r = subprocess.run([sys.executable, "-m", "pip", "install", paket],
                           capture_output=True, text=True)
        if r.returncode == 0:
            skazat(f"    + {paket}")
        else:
            skazat(f"    x {paket} — не встал")
            hvost = (r.stderr or "").strip().splitlines()[-1:] or [""]
            skazat(f"      {hvost[0][:140]}")
            if paket == "MetaTrader5":
                skazat("      (без него остров поднимется, но торговать "
                       "будет нечем)")
            else:
                return False
    return True


def zapustit(skript: str, *klyuchi) -> bool:
    """Зовём соседний скрипт и показываем, что он говорит."""
    put = KOREN / skript
    if not put.exists():
        skazat(f"  x рядом нет {skript}")
        return False
    r = subprocess.run([sys.executable, str(put), *klyuchi], cwd=str(KOREN))
    return r.returncode == 0


def prikryt_env():
    """Ключи в репозиторий не пускаем.

    GitHub блокирует пуш, если в нём находит файл с ключами — и это не
    вредность, а защита: ключ, попавший в репо, считай украден. Значит
    `.env` должен лежать на машине и НЕ попадать в git.
    """
    gitignore = KOREN / ".gitignore"
    est = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    nado = [s for s in (".env", "__pycache__/", "*.pyc", "_ПЕРЕЕЗД/",
                        "_УБОРКА/", "фон/") if s not in est]
    if nado:
        hvost = ("" if est.endswith("\n") or not est else "\n")
        gitignore.write_text(
            est + hvost + "\n# закрыто островом: ключи и рабочий сор\n"
            + "\n".join(nado) + "\n", encoding="utf-8")
        skazat(f"  прикрыл от git: {', '.join(nado)}")

    # если .env уже попал в git, одним .gitignore не отделаться —
    # надо вынуть его из индекса, файл при этом остаётся на месте
    if (KOREN / ".git").is_dir() and (KOREN / ".env").exists():
        r = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"],
                           cwd=str(KOREN), capture_output=True, text=True)
        if r.returncode == 0:
            subprocess.run(["git", "rm", "--cached", ".env"],
                           cwd=str(KOREN), capture_output=True, text=True)
            skazat("  вынул .env из git (сам файл на месте)")
            skazat("  теперь пуш пройдёт — но старый коммит с ключом")
            skazat("  всё ещё в истории: ключ лучше сменить")


def main() -> int:
    cherta()
    skazat("ОСТРОВ НАДЕЖДЫ")
    cherta()

    skazat("\n[1/4] библиотеки")
    if not postavit_biblioteki():
        skazat("\nНе смог поставить библиотеки. Покажи это окно Брату.")
        return 1

    skazat("\n[2/4] переезд")
    if (KOREN / "ostrov_main.py").exists():
        skazat("  остров уже обжит — переезд пропускаю")
    else:
        skazat("  первый раз: везу Биржу с материка")
        if not zapustit("pereselenie.py", "--sdelat"):
            skazat("\nПереезд не прошёл. Что написано выше — то и мешает.")
            return 1

    skazat("\n[3/4] главная страница")
    # ставим ВСЕГДА, а не только в первый раз: так поправленная главная
    # доезжает до тебя сама, без отдельных команд
    if not zapustit("postavit_glavnuyu.py", "--sdelat"):
        skazat("  главная не встала — остров поднимется без неё")
    if (KOREN / "postavit_zastroyshchika.py").exists():
        if not zapustit("postavit_zastroyshchika.py", "--sdelat"):
            skazat("  застройщик не встал — остальное работает")
    if (KOREN / "postavit_perevozku.py").exists():
        if not zapustit("postavit_perevozku.py", "--sdelat"):
            skazat("  перевозка не встала — остальное работает")

    fon = KOREN / "фон"
    if fon.is_dir():
        kartinki = [p for p in fon.iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
        if not kartinki:
            skazat(f"  подсказка: кинь картинку в папку {fon.name} — "
                   f"будет фон")

    if not (KOREN / ".env").exists():
        skazat("\n  ! нет файла .env с ключом модели.")
        skazat("    Остров поднимется, но говорить трейдеры не смогут.")
        skazat("    Скопируй .env с материка сюда, в эту же папку.")

    prikryt_env()

    skazat("\n[4/4] поднимаю остров")
    skazat(f"  адрес: http://localhost:{PORT}")
    skazat("  браузер откроется сам через несколько секунд")
    skazat("  закрыть остров — закрой это окно или нажми Ctrl+C")
    cherta()

    import threading

    def otkryt():
        time.sleep(4)
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except Exception:
            pass

    threading.Thread(target=otkryt, daemon=True).start()

    try:
        subprocess.run([sys.executable, str(KOREN / "ostrov_main.py")],
                       cwd=str(KOREN))
    except KeyboardInterrupt:
        skazat("\nостров остановлен")
    return 0


if __name__ == "__main__":
    try:
        kod = main()
    except Exception as e:
        skazat(f"\nx что-то пошло не так: {type(e).__name__}: {e}")
        kod = 1
    if sys.platform == "win32":
        try:
            input("\nEnter — закрыть окно.")
        except Exception:
            pass
    sys.exit(kod)
