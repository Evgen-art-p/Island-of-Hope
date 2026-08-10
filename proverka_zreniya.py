# -*- coding: utf-8 -*-
# PROVERKA_ZRENIYA_V1
"""
ДОХОДИТ ЛИ КАРТИНКА ДО МОДЕЛИ.

ЗАЧЕМ. Ученик уверенно описывает то, чего на картинке нет, и два раза
подряд по-разному. Так ведёт себя не слабое зрение, а ОТСУТСТВИЕ
зрения: если картинку выбросили по дороге, модели остаётся один текст
запроса — а там есть имя файла. Она берёт имя и сочиняет вокруг него.

ЧТО ДЕЛАЕТ, по порядку:
  1. Спрашивает у OpenRouter, умеет ли выбранная модель смотреть
     вообще (в её паспорте перечислено, что она принимает на вход).
  2. Шлёт КОНТРОЛЬНУЮ картинку, которую рисует сам: белый лист,
     на нём одно крупное слово. Ответ проверяется на это слово.
     Не назвала — картинка не дошла, и дело не в сложности графика.
  3. Шлёт твою настоящую страницу книги тем же способом, каким её
     шлёт Академия — тот же формат сообщения, буква в букву.

ЗАПУСК из корня репо — БЕЗ КИРИЛЛИЦЫ в команде (терминал Windows её
режет), скрипт сам находит последнюю картинку в руде Академии:
    python proverka_zreniya.py
    python proverka_zreniya.py --model openai/gpt-4o
Нужна другая картинка — можно указать путь, но тогда кириллицу в нём
терминал может испортить:
    python proverka_zreniya.py --file <путь>
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif"}
# Латиницей: стандартный шрифт Pillow кириллицу не рисует — выйдут
# квадраты, и проверка соврёт на ровном месте.
KODOVOE_SLOVO = "GRONDHEIM"


def _env():
    """Читает .env из корня, если переменных нет в окружении."""
    key = os.getenv("OPENROUTER_API_KEY", "")
    proxy = os.getenv("PROXY_URL", "")
    f = Path(".env")
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k == "OPENROUTER_API_KEY" and not key:
                key = v
            if k == "PROXY_URL" and not proxy:
                proxy = v
    return key, (proxy or None)


def _kontrolnaya_kartinka() -> bytes:
    """Белый лист с одним крупным словом. Проще некуда — если модель
    не прочла это, значит картинки она не видит совсем."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return b""
    # Шрифт по умолчанию мелкий: пишем на маленьком холсте вплотную,
    # потом растягиваем — получается крупная надпись без внешних шрифтов.
    tmp = Image.new("RGB", (110, 20), "white")
    ImageDraw.Draw(tmp).text((6, 5), KODOVOE_SLOVO, fill="black")
    img = tmp.resize((800, 200), Image.LANCZOS)
    import io
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def _poslat(key, proxy, model, data: bytes, ext: str, vopros: str):
    """Шлёт ровно тем же способом, что и Академия."""
    import httpx
    url = f"data:{MIME.get(ext, 'image/png')};base64,{base64.b64encode(data).decode('ascii')}"
    payload = {"model": model, "messages": [
        {"role": "user", "content": [
            {"type": "text", "text": vopros},
            {"type": "image_url", "image_url": {"url": url}},
        ]}]}
    with httpx.Client(timeout=120, proxy=proxy) as c:
        r = c.post("https://openrouter.ai/api/v1/chat/completions",
                   headers={"Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"},
                   json=payload)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        j = r.json()
        if "error" in j:
            return None, f"ошибка API: {json.dumps(j['error'], ensure_ascii=False)[:300]}"
        return j["choices"][0]["message"]["content"], ""


RUDA = Path("GRONDHEIM_CITY") / "Академия" / "руда" / "изображения"


