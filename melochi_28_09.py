# -*- coding: utf-8 -*-
# melochi_28_09.py — ПАТЧ: пять мелочей после первых сводок (28.09)
# Маркер: MELOCHI_28_09_V1
"""
Слово Шефа: «собери». Один патч на оба берега — кладёшь в корень
города или острова и запускаешь, он сам понимает, где он, и делает
только то, что есть на этом берегу.

  1-2. Сканер («Корень острова», _ПЕРЕЕЗД как чулан) — это не здесь:
       новый Брат/skaner_goroda.py кладётся отдельно на оба берега.
  3. ОСТРОВ: запускатель больше не пишет «главная не встала» —
     главная у острова своя, старый установщик не нужен.
  4-5. ОБА: Хранитель расписывает каждый мир ОДНОЙ записью — на связи
     или молчит, пульс по-человечески («28.09 14:19, 3 мин назад»),
     что сказал о себе, когда сводка и что в ней тревожного. Брат
     второй раз это не повторяет (новый Брат/ruki_brata.py).
  +. МАТЕРИК: плашка Брата не уходит за край экрана — ни из
     запомненного места, ни когда окно сузили.

Повторный запуск ничего не ломает. Копии — .bak_melochi.
"""
import ast
import py_compile
import shutil
from pathlib import Path

MARKER = "MELOCHI_28_09_V1"
V1 = '        # MAYAK_SVODKI_V1: по каждому миру — пульс, что сказал о себе,\n        # когда пришла сводка и что в ней тревожного (раздел 7 отчёта).\n        for _rod, _polka in (("город", GORODA_DIR), ("остров", OSTROVA_DIR)):\n            for _g in gor["города" if _rod == "город" else "острова"]:\n                _k = _read_json(_polka / _g["id"] / "город.json", {}) or {}\n                _s = f"• {_g[\'имя\']} ({_rod}): последний пульс {_k.get(\'последний_пульс\') or \'—\'}"\n                if _k.get("числа"):\n                    _s += "; о себе: " + ", ".join(f"{a}: {b}" for a, b in _k["числа"].items())\n                stroki.append(_s)\n                _put = _polka / _g["id"] / "сводка.md"\n                if _put.is_file():\n                    stroki.append(f"  сводка от {_k.get(\'сводка_когда\') or \'?\'}")\n                    try:\n                        _t = _put.read_text(encoding="utf-8")\n                        _i = _t.find("## 7.")\n                        if _i >= 0:\n                            _kusok = _t[_i:].split("\\n## ", 1)[0]\n                            for _l in [x for x in _kusok.splitlines()\n                                       if x.startswith("- ")][:5]:\n                                stroki.append("  " + _l[:160])\n                    except Exception:\n                        pass\n'
V2 = '        # MAYAK_SVODKI_V2: одна запись на мир — жив ли, когда пульс\n        # (по-человечески, местным временем), что сказал о себе, когда\n        # пришла сводка и что в ней тревожного (раздел 7 отчёта).\n        def _po_chel(_iso):\n            try:\n                from datetime import datetime as _dt, timezone as _tz\n                _t = _dt.fromisoformat(str(_iso))\n                if _t.tzinfo is None:\n                    _t = _t.replace(tzinfo=_tz.utc)\n                _min = (_dt.now(_tz.utc) - _t).total_seconds() / 60\n                _naz = (f"{_min:.0f} мин назад" if _min < 90 else\n                        f"{_min / 60:.0f} ч назад" if _min < 48 * 60 else\n                        f"{_min / 1440:.0f} дн назад")\n                return _t.astimezone().strftime("%d.%m %H:%M") + ", " + _naz, _min\n            except Exception:\n                return str(_iso or "—"), None\n\n        for _rod, _polka in (("город", GORODA_DIR), ("остров", OSTROVA_DIR)):\n            for _g in gor["города" if _rod == "город" else "острова"]:\n                _k = _read_json(_polka / _g["id"] / "город.json", {}) or {}\n                _kogda, _min = _po_chel(_k.get("последний_пульс"))\n                _zhiv = "на связи" if (_min is not None and _min < 30) else "молчит"\n                stroki.append(f"• {_g[\'имя\']} ({_rod}) — {_zhiv}; последний пульс "\n                              f"{_kogda}; пульсов {_k.get(\'пульсов\', 0)}")\n                if _k.get("числа"):\n                    stroki.append("  о себе: " + ", ".join(\n                        f"{a}: {b}" for a, b in _k["числа"].items()))\n                _put = _polka / _g["id"] / "сводка.md"\n                if _put.is_file():\n                    stroki.append(f"  сводка от {_po_chel(_k.get(\'сводка_когда\'))[0]}")\n                    try:\n                        _t = _put.read_text(encoding="utf-8")\n                        _i = _t.find("## 7.")\n                        if _i >= 0:\n                            _kusok = _t[_i:].split("\\n## ", 1)[0]\n                            for _l in [x for x in _kusok.splitlines()\n                                       if x.startswith("- ")][:5]:\n                                stroki.append("  " + _l[:160])\n                    except Exception:\n                        pass\n'
GL_OLD = '    if not zapustit("postavit_glavnuyu.py", "--sdelat"):\n        skazat("  главная не встала — остров поднимется без неё")\n'
GL_NEW = '    # MELOCHI_28_09_V1: старый установщик главной больше не нужен —\n    # главная острова давно своя (ui_ostrov.py). Не пугаем зря.\n    if (KOREN / "postavit_glavnuyu.py").exists():\n        if not zapustit("postavit_glavnuyu.py", "--sdelat"):\n            skazat("  главная не встала — остров поднимется без неё")\n    elif (KOREN / "ui_ostrov.py").exists():\n        skazat("  главная на месте")\n    else:\n        skazat("  главной нет — остров поднимется без неё")\n'
PL_OLD = "      if (s && typeof s.x === 'number') {"
PL_NEW = "      // MELOCHI_28_09_V1: место из прошлого не пускаем за край экрана\n      if (s && typeof s.x === 'number' && s.x >= 0 && s.y >= 0 &&\n          s.x < window.innerWidth - 200 && s.y < window.innerHeight - 120) {"
PL2_OLD = '  zavesti();\n})();\n'
PL2_NEW = "  // MELOCHI_28_09_V1: окно сузили — плашка не уходит за край, встаёт в центр\n  window.addEventListener('resize', function () {\n    const p = document.querySelector('.brat-plashka');\n    if (!p || p.style.transform === 'translate(-50%, -50%)' ||\n        p.style.left === '50%') return;\n    const x = parseInt(p.style.left), y = parseInt(p.style.top);\n    if (x < 0 || y < 0 || x > window.innerWidth - 200 ||\n        y > window.innerHeight - 120) {\n      p.style.left = '50%'; p.style.top = '50%';\n      p.style.transform = 'translate(-50%,-50%)';\n      try { localStorage.removeItem('brat_plashka'); } catch (e) {}\n    }\n  });\n  zavesti();\n})();\n"


