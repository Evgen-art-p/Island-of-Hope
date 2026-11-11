# -*- coding: utf-8 -*-
# RUKI_TREYDERA_V1
"""
РУКИ ТРЕЙДЕРА — математика по просьбе, а не по рельсам.

ЗАКОН ЭТОГО ФАЙЛА
    Ни одна рука ничего не решает и не советует. Руки считают и
    отдают ЧИСЛА. Что эти числа значат — говорит трейдер.
    КАНОН_ВХОДА.md §1④: индикаторы — ориентиры, НЕ сигналы; путь по
    их комбинации ищет трейдер. §1⑥: математику считает код, решает
    LLM и только на готовом.

    Поэтому здесь нет и не будет: «сигнал есть», «вход годится»,
    «структура подтверждена», «рекомендую». Только факт и его цена.

ПОЧЕМУ ЭТО ВАЖНО
    Раньше код сам решал, какую математику посчитать, — исходя из
    роли, прибитой к слоту. Трейдер не просил: ему приносили. Теперь
    он просит сам, и его личный выбор паттерна наконец на что-то
    влияет.
"""
from __future__ import annotations

import json
import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))


def shema(rabochiy_etazh: str = "") -> list:
    """Описание рук для модели. Формулировки нарочно сухие: рука —
    это прибор, а не советчик."""
    import masshtab
    etazhi = ", ".join(masshtab.LESTNICA)
    nizhe = masshtab.nizhe(rabochiy_etazh) or "—"
    vyshe = masshtab.vyshe(rabochiy_etazh) or "—"
    return [
        {"type": "function", "function": {
            "name": "stol_na_etazhe",
            "description": (
                "Накрыть стол на указанном этаже: Аллигатор, AO, фракталы, "
                "разворотный бар, окно объёма, натяжение, цена. Голые "
                f"показания, без выводов. Этажи: {etazhi}. "
                f"На ступень ниже твоего рабочего — {nizhe}, выше — {vyshe}."),
            "parameters": {"type": "object", "properties": {
                "этаж": {"type": "string",
                         "description": "например H1"},
                "инструмент": {"type": "string",
                               "description": ("необязательно: другая пара, "
                                               "например USDCNH — посмотреть "
                                               "и посчитать, если её котировки "
                                               "есть в городе. Пусто — твоя "
                                               "пара. Входишь всё равно только "
                                               "по своей")},
            },
                "required": ["этаж"]}}},
        {"type": "function", "function": {
            "name": "izmerit_volnu",
            "description": (
                "Померить волновую структуру на указанном этаже: длина в "
                "барах от четвёртого пересечения нуля AO назад до текущего "
                "бара, читается ли внутри пятёрка, направление и цена "
                "разворотного бара, дивергенция, ангуляция. Числа, не "
                "вердикт."),
            "parameters": {"type": "object", "properties": {
                "этаж": {"type": "string",
                         "description": "например H1"}},
                "required": ["этаж"]}}},
        # RUKA_MAYAKA_V1: выход наружу. Раньше житель мог спросить мир
        # только ДОМА — на работе мозг был глухой.
        *_ruka_mayaka_shema(),
        *_ruka_prikaza_shema(),          # RUKA_PRIKAZA_V1
        # RASTYAZHKA_V1: главные глаза трейдера. Раньше он видел ровно
        # один кадр — последние 140 баров рабочего этажа, — и растянуть
        # нужную волну не мог ничем.
        {"type": "function", "function": {
            "name": "rastyanut_volnu",
            "description": (
                "ПОКАЗАТЬ картинку куска рынка, растянутого так, чтобы он "
                "занял 100-140 баров. Так смотрят зигзаг целиком, а потом "
                "волну C внутри него. Этаж подбирается сам под длину "
                "куска — можешь не указывать. Ты УВИДИШЬ картинку."),
            "parameters": {"type": "object", "properties": {
                "с": {"type": "string",
                      "description": "начало куска, вид 2025.05.05 20:00"},
                "по": {"type": "string",
                       "description": "конец куска; пусто — до текущего бара"},
                "этаж": {"type": "string",
                         "description": "необязательно, если хочешь свой"}},
                "required": ["с"]}}},
        # KRAYNIYE_TOCHKI_V1: опора для растяжки. Не разметка волн и
        # не фракталы (те всюду и шумят) — вершина и дно, то, что глаз
        # ловит сразу. Числа нужны, чтобы назвать границы точно: на
        # кадре подписи мелкие, дату по картинке не прочесть.
        {"type": "function", "function": {
            "name": "krayniye_tochki",
            "description": (
                "Вершина и дно на куске: когда и почём. Отдельно по первой "
                "и второй половине куска. Голые числа — какая из этих точек "
                "начало твоей волны, решаешь ты, глядя на картинку. Нужны, "
                "чтобы назвать границы для rastyanut_volnu без промаха."),
            "parameters": {"type": "object", "properties": {
                "этаж": {"type": "string",
                         "description": "пусто — твой рабочий"},
                "баров": {"type": "integer",
                          "description": "сколько баров назад смотреть, "
                                         "по умолчанию 140"},
                "инструмент": {"type": "string",
                               "description": ("необязательно: другая пара, "
                                               "например USDCNH — посмотреть "
                                               "и посчитать, если её котировки "
                                               "есть в городе. Пусто — твоя "
                                               "пара. Входишь всё равно только "
                                               "по своей")},
            },
                "required": []}}},
        # CHISLA_V_TOCHKAH_V1 (слово Шефа 30.09: «не приблизительно —
        # пусть точно сверяет»). Прибор, не судья: какие бары сравнивать,
        # выбирает трейдер на кадре; рука отдаёт их числа.
        {"type": "function", "function": {
            "name": "chisla_v_tochkah",
            "description": (
                "ТОЧНЫЕ числа в барах, которые ты выбрала на кадре: high, "
                "low, close и AO каждого. Назови даты баров — например две "
                "вершины и под ними два горба AO — рука отдаст их числа, "
                "без выводов. Этими числами и называй четыре числа "
                "расхождения в приказе, не на глаз. Даты бери с кадра или "
                "из krayniye_tochki."),
            "parameters": {"type": "object", "properties": {
                "бары": {"type": "string",
                         "description": ("даты баров через запятую, вид "
                                         "2019.12.13 08:00, 2019.12.27 16:00")},
                "этаж": {"type": "string",
                         "description": "пусто — твой рабочий"},
                "инструмент": {"type": "string",
                               "description": ("необязательно: другая пара; "
                                               "пусто — твоя")},
            },
                "required": ["бары"]}}},
        {"type": "function", "function": {
            "name": "pokazat_etazh",
            "description": (
                "ПОКАЗАТЬ картинку другого этажа целиком, последние 140 "
                "баров. Когда нужно просто взглянуть шире или мельче."),
            "parameters": {"type": "object", "properties": {
                "этаж": {"type": "string", "description": "например M30"}},
                "required": ["этаж"]}}},
        # DOSKA_V1: общая память о структуре. Разворотник нельзя
        # отсеять числами — отсев это взгляд на растянутой волне C.
        # Кто посмотрел и увидел конец коррекции, тот и объявляет
        # точку ноль; от неё пляшут остальные.
        # KARTINA_SVOYA_V1: твоё чтение, не общее. Стол один на всех,
        # факты одинаковые — а волны у каждого свои. Чужих картин ты
        # не видишь: пока каждый не разобрался в своём, подсматривание
        # свело бы всех в одно мнение.
        {"type": "function", "function": {
            "name": "moya_kartina",
            "description": (
                "ТВОЁ чтение этого рынка, как ты его оставил(а) в прошлый "
                "раз: где ТВОЯ точка ноль, пошла ли от неё волна, видишь ли "
                "откат. Смотри ПЕРВЫМ делом — иначе начнёшь с чистого листа "
                "и не увидишь того, что уже разглядел(а) раньше."),
            "parameters": {"type": "object", "properties": {}, "required": []}}},
        {"type": "function", "function": {
            "name": "zapisat_v_kartinu",
            "description": (
                "Записать в СВОЮ картину то, что ты увидел(а). "
                "«ход» — вот это движение я работаю, началось здесь "
                "(скажи направление и этаж, на котором обвёл: конец "
                "будешь искать там же). «попытка» — не взяло; это не "
                "ошибка, но три подряд — повод проверить, тот ли ход. "
                "«волна» — от начала пошло движение и дошло досюда. "
                "«откат» — к своей волне видишь откат. "
                "«заметка» — мысль на память. «стереть» — твоя структура "
                "сломалась. Это ТВОЁ чтение: сосед может видеть иначе, и "
                "это нормально."),
            "parameters": {"type": "object", "properties": {
                "что": {"type": "string",
                        "description": "ход | попытка | волна | откат | заметка | стереть"},
                "цена": {"type": "number", "description": "если есть"},
                "бар": {"type": "string",
                        "description": "дата бара, вид 2025.05.05 20:00"},
                "направление": {"type": "string",
                                "description": "для хода: LONG или SHORT"},
                "этаж": {"type": "string",
                         "description": "для хода: на каком этаже ты его обвёл, например H1"},
                "почему": {"type": "string",
                           "description": "что именно ты увидел(а) — своими словами"}},
                "required": ["что"]}}},
        # UCHEBNIK_V_RUKE_V1: картинки из книги, по которой учили.
        # В памяти у неё лежит ПЕРЕСКАЗ рисунка, а не рисунок — можно
        # посмотреть заново, стоя перед живым графиком.
        {"type": "function", "function": {
            "name": "uchebnik",
            "description": (
                "ПОКАЗАТЬ картинку из того, по чему тебя учили в Академии: "
                "«приседающий бар», «фрактал», «волны AO», «окно объёма». "
                "Ты УВИДИШЬ сам рисунок и авторскую подпись к нему. Полезно, "
                "когда сомневаешься, как выглядит паттерн в учебнике — "
                "сравни с тем, что на графике сейчас. Можно сузить до "
                "дисциплины: финансы, психология, искусство."),
            "parameters": {"type": "object", "properties": {
                "о_чём": {"type": "string",
                          "description": "тема словами, например «приседающий бар»"},
                "дисциплина": {"type": "string",
                               "description": "необязательно: сузить поиск"}},
                "required": ["о_чём"]}}},
        {"type": "function", "function": {
            "name": "razbor_struktury",
            "description": (
                "Разметка волн: номера, три места входа по риску, "
                "отношения между волнами. ЭТО ИНСТРУМЕНТ ВЕДЕНИЯ, а не "
                "входа. Зови, когда ты УЖЕ В РЫНКЕ и хочешь прикинуть, "
                "где ты в структуре и сколько ещё можно пройти. Перед "
                "входом это не нужно: там вопрос один — кончился ход "
                "или нет."),
            "parameters": {"type": "object", "properties": {},
                           "required": []}}},
        {"type": "function", "function": {
            "name": "chemu_uchili",
            "description": (
                "Какие дисциплины и сколько рисунков есть в Академии. "
                "Смотри, если не знаешь, о чём вообще можно спросить."),
            "parameters": {"type": "object", "properties": {},
                           "required": []}}},
        {"type": "function", "function": {
            "name": "moy_dnevnik",
            "description": (
                "Твои последние записи: что ты решал, чем кончилось. "
                "Своя память, не чужая."),
            "parameters": {"type": "object", "properties": {
                "сколько": {"type": "integer",
                            "description": "по умолчанию 5"}},
                "required": []}}},
        # ── RUKI_ZAKLADOK_V1: метка как закладка ────────────────
        {"type": "function", "function": {
            "name": "moi_yarlyki",
            "description": (
                "ТВОЙ СЛОВАРЬ ЗАКЛАДОК: какие ярлыки ты уже вешал и "
                "сколько раз. Смотри ПЕРЕД тем, как вешать новый, и "
                "бери из этого списка: иначе через месяц у тебя будет "
                "и «дивер», и «диверы», и «дивергенция» — и ты сам не "
                "вспомнишь, под каким что лежит."),
            "parameters": {"type": "object", "properties": {},
                           "required": []}}},
        {"type": "function", "function": {
            "name": "zapomnit_s_yarlykom",
            "description": (
                "Запомнить что-то надолго и повесить на это ЗАКЛАДКУ — "
                "чтобы потом достать по имени, а не угадывать слова. "
                "Вешай, когда сам считаешь важным: держится дольше "
                "обычного. Ярлыки — твои слова, сперва глянь "
                "moi_yarlyki. «От кого» — имя, если знание пришло от "
                "человека: знание одно, а чьё оно, решать тебе."),
            "parameters": {"type": "object", "properties": {
                "что": {"type": "string",
                        "description": "сам вывод, одно-два предложения"},
                "ярлыки": {"type": "string",
                           "description": "через запятую, например «дивер, ao»"},
                "от_кого": {"type": "string",
                            "description": "необязательно: имя, например «Шеф»"}},
                "required": ["что"]}}},
        {"type": "function", "function": {
            "name": "vspomnit_po_yarlyku",
            "description": (
                "Достать из своей памяти по закладке. Один ярлык даёт "
                "широко, два сужают, три бьют в точку. Можно спросить и "
                "по имени — «что мне говорил Шеф». Пусто — значит следа "
                "нет, и это честный ответ."),
            "parameters": {"type": "object", "properties": {
                "по": {"type": "string",
                       "description": "ярлык, несколько ярлыков или имя"},
                "сколько": {"type": "integer",
                            "description": "по умолчанию 6"}},
                "required": ["по"]}}},
    ]


def _chislo(x):
    return x if isinstance(x, (int, float)) and x == x else None


