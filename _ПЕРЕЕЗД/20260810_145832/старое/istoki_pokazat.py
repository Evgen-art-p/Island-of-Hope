# -*- coding: utf-8 -*-
# ISTOKI_POKAZAT_V1
"""
ПОКАЗАТЬ ИСТОКИ И ГНЁЗДА МАЯКА.

    python istoki_pokazat.py            что подключено и что горит
    python istoki_pokazat.py --votknut  воткнуть живые истоки в гнёзда

Лежит в корне и латиницей: терминал Windows режет кириллицу в
командах, а Python внутри с кириллическими путями работает спокойно.
"""
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent
BIRZHA = KOREN / "Биржа"
GOROD = KOREN / "ГОРОД"


def main() -> int:
    if not BIRZHA.exists():
        print("✗ не вижу папку Биржа — запускай из КОРНЯ репо")
        return 1
    sys.path.insert(0, str(BIRZHA))

    print("═" * 54)
    print("ИСТОКИ (папка Биржа/истоки)")
    print("═" * 54)
    try:
        import istoki
    except Exception as e:
        print(f"✗ istoki.py не завёлся: {e}")
        return 1

    spisok = istoki.spisok()
    if not spisok:
        print("  пусто — положи файлы в Биржа/истоки/")
    for i in spisok:
        zhiv = i["жив"]
        znak = "●" if zhiv else ("○" if zhiv is False else "?")
        sost = "на связи" if zhiv else ("молчит" if zhiv is False else "не спросишь")
        print(f"  {znak} {i['имя']:22} ключ {i['ключ']:8} {i['род']:12} {sost}")

    if "--votknut" in sys.argv:
        print("\nВтыкаю живые в гнёзда Маяка:")
        for i in spisok:
            if i["жив"] is False:
                print(f"  · {i['имя']} молчит — не втыкаю")
                continue
            m = istoki.votknut_v_mayak(i["ключ"], "поток котировок")
            print(f"  · {i['имя']}: {m or 'гнёзда недоступны'}")

    print("\n" + "═" * 54)
    print("ГНЁЗДА МАЯКА")
    print("═" * 54)
    if not GOROD.exists():
        print("  папки ГОРОД нет — гнёзд не посмотреть")
        return 0
    sys.path.insert(0, str(GOROD))
    try:
        import gnezda
    except Exception as e:
        print(f"  гнёзда не завелись: {e}")
        return 0

    for g in gnezda.spisok():
        if not g.get("занято"):
            print(f"  {g['номер']:2}  —")
            continue
        srok = "постоянно" if g.get("постоянно") else f"тихо {g.get('тихо_минут', 0)} мин"
        print(f"  {g['номер']:2}  {g.get('имя',''):22} {g.get('род',''):12} "
              f"{srok:14} {g.get('что','')}")

    sv = gnezda.svodka() if hasattr(gnezda, "svodka") else {}
    if sv:
        print(f"\n  свободных лучей: {sv.get('свободно', '?')} из {sv.get('всего', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
