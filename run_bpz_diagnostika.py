# run_bpz_diagnostika.py — запускать из корня Island-of-Hope
# ─────────────────────────────────────────────────────────────
# НЕ прогон. Вскрытие одного-единственного положительного результата
# во всём Снайпере — Блока Пустых Цен. Три вопроса, три ответа.
#
# ВОПРОС 1. Толстый хвост или везение на одном окне?
#   Город уже различал эти два случая (Биржа материка, §5т/§5у):
#   у боевой формулы Искры концентрация 17-58%, но победы размазаны
#   по всей истории — законный толстый хвост, пущено в бой.
#   У фрактал-триггера Брута весь результат сидел в одном 45-дневном
#   окне (128-339% итога) — везение, в бой не пущено.
#   По одному числу "топ-5 = 101%" эти два случая НЕРАЗЛИЧИМЫ.
#   Различают их ДАТЫ. Скрипт режет историю на равные окна и
#   смотрит, сколько окон в плюсе и сколько итога даёт лучшее.
#
# ВОПРОС 2. Правда ли то, что заявляет автор?
#   Первоисточник (Blok_Pustykh_Tsen_1.pdf): блок закрывается минимум
#   на 90% в течение 1-2 суток, правило отработки ~90%. Это
#   ПРОВЕРЯЕМОЕ утверждение, и оно проверяется без всякой торговли:
#   просто взять все найденные блоки и посмотреть, сколько из них
#   реально закрылись на 90%. Ответ говорит не про наш код, а про
#   автора — ровно тот вопрос, который Шеф назвал "сказочник".
#
# ВОПРОС 3. Не держится ли всё на одном годе/квартале?
#   Разбивка по календарным месяцам входа.
#
# Запуск:
#   python run_bpz_diagnostika.py EURUSDM5.csv
#   python run_bpz_diagnostika.py EURUSDM5.csv 0.00001 2
# ─────────────────────────────────────────────────────────────
import sys
from collections import OrderedDict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BIRZHA = _ROOT / "Биржа"
sys.path.insert(0, str(_BIRZHA))

from sniper_core import (  # noqa: E402
    read_mt5_csv, compute_atr, detect_bpz, naiti_vhod_bpz,
)
from sniper_backtest import _proiti_do_iskhoda, _svodka  # noqa: E402

OKON = 6  # на сколько равных окон резать историю


def zakrylsya_li_blok(bars, b, max_barov=576, dolya=0.9):
    """Прямая проверка заявления автора, БЕЗ всякой торговли: дошла ли
    цена до dolya закрытия блока в течение max_barov баров после него.
    Никаких ретестов, сессий, стопов — только сам факт закрытия."""
    idx = b["бар_индекс"]
    lo, hi = b["лоу"], b["хай"]
    vysota = hi - lo
    if vysota <= 0:
        return False
    predel = min(len(bars), idx + 1 + max_barov)
    if b["направление"] == "UP":
        porog = lo + (1.0 - dolya) * vysota
        return any(bars[j]["low"] <= porog for j in range(idx + 1, predel))
    porog = hi - (1.0 - dolya) * vysota
    return any(bars[j]["high"] >= porog for j in range(idx + 1, predel))


