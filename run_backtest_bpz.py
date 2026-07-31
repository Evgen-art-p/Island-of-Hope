# run_backtest_bpz.py — запускать из корня Island_of_Hope
# Голый прогон Блока Пустых Цен (первоисточник, не §8-гипотеза).
# Нужен только M5 — БПЦ ищется и торгуется на одном таймфрейме.
#
# Запуск (из корня острова):
#   python run_backtest_bpz.py EURUSDM5.csv
#   python run_backtest_bpz.py EURUSDM5.csv 0.00001 2
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BIRZHA = _ROOT / "Биржа"
sys.path.insert(0, str(_BIRZHA))

from sniper_core import read_mt5_csv  # noqa: E402
from sniper_backtest import goliy_progon_bpz, _svodka  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Использование: python run_backtest_bpz.py <m5.csv> [point] [спред_пипсов]")
        print("Пример:        python run_backtest_bpz.py EURUSDM5.csv")
        sys.exit(0)

    m5_path = _ROOT / sys.argv[1]
    point = float(sys.argv[2]) if len(sys.argv) > 2 else 0.00001
    spred = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

    if not m5_path.exists():
        print(f"Не нашёл файл: {m5_path}")
        sys.exit(1)

    bars_m5 = read_mt5_csv(str(m5_path))
    if not bars_m5:
        print("Не прочитал бары из CSV — проверь файл.")
        sys.exit(1)

    rez = goliy_progon_bpz(bars_m5, point=point, spred_pipsov=spred)
    s = _svodka(rez["pnl"])

    print(f"\nБлок Пустых Цен · найдено блоков: {rez['БПЦ_найдено']}")
    print(f"Из них дождались ретеста и дали вход: {rez['входов_после_ретеста']}")
    print(f"Спред учтён: {spred} пунктов, цель = 90% закрытия блока\n")
    print(f"{'Сделок':>7} {'Винрейт':>9} {'Сумма R':>10} {'PF':>7} {'Сред. R':>9}")
    print("-" * 46)
    print(f"{s['сделок']:>7} "
          f"{(str(s['винрейт'])+'%') if s['винрейт'] is not None else '—':>9} "
          f"{s['сумма_R']:>10} "
          f"{s['профит_фактор'] if s['профит_фактор'] is not None else '—':>7} "
          f"{s['средний_R'] if s['средний_R'] is not None else '—':>9}")

    print("\nЧестно: PF > 1 значит суммарно в плюсе, PF < 1 — в минусе.")
    print("Мало сделок (< ~30) — числу пока нельзя доверять, выборка мала.")

    # РАСПРЕДЕЛЕНИЕ — не только среднее. Если результат тащат несколько
    # редких огромных R — это не край, а пара удачных выбросов.
    pnl = sorted(rez["pnl"])
    if pnl:
        print("\nРаспределение сделок по R (отсортировано):")
        stroka = "  ".join(f"{p:+.2f}" for p in pnl)
        for i in range(0, len(stroka), 100):
            print("  " + stroka[i:i+100])
        top5 = sorted(rez["pnl"], reverse=True)[:5]
        vklad_top5 = sum(top5) / sum(rez["pnl"]) * 100 if sum(rez["pnl"]) else 0
        print(f"\nТоп-5 сделок дают {vklad_top5:.0f}% от суммарного R "
              f"({', '.join(f'{p:+.2f}' for p in top5)})")
        if vklad_top5 > 50:
            print("⚠ больше половины результата — из 5 сделок. Это выбросы, не край.")


if __name__ == "__main__":
    main()
