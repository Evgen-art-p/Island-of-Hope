# -*- coding: utf-8 -*-
# NOSITEL_BRIDGE_V1
"""
МОСТ К НОСИТЕЛЮ — одна дверь между РОЛЬЮ (слот Биржи) и РОДОМ (житель).

ЗАЧЕМ ОТДЕЛЬНЫЙ ФАЙЛ, а не строки в каждом мозге:
  мостов нужно девять (девять мозгов) + два конца в hooks. Впишем сборку
  души в каждый мозг — через месяц это одиннадцать копий, которые разъедутся.
  Ровно та болезнь, от которой лечимся (четыре копии магика). Поэтому —
  ОДНА ДВЕРЬ, как council.wake_council() у Совета. Мозг стучится, дверь
  открывает. Правда живёт в одном месте.

ДВА КОНЦА КОЛЬЦА:
  ЧИТАЮЩИЙ  dusha_slota(цех, слот) → носитель + его душа текстом
            (перед решением: трейдер видит СЕБЯ — род, натуру, свой опыт)
  ПИШУЩИЙ   zapisat_vyvod(magic, вывод, pnl_r) → вывод в ЕГО ЖЕ якоря
            (после сделки: рынок рассудил, вывод осел в носителя)

  Оба конца — через маску (Закон Пары). Ни одного id роли, ни одного
  реестра. Слот знает свою пару по (цех, слот); закрытая позиция — по magic.

ЧЕГО ТУТ НЕТ: LLM, UI, торговой математики. Только сведение пары и текст.
`шесть·проверено·до·корня`
"""
from pathlib import Path
import sys as _sys

_BIRZHA = Path(__file__).resolve().parent
_REPO = _BIRZHA.parent
_ZHITELI_CODE = _REPO / "жители"      # тут живёт dvizhok.py (движок жителя)

if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))
if str(_ZHITELI_CODE) not in _sys.path:
    _sys.path.insert(0, str(_ZHITELI_CODE))


def _dvizhok(dom: str):
    """Движок носителя по его дому. Ошибка — честный None, не падение:
    торговый цикл не должен рваться из-за души."""
    try:
        from dvizhok import Dvizhok
        return Dvizhok(Path(dom))
    except Exception as e:
        print(f"[МОСТ] ⚠️  движок жителя не поднялся ({e})")
        return None


# ════════════════════════════════════════════════════════════
# ЧИТАЮЩИЙ КОНЕЦ — кто сидит в слоте и чем он дышит
# ════════════════════════════════════════════════════════════

