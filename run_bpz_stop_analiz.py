# run_bpz_stop_analiz.py — запускать из корня Island-of-Hope
# ─────────────────────────────────────────────────────────────
# ПОСЛЕДНЯЯ ПРОВЕРКА ПЕРЕД ТЕМ, КАК ВЕРИТЬ БПЦ.
#
# БАЗА устояла на трёх инструментах (PF 1.82 / 2.30 / 1.64, большинство
# окон в плюсе везде). Это профиль Necron. Но в её коде стоит порог
# min_stop_atr = 0.5, и рядом с ним честная запись: до него стоп в
# 0.08×ATR на XAUUSD давал ложные +165R.
#
# То есть класс ошибки реален, его уже ловили, а сам порог 0.5 никто
# не подбирал и не проверял — он поставлен затычкой. Если весь плюс
# БПЦ сидит вплотную к этой затычке, значит результат держит она, а
# не рынок. Это подгонка, просто спрятанная в константе.
#
# Скрипт спрашивает ровно это, двумя способами:
#
#   1. ПРОТЯЖКА ПОРОГА. Гоняет БАЗУ с min_stop_atr от 0.25 до 2.0.
#      Хорошо: PF плавно едет, плюс держится в широком диапазоне.
#      Плохо: острый пик у 0.5 и обвал по сторонам — остриё.
#
#   2. РАЗРЕЗ ПО ШИРИНЕ СТОПА. Делит сделки на три равные группы по
#      стоп/ATR и смотрит, где сидит прибыль.
#      Хорошо: плюс во всех трёх группах.
#      Плохо: всё в самой узкой — значит живём на краю затычки.
#
# Ничего не патчит. Запуск:
#   python run_bpz_stop_analiz.py EURUSDM5.csv
#   python run_bpz_stop_analiz.py XAUUSDM5.csv 0.01 16
# ─────────────────────────────────────────────────────────────
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "Биржа"))

from sniper_core import (  # noqa: E402
    read_mt5_csv, compute_atr, detect_bpz, naiti_vhod_bpz,
)
from sniper_backtest import _proiti_do_iskhoda, _svodka  # noqa: E402

OKON = 6
MAX_HOLD = 576
POROGI = [0.25, 0.4, 0.5, 0.6, 0.75, 1.0, 1.5, 2.0]


def sobrat(bars, bloki, atr, spred_p, point, porog):
    sdelki = []
    for b in bloki:
        v = naiti_vhod_bpz(bars, b, spred_p, point, atr, MAX_HOLD,
                           min_stop_atr=porog)
        if not v:
            continue
        r = _proiti_do_iskhoda(bars, v, target=v["target"],
                               max_hold_barov=MAX_HOLD, spred=spred_p * point)
        a = atr[v["entry_idx"]] if v["entry_idx"] < len(atr) else None
        sdelki.append({"дата": v["entry_date"], "R": r,
                       "стоп_atr": (v["r"] / a) if a else None})
    return sdelki


def okna_v_plyuse(bars, sdelki):
    if not sdelki:
        return "—"
    n = len(bars)
    gr = [bars[min(n - 1, k * n // OKON)]["date"] for k in range(OKON)] + [bars[-1]["date"]]
    summy = []
    for k in range(OKON):
        nach, kon = gr[k], gr[k + 1]
        v = [s for s in sdelki if (nach <= s["дата"] < kon)] if k < OKON - 1 \
            else [s for s in sdelki if nach <= s["дата"] <= kon]
        summy.append(sum(x["R"] for x in v))
    return f"{sum(1 for s in summy if s > 0)}/{OKON}"


def stroka(imya, sdelki, bars, shirina=22):
    s = _svodka([x["R"] for x in sdelki])
    pf = s["профит_фактор"] if s["профит_фактор"] is not None else "—"
    wr = f"{s['винрейт']}%" if s["винрейт"] is not None else "—"
    return (f"{imya:<{shirina}} {s['сделок']:>7} {wr:>8} {s['сумма_R']:>9} "
            f"{str(pf):>6}  {okna_v_plyuse(bars, sdelki):>5}")


def main():
    if len(sys.argv) < 2:
        print("Использование: python run_bpz_stop_analiz.py <m5.csv> [point] [спред]")
        sys.exit(0)

    m5 = _ROOT / sys.argv[1]
    point = float(sys.argv[2]) if len(sys.argv) > 2 else 0.00001
    spred_p = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    if not m5.exists():
        print(f"Не нашёл файл: {m5}")
        sys.exit(1)

    bars = read_mt5_csv(str(m5))
    atr = compute_atr(bars)
    bloki = detect_bpz(bars, atr)

    print(f"\n{'═' * 72}")
    print(f"БПЦ · ДЕРЖИТ ЛИ РЕЗУЛЬТАТ ПОРОГ min_stop_atr")
    print(f"{m5.name} · блоков {len(bloki)} · спред {spred_p}п")
    print(f"{'═' * 72}")

    # ── 1. протяжка порога ────────────────────────────────
    print(f"\n1. ПРОТЯЖКА ПОРОГА (сейчас в коде стоит 0.5)")
    print(f"{'-' * 72}")
    print(f"{'min_stop_atr':<22} {'Сделок':>7} {'Винрейт':>8} {'Сумма R':>9} {'PF':>6}  {'Окна+':>5}")
    for p in POROGI:
        sd = sobrat(bars, bloki, atr, spred_p, point, p)
        metka = "  ← в коде" if abs(p - 0.5) < 1e-9 else ""
        print(stroka(f"{p:.2f}", sd, bars) + metka)

    print("\n   Плавно едет и плюс в широком диапазоне — порог не решающий.")
    print("   Острый пик у 0.5 с обвалом по сторонам — остриё, подгонка.")

    # ── 2. разрез по ширине стопа ─────────────────────────
    baza = [s for s in sobrat(bars, bloki, atr, spred_p, point, 0.5)
            if s["стоп_atr"] is not None]
    print(f"\n2. ГДЕ СИДИТ ПРИБЫЛЬ — РАЗРЕЗ ПО ШИРИНЕ СТОПА (порог 0.5)")
    print(f"{'-' * 72}")
    if len(baza) < 9:
        print("   Сделок слишком мало для разреза.")
    else:
        baza.sort(key=lambda s: s["стоп_atr"])
        k = len(baza) // 3
        gruppy = [("узкие стопы", baza[:k]),
                  ("средние", baza[k:2 * k]),
                  ("широкие стопы", baza[2 * k:])]
        itog = sum(s["R"] for s in baza)
        print(f"{'Группа':<22} {'Сделок':>7} {'Винрейт':>8} {'Сумма R':>9} {'PF':>6}  {'Окна+':>5}")
        for imya, g in gruppy:
            print(stroka(imya, g, bars))
        print()
        for imya, g in gruppy:
            summa = sum(s["R"] for s in g)
            dolya = (summa / itog * 100) if itog else 0.0
            print(f"   {imya:<16} стоп {g[0]['стоп_atr']:.2f}–{g[-1]['стоп_atr']:.2f} ATR"
                  f"   даёт {dolya:>5.0f}% итога")
        print("\n   Плюс во всех трёх группах — БПЦ живёт сам.")
        print("   Весь плюс в узких — живём на краю затычки, это не край.")

    print()


if __name__ == "__main__":
    main()
