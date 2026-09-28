# -*- coding: utf-8 -*-
# model_iz_env.py — ПАТЧ: модель из .env не роняет страницы
# Маркер: MODEL_IZ_ENV_V1
"""
Что было: на острове в .env стоит модель по умолчанию
deepseek/deepseek-v4-pro (слово Шефа: «по умолчанию, чтобы не было
случайностей»). Страница Маяка открывалась с ней, а в её выпадающем
списке такой модели нет — NiceGUI падал, в браузере 500.

Что делает патч — в каждой странице со списком моделей:
  • модель из .env, которой нет в списке, встаёт в список первой
    строкой с пометкой «· из .env». Страница открывается на ней;
  • в список добавляется GPT-5.6 Luna (openai/gpt-5.6-luna) — она
    работает на Бирже, теперь выбирается везде.
Цена у модели из .env — прочерк: выдуманное число хуже отсутствующего.

Годится и для материка, и для острова: кладёшь в корень той репы,
которую чинишь, и запускаешь. Сам находит страницы, которые у этой
репы есть. Повторный запуск ничего не ломает. Копии — .bak_model.
"""
import ast
import py_compile
import shutil
from pathlib import Path

MARKER = "MODEL_IZ_ENV_V1"

STRANICY = [
    "Брат/ui_brat.py",
    "Маяк/ui_mayak.py",
    "жители/ui_zhitel.py",
    "Архив/ui_arkhiv.py",
    "Академия/ui_rektor.py",
    "Академия/ui_akademia.py",
    "Биржа/ui_torg.py",
]

BLOK = '''
# MODEL_IZ_ENV_V1 (слово Шефа 28.09): модель по умолчанию из .env,
# которой нет в списке, больше не роняет страницу — встаёт в список
# первой строкой с пометкой «из .env». И Луна есть в списке везде:
# она работает на Бирже. Цена у модели из .env — прочерк: выдуманное
# число хуже отсутствующего.
if not any(_m["id"] == "openai/gpt-5.6-luna" for _m in MODELS_CATALOG):
    MODELS_CATALOG.append({"id": "openai/gpt-5.6-luna", "name": "GPT-5.6 Luna",
                           "price": "$0.20 / $1.20"})
if DEFAULT_MODEL and not any(_m["id"] == DEFAULT_MODEL for _m in MODELS_CATALOG):
    MODELS_CATALOG.insert(0, {"id": DEFAULT_MODEL,
                              "name": DEFAULT_MODEL.split("/")[-1] + " · из .env",
                              "price": "—"})
'''


def naiti_koren():
    kandidaty = [Path(__file__).resolve().parent, Path.cwd()]
    for k in list(kandidaty):
        kandidaty.extend(list(k.parents)[:3])
    for k in kandidaty:
        if (k / "main.py").is_file() or (k / "ostrov_main.py").is_file():
            return k
    return None


def _gde_vstavit(tekst: str):
    """Номер строки, после которой ставить блок: конец присваивания
    DEFAULT_MODEL на верхнем уровне, если до него есть MODELS_CATALOG."""
    derevo = ast.parse(tekst)
    katalog_est = False
    for uzel in derevo.body:
        if isinstance(uzel, ast.Assign):
            imena = [t.id for t in uzel.targets if isinstance(t, ast.Name)]
            if "MODELS_CATALOG" in imena:
                katalog_est = True
            if "DEFAULT_MODEL" in imena and katalog_est:
                return uzel.end_lineno
    return None


def pochinit(p: Path) -> str:
    tekst = p.read_text(encoding="utf-8")
    if MARKER in tekst:
        return "• уже стоит"
    try:
        stroka = _gde_vstavit(tekst)
    except SyntaxError as e:
        return f"✗ файл сейчас не собирается ({e}) — не трогаю"
    if stroka is None:
        return "✗ не нашёл список моделей и модель по умолчанию — не трогаю"
    stroki = tekst.splitlines(keepends=True)
    novoe = "".join(stroki[:stroka]) + BLOK + "".join(stroki[stroka:])
    try:
        ast.parse(novoe)
    except SyntaxError as e:
        return f"✗ после правки не собирается ({e}) — не пишу"
    kopiya = p.with_name(p.name + ".bak_model")
    if not kopiya.exists():
        shutil.copy2(p, kopiya)
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
        print("✗ Не нашёл корень (нужен main.py города или ostrov_main.py острова).")
        print("  Положи патч в корень репы и запусти оттуда.")
        return
    print(f"Корень: {koren}\n")
    naydeno = 0
    for put in STRANICY:
        p = koren / put
        if not p.is_file():
            continue
        naydeno += 1
        print(f"{put:28} {pochinit(p)}")
    if not naydeno:
        print("Страниц со списком моделей здесь не нашёл.")
    print("\nПерезапусти — страницы откроются, даже если в .env модель не из списка.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            input("\nEnter — закрыть окно")
        except EOFError:
            pass
