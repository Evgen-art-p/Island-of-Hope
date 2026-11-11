# -*- coding: utf-8 -*-
# UROKI_PROGONOV_V1
"""
УРОКИ ПРОГОНОВ — чем кончались его входы, по типу входа, а не по дате (20.10).

СЛОВО ШЕФА 20.10
    «Если он всегда по-новой — значит совсем ни опыта, ни памяти. Как он научится?»
    «Делай.»

ЧТО ДЕЛАЕТ
    1. После каждого прогона (nositel.sledy_progona) каждому жителю на месте
       уровня «продвинутый новичок» в его дом, работа/uroki_progonov.jsonl, ложится по строке на
       закрытую сделку: чем кончилась (R, причина) и что ГОРОД говорил на входе
       (разворот по волнам, пули, младший). Опыт едет с жителем, а не остаётся
       на месте: житель пересел с A08 на D01 — уроки при нём.
    2. На каждом баре место уровня «продвинутый новичок» получает в задание блок «ТВОИ ПРОШЛЫЕ
       ПРОГОНЫ — ИТОГИ ПО ТИПУ ВХОДА»: сделки по типам, не по датам.
    3. КАРАНТИН ГОДА. Прогон по истории на 2024 не видит сделок 2024 года и сделок
       своего же прогона: иначе он помнил бы ответ, а не учился. Вне прогона
       (живая работа) видно всё.

ПОЧЕМУ ТИПЫ — ПО СЛОВАМ ГОРОДА, А НЕ ПО ЕГО СЛОВАМ
    «Откат / по ходу» зависит от того, как он назвал старший ход, а в разных
    прогонах на одном и том же 2024-м он называл месяц то «вверх с 2022», то
    «вниз с 2014»: одна и та же сделка выходила то откатом, то ходом. Поэтому
    основа уроков — факты города на входе: разворот по волнам (да/нет), пули у
    края, младший. Его собственное «откат / по ходу» идёт отдельной строкой.

ЧЕГО НЕ ДЕЛАЕТ
    Ничего не решает и не запрещает: факты и числа. Мало сделок — так и написано.
    Город не торгует.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
KOREN = _BIRZHA.parent
CITY = KOREN / "GRONDHEIM_CITY"
POSTY = CITY / "посты"
CEHA = CITY / "Биржа" / "цеха"
DANNYE = CITY / "Биржа" / "данные"
KOVCHEG = CITY / "жители" / "ковчег"
FAYL = "uroki_progonov.jsonl"
MIN_SDELOK = 5          # меньше — блока нет: это не закономерность
NOL = 0.005


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def _d10(s) -> str:
    return str(s or "")[:10].replace("-", ".")


def _ravny(a, b) -> bool:
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= max(2e-6, abs(a) * 2e-6)


def _pr(z) -> float:
    try:
        return float(z.get("pnl_r"))
    except (TypeError, ValueError):
        return 0.0


def _glavnaya(z) -> bool:
    return not (z.get("нога") or z.get("частичное") or z.get("тень"))


# ── запись одной сделки ──────────────────────────────────────────
def _storona(m, z) -> str:
    try:
        return "SHORT" if float(m["стоп_входа"]) > float(m["цена_входа"]) else "LONG"
    except Exception:
        pass
    try:
        e, x = float(z.get("entry")), float(z.get("exit"))
        pr = float(z.get("pnl_price"))
        if x != e and pr != 0:
            return "LONG" if (x > e) == (pr > 0) else "SHORT"
    except Exception:
        pass
    return ""


def _zapisi(ceh, slot, run_id, mesta, hody, zakr) -> list:
    """Записи по закрытым сделкам одного места в одном прогоне."""
    out = []
    for z in zakr:
        if not _glavnaya(z) or z.get("pnl_r") is None:
            continue
        sym = str(z.get("symbol") or "").upper()
        ot = _d10(z.get("opened_at"))
        kand = [m for m in mesta
                if str(m.get("действие") or "").upper() == "ENTER"
                and _ravny(m.get("цена_входа"), z.get("entry"))
                and _d10(m.get("когда_на_рынке")) <= ot]
        m = kand[-1] if kand else {}
        bar = _d10(m.get("когда_на_рынке")) if m else ""
        vhody = ((hody or {}).get(sym) or {}).get("входы") or []
        e = next((v for v in reversed(vhody)
                  if v.get("что") == "ENTER" and _d10(v.get("бар")) == bar), None) \
            if bar else None
        out.append({
            "прогон": run_id, "цех": ceh, "слот": slot, "symbol": sym,
            "tf": str(z.get("timeframe") or "").upper(),
            "год": str(z.get("opened_at") or "")[:4],
            "вход": bar, "открыта": z.get("opened_at"), "entry": z.get("entry"),
            "сторона": _storona(m, z), "R": round(_pr(z), 4),
            "причина": z.get("close_reason"),
            "разворот": (e or {}).get("разворот"),
            "пуль": (e or {}).get("пуль"),
            "младший": (e or {}).get("младший_кончик"),
            "это": (e or {}).get("это"),
        })
    return out


def _klyuch(r) -> tuple:
    return (r.get("прогон"), r.get("открыта"), round(float(r.get("entry") or 0), 5))


def _dopisat(dom: Path, zapisi: list) -> int:
    if not zapisi:
        return 0
    papka = Path(dom) / "работа"
    papka.mkdir(parents=True, exist_ok=True)
    f = papka / FAYL
    uzhe = set()
    if f.is_file():
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                uzhe.add(_klyuch(json.loads(ln)))
            except Exception:
                pass
    novye = [r for r in zapisi if _klyuch(r) not in uzhe]
    if novye:
        with open(f, "a", encoding="utf-8") as fh:
            for r in novye:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(novye)


# ── конец прогона: запись в дом жителя ───────────────────────────
def zapisat_iz_progona(papka, progon_id, zakrytiya, ceh) -> list:
    """Вызывает nositel.sledy_progona. Возвращает строки для лога."""
    out = []
    papka = Path(papka)
    run_id = papka.name
    try:
        mesta = [json.loads(s) for s in
                 (papka / "места.jsonl").read_text(encoding="utf-8").splitlines()
                 if s.strip()]
    except Exception:
        mesta = []
    try:
        import hod_mesyaca as _hm
        import mesto_urovnya as _md
        from nositel import dusha_slota
    except Exception as e:
        return [f"уроки: модули не поднялись ({e})"]
    for slot in sorted({str(m.get("слот") or "") for m in mesta if m.get("слот")}):
        try:
            if not _hm._nash(slot):
                continue
            hody = ((_json(CEHA / ceh / "слоты" / slot / "данные" / "ход_месяца.json")
                     or {}).get("прогоны") or {}).get(run_id) or {}
            magic = _md.nomer_mesta(slot, ceh)
            moi = [z for z in (zakrytiya or [])
                   if (magic is not None and z.get("magic") == magic)
                   or (magic is None and str(z.get("trader") or "").upper() == slot.upper())]
            n = dusha_slota(ceh, slot)
            if not n:
                continue
            dom = Path(n["носитель"]["папка"])
            zap = _zapisi(ceh, slot, run_id, [m for m in mesta if m.get("слот") == slot],
                          hody, moi)
            dop = _dopisat(dom, zap)
            out.append(f"{n['носитель'].get('имя') or dom.name}: уроки — "
                       f"{dop} новых записей из {len(zap)} закрытых сделок")
        except Exception as e:
            out.append(f"{slot}: уроки не легли — {e}")
    return out


# ── задним числом: из того, что уже лежит в городе ────────────────
def _sroki(post) -> list:
    sroki, otkryt = [], None
    for z in post.get("трудовая_история") or []:
        t = str(z.get("когда") or "")
        imya = str(z.get("кто") or "").strip()
        if z.get("что") == "принят" and imya:
            otkryt = (imya, t)
        elif z.get("что") == "уволен" and otkryt and otkryt[0] == imya:
            sroki.append((imya, otkryt[1], t))
            otkryt = None
    if otkryt:
        sroki.append((otkryt[0], otkryt[1], "9999"))
    return sroki


def _zhurnal() -> list:
    fayly = []
    for nm in ("trading_pnl.jsonl",):
        p = DANNYE / nm
        if p.is_file():
            fayly.append(p)
    fayly += sorted(DANNYE.glob("trading_pnl_archive_*.jsonl"))
    vse, vidno = [], set()
    for f in fayly:
        try:
            for ln in f.read_text(encoding="utf-8").splitlines():
                try:
                    z = json.loads(ln)
                except Exception:
                    continue
                k = (z.get("ts"), z.get("entry"), z.get("exit"), z.get("magic"))
                if k not in vidno:
                    vidno.add(k)
                    vse.append(z)
        except Exception:
            continue
    return vse


def _starty(ceh: str) -> list:
    import re
    d = CEHA / ceh / "прогоны"
    out = []
    if d.is_dir():
        for x in d.iterdir():
            m = re.fullmatch(r"(\d{8})_(\d{6})", x.name)
            if m:
                s, t = m.group(1), m.group(2)
                out.append((f"{s[:4]}-{s[4:6]}-{s[6:8]}T{t[:2]}:{t[2:4]}:{t[4:6]}", x.name))
    return sorted(out)


def perestroit() -> dict:
    """Собрать уроки из старых прогонов (то, что лежит в ход_месяца.json мест
    уровня «продвинутый новичок» и в журнале закрытий). Безопасно повторять: дублей не будет."""
    from bisect import bisect_right
    itog = defaultdict(int)
    posty = []
    if POSTY.is_dir():
        for d in sorted(POSTY.iterdir()):
            p = _json(d / "пост.json")
            if p and isinstance(p.get("magic"), int) and p.get("цех") and p.get("слот"):
                posty.append(p)
    zhurnal = _zhurnal()
    for p in posty:
        ceh, slot, magic = p["цех"], str(p["слот"]), p["magic"]
        hm = _json(CEHA / ceh / "слоты" / slot / "данные" / "ход_месяца.json")
        if not hm:
            continue
        sroki = _sroki(p)
        starty = _starty(ceh)
        vremena = [a for a, _b in starty]
        mojj = [z for z in zhurnal if z.get("magic") == magic]
        for run_id, hody in (hm.get("прогоны") or {}).items():
            idx = next((i for i, (_a, b) in enumerate(starty) if b == run_id), None)
            if idx is None:
                continue
            a = starty[idx][0]
            b = starty[idx + 1][0] if idx + 1 < len(starty) else "9999"
            zakr = [z for z in mojj if a <= str(z.get("ts") or "")[:19] < b]
            mesta = []
            try:
                mesta = [json.loads(s) for s in
                         (CEHA / ceh / "прогоны" / run_id / "места.jsonl")
                         .read_text(encoding="utf-8").splitlines() if s.strip()]
            except Exception:
                pass
            po_zhitelyam = defaultdict(list)
            for z in zakr:
                ts = str(z.get("ts") or "").replace("T", " ")[:16]
                kto = next((i for i, s1, s2 in sroki if s1 <= ts < s2), None)
                if kto:
                    po_zhitelyam[kto].append(z)
            for kto, zz in po_zhitelyam.items():
                dom = KOVCHEG / kto
                if not dom.is_dir():
                    continue
                zap = _zapisi(ceh, slot, run_id,
                              [m for m in mesta if m.get("слот") == slot], hody, zz)
                itog[kto] += _dopisat(dom, zap)
    return dict(itog)


# ── блок в задание ────────────────────────────────────────────────
def _zapisi_zhitelya(dom: Path) -> list:
    f = Path(dom) / "работа" / FAYL
    out = []
    if f.is_file():
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def _gruppy(recs, kl) -> dict:
    g = defaultdict(list)
    for r in recs:
        g[kl(r)].append(float(r["R"]))
    return g


def _stroka(g, poryadok) -> str:
    chasti = []
    for k in poryadok:
        x = g.get(k)
        if x:
            plyus = sum(1 for v in x if v > NOL)
            chasti.append(f"«{k}»: {len(x)} сделок, {plyus} в плюс, итог {sum(x):+.2f}R")
    return "; ".join(chasti)


def tekst(recs, god_seychas=None, run_seychas=None, symbol="", tf="") -> str:
    """Блок уроков из записей. Карантин: сделки текущего года и текущего прогона
    не показываются (если god_seychas задан — это прогон по истории)."""
    rr = [r for r in recs if r.get("R") is not None]
    if symbol:
        rr = [r for r in rr if str(r.get("symbol") or "").upper() == str(symbol).upper()]
    if tf:
        rr = [r for r in rr if str(r.get("tf") or "").upper() in ("", str(tf).upper())]
    if god_seychas:
        rr = [r for r in rr if str(r.get("год")) != str(god_seychas)
              and r.get("прогон") != run_seychas]
    if len(rr) < MIN_SDELOK:
        return ""
    po_godam = defaultdict(list)
    for r in rr:
        po_godam[str(r.get("год"))].append(float(r["R"]))
    goda = ", ".join(f"{g} — {len(v)} ({sum(v):+.2f}R)" for g, v in sorted(po_godam.items()))
    razv = lambda r: {True: "да", False: "нет"}.get(r.get("разворот"), "не считался")

    def puli(r):
        p = r.get("пуль")
        return "не считали" if p is None else ("0–2" if p <= 2 else ("3" if p == 3 else "4–5"))
    mlad = lambda r: {True: "кончик", False: "рано"}.get(r.get("младший"), "не смотрел")
    eto = lambda r: str(r.get("это") or "не назвал")
    def _l(nazv, g, poryadok):
        t = _stroka(g, poryadok)
        return f"  · {nazv}: {t}" if t else ""
    svoi = _stroka(_gruppy(rr, eto), ("в откат", "по ходу", "нет", "не назвал"))
    L = ["=== ТВОИ ПРОШЛЫЕ ПРОГОНЫ — ИТОГИ ПО ТИПУ ВХОДА (не по датам) ===",
         "Закрытые сделки твоих прогонов" + (" на других годах" if god_seychas else "")
         + f": {len(rr)} (по годам: {goda}). "
         + (f"Сделок {god_seychas} года и этого прогона здесь нет — иначе ты помнил бы "
            "ответ, а не учился. " if god_seychas else "")
         + "Что говорил город на входе → чем кончилось:",
         _l("разворот по волнам", _gruppy(rr, razv), ("да", "нет", "не считался")),
         _l("пули у края на входе", _gruppy(rr, puli), ("0–2", "3", "4–5", "не считали")),
         _l("младший этаж", _gruppy(rr, mlad), ("кончик", "рано", "не смотрел")),
         ("Как ты сам называл вход (его слова — старший ход ты называл по-разному в "
          "разных прогонах, одна и та же сделка выходила то откатом, то ходом): " + svoi)
         if svoi else "",
         "Это факты, а не правила: в других годах рынок другой. Где мало сделок — "
         "это ещё не закономерность. Что с этим делать — решаешь ты."]
    return "\n".join(x for x in L if x) + "\n\n"


def blok(slot, symbol, tf, bar=None) -> str:
    """Для hod_mesyaca.blok: блок уроков места уровня «продвинутый новичок»."""
    try:
        import hod_mesyaca as _hm
        import mesto_urovnya as _md
        from cartridge_registry import resolve_para
        if not _hm._nash(slot):
            return ""
        ceh = _md.ceh_mesta(slot)
        n = resolve_para(ceh, slot)
        if not n:
            return ""
        recs = _zapisi_zhitelya(Path(n["папка"]))
        if not recs:
            return ""
        run, god = None, None
        try:
            from hooks import load_trading_state
            run = ((load_trading_state() or {}).get("прогон") or {}).get("id")
        except Exception:
            run = None
        if run:                                   # прогон по истории — карантин года
            god = str(bar or _hm._bar_seychas() or "")[:4]
        return tekst(recs, god if god and god.isdigit() else None, run, symbol, tf)
    except Exception as e:
        print(f"[УРОКИ] блок не сложился ({e})")
        return ""


# UROKI_PROGONOV_V1 - marker


# ══ OPYT_STOLA_V1 — у места со столом опыта старых «уроков» нет: один голос ══
_blok_urokov_do_opyta = blok


def blok(slot, symbol, tf, bar=None) -> str:   # noqa: F811
    try:
        import mesto_urovnya as _mu
        import opyt_stola as _os
        if _os.vklyucheno(_mu.ceh_mesta(slot), slot):
            return ""
    except Exception:
        pass
    return _blok_urokov_do_opyta(slot, symbol, tf, bar)


# OPYT_STOLA_V1 - marker
