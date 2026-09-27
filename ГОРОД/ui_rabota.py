# -*- coding: utf-8 -*-
# STRANICA_RABOTY_V1
"""
СТРАНИЦА РАБОТЫ — /rabota

Дерево города слева, бланк должности справа. Списков не держит:
всё, что показано, приходит из rabota.mesta() — сканера папок.
Здесь только показ и четыре руки; вся правда живёт в постах.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nicegui import ui

import rabota as R

# BELYY_SHRIFT_V1: читаемость на тёмном — см.
# postavit_belyy_shrift.py. Красим только то, что
# рисует Quasar своей светлой темой внутри наших
# тёмных карточек.
_BELYY_SHRIFT = r"""
/* BELYY_SHRIFT_V1 — читаемость на тёмном.
   Карточки диалогов рисуем мы (тёмные), а подписи внутри — Quasar по
   своей СВЕТЛОЙ теме. Отсюда тёмно-серые буквы на чёрном: в окне
   перевозки так пропадали имена жителей у галочек.
   Красим только то, что отдано Quasar'у. Кнопки и наши собственные
   раскрашенные надписи не трогаем — у них цвет задан руками. */
.q-dialog .q-card,
.q-dialog .q-card .q-item__label,
.q-dialog .q-card label,
.q-checkbox__label,
.q-radio__label,
.q-toggle__label,
.q-field__native,
.q-field__input,
.q-field__label,
.q-field__prefix,
.q-field__suffix,
.q-item__label,
.q-tab__label,
.q-select__dropdown-icon,
.q-menu .q-item,
.q-menu .q-item__label {
  color: rgba(255,255,255,0.92) !important;
}

/* Подсказка в пустом поле — белая, но приглушённая: она не должна
   спорить с тем, что человек уже вписал. */
.q-field__native::placeholder,
.q-field__input::placeholder,
.q-placeholder::placeholder {
  color: rgba(255,255,255,0.45) !important;
}

/* Выпадающий список Quasar рисует НЕ внутри нашей карточки, а
   отдельным слоем поверх страницы — своей темой. Без этого он
   оставался светлым пятном с белым текстом на белом. */
.q-menu {
  background: #0d1117 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
}
"""


CSS = """
<style>
.rab-page { background:#0b0f14; color:#e6edf3;
            font-family:'Inter',system-ui,sans-serif; }
