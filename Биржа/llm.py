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


# ══ KLOD_STROGIY_V1 ═══════════════════════════════════════════════
# Строгие провайдеры (Anthropic) отказывают там, где снисходительные
# (Google) догадываются. Две мелочи ниже — вся разница.

def _polnaya_zhaloba(r) -> str:
    """Настоящая причина отказа, а не отписка OpenRouter.

    В теле ответа лежит error.message (коротко, часто бесполезно:
    «Provider returned error») и error.metadata.raw — ДОСЛОВНО то,
    что сказал провайдер. Раньше брали только первое.
    """
    try:
        d = r.json()
    except Exception:
        return (r.text or "")[:800] or f"HTTP {r.status_code}"

    err = d.get("error")
    if not isinstance(err, dict):
        return (str(err) if err else (r.text or "")[:800]) or f"HTTP {r.status_code}"

    kuski = []
    soobshchenie = str(err.get("message") or "").strip()
    if soobshchenie:
        kuski.append(soobshchenie)

    meta = err.get("metadata")
    if isinstance(meta, dict):
        if meta.get("provider_name"):
            kuski.append(f"провайдер: {meta['provider_name']}")
        if meta.get("raw"):
            kuski.append(f"дословно: {str(meta['raw'])[:700]}")
        for _k in ("reasons", "flagged_input", "provider_response"):
            if meta.get(_k):
                kuski.append(f"{_k}: {str(meta[_k])[:300]}")

    if err.get("code") is not None:
        kuski.append(f"код: {err['code']}")

    return " · ".join(kuski) or (r.text or "")[:800] or f"HTTP {r.status_code}"


def _temp_pod_model(t):
    """Потолок температуры у провайдеров разный.

    Anthropic: строго 0..1 — выше кидает 400 ещё на входе.
    Google/OpenAI: до 2.0. Натура жителя (stress_to_temperature)
    доходит до 1.2 — значит нервный трейдер на Клоде не отвечал
    ВООБЩЕ. Прижимаем только там, где это закон провайдера.
    """
    if t is None:
        return t
    try:
        model = (_CURRENT_MODEL or "").lower()
        if "anthropic" in model or "claude" in model:
            return min(float(t), 1.0)
    except Exception:
        pass
    return t


# ══ KLYUCHI_LATINICEY_V1 ══════════════════════════════════════════
# Клод (и стандарт вообще) требует, чтобы имена полей в описании руки
# были латиницей: '^[a-zA-Z0-9_.-]{1,64}$'. Город говорит по-русски —
# значит переводим на проводе, а не внутри дома. Туда — латиницей,
# обратно — как было.

_RUS_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_skazali_pro_latinicu = False


def _v_latinicu(s: str) -> str:
    """Русское имя поля → допустимое латинское. Таблица, не выдумка."""
    out = []
    for ch in (s or ""):
        nizh = ch.lower()
        if nizh in _RUS_LAT:
            out.append(_RUS_LAT[nizh])
        elif ch.isascii() and (ch.isalnum() or ch in "_.-"):
            out.append(ch)
        else:
            out.append("_")
    itog = "".join(out).strip("_")
    return (itog or "arg")[:64]


def _uzel_na_latinicu(uzel, karta_poley: dict) -> None:
    """Перевести ключи properties (и вложенные) на месте."""
    if not isinstance(uzel, dict):
        return
    props = uzel.get("properties")
    if isinstance(props, dict):
        novye, staroe_v_novoe = {}, {}
        for k, v in props.items():
            nk = _v_latinicu(k)
            while nk in novye:
                nk = (nk + "_")[:64]
            novye[nk] = v
            staroe_v_novoe[k] = nk
            if nk != k:
                karta_poley[nk] = k
        uzel["properties"] = novye
        treb = uzel.get("required")
        if isinstance(treb, list):
            uzel["required"] = [staroe_v_novoe.get(x, x) for x in treb]
        for v in novye.values():
            if isinstance(v, dict):
                _uzel_na_latinicu(v, karta_poley)
                _uzel_na_latinicu(v.get("items"), karta_poley)


