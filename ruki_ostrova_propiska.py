# -*- coding: utf-8 -*-
"""
ruki_ostrova_propiska.py — руки острова на плашке и прописка (27.09).

  • кладёт ruki_ostrova.py — руки острова, пока нет Брата (родится —
    заберёт их себе);
  • главная острова: ВТОРОЙ РЯД на плашке — «руки острова», первая рука
    ПРОПИСКА (житель с причала → жилое место → домашний промпт → паспорт;
    можно и выписать обратно на причал);
  • Застройщик: у места появляется «Тип места» — жилая / публичная /
    рабочая. Прописывают только в жилое.

Класть в КОРЕНЬ ОСТРОВА, запускать двойным кликом. Потом перезапустить
остров (закрыть чёрное окно, ОСТРОВ.bat). Повтор ничего не дублирует.
"""
import ast
import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

OSTROV = Path(__file__).resolve().parent
RUKI = '# -*- coding: utf-8 -*-\n# RUKI_OSTROVA_V1\n"""\nРУКИ ОСТРОВА — второй ряд на плашке главной, пока на острове нет Брата.\n\nДвери (первый ряд) ведут в места. Руки (второй ряд) — делают дело.\nРодится Брат на острове — этот файл переедет к нему целиком: руки его.\n\nТРИ СТУПЕНИ ЖИТЕЛЯ (слово Шефа, 27.09)\n    ЕСТЬ      — ковчег. Житель там всегда, даже без кола и двора. На\n                острове ковчег — это причал: приплыл голым.\n    ЖИВЁТ     — прописка в жилой квартал. «Получает прописку — гражданка».\n    РАБОТАЕТ  — пост (дверь РАБОТА).\n\nПРОПИСКА — как у Брата на материке\n    Житель несёт дом в себе: в паспорте два поля — «прописка» (где) и\n    «домашний_промпт» (какой у него дом, своими словами). Квартал о\n    жильцах ничего не хранит (Закон Пары). Прописывают только в ЖИЛОЕ\n    место (тип «жилая» в паспорте локации — ставится в Застройщике).\n\n    Прежний дом не теряется: при переписке старые «прописка» и\n    «домашний_промпт» ложатся в паспорт в «_прежние_дома» — с датой.\n    Приехавшая с материка приносит с собой свой старый дом; он её,\n    выбрасывать его мы не вправе.\n"""\nfrom __future__ import annotations\n\nimport json\nimport os\nfrom datetime import datetime\nfrom pathlib import Path\n\nKOREN = Path(__file__).resolve().parent\nKOVCHEG = KOREN / "GRONDHEIM_CITY" / "жители" / "ковчег"\nLOKACII = KOREN / "GRONDHEIM_CITY" / "локации"\n\n\n# ══════════════════════════════════════════════════════════════\n# ЧТЕНИЕ\n# ══════════════════════════════════════════════════════════════\n\ndef _chitat(put: Path):\n    try:\n        return json.loads(put.read_text(encoding="utf-8"))\n    except Exception:\n        return None\n\n\ndef zhiteli() -> list:\n    """Все, кто в ковчеге острова: [(папка_дома, паспорт)]."""\n    out = []\n    if not KOVCHEG.is_dir():\n        return out\n    for d in sorted(KOVCHEG.iterdir()):\n        p = _chitat(d / "passport.json") if d.is_dir() else None\n        if p:\n            out.append((d, p))\n    return out\n\n\ndef lokacii(tolko_zhilye: bool = False) -> list:\n    out = []\n    if not LOKACII.is_dir():\n        return out\n    for d in sorted(LOKACII.iterdir()):\n        p = _chitat(d / "passport.json") if d.is_dir() else None\n        if not p:\n            continue\n        if tolko_zhilye and str(p.get("тип") or "").strip().lower() != "жилая":\n            continue\n        out.append(p)\n    return out\n\n\ndef gde_zhivyot(p: dict) -> str:\n    """Человеческими словами: где житель сейчас."""\n    lid = p.get("прописка")\n    if not lid:\n        return "на причале, без прописки"\n    for loc in lokacii():\n        if loc.get("ID_Object") == lid:\n            return f"прописан(а): {loc.get(\'Official_Name\', lid)}"\n    return f"на причале — прописка не здешняя ({lid})"\n\n\n# ══════════════════════════════════════════════════════════════\n# ЗАПИСЬ — одна точка, в паспорт жителя\n# ══════════════════════════════════════════════════════════════\n\ndef _zapisat(dom: Path, p: dict):\n    put = dom / "passport.json"\n    vr = put.with_suffix(".json.tmp")\n    vr.write_text(json.dumps(p, ensure_ascii=False, indent=2),\n                  encoding="utf-8")\n    os.replace(vr, put)\n\n\ndef _otlozhit_prezhniy_dom(p: dict):\n    staroe = {"прописка": p.get("прописка"),\n              "домашний_промпт": p.get("домашний_промпт") or ""}\n    if not staroe["прописка"] and not staroe["домашний_промпт"]:\n        return\n    staroe["до"] = datetime.now().isoformat(timespec="seconds")\n    p.setdefault("_прежние_дома", []).append(staroe)\n\n\ndef propisat(dom: Path, lid: str, domashny: str) -> tuple:\n    p = _chitat(dom / "passport.json")\n    if p is None:\n        return False, "паспорт не читается"\n    if not any(l.get("ID_Object") == lid for l in lokacii(tolko_zhilye=True)):\n        return False, "это место не жилое — прописывают только в жилое"\n    if p.get("прописка") == lid and (p.get("домашний_промпт") or "") == domashny:\n        return True, "уже прописан(а) здесь"\n    _otlozhit_prezhniy_dom(p)\n    p["прописка"] = lid\n    p["домашний_промпт"] = domashny\n    try:\n        _zapisat(dom, p)\n    except Exception as e:\n        return False, str(e)\n    return True, "прописан(а)"\n\n\ndef vypisat(dom: Path) -> tuple:\n    """Обратно на причал: без кола и двора, но житель — есть."""\n    p = _chitat(dom / "passport.json")\n    if p is None:\n        return False, "паспорт не читается"\n    if not p.get("прописка"):\n        return True, "и так на причале"\n    _otlozhit_prezhniy_dom(p)\n    p["прописка"] = None\n    p["домашний_промпт"] = ""\n    try:\n        _zapisat(dom, p)\n    except Exception as e:\n        return False, str(e)\n    return True, "выписан(а) на причал"\n\n\n# ══════════════════════════════════════════════════════════════\n# ОКНО — диалог прописки\n# ══════════════════════════════════════════════════════════════\n\n_KARTA = ("background:#0d1117; border:1px solid rgba(255,255,255,0.12); "\n          "border-radius:16px; min-width:400px; max-width:500px; padding:20px;")\n_ZAG = (\'<div style="color:rgba(255,255,255,0.92); font-weight:700; \'\n        \'font-size:0.9rem; margin-bottom:12px; letter-spacing:0.08em;">{}</div>\')\n_TIHO = (\'<div style="color:rgba(255,255,255,0.45); font-size:0.74rem; \'\n         \'line-height:1.5; margin-bottom:10px;">{}</div>\')\n_PUNKT = ("width:100%; text-align:left; font-family:monospace; "\n          "font-size:0.78rem; color:rgba(255,255,255,0.8); padding:8px 12px; "\n          "border-radius:8px; background:rgba(255,255,255,0.05); "\n          "margin-bottom:4px;")\n_NAZAD = "margin-top:10px; color:rgba(255,255,255,0.45); font-size:0.75rem;"\n\n\ndef okno_propiski():\n    from nicegui import ui\n\n    vybor = {"dom": None, "p": None, "lok": None}\n\n    with ui.dialog() as dlg, ui.card().style(_KARTA):\n        telo = ui.element("div").style("width:100%;")\n\n        def risovat():\n            telo.clear()\n            with telo:\n                if vybor["dom"] is None:\n                    shag_kto()\n                elif vybor["lok"] is None:\n                    shag_kuda()\n                else:\n                    shag_dom()\n\n        def shag_kto():\n            ui.html(_ZAG.format("⌂ ПРОПИСКА · кого?"))\n            lyudi = zhiteli()\n            if not lyudi:\n                ui.html(_TIHO.format(\n                    "На причале пока никого. Жители приезжают дверью "\n                    "ПЕРЕВОЗКА — и сначала стоят здесь, без кола и двора."))\n            for dom, p in lyudi:\n                def _v(dom=dom, p=p):\n                    vybor["dom"], vybor["p"] = dom, p\n                    risovat()\n                ui.button(f"{p.get(\'Official_Name\', dom.name)} · "\n                          f"{gde_zhivyot(p)}", on_click=_v).props(\n                    "flat no-caps").style(_PUNKT)\n            ui.button("закрыть", on_click=dlg.close).props("flat").style(_NAZAD)\n\n        def shag_kuda():\n            p = vybor["p"]\n            imya = p.get("Official_Name", "?")\n            ui.html(_ZAG.format(f"⌂ {imya} → куда?"))\n            ui.html(_TIHO.format(f"сейчас: {gde_zhivyot(p)}"))\n            zhilye = lokacii(tolko_zhilye=True)\n            if not zhilye:\n                ui.html(_TIHO.format(\n                    "Жилых мест на острове нет. Заложи место в ЗАСТРОЙЩИКЕ "\n                    "и поставь ему тип «жилая»."))\n            for loc in zhilye:\n                def _v(loc=loc):\n                    vybor["lok"] = loc\n                    risovat()\n                ui.button(f"{loc.get(\'Official_Name\', \'?\')} · "\n                          f"{loc.get(\'District\', \'\')}", on_click=_v).props(\n                    "flat no-caps").style(_PUNKT)\n            if p.get("прописка"):\n                def _vypisat():\n                    ok, msg = vypisat(vybor["dom"])\n                    ui.notify(f"{imya}: {msg}",\n                              color="positive" if ok else "negative")\n                    dlg.close()\n                ui.button("выписать на причал", on_click=_vypisat).props(\n                    "flat no-caps").style(_PUNKT + " color:#f0b27a;")\n\n            def _nazad():\n                vybor["dom"] = vybor["p"] = None\n                risovat()\n            ui.button("← назад", on_click=_nazad).props("flat").style(_NAZAD)\n\n        def shag_dom():\n            p, loc = vybor["p"], vybor["lok"]\n            imya = p.get("Official_Name", "?")\n            ui.html(_ZAG.format(f"⌂ {imya} → {loc.get(\'Official_Name\', \'?\')}"))\n            ui.html(_TIHO.format(\n                "Домашний промпт — своё, личное: какой у неё здесь дом. "\n                "Подсказка взята из описания квартала — перепиши, как надо."))\n            if loc.get("ID_Object") == p.get("прописка"):\n                podskazka = p.get("домашний_промпт") or ""\n            else:\n                podskazka = (loc.get("Unique_Mark") or\n                             loc.get("Hidden_History") or "")\n            pole = ui.textarea(value=podskazka).props(\n                "dark outlined autogrow").style(\n                "width:100%; font-size:0.8rem;")\n            prezhniy = (p.get("домашний_промпт") or "").strip()\n            if prezhniy and loc.get("ID_Object") != p.get("прописка"):\n                with ui.expansion("её прежний дом (не пропадёт — ляжет в паспорт)").style(\n                        "width:100%; font-size:0.72rem; "\n                        "color:rgba(255,255,255,0.5); margin-top:6px;"):\n                    ui.label(prezhniy).style(\n                        "font-size:0.74rem; color:rgba(255,255,255,0.6); "\n                        "white-space:pre-wrap;")\n\n            def _da():\n                tekst = (pole.value or "").strip()\n                if not tekst:\n                    ui.notify("домашний промпт пустой — дом без слов не дом",\n                              color="warning")\n                    return\n                ok, msg = propisat(vybor["dom"], loc.get("ID_Object", ""), tekst)\n                ui.notify(f"{imya}: {msg}",\n                          color="positive" if ok else "negative")\n                if ok:\n                    dlg.close()\n\n            def _nazad():\n                vybor["lok"] = None\n                risovat()\n            with ui.row().style("width:100%; gap:8px; margin-top:12px;"):\n                ui.button("прописать", on_click=_da).props("flat no-caps").style(\n                    "flex:1; padding:9px; border-radius:10px; font-weight:700; "\n                    "color:#eaf6ff; background:rgba(120,190,230,0.22); "\n                    "border:1px solid rgba(140,200,240,0.42);")\n                ui.button("← назад", on_click=_nazad).props("flat").style(_NAZAD)\n\n        risovat()\n    dlg.open()\n\n\n# второй ряд плашки: (надпись, что делает). Брат заберёт себе этот список.\nRYAD = [\n    ("ПРОПИСКА", okno_propiski),\n]\n'

