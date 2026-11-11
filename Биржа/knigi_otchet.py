# -*- coding: utf-8 -*-
# GOROD_SMOTRIT_V1 — раздел «Книга места» в отчёте прогона (из журнала закрытий)
"""
Слово Шефа 13.10: город не торгует, только пишет своё и показывает жителю.
Книга одна — места: основная позиция (magic 100003), её частичные куски и его
доливки (ноги в той же magic или отдельная magic 2200003). R — в единицах
ИСХОДНОГО риска: сумма pnl_price кусков / риск основной позиции.
Рядом — «город показал бы»: тень (magic 1100003) с тем же входом, которая
вышла по фактам (стоп или три условия против). Это НЕ сделка, только мерка.
"""
from __future__ import annotations

try:   # MESTA_PO_POMETKE_V1: семья любого места уровня «продвинутый новичок», не одного A08
    import mesto_urovnya as _md
    NOMER_MESTA, NOMER_DOLIVKI, TEN = _md.LYUBOY_MESTO, _md.LYUBAYA_DOLIVKA, _md.LYUBAYA_TEN
except Exception:
    NOMER_MESTA, NOMER_DOLIVKI = 100003, 2200003
    TEN = 1100003
PO_RUSSKI = {"STOP_LOSS": "стоп", "CITY_RULES": "три условия",
             "MANUAL_CLOSE": "закрыл сам", "EXIT_BELL": "колокол"}


def _f(x):
    try:
        return float(x)
    except Exception:
        return None


def _vhod(z):
    if z.get("magic") == NOMER_DOLIVKI:
        try:
            return str(z.get("основная") or "").split("|")[2][:10]
        except IndexError:
            pass
    return str(z.get("opened_at") or "")[:10]


def svodka(otch) -> list:
    zakr = otch._zakrytiya()
    rows = [z for z in zakr if z.get("magic") in (NOMER_MESTA, NOMER_DOLIVKI)]
    teni = [z for z in zakr if z.get("magic") == TEN]
    if not rows and not teni:
        return []
    out = ["### Книга места", "",
           "Город не торгует, только смотрит и показывает (слово Шефа 13.10). Книга одна — "
           "позиция места, её частичные куски и его доливки. Колонка «город показал бы» — "
           "где вышла бы тень с тем же входом по фактам (стоп или три условия против); "
           "это не сделка, а мерка. R — в единицах исходного риска.", ""]
    vmesh = [z for z in rows if z.get("close_reason") == "CITY_RULES"]
    out.append(f"Проверка: город закрыл позиций места — **{len(vmesh)}** (должно быть 0). "
               f"Записей закрытия у места: {len(rows)}, из них доливок "
               f"{sum(1 for z in rows if z.get('нога') or z.get('magic') == NOMER_DOLIVKI)}, "
               f"частичных кусков {sum(1 for z in rows if z.get('частичное'))}.")
    out += ["", "| вход | сторона | куски и доливки места | R места | город показал бы | R тени |",
            "|---|---|---|---|---|---|"]
    gr = {}
    for z in rows:
        gr.setdefault(_vhod(z), {"j": [], "t": []})["j"].append(z)
    for z in teni:
        gr.setdefault(_vhod(z), {"j": [], "t": []})["t"].append(z)
    itog_j = itog_t = 0.0
    n = plus = 0
    for d0, g in sorted(gr.items()):
        base = next((z for z in g["j"] if z.get("magic") == NOMER_MESTA and not z.get("нога")
                     and not z.get("частичное")), None) or \
            next((z for z in g["j"] if z.get("magic") == NOMER_MESTA and not z.get("нога")), None) or \
            (g["t"][0] if g["t"] else None)
        if base is None:
            continue
        pp, pr = _f(base.get("pnl_price")), _f(base.get("pnl_r"))
        risk0 = abs(pp / pr) if (pp is not None and pr not in (None, 0.0)) else None
        if not risk0:
            continue
        det = []
        for z in sorted(g["j"], key=lambda z: str(z.get("closed_at") or "")):
            w = _f(z.get("доля")) or 1.0
            tip = ("доливка" if (z.get("нога") or z.get("magic") == NOMER_DOLIVKI) else
                   "часть" if z.get("частичное") else "позиция")
            det.append(f"{str(z.get('closed_at') or '')[:10]} {tip} {w:g}: "
                       f"{PO_RUSSKI.get(str(z.get('close_reason')), z.get('close_reason'))} "
                       f"@ {z.get('exit')}")
        ten = "; ".join(f"{str(z.get('closed_at') or '')[:10]} "
                        f"{PO_RUSSKI.get(str(z.get('close_reason')), z.get('close_reason'))} "
                        f"@ {z.get('exit')}" for z in g["t"]) or "—"
        # STORONA_PO_SDELKE_V1: сторона — по самой сделке. В записи о закрытии
        # направления нет, а стоп там последний (подвинутый стоп лонга выше
        # входа делал из него SHORT). Куда ушёл выход от входа и в плюс ли.
        sg = str(base.get("direction") or "").upper()
        if sg not in ("LONG", "SHORT"):
            _e, _x = _f(base.get("entry")), _f(base.get("exit"))
            _pr = _f(base.get("pnl_price"))
            if _pr is None:
                _pr = _f(base.get("pnl_r"))
            if _e is not None and _x is not None and _pr and _x != _e:
                sg = "LONG" if (_x > _e) == (_pr > 0) else "SHORT"
            else:
                _st0 = _f(base.get("stop_initial"))
                if _st0 is None:
                    _st0 = _f(base.get("stop"))
                sg = "LONG" if (_st0 or 0) < (_e or 0) else "SHORT"
        if g["j"]:
            Rj = sum(_f(z.get("pnl_price")) or 0.0 for z in g["j"]) / risk0
            itog_j += Rj
            n += 1
            plus += 1 if Rj > 1e-9 else 0
            rj = f"{Rj:+.2f}"
        else:
            rj = "ещё открыта"
        if g["t"]:
            Rt = sum(_f(z.get("pnl_price")) or 0.0 for z in g["t"]) / risk0
            itog_t += Rt
            rt = f"{Rt:+.2f}"
        else:
            rt = "ещё открыта"
        out.append(f"| {d0} | {sg} | {'; '.join(det) or '—'} | {rj} | {ten} | {rt} |")
    out += ["", f"Сделок места: **{n}** · в плюс {plus} · книга места **{itog_j:+.2f}R** · "
                f"город показал бы **{itog_t:+.2f}R** (не сделки, мерка)", ""]
    return out


# GOROD_SMOTRIT_V1 - marker

# KNIGI_STORONA_V1 - marker

# STORONA_PO_SDELKE_V1 - marker
