# -*- coding: utf-8 -*-
"""
СТОРОЖ (STRAZH_UNIVERSAL_V1)
════════════════════════════════════════════════════════════════
Тихий наблюдатель без LLM. Стоит рядом с Ситом 1 (математика ядра,
без модели) — но не ищет НОВУЮ точку разворота, а сторожит УЖЕ
НАЙДЕННУЮ, на каждом следующем баре, пока не подтвердится нужное
условие или точка не протухнет по сроку.

Найден по разговору с Шефом 18.07: один и тот же узор нужен
и Гансу/Бруту (ждут первый фрактал ПОСЛЕ точки Искры), и Василию
(ждёт откат до уровня Брута) — бар по свойствам один и тот же,
меняется только «чья точка-якорь» и «какое условие ищем».

Ничего здесь не решает за трейдеров. Сторож не выносит вердикт
«входить/не входить» — он только докладывает ФАКТ: условие
подтвердилось на таком-то баре, или ещё нет, или срок истёк.
Что делать с этим фактом — решают агенты (LLM), не сторож.

НЕ ТРОГАЕТ: council.py, tester_express.py, hooks.py. Это отдельный
чистый модуль, testable в изоляции. Куда его вживлять — отдельный
разговор с Шефом, ПОСЛЕ того как он увидит, что сторож правда
работает на живых данных.
"""

from williams_core import detect_fractals


def nablyudat_za_tochkoy(bars: list[dict], indeks_tochki: int, storona: str,
                          uslovie_fn, maks_barov: int | None = None) -> dict:
    """
    Универсальный сторож. Идёт по барам ПОСЛЕ indeks_tochki (сама точка
    не проверяется — она уже случилась), на каждом баре зовёт
    uslovie_fn(bars, i, indeks_tochki, storona) — если та вернула не None,
    значит условие подтвердилось на этом баре.

    bars           — полная история (список словарей date/open/high/low/close)
    indeks_tochki  — индекс бара точки-якоря (точка Искры, или точка Брута)
    storona        — "up" (бычий разворот/сетап) или "down" (медвежий)
    uslovie_fn     — функция условия, что именно ищем (см. ниже)
    maks_barov     — срок жизни точки в барах. None = сторожить до конца
                     истории (используется в бэктесте на всей истории;
                     для живого города Шеф задаёт разумный срок отдельно)

    Возвращает:
      {"found": True,  "bar_index": i, "bars_waited": N, ...поля condition...}
      {"found": False, "expired": True,  "bars_waited": N}   — протухла
      {"found": False, "expired": False, "bars_waited": N}   — история кончилась,
                                                                 условие не настало
    """
    n = len(bars)
    if indeks_tochki < 0 or indeks_tochki >= n:
        return {"found": False, "expired": False, "bars_waited": 0,
                "error": "indeks_tochki вне истории"}

    for i in range(indeks_tochki + 1, n):
        bars_waited = i - indeks_tochki
        if maks_barov is not None and bars_waited > maks_barov:
            return {"found": False, "expired": True, "bars_waited": bars_waited}

        result = uslovie_fn(bars, i, indeks_tochki, storona)
        if result is not None:
            return {"found": True, "expired": False,
                     "bar_index": i, "bars_waited": bars_waited, **result}

    return {"found": False, "expired": False, "bars_waited": n - 1 - indeks_tochki}


# ════════════════════════════════════════════════════════════
# УСЛОВИЕ 1 — для Ганса/Брута: первый фрактал ПОСЛЕ точки Искры
# ════════════════════════════════════════════════════════════
def uslovie_novy_fraktal(bars: list[dict], i: int, indeks_tochki: int,
                          storona: str) -> dict | None:
    """
    storona "up"   (Искра поймала дно волны C, ждём разворот вверх)
             → ищем ПЕРВЫЙ up-фрактал после точки — вершина волны 1.
    storona "down" → ищем ПЕРВЫЙ down-фрактал после точки.

    Фрактал Вильямса подтверждается только через 2 бара ПОСЛЕ своей
    вершины (5-барный, lookback=2) — поэтому раньше i = indeks_tochki+3
    он в принципе не может появиться. Это не костыль, это канон.
    """
    okno = bars[indeks_tochki:i + 1]
    if len(okno) < 5:
        return None

    fr = detect_fractals(okno, lookback=2)
    tselevoy = fr["last_up"] if storona == "up" else fr["last_down"]
    if tselevoy is None:
        return None

    global_idx = tselevoy["bar_index"] + indeks_tochki
    if global_idx <= indeks_tochki:
        return None   # фрактал ДО или НА точке Искры — не наш, это старьё

    # подтверждаем именно на баре, где фрактал СТАЛ виден (global_idx + 2),
    # не раньше — иначе соврём себе, что узнали раньше рынка
    if i < global_idx + 2:
        return None

    return {"fraktal_price": tselevoy["price"],
            "fraktal_date":  tselevoy["date"],
            "fraktal_bar_index": global_idx}


# ════════════════════════════════════════════════════════════
# УСЛОВИЕ 2 — для Василия — УБРАНО (STRAZH_BEZ_CHERNOVIKA_V1)
# ════════════════════════════════════════════════════════════
# Здесь жила `uslovie_otkat_do_urovnya` — черновик под гипотезу
# «Василий ждёт касания уровня Брута». Гипотеза ОТМЕНЕНА: Василий —
# не сторож на уровень, а МИНИ-ИСКРА (§5к/§5л, подтверждено картинкой
# Котина §5н). Волна 2, приближенная на меньший ТФ, сама разворачивается
# в свою структуру со своим разворотом на конце — Василий ловит ЕГО.
#
# Это отдельная стройка, сопоставимая по объёму с самой Искрой, и она
# НЕ начата. Когда начнётся — это будет не условие для сторожа, а
# собственный мини-спуск + свежий Морж + свежий Паникёр на своём
# масштабе. Держать здесь тупиковый черновик — только путать.

# STRAZH_BEZ_CHERNOVIKA_V1 - marker
