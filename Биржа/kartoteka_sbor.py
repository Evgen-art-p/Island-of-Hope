# -*- coding: utf-8 -*-
# KARTOTEKA_SBOR_V1
"""
КАРТОТЕКА ЖИТЕЛЕЙ — сборка из результатов города (19.10).

СЛОВО ШЕФА 19.10
    «Скрипт, который берёт результаты и делает карточки, такие красивые, и
    кнопка «Картотека» под панелью приборов в кабинете Биржи.»
    «Последний и лучший результат должен быть.»

ОТКУДА ЧТО
    ЦИФРЫ — из журнала города (GRONDHEIM_CITY/Биржа/данные/trading_pnl.jsonl).
        Чья сделка — по постам (посты/*/пост.json): номер счёта места и
        трудовая история (кто и когда сидел). Какой прогон — по папкам
        цеха/<цех>/прогоны/<время>/: сделка идёт в тот прогон, чьё начало
        ближе всего перед её записью. Сделки Города (тени, доливки) — по
        другим номерам счёта, в итог жителя не входят.
    ФОТО — как кабинет: «avatar» в папке жителя (жители/ковчег/<Имя>/). У тех,
        кто уже есть в картотеке, берётся прежний кадр (картотека/portrety.json).
    СЛОВА (сила / риск / не доказано / главный тест) — от Софии:
        cards_overrides.json, затем КАРТОТЕКА_ЖИТЕЛЕЙ.md. Нет слов — карточка
        с цифрами и пометкой «оценка Софии ещё не записана».
    ВИД — картотека/shablon.html (тот же дизайн, что в образце).

На карточке: ПОСЛЕДНИЙ прогон жителя и ЛУЧШИЙ (по итогу в R); в досье — все
прогоны списком. Год и рынок прогона подписаны: лучший может быть на другом
годе, и это видно.

Город не торгует и ничего не меняет: сборщик только читает журнал и пишет
одну страницу в картотека/сборка/kartoteka.html.
"""
from __future__ import annotations

import base64
import io
import json
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
KOREN = _BIRZHA.parent
CITY = KOREN / "GRONDHEIM_CITY"
POSTY = CITY / "посты"
CEHA = CITY / "Биржа" / "цеха"
ZHURNAL = CITY / "Биржа" / "данные" / "trading_pnl.jsonl"
KOVCHEG = CITY / "жители" / "ковчег"
# Картотека и её исходники перенесены внутрь GRONDHEIM_CITY/Биржа.
# Сборщик остаётся в корневой Биржа/ рядом с ui_torg.py.
KART = CITY / "Биржа" / "картотека"
SHABLON = KART / "shablon.html"
PORTRETY = KART / "portrety.json"
OVERRIDES = KART / "cards_overrides.json"
VYHOD = KART / "сборка" / "kartoteka.html"
# Новый путь — первым, чтобы оценка Софии читалась из актуальной картотеки.
# Остальные пути оставлены только как совместимый запасной вариант.
MD_PUTI = (CITY / "Биржа" / "КАРТОТЕКА_ЖИТЕЛЕЙ.md",
           KOREN / "КАРТОТЕКА_ЖИТЕЛЕЙ.md",
           KOREN / "docs" / "КАРТОТЕКА_ЖИТЕЛЕЙ.md")

NOL = 0.005                      # меньше этого по модулю — «в ноль»
PROGONOV_V_DOSYE = 14
TEKST_KLYUCHI = ("s", "k", "u", "t", "ep", "epl")
NAMES = {"СИЛА": "s", "РИСК": "k", "НЕ ДОКАЗАНО": "u", "ТЕСТ": "t", "ЭПИЗОД": "ep"}
PRICHINY = {"STOP_LOSS": "стоп", "MANUAL_CLOSE": "ручной выход",
            "TAKE_PROFIT": "тейк", "MANUAL": "ручной выход"}

SVODKA = []          # что собралось в последний раз — для проверки патча


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def _minus(s: str) -> str:
    return s.replace("-", "−")


def _rstr(v: float) -> str:
    return _minus(f"{v:+.2f}R")


