# -*- coding: utf-8 -*-
# TORG_STOL_V2 — КАБИНЕТ СОВЕТА (перенос ui_exchange.py на новые правила единиц)
"""
БИРЖА · КАБИНЕТ СОВЕТА · /torg/{tseh_id}

ЭТО ТОТ ЖЕ КАБИНЕТ, что был studio/economy/ui_exchange.py в -2 — тот же
хедер-пузырьки, та же левая колонка (загрузчик+полка активов), тот же
стол (тулбар РЫНОК/тест-реал + чат + отчёт-вьюер), та же правая колонка
(аватар+приборы). Систему торговли (Вильямс, психология агентов,
run_iskra/run_morj/...) НЕ ПЕРЕДЕЛЫВАЛИ — она приходит из движковых
модулей (iskra_live.py и т.д.), которые лежат рядом в Бирже.

ЧТО ДЕЙСТВИТЕЛЬНО ПОМЕНЯЛОСЬ (новые правила единиц):
  Старый мир: TRADING_COUNCIL — захардкоженный список id/label/icon,
  аватар — статика studio/modules/trading/AXX/... .
  Новый мир: пузырьки — РЕАЛЬНЫЙ состав, читается через Закон Пары
  (cartridge_registry.resolve_para/list_nositeli). Кто сидит в A01 —
  решает mask.json резидента (Workshop_ID+Turbo_Role), не код здесь.
  Аватар/имя — из паспорта резидента, а не из статичной папки.

СОСТАВ СОВЕТА БИРЖИ (два цеха разом, как было одним экраном в -2):
  торговый_хаос: A01 A02 A03 A04 A06 A07 A08 (7 слотов-воркеров)
  контора:       архивариус, исполнитель (штаб, общий на всю Биржу)
  Здесь это один и тот же экран (Совет всегда виделся целиком) —
  Состав читается из манифестов цехов (SOSTAV_S_DISKA_V1), иконки —
  как в старом TRADING_COUNCIL (A05=архивариус, A09=исполнитель).

Промпт роли — СОБСТВЕННОСТЬ ЦЕХА (слоты/A0X/промпт.md в manifest),
не резидента. Резидент — просто кто сегодня на смене (Закон Дежурства).

`шесть·проверено·до·корня`
"""
import sys
import json
import queue
from pathlib import Path
from datetime import datetime, timezone
import asyncio

from nicegui import ui, app, events

_HERE = Path(__file__).resolve().parent          # Биржа/
_REPO = _HERE.parent                              # корень репо
for _p in (_REPO, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import cartridge_registry as reg
import llm  # BIRZHA_MODEL_SEL_V1: переключатель модели -- set_model()/get_model()

# BIRZHA_MODEL_SEL_V1: тот же каталог, что в кабинете Брата (ui_brat.py).
# Дефолт -- GPT-4o mini (решение Шефа, 26.07: "одну оставить, проще" --
# она и график по числам Вильямса читает, и считает, vision не нужен
# никому в Совете сейчас -- ни один агент картинку не видит, llm.chat_with_images
# существует, но не подключён ни к одному слоту).
MODELS_CATALOG = [
    {"id": "openai/gpt-4o-mini-2024-07-18",    "name": "GPT-4o mini",      "price": "$0.15/$0.60"},
    {"id": "google/gemini-2.5-flash",          "name": "Gemini 2.5 Flash",  "price": "$0.15/$0.60"},
    {"id": "anthropic/claude-haiku-4-5",       "name": "Claude Haiku 4.5",  "price": "$1/$5"},
    {"id": "deepseek/deepseek-chat",           "name": "DeepSeek V3",       "price": "$0.14/$0.28"},
    {"id": "meta-llama/llama-3.3-70b-instruct","name": "Llama 3.3 70B",     "price": "$0.10/$0.32"},
    {"id": "anthropic/claude-sonnet-4-5",      "name": "Claude Sonnet 4.5", "price": "$3/$15"},
]
# GEMINI_PO_UMOLCHANIYU_V1: открываемся на модели, которая ВИДИТ кадр.
# Проверено Шефом на одном и том же кадре: 4o mini читал «Аллигатор спит,
# линии переплетены» там, где линии разведены и AO растёт. Цена та же,
# переключатель на месте — это только чем открывается кабинет.
DEFAULT_MODEL = next(
    (m["id"] for m in MODELS_CATALOG if m["id"].startswith("google/gemini")),
    MODELS_CATALOG[0]["id"])

import importlib.util
from typing import Any  # UI_TORG_TYPING_V1

_BRAIN_CACHE = {}


def _slot_brain(ceh_id: str, slot: str):
    """Закон Картриджа для кода: мозг слота живёт РЯДОМ с промптом
    (слоты/{slot}/мозг.py) — кабинет не хардкодит имена модулей, а
    спрашивает у цеха, что там реально лежит. Нет файла — честная
    вакансия мозга (None), не ошибка. Кэш на процесс — не грузим
    заново на каждый клик."""
    key = (ceh_id, slot)
    if key in _BRAIN_CACHE:
        return _BRAIN_CACHE[key]
    brain_path = (_REPO / "GRONDHEIM_CITY" / KVARTAL / "цеха" / ceh_id
                 / "слоты" / slot / "мозг.py")
    if not brain_path.exists():
        _BRAIN_CACHE[key] = None
        return None
    spec = importlib.util.spec_from_file_location(
        f"_brain_{ceh_id}_{slot}", brain_path)
    if spec is None or spec.loader is None:
        # UI_TORG_TYPING_V1: путь есть, но не опознан как модуль —
        # та же честная вакансия, что и "файла нет" строкой выше
        _BRAIN_CACHE[key] = None
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _BRAIN_CACHE[key] = mod
    return mod


KVARTAL = "Биржа"

# ── СОСТАВ СОВЕТА — порядок/иконки как в старом TRADING_COUNCIL ──────
# (ceh_id, реальный_слот_в_цехе, id_для_движка(A01..A09), иконка)
# SOSTAV_S_DISKA_V1: вбитого списка агентов здесь БОЛЬШЕ НЕТ — канон
# прямо запрещает кабинету его хранить (БИРЖА.md §2). Состав читается
# из манифестов цехов. Осталась табличка иконок: манифест их пока не
# знает, а появится в слоте поле «иконка» — возьмётся оно.
IKONKI_PO_SLOTU = {
    "A01": "✴️", "A02": "🦭", "A03": "😱", "A04": "🎯",
    "A06": "🪨", "A07": "🎲", "A08": "⚖️",
    "архивариус": "📚", "исполнитель": "🎬",
}
IKONKA_PO_UMOLCHANIYU = "🎓"

# Старые имена A05/A09 для штабных слотов: движок и отчёты кабинета
# зовут их так исторически, ломать эти имена — трогать полгорода.
STARYE_IMENA = {"архивариус": "A05", "исполнитель": "A09"}


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _avatar_url_for(papka: str, static_prefix: str) -> str:
    """Фото резидента — папка/аватар.* → путь статики (как ui_zhitel)."""
    if not papka:
        return ""
    dom = Path(papka)
    p = _read_json(dom / "passport.json") or {}
    av = p.get("avatar", "")
    if av and (dom / av).exists():
        return f"/{static_prefix}/{dom.name}/{av}"
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if (dom / ("avatar" + ext)).exists():
            return f"/{static_prefix}/{dom.name}/avatar{ext}"
    return ""


_LOKACII_DIR = _REPO / "GRONDHEIM_CITY" / "локации"
_BG_STATIC_MOUNTED = {"done": False}


def _building_bg_url(building_id: str) -> str:
    """Фон кабинета — картинка ЗДАНИЯ цеха (manifest['здание']), не
    захардкоженный старый /images/bg_main.jpg. Честно пусто, если у
    локации ещё нет image.*."""
    if not building_id:
        return ""
    dom = _LOKACII_DIR / building_id
    if not dom.exists():
        return ""
    if not _BG_STATIC_MOUNTED["done"]:
        try:
            app.add_static_files("/torg-bg", str(_LOKACII_DIR))
        except Exception:
            pass
        _BG_STATIC_MOUNTED["done"] = True
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if (dom / ("image" + ext)).exists():
            return f"/torg-bg/{building_id}/image{ext}"
    return ""


def _sostav_kvartala() -> list:
    """Кто вообще есть в квартале — по манифестам, а не по списку.

    Сколько слотов объявлено в цехах, столько и участников. Нет папки
    слота или нет мозга — участника нет, и это НЕ ошибка: слот просто
    не заведён. Один трейдер на всю Биржу — законное состояние.

    Штаб (тот цех, которого другие назвали своим штабом) идёт
    последним: он служба, а не цех.
    """
    ceha = reg.list_ceha(KVARTAL) or []
    shtaby = {c.get("штаб") for c in ceha if c.get("штаб")}
    ceha.sort(key=lambda c: (1 if c.get("id") in shtaby else 0, c.get("id", "")))

    out = []
    for c in ceha:
        if c.get("_битый"):
            continue
        ceh_id = c.get("id", "")
        put_slotov = Path(c.get("_путь", "")) / "слоты"
        for s in c.get("слоты", []):
            slot = s.get("слот")
            if not slot:
                continue
            if not (put_slotov / slot / "мозг.py").exists():
                continue          # слота нет — молча пропускаем
            out.append({
                "ceh_id": ceh_id,
                "slot": slot,
                "old_id": STARYE_IMENA.get(slot, slot),
                "role": s.get("роль", ""),
                "icon": (s.get("иконка") or IKONKI_PO_SLOTU.get(slot)
                         or IKONKA_PO_UMOLCHANIYU),
            })
    return out


def _build_roster(static_prefix: str) -> list:
    """Сводит цеха Биржи в один список пузырьков — Закон Пары решает,
    кто где сидит, эта функция просто собирает экран."""
    out = []
    for _z in _sostav_kvartala():
        ceh_id, slot = _z["ceh_id"], _z["slot"]
        old_id, icon, rol = _z["old_id"], _z["icon"], _z["role"]
        resident = reg.resolve_para(ceh_id, slot, KVARTAL)
        if resident:
            try:
                app.add_static_files(
                    f"/{static_prefix}/{Path(resident['папка']).name}",
                    resident["папка"])
            except Exception:
                pass
        out.append({
            "old_id": old_id,      # для вызовов движка (run_iskra и т.п.)
            "ceh_id": ceh_id,
            "slot": slot,
            "role": rol,
            "icon": icon,
            "resident": resident,  # None = вакансия
        })
    return out


def _agent_label(roster: list, old_id: str) -> str:
    for r in roster:
        if r["old_id"] == old_id:
            if r["resident"]:
                return r["resident"]["имя"]
            return r["role"] or old_id
    return old_id


def _agent_row(roster: list, old_id: str):
    for r in roster:
        if r["old_id"] == old_id:
            return r
    return None


def _bar_html(charge: float) -> str:
    """Живые показатели резидента — тот же вид, что в ui_zhitel.py
    (заряд/оптика), не свой отдельный виджет для Биржи."""
    mut = abs(charge)
    half = min(1.0, mut) * 50
    left = 50 if charge >= 0 else 50 - half
    znak = "+" if charge >= 0 else "\u2212"
    zcolor = "rgba(80,250,123,0.9)" if charge >= 0 else "rgba(255,120,120,0.9)"
    if mut < 0.25:
        optika, ocolor = "\u0447\u0438\u0441\u0442\u043e", "rgba(80,250,123,0.9)"
    elif mut < 0.55:
        optika, ocolor = "\u0440\u043e\u0432\u043d\u043e", "rgba(201,168,76,0.9)"
    elif mut < 0.8:
        optika, ocolor = "\u0448\u0442\u044b\u0440\u0438\u0442", "rgba(255,160,60,0.9)"
    else:
        optika, ocolor = "\u043a\u043e\u043b\u0431\u0430\u0441\u0438\u0442", "rgba(255,80,80,0.9)"
    return (
        '<div class="zpok">'
        f'<div class="zpok-row"><div class="zpok-lab">\u0437\u0430\u0440\u044f\u0434<b>{znak}{mut:.2f}</b></div>'
        f'<div class="zpok-bar zpok-bar--zaryad"><div class="zpok-mid"></div>'
        f'<div class="zpok-fill" style="left:{left}%; width:{half}%; background:{zcolor};"></div></div></div>'
        f'<div class="zpok-row"><div class="zpok-lab">\u043e\u043f\u0442\u0438\u043a\u0430<b style="color:{ocolor};">{optika}</b></div>'
        f'<div class="zpok-bar"><div class="zpok-fill" style="width:{int((1-mut)*100)}%; background:{ocolor};"></div></div></div>'
        '</div>'
    )


TORG_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

:root{
  --bg: #050510;
  --text: #ffffff;
  --muted: #8899a6;
  --glass: rgba(13, 17, 23, 0.60);
  --stroke: rgba(255,255,255,0.10);
  --g: #00ff88;
  --b: #00ccff;
  --p: #bd00ff;
  --orange: #ff9500;
}

html, body { height: 100%; margin: 0; }
body{
  width:100vw;
  height:100vh;
  overflow:hidden !important;
  background: transparent !important;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

#bg{
  position: fixed;
  inset: 0;
  z-index: -1;
  background-size: cover;
  background-position: center;
  background-color: #050510;
}
#bg::after{
  content:'';
  position:absolute;
  inset:0;
  background: rgba(5,5,16,0.88);
}

