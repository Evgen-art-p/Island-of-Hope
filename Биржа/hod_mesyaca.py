# -*- coding: utf-8 -*-
# HOD_MESYACA_V1 / HOD_STARSHIY_V2 — история старшего хода у трейдера (A08)
"""
СЛОВО ШЕФА (13.10, вечер)
    «Идёт ход — куда? вверх, вниз? что он делает, этот ход? давно? — это на
    месяце. Если дал разворотник с дивером — пусть входит и считает, что в
    откат вошёл; смотрит и ведёт. Увидел у этого отката разворот — значит,
    работает на продолжение тренда.»
    14.10: «делай как по канону, пусть работает; главное, чтобы бумаги он
    видел непротиворечивые». И в тот же день, после прогона на H4: старший
    этаж — через один выше рабочего (компас): для дневки месяц, для H4
    неделя. Слово и свеча в сценарии берутся от рабочего этажа (V2).

ЧТО ЗДЕСЬ
    История старшего хода — ЕГО слова (куда, что делает, с какого времени).
    Старший этаж — через один выше рабочего: D1 → MN1, H4 → W1, H1 → D1.
    Город их хранит и кладёт ему первыми на каждом баре. Пересмотр — только
    по факту: закрылась новая свеча старшего этажа, цена ушла за начало хода
    или обновила его край. Факта нет — история стоит (на одной картинке
    месяц читался по-разному, девять ответов на одной свече).

    Вход помечается относительно истории: против старшего хода — «в откат»,
    по нему — «по ходу». Пометка — факт из его же слов, не суждение города.

    Висящая заявка: город пишет факт — ушла ли цена за край разворотника,
    закрылась ли новая свеча старшего этажа. При CANCEL — рядом факт города и его
    причина.

    Город ничего не решает и ничего не запрещает: хранит, считает, показывает.
"""
from __future__ import annotations

import json
import re
import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))
_KOREN = _BIRZHA.parent

SLOTY = ("A08",)
PROGONOV_HRANIM = 40


def _nash(slot) -> bool:
    # MESTA_PO_POMETKE_V1: место уровня «продвинутый новичок» — по пометке в паспорте цеха
    try:
        import mesto_urovnya as _md
        return _md.eto_mesto_urovnya(slot)
    except Exception:
        return str(slot or "").strip().upper() in SLOTY


def _ceh(slot) -> str:
    """MESTA_PO_POMETKE_V1: цех, где стоит место (не всегда торговый_хаос)."""
    try:
        import mesto_urovnya as _md
        return _md.ceh_mesta(slot)
    except Exception:
        return "торговый_хаос"


def _nomer(slot):
    """MESTA_PO_POMETKE_V1: номер счёта места — в его цехе."""
    try:
        import mesto_urovnya as _md
        return _md.nomer_mesta(slot)
    except Exception:
        return {"A06": 100001, "A07": 100002, "A08": 100003}.get(
            str(slot or "").strip().upper())


# Старший этаж и его имя — через один выше рабочего (компас).
# падежи: кто/что, кого/чего, кого/что, о ком
_IMENA = {"MN1": ("месяц", "месяца", "месяц", "месяце"),
          "W1": ("неделя", "недели", "неделю", "неделе"),
          "D1": ("дневка", "дневки", "дневку", "дневке"),
          "H4": ("H4", "H4", "H4", "H4"),
          "H1": ("H1", "H1", "H1", "H1")}


def starshiy(tf) -> str:
    try:
        import cherez_etazh as _ce
        return _ce.etazh_cherez(str(tf or "")) or ""
    except Exception:
        return {"D1": "MN1", "H4": "W1", "H1": "D1"}.get(str(tf or "").upper(), "")


def imya(etazh, padezh=0) -> str:
    e = str(etazh or "").upper()
    return _IMENA.get(e, (e or "старший этаж",) * 4)[padezh]


def _etazh_ist(ist, tf=None) -> str:
    return str((ist or {}).get("этаж") or starshiy(tf) or "MN1")


def _arg(args, chto):
    """Его слово из приказа: новое имя поля (старший_…) или прежнее (месяц_…)."""
    return str(args.get("старший_" + chto) or args.get("месяц_" + chto) or "").strip()


def _put(slot) -> Path:
    return (_KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха" / _ceh(slot)
            / "слоты" / str(slot).strip().upper() / "данные" / "ход_месяца.json")


def _sostoyanie() -> dict:
    try:
        from hooks import load_trading_state
        return load_trading_state() or {}
    except Exception:
        return {}


def _progon() -> str:
    return str(((_sostoyanie().get("прогон") or {}).get("id")) or "живая")


def _bar_seychas() -> str:
    t = _sostoyanie()
    return str((t.get("рынок") or {}).get("бар") or t.get("бар") or "")


def _d(x) -> str:
    return str(x or "")[:10]


def _chitat(slot) -> dict:
    p = _put(slot)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def _pisat(slot, d: dict) -> None:
    p = _put(slot)
    try:
        pr = d.get("прогоны") or {}
        if len(pr) > PROGONOV_HRANIM:
            for k in list(pr.keys())[:-PROGONOV_HRANIM]:
                pr.pop(k, None)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
    except Exception as e:
        print(f"[ХОД МЕСЯЦА] не записался ({e})")


def _yashchik(d: dict, symbol, progon=None) -> dict:
    progon = progon or _progon()
    d["последний_прогон"] = progon
    pr = d.setdefault("прогоны", {})
    if progon in pr:                      # свежий прогон — в конец очереди
        pr[progon] = pr.pop(progon)
    return pr.setdefault(progon, {}).setdefault(str(symbol).strip().upper(), {})


def _yashchik_chitat(slot, symbol, progon=None) -> dict:
    d = _chitat(slot)
    return (((d.get("прогоны") or {}).get(progon or _progon()) or {})
            .get(str(symbol).strip().upper()) or {})


# ── его слова → одно из немногих значений ───────────────────────
_MES = (("январ", 1), ("феврал", 2), ("март", 3), ("апрел", 4), ("май", 5),
        ("мая", 5), ("мае", 5), ("июн", 6), ("июл", 7), ("август", 8),
        ("сентябр", 9), ("октябр", 10), ("ноябр", 11), ("декабр", 12))


def norm_hod(s) -> str:
    s = str(s or "").strip().lower()
    if not s:
        return ""
    if any(w in s for w in ("нет хода", "нет тренд", "боков", "флэт", "флет",
                            "топчет", "внутри")):
        return "нет хода"
    if any(w in s for w in ("вверх", "рост", "раст", "up", "бычи")):
        return "вверх"
    if any(w in s for w in ("вниз", "паден", "пада", "down", "медвеж")):
        return "вниз"
    return "не знаю"


def norm_delaet(s) -> str:
    s = str(s or "").strip().lower()
    if not s:
        return ""
    if any(w in s for w in ("откат", "коррек", "против")):
        return "откат против хода"
    if any(w in s for w in ("исход", "выдых", "кончает", "заканчив", "дивер",
                            "слабе")):
        return "на исходе"
    if any(w in s for w in ("идёт", "идет", "импульс", "разгар", "по ходу",
                            "продолж", "развива")):
        return "идёт"
    return "не знаю"


def norm_s(s) -> str:
    """С какого времени ход (по месяцам): «2021.06», «2021-06-15», «июнь 2021» → 2021.06."""
    s = str(s or "").strip().lower()
    if not s:
        return ""
    m = re.search(r"((?:19|20)\d{2})[.\-/ ](\d{1,2})(?!\d)", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}.{int(m.group(2)):02d}"
    m = re.search(r"(?:19|20)\d{2}", s)
    if m:
        for pref, n in _MES:
            if pref in s:
                return f"{m.group(0)}.{n:02d}"
        return f"{m.group(0)}.01"
    return ""


# ── факты по барам ───────────────────────────────────────────────
def _bary(symbol, tf="D1") -> list:
    try:
        import istoriya
        return istoriya._vse_bary(str(symbol), str(tf or "D1")) or []
    except Exception:
        return []


def _svecha_mesyaca(symbol, tf, kogda) -> str:
    """Дата последней ЗАКРЫТОЙ свечи старшего этажа к моменту (через один выше tf)."""
    try:
        import cherez_etazh as _ce
        return _ce.kartinka(str(symbol), str(tf or "D1"), kogda) or ""
    except Exception:
        return ""