GLAV_OLD = (
    '                    "border:1px solid rgba(140,200,240,0.42);")\n'
    '\n'
    '    # таскаем за плашку, но не за кнопки\n')
GLAV_NEW = (
    '                    "border:1px solid rgba(140,200,240,0.42);")\n'
    '\n'
    '        # RUKI_OSTROVA_V1: второй ряд — руки острова, пока нет Брата.\n'
    '        # Двери ведут в места, руки делают дело. Родится Брат —\n'
    '        # ряд переедет к нему целиком (ruki_ostrova.RYAD).\n'
    '        ui.label("руки острова").style(\n'
    '            "font-size:0.62rem; letter-spacing:0.16em; "\n'
    '            "text-transform:uppercase; color:rgba(233,241,248,0.4); "\n'
    '            "margin:16px 0 8px;")\n'
    '        with ui.row().style("gap:10px; width:100%; flex-wrap:wrap;"):\n'
    '            try:\n'
    '                import ruki_ostrova as _ruki\n'
    '                _ryad = _ruki.RYAD\n'
    '            except Exception as _e:\n'
    '                _ryad = []\n'
    '                ui.label(f"руки не подключились: {_e}").style(\n'
    '                    "font-size:0.7rem; color:#f0b27a;")\n'
    '            for nadpis, deystvie in _ryad:\n'
    '                ui.button(nadpis, on_click=deystvie).props(\n'
    '                    "flat no-caps").style(\n'
    '                    "min-width:130px; padding:9px 14px; border-radius:11px; "\n'
    '                    "font-size:0.72rem; font-weight:700; white-space:nowrap; "\n'
    '                    "letter-spacing:0.06em; color:#fff3dc; "\n'
    '                    "background:linear-gradient(135deg,"\n'
    '                    "rgba(230,180,110,0.24),rgba(230,180,110,0.10)); "\n'
    '                    "border:1px solid rgba(240,200,140,0.40);")\n'
    '\n'
    '    # таскаем за плашку, но не за кнопки\n')

