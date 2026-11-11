# -*- coding: utf-8 -*-
# FAZA_HODA_V1
"""
ФАЗЫ ХОДА — судья опыта второго уровня (A07).

СЛОВО ШЕФА (30.09, 01.10)
    Первый шаг второго уровня — опыт без смены правил: на каждом месте
    прогона трейдер называет фазу хода (третья / четвёртая / пятая /
    не знаю), а город после прогона сверяет с тем, что рынок сделал
    дальше. «В масштабе 100-140 баров, если импульс смотреть, 4 волна
    как правило пересекает ноль.»

ЗАКОН ЭТОГО ФАЙЛА
    Судья механический: цена и AO, без модели. Судит на том этаже, где
    её ход (от названного ею начала до места) занимает около 120 баров,
    и смотрит вперёд столько же баров, сколько ход уже прошёл (не меньше
    30, не больше 140). Ничего не решает за трейдера и на вход не
    влияет — только сводка в отчёт. Его итог — кандидат, не приговор.

КАК СУДИТ (ход вверх; вниз — зеркально)
    третья    — впереди AO пересёк ноль против хода, а потом цена взяла
                новый край → сбылось. Пересёк, а края нет → не сбылось.
                Не пересёк, а цена ушла дальше → под вопросом (ямка или
                третья ещё тянется).
    четвёртая — впереди цена взяла край хода → сбылось; нет → не сбылось.
    пятая     — впереди цена ушла за дно четвёртой (низ отката после
                самого большого горба AO) → сбылось; новый край с горбом
                AO больше третьего → не сбылось (это была не пятая).
    Окно кончилось раньше, чем рынок ответил, → «рынок не ответил».
"""
from __future__ import annotations

import bisect
import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

SLOTY = ("A07", "A08")                 # где идёт опыт
CEL = 120                        # середина окна 100-140
VPERYOD_MIN, VPERYOD_MAX = 30, 140
FORMAT = "%Y.%m.%d %H:%M"
ITOGI = ("сбылось", "не сбылось", "под вопросом", "рынок не ответил",
         "нечем судить")

_LENTY: dict = {}


def _norm_daty(d) -> str:
    d = str(d or "").strip()
    return d + " 00:00" if len(d) == 10 else d


def _vremya(s):
    import istoriya
    return istoriya.kak_vremya(str(s or ""))


def _norm_faza(s) -> str:
    s = str(s or "").strip().lower()
    if not s:
        return ""
    if "не зна" in s or "неясн" in s or s == "?":
        return "не знаю"
    if "трет" in s or s.startswith("3"):
        return "третья"
    if "четв" in s or s.startswith("4"):
        return "четвёртая"
    if "пят" in s or s.startswith("5"):
        return "пятая"
    return "не знаю"


def _norm_hod(s) -> int:
    s = str(s or "").strip().lower()
    if any(x in s for x in ("вверх", "верх", "up", "long", "лонг", "бык", "рост")):
        return 1
    if any(x in s for x in ("вниз", "низ", "down", "short", "шорт", "медв", "паден")):
        return -1
    return 0


def _norm_uver(s) -> str:
    s = str(s or "").strip().lower()
    if "мал" in s or "низк" in s or "слаб" in s:
        return "мало"
    if "сред" in s:
        return "средне"
    if "увер" in s or "высок" in s or "силь" in s:
        return "уверена"
    return "—"


def _lenta(sym: str, tf: str):
    """Вся лента этажа, МИМО курсора истории: прогон кончился, судье
    будущее места видеть можно. Нет файла — спрашиваем кран."""
    kl = (sym, tf)
    if kl in _LENTY:
        return _LENTY[kl]
    bs = []
    try:
        import istoriya
        bs = istoriya._vse_bary(sym, tf) or []
    except Exception:
        bs = []
    if not bs:
        try:
            from feed_source import bars as _b
            bs, _ = _b(sym, tf, 20000)
            bs = bs or []
        except Exception:
            bs = []
    _LENTY[kl] = (bs, [_norm_daty(b.get("date", "")) for b in bs])
    return _LENTY[kl]


