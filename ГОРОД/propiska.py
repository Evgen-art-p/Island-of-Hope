# -*- coding: utf-8 -*-
# PROPISKA_MIRA_V1 · V2 (дорога в обе стороны) — прописка: признаёт ли этот мир единицу
"""
ПРОПИСКА · одно место на весь мир

Слово Шефа 11.11: «нужен ключ идентификации, чтобы дубли не плодились: он
единый, даже если дубль сделать — его город и мир не примет»; «сделай эту
проверку так, чтобы она встраивалась в будущем в нужные места — будут и
локации, и ещё много чего, чтобы не забыть».

ЗАКОН ПРОПИСКИ
    Ключ единицы — отпечаток её печати создателя (_Creator_Seal_Hash), он
    рождается на Странице Жизни главного города и не меняется никогда.
    Скопировать папку можно всегда — но мир признаёт единицу только там,
    где она ПРОПИСАНА. Копия с тем же ключом в другом месте — не признаётся:
    её не будят, не сажают, ею не работают.

    ЛЮБОЕ место кода, которое берёт единицу ДЛЯ ДЕЛА (будит, сажает на пост,
    ведёт в работу, везёт), спрашивает:

        import propiska
        ok, pochemu = propiska.priznan(dom=папка)        # или klyuch=..., imya=...
        if not ok: ...  # не работать с ней, сказать почему

    Новый вид единицы (инструмент, посылка, здание…) — новая строка в ВИДЫ,
    код проверки не трогаем. Строгость вида — там же: строгий вид без
    прописки не признаётся; нестрогий — прописывается при первой встрече
    (так мягко входят виды, пока у них нет перевозки).

    Чтобы не забыть: propiska.audit_koda() показывает места кода, которые
    берут жителей и локации, но ещё не спрашивают прописку.

ГДЕ ЧТО ЛЕЖИТ (GRONDHEIM_CITY/мир/)
    город.json      — кто этот город: {"id": "T1", "имя": ..., "материк": true}
    прописка.json   — реестр: ключ → {вид, имя, id, где, дом, с, рейс}
                      На материке реестр — главный. На острове — свой список
                      тех, кого он принял по пропускам.
    рейсы.json      — пропуска, уже принятые этим городом (второй раз — нет)

ПЕЧАТЬ ГОРОДА — одна секретная фраза мира, только в .env обеих машин:
    GRONDHEIM_PECHAT_GORODA=...
    Ею заверяется пропуск рейса. В репо её нет и быть не должно.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # ГОРОД/
KOREN = _HERE.parent
CITY = KOREN / "GRONDHEIM_CITY"
MIR = CITY / "мир"
GOROD_F = MIR / "город.json"
REESTR_F = MIR / "прописка.json"
REYSY_F = MIR / "рейсы.json"
POLE_KLYUCHA = "_Creator_Seal_Hash"
ENV_PECHAT = "GRONDHEIM_PECHAT_GORODA"

# Виды единиц мира. Новый вид — новая строка, проверку не трогаем.
VIDY = {
    "житель":  {"папка": CITY / "жители" / "ковчег", "паспорт": "passport.json",
                "строго": True},
    "локация": {"папка": CITY / "локации", "паспорт": "passport.json",
                "строго": False},
}


# ── диск ───────────────────────────────────────────────────────
def _chitat(p: Path, default=None):
    for kod in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(p.read_text(encoding=kod))
        except Exception:
            continue
    return default


def _pisat(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _teper() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ── кто этот город ─────────────────────────────────────────────
def gorod() -> dict:
    g = _chitat(GOROD_F, None)
    if g:
        return g
    # Не задан — материк узнаём по Странице Жизни: она только там.
    materik = (KOREN / "Брат" / "ui_registry.py").is_file()
    return {"id": "T1" if materik else "?", "имя": "Грондхейм" if materik else "",
            "материк": materik, "_note": "не задан явно — определён по Странице Жизни"}


def gorod_id() -> str:
    return str(gorod().get("id") or "?")


def eto_materik() -> bool:
    return bool(gorod().get("материк"))


# ── реестр ─────────────────────────────────────────────────────
def reestr() -> dict:
    return _chitat(REESTR_F, None) or {"записи": {}}


def zapis(klyuch: str) -> dict:
    return (reestr().get("записи") or {}).get(klyuch or "", {}) or {}


def _sohranit_zapis(klyuch: str, z: dict) -> None:
    r = reestr()
    r.setdefault("записи", {})[klyuch] = z
    r["_note"] = ("Мировой реестр прописки: ключ единицы → где она живёт. Закон — "
                  "ГОРОД/propiska.py. Копия с тем же ключом в другом месте не признаётся.")
    _pisat(REESTR_F, r)


# ── ключ и дом единицы ─────────────────────────────────────────
def klyuch_doma(dom: Path, vid: str = "житель") -> str:
    p = _chitat(Path(dom) / VIDY.get(vid, VIDY["житель"])["паспорт"], {}) or {}
    return str(p.get(POLE_KLYUCHA) or "").strip()


def doma(vid: str = "житель") -> list:
    """[(дом, паспорт, ключ)] всех единиц вида в этом городе."""
    v = VIDY.get(vid)
    if not v or not v["папка"].is_dir():
        return []
    out = []
    for d in sorted(v["папка"].iterdir()):
        if not d.is_dir():
            continue
        p = _chitat(d / v["паспорт"], None)
        if p is None:
            continue
        out.append((d, p, str(p.get(POLE_KLYUCHA) or "").strip()))
    return out


def dom_po_imeni(imya: str, vid: str = "житель"):
    for d, p, _k in doma(vid):
        if imya in ((p.get("Official_Name") or "").strip(), d.name):
            return d
    return None


# ── ГЛАВНОЕ: признан ли ────────────────────────────────────────
def priznan(klyuch: str = "", *, dom=None, imya: str = "", vid: str = "житель") -> tuple:
    """(True/False, почему). Спрашивать перед любым ДЕЛОМ с единицей."""
    try:
        if dom is None and imya:
            dom = dom_po_imeni(imya, vid)
        if not klyuch and dom is not None:
            klyuch = klyuch_doma(dom, vid)
        if not klyuch:
            return True, "без ключа — старый порядок (печати нет)"
        z = zapis(klyuch)
        gid = gorod_id()
        strogo = VIDY.get(vid, {}).get("строго", True)
        if not z:
            if eto_materik() or not strogo:
                imya_ = imya or (dom.name if dom is not None else "")
                _sohranit_zapis(klyuch, {"вид": vid, "имя": imya_, "где": gid,
                                         "дом": dom.name if dom is not None else "",
                                         "с": _teper(), "рейс": "",
                                         "_как": "прописан при первой встрече"})
                return True, f"прописан здесь ({gid}) при первой встрече"
            return False, (f"в этом городе ({gid}) не прописан — приехать можно только "
                           "по пропуску перевозки")
        if str(z.get("где")) != gid:
            return False, (f"уехал(а) в «{z.get('где')}» с {z.get('с', '?')}"
                           + (f", рейс {z.get('рейс')}" if z.get("рейс") else "")
                           + " — здесь его нет: дом и жильё ждут, на работу не встаёт")
        if dom is not None and z.get("дом") and z.get("дом") != dom.name:
            return False, f"двойник: настоящий дом этого ключа — «{z.get('дом')}»"
        return True, f"прописан здесь ({gid})"
    except Exception as e:
        # Проверка сама не должна ронять город: честно говорим и пропускаем.
        print(f"[ПРОПИСКА] проверка не сложилась ({e}) — пропускаю")
        return True, f"проверка не сложилась: {e}"


def priznan_li(**kw) -> bool:
    return priznan(**kw)[0]


# ── первая перепись (материк) ──────────────────────────────────
def pervaya_perepis() -> dict:
    """Все единицы в этом городе с ключом и без записи — прописываются здесь.
    Двойники (два дома с одним ключом) — в отчёт, без записи второго."""
    gid = gorod_id()
    itog = {"прописано": 0, "уже": 0, "без_ключа": [], "двойники": []}
    for vid in VIDY:
        vidno = {}
        for d, p, k in doma(vid):
            if not k:
                itog["без_ключа"].append(f"{vid}: {d.name}")
                continue
            if k in vidno:
                itog["двойники"].append(f"{vid}: {d.name} = {vidno[k]}")
                continue
            vidno[k] = d.name
            if zapis(k):
                itog["уже"] += 1
                continue
            _sohranit_zapis(k, {"вид": vid, "имя": (p.get("Official_Name") or d.name),
                                "id": p.get("ID_Object", ""), "где": gid, "дом": d.name,
                                "с": _teper(), "рейс": "", "_как": "первая перепись"})
            itog["прописано"] += 1
    return itog


# ── печать города и пропуск рейса ──────────────────────────────
def _pechat() -> bytes:
    f = os.getenv(ENV_PECHAT, "")
    if not f:
        env = KOREN / ".env"
        if env.is_file():
            for s in env.read_text(encoding="utf-8", errors="replace").splitlines():
                s = s.strip()
                if s.startswith(ENV_PECHAT + "="):
                    f = s.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return f.encode("utf-8")


def est_pechat() -> bool:
    return bool(_pechat())


def _podpis(telo: dict) -> str:
    stroka = json.dumps(telo, ensure_ascii=False, sort_keys=True)
    return hmac.new(_pechat(), stroka.encode("utf-8"), hashlib.sha256).hexdigest()


def vydat_propusk(klyuch: str, kuda: str, imya: str = "", vid: str = "житель") -> dict:
    """Город, где единица прописана, переписывает прописку на «куда» и выдаёт
    заверенный пропуск. Дорога в обе стороны: с материка на остров и обратно.
    С этой секунды здесь единицы нет — дом и жильё ждут её возвращения."""
    if not est_pechat():
        raise RuntimeError(f"нет печати города — впиши {ENV_PECHAT}=… в .env")
    if str(kuda) == gorod_id():
        raise RuntimeError("пропуск в свой же город не выдаётся")
    z = zapis(klyuch)
    if z and str(z.get("где")) != gorod_id():
        raise RuntimeError(f"сейчас прописан(а) в «{z.get('где')}» — отправлять отсюда нечего")
    if not z and not eto_materik():
        raise RuntimeError("в этом городе не прописан(а) — отправить нельзя")
    reys = f"{datetime.now():%Y%m%d%H%M}-{secrets.token_hex(3)}"
    telo = {"рейс": reys, "ключ": klyuch, "вид": vid, "имя": imya,
            "откуда": gorod_id(), "куда": kuda, "когда": _teper()}
    propusk = dict(telo, подпись=_podpis(telo))
    novaya = dict(z or {}, вид=vid, имя=imya or (z or {}).get("имя", ""), где=kuda,
                  с=_teper(), рейс=reys, дом=(z or {}).get("дом", ""), _как="уехал по пропуску")
    _sohranit_zapis(klyuch, novaya)
    return propusk


def prinyat_propusk(propusk: dict, dom_imya: str = "") -> tuple:
    """Город прибытия: печать верна, пропуск сюда и ещё не использован →
    единица прописывается здесь. (True/False, почему)."""
    if not est_pechat():
        return False, f"нет печати города — впиши {ENV_PECHAT}=… в .env"
    telo = {k: v for k, v in (propusk or {}).items() if k != "подпись"}
    if not hmac.compare_digest(_podpis(telo), str((propusk or {}).get("подпись", ""))):
        return False, "печать пропуска не сходится — пропуск поддельный или печати разные"
    if str(telo.get("куда")) != gorod_id():
        return False, f"пропуск не сюда: он в «{telo.get('куда')}», а это «{gorod_id()}»"
    ispolz = _chitat(REYSY_F, None) or {"рейсы": {}}
    if telo.get("рейс") in (ispolz.get("рейсы") or {}):
        return False, f"рейс {telo.get('рейс')} уже принят — второй экземпляр не признаётся"
    ispolz.setdefault("рейсы", {})[telo["рейс"]] = {"ключ": telo.get("ключ"),
                                                   "имя": telo.get("имя"), "принят": _teper()}
    _pisat(REYSY_F, ispolz)
    _sohranit_zapis(telo["ключ"], {"вид": telo.get("вид", "житель"), "имя": telo.get("имя", ""),
                                   "где": gorod_id(), "дом": dom_imya or telo.get("имя", ""),
                                   "с": _teper(), "рейс": telo.get("рейс"),
                                   "_как": f"приехал из «{telo.get('откуда')}»"})
    return True, f"принят по пропуску рейса {telo.get('рейс')}"


# ── чтобы не забыть: где код берёт единицы без проверки ────────
_PRIMETY = (re.compile(r"ковчег"), re.compile(r"passport\.json"), re.compile(r"локации"))
_NE_SMOTRET = {".git", "__pycache__", "_ЧУЛАН", "_ПЕЧАТИ", "_ПЕРЕЕЗД", "node_modules",
               "venv", ".venv", "замеры"}


def audit_koda(koren: Path = None) -> list:
    """[(файл, сколько примет)] — модули, которые берут жителей или локации,
    но ещё не спрашивают прописку. Патчи и замеры не смотрим."""
    koren = koren or KOREN
    out = []
    for p in koren.rglob("*.py"):
        otn = p.relative_to(koren)
        if any(x in _NE_SMOTRET for x in otn.parts) or ".bak" in p.name:
            continue
        if len(otn.parts) == 1:          # корень — это патчи и замеры
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "propiska" in t or p.name == "propiska.py":
            continue
        n = sum(len(rx.findall(t)) for rx in _PRIMETY)
        if n:
            out.append((otn.as_posix(), n))
    return sorted(out, key=lambda x: -x[1])


# PROPISKA_MIRA_V1 - marker
# PROPISKA_MIRA_V2 - marker
