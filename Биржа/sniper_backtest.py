# Биржа/sniper_backtest.py
# ─────────────────────────────────────────────────────────────
# ГОЛЫЙ ПРОГОН школы Снайпер — ЭТАП 2 (§12 SCALPER_CEH_MASTER.md)
# Версия: 0.1 · без единого агента, без LLM · судья — статистика
#
# ПРАВКА 31.07 (Шеф): калибровка глазом отменена — не трейдер, не
# может судить уровни ("один так разметит, другой по-другому").
# Единственный судья теперь этот файл: прогоняет сетап ПРОБОЙ по
# всей истории, честно считает PF/винрейт/суммарный R для трёх
# вариантов выхода. Работает — двигаемся дальше. Не работает —
# честно хороним эскиз, как и обещано в мастер-доке (§11 вывод).
#
# ЗАКОН: PnL всегда ПОСЛЕ спреда — без него числа этого файла не
# существуют (см. §11 SCALPER_CEH_MASTER.md, "Спред — в фундамент").
# ─────────────────────────────────────────────────────────────

from pathlib import Path
from typing import Optional

from sniper_core import (
    read_mt5_csv, compute_atr, detect_pivots, detect_tiu, detect_iu,
    detect_zk, _chas_bara,
)

# ЗАКОН СЕССИИ (§0, §12 SCALPER_CEH_MASTER.md): торгуем только в
# европейскую и американскую сессии. Ночь (00:00-07:59 серверного) —
# цех спит, это время ЗК, не входов. Раньше прогон торговал 24 часа —
# это была НЕ система из документа, а урезанная версия без правила.
SESSIYA_NACHALO_CHAS = 8
SESSIYA_KONETS_CHAS = 23


# ════════════════════════════════════════════════════════════
# ОДНА СДЕЛКА — вход/стоп по ПРОБОЮ (§8: стоп сетапа 1 = противоположная
# граница коробки), три варианта выхода прогоняются по ОДНОМУ входу,
# чтобы сравнение было честным (не разные входы вперемешку).
# ════════════════════════════════════════════════════════════

def _postroit_vhod(bars_m5: list[dict], iu: dict,
                   spred_pipsov: float, point: float) -> Optional[dict]:
    """Вход СЛЕДУЮЩИМ баром после закрепления (не на баре импульса —
    так в реальности и торгуют, импульсный бар уже закрылся)."""
    if not iu["закреплён"]:
        return None  # сетап ПРОБОЙ требует закрепления (§2 канона)

    entry_idx = iu["импульсный_бар_индекс"] + 3  # после zakreplenie_barov=2
    if entry_idx >= len(bars_m5):
        return None

    chas = _chas_bara(bars_m5[entry_idx])
    if chas is None or not (SESSIYA_NACHALO_CHAS <= chas <= SESSIYA_KONETS_CHAS):
        return None  # ночь — цех спит, вход не берём

    spred = spred_pipsov * point
    long = iu["полярность"] == "HIGH"

    entry = bars_m5[entry_idx]["open"] + (spred if long else 0.0)
    stop = iu["коробка_лоу"] if long else iu["коробка_хай"]
    r = abs(entry - stop)
    if r <= spred:  # стоп уже съеден спредом — сделка без смысла
        return None

    return {
        "entry_idx": entry_idx, "entry_date": bars_m5[entry_idx]["date"],
        "entry": entry, "stop": stop, "r": r, "long": long,
        "уровень": iu["уровень"],
    }


