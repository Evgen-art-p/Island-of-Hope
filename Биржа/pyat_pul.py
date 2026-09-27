# -*- coding: utf-8 -*-
"""
pyat_pul.py   ·   MARKER: PYAT_PUL_V1

ВОЛНА В СВОЁМ МАСШТАБЕ И ПЯТЬ ПУЛЬ

Билл, глава 7: прибор всегда меряет какую-то волну Эллиотта, и чтобы
он мерил ИМЕННО ТУ, что тебе нужна, она должна занимать на экране
100-140 баров. Меньше сотни — прибор покажет волну старшего порядка,
больше ста сорока — младшего. Сто-сорок это НАСТРОЙКА МИКРОСКОПА, а
не допуск для входа. Его пример с йеной: от X до Y на часовике 33
бара — мало; те же X и Y на пятнадцатиминутке дают 102 бара — вот
теперь считаем.

Наша прежняя мерка отматывала четыре нуля AO назад от текущего бара.
Это своё окно прибора, а не наша волна: замер 22.08 показал, что её
длина одинакова на всех этажах (71-102 бара везде) — потому что она
меряет не волну, а сама себя.

Здесь мерка другая: берём ОТРЕЗОК от точки ноль до края, подбираем
этаж, на котором он займёт около 120 баров, и судим этот отрезок там.
Проверено на 2024-2026: медиана длины отрезка на подобранном этаже
вышла ровно 120 баров.

ПЯТЬ ПУЛЬ (глава 7). Билл не судит конец волны строгим счётом
пятёрки — он смотрит, сколько признаков сошлось:
    1. дивергенция на осцилляторе
    2. попадание в целевую зону
    3. фрактал на вершине (внизу)
    4. приседающий бар среди трёх крайних
    5. смена направления моментума

Считаем четыре из пяти. Целевую зону НЕ считаем и честно говорим об
этом: для неё нужна разметка подволн 1-2-3-4 внутри волны, а её нет.
Выдумывать число вместо неё нельзя — пуля помечается «нечем считать».

Ничего не гейтит. Отдаёт числа; что они значат, решает трейдер.
"""

from __future__ import annotations

import bisect
from typing import Optional

CEL_BAROV = 120          # середина окна Билла 100-140
RAZGON = 40              # бары слева, чтобы осциллятор успел ожить
MIN_OTREZOK = 20         # короче — судить нечего, так и скажем


# ─────────────────── масштаб: этаж под длину волны ───────────────────

def etazh_dlya_volny(barov: int, rabochiy: str) -> str:
    """Этаж, на котором отрезок длиной barov (в барах рабочего этажа)
    займёт около 120 баров. Возвращает рабочий, если подобрать нечем."""
    try:
        import masshtab
        from rastyanut import podobrat_etazh
        minut = masshtab.minut(rabochiy)
        if not minut or barov <= 0:
            return rabochiy
        tf = podobrat_etazh(barov * minut)
        return tf if masshtab.est(tf) else rabochiy
    except Exception:
        return rabochiy


def _bary_etazha(symbol: str, tf: str, do_daty: str, skolko: int):
    """Бары этажа, закрытые к указанной дате. Уважает курсор истории —
    берём тем же краном, что и весь город, второго источника нет.

    Кран отдаёт ХВОСТ файла. Начало волны может лежать раньше этого
    хвоста — тогда просим длиннее, но не бесконечно: на живом рынке
    каждый лишний бар стоит времени.
    """
    try:
        from feed_source import bars as _bars
    except Exception:
        return [], None
    prosim = max(skolko, 300)
    for _ in range(4):
        try:
            b, p = _bars(symbol, tf, prosim)
        except Exception:
            return [], None
        if not b:
            return [], None
        if b[0].get("date", "") <= do_daty or len(b) < prosim:
            break                      # начало покрыто или файл кончился
        prosim *= 6                    # хвоста не хватило — просим длиннее
    daty = [x.get("date", "") for x in b]
    i = bisect.bisect_right(daty, do_daty)
    return b[:i], p


