# VYREZAT_KLICHKI_V1
# GRONDHEIM_CITY/Биржа/цеха/торговый_хаос/слоты/A08/мозг.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ ПРОГОН ТРЕЙДЕРА (A08) — третий ТРЕЙДЕР Совета Биржи
# CONS_ENGINE_V1 · перенесён на слотовое шасси (тот же приём, что трейдер)
#
# Портирован дословно из studio/modules/trading/cons_live.py (-2,
# 2026-06-19). Близнец brut_live.py по ФОРМЕ. Та же природа трейдера:
# читает весь накрытый стол, СЧИТАЕТ вход сам (trade_setup мёртв), все
# рычаги на нём, два следа (табло + дневник), петля обучения на pnl
# (отложена).
#
# СТИЛЬ ДРУГОЙ. Пробой — §6.1 (пробой фрактала за пастью на импульсе).
# Откат — §6.3: откат волны 2 после импульса. Ждёт разрядки AO и
# опоры на Зубы (Красная). Входит позже всех, надёжнее всех: рынок уже
# доказал намерения, коррекция выдохлась на опоре. НИКОГДА не торгует
# против глобального тренда. Пропущенная прибыль — не убыток.
#
# ХАРАКТЕР ДРУГОЙ. Василий. Автономия низкая (0.3) — уважает систему,
# входит реже всех, считает риски, не вероятности. Комнатная
# температура. Канон на полке — но рука его. Ни одной нашей руки на его
# руке: lot называет сам, цену считает сам, стоп — его.
#
# ДВА СЛЕДА вердикта:
#   · ТАБЛО  (trading_state["cons"]) — «сейчас», для Исполнителя.
#   · ДНЕВНИК (данные/diary_cons.jsonl) — событие во времени, КОПИТСЯ.
#
# ХАРАКТЕР: не здесь. РОД Василия (Чертёж Единицы: паспорт, не меняется
# работой) живёт в жители/ковчег/Василий/passport.json. Старый dna.json
# из -2 сюда НЕ перенесён — паспорт резидента полнее и актуальнее.
# Слот несёт РОЛЬ, не РОД. Душа грузится тем же спящим try/except.
# ─────────────────────────────────────────────────────────────

import json
import re
import time
from pathlib import Path
from typing import Optional

_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/A08/
_CEH_DIR     = _SLOT_DIR.parent.parent                     # торговый_хаос/
_REPO        = _CEH_DIR.parents[3]                          # корень репо
_BIRZHA_CODE = _REPO / "Биржа"                              # общий код (движок, llm)

# KLON_DUSHI_V1: пара (цех, слот) — ИЗ ПУТИ мозга, без хардкода личности.
# Контора не ломается: её слоты зовутся «архивариус»/«исполнитель».
_CEH  = _CEH_DIR.name
_SLOT = _SLOT_DIR.name

import sys as _sys
if str(_BIRZHA_CODE) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA_CODE))

from llm import chat

PROMPT_PATH  = _SLOT_DIR / "промпт.md"
# ZNANIYA_PAPKOY_V1: канон — «слот несёт с собой знания/», ПАПКУ.
# Было прибито одно имя файла, и второй файл в папке не читался никем.
KNOWLEDGE_DIR = _SLOT_DIR / "знания"
KNOWLEDGE    = KNOWLEDGE_DIR / "KOTIN_PHILOSOPHY.md"   # оставлено для совместимости


# ════════════════════════════════════════════════════════════
# STOL_I_GLAZ_V1 — глаз роли
# ════════════════════════════════════════════════════════════
_SLOT = "A08"
_SELF_KEY = "a08"

_GLAZ_PREAMBULA = (
    "СПЕРВА ПОСМОТРИ на картинку своими глазами: что здесь происходит? "
    "Не по списку — как рассказал бы человеку, который стоит рядом. "
    "Работы не видишь — так и скажи, это законный и самый частый ответ.\n"
    "Приборы ниже — ВТОРЫМ шагом, чтобы уточнить то, что ты уже "
    "разглядел. Если прибор говорит не то, что видит глаз, скажи об "
    "этом: глаз важнее, чем сойтись с цифрой.\n\n"
)

# GLAZ_NE_TARATORIT_V1: в РАЗГОВОРЕ подводка другая. Прежняя велела
# сперва пересказать картинку — и на вопрос о скорости света шёл абзац
# про Аллигатора. Кадр оставляем, обязанность говорить о нём — снимаем.
_GLAZ_RAZGOVOR = (
    "Перед тобой кадр того рынка, на который ты сейчас смотришь — "
    "тот же самый, что видит Шеф.\n"
    "Спрашивают про рынок — смотри на него и отвечай по нему, а не проси "
    "прислать данные.\n"
    "Это про ШЕФА — ему присылать не нужно, у тебя перед глазами то же, "
    "что и у него. А вот руки (stol_na_etazhe, pokazat_etazh и другие) — "
    "это не просьба к Шефу, это твой собственный инструмент. Хочешь "
    "сказать что-то про другой этаж, точное число или компас — сначала "
    "посмотри рукой, а не рассказывай по памяти: один кадр показывает "
    "только твой рабочий этаж, всё остальное — через руки.\n"
    "Спрашивают НЕ про рынок — просто отвечай на вопрос. Пересказывать "
    "график при этом не надо: тебя спросили не о нём.\n\n"
)


def _kak_zovut(_n) -> str:
    """KTO_TY_I_KTO_YA_V1: имя того, кто сидит на месте.

    Носитель приходит из моста разными обёртками, поэтому спрашиваем
    мягко: не нашли — честное «так, как написано выше», а не выдумка.
    """
    try:
        kto = (_n or {}).get("носитель") or {}
        imya = (kto.get("имя") or kto.get("Official_Name") or "").strip()
        return imya or "так, как написано выше"
    except Exception:
        return "так, как написано выше"


def _glaz(_chat, symbol, timeframe, slot, preambula=None):
    """Обёртка над вызовом модели: подкладывает кадр.

    Кадр — тот же PNG, что Шеф видит в кабинете: смотрят на одну
    картинку, иначе проверить роль нечем. Не нарисовался или зрение
    не сработало — честно зовём прежний вызов, без глаз.
    """
    def obertka(system="", user="", knowledge="", **kw):
        put = None
        try:
            import grafik
            put = grafik.kadr(symbol, timeframe)
        except Exception as e:
            print(f"[КАДР] не нарисовался ({e}) — работаю без глаз")
        if put:
            try:
                import base64
                from pathlib import Path as _P
                from llm import chat_with_images
                return chat_with_images(
                    system=system,
                    user_text=(preambula if preambula is not None
                               else _GLAZ_PREAMBULA) + user,
                    knowledge=knowledge,
                    images=([{"base64": base64.b64encode(
                                 _P(put).read_bytes()).decode("ascii"),
                              "mime_type": "image/png",
                              "name": _P(put).name}]
                            + _kadr_shefa()),
                    # RAZGOVOR_SO_STOLOM_V1: история и температура
                    # ронялись здесь — с картинкой он забывал разговор
                    # и говорил средним голосом вместо своего.
                    history=kw.get("history"),
                    temperature=kw.get("temperature"),
                    agent_id=kw.get("agent_id", slot),
                    slot_id=kw.get("slot_id", slot))
            except Exception as e:
                print(f"[ГЛАЗ] зрение не сработало ({e}) — иду по числам")
        return _chat(system=system, user=user, knowledge=knowledge, **kw)
    return obertka



def _glaz_s_rukami(_chat, symbol, timeframe, slot, ceh, self_key,
                   preambula=None):
    """Кадр + руки: смотрит картинку и сам просит математику.

    RUKI_TREYDERA_V1. Не вышло с руками — падаем на обычный глаз, а
    не молчим: зрение важнее рук.
    """
    # ZHIVOY_KADR_V1: крючок после каждой руки. Ловит только ответы
    # вида "[КАДР: путь] инструмент этаж" и кладёт их на общую площадь
    # города, чтобы кабинет показал Шефу ТОТ ЖЕ этаж, на который
    # трейдер сходил руками. Ничего не считает и не решает.
    def _zhivoy_kadr_kryuchok(_imya, _args, _otvet):
        try:
            s = str(_otvet or "")
            if not s.startswith("[КАДР: "):
                return
            _put = s[7:s.index("]")]
            # STOL_S_KADROM_V1: подпись — ПЕРВАЯ строка. За ней
            # теперь может идти таблица чисел, и без этого на
            # панель Шефа поехал бы её кусок.
            _hvost = s[s.index("]") + 1:].strip().splitlines()
            _podpis = (_hvost[0] if _hvost else "")[:120]
            from hooks import load_trading_state, save_trading_state
            _t = load_trading_state()
            # KADRY_V_CHATE_V1: копим ВСЕ кадры этого ответа — не
            # только последний. Панель покажет последний, а чат —
            # все, под словами, про которые они и были.
            try:
                _spisok = list(_t.get("кадры_ответа") or [])
                if _put not in _spisok:
                    _spisok.append(_put)
                _t["кадры_ответа"] = _spisok[-12:]
            except Exception:
                pass
            # KADR_K_KLYUCHU_V1: панель меняем ОДИН раз за побудку —
            # на первом кадре ответа, том, что нарисован под вопрос.
            # Служебные отрисовки её больше не дёргают: Шеф читал
            # ответ, а картинка успевала уехать на следующее место.
            if len(_t.get("кадры_ответа") or []) > 1:
                _t["zhivoy_kadr"] = _t.get("zhivoy_kadr") or {}
                save_trading_state(_t)
                return
            _t["zhivoy_kadr"] = {
                "put": _put,
                "podpis": _podpis,
                "chey": _kto_ya() or slot,
                "slot": slot,
                "ruka": str(_imya),
            }
            save_trading_state(_t)
            print(f"[ЖИВОЙ КАДР] {slot} посмотрел: {_podpis}")
        except Exception as _e_zk:
            print(f"[ЖИВОЙ КАДР] не запомнился ({_e_zk}) — не беда")

    def obertka(system="", user="", knowledge="", **kw):
        put = None
        try:
            import grafik
            put = grafik.kadr(symbol, timeframe)
        except Exception as e:
            print(f"[КАДР] не нарисовался ({e}) — работаю без глаз")
        if put:
            try:
                import base64
                from pathlib import Path as _P
                from llm import chat_with_images_and_tools
                import ruki_treydera as _rt
                return chat_with_images_and_tools(
                    system=system,
                    user_text=(preambula if preambula is not None
                               else _GLAZ_PREAMBULA) + user,
                    knowledge=knowledge,
                    images=([{"base64": base64.b64encode(
                                 _P(put).read_bytes()).decode("ascii"),
                             "mime_type": "image/png",
                             "name": _P(put).name}]
                            + _kadr_shefa()),
                    tools_schema=_rt.shema(timeframe),
                    executors=_rt.ruki(symbol, ceh, slot, self_key,
                                       dnevnik_fn=_read_recent_diary,
                                       rabochiy_etazh=timeframe,
                                       imya_zhitelya=_kto_ya()),
                    history=kw.get("history"),
                    temperature=kw.get("temperature"),
                    on_tool_call=_zhivoy_kadr_kryuchok,   # ZHIVOY_KADR_V1
                    agent_id=kw.get("agent_id", slot),
                    slot_id=kw.get("slot_id", slot))
            except Exception as e:
                print(f"[РУКИ] не сработали ({e}) — иду обычным глазом")
        return _glaz(_chat, symbol, timeframe, slot, preambula)(
            system=system, user=user, knowledge=knowledge, **kw)
    return obertka