def _urovni(symbol, hod, s_mes, do_bara, tf="D1"):
    """Начало и край хода по рабочему этажу — строго до свечи do_bara."""
    if hod not in ("вверх", "вниз") or not s_mes:
        return None
    bary = _bary(symbol, tf)
    # Для внутридневных этажей сохраняем бары той же даты, если они
    # закрылись до входной свечи. Для D1 это по-прежнему означает отсечь
    # весь день входа.
    try:
        from volny_kanon import kak_vremya
        cutoff = kak_vremya(do_bara)
        minutes = {"D1": 1440, "H4": 240, "H1": 60,
                   "M30": 30, "M15": 15, "M10": 10, "M5": 5}.get(str(tf or "").upper())
        if cutoff is not None and minutes:
            minute_of_day = cutoff.hour * 60 + cutoff.minute
            minute_of_day = (minute_of_day // minutes) * minutes
            cutoff = cutoff.replace(hour=minute_of_day // 60,
                                    minute=minute_of_day % 60,
                                    second=0, microsecond=0)
            b = []
            for x in bary:
                dt = kak_vremya(x.get("date"))
                if (dt is not None and _d(x.get("date"))[:7] >= s_mes
                        and dt < cutoff):
                    b.append(x)
        else:
            b = [x for x in bary
                 if _d(x.get("date"))[:7] >= s_mes
                 and _d(x.get("date")) < _d(do_bara)]
    except Exception:
        b = [x for x in bary
             if _d(x.get("date"))[:7] >= s_mes
             and _d(x.get("date")) < _d(do_bara)]
    if not b:
        return None
    if hod == "вниз":
        n = max(b, key=lambda x: x["high"])
        k = min(b, key=lambda x: x["low"])
        return {"начало_цена": n["high"], "начало_дата": _d(n.get("date")),
                "край_цена": k["low"], "край_дата": _d(k.get("date"))}
    n = min(b, key=lambda x: x["low"])
    k = max(b, key=lambda x: x["high"])
    return {"начало_цена": n["low"], "начало_дата": _d(n.get("date")),
            "край_цена": k["high"], "край_дата": _d(k.get("date"))}


def fakty(symbol, ist: dict, seychas, tf="D1") -> dict:
    """Что случилось с бара записи истории. Только факты, без выводов."""
    out = {"свеча": None, "за_начало": None, "край": None}
    k_now = _svecha_mesyaca(symbol, tf, seychas)
    k_bylo = ist.get("свеча_месяца") or ""
    if k_now:
        out["свеча"] = (k_now, bool(k_bylo and k_now != k_bylo))
    hod = ist.get("ход")
    nach, kray = ist.get("начало_цена"), ist.get("край_цена")
    if hod in ("вверх", "вниз") and nach is not None and kray is not None:
        b = [x for x in _bary(symbol, tf)
             if _d(ist.get("бар")) < _d(x.get("date")) <= _d(seychas)]
        if not b:
            out["за_начало"] = (False, None, "")
            out["край"] = (False, None, "")
        elif hod == "вниз":
            v = max(b, key=lambda x: x["high"])
            n = min(b, key=lambda x: x["low"])
            out["за_начало"] = (v["high"] > nach, v["high"], _d(v.get("date")))
            out["край"] = (n["low"] < kray, n["low"], _d(n.get("date")))
        else:
            n = min(b, key=lambda x: x["low"])
            v = max(b, key=lambda x: x["high"])
            out["за_начало"] = (n["low"] < nach, n["low"], _d(n.get("date")))
            out["край"] = (v["high"] > kray, v["high"], _d(v.get("date")))
    return out


def est_fakt(f: dict) -> bool:
    return bool((f.get("свеча") or ("", False))[1]
                or (f.get("за_начало") or (False,))[0]
                or (f.get("край") or (False,))[0])


def fakty_slovami(f: dict, ist: dict) -> list:
    L = []
    sv = f.get("свеча")
    if sv:
        L.append(f"новая свеча {imya(_etazh_ist(ist), 1)}: "
                 f"{'ЗАКРЫЛАСЬ' if sv[1] else 'не закрывалась'}"
                 f" (последняя закрытая — {sv[0]})")
    zn, kr = f.get("за_начало"), f.get("край")
    if zn is not None and kr is not None:
        vniz = ist.get("ход") == "вниз"
        L.append(f"цена за начало хода ({'выше' if vniz else 'ниже'} "
                 f"{ist.get('начало_цена')}): "
                 + (f"УШЛА — {zn[1]} ({zn[2]})" if zn[0] else "не уходила"))
        L.append(f"цена обновила край хода ({'ниже' if vniz else 'выше'} "
                 f"{ist.get('край_цена')}): "
                 + (f"ДА — {kr[1]} ({kr[2]})" if kr[0] else "нет"))
    elif ist.get("ход") in ("вверх", "вниз"):
        L.append("начало и край хода по твоему этажу не посчитаны (с какого "
                 "времени ход — не назван, или баров нет)")
    return L


def _postroit(symbol, tf, seychas, hod, delaet, s_mes, slova) -> dict:
    ist = {"ход": hod, "делает": delaet or "", "с": s_mes or "",
           "слова": slova, "бар": seychas, "этаж": starshiy(tf) or "MN1",
           "рабочий": str(tf or "D1").upper(),
           "свеча_месяца": _svecha_mesyaca(symbol, tf, seychas)}
    u = _urovni(symbol, hod, s_mes, seychas, tf)
    if u:
        ist.update(u)
    return ist


# ── рука приказа: записать его слова ─────────────────────────────
def _v_tablo(tablo, args, seychas) -> None:
    """Для отчёта «Тренд, момент, ожидание» — его слова как есть."""
    try:
        from hooks import load_trading_state, save_trading_state
        hod = _arg(args, "ход")
        de = _arg(args, "делает")
        oz = str(args.get("ожидание") or "").strip()
        if not (hod or de or oz):
            return
        t = load_trading_state()
        t.setdefault(tablo, {})["через_этаж"] = {
            "бар": seychas, "через_этаж_ход": hod, "через_этаж": de,
            "ожидание": oz}
        save_trading_state(t)
    except Exception as e:
        print(f"[ХОД МЕСЯЦА] в табло не лёг ({e})")


def zapisat(slot, symbol, tf, tablo, args) -> str:
    if not _nash(slot):
        return ""
    args = args or {}
    seychas = _bar_seychas()
    try:   # SVERKA_S_GORODOM_V1: его разбор расхождений — к сверке этого бара
        _rz = str(args.get("сверка") or "").strip()
        if _rz:
            _d = _chitat(slot)
            _y = _yashchik(_d, symbol)
            _z = _sverka_na_bare(_y, seychas)
            if _z is not None:
                _z["разбор"] = _rz[:1500]
            else:
                _y["сверки"] = (_y.get("сверки") or [])[-79:] + [{
                    "бар": seychas, "разбор": _rz[:1500], "без_руки": True}]
            _pisat(slot, _d)
    except Exception as _e:
        print(f"[СВЕРКА] разбор не записался ({_e})")
    _v_tablo(tablo, args, seychas)
    r_hod = _arg(args, "ход")
    r_de = _arg(args, "делает")
    r_s = _arg(args, "с")
    izm = _arg(args, "изменилось")
    if not (r_hod or r_de or r_s):
        return ""
    hod, de, s_mes = norm_hod(r_hod), norm_delaet(r_de), norm_s(r_s)
    slova = {"ход": r_hod, "делает": r_de, "с": r_s}
    d = _chitat(slot)
    ya = _yashchik(d, symbol)
    ist = ya.get("история")

    if not ist:
        if hod not in ("вверх", "вниз", "нет хода"):
            print(f"[ХОД МЕСЯЦА] {slot}: истории нет, а ход не назван ({r_hod!r})")
            return ""
        ya["история"] = _postroit(symbol, tf, seychas, hod,
                                  de if de != "не знаю" else "", s_mes, slova)
        # Дата создания нужна, чтобы позже не приписать прошлой позиции
        # историю, которой на её входе ещё не существовало.
        ya["история"]["создана"] = seychas or ""
        _pisat(slot, d)
        print(f"[ХОД МЕСЯЦА] ✎ {slot} {symbol}: записана — ход {hod}, "
              f"с {s_mes or '—'}, делает {de or '—'} (бар {seychas})")
        return ""

    hochet = {}
    if hod in ("вверх", "вниз", "нет хода") and hod != ist.get("ход"):
        hochet["ход"] = hod
    if de and de != "не знаю" and de != ist.get("делает"):
        hochet["делает"] = de
    if s_mes and s_mes != ist.get("с"):
        hochet["с"] = s_mes
    if not hochet:
        ist["подтверждена"] = seychas
        _pisat(slot, d)
        return ""

    f = fakty(symbol, ist, seychas, tf)
    bylo = {k: ist.get(k) for k in ("ход", "делает", "с")}
    # Новый край хода ход не ломает — он его продолжает: по нему можно
    # пересмотреть, что ход делает, но не куда он идёт и откуда начался.
    # Куда и откуда — только новая свеча старшего этажа или цена за началом хода.
    _krupnyy = bool((f.get("свеча") or ("", False))[1]
                    or (f.get("за_начало") or (False,))[0])
    _mozhno = est_fakt(f) and (_krupnyy or not ({"ход", "с"} & set(hochet)))
    if _mozhno:
        nov = dict(bylo)
        nov.update(hochet)
        if "ход" in hochet and "с" not in hochet:
            nov["с"] = ""          # ход сменился — начало прежнего к нему не относится
        ya.setdefault("журнал", []).append({
            "бар": seychas, "было": bylo, "стало": nov,
            "изменилось": izm or "(не назвал)",
            "факт": "; ".join(fakty_slovami(f, ist))})
        _novaya_ist = _postroit(symbol, tf, seychas, nov["ход"], nov["делает"],
                                    nov["с"], slova)
        # Время первого появления истории неизменно при последующих пересмотрах.
        _novaya_ist["создана"] = ist.get("создана") or ""
        ya["история"] = _novaya_ist
        _pisat(slot, d)
        print(f"[ХОД МЕСЯЦА] ↻ {slot} {symbol}: пересмотрена по факту — "
              f"{bylo} → {nov}; его слова: {izm or '(не назвал)'}")
        return ""
    pop = {"бар": seychas, "хотел": hochet, "было": bylo, "его_слова": izm}
    ya["последняя_попытка"] = pop
    ya["попытки"] = (ya.get("попытки") or [])[-29:] + [pop]
    _pisat(slot, d)
    print(f"[ХОД МЕСЯЦА] ✗ {slot} {symbol}: хотел сменить {hochet} "
          f"{'без факта' if not est_fakt(f) else 'по новому краю (куда и откуда ход — только по новой свече старшего этажа или цене за началом)'}"
          f" — история стоит ({bylo})")
    return ""


# ── задание на баре: первым делом — сценарий ─────────────────────
def blok(slot, symbol, tf, bar=None) -> str:
    if not _nash(slot):
        return ""
    seychas = bar or _bar_seychas()
    ya = _yashchik_chitat(slot, symbol)
    ist = ya.get("история")
    e = _etazh_ist(ist, tf)
    zag = (f"=== СЦЕНАРИЙ: ИСТОРИЯ СТАРШЕГО ХОДА — {e}, {imya(e)} "
           f"(называл ты, хранит город) ===\n")
    if not ist:
        return (zag + f"Истории старшего хода у тебя пока нет. Старший этаж — "
                f"через один выше твоего {tf}: {e}, {imya(e)}. Открой {imya(e, 2)} "
                f"(рукой pokazat_etazh {e}), посмотри ВЕСЬ рисунок, а не последнюю "
                "свечу, и назови в приказе: старший_ход, старший_делает, "
                "старший_с. Город запомнит и будет класть её тебе первой.\n\n")
    jur = ya.get("журнал") or []
    L = [zag + f"Ход {ist.get('ход')}"
         + (f", с {ist.get('с')}" if ist.get("с") else ", с какого времени — не назван")
         + f". Что делает: {ist.get('делает') or 'не назвал'}."
         + f" Записано на баре {ist.get('бар')}"
         + (f", пересмотров по факту: {len(jur)}" if jur else "") + "."]
    if ist.get("начало_цена") is not None:
        L.append(f"По {tf}: начало хода {ist['начало_цена']} "
                 f"({ist.get('начало_дата')}), край {ist['край_цена']} "
                 f"({ist.get('край_дата')}).")
    f = fakty(symbol, ist, seychas, tf)
    L.append("С той записи — факты города:")
    L += ["  · " + x for x in fakty_slovami(f, ist)]
    _krupnyy = bool((f.get("свеча") or ("", False))[1]
                    or (f.get("за_начало") or (False,))[0])
    if _krupnyy:
        L.append("Факт есть — можешь пересмотреть историю: в приказе новые "
                 "старший_ход / старший_делает / старший_с и в старший_изменилось — "
                 "что именно изменилось. Ничего не изменилось — оставь как есть.")
    elif est_fakt(f):
        L.append("Цена обновила край хода — ход продолжается. Пересмотреть можно "
                 "только то, что он делает (старший_делает, и в старший_изменилось — "
                 "что изменилось). Куда идёт ход и откуда начался — только по новой "
                 f"свече {imya(e, 1)} или если цена ушла за начало хода.")
    else:
        L.append(f"Факта нет — история стоит: картинка {imya(e, 1)} та же, и ответ на "
                 "ней тот же. Повторять её в приказе не нужно.")
    pp = ya.get("последняя_попытка") or {}
    if pp.get("бар") and _d(pp.get("бар")) >= _d(ist.get("бар")):
        L.append(f"(На баре {pp['бар']} ты назвал иначе — {pp.get('хотел')} — "
                 "без подходящего факта. История осталась прежней.)")
    return "\n".join(L) + "\n\n"


# ── вход: что это относительно старшего хода ─────────────────────
def _eto(ist, napr) -> str:
    hod = (ist or {}).get("ход")
    napr = str(napr or "").upper()
    if hod not in ("вверх", "вниз") or napr not in ("LONG", "SHORT"):
        return "нет"
    return "по ходу" if (hod == "вверх") == (napr == "LONG") else "в откат"


def _metka_slovami(eto, hod, e="MN1") -> str:
    if eto == "в откат":
        return (f" Это вход В ОТКАТ: против старшего хода ({e}, {imya(e)}: {hod}, "
                "по твоей истории).")
    if eto == "по ходу":
        return f" Это вход ПО СТАРШЕМУ ХОДУ ({e}, {imya(e)}: {hod}, по твоей истории)."
    return (" Что это за вход относительно старшего хода — сказать не по чему: "
            f"истории хода нет или хода на {imya(e, 3)} нет.")


def _volny(symbol, tf):
    """Счёт волн по AO на рабочем этаже (VOLNY_AO_V1) — факт, не запрет."""
    try:
        import volny_ao as _va
        return _va.schet(symbol, tf), _va
    except Exception as e:
        print(f"[ВОЛНЫ] счёт не вышел ({e})")
        return None, None


def metka_vhoda(slot, symbol, napr, bar=None, chto="ENTER") -> str:
    if not _nash(slot):
        return ""
    d = _chitat(slot)
    ya = _yashchik(d, symbol)
    ist = ya.get("история")
    eto = _eto(ist, napr)
    tf = str((ist or {}).get("рабочий") or "D1")
    oc = {}
    try:   # VOLNY_AO_V3: два основания раздельно
        import volny_ao as _va
        oc = _va.ocenka_vhoda(symbol, tf, napr) or {}
        t_raz = _va.kratko(oc.get("ход"))
        _ml = oc.get("младший") or {}
        if _ml.get("текст"):
            t_raz += f"; младший ({_ml.get('этаж')}): {_ml['текст']}"
    except Exception as e:
        print(f"[ВОЛНЫ] счёт не вышел ({e})")
        t_raz = "не посчитать"
    raz, poh = oc.get("разворот"), oc.get("по_ходу")
    big = oc.get("большой") or {}
    ya["входы"] = (ya.get("входы") or [])[-39:] + [{
        "бар": bar or _bar_seychas(), "направление": str(napr or "").upper(),
        "это": eto, "ход": (ist or {}).get("ход"), "что": chto,
        "этаж": _etazh_ist(ist), "разворот": raz, "разворот_ход": t_raz,
        "по_ходу": poh, "большой": (f"{big.get('ход')}: {big.get('volna')}"
                                     if big.get("ok") and big.get("volna") else None),
        "младший_кончик": (oc.get("младший") or {}).get("кончик")}]
    try:   # PYAT_PUL_V1: сколько пуль сошлось на входе
        import volny_ao as _va2
        _pp = _va2.pyat_pul(symbol, tf, str(napr).upper() == "SHORT", oc.get("ход"))
        ya["входы"][-1]["пуль"] = _pp.get("сошлось")
        ya["входы"][-1]["пуль_из"] = _pp.get("посчитано")
    except Exception as _e_pp:
        print(f"[ВОЛНЫ] пули на входе не посчитались ({_e_pp})")
    try:   # SVERKA_S_GORODOM_V1: сверялся ли он на этом баре и совпал ли с городом
        _z = _sverka_na_bare(ya, ya["входы"][-1]["бар"])
        if _z and _z.get("его"):
            ya["входы"][-1]["сверка_его"] = _z.get("его")
            ya["входы"][-1]["сверка_совпало"] = not _z.get("расхождения")
            ya["входы"][-1]["сверка_разбор"] = _z.get("разбор")
    except Exception:
        pass
    _pisat(slot, d)
    print(f"[ХОД МЕСЯЦА] {slot} {chto} {napr}: {eto} "
          f"(старший ход {_etazh_ist(ist)} {(ist or {}).get('ход') or '—'})")
    def _sl(x):
        return "да" if x is True else ("нет" if x is False else "прочерк")
    print(f"[ВОЛНЫ] {slot} {chto} {napr} на {tf}: разворот — {_sl(raz)} ({t_raz}); "
          f"по ходу — {_sl(poh)}"
          + (" — НИ ОДНОГО ОСНОВАНИЯ ПО ВОЛНАМ" if raz is False and poh is not True else ""))
    t = _metka_slovami(eto, (ist or {}).get("ход"), _etazh_ist(ist))
    # VVOD_CHISTYY_V1: волны, пули, младший, серия стопов — в запись для
    # отчёта, но не в ответ руки: вход — сценарий и три факта (слово Шефа
    # 17.10: «до входа анализа нет, только взгляд… после входа и начинается
    # анализ»). Город покажет это в сверке, когда он в сделке.
    return t


def _moya_zayavka(slot, symbol):
    try:
        from nositel import magic_slota
        moy = _nomer(slot)
    except Exception:
        moy = None
    for p in _sostoyanie().get("positions") or []:
        if str(p.get("status") or "").upper() != "PENDING":
            continue
        if str(p.get("symbol") or "").strip().upper() != str(symbol).strip().upper():
            continue
        if p.get("доливка_города") or _pole_mesta(p, "доливка_места"):
            continue
        if moy is not None and p.get("magic") != moy:
            continue
        return p
    return None


def zayavka_perestavlena(slot, symbol, bar=None) -> str:
    p = _moya_zayavka(slot, symbol)
    if not p:
        return ""
    return metka_vhoda(slot, symbol, p.get("direction"), bar, chto="MOVE_ORDER")


def metka_pozicii(slot, symbol, napr) -> str:
    """Для задания при открытой позиции: что это за сделка, что знает канон и
    что на младшем этаже (MLADSHIY_ETAZH_V1)."""
    # SVERKA_S_GORODOM_V1 / VVOD_CHISTYY_V1: анализ — в сделке, через сверку
    t = _metka_pozicii_bez_mladshego(slot, symbol, napr)
    if t:
        t += ("Ты в сделке — вот где думать: что за ход ты развернул, где он сейчас, "
              "сколько держать, доливать или нет. Сверься с городом рукой "
              "sverka_s_gorodom — сначала своё.\n")
    try:   # VEDENIE_SDELKI_V1: факты сделки — город показывает, решает он
        import vedenie_sdelki as _vs
        t += _vs.blok(slot, symbol, napr)
    except Exception as _e_vs:
        print(f"[ВЕДЕНИЕ] факты сделки не легли ({_e_vs})")
    return t


def _mladshiy_dlya_vedeniya(slot, symbol, napr) -> str:
    """Младший этаж по открытой сделке: тот ход, что идёт в её сторону, — как
    он развивается. Слово Шефа 16.10: «там развитие хода, там точней видно»."""
    try:
        import volny_ao as _va
        ist = _yashchik_chitat(slot, symbol).get("история") or {}
        tf = str(ist.get("рабочий") or "D1").upper()
        jtf = _va.NIZHE.get(tf)
        if not jtf:
            return ""
        ot = _va.schet_hoda(symbol, jtf, str(napr).upper() == "LONG")
        t = (f"Младший ({jtf}) по твоей сделке — ход в её сторону: {_va.kratko(ot)}")
        v = str(ot.get("volna") or "")
        if v.startswith("пятая, край") or v.startswith("после пятой"):
            t += (" На младшем дивер у края твоего хода — для откатной сделки это "
                  "и есть повод выходить по канону; для сделки по ходу — повод "
                  "присмотреться. Решаешь ты.")
        return t + "\n"
    except Exception as e:
        print(f"[ВОЛНЫ] младший по сделке не посчитался ({e})")
        return ""


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:
    """Что это за сделка и что знает канон (как было)."""
    if not _nash(slot):
        return ""
    ya = _yashchik_chitat(slot, symbol)
    vh = [v for v in (ya.get("входы") or [])
          if v.get("направление") == str(napr or "").upper() and v.get("что") == "ENTER"]
    if not vh:
        return ""
    eto, hod = vh[-1].get("это"), vh[-1].get("ход")
    e = str(vh[-1].get("этаж") or "MN1")
    if eto == "в откат":
        return ("Эта сделка — ВХОД В ОТКАТ: ты вошёл против старшего хода (" + e + ", "
                + imya(e) + ": " + str(hod)
                + ", по твоей истории на входе). По канону такой ход обычно короткий: "
                "в откатной сделке не доливают и выходят быстро — на дивере младшего "
                "этажа (посмотреть можно рукой). Увидишь, что этот откат "
                "развернулся обратно по старшему ходу, — это основание закрыть её и "
                "рассмотреть вход по ходу. Это знание, не приказ: держать, закрыть "
                "часть или всё — решаешь ты.\n")
    if eto == "по ходу":
        return ("Эта сделка — ПО СТАРШЕМУ ХОДУ (" + e + ", " + imya(e) + ": " + str(hod)
                + "). По канону это главная сделка: её держат и доливают, пока "
                "старший ход идёт. Решаешь ты.\n")
    return ""


# ── висящая заявка: цел ли разворотник ───────────────────────────
def _fakt_zayavki(slot, symbol, pos, tf="D1"):
    napr = str((pos or {}).get("direction") or "").upper()
    stop = (pos or {}).get("stop")
    if napr not in ("LONG", "SHORT") or not isinstance(stop, (int, float)):
        return None
    seychas = _bar_seychas()
    ya = _yashchik_chitat(slot, symbol)
    vh = [v for v in (ya.get("входы") or []) if v.get("направление") == napr]
    ot = (vh[-1].get("бар") if vh else "") or str(pos.get("_ждёт_с") or "")
    b = ([x for x in _bary(symbol, tf) if _d(ot) < _d(x.get("date")) <= _d(seychas)]
         if ot else [])
    slom, gde = False, ""
    if b:
        if napr == "LONG":
            z = min(b, key=lambda x: x["low"])
            slom, gde = z["low"] <= stop, f"{z['low']} ({_d(z.get('date'))})"
        else:
            z = max(b, key=lambda x: x["high"])
            slom, gde = z["high"] >= stop, f"{z['high']} ({_d(z.get('date'))})"
    sv0, sv1 = _svecha_mesyaca(symbol, tf, ot), _svecha_mesyaca(symbol, tf, seychas)
    svecha = bool(sv0 and sv1 and sv0 != sv1)
    tekst = (f"Факт города по заявке {napr} (стоп {stop} — за краем разворотника), "
             f"с бара {ot or '—'}: цена за край разворотника — "
             + (f"УШЛА: {gde}, этот разворотник сломан" if slom
                else "не уходила, разворотник цел")
             + f"; новая свеча {imya(_etazh_ist(ya.get('история'), tf), 1)} — "
             + ("закрылась" if svecha else "не закрывалась")
             + ".")
    return {"текст": tekst, "сломан": slom, "свеча": svecha, "с_бара": ot}


def fakt_zayavki(slot, symbol, pos, tf="D1") -> str:
    if not _nash(slot):
        return ""
    r = _fakt_zayavki(slot, symbol, pos, tf)
    return (r["текст"] + "\n") if r else ""


def snyatie(slot, symbol, prichina, bar=None) -> str:
    """CANCEL: рядом факт города и причина трейдера — в журнал и в ответ руки."""
    if not _nash(slot):
        return ""
    p = _moya_zayavka(slot, symbol)
    r = _fakt_zayavki(slot, symbol, p, (p or {}).get("timeframe") or "D1") if p else None
    if not r:
        return ""
    d = _chitat(slot)
    ya = _yashchik(d, symbol)
    ya["снятия"] = (ya.get("снятия") or [])[-39:] + [{
        "бар": bar or _bar_seychas(), "направление": p.get("direction"),
        "факт": r["текст"], "сломан": r["сломан"], "свеча": r["свеча"],
        "причина": str(prichina or "").strip() or "(не назвал)"}]
    _pisat(slot, d)
    print(f"[СНЯТИЕ] {slot} {symbol}: {r['текст']} · причина: "
          f"{str(prichina or '').strip() or '(не назвал)'}")
    return " " + r["текст"]


# ── момент: дивер на рабочем этаже по счёту города ──────────────
def storona_sdelki(z: dict) -> str:
    """STORONA_PO_SDELKE_V1: сторона закрытой сделки. В записи о закрытии
    направления нет, а стоп там ПОСЛЕДНИЙ (подвинутый стоп лонга выше входа
    делал из него шорт). Поэтому — по самой сделке: куда ушёл выход от
    входа и в плюс это или в минус."""
    d = str(z.get("direction") or "").upper()
    if d in ("LONG", "SHORT"):
        return d
    try:
        e, x = float(z.get("entry")), float(z.get("exit"))
        pr = z.get("pnl_price")
        pr = float(pr) if pr is not None else float(z.get("pnl_r"))
        if x != e and pr != 0:
            return "LONG" if (x > e) == (pr > 0) else "SHORT"
    except Exception:
        pass
    try:
        st = float(z.get("stop_initial") if z.get("stop_initial") is not None else z.get("stop"))
        return "LONG" if st < float(z.get("entry")) else "SHORT"
    except Exception:
        return ""


def _zhurnaly_zakrytiy() -> list:
    """Все записи о закрытиях: общий журнал и журнал цеха (город пишет в
    общий, а цех может держать свой). Повторы — одна запись."""
    puti = []
    try:
        import hooks as _hk
        for x in (getattr(_hk, "PNL_PATH", None),):
            if x:
                puti.append(Path(x))
        try:
            puti.append(Path(_hk._put_pnl()))
        except Exception:
            pass
    except Exception:
        return []
    vse, vidno = [], set()
    for put in puti:
        try:
            if not put.exists():
                continue
            for line in put.read_text(encoding="utf-8").splitlines():
                try:
                    z = json.loads(line)
                except Exception:
                    continue
                k = (z.get("closed_at"), z.get("entry"), z.get("exit"), z.get("magic"),
                     z.get("trader"), z.get("ts"))   # ZAKRYTIYA_PROGONA_V1: разные прогоны — разные записи
                if k in vidno:
                    continue
                vidno.add(k)
                vse.append(z)
        except Exception:
            continue
    # ZAKRYTIYA_PROGONA_V1: в прогоне — только его сделки (по часам записи,
    # как «Книга места»). Вне прогона — весь журнал, как было.
    _nach = _nachalo_progona()
    if _nach:
        vse = [z for z in vse if str(z.get("ts") or "") >= _nach]
    return vse


# ZAKRYTIYA_PROGONA_V1: прогон, по которому сейчас пишется отчёт (в конце
# прогона метка «прогон» со стола уже снята — отчёт говорит свой сам).
_PROGON_OTCHETA = {"id": ""}


def _nachalo_progona() -> str:
    """Когда начался прогон (время записи, как поле ts). Нет прогона — пусто."""
    t = _sostoyanie().get("прогон") or {}
    if t.get("начат"):
        return str(t["начат"])
    pid = str(t.get("id") or _PROGON_OTCHETA.get("id") or "")
    try:
        from datetime import datetime as _dt
        return _dt.strptime(pid, "%Y%m%d_%H%M%S").isoformat()
    except Exception:
        return ""


def tri_stopa(slot, symbol) -> dict:
    """TRI_STOPA_V1 (V2: STORONA_PO_SDELKE_V1) — стопы подряд в одну сторону у
    трейдера в этом прогоне. Котин (слово Шефа 16.10): «три раза вынесло
    подряд — начинай думать, там ли ты». Сделки — его основной позиции (без
    тени города, кусков и доливок), с первого его входа в этом прогоне.
    Серия рвётся на сделке не по стопу и на сделке в другую сторону."""
    if not _nash(slot):
        return {}
    ya = _yashchik_chitat(slot, symbol)
    vh = [v for v in (ya.get("входы") or []) if v.get("что") == "ENTER"]
    if not vh:
        return {}
    ot = str(vh[0].get("бар") or "")[:16]
    moy = None
    try:
        from nositel import magic_slota
        moy = _nomer(slot)
    except Exception:
        pass
    if moy is None:
        moy = _nomer(slot)
    imya = {"A06": "BRUT", "A07": "AVANTURIST", "A08": "KONSERVATOR"}.get(str(slot).upper())
    zap = []
    for z in _zhurnaly_zakrytiy():
        moj = (z.get("magic") == moy) or (imya and str(z.get("trader") or "").upper() == imya
                                          and z.get("magic") in (None, moy))
        if not moj or z.get("нога") or z.get("частичное") or z.get("тень"):
            continue
        if str(z.get("symbol") or symbol).upper() != str(symbol).upper():
            continue
        if str(z.get("closed_at") or "")[:16] < ot:
            continue
        zap.append(z)
    zap.sort(key=lambda z: str(z.get("closed_at") or ""))
    n, storona, daty = 0, None, []
    for z in reversed(zap):
        if str(z.get("close_reason")) != "STOP_LOSS":
            break
        d = storona_sdelki(z)
        if not d:
            break
        if storona is None:
            storona = d
        elif d != storona:
            break
        n += 1
        daty.append(str(z.get("closed_at") or "")[:10])
    return {"n": n, "сторона": storona, "даты": list(reversed(daty))}


def _rabochiy(slot, symbol) -> str:
    ist = _yashchik_chitat(slot, symbol).get("история") or {}
    return str(ist.get("рабочий") or "H4").upper()


def _nizhe_rabochego(tf) -> list:
    try:
        import masshtab as _ms
        lest = list(_ms.LESTNICA)
        return lest[lest.index(str(tf).upper()) + 1:]
    except Exception:
        return {"D1": ["H12", "H8", "H4", "H1", "M30", "M15"],
                "H4": ["H1", "M30", "M15"]}.get(str(tf).upper(), [])


def mladshiy_svoy_hod(slot, symbol, protiv_storony) -> str:
    """TRI_STOPA_SMOTRI_V1: собственный ход младшего этажа прямо сейчас —
    тот, что житель разворачивает (серия шортов — подъём, лонгов — снижение),
    со своим началом по фракталам младшего. Слово Шефа 16.10: «а там на H1
    явно картина маслом»."""
    try:
        import volny_ao as _va
        tf = _rabochiy(slot, symbol)
        jtf = _va.NIZHE.get(tf)
        if not jtf:
            return ""
        vverh = str(protiv_storony).upper() == "SHORT"
        ot = _va.schet_hoda(symbol, jtf, vverh)
        return (f"Младший ({jtf}) сейчас — {'подъём' if vverh else 'снижение'}, "
                f"который ты разворачиваешь: {_va.kratko(ot)}")
    except Exception as e:
        print(f"[ТРИ СТОПА] младший не посчитался ({e})")
        return ""


def tri_stopa_blok(slot, symbol) -> str:
    ts = tri_stopa(slot, symbol)
    if ts.get("n", 0) < 3:
        return ""
    ml = mladshiy_svoy_hod(slot, symbol, ts["сторона"])
    jtf = (_nizhe_rabochego(_rabochiy(slot, symbol)) or ["младший"])[0]
    return (f"=== ТРИ СТОПА ПОДРЯД (Котин) ===\n"
            f"Стопов подряд в {ts['сторона']}: {ts['n']} ({', '.join(ts['даты'])}). "
            f"Котин: «три раза вынесло подряд — начинай думать, там ли ты». "
            f"Думать — значит посмотреть, а не перепроверить те же три условия "
            f"на своём этаже.\n"
            + (ml + "\n" if ml else "")
            + f"Следующий вход в {ts['сторона']} рука примет, только если на этом "
            f"баре ты сам откроешь младший ({jtf}) — стол или кадр — и скажешь, "
            f"что там видишь. Это не запрет: посмотрел и решил входить — входи.\n\n")


# ── TRI_STOPA_SMOTRI_V1: что он смотрел на этом баре ─────────────
def otmetit_vzglyad(slot, symbol, etazh) -> None:
    """Рука показала этаж — запомнить: какой и на каком баре."""
    if not _nash(slot):
        return
    try:
        bar = _bar_seychas()
        d = _chitat(slot)
        ya = _yashchik(d, symbol)
        sm = ya.get("смотрел") or {}
        if sm.get("бар") != bar:
            sm = {"бар": bar, "этажи": []}
        e = str(etazh or "").strip().upper() or "растяжка"
        if e not in sm["этажи"]:
            sm["этажи"].append(e)
        ya["смотрел"] = sm
        _pisat(slot, d)
    except Exception as e:
        print(f"[ТРИ СТОПА] взгляд не отметился ({e})")


def prosba_posmotret(slot, symbol, napr) -> str:
    """Перед ENTER: три стопа подряд в эту сторону и на этом баре младший
    не открывал — вернуть просьбу посмотреть. Иначе пусто (приказ идёт)."""
    if not _nash(slot):
        return ""
    ts = tri_stopa(slot, symbol)
    napr = str(napr or "").upper().strip()
    if ts.get("n", 0) < 3 or ts.get("сторона") != napr:
        return ""
    tf = _rabochiy(slot, symbol)
    nizhe = _nizhe_rabochego(tf)
    sm = _yashchik_chitat(slot, symbol).get("смотрел") or {}
    smotrel = [e for e in (sm.get("этажи") or [])
               if e in nizhe or e == "растяжка"] if sm.get("бар") == _bar_seychas() else []
    if smotrel:
        print(f"[ТРИ СТОПА] {slot} {napr}: после {ts['n']} стопов посмотрел "
              f"{', '.join(smotrel)} — вход пропускаю к проверкам")
        return ""
    jtf = (nizhe or ["младший"])[0]
    ml = mladshiy_svoy_hod(slot, symbol, napr)
    print(f"[ТРИ СТОПА] ✗ {slot} {napr}: {ts['n']} стопа подряд, младший на "
          f"этом баре не открывал — прошу посмотреть")
    return (f"Приказ НЕ отдан: три стопа подряд в {napr} ({', '.join(ts['даты'])}). "
            f"Котин: начинай думать, там ли ты. Сперва посмотри младший — "
            f"stol_na_etazhe или pokazat_etazh с этажом {jtf} — и скажи, что там "
            f"видишь; потом решай. "
            + (ml.rstrip(". ") + ". " if ml else "")
            + "Это не запрет: посмотрел и решил входить — входи.")


def diver_goroda(slot, symbol, tf) -> str:
    if not _nash(slot):
        return ""
    try:
        import sverka_divera as _sd
    except Exception:
        return ""
    L = [f"=== МОМЕНТ: ДИВЕР НА {tf} ПО СЧЁТУ ГОРОДА (факт, не приказ) ==="]
    for storona, imya in (("LONG", "по впадинам (для LONG)"),
                          ("SHORT", "по вершинам (для SHORT)")):
        try:
            r = _sd.poschitat(symbol, tf, storona) or {}
        except Exception as e:
            r = {"ok": False, "slovami": str(e)}
        if not r.get("ok"):
            L.append(f"  · {imya}: посчитать не вышло — {r.get('slovami')}")
            continue
        ch = ""
        if r.get("est") and r.get("цена_было") is not None:
            ch = (f": цена {r['цена_было']} → {r['цена_стало']}, "
                  f"AO {r['ao_было']:.5f} → {r['ao_стало']:.5f}")
        L.append(f"  · {imya}: дивер {'ЕСТЬ' if r.get('est') else 'нет'}{ch}")
        sl = str(r.get("slovami") or "").strip()
        if sl:
            L.append(f"    ({sl[:420]})")
    L.append("Это счёт города. Свои четыре числа берёшь рукой chisla_v_tochkah; "
             "разошлись с городом — посмотри ещё раз, где ошибка. Решаешь ты.")
    # SVERKA_S_GORODOM_V1: мнения города (волна, младший, серия стопов,
    # месяц на исходе) со стола ушли за руку sverka_s_gorodom — сначала своё.
    return "\n".join(L) + "\n\n"   # VVOD_CHISTYY_V1: вход — чистый


# ── отчёт прогона ────────────────────────────────────────────────
def svodka(mesta) -> list:
    nashi = {str(m.get("слот") or "").upper() for m in (mesta or [])
             if _nash(m.get("слот"))}   # MESTA_PO_POMETKE_V1
    if not nashi:
        return []
    s = ["## История старшего хода (называл трейдер, хранит город)", "",
         "Старший этаж — через один выше рабочего (D1 → месяц, H4 → неделя). "
         "Пересмотр — только по факту: новая свеча старшего этажа, цена за началом хода "
         "или новый край. Попытка сменить без факта не проходит и видна здесь.", ""]
    for slot in sorted(nashi):
        d = _chitat(slot)
        pr = _progon()
        if pr not in (d.get("прогоны") or {}):
            pr = d.get("последний_прогон")
        _PROGON_OTCHETA["id"] = str(pr or "")   # ZAKRYTIYA_PROGONA_V1
        for sym, ya in (((d.get("прогоны") or {}).get(pr)) or {}).items():
            ist = ya.get("история") or {}
            s.append(f"**{slot} · {sym}** — старший этаж {ist.get('этаж') or 'MN1'}; "
                     f"сейчас: ход {ist.get('ход') or '—'}, "
                     f"с {ist.get('с') or '—'}, делает: {ist.get('делает') or '—'} "
                     f"(с бара {ist.get('бар') or '—'})")
            s.append("")
            jur = ya.get("журнал") or []
            if jur:
                s += ["Пересмотры по факту:", "",
                      "| бар | было | стало | что изменилось — его слова | факт города |",
                      "|---|---|---|---|---|"]
                for z in jur:
                    s.append(f"| {z.get('бар')} | {z.get('было')} | {z.get('стало')} | "
                             f"{z.get('изменилось')} | {z.get('факт')} |")
                s.append("")
            pop = ya.get("попытки") or []
            if pop:
                s.append(f"Хотел сменить без факта: **{len(pop)}** раз(а), "
                         f"последние: " + "; ".join(
                             f"{p.get('бар')} {p.get('хотел')}" for p in pop[-5:]))
                s.append("")
            vh = [v for v in (ya.get("входы") or []) if v.get("что") == "ENTER"]
            if vh:
                def _sl(x):
                    return "да" if x is True else ("нет" if x is False else "прочерк")
                s += ["| вход | сторона | это | старший ход | разворот (пятая хода) "
                      "| по ходу (четвёртая большого) |", "|---|---|---|---|---|---|"]
                for v in vh:
                    s.append(f"| {v.get('бар')} | {v.get('направление')} | "
                             f"{v.get('это')} | {v.get('ход') or '—'} | "
                             f"{_sl(v.get('разворот'))}: {v.get('разворот_ход') or '—'} | "
                             f"{_sl(v.get('по_ходу'))}"
                             + (f" ({v.get('большой')})" if v.get("большой") else "") + " |")
                bez = [v for v in vh if v.get("разворот") is False and v.get("по_ходу") is not True]
                s.append("")
                s.append(f"Входов без основания по волнам (разворот «нет», по ходу не «да»): "
                         f"**{len(bez)}** из {len(vh)}. Прочерк — основание не определилось, "
                         f"это не нарушение.")
                prib = [v for v in vh if "ПРИБЛИЗИТЕЛЬНЫЙ" in str(v.get("разворот_ход") or "")
                        or "приблизительный" in str(v.get("разворот_ход") or "")]
                s.append(f"Из них со счётом приблизительным (масштаб мимо 100–140, до "
                         f"полутора раз): **{len(prib)}** — смотрим отдельно, помогают или врут.")
                try:   # SVERKA_S_GORODOM_V1
                    _sv = ya.get("сверки") or []
                    _s_ruk = [z for z in _sv if z.get("его")]
                    _s_razb = [z for z in _sv if z.get("разбор")]
                    _s_rash = [z for z in _s_ruk if z.get("расхождения")]
                    s += ["", "### Сверка с городом", "",
                          f"Сверялся рукой: **{len(_s_ruk)}** раз; разошёлся с городом: "
                          f"**{len(_s_rash)}**; разбор расхождений в приказе: **{len(_s_razb)}**.", ""]
                    for _ln in _itogi_slovami(slot, sym, ya).split("\n"):
                        s.append(_ln)
                    s.append("")
                    _pr = [z for z in _s_rash if z.get("разбор")][-6:]
                    if _pr:
                        s += ["| бар | его решение | расхождения | его разбор |", "|---|---|---|---|"]
                        for z in _pr:
                            s.append(f"| {z.get('бар')} | {(z.get('его') or {}).get('решение')} | "
                                     f"{'; '.join(z.get('расхождения') or [])} | "
                                     f"{str(z.get('разбор'))[:300]} |")
                        s.append("")
                except Exception as _e_sv:
                    s.append(f"(сверка в отчёт не легла: {_e_sv})")
                s.append("")
            sn = ya.get("снятия") or []
            if sn:
                s += ["Снятые заявки — факт города и его причина:", "",
                      "| бар | сторона | факт города | причина |", "|---|---|---|---|"]
                for z in sn:
                    s.append(f"| {z.get('бар')} | {z.get('направление')} | "
                             f"{z.get('факт')} | {z.get('причина')} |")
                s.append("")
    try:   # VEDENIE_SDELKI_V1: ведение — сохранил и приумножил?
        import vedenie_sdelki as _vs
        s += _vs.otchet(sorted(nashi))
    except Exception as _e_vs:
        s.append(f"(ведение в отчёт не легло: {_e_vs})")
    _PROGON_OTCHETA["id"] = ""   # ZAKRYTIYA_PROGONA_V1
    return s



# ══ SVERKA_S_GORODOM_V1 — сверка с городом ════════════════════════
# Принцип Шефа 17.10: город показывает своё мнение, но не решает; житель
# решает сам; потом сопоставляем его выбор с итогом. «Показывать так, чтобы
# он не просто читал, а анализировал, думал, сравнивая себя и город». Отсюда
# порядок: сперва своё, потом город, потом разбор расхождений и его же
# прошлые итоги — когда соглашался и когда нет.
def ruka_sverki_shema() -> dict:
    return {"type": "function", "function": {
        "name": "sverka_s_gorodom",
        "description": (
            "Сверить СВОЁ мнение о сделке с мнением города — когда ты в позиции "
            "(можно и перед входом, но вход — сценарий и три факта). Сначала "
            "назови своё: что за ход ты развернул и где он сейчас, что на "
            "младшем, что решаешь — держать, долить, подтянуть стоп, закрыть. "
            "В ответ: мнение города рядом с твоим, где разошлись, и твои прошлые "
            "итоги. Разбор расхождений — в приказе, поле «сверка»."),
        "parameters": {"type": "object", "properties": {
            "волна": {"type": "string", "description": (
                "твоё: третья / четвёртая / пятая / пятая внутри третьей / после "
                "пятой / не знаю — у хода, который разворачиваешь (или ведёшь)")},
            "младший": {"type": "string", "description": (
                "твоё: что на младшем — кончик (развернулось) / рано (ход ещё идёт) "
                "/ не смотрел")},
            "в_пятой": {"type": "string", "description": (
                "твоё: где ты внутри пятой — только началась / внутри неё кончилась "
                "третья (впереди четвёртая и пятая) / в зоне цели, конец / не знаю")},
            "пули": {"type": "string", "description": (
                "твоё: какие из пяти пуль видишь у края — дивер, цель, фрактал, "
                "приседающий среди трёх крайних, смена импульса")},
            "решение": {"type": "string", "description": (
                "твоё: ENTER LONG / ENTER SHORT / WAIT / HOLD / CLOSE")},
            "почему": {"type": "string", "description": "коротко, своими словами"}},
            "required": ["волна", "решение"]}}}


def _kat_volny(t) -> str:
    t = str(t or "").lower()
    if not t or "прочерк" in t or "не знаю" in t or "сломан" in t or "не ложится" in t:
        return "не знаю"
    if "внутри третьей" in t:
        return "пятая внутри третьей"
    if "после пятой" in t:
        return "после пятой"
    if "пятая" in t:
        return "пятая"
    if "четв" in t:
        return "четвёртая"
    if "трет" in t:
        return "третья"
    return "не знаю"


def _kat_mladshego(t) -> str:
    t = str(t or "").lower()
    if "кончик" in t or "разверн" in t:
        return "кончик"
    if "рано" in t or "идёт" in t or "идет" in t or "тянется" in t or "внутри третьей" in t:
        return "рано"
    return "не смотрел" if ("не смотр" in t or not t) else "не знаю"


def _napr_iz(resh) -> str:
    t = str(resh or "").upper()
    return "LONG" if "LONG" in t else ("SHORT" if "SHORT" in t else "")


def _ocenka(slot, symbol, tf, napr) -> dict:
    try:
        import volny_ao as _va
        return _va.ocenka_vhoda(symbol, tf, napr) or {}
    except Exception as e:
        print(f"[СВЕРКА] счёт не вышел ({e})")
        return {}


def itogi_vhodov(slot, symbol, ya=None) -> list:
    """Входы этого прогона с итогом в R (по журналу закрытий основной позиции)."""
    ya = ya if ya is not None else _yashchik_chitat(slot, symbol)
    vh = [v for v in (ya.get("входы") or []) if v.get("что") == "ENTER"]
    if not vh:
        return []
    moy = _nomer(slot)
    zak = []
    for z in _zhurnaly_zakrytiy():
        if z.get("magic") != moy or z.get("нога") or z.get("частичное") or z.get("тень"):
            continue
        if str(z.get("symbol") or symbol).upper() != str(symbol).upper():
            continue
        zak.append(z)
    zak.sort(key=lambda z: str(z.get("closed_at") or ""))
    vzyato, out = set(), []
    for v in vh:
        b0 = str(v.get("бар") or "")[:16]
        R = None
        for i, z in enumerate(zak):
            if i in vzyato:
                continue
            ot = str(z.get("opened_at") or z.get("closed_at") or "")[:16]
            if ot < b0 or storona_sdelki(z) != v.get("направление"):
                continue
            try:
                R = float(z.get("pnl_r"))
            except Exception:
                R = None
            vzyato.add(i)
            break
        out.append((v, R))
    return out


def _itogi_slovami(slot, symbol, ya=None) -> str:
    """Его прошлые итоги в этом прогоне: входы при каком мнении города."""
    rows = [(v, R) for v, R in itogi_vhodov(slot, symbol, ya) if R is not None]
    if not rows:
        return "Закрытых входов в этом прогоне ещё нет — сравнивать не с чем."

    def gr(kl):
        g = {}
        for v, R in rows:
            g.setdefault(kl(v), []).append(R)
        return "; ".join(f"при «{k}» — {len(x)} вход(а), итог {sum(x):+.2f}R"
                         for k, x in sorted(g.items()))
    sl = lambda x: "да" if x is True else ("нет" if x is False else "прочерк")
    t = ["Твои итоги в этом прогоне, по тому, что говорил город на входе:",
         "  · разворот по волнам: " + gr(lambda v: sl(v.get("разворот"))),
         "  · младший: " + gr(lambda v: {True: "кончик", False: "рано"}.get(
             v.get("младший_кончик"), "прочерк"))]
    if any(v.get("пуль") is not None for v, R in rows):
        t.append("  · пять пуль на входе: " + gr(lambda v: (
            "0–2" if (v.get("пуль") or 0) <= 2 else ("3" if v.get("пуль") == 3 else "4–5"))
            if v.get("пуль") is not None else "не считали"))
    sv = [(v, R) for v, R in rows if v.get("сверка_его")]
    if sv:
        sog = [R for v, R in sv if v.get("сверка_совпало")]
        pro = [R for v, R in sv if not v.get("сверка_совпало")]
        t.append(f"  · где ты сверялся: с городом совпал — {len(sog)} вход(а), "
                 f"{sum(sog):+.2f}R; разошёлся — {len(pro)}, {sum(pro):+.2f}R")
    return "\n".join(t)


def sverka(slot, symbol, tf, args) -> str:
    if not _nash(slot):
        return "сверка только для мест уровня «продвинутый новичок»"
    args = {str(k).strip().lower(): v for k, v in (args or {}).items()}
    ego_v = str(args.get("волна") or "").strip()
    resh = str(args.get("решение") or "").strip()
    if not ego_v or not resh:
        return ("Сначала своё: назови, какая волна у хода, который ты "
                "разворачиваешь (или ведёшь), и что решаешь. Город своё покажет "
                "после.")
    ego_m = str(args.get("младший") or "").strip()
    ego_5 = str(args.get("в_пятой") or "").strip()
    ego_p = str(args.get("пули") or "").strip()
    tf = str(tf or _rabochiy(slot, symbol)).upper()
    napr = _napr_iz(resh)
    ya_r = _yashchik_chitat(slot, symbol)
    ist = ya_r.get("история") or {}
    L = ["=== СВЕРКА С ГОРОДОМ ===",
         f"Ты: волна — {ego_v}; в пятой — {ego_5 or 'не сказал'}; пули — "
         f"{ego_p or 'не сказал'}; младший — {ego_m or 'не сказал'}; решение — {resh}."]
    rashl = []
    gor = {}   # мнение города; PYAT_PUL_V1 добавит пули и место в пятой
    if napr:
        oc = _ocenka(slot, symbol, tf, napr)
        cur = oc.get("ход") or {}
        try:
            import volny_ao as _va
            t_cur = _va.kratko(cur)
        except Exception:
            t_cur = "не посчитать"
        g_v = _kat_volny(cur.get("volna") if cur.get("volna") else t_cur)
        sl = {True: "законен", False: "не здесь", None: "прочерк"}[oc.get("разворот")]
        L.append(f"Город, ход который ты разворачиваешь: {t_cur} Разворот по волнам — {sl}.")
        if oc.get("по_ходу") is True:
            b = oc.get("большой") or {}
            L.append(f"Город, по ходу: большой ход {b.get('ход')} в четвёртой — "
                     "конец отката, вход по нему законен.")
        ml = oc.get("младший") or {}
        g_m = {True: "кончик", False: "рано"}.get(ml.get("кончик"), "не знаю")
        if ml.get("текст"):
            L.append(f"Город, младший ({ml.get('этаж')}): {ml['текст']}.")
        svoy = mladshiy_svoy_hod(slot, symbol, napr)
        if svoy:
            L.append("Город, " + svoy[0].lower() + svoy[1:])
        try:   # PYAT_PUL_V1: пять пуль и цель пятой — у края хода, который разворачиваешь
            import volny_ao as _va
            _pp = _va.pyat_pul(symbol, tf, napr == "SHORT", cur)
            L.append("Город: " + _va.pyat_pul_slovami(_pp, "вершина" if napr == "SHORT" else "дно"))
            gor["пуль"] = _pp.get("сошлось")
            _cz = _va.cel_pyatoy(cur) if str(cur.get("volna") or "").startswith(("пятая", "после пятой")) else {}
            g_5 = ("в зоне цели" if _cz.get("v_zone") else
                   ("до цели не дошла" if _cz.get("proshla") is not None else "не знаю"))
            gor["в_пятой"] = g_5
            e5 = str(ego_5).lower()
            if ("цел" in e5 or "конец" in e5) and g_5 == "до цели не дошла":
                rashl.append(f"пятая: ты — у цели, город — {_pp.get('слова', {}).get('цель', 'не дошла')}")
            if ("трет" in e5 or "началась" in e5) and g_5 == "в зоне цели":
                rashl.append("пятая: ты — ещё внутри, город — уже в зоне цели")
            if _pp.get("правила"):
                rashl.append("нормы волн нарушены — счёт под вопросом")
        except Exception as _e_pp:
            print(f"[СВЕРКА] пять пуль не посчитались ({_e_pp})")
        ts = tri_stopa(slot, symbol)
        if ts.get("n", 0) >= 3 and ts.get("сторона") == napr:
            L.append(f"Город: это будет вход в {napr} после {ts['n']} стопов подряд "
                     f"({', '.join(ts['даты'])}). Котин: начинай думать, там ли ты.")
        e_v = _kat_volny(ego_v)
        if e_v != "не знаю" and g_v != "не знаю" and e_v != g_v:
            rashl.append(f"волна: ты — {e_v}, город — {g_v}")
        e_m = _kat_mladshego(ego_m)
        if e_m in ("кончик", "рано") and g_m in ("кончик", "рано") and e_m != g_m:
            rashl.append(f"младший: ты — {e_m}, город — {g_m}")
        if e_m == "не смотрел":
            L.append("(Младший ты не назвал — если смотрел, впиши в «младший», что видел.)")
        gor.update({"разворот": oc.get("разворот"), "волна": g_v, "младший": g_m})
    elif str(resh).upper().startswith(("HOLD", "CLOSE", "ADD", "MOVE")):
        poz = _moya_poziciya(slot, symbol)
        if poz:
            L += _vedenie_goroda(slot, symbol, tf, poz, ego_v, rashl)
    if str(ist.get("делает") or "").startswith("на исходе"):
        L.append("Город: старший ход на исходе. Сделка против него может оказаться "
                 "началом нового хода, а не откатом: правило откатной «выходить "
                 "быстро» тут может срезать большую сделку. Город держал бы до трёх "
                 "условий против. Решаешь ты.")
    L.append("Где разошлись: " + ("; ".join(rashl) if rashl else "не разошлись."))
    L.append(_itogi_slovami(slot, symbol))
    L.append("Разбор — в приказе, поле «сверка»: кто, по-твоему, прав в каждом "
             "расхождении и почему. Решение твоё.")
    try:
        d = _chitat(slot)
        ya = _yashchik(d, symbol)
        bar = _bar_seychas()
        ya["сверки"] = (ya.get("сверки") or [])[-79:] + [{
            "бар": bar, "его": {"волна": ego_v, "младший": ego_m, "решение": resh,
                               "почему": str(args.get("почему") or "")},
            "города": gor, "расхождения": rashl}]
        _pisat(slot, d)
        print(f"[СВЕРКА] {slot} {bar}: {resh}; расхождения: {'; '.join(rashl) or 'нет'}")
    except Exception as e:
        print(f"[СВЕРКА] не записалась ({e})")
    return "\n".join(L)


def _vedenie_goroda(slot, symbol, tf, poz, ego_v, rashl) -> list:
    """VVOD_CHISTYY_V1: мнение города о сделке, которую он ведёт."""
    out = []
    napr = str(poz.get("direction") or "").upper()
    vverh_moy = napr == "LONG"          # ход в сторону сделки
    try:
        import volny_ao as _va
    except Exception:
        return ["(счёт волн не поднялся)"]
    # что он развернул на входе — как город считал тогда
    ya = _yashchik_chitat(slot, symbol)
    vh = [v for v in (ya.get("входы") or []) if v.get("что") == "ENTER"
          and v.get("направление") == napr]
    if vh:
        v = vh[-1]
        out.append(f"Город, что ты развернул на входе ({v.get('бар')}): "
                   f"{v.get('разворот_ход') or 'не посчитано'}"
                   + (f"; пуль у того края сошлось {v.get('пуль')} из {v.get('пуль_из') or 5}"
                      if v.get("пуль") is not None else "") + ".")
        rh = str(v.get("разворот_ход") or "")
        if "растягивалась" in rh or "внутри третьей" in rh or "рано" in rh:
            out.append("Город: тот ход ещё не был готов кончиться — сделка, скорее "
                       "всего, короткая: бери быстро, защищай прибыль.")
        elif (v.get("пуль") or 0) >= 4 and "ПЯТАЯ" in rh:
            out.append("Город: у того края сошлось много пуль — ты мог взять конец "
                       "большого хода; такую держат дольше.")
    # ход в сторону сделки сейчас
    try:
        moy = _va.schet_hoda(symbol, tf, vverh_moy)
        _k = (_va.kratko(moy).replace("Разворот не здесь.", "Конца твоего хода пока не видно.")
              .replace("Разворот здесь законен.", "У твоего хода, похоже, конец.")
              .replace("разворот не здесь", "конца твоего хода не видно"))
        out.append(f"Город, ход в твою сторону сейчас ({'подъём' if vverh_moy else 'снижение'}): " + _k)
        vm = str(moy.get("volna") or "")
        if vm == "третья":
            out.append("Город: твой ход в третьей — самой сильной волне. По канону "
                       "доливают в первую волну на пробой фракталов младшего; после "
                       "четвёртой — уже нет.")
        elif vm == "четвёртая" or vm.startswith(("пятая", "после пятой")):
            out.append("Город: твой ход уже прошёл четвёртую — по канону после неё "
                       "не доливают, это выброс.")
        pp = _va.pyat_pul(symbol, tf, vverh_moy, moy)
        out.append("Город, у края твоего хода — " + _va.pyat_pul_slovami(
            pp, "вершина" if vverh_moy else "дно").replace("Пять пуль конца хода", "пять пуль конца").strip())
        e_v = _kat_volny(ego_v)
        g_v = _kat_volny(moy.get("volna") if moy.get("volna") else "")
        if e_v != "не знаю" and g_v != "не знаю" and e_v != g_v:
            rashl.append(f"твой ход: ты — {e_v}, город — {g_v}")
    except Exception as _e:
        out.append(f"(ход в сторону сделки не посчитался: {_e})")
    ml = _mladshiy_dlya_vedeniya(slot, symbol, napr).strip()
    if ml:
        out.append("Город, " + ml[0].lower() + ml[1:])
    out.append("Как защищать прибыль — держать, подтянуть стоп, закрыть часть или "
               "всё — решаешь ты; город только показывает.")
    return out


def _moya_poziciya(slot, symbol):
    try:
        from nositel import magic_slota
        moy = _nomer(slot)
    except Exception:
        moy = None
    for p in _sostoyanie().get("positions") or []:
        if str(p.get("status") or "").upper() != "OPEN":
            continue
        if str(p.get("symbol") or "").strip().upper() != str(symbol).strip().upper():
            continue
        if p.get("доливка_города") or p.get("тень"):
            continue
        if moy is not None and p.get("magic") != moy:
            continue
        return p
    return None


def _sverka_na_bare(ya, bar):
    for z in reversed(ya.get("сверки") or []):
        if z.get("бар") == bar:
            return z
    return None


# ── тексты для задания и руки (мозг берёт отсюда) ────────────────
def polya_shemy(tf) -> dict:
    e = starshiy(tf) or "MN1"
    im = f"{e}, {imya(e)}"
    return {
        "старший_ход": {"type": "string", "description": (
            f"СЦЕНАРИЙ: куда идёт старший ход ({im} — через один выше твоего {tf}) — "
            "вверх, вниз или нет хода. Весь рисунок, не последняя свеча. История "
            "уже есть и факта нет — не пиши, она стоит")},
        "старший_делает": {"type": "string", "description": (
            "СЦЕНАРИЙ: что этот ход делает — идёт, откат против хода или на исходе "
            f"(на {imya(e, 3)} дивер)")},
        "старший_с": {"type": "string", "description": (
            "СЦЕНАРИЙ: с какого времени этот ход — месяц, в котором он начался, "
            "вид 2021.06")},
        "старший_изменилось": {"type": "string", "description": (
            "только когда пересматриваешь историю по факту: что именно изменилось")},
        "сверка": {"type": "string", "description": (
            "после руки sverka_s_gorodom: по каждому расхождению с городом — что "
            "видит город, что видишь ты и почему остаёшься при своём или меняешь "
            "решение. Не «согласен», а разбор. Сверки не было — пусто")},
        # VEDENIE_SDELKI_V1: в сделке — решение с обоснованием
        "дальше": {"type": "string", "description": (
            "в сделке (HOLD, MOVE_STOP, ADD, CLOSE частью): что должно случиться, "
            "чтобы ты сделал следующий шаг — подтянул стоп, закрыл, долил")},
        "доля": {"type": "number", "description": (
            "для CLOSE: какую долю исходной позиции закрыть — 1 (или пусто) всё, "
            "0.5 половину")},
    }


def polya_blok(tf) -> str:
    e = starshiy(tf) or "MN1"
    return (
        "\n=== СЦЕНАРИЙ В ПРИКАЗЕ ===\n"
        f"Старший этаж у тебя — {e} ({imya(e)}): через один выше твоего {tf}. "
        "В том же приказе otdat_prikaz (при любом слове) — твоя история старшего "
        "хода: старший_ход (вверх, вниз или нет хода), старший_делает (идёт, откат "
        "против хода или на исходе), старший_с (с какого времени, вид 2021.06). "
        "История уже есть и факта нет — эти поля не пиши: история стоит. Был факт "
        "и ты пересматриваешь — назови новые и в старший_изменилось — что "
        "изменилось.\n"
        "При ENTER и HOLD — ещё ожидание: быстро или долго (на выход не влияет).\n"
        "Как читать старший этаж — в знаниях: «Компас», «Тренд и откат».\n"
        "\n=== СВЕРКА С ГОРОДОМ — В СДЕЛКЕ ===\n"
        "Вход — сценарий (куда идёт старший ход, импульс это или откат, откуда) "
        "и три факта на твоём этаже. Волны на вход не влияют. Ты в сделке — вот "
        "где думать: что за ход ты развернул, где он сейчас, сколько держать, "
        "доливать ли. Порядок: 1) своё; 2) рука sverka_s_gorodom с этими "
        "ответами — город покажет свой счёт волн, пули у края твоего хода, "
        "младший и твои прошлые итоги; "
        "3) в приказе в поле «сверка» — разбор расхождений: кто, по-твоему, прав "
        "и почему. Решение всё равно твоё.\n"
        # VEDENIE_SDELKI_V1
        "\n=== В СДЕЛКЕ — РЕШЕНИЕ И ОБОСНОВАНИЕ ===\n"
        "Задача — сохранить и приумножить прибыль. На каждом баре в сделке город "
        "кладёт факты («Твоя сделка»): прибыль сейчас, лучшее место и сколько от "
        "него отдано, стоп, противоположные фракталы, доливку по канону, старший "
        "этаж. Решаешь ты: HOLD, MOVE_STOP, CLOSE (всё или долю — поле «доля») или "
        "ADD («долить» — доля исходной). В «почему» — на какие факты опираешься, в "
        "«дальше» — что должно случиться для следующего шага. Без этого рука "
        "решение в сделке не примет.\n")


# HOD_MESYACA_V1 - marker
# HOD_STARSHIY_V2 - marker
# VOLNY_AO_V1 - marker
# VOLNY_AO_V2 - marker
# VOLNY_AO_V3 - marker
# MLADSHIY_ETAZH_V1 - marker
# TRI_STOPA_V1 - marker
# ETAZH_POBLIZHE_V1 - marker
# STORONA_PO_SDELKE_V1 - marker
# TRI_STOPA_SMOTRI_V1 - marker
# SVERKA_S_GORODOM_V1 - marker
# PYAT_PUL_V1 - marker
# VVOD_CHISTYY_V1 - marker

# ZAKRYTIYA_PROGONA_V1 - marker


# ══ UROKI_PROGONOV_V1 — в задание места уровня «продвинутый новичок»: уроки его прошлых прогонов ══
_blok_bez_urokov = blok


def blok(slot, symbol, tf, bar=None) -> str:   # noqa: F811
    s = _blok_bez_urokov(slot, symbol, tf, bar)
    try:
        if _nash(slot):
            import uroki_progonov as _up
            s = (s or "") + _up.blok(slot, symbol, tf, bar)
    except Exception as _e_up:
        print(f"[УРОКИ] в задание не легли ({_e_up})")
    return s


# UROKI_PROGONOV_V1 - marker


# ══ MESTO_BEZ_IMENI_V1 — поле места: новое имя, старые записи читаются ══
def _pole_mesta(d, imya):
    try:
        import mesto_urovnya as _mu_p
        return _mu_p.pole(d, imya)
    except Exception:
        return (d or {}).get(imya)


# MESTO_BEZ_IMENI_V1 - marker


# ══ SVECHA_STARSHEGO_V1 — развернуть старший ход можно только по структуре ══
# Слово Шефа 21.10: «там тренд вниз до перелома». Закрытая свеча старшего
# этажа сама по себе направление хода не меняет — свеча закрывается каждый
# месяц. Куда идёт ход — только: цена ушла за начало хода, или ПЕРЕЛОМ —
# дивер на старшем этаже у нового края против хода (с текущей свечой).
def perelom(symbol, tf, ist) -> tuple:
    """(есть ли, словами) — дивер на старшем этаже против хода истории."""
    hod = (ist or {}).get("ход")
    if hod not in ("вверх", "вниз"):
        return False, ""
    e = _etazh_ist(ist, tf)
    try:
        import sverka_divera as _sd
        r = _sd.diver_so_svechoy(symbol, e, "LONG" if hod == "вниз" else "SHORT") or {}
    except Exception as ex:
        return False, f"не посчитался ({ex})"
    return bool(r.get("est")), str(r.get("slovami") or "")[:300]


_zapisat_do_struktury = zapisat


def zapisat(slot, symbol, tf, tablo, args) -> str:   # noqa: F811
    try:
        if _nash(slot):
            a0 = dict(args or {})
            hod = norm_hod(_arg(a0, "ход"))
            ist = _yashchik_chitat(slot, symbol).get("история") or {}
            if (ist and ist.get("ход") in ("вверх", "вниз")
                    and hod in ("вверх", "вниз", "нет хода") and hod != ist.get("ход")):
                seychas = _bar_seychas()
                f = fakty(symbol, ist, seychas, tf)
                za = bool((f.get("за_начало") or (False,))[0])
                per, per_sl = perelom(symbol, tf, ist)
                if not za and not per:
                    e = _etazh_ist(ist, tf)
                    d = _chitat(slot)
                    ya = _yashchik(d, symbol)
                    bylo = {k: ist.get(k) for k in ("ход", "делает", "с")}
                    pop = {"бар": seychas, "хотел": {"ход": hod, "делает": _arg(a0, "делает"),
                                                    "с": _arg(a0, "с")},
                           "было": bylo, "его_слова": _arg(a0, "изменилось"),
                           "почему_нет": (f"развернуть ход — только по структуре: цена за "
                                          f"начало хода — нет; перелом на {e} — нет")}
                    ya["последняя_попытка"] = pop
                    ya["попытки"] = (ya.get("попытки") or [])[-29:] + [pop]
                    _pisat(slot, d)
                    print(f"[ХОД МЕСЯЦА] ✗ {slot} {symbol}: хотел развернуть ход "
                          f"{ist.get('ход')} → {hod} без структуры (за начало хода — нет, "
                          f"перелом на {e} — нет) — история стоит ({bylo})")
                    for k in ("старший_ход", "месяц_ход", "старший_делает", "месяц_делает",
                              "старший_с", "месяц_с"):
                        a0.pop(k, None)
                    args = a0
    except Exception as e:
        print(f"[ХОД МЕСЯЦА] проверка разворота не вышла ({e}) — как было")
    return _zapisat_do_struktury(slot, symbol, tf, tablo, args)


_FRAZA_FAKT = ("Факт есть — можешь пересмотреть историю: в приказе новые "
               "старший_ход / старший_делает / старший_с и в старший_изменилось — "
               "что именно изменилось. Ничего не изменилось — оставь как есть.")
_blok_do_struktury = blok


def blok(slot, symbol, tf, bar=None) -> str:   # noqa: F811
    s = _blok_do_struktury(slot, symbol, tf, bar)
    try:
        if not _nash(slot) or not s:
            return s
        ist = _yashchik_chitat(slot, symbol).get("история") or {}
        if ist.get("ход") not in ("вверх", "вниз"):
            return s
        e = _etazh_ist(ist, tf)
        f = fakty(symbol, ist, bar or _bar_seychas(), tf)
        za = bool((f.get("за_начало") or (False,))[0])
        per, per_sl = perelom(symbol, tf, ist)
        stroka = (f"  · перелом на {e} — дивер у нового края против хода, с текущей свечой: "
                  + ("ЕСТЬ" if per else "нет") + (f" ({per_sl})" if per_sl else ""))
        if za or per:
            nov = (_FRAZA_FAKT if _FRAZA_FAKT in s else "")
        else:
            nov = (f"Закрылась новая свеча {imya(e, 1)} — можешь поправить, что ход делает "
                   "и с какого времени (старший_делает, старший_с; в старший_изменилось — "
                   "что изменилось). Куда идёт ход — развернуть историю можно только по "
                   "факту структуры: цена ушла за начало хода или перелом на "
                   f"{e}. Сейчас ни того, ни другого нет — ход {ist.get('ход')} стоит.")
        if _FRAZA_FAKT in s:
            s = s.replace(_FRAZA_FAKT, stroka + "\n" + nov)
        else:
            s = s.replace("\nС той записи — факты города:\n",
                          "\nС той записи — факты города:\n" + stroka + "\n", 1)
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] перелом в задание не лёг ({ex})")
    return s


