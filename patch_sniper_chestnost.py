# patch_sniper_chestnost.py — запускать из корня Island-of-Hope
# ─────────────────────────────────────────────────────────────
# ПАТЧ ЧЕСТНОСТИ СНАЙПЕРА · 01.08.2026
#
# Шесть правок. Пять из них — не улучшения, а починка того, что
# делало прошлые пять прогонов недействительными:
#
#   1. ГРАНИЦЫ БЛОКА ПО ТЕЛАМ, НЕ ПО ТЕНЯМ (detect_iu).
#      ТЗ говорит прямо: границы строятся ИСКЛЮЧИТЕЛЬНО по телам,
#      шпили исключены, потому что они и есть механизм сноса стопов
#      толпы. Код брал max(high)/min(low) — то есть строил уровень
#      ровно по ловушке. Через detect_blocks_generic это касалось
#      и блоков H1, и H4. Добавлен ключ granitsy_po_telam=True,
#      старое поведение доступно как False — для сравнения на равных.
#
#   2. СПРЕД НА ВЫХОДЕ ИЗ ШОРТА (_proiti_do_iskhoda).
#      Бары MT5 — это BID. Покупка на закрытие шорта идёт по ASK.
#      Каждая короткая сделка получала бесплатный спред, а её стоп
#      срабатывал позже, чем сработал бы в жизни. Лонги были
#      посчитаны верно (вход по ask уже был), их не трогаю.
#
#   3. ТРЕНД H4 ИЗ БУДУЩЕГО (goliy_progon_blok_h1_h4).
#      Тренд считался ОДИН раз по последнему бару всей истории и
#      применялся ко всем сделкам за все годы. Сделка 2019 года
#      получала направление по цене 2026-го, и у всех коррекционных
#      блоков сразу была одна и та же сторона. Гипотезу 4 надо
#      считать НЕ проверенной, а не "край не найден".
#
#   4. БЛОК H4 ИЗ БУДУЩЕГО И СРАВНЕНИЕ РАЗНЫХ ЛИНЕЕК
#      (klassifitsirovat_blok_h1). "Ближайший" блок H4 искался по
#      разнице индексов баров РАЗНЫХ таймфреймов — величины
#      несопоставимые, выбор был случайным; и искался в обе стороны,
#      то есть мог взять блок H4, которого ещё не существовало.
#      Теперь: по датам, только назад.
#
#   5. ЦЕЛЬ ИЗ БУДУЩЕГО (вариант "Б — противоположный ТИУ").
#      Целью брался уровень из списка, посчитанного по всей истории:
#      сделка 2019 года целилась в уровень, который наберёт свои
#      касания в 2022-м. Вариант убран целиком.
#
#   6. ТРЕЙЛИНГ ПО ЕЩЁ НЕ ИЗВЕСТНОМУ ПИВОТУ + БЛОК, ЕЩЁ НЕ
#      ПОДТВЕРЖДЁННЫЙ. Пивот с lookback=2 известен только через 2
#      бара после вершины, а стоп двигался уже на следующем. И
#      направление дня применялось с бара импульса, хотя блок
#      подтверждается закреплением на несколько баров позже.
#
# ЧЕГО ПАТЧ НЕ ДЕЛАЕТ: не трогает три категории надёжности из ТЗ
# (Безопасные/Консервативные/Агрессивные) — это следующая, отдельная
# работа. И не обещает, что после него появится край. Он только
# убирает основания не верить цифрам.
#
# Идемпотентен: второй запуск ничего не делает. Бэкапы .bak_chestnost.
# ─────────────────────────────────────────────────────────────

import ast
import shutil
import sys
from pathlib import Path

MARKER = "SNIPER_CHESTNOST_V1"
ROOT = Path(__file__).resolve().parent
BIRZHA = ROOT / "Биржа"

CORE = BIRZHA / "sniper_core.py"
BACKTEST = BIRZHA / "sniper_backtest.py"


# ═══════════════════════════════════════════════════════════
# ПРАВКИ ЯДРА
# ═══════════════════════════════════════════════════════════