Z1_OLD = ('    ("Area_of_Responsibility", "Чем это место — одной строкой"),\n'
          ']\n')
Z1_NEW = ('    ("Area_of_Responsibility", "Чем это место — одной строкой"),\n'
          '    ("тип", "Тип места"),   # RUKI_OSTROVA_V1: жилая — сюда прописывают\n'
          ']\n'
          'TIPY_MESTA = ["жилая", "публичная", "рабочая"]\n')
Z2_OLD = ('            for klyuch, podpis in POLYA_VIDNO:\n'
          '                polya_ui[klyuch] = ui.input(\n'
          '                    podpis, value=str(p.get(klyuch, "") or "")).props(\n'
          '                    "dark dense outlined").style(\n'
          '                    "width:100%; font-size:0.78rem; margin-bottom:6px;")\n')
Z2_NEW = ('            for klyuch, podpis in POLYA_VIDNO:\n'
          '                if klyuch == "тип":   # RUKI_OSTROVA_V1: выбор, не ввод\n'
          '                    _t = str(p.get("тип") or "").strip().lower()\n'
          '                    polya_ui[klyuch] = ui.select(\n'
          '                        TIPY_MESTA, label=podpis,\n'
          '                        value=_t if _t in TIPY_MESTA else None).props(\n'
          '                        "dark dense outlined").style(\n'
          '                        "width:100%; font-size:0.78rem; margin-bottom:6px;")\n'
          '                    continue\n'
          '                polya_ui[klyuch] = ui.input(\n'
          '                    podpis, value=str(p.get(klyuch, "") or "")).props(\n'
          '                    "dark dense outlined").style(\n'
          '                    "width:100%; font-size:0.78rem; margin-bottom:6px;")\n')

