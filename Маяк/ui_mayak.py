# -*- coding: utf-8 -*-
# MAYAK_KABINET_V2 — КАБИНЕТ МАЯКА · /mayak
"""
МАЯК ПРОБУЖДЕНИЯ · кабинет

СТИЛЬ ОТ БИРЖИ, как весь город: та же сетка (300 / центр / 260), то же
стекло, та же шапка с пузырьками, тот же стол — чат плюс отчёт, та же
плавающая консоль. Акцент свой — БИРЮЗОВЫЙ: «Бирюзовый луч, который
виден из любой точки Грондхейма» (паспорт локации). Так Маяк не
спутаешь с Академией и Биржей с одного взгляда.

ПУЗЫРЁК ЗДЕСЬ — НЕ АВАТАР, А РОЗЕТКА (слово Шефа). В Академии пузырёк
это парта, кто сидит. Здесь — луч: сколько связей маяк держит разом.
Гнездо всеядно: житель, пост, канал наружу, инструмент, сервис. Кто
внутри — то и рисуем: живому лицо, каналу знак.

ПОРЯДОК (слово Шефа): живые → свободные → ПОСТОЯННЫЕ В КОНЦЕ, ярче
всех, за разделителем. Слева движение, справа то, что стоит всегда.

ЧАТ — КОММУТАТОР (слово Шефа): «чат соединяет с кем на связи».
Выбрал гнездо — говоришь с тем, кто в нём:
    канал  → запрос уходит во внешний мир, находки в отчёт
    живой  → говоришь с ним; он стоит на Маяке и выносит оттуда
             СВОЙ чистый смысл, не пересказ выдачи
    пусто  → честно скажет, что соединять не с кем
Личность живого сюда не вшита — её поднимает ГОРОД/rezidenty.py из
паспорта. Кабинет только соединяет провода.

ЧЕГО ЗДЕСЬ ЧЕСТНО НЕТ: маяк не выдумывает выдачу. Нет ключа — скажет
«не горю» и вернёт пусто, вместо сочинённых ссылок.

`шесть·проверено·до·корня`
"""
import os
import sys
import json
from pathlib import Path

from nicegui import ui, app