CORE_PRAVKI = [
    # ── 1. detect_iu: параметр границ ──────────────────────
    (
        1,
        """def detect_iu(bars_m5: list[dict], atr_m5: list[Optional[float]],
             okno_min: int = 8, okno_max: int = 30,
             box_range_atr: float = 1.8, impuls_telo_atr: float = 1.0,
             zakreplenie_barov: int = 2) -> list[dict]:""",
        """def detect_iu(bars_m5: list[dict], atr_m5: list[Optional[float]],
             okno_min: int = 8, okno_max: int = 30,
             box_range_atr: float = 1.8, impuls_telo_atr: float = 1.0,
             zakreplenie_barov: int = 2,
             granitsy_po_telam: bool = True) -> list[dict]:""",
    ),
    # ── 1б. detect_iu: сами границы ────────────────────────
    (
        1,
        """            segment = bars_m5[i:i + okno]
            hi = max(b["high"] for b in segment)
            lo = min(b["low"] for b in segment)""",
        """            segment = bars_m5[i:i + okno]
            if granitsy_po_telam:
                # ЗАКОН ТЗ: границы блока — ИСКЛЮЧИТЕЛЬНО по телам
                # свечей. Тени исключены не для красоты: по
                # первоисточнику шпиль — это и есть снос стопов толпы.
                # Строить границу по тени = строить уровень по чужой
                # ловушке, а потом ставить туда же собственный стоп.
                hi = max(max(b["open"], b["close"]) for b in segment)
                lo = min(min(b["open"], b["close"]) for b in segment)
            else:
                # старое поведение — оставлено только чтобы можно было
                # сравнить два прогона на равных, а не по памяти
                hi = max(b["high"] for b in segment)
                lo = min(b["low"] for b in segment)""",
    ),
    # ── 2. detect_blocks_generic: проброс ключа ────────────
    (
        1,
        """def detect_blocks_generic(bars: list[dict], atr: list[Optional[float]],
                          okno_min: int = 8, okno_max: int = 30,
                          box_range_atr: float = 1.8,
                          impuls_telo_atr: float = 1.0,
                          zakreplenie_barov: int = 2) -> list[dict]:""",
        """def detect_blocks_generic(bars: list[dict], atr: list[Optional[float]],
                          okno_min: int = 8, okno_max: int = 30,
                          box_range_atr: float = 1.8,
                          impuls_telo_atr: float = 1.0,
                          zakreplenie_barov: int = 2,
                          granitsy_po_telam: bool = True) -> list[dict]:""",
    ),
    (
        1,
        """    return detect_iu(bars, atr, okno_min=okno_min, okno_max=okno_max,
                     box_range_atr=box_range_atr,
                     impuls_telo_atr=impuls_telo_atr,
                     zakreplenie_barov=zakreplenie_barov)""",
        """    return detect_iu(bars, atr, okno_min=okno_min, okno_max=okno_max,
                     box_range_atr=box_range_atr,
                     impuls_telo_atr=impuls_telo_atr,
                     zakreplenie_barov=zakreplenie_barov,
                     granitsy_po_telam=granitsy_po_telam)""",
    ),
    # ── 3. h4_trend_seychas: тренд на момент, а не на конец ─
    (
        1,
        """def h4_trend_seychas(bars_h4: list[dict], lookback: int = 20) -> Optional[str]:
    \"\"\"Грубый тренд старшего этажа: close сейчас против close
    lookback баров назад. Нужен только для стороны коррекционной
    сделки (играем ПРОТИВ этого тренда).\"\"\"
    n = len(bars_h4)
    if n < lookback + 1:
        return None
    now = bars_h4[-1]["close"]
    togda = bars_h4[-1 - lookback]["close"]""",
        """def h4_trend_seychas(bars_h4: list[dict], lookback: int = 20,
                     do_indeksa: Optional[int] = None) -> Optional[str]:
    \"\"\"Грубый тренд старшего этажа: close сейчас против close
    lookback баров назад. Нужен только для стороны коррекционной
    сделки (играем ПРОТИВ этого тренда).

    ПРАВКА 01.08: do_indeksa — на КАКОЙ момент считать тренд. Без
    него функция всегда отвечала про последний бар переданной
    истории, и прогон применял один и тот же ответ ко всем сделкам
    за все годы (сделка 2019 года получала тренд 2026-го). Оставлен
    старый смысл по умолчанию только для живого использования, где
    'последний бар' действительно означает 'сейчас'.\"\"\"
    n = len(bars_h4)
    kon = (n - 1) if do_indeksa is None else min(int(do_indeksa), n - 1)
    if kon < lookback:
        return None
    now = bars_h4[kon]["close"]
    togda = bars_h4[kon - lookback]["close"]""",
    ),
    # ── 4. klassifitsirovat_blok_h1: только прошлое, по датам ─
    (
        1,
        """    # ближайший по времени H4-блок к моменту H1-блока
    h4 = min(h4_bloki, key=lambda b: abs(b["импульсный_бар_индекс"]
                                        - h1_blok["импульсный_бар_индекс"]))""",
        """    # ПРАВКА 01.08: раньше "ближайший" H4-блок искался по разнице
    # ИНДЕКСОВ БАРОВ разных таймфреймов — индекс H4 против индекса
    # H1. Это разные линейки (один бар H4 = четыре бара H1), выбор
    # получался случайным. И искался в обе стороны, то есть блок H1
    # мог классифицироваться по блоку H4 из БУДУЩЕГО. Теперь:
    # сравниваем даты и берём последний блок H4, сформированный ДО.
    data_h1 = h1_blok.get("импульсный_бар_дата", "")
    proshlye = [b for b in h4_bloki
                if b.get("импульсный_бар_дата", "") <= data_h1]
    if not proshlye:
        return None
    h4 = max(proshlye, key=lambda b: b.get("импульсный_бар_дата", ""))""",
    ),
]