# SVECHA_STARSHEGO_V1 - marker


# ══ NA_PERELOME_V1 — против старшего хода при дивере на старшем: «на переломе» ══
# Слово Шефа 21.10. Тот же счёт, что у ворот разворота (perelom): дивер на
# старшем этаже у нового края против хода, с текущей свечой. Есть — сделка
# против хода не «откат, выходи быстро», а «перелом: долгое настроение,
# ведёшь на рабочем». Нет — всё как было.
def _na_perelome(slot, symbol, napr) -> tuple:
    """(да/нет, этаж, словами) — сделка против старшего хода на переломе."""
    ist = _yashchik_chitat(slot, symbol).get("история") or {}
    if _eto(ist, napr) != "в откат":
        return False, "", ""
    tf = str(ist.get("рабочий") or "D1")
    per, sl = perelom(symbol, tf, ist)
    return bool(per), _etazh_ist(ist, tf), sl


_metka_vhoda_do_pereloma = metka_vhoda


def metka_vhoda(slot, symbol, napr, bar=None, chto="ENTER") -> str:   # noqa: F811
    t = _metka_vhoda_do_pereloma(slot, symbol, napr, bar, chto)
    try:
        if not _nash(slot):
            return t
        da, e, sl = _na_perelome(slot, symbol, napr)
        if not da:
            return t
        d = _chitat(slot)
        ya = _yashchik(d, symbol)
        if ya.get("входы"):
            ya["входы"][-1]["перелом"] = True
            _pisat(slot, d)
        ist = _yashchik_chitat(slot, symbol).get("история") or {}
        print(f"[ХОД МЕСЯЦА] {slot} {chto} {napr}: на переломе (дивер на {e})")
        return (f" Это вход НА ПЕРЕЛОМЕ: против старшего хода ({e}, {imya(e)}: "
                f"{ist.get('ход')}, по твоей истории), но на {e} дивер у нового края "
                "против хода — может начинаться новый ход.")
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] перелом на входе не посчитался ({ex}) — как было")
        return t