def merit_volnu(symbol: str, rabochiy_etazh: str, ot_daty: str,
                do_daty: str, storona: str) -> dict:
    """Померить отрезок волны В ЕГО МАСШТАБЕ.

    ot_daty — бар точки ноль, do_daty — текущий бар (край волны).
    storona — BULL/BEAR, направление точки.

    Возвращает:
      {этаж, баров, читается, почему, в_окне}
    Ничего не решает: «читается» — это факт про форму, не разрешение.
    """
    pusto = {"этаж": rabochiy_etazh, "баров": 0, "читается": False,
             "почему": "отрезок не померен", "в_окне": False}
    try:
        import masshtab
        from williams_core import compute_ao_series, sudit_volnovuyu_strukturu
    except Exception as e:
        pusto["почему"] = f"ядро недоступно ({e})"
        return pusto

    # сколько баров рабочего этажа в отрезке — по нему и подбираем
    b_rab, _ = _bary_etazha(symbol, rabochiy_etazh, do_daty, 3000)
    if not b_rab:
        pusto["почему"] = "котировок рабочего этажа не дали"
        return pusto
    daty_rab = [x.get("date", "") for x in b_rab]
    i0r = bisect.bisect_left(daty_rab, ot_daty)
    barov_rab = max(0, len(daty_rab) - 1 - i0r)

    tf = etazh_dlya_volny(barov_rab, rabochiy_etazh)
    nado = CEL_BAROV + RAZGON + 60
    b, _p = _bary_etazha(symbol, tf, do_daty, max(nado, 400))
    if not b:
        pusto["этаж"] = tf
        pusto["почему"] = f"котировок {tf} не дали"
        return pusto

    daty = [x.get("date", "") for x in b]
    i0 = bisect.bisect_left(daty, ot_daty)
    i1 = len(b) - 1
    if i1 - i0 < MIN_OTREZOK:
        return {"этаж": tf, "баров": max(0, i1 - i0), "читается": False,
                "почему": f"отрезок короткий: {max(0, i1 - i0)} бар.",
                "в_окне": False}

    lo = max(0, i0 - RAZGON)
    seg = b[lo:i1 + 1]
    ao = compute_ao_series([x["high"] for x in seg], [x["low"] for x in seg])
    s, e = i0 - lo, len(seg) - 1
    try:
        ok, why = sudit_volnovuyu_strukturu(ao, s, e, storona)
    except Exception as ex:
        return {"этаж": tf, "баров": e - s, "читается": False,
                "почему": f"суд не сработал ({ex})", "в_окне": False}

    dlina = e - s
    return {"этаж": tf, "баров": dlina, "читается": bool(ok),
            "почему": str(why), "в_окне": 100 <= dlina <= 140}


# ─────────────────────────── пять пуль ───────────────────────────

def _fraktal_na_krayu(md: dict, storona: str) -> Optional[bool]:
    """Фрактал на вершине (для BULL-точки вершина вверху) среди
    последних баров. None — фракталов вовсе нет, считать нечем."""
    fr = (md or {}).get("fractals") or {}
    kray = fr.get("last_up") if storona == "BULL" else fr.get("last_down")
    if not kray:
        return False
    vsego = (md or {}).get("bars_total") or 0
    i = kray.get("bar_index")
    if i is None or not vsego:
        return None
    return (vsego - 1 - i) <= 5


def _prisedayushchiy_ryadom(md: dict) -> Optional[bool]:
    """Приседающий бар — один из трёх крайних (слово Билла: «один из
    трёх наивысших/низших»). Нет данных о приседающих — None."""
    sq = ((md or {}).get("squat") or {}).get("last_squat")
    if not sq:
        return False
    vsego = (md or {}).get("bars_total") or 0
    i = sq.get("bar_index")
    if i is None or not vsego:
        return None
    return (vsego - 1 - i) <= 3