.app-container{
  position: fixed;
  inset: 0;
  display: grid;
  width: 100vw;
  height: 100vh;
  grid-template-columns: 300px 1fr 260px;
  grid-template-rows: 80px 1fr;
  grid-template-areas:
    "header header header"
    "left   stage  right";
  gap: 20px;
  padding: 20px;
  box-sizing: border-box;
}

.area-header{ grid-area: header; }
.area-left{ grid-area: left; min-height:0; }
.area-stage{ grid-area: stage; min-height:0; position: relative; overflow: hidden; }
.area-right{ grid-area: right; min-height:0; }

.glass{
  background: var(--glass);
  border: 1px solid var(--stroke);
  border-radius: 20px;
  backdrop-filter: blur(16px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.45);
  min-height: 0;
}

.squad-deck{
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 16px;
  gap: 15px;
  overflow-x: auto;
}

.avatar{
  width: 44px;
  height: 44px;
  border-radius: 999px;
  border: 2px solid rgba(255,255,255,0.14);
  background-size: cover;
  background-position: center 18%;  /* верхняя треть — лица не режет по центру */
  background-color: rgba(255,255,255,0.05);
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: rgba(255,255,255,0.92);
  font-weight: 800;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}
.avatar:hover{ border-color: rgba(0,204,255,0.40); transform: scale(1.05); }
.avatar.active{
  border-color: rgba(0,204,255,0.75);
  box-shadow: 0 0 0 2px rgba(0,204,255,0.25) inset, 0 0 30px rgba(0,204,255,0.35);
}
.avatar.working{
  border-color: rgba(255,149,0,0.75);
  animation: pulse 1.5s ease-in-out infinite;
}
.avatar.done{
  border-color: rgba(0,255,136,0.75);
  box-shadow: 0 0 0 2px rgba(0,255,136,0.25) inset, 0 0 30px rgba(0,255,136,0.35);
}
.avatar.vacant{
  border-style: dashed;
  opacity: 0.4;
  cursor: default;
}

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

.left-col{ height: 100%; display: flex; flex-direction: column; gap: 12px; min-height: 0; }

.client-panel{ flex-shrink: 0; overflow: hidden; }
.asset-bay{ height: auto; max-height: 340px; flex-shrink: 0; overflow: visible; }  /* ZAGRUZCHIK_SCROLL_V1: было 120px/hidden */
.settings-panel{ flex-grow: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }

.panel-title{
  padding: 12px 16px;
  color: rgba(255,255,255,0.92);
  font-weight: 900;
  letter-spacing: .12em;
  text-transform: uppercase;
  font-size: 11px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.panel-body{ padding: 12px 16px; min-height: 0; overflow: auto; }

.file-list{ padding: 8px 12px; max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 11px; }  /* ZAGRUZCHIK_SCROLL_V1: было 50px */
/* ZAGRUZCHIK_SCROLL_V1: стрелка раскрытия папок — видимый цвет */
.file-list .q-expansion-item .q-icon,
.file-list .q-item__section--side .q-icon{
  color: rgba(0,204,255,0.9) !important;
}
.file-list .q-expansion-item{ color: rgba(255,255,255,0.85); }


.right-col{ height: 100%; display: flex; flex-direction: column; justify-content: flex-start; gap: 12px; }
.right-top-slot{
  flex-shrink: 0;
  height: 240px;
  border-radius: 20px;
  border: 1px dashed rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.04);
  display: grid;
  place-items: center;
  color: rgba(255,255,255,0.55);
  font-size: 11px;
  padding: 12px;
  text-align: center;
  overflow: hidden;
}

.neon-btn{
  height: 56px;
  width: 100%;
  border-radius: 18px;
  background: transparent;
  color: rgba(255,255,255,0.92);
  border: 1px solid rgba(255,255,255,0.10);
  font-weight: 900;
  letter-spacing: .10em;
  cursor: pointer;
  transition: all 0.3s ease;
}
.neon-btn:disabled{ opacity: 0.4; cursor: not-allowed; }

.stage-monitor{ height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.stage-toolbar{
  height: 60px;
  display: grid;
  grid-template-columns: 200px 1fr 200px;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
  background: rgba(13, 17, 23, 0.95);
  backdrop-filter: blur(16px);
  z-index: 10;
}

.monitor-utils{ display:flex; gap: 12px; }
.stage-content{
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 18px;
  padding-bottom: 130px;
}

.split-view{ height: 100%; display: flex; gap: 18px; min-height: 0; overflow: hidden; }
.chat-log, .viewer{
  flex: 1;
  min-height: 0;
  min-width: 0;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 14px;
  font-family: monospace;
  font-size: 13px;
  color: rgba(255,255,255,0.86);
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-word;
}
.viewer{ border-color: rgba(0,204,255,0.30); }

.floating-console{
  position: absolute;
  left: 50%;
  bottom: 20px;
  transform: translateX(-50%);
  width: min(820px, calc(100% - 80px));
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 50px;
  background: rgba(13, 17, 23, 0.85);
  border: 1px solid rgba(255,255,255,0.15);
  backdrop-filter: blur(20px);
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}

.floating-console input{
  width: 100%;
  border-radius: 40px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.06);
  padding: 12px 16px;
  color: rgba(255,255,255,0.92);
  outline: none;
  font-family: monospace;
}

.send-button{
  border-radius: 40px !important;
  border: 2px solid rgba(0,204,255,0.55) !important;
  background: linear-gradient(135deg, rgba(0,204,255,0.30), rgba(189,0,255,0.25)) !important;
  color: rgba(255,255,255,0.98) !important;
  font-weight: 900 !important;
  padding: 12px 24px !important;
  cursor: pointer !important;
}

.chat-msg-user {
  background: rgba(0, 204, 255, 0.1);
  border-left: 3px solid rgba(0, 204, 255, 0.6);
  padding: 8px 12px;
  margin: 8px 0;
  border-radius: 0 8px 8px 0;
}
.chat-msg-assistant {
  background: rgba(0, 255, 136, 0.08);
  border-left: 3px solid rgba(0, 255, 136, 0.6);
  padding: 8px 12px;
  margin: 8px 0;
  border-radius: 0 8px 8px 0;
}
.chat-msg-system {
  color: rgba(255,255,255,0.5);
  font-style: italic;
  padding: 4px 0;
}

.zpok{ padding:10px 16px; display:flex; flex-direction:column; gap:9px; }
.zpok-row{ display:flex; flex-direction:column; gap:3px; }
.zpok-lab{ display:flex; justify-content:space-between; font-size:0.56rem;
  text-transform:uppercase; letter-spacing:0.08em; color:rgba(255,255,255,0.5); }
.zpok-lab b{ color:rgba(255,255,255,0.85); font-weight:700; }
.zpok-bar{ height:6px; border-radius:4px; background:rgba(255,255,255,0.08); overflow:hidden;
  position:relative; }
.zpok-bar--zaryad .zpok-fill{ position:absolute; top:0; bottom:0; }
.zpok-mid{ position:absolute; left:50%; top:-2px; bottom:-2px; width:1px;
  background:rgba(255,255,255,0.4); z-index:2; }
.zpok-fill{ height:100%; border-radius:4px; }