# ═══════════════════════════════════════════════════════════
# ПРАВКИ ПРОГОНА
# ═══════════════════════════════════════════════════════════

BACKTEST_PRAVKI = [
    # ── 5. _proiti_do_iskhoda: спред на выходе из шорта ────
    (
        1,
        """def _proiti_do_iskhoda(bars_m5: list[dict], sdelka: dict,
                       target: Optional[float] = None,
                       trailing_pivoty: Optional[list] = None,
                       max_hold_barov: int = 288) -> float:""",
        """def _proiti_do_iskhoda(bars_m5: list[dict], sdelka: dict,
                       target: Optional[float] = None,
                       trailing_pivoty: Optional[list] = None,
                       max_hold_barov: int = 288,
                       spred: float = 0.0) -> float:""",
    ),
    (
        1,
        """        if long:
            if b["low"] <= tekushchiy_stop:
                return (tekushchiy_stop - entry) / r
            if target is not None and b["high"] >= target:
                return (target - entry) / r
        else:
            if b["high"] >= tekushchiy_stop:
                return (entry - tekushchiy_stop) / r
            if target is not None and b["low"] <= target:
                return (entry - target) / r""",
        """        if long:
            # лонг посчитан верно и раньше: вход был по ask
            # (open + спред), выход по bid — ровно один спред за
            # круг, как в жизни.
            if b["low"] <= tekushchiy_stop:
                return (tekushchiy_stop - entry) / r
            if target is not None and b["high"] >= target:
                return (target - entry) / r
        else:
            # ПРАВКА 01.08: бары MT5 — это BID. Закрытие шорта — это
            # ПОКУПКА, она идёт по ASK = bid + спред. Раньше выход
            # шорта считался по bid: каждая короткая сделка получала
            # спред бесплатно, а её стоп срабатывал позже, чем
            # сработал бы в терминале.
            if b["high"] + spred >= tekushchiy_stop:
                return (entry - tekushchiy_stop) / r
            if target is not None and b["low"] + spred <= target:
                return (entry - target) / r""",
    ),
    (
        1,
        """    posl = bars_m5[predel - 1]["close"]
    return ((posl - entry) / r) if long else ((entry - posl) / r)""",
        """    posl = bars_m5[predel - 1]["close"]
    return ((posl - entry) / r) if long else ((entry - (posl + spred)) / r)""",
    ),
    # ── 6. трейлинг: пивот ещё не известен ─────────────────
    (
        1,
        """            while piv_idx < len(trailing_pivoty) and trailing_pivoty[piv_idx]["bar_index"] < i:""",
        """            # ПРАВКА 01.08: пивот с lookback=2 становится ИЗВЕСТЕН
            # только через 2 бара после своей вершины — раньше него
            # его просто ещё нет на графике. Стоп двигался уже на
            # следующем баре, то есть по будущему.
            while piv_idx < len(trailing_pivoty) and trailing_pivoty[piv_idx]["bar_index"] + 2 < i:""",
    ),
    # ── 7. вариант Б убран (цель из будущего) ──────────────
    (
        1,
        """    rezultaty: dict = {
        "1R": [], "1.5R": [], "2R": [], "Б_противоположный_ТИУ": [], "В_трейлинг": [],
    }""",
        """    # ПРАВКА 01.08: вариант "Б — противоположный ТИУ" убран целиком.
    # Целью брался уровень из списка ТИУ, посчитанного по ВСЕЙ
    # истории: сделка 2019 года целилась в уровень, который наберёт
    # свои касания только в 2022-м. Числа этого варианта ничего не
    # значили, и хуже — они выглядели как результат.
    rezultaty: dict = {
        "1R": [], "1.5R": [], "2R": [], "В_трейлинг": [],
    }""",
    ),
    (
        1,
        """        tsel_b = _naiti_protivopolozhnyy_tiu(entry, long, tiu)
        if tsel_b is not None:
            rezultaty["Б_противоположный_ТИУ"].append(
                _proiti_do_iskhoda(bars_m5, sdelka, target=tsel_b))

""",
        "",
    ),
    # ── 8. спред доезжает до всех прогонов ─────────────────
    (
        3,
        """            rezultaty[imya].append(_proiti_do_iskhoda(bars_m5, sdelka, target=target))""",
        """            rezultaty[imya].append(_proiti_do_iskhoda(
                bars_m5, sdelka, target=target, spred=spred_pipsov * point))""",
    ),
    (
        3,
        """        rezultaty["В_трейлинг"].append(
            _proiti_do_iskhoda(bars_m5, sdelka, target=None, trailing_pivoty=pivoty_m5))""",
        """        rezultaty["В_трейлинг"].append(
            _proiti_do_iskhoda(bars_m5, sdelka, target=None,
                               trailing_pivoty=pivoty_m5,
                               spred=spred_pipsov * point))""",
    ),
    (
        1,
        """        pnl.append(_proiti_do_iskhoda(bars_m5, sdelka, target=sdelka["target"],
                                     max_hold_barov=max_hold_barov))""",
        """        pnl.append(_proiti_do_iskhoda(bars_m5, sdelka, target=sdelka["target"],
                                     max_hold_barov=max_hold_barov,
                                     spred=spred_pipsov * point))""",
    ),
    # ── 9. тренд H4 на момент каждого блока, не на конец ───
    (
        1,
        """    trend4 = h4_trend_seychas(bars_h4)
    pivoty_m5 = detect_pivots(bars_m5, lookback=2)

    # классифицируем каждый H1-блок один раз, сортируем по времени —
    # это и есть "события смены направления дня", честная замена ЗК
    sobytiya = []
    for hb in h1_bloki:
        kl = klassifitsirovat_blok_h1(hb, h4_bloki, atr_h4, trend4)
        if kl is not None:
            sobytiya.append((bars_h1[hb["импульсный_бар_индекс"]]["date"], kl))
    sobytiya.sort(key=lambda x: x[0])""",
        """    pivoty_m5 = detect_pivots(bars_m5, lookback=2)

    # ПРАВКА 01.08: раньше тут стояло trend4 = h4_trend_seychas(bars_h4)
    # — ОДИН раз, по последнему бару всей истории, и это одно значение
    # раздавалось всем блокам за все годы. То есть у каждого
    # коррекционного блока в истории была одна и та же сторона входа,
    # выбранная по цене конца выборки. Это был не тест гипотезы.
    daty_h4 = [b["date"] for b in bars_h4]

    def _h4_indeks_na(data: str) -> Optional[int]:
        \"\"\"Последний бар H4, закрывшийся не позже указанного момента.\"\"\"
        levo, pravo, otvet = 0, len(daty_h4) - 1, None
        while levo <= pravo:
            seredina = (levo + pravo) // 2
            if daty_h4[seredina] <= data:
                otvet = seredina
                levo = seredina + 1
            else:
                pravo = seredina - 1
        return otvet

    # классифицируем каждый H1-блок один раз, сортируем по времени —
    # это и есть "события смены направления дня", честная замена ЗК
    sobytiya = []
    for hb in h1_bloki:
        # ПРАВКА 01.08: событие датируется баром ПОДТВЕРЖДЕНИЯ блока
        # (импульс + закрепление), а не баром импульса. Блок до
        # закрепления ещё не блок — раньше направление применялось
        # на несколько баров H1 раньше, чем становилось известно.
        podtv = hb["импульсный_бар_индекс"] + hb.get("zakreplenie_barov", 2) + 1
        if podtv >= len(bars_h1):
            continue
        data_sob = bars_h1[podtv]["date"]
        i4 = _h4_indeks_na(data_sob)
        if i4 is None:
            continue
        trend4 = h4_trend_seychas(bars_h4, do_indeksa=i4)
        kl = klassifitsirovat_blok_h1(hb, h4_bloki, atr_h4, trend4)
        if kl is not None:
            sobytiya.append((data_sob, kl))
    sobytiya.sort(key=lambda x: x[0])""",
    ),
    # ── 10. то же датирование в тренд-последовательности ───
    (
        1,
        """    sobytiya = sorted(
        [(bars_h1[hb["импульсный_бар_индекс"]]["date"], hb["полярность"])
         for hb in h1_bloki],
        key=lambda x: x[0])""",
        """    # ПРАВКА 01.08: датируем событие баром ПОДТВЕРЖДЕНИЯ блока
    # (импульс + закрепление), а не баром импульса — до закрепления
    # блока ещё нет, и знать его направление неоткуда.
    sobytiya = []
    for hb in h1_bloki:
        podtv = hb["импульсный_бар_индекс"] + hb.get("zakreplenie_barov", 2) + 1
        if podtv >= len(bars_h1):
            continue
        sobytiya.append((bars_h1[podtv]["date"], hb["полярность"]))
    sobytiya.sort(key=lambda x: x[0])""",
    ),
]


