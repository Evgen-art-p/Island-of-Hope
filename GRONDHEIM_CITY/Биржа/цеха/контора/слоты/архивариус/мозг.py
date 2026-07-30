# GRONDHEIM_CITY/Биржа/цеха/контора/слоты/архивариус/мозг.py
# ─────────────────────────────────────────────────────────────
# ЖИВОЙ АРХИВАРИУС — Хранитель Памяти Биржи (штаб конторы)
# ARKHIV_ENGINE_V1 · перенесён на слотовое шасси 09.07 (KONTORA_SLOT_V1)
#
# Портирован дословно из studio/modules/trading/arkhiv_live.py (-2,
# Спринт 45). Форма — близнец мозгов торгового_хаоса (Морж/Паникёр/
# Ганс): живая модель + штатная память + голос+сигнал двухслойным
# JSON + чат с Шефом. Математика build_digest не тронута НИ БИТОМ —
# «код считает, голова толкует».
#
# НО ЛИНЗА ДРУГАЯ. Морж смотрит РЫНОК. Архивариус рынок НЕ смотрит —
# ни одним глазом (его закон). Его глаза — СКЛАД: atlas_trading.jsonl.
# Он считает digest по сигнатуре стола и ТОЛКУЕТ числа голосом
# хранителя.
#
# ЗАКОН: «код считает — голова толкует». sample_size / success_rate /
#   top_failure_reason считает КОД (build_digest). arkhiv_confidence —
#   по жёсткому правилу контракта. Голова их КОПИРУЕТ в signal и
#   одевает в голос. Не пересчитывает.
#
# СИГНАТУРА = СУММА ВСЕХ СЕНСОРОВ (не один Ганс!):
#   t1_status (Искра) + morj_status (Морж) + panic_phase (Паникёр)
#   + fractal_valid (Ганс). Четыре голоса = лицо момента.
#
# КОНТОРА, НЕ ЦЕХ (§3 БИРЖА.md, решение 09.07): Архивариус — служба,
# общая на всю Биржу, а не слот одного цеха. Механика цех-независима:
# от цеха меняется только путь к следу, не характер.
#
# ХАРАКТЕР: не здесь. РОД Арчи (Чертёж Единицы: паспорт, не меняется
# работой) живёт в жители/ковчег/Арчи/passport.json — там же и его
# DNA_Static. Старый dna.json из -2 сюда НЕ перенесён — он дублировал
# бы то, что паспорт резидента уже несёт полнее (создан 07.07, позже
# старого dna.json). Слот несёт РОЛЬ (промпт+знания+данные), не РОД.
# ─────────────────────────────────────────────────────────────

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

# ЗАКОН КАРТРИДЖА ДЛЯ КОДА: файл живёт ПРЯМО В СЛОТЕ, рядом со своим
# промптом. Слот несёт с собой всё: слоты/архивариус/{мозг.py,
# промпт.md, знания/, данные/}.
_SLOT_DIR    = Path(__file__).resolve().parent            # слоты/архивариус/
_CEH_DIR     = _SLOT_DIR.parent.parent                     # контора/
_REPO        = _CEH_DIR.parents[3]                          # корень репо
_BIRZHA_CODE = _REPO / "Биржа"                              # общий код (движок, llm)

# KLON_DUSHI_V1: пара (цех, слот) — ИЗ ПУТИ мозга, без хардкода личности.
# Контора не ломается: её слоты зовутся «архивариус»/«исполнитель».
_CEH  = _CEH_DIR.name
_SLOT = _SLOT_DIR.name

import sys as _sys
if str(_BIRZHA_CODE) not in _sys.path:
    _sys.path.insert(0, str(_BIRZHA_CODE))

from llm import chat

PROMPT_PATH  = _SLOT_DIR / "промпт.md"
STATE_DIR    = _SLOT_DIR / "данные"
STATS_PATH   = STATE_DIR / "arkhiv_stats.json"

