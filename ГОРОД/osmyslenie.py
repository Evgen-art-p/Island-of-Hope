# -*- coding: utf-8 -*-
# OSMYSLENIE_EPIZODA_V1
"""
ОСМЫСЛЕНИЕ ЭПИЗОДА — петля опыта жителя на любой работе (26.10).

СЛОВО ШЕФА 26.10
    «Ситуация — результат — осмыслил — снова ситуация уже с осмыслением и
    другой результат.» «У каждой работы своя полка и опыт, а метки все под
    одно.» Касается всех вакансий города.

КАК УСТРОЕНО
    • Эпизод работы кончился (сделка закрылась, разговор Ректора с кандидатом,
      ответ Хранителя…) — пост зовёт osmyslit(): житель СВОИМ голосом (душа
      из паспорта) говорит одну-две фразы, что он из этого понял для своей
      работы. Урока нет — честное «нечего», ничего не пишем.
    • Осмысление ложится на полку ЭТОЙ работы, у жителя дома:
      опыт/работа_<пост>.jsonl — с ключами ситуации, годом и прогоном.
      Общие метки (2_метки, предел 40) не трогаются: опыт работы их не
      вытесняет. Ищет по полке тот же движок памяти (vspomnit), теми же ключами.
    • В следующий раз пост зовёт opyt_raboty() — и 2–4 его осмысления, ближе
      всего подходящие по ключам к нынешней ситуации, ложатся на стол.
    Одна запись на эпизод: повторы не склеиваются — видно, повторяется ли урок.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
if str(_REPO / "Биржа") not in sys.path:
    sys.path.insert(0, str(_REPO / "Биржа"))
if str(_REPO / "ГОРОД") not in sys.path:
    sys.path.insert(0, str(_REPO / "ГОРОД"))

NECHEGO = ("нечего", "нечего.", "урока нет", "—")


def _slug(post: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", str(post or "работа").strip().lower(), flags=re.U)
    return s.strip("_")[:60] or "работа"


def polka_raboty(dom, post) -> Path:
    return Path(dom) / "опыт" / f"работа_{_slug(post)}.jsonl"


def zapisi_raboty(dom, post=None) -> list:
    """Все осмысления работы (одной или всех)."""
    d = Path(dom) / "опыт"
    fayly = [polka_raboty(dom, post)] if post else sorted(d.glob("работа_*.jsonl")) if d.is_dir() else []
    out = []
    for f in fayly:
        if not f.is_file():
            continue
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def _dusha(dom) -> str:
    try:
        import rezidenty as _rz
        p = json.loads((Path(dom) / "passport.json").read_text(encoding="utf-8"))
        return _rz.sobrat_dushu(p)
    except Exception:
        return f"Ты — {Path(dom).name}, житель Грондхейма. Говоришь от первого лица."


def osmyslit(dom, post: str, situaciya: str, rezultat: str, klyuchi=None,
             god: str = "", progon: str = "", nazvanie_raboty: str = "") -> str | None:
    """Житель осмысляет эпизод своей работы. Возвращает осмысление или None."""
    klyuchi = [str(k).strip().lower() for k in (klyuchi or []) if str(k).strip()]
    try:
        import llm as _llm
    except Exception as e:
        print(f"[ОСМЫСЛЕНИЕ] модель недоступна ({e})")
        return None
    rabota = nazvanie_raboty or post
    system = (_dusha(dom) + f"\nСейчас ты на своей работе: {rabota}. Это эпизод твоей "
              "работы — посмотри на него своими глазами.")
    user = (f"ЧТО БЫЛО:\n{str(situaciya).strip()[:1500]}\n\nЧЕМ КОНЧИЛОСЬ:\n"
            f"{str(rezultat).strip()[:600]}\n\n"
            "Что ты из этого понял(а) для своей работы? Одна-две фразы, от первого "
            "лица, своими словами: не пересказ, а урок — что в похожий раз сделаешь "
            "так же или иначе. Если урока здесь нет — ответь одним словом: нечего.")
    try:
        otvet = _llm.chat(system, user, agent_id=Path(dom).name, slot_id=_slug(post),
                          temperature=0.6)
    except Exception as e:
        print(f"[ОСМЫСЛЕНИЕ] {Path(dom).name}: модель не ответила ({e})")
        return None
    t = re.sub(r"\s+", " ", str(otvet or "")).strip().strip('"«»')
    if not t or t.lower().strip(" .!") in NECHEGO or len(t) < 12:
        print(f"[ОСМЫСЛЕНИЕ] {Path(dom).name} · {rabota}: урока нет")
        return None
    t = t[:500]
    zap = {"когда": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "пост": post, "работа": rabota, "ситуация": str(situaciya).strip()[:600],
           "результат": str(rezultat).strip()[:300], "осмысление": t,
           "ключи": klyuchi, "год": str(god or ""), "прогон": str(progon or ""),
           "полка": "опыт", "откуда": "работа"}
    f = polka_raboty(dom, post)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(zap, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[ОСМЫСЛЕНИЕ] не легло на полку ({e})")
        return None
    print(f"[ОСМЫСЛЕНИЕ] {Path(dom).name} · {rabota}: «{t[:90]}»")
    return t


def opyt_raboty(dom, post, klyuchi=None, n: int = 3, god=None, progon=None) -> list:
    """Его осмысления этой работы, ближе всего к ситуации по ключам.
    Карантин: в прогоне на год X осмыслений года X и этого прогона не видно."""
    kl = {str(k).strip().lower() for k in (klyuchi or []) if str(k).strip()}
    rr = zapisi_raboty(dom, post)
    if god:
        rr = [r for r in rr if str(r.get("год") or "") != str(god)
              and str(r.get("прогон") or "") != str(progon or "")]
    if not rr:
        return []
    def ves(r):
        return (len(kl & set(r.get("ключи") or [])), str(r.get("когда") or ""))
    rr.sort(key=ves, reverse=True)
    if kl and ves(rr[0])[0] == 0:
        rr = sorted(rr, key=lambda r: str(r.get("когда") or ""), reverse=True)
    return [str(r.get("осмысление") or "").strip() for r in rr[:n] if r.get("осмысление")]


def stroki_na_stol(dom, post, klyuchi=None, n: int = 3, god=None, progon=None,
                   nazvanie: str = "") -> list:
    oo = opyt_raboty(dom, post, klyuchi, n, god, progon)
    if not oo:
        return []
    return ([f"=== ТВОЁ ОСМЫСЛЕНИЕ — {nazvanie or post}: что ты сам(а) понял(а) в похожих "
             "случаях ==="] + [f"  · «{o}»" for o in oo])


# OSMYSLENIE_EPIZODA_V1 - marker


# ══ OSMYSLENIE_POSTOV_V1 — эпизоды постов: поступок и разговоры ══
import threading as _thr

RAZGOVOROV_DO_OSMYSLENIYA = 5
_BUFER = {}          # пост → [(кто, вопрос, ответ)] — разговоры с прошлого осмысления
_ISTORIYA = {}       # пост → последние разговоры (для поступков: с кем говорил)
KLYUCHI_SEYCHAS = {}  # пост → ключи нынешней ситуации (у Ректора — имя собеседника)


def _v_fone(fn, *a, **k):
    try:
        _thr.Thread(target=lambda: fn(*a, **k), daemon=True).start()
    except Exception as e:
        print(f"[ОСМЫСЛЕНИЕ] фон не запустился ({e})")


def _kto_i_dom(post_id):
    try:
        import rezidenty as _rz
        imya = _rz.kto_na_postu(post_id)
        return imya, _rz.dom_zhitelya(imya)
    except Exception:
        return "", None


def _nazvanie_posta(post_id) -> str:
    try:
        import rezidenty as _rz
        return str((_rz.get_post(post_id) or {}).get("название") or post_id)
    except Exception:
        return str(post_id)


def epizod_razgovora(post_id, vopros, otvet, kto="Шеф") -> None:
    """Разговор на посту прошёл. Раз в пять — осмысление последних пяти."""
    otvet = str(otvet or "")
    if not otvet.strip() or otvet.lstrip().startswith("⚠"):
        return
    zap = (str(kto or "Шеф"), str(vopros or "")[:400], otvet[:500])
    _ISTORIYA.setdefault(post_id, []).append(zap)
    _ISTORIYA[post_id] = _ISTORIYA[post_id][-30:]
    buf = _BUFER.setdefault(post_id, [])
    buf.append(zap)
    if len(buf) < RAZGOVOROV_DO_OSMYSLENIYA:
        return
    pyat, _BUFER[post_id] = list(buf), []
    imya, dom = _kto_i_dom(post_id)
    if not dom:
        return
    sit = "Последние разговоры на твоей работе:\n" + "\n".join(
        f"— {k}: {v[:200]}\n  я: {o[:220]}" for k, v, o in pyat)
    kl = [post_id] + sorted({k for k, _v, _o in pyat if k})
    _v_fone(osmyslit, dom, post_id, sit, "Разговоры прошли — что ты из них вынес(ла) "
            "о своей работе?", kl, nazvanie_raboty=_nazvanie_posta(post_id))


def epizod_postupka(post_id, deystvie, s_kem, rezultat, dop_klyuchi=None) -> None:
    """Поступок на посту с результатом: осмыслить разговор с этим человеком и итог."""
    imya, dom = _kto_i_dom(post_id)
    if not dom:
        return
    s_kem = str(s_kem or "")
    razg = [z for z in _ISTORIYA.get(post_id, [])
            if s_kem and (z[0] == s_kem or s_kem.lower() in (z[1] + " " + z[2]).lower())][-4:]
    sit = (f"{deystvie}: {s_kem}." + ("\nРазговор перед этим:\n" + "\n".join(
        f"— {k}: {v[:220]}\n  я: {o[:240]}" for k, v, o in razg) if razg else
        "\nРазговора перед этим в памяти поста нет."))
    kl = [str(deystvie).lower(), s_kem.lower()] + [str(x).lower() for x in (dop_klyuchi or []) if x]
    _v_fone(osmyslit, dom, post_id, sit, str(rezultat), kl,
            nazvanie_raboty=_nazvanie_posta(post_id))


# OSMYSLENIE_POSTOV_V1 - marker