def _proiti_do_iskhoda(bars_m5: list[dict], sdelka: dict,
                       target: Optional[float] = None,
                       trailing_pivoty: Optional[list] = None,
                       max_hold_barov: int = 288) -> float:
    """Идёт бар за баром от входа до стопа/цели/потолка удержания.
    Возвращает PnL в R (может быть отрицательным). Консервативно:
    если в одном баре задет и стоп, и цель — считается стоп (баг в
    пользу пессимизма безопаснее, чем в пользу оптимизма).

    max_hold_barov=288 (сутки M5) — система внутридневная (§0 "перенос
    через ночь не приветствуется"), сделка не должна ехать месяцами.
    Если к потолку не закрылась — закрываем по цене принудительно,
    как и в реальности закрыли бы позицию к концу сессии."""
    entry, stop, r, long = sdelka["entry"], sdelka["stop"], sdelka["r"], sdelka["long"]
    tekushchiy_stop = stop
    n = len(bars_m5)
    entry_idx = sdelka["entry_idx"]

    # БАГФИКС: пивоты берём ТОЛЬКО после входа — раньше сканировали
    # с начала всей истории (годы чужих, не относящихся к сделке
    # экстремумов), и стоп мог задраться на случайную древнюю цену.
    piv_idx = 0
    if trailing_pivoty:
        while piv_idx < len(trailing_pivoty) and trailing_pivoty[piv_idx]["bar_index"] <= entry_idx:
            piv_idx += 1

    predel = min(n, entry_idx + 1 + max_hold_barov)

    for i in range(entry_idx + 1, predel):
        b = bars_m5[i]

        if trailing_pivoty:
            while piv_idx < len(trailing_pivoty) and trailing_pivoty[piv_idx]["bar_index"] < i:
                p = trailing_pivoty[piv_idx]
                if long and p["type"] == "LOW" and p["price"] > tekushchiy_stop:
                    tekushchiy_stop = p["price"]
                elif not long and p["type"] == "HIGH" and p["price"] < tekushchiy_stop:
                    tekushchiy_stop = p["price"]
                piv_idx += 1

        if long:
            if b["low"] <= tekushchiy_stop:
                return (tekushchiy_stop - entry) / r
            if target is not None and b["high"] >= target:
                return (target - entry) / r
        else:
            if b["high"] >= tekushchiy_stop:
                return (entry - tekushchiy_stop) / r
            if target is not None and b["low"] <= target:
                return (entry - target) / r

    # потолок удержания или конец истории — закрываем по цене
    posl = bars_m5[predel - 1]["close"]
    return ((posl - entry) / r) if long else ((entry - posl) / r)


def _naiti_protivopolozhnyy_tiu(entry: float, long: bool, tiu: list[dict]) -> Optional[float]:
    """Ближайший ТИУ по ходу сделки — цель варианта Б."""
    kandidaty = [u["цена_центр"] for u in tiu
                if (u["цена_центр"] > entry) == long]
    if not kandidaty:
        return None
    return min(kandidaty, key=lambda p: abs(p - entry))


def _dnevnoy_bias(data: str, zk_po_datam: dict, tsena: float) -> Optional[str]:
    """Направление дня по §0/§12 канона: 'Тренд дня определяется
    пробоем ночного флэта (ЗК)'. Если день ещё не определился (цена
    внутри флэта) или флэт невалиден/не найден — контекста нет, и
    без контекста сделку не берём (закон школы: 'контекст разрешает,
    триггер исполняет' — сам триггер разрешения не даёт)."""
    z = zk_po_datam.get(data)
    if not z or not z["валиден"]:
        return None
    if tsena > z["флэт_хай"]:
        return "HIGH"
    if tsena < z["флэт_лоу"]:
        return "LOW"
    return None


# ════════════════════════════════════════════════════════════
# ПРОГОН ПО ВСЕЙ ИСТОРИИ
# ════════════════════════════════════════════════════════════

def goliy_progon_proboy(bars_h1: list[dict], bars_m5: list[dict],
                        point: float, spred_pipsov: float = 2.0) -> dict:
    """
    Прогоняет сетап ПРОБОЙ (ИУ с закреплением) по всей истории M5.
    ПРАВКА 31.07: добавлены два недостающих правила канона, без
    которых это была не система из документа, а урезанная версия:
      · сессия (§0/§12) — уже в _postroit_vhod
      · контекст H1 (§0/§3) — вход берём, ТОЛЬКО если направление
        M5-пробоя совпадает с направлением дня (пробой ЗК на H1).
        Без этого совпадения контекста нет — сделку не берём вовсе,
        не подгоняем цель/стоп, просто пропускаем.

    Три варианта выхода — каждый на ТОМ ЖЕ входе, для честного
    сравнения:
      A1/A2/A3 — фикс-цель 1R / 1.5R / 2R
      Б        — противоположный уровень H1 (ближайший ТИУ)
      В        — трейлинг по пивотам M5
    """
    atr_h1 = compute_atr(bars_h1)
    atr_m5 = compute_atr(bars_m5)

    tiu = detect_tiu(bars_h1, atr_h1)
    iu = detect_iu(bars_m5, atr_m5)
    zk = detect_zk(bars_h1, atr_h1, point=point)
    zk_po_datam = {z["дата"]: z for z in zk}
    pivoty_m5 = detect_pivots(bars_m5, lookback=2)

    vkhody = []
    bez_konteksta = 0
    for u in iu:
        v = _postroit_vhod(bars_m5, u, spred_pipsov, point)
        if not v:
            continue
        data = v["entry_date"].split(" ")[0]
        bias = _dnevnoy_bias(data, zk_po_datam, v["entry"])
        if bias is None or bias != u["полярность"]:
            bez_konteksta += 1
            continue  # M5-сигнал есть, но H1 не разрешает — не берём
        vkhody.append(v)

    rezultaty: dict = {
        "1R": [], "1.5R": [], "2R": [], "Б_противоположный_ТИУ": [], "В_трейлинг": [],
    }

    for sdelka in vkhody:
        entry, stop, r, long = sdelka["entry"], sdelka["stop"], sdelka["r"], sdelka["long"]

        for imya, mult in (("1R", 1.0), ("1.5R", 1.5), ("2R", 2.0)):
            target = entry + (mult * r if long else -mult * r)
            rezultaty[imya].append(_proiti_do_iskhoda(bars_m5, sdelka, target=target))

        tsel_b = _naiti_protivopolozhnyy_tiu(entry, long, tiu)
        if tsel_b is not None:
            rezultaty["Б_противоположный_ТИУ"].append(
                _proiti_do_iskhoda(bars_m5, sdelka, target=tsel_b))

        rezultaty["В_трейлинг"].append(
            _proiti_do_iskhoda(bars_m5, sdelka, target=None, trailing_pivoty=pivoty_m5))


    return {"сделок_всего": len(vkhody), "по_вариантам": rezultaty,
           "отсеяно_без_контекста_h1": bez_konteksta}


