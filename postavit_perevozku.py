#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PEREVOZKA_KNOPKI_V1
"""
ПЕРЕВОЗКА КНОПКОЙ — на материке у Брата, на острове в плашке.

    python postavit_perevozku.py            посмотреть
    python postavit_perevozku.py --sdelat   поставить

Запускать из КОРНЯ — материка или острова. Сам разберётся, где он, и
поставит нужную сторону.

ЧТО МЕНЯЕТСЯ

    Отдельный `ПЕРЕВОЗКА.bat` больше не нужен.

    НА МАТЕРИКЕ у Брата в нижнем ряду, рядом с «Тик» и «Работа»,
    появляется «Перевозка». Открывается список жителей, отмечаешь кого
    везти, жмёшь «упаковать» — человек снимается с места (личное едет
    к нему домой само) и ложится архивом в `_ОТПРАВКА/`.

    НА ОСТРОВЕ в плашке появляется четвёртая дверь — «ПЕРЕВОЗКА». За
    ней страница, куда архив просто бросают мышью. Дальше остров сам
    распаковывает человека и предлагает свободные места: выбрал —
    посажен.

    Файл `perevozka.py` остаётся: кнопки зовут именно его, чтобы не
    заводить вторую правду о том, что и как едет. Из консоли он тоже
    по-прежнему работает.
"""
import argparse
import ast
import py_compile
import shutil
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

KOREN = Path(__file__).resolve().parent
BRAT = KOREN / "Брат" / "ui_brat.py"
OSTROV_MAIN = KOREN / "ostrov_main.py"
STRANICA = KOREN / "ui_perevozka.py"
GLAVNAYA = KOREN / "ui_ostrov.py"
MARKER = "# PEREVOZKA_KNOPKI_V1 - marker"
BAK = ".bak_perevozka"


def eto_ostrov() -> bool:
    return (KOREN / "ostrov_puls.py").is_file() or \
           (KOREN / "OSTROV_NADEZHDY.md").is_file()


# ══════════════════════════════════════════════════════════════
# МАТЕРИК — кнопка у Брата
# ══════════════════════════════════════════════════════════════

STAROE_BRAT_FUNC = '''    async def do_tik():
'''
NOVOE_BRAT_FUNC = '''    async def do_perevozka():
        """PEREVOZKA_KNOPKI_V1: собрать жителя в дорогу на остров.

        Руками ничего не пакуем: зовём perevozka.py, тот же, что работает
        из консоли. Две правды о том, что едет, нам не нужны.
        """
        try:
            import sys as _sys
            _k = str(_REPO_ROOT_FOR_IMPORT)
            if _k not in _sys.path:
                _sys.path.insert(0, _k)
            _g = str(_REPO_ROOT_FOR_IMPORT / "ГОРОД")
            if _g not in _sys.path:
                _sys.path.insert(0, _g)
            import perevozka as P
            try:
                import rabota as R
            except Exception:
                R = None
        except Exception as e:
            ui.notify(f"⚠ перевозка не поднялась: {e}", color="negative")
            return

        lyudi = P.zhiteli()
        if not lyudi:
            ui.notify("Жителей не нашёл", color="warning")
            return

        otmecheny: dict = {}

        with ui.dialog() as dlg, ui.card().style(
            "background:#0d1117; border:1px solid rgba(255,255,255,0.12); "
            "border-radius:16px; min-width:420px; max-width:520px; padding:20px;"
        ):
            ui.html('<div style="color:rgba(255,255,255,0.9); font-weight:700; '
                    'font-size:0.9rem; margin-bottom:6px; letter-spacing:0.08em;">'
                    '🧳 ПЕРЕВОЗКА НА ОСТРОВ</div>')
            ui.html('<div style="color:rgba(255,255,255,0.45); '
                    'font-size:0.72rem; margin-bottom:12px;">'
                    'Кого отметишь — тот снимется с места и ляжет архивом '
                    'в папку _ОТПРАВКА. Личное уедет с ним.</div>')

            with ui.element("div").style("max-height:46vh; overflow-y:auto;"):
                for ch in lyudi:
                    gde = ch["работа"] or "— без места —"
                    otmecheny[ch["имя"]] = ui.checkbox(
                        f'{ch["имя"]}   ·   {gde}').props("dark dense").style(
                        "font-size:0.78rem;")

            itog = ui.html("")

            def _upakovat():
                vybor = [ch for ch in lyudi
                         if otmecheny[ch["имя"]].value]
                if not vybor:
                    ui.notify("Никого не отметил", color="warning")
                    return
                gotovo = []
                for ch in vybor:
                    try:
                        a = P.upakovat(ch, R)
                        if a:
                            gotovo.append(a.name)
                    except Exception as e:
                        ui.notify(f"⚠ {ch['имя']}: {e}", color="negative")
                if gotovo:
                    itog.content = (
                        '<div style="color:rgba(80,250,123,0.85); '
                        'font-size:0.75rem; margin-top:10px;">Собрано: '
                        + "<br>".join(gotovo) +
                        '<br><br>Лежит в папке _ОТПРАВКА. Перенеси файл на '
                        'остров и брось его там на странице перевозки.</div>')
                    ui.notify(f"🧳 собрано архивов: {len(gotovo)}",
                              color="positive")

            with ui.row().style("gap:8px; margin-top:14px; width:100%;"):
                ui.button("закрыть", on_click=dlg.close).props("flat").style(
                    "color:rgba(255,255,255,0.4); font-size:0.75rem;")
                ui.element("div").style("flex:1")
                ui.button("упаковать", on_click=_upakovat).props(
                    "flat no-caps").style(
                    "padding:8px 20px; border-radius:8px; font-weight:700; "
                    "font-size:0.8rem; color:#fff; "
                    "background:linear-gradient(135deg,rgba(201,168,76,0.30),"
                    "rgba(201,168,76,0.18)); "
                    "border:1px solid rgba(201,168,76,0.55);")
        dlg.open()

    async def do_tik():
'''

