# -*- coding: utf-8 -*-
# SOSTOYANIE_V1
"""
СОСТОЯНИЕ ЖИТЕЛЯ — единая дверь к тому, ГДЕ он сейчас.

ЗАМЫСЕЛ ШЕФА (переворот): не карта ищет жителя — житель САМ держит своё
место. Карта тупо читает и светит точку. Знание — у жителя, не у карты.
Это третий раз один закон: цех объявляет себя, житель объявляет роль,
теперь житель объявляет место. Самообъявление вместо гадания.

ГДЕ ЖИВЁТ: отдельный лёгкий файл state.json в доме жителя — рядом с
паспортом, но НЕ в нём. Паспорт вечен (кто ты, история, характер);
state дышит (где ты прямо сейчас). Мешать вечное с сиюминутным нельзя —
паспорт святое, его не дёргают каждую сессию.

ЗАРЯД НЕ ТРОГАЕМ: _charge остаётся в паспорте (его пишет dvizhok, живой
работающий движок). Не чиним дышащее ради красоты. Переселение заряда —
отдельный осознанный шаг, если Шеф захочет. Один камень за раз.

ПРАВИЛО ПО УМОЛЧАНИЮ (железное): никто не двигал → житель ДОМА.
Пусто/нет файла → место = прописка (passport.прописка). Трейдер без
прописки (ковчег) → дом = ковчег. Честно и предсказуемо.

КТО ПИШЕТ: только механизмы движения (Калибровка открыла сессию →
рабочее здание; закрыла → дом; будущие прогулки → локация прогулки).
Все зовут postavit_mesto(), никто не пишет state.json руками.

БЕЗ LLM. Чистое чтение/запись диска.
`шесть·проверено·до·корня`
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _passport(dom: Path) -> dict:
    return _read_json(dom / "passport.json") or {}


def _propiska(dom: Path) -> str | None:
    """Дом жителя по умолчанию. Прописка из паспорта; если null/пусто —
    None (значит бездомный/ковчег, карта решит как рисовать)."""
    p = _passport(dom)
    prop = p.get("прописка")
    if prop and str(prop).strip():
        return str(prop).strip()
    return None


def gde_ya(dom) -> dict:
    """ГДЕ житель сейчас. Единственная точка правды для карты.

    Возвращает:
      {"локация": <id или None>, "почему": str, "дома": bool, "ts": str|None}

    Логика:
      есть свежий state с локацией → там житель
      нет state / пусто           → дома (прописка); None если бездомный
    """
    dom = Path(dom)
    st = _read_json(dom / "state.json")
    if st and st.get("активная_локация"):
        return {
            "локация": st["активная_локация"],
            "почему": st.get("почему", ""),
            "дома": False,
            "ts": st.get("ts"),
        }
    # дефолт — дом
    prop = _propiska(dom)
    return {
        "локация": prop,
        "почему": "по умолчанию — дома" if prop else "бездомный (нет прописки)",
        "дома": True,
        "ts": None,
    }


def postavit_mesto(dom, lokacia: str | None, pochemu: str = "") -> dict:
    """Штамп места. Зовут механизмы движения (Калибровка, прогулки).
    lokacia=None → житель вернулся домой (стираем активную локацию,
    gde_ya снова отдаст прописку). Пишем ТОЛЬКО state.json, паспорт цел."""
    dom = Path(dom)
    dom.mkdir(parents=True, exist_ok=True)
    st_path = dom / "state.json"
    st = _read_json(st_path) or {}
    if lokacia:
        st["активная_локация"] = str(lokacia)
        st["почему"] = pochemu
        st["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        # домой — снимаем активную, но помним когда ушёл
        st.pop("активная_локация", None)
        st["почему"] = pochemu or "вернулся домой"
        st["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    st_path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    return gde_ya(dom)


def domoy(dom, pochemu: str = "вернулся домой") -> dict:
    """Сахар: житель идёт домой (эквивалент postavit_mesto(None))."""
    return postavit_mesto(dom, None, pochemu)


if __name__ == "__main__":
    import sys, tempfile, shutil, io
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    print("═══ СОСТОЯНИЕ ЖИТЕЛЯ — самопроверка ═══")
    tmp = Path(tempfile.mkdtemp())
    try:
        # житель с пропиской
        dom = tmp / "Тест"
        dom.mkdir()
        (dom / "passport.json").write_text(
            json.dumps({"Official_Name": "Тест", "прописка": "0013_TRADING_QUARTER"},
                       ensure_ascii=False), encoding="utf-8")
        print(f"1. свежерождённый → {gde_ya(dom)}")
        assert gde_ya(dom)["дома"] and gde_ya(dom)["локация"] == "0013_TRADING_QUARTER"

        postavit_mesto(dom, "0014_EXCHANGE", "открылась сессия Европа")
        r = gde_ya(dom)
        print(f"2. на смене       → {r}")
        assert r["локация"] == "0014_EXCHANGE" and not r["дома"]

        domoy(dom, "сессия закрылась")
        r = gde_ya(dom)
        print(f"3. домой          → {r}")
        assert r["дома"] and r["локация"] == "0013_TRADING_QUARTER"

        # бездомный (ковчег, прописка null)
        dom2 = tmp / "Бездомный"
        dom2.mkdir()
        (dom2 / "passport.json").write_text(
            json.dumps({"Official_Name": "Бездомный", "прописка": None},
                       ensure_ascii=False), encoding="utf-8")
        print(f"4. без прописки   → {gde_ya(dom2)}")
        assert gde_ya(dom2)["локация"] is None and gde_ya(dom2)["дома"]

        print("\nВСЕ ТЕСТЫ — ЗЕЛЁНЫЕ")
    finally:
        shutil.rmtree(tmp)
    print("═══ конец ═══")