def _sobrat_dushu(stol: dict, s_domom: bool = False) -> str:
    """Стол носителя → текст для системного промпта.

    ГРАНИЦА (та же, что у Искры): душа красит ГОЛОС и решение человека,
    но НЕ подменяет факты рынка. Числа стола считает движок.

    s_domom=False по умолчанию: на бирже человек за РАБОЧИМ столом, не
    дома (Закон Входа-Выхода — не тащим кухню в чужую кухню). Плюс
    трезвый расчёт: домашний_промпт Ильи ~2 000 знаков, а тестер зовёт
    мозг тысячи раз — это деньги на ветер. Нужен дом в промпте — включишь
    флагом, решение Шефа.
    """
    if not stol:
        return ""
    L = []
    L.append(f"Тебя зовут {stol.get('кто_я') or '—'}. Это ТЫ, не роль.")
    if stol.get("ядро"):
        L.append(f"Твоё ядро: {stol['ядро']}")

    dna = stol.get("натура") or {}
    if dna:
        L.append(
            "Твоя натура (ручки, 0..1): "
            f"упрямство {dna.get('Stubbornness','—')}, "
            f"автономия {dna.get('Autonomy_Level','—')}, "
            f"эмпатия {dna.get('Empathy','—')}, "
            f"порог вкуса {dna.get('Aesthetic_Threshold','—')}, "
            f"фильтр общения {dna.get('Social_Filter','—')}, "
            f"резонанс {dna.get('Resonance_Frequency','—')}."
        )
    if stol.get("история"):
        L.append(f"Твоя история: {stol['история']}")
    if stol.get("чувство"):
        L.append(f"Как ты отзываешься: {stol['чувство']}")

    zaryad = stol.get("заряд")
    if zaryad is not None:
        if zaryad > 0.3:
            sost = "на подъёме"
        elif zaryad < -0.3:
            sost = "придавлен(а), несёшь тяжесть"
        else:
            sost = "ровно"
        L.append(f"Твой заряд сейчас: {zaryad} ({sost}).")

    # ── ТРИ ГОЛОСА (DVER_V_METKI_V1) ────────────────────────────
    # Закон ядра (Брат/README.md): род / метки / маяки — три этажа,
    # три РАЗНЫХ голоса. Раньше здесь был один, и он ВРАЛ: называл
    # род «твоими выводами, оплаченными твоими деньгами». А род вписан
    # при рождении — житель его не выносил и не оплачивал.
    # Голоса разные — значит житель может их СТОЛКНУТЬ.

    # ГОЛОС 1 — РОД. Кто он ЕСТЬ. Не менялось и не меняется.
    yak = stol.get("якоря") or ""
    parts = [x.strip() for x in yak.replace("\\n", "\n").split("\n") if x.strip()]
    if parts:
        L.append("\nКТО ТЫ ЕСТЬ — твой род. Не выводы, не уроки: так ты "
                 "устроен(а) с самого начала. Это дно, оно не спорит:")
        for p in parts:
            L.append(f"  • {p}")

    # ГОЛОС 2 — МЕТКИ. Нажитое. ВОТ ЭТО оплачено, и вот здесь голос
    # «твои же выводы» — правда. Поле ОТКУДА даёт разный тон: то, что
    # сказал рынок, звучит иначе, чем то, чему учили.
    metki = stol.get("метки") or []
    if metki:
        L.append("\nЧТО ТЫ НАЖИЛ САМ — выводы, которых при рождении не "
                 "было. Ты их заработал:")
        for m in metki:
            otk = (m.get("откуда") or "").strip()
            golos = {
                "рынок":  "рынок сказал",
                "учёба":  "чему тебя учили",
            }.get(otk, f"вынес(ла) как {otk}" if otk else "вынес(ла)")
            L.append(f"  • [{golos}] {m.get('текст','')}")
        L.append("Это твоё, оплаченное. Хочешь идти против — иди, "
                 "но знай, что идёшь против себя же.")

    # ГОЛОС 3 — МАЯКИ. Момент. Ещё не вывод (Гл.4.4: один вывод — не опыт).
    chernoviki = stol.get("черновики") or []
    if chernoviki:
        L.append("\nЗАМЕЧАЮ ЗА СОБОЙ (не подтвердилось повтором — "
                 "наблюдение, не готовый вывод):")
        for d in chernoviki:
            raz = d.get("раз", 1)
            hvost = "" if raz < 2 else f" (уже {raz} раз(а) — похоже на закономерность)"
            L.append(f"  • {d.get('текст','')}{hvost}")

    if s_domom and stol.get("дом"):
        L.append(f"\nТвой дом: {stol['дом']}")

    return "\n".join(L)


def dusha_slota(ceh: str, slot: str, s_domom: bool = False) -> dict:
    """ЧИТАЮЩИЙ КОНЕЦ. Пара (цех, слот) → носитель + его душа текстом.

    Возвращает {"носитель": {...}, "душа": "...", "magic": int|None}
    или None — слот пуст (честная вакансия, не ошибка).

    Читает БЕЗ побочек: nakryt_stol_chisto не пишет в память жителя
    (vydoh_stol пишет на каждый вызов — на баре его звать нельзя).
    """
    try:
        from cartridge_registry import resolve_para
    except Exception as e:
        print(f"[МОСТ] ⚠️  реестр не поднялся ({e})")
        return None

    n = resolve_para(ceh, slot)
    if not n:
        print(f"[МОСТ] ℹ️  слот {ceh}/{slot} — вакансия, носителя нет")
        return None

    d = _dvizhok(n["папка"])
    if d is None:
        return {"носитель": n, "душа": "", "magic": n.get("magic")}

    try:
        stol = d.nakryt_stol_chisto()
    except AttributeError:
        print("[МОСТ] ⚠️  в dvizhok нет nakryt_stol_chisto — "
              "нужен patch_dvizhok_stol_chisto_vyvod_v1")
        return {"носитель": n, "душа": "", "magic": n.get("magic")}

    return {
        "носитель": n,
        "душа": _sobrat_dushu(stol, s_domom=s_domom),
        "magic": n.get("magic"),
        "стол": stol,
    }


def magic_slota(ceh: str, slot: str):
    """Магик носителя этого слота — из МАСКИ, единственной правды.
    Не из константы в мозге (их было четыре копии — так и разъезжались)."""
    try:
        from cartridge_registry import resolve_para
        n = resolve_para(ceh, slot)
        return (n or {}).get("magic")
    except Exception:
        return None


