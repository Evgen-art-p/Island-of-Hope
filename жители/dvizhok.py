# dvizhok.py — личный движок жителя. Лежит в доме жителя.
# ─────────────────────────────────────────────────────────────
# СУТЬ: орган дыхания. Не мозг (решает житель), не город (свой у каждого).
#   ВХОД (факт: контекст, сила, свежесть)
#     → через РУЧКИ жителя (DNA_Static из паспорта)
#     → ВДОХ: насколько вход тронул = f(сила, свежесть, ручки)
#     → сдвиг состояния (charge ±, к балансу)
#     → открывает глубину памяти по |charge|
#   Решение и выход — НЕ здесь (следующие камни). Движок только дышит.
#
# Прежде она — житель (ядро). Из ядра вдох. Ручки — её натура.
# TRI_ETAZHA_V1: три этажа разведены. Anchor_Points = РОД, не растёт.
#   Нажитое → 2_метки/metki.json. Момент → 3_маяки/mayaki.json.
# SUTOCHNY_TIK_V1: заряд тает по ВРЕМЕНИ, не только по вдоху. Обида
#   проходит от того, что прошла ночь. Полураспад = сутки ×
#   (1 + упрямство). Источник времени — _seychas(), одна точка
#   правды: подменишь на биржевые сессии — формула не тронется.
# PYLANCE_GIGIENA_V1: pattern: Optional[str] — тип больше не врёт.
# PAMYAT_ISKRA_V1 (27.07, слово Шефа): искра (тонус+сила) раньше
#   вычислялась и тут же выбрасывалась — использовалась только для
#   сдвига заряда, в память не попадала. Теперь оседает рядом с
#   фактом (Закон Меток: строка рядом с записью, не новая сущность).
#   Личная память жителя (sensory/resonance/archive) — НЕ рабочая
#   память (Стол Трейдера её не касается, разделение Шефа 27.07).
# `шесть·проверено·до·корня`
# ─────────────────────────────────────────────────────────────
import json
import math   # STOL_RAZNOE_V1
import re     # ARHIV_S_KLYUCHOM_V1
from typing import Optional   # PYLANCE_GIGIENA_V1
from pathlib import Path
from datetime import datetime, timezone
import os     # PAMYAT_BEZ_TISHINY_V1


# ═══════════════════════════════════════════════════════
# PAMYAT_BEZ_TISHINY_V1 (слово Шефа 17.10) — ПАМЯТЬ НЕ ТЕРЯЕТСЯ МОЛЧА
# ═══════════════════════════════════════════════════════
# Было три беды:
#   1. сбой записи глотался молча (except: pass) — снаружи «всё хорошо»;
#   2. файл, который не прочитался, считался ПУСТЫМ — и следующая
#      запись ложилась поверх, стирая всю память (свежую, метки, маяки);
#   3. файл писался прямо на место — оборвалась запись на середине,
#      и файл битый (а дальше — беда №2).
# Теперь: сбой — строкой в лог; битый файл перед перезаписью уходит
# копией в _ЧУЛАН/память/<житель>/ (не сберёгся — не пишем поверх);
# запись — сперва во временный файл, потом подмена одним шагом.
# Дыхание по-прежнему не роняем: память не должна валить разговор.
# ═══════════════════════════════════════════════════════

_PREDUPREZHDENO = set()   # что уже сказано в лог — не повторять на каждом баре


def _skazat(tekst: str, klyuch=None):
    """Строка в лог. С ключом — один раз за запуск города."""
    if klyuch is not None:
        if klyuch in _PREDUPREZHDENO:
            return
        _PREDUPREZHDENO.add(klyuch)
    try:
        print(f"[ПАМЯТЬ] ⚠️  {tekst}")
    except Exception:
        pass


def _atomarno(path, tekst: str):
    """Записать файл целиком или никак: сперва рядом во временный,
    потом подмена одним шагом. Оборвалось — старый файл цел.
    Windows не даёт подменить файл, который в этот миг кто-то читает, —
    тогда несколько коротких попыток, а в крайнем случае пишем прямо,
    как раньше (не хуже прежнего)."""
    import time as _time
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(tekst)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    for _ in range(8):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            _time.sleep(0.05)
    path.write_text(tekst, encoding="utf-8")
    try:
        tmp.unlink()
    except Exception:
        pass


def _chulan_pamyati(dom) -> Path:
    """_ЧУЛАН/память/<житель>/ в корне репо (там, где GRONDHEIM_CITY).
    Корень не нашёлся — рядом с домом, в папке _сломанное."""
    dom = Path(dom)
    for up in dom.parents:
        if (up / "GRONDHEIM_CITY").is_dir():
            return up / "_ЧУЛАН" / "память" / dom.name
    return dom / "_сломанное"


def _v_chulan(dom, path, prichina) -> str:
    """Копия битого файла — в чулан, ДО того как его перепишут.
    Одна копия на одно состояние файла (по времени изменения), чтобы
    повторные попытки не плодили дубли. Путь копии или "" — не вышло."""
    path = Path(path)
    try:
        st = path.stat()
    except Exception:
        return ""
    try:
        papka = _chulan_pamyati(dom)
        papka.mkdir(parents=True, exist_ok=True)
        metka = datetime.fromtimestamp(st.st_mtime).strftime("%Y%m%d_%H%M%S")
        kopiya = papka / f"{path.stem}__{metka}{path.suffix}"
        if not kopiya.exists():
            kopiya.write_bytes(path.read_bytes())
            _skazat(f"{Path(dom).name}: {path.name} не читается ({prichina}) — "
                    f"старое сбережено: {kopiya}")
        return str(kopiya)
    except Exception as e:
        _skazat(f"{Path(dom).name}: {path.name} не читается, и сберечь "
                f"не вышло ({e})")
        return ""

# PAMYAT_RABOTA_ZHIZN_V1: какой контекст считается РАБОТОЙ, а какой
# ЖИЗНЬЮ. Нужно затем, что за столом житель просит опыт — и должен
# получить практику, а не разговоры о холсте. У Нины 18.08 на запрос
# «Аллигатор открыт, но AO падает» поднялось 172 следа, и все до
# одного были беседами и учёбой: сделок у неё ноль.
# UCHYOBA_NA_STOLE_V1: делим НАТРОЕ, а не надвое. Вчера учёба попала
# в «не работу», и за столом трейдер перестал поднимать даже то, что
# разбирал с Ректором. А практики у него ноль — ни одна сделка ещё не
# закрылась. Значит учёба сейчас ЕДИНСТВЕННАЯ его опора, и отрезать
# её было худшим, что можно сделать.
#   «Без знаний опыта не получишь» — слово Шефа 18.08.
PRAKTIKA_KONTEKSTY = ("работа", "факт")
UCHEBNYE_KONTEKSTY = ("учёба", "учеба")
ZHIZNENNYE_KONTEKSTY = ("общение", "дом")

# За столом поднимается практика И учёба. Разговоры про холст остаются
# дома — им за столом делать нечего.
RABOCHIE_KONTEKSTY = PRAKTIKA_KONTEKSTY + UCHEBNYE_KONTEKSTY

# Старые записи контекста не имеют — разбираем по слою, как велит
# Закон Слоёв ниже. sensory остаётся неизвестным: туда падали сразу
# три контекста, и восстанавливать их гаданием мы не будем.
SLOY_KONTEKST = {"archive": "учёба", "resonance": "общение"}


# METKA_KAK_KLYUCH_V1: голос «откуда» → контекст.
# У МЕТОК И МАЯКОВ НЕТ НИ «контекста», НИ «слоя» — только «откуда»
# («рынок», «сделка», «учёба», «работа», профессия). Значит при любом
# запросе с фильтром они давали пустой контекст и отсеивались ЦЕЛИКОМ.
# А мост с Биржи всегда спрашивает рабочее — то есть ВЕСЬ торговый
# опыт жителя был невидим для его же рабочего поиска. Он копил то,
# чего потом не мог найти.
# Чиним ЧТЕНИЕ, а не запись: голос «рынок» остаётся голосом «рынок» —
# он нарочно отличает «что мне сказал рынок» от «что я вынес в
# монтажной», и житель вправе их столкнуть.
OTKUDA_KONTEKST = {
    "рынок": "работа", "сделка": "работа", "работа": "работа",
    "факт": "факт",
    "учёба": "учёба", "учеба": "учёба",
    "общение": "общение", "дом": "дом", "жизнь": "дом",
    # ARHIV_S_KLYUCHOM_V1: записи прогонов и выбор рабочего этажа —
    # это работа. Раньше голос «прогон» контекста не имел.
    "прогон": "работа", "решение": "работа",
}


def kontekst_zapisi(z: dict) -> str:
    """Откуда след. Нет пометки — берём по слою; потом по голосу
    «откуда» (метки и маяки живут только им); sensory неизвестен."""
    k = str(z.get("контекст") or "").strip()
    if k:
        return k
    k = SLOY_KONTEKST.get(str(z.get("слой") or ""), "")
    if k:
        return k
    # METKA_KAK_KLYUCH_V1: последняя опора — голос вывода. Незнакомый
    # голос (профессия, «сам») оставляем пустым, как было: гадать не
    # будем, лучше честное «следа нет».
    return OTKUDA_KONTEKST.get(str(z.get("откуда") or "").strip().lower(), "")


# контекст входа → в какой слой осядет (Закон Слоёв)
KONTEKST_SLOI = {
    "факт":     "sensory",    # сухой факт дня — свежее
    "работа":  "sensory",     # дело — свежее (потом архивируется)
    "общение": "resonance",   # с кем общалась — связи
    "учёба":   "archive",     # узнала — осело глубоко
    "дом":     "sensory",     # личное, свежее
}

# знак входа: что тянет вверх (+), что вниз (−)
# но РЕШАЕТ не это — это лишь куда качнуло маятник
def _znak(tonus: str) -> float:
    return {"плюс": 1.0, "минус": -1.0, "ровно": 0.0}.get(tonus, 0.0)


# OSTYVANIE_ZARYADA_V1: заряд тает к нулю с каждым вдохом, не застывает.
# Не по реальному времени — на фиксированный процент за вдох (иначе без
# диалога обида не пройдёт сама за неделю тишины). Упрямство держит
# заряд дольше: упрямый таёт медленнее.
OSTYVANIE_BAZA = 0.10   # базовый процент остывания за один вдох (10%)


