# run_sniper.py — запускать из корня Island_of_Hope
# Обёртка над Биржа/sniper_core.py. Не надо заходить в папку Биржа
# руками — эта обёртка сама находит её, как main.py делает в городе.
#
# Запуск (из корня острова):
#   python run_sniper.py EURUSDH1.csv EURUSDM5.csv
#   python run_sniper.py EURUSDH1.csv EURUSDM5.csv 0.01   (для золота)
#
# CSV клади прямо в корень острова, рядом с этим файлом.
#
# Результат — не текст, а ДВЕ КАРТИНКИ рядом с этим файлом:
#   sniper_h1.png  — свечи H1 + отметки ТИУ и ЗК
#   sniper_m5.png  — свечи M5 + отметки ИУ и УРСТ
# Открой их и сверь глазами с тем же участком графика в MT5.
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BIRZHA = _ROOT / "Биржа"
sys.path.insert(0, str(_BIRZHA))

from sniper_core import read_mt5_csv, build_sniper_map, compute_atr  # noqa: E402

# сколько последних баров рисовать на картинке — иначе тысячи баров
# сольются в кашу, а последние уровни — самые свежие и интересные
POKAZAT_BAROV_H1 = 200
POKAZAT_BAROV_M5 = 300


def _narisovat_svechi(ax, bars, indeksy=None):
    """Простые свечи без внешних библиотек — только matplotlib."""
    idxs = indeksy if indeksy is not None else range(len(bars))
    for x, i in enumerate(idxs):
        b = bars[i]
        cvet = "#2e7d32" if b["close"] >= b["open"] else "#c62828"
        ax.plot([x, x], [b["low"], b["high"]], color=cvet, linewidth=0.8)
        lo, hi = sorted([b["open"], b["close"]])
        ax.add_patch(__import__("matplotlib").patches.Rectangle(
            (x - 0.3, lo), 0.6, max(hi - lo, 1e-9), color=cvet))