_HERE = Path(__file__).resolve().parent      # ГОРОД/
_REPO = _HERE.parent                          # корень репо
for _p in (_REPO, _HERE, _REPO / "жители"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import gnezda                                  # noqa: E402
import mayak                                   # noqa: E402
import khranitel_mayaka                        # noqa: E402  MAYAK_KHRANITEL_V1

_LOKACII = _REPO / "GRONDHEIM_CITY" / "локации"
_KOVCHEG = _REPO / "GRONDHEIM_CITY" / "жители" / "ковчег"
_STATIC = "mayak-static"
_MOUNTED = {"bg": False}

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
PROXY_URL = os.getenv("PROXY_URL", "") or None

# MAYAK_MODEL_SEL_V1: тот же каталог, что в кабинете Брата (ui_brat.py) —
# один список моделей на весь город, не плодим второй источник правды.
MODELS_CATALOG = [
    {"id": "google/gemini-2.5-flash",          "name": "Gemini 2.5 Flash",  "price": "$0.15/$0.60"},
    {"id": "anthropic/claude-haiku-4-5",       "name": "Claude Haiku 4.5",  "price": "$1/$5"},
    {"id": "deepseek/deepseek-chat",           "name": "DeepSeek V3",       "price": "$0.14/$0.28"},
    {"id": "openai/gpt-4o-mini-2024-07-18",              "name": "GPT-4o mini",      "price": "$0,15 / $0,60"},
    {"id": "meta-llama/llama-3.3-70b-instruct","name": "Llama 3.3 70B",     "price": "$0.10/$0.32"},
    {"id": "anthropic/claude-sonnet-4-5",      "name": "Claude Sonnet 4.5", "price": "$3/$15"},
]
DEFAULT_MODEL = OPENROUTER_MODEL or MODELS_CATALOG[0]["id"]

# как рисуем род в гнезде: (знак, цвет)
ZNAKI = {
    gnezda.ROD_KANAL:      ("🛰", "rgba(0,229,222,0.95)"),
    gnezda.ROD_INSTRUMENT: ("⚙",  "rgba(201,168,76,0.95)"),
    gnezda.ROD_SERVIS:     ("☁",  "rgba(189,0,255,0.95)"),
    gnezda.ROD_ZHIVOY:     ("◉",  "rgba(80,250,123,0.95)"),
}


def _read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _znak(rod):
    return ZNAKI.get(rod, ("◈", "rgba(255,255,255,0.85)"))


def _lok() -> dict:
    try:
        return mayak.nayti_lokaciyu()
    except Exception:
        return {}


def _bg_url() -> str:
    """Фон кабинета — образ Маяка. Локацию маяк ищет сам, по приметам."""
    lok = _lok()
    dom = lok.get("путь") if lok else None
    if not dom or not Path(dom).exists():
        return ""
    if not _MOUNTED["bg"]:
        try:
            app.add_static_files("/mayak-bg", str(_LOKACII))
        except Exception:
            pass
        _MOUNTED["bg"] = True
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if (Path(dom) / ("image" + ext)).exists():
            return f"/mayak-bg/{Path(dom).name}/image{ext}"
    return ""


def _dom_zhitelya(imya: str, klyuch: str = ""):
    """Дом жителя. Сперва по имени папки, потом сканом по ID."""
    if imya:
        d = _KOVCHEG / imya
        if (d / "passport.json").exists():
            return d
    if klyuch and _KOVCHEG.exists():
        for d in _KOVCHEG.iterdir():
            p = _read_json(d / "passport.json", {}) or {}
            if p.get("ID_Object") == klyuch:
                return d
    return None


def _avatar_url(dom) -> str:
    if not dom or not dom.exists():
        return ""
    p = _read_json(dom / "passport.json", {}) or {}
    av = p.get("avatar", "")
    if av and (dom / av).exists():
        return f"/{_STATIC}/{dom.name}/{av}"
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if (dom / ("avatar" + ext)).exists():
            return f"/{_STATIC}/{dom.name}/avatar{ext}"
    return ""


MAYAK_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

:root{ --glass:rgba(13,17,23,0.60); --stroke:rgba(255,255,255,0.10);
       --luch:#00e5de; }

html, body{ height:100%; margin:0; }
body{ width:100vw; height:100vh; overflow:hidden !important;
      background:transparent !important;
      font-family:Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }

#mbg{ position:fixed; inset:0; z-index:-1; background-size:cover;
      background-position:center; background-color:#050510; }
#mbg::after{ content:''; position:absolute; inset:0;
      background:radial-gradient(circle at 50% 15%, rgba(0,229,222,0.13), transparent 55%),
                 rgba(5,5,16,0.70); }

.app-container{ position:fixed; inset:0; display:grid;
  width:100vw; height:100vh;
  grid-template-columns:300px 1fr 260px;
  grid-template-rows:80px 1fr;
  grid-template-areas:"header header header" "left stage right";
  gap:20px; padding:20px; box-sizing:border-box; }

.area-header{ grid-area:header; }
.area-left{ grid-area:left; min-height:0; }
.area-stage{ grid-area:stage; min-height:0; position:relative; overflow:hidden; }
.area-right{ grid-area:right; min-height:0; }

.glass{ background:var(--glass); border:1px solid var(--stroke);
  border-radius:20px; backdrop-filter:blur(16px);
  box-shadow:0 20px 60px rgba(0,0,0,0.45); min-height:0; }

.squad-deck{ height:100%; display:flex; align-items:center;
  padding:10px 16px; gap:8px; overflow-x:auto; }

/* ── ГНЕЗДО ── */
.gn{ width:46px; height:46px; border-radius:999px; flex:0 0 auto;
  display:grid; place-items:center; cursor:pointer; position:relative;
  border:2px solid rgba(255,255,255,0.14);
  background:rgba(255,255,255,0.05); background-size:cover;
  background-position:center 18%;
  color:rgba(255,255,255,0.9); font-weight:800; font-size:16px;
  transition:all .25s ease; }
.gn:hover{ transform:scale(1.07); }

.gn.pusto{ border-style:dashed; opacity:.34; cursor:default;
  font-size:11px; color:rgba(255,255,255,0.5); }
.gn.pusto:hover{ transform:none; }

/* ПОСТОЯННЫЕ — ЯРЧЕ ВСЕХ, слово Шефа */
.gn.stoit{ opacity:1;
  border-color:rgba(0,229,222,0.55);
  box-shadow:0 0 24px rgba(0,229,222,0.50), 0 0 0 1px rgba(255,255,255,0.10) inset;
  filter:saturate(1.3) brightness(1.15); }
.gn.stoit::after{ content:''; position:absolute; right:-1px; bottom:-1px;
  width:11px; height:11px; border-radius:999px;
  background:var(--luch); border:2px solid rgba(5,5,16,0.92);
  box-shadow:0 0 10px rgba(0,229,222,0.9); }

.gn.aktiv{ border-color:rgba(0,229,222,0.9);
  box-shadow:0 0 0 3px rgba(0,229,222,0.25) inset, 0 0 34px rgba(0,229,222,0.6); }

.razdel{ width:1px; height:32px; flex:0 0 auto; margin:0 6px;
  background:linear-gradient(transparent, rgba(0,229,222,0.45), transparent); }

.left-col, .right-col{ height:100%; display:flex; flex-direction:column;
  gap:12px; min-height:0; }
.panel-title{ padding:12px 16px; color:rgba(255,255,255,0.92); font-weight:900;
  letter-spacing:.12em; text-transform:uppercase; font-size:11px;
  border-bottom:1px solid rgba(255,255,255,0.08); }

.stage-monitor{ height:100%; display:flex; flex-direction:column; overflow:hidden; }
.stage-toolbar{ height:60px; display:flex; align-items:center;
  justify-content:space-between; padding:0 14px;
  border-bottom:1px solid rgba(255,255,255,0.08); flex-shrink:0;
  background:rgba(13,17,23,0.95); backdrop-filter:blur(16px); z-index:10; }
.stage-content{ flex:1; min-height:0; overflow:hidden; padding:18px; padding-bottom:130px; }

.split-view{ height:100%; display:flex; gap:18px; min-height:0; overflow:hidden; }
.chat-log, .viewer{ flex:1; min-height:0; min-width:0; border-radius:18px;
  border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03);
  overflow-y:auto; overflow-x:hidden; padding:14px;
  font-family:monospace; font-size:13px; color:rgba(255,255,255,0.86);
  white-space:pre-wrap; word-wrap:break-word; word-break:break-word; }