def _podobrat(sym: str, s0: str, sp: str, minut_v_hode: float):
    """Этаж, на котором ход ляжет ближе всего к 120 барам."""
    import masshtab
    import rastyanut
    L = masshtab.LESTNICA
    g = rastyanut.podobrat_etazh(minut_v_hode)
    i = L.index(g) if g in L else L.index("H4")
    luchshiy = None
    for j in range(max(0, i - 2), min(len(L), i + 3)):
        tf = L[j]
        bs, daty = _lenta(sym, tf)
        if not bs:
            continue
        n = bisect.bisect_right(daty, sp) - bisect.bisect_left(daty, s0)
        if n < 5:
            continue
        ocenka = abs(n - CEL)
        if luchshiy is None or ocenka < luchshiy[0]:
            luchshiy = (ocenka, tf, n)
    return luchshiy


def _ch(x) -> str:
    try:
        return f"{round(float(x), 5):g}"
    except Exception:
        return str(x)


def _sud(faza, d, seg, ao, I0, IP, obrezano):
    def kray(k):
        return seg[k]["high"] if d > 0 else seg[k]["low"]

    def iznanka(k):
        return seg[k]["low"] if d > 0 else seg[k]["high"]

    def dalshe(x, y):
        return x > y if d > 0 else x < y

    def dao(k):
        v = ao[k] if k < len(ao) else None
        return None if v is None else d * v

    def kogda(k):
        return str(seg[k].get("date", ""))

    vpered = range(IP + 1, len(seg))
    E = kray(I0)
    for k in range(I0, IP + 1):
        if dalshe(kray(k), E):
            E = kray(k)

    if faza == "третья":
        j = next((k for k in vpered
                  if dao(k) is not None and dao(k) < 0), None)
        konec = j if j is not None else len(seg)

        # FAZY_SUDYA_V2: пятая без нуля. Слово Шефа: «если есть 3 и 5
        # волны, будет и дивер», а четвёртая пересекает ноль «как
        # правило» — не всегда. Был горб третьей (на месте или после
        # него), AO откатил и вернулся, и цена взяла новый край МЕНЬШИМ
        # горбом — это пятая, значит на месте была третья.
        def _pyataya_bez_nulya():
            hm, km, pe = None, None, None
            for k in range(I0, konec):
                v = dao(k)
                if (k > IP and pe is not None and dalshe(kray(k), pe)
                        and v is not None and hm is not None and hm > 0
                        and km is not None and km >= IP - 3
                        and k > km + 1 and v < hm):
                    yama = min((dao(b) for b in range(km + 1, k)
                                if dao(b) is not None), default=None)
                    if yama is not None and yama < v:
                        return km, k
                if v is not None and (hm is None or v > hm):
                    hm, km = v, k
                if pe is None or dalshe(kray(k), pe):
                    pe = kray(k)
            return None

        if j is not None:
            verh = E
            for k in range(IP + 1, j + 1):
                if dalshe(kray(k), verh):
                    verh = kray(k)
            nov = next((k for k in range(j + 1, len(seg))
                        if dalshe(kray(k), verh)), None)
            if nov is not None:
                return ("сбылось", f"AO перешёл ноль {kogda(j)}, потом "
                                   f"цена взяла новый край {kogda(nov)}")
            p5 = _pyataya_bez_nulya()
            if p5:
                return ("сбылось", f"четвёртая без нуля: после горба "
                        f"{kogda(p5[0])} AO откатил, новый край {kogda(p5[1])} "
                        f"меньшим горбом — пятая")
            if obrezano:
                return ("рынок не ответил", f"AO перешёл ноль {kogda(j)}, "
                        "нового края до конца истории нет")
            return ("не сбылось", f"AO перешёл ноль {kogda(j)}, а нового "
                                  "края за окно не было")
        p5 = _pyataya_bez_nulya()
        if p5:
            return ("сбылось", f"четвёртая без нуля: после горба "
                    f"{kogda(p5[0])} AO откатил, новый край {kogda(p5[1])} "
                    f"меньшим горбом — пятая")
        nov = next((k for k in vpered if dalshe(kray(k), E)), None)
        if nov is not None:
            return ("под вопросом", f"ход пошёл дальше ({kogda(nov)}), а AO "
                    "ноль не пересёк — ямка или третья ещё тянется")
        return "рынок не ответил", "за окно ни ноля, ни нового края"


    if faza == "четвёртая":
        nov = next((k for k in vpered if dalshe(kray(k), E)), None)
        if nov is not None:
            return "сбылось", f"цена взяла край хода {_ch(E)} — {kogda(nov)}"
        if obrezano:
            return "рынок не ответил", "края нет, а история кончилась"
        return "не сбылось", f"за окно край хода {_ch(E)} не взят"

    if faza == "пятая":
        k3, h3 = None, None
        for k in range(I0, IP + 1):
            v = dao(k)
            if v is not None and (h3 is None or v > h3):
                k3, h3 = k, v
        if k3 is None or k3 >= IP or h3 is None or h3 <= 0:
            return ("нечем судить", "до места не видно горба третьей и "
                    "отката после него")
        dno = iznanka(k3)
        for k in range(k3, IP + 1):
            if dalshe(dno, iznanka(k)):
                dno = iznanka(k)
        for k in vpered:
            if dalshe(kray(k), E) and dao(k) is not None and dao(k) > h3:
                return ("не сбылось", f"новый край {kogda(k)} с горбом AO "
                        "больше третьего — это была не пятая")
            if dalshe(dno, iznanka(k)):
                return "сбылось", f"цена ушла за дно четвёртой {_ch(dno)} — {kogda(k)}"
        return ("рынок не ответил", f"за окно цена не ушла за дно "
                f"четвёртой {_ch(dno)}")

    return "не знаю", ""


