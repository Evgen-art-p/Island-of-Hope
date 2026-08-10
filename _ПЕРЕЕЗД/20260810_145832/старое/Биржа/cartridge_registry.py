# -*- coding: utf-8 -*-
# BIRZHA_BAZA_V1
"""
CARTRIDGE REGISTRY — сканер цехов нового города.

ЗАКОН КАРТРИДЖА (перенесён из -2 ПРИНЦИПОМ, не кодом):
  1. Цех объявляет себя сам: папка + manifest.json = цех,
     его id — ИМЯ ПАПКИ, не поле внутри манифеста.
  2. Никто не ведёт списков: этот модуль сканирует диск на лету.
     Удалил папку — цех исчез отовсюду.
  3. Город помнит снаружи: хроники/резонанс живут вне цеха.

ЗАКОН ПАРЫ (новый город, Чертёж §1.5.2б / §4.4а):
  Цех объявляет СЛОТЫ (роли-вакансии). Носителей у цеха НЕТ.
  Житель (Род) живёт в GRONDHEIM_CITY/жители/ и надевается на слот
  актом «Роль» (кабинет Брата) — кнопка пишет в его
  маски/работа/mask.json поля Workshop_ID + Turbo_Role.
  resolve_para() сводит пару НА ЛЕТУ по этим полям.
  ID_Object жителя в опознании роли НЕ УЧАСТВУЕТ НИКОГДА —
  это лекарство от болезни -2 («стресс 0.0»: суд по роли,
  id по реестру, письмо на несуществующий адрес).

ОДИН МЕХАНИЗМ, ДВА КРАНА:
  корень данных — параметр `kvartal`:
    "Биржа"  → GRONDHEIM_CITY/Биржа/цеха/
    "Студия" → GRONDHEIM_CITY/Студия/цеха/
  Механизм один — источники разные (Закон Фрактала).

Без LLM. Без UI. Без NiceGUI. Чистое чтение диска.
"""
import json
from pathlib import Path

# Корень города — от места этого файла (Биржа/ лежит рядом с GRONDHEIM_CITY/)
_REPO = Path(__file__).resolve().parent.parent
CITY = _REPO / "GRONDHEIM_CITY"