STAROE_BRAT_KNOPKA = '''                        ui.button("Работа",
                                  on_click=lambda: ui.navigate.to("/rabota")
                                  ).props("flat").classes("brat-gate")
'''
NOVOE_BRAT_KNOPKA = '''                        ui.button("Работа",
                                  on_click=lambda: ui.navigate.to("/rabota")
                                  ).props("flat").classes("brat-gate")
                        # PEREVOZKA_KNOPKI_V1: собрать жителя в дорогу
                        ui.button("Перевозка",
                                  on_click=do_perevozka
                                  ).props("flat").classes("brat-gate")
'''


# ══════════════════════════════════════════════════════════════
# ОСТРОВ — страница приёма
# ══════════════════════════════════════════════════════════════

UI_PEREVOZKA = r'''# -*- coding: utf-8 -*-
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
'''

STAROE_OSTROV_MAIN = '''@ui.page("/rabota")
def _rabota():
    page_rabota()
'''
NOVOE_OSTROV_MAIN = '''@ui.page("/rabota")
def _rabota():
    page_rabota()


# PEREVOZKA_KNOPKI_V1 — сюда бросают архив с жителем
from ui_perevozka import page_perevozka   # noqa: E402


@ui.page("/perevozka")
def _perevozka():
    page_perevozka()
'''

STAROE_DVERI = '''            for nadpis, kuda in (("МАЯК", "/mayak"), ("РАБОТА", "/rabota"),
                                 ("ЗАСТРОЙЩИК", "/zastroyshchik")):'''
NOVOE_DVERI = '''            for nadpis, kuda in (("МАЯК", "/mayak"), ("РАБОТА", "/rabota"),
                                 ("ЗАСТРОЙЩИК", "/zastroyshchik"),
                                 ("ПЕРЕВОЗКА", "/perevozka")):'''


def proverit_python(tekst: str, imya: str) -> bool:
    try:
        ast.parse(tekst)
    except SyntaxError as e:
        print(f"  x {imya}: синтаксис сломан ({e}) — НЕ пишу")
        return False
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(tekst)
        vrem = f.name
    try:
        py_compile.compile(vrem, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"  x {imya}: не компилируется ({e}) — НЕ пишу")
        return False
    finally:
        Path(vrem).unlink(missing_ok=True)


