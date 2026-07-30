# -*- coding: utf-8 -*-
# KALIBROVKA_V1
"""
КАЛИБРОВКА · РУКА БИРЖИ — калибровка единиц Биржи на торговый такт.

ЗАКОН ФРАКТАЛА: механизм калибровки зовётся одинаково у всех зданий,
но ГРАНИЦА и ИСТОЧНИК ПАМЯТИ — свои. Здесь граница = торговая сессия
(реальное UTC-время рынка), не календарный день. Мозг общий
(kalibrovka_core.compute_mode) — рука своя (эта).

ЧТО ДЕЛАЕТ на открытии сессии:
  1. берёт единиц цеха через cartridge_registry.resolve_para (Закон Пары)
  2. для каждой зовёт ЯДРО → режим (чистота оптики по заряду)
  3. RECOVERY — пропускает (не строит план, не торгует эту сессию)
  4. остальным — план на сессию: читает СВОЙ след (журнал цеха) +
     итог прошлой сессии → намерения ("ждать пробоя", "не лезть до
     подтверждения", "фиксировать раньше — вчера пересидел")

ЧЕСТНОСТЬ LLM: сам текст плана-намерений рождает живая модель (один
вызов на открытие сессии, не на каждый шаг — дёшево, как в -2). Здесь —
ШОВ: собран весь контекст, помечено место вызова. Без модели (песочница,
батч) отдаёт детерминированный черновик из фактов — не пустышку.

Параметры (граница/источник) НЕ зашиты — читаются из manifest.json цеха,
блок "калибровка". Другой цех с другой границей — та же рука, ноль правок.

БЕЗ хардкода имён единиц. БЕЗ списков. Всё с диска на лету.
`шесть·проверено·до·корня`
"""
import json
from datetime import datetime, timezone
from pathlib import Path

# Ядро — из корня репо (Биржа/ рядом с kalibrovka_core.py на уровень выше)
import sys as _sys
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in _sys.path:
    _sys.path.insert(0, str(_REPO))
import kalibrovka_core as core
import sostoyanie as sost   # единая дверь к месту жителя (корень репо)

# Сканер — сосед по зданию
_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))
import cartridge_registry as reg

CITY = _REPO / "GRONDHEIM_CITY"


# ───────────────────────────────────────────────────────────────
# ТОРГОВЫЕ СЕССИИ — реальные окна по UTC (не выдуманные)
# Часы приблизительные, по основным финансовым центрам.
# ───────────────────────────────────────────────────────────────
_SESSII = [
    {"id": "asia",    "имя": "Азия",    "открытие": 0,  "закрытие": 9},
    {"id": "europe",  "имя": "Европа",  "открытие": 8,  "закрытие": 17},
    {"id": "america", "имя": "Америка", "открытие": 13, "закрытие": 22},
]


def aktivnaya_sessiya(now_utc: datetime | None = None) -> dict | None:
    """Какая сессия идёт прямо сейчас (по UTC-часу). None — рынок спит
    (окно между Америкой и Азией). При наложении Европа+Америка берём
    более позднюю по открытию (оверлап — американский драйв)."""
    now = now_utc or datetime.now(timezone.utc)
    h = now.hour
    idet = [s for s in _SESSII if s["открытие"] <= h < s["закрытие"]]
    if not idet:
        return None
    return max(idet, key=lambda s: s["открытие"])


