# -*- coding: utf-8 -*-
# STOL_KODOM_V1
"""
СТОЛ ТРЕЙДЕРА, НАКРЫТЫЙ КОДОМ.

Раньше стол накрывали четыре живых сенсора: Искра клала разворотный
бар, Морж — пасть и натяжение, Паникёр — фазу толпы, Ганс — фрактал.
По решению Шефа (06.08) сенсоры стали математикой и уехали из цеха.
Этот файл делает их работу — без голосов и без вызовов модели.

ГДЕ ОН ЛЕЖИТ И ПОЧЕМУ ЗДЕСЬ
    В папке `Биржа/`, рядом с `williams_core.py` и `grafik.py`.
    Математика НИЧЬЯ: она не принадлежит слоту и не носит характера.
    Слот несёт роль и зовёт математику — так велит канон.

ЧТО ОН ГАРАНТИРУЕТ
    Те же имена полей, что клали сенсоры. Мозг трейдера подмены не
    замечает: читает как читал, только теперь ему не надо ждать,
    пока кто-то проснётся и накроет.

ЧЕГО ОН НАРОЧНО НЕ ДЕЛАЕТ

    Не интерпретирует. Сенсор-голос переводил объём в «жадность» и
    «недоверие» — код так не умеет и не должен: он кладёт ФАКТ
    (GREEN/FADE/FAKE/SQUAT), а что это значит, решает трейдер. Это и
    было решением Шефа: сенсор докладывает, трейдер судит.

    Не спускается по этажам. Спуск был работой Искры-диспетчера; по
    новому порядку направление приходит СВЕРХУ (со старшего этажа), а
    работаем на том, что задан. Никто больше не ищет бар «где-нибудь».

    Не решает за трейдера и не ставит порогов. Ни одного числа,
    которого нет в источниках.

    STOL_BEZ_VYVODOV_V1 (слово Шефа 07.08): «то, что ты посчитал код
    готовый, он не будет работать». И это верно: если код нашёл
    разворотный бар, посчитал согласие с водой и объявил фрактал
    действительным — трейдеру остаётся кивнуть. Выбирать нечего,
    смотреть незачем, и получается бот с характером.

    Поэтому граница проведена так:

      ПОКАЗАНИЕ ПРИБОРА — остаётся. Где стоят линии и в каком они
        порядке, спит пасть или нет, какое значение у гистограммы и
        растёт ли она, где последние фракталы, какое окно объёма,
        какое натяжение, куда смотрит старший Аллигатор.

      ВЫВОД — убран. «Разворотный бар найден», «согласен с водой»,
        «фрактал действителен», «структура читается». Это уже
        суждения, и делать их трейдеру.

    Приборы лежат в ключе «приборы». Старые ключи сенсоров остаются
    пустыми — их читает мозг, и пустота там честная: сенсоров нет.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

_BIRZHA = Path(__file__).resolve().parent

# SPRED_PO_UMOLCHANIYU_V1: сколько пунктов спреда брать, когда в
# истории его нет. Слово Шефа 17.09: «ставь три пункта, ордера
# выше свечи — два спреда, ниже свечи — один спред».
#
# Ноль вместо спреда стоил прогону 54 убытка из 55: стол выдавал
# голые края бара, стоп вставал ровно на край, и обычный ретест
# снимал сделку до того, как она успевала стать правой.
#
# Живой спред из терминала главнее — это только на бесспредовую
# историю. Менять цифру можно прямо здесь.
SPRED_PO_UMOLCHANIYU = 3
if str(_BIRZHA) not in sys.path:
    sys.path.insert(0, str(_BIRZHA))


# ─────────────────────────────────────────────────────────────
# ПУСТОЙ СТОЛ — тот же по форме, что и накрытый
# ─────────────────────────────────────────────────────────────
# Читатель не должен ловить KeyError на холодном старте: пустой стол
# отличается от накрытого значениями, а не набором полей.

def pustoy(self_key: str = "brut") -> dict:
    return {
        "iskra": {"t1_status": "NOT_FOUND", "zero_point_price": None,
                  "trend_direction": None, "dlina": None,
                  "struktura_chitaetsya": False,
                  "compass": None, "soglasie": None,
                  "found_timeframe": None},
        "morj": {"morj_status": "SLEEPING", "wave_1_validated": False,
                 "tension_peak": False, "tension_ratio": None},
        "panic": {"panic_phase": None, "crowd_sentiment": None},
        "hans": {"fractal_valid": False, "fractal_side": None,
                 "fractal_price": None},
        "arkhiv": {},
        "self": {},
        "приборы": {},
    }


def _tochka_nol(md: dict, symbol: str = "", timeframe: str = "") -> dict:
    """TOCHKA_ROZHDAETSYA_V1: точка ноль на стол — КООРДИНАТА, не вывод.

    Разворотный бар выше по столу — это «есть ли он на ЭТОЙ свече».
    Точка — то же самое, но живущее между барами: вот начало, вот
    когда оно было, вот куда цена от него ушла. От неё трейдер и
    смотрит волну 1, как смотрит Шеф глазом.

    Ни «вход здесь», ни «сигнал». Что это значит — решает трейдер.
    """
    try:
        from hooks import load_trading_state, _blok_tochki, _para_tochki
        isk = _blok_tochki(load_trading_state() or {},
                           _para_tochki(symbol, timeframe))
    except Exception:
        return {}
    if not isk.get("alive"):
        return {"жива": False, "сторона": isk.get("trend_direction"),
                "цена": isk.get("zero_point_price")}
    return {
        "жива": True,
        "сторона": isk.get("trend_direction"),
        "цена": isk.get("zero_point_price"),
        "бар_рождения": isk.get("rodilas_na_bare"),
        "баров_назад": isk.get("barov_s_tochki"),
        "край_после_точки": isk.get("kray_posle"),
        # НЕ длина новой волны — её никто знать не может, точка только
        # родилась. Это отмерено НАЗАД: сколько баров заняла структура,
        # которая только что кончилась (4 перехода нуля AO, канон 18.07).
        "структура_позади_баров": isk.get("struktura_pozadi"),
        # VOLNA_NA_STOLE_V1: конец первой волны — координатой, как сама
        # точка. Трейдера будили словами «волна 1 кончилась», а на столе
        # этого не было, и он честно отвечал «первой волны нет».
        "волна_1": (lambda _k: ({
            "кончилась": True,
            "макушка": _k.get("цена"),
            "бар": _k.get("бар"),
            "баров_от_точки": _k.get("баров_от_точки"),
            # NOGI_SCHYOTNYE_V1: которая это нога от точки. Пусто у
            # структур, начатых до патча, — тогда просто первая.
            "нога": _k.get("нога") or 1,
        } if _k else {"кончилась": False}))(isk.get("konec_volny_1") or {}),
        # TRI_POPYTKI_V1: чем входить. Разворотник — он же и мера риска:
        # вход за ним, стоп за ним же. Не совет входить, а цена, которую
        # трейдер и так обязан назвать, чтобы заявку приняли.
        "попыток": int(isk.get("попыток") or 0),
        # KONEC_VOLNY_2_V1: откат — третья координата, рядом с точкой и
        # волной. Трейдер говорил «волна кончилась, но мне нужен откат
        # к ней» — вот он, тем же прибором.
        "волна_2": (lambda _k: ({
            "кончилась": True,
            "цена": _k.get("цена"),
            "бар": _k.get("бар"),
            "баров_от_макушки": _k.get("баров_от_макушки"),
            "нога": _k.get("нога") or 1,   # NOGI_SCHYOTNYE_V1
        } if _k else {"кончилась": False}))(isk.get("konec_volny_2") or {}),
        "попыток": int(isk.get("попыток") or 0),   # TRI_POPYTKI_V1
        "цена_сейчас": ((md or {}).get("price") or {}).get("close"),
    }


def _status_alligatora(al: dict) -> str:
    """Словарь Моржа, слово в слово как он его писал."""
    if al.get("sleeping"):
        return "SLEEPING"
    if al.get("mature"):
        return "MATURE"
    if al.get("opening"):
        return "WAKING"
    return "AWAKE"


# KOMPAS_PRICHINA_V1: про какой расклад воды уже говорили в лог.
# Без этого строчка повторялась бы на каждом баре и утопила бы
# лог так же, как его топят сохранения стола.
_KOMPAS_SKAZANO = set()


def nakryt(symbol: str, timeframe: str,
           md: Optional[dict] = None,
           bars: Optional[list] = None,
           point: Optional[float] = None,
           self_key: str = "brut") -> dict:
    """Накрывает стол по факту рынка. Не падает никогда — в худшем
    случае отдаёт пустой стол той же формы.

    md/bars/point можно передать, если вызывающий их уже посчитал —
    тогда второй раз считать не будем.
    """
    stol = pustoy(self_key)

    # справка Архивариуса и своя обратная связь по ведению остаются
    # с шины: Архивариус живой и кладёт сам, а «self» пишет сам трейдер
    try:
        from hooks import load_trading_state
        t = load_trading_state()
        stol["arkhiv"] = t.get("arkhiv", {}) or {}
        stol["self"] = t.get(self_key, {}) or {}
    except Exception:
        pass

    try:
        if md is None:
            from feed_source import bars as source_bars
            from williams_core import build_market_data
            if bars is None:
                bars, point = source_bars(symbol, timeframe, count=400)
                # TOLKO_ZAKRYTYE_V1: приборы считаем по закрытым барам —
                # идущая свеча пляшет и вместе с ней пляшет разворотник.
                try:
                    from hooks import _tolko_zakrytye
                    bars = _tolko_zakrytye(bars)
                except Exception:
                    pass
            if not bars or len(bars) < 42:
                return stol
            md = build_market_data(bars, symbol=symbol,
                                   timeframe=timeframe, point=point)
        if not md:
            return stol
    except Exception:
        return stol

    al = md.get("alligator", {}) or {}
    nb = md.get("necron_bar", {}) or {}
    rb = md.get("rubber_band", {}) or {}
    wf = md.get("wave_form", {}) or {}
    fr = md.get("fractals", {}) or {}
    mfi = md.get("mfi", {}) or {}

    # ── КОМПАС: направление СО СТАРШЕГО этажа ────────────────
    # Порядок Шефа (04.08): первым идёт большая вода, и берётся она
    # своим инструментом на своём масштабе. Раньше компас наследовал
    # этаж Искры — то есть был эхом сигнала, а не проверкой.
    compass = None
    starshiy_tf = None
    starshiy_prishyol = False
    _voda_etazhi = None       # VODA_NA_STOLE_V1
    _voda_why = ""            # VODA_NA_STOLE_V1
    try:
        from global_anchor import global_trend, senior_timeframe
        starshiy_tf = senior_timeframe(timeframe)
        st = global_trend(symbol, timeframe,
                          as_of_date=(md.get("bar_time")))
        starshiy_prishyol = bool((st or {}).get("ok"))
        b = (st or {}).get("bias")
        compass = b if b in ("BULL", "BEAR") else None
        # VODA_NA_STOLE_V1: чем именно вода такая — целиком на стол
        _voda_etazhi = (st or {}).get("вода_этажи")
        _voda_why = (st or {}).get("why") or ""
    except Exception:
        compass = None
    # KOMPAS_CHESTNYY_V1: раньше здесь стояла ПОДМЕНА — старший этаж
    # не пришёл, и компас брался из md["global_bias"], который считан
    # по РАБОЧЕМУ этажу. А на столе он оставался подписан «старший
    # Аллигатор»: трейдер думал, что видит направление сверху, а видел
    # свой же этаж. Тихое враньё — не падает, не жалуется, выглядит
    # правдой, и на него опирается решение.
    # Теперь: не пришёл — значит нет. Направление рабочего этажа
    # отдаётся отдельной строкой, под своим именем.
    if compass is None and not starshiy_prishyol:
        print(f"[СТОЛ] ⚠️  компаса нет: старший этаж "
              f"{starshiy_tf or '?'} не пришёл")
    else:
        # KOMPAS_PRICHINA_V1: этаж пришёл — значит молчание компаса
        # имеет причину, и она лежит на столе в «вода_почему».
        # Раньше эта причина не выходила наружу: жалобы нет,
        # компаса нет, понять нечем. Теперь видно.
        try:
            _et = ""
            if isinstance(_voda_etazhi, dict):
                _et = ", ".join(f"{k} {v}"
                                for k, v in _voda_etazhi.items())
            elif _voda_etazhi:
                _et = str(_voda_etazhi)
            _rasklad = f"{compass or 'воды нет'} · {_et} · {_voda_why}"
            _klyuch = (symbol, timeframe, _rasklad)
            if _klyuch not in _KOMPAS_SKAZANO:
                _KOMPAS_SKAZANO.add(_klyuch)
                _chto = compass if compass else "воды нет"
                _hvost = _et or _voda_why or "причина не названа"
                print(f"[КОМПАС] {symbol} {timeframe}: "
                      f"{_chto} — {_hvost}")
        except Exception as _e_kp:
            print(f"[КОМПАС] сказать не вышло ({_e_kp}) — не беда")
    svoy_etazh_napravlenie = md.get("global_bias")
    if svoy_etazh_napravlenie not in ("BULL", "BEAR"):
        svoy_etazh_napravlenie = None

    napravlenie = nb.get("direction")

    # STOL_BEZ_VYVODOV_V1: сигнала здесь БОЛЬШЕ НЕТ. Разворотный бар,
    # согласие с водой и «структура читается» были выводами кода —
    # теперь их делает трейдер, глядя на картинку. Остаются компас
    # (показание старшего Аллигатора — факт рынка, а не решение) и
    # этаж, на котором работаем.
    stol["iskra"] = {
        "t1_status": None,
        "trend_direction": None,
        "zero_point_price": None,
        "dlina": None,
        "struktura_chitaetsya": None,
        "compass": compass,
        "soglasie": None,
        "found_timeframe": timeframe,
    }

    stol["morj"] = {
        "morj_status": _status_alligatora(al),   # состояние пасти — факт
        "wave_1_validated": None,                # был вывод, убран
        "tension_peak": bool(rb.get("is_peak")),
        "tension_ratio": rb.get("tension_ratio"),
    }

    stol["panic"] = {
        # ФАКТ окна Вильямса, а не пересказ настроения
        "panic_phase": mfi.get("type"),
        "crowd_sentiment": None,
    }

    # STOL_BEZ_VYVODOV_V1: «действительный фрактал» был выводом — какой
    # из двух годится, решает тот, кто выбрал себе вход. Отдаём ОБА как
    # координаты на графике.
    stol["hans"] = {
        "fractal_valid": None,
        "fractal_side": None,
        "fractal_price": None,
    }

    # ── ПРИБОРЫ: голые показания, без единого суждения ────────
    ao = md.get("ao", {}) or {}
    stol["приборы"] = {
        "старший_аллигатор": compass,          # куда смотрит большая вода
        # VODA_NA_STOLE_V1: вода — ФАКТ рядом с сигналом, не ворота.
        # Считается структурой старших этажей (фрактал: две вершины,
        # две впадины). Нет согласия этажей — нет и воды.
        "вода": compass,
        "вода_этажи": _voda_etazhi,
        "вода_почему": _voda_why,
        # KOMPAS_CHESTNYY_V1: чем именно пуст компас и что говорит
        # рабочий этаж — под своим именем, а не под чужим
        "старший_этаж": starshiy_tf,
        "старший_пришёл": starshiy_prishyol,
        "направление_рабочего": svoy_etazh_napravlenie,
        "этаж": timeframe,
        "аллигатор": {
            "челюсть": al.get("jaw"), "зубы": al.get("teeth"),
            "губы": al.get("lips"),
            "спит": al.get("sleeping"),
            "баров_открыт": al.get("bars_open"),
        },
        "ao": {
            "значение": ao.get("value"), "прошлое": ao.get("prev_value"),
            "растёт": ao.get("direction"),
            "перешёл_ноль": ao.get("crossed_zero"),
        },
        "фракталы": {"вверх": fr.get("last_up"), "вниз": fr.get("last_down")},
        "объём_окно": mfi.get("type"),
        "натяжение": {"сейчас": rb.get("distance_now"),
                      "пик": rb.get("distance_max"),
                      "доля_от_пика": rb.get("tension_ratio"),
                      # REZINKA_CHESTNAYA_V1: сторона названа прямо
                      "цена_по_другую_сторону_губ": rb.get("za_gubami")},
        "цена": md.get("price"),
        "бар": md.get("bar_time"),
        # ZAYAVKA_I_SPRED_V1: имя пары нужно, чтобы спросить спред
        "инструмент": symbol,
        # ALLIG_NA_VHODE_V1: шаг цены — чтобы разброс линий читался в
        # пунктах инструмента, а не в сырых долях. На золоте и на евро
        # одно и то же «0.004» значит совершенно разное.
        "point": md.get("point"),
        # ── PRIBORY_NA_STOL_V1 ───────────────────────────────
        # Всё это ядро считало и раньше — но на стол не выкладывало,
        # и трейдер их не видел. Особенно разворотный бар: его
        # зовут на место ИМЕННО из-за него, а на столе его не было.
        "разворотный_бар": {
            "есть": bool((md.get("necron_bar") or {}).get("direction")),
            "сторона": (md.get("necron_bar") or {}).get("direction"),
            "цена": (md.get("necron_bar") or {}).get("price"),
        },
        # ЗОНА по Вильямсу (iZone из эксперта Шефа): AO и AC вместе.
        # Зелёная — оба растут, красная — оба падают, серая — спорят.
        # TOCHKA_ROZHDAETSYA_V1: начало, которое живёт дольше свечи
        "точка_ноль": _tochka_nol(md, symbol, timeframe),
        # AC_VON_V1: AC и ЗОНА (AO+AC) убраны — скорость городу не нужна
        # UBRAT_STROKU_DIVERGENCII_V1 (14-15.09, Шеф): два судьи в
        # одном поле зрения хуже одного неидеального. Трейдер видит
        # дивер глазами по всей картине (лесенка, а не пара точек) —
        # казённое True/False рядом создаёт ложный спор с собой.
        # Раньше здесь стояли "дивергенция_ao" и "дивергенция_ao_медвежья".
        # PRISEDANIE_PRAVDA_V1: словами, в окне трёх баров.
        "приседающий_бар": _prisedanie(md, bars, timeframe),
    }

    return stol


# AC_VON_V1: функция зоны убрана вместе с AC. Зона по определению
# считалась из AO+AC (iZone.mq4): оба растут — зелёная, оба падают —
# красная. Без AC её посчитать нечем, а показывать цвет, собранный
# из половины прибора, — врать трейдеру.


# PRISEDANIE_PRAVDA_V1 (слово Шефа 23.09): приседающий считается, если
# он в пределах ТРЁХ баров — на самом разворотном баре или не раньше
# чем за два бара до него (разворотник — третий). Один или дорожка —
# всё равно. Раньше здесь стояло bool(last_squat) — «был ли хоть один
# приседающий во всей истории», то есть True всегда, на любом баре.
# TRI_BARA_V2 (слово Шефа 25.09): разворотник и три бара до —
# всего четыре бара в окне.
_PRISED_OKNO = 4


def _prisedanie(md: dict, bars, timeframe: str = "") -> str:
    """Приседающий словами: есть ли в окне трёх баров и где последний."""
    last = ((md or {}).get("squat") or {}).get("last_squat") or {}
    if not last:
        return "нет — на этом этаже ни одного"
    d_last = str(last.get("date") or "")
    nazad = None
    v_okne = []
    if bars:
        try:
            _daty = [str(b.get("date")) for b in bars]
            if d_last in _daty:
                nazad = len(_daty) - 1 - _daty.index(d_last)
            _hvost = bars[-(_PRISED_OKNO + 1):]
            for _k in range(1, len(_hvost)):
                _b, _pb = _hvost[_k], _hvost[_k - 1]
                if not _b.get("volume") or not _pb.get("volume"):
                    continue
                _m = (_b["high"] - _b["low"]) / _b["volume"]
                _pm = (_pb["high"] - _pb["low"]) / _pb["volume"]
                if _b["volume"] > _pb["volume"] and _m < _pm:
                    v_okne.append(len(_hvost) - 1 - _k)
        except Exception:
            nazad = None
    if nazad is None:
        # баров под рукой нет — считаем по часам этажа
        try:
            from datetime import datetime
            _f = "%Y.%m.%d %H:%M"
            _chas = {"M1": 1 / 60, "M5": 5 / 60, "M15": 0.25, "M30": 0.5,
                     "H1": 1, "H4": 4, "D1": 24, "W1": 168}.get(
                str(timeframe or md.get("timeframe") or "H1").upper(), 1)
            from datetime import timedelta
            _t = datetime.strptime(d_last, _f)
            _konec = datetime.strptime(str(md.get("bar_time")), _f)
            _shag = timedelta(hours=_chas)
            nazad = 0
            # выходные не в счёт: в субботу и воскресенье баров нет
            while _t < _konec and nazad < 500:
                _t += _shag
                if _t.weekday() < 5:
                    nazad += 1
        except Exception:
            nazad = None
    kogda = d_last[5:] if len(d_last) >= 16 else d_last
    if nazad is not None and 0 <= nazad < _PRISED_OKNO:
        if len(v_okne) >= 2:
            return (f"есть — дорожка: {len(v_okne)} приседающих за последние "
                    f"{_PRISED_OKNO} бара, последний {kogda}")
        if nazad == 0:
            return "есть — на этом баре"
        # TRI_BARA_PRISED_V1: прямо говорим, что это считается
        return (f"есть — за {nazad} бар(а) до этого бара ({kogda}), "
                f"в окне трёх баров — считается")
    if nazad is None:
        return f"не ясно — последний {kogda}"
    return (f"нет — последний {kogda}, {nazad} бар(ов) назад "
            f"(дальше трёх баров)")


def slovami(stol: dict) -> str:
    """Приборы человеку — для кабинета и для проверки без модели.

    Ни одного вывода: только показания. Что они значат — говорит тот,
    кто смотрит.
    """
    p = stol.get("приборы", {}) or {}
    al = p.get("аллигатор", {}) or {}
    ao = p.get("ao", {}) or {}
    fr = p.get("фракталы", {}) or {}
    nt = p.get("натяжение", {}) or {}
    c = p.get("цена", {}) or {}
    L = [
        _voda_strokoy(p),   # VODA_NA_STOLE_V1
        # ALLIG_NA_VHODE_V1: слова «спит» здесь больше нет. Оно тянуло
        # за собой готовый вывод «боковик, не торгуй» — а на конце
        # отката сомкнутая пасть это норма, там и надо входить.
        # Показываем разброс линий и сколько баров они сомкнуты:
        # число трейдер истолкует сам, ярлык истолковывал за него.
        (lambda _r: (
            f"Аллигатор: челюсть {al.get('челюсть')}  зубы {al.get('зубы')}  "
            f"губы {al.get('губы')}"
            f"   разброс линий: {_r}"
            f"   открыт баров: {al.get('баров_открыт')}"
            + ("   (сомкнуты — на входе это норма, "
               "раскроет сам импульс)" if al.get("спит") else "")))(
            _razbros_linij(al, p)),
        f"AO: {ao.get('значение')} (было {ao.get('прошлое')})   "
        f"растёт: {ao.get('растёт')}   перешёл ноль: {ao.get('перешёл_ноль')}",
        f"фракталы: вверх {(fr.get('вверх') or {}).get('price')}   "
        f"вниз {(fr.get('вниз') or {}).get('price')}",
        f"объём (окно): {p.get('объём_окно') or '—'}",
        # REZINKA_CHESTNAYA_V1: словами, а не знаком минуса. Трейдер
        # читал «−229.2 п., доля −1.732» и спотыкался: доля не бывает
        # −1.7. Теперь сторона названа прямо, а доля показывается
        # только когда она есть. Хватает отрыва или нет — видно на
        # кадре, и решает это трейдер, не прибор.
        (lambda _n: (
            f"расстояние до губ: {abs(_n.get('сейчас') or 0):.0f} п. "
            + ("(цена по другую сторону губ)"
               if _n.get('цена_по_другую_сторону_губ')
               else f"(пик {_n.get('пик')}, доля {_n.get('доля_от_пика')})")
        ))(nt),
        # PRIBORY_NA_STOL_V1: то, ради чего трейдера зовут, — первой
        # строкой, а не в конце и не молчком.
        f"РАЗВОРОТНЫЙ БАР: "
        f"{(p.get('разворотный_бар') or {}).get('сторона') or 'нет'}"
        + (f" @ {(p.get('разворотный_бар') or {}).get('цена')}"
           if (p.get('разворотный_бар') or {}).get('есть') else ""),
        # TOCHKA_ROZHDAETSYA_V1: от начала трейдер и меряет волну 1
        (lambda _t: (
            f"ТОЧКА НОЛЬ: {_t.get('сторона') or '—'} @ {_t.get('цена')}"
            f"   {_t.get('баров_назад')} бар(ов) назад"
            f"   край после точки: {_t.get('край_после_точки')}"
            f"   структура позади: {_t.get('структура_позади_баров')} бар."
            f"   сейчас: {_t.get('цена_сейчас')}"
            if _t.get("жива") else "ТОЧКА НОЛЬ: нет"))(
                p.get("точка_ноль") or {}),
        # VOLNA_NA_STOLE_V1: кончилась первая волна — говорим где,
        # а не молчим. Трейдера будили словами «волна 1 кончилась»,
        # а на столе этого не было, и он честно отвечал «первой
        # волны нет».
        (lambda _v, _t: (
            f"ВОЛНА {_v.get('нога') or 1}: от {_t.get('цена')} → "
            f"{'вершина' if _t.get('сторона') == 'BULL' else 'дно'} "
            f"{_v.get('макушка')}"
            f"   {_v.get('баров_от_точки')} бар(ов) от точки"
            f"   бар {_v.get('бар')}"
            # NOGI_SCHYOTNYE_V1: нога от точки, а не всегда «первая».
            + (f"   нога {_v.get('нога')} от точки"
               if (_v.get('нога') or 1) > 1 else "")
            if _v.get("кончилась")
            else f"ВОЛНА {(_t.get('нога_идёт') or 1)}: ещё идёт"))(
                (p.get("точка_ноль") or {}).get("волна_1") or {},
                p.get("точка_ноль") or {}),
        # VOLNA_V_MASSHTABE_V1: та же волна, померенная в СВОЁМ
        # масштабе, и пять пуль Билла. Не приговор — показания.
        # Целевой зоны среди пуль нет: для неё нужна разметка подволн
        # внутри волны, а её нет. Пустое место честнее выдуманного.
        (lambda _m: (
            f"МАСШТАБ ВОЛНЫ: {_m.get('баров_на_этаже')} бар(ов) на "
            f"{_m.get('этаж_волны')}"
            f"   {'в окне 100-140' if _m.get('в_окне_100_140') else 'мимо окна 100-140'}"
            f"   пятёрка: {'читается' if _m.get('пятёрка') else 'нет'}"
            f" ({_m.get('пятёрка_почему')})"
            f"   ПУЛЬ СОШЛОСЬ: {_m.get('пуль_сошлось')} из "
            f"{_m.get('пуль_посчитано')}"
            f"   {_m.get('пули')}"
            if _m.get("этаж_волны") else
            "МАСШТАБ ВОЛНЫ: волна ещё не кончилась — мерить нечего"))(
                _volna_1_syro(p)),
        # VOLNA_V_MASSHTABE_V1: глубина отката от волны 1. Билл: волна
        # 2 откатывает на 38-62% в трёх случаях из четырёх, глубже 62%
        # — в одном из шести. Число, а не разрешение входить.
        (lambda _t, _v, _c: (
            (lambda _g: f"ГЛУБИНА ОТКАТА: {_g.get('процент')}% — {_g.get('зона')}")(
                __import__("pyat_pul").glubina_otkata(
                    _t.get("цена"), _v.get("макушка"), _c))
            if (_v.get("кончилась") and _t.get("цена") is not None
                and _c is not None)
            else "ГЛУБИНА ОТКАТА: считать не от чего"))(
                p.get("точка_ноль") or {},
                (p.get("точка_ноль") or {}).get("волна_1") or {},
                c.get("close")),
        # UROVEN_SLOMA_V1: где кончается волна. Слово Шефа: слом — это
        # ПРОБОЙ ЭКСТРЕМУМА начала волны 1, а не глубокий процент.
        # Откат может лечь вплотную к точке и нарисовать двойное дно —
        # это нормальная фигура, волна жива. Раньше на столе стояли
        # проценты, но не было САМОЙ ГРАНИЦЫ: 12.02 оба вошли в шорт,
        # не видя, что до слома оставалось меньше двух пунктов.
        _uroven_sloma(p, c),
        # TRI_POPYTKI_V1: вход и стоп — по разворотному бару, и какая
        # это попытка на текущей структуре.
        # ZAYAVKA_I_SPRED_V1: уровни готовыми числами, с обеих сторон.
        # Раньше стояла одна цена и слова «стоп за ним же» — считать
        # приходилось в уме, а в уме легко решить «подожду пробоя».
        (lambda _rb, _t: (
            (_urovni_zayavki(_rb, c, p)
             if _rb.get("есть") else "ВХОД: разворотного бара сейчас нет")
            + ((f"   ·   ПОПЫТКА {int(_t.get('попыток') or 0) + 1}-я "
                f"на этой структуре"
                + ("  — то ли ты делаешь?"
                   if int(_t.get("попыток") or 0) >= 3 else ""))
               if int(_t.get("попыток") or 0) else "")
            # SVOI_SDELKI_VIDNO_V1: чем кончились прошлые попытки —
            # прямо здесь, без запроса в память. Это и есть «видеть
            # свои сделки»: пришёл на структуру — знаешь, что было.
            + _proshlye_popytki(_t)
        ))(p.get("разворотный_бар") or {}, p.get("точка_ноль") or {}),
        # KONEC_VOLNY_2_V1: и откат к ней — если он уже кончился.
        (lambda _o, _t: (
            f"ОТКАТ: кончился @ {_o.get('цена')}"
            f"   {_o.get('баров_от_макушки')} бар(ов) от "
            f"{'вершины' if _t.get('сторона') == 'BULL' else 'дна'}"
            f"   бар {_o.get('бар')}"
            + (f"   нога {_o.get('нога')} от точки"   # NOGI_SCHYOTNYE_V1
               if (_o.get('нога') or 1) > 1 else "")
            if _o.get("кончилась") else "ОТКАТ: идёт"))(
                (p.get("точка_ноль") or {}).get("волна_2") or {},
                p.get("точка_ноль") or {}),
        f"приседающий бар: {p.get('приседающий_бар')}",
        f"цена: O={c.get('open')} H={c.get('high')} L={c.get('low')} "
        f"C={c.get('close')}   бар: {p.get('бар')}",
    ]
    return "\n".join(f"— {x}" for x in L)


# ══════════════════════════════════════════════════════════════
# VODA_NA_STOLE_V1 — вода отдельной строкой
# ══════════════════════════════════════════════════════════════

def _voda_strokoy(p: dict) -> str:
    # Вода на столе: сторона, оба этажа, и чем её нет, если её нет.
    # Слово Шефа: вода не разрешает и не запрещает. Она лежит рядом с
    # сигналом, и трейдер решает сам — в том числе войти против неё, со
    # своим стопом. Поэтому здесь нет ни «можно», ни «нельзя»: только
    # куда смотрит структура старших этажей.
    v = (p or {}).get("вода")
    etazhi = (p or {}).get("вода_этажи") or ""
    pochemu = (p or {}).get("вода_почему") or ""
    svoy = (p or {}).get("направление_рабочего")
    hvost = (f"   направление рабочего: {svoy}" if svoy else "")
    hvost += f"   этаж: {(p or {}).get('этаж') or '—'}"
    golova = f"ВОДА: {v}" if v in ("BULL", "BEAR") else "ВОДА: НЕТ НА СТОЛЕ"
    if pochemu:
        golova += f"   ({pochemu})"
    golova += hvost
    if etazhi:
        golova += f"\n     этажи: {etazhi}"
    return golova




# PRIBORY_NA_STOL_V1 - marker

# KOMPAS_CHESTNYY_V1 - marker

# TOCHKA_ROZHDAETSYA_V1 - marker

# TOLKO_ZAKRYTYE_V1 - marker

# REZINKA_CHESTNAYA_V1 - marker

# VOLNA_NA_STOLE_V1 - marker

# KONEC_VOLNY_2_V1 - marker

# KRAY_VOLNY_V1 - marker

# TRI_POPYTKI_V1 - marker


# ══════════════════════════════════════════════════════════════
# VOLNA_V_MASSHTABE_V1 — сырая отметка конца волны 1
# ══════════════════════════════════════════════════════════════
# Стол показывает волну ДВАЖДЫ и намеренно: сверху координатами
# (откуда, куда, сколько баров прошло), ниже — в её собственном
# масштабе. Это не повтор: первое отвечает «где», второе — «какого
# размера то, на что ты смотришь».

def _volna_1_syro(p: dict) -> dict:
    """Отметка конца волны 1 из общего стола, как её записала рука
    рынка. Пусто — волна ещё идёт, и мерить нечего."""
    try:
        from hooks import load_trading_state, _blok_tochki, _para_tochki
        isk = _blok_tochki(load_trading_state() or {},
                           _para_tochki((p or {}).get("инструмент") or "",
                                        (p or {}).get("этаж") or ""))
        return (isk.get("konec_volny_1") or {})
    except Exception:
        return {}

# VOLNA_V_MASSHTABE_V1 - marker


# ══════════════════════════════════════════════════════════════
# ALLIG_NA_VHODE_V1 — разброс линий числом
# ══════════════════════════════════════════════════════════════

def _razbros_linij(al: dict, p: dict) -> str:
    """Насколько разошлись линии — в пунктах инструмента.

    Тот же размах, по которому код решает «спит или нет», только
    отданный числом. Не посчиталось — говорим «нет данных», а не
    подставляем ноль: ноль читался бы как «слиплись намертво».
    """
    try:
        j = float(al.get("челюсть"))
        t = float(al.get("зубы"))
        l = float(al.get("губы"))
    except (TypeError, ValueError):
        return "нет данных"
    razmah = max(abs(j - t), abs(t - l), abs(j - l))
    try:
        tochka = float((p or {}).get("point") or 0)
        if tochka > 0:
            return f"{razmah / tochka:.0f} пункт(ов)"
    except (TypeError, ValueError):
        pass
    return f"{razmah:.5f}"

# ALLIG_NA_VHODE_V1 - marker


# ══════════════════════════════════════════════════════════════
# ZAYAVKA_I_SPRED_V1 — уровни заявки и стопа
# ══════════════════════════════════════════════════════════════
# Правило Шефа про УРОВЕНЬ, а не про сделку: выше свечи — два спреда,
# ниже — один. Разворотный бар это всегда ТЕКУЩИЙ бар (так его и
# ловит ядро), поэтому его края — это high/low цены на столе.
#
# Спред в истории нулевой: в файлах колонка есть, значения нет. Число
# не выдумываем — говорим, что его нет, и показываем голые уровни.
# Выдуманный спред был бы тем же, чем был порог «50 пунктов».

def _spred_ceny(symbol: str, timeframe: str, point) -> tuple:
    """(спред в цене, откуда) — или (None, почему нет).

    MT5 отдаёт спред целым числом ПУНКТОВ, поэтому умножаем на шаг
    цены. Ноль — это не «спред нулевой», это «в файле не записан».
    """
    try:
        from feed_source import bars as _bars
        b, p = _bars(symbol, timeframe, 3)
        if not b:
            return None, "котировок нет"
        sp = (b[-1] or {}).get("spread")
        shag = point or p
        if not shag:
            return None, "шага цены нет"
        try:
            sp = float(sp) if sp not in (None, "") else 0.0
        except (TypeError, ValueError):
            sp = 0.0
        if sp <= 0:
            # SPRED_PO_UMOLCHANIYU_V1: в истории спреда нет —
            # раньше отсюда уходил None, и выше подставлялся
            # НОЛЬ. Стол выдавал голые края бара, стоп вставал
            # ровно на край. Ноль — это не «спреда нет», это
            # «его не записали»; в рынке его не бывает.
            return (SPRED_PO_UMOLCHANIYU * float(shag),
                    f"{SPRED_PO_UMOLCHANIYU} пункт(а) по умолчанию — "
                    f"в истории спреда нет")
        return sp * float(shag), f"{sp:.0f} пункт(ов)"
    except Exception as e:
        return None, f"не прочитан ({e})"


def _urovni_zayavki(rb: dict, c: dict, p: dict) -> str:
    """ВХОД одной строкой: куда заявка, куда стоп, с обеих сторон."""
    storona = (rb.get("сторона") or "").upper()
    try:
        h = float(c.get("high"))
        l = float(c.get("low"))
    except (TypeError, ValueError):
        return f"ВХОД: разворотник есть @ {rb.get('цена')}, краёв бара нет"

    spred, otkuda = _spred_ceny((p or {}).get("инструмент") or "",
                                (p or {}).get("этаж") or "",
                                (p or {}).get("point"))
    s = spred or 0.0
    znakov = 5
    try:
        shag = float((p or {}).get("point") or 0)
        if shag >= 0.01:
            znakov = 2
    except (TypeError, ValueError):
        pass

    if storona == "BULL":
        zayavka, stop = h + 2 * s, l - s
        kuda = "Buy Stop"
    else:
        zayavka, stop = l - s, h + 2 * s
        kuda = "Sell Stop"

    hvost = (f"   (спред {otkuda})" if spred else
             f"   ⚠ спред НЕ учтён: {otkuda} — в реале добавь "
             f"два спреда сверху, один снизу")
    return (f"ВХОД: {kuda} @ {zayavka:.{znakov}f}   стоп {stop:.{znakov}f}"
            f"   (бар: H {h:.{znakov}f} / L {l:.{znakov}f})" + hvost)

# ZAYAVKA_I_SPRED_V1 - marker


# ══════════════════════════════════════════════════════════════
# UROVEN_SLOMA_V1 — граница волны числом
# ══════════════════════════════════════════════════════════════

def _uroven_sloma(p: dict, c: dict) -> str:
    """Цена точки ноль и сколько до неё осталось.

    Единственный уровень, отделяющий живую волну от сломанной. Пока
    цена по свою сторону — волна жива, каким бы глубоким ни был откат.
    Закрылись за ним — точка гаснет, и структуры больше нет.

    Расстояние даём в пунктах инструмента: «двести пунктов» человек
    понимает, «0.00200» надо переводить в уме, а в уме легко ошибиться
    на порядок — особенно когда рядом золото с другим шагом.
    """
    t = (p or {}).get("точка_ноль") or {}
    cena_tochki = t.get("цена")
    storona = (t.get("сторона") or "").upper()
    seychas = (c or {}).get("close")
    if not t.get("жива") or cena_tochki is None or seychas is None:
        return "УРОВЕНЬ СЛОМА: точки нет — граница не считается"

    try:
        ct, sc = float(cena_tochki), float(seychas)
    except (TypeError, ValueError):
        return "УРОВЕНЬ СЛОМА: цена не прочиталась"

    # BULL-точка стоит на дне: слом, если уйдём НИЖЕ неё. BEAR — выше.
    do = (sc - ct) if storona == "BULL" else (ct - sc)
    shag = (p or {}).get("point")
    try:
        shag = float(shag or 0)
    except (TypeError, ValueError):
        shag = 0
    rasstoyanie = (f"{abs(do) / shag:.0f} пункт(ов)" if shag > 0
                   else f"{abs(do):.5f}")
    znakov = 2 if shag >= 0.01 else 5

    if do < 0:
        hvost = "   ⚠ ЦЕНА УЖЕ ЗА НЕЙ — волна сломана"
    elif do == 0:
        hvost = "   цена ровно на уровне"
    else:
        hvost = f"   до слома {rasstoyanie}"
    return (f"УРОВЕНЬ СЛОМА: {ct:.{znakov}f} "
            f"({'ниже' if storona == 'BULL' else 'выше'} — и волны нет)"
            + hvost)

# UROVEN_SLOMA_V1 - marker


# ══════════════════════════════════════════════════════════════
# SVOI_SDELKI_VIDNO_V1 — чем кончились прошлые попытки
# ══════════════════════════════════════════════════════════════

def _proshlye_popytki(t: dict) -> str:
    """Исходы прошлых входов на ЭТОЙ структуре, одной строкой.

    Не упрёк и не запрет: три попытки — право трейдера, слово Шефа.
    Просто факт о себе рядом с фактами о рынке, как «попытка 3-я».
    Живёт при точке: новая структура — пусто, чужих граблей не
    наследуем.
    """
    ish = (t or {}).get("исходы") or []
    if not ish:
        return ""
    kuski = []
    for i in ish:
        if not isinstance(i, dict):
            continue
        cena = i.get("цена")
        kuda = (i.get("куда") or "").upper()
        kuski.append(f"{i.get('попытка')}: {kuda} → {i.get('чем')}"
                     + (f" @ {cena}" if cena is not None else ""))
    if not kuski:
        return ""
    return "   ·   БЫЛО: " + "; ".join(kuski)

# SVOI_SDELKI_VIDNO_V1 - marker

# NOGI_SCHYOTNYE_V1 - marker

# VODA_NA_STOLE_V1 - marker

# VODA_STROKOY_MESTO_V1 - marker


if __name__ == "__main__":
    # Проверка без модели и без денег: python stol.py EURUSD H1
    s = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    tf = sys.argv[2] if len(sys.argv) > 2 else "H1"
    print(f"Стол {s} {tf}:\n")
    print(slovami(nakryt(s, tf)))

# ZAPUSK_V_KONEC_V1 - marker

# AC_VON_V1 - marker
