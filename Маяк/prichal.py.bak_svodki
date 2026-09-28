# -*- coding: utf-8 -*-
# PRICHAL_V1 — причал Маяка: граница между городами
"""
ПРИЧАЛ · один контракт на обе стороны границы

Этот файл знает ФОРМАТ ПУЛЬСА — и умеет его принять, и умеет его
отправить. Обе стороны берут ОДИН И ТОТ ЖЕ файл, поэтому двух правд
о формате быть не может физически: разойтись нечему.

    материк:  prinyat(dannye)   — кладёт карточку на полку Маяка
    остров:   otpravit(...)     — шлёт пульс на материк
    оба:      SHEMA, proverit_pulse() — что считается правильным пульсом

САМОДОСТАТОЧЕН НАРОЧНО. Не импортирует ни город, ни rezidenty, ни
mayak — только stdlib и httpx. Остров живёт в другом репозитории, у
него нет ни ковчега, ни гнёзд; он копирует этот файл к себе и зовёт
otpravit(). Всё, что нужно для границы, лежит здесь.

ЧТО ТАКОЕ ПУЛЬС (решение Шефа 29.07 — первый рейс). Не сделка, не
вывод, не личность. Только: я жив, вот кто я, вот пара чисел. Самый
дешёвый груз, каким проверяют, что провод есть.

ЧЕСТНО ПРО ГРАНИЦУ:
  • пульс НЕ несёт личность. Житель границу не пересекает — это
    прямое решение (Живая Книга возит biography_snapshot, снимок, а
    не самих агентов).
  • пульс НЕ доказывает, что остров говорит правду о своих числах.
    Он доказывает только, что остров жив и на связи.
  • нет ключа в .env — причал пускает всех. Это удобно локально и
    опасно в интернете, и причал об этом честно говорит, а не
    притворяется защищённым.

`шесть·проверено·до·корня`
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent      # Маяк/ (на материке)

GORODA_DIR = _HERE / "города"
OSTROVA_DIR = _HERE / "острова"

# Общий секрет. Пусто — причал открыт всем (локально это нормально).
PULSE_KEY = os.getenv("GRONDHEIM_PULSE_KEY", "")
KEY_HEADER = "X-Grondheim-Key"

RODY = ("город", "остров")


# ═══════════════════════════════════════════════════════════
# СХЕМА — что считается правильным пульсом
# ═══════════════════════════════════════════════════════════

SHEMA = {
    "id":     "строка, обязательно — короткое имя папки (латиница/цифры/-_)",
    "имя":    "строка, обязательно — как звать этот мир по-человечески",
    "род":    f"строка, обязательно — одно из {RODY}",
    "адрес":  "строка, необязательно — где его искать (URL)",
    "числа":  "объект, необязательно — что мир хочет сказать о себе",
    "версия": "строка, необязательно — версия шасси, чтобы видеть расхождение",
}


def _chistyy_id(raw: str) -> str:
    """ID станет именем ПАПКИ — пускаем только безопасное. Это не
    придирка: без чистки чужой мир мог бы попросить записать себя
    куда угодно на диске («../../»), и причал послушно записал бы."""
    razresheno = set("abcdefghijklmnopqrstuvwxyz"
                     "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    s = "".join(c for c in str(raw or "") if c in razresheno)
    return s[:48]


def proverit_pulse(d: dict) -> tuple:
    """Проверка пульса. Возвращает (ок: bool, причина: str, чистый: dict).
    Кривой пульс не записываем — молча испорченная полка хуже отказа."""
    if not isinstance(d, dict):
        return False, "пульс не объект", {}
    pid = _chistyy_id(d.get("id", ""))
    if not pid:
        return False, "пустой или недопустимый id", {}
    imya = str(d.get("имя", "") or pid).strip()[:80]
    rod = str(d.get("род", "") or "").strip().lower()
    if rod not in RODY:
        return False, f"род должен быть одним из {RODY}, пришло «{rod}»", {}
    chisla = d.get("числа") or {}
    if not isinstance(chisla, dict):
        chisla = {}
    return True, "", {
        "id": pid,
        "имя": imya,
        "род": rod,
        "адрес": str(d.get("адрес", "") or "")[:200],
        "числа": chisla,
        "версия": str(d.get("версия", "") or "")[:40],
    }


def _polka(rod: str) -> Path:
    return OSTROVA_DIR if rod == "остров" else GORODA_DIR


# ═══════════════════════════════════════════════════════════
# СТОРОНА МАТЕРИКА — принять
# ═══════════════════════════════════════════════════════════

def prinyat(dannye: dict, klyuch: str = "") -> dict:
    """Принимает пульс и кладёт карточку на полку Маяка.

    Возвращает {"ok": bool, "причина": str, "id": str}.
    Карточка — ровно тот формат, что уже читает Хранитель Маяка
    (khranitel_mayaka._skan_polki): имя, адрес, последний_пульс.
    Плюс рядом журнал `пульсы.jsonl` — история, append-only, чтобы
    видеть не только последний удар, но и ритм.
    """
    if PULSE_KEY and klyuch != PULSE_KEY:
        return {"ok": False, "причина": "ключ не подошёл", "id": ""}

    ok, prichina, p = proverit_pulse(dannye)
    if not ok:
        return {"ok": False, "причина": prichina, "id": ""}

    teper = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dom = _polka(p["род"]) / p["id"]
    try:
        dom.mkdir(parents=True, exist_ok=True)
        kartochka_path = dom / "город.json"
        # первое знакомство помним отдельно — когда этот мир появился
        staroe = {}
        if kartochka_path.exists():
            try:
                staroe = json.loads(kartochka_path.read_text(encoding="utf-8"))
            except Exception:
                staroe = {}
        kartochka = {
            "id": p["id"],
            "имя": p["имя"],
            "род": p["род"],
            "адрес": p["адрес"],
            "версия": p["версия"],
            "числа": p["числа"],
            "первый_пульс": staroe.get("первый_пульс") or teper,
            "последний_пульс": teper,
            "пульсов": int(staroe.get("пульсов", 0)) + 1,
        }
        kartochka_path.write_text(
            json.dumps(kartochka, ensure_ascii=False, indent=2),
            encoding="utf-8")
        with (dom / "пульсы.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"когда": teper, "числа": p["числа"],
                                "версия": p["версия"]},
                               ensure_ascii=False) + "\n")
    except Exception as e:
        return {"ok": False, "причина": f"не записалось: {e}", "id": p["id"]}

    return {"ok": True, "причина": "", "id": p["id"]}


def kto_na_svyazi(molchit_chasov: float = 24.0) -> list:
    """Все миры с полок + давно ли молчат. Для отчётов и Хранителя.
    Возвращает [{"id","имя","род","часов_молчит","живой"}]."""
    out = []
    teper = datetime.now(timezone.utc)
    for polka, rod in ((GORODA_DIR, "город"), (OSTROVA_DIR, "остров")):
        if not polka.exists():
            continue
        for d in sorted(polka.iterdir()):
            if not d.is_dir():
                continue
            try:
                k = json.loads((d / "город.json").read_text(encoding="utf-8"))
            except Exception:
                continue
            chasov = None
            try:
                t = datetime.fromisoformat(str(k.get("последний_пульс", "")))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                chasov = round((teper - t).total_seconds() / 3600.0, 1)
            except Exception:
                pass
            out.append({
                "id": k.get("id", d.name),
                "имя": k.get("имя", d.name),
                "род": k.get("род", rod),
                "часов_молчит": chasov,
                "живой": (chasov is not None and chasov <= molchit_chasov),
                "пульсов": k.get("пульсов", 0),
            })
    return out


# ═══════════════════════════════════════════════════════════
# СТОРОНА ОСТРОВА — отправить
# ═══════════════════════════════════════════════════════════

async def otpravit(kuda: str, id: str, imya: str, rod: str = "остров",
                   chisla: dict = None, versia: str = "",
                   adres: str = "", klyuch: str = "",
                   timeout: float = 15.0) -> dict:
    """Шлёт пульс на материк. Зовётся С ОСТРОВА, из его собственного
    тика — материк никого не опрашивает (иначе он молчаливо становится
    начальником, и сеть равных не вырастет; решение 29.07).

    kuda — базовый адрес материка, напр. "http://localhost:8080"
    Возвращает {"ok": bool, "причина": str}.

    Обрыв связи — НЕ ошибка острова. Остров живёт дальше (Автономный
    Форт из Живой Книги: связь для обмена, не для жизни). Вызывающий
    просто пишет неудачу себе в журнал и работает как работал.
    """
    import httpx
    telo = {"id": id, "имя": imya, "род": rod,
            "числа": chisla or {}, "версия": versia, "адрес": adres}
    zagolovki = {"Content-Type": "application/json"}
    kl = klyuch or PULSE_KEY
    if kl:
        zagolovki[KEY_HEADER] = kl
    url = kuda.rstrip("/") + "/api/pulse"
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(url, json=telo, headers=zagolovki)
            if r.status_code != 200:
                return {"ok": False,
                        "причина": f"материк ответил {r.status_code}: {r.text[:200]}"}
            return r.json()
    except Exception as e:
        return {"ok": False, "причина": f"материк не отозвался: {e}"}


# ═══════════════════════════════════════════════════════════
# ПРОВЕРКА — песочница до зелёного, без острова
# ═══════════════════════════════════════════════════════════

async def _samoproverka(kuda: str = "http://localhost:8080"):
    """Шлёт фальшивый пульс самому себе. Нужен, чтобы довести причал
    до зелёного ДО того, как остров вообще появится."""
    print(f"── проверка причала · стучусь в {kuda}")
    rez = await otpravit(
        kuda=kuda,
        id="test-ostrov",
        imya="Тестовый остров (проверка причала)",
        rod="остров",
        chisla={"сделок": 0, "это": "проверка, не настоящий мир"},
        versia="проверка",
    )
    if rez.get("ok"):
        print(f"✓ пульс принят, id={rez.get('id','')}")
        print(f"  смотри полку: Маяк/острова/test-ostrov/")
        print(f"  спроси Хранителя Маяка — он должен увидеть новый мир")
        print(f"  карточку потом просто удали, она тестовая")
    else:
        print(f"✗ не принят: {rez.get('причина','')}")
        print("  город запущен? (python main.py) причал встроен в main.py?")
    return rez


if __name__ == "__main__":
    import sys as _s
    if "--проверить" in _s.argv or "--check" in _s.argv:
        import asyncio
        _kuda = "http://localhost:8080"
        for _i, _a in enumerate(_s.argv):
            if _a in ("--куда", "--to") and _i + 1 < len(_s.argv):
                _kuda = _s.argv[_i + 1]
        asyncio.run(_samoproverka(_kuda))
    else:
        print(__doc__)
        print("\nЧто на связи прямо сейчас:")
        for m in kto_na_svyazi():
            _s_ = "жив" if m["живой"] else "молчит"
            print(f"  · {m['имя']} ({m['род']}) — {_s_}, "
                  f"пульсов {m['пульсов']}")
        print("\nПроверить причал:  python Маяк/prichal.py --проверить")


# PRICHAL_V1 — маркер идемпотентности