.viewer{ border-color:rgba(0,229,222,0.30); }

.floating-console{ position:absolute; left:50%; bottom:20px;
  transform:translateX(-50%); width:min(820px, calc(100% - 80px)); z-index:50;
  display:flex; align-items:center; gap:8px; padding:10px 12px;
  border-radius:50px; background:rgba(13,17,23,0.85);
  border:1px solid rgba(255,255,255,0.15); backdrop-filter:blur(20px);
  box-shadow:0 10px 40px rgba(0,0,0,0.5); }
.floating-console input{ width:100%; border-radius:40px;
  border:1px solid rgba(255,255,255,0.10); background:rgba(255,255,255,0.06);
  padding:12px 16px; color:rgba(255,255,255,0.92); outline:none;
  font-family:monospace; }
.send-button{ border-radius:40px !important;
  border:2px solid rgba(0,229,222,0.55) !important;
  background:linear-gradient(135deg, rgba(0,229,222,0.30), rgba(0,140,200,0.25)) !important;
  color:rgba(255,255,255,0.98) !important; font-weight:900 !important;
  padding:12px 24px !important; cursor:pointer !important; }

.chat-msg-user{ background:rgba(0,229,222,0.10);
  border-left:3px solid rgba(0,229,222,0.6); padding:8px 12px;
  margin:8px 0; border-radius:0 8px 8px 0; }
.chat-msg-a{ background:rgba(80,250,123,0.08);
  border-left:3px solid rgba(80,250,123,0.6); padding:8px 12px;
  margin:8px 0; border-radius:0 8px 8px 0; }
.chat-msg-system{ color:rgba(255,255,255,0.5); font-style:italic; padding:4px 0; }

.mbtn{ padding:6px 13px; border-radius:8px; font-size:11px; font-weight:700;
  cursor:pointer; display:flex; align-items:center;
  background:rgba(255,255,255,0.03); color:rgba(255,255,255,0.6);
  border:1px solid rgba(255,255,255,0.10); }
.mbtn:hover{ color:rgba(255,255,255,0.9); border-color:rgba(0,229,222,0.35); }

/* MAYAK_MODEL_SEL_V1 — калька .brat-model-sel из ui_brat.py, бирюзовый акцент */
.mmodel-sel .q-field__control{ background:rgba(255,255,255,0.06)!important;
  border:1px solid rgba(0,229,222,0.20)!important; border-radius:10px!important; }

