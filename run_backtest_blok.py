# run_backtest_blok.py — запускать из корня Island-of-Hope
# Гипотеза вложенности блоков H1↔H4 из первоисточника: блок H1 у края
# блока H4 = разворотный, в середине = коррекционный (против тренда H4).
# Нужны ТРИ файла: H1 + H4 + M5.
#
# ЧЕСТНО (01.08): прошлый результат этой гипотезы (179 сделок, PF 0.98
# на GBPUSD) считался с трендом H4, взятым по последнему бару всей
# истории и розданным всем сделкам за все годы. Это был не тест.
# После патча patch_sniper_chestnost.py гипотеза проверяется впервые.
#
# Запуск (из корня острова):
#   python run_backtest_blok.py EURUSDH1.csv EURUSDH4.csv EURUSDM5.csv
#   python run_backtest_blok.py EURUSDH1.csv EURUSDH4.csv EURUSDM5.csv 0.00001 2
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BIRZHA = _ROOT / "Биржа"
sys.path.insert(0, str(_BIRZHA))

from sniper_core import read_mt5_csv  # noqa: E402
from sniper_backtest import goliy_progon_blok_h1_h4, _svodka  # noqa: E402


def main():
    if len(sys.argv) < 4:
        print("Использование: python run_backtest_blok.py <h1.csv> <h4.csv> <m5.csv> [point] [спред_пипсов]")
        print("Пример:        python run_backtest_blok.py EURUSDH1.csv EURUSDH4.csv EURUSDM5.csv")
        print("\nH4 нужен обязательно — вся гипотеза про то, ГДЕ блок H1")
        print("стоит внутри блока H4. Выгрузи H4 из MT5 тем же экспортом.")
        sys.exit(0)

    h1_path = _ROOT / sys.argv[1]
    h4_path = _ROOT / sys.argv[2]
    m5_path = _ROOT / sys.argv[3]
    point = float(sys.argv[4]) if len(sys.argv) > 4 else 0.00001
    spred = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0

    for p in (h1_path, h4_path, m5_path):
        if not p.exists():
            print(f"Не нашёл файл: {p}")
            sys.exit(1)

    bars_h1 = read_mt5_csv(str(h1_path))
    bars_h4 = read_mt5_csv(str(h4_path))
    bars_m5 = read_mt5_csv(str(m5_path))
    if not bars_h1 or not bars_h4 or not bars_m5:
        print("Не прочитал бары из CSV — проверь файлы.")
        sys.exit(1)

    rez = goliy_progon_blok_h1_h4(bars_h1, bars_h4, bars_m5,
                                  point=point, spred_pipsov=spred)

    print(f"\nВложенность H1↔H4 · блоков H1: {rez['h1_блоков']} · "
          f"блоков H4: {rez['h4_блоков']}")
    print(f"Классифицировано событий (разворотный/коррекционный): "
          f"{rez['классифицировано_событий']}")
    print(f"Входов после совпадения направления: {rez['сделок_всего']}")
    print(f"(отсеяно по несовпадению: {rez['отсеяно_без_контекста']})")
    print(f"Спред учтён: {spred} пунктов, на входе И на выходе\n")
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
    print("И даже при большой выборке сделки идут внахлёст — независимых")
    print("наблюдений заметно меньше, чем строк в этой таблице.")


if __name__ == "__main__":
    main()