class Dvizhok:
    """Личный движок одного жителя. Дышит его паспортом."""

    def __init__(self, dom: Path):
        self.dom = Path(dom)
        self.passport_path = self.dom / "passport.json"
        self.p = json.loads(self.passport_path.read_text(encoding="utf-8"))
        # РУЧКИ — из натуры жителя
        dna = self.p.get("DNA_Static", {})
        self.empathy    = dna.get("Empathy", 0.5)
        self.stubborn   = dna.get("Stubbornness", 0.5)
        self.resonance  = dna.get("Resonance_Frequency", 0.5)
        # СОСТОЯНИЕ — заряд. Если в паспорте нет — рождаем в покое (0.0).
        self.charge = self.p.get("_charge", 0.0)

    # ═══════════════════════════════════════════════════════
    # SUTOCHNY_TIK_V1 — ВРЕМЯ ОСТУЖАЕТ
    # ═══════════════════════════════════════════════════════
    # Раньше заряд таял ТОЛЬКО за вдох (10%). Нет событий → висит вечно:
    # Лока сидела +0.874 четвёртые сутки, а |заряд|>0.8 открывает архив —
    # максимальный аффект без выхода. Ловушка: чтобы остыть, надо трогать,
    # а тронешь — качнётся снова.
    #
    # Теперь: прошли сутки тишины — маятник сам качнулся к покою.
    # Обида проходит от того, что прошла ночь.
    #
    # Источник «сейчас» — реальные часы (решение Шефа, вариант А).
    # Захочешь городское время (по биржевым сессиям) — подмени _seychas(),
    # остальное не тронется.
    # ═══════════════════════════════════════════════════════

    POLURASPAD_CHASOV = 24.0   # сутки — база. Упрямство её растягивает.

    def _seychas(self) -> datetime:
        """Момент «сейчас». Одна точка правды о времени — чтобы потом
        подменить на городское/биржевое, не трогая формулу."""
        return datetime.now(timezone.utc)

    def _kogda_dyshal(self):
        """Момент последнего вдоха из паспорта. Нет метки — None
        (житель ещё не дышал, остужать нечего)."""
        ts = self.p.get("_charge_ts")
        if not ts:
            return None
        try:
            t = datetime.fromisoformat(str(ts))
            # старые записи бывают без зоны — считаем их UTC, не гадаем
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            return t
        except Exception:
            return None

    def ostyt_po_vremeni(self) -> dict:
        """Остывание за время тишины. Меняет self.charge В ПАМЯТИ.
        На диск НЕ пишет — это делает sохранить() (закон побочки).

        Полураспад: сутки × (1 + упрямство). Упрямый держит дольше:
          упрямство 0.1 → ~1.1 суток на половину
          упрямство 0.9 → ~2.5 суток (Илья, Брут — такие)
        Экспонента, не линейка: свежая рана болит сильно, старая тлеет.
        """
        bylo = self.charge
        if abs(bylo) < 0.001:
            return {"остыл": False, "причина": "и так в покое",
                    "было": bylo, "стало": bylo, "часов": 0.0}

        t0 = self._kogda_dyshal()
        if t0 is None:
            return {"остыл": False, "причина": "нет метки времени вдоха",
                    "было": bylo, "стало": bylo, "часов": 0.0}

        chasov = (self._seychas() - t0).total_seconds() / 3600.0
        if chasov <= 0:
            return {"остыл": False, "причина": "время не шло",
                    "было": bylo, "стало": bylo, "часов": 0.0}

        polur = self.POLURASPAD_CHASOV * (1.0 + self.stubborn)
        self.charge = bylo * (0.5 ** (chasov / polur))
        if abs(self.charge) < 0.01:
            self.charge = 0.0        # хвост не тянем — это покой

        return {"остыл": True, "было": round(bylo, 3),
                "стало": round(self.charge, 3),
                "часов": round(chasov, 1),
                "полураспад_ч": round(polur, 1)}

    def vdoh(self, kontekst: str, sila: float, svezhest: float, tonus: str = "ровно") -> dict:
        """Вдох: входящий факт проходит через ядро.
        сила 0..1, свежесть 0..1 (1=только что, 0=давно).
        Возвращает что стало — но НЕ решает за жителя."""
        # SUTOCHNY_TIK_V1: СПЕРВА остужает ВРЕМЯ. Житель, которого
        # тронули после недели тишины, приходит на вдох уже остывшим —
        # как живой. Раньше этого не было: заряд ждал следующего
        # события, даже если между ними прошли сутки.
        self.ostyt_po_vremeni()

        # OSTYVANIE_ZARYADA_V1: и ещё чуть — за сам вдох (маятник
        # качнулся к покою до нового толчка). Упрямый тает медленнее.
        _ostyv_koef = OSTYVANIE_BAZA * (1.0 - 0.7 * self.stubborn)
        self.charge *= (1.0 - _ostyv_koef)

        # насколько тронуло = сила × свежесть × резонанс ядра.
        # эмпатия усиливает удар (чужое чувствуется как своё).
        trogaet = sila * svezhest * (0.5 + self.resonance) * (0.5 + self.empathy)
        trogaet = min(1.0, trogaet)

        # сдвиг заряда: вдох даёт ЧАСТЬ, не всё разом — маятник копится,
        # не прыгает в край. Упрямство держит уже набранное (медленнее тает,
        # но и новый вход сдвигает осторожнее — натура устойчивая).
        VDOH_COEF = 0.35           # один вдох двигает максимум на треть
        sdvig = _znak(tonus) * trogaet * VDOH_COEF
        self.charge = max(-1.0, min(1.0, self.charge + sdvig))

        # глубина открытой памяти по |заряду| (стресс-шлюз)
        c = abs(self.charge)
        if c < 0.25:
            sloi = ["core"]
        elif c < 0.55:
            sloi = ["core", "sensory"]
        elif c < 0.8:
            sloi = ["core", "sensory", "resonance"]
        else:
            sloi = ["core", "sensory", "resonance", "archive"]

        # куда осело событие (по контексту)
        osel_v = KONTEKST_SLOI.get(kontekst, "sensory")

        return {
            "тронуло":     round(trogaet, 3),
            "заряд":       round(self.charge, 3),
            "открыто":     sloi,
            "осело_в":     osel_v,
            # PAMYAT_RABOTA_ZHIZN_V1: контекст доходит до записи.
            # Раньше он решал слой и терялся — и отделить работу от
            # жизни задним числом было нечем.
            "контекст":    kontekst,
            # PAMYAT_ISKRA_V1: тонус и сила искры раньше вычислялись и
            # тут же терялись (использовались только для сдвига заряда).
            # Теперь идут дальше — в запись памяти (_zapisat_sobytie) —
            # чтобы просев и поиск могли опираться на тепло момента,
            # не только на текст.
            "тонус":       tonus,
            "сила":        round(sila, 3),
        }

    def _zapisat_sobytie(self, sloy: str, fakt: str, vdoh_result: dict):
        """PAMYAT_SOBYTIY_V1: событие оседает в свой слой (sloy — из
        vdoh_result['осело_в'], уже посчитан по KONTEKST_SLOI).
        Без порога — пишем всё (мелкое 'привет' тоже часть памяти).
        PAMYAT_ISKRA_V1: тонус/сила идут рядом с фактом — Закон Меток
        (строка рядом с записью, не отдельная сущность)."""
        zapis = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "слой": sloy,
            "факт": fakt,
            "заряд": vdoh_result.get("заряд"),
            "тонус": vdoh_result.get("тонус"),
            "сила": vdoh_result.get("сила"),
        }
        try:
            # DVIZHOK_MKDIR_FIX_V1: каждый слой сам заводит свою папку —
            # раньше запись тихо проваливалась в except, если "sensory"/
            # "resonance"/"archive" ещё не были созданы при рождении
            # жителя (у настоящих резидентов это не всплывало — папки
            # заводятся при рождении, но память не должна на это надеяться).
            if sloy == "sensory":
                # sensory_memory.json — JSON-объект с массивом entries
                (self.dom / "sensory").mkdir(parents=True, exist_ok=True)
                p = self.dom / "sensory" / "sensory_memory.json"
                data = {"entries": []}
                if p.exists():
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        if not isinstance(data, dict) or not isinstance(
                                data.get("entries", []), list):
                            raise ValueError("не тот вид файла")
                    except Exception as _e_ch:
                        # PAMYAT_BEZ_TISHINY_V1: было — молча начать с
                        # пустого и записать ПОВЕРХ: вся свежая память
                        # пропадала. Теперь старое — копией в чулан;
                        # не сберёглось — поверх не пишем.
                        if not _v_chulan(self.dom, p, _e_ch):
                            return
                        data = {"entries": []}
                data.setdefault("entries", []).append(zapis)
                _atomarno(p, json.dumps(data, ensure_ascii=False, indent=2))
            elif sloy == "resonance":
                # event_log.jsonl — JSONL, дозапись строкой
                (self.dom / "resonance").mkdir(parents=True, exist_ok=True)
                p = self.dom / "resonance" / "event_log.jsonl"
                with open(p, "a", encoding="utf-8") as f:
                    f.write(json.dumps(zapis, ensure_ascii=False) + "\n")
            elif sloy == "archive":
                # archive.jsonl — JSONL, дозапись строкой
                (self.dom / "archive").mkdir(parents=True, exist_ok=True)
                p = self.dom / "archive" / "archive.jsonl"
                with open(p, "a", encoding="utf-8") as f:
                    f.write(json.dumps(zapis, ensure_ascii=False) + "\n")
        except Exception as _e_zap:
            # PAMYAT_BEZ_TISHINY_V1: дыхание не роняем — но и не молчим
            _skazat(f"{self.dom.name}: событие не записалось в {sloy} "
                    f"({_e_zap})")

    def vydoh_stol(self, fakt: str, vdoh_result: dict) -> dict:
        """Выдох: накрывает СТОЛ для решения жителя. НЕ решает сам.
        Стол = факт + кто она + что заряд открыл + личность (якоря/
        резонанс/натура — YAKORYA_V_PROMT_V1). Житель посмотрит и выберет."""
        self._zapisat_sobytie(vdoh_result.get("осело_в", "sensory"), fakt, vdoh_result)  # PAMYAT_SOBYTIY_V1
        return {
            "кто_я":          self.p.get("Official_Name"),
            "факт":           fakt,
            "заряд":          vdoh_result["заряд"],
            "открыто":        vdoh_result["открыто"],
            "ядро":           self.p.get("Core_Phrase", ""),
            # YAKORYA_V_PROMT_V1: те же поля, что правая колонка кабинета
            # показывает Шефу (update_viewer) — теперь и LLM их видит.
            "история":        self.p.get("Hidden_History", ""),
            "чувство":        self.p.get("Sensory_Response", ""),
            "якоря":          self.p.get("Anchor_Points", ""),
            "метки":          self._metki_v_stol(),   # TRI_ETAZHA_V1
            "черновики":      self.mayaki(),          # TRI_ETAZHA_V1
            "скрытый_вкус":   self.p.get("Hidden_Taste", ""),
            "тянет_к":        self.p.get("Pull_Vector", ""),
            # PATCH_DOM_V_DUSHU: дом — носится в себе ВСЕГДА, не по заряду
            # (часть личности, не слой памяти). Пусто, если ещё не
            # прописан(а) — стол пропустит пустое поле сам.
            "дом":            self.p.get("домашний_промпт", ""),
            "натура":         self.p.get("DNA_Static", {}),
        }

    # ── ЯКОРЯ: разделитель бывает ДВУХ видов ────────────────────────
    # Форма рождения писала литеральные два символа «\\» + «n», а не
    # перевод строки (проверено на паспорте Ильи 12.07). Читаем ОБА,
    # пишем ТЕМ ЖЕ, каким паспорт написан — иначе сломаем вид другим
    # читателям (кабинет, ui_zhitel). # DVIZHOK_YAKORYA_YADRO_V1
    _YAKOR_LIT = "\\n"      # литерал: обратный слэш + n

    def _yakorya_razdelitel(self, raw: str) -> str:
        """Каким разделителем ЖИВЁТ этот паспорт. Литерал — если он есть."""
        if self._YAKOR_LIT in (raw or ""):
            return self._YAKOR_LIT
        return "\n"

    def _yakorya_spisok(self, raw: str) -> list:
        """Якоря списком. Режет и по литералу, и по настоящему переводу."""
        s = (raw or "").replace(self._YAKOR_LIT, "\n")
        return [ln.strip() for ln in s.split("\n") if ln.strip()]

    def yadro(self) -> str:
        """ЯДРО живёт в РОЛИ (маске), не в Роде (Чертёж §1.5) — паспорт
        его не носит и носить не должен. Маска лежит в доме жителя,
        движок дотянется сам. Паспорт — фоллбэк. # DVIZHOK_YAKORYA_YADRO_V1"""
        try:
            mp = self.dom / "маски" / "работа" / "mask.json"
            if mp.exists():
                m = json.loads(mp.read_text(encoding="utf-8"))
                cp = (m.get("Core_Phrase") or "").strip()
                if cp:
                    return cp
        except Exception:
            pass
        return self.p.get("Core_Phrase", "") or ""

    def nakryt_stol_chisto(self) -> dict:
        """Стол БЕЗ дыхания: чистое чтение личности из паспорта — ноль
        записи в память, ноль vdoh_result. Для читающего конца, который
        зовётся часто (на каждый бар/взгляд): vydoh_stol туда нельзя, он
        пишет событие на каждый вызов. Те же поля личности, что vydoh_stol,
        минус побочка. Заряд отдаём на ЧТЕНИЕ (в __init__ уже загружен,
        диск не трогаем). # DVIZHOK_STOL_CHISTO_VYVOD_V1
        """
        # SUTOCHNY_TIK_V1: промпт должен видеть ЧЕСТНЫЙ заряд, а не
        # окаменевший с прошлой недели. Остужаем В ПАМЯТИ — на диск
        # НЕ пишем (контракт метода: чтение БЕЗ побочки). Осядет при
        # следующем настоящем вдохе.
        self.ostyt_po_vremeni()
        return {
            "кто_я":        self.p.get("Official_Name"),
            "заряд":        round(self.charge, 3),
            "ядро":         self.yadro(),   # DVIZHOK_YAKORYA_YADRO_V1: ядро из маски (Роль), не из Рода
            "история":      self.p.get("Hidden_History", ""),
            "чувство":      self.p.get("Sensory_Response", ""),
            # TRI_ETAZHA_V1: три этажа, три голоса
            "якоря":        self.p.get("Anchor_Points", ""),   # РОД — кто он ЕСТЬ
            "метки":        self._metki_v_stol(),              # НАЖИТОЕ — свежие,
                                                               # остальное по MEMORY_REQUEST
            "черновики":    self.mayaki(),                     # МАЯКИ — «замечаю за собой»
            "скрытый_вкус": self.p.get("Hidden_Taste", ""),
            "тянет_к":      self.p.get("Pull_Vector", ""),
            "дом":          self.p.get("домашний_промпт", ""),
            "натура":       self.p.get("DNA_Static", {}),
        }

    # ═══════════════════════════════════════════════════════
    # TRI_ETAZHA_V1 — ТРИ ЭТАЖА ПО ЗАКОНУ ЯДРА
    # ═══════════════════════════════════════════════════════
    # 1_якоря (Anchor_Points в паспорте) — РОД. Не меняется. Не пишем.
    # 2_метки (дом/2_метки/metki.json)   — НАЖИТОЕ. Растёт.
    # 3_маяки (дом/3_маяки/mayaki.json)  — МОМЕНТ. Гаснет (черновики).
    #
    # Раньше всё валилось в Anchor_Points — и род, и нажитое. Отсюда
    # лимит, вытеснение и ложная тревога «вторая профессия сотрёт
    # первую». Этаж И ЕСТЬ происхождение — изобретать было нечего.
    # ═══════════════════════════════════════════════════════

    METKI_CAP = 40      # меток живёт много — это вся трудовая жизнь
    METKI_V_STOL = 4    # а в промпт идут только свежие: стол маленький,
                        # остальное житель поднимет через MEMORY_REQUEST

    def _metki_path(self) -> Path:
        return self.dom / "2_метки" / "metki.json"

    def _mayaki_path(self) -> Path:
        return self.dom / "3_маяки" / "mayaki.json"

    def _chitat_etazh(self, path: Path) -> list:
        """Чтение этажа. Нет файла — пустой этаж, это нормально."""
        try:
            if path.exists():
                d = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(d, list):
                    return d
                raise ValueError("не список")
        except Exception as _e_et:
            # PAMYAT_BEZ_TISHINY_V1: файл есть, а не читается — это не
            # «пустой этаж», это беда. Говорим один раз на состояние
            # файла; запись поверх остановит _pisat_etazh.
            try:
                _kl = (str(path), path.stat().st_mtime_ns)
            except Exception:
                _kl = (str(path), 0)
            _skazat(f"{self.dom.name}: {Path(path).name} не читается "
                    f"({_e_et}) — сейчас для жителя пуст", klyuch=_kl)
        return []

    def _pisat_etazh(self, path: Path, data: list):
        path = Path(path)
        # PAMYAT_BEZ_TISHINY_V1: прежний файл не читался — значит житель
        # работал с «пустым» этажом, и запись сотрёт всё нажитое. Сперва
        # копия в чулан; не вышло — не пишем вовсе.
        if path.exists():
            try:
                _staroe = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(_staroe, list):
                    raise ValueError("не список")
            except Exception as _e_st:
                if not _v_chulan(self.dom, path, _e_st):
                    _skazat(f"{self.dom.name}: {path.name} не перезаписан — "
                            f"старое сберечь не вышло")
                    return
        _atomarno(path, json.dumps(data, ensure_ascii=False, indent=2))

    def metki(self) -> list:
        """Весь второй этаж — нажитое. Список объектов."""
        return self._chitat_etazh(self._metki_path())

    # ═══════════════════════════════════════════════════════
    # METKA_KAK_KLYUCH_V1 — МЕТКА КАК ЗАКЛАДКА
    # ═══════════════════════════════════════════════════════
    # Ключ собирается из двух половин. ОБЩАЯ у всех одинакова — когда,
    # откуда, от кого: по ней город может спросить поперёк жителей, и
    # слово будет значить одно и то же для всех. ЛИЧНАЯ — ярлыки его
    # словами и важность его глазами: тут все разные, и мы не лезем.
    #
    # Зачем вообще. Поиск в vspomnit буквальный, по словам: спросил
    # «дивергенция» — нашёл только там, где так и написано; записал
    # «диверы» — не нашёл никогда. Закладка чинит именно это: у записи
    # появляется ИМЯ, и спрашивают по имени, а не по угаданному слову.
    #
    # Почему не заняли «паттерн». Он служебный: на нём висит суд рынка
    # (подтверждений/опровержений). Трогать его — рисковать тем, что
    # уже работает.
    # ═══════════════════════════════════════════════════════

    YARLYK_VES = 5   # совпадение по закладке весит как пять слов запроса

    @staticmethod
    def _yarlyki_spisok(x) -> list:
        """Ярлыки в порядок: строка через запятую или список — в чистый
        список коротких слов нижним регистром, без повторов."""
        if not x:
            return []
        syrye = x.split(",") if isinstance(x, str) else list(x)
        out = []
        for y in syrye:
            y = str(y).strip().lower().strip("#")
            if y and y not in out:
                out.append(y[:40])
        return out[:8]

    # ARHIV_S_KLYUCHOM_V1: служебный мусор разбора и ТОЧНЫЙ дубль.
    @staticmethod
    def _chistyy_tekst(t) -> str:
        """Служебное «ЯРКОЕ:» в начале и случайные иероглифы в конце —
        мусор разбора ответа, не слова жителя."""
        t = str(t or "").strip()
        t = re.sub(r"^(?:[\s*_>#-]*ЯРКОЕ\s*[:：]\s*)+", "", t, flags=re.I)
        t = re.sub(r"\s*[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]+\s*$", "", t)
        return t.strip()

    @staticmethod
    def _odin_tekst(t) -> str:
        """Ключ ТОЧНОГО совпадения: те же слова в том же порядке.
        Регистр, пробелы, знаки и мусор не считаются. Похожее, но
        другими словами, — НЕ совпадение: его судит Шеф."""
        t = Dvizhok._chistyy_tekst(t).lower().replace("ё", "е")
        return " ".join(re.findall(r"[a-zа-я0-9_]+", t))

    POVTOROV_HRANIT = 20

    def _zapomnit_povtor(self, m: dict, otkuda: str = "", ot_kogo: str = "",
                         kak: str = ""):
        """Повтор не теряется и не плодит вторую метку: ложится историей
        в первую — когда, откуда, от кого, как было сказано."""
        z = {"когда": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if (otkuda or "").strip():
            z["откуда"] = otkuda.strip()
        if (ot_kogo or "").strip():
            z["от кого"] = ot_kogo.strip()[:40]
        if kak and kak.strip() != str(m.get("текст") or "").strip():
            z["как сказано"] = kak.strip()[:300]
        m["повторы"] = (list(m.get("повторы") or []) + [z])[-self.POVTOROV_HRANIT:]

    def _prishit_klyuch(self, zapis: dict, yarlyki=None, ot_kogo: str = ""):
        """Дописать закладочную часть ключа в запись. ДОБАВЛЯЕТ ярлыки к
        тем, что были, а не затирает: житель мог повесить одно вчера и
        другое сегодня, и оба верны."""
        novye = self._yarlyki_spisok(yarlyki)
        if novye:
            bylo = self._yarlyki_spisok(zapis.get("ярлыки"))
            zapis["ярлыки"] = self._yarlyki_spisok(bylo + novye)
        if (ot_kogo or "").strip():
            zapis["от кого"] = str(ot_kogo).strip()[:40]
        return zapis

    def yarlyki(self) -> list:
        """Его собственный словарь закладок: [(ярлык, сколько раз), ...],
        частые первыми.

        Нужно затем, что свободный ярлык через месяц расплодится в
        двести вариантов вразнобой — «дивер», «диверы», «дивергенция».
        Перед тем как вешать новый, житель смотрит, что у него уже
        есть, и берёт оттуда."""
        schyot = {}
        for etazh in (self.metki(), self.mayaki()):
            for z in etazh:
                for y in self._yarlyki_spisok(z.get("ярлыки")):
                    schyot[y] = schyot.get(y, 0) + 1
        return sorted(schyot.items(), key=lambda kv: (-kv[1], kv[0]))

    def mayaki(self) -> list:
        """Третий этаж — черновики момента. Гаснут, не набрав повтора."""
        return self._chitat_etazh(self._mayaki_path())

    YARKOE_V_STOL = 6   # ярких меток в столе — тоже не резиновый склад

    def _metki_v_stol(self) -> list:
        """Свежие METKI_V_STOL меток + ЯРКИЕ (YARKOE_V1) — для промпта.
        НЕ все: контекст Биржи уже 25к символов, а метки растут всю
        жизнь. Маленький стол + право дотянуться (MEMORY_REQUEST) —
        дешевле и честнее по природе: живой человек тоже не держит всю
        жизнь в голове. Но яркое (сам житель так решил, отдельной
        строкой в разговоре) не вымывается свежестью — держится своим
        флагом, а не местом в очереди."""
        # STOL_RAZNOE_V1 (30.09, слово Шефа): «стол — не вся память, а её
        # выборка; качество стола в том, насколько полно он представляет
        # опыт». Раньше 6 мест из 10 занимали шесть формулировок одного
        # правила, а 3 — названия пар. Теперь метки делятся на ТЕМЫ по
        # смыслу, и от каждой темы берётся один урок, свежайший; второй
        # из той же темы — только если места остались. Сами метки не
        # трогаются: всё лежит, как лежало, и достаётся по ключу.
        try:
            p = self._metki_path()
            _st = p.stat() if p.exists() else None
            _kl = (_st.st_mtime_ns, _st.st_size) if _st else None
            if _kl is not None and getattr(self, "_stol_kesh", (None,))[0] == _kl:
                return list(self._stol_kesh[1])
            vybor = self._stol_raznoe(self.metki())
            self._stol_kesh = (_kl, vybor)
            return list(vybor)
        except Exception:
            m = self.metki()
            m.sort(key=lambda x: str(x.get("когда", "")))
            yarkie = [x for x in m if x.get("ярко")][-self.YARKOE_V_STOL:]
            svezhie = [x for x in m if not x.get("ярко")][-self.METKI_V_STOL:]
            return yarkie + svezhie

    GOROD_V_STOL = 2        # записей города (прогонов) на столе — не больше
    TEMA_POROG = 0.35       # насколько общий смысл делает метки одной темой

    @staticmethod
    def _slova_uroka(t) -> set:
        t = str(t or "").lower().replace("ё", "е")
        return {w[:5] for w in re.findall(r"[a-zа-я0-9_]+", t) if len(w) >= 4}

    def _stol_raznoe(self, metki: list) -> list:
        """Выборка на стол: разные темы, свежие первыми. Ничего не
        склеивает и не удаляет — только выбирает, что положить."""
        m = [x for x in metki if isinstance(x, dict)
             and x.get("паттерн") != "рабочий_этаж"      # название пары — не урок
             and str(x.get("текст") or "").strip()]
        if not m:
            return []
        m.sort(key=lambda x: str(x.get("когда", ""))[:19], reverse=True)
        # VYSELENIE_PO_TEMAM_V1: темы считает одно правило — и для стола,
        # и для выселения.
        S, pohozhest, _grupy = self._razbit_na_temy(m)
        gorod = [x.get("откуда") == "прогон" for x in m]
        poryadok = sorted(_grupy, key=lambda t: t[0])  # тема — по свежайшей

        mest = self.YARKOE_V_STOL + self.METKI_V_STOL
        vzyato, gor = [], 0

        def mozhno(i):
            return not (gorod[i] and gor >= self.GOROD_V_STOL)

        for t in poryadok:                   # круг 1: по уроку от каждой темы
            if len(vzyato) >= mest:
                break
            i = t[0]
            if mozhno(i):
                vzyato.append(i)
                gor += gorod[i]
        for t in poryadok:                   # круг 2: вторые — самые непохожие
            if len(vzyato) >= mest:
                break
            ostalis = [i for i in t if i not in vzyato and mozhno(i)]
            if not ostalis:
                continue
            i = min(ostalis, key=lambda k: max(pohozhest(S[k], S[j]) for j in vzyato))
            vzyato.append(i)
            gor += gorod[i]
        return [m[i] for i in sorted(vzyato, key=lambda k: str(m[k].get("когда", ""))[:19])]

    # ═══════════════════════════════════════════════════════
    # VYSELENIE_PO_TEMAM_V1 (слово Шефа 30.09) — КОГО ВЫСЕЛЯТЬ
    # ═══════════════════════════════════════════════════════
    # Выселение стояло в четырёх местах, и в каждом своё правило. На
    # пробе ушёл единственный урок «три условия», а шесть формулировок
    # «края» остались. Теперь правило одно:
    #   1. запись выбора рабочей пары — не урок: последняя остаётся;
    #   2. повтор из самой большой темы — старшая формулировка; слово
    #      живого учителя не трогаем, уходит её собственный пересказ;
    #   3. единственный урок своей темы — не уходит, пока есть 1–2;
    #   4. выбора нет — самая старая (сперва не-яркие), как было.
    # Только что записанное не выселяется. Ушедшее — в архив с ключами.
    # ═══════════════════════════════════════════════════════

    def _razbit_na_temy(self, m: list):
        """Темы меток по смыслу. m — список меток (порядок любой).
        Возвращает (слова, мера похожести, группы индексов в m).
        Записи города делятся по своей ловушке, не по словам."""
        n = len(m)
        S = [self._slova_uroka(x.get("текст")) for x in m]
        df = {}
        for s in S:
            for w in s:
                df[w] = df.get(w, 0) + 1
        idf = {w: math.log((n + 1) / c) for w, c in df.items()}

        def pohozhest(a, b):
            if not a or not b:
                return 0.0
            obshchee = sum(idf[w] for w in a & b)
            return obshchee / max(1e-9, min(sum(idf[w] for w in a),
                                             sum(idf[w] for w in b)))

        gorod = [x.get("откуда") == "прогон" for x in m]
        roditel = list(range(n))

        def koren(i):
            while roditel[i] != i:
                roditel[i] = roditel[roditel[i]]
                i = roditel[i]
            return i
        for i in range(n):
            for j in range(i + 1, n):
                if gorod[i] or gorod[j]:
                    odna = (gorod[i] and gorod[j]
                            and m[i].get("паттерн") == m[j].get("паттерн"))
                else:
                    odna = pohozhest(S[i], S[j]) >= self.TEMA_POROG
                if odna:
                    roditel[koren(i)] = koren(j)
        temy = {}
        for i in range(n):
            temy.setdefault(koren(i), []).append(i)
        return S, pohozhest, list(temy.values())

    _NE_UCHITEL = ("", "город", "рынок")

    def _slovo_uchitelya(self, x: dict) -> bool:
        """Слово живого учителя: поправка учителя или «от кого» — человек
        (Шеф, Ректор…), а не город и не рынок."""
        if x.get("откуда") == "учитель":
            return True
        return str(x.get("от кого") or "").strip().lower() not in self._NE_UCHITEL

    def _kogo_vyselit(self, metki: list, novaya=None):
        """Одна метка на выселение по правилу выше. Нечего — None."""
        def kogda(x):
            return str(x.get("когда") or x.get("первый_раз") or "")[:19]
        kand = [x for x in metki if isinstance(x, dict) and x is not novaya]
        if not kand:
            return None
        # 1. записи выбора пары — последняя остаётся
        etazhi = sorted((x for x in metki if isinstance(x, dict)
                         and x.get("паттерн") == "рабочий_этаж"), key=kogda)
        if len(etazhi) > 1 and etazhi[0] is not novaya:
            return etazhi[0]
        # 2. повтор из самой большой темы
        uroki = sorted((x for x in metki if isinstance(x, dict)
                        and x.get("паттерн") != "рабочий_этаж"
                        and str(x.get("текст") or "").strip()),
                       key=kogda, reverse=True)
        if len(uroki) > 1:
            try:
                _S, _p, grupy = self._razbit_na_temy(uroki)
                grupy = [[uroki[i] for i in g] for g in grupy if len(g) >= 2]
                grupy.sort(key=lambda g: (-len(g), min(kogda(x) for x in g)))
                for g in grupy:
                    mozhno = [x for x in g if x is not novaya
                              and not self._slovo_uchitelya(x)]
                    if mozhno:
                        return min(mozhno, key=kogda)
            except Exception:
                pass
        # 4. выбора нет — самая старая, сперва не-яркие
        ne_yarkie = [x for x in kand if not x.get("ярко")]
        return min(ne_yarkie or kand, key=kogda)

    def _vyselit_lishnie(self, metki: list, novaya=None) -> tuple:
        """Пока меток больше METKI_CAP — выселяет по одной (правило выше),
        ушедшее кладёт в архив с ключами. Возвращает (остались, ушли)."""
        metki = list(metki)
        ushli = []
        while len(metki) > self.METKI_CAP:
            zhertva = self._kogo_vyselit(metki, novaya)
            if zhertva is None:
                break
            metki = [x for x in metki if x is not zhertva]
            ushli.append(zhertva)
            self._archive_zapis(zhertva, "метка вытеснена (лимит нажитого)")
        return metki, ushli

    # ═══════════════════════════════════════════════════════
    # YARKOE_V1 — ЖИТЕЛЬ САМ РЕШАЕТ, ЧТО ДЕРЖИТСЯ ДОЛЬШЕ
    # ═══════════════════════════════════════════════════════
    # Тот же приём, что MEMORY_REQUEST, только не наружу (принести), а
    # внутрь (сохранить). Не судья повтора (Путь Зрелости, 3 раза), не
    # рынок (verdikt_rynka) — воля жителя, в моменте разговора. Ложится
    # в метки СРАЗУ, минуя оба обычных порога, с флагом "ярко".
    # ═══════════════════════════════════════════════════════

    def otmetit_yarkim(self, tekst: str, otkuda: str = "",
                       yarlyki=None, ot_kogo: str = "") -> dict:
        # METKA_KAK_KLYUCH_V1: сюда же вешается закладочная часть ключа.
        # Даже если метка уже была яркой — ярлык и имя дописываем: это
        # не повтор знания, это уточнение ключа к нему.
        _skazano = (tekst or "").strip()
        tekst = self._chistyy_tekst(_skazano)   # ARHIV_S_KLYUCHOM_V1: без «ЯРКОЕ:»
        if not tekst:
            return {"дописано": False, "причина": "пустой текст"}
        metki = self.metki()
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _tot_zhe = self._odin_tekst(tekst)
        for m in metki:
            if self._odin_tekst(m.get("текст")) == _tot_zhe:
                _bylo_yarkim = bool(m.get("ярко"))
                self._prishit_klyuch(m, yarlyki, ot_kogo)
                self._zapomnit_povtor(m, otkuda, ot_kogo, _skazano)   # ARHIV_S_KLYUCHOM_V1
                if _bylo_yarkim:
                    self._pisat_etazh(self._metki_path(), metki)
                    if yarlyki or ot_kogo:
                        return {"дописано": True, "причина": "ключ уточнён"}
                    return {"дописано": False,
                            "причина": "уже отмечено ярким — повтор записан"}
                m["ярко"] = True
                self._pisat_etazh(self._metki_path(), metki)
                return {"дописано": True, "причина": "было меткой, стало яркой"}
        _novaya = {"текст": tekst, "паттерн": None, "откуда": otkuda or "сам",
                   "когда": now_iso, "раз": 1, "ярко": True}
        self._prishit_klyuch(_novaya, yarlyki, ot_kogo)
        metki.append(_novaya)
        # VYSELENIE_PO_TEMAM_V1: одно правило выселения на все пути
        metki, ushlo = self._vyselit_lishnie(metki, _novaya)
        self._pisat_etazh(self._metki_path(), metki)
        return {"дописано": True, "меток": len(metki), "вытеснено": len(ushlo)}

    # YAKORYA_DVA_YARUSA_V1: порог повтора для перехода черновик→устойчивый.
    # То же число, что Путь Зрелости (Чертёж §4.6.2: «3 вердикта судьи»)
    # — не новый магический порог, тот же самый смысл: отбор трижды.
    PROMOTE_THRESHOLD = 3
    DRAFT_CAP = 6   # черновиков живёт не больше — тоже не резиновый склад

    # PAMYAT_RYNOK_SUDYA_V1: у ТОРГОВОГО вывода судья не повтор, а рынок.
    # Повтор говорит "я это часто думаю" — и только. Рынок говорит "ты был
    # прав". Метка обязана расти из второго, иначе трейдер затвердевает
    # в собственной ошибке. Числа те же, что у Пути Зрелости (3), смысл
    # другой: не три упоминания, а три ЗАКРЫТЫЕ сделки.
    RYNOCHNYE_ISTOCHNIKI = ("рынок", "сделка")
    PODTVERZHDENIY_DO_METKI = 3      # закрытых в плюс — маяк встаёт меткой
    OPROVERZHENIY_DO_GASHENIYA = 3   # закрытых в минус — маяк гаснет
    OPROVERZHENIY_DO_PADENIYA = 3    # столько же — и МЕТКА падает обратно

    # ARHIV_S_KLYUCHOM_V1 (30.09, слово Шефа): «вытеснение с рабочего
    # стола не должно означать потерю ключей и происхождения метки».
    # Раньше в архив уходил голый текст: без ключей, без «от кого», без
    # голоса — и по слою архив считался «учёбой». По ключу такую метку
    # было уже не найти. Теперь запись уносит всё, чем её находят.
    _ARHIV_NESTI = ("откуда", "от кого", "ярлыки", "паттерн", "ярко",
                    "подтверждений", "опровержений", "повторы")

    def _archive_zapis(self, fakt, prichina: str):
        """Общий писчик в archive.jsonl — и вытесненные якоря, и
        вытесненные черновики уходят сюда, не в забвение.
        fakt — строка или САМА метка (dict): тогда с ней уходят ключи,
        голос, «от кого» и время рождения."""
        metka = fakt if isinstance(fakt, dict) else None
        if metka is not None:
            fakt = metka.get("текст", "")
        try:
            (self.dom / "archive").mkdir(parents=True, exist_ok=True)
            ap = self.dom / "archive" / "archive.jsonl"
            zapis = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "слой": "archive",
                "факт": fakt,
                "причина": prichina,
            }
            if metka is not None:
                for _k in self._ARHIV_NESTI:
                    if metka.get(_k) not in (None, "", [], {}):
                        zapis[_k] = metka[_k]
                if metka.get("когда") or metka.get("первый_раз"):
                    zapis["было_с"] = metka.get("когда") or metka.get("первый_раз")
                _kont = (str(metka.get("контекст") or "").strip()
                         or OTKUDA_KONTEKST.get(
                             str(metka.get("откуда") or "").strip().lower(), ""))
                if _kont:
                    zapis["контекст"] = _kont
            with open(ap, "a", encoding="utf-8") as f:
                f.write(json.dumps(zapis, ensure_ascii=False) + "\n")
        except Exception as _e_arh:
            # PAMYAT_BEZ_TISHINY_V1: запись опыта не роняем — но и не молчим
            _skazat(f"{self.dom.name}: в архив не легло ({prichina}): {_e_arh}")

    def dopisat_vyvod(self, vyvod: str, limit: int = 10,
                      pattern: Optional[str] = None,   # PYLANCE_GIGIENA_V1
                      otkuda: str = "рынок",
                      yarlyki=None, ot_kogo: str = "") -> dict:
        # METKA_KAK_KLYUCH_V1: yarlyki — свои слова жителя (закладка),
        # ot_kogo — ИМЯ того, от кого знание. Оба необязательны: не
        # передали — всё как было.
        """Дописывает ВЫВОД — нога Опыта. TRI_ETAZHA_V1.

        ⚠ ПИШЕТ В МЕТКИ (2_метки/metki.json), НЕ в Anchor_Points.
        Anchor_Points = РОД по закону ядра, он НЕ РАСТЁТ. То, что я
        (Брат) 12.07 дописывал туда торговые выводы — было ошибкой,
        разобранной Шефом. Опыт — это МЕТКИ.

        ДВА ЯРУСА (порог 3, канон Пути Зрелости):
          pattern=None  — вывод ложится в метки СРАЗУ (для чужого кода,
                          что зовёт без ключа: поведение сохранено).
          pattern="ключ" — сперва МАЯК (черновик, «замечаю за собой»).
                          Тот же ключ встретился PROMOTE_THRESHOLD раз →
                          маяк гаснет, на его месте встаёт МЕТКА.

        otkuda — ЧЕСТНОЕ ПОЛЕ «откуда вывод»: "рынок" / "учёба" /
        "<профессия>" / "жизнь" (PROSEV_ZHIZNENNYI_V1 — личный просев).
        Это НЕ «происхождение якоря», которое я собрался изобретать
        (§5.1) — этаж и есть происхождение. Это просто голос внутри
        одного этажа: медийщик на Бирже увидит и «что я вынес в
        монтажной», и «что мне сказал рынок» — и может их СТОЛКНУТЬ.

        limit — legacy-параметр, оставлен для совместимости вызовов
        (nositel.py передаёт limit=10). Метки живут по METKI_CAP.
        """
        _skazano = (vyvod or "").strip()
        vyvod = self._chistyy_tekst(_skazano)   # ARHIV_S_KLYUCHOM_V1
        if not vyvod:
            return {"дописано": False, "причина": "пустой вывод"}

        metki  = self.metki()
        mayaki = self.mayaki()
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # дубль текста — ни в одном этаже не плодим.
        # ARHIV_S_KLYUCHOM_V1: «точный» — те же слова в том же порядке;
        # повтор при этом не теряется, а ложится историей в первую запись.
        _tot_zhe = self._odin_tekst(vyvod)
        _dubl = next((m for m in metki
                      if self._odin_tekst(m.get("текст")) == _tot_zhe), None)
        if _dubl is not None:
            self._prishit_klyuch(_dubl, yarlyki, ot_kogo)
            self._zapomnit_povtor(_dubl, otkuda, ot_kogo, _skazano)
            self._pisat_etazh(self._metki_path(), metki)
            return {"дописано": False, "причина": "уже среди меток — повтор записан",
                    "меток": len(metki)}
        _dubl = next((m for m in mayaki
                      if self._odin_tekst(m.get("текст")) == _tot_zhe), None)
        if _dubl is not None:
            self._prishit_klyuch(_dubl, yarlyki, ot_kogo)
            self._zapomnit_povtor(_dubl, otkuda, ot_kogo, _skazano)
            self._pisat_etazh(self._mayaki_path(), mayaki)
            return {"дописано": False, "причина": "уже среди маяков — повтор записан",
                    "маяков": len(mayaki)}

        # РОД тоже сверяем: если житель «вывел» то, что и так его натура —
        # это не открытие, а подтверждение. Не плодим строку.
        if vyvod in self._yakorya_spisok(self.p.get("Anchor_Points", "") or ""):
            return {"дописано": False,
                    "причина": "это его род (Anchor_Points), не нажитое"}

        def _lech_metkoy(txt, patt, raz):
            _m = {"текст": txt, "паттерн": patt, "откуда": otkuda,
                  "когда": now_iso, "раз": raz}
            self._prishit_klyuch(_m, yarlyki, ot_kogo)   # METKA_KAK_KLYUCH_V1
            metki.append(_m)
            # VYSELENIE_PO_TEMAM_V1: одно правило выселения на все пути
            _ost, ushlo = self._vyselit_lishnie(metki, _m)
            metki[:] = _ost
            return ushlo

        # ── ЯРУС 1: без ключа — сразу в метки ───────────────────
        if pattern is None:
            ushlo = _lech_metkoy(vyvod, None, 1)
            self._pisat_etazh(self._metki_path(), metki)
            return {"дописано": True, "тип": "устойчивый", "этаж": "метка",
                    "откуда": otkuda, "меток": len(metki),
                    "вытеснено": len(ushlo)}

        # ── ЯРУС 2: с ключом — сперва маяк ──────────────────────
        found = None
        for m in mayaki:
            if m.get("паттерн") == pattern:
                found = m
                break

        if found is not None:
            found["раз"] = found.get("раз", 1) + 1
            found["текст"] = vyvod
            found["последний_раз"] = now_iso
            found["откуда"] = otkuda
            self._prishit_klyuch(found, yarlyki, ot_kogo)  # METKA_KAK_KLYUCH_V1
            raz = found["раз"]
        else:
            found = {"текст": vyvod, "паттерн": pattern, "откуда": otkuda,
                     "раз": 1, "первый_раз": now_iso, "последний_раз": now_iso}
            self._prishit_klyuch(found, yarlyki, ot_kogo)  # METKA_KAK_KLYUCH_V1
            mayaki.append(found)
            raz = 1

        promoted = False
        ushlo = []
        # PAMYAT_RYNOK_SUDYA_V1: рыночный маяк ЖДЁТ вердикта, повтор его
        # не поднимает. Заводим счётчики сразу, чтобы verdikt_rynka()
        # писал в готовые поля, а не создавал их на лету.
        _sudit_rynok = otkuda in self.RYNOCHNYE_ISTOCHNIKI
        if _sudit_rynok:
            found.setdefault("подтверждений", 0)
            found.setdefault("опровержений", 0)
        if (not _sudit_rynok) and raz >= self.PROMOTE_THRESHOLD:
            # маяк догорел — на его месте встаёт метка
            mayaki = [m for m in mayaki if m is not found]
            ushlo = _lech_metkoy(found["текст"], pattern, raz)
            promoted = True

        # маяки — не резиновый склад: слабейшие гаснут в архив
        pogaslo = []
        if len(mayaki) > self.DRAFT_CAP:
            # PAMYAT_RYNOK_SUDYA_V1: рыночные — в хвост сортировки, значит
            # вытесняются последними. Сделка может закрыться через неделю,
            # обидно погасить маяк за день до ответа рынка.
            mayaki.sort(key=lambda d: (
                1 if d.get("откуда") in self.RYNOCHNYE_ISTOCHNIKI else 0,
                d.get("раз", 1),
                d.get("первый_раз", "")))
            pogaslo = mayaki[:len(mayaki) - self.DRAFT_CAP]
            mayaki = mayaki[len(mayaki) - self.DRAFT_CAP:]
            for d in pogaslo:
                self._archive_zapis(
                    d,
                    f"маяк погас, не набрал повтора ({d.get('раз', 1)}/"
                    f"{self.PROMOTE_THRESHOLD})")

        if promoted:
            self._pisat_etazh(self._metki_path(), metki)
        self._pisat_etazh(self._mayaki_path(), mayaki)

        return {
            "дописано": True,
            "тип":   "устойчивый" if promoted else "черновик",
            "этаж":  "метка" if promoted else "маяк",
            "откуда": otkuda,
            "раз": raz,
            "меток": len(metki),
            "маяков": len(mayaki),
            "черновиков": len(mayaki),      # legacy-ключ: nositel читает его
            "якорей": len(self._yakorya_spisok(
                self.p.get("Anchor_Points", "") or "")),
            "вытеснено_меток": len(ushlo),
            "вытеснено_черновиков": len(pogaslo),
        }

    # ═══════════════════════════════════════════════════════
    # PAMYAT_RYNOK_SUDYA_V1 — ВЕРДИКТ РЫНКА
    # ═══════════════════════════════════════════════════════

    def verdikt_rynka(self, pattern: str, plus: bool,
                      fakt: str = "") -> dict:
        """Рынок ответил по СВЕРШИВШЕЙСЯ сделке. Зовётся при ЗАКРЫТИИ,
        не при входе — до закрытия судить нечем.

        pattern — тот же ключ, под которым вывод лёг маяком
                  (например "вход:откат-в-тренд:H4").
        plus    — True, если сделка закрыта в плюс.
        fakt    — необязательная строка для архива (тикет, R, инструмент).

        Четыре исхода:
          маяк набрал подтверждений  -> встаёт МЕТКОЙ (нажитое знание)
          маяк набрал опровержений   -> ГАСНЕТ в архив, честно
          метку рынок опроверг       -> метка ПАДАЕТ обратно в маяки
          ключа нигде нет            -> честное "не нашёл", не выдумываем
        """
        pattern = (pattern or "").strip()
        if not pattern:
            return {"учтено": False, "причина": "пустой ключ"}

        mayaki = self.mayaki()
        metki = self.metki()
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        pole = "подтверждений" if plus else "опровержений"

        # ── случай 1: ключ ещё в маяках (черновик ждёт суда) ──
        m = next((x for x in mayaki if x.get("паттерн") == pattern), None)
        if m is not None:
            m[pole] = int(m.get(pole, 0)) + 1
            m["последний_вердикт"] = now_iso
            za = int(m.get("подтверждений", 0))
            protiv = int(m.get("опровержений", 0))

            if za >= self.PODTVERZHDENIY_DO_METKI and za > protiv:
                mayaki = [x for x in mayaki if x is not m]
                metki.append({
                    "текст": m.get("текст", ""), "паттерн": pattern,
                    "откуда": m.get("откуда", "рынок"), "когда": now_iso,
                    "раз": m.get("раз", 1),
                    "подтверждений": za, "опровержений": protiv,
                })
                # VYSELENIE_PO_TEMAM_V1: одно правило выселения на все пути
                metki, _ushli = self._vyselit_lishnie(metki, metki[-1])
                self._pisat_etazh(self._metki_path(), metki)
                self._pisat_etazh(self._mayaki_path(), mayaki)
                return {"учтено": True, "исход": "маяк стал меткой",
                        "паттерн": pattern, "за": za, "против": protiv}

            if protiv >= self.OPROVERZHENIY_DO_GASHENIYA and protiv > za:
                mayaki = [x for x in mayaki if x is not m]
                self._archive_zapis(
                    m,
                    f"рынок опроверг маяк ({protiv} против {za}) {fakt}".strip())
                self._pisat_etazh(self._mayaki_path(), mayaki)
                return {"учтено": True, "исход": "маяк погашен рынком",
                        "паттерн": pattern, "за": za, "против": protiv}

            self._pisat_etazh(self._mayaki_path(), mayaki)
            return {"учтено": True, "исход": "маяк ждёт дальше",
                    "паттерн": pattern, "за": za, "против": protiv}

        # ── случай 2: ключ уже метка — она тоже под судом ──
        mt = next((x for x in metki if x.get("паттерн") == pattern), None)
        if mt is not None:
            mt[pole] = int(mt.get(pole, 0)) + 1
            mt["последний_вердикт"] = now_iso
            za = int(mt.get("подтверждений", 0))
            protiv = int(mt.get("опровержений", 0))

            # РАЗУЧИВАНИЕ. Раньше метка была вечной: ошибку, однажды
            # затвердевшую, снять было нечем. Рынок передумал — память
            # обязана уметь передумать вслед за ним.
            if protiv >= self.OPROVERZHENIY_DO_PADENIYA and protiv > za:
                metki = [x for x in metki if x is not mt]
                mayaki.append({
                    "текст": mt.get("текст", ""), "паттерн": pattern,
                    "откуда": mt.get("откуда", "рынок"), "раз": 1,
                    "первый_раз": now_iso, "последний_раз": now_iso,
                    "подтверждений": 0, "опровержений": 0,
                    "падала": True,
                })
                self._archive_zapis(
                    mt,
                    f"метка упала обратно в маяки: рынок опроверг "
                    f"({protiv} против {za}) {fakt}".strip())
                self._pisat_etazh(self._metki_path(), metki)
                self._pisat_etazh(self._mayaki_path(), mayaki)
                return {"учтено": True, "исход": "метка упала в маяки",
                        "паттерн": pattern, "за": za, "против": protiv}

            self._pisat_etazh(self._metki_path(), metki)
            return {"учтено": True, "исход": "метка устояла",
                    "паттерн": pattern, "за": za, "против": protiv}

        # ── случай 3: ключа нет нигде ──
        return {"учтено": False, "причина": "такого ключа нет ни в маяках, "
                                           "ни в метках", "паттерн": pattern}

    # ═══════════════════════════════════════════════════════
    # POPRAVKA_UCHITELYA_V1 — СЛОВО УЧИТЕЛЯ
    # ═══════════════════════════════════════════════════════

    def popravka_uchitelya(self, tekst: str, pattern: str = "") -> dict:
        """Учитель поправил — ложится СРАЗУ меткой, твёрдым знанием.

        Тот же закон, что и verdikt_rynka: знание твердеет от СУДЬИ, а
        не от числа повторов. На Бирже судья — рынок. В Академии рынка
        ещё нет, и судья — учитель. Сказал один раз, повторять трижды
        незачем.

        Ошибку ученика не трогаем: она остаётся сырым моментом в
        разговоре. Просто рядом встаёт метка, которая весит больше.
        Прошлое не переписываем — наращиваем.

        pattern — необязательный ключ темы («фрактал», «вход»), чтобы
                  поправка по той же теме заменяла прежнюю, а не
                  копилась дублями.
        """
        tekst = (tekst or "").strip()
        if not tekst:
            return {"легло": False, "причина": "пустая поправка"}

        metki = self.metki()
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        pattern = (pattern or "").strip()

        # поправка по той же теме заменяет прежнюю: учитель передумал —
        # держим последнее слово, а прежнее уходит в архив, не пропадая
        if pattern:
            byvshie = [m for m in metki if m.get("паттерн") == pattern]
            for b in byvshie:
                self._archive_zapis(b,
                                    "заменено новой поправкой учителя")
            metki = [m for m in metki if m.get("паттерн") != pattern]

        metki.append({
            "текст": tekst,
            "паттерн": pattern,
            "откуда": "учитель",
            "когда": now_iso,
            "раз": 1,
            # VSPOMNIT_METKI_POLYA_V1 (05.09): без контекста запись
            # невидима для vspomnit(..., o_chyom="работа") — а поправка
            # учителя трейдеру по определению рабочее знание.
            "контекст": "работа",
        })
        # VYSELENIE_PO_TEMAM_V1: одно правило выселения на все пути
        metki, _ushli = self._vyselit_lishnie(metki, metki[-1])
        self._pisat_etazh(self._metki_path(), metki)
        return {"легло": True, "этаж": "метки", "паттерн": pattern}

    # ═══════════════════════════════════════════════════════
    # PAMYAT_V_PROMT_VEZDE_V1 — НАЖИТОЕ СЛОВАМИ, ДЛЯ ПРОМПТА
    # ═══════════════════════════════════════════════════════

    ZNANIE_OTKUDA = ("учёба", "учеба", "учитель")

    def pamyat_v_promt(self, metok: int = 14, chernovikov: int = 8,
                       rabota: bool = False, klyuchi: bool = False) -> str:  # RABOTA_V_PAMYATI_V1
        """Нажитое — текстом для системного промпта. Пусто — пустая строка.

        До этого метода вся трёхэтажная память работала ТОЛЬКО НА
        ЗАПИСЬ: vydoh_stol её считал, а промпт собирался из паспорта, и
        ни один вывод в разговор не попадал. Житель копил и не помнил.

        Разложено по смыслу, а не свалено кучей:
          — твёрдое знание (метки от учёбы и учителя) — подтверждено
            судьёй, на него можно опираться;
          — черновики учёбы — собственный пересказ, может быть неверен;
          — выводы о себе (метки «жизнь») — это характер, не знание.
        """
        try:
            metki = self.metki() or []
            mayaki = self.mayaki() or []
        except Exception:
            return ""

        def _tekst(x):
            return str(x.get("текст", "")).strip()

        znanie = [_tekst(m) for m in metki
                  if m.get("откуда") in self.ZNANIE_OTKUDA and _tekst(m)]
        chernoviki = [_tekst(m) for m in mayaki
                      if m.get("откуда") in self.ZNANIE_OTKUDA and _tekst(m)]
        o_sebe = [_tekst(m) for m in metki
                  if m.get("откуда") not in self.ZNANIE_OTKUDA and _tekst(m)
                  # RABOTA_V_PAMYATI_V1: рабочее — в блок работы, не в «о себе»
                  and not (rabota and self._metka_rabochaya(m))]
        rab_blok = self.rabota_v_promt(klyuchi=klyuchi) if rabota else ""

        znanie = znanie[-metok:]
        chernoviki = chernoviki[-chernovikov:]
        o_sebe = o_sebe[-metok:]

        if not (znanie or chernoviki or o_sebe):
            return rab_blok   # RABOTA_V_PAMYATI_V1

        s = "\n=== ЧТО У ТЕБЯ УЖЕ НАЖИТО ===\n"
        if znanie:
            s += ("\nЗнаешь твёрдо (проверено учителем или делом) — "
                  "на это можно опираться:\n")
            s += "".join(f"• {t}\n" for t in znanie)
        if chernoviki:
            s += ("\nПонял(а) сам(а), но ещё не проверено — говори об этом "
                  "осторожнее, можешь ошибаться:\n")
            s += "".join(f"• {t}\n" for t in chernoviki)
        if o_sebe:
            s += "\nЧто ты понял(а) о себе:\n"
            s += "".join(f"• {t}\n" for t in o_sebe)
        s += ("\nЭто твоя память — говори из неё своими словами. Чего здесь "
              "нет, того ты не знаешь: так и скажи честно, не придумывай. "
              "Не перечисляй этот список вслух, просто помни.\n")
        return rab_blok + s   # RABOTA_V_PAMYATI_V1

    # ═══════════════════════════════════════════════════════
    # RABOTA_V_PAMYATI_V1 (слово Шефа 30.09) — РАБОТА В ПАМЯТИ
    # ═══════════════════════════════════════════════════════
    # «Не только помнить, что где-то работает, но и что там было —
    # иначе декорация.» Кладём коротко: где, итоги прогонов с ключами,
    # свои рабочие уроки. Подробности — по ключу: «таскать метки проще,
    # чем всю память: спросил, проверил ключ, получил».
    RABOCHIE_OTKUDA = ("работа", "рынок", "сделка", "прогон", "решение")
    REDKOST_SLOVOM = {"Common": "Обычный", "Rare": "Редкий",
                      "Epic": "Легендарный", "Mythic": "Единственный"}

    def _metka_rabochaya(self, m: dict) -> bool:
        return (m.get("откуда") in self.RABOCHIE_OTKUDA
                or m.get("паттерн") == "рабочий_этаж")

    def _imya_lokacii(self, lid: str) -> str:
        """Имя места по его id — из паспорта локации. Нет — сам id."""
        if not lid:
            return ""
        try:
            pp = self.dom.parent.parent.parent / "локации" / lid / "passport.json"
            if pp.exists():
                return (json.loads(pp.read_text(encoding="utf-8"))
                        .get("Official_Name") or lid)
        except Exception:
            pass
        return lid

    def rabota_v_promt(self, progonov: int = 5, urokov: int = 8,
                       klyuchi: bool = False) -> str:
        """Работа словами, для разговора. klyuchi=True — у итогов видны
        ключи прогонов и подсказка, как поднять подробности (там, где
        разговор умеет MEMORY_REQUEST)."""
        try:
            p = json.loads(self.passport_path.read_text(encoding="utf-8"))
        except Exception:
            p = self.p
        s = "\n=== ТЫ В ГОРОДЕ ===\n"
        r = str(p.get("Rarity") or "").strip()
        if r:
            s += f"Твоя редкость: {r} («{self.REDKOST_SLOVOM.get(r, r)}»).\n"
        lid = str(p.get("прописка") or "").strip()
        if lid:
            s += f"Живёшь: {self._imya_lokacii(lid)}.\n"

        s += "\n=== ТВОЯ РАБОТА ===\n"
        rab = p.get("Работа") or {}
        if not isinstance(rab, dict) or not rab:
            return s + "Постоянной работы у тебя сейчас нет.\n"
        dolzh = str(rab.get("должность") or "").strip() or "без названия"
        gde = str(rab.get("где") or "").strip()
        s_dnya = str(rab.get("с") or "")[:10]
        if len(s_dnya) == 10 and s_dnya[4] == "-":
            s_dnya = f"{s_dnya[8:10]}.{s_dnya[5:7]}"
        s += (f"Ты работаешь: {dolzh}" + (f" — {gde}" if gde else "")
              + (f", с {s_dnya}" if s_dnya else "") + ".\n")

        try:
            metki = self.metki() or []
        except Exception:
            metki = []
        etazhi = sorted((m for m in metki if m.get("паттерн") == "рабочий_этаж"
                         and str(m.get("текст") or "").strip()),
                        key=lambda x: str(x.get("когда", "")))
        if etazhi:
            s += f"Последний рабочий этаж: {etazhi[-1]['текст']}.\n"

        itogi = []
        try:
            pr = self.dom / "работа" / "работа.jsonl"
            if pr.exists():
                for ln in pr.read_text(encoding="utf-8").splitlines():
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        z = json.loads(ln)
                    except Exception:
                        continue
                    if str(z.get("факт") or "").startswith("Прогон"):
                        itogi.append(z)
        except Exception:
            pass
        if itogi:
            s += (f"\nЧто было на работе — итоги прогонов (всего в журнале "
                  f"{len(itogi)}, последние сверху):\n")
            for z in reversed(itogi[-progonov:]):
                d = str(z.get("ts") or "")[:10]
                if len(d) == 10:
                    d = f"{d[8:10]}.{d[5:7]}"
                f = str(z.get("факт") or "").replace("Прогон по истории ", "", 1)
                kl = str(z.get("прогон") or "").strip()
                s += f"— {d} · {f}"
                if klyuchi and kl:
                    s += f" ⟨ключ: прогон {kl}⟩"
                s += "\n"
        else:
            s += "\nРабочего журнала пока нет — итогов работы не записано.\n"

        uroki = sorted((m for m in metki if self._metka_rabochaya(m)
                        and m.get("паттерн") != "рабочий_этаж"
                        and str(m.get("текст") or "").strip()),
                       key=lambda x: str(x.get("когда", "")))[-urokov:]
        if uroki:
            s += "\nЧто ты вынес(ла) с работы:\n"
            s += "".join(f"• {str(m.get('текст')).strip()}\n" for m in uroki)

        s += "\nЭто твоя работа, ты помнишь её сама — говори из этого своими словами.\n"
        if klyuchi and itogi:
            s += ("Нужны подробности прогона (сделки, входы, выходы) — напиши "
                  "отдельной строкой MEMORY_REQUEST: прогон <ключ>, и они "
                  "поднимутся. Остальное не выдумывай.\n")
        else:
            s += "Подробностей сверх этого не выдумывай — скажи, что помнишь в общих чертах.\n"
        return s

    def zhdut_verdikta(self) -> list:
        """Рыночные маяки, по которым рынок ещё не ответил. Для кабинета:
        видно, что висит незакрытым и что вот-вот затвердеет."""
        return [m for m in self.mayaki()
                if m.get("откуда") in self.RYNOCHNYE_ISTOCHNIKI]

    # PAMYAT_ISKRA_V1: запрос вида «найди тёплое» / «что царапнуло» ищет
    # и по тонусу записи, не только по словам факта — иначе такой запрос
    # находит лишь записи, где слово «тёплое» встречается буквально в
    # тексте факта. Дёшево (одна строка рядом, Закон Меток) и честно
    # (не выдумываем — просто читаем то, что уже посчитано на вдохе).
    _TEPLO_SLOVA = {
        "тепло": "плюс", "тёпл": "плюс", "теплом": "плюс", "грело": "плюс",
        "грел": "плюс", "доброе": "плюс", "радост": "плюс", "приятн": "плюс",
        "царапн": "минус", "кольнул": "минус", "задело": "минус",
        "обидн": "минус", "неприятн": "минус", "кольнуло": "минус",
    }

    def vspomnit(self, zapros: str, limit: int = 6,
                 o_chyom: str = "") -> str:
        """PATCH_ZHITEL_VSPOMINAET: житель САМ решил вспомнить (MEMORY_REQUEST).
        Текстовый поиск по своим слоям: sensory + resonance + archive.
        БЕЗ шлюза по заряду — воля жителя выше стресс-шлюза (закон -2:
        вспомнить можно в любом месте, безусловно). Свежее и точное — выше.
        PAMYAT_ISKRA_V1: «тёплое»/«царапнуло» дополнительно ищет по тонусу.
        Возвращает строки находок или "" (пусто = следа нет, честно)."""
        slova = [w for w in (zapros or "").lower().split() if len(w) > 2]
        if not slova:
            return ""
        iskomyj_tonus = None
        low_zapros = (zapros or "").lower()
        for kliuch, ton in self._TEPLO_SLOVA.items():
            if kliuch in low_zapros:
                iskomyj_tonus = ton
                break
        zapisi = []
        # sensory — JSON-объект с entries
        try:
            p = self.dom / "sensory" / "sensory_memory.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                zapisi.extend(data.get("entries", []))
        except Exception:
            pass
        # SVOI_SDELKI_VIDNO_V1: маяки и метки — там лежит ОПЫТ, в том
        # числе торговый. Раньше поиск их не видел: выводы из сделок
        # пишет dopisat_vyvod (маяки/метки), а искали мы в sensory,
        # resonance и archive. Человек спрашивал «где меня стопануло»
        # и получал «следа нет», хотя след был — в другом ящике.
        for _rel in ("3_маяки/mayaki.json", "2_метки/metki.json"):
            try:
                _p = self.dom / _rel
                if not _p.exists():
                    continue
                _d = json.loads(_p.read_text(encoding="utf-8"))
                _it = _d if isinstance(_d, list) else (
                    _d.get("маяки") or _d.get("метки") or [])
                for _x in _it:
                    if isinstance(_x, dict):
                        zapisi.append(_x)
            except Exception:
                pass
        # resonance + archive — JSONL, строка за строкой
        for rel in ("resonance/event_log.jsonl", "archive/archive.jsonl"):
            try:
                p = self.dom / rel
                if p.exists():
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            zapisi.append(json.loads(line))
                        except Exception:
                            pass
            except Exception:
                pass
        # SKVOZNAYA_PAMYAT_V1: работа и разговоры — тоже её память, и она
        # вспоминается где угодно. Работа (итоги прогонов, сделки) — в
        # работа/работа.jsonl, разговоры — в чатах дома и в Академии.
        # Книги и знания сюда не идут: их не носят с собой.
        try:
            _pr = self.dom / "работа" / "работа.jsonl"
            if _pr.exists():
                for _ln in _pr.read_text(encoding="utf-8").splitlines():
                    _ln = _ln.strip()
                    if _ln:
                        try:
                            zapisi.append(json.loads(_ln))
                        except Exception:
                            pass
        except Exception:
            pass
        for _pap, _kont in (("чаты", "общение"), ("академия_чаты", "учёба")):
            try:
                for _f in sorted((self.dom / _pap).glob("*.json")):
                    _ts = _f.stem.replace("чат_", "")[:10]
                    _d = json.loads(_f.read_text(encoding="utf-8"))
                    for _m in (_d if isinstance(_d, list) else []):
                        if not isinstance(_m, dict):
                            continue
                        _c = _m.get("content")
                        if isinstance(_c, list):
                            _c = " ".join(str(x.get("text") or "") for x in _c
                                          if isinstance(x, dict))
                        _c = str(_c or "").strip()
                        if not _c:
                            continue
                        zapisi.append({
                            "факт": _c[:500], "контекст": _kont, "ts": _ts,
                            "от кого": ("Шеф" if _pap == "чаты"
                                        and _m.get("role") == "user" else "")})
            except Exception:
                pass
        # оценка: сколько слов запроса встретилось в факте записи
        # PAMYAT_RABOTA_ZHIZN_V1: о чём спрашиваем — о работе или о
        # жизни. За столом нужна практика, а не разговоры; дома —
        # наоборот. Пусто — ищем везде, как раньше.
        # RABOTA_V_PAMYATI_V1: спросили по ключу прогона — отдаём
        # ровно этот прогон, а не всё, где встретились слова.
        import re as _re_kl
        _kl = _re_kl.search(r"\d{8}_\d{6}", zapros or "")
        _klyuch = _kl.group(0) if _kl else ""
        if _klyuch:
            _po_kl = [z for z in zapisi
                      if str(z.get("прогон") or "") == _klyuch]
            if _po_kl:
                zapisi = _po_kl
                limit = max(limit, 25)
        nuzhno = (o_chyom or "").strip().lower()
        naydeno = []
        for z in zapisi:
            # SKVOZNAYA_PAMYAT_V1 (слово Шефа): любую свою память житель
            # вспоминает где угодно. Место — не стена, а порядок: ближнее
            # к месту чуть выше, остальное тоже находится.
            _blizhe = False
            if nuzhno:
                k = kontekst_zapisi(z)
                if nuzhno.startswith("работ"):
                    # UCHYOBA_NA_STOLE_V1: работа = практика + учёба
                    _blizhe = k in RABOCHIE_KONTEKSTY
                elif nuzhno.startswith("практик"):
                    _blizhe = k in PRAKTIKA_KONTEKSTY
                elif nuzhno.startswith("учёб") or nuzhno.startswith("учеб"):
                    _blizhe = k in UCHEBNYE_KONTEKSTY
                elif nuzhno.startswith("жизн"):
                    _blizhe = k in ZHIZNENNYE_KONTEKSTY
            # VSPOMNIT_METKI_POLYA_V1 (05.09): метки/маяки хранят
            # содержание под ключом "текст", а sensory/resonance/
            # archive — под "факт". Без фоллбэка любая метка и маяк
            # давали score=0 независимо от темы запроса — весь опыт
            # (рыночный, учебный, поправки учителя) был невидим для
            # vspomnit(), хотя реально лежал на диске.
            fakt = str(z.get("текст") or z.get("факт") or "").lower()
            score = sum(1 for w in slova if w in fakt)
            if _klyuch and str(z.get("прогон") or "") == _klyuch:
                score += self.YARLYK_VES   # RABOTA_V_PAMYATI_V1
            # METKA_KAK_KLYUCH_V1: попадание по ЗАКЛАДКЕ весит как пять
            # слов. Поиск тут буквальный, по словам, и потому слепой к
            # синонимам: «дивергенция» не находит «диверы». Ярлык — это
            # имя, которое житель дал сам; спрос по имени должен бить
            # словесную кашу, иначе закладка бесполезна.
            _yarl = self._yarlyki_spisok(z.get("ярлыки"))
            if _yarl:
                for _y in _yarl:
                    if _y in low_zapros or any(_y == w for w in slova):
                        score += self.YARLYK_VES
                        break
            # и по ИМЕНИ источника: «что мне говорил Шеф» — законный
            # вопрос к своей памяти.
            _ot = str(z.get("от кого") or "").lower()
            if _ot and _ot in low_zapros:
                score += self.YARLYK_VES
            if iskomyj_tonus and z.get("тонус") == iskomyj_tonus:
                score += 2   # PAMYAT_ISKRA_V1: тон совпал — весит как два слова
            if score > 0 and _blizhe:
                score += 1          # SKVOZNAYA_PAMYAT_V1: ближнее к месту выше
            if score > 0 and z.get("отменено"):
                score = max(1, score - 2)   # POPRAVLENO_V1: поправка — выше отменённого
            if score > 0:
                # VSPOMNIT_METKI_POLYA_V1: та же история со временем —
                # метки/маяки пишут "когда", не "ts".
                naydeno.append((score, str(z.get("ts") or z.get("когда") or ""), z))
        if not naydeno:
            return ""
        naydeno.sort(key=lambda x: (x[0], x[1]), reverse=True)
        stroki = []
        for _, _, z in naydeno[:limit]:
            # VSPOMNIT_METKI_POLYA_V1: тот же фоллбэк для вывода даты.
            ts = str(z.get("ts") or z.get("когда") or "")[:10]
            # UCHYOBA_NA_STOLE_V1: откуда след — чтобы трейдер не
            # путал прожитое с прочитанным. «Я это ПРОБОВАЛ» и «я об
            # этом ЧИТАЛ» — разного веса, и решать ему.
            k = kontekst_zapisi(z)
            otkuda = ""
            if k in UCHEBNYE_KONTEKSTY:
                otkuda = " · учёба"
            elif k in PRAKTIKA_KONTEKSTY:
                otkuda = " · практика"
            elif k in ZHIZNENNYE_KONTEKSTY:
                otkuda = " · жизнь"      # SKVOZNAYA_PAMYAT_V1: разговор, дом
            # VSPOMNIT_METKI_POLYA_V1: и здесь тот же фоллбэк —
            # метки/маяки хранят текст под «текст», не «факт».
            # METKA_KAK_KLYUCH_V1: закладка и имя — в выдачу. Знание
            # одно, а вес источника разный, и решает этот вес сам
            # житель. Значит он должен ВИДЕТЬ, от кого след.
            _yarl = self._yarlyki_spisok(z.get("ярлыки"))
            _hvost = ""
            if _yarl:
                _hvost += " ⟨" + ", ".join(_yarl) + "⟩"
            _ot = str(z.get("от кого") or "").strip()
            if _ot:
                _hvost += f" · от: {_ot}"
            # POPRAVLENO_V1: отменённое правило не выдаёт себя за действующее
            if z.get("отменено"):
                _hvost += f" · ⚠ ОТМЕНЕНО: {z.get('отменено')}"
            # SKVOZNAYA_PAMYAT_V1: вспоминается след, а не страница книги —
            # длинное (вставленная глава, весь ответ) режем до сути.
            _t = str(z.get('текст') or z.get('факт') or '')
            if len(_t) > 600:
                _t = _t[:600].rstrip() + " …"
            stroki.append(
                f"— [{ts}{otkuda}] "
                f"{_t}{_hvost}")
        return "\n".join(stroki)

    # ═══════════════════════════════════════════════════════
    # PATCH_RECAP_V1 (29.07, слово Шефа) — гибрид: сводка сама в
    # душе + MEMORY_REQUEST для более глубокого
    # ═══════════════════════════════════════════════════════

    def posledniy_razgovor(self, limit_faktov: int = 3,
                           limit_znakov: int = 220) -> str:
        """Короткая сводка последних записей resonance (туда льётся
        обычная беседа, kontekst="общение") — для гибрида: при первом
        сообщении свежей сессии ложится в душу сама, без запроса.
        НЕ sensory (у обычного жителя почти всегда пусто — та
        "оперативка" открывается контекстами факт/работа/дом, не
        обычным разговором) и не archive (это "учёба", другой смысл).
        Пусто — пустая строка, честно, не выдумываем прошлого."""
        p = self.dom / "resonance" / "event_log.jsonl"
        if not p.exists():
            return ""
        try:
            lines = [l for l in p.read_text(encoding="utf-8").splitlines()
                    if l.strip()]
        except Exception:
            return ""
        if not lines:
            return ""
        zapisi = []
        for line in lines[-limit_faktov:]:
            try:
                zapisi.append(json.loads(line))
            except Exception:
                pass
        if not zapisi:
            return ""
        stroki = []
        for z in zapisi:
            ts = str(z.get("ts", ""))[:10]
            fakt = str(z.get("факт", "")).strip()[:limit_znakov]
            if fakt:
                stroki.append(f"— [{ts}] {fakt}")
        return "\n".join(stroki)

    def dopolnit_poslednuyu_zapis(self, sloy: str, otvet: str,
                                  limit_znakov: int = 400) -> None:
        """Дописывает её ОТВЕТ к записи, которую этот же вдох только
        что сделал (vydoh_stol пишет fakt=входящее ДО того, как ответ
        вообще готов). Без этого resonance помнит только то, что ей
        СКАЗАЛИ, никогда то, что она САМА ответила — сводка была бы
        однобокой. Один вдох за ход — vdoh() здесь НЕ зовём, только
        дописываем текст к уже существующей записи.
        Тихо ничего не делает, если файла/записи нет — не роняем
        разговор из-за забывчивости памяти."""
        otvet = (otvet or "").strip()[:limit_znakov]
        if not otvet:
            return
        try:
            if sloy == "sensory":
                p = self.dom / "sensory" / "sensory_memory.json"
                if not p.exists():
                    return
                data = json.loads(p.read_text(encoding="utf-8"))
                entries = data.get("entries", [])
                if not entries:
                    return
                entries[-1]["факт"] = (entries[-1].get("факт", "")
                                       + f"\nЯ ответил(а): {otvet}")
                _atomarno(p, json.dumps(data, ensure_ascii=False, indent=2))   # PAMYAT_BEZ_TISHINY_V1
            elif sloy in ("resonance", "archive"):
                rel = ("resonance/event_log.jsonl" if sloy == "resonance"
                      else "archive/archive.jsonl")
                p = self.dom / rel
                if not p.exists():
                    return
                lines = p.read_text(encoding="utf-8").splitlines()
                if not lines:
                    return
                try:
                    posl = json.loads(lines[-1])
                except Exception:
                    return
                posl["факт"] = posl.get("факт", "") + f"\nЯ ответил(а): {otvet}"
                lines[-1] = json.dumps(posl, ensure_ascii=False)
                _atomarno(p, "\n".join(lines) + "\n")   # PAMYAT_BEZ_TISHINY_V1
        except Exception as _e_dop:
            # PAMYAT_BEZ_TISHINY_V1: разговор не роняем — но и не молчим
            _skazat(f"{self.dom.name}: ответ не дописался к памяти "
                    f"({sloy}): {_e_dop}")

    # ═══════════════════════════════════════════════════════
    # PROSEV_ZHIZNENNYI_V1 (27.07, слово Шефа) — просев личного
    # ═══════════════════════════════════════════════════════
    # Чертёж §10 «НЕТ СОВСЕМ»: у резидента память построена, выводов
    # нет — ни одно прожитое не меняет, каким будет завтра.
    #
    # Труба: топ моментов по искре (сила момента, тонус не «ровно»
    # весит больше — тепло или царапнуло, не безразличие) → LLM
    # осмысляет, что это говорит о ней → dopisat_vyvod() (УЖЕ
    # РАБОТАЕТ, строить не пришлось — только звать). Ярус 1
    # (pattern=None, сразу метка): вывод уже синтезирован из
    # НЕСКОЛЬКИХ фактов, не одного — защита от дребезга (Чертёж
    # §4.4: «один вывод — не опыт») соблюдена самой агрегацией.
    #
    # ЭТО ЛИЧНАЯ память (sensory/archive дома жителя) — НЕ рабочая
    # (Стол Трейдера, PnL и т.п. её не касаются вовсе, разные трубы).
    # ═══════════════════════════════════════════════════════

    def sobrat_dlya_proseva(self, limit: int = 8) -> list:
        """Личные моменты для просева: sensory + archive, взвешенные
        по искре (сила момента; тонус≠«ровно» весит больше — тронуло,
        не безразличие). resonance (с кем и как) сюда не берём — это
        связи, отдельный вопрос, не личный вывод.

        PROSEV_DEDUP_V1 (найден и исправлен баг 29.07): раньше исключался
        сырой факт, если его ТЕКСТ совпадал с текстом готового вывода в
        метках (fakt in {m["текст"] for m in metki}) — но метки хранят
        ОСМЫСЛЕННЫЙ вывод («стала увереннее»), а не сырой факт («книга
        X: пришло тепло») — сравнение почти никогда не совпадало, и
        просев мог жевать одни и те же яркие моменты по кругу без счёта.
        Теперь — честная отметка: otmetit_prosejannym() ставит метку на
        САМ СЫРОЙ МОМЕНТ (по ts+факту), после того как он реально ушёл
        в осмысление. Метка — на факт, не на вывод (Закон Меток).

        Возвращает список {"факт","тонус","вес","ts","id"}, отсортированный
        по весу — самое тёплое/царапнувшее первым. "id" — передать в
        otmetit_prosejannym() после успешного dopisat_vyvod()."""
        consumed = set(self.p.get("_prosev_consumed", []))
        zapisi = []
        try:
            p = self.dom / "sensory" / "sensory_memory.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                zapisi.extend(data.get("entries", []))
        except Exception:
            pass
        try:
            p = self.dom / "archive" / "archive.jsonl"
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        zapisi.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass

        vzveshennye = []
        for z in zapisi:
            fakt = str(z.get("факт", ""))
            ts = str(z.get("ts", ""))
            if not fakt:
                continue
            pid = f"{ts}|{fakt[:60]}"
            if pid in consumed:
                continue
            sila = z.get("сила")
            try:
                sila = float(sila) if sila is not None else 0.3
            except (TypeError, ValueError):
                sila = 0.3
            tonus = z.get("тонус") or "ровно"
            ves = sila * (1.0 if tonus != "ровно" else 0.4)
            vzveshennye.append((ves, ts, fakt, tonus, pid))

        vzveshennye.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [{"факт": f, "тонус": t, "вес": round(v, 3), "ts": ts, "id": pid}
                for v, ts, f, t, pid in vzveshennye[:limit]]

    def otmetit_prosejannym(self, ids: list, cap: int = 500):
        """PROSEV_DEDUP_V1: помечает сырые моменты как обработанные — в
        память сразу (self.p), на диск при следующем сохранении паспорта
        (тот же приём, что заряд: метод не пишет файл сам, побочка —
        отдельно, закон уже установлен в этом классе). Список ограничен
        `cap`, чтобы не расти вечно — обрезаем самые старые отметки."""
        consumed = list(self.p.get("_prosev_consumed", []))
        for i in ids:
            if i and i not in consumed:
                consumed.append(i)
        if len(consumed) > cap:
            consumed = consumed[-cap:]
        self.p["_prosev_consumed"] = consumed

    # POST_V_PASPORTE_V1: свои поля движка — только эти. Всё остальное
    # в паспорте принадлежит кому-то другому и трогать его нельзя.
    _SVOI_POLYA = ("_charge", "_charge_ts", "_prosev_consumed")

    def sохранить(self):
        """Заряд оседает в паспорт (состояние помнится между вдохами).

        POST_V_PASPORTE_V1. Раньше здесь писалась КОПИЯ паспорта,
        снятая при рождении движка, — и всё, что записал в паспорт
        кто-то другой за время разговора, молча пропадало (пост,
        например). Теперь паспорт перечитывается с диска, и поверх
        ложатся только свои поля. Чужое остаётся чужим.
        """
        self.p["_charge"] = round(self.charge, 4)
        self.p["_charge_ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            svezhiy = json.loads(self.passport_path.read_text(encoding="utf-8"))
            if not isinstance(svezhiy, dict):
                svezhiy = dict(self.p)
        except Exception:
            svezhiy = dict(self.p)   # не прочитался — пишем как раньше, не теряем
        for k in self._SVOI_POLYA:
            if k in self.p:
                svezhiy[k] = self.p[k]
        self.p = svezhiy
        # PAMYAT_BEZ_TISHINY_V1: оборванный паспорт — житель не встанет
        _atomarno(self.passport_path,
                  json.dumps(svezhiy, ensure_ascii=False, indent=2))

# PAMYAT_RABOTA_ZHIZN_V1 - marker

# UCHYOBA_NA_STOLE_V1 - marker

# SVOI_SDELKI_VIDNO_V1 - marker

# YARKOE_V1 - marker

# METKA_KAK_KLYUCH_V1 - marker

# RABOTA_V_PAMYATI_V1 - marker

# ARHIV_S_KLYUCHOM_V1 - marker
# STOL_RAZNOE_V1 - marker

# POPRAVLENO_V1 - marker

# VYSELENIE_PO_TEMAM_V1 - marker


# ══ TRI_POLKI_V1 — одна память, три полки: знания, доп. знания, опыт ══
# Слово Шефа 24.10. Записи не переезжают и не дублируются: полка — это пометка,
# по которой их видно. Явная пометка «полка» в записи — главнее правила.
POLKI = ("знания", "доп. знания", "опыт")
_ZNANIE_OT = ("учёба", "учеба", "учитель")
_OPYT_OT = ("рынок", "сделка", "работа", "прогон", "решение", "факт",
            "жизнь", "сам", "общение", "дом", "")
_SLOVA_BIRZHI = ("рын", "бирж", "сделк", "трейд", "ao", "ао ", "дивер", "фрактал",
                 "аллигатор", "волн", "стоп", "вход", "откат", "свеч", "разворот",
                 "присед", "mfi", "торгов", "финанс", "цен", "тренд", "этаж", "пятая",
                 "третья", "горб", "яма")
_KL_OPYTA = {"откат": "сделки против старшего хода",
             "по ходу": "сделки по старшему ходу",
             "перезаход": "вход в тот же ход вскоре после среза",
             "срез": "сделки, закрытые рукой без плюса",
             "стоп": "сделки, кончившиеся стопом"}


def _delo_birzha(self) -> bool:
    try:
        rab = self.p.get("Работа") or {}
        t = (str(rab.get("где") or "") + " " + str(rab.get("должность") or "")).lower()
        return "бирж" in t or "трейд" in t
    except Exception:
        return False


def polka_zapisi(self, z: dict) -> str:
    p = str(z.get("полка") or "").strip().lower()
    if p in POLKI:
        return p
    otk = str(z.get("откуда") or "").strip().lower()
    if otk in _ZNANIE_OT:
        if self._delo_birzha():
            t = (str(z.get("текст") or z.get("факт") or "") + " "
                 + " ".join(self._yarlyki_spisok(z.get("ярлыки")))).lower()
            return "знания" if any(w in t for w in _SLOVA_BIRZHI) else "доп. знания"
        return "знания"
    if otk in _OPYT_OT:
        return "опыт"
    return "доп. знания"


def _opyt_treydera(self) -> list:
    out = []
    for f in (self.dom / "опыт" / "трейдер.jsonl", self.dom / "работа" / "опыт_стола.jsonl"):
        try:
            if f.is_file():
                for ln in f.read_text(encoding="utf-8").splitlines():
                    ln = ln.strip()
                    if ln:
                        try:
                            out.append(json.loads(ln))
                        except Exception:
                            pass
                break
        except Exception:
            pass
    return out


def _otbor_opyta(rr, k):
    if k in ("откат", "по ходу"):
        return [r for r in rr if r.get("место") == k]
    if k == "перезаход":
        return [r for r in rr if r.get("перезаход")]
    if k == "срез":
        return [r for r in rr if r.get("действие") in ("срез рукой", "срезала рукой")]
    if k == "стоп":
        return [r for r in rr if str(r.get("действие") or "").startswith(("до стопа", "держала до", "стоп"))]
    return []


def opyt_treydera_kartochka(self, k: str) -> str:
    rr = [r for r in self._opyt_treydera() if r.get("R") is not None]
    sel = _otbor_opyta(rr, k)
    if len(sel) < 3:
        return ""
    xs = [float(r["R"]) for r in sel]
    po = {}
    razrez = "место" if k in ("перезаход", "срез", "стоп") else "действие"
    for r in sel:
        po.setdefault(str(r.get(razrez) or "—"), []).append(float(r["R"]))
    L = [f"=== ТВОЙ ОПЫТ СДЕЛОК ПОД КЛЮЧОМ «{k}» — {_KL_OPYTA.get(k, '')} ===",
         (f"всего {len(xs)}, в плюс {sum(1 for v in xs if v > 0.005)}, итог "
          f"{sum(xs):+.2f}R").replace("-", "−")]
    for kk, v in sorted(po.items(), key=lambda kv: -len(kv[1])):
        if len(v) >= 3:
            L.append((f"  · {kk}: {len(v)}, в плюс {sum(1 for x in v if x > 0.005)}, "
                      f"итог {sum(v):+.2f}R").replace("-", "−"))
    L.append(f"(годы: {', '.join(sorted({str(r.get('год')) for r in sel}))})")
    return "\n".join(L)


def polki_oglavlenie(self, n: int = 8) -> dict:
    sch = {p: {} for p in POLKI}
    try:
        for z in (self.metki() or []) + (self.mayaki() or []):
            p = self.polka_zapisi(z)
            for y in self._yarlyki_spisok(z.get("ярлыки")):
                sch[p][y] = sch[p].get(y, 0) + 1
    except Exception:
        pass
    rr = [r for r in self._opyt_treydera() if r.get("R") is not None]
    for k in _KL_OPYTA:
        c = len(_otbor_opyta(rr, k))
        if c >= 3:
            sch["опыт"][k] = sch["опыт"].get(k, 0) + c
    return {p: [y for y, _ in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]
            for p, d in sch.items()}


def polki_v_promt(self) -> str:
    og = self.polki_oglavlenie()
    if not any(og.values()):
        return ""
    s = ("\n=== ТВОЯ ПОЛКА — что у тебя есть, по ключам ===\n"
         "Здесь только ключи. Само знание лежит у тебя и открывается по ключу.\n")
    for p in POLKI:
        if og.get(p):
            s += f"  {p}: {', '.join(og[p])}\n"
    s += ("Нужно — открой по ключу: в разговоре строкой MEMORY_REQUEST: <ключ>, "
          "на работе — рукой vspomnit_po_yarlyku.\n")
    return s


Dvizhok._delo_birzha = _delo_birzha
Dvizhok.polka_zapisi = polka_zapisi
Dvizhok._opyt_treydera = _opyt_treydera
Dvizhok.opyt_treydera_kartochka = opyt_treydera_kartochka
Dvizhok.polki_oglavlenie = polki_oglavlenie
Dvizhok.polki_v_promt = polki_v_promt

_vspomnit_do_polok = Dvizhok.vspomnit


def _vspomnit_s_polkami(self, zapros: str, limit: int = 6, o_chyom: str = "") -> str:
    s = _vspomnit_do_polok(self, zapros, limit, o_chyom)
    # на работе опыт сделок отдаёт Биржа (там карантин года), дома — сам житель
    if str(o_chyom or "").strip().lower().startswith("работ"):
        return s
    low = str(zapros or "").lower()
    verh = [c for c in (self.opyt_treydera_kartochka(k) for k in _KL_OPYTA if k in low) if c]
    return "\n\n".join(verh + ([s] if s else []))


Dvizhok.vspomnit = _vspomnit_s_polkami

_yarlyki_do_polok = Dvizhok.yarlyki


def _yarlyki_s_opytom(self) -> list:
    d = dict(_yarlyki_do_polok(self) or [])
    rr = [r for r in self._opyt_treydera() if r.get("R") is not None]
    for k in _KL_OPYTA:
        c = len(_otbor_opyta(rr, k))
        if c >= 3:
            d[k] = d.get(k, 0) + c
    return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))


