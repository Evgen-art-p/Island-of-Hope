# -*- coding: utf-8 -*-
# GRAFIK_ODNA_KARTINKA_V1
"""
ГРАФИК БИРЖИ — одна картинка на двоих.

ЗАЧЕМ. Решение Шефа (06.08): трейдер не просыпается от сигнала кода —
он СМОТРИТ, видит паттерн или не видит, и только увидев подключает
индикаторы. Значит ему нужна картинка. А Шефу нужна ТА ЖЕ САМАЯ, иначе
проверить трейдера нечем.

Отсюда главное решение: рисуем PNG, а не интерактивный виджет. Один
файл идёт и в кабинет на экран, и в запрос модели со зрением. Не два
механизма, а один — что Шеф видит, то трейдер и смотрел.

ЧТО РИСУЕМ (первый заход — минимум, который читается)
    свечи · три линии Аллигатора · AO гистограммой снизу
Фракталы стрелками и объём — вторым слоем, когда станет видно, что
основное читается. Нарисовать всё сразу легко, разглядеть — тяжело:
на скриншоте терминала Шефа половина деталей уже терялась.

ПОЧЕМУ БЕЗ ЛИШНЕЙ КРАСОТЫ. Читает это модель. Ей нужны толстые линии,
крупные бары и высокий контраст, а не тонкая сетка и мелкие подписи.
Светлый фон — по той же причине.

ЧТО НУЖНО ОДИН РАЗ:
    pip install matplotlib
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# ── Кадр. Не весь экран, а окно последних баров: на терминальном
# скриншоте всё сразу — мелко и нечитаемо (проверено на живом).
# 140 баров — число Вильямса: на втором уровне взгляд меняется
# «от сравнения двух соседних баров до анализа 140 и более».
BAROV_V_KADRE = 140

# METKA_NA_VHODE_V1: контрольные метки последних кадров, по паре
# и этажу. Метка есть ТОЛЬКО на картинке — ни на столе, ни в
# знаниях. Назвал её трейдер — значит смотрел.
METKI_KADROV: dict = {}


def metki_kadrov(chey: str) -> list:
    """Коды последних кадров для пары и этажа, например "EURUSD H4"."""
    return list(METKI_KADROV.get(str(chey).strip(), []))

# ── Смещения Аллигатора ВПЕРЁД, как в терминале: челюсть +8, зубы +5,
# губы +3. Ядро считает без смещения (ему сравнивать цену с текущей
# линией), но ГЛАЗ видит другую фигуру: в MT5 линии выступают за
# последнюю свечу. Рисуем как в терминале, иначе трейдер учится на
# одной картинке, а Шеф смотрит на другую.
SDVIG_JAW, SDVIG_TEETH, SDVIG_LIPS = 8, 5, 3

# ── Цвета. Аллигатор канонический: челюсть синяя, зубы красные,
# губы зелёные.
#
# SVECHA_VIDNA_V1 — БЫЛО СЛОМАНО, И ЭТО ЛОМАЛО ВСЁ ОСТАЛЬНОЕ.
# Фон был #fdf6e3 (кремовый), растущая свеча #f2f2f2 (почти
# белая). Контраст растущей к фону — 1.04 к 1, то есть
# НЕОТЛИЧИМО; падающей — 10.5 к 1. Растущую свечу держал только
# волосяной контур, а провайдеры уменьшают кадр перед показом
# модели, и контур смазывался. Модель видела тёмную массу на
# падениях и пустоту на росте — и путала направление. Так было
# у ВСЕХ моделей сразу: Haiku, Gemini, Sonnet.
#
# Почему именно тёмный фон. Одна свеча обязана быть светлой,
# другая тёмной — иначе не отличить рост от падения. Светлая
# свеча требует тёмного фона. Это ровно то, как устроен
# терминал Шефа, который он читает без труда.
#   растущая к фону 17.2:1 · падающая 3.9:1 · между собой 4.5:1
C_UP = "#f5f5f5"      # растущая — светлая
C_DOWN = "#cf3b2c"    # падающая — красная
C_KRAY = "#0a0d11"    # контур: тёмный, отделяет свечу от свечи
C_JAW = "#4d9bff"     # челюсть синяя — светлее под тёмный фон
C_TEETH = "#ff5c5c"   # зубы красные
C_LIPS = "#3ddc6b"    # губы зелёные
C_FON = "#0e1218"     # было #fdf6e3 — см. выше
C_AO_UP = "#3ddc6b"
C_AO_DOWN = "#ff5c5c"
# SVECHA_VIDNA_V1: сетка, подписи и рамки — под тёмный фон.
C_SETKA = "#ffffff1f"
C_TEKST = "#e6edf3"
C_RAMKA = "#ffffff40"
# PRISEDAYUSHCHIE_NA_KADRE_V1: строчка приседающих внизу кадра.
# Красный — как в терминале Шефа (BW MFI, красный столбик).
C_SQUAT = "#d92626"


# ── UCHEBKA_V1: учебный режим кадра ───────────────────────────
# Слово Шефа 22.09: линии расхождения на кадре — учёба, а не
# постоянное устройство. Пусть поработает с ними пару прогонов, потом
# выключим и посмотрим, осталось ли чтение.
# Включение: положить рядом файл «учебный_режим.txt» (пустой). Убрать
# файл — линии пропадают. Никаких кнопок и настроек.
def _uchebnyy_rezhim() -> bool:
    try:
        return (Path(__file__).resolve().parent / "учебный_режим.txt").exists()
    except Exception:
        return False


def narisovat(bars: list, alligator: dict, ao_series: list,
              symbol: str = "", timeframe: str = "",
              kuda: Optional[Path] = None,
              barov: int = BAROV_V_KADRE,
              fraktaly: Optional[dict] = None,
              prisedayushchie: Optional[list] = None,
              linii: bool = True) -> Optional[Path]:
    """Рисует кадр и возвращает путь к PNG. Нет matplotlib — вернёт None.

    bars       — список баров как их отдаёт feed_source
    alligator  — как его отдаёт compute_alligator (нужны *_series)
    ao_series  — как его отдаёт compute_ao_series
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        # KADR_BEZ_PYPLOT_V1: НЕ pyplot. Общий склад картинок один на
        # весь процесс и не переживает, когда в него лезут из двух
        # потоков разом (кнопка Шефа и рука трейдера). Берём объект.
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.patches import Rectangle
        from matplotlib.ticker import MaxNLocator
    except ImportError:
        return None

    if not bars or len(bars) < 10:
        return None

    n = min(barov, len(bars))
    b = bars[-n:]

    def _hvost(seq):
        """Последние n значений ряда, выровненные по кадру."""
        if not seq:
            return [None] * n
        s = list(seq)[-n:]
        return [None] * (n - len(s)) + s

    # Смещаем вперёд: значение бара i рисуется на позиции i+сдвиг.
    # Хвост уходит правее последней свечи — там же, где он в терминале.
    def _sdvinut(seq, sdvig):
        h = _hvost(seq)
        return [None] * sdvig + h

    jaw = _sdvinut(alligator.get("jaw_series"), SDVIG_JAW)
    teeth = _sdvinut(alligator.get("teeth_series"), SDVIG_TEETH)
    lips = _sdvinut(alligator.get("lips_series"), SDVIG_LIPS)
    ao = _hvost(ao_series)

    # Свечи сверху, AO снизу — как в терминале, глаз к этому привык.
    # Пропорция 7:3: гистограмма нужна для формы, а не для чтения цифр.
    # KADR_BEZ_PYPLOT_V1: своя картинка, не из общего склада.
    fig = Figure(figsize=(16, 9), dpi=110)
    FigureCanvasAgg(fig)
    ax, axo = fig.subplots(
        2, 1, sharex=True,
        gridspec_kw={"height_ratios": [7, 3], "hspace": 0.06})
    fig.patch.set_facecolor(C_FON)

    x = list(range(n))
    shirina = 0.58

    for i, bar in enumerate(b):
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        rastet = c >= o
        # тень
        # SVECHA_VIDNA_V1: тень светлая — на тёмном фоне тёмная
        # тень пропадала вместе с размахом бара.
        ax.plot([i, i], [l, h], color="#9fb0c0", linewidth=1.3,
                zorder=2)
        # тело; доджи рисуем полоской, иначе бар пропадает
        telo = abs(c - o)
        # SVECHA_VIDNA_V1: линии толще. Волосяная линия не
        # переживает уменьшение кадра на стороне провайдера —
        # смазывается в фон вместе со всей свечой. Доджи рисуем
        # светлым, иначе на тёмном фоне бар пропадает совсем.
        if telo < (h - l) * 0.02:
            ax.plot([i - shirina / 2, i + shirina / 2], [c, c],
                    color=C_UP, linewidth=2.2, zorder=3)
        else:
            ax.add_patch(Rectangle(
                (i - shirina / 2, min(o, c)), shirina, telo,
                facecolor=C_UP if rastet else C_DOWN,
                edgecolor=C_KRAY, linewidth=1.6, zorder=3))

    # Аллигатор — толсто, это главные линии кадра.
    # KADR_BEZ_ALLIGATORA_V1: но трейдеру первого уровня они не
    # рисуются вовсе. Три попытки запретить их бумагой провалились —
    # он возвращался к ним в каждом отказе. Нечего вплетать, если
    # нечего видеть. Направление он берёт строкой со стола.
    for ryad, cvet, imya in (() if not linii else
                             ((jaw, C_JAW, "Челюсть"),
                              (teeth, C_TEETH, "Зубы"),
                              (lips, C_LIPS, "Губы"))):
        xs = [i for i, v in enumerate(ryad) if v is not None]
        ys = [v for v in ryad if v is not None]
        if xs:
            ax.plot(xs, ys, color=cvet, linewidth=2.2, zorder=4, label=imya)

    # Фракталы — стрелки над/под баром, как в терминале. Это точка
    # отсчёта для входа и место стопа: не нарисовать их — значит
    # заставить трейдера считать пять баров глазами на каждом шаге.
    if fraktaly:
        sdvig_ot = len(bars) - n   # индексы фракталов — по всему ряду
        for storona, znak, dy in (("all_up", "v", 1), ("all_down", "^", -1)):
            for f in (fraktaly.get(storona) or []):
                i = f.get("bar_index")
                if i is None:
                    continue
                k = i - sdvig_ot
                if not (0 <= k < n):
                    continue
                cena = f.get("price")
                if cena is None:
                    continue
                razmah = max(x["high"] for x in b) - min(x["low"] for x in b)
                ax.plot(k, cena + dy * razmah * 0.012, marker=znak,
                        color="#7a4fbf", markersize=8, zorder=5)

    # RB_NA_KADRE_V1: РАЗВОРОТНЫЕ БАРЫ — как в терминале Шефа.
    # Фракталы мы рисуем и объясняем это тем, что иначе трейдер будет
    # считать бары глазами. С разворотником вышло ровно так: он важнее
    # (по нему входят), а на кадре его не было вовсе — трейдер смотрел
    # на голые свечи и гадал, о каком баре речь.
    # Правило то же, что в ядре (detect_necron_bar) и в твоём
    # iDivergenceBar.mq4: сдвиг линий 8/5/3, новый экстремум, закрытие
    # в противоположной половине и весь бар ЦЕЛИКОМ вне пасти. Считаем
    # прямо по рядам линий — одним проходом по окну кадра.
    try:
        from williams_core import _shifted_series
        _jaw = _shifted_series(alligator.get("jaw_series"), 8)
        _teeth = _shifted_series(alligator.get("teeth_series"), 5)
        _lips = _shifted_series(alligator.get("lips_series"), 3)
        _razmah_rb = max(x["high"] for x in b) - min(x["low"] for x in b)
        _sdvig_rb = len(bars) - n
        _posledniy = None
        for _k in range(1, n):
            _i = _sdvig_rb + _k
            if _i < 1 or _i >= len(_jaw):
                continue
            _j, _t, _l = _jaw[_i], _teeth[_i], _lips[_i]
            if _j is None or _t is None or _l is None:
                continue
            _up, _dn = max(_l, _t, _j), min(_l, _t, _j)
            _bar, _pred = bars[_i], bars[_i - 1]
            _mid = (_bar["high"] + _bar["low"]) / 2
            _storona = None
            if (_bar["high"] > _pred["high"] and _bar["close"] < _mid
                    and _bar["low"] > _up):
                _storona = "BEAR"
            elif (_bar["low"] < _pred["low"] and _bar["close"] > _mid
                    and _bar["high"] < _dn):
                _storona = "BULL"
            if not _storona:
                continue
            _bych = _storona == "BULL"
            _cena = _bar["low"] if _bych else _bar["high"]
            _dy = -1 if _bych else 1
            ax.plot(_k, _cena + _dy * _razmah_rb * 0.02,
                    marker="^" if _bych else "v",
                    color="#e0a020", markersize=11, zorder=6)
            _posledniy = (_k, _cena, _dy)
        if _posledniy:
            _k, _cena, _dy = _posledniy
            ax.plot(_k, _cena + _dy * _razmah_rb * 0.02, marker="o",
                    markerfacecolor="none", markeredgecolor="#e0a020",
                    markersize=20, markeredgewidth=1.6, zorder=6)
    except Exception as _e_rb:
        print(f"[КАДР] разворотники не нарисовались: {_e_rb}")

    # PRISEDAYUSHCHIE_NA_KADRE_V1: строчка приседающих вдоль низа.
    # Не второе окно и не гистограмма объёма — просто отметка, ГДЕ
    # рынок присел. Смысл ей придаёт место: на дне после падения —
    # упёрся в пол, на потолке — толкают, а не растёт, в середине
    # хода — вдох. Кадр кладёт факт, вывод делает смотрящий.
    # Совпадение с разворотником отмечать отдельно не нужно: кружок
    # окажется под тем же баром, где жёлтая стрелка.
    if prisedayushchie:
        try:
            _sdvig_sq = len(bars) - n
            _nizy = [x['low'] for x in b]
            _razmah_sq = max(x['high'] for x in b) - min(_nizy)
            _stroka_y = min(_nizy) - _razmah_sq * 0.045
            _xs_sq = []
            for _s in prisedayushchie:
                _i = _s.get('bar_index')
                if _i is None:
                    continue
                _k = _i - _sdvig_sq
                if 0 <= _k < n:
                    _xs_sq.append(_k)
            if _xs_sq:
                ax.plot(_xs_sq, [_stroka_y] * len(_xs_sq),
                        linestyle='none', marker='o',
                        markerfacecolor=C_SQUAT,
                        markeredgecolor=C_SQUAT,
                        markersize=4.5, zorder=5,
                        label='приседающий')
        except Exception as _e_sq:
            print(f"[КАДР] приседающие не нарисовались: {_e_sq}")

    ax.set_facecolor(C_FON)
    ax.grid(True, color=C_SETKA, linewidth=0.8)   # SVECHA_VIDNA_V1
    # правее последней свечи оставляем место под вынос линий
    ax.set_xlim(-1, n + SDVIG_JAW + 1)
    # легенда снаружи справа — в углу она закрывала свечи
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9,
              bbox_to_anchor=(1.005, 1.0), borderaxespad=0)
    zag = f"{symbol} {timeframe}".strip()
    if zag:
        ax.set_title(zag, fontsize=15, loc="left", color=C_TEKST)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=9))
    ax.tick_params(labelsize=10, colors=C_TEKST)   # SVECHA_VIDNA_V1
    for s in ax.spines.values():
        s.set_color(C_RAMKA)

    # AO — знак и форма важнее величины
    xs = [i for i, v in enumerate(ao) if v is not None]
    ys = [v for v in ao if v is not None]
    if xs:
        cveta = [C_AO_UP if (k == 0 or ys[k] >= ys[k - 1]) else C_AO_DOWN
                 for k in range(len(ys))]
        axo.bar(xs, ys, color=cveta, width=0.7, zorder=3)

    # UCHEBKA_V1: учебный режим — две линии расхождения прямо на кадре.
    # UCHEBKA_MATRYOSHKA_V1 (23.09, слово Шефа): рисуем самую большую
    # пару (весь ход) — толстой линией, и последнюю справа (край) —
    # тонкой. Если это одна и та же пара — одна линия. Расхождение
    # нашлось в обе стороны — берём ту сторону, где край свежее.
    # Включается файлом Биржа/учебный_режим.txt — нет файла, линий нет.
    if _uchebnyy_rezhim():
        try:
            import sverka_divera as _sd
            _hi = [x.get("high") for x in b]
            _lo = [x.get("low") for x in b]
            _vid = list(range(len(ao)))
            _luchshe, _svezhest = None, -1
            for _verh in (True, False):
                _r = _sd.dve_gorki(ao, _hi, _lo, _vid, _verh, b)
                # TONKAYA_SAMA_V1: рисуем, где бы ни было расхождение —
                # тонкая сама по себе, даже без дивера у толстой.
                _vse = _r.get("пары") or []
                _pary = [x for x in _vse if x.get("est")]
                if not _pary:
                    continue
                if _pary[-1]["i_цена_2"] > _svezhest:
                    _luchshe, _svezhest = _pary, _pary[-1]["i_цена_2"]
            if _luchshe:
                _risovat = [(_luchshe[0], 2.4)]
                if _luchshe[-1] is not _luchshe[0]:
                    _risovat.append((_luchshe[-1], 1.3))
                for _p, _tol in _risovat:
                    ax.plot([_p["i_цена_1"], _p["i_цена_2"]],
                            [_p["цена_было"], _p["цена_стало"]],
                            color="#22d3ee", linewidth=_tol, zorder=8)
                    axo.plot([_p["i_ao_1"], _p["i_ao_2"]],
                             [_p["ao_было"], _p["ao_стало"]],
                             color="#22d3ee", linewidth=_tol, zorder=8)
        except Exception as _e_uch:
            print(f"[УЧЕБКА] линии не нарисовались ({_e_uch}) — не беда")

    # SVECHA_VIDNA_V1: нулевая линия и подписи — под тёмный фон.
    axo.axhline(0, color="#ffffff66", linewidth=1.3, zorder=2)
    axo.set_facecolor(C_FON)
    axo.grid(True, color=C_SETKA, linewidth=0.8)
    axo.set_ylabel("AO", fontsize=11, color=C_TEKST)
    axo.tick_params(labelsize=9, colors=C_TEKST)
    for s in axo.spines.values():
        s.set_color(C_RAMKA)

    # Подписи времени — редко: частые превращаются в кашу
    shag = max(1, n // 8)
    poz = list(range(0, n, shag))
    axo.set_xlim(-1, n + SDVIG_JAW + 1)
    axo.set_xticks(poz)
    axo.set_xticklabels([str(b[i].get("date", ""))[:16] for i in poz],
                        rotation=0, fontsize=9)

    if kuda is None:
        # KADR_I_VAKANSIYA_V1: своё имя каждому снимку. Один файл на
        # все кадры значил, что браузер и глаз трейдера получают по
        # знакомому адресу вчерашнюю картинку.
        from datetime import datetime as _dt
        _papka = Path(__file__).resolve().parent / "кадры"
        _papka.mkdir(parents=True, exist_ok=True)
        _chisto = lambda s: "".join(
            c for c in str(s) if c.isalnum() or c in "-_") or "нет"
        kuda = _papka / (f"{_chisto(symbol)}_{_chisto(timeframe)}_"
                         f"{_dt.now().strftime('%Y%m%d_%H%M%S_%f')}.png")
        try:   # папка не должна расти без края: держим последние 20
            _bylye = sorted(_papka.glob("*.png"),
                            key=lambda f: f.stat().st_mtime)
            for _f in _bylye[:-20]:
                _f.unlink(missing_ok=True)
        except Exception:
            pass
    # SVECHA_VIDNA_V1: КОНТРОЛЬНАЯ МЕТКА. Код из двух букв и двух
    # цифр, новый при каждой отрисовке. Его нет ни на столе, ни в
    # промпте, ни в знаниях — ТОЛЬКО на картинке. Спроси трейдера
    # «какой код в левом верхнем углу кадра?»: назвал — видит,
    # не назвал — не видит, и никакие цвета этого не объяснят.
    try:
        import random as _rnd
        _bukvy = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
        _kod = (_rnd.choice(_bukvy) + _rnd.choice(_bukvy)
                + f'{_rnd.randint(10, 99)}')
        # METKA_VIDNA_V1: было 18 — в ужатой панели Кабинета это
        # девять пикселей, метку не разглядеть. А метка, которую
        # не видит Шеф, не проверяет ничего.
        fig.text(0.012, 0.985, _kod, ha='left', va='top',
                 fontsize=44, color='#ffd866', family='monospace',
                 fontweight='bold', zorder=20)
        # METKA_NAZYVAET_KADR_V1: метка без имени кадра
        # бесполезна — за один взгляд их печатается несколько,
        # и ответ трейдера не с чем сверить.
        _chey = f"{symbol} {timeframe}".strip() or "?"
        print(f'[КАДР] контрольная метка: {_kod} · {_chey}')
        # METKA_NA_VHODE_V1: запоминаем код, иначе сверять ответ
        # трейдера не с чем. Держим последние 12 на пару и этаж:
        # за один взгляд кадр рисуется несколько раз, и смотреть
        # он мог не самый последний.
        _spisok = METKI_KADROV.setdefault(_chey, [])
        _spisok.append(_kod)
        del _spisok[:-12]
    except Exception as _e_kod:
        print(f'[КАДР] метка не встала: {_e_kod}')

    # UROVNI_ORDEROV_V1: уровни заявок и позиций на кадре. Слово
    # Шефа: заявка — зелёный пунктир, вход открытой позиции —
    # зелёная сплошная, стоп — красный пунктир, старый стоп (до
    # трейлинга) — жёлтый пунктир. Цена у правого края.
    try:
        from hooks import load_trading_state as _lts_u
        _poz = (_lts_u() or {}).get('positions') or []
        _sym = str(symbol or '').strip().upper()
        _tf = str(timeframe or '').strip().upper()
        _linii = []   # (цена, цвет, стиль, подпись)
        for _p in _poz:
            _ps = str(_p.get('symbol') or '').strip().upper()
            _pt = str(_p.get('timeframe') or '').strip().upper()
            if _ps and _sym and _ps != _sym:
                continue
            if _pt and _tf and _pt != _tf:
                continue
            _st = str(_p.get('status') or '').upper()
            _vh = _p.get('entry')
            _sp = _p.get('stop')
            _s0 = _p.get('stop_initial')
            if _st == 'OPEN':
                if _vh is not None:
                    _linii.append((float(_vh), '#3ddc6b', '-', 'вход'))
            elif _st in ('PENDING', 'WATCHING'):
                if _vh is not None:
                    _linii.append((float(_vh), '#3ddc6b', '--', 'заявка'))
            else:
                continue
            if _sp is not None:
                _linii.append((float(_sp), '#ff5c5c', '--', 'стоп'))
            if (_s0 is not None and _sp is not None
                    and abs(float(_s0) - float(_sp)) > 1e-9):
                _linii.append((float(_s0), '#ffd866', '--', 'был стоп'))
        if _linii:
            _lo, _hi = ax.get_ylim()
            _ceny = [c for c, *_ in _linii] + [_lo, _hi]
            _nlo, _nhi = min(_ceny), max(_ceny)
            _zap = (_nhi - _nlo) * 0.03
            if _nlo < _lo or _nhi > _hi:
                ax.set_ylim(_nlo - _zap, _nhi + _zap)
            # знаков после точки — по величине самой цены
            _c0 = abs(_linii[0][0])
            _znakov = 5 if _c0 < 20 else (3 if _c0 < 500 else 2)
            # линии через весь кадр
            for _c, _cv, _ls, _pod in _linii:
                ax.axhline(_c, color=_cv, linestyle=_ls,
                           linewidth=1.4, alpha=0.95, zorder=15)
            # UROVNI_SLEVA_V1 (23.09, слово Шефа): подписи — у ЛЕВОГО
            # края: справа они закрывали свежую цену.
            # (было: подписи ВНУТРИ кадра у правого края: справа от свечей)
            # пустое поле сдвига Аллигатора. Снаружи справа стоит
            # легенда — там подписи прятались под её рамкой.
            # Близкие цены разводим по вертикали, иначе слипаются.
            _ylo, _yhi = ax.get_ylim()
            _raz = (_yhi - _ylo) or 1.0
            _por = sorted(_linii, key=lambda t: t[0])
            _pos = []
            for _c, _cv, _ls, _pod in _por:
                _f = (_c - _ylo) / _raz
                if _pos and _f - _pos[-1] < 0.045:
                    _f = _pos[-1] + 0.045
                _pos.append(_f)
                ax.text(0.005, _f, f'{_pod} {_c:.{_znakov}f}',
                        transform=ax.transAxes, color=_cv,
                        fontsize=10, va='center', ha='left',
                        family='monospace', zorder=17,
                        bbox=dict(facecolor='#0d1117', alpha=0.85,
                                  edgecolor=_cv, linewidth=0.6,
                                  boxstyle='round,pad=0.25'))
            print(f'[КАДР] уровни на кадре: {len(_linii)}')
    except Exception as _e_ur:
        print(f'[КАДР] уровни не встали ({_e_ur}) — рисую без них')

    kuda = Path(kuda)
    kuda.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(kuda, facecolor=C_FON, bbox_inches="tight")
    # KADR_BEZ_PYPLOT_V1: закрывать нечего — картинка нигде не
    # зарегистрирована и уходит сама, как только кончится вызов.
    return kuda


def kadr(symbol: str, timeframe: str, kuda: Optional[Path] = None,
         barov: int = BAROV_V_KADRE,
         linii: bool = True) -> Optional[Path]:
    """Взять бары из источника, посчитать индикаторы и нарисовать кадр.

    Готовая кнопка для кабинета: «посмотреть» — Шеф видит то же, что
    ляжет трейдеру, и никого при этом не будит и модель не тратит.
    """
    import sys
    p = Path(__file__).resolve().parent
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    from feed_source import bars as source_bars
    from williams_core import (compute_alligator, compute_ao_series,
                               detect_fractals, detect_squat_bars)

    bs, point = source_bars(symbol, timeframe, count=max(400, barov + 60))
    # TOLKO_ZAKRYTYE_V1: кадр рисуем по тем же барам, по которым считан
    # стол. Иначе Шеф и трейдер смотрят разные картинки, а на столе
    # стоит третья правда. Живая свеча — в терминале.
    try:
        from hooks import _tolko_zakrytye
        bs = _tolko_zakrytye(bs)
    except Exception:
        pass
    # KADR_PO_BARU_GORODA_V1: не заглядываем вперёд. В прогоне курсор
    # успевает сдвинуться, и кадр рисовался по бару, которого в момент
    # вопроса ещё не было, — трейдер подглядывал в будущее.
    try:
        from hooks import load_trading_state as _lts
        _bar_goroda = str(((_lts() or {}).get("рынок") or {}).get("бар") or "")
        if _bar_goroda:
            _do = [b for b in bs if str(b.get("date", "")) <= _bar_goroda]
            # обрезаем ВСЕГДА, когда что-то осталось. Порога тут быть
            # не должно: «мало баров — нарисую как есть» означало бы
            # снова показать будущее, а короткий честный кадр лучше
            # длинного, но подглядывающего.
            if _do:
                if len(_do) != len(bs):
                    print(f"[КАДР] обрезал по бару города {_bar_goroda}: "
                          f"{len(bs)} → {len(_do)}")
                bs = _do
            else:
                print(f"[КАДР] по бару города {_bar_goroda} баров нет — "
                      f"кадра не будет")
                return None
    except Exception as _e_bar:
        print(f"[КАДР] бар города не спросился ({_e_bar}) — рисую как есть")

    if not bs:
        return None
    highs = [x["high"] for x in bs]
    lows = [x["low"] for x in bs]
    al = compute_alligator(highs, lows, point=point)
    ao = compute_ao_series(highs, lows)
    fr = detect_fractals(bs)
    # PRISEDAYUSHCHIE_NA_KADRE_V1: считаем ЯДРОМ, не своей формулой.
    # detect_squat_bars — канон BWMFI: объём вырос, MFI упал.
    # Второй счёт той же сущности в рисовалке = вторая правда.
    try:
        _sq = detect_squat_bars(bs, point=point).get('all') or []
    except Exception as _e_sq:
        print(f"[КАДР] приседающие не посчитались: {_e_sq}")
        _sq = []
    return narisovat(bs, al, ao, symbol, timeframe, kuda=kuda, barov=barov,
                     fraktaly=fr, prisedayushchie=_sq,
                     linii=linii)          # KADR_BEZ_ALLIGATORA_V1

# KADR_I_VAKANSIYA_V1 - marker

# RB_NA_KADRE_V1 - marker

# TOLKO_ZAKRYTYE_V1 - marker

# PRISEDAYUSHCHIE_NA_KADRE_V1 - marker

# SVECHA_VIDNA_V1 - marker

# KADR_BEZ_PYPLOT_V1 - marker


