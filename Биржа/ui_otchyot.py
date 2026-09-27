# -*- coding: utf-8 -*-
# UI_OTCHYOT_V1
"""
СТРАНИЦА ОТЧЁТА · каждый кадр со своим разбором

ЗАЧЕМ. Прогон писал итог в консоль и складывал кадры по папкам. Ни
туда, ни туда никто не пойдёт: «в терминале неудобно — никто там
смотреть не будет, и в папках в репе искать тоже никто не будет»
(слово Шефа 11.09).

А смотреть надо: прогон и делается ради того, чтобы глазами увидеть,
где трейдер был прав, а где выдумал условие.

ЧТО ЭТО. Лента по местам, сверху вниз. На каждое место карточка:
слева кадр ТОГО САМОГО бара, справа — когда, что разбудило, что он
решил и его слова целиком, не обрезанные.

Сверху — итог: мест, входов, ведения, отказов, молчаний. И выбор
прогона: последний открывается сам, прошлые — из списка.

ОТКУДА БЕРЁТ. Из `места.jsonl`, который отчёт уже пишет, и из
подпапки `кадры`. Ничего не пересчитывает и ничего не меняет:
страница только показывает.

    /otchyot                  — последний прогон торгового цеха
    /otchyot/{ceh}            — последний прогон этого цеха
    /otchyot/{ceh}/{папка}    — конкретный прогон

`шесть·проверено·до·корня`
"""
import json
from pathlib import Path

from nicegui import app, ui

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_CEHA = _REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха"

# кадры отдаём как статику — иначе браузер их не покажет
try:
    if _CEHA.exists():
        app.add_static_files("/otchyot-kadry", str(_CEHA))
except Exception as _e:
    print(f"[ОТЧЁТ] статика кадров не поднялась: {_e}")

FON = "#0d1117"
RAMKA = "1px solid rgba(255,255,255,0.10)"


def _progony(ceh: str) -> list:
    """Папки прогонов, свежие первыми."""
    p = _CEHA / ceh / "прогоны"
    if not p.exists():
        return []
    return sorted((d for d in p.iterdir() if d.is_dir()),
                  key=lambda d: d.name, reverse=True)


def _mesta(papka: Path) -> list:
    f = papka / "места.jsonl"
    if not f.exists():
        return []
    out = []
    for s in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = s.strip()
        if not s:
            continue
        try:
            out.append(json.loads(s))
        except Exception:
            continue
    return out


# ── OTCHYOT_PRAVDU_I_R_V1: результат сделки числом ──
# Город считает pnl_r при каждом закрытии и кладёт в журнал
# trading_pnl.jsonl. Отчёт туда не заглядывал — оттого в нём был
# один текст и ни одного показателя.

_ZHURNAL: dict = {}
# KRAY_I_SHAPKA_V1: окно времени открытого прогона — [с, по).
# Закрытия берём только из него, чтобы не подхватить чужой прогон.
_OKNO: list = [None, None]


def _zhurnal_zakrytiy() -> dict:
    """Закрытия по цене входа: {цена: запись}. Читается один раз."""
    if _ZHURNAL:
        return _ZHURNAL
    try:
        import json as _js
        from hooks import PNL_PATH
        p = Path(PNL_PATH)
        if not p.exists():
            _ZHURNAL["_"] = None
            return _ZHURNAL
        with open(p, encoding="utf-8") as f:
            for stroka in f:
                stroka = stroka.strip()
                if not stroka:
                    continue
                try:
                    z = _js.loads(stroka)
                except Exception:
                    continue
                # KRAY_I_SHAPKA_V1: только закрытия этого прогона
                if _OKNO[0] is not None:
                    try:
                        from datetime import datetime as _dtz
                        _tsz = _dtz.fromisoformat(
                            str(z.get("ts") or "")[:19])
                    except Exception:
                        continue
                    if _tsz < _OKNO[0] or (_OKNO[1] is not None
                                           and _tsz >= _OKNO[1]):
                        continue
                vh = z.get("entry")
                if isinstance(vh, (int, float)):
                    _ZHURNAL[round(float(vh), 5)] = z
    except Exception as e:
        print(f"[ОТЧЁТ] журнал закрытий не прочитался: {e}")
        _ZHURNAL["_"] = None
    return _ZHURNAL