_metka_pozicii_do_pereloma = _metka_pozicii_bez_mladshego


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:   # noqa: F811
    try:
        if _nash(slot):
            da, e, sl = _na_perelome(slot, symbol, napr)
            if da:
                ist = _yashchik_chitat(slot, symbol).get("история") or {}
                return ("Эта сделка — НА ПЕРЕЛОМЕ: ты вошёл против старшего хода ("
                        + e + ", " + imya(e) + ": " + str(ist.get("ход"))
                        + "), но на " + e + " дивер у нового края против хода"
                        + (f" ({sl[:200]})" if sl else "")
                        + ". Это может быть начало нового хода, а не короткий откат: "
                        "долгое настроение — даёшь движению пространство, ведёшь на "
                        "рабочем этаже и ждёшь дивер на рабочем. Правило откатной "
                        "«выходить быстро на дивере младшего» здесь может срезать "
                        "большую сделку. Это знание, не приказ: решаешь ты.\n")
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] перелом в сделке не посчитался ({ex}) — как было")
    return _metka_pozicii_do_pereloma(slot, symbol, napr)


# NA_PERELOME_V1 - marker


# ══ POSLE_PERELOMA_V1 — вход был в откат, старший развернулся в сторону сделки ══
# Пометка входа заморожена («в откат»), а история старшего хода — живая. Когда
# она по факту развернулась В СТОРОНУ сделки, сделка — не откат: это сделка по
# старшему ходу, главная. Слово Шефа 22.10.
def _eto_pri_vhode(slot, symbol, napr):
    vh = [v for v in (_yashchik_chitat(slot, symbol).get("входы") or [])
          if v.get("что") == "ENTER" and v.get("направление") == str(napr).upper()]
    return vh[-1].get("это") if vh else None