def temperatura_slota(ceh: str, slot: str):
    """НАТУРА → ТЕМПЕРАТУРА. Как думает голова, а не только что читает.

    До этого моста stress_to_temperature() в llm.py была МЁРТВОЙ: ни один
    мозг не передавал temperature, все девять думали на дефолте модели.
    Душа была буквами в промпте — на поведение головы не влияла.

    Заряд — маятник состояния (Чертёж):
        минус ДАВИТ → stress → выше температура (нервный, хаотичный)
        плюс  ГРЕЕТ → light  → ниже температура (спокойный, точный)
    Упрямство — натура: упрямого мотает МЕНЬШЕ (устойчив к состоянию).

    Честный None — носителя нет: тогда мозг зовёт модель как раньше,
    на дефолте (ничего не ломаем).   # NATURA_V_TEMPERATURU_V1
    """
    d = dusha_slota(ceh, slot)
    if not d or not d.get("стол"):
        return None
    stol = d["стол"]
    try:
        from llm import stress_to_temperature
    except Exception:
        return None

    charge = float(stol.get("заряд") or 0.0)
    dna = stol.get("натура") or {}
    stubborn = float(dna.get("Stubbornness", 0.5) or 0.5)

    stress = max(0.0, -charge)              # минус давит
    light = 0.5 + max(0.0, charge) / 2.0    # плюс греет
    t = stress_to_temperature(stress, light)

    # упрямый устойчив: натура гасит размах от состояния
    t = 0.70 + (t - 0.70) * (1.0 - 0.5 * stubborn)
    return round(max(0.3, min(1.2, t)), 2)


# ════════════════════════════════════════════════════════════
# ПИШУЩИЙ КОНЕЦ — суд рынка оседает ОПЫТОМ в носителя
# ════════════════════════════════════════════════════════════

# Порог крайности: рутинная сделка в ЯКОРЯ не идёт (якорей всего 7-10 —
# это ОПЫТ, не журнал). Факт каждой сделки и так лежит в pnl.jsonl и в
# дневнике роли — это ПАМЯТЬ (Чертёж: память ≠ опыт).
KRAYNOST_R = 2.0


# ── РУБИЛЬНИК УЧЁБЫ, ОДИН НА ВСЕХ ───────────────────────────  # SUD_SENSOROV_V2
# Стерильность тестера глушила только запись ТРЕЙДЕРОВ (подменой
# zapisat_vyvod). Сенсоры пишут другой рукой (zapisat_vyvod_pare) и шли бы
# МИМО — стерильный бэктест калечил бы Веру с Моржом. Один флаг на всё.
UCHIT = True


def _pisat_mozhno() -> bool:
    """Разрешена ли запись в паспорт живого жителя (учебный прогон/реал)."""
    return bool(UCHIT)


def sudit_po_kotinu(direction, entry_bias, pnl_r, close_reason, bar) -> str:
    """Вывод из сделки — СЧИТАЕТ КОД, не LLM (числа не галлюцинируют).

    §12 Котина: направление — факт структуры, не мнение. Идти ЗА компасом —
    обычный хлеб. Идти ПРОТИВ — редкая осознанная ставка с ценой.
    Отсюда суд:
      минус ПРОТИВ ветра → УРОК (всегда значим, даже мелкий: это тот самый
                            систематический стоп, за который мы патчили промт)
      минус ПО ветру      → честная плата (значим только крупный)
      плюс ПРОТИВ ветра   → повезло, не система (не путать удачу с правотой)
      плюс ПО ветру       → так и работает (значим только крупный)

    Пустая строка = сделка рутинная, в якоря не идёт.
    """
    if pnl_r is None:
        return ""
    r = round(float(pnl_r), 2)
    kray = abs(r) >= KRAYNOST_R
    protiv = bool(entry_bias) and bool(direction) and (
        (entry_bias == "BULL" and direction == "SHORT") or
        (entry_bias == "BEAR" and direction == "LONG")
    )
    shtil = not entry_bias
    when = f" ({bar})" if bar else ""
    veter = ("против компаса" if protiv
             else "в штиль (компас молчал)" if shtil
             else "по компасу")

    # причина закрытия доезжает не всегда (_settle шлёт судье pos, а
    # close_reason живёт в record) — молчим, а не выдумываем: якорь не врёт.
    why = f", {close_reason}" if close_reason else ""

    if r < 0 and protiv:
        return (f"Минус {r}R{when}: вошёл {direction} {veter}{why}. "
                f"Против ветра — редкая ставка, не хлеб.")
    if r < 0 and kray:
        return (f"Минус {r}R{when}: {direction} {veter}{why}. "
                f"Плата по системе — не повод менять систему.")
    if r > 0 and protiv and kray:
        return (f"Плюс {r}R{when}: {direction} {veter}. Взял — но против "
                f"ветра это удача, а не правота. Не строй на этом систему.")
    if r > 0 and kray:
        return f"Плюс {r}R{when}: {direction} {veter}. Так это и работает."
    return ""   # рутина — живёт в pnl.jsonl, в опыт не лезет


