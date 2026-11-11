# -*- coding: utf-8 -*-
# ZA_DIAPAZONOM_V1
"""
РАЗВОРОТ ЗА ПРЕДЕЛАМИ ДИАПАЗОНА — одно правило для руки и стола.

Канон («Торговый хаос», 2-е изд., гл. 9): у бара разворота ключ в том, что
рынок вывел цену за рамки текущего ценового диапазона. Слово Шефа 09.11.

Край — экстремум последних четырёх закрытых баров. Ход, который вход
разворачивает, — по подтверждённым фракталам (volny_ao._hod_seychas), его
начало S. Прошлый размах — от P до S: P — дно (для LONG) с тех пор, как цена
в последний раз была выше S. LONG: край ниже P — за пределами. SHORT —
зеркально. Город считает и показывает; запрет ставит рука места.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
if str(_BIRZHA) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA))

OKNO = 140
NAZAD = 400


def _d(b, i):
    return str((b[i] or {}).get("date") or "")[:16]


def proverit(symbol: str, tf: str, napr: str, bars=None) -> dict:
    """→ {"за": True/False/None, "слова": str, "откат": float|None}."""
    napr = str(napr or "").upper()
    if napr not in ("LONG", "SHORT"):
        return {"за": None, "слова": "сторона не названа", "откат": None}
    try:
        if bars is None:
            from feed_source import bars as _bars
            bars, _pt = _bars(symbol, tf, 400)
            try:
                from hooks import _tolko_zakrytye
                bars = _tolko_zakrytye(bars)
            except Exception:
                pass
        n = len(bars or [])
        if n < 60:
            return {"за": None, "слова": "мало баров", "откат": None}
        hi = [b["high"] for b in bars]
        lo = [b["low"] for b in bars]
        j = n - 1
        dlong = napr == "LONG"
        okno = range(max(0, j - 3), j + 1)
        e = (min(okno, key=lambda i: (lo[i], -i)) if dlong
             else max(okno, key=lambda i: (hi[i], i)))
        a = max(0, n - (OKNO + 40))
        hw, lw = hi[a:], lo[a:]
        m = len(hw)
        import volny_ao as _va
        hs = _va._hod_seychas(hw, lw, not dlong, max(0, m - OKNO), m - 1)
        if not hs or hs.get("начало") is None:
            return {"за": None, "слова": "ход к краю не читается по фракталам", "откат": None}
        S = a + hs["начало"]
        if S >= e:
            return {"за": None, "слова": "начало хода не раньше края", "откат": None}
        q = None
        for i in range(S - 1, max(-1, S - NAZAD), -1):
            if (dlong and hi[i] > hi[S]) or (not dlong and lo[i] < lo[S]):
                q = i
                break
        q = (q + 1) if q is not None else max(0, S - NAZAD)
        if q >= S:
            return {"за": None, "слова": "прошлого размаха нет", "откат": None}
        if dlong:
            P = min(range(q, S + 1), key=lambda i: (lo[i], -i))
            raz, hod = hi[S] - lo[P], hi[S] - lo[e]
            za = lo[e] < lo[P]
            kak = (f"снижение от {hi[S]} ({_d(bars, S)}) до {lo[e]} ({_d(bars, e)}); "
                   f"прошлый подъём начинался с {lo[P]} ({_d(bars, P)})")
        else:
            P = max(range(q, S + 1), key=lambda i: (hi[i], i))
            raz, hod = hi[P] - lo[S], hi[e] - lo[S]
            za = hi[e] > hi[P]
            kak = (f"подъём от {lo[S]} ({_d(bars, S)}) до {hi[e]} ({_d(bars, e)}); "
                   f"прошлое снижение начиналось с {hi[P]} ({_d(bars, P)})")
        r = (hod / raz) if raz > 0 else None
        if za:
            sl = f"ЗА ПРЕДЕЛАМИ — {kak}: край ушёл дальше начала прошлого размаха"
        else:
            sl = (f"ВНУТРИ — {kak}: это откат "
                  + (f"{r:.2f} " if r is not None else "") + "прошлого размаха, цена за "
                  "рамки диапазона не вышла")
        return {"за": bool(za), "слова": sl, "откат": r}
    except Exception as e:
        return {"за": None, "слова": f"не посчиталось ({e})", "откат": None}


def mesta() -> list:
    """Места с пометкой «за_диапазоном»: «да» во всех цехах → [(цех, слот, ключ)]."""
    import json as _j
    out = []
    korn = _BIRZHA.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха"
    try:
        for mp in korn.glob("*/manifest.json"):
            try:
                man = _j.loads(mp.read_text(encoding="utf-8"))
            except Exception:
                continue
            for z in man.get("слоты") or []:
                if str(z.get("за_диапазоном") or "").strip().lower() in ("да", "true", "1"):
                    sl = str(z.get("слот") or "").strip()
                    out.append((mp.parent.name, sl, str(z.get("ключ") or sl).strip().lower()))
    except Exception:
        pass
    return out


# ZA_DIAPAZONOM_V1 - marker
