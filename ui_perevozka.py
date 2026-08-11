# -*- coding: utf-8 -*-
# PEREVOZKA_KNOPKI_V1
"""
ПЕРЕВОЗКА — сюда бросают архив с жителем.

Страница ничего не решает сама: распаковкой и посадкой занимается
perevozka.py, тот же, что работает из консоли. Здесь только руки —
принять файл и показать, куда садить.
"""
from pathlib import Path
from typing import Any

from nicegui import ui

KOREN = Path(__file__).resolve().parent
PRIBYTIE = KOREN / "_ПРИБЫТИЕ"

CSS = """
<style>
.p-page { background:#0b0f14; color:#e6edf3;
          font-family:'Inter',system-ui,sans-serif; }
.p-card { background:rgba(255,255,255,0.03); border-radius:14px;
          border:1px solid rgba(255,255,255,0.08); padding:18px;
          max-width:640px; margin:22px auto; }
.p-tihoe { color:rgba(255,255,255,0.45); font-size:0.75rem; }
</style>
"""


def _mehanizm():
    import sys
    for p in (str(KOREN), str(KOREN / "ГОРОД")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import perevozka as P
    try:
        import rabota as R
    except Exception:
        R = None
    return P, R


def page_perevozka():
    ui.add_head_html(CSS)
    ui.query("body").classes("p-page")
    sost: dict[str, Any] = {"gost": None}

    with ui.element("div").classes("p-card"):
        with ui.row().style("width:100%; align-items:center;"):
            ui.html('<div style="font-weight:800; letter-spacing:0.14em; '
                    'font-size:0.95rem;">🧳 ПЕРЕВОЗКА · ПРИЁМ</div>')
            ui.element("div").style("flex:1")
            ui.button("← НА ГЛАВНУЮ",
                      on_click=lambda: ui.navigate.to("/")).props(
                "flat no-caps").style("font-size:0.72rem; "
                                      "color:rgba(139,233,253,0.85);")

        ui.html('<div class="p-tihoe" style="margin:8px 0 14px;">'
                'Брось сюда архив, собранный на материке — файл вида '
                '«Имя_20260810_1130.zip». Человек распакуется в ковчег, и '
                'я предложу свободные места.</div>')

        telo = ui.element("div")

        def prinyat_fayl(e):
            try:
                PRIBYTIE.mkdir(exist_ok=True)
                put = PRIBYTIE / e.name
                put.write_bytes(e.content.read())
            except Exception as err:
                ui.notify(f"⚠ файл не лёг: {err}", color="negative")
                return
            P, R = _mehanizm()
            try:
                imya = P.raspakovat(put)
            except Exception as err:
                ui.notify(f"⚠ распаковать не вышло: {err}", color="negative")
                return
            if not imya:
                ui.notify("⚠ это не архив перевозки", color="negative")
                return
            try:
                (PRIBYTIE / "принято").mkdir(parents=True, exist_ok=True)
                put.replace(PRIBYTIE / "принято" / put.name)
            except Exception:
                pass
            sost["gost"] = imya
            ui.notify(f"🧳 {imya} приехал(а)", color="positive")
            risovat()

        ui.upload(on_upload=prinyat_fayl, auto_upload=True,
                  label="положить архив с жителем").props("dark flat").style(
            "width:100%; font-size:0.8rem;")

        def risovat():
            telo.clear()
            imya = sost["gost"]
            if not imya:
                return
            P, R = _mehanizm()
            with telo:
                ui.html(f'<div style="margin-top:16px; font-weight:700; '
                        f'font-size:0.9rem;">{imya} — на острове</div>')
                if R is None:
                    ui.label("механизм работы не поднялся — посади вручную"
                             ).style("color:rgba(255,180,60,0.85); "
                                     "font-size:0.78rem;")
                    return
                try:
                    svobodnye = [m for m in R.mesta()
                                 if m.get("есть_пост") and not m.get("кто_сидит")]
                except Exception as e:
                    ui.label(f"мест не вижу: {e}").style(
                        "color:rgba(255,180,60,0.85); font-size:0.78rem;")
                    return
                if not svobodnye:
                    ui.label("Свободных мест нет — посадишь позже на "
                             "странице работы.").style(
                        "color:rgba(255,255,255,0.5); font-size:0.78rem;")
                    return
                opts = {m["id"]: f'{m["название"]}  ·  {m.get("цех", "")}'
                        for m in svobodnye}
                sel = ui.select(opts, value=next(iter(opts)),
                                label="куда сажаем").props(
                    "dark dense outlined").style(
                    "width:100%; font-size:0.8rem; margin-top:10px;")

                def _posadit():
                    ok, msg = R.prinyat((sel.value or "").strip(), imya,
                                        pochemu="приехал с материка")
                    ui.notify(("🧳 " if ok else "⚠ ") + msg,
                              color="positive" if ok else "negative")
                    if ok:
                        sost["gost"] = None
                        risovat()

                ui.button("посадить", on_click=_posadit).props(
                    "flat no-caps").style(
                    "margin-top:10px; padding:8px 20px; border-radius:8px; "
                    "font-weight:700; font-size:0.8rem; color:#fff; "
                    "background:linear-gradient(135deg,rgba(80,250,123,0.28),"
                    "rgba(80,250,123,0.16)); "
                    "border:1px solid rgba(80,250,123,0.5);")

        risovat()
