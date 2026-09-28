# -*- coding: utf-8 -*-
# mayak_svodki.py — ПАТЧ: сводки через Маяк (причал + Хранитель)
# Маркер: MAYAK_SVODKI_V1
"""
Слово Шефа (28.09): остров сигналит на наш Маяк, Хранитель Маяка
докладывает Брату — сводки с острова и так далее.

ЧТО ДЕЛАЕТ (Маяк/prichal.py и Маяк/khranitel_mayaka.py)
  Причал:
    • пульс может нести СВОДКУ — отчёт мира тем же сканером, что у нас;
    • причал кладёт её на полку мира: Маяк/острова/<id>/сводка.md,
      в карточке отмечает, когда пришла (сводка_когда);
    • в журнал пульсов сводка не пишется — журнал остаётся лёгким;
    • отправка (otpravit) умеет брать сводку с собой.
  Хранитель:
    • в своей сводке видит по каждому миру: когда последний пульс, что
      мир сказал о себе, когда пришла его сводка и что в ней тревожного.

Причал и Хранитель — одни и те же файлы на материке и на острове.
Поэтому патч ОДИН на оба берега: кладёшь в корень репы (города или
острова) и запускаешь. Повторный запуск ничего не ломает.
Копии — .bak_svodki.
"""
import ast
import py_compile
import shutil
from pathlib import Path

MARKER = "MAYAK_SVODKI_V1"


def naiti_koren():
    kandidaty = [Path(__file__).resolve().parent, Path.cwd()]
    for k in list(kandidaty):
        kandidaty.extend(list(k.parents)[:3])
    for k in kandidaty:
        if (k / "Маяк" / "prichal.py").is_file() and \
                ((k / "main.py").is_file() or (k / "ostrov_main.py").is_file()):
            return k
    return None


# (что, где, как, текст)
PRICHAL = [
    ("предел сводки", 'RODY = ("город", "остров")\n', "после", '''
# MAYAK_SVODKI_V1: пульс может нести сводку мира — его отчёт тем же
# сканером, что у материка. Предел — чтобы чужой мир не завалил диск.
SVODKA_MAX = 150_000
'''),
    ("схема", '''    "версия": "строка, необязательно — версия шасси, чтобы видеть расхождение",
}''', "вместо", '''    "версия": "строка, необязательно — версия шасси, чтобы видеть расхождение",
    "сводка": "строка, необязательно — отчёт мира (сканер), markdown",  # MAYAK_SVODKI_V1
}'''),
    ("проверка", '''        "версия": str(d.get("версия", "") or "")[:40],
    }''', "вместо", '''        "версия": str(d.get("версия", "") or "")[:40],
        "сводка": str(d.get("сводка", "") or "")[:SVODKA_MAX],  # MAYAK_SVODKI_V1
    }'''),
    ("карточка", '''            "пульсов": int(staroe.get("пульсов", 0)) + 1,
        }''', "вместо", '''            "пульсов": int(staroe.get("пульсов", 0)) + 1,
            # MAYAK_SVODKI_V1: когда пришла последняя сводка мира
            "сводка_когда": teper if p.get("сводка") else staroe.get("сводка_когда", ""),
        }'''),
    ("сводка на полку", '''    except Exception as e:
        return {"ok": False, "причина": f"не записалось: {e}", "id": p["id"]}
''', "до", '''        # MAYAK_SVODKI_V1: сводка — рядом с карточкой, целиком заменяется
        if p.get("сводка"):
            _vr = dom / "сводка.md.tmp"
            _vr.write_text(p["сводка"], encoding="utf-8")
            os.replace(_vr, dom / "сводка.md")
'''),
    ("отправка: вход", '''                   timeout: float = 15.0) -> dict:''', "вместо",
     '''                   timeout: float = 15.0, svodka: str = "") -> dict:'''),
    ("отправка: тело", '''            "числа": chisla or {}, "версия": versia, "адрес": adres}
''', "после", '''    if svodka:   # MAYAK_SVODKI_V1
        telo["сводка"] = svodka
'''),
]