# ── КЛЮЧИ ПАТТЕРНОВ (YAKORYA_DVA_YARUSA_V1) ──────────────────────────
# Природа вывода, не его точный текст. dvizhok использует ключ, чтобы
# копить повторы; сниффинг безопасен — это НАШИ ЖЕ шаблоны, не LLM.
# Порядок проверки важен: специфичные маркеры раньше общих.

def _klyuch_trader(vyvod: str) -> str:
    if "удача, а не правота" in vyvod:
        return "трейдер_плюс_удача_против_ветра"
    if "редкая ставка, не хлеб" in vyvod:
        return "трейдер_минус_против_ветра"
    if "Плата по системе" in vyvod:
        return "трейдер_минус_по_системе"
    if "Так это и работает" in vyvod:
        return "трейдер_плюс_по_ветру"
    return "трейдер_прочее"


def _klyuch_sensora(vyvod: str) -> str:
    if "МОЯ ОШИБКА" in vyvod:
        return "сенсор_ошибка"
    if "ПРОСПАЛ" in vyvod:
        return "сенсор_проспал"
    if "Подтвердилось" in vyvod:
        return "сенсор_подтвердилось"
    if "молчание было право" in vyvod:
        return "сенсор_молчание_право"
    return "сенсор_прочее"


def _dyhnut(n: dict, pnl_r, delitel: float) -> dict:
    """Общий вдох: событие качнуло человека. Заряд оседает в паспорт.

    ЭТО НЕ ОПЫТ (Чертёж Гл.4.2: маятник состояния — «обучение первого
    уровня, без понимания»). Опыт — выводы словами, отдельная труба.
    Здесь только дыхание: минус давит, плюс греет.   # DYHANIE_SDELKI_V1
    """
    if pnl_r is None:
        return {"вдох": False, "причина": "нет исхода"}
    if not _pisat_mozhno():
        return {"вдох": False, "причина": "стерильный прогон"}
    d = _dvizhok(n["папка"])
    if d is None:
        return {"вдох": False, "причина": "движок не поднялся"}
    try:
        r = float(pnl_r)
        sila = min(1.0, abs(r) / delitel)
        tonus = "плюс" if r > 0 else "минус" if r < 0 else "ровно"
        res = d.vdoh("работа", sila=sila, svezhest=1.0, tonus=tonus)
        d.sохранить()
        print(f"[МОСТ] 🫁 {n['имя']}: {r:+.1f}R → заряд {res.get('заряд')}")
        return {"вдох": True, "заряд": res.get("заряд")}
    except Exception as e:
        print(f"[МОСТ] ⚠️  вдох не прошёл ({e})")
        return {"вдох": False, "причина": str(e)}


def dyhnut_sdelkoy(magic, pnl_r) -> dict:
    """ТРЕЙДЕР ДЫШИТ СВОЕЙ СДЕЛКОЙ — на КАЖДОМ исходе, даже рутинном.

    Чертёж Гл.4.4: «Единичное событие меняет ЗАРЯД, не фильтр». Раньше
    вдох жил внутри zapisat_vyvod — то есть внутри ЗАПИСИ ОПЫТА, и при
    рутинной сделке (минус по ветру, |R|<2) не случался вовсе: человек
    терял деньги и ничего не чувствовал. Теперь дыхание своё.
    Своя шкура — делитель 3 (бьёт сильно).   # DYHANIE_SDELKI_V1
    """
    try:
        from cartridge_registry import resolve_by_magic
    except Exception:
        return {"вдох": False, "причина": "нет реестра"}
    n = resolve_by_magic(magic)
    if not n:
        return {"вдох": False, "причина": "носитель не найден"}
    return _dyhnut(n, pnl_r, 3.0)


def dyhnut_slovom(ceh: str, slot: str, pnl_r) -> dict:
    """СЕНСОР ДЫШИТ ЧУЖОЙ СДЕЛКОЙ, но по СВОЕМУ слову.

    Он не был в позиции — деньги не его. Но его слово повело туда
    трейдера, и исход задевает. Чужая шкура — делитель 6 (вполовину
    тише, чем своя).   # DYHANIE_SDELKI_V1
    """
    try:
        from cartridge_registry import resolve_para
    except Exception:
        return {"вдох": False, "причина": "нет реестра"}
    n = resolve_para(ceh, slot)
    if not n:
        return {"вдох": False, "причина": f"слот {ceh}/{slot} пуст"}
    return _dyhnut(n, pnl_r, 6.0)


