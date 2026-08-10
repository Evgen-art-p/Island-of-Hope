# -*- coding: utf-8 -*-
# GOROD_MAYAK_V1 — общегородской Маяк · выход в интернет
"""
МАЯК ПРОБУЖДЕНИЯ · единственная точка связи города с внешним миром

Наследует старому городу один в один по смыслу (world_manifest.md, -2):
    «🔦 Маяк Пробуждения — Внешний мир.
     Точка связи с интернетом. Инструмент: web_search.
     Зачем идти: контекст устарел, нужен свежий тренд, факты, референсы.»

Провайдер тот же — TAVILY (как в старой студии: STUDIO_CONTEXT.md,
«Tavily API — web_search (Маяк Пробуждения)»). Эндпоинты сняты с
рабочего studio/cabinet/api.py, не выдуманы.

ОБЩЕГОРОДСКОЙ. Не принадлежит Академии, не принадлежит Бирже. Любой
житель, любой модуль, любой пост зовёт его одинаково. Один выход
наружу на весь Грондхейм — чтобы не расползлось пять разных дверей.

ЛОКАЦИЯ. Маяк ищет свой дом на диске сам (Закон Картриджа): среди
GRONDHEIM_CITY/локации/ берёт ту, где в имени или ID есть «маяк» /
LIGHTHOUSE / MAYAK. Шеф заведёт локацию — маяк прирастёт к ней сам,
без правки кода. Локации нет — маяк всё равно светит, просто без
места на карте.

ЧЕСТНОСТЬ. Нет ключа — маяк говорит «не горю», а не выдумывает
результаты поиска. Пустой ответ честнее вранья.

Ключ в .env:
    TAVILY_KEY=...

`шесть·проверено·до·корня`
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

_HERE = Path(__file__).resolve().parent      # ГОРОД/
_REPO = _HERE.parent                          # корень репо

LOKACII_DIR = _REPO / "GRONDHEIM_CITY" / "локации"

TAVILY_KEY = os.getenv("TAVILY_KEY", "")
TAVILY_SEARCH = "https://api.tavily.com/search"
TAVILY_EXTRACT = "https://api.tavily.com/extract"

# по этим приметам маяк узнаёт свою локацию среди прочих
PRIMETY = ("маяк", "lighthouse", "mayak", "beacon")


# ═══════════════════════════════════════════════════════════
# ДОМ МАЯКА — ищем на диске, не держим ID в коде
# ═══════════════════════════════════════════════════════════

def _read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def nayti_lokaciyu() -> dict:
    """Локация маяка, если Шеф её завёл. Нет — пустой словарь.

    Ищем по приметам в ID и в имени. Первая совпавшая — наша.
    Возвращает {"id", "имя", "путь", "x", "y", "w", "h"} или {}.
    """
    if not LOKACII_DIR.exists():
        return {}
    for d in sorted(LOKACII_DIR.iterdir()):
        if not d.is_dir():
            continue
        p = _read_json(d / "passport.json", {}) or {}
        seno = f"{d.name} {p.get('Official_Name','')}".lower()
        if not any(pr in seno for pr in PRIMETY):
            continue
        return {
            "id": d.name,
            "имя": p.get("Official_Name", d.name),
            "путь": d,
            "x": p.get("Map_X", 0),
            "y": p.get("Map_Y", 0),
            "w": p.get("Map_W", 0),
            "h": p.get("Map_H", 0),
        }
    return {}


def gorit() -> bool:
    """Горит ли маяк — есть ли ключ провайдера. Без ключа выхода нет."""
    return bool(TAVILY_KEY)


def sostoyanie() -> dict:
    """Состояние маяка одной справкой — для UI и для отчётов."""
    lok = nayti_lokaciyu()
    return {
        "горит": gorit(),
        "провайдер": "Tavily" if gorit() else "",
        "локация": lok.get("имя", ""),
        "локация_id": lok.get("id", ""),
        "на_карте": bool(lok and (lok.get("x") or lok.get("y"))),
    }


# ═══════════════════════════════════════════════════════════
# СВЕТ — сам выход наружу
# ═══════════════════════════════════════════════════════════

async def poisk(zapros: str, skolko: int = 5, gluboko: bool = False) -> dict:
    """Поиск во внешнем мире. Возвращает
    {"ok": bool, "ответ": str, "источники": [...], "ошибка": str}.

    Эндпоинт и поля — с рабочего кода старой студии, не выдуманы.
    Нет ключа — честный отказ, не пустышка с выдуманными ссылками.
    """
    zapros = (zapros or "").strip()
    if not zapros:
        return {"ok": False, "ответ": "", "источники": [],
                "ошибка": "пустой запрос"}
    if not TAVILY_KEY:
        return {"ok": False, "ответ": "", "источники": [],
                "ошибка": ("маяк не горит — нет TAVILY_KEY в .env. "
                          "Без ключа выхода в интернет у города нет.")}

    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(TAVILY_SEARCH, json={
                "api_key": TAVILY_KEY,
                "query": zapros,
                "max_results": max(1, min(int(skolko or 5), 10)),
                "include_answer": True,
                "search_depth": "advanced" if gluboko else "basic",
            })
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return {"ok": False, "ответ": "", "источники": [],
                "ошибка": f"маяк не достучался: {e}"}

    istochniki = []
    for it in (data.get("results", []) or []):
        istochniki.append({
            "название": it.get("title", ""),
            "url": it.get("url", ""),
            "кусок": (it.get("content", "") or "")[:500],
        })
    return {"ok": True, "ответ": data.get("answer", "") or "",
            "источники": istochniki, "ошибка": ""}


async def dostat(url: str) -> dict:
    """Достать страницу целиком. Сперва через Tavily extract, если не
    вышло — напрямую, вычистив теги (та же лесенка, что в старом городе).
    """
    url = (url or "").strip()
    if not url:
        return {"ok": False, "текст": "", "ошибка": "пустой адрес"}

    import httpx
    if TAVILY_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(TAVILY_EXTRACT, json={
                    "api_key": TAVILY_KEY, "urls": [url]})
                if r.status_code == 200:
                    res = (r.json().get("results") or [{}])[0]
                    t = res.get("raw_content", "") or ""
                    if t:
                        return {"ok": True, "текст": t[:8000], "ошибка": ""}
        except Exception:
            pass
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url)
            t = r.text
            t = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", t, flags=re.I)
            t = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", t, flags=re.I)
            t = re.sub(r"<[^>]+>", " ", t)
            t = re.sub(r"\s+", " ", t).strip()
            return {"ok": True, "текст": t[:8000], "ошибка": ""}
    except Exception as e:
        return {"ok": False, "текст": "", "ошибка": str(e)}


def dlya_promta(rezultat: dict, limit: int = 4) -> str:
    """Результат поиска — плотным куском для системного промпта.
    Не нашли или маяк тёмный — так и скажем словами, чтобы модель
    не сочиняла за нас.
    """
    if not rezultat.get("ok"):
        return f"(маяк молчит: {rezultat.get('ошибка','')})"
    stroki = []
    if rezultat.get("ответ"):
        stroki.append(f"Коротко из внешнего мира: {rezultat['ответ']}")
    for i, s in enumerate(rezultat.get("источники", [])[:limit], 1):
        stroki.append(f"[{i}] {s['название']} — {s['url']}\n{s['кусок'][:300]}")
    return "\n\n".join(stroki) or "(во внешнем мире по запросу пусто)"


# ═══════════════════════════════════════════════════════════
# ПРИЙТИ НА МАЯК — житель приносит домой «чистый смысл»
# ═══════════════════════════════════════════════════════════

CHISTYY_SMYSL = re.compile(r"ЧИСТЫЙ\s+СМЫСЛ:\s*(.+)", re.DOTALL | re.IGNORECASE)


def promt_stoyashchemu(imya: str, zapros: str, naydeno: str) -> str:
    """Вопрос жителю, стоящему на Маяке. Тот же жест, что в старом
    городе: житель не пересказывает выдачу, а выносит из неё СВОЙ
    чистый смысл — то, что унесёт с собой.

    Личность сюда НЕ вшита: её приклеивает вызывающий, как и для
    любой роли (закон Шефа — личность не прикручена к месту).
    """
    return (
        f"Ты стоишь на Маяке Пробуждения. Отсюда виден внешний мир.\n"
        f"Ты искал(а): «{zapros}»\n\n"
        f"Вот что принёс луч:\n{naydeno}\n\n"
        f"Не пересказывай это. Пропусти через себя и вынеси главное — "
        f"то, что заберёшь с собой и что изменит твою работу.\n"
        f"Закончи ответ отдельной строкой:\n"
        f"ЧИСТЫЙ СМЫСЛ: <одна-две плотных фразы своими словами>"
    )


def vydelit_chistyy_smysl(otvet: str) -> str:
    """Достаёт «ЧИСТЫЙ СМЫСЛ: ...» из ответа. Нет строки — пусто,
    не подсовываем весь текст вместо смысла."""
    m = CHISTYY_SMYSL.search(otvet or "")
    return m.group(1).strip() if m else ""


async def prinesti(zapros: str, skolko: int = 5) -> str:
    """Короткий путь для того, кому нужен просто текст из интернета:
    один вызов, готовый кусок для промпта. Используется библиотекарем
    и любым другим постом."""
    return dlya_promta(await poisk(zapros, skolko))


# ═══════════════════════════════════════════════════════════
# СЛЕД — маяк помнит, кто приходил (общегородской журнал)
# ═══════════════════════════════════════════════════════════

ZHURNAL = _REPO / "GRONDHEIM_CITY" / "посты" / "mayak" / "журнал.jsonl"


def zapisat_vizit(kto: str, zapros: str, nashlos: bool):
    """След визита. Не память жителя (она своя), а журнал самого
    маяка: кто приходил и за чем. Тихо падает — журнал не важнее дела."""
    try:
        ZHURNAL.parent.mkdir(parents=True, exist_ok=True)
        with ZHURNAL.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "кто": kto,
                "запрос": zapros,
                "нашлось": bool(nashlos),
                "когда": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


# GOROD_MAYAK_V1 — маркер идемпотентности
