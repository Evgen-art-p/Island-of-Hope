
# -*- coding: utf-8 -*-
# VODA_NA_STOLE_V1
"""
ВОДА — ФАКТ НА СТОЛЕ, НЕ ВОРОТА.

Слово Шефа (26.08): точка на H4 рождается только от собственной
структуры H4. Вода её не разрешает и не запрещает — она ложится рядом
ОТДЕЛЬНОЙ СТРОКОЙ. Трейдер видит оба факта и решает сам, в том числе
войти против воды, со своим стопом.

Этот файл считает воду так, чтобы она была действительностью, а не
выдумкой.

КАК СЧИТАЕТСЯ
    · Структура этажа — две последние вершины и две последние впадины
      (обычный фрактал, 2 бара с каждой стороны — тот же detect_fractals,
      что уже есть в ядре).
      Обе выше предыдущих — бык. Обе ниже — медведь.
    · Разнобой НЕ ГАСИТ воду: она держится прежней стороной, пока её не
      сломает новый подтверждённый экстремум с обеих сторон.
    · Тот же счёт повторяется этажом выше — для подтверждения.
    · Вода на столе есть ТОЛЬКО когда оба этажа смотрят в одну сторону.
      Иначе на столе стоит «воды нет» — а не выдуманное направление.

ЛЕСЕНКА (месяц выкинут, выше недельки не лезем)
    H4 → дневка + неделька
    H1 → H4 + дневка

ПОЧЕМУ НЕ ВЕЕР АЛЛИГАТОРА
    Веер соврал на откате в 43% случаев — такой факт трейдеру на стол
    класть нельзя. Зигзаг с порогом ATR проверен отдельно: не помог,
    хуже монетки и сам, и в связке. Фрактал-дневка+неделька держит 54%
    против веерных 46% там, где они расходятся — на двух рынках, 16 и
    22 года истории.

ЕСЛИ ЭТАЖА НЕТ В ИСТОЧНИКЕ
    Дневка и неделька СКЛЕИВАЮТСЯ из рабочих баров (день = баров одной
    даты, неделя = баров одной календарной недели). Это те же самые
    котировки, просто сложенные — и на столе так и написано: «склеена».
    Выдуманного направления не появляется ни при каком раскладе.

ПРОВЕРИТЬ РУКАМИ
    py Биржа/voda.py EURUSD H4
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path
from typing import Optional

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

# Лесенка воды. Меняется одной строкой — не по коду.
# KOMPAS_DLYA_D1_V1: дневки в лесенке НЕ БЫЛО — и трейдер на D1
# работал без компаса вовсе. В прогоне 16.09 это была каждая
# строчка лога: «компаса нет, старший этаж W1 не пришёл». Этаж
# был ни при чём: для D1 просто не написали правило.
LESENKA = {
    "D1": ("W1", "MN1"),
    "H4": ("D1", "W1"),
    "H1": ("H4", "D1"),
}

GLUBINA = 400        # сколько баров этажа берём на счёт структуры
GLUBINA_SKLEYKI = 8000   # сколько рабочих баров просить на склейку


# ─────────────────────────────────────────────────────────────
# СТРУКТУРА ЭТАЖА
# ─────────────────────────────────────────────────────────────

def struktura(bars: list) -> tuple:
    """Куда смотрит структура: ("BULL"|"BEAR"|None, словами).

    Идём по подтверждённым фракталам в том порядке, в каком их видел
    рынок. На каждом новом фрактале смотрим две последние вершины и две
    последние впадины: обе выше — бык, обе ниже — медведь, разнобой —
    держим прежнюю сторону.
    """
    if not bars or len(bars) < 12:
        return None, "баров мало"
    try:
        from williams_core import detect_fractals
    except Exception as e:
        return None, f"ядро не подключилось ({e})"

    f = detect_fractals(bars, lookback=2)
    verh = list(f.get("all_up") or [])
    niz = list(f.get("all_down") or [])
    if len(verh) < 2 or len(niz) < 2:
        return None, "вершин или впадин меньше двух"

    # Фрактал подтверждается через 2 бара после своего центра — раньше
    # его на графике нет, и знать о нём мы не имеем права.
    momenty = sorted([(x["bar_index"] + 2, "V") for x in verh]
                     + [(x["bar_index"] + 2, "N") for x in niz])

    storona = None
    for t, _ in momenty:
        v = [x for x in verh if x["bar_index"] + 2 <= t][-2:]
        n = [x for x in niz if x["bar_index"] + 2 <= t][-2:]
        if len(v) < 2 or len(n) < 2:
            continue
        vverh = v[-1]["price"] > v[-2]["price"] and n[-1]["price"] > n[-2]["price"]
        vniz = v[-1]["price"] < v[-2]["price"] and n[-1]["price"] < n[-2]["price"]
        if vverh:
            storona = "BULL"
        elif vniz:
            storona = "BEAR"
        # разнобой — вода держится прежней стороной

    v2, n2 = verh[-2:], niz[-2:]
    slovami = (f"вершины {v2[0]['price']}→{v2[1]['price']}, "
               f"впадины {n2[0]['price']}→{n2[1]['price']}")
    if storona is None:
        return None, "сторона ни разу не сложилась (" + slovami + ")"
    return storona, slovami


# ─────────────────────────────────────────────────────────────
# БАРЫ ЭТАЖА
# ─────────────────────────────────────────────────────────────

def _kak_vremya(s: str):
    from datetime import datetime
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def skleit(bars: list, kuda: str) -> list:
    """Сложить мелкие бары в дневные или недельные.

    Не новая математика: высшая точка группы — high, низшая — low.
    Больше воде ничего и не нужно, она считается по экстремумам.
    """
    kuda = (kuda or "").upper()
    # KOMPAS_DLYA_D1_V1: добавлен MN1 — склейка знала только день
    # и неделю, а месяц теперь тоже бывает нужен как этаж воды.
    if kuda not in ("D1", "W1", "MN1") or not bars:
        return []
    groups: dict = {}
    poryadok = []
    for b in bars:
        t = _kak_vremya(b.get("date", ""))
        if t is None:
            continue
        if kuda == "D1":
            k = (t.year, t.month, t.day)
        elif kuda == "MN1":
            # KOMPAS_DLYA_D1_V1: месяц — год и номер месяца.
            k = (t.year, t.month)
        else:
            iso = t.isocalendar()
            k = (iso[0], iso[1])
        g = groups.get(k)
        if g is None:
            groups[k] = {
                "date": b.get("date", ""), "open": b["open"],
                "high": b["high"], "low": b["low"], "close": b["close"],
                "volume": b.get("volume", 0), "spread": b.get("spread", 0.0),
            }
            poryadok.append(k)
        else:
            g["high"] = max(g["high"], b["high"])
            g["low"] = min(g["low"], b["low"])
            g["close"] = b["close"]
            g["volume"] = (g.get("volume") or 0) + (b.get("volume") or 0)
    return [groups[k] for k in poryadok]


def bary_etazha(symbol: str, tf: str, as_of_date: Optional[str],
                rabochiy_tf: str = "") -> tuple:
    """Бары этажа: (бары, откуда_словами). Пусто — честно пусто."""
    otkuda = tf
    bars = []
    try:
        from feed_source import bars as source_bars
        b, _p = source_bars(symbol, tf, count=GLUBINA * 3)
        bars = list(b or [])
    except Exception:
        bars = []

    # KOMPAS_DLYA_D1_V1: месяц тоже можно склеить, если файла нет.
    if not bars and rabochiy_tf and tf in ("D1", "W1", "MN1"):
        try:
            from feed_source import bars as source_bars
            b, _p = source_bars(symbol, rabochiy_tf, count=GLUBINA_SKLEYKI)
            syrye = list(b or [])
            if as_of_date:
                cut = as_of_date.strip()
                syrye = [x for x in syrye if x.get("date", "") <= cut]
            bars = skleit(syrye, tf)
            otkuda = f"{tf} склеена из {rabochiy_tf}"
        except Exception:
            bars = []

    if as_of_date and bars:
        cut = as_of_date.strip()
        # Дата бара — его НАЧАЛО. Дневка, начавшаяся сегодня утром,
        # содержит весь сегодняшний день, включая то, что ещё не
        # случилось — это и есть заглядывание в будущее. Поэтому у
        # взятых из источника этажей последний бар отбрасываем: он
        # не закрыт. У склеенных этого делать не надо — они собраны
        # только из тех мелких баров, что уже были.
        bars = [x for x in bars if x.get("date", "") <= cut]
        if otkuda == tf and bars:
            bars = bars[:-1]
    if len(bars) > GLUBINA:
        bars = bars[-GLUBINA:]
    return bars, otkuda


def napravlenie(symbol: str, tf: str, as_of_date: Optional[str] = None,
                rabochiy_tf: str = "") -> dict:
    """Структура одного этажа: {"сторона", "почему", "откуда", "баров"}."""
    bars, otkuda = bary_etazha(symbol, tf, as_of_date, rabochiy_tf)
    if not bars:
        return {"сторона": None, "почему": f"{tf} не дал баров",
                "откуда": otkuda, "баров": 0}
    s, why = struktura(bars)
    return {"сторона": s, "почему": why, "откуда": otkuda, "баров": len(bars)}


# ─────────────────────────────────────────────────────────────
# ВОДА НА СТОЛ
# ─────────────────────────────────────────────────────────────

def voda_na_stole(symbol: str, working_tf: str,
                  as_of_date: Optional[str] = None) -> dict:
    """Вода для рабочего этажа. Тот же контракт, что был у якоря:
    {"bias": "BULL"|"BEAR"|"NONE", "senior_tf", "ok", "why", ...}

    bias="NONE" — воды НЕТ. Это честный факт, а не поломка: два этажа
    смотрят в разные стороны, и выдумывать сторону мы не станем.
    """
    tf = (working_tf or "").upper()
    para = LESENKA.get(tf)
    if not para:
        return {"bias": "NONE", "senior_tf": None, "ok": False,
                "why": f"воды для {tf or '?'} нет — лесенка держит только "
                       f"{', '.join(LESENKA)}",
                "вода_этажи": None}

    a, b = para
    ra = napravlenie(symbol, a, as_of_date, rabochiy_tf=tf)
    rb = napravlenie(symbol, b, as_of_date, rabochiy_tf=tf)

    etazhi = (f"{a}: {ra['сторона'] or '—'} ({ra['почему']}) · "
              f"{b}: {rb['сторона'] or '—'} ({rb['почему']})")

    if ra["сторона"] is None or rb["сторона"] is None:
        pusto = a if ra["сторона"] is None else b
        return {"bias": "NONE", "senior_tf": a, "ok": True,
                "why": f"воды нет: {pusto} не сложился",
                "вода_этажи": etazhi, "этажи": (a, b),
                "откуда": (ra["откуда"], rb["откуда"])}

    if ra["сторона"] != rb["сторона"]:
        return {"bias": "NONE", "senior_tf": a, "ok": True,
                "why": f"воды нет: {a} {ra['сторона']}, {b} {rb['сторона']}",
                "вода_этажи": etazhi, "этажи": (a, b),
                "откуда": (ra["откуда"], rb["откуда"])}

    return {"bias": ra["сторона"], "senior_tf": a, "ok": True,
            "why": f"{a} и {b} смотрят в одну сторону",
            "вода_этажи": etazhi, "этажи": (a, b),
            "откуда": (ra["откуда"], rb["откуда"])}


def slovami(v: dict) -> str:
    """Вода одной строкой — для стола и для кабинета."""
    if not v:
        return "ВОДА: не считалась"
    b = v.get("bias")
    if b in ("BULL", "BEAR"):
        return (f"ВОДА: {b}   ({v.get('why')})"
                f"   [{v.get('вода_этажи') or ''}]")
    return f"ВОДА: НЕТ НА СТОЛЕ   ({v.get('why')})   [{v.get('вода_этажи') or ''}]"


if __name__ == "__main__":
    a = _sys.argv[1:]
    if len(a) < 2:
        print("py voda.py EURUSD H4 [YYYY.MM.DD HH:MM]")
        raise SystemExit(1)
    try:
        import hooks
        hooks.postavit_ceh("торговый_хаос")
    except Exception:
        pass
    kogda = a[2] if len(a) > 2 else None
    r = voda_na_stole(a[0].upper(), a[1].upper(), as_of_date=kogda)
    print(slovami(r))

# VODA_NA_STOLE_V1 - marker
