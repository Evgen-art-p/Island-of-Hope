#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VAKANSII_OSTROVA_V1
"""
ВАКАНСИИ ОСТРОВА — убрать места упразднённых сенсоров.

    python popravit_vakansii.py            посмотреть
    python popravit_vakansii.py --sdelat   поправить

Запускать из КОРНЯ ОСТРОВА.

ЧТО НЕ ТАК

    В цехе торгового хаоса на острове объявлено семь мест: A01 компас,
    A02 пасть и резинка, A03 фаза толпы, A04 фрактал — и три трейдера.

    Первые четыре — сенсоры. На материке их упразднили шестого августа:
    их работу теперь делает стол, который накрывается сам, без голов и
    без денег. Здесь они остались от июльского слепка. Пока они стоят в
    манифесте, город считает их вакансиями: показывает в кабинете,
    ждёт носителей, зовёт их мозги.

ЧТО ДЕЛАЕТ

    Вычёркивает эти четыре места из манифеста цеха и уносит их папки в
    `_УБРАННЫЕ_ВАКАНСИИ/`. Не удаляет — уносит: захочешь вернуть,
    вернёшь.

    Остаётся ровно то, что на материке: A06 трейдер-пробой, A07
    трейдер-ранний, A08 трейдер-откат. Контору не трогает — там
    архивариус и исполнитель, они на месте и на материке те же.

    Перед тем как убрать, сверяет роль в манифесте с ожидаемой. Роль не
    совпала — значит место переиначили, и скрипт его НЕ ТРОГАЕТ, а
    говорит об этом.
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

KOREN = Path(__file__).resolve().parent
CEH = KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха" / "торговый_хаос"
MANIFEST = CEH / "manifest.json"
CHULAN = KOREN / "_УБРАННЫЕ_ВАКАНСИИ"

# упразднённые сенсоры: слот → роль, какой она должна быть в манифесте
SENSORY = {
    "A01": "компас",
    "A02": "пасть и резинка",
    "A03": "фаза толпы",
    "A04": "фрактал",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdelat", action="store_true")
    a = ap.parse_args()

    print("=" * 60)
    print("ВАКАНСИИ ОСТРОВА" + ("" if a.sdelat else "   [СУХОЙ ПРОГОН]"))
    print("=" * 60)

    if not MANIFEST.exists():
        print(f"x не вижу {MANIFEST.relative_to(KOREN)}")
        print("  запускай из корня ОСТРОВА")
        return 1

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sloty = m.get("слоты", [])
    print("\nсейчас в цехе:")
    for s in sloty:
        print(f"   {s.get('слот'):<6} {s.get('роль','')}")

    ubrat, ostavit, spor = [], [], []
    for s in sloty:
        imya = s.get("слот")
        if imya not in SENSORY:
            ostavit.append(s)
            continue
        rol = (s.get("роль") or "").strip()
        if rol != SENSORY[imya]:
            spor.append((imya, rol))
            ostavit.append(s)
            continue
        ubrat.append(s)

    if spor:
        print("\n! не трогаю — роль не та, что я ждал:")
        for imya, rol in spor:
            print(f"   {imya}: в манифесте «{rol}», "
                  f"ждал «{SENSORY[imya]}»")

    if not ubrat:
        print("\nУбирать нечего — вакансии уже в порядке.")
        return 0

    print(f"\nубираю {len(ubrat)}:")
    for s in ubrat:
        d = CEH / "слоты" / s["слот"]
        est = "папка есть" if d.exists() else "папки нет"
        print(f"   {s['слот']:<6} {s.get('роль','')}   ({est})")

    print(f"\nостаётся {len(ostavit)}:")
    for s in ostavit:
        print(f"   {s.get('слот'):<6} {s.get('роль','')}")

    if not a.sdelat:
        print("\n" + "-" * 60)
        print("Это был показ. Поправить: python popravit_vakansii.py --sdelat")
        return 0

    kuda = CHULAN / datetime.now().strftime("%Y%m%d_%H%M%S")
    kuda.mkdir(parents=True, exist_ok=True)

    shutil.copy2(MANIFEST, kuda / "manifest.json.было")
    m["слоты"] = ostavit
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    unesli = []
    for s in ubrat:
        d = CEH / "слоты" / s["слот"]
        if d.exists():
            shutil.move(str(d), str(kuda / s["слот"]))
            unesli.append(s["слот"])

    (kuda / "ЧТО_ЭТО.txt").write_text(
        "Места упразднённых сенсоров, убранные из цеха торгового хаоса.\n"
        "На материке их не стало 06.08 — работу делает стол, без голов.\n\n"
        "Здесь лежат их папки и прежний manifest.json (как «было»).\n"
        "Вернуть: скопировать папки обратно в\n"
        "GRONDHEIM_CITY/Биржа/цеха/торговый_хаос/слоты/\n"
        "и восстановить манифест из manifest.json.было\n",
        encoding="utf-8")

    print("\n" + "-" * 60)
    print(f"+ манифест поправлен, унесено папок: {len(unesli)}")
    print(f"  всё лежит в {kuda.relative_to(KOREN)} — не удалено")
    print("\nПроверь: python rabota_pult.py — в списке должны остаться")
    print("три трейдерских места и контора.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