def _narisovat_h1(bars_h1, tiu, zk, put_kartinki):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(bars_h1)
    okno = min(POKAZAT_BAROV_H1, n)
    off = n - okno
    vidimye = bars_h1[off:]
    idxs = list(range(off, n))

    # показываем только уровни РЯДОМ С ТЕКУЩЕЙ ЦЕНОЙ — раньше сортировал
    # по числу касаний за всю историю, и старые уровни из другого края
    # многолетних данных выигрывали просто потому что дольше жили,
    # хотя к сегодняшнему графику отношения не имеют
    tekushchaya_tsena = bars_h1[-1]["close"]
    atr_h1 = compute_atr(bars_h1)
    poslednii_atr = next((a for a in reversed(atr_h1) if a is not None), None)
    okno_relevantnosti = (poslednii_atr or 0.001) * 40  # ~40 ATR вокруг цены

    tiu_ryadom = [u for u in tiu
                 if abs(u["цена_центр"] - tekushchaya_tsena) <= okno_relevantnosti]
    tiu_pokazat = sorted(tiu_ryadom, key=lambda u: u["касаний"], reverse=True)[:10]

    fig, ax = plt.subplots(figsize=(16, 8))
    _narisovat_svechi(ax, bars_h1, idxs)

    for u in tiu_pokazat:
        cvet = "#1565c0" if not u["пробит"] else "#8e24aa"
        ax.axhspan(u["зона_лоу"], u["зона_хай"], color=cvet, alpha=0.25)
        ax.text(len(idxs) - 1, u["цена_центр"],
                f" ТИУ {'(пробит)' if u['пробит'] else ''} {u['касаний']}× ",
                color=cvet, fontsize=8, va="center")

    for z in zk:
        try:
            first_i = next(i for i in idxs if bars_h1[i]["date"].startswith(z["дата"]))
        except StopIteration:
            continue
        cvet = "#ef6c00" if z["валиден"] else "#9e9e9e"
        ax.axhspan(z["флэт_лоу"], z["флэт_хай"],
                  xmin=(first_i - off) / okno, xmax=min((first_i - off + 8) / okno, 1.0),
                  color=cvet, alpha=0.25)

    ax.set_title(f"H1 · последние {okno} баров · показаны {len(tiu_pokazat)} "
                f"ближайших к цене ТИУ из {len(tiu)} найденных всего · оранжевое=ЗК")
    ax.set_xticks(range(0, okno, max(1, okno // 15)))
    ax.set_xticklabels([vidimye[i]["date"] for i in range(0, okno, max(1, okno // 15))],
                       rotation=45, ha="right", fontsize=7)
    fig.tight_layout()
    fig.savefig(put_kartinki, dpi=130)
    plt.close(fig)


def _narisovat_m5(bars_m5, iu, urst, put_kartinki):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(bars_m5)
    okno = min(POKAZAT_BAROV_M5, n)
    off = n - okno
    vidimye = bars_m5[off:]
    idxs = list(range(off, n))

    fig, ax = plt.subplots(figsize=(18, 8))
    _narisovat_svechi(ax, bars_m5, idxs)

    for u in iu:
        bi = u["импульсный_бар_индекс"]
        if bi < off:
            continue
        x = bi - off
        cvet = "#2e7d32" if u["закреплён"] else "#f9a825"
        ax.axhline(u["уровень"], color=cvet, linewidth=1.0, linestyle=":")
        ax.plot(x, u["уровень"], marker="s", color=cvet, markersize=6)
        ax.text(x, u["уровень"], f" ИУ{'✓' if u['закреплён'] else '?'}",
                color=cvet, fontsize=7)

    for r in urst:
        bi = r["бар_индекс"]
        if bi < off:
            continue
        if not r["v_подтверждён"]:
            continue  # неподтверждённых слишком много — только шум на картинке
        x = bi - off
        ax.plot(x, r["цена"], marker="D", color="#6a1b9a", markersize=7)
        ax.text(x, r["цена"], " УРСТ", color="#6a1b9a", fontsize=7)

    ax.set_title(f"M5 · последние {okno} баров · квадрат=ИУ (зелёный=закреплён) · "
                f"ромб=УРСТ (только подтверждённые, {sum(1 for r in urst if r['v_подтверждён'])} "
                f"из {len(urst)} найденных)")
    ax.set_xticks(range(0, okno, max(1, okno // 15)))
    ax.set_xticklabels([vidimye[i]["date"] for i in range(0, okno, max(1, okno // 15))],
                       rotation=45, ha="right", fontsize=7)
    fig.tight_layout()
    fig.savefig(put_kartinki, dpi=130)
    plt.close(fig)


def main():
    if len(sys.argv) < 3:
        print("Использование: python run_sniper.py <h1.csv> <m5.csv> [point]")
        print("Пример:        python run_sniper.py EURUSDH1.csv EURUSDM5.csv")
        sys.exit(0)

    h1_path = _ROOT / sys.argv[1]
    m5_path = _ROOT / sys.argv[2]
    point = float(sys.argv[3]) if len(sys.argv) > 3 else 0.00001

    if not h1_path.exists():
        print(f"Не нашёл файл: {h1_path}")
        sys.exit(1)
    if not m5_path.exists():
        print(f"Не нашёл файл: {m5_path}")
        sys.exit(1)

    bars_h1 = read_mt5_csv(str(h1_path))
    bars_m5 = read_mt5_csv(str(m5_path))

    if not bars_h1 or not bars_m5:
        print("Не прочитал бары из CSV — проверь файлы.")
        sys.exit(1)

    karta = build_sniper_map(bars_h1, bars_m5, point=point)
    if not karta:
        return

    try:
        put_h1 = _ROOT / "sniper_h1.png"
        put_m5 = _ROOT / "sniper_m5.png"
        _narisovat_h1(bars_h1, karta["ТИУ"], karta["ЗК"], put_h1)
        _narisovat_m5(bars_m5, karta["ИУ"], karta["УРСТ"], put_m5)
        print()
        print(f"Готово. Открой картинки и сверь глазами с MT5:")
        print(f"  {put_h1}")
        print(f"  {put_m5}")
    except ImportError:
        print()
        print("Не нашёл matplotlib — поставь его один раз командой:")
        print("  pip install matplotlib")
        print("и запусти ещё раз, картинки появятся.")


if __name__ == "__main__":
    main()