# ── посты: чей номер счёта, кто и когда сидел ────────────────────
def _posty() -> dict:
    """{номер счёта: пост}. Один номер у двух постов — не угадываем."""
    out, dubli = {}, set()
    if not POSTY.is_dir():
        return out
    for d in sorted(POSTY.iterdir()):
        p = _json(d / "пост.json")
        if not p or not isinstance(p.get("magic"), int) or not p.get("цех"):
            continue
        m = p["magic"]
        if m in out:
            dubli.add(m)
        out[m] = p
    for m in dubli:
        print(f"[КАРТОТЕКА] номер счёта {m} у нескольких постов — их сделки не беру")
        out.pop(m, None)
    return out


def _sroki(post: dict) -> list:
    """[(имя, с, до)] — время строками 'ГГГГ-ММ-ДД ЧЧ:ММ'."""
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


def _kto_sidel(sroki: list, ts: str):
    for imya, a, b in sroki:
        if a <= ts < b:
            return imya
    return None


def _starty(ceh: str) -> tuple:
    """([время старта], [номер прогона]) по папкам цеха/<цех>/прогоны/."""
    d = CEHA / ceh / "прогоны"
    spisok = []
    if d.is_dir():
        for x in d.iterdir():
            m = re.fullmatch(r"(\d{8})_(\d{6})", x.name)
            if m:
                s, t = m.group(1), m.group(2)
                spisok.append((f"{s[:4]}-{s[4:6]}-{s[6:8]} {t[:2]}:{t[2:4]}", x.name))
    spisok.sort()
    return [a for a, _b in spisok], [b for _a, b in spisok]



# ══ A07_NOMER_GORODA_V1 — прежний номер поста ══
# Пост сменил номер счёта (A07: 100002 → 100014). Сделки под прежним
# номером до минуты смены («прежний_magic_до» в посте) — этого поста.
_PREZH = {"t": -1e9, "d": {}}


def _prezhniy_post(m, ts16):
    import time as _t_ng
    if _t_ng.monotonic() - _PREZH["t"] > 5:
        d = {}
        try:
            for x in sorted(POSTY.iterdir()):
                p = _json(x / "пост.json")
                if (p and isinstance(p.get("прежний_magic"), int)
                        and p.get("прежний_magic_до") and p.get("цех") and p.get("слот")):
                    d.setdefault(p["прежний_magic"], []).append(p)
        except Exception:
            pass
        _PREZH.update(t=_t_ng.monotonic(), d=d)
    try:
        m = int(m)
    except Exception:
        return None
    kand = [p for p in _PREZH["d"].get(m, []) if str(ts16) < str(p["прежний_magic_до"])]
    return kand[0] if len(kand) == 1 else None