def ruki(symbol: str, ceh: str, slot: str, self_key: str,
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    """Собрать руки для этого трейдера. Возвращает {имя: функция}."""

    # RUKA_CHUZHAYA_PARA_V1: какую пару смотреть. Пусто — свою.
    def _para(args: dict):
        _i = str((args or {}).get("инструмент") or "").strip().upper()
        _i = "".join(ch for ch in _i if ch.isalnum() or ch in "._")[:16]
        if not _i or _i == str(symbol).strip().upper():
            return symbol, False
        return _i, True

    def _stol(args: dict) -> str:
        tf = str(args.get("этаж", "")).strip().upper()
        _sym, _chuzhaya = _para(args)   # RUKA_CHUZHAYA_PARA_V1
        try:
            import masshtab
            if not masshtab.est(tf):
                return f"Такого этажа нет: {tf}. Есть: {', '.join(masshtab.LESTNICA)}"
            import stol as _s
            t = _s.nakryt(_sym, tf, self_key=self_key)
            if _chuzhaya and not (t or {}).get("приборы"):
                return (f"котировок {_sym} {tf} в городе нет (или не "
                        f"дали) — смотреть нечего. Твоя пара — {symbol}.")
            chisla = f"=== СТОЛ · {_sym} {tf} ===\n" + _s.slovami(t)
            # STOL_S_KADROM_V1: кадр важнее чисел, и просить его
            # отдельной рукой трейдер не обязан. Рисуем этот же этаж
            # и кладём числа следом. Картинка не вышла — уходят одни
            # числа, как было: рука из-за кадра не падает.
            try:
                import grafik
                # KADR_BEZ_ALLIGATORA_V1: трейдеру — без линий
                put = grafik.kadr(_sym, tf, linii=_s_liniyami(slot))
            except Exception as _ek:
                put = None
                print(f"[СТОЛ] кадр {tf} не нарисовался ({_ek}) — только числа")
            # RUKA_CHUZHAYA_PARA_V1: подпись прямая — чей это кадр.
            # На чужую пару «домой» не досылаем: она не уходила со
            # своего рынка, а посмотрела в сторону.
            if _chuzhaya:
                if put:
                    return (f"[КАДР: {put}] ВЗЯТ РУКОЙ · {_sym} {tf} — "
                            f"посмотреть, не твоя рабочая пара ({symbol}); "
                            f"это НЕ картинка Шефа · стол ниже\n" + chisla)
                return chisla
            if put:
                return (f"[КАДР: {put}] ТВОЙ СТОЛ, взят рукой · {symbol} {tf} — "
                        f"это НЕ картинка Шефа · стол ниже\n"
                        + chisla + _domoy(tf))
            return chisla + _domoy(tf)
        except Exception as e:
            return f"стол на {tf} не накрылся: {e}"

    def _volna(args: dict) -> str:
        tf = str(args.get("этаж", "")).strip().upper()
        try:
            import masshtab
            if not masshtab.est(tf):
                return f"Такого этажа нет: {tf}"
            from feed_source import bars as _bars
            from williams_core import build_market_data
            b, point = _bars(symbol, tf, 300)
            if not b or point is None:
                return f"котировок {symbol} {tf} не дали"
            md = build_market_data(b, symbol=symbol, timeframe=tf,
                                   point=point)
            wf = (md or {}).get("wave_form") or {}
            d = {
                "этаж": tf,
                "длина_волны_баров": _chislo(wf.get("dlina")),
                "структура_читается": wf.get("struktura_chitaetsya"),
                "почему": wf.get("struktura_prichina"),
                "разворотный_бар_направление": wf.get("bdb_dir"),
                "разворотный_бар_цена": _chislo(wf.get("bdb_price")),
                # ВАЖНО: дивергенция и ангуляция живут НЕ в форме волны.
                # Проверено 15.08: в wave_form есть divergence_dir, а
                # сама дивергенция — md["divergence_ao"], ангуляция же
                # меряется резинкой Джастин (отрыв цены от Аллигатора)
                # в md["rubber_band"]. Читать их из wave_form — значит
                # вечно отдавать пустоту.
                "дивергенция_в_волне": wf.get("divergence_dir"),
                "дивергенция_AO": (md or {}).get("divergence_ao"),
                "ангуляция_отрыв_пунктов":
                    _chislo(((md or {}).get("rubber_band") or {})
                            .get("distance_now")),
                "ангуляция_доля_от_максимума":
                    _chislo(((md or {}).get("rubber_band") or {})
                            .get("tension_ratio")),
                "ангуляция_на_пике":
                    ((md or {}).get("rubber_band") or {}).get("is_peak"),
                "разворотный_бар_некрона": (md or {}).get("necron_bar"),
                "компас": (md or {}).get("global_bias"),
                "окно_измерения_баров": wf.get("window"),
            }
            return ("=== ВОЛНА · измерено, не истолковано ===\n"
                    + json.dumps(d, ensure_ascii=False, indent=1))
        except Exception as e:
            return f"волна на {tf} не померилась: {e}"

    def _dnevnik(args: dict) -> str:
        """YASHCHIK_STOLA_V1: журнал МЕСТА, а не твоя память.

        Тетрадь лежит при посте и переживает жильцов. Раньше она
        отдавалась молча, и чужие записи читались как свои — так
        новый человек на A06 выучил канон прежнего. Теперь у каждой
        записи видно автора, а сверху сказано прямо, чьё это.
        """
        n = int(args.get("сколько") or 5)
        if dnevnik_fn is None:
            return "дневник недоступен"
        try:
            zapisi = dnevnik_fn(n) or []
            if not zapisi:
                return "записей пока нет"
            _ya = (imya_zhitelya or "").strip()
            _avtory = sorted({str(z.get("кто") or z.get("житель") or "").strip()
                              for z in zapisi} - {""})
            _chuzhie = [a for a in _avtory if _ya and a != _ya]
            _shapka = (f"=== ЖУРНАЛ МЕСТА · последние {len(zapisi)} ===\n"
                       "Это записи РАБОЧЕГО МЕСТА, а не твоя память. "
                       "Место старше тебя.\n")
            if _chuzhie:
                _shapka += (f"Среди них есть чужие — писали: "
                            f"{', '.join(_chuzhie)}. Их канон это ИХ канон, "
                            f"не твой.\n")
            elif not _avtory:
                _shapka += ("Записи без подписи — старые, автор "
                            "неизвестен. Своими их не считай.\n")
            return (_shapka
                    + json.dumps(zapisi, ensure_ascii=False, indent=1)[:3000])
        except Exception as e:
            return f"журнал не прочитался: {e}"

    def _rastyanut(args: dict) -> str:
        """RASTYAZHKA_V1: возвращает МЕТКУ кадра — картинку дошлёт
        разговор. Текстом картинку не передать, а трейдеру нужно
        именно увидеть."""
        try:
            import rastyanut as _r
            d = _r.rastyanut(symbol, str(args.get("с", "")),
                             str(args.get("по", "")),
                             str(args.get("этаж", "")))
        except Exception as e:
            return f"растянуть не вышло: {e}"
        if not d.get("кадр"):
            return d.get("пояснение") or "кадр не нарисовался"
        return (f"[КАДР: {d['кадр']}] {d.get('пояснение', '')} · "
                f"с {d.get('с')} по {d.get('по')}")

    def _pokazat_etazh(args: dict) -> str:
        tf = str(args.get("этаж", "")).strip().upper()
        try:
            import masshtab
            if not masshtab.est(tf):
                return f"такого этажа нет: {tf}"
            import grafik
            # KADR_BEZ_ALLIGATORA_V1: трейдеру — без линий
            put = grafik.kadr(symbol, tf, linii=_s_liniyami(slot))
        except Exception as e:
            return f"показать {tf} не вышло: {e}"
        if not put:
            return f"котировок {symbol} {tf} не дали"
        return (f"[КАДР: {put}] {symbol} {tf}, последние 140 баров"
                + _domoy(tf))

    def _domoy(kuda_hodil: str) -> str:
        """VOZVRAT_NA_RABOCHIY_V1: сходил на чужой этаж — вот твой.

        Возвращает хвост к ответу руки: кадр рабочего этажа, чтобы
        последним перед глазами был ДОМ, а не тот этаж, куда ходили
        смотреть. Решение и вход — всегда на своём.

        Сходил на свой же (или рабочего этажа нет) — хвоста нет:
        возвращать некуда. Это же покрывает случай, когда трейдер
        сменил рабочий этаж на тот, куда пришёл, — он уже дома.
        """
        try:
            svoy = (rabochiy_etazh or "").strip().upper()
            if not svoy or svoy == (kuda_hodil or "").strip().upper():
                return ""
            import grafik
            _p = grafik.kadr(symbol, svoy, linii=_s_liniyami(slot))
            if not _p:
                return (f"\n\n(домой на {svoy} не вернулся: котировок не "
                        f"дали. Решай по своему этажу, а не по {kuda_hodil}.)")
            print(f"[ВОЗВРАТ] {slot}: посмотрел {kuda_hodil} → домой на {svoy}")
            return (f"\n\n[КАДР: {_p}] ВЕРНУЛСЯ ДОМОЙ · {symbol} {svoy} — "
                    f"твой рабочий этаж. Смотрел ты {kuda_hodil}, а решаешь "
                    f"и входишь здесь.")
        except Exception as _e:
            print(f"[ВОЗВРАТ] не вышло ({_e}) — трейдер остался на "
                  f"{kuda_hodil}")
            return ""

    def _krayniye(args: dict) -> str:
        """KRAYNIYE_TOCHKI_V1: вершина и дно. Факты, не разметка."""
        tf = str(args.get("этаж", "")).strip().upper()
        try:
            import masshtab
            if not masshtab.est(tf):
                tf = rabochiy_etazh if masshtab.est(rabochiy_etazh) else "H4"
            n = int(args.get("баров") or 140)
            _sym_k, _ = _para(args)   # RUKA_CHUZHAYA_PARA_V1
            from feed_source import bars as _bars
            b, _p = _bars(_sym_k, tf, max(n, 60))
        except Exception as e:
            return f"крайние точки не посчитались: {e}"
        if not b:
            return f"котировок {_sym_k} {tf} в городе нет (или не дали)"
        b = b[-n:]

        def _kray(kusok, imya):
            if not kusok:
                return f"{imya}: пусто"
            v = max(kusok, key=lambda x: x["high"])
            d = min(kusok, key=lambda x: x["low"])
            return (f"{imya}: вершина {v['high']} ({v.get('date')}) · "
                    f"дно {d['low']} ({d.get('date')})")

        pol = len(b) // 2
        v = max(b, key=lambda x: x["high"])
        d = min(b, key=lambda x: x["low"])
        mezhdu = abs(b.index(v) - b.index(d))
        return ("=== КРАЙНИЕ ТОЧКИ · факты, не разметка ===\n"
                f"{_sym_k} {tf}, {len(b)} баров "
                f"({b[0].get('date')} → {b[-1].get('date')})\n"
                + _kray(b, "всё окно") + "\n"
                + f"между вершиной и дном: {mezhdu} баров\n"
                + _kray(b[:pol], "первая половина") + "\n"
                + _kray(b[pol:], "вторая половина"))

    def _chisla_v_tochkah(args: dict) -> str:
        """CHISLA_V_TOCHKAH_V1: точные числа в барах, названных трейдером."""
        try:
            import masshtab
            tf = str(args.get("этаж", "")).strip().upper()
            if not masshtab.est(tf):
                tf = rabochiy_etazh if masshtab.est(rabochiy_etazh) else "H4"
            _sym_c, _ = _para(args)
            syrye = args.get("бары")
            if isinstance(syrye, list):
                daty = [str(x).strip() for x in syrye if str(x).strip()]
            else:
                daty = [x.strip() for x in str(syrye or "").replace(";", ",")
                        .split(",") if x.strip()]
            if not daty:
                return ("назови бары: даты через запятую, вид "
                        "2019.12.13 08:00, 2019.12.27 16:00")
            daty = daty[:6]
            from feed_source import bars as _bars
            b, pt = _bars(_sym_c, tf, 600)
            try:
                from hooks import _tolko_zakrytye
                b = _tolko_zakrytye(b)
            except Exception:
                pass
            # как кадр: не заглядываем вперёд бара города
            try:
                from hooks import load_trading_state as _lts
                _bg = str(((_lts() or {}).get("рынок") or {}).get("бар") or "")
                if _bg and b:
                    _do = [x for x in b if str(x.get("date", "")) <= _bg]
                    if _do:
                        b = _do
            except Exception:
                pass
            if not b:
                return f"котировок {_sym_c} {tf} в городе нет (или не дали)"
            from williams_core import compute_ao_series
            ao = compute_ao_series([x["high"] for x in b], [x["low"] for x in b])
            gde = {str(x.get("date")): i for i, x in enumerate(b)}
            z = 2 if (pt or 0) >= 0.01 else 5
            L = [f"=== ЧИСЛА В ТОЧКАХ · {_sym_c} {tf} · точно, не на глаз ==="]
            for d in daty:
                i = gde.get(d)
                if i is None:
                    den = [str(x.get("date")) for x in b
                           if str(x.get("date", "")).startswith(d[:10])][:6]
                    L.append(f"{d}: такого бара нет"
                             + (f" — в этот день есть: {', '.join(den)}"
                                if den else " (дата не та или вне истории)"))
                    continue
                x, a = b[i], ao[i]
                L.append(f"{d}: high {x['high']:.{z}f} · low {x['low']:.{z}f}"
                         f" · close {x['close']:.{z}f} · AO "
                         + (f"{a:.6f}" if a is not None else "ещё не считается"))
            L.append("Для вершины бери high, для впадины — low; AO — той же "
                     "строки. Эти числа и называй в приказе.")
            return "\n".join(L)
        except Exception as e:
            return f"числа не посчитались: {e}"

    def _moya_kartina(args: dict) -> str:
        try:
            import kartina
            return kartina.slovami(ceh, slot, symbol,
                                   kto=imya_zhitelya or "")   # KARTINA_TOLKO_SVOYO_V1
        except Exception as e:
            return f"картина не прочиталась: {e}"

    def _zapisat_v_kartinu(args: dict) -> str:
        try:
            import kartina
            ok, m = kartina.obyavit(
                ceh, slot, symbol, str(args.get("что", "")),
                kto=(imya_zhitelya or slot), cena=args.get("цена"),
                bar=str(args.get("бар", "")),
                pochemu=str(args.get("почему", "")),
                napravlenie=str(args.get("направление", "")),   # KARTINA_HOD_V1
                etazh=str(args.get("этаж", "")))
        except Exception as e:
            return f"записать не вышло: {e}"
        print(f"[КАРТИНА] {'✓' if ok else '✗'} {imya_zhitelya or slot}: {m}")
        return ("Записал(а) в твою картину. " + m) if ok else ("Не записано: " + m)

    def _uchebnik(args: dict) -> str:
        """UCHEBNIK_DISCIPLINY_V1: показать рисунок из Академии.

        Ищет по ВСЕМ дисциплинам: списка книг в коде нет, сканируется
        дерево. Появится новая книга — будет видна сразу.
        """
        o = str(args.get("о_чём", "")).strip()
        tema = str(args.get("дисциплина", "")).strip()
        try:
            import uchebnik as _u
            nashlos = _u.nayti(o, skolko=1, tema=tema)
        except Exception as e:
            return f"учебник не открылся: {e}"
        if not nashlos:
            try:
                import uchebnik as _u
                spisok = _u.temy()
            except Exception:
                spisok = ""
            gde = f" в дисциплине «{tema}»" if tema else ""
            return (f"по «{o}»{gde} рисунка не нашёл. Что есть в Академии:\n"
                    f"{spisok}")
        p, t, glava, podpis = nashlos[0]
        hvost = f" · {glava}" if glava else ""
        podp = f"\nподпись автора: {podpis}" if podpis else ""
        return f"[КАДР: {p}] учебник · {t}{hvost} · {p.name}{podp}"

    def _chemu_uchili(args: dict) -> str:
        try:
            import uchebnik as _u
            return "=== ЧЕМУ УЧАТ В АКАДЕМИИ ===\n" + _u.temy()
        except Exception as e:
            return f"дисциплины не прочитались: {e}"

    # ── RUKI_ZAKLADOK_V1: закладки ──────────────────────────
    # Ключ метки: ОБЩЕЕ (когда, откуда, от кого) + ЛИЧНОЕ (ярлыки
    # своими словами, важность своими глазами). Общее нужно, чтобы
    # город понимал всех одинаково; личное — чтобы жители отличались.
    def _dusha():
        """Движок памяти того, кто сидит в этом слоте."""
        from nositel import dusha_slota, _dvizhok
        n = dusha_slota(ceh, slot)
        if not n:
            return None
        return _dvizhok(n["носитель"]["папка"])

    def _moi_yarlyki(args: dict) -> str:
        try:
            d = _dusha()
            if d is None:
                return "память недоступна"
            spisok = d.yarlyki()
        except Exception as e:
            return f"словарь не прочитался: {e}"
        if not spisok:
            return ("Закладок пока нет. Первую заведёшь сам — "
                    "zapomnit_s_yarlykom.")
        return ("=== ТВОИ ЗАКЛАДКИ ===\n"
                + "\n".join(f"  {y} · {n}" for y, n in spisok[:40])
                + "\nБери отсюда, новый заводи только если правда новый.")

    def _zapomnit_s_yarlykom(args: dict) -> str:
        chto = str(args.get("что") or "").strip()
        if not chto:
            return "нечего запоминать: пусто"
        try:
            d = _dusha()
            if d is None:
                return "память недоступна"
            res = d.otmetit_yarkim(
                chto[:600], otkuda="работа",
                yarlyki=args.get("ярлыки"),
                ot_kogo=str(args.get("от_кого") or "").strip())
        except TypeError:
            return ("движок ещё не знает закладок — нужен "
                    "postavit_metku_klyuchom.py")
        except Exception as e:
            return f"не запомнилось: {e}"
        if res.get("дописано"):
            _y = str(args.get("ярлыки") or "").strip()
            return "Запомнил." + (f" Закладка: {_y}." if _y else "")
        return "Не записано: " + str(res.get("причина", "—"))

    def _vspomnit_po_yarlyku(args: dict) -> str:
        po = str(args.get("по") or "").strip()
        if not po:
            return "по чему вспоминать не сказано"
        try:
            d = _dusha()
            if d is None:
                return "память недоступна"
            n = int(args.get("сколько") or 6)
            nayd = d.vspomnit(po, limit=n, o_chyom="работа") or ""
        except Exception as e:
            return f"вспомнить не вышло: {e}"
        if not nayd:
            return (f"По «{po}» следа нет. Такого с тобой не было — или "
                    "ты не повесил закладку. Решай без этого.")
        return f"=== ПО ЗАКЛАДКЕ «{po}» ===\n{nayd}"

    def _razbor_struktury(args: dict) -> str:
        """RUKA_RAZBORA_V1: полка ВЕДЕНИЯ. Лежит в подпапке
        знания/ведение/ и потому НЕ грузится с остальными знаниями на
        каждом взгляде — загрузчик берёт только файлы папки, подпапки
        пропускает. Достаётся рукой, когда трейдер уже в рынке.

        Слово Шефа 08.09: «он из дальнейшего разбора, когда уже вошёл и
        видит, что правильно идёт, может определить, где он зашёл в
        своей структуре, и дальше спланировать, сколько пройти можно».
        """
        try:
            _koren = Path(__file__).resolve().parent.parent
            _p = (_koren / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh
                  / "слоты" / slot / "знания" / "ведение")
            if not _p.exists():
                return "полки ведения нет"
            _kuski = []
            for f in sorted(_p.iterdir()):
                if f.is_file() and f.suffix.lower() in (".md", ".txt"):
                    _kuski.append(f"\n\n===== {f.stem} =====\n"
                                  + f.read_text(encoding="utf-8"))
            if not _kuski:
                return "полка ведения пуста"
            return ("=== РАЗБОР СТРУКТУРЫ (для ведения, не для входа) ==="
                    + "".join(_kuski)[:6000])
        except Exception as e:
            return f"разбор не прочитался: {e}"

    itog = {"razbor_struktury": _razbor_struktury,      # RUKA_RAZBORA_V1
            "moi_yarlyki": _moi_yarlyki,                # RUKI_ZAKLADOK_V1
            "zapomnit_s_yarlykom": _zapomnit_s_yarlykom,
            "vspomnit_po_yarlyku": _vspomnit_po_yarlyku,
            "stol_na_etazhe": _stol,
            "izmerit_volnu": _volna,
            "moy_dnevnik": _dnevnik,
            "uchebnik": _uchebnik,          # UCHEBNIK_DISCIPLINY_V1
            "chemu_uchili": _chemu_uchili,
            "moya_kartina": _moya_kartina,            # KARTINA_SVOYA_V1
            "zapisat_v_kartinu": _zapisat_v_kartinu,
            "krayniye_tochki": _krayniye,      # KRAYNIYE_TOCHKI_V1
            "chisla_v_tochkah": _chisla_v_tochkah,   # CHISLA_V_TOCHKAH_V1
            "rastyanut_volnu": _rastyanut,      # RASTYAZHKA_V1
            "pokazat_etazh": _pokazat_etazh}
    itog.update(_ruka_mayaka_ruki(slot))   # RUKA_MAYAKA_V1
    itog.update(_ruka_prikaza_ruki(          # RUKA_PRIKAZA_V1
        symbol, slot, imya_zhitelya, rabochiy_etazh, ceh=ceh))   # PASPORT_RUKI_V1
    return itog


# ── RUKA_MAYAKA_V1: одна дверь наружу на весь город ──────────
def _ruka_mayaka_shema() -> list:
    try:
        import sys as _s
        from pathlib import Path as _P
        _g = str(_P(__file__).resolve().parent.parent / "ГОРОД")
        if _g not in _s.path:
            _s.path.insert(0, _g)
        import ruka_mayaka
        return ruka_mayaka.shema()
    except Exception:
        return []          # Маяка нет — руки просто не будет


def _ruka_mayaka_ruki(kto: str) -> dict:
    try:
        import sys as _s
        from pathlib import Path as _P
        _g = str(_P(__file__).resolve().parent.parent / "ГОРОД")
        if _g not in _s.path:
            _s.path.insert(0, _g)
        import ruka_mayaka
        return ruka_mayaka.ruki(kto)
    except Exception:
        return {}


# RUKI_TREYDERA_V1 - marker

# RUKA_MAYAKA_V1 - marker

# RASTYAZHKA_V1 - marker

# KRAYNIYE_TOCHKI_V1 - marker

# DOSKA_V1 - marker

# KARTINA_SVOYA_V1 - marker

# UCHEBNIK_V_RUKE_V1 - marker

# UCHEBNIK_DISCIPLINY_V1 - marker

# YASHCHIK_STOLA_V1 - marker

# RUKI_ZAKLADOK_V1 - marker

# KARTINA_HOD_V1 - marker

# RUKA_RAZBORA_V1 - marker


# ── RUKA_PRIKAZA_V1: приказ исполнителю ──────────────────────
# Единственный способ что-то СДЕЛАТЬ. Всё остальное у трейдера —
# смотреть и вспоминать. Закон Рычага: сказал, напрягся, сделал.
#
# Приказ ложится на то же табло (trading_state), которое читает
# Сергей-исполнитель, и теми же полями, что раньше писал разбор
# текста. Разница одна и главная: кладёт ТРЕЙДЕР, а не парсер.
#
# Бар рука проставляет САМА, из состояния города — трейдер не может
# ни соврать про бар, ни забыть его. Без отметки бара исполнитель
# приказ не берёт вовсе (SVEZHEST_V1).

_TABLO_PO_SLOTU = {"A06": "brut", "A07": "avan", "A08": "cons"}
# ZAYAVKA_I_SEYF_V1: MOVE_ORDER и CANCEL — руки для висящей заявки.
_PRIKAZY = ("ENTER", "WAIT", "HOLD", "MOVE_STOP", "ADD", "CLOSE",
            "MOVE_ORDER", "CANCEL")


def _ruka_prikaza_shema() -> list:
    return [
        {"type": "function", "function": {
            "name": "otdat_prikaz",
            "description": (
                "Отдать приказ исполнителю. Это ЕДИНСТВЕННЫЙ способ "
                "войти, передвинуть стоп, долить или закрыть. Сказать "
                "словами — не приказ: исполнитель слов не слышит, он "
                "читает только то, что положено этой рукой. Не позвал "
                "— ничего не произошло, сколько ни рассказывай. "
                "ENTER без направления, цены, стопа и четырёх чисел "
                "расхождения (цена_1, ao_1, цена_2, ao_2) не "
                "принимается: "
                "это не строгость, а то же правило — приказ должен "
                "быть исполним. Рука ничего не советует и не проверяет "
                "рынок: она передаёт твоё решение и отвечает, принято "
                "оно или нет."),
            "parameters": {"type": "object", "properties": {
                # HOLD_PRI_POZICII_V1: у каждого слова названо, КОГДА
                # оно уместно. Раньше «HOLD — держу как есть» стояло
                # без условия, и трейдер брал его без позиции,
                # сочиняя себе сделку, которой нет.
                "что": {"type": "string",
                        "description": ("Позиции НЕТ: ENTER — войти · "
                                        "WAIT — не работаю. "
                                        "Позиция ОТКРЫТА (есть блок "
                                        "position на столе): HOLD — держу "
                                        "как есть · MOVE_STOP — передвинуть "
                                        "стоп · ADD — долить · CLOSE — "
                                        "закрыть. Позиции нет — HOLD, "
                                        "MOVE_STOP, ADD и CLOSE сказать не "
                                        "о чем. "
                                        "Висит ЗАЯВКА (ещё не сработала): "
                                        "MOVE_ORDER — переставить её на "
                                        "новый разворотный бар (новые цена "
                                        "и стоп) · CANCEL — снять, "
                                        "передумала · WAIT — оставить "
                                        "висеть как есть. WAIT заявку НЕ "
                                        "снимает.")},
                "направление": {"type": "string",
                                "description": "LONG или SHORT (для ENTER)"},
                "цена": {"type": "number",
                         "description": "цена заявки (для ENTER)"},
                "стоп": {"type": "number",
                         "description": ("цена стопа (для ENTER): за краем "
                                         "разворотника. ZAPAS_STOPA_V1: "
                                         "город сам отодвинет его ещё на "
                                         "пятую часть риска — запас от "
                                         "выброса на несколько пунктов")},
                # CHETYRE_CHISLA_V1: по каким точкам увидела расхождение.
                # Слова «AO слабее прежнего горба» ничего не значат, пока
                # не названы места. Четыре числа — две цены и два AO с
                # ТЕХ ЖЕ мест: первая точка и вторая.
                # CHISLA_S_KADRA_V1: числа с кадра, на глаз, из одной пары.
                "цена_1": {"type": "number",
                           "description": ("для ENTER: цена в ПЕРВОЙ точке "
                                           "расхождения — вершина (вниз: "
                                           "впадина). Все четыре числа "
                                           "называй ТОЧНО, рукой chisla_v_tochkah: "
                                           "назови ей даты баров, что выбрала на "
                                           "кадре, — она отдаст их цены и AO. Бери их из ОДНОЙ "
                                           "пары: обе цены и обе ямы "
                                           "(горба) AO — с одних мест, "
                                           "точки разных пар не смешивай. "
                                           "Входишь по краю — называй пару "
                                           "у края (на кадре тонкая линия), "
                                           "по всему ходу — большую пару "
                                           "(толстая линия). "
                                           # TONKAYA_SAMA_V1
                                           "Дивер у края (тонкая линия) "
                                           "считается сам по себе: "
                                           "большой может быть и за "
                                           "краем экрана")},
                "ao_1": {"type": "number",
                         "description": ("для ENTER: AO в этой же ПЕРВОЙ "
                                         "точке — горб (яма) той же пары, "
                                         "точно, из chisla_v_tochkah")},   # CHISLA_V_TOCHKAH_V1
                "цена_2": {"type": "number",
                           "description": ("для ENTER: цена во ВТОРОЙ точке "
                                           "той же пары — новая вершина "
                                           "(впадина), дальше по ходу")},
                "ao_2": {"type": "number",
                         "description": ("для ENTER: AO в этой же ВТОРОЙ "
                                         "точке — горб (яма) под ней, той "
                                         "же пары")},
                "лот": {"type": "number", "description": "объём, если знаешь"},
                # METKA_NA_VHODE_V1: код из угла кадра. Проверка
                # зрения: его нет ни на столе, ни в знаниях.
                "метка": {"type": "string",
                          "description": ("код из левого верхнего угла "
                                          "кадра — две буквы и две цифры. "
                                          "На ENTER назови обязательно: "
                                          "это доказательство, что ты "
                                          "смотрел картинку, а не "
                                          "вспоминал правило")},
                "новый_стоп": {"type": "number",
                               "description": "для MOVE_STOP"},
                "долить": {"type": "number", "description": (
                    "для ADD — не нужно: доливок на этом месте нет")},   # UBORKA_0911_V1
                "почему": {"type": "string",
                           "description": "коротко, своими словами"}},
                "required": ["что"]}}},
    ]


def _klyuch_po_imeni(imya: str) -> str:
    """Ключ жителя. Нет модуля или нет такого — пустая строка."""
    try:
        import sys as _s
        from pathlib import Path as _P
        _g = str(_P(__file__).resolve().parent.parent / "ГОРОД")
        if _g not in _s.path:
            _s.path.insert(0, _g)
        import klyuch
        return klyuch.klyuch_zhitelya(imya)
    except Exception:
        return ""


def _ispolnitel() -> tuple:
    """(имя, ключ) того, кто сидит казначеем. Пусто — приказ всё равно
    ложится: место работает, даже когда пост пуст."""
    try:
        import sys as _s
        from pathlib import Path as _P
        _g = str(_P(__file__).resolve().parent.parent / "ГОРОД")
        if _g not in _s.path:
            _s.path.insert(0, _g)
        import rezidenty
        imya = rezidenty.kto_na_postu("контора__исполнитель") or ""
        return imya, _klyuch_po_imeni(imya)
    except Exception:
        return "", ""


def _sled_prikaza(zapis: dict) -> None:
    """След приказа — у того, КОМУ он отдан. Один факт, два ключа."""
    try:
        import json as _j
        from pathlib import Path as _P
        p = (_P(__file__).resolve().parent / "цеха" / "контора" /
             "слоты" / "исполнитель" / "данные" / "приказы.jsonl")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(_j.dumps(zapis, ensure_ascii=False) + "\n")
    except Exception:
        pass          # след не лёг — приказ всё равно отдан


def _ruka_prikaza_ruki(symbol: str, slot: str, imya_zhitelya: str,
                       rabochiy_etazh: str, ceh: str = "") -> dict:
    tablo = _klyuch_tablo(ceh, slot)   # PASPORT_RUKI_V1
    if not tablo:
        return {}     # не торговое место — руки нет

    def _chto_u_menya_est() -> str:
        """NE_ZAYDI_DVAZHDY_V1: своя заявка или позиция — словами.

        Пусто — значит руки свободны и входить можно.
        """
        try:
            from hooks import load_trading_state as _lts
            _t = _lts() or {}
            for _p in (_t.get("positions") or []):
                if str(_p.get("symbol", "")).strip().upper() != \
                        str(symbol).strip().upper():
                    continue
                _st = str(_p.get("status") or "").upper()
                if _st not in ("OPEN", "PENDING"):
                    continue
                _kto = str(_p.get("slot") or _p.get("agent") or "")
                if _kto and _kto.upper() != str(slot).upper():
                    continue
                # SVOYO_TOLKO_SVOYO_V1: своё — по номеру счёта места,
                # иначе на одной паре чужая заявка отбивает твой вход.
                try:
                    from nositel import magic_slota as _ms_sv
                    _mm_sv = _nomer_r(slot)
                except Exception:
                    _mm_sv = None
                if (_mm_sv is not None and _p.get("magic") is not None
                        and _p.get("magic") != _mm_sv):
                    continue
                _n = str(_p.get("direction") or "?").upper()
                _c = _p.get("entry")
                _s = _p.get("stop")
                _chto = ("позиция" if _st == "OPEN" else "висящая заявка")
                return (f"{_chto}: {_n} {symbol}"
                        + (f" по {_c}" if _c else "")
                        + (f", стоп {_s}" if _s else ""))
        except Exception as _e:
            print(f"[РУКА] своё не спросилось ({_e}) — пропускаю приказ")
        return ""

    def _otdat(args: dict) -> str:
        from datetime import datetime, timezone
        # POLYA_PRIKAZA_PROSHCHAYUT_V1: имя поля чистим от пробелов и
        # регистра. Первый живой приказ пришёл с полем «почему » — с
        # пробелом на конце — и причина потерялась целиком. Имя РУКИ
        # поиск уже прощает; имена полей сверялись знак в знак, а это
        # та же болезнь этажом ниже. Значения не трогаем: прощаем
        # описку в имени, ничего не выдумывая за трейдера.
        args = {str(_k).strip().lower(): _v
                for _k, _v in (args or {}).items()}
        _faza_zapisat(tablo, args)   # FAZA_HODA_V1
        _alli_zapisat(tablo, args)   # ALLIGATOR_OPYT_V1
        _cherez_zapisat(tablo, args)   # CHEREZ_ETAZH_V1
        _hm_vyzov("zapisat", slot, symbol, rabochiy_etazh, tablo, args)   # HOD_MESYACA_V1
        chto = str(args.get("что", "")).upper().strip()
        if chto not in _PRIKAZY:
            return ("Такого приказа нет: " + (chto or "пусто") +
                    ". Есть: " + ", ".join(_PRIKAZY) + ". Ничего не отдано.")
        # VEDENIE_SDELKI_V1: в сделке — решение с обоснованием (только A08)
        _obosn = _vs_vyzov(slot, symbol, rabochiy_etazh, chto, args)
        if _obosn:
            return _obosn
        # DVE_KNIGI_V1: на A08 CLOSE — решение КНИГИ МЕСТА, город ведёт свою
        if str(slot).strip().upper() in _GOROD_VEDYOT_SLOTY and chto == "CLOSE":
            try:
                _dolya = float(args.get("доля") or 1.0)
            except (TypeError, ValueError):
                _dolya = 1.0
            _dolya = max(0.05, min(1.0, _dolya))
            try:
                from hooks import load_trading_state as _lts
                _bar = str(((_lts().get("рынок") or {}).get("бар")) or "")
            except Exception:
                _bar = ""
            print(f"[КНИГА МЕСТА] 📕 CLOSE доля={_dolya:g} бар={_bar} "
                  f"символ={symbol}")
            try:   # KNIGI_V_OTCHETE_V1: решение — в стол, отчёт его прочтёт
                from hooks import load_trading_state as _lts2, save_trading_state as _sts2
                from datetime import datetime as _dt2
                _t2 = _lts2()
                _t2.setdefault("книга_места", []).append({
                    "бар": _bar, "доля": _dolya, "symbol": str(symbol),
                    "ts": _dt2.now().isoformat()})
                _sts2(_t2)
            except Exception as _e2:
                print(f"[КНИГА МЕСТА] в стол не записалось ({_e2})")
            _hv = ("Твоя книга закрыта целиком." if _dolya >= 0.999 else
                   "Остаток твоей книги живёт дальше с тем же стопом.")
            return (f"Принято как решение твоей книги: CLOSE, доля {_dolya:g} "
                    "исходной позиции. Городскую позицию это не меняет: её "
                    "ведёт город по стопу и трём условиям. " + _hv)
        # GOROD_VEDYOT_A08_V1: на A08 после входа позицию ведёт город
        if (str(slot).strip().upper() in _GOROD_VEDYOT_SLOTY
                and chto == "MOVE_STOP"):
            print(f"[ВЫХОД ГОРОДА] {slot}: {chto} не принят — позицию ведёт город")
            return ("Приказ НЕ отдан: на этом месте после входа позицию ведёт "
                    "город. Стоп стоит, где поставлен; город закроет, когда на "
                    "твоём этаже сойдутся три условия против (разворотник против, "
                    "приседающий, дивер), или по стопу. Доливает тоже город — одну "
                    "доливку, на пробой откатной вершины часовика. "
                    "Твоё — вход: заявку ставишь, переставляешь (MOVE_ORDER) и "
                    "снимаешь (CANCEL) сам. Позицию можно держать — HOLD.")

        napravlenie = str(args.get("направление", "")).upper().strip() or None
        cena = args.get("цена")
        stop = args.get("стоп")

        if chto == "ENTER":
            # NE_ZAYDI_DVAZHDY_V1: своё уже есть — второй ENTER не
            # принимаем. 12.09 трейдер вошёл четыре раза подряд в одно
            # место: его будили «заявка висит», а он разбирал график
            # заново и честно входил по правилу «сошлись — окружай».
            _moyo = _chto_u_menya_est()
            if _moyo:
                return ("Приказ НЕ отдан: у тебя УЖЕ есть " + _moyo +
                        ". Второй раз в то же место не входят. Сейчас "
                        "можно: HOLD — держать, MOVE_STOP — подвинуть "
                        "стоп, ADD — долить к этой же позиции, "
                        "CLOSE — закрыть. Если это висящая заявка: "
                        "MOVE_ORDER — переставить (новые цена и "
                        "стоп), CANCEL — снять.")
            net = []
            if napravlenie not in ("LONG", "SHORT"):
                net.append("направление (LONG или SHORT)")
            if not isinstance(cena, (int, float)):
                net.append("цена")
            if not isinstance(stop, (int, float)):
                net.append("стоп")
            # CHETYRE_CHISLA_V1: где увидела расхождение — числами.
            _tochki = {}
            for _pole in ("цена_1", "ao_1", "цена_2", "ao_2"):
                _zn = args.get(_pole)
                if isinstance(_zn, (int, float)):
                    _tochki[_pole] = float(_zn)
                else:
                    net.append(_pole)
            if net:
                return ("Приказ НЕ отдан: не хватает " + ", ".join(net) +
                        ". Войти вслепую нельзя — назови и позови снова.")
            # SVOI_CHISLA_V1: её собственные четыре числа должны
            # показывать расхождение — это её же утверждение, не
            # толкование города. LONG: цена ниже, AO выше (яма мельче).
            # SHORT: цена выше, AO ниже (горка ниже).
            _short_ch = str(napravlenie or "").upper() == "SHORT"
            _c1, _c2 = _tochki["цена_1"], _tochki["цена_2"]
            _a1, _a2 = _tochki["ao_1"], _tochki["ao_2"]
            _c_ok = (_c2 > _c1) if _short_ch else (_c2 < _c1)
            _a_ok = (_a2 < _a1) if _short_ch else (_a2 > _a1)
            if not (_c_ok and _a_ok):
                _nado = ("для SHORT цена во второй точке выше первой, а AO "
                         "ниже" if _short_ch else
                         "для LONG цена во второй точке ниже первой, а AO "
                         "выше (яма мельче)")
                _est = (f"у тебя цена {_c1} → {_c2} "
                        f"({'выше' if _c2 > _c1 else 'ниже'}), AO {_a1} → "
                        f"{_a2} ({'выше' if _a2 > _a1 else 'ниже'})")
                print(f"[СВОИ ЧИСЛА] ✗ {symbol} {rabochiy_etazh} "
                      f"{napravlenie}: {_est} — расхождения нет")
                return ("Приказ НЕ отдан: твои же четыре числа не "
                        "показывают расхождения. Нужно: " + _nado +
                        ". А " + _est + ". Посмотри кадр ещё раз: где "
                        "пара, в которой это есть? Если её нет — входа "
                        "нет.")
            # PRISEDANIE_NA_VHODE_V1 (слово Шефа 24.09: «приседающий —
            # дыры»). Приседающий — факт MFI, не толкование. Вход по
            # канону — разворотник с приседающим на нём или за один-два
            # бара до него. Нет его — вход не принимается, и город
            # говорит, где был последний, — ровно как стол.
            try:
                import stol as _stol_mod
                _pr = str(((_stol_mod.nakryt(symbol, rabochiy_etazh) or {})
                           .get("приборы") or {}).get("приседающий_бар")
                          or "")
            except Exception as _e_pr:
                _pr = ""
                print(f"[ПРИСЕД] проверить не вышло ({_e_pr}) — не мешаю")
            if _pr.startswith("нет"):
                print(f"[ПРИСЕД] ✗ {symbol} {rabochiy_etazh}: вход без "
                      f"приседающего — {_pr}")
                return ("Приказ НЕ отдан: приседающего в окне трёх баров "
                        "нет — стол говорит: «" + _pr + "». По канону вход — "
                        "разворотный бар с приседающим на нём или за один-два "
                        "бара до него (MFI.md). Посмотри стол и реши снова.")
            if _pr:
                print(f"[ПРИСЕД] ✓ {symbol} {rabochiy_etazh}: {_pr}")
            # METKA_NA_VHODE_V1: сверяем код с кадра. Вход НЕ
            # блокируем — это замер, а не запрет: сперва узнаем,
            # сколько входов сделано глазами, потом решим.
            try:
                import grafik as _gr
                # POCHINIT_SVERKI_V1: внутри руки этаж зовётся
                # rabochiy_etazh. Стояло чужое имя, взятое
                # наугад, и сверка падала на первой же строке.
                _chey = f"{symbol} {rabochiy_etazh}".strip()
                _byli = _gr.metki_kadrov(_chey)
                _skazala = str(args.get("метка") or "").strip().upper()
                if not _skazala:
                    print(f"[МЕТКА] ∅ {_chey}: метка не названа")
                elif _skazala in _byli:
                    print(f"[МЕТКА] ✓ {_chey}: назвала {_skazala} — "
                          f"на кадре была")
                else:
                    print(f"[МЕТКА] ✗ {_chey}: назвала {_skazala} — "
                          f"на кадрах: {', '.join(_byli[-4:]) or '—'}")
            except Exception as _e_mk:
                print(f"[МЕТКА] сверить не вышло ({_e_mk}) — не беда")
            # SVERKA_DIVERA_V1: город считает дивер САМ и кладёт
            # рядом со словами трейдера. Не блокирует: считает и
            # показывает, решает трейдер.
            try:
                import sverka_divera as _sd
                # POCHINIT_SVERKI_V1: то же чужое имя, та же беда.
                _d = _sd.poschitat(symbol, rabochiy_etazh, napravlenie)
                if not _d.get("ok"):
                    print(f"[ДИВЕР] ? {napravlenie}: "
                          f"{_d.get('slovami')}")
                elif _d.get("est"):
                    print(f"[ДИВЕР] ✓ {napravlenie}: есть — "
                          f"{_d.get('slovami')}")
                else:
                    print(f"[ДИВЕР] ✗ {napravlenie}: НЕТ — "
                          f"{_d.get('slovami')}")
                # CHETYRE_CHISLA_V1: её точки рядом с городскими —
                # видно, по тем же местам смотрели или по разным.
                try:
                    _nak_c = ("выше" if _tochki["цена_2"] > _tochki["цена_1"]
                              else "ниже")
                    _nak_a = ("выше" if _tochki["ao_2"] > _tochki["ao_1"]
                              else "ниже")
                    print(f"[ТОЧКИ] её: цена {_tochki['цена_1']}→"
                          f"{_tochki['цена_2']} ({_nak_c}), AO "
                          f"{_tochki['ao_1']}→{_tochki['ao_2']} ({_nak_a})")
                    if _d.get("ok") and _d.get("цена_было") is not None:
                        print(f"[ТОЧКИ] города: цена {_d.get('цена_было')}→"
                              f"{_d.get('цена_стало')}, AO "
                              f"{_d.get('ao_было')}→{_d.get('ao_стало')}")
                except Exception:
                    pass
            except Exception as _e_sd:
                print(f"[ДИВЕР] посчитать не вышло ({_e_sd}) — не беда")
            # KRAY_I_SHAPKA_V1 (слово Шефа 24.09): большой край — факт
            # цены. Пока цена не взяла прежний край большого хода, это
            # откат внутри хода, и мелкий дивер в нём — не вход.
            try:
                _sl_k = str((locals().get("_d") or {}).get("slovami")
                            or "")
            except Exception:
                _sl_k = ""
            _bolshoy_k = _sl_k.split("||")[0]
            # TONKAYA_SAMA_V1: край не взят у большой пары — отбиваем,
            # только если расхождения нет ни на одном размере.
            try:
                _est_k = any(_x.get("est") for _x in
                             ((locals().get("_d") or {}).get("пары") or []))
            except Exception:
                _est_k = False
            if _kray_ne_vzyat(_bolshoy_k) and not _est_k:   # ZAPRETY_PO_SMYSLU_V1
                print(f"[КРАЙ] ✗ {symbol} {rabochiy_etazh} "
                      f"{napravlenie}: большой край не взят — вход не "
                      f"принят")
                if _dzh(slot):   # HOD_MESYACA_V1: без «мелкий дивер — не вход»
                    return ("Приказ НЕ отдан: город расхождения не видит ни "
                            "на одном размере — ни на весь ход, ни у края. "
                            "Город: «" + _bolshoy_k.strip() + "». Дивер — "
                            "твоё условие и в откате: нужен дивер у края "
                            "своего хода. Посмотри числа ещё раз или реши "
                            "снова.")
                return ("Приказ НЕ отдан: цена прежний край большого "
                        "хода не взяла — откат ещё идёт. Город: «"
                        + _bolshoy_k.strip() + "». Пока цена не взяла "
                        "большой край, это откат внутри хода, и мелкий "
                        "дивер в нём — не вход. Жди, когда цена возьмёт "
                        "край, или реши снова.")
            # ODNA_YAMA_I_STOL_V1: город не нашёл вообще никакой пары,
            # потому что второй ямки (горки) нет — AO после отката просто
            # ползёт. Обе точки Синди тогда лежат в ОДНОЙ яме: дно и место,
            # где яма выкарабкивается. Это не дивер — сравнивать нечего.
            try:
                _dd_y = locals().get("_d") or {}
                _sl_y = str(_dd_y.get("slovami") or "")
                _net_par = not (_dd_y.get("пары") or [])
            except Exception:
                _sl_y, _net_par = "", False
            if _net_par and _vtoroy_net(_sl_y):   # ZAPRETY_PO_SMYSLU_V1
                _short_y = str(napravlenie).upper() == "SHORT"
                _odna = "одна горка" if _short_y else "одна яма"
                _dve = ("две горки с ямкой между ними" if _short_y
                        else "две ямки с горкой между ними")
                print(f"[ОДНА ЯМА] ✗ {symbol} {rabochiy_etazh} "
                      f"{napravlenie}: второй ямки нет — вход не принят")
                return ("Приказ НЕ отдан: между твоими точками AO не было "
                        f"отката — это {_odna}, сравнивать нечего. Город: «"
                        + _sl_y.strip() + "». Дивер — это " + _dve +
                        ". Жди, когда AO откатится и появится вторая.")
            # EKSTREMUM_NA_VHODE_V1 (слово Шефа 24.09: «цена не
            # экстремум»). Дивергентный бар — это и есть новый край
            # цены. Если город видит расхождение, а этот бар стоит
            # ниже вершины хода (для LONG — выше дна) — вход левый.
            try:
                _pary_e = [x for x in ((locals().get("_d") or {})
                           .get("пары") or []) if x.get("est")]
            except Exception:
                _pary_e = []
            if _pary_e:
                try:
                    from feed_source import bars as _fb_e
                    _bs_e, _pt_e = _fb_e(symbol, rabochiy_etazh, 60)
                    _bar_e = _bs_e[-1] if _bs_e else None
                except Exception as _e_e:
                    _bar_e = None
                    print(f"[ЭКСТРЕМУМ] проверить не вышло ({_e_e}) — "
                          f"не мешаю")
                _kr_e = _pary_e[-1].get("цена_стало")
                if _bar_e and isinstance(_kr_e, (int, float)):
                    _short_e = str(napravlenie).upper() == "SHORT"
                    _moy_e = _bar_e["high"] if _short_e else _bar_e["low"]
                    _dop_e = (_pt_e or 0.00001) * 0.5
                    _ne_kray = ((_moy_e < _kr_e - _dop_e) if _short_e
                                else (_moy_e > _kr_e + _dop_e))
                    # PRISEDANIE_POSLE_V1: приседающий мог прийти после
                    # разворотника — тогда заявка ставится на тот бар, он
                    # бар-два назад. Край хода среди последних трёх баров
                    # и стоп ЗА этим краем — это вход на экстремуме. Стоп
                    # не за краем — по-прежнему левый вход.
                    if _ne_kray and isinstance(stop, (int, float)):
                        _za_e = ((stop >= _kr_e - _dop_e) if _short_e
                                 else (stop <= _kr_e + _dop_e))
                        _ned_e = any(
                            ((_x["high"] >= _kr_e - _dop_e) if _short_e
                             else (_x["low"] <= _kr_e + _dop_e))
                            for _x in _bs_e[-4:])  # TRI_BARA_V2
                        if _za_e and _ned_e:
                            _ne_kray = False
                            print(f"[ЭКСТРЕМУМ] ✓ {symbol} {rabochiy_etazh}: "
                                  f"край хода {_kr_e} бар-два назад, стоп "
                                  f"за ним — вход на том разворотнике")
                    if _ne_kray:
                        _slovo = "вершина" if _short_e else "дно"
                        print(f"[ЭКСТРЕМУМ] ✗ {symbol} {rabochiy_etazh} "
                              f"{napravlenie}: бар {_moy_e}, а край хода "
                              f"{_kr_e} — вход не на экстремуме")
                        return ("Приказ НЕ отдан: цена не на экстремуме. "
                                f"{_slovo.capitalize()} хода — {_kr_e}, "
                                f"а у этого бара {_slovo} {_moy_e}. "
                                "Дивергентный бар — это и есть новый край "
                                "цены; этот разворотник стоит не на краю, "
                                "а после него. Жди разворотник на самом "
                                "экстремуме или реши снова.")
                    print(f"[ЭКСТРЕМУМ] ✓ {symbol} {rabochiy_etazh}: "
                          f"бар {_moy_e} — край хода")
        # ZAYAVKA_I_SEYF_V1: переставить или снять можно только
        # свою висящую заявку.
        if chto in ("MOVE_ORDER", "CANCEL"):
            _moyo = _chto_u_menya_est()
            if not _moyo.startswith("висящая заявка"):
                return ("Приказ НЕ отдан: висящей заявки у тебя нет"
                        + (f" (есть {_moyo})" if _moyo else "") +
                        ". " + chto + " — только для заявки, которая "
                        "ещё не сработала.")
            if chto == "MOVE_ORDER":
                _net = [p for p, z in (("цена", cena), ("стоп", stop))
                        if not isinstance(z, (int, float))]
                if _net:
                    return ("Приказ НЕ отдан: MOVE_ORDER без "
                            + ", ".join(_net) + ". Назови новые цену "
                            "и стоп заявки и позови снова.")
        if chto == "MOVE_STOP" and not isinstance(args.get("новый_стоп"),
                                                  (int, float)):
            return "Приказ НЕ отдан: MOVE_STOP без нового стопа."
        if chto == "ADD" and not isinstance(args.get("долить"), (int, float)):
            return "Приказ НЕ отдан: ADD без объёма долива."

        try:
            from hooks import load_trading_state, save_trading_state
            t = load_trading_state()
        except Exception as e:
            return f"Табло не открылось ({e}) — приказ не отдан."

        # бар город ставит сам; трейдер про него не спрашивается
        bar = str((t.get("рынок") or {}).get("бар") or t.get("бар") or "")

        v = t.setdefault(tablo, {})
        v["бар"] = bar
        v["action"] = chto
        v["verdict"] = ("APPROVED" if chto == "ENTER"
                        else ("REJECTED" if chto == "WAIT"
                              else v.get("verdict")))
        v["reason"] = str(args.get("почему", "")).strip()
        if chto == "CLOSE":   # DVE_KNIGI_V2: доля исходной позиции едет в поле «объём»
            try:
                _sh = float(args.get("доля") or 1.0)
            except (TypeError, ValueError):
                _sh = 1.0
            _sh = max(0.05, min(1.0, _sh))
            v["add_lot"] = (round(_sh, 4) if _sh < 0.999 else None)
            if _dzh(slot):
                print(f"[КНИГА МЕСТА] 📕 приказ CLOSE доля={_sh:g} бар={bar} символ={symbol}")
        if chto == "ADD" and _dzh(slot):
            print(f"[КНИГА МЕСТА] 📗 приказ ADD нога={args.get('долить')} бар={bar} символ={symbol}")
            if isinstance(args.get("новый_стоп"), (int, float)):
                v["new_stop"] = args["новый_стоп"]
        if chto == "MOVE_STOP" and _dzh(slot):
            print(f"[КНИГА МЕСТА] 📘 приказ MOVE_STOP → {args.get('новый_стоп')} бар={bar} символ={symbol}")
        if chto == "WAIT":
            # не работаю — значит и цены моей на табло нет. Иначе
            # вчерашняя цена лежит рядом с сегодняшним отказом и
            # ждёт, пока кто-нибудь её подберёт.
            for pole in ("direction", "entry", "stop", "lot",
                         "new_stop", "add_lot"):
                v.pop(pole, None)
        if chto == "ENTER":
            v["direction"] = napravlenie
            v["entry"] = cena
            v["stop"] = stop
            if isinstance(args.get("лот"), (int, float)):
                v["lot"] = args["лот"]
        if chto == "MOVE_STOP":
            v["new_stop"] = args.get("новый_стоп")
        if chto == "MOVE_ORDER":
            v["entry"] = cena
            v["stop"] = stop
        if chto == "ADD":
            v["add_lot"] = args.get("долить")
        v["отдан_рукой"] = True
        v["кто_отдал"] = imya_zhitelya or ""
        v["ключ_отдавшего"] = _klyuch_po_imeni(imya_zhitelya)

        try:
            save_trading_state(t)
        except Exception as e:
            return f"Табло не записалось ({e}) — приказ не отдан."

        komu, klyuch_komu = _ispolnitel()
        _sled_prikaza({
            "когда": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "бар": bar,
            "инструмент": symbol,
            "этаж": rabochiy_etazh,
            "место": slot,
            "от_кого": imya_zhitelya or "",
            "ключ": v["ключ_отдавшего"],
            "кому": komu,
            "ключ_кому": klyuch_komu,
            "что": chto,
            "направление": napravlenie,
            "цена": cena,
            "стоп": stop,
            "лот": args.get("лот"),
            "новый_стоп": args.get("новый_стоп"),
            "долить": args.get("долить"),
            "почему": v["reason"],
        })

        adresat = komu or "исполнитель"
        if chto == "ENTER":
            return (f"Приказ отдан: {adresat} принял ENTER {napravlenie} "
                    f"{symbol} по {cena}, стоп {stop}"
                    + (f", бар {bar}" if bar else "")
                    + ". Заявка на табло."
                    + _hm_vyzov("metka_vhoda", slot, symbol, napravlenie, bar))   # HOD_MESYACA_V1
        if chto == "MOVE_ORDER":
            return (f"Приказ отдан: {adresat} переставит заявку на "
                    f"{cena}, стоп {stop}"
                    + (f", бар {bar}" if bar else "") + "."
                    + _hm_vyzov("zayavka_perestavlena", slot, symbol, bar))   # HOD_MESYACA_V1
        if chto == "CANCEL":
            return (f"Приказ отдан: {adresat} снимет заявку"
                    + (f", бар {bar}" if bar else "") + "."
                    + _hm_vyzov("snyatie", slot, symbol, v.get("reason"), bar))   # HOD_MESYACA_V1
        if chto == "WAIT":
            return f"Принято: не работаешь на этом баре{', ' + bar if bar else ''}."
        return (f"Приказ отдан: {adresat} принял {chto}"
                + (f", бар {bar}" if bar else "") + ".")

    return {"otdat_prikaz": _otdat}


# RUKA_PRIKAZA_V1 - marker

# RUKA_CHUZHAYA_PARA_V1 - marker

# ODNO_PRAVILO_RB_V1 - marker


# ── FAZA_HODA_V1: фаза хода на табло ──────────────────────────
# Опыт второго уровня (A07). Фаза — не часть приказа: она ложится на
# табло СРАЗУ, ещё до проверок, чтобы не пропасть, если сам приказ не
# принят. Полей фазы нет (у A06 их и не предлагают) — ничего не делаем.
_FAZA_POLYA = ("ход", "начало_хода", "фаза", "уверенность", "почему_фаза")


def _faza_zapisat(tablo: str, args: dict) -> None:
    try:
        if not any(str((args or {}).get(p) or "").strip()
                   for p in _FAZA_POLYA):
            return
        from hooks import load_trading_state, save_trading_state
        t = load_trading_state()
        bar = str((t.get("рынок") or {}).get("бар") or t.get("бар") or "")
        z = {"бар": bar}
        for p in _FAZA_POLYA:
            z[p] = str((args or {}).get(p) or "").strip()
        t.setdefault(tablo, {})["фаза"] = z
        save_trading_state(t)
        print(f"[ФАЗА] {tablo}: ход {z['ход'] or '—'} с "
              f"{z['начало_хода'] or '—'} · {z['фаза'] or '—'} "
              f"({z['уверенность'] or '—'})")
    except Exception as _e:
        print(f"[ФАЗА] не записалась ({_e}) — приказ идёт как есть")


# FAZA_HODA_V1 - marker

# KARTINA_TOLKO_SVOYO_V1 - marker


# ── ARHIV_RUKI_V1: рука «из архива» ──────────────────────────
# Слово Шефа (01.10): чужой опыт — по просьбе, если своего мало, «но
# не всегда»; перед показом — «это не источник, а опыт». Правило живёт
# в Биржа/arhiv_birzhi.py (iz_arhiva), здесь только дверь.
_ARHIV_SHEMA = {"type": "function", "function": {
    "name": "iz_arhiva",
    "description": (
        "Достать из Архива Биржи похожие места из прошлых прогонов: где "
        "это было, что ты решала, какими словами, что сказал судья фаз. "
        "Сперва — ТВОЁ. Если своего мало, архив добавит немного чужого "
        "опыта, с предупреждением: это не источник и не правило, а "
        "чей-то опыт; источник — твои знания. По твоей паре — только то, "
        "что на рынке было раньше текущего бара."),
    "parameters": {"type": "object", "properties": {
        "что": {"type": "string",
                "description": ("словами, что ищешь: например «пятая GBPUSD "
                                "D1», «край», «свои числа», «дивер вход»")}},
        "required": ["что"]}}}

_shema_bez_arhiva = shema


def shema(rabochiy_etazh: str = "") -> list:      # noqa: F811
    s = _shema_bez_arhiva(rabochiy_etazh)
    s.append(_ARHIV_SHEMA)
    return s


_ruki_bez_arhiva = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_bez_arhiva(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                         rabochiy_etazh=rabochiy_etazh,
                         imya_zhitelya=imya_zhitelya)

    def _iz_arhiva(args: dict) -> str:
        try:
            import arhiv_birzhi as _ab
            from hooks import load_trading_state as _lts
            bar = str(((_lts() or {}).get("рынок") or {}).get("бар") or "")
            return _ab.iz_arhiva(str((args or {}).get("что") or ""),
                                 imya_zhitelya or "", symbol, bar, slot)
        except Exception as e:
            return f"архив не открылся: {e}"

    r["iz_arhiva"] = _iz_arhiva
    return r


# ARHIV_RUKI_V1 - marker

# SVOYO_TOLKO_SVOYO_V1 - marker


# ── ZAPRETY_PO_SMYSLU_V1: сверку узнаём по смыслу, не по точной фразе ──
# 02.10: Брат переписал слова сверки («цена край своего хода не взяла»,
# «второй горки ещё нет»), а запреты искали старые фразы знак в знак —
# и молча перестали срабатывать. Теперь узнают и старые, и новые.
import re as _re_zp


def _kray_ne_vzyat(s) -> bool:
    """«цена прежний край не взяла» / «цена край своего хода не взяла»."""
    return bool(_re_zp.search(r"край(?:\s+своего\s+хода)?\s+не\s+взял",
                              str(s or "")))


def _vtoroy_net(s) -> bool:
    """«второй ямки нет» / «второй горки ещё нет» / «второй ещё нет»."""
    return bool(_re_zp.search(
        r"втор(?:ой|ая)\s+(?:(?:ямки|горки)\s+)?(?:ещё\s+)?нет",
        str(s or "")))


# ZAPRETY_PO_SMYSLU_V1 - marker


# ── ALLIGATOR_OPYT_V1: ответ «где ты по Аллигатору» — на табло ──
# Как фаза: ложится сразу, до проверок приказа. Нет полей — ничего.
_ALLI_POLYA = ("аллигатор", "движение")


def _alli_zapisat(tablo: str, args: dict) -> None:
    try:
        if not any(str((args or {}).get(p) or "").strip() for p in _ALLI_POLYA):
            return
        from hooks import load_trading_state, save_trading_state
        t = load_trading_state()
        bar = str((t.get("рынок") or {}).get("бар") or t.get("бар") or "")
        z = {"бар": bar}
        for p in _ALLI_POLYA:
            z[p] = str((args or {}).get(p) or "").strip()
        t.setdefault(tablo, {})["аллигатор"] = z
        save_trading_state(t)
        print(f"[АЛЛИГАТОР] {tablo}: {z['аллигатор'] or '—'} · {z['движение'] or '—'}")
    except Exception as _e:
        print(f"[АЛЛИГАТОР] не записался ({_e}) — приказ идёт как есть")


# ALLIGATOR_OPYT_V1 - marker


# ── LINII_A08_V1: кому рисовать линии Аллигатора на кадрах рук ──
# KADR_BEZ_ALLIGATORA_V1 (03.10) задуман для первого уровня, а рисовал
# без линий всем. На A08 идёт опыт «где ты по Аллигатору» (05.10) —
# там линии нужны. Остальным — как было.
_S_LINIYAMI = {"A08"}


def _s_liniyami(slot) -> bool:
    return _dzh(slot) or str(slot or "").strip().upper() in _S_LINIYAMI   # MESTA_PO_POMETKE_V1


# LINII_A08_V1 - marker


# ── GOROD_VEDYOT_A08_V1: места, где позицию после входа ведёт город ──
_GOROD_VEDYOT_SLOTY = set()   # DVE_KNIGI_V2: житель ведёт сам, ограничений рук на A08 нет


# GOROD_VEDYOT_A08_V1 - marker


# ── CHEREZ_ETAZH_V1: ответ «через этаж» — на табло ────────────
# Как фаза и Аллигатор: ложится сразу, до проверок приказа.
_CHEREZ_POLYA = ("через_этаж_ход", "через_этаж", "ожидание")   # OZHIDANIE_V1


def _cherez_zapisat(tablo: str, args: dict) -> None:
    try:
        if not any(str((args or {}).get(p) or "").strip() for p in _CHEREZ_POLYA):
            return
        from hooks import load_trading_state, save_trading_state
        t = load_trading_state()
        bar = str((t.get("рынок") or {}).get("бар") or t.get("бар") or "")
        z = {"бар": bar}
        for p in _CHEREZ_POLYA:
            z[p] = str((args or {}).get(p) or "").strip()
        t.setdefault(tablo, {})["через_этаж"] = z
        save_trading_state(t)
        print(f"[ЧЕРЕЗ ЭТАЖ] {tablo}: {z['через_этаж_ход'] or '—'} · "
              f"{z['через_этаж'] or '—'} · ждёт {z['ожидание'] or '—'}")
    except Exception as _e:
        print(f"[ЧЕРЕЗ ЭТАЖ] не записался ({_e}) — приказ идёт как есть")


# CHEREZ_ETAZH_V1 - marker


# LYUBOY_ETAZH_V1 - marker


# ══ CHISTKA_DOLIVOK_V1 (30.10): здесь была старая доливка — выброшена ══
# Слово Шефа: «старые доливки выбросить, почистить совсем». Метка ниже
# оставлена, чтобы старый патч не вписал её обратно.
# DOLIVKA_DZHEMA_V1 - marker

# DOLIVKA_STOP_GORODA_V1 - marker

# ODNA_DOLIVKA_V1 - marker

# OZHIDANIE_V1 - marker

# DVE_KNIGI_V1 - marker

# KNIGI_V_OTCHETE_V1 - marker

# DVE_KNIGI_V2 - marker


# ── HOD_MESYACA_V1: история хода месяца — дверь в Биржа/hod_mesyaca.py ──
# Только A08 (модуль сам проверяет место). Не вышло — приказ идёт как есть.
def _hm_vyzov(imya, *a, **k) -> str:
    try:
        import hod_mesyaca as _hm
        return getattr(_hm, imya)(*a, **k) or ""
    except Exception as _e:
        print(f"[ХОД МЕСЯЦА] {imya} не вышло ({_e}) — приказ идёт как есть")
        return ""


# HOD_MESYACA_V1 - marker


# ── TRI_STOPA_SMOTRI_V1: после трёх стопов — сперва посмотреть младший ──
# Слово Шефа 16.10: «он не просто проговорить и продолжить после третьего
# стопа должен, а посмотреть, что по этажам, — а там на H1 явно картина
# маслом». Руки, которые показывают этаж, отмечают взгляд (какой этаж, на
# каком баре). После трёх стопов подряд в одну сторону ENTER в ту же
# сторону проходит дальше, только если на этом баре он открыл этаж ниже
# рабочего. Не запрет торговать — запрет входить не глядя. Только A08.
_ruki_bez_smotra = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_bez_smotra(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                         rabochiy_etazh=rabochiy_etazh,
                         imya_zhitelya=imya_zhitelya)
    if not _dzh(slot):
        return r

    def _s_otmetkoy(imya_ruki, fn):
        def _f(args):
            try:
                a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
                e = str(a.get("этаж") or "").strip()
                if imya_ruki == "rastyanut_volnu" and not e:
                    e = "растяжка"
                _chuzh = str(a.get("инструмент") or "").strip().upper()
                if e and (not _chuzh or _chuzh == str(symbol).strip().upper()):
                    _hm_vyzov("otmetit_vzglyad", slot, symbol, e)
            except Exception:
                pass
            return fn(args)
        return _f

    for _imya in ("stol_na_etazhe", "pokazat_etazh", "rastyanut_volnu",
                  "izmerit_volnu"):
        if _imya in r:
            r[_imya] = _s_otmetkoy(_imya, r[_imya])

    # SVERKA_S_GORODOM_V1: рука сверки — сперва своё, потом город
    r["sverka_s_gorodom"] = lambda args: (_hm_vyzov(
        "sverka", slot, symbol, rabochiy_etazh, args) or "сверка не вышла")

    if "otdat_prikaz" in r:
        _orig = r["otdat_prikaz"]

        def _otdat_smotri(args):
            try:
                a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
                if str(a.get("что") or "").upper().strip() == "ENTER":
                    # SVERKA_S_GORODOM_V1 (слово Шефа 17.10): город не решает
                    # за него — не отказываем, только отмечаем, смотрел ли он
                    _pros = _hm_vyzov("prosba_posmotret", slot, symbol,
                                      a.get("направление"))
                    if _pros:
                        print("[ТРИ СТОПА] вход без взгляда на младший — не держу, отмечаю")
            except Exception as _e:
                print(f"[ТРИ СТОПА] проверка не вышла ({_e}) — приказ идёт как есть")
            return _orig(args)

        r["otdat_prikaz"] = _otdat_smotri
    return r


# TRI_STOPA_SMOTRI_V1 - marker

# SVERKA_S_GORODOM_V1 - marker


# ── VEDENIE_SDELKI_V1: решение в сделке — с обоснованием ─────────
# Слово Шефа 17.10: «город показывает, житель решает и обосновывает каждое
# решение». Правило живёт в Биржа/vedenie_sdelki.py, здесь только дверь.
# Не вышло — приказ идёт как есть.
def _vs_vyzov(slot, symbol, tf, chto, args) -> str:
    try:
        import vedenie_sdelki as _vs
        return _vs.obosnovanie(slot, symbol, tf, chto, args) or ""
    except Exception as _e:
        print(f"[ВЕДЕНИЕ] проверка не вышла ({_e}) — приказ идёт как есть")
        return ""


# VEDENIE_SDELKI_V1 - marker


# ── MESTA_PO_POMETKE_V1: место уровня «продвинутый новичок» и его номер — по паспорту цеха ──
def _dzh(slot) -> bool:
    try:
        import mesto_urovnya as _md
        return _md.eto_mesto_urovnya(slot)
    except Exception:
        return str(slot or "").strip().upper() == "A08"


def _nomer_r(slot):
    try:
        import mesto_urovnya as _md
        return _md.nomer_mesta(slot)
    except Exception:
        try:
            from nositel import magic_slota
            return magic_slota("торговый_хаос", slot)
        except Exception:
            return None


# ══ PASPORT_RUKI_V1 — ключ табло для руки приказа из паспорта цеха ══
# Старый цех торговый_хаос — прежняя таблица (A06→brut, A07→avan,
# A08→cons), как было. Другой цех — ключ из его паспорта (поле «ключ»
# у места), тем же правилом, что у Совета и исполнителя: нет «ключа» —
# имя места маленькими. Места нет ни в паспорте, ни мозга у него —
# не торговое место, руки нет.
def _klyuch_tablo(ceh, slot) -> str:
    s = str(slot or "").strip()
    c = str(ceh or "").strip()
    if not c or c == "торговый_хаос":
        return _TABLO_PO_SLOTU.get(s.upper(), "")
    korn = _BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / c
    try:
        man = json.loads((korn / "manifest.json").read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[РУКА] паспорт цеха {c} не прочёлся ({e}) — руки приказа нет")
        return ""
    for z in man.get("слоты") or []:
        if str(z.get("слот") or "").strip() == s:
            return str(z.get("ключ") or s).strip().lower()
    if (korn / "слоты" / s / "мозг.py").exists():
        return s.lower()
    return ""


# PASPORT_RUKI_V1 - marker


# ══ MESTO_BEZ_IMENI_V1 — поле места: новое имя, старые записи читаются ══
def _pole_mesta(d, imya):
    try:
        import mesto_urovnya as _mu_p
        return _mu_p.pole(d, imya)
    except Exception:
        return (d or {}).get(imya)


# MESTO_BEZ_IMENI_V1 - marker


# ══ POLKA_KLYUCHI_V1 — её полка: общие ключи в закладках, открытия пишутся ══
_ruki_bez_polki = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_bez_polki(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                        rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    try:
        import opyt_stola as _os
        if not _os.vklyucheno(ceh, slot):
            return r
    except Exception:
        return r

    def _god_run():
        try:
            from hooks import load_trading_state as _lts
            t = _lts() or {}
            run = (t.get("прогон") or {}).get("id")
            bar = str((t.get("рынок") or {}).get("бар") or "")
            return (bar[:4] if run and bar[:4].isdigit() else None), run, bar
        except Exception:
            return None, None, ""

    _vsp = r.get("vspomnit_po_yarlyku")
    _my = r.get("moi_yarlyki")

    def _vspomnit(args):
        po = str((args or {}).get("по") or "")
        kl = _os.klyuchi_v_tekste(po)
        god, run, bar = _god_run()
        verh = []
        for k in kl:
            verh.append(_os.kartochka(imya_zhitelya, k, god, run))
            _os.otmetit_klyuch(ceh, slot, k, bar)
            print(f"[КЛЮЧ] {slot} {imya_zhitelya}: открыт ключ «{k}» (бар {bar})")
        niz = _vsp(args) if _vsp else ""
        return ("\n\n".join(verh) + ("\n\n" if verh and niz else "") + (niz or "")) or niz

    def _moi(args):
        verh = _my(args) if _my else ""
        god, run, _bar = _god_run()
        og = _os.oglavlenie(imya_zhitelya, god, run)
        if og:
            verh = (verh + "\n\n=== ОБЩИЕ КЛЮЧИ ГОРОДА — ПОД НИМИ ТВОЙ ОПЫТ СДЕЛОК ===\n"
                    + "\n".join(og)
                    + "\nОткрыть — vspomnit_po_yarlyku, по: ключ.")
        return verh

    if _vsp:
        r["vspomnit_po_yarlyku"] = _vspomnit
    if _my:
        r["moi_yarlyki"] = _moi
    return r


# POLKA_KLYUCHI_V1 - marker


# ══ BIBLIOTEKA_MESTA_V1 — рука ключей на любом торговом месте ══
# По ключу: книга места (литература любого, кто сидит) + её опыт сделок (карантин
# года) + её память. Словарь: её три полки и библиотека места.
_ruki_do_biblioteki = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_biblioteki(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                            rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    try:
        import opyt_stola as _os
    except Exception:
        return r

    def _god_run():
        try:
            from hooks import load_trading_state as _lts
            t = _lts() or {}
            run = (t.get("прогон") or {}).get("id")
            bar = str((t.get("рынок") or {}).get("бар") or "")
            return (bar[:4] if run and bar[:4].isdigit() else None), run, bar
        except Exception:
            return None, None, ""

    def _dvig():
        try:
            from nositel import dusha_slota as _ds, _dvizhok as _dv
            n = _ds(ceh, slot)
            return _dv(n["носитель"]["папка"]) if n else None
        except Exception:
            return None

    def _vspomnit(args):
        a = args or {}
        po = str(a.get("по") or "").strip()
        if not po:
            return "по чему вспоминать не сказано"
        god, run, bar = _god_run()
        verh = []
        for k in _os.klyuchi_zaprosa(ceh, slot, po):
            km = _os.kartochka_mesta(ceh, slot, k)
            if km:
                verh.append(km)
            ko = _os.kartochka_opyta(imya_zhitelya, k, god, run)
            if ko:
                verh.append(ko)
            _os.otmetit_klyuch(ceh, slot, k, bar)
            print(f"[КЛЮЧ] {slot} {imya_zhitelya}: открыт ключ «{k}» (бар {bar})")
        d = _dvig()
        try:
            niz = d.vspomnit(po, limit=int(a.get("сколько") or 6), o_chyom="работа") if d else ""
        except Exception:
            niz = ""
        out = verh + ([f"=== ТВОЯ ПАМЯТЬ ПО «{po}» ===\n{niz}"] if niz else [])
        return "\n\n".join(out) or (f"По «{po}» ничего нет — ни в библиотеке места, "
                                      "ни у тебя. Решай без этого.")

    def _moi(args):
        d = _dvig()
        s = ""
        try:
            s = d.polki_v_promt() if d and hasattr(d, "polki_v_promt") else ""
        except Exception:
            s = ""
        lib = _os.klyuchi_mesta(ceh, slot)
        if lib:
            s += ("\n=== БИБЛИОТЕКА МЕСТА — литература любого, кто здесь сидит ===\n  "
                  + ", ".join(lib) + "\nОткрыть — vspomnit_po_yarlyku, по: ключ.\n")
        return s or "Ключей пока нет."

    r["vspomnit_po_yarlyku"] = _vspomnit
    r["moi_yarlyki"] = _moi
    return r


# BIBLIOTEKA_MESTA_V1 - marker


# ══ D01_KAK_A06_V1 — выход по месту: стоп не двигают, «место» в сделке ══
def _po_mestu(ceh, slot) -> bool:
    try:
        man = json.loads((_BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / str(ceh)
                          / "manifest.json").read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper():
                return str(z.get("выход") or "").strip().lower() == "по месту"
    except Exception:
        pass
    return False


_shema_do_mesta = shema


def shema(rabochiy_etazh: str = "") -> list:   # noqa: F811
    s = _shema_do_mesta(rabochiy_etazh)
    for f in s:
        fn = (f or {}).get("function") or {}
        if fn.get("name") == "otdat_prikaz":
            fn.setdefault("parameters", {}).setdefault("properties", {})["место"] = {
                "type": "string",
                "description": ("в сделке (HOLD, CLOSE, ADD): где ты оказалась после входа — "
                                "откат, по ходу или перелом — и почему, по старшему этажу. "
                                "На месте с выходом по месту — обязательно")}
    return s


_ruki_do_mesta = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_mesta(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                       rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    if "otdat_prikaz" not in r or not _po_mestu(ceh, slot):
        return r
    _orig = r["otdat_prikaz"]

    def _otdat_po_mestu(args):
        a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
        chto = str(a.get("что") or "").upper().strip()
        if chto == "MOVE_STOP":
            print(f"[МЕСТО] ✗ {slot}: MOVE_STOP не принят — стоп не двигают")
            return ("Приказ НЕ отдан: на этом месте стоп не двигают — ни код, ни ты. "
                    "Он стоит там, где поставлен при входе (слово Шефа). Выход — по "
                    "месту: откат — встречный разворотник с приседающим в заметном "
                    "плюсе; по ходу и перелом — дивер против сделки на рабочем. "
                    "Можно HOLD, CLOSE или ADD.")
        if chto in ("HOLD", "CLOSE", "ADD"):
            mesto = str(a.get("место") or "").strip()
            gorod = ""
            try:
                import vedenie_sdelki as _vs
                from hooks import load_trading_state as _lts
                moy = _nomer_r(slot)
                poz = next((p for p in ((_lts() or {}).get("positions") or [])
                            if str(p.get("status") or "").upper() == "OPEN"
                            and p.get("magic") == moy), None)
                if poz:
                    nap = "LONG" if str(poz.get("direction") or "").upper() == "LONG" else "SHORT"
                    gorod = str(_vs._scenariy(slot, symbol, nap) or "")
            except Exception:
                poz = True
            if poz and len(mesto) < 5:
                print(f"[МЕСТО] ✗ {slot} {chto}: «место» не названо")
                return ("Приказ НЕ отдан: назови «место» — где ты оказалась после входа: "
                        "откат, по ходу или перелом, и почему (посмотри старший этаж: ход и "
                        "дивер на нём)."
                        + (f" Город считает: {gorod}." if gorod else "")
                        + _vyhod_po_mestu_tekst(ceh, slot))   # VEDENIE_MASSHTAB_V3
            if poz:
                try:
                    from hooks import load_trading_state as _lts2
                    bar = str(((_lts2() or {}).get("рынок") or {}).get("бар") or "")
                    p = (_BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / str(ceh)
                         / "слоты" / str(slot) / "данные" / "место_в_сделке.jsonl")
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with open(p, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"бар": bar, "что": chto, "её": mesto[:300],
                                            "город": gorod}, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                print(f"[МЕСТО] {slot} {chto}: её «{mesto[:80]}» · город: {gorod or '—'}")
        return _orig(args)

    r["otdat_prikaz"] = _otdat_po_mestu
    return r


# D01_KAK_A06_V1 - marker


# ══ OPYT_NA_STOLE_V1 — опыт на столе; сила входа пишется на входе ══
_ruki_do_opyta_na_stole = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_opyta_na_stole(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                                rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    try:
        import opyt_stola as _os
    except Exception:
        return r

    def _god_run():
        try:
            from hooks import load_trading_state as _lts
            t = _lts() or {}
            run = (t.get("прогон") or {}).get("id")
            bar = str((t.get("рынок") or {}).get("бар") or "")
            return (bar[:4] if run and bar[:4].isdigit() else None), run, bar, t
        except Exception:
            return None, None, "", {}

    def _v_sdelke(t):
        moy = _nomer_r(slot)
        return any(str(p.get("status") or "").upper() == "OPEN" and p.get("magic") == moy
                   for p in (t.get("positions") or []))

    def _napr_razvorota():
        try:
            from feed_source import bars as _bars
            from williams_core import compute_alligator, vse_necron
            bs, point = _bars(symbol, rabochiy_etazh, 300)
            try:
                from hooks import _tolko_zakrytye
                bs = _tolko_zakrytye(bs)
            except Exception:
                pass
            n = len(bs or [])
            if n < 40:
                return None
            al = compute_alligator([b["high"] for b in bs], [b["low"] for b in bs], point=point)
            nec = {x["i"]: x["сторона"] for x in vse_necron(
                bs, al.get("jaw_series"), al.get("teeth_series"), al.get("lips_series"),
                s=max(1, n - 6))}
            for i in range(n - 1, n - 5, -1):
                if nec.get(i) in ("BULL", "BEAR"):
                    return "LONG" if nec[i] == "BULL" else "SHORT"
        except Exception:
            return None
        return None

    if "stol_na_etazhe" in r:
        _stol0 = r["stol_na_etazhe"]

        def _stol_s_opytom(args):
            out = _stol0(args)
            try:
                a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
                tf = str(a.get("этаж") or "").strip().upper()
                para = str(a.get("инструмент") or "").strip().upper()
                if tf != str(rabochiy_etazh).upper() or (para and para != str(symbol).upper()):
                    return out
                god, run, bar, t = _god_run()
                if _v_sdelke(t):
                    L = _os.stroki_sdelki(imya_zhitelya, god, run)
                else:
                    napr = _napr_razvorota()
                    if not napr:
                        return out
                    k, n = _os.sila_divera(symbol, rabochiy_etazh, napr)
                    L = _os.stroki_vhoda(imya_zhitelya, k, n, god, run)
                if L:
                    print(f"[ОПЫТ] {slot} {imya_zhitelya}: на столе {len(L) - 2} строк опыта")
                    return out + "\n\n" + "\n".join(L)
            except Exception as e:
                print(f"[ОПЫТ] на стол не лёг ({e})")
            return out

        r["stol_na_etazhe"] = _stol_s_opytom

    if "otdat_prikaz" in r:
        _prikaz0 = r["otdat_prikaz"]

        def _prikaz_s_siloy(args):
            otv = _prikaz0(args)
            try:
                a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
                if (str(a.get("что") or "").upper().strip() == "ENTER"
                        and str(otv).startswith("Приказ отдан")):
                    napr = str(a.get("направление") or "").upper().strip()
                    k, n = _os.sila_divera(symbol, rabochiy_etazh, napr)
                    _g, run, bar, _t = _god_run()
                    _os.zapisat_vhod(ceh, slot, {"прогон": run, "бар": bar, "направление": napr,
                                                 "k": k, "n": n, "откуда": "рука"})
                    print(f"[ОПЫТ] {slot}: вход {napr} — дивер на {k} из {n} размеров")
            except Exception:
                pass
            return otv

        r["otdat_prikaz"] = _prikaz_s_siloy
    return r


# OPYT_NA_STOLE_V1 - marker


# ══ OSMYSLENIE_EPIZODA_V1 — на входе рука запоминает её «почему» ══
_ruki_do_pochemu = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_pochemu(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                         rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    if "otdat_prikaz" not in r:
        return r
    _p0 = r["otdat_prikaz"]

    def _prikaz_s_pochemu(args):
        otv = _p0(args)
        try:
            a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
            if (str(a.get("что") or "").upper().strip() == "ENTER"
                    and str(otv).startswith("Приказ отдан")):
                import opyt_stola as _os
                from hooks import load_trading_state as _lts
                t = _lts() or {}
                _os.zapisat_pochemu(ceh, slot, {
                    "прогон": (t.get("прогон") or {}).get("id"),
                    "бар": str((t.get("рынок") or {}).get("бар") or ""),
                    "направление": str(a.get("направление") or "").upper().strip(),
                    "почему": str(a.get("почему") or "")[:600]})
        except Exception:
            pass
        return otv

    r["otdat_prikaz"] = _prikaz_s_pochemu
    return r


# OSMYSLENIE_EPIZODA_V1 - marker


# ══ TRI_SLOVA_V1 — в сделке: месяц на каждом пробуждении и одно из трёх слов ══
# Слово Шефа 27.10: «про волны убрать пока, сейчас важно откат, продолжение,
# перелом — чтобы эти три момента чётко уяснили, и каждый раз месяц сверяли»;
# «на каждом пробудном»; «пусть переключает». Только места с выходом по месту
# (паспорт цеха: «выход»: «по месту»). Перед входом — ничего нового.
_TRI_GOROD_R = {"в откат": "откат", "по ходу": "продолжение",
                "на переломе": "перелом", "после перелома": "продолжение"}
_TRI_PRIMETY = (("откат", ("откат",)), ("продолжение", ("продолж", "по ходу")),
                ("перелом", ("перелом",)))


def _tri_slovo(s) -> str:
    """Одно из трёх слов — то, что стоит раньше всех в её «месте»."""
    t = str(s or "").lower().replace("ё", "е")
    kand = []
    for slovo, primety in _TRI_PRIMETY:
        idx = [t.find(p) for p in primety if t.find(p) != -1]
        if idx:
            kand.append((min(idx), slovo))
    return min(kand)[1] if kand else ""


def _tri_mesyac_smotrela(slot, symbol, tf):
    """(открывала ли месяц рукой на этом пробуждении, какой это этаж)."""
    try:
        import hod_mesyaca as _hm_t
        e = _hm_t.starshiy(tf) or "MN1"
        sm = _hm_t._yashchik_chitat(slot, symbol).get("смотрел") or {}
        return (sm.get("бар") == _hm_t._bar_seychas()
                and e in (sm.get("этажи") or [])), e
    except Exception as _e_t:
        print(f"[ТРИ СЛОВА] взгляд на месяц не проверился ({_e_t}) — не держу")
        return True, "MN1"


_ruki_do_trekh_slov = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_trekh_slov(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                            rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    if "otdat_prikaz" not in r or not _po_mestu(ceh, slot):
        return r
    _p0 = r["otdat_prikaz"]

    def _prikaz_tri_slova(args):
        a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
        chto = str(a.get("что") or "").upper().strip()
        if chto not in ("HOLD", "CLOSE", "ADD"):
            return _p0(args)
        try:
            from hooks import load_trading_state as _lts_t
            t = _lts_t() or {}
            moy = _nomer_r(slot)
            poz = next((p for p in (t.get("positions") or [])
                        if str(p.get("status") or "").upper() == "OPEN"
                        and p.get("magic") == moy), None)
            run = (t.get("прогон") or {}).get("id")
            bar = str((t.get("рынок") or {}).get("бар") or "")
        except Exception as _e_t:
            print(f"[ТРИ СЛОВА] позиция не нашлась ({_e_t}) — приказ идёт как есть")
            return _p0(args)
        if not poz:
            return _p0(args)
        mesto = str(a.get("место") or "").strip()
        slovo = _tri_slovo(mesto)
        mes = str(a.get("месяц") or "").strip()
        vidit, e = _tri_mesyac_smotrela(slot, symbol, rabochiy_etazh)
        net = []
        if not vidit:
            net.append(f"открыть месяц ({e}) рукой на этом пробуждении — pokazat_etazh "
                       f"или stol_na_etazhe с этажом {e}")
        if len(mes) < 20:
            net.append("«месяц» — куда идёт ход месяца, что он делает сейчас (идёт, "
                       "откатывается или ломается) и изменилось ли что-то с твоего входа")
        if not slovo:
            net.append("«место» — начни с одного из трёх слов: откат, продолжение или "
                       "перелом — и скажи почему")
        if net:
            print(f"[ТРИ СЛОВА] ✗ {slot} {chto}: " + "; ".join(net))
            return ("Приказ НЕ отдан: в сделке на каждом пробуждении сначала месяц, "
                    "потом место. Не хватает: " + "; ".join(net)
                    + ". Посмотри, назови и позови снова.")
        napr = "LONG" if str(poz.get("direction") or "").upper() == "LONG" else "SHORT"
        gorod = ""
        try:
            import vedenie_sdelki as _vs_t
            gorod = _TRI_GOROD_R.get(str(_vs_t._scenariy(slot, symbol, napr) or ""), "")
        except Exception:
            pass
        kl = f"{str(poz.get('opened_at') or '')[:16]}|{poz.get('entry')}"
        f = (_BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / str(ceh)
             / "слоты" / str(slot) / "данные" / "три_слова.jsonl")
        bylo = ""
        try:
            if f.exists():
                for ln in f.read_text(encoding="utf-8").splitlines():
                    try:
                        z = json.loads(ln)
                    except Exception:
                        continue
                    if z.get("сделка") == kl and z.get("прогон") == run:
                        bylo = str(z.get("слово") or "")
            f.parent.mkdir(parents=True, exist_ok=True)
            with open(f, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"прогон": run, "бар": bar, "сделка": kl,
                                     "что": chto, "слово": slovo, "город": gorod,
                                     "место": mesto[:400], "месяц": mes[:600]},
                                    ensure_ascii=False) + "\n")
        except Exception as _e_z:
            print(f"[ТРИ СЛОВА] не записалось ({_e_z})")
        smena = (f" · смена: {bylo} → {slovo}" if bylo and bylo != slovo else "")
        print(f"[ТРИ СЛОВА] {slot} {chto}: {imya_zhitelya or 'житель'} — {slovo} · город — {gorod or '—'}{smena}")
        print(f"[МЕСЯЦ] {slot} {chto}: {imya_zhitelya or 'житель'} — «{mes[:160]}»")
        if not mesto.lower().replace("ё", "е").startswith(slovo):
            a["место"] = f"{slovo} — {mesto}"
        return _p0(a)

    r["otdat_prikaz"] = _prikaz_tri_slova
    return r


# TRI_SLOVA_V1 - marker


# ══ VOLNY_KANON_V1 — рука albom_voln у места с «волны: по канону» ══
# Слово Шефа 27.10: «нужна база с тем, как это выглядит фактически». Альбом
# лежит у места (папка альбом_волн); рука отдаёт список или картинку.
def _volny_po_kanonu(ceh, slot) -> bool:
    try:
        import json as _js_vk
        man = _js_vk.loads((_BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / str(ceh)
                            / "manifest.json").read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper():
                return str(z.get("волны") or "").strip().lower() == "по канону"
    except Exception:
        pass
    return False


_ruki_do_alboma_voln = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_alboma_voln(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                             rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    if not _volny_po_kanonu(ceh, slot):
        return r

    def _albom_voln(args):
        try:
            import volny_kanon as _vk
            a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
            otv = _vk.albom(ceh, slot, a.get("номер"))
            print(f"[АЛЬБОМ ВОЛН] {slot}: {str(a.get('номер') or 'список')}")
            return otv
        except Exception as e:
            return f"Альбом не открылся: {e}"

    r["albom_voln"] = _albom_voln
    return r


# VOLNY_KANON_V1 - marker


# ══ CHISTKA_DOLIVOK_V1 — ADD не принимается: старых доливок больше нет ══
# Слово Шефа 30.10: «старые доливки выбросить, почистить совсем». Новая
# доливка (D03) откроет свою дверь отдельным патчем — поверх этой.
_ruki_do_chistki_dolivok = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_chistki_dolivok(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                                 rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    if "otdat_prikaz" not in r:
        return r
    _p0 = r["otdat_prikaz"]

    def _prikaz_bez_dolivok(args):
        a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
        if str(a.get("что") or "").upper().strip() == "ADD":
            print(f"[ДОЛИВКА] {slot}: ADD не принят — доливок на этом месте нет")
            return ("Приказ НЕ отдан: доливок на этом месте нет. Позицию держать — "
                    "HOLD, закрыть — CLOSE.")
        return _p0(args)

    r["otdat_prikaz"] = _prikaz_bez_dolivok
    return r


# CHISTKA_DOLIVOK_V1 - marker


# ══ DOLIVKA_FRAKTAL_V1 (31.10): здесь была доливка «по окну в продолжении» ══
# Слово Шефа 31.10: доливка — по первому фракталу на два этажа ниже, во все
# входы, ставит город (hooks, DOLIVKA_FRAKTAL_V1). Метка оставлена, чтобы
# старый патч не вписал окно обратно.
# DOLIVKA_D03_V1 - marker


# DOLIVKA_FRAKTAL_V1 - marker


# ══ UBORKA_0911_V1 (09.11): здесь были быстрые доливки (фрактал H1, вершина H4,
# вторая доливка жителя) — удалены словом Шефа. Доливки — по канону главы 9, заново.
# DOLIVKI_TRI_V1 - marker


# ══ VEDENIE_MASSHTAB_V3 — подсказка руки про выход: на «ведение_масштаб» — новое правило ══
def _vyhod_po_mestu_tekst(ceh, slot) -> str:
    try:
        man = json.loads((_BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / str(ceh)
                          / "manifest.json").read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if (str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper()
                    and str(z.get("ведение_масштаб") or "").strip().lower() in ("да", "true", "1")):
                return (" Выход не зависит от места: он по масштабу импульса — строка «ВЕДЕНИЕ "
                        "ПО МАСШТАБУ ИМПУЛЬСА» («3 на 5» — CLOSE, иначе держать).")
    except Exception:
        pass
    return (" От места зависит выход: откат — встречный разворотник с приседающим в заметном "
            "плюсе; по ходу и перелом — дивер против сделки на рабочем.")


# VEDENIE_MASSHTAB_V3 - marker


# ══ VEDENIE_MASSHTAB_V4 — подсказка руки: откат — разворотник, импульс — масштаб ══
def _vyhod_po_mestu_tekst(ceh, slot) -> str:   # noqa: F811
    try:
        man = json.loads((_BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / str(ceh)
                          / "manifest.json").read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if (str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper()
                    and str(z.get("ведение_масштаб") or "").strip().lower() in ("да", "true", "1")):
                return (" От места зависит выход: откат — встречный разворотник с приседающим "
                        "в заметном плюсе; по ходу и перелом — по масштабу импульса (строка "
                        "«ВЕДЕНИЕ ПО МАСШТАБУ ИМПУЛЬСА»: «3 на 5» — CLOSE, иначе держать).")
    except Exception:
        pass
    return (" От места зависит выход: откат — встречный разворотник с приседающим в заметном "
            "плюсе; по ходу и перелом — дивер против сделки на рабочем.")


# VEDENIE_MASSHTAB_V4 - marker


# ══ ODNA_SVECHA_V1 — на месте «две_свечи: нет» вход только по одиночному бару ══
# Канон («Торговый хаос», 2-е изд., гл. 9): бар разворота — одна свеча: новый
# край, закрытие в нужной половине, целиком за пастью Аллигатора. Слово Шефа
# 09.11. ENTER и MOVE_ORDER принимаются, только если у города есть такой бар в
# сторону сделки на баре решения или до трёх баров раньше. Посчитать не вышло
# — приказ идёт как есть (сбой города — не её вина).
def _odna_svecha_mesto(ceh, slot) -> bool:
    try:
        man = json.loads((_BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / str(ceh)
                          / "manifest.json").read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper():
                return str(z.get("две_свечи") or "").strip().lower() == "нет"
    except Exception:
        pass
    return False


def _odin_razvorotnik(symbol, tf, napr):
    """(есть ли, что сказать). Есть — одиночный бар разворота в сторону napr
    на последнем закрытом баре или до трёх баров раньше. None — не посчиталось."""
    try:
        from feed_source import bars as _bars
        from williams_core import compute_alligator, vse_necron
        bs, point = _bars(symbol, tf, 300)
        try:
            from hooks import _tolko_zakrytye
            bs = _tolko_zakrytye(bs)
        except Exception:
            pass
        n = len(bs or [])
        if n < 40:
            return None, "мало баров"
        al = compute_alligator([b["high"] for b in bs], [b["low"] for b in bs], point=point)
        nado = "BULL" if napr == "LONG" else "BEAR"
        vse = vse_necron(bs, al.get("jaw_series"), al.get("teeth_series"),
                         al.get("lips_series"), s=max(1, n - 6))
        for x in reversed(vse):
            if x.get("i") is not None and x["i"] >= n - 4 and x.get("сторона") == nado:
                return True, f"{nado} @ {x.get('цена')} ({str(x.get('дата') or '')[:16]})"
        return False, f"за последние четыре бара одиночного {nado} нет"
    except Exception as e:
        return None, f"не посчиталось ({e})"


_ruki_do_odnoy_svechi = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_odnoy_svechi(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                              rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    if "otdat_prikaz" not in r or not _odna_svecha_mesto(ceh, slot):
        return r
    _p0 = r["otdat_prikaz"]

    def _prikaz_odna_svecha(args):
        a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
        chto = str(a.get("что") or "").upper().strip()
        if chto not in ("ENTER", "MOVE_ORDER"):
            return _p0(args)
        napr = str(a.get("направление") or "").upper().strip()
        if chto == "MOVE_ORDER" and napr not in ("LONG", "SHORT"):
            try:
                from hooks import load_trading_state as _lts_o
                moy = _nomer_r(slot)
                for p in ((_lts_o() or {}).get("positions") or []):
                    if (str(p.get("status") or "").upper() in ("PENDING", "WATCHING")
                            and (moy is None or p.get("magic") == moy)):
                        napr = str(p.get("direction") or "").upper()
                        break
            except Exception:
                pass
        if napr not in ("LONG", "SHORT"):
            return _p0(args)
        est, chto_skazat = _odin_razvorotnik(symbol, rabochiy_etazh, napr)
        if est is None:
            print(f"[ОДНА СВЕЧА] ? {slot} {chto} {napr}: {chto_skazat} — приказ идёт как есть")
            return _p0(args)
        if not est:
            print(f"[ОДНА СВЕЧА] ✗ {slot} {chto} {napr}: {chto_skazat}")
            return ("Приказ НЕ отдан: бара разворота нет. По канону («Торговый хаос», 2-е "
                    "изд., гл. 9) бар разворота — одна свеча: новый край, закрытие в "
                    "нужной половине, целиком за пастью Аллигатора. Вход — только по "
                    "такому бару в сторону сделки, на этом баре или до трёх баров "
                    "раньше. Разворот двумя свечами на этом месте входом не считается. "
                    "Город: " + chto_skazat + ". Посмотри строку РАЗВОРОТНЫЙ БАР на столе.")
        print(f"[ОДНА СВЕЧА] ✓ {slot} {chto} {napr}: {chto_skazat}")
        return _p0(args)

    r["otdat_prikaz"] = _prikaz_odna_svecha
    return r

# ODNA_SVECHA_V1 - marker


# ══ ZA_DIAPAZONOM_V1 — на месте «за_диапазоном: да» разворот только за пределами ══
# Канон («Торговый хаос», 2-е изд., гл. 9): рынок вывел цену за рамки текущего
# диапазона. Слово Шефа 09.11. Правило — Биржа/diapazon.py.
_ruki_do_diapazona = ruki


def ruki(symbol: str, ceh: str, slot: str, self_key: str,   # noqa: F811
         dnevnik_fn=None, rabochiy_etazh: str = "H4",
         imya_zhitelya: str = "") -> dict:
    r = _ruki_do_diapazona(symbol, ceh, slot, self_key, dnevnik_fn=dnevnik_fn,
                           rabochiy_etazh=rabochiy_etazh, imya_zhitelya=imya_zhitelya)
    if "otdat_prikaz" not in r:
        return r
    try:
        import diapazon as _dp
        if str(slot or "").strip().upper() not in {s.upper() for c, s, _k in _dp.mesta()
                                                   if c == str(ceh)}:
            return r
    except Exception:
        return r
    _p0 = r["otdat_prikaz"]

    def _prikaz_za_diapazonom(args):
        a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
        chto = str(a.get("что") or "").upper().strip()
        if chto not in ("ENTER", "MOVE_ORDER"):
            return _p0(args)
        napr = str(a.get("направление") or "").upper().strip()
        if chto == "MOVE_ORDER" and napr not in ("LONG", "SHORT"):
            try:
                from hooks import load_trading_state as _lts_d
                moy = _nomer_r(slot)
                for p in ((_lts_d() or {}).get("positions") or []):
                    if (str(p.get("status") or "").upper() in ("PENDING", "WATCHING")
                            and (moy is None or p.get("magic") == moy)):
                        napr = str(p.get("direction") or "").upper()
                        break
            except Exception:
                pass
        if napr not in ("LONG", "SHORT"):
            return _p0(args)
        try:
            import diapazon as _dp2
            d = _dp2.proverit(symbol, rabochiy_etazh, napr)
        except Exception as e:
            d = {"за": None, "слова": f"не посчиталось ({e})"}
        if d.get("за") is None:
            print(f"[ДИАПАЗОН] ? {slot} {chto} {napr}: {d.get('слова')} — приказ идёт как есть")
            return _p0(args)
        if not d.get("за"):
            print(f"[ДИАПАЗОН] ✗ {slot} {chto} {napr}: {d.get('слова')}")
            return ("Приказ НЕ отдан: разворот внутри диапазона. По канону («Торговый хаос», "
                    "2-е изд., гл. 9) у бара разворота ключ в том, что рынок вывел цену за "
                    "рамки текущего диапазона. Ход, который ты разворачиваешь, должен уйти "
                    "дальше начала прошлого размаха. Город: " + str(d.get("слова")) + ".")
        print(f"[ДИАПАЗОН] ✓ {slot} {chto} {napr}: {d.get('слова')}")
        return _p0(args)

    r["otdat_prikaz"] = _prikaz_za_diapazonom
    return r

# ZA_DIAPAZONOM_V1 - marker
