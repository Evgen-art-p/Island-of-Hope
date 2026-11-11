# -*- coding: utf-8 -*-
# OPYT_STOLA_V1
"""
СТОЛ ОПЫТА ТРЕЙДЕРА — камень №1 из ЧЕРТЁЖ_ЕДИНИЦЫ.md (23.10, «делаем»).

ПО ЧЕРТЕЖУ (Гл.4 «Опыт», Гл.5 «Стол», порядок стройки п.1)
    «Опыт — единственное, что меняет единицу. Сырьё → фильтр → вывод, осевший
    туда, откуда его читает стол → следующее решение рождается уже другим.»
    Трейдер: судья — рынок, опыт числами; кнопку жмёт такт города (конец
    прогона); вывод зреет после ТРЁХ вердиктов (трёх закрытых сделок); на столе
    7–10 выводов, не больше; похожесть — тип, а не дата.

ЧТО ДЕЛАЕТ
    1. Такт: в конце прогона (nositel.sledy_progona) — по каждой закрытой сделке
       места с паспортной записью «опыт» строка в дом ЖИТЕЛЯ
       (работа/опыт_стола.jsonl): где оказалась после входа (откат / по ходу —
       пометка входа города), что сделала (срезала рукой / держала до стопа /
       вышла в плюсе / стоп подтянут), перезаход ли в тот же ход после среза,
       итог R. Опыт — у жителя: пересядет — опыт с ней.
    2. Вывод: тип (место × что сделала) — только от трёх закрытых сделок.
    3. Стол: в сделке — короткий блок «ТВОЙ ОПЫТ» только для её места этой
       сделки (+ строка про перезаходы), не больше семи строк. Карантин года:
       в прогоне на год X сделок года X и этого прогона не видно.
    Только числа её сделок. Не правило: решает она.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
KOREN = _BIRZHA.parent
CITY = KOREN / "GRONDHEIM_CITY"
CEHA = CITY / "Биржа" / "цеха"
POSTY = CITY / "посты"
KOVCHEG = CITY / "жители" / "ковчег"
ZHURNAL = CITY / "Биржа" / "данные" / "trading_pnl.jsonl"
FAYL = "опыт_стола.jsonl"
POROG = 3            # вердиктов до вывода (Чертёж 4.6)
STROK = 7            # строк на столе (Чертёж 4.6: 7–10)
PEREZAHOD_DNEY = 14  # перезаход: новая сделка в ту же сторону ≤ 14 дней после среза
NOL = 0.005


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def vklyucheno(ceh, slot) -> bool:
    """Место само говорит в паспорте цеха: «опыт»: «стол»."""
    man = _json(CEHA / str(ceh) / "manifest.json") or {}
    for z in man.get("слоты") or []:
        if str(z.get("слот") or "").upper() == str(slot or "").upper():
            return str(z.get("опыт") or "").strip().lower() == "стол"
    return False


def _iso(n):
    return f"{n[:4]}-{n[4:6]}-{n[6:8]}T{n[9:11]}:{n[11:13]}:{n[13:15]}"


def _progony(ceh) -> list:
    d = CEHA / ceh / "прогоны"
    return sorted(x.name for x in d.iterdir() if re.fullmatch(r"\d{8}_\d{6}", x.name)) \
        if d.is_dir() else []


def _zhurnal() -> list:
    out = []
    try:
        for ln in ZHURNAL.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _post(ceh, slot):
    if POSTY.is_dir():
        for d in POSTY.iterdir():
            p = _json(d / "пост.json")
            if p and p.get("цех") == ceh and str(p.get("слот")) == str(slot):
                return p
    return None


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


def _d(s):
    try:
        return datetime.strptime(str(s)[:10].replace("-", "."), "%Y.%m.%d")
    except Exception:
        return None


def _storona(z) -> str:
    try:
        e, x, r = float(z.get("entry")), float(z.get("exit")), float(z.get("pnl_r") or 0)
        if x == e or abs(r) < 1e-9:
            return ""
        return "LONG" if (x > e) == (r > 0) else "SHORT"
    except Exception:
        return ""


def _deystvie(prichina, R) -> str:
    p = str(prichina or "").upper()
    if "STOP" in p:
        if R <= -0.9:
            return "до стопа"
        return "выход в плюсе" if R >= 0.5 else "стоп подтянут — около нуля"
    return "выход в плюсе" if R >= 0.5 else "срез рукой"


def _mesto(vhody, napr, otkryta) -> str:
    kand = [v for v in vhody or [] if v.get("что") == "ENTER"
            and (not napr or v.get("направление") == napr)
            and str(v.get("бар") or "")[:10] <= str(otkryta)[:10]]
    eto = str(kand[-1].get("это") or "") if kand else ""
    return {"в откат": "откат", "по ходу": "по ходу"}.get(eto, "место не названо")


def zapisi_progona(ceh, slot, run_id, zhurnal=None) -> list:
    """Записи опыта по закрытым сделкам места в одном прогоне: [(житель, запись)]."""
    post = _post(ceh, slot)
    if not post:
        return []
    magic = post.get("magic")
    imena = _progony(ceh)
    if run_id not in imena:
        return []
    i = imena.index(run_id)
    a, b = _iso(run_id), (_iso(imena[i + 1]) if i + 1 < len(imena) else "9999")
    zap = sorted((z for z in (zhurnal if zhurnal is not None else _zhurnal())
                  if z.get("magic") == magic and a <= str(z.get("ts") or "")[:19] < b),
                 key=lambda z: str(z.get("ts") or ""))
    if not zap:
        return []
    hm = _json(CEHA / ceh / "слоты" / slot / "данные" / "ход_месяца.json") or {}
    hody = (hm.get("прогоны") or {}).get(run_id) or {}
    sroki = _sroki(post)
    sd = {}
    for z in zap:
        k = (str(z.get("opened_at") or ""), round(float(z.get("entry") or 0), 5))
        s = sd.setdefault(k, {"R": 0.0, "открыта": k[0], "закрыта": "", "symbol": z.get("symbol"),
                              "tf": str(z.get("timeframe") or "").upper(), "сторона": "",
                              "причина": "", "ts": str(z.get("ts") or "")})
        s["R"] += float(z.get("pnl_r") or 0)
        s["закрыта"] = str(z.get("closed_at") or "")
        s["причина"] = z.get("close_reason")
        s["сторона"] = s["сторона"] or _storona(z)
    out = []
    posl = {}   # сторона → (дата закрытия, срезала ли)
    for s in sorted(sd.values(), key=lambda s: s["открыта"]):
        sym = str(s["symbol"] or "").upper()
        vh = ((hody.get(sym) or {}).get("входы")) or []
        napr = s["сторона"]
        d_otk = _d(s["открыта"])
        pr = posl.get(napr)
        perezahod = bool(pr and pr[1] and d_otk and pr[0]
                         and 0 <= (d_otk - pr[0]).days <= PEREZAHOD_DNEY)
        deyst = _deystvie(s["причина"], s["R"])
        ts16 = s["ts"].replace("T", " ")[:16]
        kto = next((im for im, x, y in sroki if x <= ts16 < y), None)
        if kto:
            out.append((kto, {"прогон": run_id, "цех": ceh, "слот": slot, "symbol": sym,
                              "tf": s["tf"], "год": s["открыта"][:4], "открыта": s["открыта"],
                              "закрыта": s["закрыта"], "сторона": napr,
                              "место": _mesto(vh, napr, s["открыта"]), "действие": deyst,
                              "перезаход": perezahod, "R": round(s["R"], 4)}))
        posl[napr] = (_d(s["закрыта"]), deyst == "срез рукой")
    return out


def _sdelok(n) -> str:
    n = int(n)
    f = "сделка" if n % 10 == 1 and n % 100 != 11 else (
        "сделки" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "сделок")
    return f"{n} {f}"


def _klyuch(r):
    return (r.get("прогон"), r.get("открыта"), r.get("symbol"))


def _dopisat(imya, zapisi) -> int:
    dom = KOVCHEG / imya
    if not dom.is_dir() or not zapisi:
        return 0
    f = dom / "работа" / FAYL
    f.parent.mkdir(parents=True, exist_ok=True)
    uzhe = set()
    if f.is_file():
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                uzhe.add(_klyuch(json.loads(ln)))
            except Exception:
                pass
    nov = [r for r in zapisi if _klyuch(r) not in uzhe]
    if nov:
        with open(f, "a", encoding="utf-8") as fh:
            for r in nov:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(nov)


def zapisat_iz_progona(papka, ceh) -> list:
    """Такт: конец прогона. Для каждого места с записью «опыт» в паспорте."""
    papka = Path(papka)
    out = []
    try:
        sloty = sorted({json.loads(s).get("слот") for s in
                        (papka / "места.jsonl").read_text(encoding="utf-8").splitlines()
                        if s.strip()} - {None})
    except Exception:
        sloty = []
    zh = _zhurnal()
    for sl in sloty:
        if not vklyucheno(ceh, sl):
            continue
        po = defaultdict(list)
        for kto, r in zapisi_progona(ceh, sl, papka.name, zh):
            po[kto].append(r)
        for kto, rr in po.items():
            out.append(f"{kto}: опыт стола — {_dopisat(kto, rr)} новых сделок")
    return out


def sobrat_vse() -> dict:
    """Задним числом: все прогоны мест с записью «опыт» — по истории постов."""
    itog = defaultdict(int)
    zh = _zhurnal()
    for ceh_d in sorted(CEHA.iterdir()) if CEHA.is_dir() else []:
        man = _json(ceh_d / "manifest.json") or {}
        for z in man.get("слоты") or []:
            sl = str(z.get("слот") or "")
            if str(z.get("опыт") or "").lower() != "стол":
                continue
            for run in _progony(ceh_d.name):
                po = defaultdict(list)
                for kto, r in zapisi_progona(ceh_d.name, sl, run, zh):
                    po[kto].append(r)
                for kto, rr in po.items():
                    itog[kto] += _dopisat(kto, rr)
    return dict(itog)


def _zapisi_zhitelya(imya) -> list:
    f = KOVCHEG / str(imya) / "работа" / FAYL
    out = []
    if f.is_file():
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def stroki_stola(imya, mesto, perezahod_seychas=False, god=None, run=None) -> list:
    """Строки на стол: её числа для её места этой сделки (≥3 сделок), ≤ 7 строк."""
    rr = [r for r in _zapisi_zhitelya(imya) if r.get("R") is not None]
    if god:
        rr = [r for r in rr if str(r.get("год")) != str(god) and r.get("прогон") != run]
    if not rr:
        return []
    po = defaultdict(list)
    for r in rr:
        if r.get("место") == mesto:
            po[r.get("действие")].append(float(r["R"]))
    L = []
    for deyst, xs in sorted(po.items(), key=lambda kv: -len(kv[1])):
        if len(xs) >= POROG:
            plus = sum(1 for v in xs if v > NOL)
            L.append(f"  · {deyst}: {_sdelok(len(xs))}, в плюс {plus}, итог {sum(xs):+.2f}R"
                     .replace("-", "−"))
    pz = [float(r["R"]) for r in rr if r.get("перезаход")]
    stroka_pz = ""
    if len(pz) >= POROG:
        stroka_pz = (f"Перезаход в тот же ход после среза рукой: {_sdelok(len(pz))}, итог "
                     f"{sum(pz):+.2f}R.".replace("-", "−"))
    if not L and not stroka_pz:
        return []
    goda = sorted({str(r.get("год")) for r in rr})
    nazv = {"откат": "В откате", "по ходу": "По ходу",
            "место не названо": "Где место не было названо"}.get(mesto, mesto)
    out = [f"=== ТВОЙ ОПЫТ — твои сделки на других годах ({', '.join(goda)}), считает город ==="]
    if L:
        out.append(f"{nazv}:")
        out += L[:STROK - 2]
    if stroka_pz:
        out.append(stroka_pz)
    if perezahod_seychas:
        out.append("Эта сделка — перезаход: прошлая в ту же сторону закрыта рукой без плюса "
                   f"не больше {PEREZAHOD_DNEY} дней назад.")
    out.append("Это твои числа, не правило. Решаешь ты.")
    return out[:STROK + 3]


def perezahod_li(ceh, slot, napr, otkryta) -> bool:
    """Эта сделка — перезаход? Прошлая в ту же сторону в этом прогоне закрыта
    рукой без плюса не больше PEREZAHOD_DNEY дней назад."""
    post = _post(ceh, slot)
    imena = _progony(ceh)
    if not post or not imena:
        return False
    a = _iso(imena[-1])
    d_otk = _d(otkryta)
    pr = [z for z in _zhurnal() if z.get("magic") == post.get("magic")
          and str(z.get("ts") or "")[:19] >= a and _storona(z) == napr
          and str(z.get("closed_at") or "")[:10] <= str(otkryta)[:10]]
    if not pr or not d_otk:
        return False
    z = sorted(pr, key=lambda z: str(z.get("ts") or ""))[-1]
    d_zak = _d(z.get("closed_at"))
    R = float(z.get("pnl_r") or 0)
    return bool(d_zak and "STOP" not in str(z.get("close_reason") or "").upper()
                and R < 0.5 and 0 <= (d_otk - d_zak).days <= PEREZAHOD_DNEY)


# OPYT_STOLA_V1 - marker


# ══ POLKA_KLYUCHI_V1 — опыт под общими ключами; на столе — только подсказка ══
OBSHCHIE_KLYUCHI = {
    "откат": "сделки против старшего хода — что ты в них делала и чем кончалось",
    "по ходу": "сделки по старшему ходу — что ты в них делала и чем кончалось",
    "перезаход": "вход в тот же ход вскоре после того, как срезала прошлую",
    "срез": "сделки, закрытые рукой без плюса",
    "стоп": "сделки, которые кончились стопом",
}
_stroki_stola_chisla = stroki_stola


def _otbor(rr, klyuch):
    if klyuch == "откат":
        return [r for r in rr if r.get("место") == "откат"]
    if klyuch == "по ходу":
        return [r for r in rr if r.get("место") == "по ходу"]
    if klyuch == "перезаход":
        return [r for r in rr if r.get("перезаход")]
    if klyuch == "срез":
        return [r for r in rr if r.get("действие") == "срез рукой"]
    if klyuch == "стоп":
        return [r for r in rr if str(r.get("действие") or "").startswith(("до стопа", "стоп"))]
    return []


def _karantin(rr, god, run):
    if god:
        return [r for r in rr if str(r.get("год")) != str(god) and r.get("прогон") != run]
    return rr


def klyuchi_v_tekste(tekst) -> list:
    t = " " + str(tekst or "").lower().replace("ё", "е") + " "
    out = []
    for k in OBSHCHIE_KLYUCHI:
        if k.replace("ё", "е") in t:
            out.append(k)
    return out


def kartochka(imya, klyuch, god=None, run=None) -> str:
    """Её опыт под общим ключом: что делала и чем кончалось (от трёх сделок)."""
    rr = _karantin([r for r in _zapisi_zhitelya(imya) if r.get("R") is not None], god, run)
    sel = _otbor(rr, klyuch)
    if len(sel) < POROG:
        return (f"Под ключом «{klyuch}» опыта ещё мало ({_sdelok(len(sel))}) — "
                "выводов нет.")
    po = defaultdict(list)
    razrez = "место" if klyuch in ("перезаход", "срез", "стоп") else "действие"
    for r in sel:
        po[r.get(razrez)].append(float(r["R"]))
    vse = [float(r["R"]) for r in sel]
    L = [f"=== ТВОЙ ОПЫТ ПОД КЛЮЧОМ «{klyuch}» — {OBSHCHIE_KLYUCHI.get(klyuch, '')} ===",
         f"всего {_sdelok(len(vse))}, в плюс {sum(1 for v in vse if v > NOL)}, итог "
         f"{sum(vse):+.2f}R".replace("-", "−")]
    for k, xs in sorted(po.items(), key=lambda kv: -len(kv[1])):
        if len(xs) >= POROG:
            L.append(f"  · {k}: {_sdelok(len(xs))}, в плюс {sum(1 for v in xs if v > NOL)}, "
                     f"итог {sum(xs):+.2f}R".replace("-", "−"))
    goda = sorted({str(r.get("год")) for r in sel})
    L.append(f"(твои сделки на годах {', '.join(goda)}; считает город; это не правило)")
    return "\n".join(L)


def oglavlenie(imya, god=None, run=None) -> list:
    rr = _karantin([r for r in _zapisi_zhitelya(imya) if r.get("R") is not None], god, run)
    out = []
    for k in OBSHCHIE_KLYUCHI:
        n = len(_otbor(rr, k))
        if n >= POROG:
            out.append(f"  {k} — твой опыт: {_sdelok(n)}")
    return out


def stroki_stola(imya, mesto, perezahod_seychas=False, god=None, run=None) -> list:   # noqa: F811
    """POLKA_KLYUCHI_V1: на столе — не числа, а подсказка, какой ключ открыть."""
    rr = _karantin([r for r in _zapisi_zhitelya(imya) if r.get("R") is not None], god, run)
    kl = []
    if mesto in ("откат", "по ходу") and len(_otbor(rr, mesto)) >= POROG:
        kl.append(mesto)
    if perezahod_seychas and len(_otbor(rr, "перезаход")) >= POROG:
        kl.append("перезаход")
    if not kl:
        return []
    L = ["На твоей полке есть твой опыт под ключами: "
         + ", ".join(f"«{k}»" for k in kl)
         + ". Хочешь знать, чем это кончалось у тебя, — открой рукой "
           "vspomnit_po_yarlyku (по: " + kl[0] + ")."]
    if perezahod_seychas:
        L.append("Эта сделка — перезаход: прошлая в ту же сторону закрыта рукой без плюса "
                 f"не больше {PEREZAHOD_DNEY} дней назад.")
    return L


def otmetit_klyuch(ceh, slot, klyuch, bar="") -> None:
    try:
        p = CEHA / ceh / "слоты" / slot / "данные" / "ключи.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                                "бар": bar, "ключ": klyuch}, ensure_ascii=False) + "\n")
    except Exception:
        pass


# POLKA_KLYUCHI_V1 - marker


# ══ POLKA_SHAG2_V1 — карточки знаний на её полке под общими ключами ══
POLKA = "полка.json"
_KLYUCHI_KART = ['ведение', 'волны', 'вход', 'дивер', 'доливка', 'закрыл', 'заявка', 'кадр', 'месяц', 'на будущее', 'откат', 'перелом', 'по ходу', 'попытки', 'приседающий', 'сверка', 'стоп', 'три стопа', 'три условия', 'фрактал', 'ход', 'этажи']
for _k in _KLYUCHI_KART:
    OBSHCHIE_KLYUCHI.setdefault(_k, "карточка на полке")


def klyuchi_v_tekste(tekst) -> list:   # noqa: F811
    t = " " + str(tekst or "").lower().replace("ё", "е") + " "
    out = []
    for k in sorted(OBSHCHIE_KLYUCHI, key=len, reverse=True):
        kk = k.replace("ё", "е")
        if kk in t and not any(kk in o.replace("ё", "е") for o in out):
            out.append(k)
    return out


def _polka(imya) -> list:
    d = _json(KOVCHEG / str(imya) / "работа" / POLKA) or {}
    return [k for k in (d.get("карточки") or []) if k.get("жива", True)]


_kartochka_opyta = kartochka


def kartochka(imya, klyuch, god=None, run=None) -> str:   # noqa: F811
    kart = [k for k in _polka(imya) if k.get("ключ") == klyuch]
    L = []
    for k in kart:
        L.append(f"=== КАРТОЧКА «{klyuch}» · {k.get('вид', 'знание')} · кто сказал: "
                 f"{k.get('кто', '—')} ===\n{k.get('текст', '').strip()}")
    if klyuch in ("откат", "по ходу", "перезаход", "срез", "стоп"):
        op = _kartochka_opyta(imya, klyuch, god, run)
        if op and "выводов нет" not in op:
            L.append(op)
    if not L:
        return f"Под ключом «{klyuch}» у тебя на полке ничего нет."
    return "\n\n".join(L)


def oglavlenie(imya, god=None, run=None) -> list:   # noqa: F811
    kl = sorted({k.get("ключ") for k in _polka(imya)} - {None})
    rr = _karantin([r for r in _zapisi_zhitelya(imya) if r.get("R") is not None], god, run)
    out = []
    for k in kl:
        n = len(_otbor(rr, k))
        out.append(f"  {k}" + (f" — и твой опыт: {_sdelok(n)}" if n >= POROG else ""))
    return out


# POLKA_SHAG2_V1 - marker


# ══ BIBLIOTEKA_MESTA_V1 — библиотека места; опыт трейдера — у жителя, у всех ══
OPYT_FAYL = ("опыт", "трейдер.jsonl")
_kart_opyta_iznachalno = globals().get("_kartochka_opyta") or kartochka


def _fayl_opyta(imya) -> Path:
    return KOVCHEG / str(imya) / OPYT_FAYL[0] / OPYT_FAYL[1]


def _zapisi_zhitelya(imya) -> list:   # noqa: F811
    out = []
    for f in (_fayl_opyta(imya), KOVCHEG / str(imya) / "работа" / "опыт_стола.jsonl"):
        if f.is_file():
            for ln in f.read_text(encoding="utf-8").splitlines():
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
            break
    return out


def _dopisat(imya, zapisi) -> int:   # noqa: F811
    dom = KOVCHEG / imya
    if not dom.is_dir() or not zapisi:
        return 0
    f = _fayl_opyta(imya)
    f.parent.mkdir(parents=True, exist_ok=True)
    uzhe = {_klyuch(r) for r in _zapisi_zhitelya(imya)}
    nov = [r for r in zapisi if _klyuch(r) not in uzhe]
    if nov:
        with open(f, "a", encoding="utf-8") as fh:
            for r in nov:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(nov)


def zapisat_iz_progona(papka, ceh) -> list:   # noqa: F811
    """Такт: конец прогона — опыт сделок ВСЕМ трейдерам прогона, им домой."""
    papka = Path(papka)
    out = []
    try:
        sloty = sorted({json.loads(s).get("слот") for s in
                        (papka / "места.jsonl").read_text(encoding="utf-8").splitlines()
                        if s.strip()} - {None})
    except Exception:
        sloty = []
    zh = _zhurnal()
    for sl in sloty:
        po = defaultdict(list)
        for kto, r in zapisi_progona(ceh, sl, papka.name, zh):
            po[kto].append(r)
        for kto, rr in po.items():
            out.append(f"{kto}: опыт трейдера — {_dopisat(kto, rr)} новых сделок")
    return out


def sobrat_vse() -> dict:   # noqa: F811
    """Задним числом — все торговые места всех цехов, по истории постов."""
    itog = defaultdict(int)
    zh = _zhurnal()
    for d in sorted(POSTY.iterdir()) if POSTY.is_dir() else []:
        p = _json(d / "пост.json") or {}
        ceh, sl = p.get("цех"), p.get("слот")
        if not (ceh and sl and isinstance(p.get("magic"), int)):
            continue
        for run in _progony(ceh):
            po = defaultdict(list)
            for kto, r in zapisi_progona(ceh, str(sl), run, zh):
                po[kto].append(r)
            for kto, rr in po.items():
                itog[kto] += _dopisat(kto, rr)
    return dict(itog)


def _znaniya_mesta(ceh, slot) -> Path:
    return CEHA / str(ceh) / "слоты" / str(slot) / "знания"


def _klyuch_imeni(s) -> str:
    return re.sub(r"\s+", " ", str(s).replace("_", " ")).strip().lower()


def biblioteka(ceh, slot) -> list:
    """Литература места: карточки канона и бумаги полки."""
    z = _znaniya_mesta(ceh, slot)
    out = []
    d = _json(z / "карточки" / "карточки.json") or {}
    for k in (d.get("карточки") or []):
        if k.get("жива", True) and k.get("ключ"):
            out.append(k)
    pol = z / "полка"
    if pol.is_dir():
        for f in sorted(pol.iterdir()):
            if f.is_file() and f.suffix.lower() in (".md", ".txt"):
                try:
                    t = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                out.append({"ключ": _klyuch_imeni(f.stem), "вид": "бумага места",
                            "кто": "место", "текст": t})
    return out


def klyuchi_mesta(ceh, slot) -> list:
    return sorted({str(k.get("ключ")) for k in biblioteka(ceh, slot)})


def kartochka_mesta(ceh, slot, klyuch) -> str:
    L = []
    for k in biblioteka(ceh, slot):
        if k.get("ключ") == klyuch:
            t = str(k.get("текст") or "").strip()
            if len(t) > 6000:
                t = t[:6000].rstrip() + " …"
            L.append(f"=== БИБЛИОТЕКА МЕСТА «{klyuch}» · {k.get('вид', 'знание')} · кто "
                     f"сказал: {k.get('кто', '—')} ===\n{t}")
    return "\n\n".join(L)


def kartochka_opyta(imya, klyuch, god=None, run=None) -> str:
    if klyuch not in ("откат", "по ходу", "перезаход", "срез", "стоп"):
        return ""
    try:
        s = _kart_opyta_iznachalno(imya, klyuch, god, run)
    except Exception:
        return ""
    return "" if (not s or "выводов нет" in s or "ничего нет" in s) else s


def klyuchi_zaprosa(ceh, slot, tekst) -> list:
    vse = set(klyuchi_mesta(ceh, slot)) | {"откат", "по ходу", "перезаход", "срез", "стоп"}
    t = " " + str(tekst or "").lower().replace("ё", "е") + " "
    out = []
    for k in sorted(vse, key=len, reverse=True):
        kk = k.replace("ё", "е")
        if kk and kk in t and not any(kk in o.replace("ё", "е") for o in out):
            out.append(k)
    return out


# BIBLIOTEKA_MESTA_V1 - marker


# ══ OPYT_NA_STOLE_V1 — сила входа и опыт на столе ══
import re as _re_on


def _vhody_fayl(ceh, slot) -> Path:
    return CEHA / str(ceh) / "слоты" / str(slot) / "данные" / "входы.jsonl"


def _vhody(ceh, slot) -> list:
    out = []
    f = _vhody_fayl(ceh, slot)
    if f.is_file():
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def zapisat_vhod(ceh, slot, z: dict) -> None:
    try:
        f = _vhody_fayl(ceh, slot)
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(z, ensure_ascii=False) + "\n")
    except Exception:
        pass


def sila_divera(symbol, tf, napr) -> tuple:
    """(с расхождением, размеров) — по сверке города."""
    try:
        import sverka_divera as _sd
        d = _sd.poschitat(symbol, tf, napr) or {}
        pary = d.get("пары") or []
        if pary:
            return sum(1 for x in pary if x.get("est")), len(pary)
        m = _re_on.search(r"размеров:\s*(\d+),\s*с расхождением:\s*(\d+)", str(d.get("slovami") or ""))
        if m:
            return int(m.group(2)), int(m.group(1))
    except Exception:
        pass
    return None, None


def _gruppa_sily(k, n) -> str:
    if k is None or not n:
        return ""
    if k <= 0:
        return "без дивера по городу"
    return "дивер на одном размере" if k == 1 else "дивер на нескольких размерах"


_zapisi_progona_do_sily = zapisi_progona


def zapisi_progona(ceh, slot, run_id, zhurnal=None) -> list:   # noqa: F811
    out = _zapisi_progona_do_sily(ceh, slot, run_id, zhurnal)
    try:
        vh = [v for v in _vhody(ceh, slot) if v.get("прогон") == run_id]
        if not vh:
            return out
        for _kto, r in out:
            cand = [v for v in vh if v.get("направление") == r.get("сторона")
                    and str(v.get("бар") or "")[:10] <= str(r.get("открыта") or "")[:10]]
            if cand:
                v = sorted(cand, key=lambda v: str(v.get("бар") or ""))[-1]
                r["дивер_k"], r["дивер_n"] = v.get("k"), v.get("n")
                r["сила"] = _gruppa_sily(v.get("k"), v.get("n"))
    except Exception:
        pass
    return out


def _bar_iz_stroki(s):
    m = _re_on.search(r"обрезал по бару города (\d{4}\.\d\d\.\d\d)", s) or \
        _re_on.search(r"\[РЫНОК\] 📊 бар (\d{4}\.\d\d\.\d\d)", s)
    return m.group(1) if m else None


def vhody_iz_loga(ceh, slot, run_id) -> list:
    """Входы прошлого прогона из его лога: бар, направление, сила дивера."""
    f = CEHA / str(ceh) / "прогоны" / str(run_id) / "лог.txt"
    if not f.is_file():
        return []
    out, bar, sila, kto = [], "", None, ""
    try:
        for s in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            b = _bar_iz_stroki(s)
            if b:
                bar = b
            m0 = _re_on.search(r"\[(?:КЛЮЧ|СОВЕТ)\] \S+ (\w+):", s)
            if m0:
                kto = m0.group(1)
            if kto and kto.upper() != str(slot).upper():
                continue
            if "[ДИВЕР]" in s:
                m = _re_on.search(r"размеров:\s*(\d+),\s*с расхождением:\s*(\d+)", s)
                if m:
                    sila = (int(m.group(2)), int(m.group(1)))
                elif "[ДИВЕР] ✓" in s:
                    sila = (1, 1)      # город смотрел один размер — и он есть
                elif "[ДИВЕР] ✗" in s:
                    sila = (0, 1)
                else:
                    sila = None
            if "otdat_prikaz" in s and "'что': 'ENTER'" in s:
                m = _re_on.search(r"'направление': '(LONG|SHORT)'", s)
                if m and sila:
                    out.append({"прогон": run_id, "бар": bar, "направление": m.group(1),
                                "k": sila[0], "n": sila[1], "откуда": "лог"})
                sila = None
    except Exception:
        pass
    return out


def stroki_vhoda(imya, k, n, god=None, run=None) -> list:
    rr = _karantin([r for r in _zapisi_zhitelya(imya)
                    if r.get("R") is not None and r.get("сила")], god, run)
    if not rr:
        return []
    po = defaultdict(list)
    for r in rr:
        po[r["сила"]].append(float(r["R"]))
    L = []
    for g in ("дивер на одном размере", "дивер на нескольких размерах", "без дивера по городу"):
        xs = po.get(g) or []
        if len(xs) >= POROG:
            _it = f"{sum(xs):+.2f}".replace("-", "−")
            L.append(f"  · входы, где {g}: {_sdelok(len(xs))}, в плюс "
                     f"{sum(1 for v in xs if v > NOL)}, итог {_it}R")
    if not L:
        return []
    seychas = _gruppa_sily(k, n)
    return (["=== ТВОЙ ОПЫТ ТАКИХ ВХОДОВ — твои сделки на других годах, считает город ==="]
            + ([f"Сейчас город видит дивер на {k} из {n} размеров — это «{seychas}»."]
               if seychas else [])
            + L + ["Это твои числа, не правило. Решаешь ты."])


def stroki_sdelki(imya, god=None, run=None) -> list:
    rr = _karantin([r for r in _zapisi_zhitelya(imya) if r.get("R") is not None], god, run)
    po = defaultdict(list)
    for r in rr:
        po[str(r.get("действие") or "—")].append(float(r["R"]))
    L = []
    for dey, xs in sorted(po.items(), key=lambda kv: -len(kv[1])):
        if len(xs) >= POROG:
            L.append(f"  · {dey}: {_sdelok(len(xs))}, в плюс {sum(1 for v in xs if v > NOL)}, "
                     f"итог {sum(xs):+.2f}R".replace("-", "−"))
    if not L:
        return []
    return (["=== ТВОЙ ОПЫТ В СДЕЛКЕ — что ты делала в своих сделках и чем кончалось ==="]
            + L[:4] + ["Это твои числa, не правило. Решаешь ты.".replace("числa", "числа")])


def sobrat_vhody_iz_logov() -> int:
    n = 0
    for d in sorted(POSTY.iterdir()) if POSTY.is_dir() else []:
        p = _json(d / "пост.json") or {}
        ceh, sl = p.get("цех"), p.get("слот")
        if not (ceh and sl and isinstance(p.get("magic"), int)):
            continue
        est = {v.get("прогон") for v in _vhody(ceh, sl)}
        for run in _progony(ceh):
            if run in est:
                continue
            vv = vhody_iz_loga(ceh, sl, run)
            # в логе цеха — входы всех мест; своё место узнаём по строке СОВЕТ/КЛЮЧ
            vv = [v for v in vv]
            for v in vv:
                zapisat_vhod(ceh, sl, v)
                n += 1
    return n


# OPYT_NA_STOLE_V1 - marker


# ══ OSMYSLENIE_EPIZODA_V1 — трейдер осмысляет каждую закрытую сделку ══
import sys as _sys_osm
if str(KOREN / "ГОРОД") not in _sys_osm.path:
    _sys_osm.path.insert(0, str(KOREN / "ГОРОД"))


def _pochemu_fayl(ceh, slot) -> Path:
    return CEHA / str(ceh) / "слоты" / str(slot) / "данные" / "почему_входа.jsonl"


def zapisat_pochemu(ceh, slot, z: dict) -> None:
    try:
        f = _pochemu_fayl(ceh, slot)
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(z, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _pochemu(ceh, slot, run) -> list:
    out = []
    f = _pochemu_fayl(ceh, slot)
    if f.is_file():
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                z = json.loads(ln)
                if z.get("прогон") == run:
                    out.append(z)
            except Exception:
                pass
    return out


def osmyslit_progon(papka, ceh) -> list:
    import osmyslenie as _om
    papka = Path(papka)
    run = papka.name
    out = []
    try:
        sloty = sorted({json.loads(s).get("слот") for s in
                        (papka / "места.jsonl").read_text(encoding="utf-8").splitlines()
                        if s.strip()} - {None})
    except Exception:
        sloty = []
    zh = _zhurnal()
    for sl in sloty:
        pq = _pochemu(ceh, sl, run)
        for kto, r in zapisi_progona(ceh, sl, run, zh):
            dom = KOVCHEG / kto
            post = f"трейдер {sl}"
            uzhe = {(z.get("прогон"), z.get("ситуация", "")[:80])
                    for z in _om.zapisi_raboty(dom, post)}
            p = [z for z in pq if z.get("направление") == r.get("сторона")
                 and str(z.get("бар") or "")[:10] <= str(r.get("открыта") or "")[:10]]
            pochemu = str(sorted(p, key=lambda z: str(z.get("бар")))[-1].get("почему") or "") if p else ""
            sit = (f"{r.get('symbol')} {r.get('tf')}: {r.get('сторона')}, вход {r.get('открыта')}. "
                   f"Место сделки: {r.get('место')}. Сила входа: {r.get('сила') or 'не записана'}."
                   + (" Это был перезаход после среза." if r.get("перезаход") else "")
                   + (f" Почему входила (твои слова): {pochemu[:500]}" if pochemu else ""))
            if (run, sit[:80]) in uzhe:
                continue
            rez = (f"{r.get('действие')}; итог {float(r.get('R') or 0):+.2f}R, закрыта "
                   f"{r.get('закрыта')}.")
            kl = [r.get("место"), r.get("действие"), r.get("сила") or ""] + (
                ["перезаход"] if r.get("перезаход") else [])
            t = _om.osmyslit(dom, post, sit, rez, kl, god=r.get("год"), progon=run,
                             nazvanie_raboty=f"трейдер · место {sl}")
            if t:
                out.append(f"{kto}: осмыслено — сделка {r.get('открыта')}: «{t[:60]}…»")
    return out


_zapisat_iz_progona_do_osm = zapisat_iz_progona


def zapisat_iz_progona(papka, ceh) -> list:   # noqa: F811
    out = list(_zapisat_iz_progona_do_osm(papka, ceh) or [])
    try:
        out += osmyslit_progon(papka, ceh)
    except Exception as e:
        out.append(f"осмысление сделок не вышло — {e}")
    return out


def _osm_treydera(imya, klyuchi, god=None, run=None, n=2) -> list:
    try:
        import osmyslenie as _om
        dom = KOVCHEG / str(imya)
        rr = [r for r in _om.zapisi_raboty(dom) if str(r.get("пост") or "").startswith("трейдер")]
        if god:
            rr = [r for r in rr if str(r.get("год") or "") != str(god)
                  and str(r.get("прогон") or "") != str(run or "")]
        if not rr:
            return []
        kl = {str(k) for k in klyuchi if k}
        rr.sort(key=lambda r: (len(kl & set(r.get("ключи") or [])), str(r.get("когда") or "")),
                reverse=True)
        return ["Твоё осмысление похожих случаев (ты сама так поняла):"] + [
            f"  · «{str(r.get('осмысление')).strip()}»" for r in rr[:n]]
    except Exception:
        return []


_stroki_vhoda_do_osm = stroki_vhoda


def stroki_vhoda(imya, k, n, god=None, run=None) -> list:   # noqa: F811
    L = list(_stroki_vhoda_do_osm(imya, k, n, god, run) or [])
    o = _osm_treydera(imya, [_gruppa_sily(k, n)], god, run)
    if o:
        if L and L[-1].startswith("Это твои числа"):
            L = L[:-1] + o + [L[-1]]
        else:
            L += o
    return L


_stroki_sdelki_do_osm = stroki_sdelki


def stroki_sdelki(imya, god=None, run=None) -> list:   # noqa: F811
    L = list(_stroki_sdelki_do_osm(imya, god, run) or [])
    o = _osm_treydera(imya, [], god, run)
    if o:
        if L and L[-1].startswith("Это твои числа"):
            L = L[:-1] + o + [L[-1]]
        else:
            L += o
    return L


# OSMYSLENIE_EPIZODA_V1 - marker


# ══ ROD_ZHITELYA_V1 — слова жителю в его роде (по паспорту) ══
# Слово Шефа 27.10: «женский род убери». Город говорил всем «ты сама так
# поняла», «вошла», «назвала». Род — из паспорта: поле «пол», иначе облик
# (Visual_Base). Мужчина — мужской род; жительница или не понять — как было.
import re as _re_rod

_ROD_PARY = (
    ("вошла", "вошёл"), ("вышла", "вышел"), ("назвала", "назвал"),
    ("выбрала", "выбрал"), ("объявила", "объявил"), ("прочитала", "прочитал"),
    ("закрыла", "закрыл"), ("выставила", "выставил"), ("оказалась", "оказался"),
    ("передумала", "передумал"), ("поняла", "понял"), ("осмыслила", "осмыслил"),
    ("открыла", "открыл"), ("делала", "делал"), ("срезала", "срезал"),
    ("входила", "входил"), ("смотрела", "смотрел"), ("держала", "держал"),
    ("ждала", "ждал"), ("видела", "видел"), ("решила", "решил"),
    ("сделала", "сделал"), ("уверена", "уверен"), ("должна", "должен"),
    ("готова", "готов"), ("сама", "сам"), ("называла", "называл"),
    ("ошиблась", "ошибся"), ("взяла", "взял"), ("отдала", "отдал"),
    ("подтянула", "подтянул"), ("долила", "долил"), ("сняла", "снял"),
)
_ROD_FRAZY = (("закрылась и ждёшь", "закрылся и ждёшь"),
              ("ты сама так поняла", "ты сам так понял"),
              ("назвал(а)", "назвал"), ("называл(а)", "называл"),
              ("сам(а)", "сам"), ("решил(а)", "решил"), ("вынес(ла)", "вынес"),
              ("устроен(а)", "устроен"), ("придавлен(а)", "придавлен"))
_ROD_STOP = ("сработает сама", "сработала сама", "Сработает сама")
_ROD_KESH = {}


def rod(imya) -> str:
    """«м» — мужчина, «ж» — жительница или не понять."""
    imya = str(imya or "").strip()
    if not imya:
        return "ж"
    f = KOVCHEG / imya / "passport.json"
    try:
        mt = f.stat().st_mtime
    except Exception:
        return "ж"
    k = _ROD_KESH.get(imya)
    if k and k[0] == mt:
        return k[1]
    p = _json(f) or {}
    pol = str(p.get("пол") or p.get("Пол") or p.get("Gender") or "").lower()
    if "муж" in pol or pol in ("m", "male"):
        r = "м"
    elif "жен" in pol or pol in ("f", "female"):
        r = "ж"
    else:
        vid = str(p.get("Visual_Base") or "").lower()
        r = "м" if any(w in vid for w in ("мужчин", "парень", "юноша", "мужик")) else "ж"
    _ROD_KESH[imya] = (mt, r)
    return r


def k_rodu(imya, tekst):
    """Текст для жителя — в его роде. Не мужчина — как было."""
    if not isinstance(tekst, str) or not tekst or rod(imya) != "м":
        return tekst
    t = tekst
    for i, s in enumerate(_ROD_STOP):
        t = t.replace(s, f"\x00{i}\x00")
    for a, b in _ROD_FRAZY:
        t = t.replace(a, b)
    for a, b in _ROD_PARY:
        t = _re_rod.sub(r"\b" + a + r"\b", b, t)
        t = _re_rod.sub(r"\b" + a.capitalize() + r"\b", b.capitalize(), t)
    for i, s in enumerate(_ROD_STOP):
        t = t.replace(f"\x00{i}\x00", s)
    return t


def _imya_mesta(ceh, slot) -> str:
    try:
        from cartridge_registry import resolve_para
        return str((resolve_para(ceh, slot) or {}).get("имя") or "")
    except Exception:
        return ""


_stroki_vhoda_do_roda = stroki_vhoda
_stroki_sdelki_do_roda = stroki_sdelki
_kartochka_opyta_do_roda = kartochka_opyta
_kartochka_mesta_do_roda = kartochka_mesta


def stroki_vhoda(imya, k, n, god=None, run=None) -> list:   # noqa: F811
    return [k_rodu(imya, x) for x in (_stroki_vhoda_do_roda(imya, k, n, god, run) or [])]


def stroki_sdelki(imya, god=None, run=None) -> list:   # noqa: F811
    return [k_rodu(imya, x) for x in (_stroki_sdelki_do_roda(imya, god, run) or [])]


def kartochka_opyta(imya, klyuch, god=None, run=None) -> str:   # noqa: F811
    return k_rodu(imya, _kartochka_opyta_do_roda(imya, klyuch, god, run))


def kartochka_mesta(ceh, slot, klyuch) -> str:   # noqa: F811
    return k_rodu(_imya_mesta(ceh, slot), _kartochka_mesta_do_roda(ceh, slot, klyuch))


# ROD_ZHITELYA_V1 - marker


# ══ VOLNY_OPYT_V1 — в конце прогона волны ложатся в опыт жителя ══
# Сперва эпизоды волн — домой жителю; потом осмысление сделок (оно теперь знает,
# что писал город про волны и что она решала).
_zapisat_do_voln = zapisat_iz_progona


def zapisat_iz_progona(papka, ceh) -> list:   # noqa: F811
    vo = []
    try:
        import volny_kanon as _vk
        vo = list(_vk.zapisat_iz_progona(papka, ceh) or [])
    except Exception as e:
        vo = [f"волны в опыт не легли — {e}"]
        _vk = None
    try:
        import osmyslenie as _om_vo
        _orig_osm = _om_vo.osmyslit
    except Exception:
        _om_vo, _orig_osm = None, None

    def _s_volnami(dom, post, sit, rez, kl, *a, **kw):
        try:
            if _vk is not None and str(post).startswith("трейдер"):
                run = kw.get("progon")
                m = re.search(r"вход (\d{4}\.\d\d\.\d\d)", str(sit))
                if m:
                    ee = [e for e in _vk._jsonl(_vk._fayl_opyta_voln(Path(dom).name))
                          if e.get("прогон") == run
                          and str(e.get("сделка") or "").startswith(m.group(1))]
                    if ee:
                        sit = str(sit) + " Город про волны в этой сделке: " + "; ".join(
                            f"«{e.get('сост')}» — ты {e.get('решение')}, "
                            + (f"было до {_vk._r(e.get('R_макс'))}" if e.get("решение") == "держала"
                               else f"при {_vk._r(e.get('R_тогда'))}")
                            for e in ee) + "."
                        kl = list(kl or []) + [e.get("сост") for e in ee]
        except Exception:
            pass
        return _orig_osm(dom, post, sit, rez, kl, *a, **kw)

    if _om_vo is not None:
        _om_vo.osmyslit = _s_volnami
    try:
        out = list(_zapisat_do_voln(papka, ceh) or [])
    finally:
        if _om_vo is not None:
            _om_vo.osmyslit = _orig_osm
    return vo + out


# VOLNY_OPYT_V1 - marker