ПО_РУССКИ_ЗАКРЫТИЕ = {"STOP_LOSS": "стоп", "EXIT_BELL": "колокол",
                      "MANUAL_CLOSE": "закрыла сама"}


def _itog_mesta(m: dict):
    """(R числом или None, словами) для места-входа."""
    c = m.get("цена_входа")
    if not isinstance(c, (int, float)):
        return None, ""
    z = _zhurnal_zakrytiy().get(round(float(c), 5))
    if not z:
        # ZAYAVKA_ZHDYOT_BARY_V1: было «в работе». А у ОТМЕНЁННОЙ
        # заявки закрытия нет вовсе — она не открывалась, — и под
        # «в работе» прятались отменённые. Отличить по журналу
        # закрытий нельзя: отмена туда не пишется.
        return None, "не сработала или ещё открыта"
    r = z.get("pnl_r")
    chem = ПО_РУССКИ_ЗАКРЫТИЕ.get(str(z.get("close_reason")), "?")
    if isinstance(r, (int, float)):
        return float(r), f"{float(r):+.2f}R · {chem}"
    return None, f"R не посчитан · {chem}"


def _chto_sdelal(m: dict) -> tuple:
    """(метка, цвет) — вошёл, ведёт, отказался или промолчал."""
    d = str(m.get("действие") or "").upper()
    v = str(m.get("вердикт") or "").upper()
    # OTCHYOT_PRAVDU_I_R_V1: ДЕЙСТВИЕ СМОТРИМ ПЕРВЫМ. Раньше
    # вердикт стоял раньше — а APPROVED город ставит на ЛЮБОЙ
    # принятый приказ, и HOLD с MOVE_STOP подписывались как
    # «ВОШЁЛ». Одна сделка давала три строки «ВОШЁЛ @ …», и
    # выходило, будто открыт новый вход при незакрытом старом.
    if d in ("HOLD", "MOVE_STOP", "ADD", "CLOSE"):
        return {"HOLD": "ДЕРЖУ", "MOVE_STOP": "СТОП ПЕРЕНЁС",
                "ADD": "ДОЛИЛ", "CLOSE": "ЗАКРЫЛ"}[d], "#4d9bff"
    if d == "WAIT":
        return "ОТКАЗ", "#ffb454"
    if d == "ENTER" or v in ("APPROVED", "ENTER", "OK"):
        c = m.get("цена_входа")
        s = m.get("стоп_входа")
        hvost = (f" @ {c}" if c else "") + (f", стоп {s}" if s else "")
        return f"ВОШЁЛ{hvost}", "#3ddc6b"
    if d in ("HOLD", "MOVE_STOP", "ADD", "CLOSE"):
        return {"HOLD": "ДЕРЖУ", "MOVE_STOP": "СТОП ПЕРЕНЁС",
                "ADD": "ДОЛИЛ", "CLOSE": "ЗАКРЫЛ"}[d], "#4d9bff"
    if d == "WAIT" or v in ("REJECTED", "WAIT"):
        return "ОТКАЗ", "#ffb454"
    return "ПОДУМАЛ, приказа не было", "#ff5c5c"