def _shema_na_latinicu(tools_schema):
    """(схема для провода, карта обратного перевода).

    Схема НЕ портится: работаем на глубокой копии. Если всё и так
    латиницей — возвращаем как было, без копирования.
    """
    global _skazali_pro_latinicu
    if not tools_schema:
        return tools_schema, {}

    nado = False
    for t in tools_schema:
        fn = (t or {}).get("function") or {}
        if not str(fn.get("name", "")).isascii():
            nado = True
        par = fn.get("parameters") or {}
        for k in (par.get("properties") or {}):
            if not str(k).isascii():
                nado = True
    if not nado:
        return tools_schema, {}

    import copy
    novaya = copy.deepcopy(tools_schema)
    imena, polya = {}, {}
    skolko = 0
    for t in novaya:
        fn = (t or {}).get("function") or {}
        rodnoe_imya = str(fn.get("name", ""))
        karta_poley = {}
        _uzel_na_latinicu(fn.get("parameters"), karta_poley)
        if karta_poley:
            polya[rodnoe_imya] = karta_poley
            skolko += len(karta_poley)
        if not rodnoe_imya.isascii():
            novoe = _v_latinicu(rodnoe_imya)
            fn["name"] = novoe
            imena[novoe] = rodnoe_imya
            polya[rodnoe_imya] = karta_poley

    if not _skazali_pro_latinicu:
        _skazali_pro_latinicu = True
        print(f"[РУКИ] ключи полей едут на провод латиницей "
              f"({skolko} шт.) — домой вернутся русскими")
    return novaya, {"imena": imena, "polya": polya}


def _ruka_obratno(imya: str, args, karta):
    """Имя руки и ключи — обратно в русские, до исполнения."""
    if not karta:
        return imya, args
    rodnoe = (karta.get("imena") or {}).get(imya, imya)
    perevod = (karta.get("polya") or {}).get(rodnoe) or {}
    if perevod and isinstance(args, dict):
        args = {perevod.get(k, k): v for k, v in args.items()}
    return rodnoe, args


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
    # KRAYNIYE_TOCHKI_V1: было 3 — на матрёшку Шефа (зигзаг целиком →
    # волна C внутри него → её третья волна) этого не хватает: три-
    # четыре растяжки подряд, каждая с картинкой. На старом потолке
    # трейдер упирался на середине и отвечал недосмотрев.
    max_tool_rounds: int = 12,
    temperature: Optional[float] = None,
    on_tool_call: Optional[Callable] = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
    knowledge_source: str = "internal",
    executors: Optional[dict] = None,       # RUKI_TREYDERA_V1
    history: Optional[list] = None,         # RUKA_MAYAKA_V1
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
    # RUKA_MAYAKA_V1: история разговора — как в chat(). Мозг конторы
    # передаёт её всегда; без этого он терял руки на каждом ответе.
    if history:
        for _m in history:
            if _m.get("role") in ("user", "assistant") and _m.get("content"):
                messages.append({"role": _m["role"], "content": _m["content"]})
    messages.append({"role": "user", "content": user})

    # RUKI_TREYDERA_V1: список рук был зашит здесь намертво — только
    # поиск Маяка. Значит своей руки не мог завести никто, кроме
    # Архива. Теперь вызывающий передаёт свои; встроенная остаётся.
    tool_executors = {
        "web_search": lambda args: _exec_tavily_search(args.get("query", "")),
    }
    if executors:
        tool_executors.update(executors)

    # KLYUCHI_LATINICEY_V1
    tools_schema, _karta_ruk = _shema_na_latinicu(tools_schema)

    tool_calls_made = 0

    for round_num in range(max_tool_rounds + 1):
        payload = {
            "model": _CURRENT_MODEL,
            "messages": messages,
            "max_tokens": LLM_MAX_TOKENS,   # LLM_MAX_TOKENS_V1
        }
        if temperature is not None:
            payload["temperature"] = _temp_pod_model(temperature)   # KLOD_STROGIY_V1

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
            err = _polnaya_zhaloba(r)   # KLOD_STROGIY_V1
            print(f"[LLM] ✕ OpenRouter [{r.status_code}] "
                  f"модель={_CURRENT_MODEL} :: {err}")
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
        # KLOD_STROGIY_V1: сказал словами — кладём слова; промолчал —
        # не кладём ничего. Пустой текст строгий провайдер не примет,
        # а выдумывать за трейдера слова мы не будем.
        _ego_otvet = {"role": "assistant", "tool_calls": tool_calls}
        _ego_slovo = (msg.get("content") or "").strip()
        if _ego_slovo:
            _ego_otvet["content"] = _ego_slovo
        messages.append(_ego_otvet)

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"].get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = {}
            # KLYUCHI_LATINICEY_V1: домой — русскими
            fn_name, fn_args = _ruka_obratno(fn_name, fn_args, _karta_ruk)

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
        payload_final["temperature"] = _temp_pod_model(temperature)   # KLOD_STROGIY_V1

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
        payload["temperature"] = _temp_pod_model(temperature)   # KLOD_STROGIY_V1

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
        err_msg = _polnaya_zhaloba(r)   # KLOD_STROGIY_V1
        print(f"[LLM] ✕ OpenRouter [{r.status_code}] "
              f"модель={_CURRENT_MODEL} :: {err_msg}")
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