.nicegui-content{ overflow:hidden !important; height:100% !important; }
.area-stage{ overflow:hidden !important; }
.area-stage > *{ overflow:hidden !important; min-height:0 !important; max-height:100% !important; }
.stage-monitor{ overflow:hidden !important; height:100% !important; }
.stage-monitor > *{ min-height:0 !important; }
.stage-content{ flex:1 1 0 !important; min-height:0 !important;
  overflow:hidden !important; max-height:calc(100% - 60px) !important; }
.stage-content > *{ min-height:0 !important; max-height:100% !important; overflow:hidden !important; }
.split-view{ height:100% !important; min-height:0 !important; overflow:hidden !important; }
.split-view > *{ min-height:0 !important; overflow:hidden !important; }
.chat-log, .viewer{ flex:1 1 0 !important; min-height:0 !important;
  max-height:100% !important; overflow-y:auto !important; overflow-x:hidden !important; }
"""


def page_mayak() -> None:
    """Кабинет Маяка Пробуждения."""

    # уборка погасших и самостоятельный канал — при открытии, один раз
    try:
        gnezda.pribrat()
        gnezda.zavesti_kanal_provaydera()
    except Exception:
        pass

    _gn = gnezda.spisok()
    _pervoe = next((g["номер"] for g in _gn if g["занято"]), 1)

    state = {"гнездо": _pervoe, "чат": [], "смыслы": [], "модель": DEFAULT_MODEL,
             "хранитель": False}   # MAYAK_KHRANITEL_V1: чат идёт к Хранителю
    refs = {"чат": None, "отчёт": None, "ввод": None,
            "лево": None, "право": None, "шапка": None}

    def on_model_change(e):
        state["модель"] = e.value

    ui.add_head_html(f"<style>{MAYAK_CSS}</style>")
    _bg = _bg_url()
    if _bg:
        ui.add_head_html(f"<style>#mbg{{background-image:url('{_bg}');}}</style>")
    ui.html('<div id="mbg"></div>')

    # ── чат и отчёт ────────────────────────────────────────
    def update_chat():
        if not refs["чат"]:
            return
        refs["чат"].clear()
        with refs["чат"]:
            if not state["чат"]:
                ui.html('<div class="chat-msg-system">SYSTEM: Маяк на связи. '
                        'Выбери гнездо наверху — чат соединит с тем, кто в нём.'
                        '</div>')
                return
            for m in state["чат"]:
                if m.get("кто") == "Шеф":
                    ui.html(f'<div class="chat-msg-user"><b>ШЕФ:</b> '
                            f'{m.get("текст","")}</div>')
                else:
                    ui.html(f'<div class="chat-msg-a"><b>{m.get("кто","МАЯК")}:</b> '
                            f'{m.get("текст","")}</div>')

    def update_otchet(md: str):
        if not refs["отчёт"]:
            return
        refs["отчёт"].clear()
        with refs["отчёт"]:
            ui.markdown(md)

    # ── шапка: гнёзда в нужном порядке ─────────────────────
    def update_shapka():
        if not refs["шапка"]:
            return
        refs["шапка"].clear()
        with refs["шапка"]:
            byl_razdel = False
            for g in gnezda.po_poryadku():
                n = g["номер"]
                # разделитель перед блоком постоянных
                if g["занято"] and g["постоянно"] and not byl_razdel:
                    ui.element("div").classes("razdel")
                    byl_razdel = True

                cls = "gn"
                if not g["занято"]:
                    cls += " pusto"
                elif g["постоянно"]:
                    cls += " stoit"
                if n == state["гнездо"]:
                    cls += " aktiv"

                b = ui.element("div").classes(cls)
                if g["занято"]:
                    hint = f'{g["имя"]} · {g["род"]}'
                    if g["что"]:
                        hint += f' — {g["что"]}'
                else:
                    hint = f"гнездо {n} · свободно"
                b.props(f'title="{hint}"')
                b.on("click", lambda e, k=n: vybrat(k))

                dom = None
                if g["занято"] and g["род"] == gnezda.ROD_ZHIVOY:
                    dom = _dom_zhitelya(g["имя"], g["ключ"])
                    if dom:
                        try:
                            app.add_static_files(f"/{_STATIC}/{dom.name}", str(dom))
                        except Exception:
                            pass
                        av = _avatar_url(dom)
                        if av:
                            b.style(f"background-image:url('{av}');")
                with b:
                    if not g["занято"]:
                        ui.label(str(n))
                    elif not (g["род"] == gnezda.ROD_ZHIVOY and dom):
                        zn, cv = _znak(g["род"])
                        ui.html(f'<span style="color:{cv};">{zn}</span>')

            # MAYAK_KHRANITEL_V1: пузырёк Хранителя Маяка — ОТДЕЛЬНО от
            # гнёзд, за своим разделителем. Гнездо — это луч (сеанс),
            # а пост стоит всегда, даже когда все лучи погашены. Смешивать
            # их в один ряд значило бы соврать про природу обоих.
            _est_khr = khranitel_mayaka.est_khranitel()
            _imya_khr = khranitel_mayaka.imya_na_postu()
            ui.element("div").classes("razdel")
            _cls_khr = "gn" if _est_khr else "gn pusto"
            if state.get("хранитель"):
                _cls_khr += " aktiv"
            _bk = ui.element("div").classes(_cls_khr)
            _bk.props('title="{}"'.format(
                f"{_imya_khr} · Хранитель Маяка" if _est_khr
                else "Хранитель Маяка · пост свободен"))
            _bk.on("click", lambda: toggle_khranitel())
            _dom_khr = khranitel_mayaka.dom_na_postu() if _est_khr else None
            if _dom_khr:
                try:
                    app.add_static_files(f"/{_STATIC}/{_dom_khr.name}", str(_dom_khr))
                except Exception:
                    pass
                _av_khr = _avatar_url(_dom_khr)
                if _av_khr:
                    _bk.style(f"background-image:url('{_av_khr}');")
            with _bk:
                if not _dom_khr:
                    ui.html('<span style="color:rgba(0,229,222,0.85);">✎</span>')

    # ── левая: кто на связи ────────────────────────────────
    def update_levo():
        if not refs["лево"]:
            return
        refs["лево"].clear()
        with refs["лево"]:
            zan = [g for g in gnezda.po_poryadku() if g["занято"]]
            if not zan:
                ui.html('<div style="color:rgba(255,255,255,0.35);font-size:11px;'
                        'padding:10px 14px;">Ни одного разъёма — маяк один</div>')
                return
            for g in zan:
                zn, cv = _znak(g["род"])
                srok = ("постоянно" if g["постоянно"]
                        else f"сеанс · тихо {g['тихо_минут']} мин")
                ui.html(f'''
                  <div style="padding:8px 11px;margin:4px 0;border-radius:9px;
                              background:rgba(255,255,255,0.02);
                              border:1px solid rgba(255,255,255,0.07);
                              font-family:'JetBrains Mono',monospace;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                      <span style="color:{cv};font-size:11px;font-weight:700;">
                        {zn} {g['имя']}</span>
                      <span style="color:rgba(255,255,255,0.35);font-size:9px;">
                        №{g['номер']}</span>
                    </div>
                    <div style="color:rgba(255,255,255,0.5);font-size:9px;margin-top:3px;">
                      {g['что'] or g['род']} · {srok}</div>
                  </div>''')

    # ── правая: приборы ────────────────────────────────────
    def update_pravo():
        if not refs["право"]:
            return
        s = mayak.sostoyanie()
        sv = gnezda.svodka()
        refs["право"].clear()
        with refs["право"]:
            cvet = "var(--luch)" if s["горит"] else "rgba(255,80,80,0.7)"
            slovo = "ГОРИТ" if s["горит"] else "ТЁМНЫЙ"
            ui.html(f'''
              <div style="padding:14px 16px;font-family:'JetBrains Mono',monospace;">
                <div style="font-size:1.45rem;font-weight:900;color:{cvet};
                            letter-spacing:0.08em;">🔦 {slovo}</div>
                <div style="font-size:0.66rem;color:rgba(255,255,255,0.5);
                            margin-top:6px;line-height:1.8;">
                  провайдер: <b style="color:rgba(255,255,255,0.8);">
                    {s['провайдер'] or '—'}</b><br>
                  место: <b style="color:rgba(255,255,255,0.8);">
                    {s['локация'] or 'не найдено'}</b><br>
                  на карте: <b style="color:rgba(255,255,255,0.8);">
                    {'да' if s['на_карте'] else 'нет'}</b>
                </div>
                <div style="margin-top:12px;padding-top:10px;
                            border-top:1px solid rgba(255,255,255,0.08);
                            font-size:0.66rem;color:rgba(255,255,255,0.5);line-height:1.8;">
                  лучей горит: <b style="color:var(--luch);">{sv['горит']}</b>
                    из {sv['всего']}<br>
                  постоянных: {sv['постоянных']} · живых: {sv['живых']}
                </div>
              </div>''')
            if not s["горит"]:
                ui.html('<div style="padding:0 16px 14px 16px;font-size:0.63rem;'
                        'color:rgba(255,160,60,0.75);line-height:1.5;">'
                        'Нет TAVILY_KEY в .env — наружу не выйти. '
                        'Врать про находки не буду.</div>')

    def osvezhit():
        update_shapka()
        update_levo()
        update_pravo()

    # ── выбор гнезда ───────────────────────────────────────
    def toggle_khranitel():
        """MAYAK_KHRANITEL_V1: включить/выключить разговор с Хранителем.
        Пока включён — чат идёт к нему, а не в гнездо."""
        if not khranitel_mayaka.est_khranitel():
            ui.notify("Пост Хранителя Маяка свободен — сажать некого",
                      color="warning")
            return
        state["хранитель"] = not state.get("хранитель")
        update_shapka()
        if state["хранитель"]:
            imya = khranitel_mayaka.imya_na_postu()
            update_otchet(
                f"# ✎ {imya} · Хранитель Маяка\n\n"
                f"{khranitel_mayaka.svodka_tekstom()}\n\n"
                f"---\n\n*Спроси про связи, про учёт народа, "
                f"про города на связи.*")
        else:
            vybrat(state["гнездо"])

    def vybrat(n: int):
        state["гнездо"] = n
        state["хранитель"] = False   # MAYAK_KHRANITEL_V1: выбрал луч — вышел с поста
        g = gnezda.gnezdo(n)
        update_shapka()
        if not g.get("занято"):
            update_otchet(f"# Гнездо {n}\n\n*Свободно.*\n\nВоткнуть сюда можно "
                          f"кого угодно — жителя, канал, инструмент, сервис. "
                          f"Гнездо не спрашивает породу.")
            return
        zn, _ = _znak(g["род"])
        srok = ("держится постоянно" if g["постоянно"]
                else f"сеанс, тихо {g['тихо_минут']} мин из {gnezda.SEANS_MINUT}")
        s_kem = ("внешним миром" if g["род"] == gnezda.ROD_KANAL
                 else f"{g['имя']}")
        update_otchet(
            f"# {zn} {g['имя']}\n\n"
            f"**Род:** {g['род']} · {srok}\n\n"
            f"**Гнездо:** {g['номер']}\n\n"
            f"**Чем занят:** {g['что'] or '—'}\n\n"
            f"---\n\n*Пиши в консоль — соединю с {s_kem}.*"
        )

    def pogasit():
        skolko = gnezda.pogasit_zhivyh()
        osvezhit()
        ui.notify(f"погасил живых: {skolko} · каналы не тронул",
                  color="info" if skolko else "warning")

    # ── ГОЛОС ──────────────────────────────────────────────
    async def _llm(sistema: str, vopros: str) -> str:
        if not OPENROUTER_KEY:
            return "⚠ OPENROUTER_API_KEY не задан — голоса нет."
        import httpx
        msgs = [{"role": "system", "content": sistema}]
        for m in state["чат"][-8:]:
            msgs.append({"role": "user" if m.get("кто") == "Шеф" else "assistant",
                         "content": m.get("текст", "")})
        msgs.append({"role": "user", "content": vopros})
        try:
            async with httpx.AsyncClient(timeout=120, proxy=PROXY_URL) as c:
                r = await c.post("https://openrouter.ai/api/v1/chat/completions",
                                 headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                                          "Content-Type": "application/json"},
                                 json={"model": state.get("модель", DEFAULT_MODEL), "messages": msgs})
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"⚠ не отозвался: {e}"

    async def _cherez_kanal(g, vopros):
        """Гнездо-канал: запрос уходит наружу, находки в отчёт."""
        if not mayak.gorit():
            return g["имя"], "Не горю — нет TAVILY_KEY в .env. Ссылки выдумывать не буду."
        rez = await mayak.poisk(vopros, 5)
        try:
            mayak.zapisat_vizit("Шеф", vopros, rez.get("ok", False))
            gnezda.podderzhat(g["ключ"], g["имя"], f"искали: {vopros[:40]}")
        except Exception:
            pass
        if not rez.get("ok"):
            return g["имя"], f"молчит: {rez.get('ошибка','')}"

        md = [f"# 🔦 Из внешнего мира", "", f"**Запрос:** {vopros}", ""]
        if rez.get("ответ"):
            md += [rez["ответ"], ""]
        md.append("---")
        for i, s in enumerate(rez.get("источники", []), 1):
            md.append(f"**[{i}] {s['название']}**\n\n{s['url']}\n\n{s['кусок'][:400]}\n")
        if not rez.get("источники"):
            md.append("*Источников не пришло.*")
        update_otchet("\n".join(md))

        otvet = rez.get("ответ") or "ответа нет, но источники есть"
        n = len(rez.get("источники", []))
        return g["имя"], f"{otvet}\n\n(источников: {n} — смотри отчёт справа)"

    async def _cherez_zhivogo(g, vopros):
        """Гнездо-живой: он стоит на Маяке и выносит СВОЙ чистый смысл."""
        try:
            import rezidenty
        except ImportError:
            return "СИСТЕМА", "модуль резидентов не поднялся"

        dom = _dom_zhitelya(g["имя"], g["ключ"])
        if dom is None:
            return "СИСТЕМА", (f"«{g['имя']}» в гнезде есть, а дома в ковчеге нет — "
                              f"это пост или служба, живого голоса у неё нет.")
        p = _read_json(dom / "passport.json", {}) or {}

        naydeno = "(маяк тёмный — наружу не выходили)"
        if mayak.gorit():
            rez = await mayak.poisk(vopros, 4)
            naydeno = mayak.dlya_promta(rez)
            try:
                mayak.zapisat_vizit(g["имя"], vopros, rez.get("ok", False))
            except Exception:
                pass

        promt = (rezidenty.sobrat_dushu(p) + "\n"
                 + mayak.promt_stoyashchemu(g["имя"], vopros, naydeno))
        otvet = await _llm(promt, vopros)

        smysl = mayak.vydelit_chistyy_smysl(otvet)
        if smysl:
            state["смыслы"].append({"кто": g["имя"], "смысл": smysl})
            update_otchet(f"# ✦ Чистый смысл\n\n**{g['имя']}** принёс(ла) с Маяка:\n\n"
                          f"> {smysl}\n\n---\n\n**Искали:** {vopros}\n\n"
                          f"*Это его собственный вывод, не пересказ выдачи.*")
        try:
            gnezda.podderzhat(g["ключ"], g["имя"], f"искал(а): {vopros[:40]}")
        except Exception:
            pass
        return g["имя"], otvet

    async def sprosit():
        inp = refs["ввод"]
        if not inp:
            return
        vopros = (inp.value or "").strip()
        if not vopros:
            return
        inp.value = ""
        state["чат"].append({"кто": "Шеф", "текст": vopros})
        update_chat()

        # MAYAK_KHRANITEL_V1: Хранитель на посту перехватывает разговор —
        # он не в гнезде, он ЗА пультом. Тот же приём, что у Хранителя
        # Архива в ui_arkhiv.py.
        if state.get("хранитель"):
            _imya_khr = khranitel_mayaka.imya_na_postu() or "ХРАНИТЕЛЬ"
            state["чат"].append({"кто": _imya_khr, "текст": "…смотрит журнал"})
            update_chat()
            _ist = [{"role": "user" if m.get("кто") == "Шеф" else "assistant",
                     "content": m.get("текст", "")} for m in state["чат"][:-2]]
            try:
                _otv = await khranitel_mayaka.sprosit(
                    vopros, _ist, "Шеф", model=state.get("модель"))
            except Exception as e:
                _otv = f"⚠ сорвалось: {e}"
            state["чат"].pop()
            state["чат"].append({"кто": _imya_khr, "текст": _otv})
            update_chat()
            update_otchet(f"# ✎ {_imya_khr} · Хранитель Маяка\n\n"
                          f"{khranitel_mayaka.svodka_tekstom()}")
            return

        g = gnezda.gnezdo(state["гнездо"])
        if not g.get("занято"):
            state["чат"].append({"кто": "МАЯК", "текст":
                                 f"Гнездо {state['гнездо']} свободно — "
                                 f"соединять не с кем. Выбери занятое."})
            update_chat()
            return

        state["чат"].append({"кто": g["имя"], "текст": "…луч пошёл"})
        update_chat()
        try:
            if g["род"] == gnezda.ROD_KANAL:
                kto, otvet = await _cherez_kanal(g, vopros)
            else:
                kto, otvet = await _cherez_zhivogo(g, vopros)
        except Exception as e:
            kto, otvet = "СИСТЕМА", f"⚠ сорвалось: {e}"
        state["чат"].pop()
        state["чат"].append({"кто": kto, "текст": otvet})
        update_chat()
        osvezhit()

    # ═══ LAYOUT ═══════════════════════════════════════════
    with ui.element("div").classes("app-container"):

        with ui.element("div").classes("area-header"):
            with ui.element("div").classes("glass squad-deck"):
                refs["шапка"] = ui.element("div").style(
                    "display:flex;align-items:center;gap:8px;flex:1;overflow-x:auto;")
                update_shapka()
                with ui.row().style("gap:6px;align-items:center;"):
                    with ui.element("div").classes("mmodel-sel").style("margin-right:6px;"):
                        _opts = {m["id"]: f'{m["name"]} ({m["price"]})' for m in MODELS_CATALOG}
                        ui.select(_opts, value=state["модель"], on_change=on_model_change) \
                            .props('dense borderless dark options-dense').style("min-width:180px;")
                    for podpis, deystvie in (
                        ("✕ ГАСИТЬ", pogasit),
                        ("🏙 ГОРОД", lambda: ui.navigate.to("/grondheim")),
                        ("← БРАТ", lambda: ui.navigate.to("/brat")),
                    ):
                        b = ui.element("div").classes("mbtn")
                        b.on("click", deystvie)
                        with b:
                            ui.html(podpis)

        with ui.element("div").classes("area-left"):
            with ui.element("div").classes("left-col"):
                with ui.element("div").classes("glass").style(
                        "flex-shrink:0;overflow:hidden;"):
                    ui.html('<div class="panel-title">НА СВЯЗИ</div>')
                    refs["лево"] = ui.element("div").style(
                        "padding:8px 10px;max-height:430px;overflow-y:auto;")
                    update_levo()
                ui.html('<div style="padding:10px 14px;font-size:9px;'
                        'color:rgba(255,255,255,0.28);line-height:1.6;">'
                        'каналы горят постоянно · живые гаснут, '
                        f'если молчат {gnezda.SEANS_MINUT} мин</div>')

        with ui.element("div").classes("area-stage"):
            with ui.element("div").classes("glass stage-monitor").style(
                    "height:100%;overflow:hidden;"):
                with ui.element("div").classes("stage-toolbar"):
                    ui.html('<div style="color:rgba(255,255,255,0.55);font-size:11px;'
                            'letter-spacing:.14em;font-weight:900;">'
                            '🔦 МАЯК ПРОБУЖДЕНИЯ</div>')
                    ui.html('<div style="color:rgba(255,255,255,0.32);font-size:10px;">'
                            'чат соединяет с выбранным гнездом</div>')

                with ui.element("div").classes("stage-content"):
                    with ui.element("div").classes("split-view"):
                        refs["чат"] = ui.element("div").classes("chat-log")
                        refs["отчёт"] = ui.element("div").classes("viewer")

                with ui.element("div").classes("floating-console"):
                    refs["ввод"] = ui.input(placeholder="Запрос в выбранное гнездо...").props(
                        "borderless").style("flex:1")
                    refs["ввод"].on("keydown.enter", sprosit)
                    ui.button("SEND", on_click=sprosit).classes("send-button")

        with ui.element("div").classes("area-right"):
            with ui.element("div").classes("right-col"):
                with ui.element("div").classes("glass").style(
                        "flex-shrink:0;overflow:hidden;"):
                    refs["право"] = ui.element("div")
                    update_pravo()

    update_chat()
    vybrat(state["гнездо"])


if __name__ in {"__main__", "__mp_main__"}:
    @ui.page("/mayak")
    def _p():
        page_mayak()
    ui.run(title="Маяк · Грондхейм", port=8106, reload=False)

# MAYAK_KABINET_V2 — маркер идемпотентности
