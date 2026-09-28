# -*- coding: utf-8 -*-
# OSTROV_PULS_V2 — остров говорит сам и по-настоящему
"""
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
"""
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
МАТЕРИК = "http://localhost:8080"
ID_ОСТРОВА = "island-of-hope"
ИМЯ_ОСТРОВА = "Остров_Надежды"
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
    """Что остров рассказывает о себе. Только счёт — без имён и без
    содержимого домов."""
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
    """Снять отчёт острова сканером (Брат/skaner_goroda.py) и взять из
    него главное: как читать, город одним взглядом, люди, приметы
    неладного, что изменилось. Нет сканера — пустая строка, пульс уйдёт
    без сводки."""
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
    """Шлёт ровно одну открытку и возвращает, что ответил материк."""
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
    """Стучится сам: «я жив» каждые ИНТЕРВАЛ_МИНУТ, сводка — раз в
    СВОДКА_КАЖДЫЕ_МИНУТ. В консоль пишет только перемены и сводки."""
    posl_svodka = None
    bylo_ok = None
    while True:
        try:
            nado = posl_svodka is None or \
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
    """Зовёт остров при старте (ostrov_main): пульс идёт сам, пока
    остров поднят."""
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