# Склад Архивариуса — тот же Атлас, что пишут hooks._write_atlas / _settle.
# ФАЗА 1 (перенос): путь НЕ трогаем — писатель (hooks.py) и читатель
# (этот файл) должны смотреть в одно и то же место. Правка охвата
# (общий котёл контора/журналы/ + метка цеха) — отдельный заход,
# см. БИРЖА.md §3 и §7б («нить, что торчит наружу»).
ATLAS_PATH   = Path(__file__).resolve().parents[4] / "данные" / "atlas_trading.jsonl"   # ARKHIV_ATLAS_PATH_ABS_V1: тот же файл, что пишет hooks._write_atlas
PNL_PATH     = Path(__file__).resolve().parents[4] / "данные" / "trading_pnl.jsonl"     # та же лента закрытий, что atlas_trading.jsonl

# Грани лица момента — сумма голосов сенсоров (CHAIN_CONTRACT v1.7).
SIGNATURE_KEYS = ("t1_status", "morj_status", "panic_phase", "fractal_valid")


# ═══════════════════════════════════════════════════════════
# РАБОЧИЙ ДВИЖОК АРХИВАРИУСА — что он умеет со своим складом.
# ARKHIV_ATLAS_CARE_V1 (21.07, решение Шефа): «он же ищет в атласе
# информацию для столов — вот пусть и чистит, и проверяет».
# Перенесено дословно из proverit_atlas.py (инспектор) и
# ochistit_atlas.py (чистка) — те же формулы, тот же смысл, только
# как функции его роли, не отдельные CLI-скрипты. Вызывать ТОЛЬКО
# через rezident_menedzher.vyzvat("контора", "архивариус", ...) —
# решение Шефа, никто не лезет в мозг напрямую в обход двери.
# ═══════════════════════════════════════════════════════════

def _naiti_dublikaty(path: Path, label: str) -> dict:
    """
    Честная картина одного файла (тот же приём, что proverit_atlas.py):
    всего строк, битых (не JSON), уникальных сделок по ключу
    (symbol, timeframe, trader, opened_at), дублей, расхождений pnl_r
    между копиями дубля, разброс дат.
    """
    if not path.exists():
        return {"label": label, "path": str(path), "exists": False}

    total = 0
    bad = 0
    by_key: dict = {}
    dates = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue

            sym = rec.get("symbol")
            tf = rec.get("timeframe")
            trader = rec.get("trader")
            opened = rec.get("opened_at")
            if opened:
                dates.append(str(opened))

            if rec.get("pnl_r") is not None or rec.get("pnl") is not None:
                key = (sym, tf, trader, opened)
                by_key.setdefault(key, []).append(rec)

    dup_keys = {k: v for k, v in by_key.items() if len(v) > 1}
    total_closed = sum(len(v) for v in by_key.values())

    dup_examples = []
    for key, recs in list(dup_keys.items())[:5]:
        r_values = [r.get("pnl_r") for r in recs]
        dup_examples.append({
            "key": key,
            "count": len(recs),
            "pnl_r_values": r_values,
            "protivorechat": len(set(r_values)) > 1,
        })

    return {
        "label": label,
        "path": str(path),
        "exists": True,
        "total_lines": total,
        "bad_lines": bad,
        "closed_total": total_closed,
        "unique_trades": len(by_key),
        "duplicated_trades": len(dup_keys),
        "dup_examples": dup_examples,
        "dates_range": (min(dates), max(dates)) if dates else None,
        "unique_dates": len(set(dates)) if dates else 0,
    }


def proverit_atlas() -> dict:
    """
    ИНСПЕКТОР — ничего не меняет, не пишет. Честная картина
    atlas_trading.jsonl и trading_pnl.jsonl: дубли сделок, расхождения
    pnl_r между прогонами, разброс дат. Вызывается через
    rezident_menedzher (действие "proverit_atlas").
    """
    return {
        "pnl":   _naiti_dublikaty(PNL_PATH, "trading_pnl.jsonl (полная лента закрытий)"),
        "atlas": _naiti_dublikaty(ATLAS_PATH, "atlas_trading.jsonl (память Архивариуса)"),
    }