def zapisat_vyvod(magic, vyvod: str, pnl_r=None, limit: int = 10) -> dict:
    """ПИШУЩИЙ КОНЕЦ. magic закрытой позиции → носитель → его якоря.

    Заодно ЖИВОЙ ВДОХ: сделка качает заряд носителя (плюс греет, минус
    давит), сила — по |pnl_r|. Это дыхание, а не оценка: заряд ≠ опыт.

    Честный no-op, если носителя по магику нет — торговый цикл не рвём.
    """
    if not vyvod:
        return {"дописано": False, "причина": "рутина (в опыт не идёт)"}
    if not _pisat_mozhno():   # SUD_SENSOROV_V2: рубильник учёбы
        return {"дописано": False, "причина": "стерильный прогон"}
    try:
        from cartridge_registry import resolve_by_magic
    except Exception as e:
        print(f"[МОСТ] ⚠️  реестр не поднялся ({e})")
        return {"дописано": False, "причина": "нет реестра"}

    n = resolve_by_magic(magic)
    if not n:
        print(f"[МОСТ] ⚠️  magic {magic} → носителя нет "
              f"(магик в маске? patch_magic_v_masku_v1)")
        return {"дописано": False, "причина": "носитель не найден"}

    d = _dvizhok(n["папка"])
    if d is None:
        return {"дописано": False, "причина": "движок не поднялся"}

    # ── ВДОХ: сделка тронула человека ────────────────────────────
    try:
        if pnl_r is not None:
            sila = min(1.0, abs(float(pnl_r)) / 3.0)
            tonus = "плюс" if float(pnl_r) > 0 else "минус" if float(pnl_r) < 0 else "ровно"
            d.vdoh("работа", sila=sila, svezhest=1.0, tonus=tonus)
            d.sохранить()          # заряд оседает в паспорт
    except Exception as e:
        print(f"[МОСТ] ⚠️  вдох не прошёл ({e}) — пишу вывод без дыхания")

    # ── ВЫВОД в якоря (нога Опыта) ───────────────────────────────
    # ЗАЩИТА ОТ ПОВТОРА (поймано на прогоне 12.07): dopisat_vyvod бьёт
    # дубль по ТОЧНОЙ строке. Но один и тот же бар в двух прогонах даёт
    # чуть разный текст — и якоря забились бы вариациями ОДНОГО урока,
    # вытеснив настоящий старый опыт (их всего 7-10!). Поэтому сверяем по
    # СУТИ: дата входа + направление уже есть среди якорей → не пишем.
    try:
        _raw = d.p.get("Anchor_Points", "") or ""
        _est = [x.strip() for x in _raw.replace("\\n", "\n").split("\n") if x.strip()]
        # YAKORYA_DVA_YARUSA_V1: та же сделка не должна засчитаться как ВТОРОЙ
        # повтор паттерна — сверяем и черновики, не только устойчивые якоря.
        # DVER_V_METKI_V1: черновики уехали из паспорта в 3_маяки.
        # Сверяем ВСЕ ТРИ этажа — иначе повтор проскочит.
        try:
            _est += [dd.get("текст", "") for dd in d.mayaki()]
            _est += [dd.get("текст", "") for dd in d.metki()]
        except AttributeError:
            _est += [dd.get("текст", "") for dd in (d.p.get("Draft_Anchors") or [])]
        _bar = ""
        if "(" in vyvod and ")" in vyvod:
            _bar = vyvod[vyvod.find("(") + 1:vyvod.find(")")]
        _dir = "SHORT" if "SHORT" in vyvod else "LONG" if "LONG" in vyvod else ""
        if _bar and _dir:
            for _e in _est:
                if _bar in _e and _dir in _e:
                    return {"дописано": False,
                            "причина": f"этот урок уже есть ({_bar} {_dir})"}
    except Exception:
        pass

    try:
        res = d.dopisat_vyvod(vyvod, limit=limit,
                              pattern=_klyuch_trader(vyvod),
                              otkuda="рынок")   # DVER_V_METKI_V1: голос вывода назван   # YAKORYA_DVA_YARUSA_V1
    except AttributeError:
        print("[МОСТ] ⚠️  в dvizhok нет dopisat_vyvod — "
              "нужен patch_dvizhok_stol_chisto_vyvod_v1")
        return {"дописано": False, "причина": "нет руки опыта"}

    if res.get("тип") == "черновик":
        print(f"[МОСТ] 📝 черновик → {n['имя']}: «{vyvod[:60]}...» "
              f"(раз: {res.get('раз')}/3)")
    elif res.get("дописано"):
        print(f"[МОСТ] 🧠 ОПЫТ → {n['имя']}: «{vyvod}» "
              f"(якорей: {res.get('якорей')})")
    return res


