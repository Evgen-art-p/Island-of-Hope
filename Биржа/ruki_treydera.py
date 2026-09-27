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
                         "description": "например H1"}},
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
                                         "по умолчанию 140"}},
                "required": []}}},
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

    def _stol(args: dict) -> str:
        tf = str(args.get("этаж", "")).strip().upper()
        try:
            import masshtab
            if not masshtab.est(tf):
                return f"Такого этажа нет: {tf}. Есть: {', '.join(masshtab.LESTNICA)}"
            import stol as _s
            t = _s.nakryt(symbol, tf, self_key=self_key)
            chisla = f"=== СТОЛ · {symbol} {tf} ===\n" + _s.slovami(t)
            # STOL_S_KADROM_V1: кадр важнее чисел, и просить его
            # отдельной рукой трейдер не обязан. Рисуем этот же этаж
            # и кладём числа следом. Картинка не вышла — уходят одни
            # числа, как было: рука из-за кадра не падает.
            try:
                import grafik
                # KADR_BEZ_ALLIGATORA_V1: трейдеру — без линий
                put = grafik.kadr(symbol, tf, linii=False)
            except Exception as _ek:
                put = None
                print(f"[СТОЛ] кадр {tf} не нарисовался ({_ek}) — только числа")
            if put:
                return (f"[КАДР: {put}] {symbol} {tf} · стол ниже\n"
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
            put = grafik.kadr(symbol, tf, linii=False)
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
            _p = grafik.kadr(symbol, svoy, linii=False)
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
            from feed_source import bars as _bars
            b, _p = _bars(symbol, tf, max(n, 60))
        except Exception as e:
            return f"крайние точки не посчитались: {e}"
        if not b:
            return f"котировок {symbol} {tf} не дали"
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
                f"{symbol} {tf}, {len(b)} баров "
                f"({b[0].get('date')} → {b[-1].get('date')})\n"
                + _kray(b, "всё окно") + "\n"
                + f"между вершиной и дном: {mezhdu} баров\n"
                + _kray(b[:pol], "первая половина") + "\n"
                + _kray(b[pol:], "вторая половина"))

    def _moya_kartina(args: dict) -> str:
        try:
            import kartina
            return kartina.slovami(ceh, slot, symbol)
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
            "rastyanut_volnu": _rastyanut,      # RASTYAZHKA_V1
            "pokazat_etazh": _pokazat_etazh}
    itog.update(_ruka_mayaka_ruki(slot))   # RUKA_MAYAKA_V1
    itog.update(_ruka_prikaza_ruki(          # RUKA_PRIKAZA_V1
        symbol, slot, imya_zhitelya, rabochiy_etazh))
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
                                           "называй С КАДРА, на глаз: стол "
                                           "их не даёт, точность до пункта "
                                           "не нужна. Бери их из ОДНОЙ "
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
                                         "с кадра на глаз")},
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
                "долить": {"type": "number", "description": "для ADD"},
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
                       rabochiy_etazh: str) -> dict:
    tablo = _TABLO_PO_SLOTU.get(str(slot).upper())
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
        chto = str(args.get("что", "")).upper().strip()
        if chto not in _PRIKAZY:
            return ("Такого приказа нет: " + (chto or "пусто") +
                    ". Есть: " + ", ".join(_PRIKAZY) + ". Ничего не отдано.")

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
            if "цена прежний край не взяла" in _bolshoy_k and not _est_k:
                print(f"[КРАЙ] ✗ {symbol} {rabochiy_etazh} "
                      f"{napravlenie}: большой край не взят — вход не "
                      f"принят")
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
            if _net_par and any(_s in _sl_y for _s in (
                    "второй ямки нет", "второй горки нет",
                    "второй ещё нет")):
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
                    + ". Заявка на табло.")
        if chto == "MOVE_ORDER":
            return (f"Приказ отдан: {adresat} переставит заявку на "
                    f"{cena}, стоп {stop}"
                    + (f", бар {bar}" if bar else "") + ".")
        if chto == "CANCEL":
            return (f"Приказ отдан: {adresat} снимет заявку"
                    + (f", бар {bar}" if bar else "") + ".")
        if chto == "WAIT":
            return f"Принято: не работаешь на этом баре{', ' + bar if bar else ''}."
        return (f"Приказ отдан: {adresat} принял {chto}"
                + (f", бар {bar}" if bar else "") + ".")

    return {"otdat_prikaz": _otdat}


# RUKA_PRIKAZA_V1 - marker