def naiti_koren():
    kandidaty = [Path(__file__).resolve().parent, Path.cwd()]
    for k in list(kandidaty):
        kandidaty.extend(list(k.parents)[:3])
    for k in kandidaty:
        if (k / "main.py").is_file() or (k / "ostrov_main.py").is_file():
            return k
    return None


def zamenit(p: Path, pary, marker: str, python: bool = True) -> str:
    if not p.is_file():
        return "— нет файла на этом берегу"
    tekst = p.read_text(encoding="utf-8")
    if marker in tekst:
        return "• уже стоит"
    plohie = [tekst.count(a) for a, _ in pary if tekst.count(a) != 1]
    if plohie:
        return "✗ не нашёл места ровно по одному разу — не трогаю"
    novoe = tekst
    for a, b in pary:
        novoe = novoe.replace(a, b, 1)
    if python:
        try:
            ast.parse(novoe)
        except SyntaxError as e:
            return f"✗ после правки не собирается ({e}) — не пишу"
    k = p.with_name(p.name + ".bak_melochi")
    if not k.exists():
        shutil.copy2(p, k)
    p.write_text(novoe, encoding="utf-8")
    if python:
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            p.write_text(tekst, encoding="utf-8")
            return f"✗ не компилируется ({e}) — вернул как было"
    return "✓ починено"


def main():
    koren = naiti_koren()
    if koren is None:
        print("✗ Не нашёл корень (нужен main.py города или ostrov_main.py острова).")
        return
    ostrov = (koren / "ostrov_main.py").is_file() and not (koren / "main.py").is_file()
    print(f"Корень: {koren}  ({'остров' if ostrov else 'материк'})\n")

    kh = koren / "Маяк" / "khranitel_mayaka.py"
    if kh.is_file() and "MAYAK_SVODKI_V1" not in kh.read_text(encoding="utf-8"):
        print("Маяк/khranitel_mayaka.py   ✗ сначала mayak_svodki.py, потом этот")
    else:
        print(f"Маяк/khranitel_mayaka.py   {zamenit(kh, [(V1, V2)], 'MAYAK_SVODKI_V2')}")

    if ostrov:
        print(f"остров.py                  {zamenit(koren / 'остров.py', [(GL_OLD, GL_NEW)], MARKER)}")
    else:
        ub = koren / "Брат" / "ui_brat.py"
        if ub.is_file() and "PLASHKA_BRATA_V1" not in ub.read_text(encoding="utf-8"):
            print("Брат/ui_brat.py            — плашки ещё нет, трогать нечего")
        else:
            print(f"Брат/ui_brat.py            {zamenit(ub, [(PL_OLD, PL_NEW), (PL2_OLD, PL2_NEW)], MARKER)}")

    print("\nНе забудь: новые Брат/skaner_goroda.py (оба берега) и "
          "Брат/ruki_brata.py (материк).")
    print("Перезапусти.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            input("\nEnter — закрыть окно")
        except EOFError:
            pass
