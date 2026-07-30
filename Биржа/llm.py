# -*- coding: utf-8 -*-
# BIRZHA_LLM_PORT_V1
"""
llm.py — LLM-клиент Биржи. Перенесён из -2 (studio/llm.py) МЕХАНИЗМОМ:
вся логика chat()/chat_with_tools()/chat_with_images()/retry — БЕЗ
ИЗМЕНЕНИЙ (систему торговли не переделывали — это касается и того, как
агенты думают). Изменилось только ДВА места:
  1. Конфиг (ключ/модель/прокси/таймаут) — берём из os.environ напрямую
     (главный main.py уже делает load_dotenv() из корня репо), вместо
     studio.config, которого в новом городе нет.
  2. billing_ledger — свой, локальный (Биржа/billing_ledger.py),
     вместо общестудийного.

Ничего в самом ПОВЕДЕНИИ модели (retry, temperature, tool use, vision)
не тронуто — это то самое "систему торговли то мы не переделывали".
"""
import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Callable, Any  # LLM_TYPING_V1 / LLM_TYPING_V2

import billing_ledger as _ledger  # свой, локальный (Биржа/billing_ledger.py)

# ── Конфиг — читаем окружение напрямую (main.py уже сделал load_dotenv) ──
# Подстраховка: если этот модуль когда-нибудь запустят не через main.py,
# подтягиваем .env из корня репо сами (тот же приём, что был в studio.config).
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env_file_if_needed() -> None:
    if os.getenv("OPENROUTER_API_KEY"):
        return  # уже загружено (main.py) — не лезем
    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and not os.getenv(key):
                os.environ[key] = value
    except Exception:
        pass


_load_env_file_if_needed()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

# BIRZHA_MODEL_SEL_V1: одна модель на весь Совет разом (решение Шефа —
# "проще"), не per-slot. Кабинет (ui_torg.py) меняет её через set_model()
# из выбора в шапке; агенты её не выбирают сами, только исполняют.
_CURRENT_MODEL = OPENROUTER_MODEL


def set_model(model_id: str) -> None:
    """Кабинет вызывает это при смене селектора в шапке. Пустое значение —
    не трогаем текущую (защита от случайного сброса на дефолт)."""
    global _CURRENT_MODEL
    if model_id:
        _CURRENT_MODEL = model_id


def get_model() -> str:
    """Что сейчас реально летит в OpenRouter — для UI/логов."""
    return _CURRENT_MODEL
PROXY_URL = os.getenv("PROXY_URL", "")
TAVILY_KEY = os.getenv("TAVILY_KEY", "")
HTTP_TIMEOUT = 90

# LLM_MAX_TOKENS_V1: ПОТОЛОК ОТВЕТА. Раньше max_tokens не задавался ВООБЩЕ —
# OpenRouter брал максимум модели (65536 у deepseek-v4-pro) и требовал
# денег под весь потолок ЗАРАНЕЕ. Прогон падал с 402 «can only afford
# 11021», хотя реальный ответ агента — 200-600 слов.
# 4000 — запас ×5 к самому длинному ответу Совета. Мало? Подними в .env:
#     LLM_MAX_TOKENS=8000
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))


# ══ RETRY HELPER ══════════════════════════════════════════════════
# Ошибка 10054 (Connection Reset) = OpenRouter/прокси сбросил сокет.
# Это временная сетевая проблема — ретраим с паузой.
# НЕ ретраим: 400 Bad Request, 401 Unauthorized, 429 Rate Limit.

_RETRY_DELAYS = [0, 2, 5]  # секунды перед попыткой 1, 2, 3