def sudit_mesto(m: dict) -> dict:
    f = m.get("фаза") or {}
    if not f:
        return {"итог": "не назвала"}
    faza = _norm_faza(f.get("фаза"))
    d = _norm_hod(f.get("ход"))
    out = {"фаза": faza or "—",
           "ход": "вверх" if d > 0 else "вниз" if d < 0 else "—",
           "начало": str(f.get("начало_хода") or "").strip(),
           "уверенность": _norm_uver(f.get("уверенность")),
           "почему_она": str(f.get("почему_фаза") or "").strip()[:200]}
    if faza in ("", "не знаю"):
        out["итог"] = "не знаю"
        return out
    if not d:
        out.update({"итог": "нечем судить",
                    "почему": "не сказано, вверх ход или вниз"})
        return out
    t0 = _vremya(out["начало"])
    tp = _vremya(m.get("когда_на_рынке"))
    # FAZY_SUDYA_V2: место — КОНЕЦ её бара. Дата бара — его открытие, а
    # смотрит она уже на закрытый бар. Раньше судья на мелком этаже
    # засчитывал «сбылось» за то, что было внутри бара, который она видела.
    try:
        import masshtab as _ms_v2
        from datetime import timedelta as _td_v2
        _mn_v2 = _ms_v2.minut(str(m.get("этаж") or ""))
        if tp is not None and _mn_v2:
            tp = tp + _td_v2(minutes=_mn_v2)
    except Exception:
        pass
    if t0 is None or tp is None or t0 >= tp:
        out.update({"итог": "нечем судить",
                    "почему": "начало хода не названо или не раньше места"})
        return out
    sym = str(m.get("инструмент") or "")
    s0, sp = t0.strftime(FORMAT), tp.strftime(FORMAT)
    p = _podobrat(sym, s0, sp, (tp - t0).total_seconds() / 60.0)
    if not p:
        out.update({"итог": "нечем судить",
                    "почему": f"котировок {sym} под этот ход не нашлось"})
        return out
    _, tf, _n = p
    bs, daty = _lenta(sym, tf)
    i0 = bisect.bisect_left(daty, s0)
    ip = bisect.bisect_right(daty, sp) - 1
    try:
        import istoriya
        while ip >= i0 and not istoriya.zakryt_li(
                bs[ip].get("date", ""), tf, sp):
            ip -= 1
    except Exception:
        pass
    if ip - i0 < 3:
        out.update({"итог": "нечем судить", "этаж": tf,
                    "почему": "на этом масштабе ход короче четырёх баров"})
        return out
    dlina = ip - i0 + 1
    vperyod = max(VPERYOD_MIN, min(VPERYOD_MAX, dlina))
    a = max(0, i0 - 40)                       # запас AO на разгон
    z = min(len(bs), ip + 1 + vperyod)
    obrezano = (ip + 1 + vperyod) > len(bs)
    seg = bs[a:z]
    from williams_core import compute_ao_series
    ao = compute_ao_series([x["high"] for x in seg], [x["low"] for x in seg])
    itog, pochemu = _sud(faza, d, seg, ao, i0 - a, ip - a, obrezano)
    out.update({"этаж": tf, "баров_в_ходе": dlina, "вперёд": vperyod,
                "итог": itog, "почему": pochemu})
    return out


