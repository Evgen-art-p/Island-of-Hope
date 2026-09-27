# -*- coding: utf-8 -*-
"""
zhilyo_kvartala.py — жильё квартала + её слова (27.09).

Домашний промпт жителя теперь складывается из двух половин:
  • ЖИЛЬЁ — одинаковое для всех, кто прописан в квартале (служебная
    квартира в торговом, лофт у мастеров, комната при конторе). Лежит в
    паспорте самого места, поле «жильё». Описал раз — подставится каждому.
  • ЕЁ СЛОВА — что житель привёз с собой, как обживается. Из разговора
    Шефа с ним перед переездом.

Что правит:
  • ОСТРОВ: руки острова (окно ПРОПИСКА — два поля вместо одного),
    Застройщик — поле «Жильё» у места;
  • МАТЕРИК: прописка у Брата — те же два поля (Квартал Мастеров и
    любой жилой квартал материка).

Класть в КОРЕНЬ ОСТРОВА, запускать двойным кликом. Материк найдёт сам.
Потом перезапустить и остров, и город. Повтор ничего не дублирует.
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
METKA = "ZHILYO_KVARTALA_V1"
RUKI_V2 = '# -*- coding: utf-8 -*-\n# RUKI_OSTROVA_V1\n# RUKI_OSTROVA_V2: жильё квартала + её слова (27.09)\n"""\nРУКИ ОСТРОВА — второй ряд на плашке главной, пока на острове нет Брата.\n\nДвери (первый ряд) ведут в места. Руки (второй ряд) — делают дело.\nРодится Брат на острове — этот файл переедет к нему целиком: руки его.\n\nТРИ СТУПЕНИ ЖИТЕЛЯ (слово Шефа, 27.09)\n    ЕСТЬ      — ковчег. Житель там всегда, даже без кола и двора. На\n                острове ковчег — это причал: приплыл голым.\n    ЖИВЁТ     — прописка в жилой квартал. «Получает прописку — гражданка».\n    РАБОТАЕТ  — пост (дверь РАБОТА).\n\nПРОПИСКА — как у Брата на материке\n    Житель несёт дом в себе: в паспорте два поля — «прописка» (где) и\n    «домашний_промпт» (какой у него дом, своими словами). Квартал о\n    жильцах ничего не хранит (Закон Пары). Прописывают только в ЖИЛОЕ\n    место (тип «жилая» в паспорте локации — ставится в Застройщике).\n\n    ДОМАШНИЙ ПРОМПТ = ЖИЛЬЁ + ЕЁ СЛОВА (слово Шефа, 27.09)\n    Жильё в квартале одинаковое для всех, кто там прописан — служебная\n    квартира в торговом, лофт у мастеров, комната при конторе. Оно\n    хранится в паспорте ЛОКАЦИИ, поле «жильё»: описал раз — подставится\n    каждому новому жильцу. Своё житель приносит сам: Шеф спрашивает\n    перед переездом «что возьмёшь с собой?» — её слова и есть вторая\n    половина дома.\n\n    Прежний дом не теряется: при переписке старые «прописка» и\n    «домашний_промпт» ложатся в паспорт в «_прежние_дома» — с датой.\n    Приехавшая с материка приносит с собой свой старый дом; он её,\n    выбрасывать его мы не вправе.\n"""\nfrom __future__ import annotations\n\nimport json\nimport os\nfrom datetime import datetime\nfrom pathlib import Path\n\nKOREN = Path(__file__).resolve().parent\nKOVCHEG = KOREN / "GRONDHEIM_CITY" / "жители" / "ковчег"\nLOKACII = KOREN / "GRONDHEIM_CITY" / "локации"\n\n\n# ══════════════════════════════════════════════════════════════\n# ЧТЕНИЕ\n# ══════════════════════════════════════════════════════════════\n\ndef _chitat(put: Path):\n    try:\n        return json.loads(put.read_text(encoding="utf-8"))\n    except Exception:\n        return None\n\n\ndef zhiteli() -> list:\n    """Все, кто в ковчеге острова: [(папка_дома, паспорт)]."""\n    out = []\n    if not KOVCHEG.is_dir():\n        return out\n    for d in sorted(KOVCHEG.iterdir()):\n        p = _chitat(d / "passport.json") if d.is_dir() else None\n        if p:\n            out.append((d, p))\n    return out\n\n\ndef lokacii(tolko_zhilye: bool = False) -> list:\n    out = []\n    if not LOKACII.is_dir():\n        return out\n    for d in sorted(LOKACII.iterdir()):\n        p = _chitat(d / "passport.json") if d.is_dir() else None\n        if not p:\n            continue\n        if tolko_zhilye and str(p.get("тип") or "").strip().lower() != "жилая":\n            continue\n        out.append(p)\n    return out\n\n\ndef gde_zhivyot(p: dict) -> str:\n    """Человеческими словами: где житель сейчас."""\n    lid = p.get("прописка")\n    if not lid:\n        return "на причале, без прописки"\n    for loc in lokacii():\n        if loc.get("ID_Object") == lid:\n            return f"прописан(а): {loc.get(\'Official_Name\', lid)}"\n    return f"на причале — прописка не здешняя ({lid})"\n\n\n# ══════════════════════════════════════════════════════════════\n# ЗАПИСЬ — одна точка, в паспорт жителя\n# ══════════════════════════════════════════════════════════════\n\ndef _zapisat(dom: Path, p: dict):\n    put = dom / "passport.json"\n    vr = put.with_suffix(".json.tmp")\n    vr.write_text(json.dumps(p, ensure_ascii=False, indent=2),\n                  encoding="utf-8")\n    os.replace(vr, put)\n\n\ndef _otlozhit_prezhniy_dom(p: dict):\n    staroe = {"прописка": p.get("прописка"),\n              "домашний_промпт": p.get("домашний_промпт") or ""}\n    if not staroe["прописка"] and not staroe["домашний_промпт"]:\n        return\n    staroe["до"] = datetime.now().isoformat(timespec="seconds")\n    p.setdefault("_прежние_дома", []).append(staroe)\n\n\ndef propisat(dom: Path, lid: str, domashny: str) -> tuple:\n    p = _chitat(dom / "passport.json")\n    if p is None:\n        return False, "паспорт не читается"\n    if not any(l.get("ID_Object") == lid for l in lokacii(tolko_zhilye=True)):\n        return False, "это место не жилое — прописывают только в жилое"\n    if p.get("прописка") == lid and (p.get("домашний_промпт") or "") == domashny:\n        return True, "уже прописан(а) здесь"\n    _otlozhit_prezhniy_dom(p)\n    p["прописка"] = lid\n    p["домашний_промпт"] = domashny\n    try:\n        _zapisat(dom, p)\n    except Exception as e:\n        return False, str(e)\n    return True, "прописан(а)"\n\n\ndef zapisat_zhilyo(lid: str, tekst: str) -> tuple:\n    """Жильё квартала — свойство самого места, одно на всех жильцов."""\n    put = LOKACII / lid / "passport.json"\n    p = _chitat(put)\n    if p is None:\n        return False, "паспорт места не читается"\n    if (p.get("жильё") or "") == tekst:\n        return True, "жильё то же"\n    p["жильё"] = tekst\n    try:\n        vr = put.with_suffix(".json.tmp")\n        vr.write_text(json.dumps(p, ensure_ascii=False, indent=2),\n                      encoding="utf-8")\n        os.replace(vr, put)\n    except Exception as e:\n        return False, str(e)\n    return True, "жильё квартала описано"\n\n\ndef sobrat_dom(zhilyo: str, svoyo: str) -> str:\n    """Домашний промпт: жильё квартала, потом её слова."""\n    chasti = [x.strip() for x in (zhilyo, svoyo) if x and x.strip()]\n    return "\\n\\n".join(chasti)\n\n\ndef vypisat(dom: Path) -> tuple:\n    """Обратно на причал: без кола и двора, но житель — есть."""\n    p = _chitat(dom / "passport.json")\n    if p is None:\n        return False, "паспорт не читается"\n    if not p.get("прописка"):\n        return True, "и так на причале"\n    _otlozhit_prezhniy_dom(p)\n    p["прописка"] = None\n    p["домашний_промпт"] = ""\n    try:\n        _zapisat(dom, p)\n    except Exception as e:\n        return False, str(e)\n    return True, "выписан(а) на причал"\n\n\n# ══════════════════════════════════════════════════════════════\n# ОКНО — диалог прописки\n# ══════════════════════════════════════════════════════════════\n\n_KARTA = ("background:#0d1117; border:1px solid rgba(255,255,255,0.12); "\n          "border-radius:16px; min-width:400px; max-width:500px; padding:20px;")\n_ZAG = (\'<div style="color:rgba(255,255,255,0.92); font-weight:700; \'\n        \'font-size:0.9rem; margin-bottom:12px; letter-spacing:0.08em;">{}</div>\')\n_TIHO = (\'<div style="color:rgba(255,255,255,0.45); font-size:0.74rem; \'\n         \'line-height:1.5; margin-bottom:10px;">{}</div>\')\n_PUNKT = ("width:100%; text-align:left; font-family:monospace; "\n          "font-size:0.78rem; color:rgba(255,255,255,0.8); padding:8px 12px; "\n          "border-radius:8px; background:rgba(255,255,255,0.05); "\n          "margin-bottom:4px;")\n_NAZAD = "margin-top:10px; color:rgba(255,255,255,0.45); font-size:0.75rem;"\n\n\ndef okno_propiski():\n    from nicegui import ui\n\n    vybor = {"dom": None, "p": None, "lok": None}\n\n    with ui.dialog() as dlg, ui.card().style(_KARTA):\n        telo = ui.element("div").style("width:100%;")\n\n        def risovat():\n            telo.clear()\n            with telo:\n                if vybor["dom"] is None:\n                    shag_kto()\n                elif vybor["lok"] is None:\n                    shag_kuda()\n                else:\n                    shag_dom()\n\n        def shag_kto():\n            ui.html(_ZAG.format("⌂ ПРОПИСКА · кого?"))\n            lyudi = zhiteli()\n            if not lyudi:\n                ui.html(_TIHO.format(\n                    "На причале пока никого. Жители приезжают дверью "\n                    "ПЕРЕВОЗКА — и сначала стоят здесь, без кола и двора."))\n            for dom, p in lyudi:\n                def _v(dom=dom, p=p):\n                    vybor["dom"], vybor["p"] = dom, p\n                    risovat()\n                ui.button(f"{p.get(\'Official_Name\', dom.name)} · "\n                          f"{gde_zhivyot(p)}", on_click=_v).props(\n                    "flat no-caps").style(_PUNKT)\n            ui.button("закрыть", on_click=dlg.close).props("flat").style(_NAZAD)\n\n        def shag_kuda():\n            p = vybor["p"]\n            imya = p.get("Official_Name", "?")\n            ui.html(_ZAG.format(f"⌂ {imya} → куда?"))\n            ui.html(_TIHO.format(f"сейчас: {gde_zhivyot(p)}"))\n            zhilye = lokacii(tolko_zhilye=True)\n            if not zhilye:\n                ui.html(_TIHO.format(\n                    "Жилых мест на острове нет. Заложи место в ЗАСТРОЙЩИКЕ "\n                    "и поставь ему тип «жилая»."))\n            for loc in zhilye:\n                def _v(loc=loc):\n                    vybor["lok"] = loc\n                    risovat()\n                ui.button(f"{loc.get(\'Official_Name\', \'?\')} · "\n                          f"{loc.get(\'District\', \'\')}", on_click=_v).props(\n                    "flat no-caps").style(_PUNKT)\n            if p.get("прописка"):\n                def _vypisat():\n                    ok, msg = vypisat(vybor["dom"])\n                    ui.notify(f"{imya}: {msg}",\n                              color="positive" if ok else "negative")\n                    dlg.close()\n                ui.button("выписать на причал", on_click=_vypisat).props(\n                    "flat no-caps").style(_PUNKT + " color:#f0b27a;")\n\n            def _nazad():\n                vybor["dom"] = vybor["p"] = None\n                risovat()\n            ui.button("← назад", on_click=_nazad).props("flat").style(_NAZAD)\n\n        def shag_dom():\n            p, loc = vybor["p"], vybor["lok"]\n            imya = p.get("Official_Name", "?")\n            lid = loc.get("ID_Object", "")\n            ui.html(_ZAG.format(f"⌂ {imya} → {loc.get(\'Official_Name\', \'?\')}"))\n\n            ui.html(_TIHO.format(\n                "<b>Жильё здесь</b> — одинаковое для всех, кто прописан в этом "\n                "квартале. Хранится в самом квартале: опишешь раз — "\n                "подставится каждому следующему."))\n            pole_zh = ui.textarea(value=loc.get("жильё") or "").props(\n                "dark outlined autogrow").style(\n                "width:100%; font-size:0.8rem;")\n            if not (loc.get("жильё") or "").strip():\n                pole_zh.props(\'placeholder="какое жильё получает здесь каждый…"\')\n\n            ui.html(_TIHO.format(\n                "<b>Её слова</b> — что она привезла с собой, как обживается. "\n                "Из твоего разговора с ней перед переездом."))\n            pole_svoyo = ui.textarea(value="").props(\n                \'dark outlined autogrow placeholder="что возьмёшь с собой?…"\'\n            ).style("width:100%; font-size:0.8rem;")\n\n            prezhniy = (p.get("домашний_промпт") or "").strip()\n            if prezhniy:\n                with ui.expansion("её нынешний дом (не пропадёт — ляжет в паспорт)").style(\n                        "width:100%; font-size:0.72rem; "\n                        "color:rgba(255,255,255,0.5); margin-top:6px;"):\n                    ui.label(prezhniy).style(\n                        "font-size:0.74rem; color:rgba(255,255,255,0.6); "\n                        "white-space:pre-wrap;")\n\n            def _da():\n                zhilyo = (pole_zh.value or "").strip()\n                svoyo = (pole_svoyo.value or "").strip()\n                if not zhilyo and not svoyo:\n                    ui.notify("дом без слов не дом — опиши жильё или её слова",\n                              color="warning")\n                    return\n                if zhilyo != (loc.get("жильё") or "").strip():\n                    ok_z, msg_z = zapisat_zhilyo(lid, zhilyo)\n                    if not ok_z:\n                        ui.notify(f"жильё квартала: {msg_z}", color="negative")\n                        return\n                ok, msg = propisat(vybor["dom"], lid, sobrat_dom(zhilyo, svoyo))\n                ui.notify(f"{imya}: {msg}",\n                          color="positive" if ok else "negative")\n                if ok:\n                    dlg.close()\n\n            def _nazad():\n                vybor["lok"] = None\n                risovat()\n            with ui.row().style("width:100%; gap:8px; margin-top:12px;"):\n                ui.button("прописать", on_click=_da).props("flat no-caps").style(\n                    "flex:1; padding:9px; border-radius:10px; font-weight:700; "\n                    "color:#eaf6ff; background:rgba(120,190,230,0.22); "\n                    "border:1px solid rgba(140,200,240,0.42);")\n                ui.button("← назад", on_click=_nazad).props("flat").style(_NAZAD)\n\n        risovat()\n    dlg.open()\n\n\n# второй ряд плашки: (надпись, что делает). Брат заберёт себе этот список.\nRYAD = [\n    ("ПРОПИСКА", okno_propiski),\n]\n'

Z1_OLD = '    ("тип", "Тип места"),   # RUKI_OSTROVA_V1: жилая — сюда прописывают\n'
Z1_NEW = (Z1_OLD +
          '    ("жильё", "Жильё — какое получает здесь каждый (для жилых мест)"),'
          '   # ZHILYO_KVARTALA_V1\n')
Z2_OLD = '                if klyuch == "тип":   # RUKI_OSTROVA_V1: выбор, не ввод\n'
Z2_NEW = ('                if klyuch == "жильё":   # ZHILYO_KVARTALA_V1: длинное — полем\n'
          '                    polya_ui[klyuch] = ui.textarea(\n'
          '                        podpis, value=str(p.get("жильё") or "")).props(\n'
          '                        "dark dense outlined autogrow").style(\n'
          '                        "width:100%; font-size:0.78rem; margin-bottom:6px;")\n'
          '                    continue\n' + Z2_OLD)

BRAT_OLD = '                        suggestion = (pick["lokacia"].get("Unique_Mark")\n                                      or pick["lokacia"].get("Hidden_History") or "")\n                        ui.html(f\'<div style="color:rgba(255,255,255,0.9); font-weight:700; \'\n                                f\'font-size:0.9rem; margin-bottom:10px; letter-spacing:0.08em;">\'\n                                f\'⌂ {zn} → {ln}</div>\')\n                        ui.html(\'<div style="color:rgba(255,255,255,0.45); font-size:0.68rem; \'\n                                \'margin-bottom:6px; text-transform:uppercase; letter-spacing:0.06em;">\'\n                                \'домашний промпт — своё, личное</div>\')\n                        ta = ui.textarea(value=suggestion).props("dark outlined").style(\n                            "width:100%; font-size:0.8rem;")\n\n                        async def _confirm():\n                            ok, msg = propisat_zhitelya(\n                                pick["zhitel"].get("ID_Object", ""),\n                                pick["lokacia"].get("ID_Object", ""),\n                                (ta.value or "").strip(),\n                            )\n                            if ok:\n                                ui.notify(f"⌂ {zn} прописан(а): {ln}", color="positive")\n                                dlg.close()\n                            else:\n                                ui.notify(f"⚠ {msg}", color="negative")\n'
BRAT_NEW = '                        # ZHILYO_KVARTALA_V1: домашний промпт = жильё квартала\n                        # (одно на всех жильцов, лежит в паспорте места, поле\n                        # «жильё») + её слова (что привезла, как обживается).\n                        _lok = pick["lokacia"]\n                        _zhilyo0 = str(_lok.get("жильё") or "")\n                        ui.html(f\'<div style="color:rgba(255,255,255,0.9); font-weight:700; \'\n                                f\'font-size:0.9rem; margin-bottom:10px; letter-spacing:0.08em;">\'\n                                f\'⌂ {zn} → {ln}</div>\')\n                        ui.html(\'<div style="color:rgba(255,255,255,0.45); font-size:0.68rem; \'\n                                \'margin-bottom:6px; text-transform:uppercase; letter-spacing:0.06em;">\'\n                                \'жильё здесь — одинаковое для всех жильцов квартала</div>\')\n                        ta_zh = ui.textarea(value=_zhilyo0).props(\n                            \'dark outlined autogrow placeholder="какое жильё получает здесь каждый…"\'\n                        ).style("width:100%; font-size:0.8rem;")\n                        ui.html(\'<div style="color:rgba(255,255,255,0.45); font-size:0.68rem; \'\n                                \'margin:10px 0 6px; text-transform:uppercase; letter-spacing:0.06em;">\'\n                                \'её слова — что привезла с собой, как обживается</div>\')\n                        ta = ui.textarea(value="").props(\n                            \'dark outlined autogrow placeholder="что возьмёшь с собой?…"\'\n                        ).style("width:100%; font-size:0.8rem;")\n                        _prezhniy = str(pick["zhitel"].get("домашний_промпт") or "").strip()\n                        if _prezhniy:\n                            with ui.expansion("нынешний дом (не пропадёт — ляжет в паспорт)").style(\n                                    "width:100%; font-size:0.72rem; "\n                                    "color:rgba(255,255,255,0.5); margin-top:6px;"):\n                                ui.label(_prezhniy).style(\n                                    "font-size:0.74rem; color:rgba(255,255,255,0.6); "\n                                    "white-space:pre-wrap;")\n\n                        async def _confirm():\n                            _zh = (ta_zh.value or "").strip()\n                            _svoyo = (ta.value or "").strip()\n                            if not _zh and not _svoyo:\n                                ui.notify("дом без слов не дом — опиши жильё или её слова",\n                                          color="warning")\n                                return\n                            if _zh != _zhilyo0.strip():\n                                try:\n                                    import json as _js\n                                    _pf = (_REPO_ROOT_FOR_IMPORT / "GRONDHEIM_CITY" / "локации"\n                                           / _lok.get("ID_Object", "") / "passport.json")\n                                    _pl = _js.loads(_pf.read_text(encoding="utf-8"))\n                                    _pl["жильё"] = _zh\n                                    _pf.write_text(_js.dumps(_pl, ensure_ascii=False, indent=2),\n                                                   encoding="utf-8")\n                                except Exception as _ez:\n                                    ui.notify(f"⚠ жильё квартала не записалось: {_ez}",\n                                              color="negative")\n                                    return\n                            try:   # прежний дом не пропадает — в паспорт, с датой\n                                import json as _js2\n                                from datetime import datetime as _dt2\n                                _pp, _dd = find_dom(pick["zhitel"].get("ID_Object", ""))\n                                if _pp is not None and _dd is not None and (\n                                        _pp.get("прописка") or _pp.get("домашний_промпт")):\n                                    _pp.setdefault("_прежние_дома", []).append({\n                                        "прописка": _pp.get("прописка"),\n                                        "домашний_промпт": _pp.get("домашний_промпт") or "",\n                                        "до": _dt2.now().isoformat(timespec="seconds")})\n                                    (_dd / "passport.json").write_text(\n                                        _js2.dumps(_pp, ensure_ascii=False, indent=2),\n                                        encoding="utf-8")\n                            except Exception:\n                                pass\n                            ok, msg = propisat_zhitelya(\n                                pick["zhitel"].get("ID_Object", ""),\n                                _lok.get("ID_Object", ""),\n                                "\\n\\n".join(x for x in (_zh, _svoyo) if x),\n                            )\n                            if ok:\n                                ui.notify(f"⌂ {zn} прописан(а): {ln}", color="positive")\n                                dlg.close()\n                            else:\n                                ui.notify(f"⚠ {msg}", color="negative")\n'


def pravka(put: Path, zameny, metka=METKA) -> str:
    if not put.exists():
        raise RuntimeError("файла нет")
    syroy = put.read_bytes().decode("utf-8")
    crlf = "\r\n" in syroy
    t = syroy.replace("\r\n", "\n")
    if metka in t:
        return "уже стоит"
    for old, new in zameny:
        n = t.count(old)
        if n != 1:
            raise RuntimeError(f"якорь найден {n} раз: {old.splitlines()[0].strip()[:60]!r}")
        t = t.replace(old, new, 1)
    ast.parse(t)
    bak = put.with_suffix(put.suffix + ".bak_zhilyo")
    if not bak.exists():
        shutil.copy2(put, bak)
    put.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
    return "поставлено"


def ruki() -> str:
    put = OSTROV / "ruki_ostrova.py"
    if not put.exists():
        raise RuntimeError("нет ruki_ostrova.py — сначала запусти ruki_ostrova_propiska.py")
    t = put.read_text(encoding="utf-8", errors="replace")
    if "RUKI_OSTROVA_V2" in t:
        return "уже стоит"
    if "RUKI_OSTROVA_V1" not in t:
        raise RuntimeError("лежит чужой ruki_ostrova.py — не трогаю")
    shutil.copy2(put, put.with_suffix(".py.bak_zhilyo"))
    put.write_text(RUKI_V2, encoding="utf-8")
    return "обновлены: жильё + её слова"


def eto_materik(d: Path) -> bool:
    return (d / "GRONDHEIM_CITY").is_dir() and (d / "Брат" / "ui_brat.py").is_file()


def nayti_materik():
    dom = Path.home()
    for k in (OSTROV.parent, OSTROV.parent.parent, dom, dom / "Desktop",
              dom / "Documents", dom / "Рабочий стол", dom / "Документы"):
        try:
            for d in k.iterdir():
                if d.is_dir() and d != OSTROV and eto_materik(d):
                    return d
        except Exception:
            continue
    print("Материк сам не нашёл. Перетащи его папку сюда и нажми Enter")
    print("(или просто Enter — тогда только остров):")
    s = input("> ").strip().strip('"').strip("'")
    return Path(s) if s and eto_materik(Path(s)) else None


def main():
    if not (OSTROV / "ui_zastroyshchik.py").exists():
        print("x не вижу острова. Положи меня в КОРЕНЬ ОСТРОВА.")
        return
    print("Жильё квартала + её слова\n")
    print("ОСТРОВ:")
    for imya, fn in (("руки острова", ruki),
                     ("Застройщик", lambda: pravka(OSTROV / "ui_zastroyshchik.py",
                                                   [(Z1_OLD, Z1_NEW), (Z2_OLD, Z2_NEW)]))):
        try:
            print(f"  {imya}: {fn()}")
        except Exception as e:
            print(f"  {imya}: ✗ {e}")
    print("\nМАТЕРИК:")
    materik = nayti_materik()
    if materik:
        try:
            print(f"  прописка у Брата: "
                  f"{pravka(materik / 'Брат' / 'ui_brat.py', [(BRAT_OLD, BRAT_NEW)])}")
        except Exception as e:
            print(f"  прописка у Брата: ✗ {e} — файл не тронут")
    else:
        print("  материк не найден — не тронут")
    print("\nГотово. Перезапусти остров (ОСТРОВ.bat) и город.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nx сорвалось: {e}\n  Скинь это окно Брату.")
    finally:
        input("\nEnter — закрыть окно")