def _moment_razvernulsya(md: dict, storona: str) -> Optional[bool]:
    """Смена направления моментума ПРОТИВ стороны точки: волна
    выдыхается. AO не отдал направление — None."""
    ao = (md or {}).get("ao") or {}
    napr = ao.get("direction")
    if napr not in ("UP", "DOWN"):
        return None
    return napr == ("DOWN" if storona == "BULL" else "UP")


def pyat_pul(md: dict, storona: str) -> dict:
    """Сколько признаков конца волны сошлось. Ничего не решает.

    Каждая пуля: True (есть), False (нет) или None (нечем считать).
    None в счёт НЕ идёт ни в числитель, ни в знаменатель — иначе
    отсутствие прибора выглядело бы как отсутствие признака.
    """
    puli = {
        "дивергенция": bool((md or {}).get("divergence_ao")),
        "целевая_зона": None,      # нужна разметка подволн — её нет
        "фрактал_на_краю": _fraktal_na_krayu(md, storona),
        "приседающий": _prisedayushchiy_ryadom(md),
        "моментум_развернулся": _moment_razvernulsya(md, storona),
    }
    schitaem = [v for v in puli.values() if v is not None]
    return {
        "пули": puli,
        "сошлось": sum(1 for v in schitaem if v),
        "посчитано": len(schitaem),
        "не_считаем": [k for k, v in puli.items() if v is None],
    }


# ──────────────────── глубина отката (главa 7) ────────────────────
# Волна 2 обычно откатывает на 38-62% от волны 1 — три случая из
# четырёх; глубже 62% только один из шести. Число, а не приговор:
# трейдер сам смотрит, дошёл ли откат до своей зоны.

def glubina_otkata(tochka: float, kray: float, seychas: float) -> dict:
    """Насколько откат съел волну 1, в процентах."""
    try:
        volna = abs(float(kray) - float(tochka))
        if volna <= 0:
            return {"процент": None, "зона": "волны нет"}
        dolya = abs(float(kray) - float(seychas)) / volna * 100.0
    except Exception:
        return {"процент": None, "зона": "не посчиталось"}
    # UROVEN_SLOMA_V1: зоны — про цену риска, не про жизнь волны.
    # Слово Шефа: слом это ПРОБОЙ экстремума, а не процент. Волна 1
    # умеет откатывать очень глубоко и рисовать двойное дно — конец
    # отката на уровне точки ноль. Прежняя формулировка «за точку —
    # волна под вопросом» создавала третье состояние, которого не
    # бывает: за точкой волна не под вопросом, она сломана, и точка к
    # тому мигу уже погашена.
    if dolya < 38:
        zona = "мелко (до 38%)"
    elif dolya <= 62:
        zona = "обычная зона 38-62%"
    elif dolya <= 95:
        zona = "глубоко (больше 62%) — дороже, но волна жива"
    else:
        zona = ("почти вся волна — возможно двойное дно; "
                "волна жива до пробоя точки")
    return {"процент": round(dolya, 1), "зона": zona}


def slovami(izmerenie: dict, puli: dict) -> str:
    """Одной строкой для стола."""
    m = izmerenie or {}
    p = puli or {}
    okno = "в окне 100-140" if m.get("в_окне") else "мимо окна"
    s = (f"волна на {m.get('этаж','?')}: {m.get('баров',0)} бар. ({okno})"
         f"   пятёрка: {'читается' if m.get('читается') else 'нет'}"
         f" — {m.get('почему','')}")
    if p:
        s += (f"   пули: {p.get('сошлось',0)} из {p.get('посчитано',0)}")
        if p.get("не_считаем"):
            s += f" (нечем считать: {', '.join(p['не_считаем'])})"
    return s


# PYAT_PUL_V1 - marker

# UROVEN_SLOMA_V1 - marker