# ── OBRAZCY_V_ZNANIYA_V1: образцы идут со знаниями, не с кадром ──
# Образцы в одном сообщении с кадром модель смешивала и описывала
# образец вместо своего рынка. Теперь они — часть «базы знаний» в
# начале разговора, как учебник; кадр остаётся один в вопросе.
def _znaniya_s_obrazcami(knowledge: str, knowledge_images=None):
    if not knowledge_images:
        return f"БАЗА ЗНАНИЙ:\n{knowledge}"
    kuski = [{"type": "text", "text": f"БАЗА ЗНАНИЙ:\n{knowledge}"},
             {"type": "text", "text":
              "ОБРАЗЦЫ ИЗ УЧЕБНИКА. Это НЕ твой рынок и НЕ сегодняшний "
              "кадр — так выглядит правило. Твой кадр придёт позже, в "
              "вопросе, отдельно."}]
    for img in knowledge_images:
        b64 = img.get("base64", "")
        if not b64:
            continue
        kuski.append({"type": "text",
                      "text": f"[Образец: {img.get('name', 'образец')}]"})
        kuski.append({"type": "image_url", "image_url": {
            "url": f"data:{img.get('mime_type', 'image/png')};base64,{b64}"}})
    return kuski


def chat_with_images(system: str, user_text: str, images: Optional[list] = None,
                     knowledge: str = "", history: Optional[list] = None,
                     temperature: Optional[float] = None,
                     agent_id: str = "unknown", slot_id: str = "unknown",
                     knowledge_source: str = "internal",
                     knowledge_images: Optional[list] = None) -> str:
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
    if knowledge or knowledge_images:   # OBRAZCY_V_ZNANIYA_V1
        messages.append({"role": "user", "content":
                         _znaniya_s_obrazcami(knowledge, knowledge_images)})
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
        payload["temperature"] = _temp_pod_model(temperature)   # KLOD_STROGIY_V1

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
        err_msg = _polnaya_zhaloba(r)   # KLOD_STROGIY_V1
        print(f"[LLM] ✕ OpenRouter [{r.status_code}] "
              f"модель={_CURRENT_MODEL} :: {err_msg}")
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