def pravit(put: Path, stezhki, suho: bool) -> bool:
    if not put.exists():
        print(f"  x нет {put.name}")
        return False
    tekst = put.read_text(encoding="utf-8")
    if MARKER in tekst:
        print(f"  {put.name}: уже накатано")
        return True
    for nazv, staroe, novoe in stezhki:
        n = tekst.count(staroe)
        if n != 1:
            print(f"  x {put.name}: якорь «{nazv}» найден {n} раз — не трогаю")
            return False
        tekst = tekst.replace(staroe, novoe, 1)
        print(f"    · {nazv}")
    tekst = tekst.rstrip("\n") + "\n\n" + MARKER + "\n"
    if not proverit_python(tekst, put.name):
        return False
    if suho:
        print(f"  {put.name}: + готов")
        return True
    shutil.copy2(put, put.with_suffix(put.suffix + BAK))
    put.write_text(tekst, encoding="utf-8")
    print(f"  {put.name}: + накатано")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdelat", action="store_true")
    a = ap.parse_args()
    suho = not a.sdelat

    ostrov = eto_ostrov()
    print("=" * 60)
    print("ПЕРЕВОЗКА КНОПКОЙ · " + ("ОСТРОВ" if ostrov else "МАТЕРИК") +
          ("   [СУХОЙ ПРОГОН]" if suho else ""))
    print("=" * 60)

    if not (KOREN / "perevozka.py").exists():
        print("x рядом нет perevozka.py — положи его сюда, кнопки зовут его")
        return 1

    if ostrov:
        if not OSTROV_MAIN.exists():
            print("x не вижу ostrov_main.py")
            return 1
        print("\nстраница приёма:")
        if not proverit_python(UI_PEREVOZKA, "ui_perevozka.py"):
            return 1
        print(f"  ui_perevozka.py: "
              f"{'обновится' if STRANICA.exists() else 'ляжет'}")
        if not suho:
            STRANICA.write_text(UI_PEREVOZKA, encoding="utf-8")
        print("\nмаршрут:")
        if not pravit(OSTROV_MAIN, (("маршрут /perevozka", STAROE_OSTROV_MAIN,
                                     NOVOE_OSTROV_MAIN),), suho):
            return 1
        print("\nчетвёртая дверь в плашке:")
        if GLAVNAYA.exists():
            t = GLAVNAYA.read_text(encoding="utf-8")
            if "ПЕРЕВОЗКА" in t:
                print("  ui_ostrov.py: дверь уже есть")
            elif t.count(STAROE_DVERI) == 1 and not suho:
                shutil.copy2(GLAVNAYA, GLAVNAYA.with_suffix(
                    GLAVNAYA.suffix + BAK))
                GLAVNAYA.write_text(t.replace(STAROE_DVERI, NOVOE_DVERI, 1),
                                    encoding="utf-8")
                print("  ui_ostrov.py: + дверь добавлена")
            elif t.count(STAROE_DVERI) == 1:
                print("  ui_ostrov.py: + дверь добавится")
            else:
                print("  ! ряд дверей не узнал — поправь postavit_glavnuyu.py")
        else:
            print("  ui_ostrov.py пока нет — поставь главную, дверь придёт с ней")
    else:
        print("\nкнопка у Брата:")
        if not pravit(BRAT, (("дверь перевозки", STAROE_BRAT_FUNC,
                              NOVOE_BRAT_FUNC),
                             ("кнопка в нижнем ряду", STAROE_BRAT_KNOPKA,
                              NOVOE_BRAT_KNOPKA)), suho):
            return 1

    print("\n" + "-" * 60)
    if suho:
        print("Это был показ. Ставить: python postavit_perevozku.py --sdelat")
        return 0
    if ostrov:
        print("Готово. На главной четвёртая дверь — ПЕРЕВОЗКА.")
        print("Бросаешь туда архив мышью, дальше остров сам.")
    else:
        print("Готово. У Брата в нижнем ряду — «Перевозка».")
        print("Отдельный ПЕРЕВОЗКА.bat больше не нужен, можешь убрать.")
    return 0


if __name__ == "__main__":
    _kod = main()
    if sys.platform == "win32" and len(sys.argv) == 1:
        try:
            input("\nготово. Enter — закрыть окно.")
        except Exception:
            pass
    sys.exit(_kod)