def posle_pereloma(slot, symbol, napr) -> bool:
    ist = _yashchik_chitat(slot, symbol).get("история") or {}
    return (_eto_pri_vhode(slot, symbol, napr) == "в откат"
            and _eto(ist, napr) == "по ходу")


_metka_pozicii_do_posle = _metka_pozicii_bez_mladshego


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:   # noqa: F811
    try:
        if _nash(slot) and posle_pereloma(slot, symbol, napr):
            ist = _yashchik_chitat(slot, symbol).get("история") or {}
            e = _etazh_ist(ist, str(ist.get("рабочий") or "D1"))
            return ("Эта сделка — ПОСЛЕ ПЕРЕЛОМА: ты входила в откат против старшего "
                    "хода, но старший ход по факту развернулся в твою сторону (" + e + ", "
                    + imya(e) + ": " + str(ist.get("ход")) + " с " + str(ist.get("с") or "—")
                    + ", по твоей истории). Теперь это сделка по старшему ходу — главная: "
                    "её держат, пока старший ход идёт; доливают в первую волну, после "
                    "четвёртой не доливают. «Выходить быстро на дивере младшего» — правило "
                    "отката, здесь оно не твоё. Это знание, не приказ: решаешь ты.\n")
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] «после перелома» не посчиталось ({ex}) — как было")
    return _metka_pozicii_do_posle(slot, symbol, napr)


