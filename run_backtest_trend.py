# run_backtest_trend.py — запускать из корня Island_of_Hope
# Самая простая гипотеза тренда из ТЗ: следующий блок продолжает
# направление предыдущего (автор заявляет 70-80%). Нужны H1 + M5.
#
# Запуск (из корня острова):
#   python run_backtest_trend.py EURUSDH1.csv EURUSDM5.csv
#   python run_backtest_trend.py EURUSDH1.csv EURUSDM5.csv 0.00001 2
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BIRZHA = _ROOT / "Биржа"
sys.path.insert(0, str(_BIRZHA))

from sniper_core import read_mt5_csv  # noqa: E402
from sniper_backtest import goliy_progon_trend_posledovatelnost, _svodka  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print("Использование: python run_backtest_trend.py <h1.csv> <m5.csv> [point] [спред_пипсов]")
        print("Пример:        python run_backtest_trend.py EURUSDH1.csv EURUSDM5.csv")
        sys.exit(0)

    h1_path = _ROOT / sys.argv[1]
    m5_path = _ROOT / sys.argv[2]
    point = float(sys.argv[3]) if len(sys.argv) > 3 else 0.00001
    spred = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0

    for p in (h1_path, m5_path):
        if not p.exists():
            print(f"Не нашёл файл: {p}")
            sys.exit(1)

    bars_h1 = read_mt5_csv(str(h1_path))
    bars_m5 = read_mt5_csv(str(m5_path))
    if not bars_h1 or not bars_m5:
        print("Не прочитал бары из CSV — проверь файлы.")
        sys.exit(1)

    rez = goliy_progon_trend_posledovatelnost(bars_h1, bars_m5, point=point, spred_pipsov=spred)

    print(f"\nТренд-последовательность · H1-блоков: {rez['h1_блоков']}")
    print(f"Входов после совпадения с направлением предыдущего блока: {rez['сделок_всего']}")
    print(f"(отсеяно по несовпадению: {rez['отсеяно_без_контекста']})")
    print(f"Спред учтён: {spred} пунктов на каждый вход\n")
    print(f"{'Выход':<15} {'Сделок':>7} {'Винрейт':>9} {'Сумма R':>10} "
          f"{'PF':>7} {'Сред. R':>9}")
    print("-" * 62)
    for imya, pnl_list in rez["по_вариантам"].items():
        s = _svodka(pnl_list)
        print(f"{imya:<15} {s['сделок']:>7} "
              f"{(str(s['винрейт'])+'%') if s['винрейт'] is not None else '—':>9} "
              f"{s['сумма_R']:>10} "
              f"{s['профит_фактор'] if s['профит_фактор'] is not None else '—':>7} "
              f"{s['средний_R'] if s['средний_R'] is not None else '—':>9}")

    print("\nЧестно: PF > 1 значит суммарно в плюсе, PF < 1 — в минусе.")
    print("Мало сделок (< ~30) — числу пока нельзя доверять, выборка мала.")


if __name__ == "__main__":
    main()