def _post_with_retry(url: str, headers: dict, json_payload: dict,
                     proxies: Optional[dict] = None, timeout: Optional[int] = None) -> requests.Response:
    """requests.post с тремя попытками при сетевых ошибках (10054, ConnectionReset)."""
    last_err = None
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        if delay > 0:
            print(f"[RETRY] Сеть упала — ждём {delay}с (попытка {attempt}/{len(_RETRY_DELAYS)})...")
            time.sleep(delay)
        try:
            r = requests.post(url, headers=headers, json=json_payload,
                              proxies=proxies, timeout=timeout)
            return r  # успех — возвращаем ответ как есть
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as e:
            last_err = e
            print(f"[RETRY] Попытка {attempt} упала: {type(e).__name__}")
            # Не ретраим если это явно не сетевая проблема
            if "ProxyError" in type(e).__name__:
                raise  # прокси не настроен — ретрай бессмысленен
        except requests.exceptions.Timeout:
            raise  # таймаут — ретраить не имеет смысла
    raise requests.exceptions.ConnectionError(
        f"OpenRouter недоступен после {len(_RETRY_DELAYS)} попыток: {last_err}"
    )
# ═════════════════════════════════════════════════════════════════


def stress_to_temperature(stress: float = 0.0, light: float = 0.8) -> float:
    """Вычисляет temperature LLM из ДНК-состояния агента.

    stress=0.0, light=0.8 → 0.46 (спокойный, точный)
    stress=0.5, light=0.5 → 0.80 (нормальный)
    stress=0.8, light=0.3 → 1.01 (нервничает, хаотичный)
    """
    base = 0.5 + stress * 0.6
    light_mod = (0.5 - light) * 0.15
    temp = base + light_mod
    return round(max(0.3, min(1.2, temp)), 2)


# ═══════════════════════════════════════════════════════════
# PIPELINE TOOL USE — web_search для агентов (Маяк Пробуждения)
# ═══════════════════════════════════════════════════════════

PIPELINE_WEB_SEARCH_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Поиск актуальной информации в интернете через Маяк Пробуждения. "
                "Используй для поиска трендов, новостей, актуальных форматов, "
                "вирусных роликов, статистики платформ."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос — конкретный, на языке платформы"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def _exec_tavily_search(query: str) -> str:
    """Синхронный поиск через Tavily API."""
    if not TAVILY_KEY:
        return "[Маяк недоступен: TAVILY_KEY не настроен]"

    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_KEY,
                "query": query,
                "max_results": 5,
                "include_answer": True,
                "search_depth": "basic",
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        out = ""
        if data.get("answer"):
            out += f"Краткий ответ: {data['answer']}\n\n"
        for i, result in enumerate(data.get("results", []), 1):
            out += (
                f"[{i}] {result.get('title', '')}\n"
                f"{result.get('url', '')}\n"
                f"{result.get('content', '')[:500]}\n\n"
            )
        return out or "Ничего не найдено."

    except requests.exceptions.Timeout:
        return "[Маяк: таймаут поиска — Tavily не ответил за 30 сек]"
    except Exception as e:
        return f"[Маяк: ошибка поиска — {e}]"


