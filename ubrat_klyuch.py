#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# UBRAT_KLYUCH_V1
"""
УБРАТЬ КЛЮЧ ИЗ РЕПОЗИТОРИЯ — чтобы GitHub перестал блокировать пуш.

Запускается двойным щелчком по `УБРАТЬ_КЛЮЧ.bat`, из корня репозитория.

ЧТО СЛУЧИЛОСЬ

    Файл `.env` с ключом попал в коммит. GitHub увидел ключ и не пускает
    отправку — и правильно делает. Кнопку «Bypass» жать нельзя: она
    опубликует ключ в открытый интернет, его подберут за минуты.

СНАЧАЛА — ПЕРЕВЫПУСТИ КЛЮЧ

    Ключ уже лежит в истории у тебя на диске, а история — вещь
    расползающаяся. Считай его засвеченным: зайди на OpenRouter, удали
    старый, выпусти новый. Это надёжнее любой чистки.

ЧТО ДЕЛАЕТ СКРИПТ

    1. Находит все `.env` и говорит, какие из них git видит.
    2. Заводит (или дополняет) `.gitignore`, чтобы `.env` больше никогда
       не попадал в коммиты.
    3. Убирает `.env` из git — файл на диске ОСТАЁТСЯ, пропадает только
       из-под учёта.
    4. Схлопывает неотправленные коммиты в один чистый. Ключа в нём уже
       нет, значит GitHub пропустит.

    Сам НИЧЕГО не отправляет и не удаляет с диска. Отправляешь ты, из
    GitHub Desktop, как обычно.

ЕСЛИ КЛЮЧ УЖЕ БЫЛ ОТПРАВЛЕН РАНЬШЕ

    Тогда чистки мало: он уже в интернете. Перевыпуск ключа —
    единственное, что помогает. Скрипт об этом предупредит.
"""
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

KOREN = Path(__file__).resolve().parent
ZAPRETIT = [".env", ".env.*", "*.key", "_ОТПРАВКА/", "_ПРИБЫТИЕ/",
            "__pycache__/", "*.pyc", "_ПЕРЕЕЗД/", "_УБОРКА/"]


def skazat(s=""):
    print(s, flush=True)


def cherta():
    skazat("=" * 62)


def git(*args, tiho=False):
    r = subprocess.run(["git", *args], cwd=str(KOREN),
                       capture_output=True, text=True)
    if not tiho and r.returncode != 0 and r.stderr.strip():
        skazat(f"    (git: {r.stderr.strip().splitlines()[0][:120]})")
    return r


def main() -> int:
    cherta()
    skazat("УБРАТЬ КЛЮЧ ИЗ РЕПОЗИТОРИЯ")
    cherta()

    if not (KOREN / ".git").exists():
        skazat("\nx здесь нет репозитория — положи меня в корень папки,")
        skazat("  которую показывает GitHub Desktop, и запусти оттуда")
        return 1
    if git("--version", tiho=True).returncode != 0:
        skazat("\nx не нашёл git. Он ставится вместе с GitHub Desktop —")
        skazat("  проверь, что Desktop установлен")
        return 1

    skazat("\n[1/4] ищу файлы с ключами")
    na_diske = [p for p in KOREN.rglob(".env") if ".git" not in p.parts]
    for p in na_diske:
        skazat(f"  на диске: {p.relative_to(KOREN)}")
    pod_uchyotom = [s.strip() for s in
                    git("ls-files").stdout.splitlines() if
                    Path(s).name.startswith(".env")]
    if pod_uchyotom:
        for s in pod_uchyotom:
            skazat(f"  git его ВИДИТ: {s}  ← из-за этого и блокировка")
    else:
        skazat("  git ни одного .env не видит — возможно, уже почищено")

    skazat("\n[2/4] запрещаю на будущее")
    gi = KOREN / ".gitignore"
    bylo = gi.read_text(encoding="utf-8") if gi.exists() else ""
    dobavit = [z for z in ZAPRETIT if z not in bylo.splitlines()]
    if dobavit:
        novoe = bylo.rstrip("\n")
        if novoe:
            novoe += "\n"
        novoe += "\n# UBRAT_KLYUCH_V1 — это в репозиторий не кладём\n"
        novoe += "\n".join(dobavit)
        gi.write_text(novoe + "\n", encoding="utf-8")
        skazat(f"  .gitignore дополнен: {', '.join(dobavit)}")
    else:
        skazat("  .gitignore уже всё запрещает")

    skazat("\n[3/4] убираю из-под учёта (файл на диске остаётся)")
    for s in pod_uchyotom:
        git("rm", "--cached", "--quiet", s)
        skazat(f"  снят с учёта: {s}")

    skazat("\n[4/4] схлопываю неотправленные коммиты в один чистый")
    est_origin = git("rev-parse", "--verify", "origin/main",
                     tiho=True).returncode == 0
    if not est_origin:
        est_origin = git("rev-parse", "--verify", "origin/master",
                         tiho=True).returncode == 0
        vetka = "origin/master" if est_origin else ""
    else:
        vetka = "origin/main"

    if est_origin:
        skolko = git("rev-list", "--count", f"{vetka}..HEAD").stdout.strip()
        skazat(f"  неотправленных коммитов: {skolko or '?'}")
        r = git("reset", "--soft", vetka)
        if r.returncode != 0:
            skazat("  x откатить не вышло — покажи это окно Брату")
            return 1
        skazat(f"  откатился к последнему отправленному ({vetka})")
        skazat("\n  ! ВАЖНО: если ключ попадал в УЖЕ отправленные коммиты,")
        skazat("    чистка не поможет — он в интернете. Перевыпусти ключ.")
    else:
        skazat("  на GitHub ещё ничего не отправлено — начинаю историю заново")
        git("update-ref", "-d", "HEAD")

    for s in pod_uchyotom:
        git("rm", "--cached", "--quiet", s, tiho=True)
    git("add", "-A")
    r = git("commit", "-m", "чистый коммит без ключей")
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        skazat("  x закоммитить не вышло — покажи это окно Брату")
        return 1
    skazat("  собран один чистый коммит")

    ostalos = [s for s in git("ls-files").stdout.splitlines()
               if Path(s).name.startswith(".env")]
    cherta()
    if ostalos:
        skazat("! git всё ещё видит: " + ", ".join(ostalos))
        skazat("  что-то пошло не так — покажи это окно Брату")
        return 1
    skazat("Готово. Ключа в коммитах нет, .env на диске цел.")
    skazat("")
    skazat("Теперь в GitHub Desktop жми Push origin — пройдёт.")
    skazat("И не забудь перевыпустить ключ на OpenRouter: старый")
    skazat("считаем засвеченным.")
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