.rab-head { padding:14px 20px; border-bottom:1px solid rgba(255,255,255,0.08);
            display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
.rab-title { font-weight:800; letter-spacing:0.14em; font-size:0.95rem; }
.rab-schet { color:rgba(139,233,253,0.75); font-size:0.72rem;
             letter-spacing:0.06em; }
.rab-body { display:flex; gap:16px; padding:16px 20px; align-items:flex-start; }
.rab-left { width:390px; flex-shrink:0; }
.rab-right { flex:1; min-width:0; }
.rab-card { background:rgba(255,255,255,0.03); border-radius:14px;
            border:1px solid rgba(255,255,255,0.08); padding:14px; }
.rab-mesto { width:100%; text-align:left; font-family:monospace;
             font-size:0.76rem; padding:6px 10px; border-radius:8px;
             background:rgba(255,255,255,0.04); margin-bottom:3px; }
.rab-podpis { color:rgba(255,255,255,0.42); font-size:0.66rem;
              letter-spacing:0.08em; text-transform:uppercase;
              margin:10px 0 4px; }
</style>
"""

# KOROTKIY_BLANK_V1: на виду только то, что и правда пишут руками.
# Квартал, цех и слот сюда не попадают вовсе — они приходят от локации
# и картриджа, руками их писать незачем.
POLYA = [
    ("название", "Название должности"),
    ("чем_занят", "Чем занят — одной строкой"),
]

# под «подробнее» — свёрнуто, пусто по умолчанию, никого не держит
POLYA_ESHCHE = [
    ("судья", "Судья — чем меряется работа"),
    ("требования", "Требования"),
    ("условия", "Условия"),
    ("движок", "Движок (модуль, который умеет работать)"),
]


def _zhiteli() -> list:
    """Имена жителей города. Читаем паспорта, списков не держим."""
    out = []
    if not R.KOVCHEG.exists():
        return out
    for p in sorted(R.KOVCHEG.glob("*/passport.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        imya = (d.get("Official_Name") or p.parent.name).strip()
        if imya:
            out.append(imya)
    return out


# ZHITELI_V_RABOTE_V1: тип и фраза живут там же, где жили при «Роли» —
# тип в паспорте, фраза в маске работы. Новых тетрадей не заводим.
# ROL_V_RABOTU_V1: четыре типа-поста приехали сюда со снесённой
# вкладки «Роль» у Брата — библиотекарь, хранитель_архива, ректор,
# хранитель_маяка. Без них эти четверо остались бы без типа: посадить
# на пост можно во вкладке МЕСТА, а назвать — было негде.
TIPY = ["резидент", "хранитель", "воркер", "студент",
        "библиотекарь", "хранитель_архива", "ректор", "хранитель_маяка"]

# Тип «студент» — не просто слово в паспорте: он занимает место в
# Академии. Раньше это делала «Роль», теперь мы, но ТОЙ ЖЕ рукой —
# не копией. Копия завела бы вторую правду о местах Академии, а
# правда одна: GRONDHEIM_CITY/Академия/ученики.json.
def _zapisat_v_akademiyu(imya: str) -> tuple:
    """(получилось, что сказать). Место занято/мест нет — честно вернём."""
    try:
        import sys as _s
        _repo = Path(__file__).resolve().parent.parent
        for _p in (str(_repo), str(_repo / "Брат")):
            if _p not in _s.path:
                _s.path.insert(0, _p)
        # VYPUSK_V1: зачисляет РЕКТОР — одна дверь. Раньше здесь была
        # своя рука Брата, и она клала куцую запись без статуса,
        # дисциплин и поля под диплом. Оттого в реестре и был разнобой.
        _s.path.insert(0, str(_repo / "Академия"))
        import rektor
        return rektor.zachislit(imya)
    except Exception as e:
        return False, f"Академия недоступна ({e})"


def _pasport(imya: str):
    dom = R.dom_zhitelya(imya)
    if dom is None:
        return None, None
    p = dom / "passport.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")), dom
    except Exception:
        return None, dom


def _maska(dom: Path) -> dict:
    try:
        return json.loads((dom / "маски" / "работа" / "mask.json").read_text(
            encoding="utf-8"))
    except Exception:
        return {}


def _sohranit_zhitelya(imya: str, tip: str, fraza: str) -> tuple:
    p, dom = _pasport(imya)
    if p is None or dom is None:
        return False, "жителя не нашёл"
    try:
        if tip:
            p["тип"] = tip
        (dom / "passport.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        mp = dom / "маски" / "работа" / "mask.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        m = _maska(dom)
        m["_активна"] = True
        m["Core_Phrase"] = fraza
        mp.write_text(json.dumps(m, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        return True, "записано"
    except Exception as e:
        return False, str(e)


def page_rabota():
    ui.add_head_html(CSS)
    ui.add_head_html("<style>" + _BELYY_SHRIFT + "</style>")   # BELYY_SHRIFT_V1
    ui.query("body").classes("rab-page")

    sost: dict[str, Any] = {"vybrano": None, "poisk": "", "filtr": "все",
                            "rezhim": "места", "zhitel": None,
                            "vybor_kogo": None}
    refs: dict[str, Any] = {}

    # ── шапка ────────────────────────────────────────────────
    with ui.element("div").classes("rab-head"):
        ui.html('<div class="rab-title">ГРОНДХЕЙМ · РАБОТА</div>')
        refs["schet"] = ui.html("")
        # ZHITELI_V_RABOTE_V1: одна дверь, две стороны дела.
        with ui.row().style("gap:4px; margin-left:10px;"):
            for _r in ("места", "жители", "выбор"):
                def _rezhim(r=_r):
                    sost["rezhim"] = r
                    sost["vybrano"] = None
                    sost["zhitel"] = None
                    risovat_derevo()
                    risovat_kartu()
                ui.button(_r.upper(), on_click=_rezhim).props(
                    "flat no-caps").style(
                    "font-size:0.7rem; padding:3px 12px; border-radius:12px; "
                    "color:rgba(139,233,253,0.9); "
                    "background:rgba(139,233,253,0.10);")
        ui.element("div").style("flex:1")
        # STRANICA_CEHOV_V1: отсюда к картриджам Биржи
        ui.button("ЦЕХА",
                  on_click=lambda: ui.navigate.to("/ceha", new_tab=True)).props(
            "flat no-caps").style("font-size:0.72rem; "
                                  "color:rgba(139,233,253,0.85);")
        ui.button("← БРАТ", on_click=lambda: ui.navigate.to("/brat", new_tab=True)).props(
            "flat no-caps").style("font-size:0.72rem; "
                                  "color:rgba(139,233,253,0.85);")

    def obnovit_schet():
        s = R.schet()
        refs["schet"].content = (
            f'<div class="rab-schet">всего {s["всего"]} · '
            f'с должностью {s["с должностью"]} · занято {s["занято"]} · '
            f'свободно {s["свободно"]} · '
            f'без должности {s["без должности"]}</div>')

    # ── тело ─────────────────────────────────────────────────
    with ui.element("div").classes("rab-body"):
        with ui.element("div").classes("rab-left"):
            with ui.element("div").classes("rab-card"):
                poisk = ui.input(placeholder="поиск: имя, цех, слот…").props(
                    "dark dense outlined").style("width:100%; font-size:0.8rem;")

                def _poisk(_=None):
                    sost["poisk"] = (poisk.value or "").strip().lower()
                    risovat_derevo()

                poisk.on("keydown.enter", _poisk)
                poisk.on("blur", _poisk)

                with ui.row().style("gap:4px; margin:8px 0 4px; flex-wrap:wrap;"):
                    for f in ("все", "свободные", "занятые", "без должности"):
                        def _set(f=f):
                            sost["filtr"] = f
                            risovat_derevo()
                        ui.button(f, on_click=_set).props("flat no-caps").style(
                            "font-size:0.68rem; padding:3px 9px; border-radius:12px; "
                            "color:rgba(139,233,253,0.85); "
                            "background:rgba(139,233,253,0.08);")
                refs["derevo"] = ui.element("div").style(
                    "max-height:66vh; overflow-y:auto; margin-top:6px;")

        with ui.element("div").classes("rab-right"):
            refs["karta"] = ui.element("div").classes("rab-card")

    # ── дерево ───────────────────────────────────────────────
    def otobrat() -> list:
        v = R.mesta()
        q = sost["poisk"]
        if q:
            v = [m for m in v if q in (f'{m["название"]} {m["цех"]} '
                                       f'{m["слот"]} {m["кто_сидит"]}').lower()]
        f = sost["filtr"]
        if f == "свободные":
            v = [m for m in v if m["есть_пост"] and not m["кто_сидит"]]
        elif f == "занятые":
            v = [m for m in v if m["кто_сидит"]]
        elif f == "без должности":
            v = [m for m in v if not m["есть_пост"]]
        return v

    def risovat_zhiteley():
        """Список жителей города. Тот же поиск, что и по местам."""
        refs["derevo"].clear()
        gde = {}
        for m in R.mesta():
            if m["кто_сидит"]:
                gde[m["кто_сидит"]] = m["название"]
        q = sost["poisk"]
        with refs["derevo"]:
            imena = [i for i in _zhiteli() if not q or q in i.lower()]
            if not imena:
                ui.label("никого не нашлось").style(
                    "color:rgba(255,255,255,0.35); font-size:0.78rem;")
                return
            for imya in imena:
                rabota = gde.get(imya, "")
                hvost = rabota or "— без места —"
                cvet = ("rgba(80,250,123,0.85)" if rabota
                        else "rgba(255,255,255,0.5)")

                def _vyb(imya=imya):
                    sost["zhitel"] = imya
                    risovat_kartu()

                ui.button(f"{imya:<16} {hvost}", on_click=_vyb).props(
                    "flat no-caps").style(
                    f"width:100%; text-align:left; font-family:monospace; "
                    f"font-size:0.74rem; color:{cvet}; padding:5px 10px; "
                    f"border-radius:8px; background:rgba(255,255,255,0.04); "
                    f"margin-bottom:3px;")

    def risovat_vybory():
        """VYBOR_VKLADKOY_V1: что у трейдеров ЗАПИСАНО, а не сказано.

        Раньше это показывал скрипт из терминала. Место ему здесь:
        выбор входа — часть работы, и смотреть на него надо там же, где
        смотрят на места и людей.
        """
        refs["derevo"].clear()
        try:
            import sys as _s
            _b = str(Path(__file__).resolve().parent.parent / "Биржа")
            if _b not in _s.path:
                _s.path.insert(0, _b)
            import vybor as _V
        except Exception as e:
            with refs["derevo"]:
                ui.label(f"механизм выбора не поднялся: {e}").style(
                    "color:rgba(255,180,60,0.85); font-size:0.78rem;")
            return

        stroki, teksty = [], {}
        for m in R.mesta():
            if not m.get("цех") or not m.get("слот"):
                continue
            kto = m.get("кто_сидит") or ""
            if not kto:
                continue
            try:
                ist = _V.istoriya(m["цех"], m["слот"])
            except Exception:
                ist = []
            posl = ist[-1] if ist else {}
            stroki.append({"кто": kto, "место": m["название"],
                           "цех": m["цех"], "слот": m["слот"],
                           "текст": (posl.get("текст") or "").strip(),
                           "когда": str(posl.get("когда", ""))[:16],
                           "раз": len(ist)})
            if posl.get("текст"):
                teksty.setdefault(posl["текст"].strip().lower(), []).append(kto)

        with refs["derevo"]:
            if not stroki:
                ui.label("на местах никого — выбирать некому").style(
                    "color:rgba(255,255,255,0.35); font-size:0.78rem;")
                return
            for s in stroki:
                def _vyb(s=s):
                    sost["vybor_kogo"] = s
                    risovat_kartu()

                est = bool(s["текст"])
                cvet = ("rgba(80,250,123,0.85)" if est
                        else "rgba(255,180,60,0.85)")
                hvost = s["когда"] if est else "выбора нет"
                ui.button(f'{s["кто"]}  ·  {s["слот"]}  ·  {hvost}',
                          on_click=_vyb).props("flat no-caps").style(
                    f"width:100%; text-align:left; font-family:monospace; "
                    f"font-size:0.74rem; color:{cvet}; padding:5px 10px; "
                    f"border-radius:8px; background:rgba(255,255,255,0.04); "
                    f"margin-bottom:3px;")

            sovpali = {t: k for t, k in teksty.items() if len(k) > 1}
            if sovpali:
                ui.html('<div class="rab-podpis">одинаковый выбор</div>')
                for t, k in sovpali.items():
                    ui.label(f'{", ".join(k)} — «{t[:60]}»').style(
                        "color:rgba(255,180,60,0.8); font-size:0.72rem;")
                ui.label("Либо оба правда так решили, либо метка легла "
                         "не тому.").style(
                    "color:rgba(255,255,255,0.45); font-size:0.7rem;")

    def risovat_kartu_vybora():
        refs["karta"].clear()
        s = sost.get("vybor_kogo")
        with refs["karta"]:
            if not s:
                ui.label("Выбери человека слева — покажу, что у него "
                         "записано.").style(
                    "color:rgba(255,255,255,0.4); font-size:0.82rem;")
                return
            try:
                import sys as _s2
                _b = str(Path(__file__).resolve().parent.parent / "Биржа")
                if _b not in _s2.path:
                    _s2.path.insert(0, _b)
                import vybor as _V
                ist = _V.istoriya(s["цех"], s["слот"])
            except Exception as e:
                ui.label(f"не читается: {e}").style(
                    "color:rgba(255,180,60,0.85); font-size:0.8rem;")
                return

            ui.html(f'<div style="font-weight:800; font-size:0.92rem;">'
                    f'{s["кто"]}</div>'
                    f'<div style="color:rgba(255,255,255,0.35); '
                    f'font-size:0.68rem; font-family:monospace; '
                    f'margin-bottom:12px;">{s["место"]} · {s["слот"]}</div>')

            if not ist:
                ui.label("Выбора нет — метки не записано.").style(
                    "color:rgba(255,180,60,0.85); font-size:0.85rem;")
                ui.label("Значит всё, что он говорит про свой вход, взято "
                         "из книги сейчас, а не решено им однажды. Спроси "
                         "его в кабинете Биржи: «какой у тебя вход и почему "
                         "именно он твой» — и пусть объявит строкой ВЫБОР.").style(
                    "color:rgba(255,255,255,0.5); font-size:0.76rem; "
                    "margin-top:6px;")
                return

            posl = ist[-1]
            ui.label(posl.get("текст", "")).style(
                "color:rgba(80,250,123,0.9); font-size:0.86rem;")
            ui.label(f'выбрано {str(posl.get("когда",""))[:16]}').style(
                "color:rgba(255,255,255,0.45); font-size:0.72rem;")

            if len(ist) > 1:
                ui.html('<div class="rab-podpis">передумывал</div>')
                for z in reversed(ist[:-1]):
                    ui.label(f'{str(z.get("когда",""))[:16]} — '
                             f'{z.get("текст","")}').style(
                        "color:rgba(255,255,255,0.5); font-size:0.74rem; "
                        "font-family:monospace;")

    def risovat_derevo():
        obnovit_schet()
        if sost["rezhim"] == "выбор":
            risovat_vybory()
            return
        if sost["rezhim"] == "жители":
            risovat_zhiteley()
            return
        refs["derevo"].clear()
        v = otobrat()
        if not v:
            with refs["derevo"]:
                ui.label("ничего не нашлось").style(
                    "color:rgba(255,255,255,0.35); font-size:0.78rem;")
            return
        # LOKACIYA_DAYOT_MESTA_V1: дерево идёт ОТ ЛОКАЦИЙ. Локация →
        # картридж, который в ней стоит → место. Свои места локации
        # (ректор, хранитель) лежат там же, под пометкой «без цеха».
        vidno = {m["id"] for m in v}
        with refs["derevo"]:
            for L in R.po_lokaciyam():
                moi = [m for m in L["места"] if m["id"] in vidno]
                if not moi and sost["poisk"]:
                    continue
                if not moi:
                    ui.html(f'<div class="rab-podpis">{L["название"]} '
                            f'— вакансий не предлагает</div>')
                    continue
                ceha: dict = {}
                for m in moi:
                    ceha.setdefault(m["цех"] or "(места локации)", []).append(m)
                with ui.expansion(
                        f'{L["название"]}  ·  {len(moi)}'
                        f'  (занято {L["занято"]})',
                        value=bool(sost["poisk"])).style(
                        "width:100%; font-size:0.8rem;"):
                    for ceh in sorted(ceha):
                        ui.html(f'<div class="rab-podpis">{ceh}</div>')
                        for m in sorted(ceha[ceh], key=lambda x: x["слот"]):
                            if m["кто_сидит"]:
                                hvost = m["кто_сидит"]
                                cvet = "rgba(80,250,123,0.85)"
                            elif m["есть_пост"]:
                                hvost = "свободно"
                                cvet = "rgba(255,255,255,0.55)"
                            else:
                                hvost = "должности нет"
                                cvet = "rgba(255,180,60,0.8)"
                            nadpis = (f'{m["слот"] or "—":<6} '
                                      f'{m["название"][:24]:<24} {hvost}')

                            def _vybrat(m=m):
                                sost["vybrano"] = m
                                risovat_kartu()

                            ui.button(nadpis, on_click=_vybrat).props(
                                "flat no-caps").style(
                                f"width:100%; text-align:left; "
                                f"font-family:monospace; font-size:0.74rem; "
                                f"color:{cvet}; padding:5px 10px; "
                                f"border-radius:8px; "
                                f"background:rgba(255,255,255,0.04); "
                                f"margin-bottom:3px;")

    # ── карточка места ───────────────────────────────────────
    def risovat_kartu_zhitelya():
        refs["karta"].clear()
        imya = sost["zhitel"]
        with refs["karta"]:
            if imya is None:
                ui.label("Выбери человека слева.").style(
                    "color:rgba(255,255,255,0.4); font-size:0.82rem;")
                return
            p, dom = _pasport(imya)
            if p is None:
                ui.label(f"Паспорт {imya} не читается.").style(
                    "color:rgba(255,180,60,0.85); font-size:0.8rem;")
                return
            maska = _maska(dom)
            ui.html(f'<div style="font-weight:800; font-size:0.92rem; '
                    f'letter-spacing:0.06em; margin-bottom:2px;">{imya}</div>'
                    f'<div style="color:rgba(255,255,255,0.35); '
                    f'font-size:0.68rem; font-family:monospace; '
                    f'margin-bottom:12px;">{p.get("ID_Object","")}</div>')

            rab = p.get("Работа") or {}
            if rab:
                ui.label(f'Работает: {rab.get("должность","")} · '
                         f'{rab.get("где","")}').style(
                    "color:rgba(80,250,123,0.8); font-size:0.78rem; "
                    "margin-bottom:8px;")
            else:
                ui.label("Места пока нет — посадить можно во вкладке МЕСТА.").style(
                    "color:rgba(255,255,255,0.4); font-size:0.78rem; "
                    "margin-bottom:8px;")

            _tek = p.get("тип") or ""
            sel = ui.select({t: t for t in TIPY},
                            value=_tek if _tek in TIPY else None,
                            label="Кто он").props("dark dense outlined").style(
                "width:100%; font-size:0.78rem; margin-bottom:6px;")
            fr = ui.input("Коронная фраза",
                          value=maska.get("Core_Phrase", "")).props(
                "dark dense outlined").style(
                "width:100%; font-size:0.78rem;")

            def _sohr():
                _tip_novyy = (sel.value or "").strip()
                ok, msg = _sohranit_zhitelya(imya, _tip_novyy,
                                             (fr.value or "").strip())
                # ROL_V_RABOTU_V1: студент — не только слово в паспорте.
                # Раньше место в Академии занимала «Роль»; теперь мы.
                if ok and _tip_novyy == "студент":
                    ok_ak, msg_ak = _zapisat_v_akademiyu(imya)
                    msg = f"{msg} · Академия: {msg_ak}"
                    ui.notify(("🎓 " if ok_ak else "⚠ Академия: ") + msg_ak,
                              color="positive" if ok_ak else "warning")
                ui.notify(("🪑 " if ok else "⚠ ") + msg,
                          color="positive" if ok else "negative")
                risovat_derevo()
                risovat_kartu()

            ui.button("сохранить", on_click=_sohr).props(
                "flat no-caps").style(
                "margin-top:12px; padding:7px 18px; border-radius:8px; "
                "font-weight:700; font-size:0.78rem; color:#fff; "
                "background:linear-gradient(135deg,rgba(120,168,201,0.30),"
                "rgba(120,168,201,0.18)); "
                "border:1px solid rgba(120,168,201,0.55);")

    def risovat_kartu():
        if sost["rezhim"] == "выбор":
            risovat_kartu_vybora()
            return
        if sost["rezhim"] == "жители":
            risovat_kartu_zhitelya()
            return
        refs["karta"].clear()
        m = sost["vybrano"]
        with refs["karta"]:
            if m is None:
                ui.label("Выбери место слева — здесь откроется его бланк.").style(
                    "color:rgba(255,255,255,0.4); font-size:0.82rem;")
                return

            post = R.chitat(m["id"]) or {}
            est = bool(post)

            ui.html(f'<div style="font-weight:800; font-size:0.92rem; '
                    f'letter-spacing:0.06em; margin-bottom:2px;">'
                    f'{post.get("название") or m["название"]}</div>'
                    f'<div style="color:rgba(255,255,255,0.35); '
                    f'font-size:0.68rem; font-family:monospace; '
                    f'margin-bottom:12px;">id: {m["id"]}'
                    f'{"" if est else "  ·  должности ещё нет"}</div>')

            # LOKACIYA_DAYOT_MESTA_V1: локация первой строкой. У места
            # от картриджа она приходит из здания цеха и не правится —
            # иначе руками разведём здание и картридж.
            loc = R.lokacii()
            m_loc = post.get("локация") or m.get("локация") or ""
            ot_kartridzha = bool(m.get("цех"))
            ui.html('<div class="rab-podpis">локация — она и даёт это место</div>')
            if ot_kartridzha:
                ui.label(f'{loc.get(m_loc, m_loc or "— здание не указано —")}'
                         f'   ·   из картриджа {m.get("цех")}').style(
                    "color:rgba(139,233,253,0.8); font-size:0.8rem; "
                    "margin-bottom:8px;")
                sel_loc = None
            else:
                _opts = {"": "— не выбрана —"}
                _opts.update(loc)
                sel_loc = ui.select(_opts, value=m_loc if m_loc in loc else "").props(
                    "dark dense outlined").style(
                    "width:100%; font-size:0.78rem; margin-bottom:8px;")

            # KOROTKIY_BLANK_V1: где стоит — строкой, а не тремя полями.
            _gde = " · ".join(x for x in (m.get("квартал"), m.get("цех"),
                                          m.get("слот")) if x)
            if _gde:
                ui.label(_gde).style("color:rgba(255,255,255,0.4); "
                                     "font-size:0.72rem; margin-bottom:8px;")

            polya_ui = {}
            for klyuch, podpis in POLYA:
                znach = post.get(klyuch, "") if est else (
                    m["название"] if klyuch == "название" else "")
                polya_ui[klyuch] = ui.input(podpis, value=znach or "").props(
                    "dark dense outlined").style(
                    "width:100%; font-size:0.78rem; margin-bottom:6px;")

            with ui.expansion("подробнее — обязанности, судья, условия").style(
                    "width:100%; font-size:0.75rem; "
                    "color:rgba(255,255,255,0.5);"):
                for klyuch, podpis in POLYA_ESHCHE:
                    polya_ui[klyuch] = ui.input(
                        podpis, value=post.get(klyuch, "") or "").props(
                        "dark dense outlined").style(
                        "width:100%; font-size:0.78rem; margin-bottom:6px;")
                ui.html('<div class="rab-podpis">обязанности — по одной в строке</div>')
                obyaz = ui.textarea(
                    value="\n".join(post.get("обязанности", []) or [])).props(
                    "dark dense outlined").style(
                    "width:100%; font-size:0.78rem;")

            def _sobrat() -> dict:
                d = {k: (polya_ui[k].value or "").strip()
                     for k, _ in (POLYA + POLYA_ESHCHE)}
                # квартал, цех и слот не спрашиваем — берём от места
                for k in ("квартал", "цех", "слот"):
                    if m.get(k):
                        d[k] = m[k]
                d["локация"] = (m_loc if sel_loc is None
                                else (sel_loc.value or "").strip())
                d["обязанности"] = [s.strip() for s in
                                    (obyaz.value or "").splitlines() if s.strip()]
                return d

            def _sohranit():
                if est:
                    ok, msg = R.obnovit(m["id"], _sobrat())
                else:
                    ok, msg = R.zavesti(m["id"], _sobrat())
                ui.notify(("🪑 " if ok else "⚠ ") + msg,
                          color="positive" if ok else "negative")
                risovat_derevo()
                risovat_kartu()

            with ui.row().style("gap:8px; margin-top:12px; width:100%;"):
                ui.button("сохранить бланк" if est else "завести должность",
                          on_click=_sohranit).props("flat no-caps").style(
                    "padding:7px 18px; border-radius:8px; font-weight:700; "
                    "font-size:0.78rem; background:linear-gradient(135deg,"
                    "rgba(120,168,201,0.30),rgba(120,168,201,0.18)); "
                    "border:1px solid rgba(120,168,201,0.55); color:#fff;")

            if not est:
                return

            # ── кто сидит и руки ─────────────────────────────
            kto = ((post.get("кто_сидит") or {}).get("имя") or "").strip()
            ui.html('<div class="rab-podpis">кто на месте</div>')
            prich = ui.input("Причина — ляжет в трудовую историю").props(
                "dark dense outlined").style("width:100%; font-size:0.78rem;")

            if kto:
                ui.label(f"Сейчас: {kto}  ·  с {(post.get('кто_сидит') or {}).get('с','')}").style(
                    "color:rgba(80,250,123,0.85); font-size:0.82rem;")

                def _uvolit():
                    ok, msg = R.uvolit(m["id"], pochemu=(prich.value or "").strip())
                    ui.notify(("🪑 " if ok else "⚠ ") + msg,
                              color="positive" if ok else "negative")
                    risovat_derevo()
                    risovat_kartu()

                ui.button("уволить", on_click=_uvolit).props("flat no-caps").style(
                    "margin-top:8px; padding:7px 18px; border-radius:8px; "
                    "font-size:0.78rem; font-weight:700; color:#fff; "
                    "background:rgba(217,38,38,0.22); "
                    "border:1px solid rgba(217,38,38,0.55);")
            else:
                imena = _zhiteli()
                if not imena:
                    ui.label("Жителей ещё нет — роди их в Странице Жизни.").style(
                        "color:rgba(255,180,60,0.85); font-size:0.78rem;")
                else:
                    sel = ui.select({i: i for i in imena}, value=imena[0]).props(
                        "dark dense outlined").style(
                        "width:100%; font-size:0.78rem;")

                    def _prinyat():
                        ok, msg = R.prinyat(m["id"], (sel.value or "").strip(),
                                            pochemu=(prich.value or "").strip())
                        ui.notify(("🪑 " if ok else "⚠ ") + msg,
                                  color="positive" if ok else "negative")
                        risovat_derevo()
                        risovat_kartu()

                    def _snesti():
                        ok, msg = R.snesti(m["id"])
                        ui.notify(("🪑 " if ok else "⚠ ") + msg,
                                  color="positive" if ok else "negative")
                        if ok:
                            sost["vybrano"] = None
                        risovat_derevo()
                        risovat_kartu()

                    with ui.row().style("gap:8px; margin-top:8px;"):
                        ui.button("принять", on_click=_prinyat).props(
                            "flat no-caps").style(
                            "padding:7px 18px; border-radius:8px; "
                            "font-weight:700; font-size:0.78rem; color:#fff; "
                            "background:linear-gradient(135deg,"
                            "rgba(80,250,123,0.28),rgba(80,250,123,0.16)); "
                            "border:1px solid rgba(80,250,123,0.5);")
                        ui.button("снести должность", on_click=_snesti).props(
                            "flat no-caps").style(
                            "padding:7px 14px; border-radius:8px; "
                            "font-size:0.74rem; color:rgba(255,255,255,0.5); "
                            "border:1px solid rgba(255,255,255,0.18);")

            # ── трудовая история ─────────────────────────────
            ist = post.get("трудовая_история", []) or []
            ui.html('<div class="rab-podpis">трудовая история</div>')
            if not ist:
                ui.label("пусто — здесь ещё никто не работал").style(
                    "color:rgba(255,255,255,0.3); font-size:0.75rem;")
            else:
                with ui.element("div").style(
                        "max-height:170px; overflow-y:auto; "
                        "font-family:monospace; font-size:0.72rem; "
                        "color:rgba(255,255,255,0.55);"):
                    for z in reversed(ist):
                        pch = f' — {z.get("почему")}' if z.get("почему") else ""
                        ui.label(f'{z.get("когда","")}  {z.get("что","")}: '
                                 f'{z.get("кто","")} (кем: {z.get("кем","")}){pch}')

    risovat_derevo()
    risovat_kartu()

# LOKACIYA_DAYOT_MESTA_V1 - marker

# KOROTKIY_BLANK_V1 - marker

# ZHITELI_V_RABOTE_V1 - marker

# SVOYO_OKNO_V1 - marker

# INSTRUMENT_NAZNACHIT_ILI_SAM_V1 - marker

# PANEL_TREYDERA_V1 - marker

# VYBOR_VKLADKOY_V1 - marker

# ROL_V_RABOTU_V1 - marker

# VYPUSK_V1 - marker