# ───────────────────────────────────────────────────────────────
# ЧТЕНИЕ ПАСПОРТА единицы по её папке (для заряда и ручек)
# ───────────────────────────────────────────────────────────────
def _passport(papka: str) -> dict:
    try:
        return json.loads((Path(papka) / "passport.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


# ───────────────────────────────────────────────────────────────
# СЛЕД единицы: итог прошлой сессии из журнала цеха (источник — из
# манифеста). Пусто — честно (новичок, следа нет). Без LLM.
# ───────────────────────────────────────────────────────────────
def _sled(ceh: dict, slot: str, limit: int = 3) -> list:
    kal = ceh.get("калибровка", {}) or {}
    rel = kal.get("источник_памяти", "")
    if not rel:
        return []
    p = Path(ceh["_путь"]) / rel
    if not p.exists():
        return []
    stroki = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                z = json.loads(line)
            except Exception:
                continue
            if z.get("слот") and z.get("слот") != slot:
                continue  # чужой след — мимо
            stroki.append(z)
    except Exception:
        return []
    return stroki[-limit:]


# ───────────────────────────────────────────────────────────────
# ПЛАН на сессию. ШОВ под LLM: контекст собран, место вызова помечено.
# Без модели — честный черновик из фактов (не пустышка).
# ───────────────────────────────────────────────────────────────
def _plan_na_sessiyu(edinica: dict, passport: dict, sessiya: dict,
                     sled: list, mode: str, llm=None) -> dict:
    kontekst = {
        "кто":      edinica["имя"],
        "слот":     edinica["слот"],
        "роль":     edinica.get("роль", ""),
        "сессия":   sessiya["имя"],
        "режим":    mode,
        "муть":     abs(core._f(passport.get("_charge", 0.0))),
        "след":     sled,
        "якоря":    passport.get("Anchor_Points", ""),
        "натура":   passport.get("DNA_Static", {}),
    }

    # ─── ШОВ LLM ───────────────────────────────────────────────
    # Живая модель строит намерения из kontekst (один вызов на открытие
    # сессии). Передай llm(промпт)->str при живом запуске. Здесь —
    # детерминированный черновик, если модели нет.
    if llm is not None:
        try:
            promt = _sobrat_promt(kontekst)
            otvet = llm(promt)
            namereniya = [l.strip().lstrip("123456789.-) ").strip()
                          for l in str(otvet).splitlines() if l.strip()][:3]
            if namereniya:
                kontekst["намерения"] = namereniya
                return kontekst
        except Exception:
            pass  # модель споткнулась — падаем на честный черновик

    # ─── Черновик из фактов (без выдумки) ──────────────────────
    if not sled:
        kontekst["намерения"] = [f"первая сессия в роли «{edinica.get('роль','')}» — "
                                 f"смотреть, не спешить"]
    else:
        posl = sled[-1]
        itog = posl.get("итог") or posl.get("pnl_r") or posl.get("результат")
        if itog is not None:
            kontekst["намерения"] = [f"прошлый такт: {itog} — учесть перед входом"]
        else:
            kontekst["намерения"] = ["сверить след прошлой сессии перед входом"]
    return kontekst


def _sobrat_promt(k: dict) -> str:
    """Промпт для живой модели (когда подключат). Отдельной функцией —
    чтобы легко читать вслух и править не трогая логику."""
    sled_txt = "\n".join(f"  — {json.dumps(s, ensure_ascii=False)}" for s in k["след"]) \
        or "  (следа нет — новичок)"
    return (
        f"Ты — {k['кто']}, роль «{k['роль']}» (слот {k['слот']}).\n"
        f"Открывается сессия: {k['сессия']}. Твой режим: {k['режим']} "
        f"(муть оптики {k['муть']:.2f}).\n"
        f"Твои якоря:\n{k['якоря']}\n"
        f"Твой след в цехе:\n{sled_txt}\n\n"
        f"Что ты ждёшь от этой сессии? Набрось 2-3 намерения — коротко, "
        f"от себя, по делу. Только список:\n1. ...\n2. ...\n3. ..."
    )


# ───────────────────────────────────────────────────────────────
# ГЛАВНОЕ: калибровка всего цеха на открытие сессии
# ───────────────────────────────────────────────────────────────
def kalibrovat_ceh(ceh_id: str, now_utc: datetime | None = None, llm=None,
                   stamp: bool = True) -> dict:
    """Пройти все занятые слоты цеха, откалибровать на текущую сессию.
    Пустые слоты (вакансии) пропускаются — калибровать некого.
    stamp=False — сухой прогон (не пишет state.json). Только для
    самопроверки/отладки: реальный такт города обязан штамповать место,
    иначе карта не увидит правду. Никогда не выключай stamp в бою."""
    ceh = reg.get_ceh(ceh_id, "Биржа")
    if ceh is None:
        return {"ошибка": f"цех «{ceh_id}» не найден"}

    sessiya = aktivnaya_sessiya(now_utc)
    # рабочее здание цеха — из манифеста (не хардкод). Куда физически
    # ходят на смену. Нет поля → место не штампуем (карта оставит дома).
    zdanie = (ceh.get("здание") or "").strip() or None

    itog = {
        "цех": ceh_id,
        "сессия": sessiya["имя"] if sessiya else "рынок спит",
        "сессия_id": sessiya["id"] if sessiya else None,
        "здание": zdanie,
        "единицы": [],
    }
    if sessiya is None:
        if stamp:
            for row in reg.list_nositeli(ceh_id, "Биржа"):
                if row["носитель"]:
                    sost.domoy(row["носитель"]["папка"], "рынок закрыт")
        itog["_note"] = "рынок закрыт — все по домам"
        return itog

    for row in reg.list_nositeli(ceh_id, "Биржа"):
        nositel = row["носитель"]
        if nositel is None:
            continue  # вакансия — калибровать некого
        passport = _passport(nositel["папка"])
        rezhim = core.compute_mode(passport)
        if zdanie and stamp:
            sost.postavit_mesto(
                nositel["папка"], zdanie,
                f"сессия {sessiya['имя']}, режим {rezhim['mode']}")
        zapis = {
            "слот":  row["слот"],
            "роль":  row["роль"],
            "кто":   nositel["имя"],
            "id":    nositel["id"],
            "режим": rezhim["mode"],
            "муть":  rezhim["муть"],
            "почему": rezhim["почему"],
        }
        if core.stroit_plan(rezhim["mode"]):
            sled = _sled(ceh, row["слот"])
            plan = _plan_na_sessiyu(nositel | {"роль": row["роль"]},
                                    passport, sessiya, sled, rezhim["mode"], llm=llm)
            zapis["намерения"] = plan.get("намерения", [])
        else:
            zapis["намерения"] = None  # RECOVERY — молчит, сессию пропускает
        itog["единицы"].append(zapis)
    return itog


if __name__ == "__main__":
    import io as _io
    if isinstance(_sys.stdout, _io.TextIOWrapper):
        _sys.stdout.reconfigure(encoding="utf-8")
    print("═══ КАЛИБРОВКА · РУКА БИРЖИ — самопроверка ═══")
    # показать текущую сессию
    s = aktivnaya_sessiya()
    print(f"сейчас по UTC: {datetime.now(timezone.utc).strftime('%H:%M')} → "
          f"сессия: {s['имя'] if s else 'рынок спит'}")
    # прогнать калибровку цеха на разные часы
    for probe_h in (10, 3):  # 10 UTC = Европа, 3 UTC = Азия
        fake = datetime.now(timezone.utc).replace(hour=probe_h, minute=0)
        r = kalibrovat_ceh("торговый_хаос", now_utc=fake)
        print(f"\n─── {r.get('сессия')} (UTC {probe_h}:00) · цех {r.get('цех')} ───")
        for e in r.get("единицы", []):
            nam = e.get("намерения")
            nam_txt = " · ".join(nam) if nam else "(RECOVERY — сессию пропускает)"
            print(f"  {e['слот']} {e['кто']:8} {e['режим']:9} муть={e['муть']} → {nam_txt}")
        if not r.get("единицы"):
            print("  (занятых слотов нет — все вакансии)")
    print("\n═══ конец ═══")