def sudit_mesta(mesta: list) -> list:
    """Проходит места A07 и кладёт рядом «фаза_итог». Прочие не трогает."""
    n = 0
    for m in mesta or []:
        if str(m.get("слот") or "") not in SLOTY:
            continue
        try:
            m["фаза_итог"] = sudit_mesto(m)
        except Exception as e:
            m["фаза_итог"] = {"итог": "нечем судить",
                              "почему": f"судья споткнулся: {e}"}
        n += 1
    if n:
        print(f"[ФАЗЫ] судья прошёл мест: {n}")
    return mesta


def _bez_chert(s) -> str:
    return " ".join(str(s or "").replace("|", "/").split())[:180]


def svodka(mesta: list) -> list:
    """Блок отчёта. Мест A07 нет — пусто, отчёт A06 как был."""
    nashi = [(i, m) for i, m in enumerate(mesta or [], 1)
             if str(m.get("слот") or "") in SLOTY]
    if not nashi:
        return []
    for _, m in nashi:
        if "фаза_итог" not in m:
            try:
                m["фаза_итог"] = sudit_mesto(m)
            except Exception as e:
                m["фаза_итог"] = {"итог": "нечем судить",
                                  "почему": f"судья споткнулся: {e}"}
    vse = [m.get("фаза_итог") or {} for _, m in nashi]
    tri = ("третья", "четвёртая", "пятая")

    s = ["## Фазы хода — опыт (на вход не влияет)", ""]
    s.append("Судья механический: цена и AO, без модели. Судит на этаже, "
             "где её ход занимает около 120 баров, и смотрит вперёд "
             "столько же баров, сколько ход уже прошёл (не меньше 30, не "
             "больше 140). Итог — кандидат, не приговор: несколько мест "
             "сверь глазами.")
    s.append("")
    s.append("| фаза | названо | " + " | ".join(ITOGI) + " |")
    s.append("|---|---|" + "---|" * len(ITOGI))
    for faza in tri:
        ets = [e for e in vse if e.get("фаза") == faza]
        s.append(f"| {faza} | {len(ets)} | " + " | ".join(
            str(sum(1 for e in ets if e.get("итог") == it)) for it in ITOGI)
            + " |")
    s.append("")
    ne_znayu = sum(1 for e in vse if e.get("итог") == "не знаю")
    ne_nazvala = sum(1 for e in vse if e.get("итог") == "не назвала")
    s.append(f"Мест всего: **{len(nashi)}** · «не знаю» — {ne_znayu} · "
             f"фазу не назвала — {ne_nazvala}")
    s.append("")

    s.append("| уверенность | сбылось | не сбылось | под вопросом |")
    s.append("|---|---|---|---|")
    for u in ("мало", "средне", "уверена", "—"):
        ets = [e for e in vse if e.get("фаза") in tri
               and e.get("уверенность") == u]
        if not ets:
            continue
        s.append(f"| {u} | "
                 f"{sum(1 for e in ets if e.get('итог') == 'сбылось')} | "
                 f"{sum(1 for e in ets if e.get('итог') == 'не сбылось')} | "
                 f"{sum(1 for e in ets if e.get('итог') == 'под вопросом')} |")
    s.append("")

    s.append("### По местам")
    s.append("")
    s.append("| # | когда | пара | ход | начало | фаза | уверенность | "
             "этаж судьи | итог | почему (судья) | её слова |")
    s.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, m in nashi:
        e = m.get("фаза_итог") or {}
        et = e.get("этаж") or "—"
        if e.get("баров_в_ходе"):
            et += f" · {e['баров_в_ходе']} бар."
        s.append(f"| {i} | {m.get('когда_на_рынке', '')} | "
                 f"{m.get('инструмент', '')} {m.get('этаж', '')} | "
                 f"{e.get('ход', '—')} | {e.get('начало') or '—'} | "
                 f"{e.get('фаза', '—')} | {e.get('уверенность', '—')} | "
                 f"{et} | {e.get('итог', '—')} | "
                 f"{_bez_chert(e.get('почему'))} | "
                 f"{_bez_chert(e.get('почему_она'))} |")
    s.append("")
    return s