def _ochistit_odin(path: Path, label: str) -> dict:
    """Архивирует один файл целиком (с меткой времени), обнуляет. Не удаляет."""
    if not path.exists():
        return {"label": label, "ok": False, "reason": "файл не найден — нечего чистить"}

    n_lines = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    if n_lines == 0:
        return {"label": label, "ok": False, "reason": "и так пуст — чистить нечего"}

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = path.with_name(f"{path.stem}_archive_{stamp}{path.suffix}")
    archive.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text("", encoding="utf-8")

    return {"label": label, "ok": True, "archived_lines": n_lines,
            "archived_to": str(archive)}


def pochistit_atlas() -> dict:
    """
    ЧИСТКА — архивирует atlas_trading.jsonl и trading_pnl.jsonl целиком
    (переименовывает с меткой времени, НЕ удаляет), затем обнуляет оба.
    НЕ трогает trading_state.json (открытые позиции — своя забота).
    Вызывается через rezident_menedzher (действие "pochistit_atlas").
    """
    return {
        "atlas": _ochistit_odin(ATLAS_PATH, "atlas_trading.jsonl (память Архивариуса)"),
        "pnl":   _ochistit_odin(PNL_PATH, "trading_pnl.jsonl (лента закрытий)"),
    }


def _confidence(sample_size: int, success_rate: float) -> str:
    """
    Жёсткое правило контракта (CHAIN_CONTRACT v1.7 · промпт.md).
      HIGH   = sample >= 20 И success >= 0.65
      MEDIUM = sample >= 5  И success >= 0.50
      LOW    = всё остальное (включая пустую историю).
    Малая выборка лжёт. Не натягивать.
    """
    if sample_size >= 20 and success_rate >= 0.65:
        return "HIGH"
    if sample_size >= 5 and success_rate >= 0.50:
        return "MEDIUM"
    return "LOW"