# POSLE_PERELOMA_V1 - marker


# ══ OTKAT_TRETYA_V1 — откат: дивер младшего — только после своей третьей ══
_metka_pozicii_do_tretey = _metka_pozicii_bez_mladshego


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:   # noqa: F811
    try:
        if (_nash(slot) and _eto_pri_vhode(slot, symbol, napr) == "в откат"
                and not posle_pereloma(slot, symbol, napr)
                and not _na_perelome(slot, symbol, napr)[0]):
            ist = _yashchik_chitat(slot, symbol).get("история") or {}
            e = _etazh_ist(ist, str(ist.get("рабочий") or "D1"))
            return ("Эта сделка — ВХОД В ОТКАТ: против старшего хода (" + e + ", " + imya(e)
                    + ": " + str(ist.get("ход")) + "), перелома на " + e + " нет. Не доливают; "
                    "младший смотришь на каждом пробуждении. Дивер младшего этажа — повод "
                    "выйти, НО ТОЛЬКО КОГДА ТРЕТЬЯ ВОЛНА ТВОЕГО ХОДА УЖЕ ПРОШЛА (самый большой "
                    "горб/яма AO своего хода позади). Пока третья не прошла — откат держат, "
                    "даже если младший развернулся: откат против старшего на рабочем этаже "
                    "бывает и долгим ходом. Это знание, не приказ: решаешь ты.\n")
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] слова отката не сложились ({ex}) — как было")
    return _metka_pozicii_do_tretey(slot, symbol, napr)