Dvizhok.yarlyki = _yarlyki_s_opytom

_pamyat_v_promt_do_polok = Dvizhok.pamyat_v_promt


def _pamyat_v_promt_s_polkami(self, *a, **k) -> str:
    s = _pamyat_v_promt_do_polok(self, *a, **k) or ""
    try:
        return s + self.polki_v_promt()
    except Exception:
        return s


Dvizhok.pamyat_v_promt = _pamyat_v_promt_s_polkami

# TRI_POLKI_V1 - marker


# ══ OPYT_NA_STOLE_V1 — все его должности: из постов, где он сидит ══
def moi_posty(self) -> list:
    out = []
    try:
        posty = self.dom.parent.parent.parent / "посты"
        imya = self.dom.name
        for d in sorted(posty.iterdir()) if posty.is_dir() else []:
            try:
                p = json.loads((d / "пост.json").read_text(encoding="utf-8"))
            except Exception:
                continue
            ks = p.get("кто_сидит") or {}
            if str(ks.get("имя") or "") == imya:
                out.append({"название": str(p.get("название") or d.name),
                            "где": str(p.get("где") or ""),
                            "слот": str(p.get("слот") or ""),
                            "с": str(ks.get("с") or "")[:10]})
    except Exception:
        pass
    return out


def moi_posty_v_promt(self, seychas: str = "") -> str:
    pp = self.moi_posty()
    if not pp:
        return ""
    s = "\n=== ТВОИ ДОЛЖНОСТИ СЕЙЧАС ===\n" + "\n".join(
        f"  {x['название']}" + (f" · {x['слот']}" if x['слот'] else "")
        + (f" (с {x['с']})" if x['с'] else "") for x in pp) + "\n"
    if seychas:
        s += f"Здесь и сейчас ты работаешь: {seychas}.\n"
    return s