# ════════════════════════════════════════════════════════════
# Самопроверка: python Биржа/nositel.py
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import io as _io
    if isinstance(_sys.stdout, _io.TextIOWrapper):
        try:
            _sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("═══ МОСТ К НОСИТЕЛЮ — самопроверка ═══")
    d = dusha_slota("торговый_хаос", "A07")
    if not d:
        print("✗ A07 → носителя нет")
        raise SystemExit(1)
    print(f"A07 → {d['носитель']['имя']} (magic {d['magic']})")
    print("--- душа, как её увидит модель ---")
    print(d["душа"])
    print("--- суд по Котину (сухие числа, без LLM) ---")
    for dir_, bias, r, why in [
        ("SHORT", "BULL", -1.0, "стоп против ветра"),
        ("LONG",  "BULL", -1.0, "стоп по ветру (рутина)"),
        ("LONG",  "BULL", -2.4, "крупный минус по ветру"),
        ("LONG",  "BULL",  2.6, "крупный плюс по ветру"),
        ("SHORT", "BULL",  2.6, "крупный плюс против ветра"),
        ("LONG",  None,    0.4, "мелочь в штиль"),
    ]:
        v = sudit_po_kotinu(dir_, bias, r, "STOP_LOSS", "2010.05.13")
        print(f"  [{why}] → {v or '(рутина, в опыт не идёт)'}")
    print("═══ конец самопроверки ═══")


# ════════════════════════════════════════════════════════════
# СУД СЕНСОРА — их опыт есть работа над своими ошибками (слово Шефа)
# ────────────────────────────────────────────────────────────
# У трейдера судья очевиден: рынок, деньги, R. А сенсор не торгует —
# он НАКРЫВАЕТ СТОЛ. Его правота проверяется ИСХОДОМ, до которого он
# сам не дожил: сделкой, которую его слово породило или проспало.
#
# Симметрия (без LLM, всё считает код):
#     ЗВАЛ  + минус  → ОШИБКА (всегда в опыт — это и есть его школа)
#     МОЛЧАЛ + крупный плюс → ПРОСПАЛ (всегда в опыт)
#     ЗВАЛ  + крупный плюс  → подтверждение
#     МОЛЧАЛ + крупный минус → «моё молчание было право»
#     остальное → рутина, в якоря не идёт (память живёт в журналах)
#
# «Звал» — значит его показание тянуло В СТОРОНУ сделки. Считается
# по слепку стола НА БАРЕ ВХОДА (не по текущему: стол перетирается
# каждый бар — судить сенсора по чужому бару было бы клеветой).
# ════════════════════════════════════════════════════════════

SENSOR_SLOTS = {           # ключ в trading_state → слот цеха
    "iskra": "A01",
    "morj":  "A02",
    "panic": "A03",
    "hans":  "A04",
}


def _zval(key: str, pokazanie: dict, direction: str):
    """Тянуло ли показание сенсора В СТОРОНУ сделки. None — не судим."""
    if not pokazanie or not direction:
        return None
    if key == "iskra":
        if pokazanie.get("t1_status") not in ("DETECTED", "CONFIRMED"):
            return False
        kompas = pokazanie.get("trend_direction")
        if not kompas:
            return False
        return ((kompas == "BULL" and direction == "LONG") or
                (kompas == "BEAR" and direction == "SHORT"))
    if key == "morj":
        # звал = подтвердил масштаб (зверь проснулся / волна 1 засчитана)
        return bool(pokazanie.get("wave_1_validated")) or             pokazanie.get("morj_status") == "AWAKE"
    if key == "panic":
        faza = pokazanie.get("panic_phase")
        # толпа тянет в лонг на жадности, в шорт — на ликвидации
        if faza in ("FOMO", "GREED"):
            return direction == "LONG"
        if faza in ("LIQUIDATION", "PANIC"):
            return direction == "SHORT"
        return False
    if key == "hans":
        if not pokazanie.get("fractal_valid"):
            return False
        side = pokazanie.get("fractal_side")
        if not side:
            return True            # фрактал есть, стороны не назвал
        return ((side in ("UP", "LONG") and direction == "LONG") or
                (side in ("DOWN", "SHORT") and direction == "SHORT"))
    return None


def _chto_skazal(key: str, p: dict) -> str:
    """Его собственное показание — словами, коротко. Для якоря."""
    if key == "iskra":
        zp = p.get("zero_point_price")
        return (f"точка {p.get('t1_status','—')} "
                f"{p.get('trend_direction') or ''} "
                f"{('@' + str(zp)) if zp else ''}").strip()
    if key == "morj":
        return (f"пасть {p.get('morj_status','—')}, "
                f"волна1={'да' if p.get('wave_1_validated') else 'нет'}")
    if key == "panic":
        return f"толпа {p.get('panic_phase','—')}"
    if key == "hans":
        fp = p.get("fractal_price")
        return (f"фрактал {'валиден' if p.get('fractal_valid') else 'нет'} "
                f"{p.get('fractal_side') or ''} {('@' + str(fp)) if fp else ''}").strip()
    return "—"