def _shapka(ceh: str, papka: Path, mesta: list):
    schet = {"ВОШЁЛ": 0, "ВЕДЕНИЕ": 0, "ОТКАЗ": 0, "БЕЗ ПРИКАЗА": 0}
    for m in mesta:
        metka, _ = _chto_sdelal(m)
        if metka.startswith("ВОШЁЛ"):
            schet["ВОШЁЛ"] += 1
        elif metka in ("ДЕРЖУ", "СТОП ПЕРЕНЁС", "ДОЛИЛ", "ЗАКРЫЛ"):
            schet["ВЕДЕНИЕ"] += 1
        elif metka == "ОТКАЗ":
            schet["ОТКАЗ"] += 1
        else:
            schet["БЕЗ ПРИКАЗА"] += 1

    with ui.element("div").style(
        f"background:{FON}; border:{RAMKA}; border-radius:14px; "
        f"padding:16px 20px; margin-bottom:18px;"
    ):
        with ui.row().style("align-items:baseline; gap:14px; width:100%;"):
            ui.html('<span style="color:rgba(255,255,255,0.9); '
                    'font-weight:700; letter-spacing:0.08em;">'
                    'ОТЧЁТ ПРОГОНА</span>')
            ui.html(f'<span style="color:rgba(255,255,255,0.45); '
                    f'font-size:0.8rem;">{papka.name} · цех {ceh}</span>')
            ui.element("div").style("flex:1")
            ui.button("← в кабинет",
                      on_click=lambda: ui.navigate.to(f"/torg/{ceh}")
                      ).props("flat no-caps dense").style(
                "color:rgba(255,255,255,0.5); font-size:0.75rem;")

        ui.html(
            '<div style="margin-top:10px; display:flex; gap:18px; '
            'flex-wrap:wrap; font-size:0.82rem;">'
            + f'<span style="color:rgba(255,255,255,0.75);">мест: '
              f'<b>{len(mesta)}</b></span>'
            + f'<span style="color:#3ddc6b;">вошёл: '
              f'<b>{schet["ВОШЁЛ"]}</b></span>'
            + f'<span style="color:#4d9bff;">ведение: '
              f'<b>{schet["ВЕДЕНИЕ"]}</b></span>'
            + f'<span style="color:#ffb454;">отказов: '
              f'<b>{schet["ОТКАЗ"]}</b></span>'
            + f'<span style="color:#ff5c5c;">без приказа: '
              f'<b>{schet["БЕЗ ПРИКАЗА"]}</b></span>'
            + '</div>')

        # OTCHYOT_PRAVDU_I_R_V1: ИТОГ ПО СДЕЛКАМ. Раньше отчёт не
        # давал ни одного показателя — только текст.
        # SHAPKA_PO_ZHURNALU_V1: сделки — прямо из журнала закрытий за
        # время этого прогона, как в самом отчёте. Через места терялись
        # сделки, у которых заявку перевезли (город или MOVE_ORDER):
        # цена входа на месте и в журнале уже разная.
        _ry = []
        _pk_sh = []   # PUNKTY_V_OTCHYOTE_V1
        try:
            from hooks import PNL_PATH as _pp_sh
            from datetime import datetime as _dt_sh
            _p_sh = Path(_pp_sh)
            if _p_sh.exists():
                for _ln in _p_sh.read_text(encoding="utf-8").splitlines():
                    _ln = _ln.strip()
                    if not _ln:
                        continue
                    try:
                        _z = json.loads(_ln)
                        _t = _dt_sh.fromisoformat(str(_z.get("ts") or "")[:19])
                    except Exception:
                        continue
                    if _OKNO[0] is None or _t < _OKNO[0]:
                        continue
                    if _OKNO[1] is not None and _t >= _OKNO[1]:
                        continue
                    _rz = _z.get("pnl_r")
                    if isinstance(_rz, (int, float)):
                        _ry.append(float(_rz))
                    # PUNKTY_V_OTCHYOTE_V1: пункты сделки
                    _pp = _z.get("pnl_price")
                    if isinstance(_pp, (int, float)):
                        _s = str(_z.get("symbol") or "").upper()
                        _pt = (0.001 if ("JPY" in _s or "XAG" in _s) else
                               0.01 if ("XAU" in _s or "GOLD" in _s)
                               else 0.00001)
                        _pk_sh.append(int(round(_pp / _pt)))
        except Exception as _e_sh:
            print(f"[ОТЧЁТ] шапка: журнал не прочитался ({_e_sh})")
        if _ry:
            _pl = [x for x in _ry if x > 0]
            _mi = [x for x in _ry if x < 0]
            _obshchiy = sum(_ry)
            _sredniy = _obshchiy / len(_ry)
            _c_ob = "#3ddc6b" if _obshchiy > 0 else "#ff5c5c"
            _c_sr = "#3ddc6b" if _sredniy > 0 else "#ff5c5c"
            ui.html(
                '<div style="margin-top:8px; padding-top:8px; '
                'border-top:1px solid rgba(255,255,255,0.08); '
                'display:flex; gap:18px; flex-wrap:wrap; '
                'font-size:0.82rem;">'
                + f'<span style="color:rgba(255,255,255,0.75);">'
                  f'сделок закрыто: <b>{len(_ry)}</b></span>'
                + f'<span style="color:#3ddc6b;">в плюс: '
                  f'<b>{len(_pl)}</b></span>'
                + f'<span style="color:#ff5c5c;">в минус: '
                  f'<b>{len(_mi)}</b></span>'
                + f'<span style="color:{_c_ob};">общий: '
                  f'<b>{_obshchiy:+.2f}R</b></span>'
                + f'<span style="color:{_c_sr};">средний: '
                  f'<b>{_sredniy:+.2f}R</b></span>'
                + (f'<span style="color:'
                   f'{"#3ddc6b" if sum(_pk_sh) > 0 else "#ff5c5c"};">'
                   f'пункты: <b>{sum(_pk_sh):+d}</b></span>'
                   if _pk_sh else '')
                + '</div>')

        # выбор другого прогона
        vse = _progony(ceh)
        if len(vse) > 1:
            with ui.row().style("margin-top:10px; gap:6px; "
                                "flex-wrap:wrap; align-items:center;"):
                ui.html('<span style="color:rgba(255,255,255,0.4); '
                        'font-size:0.72rem;">другие прогоны:</span>')
                for d in vse[:10]:
                    if d.name == papka.name:
                        continue
                    ui.button(
                        d.name,
                        on_click=lambda _=None, n=d.name:
                            ui.navigate.to(f"/otchyot/{ceh}/{n}")
                    ).props("flat no-caps dense").style(
                        "font-size:0.7rem; color:rgba(120,168,201,0.9);")