.nicegui-content { overflow: hidden !important; height: 100% !important; }
.area-stage { overflow: hidden !important; }
.area-stage > * { overflow: hidden !important; min-height: 0 !important; max-height: 100% !important; }
.stage-monitor { overflow: hidden !important; height: 100% !important; }
.stage-monitor > * { min-height: 0 !important; }
.stage-toolbar { flex-shrink: 0 !important; overflow: hidden !important; }
.stage-content { flex: 1 1 0 !important; min-height: 0 !important; overflow: hidden !important; max-height: calc(100% - 60px) !important; }
.stage-content > * { min-height: 0 !important; max-height: 100% !important; overflow: hidden !important; }
.split-view { height: 100% !important; min-height: 0 !important; overflow: hidden !important; }
.split-view > * { min-height: 0 !important; overflow: hidden !important; }
.chat-log, .viewer { flex: 1 1 0 !important; min-height: 0 !important; max-height: 100% !important; overflow-y: auto !important; overflow-x: hidden !important; }
"""


def page_torg(tseh_id: str = "торговый_хаос") -> None:
    """Кабинет Совета Биржи — тот же, что был /exchange в -2."""

    static_prefix = "torg-static"
    roster = _build_roster(static_prefix)

    # ── состояние страницы (как было в ui_exchange.py) ──────────
    state = {
        # POCHINIT_SOSTAV_V1: активным встаёт первый, кто реально есть
        # на диске. Состав собран строкой выше, поэтому берём прямо
        # здесь — раньше это стояло ДО создания state и роняло кабинет.
        # Пусто в квартале — пустая строка, и ничего не падает.
        "active_agent": (roster[0]["old_id"] if roster else ""),
        "chat_history": [],
        "reports": {},
        "uploaded_files": [],
        "loaded_assets": [],
        "active_asset": None,
        "iskra_signal": {},
        "iskra_last_run": None,
        "iskra_stats": {},
        "market": {},
        "running": False,
        "mode": "real",
        "bars_to_live": 1,
        "stop_requested": False,
        "tester_running": False,
        "learn": False,          # TORG_LEARN_SWITCH_V1: учебный прогон (якоря растут)
        "morj_last_run": None,
        "panic_last_run": None,
        "hans_last_run": None,
        "arkhiv_last_run": None,
        "arkhiv_signal": {},
        "arkhiv_stats": {},
        "arkhiv_digest": {},
        "model": DEFAULT_MODEL,   # BIRZHA_MODEL_SEL_V1
        # VAHTA_NOVAYA_SVECHA_V1: смотрим каждую новую свечу рабочего
        # этажа. Выключена по умолчанию — прогон платный, включать надо
        # осознанно.
        "vahta": False,
        "vahta_bar": "",
    }

    llm.set_model(state["model"])  # BIRZHA_MODEL_SEL_V1: применяем сразу при открытии кабинета

    def on_model_change(e):        # BIRZHA_MODEL_SEL_V1
        state["model"] = e.value
        llm.set_model(e.value)

    chat_log_ref: dict[str, Any] = {"element": None}
    toolbar_refs: dict[str, Any] = {}
    viewer_ref:   dict[str, Any] = {"element": None}
    kadr_ref:     dict[str, Any] = {"element": None}   # KABINET_GRAFIK_V1
    files_ref:    dict[str, Any] = {"element": None}
    avatar_ref:   dict[str, Any] = {"element": None}
    vitals_ref:   dict[str, Any] = {"element": None}   # заряд/оптика резидента — как везде в городе
    stats_ref:    dict[str, Any] = {"element": None}
    avatars_ref:  dict[str, Any] = {"elements": {}}
    input_ref:    dict[str, Any] = {"element": None}

    ui.add_head_html(f"<style>{TORG_CSS}</style>")
    _ceh0 = reg.get_ceh(tseh_id, KVARTAL)
    _bg_url = _building_bg_url(_ceh0.get("здание", "")) if _ceh0 else ""
    _bg_style = f" style=\"background-image:url('{_bg_url}');\"" if _bg_url else ""
    ui.html(f'<div id="bg"{_bg_style}></div>')

    # ── чат ───────────────────────────────────────────────────
    def update_chat_display():
        if not chat_log_ref["element"]:
            return
        chat_log_ref["element"].clear()
        with chat_log_ref["element"]:
            if not state["chat_history"]:
                ui.html('<div class="chat-msg-system">SYSTEM: Биржа готова.</div>')
            else:
                for msg in state["chat_history"]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    who = msg.get("agent", "")
                    if role == "user":
                        ui.html(f'<div class="chat-msg-user"><b>ШЕФ:</b> {content}</div>')
                    else:
                        ui.html(f'<div class="chat-msg-assistant"><b>{who}:</b> {content}</div>')

    # ── KABINET_GRAFIK_V1: кадр ──────────────────────────────
    def _aktivnyy_rynok() -> tuple:
        """Что сейчас на полке: символ и рабочий этаж.

        KABINET_VZGLYAD_V1: спрашиваем ПОЛКУ — тот самый актив, по
        которому Шеф кликнул слева. Раньше здесь спрашивались ключи,
        которых в кабинете нет, и ответ всегда был один и тот же
        (EURUSD H1) — кадр жил своей жизнью, Совет своей.
        Полка пуста — честный запасной вариант, как было в кнопке.
        """
        try:
            assets = state.get("loaded_assets", []) or []
            i = state.get("active_asset")
            if assets and i is not None and 0 <= i < len(assets):
                a = assets[i]
                s = (a.get("symbol") or "").strip()
                tf = (a.get("timeframe") or "").strip()
                if s and tf:
                    return s, tf
        except Exception:
            pass
        return "XAUUSD", "H4"

    def pokazat_kadr(put=None):
        """Рисует кадр и кладёт в верхнюю половину правой части.

        Модель не трогаем: Шеф смотрит, трейдер спит. Это и есть
        дешёвый способ проверить, читается ли картинка, ПЕРЕД тем как
        отдавать её глазу.
        """
        if not kadr_ref["element"]:
            return None
        symbol, tf = _aktivnyy_rynok()
        try:
            import grafik
            p = Path(put) if put else grafik.kadr(symbol, tf)
        except Exception as e:
            ui.notify(f"⚠ кадр не нарисовался: {e}", type="negative")
            return None
        if not p:
            ui.notify("⚠ кадр не нарисовался (нет matplotlib или баров)",
                      type="warning")
            return None
        kadr_ref["element"].clear()
        with kadr_ref["element"]:
            # KADR_NA_VES_KVADRAT_V1: тянемся на всю клетку, но БЕЗ
            # плющенья — contain держит пропорции свечей. Плющеная
            # свеча врёт глазу, а глаз у нас важнее цифры.
            ui.image(str(p)).style(
                "width:100%; height:100%; object-fit:contain; "
                "flex:1; min-height:0;")
            # KABINET_VZGLYAD_V1: подпись под кадром. Что смотрим и
            # каким краном — иначе глазом реал от истории не отличить.
            # KADR_NA_VES_KVADRAT_V1: плюс дата последнего бара —
            # живой рынок сегодняшним числом, тестер прошлогодним.
            _kran = "ТЕСТЕР" if state.get("mode") == "tester" else "РЕАЛ"
            _kogda = ""
            try:
                from feed_source import bars as _src_bars
                _bs, _ = _src_bars(symbol, tf, 3)
                if _bs:
                    _kogda = f" · {str(_bs[-1].get('date', ''))[:16]}"
            except Exception:
                pass
            ui.label(f"👁 {symbol} · {tf} · {_kran}{_kogda}").style(
                "color:rgba(139,233,253,0.75); font-size:11px; "
                "letter-spacing:0.06em; padding-top:6px; "
                "flex-shrink:0; width:100%; text-align:center;")
        return p

    def update_viewer(content: str):
        if not viewer_ref["element"]:
            return
        viewer_ref["element"].clear()
        with viewer_ref["element"]:
            ui.markdown(content)

    # ── аватар активного (правая колонка) — теперь РЕЗИДЕНТ ────
    def update_avatar():
        if not avatar_ref["element"]:
            return
        old_id = state["active_agent"]
        row = _agent_row(roster, old_id)
        label = _agent_label(roster, old_id)
        avatar_ref["element"].clear()
        with avatar_ref["element"]:
            av = _avatar_url_for(row["resident"]["папка"], static_prefix) if (row and row["resident"]) else ""
            img_html = (f'<img src="{av}" style="width:100%;height:100%;object-fit:cover;'
                       f'border-radius:12px;opacity:0.85;" onerror="this.style.display=\'none\'">'
                       if av else "")
            vacancy_note = "" if (row and row["resident"]) else '<div style="font-size:0.65rem;color:rgba(255,80,80,0.6);">вакансия</div>'
            ui.html(f'''
                <div style="position:relative; width:100%; height:100%; min-height:200px;">
                    {img_html}
                    <div style="position:absolute; bottom:0; left:0; right:0;
                                padding:15px; background:linear-gradient(transparent, rgba(0,0,0,0.8));
                                border-radius:0 0 12px 12px;">
                        <div style="font-size:0.65rem; color:rgba(255,255,255,0.5);
                                    letter-spacing:0.15em;">АКТИВНЫЙ АГЕНТ</div>
                        <div style="font-size:1.3rem; font-weight:700; color:#00ff88;">{old_id}</div>
                        <div style="font-size:0.8rem; color:rgba(255,255,255,0.8);">{label}</div>
                        {vacancy_note}
                    </div>
                </div>
            ''')

    # ── живые показатели резидента (заряд/оптика) — как везде в городе ──
    def update_vitals():
        if not vitals_ref["element"]:
            return
        vitals_ref["element"].clear()
        row = _agent_row(roster, state["active_agent"])
        with vitals_ref["element"]:
            if row and row["resident"]:
                p = _read_json(Path(row["resident"]["папка"]) / "passport.json") or {}
                charge = float(p.get("_charge", 0.0) or 0.0)
                ui.html(_bar_html(charge))
            else:
                ui.html('<div style="color:rgba(255,255,255,0.3); font-size:10px; '
                        'padding:8px 16px;">— вакансия, показывать нечего —</div>')

    # ── приборы под аватаром (перенесено без изменений по сути) ─
    def update_stats_panel():
        if not stats_ref["element"]:
            return
        sig = state["iskra_signal"]
        st  = state["iskra_stats"]
        mk  = state["market"]
        stats_ref["element"].clear()

        if state["active_agent"] == "A02":
            msig = state.get("morj_signal", {})
            mst  = state.get("morj_stats", {})
            rb   = state.get("morj_rubber", {})
            mmk  = state.get("morj_market", {})
            if not msig:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Морж ещё не смотрел — '
                            'нажми РЫНОК</div>')
                return
            mstatus = msig.get("morj_status", "—")
            st_color = {"AWAKE": "#00ff88", "WAKING": "#ffb400",
                        "SLEEPING": "rgba(255,255,255,0.4)"}.get(mstatus, "rgba(255,255,255,0.4)")
            peak = msig.get("tension_peak")
            peak_txt = "🔴 НА ПРЕДЕЛЕ" if peak else "вяло"
            peak_color = "#ff5050" if peak else "rgba(255,255,255,0.4)"
            ratio = rb.get("tension_ratio")
            ratio_txt = f"{ratio}" if ratio is not None else "—"
            dist = rb.get("distance_now")
            dist_txt = f"{dist} пт" if dist is not None else "—"
            wave1 = "✓" if msig.get("wave_1_validated") else "—"
            alst = (msig.get("alligator_state") or {})
            bopen = alst.get("bars_open", "—")
            with stats_ref["element"]:
                ui.html(f'''
                <div style="padding:10px 12px; font-family:\'JetBrains Mono\',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ПАСТЬ</span>
                    <span style="color:{st_color}; font-size:11px; font-weight:700;">{mstatus}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">РЕЗИНКА</span>
                    <span style="color:{peak_color}; font-size:11px; font-weight:700;">{peak_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">НАТЯЖЕНИЕ</span>
                    <span style="color:rgba(0,204,255,0.9); font-size:11px;">{ratio_txt} · {dist_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ВОЛНА 1 / БАРОВ ОТКРЫТ</span>
                    <span style="color:rgba(255,255,255,0.7); font-size:11px;">{wave1} · {bopen}</span>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                    взглядов: {mst.get("runs",0)} ·
                    проснулся: {mst.get("awake",0)} ·
                    спал: {mst.get("sleeping",0)} ·
                    пиков: {mst.get("tension_peaks",0)}
                    <br>{mmk.get("symbol","")} {mmk.get("timeframe","")} · {mmk.get("bar_time","")}
                  </div>
                </div>
                ''')
            return

        if state["active_agent"] == "A03":
            psig = state.get("panic_signal", {})
            pst  = state.get("panic_stats", {})
            pmk  = state.get("panic_market", {})
            if not psig:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Паникёр ещё не мерил толпу — '
                            'нажми РЫНОК</div>')
                return
            phase = psig.get("panic_phase", "—")
            ph_color = {"PANIC": "#ff5050", "GREED": "#ffb400",
                        "TENSION": "#ffb400", "DECEPTION": "#cc88ff",
                        "DISBELIEF": "rgba(0,204,255,0.9)",
                        "ASLEEP": "rgba(255,255,255,0.4)"}.get(phase, "rgba(255,255,255,0.7)")
            sentiment = psig.get("crowd_sentiment", "—") or "—"
            action = psig.get("action_for_traders", "—")
            act_color = {"GREEN_LIGHT_IF_GANS": "#00ff88",
                         "HIGH_SKEPTICISM": "#ffb400",
                         "NEUTRAL": "rgba(255,255,255,0.4)"}.get(action, "rgba(255,255,255,0.4)")
            with stats_ref["element"]:
                ui.html(f'''
                <div style="padding:10px 12px; font-family:\'JetBrains Mono\',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ТОЛПА</span>
                    <span style="color:{ph_color}; font-size:11px; font-weight:700;">{phase}</span>
                  </div>
                  <div style="margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">НАКАЛ</span>
                    <div style="color:rgba(255,255,255,0.7); font-size:10px; font-style:italic;
                                margin-top:3px; line-height:1.4;">«{sentiment}»</div>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">СВЕТОФОР</span>
                    <span style="color:{act_color}; font-size:11px; font-weight:700;">{action}</span>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                    замеров: {pst.get("runs",0)} ·
                    паник: {pst.get("panic",0)} ·
                    жадности: {pst.get("greed",0)} ·
                    скуки: {pst.get("asleep",0)}
                    <br>{pmk.get("symbol","")} {pmk.get("timeframe","")} · {pmk.get("bar_time","")}
                  </div>
                </div>
                ''')
            return

        if state["active_agent"] == "A04":
            hsig = state.get("hans_signal", {})
            hst  = state.get("hans_stats", {})
            hmk  = state.get("hans_market", {})
            if not hsig:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Ганс ещё не выходил на след — '
                            'нажми РЫНОК</div>')
                return
            valid = hsig.get("fractal_valid")
            v_txt = "🎯 ВНЕ КРАСНОЙ" if valid else "пусто"
            v_color = "#00ff88" if valid else "rgba(255,255,255,0.4)"
            side = hsig.get("fractal_side") or "—"
            fprice = hsig.get("fractal_price")
            fprice_txt = f"{fprice}" if fprice is not None else "—"
            absr = hsig.get("absorption_ratio")
            absr_txt = f"{absr}" if absr is not None else "—"
            abs_color = "#ff5050" if (absr is not None and absr >= 0.7) else "rgba(255,255,255,0.7)"
            with stats_ref["element"]:
                ui.html(f'''
                <div style="padding:10px 12px; font-family:\'JetBrains Mono\',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ФРАКТАЛ</span>
                    <span style="color:{v_color}; font-size:11px; font-weight:700;">{v_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">СТОРОНА</span>
                    <span style="color:rgba(255,255,255,0.7); font-size:11px;">{side}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ЦЕНА (ОРИЕНТИР)</span>
                    <span style="color:rgba(0,204,255,0.9); font-size:11px;">{fprice_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ПОГЛОЩЕНИЕ</span>
                    <span style="color:{abs_color}; font-size:11px;">{absr_txt}</span>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                    выходов: {hst.get("runs",0)} ·
                    добыча: {hst.get("valid",0)} ·
                    мёртвых: {hst.get("dead",0)} ·
                    пусто: {hst.get("none",0)}
                    <br>{hmk.get("symbol","")} {hmk.get("timeframe","")} · {hmk.get("bar_time","")}
                  </div>
                </div>
                ''')
            return

        if state["active_agent"] == "A05":
            asig = state.get("arkhiv_signal", {})
            ast  = state.get("arkhiv_stats", {})
            adg  = state.get("arkhiv_digest", {})
            if not asig and not adg:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Архивариус ещё не листал Атлас — '
                            'нажми РЫНОК</div>')
                return
            sample = asig.get("sample_size", adg.get("sample_size", 0))
            closed = adg.get("closed_trades", "—")
            success = asig.get("success_rate", adg.get("success_rate"))
            success_txt = f"{round(success*100)}%" if isinstance(success, (int, float)) else "—"
            conf = asig.get("arkhiv_confidence", adg.get("arkhiv_confidence", "—"))
            conf_color = {"HIGH": "#00ff88", "MEDIUM": "#ffb400",
                          "LOW": "rgba(255,255,255,0.45)"}.get(conf, "rgba(255,255,255,0.45)")
            reason = asig.get("top_failure_reason", adg.get("top_failure_reason", "—")) or "—"
            empty = (sample == 0)
            sample_color = "rgba(255,255,255,0.4)" if empty else "rgba(0,204,255,0.9)"
            sample_txt = "пусто — первый случай" if empty else f"{sample} (закрыто {closed})"
            with stats_ref["element"]:
                ui.html(f'''
                <div style="padding:10px 12px; font-family:\'JetBrains Mono\',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">СКЛАД</span>
                    <span style="color:{sample_color}; font-size:11px; font-weight:700;">{sample_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">УДАЧА</span>
                    <span style="color:rgba(255,255,255,0.7); font-size:11px;">{success_txt}</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">УВЕРЕННОСТЬ</span>
                    <span style="color:{conf_color}; font-size:11px; font-weight:700;">{conf}</span>
                  </div>
                  <div style="margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ЧАСТАЯ ПРИЧИНА ПОТЕРЬ</span>
                    <div style="color:rgba(255,255,255,0.7); font-size:10px; font-style:italic;
                                margin-top:3px; line-height:1.4;">«{reason}»</div>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                    взглядов: {ast.get("runs",0)} ·
                    HIGH: {ast.get("high",0)} ·
                    MEDIUM: {ast.get("medium",0)} ·
                    LOW: {ast.get("low",0)} ·
                    пусто: {ast.get("empty",0)}
                  </div>
                </div>
                ''')
            return

        # PRIBORY_TREJDEROV_V1: трейдеры (A06/A07/A08) — приборов не было ВООБЩЕ,
        # код падал сразу в заглушку ниже. Один шаблон на троих — та же
        # связка pre=brut/avan/cons, что уже использует _apply_agent_result.
        if state["active_agent"] in ("A06", "A07", "A08"):
            pre = {"A06": "brut", "A07": "avan", "A08": "cons"}[state["active_agent"]]
            _label = _agent_label(roster, state["active_agent"])
            tsig = state.get(f"{pre}_signal", {})
            tst  = state.get(f"{pre}_stats", {})
            if not tsig:
                with stats_ref["element"]:
                    ui.html(f'<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            f'padding:10px; text-align:center;">{_label} ещё не смотрел(а) '
                            f'стол — нажми РЫНОК</div>')
                return
            verdict = tsig.get(f"{pre}_verdict", "—")
            v_ok = (verdict == "APPROVED")
            v_color = "#00ff88" if v_ok else "rgba(255,255,255,0.5)"
            body = (
                '<div style="display:flex; justify-content:space-between; margin-bottom:7px;">'
                '<span style="color:rgba(255,255,255,0.45); font-size:10px;">ВЕРДИКТ</span>'
                f'<span style="color:{v_color}; font-size:11px; font-weight:700;">{verdict}</span></div>'
            )
            if v_ok:
                direction = tsig.get(f"{pre}_direction", "—") or "—"
                entry = tsig.get(f"{pre}_entry", "—")
                stop  = tsig.get(f"{pre}_stop", "—")
                lot   = tsig.get(f"{pre}_lot", "—")
                body += (
                    '<div style="display:flex; justify-content:space-between; margin-bottom:7px;">'
                    '<span style="color:rgba(255,255,255,0.45); font-size:10px;">НАПРАВЛЕНИЕ</span>'
                    f'<span style="color:rgba(0,204,255,0.9); font-size:11px; font-weight:700;">{direction}</span></div>'
                    '<div style="display:flex; justify-content:space-between; margin-bottom:7px;">'
                    '<span style="color:rgba(255,255,255,0.45); font-size:10px;">ВХОД / СТОП</span>'
                    f'<span style="color:rgba(255,255,255,0.7); font-size:11px;">{entry} / {stop}</span></div>'
                    '<div style="display:flex; justify-content:space-between; margin-bottom:10px;">'
                    '<span style="color:rgba(255,255,255,0.45); font-size:10px;">ЛОТ</span>'
                    f'<span style="color:rgba(255,255,255,0.7); font-size:11px;">{lot}</span></div>'
                )
            else:
                reason = tsig.get(f"{pre}_reason", "—") or "—"
                body += (
                    '<div style="margin-bottom:10px;">'
                    '<span style="color:rgba(255,255,255,0.45); font-size:10px;">ПРИЧИНА</span>'
                    '<div style="color:rgba(255,255,255,0.7); font-size:10px; font-style:italic;'
                    f'margin-top:3px; line-height:1.4;">«{reason}»</div></div>'
                )
            body += (
                '<div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;'
                'color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">'
                f'взглядов: {tst.get("runs","—")} · '
                f'входов: {tst.get("approved","—")} · '
                f'пасов: {tst.get("rejected","—")}</div>'
            )
            with stats_ref["element"]:
                ui.html(f'<div style="padding:10px 12px; '
                        f'font-family:\'JetBrains Mono\',monospace;">{body}</div>')
            return

        # PRIBORY_TREJDEROV_V1: Исполнитель (A09) — тоже приборов не было.
        if state["active_agent"] == "A09":
            esig = state.get("executor_signal", {})
            if not esig:
                with stats_ref["element"]:
                    ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                            'padding:10px; text-align:center;">Исполнитель ещё не '
                            'подводил итог — нажми РЫНОК</div>')
                return
            fdna = esig.get("final_dna", {})
            sent = fdna.get("orders_sent", "—")
            tsk  = fdna.get("task_score", "—")
            hist = esig.get("history_dna", "") or "—"
            with stats_ref["element"]:
                ui.html(f'''
                <div style="padding:10px 12px; font-family:'JetBrains Mono',monospace;">
                  <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">ОРДЕРОВ</span>
                    <span style="color:rgba(0,204,255,0.9); font-size:11px; font-weight:700;">{sent} из 3</span>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:rgba(255,255,255,0.45); font-size:10px;">TASK_SCORE</span>
                    <span style="color:rgba(255,255,255,0.7); font-size:11px;">{tsk}</span>
                  </div>
                  <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                              color:rgba(255,255,255,0.35); font-size:9px; line-height:1.4;">
                    {hist}
                  </div>
                </div>
                ''')
            return

        if state["active_agent"] != "A01":
            with stats_ref["element"]:
                ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                        'padding:10px; text-align:center;">Приборы появятся при подключении агента</div>')
            return

        t1 = sig.get("t1_status", "—")
        t1_color = {"DETECTED": "#ffb400", "CONFIRMED": "#00ff88",
                    "NOT_FOUND": "rgba(255,255,255,0.4)"}.get(t1, "rgba(255,255,255,0.4)")
        zero = sig.get("zero_point_price")
        zero_txt = f"{zero}" if zero else "—"
        bell = "🔔 ЗВОНИТ" if sig.get("exit_bell") else "—"
        bell_color = "#ff5050" if sig.get("exit_bell") else "rgba(255,255,255,0.4)"

        with stats_ref["element"]:
            ui.html(f'''
            <div style="padding:10px 12px; font-family:'JetBrains Mono',monospace;">
              <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                <span style="color:rgba(255,255,255,0.45); font-size:10px;">СТАТУС</span>
                <span style="color:{t1_color}; font-size:11px; font-weight:700;">{t1}</span>
              </div>
              <div style="display:flex; justify-content:space-between; margin-bottom:7px;">
                <span style="color:rgba(255,255,255,0.45); font-size:10px;">ТОЧКА НОЛЬ</span>
                <span style="color:rgba(0,204,255,0.9); font-size:11px;">{zero_txt}</span>
              </div>
              <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:rgba(255,255,255,0.45); font-size:10px;">КОЛОКОЛ</span>
                <span style="color:{bell_color}; font-size:11px;">{bell}</span>
              </div>
              <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;
                          color:rgba(255,255,255,0.35); font-size:9px; line-height:1.7;">
                прогонов: {st.get("runs",0)} ·
                нашла: {st.get("detected",0)} ·
                подтвердилось: {st.get("confirmed",0)} ·
                аннулировано: {st.get("annulled",0)}
                <br>{mk.get("symbol","")} {mk.get("timeframe","")} · {mk.get("bar_time","")}
              </div>
            </div>
            ''')

    # ── ТУМБЛЕР ТЕСТЕР/РЕАЛ + ПЕРЕБОР ИСТОРИИ + СТОП ─────────────

    def set_mode(mode: str):
        state["mode"] = mode
        try:
            from feed_source import set_feed_mode
            _sym = None
            _assets = state.get("loaded_assets", [])
            _ai = state.get("active_asset")
            if _assets and _ai is not None and 0 <= _ai < len(_assets):
                _sym = _assets[_ai].get("symbol")
            set_feed_mode(mode, _sym)
        except Exception as _e:
            print(f"[TORG] feed_source не подключён: {_e}")
        is_tester = (mode == "tester")
        for key in ("bars_input", "stop_btn", "bars_label",
                    "learn_btn"):   # TORG_LEARN_SWITCH_V1

            el = toolbar_refs.get(key)
            if el:
                el.style(f"display: {'flex' if is_tester else 'none'}")
        for key, m in (("mode_real", "real"), ("mode_tester", "tester")):
            el = toolbar_refs.get(key)
            if el:
                active = (m == mode)
                el.style(
                    "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                    "cursor:pointer;" + (
                        "background:rgba(0,255,136,0.15);color:#00ff88;"
                        "border:1px solid rgba(0,255,136,0.4);"
                        if active else
                        "background:rgba(255,255,255,0.03);color:rgba(255,255,255,0.45);"
                        "border:1px solid rgba(255,255,255,0.08);"
                    )
                )
        ui.notify(f"Режим: {'ТЕСТЕР (история)' if is_tester else 'РЕАЛ (живой рынок)'}",
                  type="info")

    def request_stop():
        if not state.get("tester_running"):
            ui.notify("Перебор не идёт", type="warning")
            return
        state["stop_requested"] = True
        ui.notify("⏸ СТОП — останавливаю на следующем кандидате...", type="info")

    def toggle_learn():
        """TORG_LEARN_SWITCH_V1: УЧИТЬ — писать ли выводы из сделок в живых жителей.

        Выкл (умолчание) — стерильно: смотрим, не калеча. Трейдер всё равно
        сидит за столом СОБОЙ (читающий конец души работает всегда), но
        паспорта не трогаются: якоря не растут, заряд не едет.
        Вкл — учебный прогон: рынок судит, вывод оседает в носителя.
        """
        if state.get("tester_running"):
            ui.notify("Идёт прогон — переключай до старта", type="warning")
            return
        state["learn"] = not state.get("learn", False)
        on = state["learn"]
        el = toolbar_refs.get("learn_btn")
        if el:
            el.style(
                "display:flex;align-items:center;padding:6px 14px;border-radius:7px;"
                "font-size:12px;font-weight:700;cursor:pointer;" + (
                    "background:rgba(189,0,255,0.15);color:#bd88ff;"
                    "border:1px solid rgba(189,0,255,0.45);"
                    if on else
                    "background:rgba(255,255,255,0.03);color:rgba(255,255,255,0.45);"
                    "border:1px solid rgba(255,255,255,0.08);"
                ))
        ui.notify(
            "🎓 УЧИТЬ включено: якоря жителей будут расти, заряд качаться"
            if on else
            "🧪 УЧИТЬ выключено: стерильно — паспорта жителей не трогаем",
            type="warning" if on else "info")

    def _apply_agent_result(aid, r, narrative):
        """
        Раскладывает результат ОДНОГО агента по state кабинета: аватары,
        пузырьки чата, вьюер отчёта, *_last_run (рабочая память для чата
        с агентом по клику на пузырёк).

        ОБЩАЯ функция для ОБОИХ путей пробуждения Совета -- РЫНОК
        (run_market) и ТЕСТЕР (run_tester_session). Раньше тестер эту
        память не писал вовсе: state[*_last_run] оставался пуст после
        тестового прогона, и чат с агентом сразу после ТЕСТЕРА честно,
        но неверно по сути отвечал "рынок не запускали" -- хотя агент
        только что отработал через ту же дверь (council.wake_council).
        Теперь оба пути кладут память сюда же -- один источник правды.
        """
        # ── A01 ИСКРА ──
        if aid == "A01":
            if not r.get("ok"):
                err = r.get("error", "неизвестная ошибка")
                state["chat_history"].append({
                    "role": "assistant", "agent": "A01", "content": f"⚠️ {err}"})
                update_chat_display()
                ui.notify(err, type="negative", timeout=6000)
                return
            state["active_agent"] = "A01"
            state["iskra_signal"] = r.get("signal", {})
            state["iskra_stats"]  = r.get("stats", {})
            state["market"]       = r.get("market", {})
            state["reports"]["A01"] = r.get("narrative", "") or r.get("raw", "")
            state["iskra_last_run"] = {
                "narrative": r.get("narrative", ""),
                "signal":    r.get("signal", {}),
                "market":    r.get("market", {}),
            }
            update_avatar()
            update_vitals()
            update_avatar_states()
            update_stats_panel()
            sig = state["iskra_signal"]
            update_viewer(
                f"# ✴️ {_agent_label(roster,'A01')} (A01)\n\n"
                f"**Статус:** {sig.get('t1_status','—')}  ·  "
                f"**Дивергенция:** {sig.get('divergence','—')}\n\n"
                f"---\n\n{r.get('narrative','') or '*(нет текста)*'}"
            )
            state["chat_history"].append({
                "role": "assistant", "agent": "A01",
                "content": f"✴️ Отработала рынок — статус {sig.get('t1_status','—')}. Отчёт справа."})
            update_chat_display()
            ui.notify(f"✴️ Искра: {sig.get('t1_status','—')}", type="positive")
            return

        # ── ошибка любого из остальных агентов ──
        if not r.get("ok"):
            _names = {"A02": ("🦭", "Морж"), "A03": ("😱", "Паникёр"),
                      "A04": ("🎯", "Ганс"), "A05": ("📚", "Архивариус"),
                      "A06": ("🪨", _agent_label(roster, "A06")),
                      "A07": ("⚡", _agent_label(roster, "A07")),
                      "A08": ("🛡", _agent_label(roster, "A08")),
                      "A09": ("📋", "Исполнитель")}
            icon, nm = _names.get(aid, ("•", aid))
            ui.notify(f"{icon} {nm} смолчал (нет данных или сбой)", type="warning")
            return

        sig = r.get("signal", {}) or {}

        # ── A02 МОРЖ ──
        if aid == "A02":
            rb = r.get("rubber_band", {})
            state["reports"]["A02"] = narrative
            state["morj_signal"] = sig
            state["morj_stats"]  = r.get("stats", {})
            state["morj_rubber"] = rb
            state["morj_market"] = r.get("market", {})
            state["morj_last_run"] = {
                "narrative":   r.get("narrative", ""),
                "signal":      sig,
                "market":      r.get("market", {}),
                "rubber_band": rb,
                "iskra_status": r.get("iskra_status", state.get("iskra_signal", {}).get("t1_status")),
            }
            state["active_agent"] = "A02"   # AGENT_LIVE_SWITCH_V1
            update_avatar()
            update_vitals()
            update_viewer(f"# 🦭 {_agent_label(roster,'A02')} (A02)\n\n{narrative or '*(нет текста)*'}")
            state["chat_history"].append({
                "role": "assistant", "agent": "A02",
                "content": (f"🦭 Посмотрел. Пасть: {sig.get('morj_status','—')}, резинка "
                            f"{'натянута' if sig.get('tension_peak') else 'вяло'}. Отчёт справа.")})
            update_chat_display()
            update_avatar_states()
            ui.notify(f"🦭 Морж: {sig.get('morj_status','—')}", type="positive")

        # ── A03 ПАНИКЁР ──
        elif aid == "A03":
            state["reports"]["A03"] = narrative
            state["panic_signal"] = sig
            state["panic_stats"]  = r.get("stats", {})
            state["panic_market"] = r.get("market", {})
            state["panic_last_run"] = {
                "narrative": r.get("narrative", ""), "signal": sig, "market": r.get("market", {})}
            state["active_agent"] = "A03"   # AGENT_LIVE_SWITCH_V1
            update_avatar()
            update_vitals()
            update_viewer(f"# 😱 {_agent_label(roster,'A03')} (A03)\n\n{narrative or '*(нет текста)*'}")
            state["chat_history"].append({
                "role": "assistant", "agent": "A03",
                "content": (f"😱 Толпа: {sig.get('panic_phase','—')}. "
                            f"{sig.get('crowd_sentiment','')} Отчёт справа.")})
            update_chat_display()
            update_avatar_states()
            ui.notify(f"😱 Паникёр: {sig.get('panic_phase','—')}", type="positive")

        # ── A04 ГАНС ──
        elif aid == "A04":
            state["reports"]["A04"] = narrative
            state["hans_signal"] = sig
            state["hans_stats"]  = r.get("stats", {})
            state["hans_market"] = r.get("market", {})
            state["hans_last_run"] = {
                "narrative": r.get("narrative", ""), "signal": sig, "market": r.get("market", {})}
            valid = sig.get("fractal_valid")
            prey = (f"добыча {sig.get('fractal_side','—')} @ {sig.get('fractal_price','—')}"
                    if valid else "добычи нет")
            state["active_agent"] = "A04"   # AGENT_LIVE_SWITCH_V1
            update_avatar()
            update_vitals()
            update_viewer(f"# 🎯 {_agent_label(roster,'A04')} (A04)\n\n{narrative or '*(нет текста)*'}")
            state["chat_history"].append({
                "role": "assistant", "agent": "A04", "content": f"🎯 Фрактал: {prey}. Отчёт справа."})
            update_chat_display()
            update_avatar_states()
            ui.notify(f"🎯 Ганс: {'фрактал вне Красной' if valid else 'пусто'}", type="positive")

        # ── A05 АРХИВАРИУС ──
        elif aid == "A05":
            state["reports"]["A05"] = narrative
            state["arkhiv_signal"] = sig
            state["arkhiv_stats"]  = r.get("stats", {})
            state["arkhiv_digest"] = r.get("digest", {})
            state["arkhiv_last_run"] = {
                "narrative": r.get("narrative", ""), "signal": sig, "signature": r.get("signature", {})}
            conf = sig.get("arkhiv_confidence", "—")
            n_ = sig.get("sample_size", "—")
            state["active_agent"] = "A05"   # AGENT_LIVE_SWITCH_V1
            update_avatar()
            update_vitals()
            update_viewer(f"# 📚 {_agent_label(roster,'A05')} (A05)\n\n{narrative or '*(нет текста)*'}")
            state["chat_history"].append({
                "role": "assistant", "agent": "A05",
                "content": (f"📚 Похожих случаев в Атласе: {n_}. Уверенность: {conf}. Отчёт справа.")})
            update_chat_display()
            update_avatar_states()
            ui.notify(f"📚 Архивариус: {conf} ({n_} случаев)", type="positive")

        # ── A06/A07/A08 ТРЕЙДЕРЫ ──
        elif aid in ("A06", "A07", "A08"):
            pre = {"A06": "brut", "A07": "avan", "A08": "cons"}[aid]
            icon = {"A06": "🪨", "A07": "⚡", "A08": "🛡"}[aid]
            _nm = _agent_label(roster, aid)
            state["reports"][aid] = narrative
            state[f"{pre}_signal"] = sig
            state[f"{pre}_stats"]  = r.get("stats", {})
            _last_key = {"A06": "brut_last_run", "A07": "avan_last_run", "A08": "cons_last_run"}[aid]
            state[_last_key] = {
                "narrative": r.get("narrative", ""), "signal": sig, "market": r.get("market", {})}
            verdict = sig.get(f"{pre}_verdict", "—")
            if verdict == "APPROVED":
                line = (f"{icon} {_nm}: ВХОД {sig.get(f'{pre}_direction','')} · "
                        f"вход {sig.get(f'{pre}_entry','—')} · стоп {sig.get(f'{pre}_stop','—')} · "
                        f"лот {sig.get(f'{pre}_lot','—')}. Отчёт справа.")
                ui.notify(f"{icon} {_nm}: ВХОД {sig.get(f'{pre}_direction','')}", type="positive")
            else:
                line = f"{icon} {_nm}: пас ({sig.get(f'{pre}_reason','—')}). Отчёт справа."
                ui.notify(f"{icon} {_nm}: пас", type="info")
            state["active_agent"] = aid   # AGENT_LIVE_SWITCH_V1
            update_avatar()
            update_vitals()
            update_viewer(f"# {icon} {_nm} ({aid})\n\n{narrative or '*(нет текста)*'}")
            state["chat_history"].append({"role": "assistant", "agent": aid, "content": line})
            update_chat_display()
            update_avatar_states()

        # ── A09 ИСПОЛНИТЕЛЬ ──
        elif aid == "A09":
            fdna = sig.get("final_dna", {})
            sent = fdna.get("orders_sent", "—")
            tsk  = fdna.get("task_score", "—")
            state["reports"]["A09"] = r.get("narrative", "") + "\n\n— Летопись: " + sig.get("history_dna", "")
            state["executor_signal"] = sig
            state["executor_stats"]  = r.get("stats", {})
            state["executor_last_run"] = {
                "narrative": r.get("narrative", ""), "signal": sig, "market": r.get("market", {})}
            state["active_agent"] = "A09"   # AGENT_LIVE_SWITCH_V1
            update_avatar()
            update_vitals()
            update_viewer(f"# 📋 {_agent_label(roster,'A09')} (A09)\n\n{state['reports']['A09']}")
            line = f"📋 Исполнитель: ордеров {sent} из 3 · task_score {tsk}. {sig.get('history_dna','')}"
            ui.notify(f"📋 Исполнитель: {sent} из 3", type="positive")
            state["chat_history"].append({"role": "assistant", "agent": "A09", "content": line})
            update_chat_display()
            update_avatar_states()

    async def run_tester_session():
        assets = state.get("loaded_assets", [])
        ai = state.get("active_asset")
        hist = assets[ai] if (assets and ai is not None and 0 <= ai < len(assets)) else None
        if not hist:
            ui.notify("Загрузи актив и кликни по нему в списке слева", type="warning")
            return
        if state.get("tester_running"):
            ui.notify("Перебор уже идёт...", type="warning")
            return

        state["tester_running"] = True
        state["stop_requested"] = False
        symbol = hist.get("symbol", "XAUUSD")
        tf     = hist.get("timeframe", "H4")
        path   = hist.get("path", "")
        n      = int(state.get("bars_to_live", 1) or 1)

        _uch = ("🎓 УЧЕБНЫЙ (якоря жителей растут)" if state.get("learn")
                else "🧪 стерильный (паспорта не трогаем)")   # TORG_LEARN_SWITCH_V1
        state["chat_history"].append({
            "role": "assistant", "agent": "SYSTEM",
            "content": f"▶ ТЕСТЕР: гоню {symbol} {tf} · ловлю {n} срабатываний · "
                       f"{_uch}. СТОП — прервать."})
        update_chat_display()
        ui.notify(f"▶ Тестер: {symbol} {tf}", type="info")

        # BIRZHA_UI_THREAD_SAFE_V1: потокобезопасная очередь событий.
        # _on_progress зовётся ИЗ ФОНОВОГО ПОТОКА (run_in_executor) —
        # слот-контекст NiceGUI туда не копируется, поэтому там нельзя
        # трогать ui.* НИКАК. Колбэк только кладёт событие в очередь;
        # разбор и вся отрисовка — в _apply_progress_event(), которую
        # зовёт ГЛАВНЫЙ поток (см. цикл дренажа ниже).
        _evt_queue: "queue.Queue" = queue.Queue()

        def _on_progress(msg):
            _evt_queue.put(msg)

        def _apply_progress_event(msg):
            """Разбор событий тестера — та же логика, что раньше жила
            прямо в _on_progress, просто теперь исполняется на главном
            потоке (слот-контекст этого клиента жив, ui.* работает)."""
            if isinstance(msg, dict) and msg.get("type") == "report":
                aid = msg.get("agent")
                narrative = msg.get("narrative", "")
                result = msg.get("result")
                if aid and narrative and result is not None:
                    # ENGINE_ONE_DOOR_V1 (память чата): result присутствует —
                    # тестер теперь несёт ПОЛНЫЙ словарь run_* агента, не
                    # только голос. Зовём ТУ ЖЕ функцию, что и РЫНОК —
                    # заполнит *_last_run, чтобы чат с агентом после
                    # ТЕСТЕРА знал, что тот только что видел, а не отвечал
                    # честно, но неверно "рынок не запускали".
                    if aid == "A01":
                        state["reports"] = {}
                        state["active_agent"] = None
                        try:
                            update_avatar_states()
                        except Exception:
                            pass
                    try:
                        _apply_agent_result(aid, result, narrative)
                    except Exception as e:
                        print(f"[TORG·TESTER] _apply_agent_result сбой ({aid}): {e}")
                    return
                if aid and narrative:
                    if aid == "A01":
                        state["reports"] = {}
                        state["active_agent"] = None
                        try:
                            update_avatar_states()
                        except Exception:
                            pass
                    state["reports"][aid] = narrative
                    state["active_agent"] = aid
                    label = _agent_label(roster, aid)
                    try:
                        update_viewer(f"# {label} ({aid})\n\n{narrative}")
                        update_avatar()
                        update_vitals()
                        update_avatar_states()
                    except Exception:
                        pass
                    status = msg.get("status", "")
                    tail = f" · {status}" if status else ""
                    state["chat_history"].append({
                        "role": "assistant", "agent": aid,
                        "content": f"отработал{tail}. Отчёт справа."})
                    try:
                        update_chat_display()
                    except Exception:
                        pass
                return
            if isinstance(msg, dict) and msg.get("type") == "verdict":
                txt = msg.get("text", "")
                hint = msg.get("hint", "")
                state["chat_history"].append({
                    "role": "assistant", "agent": "РАЗВИЛКА",
                    "content": f"📊 {txt}\n→ {hint}"})
                try:
                    update_chat_display()
                except Exception:
                    pass
                return
            if isinstance(msg, dict) and msg.get("type") == "trade":
                state["chat_history"].append({
                    "role": "assistant", "agent": "СДЕЛКА",
                    "content": msg.get("text", "")})
                try:
                    update_chat_display()
                except Exception:
                    pass
                return
            if isinstance(msg, dict) and msg.get("type") == "progress":
                state["chat_history"].append({
                    "role": "assistant", "agent": "···",
                    "content": msg.get("text", "")})
                try:
                    update_chat_display()
                except Exception:
                    pass
                return
            print(f"[TORG·TESTER] {msg}")

        def _should_stop():
            return state.get("stop_requested", False)

        try:
            from tester_express import run_tester
            loop = asyncio.get_event_loop()
            _tester_future = loop.run_in_executor(
                None,
                lambda: run_tester(
                    csv_path=path, symbol=symbol, timeframe=tf,
                    n_signals=n, on_progress=_on_progress,
                    should_stop=_should_stop,
                    learn=state.get("learn", False),   # TORG_LEARN_SWITCH_V1
                )
            )
            # Дренаж очереди на ГЛАВНОМ потоке, пока фоновый прогон
            # крутится — здесь слот-контекст этого клиента жив.
            while not _tester_future.done():
                drained_any = False
                while True:
                    try:
                        _msg = _evt_queue.get_nowait()
                    except queue.Empty:
                        break
                    drained_any = True
                    _apply_progress_event(_msg)
                if not drained_any:
                    await asyncio.sleep(0.05)
            await _tester_future
            # Добор хвоста: событие могло прийти между последней
            # проверкой .done() и фактическим завершением потока.
            while True:
                try:
                    _msg = _evt_queue.get_nowait()
                except queue.Empty:
                    break
                _apply_progress_event(_msg)
        except Exception as e:
            ui.notify(f"Тестер упал: {e}", type="negative")
            state["chat_history"].append({
                "role": "assistant", "agent": "SYSTEM",
                "content": f"⚠️ Тестер упал: {e}"})
            update_chat_display()
        finally:
            state["tester_running"] = False
            stopped = state.get("stop_requested", False)
            state["stop_requested"] = False

        tail = "⏸ остановлен по СТОП" if stopped else "✓ заход прожит"
        state["chat_history"].append({
            "role": "assistant", "agent": "SYSTEM",
            "content": f"{tail}. Совет отработал историю."})
        update_chat_display()
        update_avatar_states()
        ui.notify(tail, type="positive" if not stopped else "warning")

    def _vahta_vid():
        """Вид кнопки: горит — стоим на вахте."""
        el = toolbar_refs.get("vahta_btn")
        ht = toolbar_refs.get("vahta_html")
        if el is None or ht is None:
            return
        if state.get("vahta"):
            el.style("background:rgba(0,204,255,0.15);color:#00ccff;"
                     "border:1px solid rgba(0,204,255,0.45);")
            ht.content = "⏱ ВАХТА ●"
        else:
            el.style("background:rgba(255,255,255,0.03);"
                     "color:rgba(255,255,255,0.45);"
                     "border:1px solid rgba(255,255,255,0.08);")
            ht.content = "⏱ ВАХТА"

    def _vahta_pereklyuchit():
        state["vahta"] = not state.get("vahta")
        # забываем, где стояли: включаем — начинаем считать заново
        state["vahta_bar"] = ""
        _vahta_vid()
        if state["vahta"]:
            _s, _t = _aktivnyy_rynok()
            ui.notify(f"⏱ вахта: жду новую свечу {_s} {_t}", type="info")
        else:
            ui.notify("⏱ вахта снята", type="info")

    def _posledniy_bar(symbol: str, tf: str) -> str:
        """Время последнего бара по тому же крану, что и кадр."""
        try:
            from feed_source import bars as _src_bars
            _bs, _ = _src_bars(symbol, tf, 3)
            if _bs:
                return str(_bs[-1].get("date", ""))
        except Exception:
            pass
        return ""

    async def _vahta_tik():
        """Раз в двадцать секунд: не сменилась ли свеча.

        VAHTA_NOVAYA_SVECHA_V1. Первый тик только запоминает бар —
        иначе Совет дёргался бы посреди уже начатой свечи. В тестере
        молчим: там время идёт из файла, а не из жизни.
        """
        if not state.get("vahta") or state.get("running"):
            return
        if state.get("mode") == "tester":
            return
        _s, _t = _aktivnyy_rynok()
        _bar = _posledniy_bar(_s, _t)
        if not _bar:
            return
        if not state.get("vahta_bar"):
            state["vahta_bar"] = _bar
            return
        if _bar == state["vahta_bar"]:
            return
        state["vahta_bar"] = _bar
        ui.notify(f"🔔 новая свеча {_s} {_t} · {_bar[:16]} — смотрю",
                  type="positive")
        await market_dispatch()

    async def market_dispatch():
        if state.get("mode") == "tester":
            await run_tester_session()
        else:
            await run_market()

    async def run_market():
        # ── ЕДИНАЯ ДВЕРЬ СОВЕТА (ENGINE_ONE_DOOR_V1) ──
        # Раньше здесь была ручная лестница вызовов агентов — вторая
        # копия той, что жила в tester_express.py. Это был маскарад:
        # две лестницы расходятся. Теперь кабинет зовёт ТУ ЖЕ дверь
        # council.wake_council, что и тестер. Порядок, ворота по
        # спуску, обработка сбоев — одно место правды (council.py).
        #
        # ВОРОТА: раньше кабинет сам проверял t1 in (DETECTED,
        # CONFIRMED), чтобы решить, будить ли остальных. Это была
        # СТАРАЯ логика — тестер уже давно живёт по ЗАКОНУ СПУСКА
        # (COUNCIL_BY_DESCENT_V1): спуск нашёл точку = ФАКТ, Совет
        # собирается сам, t1_status — голос Искры, не замок. Теперь
        # кабинет тоже по этому закону (summary["idle"] из wake_council).
        #
        # BIRZHA_MARKET_THREAD_SAFE_V1: council.wake_council крутится
        # в фоновом потоке (run_in_executor) — тот же слот-стек NiceGUI
        # туда не копируется, что уже чинили в run_tester_session.
        # Колбэк _on_event раньше дёргал _apply_agent_result НАПРЯМУЮ
        # из фонового потока — "slot stack ... empty", да ещё и
        # ПРОГЛОЧЕННЫЙ МОЛЧА через try/except в council._emit(). Теперь
        # _on_event только кладёт событие в очередь; разбор — на
        # главном потоке (_apply_market_event, дренаж ниже), как в
        # тестере.
        if state["running"]:
            ui.notify("Прогон уже идёт...", type="warning")
            return
        state["running"] = True
        ui.notify("📡 Поднимаю контур...", type="info")

        import council
        import queue as _queue_mod

        _mkt_queue: "_queue_mod.Queue" = _queue_mod.Queue()

        def _on_event(ev):
            _mkt_queue.put(ev)

        def _apply_market_event(ev):
            """Та же логика, что раньше жила прямо в _on_event — теперь
            вызывается на главном потоке, где слот-контекст клиента жив."""
            etype = ev.get("type")

            if etype == "council_idle":
                return

            if etype != "agent":
                return

            aid = ev.get("id")
            r = ev.get("result", {}) or {}
            narrative = ev.get("narrative", "") or r.get("raw", "")

            try:
                _apply_agent_result(aid, r, narrative)
            except Exception as e:
                print(f"[TORG·MARKET] _apply_agent_result сбой ({aid}): {e}")

        # KABINET_VZGLYAD_V1: инструмент и этаж — с полки, не из кода.
        # Одна пара на кадр и на трейдера: смотрят одно и то же.
        _sym_now, _tf_now = _aktivnyy_rynok()
        ui.notify(f"👁 смотрим {_sym_now} {_tf_now}", type="info")
        try:
            loop = asyncio.get_event_loop()
            _market_future = loop.run_in_executor(
                None, lambda: council.wake_council(_sym_now, _tf_now,
                                                   on_event=_on_event))
            # Дренаж очереди на ГЛАВНОМ потоке, пока wake_council крутится.
            while not _market_future.done():
                drained_any = False
                while True:
                    try:
                        _ev = _mkt_queue.get_nowait()
                    except _queue_mod.Empty:
                        break
                    drained_any = True
                    _apply_market_event(_ev)
                if not drained_any:
                    await asyncio.sleep(0.05)
            summary = await _market_future
            # Добор хвоста очереди — событие могло прийти между
            # последней проверкой .done() и фактическим концом потока.
            while True:
                try:
                    _ev = _mkt_queue.get_nowait()
                except _queue_mod.Empty:
                    break
                _apply_market_event(_ev)
        except Exception as e:
            state["running"] = False
            ui.notify(f"Сбой прогона: {e}", type="negative")
            return
        state["running"] = False

        if summary.get("idle"):
            ui.notify("📣 Спуск не нашёл точку — Совет не собирается", type="info")

    def update_avatar_states():
        for aid, el in avatars_ref["elements"].items():
            row = _agent_row(roster, aid)
            base = "avatar vacant" if (row and not row["resident"]) else "avatar"
            el.classes(replace=base)
            if aid == state["active_agent"]:
                el.classes(add="active")
            if aid in state["reports"]:
                el.classes(add="done")

    def switch_agent(agent_id: str):
        row = _agent_row(roster, agent_id)
        if row and not row["resident"]:
            ui.notify("Вакансия — сюда ещё никого не наняли", type="warning")
        state["active_agent"] = agent_id
        update_avatar()
        update_vitals()
        update_avatar_states()
        update_stats_panel()
        label = _agent_label(roster, agent_id)
        if agent_id in state["reports"]:
            update_viewer(f"# {label} ({agent_id})\n\n{state['reports'][agent_id]}")
        else:
            update_viewer(f"# {label} ({agent_id})\n\n*Отчёт пока не создан.*")

    # ── загрузчик (левая колонка) ────────────────────────────
    def set_active(i):
        assets = state.get("loaded_assets", [])
        if 0 <= i < len(assets):
            state["active_asset"] = i
            update_files_display()
            a = assets[i]
            ui.notify(f"Активен: {a['symbol']} {a['timeframe']}", type="info")

    def update_files_display():
        # ZAGRUZCHIK_PAPKI_TORG_V1: активы сгруппированы в папки по symbol.
        # Внутри папки — список ТФ. Папка с активным ТФ раскрыта сама.
        if not files_ref["element"]:
            return
        files_ref["element"].clear()
        with files_ref["element"]:
            assets = state.get("loaded_assets", [])
            if not assets:
                ui.label("Нет активов").style("color: rgba(255,255,255,0.4); font-size:11px;")
                return

            active = state.get("active_asset")

            groups = {}
            order = []
            for i, a in enumerate(assets):
                sym = a["symbol"]
                if sym not in groups:
                    groups[sym] = []
                    order.append(sym)
                groups[sym].append(i)

            for sym in order:
                idxs = groups[sym]
                has_active = active in idxs
                with ui.expansion(
                    f"{sym}  ·  {len(idxs)} ТФ",
                    value=has_active,
                ).classes("w-full").style(
                    "background:rgba(255,255,255,0.02); "
                    "border:1px solid rgba(255,255,255,0.07); "
                    "border-radius:7px; margin:3px 0; "
                    "font-family:'JetBrains Mono',monospace; "
                    + ("border-color:rgba(0,255,136,0.45);" if has_active else "")
                ):
                    for i in idxs:
                        a = assets[i]
                        is_active = (i == active)
                        row = ui.element("div").style(
                            "padding:7px 10px; margin:3px 0; border-radius:7px; cursor:pointer; "
                            "font-family:'JetBrains Mono',monospace; "
                            + ("background:rgba(0,255,136,0.10); border:1px solid rgba(0,255,136,0.45);"
                               if is_active else
                               "background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.07);"))
                        row.on("click", lambda _, idx=i: set_active(idx))
                        with row:
                            ui.html(
                                f'''<div style="display:flex;justify-content:space-between;align-items:center;">
                                  <span style="color:rgba(255,255,255,0.4);font-size:10px;">ТФ</span>
                                  <span style="color:{'#00ff88' if is_active else 'rgba(0,204,255,0.9)'};
                                               font-size:11px;font-weight:700;">{a["timeframe"]}</span>
                                </div>
                                <div style="color:rgba(255,255,255,0.5);font-size:9px;margin-top:2px;">
                                  {a["date_from"]} → {a["date_to"]} · {a["bars"]}
                                </div>''')

    _HISTORY_TFS = ["MN1", "W1", "D1", "H12", "H8", "H4", "H1",
                    "M30", "M15", "M10", "M5", "M1"]
    _WORD_TFS = {"MONTHLY": "MN1", "WEEKLY": "W1", "DAILY": "D1", "HOURLY": "H1"}

    def _parse_symbol_tf(filename: str):
        stem = filename.rsplit(".", 1)[0].upper().strip()
        for word, tf in sorted(_WORD_TFS.items(), key=lambda x: -len(x[0])):
            if stem.endswith(word):
                return stem[:-len(word)].rstrip("_- "), tf
        for tf in sorted(_HISTORY_TFS, key=len, reverse=True):
            if stem.endswith(tf):
                return stem[:-len(tf)].rstrip("_- "), tf
        return stem, "?"

    _TEST_DATA_DIR = _HERE / "test_data"

    def _passport_from_csv(path):
        from williams_core import read_mt5_csv
        p = Path(path)
        bars = read_mt5_csv(str(p))
        if not bars:
            return None
        symbol, tf = _parse_symbol_tf(p.name)
        return {
            "name": p.name, "path": str(p), "symbol": symbol, "timeframe": tf,
            "bars": len(bars), "date_from": bars[0].get("date", "?"), "date_to": bars[-1].get("date", "?"),
        }

    def _scan_test_data():
        assets = []
        try:
            if _TEST_DATA_DIR.exists():
                for f in sorted(_TEST_DATA_DIR.glob("*.csv")):
                    try:
                        pp = _passport_from_csv(f)
                        if pp:
                            assets.append(pp)
                    except Exception as _e:
                        print(f"[TORG·SCAN] {f.name}: {_e}")
        except Exception as _e:
            print(f"[TORG·SCAN] папка: {_e}")
        state["loaded_assets"] = assets
        state["active_asset"] = 0 if assets else None

    async def handle_upload(e):
        name = e.name
        try:
            content = e.content.read() if hasattr(e.content, "read") else e.content
        except Exception as _ce:
            ui.notify(f"Не прочитать файл: {_ce}", type="negative")
            return
        if not name.lower().endswith(".csv"):
            ui.notify("Нужен CSV экспорта MT5", type="warning")
            return
        dest_dir = _TEST_DATA_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / name
        try:
            dest.write_bytes(content)
        except Exception as _we:
            ui.notify(f"Не сохранить файл: {_we}", type="negative")
            return
        try:
            from williams_core import read_mt5_csv
            bars = read_mt5_csv(str(dest))
        except Exception as _re:
            ui.notify(f"Ядро не прочло CSV: {_re}", type="negative")
            return
        if not bars:
            ui.notify(f"{name}: пусто или не формат MT5", type="warning")
            return
        symbol, tf = _parse_symbol_tf(name)
        passport = {
            "name": name, "path": str(dest), "symbol": symbol, "timeframe": tf,
            "bars": len(bars), "date_from": bars[0].get("date", "?"), "date_to": bars[-1].get("date", "?"),
        }
        assets = state.setdefault("loaded_assets", [])
        existing = next((k for k, x in enumerate(assets) if x.get("path") == passport["path"]), None)
        if existing is not None:
            assets[existing] = passport
            state["active_asset"] = existing
        else:
            assets.append(passport)
            state["active_asset"] = len(assets) - 1
        update_files_display()
        ui.notify(f"⚡ Заряжено: {symbol} {tf} · {len(bars)} баров", type="positive")
        _up = files_ref.get("uploader")
        if _up:
            try:
                _up.reset()
            except Exception:
                pass

    def clear_files():
        state["uploaded_files"] = []
        state["loaded_assets"] = []
        state["active_asset"] = None
        update_files_display()
        ui.notify("Очищено", type="info")

    # ── чат с активным агентом ───────────────────────────────
    async def send_message():
        if not input_ref["element"]:
            return
        msg = input_ref["element"].value.strip()
        if not msg:
            return
        input_ref["element"].value = ""
        state["chat_history"].append({"role": "user", "content": msg})
        update_chat_display()

        agent_id = state["active_agent"]
        row = _agent_row(roster, agent_id)
        if row and not row["resident"]:
            state["chat_history"].append({
                "role": "assistant", "agent": agent_id,
                "content": "здесь вакансия — прописать резидента на этот слот можно в кабинете Брата."})
            update_chat_display()
            return

        _chat_map = {
            "A02": ("торговый_хаос", "A02", "chat_with_morj", "morj_last_run", "🦭"),
            "A03": ("торговый_хаос", "A03", "chat_with_panikyor", "panic_last_run", "😱"),
            "A04": ("торговый_хаос", "A04", "chat_with_hans", "hans_last_run", "🎯"),
            "A05": ("контора", "архивариус", "chat_with_arkhiv", "arkhiv_last_run", "📚"),
            "A06": ("торговый_хаос", "A06", "chat_with_brut", "brut_last_run", "🪨"),
            "A07": ("торговый_хаос", "A07", "chat_with_avan", "avan_last_run", "🎲"),
            "A08": ("торговый_хаос", "A08", "chat_with_cons", "cons_last_run", "⚖️"),
            "A09": ("контора", "исполнитель", "chat_with_executor", "executor_last_run", "🎬"),
        }
        label = _agent_label(roster, agent_id)

        if agent_id in _chat_map:
            _ceh_id, _slot, _fn_name, _last_key, _ic = _chat_map[agent_id]
            ui.notify(f"{_ic} {label} думает...", type="info")
            try:
                _brain = _slot_brain(_ceh_id, _slot)
                if _brain is None:
                    raise RuntimeError(f"мозг {_slot} ещё не в слоте")
                _chat = getattr(_brain, _fn_name)
                dialog = [m for m in state["chat_history"]
                          if m.get("role") in ("user", "assistant") and m.get("content")]
                # RAZGOVOR_SO_STOLOM_V1: отдаём собеседнику тот же
                # инструмент, что выбран на полке, — чтобы он смотрел
                # на то же, что и Шеф. Кто ещё не умеет принимать
                # рынок (морж, паникёр, ганс, архивариус, исполнитель)
                # — спрашиваем по-старому.
                _rynok_seychas = _aktivnyy_rynok()
                try:
                    reply = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: _chat(msg, state.get(_last_key), dialog,
                                            rynok=_rynok_seychas))
                except TypeError:
                    reply = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: _chat(msg, state.get(_last_key), dialog))
            except Exception as e:
                reply = f"⚠️ {label} не смог(ла) ответить: {e}"
            # VYBOR_METKOY_V1: объявил выбор строкой «ВЫБОР: …» —
            # кладём его меткой в дом человека, а не в слот.
            try:
                from vybor import poymat as _poymat_vybor
                _ok_v, _msg_v = _poymat_vybor(_ceh_id, _slot, reply or "")
                if _ok_v and _msg_v:
                    ui.notify(f"🎯 {_msg_v}", type="positive")
            except Exception:
                pass
            state["chat_history"].append({"role": "assistant", "agent": agent_id, "content": reply})
            update_chat_display()
            return

        if agent_id != "A01":
            state["chat_history"].append({
                "role": "assistant", "agent": agent_id,
                "content": f"{label} ещё не подключён(а) к живому разговору."})
            update_chat_display()
            return

        ui.notify("✴️ Искра думает...", type="info")
        try:
            _brain = _slot_brain("торговый_хаос", "A01")
            if _brain is None:
                raise RuntimeError("мозг A01 ещё не в слоте")
            dialog = [m for m in state["chat_history"]
                      if m.get("role") in ("user", "assistant") and m.get("content")]
            reply = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _brain.chat_with_iskra(msg, state.get("iskra_last_run"), dialog))
        except Exception as e:
            state["chat_history"].append({
                "role": "assistant", "agent": "A01", "content": f"⚠️ Не смогла ответить: {e}"})
            update_chat_display()
            return
        state["chat_history"].append({"role": "assistant", "agent": "A01", "content": reply})
        update_chat_display()

    # ═══ LAYOUT — та же калька, что была в -2/studio/economy/ui_exchange.py ═══
    with ui.element("div").classes("app-container"):

        with ui.element("div").classes("area-header"):
            with ui.element("div").classes("glass squad-deck").style(
                "display:flex; align-items:center; width:100%; gap:8px; padding:0 8px; position:relative;"
            ):
                with ui.element("div").style(
                    "display:flex; align-items:center; gap:6px; flex-wrap:wrap; justify-content:center; flex:1;"
                ):
                    for r in roster:
                        old_id = r["old_id"]
                        occupied = bool(r["resident"])
                        cls = f'avatar {"active" if old_id == "A01" else ""} {"" if occupied else "vacant"}'
                        avatar = ui.element("div").classes(cls)
                        style = ""
                        if occupied:
                            av = _avatar_url_for(r["resident"]["папка"], static_prefix)
                            if av:
                                style = f"background-image:url('{av}');"
                        avatar.style(style)
                        avatar.on("click", lambda e, w=old_id: switch_agent(w))
                        with avatar:
                            if not occupied:
                                ui.label(old_id).style("font-size: 9px")
                        avatars_ref["elements"][old_id] = avatar
                with ui.element("div").style(
                    "margin-right:10px; background:rgba(255,255,255,0.06); "
                    "border:1px solid rgba(255,255,255,0.12); border-radius:10px;"
                ):
                    _opts = {m["id"]: f'{m["name"]} ({m["price"]})' for m in MODELS_CATALOG}
                    ui.select(_opts, value=state["model"], on_change=on_model_change) \
                        .props('dense borderless dark options-dense').style("min-width:190px;")
                ui.button("← Город", on_click=lambda: ui.navigate.to("/grondheim")).props("flat").style(
                    "color:rgba(255,255,255,0.5);")

        with ui.element("div").classes("area-left"):
            with ui.element("div").classes("left-col"):
                with ui.element("div").classes("glass asset-bay").style("height:auto; max-height:360px; flex:0 0 auto;"):  # ZAGRUZCHIK_SCROLL2_V1
                    with ui.row().style(
                        "width:100%; justify-content:space-between; align-items:center; "
                        "padding:8px 16px 6px 16px; border-bottom:1px solid rgba(255,255,255,0.08);"
                    ):
                        ui.label("ЗАГРУЗЧИК").style(
                            "color:rgba(255,255,255,0.92); font-weight:900; letter-spacing:.12em; "
                            "text-transform:uppercase; font-size:11px;")
                        ui.button("CLEAR", on_click=clear_files).props("flat dense size=xs").style(
                            "color:rgba(255,80,80,0.5); font-size:9px;")
                    files_ref["uploader"] = ui.upload(
                        on_upload=handle_upload, multiple=True, auto_upload=True,
                    ).props("flat color=cyan").style("margin: 0 8px 8px 8px;")
                    # ZAGRUZCHIK_SCROLL2_V1: инлайн глушил CSS-скролл. Даём предел
                    # высоты и вертикальный скролл — до нижних ТФ добраться.
                    files_ref["element"] = ui.element("div").classes("file-list").style(
                        "max-height:300px; overflow-y:auto; overflow-x:hidden; padding:4px 8px;")
                    _scan_test_data()
                    update_files_display()

        with ui.element("div").classes("area-stage"):
            with ui.element("div").classes("glass stage-monitor").style("height:100%; overflow:hidden;"):
                with ui.element("div").classes("stage-toolbar").style("flex-shrink:0;"):
                    with ui.element("div").style("display:flex; gap:6px; align-items:center;"):
                        ui.button("📡 РЫНОК", on_click=market_dispatch).props("flat").style('''
                            padding: 8px 18px; border-radius: 8px;
                            background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,204,255,0.10)) !important;
                            border: 1px solid rgba(0,255,136,0.35);
                            color: rgba(255,255,255,0.9); font-weight: 700;
                        ''')

                        # VAHTA_NOVAYA_SVECHA_V1 — стоять на вахте и
                        # смотреть каждую новую свечу рабочего этажа.
                        toolbar_refs["vahta_btn"] = ui.element("div").style(
                            "padding:6px 14px;border-radius:7px;font-size:12px;"
                            "font-weight:700;cursor:pointer;"
                            "background:rgba(255,255,255,0.03);"
                            "color:rgba(255,255,255,0.45);"
                            "border:1px solid rgba(255,255,255,0.08);")
                        with toolbar_refs["vahta_btn"]:
                            toolbar_refs["vahta_html"] = ui.html("⏱ ВАХТА")
                        toolbar_refs["vahta_btn"].on(
                            "click", lambda: _vahta_pereklyuchit())
                        ui.timer(20.0, _vahta_tik)   # async-колбэк NiceGUI ждёт сам
                        toolbar_refs["mode_real"] = ui.element("div").style(
                            "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                            "cursor:pointer;background:rgba(0,255,136,0.15);color:#00ff88;"
                            "border:1px solid rgba(0,255,136,0.4);")
                        toolbar_refs["mode_real"].on("click", lambda: set_mode("real"))
                        with toolbar_refs["mode_real"]:
                            ui.html("РЕАЛ")
                        toolbar_refs["mode_tester"] = ui.element("div").style(
                            "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                            "cursor:pointer;background:rgba(255,255,255,0.03);"
                            "color:rgba(255,255,255,0.45);border:1px solid rgba(255,255,255,0.08);")
                        toolbar_refs["mode_tester"].on("click", lambda: set_mode("tester"))
                        with toolbar_refs["mode_tester"]:
                            ui.html("ТЕСТЕР")
                        toolbar_refs["bars_label"] = ui.element("div").style("display:none;align-items:center;gap:5px;")
                        with toolbar_refs["bars_label"]:
                            ui.label("ловить:").style("color:rgba(255,255,255,0.45);font-size:11px;")
                        toolbar_refs["bars_input"] = ui.element("div").style("display:none;align-items:center;")
                        with toolbar_refs["bars_input"]:
                            def _on_bars_change(e):   # TORG_BARS_ONCHANGE_V1
                                try:
                                    state["bars_to_live"] = int(e.value or 1)
                                except (TypeError, ValueError):
                                    state["bars_to_live"] = 1
                            _bi = ui.number(
                                value=1, min=1, max=999,
                                on_change=_on_bars_change,   # штатный API NiceGUI, не сырое quasar-событие
                            ).props(  # CATCH_FIELD_VISIBLE_V1: видимая коробка + гарантированная отрисовка числа
                                'dense outlined '
                                'input-style="color:rgba(0,204,255,0.95);'
                                'font-family:JetBrains Mono;font-size:13px;'
                                'text-align:center;padding:0 2px;"'
                            ).style("width:78px;")
                        toolbar_refs["stop_btn"] = ui.element("div").style(
                            "display:none;align-items:center;padding:6px 14px;border-radius:7px;"
                            "font-size:12px;font-weight:700;cursor:pointer;"
                            "background:rgba(255,80,80,0.12);color:#ff5050;border:1px solid rgba(255,80,80,0.4);")
                        toolbar_refs["stop_btn"].on("click", lambda: request_stop())
                        with toolbar_refs["stop_btn"]:
                            ui.html("⏸ СТОП")

                        # KNOPKA_OCHISTKI_V1: кнопка очистки истории — вместо ручного
                        # запуска ochistit_atlas.py/ochistit_pozicii.py из консоли.
                        # Диалог подтверждения — действие меняет файлы на диске
                        # (архивирует, не удаляет).
                        def _ochistit_istoriyu():
                            def _do_clean():
                                from hooks import (ATLAS_PATH, PNL_PATH,
                                                    load_trading_state,
                                                    save_trading_state)
                                from datetime import datetime as _dt
                                stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
                                lines_out = []
                                for _path, _label in ((ATLAS_PATH, "Атлас"),
                                                       (PNL_PATH, "лента PnL")):
                                    if not _path.exists():
                                        lines_out.append(f"{_label}: не найден")
                                        continue
                                    _lines = [l for l in _path.read_text(
                                        encoding="utf-8").splitlines() if l.strip()]
                                    if not _lines:
                                        lines_out.append(f"{_label}: и так пуст")
                                        continue
                                    _archive = _path.with_name(
                                        f"{_path.stem}_archive_{stamp}{_path.suffix}")
                                    _archive.write_text(
                                        _path.read_text(encoding="utf-8"),
                                        encoding="utf-8")
                                    _path.write_text("", encoding="utf-8")
                                    lines_out.append(
                                        f"{_label}: архивировано {len(_lines)} строк")
                                _ts = load_trading_state()
                                _n_pos = len(_ts.get("positions", []) or [])
                                _ts["positions"] = []
                                save_trading_state(_ts)
                                lines_out.append(
                                    f"открытые позиции: очищено {_n_pos}")
                                ui.notify(" · ".join(lines_out),
                                          type="positive", timeout=8000)

                            with ui.dialog() as _dlg, ui.card().style(
                                    "background:#1a1f2e;"
                                    "border:1px solid rgba(255,255,255,0.1);"):
                                ui.label("Очистить историю сделок?").style(
                                    "font-weight:700;color:rgba(255,255,255,0.9);"
                                    "font-size:14px;")
                                ui.label(
                                    "Атлас и лента PnL будут АРХИВИРОВАНЫ (не "
                                    "удалены, лежат рядом с меткой времени) и "
                                    "обнулены. Открытые позиции очистятся. "
                                    "Используй перед чистым прогоном после "
                                    "правок кода."
                                ).style("color:rgba(255,255,255,0.55);"
                                        "font-size:12px;max-width:340px;"
                                        "margin:8px 0 14px 0;line-height:1.5;")
                                with ui.row().style(
                                        "gap:8px;justify-content:flex-end;"
                                        "width:100%;"):
                                    ui.button("Отмена",
                                              on_click=_dlg.close).props(
                                        "flat").style("color:rgba(255,255,255,0.5);")

                                    def _confirm():
                                        _do_clean()
                                        _dlg.close()
                                    ui.button("Очистить",
                                              on_click=_confirm).props(
                                        "color=negative").style(
                                        "font-weight:700;")
                            _dlg.open()

                        # TORG_LEARN_SWITCH_V1: рубильник учёбы — рядом со СТОП
                        toolbar_refs["learn_btn"] = ui.element("div").style(
                            "display:none;align-items:center;padding:6px 14px;border-radius:7px;"
                            "font-size:12px;font-weight:700;cursor:pointer;"
                            "background:rgba(255,255,255,0.03);color:rgba(255,255,255,0.45);"
                            "border:1px solid rgba(255,255,255,0.08);")
                        toolbar_refs["learn_btn"].on("click", lambda: toggle_learn())
                        with toolbar_refs["learn_btn"]:
                            ui.html("🎓 УЧИТЬ")
                        # KNOPKA_OCHISTKI_V1: кнопка очистки истории
                        _clean_btn = ui.element("div").style(
                            "display:flex;align-items:center;padding:6px 14px;border-radius:7px;"
                            "font-size:12px;font-weight:700;cursor:pointer;"
                            "background:rgba(255,180,0,0.08);color:rgba(255,180,0,0.85);"
                            "border:1px solid rgba(255,180,0,0.3);")
                        _clean_btn.on("click", lambda: _ochistit_istoriyu())
                        with _clean_btn:
                            ui.html("🧹 ОЧИСТИТЬ")
                    # UBRAT_NADPIS_BIRZHA_V1: надпись «БИРЖА · СОВЕТ» убрана —
                    # наезжала на кнопку ОЧИСТИТЬ, и была избыточна
                    # (страница подписана вкладками и хедером Совета).
                    with ui.row().style("gap:8px; justify-content:flex-end;"):
                        ui.button("← Брат", on_click=lambda: ui.navigate.to("/brat")).props("flat").style(
                            "padding:6px 14px; border-radius:8px; font-size:12px; "
                            "background:rgba(99,130,255,0.08); border:1px solid rgba(99,130,255,0.25); "
                            "color:rgba(180,190,220,0.8);")

                with ui.element("div").classes("stage-content").style("flex:1; min-height:0; overflow:hidden;"):
                    with ui.element("div").classes("split-view").style("height:100%; min-height:0; overflow:hidden;"):
                        chat_log_ref["element"] = ui.element("div").classes("chat-log").style(
                            "flex:1; min-height:0; overflow-y:auto;")
                        with chat_log_ref["element"]:
                            ui.html('<div class="chat-msg-system">SYSTEM: Биржа готова</div>')
                        # KABINET_GRAFIK_V1: правая часть — две половины
                        # по горизонтали: сверху кадр, снизу отчёты.
                        with ui.element("div").style(
                                "flex:1; min-height:0; display:flex; "
                                "flex-direction:column; gap:8px;"):
                            # KADR_NA_VES_KVADRAT_V1: колонка, не строка.
                            # В строке подпись вставала СПРАВА от кадра и
                            # отжимала его — картинка не тянулась на клетку.
                            kadr_ref["element"] = ui.element("div").classes("viewer").style(
                                "flex:1; min-height:0; overflow:hidden; "
                                "display:flex; flex-direction:column; "
                                "align-items:center; "
                                "justify-content:center;")
                            with kadr_ref["element"]:
                                ui.label("Кадр появится здесь — жми «👁 Взгляд»")
                            viewer_ref["element"] = ui.element("div").classes("viewer").style(
                                "flex:1; min-height:0; overflow-y:auto;")
                            with viewer_ref["element"]:
                                ui.label("Отчёты агентов появятся здесь")

                with ui.element("div").classes("floating-console"):
                    input_ref["element"] = ui.input(placeholder="Сообщение Совету...").props("borderless").style("flex:1")
                    input_ref["element"].on("keydown.enter", send_message)
                    # KABINET_GRAFIK_V1: посмотреть самому / дать посмотреть
                    ui.button("👁 Взгляд", on_click=lambda: pokazat_kadr()).props(
                        "flat no-caps").style(
                        "font-size:0.75rem; padding:8px 14px; border-radius:20px; "
                        "color:rgba(139,233,253,0.9); background:rgba(139,233,253,0.10); "
                        "border:1px solid rgba(139,233,253,0.35); white-space:nowrap;")
                    ui.button("SEND", on_click=send_message).classes("send-button")

        with ui.element("div").classes("area-right"):
            with ui.element("div").classes("right-col"):
                avatar_ref["element"] = ui.element("div").classes("right-top-slot")
                update_avatar()

                with ui.element("div").classes("glass").style("margin-top:12px; flex-shrink:0; overflow:hidden;"):
                    vitals_ref["element"] = ui.element("div")
                    update_vitals()

                with ui.element("div").classes("glass").style("margin-top:12px; flex-shrink:0; overflow:hidden;"):
                    ui.html('<div class="panel-title">ПРИБОРЫ</div>')
                    stats_ref["element"] = ui.element("div")
                    with stats_ref["element"]:
                        ui.html('<div style="color:rgba(255,255,255,0.3); font-size:11px; '
                                'padding:10px; text-align:center;">Нажми РЫНОК — стол накроется</div>')


if __name__ in {"__main__", "__mp_main__"}:
    @ui.page("/torg/{tseh_id}")
    def _torg_page(tseh_id: str = "торговый_хаос"):
        page_torg(tseh_id)
    @ui.page("/torg")
    def _torg0():
        page_torg()
    ui.run(title="Совет Биржи · Грондхейм", port=8104, reload=False)

# UI_TORG_TYPING_V1 — маркер идемпотентности

# BIRZHA_UI_THREAD_SAFE_V1 — маркер идемпотентности

# BIRZHA_MARKET_THREAD_SAFE_V1 — маркер идемпотентности

# AGENT_LIVE_SWITCH_V1 — маркер идемпотентности

# TORG_BARS_ONCHANGE_V1 — маркер идемпотентности

# KABINET_VZGLYAD_V1 - marker

# RAZGOVOR_SO_STOLOM_V1 - marker

# KADR_NA_VES_KVADRAT_V1 - marker

# VYBOR_METKOY_V1 - marker

# GEMINI_PO_UMOLCHANIYU_V1 - marker

# VAHTA_NOVAYA_SVECHA_V1 - marker