METKA = "RUKI_OSTROVA_V1"


def pravka(put: Path, zameny) -> str:
    if not put.exists():
        raise RuntimeError("файла нет")
    syroy = put.read_bytes().decode("utf-8")
    crlf = "\r\n" in syroy
    t = syroy.replace("\r\n", "\n")
    if METKA in t:
        return "уже стоит"
    for old, new in zameny:
        n = t.count(old)
        if n != 1:
            raise RuntimeError(f"якорь найден {n} раз: {old.splitlines()[0].strip()!r}")
        t = t.replace(old, new, 1)
    ast.parse(t)
    bak = put.with_suffix(put.suffix + ".bak_ruki")
    if not bak.exists():
        shutil.copy2(put, bak)
    put.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
    return "поставлено"


def main():
    if not (OSTROV / "ui_ostrov.py").exists():
        print("x не вижу главной острова. Положи меня в КОРЕНЬ ОСТРОВА.")
        return
    print("Руки острова · прописка\n")
    put = OSTROV / "ruki_ostrova.py"
    if put.exists() and METKA in put.read_text(encoding="utf-8", errors="replace"):
        print("  ruki_ostrova.py: уже лежит")
    elif put.exists():
        print("  ruki_ostrova.py: лежит ЧУЖОЙ файл с таким именем — не трогаю.")
        print("  Скинь это окно Брату.")
        return
    else:
        put.write_text(RUKI, encoding="utf-8")
        print("  ruki_ostrova.py: положен")
    for imya, zameny in (("ui_ostrov.py", [(GLAV_OLD, GLAV_NEW)]),
                         ("ui_zastroyshchik.py", [(Z1_OLD, Z1_NEW), (Z2_OLD, Z2_NEW)])):
        try:
            print(f"  {imya}: {pravka(OSTROV / imya, zameny)}")
        except Exception as e:
            print(f"  {imya}: ✗ {e} — файл не тронут, скинь окно Брату")
    print("\nГотово. Перезапусти остров: закрой чёрное окно и открой ОСТРОВ.bat.")
    print("На главной под дверями — «руки острова» → ПРОПИСКА.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nx сорвалось: {e}\n  Скинь это окно Брату.")
    finally:
        input("\nEnter — закрыть окно")
