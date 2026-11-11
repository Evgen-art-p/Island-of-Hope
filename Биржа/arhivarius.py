# -*- coding: utf-8 -*-
# ARHIVARIUS_V1
# ARHIVARIUS_V2
"""
АРХИВАРИУС БИРЖИ — разбор прогонов в картотеку жителей (27.10, V2).

СЛОВО ШЕФА 27.10
    «Просеивать прогоны и писать в картотеку про жителя не то, какой он
    красивый, а те вопросы, что нам нужны; места, особые случаи, ситуации.»
    «Вакансия, картридж, слот; числа скрипт считает.»

ЧЕТЫРЕ ПРАВИЛА (София, 27.10 — Шеф: «делай»)
    1. Сводка — только из записанного городом. У каждого факта номер, прогон
       и бар (или список фактов, из которых он сложен). Чего город не
       записал — так и сказано («не записано»), скрипт не додумывает.
    2. Архивариус толкует факты своими словами; новых правил торговли не
       вводит, историю не меняет.
    3. Проверка машинная — по утверждению: во фразе с числом или датой должна
       стоять ссылка на факт [Ф…], и каждое её число и каждая дата должны
       быть в этом факте. Иначе строка помечается «⚠ не из сводки» — молча
       ничего не исправляется.
    4. Картотека — развивающийся разбор жителя, свежее сверху. Архив Биржи
       (отдельные случаи для трейдеров) — следующий шаг, не здесь.
    Сравнение с прошлым прогоном говорит, ЧТО изменилось: условия (период,
    мест), состав записанных фактов, решения на одинаковых местах, результат.
    Разные условия — без «лучше/хуже».

Только пишет: на торговлю и решения не влияет, трейдерам ничего не подкладывает.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
_REPO = _BIRZHA.parent
GOROD = _REPO / "GRONDHEIM_CITY"
CEHA = GOROD / "Биржа" / "цеха"
KARTOTEKA = GOROD / "Биржа" / "картотека" / "разборы"
CEH_A, SLOT_A = "контора", "архивариус"
for _p in (str(_BIRZHA), str(_REPO / "ГОРОД")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

NOL = 0.005
_DATA = re.compile(r"\d{4}\.\d{2}(?:\.\d{2})?")
_CHISLO = re.compile(r"\d+(?:[.,]\d+)?")
_SSYLKA = re.compile(r"\[([ФСУ]\d+)\]")


# ── мелочи ───────────────────────────────────────────────────────
def _jl(f) -> list:
    out = []
    try:
        for ln in Path(f).read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _f(x):
    try:
        return float(str(x).replace("−", "-").replace(",", ".").replace("+", "").strip())
    except Exception:
        return None


def _r(x) -> str:
    return f"{x:+.2f}R".replace("-", "−")


def _imya_mesta(ceh, slot) -> str:
    try:
        from cartridge_registry import resolve_para
        return str((resolve_para(ceh, slot) or {}).get("имя") or "")
    except Exception:
        return ""


_SLOVA_CHISLA = (
    (r"дв(?:а|е|ух|ум|умя)", "2"), (r"тр(?:и|[её]х|[её]м|емя)", "3"),
    (r"четыр(?:е|[её]х|[её]м|ьмя)", "4"), (r"пят(?:ь|и|ью)", "5"),
    (r"шест(?:ь|и|ью)", "6"), (r"сем(?:ь|и|ью)", "7"), (r"восьм(?:и|ью)|восемь", "8"),
    (r"девят(?:ь|и|ью)", "9"), (r"десят(?:ь|и|ью)", "10"),
)


def _razbor_teksta(t: str):
    """(даты, числа) утверждения: даты отдельно, числа — без дат и номеров фактов.
    Числа словами («четыре стопа») считаются числами."""
    t = _SSYLKA.sub(" ", str(t or ""))
    t = re.sub(r"[ФСУ]\d+", " ", t)
    for _sl, _ch in _SLOVA_CHISLA:
        t = re.sub(r"(?i)\b(?:" + _sl + r")\b", f" {_ch} ", t)
    daty = set(_DATA.findall(t))
    t = _DATA.sub(" ", t)
    t = re.sub(r"^\s*\d+[.)]\s", " ", t)            # «1) …», «2. …» в начале
    chisla = set()
    for m in _CHISLO.findall(t.replace("−", "-")):
        v = _f(m)
        if v is not None:
            chisla.add(round(abs(v), 2))
    return daty, chisla


# ── что записал город ────────────────────────────────────────────
_ZH_BEDA = {}   # A07_NOMER_GORODA_V1: (цех, место, прогон) → почему журнал не дал сделок


def _zhurnal(ceh, slot, run_id) -> list:
    _ZH_BEDA.pop((ceh, slot, run_id), None)
    try:
        import schet as _sch
        a, b = _sch._okno_progona(ceh, run_id)
        if not a:
            _ZH_BEDA[(ceh, slot, run_id)] = f"прогон {run_id} не найден среди прогонов цеха {ceh}"
            return []
        if _sch._nomer(ceh, slot) is None:
            _ZH_BEDA[(ceh, slot, run_id)] = f"у места {slot} нет номера счёта"
            return []
        return _sch._zapisi(ceh, slot, a, b)
    except Exception as e:
        print(f"[АРХИВАРИУС] журнал не прочёлся ({e})")
        _ZH_BEDA[(ceh, slot, run_id)] = f"журнал города не прочёлся ({e})"
        return []


def _zakryto_v_otchete(papka):
    """Сколько сделок закрыто по отчёту прогона (на все места); None — отчёта нет."""
    try:
        t = (Path(papka) / "отчёт.md").read_text(encoding="utf-8")
    except Exception:
        return None
    m = re.search(r"\|\s*сделок закрыто\s*\|\s*(\d+)\s*\|", t)
    return int(m.group(1)) if m else 0


def _net_sdelok_pochemu(papka, ceh, slot, run) -> tuple:
    """(код, факт), когда по номеру места в журнале сделок нет.
    Ноль — только когда и журнал, и отчёт говорят «нет»."""
    beda = _ZH_BEDA.get((ceh, slot, run))
    if beda:
        return "журнал", f"ДАННЫХ НЕТ: {beda} — были ли сделки, неизвестно; это не ноль"
    n = _zakryto_v_otchete(papka)
    if n is None:
        return "нет отчёта", ("отчёт прогона не найден, по номеру места в журнале сделок нет — "
                              "были ли сделки, неизвестно; это не ноль")
    if n <= 0:
        return "нет", "закрытых сделок в прогоне нет (и в журнале, и в отчёте)"
    try:
        import schet as _sch
        nom = _sch._nomer(ceh, slot)
    except Exception:
        nom = None
    odin = len({z.get("слот") for z in _jl(Path(papka) / "места.jsonl")} - {None}) <= 1
    if odin:
        return "не дошли", (f"ДАННЫЕ НЕ ДОШЛИ: в отчёте прогона закрыто сделок {n}, а в журнале "
                            f"города под номером места {nom or '—'} ни одной — сделки этого "
                            "прогона разобрать нельзя; это не ноль")
    return "не ясно", (f"в отчёте прогона закрыто сделок {n} на все места, у этого места под "
                       f"номером {nom or '—'} в журнале ни одной — если у него были сделки, "
                       "данные не дошли")




def _tablica(t: str, zagolovok: str) -> list:
    i = t.find(zagolovok)
    if i < 0:
        return []
    rows = []
    for ln in t[i:].splitlines()[1:]:
        if ln.startswith("#"):
            break
        if ln.startswith("|") and not set(ln) <= set("|-: "):
            rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return rows[1:] if rows else []


def _iz_otcheta(papka: Path) -> dict:
    try:
        t = (papka / "отчёт.md").read_text(encoding="utf-8")
    except Exception:
        return {"есть": False, "книга": [], "ведение": []}
    kniga = []
    for c in _tablica(t, "### Книга места"):
        if len(c) >= 6 and _DATA.match(c[0]):
            kak = ("стоп" if " стоп " in f" {c[2]} " or "стоп @" in c[2]
                   else "закрыл сам" if "закрыл сам" in c[2] else "")
            kniga.append({"вход": c[0], "сторона": c[1],
                          "закрыта": (_DATA.findall(c[2]) or [""])[0], "как": kak,
                          "R": _f(c[3]), "тень": c[4],
                          "тень_когда": (_DATA.findall(c[4]) or [""])[0], "R_тени": _f(c[5])})
    ved = []
    for c in _tablica(t, "## Ведение сделок"):
        if len(c) >= 4 and c[1] == "CLOSE":
            ved.append({"бар": c[0], "R": _f(c[2]), "лучшее": _f(c[3])})
    return {"есть": True, "книга": kniga, "ведение": ved}


def _log(papka: Path) -> str:
    try:
        return (papka / "лог.txt").read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _konec_hoda(log: str, slot: str, tri: list) -> tuple:
    """(записывал ли город, где держал при диверe на конце хода)."""
    zapisan = f"[КОНЕЦ ХОДА] {slot} " in log
    out, posl, k = [], None, 0
    for ln in log.splitlines():
        m = re.search(r"\[КОНЕЦ ХОДА\] (\S+) (LONG|SHORT) \S+: дивер на конце хода — (\S+)", ln)
        if m and m.group(1) == slot:
            posl = (m.group(2), m.group(3))
            continue
        m = re.search(r"\[ТРИ СЛОВА\] (\S+) (HOLD|CLOSE|ADD):", ln)
        if m and m.group(1) == slot and "✗" not in ln:
            zap = tri[k] if k < len(tri) else {}
            k += 1
            if posl and posl[1] == "ЕСТЬ" and m.group(2) == "HOLD" and zap.get("бар"):
                out.append({"бар": zap["бар"], "сторона": posl[0], "слово": zap.get("слово") or ""})
            posl = None
    return zapisan, out


# ── сводка: пронумерованные факты ────────────────────────────────
class _Fakty:
    def __init__(self):
        self.spisok = []

    def dob(self, bukva: str, tekst: str) -> str:
        n = sum(1 for x in self.spisok if x["id"].startswith(bukva)) + 1
        fid = f"{bukva}{n}"
        daty, chisla = _razbor_teksta(tekst)
        self.spisok.append({"id": fid, "текст": tekst, "даты": daty, "числа": chisla})
        return fid

    def tekst(self) -> str:
        return "\n".join(f"[{x['id']}] {x['текст']}" for x in self.spisok)

    def po_id(self) -> dict:
        return {x["id"]: x for x in self.spisok}


def svodka(papka, ceh: str, slot: str, proshlaya: dict | None) -> tuple:
    """(факты, запись для сравнения в следующий раз)."""
    papka = Path(papka)
    run = papka.name
    F = _Fakty()
    mesta = [z for z in _jl(papka / "места.jsonl") if z.get("слот") == slot]
    daty = sorted(str(z.get("когда_на_рынке") or "") for z in mesta if z.get("когда_на_рынке"))
    tri = [z for z in _jl(CEHA / ceh / "слоты" / slot / "данные" / "три_слова.jsonl")
           if z.get("прогон") == run]
    ot = _iz_otcheta(papka)
    odin_slot = len({z.get("слот") for z in _jl(papka / "места.jsonl")} - {None}) <= 1
    log = _log(papka)
    kh_zapisan, kh = _konec_hoda(log, slot, tri)

    # условия и состав записанного
    period = f"{daty[0]}–{daty[-1]}" if daty else "не записан"
    F.dob("У", f"прогон {run}: место {ceh}/{slot}, мест пройдено {len(mesta)}, период {period}")
    zapisano = {"слово места и месяц (три слова)": bool(tri),
                "книга места и тень (отчёт)": bool(ot["книга"]) and odin_slot,
                "ведение: лучшее в сделке (отчёт)": bool(ot["ведение"]),
                "дивер на конце хода (лог)": kh_zapisan}
    F.dob("У", "город записывал: " + ("; ".join(k for k, v in zapisano.items() if v) or "—")
          + " · не записывал: " + ("; ".join(k for k, v in zapisano.items() if not v) or "—"))

    # сделки
    mesto_po_cene = {}
    for z in tri:
        try:
            mesto_po_cene.setdefault(round(float(str(z.get("сделка")).split("|")[1]), 5),
                                     (z.get("слово") or "", z.get("бар") or ""))
        except Exception:
            continue
    kniga_po_vhodu = {k["вход"]: k for k in ot["книга"]} if odin_slot else {}
    sd = {}
    for z in _zhurnal(ceh, slot, run):
        k = (str(z.get("opened_at") or "")[:10], round(_f(z.get("entry")) or 0, 5))
        s = sd.setdefault(k, {"вход": k[0], "цена": k[1], "R": 0.0, "закрыта": "",
                              "причина": ""})
        s["R"] += _f(z.get("pnl_r")) or 0.0
        s["закрыта"] = str(z.get("closed_at") or "")[:10]
        s["причина"] = str(z.get("close_reason") or "") or s["причина"]
    sdelki = sorted(sd.values(), key=lambda s: (s["закрыта"], s["вход"]))
    po_mestam, f_sd = {}, []
    for s in sdelki:
        kn = kniga_po_vhodu.get(s["вход"])
        if kn and kn["как"]:
            s["как"] = kn["как"]
        elif s["причина"]:
            s["как"] = "стоп" if "STOP" in s["причина"].upper() else s["причина"].lower()
        else:
            s["как"] = ""
        sl, sbar = mesto_po_cene.get(s["цена"], ("", ""))
        s["место"] = sl
        fid = F.dob("Ф", f"сделка {s['вход']} @ {s['цена']} → закрыта {s['закрыта'] or 'не записано'}: "
                    f"{_r(s['R'])}; как закрыта: {s['как'] or 'не записано'}; место: "
                    + (f"«{sl}» (его слово на баре {sbar})" if sl else "не записано"))
        s["факт"] = fid
        f_sd.append(fid)
        g = po_mestam.setdefault(sl or "не записано", {"сделок": 0, "R": 0.0, "плюс": 0, "факты": []})
        g["сделок"] += 1
        g["R"] += s["R"]
        g["плюс"] += 1 if s["R"] > NOL else 0
        g["факты"].append(fid)
    itog = sum(s["R"] for s in sdelki)
    _dannye = ("есть", "")   # A07_NOMER_GORODA_V1
    if sdelki:
        F.dob("Ф", f"итог прогона: сделок {len(sdelki)}, в плюс "
              f"{sum(1 for s in sdelki if s['R'] > NOL)}, итог {_r(itog)} (из {', '.join(f_sd)})")
    else:
        _dannye = _net_sdelok_pochemu(papka, ceh, slot, run)   # A07_NOMER_GORODA_V1
        F.dob("Ф", _dannye[1])
    for m_, g in sorted(po_mestam.items()):
        F.dob("Ф", f"место «{m_}»: сделок {g['сделок']}, в плюс {g['плюс']}, итог {_r(g['R'])} "
              f"(из {', '.join(g['факты'])})")

    # слово места против города
    s_gor = [z for z in tri if z.get("город")]
    sovp = [z for z in s_gor if z.get("слово") == z.get("город")]
    if s_gor:
        F.dob("Ф", f"слово места совпало с городом в {len(sovp)} из {len(s_gor)} решений в сделке "
              f"(бары {s_gor[0].get('бар')}–{s_gor[-1].get('бар')})")
    for z in [z for z in s_gor if z.get("слово") != z.get("город")][:5]:
        F.dob("Ф", f"{z.get('бар')} {z.get('что')}: его слово «{z.get('слово')}», город "
              f"«{z.get('город')}»; месяц его словами: {str(z.get('месяц') or '')[:160]}")

    # ведение: отдал от лучшего
    for v in ot["ведение"]:
        if v["R"] is not None and v["лучшее"] is not None:
            F.dob("Ф", f"{v['бар']} CLOSE: закрыл на {_r(v['R'])}, лучшее в сделке было "
                  f"{_r(v['лучшее'])}, разница {(v['лучшее'] - v['R']):.2f}R")

    # особые случаи — только записанное
    osob = 0
    for k in (ot["книга"] if odin_slot else []):
        if (k["R_тени"] is not None and k["R"] is not None and "три условия" in k["тень"]
                and k["тень_когда"] and k["закрыта"] and k["тень_когда"] < k["закрыта"]):
            F.dob("Ф", f"ОСОБЫЙ СЛУЧАЙ: сделка {k['вход']} {k['сторона']} — город-тень вышел по "
                  f"трём условиям {k['тень_когда']} на {_r(k['R_тени'])}, он закрыл "
                  f"{k['закрыта']} на {_r(k['R'])}")
            osob += 1
    for d in kh[:5]:
        F.dob("Ф", f"ОСОБЫЙ СЛУЧАЙ: {d['бар']} город записал дивер на конце его хода "
              f"({d['сторона']}) — ЕСТЬ, его решение HOLD, место «{d['слово']}»")
        osob += 1
    tek = []
    for s in sdelki + [None]:
        if s and s["как"] == "стоп":
            tek.append(s)
            continue
        if len(tek) >= 3:
            F.dob("Ф", f"ОСОБЫЙ СЛУЧАЙ: стопов подряд {len(tek)} — сделки "
                  f"{tek[0]['вход']}–{tek[-1]['вход']} ({', '.join(x['факт'] for x in tek)})")
            osob += 1
        tek = []

    zap = {"прогон": run, "цех": ceh, "слот": slot, "период": period, "мест": len(mesta),
           "записано": [k for k, v in zapisano.items() if v], "сделок": len(sdelki),
           "итог_R": round(itog, 2), "совпало": len(sovp), "с_городом": len(s_gor),
           "по_местам": {k: {"сделок": v["сделок"], "R": round(v["R"], 2)}
                         for k, v in po_mestam.items()}, "особых": osob}
    zap["данные"] = _dannye[0]   # A07_NOMER_GORODA_V1: «нет» — ноль; остальное — не ноль

    # сравнение: что изменилось
    if proshlaya:
        p = proshlaya
        odni = p.get("период") == period
        F.dob("С", f"прошлый разобранный прогон {p.get('прогон')}: период {p.get('период')}, "
              f"мест {p.get('мест')}; этот: период {period}, мест {len(mesta)} — "
              + ("условия те же (тот же период)" if odni
                 else "условия разные: другой период рынка, разница результата может быть от рынка"))
        bylo, stalo = set(p.get("записано") or []), set(zap["записано"])
        if bylo != stalo:
            F.dob("С", "состав записанного изменился: "
                  + ("появилось: " + "; ".join(sorted(stalo - bylo)) if stalo - bylo else "")
                  + (" · пропало: " + "; ".join(sorted(bylo - stalo)) if bylo - stalo else "")
                  + " — сравнивать эти части нельзя")
        for m_ in sorted(set(p.get("по_местам") or {}) | set(zap["по_местам"])):
            a = (p.get("по_местам") or {}).get(m_)
            b = zap["по_местам"].get(m_)
            F.dob("С", f"место «{m_}»: тогда "
                  + (f"сделок {a['сделок']}, итог {_r(a['R'])}" if a else "сделок не было")
                  + "; сейчас " + (f"сделок {b['сделок']}, итог {_r(b['R'])}" if b else "сделок нет"))
        if p.get("с_городом") or zap["с_городом"]:
            F.dob("С", f"совпадение слова места с городом: тогда {p.get('совпало', 0)} из "
                  f"{p.get('с_городом', 0)}, сейчас {len(sovp)} из {len(s_gor)}")
        F.dob("С", f"результат: тогда сделок {p.get('сделок')}, итог {_r(p.get('итог_R') or 0)}; "
              f"сейчас сделок {len(sdelki)}, итог {_r(itog)}")
        zap["условия_те_же"] = odni
    return F, zap


# ── проверка: по утверждению ─────────────────────────────────────
def proverit(tekst: str, F: _Fakty) -> tuple:
    """Каждая строка с числом или датой: есть ссылка на факт, и все её числа и
    даты — в этих фактах. Иначе пометка; текст не правится."""
    po = F.po_id()
    out, plohih = [], 0
    for ln in str(tekst or "").splitlines():
        daty, chisla = _razbor_teksta(ln)
        if not daty and not chisla:
            out.append(ln)
            continue
        ssylki = _SSYLKA.findall(ln)
        bez = [s for s in ssylki if s not in po]
        if not ssylki:
            out.append(ln.rstrip() + "  ⚠ не из сводки: нет ссылки на факт")
            plohih += 1
            continue
        d_ok = set().union(*(po[s]["даты"] for s in ssylki if s in po))
        c_ok = set().union(*(po[s]["числа"] for s in ssylki if s in po))
        lishnie = sorted(daty - d_ok) + [f"{c:g}" for c in sorted(chisla - c_ok)]
        if bez or lishnie:
            pr = []
            if bez:
                pr.append("нет таких фактов: " + ", ".join(bez))
            if lishnie:
                pr.append("нет в " + ", ".join(ssylki) + ": " + ", ".join(lishnie))
            out.append(ln.rstrip() + "  ⚠ не из сводки: " + "; ".join(pr))
            plohih += 1
        else:
            out.append(ln)
    return "\n".join(out), plohih


# ── архивариус ───────────────────────────────────────────────────
def kto_arhivarius() -> dict | None:
    try:
        from cartridge_registry import resolve_para
        return resolve_para(CEH_A, SLOT_A)
    except Exception:
        return None


def _rol() -> str:
    try:
        return (CEHA / CEH_A / "слоты" / SLOT_A / "промпт.md").read_text(encoding="utf-8")
    except Exception:
        return ""


def razbor_arhivariusa(imya_zhitelya: str, F: _Fakty, te_zhe: bool | None) -> tuple:
    n = kto_arhivarius()
    if not n:
        return "", ""
    try:
        import rezidenty as _rz
        p = json.loads((Path(n["папка"]) / "passport.json").read_text(encoding="utf-8"))
        dusha = _rz.sobrat_dushu(p)
    except Exception:
        dusha = f"Ты — {n.get('имя')}, житель Грондхейма. Говоришь от первого лица."
    sravn = ("" if te_zhe is None else
             "Условия прошлого и этого прогона те же — можно сказать, лучше или хуже.\n"
             if te_zhe else
             "Условия прошлого и этого прогона РАЗНЫЕ — не пиши «стал лучше/хуже», "
             "пиши, что именно отличается.\n")
    user = (f"Разбери работу трейдера {imya_zhitelya} по фактам города.\n\n"
            f"ФАКТЫ ГОРОДА:\n{F.tekst()}\n\n"
            "Напиши для Шефа и Брата, коротко, по делу, каждая мысль с новой строки:\n"
            "1) что у него повторяется — хорошее и плохое;\n"
            "2) что изменилось с прошлого разобранного прогона (если он есть);\n"
            "3) два-три особых случая — бар, что было, чем кончилось;\n"
            "4) если в фактах есть [И…] — два-три предложения «Для инвестора»: что изменилось в метриках серии с этим прогоном и можно ли этому доверять (сколько сделок, держится ли результат без трёх лучших).\n"
            + sravn +
            "В КАЖДОЙ строке, где есть число или дата, в конце поставь номер факта, "
            "откуда они, например [Ф7] или [Ф3][С2]. Числа и даты — только из этих "
            "фактов. Только работа: ни характера, ни похвал, ни новых правил торговли.")
    try:
        import llm as _llm
        t = _llm.chat(dusha + "\n\n" + _rol(), user, agent_id=n.get("имя") or "архивариус",
                      slot_id="arhivarius", temperature=0.3)
    except Exception as e:
        print(f"[АРХИВАРИУС] модель не ответила ({e})")
        return n.get("имя") or "", ""
    return n.get("имя") or "", str(t or "").strip()


# ── картотека ────────────────────────────────────────────────────
def _proshlaya(imya: str, slot: str) -> dict | None:
    rr = [r for r in _jl(KARTOTEKA / f"{imya}.jsonl") if r.get("слот") == slot
          and r.get("данные", "есть") in ("есть", "нет")]   # A07_NOMER_GORODA_V1: без данных — не мерка
    return rr[-1] if rr else None


def zapisat(imya: str, zap: dict, F: _Fakty, kto: str, tekst: str, plohih: int):
    KARTOTEKA.mkdir(parents=True, exist_ok=True)
    zap = dict(zap, когда=datetime.now().isoformat(timespec="seconds"), архивариус=kto,
               не_из_сводки=plohih)
    with open(KARTOTEKA / f"{imya}.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(zap, ensure_ascii=False) + "\n")
    blok = [f"## Прогон {zap['прогон']} · {zap['цех']}/{zap['слот']} · период {zap['период']}", "",
            "### Факты города", "", "```", F.tekst(), "```", ""]
    if tekst:
        blok += [f"### Разбор архивариуса ({kto})"
                 + (f" · строк не из сводки: {plohih}" if plohih else " · все строки подтверждены"),
                 "", tekst, ""]
    else:
        blok += ["*Место архивариуса свободно — здесь только факты города.*" if not kto
                 else f"*Архивариус {kto} в этот раз не ответил.*", ""]
    f = KARTOTEKA / f"{imya}.md"
    staroe = ""
    try:
        staroe = f.read_text(encoding="utf-8")
    except Exception:
        pass
    if staroe.startswith("# Картотека"):
        i = staroe.find("\n## ")
        staroe = staroe[i + 1:] if i >= 0 else ""
    f.write_text(f"# Картотека · {imya}\n\nРазборы прогонов, свежее сверху. Каждое число — "
                 "из фактов города; [Ф…] — номер факта, [С…] — сравнение, [У…] — условия.\n\n"
                 + "\n".join(blok) + "\n" + staroe, encoding="utf-8")


def razobrat_progon(papka, ceh: str = "") -> list:
    papka = Path(papka)
    if not ceh:
        ceh = papka.parent.parent.name if papka.parent.name == "прогоны" else ""
    sloty = sorted({z.get("слот") for z in _jl(papka / "места.jsonl")} - {None})
    out = []
    for sl in sloty:
        try:
            imya = _imya_mesta(ceh, sl) or sl
            if any(r.get("прогон") == papka.name and r.get("слот") == sl
                   for r in _jl(KARTOTEKA / f"{imya}.jsonl")):
                out.append(f"картотека {imya}: прогон {papka.name} уже разобран")
                continue
            pr = _proshlaya(imya, sl)
            F, zap = svodka(papka, ceh, sl, pr)
            kto, t = razbor_arhivariusa(imya, F, zap.get("условия_те_же") if pr else None)
            t, plohih = proverit(t, F) if t else ("", 0)
            zapisat(imya, zap, F, kto, t, plohih)
            out.append(f"картотека {imya}: фактов {len(F.spisok)}, сделок {zap['сделок']}, "
                       f"{_r(zap['итог_R'])}" + (f", разбор {kto}" if t else ", только факты")
                       + (f" (⚠ {plohih} строк не из сводки)" if plohih else ""))
            print(f"[АРХИВАРИУС] {out[-1]}")
        except Exception as e:
            out.append(f"картотека {sl}: не легла — {e}")
    return out


# ARHIVARIUS_V1 - marker
# ARHIVARIUS_V2 - marker


# ══ ARHIVARIUS_V3 — архивариус на посту как все: душа поста и петля опыта ══
# Слово Шефа 27.10: «опыт, петля — всё как полагается». Разбор — эпизод его
# работы: ситуация — прогон и сводка, результат — что город подтвердил в его
# строках. Осмысление ложится на полку этой работы; на следующем разборе его
# осмысления лежат перед ним (как у Ректора и Хранителя).
POST_ID = "контора__архивариус"


def _dusha_posta(imya_zhitelya: str):
    try:
        import rezidenty as _rz
        try:
            import osmyslenie as _om
            _om.KLYUCHI_SEYCHAS[POST_ID] = ["разбор", str(imya_zhitelya or "").lower()]
        except Exception:
            pass
        p, dom = _rz.lichnost_na_postu(POST_ID)
        if p:
            return _rz.sobrat_dushu(p), str(p.get("Official_Name") or ""), dom
    except Exception as e:
        print(f"[АРХИВАРИУС] душа поста не собралась ({e})")
    return "", "", None


def razbor_arhivariusa(imya_zhitelya: str, F, te_zhe) -> tuple:   # noqa: F811
    dusha, kto, _dom = _dusha_posta(imya_zhitelya)
    if not dusha:
        return "", ""
    sravn = ("" if te_zhe is None else
             "Условия прошлого и этого прогона те же — можно сказать, лучше или хуже.\n"
             if te_zhe else
             "Условия прошлого и этого прогона РАЗНЫЕ — не пиши «стал лучше/хуже», "
             "пиши, что именно отличается.\n")
    user = (f"Разбери работу трейдера {imya_zhitelya} по фактам города.\n\n"
            f"ФАКТЫ ГОРОДА:\n{F.tekst()}\n\n"
            "Напиши для Шефа и Брата, коротко, по делу, каждая мысль с новой строки:\n"
            "1) что у него повторяется — хорошее и плохое;\n"
            "2) что изменилось с прошлого разобранного прогона (если он есть);\n"
            "3) два-три особых случая — бар, что было, чем кончилось;\n"
            "4) если в фактах есть [И…] — два-три предложения «Для инвестора»: что изменилось в метриках серии с этим прогоном и можно ли этому доверять (сколько сделок, держится ли результат без трёх лучших).\n"
            + sravn +
            "В КАЖДОЙ строке, где есть число или дата, в конце поставь номер факта, "
            "откуда они, например [Ф7] или [Ф3][С2]. Числа и даты — только из этих "
            "фактов. Только работа: ни характера, ни похвал, ни новых правил торговли.")
    try:
        import llm as _llm
        t = _llm.chat(dusha + "\n\n" + _rol(), user, agent_id=kto or "архивариус",
                      slot_id="arhivarius", temperature=0.3)
    except Exception as e:
        print(f"[АРХИВАРИУС] модель не ответила ({e})")
        return kto, ""
    return kto, str(t or "").strip()


_zapisat_do_petli = zapisat


def zapisat(imya, zap, F, kto, tekst, plohih):   # noqa: F811
    _zapisat_do_petli(imya, zap, F, kto, tekst, plohih)
    if not (kto and tekst):
        return
    try:
        import rezidenty as _rz
        import osmyslenie as _om
        dom = _rz.dom_zhitelya(kto)
        if dom is None:
            return
        vsego = sum(1 for ln in tekst.splitlines()
                    if _razbor_teksta(ln)[0] or _razbor_teksta(ln)[1])
        plohie = [ln.split("  ⚠", 1)[0].strip() for ln in tekst.splitlines() if "⚠ не из сводки" in ln]
        sit = (f"Разбор прогона {zap.get('прогон')} трейдера {imya} "
               f"({zap.get('цех')}/{zap.get('слот')}, период {zap.get('период')}): "
               f"фактов {len(F.spisok)}, сделок {zap.get('сделок')}.")
        rez = (f"Город проверил мои строки с числами: подтверждено {vsego - plohih} из {vsego}."
               + ("" if not plohie else " Не из сводки: " + " | ".join(plohie[:3])))
        _om.osmyslit(dom, POST_ID, sit, rez,
                     ["разбор", str(imya).lower(), "не из сводки" if plohih else "подтверждено"],
                     progon=str(zap.get("прогон") or ""), nazvanie_raboty="архивариус биржи")
    except Exception as e:
        print(f"[ОСМЫСЛЕНИЕ] разбор архивариуса не лёг в эпизод ({e})")


# ARHIVARIUS_V3 - marker


# ══ ARCHI_V_KARTOTEKU_V1 — после разбора страница картотеки пересобирается сама ══
_razobrat_progon_do_kartoteki = razobrat_progon


def razobrat_progon(papka, ceh: str = "") -> list:   # noqa: F811
    out = _razobrat_progon_do_kartoteki(papka, ceh)
    try:
        import importlib
        import kartoteka_sbor as _ks
        importlib.reload(_ks)
        _ks.sobrat()
        print("[АРХИВАРИУС] страница картотеки пересобрана")
    except Exception as e:
        print(f"[АРХИВАРИУС] картотека не пересобралась ({e}) — соберётся кнопкой")
    return out


# ARCHI_V_KARTOTEKU_V1 - marker


# A07_NOMER_GORODA_V1 - marker


# ══ METRIKI_INVESTORA_V1 — Арчи: метрики серии до и после прогона ══
# Считает город (metriki_investora), Арчи только объясняет: факты [И…].
_svodka_do_metrik = svodka


def svodka(papka, ceh: str, slot: str, proshlaya: dict | None) -> tuple:   # noqa: F811
    F, zap = _svodka_do_metrik(papka, ceh, slot, proshlaya)
    try:
        import importlib
        import metriki_investora as _mi
        importlib.reload(_mi)
        for s in _mi.dlya_arhivariusa(ceh, slot, Path(papka).name):
            F.dob("И", s)
    except Exception as e:
        print(f"[АРХИВАРИУС] метрики серии не легли в факты ({e})")
    return F, zap


# METRIKI_INVESTORA_V1 - marker