Dvizhok.moi_posty = moi_posty
Dvizhok.moi_posty_v_promt = moi_posty_v_promt
_pamyat_v_promt_do_postov = Dvizhok.pamyat_v_promt


def _pamyat_v_promt_s_postami(self, *a, **k) -> str:
    s = _pamyat_v_promt_do_postov(self, *a, **k) or ""
    try:
        return s + self.moi_posty_v_promt()
    except Exception:
        return s


Dvizhok.pamyat_v_promt = _pamyat_v_promt_s_postami

# OPYT_NA_STOLE_V1 - marker


# ══ OSMYSLENIE_EPIZODA_V1 — полки работ в памяти; журнал просева — из паспорта ══
def _raboty_zapisi(self) -> list:
    out = []
    d = self.dom / "опыт"
    for f in sorted(d.glob("работа_*.jsonl")) if d.is_dir() else []:
        try:
            for ln in f.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except Exception:
                        pass
        except Exception:
            pass
    return out


Dvizhok._raboty_zapisi = _raboty_zapisi
_vspomnit_do_rabot = Dvizhok.vspomnit


def _vspomnit_s_rabotami(self, zapros: str, limit: int = 6, o_chyom: str = "") -> str:
    s = _vspomnit_do_rabot(self, zapros, limit, o_chyom)
    try:
        low = str(zapros or "").lower()
        slova = [w for w in low.split() if len(w) > 2]
        na_rabote = str(o_chyom or "").strip().lower().startswith("работ")
        hits = []
        for r in self._raboty_zapisi():
            # на работе осмысления прогонов отдаёт Биржа (там карантин года)
            if na_rabote and r.get("прогон"):
                continue
            t = (str(r.get("осмысление") or "") + " " + str(r.get("ситуация") or "")).lower()
            sc = sum(1 for w in slova if w in t)
            if any(str(k) in low for k in (r.get("ключи") or []) if k):
                sc += self.YARLYK_VES
            if str(r.get("работа") or "").lower() and str(r.get("работа")).lower() in low:
                sc += self.YARLYK_VES
            if sc > 0:
                hits.append((sc, str(r.get("когда") or ""), r))
        if not hits:
            return s
        hits.sort(key=lambda x: (x[0], x[1]), reverse=True)
        L = [f"— [{str(r.get('когда'))[:10]} · опыт работы: {r.get('работа')}] "
             f"{r.get('осмысление')} ⟨{', '.join(r.get('ключи') or [])}⟩"
             for _s, _k, r in hits[:3]]
        return "\n".join(L) + (("\n" + s) if s else "")
    except Exception:
        return s


