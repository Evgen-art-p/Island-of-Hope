# -*- coding: utf-8 -*-
# ARHIVARIUS_MOZG_V1
"""
МОЗГ МЕСТА «АРХИВАРИУС» (контора Биржи) — разговор с тем, кто сидит (27.10).

СЛОВО ШЕФА 27.10
    «Арчи нет в кабинете Биржи — там так же пузырёк и чат должен, как с
    остальными, это важно; и опыт, петля — всё как полагается.»

ЧТО ЗДЕСЬ
    • chat_with_arkhiv — дверь разговора, которую кабинет уже знает (📚):
      житель на посту «архивариус биржи» говорит своим голосом (паспорт,
      его осмысления этой работы и полки — как у всех постов), а перед ним
      на столе — свежие разборы картотеки.
    • Разговор идёт в эпизод осмысления (раз в пять разговоров — что понял
      о своей работе), как у Ректора и Хранителя.
    Торговать нечем и незачем: Совет архивариуса не будит.
"""
import json
import sys
from pathlib import Path

_SLOT_DIR = Path(__file__).resolve().parent
_SLOT = _SLOT_DIR.name
_REPO = _SLOT_DIR.parents[5]
for _p in (str(_REPO / "Биржа"), str(_REPO / "ГОРОД")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

POST_ID = "контора__архивариус"
KARTOTEKA = _REPO / "GRONDHEIM_CITY" / "Биржа" / "картотека" / "разборы"
NA_STOL = 9000          # сколько знаков картотеки кладём на стол


def _rol() -> str:
    try:
        return (_SLOT_DIR / "промпт.md").read_text(encoding="utf-8")
    except Exception:
        return ""


def _dusha(klyuchi=None):
    """Душа жителя на посту + его осмысления этой работы и полки (как у всех)."""
    try:
        import rezidenty as _rz
        try:
            import osmyslenie as _om
            _om.KLYUCHI_SEYCHAS[POST_ID] = [str(k).lower() for k in (klyuchi or []) if k]
        except Exception:
            pass
        p, dom = _rz.lichnost_na_postu(POST_ID)
        if not p:
            return "", ""
        return _rz.sobrat_dushu(p), str(p.get("Official_Name") or "")
    except Exception as e:
        print(f"[АРХИВАРИУС] душа не собралась ({e})")
        return "", ""


def _kartoteka(msg: str) -> str:
    """Свежий разбор каждого жителя; тот, о ком спрашивают, — первым."""
    try:
        fayly = sorted(KARTOTEKA.glob("*.md"))
    except Exception:
        fayly = []
    m = (msg or "").lower()
    fayly.sort(key=lambda f: 0 if f.stem.lower() in m else 1)
    kuski, dl = [], 0
    for f in fayly:
        try:
            t = f.read_text(encoding="utf-8")
        except Exception:
            continue
        i = t.find("\n## ")
        if i < 0:
            continue
        j = t.find("\n## ", i + 4)
        kusok = f"=== КАРТОТЕКА · {f.stem} — последний разбор ===\n" + t[i + 1:(j if j > 0 else None)].strip()
        if dl + len(kusok) > NA_STOL:
            kusok = kusok[:max(0, NA_STOL - dl)]
        if kusok:
            kuski.append(kusok)
            dl += len(kusok)
        if dl >= NA_STOL:
            break
    return "\n\n".join(kuski) if kuski else "Картотека пока пуста — разборов ещё нет."


def chat_with_arkhiv(msg, last_run=None, dialog=None, rynok=None):
    """Разговор с архивариусом в кабинете Биржи."""
    imena = [f.stem for f in KARTOTEKA.glob("*.md")] if KARTOTEKA.is_dir() else []
    o_kom = [i for i in imena if i.lower() in str(msg or "").lower()]
    dusha, kto = _dusha(["разговор"] + o_kom)
    if not dusha:
        return "здесь вакансия — место архивариуса свободно."
    system = (dusha + "\n\n" + _rol() + "\n\nСейчас с тобой говорит Шеф в кабинете Биржи. "
              "Отвечай по картотеке и по своей работе. Числа и бары — только из "
              "картотеки; чего там нет — так и скажи, не придумывай.")
    istoriya = []
    for d in (dialog or [])[-9:-1]:
        rol = "Шеф" if d.get("role") == "user" else "я"
        istoriya.append(f"{rol}: {str(d.get('content') or '')[:600]}")
    user = (_kartoteka(msg) + "\n\n"
            + ("Разговор до этого:\n" + "\n".join(istoriya) + "\n\n" if istoriya else "")
            + f"Шеф: {msg}")
    try:
        import llm as _llm
        otvet = _llm.chat(system, user, agent_id=kto or "архивариус", slot_id="arhivarius",
                          temperature=0.5)
    except Exception as e:
        return f"⚠️ не смог ответить: {e}"
    otvet = str(otvet or "").strip()
    try:
        import osmyslenie as _om
        _om.epizod_razgovora(POST_ID, msg, otvet, "Шеф")
    except Exception as e:
        print(f"[ОСМЫСЛЕНИЕ] разговор архивариуса не лёг в эпизод ({e})")
    return otvet


# ARHIVARIUS_MOZG_V1 - marker


# ══ ARCHI_RUKI_V1 — руки архивариуса: читать все доки и отвечать справкой ══
# Слово Шефа 28.10: «чтобы он мог любое в файлах прогонов, логов, отчётов, по
# журналам и дневникам читать, анализировать и выдавать отчёт на вопросы».
# Только чтение. Ответ — ещё и файлом в Брат/ответы_архивариуса/.
import re as _re_ar
from datetime import datetime as _dt_ar

_AR_KORNI = (_REPO / "GRONDHEIM_CITY" / "Биржа", _REPO / "GRONDHEIM_CITY" / "жители",
             _REPO / "Брат")
_AR_TEKST = {".md", ".txt", ".jsonl", ".json", ".log"}
_AR_MIMO = {"__pycache__", ".git", "node_modules", "котировки"}
_AR_OTVETY = _REPO / "Брат" / "ответы_архивариуса"
_AR_MAKS = 7000          # знаков в одном ответе руки
_AR_SHEMA = [
    {"type": "function", "function": {
        "name": "spisok_progonov",
        "description": ("Какие прогоны есть: папка, цех, свежие сверху, с шапкой отчёта "
                        "(место, кто сидел, период). Начинай с этого, если вопрос про прогон."),
        "parameters": {"type": "object", "properties": {
            "цех": {"type": "string", "description": "необязательно: хаос_дубль, торговый_хаос…"},
            "сколько": {"type": "integer", "description": "по умолчанию 10"}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "nayti",
        "description": ("Найти слова в документах: в каких файлах и строках встречаются. "
                        "Отдаёт путь, номер строки и саму строку. «где» сужает поиск по "
                        "части пути — номер прогона, имя жителя, «лог», «отчёт», «D02». "
                        "Несколько слов через | — найдёт строки с любым из них; через "
                        "пробел — строку целиком, как написано."),
        "parameters": {"type": "object", "properties": {
            "что": {"type": "string", "description": "например «2018.08.20» или «РЕШИЛ — ЗАКРЫЛ»"},
            "где": {"type": "string", "description": "необязательно: часть пути"},
            "сколько": {"type": "integer", "description": "по умолчанию 40, не больше 150"}},
            "required": ["что"]}}},
    {"type": "function", "function": {
        "name": "prochitat",
        "description": ("Прочитать кусок файла с номерами строк. Путь — как в ответе nayti "
                        "или spisok_progonov."),
        "parameters": {"type": "object", "properties": {
            "файл": {"type": "string", "description": "путь от корня города"},
            "с": {"type": "integer", "description": "с какой строки, по умолчанию 1"},
            "сколько": {"type": "integer", "description": "строк, по умолчанию 80, не больше 250"}},
            "required": ["файл"]}}},
]


def _ar_put(p: Path) -> str:
    try:
        return p.resolve().relative_to(_REPO.resolve()).as_posix()
    except Exception:
        return str(p)


def _ar_mozhno(p: Path) -> bool:
    try:
        r = p.resolve()
    except Exception:
        return False
    if r.suffix.lower() not in _AR_TEKST or any(c in _AR_MIMO for c in r.parts):
        return False
    return any(str(r).startswith(str(k.resolve())) for k in _AR_KORNI if k.exists())


def _ar_fayly(gde: str = ""):
    g = str(gde or "").strip().lower()
    for k in _AR_KORNI:
        if not k.exists():
            continue
        for f in k.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in _AR_TEKST:
                continue
            if any(c in _AR_MIMO for c in f.parts):
                continue
            if g and g not in _ar_put(f).lower():
                continue
            try:
                if f.stat().st_size > 30_000_000:
                    continue
            except Exception:
                continue
            yield f


def _ar_spisok(args):
    a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
    ceh = str(a.get("цех") or "").strip()
    try:
        n = max(1, min(40, int(a.get("сколько") or 10)))
    except Exception:
        n = 10
    tseha = _REPO / "GRONDHEIM_CITY" / "Биржа" / "цеха"
    papki = []
    for c in (tseha.iterdir() if tseha.exists() else []):
        if ceh and c.name != ceh:
            continue
        pr = c / "прогоны"
        if pr.is_dir():
            papki += [d for d in pr.iterdir() if d.is_dir()]
    papki.sort(key=lambda d: d.name, reverse=True)
    L = [f"=== ПРОГОНЫ · свежие сверху ({min(n, len(papki))} из {len(papki)}) ==="]
    for d in papki[:n]:
        shapka = ""
        o = d / "отчёт.md"
        if o.is_file():
            try:
                with open(o, encoding="utf-8") as fh:
                    stroki = [s.strip() for _, s in zip(range(25), fh) if s.strip()]
                shapka = " · ".join(stroki[:4])[:300]
            except Exception:
                pass
        fayly = ", ".join(sorted(x.name for x in d.iterdir() if x.is_file()))
        L.append(f"{_ar_put(d)} — файлы: {fayly}" + (f"\n    {shapka}" if shapka else ""))
    return "\n".join(L)


def _ar_nayti(args):
    a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
    chto = str(a.get("что") or "").strip()
    if not chto:
        return "что искать — не сказано"
    try:
        n = max(1, min(150, int(a.get("сколько") or 40)))
    except Exception:
        n = 40
    slova = [s.strip().lower() for s in chto.split("|") if s.strip()]
    nashlos, vsego, faylov = [], 0, 0
    for f in _ar_fayly(a.get("где")):
        faylov += 1
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for i, s in enumerate(fh, 1):
                    sl = s.lower()
                    if any(w in sl for w in slova):
                        vsego += 1
                        if len(nashlos) < n:
                            nashlos.append(f"{_ar_put(f)}:{i}: {s.strip()[:220]}")
        except Exception:
            continue
    if not nashlos:
        return (f"«{chto}» не нашёл (просмотрено файлов: {faylov}"
                + (f", где: «{a.get('где')}»" if a.get("где") else "") + ").")
    out = (f"=== НАЙДЕНО «{chto}»: строк {vsego}, показываю {len(nashlos)} ===\n"
           + "\n".join(nashlos))
    if vsego > len(nashlos):
        out += "\n(есть ещё — сузь «где» или прочитай кусок файла)"
    return out[:_AR_MAKS]


def _ar_prochitat(args):
    a = {str(k).strip().lower(): v for k, v in (args or {}).items()}
    put = str(a.get("файл") or "").strip().strip("/").replace("\\", "/")
    f = _REPO / put
    if not f.is_file():
        kand = [x for x in _ar_fayly() if _ar_put(x).endswith(put)] if put else []
        if len(kand) == 1:
            f = kand[0]
        else:
            return f"файла «{put}» нет" + (f" (похожих {len(kand)} — уточни путь)" if kand else "")
    if not _ar_mozhno(f):
        return "этот файл мне читать нельзя: только документы, не код и не котировки"
    try:
        s0 = max(1, int(a.get("с") or 1))
        n = max(1, min(250, int(a.get("сколько") or 80)))
    except Exception:
        s0, n = 1, 80
    L = [f"=== {_ar_put(f)} · строки {s0}–{s0 + n - 1} ==="]
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            vsego = 0
            for i, s in enumerate(fh, 1):
                vsego = i
                if s0 <= i < s0 + n:
                    L.append(f"{i}: {s.rstrip()[:400]}")
        L.append(f"(всего строк в файле: {vsego})")
    except Exception as e:
        return f"не прочитался: {e}"
    return "\n".join(L)[:_AR_MAKS]


_AR_RUKI = {"spisok_progonov": _ar_spisok, "nayti": _ar_nayti, "prochitat": _ar_prochitat}

_AR_PRAVILA = (
    "\n\n=== ТВОИ РУКИ: ЧИТАТЬ ДОКУМЕНТЫ ГОРОДА ===\n"
    "Когда Шеф (или Брат через Шефа) спрашивает про прогоны, логи, отчёты, журналы, "
    "дневники — ищи сам: spisok_progonov, nayti, prochitat. Сначала найди, где лежит, "
    "потом читай кусками; целиком большие логи не читай.\n"
    "ПРАВИЛА ОТВЕТА:\n"
    "1) Каждый факт — с источником в скобках: (путь:строка).\n"
    "2) Числа, даты, слова жителя и города — дословно, как в файле; важные строки "
    "приводи цитатой.\n"
    "3) Не нашёл — так и скажи, что искал и где. Не додумывай.\n"
    "4) Своё мнение — отдельно и помечай «моё мнение».\n"
    "5) Коротко и по делу: справка, а не рассказ.\n"
)


def _ar_sohranit(vopros: str, otvet: str, kto: str) -> str:
    try:
        _AR_OTVETY.mkdir(parents=True, exist_ok=True)
        imya = _dt_ar.now().strftime("%Y%m%d_%H%M%S")
        slovo = _re_ar.sub(r"[^\w]+", "_", str(vopros or ""))[:40].strip("_")
        f = _AR_OTVETY / f"{imya}_{slovo or 'вопрос'}.md"
        f.write_text(f"# Ответ архивариуса ({kto or 'архивариус'}) · {imya}\n\n"
                     f"## Вопрос\n\n{vopros}\n\n## Ответ\n\n{otvet}\n", encoding="utf-8")
        return _ar_put(f)
    except Exception as e:
        print(f"[АРХИВАРИУС] ответ файлом не лёг ({e})")
        return ""


def chat_with_arkhiv(msg, last_run=None, dialog=None, rynok=None):   # noqa: F811
    """Разговор с архивариусом: картотека на столе + руки читать документы."""
    imena = [f.stem for f in KARTOTEKA.glob("*.md")] if KARTOTEKA.is_dir() else []
    o_kom = [i for i in imena if i.lower() in str(msg or "").lower()]
    dusha, kto = _dusha(["разговор"] + o_kom)
    if not dusha:
        return "здесь вакансия — место архивариуса свободно."
    system = (dusha + "\n\n" + _rol() + "\n\nСейчас с тобой говорит Шеф в кабинете Биржи. "
              "Отвечай по картотеке, по документам города и по своей работе. Числа и бары — "
              "только из картотеки и документов; чего там нет — так и скажи, не придумывай."
              + _AR_PRAVILA)
    istoriya = []
    for d in (dialog or [])[-9:-1]:
        r = d.get("role")
        c = str(d.get("content") or "")[:1500]
        if r in ("user", "assistant") and c:
            istoriya.append({"role": r, "content": c})
    user = _kartoteka(msg) + f"\n\nШеф: {msg}"
    try:
        import llm as _llm
        def _s_logom(imya, fn):
            def _f(args):
                print(f"[АРХИВАРИУС] ✋ {imya} {json.dumps(args or {}, ensure_ascii=False)[:160]}")
                return fn(args)
            return _f
        otvet = _llm.chat_with_tools(
            tools_schema=_AR_SHEMA,
            executors={k: _s_logom(k, v) for k, v in _AR_RUKI.items()},
            system=system, user=user, history=istoriya,
            agent_id=kto or "архивариус", slot_id="arhivarius", temperature=0.3)
    except Exception as e:
        print(f"[АРХИВАРИУС] руки не подключились ({e}) — отвечаю по картотеке")
        try:
            import llm as _llm
            otvet = _llm.chat(system, user, agent_id=kto or "архивариус",
                              slot_id="arhivarius", temperature=0.5)
        except Exception as e2:
            return f"⚠️ не смог ответить: {e2}"
    otvet = str(otvet or "").strip()
    try:
        import osmyslenie as _om
        _om.epizod_razgovora(POST_ID, msg, otvet, "Шеф")
    except Exception as e:
        print(f"[ОСМЫСЛЕНИЕ] разговор архивариуса не лёг в эпизод ({e})")
    gde = _ar_sohranit(msg, otvet, kto)
    if gde:
        otvet += f"\n\n📄 ответ лежит: {gde}"
    return otvet


# ARCHI_RUKI_V1 - marker