def chat_with_tools(
    system: str,
    user: str,
    knowledge: str = "",
    tools_schema: Optional[list] = None,
    max_tool_rounds: int = 3,
    temperature: Optional[float] = None,
    on_tool_call: Optional[Callable] = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
    knowledge_source: str = "internal",
) -> str:
    """Вызов LLM с поддержкой Tool Use (синхронный).

    Цикл:
      1. Отправляем сообщение с tools schema
      2. Если модель вызвала tool — исполняем, отправляем результат
      3. Повторяем до max_tool_rounds или пока модель не ответит текстом
    """
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})
    messages.append({"role": "user", "content": user})

    tool_executors = {
        "web_search": lambda args: _exec_tavily_search(args.get("query", "")),
    }

    tool_calls_made = 0

    for round_num in range(max_tool_rounds + 1):
        payload = {
            "model": _CURRENT_MODEL,
            "messages": messages,
            "max_tokens": LLM_MAX_TOKENS,   # LLM_MAX_TOKENS_V1
        }
        if temperature is not None:
            payload["temperature"] = temperature

        if tools_schema and tool_calls_made < max_tool_rounds:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"

        try:
            r = _post_with_retry(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json_payload=payload,
                proxies=proxies,
                timeout=HTTP_TIMEOUT,
            )
        except Exception as e:
            raise RuntimeError(f"OpenRouter Tool Use: {e}")

        if r.status_code != 200:
            try:
                err = r.json().get("error", {}).get("message", r.text[:300])
            except Exception:
                err = r.text[:300]
            raise RuntimeError(f"OpenRouter [{r.status_code}]: {err}")

        data = r.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        if not msg.get("tool_calls"):
            content = msg.get("content", "")
            if not content or not content.strip():
                raise RuntimeError("Модель вернула пустой ответ (tool use loop)")

            usage = data.get("usage", {})
            _ledger.record(
                agent_id=agent_id,
                slot_id=slot_id,
                model=payload["model"],
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                call_type="chat_with_tools",
                knowledge_source="beacon" if tool_calls_made > 0 else knowledge_source,
            )

            return content

        tool_calls = msg["tool_calls"]
        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"].get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = {}

            executor = tool_executors.get(fn_name)
            if executor:
                result = executor(fn_args)
                tool_calls_made += 1
                print(
                    f"[МАЯК] 🔍 {fn_name}({fn_args.get('query', '')[:80]}) "
                    f"→ {len(result)} симв. (раунд {tool_calls_made}/{max_tool_rounds})"
                )
            else:
                result = f"Неизвестный инструмент: {fn_name}"

            if on_tool_call:
                try:
                    on_tool_call(fn_name, fn_args, result)
                except Exception:
                    pass

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    payload_final = {
        "model": _CURRENT_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,   # LLM_MAX_TOKENS_V1
    }
    if temperature is not None:
        payload_final["temperature"] = temperature

    try:
        r = _post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json_payload=payload_final,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        usage = data.get("usage", {})
        _ledger.record(
            agent_id=agent_id,
            slot_id=slot_id,
            model=payload_final["model"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            call_type="chat_with_tools",
            knowledge_source="beacon" if tool_calls_made > 0 else knowledge_source,
        )

        return content or "[Модель не дала финальный ответ после tool calls]"
    except Exception as e:
        raise RuntimeError(f"Финальный вызов после tools: {e}")


def chat(system: str, user: str, knowledge: str = "", history: Optional[list] = None,
         temperature: Optional[float] = None,
         agent_id: str = "unknown", slot_id: str = "unknown",
         knowledge_source: str = "internal") -> str:
    """
    Отправляет запрос к LLM.

    Args:
        system: системный промпт
        user: текущее сообщение пользователя
        knowledge: база знаний (опционально)
        history: история диалога [{"role": "user"/"assistant", "content": "..."}]
    """
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

    messages = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user})

    payload = {
        "model": _CURRENT_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,   # LLM_MAX_TOKENS_V1
    }
    if temperature is not None:
        payload["temperature"] = temperature

    _ctx_size = sum(len(str(m.get('content', ''))) for m in messages)
    # NATURA_V_TEMPERATURU_V1: температура в логе. Раньше строка была одинакова у
    # всех — потому что temperature никто не передавал и натура не влияла
    # на голову. Честно показываем и тех, кого ещё не подключили.
    _t = (f" | t={temperature}" if temperature is not None
          else " | t=дефолт (натура не подключена)")
    print(f"[LLM] → {agent_id} | контекст: {_ctx_size} симв | "
          f"модель: {_CURRENT_MODEL[:30]}{_t} | потолок: {LLM_MAX_TOKENS}")
    try:
        r = _post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json_payload=payload,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")

    if r.status_code != 200:
        try:
            err_data = r.json()
            err_msg = err_data.get("error", {}).get("message", r.text[:300])
        except Exception:
            err_msg = r.text[:300] if r.text else f"HTTP {r.status_code}"
        raise RuntimeError(f"OpenRouter API [{r.status_code}]: {err_msg}")

    raw_text = r.text.strip()
    if not raw_text:
        raise RuntimeError("OpenRouter вернул пустой ответ (пустое тело)")

    try:
        data = r.json()
    except Exception as e:
        preview = raw_text[:200]
        raise RuntimeError(f"Ответ не JSON. Первые 200 символов:\n{preview}")

    if "choices" not in data or not data["choices"]:
        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err))
            raise RuntimeError(f"OpenRouter error: {msg}")
        raise RuntimeError(f"Нет 'choices' в ответе. Ключи: {list(data.keys())}")

    content = data["choices"][0].get("message", {}).get("content")

    usage = data.get("usage", {})
    _ledger.record(
        agent_id=agent_id,
        slot_id=slot_id,
        model=payload["model"],
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        call_type="chat",
        knowledge_source=knowledge_source,
    )

    if content is None:
        finish = data["choices"][0].get("finish_reason", "unknown")
        raise RuntimeError(f"Модель не вернула content (finish_reason={finish})")

    if not content.strip():
        raise RuntimeError("Модель вернула пустую строку")

    return content