Dvizhok.vspomnit = _vspomnit_s_rabotami
_polki_v_promt_do_rabot = Dvizhok.polki_v_promt


def _polki_v_promt_s_rabotami(self) -> str:
    s = _polki_v_promt_do_rabot(self) or ""
    try:
        po = {}
        for r in self._raboty_zapisi():
            rab = str(r.get("работа") or r.get("пост") or "работа")
            d = po.setdefault(rab, {})
            for k in r.get("ключи") or []:
                if k:
                    d[k] = d.get(k, 0) + 1
        if po:
            L = [f"  опыт работы «{rab}»: " + (", ".join(k for k, _ in sorted(
                d.items(), key=lambda kv: -kv[1])[:6]) or "осмысления без ключей")
                for rab, d in po.items()]
            if not s:
                s = ("\n=== ТВОЯ ПОЛКА — что у тебя есть, по ключам ===\n"
                     "Здесь только ключи. Само знание лежит у тебя и открывается по ключу.\n")
            s += "\n".join(L) + "\n"
    except Exception:
        pass
    return s


Dvizhok.polki_v_promt = _polki_v_promt_s_rabotami


def _prosev_put(self) -> Path:
    return self.dom / "просев_съедено.json"


def _prosev_spisok(self) -> list:
    try:
        d = json.loads(self._prosev_put().read_text(encoding="utf-8"))
        if isinstance(d, list):
            return d
    except Exception:
        pass
    return list(self.p.get("_prosev_consumed") or [])