# ═══════════════════════════════════════════════════════════
# МЕХАНИКА
# ═══════════════════════════════════════════════════════════

def primenit(path: Path, pravki: list, marker_kommentariy: str) -> bool:
    if not path.exists():
        print(f"  ✗ не нашёл файл: {path}")
        return False

    tekst = path.read_text(encoding="utf-8")

    if MARKER in tekst:
        print(f"  · {path.name}: уже пропатчен, пропускаю")
        return True

    # сухая проверка ВСЕХ якорей до единой правки — либо все, либо ни одной
    problemy = []
    for ozhidaemo, staroe, _novoe in pravki:
        naideno = tekst.count(staroe)
        if naideno != ozhidaemo:
            problemy.append(f"якорь встретился {naideno} раз вместо {ozhidaemo}: "
                            f"{staroe.strip().splitlines()[0][:70]}")
    if problemy:
        print(f"  ✗ {path.name}: файл не тот, что я читал. Ничего не тронул.")
        for p in problemy:
            print(f"      {p}")
        return False

    for _ozhidaemo, staroe, novoe in pravki:
        tekst = tekst.replace(staroe, novoe)

    tekst = tekst.rstrip("\n") + f"\n# {MARKER} — {marker_kommentariy}\n"

    try:
        ast.parse(tekst)
    except SyntaxError as e:
        print(f"  ✗ {path.name}: после правок ломается синтаксис ({e}). Не пишу.")
        return False

    bak = path.with_suffix(path.suffix + ".bak_chestnost")
    if not bak.exists():
        shutil.copy2(path, bak)
    path.write_text(tekst, encoding="utf-8")
    print(f"  ✓ {path.name}: {len(pravki)} правок, бэкап {bak.name}")
    return True


