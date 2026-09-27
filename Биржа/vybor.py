# -*- coding: utf-8 -*-
# VYBOR_METKOY_V1
"""
ВЫБОР ВХОДА — метка жителя, а не свойство места.

ЗАКОН ЭТОГО ФАЙЛА
    Трейдер выбирает место входа сам, один раз, и носит выбор с собой.
    Хранится он там же, где всё нажитое — в метках жителя (дом/2_метки).
    Поэтому дома, в Академии и на Бирже это ОДИН человек с одной
    позицией, а не три догадки подряд.

    Здесь нет модели и нет UI. Чтение и запись.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
_KOREN = _BIRZHA.parent
for _p in (str(_BIRZHA), str(_KOREN / "жители")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

PATTERN = "выбор_входа"      # ключ метки — по нему её и находим
SLOVO = "ВЫБОР:"             # как трейдер объявляет выбор в разговоре


def _dvizhok_zhitelya(ceh: str, slot: str):
    """Движок того, кто сидит на месте. Пусто — честный None."""
    try:
        from cartridge_registry import resolve_para
        from dvizhok import Dvizhok
    except Exception:
        return None, None
    n = resolve_para(ceh, slot)
    if not n:
        return None, None
    try:
        return Dvizhok(Path(n["папка"])), n
    except Exception:
        return None, n


def chitat(ceh: str, slot: str) -> dict:
    """Последний выбор жителя этого места. Нет — пустой словарь."""
    d, _ = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return {}
    try:
        moi = [m for m in d.metki() if m.get("паттерн") == PATTERN]
    except Exception:
        return {}
    if not moi:
        return {}
    moi.sort(key=lambda x: str(x.get("когда", "")))
    return moi[-1]


def istoriya(ceh: str, slot: str) -> list:
    """Все выборы подряд — видно, передумывал ли и когда."""
    d, _ = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return []
    try:
        moi = [m for m in d.metki() if m.get("паттерн") == PATTERN]
    except Exception:
        return []
    moi.sort(key=lambda x: str(x.get("когда", "")))
    return moi


def zapisat(ceh: str, slot: str, tekst: str) -> tuple:
    """Положить выбор меткой. Старую не стираем: передумал — это тоже
    часть его жизни, и её видно."""
    tekst = (tekst or "").strip()
    if not tekst:
        return False, "пустой выбор"
    d, n = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return False, "на месте никого — некому выбирать"
    prezhniy = chitat(ceh, slot)
    if (prezhniy.get("текст") or "").strip() == tekst:
        return True, "тот же выбор, что и был"
    try:
        from datetime import datetime
        metki = d.metki()
        metki.append({"текст": tekst, "паттерн": PATTERN,
                      "откуда": "решение",
                      "когда": datetime.now().isoformat(timespec="seconds"),
                      "раз": 1})
        d._pisat_etazh(d._metki_path(), metki)
    except Exception as e:
        return False, str(e)
    kto = (n or {}).get("имя", "житель")
    if prezhniy:
        return True, f"{kto} передумал(а): {tekst}"
    return True, f"{kto} выбрал(а): {tekst}"


def poymat(ceh: str, slot: str, otvet: str) -> tuple:
    """Найти в ответе строку «ВЫБОР: …» и положить её меткой.

    Так же, как ловится запрос к архиву: житель объявляет словом, а не
    кнопкой. Ничего не нашли — молчим, это обычный разговор.
    """
    for stroka in (otvet or "").splitlines():
        s = stroka.strip()
        if s.upper().startswith(SLOVO):
            return zapisat(ceh, slot, s[len(SLOVO):].strip())
    return False, ""


def blok_dlya_prompta(ceh: str, slot: str) -> str:
    """Кусок в системную бумагу. Выбор подставляем ОТДЕЛЬНО, а не через
    окно свежих меток: окно маленькое (четыре), выбор из него вымывался
    бы, а он должен стоять всегда."""
    v = chitat(ceh, slot)
    if v:
        return ("\n\n=== ТВОЙ ВЫБОР ВХОДА ===\n"
                f"{v.get('текст','')}\n"
                f"(выбрано тобой {str(v.get('когда',''))[:16]})\n"
                "Это твоё решение, не приказ места. Работаешь по нему: не "
                "твоё место входа — пас, и так и скажи. Передумал(а) — "
                "скажи строкой «ВЫБОР: …», и это запишется как перемена.\n")
    # VYBOR_SVOY_NE_KNIZHNYY_V1: раньше здесь стояло «выбери и объяви»,
    # и человек шёл выбирать в книгу. А книга не нейтральна: третье место
    # в ней названо «самым подтверждённым», и все выбирали третье. Теперь
    # вопрос задан иначе — не «какое место лучше», а «какое по тебе».
    return ("\n\n=== ТВОЙ ВЫБОР ВХОДА ===\n"
            # VYBOR_NE_MESHAET_V1: слово Шефа — «выбор входа дело
            # трейдера и с выбором места не связан, машину это не
            # должно волновать». Здесь стоял прямой приказ отказывать,
            # пока выбор не сделан, — человек честно и отказывал, по
            # инструкции. Приказ убран, вопрос оставлен.
            "Своего входа ты ещё не выбрал(а) — и это не мешает работать: "
            "смотри на стол и решай, как решается. Захочешь назвать своё "
            "место — назови, и город это запомнит.\n"
            "Три места лежат у тебя в знаниях, рядом. Выбирай НЕ то, что "
            "там названо самым подтверждённым, — «подтверждённое» и "
            "«твоё» это разные вещи, и за подтверждённость платят "
            "упущенным началом движения. Выбирай по СЕБЕ: сколько ты "
            "готов(а) ждать, чем готов(а) платить, что переносишь легче — "
            "войти рано и ошибиться или опоздать и недобрать. Кто ты и "
            "какой ты — написано выше, в блоке про тебя.\n"
            "Решил(а) — объяви ОДНОЙ строкой:\n"
            "    ВЫБОР: <какое место входа> — <почему оно твоё>\n"
            "Один раз. Дальше живёшь по нему, а не выбираешь заново "
            "каждый бар.\n")

# VYBOR_SVOY_NE_KNIZHNYY_V1 - marker


# ══════════════════════════════════════════════════════════════
# ИНСТРУМЕНТ (INSTRUMENT_NAZNACHIT_ILI_SAM_V1)
# ══════════════════════════════════════════════════════════════
# Слово Шефа: не приколоченный, а на выбор — можно задать трейдеру
# инструмент, а можно оставить пустым, и тогда он выберет сам.
#
# Устройство то же, что с местом входа: НАЗНАЧЕНИЕ — свойство МЕСТА
# (лежит в бланке должности, его пишет Шеф), ВЫБОР — свойство
# ЧЕЛОВЕКА (лежит меткой в его доме, его объявляет он).
#
# Порядок старшинства:
#   1. назначено в бланке места  → работает по нему, это задание;
#   2. не назначено, но выбрал сам → работает по своему выбору;
#   3. ни того ни другого → работает по тому, что дал кабинет,
#      и его просят выбрать.
PATTERN_INSTR = "выбор_инструмента"
SLOVO_INSTR = "ИНСТРУМЕНТ:"


def instrument_mesta(ceh: str, slot: str) -> str:
    """Что Шеф задал этому месту. Пусто — не задавал, выбирает сам.

    PARA_MESTA_V1 (правка 14.08): читаем ПОСТ, а не общий листок.
    Листок `Биржа/данные/naznacheniya.json` был списком за других —
    ровно тем, что запрещает Чертёж (Гл.7.2): «единица есть там, где
    лежит, и говорит сама». Поле «инструмент» в бланке поста было
    заведено давно и пустовало. Листок ещё читаем — но только как
    запасной, для того, что не переехало.
    """
    _r, post = _post_mesta(ceh, slot)
    if post:
        iz_posta = (post.get("инструмент") or "").strip().upper()
        if iz_posta:
            return iz_posta
    return (_nazn_chitat().get(f"{ceh}/{slot}") or "").strip().upper()


def instrument_zhitelya(ceh: str, slot: str) -> dict:
    """Что выбрал сам житель. Нет метки — пустой словарь."""
    d, _ = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return {}
    try:
        moi = [m for m in d.metki() if m.get("паттерн") == PATTERN_INSTR]
    except Exception:
        return {}
    if not moi:
        return {}
    moi.sort(key=lambda x: str(x.get("когда", "")))
    return moi[-1]


def instrument_dlya(ceh: str, slot: str, zapasnoy: str = "") -> tuple:
    """(инструмент, откуда) — по старшинству: место → человек → кабинет."""
    naznachen = instrument_mesta(ceh, slot)
    if naznachen:
        return naznachen, "назначен"
    svoy = (instrument_zhitelya(ceh, slot).get("текст") or "").strip().upper()
    if svoy:
        return svoy, "выбрал сам"
    return (zapasnoy or "").strip().upper(), "с полки кабинета"


def zapisat_instrument(ceh: str, slot: str, tekst: str) -> tuple:
    """Объявленный инструмент — меткой в дом человека."""
    tekst = (tekst or "").strip().upper()
    if not tekst:
        return False, "пустой инструмент"
    if instrument_mesta(ceh, slot):
        return False, ("инструмент этому месту назначен Шефом — "
                       "выбирать нечего")
    d, n = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return False, "на месте никого"
    prezhniy = (instrument_zhitelya(ceh, slot).get("текст") or "").strip()
    if prezhniy.upper() == tekst:
        return True, "тот же инструмент, что и был"
    try:
        from datetime import datetime
        metki = d.metki()
        metki.append({"текст": tekst, "паттерн": PATTERN_INSTR,
                      "откуда": "решение",
                      "когда": datetime.now().isoformat(timespec="seconds"),
                      "раз": 1})
        d._pisat_etazh(d._metki_path(), metki)
    except Exception as e:
        return False, str(e)
    kto = (n or {}).get("имя", "житель")
    return True, f"{kto} взял(а) инструмент: {tekst}"


def poymat_instrument(ceh: str, slot: str, otvet: str) -> tuple:
    """Строка «ИНСТРУМЕНТ: EURUSD» в ответе — записываем меткой."""
    for stroka in (otvet or "").splitlines():
        s = stroka.strip()
        if s.upper().startswith(SLOVO_INSTR):
            return zapisat_instrument(ceh, slot, s[len(SLOVO_INSTR):])
    return False, ""


def blok_instrumenta(ceh: str, slot: str, dostupnye=None,
                     zapasnoy: str = "") -> str:
    """Кусок в промпт: чем работаем и откуда это взялось."""
    instr, otkuda = instrument_dlya(ceh, slot, zapasnoy)
    if otkuda == "назначен":
        return ("\n\n=== ТВОЙ ИНСТРУМЕНТ ===\n"
                f"{instr} — назначен тебе Шефом. Это задание, не выбор: "
                "работаешь по нему.\n")
    if otkuda == "выбрал сам":
        return ("\n\n=== ТВОЙ ИНСТРУМЕНТ ===\n"
                f"{instr} — ты выбрал(а) его сам(а). Место тебе ничего не "
                "навязывало.\nПередумал(а) — скажи строкой "
                "«ИНСТРУМЕНТ: <тикер>», и это запишется как перемена.\n")
    spisok = ""
    if dostupnye:
        spisok = ("Что сейчас доступно в городе: "
                  + ", ".join(sorted(set(dostupnye))[:24]) + ".\n")
    return ("\n\n=== ТВОЙ ИНСТРУМЕНТ ===\n"
            f"Тебе никто ничего не назначил, и своего ты пока не брал(а). "
            f"Сейчас работаешь по тому, что открыл кабинет: {instr}.\n"
            + spisok +
            "Хочешь свой — возьми: скажи строкой «ИНСТРУМЕНТ: <тикер>». "
            "Бери тот, который знаешь и чувствуешь, а не тот, где сегодня "
            "громче. Не хочешь выбирать — работай по кабинетному, это "
            "тоже честно.\n")

# INSTRUMENT_NAZNACHIT_ILI_SAM_V1 - marker


# ══════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЯ ШЕФА (PANEL_TREYDERA_V1)
# ══════════════════════════════════════════════════════════════
# Сперва я положил инструмент в бланк должности — и был неправ.
# Бланк про должность, он живёт месяцами; а инструмент — рабочее
# задание на сегодня. Теперь назначения лежат отдельным листком при
# Бирже: Шеф кликнул трейдера, кликнул инструмент — записалось.
_NAZN = Path(__file__).resolve().parent / "данные" / "naznacheniya.json"


def _nazn_chitat() -> dict:
    try:
        import json as _j
        return _j.loads(_NAZN.read_text(encoding="utf-8"))
    except Exception:
        return {}


def naznachit(ceh: str, slot: str, symbol: str) -> tuple:
    """Шеф даёт трейдеру инструмент. Пусто — снимает задание.

    PARA_MESTA_V1: пишем в ПОСТ места. Поста нет (место без бланка) —
    падаем в старый листок, чтобы задание не потерялось.
    """
    symbol_up = (symbol or "").strip().upper()
    _r, post = _post_mesta(ceh, slot)
    if _r is not None and post:
        ok, chto = _r.obnovit(post.get("_id", ""),
                              {"инструмент": symbol_up})
        if ok:
            return True, (f"задание: {symbol_up}" if symbol_up
                          else "задание снято")
        return False, chto
    import json as _j
    d = _nazn_chitat()
    klyuch = f"{ceh}/{slot}"
    symbol = (symbol or "").strip().upper()
    if symbol:
        d[klyuch] = symbol
    else:
        d.pop(klyuch, None)
    try:
        _NAZN.parent.mkdir(parents=True, exist_ok=True)
        _NAZN.write_text(_j.dumps(d, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    except Exception as e:
        return False, str(e)
    return True, (f"задание: {symbol}" if symbol else "задание снято")

# PANEL_TREYDERA_V1 - marker


# ═══════════════════════════════════════════════════════════
# РАБОЧАЯ ПАРА МЕСТА: инструмент + этаж (PARA_MESTA_V1)
# ═══════════════════════════════════════════════════════════
# Слово Шефа 14.08: инструмент трейдер меняет ПО СОГЛАСИЮ Шефа,
# а этаж — всегда его право, и он должен этажами активно
# пользоваться (искать масштаб, в который ляжет его структура).
#
# Поэтому хранятся они по-разному:
#   инструмент — в ПОСТЕ места (задание Шефа, поле «инструмент»);
#   этаж       — МЕТКОЙ жителя, и обязательно ПРИ ИНСТРУМЕНТЕ:
#                у одного человека на золоте структура может
#                читаться с дневок, а на евро с часов. Один общий
#                этаж — это и был тот «ещё один», которого Шеф
#                велел убрать.

# OTPERET_V1: с какого этажа человек пляшет, пока не сказал иначе.
ETAZH_OT_KOMFORTA = "H4"

PATTERN_ETAZH = "рабочий_этаж"      # ключ метки
SLOVO_ETAZH = "ЭТАЖ:"               # как трейдер объявляет его словом


def _post_mesta(ceh: str, slot: str):
    """(модуль rabota, пост места) — или (None, None).

    Пост ищем ПО ПРИВЯЗКЕ (поля цех/слот), а не по угаданному имени
    папки: посты трейдеров заведены как `treyder_proboy`, а не
    `торговый_хаос__A06`. Так же делает и сам город в
    `rabota.kto_na_slote` — Закон Картриджа: сканируем, а не помним
    имена наизусть.
    """
    try:
        import sys as _s
        import json as _j
        from pathlib import Path as _P
        _gorod = str(_P(__file__).resolve().parent.parent / "ГОРОД")
        if _gorod not in _s.path:
            _s.path.insert(0, _gorod)
        import rabota as _r
        if not _r.POSTY.exists():
            return _r, None
        for d in sorted(_r.POSTY.iterdir()):
            f = d / "пост.json"
            if not f.exists():
                continue
            try:
                p = _j.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if p.get("цех") == ceh and p.get("слот") == slot:
                p["_id"] = p.get("id") or d.name
                return _r, p
        return _r, None
    except Exception:
        return None, None


def etazh_zhitelya(ceh: str, slot: str, symbol: str) -> str:
    """Рабочий этаж, который житель выбрал для ЭТОГО инструмента."""
    symbol = (symbol or "").strip().upper()
    d, _ = _dvizhok_zhitelya(ceh, slot)
    if d is None or not symbol:
        return ""
    try:
        moi = [m for m in d.metki() if m.get("паттерн") == PATTERN_ETAZH]
    except Exception:
        return ""
    moi.sort(key=lambda x: str(x.get("когда", "")))
    for m in reversed(moi):
        kuski = (m.get("текст") or "").strip().upper().split()
        if len(kuski) == 2 and kuski[0] == symbol:
            return kuski[1]
    return ""


def zapisat_etazh(ceh: str, slot: str, symbol: str, tf: str) -> tuple:
    """Житель ставит себе рабочий этаж. Согласия не спрашивает —
    это его кухня (Закон II). Прошлые не стираем: видно, как он
    искал масштаб."""
    symbol = (symbol or "").strip().upper()
    tf = (tf or "").strip().upper()
    if not symbol:
        return False, "не сказано, по какому инструменту"
    try:
        import masshtab
        if not masshtab.est(tf):
            return False, f"такого этажа нет в лесенке: {tf}"
    except Exception:
        pass
    d, n = _dvizhok_zhitelya(ceh, slot)
    if d is None:
        return False, "на месте никого"
    if etazh_zhitelya(ceh, slot, symbol) == tf:
        return True, "тот же этаж, что и был"
    try:
        from datetime import datetime
        metki = d.metki()
        metki.append({"текст": f"{symbol} {tf}", "паттерн": PATTERN_ETAZH,
                      "откуда": "решение",
                      "когда": datetime.now().isoformat(timespec="seconds"),
                      "раз": 1})
        d._pisat_etazh(d._metki_path(), metki)
    except Exception as e:
        return False, str(e)
    kto = (n or {}).get("имя", "житель")
    return True, f"{kto} работает {symbol} с {tf}"


def poymat_etazh(ceh: str, slot: str, symbol: str, otvet: str) -> tuple:
    """Строка «ЭТАЖ: H1» в ответе — ставим сразу, без согласия."""
    for stroka in (otvet or "").splitlines():
        s = stroka.strip()
        if s.upper().startswith(SLOVO_ETAZH):
            return zapisat_etazh(ceh, slot, symbol,
                                 s[len(SLOVO_ETAZH):])
    return False, ""


def rabota_dlya(ceh: str, slot: str) -> dict:
    """ОДНА ДВЕРЬ: чем и на каком этаже работает это место.

    {инструмент, этаж, откуда_инструмент, откуда_этаж, готов}

    готов=False — работать нечем, и это НЕ ошибка: место молчит,
    пока ему не сказано или пока человек не выбрал сам. Запасного
    инструмента «лишь бы какой» тут нет намеренно: он и был тем
    четвёртым, которого никто не звал, а работали все по нему.
    """
    # SVOY_VYBOR_U_KAZHDOGO_V1: блок «сперва ЭКРАН» снят по слову
    # Шефа: «единый выбор убери, выбор трейдера запоминается, они не
    # зависят». Экран — это где смотрит Шеф. Работа трейдера — своя:
    # назначенный инструмент и ЗАПОМНЕННЫЙ им этаж.

    instr, otk_i = instrument_dlya(ceh, slot)
    etazh, otk_e = "", ""
    if instr:
        etazh = etazh_zhitelya(ceh, slot, instr)
        otk_e = "выбрал сам" if etazh else ""
        # OTPERET_V1: не выбрал — берём КОМФОРТНЫЙ. Слова Шефа: «мне
        # комфортно работать H4-H1, я с него начинаю, смотрю, и если
        # сразу не видно ничего — прохожу». Рабочий этаж и есть тот,
        # от которого пляшут. Раньше без выбора место молчало намертво,
        # а выбрать его в кабинете было нечем — я запер троих
        # требованием, которое им нечем исполнить.
        # Собственный выбор всегда старше умолчания.
        if not etazh:
            etazh, otk_e = ETAZH_OT_KOMFORTA, "от комфорта"
    # VYBOR_NE_PRI_MESTE_V1: паттерна тут больше нет вовсе. Он стоял
    # ногой готовности («выбрал инструмент и паттерн — работай»), потом
    # был снят из готовности, но продолжал читаться и ездить с парой.
    # Слово Шефа: движок единый, выбор входа месту не подчинён и месту
    # не сообщается. Что человек считает своим — он говорит на баре.
    pattern = ""
    # MESTO_BEZ_VYBORA_V1: слово Шефа — «снимай привязку места от
    # выбора входа, должны работать Нининым кодом». Движок стал общим:
    # точка, волна, откат, наблюдение, попытки лежат в hooks, council и
    # столе одинаково для всех трёх мест. Чужой стратегии в коде больше
    # нет, значит и запирать дверь не за чем. Паттерн читается и идёт
    # трейдеру в стопку как прежде — просто он больше не пропуск.
    # VYBOR_NE_PRI_MESTE_V1: место без человека НЕ работает. Инструмент
    # живёт в посте и остаётся там после увольнения, а этаж без жителя
    # подставлялся от комфорта — пустое место выглядело готовым, и
    # Совет судил по нему рынок и рождал точки, которые некому смотреть.
    # Вакансия — это не рабочая пара. Проверка стоит здесь, в одной
    # двери, чтобы кабинет, Совет, обход и исполнитель отвечали одно.
    if not kto_sidit(ceh, slot):
        return {"инструмент": instr, "этаж": etazh, "паттерн": "",
                "откуда_инструмент": otk_i if instr else "",
                "откуда_этаж": otk_e,
                "готов": False}
    return {"инструмент": instr, "этаж": etazh, "паттерн": pattern,
            "откуда_инструмент": otk_i if instr else "",
            "откуда_этаж": otk_e,
            "готов": bool(instr and etazh)}


def pochemu_molchit(ceh: str, slot: str) -> str:
    """Человеческим языком: чего не хватает, чтобы место работало."""
    r = rabota_dlya(ceh, slot)
    if r["готов"]:
        return ""
    if not kto_sidit(ceh, slot):
        return "место свободно — сажать некого"
    if not r["инструмент"]:
        return "инструмент не задан и не выбран"
    return "рабочий этаж не выбран"   # OTPERET_V1: теперь почти не бывает


# PARA_MESTA_V1 - marker

# RABOTA_PO_PARE_V1 - marker

# OTPERET_V1 - marker

# VYBOR_NE_MESHAET_V1 - marker

# MESTO_BEZ_VYBORA_V1 - marker


# VYBOR_NE_PRI_MESTE_V1 ─────────────────────────────────────────
def kto_sidit(ceh: str, slot: str) -> str:
    """Имя того, кто сидит на месте. Пусто — вакансия.

    Спрашиваем ту же единственную дверь, что и весь город:
    cartridge_registry.resolve_para. Второй правды о найме не заводим.
    Сбой чтения — считаем, что человек ЕСТЬ: пропустить взгляд из-за
    нашей ошибки хуже, чем лишний раз посчитать.
    """
    try:
        import cartridge_registry as _cr
        nos = _cr.resolve_para(ceh, slot)
    except Exception:
        return "?"
    if not nos:
        return ""
    if isinstance(nos, dict):
        return str(nos.get("имя") or nos.get("name") or "").strip() or "?"
    return str(getattr(nos, "имя", "") or getattr(nos, "name", "") or
               nos).strip() or "?"

# VYBOR_NE_PRI_MESTE_V1 - marker

# EDINYY_VYBOR_V1 - marker
