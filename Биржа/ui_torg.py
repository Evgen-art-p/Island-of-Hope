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


class _TeeVyvod:
    """LOG_PROGONA_SYROY_V1: пишет разом в консоль и в файл.

    Ничего не решает и не фильтрует — сырое дублирование вывода,
    чтобы после прогона было что почитать, кроме памяти терминала.
    """

    def __init__(self, *potoki):
        self.potoki = potoki

    def write(self, dannye):
        for p in self.potoki:
            try:
                p.write(dannye)
            except Exception:
                pass

    def flush(self):
        for p in self.potoki:
            try:
                p.flush()
            except Exception:
                pass


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
    {"id": "openai/gpt-5.6-luna",              "name": "GPT-5.6 Luna",      "price": "$0.20 / $1.20"},
    {"id": "openai/gpt-5-mini",                "name": "GPT-5 Mini",      "price": "$0.25 / $2"},
    {"id": "google/gemini-2.5-flash",          "name": "Gemini 2.5 Flash",  "price": "$0.30 / $2.50"},
    {"id": "anthropic/claude-haiku-4-5",       "name": "Claude Haiku 4.5",  "price": "$1/$5"},
    {"id": "deepseek/deepseek-chat",           "name": "DeepSeek V3",       "price": "$0.14/$0.28"},
    {"id": "meta-llama/llama-3.3-70b-instruct","name": "Llama 3.3 70B",     "price": "$0.10/$0.32"},
    {"id": "anthropic/claude-sonnet-4-5",      "name": "Claude Sonnet 4.5", "price": "$3/$15"},
    # QWEN_V_SPISKE_V1 (слово Шефа 10.09). Цена прочерком:
    # выдуманное число хуже отсутствующего — по нему станут
    # считать. Посмотрит на openrouter.ai — впишем.
    {"id": "qwen/qwen3.5-397b-a17b",           "name": "Qwen 3.5 397B",   "price": "$0.39 / $2.34"},
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

# BELYY_SHRIFT_V1: читаемость на тёмном — см.
# postavit_belyy_shrift.py. Красим только то, что
# рисует Quasar своей светлой темой внутри наших
# тёмных карточек.
_BELYY_SHRIFT = r"""
/* BELYY_SHRIFT_V1 — читаемость на тёмном.
   Карточки диалогов рисуем мы (тёмные), а подписи внутри — Quasar по
   своей СВЕТЛОЙ теме. Отсюда тёмно-серые буквы на чёрном: в окне
   перевозки так пропадали имена жителей у галочек.
   Красим только то, что отдано Quasar'у. Кнопки и наши собственные
   раскрашенные надписи не трогаем — у них цвет задан руками. */
.q-dialog .q-card,
.q-dialog .q-card .q-item__label,
.q-dialog .q-card label,
.q-checkbox__label,
.q-radio__label,
.q-toggle__label,
.q-field__native,
.q-field__input,
.q-field__label,
.q-field__prefix,
.q-field__suffix,
.q-item__label,
.q-tab__label,
.q-select__dropdown-icon,
.q-menu .q-item,
.q-menu .q-item__label {
  color: rgba(255,255,255,0.92) !important;
}

/* Подсказка в пустом поле — белая, но приглушённая: она не должна
   спорить с тем, что человек уже вписал. */
.q-field__native::placeholder,
.q-field__input::placeholder,
.q-placeholder::placeholder {
  color: rgba(255,255,255,0.45) !important;
}

/* Выпадающий список Quasar рисует НЕ внутри нашей карточки, а
   отдельным слоем поверх страницы — своей темой. Без этого он
   оставался светлым пятном с белым текстом на белом. */
.q-menu {
  background: #0d1117 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
}
"""


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

# LENTA_NE_ZABIVAET_BRAUZER_V1: сколько последних сообщений
# рисуем. Остальное никуда не девается — оно в памяти и в
# отчёте, просто не перерисовывается каждую секунду.
LENTA_HVOST = 80

# KADR_NE_TERYAETSYA_V1: последний кадр, общий на ВСЕ вкладки.
# Прогон мог начаться в одном окне, а смотрят из другого —
# счёт растёт, и любое живое окно видит, что кадр сменился.
_KADR_NA_VIDU = {"put": None, "podpis": "", "schet": 0}

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


# ══════════════════════════════════════════════════════════════
# ВАХТА ГОРОДСКАЯ (VAHTA_GORODSKAYA_V1)
# ══════════════════════════════════════════════════════════════
# Была вахта комнатная: таймер жил в открытой вкладке. Ушёл на другую
# страницу — вахта встала, и никто об этом не сказал.
#
# Теперь она живёт при ГОРОДЕ, а не при окне: заводится один раз на
# запуск, тикает на сервере и работает, пока город поднят. Закрыл
# браузер — она всё равно стоит на посту. Вернулся — кнопка горит.
_VAHTA = {
    "идёт": False,      # стоим ли на вахте
    "инструмент": "",   # что сторожим — запомнили в миг нажатия
    "этаж": "",
    "бар": "",          # на какой свече стоим
    "цех": "",          # KABINET_ZNAET_CEH_V1: чей цех сторожим
    "работает": False,  # прогон уже идёт — второй не начинаем
    "последнее": "",    # что случилось в прошлый раз (для кнопки)
}
_VAHTA_ZAVEDENA = False


def _vahta_posledniy_bar(symbol: str, tf: str) -> str:
    try:
        from feed_source import bars as _src_bars
        _bs, _ = _src_bars(symbol, tf, 3)
        if _bs:
            return str(_bs[-1].get("date", ""))
    except Exception:
        pass
    return ""


async def _vahta_sluzhba():
    """Тик вахты. Живёт на сервере, окна не касается.

    VAHTA_GORODSKAYA_V1: Совет зовём НАПРЯМУЮ, а не через кнопку
    кабинета — кнопка рисует в окно, а окна может не быть вовсе.
    """
    if not _VAHTA["идёт"] or _VAHTA["работает"]:
        return
    # EDINYY_VYBOR_V1: сторожим ЭКРАН, а не то, что вахта запомнила
    # при нажатии. Переехал выбор — вахта переехала следом, снимать и
    # заводить заново не нужно. Экран пуст — держимся прежнего.
    sym, tf = _VAHTA["инструмент"], _VAHTA["этаж"]
    try:
        import ekran as _ekr
        _i, _e = _ekr.para()
        if _i and _e and (_i, _e) != (sym, tf):
            print(f"[ВАХТА] ▣ выбор переехал: {sym} {tf} → {_i} {_e}")
            sym, tf = _i, _e
            _VAHTA.update({"инструмент": _i, "этаж": _e, "бар": ""})
            return          # новый пост — этот тик только запоминаем
    except Exception:
        pass
    if not sym or not tf:
        return
    bar = _vahta_posledniy_bar(sym, tf)
    if not bar:
        return
    if not _VAHTA["бар"]:
        _VAHTA["бар"] = bar          # первый тик — только запомнить
        return
    if bar == _VAHTA["бар"]:
        return

    _VAHTA["бар"] = bar
    _VAHTA["работает"] = True
    print(f"[ВАХТА] 🔔 новая свеча {sym} {tf} · {bar[:16]} — зову Совет")
    try:
        import asyncio as _a
        import council
        # KABINET_ZNAET_CEH_V1: вахта сторожит СВОЙ цех, а не «какой-то».
        _ceh = _VAHTA.get("цех") or ""
        await _a.get_event_loop().run_in_executor(
            None, lambda: (council.wake_council("", "", ceh_id=_ceh)
                           if _ceh else council.wake_council("", "")))
        _VAHTA["последнее"] = f"{bar[:16]} · Совет отработал"
        print(f"[ВАХТА] ✓ {sym} {tf} · {bar[:16]} — Совет отработал")
    except Exception as e:
        _VAHTA["последнее"] = f"{bar[:16]} · сбой: {e}"
        print(f"[ВАХТА] ⚠️  сбой на {sym} {tf}: {e}")
    finally:
        _VAHTA["работает"] = False


def _vahta_zavesti():
    """Один тик на весь город, не на каждое окно.

    VAHTA_ZAVEDI_LYUBOY_V1: раньше звался только app.timer — в NiceGUI
    постарше его нет, и вахта молча не заводилась. Кнопка горела, а
    тика не было: худший вид поломки. Теперь три захода по очереди,
    и если не вышло ни одного — говорим об этом вслух, а не молчим.
    """
    global _VAHTA_ZAVEDENA
    if _VAHTA_ZAVEDENA:
        return
    # 1. городской таймер NiceGUI — если он в этой версии есть
    try:
        from nicegui import app as _app
        if hasattr(_app, "timer"):
            _app.timer(20.0, _vahta_sluzhba)
            _VAHTA_ZAVEDENA = True
            print("[ВАХТА] ⏱ заведена городским таймером (тик 20 сек)")
            return
    except Exception as e:
        print(f"[ВАХТА] городской таймер не вышел: {e}")
    # 2. своя петля в общем круге — работает в любой версии
    try:
        import asyncio as _a

        async def _petlya():
            print("[ВАХТА] ⏱ заведена своей петлёй (тик 20 сек)")
            while True:
                await _a.sleep(20)
                try:
                    await _vahta_sluzhba()
                except Exception as e:
                    print(f"[ВАХТА] ⚠️  сбой тика: {e}")

        _a.get_event_loop().create_task(_petlya())
        _VAHTA_ZAVEDENA = True
        return
    except Exception as e:
        print(f"[ВАХТА] своя петля не вышла: {e}")
    # 3. отдельная нитка — последний заход
    try:
        import asyncio as _a
        import threading as _t

        def _nitka():
            print("[ВАХТА] ⏱ заведена отдельной ниткой (тик 20 сек)")
            while True:
                _time.sleep(20)
                try:
                    _a.run(_vahta_sluzhba())
                except Exception as e:
                    print(f"[ВАХТА] ⚠️  сбой тика: {e}")

        import time as _time
        _t.Thread(target=_nitka, daemon=True).start()
        _VAHTA_ZAVEDENA = True
        return
    except Exception as e:
        print(f"[ВАХТА] ⚠️  НЕ ЗАВЕЛАСЬ ВОВСЕ: {e}")
        print("[ВАХТА] ⚠️  кнопка гореть будет, а сторожить некому — "
              "нажимай РЫНОК руками")




# KABINET_ZHIVYOT_PRI_GORODE_V1: память кабинета живёт ПРИ ГОРОДЕ,
# а не при вкладке. Раньше state рождался внутри страницы: моргнула
# связь или обновилась страница — рождался новый пустой, лента
# исчезала с экрана, а прогон продолжал писать в старый, которого
# уже никто не видит. Один кабинет на цех — как один стол и один
# момент истории.
_KABINETY: dict = {}



def _bystryy_pasport(p) -> dict | None:
    """Три числа о файле БЕЗ разбора баров: сколько строк, первая
    дата, последняя.

    POLKA_NE_DUSHIT_SVYAZ_V1. Формат тот же, что читает read_mt5_csv:
    MT5-выгруз в utf-16-le, поля через запятую, дата первым полем.

    Строки считаем кусками по мегабайту — это чтение с диска и ничего
    больше. Последнюю строку берём с ХВОСТА файла, не проходя его
    целиком. Не вышло — возвращаем None, и зовущий разберёт файл
    по-старому.
    """
    try:
        razmer = p.stat().st_size
        if razmer <= 0:
            return None

        KUSOK = 1 << 20          # мегабайт за раз
        perevodov = 0
        pervaya = b""
        with open(p, "rb") as f:
            kusok = f.read(KUSOK)
            if not kusok:
                return None
            pervaya = kusok.split(b"\n", 1)[0]
            while kusok:
                perevodov += kusok.count(b"\n")
                kusok = f.read(KUSOK)

            # Хвост: последняя непустая строка. Кодировка utf-16-le —
            # два байта на букву, поэтому и начало куска, и разбор
            # должны идти по буквам, а не по байтам, иначе последняя
            # дата читается мусором.
            hvost_dlina = min(8192, razmer)
            nachalo = razmer - hvost_dlina
            if nachalo % 2:            # встать на границу буквы
                nachalo += 1
            f.seek(nachalo)
            hvost = f.read(razmer - nachalo)

        def _stroka_v_datu(syrye: bytes):
            try:
                s = syrye.decode("utf-16-le", errors="ignore")
            except Exception:
                return None
            s = s.strip().lstrip("\ufeff").strip("\x00").strip()
            if not s:
                return None
            chasti = s.split(",")
            if len(chasti) < 6:
                return None
            data = chasti[0].strip()
            # у настоящего бара дальше идут числа — проверяем одно
            try:
                float(chasti[1])
            except (ValueError, IndexError):
                return None
            return data or None

        do_konca = _stroka_v_datu(pervaya)

        posle = None
        try:
            hvost_tekst = hvost.decode("utf-16-le", errors="ignore")
        except Exception:
            hvost_tekst = ""
        for stroka in reversed(hvost_tekst.split("\n")):
            stroka = stroka.strip().lstrip("\ufeff").strip("\x00").strip()
            if not stroka:
                continue
            chasti = stroka.split(",")
            if len(chasti) < 6:
                continue
            try:
                float(chasti[1])
            except (ValueError, IndexError):
                continue
            posle = chasti[0].strip()
            if posle:
                break

        if not do_konca or not posle:
            return None

        # строк с данными: переводы строк минус возможная пустая
        # последняя. Точность до одной строки полке не важна, но
        # заниженным числом пугать тоже не будем.
        barov = max(1, perevodov)
        return {"bars": barov, "date_from": do_konca, "date_to": posle}
    except Exception as e:
        print(f"[ПОЛКА] быстро не прочитал {getattr(p, 'name', p)} ({e}) — "
              f"разберу полностью")
        return None