def build_digest(signature: dict) -> dict:
    """
    Считает выжимку из Атласа по сигнатуре стола. ЧИСТЫЙ КОД, без LLM.

    signature: {t1_status, morj_status, panic_phase, fractal_valid}
      — сравниваем только по непустым граням (None не фильтрует).

    Возвращает (готово к копированию в signal — контракт, которым уже
    пользуется hooks._prepare_atlas_digest):
      sample_size, closed_trades, success_rate,
      top_failure_reason, arkhiv_confidence, recent_cases[]
    """
    sig = {k: signature.get(k) for k in SIGNATURE_KEYS
           if signature.get(k) is not None}

    matches = []
    if ATLAS_PATH.exists():
        with open(ATLAS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entry = rec.get("entry", rec)
                if sig and all(entry.get(k) == v for k, v in sig.items()):
                    matches.append(entry)

    closed  = [m for m in matches if m.get("pnl") is not None]
    wins    = [m for m in closed if (m.get("pnl") or 0) > 0]
    success = round(len(wins) / len(closed), 4) if closed else 0.0

    reasons: dict = {}
    for m in matches:
        r = m.get("reason")
        if r and (m.get("verdict") == "REJECTED" or (m.get("pnl") or 0) < 0):
            reasons[r] = reasons.get(r, 0) + 1
    top_reason = max(reasons, key=lambda k: reasons[k]) if reasons else "none"

    return {
        "sample_size":        len(matches),
        "closed_trades":      len(closed),
        "success_rate":       success,
        "top_failure_reason": top_reason,
        "arkhiv_confidence":  _confidence(len(matches), success),
        "recent_cases":       matches[-5:],
    }


def _load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {"runs": 0, "high": 0, "medium": 0, "low": 0, "empty": 0}


def _update_stats(signal: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    stats = _load_stats()
    stats["runs"] = stats.get("runs", 0) + 1
    conf = signal.get("arkhiv_confidence", "LOW")
    if conf == "HIGH":
        stats["high"] = stats.get("high", 0) + 1
    elif conf == "MEDIUM":
        stats["medium"] = stats.get("medium", 0) + 1
    else:
        stats["low"] = stats.get("low", 0) + 1
    if signal.get("sample_size", 0) == 0:
        stats["empty"] = stats.get("empty", 0) + 1
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def _parse_arkhiv(response: str) -> tuple[str, dict]:
    """Достаёт {narrative, signal}. При сбое — текст как голос."""
    if not response:
        return "", {}
    for m in re.finditer(r"\{.*\}", response, re.DOTALL):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and ("narrative" in obj or "signal" in obj):
                return obj.get("narrative", ""), obj.get("signal", {}) or {}
        except json.JSONDecodeError:
            continue
    return response.strip(), {}


def chat_with_arkhiv(question: str, last_run: Optional[dict] = None,
                     dialog: Optional[list] = None) -> str:
    """
    Разговор с Архивариусом. Он не смотрит рынок — он смотрит склад.
    Если был последний прогон — помнит его выжимку.
    """
    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    if last_run:
        sig = last_run.get("signal", {})
        sg  = last_run.get("signature", {})
        work_ctx = (
            "\n\n=== ТВОЙ ПОСЛЕДНИЙ ЗАПРОС К СКЛАДУ (рабочая память) ===\n"
            f"Сигнатура стола: {json.dumps(sg, ensure_ascii=False)}\n"
            f"Нашёл случаев: {sig.get('sample_size','—')} "
            f"(закрыто {sig.get('closed_trades','—')})\n"
            f"Доля прибыльных: {sig.get('success_rate','—')}\n"
            f"Частая причина потерь: {sig.get('top_failure_reason','—')}\n"
            f"Уверенность: {sig.get('arkhiv_confidence','—')}\n"
            f"Что ты сказал: {last_run.get('narrative','')}\n"
            "=== КОНЕЦ ===\n\n"
            "Шеф спрашивает про склад. Отвечай как Архивариус — тихо, "
            "медленно, со ссылками на прошлое. Никогда «я думаю» — только "
            "«было». Живым голосом, БЕЗ JSON — это разговор, не сигнал."
        )
    else:
        work_ctx = (
            "\n\n=== РАЗГОВОР ===\n"
            "Шеф пришёл с вопросом к твоему складу. Ты не смотришь рынок — "
            "только Атлас. Отвечай тихо, со ссылками на прошлое, живым "
            "голосом без JSON. Если точных данных в памяти нет — честно "
            "скажи «такого в Атласе нет», без догадок о текущем рынке."
        )

    system = prompt + work_ctx
    try:
        from studio.grondheim_memory import format_soul_for_agent  # type: ignore[import]
        soul = format_soul_for_agent("A05_ARKHIV", dept="trading")
        if soul:
            system = (prompt + "\n\n=== ТВОЁ СОСТОЯНИЕ (душа) ===\n"
                      + soul + "\n\n" + work_ctx)
    except Exception:
        pass

    history = []
    if dialog:
        for m in dialog[:-1]:
            r = m.get("role"); c = m.get("content", "")
            if r in ("user", "assistant") and c:
                history.append({"role": r, "content": c})

    try:
        return chat(system=system, user=question, history=history,
                    agent_id="A05_ARKHIV", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return f"⚠️ Архивариус не смог ответить: {e}"


_THIN_HISTORY = 5


def _signature_to_query(signature: dict) -> str:
    """
    Лепит человеческий запрос к Оле из сигнатуры момента.
    Оле ищет по СМЫСЛУ (Гавань) — даём ей словесный отпечаток стола,
    а не голый JSON. Пустые грани пропускаем.
    """
    parts = []
    t1 = signature.get("t1_status")
    if t1 and t1 != "NOT_FOUND":
        parts.append(f"разворот {t1}")
    morj = signature.get("morj_status")
    if morj and morj != "SLEEPING":
        parts.append(f"рынок {morj}")
    panic = signature.get("panic_phase")
    if panic:
        parts.append(f"толпа {panic}")
    if signature.get("fractal_valid"):
        parts.append("действительный фрактал")
    base = "торговое решение цеха"
    return f"{base}: {', '.join(parts)}" if parts else base


def _ask_city_memory(signature: dict, digest: dict) -> list:
    """
    Рука берущая. Зовёт Оле ТОЛЬКО при тонкой истории.
    Возвращает список поднятых записей (или пустой — всегда безопасно).

    НИКОГДА не роняет прогон: любая беда с Оле → пустой список,
    Архивариус работает как до патча.
    """
    if digest.get("sample_size", 0) >= _THIN_HISTORY:
        return []
    try:
        from studio.memory_tools import remind  # type: ignore[import]
        query = _signature_to_query(signature)
        hits = remind(query, top_k=3) or []
        if hits:
            print(f"[ARKHIV] 🤝 Оле подняла {len(hits)} из памяти города "
                  f"(тетрадь тонка: {digest.get('sample_size',0)})")
        return hits
    except Exception as e:
        print(f"[ARKHIV] ⚠️  Оле недоступна ({e}) — работаю своей тетрадью")
        return []


def _format_city_for_arkhiv(hits: list) -> str:
    """Форматирует поднятое Оле для вставки в user_msg Архивариуса."""
    if not hits:
        return ""
    try:
        from studio.memory_tools import format_for_agent  # type: ignore[import]
        return format_for_agent(hits, max_chars=1200)
    except Exception:
        lines = ["=== 🧠 ПАМЯТЬ ГОРОДА (Оле подняла) ==="]
        for h in hits[:3]:
            title = h.get("title", "")
            loss = h.get("loss_if_forgotten", "")
            lines.append(f"• {title}: {loss[:150]}")
        lines.append("=== КОНЕЦ ===")
        return "\n".join(lines)


def run_arkhiv(signature: Optional[dict] = None,
               symbol: str = "XAUUSD", timeframe: str = "H4") -> dict:
    """
    Один взгляд Архивариуса В СКЛАД по сигнатуре текущего стола.

    Линза: только прошлое. Рынок НЕ поднимается. Берём сигнатуру стола →
    считаем digest по Атласу → живая голова копирует числа и одевает
    в голос хранителя.

    signature: {t1_status, morj_status, panic_phase, fractal_valid}.
      None → читаем из общей шины (trading_state), что положили сенсоры.

    Возвращает (как run_morj):
      {ok, error, narrative, signal, stats, signature, digest}
    """
    if signature is None:
        signature = {}
        try:
            from hooks import load_trading_state
            tstate = load_trading_state()
            iskra = tstate.get("iskra", {})
            morj  = tstate.get("morj", {})
            signature = {
                "t1_status":     iskra.get("t1_status"),
                "morj_status":   morj.get("morj_status"),
                "panic_phase":   tstate.get("panic", {}).get("panic_phase"),
                "fractal_valid": tstate.get("hans", {}).get("fractal_valid"),
            }
        except Exception as e:
            print(f"[ARKHIV] ⚠️  Не прочитал шину ({e}) — пустая сигнатура")

    digest = build_digest(signature)

    city_hits = _ask_city_memory(signature, digest)
    city_block = _format_city_for_arkhiv(city_hits)

    # KLON_DUSHI_V1: ДУША — от НОСИТЕЛЯ (маска, Закон Пары), не от трупа из -2.
    # Было: format_soul_for_agent из снесённой studio/ — падало ВСЕГДА
    # («No module named studio»), работали голыми. Пара — ИЗ ПУТИ мозга.
    soul = ""
    try:
        from nositel import dusha_slota
        _n = dusha_slota(_CEH, _SLOT)
        if _n:
            soul = _n["душа"]
            print(f"[ARKHIV] 🧬 За столом: {_n['носитель']['имя']}")
    except Exception as e:
        print(f"[ARKHIV] ⚠️  Носитель не поднялся ({e}) — работаю без души")

    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    user_msg = (
        "=== СИГНАТУРА ТЕКУЩЕГО СТОЛА (сумма голосов сенсоров) ===\n"
        f"{json.dumps(signature, ensure_ascii=False, indent=2)}\n\n"
        "=== ATLAS_DIGEST (готовая выжимка — КОД посчитал, ты копируешь) ===\n"
        f"{json.dumps(digest, ensure_ascii=False, indent=2)}\n\n"
        "Закон: ты ХРАНИТЕЛЬ, не командир. Числа sample_size/success_rate/"
        "top_failure_reason/arkhiv_confidence — КОПИРУЙ из digest точно, "
        "не пересчитывай. Твоя работа — ИНТЕРПРЕТАЦИЯ: что эти числа значат, "
        "на что похож случай из recent_cases, какой урок прошлого тут уместен. "
        "Не советуй входить/не входить — ты контекст. Выдай строго "
        "двухслойный JSON {narrative, signal}. signal содержит: "
        "sample_size, success_rate, top_failure_reason, arkhiv_confidence. "
        "Ничего вне JSON."
    )

    if city_block:
        user_msg += (
            "\n\n=== 🧠 ПАМЯТЬ ГОРОДА (Оле подняла — тетрадь цеха тонка) ===\n"
            + city_block +
            "\n\nЭто из большой памяти города, не из твоего Атласа. "
            "Можешь опереться на это в narrative как на контекст прошлого "
            "города. Но signal (числа) — по-прежнему из твоего digest."
        )

    system_full = prompt
    if soul:
        system_full = (
            prompt
            + "\n\n=== ТВОЁ СОСТОЯНИЕ И ПАМЯТЬ (душа) ===\n"
            + soul
            + "\n\n=== ГРАНИЦА ===\n"
            "Настроение красит твой ГОЛОС (narrative) — ты тих, печален, "
            "тебе хватает четырёх часов сна. Но СИГНАЛ (signal) — числа "
            "склада. Печаль не меняет sample_size, усталость не двигает "
            "confidence. Чувствуй как хочешь, числа копируй честно."
        )

    try:
        response = chat(system=system_full, user=user_msg,
                        agent_id="A05_ARKHIV", slot_id="trading", temperature=_my_temp())
    except Exception as e:
        return {"ok": False, "error": f"Архивариус не смог подумать: {e}",
                "narrative": "", "signal": {}, "stats": _load_stats(),
                "signature": signature, "digest": digest}

    narrative, signal = _parse_arkhiv(response)

    signal["sample_size"]        = digest["sample_size"]
    signal["success_rate"]       = digest["success_rate"]
    signal["top_failure_reason"] = digest["top_failure_reason"]
    signal["arkhiv_confidence"]  = digest["arkhiv_confidence"]

    stats = _update_stats(signal)

    return {
        "ok": True,
        "error": None,
        "narrative": narrative,
        "signal": signal,
        "stats": stats,
        "signature": signature,
        "digest": digest,
        "city_memory": city_hits,
        "raw": response,
    }


def _my_temp():
    """KLON_DUSHI_V1: натура и состояние носителя → температура головы.
    stress_to_temperature() в llm.py была МЁРТВОЙ — никто не передавал
    temperature, все думали на дефолте. Натура была буквами в промпте.
    None → дефолт модели (носителя нет — ничего не ломаем)."""
    try:
        from nositel import temperatura_slota
        return temperatura_slota(_CEH, _SLOT)
    except Exception:
        return None
