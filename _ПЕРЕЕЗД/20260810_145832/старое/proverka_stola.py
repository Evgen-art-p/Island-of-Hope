# proverka_stola.py — ПРОВЕРКА ФАКТА, НЕ ГАЛОЧКИ.
# ─────────────────────────────────────────────────────────────
# Патч patch_sutochny_tik.py отчитался ТРЕМЯ пунктами вместо четырёх:
# строки «nakryt_stol_chisto(): промпт видит честный заряд» в выводе
# Шефа НЕ БЫЛО. Значит либо матчер промахнулся молча, либо вывод просто
# не долистался. ГАДАТЬ НЕЛЬЗЯ — читаем ЖИВОЙ ФАЙЛ и смотрим факт.
#
# Ничего не пишет. Только смотрит и говорит правду.
#
# Запуск из корня репо:  python proverka_stola.py
# `шесть·проверено·до·корня`
# ─────────────────────────────────────────────────────────────
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DVIZHOK = ROOT / "жители" / "dvizhok.py"

print()
print("  ПРОВЕРКА СТОЛА — зовёт ли он остывание?")
print("  " + "─" * 60)

if not DVIZHOK.exists():
    print(f"  ⚠ не нашёл {DVIZHOK}")
    sys.exit(1)

src = DVIZHOK.read_text(encoding="utf-8")

# ── 1. Что вообще есть в движке ─────────────────────────────
print()
print("  ── ЧТО ЕСТЬ В ДВИЖКЕ ──")
for mark, chto in [
    ("TRI_ETAZHA_V1",       "три этажа (метки/маяки)"),
    ("SUTOCHNY_TIK_V1",     "суточный тик"),
    ("SUTOCHNY_TIK_STOL_V1","добивка стола"),
    ("def ostyt_po_vremeni","метод остывания"),
]:
    print(f"     {'✓' if mark in src else '✗'} {chto}")

# ── 2. ТЕЛО nakryt_stol_chisto — глазами кода ───────────────
i = src.find("    def nakryt_stol_chisto(self)")
if i < 0:
    print("\n  ⚠ nakryt_stol_chisto НЕ НАЙДЕН вообще. Плохо.")
    sys.exit(1)

j = src.find("\n    def ", i + 10)
telo = src[i:j if j > 0 else len(src)]

zovet   = "self.ostyt_po_vremeni()" in telo
pered   = False
if zovet:
    pered = telo.find("self.ostyt_po_vremeni()") < telo.find("return {")

print()
print("  ── ТЕЛО nakryt_stol_chisto ──")
print(f"     {'✓' if zovet else '✗'} зовёт ostyt_po_vremeni()")
print(f"     {'✓' if pered else '✗'} зовёт ДО return (иначе бесполезно)")

# ── 3. ЖИВОЙ ЗАМЕР: стол vs паспорт ─────────────────────────
print()
print("  ── ЖИВОЙ ЗАМЕР (главное) ──")
sys.path.insert(0, str(ROOT / "жители"))
try:
    from dvizhok import Dvizhok
except Exception as ex:
    print(f"     ⚠ движок не импортируется: {ex}")
    sys.exit(1)

CITY = ROOT / "GRONDHEIM_CITY"
SKIP = {".git", "__pycache__", "_ARCHIVE", "_OLD", ".venv"}

nashli = False
for pp in CITY.rglob("passport.json"):
    if any(x in SKIP for x in pp.parts):
        continue
    try:
        p = json.loads(pp.read_text(encoding="utf-8"))
    except Exception:
        continue
    if not (isinstance(p, dict) and p.get("DNA_Static")):
        continue
    ch = p.get("_charge")
    if ch is None or abs(ch) < 0.02:
        continue          # в покое — по нему не увидишь разницы

    imya = p.get("Official_Name") or pp.parent.name
    stol = Dvizhok(pp.parent).nakryt_stol_chisto()
    na_diske = json.loads(pp.read_text(encoding="utf-8")).get("_charge")

    print(f"     {imya}:")
    print(f"        в паспорте:  {ch:+.3f}")
    print(f"        в СТОЛЕ:     {stol['заряд']:+.3f}   ← это видит промпт")
    print(f"        диск цел:    {na_diske == ch}  (стол не должен писать)")
    nashli = True
    break

if not nashli:
    print("     все в покое — разницу не увидеть.")
    print("     Прогони tik.py ПОСЛЕ пары сделок и вернись сюда.")

# ── ВЕРДИКТ ─────────────────────────────────────────────────
print()
print("  " + "─" * 60)
if zovet and pered:
    print("  ВЕРДИКТ: ✓ стол честный. Промпт на каждом баре видит")
    print("           заряд, остуженный временем — не окаменевший.")
else:
    print("  ВЕРДИКТ: ✗ ДЫРА. Стол читает окаменевший заряд.")
    print("           tik.py остужает диск, а промпт между тиками")
    print("           видит старое. Гони: python patch_tik_dobivka.py")
print()