def _read_json(path: Path):
    """Честное чтение: битый файл → None, не падение."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ───────────────────────────────────────────────────────────────
# СТАТЬЯ 1-2: сканер цехов
# ───────────────────────────────────────────────────────────────

def list_ceha(kvartal: str = "Биржа") -> list:
    """Все цеха квартала. Папка с manifest.json = цех, id = имя папки.
    Битый манифест → цех виден, но с честной пометкой _битый."""
    root = CITY / kvartal / "цеха"
    out = []
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        mf = d / "manifest.json"
        if not mf.exists():
            continue  # папка без манифеста — не цех (статья 1)
        m = _read_json(mf)
        if m is None:
            out.append({"id": d.name, "_битый": True, "_путь": str(d)})
            continue
        m["id"] = d.name          # id = имя папки, всегда (статья 1)
        m["_путь"] = str(d)
        out.append(m)
    return out


def get_ceh(ceh_id: str, kvartal: str = "Биржа"):
    """Один цех по id. Честный None, если нет."""
    for c in list_ceha(kvartal):
        if c["id"] == ceh_id:
            return c
    return None


# ───────────────────────────────────────────────────────────────
# ЗАКОН ПАРЫ: свод носителя и слота на лету
# ───────────────────────────────────────────────────────────────

def _scan_zhiteli_maski():
    """Все жители с активной маской «работа».
    Скан: GRONDHEIM_CITY/жители/{профиль}/{Имя}/маски/работа/mask.json
    Это граница жителя (паспорт+маска), не его кухня — слои не трогаем."""
    root = CITY / "жители"
    out = []
    if not root.exists():
        return out
    for passport_path in sorted(root.glob("*/*/passport.json")):
        dom = passport_path.parent
        mask_path = dom / "маски" / "работа" / "mask.json"
        if not mask_path.exists():
            continue
        mask = _read_json(mask_path)
        if not mask or not mask.get("_активна"):
            continue
        p = _read_json(passport_path) or {}
        out.append({
            "имя": p.get("Official_Name", dom.name),
            "id": p.get("ID_Object", ""),
            "тип": p.get("тип", ""),
            "папка": str(dom),
            "цех": (mask.get("Workshop_ID") or "").strip(),
            "слот": (mask.get("Turbo_Role") or "").strip(),
            "core_phrase": mask.get("Core_Phrase", ""),
            "magic": mask.get("magic"),   # MAGIC_IN_MASK_V1: обратный мостик
        })
    return out


def _zhitel_po_imeni(imya: str):
    """RABOTA_DOKUMENT_V1: житель по имени, без всяких масок работы.
    Нужен, когда правду о найме говорит документ места, а не бумажка
    в жителе. Магик по-прежнему берём из маски — он про человека и
    его сделки, а не про место."""
    imya = (imya or "").strip()
    if not imya:
        return None
    root = CITY / "жители"
    if not root.exists():
        return None
    for passport_path in sorted(root.glob("*/*/passport.json")):
        p = _read_json(passport_path) or {}
        if (p.get("Official_Name") or passport_path.parent.name).strip() != imya:
            continue
        dom = passport_path.parent
        mask = _read_json(dom / "маски" / "работа" / "mask.json") or {}
        return {
            "имя": p.get("Official_Name", dom.name),
            "id": p.get("ID_Object", ""),
            "тип": p.get("тип", ""),
            "папка": str(dom),
            "цех": "",
            "слот": "",
            "core_phrase": mask.get("Core_Phrase", ""),
            "magic": mask.get("magic"),
        }
    return None


def resolve_para(ceh_id: str, slot: str, kvartal: str = "Биржа"):
    """ЕДИНСТВЕННАЯ точка правды пары (цех, слот) → носитель.

    RABOTA_DOKUMENT_V1: сперва спрашиваем ДОКУМЕНТ МЕСТА
    (слоты/{слот}/должность.json) — там написано, кого приняли.
    Работа больше не вкручена в личность: уволить можно, не трогая
    жителя. Документа у места ещё нет — работаем по-старому, по
    mask.json, чтобы уже сидящие не выпали из строя.
    Честный None: слот пуст / цеха нет / слота в манифесте нет."""
    ceh = get_ceh(ceh_id, kvartal)
    if ceh is None:
        return None
    slots = [s.get("слот") for s in ceh.get("слоты", [])]
    if slot not in slots:
        return None  # такой вакансии в цехе не объявлено

    try:
        # STANDART_RABOTY_V1: правду о найме говорит ПОСТ — единый
        # реестр мест города. Поста на этом слоте нет — работаем
        # по-старому, по mask.json, чтобы сидящие не выпали.
        import sys as _sys
        _g = str(CITY.parent / "ГОРОД")
        if _g not in _sys.path:
            _sys.path.insert(0, _g)
        import rabota as _rab
        if _rab.est_post_na_slote(ceh_id, slot):
            _imya = _rab.kto_na_slote(ceh_id, slot)
            if not _imya:
                return None            # пост говорит: место свободно
            _z = _zhitel_po_imeni(_imya)
            if _z is None:
                return None            # в посте имя, а жителя нет
            _z["цех"] = ceh_id
            _z["слот"] = slot
            return _z
    except Exception:
        pass

    for z in _scan_zhiteli_maski():
        if z["цех"] == ceh_id and z["слот"] == slot:
            return z
    return None  # вакансия есть, носителя нет — слот пуст, честно


def resolve_by_magic(magic):
    """ОБРАТНЫЙ мостик: magic закрытой позиции → носитель.
    Близнец resolve_para, тот же скан масок — magic живёт В МАСКЕ
    (Закон Пары), отдельного реестра магиков нет. Честный None:
    магик не найден ни в одной активной маске. Приводит к int, чтобы
    100002 и "100002" резолвились одинаково. # MAGIC_IN_MASK_V1
    """
    try:
        m = int(magic)
    except (TypeError, ValueError):
        return None
    for z in _scan_zhiteli_maski():
        zm = z.get("magic")
        if zm is None:
            continue
        try:
            if int(zm) == m:
                return z
        except (TypeError, ValueError):
            continue
    return None


def list_nositeli(ceh_id: str, kvartal: str = "Биржа") -> list:
    """Все носители цеха: по слоту — кто нанят (или None).
    Для UI приборной панели: рисовать универсально, без хардкода имён."""
    ceh = get_ceh(ceh_id, kvartal)
    if ceh is None:
        return []
    nanyatye = {(z["цех"], z["слот"]): z for z in _scan_zhiteli_maski()}
    out = []
    for s in ceh.get("слоты", []):
        slot = s.get("слот", "")
        out.append({
            "слот": slot,
            "роль": s.get("роль", ""),
            "носитель": nanyatye.get((ceh_id, slot)),  # None = вакансия
        })
    return out


# ───────────────────────────────────────────────────────────────
# Самопроверка (запуск напрямую): python Биржа/cartridge_registry.py
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _s
    import io as _io
    if isinstance(_s.stdout, _io.TextIOWrapper):
        _s.stdout.reconfigure(encoding="utf-8")
    print("═══ CARTRIDGE REGISTRY — самопроверка ═══")
    ceha = list_ceha("Биржа")
    print(f"цехов на Бирже: {len(ceha)}")
    for c in ceha:
        if c.get("_битый"):
            print(f"  ⚠ {c['id']} — манифест битый")
            continue
        slots = c.get("слоты", [])
        print(f"  ⚙ {c['id']} — «{c.get('название','?')}» · "
              f"слотов: {len(slots)} · судья: {c.get('судья','?')}")
        for row in list_nositeli(c["id"]):
            n = row["носитель"]
            who = f"{n['имя']} ({n['id']})" if n else "— вакансия —"
            print(f"     {row['слот']:>4} {row['роль']:<22} {who}")
    print(f"несуществующий цех → {get_ceh('нет_такого')}")
    print(f"несуществующий слот → {resolve_para('торговый_хаос', 'A99')}")
    _by_magic = resolve_by_magic(100002)
    print(f"magic 100002 → {(_by_magic or {}).get('имя') or '— не найден —'}")
    print("═══ конец самопроверки ═══")

# RABOTA_DOKUMENT_V1 - marker

# STANDART_RABOTY_V1 - marker
