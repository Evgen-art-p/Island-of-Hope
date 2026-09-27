# -*- coding: utf-8 -*-
# ISKATEL_V1
"""
ИСКАТЕЛЬ КАНДИДАТОВ — код находит поводы, трейдер выбирает.

ЗАКОН ЭТОГО ФАЙЛА
    Здесь нет ни одного суждения о рынке. Кандидат — это МЕСТО, где
    формально сложились три факта, и ничего больше:

        · есть разворотный бар;
        · читается волновая структура;
        · известна её длина в барах.

    Ни «хороший вход», ни «сигнал», ни «подтверждено». Слово Шефа:
    «трейдерам никакой код не должен говорить, что делать, а только
    факты-математику, а трейдер по этой математике судит».

    КАНОН_ВХОДА.md §1②: величина зигзага не принципиальна — какой
    нашли на снимке, тот и работаем. Значит от кода не требуется
    попасть в «настоящую» пятую волну. Требуется не пропустить место,
    на которое стоит взглянуть.

ЦЕНА
    Ноль. Это чистая математика по барам: 1500 баров — 3.4 секунды.
    Платим только когда по найденному месту зовём трейдера.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

OKNO_RASCHYOTA = 300      # сколько баров нужно математике для расчёта

# ── OKNO_ISKATELYA_V1: на каком масштабе вообще стоит звать ──
# Слова Шефа: «раскладываешь эту волну на 100-140, она может быть
# немного меньше или больше, но точность не главное». Волна короче —
# разворотный бар не разглядеть; длиннее — AO посчитан не под неё, и
# дивергенция говорит о другой волне.
#
# Считано, а не придумано: на 3000 барах H4 (≈2 года) кандидатов 79,
# из них в окне 100-140 — 31 (39%), в рамке 80-180 — 58 (73%).
# Поток фильтр не осушает.
#
# Рамка здесь ЯВНАЯ и меняется одной строкой — если решишь, что она
# узка, поправь тут, а не по коду.
OKNO_VOLNY = (100, 140)


def v_okne(dlina) -> bool:
    """Ложится ли волна в рамку. Длина неизвестна — не наше дело
    решать за трейдера: считаем, что не ложится, и не зовём."""
    if not dlina:
        return False
    return OKNO_VOLNY[0] <= dlina <= OKNO_VOLNY[1]


def _dobrat_kompas(k: dict, bars: list, symbol: str, tf: str, point: float):
    """KOMPAS_MESTA_IZ_VODY_V1: компас месту — ОТТУДА ЖЕ, откуда его
    берёт трейдер: из ВОДЫ, по структуре двух старших этажей.

    Раньше здесь стоял компас РАБОЧЕГО этажа (веер Аллигатора,
    md["global_bias"]) — та самая подмена, что была вычищена из
    стола как тихое враньё. Из стола убрали, а в местах осталась;
    и с тех пор, как веер перестал быть источником компаса,
    global_bias никем не заполняется — в месте лежала пустота.

    Спрашиваем воду НА ДАТУ ЭТОГО МЕСТА: она обрезает старшие бары
    по ней и в будущее не заглядывает — закон тестера цел.

    Это запись ДЛЯ ОТЧЁТА. На стол трейдера и на его решения не
    влияет ничем.
    """
    try:
        from global_anchor import global_trend
        st = global_trend(symbol, tf, as_of_date=k.get("дата"))
        b = (st or {}).get("bias")
        k["компас"] = b if b in ("BULL", "BEAR") else None
        _why = (st or {}).get("why") or ""
        if _why:
            k["вода_почему"] = _why
        return k
    except Exception as e:
        print(f"[ИСКАТЕЛЬ] вода месту не ответила ({e}) — "
              f"беру рабочий этаж")
    # Запасной путь — как было раньше.
    try:
        from williams_core import build_market_data
        md = build_market_data(bars, symbol=symbol, timeframe=tf,
                               point=point, starshiy=True)
        if md and md.get("global_bias"):
            k["компас"] = md.get("global_bias")
    except Exception as e:
        print(f"[ИСКАТЕЛЬ] компас месту не досчитан ({e}) — не беда")
    return k


def _priznaki(bars: list, symbol: str, tf: str, point: float):
    """Факты последнего бара окна. Не кандидат — не None.

    ISKATEL_SVOY_ETAZH_V1: ищем на СВОЁМ, рабочем этаже. Разворотный
    бар и структура считаются здесь же, старший этаж для поиска не
    нужен — и не спрашивается (слово Шефа 20.08).
    """
    from williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=tf, point=point,
                           starshiy=False)
    if not md:
        return None
    wf = md.get("wave_form") or {}
    if not wf.get("bdb_dir"):
        return None
    if not wf.get("struktura_chitaetsya"):
        return None
    rb = md.get("rubber_band") or {}
    # Момент, в который город должен встать, чтобы УВИДЕТЬ этот бар.
    # Дата бара — это его НАЧАЛО; к этой секунде он ещё не закрыт, и
    # кран его честно прячет (иначе показывал бы будущее). Поэтому
    # момент = конец бара, иначе трейдер встаёт на бар раньше и
    # самого разворотного бара не видит.
    _data = bars[-1].get("date", "")
    _moment = _data
    try:
        import masshtab
        from datetime import timedelta
        import istoriya
        _t0 = istoriya.kak_vremya(_data)
        _m = masshtab.minut(tf)
        if _t0 is not None and _m:
            _moment = (_t0 + timedelta(minutes=_m)).strftime(istoriya.FORMAT)
    except Exception:
        pass
    return {
        "дата": _data,
        "момент": _moment,
        "разворотный": wf.get("bdb_dir"),
        "цена_разворотного": wf.get("bdb_price"),
        "длина_волны": wf.get("dlina"),
        "дивергенция_в_волне": wf.get("divergence_dir"),
        "дивергенция_AO": md.get("divergence_ao"),
        "отрыв_цены": rb.get("distance_now"),
        "доля_натяжения": rb.get("tension_ratio"),
        "компас": md.get("global_bias"),
        "цена": (md.get("price") or {}).get("close"),
    }


def est_seychas(symbol: str, tf: str):
    """Кандидат ли ТЕКУЩИЙ бар (по тому, что отдаёт кран).

    Это же — ключ пробуждения в реале: пришла свеча, спросили, есть
    ли повод. Нет — никого не будим и ничего не платим.
    """
    import feed_source as fs
    b, point = fs.bars(symbol, tf, OKNO_RASCHYOTA)
    if not b or point is None:
        return None
    return _priznaki(b, symbol, tf, point)


def iskat(symbol: str, tf: str, do_momenta: str = "", skolko: int = 10,
          s_momenta: str = "",   # POISK_S_DATY_V1: идти ВПЕРЁД от даты
          predel_barov: int = 4000, otstup: int = 12, govorit=None,
          tolko_v_okne: bool = True):
    """Пробежать историю НАЗАД от точки и набрать кандидатов.

    do_momenta — откуда начинать искать (пусто = с конца истории).
    skolko     — сколько набрать и остановиться.
    predel_barov — насколько глубоко копать, чтобы не молотить зря.
    otstup     — сколько баров считать ОДНИМ местом.

    Про отступ. Признаки держатся несколько баров подряд, и без
    склейки список выглядит так:

        2026.05.27 16:00 · волна 93 баров
        2026.05.27 08:00 · волна 91 баров
        2026.05.27 04:00 · волна 90 баров

    Это одно место, а не три: та же волна, тот же разворот. Двенадцать
    таких «кандидатов» оказались бы тремя настоящими. Поэтому соседей
    ближе отступа считаем одним местом и берём самый свежий из них —
    тот, на котором картина уже сложилась целиком.

    Возвращает список кандидатов, СВЕЖИЕ ПЕРВЫМИ.
    """
    import istoriya
    vse = istoriya._vse_bary(symbol, tf)
    if not vse:
        return []
    import feed_source as fs
    point = fs._test_point(symbol)

    konec = len(vse) - 1
    if do_momenta:
        konec = -1
        for j, b in enumerate(vse):
            if b.get("date", "") <= do_momenta:
                konec = j
            else:
                break
        if konec < 0:
            return []

    # POISK_S_DATY_V1: слово Шефа — «чтобы начинался С даты, а не ДО».
    # Поле в кабинете называлось «с даты», а ход шёл назад: нужное
    # место оказывалось последним, а четыре взгляда уходили на дорогу.
    # Теперь второй способ ходить — вперёд, в том порядке, в каком всё
    # и случалось: точка, её волна, откат.
    _vperyod = bool(s_momenta)
    if _vperyod:
        nachalo_i = None
        for j, b in enumerate(vse):
            if b.get("date", "") >= s_momenta:
                nachalo_i = j
                break
        if nachalo_i is None:
            return []
        nachalo_i = max(OKNO_RASCHYOTA, nachalo_i)
        konec_i = min(len(vse) - 1, nachalo_i + predel_barov)
        hod = range(nachalo_i, konec_i + 1)
    else:
        hod = None

    nayden = []
    mimo = 0                       # OKNO_ISKATELYA_V1: прошли мимо рамки
    _mimo_trenda = 0               # POISK_PO_TRENDU_V1
    posledniy_i = None
    nachalo = max(OKNO_RASCHYOTA, konec - predel_barov)
    # POISK_S_DATY_V1: вперёд или назад — дальше всё одинаково.
    for i in (hod if _vperyod else range(konec, nachalo - 1, -1)):
        if posledniy_i is not None and abs(posledniy_i - i) < otstup:
            continue
        okno = vse[max(0, i - OKNO_RASCHYOTA + 1):i + 1]
        if len(okno) < OKNO_RASCHYOTA // 2:
            break
        p = _priznaki(okno, symbol, tf, point)
        if p:
            _dobrat_kompas(p, okno, symbol, tf, point)   # ISKATEL_SVOY_ETAZH_V1
            # POISK_PO_TRENDU_V1: место против старшего тренда — мимо.
            # Трейдер пятнадцать раз подряд отказывал словами «это
            # против направления», и был прав: 57% точек смотрели
            # против дневного Аллигатора. Канон: не торговать
            # разворотный бар против тренда в сильном тренде. Котин:
            # «интересует, куда направлен ДНЕВНОЙ Аллигатор».
            # Старшего этажа нет — место годится: из-за нехватки данных
            # ничего не отсекаем.
            # VODA_NA_STOLE_V1: ВОРОТ БОЛЬШЕ НЕТ. Раньше место против
            # старшего тренда выбрасывалось — код решал за трейдера,
            # входить или нет. Слово Шефа: вода это факт на столе, а не
            # разрешение. Место отдаётся как есть, вода кладётся рядом
            # отдельным полем; решает человек — он и рискует своим стопом.
            _komp = p.get("компас")
            p["вода"] = _komp
            if _komp in ("BULL", "BEAR") and _komp != p.get("разворотный"):
                _mimo_trenda += 1
        if p:
            posledniy_i = i
            # OKNO_ISKATELYA_V1: зовём только там, где масштаб годится.
            # Мимо — считаем и идём дальше: место не потеряно, просто
            # смотреть на нём нечего, и платить за это незачем.
            if tolko_v_okne and not v_okne(p.get("длина_волны")):
                mimo += 1
                continue
            nayden.append(p)
            if govorit:
                govorit(f"[ИСКАТЕЛЬ] · {p['дата']} · {p['разворотный']} · "
                        f"волна {p['длина_волны']} баров")
            if len(nayden) >= skolko:
                break
    # OKNO_ISKATELYA_V1: отсеянные не пропадают молча — иначе однажды
    # фильтр съест всё, а мы будем гадать, почему пусто.
    # POISK_PO_TRENDU_V1: отсев по старшей воде тоже вслух.
    if _mimo_trenda:
        _skazat = govorit or print
        _skazat(f"[ИСКАТЕЛЬ] против воды: {_mimo_trenda} мест — "
                f"отданы трейдеру как есть, судит он")
    if mimo and govorit:
        govorit(f"[ИСКАТЕЛЬ] мимо рамки {OKNO_VOLNY[0]}-{OKNO_VOLNY[1]} "
                f"баров: {mimo} мест — там масштаб не тот")
    elif mimo:
        print(f"[ИСКАТЕЛЬ] мимо рамки {OKNO_VOLNY[0]}-{OKNO_VOLNY[1]}: "
              f"{mimo} мест")
    return nayden


def slovami(k: dict) -> str:
    """Кандидат одной строкой — для ленты кабинета."""
    if not k:
        return ""
    return (f"{k.get('дата')} · разворотный {k.get('разворотный')} @ "
            f"{k.get('цена_разворотного')} · волна {k.get('длина_волны')} "
            f"баров · компас {k.get('компас')}")


if __name__ == "__main__":
    import hooks
    a = _sys.argv[1:]
    if len(a) < 2:
        print("py kandidaty.py XAUUSD H4 [сколько]")
        raise SystemExit(1)
    hooks.postavit_ceh("торговый_хаос")
    n = int(a[2]) if len(a) > 2 else 10
    spisok = iskat(a[0].upper(), a[1].upper(), skolko=n, govorit=print)
    print(f"\nнашёл {len(spisok)} кандидатов (свежие первыми):")
    for k in spisok:
        print("  " + slovami(k))

# ISKATEL_V1 - marker

# OKNO_ISKATELYA_V1 - marker

# ISKATEL_SVOY_ETAZH_V1 - marker

# POISK_PO_TRENDU_V1 - marker

# POISK_S_DATY_V1 - marker

# VODA_NA_STOLE_V1 - marker