def chat_with_images(system: str, user_text: str, images: Optional[list] = None,
                     knowledge: str = "", history: Optional[list] = None,
                     temperature: Optional[float] = None,
                     agent_id: str = "unknown", slot_id: str = "unknown",
                     knowledge_source: str = "internal") -> str:
    """
    Отправляет запрос с изображениями (vision).

    Args:
        system: системный промпт
        user_text: текстовое сообщение
        images: список dict [{"base64": "...", "mime_type": "image/png", "name": "file.png"}, ...]
        knowledge: база знаний
        history: история диалога
    """
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

    # LLM_TYPING_V2: content здесь честно смешанный — обычная реплика
    # несёт строку, сообщение с картинкой ниже несёт список блоков
    # (протокол vision OpenRouter/OpenAI). dict[str, Any] называет то,
    # что уже происходит в рантайме, а не выдумывает новое поведение.
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    if knowledge:
        messages.append({"role": "user", "content": f"БАЗА ЗНАНИЙ:\n{knowledge}"})
        messages.append({"role": "assistant", "content": "Принял базу знаний. Готов к работе."})

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    user_content = []

    if images:
        for img in images:
            b64 = img.get("base64", "")
            mime = img.get("mime_type", "image/png")
            name = img.get("name", "image")

            if not b64:
                continue

            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64}"
                }
            })
            user_content.append({
                "type": "text",
                "text": f"[Изображение: {name}]"
            })

    user_content.append({
        "type": "text",
        "text": user_text
    })

    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": _CURRENT_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,   # LLM_MAX_TOKENS_V1
    }
    if temperature is not None:
        payload["temperature"] = temperature

    try:
        r = _post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json_payload=payload,
            proxies=proxies,
            timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ProxyError as e:
        raise RuntimeError(f"Прокси недоступен ({PROXY_URL}): {e}")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Таймаут {HTTP_TIMEOUT}s — OpenRouter не ответил")
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"Нет соединения с OpenRouter: {e}")

    if r.status_code != 200:
        try:
            err_data = r.json()
            err_msg = err_data.get("error", {}).get("message", r.text[:300])
        except Exception:
            err_msg = r.text[:300] if r.text else f"HTTP {r.status_code}"
        raise RuntimeError(f"OpenRouter API [{r.status_code}]: {err_msg}")

    raw_text = r.text.strip()
    if not raw_text:
        raise RuntimeError("OpenRouter вернул пустой ответ")

    try:
        data = r.json()
    except Exception as e:
        raise RuntimeError(f"Ответ не JSON: {raw_text[:200]}")

    if "choices" not in data or not data["choices"]:
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")
        raise RuntimeError(f"Нет choices в ответе")

    content = data["choices"][0].get("message", {}).get("content")

    usage = data.get("usage", {})
    _ledger.record(
        agent_id=agent_id,
        slot_id=slot_id,
        model=payload["model"],
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        call_type="chat_with_images",
        knowledge_source=knowledge_source,
    )

    if not content or not content.strip():
        raise RuntimeError("Модель вернула пустой ответ")

    return content

# LLM_TYPING_V1 — маркер идемпотентности

# LLM_TYPING_V2 — маркер идемпотентности
