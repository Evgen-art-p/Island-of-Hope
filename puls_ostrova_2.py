# -*- coding: utf-8 -*-
# puls_ostrova_2.py — ПАТЧ ОСТРОВА: пульс сам и со сводкой
# Маркер: PULS_OSTROVA_V2
"""
Слово Шефа (28.09): «делай шаг 2» — остров сигналит домой сам, с
настоящими числами и сводкой.

ЧТО ДЕЛАЕТ (только на ОСТРОВЕ — кладёшь в корень острова, где
ostrov_main.py, и запускаешь)
  1. ostrov_puls.py — новый: настоящие числа острова (жителей, прописано,
     на причале, посты, места, последний прогон) и раз в час — сводка:
     отчёт острова тем же сканером, что у материка.
     Адрес материка, id и имя острова берутся из старого файла — твои
     настройки не теряются.
  2. ostrov_main.py — остров при старте сам заводит пульс: раз в 5 минут
     «я жив», раз в час — со сводкой. Отдельное окно не нужно.

Нужно рядом:
  • Брат/skaner_goroda.py на острове (тот же файл, что у материка) —
    без него пульс уйдёт, но без сводки;
  • mayak_svodki.py накатан на ОБОИХ берегах — иначе сводку некому
    везти и некому принять (пульс всё равно дойдёт).

Повторный запуск ничего не ломает. Копии — .bak_puls2.
"""
import ast
import py_compile
import re
import shutil
from pathlib import Path

MARKER = "PULS_OSTROVA_V2"

