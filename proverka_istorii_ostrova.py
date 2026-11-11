# -*- coding: utf-8 -*-
"""
ПРОВЕРКА ИСТОРИИ ОСТРОВА (11.11) — читает котировки ТЕМ ЖЕ способом, что сам
город (feed_source._find_csv + williams_core.read_mt5_csv), и говорит, по
каждой паре и этажу: какой файл, сколько баров, с какой даты и до какой.

Зачем: проверка в pereselenie_3.py искала файлы по своим приметам и не узнала
дневки, недели и месяцы (у MT5 они называются Daily / Weekly / Monthly), а
даты не прочитала. Город читает иначе — значит, и проверять надо его руками.

Класть в КОРЕНЬ ОСТРОВА (рядом с ostrov_main.py), запускать как обычно.
Ничего не меняет.
"""
import sys
from pathlib import Path

OSTROV = Path(__file__).resolve().parent
PARY = ("GBPUSD", "EURUSD", "AUDUSD")
ETAZHI = ("H1", "H4", "D1", "W1", "MN1")


def main():
    for p in (OSTROV / "Биржа", OSTROV):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import feed_source as fs
    from williams_core import read_mt5_csv
    print("История котировок на острове — глазами города\n")
    vse_ok = True
    for sym in PARY:
        for et in ETAZHI:
            try:
                p = fs._find_csv(sym, et)
            except Exception as e:
                p, oshibka = None, e
            if p is None:
                print(f"  ✗ {sym} {et:<4} — город файла не находит")
                vse_ok = False
                continue
            try:
                bars = read_mt5_csv(str(p)) or []
            except Exception as e:
                print(f"  ✗ {sym} {et:<4} {Path(p).name} — не читается: {e}")
                vse_ok = False
                continue
            if not bars:
                print(f"  ✗ {sym} {et:<4} {Path(p).name} — пустой")
                vse_ok = False
                continue
            ot, do = bars[0].get("date", "?"), bars[-1].get("date", "?")
            znak = "✓" if str(do) >= "2025.12" else "·"
            if znak != "✓":
                vse_ok = False
            print(f"  {znak} {sym} {et:<4} {Path(p).name:<24} {len(bars):>7} баров  {ot} … {do}")
    print("\n✓ — история доходит до декабря 2025 года, · — кончается раньше")
    print("Всё на месте — можно гнать 2020–2025." if vse_ok else
          "Чего-то не хватает — скинь окно Брату.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nx что-то пошло не так: {type(e).__name__}: {e}")
    finally:
        try:
            input("\nEnter — закрыть окно")
        except Exception:
            pass
