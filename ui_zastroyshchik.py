# -*- coding: utf-8 -*-
# ZASTROYSHCHIK_V1
"""
ЗАСТРОЙЩИК — здесь остров обзаводится местами.

Локация тут заводится тем же паспортом, что и в городе: все поля до
единого. На виду только те, которыми место опознаётся; остальное
разложено по свёрткам, чтобы не пугать простынёй.

Списков не держим: локации читаются из папки GRONDHEIM_CITY/локации.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from nicegui import app, ui

KOREN = Path(__file__).resolve().parent
LOKACII = KOREN / "GRONDHEIM_CITY" / "локации"
KARTINKI = (".jpg", ".jpeg", ".png", ".webp")

# номера острова идут с тысячи — материковым не мешают
NACHALO_OSTROVA = 1001

# на виду
POLYA_VIDNO = [
    ("Official_Name", "Имя места"),
    ("District", "Район острова"),
    ("Area_of_Responsibility", "Чем это место — одной строкой"),
]

# под свёртками: как в городе, ничего не выброшено
SVYORTKI = [
    ("как выглядит", [
        ("Visual_Base", "Облик"),
        ("Material_Texture", "Из чего сделано"),
        ("Lighting", "Свет"),
        ("Scale", "Размах"),
        ("Style_Tags", "Метки стиля"),
    ]),
    ("чем дышит", [
        ("Unique_Mark", "Чем особенно"),
        ("Hidden_History", "Скрытая история"),
        ("Sensory_Response", "Что чувствуешь внутри"),
        ("Object_Behavior", "Как себя ведёт"),
        ("Creator_Seal", "Печать создателя"),
    ]),
    ("как устроено", [
        ("Social_Rank", "Ранг"),
        ("Profession", "Назначение"),
        ("Access_Level", "Уровень доступа"),
        ("Capacity", "Вместимость"),
        ("Interaction_Scripts", "Что здесь делают (через запятую)"),
        ("Domain_Connection", "Чей домен"),
        ("Relationships", "Связи"),
        ("Location_Connections", "Соседние места"),
    ]),
    ("где на карте", [
        ("Map_X", "X"), ("Map_Y", "Y"),
        ("Map_W", "Ширина"), ("Map_H", "Высота"),
    ]),
]

CSS = """
<style>
.z-page { background:#0b0f14; color:#e6edf3;
          font-family:'Inter',system-ui,sans-serif; }