# ── прогоны жителей из журнала ───────────────────────────────────
def _pr(r) -> float:
    try:
        return float(r.get("pnl_r") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _chislo(x) -> str:
    try:
        return f"{float(x):g}"
    except (TypeError, ValueError):
        return str(x)


def _progony() -> dict:
    """{имя: [прогон, …]} по времени. Прогон — итог жителя за один прогон."""
    posty = _posty()
    sroki = {m: _sroki(p) for m, p in posty.items()}
    starty = {}
    gruppy = defaultdict(list)
    if not ZHURNAL.is_file():
        return {}
    with open(ZHURNAL, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            ts = str(r.get("ts") or "").replace("T", " ")[:16]
            p = posty.get(r.get("magic")) or _prezhniy_post(r.get("magic"), ts)   # A07_NOMER_GORODA_V1
            if not p:
                continue                      # тени и доливки города — не жителя
            imya = _kto_sidel(_sroki(p), ts)
            if not imya:
                continue
            ceh = p["цех"]
            if ceh not in starty:
                starty[ceh] = _starty(ceh)
            vremena, nomera = starty[ceh]
            i = bisect_right(vremena, ts) - 1
            if i < 0:
                continue                      # раньше самого первого прогона
            gruppy[(imya, ceh, nomera[i])].append(r)
    itog = defaultdict(list)
    for (imya, ceh, nomer), recs in gruppy.items():
        osn = [r for r in recs if not r.get("нога") and not r.get("частичное")]
        if not osn:
            continue
        par = Counter((r.get("symbol"), r.get("timeframe")) for r in osn).most_common(1)[0][0]
        god = Counter(str(r.get("opened_at") or "")[:4] for r in osn).most_common(1)[0][0]
        plus = sum(1 for r in osn if _pr(r) > NOL)
        minus = sum(1 for r in osn if _pr(r) < -NOL)
        nol = len(osn) - plus - minus
        luch = max(osn, key=_pr)
        itog[imya].append({
            "nomer": nomer, "ceh": ceh, "R": sum(_pr(r) for r in recs),
            "closed": len(osn), "plus": plus, "minus": minus, "nol": nol,
            "metka": ("ПРОГОН " + nomer + " · "
                      + " ".join(x for x in (par[0], par[1], god) if x)),
            "luch": luch})
    for spisok in itog.values():
        spisok.sort(key=lambda x: x["nomer"])
    return itog


# ── слова Софии ──────────────────────────────────────────────────
def _predlozheniya(text, limit=230):
    text = re.sub(r"\s+", " ", (text or "").strip())
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", text):
        if out and len(out) + len(s) > limit:
            break
        out = (out + " " + s).strip()
        if len(out) >= limit * 0.6:
            break
    return out[:1].upper() + out[1:]


def _slova_iz_md() -> tuple:
    """({имя: {s,k,u,t,ep}}, [имена по порядку в файле])."""
    text = ""
    for p in MD_PUTI:
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            break
    res, poryadok = {}, []
    for sec in re.split(r"(?m)^## ", text)[1:]:
        name = sec.split("\n", 1)[0].strip()
        if not re.search(r"\*\*Прогон:\*\*\s*`([^`]+)`", sec):
            continue
        bl = {a.strip(): b.strip()
              for a, b in re.findall(r"(?m)^- \*\*(.+?):\*\*\s*(.+)$", sec)}
        c = {"s": _predlozheniya(bl.get("Сильная сторона", "")),
             "k": _predlozheniya(bl.get("Слабое место / риск", "")),
             "u": _predlozheniya(bl.get("Соответствие паспорту", "")),
             "t": "", "ep": ""}
        nt = re.search(r"Следующий тест:\s*(.+?)(?:\.\s|\.?$|\n)", sec)
        if nt:
            x = nt.group(1).strip()
            c["t"] = x[:1].upper() + x[1:] + ("" if x.endswith(".") else ".")
        blk = re.search(r"\*\*Карточка:\*\*\s*\n((?:\s*- .+\n?)+)", sec)
        if blk:
            for ln in blk.group(1).splitlines():
                mm = re.match(r"\s*- ([А-ЯЁ ]+):\s*(.+)", ln)
                if mm and mm.group(1).strip() in NAMES:
                    c[NAMES[mm.group(1).strip()]] = mm.group(2).strip()
        res[name] = c
        poryadok.append(name)
    return res, poryadok


# ── фото ─────────────────────────────────────────────────────────
def _avatar(imya: str):
    dom = KOVCHEG / imya
    if not dom.is_dir():
        return None
    p = _json(dom / "passport.json") or {}
    av = p.get("avatar", "")
    if av and (dom / av).is_file():
        return dom / av
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if (dom / ("avatar" + ext)).is_file():
            return dom / ("avatar" + ext)
    return None


def _lico(im):
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    g = cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2GRAY)
    k = 900 / max(g.shape)
    if k < 1:
        g = cv2.resize(g, None, fx=k, fy=k)
    else:
        k = 1
    f = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = f.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
    if not len(faces):
        return None
    x, y, w, h = max(faces, key=lambda a: a[2] * a[3])
    return x / k, y / k, w / k, h / k


def _kadr_portreta(path):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (247, 248, 249, 255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    W, H = im.size
    face = _lico(im)
    if face:
        fx, fy, fw, fh = face
        cw = fw * 3.0
        ch = cw * 1.25
        x0, y0 = fx + fw / 2 - cw / 2, fy - fh * 0.55
        x1, y1 = x0 + cw, y0 + ch
    else:
        cw = H * 0.28 if H > W * 1.4 else W * 0.7
        ch = cw * 1.25
        x0, y0 = W / 2 - cw / 2, H * 0.04
        x1, y1 = x0 + cw, y0 + ch
    dx = max(0, -x0) - max(0, x1 - W)
    dy = max(0, -y0) - max(0, y1 - H)
    box = tuple(int(v) for v in (max(0, x0 + dx), max(0, y0 + dy),
                                 min(W, x1 + dx), min(H, y1 + dy)))
    out = im.crop(box).resize((336, 420), Image.LANCZOS)
    b = io.BytesIO()
    out.save(b, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def _portret(imya: str, kesh: dict):
    """Прежний кадр (он выставлен руками) главнее; нового берём из папки жителя."""
    e = kesh.get(imya)
    if e and e.get("data"):
        return e["data"]
    f = _avatar(imya)
    if not f:
        return None
    try:
        data = _kadr_portreta(f)
    except Exception as ex:
        print(f"[КАРТОТЕКА] фото {imya} не обработалось ({ex}) — будет силуэт")
        return None
    kesh[imya] = {"src": str(f.name), "data": data}
    kesh["_izmenen"] = True
    return data


# ── сборка ───────────────────────────────────────────────────────
def _kartochki() -> list:
    progony = _progony()
    slova, poryadok = _slova_iz_md()
    ov = _json(OVERRIDES) or {}
    imena = [n for n in poryadok if n in progony]
    novye = sorted((n for n in progony if n not in imena),
                   key=lambda n: progony[n][0]["nomer"])
    cards = []
    for n, imya in enumerate(imena + novye, 1):
        runs = progony[imya]
        posl = runs[-1]
        luch = max(runs, key=lambda x: (x["R"], x["nomer"]))
        c = {"name": imya.upper(), "n": n, "img": imya,
             "run": posl["metka"], "closed": str(posl["closed"]),
             "r": round(posl["R"], 2), "res": _rstr(posl["R"]),
             "pm": f'{posl["plus"]} / {posl["minus"]}'
                   + (f' / {posl["nol"]}' if posl["nol"] else "")}
        if posl["nol"]:
            c["pl"] = "+ / − / 0"
        if luch is not posl:
            c["best"] = _rstr(luch["R"])
            c["best_r"] = round(luch["R"], 2)
            c["best_run"] = luch["metka"]
        lz = posl["luch"]
        c["ep"] = (f'{_chislo(lz.get("entry"))} → '
                   f'{PRICHINY.get(str(lz.get("close_reason")), str(lz.get("close_reason") or "").lower())} '
                   + _rstr(_pr(lz)))
        c["epl"] = "ЛУЧШАЯ СДЕЛКА ПРОГОНА"
        c["runs"] = [{"run": x["metka"], "res": _rstr(x["R"]), "r": round(x["R"], 2),
                      "closed": x["closed"], "last": x is posl, "best": x is luch}
                     for x in reversed(runs[-PROGONOV_V_DOSYE:])]
        for k, v in (slova.get(imya) or {}).items():
            if v:
                c[k] = v
        for k, v in (ov.get(imya) or {}).items():
            if k in TEKST_KLYUCHI and v:
                c[k] = v
        cards.append(c)
    return cards


def sobrat() -> str:
    """Собрать картотеку заново из свежих результатов. Возвращает путь к странице."""
    if not SHABLON.is_file():
        raise RuntimeError("нет картотека/shablon.html — запусти патч картотеки заново")
    cards = _kartochki()
    kesh = _json(PORTRETY) or {}
    imgs = {}
    for c in cards:
        data = _portret(c["img"], kesh)
        if data:
            imgs[c["img"]] = data
        else:
            c.pop("img")
    if kesh.pop("_izmenen", False):
        try:
            PORTRETY.write_text(json.dumps(kesh, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[КАРТОТЕКА] кэш фото не записался ({e})")
    cards = [c for c in cards]
    imgs = {k: v for k, v in imgs.items()}
    vsego = sum(1 for d in KOVCHEG.iterdir() if (d / "passport.json").is_file()) \
        if KOVCHEG.is_dir() else 21
    vsego = max(vsego, len(cards))

    def safe(o):
        return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")

    html = SHABLON.read_text(encoding="utf-8")
    html = (html.replace("/*__IMG__*/{}", safe(imgs))
            .replace("/*__DATA__*/[]", safe(cards))
            .replace("__TOTAL__", str(vsego))
            .replace("__DATE__", datetime.now().strftime("%Y-%m-%d %H:%M")))
    VYHOD.parent.mkdir(parents=True, exist_ok=True)
    VYHOD.write_text(html, encoding="utf-8")
    SVODKA[:] = [(c["name"], c["res"], c.get("best"), len(c.get("runs") or [])) for c in cards]
    print(f"[КАРТОТЕКА] собрано: {len(cards)} жителей из {vsego} → {VYHOD.name}")
    return str(VYHOD)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(sobrat())
    for s in SVODKA:
        print("  ", s)

# KARTOTEKA_SBOR_V1 - marker


# ══ ARCHI_V_KARTOTEKU_V1 — разбор архивариуса на карточке жителя ══
# Слово Шефа 27.10: «Арчи туда записывал после прогонов, что нам нужно».
# Берём из картотека/разборы/<имя>.md самый свежий блок с разбором архивариуса.
RAZBORY = KART / "разборы"


def _razbor_arhivariusa(imya: str):
    import html as _h
    try:
        t = (RAZBORY / f"{imya}.md").read_text(encoding="utf-8")
    except Exception:
        return None
    for blok in t.split("\n## ")[1:]:
        i = blok.find("### Разбор архивариуса")
        if i < 0:
            continue
        zag = blok.split("\n", 1)[0].strip()             # «Прогон … · цех/место · период …»
        ost = blok[i:].split("\n", 1)
        kto = ost[0].replace("### Разбор архивариуса", "").strip(" ()")
        kto = kto.split(")")[0].strip(" (") if kto else ""
        tekst = (ost[1] if len(ost) > 1 else "").strip()
        if not tekst:
            continue
        return {"arhl": "РАЗБОР АРХИВАРИУСА" + (f" · {kto}" if kto else "") + f" · {zag}",
                "arh": _h.escape(tekst).replace("\n", "<br>")}
    return None


_kartochki_do_arhivariusa = _kartochki


def _kartochki() -> list:   # noqa: F811
    cards = _kartochki_do_arhivariusa()
    for c in cards:
        imya = str(c.get("img") or c.get("name") or "")
        r = _razbor_arhivariusa(imya) or _razbor_arhivariusa(imya.capitalize())
        if r:
            c.update(r)
    return cards


# ARCHI_V_KARTOTEKU_V1 - marker


# A07_NOMER_GORODA_V1 - marker


# ══ METRIKI_INVESTORA_V1 — метрики инвестора на карточке и кратко сверху ══
# Слово Шефа 31.10. Считает metriki_investora.py; здесь — только раскладка.
_SV_METRIKI = []
_kartochki_do_metrik = _kartochki


def _kartochki() -> list:   # noqa: F811
    cards = _kartochki_do_metrik()
    try:
        import importlib
        import metriki_investora as _mi
        importlib.reload(_mi)
        dn = _mi.po_zhitelyam()
        _SV_METRIKI[:] = _mi.svodka_sverhu(dn)
    except Exception as e:
        print(f"[КАРТОТЕКА] метрики не посчитались ({e})")
        return cards
    po_imeni = {k.upper(): v for k, v in dn.items()}
    for c in cards:
        ss = po_imeni.get(str(c.get("name") or "").upper())
        if ss:
            c["inv"] = [{"имя": s["имя"], "м": s["м"], "история": s["история"]} for s in ss[:3]]
    return cards


_sobrat_do_metrik = sobrat


def sobrat() -> str:   # noqa: F811
    put = _sobrat_do_metrik()
    try:
        html = VYHOD.read_text(encoding="utf-8")
        html = html.replace("/*__SVODKA__*/[]",
                            json.dumps(_SV_METRIKI, ensure_ascii=False).replace("</", "<\\/"))
        VYHOD.write_text(html, encoding="utf-8")
    except Exception as e:
        print(f"[КАРТОТЕКА] сводка сверху не легла ({e})")
    return put


# METRIKI_INVESTORA_V1 - marker


# ══ KAZNA_V1 — после сборки картотеки (то есть после прогона) — пересчёт счетов ══
_sobrat_do_kazny = sobrat


def sobrat():   # noqa: F811
    put = _sobrat_do_kazny()
    try:
        import kazna as _kz
        n = len(_kz.sinhron_vse())
        print(f"[КАЗНА] счета работников пересчитаны: {n}")
    except Exception as e:
        print(f"[КАЗНА] счета не пересчитались ({e})")
    return put


# KAZNA_V1 - marker