# FAZA_HODA_V1 - marker


# ── FAZY_SUDYA_V2: пересудить прогон, который уже прошёл ──────
def perestroit_otchyot(papka) -> str:
    """Заново судит места A07 прогона и переписывает блок «Фазы хода» в
    его отчёте. Остальной отчёт не трогает. Возвращает строку-итог."""
    import json as _js
    papka = Path(papka)
    f = papka / "места.jsonl"
    if not f.exists():
        return ""
    syroe = f.read_bytes().decode("utf-8")
    mesta = []
    for s in syroe.splitlines():
        s = s.strip()
        if s:
            try:
                mesta.append(_js.loads(s))
            except Exception:
                continue
    if not any(str(m.get("слот") or "") in SLOTY and m.get("фаза")
               for m in mesta):
        return ""
    bylo = {}
    for m in mesta:
        it = (m.get("фаза_итог") or {}).get("итог")
        if it:
            bylo[it] = bylo.get(it, 0) + 1
        m.pop("фаза_итог", None)
    sudit_mesta(mesta)
    stalo = {}
    for m in mesta:
        it = (m.get("фаза_итог") or {}).get("итог")
        if it:
            stalo[it] = stalo.get(it, 0) + 1
    # котировок у судьи не нашлось — не затираем прежний суд пустым
    if stalo.get("нечем судить", 0) > bylo.get("нечем судить", 0) + 3:
        return ("не пересудил: у судьи не нашлось котировок, прежний "
                "суд оставлен")
    f.write_text("\n".join(_js.dumps(m, ensure_ascii=False) for m in mesta)
                 + "\n", encoding="utf-8")
    po = papka / "отчёт.md"
    if po.exists():
        t = po.read_bytes().decode("utf-8")
        crlf = "\r\n" in t
        t = t.replace("\r\n", "\n")
        a = t.find("## Фазы хода")
        if a >= 0:
            b = t.find("\n## ", a + 5)
            b = len(t) if b < 0 else b + 1
            novyy = "\n".join(svodka(mesta)).rstrip("\n") + "\n\n"
            t = t[:a] + novyy + t[b:]
            po.write_bytes((t.replace("\n", "\r\n") if crlf else t)
                           .encode("utf-8"))
    try:
        import arhiv_birzhi as _ab
        _ab.kartochka_progona(papka)
    except Exception:
        pass
    _sl = lambda d: ", ".join(f"{k} {v}" for k, v in sorted(d.items()))
    return f"было: {_sl(bylo)} → стало: {_sl(stalo)}"


# FAZY_SUDYA_V2 - marker