# OTKAT_TRETYA_V1 - marker


# ══ VEDENIE_PROSTO_V1 — пометка сделки двумя простыми правилами ══
_metka_pozicii_do_prosto = _metka_pozicii_bez_mladshego


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:   # noqa: F811
    try:
        import vedenie_sdelki as _vs
        if _vs._vedenie_po_zapiske(slot):
            scen = _vs._scenariy(slot, symbol, napr)
            nazv = {"в откат": "ОТКАТ", "по ходу": "ПО ХОДУ", "на переломе": "НА ПЕРЕЛОМЕ",
                    "после перелома": "ПОСЛЕ ПЕРЕЛОМА"}.get(scen, str(scen).upper())
            return f"Эта сделка — {nazv}: {_vs._pravilo(scen)}. Решаешь ты.\n"
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] простая пометка не сложилась ({ex}) — как было")
    return _metka_pozicii_do_prosto(slot, symbol, napr)


# VEDENIE_PROSTO_V1 - marker


# ══ OTKAT_DO_SOSEDEY_V1 — пометки сделки снова прежние (слово Шефа 23.10) ══
try:
    _metka_pozicii_bez_mladshego = _metka_pozicii_do_pereloma   # noqa: F811
except NameError:
    pass
try:
    metka_vhoda = _metka_vhoda_do_pereloma   # noqa: F811