# ═══════════════════════════════════════════════════════════
# КАРТИНКА И РУКИ ВМЕСТЕ (RUKI_TREYDERA_V1)
# ═══════════════════════════════════════════════════════════
# Было две двери и ни одной нужной: chat_with_images — кадр без рук,
# chat_with_tools — руки без кадра. А трейдеру нужно и то, и другое:
# он смотрит на картинку и по ней просит числа. Дверь одна.
def chat_with_images_and_tools(
    system: str,
    user_text: str,
    images: Optional[list] = None,
    knowledge: str = "",
    tools_schema: Optional[list] = None,
    executors: Optional[dict] = None,
    max_tool_rounds: int = 12,      # KRAYNIYE_TOCHKI_V1
    temperature: Optional[float] = None,
    history: Optional[list] = None,
    on_tool_call: Optional[Callable] = None,
    agent_id: str = "unknown",
    slot_id: str = "unknown",
    knowledge_source: str = "internal",
    knowledge_images: Optional[list] = None,
) -> str:
    """Разговор с кадром, где собеседник может сам просить математику.

    Руки исполняются здесь же и их ответы возвращаются в тот же
    разговор, поэтому он видит и картинку, и числа, которые запросил
    ПО ЭТОЙ картинке. Не попросил — ничего лишнего не считали.
    """
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}",
               "Content-Type": "application/json"}

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    if knowledge or knowledge_images:   # OBRAZCY_V_ZNANIYA_V1
        messages.append({"role": "user", "content":
                         _znaniya_s_obrazcami(knowledge, knowledge_images)})
        messages.append({"role": "assistant",
                         "content": "Принял базу знаний. Готов к работе."})
    if history:
        for m in history:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"]})

    user_content: list = []
    for img in (images or []):
        b64 = img.get("base64", "")
        if not b64:
            continue
        mime = img.get("mime_type", "image/png")
        user_content.append({"type": "image_url",
                             "image_url": {"url": f"data:{mime};base64,{b64}"}})
        user_content.append({"type": "text",
                             "text": f"[Изображение: {img.get('name', 'кадр')}]"})
    user_content.append({"type": "text", "text": user_text})
    messages.append({"role": "user", "content": user_content})

    # KLYUCHI_LATINICEY_V1
    tools_schema, _karta_ruk = _shema_na_latinicu(tools_schema)

    ruki = dict(executors or {})
    sdelano = 0
    # RUKI_NE_TERYAT_SLOVO_V1: последнее, что собеседник сказал СЛОВАМИ.
    # Он может писать текст в том же ответе, где просит руку, — и
    # раньше этот текст выбрасывался, если круг кончался.
    posledneye_slovo = ""
    zvali_ruki: list = []          # за чем бегал по кругу

    for _krug in range(max_tool_rounds + 1):
        payload: dict = {"model": _CURRENT_MODEL, "messages": messages,
                         "max_tokens": LLM_MAX_TOKENS}
        if temperature is not None:
            payload["temperature"] = _temp_pod_model(temperature)   # KLOD_STROGIY_V1
        if tools_schema and sdelano < max_tool_rounds:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"
        elif tools_schema:
            # RUKI_NE_TERYAT_SLOVO_V1: раньше мы просто молча убирали
            # руки и ждали, что собеседник догадается. Он не
            # догадывался — просил снова. Теперь говорим прямо.
            messages.append({
                "role": "user",
                "content": ("Рук больше не будет — предел на этот взгляд "
                            "исчерпан. Ответь тем, что уже видишь: "
                            "словами и своим JSON, как обычно.")})

        r = _post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json_payload=payload, proxies=proxies,
            timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            err = _polnaya_zhaloba(r)   # KLOD_STROGIY_V1
            print(f"[LLM] ✕ OpenRouter [{r.status_code}] "
                  f"модель={_CURRENT_MODEL} :: {err}")
            raise RuntimeError(f"OpenRouter [{r.status_code}]: {err}")

        data = r.json()
        msg = (data.get("choices") or [{}])[0].get("message", {}) or {}

        if not msg.get("tool_calls"):
            content = msg.get("content") or ""
            if not content.strip():
                # RUKA_SRABOTALA_OTVET_PUST_V1: рассказ не дописался.
                # Если руки в этом заходе УЖЕ отработали — дело
                # сделано: приказ лежит на табло, счёт посчитан.
                # Перезаходить заново незачем: это лишний кадр и
                # лишнее обращение к модели на каждом таком баре.
                # Берём последнее сказанное словами (город его и
                # так помнит — RUKI_NE_TERYAT_SLOVO_V1), а нет
                # его — идём с пустым рассказом.
                if sdelano or zvali_ruki:
                    content = (posledneye_slovo or "").strip() or "{}"
                    print(f"[РУКИ] рассказ не дописался, но руки "
                          f"отработали ({sdelano}) — иду с тем, "
                          f"что есть")
                else:
                    # Рук не было и сказать нечего — это правда
                    # пустой ответ, как и раньше.
                    raise RuntimeError(
                        "Модель вернула пустой ответ (кадр+руки)")
            usage = data.get("usage", {})
            _ledger.record(agent_id=agent_id, slot_id=slot_id,
                           model=payload["model"],
                           prompt_tokens=usage.get("prompt_tokens", 0),
                           completion_tokens=usage.get("completion_tokens", 0),
                           call_type="chat_with_images_and_tools",
                           knowledge_source=knowledge_source)
            return content

        # RUKI_NE_TERYAT_SLOVO_V1: запомнить слово, сказанное вместе с
        # просьбой о руке. Оно и есть ответ, если круг кончится.
        _skazal_seychas = (msg.get("content") or "").strip()
        if _skazal_seychas:
            posledneye_slovo = _skazal_seychas

        # KLOD_STROGIY_V1: см. выше — пустого текста в разговоре быть
        # не должно, а придуманного за трейдера тем более.
        _ego_otvet = {"role": "assistant", "tool_calls": msg["tool_calls"]}
        if _skazal_seychas:
            _ego_otvet["content"] = _skazal_seychas
        messages.append(_ego_otvet)
        for tc in msg["tool_calls"]:
            imya = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            # KLYUCHI_LATINICEY_V1: домой — русскими
            imya, args = _ruka_obratno(imya, args, _karta_ruk)
            # RUKA_PO_SMYSLU_V1: прощаем кириллические двойники и
            # мелкие опечатки в имени руки — см. _nayti_ruku ниже.
            ruka, imya_tochno = _nayti_ruku(ruki, imya)
            if imya_tochno and imya_tochno != imya:
                imya = imya_tochno
            zvali_ruki.append(imya)
            # RUKI_NE_TERYAT_SLOVO_V1: заход считаем ВСЕГДА. Раньше
            # счётчик рос только на найденной руке — и звонок в пустоту
            # тратил заход, не двигая счётчик. Круг выкручивался
            # вхолостую и упирался в предел, ни разу его не увеличив.
            sdelano += 1
            if ruka:
                try:
                    otvet = str(ruka(args))
                except Exception as e:
                    otvet = f"рука {imya} сорвалась: {e}"
                print(f"[РУКА] 🖐 {imya}({args}) → {len(otvet)} симв. "
                      f"({sdelano}/{max_tool_rounds})")
            else:
                otvet = (f"Такой руки нет: {imya}. Больше её не проси — "
                         f"её не появится.")
                print(f"[РУКА] ✕ {imya} — такой руки нет "
                      f"({sdelano}/{max_tool_rounds})")
            if on_tool_call:
                try:
                    on_tool_call(imya, args, otvet)
                except Exception:
                    pass
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": otvet})
            # RASTYAZHKA_V1: рука вернула метку кадра — досылаем саму
            # КАРТИНКУ отдельным сообщением. В ответ руки изображение
            # не положить, а трейдеру нужно увидеть, а не прочитать.
            if isinstance(otvet, str) and otvet.startswith("[КАДР: "):
                try:
                    import base64 as _b64
                    from pathlib import Path as _P
                    _put = _P(otvet[7:otvet.index("]")])
                    if _put.exists():
                        _b = _b64.b64encode(_put.read_bytes()).decode("ascii")
                        messages.append({"role": "user", "content": [
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/png;base64,{_b}"}},
                            {"type": "text",
                             "text": "Вот картинка, которую ты попросил(а). "
                                     "Смотри."}]})
                        print(f"[РУКА] 🖼 дослал кадр: {_put.name}")
                except Exception as _ek:
                    print(f"[РУКА] кадр не дослался: {_ek}")

    # RUKI_NE_TERYAT_SLOVO_V1: круг кончился. Раньше здесь терялось
    # всё, что собеседник успел сказать, и в отчёт уходила заглушка
    # вместо слов трейдера. Слово дороже нашей аккуратности.
    if posledneye_slovo:
        print(f"[РУКИ] круг кончился ({sdelano}/{max_tool_rounds}), "
              f"беру последнее сказанное словами")
        return posledneye_slovo
    _skolko = {}
    for _i in zvali_ruki:
        _skolko[_i] = _skolko.get(_i, 0) + 1
    _spisok = ", ".join(f"{k}×{v}" for k, v in
                        sorted(_skolko.items(), key=lambda x: -x[1]))
    print(f"[РУКИ] ⚠️  круг кончился и НИ СЛОВА не сказано. "
          f"Звали: {_spisok or 'ничего'}")
    return (f"(промолчал: круг рук кончился, слов не было. "
            f"Звал: {_spisok or 'ничего'})")