def main():
    print("\nПАТЧ ЧЕСТНОСТИ СНАЙПЕРА · тела вместо теней, спред, будущее\n")

    if not BIRZHA.exists():
        print(f"Не нашёл папку Биржа рядом со скриптом ({BIRZHA}).")
        print("Запускать из КОРНЯ острова: python patch_sniper_chestnost.py")
        sys.exit(1)

    ok = True
    ok &= primenit(CORE, CORE_PRAVKI, "границы по телам + тренд/блок H4 только из прошлого")
    ok &= primenit(BACKTEST, BACKTEST_PRAVKI, "спред на выходе шорта, убран вариант Б, убраны заглядывания вперёд")

    if not ok:
        print("\nЧто-то не легло — смотри выше. Файлы либо не тронуты, либо восстанавливай из .bak_chestnost.")
        sys.exit(1)

    print("\nГотово. Дальше — перегнать заново ВСЕ прошлые прогоны:")
    print("  python run_backtest.py       EURUSDH1.csv EURUSDM5.csv")
    print("  python run_backtest_trend.py EURUSDH1.csv EURUSDM5.csv")
    print("  python run_backtest_bpz.py   EURUSDM5.csv")
    print("  python run_backtest_blok.py  EURUSDH1.csv EURUSDH4.csv EURUSDM5.csv")
    print("\nСтарые цифры (PF 0.89 / 0.98 / 1.04 и прочие) с этого момента")
    print("недействительны — они считались по теням и по будущему.\n")


if __name__ == "__main__":
    main()