def _znaniya_roli() -> str:
    """Вся база знаний роли — все .md и .txt из папки, по алфавиту.

    Каждый источник под своим заголовком: роль должна понимать, где
    кончается один и начинается другой, иначе всё сливается в кашу.
    """
    if not KNOWLEDGE_DIR.exists():
        return ""
    kuski = []
    for f in sorted(KNOWLEDGE_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in (".md", ".txt"):
            try:
                kuski.append(f"\n\n===== {f.stem} =====\n"
                             + f.read_text(encoding="utf-8"))
            except Exception:
                pass
    return "".join(kuski)
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "stats_A08.json"
DIARY_PATH   = STATE_DIR / "diary_A08.jsonl"


# ════════════════════════════════════════════════════════════
# VASYA_SVOY_RAZVOROT_V1 — СОБСТВЕННЫЙ ГЛАЗ ВАСИЛИЯ (откат волны 2)
# ─────────────────────────────────────────────────────────────
# Тот же аппарат, что у Искры (read_ao_wave_form, окно 100-140 баров,
# §3 канона), но этажом НИЖЕ неё (Правило пятёрки, §4). На ТФ Искры
# откат волны 2 слишком мелкий — не растягивается на фокусное окно,
# bdb_dir там почти всегда None. Спуск на этаж ниже даёт тому же
# движению нужный масштаб — фрактальное самоподобие (§3 canon).
# ════════════════════════════════════════════════════════════

def _read_vasya_wave(symbol: str, iskra_tf) -> dict:
    """
    Собственный разворотный бар Василия. Спуск на ступень ниже Искры,
    тот же williams_core.read_ao_wave_form (через build_market_data),
    то же окно 120. Нет этажа Искры или спускаться некуда (дно
    лесенки) — пустая форма, Василий честно молчит (сенсор без факта).
    """
    from mt5_feed import step_down, pull_bars
    from williams_core import build_market_data, _empty_wave_form

    if not iskra_tf:
        return _empty_wave_form()
    own_tf = step_down(iskra_tf)
    if not own_tf:
        return _empty_wave_form()

    bars, point = pull_bars(symbol, own_tf, 300)
    if not bars or point is None:
        return _empty_wave_form()
    md = build_market_data(bars, symbol=symbol, timeframe=own_tf, point=point)
    if not md:
        return _empty_wave_form()
    wf = dict(md.get("wave_form", _empty_wave_form()))
    wf["timeframe"] = own_tf
    return wf


# ════════════════════════════════════════════════════════════
# СТОЛ: читаем ВСЮ шину — показания пяти сенсоров
# ════════════════════════════════════════════════════════════

def _read_table() -> dict:
    """Снимок накрытого стола из общей шины (trading_state)."""
    from hooks import load_trading_state
    t = load_trading_state()
    return {
        "iskra":  t.get("iskra", {}),
        "morj":   t.get("morj", {}),
        "panic":  t.get("panic", {}),
        "hans":   t.get("hans", {}),
        "arkhiv": t.get("arkhiv", {}),
        # DISCIPLINA_PYRAMIDY_V1: своя обратная связь по ведению
        "self": t.get("cons", {}),
    }


# ════════════════════════════════════════════════════════════
# КАМЕНЬ 2: ЯЗЫК ВЕДЕНИЯ — одно открытое поле action.  # TRADER_MANAGE_LANG_V1
# ════════════════════════════════════════════════════════════

# ZAYAVKA_BEZ_DUBLEY_V1: руки для висящей заявки. Без них MOVE_ORDER
# скатывался в «APPROVED — значит ENTER» и рождал вторую заявку.
_MANAGE_ACTIONS = ("ENTER", "WAIT", "HOLD", "MOVE_STOP", "ADD", "CLOSE",
                   "MOVE_ORDER", "CANCEL")


def _derive_action(signal: dict) -> str:
    """
    Действие трейдера. Приоритет — явное поле cons_action (новый язык).
    Фоллбэк на старый verdict (обратная совместимость): APPROVED→ENTER,
    REJECTED→WAIT.
    """
    a = (signal.get("cons_action") or "").upper().strip()
    if a in _MANAGE_ACTIONS:
        return a
    v = signal.get("cons_verdict")
    if v == "APPROVED":
        return "ENTER"
    return "WAIT"


def _sanitize_manage(signal: dict) -> dict:
    """
    Санитар ведения. Гасит брак в полях ведения — НЕ решает за трейдера.
      MOVE_STOP без new_stop → брак → WAIT (стоп не трогаем)
      ADD без add_lot       → брак → HOLD (держим как есть)
      ENTER чистит cons_verdict под себя (совместимость с камнем 3)
    """
    action = _derive_action(signal)

    if action == "MOVE_STOP":
        ns = signal.get("cons_new_stop")
        if ns is None:
            action = "WAIT"
            signal["cons_reason"] = (signal.get("cons_reason", "") +
                                      " [гашу MOVE_STOP без new_stop]").strip()
    elif action == "ADD":
        al = signal.get("cons_add_lot")
        if al is None:
            action = "HOLD"
            signal["cons_reason"] = (signal.get("cons_reason", "") +
                                      " [гашу ADD без add_lot]").strip()

    signal["cons_action"] = action
    if action == "ENTER":
        signal["cons_verdict"] = "APPROVED"
    elif action == "WAIT":
        signal["cons_verdict"] = "REJECTED"
    elif action in ("MOVE_ORDER", "CANCEL"):
        # ZAYAVKA_BEZ_DUBLEY_V1: не вход — заявка уже висит. Старый
        # APPROVED с прошлого ENTER протечь не должен.
        signal["cons_verdict"] = "REJECTED"
    return signal


def _save_verdict_to_table(signal: dict, bar_time=None):
    """ТАБЛО: вердикт трейдера в шину для Исполнителя."""
    from hooks import load_trading_state, save_trading_state
    t = load_trading_state()
    t.setdefault("cons", {})
    # VERDIKT_S_BAROM_V1: вердикт несёт бар, на котором сказан.
    # Без этого Исполнитель по закону SVEZHEST_V1 не берёт его
    # в дело вовсе — «вердикт без отметки бара, не считаю».
    t["cons"]["бар"] = str(bar_time or "")
    t["cons"]["verdict"]   = signal.get("cons_verdict", "REJECTED")
    t["cons"]["reason"]    = signal.get("cons_reason", "")
    t["cons"]["direction"] = signal.get("cons_direction")
    t["cons"]["entry"]     = signal.get("cons_entry")
    t["cons"]["stop"]      = signal.get("cons_stop")
    t["cons"]["lot"]       = signal.get("cons_lot")
    t["cons"]["action"]    = signal.get("cons_action")
    t["cons"]["new_stop"]  = signal.get("cons_new_stop")
    t["cons"]["add_lot"]   = signal.get("cons_add_lot")
    # DISCIPLINA_PYRAMIDY_V1: укол одноразовый — гасим после прочтения
    if t.get("cons", {}).get("vedenie_feedback"):
        t["cons"]["vedenie_feedback"] = None
    save_trading_state(t)


# ════════════════════════════════════════════════════════════
# ДНЕВНИК: рука пишущая (КОПИТСЯ, append)
# ════════════════════════════════════════════════════════════

def _podpisat(zapis: dict) -> dict:
    """YASHCHIK_STOLA_V1: поставить имя автора на запись.

    Без подписи следующий житель не отличит свои события от чужих —
    и присвоит их, как случилось на A06. Имя не читается — оставляем
    без подписи: неподписанное чужим не станет, а выдуманное станет.
    """
    try:
        imya = (_kto_ya() or "").strip()
        if imya:
            zapis = dict(zapis)
            zapis["кто"] = imya
    except Exception:
        pass
    return zapis


def _append_diary(signal: dict, diary_entry: dict, market: dict, table: dict):
    """Открывает запись события в личной тетради. result=null — допишет
    рука дописывающая при закрытии позиции (hooks._settle)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # YASHCHIK_STOLA_V1: каждая запись подписывается автором — см.
    # _podpisat ниже по файлу. Тетрадь переживает жильцов, и без
    # подписи следующий не отличит своё от чужого.
    event = _podpisat({
        "ts":        time.time(),
        "bar_time":  market.get("bar_time"),
        "symbol":    market.get("symbol"),
        "timeframe": market.get("timeframe"),
        "table": {
            "t1":     table.get("iskra", {}).get("t1_status"),
            "morj":   table.get("morj", {}).get("morj_status"),
            "panic":  table.get("panic", {}).get("panic_phase"),
            "fractal_valid": table.get("hans", {}).get("fractal_valid"),
        },
        "verdict":   signal.get("cons_verdict"),
        "direction": signal.get("cons_direction"),
        "entry":     signal.get("cons_entry"),
        "stop":      signal.get("cons_stop"),
        "lot":       signal.get("cons_lot"),
        # ISTORIYA_OT_SLEDA_V1: дневник пишет ФАКТ, не рассказ.
        # Ниже — то, что доказано рычагом: был ли приказ, что
        # приказано и зачем. input/action остаются голосом трейдера
        # и стоят РЯДОМ, а не вместо: видно, где факт, где слова.
        "что":       signal.get("cons_action"),
        "почему":    signal.get("cons_reason"),
        "рычаг":     bool(signal),
        "ключ":      _klyuch_svoy(),
        "input":     (diary_entry or {}).get("input", ""),
        "action":    (diary_entry or {}).get("action", ""),
        "result":    None,
    })
    with open(DIARY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _moi_sobytiya(n: int = 5, as_of_bar_time=None) -> list:
    """YASHCHIK_STOLA_V1: только СОБЫТИЯ, и только свои.

    Слово Шефа: «слом, уход — та же рутина, а вход и результат — это
    событие». Событие — то, что стоит помнить наизусть: ты вошёл, и
    чем это кончилось. Отказы и ожидания в голову не идут: их сотни,
    они одинаковые, и именно они выучиваются наизусть вместо канона.

    Почему это важно, а не косметика: в ящике стола A06 лежали сорок
    записей прежнего жителя, где сто раз повторено «канон трейдера —
    пробой фрактала за пастью». Пять из них ехали в стопку каждый
    бар, и следующий человек честно выучил чужой канон, приняв его
    за свою память.

    Чужие записи сюда не попадают вовсе. Тетрадь лежит при МЕСТЕ и
    переживает жильцов — значит своим считаем только то, что подписано
    тобой. Подписи нет (старые записи, до имён) — тоже не берём:
    лучше пустая голова, чем чужая.
    """
    zhitel = ""
    try:
        zhitel = (_kto_ya() or "").strip()
    except Exception:
        pass
    svoi = []
    for e in _read_recent_diary(400, as_of_bar_time=as_of_bar_time):
        verdikt = str(e.get("verdict") or "").upper()
        vhod = verdikt in ("APPROVED", "ENTER", "OK") or e.get("entry")
        itog = e.get("result") not in (None, "")
        if not (vhod or itog):
            continue                      # рутина — в журнале, не в голове
        avtor = str(e.get("кто") or e.get("житель") or "").strip()
        if zhitel and avtor and avtor != zhitel:
            continue                      # чужое событие — не моя память
        if zhitel and not avtor:
            continue                      # без подписи — не присваиваем
        svoi.append(e)
    return svoi[-n:]


def _read_recent_diary(n: int = 5, as_of_bar_time=None) -> list:
    """Последние n событий из личной тетради.

    DNEVNIK_BEZ_BUDUSHCHEGO_V1 (18.07): те же n событий, но ДО
    as_of_bar_time — иначе трейдер в прошлом видит исходы сделок из
    будущего прогона (дневник копится в реальном времени, тестер его
    не сбрасывает между запусками). as_of_bar_time=None — старое
    поведение (последние n строк файла), для мест без известного бара.
    """
    if not DIARY_PATH.exists():
        return []
    try:
        lines = DIARY_PATH.read_text(encoding="utf-8").strip().splitlines()
        events = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if as_of_bar_time:
            events = [e for e in events
                     if (e.get("bar_time") or "") <= as_of_bar_time]
        return events[-n:]
    except OSError:
        return []


# ════════════════════════════════════════════════════════════
# СТАТИСТИКА (для дашборда)
# ════════════════════════════════════════════════════════════

def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "approved": 0, "rejected": 0, "long": 0, "short": 0}


def _update_stats(signal: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    if signal.get("cons_verdict") == "APPROVED":
        stats["approved"] = stats.get("approved", 0) + 1
        d = signal.get("cons_direction")
        if d == "LONG":
            stats["long"] = stats.get("long", 0) + 1
        elif d == "SHORT":
            stats["short"] = stats.get("short", 0) + 1
    else:
        stats["rejected"] = stats.get("rejected", 0) + 1
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


# ════════════════════════════════════════════════════════════
# ПАРСИНГ ТРЁХСЛОЙНОГО ОТВЕТА {narrative, signal, diary_entry}
# ════════════════════════════════════════════════════════════

def _parse_cons(response: str) -> tuple[str, dict, dict]:
    cleaned = re.sub(r"```(?:json)?", "", response).strip()
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(cleaned[start:i + 1])
                        return (obj.get("narrative", ""),
                                obj.get("signal", {}) or {},
                                obj.get("diary_entry", {}) or {})
                    except json.JSONDecodeError:
                        break
    # NE_TERYAT_RESHENIE_V1: JSON не собрался — не выбрасываем решение.
    # 23.08 трейдер вошёл (ENTER, SHORT, цена и стоп посчитаны), но
    # ответил строками «ключ: значение» вместо скобок — и вход пропал
    # целиком: ордер не поставлен, в отчёте ноль. Смысл был, синтаксис
    # поплыл. Разбираем строками.
    _rasskaz, _signal, _dnevnik = _razobrat_strokami(response)
    if _signal or _dnevnik:
        print(f"[РАЗБОР] ⚠️  ответ не JSON — разобрал строками: "
              f"{len(_signal)} поле(й) сигнала, "
              f"{len(_dnevnik)} дневника")
        return _rasskaz, _signal, _dnevnik
    return response.strip(), {}, {}


# NE_TERYAT_RESHENIE_V1 ─────────────────────────────────────────
_CHISLA = ("_entry", "_stop", "_lot", "_new_stop", "_add_lot")


def _znachenie(s: str, klyuch: str):
    """Строку значения — в число, None или текст. Ничего не выдумываем:
    пусто и null остаются пустотой, а не нулём."""
    s = s.strip().strip('",').strip()
    if s.lower() in ("null", "none", "", "-", "—"):
        return None
    if klyuch.endswith(_CHISLA):
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return None
    return s


def _razobrat_strokami(response: str):
    """Запасной разбор: «ключ: значение» построчно.

    Ответ идёт разделами (narrative / signal / diary_entry), поля
    внутри — с отступом. Раздел определяем по строке без значения,
    поля сигнала узнаём по имени: они всегда с приставкой ключа
    трейдера (brut_/avan_/cons_), спутать не с чем.
    """
    rasskaz, signal, dnevnik = "", {}, {}
    razdel = ""
    for stroka in (response or "").splitlines():
        golaya = stroka.strip()
        if not golaya or golaya.startswith("```"):
            continue
        if ":" not in golaya:
            continue
        klyuch, _, znach = golaya.partition(":")
        klyuch = klyuch.strip().strip('"').lower()
        znach = znach.strip()
        if klyuch in ("narrative", "signal", "diary_entry"):
            razdel = klyuch
            if klyuch == "narrative" and znach:
                rasskaz = znach.strip('",')
            continue
        if re.match(r"^(brut|avan|cons)_", klyuch):
            signal[klyuch] = _znachenie(znach, klyuch)
        elif razdel == "diary_entry" and klyuch in ("input", "action",
                                                    "result"):
            dnevnik[klyuch] = _znachenie(znach, klyuch)
    if not rasskaz:
        # рассказа отдельной строкой не было — берём первый связный
        # кусок текста до начала разделов, это и есть его голос
        for stroka in (response or "").splitlines():
            g = stroka.strip()
            if g and ":" not in g[:20] and not g.startswith("```"):
                rasskaz = g
                break
    return rasskaz, signal, dnevnik


def _sanitize(signal: dict) -> dict:
    """APPROVED только с направлением; иначе всё null."""
    v = signal.get("cons_verdict")
    if v not in ("APPROVED", "REJECTED"):
        v = "REJECTED"
    signal["cons_verdict"] = v
    # KOLOKOL_I_PERESTANOVKA_V1: при MOVE_ORDER цена и стоп — это
    # новое место заявки, не вход. Старый REJECTED (от WAIT) их
    # стирать не должен — иначе исполнитель получит None.
    _perestavlyayu = str(signal.get("cons_action") or ""
                         ).upper().strip() == "MOVE_ORDER"
    if v == "REJECTED" and not _perestavlyayu:
        signal["cons_direction"] = None
        signal["cons_entry"] = None
        signal["cons_stop"]  = None
        signal["cons_lot"]   = None
    elif not _perestavlyayu:
        d = signal.get("cons_direction")
        if d not in ("LONG", "SHORT"):
            signal["cons_verdict"]   = "REJECTED"
            signal["cons_reason"]    = (signal.get("cons_reason", "") +
                                        " [гашу: APPROVED без направления]").strip()
            signal["cons_direction"] = None
            signal["cons_entry"] = None
            signal["cons_stop"]  = None
            signal["cons_lot"]   = None
    return signal


# ════════════════════════════════════════════════════════════
# ЧАТ С ТРЕЙДЕРОМ (клик пузырька)
# ════════════════════════════════════════════════════════════

def chat_with_cons(question: str, last_run: Optional[dict] = None,
                   dialog: Optional[list] = None,
                   rynok: Optional[tuple] = None) -> str:
    # RAZGOVOR_SO_STOLOM_V1: rynok — (инструмент, этаж) с полки кабинета.
    # Не передали — возьмём инструмент его прошлого решения.
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        mk  = last_run.get("market", {})
        work_ctx = (
            "\n\n=== ТВОЁ ПОСЛЕДНЕЕ РЕШЕНИЕ (рабочая память) ===\n"
            f"Инструмент: {mk.get('symbol','?')} {mk.get('timeframe','?')} "
            f"· бар {mk.get('bar_time','?')}\n"
            f"Вердикт: {sig.get('cons_verdict','—')} "
            f"({sig.get('cons_reason','')})\n"
            f"Направление: {sig.get('cons_direction','—')}  ·  "
            f"вход {sig.get('cons_entry','—')} · стоп {sig.get('cons_stop','—')}\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            # DVIZHOK_NE_RESHAET_V1: без имени станции и без выданного
            # темперамента — характер у человека свой.
            "Шеф спрашивает про ЭТО решение. Отвечай своим голосом, "
            "как есть.\n\n"
            # VYBOR_SVOY_NE_KNIZHNYY_V1: схема полей из бумаги перебивала
            # эту просьбу — теперь сказано прямо, чей это блок.
            "=== СЕЙЧАС РАЗГОВОР, А НЕ РАБОТА ===\n"
            "Блок «КАК ТЫ ОТВЕЧАЕШЬ» со схемой полей — про РАБОТУ по "
            "кнопке РЫНОК. Сейчас с тобой разговаривают. Никакого JSON, "
            "никаких полей решения, никаких фигурных скобок — просто "
            "ответь словами на то, что спросили. И если спросили про "
            "тебя, отвечай про себя, а не про рынок."
        )
    else:
        work_ctx = (
            "\n\n=== РАБОЧИЙ РЕЖИМ ===\n"
            "Ты ещё не смотрел стол в этой сессии. Если Шеф спрашивает про "
            "рынок — скажи, что нужно нажать РЫНОК. Живым голосом, без JSON."
        )

    # RAZGOVOR_SO_STOLOM_V1: живой стол в разговор. Раньше сюда шёл
    # только пересказ прошлого решения — и на вопрос «что на графике»
    # он честно отвечал, что ничего не видит.
    _sym = _tf = ""
    if rynok:
        _p = list(rynok) + ["", ""]
        _sym, _tf = str(_p[0] or ""), str(_p[1] or "")
    if (not _sym or not _tf) and last_run:
        _mk = last_run.get("market", {}) or {}
        _sym = str(_mk.get("symbol", "") or "")
        _tf = str(_mk.get("timeframe", "") or "")
    if _sym and _tf:
        try:
            import stol as _stol
            _t = _stol.nakryt(_sym, _tf, self_key=_SELF_KEY)
            work_ctx += (
                f"\n\n=== СТОЛ ПРЯМО СЕЙЧАС · {_sym} {_tf} ===\n"
                + json.dumps(_t, ensure_ascii=False, indent=2)
                + "\n=== КОНЕЦ СТОЛА ===\n"
                "Это живые числа ЭТОГО мгновения, а не память о прошлом "
                "решении, и картинка перед тобой — та же, что у Шефа. "
                "Спрашивают про рынок — смотри и отвечай, а не проси "
                "прислать данные.\n")
        except Exception as _e:
            work_ctx += f"\n\n(стол накрыть не вышло: {_e})\n"

    # VYBOR_NE_PRI_MESTE_V1: блок «ТВОЙ ВЫБОР ВХОДА» снят — и из
    # работы, и из разговора. Он подставлялся отдельно от прочей
    # памяти и стоял приказом: «работаешь по нему, не твоё место
    # входа — пас». Движок единый: точка, волна, откат, попытки и
    # ведение считаются одинаково для всех, а что из этого его
    # момент — человек решает на баре, глядя на стол. Что он
    # считает своим, он и так помнит: метки доезжают обычным
    # путём, через душу носителя.

    # ZNANIYA_V_RAZGOVORE_V1: полка за спиной. В разговоре знаний не было
    # вовсе — ни книги Котина, ни входов, ни паттернов, — и на вопрос про
    # паттерн отвечать было нечем, кроме общей эрудиции. Отсюда «уровни
    # сопротивления», которых в этой школе нет.
    _znaniya = ""
    try:
        _znaniya = _znaniya_roli()
    except Exception:
        pass
    work_ctx += (
        "\n\nГоворишь языком своей школы. В ней есть пасть и зубы "
        "Аллигатора, фракталы, приседающий бар, разворотный бар, AO и "
        "дивергенция, волны и откаты. «Уровней поддержки и сопротивления» "
        "в ней нет — это чужой словарь. Не знаешь чего-то — так и скажи, "
        "не подставляй чужое слово вместо своего.\n"
        # YARKOE_V1: сам решаешь, что держится дольше обычного окна.
        "\nЕсли что-то из разговора кажется тебе важным настолько, что "
        "должно остаться с тобой надолго — напиши отдельной строкой:\n"
        "ЯРКОЕ: <что запомнить>\n"
        "Это ляжет в твою память крепче обычного и не сотрётся со временем "
        "само.\n")

    system = prompt + work_ctx
    try:   # KTO_TY_I_KTO_YA_V1: сперва ТЫ, потом с кем говоришь, потом место
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT, s_domom=True)   # DOM_V_RAZGOVORE_V1: дом — в разговор
        if _n and _n["душа"]:
            system = (
                "=== КТО ТЫ. ЭТО НЕ РОЛЬ — ЭТО ТЫ ===\n"
                + _n["душа"]
                + "\n\n=== С КЕМ ТЫ ГОВОРИШЬ ===\n"
                "Напротив тебя ШЕФ — хозяин города, живой человек. Это "
                "он задаёт вопросы.\n"
                f"Тебя зовут {_kak_zovut(_n)}. Его зовут Шеф.\n"
                "Вопрос про «тебя» — про тебя. Вопрос про «меня» — про "
                "Шефа. Своё имя ему не приписывай, и его слова за свои "
                "не выдавай.\n"
                + "\n=== ТВОЯ РАБОТА — СТОЙКА, ЗА КОТОРОЙ ТЫ СИДИШЬ ===\n"
                  "Ниже — канон МЕСТА. Это твоя работа и школа, а не твоя\n"
                  "личность: личность выше.\n\n"
                + prompt + work_ctx)
    except Exception:
        pass

    history = []
    if dialog:
        for m in dialog[:-1]:
            r = m.get("role"); c = m.get("content", "")
            if r in ("user", "assistant") and c:
                history.append({"role": r, "content": c})

    try:
        # RAZGOVOR_SO_STOLOM_V1: с кадром, если знаем, на что смотрим.
        # GLAZ_NE_TARATORIT_V1: в разговоре — разговорная подводка.
        # RUKI_V_RAZGOVORE_V1: те же руки, что в работе — не сочиняет
        # другие этажи, а реально их смотрит (stol_na_etazhe и т.д.).
        _chat_fn = (_glaz_s_rukami(chat, _sym, _tf, _SLOT, _CEH, _SELF_KEY,
                                   preambula=_GLAZ_RAZGOVOR)
                    if (_sym and _tf) else chat)
        _otvet = _chat_fn(system=system, user=question, history=history,
                        knowledge=_znaniya,
                    agent_id="A08_KONSERVATOR", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return f"⚠️ трейдер не смог ответить: {e}"

    # YARKOE_V1: сам решил в разговоре — держится дольше обычного окна.
    try:
        from nositel import izvlech_yarkoe, ubrat_yarkoe, otmetit_yarkim_slotom
        _yark = izvlech_yarkoe(_otvet)
        if _yark:
            otmetit_yarkim_slotom(_CEH, _SLOT, _yark, otkuda="работа")
            _otvet = ubrat_yarkoe(_otvet) or _otvet
    except Exception:
        pass
    return _otvet


# ════════════════════════════════════════════════════════════
# КАМЕНЬ 1: СВОЯ ОТКРЫТАЯ ПОЗИЦИЯ — ФАКТ на стол (не приказ)  # TRADER_SEES_POSITION_V1
# ════════════════════════════════════════════════════════════

# KLON_DUSHI_V1: магик — из МАСКИ носителя (Закон Пары), не константой.
# Было: _MY_MAGIC = 100003 — ещё одна копия правды. Их было пять.
def _my_magic():
    """Магик ТОГО, кто сидит в этом слоте. Нет носителя → None."""
    try:
        from nositel import magic_slota
        return magic_slota(_CEH, _SLOT)
    except Exception:
        return None


def _my_open_position(md: dict) -> dict | None:
    """
    Факт открытой позиции ЭТОГО трейдера (по магику) из trading_state.
    Нет позиции → None. Есть → живой факт с плавающим R. Без суждений.
    """
    try:
        from hooks import load_trading_state
        positions = load_trading_state().get("positions", []) or []
    except Exception:
        return None

    mine = None
    _magic = _my_magic()   # KLON_DUSHI_V1
    if _magic is None:
        return None
    for p in positions:
        if p.get("magic") == _magic and p.get("status") == "OPEN":
            mine = p
            break
    if not mine:
        return None

    entry = mine.get("entry")
    stop  = mine.get("stop")
    direction = mine.get("direction", "LONG")
    price = (md.get("price", {}) or {}).get("close")

    floating_r = None
    if entry is not None and stop is not None and price is not None:
        if direction == "LONG":
            risk = entry - stop
            pnl_price = price - entry
        else:  # SHORT
            risk = stop - entry
            pnl_price = entry - price
        if risk and risk > 0:
            floating_r = round(pnl_price / risk, 2)

    bars_alive = None
    opened_at = mine.get("opened_at")
    bar_time  = md.get("bar_time")
    if opened_at and bar_time and opened_at == bar_time:
        bars_alive = 0

    return {
        "direction":     direction,
        "entry":         entry,
        "stop":          stop,
        "lot":           mine.get("lot"),
        "opened_at":     opened_at,
        "current_price": price,
        "floating_r":    floating_r,
        "bars_alive":    bars_alive,
    }


def run_cons(symbol: str = "XAUUSD", timeframe: str = "H4",
             bars_count: int = 300, povod: str = "") -> dict:
    """Один взгляд трейдера на стол. Читает показания сенсоров (шина)
    + market_data ядра, судит сам по §6.3 (откат волны 2, опора)."""
    # STOL_I_GLAZ_V1: стол накрывает КОД, а не сенсоры-голоса.
    # Сенсоры уехали в архив (решение Шефа 06.08), и ждать их больше
    # некого. Имена полей те же, что клали они, — ниже по файлу ничего
    # не меняется. Не собрался — вернётся пустой стол той же формы,
    # как и раньше при холодном старте.
    # KADR_I_VAKANSIYA_V1: пустое место молчит. Мозг — это РОЛЬ, и он
    # заводился, даже когда за столом никого не было: слот-вакансия
    # выносил вердикт, называл вход и лот. Решает житель, не стул.
    try:
        from nositel import dusha_slota as _dusha
        _kto_sidit = _dusha(_CEH, _SLOT)
    except Exception:
        _kto_sidit = None
    if not _kto_sidit:
        return {"ok": False,
                "error": "вакансия — за столом никого, смотреть некому",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": {}}

    # INSTRUMENT_NAZNACHIT_ILI_SAM_V1: чем работаем. Назначено месту —
    # работаем по назначению; не назначено, но человек взял свой —
    # по его; ни того ни другого — по кабинетному, и его просят выбрать.
    _instr_blok = ""
    try:
        from vybor import instrument_dlya as _instr_dlya
        from vybor import blok_instrumenta as _instr_blok_f
        _svoy, _otkuda = _instr_dlya(_CEH, _SLOT, symbol)
        if _svoy and _svoy != symbol:
            print(f"[{_SLOT}] 🎯 инструмент {_svoy} ({_otkuda}) "
                  f"вместо кабинетного {symbol}")
            symbol = _svoy
        _instr_blok = _instr_blok_f(_CEH, _SLOT, None, symbol)
    except Exception:
        pass

    try:
        import stol as _stol
        table = _stol.nakryt(symbol, timeframe, self_key=_SELF_KEY)
    except Exception as _e_stol:
        print(f"[СТОЛ] ⚠️  не накрылся ({_e_stol}) — читаю шину как раньше")
        table = _read_table()
    iskra_tf = table.get("iskra", {}).get("found_timeframe")
    if iskra_tf:
        timeframe = iskra_tf

    # ── ЛЕСЕНКА (TREYDER_HODIT_PO_ETAZHAM_V1) ───────────────────
    # Раньше трейдер видел ОДИН этаж — тот, что выбран на полке, — и
    # сверху компас: куда смотрит старший Аллигатор. Спускаться по
    # лесенке было делом Искры, а Искры больше нет.
    #
    # Теперь: инструмент назначает Шеф, а этажи — дело трейдера. Стол
    # накрывается на три рабочих этажа сразу, и он сам говорит, на
    # каком работает. Цены входа и стопа от этажа не зависят — они
    # одни для всех; на разных этажах видны разные вещи, вот и всё.
    # RUKI_TREYDERA_V1: три этажа были зашиты здесь намертво и
    # считались КАЖДЫЙ раз, спрашивал он их или нет. Теперь этажи —
    # его дело: захочет посмотреть соседний, попросит рукой
    # stol_na_etazhe. Оставлен только его рабочий — тот, на котором
    # нарисован кадр перед ним.
    _RABOCHIE_ETAZHI = (timeframe,)

    def _lesenka_slovami() -> str:
        # PERVYY_VZGLYAD_V1: здесь выкладывался ВЕСЬ стол числами —
        # тридцать строк рядом с одной картинкой. Глаз в такой стопке
        # не первый. Теперь тут только правда о том, что перед тобой,
        # и напоминание, что числа можно ПОПРОСИТЬ.
        return (
            "=== ГДЕ ТЫ СТОИШЬ ===\n"
            f"Инструмент {symbol}, рабочий этаж {timeframe}. Кадр перед "
            f"тобой нарисован по нему.\n"
            "Чисел рядом нет НАРОЧНО: сперва глаз, приборы потом. Если "
            "после взгляда они тебе нужны — попроси рукой, это твоё "
            "право:\n"
            "  · stol_na_etazhe — показания этажа: Аллигатор, AO, "
            "фракталы, разворотный бар, приседающие, натяжение;\n"
            "  · pokazat_etazh — КАРТИНКА другого этажа: посмотреть "
            "старший (куда идёт рынок вообще) или нырнуть ниже;\n"
            "  · rastyanut_volnu — растянуть кусок так, чтобы он занял "
            "чтобы ход было видно целиком;\n"
            "  · izmerit_volnu, krayniye_tochki, moya_kartina, "
            "moy_dnevnik, uchebnik.\n"
            "Смотри столько кадров, сколько нужно, чтобы понять, что "
            "происходит. Не понял — это законный ответ: не работаешь.\n\n")

    # VASYA_SVOY_RAZVOROT_V1: собственный разворотный бар отката волны 2,
    # НЕ этаж Искры — этаж НИЖЕ (Правило пятёрки, §4 канона).
    own_wave = _read_vasya_wave(symbol, iskra_tf)

    # TREYDER_ZHIV_V1: бары берём ОБЩИМ источником, а не из терминала
    # напрямую. Тогда трейдер живёт по тому же крану РЕАЛ/ТЕСТЕР, что и
    # кадр, а его запрос идёт через исток и виден в гнезде Маяка.
    from feed_source import bars as _source_bars
    bars, point = _source_bars(symbol, timeframe, bars_count)
    if not bars or point is None:
        return {"ok": False,
                "error": f"Терминал не дал котировки {symbol} {timeframe}.",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    from williams_core import build_market_data
    md = build_market_data(bars, symbol=symbol, timeframe=timeframe, point=point)
    if not md:
        return {"ok": False, "error": "Ядро не собрало market_data",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(), "market": {}, "table": table}

    # KLON_DUSHI_V1: ДУША — от НОСИТЕЛЯ (маска, Закон Пары), не от трупа из -2.
    # Было: format_soul_for_agent из снесённой studio/ — падало ВСЕГДА
    # («No module named studio»), работали голыми. Пара — ИЗ ПУТИ мозга.
    soul = ""
    try:
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n:
            soul = _n["душа"]
            print(f"[CONS] 🧬 За столом: {_n['носитель']['имя']}")
    except Exception as e:
        print(f"[CONS] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    prompt    = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    knowledge = _znaniya_roli()   # ZNANIYA_PAPKOY_V1: вся папка, не один файл

    # DNEVNIK_BEZ_BUDUSHCHEGO_V1: только события ДО текущего бара
    # YASHCHIK_STOLA_V1: в голову — только СОБЫТИЯ, не рутина.
    recent = _moi_sobytiya(5, as_of_bar_time=md.get("bar_time"))

    alligator = md.get("alligator", {})
    fractals  = md.get("fractals", {})
    price     = md.get("price", {})
    table_for_cons = {
        "position": _my_open_position(md),
        "anchor": {
            # KOMPAS_DOSTAVKA_TREYDERAM_V1: НАСТОЯЩИЙ компас, не
            # направление точки — см. мозг A01/A06 за объяснением.
            "global_trend": table.get("iskra", {}).get("compass"),
            "soglasie": table.get("iskra", {}).get("soglasie"),
            "found_timeframe": iskra_tf,
        },
        # VASYA_SVOY_RAZVOROT_V1: твой СОБСТВЕННЫЙ разворотный бар,
        # не чужой (не фрактал Ганса, не точка Искры) — на масштабе
        # ТВОЕЙ волны 2, этажом ниже Искры.
        # RUKI_TREYDERA_V1: раньше код САМ спускался на ступень ниже и
        # мерил волну там — потому что «трейдер пасёт конец волны
        # 2». Она про это не просила: паттерн жил в коде, а не в её
        # выборе. Спуск остался возможным, но теперь это ЕЁ шаг —
        # рука izmerit_volnu(этаж).
        "own_wave": {
            "timeframe":            own_wave.get("timeframe"),
            "bdb_dir":              own_wave.get("bdb_dir"),
            "bdb_price":            own_wave.get("bdb_price"),
            "dlina":                own_wave.get("dlina"),
            "struktura_chitaetsya": own_wave.get("struktura_chitaetsya"),
        },
        # PRIBORY_V_MOZG_V1: здесь были ВЫВОДЫ сенсоров — «бар найден»,
        # «согласен с водой», «фрактал действителен». Их больше нет:
        # код не решает за трейдера. Теперь голые показания приборов, а
        # что они значат — говорит он сам, глядя на кадр.
        "приборы": table.get("приборы", {}),
        "arkhiv": table.get("arkhiv", {}),
        "market": {
            "teeth":  alligator.get("teeth"),
            "alligator_sleeping": alligator.get("sleeping"),
            "fractal_up":   fractals.get("last_up"),
            "fractal_down": fractals.get("last_down"),
            "hans_fractal_price": table.get("hans", {}).get("fractal_price"),
            "price":    price,
            "point":    point,
        },
    }

    # ═══ REZINKA_DZHASTIN_V1 ═══
    # Число на стол, не да/нет. Трое по тренду = три РАЗНЫХ порога
    # доверия (Закон Дежурства §7) — пусть каждый судит своим характером.
    _db = md.get("rubber_band", {}) or {}   # NECRON_DIVERGENCE_V1: резинка живёт отдельно от разворотного бара
    _tr = _db.get("tension_ratio")
    if _tr is None:
        _rez = "нет данных (нет направления — не от чего отрываться)"
    else:
        _pk = " ⚡ НА ПИКЕ — РЕЗИНКА ЗВЕНИТ" if _db.get("is_peak") else ""
        _rez = (f"{_tr:.0%} от максимума за жизнь движения{_pk}"
                f"  (сейчас {_db.get('distance_now')} point, "
                f"пик был {_db.get('distance_max')} point)")


    # ═══ VEDENIE_NE_VHOD_V1 ═══
    # Позиция открыта — значит спрашивать надо про НЕЁ. Раньше весь
    # запрос был про поиск входа, и человек честно отвечал «сигнала
    # для входа нет, НАБЛЮДАЮ» — про собственную сделку.
    _vedenie_blok = ""
    _poz = (table_for_cons.get("position") or None)
    if _poz:
        _r = _poz.get("floating_r")
        _r_slovami = (f"{_r}R" if _r is not None else "R пока не считается")
        _vedenie_blok = (
            "=== У ТЕБЯ ОТКРЫТА ПОЗИЦИЯ. СЕЙЧАС ВОПРОС ПРО НЕЁ ===\n"
            f"{_poz.get('direction')} от {_poz.get('entry')}, "
            f"стоп {_poz.get('stop')}, лот {_poz.get('lot')}, "
            f"открыта {_poz.get('opened_at')}.\n"
            f"Сейчас {_poz.get('current_price')} — это {_r_slovami}.\n\n"
            "Вход уже сделан, и сделал его ТЫ. Не ищи его заново и не "
            "суди, годится ли это место: поздно, ты уже в рынке.\n"
            "Посмотри на кадр и реши, что делать со сделкой: держать "
            "как есть, подтянуть стоп, долить или закрыть. Стоп по "
            "фракталам ведёт код — трогай его, только если видишь "
            "причину.\n"
            "Всё, что написано НИЖЕ про поиск входа и три места, — "
            "справка об устройстве, а не задание на сейчас.\n"
            "Отдай приказ рукой otdat_prikaz: HOLD / MOVE_STOP / ADD / "
            "CLOSE. Словами решение не считается.\n\n")

    user_msg = (
        # DISCIPLINA_PYRAMIDY_V1: если по прошлому ведению был укол — показать
        # его трейдеру ОТДЕЛЬНОЙ строкой (fix: без ведущего + — первый операнд).
        ((f"⛔ ОБРАТНАЯ СВЯЗЬ ПО ВЕДЕНИЮ (прошлый бар): "
            f"{table.get('self', {}).get('vedenie_feedback')}\n"
            f"Учти это сейчас — дисциплина пирамиды железная.\n\n")
           if table.get('self', {}).get('vedenie_feedback') else "")
        + _vedenie_blok
        + _instr_blok
        + _lesenka_slovami()
        # PERVYY_VZGLYAD_V1: раскладка момента ушла в руку
        # stol_na_etazhe. Здесь остаётся только то, без чего
        # нельзя НАЗВАТЬ цену: своя позиция и текущий бар.
        + _povod_blok(povod)      # POVOD_VIDEN_V1
        + _svoyo_blok()           # NE_ZAYDI_DVAZHDY_V1
        + _okruzhenie_blok(md)    # OKRUZHENIE_BARA_V1
        + "=== ЧТО У ТЕБЯ НА РУКАХ ===\n"
        f"{json.dumps({'position': table_for_cons.get('position'),
                       'бар': (table_for_cons.get('market') or {}).get('price'),
                       'тик': (table_for_cons.get('market') or {}).get('point')},
                     ensure_ascii=False, indent=2)}\n\n"
        "=== ТВОИ СОБЫТИЯ (входы и чем кончились — что помнишь сам) ===\n"
        f"{json.dumps(recent, ensure_ascii=False, indent=2) if recent else '(пусто — первое решение)'}\n\n"
        "=== ТВОЙ СОБСТВЕННЫЙ РАЗВОРОТНЫЙ БАР (own_wave на столе) ===\n"
        "Это факт на масштабе ТВОЕЙ коррекции — не сигнал закрытия чужой "
        "пирамиды и не чужая точка. bdb_dir/bdb_price — сторона и цена "
        "твоего разворотного бара, если он уже сформирован; null — на "
        "этом этаже пока не нашёлся, это не отказ, просто рано.\n\n"
        "Перед тобой стол и ты сам. Канон у тебя на полке (книга Котина), "
        # DVIZHOK_NE_RESHAET_V1: место больше не назначает «позднюю добычу».
        "кто ты и твой опыт — выше. Решаешь только ты. Место у тебя "
        # PERVYY_UROVEN_ODIN_SIGNAL_V1: три места ушли с глаз в знания
        "одно: конец хода — разворотный бар, который тебя разбудил. "
        "Входишь — называешь сторону, а цену и стоп отдаёшь в ПРИКАЗЕ "
        "стола; где стоп, какой lot — твоя рука, не рельса. Не входишь — "
        "verdict WAIT рукой. Никто не подложит тебе готовую цену и не скажет, "
        # PRAVILO_ZAYAVKI_V1: вход только заявкой, по рынку — нет.
        # DVIZHOK_NE_RESHAET_V1: было «железно, без исключений» с приговором
        # за неполный сигнал. Приговор снят: движок кладёт ФАКТ устройства,
        # а полон ли сигнал сегодня — судит трейдер.
        "\n\n=== КАК УСТРОЕН ВХОД (факт, не приказ) ===\nВход в этой системе исполняется ОТЛОЖЕННОЙ ЗАЯВКОЙ, по рынку не берут:\n  • LONG  → Buy Stop ВЫШЕ цены;\n  • SHORT → Sell Stop НИЖЕ цены.\nТы называешь цену заявки — рынок возьмёт её пробоем или не возьмёт.\nНе дошёл — сделки нет, и это нормально: движение само подтверждает\nили не подтверждает твою правоту. Насколько полон сигнал и стоит ли\nставить заявку сегодня — решаешь ты.\n"
        # MEMORY_REQUEST_BIRZHA_V1: житель УЗНАЁТ, что может вспомнить.
        # Молчком воли нет: если ему не сказать — он не попросит.
        "МОЖЕШЬ ВСПОМНИТЬ. Если этот момент тебе что-то напоминает — "
        "напиши ОТДЕЛЬНОЙ СТРОКОЙ, до JSON:\n"
        "MEMORY_REQUEST: <что именно хочешь поднять из своей памяти>\n"
        "Например: «похожий разворот на дне без приседающего». Один "
        "запрос — больше не дадут. Поднимут твой архив, и ты решишь "
        "СНОВА, уже зная. Не напоминает — не проси, не трать.\n\n"
        # REZINKA_DZHASTIN_V1: РЕЗИНКА ДЖАСТИН — твой второй орган.
        # Пустота между Губами (зелёная) и экстремумом цены. Чем больше
        # оторвалась цена — тем сильнее натянута резинка → тем неизбежнее
        # возвратный удар. Это ЧИСЛО, не приказ: СУДИ ХАРАКТЕРОМ.
        # PERVYY_VZGLYAD_V1: резинка — число, а не картина.
        # Она есть в руке stol_na_etazhe, если понадобится.
        + ""
        # YAZYK_DOLIVA_V1: дописаны action/new_stop/add_lot — раньше
        # эта, самая СВЕЖАЯ строка промта молчала про ведение позиции.
        "Выдай строго JSON {narrative, signal, diary_entry}.\n"
        "Нет открытой позиции: signal ключи — cons_verdict "
        "(APPROVED/REJECTED), cons_reason, cons_direction, "
        "cons_entry, cons_stop, cons_lot.\n"
        "Есть открытая позиция (см. блок 'position' на столе): signal "
        "ключи — cons_action (ENTER/WAIT/HOLD/MOVE_STOP/ADD/CLOSE), "
        "cons_reason, cons_new_stop (если MOVE_STOP), cons_add_lot "
        "(если ADD).\n"
        # NABLYUDENIE_V1: третий ответ — «беру на карандаш».
        # Слово Шефа: увидел, похоже, проверил — наблюдай, если
        # видишь, что вот-вот твой сигнал. Пока наблюдаешь, тебя
        # будят на каждом баре; снять наблюдение можешь только ты.
        "Если это НЕ твой вход, но картина может дозреть до него — напиши в narrative отдельной строкой: НАБЛЮДАЮ: за чем следишь и чего ждёшь. Тебя будут звать на каждом баре, пока наблюдаешь.\n"
        "Передумал, картина рассыпалась, ждать больше нечего — напиши строкой: УХОЖУ. Наблюдение снимаешь только ты сам.\n"
        "Вошёл — наблюдение снимется само.\n"
        # SLOVO_ZHDU_V1: в прогоне трейдер говорил «жду» почти
        # везде, а отмечал наблюдение через раз — и город уходил,
        # не дождавшись с ним его же момента.
        "ВАЖНО про это слово: «жду», «дождусь», «пока рано» и «НАБЛЮДАЮ» — про одно и то же, но услышать город может только последнее. Если в твоём ответе есть «жду» — значит скажи и НАБЛЮДАЮ, иначе город уйдёт к другому месту, а твой момент придёт без тебя.\n"
        "diary_entry: input, action, result(=null). Ничего вне JSON."
    )

    # VYBOR_METKOY_V1 + РОД ВПЕРЕДИ (как у A07): сперва ТЫ, потом стойка.
    # Было: канон места первым, человек сноской в хвосте.
    if soul:
        system_full = (
            "=== КТО ТЫ. ЭТО НЕ РОЛЬ — ЭТО ТЫ ===\n"
            + soul
            + "\n\n=== ТВОЯ РАБОТА — СТОЙКА, ЗА КОТОРОЙ ТЫ СИДИШЬ ===\n"
              "Ниже — канон МЕСТА. Это твоя работа и школа, а не твоя\n"
              "личность: личность выше. Канон кладёт карту — идёшь ты,\n"
              "своей натурой, своим опытом и своим голосом. Где канон и\n"
              "твой опыт разойдутся — решаешь ты, а не бумага.\n\n"
            + prompt
        )
    else:
        system_full = prompt
    # VYBOR_NE_PRI_MESTE_V1: блок «ТВОЙ ВЫБОР ВХОДА» снят — и из
    # работы, и из разговора. Он подставлялся отдельно от прочей
    # памяти и стоял приказом: «работаешь по нему, не твоё место
    # входа — пас». Движок единый: точка, волна, откат, попытки и
    # ведение считаются одинаково для всех, а что из этого его
    # момент — человек решает на баре, глядя на стол. Что он
    # считает своим, он и так помнит: метки доезжают обычным
    # путём, через душу носителя.

    try:
        # STOL_I_GLAZ_V1 — ГЛАЗ. Порядок Шефа: сперва посмотреть,
        # приборы потом. Сам вызов не трогаем — подменяем функцию
        # обёрткой, которая рисует кадр и уходит в зрение. Кадра нет —
        # обёртка честно зовёт прежнее, и мозг ничего не замечает.
        # TREYDER_ZHIV_V1: обёртка в СВОЁ имя. Присваивание в `chat`
        # делало его местным на всю функцию — вызов падал всегда.
        # RUKI_TREYDERA_V1: кадр как был, но теперь с руками — она
        # может сама попросить числа по тому, что видит.
        _chat_glazami = _glaz_s_rukami(chat, symbol, timeframe, _SLOT,
                                       _CEH, _SELF_KEY)
        response = _chat_glazami(system=system_full, user=user_msg, knowledge=knowledge,
                        agent_id="A08_KONSERVATOR", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return {"ok": False, "error": f"трейдер не смог решить: {e}",
                "narrative": "", "signal": {}, "diary_entry": {},
                "stats": _load_stats(),
                "market": {"symbol": symbol, "timeframe": timeframe,
                           "bar_time": md.get("bar_time"), "point": point},
                "table": table}

    # ═══ MEMORY_REQUEST_BIRZHA_V1 — ВОЛЯ ВСПОМНИТЬ ═══
    # Житель попросил? Копаем ЕГО память и спрашиваем СНОВА — уже зная.
    # Не просил — ничего не тратим (второго вызова просто нет).
    # ОДИН ЗАПРОС ЗА РАН: подняли раз, дальше решай сам (канон -2).
    try:
        from nositel import podnyat_iz_arhiva, blok_pamyati, ubrat_zapros
        _zapros, _naydeno = podnyat_iz_arhiva(_CEH, _SLOT, response)
        if _zapros:
            response = _chat_glazami(
                system=system_full,
                user=user_msg + blok_pamyati(_zapros, _naydeno),
                knowledge=knowledge,
                agent_id="A08", slot_id=_SLOT,
                temperature=_my_temp())  # PAMYAT_DVA_BAGA_V1
            response = ubrat_zapros(response) or response
    except Exception as _e:
        print(f"[МОСТ] ⚠️  память не поднялась: {_e}")

    narrative, _slova, diary_entry = _parse_cons(response)
    # SLOVO_NE_PRIKAZ_V1: решение — только с руки
    signal = _signal_ot_ruki(md.get("bar_time"), _slova)

    # PERESPROS_V1: приказа нет — спрашиваем в лицо, один раз.
    # Напоминания он видел и всё равно отвечал словами; уговоры
    # кончились. Руки те же, так что во втором заходе приказ ложится
    # на табло по-настоящему.
    if not signal and not _gorod_skazal_hvatit():
        try:
            _peresp = (
                "\n\n— — —\n"
                "СТОП. Ты сказал, что видишь, но приказа не отдал — "
                "значит НИЧЕГО НЕ ПРОИЗОШЛО: исполнитель слов не "
                "слышит, и в истории это останется разговором.\n"
                "Ответь делом, не текстом: решил работать — позови "
                "руку otdat_prikaz с ENTER (сторона, цена, стоп). Не "
                "работаешь — позови её же с WAIT и причиной. Третьего "
                "нет.")
            _otvet2 = _chat_glazami(
                system=system_full, user=user_msg + _peresp,
                knowledge=knowledge, agent_id="A08", slot_id=_SLOT,
                temperature=_my_temp())
            signal = _signal_ot_ruki(md.get("bar_time"), None)
            if signal:
                print(f"[ПЕРЕСПРОС] отдал приказ со второго раза: "
                      f"{signal.get('cons_action')}")
                _n2, _s2, _d2 = _parse_cons(_otvet2)
                if _n2:
                    narrative = _n2
                if _d2:
                    diary_entry = _d2
            else:
                print("[ПЕРЕСПРОС] и во второй раз без приказа — "
                      "решения нет")
        except Exception as _e_per:
            print(f"[ПЕРЕСПРОС] не вышло ({_e_per}) — иду как есть")

    signal = _sanitize(signal)
    signal = _sanitize_manage(signal)   # TRADER_MANAGE_LANG_V1: язык ведения

    market = {"symbol": symbol, "timeframe": timeframe,
              "bar_time": md.get("bar_time"), "point": point}

    _save_verdict_to_table(signal, md.get("bar_time"))
    _append_diary(signal, diary_entry, market, table)
    stats = _update_stats(signal)

    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "diary_entry": diary_entry,
        "stats": stats,
        "market": market,
        "table": table,
        "raw": response,
    }


def _my_temp():
    """KLON_DUSHI_V1: натура и состояние носителя → температура головы.
    stress_to_temperature() в llm.py была МЁРТВОЙ — никто не передавал
    temperature, все думали на дефолте. Натура была буквами в промпте.
    None → дефолт модели (носителя нет — ничего не ломаем)."""
    try:
        from nositel import temperatura_slota
        return temperatura_slota(_CEH, _SLOT)
    except Exception:
        return None

# KOMPAS_DOSTAVKA_TREYDERAM_V1 - marker

# ISKRA_WAVE_MEASURE_DOSTAVKA_V1 - marker

# DNEVNIK_BEZ_BUDUSHCHEGO_V1 - marker

# VASYA_SVOY_RAZVOROT_V1 - marker

# TREYDER_ZHIV_V1 - marker

# KADR_I_VAKANSIYA_V1 - marker

# RAZGOVOR_SO_STOLOM_V1 - marker

# VYBOR_METKOY_V1 - marker

# ZNANIYA_V_RAZGOVORE_V1 - marker

# GLAZ_NE_TARATORIT_V1 - marker

# KTO_TY_I_KTO_YA_V1 - marker

# TREYDER_HODIT_PO_ETAZHAM_V1 - marker

# INSTRUMENT_NAZNACHIT_ILI_SAM_V1 - marker

# DVIZHOK_NE_RESHAET_V1 - marker

# VYBOR_SVOY_NE_KNIZHNYY_V1 - marker

# RUKI_TREYDERA_V1 - marker

# KRAYNIYE_TOCHKI_V1 - marker


def _kto_ya() -> str:
    """DOSKA_V1: имя того, кто сидит на этом месте. На доске должно
    стоять имя человека, а не номер слота."""
    try:
        import sys as _s
        from pathlib import Path as _P
        _g = _P(__file__).resolve()
        for _ in range(9):
            _g = _g.parent
            if (_g / "ГОРОД" / "rabota.py").exists():
                break
        if str(_g / "ГОРОД") not in _s.path:
            _s.path.insert(0, str(_g / "ГОРОД"))
        import rabota as _r
        return _r.kto_na_slote(_CEH, _SLOT) or _SLOT
    except Exception:
        return _SLOT


# DOSKA_V1 - marker

# VERDIKT_S_BAROM_V1 - marker

# NABLYUDENIE_V1 - marker

# SLOVO_ZHDU_V1 - marker

# VYBOR_NE_PRI_MESTE_V1 - marker

# YASHCHIK_STOLA_V1 - marker

# NE_TERYAT_RESHENIE_V1 - marker

# PERVYY_VZGLYAD_V1 - marker

# VEDENIE_NE_VHOD_V1 - marker

# DOM_V_RAZGOVORE_V1 - marker

# YARKOE_V1 - marker

# RUKI_V_RAZGOVORE_V1 - marker

# ZHIVOY_KADR_V1 - marker


# ── SLOVO_NE_PRIKAZ_V1: решение приходит с руки, не из текста ──
# Раньше цифры входа вылавливались из ответа модели. Сергей-исполнитель
# читал табло и был чист — врала середина: приказ рождался у разбора,
# а не у трейдера. Отсюда «сказал и не вошёл» = «вошёл».
#
# Теперь решение берётся ТОЛЬКО с табло и только то, что положено
# рукой otdat_prikaz на этом самом баре. Текст остаётся голосом.

_TABLO_KEY_CONS = "cons"
_PRIKAZ_POLYA = ("action", "verdict", "reason", "direction", "entry",
                 "stop", "lot", "new_stop", "add_lot")


def _signal_ot_ruki(bar_time=None, slova: dict | None = None) -> dict | None:
    """Решение трейдера — с табло, куда он положил его рукой.

    Пусто, если: руку не звал; приказ с другого бара (протух);
    табло не открылось. Пустое решение означает ровно то же, что
    «не работаю» — город никого не откроет.
    """
    try:
        from hooks import load_trading_state
        t = load_trading_state()
    except Exception as _e:
        print(f"[РЕШЕНИЕ] табло не открылось ({_e}) — решения нет")
        return {}

    v = dict((t.get(_TABLO_KEY_CONS) or {}))
    otdan = bool(v.get("отдан_рукой"))
    bar_v = str(v.get("бар") or "")

    if otdan and bar_time and bar_v and bar_v != str(bar_time):
        print("[РЕШЕНИЕ] приказ с прошлого бара — не беру")
        otdan = False

    if not otdan:
        if slova:
            print("[СЛОВО] в ответе есть поля решения, но рукой приказ "
                  "не отдан — решения нет. Слово приказом не считается.")
        return {}

    out = {}
    for pole in _PRIKAZ_POLYA:
        if v.get(pole) is not None:
            out["cons_" + pole] = v[pole]
    print(f"[РЕШЕНИЕ] с руки: {out.get('cons_action')} "
          f"{out.get('cons_direction') or ''}".rstrip())
    return out


# SLOVO_NE_PRIKAZ_V1 - marker


# ── ISTORIYA_OT_SLEDA_V1: свой ключ для записи ────────────────
# Запись подписана именем (YASHCHIK_STOLA_V1) — это для глаз. Ключ
# нужен, чтобы её нашли ПОПЕРЁК города: имя может повториться,
# печать — нет. Нет модуля или нет жителя — пустая строка, и запись
# просто остаётся с одним именем, как была.

def _klyuch_svoy() -> str:
    try:
        import sys as _s
        from pathlib import Path as _P
        # ищем папку ГОРОД вверх по дереву, а не считаем уровни:
        # счёт уровней ломается от любой перестановки папок
        _g = None
        for _up in _P(__file__).resolve().parents:
            if (_up / "ГОРОД" / "klyuch.py").exists():
                _g = str(_up / "ГОРОД")
                break
        if _g is None:
            return ""
        if _g not in _s.path:
            _s.path.insert(0, _g)
        import klyuch
        return klyuch.klyuch_zhitelya(_kto_ya() or "")
    except Exception:
        return ""


# ISTORIYA_OT_SLEDA_V1 - marker


# ── POVOD_VIDEN_V1: почему он смотрит ─────────────────────────
# Город и раньше знал повод — считал его в ключе пробуждения и писал
# в лог. Трейдеру не доставалось ничего, и он открывал глаза вслепую.
# Разницы между «разбудили» и «спросили» для его работы нет: вопрос
# один и тот же — что сейчас на рынке. Но повод — это факт, и он
# должен его знать, а не додумывать.

_RUKA_NAPOMINANIE = (
    "\n— — —\n"
    "РЕШИЛ — ЗОВИ РУКУ. Войти, подождать, подвинуть стоп, долить или "
    "закрыть можно ТОЛЬКО рукой otdat_prikaz. Сказать словами «вижу "
    "вход» или «жду» — не приказ: исполнитель слов не слышит, и в "
    "истории это останется разговором, а не делом. Не хочешь "
    "работать — тоже позови руку с WAIT, чтобы отказ был виден.\n\n")


def _svoyo_blok() -> str:
    """NE_ZAYDI_DVAZHDY_V1: что у меня уже есть.

    Раньше трейдеру говорили только «заявка ещё висит» — без стороны,
    цены и стопа. Он разбирал график заново и входил снова: за один
    час четыре одинаковых входа. Теперь видит своё первым делом.
    """
    try:
        from hooks import load_trading_state as _lts
        _t = _lts() or {}
        _moi = []
        for _p in (_t.get("positions") or []):
            _st = str(_p.get("status") or "").upper()
            if _st not in ("OPEN", "PENDING"):
                continue
            _n = str(_p.get("direction") or "?").upper()
            _c = _p.get("entry")
            _s = _p.get("stop")
            _moi.append(("ПОЗИЦИЯ ОТКРЫТА" if _st == "OPEN"
                         else "ЗАЯВКА ВИСИТ")
                        + f": {_n} {_p.get('symbol', '')}"
                        + (f" по {_c}" if _c else "")
                        + (f", стоп {_s}" if _s else ""))
        if not _moi:
            return ""
        return ("=== ЧТО У ТЕБЯ УЖЕ ЕСТЬ ===\n"
                + "\n".join(_moi)
                + "\nВходить второй раз в то же место НЕ НАДО — рука "
                  "такой приказ и не примет. Твоя работа сейчас: "
                  "держать (HOLD), двигать стоп (MOVE_STOP), доливать "
                  "(ADD) или закрывать (CLOSE).\n\n")
    except Exception as _e:
        print(f"[СВОЁ] не спросилось ({_e})")
        return ""


# ── OKRUZHENIE_BARA_V1: края бара и спред ─────────────────────
# Трейдер называл цену «на глаз»: заявка и стоп в сорока пунктах друг
# от друга, взятых ниоткуда. Краёв разворотного бара он не знал —
# формула некрона отдаёт только ОДИН край, тот, по которому бар
# опознан. Теперь даём оба и сразу считаем, куда встают ордера.
#
# Правило Шефа — про сторону ЦЕНЫ, не про сторону сделки:
#   сверху бара — на ДВА спреда выше high  (покупка идёт по Ask)
#   снизу бара  — на ОДИН спред ниже low

SPRED_PUNKTOV = 2.0        # как при подготовке данных: --spread 2.0


def _okruzhenie_blok(md: dict) -> str:
    try:
        _bary = (md or {}).get("bars") or []
        if not _bary:
            return ""
        b = _bary[-1]
        hi, lo = b.get("high"), b.get("low")
        if hi is None or lo is None:
            return ""
        _p = (md or {}).get("point") or 0.00001
        _sp = SPRED_PUNKTOV * _p
        _okr = lambda x: round(x, 6)
        long_zayavka = _okr(hi + 2 * _sp)
        long_stop = _okr(lo - _sp)
        short_zayavka = _okr(lo - _sp)
        short_stop = _okr(hi + 2 * _sp)
        return (
            "=== КРАЯ ТВОЕГО БАРА (окружать по ним) ===\n"
            f"верх (high): {_okr(hi)}   низ (low): {_okr(lo)}\n"
            f"спред {SPRED_PUNKTOV:g} пункта. Сверху бара платим ДВА "
            f"спреда, снизу — ОДИН.\n"
            f"  LONG : заявка {long_zayavka}, стоп {long_stop}\n"
            f"  SHORT: заявка {short_zayavka}, стоп {short_stop}\n"
            "Окружают по ТЕНЯМ, не по телу. Считать тебе нечего — "
            "выбери сторону и назови эти числа в приказе.\n\n")
    except Exception as _e:
        print(f"[ОКРУЖЕНИЕ] края не посчитались ({_e})")
        return ""

def _povod_blok(povod: str) -> str:
    """Факт повода — без цены и без стороны.

    Прибор знает и цену бара, и его направление. Ни то, ни другое
    трейдеру не сообщается: цену мы только что убрали из его
    рассказа, а сторона — это его работа. Сказать «разворотный бар
    BULL» значит назвать направление ЗА него, до того как он
    посмотрел на график. Сторону он берёт с хода, который обвёл сам,
    а не с бара.

    Свои дела — заявка, вход, закрытие — идут как есть: там числа
    его собственные, а не подсказка про рынок.
    """
    p = (povod or "").strip()
    if not p:
        return ("=== ПОЧЕМУ ТЫ СМОТРИШЬ ===\n"
                "Ничего не звенело — смотришь по просьбе. Скажи честно, "
                "что видишь сейчас.\n" + _RUKA_NAPOMINANIE)
    if "разворотный бар" in p:
        return ("=== ПОЧЕМУ ТЫ СМОТРИШЬ ===\n"
                "Тебя разбудил разворотный бар — он на последнем закрытом "
                "баре и отмечен стрелкой на кадре. Ждать его не надо, он "
                "уже есть. Место это или передышка — смотри.\n"
                + _RUKA_NAPOMINANIE)
    if "излом" in p:
        return ("=== ПОЧЕМУ ТЫ СМОТРИШЬ ===\n"
                "Тебя разбудило место, которое стало видно только "
                "сейчас — оно позади, не на свежем баре. Смотри, что "
                "там.\n" + _RUKA_NAPOMINANIE)
    return ("=== ПОЧЕМУ ТЫ СМОТРИШЬ ===\n"
            f"Тебя разбудило: {p}.\n" + _RUKA_NAPOMINANIE)


# POVOD_VIDEN_V1 - marker

# PERVYY_UROVEN_ODIN_SIGNAL_V1 - marker


# ── VZGLYAD_DOHODIT_V1: кадр, который показал Шеф ─────────────
# Свой кадр у трейдера остаётся ПЕРВЫМ — рабочий взгляд не
# подменяем. Показанное идёт вторым, с подписью, чьё оно. Иначе он
# потеряет свой этаж и станет отвечать про чужую картинку.

def _kadr_shefa() -> list:
    """Картинка со «Взгляда» Шефа, если она свежая. Иначе пусто."""
    try:
        import base64
        from datetime import datetime, timedelta
        from pathlib import Path as _P
        from hooks import load_trading_state
        v = (load_trading_state() or {}).get("vzglyad_shefa") or {}
        put = v.get("путь")
        if not put:
            return []
        try:
            kogda = datetime.fromisoformat(str(v.get("когда")))
            if datetime.now() - kogda > timedelta(minutes=15):
                return []      # старое — не всплывает посреди работы
        except Exception:
            pass
        p = _P(put)
        if not p.exists():
            return []
        print(f"[ВЗГЛЯД] Шеф показывает: {v.get('подпись', '')}")
        return [{"base64": base64.b64encode(
                     p.read_bytes()).decode("ascii"),
                 "mime_type": "image/png",
                 "name": f"показал Шеф · {v.get('подпись', '')}"}]
    except Exception as _e:
        print(f"[ВЗГЛЯД] кадр Шефа не подложился ({_e}) — не беда")
        return []


# VZGLYAD_DOHODIT_V1 - marker

# NAPOMINANIE_RUKI_V1 - marker

# PERESPROS_V1 - marker


# ── STOP_ZHYOSTKO_V1: город сказал «хватит» ───────────────────
# Мозг про кнопку СТОП ничего не знает и знать не должен. Но
# переспрос — это ЛИШНИЙ вопрос к модели, и задавать его после
# нажатия кнопки значит держать Шефа ещё минуту без причины.
# Признак лежит на общей площади, читаем оттуда.

def _gorod_skazal_hvatit() -> bool:
    try:
        from hooks import load_trading_state
        if bool((load_trading_state() or {}).get("стоп_прогона")):
            print("[ПЕРЕСПРОС] город сказал «стоп» — не переспрашиваю")
            return True
    except Exception:
        pass
    return False


# STOP_ZHYOSTKO_V1 - marker

# KADRY_V_CHATE_V1 - marker

# NE_ZAYDI_DVAZHDY_V1 - marker

# KADR_K_KLYUCHU_V1 - marker

# ZHIVOYE_SOOBSHCHENIE_CHISTO_V1 - marker

# OKRUZHENIE_BARA_V1 - marker