def _itog_kuskom(m: dict) -> str:
    """OTCHYOT_PRAVDU_I_R_V1: кусок разметки с результатом сделки."""
    d = str(m.get("действие") or "").upper()
    v = str(m.get("вердикт") or "").upper()
    if not (d == "ENTER" or (d not in ("HOLD", "MOVE_STOP", "ADD",
                                       "CLOSE", "WAIT")
                             and v in ("APPROVED", "ENTER", "OK"))):
        return ""
    r, slovami = _itog_mesta(m)
    if not slovami:
        return ""
    c = "#7c8b99" if r is None else ("#3ddc6b" if r > 0 else "#ff5c5c")
    return (f'<span style="color:{c}; font-weight:700; '
            f'font-size:0.82rem;">{slovami}</span>')


def _kartochka(ceh: str, papka: Path, nomer: int, m: dict):
    metka, cvet = _chto_sdelal(m)
    kadr = str(m.get("кадр") or "")
    kogda = str(m.get("когда_на_рынке") or m.get("место_найдено_на") or "?")
    nayden = str(m.get("место_найдено_на") or "")
    povod = str(m.get("разворотный") or "")
    cena_r = m.get("цена_разворотного")
    skazal = str(m.get("сказал") or m.get("причина") or "").strip()

    with ui.element("div").style(
        f"background:{FON}; border:{RAMKA}; border-left:3px solid {cvet}; "
        f"border-radius:12px; padding:14px 16px; margin-bottom:14px;"
    ):
        with ui.row().style("gap:16px; width:100%; align-items:flex-start; "
                            "flex-wrap:wrap;"):
            # кадр
            if kadr:
                ui.html(
                    f'<a href="/otchyot-kadry/{ceh}/прогоны/{papka.name}'
                    f'/кадры/{kadr}" target="_blank">'
                    f'<img src="/otchyot-kadry/{ceh}/прогоны/{papka.name}'
                    f'/кадры/{kadr}" '
                    f'style="width:460px; max-width:46vw; border-radius:8px; '
                    f'border:1px solid rgba(255,255,255,0.08);"></a>')
            else:
                ui.html('<div style="width:460px; max-width:46vw; '
                        'height:120px; display:flex; align-items:center; '
                        'justify-content:center; border-radius:8px; '
                        'border:1px dashed rgba(255,255,255,0.15); '
                        'color:rgba(255,255,255,0.3); font-size:0.75rem;">'
                        'кадра нет</div>')

            # разбор
            with ui.element("div").style("flex:1; min-width:280px;"):
                ui.html(
                    f'<div style="display:flex; gap:10px; '
                    f'align-items:baseline; flex-wrap:wrap;">'
                    f'<span style="color:rgba(255,255,255,0.35); '
                    f'font-size:0.72rem;">{nomer:02d}</span>'
                    f'<span style="color:rgba(255,255,255,0.9); '
                    f'font-weight:700; font-size:0.86rem;">{kogda}</span>'
                    f'<span style="color:{cvet}; font-weight:700; '
                    f'font-size:0.82rem;">{metka}</span>'
                    # OTCHYOT_PRAVDU_I_R_V1: чем кончилась ЭТА сделка.
                    + _itog_kuskom(m) + '</div>')

                _hv = []
                if povod:
                    _hv.append(f"разбудило: {povod}"
                               + (f" @ {cena_r}" if cena_r else ""))
                if nayden and nayden != kogda:
                    _hv.append(f"место найдено на {nayden}")
                if m.get("этаж"):
                    _hv.append(f"{m.get('инструмент', '')} "
                               f"{m.get('этаж', '')}".strip())
                if _hv:
                    ui.html(f'<div style="color:rgba(255,255,255,0.45); '
                            f'font-size:0.74rem; margin-top:4px;">'
                            f'{" · ".join(_hv)}</div>')

                if skazal:
                    ui.html(
                        f'<div style="color:rgba(255,255,255,0.78); '
                        f'font-size:0.82rem; line-height:1.55; '
                        f'margin-top:10px; white-space:pre-wrap;">'
                        f'{skazal}</div>')


