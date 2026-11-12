#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PEREVOZKA_ZHITELYA_V3
"""
ПЕРЕВОЗКА ЖИТЕЛЯ · с ключом, в обе стороны. Один файл на оба берега.

Слово Шефа 29.09 и 11.11: житель едет ВЕСЬ — с лицом и со всей памятью,
включая рабочий след; квартира в городе остаётся за ним, он может вернуться;
у жителя один ключ, и прописан он ровно в одном месте; на причале — сверка.

    ОТПРАВИТЬ (любой берег, где житель прописан):
        1. снимается с места (работы);
        2. пакуется ВЕСЬ дом: паспорт, лицо, маски, память, опыт, работа,
           чаты — кроме служебного мусора и видео/звука; фразы печати нет;
        3. у каждого файла — отпечаток;
        4. город переписывает прописку на место прибытия и кладёт в архив
           ПРОПУСК РЕЙСА, заверенный печатью города.
        Дом и жильё здесь ОСТАЮТСЯ: в паспорте отметка «уехал(а) туда-то,
        рейс такой-то». Пока его нет — не будят и не сажают на работу.

    ПРИНЯТЬ (берег прибытия):
        1. сверка отпечатков; 2. сверка печати пропуска и что рейс новый;
        3. житель — на ПРИЧАЛ (ковчег), прописан здесь. Если здесь был его
           прежний дом (возвращение) — прежняя папка откладывается рядом,
           житель возвращается в свою квартиру со всем, что прожил;
        4. дальше — твоими руками, по трём ступеням: ЕСТЬ (причал) →
           ЖИВЁТ (ПРОПИСКА в жильё: жильё квартала + его слова) → РАБОТАЕТ (пост).
        Не сошлось — не принимается, архив уходит в _ПРИБЫТИЕ/отказ.

Архивом, а не по сети: берега — разные машины. Архив переносится как угодно.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

KOREN = Path(__file__).resolve().parent
CITY = KOREN / "GRONDHEIM_CITY"
KOVCHEG = CITY / "жители" / "ковчег"
OTPRAVKA = KOREN / "_ОТПРАВКА"
PRIBYTIE = KOREN / "_ПРИБЫТИЕ"

NE_VEZYOM_PAPKI = {"__pycache__", ".git"}
NE_VEZYOM_RASSH = {".mp3", ".mp4", ".wav", ".mov", ".avi", ".zip", ".pyc", ".tmp"}
SEKRET = "Creator_Seal"          # фраза печати — никогда не едет
KUDA_PO_UMOLCHANIYU = ""            # пусто — с материка на «I1», с острова домой на «T1»


def skazat(s=""):
    print(s, flush=True)


def cherta():
    skazat("=" * 62)


def _sprosit(vopros: str) -> str:
    try:
        return input(vopros).strip()
    except Exception:
        return ""


def _put_goroda():
    for p in (KOREN / "ГОРОД",):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _propiska():
    _put_goroda()
    try:
        import propiska
        return propiska
    except Exception as e:
        skazat(f"  x закона прописки нет ({e}) — сначала propiska_mira.py / переселение")
        return None


def _rabota():
    _put_goroda()
    try:
        import rabota
        return rabota
    except Exception as e:
        skazat(f"  (механизм работы не поднялся: {e})")
        return None


def eto_ostrov() -> bool:
    pr = _propiska()
    if pr is not None:
        try:
            return not pr.eto_materik()
        except Exception:
            pass
    return (KOREN / "ostrov_puls.py").is_file() or (KOREN / "OSTROV_NADEZHDY.md").is_file()


def _otpechatok(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bez_sekreta(otn: Path, data: bytes) -> bytes:
    """Из json-файлов убираем фразу печати, если где-то осталась."""
    if otn.suffix.lower() != ".json" or SEKRET.encode() not in data:
        return data
    try:
        d = json.loads(data.decode("utf-8"))
    except Exception:
        return data

    def chistit(x):
        if isinstance(x, dict):
            x.pop(SEKRET, None)
            for v in x.values():
                chistit(v)
        elif isinstance(x, list):
            for v in x:
                chistit(v)
    chistit(d)
    return json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8")


# ══════════════════════════════════════════════════════════════
# ОТПРАВИТЕЛЬ — материк
# ══════════════════════════════════════════════════════════════

def zhiteli() -> list:
    out = []
    if not KOVCHEG.is_dir():
        return out
    pr = _propiska()
    for d in sorted(KOVCHEG.iterdir()):
        if not d.is_dir():
            continue
        p = d / "passport.json"
        imya, rabota_gde, klyuch = d.name, "", ""
        if p.is_file():
            try:
                dd = json.loads(p.read_text(encoding="utf-8"))
                imya = dd.get("Official_Name", d.name)
                klyuch = str(dd.get("_Creator_Seal_Hash") or "")
                r = dd.get("Работа") or {}
                rabota_gde = r.get("должность", "") or r.get("где", "")
            except Exception:
                pass
        priznan, pochemu = (True, "")
        if pr is not None:
            priznan, pochemu = pr.priznan(dom=d)
        out.append({"имя": imya, "папка": d, "работа": rabota_gde, "ключ": klyuch,
                    "признан": priznan, "почему": pochemu})
    return out


def _post_zhitelya(R, imya: str):
    if R is None:
        return None
    try:
        for m in R.mesta():
            if m.get("кто_сидит") == imya:
                return m["id"]
    except Exception:
        pass
    return None


def _kuda_po_umolchaniyu() -> str:
    pr = _propiska()
    try:
        return "I1" if (pr is None or pr.eto_materik()) else "T1"
    except Exception:
        return "I1"


def upakovat(chelovek: dict, R, kuda: str = KUDA_PO_UMOLCHANIYU):
    kuda = kuda or _kuda_po_umolchaniyu()
    imya, dom = chelovek["имя"], chelovek["папка"]
    pr = _propiska()
    if pr is None:
        return None
    if not chelovek.get("ключ"):
        skazat("  x у жителя нет ключа (печати) — с ключом рождают на Странице Жизни")
        return None
    if not chelovek.get("признан", True):
        skazat(f"  x не отправляю: {chelovek.get('почему')}")
        return None
    if not pr.est_pechat():
        skazat(f"  x нет печати города — впиши {pr.ENV_PECHAT}=… в .env")
        return None

    post = _post_zhitelya(R, imya)
    if post:
        ok, msg = R.uvolit(post, pochemu="переезд на остров")
        skazat(f"  снят с места: {msg}" if ok else f"  ! снять не вышло: {msg}")

    fajly, n_bajt = {}, 0
    OTPRAVKA.mkdir(exist_ok=True)
    arhiv = OTPRAVKA / f"{imya}_{datetime.now():%Y%m%d_%H%M}.zip"
    with zipfile.ZipFile(arhiv, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dom.rglob("*")):
            if not p.is_file():
                continue
            otn = p.relative_to(dom)
            if any(x in NE_VEZYOM_PAPKI for x in otn.parts):
                continue
            if p.suffix.lower() in NE_VEZYOM_RASSH or ".bak" in p.name:
                continue
            data = _bez_sekreta(otn, p.read_bytes())
            imya_v = str(Path(imya) / otn).replace("\\", "/")
            z.writestr(imya_v, data)
            fajly[imya_v] = _otpechatok(data)
            n_bajt += len(data)
        # пропуск — последним: с этой секунды прописка уже на острове
        try:
            propusk = pr.vydat_propusk(chelovek["ключ"], kuda, imya)
        except Exception as e:
            z.close()
            arhiv.unlink(missing_ok=True)
            skazat(f"  x пропуск не выдан: {e} — ничего не отправлено")
            return None
        z.writestr("_ПРОПУСК.json", json.dumps(propusk, ensure_ascii=False, indent=2))
        z.writestr("_ПЕРЕВОЗКА.json", json.dumps({
            "имя": imya, "когда": datetime.now().isoformat(timespec="seconds"),
            "откуда": pr.gorod_id(), "куда": kuda, "рейс": propusk["рейс"],
            "файлов": len(fajly), "отпечатки": fajly,
            "_note": "житель целиком: паспорт, лицо, маски, память, опыт, работа. "
                     "Фразы печати в архиве нет."}, ensure_ascii=False, indent=2))
    # отметка на материковой копии — видно, что житель уехал
    try:
        pp = dom / "passport.json"
        d = json.loads(pp.read_text(encoding="utf-8"))
        d["_уехал"] = {"куда": kuda, "рейс": propusk["рейс"],
                       "когда": datetime.now().isoformat(timespec="seconds"),
                       "_note": "уехал(а); дом и жильё здесь остаются за жителем. Пока "
                                "его нет — не будят и не сажают на работу. Вернётся — "
                                "перевозкой обратно, в эту же квартиру."}
        pp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    skazat(f"  упаковано файлов: {len(fajly)} ({n_bajt / 1024 / 1024:.1f} МБ), "
           f"рейс {propusk['рейс']} → {kuda}")
    return arhiv


def otpravitel(kuda: str = KUDA_PO_UMOLCHANIYU) -> int:
    kuda = kuda or _kuda_po_umolchaniyu()
    lyudi = [ch for ch in zhiteli() if ch["признан"]]
    if not lyudi:
        skazat("  жителей не нашёл — это точно материк?")
        return 1
    R = _rabota()
    skazat(f"\nКого отправляем в «{kuda}»?\n")
    for i, ch in enumerate(lyudi, 1):
        gde = ch["работа"] or "— без места —"
        skazat(f"   {i:>2}. {ch['имя']:<16} {gde}")
    skazat("\n   можно несколько через запятую · Enter — отмена")
    otvet = _sprosit("\n> ")
    if not otvet:
        skazat("отменил")
        return 0
    nomera = [int(k) for k in otvet.replace(" ", "").split(",")
              if k.isdigit() and 1 <= int(k) <= len(lyudi)]
    if not nomera:
        skazat("не понял, кого — отменил")
        return 0
    skazat("")
    arhivy = []
    for n in nomera:
        ch = lyudi[n - 1]
        skazat(f"— {ch['имя']}")
        a = upakovat(ch, R, kuda)
        if a:
            arhivy.append(a)
            skazat(f"  готово: {a.relative_to(KOREN)}")
    cherta()
    skazat(f"Собрано архивов: {len(arhivy)} — в папке {OTPRAVKA.name}")
    skazat(f"Перенеси архив(ы) в «{kuda}» (флешка, облако, RDP) — в корень того города —")
    skazat("и запусти там перевозку: «принять».")
    skazat("Дом и жильё здесь остаются за жителем; пока его нет — на работу его не зовут.")
    return 0


# ══════════════════════════════════════════════════════════════
# ПОЛУЧАТЕЛЬ — остров
# ══════════════════════════════════════════════════════════════

def nayti_arhivy() -> list:
    out = []
    for d in (KOREN, PRIBYTIE):            # своё исходящее (_ОТПРАВКА) не принимаем
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.zip")):
            try:
                with zipfile.ZipFile(p) as z:
                    if "_ПЕРЕВОЗКА.json" in z.namelist():
                        out.append(p)
            except Exception:
                continue
    return out


def _gorod_ostrova():
    """На острове без мир/город.json — заводим «I1»."""
    gf = CITY / "мир" / "город.json"
    if gf.is_file():
        return
    if (KOREN / "Брат" / "ui_registry.py").is_file():
        return                       # это материк — не трогаем
    gf.parent.mkdir(parents=True, exist_ok=True)
    gf.write_text(json.dumps({"id": "I1", "имя": "Остров Надежды", "материк": False},
                             ensure_ascii=False, indent=2), encoding="utf-8")
    skazat("  (мир/город.json не было — этот город записан как «I1», Остров Надежды)")


def raspakovat(arhiv: Path):
    pr = _propiska()
    if pr is None:
        return None
    with zipfile.ZipFile(arhiv) as z:
        imena = z.namelist()
        try:
            karta = json.loads(z.read("_ПЕРЕВОЗКА.json").decode("utf-8"))
        except Exception:
            skazat(f"  x {arhiv.name}: это не архив перевозки")
            return None
        imya = (karta.get("имя") or "").strip()
        if "_ПРОПУСК.json" not in imena or not karta.get("отпечатки"):
            skazat(f"  x {arhiv.name}: архив старой перевозки — без пропуска и отпечатков. "
                   "Не принимаю: отправь жителя заново новой перевозкой.")
            return None
        # 1. отпечатки
        plohie = [i for i, o in karta["отпечатки"].items()
                  if i not in imena or _otpechatok(z.read(i)) != o]
        lishnie = [i for i in imena if i not in karta["отпечатки"]
                   and i not in ("_ПЕРЕВОЗКА.json", "_ПРОПУСК.json")]
        if plohie or lishnie:
            skazat(f"  x {imya}: архив повреждён или подменён (не сошлось: {len(plohie)}, "
                   f"лишних: {len(lishnie)}) — не принимаю")
            return None
        skazat(f"  отпечатки сошлись: {len(karta['отпечатки'])} файлов")
        # 2. распаковать во временное место, проверить пропуск, потом — в ковчег
        propusk = json.loads(z.read("_ПРОПУСК.json").decode("utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            for i in karta["отпечатки"]:
                z.extract(i, tmp)
            ok, pochemu = pr.prinyat_propusk(propusk, dom_imya=imya)
            if not ok:
                skazat(f"  x {imya}: {pochemu}")
                return None
            skazat(f"  пропуск: {pochemu}")
            KOVCHEG.mkdir(parents=True, exist_ok=True)
            dom = KOVCHEG / imya
            if dom.exists():
                zapas = KOVCHEG / f"_{imya}_было_{datetime.now():%Y%m%d_%H%M}"
                dom.replace(zapas)
                skazat(f"  вернулся(ась) домой: прежняя папка отложена как {zapas.name}")
            shutil.move(str(Path(tmp) / imya), str(dom))
        # снять отметку «уехал» — здесь он дома
        try:
            pp = dom / "passport.json"
            d = json.loads(pp.read_text(encoding="utf-8"))
            d.pop("_уехал", None)
            d.pop("Работа", None)
            d["_приехал"] = {"откуда": karta.get("откуда"), "рейс": propusk.get("рейс"),
                             "когда": datetime.now().isoformat(timespec="seconds")}
            pp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        skazat(f"  {imya}: на причале (ковчег), прописан здесь")
    return imya


def posadit(R, imya: str):
    if R is None:
        return
    try:
        svobodnye = [m for m in R.mesta() if m.get("есть_пост") and not m.get("кто_сидит")]
    except Exception as e:
        skazat(f"  (мест не вижу: {e})")
        return
    if not svobodnye:
        skazat("  свободных мест нет — посадишь позже на странице работы")
        return
    skazat(f"\n  Куда сажаем {imya}?")
    for i, m in enumerate(svobodnye, 1):
        skazat(f"     {i:>2}. {m['название']:<34} {m.get('цех', '')}")
    skazat("     Enter — не сажать, пусть пока живёт без места")
    otvet = _sprosit("\n  > ")
    if not (otvet.isdigit() and 1 <= int(otvet) <= len(svobodnye)):
        skazat(f"  {imya} поселён, места пока нет")
        return
    m = svobodnye[int(otvet) - 1]
    ok, msg = R.prinyat(m["id"], imya, pochemu="приехал с материка")
    skazat(("  + " if ok else "  ! ") + msg)


def poluchatel() -> int:
    _gorod_ostrova()
    arhivy = nayti_arhivy()
    if not arhivy:
        skazat("  архивов рядом не нашёл. Положи «Имя_ГГГГММДД_ЧЧММ.zip» в корень острова")
        skazat("  и запусти меня снова.")
        return 0
    skazat("\nНашёл архивы:\n")
    for i, a in enumerate(arhivy, 1):
        skazat(f"   {i:>2}. {a.name}")
    skazat("\n   Enter — принять все · номера через запятую — выборочно")
    otvet = _sprosit("\n> ")
    if otvet:
        nomera = [int(x) for x in otvet.replace(" ", "").split(",")
                  if x.isdigit() and 1 <= int(x) <= len(arhivy)]
        arhivy = [arhivy[n - 1] for n in nomera] or arhivy
    R = _rabota()
    prinyaty = []
    for a in arhivy:
        skazat(f"\n— {a.name}")
        imya = raspakovat(a)
        kuda = PRIBYTIE / ("принято" if imya else "отказ")
        kuda.mkdir(parents=True, exist_ok=True)
        try:
            a.replace(kuda / a.name)
        except Exception:
            pass
        if not imya:
            continue
        prinyaty.append(imya)
    cherta()
    skazat(f"Принято: {len(prinyaty)} — {', '.join(prinyaty)}" if prinyaty else "Никого не принял")
    skazat("Архивы — в _ПРИБЫТИЕ/принято и _ПРИБЫТИЕ/отказ, не удалены.")
    if prinyaty:
        skazat("\nДальше — твоими руками, по трём ступеням:")
        skazat("  ЕСТЬ      — житель на причале (сейчас);")
        skazat("  ЖИВЁТ     — ПРОПИСКА в жильё (жильё квартала + его слова из разговора);")
        skazat("  РАБОТАЕТ  — посадка на пост на странице РАБОТА.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--otpravit", action="store_true", help="сразу отправлять")
    ap.add_argument("--prinyat", action="store_true", help="сразу принимать")
    ap.add_argument("--kuda", default=KUDA_PO_UMOLCHANIYU, help="куда отправлять")
    a = ap.parse_args()
    cherta()
    skazat("ПЕРЕВОЗКА ЖИТЕЛЯ · с ключом · в обе стороны")
    cherta()
    if not CITY.is_dir():
        skazat("x не вижу GRONDHEIM_CITY — запускай из корня города")
        return 1
    if eto_ostrov():
        _gorod_ostrova()
    pr = _propiska()
    if pr is not None:
        skazat(f"этот город: «{pr.gorod_id()}»" + (" (материк)" if pr.eto_materik() else ""))
    if a.otpravit:
        return otpravitel(a.kuda)
    if a.prinyat:
        return poluchatel()
    n = len(nayti_arhivy())
    skazat("\n   1. Отправить жителя")
    skazat(f"   2. Принять прибывших" + (f" — рядом архивов: {n}" if n else " — архивов рядом нет"))
    o = _sprosit("\n> ")
    if o == "1":
        return otpravitel(a.kuda)
    if o == "2":
        return poluchatel()
    skazat("отменил")
    return 0


if __name__ == "__main__":
    try:
        kod = main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        skazat(f"\nx что-то пошло не так: {type(e).__name__}: {e}")
        kod = 1
    if sys.platform == "win32":
        try:
            input("\nEnter — закрыть окно.")
        except Exception:
            pass
    sys.exit(kod)

# PEREVOZKA_ZHITELYA_V3 - marker