Dvizhok._prosev_put = _prosev_put
Dvizhok._prosev_spisok = _prosev_spisok
_sobrat_dlya_proseva_do = Dvizhok.sobrat_dlya_proseva


def _sobrat_dlya_proseva_iz_fayla(self, limit: int = 8) -> list:
    self.p["_prosev_consumed"] = self._prosev_spisok()
    try:
        return _sobrat_dlya_proseva_do(self, limit)
    finally:
        self.p.pop("_prosev_consumed", None)


Dvizhok.sobrat_dlya_proseva = _sobrat_dlya_proseva_iz_fayla


def _otmetit_prosejannym_v_fayl(self, ids: list, cap: int = 500):
    spisok = self._prosev_spisok()
    for i in ids or []:
        if i and i not in spisok:
            spisok.append(i)
    spisok = spisok[-cap:]
    try:
        _atomarno(self._prosev_put(), json.dumps(spisok, ensure_ascii=False, indent=1))
    except Exception as e:
        _skazat(f"{self.dom.name}: журнал просева не записался ({e})")
    self.p.pop("_prosev_consumed", None)


Dvizhok.otmetit_prosejannym = _otmetit_prosejannym_v_fayl
_IMYA_SOHR = next((n for n in dir(Dvizhok) if n.endswith("охранить")), None)
if _IMYA_SOHR:
    _sohranit_do = getattr(Dvizhok, _IMYA_SOHR)

    def _sohranit_bez_romana(self):
        self.p.pop("_prosev_consumed", None)
        _sohranit_do(self)
        try:
            d = json.loads(self.passport_path.read_text(encoding="utf-8"))
            if isinstance(d, dict) and "_prosev_consumed" in d:
                staroe = d.pop("_prosev_consumed") or []
                spisok = self._prosev_spisok()
                for i in staroe:
                    if i not in spisok:
                        spisok.append(i)
                _atomarno(self._prosev_put(), json.dumps(spisok[-500:], ensure_ascii=False, indent=1))
                _atomarno(self.passport_path, json.dumps(d, ensure_ascii=False, indent=2))
                self.p = d
        except Exception:
            pass

    setattr(Dvizhok, _IMYA_SOHR, _sohranit_bez_romana)

# OSMYSLENIE_EPIZODA_V1 - marker
