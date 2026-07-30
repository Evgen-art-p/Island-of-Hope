# -*- coding: utf-8 -*-
# BIRZHA_LLM_PORT_V1
"""
billing_ledger.py — учёт реальных вызовов LLM Биржи.

Перенесено ИЗ -2 (studio/billing_ledger.py) МЕХАНИЗМОМ, не байт-в-байт:
там record() писал в общий billing_ledger.jsonl всей студии (все цеха
разом). Здесь — свой файл, только для Биржи (Закон Фрактала: источник
свой, механизм тот же). Ничего не решает и не считает деньги — только
честно пишет факт вызова (сколько токенов, какая модель, кто звал).

Файл: Биржа/данные/billing_ledger.jsonl (одна строка — один вызов).
"""
import json
from datetime import datetime
from pathlib import Path

_LEDGER_PATH = Path(__file__).resolve().parent / "данные" / "billing_ledger.jsonl"


def record(agent_id: str, slot_id: str, model: str,
           prompt_tokens: int = 0, completion_tokens: int = 0,
           call_type: str = "chat", knowledge_source: str = "internal") -> None:
    """Дописывает одну строку факта вызова. Никогда не падает наружу —
    учёт не должен ронять реальный прогон агента."""
    try:
        _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now().isoformat(),
            "agent_id": agent_id,
            "slot_id": slot_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "call_type": call_type,
            "knowledge_source": knowledge_source,
        }
        with _LEDGER_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[BILLING] ⚠️ запись не удалась (не критично): {e}")