def main():
    if len(sys.argv) < 2:
        print("Использование: python run_bpz_diagnostika.py <m5.csv> [point] [спред_пипсов]")
        print("Пример:        python run_bpz_diagnostika.py EURUSDM5.csv")
        sys.exit(0)

    m5_path = _ROOT / sys.argv[1]
    point = float(sys.argv[2]) if len(sys.argv) > 2 else 0.00001
    spred_p = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0

    if not m5_path.exists():
        print(f"Не нашёл файл: {m5_path}")
        sys.exit(1)

    bars = read_mt5_csv(str(m5_path))
    if not bars:
        print("Не прочитал бары из CSV.")
        sys.exit(1)

    atr = compute_atr(bars)
    bloki = detect_bpz(bars, atr)

    sdelki = []
    for b in bloki:
        v = naiti_vhod_bpz(bars, b, spred_p, point, atr)
        if not v:
            continue
        r = _proiti_do_iskhoda(bars, v, target=v["target"],
                               max_hold_barov=576, spred=spred_p * point)
        sdelki.append({"дата": v["entry_date"], "R": r,
                       "направление": "SELL" if not v["long"] else "BUY"})
    sdelki.sort(key=lambda s: s["дата"])

    print(f"\n{'═'*66}")
    print(f"ДИАГНОСТИКА БПЦ · {m5_path.name}")
    print(f"История: {bars[0]['date']} → {bars[-1]['date']} ({len(bars)} баров)")
    print(f"{'═'*66}")

    if not sdelki:
        print("\nСделок нет — дальше смотреть нечего.")
        return

    itog = sum(s["R"] for s in sdelki)
    svod = _svodka([s["R"] for s in sdelki])
    print(f"\nБлоков найдено: {len(bloki)} · сделок: {svod['сделок']} · "
          f"винрейт {svod['винрейт']}% · итог {svod['сумма_R']}R · PF {svod['профит_фактор']}")

    # ── ВОПРОС 1: концентрация ВО ВРЕМЕНИ ─────────────────────
    print(f"\n{'─'*66}")
    print(f"1. РАСПРЕДЕЛЕНИЕ ПО ВРЕМЕНИ — {OKON} равных окон истории")
    print(f"{'─'*66}")
    print("   Толстый хвост: плюс размазан, большинство окон в плюсе.")
    print("   Везение: одно окно даёт весь итог, остальные около нуля.\n")

    n = len(bars)
    granitsy = [bars[min(n - 1, k * n // OKON)]["date"] for k in range(OKON)] + [bars[-1]["date"]]
    okna = []
    for k in range(OKON):
        nach, kon = granitsy[k], granitsy[k + 1]
        v_okne = [s for s in sdelki if nach <= s["дата"] < kon] if k < OKON - 1 \
            else [s for s in sdelki if nach <= s["дата"] <= kon]
        okna.append((nach[:10], kon[:10], v_okne))

    print(f"   {'Окно':<24} {'Сделок':>7} {'Сумма R':>10} {'Доля итога':>12}")
    v_plyuse = 0
    luchshee = 0.0
    for nach, kon, v_okne in okna:
        s = sum(x["R"] for x in v_okne)
        if s > 0:
            v_plyuse += 1
        luchshee = max(luchshee, s)
        dolya = (s / itog * 100) if itog != 0 else 0.0
        print(f"   {nach}–{kon:<11} {len(v_okne):>7} {s:>10.2f} {dolya:>11.0f}%")

    print(f"\n   Окон в плюсе: {v_plyuse} из {OKON}")
    if itog > 0:
        print(f"   Лучшее окно даёт {luchshee / itog * 100:.0f}% итога")
        if luchshee / itog > 1.0:
            print("   ⚠ ОДНО окно даёт больше 100% итога — остальная история")
            print("     суммарно в минусе. Это профиль ВЕЗЕНИЯ, как у")
            print("     фрактал-триггера Брута. В бой такое город не пускал.")
        elif v_plyuse >= OKON - 1:
            print("   ✓ Плюс размазан по истории — профиль ТОЛСТОГО ХВОСТА,")
            print("     как у боевой формулы Искры.")
        else:
            print("   · Промежуточно. Нужна проверка на других инструментах,")
            print("     одного этого не хватит для решения.")

    # ── ВОПРОС 2: правда ли заявление автора ──────────────────
    print(f"\n{'─'*66}")
    print("2. ЗАЯВЛЕНИЕ АВТОРА ПРОТИВ ФАКТА")
    print(f"{'─'*66}")
    print("   Первоисточник: блок закрывается минимум на 90% в течение")
    print("   1-2 суток, отработка ~90%. Проверяем прямо, без торговли.\n")

    for dolya, imya in ((0.9, "90%"), (0.5, "50%")):
        zakrylis = sum(1 for b in bloki if zakrylsya_li_blok(bars, b, 576, dolya))
        prots = zakrylis / len(bloki) * 100 if bloki else 0.0
        print(f"   закрылись на {imya} за 2 суток: {zakrylis} из {len(bloki)}  ({prots:.0f}%)")

    zakrylis_nedelya = sum(1 for b in bloki if zakrylsya_li_blok(bars, b, 2016, 0.9))
    print(f"   закрылись на 90% за неделю:  {zakrylis_nedelya} из {len(bloki)}  "
          f"({zakrylis_nedelya / len(bloki) * 100:.0f}%)")
    print("\n   Автор обещает ~90%. Насколько цифра выше расходится с этим —")
    print("   настолько к остальным его числам стоит относиться осторожнее.")

    # ── ВОПРОС 3: по месяцам ──────────────────────────────────
    print(f"\n{'─'*66}")
    print("3. ПО МЕСЯЦАМ ВХОДА")
    print(f"{'─'*66}")
    po_mes: OrderedDict = OrderedDict()
    for s in sdelki:
        klyuch = s["дата"][:7]
        po_mes.setdefault(klyuch, []).append(s["R"])
    for mes, rs in po_mes.items():
        summa = sum(rs)
        stolbik = ("+" * min(20, int(summa))) if summa > 0 else ("-" * min(20, int(-summa)))
        print(f"   {mes}  сделок {len(rs):>3}  R {summa:>7.2f}  {stolbik}")

    mes_v_plyuse = sum(1 for rs in po_mes.values() if sum(rs) > 0)
    print(f"\n   Месяцев в плюсе: {mes_v_plyuse} из {len(po_mes)}")

    # ── топ-сделки с датами ───────────────────────────────────
    print(f"\n{'─'*66}")
    print("4. ПЯТЬ ЛУЧШИХ СДЕЛОК — КОГДА ИМЕННО")
    print(f"{'─'*66}")
    for s in sorted(sdelki, key=lambda x: -x["R"])[:5]:
        print(f"   {s['дата']}  {s['направление']:<5} {s['R']:>+7.2f}R")
    print("\n   Если все пять сидят в одном месяце — это одно рыночное")
    print("   событие, посчитанное пять раз, а не пять независимых удач.\n")


if __name__ == "__main__":
    main()