def sudit_sensora(key: str, pokazanie: dict, direction, pnl_r,
                  trader: str = "", bar: str = "") -> str:
    """Вывод сенсора из ЧУЖОЙ сделки, которую породило его слово.
    Пустая строка = рутина, в опыт не идёт."""
    if pnl_r is None or not pokazanie:
        return ""
    r = round(float(pnl_r), 2)
    kray = abs(r) >= KRAYNOST_R
    zval = _zval(key, pokazanie, direction)
    if zval is None:
        return ""
    skazal = _chto_skazal(key, pokazanie)
    kto = (trader or "трейдер").capitalize()
    when = f" ({bar})" if bar else ""

    if zval and r < 0:
        return (f"МОЯ ОШИБКА{when}: я дал «{skazal}» — {kto} вошёл "
                f"{direction} и получил {r}R. Моё слово повело в минус.")
    if (not zval) and r > 0 and kray:
        return (f"ПРОСПАЛ{when}: я дал «{skazal}» — а {kto} взял "
                f"{direction} на {r}R без меня. Движение было, я его не увидел.")
    if zval and r > 0 and kray:
        return (f"Подтвердилось{when}: «{skazal}» — {kto} взял {r}R "
                f"по моему слову. Так это и работает.")
    if (not zval) and r < 0 and kray:
        return (f"Моё молчание было право{when}: я не звал, {kto} вошёл "
                f"{direction} сам и получил {r}R.")
    return ""


def zapisat_vyvod_pare(ceh: str, slot: str, vyvod: str,
                       pnl_r=None, limit: int = 10) -> dict:
    """ПИШУЩИЙ КОНЕЦ СЕНСОРА: пара (цех, слот) → носитель → его якоря.
    Магика у сенсора нет и быть не должно — позиций не держит.
    Дыхание тише, чем у трейдера: чужая сделка трогает, но не так,
    как своя (сила вдвое меньше)."""
    if not vyvod:
        return {"дописано": False, "причина": "рутина"}
    if not _pisat_mozhno():   # SUD_SENSOROV_V2: рубильник учёбы
        return {"дописано": False, "причина": "стерильный прогон"}
    try:
        from cartridge_registry import resolve_para
    except Exception as e:
        print(f"[МОСТ] ⚠️  реестр не поднялся ({e})")
        return {"дописано": False, "причина": "нет реестра"}

    n = resolve_para(ceh, slot)
    if not n:
        return {"дописано": False, "причина": f"слот {ceh}/{slot} пуст"}

    d = _dvizhok(n["папка"])
    if d is None:
        return {"дописано": False, "причина": "движок не поднялся"}

    try:
        if pnl_r is not None:
            sila = min(1.0, abs(float(pnl_r)) / 6.0)   # чужая сделка — тише
            tonus = ("минус" if "ОШИБКА" in vyvod or "ПРОСПАЛ" in vyvod
                     else "плюс")
            d.vdoh("работа", sila=sila, svezhest=1.0, tonus=tonus)
            d.sохранить()
    except Exception as e:
        print(f"[МОСТ] ⚠️  вдох не прошёл ({e})")

    # YAKORYA_DVA_YARUSA_V1: та же защита от ложного счёта, что у трейдера —
    # не дать одному и тому же бару засчитаться дважды в раз повтора.
    try:
        _raw = d.p.get("Anchor_Points", "") or ""
        _est = [x.strip() for x in _raw.replace("\\n", "\n").split("\n") if x.strip()]
        # DVER_V_METKI_V1: черновики уехали из паспорта в 3_маяки.
        # Сверяем ВСЕ ТРИ этажа — иначе повтор проскочит.
        try:
            _est += [dd.get("текст", "") for dd in d.mayaki()]
            _est += [dd.get("текст", "") for dd in d.metki()]
        except AttributeError:
            _est += [dd.get("текст", "") for dd in (d.p.get("Draft_Anchors") or [])]
        _bar = ""
        if "(" in vyvod and ")" in vyvod:
            _bar = vyvod[vyvod.find("(") + 1:vyvod.find(")")]
        if _bar:
            for _e in _est:
                if _bar in _e:
                    return {"дописано": False,
                            "причина": f"этот урок уже есть ({_bar})"}
    except Exception:
        pass

    try:
        res = d.dopisat_vyvod(vyvod, limit=limit,
                              pattern=_klyuch_sensora(vyvod),
                              otkuda="рынок")   # DVER_V_METKI_V1: голос вывода назван   # YAKORYA_DVA_YARUSA_V1
    except AttributeError:
        return {"дописано": False, "причина": "нет руки опыта"}

    if res.get("тип") == "черновик":
        print(f"[МОСТ] 📝 черновик → {n['имя']} ({slot}): «{vyvod[:60]}...» "
              f"(раз: {res.get('раз')}/3)")
    elif res.get("дописано"):
        print(f"[МОСТ] 🧠 ОПЫТ → {n['имя']} ({slot}): «{vyvod[:60]}...»")
    return res


