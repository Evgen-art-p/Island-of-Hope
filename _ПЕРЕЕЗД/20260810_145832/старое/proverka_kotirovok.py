# -*- coding: utf-8 -*-
# PROVERKA_KOTIROVOK_V1
"""
ЧТО НА САМОМ ДЕЛЕ ПРИХОДИТ В БИРЖУ.

ЗАЧЕМ. «Котировки некорректные» — слишком много причин, чтобы гадать:
включён не тот кран, символ в терминале с суффиксом, этаж не найден,
кэш держит старый файл, время сдвинуто относительно терминала. Эта
проверялка печатает ровно то, что отдаёт `feed_source.bars()`, — и
дальше сравниваешь с терминалом глазами.

ЗАПУСК из корня репо (кириллицы в команде нет — терминал её режет):
    python proverka_kotirovok.py
    python proverka_kotirovok.py --symbol EURUSD --tf H1
    python proverka_kotirovok.py --vse       # пройтись по всей лесенке
"""
import argparse
import sys
from pathlib import Path

LESENKA = ["MN1", "W1", "D1", "H12", "H8", "H4", "H1", "M30", "M15", "M10", "M5"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="")
    ap.add_argument("--tf", default="H1")
    ap.add_argument("--vse", action="store_true", help="все этажи лесенки")
    ap.add_argument("--barov", type=int, default=5, help="сколько последних показать")
    a = ap.parse_args()

    b = Path("Биржа")
    if not b.exists():
        print("✗ нет папки Биржа — запускай из КОРНЯ репо")
        return 1
    sys.path.insert(0, str(b))

    from feed_source import get_feed_mode, bars as source_bars

    rezhim = get_feed_mode()
    symbol = a.symbol or rezhim.get("symbol") or "EURUSD"

    print("① КАКОЙ КРАН ВКЛЮЧЁН")
    print(f"   режим: {rezhim.get('mode')}   "
          f"({'терминал MT5' if rezhim.get('mode') == 'real' else 'папка test_data'})")
    print(f"   символ на площади: {rezhim.get('symbol')}")
    print(f"   проверяем: {symbol}")

    if rezhim.get("mode") == "real":
        print("\n② ЧТО ВИДИТ ТЕРМИНАЛ")
        try:
            from mt5_feed import _terminal
            mt5 = _terminal()
            if mt5 is None:
                print("   ✗ терминал не поднялся — MetaTrader5 не установлен "
                      "или терминал закрыт")
            else:
                if not mt5.initialize():
                    print("   ✗ initialize=False — терминал закрыт или занят")
                else:
                    info = mt5.symbol_info(symbol)
                    if info is None:
                        print(f"   ✗ символа «{symbol}» в терминале НЕТ.")
                        print("     Частая причина: у брокера он с суффиксом.")
                        vse = mt5.symbols_get()
                        pohozhie = [s.name for s in (vse or [])
                                    if symbol[:6].upper() in s.name.upper()][:12]
                        if pohozhie:
                            print(f"     Похожие в терминале: {pohozhie}")
                    else:
                        print(f"   символ найден: {info.name}")
                        print(f"   point={info.point}  digits={info.digits}  "
                              f"виден в обзоре={info.visible}")
                        t = mt5.symbol_info_tick(symbol)
                        if t:
                            print(f"   тик сейчас: bid={t.bid}  ask={t.ask}")
                    mt5.shutdown()
        except Exception as e:
            print(f"   ✗ {e}")
    else:
        print("\n② ЧТО ЛЕЖИТ В ПАПКЕ test_data")
        td = b / "test_data"
        if not td.exists():
            print(f"   ✗ нет {td}")
        else:
            for f in sorted(td.glob("*.csv")):
                print(f"   · {f.name}  {f.stat().st_size // 1024} КБ")

    etazhi = LESENKA if a.vse else [a.tf.upper()]
    print("\n③ ЧТО ОТДАЁТ ИСТОЧНИК")
    for tf in etazhi:
        bs, point = source_bars(symbol, tf, count=200)
        if not bs:
            print(f"   {tf:4} — ПУСТО (баров нет)")
            continue
        p = bs[-1]
        print(f"   {tf:4} — баров {len(bs):4}  point={point}")
        print(f"          первый: {bs[0]['date']}  close={bs[0]['close']}")
        print(f"          последний: {p['date']}  "
              f"O={p['open']} H={p['high']} L={p['low']} C={p['close']} "
              f"V={p.get('volume')}")
        if not a.vse:
            print(f"\n   Последние {a.barov} баров — сверь с терминалом:")
            for x in bs[-a.barov:]:
                print(f"     {x['date']}  O={x['open']} H={x['high']} "
                      f"L={x['low']} C={x['close']} V={x.get('volume')}")

    print("\n④ НА ЧТО СМОТРЕТЬ")
    print("   · цены не те        → скорее всего кран стоит в tester,")
    print("                         а ты ждёшь реал (или наоборот)")
    print("   · время сдвинуто    → терминал показывает время СЕРВЕРА брокера;")
    print("                         сверь час последнего бара с терминалом")
    print("   · символ не найден  → у брокера суффикс, см. «Похожие» выше")
    print("   · баров мало/пусто  → инструмент не открыт в обзоре рынка")
    print("   · данные старые     → в tester это нормально: файл статичен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