def page_otchyot(ceh: str = "торговый_хаос", papka: str = ""):
    """Страница отчёта. Пусто — берём свежий прогон цеха."""
    ui.query("body").style(f"background:#070a0e;")
    with ui.element("div").style(
        "max-width:1180px; margin:0 auto; padding:22px 18px 60px;"
    ):
        vse = _progony(ceh)
        if not vse:
            ui.html('<div style="color:rgba(255,255,255,0.6);">'
                    'Прогонов пока нет — сходи в кабинет и запусти.</div>')
            ui.button("← в кабинет",
                      on_click=lambda: ui.navigate.to(f"/torg/{ceh}")
                      ).props("flat no-caps")
            return

        p = None
        if papka:
            p = next((d for d in vse if d.name == papka), None)
        if p is None:
            p = vse[0]

        mesta = _mesta(p)
        # KRAY_I_SHAPKA_V1: окно прогона — от его начала до начала
        # следующего (имена папок — время старта).
        try:
            from datetime import datetime as _dtk
            _ik = vse.index(p)
            _OKNO[0] = _dtk.strptime(p.name[:15], "%Y%m%d_%H%M%S")
            _OKNO[1] = (_dtk.strptime(vse[_ik - 1].name[:15],
                                      "%Y%m%d_%H%M%S")
                        if _ik > 0 else None)
        except Exception:
            _OKNO[0] = _OKNO[1] = None
        _ZHURNAL.clear()
        _shapka(ceh, p, mesta)

        if not mesta:
            ui.html('<div style="color:rgba(255,255,255,0.5); '
                    'font-size:0.85rem;">В этом прогоне мест не '
                    'записано.</div>')
            return

        for i, m in enumerate(mesta, 1):
            _kartochka(ceh, p, i, m)