# ═══════════════════════════════════════════════════════════
# MEMORY_REQUEST_BIRZHA_V1 — ВОЛЯ ЖИТЕЛЯ ВСПОМНИТЬ
# ═══════════════════════════════════════════════════════════
# Шлюз (|заряд|>0.8 → архив) работает от СОСТОЯНИЯ. Запрос — от ВОЛИ.
# Спокойный Илья на Точке Ноль увидит знакомый разворот и ЗАХОЧЕТ
# вспомнить — а шлюз ему этого не даст, потому что он спокоен.
# Закон -2 (Спринт 43): «вспомнить можно в любом месте, БЕЗУСЛОВНО».
#
# ОДНА ДВЕРЬ на всех — как dusha_slota. В девять мозгов не вписываем:
# через месяц было бы девять копий, которые разъехались.
# Правило: ОДИН ЗАПРОС ЗА РАН. Архив не льётся сам.
# ═══════════════════════════════════════════════════════════

MEMORY_MARKER = "MEMORY_REQUEST:"


def izvlech_zapros(text: str) -> str:
    """Первая строка MEMORY_REQUEST: <что вспомнить> из ответа жителя.
    Один запрос за ран — берём ТОЛЬКО первую (канон -2)."""
    for line in (text or "").splitlines():
        if MEMORY_MARKER in line:
            return line.split(MEMORY_MARKER, 1)[1].strip()
    return ""


def ubrat_zapros(text: str) -> str:
    """Техническая строка вычищается — она не часть ответа, она сигнал."""
    lines = [l for l in (text or "").splitlines() if MEMORY_MARKER not in l]
    return "\n".join(lines).strip()


def vspomnit_slotom(ceh: str, slot: str, zapros: str, limit: int = 6) -> str:
    """Житель, сидящий в слоте, копает СВОЮ память по своему запросу.
    Ищет по sensory + resonance + archive (dvizhok.vspomnit).
    Пусто — значит следа нет. Честно, без выдумок."""
    if not (zapros or "").strip():
        return ""
    try:
        n = dusha_slota(ceh, slot)
        if not n:
            return ""
        # PAMYAT_DVA_BAGA_V1: было "дом" (не то поле — это прописка
        # из _sobrat_dushu). Папка резидента — "папка" (см.
        # dusha_slota выше в этом же файле, n["папка"]).
        d = _dvizhok(n["носитель"]["папка"])
        if d is None:
            return ""
        return d.vspomnit(zapros, limit=limit) or ""
    except Exception as e:
        print(f"[МОСТ] ⚠️  вспомнить не вышло ({ceh}/{slot}): {e}")
        return ""


def podnyat_iz_arhiva(ceh: str, slot: str, otvet: str) -> tuple:
    """ПОЛНЫЙ ЦИКЛ ЗАПРОСА — одной дверью.

    Житель ответил. Если он ПОПРОСИЛ вспомнить — копаем и отдаём
    найденное для ВТОРОГО вызова модели. Если не просил — ничего
    не тратим.

    Возвращает (запрос, поднятое). Оба пустые — житель не просил
    или следа нет.
    """
    zapros = izvlech_zapros(otvet)
    if not zapros:
        return "", ""
    naydeno = vspomnit_slotom(ceh, slot, zapros)
    if naydeno:
        print(f"[МОСТ] 🧠 {ceh}/{slot} вспоминает: «{zapros[:50]}» — "
              f"поднято {len(naydeno.splitlines())} след(ов)")
    else:
        print(f"[МОСТ] 🧠 {ceh}/{slot} искал «{zapros[:50]}» — следа нет")
    return zapros, naydeno


def blok_pamyati(zapros: str, naydeno: str) -> str:
    """Найденное — в контекст следующего шага. Пусто тоже говорим:
    «следа нет» — это ЧЕСТНЫЙ ответ, не ошибка. Житель должен знать,
    что он искал и не нашёл, а не думать, что его не услышали."""
    if not zapros:
        return ""
    if not naydeno:
        return (f"\n\n=== 📚 ТЫ ИСКАЛ В ПАМЯТИ: «{zapros}» ===\n"
                "Следа нет. Такого с тобой не было — или ты не запомнил.\n"
                "Решай без этого.")
    return (f"\n\n=== 📚 ПОДНЯТО ИЗ ТВОЕЙ ПАМЯТИ (ты просил: «{zapros}») ===\n"
            f"{naydeno}\n"
            "Это твоё, было с тобой. Теперь решай.")