NOVYY_PULS = """# -*- coding: utf-8 -*-
# OSTROV_PULS_V2 — остров говорит сам и по-настоящему
\"\"\"
Остров шлёт пульс на материк: «я жив» + настоящие числа о себе, а раз в
час — и СВОДКУ: свой отчёт тем же сканером, что у материка (общий язык
клетки). Причал материка кладёт сводку на полку острова, Хранитель
Маяка и Брат её читают.

СЛОВО ШЕФА (28.09): остров сигналит на наш Маяк, Хранитель докладывает
Брату — сводки с острова. Пока остров поднят (ОСТРОВ.bat), пульс идёт
сам, раз в ИНТЕРВАЛ_МИНУТ, без отдельного окна.

Что уходит на материк — только факты: числа и отчёт сканера. Дома
жителей закрыты (сканер их не открывает), ключи не читаются.

Руками тоже можно:
    python ostrov_puls.py            — один пульс со сводкой
    python ostrov_puls.py --вечно    — стучаться, пока не остановишь
Обрыв связи — не беда острова: он живёт дальше и пробует снова.
\"\"\"
import asyncio
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

KOREN = Path(__file__).resolve().parent
sys.path.insert(0, str(KOREN / "Маяк"))
from prichal import otpravit   # noqa: E402

# ═══════════════════════════════════════════════════
# НАСТРОЙКИ ОСТРОВА
# ═══════════════════════════════════════════════════
МАТЕРИК = "@@MATERIK@@"
ID_ОСТРОВА = "@@ID@@"
ИМЯ_ОСТРОВА = "@@IMYA@@"
ИНТЕРВАЛ_МИНУТ = 5            # как часто «я жив»
СВОДКА_КАЖДЫЕ_МИНУТ = 60      # как часто прикладывать сводку
# ═══════════════════════════════════════════════════

GC = KOREN / "GRONDHEIM_CITY"


def _json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def нынешние_числа() -> dict:
    \"\"\"Что остров рассказывает о себе. Только счёт — без имён и без
    содержимого домов.\"\"\"
    kov = GC / "жители" / "ковчег"
    doma = [d for d in kov.iterdir() if d.is_dir()] if kov.is_dir() else []
    propisano = sum(1 for d in doma
                    if (_json(d / "passport.json") or {}).get("прописка"))
    posty = sorted((GC / "посты").glob("*/пост.json")) if (GC / "посты").is_dir() else []
    zanyato = 0
    for f in posty:
        kto = (_json(f) or {}).get("кто_сидит")
        if isinstance(kto, dict) and kto.get("имя"):
            zanyato += 1
    lok = GC / "локации"
    mest = len([d for d in lok.iterdir() if d.is_dir()]) if lok.is_dir() else 0
    progony = GC / "Биржа" / "цеха" / "торговый_хаос" / "прогоны"
    imena = sorted(d.name for d in progony.iterdir() if d.is_dir()) if progony.is_dir() else []
    return {
        "жителей": len(doma),
        "прописано": propisano,
        "на_причале": len(doma) - propisano,
        "постов": len(posty),
        "занято_постов": zanyato,
        "мест": mest,
        "последний_прогон": imena[-1] if imena else "—",
    }


def свежая_сводка() -> str:
    \"\"\"Снять отчёт острова сканером (Брат/skaner_goroda.py) и взять из
    него главное: как читать, город одним взглядом, люди, приметы
    неладного, что изменилось. Нет сканера — пустая строка, пульс уйдёт
    без сводки.\"\"\"
    put = KOREN / "Брат" / "skaner_goroda.py"
    if not put.is_file():
        return ""
    spec = importlib.util.spec_from_file_location("skaner_goroda", str(put))
    sk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sk)
    sk.main()
    otchyot = KOREN / "Брат" / "отчёты" / "ГОРОД.md"
    tekst = otchyot.read_text(encoding="utf-8")
    kuski = re.split(r"(?m)^(?=## )", tekst)
    nuzhno = ("## Как читать", "## 1.", "## 2.", "## 7.", "## 8.")
    return kuski[0] + "".join(k for k in kuski[1:] if k.startswith(nuzhno))


async def один_пульс(со_сводкой: bool = True, tiho: bool = False) -> dict:
    \"\"\"Шлёт ровно одну открытку и возвращает, что ответил материк.\"\"\"
    svodka = ""
    if со_сводкой:
        try:
            svodka = await asyncio.to_thread(свежая_сводка)
        except Exception as e:
            print(f"[ПУЛЬС] сводка не снялась: {e} — шлю без неё")
    if not tiho:
        print(f"── стучусь в {МАТЕРИК} ..." + (" (со сводкой)" if svodka else ""))
    args = dict(kuda=МАТЕРИК, id=ID_ОСТРОВА, imya=ИМЯ_ОСТРОВА, rod="остров",
                chisla=нынешние_числа(), versia="v2")
    try:
        рез = await otpravit(**args, svodka=svodka)
    except TypeError:
        # причал на острове ещё старый — сводку он везти не умеет
        print("[ПУЛЬС] причал старый: накати mayak_svodki.py — пока без сводки")
        рез = await otpravit(**args)
    рез["_сводка"] = bool(svodka)
    if not tiho:
        if рез.get("ok"):
            print(f"✓ пульс принят, id={рез.get('id', '')}")
        else:
            print(f"✗ не принят: {рез.get('причина', '')}")
    return рез


async def вечно(tiho: bool = False):
    \"\"\"Стучится сам: «я жив» каждые ИНТЕРВАЛ_МИНУТ, сводка — раз в
    СВОДКА_КАЖДЫЕ_МИНУТ. В консоль пишет только перемены и сводки.\"\"\"
    posl_svodka = None
    bylo_ok = None
    while True:
        try:
            nado = posl_svodka is None or \\
                (time.monotonic() - posl_svodka) >= СВОДКА_КАЖДЫЕ_МИНУТ * 60
            рез = await один_пульс(со_сводкой=nado, tiho=True)
            ok = bool(рез.get("ok"))
            if ok and рез.get("_сводка"):
                posl_svodka = time.monotonic()
                print(f"[ПУЛЬС] ✓ материк на связи, сводка отправлена ({time.strftime('%H:%M')})")
            elif ok != bylo_ok:
                print(f"[ПУЛЬС] {'✓ материк на связи' if ok else '✗ ' + str(рез.get('причина', ''))}")
            bylo_ok = ok
        except Exception as e:
            print(f"[ПУЛЬС] сбой: {e}")
        await asyncio.sleep(ИНТЕРВАЛ_МИНУТ * 60)


_ZAPUSHCHEN = {"да": False}


async def zapustit_fonom():
    \"\"\"Зовёт остров при старте (ostrov_main): пульс идёт сам, пока
    остров поднят.\"\"\"
    if _ZAPUSHCHEN["да"]:
        return
    _ZAPUSHCHEN["да"] = True
    asyncio.create_task(вечно(tiho=True))


if __name__ == "__main__":
    if "--вечно" in sys.argv:
        print(f"остров будет стучаться каждые {ИНТЕРВАЛ_МИНУТ} мин. Ctrl+C — остановить.")
        asyncio.run(вечно())
    else:
        asyncio.run(один_пульс())
"""