.z-head { padding:14px 20px; border-bottom:1px solid rgba(255,255,255,0.08);
          display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
.z-title { font-weight:800; letter-spacing:0.14em; font-size:0.95rem; }
.z-tihoe { color:rgba(139,233,253,0.75); font-size:0.72rem;
           letter-spacing:0.06em; }
.z-body { display:flex; gap:16px; padding:16px 20px; align-items:flex-start; }
.z-left { width:330px; flex-shrink:0; }
.z-right { flex:1; min-width:0; }
.z-card { background:rgba(255,255,255,0.03); border-radius:14px;
          border:1px solid rgba(255,255,255,0.08); padding:14px; }
.z-podpis { color:rgba(255,255,255,0.42); font-size:0.66rem;
            letter-spacing:0.08em; text-transform:uppercase;
            margin:10px 0 4px; }
</style>
"""


def _chitat(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def lokacii() -> list:
    """Все локации острова. Списков не ведём — читаем папку."""
    out = []
    if not LOKACII.is_dir():
        return out
    for d in sorted(LOKACII.iterdir()):
        if not d.is_dir():
            continue
        p = _chitat(d / "passport.json")
        if p is None:
            continue
        out.append({"id": d.name, "имя": p.get("Official_Name", d.name),
                    "район": p.get("District", ""), "папка": d})
    return out


def _sleng(imya: str) -> str:
    """Имя латиницей для номера. Кириллицу переводим по-простому."""
    tabl = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
            "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
            "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
            "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
            "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
            "э": "e", "ю": "yu", "я": "ya"}
    s = "".join(tabl.get(c, c) for c in (imya or "").lower())
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_").upper()
    return s[:24] or "PLACE"


def novy_nomer() -> int:
    """Следующий островной номер. Материковые (с нуля) не трогаем."""
    est = []
    if LOKACII.is_dir():
        for d in LOKACII.iterdir():
            m = re.match(r"^(\d{4})_", d.name)
            if m:
                est.append(int(m.group(1)))
    svoi = [n for n in est if n >= NACHALO_OSTROVA]
    return (max(svoi) + 1) if svoi else NACHALO_OSTROVA


def zalozhit(polya: dict) -> tuple:
    """Заложить локацию: папка и паспорт, как в городе."""
    imya = (polya.get("Official_Name") or "").strip()
    if not imya:
        return False, "у места нет имени", None
    nomer = novy_nomer()
    lid = f"{nomer:04d}_{_sleng(imya)}"
    d = LOKACII / lid
    if d.exists():
        return False, f"папка {lid} уже есть", None
    teper = datetime.now()
    p = {
        "Rarity": polya.get("Rarity") or "Rare",
        "Object_Type_Class": "location",
        "ID_Object": lid,
        "Official_Name": imya,
        "Object_Type": "Location",
        "Author_Signature": "[OSTROV] застройщик",
        "Creation_Date": teper.strftime("%Y-%m-%d"),
        "_timestamp": teper.isoformat(timespec="microseconds"),
    }
    for _, spisok in [("", POLYA_VIDNO)] + [(n, s) for n, s in SVYORTKI]:
        for klyuch, _ in spisok:
            if klyuch not in p:
                p[klyuch] = polya.get(klyuch, "")
    # что здесь делают — списком, как в городе
    sk = (polya.get("Interaction_Scripts") or "").strip()
    p["Interaction_Scripts"] = [x.strip() for x in sk.split(",") if x.strip()]
    pechat = (p.get("Creator_Seal") or "").strip()
    p["_Creator_Seal_Hash"] = hashlib.sha256(
        pechat.encode("utf-8")).hexdigest() if pechat else ""
    try:
        d.mkdir(parents=True)
        (d / "passport.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return False, str(e), None
    return True, f"заложена: {lid}", lid


def sohranit(lid: str, polya: dict) -> tuple:
    put = LOKACII / lid / "passport.json"
    p = _chitat(put)
    if p is None:
        return False, "паспорта нет"
    for klyuch, znach in polya.items():
        if klyuch == "Interaction_Scripts":
            p[klyuch] = [x.strip() for x in (znach or "").split(",")
                         if x.strip()]
        else:
            p[klyuch] = znach
    pechat = (p.get("Creator_Seal") or "").strip()
    p["_Creator_Seal_Hash"] = hashlib.sha256(
        pechat.encode("utf-8")).hexdigest() if pechat else ""
    try:
        put.write_text(json.dumps(p, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    except Exception as e:
        return False, str(e)
    return True, "паспорт сохранён"


def page_zastroyshchik():
    ui.add_head_html(CSS)
    ui.query("body").classes("z-page")

    sost: dict[str, Any] = {"vybrano": None, "poisk": "", "novaya": False}
    refs: dict[str, Any] = {}

    with ui.element("div").classes("z-head"):
        ui.html('<div class="z-title">ОСТРОВ · ЗАСТРОЙЩИК</div>')
        refs["schet"] = ui.html("")
        ui.element("div").style("flex:1")
        ui.button("← НА ГЛАВНУЮ",
                  on_click=lambda: ui.navigate.to("/")).props(
            "flat no-caps").style("font-size:0.72rem; "
                                  "color:rgba(139,233,253,0.85);")

    with ui.element("div").classes("z-body"):
        with ui.element("div").classes("z-left"):
            with ui.element("div").classes("z-card"):
                poisk = ui.input(placeholder="поиск по имени…").props(
                    "dark dense outlined").style("width:100%; font-size:0.8rem;")

                def _poisk(_=None):
                    sost["poisk"] = (poisk.value or "").strip().lower()
                    risovat_spisok()

                poisk.on("keydown.enter", _poisk)
                poisk.on("blur", _poisk)

                def _novaya():
                    sost["novaya"] = True
                    sost["vybrano"] = None
                    risovat_kartu()

                ui.button("+ заложить локацию", on_click=_novaya).props(
                    "flat no-caps").style(
                    "width:100%; margin:8px 0 4px; padding:7px; "
                    "border-radius:8px; font-size:0.78rem; font-weight:700; "
                    "color:#fff; background:linear-gradient(135deg,"
                    "rgba(120,168,201,0.30),rgba(120,168,201,0.18)); "
                    "border:1px solid rgba(120,168,201,0.55);")
                refs["spisok"] = ui.element("div").style(
                    "max-height:68vh; overflow-y:auto; margin-top:6px;")

        with ui.element("div").classes("z-right"):
            refs["karta"] = ui.element("div").classes("z-card")

    def risovat_spisok():
        refs["spisok"].clear()
        vse = lokacii()
        refs["schet"].content = (f'<div class="z-tihoe">локаций острова: '
                                 f'{len(vse)}</div>')
        q = sost["poisk"]
        if q:
            vse = [m for m in vse
                   if q in (m["имя"] + m["id"] + m["район"]).lower()]
        with refs["spisok"]:
            if not vse:
                ui.label("пока пусто — заложи первую").style(
                    "color:rgba(255,255,255,0.35); font-size:0.78rem;")
                return
            for m in vse:
                def _vyb(m=m):
                    sost["novaya"] = False
                    sost["vybrano"] = m["id"]
                    risovat_kartu()

                svoya = m["id"][:4].isdigit() and \
                    int(m["id"][:4]) >= NACHALO_OSTROVA
                ui.button(f'{m["имя"]}  ·  {m["район"] or "—"}',
                          on_click=_vyb).props("flat no-caps").style(
                    f"width:100%; text-align:left; font-family:monospace; "
                    f"font-size:0.75rem; padding:6px 10px; border-radius:8px; "
                    f"background:rgba(255,255,255,0.04); margin-bottom:3px; "
                    f"color:{'rgba(80,250,123,0.85)' if svoya else 'rgba(255,255,255,0.6)'};")

    def risovat_kartu():
        refs["karta"].clear()
        lid = sost["vybrano"]
        novaya = sost["novaya"]
        with refs["karta"]:
            if not lid and not novaya:
                ui.label("Выбери локацию слева — или заложи новую.").style(
                    "color:rgba(255,255,255,0.4); font-size:0.82rem;")
                return

            p = _chitat(LOKACII / lid / "passport.json") if lid else {}
            p = p or {}

            zagolovok = ("НОВАЯ ЛОКАЦИЯ" if novaya
                         else p.get("Official_Name", lid))
            ui.html(f'<div style="font-weight:800; font-size:0.95rem; '
                    f'letter-spacing:0.06em;">{zagolovok}</div>'
                    f'<div style="color:rgba(255,255,255,0.35); '
                    f'font-size:0.68rem; font-family:monospace; '
                    f'margin-bottom:12px;">'
                    f'{lid if lid else "номер выдам сам, островной"}</div>')

            polya_ui = {}
            for klyuch, podpis in POLYA_VIDNO:
                polya_ui[klyuch] = ui.input(
                    podpis, value=str(p.get(klyuch, "") or "")).props(
                    "dark dense outlined").style(
                    "width:100%; font-size:0.78rem; margin-bottom:6px;")

            for imya_svertki, spisok in SVYORTKI:
                with ui.expansion(imya_svertki).style(
                        "width:100%; font-size:0.76rem; "
                        "color:rgba(255,255,255,0.5);"):
                    for klyuch, podpis in spisok:
                        znach = p.get(klyuch, "")
                        if isinstance(znach, list):
                            znach = ", ".join(str(x) for x in znach)
                        polya_ui[klyuch] = ui.input(
                            podpis, value=str(znach or "")).props(
                            "dark dense outlined").style(
                            "width:100%; font-size:0.78rem; margin-bottom:6px;")

            def _sobrat():
                return {k: (v.value or "").strip() for k, v in polya_ui.items()}

            def _sohranit():
                if novaya:
                    ok, msg, novy = zalozhit(_sobrat())
                    if ok:
                        sost["novaya"] = False
                        sost["vybrano"] = novy
                else:
                    ok, msg = sohranit(lid, _sobrat())
                ui.notify(("🏝 " if ok else "⚠ ") + msg,
                          color="positive" if ok else "negative")
                risovat_spisok()
                risovat_kartu()

            ui.button("заложить" if novaya else "сохранить паспорт",
                      on_click=_sohranit).props("flat no-caps").style(
                "margin-top:12px; padding:7px 20px; border-radius:8px; "
                "font-weight:700; font-size:0.8rem; color:#fff; "
                "background:linear-gradient(135deg,rgba(120,168,201,0.30),"
                "rgba(120,168,201,0.18)); "
                "border:1px solid rgba(120,168,201,0.55);")

            if novaya:
                return

            # ── картинка места ──
            ui.html('<div class="z-podpis">картинка места</div>')
            papka = LOKACII / lid
            est = [f for f in papka.iterdir()
                   if f.suffix.lower() in KARTINKI] if papka.is_dir() else []
            if est:
                try:
                    app.add_static_files(f"/лок/{lid}", str(papka))
                except Exception:
                    pass
                ui.image(f"/лок/{lid}/{est[0].name}").style(
                    "width:100%; max-width:420px; border-radius:10px;")
            else:
                ui.label("картинки нет").style(
                    "color:rgba(255,255,255,0.3); font-size:0.75rem;")

            def _prinyat_fayl(e):
                try:
                    imya = f"image{Path(e.name).suffix.lower() or '.jpg'}"
                    (papka / imya).write_bytes(e.content.read())
                    ui.notify(f"🏝 картинка легла: {imya}", color="positive")
                    risovat_kartu()
                except Exception as err:
                    ui.notify(f"⚠ {err}", color="negative")

            ui.upload(on_upload=_prinyat_fayl, auto_upload=True,
                      label="положить картинку").props("dark flat").style(
                "width:100%; font-size:0.75rem; margin-top:8px;")

    risovat_spisok()
    risovat_kartu()
