# -*- coding: utf-8 -*-
# STANDART_RABOTY_V1
"""
ПУЛЬТ РАБОТЫ — запасной ход к тем же четырём рукам.

    python rabota_pult.py                       все места города
    python rabota_pult.py --svobodnye           только свободные
    python rabota_pult.py --iskat трейдер       поиск по названию
    python rabota_pult.py --zavesti ID --ceh X --slot A06 --nazvanie "..."
    python rabota_pult.py --prinyat ID Имя
    python rabota_pult.py --uvolit ID --pochemu "..."
    python rabota_pult.py --snesti ID
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ГОРОД"))
import rabota as R   # noqa: E402


def pokazat(a):
    v = R.mesta()
    if a.iskat:
        q = a.iskat.lower()
        v = [m for m in v if q in (m["название"] + m["цех"] + m["слот"]).lower()]
    if a.svobodnye:
        v = [m for m in v if not m["кто_сидит"]]
    s = R.schet()
    print("═" * 66)
    print(f"МЕСТА ГОРОДА · всего {s['всего']} · с должностью "
          f"{s['с должностью']} · занято {s['занято']} · "
          f"свободно {s['свободно']} · без должности {s['без должности']}")
    print("═" * 66)
    kvartal = None
    for m in sorted(v, key=lambda x: (x["квартал"], x["цех"], x["слот"])):
        if m["квартал"] != kvartal:
            kvartal = m["квартал"]
            print(f"\n  {kvartal or '(без квартала)'}")
        kto = m["кто_сидит"] or ("— свободно" if m["есть_пост"]
                                 else "— должности нет")
        print(f"    {m['цех']:<16} {m['слот']:<6} {m['название']:<26} {kto}")
        print(f"      id: {m['id']}")
    print("\n" + "─" * 66)
    print("принять:  python rabota_pult.py --prinyat <id> Имя")
    print("уволить:  python rabota_pult.py --uvolit <id>")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iskat", default="")
    ap.add_argument("--svobodnye", action="store_true")
    ap.add_argument("--zavesti", metavar="ID")
    ap.add_argument("--ceh", default="")
    ap.add_argument("--slot", default="")
    ap.add_argument("--kvartal", default="")
    ap.add_argument("--nazvanie", default="")
    ap.add_argument("--prinyat", nargs=2, metavar=("ID", "ИМЯ"))
    ap.add_argument("--uvolit", metavar="ID")
    ap.add_argument("--snesti", metavar="ID")
    ap.add_argument("--pochemu", default="")
    a = ap.parse_args()

    if a.zavesti:
        ok, msg = R.zavesti(a.zavesti, {
            "название": a.nazvanie, "квартал": a.kvartal,
            "цех": a.ceh, "слот": a.slot})
        print(("✓ " if ok else "✗ ") + msg + "\n")
    if a.prinyat:
        ok, msg = R.prinyat(a.prinyat[0], a.prinyat[1], pochemu=a.pochemu)
        print(("✓ " if ok else "✗ ") + msg + "\n")
    if a.uvolit:
        ok, msg = R.uvolit(a.uvolit, pochemu=a.pochemu)
        print(("✓ " if ok else "✗ ") + msg + "\n")
    if a.snesti:
        ok, msg = R.snesti(a.snesti)
        print(("✓ " if ok else "✗ ") + msg + "\n")

    pokazat(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
