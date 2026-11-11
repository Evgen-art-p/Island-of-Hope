# -*- coding: utf-8 -*-
# ARHIV_BIRZHI_V1
"""
АРХИВ БИРЖИ — опыт Биржи с карточками, по эпохам.

СЛОВО ШЕФА (01.10)
    «Все наработки биржи не в чулане должны быть, а в архиве биржи, и
    доставались по меткам — по запросу, так можно использовать для
    практики любой опыт.» Старый ошибочный опыт (код врал) — в чулан.
    «Сейчас у Синди после каждого прогона эпохи меняться будут))» —
    поэтому эпоха меняется ТОЛЬКО когда машина врала в данных или в
    счёте, а не когда меняются правила или подача. Объявляет её Шеф.

ЗАКОН ЭТОГО ФАЙЛА (тот же, что у Архива Города)
    Архив знает, ГДЕ лежит опыт, и заводит на него карточку. Прогоны не
    переносит: они живут в папке прогонов, с неё читает страница отчёта.
    Одно исключение — то, что лежит ПРИ МЕСТЕ (тетрадь, картина): место
    переживает жильцов, и чужое досталось бы следующему как своё.
    Поэтому чужое с места уезжает сюда, по людям.

    Две метки на каждой карточке:
        кто    — чей опыт (имя жителя), ставится сама;
        эпоха  — в какой версии машины набран. Новая эпоха — всё, что
                 до неё, уходит в чулан (архив делает это сам).

ЧТО ЗДЕСЬ ЛЕЖИТ
    GRONDHEIM_CITY/Биржа/архив/
        эпохи.json       — эпохи и почему каждая началась
        карточки.jsonl   — по карточке на прогон, тетрадь, картину
        тетради/<кто>__<место>.jsonl
        картины/<кто>__<место>.json
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys as _sys
from datetime import datetime
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
KOREN = _BIRZHA.parent
CITY_B = KOREN / "GRONDHEIM_CITY" / "Биржа"
CEHA = CITY_B / "цеха"
DANNYE = CITY_B / "данные"
ARHIV = CITY_B / "архив"
EPOHI = ARHIV / "эпохи.json"
KARTOCHKI = ARHIV / "карточки.jsonl"
TETRADI = ARHIV / "тетради"
KARTINY = ARHIV / "картины"
CHULAN = KOREN / "_ЧУЛАН" / "старое"
TORG_CEHA = ("торговый_хаос",)

PERVAYA_EPOHA = {
    "номер": 1, "с": "2026-09-27 00:00",
    "почему": ("до этого дня машина врала в данных и в счёте (невидимая "
               "свеча, сломанная подача дивера, неверный счёт R, общая "
               "тетрадь без метки прогона); с этого дня у записи метка "
               "прогона"),
}


# ── время ─────────────────────────────────────────────────────
def _vremya(s):
    s = str(s or "").strip()
    for f in ("%Y-%m-%d %H:%M", "%Y%m%d_%H%M%S", "%Y-%m-%dT%H:%M:%S",
              "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19] if "T" in s else s, f)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s[:19])
    except Exception:
        return None


def _iz_ts(ts):
    try:
        return datetime.fromtimestamp(float(ts))
    except Exception:
        return None


def _iz_imeni(imya: str):
    """Время из имени вида 20260929_175316 или ..._archive_20260929_175316."""
    m = re.search(r"(\d{8}_\d{6})", imya or "")
    return _vremya(m.group(1)) if m else None


# ── эпохи ─────────────────────────────────────────────────────
def epohi() -> list:
    try:
        L = json.loads(EPOHI.read_text(encoding="utf-8"))
        if isinstance(L, list) and L:
            return sorted(L, key=lambda e: int(e.get("номер") or 0))
    except Exception:
        pass
    ARHIV.mkdir(parents=True, exist_ok=True)
    EPOHI.write_text(json.dumps([PERVAYA_EPOHA], ensure_ascii=False,
                                indent=2), encoding="utf-8")
    return [dict(PERVAYA_EPOHA)]


def tekushchaya() -> dict:
    return epohi()[-1]


def nachalo() -> datetime:
    return _vremya(tekushchaya().get("с")) or datetime(2026, 9, 27)


def epoha_v(moment) -> int:
    """Номер эпохи, в которой лежит момент. До первой — 0."""
    if moment is None:
        return 0
    n = 0
    for e in epohi():
        t = _vremya(e.get("с"))
        if t and t <= moment:
            n = int(e.get("номер") or 0)
    return n


# ── карточки ──────────────────────────────────────────────────
def kartochki() -> list:
    if not KARTOCHKI.exists():
        return []
    out = []
    for s in KARTOCHKI.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(s))
        except Exception:
            continue
    return out


def _zapisat_kartochki(L: list):
    ARHIV.mkdir(parents=True, exist_ok=True)
    _atomno(KARTOCHKI, "\n".join(json.dumps(k, ensure_ascii=False)
                                 for k in L) + ("\n" if L else ""))


def polozhit(k: dict):
    L = [x for x in kartochki() if x.get("id") != k.get("id")]
    L.append(k)
    _zapisat_kartochki(L)


def _klyuch(imya: str) -> str:
    try:
        _g = str(KOREN / "ГОРОД")
        if _g not in _sys.path:
            _sys.path.insert(0, _g)
        import klyuch
        return klyuch.klyuch_zhitelya(imya) or ""
    except Exception:
        return ""


def _otn(p: Path) -> str:
    try:
        return str(p.relative_to(KOREN))
    except Exception:
        return str(p)


def _atomno(p: Path, tekst: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp_arhiv")
    tmp.write_text(tekst, encoding="utf-8")
    os.replace(tmp, p)


def _dopisat(p: Path, zapisi: list):
    if not zapisi:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        for z in zapisi:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")


# ── карточка прогона ──────────────────────────────────────────
def _chislo_posle(tekst: str, razdel: str, shablon: str):
    i = tekst.find(razdel)
    if i < 0:
        return None
    m = re.search(shablon, tekst[i:i + 4000])
    return m.group(1) if m else None


def kartochka_progona(papka) -> dict | None:
    """Карточка на прогон — из того, что отчёт уже записал."""
    papka = Path(papka)
    f = papka / "места.jsonl"
    if not f.exists():
        return None
    mesta = []
    for s in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            mesta.append(json.loads(s))
        except Exception:
            continue
    if not mesta:
        return None
    try:
        otch = (papka / "отчёт.md").read_text(encoding="utf-8",
                                               errors="ignore")
    except Exception:
        otch = ""
    r = _chislo_posle(otch, "### Чем кончилось",
                      r"\| итог в R \| ([+-]?\d+(?:\.\d+)?)R \|")
    zakr = _chislo_posle(otch, "### Чем кончилось",
                         r"\| сделок закрыто \| (\d+) \|")
    kto = sorted({str(m.get("кто") or "") for m in mesta} - {""})
    sloty = sorted({str(m.get("слот") or "") for m in mesta} - {""})
    instr = sorted({str(m.get("инструмент") or "") for m in mesta} - {""})
    etazhi = sorted({str(m.get("этаж") or "") for m in mesta} - {""})
    daty = sorted(str(m.get("когда_на_рынке") or "") for m in mesta
                  if m.get("когда_на_рынке"))
    vhodov = sum(1 for m in mesta
                 if str(m.get("действие") or "").upper() == "ENTER")
    fazy = {}
    for m in mesta:
        it = (m.get("фаза_итог") or {}).get("итог")
        if it:
            fazy[it] = fazy.get(it, 0) + 1
    t = _iz_imeni(papka.name)
    k = {
        "id": f"прогон:{papka.name}", "вид": "прогон",
        "кто": kto, "ключи": [x for x in (_klyuch(i) for i in kto) if x],
        "место": sloty, "инструмент": instr, "этаж": etazhi,
        "рынок_с": daty[0] if daty else "", "рынок_по": daty[-1] if daty else "",
        "мест": len(mesta), "входов": vhodov,
        "сделок_закрыто": int(zakr) if zakr else 0,
        "итог_R": float(r) if r is not None else None,
        "фазы": fazy,
        "когда": t.strftime("%Y-%m-%d %H:%M") if t else "",
        "эпоха": epoha_v(t),
        "ярлыки": sorted(set(kto + sloty + instr + etazhi + ["прогон"]
                             + (["фазы"] if fazy else []))),
        "где": _otn(papka),
    }
    polozhit(k)
    print(f"[АРХИВ БИРЖИ] карточка: прогон {papka.name} · "
          f"{', '.join(kto) or '—'} · {' '.join(instr)} {' '.join(etazhi)}")
    return k


# ── места: тетрадь и картина ──────────────────────────────────
def _kto_sidit(ceh: str, slot: str) -> str:
    try:
        _g = str(KOREN / "ГОРОД")
        if _g not in _sys.path:
            _sys.path.insert(0, _g)
        import rabota
        return (rabota.kto_na_slote(ceh, slot) or "").strip()
    except Exception:
        return ""


def _chitat_jsonl(p: Path) -> list:
    out = []
    try:
        for s in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = s.strip()
            if not s:
                continue
            try:
                out.append(json.loads(s))
            except Exception:
                out.append({"_сырое": s})
    except Exception:
        pass
    return out


def _kartochka_tetradi(avtor: str, slot: str, p: Path):
    zap = _chitat_jsonl(p)
    bary = sorted(str(z.get("bar_time") or "") for z in zap
                  if z.get("bar_time"))
    instr = sorted({str(z.get("symbol") or "") for z in zap} - {""})
    etazhi = sorted({str(z.get("timeframe") or "") for z in zap} - {""})
    progony = sorted({str(z.get("прогон")) for z in zap if z.get("прогон")})
    vremena = [t for t in (_iz_ts(z.get("ts")) for z in zap) if t]
    polozhit({
        "id": f"тетрадь:{avtor}:{slot}", "вид": "тетрадь",
        "кто": [avtor], "ключи": [x for x in [_klyuch(avtor)] if x],
        "место": [slot], "инструмент": instr, "этаж": etazhi,
        "рынок_с": bary[0] if bary else "", "рынок_по": bary[-1] if bary else "",
        "записей": len(zap), "прогонов": len(progony),
        "когда": max(vremena).strftime("%Y-%m-%d %H:%M") if vremena else "",
        "эпоха": epoha_v(max(vremena)) if vremena else 0,
        "ярлыки": sorted(set([avtor, slot, "тетрадь"] + instr + etazhi)),
        "где": _otn(p),
    })


_KARTINA_POLYA = ("точка_ноль", "волна", "откат")


def _razrezat_kartinu(moya: dict, berem) -> tuple:
    """(взято, осталось) — по записям; berem(запись) -> bool."""
    pusto = lambda: {"точка_ноль": None, "волна": None, "откат": None,
                     "заметки": [], "попыток": 0}
    vzyato, ostalos = pusto(), pusto()
    for k in _KARTINA_POLYA:
        z = moya.get(k)
        if isinstance(z, dict):
            (vzyato if berem(z) else ostalos)[k] = z
    for z in moya.get("заметки") or []:
        if isinstance(z, dict):
            (vzyato if berem(z) else ostalos)["заметки"].append(z)
    tn = moya.get("точка_ноль")
    if isinstance(tn, dict):
        (vzyato if berem(tn) else ostalos)["попыток"] = \
            int(moya.get("попыток") or 0)
    return vzyato, ostalos


def _est_li(moya: dict) -> bool:
    return any(isinstance(moya.get(k), dict) for k in _KARTINA_POLYA) \
        or bool(moya.get("заметки"))


def razobrat_mesto(ceh: str, slot: str, kuda_staroe: Path | None = None) -> list:
    """С места: записи прошлых эпох — в чулан, чужие — в архив по людям.
    Своё (того, кто сидит) и неподписанное — остаётся."""
    out = []
    papka = CEHA / ceh / "слоты" / slot / "данные"
    if not papka.is_dir():
        return out
    start = nachalo()
    kuda_staroe = kuda_staroe or (CHULAN / f"до_эпохи_{tekushchaya()['номер']}")
    sidit = _kto_sidit(ceh, slot)

    # тетрадь места
    for f in sorted(papka.glob("diary_*.jsonl")):
        zap = _chitat_jsonl(f)
        if not zap:
            continue
        ostaetsya, v_chulan, chuzhoe = [], [], {}
        for z in zap:
            t = _iz_ts(z.get("ts"))
            avtor = str(z.get("кто") or z.get("житель") or "").strip()
            if t is None or t < start:
                v_chulan.append(z)
            elif avtor and avtor != sidit:
                chuzhoe.setdefault(avtor, []).append(z)
            else:
                ostaetsya.append(z)
        if not v_chulan and not chuzhoe:
            continue
        _dopisat(kuda_staroe / "тетради" / f"{slot}__{f.name}", v_chulan)
        for avtor, zz in chuzhoe.items():
            p = TETRADI / f"{avtor}__{slot}.jsonl"
            _dopisat(p, zz)
            _kartochka_tetradi(avtor, slot, p)
        _atomno(f, "\n".join(json.dumps(z, ensure_ascii=False)
                             for z in ostaetsya) + ("\n" if ostaetsya else ""))
        out.append(f"тетрадь {slot}: в чулан {len(v_chulan)}, в архив "
                   + (", ".join(f"{a} {len(z)}" for a, z in chuzhoe.items())
                      or "0") + f", осталось {len(ostaetsya)}")

    # картина места
    fk = papka / "картина.json"
    if fk.exists():
        try:
            vsya = json.loads(fk.read_text(encoding="utf-8")) or {}
        except Exception:
            vsya = {}
        staroe, chuzhoe, ostaetsya = {}, {}, {}
        for sym, moya in vsya.items():
            if not isinstance(moya, dict):
                continue
            star = lambda z: ((_vremya(z.get("когда")) or datetime(1970, 1, 1))
                              < start)
            vz, moya2 = _razrezat_kartinu(moya, star)
            if _est_li(vz):
                staroe[sym] = vz
            avtory = {str(z.get("кто") or "").strip()
                      for z in ([moya2.get(k) for k in _KARTINA_POLYA]
                                + list(moya2.get("заметки") or []))
                      if isinstance(z, dict)}
            for avtor in sorted(avtory - {"", sidit}):
                vz, moya2 = _razrezat_kartinu(
                    moya2, lambda z, a=avtor: str(z.get("кто") or "").strip() == a)
                if _est_li(vz):
                    chuzhoe.setdefault(avtor, {})[sym] = vz
            if _est_li(moya2):
                ostaetsya[sym] = moya2
        if staroe or chuzhoe:
            if staroe:
                p = kuda_staroe / "картины" / f"{slot}_картина.json"
                bylo = {}
                if p.exists():
                    try:
                        bylo = json.loads(p.read_text(encoding="utf-8")) or {}
                    except Exception:
                        bylo = {}
                bylo.update(staroe)
                _atomno(p, json.dumps(bylo, ensure_ascii=False, indent=2))
            for avtor, kart in chuzhoe.items():
                p = KARTINY / f"{avtor}__{slot}.json"
                bylo = {}
                if p.exists():
                    try:
                        bylo = json.loads(p.read_text(encoding="utf-8")) or {}
                    except Exception:
                        bylo = {}
                bylo.update(kart)
                _atomno(p, json.dumps(bylo, ensure_ascii=False, indent=2))
                polozhit({
                    "id": f"картина:{avtor}:{slot}", "вид": "картина",
                    "кто": [avtor], "ключи": [x for x in [_klyuch(avtor)] if x],
                    "место": [slot], "инструмент": sorted(bylo),
                    "когда": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "эпоха": tekushchaya()["номер"],
                    "ярлыки": sorted(set([avtor, slot, "картина"] + list(bylo))),
                    "где": _otn(p)})
            _atomno(fk, json.dumps(ostaetsya, ensure_ascii=False, indent=2))
            out.append(f"картина {slot}: в чулан {len(staroe)} инстр., в архив "
                       + (", ".join(f"{a} {len(k)}" for a, k in chuzhoe.items())
                          or "0"))
    return out


def snyat_s_mesta(ceh: str, slot: str, imya: str = "") -> list:
    """Зовёт Страница Работы при увольнении: место уже свободно, всё
    подписанное уезжает в архив по людям."""
    if ceh not in TORG_CEHA or not slot:
        return []
    out = razobrat_mesto(ceh, slot)
    for s in out:
        print(f"[АРХИВ БИРЖИ] {s}")
    return out


# ── уборка по эпохам ──────────────────────────────────────────
def ubrat_staroe() -> list:
    """Всё, что старше текущей эпохи, — в чулан; на свежие прогоны —
    карточки. Повторный запуск ничего не ломает."""
    out = []
    start = nachalo()
    n = tekushchaya()["номер"]
    kuda = CHULAN / f"до_эпохи_{n}"

    # прогоны
    for ceh in sorted(CEHA.iterdir()) if CEHA.is_dir() else []:
        pp = ceh / "прогоны"
        if not pp.is_dir():
            continue
        ushlo = 0
        for d in sorted(pp.iterdir()):
            t = _iz_imeni(d.name)
            if d.is_dir() and t and t < start:
                cel = kuda / "прогоны" / ceh.name / d.name
                cel.parent.mkdir(parents=True, exist_ok=True)
                if cel.exists():
                    shutil.rmtree(cel)
                shutil.move(str(d), str(cel))
                ushlo += 1
        if ushlo:
            out.append(f"прогоны {ceh.name}: в чулан {ushlo}")
        svezhie = [d for d in sorted(pp.iterdir()) if d.is_dir()]
        est = {k.get("id") for k in kartochki()}
        novyh = 0
        for d in svezhie:
            if f"прогон:{d.name}" not in est:
                if kartochka_progona(d):
                    novyh += 1
        if novyh:
            out.append(f"прогоны {ceh.name}: карточек заведено {novyh}")

    # журналы сделок (копии от «ОЧИСТИТЬ»)
    if DANNYE.is_dir():
        ushlo = 0
        for f in sorted(DANNYE.glob("trading_pnl_archive_*.jsonl")):
            t = _iz_imeni(f.name)
            if t and t < start:
                cel = kuda / "журналы_сделок" / f.name
                cel.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(cel))
                ushlo += 1
        if ushlo:
            out.append(f"журналы сделок: в чулан {ushlo}")

    # места
    for ceh in TORG_CEHA:
        sl = CEHA / ceh / "слоты"
        if sl.is_dir():
            for d in sorted(sl.iterdir()):
                if d.is_dir():
                    out += razobrat_mesto(ceh, d.name, kuda)

    # уже лежащее в архиве — тетради и картины прошлых эпох
    if TETRADI.is_dir():
        for f in sorted(TETRADI.glob("*.jsonl")):
            zap = _chitat_jsonl(f)
            st = [z for z in zap if (_iz_ts(z.get("ts")) or start) < start]
            if st:
                _dopisat(kuda / "тетради" / f"архив__{f.name}", st)
                ost = [z for z in zap if z not in st]
                _atomno(f, "\n".join(json.dumps(z, ensure_ascii=False)
                                     for z in ost) + ("\n" if ost else ""))
                out.append(f"архив, тетрадь {f.stem}: в чулан {len(st)}")
    if KARTINY.is_dir():
        for f in sorted(KARTINY.glob("*.json")):
            try:
                vsya = json.loads(f.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            staroe, ost = {}, {}
            for sym, moya in vsya.items():
                vz, m2 = _razrezat_kartinu(
                    moya, lambda z: ((_vremya(z.get("когда"))
                                      or datetime(1970, 1, 1)) < start))
                if _est_li(vz):
                    staroe[sym] = vz
                if _est_li(m2):
                    ost[sym] = m2
            if staroe:
                _atomno(kuda / "картины" / f"архив__{f.name}",
                        json.dumps(staroe, ensure_ascii=False, indent=2))
                _atomno(f, json.dumps(ost, ensure_ascii=False, indent=2))
                out.append(f"архив, картина {f.stem}: в чулан {len(staroe)}")

    # карточки прошлых эпох (прогоны); тетради и картины архива —
    # пересчитываем по тому, что в них осталось
    L = kartochki()
    star = [k for k in L if k.get("вид") == "прогон"
            and int(k.get("эпоха") or 0) < n]
    if star:
        _dopisat(kuda / "карточки.jsonl", star)
        _zapisat_kartochki([k for k in L if k not in star])
        out.append(f"карточек прошлых эпох — в чулан: {len(star)}")
    _obnovit_kartochki_arhiva()
    return out


def _obnovit_kartochki_arhiva():
    """Карточки тетрадей и картин — по тому, что лежит сейчас. Пустое —
    без карточки."""
    zhivye = set()
    if TETRADI.is_dir():
        for f in sorted(TETRADI.glob("*.jsonl")):
            if "__" not in f.stem or not _chitat_jsonl(f):
                continue
            avtor, slot = f.stem.rsplit("__", 1)
            _kartochka_tetradi(avtor, slot, f)
            zhivye.add(f"тетрадь:{avtor}:{slot}")
    if KARTINY.is_dir():
        for f in sorted(KARTINY.glob("*.json")):
            if "__" not in f.stem:
                continue
            try:
                vsya = json.loads(f.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            if not any(_est_li(m) for m in vsya.values()
                       if isinstance(m, dict)):
                continue
            avtor, slot = f.stem.rsplit("__", 1)
            zhivye.add(f"картина:{avtor}:{slot}")
    L = kartochki()
    ostavit = [k for k in L if k.get("вид") == "прогон"
               or k.get("id") in zhivye]
    if len(ostavit) != len(L):
        _zapisat_kartochki(ostavit)


def novaya_epoha(pochemu: str) -> list:
    """Шеф объявил: машина врала. Всё до этой минуты — в чулан."""
    L = epohi()
    n = int(L[-1].get("номер") or 0) + 1
    L.append({"номер": n, "с": datetime.now().strftime("%Y-%m-%d %H:%M"),
              "почему": (pochemu or "").strip() or "объявил Шеф"})
    ARHIV.mkdir(parents=True, exist_ok=True)
    _atomno(EPOHI, json.dumps(L, ensure_ascii=False, indent=2))
    return [f"эпоха {n} началась"] + ubrat_staroe()


# ARHIV_BIRZHI_V1 - marker


# ═══════════════════════════════════════════════════════════════
# ARHIV_RUKI_V1 — достать из архива: трейдеру, Локе, ниточке
# ═══════════════════════════════════════════════════════════════
# Слово Шефа (01.10): чужой опыт житель берёт по просьбе, если своего
# мало, «но не всегда»; перед показом — «это не источник, а опыт».
# Арчи упразднён: архив — код, хранитель на весь город одна — Лока.

_SINONIMY = {
    "фунт": "gbpusd", "gbp": "gbpusd", "евро": "eurusd", "eur": "eurusd",
    "юан": "usdcnh", "cnh": "usdcnh", "золот": "xauusd", "голд": "xauusd",
    "иен": "usdjpy", "йен": "usdjpy", "дневк": "d1", "днев": "d1",
    "недел": "w1", "часов": "h1", "четырехчас": "h4",
    "вход": "enter", "вошл": "enter", "отказ": "wait",
}
_STOP = {"как", "что", "где", "был", "была", "было", "были", "это", "все",
         "всё", "для", "при", "про", "мне", "мои", "мой", "моя", "она",
         "они", "его", "её", "или", "так", "там", "тут", "уже", "еще", "ещё",
         "чем", "кто", "когда", "надо", "можно", "покажи", "найди", "дай",
         "есть"}


_OKONCHANIYA = ("иями", "ями", "ами", "ого", "его", "ому", "ему", "ыми",
                "ими", "ая", "яя", "ые", "ие", "ый", "ий", "ой", "ое", "ее",
                "ую", "юю", "ья", "ьи", "ье", "ов", "ев", "ей", "ам", "ям",
                "ах", "ях", "ом", "ем", "а", "я", "ы", "и", "е", "у", "ю", "о")


def _osnova(s: str) -> str:
    """Грубая основа слова: «пятая», «пятые», «пятой» → «пят»."""
    for ok in _OKONCHANIYA:
        if s.endswith(ok) and len(s) - len(ok) >= 3:
            return s[:-len(ok)]
    return s


def _slova_zaprosa(zapros: str) -> list:
    out = []
    for s in re.split(r"[^\w]+", (zapros or "").lower().replace("ё", "е")):
        if len(s) < 2 or s in _STOP or (len(s) < 3 and not s.isascii()):
            continue
        zamena = next((v for k, v in _SINONIMY.items() if s.startswith(k)), "")
        out.append(zamena or _osnova(s))
    return list(dict.fromkeys(out))


def _ochki(tekst: str, slova: list) -> int:
    t = (tekst or "").lower().replace("ё", "е")
    return sum(1 for s in slova if s in t)


def _nado_ochkov(slova: list) -> int:
    """Одно-два слова — нужны все; больше — две трети."""
    n = len(slova)
    return n if n <= 2 else -(-2 * n // 3)


_KESH_MEST: dict = {}


def _mesta_progona(k: dict) -> list:
    p = KOREN / str(k.get("где") or "") / "места.jsonl"
    try:
        mt = p.stat().st_mtime
    except Exception:
        return []
    kl = str(p)
    if kl in _KESH_MEST and _KESH_MEST[kl][0] == mt:
        return _KESH_MEST[kl][1]
    mesta = []
    for s in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            mesta.append(json.loads(s))
        except Exception:
            continue
    _KESH_MEST[kl] = (mt, mesta)
    return mesta


def _vse_mesta():
    """(карточка, место) по всем прогонам текущей эпохи."""
    n = tekushchaya()["номер"]
    for k in kartochki():
        if k.get("вид") != "прогон" or int(k.get("эпоха") or 0) < n:
            continue
        for m in _mesta_progona(k):
            yield k, m


def _tekst_mesta(m: dict) -> str:
    fi = m.get("фаза_итог") or {}
    return " ".join(str(x or "") for x in (
        m.get("инструмент"), m.get("этаж"), m.get("действие"),
        m.get("вердикт"), m.get("разворотный"), m.get("причина"),
        m.get("сказал"), fi.get("фаза"), fi.get("итог"), fi.get("почему"),
        fi.get("ход"), m.get("кто")))


def _chto_sdelala(m: dict) -> str:
    d = str(m.get("действие") or "").upper()
    c = m.get("цена_входа")
    return {"ENTER": f"вход @ {c}" if c else "вход",
            "WAIT": "не работала", "HOLD": "держала",
            "MOVE_STOP": "перенесла стоп", "CLOSE": "закрыла",
            "ADD": "долила", "MOVE_ORDER": "переставила заявку",
            "CANCEL": "сняла заявку"}.get(d, d.lower() or "без приказа")


def _stroka_mesta(k: dict, m: dict, s_kem: bool = False) -> str:
    fi = m.get("фаза_итог") or {}
    slova = " ".join(str(m.get("сказал") or m.get("причина") or "").split())
    out = (f"· {m.get('когда_на_рынке', '?')} · {m.get('инструмент', '')} "
           f"{m.get('этаж', '')} · {_chto_sdelala(m)}")
    if slova:
        out += f" · «{slova[:220]}{'…' if len(slova) > 220 else ''}»"
    if fi.get("фаза") in ("третья", "четвёртая", "пятая"):
        out += f" · фаза: {fi['фаза']} → {fi.get('итог', '?')}"
    out += f"  [прогон {k.get('когда', '?')}"
    if k.get("итог_R") is not None:
        out += f", итог прогона {k['итог_R']:+.2f}R"
    if s_kem:
        out += f", {m.get('кто', '?')}"
    return out + "]"


def _norm_daty(d) -> str:
    d = str(d or "").strip()
    return d + " 00:00" if len(d) == 10 else d


def iz_arhiva(zapros: str, kto: str, symbol: str = "", bar: str = "",
              slot: str = "") -> str:
    """Рука трейдера. Сперва своё; своего мало — немного чужого,
    раз за место, с предупреждением. По своей паре — только то, что
    на рынке было раньше текущего бара."""
    slova = _slova_zaprosa(zapros)
    if not slova:
        return ("Скажи словами, что ищешь: например «пятая GBPUSD D1», "
                "«край», «свои числа».")
    kto = (kto or "").strip()
    sym = (symbol or "").strip().upper()
    bar_n = _norm_daty(bar)
    nado = _nado_ochkov(slova)

    svoe, chuzhoe = [], []
    for k, m in _vse_mesta():
        if sym and bar_n and str(m.get("инструмент") or "").upper() == sym \
                and _norm_daty(m.get("когда_на_рынке")) >= bar_n:
            continue                       # будущее своей пары — нельзя
        o = _ochki(_tekst_mesta(m), slova)
        if o < nado:
            continue
        kl = (o, str(k.get("когда") or ""), str(m.get("когда_на_рынке") or ""))
        (svoe if kto and str(m.get("кто") or "") == kto else chuzhoe
         ).append((kl, k, m))
    svoe.sort(key=lambda x: x[0], reverse=True)
    chuzhoe.sort(key=lambda x: x[0], reverse=True)

    L = [f"=== ИЗ АРХИВА БИРЖИ · «{zapros}» ==="]
    if svoe:
        L.append(f"ТВОЁ — {len(svoe)} мест(а), показываю до пяти:")
        L += [_stroka_mesta(k, m) for _, k, m in svoe[:5]]
    else:
        L.append("Твоего по этому запросу нет.")
    if len(svoe) >= 3:
        return "\n".join(L)

    if not chuzhoe:
        L.append("Чужого тоже нет. Решай по своему взгляду.")
        return "\n".join(L)
    # «но не всегда»: чужое — раз за место
    try:
        _g = str(_BIRZHA)
        if _g not in _sys.path:
            _sys.path.insert(0, _g)
        from hooks import load_trading_state, save_trading_state
        t = load_trading_state()
        bylo = (t.get("архив_чужое") or {}).get(slot or "?")
        if bar and bylo == bar:
            L.append("Чужое на этом месте ты уже брала — второй раз не дам. "
                     "Решай по своему взгляду.")
            return "\n".join(L)
        t.setdefault("архив_чужое", {})[slot or "?"] = bar
        save_trading_state(t)
    except Exception:
        pass
    imena = sorted({str(m.get("кто") or "?") for _, _, m in chuzhoe[:3]})
    L.append("")
    L.append(f"— — — ЧУЖОЙ ОПЫТ ({', '.join(imena)}) — — —")
    L.append("Это НЕ источник и НЕ правило, а чей-то опыт: как другой "
             "человек прочитал похожее место и что было дальше. Источник — "
             "твои знания. Чужое решение было его, а не твоё: сравни со "
             "своим взглядом, но не бери вместо него.")
    L += [_stroka_mesta(k, m, s_kem=True) for _, k, m in chuzhoe[:3]]
    return "\n".join(L)


def nayti(zapros: str, predel: int = 20) -> list:
    """Для Локи и ниточки: всё подряд, без правила своё/чужое (это
    смотрит Шеф). [{когда, что, откуда, id}]"""
    slova = _slova_zaprosa(zapros)
    if not slova:
        return []
    nado = _nado_ochkov(slova)
    out = []
    for k in kartochki():
        o = _ochki(json.dumps(k, ensure_ascii=False), slova)
        if o >= nado:
            out.append((o + 1, {
                "когда": str(k.get("когда") or ""),
                "что": _kartochka_slovami(k),
                "откуда": f"Архив Биржи · карточка · {k.get('id')}",
                "id": k.get("id")}))
    for k, m in _vse_mesta():
        o = _ochki(_tekst_mesta(m), slova)
        if o >= nado:
            out.append((o, {
                "когда": str(k.get("когда") or ""),
                "что": _stroka_mesta(k, m, s_kem=True),
                "откуда": f"Архив Биржи · {k.get('id')}",
                "id": k.get("id")}))
    out.sort(key=lambda x: (x[0], x[1]["когда"]), reverse=True)
    return [x[1] for x in out[:predel]]


def _kartochka_slovami(k: dict) -> str:
    vid = k.get("вид")
    kto = ", ".join(k.get("кто") or []) or "—"
    mesto = ", ".join(k.get("место") or [])
    para = " ".join((k.get("инструмент") or []) + (k.get("этаж") or []))
    s = f"{vid} · {kto} · {mesto} · {para}"
    if k.get("рынок_с"):
        s += f" · рынок {k['рынок_с']} — {k.get('рынок_по', '')}"
    if vid == "прогон":
        s += (f" · мест {k.get('мест')}, приказов войти {k.get('входов')}, "
              f"сделок {k.get('сделок_закрыто')}")
        if k.get("итог_R") is not None:
            s += f", итог {k['итог_R']:+.2f}R"
        if k.get("фазы"):
            s += " · фазы: " + ", ".join(f"{a} {b}" for a, b in k["фазы"].items())
    elif vid == "тетрадь":
        s += f" · записей {k.get('записей')}, прогонов {k.get('прогонов')}"
    return s + f" · эпоха {k.get('эпоха')}"


def otkryt(id_ili_imya: str) -> str:
    """Открыть карточку: что это, чьё и что внутри (коротко)."""
    q = str(id_ili_imya or "").strip()
    L = kartochki()
    k = next((x for x in L if x.get("id") == q), None) or \
        next((x for x in L if q and q in str(x.get("id") or "")), None)
    if not k:
        return f"Карточки «{q}» в Архиве Биржи нет."
    out = ["=== " + _kartochka_slovami(k) + " ===",
           f"лежит: {k.get('где')}"]
    if k.get("вид") == "прогон":
        mesta = _mesta_progona(k)
        sch: dict = {}
        for m in mesta:
            d = _chto_sdelala(m).split(" @")[0]
            sch[d] = sch.get(d, 0) + 1
        out.append("что делала: " + ", ".join(
            f"{a} — {b}" for a, b in sorted(sch.items(), key=lambda x: -x[1])))
        vhody = [m for m in mesta
                 if str(m.get("действие") or "").upper() == "ENTER"]
        if vhody:
            out.append(f"входы (до 12 из {len(vhody)}):")
            out += [_stroka_mesta(k, m) for m in vhody[:12]]
    elif k.get("вид") == "тетрадь":
        zap = _chitat_jsonl(KOREN / str(k.get("где") or ""))
        out.append(f"последние записи (до 10 из {len(zap)}):")
        for z in zap[-10:]:
            out.append(f"· {z.get('bar_time', '?')} · {z.get('symbol', '')} "
                       f"{z.get('timeframe', '')} · {z.get('что') or z.get('verdict') or ''}"
                       f" · {str(z.get('почему') or z.get('action') or '')[:160]}")
    return "\n".join(out)


def svodka() -> str:
    """Что лежит в архиве — для Шефа и Локи."""
    L = kartochki()
    out = ["=== АРХИВ БИРЖИ ==="]
    for e in epohi():
        out.append(f"эпоха {e.get('номер')} — с {e.get('с')}: {e.get('почему')}")
    po_vidu: dict = {}
    for k in L:
        po_vidu[k.get("вид")] = po_vidu.get(k.get("вид"), 0) + 1
    out.append("карточек: " + (", ".join(f"{a} {b}" for a, b in po_vidu.items())
                               or "пока нет"))
    po_lyudyam: dict = {}
    for k in L:
        if k.get("вид") != "прогон":
            continue
        for kto in k.get("кто") or ["?"]:
            d = po_lyudyam.setdefault(kto, {"прогонов": 0, "R": 0.0})
            d["прогонов"] += 1
            d["R"] += float(k.get("итог_R") or 0)
    for kto, d in po_lyudyam.items():
        out.append(f"{kto}: прогонов {d['прогонов']}, сумма итогов {d['R']:+.2f}R")
    return "\n".join(out)


# ── из мозга Арчи: проверка журнала сделок (код, без модели) ──
def proverit_zhurnal_sdelok() -> str:
    """Дубли сделок и расхождения R в журнале закрытий. Ничего не меняет."""
    p = DANNYE / "trading_pnl.jsonl"
    if not p.exists():
        return "Журнала закрытий нет."
    vsego = bityh = 0
    po_klyuchu: dict = {}
    for s in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = s.strip()
        if not s:
            continue
        vsego += 1
        try:
            z = json.loads(s)
        except Exception:
            bityh += 1
            continue
        if z.get("pnl_r") is None and z.get("pnl") is None:
            continue
        kl = (z.get("symbol"), z.get("timeframe"), z.get("trader"),
              z.get("opened_at"))
        po_klyuchu.setdefault(kl, []).append(z)
    dubli = {k: v for k, v in po_klyuchu.items() if len(v) > 1}
    rashozh = sum(1 for v in dubli.values()
                  if len({x.get("pnl_r") for x in v}) > 1)
    return (f"Журнал закрытий: строк {vsego}, битых {bityh}, сделок "
            f"{len(po_klyuchu)}, повторов {len(dubli)}"
            + (f", из них с разным R — {rashozh}" if rashozh else "") + ".")


# ── уборка по эпохам: и старые копии склада (Атлас) ──
_ubrat_staroe_osnova = ubrat_staroe


def ubrat_staroe() -> list:   # noqa: F811 — дополняем, не заменяем
    out = _ubrat_staroe_osnova()
    try:
        start = nachalo()
        kuda = CHULAN / f"до_эпохи_{tekushchaya()['номер']}" / "атлас"
        ushlo = 0
        for f in sorted(DANNYE.glob("atlas_trading_archive_*.jsonl")) \
                if DANNYE.is_dir() else []:
            t = _iz_imeni(f.name)
            if t and t < start:
                kuda.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(kuda / f.name))
                ushlo += 1
        if ushlo:
            out.append(f"старые копии Атласа: в чулан {ushlo}")
    except Exception as e:
        out.append(f"Атлас не разобран ({e})")
    return out


# ARHIV_RUKI_V1 - marker