except NameError:
    pass


# OTKAT_DO_SOSEDEY_V1 - marker


# ══ POLKA_SHAG2_V1 — подсказка ключей перед входом (месяц — на каждом входе) ══
_blok_do_polki = blok


def blok(slot, symbol, tf, bar=None) -> str:   # noqa: F811
    s = _blok_do_polki(slot, symbol, tf, bar)
    try:
        import opyt_stola as _os
        import mesto_urovnya as _mu
        ceh = _mu.ceh_mesta(slot)
        if not _os.vklyucheno(ceh, slot):
            return s
        from hooks import load_trading_state as _lts
        moy = _mu.nomer_mesta(slot, ceh)
        v_sdelke = any(str(p.get("status") or "").upper() == "OPEN" and p.get("magic") == moy
                       for p in ((_lts() or {}).get("positions") or []))
        if v_sdelke:
            hint = ("Ты в сделке. На твоей полке: «ведение» — как ведут; открой рукой "
                    "vspomnit_po_yarlyku (по: ведение).")
        else:
            hint = ("Перед входом: на твоей полке «месяц», «три условия», «вход». Месяц "
                    "смотришь на каждом входе. Открыть — vspomnit_po_yarlyku (по: ключ).")
        return (s or "") + "\n" + hint + "\n"
    except Exception as e:
        print(f"[ПОЛКА] подсказка ключей не легла ({e})")
        return s


# POLKA_SHAG2_V1 - marker


# ══ D01_KAK_A06_V1 — пометка сделки: выход по месту, стоп не двигаешь ══
import json
from pathlib import Path
_metka_pozicii_do_a06 = _metka_pozicii_bez_mladshego


def _po_mestu_hm(slot) -> bool:
    try:
        import mesto_urovnya as _mu
        ceh = _mu.ceh_mesta(slot)
        p = Path(__file__).resolve().parent.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh / "manifest.json"
        man = json.loads(p.read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper():
                return str(z.get("выход") or "").strip().lower() == "по месту"
    except Exception:
        pass
    return False


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:   # noqa: F811
    try:
        if _po_mestu_hm(slot):
            import vedenie_sdelki as _vs
            scen = str(_vs._scenariy(slot, symbol, napr) or "")
            nazv = {"в откат": "ОТКАТ", "по ходу": "ПО ХОДУ", "на переломе": "ПЕРЕЛОМ",
                    "после перелома": "ПО ХОДУ (после перелома)"}.get(scen, scen.upper() or "—")
            pravilo = ("выход — встречный разворотный бар с приседающим на рабочем, когда ты "
                       "в заметном плюсе (в нуле это шум)" if scen == "в откат" else
                       "держишь до дивера против сделки на рабочем; первый встречный "
                       "разворотник — не выход")
            return (f"Город считает: эта сделка — {nazv}. По месту {pravilo}. Стоп не "
                    "двигаешь. Место называешь ты — в поле «место».\n")
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] пометка по месту не сложилась ({ex}) — как было")
    return _metka_pozicii_do_a06(slot, symbol, napr)


# D01_KAK_A06_V1 - marker


# ══ VEDENIE_MASSHTAB_V3 — на месте «ведение_масштаб» пометка места без старого выхода ══
def _vedenie_masshtab_hm(slot) -> bool:
    try:
        import mesto_urovnya as _mu3
        ceh = _mu3.ceh_mesta(slot)
        p = (Path(__file__).resolve().parent.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh
             / "manifest.json")
        man = json.loads(p.read_text(encoding="utf-8"))
        for z in man.get("слоты") or []:
            if str(z.get("слот") or "").strip().upper() == str(slot or "").strip().upper():
                return str(z.get("ведение_масштаб") or "").strip().lower() in ("да", "true", "1")
    except Exception:
        pass
    return False


_metka_do_masshtaba = _metka_pozicii_bez_mladshego


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:   # noqa: F811
    try:
        if _vedenie_masshtab_hm(slot):
            import vedenie_sdelki as _vs3
            scen = str(_vs3._scenariy(slot, symbol, napr) or "")
            nazv = {"в откат": "ОТКАТ", "по ходу": "ПО ХОДУ", "на переломе": "ПЕРЕЛОМ",
                    "после перелома": "ПО ХОДУ (после перелома)"}.get(scen, scen.upper() or "—")
            return (f"Город считает: эта сделка — {nazv}. Выход у тебя один, на любом месте — "
                    "по масштабу импульса: смотри строку «ВЕДЕНИЕ ПО МАСШТАБУ ИМПУЛЬСА» "
                    "(«3 на 5» — CLOSE; «5 в 3», дивера нет, край не подтверждён — держать). "
                    "Встречный разворотник, «заметный плюс», дивер на другом этаже — не выход. "
                    "Стоп не двигаешь. Место называешь ты — в поле «место».\n")
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] пометка «по масштабу» не сложилась ({ex}) — как было")
    return _metka_do_masshtaba(slot, symbol, napr)


# VEDENIE_MASSHTAB_V3 - marker


# ══ VEDENIE_MASSHTAB_V4 — пометка места: откат — по разворотнику, импульс — по масштабу ══
_metka_do_v4 = _metka_pozicii_bez_mladshego


def _metka_pozicii_bez_mladshego(slot, symbol, napr) -> str:   # noqa: F811
    try:
        if _vedenie_masshtab_hm(slot):
            import vedenie_sdelki as _vs4
            if str(_vs4._scenariy(slot, symbol, napr) or "") == "в откат":
                return ("Город считает: эта сделка — ОТКАТ (коррекция против старшего хода). "
                        "Выход — встречный разворотный бар с приседающим на рабочем, когда ты в "
                        "заметном плюсе (в нуле это шум). Масштаб импульса для отката не "
                        "считается: в коррекции пятой волны нет. Стоп не двигаешь. Место "
                        "называешь ты — в поле «место».\n")
    except Exception as ex:
        print(f"[ХОД МЕСЯЦА] пометка отката не сложилась ({ex}) — как было")
    return _metka_do_v4(slot, symbol, napr)


# VEDENIE_MASSHTAB_V4 - marker