def page_torg(tseh_id: str = "торговый_хаос") -> None:
    # OTPERET_V1: назвать цех столу СРАЗУ при входе в кабинет. Совет
    # называет его сам, но до Совета стол успевает открыть тот, кто
    # зовёт краном раньше — и запись уходила в общую тетрадь
    # («[STATE] стол сохранён (общий)»).
    try:
        import hooks as _h_ceh
        if hasattr(_h_ceh, "postavit_ceh"):
            _h_ceh.postavit_ceh(tseh_id)
    except Exception:
        pass
    """Кабинет Совета Биржи — тот же, что был /exchange в -2."""

    static_prefix = "torg-static"
    roster = _build_roster(static_prefix)

    # ── состояние страницы (как было в ui_exchange.py) ──────────
    _svezhee = {
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
        "kandidaty": [],            # ISKATEL_V1: найденные места
        "kandidat_i": None,         # на каком стоим
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

    # KABINET_ZHIVYOT_PRI_GORODE_V1: берём кабинет этого цеха, если он
    # уже открыт был — тогда лента, полка и режим на месте. Первый
    # раз — кладём свежий. Новые ключи (после патчей) доливаем, чтобы
    # старый кабинет не падал на том, чего в нём ещё нет.
    state = _KABINETY.setdefault(tseh_id, _svezhee)
    for _k, _v in _svezhee.items():
        state.setdefault(_k, _v)

    llm.set_model(state["model"])  # BIRZHA_MODEL_SEL_V1: применяем сразу при открытии кабинета

    def on_model_change(e):        # BIRZHA_MODEL_SEL_V1
        state["model"] = e.value
        llm.set_model(e.value)

    chat_log_ref: dict[str, Any] = {"element": None}
    toolbar_refs: dict[str, Any] = {}
    viewer_ref:   dict[str, Any] = {"element": None}
    vremya_ref:   dict[str, Any] = {"element": None}   # VREMYA_GORODA_V1
    kadr_ref:     dict[str, Any] = {"element": None}   # KABINET_GRAFIK_V1
    files_ref:    dict[str, Any] = {"element": None}
    avatar_ref:   dict[str, Any] = {"element": None}
    vitals_ref:   dict[str, Any] = {"element": None}   # заряд/оптика резидента — как везде в городе
    stats_ref:    dict[str, Any] = {"element": None}
    avatars_ref:  dict[str, Any] = {"elements": {}}
    input_ref:    dict[str, Any] = {"element": None}

    ui.add_head_html(f"<style>{TORG_CSS}</style>")
    ui.add_head_html("<style>" + _BELYY_SHRIFT + "</style>")   # BELYY_SHRIFT_V1
    _ceh0 = reg.get_ceh(tseh_id, KVARTAL)
    _bg_url = _building_bg_url(_ceh0.get("здание", "")) if _ceh0 else ""
    _bg_style = f" style=\"background-image:url('{_bg_url}');\"" if _bg_url else ""
    ui.html(f'<div id="bg"{_bg_style}></div>')

    # ── чат ───────────────────────────────────────────────────
    def update_chat_display():
        # PROGON_BEZ_OKNA_V1: вкладка могла умереть, пока прогон
        # работает в фоне (связь моргнула, страница обновилась,
        # компьютер уснул). NiceGUI на запись в мёртвого клиента
        # бросает «Client has been deleted» и KeyError, и это роняло
        # ВЕСЬ прогон. Лента в закрытой вкладке никому не видна —
        # значит и падать из-за неё нельзя. Считаем дальше молча,
        # отчёт всё равно пишется на диск.
        try:
            _risovat_chat()
        except Exception as e:
            print(f"[ПРОГОН] окно не принимает ленту ({e}) — "
                  f"работаю молча, отчёт пишется на диск")

    def _risovat_chat():
        if not chat_log_ref["element"]:
            return
        chat_log_ref["element"].clear()
        with chat_log_ref["element"]:
            if not state["chat_history"]:
                ui.html('<div class="chat-msg-system">SYSTEM: Биржа готова.</div>')
            else:
                # LENTA_NE_ZABIVAET_BRAUZER_V1: рисуем ХВОСТ, а не
                # всю ленту. Перерисовывать сотни сообщений с
                # картинками раз в секунду — от этого браузер и
                # рвал связь, а с ней умирала вкладка.
                _vsya = state["chat_history"]
                _hvost = _vsya[-LENTA_HVOST:]
                _skryto = len(_vsya) - len(_hvost)
                if _skryto > 0:
                    ui.html(
                        '<div class="chat-msg-system">SYSTEM: выше '
                        f'ещё {_skryto} сообщ. — полная лента в '
                        'отчёте на диске.</div>')
                for msg in _hvost:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    who = msg.get("agent", "")
                    if role == "user":
                        ui.html(f'<div class="chat-msg-user"><b>ШЕФ:</b> {content}</div>')
                    else:
                        ui.html(f'<div class="chat-msg-assistant"><b>{who}:</b> {content}</div>')
                        # KADRY_V_CHATE_V1: под ответом — то, что он
                        # видел. Панель одна и всегда про «сейчас»;
                        # здесь картинки лежат рядом со словами и
                        # больше не разъезжаются.
                        # KADR_K_KLYUCHU_V1: в ленте картинок больше нет —
                        # кадр показывается справа, один на побудку.
                        # Все кадры места целы в папке отчёта и видны
                        # на странице отчёта, там им и место.
                        _kadry = []
                        if _kadry:
                            with ui.row().style(
                                "gap:6px; flex-wrap:wrap; "
                                "margin:2px 0 10px 10px;"
                            ):
                                for _i_k, _pk in enumerate(_kadry, 1):
                                    try:
                                        if not Path(_pk).exists():
                                            continue
                                        with ui.element("div").style(
                                            "display:flex; "
                                            "flex-direction:column; "
                                            "align-items:center;"
                                        ):
                                            ui.image(str(_pk)).style(
                                                "width:210px; "
                                                "border-radius:6px; "
                                                "border:1px solid "
                                                "rgba(255,255,255,0.10); "
                                                "cursor:pointer;").on(
                                                "click",
                                                lambda _=None, p=_pk:
                                                    _kadr_krupno(p))
                                            ui.label(f"кадр {_i_k}").style(
                                                "color:rgba(255,255,255,0.35);"
                                                "font-size:10px;")
                                    except Exception:
                                        continue

    def _kadr_krupno(put: str):
        """Клик по кадру в ленте — показать во весь экран."""
        try:
            # KADR_KRUPNO_V1: картинке нужна ШИРИНА. С одним
            # max-width Quasar схлопывал её в иконку — кадр
            # «не разворачивался», как ни щёлкай.
            with ui.dialog() as _d, ui.card().style(
                "background:#0d1117; padding:10px; width:96vw; "
                "max-width:96vw;"
            ):
                ui.image(str(put)).style(
                    "width:100%; height:auto; max-height:86vh; "
                    "object-fit:contain;")
                ui.button("закрыть", on_click=_d.close).props(
                    "flat no-caps dense").style(
                    "color:rgba(255,255,255,0.5); font-size:0.75rem;")
            _d.open()
        except Exception as _e:
            print(f"[ЧАТ] кадр не открылся крупно ({_e})")

    # KABINET_ZHIVYOT_PRI_GORODE_V1: лента сама догоняет.
    # Прогон, начатый в другой вкладке (или до обновления страницы),
    # держит ссылку на СТАРОЕ окно и в это уже не пишет. Раз в
    # секунду смотрим, не выросла ли лента, и дорисовываем — тогда
    # фоновый прогон снова виден на экране.
    _lenta_vidno = {"skolko": -1}

    def _dognat_lentu():
        try:
            n = len(state.get("chat_history") or [])
            if n != _lenta_vidno["skolko"]:
                _lenta_vidno["skolko"] = n
                _risovat_chat()
        except Exception:
            pass

    try:
        ui.timer(1.0, _dognat_lentu)
    except Exception as _e_tmr:
        print(f"[КАБИНЕТ] лента не догоняет ({_e_tmr}) — не беда")

    # ZHIVOY_KADR_V1: панель показывает ТО, НА ЧТО СМОТРИТ ТРЕЙДЕР.
    # Раньше кадр всегда был про назначенный этаж места, а когда
    # трейдер уходил руками на другой — Шеф этого не видел вовсе, и
    # сверить его слова было не с чем. Тот же приём, что у ленты выше:
    # раз в секунду смотрим на площадь города, не появился ли новый.
    _zhivoy_vidno = {"put": None}

    def _dognat_zhivoy_kadr():
        try:
            if not kadr_ref["element"]:
                return
            from hooks import load_trading_state
            zk = (load_trading_state() or {}).get("zhivoy_kadr") or {}
            put = zk.get("put")
            if not put or put == _zhivoy_vidno["put"]:
                return
            p = Path(put)
            if not p.exists():
                return
            _zhivoy_vidno["put"] = put
            kadr_ref["element"].clear()
            with kadr_ref["element"]:
                ui.image(str(p)).style(
                    "width:100%; height:100%; object-fit:contain; "
                    "flex:1; min-height:0;")
                _chey = zk.get("chey") or zk.get("slot") or "трейдер"
                _pod = zk.get("podpis") or ""
                ui.label(f"🖐 {_chey} смотрит рукой · {_pod}").style(
                    "color:rgba(224,160,32,0.9); font-size:11px; "
                    "letter-spacing:0.06em; padding-top:6px; "
                    "flex-shrink:0; width:100%; text-align:center;")
        except Exception:
            pass

    try:
        ui.timer(1.0, _dognat_zhivoy_kadr)
    except Exception as _e_zk:
        print(f"[КАБИНЕТ] живой кадр не догоняет ({_e_zk}) — не беда")

    # KADR_NE_TERYAETSYA_V1: кадр ПРОГОНА тоже догоняем.
    # Прогон мог начаться в другой вкладке или до обновления
    # страницы — он держит ссылку на старое окно и в это уже не
    # пишет. Раз в секунду смотрим, не сменился ли кадр.
    _kadr_progona_vidno = {"schet": -1}

    def _dognat_kadr_progona():
        try:
            if not kadr_ref["element"]:
                return
            if _KADR_NA_VIDU["schet"] == _kadr_progona_vidno["schet"]:
                return
            _put = _KADR_NA_VIDU.get("put")
            if not _put or not Path(_put).exists():
                return
            _kadr_progona_vidno["schet"] = _KADR_NA_VIDU["schet"]
            kadr_ref["element"].clear()
            with kadr_ref["element"]:
                # METKA_VIDNA_V1: тот же щелчок и у догнанного кадра.
                ui.image(str(_put)).style(
                    "width:100%; height:100%; object-fit:contain; "
                    "flex:1; min-height:0; cursor:pointer;").on(
                    "click", lambda _=None, _q=str(_put): _kadr_krupno(_q))
                ui.label(
                    f"👁 {_KADR_NA_VIDU.get('podpis') or ''}").style(
                    "color:rgba(139,233,253,0.75); font-size:11px; "
                    "letter-spacing:0.06em; padding-top:6px; "
                    "flex-shrink:0; width:100%; text-align:center;")
        except Exception:
            pass

    try:
        ui.timer(1.0, _dognat_kadr_progona)
    except Exception as _e_kp:
        print(f"[КАБИНЕТ] кадр прогона не догоняет ({_e_kp}) — не беда")

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
        # UBRAT_CHETVERTOGO_V1: выдуманного запасного «XAUUSD H4»
        # больше нет. Это и был четвёртый инструмент при трёх
        # трейдерах: ничей, никем не выбранный, а работали по нему
        # все. Полка пуста — так и говорим, пустотой.
        return "", ""

    # ── VZGLYAD_KAZHDOGO_V1: память полки и пара активного ──
    def _klyuch_aktiva(a: dict) -> str:
        """Имя строки полки. Номер строки для этого не годится:
        ТЕРМИНАЛ кладёт свежее в НАЧАЛО списка, всё съезжает вниз, а
        номер остаётся — и выбор указывает уже на чужую строку. Так и
        получался вечный сброс на M15: он первый в опросе этажей."""
        if not a:
            return ""
        return (f"{a.get('symbol', '')}|{a.get('timeframe', '')}"
                f"|{a.get('источник', '')}")

    def _zapomnit_vybor() -> str:
        aktivy = state.get("loaded_assets") or []
        i = state.get("active_asset")
        if i is None or not (0 <= i < len(aktivy)):
            return ""
        return _klyuch_aktiva(aktivy[i])

    def _vernut_vybor(klyuch: str, tiho: bool = False):
        """Вернуть курсор на ту же строку после перестройки полки."""
        aktivy = state.get("loaded_assets") or []
        if not aktivy:
            state["active_asset"] = None
            return
        if klyuch:
            for j, a in enumerate(aktivy):
                if _klyuch_aktiva(a) == klyuch:
                    state["active_asset"] = j
                    return
            if not tiho:
                ui.notify("⚠ прежний актив с полки ушёл — "
                          "выбери заново", type="warning")
                state["active_asset"] = None
                return
        if state.get("active_asset") is None:
            state["active_asset"] = 0

    def _para_aktivnogo() -> tuple:
        """(инструмент, этаж, чей, чего не хватает) активного трейдера.

        Взгляд принадлежит трейдеру, а не полке: у каждого свой
        инструмент и свой этаж, и смотреть Шеф должен именно на его
        картинку, иначе проверить его нечем.
        """
        aid = state.get("active_agent") or ""
        imya = _agent_label(roster, aid) or aid
        if aid not in ("A06", "A07", "A08"):
            s, t = _aktivnyy_rynok()
            if not s or not t:
                return "", "", imya, "на полке ничего не выбрано"
            return s, t, "", ""
        try:
            import vybor
            r = vybor.rabota_dlya(tseh_id, aid)
            if r.get("инструмент") and r.get("этаж"):
                return r["инструмент"], r["этаж"], imya, ""
            return "", "", imya, vybor.pochemu_molchit(tseh_id, aid)
        except Exception as e:
            return "", "", imya, f"пара не прочиталась ({e})"

    # ── VREMYA_V_KABINETE_V1: шаг по истории ──────────────────
    def _para_dlya_shaga() -> tuple:
        """По чьему этажу шагаем. По активному трейдеру: у каждого
        свой рабочий этаж, и шаг должен быть в его барах."""
        s, t, _chey, _net = _para_aktivnogo()
        if s and t:
            return s, t
        return _aktivnyy_rynok()

    def _vremya_vid():
        """Обновить надпись «стоим: …»."""
        el = toolbar_refs.get("moment_label")
        if el is None:
            return
        try:
            import istoriya
            m = istoriya.gde_stoim()
        except Exception:
            m = ""
        el.text = f"стоим: {m}" if m else "конец истории"

    def _kandidat_vid():
        """Надпись «3/12» — на каком кандидате стоим."""
        el = toolbar_refs.get("kand_label")
        if el is None:
            return
        spisok = state.get("kandidaty") or []
        i = state.get("kandidat_i")
        if not spisok:
            el.text = "—"
        elif i is None:
            el.text = f"0/{len(spisok)}"
        else:
            el.text = f"{i + 1}/{len(spisok)}"

    async def _iskat_kandidatov():
        """ISKATEL_V1: код пробегает историю и приносит места, где
        стоит взглянуть. Бесплатно — это математика, не модель."""
        if state.get("mode") != "tester":
            ui.notify("Искать по истории можно в ТЕСТЕРЕ", type="warning")
            return
        symbol, tf = _para_dlya_shaga()
        if not symbol or not tf:
            ui.notify("Не пойму, где искать — выбери трейдера или актив",
                      type="warning")
            return
        ui.notify(f"🔍 ищу по {symbol} {tf}…", type="info")
        try:
            import asyncio
            import istoriya
            ot = istoriya.gde_stoim()

            def _rabota():
                import kandidaty
                return kandidaty.iskat(symbol, tf, do_momenta=ot,
                                       skolko=12, govorit=print)

            spisok = await asyncio.get_event_loop().run_in_executor(
                None, _rabota)
        except Exception as e:
            ui.notify(f"Искать не вышло: {e}", type="negative")
            return
        state["kandidaty"] = spisok
        state["kandidat_i"] = None
        _kandidat_vid()
        if not spisok:
            ui.notify("Ничего не нашлось — отмотай назад и поищи ещё",
                      type="warning")
            return
        ui.notify(f"🔍 нашёл {len(spisok)} мест — жми ⟩", type="positive")
        _k_kandidatu(0)

    def _k_kandidatu(nomer):
        """Встать на кандидата: курсор истории туда, кадр перерисовать."""
        spisok = state.get("kandidaty") or []
        if not spisok:
            ui.notify("Сперва найди кандидатов — кнопка 🔍", type="warning")
            return
        nomer = max(0, min(len(spisok) - 1, nomer))
        k = spisok[nomer]
        try:
            import istoriya
            istoriya.postavit(k.get("дата", ""))
        except Exception as e:
            ui.notify(f"Не встал: {e}", type="negative")
            return
        state["kandidat_i"] = nomer
        _kandidat_vid()
        _vremya_vid()
        try:
            # KADR_RISUETSYA_VEZDE_V1: pokazat_kadr асинхронная, а мы
            # в обычной функции. Прямой вызов создаёт корутину и НЕ
            # выполняет её — молча, без исключения. Ставим задачей.
            import asyncio as _a
            _a.get_event_loop().create_task(pokazat_kadr())
        except Exception as e:
            print(f"[ИСКАТЕЛЬ] кадр не перерисовался: {e}")
        try:
            import kandidaty as _kd
            stroka = _kd.slovami(k)
        except Exception:
            stroka = k.get("дата", "")
        print(f"[ИСКАТЕЛЬ] 📍 {nomer + 1}/{len(spisok)} · {stroka}")
        ui.notify(f"📍 {stroka}", type="info")

    def _kandidat_shag(kuda):
        i = state.get("kandidat_i")
        _k_kandidatu(0 if i is None else i + kuda)

    def _razobrat_datu(s: str) -> str:
        """PROGON_S_DATY_V1: понять дату, как её пишет человек.

        Отдаём в том виде, в каком её держит история: «ГГГГ.ММ.ДД ЧЧ:ММ».
        Не разобралась — возвращаем пусто, и прогон идёт от сегодня, как
        и раньше. Ругаться на человека за формат мы не будем.
        """
        s = (s or "").strip().replace("-", ".").replace("/", ".")
        if not s:
            return ""
        chasti = s.split()
        d = chasti[0]
        vremya = chasti[1] if len(chasti) > 1 else "00:00"
        kuski = [k for k in d.split(".") if k]
        if len(kuski) != 3:
            print(f"[ПРОГОН] дату «{s}» не разобрал — иду от сегодня")
            return ""
        if len(kuski[0]) == 4:                 # 2026.04.28
            god, mes, den = kuski
        else:                                  # 28.04.2026
            den, mes, god = kuski
        if ":" not in vremya:
            vremya = "00:00"
        try:
            god, mes, den = int(god), int(mes), int(den)
            # DATY_PO_CHELOVECHESKI_V1: «2016.30.04» — тридцатый месяц.
            # Раньше такое молча уходило в пустоту, и прогон шёл не
            # туда, куда просили, ничего не сказав.
            if not (1 <= mes <= 12 and 1 <= den <= 31):
                raise ValueError(f"месяц {mes}, день {den}")
            itog = f"{god:04d}.{mes:02d}.{den:02d} {vremya}"
        except ValueError as _e:
            print(f"[ПРОГОН] дату «{s}» не разобрал ({_e}) — иду от сегодня")
            try:
                ui.notify(f"дату «{s}» не понял — пишется "
                          f"число.месяц.год", type="warning")
            except Exception:
                pass
            return ""
        print(f"[ПРОГОН] ищу места до {itog}")
        return itog

    def _shagnut(skolko):
        """Шаг по истории. skolko=None — в конец (снять курсор)."""
        if state.get("mode") != "tester":
            ui.notify("Шаг по истории есть только в ТЕСТЕРЕ", type="warning")
            return
        symbol, tf = _para_dlya_shaga()
        if not symbol or not tf:
            ui.notify("Не пойму, по какому этажу шагать — "
                      "выбери трейдера или актив слева", type="warning")
            return
        try:
            import istoriya
            if skolko is None:
                istoriya.postavit("")
                ui.notify("⏭ конец истории", type="info")
            elif skolko == "начало":
                pervyy, _ = istoriya.dokuda_est(symbol, tf)
                if not pervyy:
                    ui.notify(f"Нет истории {symbol} {tf} в test_data",
                              type="warning")
                    return
                istoriya.postavit(pervyy)
                ui.notify(f"⏮ {pervyy}", type="info")
            else:
                m = istoriya.shag(tf, int(skolko), symbol=symbol)
                if not m:
                    ui.notify(f"Нет истории {symbol} {tf} в test_data",
                              type="warning")
                    return
        except Exception as e:
            ui.notify(f"Шаг не вышел: {e}", type="negative")
            return
        _vremya_vid()
        try:
            # KADR_RISUETSYA_VEZDE_V1: то же самое — задачей, иначе
            # корутина повиснет неисполненной и кадр останется прошлым.
            import asyncio as _a
            _a.get_event_loop().create_task(pokazat_kadr())
        except Exception as e:
            print(f"[ВРЕМЯ] кадр не перерисовался: {e}")

    def _kadr_zhivoy() -> bool:
        """KADR_BEZ_OKNA_V1: жива ли вкладка, в которую рисуем кадр.

        Вкладка могла умереть, пока прогон работает в фоне. NiceGUI на
        отрисовку в мёртвое окно НЕ бросает ошибку — он предупреждает и
        валит в лог полный стек. Поэтому try/except тут бесполезен:
        ловить нечего, надо спрашивать заранее.

        Живого клиента NiceGUI держит в своём списке, умершего убирает.
        Не смогли спросить — считаем живым и рисуем как раньше: молчать
        без причины хуже, чем лишняя строчка в логе.
        """
        el = kadr_ref["element"]
        if not el:
            return False
        try:
            from nicegui import Client as _Cl
            kl = getattr(el, "client", None)
            if kl is None or not hasattr(_Cl, "instances"):
                return True
            return kl.id in _Cl.instances
        except Exception:
            return True

    async def pokazat_kadr(put=None):
        """Рисует кадр ПО ВЫБОРУ ШЕФА и кладёт направо.

        VZGLYAD_PO_VYBORU_V1 (09.09, слово Шефа: «который просит — тот
        и давать; я какой выбрал, тот и давать»).

        Прежде кнопка была переведена с полки на трейдера
        (VZGLYAD_KAZHDOGO_V1) по верному тогда резону: смотреть Шеф
        должен на ЕГО картинку, иначе проверить его нечем. Но с тех
        пор появился ЖИВОЙ КАДР — когда трейдер идёт руками на другой
        этаж, панель сама показывает то, на что он смотрел, с
        подписью. Задача решается сама и лучше: по факту, а не по
        назначению.

        Значит кнопка возвращается Шефу, и разделение выходит чистое:
            живой кадр — что смотрит ТРЕЙДЕР;
            «Взгляд»   — что выбрал ШЕФ.

        Полка пуста — падаем на пару трейдера, чтобы кнопка не была
        немой. Модель не трогаем: Шеф смотрит, трейдер спит.
        """
        if not kadr_ref["element"]:
            return None
        # KADR_NE_TERYAETSYA_V1: раньше здесь был ранний выход —
        # окно мертво, уходим. Из-за него кадр прогона пропадал
        # бесследно. Теперь сперва рисуем и ЗАПОМИНАЕМ кадр, а
        # проверка живости стоит ниже, у самой отрисовки.
        # VZGLYAD_PO_VYBORU_V1: сперва спрашиваем ПОЛКУ.
        symbol, tf, chey, nehvatka = "", "", "", ""
        try:
            _s_p, _t_p = _aktivnyy_rynok()
        except Exception:
            _s_p, _t_p = "", ""
        if _s_p and _t_p:
            symbol, tf, chey, nehvatka = _s_p, _t_p, "выбор Шефа", ""
        else:
            symbol, tf, chey, nehvatka = _para_aktivnogo()
        if nehvatka:
            kadr_ref["element"].clear()
            with kadr_ref["element"]:
                ui.label(f"👁 {chey}: смотреть нечего").style(
                    "color:rgba(255,180,120,0.85); font-size:13px;")
                ui.label(nehvatka).style(
                    "color:rgba(255,255,255,0.55); font-size:11px;")
            return None
        try:
            import grafik
            if put:
                p = Path(put)
            else:
                # POKAZAT_KADR_NE_VESHAET_SERVER_V1: тот же приём,
                # что уже спасает progon_po_istorii — рисуем не в
                # обработчике клика, а в фоновом потоке.
                import asyncio
                _loop = asyncio.get_event_loop()
                p = await _loop.run_in_executor(
                    None, grafik.kadr, symbol, tf)
        except Exception as e:
            ui.notify(f"⚠ кадр не нарисовался: {e}", type="negative")
            return None
        if not p:
            ui.notify("⚠ кадр не нарисовался (нет matplotlib или баров)",
                      type="warning")
            return None
        # ZHIVOY_KADR_V1: Шеф смотрит сам — значит живой кадр трейдера
        # больше не показываем поверх, пока трейдер не сходит рукой
        # заново. Иначе таймер перерисует панель через секунду.
        try:
            from hooks import load_trading_state, save_trading_state
            _t_zk = load_trading_state()
            if _t_zk.get("zhivoy_kadr"):
                _t_zk["zhivoy_kadr"] = {}
            # VZGLYAD_DOHODIT_V1: то, что Шеф показал, должно дойти и
            # до трейдера — иначе он отвечает про свою картинку, а
            # спрашивают его про эту, и оба правы.
            # STOP_I_VZGLYAD_V1: помечаем только то, что Шеф показал
            # РУКОЙ. Раньше метка вешалась на любую отрисовку — и
            # трейдеру, работающему на M5, досылался автоматический D1
            # с подписью «показал Шеф». Графики не сходились.
            if state.pop("взгляд_рукой", False):
                try:
                    from datetime import datetime as _dtv
                    _t_zk["vzglyad_shefa"] = {
                        "путь": str(put),
                        "подпись": f"{symbol} {tf}",
                        "когда": _dtv.now().isoformat(timespec="seconds"),
                    }
                except Exception:
                    pass
            save_trading_state(_t_zk)
            _zhivoy_vidno["put"] = None
        except Exception:
            pass
        # KADR_NE_TERYAETSYA_V1: запоминаем кадр ДО отрисовки.
        # Даже если эта вкладка умерла — новая подхватит его
        # таймером за секунду.
        try:
            _KADR_NA_VIDU["put"] = str(p)
            _KADR_NA_VIDU["podpis"] = f"{chey + ' · ' if chey else ''}"\
                                      f"{symbol} · {tf}"
            _KADR_NA_VIDU["schet"] += 1
        except Exception:
            pass
        # KADR_BEZ_OKNA_V1: вкладка умерла — рисовать некуда.
        if not _kadr_zhivoy():
            print("[ПРОГОН] окно не принимает кадр — "
                  "кадр запомнен, новая вкладка подхватит")
            return p
        # рисуем сами — значит догонялке тут делать нечего
        try:
            _kadr_progona_vidno["schet"] = _KADR_NA_VIDU["schet"]
        except Exception:
            pass
        kadr_ref["element"].clear()
        with kadr_ref["element"]:
            # KADR_NA_VES_KVADRAT_V1: тянемся на всю клетку, но БЕЗ
            # плющенья — contain держит пропорции свечей. Плющеная
            # свеча врёт глазу, а глаз у нас важнее цифры.
            # METKA_VIDNA_V1: щелчок по кадру — во весь экран.
            # Показ уже готов, им живут миниатюры в ленте.
            ui.image(str(p)).style(
                "width:100%; height:100%; object-fit:contain; "
                "flex:1; min-height:0; cursor:pointer;").on(
                "click", lambda _=None, _p=str(p): _kadr_krupno(_p))
            # KABINET_VZGLYAD_V1: подпись под кадром. Что смотрим и
            # каким краном — иначе глазом реал от истории не отличить.
            # KADR_NA_VES_KVADRAT_V1: плюс дата последнего бара —
            # живой рынок сегодняшним числом, тестер прошлогодним.
            _kran = "ТЕСТЕР" if state.get("mode") == "tester" else "РЕАЛ"
            _kogda = ""
            try:
                from feed_source import bars as _src_bars
                _bs, _ = _src_bars(symbol, tf, 3)   # VZGLYAD_KAZHDOGO_V1
                if _bs:
                    _kogda = f" · {str(_bs[-1].get('date', ''))[:16]}"
            except Exception:
                pass
            # VZGLYAD_KAZHDOGO_V1: чей это взгляд — теперь в подписи,
            # иначе три разных кадра не отличить друг от друга.
            _chey = f"{chey} · " if chey else ""
            ui.label(f"👁 {_chey}{symbol} · {tf} · {_kran}{_kogda}").style(
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
        # TUMBLER_V1: след в консоли. Если нажатие не доходит — здесь
        # будет пусто, и станет ясно, что беда не в переключении.
        print(f"[ТУМБЛЕР] нажали: {mode}")
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
        # VREMYA_V_KABINETE_V1: ушли в РЕАЛ — снимаем курсор истории,
        # иначе живой рынок останется стоять в прошлом и будет тихо
        # показывать вчерашние бары как сегодняшние.
        if not is_tester:
            try:
                import istoriya
                if istoriya.gde_stoim():
                    istoriya.postavit("")
                    print("[ВРЕМЯ] курсор истории снят — вернулись в реал")
            except Exception:
                pass
            # SNYAT_BAR_GORODA_V1: и бар города тоже. Кадр обрезается
            # по полю `рынок.бар` (чтобы трейдер не подглядывал в
            # будущее), но после прогона там остаётся его последний
            # бар. Все бары живого рынка свежее — после обрезки не
            # остаётся ни одного, и кадр не рисуется совсем:
            #   «по бару города 2025.01.20 баров нет — кадра не будет»
            # Курсор истории — другое поле, тумблер его снимал, а это
            # лежало с прошлого раза.
            # Защиту не отменяем: в прогоне бар города ставится заново
            # на каждом шаге.
            try:
                from hooks import (load_trading_state as _lts_r,
                                   save_trading_state as _sts_r)
                _t_r = _lts_r() or {}
                _ryn_r = dict(_t_r.get("рынок") or {})
                if _ryn_r.get("бар"):
                    _staryy_bar = _ryn_r.get("бар")
                    _ryn_r["бар"] = ""
                    _t_r["рынок"] = _ryn_r
                    _sts_r(_t_r)
                    print(f"[ВРЕМЯ] бар города снят ({_staryy_bar}) — "
                          f"живой кадр больше не обрезается прошлым")
            except Exception as _e_bg:
                print(f"[ВРЕМЯ] бар города не снялся: {_e_bg}")
        try:
            _vremya_vid()
        except Exception:
            pass
        for key in ("bars_input", "stop_btn", "bars_label",
                    "ot_daty_label", "ot_daty_input",   # PROGON_S_DATY_V1
                    "po_datu_input",                    # TESTER_PULT_V2
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
        try:
            from feed_source import get_feed_mode as _gfm
            _kran = (_gfm() or {}).get("mode", "?")
        except Exception as _e:
            _kran = f"не спросить ({_e})"
        print(f"[ТУМБЛЕР] режим встал: {mode} · кран {_kran}")
        ui.notify(f"Режим: {'ТЕСТЕР (история)' if is_tester else 'РЕАЛ (живой рынок)'}",
                  type="info")

    def request_stop():
        # STOP_ZHYOSTKO_V1: первое нажатие — мягко, второе — бросаем.
        # Прогон висит внутри вопроса к модели, поэтому мягкий стоп
        # слышен только когда ответ вернётся. Второе нажатие не ждёт.
        if not state.get("tester_running"):
            ui.notify("Перебор не идёт", type="warning")
            return
        if state.get("stop_requested"):
            state["stop_hard"] = True
            _pometit_stop_dlya_mozga(True)
            ui.notify("⏹ БРОСАЮ — не жду текущий ответ", type="warning")
            return
        state["stop_requested"] = True
        _pometit_stop_dlya_mozga(True)
        ui.notify("⏸ СТОП — встану, как вернётся текущий ответ "
                  "(нажми ещё раз, чтобы бросить сразу)", type="info")

    def _pometit_stop_dlya_mozga(nado: bool):
        """Мозг про кнопку не знает — кладём признак на общую площадь."""
        try:
            from hooks import load_trading_state, save_trading_state
            _t = load_trading_state()
            _t["стоп_прогона"] = bool(nado)
            save_trading_state(_t)
        except Exception as _e:
            print(f"[СТОП] признак не лёг ({_e})")

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

    sostav_ref: dict = {"element": None}

    def _vahta_vid():
        """Вид кнопки: горит — стоим на вахте.

        VAHTA_GORODSKAYA_V1: спрашиваем ГОРОДСКУЮ вахту, не окно. Зашёл
        с другой страницы или из другого окна — кнопка всё равно
        показывает правду.
        """
        el = toolbar_refs.get("vahta_btn")
        ht = toolbar_refs.get("vahta_html")
        if el is None or ht is None:
            return
        if _VAHTA["идёт"]:
            el.style("background:rgba(0,204,255,0.15);color:#00ccff;"
                     "border:1px solid rgba(0,204,255,0.45);"
                     "white-space:nowrap;")
            # PROSTO_I_ROVNO_V1: в подписи коротко, что сторожит — в
            # подсказке и в строке состава под пузырьками.
            ht.content = "⏱ ВАХТА ●"
            try:
                el.tooltip(f'сторожу {_VAHTA["инструмент"]} '
                           f'{_VAHTA["этаж"]}')
            except Exception:
                pass
        else:
            el.style("background:rgba(255,255,255,0.03);"
                     "color:rgba(255,255,255,0.45);"
                     "border:1px solid rgba(255,255,255,0.08);")
            ht.content = "⏱ ВАХТА"

    def _vahta_pereklyuchit():
        if _VAHTA["идёт"]:
            _VAHTA.update({"идёт": False, "бар": ""})
            _vahta_vid()
            ui.notify("⏱ вахта снята", type="info")
            print("[ВАХТА] ⏹ снята")
            return
        if state.get("mode") == "tester":
            ui.notify("⏱ в тестере вахта не нужна — там время из файла",
                      type="warning")
            return
        _s, _t = _aktivnyy_rynok()
        # UBRAT_CHETVERTOGO_V1: вахта — это ДЕЖУРСТВО, будильник. По
        # какой свече звонить — берём с полки, как и раньше; но
        # разбуженные работают КАЖДЫЙ СВОИМ, а не тем, что на полке.
        # Полка пуста — дежурить не по чему, честно откажемся.
        if not _s or not _t:
            ui.notify("⏱ выбери слева, по какой свече дежурить",
                      type="warning")
            return
        # EDINYY_VYBOR_V1: встать на вахту — это и есть выбор.
        # Пишем в экран, чтобы трейдер и кадр поехали туда же.
        try:
            import ekran as _ekr
            _ekr.postavit(_s, _t, kto="Шеф", pochemu="встал на вахту")
        except Exception as _e_ekr:
            print(f"[ВАХТА] экран не записался ({_e_ekr})")
        _VAHTA.update({"идёт": True, "инструмент": _s, "этаж": _t,
                       "бар": "", "цех": tseh_id})
        _vahta_zavesti()
        _vahta_vid()
        if _VAHTA_ZAVEDENA:
            ui.notify(f"⏱ вахта: сторожу {_s} {_t}. Идёт, пока поднят "
                      f"город — окно можно закрыть", type="info")
        else:
            # VAHTA_ZAVEDI_LYUBOY_V1: не завелась — так и скажем, а не
            # оставим гореть кнопку впустую.
            _VAHTA["идёт"] = False
            _vahta_vid()
            ui.notify("⚠ вахта не завелась — смотри чёрное окно. "
                      "Пока жми РЫНОК руками.", type="negative")
        print(f"[ВАХТА] ▶ стою на {_s} {_t}")

    # VAHTA_GORODSKAYA_V1: комнатный тик убран — вахту несёт город
    # (см. _vahta_sluzhba наверху файла). Здесь осталась только
    # синхронизация кнопки при заходе на страницу.

    async def progon_po_istorii():
        """ODNA_KNOPKA_V1: весь тестер в одной кнопке.

        Раньше здесь был пульт из стрелок, а до него — tester_express
        на упразднённой Искре. Теперь: код ищет места, город встаёт в
        каждое, трейдер говорит. Шеф только читает ленту.
        """
        if state.get("tester_running"):
            ui.notify("Прогон уже идёт", type="warning")
            return
        try:
            import istoriya
            import kandidaty as _kd
            import vybor
        except Exception as e:
            ui.notify(f"Прогон недоступен: {e}", type="negative")
            return

        # кто может работать: у кого есть и инструмент, и этаж
        # PARA_PO_POSTU_V1: пара приходит из ПОСТА каждого, и ниоткуда
        # больше. Подмены с полки здесь БОЛЬШЕ НЕТ: пока на Бирже сидел
        # один человек, она выглядела разумной, а на двоих согнала обоих
        # на один инструмент — 24.08 Илья и Нина пошли по евро, хотя у
        # Нины в посте золото. Для сравнения двух трейдеров это срыв
        # самой затеи: они должны идти по своей паре, а не по той, что
        # кабинет молча выбрал за них.
        #
        # Полка слева снова только то, ЧТО СМОТРИШЬ. Нужен общий рынок
        # для сравнения — пропиши обоим одну пару в постах.
        _podmena = ""
        rabotniki = []
        for _sl in ("A06", "A07", "A08"):
            r = vybor.rabota_dlya(tseh_id, _sl)
            if r.get("готов"):
                rabotniki.append((_sl, r["инструмент"], r["этаж"]))
            else:
                print(f"[ПРОГОН] {_sl} не участвует: "
                      f"{vybor.pochemu_molchit(tseh_id, _sl)}")
        if not rabotniki:
            ui.notify("Некому работать: ни у кого нет инструмента и этажа",
                      type="warning")
            return

        # TESTER_PULT_V1: «ловить N» — это ПРЕДЕЛ ПО СРАБАТЫВАНИЯМ, а
        # не по барам. Бар город считает даром, а вопрос трейдеру стоит
        # денег, и считать надо оплаченные взгляды. 0 или пусто — без
        # предела, идём весь отрезок.
        try:
            skolko = int(state.get("bars_to_live") or 0)
        except (TypeError, ValueError):
            skolko = 0
        _ot_daty = _razobrat_datu(state.get("progon_ot_daty") or "")
        _po_datu = _razobrat_datu(state.get("progon_po_datu") or "")
        if _ot_daty and _po_datu and _po_datu < _ot_daty:
            _ot_daty, _po_datu = _po_datu, _ot_daty
            print("[ПРОГОН] даты стояли задом наперёд — поменял местами")
        # OTCHYOT_PROGONA_V1: заводим папку прогона — туда лягут
        # таблица, строки машиной и кадр КАЖДОГО места.
        try:
            import otchyot as _ot
            _otchyot = _ot.Otchyot(Path(__file__).resolve().parent.parent,
                                   tseh_id)
        except Exception as _e:
            _otchyot = None
            print(f"[ОТЧЁТ] не завёлся ({_e}) — прогон пойдёт без записи")
        # LOG_PROGONA_SYROY_V1: дублируем весь вывод в лог.txt рядом
        # с отчётом — без фильтров, чтобы после прогона не бегать по
        # терминалу за тем, что там мелькнуло и пропало.
        _original_stdout = sys.stdout
        _log_fayl_progona = None
        if _otchyot is not None:
            try:
                _log_fayl_progona = open(_otchyot.papka / "лог.txt", "a",
                                          encoding="utf-8")
                sys.stdout = _TeeVyvod(_original_stdout, _log_fayl_progona)
            except Exception as _e_log:
                print(f"[ЛОГ] файл прогона не завёлся ({_e_log}) — иду "
                      f"без него")
        state["tester_running"] = True
        state["stop_requested"] = False
        state["stop_hard"] = False          # STOP_ZHYOSTKO_V1
        _pometit_stop_dlya_mozga(False)
        _bylo_moment = ""
        # CHISTYY_START_PROGONA_V1: новый прогон — чистый стол.
        # «Последнее закрытие» и позиции прошлого прогона будили
        # трейдера чужими событиями на тех же барах.
        try:
            from hooks import load_trading_state as _lts0
            from hooks import save_trading_state as _sts0
            _t0 = _lts0()
            _bylo_z = _t0.pop("последнее_закрытие", None)
            # живые (mode=live) не трогаем — только прошлые прогоны
            _vse0 = _t0.get("positions") or []
            _zhivye0 = [p for p in _vse0
                        if str(p.get("mode") or "").lower() == "live"]
            _bylo_p = len(_vse0) - len(_zhivye0)
            if _bylo_p:
                _t0["positions"] = _zhivye0
            if _bylo_z is not None or _bylo_p:
                _sts0(_t0)
                print(f"[ПРОГОН] 🧹 чистый стол: прошлое закрытие "
                      f"{'стёрто' if _bylo_z is not None else 'не было'}"
                      f", позиций/заявок прошлого прогона снято: {_bylo_p}")
        except Exception as _e_ch:
            print(f"[ПРОГОН] почистить стол не вышло ({_e_ch})")
        try:
            _bylo_moment = istoriya.gde_stoim()
        except Exception:
            pass

        state["chat_history"].append({
            "role": "system",
            "content": (f"▶ ПРОГОН ПО ИСТОРИИ · {len(rabotniki)} "
                        f"трейдер(ов)"
                        # PARA_PO_POSTU_V1: у каждого своя пара — пишем
                        # их все, чтобы сразу видеть, кто чем гонит.
                        + " · " + ", ".join(f"{_s}:{_sy} {_tf2}"
                                            for _s, _sy, _tf2 in rabotniki)
                        + (f" · с {_ot_daty}" if _ot_daty else "")
                        + (f" · по {_po_datu}" if _po_datu else "")
                        + (f" · ловлю {skolko} срабатывани(й)"
                           if skolko else " · до конца отрезка"))})
        update_chat_display()
        ui.notify("🔍 ищу места в истории…", type="info")

        import asyncio
        loop = asyncio.get_event_loop()

        # 1. PROGON_PODRYAD_V1: идём по истории ПОДРЯД, бар за баром.
        # Слово Шефа: «есть история — прогнал, посмотрел реально».
        # Раньше здесь работал искатель: прыгал по своим «местам» от
        # свежих к старым и половину отсеивал рамкой и трендом. Город
        # видел не историю, а выборку, собранную нашими же правилами, —
        # такая проверка проверяет только саму себя.
        #
        # Теперь: с даты пусто — последний год; задана — с неё до конца
        # данных. Каждый бар город считает сам, молча и даром. Трейдера
        # зовут только на открытом ключе.
        mesta = []
        for _sl, _sym, _tf in rabotniki:
            try:
                _vse = await loop.run_in_executor(
                    None, lambda s=_sym, t=_tf: istoriya._vse_bary(s, t))
            except Exception as e:
                print(f"[ПРОГОН] {_sl}: история не открылась — {e}")
                continue
            if not _vse:
                continue
            _daty = [b.get("date", "") for b in _vse]
            if _ot_daty:
                _s = next((j for j, d in enumerate(_daty)
                           if d >= _ot_daty), None)
                if _s is None:
                    print(f"[ПРОГОН] {_sl}: после {_ot_daty} баров нет")
                    continue
            else:
                # год назад: на H4 это около 1500 баров, на D1 — 250.
                # Берём по числу баров, а не по календарю: файл может
                # кончаться раньше сегодняшнего дня.
                _v_godu = {"MN1": 12, "W1": 52, "D1": 252, "H12": 500,
                           "H8": 750, "H4": 1500, "H1": 6000}.get(
                               str(_tf).upper(), 1500)
                _s = max(0, len(_daty) - _v_godu)
            _s = max(_s, 300)          # ядру нужно окно на разгон
            # TESTER_PULT_V1: верхняя граница отрезка. Раньше её не
            # было вовсе — от даты и до конца файла, вырезать кусок
            # истории было нечем.
            _e = len(_daty)
            if _po_datu:
                _e = next((j for j, d in enumerate(_daty) if d > _po_datu),
                          len(_daty))
                if not _ot_daty:
                    # Год отсчитываем НАЗАД ОТ верхней границы, а не от
                    # конца файла: иначе «только по дату» давало пустой
                    # отрезок — нижняя граница оказывалась позже верхней.
                    _s = max(0, _e - _v_godu)
            _s = max(_s, 300)          # ядру нужно окно на разгон
            if _e <= _s:
                print(f"[ПРОГОН] {_sl}: между {_ot_daty or 'началом'} и "
                      f"{_po_datu} баров нет")
                continue
            for j in range(_s, _e):
                mesta.append((_daty[j], _sl, _sym, _tf,
                              {"дата": _daty[j], "подряд": True}))
            print(f"[ПРОГОН] {_sl}: {_sym} {_tf} — "
                  f"{_e - _s} баров, "
                  f"с {_daty[_s]} по {_daty[_e - 1]}")

        if not mesta:
            state["tester_running"] = False
            # DATY_PO_CHELOVECHESKI_V1: «пусто» само по себе врёт —
            # похоже, будто сломан прогон. Чаще всего история просто
            # в другом отрезке. Говорим, какая она есть.
            _skazat = "Ничего не нашлось в истории — пусто."
            try:
                _kraya = []
                from feed_source import bars as _src_bars
                for _sl2, _s2, _t2 in rabotniki:
                    _v2, _ = _src_bars(_s2, _t2, 0)
                    if _v2:
                        _kraya.append(f"{_s2} {_t2}: история с "
                                      f"{_v2[0].get('date', '?')} по "
                                      f"{_v2[-1].get('date', '?')}")
                if _kraya:
                    _zadano = (state.get("progon_ot_daty") or "").strip()
                    _do = (state.get("progon_po_datu") or "").strip()
                    _otrez = (f" Задан отрезок {_zadano or 'с начала'} → "
                              f"{_do or 'до конца'}.")
                    _skazat = ("В заданном отрезке баров нет. " +
                               " · ".join(_kraya) + "." + _otrez)
            except Exception:
                pass
            state["chat_history"].append({
                "role": "system", "content": _skazat})
            update_chat_display()
            ui.notify("Мест не нашлось", type="warning")
            return

        # от старых к свежим — как шло время
        mesta.sort(key=lambda x: x[0])
        state["chat_history"].append({
            "role": "system",
            # PROGON_PODRYAD_V2: подряд — это бары, а не места.
            "content": (f"Иду по истории: {len(mesta)} баров."
                        if mesta and mesta[0][4].get("подряд")
                        else f"Нашёл {len(mesta)} мест. Иду по ним.")})
        update_chat_display()

        # 2. по каждому месту: встать туда и спросить того, чьё оно
        proydeno = 0
        _razbudili = 0          # TESTER_PULT_V1: оплаченных взглядов
        try:
            for data, _sl, _sym, _tf, k in mesta:
                # STOP_I_VZGLYAD_V1: передышка для интерфейса. Без неё
                # на сплошном ходу цикл не отпускает поток, нажатие
                # СТОП не успевает обработаться — и прогон идёт дальше,
                # хотя проверка флага стоит прямо ниже.
                await asyncio.sleep(0)
                if state.get("stop_hard"):   # STOP_ZHYOSTKO_V1
                    stopped = True
                    break
                if state.get("stop_requested"):
                    state["chat_history"].append({
                        "role": "system", "content": "⏸ остановлено"})
                    update_chat_display()
                    break
                # BUDIM_NA_SVOYOM_BARE_V1: курсор — на момент ЗАКРЫТИЯ
                # бара места, а не на его начало. Машина времени отдаёт
                # только закрытое: поставь курсор на начало — и сам бар
                # события окажется «ещё идущим», город возьмёт
                # предыдущий, а трейдера разбудят ДО того, как некрон
                # сформировался. Отсюда и его вечное «жду ещё бар».
                istoriya.postavit(_moment_zakrytiya(data, _tf))
                # PROGON_PODRYAD_V1: на сплошном ходу считаем сами и
                # смотрим ключ. Закрыт — идём дальше молча и даром.
                if k.get("подряд"):
                    try:
                        def _tiho(s=_sym, t=_tf, sl=_sl):
                            import hooks as _h2
                            _h2.rynok_novyy_bar(s, t)
                            return __import__("council")._klyuch_probuzhdeniya(
                                s, t, sl)
                        _kk = await loop.run_in_executor(None, _tiho)
                    except Exception as _ek:
                        print(f"[ПРОГОН] ключ не прочёлся: {_ek}")
                        _kk = {"будим": False}
                    if not _kk.get("будим"):
                        continue
                    k = dict(k)
                    k["почему"] = _kk.get("почему", "")
                    # TESTER_PULT_V1: вот оно, настоящее срабатывание —
                    # ключ открылся, сейчас трейдера спросят. Считаем
                    # здесь, а не по барам: платим мы за вопросы.
                    _razbudili += 1
                # TOCHKA_NE_TASHCHITSYA_V1: прогон прыгнул в другой
                # момент истории — точка с прошлого места сюда не
                # едет. Иначе она формально жива, заново не рождается,
                # и ключ молчит на честном разворотнике.
                #
                # KONEC_VOLNY_NE_SYEDEN_V1: но только на ПРЫЖКАХ. На
                # сплошном ходу чистка стояла здесь же и стирала
                # ячейку точки сразу после того, как молчаливый шаг
                # нашёл конец первой волны, — вместе с отметкой и с
                # защитой «один бар — одно решение». Совет судил тот же
                # бар начисто, тот же разворотник читался уже как новая
                # точка, и трейдеру говорили «точка родилась» вместо
                # «волна 1 кончилась». За год событие случилось дважды
                # и оба раза было съедено; а откат считается ОТ этой
                # отметки, значит третьего события не бывало вовсе.
                #
                # Сплошной прогон не прыгает: он идёт баром за баром,
                # как живой город, и точка обязана жить между барами.
                if not k.get("подряд"):
                    try:
                        import hooks as _h
                        _h.zabyt_tochku(_sym, _tf)
                    except Exception as _ez:
                        print(f"[ПРОГОН] точку забыть не вышло: {_ez}")
                imya = _agent_label(roster, _sl) or _sl
                # PROGON_VIDNO_V1: кадр рисуем ОДИН раз и В ФОНЕ.
                # Раньше он рисовался в главном потоке, да ещё дважды
                # на место (для экрана и для отчёта) — matplotlib на
                # секунды вешал сервер, и браузер обрывал связь:
                # «Connection lost». Одна картинка идёт и на экран,
                # и в отчёт.
                _kadr = None
                try:
                    _kadr = await loop.run_in_executor(
                        None, lambda s=_sym, t=_tf: __import__(
                            "grafik").kadr(s, t))
                except Exception as _ek:
                    print(f"[ПРОГОН] кадр не нарисовался: {_ek}")
                # KADR_PRYAMO_V_PAMYAT_V1: кладём кадр в общую
                # память СРАЗУ, до всякого показа. pokazat_kadr —
                # функция того окна, где прогон начинался; после
                # перезагрузки страницы она уводит кадр в никуда,
                # и делает это молча. Общая память ни от какого
                # окна не зависит: любая живая вкладка подберёт
                # кадр своим таймером за секунду.
                if _kadr:
                    try:
                        _KADR_NA_VIDU["put"] = str(_kadr)
                        _KADR_NA_VIDU["podpis"] = f"{_sym} · {_tf}"
                        _KADR_NA_VIDU["schet"] += 1
                        print(f"[КАДР] в панель: "
                              f"{Path(_kadr).name}")
                    except Exception as _ep:
                        print(f"[КАДР] в панель не лёг: {_ep}")
                try:
                    await pokazat_kadr(_kadr)
                except Exception:
                    pass
                # PODPIS_PO_BARU_GORODA_V1: подписываем баром, на
                # котором город стоит НА САМОМ ДЕЛЕ. Дата места —
                # это бар, где признак стал ВИДЕН, она на шаг вперёд,
                # и из-за неё казалось, будто кадр отстаёт.
                _podpis_bar = data
                _hvost_mesta = ""
                try:
                    from hooks import load_trading_state as _lts_p
                    _bg = str(((_lts_p() or {}).get("рынок") or {})
                              .get("бар") or "")
                    if _bg:
                        _podpis_bar = _bg
                        if str(data) and str(data) != _bg:
                            _hvost_mesta = f" (место найдено на {data})"
                except Exception:
                    pass

                state["chat_history"].append({
                    "role": "system",
                    # PROGON_PODRYAD_V2: на сплошном ходу говорим, ЧТО
                    # случилось на баре, а не «разворотный None @ None».
                    "content": (f"📍 {_podpis_bar}{_hvost_mesta} · "
                                f"{k.get('почему')} → спрашиваю {imya}"
                                if k.get("подряд")
                                else f"📍 {_podpis_bar}{_hvost_mesta} · "
                                     f"{_kd.slovami(k)} → спрашиваю {imya}")})
                update_chat_display()

                def _zvat():
                    import council
                    return council.wake_council("", "", ceh_id=tseh_id)

                try:
                    itog = await loop.run_in_executor(None, _zvat)
                except Exception as e:
                    print(f"[ПРОГОН] Совет сорвался на {data}: {e}")
                    continue
                proydeno += 1

                r = (itog.get("results") or {}).get(_sl) or {}
                skazal = (r.get("narrative") or "").strip()
                if not skazal and r.get("error"):
                    skazal = f"(промолчал: {r['error']})"
                # OTCHYOT_PROGONA_V1: кадр этого места — в папку прогона,
                # рядом со строкой. Раньше все кадры валились в общую
                # кучу, и найти картинку к месту было нельзя.
                if _otchyot is not None:
                    try:
                        _otchyot.zapisat(k, _sl, imya, _sym, _tf, r, _kadr)
                    except Exception as _e:
                        print(f"[ОТЧЁТ] место не записалось: {_e}")
                # KADRY_V_CHATE_V1: забираем всё, что он видел за этот
                # вопрос, и вешаем на сообщение. Список чистим, чтобы
                # следующему ответу достались только его кадры.
                _kadry_otveta = []
                try:
                    from hooks import (load_trading_state as _lts_k,
                                       save_trading_state as _sts_k)
                    _tk = _lts_k()
                    _kadry_otveta = list(_tk.get("кадры_ответа") or [])
                    if _kadry_otveta:
                        _tk["кадры_ответа"] = []
                        _sts_k(_tk)
                except Exception as _e_k:
                    print(f"[ЧАТ] кадры ответа не забрались ({_e_k})")
                if _kadr and str(_kadr) not in _kadry_otveta:
                    _kadry_otveta.insert(0, str(_kadr))

                state["chat_history"].append({
                    "role": "assistant", "agent": _sl,
                    "content": skazal or "(без текста)",
                    "кадры": _kadry_otveta})
                update_chat_display()
                # TESTER_PULT_V1: предел по срабатываниям. Проверяем
                # ПОСЛЕ ответа, чтобы последний взгляд был договорён до
                # конца, а не обрезан на полуслове.
                if skolko and _razbudili >= skolko:
                    state["chat_history"].append({
                        "role": "system",
                        "content": (f"⏹ поймано {_razbudili} "
                                    f"срабатывани(й) — предел, "
                                    f"останавливаюсь")})
                    update_chat_display()
                    break

                # ── PROGON_VPERYOD_V1 ────────────────────────
                # Слово Шефа: «в чём разница факта? что на истории он
                # есть, что на реале — появилось, наблюдает, дошло,
                # вошла». Прогон прыгал через месяцы не потому, что
                # история такая, а потому что я его таким сделал.
                # Теперь: трейдер взял на карандаш — шагаем ВПЕРЁД по
                # одному настоящему бару и спрашиваем снова, пока он
                # наблюдает. Граница — дата следующего места: дальше
                # начинается своя точка, старую наблюдать не за чем.
                _sled = None
                try:
                    _i_tek = mesta.index((data, _sl, _sym, _tf, k))
                    if _i_tek + 1 < len(mesta):
                        _sled = mesta[_i_tek + 1][0]
                except Exception:
                    _sled = None
                # PROGON_PODRYAD_V2: на сплошном ходу шаги вперёд не
                # нужны — мы и так идём по каждому бару. Раньше два
                # способа ходить работали разом, курсор уезжал вперёд,
                # а внешний цикл продолжал из прошлого: время в ленте
                # ехало назад, точки рождались по два раза.
                while not k.get("подряд"):
                    if state.get("stop_requested"):
                        break
                    try:
                        import hooks as _h
                        if not _h.nablyudenie(_sym, _tf, _sl):
                            break
                        # PROGON_POSLE_SLOMA_V1: точка ушла — наблюдать
                        # больше не за чем, идём к следующему месту.
                        # Правило ТОЛЬКО для прогона: там следующее
                        # место известно заранее. В живом городе
                        # наблюдение снимает сам трейдер, и никто иной.
                        _tt = _h._blok_tochki(_h.load_trading_state(),
                                              _h._para_tochki(_sym, _tf))
                        if not _tt.get("alive"):
                            _h.snyat_nablyudenie(_sym, _tf, _sl,
                                                 "точка ушла")
                            state["chat_history"].append({
                                "role": "system",
                                "content": "✕ точка ушла — иду к "
                                           "следующему месту"})
                            update_chat_display()
                            break
                    except Exception as _en:
                        print(f"[ПРОГОН] наблюдение не прочлось: {_en}")
                        break
                    try:
                        _bylo = istoriya.gde_stoim()
                        _stalo = istoriya.shag(_tf, 1, _sym)
                    except Exception as _esh:
                        print(f"[ПРОГОН] шаг вперёд не вышел: {_esh}")
                        break
                    if not _stalo or _stalo == _bylo:
                        print("[ПРОГОН] история кончилась — иду дальше")
                        break
                    if _sled and _stalo >= _sled:
                        print("[ПРОГОН] дошёл до следующего места — "
                              "наблюдение закрываю")
                        try:
                            _h.snyat_nablyudenie(_sym, _tf, _sl,
                                                 "дошли до следующего места")
                        except Exception:
                            pass
                        break
                    # KONEC_VOLNY_1_V1: шагаем МОЛЧА. Рука рынка — код,
                    # не модель: ведёт точку и ищет конец первой волны
                    # бесплатно. Ключ закрыт — идём дальше даром.
                    try:
                        # SVYAZ_I_PAPKA_V1: молчаливый шаг — в рабочий
                        # поток. Раньше он считал приборы прямо в
                        # корутине и подмораживал окно на каждом баре.
                        def _schitat(s=_sym, t=_tf, sl=_sl):
                            import hooks as _hh2
                            _hh2.rynok_novyy_bar(s, t)
                            return __import__("council")._klyuch_probuzhdeniya(
                                s, t, sl)
                        _kk = await loop.run_in_executor(None, _schitat)
                    except Exception as _ekl:
                        print(f"[ПРОГОН] ключ не прочёлся: {_ekl}")
                        _kk = {"будим": True, "почему": "ключ не прочёлся"}
                    if not _kk.get("будим"):
                        continue
                    state["chat_history"].append({
                        "role": "system",
                        "content": f"👁 {_stalo} · {_kk.get('почему')} "
                                   f"→ спрашиваю {imya}"})
                    update_chat_display()
                    _kadr = None
                    try:
                        _kadr = await loop.run_in_executor(
                            None, lambda s=_sym, t=_tf: __import__(
                                "grafik").kadr(s, t))
                    except Exception as _ek:
                        print(f"[ПРОГОН] кадр не нарисовался: {_ek}")
                    try:
                        # PROGON_BEZ_OKNA_V1: показать — дело окна,
                        # а его может уже не быть. Кадр всё равно
                        # сохранён и попадёт в отчёт.
                        await pokazat_kadr(_kadr)
                    except Exception as _ep:
                        print(f"[ПРОГОН] кадр не показан ({_ep}) — "
                              f"он в отчёте")
                    try:
                        itog = await loop.run_in_executor(None, _zvat)
                    except Exception as e:
                        print(f"[ПРОГОН] Совет сорвался на {_stalo}: {e}")
                        break
                    r = (itog.get("results") or {}).get(_sl) or {}
                    skazal = (r.get("narrative") or "").strip()
                    if not skazal and r.get("error"):
                        skazal = f"(промолчал: {r['error']})"
                    if _otchyot is not None:
                        try:
                            _otchyot.zapisat(k, _sl, imya, _sym, _tf, r,
                                             _kadr)
                        except Exception as _e:
                            print(f"[ОТЧЁТ] шаг не записался: {_e}")
                    state["chat_history"].append({
                        "role": "assistant", "agent": _sl,
                        "content": skazal or "(без текста)"})
                    update_chat_display()
                # PROGON_VIDNO_V1: и в ОТЧЁТ справа. Раньше там висело
                # «Отчёт пока не создан»: прогон писал только в ленту.
                try:
                    _shapka = (f"# {imya} ({_sl})\n\n"
                               f"**{k.get('дата', '')}** · {_sym} {_tf} · "
                               f"разворотный {k.get('разворотный')} · "
                               f"волна {k.get('длина_волны')} баров · "
                               f"компас {k.get('компас')}\n\n---\n\n")
                    state["reports"][_sl] = _shapka + (
                        skazal or "(без текста)")
                    if state.get("active_agent") == _sl:
                        update_viewer(state["reports"][_sl])
                except Exception as _er2:
                    print(f"[ПРОГОН] отчёт не показался: {_er2}")
        finally:
            # LOG_PROGONA_SYROY_V1: возвращаем stdout ПЕРВЫМ делом —
            # finally срабатывает даже при необработанном исключении,
            # терминал не должен онеметь навсегда из-за сбоя прогона.
            sys.stdout = _original_stdout
            if _log_fayl_progona:
                try:
                    _log_fayl_progona.close()
                except Exception:
                    pass
            state["tester_running"] = False
            state["stop_requested"] = False
            try:
                istoriya.postavit(_bylo_moment)
            except Exception:
                pass

        # OTCHYOT_PROGONA_V1: закрываем отчёт и говорим, где он лёг.
        _gde = None
        if _otchyot is not None:
            try:
                _gde = _otchyot.zakryt()
            except Exception as _e:
                print(f"[ОТЧЁТ] не закрылся: {_e}")
        _hvost = ""
        if _gde:
            try:
                _otn = _gde.relative_to(Path(__file__).resolve().parent.parent)
            except Exception:
                _otn = _gde
            _hvost = f" · отчёт: {_otn}"
            print(f"[ОТЧЁТ] 📄 {_gde}")
        # ZHURNAL_PROGONA_V1: журнал сделок вместо списка фраз.
        # Даты берём из «когда_на_рынке» (отчёт кладёт их туда), а
        # места делим по ДЕЙСТВИЮ: вход, ведение, отказ, молчание.
        _vhodov = _otkazov = _vedeniy = _molchaniy = 0
        _stroki_zhurnala = []
        _gde_kadry = ""
        try:
            for _m in (_otchyot.mesta if _otchyot is not None else []):
                _kogda = str(_m.get("когда_на_рынке")
                             or _m.get("место_найдено_на") or "?")[:16]
                _d = str(_m.get("действие") or "").upper()
                _v = str(_m.get("вердикт") or "").upper()
                _pochemu = str(_m.get("причина") or "").strip()
                _kadr = str(_m.get("кадр") or "")
                if _kadr and not _gde_kadry:
                    _gde_kadry = "кадры"

                if _d == "ENTER" or _v in ("APPROVED", "ENTER", "OK"):
                    _vhodov += 1
                    _c = _m.get("цена_входа")
                    _s = _m.get("стоп_входа")
                    _hv = (f" @ {_c}" if _c else "")
                    _hv += (f", стоп {_s}" if _s else "")
                    _metka = f"ВОШЁЛ {_hv}".strip()
                elif _d in ("HOLD", "MOVE_STOP", "ADD", "CLOSE"):
                    _vedeniy += 1
                    _metka = {"HOLD": "ДЕРЖУ", "MOVE_STOP": "СТОП ПЕРЕНЁС",
                              "ADD": "ДОЛИЛ", "CLOSE": "ЗАКРЫЛ"}[_d]
                elif _d == "WAIT" or _v in ("REJECTED", "WAIT"):
                    _otkazov += 1
                    _metka = "ОТКАЗ"
                else:
                    _molchaniy += 1
                    _metka = "ПОДУМАЛ, приказа не было"
                _stroki_zhurnala.append(
                    f"  {_kogda:16} {_metka:22} {_pochemu[:58]}")
        except Exception as _e_it:
            print(f"[ИТОГ] не собрался ({_e_it})")

        _stroki = [f"✓ прогон окончен · мест {proydeno}{_hvost}", ""]
        _stroki += _stroki_zhurnala[:40]
        if len(_stroki_zhurnala) > 40:
            _stroki.append(f"  … ещё {len(_stroki_zhurnala) - 40} "
                           f"(все — в отчёте)")
        _stroki.append("")
        _stroki.append(f"ВХОДОВ: {_vhodov} · ВЕДЕНИЕ: {_vedeniy} · "
                       f"ОТКАЗОВ: {_otkazov} · БЕЗ ПРИКАЗА: {_molchaniy}")
        if _gde_kadry:
            _stroki.append("Кадры каждого места — в папке отчёта, "
                           "подпапка «кадры».")
        if not _vhodov and not _molchaniy:
            _stroki.append("Входов нет, но все решения отданы рукой — "
                           "он отказывался сам, причины выше.")

        state["chat_history"].append({
            "role": "system", "content": "\n".join(_stroki)})
        update_chat_display()
        ui.notify(f"✓ прогон окончен · {proydeno} мест", type="positive")

    async def market_dispatch():
        # ODNA_KNOPKA_V1: одна кнопка РЫНОК. В реале — живой Совет,
        # в тестере — прогон по истории. Старый run_tester_session
        # оставлен в файле нетронутым: он держится на упразднённой
        # Искре и не заводится, но выкидывать чужой труд не мне.
        if state.get("mode") == "tester":
            await progon_po_istorii()
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
        # UBRAT_CHETVERTOGO_V1: кабинет Совету пару НЕ передаёт.
        # Каждый берёт свою — инструмент из поста, этаж свой.
        _sym_now, _tf_now = "", ""
        ui.notify("📡 Совет: каждый смотрит своё", type="info")
        try:
            loop = asyncio.get_event_loop()
            # KABINET_ZNAET_CEH_V1: кабинет открыт по адресу цеха —
            # значит и Совет собираем по ЭТОМУ цеху, а не по зашитому.
            # Совет постарше про цех не знает — тогда зовём как раньше.
            def _zvat_sovet():
                try:
                    return council.wake_council(_sym_now, _tf_now,
                                                on_event=_on_event,
                                                ceh_id=tseh_id)
                except TypeError:
                    return council.wake_council(_sym_now, _tf_now,
                                                on_event=_on_event)

            _market_future = loop.run_in_executor(None, _zvat_sovet)
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

    def update_sostav():
        """PROSTO_I_ROVNO_V1: кто на местах и чем работаем — одной строкой.

        Раньше это было видно только по мелькающим уведомлениям, и
        выходило «говорят одно, написано другое». Теперь висит на месте.
        """
        el = sostav_ref.get("element")
        if el is None:
            return
        try:
            _s, _t = _aktivnyy_rynok()
            # PODPISI_POD_PUZYRKAMI_V1: по людям, а не общей кашей.
            # Видно сразу, кто чем занят и у кого своё.
            from vybor import instrument_dlya as _idl
            kuski = []
            for _sl in ("A06", "A07", "A08"):
                _row = _agent_row(roster, _sl)
                if not (_row and _row.get("resident")):
                    continue
                _imya = _row["resident"].get("имя", _sl)
                try:
                    _ins, _otk = _idl(tseh_id, _sl, _s)
                except Exception:
                    _ins, _otk = _s, ""
                _svoy = _otk in ("назначен", "выбрал сам")
                _cvet = "rgba(0,255,136,0.9)" if _svoy else \
                        "rgba(255,255,255,0.6)"
                kuski.append(f'{_imya} — <b style="color:{_cvet}">'
                             f'{_ins or _s} {_t}</b>')
            if not kuski:
                kuski = ['<span style="opacity:.5">за столом никого</span>']
            _text = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(kuski)
            if _VAHTA["идёт"]:
                _text += ('&nbsp;&nbsp;·&nbsp;&nbsp;'
                          '<span style="color:#00ccff">вахта идёт</span>')
            el.content = _text
        except Exception:
            pass

    # PUZYR_PODSVETKA_V2: кольцо рисуем ПРЯМО В style, с !important.
    # Классы .active/.done оставляем — они не мешают, но у QBtn свои
    # стили на border-color/box-shadow, и класс снаружи им проигрывает.
    # Inline-стиль сильнее — спорить больше не с чем.
    _PODSVETKA = {
        "active": ("border-color: rgba(0,204,255,0.75) !important; "
                   "box-shadow: 0 0 0 2px rgba(0,204,255,0.25) inset, "
                   "0 0 30px rgba(0,204,255,0.35) !important;"),
        "done":   ("border-color: rgba(0,255,136,0.75) !important; "
                   "box-shadow: 0 0 0 2px rgba(0,255,136,0.25) inset, "
                   "0 0 30px rgba(0,255,136,0.35) !important;"),
    }

    def update_avatar_states():
        _vidno = []   # PUZYR_NE_OBRYVAETSYA_V3
        _stil_leg = 0   # PUZYR_STILEM_I_UPDATE_V4
        for aid, el in avatars_ref["elements"].items():
            row = _agent_row(roster, aid)
            base = "avatar vacant" if (row and not row["resident"]) else "avatar"
            el.classes(replace=base)
            if aid == state["active_agent"]:
                el.classes(add="active")
            if aid in state["reports"]:
                el.classes(add="done")
            # PUZYR_NE_OBRYVAETSYA_V3: собираем, что применилось —
            # печать одной строкой ниже, после обхода всех.
            _vidno.append(f"{aid}=" + ("active" if aid == state["active_agent"]
                                       else "done" if aid in state["reports"]
                                       else "vacant" if "vacant" in base
                                       else "—"))

            # PUZYR_STILEM_I_UPDATE_V4: кольцо — inline-стилем, с
            # !important. Классов оказалось мало: сервер их менял
            # (видно строкой выше), а на экране кольцо не переезжало.
            # Inline сильнее классов и стилей Quasar; плюс явная
            # команда обновиться — на случай, если автописьмо в
            # браузер не уходит.
            try:
                if not hasattr(el, "_baz_style_puzyrya"):
                    el._baz_style_puzyrya = "; ".join(
                        f"{_k}: {_v}" for _k, _v in
                        getattr(el, "_style", {}).items()) or ""
                if aid == state["active_agent"]:
                    _hvost = ("border-color: rgba(0,204,255,0.95) !important; "
                              "box-shadow: 0 0 0 2px rgba(0,204,255,0.30) inset, "
                              "0 0 30px rgba(0,204,255,0.45) !important;")
                elif aid in state["reports"]:
                    _hvost = ("border-color: rgba(0,255,136,0.95) !important; "
                              "box-shadow: 0 0 0 2px rgba(0,255,136,0.30) inset, "
                              "0 0 30px rgba(0,255,136,0.45) !important;")
                else:
                    _hvost = ("border-color: rgba(255,255,255,0.14) !important; "
                              "box-shadow: none !important;")
                _baz = el._baz_style_puzyrya
                el.style(replace=(_baz + "; " if _baz else "") + _hvost)
                el.update()
                _stil_leg += 1
            except Exception as _e_st:
                print(f"[ПУЗЫРЬ] ⚠ стиль {aid} не лёг: {_e_st}")

            # активный важнее «отчёт готов»: смотрим-то мы на него
            if aid == state["active_agent"]:
                hvost = _PODSVETKA["active"]
            elif aid in state["reports"]:
                hvost = _PODSVETKA["done"]
            else:
                hvost = ""
            try:
                bazovyy = getattr(el, "_bazovyy_style", "") or ""
                el.style(replace=bazovyy + hvost)
            except Exception:
                pass

        # PUZYR_NE_OBRYVAETSYA_V3: одна строка на клик — видно сразу,
        # дошла подсветка или нет, и к скольким пузырькам.
        # PUZYR_PRYAMO_V_BRAUZER_V5: приказываем браузеру напрямую.
        # Обновление элементов где-то теряется (см. докстроку патча),
        # а команда из обработчика клика уходит в ТО окно, где кликнули.
        try:
            _kuski = []
            for _aid, _el in avatars_ref["elements"].items():
                if _aid == state["active_agent"]:
                    _bc, _bs = ("rgba(0,204,255,0.95)",
                                "0 0 0 2px rgba(0,204,255,0.30) inset, "
                                "0 0 30px rgba(0,204,255,0.45)")
                elif _aid in state["reports"]:
                    _bc, _bs = ("rgba(0,255,136,0.95)",
                                "0 0 0 2px rgba(0,255,136,0.30) inset, "
                                "0 0 30px rgba(0,255,136,0.45)")
                else:
                    _bc, _bs = ("rgba(255,255,255,0.14)", "none")
                # PUZYR_BEZ_GETHTMLELEMENT_V6: getHtmlElement есть
                # только с NiceGUI 2.9 — на здешней версии команда
                # падала целиком (ReferenceError в консоли). Берём
                # самый обычный способ: браузер сам находит пузырьки
                # по их оформлению, в порядке отрисовки.
                _kuski.append("['%s','%s']" % (_bc, _bs))
            if _kuski:
                _js = ("(()=>{const st=[" + ",".join(_kuski) + "];"
                       "const els=document.querySelectorAll('.avatar');"
                       "els.forEach((e,i)=>{if(st[i]){"
                       "e.style.setProperty('border-color',st[i][0],'important');"
                       "e.style.setProperty('box-shadow',st[i][1],'important');"
                       "}});})();")
                ui.run_javascript(_js)
                print(f"[ПУЗЫРЬ] команда в браузер: {len(_kuski)} пузырьков")
        except Exception as _e_js:
            # фоновый вызов без окна — это нормально, не шумим лишнего
            print(f"[ПУЗЫРЬ] команда в браузер не ушла: {_e_js}")

        if _vidno:
            print("[ПУЗЫРЬ] подсветка: " + " ".join(_vidno))
            print(f"[ПУЗЫРЬ] стиль применён: {_stil_leg} из {len(_vidno)}")
        else:
            print("[ПУЗЫРЬ] ⚠ подсветка: пузырьков в avatars_ref НЕТ")

    async def switch_agent(agent_id: str):
        row = _agent_row(roster, agent_id)
        if row and not row["resident"]:
            ui.notify("Вакансия — сюда ещё никого не наняли", type="warning")
        state["active_agent"] = agent_id
        # PUZYR_NE_OBRYVAETSYA_V3: раньше эти четыре шли подряд и без
        # защиты — споткнулся первый, и подсветка (третья в очереди)
        # не наступала вовсе. Снаружи выглядело как мёртвый пузырёк.
        # Теперь подсветка первая, и каждый шаг сам за себя.
        for _imya_shaga, _shag in (("update_avatar_states", update_avatar_states),
                                   ("update_avatar", update_avatar),
                                   ("update_vitals", update_vitals),
                                   ("update_stats_panel", update_stats_panel)):
            try:
                _shag()
            except Exception as _e_shag:
                print(f"[ПУЗЫРЬ] ⚠ {_imya_shaga} сорвалась: {_e_shag}")
        # NAZNACHENIYA_PROCH_V1: было уведомление про инструмент —
        # мелькало и пропадало. Теперь всё в строке состава.
        try:
            update_files_display()
            update_sostav()
        except Exception:
            pass
        label = _agent_label(roster, agent_id)
        if agent_id in state["reports"]:
            update_viewer(f"# {label} ({agent_id})\n\n{state['reports'][agent_id]}")
        else:
            update_viewer(f"# {label} ({agent_id})\n\n*Отчёт пока не создан.*")
        # VZGLYAD_KAZHDOGO_V1: кликнул трейдера — сразу его взгляд.
        # Кадр рисуется из готовых баров, модель не зовётся: это
        # по-прежнему бесплатный просмотр для Шефа.
        try:
            await pokazat_kadr()
        except Exception as _e:
            print(f"[ВЗГЛЯД] кадр не показался: {_e}")

    # ── загрузчик (левая колонка) ────────────────────────────
    def _slot_agenta(agent_id: str) -> str:
        """Слот, если это торговое место. Морж и прочие — не в счёт."""
        row = _agent_row(roster, agent_id) or {}
        slot = row.get("slot") or row.get("old_id") or agent_id
        return slot if slot in ("A06", "A07", "A08") else ""

    def set_active(i):
        """Клик по полке: чем работает ВЫБРАННЫЙ сейчас трейдер.

        PODPISI_POD_PUZYRKAMI_V1: кликнул человека наверху, кликнул
        инструмент слева — он взял его. Кто чем занят, тут же написано
        строкой ниже, по именам. Никого не выбрал — меняем общий.
        """
        assets = state.get("loaded_assets", [])
        if not (0 <= i < len(assets)):
            return
        state["active_asset"] = i
        a = assets[i]
        slot = _slot_agenta(state.get("active_agent", ""))
        if slot:
            try:
                from vybor import naznachit as _nazn
                _nazn(tseh_id, slot, a["symbol"])
                # SVOY_VYBOR_U_KAZHDOGO_V1: запоминаем и ЭТАЖ — тому,
                # кого Шеф сейчас выбрал, и только ему. Раньше клик
                # назначал один инструмент, а этаж молча брался «от
                # комфорта»: выбрать этаж трейдеру было нечем.
                try:
                    from vybor import zapisat_etazh as _zap
                    _zap(tseh_id, slot, a["symbol"], a["timeframe"])
                except Exception as _e_et:
                    print(f"[ВЫБОР] этаж не запомнился ({_e_et})")
                imya = _agent_label(roster, state["active_agent"])
                ui.notify(f"{imya} → {a['symbol']} {a['timeframe']}",
                          type="positive")
                print(f"[РАБОТА] {imya} ({slot}) → {a['symbol']}")
            except Exception as e:
                ui.notify(f"⚠ не записалось: {e}", type="negative")
        else:
            ui.notify(f"Работаем: {a['symbol']} {a['timeframe']}", type="info")
        if _VAHTA["идёт"]:
            _VAHTA.update({"инструмент": a["symbol"],
                           "этаж": a["timeframe"], "бар": ""})
        update_files_display()

    def update_files_display():
        update_sostav()          # PROSTO_I_ROVNO_V1: состав всегда свеж
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
            # POLKA_IZ_TERMINALA_V1: живое и история лежат рядом — пусть
            # будет видно, что есть что. Спутать их дороже всего.
            _zhivyh = sum(1 for _a in assets
                          if _a.get("источник") == "терминал")
            if _zhivyh:
                ui.label(f"из терминала: {_zhivyh}").style(
                    "color:rgba(0,255,136,0.55); font-size:9px; "
                    "letter-spacing:.08em; padding:0 4px 4px;")

            groups = {}
            order = []
            for i, a in enumerate(assets):
                sym = a["symbol"]
                if sym not in groups:
                    groups[sym] = []
                    order.append(sym)
                groups[sym].append(i)

            # LENIVAYA_POLKA_V1: инструменты из терминала, у которых
            # этажи ещё не смотрели, тоже стоят на полке — пустой
            # папкой. Раскрыл — сходили. Так список виден сразу, а
            # платим только за открытое.
            for sym in (state.get("term_spisok") or []):
                if sym not in groups:
                    groups[sym] = []
                    order.append(sym)

            for sym in order:
                idxs = groups[sym]
                has_active = active in idxs
                _podpis = (f"{sym}  ·  {len(idxs)} ТФ" if idxs
                           else f"{sym}  ·  раскрой — посмотрю этажи")
                # POLKA_POMNIT_V1: раскрытые папки помним. Разведка
                # этажей перерисовывает полку, и папка закрывалась
                # ровно тогда, когда в ней появлялось содержимое.
                _pomnim = state.setdefault("раскрыто", set())
                with ui.expansion(
                    _podpis,
                    value=(has_active or sym in _pomnim),
                    on_value_change=lambda e, s=sym: _raskryli_papku(
                        s, bool(getattr(e, "value", False))),
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

    # SVYAZ_I_PAPKA_V1: память полки живёт в модуле, а не в странице —
    # переподключился браузер, страница новая, а разобранные файлы те же.
    global _PASPORTA_KESH
    try:
        _PASPORTA_KESH
    except NameError:
        _PASPORTA_KESH = {}

    def _passport_from_csv(path):
        # SVYAZ_I_PAPKA_V1: помним разобранные файлы по пути, размеру и
        # времени правки. Пересборка страницы (а она случается на КАЖДОМ
        # переподключении браузера) читала весь каталог заново — почти
        # миллион баров в главном потоке. Сервер молчал, браузер рвал
        # связь по минуте, страница строилась опять — и так по кругу.
        from williams_core import read_mt5_csv
        p = Path(path)
        try:
            st = p.stat()
            klyuch = (str(p.resolve()), st.st_size, int(st.st_mtime))
        except Exception:
            klyuch = None
        if klyuch is not None and klyuch in _PASPORTA_KESH:
            return dict(_PASPORTA_KESH[klyuch])

        # POLKA_NE_DUSHIT_SVYAZ_V1: полке нужны ТРИ числа — сколько
        # баров, первая дата, последняя. Раньше ради них разбирался
        # ВЕСЬ файл, и на тридцати трёх файлах это было около полутора
        # миллионов баров в главной нитке. Пока сервер их грыз, он не
        # отвечал браузеру — тот рвал связь («Connection lost»), после
        # переподключения страница строилась заново, и всё по кругу.
        # Отсюда же пустой экран и «пузыри не жмутся»: нажатие до
        # сервера доходит, а ответить некому.
        #
        # Считаем строки кусками, даты берём с двух концов файла.
        # Ни одно число не разбирается. Не получилось — падаем на
        # прежний полный разбор, чтобы файл не пропал с полки.
        _bystro = _bystryy_pasport(p)
        if _bystro is not None:
            symbol, tf = _parse_symbol_tf(p.name)
            _pasport = dict(_bystro)
            _pasport.update({"name": p.name, "path": str(p),
                             "symbol": symbol, "timeframe": tf})
            if klyuch is not None:
                _PASPORTA_KESH[klyuch] = dict(_pasport)
            return _pasport

        bars = read_mt5_csv(str(p))
        if not bars:
            return None
        symbol, tf = _parse_symbol_tf(p.name)
        _pasport = {
            "name": p.name, "path": str(p), "symbol": symbol, "timeframe": tf,
            "bars": len(bars), "date_from": bars[0].get("date", "?"), "date_to": bars[-1].get("date", "?"),
        }
        if klyuch is not None:      # SVYAZ_I_PAPKA_V1
            _PASPORTA_KESH[klyuch] = dict(_pasport)
        return _pasport

    # POLKA_IZ_TERMINALA_V1 — какие этажи спрашиваем у терминала.
    # Не все подряд: минутка и двухчасовка редко нужны, а опрос платный
    # временем. Пустые этажи на полку не кладём.
    # OKNO_MOGLO_UYTI_V1: было девять этажей — на большом обзоре рынка это
    # сотни походов в терминал, опрос тянулся минутами, и страница успевала
    # уйти из-под него. Шесть рабочих этажей и потолок по инструментам:
    # быстро, и хватает на всё, чем торгуют.
    _TERM_ETAZHI = ("M15", "M30", "H1", "H4", "D1", "W1")
    _TERM_POTOLOK = 25      # инструментов за раз; обзор рынка длиннее — режем

    # ── LENIVAYA_POLKA_V1 ──────────────────────────────────────
    # Список — сразу и целиком. Этажи — только у того инструмента,
    # который открыли. Раньше платили за всё сразу, оттого и висело.

    def _vse_etazhi_nasosa() -> tuple:
        """Все этажи, какие знает насос, от старших к младшим."""
        try:
            import sys as _s
            _b = str(_HERE)
            if _b not in _s.path:
                _s.path.insert(0, _b)
            import mt5_feed as _mf
            karta = dict(getattr(_mf, "_TF_MAP", {}) or {})
        except Exception:
            karta = {}
        if not karta:
            return _TERM_ETAZHI
        poryadok = ["MN1", "W1", "D1", "H12", "H8", "H4", "H2", "H1",
                    "M30", "M20", "M15", "M12", "M10", "M6", "M5",
                    "M4", "M3", "M2", "M1"]
        est = [tf for tf in poryadok if tf in karta]
        # то, чего нет в нашем порядке, но есть у насоса — в хвост
        est += [tf for tf in karta if tf not in est]
        return tuple(est)

    def _otkryt_terminal():
        """(mt5, беда). Связь открыта — закрывать зовущему."""
        try:
            import sys as _s
            _b = str(_HERE)
            if _b not in _s.path:
                _s.path.insert(0, _b)
            import mt5_feed as _mf
        except Exception as e:
            return None, None, f"насос не поднялся: {e}"
        mt5 = _mf._terminal()
        if mt5 is None:
            return None, None, ("MetaTrader5 для питона не установлен — "
                                "поставь его и перезапусти город")
        try:
            if not mt5.initialize():
                oshibka = ""
                try:
                    oshibka = f" ({mt5.last_error()})"
                except Exception:
                    pass
                return None, None, ("терминал не отвечает" + oshibka +
                                    ". Запусти MetaTrader и войди в счёт")
        except Exception as e:
            return None, None, f"связь с терминалом не открылась: {e}"
        return mt5, _mf, ""

    def _spisok_iz_terminala() -> tuple:
        """Только ИМЕНА инструментов. Один поход, без баров."""
        mt5, _mf, beda = _otkryt_terminal()
        if beda:
            return [], beda
        try:
            vse = mt5.symbols_get() or []
        except Exception as e:
            return [], f"терминал не отдал список: {e}"
        finally:
            try:
                mt5.shutdown()
            except Exception:
                pass
        if not vse:
            return [], ("терминал на связи, но инструментов не отдал — "
                        "проверь, что счёт залогинен")
        vidnye = [getattr(s, "name", "") for s in vse
                  if getattr(s, "visible", False)]
        vidnye = [n for n in vidnye if n]
        if not vidnye:
            vidnye = [getattr(s, "name", "") for s in list(vse)[:10]]
            vidnye = [n for n in vidnye if n]
        return vidnye, ""

    def _etazhi_instrumenta(imya: str) -> tuple:
        """Все живые этажи ОДНОГО инструмента. Платим только за него."""
        mt5, _mf, beda = _otkryt_terminal()
        if beda:
            return [], beda
        aktivy = []
        try:
            try:
                info = mt5.symbol_info(imya)
                if info is not None and not getattr(info, "visible", True):
                    mt5.symbol_select(imya, True)
            except Exception:
                pass
            for tf in _vse_etazhi_nasosa():
                kod = (getattr(_mf, "_TF_MAP", {}) or {}).get(tf)
                if kod is None:
                    continue
                try:
                    bary = mt5.copy_rates_from_pos(imya, kod, 0, 2)
                except Exception:
                    bary = None
                if bary is None or len(bary) == 0:
                    continue          # этаж молчит — на полку не кладём
                try:
                    from datetime import datetime as _dt
                    posledniy = _dt.fromtimestamp(
                        int(bary[-1]["time"])).strftime("%Y.%m.%d %H:%M")
                except Exception:
                    posledniy = "?"
                aktivy.append({
                    "name": f"{imya} {tf}", "path": "", "symbol": imya,
                    "timeframe": tf, "bars": 0,
                    "date_from": "терминал", "date_to": posledniy,
                    "источник": "терминал",
                })
        finally:
            try:
                mt5.shutdown()
            except Exception:
                pass
        if not aktivy:
            return [], f"{imya}: терминал не отдал ни одного этажа"
        return aktivy, ""

    async def _razvedat_instrument(imya: str):
        """Раскрыли папку — сходить за этажами именно этого."""
        razvedano = state.setdefault("разведано", set())
        if imya in razvedano or state.get("развед_идёт") == imya:
            return
        state["развед_идёт"] = imya
        try:
            ui.notify(f"📡 {imya}: смотрю этажи…", type="info")
        except Exception:
            pass
        import asyncio as _a
        try:
            aktivy, beda = await _a.get_event_loop().run_in_executor(
                None, _etazhi_instrumenta, imya)
        finally:
            state["развед_идёт"] = ""
        if beda:
            print(f"[ПОЛКА] ⚠️  {beda}")
            try:
                ui.notify(f"⚠ {beda}", type="warning")
            except Exception:
                pass
            return
        est = state.get("loaded_assets") or []
        byli = {(a.get("symbol"), a.get("timeframe")) for a in est}
        novye = [a for a in aktivy
                 if (a["symbol"], a["timeframe"]) not in byli]
        state["loaded_assets"] = est + novye
        razvedano.add(imya)
        print(f"[ПОЛКА] 📂 {imya}: этажей {len(aktivy)}")
        try:
            update_files_display()
        except Exception as e:
            print(f"[ПОЛКА] полка не перерисовалась: {e}")

    def _raskryli_papku(imya: str, otkryta: bool):
        """Обработчик раскрытия. Задачей — рисовать нельзя блокируя."""
        # POLKA_POMNIT_V1: запоминаем ДО всего остального — иначе
        # перерисовка после разведки закроет то, что Шеф открыл.
        _pomnim = state.setdefault("раскрыто", set())
        if otkryta:
            _pomnim.add(imya)
        else:
            _pomnim.discard(imya)
        if not otkryta:
            return
        if imya in (state.get("разведано") or set()):
            return
        try:
            import asyncio as _a
            _a.get_event_loop().create_task(_razvedat_instrument(imya))
        except Exception as e:
            print(f"[ПОЛКА] разведка не пошла: {e}")

    def _sobrat_iz_terminala() -> tuple:
        """Спросить сам терминал: что открыто в обзоре рынка и что живо.

        Возвращает (активы, беда). Беда — текстом, чтобы кабинет мог
        сказать её вслух, а не молчать.
        """
        try:
            import sys as _s
            _b = str(_HERE)
            if _b not in _s.path:
                _s.path.insert(0, _b)
            import mt5_feed as _mf
        except Exception as e:
            return [], f"насос не поднялся: {e}"

        mt5 = _mf._terminal()
        if mt5 is None:
            return [], ("MetaTrader5 для питона не установлен — "
                        "поставь его и перезапусти город")

        # SVYAZ_S_TERMINALOM_V1: _terminal() только ИМПОРТИРУЕТ библиотеку,
        # связь он не открывает — имя обмануло. Без initialize() терминал
        # молчит на всё: список инструментов пуст, баров нет, а выглядит
        # это как «на связи, но котировок не даёт».
        try:
            if not mt5.initialize():
                oshibka = ""
                try:
                    oshibka = f" ({mt5.last_error()})"
                except Exception:
                    pass
                return [], ("терминал не отвечает" + oshibka +
                            ". Запусти MetaTrader и войди в счёт — "
                            "питон говорит с УЖЕ ОТКРЫТЫМ терминалом")
        except Exception as e:
            return [], f"связь с терминалом не открылась: {e}"

        try:
            vse = mt5.symbols_get() or []
        except Exception as e:
            try:
                mt5.shutdown()
            except Exception:
                pass
            return [], f"терминал не отдал список инструментов: {e}"

        if not vse:
            try:
                mt5.shutdown()
            except Exception:
                pass
            return [], ("терминал на связи, но инструментов не отдал — "
                        "проверь, что счёт залогинен")

        vidnye = [s for s in vse if getattr(s, "visible", False)]
        if not vidnye:
            vidnye = list(vse)[:10]      # обзор пуст — берём хоть что-то
        vidnye = vidnye[:_TERM_POTOLOK]

        aktivy = []
        for s in vidnye:
            imya = getattr(s, "name", "")
            if not imya:
                continue
            # SVYAZ_S_TERMINALOM_V1: инструмент, не отмеченный в обзоре
            # рынка, баров не отдаёт — сперва берём его в обзор.
            try:
                info = mt5.symbol_info(imya)
                if info is not None and not getattr(info, "visible", True):
                    mt5.symbol_select(imya, True)
            except Exception:
                pass
            for tf in _TERM_ETAZHI:
                kod = _mf._TF_MAP.get(tf)
                if kod is None:
                    continue
                try:
                    bary = mt5.copy_rates_from_pos(imya, kod, 0, 2)
                except Exception:
                    bary = None
                if bary is None or len(bary) == 0:
                    continue          # этаж молчит — на полку не кладём
                try:
                    from datetime import datetime as _dt
                    posledniy = _dt.fromtimestamp(
                        int(bary[-1]["time"])).strftime("%Y.%m.%d %H:%M")
                except Exception:
                    posledniy = "?"
                aktivy.append({
                    "name": f"{imya} {tf}", "path": "", "symbol": imya,
                    "timeframe": tf, "bars": 0,
                    "date_from": "терминал", "date_to": posledniy,
                    "источник": "терминал",
                })
        try:
            mt5.shutdown()
        except Exception:
            pass
        if not aktivy:
            return [], (f"терминал на связи, инструментов видит "
                        f"{len(vidnye)}, но баров не отдал ни по одному — "
                        f"похоже, счёт не залогинен или брокер не даёт "
                        f"историю")
        return aktivy, ""

    async def sobrat_terminal():
        """Кнопка ТЕРМИНАЛ: сходить и разложить котировки по полке.

        OKNO_MOGLO_UYTI_V1: опрос долгий, а страница за это время могла
        перезагрузиться. Тогда окно, в которое мы собрались рисовать,
        уже мертво — NiceGUI роняет KeyError изнутри. Поэтому всё, что
        трогает экран ПОСЛЕ похода, обёрнуто: данные ложатся в state
        всегда, а рисуем — если есть куда.
        """
        def _tiho(chto, *a, **kw):
            try:
                chto(*a, **kw)
            except Exception:
                pass       # окна нет — не беда, данные уже сохранены

        # LENIVAYA_POLKA_V1: спрашиваем ТОЛЬКО СПИСОК — один поход.
        # Этажи подтянутся при раскрытии папки, каждый за себя.
        _tiho(ui.notify, "📡 спрашиваю терминал…", type="info")
        import asyncio as _a
        imena, beda = await _a.get_event_loop().run_in_executor(
            None, _spisok_iz_terminala)
        if not beda:
            state["term_spisok"] = imena
            state.setdefault("разведано", set())
            print(f"[ТЕРМИНАЛ] 📋 инструментов {len(imena)} — "
                  f"этажи по клику")
        aktivy = []
        if beda:
            _tiho(ui.notify, f"⚠ {beda}", type="warning")
            print(f"[ТЕРМИНАЛ] ⚠️  {beda}")
            return
        # файлы не выкидываем: живое и история лежат рядом, но помечены
        bylo = [x for x in state.get("loaded_assets", [])
                if x.get("источник") != "терминал"]
        # VZGLYAD_KAZHDOGO_V1: запомнили выбор ИМЕНЕМ до перестройки.
        # Свежее ложится в начало, всё съезжает вниз — и прежний
        # номер строки начинает показывать на чужой актив. Первым в
        # опросе этажей идёт M15, поэтому сброс всегда выглядел как
        # «скинуло на M15».
        _bylo_vybrano = _zapomnit_vybor()
        state["loaded_assets"] = aktivy + bylo
        _vernut_vybor(_bylo_vybrano)
        simvolov = len({x["symbol"] for x in aktivy})
        print(f"[ТЕРМИНАЛ] 📡 инструментов {simvolov}, этажей {len(aktivy)}")
        _tiho(update_files_display)
        _tiho(ui.notify, f"📡 с терминала: инструментов {simvolov}, "
                         f"этажей {len(aktivy)}", type="positive")

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
        # VZGLYAD_KAZHDOGO_V1: пересканирование папки роняло выбор
        # так же молча, как ТЕРМИНАЛ.
        _bylo_vybrano = _zapomnit_vybor()
        state["loaded_assets"] = assets
        _vernut_vybor(_bylo_vybrano, tiho=True)

    async def handle_upload(e):
        name = e.name
        try:
            content = e.content.read() if hasattr(e.content, "read") else e.content
        except Exception as _ce:
            ui.notify(f"Не прочитать файл: {_ce}", type="negative")
            return
        # KARTINKA_SHEFA_V1: картинку Шеф показывает жителю, а не
        # заряжает как котировки. Уходит тем же путём, что «Взгляд».
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            try:
                from pathlib import Path as _Pk
                from datetime import datetime as _dtk
                _pap = _Pk(__file__).resolve().parent / "показанное"
                _pap.mkdir(parents=True, exist_ok=True)
                _dest = _pap / name
                _dest.write_bytes(content)
                from hooks import load_trading_state, save_trading_state
                _tk = load_trading_state()
                _tk["vzglyad_shefa"] = {
                    "путь": str(_dest),
                    "подпись": _Pk(name).stem,
                    "когда": _dtk.now().isoformat(timespec="seconds"),
                }
                save_trading_state(_tk)
                ui.notify(f"\U0001f5bc Показываю жителю: {_Pk(name).stem}",
                          type="positive")
            except Exception as _ke:
                ui.notify(f"Картинка не дошла: {_ke}", type="negative")
            _up = files_ref.get("uploader")
            if _up:
                try:
                    _up.reset()
                except Exception:
                    pass
            return
        if not name.lower().endswith(".csv"):
            ui.notify("Нужен CSV экспорта MT5 или картинка", type="warning")
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
    # ═══ CHAT_KNOPKI_I_OSMYSLIT_V1 ═══
    # Сохранить / достать — тем же способом и с тем же именем файла,
    # что в кабинете Брата: один город, одна привычка.
    _CHATY_DIR = Path(__file__).resolve().parent / "чаты"

    def _sohranit_chat():
        if not state.get("chat_history"):
            ui.notify("Разговор пустой — нечего сохранять", type="warning")
            return
        try:
            import json
            from datetime import datetime as _dt
            _CHATY_DIR.mkdir(parents=True, exist_ok=True)
            ts = _dt.now().strftime("%Y-%m-%d_%H-%M-%S")
            fp = _CHATY_DIR / f"чат_{ts}.json"
            fp.write_text(json.dumps(state["chat_history"],
                                     ensure_ascii=False, indent=2),
                          encoding="utf-8")
            ui.notify(f"💾 сохранено: {fp.name}", type="positive")
        except Exception as e:
            ui.notify(f"не сохранилось: {e}", type="negative")

    def _dostat_chat():
        try:
            files = sorted(_CHATY_DIR.glob("чат_*.json"), reverse=True) \
                if _CHATY_DIR.exists() else []
        except Exception:
            files = []
        if not files:
            ui.notify("Сохранённых разговоров нет", type="warning")
            return
        with ui.dialog() as _dlg, ui.card().style(
                "background:#0d1117;border:1px solid rgba(255,255,255,0.12);"
                "border-radius:16px;min-width:340px;padding:20px;"):
            ui.html('<div style="color:rgba(255,255,255,0.9);font-weight:700;'
                    'font-size:0.9rem;margin-bottom:14px;letter-spacing:0.08em;">'
                    '📂 ВЫБЕРИ РАЗГОВОР</div>')
            for fp in files[:20]:
                def _zagruzit(f=fp):
                    try:
                        import json
                        state["chat_history"] = json.loads(
                            f.read_text(encoding="utf-8"))
                        update_chat_display()
                        _dlg.close()
                        ui.notify(f"📂 загружен: {f.name}", type="positive")
                    except Exception as e:
                        ui.notify(f"не загрузилось: {e}", type="negative")
                ui.button(fp.stem.replace("чат_", ""),
                          on_click=_zagruzit).props("flat no-caps").style(
                    "width:100%;text-align:left;font-family:monospace;"
                    "font-size:0.78rem;color:rgba(255,255,255,0.75);"
                    "padding:8px 12px;border-radius:8px;"
                    "background:rgba(255,255,255,0.04);margin-bottom:4px;")
            ui.button("отмена", on_click=_dlg.close).props("flat").style(
                "margin-top:10px;color:rgba(255,255,255,0.4);font-size:0.75rem;")
        _dlg.open()

    def _ochistit_razgovor():
        """Чистит ТОЛЬКО ленту разговора. История сделок — своя кнопка
        наверху, её этот веник не трогает. Нужно при смене модели:
        новая не должна получать разговор, который вела предыдущая,
        иначе подхватит чужой голос и чужие выводы."""
        n = len(state.get("chat_history") or [])
        if not n:
            ui.notify("Разговор и так пуст", type="info")
            return
        with ui.dialog() as _dlg, ui.card().style(
                "background:#1a1f2e;border:1px solid rgba(255,255,255,0.1);"):
            ui.label(f"Очистить разговор? ({n} сообщений)").style(
                "font-weight:700;color:rgba(255,255,255,0.9);font-size:14px;")
            ui.label("История сделок не пострадает — у неё своя кнопка "
                     "наверху. Сохранённые разговоры тоже останутся.").style(
                "color:rgba(255,255,255,0.55);font-size:12px;max-width:340px;")
            with ui.row():
                ui.button("отмена", on_click=_dlg.close).props("flat")

                def _da():
                    state["chat_history"] = []
                    update_chat_display()
                    _dlg.close()
                    ui.notify("🧹 разговор очищен", type="positive")
                ui.button("Очистить", on_click=_da).props("color=negative")
        _dlg.open()

    async def _osmyslit():
        """Житель сам пишет вывод по последним своим словам — и вывод
        ложится ему В ПАМЯТЬ КАК РАБОЧИЙ.

        Почему рабочий, а не «общение». Память жителя раскладывается по
        КОНТЕКСТУ входа, и мост с Биржи спрашивает только рабочее. Если
        записать разговор как общение — за столом он не всплывёт
        никогда, и выученное у Шефа пропадёт даром. Слово Шефа: «на
        работе же разговор».

        Вывод пишет ОН, а не мы: своими словами, по своим последним
        сообщениям. Мы только просим и кладём.
        """
        aid = state.get("active_agent")
        _karta = {"A02": ("торговый_хаос", "A02", "chat_with_morj"),
                  "A03": ("торговый_хаос", "A03", "chat_with_panikyor"),
                  "A04": ("торговый_хаос", "A04", "chat_with_hans"),
                  "A05": ("контора", "архивариус", "chat_with_arkhiv"),
                  "A06": ("торговый_хаос", "A06", "chat_with_brut"),
                  "A07": ("торговый_хаос", "A07", "chat_with_avan"),
                  "A08": ("торговый_хаос", "A08", "chat_with_cons"),
                  "A09": ("контора", "исполнитель", "chat_with_executor")}
        if aid not in _karta:
            ui.notify("Осмыслить может только живой собеседник", type="warning")
            return
        _ceh_id, _slot, _fn_name = _karta[aid]
        svoi = [m for m in (state.get("chat_history") or [])
                if m.get("role") == "assistant" and m.get("agent") == aid
                and m.get("content")]
        if not svoi:
            ui.notify("Он ещё ничего не сказал — осмыслять нечего",
                      type="warning")
            return
        label = _agent_label(roster, aid)
        ui.notify(f"🧠 {label} осмысляет...", type="info")
        prosba = (
            "Остановись и посмотри на свои последние слова в этом "
            "разговоре. Что ты из него забрал ДЛЯ РАБОТЫ? Напиши ОДИН "
            "короткий вывод своими словами — одно-два предложения, без "
            "пересказа разговора и без JSON. Не «мы обсудили то-то», а "
            "то, что ты теперь понимаешь и будешь делать иначе. Если "
            "забрать нечего — так и скажи одной строкой.")
        try:
            _brain = _slot_brain(_ceh_id, _slot)
            if _brain is None:
                raise RuntimeError(f"мозг {_slot} ещё не в слоте")
            _chat = getattr(_brain, _fn_name)
            dialog = [m for m in state["chat_history"]
                      if m.get("role") in ("user", "assistant")
                      and m.get("content")][-10:]
            vyvod = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _chat(prosba, None, dialog))
        except Exception as e:
            ui.notify(f"не осмыслилось: {e}", type="negative")
            return
        vyvod = (str(vyvod or "")).strip()
        if not vyvod:
            ui.notify("Он промолчал — ничего не записано", type="warning")
            return
        try:
            from nositel import otmetit_yarkim_slotom
            res = otmetit_yarkim_slotom(_ceh_id, _slot, vyvod[:600],
                                        otkuda="работа")
        except Exception as e:
            ui.notify(f"в память не легло: {e}", type="negative")
            return
        state["chat_history"].append({
            "role": "assistant", "agent": aid,
            "content": f"🧠 осмыслил: {vyvod}"})
        update_chat_display()
        if res.get("дописано"):
            ui.notify("🧠 легло в память как рабочее", type="positive")
        else:
            ui.notify(f"🧠 не записалось: {res.get('причина','—')}",
                      type="warning")

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
                # RAZGOVOR_PRO_SVOY_INSTRUMENT_V1: берём ту же пару,
                # что и кадр справа — у трейдера СВОЙ инструмент и
                # свой этаж. Раньше здесь была полка загрузчика, и
                # Илья на GBPUSD отвечал про EURUSD, потому что евро
                # было выбрано слева. Для не-трейдеров
                # _para_aktivnogo сама вернёт полку — им как было.
                try:
                    _s_sv, _t_sv, _chey_sv, _net_sv = _para_aktivnogo()
                    _rynok_seychas = ((_s_sv, _t_sv) if (_s_sv and _t_sv)
                                      else _aktivnyy_rynok())
                except Exception as _e_sv:
                    print(f"[РЫНОК] пара трейдера не прочиталась "
                          f"({_e_sv}) — беру полку")
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
                    # PUZYRI_V1: были голые div — клик держался на
                    # всплытии и терялся, как у тумблера. И подсветка
                    # «кто выбран» была прибита к A01, то есть к Искре,
                    # упразднённой 06.08: кабинет открывался на агенте,
                    # которого нет, оттого ни кадра, ни отчёта, ни чата.
                    for r in roster:
                        old_id = r["old_id"]
                        occupied = bool(r["resident"])
                        aktiven = (old_id == state.get("active_agent"))
                        cls = (f'avatar {"active" if aktiven else ""} '
                               f'{"" if occupied else "vacant"}')
                        style = ""
                        if occupied:
                            av = _avatar_url_for(r["resident"]["папка"], static_prefix)
                            if av:
                                style = f"background-image:url('{av}');"

                        async def _nazhali(w=old_id):
                            print(f"[ПУЗЫРЬ] нажали: {w}")
                            await switch_agent(w)

                        avatar = ui.button(on_click=_nazhali).classes(cls)
                        avatar.props("flat dense no-caps").style(style)
                        # PUZYR_PODSVETKA_V2: базовый style (аватарка
                        # фоном) запоминаем — подсветка будет дописываться
                        # к нему, а не затирать его.
                        avatar._bazovyy_style = style
                        with avatar:
                            if not occupied:
                                ui.label(old_id).style("font-size: 9px")
                        avatars_ref["elements"][old_id] = avatar
                # PROSTO_I_ROVNO_V1: строка состава. Всегда на виду, кто
                # на местах и чем работаем — чтобы не гадать по кликам и
                # не ловить пропадающие уведомления.
                sostav_ref["element"] = ui.html("").style(
                    "color:rgba(255,255,255,0.55); font-size:11px; "
                    "letter-spacing:0.04em; margin-right:14px; "
                    "white-space:nowrap; overflow:hidden; "
                    "text-overflow:ellipsis; max-width:46vw;")
                # VREMYA_GORODA_V1: часы и сессия — текстом, всегда на
                # виду. Пояс сервера город узнаёт сам у терминала, руками
                # ничего не вбивается. Сессии берутся из kalibrovka —
                # второй правды о рынке не заводим.
                vremya_ref["element"] = ui.label("").style(
                    "color:rgba(139,233,253,0.75); font-size:11px; "
                    "letter-spacing:0.05em; margin-right:14px; "
                    "white-space:nowrap;")

                def _vremya_obnovit():
                    try:
                        import vremya
                        if vremya_ref["element"]:
                            vremya_ref["element"].text = vremya.stroka()
                    except Exception:
                        pass

                _vremya_obnovit()
                ui.timer(30.0, _vremya_obnovit)

                with ui.element("div").style(
                    "margin-right:10px; background:rgba(255,255,255,0.06); "
                    "border:1px solid rgba(255,255,255,0.12); border-radius:10px;"
                ):
                    _opts = {m["id"]: f'{m["name"]} ({m["price"]})' for m in MODELS_CATALOG}
                    ui.select(_opts, value=state["model"], on_change=on_model_change) \
                        .props('dense borderless dark options-dense').style("min-width:190px;")
                svoya_model_ref: dict[str, Any] = {"element": None}

                def _svoya_model(_e=None):
                    val = (svoya_model_ref["element"].value or "").strip()
                    if not val:
                        return
                    state["model"] = val
                    llm.set_model(val)
                    ui.notify(f"модель: {val}", type="info")

                with ui.row().style("gap:2px; align-items:center; margin-right:10px;"):
                    svoya_model_ref["element"] = ui.input(
                        placeholder="своя модель с OpenRouter…").props(
                        'dense borderless dark').style(
                        "min-width:170px; color:rgba(255,255,255,0.85); "
                        "font-size:11px; background:rgba(255,255,255,0.06); "
                        "border:1px solid rgba(255,255,255,0.12); border-radius:10px; padding:2px 8px;")
                    svoya_model_ref["element"].on("keydown.enter", _svoya_model)
                    ui.button("➜", on_click=_svoya_model).props("flat dense size=sm").style(
                        "color:rgba(0,255,136,0.75);")

                ui.button("← Город", on_click=lambda: ui.navigate.to("/grondheim", new_tab=True)).props("flat").style(
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
                        # POLKA_IZ_TERMINALA_V1: живые котировки на полку
                        ui.button("ТЕРМИНАЛ", on_click=sobrat_terminal).props(
                            "flat dense size=xs").style(
                            "color:rgba(0,255,136,0.75); font-size:9px;")
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
                        # PROSTO_I_ROVNO_V1: кнопка сворачивалась в две
                        # строки и поднимала соседей — ряд разъезжался.
                        # Теперь одна строка и та же высота, что у прочих.
                        toolbar_refs["vahta_btn"] = ui.element("div").style(
                            "padding:8px 16px;border-radius:8px;font-size:12px;"
                            "font-weight:700;cursor:pointer;white-space:nowrap;"
                            "display:flex;align-items:center;flex-shrink:0;"
                            "background:rgba(255,255,255,0.03);"
                            "color:rgba(255,255,255,0.45);"
                            "border:1px solid rgba(255,255,255,0.08);")
                        with toolbar_refs["vahta_btn"]:
                            toolbar_refs["vahta_html"] = ui.html("⏱ ВАХТА")
                        toolbar_refs["vahta_btn"].on(
                            "click", lambda: _vahta_pereklyuchit())
                        # VAHTA_GORODSKAYA_V1: таймер вахты живёт при
                        # городе. Здесь только подтягиваем вид кнопки —
                        # чтобы, зайдя из другого окна, видеть правду.
                        ui.timer(3.0, _vahta_vid)
                        # TUMBLER_V1: были голые div — клик держался на
                        # всплытии события и терялся, если сверху лёг любой
                        # слой. Выглядело как «кнопка не кликается»,
                        # хотя обработчик был цел. Теперь настоящие кнопки:
                        # клик обрабатывает сама кнопка.
                        toolbar_refs["mode_real"] = ui.button(
                            "РЕАЛ", on_click=lambda: set_mode("real")
                        ).props("flat no-caps dense").style(
                            "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                            "cursor:pointer;background:rgba(0,255,136,0.15);color:#00ff88;"
                            "border:1px solid rgba(0,255,136,0.4);")
                        toolbar_refs["mode_tester"] = ui.button(
                            "ТЕСТЕР", on_click=lambda: set_mode("tester")
                        ).props("flat no-caps dense").style(
                            "padding:6px 14px;border-radius:7px;font-size:12px;font-weight:700;"
                            "cursor:pointer;background:rgba(255,255,255,0.03);"
                            "color:rgba(255,255,255,0.45);border:1px solid rgba(255,255,255,0.08);")
                        # PARA_PO_POSTU_V1: «ловить» переехало ВНИЗ, к
                        # своему полю. Раньше подпись стояла здесь, а
                        # число — после дат, и на панели читалось
                        # «ловить: отрезок: 01.02 10.03 15»: подпись от
                        # одного поля, значение от другого.
                        # PROGON_S_DATY_V1: поле «с даты». Пусто — ищем
                        # от сегодня, как было. Заполнено — искатель
                        # встаёт в этот момент истории и ищет назад.
                        toolbar_refs["ot_daty_label"] = ui.element("div").style("display:none;align-items:center;gap:5px;")
                        with toolbar_refs["ot_daty_label"]:
                            # TESTER_PULT_V2: одна подпись на обе даты
                            ui.label("отрезок:").style("color:rgba(255,255,255,0.45);font-size:11px;")
                        toolbar_refs["ot_daty_input"] = ui.element("div").style("display:none;align-items:center;")
                        with toolbar_refs["ot_daty_input"]:
                            def _on_daty_change(e):   # PROGON_S_DATY_V1
                                state["progon_ot_daty"] = (e.value or "").strip()
                            ui.input(
                                value="", placeholder="с 28.04.2026",   # DATY_PO_CHELOVECHESKI_V1
                                on_change=_on_daty_change,
                            ).props(
                                'dense outlined '
                                'input-style="color:rgba(0,204,255,0.95);'
                                'font-family:JetBrains Mono;font-size:11px;'
                                'text-align:center;padding:0 2px;"'
                            ).style("width:112px;")

                        # TESTER_PULT_V1: верхняя граница отрезка.
                        # Вдвоём с «с даты» вырезает любой кусок истории.
                        # TESTER_PULT_V2: подписи у второй даты нет —
                        # подсказка внутри поля говорит сама, а строка
                        # панели узкая и каждый ярлык стоит места.
                        toolbar_refs["po_datu_input"] = ui.element("div").style("display:none;align-items:center;")
                        with toolbar_refs["po_datu_input"]:
                            def _on_po_datu_change(e):   # TESTER_PULT_V1
                                state["progon_po_datu"] = (e.value or "").strip()
                            ui.input(
                                value="", placeholder="по 30.07.2026",  # DATY_PO_CHELOVECHESKI_V1
                                on_change=_on_po_datu_change,
                            ).props(
                                'dense outlined '
                                'input-style="color:rgba(0,204,255,0.95);'
                                'font-family:JetBrains Mono;font-size:11px;'
                                'text-align:center;padding:0 2px;"'
                            ).style("width:112px;")

                        # TESTER_PULT_V2: поля «инструмент» здесь больше
                        # нет — чем работать, говорит пост трейдера.
                        # PARA_PO_POSTU_V1: подпись «ловить» теперь тут,
                        # вплотную к своему полю.
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
                        # KNOPKA_OTCHYOTA_K_OCHISTKE_V1: отчёт — сюда же.
                        # Справа в своём ряду его перекрывали кнопки
                        # тестера, как раньше «← Брат» и надпись Биржи.
                        _otchyot_btn = ui.element("div").style(
                            "display:flex;align-items:center;"
                            "padding:6px 14px;border-radius:7px;"
                            "font-size:12px;font-weight:700;cursor:pointer;"
                            "background:rgba(99,130,255,0.08);"
                            "color:rgba(150,175,255,0.85);"
                            "border:1px solid rgba(99,130,255,0.3);")
                        _otchyot_btn.on("click", lambda: ui.navigate.to(
                            f"/otchyot/{tseh_id}", new_tab=True))
                        with _otchyot_btn:
                            ui.html("📄 ОТЧЁТ")
                    # UBRAT_NADPIS_BIRZHA_V1: надпись «БИРЖА · СОВЕТ» убрана —
                    # наезжала на кнопку ОЧИСТИТЬ, и была избыточна
                    # (страница подписана вкладками и хедером Совета).
                    # UBRAT_KNOPKU_BRAT_V1: кнопка «← Брат» убрана по
                    # слову Шефа — не использовалась и жалась к
                    # «ОЧИСТИТЬ». К Брату ходим через город.
                    # KNOPKA_OTCHYOTA_K_OCHISTKE_V1: кнопка отчёта
                    # переехала в общий ряд, к «ОЧИСТИТЬ».

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
                    # CHAT_KNOPKI_I_OSMYSLIT_V1: три маленькие иконки слева —
                    # сохранить, достать, очистить. Золото — как у Брата.
                    for _ico, _hint, _fn in (
                            ("💾", "сохранить разговор", _sohranit_chat),
                            ("📂", "достать разговор", _dostat_chat),
                            ("🧹", "очистить разговор", _ochistit_razgovor)):
                        ui.button(_ico, on_click=_fn).props("flat").tooltip(
                            _hint).style(
                            "font-size:1rem;padding:4px 8px;border-radius:9px;"
                            "min-width:0;color:rgba(201,168,76,0.9);"
                            "background:rgba(201,168,76,0.10);"
                            "border:1px solid rgba(201,168,76,0.30);")
                    input_ref["element"] = ui.input(placeholder="Сообщение Совету...").props("borderless").style("flex:1")
                    input_ref["element"].on("keydown.enter", send_message)
                    # KABINET_GRAFIK_V1: посмотреть самому / дать посмотреть
                    # STOP_I_VZGLYAD_V1: рука Шефа — вот она.
                    ui.button("👁 Взгляд",
                              on_click=lambda: (
                                  state.__setitem__("взгляд_рукой", True),
                                  pokazat_kadr())[-1]).props(
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

                # CHAT_KNOPKI_I_OSMYSLIT_V1: под аватаром, над приборами.
                # Житель сам пишет вывод по последним своим словам, и
                # вывод ложится ему в память КАК РАБОЧИЙ — иначе за
                # столом выученное у Шефа не всплывёт никогда.
                ui.button("🧠 ОСМЫСЛИТЬ", on_click=_osmyslit).props(
                    "flat no-caps").tooltip(
                    "Пусть сам напишет, что забрал из разговора — "
                    "и запомнит это как рабочее").style(
                    "margin-top:12px;width:100%;font-size:0.72rem;"
                    "letter-spacing:0.08em;padding:8px 10px;"
                    "border-radius:10px;color:rgba(201,168,76,0.9);"
                    "background:rgba(201,168,76,0.10);"
                    "border:1px solid rgba(201,168,76,0.30);")

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

# POLKA_IZ_TERMINALA_V1 - marker

# SVYAZ_S_TERMINALOM_V1 - marker

# OKNO_MOGLO_UYTI_V1 - marker

# VAHTA_GORODSKAYA_V1 - marker

# SVOYO_OKNO_V1 - marker

# PANEL_TREYDERA_V1 - marker

# PROSTO_I_ROVNO_V1 - marker

# NAZNACHENIYA_PROCH_V1 - marker

# VAHTA_ZA_POLKOY_V1 - marker

# PODPISI_POD_PUZYRKAMI_V1 - marker

# VAHTA_ZAVEDI_LYUBOY_V1 - marker

# KABINET_ZNAET_CEH_V1 - marker

# VZGLYAD_KAZHDOGO_V1 - marker

# UBRAT_CHETVERTOGO_V1 - marker

# VREMYA_V_KABINETE_V1 - marker

# ISKATEL_V1 - marker

# ODNA_KNOPKA_V1 - marker

# OTPERET_V1 - marker

# TUMBLER_V1 - marker

# OTCHYOT_PROGONA_V1 - marker

# PUZYRI_V1 - marker

# PROGON_VIDNO_V1 - marker

# TOCHKA_NE_TASHCHITSYA_V1 - marker

# PROGON_VPERYOD_V1 - marker

# KONEC_VOLNY_1_V1 - marker

# PROGON_POSLE_SLOMA_V1 - marker

# PROGON_BEZ_OKNA_V1 - marker

# SVYAZ_I_PAPKA_V1 - marker

# PROGON_S_DATY_V1 - marker

# POISK_S_DATY_V1 - marker

# PROGON_PODRYAD_V1 - marker

# PROGON_PODRYAD_V2 - marker

# KONEC_VOLNY_NE_SYEDEN_V1 - marker

# TESTER_PULT_V1 - marker

# TESTER_PULT_V2 - marker

# PARA_PO_POSTU_V1 - marker

# KABINET_ZHIVYOT_PRI_GORODE_V1 - marker

# POLKA_NE_DUSHIT_SVYAZ_V1 - marker

# PUZYR_KAK_V_AKADEMII_V1 - marker

# PUZYR_PODSVETKA_V2 - marker

# PUZYR_NE_OBRYVAETSYA_V3 - marker

# RAZGOVOR_PRO_SVOY_INSTRUMENT_V1 - marker

# PUZYR_STILEM_I_UPDATE_V4 - marker

# PUZYR_PRYAMO_V_BRAUZER_V5 - marker

# PUZYR_BEZ_GETHTMLELEMENT_V6 - marker

# POKAZAT_KADR_NE_VESHAET_SERVER_V1 - marker

# SVOYA_MODEL_POLEM_V1 - marker

# ZHIVOY_KADR_V1 - marker

# CHAT_KNOPKI_I_OSMYSLIT_V1 - marker

# VZGLYAD_PO_VYBORU_V1 - marker

# EDINYY_VYBOR_V1 - marker


def _moment_zakrytiya(data_bara: str, etazh: str) -> str:
    """Момент, когда этот бар закрылся. Не вышло посчитать — отдаём
    как есть: лучше прежнее поведение, чем сломанный курсор."""
    try:
        from datetime import timedelta
        import istoriya as _ist
        import masshtab as _m
        t0 = _ist.kak_vremya(data_bara)
        minut = _m.minut(etazh)
        if t0 is None or not minut:
            return data_bara
        return (t0 + timedelta(minutes=minut)).strftime(_ist.FORMAT)
    except Exception as _e:
        print(f"[ПРОГОН] момент закрытия не посчитался ({_e}) — "
              f"ставлю курсор как раньше")
        return data_bara

# BUDIM_NA_SVOYOM_BARE_V1 - marker

# POLKA_POMNIT_V1 - marker

# SNYAT_BAR_GORODA_V1 - marker
