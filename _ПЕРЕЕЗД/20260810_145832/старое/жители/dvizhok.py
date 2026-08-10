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
from typing import Optional   # PYLANCE_GIGIENA_V1
from pathlib import Path
from datetime import datetime, timezone

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
                    except Exception:
                        data = {"entries": []}
                data.setdefault("entries", []).append(zapis)
                p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
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
        except Exception:
            pass  # память не должна ронять дыхание — пропускаем тихо

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
                return d if isinstance(d, list) else []
        except Exception:
            pass
        return []

    def _pisat_etazh(self, path: Path, data: list):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def metki(self) -> list:
        """Весь второй этаж — нажитое. Список объектов."""
        return self._chitat_etazh(self._metki_path())

    def mayaki(self) -> list:
        """Третий этаж — черновики момента. Гаснут, не набрав повтора."""
        return self._chitat_etazh(self._mayaki_path())

    def _metki_v_stol(self) -> list:
        """Свежие METKI_V_STOL меток — для промпта. НЕ все: контекст
        Биржи уже 25к символов, а метки растут всю жизнь. Маленький
        стол + право дотянуться (MEMORY_REQUEST) — дешевле и честнее
        по природе: живой человек тоже не держит всю жизнь в голове."""
        m = self.metki()
        m.sort(key=lambda x: str(x.get("когда", "")))
        return m[-self.METKI_V_STOL:]

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

    def _archive_zapis(self, fakt: str, prichina: str):
        """Общий писчик в archive.jsonl — и вытесненные якоря, и
        вытесненные черновики уходят сюда, не в забвение."""
        try:
            (self.dom / "archive").mkdir(parents=True, exist_ok=True)
            ap = self.dom / "archive" / "archive.jsonl"
            with open(ap, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc)
                          .isoformat(timespec="seconds"),
                    "слой": "archive",
                    "факт": fakt,
                    "причина": prichina,
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass   # архив не должен ронять запись опыта

    def dopisat_vyvod(self, vyvod: str, limit: int = 10,
                      pattern: Optional[str] = None,   # PYLANCE_GIGIENA_V1
                      otkuda: str = "рынок") -> dict:
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
        vyvod = (vyvod or "").strip()
        if not vyvod:
            return {"дописано": False, "причина": "пустой вывод"}

        metki  = self.metki()
        mayaki = self.mayaki()
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # дубль текста — ни в одном этаже не плодим
        if any(m.get("текст") == vyvod for m in metki):
            return {"дописано": False, "причина": "уже среди меток",
                    "меток": len(metki)}
        if any(m.get("текст") == vyvod for m in mayaki):
            return {"дописано": False, "причина": "уже среди маяков",
                    "маяков": len(mayaki)}

        # РОД тоже сверяем: если житель «вывел» то, что и так его натура —
        # это не открытие, а подтверждение. Не плодим строку.
        if vyvod in self._yakorya_spisok(self.p.get("Anchor_Points", "") or ""):
            return {"дописано": False,
                    "причина": "это его род (Anchor_Points), не нажитое"}

        def _lech_metkoy(txt, patt, raz):
            metki.append({"текст": txt, "паттерн": patt, "откуда": otkuda,
                          "когда": now_iso, "раз": raz})
            ushlo = []
            if len(metki) > self.METKI_CAP:
                ushlo = metki[:len(metki) - self.METKI_CAP]
                del metki[:len(metki) - self.METKI_CAP]
                for old in ushlo:
                    self._archive_zapis(old.get("текст", ""),
                                        "метка вытеснена (лимит нажитого)")
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
            raz = found["раз"]
        else:
            found = {"текст": vyvod, "паттерн": pattern, "откуда": otkuda,
                     "раз": 1, "первый_раз": now_iso, "последний_раз": now_iso}
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
                    d.get("текст", ""),
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
                if len(metki) > self.METKI_CAP:
                    for old in metki[:len(metki) - self.METKI_CAP]:
                        self._archive_zapis(old.get("текст", ""),
                                            "метка вытеснена (лимит нажитого)")
                    del metki[:len(metki) - self.METKI_CAP]
                self._pisat_etazh(self._metki_path(), metki)
                self._pisat_etazh(self._mayaki_path(), mayaki)
                return {"учтено": True, "исход": "маяк стал меткой",
                        "паттерн": pattern, "за": za, "против": protiv}

            if protiv >= self.OPROVERZHENIY_DO_GASHENIYA and protiv > za:
                mayaki = [x for x in mayaki if x is not m]
                self._archive_zapis(
                    m.get("текст", ""),
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
                    mt.get("текст", ""),
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
                self._archive_zapis(b.get("текст", ""),
                                    "заменено новой поправкой учителя")
            metki = [m for m in metki if m.get("паттерн") != pattern]

        metki.append({
            "текст": tekst,
            "паттерн": pattern,
            "откуда": "учитель",
            "когда": now_iso,
            "раз": 1,
        })
        if len(metki) > self.METKI_CAP:
            for old in metki[:len(metki) - self.METKI_CAP]:
                self._archive_zapis(old.get("текст", ""),
                                    "метка вытеснена (лимит нажитого)")
            del metki[:len(metki) - self.METKI_CAP]
        self._pisat_etazh(self._metki_path(), metki)
        return {"легло": True, "этаж": "метки", "паттерн": pattern}

    # ═══════════════════════════════════════════════════════
    # PAMYAT_V_PROMT_VEZDE_V1 — НАЖИТОЕ СЛОВАМИ, ДЛЯ ПРОМПТА
    # ═══════════════════════════════════════════════════════

    ZNANIE_OTKUDA = ("учёба", "учеба", "учитель")

    def pamyat_v_promt(self, metok: int = 14, chernovikov: int = 8) -> str:
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
                  if m.get("откуда") not in self.ZNANIE_OTKUDA and _tekst(m)]

        znanie = znanie[-metok:]
        chernoviki = chernoviki[-chernovikov:]
        o_sebe = o_sebe[-metok:]

        if not (znanie or chernoviki or o_sebe):
            return ""

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

    def vspomnit(self, zapros: str, limit: int = 6) -> str:
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
        # оценка: сколько слов запроса встретилось в факте записи
        naydeno = []
        for z in zapisi:
            fakt = str(z.get("факт", "")).lower()
            score = sum(1 for w in slova if w in fakt)
            if iskomyj_tonus and z.get("тонус") == iskomyj_tonus:
                score += 2   # PAMYAT_ISKRA_V1: тон совпал — весит как два слова
            if score > 0:
                naydeno.append((score, str(z.get("ts", "")), z))
        if not naydeno:
            return ""
        naydeno.sort(key=lambda x: (x[0], x[1]), reverse=True)
        stroki = []
        for _, _, z in naydeno[:limit]:
            ts = str(z.get("ts", ""))[:10]
            stroki.append(f"— [{ts}] {z.get('факт', '')}")
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
                p.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                            encoding="utf-8")
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
                p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

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
        self.passport_path.write_text(
            json.dumps(svezhiy, ensure_ascii=False, indent=2), encoding="utf-8")