KHRANITEL = [
    ("миры подробно", '''        stroki.append(f"На связи миры: {', '.join(imena)}.")
''', "после", '''        # MAYAK_SVODKI_V1: по каждому миру — пульс, что сказал о себе,
        # когда пришла сводка и что в ней тревожного (раздел 7 отчёта).
        for _rod, _polka in (("город", GORODA_DIR), ("остров", OSTROVA_DIR)):
            for _g in gor["города" if _rod == "город" else "острова"]:
                _k = _read_json(_polka / _g["id"] / "город.json", {}) or {}
                _s = f"• {_g['имя']} ({_rod}): последний пульс {_k.get('последний_пульс') or '—'}"
                if _k.get("числа"):
                    _s += "; о себе: " + ", ".join(f"{a}: {b}" for a, b in _k["числа"].items())
                stroki.append(_s)
                _put = _polka / _g["id"] / "сводка.md"
                if _put.is_file():
                    stroki.append(f"  сводка от {_k.get('сводка_когда') or '?'}")
                    try:
                        _t = _put.read_text(encoding="utf-8")
                        _i = _t.find("## 7.")
                        if _i >= 0:
                            _kusok = _t[_i:].split("\\n## ", 1)[0]
                            for _l in [x for x in _kusok.splitlines()
                                       if x.startswith("- ")][:5]:
                                stroki.append("  " + _l[:160])
                    except Exception:
                        pass
'''),
]


def primenit(p: Path, pravki, kopiya_hvost: str) -> str:
    tekst = p.read_text(encoding="utf-8")
    if MARKER in tekst:
        return "• уже стоит"
    plohie = [(c, tekst.count(g)) for c, g, _, _ in pravki if tekst.count(g) != 1]
    if plohie:
        return f"✗ не нашёл мест ровно по одному разу: {plohie} — не трогаю"
    novoe = tekst
    for _, gde, kak, vstavka in pravki:
        if kak == "до":
            novoe = novoe.replace(gde, vstavka + gde, 1)
        elif kak == "после":
            novoe = novoe.replace(gde, gde + vstavka, 1)
        else:
            novoe = novoe.replace(gde, vstavka, 1)
    novoe = novoe.rstrip() + f"\n\n# {MARKER} - marker\n"
    try:
        ast.parse(novoe)
    except SyntaxError as e:
        return f"✗ после правки не собирается ({e}) — не пишу"
    k = p.with_name(p.name + kopiya_hvost)
    if not k.exists():
        shutil.copy2(p, k)
    p.write_text(novoe, encoding="utf-8")
    try:
        py_compile.compile(str(p), doraise=True)
    except py_compile.PyCompileError as e:
        p.write_text(tekst, encoding="utf-8")
        return f"✗ не компилируется ({e}) — вернул как было"
    return "✓ починено"


def main():
    koren = naiti_koren()
    if koren is None:
        print("✗ Не нашёл корень (нужен Маяк/prichal.py рядом с main.py или ostrov_main.py).")
        print("  Положи патч в корень репы и запусти оттуда.")
        return
    bereg = "остров" if (koren / "ostrov_main.py").is_file() else "материк"
    print(f"Корень: {koren}  ({bereg})\n")
    print(f"Маяк/prichal.py            {primenit(koren / 'Маяк' / 'prichal.py', PRICHAL, '.bak_svodki')}")
    kh = koren / "Маяк" / "khranitel_mayaka.py"
    if kh.is_file():
        print(f"Маяк/khranitel_mayaka.py   {primenit(kh, KHRANITEL, '.bak_svodki')}")
    print("\nПерезапусти — пульс сможет нести сводку, причал её примет.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            input("\nEnter — закрыть окно")
        except EOFError:
            pass
