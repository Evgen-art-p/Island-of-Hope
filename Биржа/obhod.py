# -*- coding: utf-8 -*-
# OBHOD_ETAZHEY_V1
"""
ОБХОД ЭТАЖЕЙ — как трейдер находит свой рабочий масштаб.

ЗАЧЕМ
    Шеф задаёт трейдеру ТОЛЬКО инструмент. Этаж — его дело: он
    проходит по коридору масштабов, смотрит картинку на каждом и
    выбирает тот, где ЕГО структура ложится в окно целиком.
    Окно фиксировано (140 баров), меняется этаж — меняется, сколько
    времени в это окно влезает.

ЗАКОН ЭТОГО ФАЙЛА
    Рука ВОДИТ и ЗАПИСЫВАЕТ. Она не решает и не имеет своего мнения
    о рынке. Смотрит глаз трейдера — через разговорную дверь его
    СОБСТВЕННОГО мозга. Своей модели, своего промпта и своих знаний
    у руки нет: параллельной дороги вдоль слота мы больше не строим
    (урок vzglyad.py, 06.08).

ЦЕНА
    Каждый этаж — картинка, картинка — деньги. Поэтому обход не на
    каждый бар: при назначении инструмента, дальше раз в сутки или
    когда позвали руками.
"""
from __future__ import annotations

import json
import sys as _sys
from datetime import datetime, timedelta
from pathlib import Path

_BIRZHA = Path(__file__).resolve().parent
_KOREN = _BIRZHA.parent
for _p in (str(_BIRZHA), str(_KOREN / "ГОРОД"), str(_KOREN / "жители")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

CEH_PO_UMOLCHANIYU = "торговый_хаос"
SUTKI = timedelta(hours=24)

# где помним, когда и по чему ходили — при слоте, а не общим листком
def _sled_put(ceh: str, slot: str) -> Path:
    return (_KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh / "слоты"
            / slot / "данные" / "obhod.json")


def _sled(ceh: str, slot: str) -> dict:
    try:
        return json.loads(_sled_put(ceh, slot).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _zapisat_sled(ceh: str, slot: str, d: dict):
    p = _sled_put(ceh, slot)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    except Exception as e:
        print(f"[ОБХОД] ⚠️  след не записался: {e}")


def nado_li_oboyti(ceh: str, slot: str) -> tuple:
    """(надо ли, почему). Обход платный — зовём по делу, не каждый бар."""
    import vybor
    r = vybor.rabota_dlya(ceh, slot)
    if not r.get("инструмент"):
        return False, "инструмент не задан — обходить нечего"
    sled = _sled(ceh, slot)
    if not r.get("этаж"):
        return True, "рабочего этажа ещё нет"
    if (sled.get("инструмент") or "").upper() != r["инструмент"].upper():
        return True, "инструмент сменился"
    kogda = sled.get("когда") or ""
    try:
        if datetime.fromisoformat(kogda) < datetime.now() - SUTKI:
            return True, "прошли сутки с прошлого обхода"
    except Exception:
        return True, "неизвестно, когда ходили"
    return False, "ходили недавно, этаж есть"


def _dver_razgovora(ceh: str, slot: str):
    """Разговорная дверь мозга ЭТОГО слота. Своей не заводим."""
    import importlib.util
    put = (_KOREN / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh / "слоты"
           / slot / "мозг.py")
    if not put.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"_mozg_{ceh}_{slot}", put)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for imya in dir(mod):
        if imya.startswith("chat_with_"):
            return getattr(mod, imya)
    return None


VOPROS = """Тебе назначен инструмент {symbol}. Рабочий этаж выбираешь ты сам.

Сейчас ты смотришь {tf}. На картинке — {barov} баров этого этажа.

Вопрос один: ложится ли на этом масштабе ТВОЯ структура целиком —
та, по которой ты работаешь? Тебе нужно видеть и импульс, и коррекцию
после него, и место, где ты входишь. Не «есть ли сигнал прямо сейчас»,
а «читается ли здесь картина».

Если структура не влезла — масштаб мелкий, надо крупнее.
Если она сжата в несколько баров и разворотный бар не разглядеть —
масштаб крупный, надо мельче.

Ответь коротко, своими словами. Если этот этаж тебе подходит как
РАБОЧИЙ — закончи ответ отдельной строкой:
ЭТАЖ: {tf}
Если не подходит — просто скажи почему, строку не пиши."""


def oboyti(ceh: str = CEH_PO_UMOLCHANIYU, slot: str = "",
           predel: int = 0, govorit=print) -> dict:
    """Провести трейдера по коридору. Решение — его, запись — наша.

    predel — сколько этажей показать максимум (0 = весь коридор).
    Возвращает {этаж, шагов, почему, ошибка}.
    """
    import vybor
    import masshtab

    itog = {"этаж": "", "шагов": 0, "почему": "", "ошибка": ""}
    r = vybor.rabota_dlya(ceh, slot)
    symbol = r.get("инструмент") or ""
    if not symbol:
        itog["ошибка"] = "инструмент не задан — водить не по чему"
        return itog

    dver = _dver_razgovora(ceh, slot)
    if dver is None:
        itog["ошибка"] = "у слота нет разговорной двери (мозг не найден)"
        return itog

    etazhi = masshtab.koridor_ot(r.get("этаж") or "")
    if predel > 0:
        etazhi = etazhi[:predel]

    govorit(f"[ОБХОД] 🧭 {slot} · {symbol} · коридор: {', '.join(etazhi)}")
    for tf in etazhi:
        itog["шагов"] += 1
        vopros = VOPROS.format(symbol=symbol, tf=tf,
                               barov=masshtab.BAROV_V_KADRE)
        try:
            # rynok=(инструмент, этаж) — кадр этого этажа подложит
            # сам мозг, своим глазом. Мы картинку не рисуем.
            otvet = dver(vopros, None, None, (symbol, tf))
        except Exception as e:
            govorit(f"[ОБХОД] ⚠️  {tf}: не ответил ({e})")
            continue
        vzyal, chto = vybor.poymat_etazh(ceh, slot, symbol, otvet or "")
        korotko = " ".join((otvet or "").split())[:110]
        if vzyal:
            govorit(f"[ОБХОД] ✓ {tf} — берёт: {chto}")
            govorit(f"[ОБХОД]   его словами: {korotko}")
            itog["этаж"] = tf
            itog["почему"] = korotko
            break
        govorit(f"[ОБХОД] · {tf} — не тот: {korotko}")

    _zapisat_sled(ceh, slot, {
        "инструмент": symbol,
        "этаж": itog["этаж"],
        "шагов": itog["шагов"],
        "когда": datetime.now().isoformat(timespec="seconds"),
        "почему": itog["почему"],
    })
    if not itog["этаж"]:
        itog["ошибка"] = ("прошёл коридор и не выбрал ни одного этажа — "
                          "картинка не читается ни на одном масштабе")
        govorit(f"[ОБХОД] 🤐 {slot}: {itog['ошибка']}")
    return itog


if __name__ == "__main__":
    _slot = _sys.argv[1] if len(_sys.argv) > 1 else ""
    if not _slot:
        print("Скажи, кого вести: py obhod.py A06")
        raise SystemExit(1)
    _ceh = _sys.argv[2] if len(_sys.argv) > 2 else CEH_PO_UMOLCHANIYU
    nado, pochemu = nado_li_oboyti(_ceh, _slot)
    print(f"[ОБХОД] надо ли: {'да' if nado else 'нет'} — {pochemu}")
    print(oboyti(_ceh, _slot))

# OBHOD_ETAZHEY_V1 - marker
