# run_bpz_varianty.py — запускать из корня Island-of-Hope
# ─────────────────────────────────────────────────────────────
# ОДНИ И ТЕ ЖЕ БЛОКИ, РАЗНЫЕ СПОСОБЫ ИХ ТОРГОВАТЬ.
#
# Зачем. Диагностика показала расхождение, которое нельзя объяснить
# рынком: 80% найденных блоков реально закрываются на 90% в течение
# двух суток, а наша торговля по ним даёт винрейт 54%. Явление
# сильное, сделка слабая. Значит теряем не на рынке, а по дороге
# от блока к ордеру.
#
# Главный подозреваемый — требование "цена должна сперва уйти ДАЛЬШЕ
# за блок, и только потом вернуться". Оно отсекает 81 блок из 133,
# и отбирает при этом ровно те, где импульс ПРОДОЛЖИЛСЯ — то есть
# наименее склонные закрываться. Плюс стоп ставится на экстремум
# этого же продолжения: чем сильнее ушло, тем дальше стоп.
#
# Скрипт НИЧЕГО не патчит. Берёт те же блоки (detect_bpz, пороги не
# трогаю) и прогоняет четыре способа входа на равных: одна история,
# один спред, один фильтр сессии, одна цель (90% закрытия).
#
#   БАЗА              — как сейчас: ждём ухода дальше, потом ретест
#                       ближнего края; стоп = экстремум продолжения
#   БАЗА+СТОП_БЛОКА   — тот же вход, но стоп = высота блока × k
#                       (проверяет: виноват вход или виноват стоп)
#   СРАЗУ k=1.0       — вход на закрытии самого блока, без ожидания;
#                       стоп = высота блока × 1.0
#   СРАЗУ k=2.0       — то же, стоп вдвое шире (проверяет: не режет
#                       ли нас слишком тесный стоп)
#
# Для каждого — не только PF, но и распределение по 6 окнам истории.
# PF без распределения город уже один раз обманул.
#
# Запуск:
#   python run_bpz_varianty.py EURUSDM5.csv
#   python run_bpz_varianty.py EURUSDM5.csv 0.00001 2
# ─────────────────────────────────────────────────────────────
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent
_BIRZHA = _ROOT / "Биржа"
sys.path.insert(0, str(_BIRZHA))

from sniper_core import (  # noqa: E402
    read_mt5_csv, compute_atr, detect_bpz, naiti_vhod_bpz, _chas_bara,
)
from sniper_backtest import _proiti_do_iskhoda, _svodka  # noqa: E402

OKON = 6
MAX_HOLD = 576          # двое суток M5 — окно из первоисточника
SESSIYA = (8, 23)


def _tsel(b: dict) -> float:
    """Цель одна на все варианты — 90% закрытия блока (правило автора)."""
    lo, hi = b["лоу"], b["хай"]
    return lo + 0.1 * (hi - lo) if b["направление"] == "UP" else hi - 0.1 * (hi - lo)


def vhod_srazu(bars, b, spred, k: float) -> Optional[dict]:
    """Вход на закрытии самого блока, без ожидания ухода и возврата.
    Ставка ровно на то, что измерено: блок закроется. Стоп — не по
    чужому экстремуму, а по собственной высоте блока."""
    idx = b["бар_индекс"]
    if idx + 1 >= len(bars):
        return None
    bar = bars[idx]
    chas = _chas_bara(bar)
    if chas is None or not (SESSIYA[0] <= chas <= SESSIYA[1]):
        return None
    lo, hi = b["лоу"], b["хай"]
    vysota = hi - lo
    if vysota <= 0:
        return None

    if b["направление"] == "UP":       # ждём возврата вниз -> продаём
        entry, stop, long = hi, hi + k * vysota, False
    else:                              # ждём возврата вверх -> покупаем
        entry, stop, long = lo, lo - k * vysota, True

    r = abs(stop - entry)
    if r <= spred:
        return None
    return {"entry_idx": idx, "entry_date": bar["date"], "entry": entry,
            "stop": stop, "target": _tsel(b), "r": r, "long": long}


def vhod_baza_stop_bloka(bars, b, spred, point, atr, k: float) -> Optional[dict]:
    """Вход как в базе (ждём ухода дальше + ретест), но стоп считаем
    от высоты блока, а не от экстремума продолжения. Разделяет два
    подозрения: плох вход или плох стоп."""
    v = naiti_vhod_bpz(bars, b, spred / point, point, atr, MAX_HOLD)
    if v is None:
        return None
    vysota = b["хай"] - b["лоу"]
    if vysota <= 0:
        return None
    entry = v["entry"]
    stop = entry + k * vysota if not v["long"] else entry - k * vysota
    r = abs(stop - entry)
    if r <= spred:
        return None
    return {**v, "stop": stop, "r": r}


