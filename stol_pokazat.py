# -*- coding: utf-8 -*-
# STOL_POKAZAT_V1
"""
ПОКАЗАТЬ СТОЛ — без модели, без денег, без кириллицы в команде.

Терминал Windows режет кириллицу в аргументах, поэтому `python
Биржа/stol.py` не работает. Эта запускалка лежит в КОРНЕ и латиницей,
а путь к папке Биржа собирает уже внутри — Python с кириллицей в путях
работает спокойно.

    python stol_pokazat.py
    python stol_pokazat.py EURUSD H1
    python stol_pokazat.py XAUUSD D1 --polno     весь стол, как его видит мозг

Это самая дешёвая проверка из всех: если стол врёт, дальше идти
незачем — и мы это увидим, не потратив ни одного обращения к модели.
"""
import json
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent
BIRZHA = KOREN / "Биржа"


def main() -> int:
    if not BIRZHA.exists():
        print("✗ не вижу папку Биржа — запускай из КОРНЯ репо")
        return 1
    if not (BIRZHA / "stol.py").exists():
        print("✗ нет Биржа/stol.py — положи его туда")
        return 1

    sys.path.insert(0, str(BIRZHA))

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    polno = "--polno" in sys.argv
    symbol = args[0] if args else "EURUSD"
    tf = args[1] if len(args) > 1 else "H1"

    try:
        import stol
    except Exception as e:
        print(f"✗ stol.py не завёлся: {e}")
        return 1

    print(f"Стол {symbol} {tf}\n")
    try:
        s = stol.nakryt(symbol, tf)
    except Exception as e:
        print(f"✗ стол не собрался: {e}")
        return 1

    print(stol.slovami(s))

    if polno:
        print("\n" + "─" * 52)
        print("ПОЛНЫЙ СТОЛ (так его читает мозг):\n")
        print(json.dumps({k: v for k, v in s.items() if k != "self"},
                         ensure_ascii=False, indent=2))

    # честная подсказка, если стол пустой
    if s["iskra"]["compass"] is None and s["morj"]["morj_status"] == "SLEEPING":
        print("\n⚠ Стол почти пустой. Обычные причины:")
        print("   · кран стоит в tester, а данных в test_data нет")
        print("   · терминал закрыт или символ в нём с суффиксом")
        print("   · баров меньше 42 — считать нечем")
        print("   Проверить: python proverka_kotirovok.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