# RUKI_TREYDERA_V1 - marker

# RUKA_MAYAKA_V1 - marker

# RASTYAZHKA_V1 - marker

# KRAYNIYE_TOCHKI_V1 - marker

# RUKI_NE_TERYAT_SLOVO_V1 - marker


# ═══════════════════════════════════════════════════════════════
# RUKA_PO_SMYSLU_V1 — имя руки ищем по смыслу, а не по точной букве
# ═══════════════════════════════════════════════════════════════
# Модель говорит по-русски и иногда соскальзывает на кириллицу внутри
# латинского имени: `stol_nсetazhe` вместо `stol_na_etazhe` (шестой
# символ — кириллическая «с», глазом неотличима). Строгий ruki.get()
# на этом ронял вызов, и трейдер честно отвечал «такой руки нет».
# Здесь три шага: точно → нормализованно → ближайшее с высоким
# порогом. Выдумать руку, которой нет, эти шаги не могут.

_GOMOGLIFY = str.maketrans({
    "а": "a", "в": "b", "с": "c", "е": "e", "ё": "e", "н": "h", "к": "k",
    "м": "m", "о": "o", "р": "p", "т": "t", "у": "y", "х": "x",
    "ѕ": "s", "і": "i", "ј": "j",
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K", "М": "M",
    "О": "O", "Р": "P", "Т": "T", "У": "Y", "Х": "X",
})