def _nayti_kartinku():
    """Ищет картинку сам — чтобы в команде не было ни одной кириллической
    буквы. Терминал Windows их режет, а Python внутри работает с ними
    спокойно. Берём самую свежую: её ученик и читал последней."""
    if not RUDA.exists():
        return None, f"нет папки {RUDA} — запускай из КОРНЯ репо"
    fajly = [f for f in RUDA.iterdir()
             if f.is_file() and f.suffix.lower() in MIME]
    if not fajly:
        return None, f"в {RUDA} нет ни одной картинки"
    return max(fajly, key=lambda f: f.stat().st_mtime), ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="", help="картинка (по умолчанию — свежая из руды)")
    ap.add_argument("--model", default="", help="какую модель проверяем")
    a = ap.parse_args()

    key, proxy = _env()
    if not key:
        print("✗ нет OPENROUTER_API_KEY (ни в окружении, ни в .env)")
        return 1

    if a.file:
        put = Path(a.file)
        if not put.exists():
            print(f"✗ нет файла: {put}")
            return 1
    else:
        put, err = _nayti_kartinku()
        if put is None:
            print(f"✗ {err}")
            return 1
        print(f"Беру свежую картинку из руды: {put.name}\n")

    try:
        import httpx
    except ImportError:
        print("✗ нет httpx:  pip install httpx")
        return 1

    model = a.model
    # ── 1. умеет ли модель смотреть ──────────────────────────
    print("① Проверяю паспорт модели у OpenRouter...")
    try:
        with httpx.Client(timeout=60, proxy=proxy) as c:
            r = c.get("https://openrouter.ai/api/v1/models",
                      headers={"Authorization": f"Bearer {key}"})
            spisok = r.json().get("data", [])
    except Exception as e:
        spisok = []
        print(f"   ⚠ список моделей не получил: {e}")

    if not model:
        print("   Модель не указана (--model). Вот те, что УМЕЮТ смотреть:")
        for m in spisok:
            vhod = (m.get("architecture") or {}).get("input_modalities") or []
            if "image" in vhod:
                print(f"     · {m['id']}")
        print("\n   Запусти ещё раз с --model <id>")
        return 0

    nashli = next((m for m in spisok if m.get("id") == model), None)
    if nashli:
        vhod = (nashli.get("architecture") or {}).get("input_modalities") or []
        umeet = "image" in vhod
        print(f"   {model}: принимает {vhod}")
        if not umeet:
            print("   ✗ ЭТА МОДЕЛЬ НЕ СМОТРИТ КАРТИНКИ.")
            print("     Вот и разгадка: картинку выбрасывают по дороге,")
            print("     модели остаётся имя файла — и она сочиняет вокруг него.")
            print("     Поставь в Академии модель из тех, что выше.")
            return 0
        print("   ✓ смотреть умеет — идём дальше")
    else:
        print(f"   ⚠ модели «{model}» в списке нет, проверяю вслепую")

    # ── 2. контрольная картинка ──────────────────────────────
    print("\n② Контрольная картинка (белый лист, одно слово)...")
    kontrol = _kontrolnaya_kartinka()
    if not kontrol:
        print("   ⚠ нет Pillow, пропускаю  (pip install pillow)")
    else:
        otvet, err = _poslat(key, proxy, model, kontrol, ".png",
                             "Какое слово написано на картинке? Ответь одним словом.")
        if err:
            print(f"   ✗ {err}")
            return 1
        print(f"   ответ: {otvet.strip()[:120]}")
        if KODOVOE_SLOVO.lower() in (otvet or "").lower():
            print("   ✓ слово названо — картинки ДОХОДЯТ")
        else:
            print("   ✗ слово НЕ названо — картинка до модели НЕ ДОШЛА.")
            print("     Дело не в сложности графика: она не видит вообще ничего.")
            return 0

    # ── 3. настоящая страница ────────────────────────────────
    print(f"\n③ Твоя страница ({put.name})...")
    otvet, err = _poslat(key, proxy, model, put.read_bytes(), put.suffix.lower(),
                         "Что изображено? Есть ли на картинке биржевой график "
                         "или столбики баров? Отвечай только по тому, что видишь.")
    if err:
        print(f"   ✗ {err}")
        return 1
    print("   ответ:")
    for s in (otvet or "").strip().splitlines():
        print("     " + s)
    print("\n   Если здесь она описала график и бары — зрение работает,")
    print("   и глюки были от модели без зрения. Если снова сочиняет при")
    print("   пройденной контрольной — тогда дело в самой странице:")
    print("   мелко, много деталей, надо крупнее или резать по частям.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