def okna_istorii(bars):
    n = len(bars)
    gr = [bars[min(n - 1, k * n // OKON)]["date"] for k in range(OKON)] + [bars[-1]["date"]]
    return [(gr[k], gr[k + 1]) for k in range(OKON)]


def raspredelenie(sdelki, okna) -> str:
    """Компактная строка: сколько окон в плюсе и доля лучшего окна."""
    if not sdelki:
        return "—"
    itog = sum(s["R"] for s in sdelki)
    summy = []
    for i, (nach, kon) in enumerate(okna):
        if i < OKON - 1:
            v = [s for s in sdelki if nach <= s["дата"] < kon]
        else:
            v = [s for s in sdelki if nach <= s["дата"] <= kon]
        summy.append(sum(x["R"] for x in v))
    v_plyuse = sum(1 for s in summy if s > 0)
    if itog <= 0:
        return f"{v_plyuse}/{OKON} окон+"
    return f"{v_plyuse}/{OKON} окон+, лучшее {max(summy) / itog * 100:.0f}%"


def main():
    if len(sys.argv) < 2:
        print("Использование: python run_bpz_varianty.py <m5.csv> [point] [спред_пипсов]")
        print("Пример:        python run_bpz_varianty.py EURUSDM5.csv")
        sys.exit(0)

    m5_path = _ROOT / sys.argv[1]
    point = float(sys.argv[2]) if len(sys.argv) > 2 else 0.00001
    spred_p = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    spred = spred_p * point

    if not m5_path.exists():
        print(f"Не нашёл файл: {m5_path}")
        sys.exit(1)

    bars = read_mt5_csv(str(m5_path))
    if not bars:
        print("Не прочитал бары из CSV.")
        sys.exit(1)

    atr = compute_atr(bars)
    bloki = detect_bpz(bars, atr)
    okna = okna_istorii(bars)

    print(f"\n{'═' * 78}")
    print(f"БПЦ · ЧЕТЫРЕ СПОСОБА ВХОДА НА ОДНИХ И ТЕХ ЖЕ {len(bloki)} БЛОКАХ")
    print(f"{m5_path.name} · {bars[0]['date'][:10]} → {bars[-1]['date'][:10]} · "
          f"спред {spred_p}п на входе и выходе")
    print(f"{'═' * 78}")

    varianty = [
        ("БАЗА (как сейчас)",
         lambda b: naiti_vhod_bpz(bars, b, spred_p, point, atr, MAX_HOLD)),
        ("БАЗА + стоп блока k=1.0",
         lambda b: vhod_baza_stop_bloka(bars, b, spred, point, atr, 1.0)),
        ("СРАЗУ k=1.0",
         lambda b: vhod_srazu(bars, b, spred, 1.0)),
        ("СРАЗУ k=2.0",
         lambda b: vhod_srazu(bars, b, spred, 2.0)),
    ]

    print(f"\n{'Вариант':<26} {'Входов':>7} {'Винрейт':>8} {'Сумма R':>9} "
          f"{'PF':>6} {'Сред R':>8}  Распределение")
    print("-" * 78)

    for imya, postroit in varianty:
        sdelki = []
        for b in bloki:
            v = postroit(b)
            if not v:
                continue
            r = _proiti_do_iskhoda(bars, v, target=v["target"],
                                   max_hold_barov=MAX_HOLD, spred=spred)
            sdelki.append({"дата": v["entry_date"], "R": r})
        s = _svodka([x["R"] for x in sdelki])
        pf = s["профит_фактор"] if s["профит_фактор"] is not None else "—"
        wr = f"{s['винрейт']}%" if s["винрейт"] is not None else "—"
        sr = s["средний_R"] if s["средний_R"] is not None else "—"
        print(f"{imya:<26} {s['сделок']:>7} {wr:>8} {s['сумма_R']:>9} "
              f"{str(pf):>6} {str(sr):>8}  {raspredelenie(sdelki, okna)}")

    print("\nЧитать так:")
    print("  · Если СРАЗУ заметно лучше БАЗЫ — виновато требование")
    print("    'уйти дальше и вернуться': оно отбирает худшие блоки.")
    print("  · Если БАЗА+стоп_блока лучше БАЗЫ, а СРАЗУ нет — виноват")
    print("    не вход, а стоп на экстремуме продолжения.")
    print("  · Если все четыре примерно одинаковы — дело не в механике")
    print("    входа, и 80% закрытий просто не переводятся в деньги.")
    print("  · PF без распределения ничего не значит. Смотреть оба.\n")


if __name__ == "__main__":
    main()