YAKOR_MAIN = 'if __name__ in {"__main__", "__mp_main__"}:\n'
VSTAVKA_MAIN = """# PULS_OSTROVA_V2 — остров сигналит домой сам, пока поднят (слово Шефа
# 28.09): раз в 5 минут «я жив», раз в час — со сводкой. Сломается пульс —
# остров живёт дальше, связь для обмена, не для жизни.
try:
    from nicegui import app as _app_puls
    import ostrov_puls as _puls
    _app_puls.on_startup(_puls.zapustit_fonom)
except Exception as _e_puls:
    print(f"[ПУЛЬС] не завёлся: {_e_puls}")


"""


def naiti_koren():
    kandidaty = [Path(__file__).resolve().parent, Path.cwd()]
    for k in list(kandidaty):
        kandidaty.extend(list(k.parents)[:3])
    for k in kandidaty:
        if (k / "ostrov_main.py").is_file() and (k / "Маяк" / "prichal.py").is_file():
            return k
    return None


def _nastroyka(staryy: str, imya: str, po_umolch: str) -> str:
    m = re.search(rf'^{imya}\s*=\s*"([^"]*)"', staryy, re.M)
    return m.group(1) if m else po_umolch


def _zapisat(p: Path, novoe: str, staroe) -> bool:
    try:
        ast.parse(novoe)
    except SyntaxError as e:
        print(f"  ✗ {p.name}: не собирается ({e}) — не пишу")
        return False
    p.write_text(novoe, encoding="utf-8")
    try:
        py_compile.compile(str(p), doraise=True)
    except py_compile.PyCompileError as e:
        if staroe is None:
            p.unlink()
        else:
            p.write_text(staroe, encoding="utf-8")
        print(f"  ✗ {p.name}: не компилируется ({e}) — вернул как было")
        return False
    return True


def main():
    koren = naiti_koren()
    if koren is None:
        print("✗ Это не остров (нет ostrov_main.py и Маяк/prichal.py рядом).")
        print("  Патч только для острова: положи его в корень острова.")
        return
    print(f"Корень острова: {koren}\n")

    # 1. ostrov_puls.py
    p = koren / "ostrov_puls.py"
    staryy = p.read_text(encoding="utf-8") if p.is_file() else None
    if staryy and "OSTROV_PULS_V2" in staryy:
        print("• ostrov_puls.py — уже новый")
    else:
        st = staryy or ""
        tekst = (NOVYY_PULS
                 .replace("@@MATERIK@@", _nastroyka(st, "МАТЕРИК", "http://localhost:8080"))
                 .replace("@@ID@@", _nastroyka(st, "ID_ОСТРОВА", "island-of-hope"))
                 .replace("@@IMYA@@", _nastroyka(st, "ИМЯ_ОСТРОВА", "Остров_Надежды")))
        if staryy is not None:
            k = p.with_name(p.name + ".bak_puls2")
            if not k.exists():
                shutil.copy2(p, k)
        if _zapisat(p, tekst, staryy):
            print("✓ ostrov_puls.py — настоящие числа и сводка (настройки сохранены)")

    # 2. ostrov_main.py
    m = koren / "ostrov_main.py"
    tekst = m.read_text(encoding="utf-8")
    if MARKER in tekst:
        print("• ostrov_main.py — пульс уже заводится при старте")
    elif tekst.count(YAKOR_MAIN) != 1:
        print(f"✗ ostrov_main.py — место для пульса найдено {tekst.count(YAKOR_MAIN)} раз, "
              "нужно ровно 1. Не трогаю — пришли Брату.")
    else:
        k = m.with_name(m.name + ".bak_puls2")
        if not k.exists():
            shutil.copy2(m, k)
        novoe = tekst.replace(YAKOR_MAIN, VSTAVKA_MAIN + YAKOR_MAIN, 1)
        if _zapisat(m, novoe, tekst):
            print("✓ ostrov_main.py — остров сам заводит пульс при старте")

    print()
    if not (koren / "Брат" / "skaner_goroda.py").is_file():
        print("! Нет Брат/skaner_goroda.py на острове — положи туда сканер,")
        print("  иначе пульс уйдёт без сводки.")
    txt = (koren / "Маяк" / "prichal.py").read_text(encoding="utf-8")
    if "MAYAK_SVODKI_V1" not in txt:
        print("! Причал острова старый — накати mayak_svodki.py и здесь.")
    print("Перезапусти остров (ОСТРОВ.bat) — в его окне появится [ПУЛЬС] ✓.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            input("\nEnter — закрыть окно")
        except EOFError:
            pass
