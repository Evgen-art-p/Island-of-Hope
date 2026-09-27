# -*- coding: utf-8 -*-
# OTCHYOT_PROGONA_V1
"""
ОТЧЁТ ПРОГОНА — след, по которому можно судить.

ЗАЧЕМ
    Прогон говорил в чат и растворялся. Нельзя было ни пересчитать, ни
    сравнить два прогона, ни найти кадр к конкретному месту: все кадры
    валились в общую папку вперемешку.

ЗАКОН ЭТОГО ФАЙЛА
    Отчёт ЗАПИСЫВАЕТ, а не судит. Никаких «вход был хорош» и «стоило
    войти». Числа, слова трейдера и картинка — судит Шеф.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

OKNO = (100, 140)      # канон Шефа: столько баров держит волну читаемой


class Otchyot:
    """Одна папка на один прогон: отчёт.md, места.jsonl, кадры/."""

    def __init__(self, koren: Path, ceh: str):
        self.kogda = datetime.now()
        self.papka = (koren / "GRONDHEIM_CITY" / "Биржа" / "цеха" / ceh
                      / "прогоны" / self.kogda.strftime("%Y%m%d_%H%M%S"))
        self.kadry = self.papka / "кадры"
        self.ceh = ceh
        self.mesta: list = []
        try:
            self.kadry.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[ОТЧЁТ] папку не завести: {e}")
        # ITOG_SDELOK_V1: сколько строк было в журнале закрытий на
        # старте. Всё, что прибавится, — сделки ЭТОГО прогона.
        # По времени отбирать нельзя: в журнале бар рынка, а
        # прогоны ходят по истории вразнобой.
        self.zhurnal_bylo = self._dlina_zhurnala()

    # ── одно место ──
    def zapisat(self, k: dict, slot: str, imya: str, symbol: str,
                etazh: str, otvet: dict, kadr_put=None):
        signal = (otvet or {}).get("signal") or {}
        verdikt = ""
        prichina = ""
        for kl, zn in signal.items():
            if kl.endswith("_verdict") and zn:
                verdikt = str(zn)
            if kl.endswith("_reason") and zn:
                prichina = str(zn)
        # ZHURNAL_PROGONA_V1: сохраняем ДЕЙСТВИЕ и цены. Раньше в
        # место шёл только вердикт, и «держу позицию» (HOLD) было
        # неотличимо от «работать не стану» (WAIT).
        deystvie = ""
        cena_vhoda = None
        stop_vhoda = None
        for kl, zn in signal.items():
            if kl.endswith("_action") and zn:
                deystvie = str(zn).upper()
            if kl.endswith("_entry") and zn is not None:
                cena_vhoda = zn
            if kl.endswith("_stop") and zn is not None:
                stop_vhoda = zn
        skazal = ((otvet or {}).get("narrative") or "").strip()
        if not prichina:
            prichina = skazal[:200]

        imya_kadra = ""
        if kadr_put:
            try:
                p = Path(kadr_put)
                if p.exists():
                    imya_kadra = f"{len(self.mesta) + 1:02d}_{imya}_{p.name}"
                    shutil.copy2(p, self.kadry / imya_kadra)
            except Exception as e:
                print(f"[ОТЧЁТ] кадр не лёг: {e}")

        # VOLNA_NA_STOLE_V1: даты. Шаги наблюдения подписывались датой
        # КАНДИДАТА — в прогоне 20.08 места 10, 11 и 12 вышли с одной
        # датой 2025.11.21 12:00, хотя это три разных бара (видно по
        # дневнику самой Нины: там стоит 2025.11.27 04:00).
        # Берём бар, на котором трейдера спросили НА САМОМ ДЕЛЕ; дату
        # места оставляем отдельно, она тоже нужна.
        _nastoyashchiy_bar = ""
        try:
            from hooks import load_trading_state as _lts
            _nastoyashchiy_bar = str(
                ((_lts() or {}).get("рынок") or {}).get("бар") or "")
        except Exception:
            pass
        # CHISLA_V_MESTO_V1: показатели берём СО СТОЛА трейдера.
        # Мозг отдаёт его целиком ключом "table" — это ровно то,
        # что трейдер видел. Кандидат в прогоне таких полей не
        # несёт, оттого в 285 местах подряд стояло None.
        # Пересчитывать заново нельзя: попадём на другой бар и
        # запишем неправду — хуже, чем пусто.
        _st = {}
        _pr = {}
        try:
            _st = (otvet or {}).get("table") or {}
            _pr = _st.get("приборы") or {}
        except Exception:
            pass
        _rb = _pr.get("разворотный_бар") or {}
        _ao = _pr.get("ao") or {}
        _fr = _pr.get("фракталы") or {}

        def _ili(iz_kandidata, iz_stola):
            """Кандидат главнее — он ближе к моменту находки."""
            return iz_kandidata if iz_kandidata is not None else iz_stola

        _volna = k.get("длина_волны")
        self.mesta.append({
            "когда_на_рынке": _nastoyashchiy_bar or k.get("дата", ""),
            "место_найдено_на": k.get("дата", ""),
            "кто": imya, "слот": slot,
            "инструмент": symbol, "этаж": etazh,
            "разворотный": _ili(k.get("разворотный"),
                                _rb.get("сторона")),
            "цена_разворотного": _ili(k.get("цена_разворотного"),
                                      _rb.get("цена")),
            "длина_волны": _volna,
            "в_окне_100_140": bool(
                _volna and OKNO[0] <= _volna <= OKNO[1]),
            "компас": _ili(k.get("компас"), _pr.get("вода")),
            # ── голые показания стола, без суждений ──
            "вода_этажи": _pr.get("вода_этажи"),
            "вода_почему": _pr.get("вода_почему"),
            "направление_рабочего": _pr.get("направление_рабочего"),
            "ao_значение": _ao.get("значение"),
            "ao_прошлое": _ao.get("прошлое"),
            "ao_растёт": _ao.get("растёт"),
            "фрактал_вверх": _fr.get("вверх"),
            "фрактал_вниз": _fr.get("вниз"),
            "цена_бара": _pr.get("цена"),
            "бар_времени": _pr.get("бар"),
            "шаг_цены": _pr.get("point"),
            # NE_TERYAT_RESHENIE_V1: «без вердикта» звучало безобидно и
            # пряталось за нулём во входах — а за ним стоял потерянный
            # вход. Называем прямо.
            "вердикт": verdikt or ("промолчал" if not skazal
                                   else "ОТВЕТ НЕ РАЗОБРАН"),
            "действие": deystvie,          # ZHURNAL_PROGONA_V1
            "цена_входа": cena_vhoda,
            "стоп_входа": stop_vhoda,
            "причина": prichina,
            "сказал": skazal,
            "кадр": imya_kadra,
        })

    # ── итог ──
    def zakryt(self) -> Path | None:
        if not self.mesta:
            return None
        try:
            (self.papka / "места.jsonl").write_text(
                "\n".join(json.dumps(m, ensure_ascii=False)
                          for m in self.mesta), encoding="utf-8")
            (self.papka / "отчёт.md").write_text(self._svodka(),
                                                 encoding="utf-8")
        except Exception as e:
            print(f"[ОТЧЁТ] не записался: {e}")
            return None
        return self.papka

    # ── RASKLAD_PROGONA_V1: расклад по прогону ──
    # Шеф считал это руками по места.jsonl. Теперь выходит само.
    # Закон файла соблюдён: отчёт кладёт ЧИСЛА и СЛОВА трейдера,
    # приговоров не выносит.

    _PRIZNAKI_SHODYATSYA = (
        "все три условия", "три условия сход", "условия сход",
        "условия сошлись", "всё сходится", "все сходится",
        "все совпад", "картина сложил",
    )

    @staticmethod
    def _punkt(cena: float) -> float:
        """Размер пункта по величине цены. Отчёт скажет, какой взял."""
        c = abs(float(cena))
        if c < 20:          # EURUSD, GBPUSD и прочие пятизнаки
            return 0.00001
        if c < 500:         # иеновые пары
            return 0.001
        return 0.01         # золото и индексы

    def _sdelki(self) -> list:
        """Собирает сделки: вход и всё, что к нему прицепилось."""
        sdelki = []
        otkrytye = {}
        for nomer, m in enumerate(self.mesta, 1):
            d = str(m.get("действие") or "").upper()
            v = str(m.get("вердикт") or "").upper()
            para = f"{m.get('инструмент')} {m.get('этаж')}"
            vh = m.get("цена_входа")
            st = m.get("стоп_входа")

            vhod = (d == "ENTER") or (v in ("APPROVED", "ENTER", "OK")
                                      and d not in ("MOVE_STOP", "HOLD",
                                                    "ADD", "CLOSE"))
            if vhod and vh and st:
                s = {"номер": nomer, "когда": m.get("когда_на_рынке", ""),
                     "пара": para, "вход": float(vh), "стоп": float(st),
                     "перенос": None, "перенос_когда": "",
                     "закрыт": False}
                sdelki.append(s)
                otkrytye[para] = s
                continue

            if d == "MOVE_STOP" and st and para in otkrytye:
                otkrytye[para]["перенос"] = float(st)
                otkrytye[para]["перенос_когда"] = m.get("когда_на_рынке", "")
            if d == "CLOSE" and para in otkrytye:
                otkrytye[para]["закрыт"] = True
                otkrytye.pop(para, None)
        return sdelki

    # ── ITOG_SDELOK_V1: чем кончились сделки ──
    # Город всё считает сам и кладёт в trading_pnl.jsonl: цену выхода,
    # причину, pnl_r от ПЕРВОНАЧАЛЬНОГО риска. Отчёту оставалось
    # только заглянуть в журнал — раньше он этого не делал.

    @staticmethod
    def _zhurnal_put():
        try:
            from hooks import PNL_PATH
            return Path(PNL_PATH)
        except Exception:
            return None

    @staticmethod
    def _dlina_zhurnala() -> int:
        p = Otchyot._zhurnal_put()
        if not p or not p.exists():
            return 0
        try:
            with open(p, encoding="utf-8") as f:
                return sum(1 for stroka in f if stroka.strip())
        except Exception:
            return 0

    def _zakrytiya(self) -> list:
        """Сделки, закрывшиеся за ЭТОТ прогон — прибавка к журналу."""
        p = self._zhurnal_put()
        if not p or not p.exists():
            return []
        try:
            with open(p, encoding="utf-8") as f:
                stroki = [x for x in f if x.strip()]
        except Exception as e:
            print(f"[ОТЧЁТ] журнал закрытий не прочитался: {e}")
            return []
        out = []
        for x in stroki[int(getattr(self, "zhurnal_bylo", 0) or 0):]:
            try:
                out.append(json.loads(x))
            except Exception:
                pass
        return out

    def _itog_sdelok(self) -> list:
        zakr = self._zakrytiya()
        # PUNKTY_V_OTCHYOTE_V1: пункты — разница цены в минимальных шагах.
        def _punkty(_z):
            _pp = _z.get("pnl_price")
            if not isinstance(_pp, (int, float)):
                return None
            _s = str(_z.get("symbol") or "").upper()
            _pt = (0.001 if ("JPY" in _s or "XAG" in _s) else
                   0.01 if ("XAU" in _s or "GOLD" in _s) else 0.00001)
            return int(round(_pp / _pt))

        if not zakr:
            return [
                "### Чем кончилось", "",
                "За этот прогон ни одна сделка не закрылась. Либо входов "
                "не было, либо открытые дожили до конца отрезка — тогда "
                "их результат появится в следующем прогоне, когда рынок "
                "до них дойдёт.", "",
                "Считать winrate и просадку не из чего: закрытий ноль.",
                "",
            ]

        # pnl_r может быть None (трейлинг увёл риск в ноль) — такие
        # в счёт R не берём, но из списка не прячем.
        r = [x.get("pnl_r") for x in zakr]
        r_est = [float(v) for v in r if isinstance(v, (int, float))]
        plyusy = [v for v in r_est if v > 0]
        minusy = [v for v in r_est if v < 0]

        s = ["### Чем кончилось", ""]
        s.append("| что | сколько |")
        s.append("|---|---|")
        s.append(f"| сделок закрыто | {len(zakr)} |")
        if r_est:
            s.append(f"| в плюс | {len(plyusy)} |")
            s.append(f"| в минус | {len(minusy)} |")
            s.append(f"| доля прибыльных | "
                     f"{len(plyusy) / len(r_est) * 100:.0f}% |")
            s.append(f"| итог в R | {sum(r_est):+.2f}R |")
            _pk_vse = [_punkty(x) for x in zakr]
            _pk_vse = [v for v in _pk_vse if v is not None]
            if _pk_vse:
                s.append(f"| итог в пунктах | {sum(_pk_vse):+d} |")
            s.append(f"| в среднем на сделку | "
                     f"{sum(r_est) / len(r_est):+.2f}R |")
            if minusy:
                pf = sum(plyusy) / abs(sum(minusy))
                s.append(f"| на рубль потерь заработано | {pf:.2f} |")
            elif plyusy:
                s.append("| на рубль потерь заработано | потерь не было |")
            # худшая просадка: самый глубокий провал кривой счёта
            pik = 0.0
            schyot = 0.0
            prosadka = 0.0
            for v in r_est:
                schyot += v
                pik = max(pik, schyot)
                prosadka = min(prosadka, schyot - pik)
            s.append(f"| худшая просадка | {prosadka:.2f}R |")
        if len(r_est) != len(zakr):
            s.append(f"| без R (риск ушёл в ноль) | "
                     f"{len(zakr) - len(r_est)} |")
        s.append("")

        # чем именно закрывались
        prichiny: dict = {}
        for x in zakr:
            p = str(x.get("close_reason") or "?")
            prichiny[p] = prichiny.get(p, 0) + 1
        po_russki = {"STOP_LOSS": "выбил стоп",
                     "EXIT_BELL": "колокол на выход",
                     "MANUAL_CLOSE": "закрыл сам"}
        s.append("Чем закрывались: " + ", ".join(
            f"{po_russki.get(k, k)} — {v}"
            for k, v in sorted(prichiny.items(), key=lambda x: -x[1])))
        s.append("")

        # таблица
        s.append("| # | закрыта | пара | кто | вход | выход | чем | R | пункты |")
        s.append("|---|---|---|---|---|---|---|---|---|")
        for i, x in enumerate(zakr, 1):
            rv = x.get("pnl_r")
            rs = f"{float(rv):+.2f}" if isinstance(rv, (int, float)) else "—"
            _pk1 = _punkty(x)
            ps = f"{_pk1:+d}" if _pk1 is not None else "—"
            s.append(f"| {i} | {x.get('closed_at', '—')} | "
                     f"{x.get('symbol', '—')} {x.get('timeframe', '')} | "
                     f"{x.get('trader', '—')} | {x.get('entry', '—')} | "
                     f"{x.get('exit', '—')} | "
                     f"{po_russki.get(str(x.get('close_reason')), '?')} | "
                     f"{rs} | {ps} |")
        s.append("")
        s.append("R считается от риска НА ВХОДЕ — от первого стопа, а не "
                 "от подвинутого трейлингом. Иначе перенос стопа сам себе "
                 "рисовал бы результат.")
        s.append("")
        return s

    def _rasklad(self) -> list:
        n = len(self.mesta)
        if not n:
            return []

        vhody = [m for m in self.mesta
                 if str(m.get("действие") or "").upper() == "ENTER"
                 or str(m.get("вердикт") or "").upper() in ("APPROVED",
                                                            "ENTER", "OK")]
        otkazy = [m for m in self.mesta
                  if str(m.get("вердикт") or "").upper() in ("REJECTED",
                                                             "WAIT")]
        sboi = [i for i, m in enumerate(self.mesta, 1)
                if not (m.get("сказал") or "").strip()
                or str(m.get("вердикт") or "") in ("промолчал",
                                                   "ОТВЕТ НЕ РАЗОБРАН")]
        sdelki = self._sdelki()

        s = ["## Расклад", ""]
        s.append("| что | сколько |")
        s.append("|---|---|")
        s.append(f"| мест пройдено | {n} |")
        s.append(f"| входов | {len(sdelki)} |")
        s.append(f"| отказов (WAIT / REJECTED) | {len(otkazy)} |")
        s.append(f"| конверсия мест во входы | "
                 f"{len(sdelki) / n * 100:.1f}% |")
        s.append(f"| сделок закрыто | "
                 f"{sum(1 for x in sdelki if x['закрыт'])} |")
        if sboi:
            s.append(f"| мест без слов (сбой записи) | {len(sboi)} |")
        s.append("")

        if len(vhody) != len(sdelki):
            s.append(f"> Мест с вердиктом входа: {len(vhody)}, а сделок "
                     f"собралось {len(sdelki)} — у остальных нет цены "
                     f"или стопа.")
            s.append("")

        # ── риск по сделкам ──
        if sdelki:
            s.append("### Риск по сделкам")
            s.append("")
            for nomer, x in enumerate(sdelki, 1):
                p = self._punkt(x["вход"])
                dlinnaya = x["стоп"] < x["вход"]
                storona = "LONG" if dlinnaya else "SHORT"
                risk = abs(x["вход"] - x["стоп"])
                risk_p = risk / p
                s.append(f"**Сделка {nomer} — {storona}, {x['пара']}, "
                         f"{x['когда']}**")
                s.append("")
                s.append(f"- вход {x['вход']}, стоп {x['стоп']} → риск "
                         f"**{risk_p:.0f} п. = 1R**")
                if x["перенос"] is not None and risk:
                    ns = x["перенос"]
                    hod = (ns - x["вход"]) if dlinnaya else (x["вход"] - ns)
                    s.append(f"- {x['перенос_когда']} стоп перенесён на "
                             f"{ns} → **{hod / risk:+.2f}R** "
                             f"гарантии, если стоп сработает")
                if not x["закрыт"]:
                    s.append("- выхода в записях нет — чем кончилось, "
                             "неизвестно")
                s.append("")
            s.append(f"Пункт взят как {self._punkt(sdelki[0]['вход'])} — "
                     f"по величине цены. Направление — из положения стопа, "
                     f"не из слов.")
            s.append("")

        s += self._itog_sdelok()

        # ── отказ при сошедшихся условиях ──
        spornye = []
        for i, m in enumerate(self.mesta, 1):
            if str(m.get("вердикт") or "").upper() not in ("REJECTED",
                                                           "WAIT"):
                continue
            slova = ((m.get("сказал") or "") + " "
                     + (m.get("причина") or "")).lower()
            if any(pr in slova for pr in self._PRIZNAKI_SHODYATSYA):
                spornye.append((i, m))
        if spornye:
            s.append("### Отказ при сошедшихся условиях")
            s.append("")
            s.append(f"Мест, где вердикт — отказ, а в собственных словах "
                     f"трейдера есть признак сошедшихся условий: "
                     f"**{len(spornye)}**.")
            s.append("")
            s.append("Отчёт не судит, входить было надо или нет. Он кладёт "
                     "рядом вердикт и слова — смотри сам.")
            s.append("")
            for i, m in spornye[:15]:
                slova = (m.get("сказал") or m.get("причина") or "").strip()
                s.append(f"- **{i}. {m.get('когда_на_рынке')}** · "
                         f"{m.get('вердикт')} — {slova[:160]}")
            if len(spornye) > 15:
                s.append(f"- … ещё {len(spornye) - 15} (все — в места.jsonl)")
            s.append("")

        return s

    def _svodka(self) -> str:
        n = len(self.mesta)
        dliny = [m["длина_волны"] for m in self.mesta if m["длина_волны"]]
        v_okne = sum(1 for m in self.mesta if m["в_окне_100_140"])
        vhody = [m for m in self.mesta
                 if str(m["вердикт"]).upper() in ("APPROVED", "ENTER", "OK")]
        otkazy = [m for m in self.mesta
                  if str(m["вердикт"]).upper() in ("REJECTED", "WAIT")]

        s = [f"# Прогон {self.kogda:%Y-%m-%d %H:%M} · цех {self.ceh}", ""]
        s.append(f"Мест пройдено: **{n}** · входов: **{len(vhody)}** · "
                 f"отказов: **{len(otkazy)}**")
        if dliny:
            dliny_s = sorted(dliny)
            s.append(f"Длина волны: от {dliny_s[0]} до {dliny_s[-1]} баров, "
                     f"середина {dliny_s[len(dliny_s) // 2]}")
            s.append(f"В окне 100-140: **{v_okne} из {n}** — на остальных "
                     f"масштаб не тот, и трейдер это видит.")
        s.append("")

        s += self._rasklad()

        # кто сколько
        po_lyudyam: dict = {}
        for m in self.mesta:
            d = po_lyudyam.setdefault(m["кто"], {"всего": 0, "входы": 0})
            d["всего"] += 1
            if m in vhody:
                d["входы"] += 1
        s.append("| кто | мест | входов |")
        s.append("|---|---|---|")
        for kto, d in sorted(po_lyudyam.items()):
            s.append(f"| {kto} | {d['всего']} | {d['входы']} |")
        s.append("")

        # таблица мест
        s.append("## Места")
        s.append("")
        s.append("| # | когда | кто | пара | волна | окно | компас | "
                 "вердикт | кадр |")
        s.append("|---|---|---|---|---|---|---|---|---|")
        for i, m in enumerate(self.mesta, 1):
            s.append(f"| {i} | {m['когда_на_рынке']} | {m['кто']} | "
                     f"{m['инструмент']} {m['этаж']} | "
                     f"{m['длина_волны'] or '—'} | "
                     f"{'✓' if m['в_окне_100_140'] else '·'} | "
                     f"{m['компас'] or '—'} | {m['вердикт']} | "
                     f"{m['кадр'] or '—'} |")
        s.append("")

        # частые причины
        prichiny: dict = {}
        for m in self.mesta:
            p = (m["причина"] or "").strip()
            if p:
                prichiny[p[:90]] = prichiny.get(p[:90], 0) + 1
        if prichiny:
            s.append("## Что говорили чаще всего")
            s.append("")
            for p, skolko in sorted(prichiny.items(), key=lambda x: -x[1])[:10]:
                s.append(f"- **{skolko}×** {p}")
            s.append("")

        s.append("## Словами")
        s.append("")
        for i, m in enumerate(self.mesta, 1):
            if m["сказал"]:
                s.append(f"**{i}. {m['кто']} · {m['когда_на_рынке']} · "
                         f"{m['инструмент']} {m['этаж']}**")
                s.append("")
                s.append(m["сказал"])
                s.append("")
        return "\n".join(s)


# OTCHYOT_PROGONA_V1 - marker

# VOLNA_NA_STOLE_V1 - marker

# NE_TERYAT_RESHENIE_V1 - marker