def _svodka(pnl_list: list[float]) -> dict:
    if not pnl_list:
        return {"сделок": 0, "винрейт": None, "сумма_R": 0.0,
                "профит_фактор": None, "средний_R": None}
    n = len(pnl_list)
    pobedy = [p for p in pnl_list if p > 0]
    porazheniya = [p for p in pnl_list if p <= 0]
    suma = sum(pnl_list)
    proshlo_v_plyus = sum(pobedy)
    proshlo_v_minus = abs(sum(porazheniya))
    pf = (proshlo_v_plyus / proshlo_v_minus) if proshlo_v_minus > 0 else None
    return {
        "сделок": n,
        "винрейт": round(len(pobedy) / n * 100, 1),
        "сумма_R": round(suma, 2),
        "профит_фактор": round(pf, 2) if pf is not None else None,
        "средний_R": round(suma / n, 3),
    }


# ════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Использование: python sniper_backtest.py <h1.csv> <m5.csv> [point] [спред_пипсов]")
        print("Пример:        python sniper_backtest.py EURUSDH1.csv EURUSDM5.csv 0.00001 2")
        sys.exit(0)

    h1_path, m5_path = sys.argv[1], sys.argv[2]
    point = float(sys.argv[3]) if len(sys.argv) > 3 else 0.00001
    spred = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0

    bars_h1 = read_mt5_csv(h1_path)
    bars_m5 = read_mt5_csv(m5_path)

    if not bars_h1 or not bars_m5:
        print("Не прочитал бары — проверь файлы.")
        sys.exit(1)

    rez = goliy_progon_proboy(bars_h1, bars_m5, point=point, spred_pipsov=spred)

    print(f"\nСетап ПРОБОЙ · входов после сессии+контекста H1: {rez['сделок_всего']}")
    print(f"(отсеяно по несовпадению с направлением дня H1: "
          f"{rez['отсеяно_без_контекста_h1']})")
    print(f"Спред учтён: {spred} пунктов на каждый вход\n")
    print(f"{'Выход':<26} {'Сделок':>7} {'Винрейт':>9} {'Сумма R':>10} "
          f"{'PF':>7} {'Сред. R':>9}")
    print("-" * 72)
    for imya, pnl_list in rez["по_вариантам"].items():
        s = _svodka(pnl_list)
        print(f"{imya:<26} {s['сделок']:>7} "
              f"{(str(s['винрейт'])+'%') if s['винрейт'] is not None else '—':>9} "
              f"{s['сумма_R']:>10} "
              f"{s['профит_фактор'] if s['профит_фактор'] is not None else '—':>7} "
              f"{s['средний_R'] if s['средний_R'] is not None else '—':>9}")

    print("\nЧестно: PF > 1 значит суммарно в плюсе, PF < 1 — в минусе.")
    print("Мало сделок (< ~30) — числу пока нельзя доверять, выборка мала.")

# SNIPER_BACKTEST_V1 — маркер идемпотентности