_PORAG_SHODSTVA = 0.82   # ниже — не подставляем
_ZAPAS_NAD_VTOROY = 0.10  # лучшая должна заметно обойти вторую


def _norm_imya_ruki(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'").translate(_GOMOGLIFY).lower()
    return "".join(ch for ch in s if ch.isalnum())


def _nayti_ruku(ruki: dict, imya: str):
    """(рука, настоящее_имя) или (None, None). Не выдумывает."""
    ruka = ruki.get(imya)
    if ruka:
        return ruka, imya

    tseli = list(ruki.keys())
    if not tseli:
        return None, None

    # шаг 2: нормализованное совпадение
    n = _norm_imya_ruki(imya)
    for k in tseli:
        if _norm_imya_ruki(k) == n:
            print(f"[РУКА] ~ {imya} → понял как {k} (двойники букв)")
            return ruki[k], k

    # шаг 3: ближайшее по написанию, с порогом и запасом над второй
    try:
        import difflib
        pary = sorted(
            ((difflib.SequenceMatcher(None, n, _norm_imya_ruki(k)).ratio(), k)
             for k in tseli), reverse=True)
        luchshaya, vtoraya = pary[0], (pary[1] if len(pary) > 1 else (0.0, ""))
        if luchshaya[0] >= _PORAG_SHODSTVA and \
                (luchshaya[0] - vtoraya[0]) >= _ZAPAS_NAD_VTOROY:
            print(f"[РУКА] ~ {imya} → понял как {luchshaya[1]} "
                  f"({luchshaya[0]:.2f})")
            return ruki[luchshaya[1]], luchshaya[1]
    except Exception as e:
        print(f"[РУКА] поиск по смыслу сорвался: {e}")

    return None, None

# RUKA_PO_SMYSLU_V1 - marker
