#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PEREVOZKA_ZHITELYA_V1
"""
ПЕРЕВОЗКА ЖИТЕЛЯ — один файл на оба берега.

Запускается двойным щелчком по `ПЕРЕВОЗКА.bat`. Сам понимает, где он:

    НА МАТЕРИКЕ он ОТПРАВИТЕЛЬ. Показывает жителей, ты выбираешь
    номером. Он снимает человека с места (личное при этом уезжает к
    нему домой), пакует дом в архив и кладёт в `_ОТПРАВКА/`.

    НА ОСТРОВЕ он ПОЛУЧАТЕЛЬ. Находит архив рядом, распаковывает
    человека в ковчег и тут же предлагает посадить на свободное место —
    выбрать номером. Всё.

ЧТО ЕДЕТ В АРХИВЕ

    Паспорт с ДНК, маски, метки и маяки, слои (ядро, отклик, чувства,
    архив), опыт — включая дневники, которые уехали с ним при снятии с
    места. То есть человек целиком, со всей кухней из отбытия.

ЧТО НЕ ЕДЕТ

    Прочитанное, чаты, склады и картинки. Это материковая кухня: там
    учат, там и остаётся. На острове человеку это не работает, а весит
    много.

ПОЧЕМУ АРХИВОМ, А НЕ ПО СЕТИ

    Берега — разные машины, и часто разные страны. Архив кладётся,
    переносится как угодно (флешка, облако, RDP) и распаковывается.
    Никаких паролей, портов и «а почему не соединяется».
"""
import argparse
import json
import shutil
import sys
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

# что берём из дома человека — это он сам
VEZYOM = {"passport.json", "_слои_заведены.txt"}
VEZYOM_PAPKI = {"маски", "2_метки", "3_маяки", "core", "resonance",
                "sensory", "archive", "опыт", "метки", "маяки"}
# материковая кухня — остаётся дома
NE_VEZYOM = {"прочитано", "чаты", "академия_чаты", "ректор_чаты", "руда",
             "медиа", "__pycache__"}
TYAZHYOLOE = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp3", ".mp4",
              ".wav", ".zip"}


def skazat(s=""):
    print(s, flush=True)


def cherta():
    skazat("=" * 62)


def eto_ostrov() -> bool:
    return (KOREN / "ostrov_puls.py").is_file() or \
           (KOREN / "OSTROV_NADEZHDY.md").is_file()


def _rabota():
    """Механизм работы — им снимаем и сажаем. Нет его — работаем без."""
    try:
        put = str(KOREN / "ГОРОД")
        if put not in sys.path:
            sys.path.insert(0, put)
        import rabota
        return rabota
    except Exception as e:
        skazat(f"  (механизм работы не поднялся: {e})")
        return None


def _sprosit(vopros: str) -> str:
    try:
        return input(vopros).strip()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════
# ОТПРАВИТЕЛЬ — материк
# ══════════════════════════════════════════════════════════════

def zhiteli() -> list:
    out = []
    if not KOVCHEG.is_dir():
        return out
    for d in sorted(KOVCHEG.iterdir()):
        if not d.is_dir():
            continue
        p = d / "passport.json"
        imya = d.name
        rabota_gde = ""
        if p.is_file():
            try:
                dd = json.loads(p.read_text(encoding="utf-8"))
                imya = dd.get("Official_Name", d.name)
                r = dd.get("Работа") or {}
                rabota_gde = r.get("должность", "") or r.get("где", "")
            except Exception:
                pass
        out.append({"имя": imya, "папка": d, "работа": rabota_gde})
    return out


def _post_zhitelya(R, imya: str):
    """Пост, на котором человек сидит. Нет — None."""
    if R is None:
        return None
    try:
        for m in R.mesta():
            if m.get("кто_сидит") == imya:
                return m["id"]
    except Exception:
        pass
    return None


def upakovat(chelovek: dict, R) -> Path | None:
    imya = chelovek["имя"]
    dom = chelovek["папка"]

    # сперва снимаем с места: личное уедет к нему домой само
    post = _post_zhitelya(R, imya)
    if post:
        ok, msg = R.uvolit(post, pochemu="переезд на остров")
        skazat(f"  снят с места: {msg}" if ok else f"  ! снять не вышло: {msg}")

    OTPRAVKA.mkdir(exist_ok=True)
    arhiv = OTPRAVKA / f"{imya}_{datetime.now():%Y%m%d_%H%M}.zip"
    n = 0
    with zipfile.ZipFile(arhiv, "w", zipfile.ZIP_DEFLATED) as z:
        for p in dom.rglob("*"):
            if not p.is_file():
                continue
            otn = p.relative_to(dom)
            if any(x in NE_VEZYOM for x in otn.parts):
                continue
            if p.suffix.lower() in TYAZHYOLOE:
                continue
            verh = otn.parts[0]
            if len(otn.parts) == 1 and verh not in VEZYOM:
                continue
            if len(otn.parts) > 1 and verh not in VEZYOM_PAPKI:
                continue
            z.write(p, str(Path(imya) / otn))
            n += 1
        z.writestr("_ПЕРЕВОЗКА.json", json.dumps(
            {"имя": imya, "когда": datetime.now().isoformat(timespec="seconds"),
             "откуда": str(KOREN), "файлов": n,
             "_note": "человек целиком: паспорт, маски, метки, слои, опыт. "
                      "Прочитанное и чаты остались на материке."},
            ensure_ascii=False, indent=2))
    skazat(f"  упаковано файлов: {n}")
    return arhiv


def otpravitel() -> int:
    lyudi = zhiteli()
    if not lyudi:
        skazat("  жителей не нашёл — это точно материк?")
        return 1
    R = _rabota()

    skazat("\nКого отправляем на остров?\n")
    for i, ch in enumerate(lyudi, 1):
        gde = ch["работа"] or "— без места —"
        skazat(f"   {i:>2}. {ch['имя']:<16} {gde}")
    skazat("\n   можно несколько через запятую · Enter — отмена")
    otvet = _sprosit("\n> ")
    if not otvet:
        skazat("отменил")
        return 0

    nomera = []
    for kusok in otvet.replace(" ", "").split(","):
        if kusok.isdigit() and 1 <= int(kusok) <= len(lyudi):
            nomera.append(int(kusok))
    if not nomera:
        skazat("не понял, кого — отменил")
        return 0

    skazat("")
    arhivy = []
    for n in nomera:
        ch = lyudi[n - 1]
        skazat(f"— {ch['имя']}")
        a = upakovat(ch, R)
        if a:
            arhivy.append(a)
            skazat(f"  готово: {a.relative_to(KOREN)}")

    cherta()
    skazat(f"Собрано архивов: {len(arhivy)}")
    skazat(f"Лежат в папке {OTPRAVKA.name}")
    skazat("")
    skazat("Дальше: перенеси файл(ы) на остров — флешкой, облаком, как")
    skazat("удобно — и положи прямо в папку острова, рядом с ОСТРОВ.bat.")
    skazat("Там запусти ПЕРЕВОЗКУ ещё раз: она их сама найдёт.")
    return 0


# ══════════════════════════════════════════════════════════════
# ПОЛУЧАТЕЛЬ — остров
# ══════════════════════════════════════════════════════════════

def nayti_arhivy() -> list:
    mesta = [KOREN, PRIBYTIE, OTPRAVKA]
    out = []
    for d in mesta:
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


def raspakovat(arhiv: Path) -> str | None:
    with zipfile.ZipFile(arhiv) as z:
        try:
            karta = json.loads(z.read("_ПЕРЕВОЗКА.json").decode("utf-8"))
        except Exception:
            skazat(f"  x {arhiv.name}: это не архив перевозки")
            return None
        imya = karta.get("имя", "").strip()
        if not imya:
            skazat(f"  x {arhiv.name}: в архиве не сказано, кто едет")
            return None
        KOVCHEG.mkdir(parents=True, exist_ok=True)
        dom = KOVCHEG / imya
        if dom.exists():
            zapas = KOVCHEG / f"{imya}_было_{datetime.now():%Y%m%d_%H%M}"
            dom.replace(zapas)
            skazat(f"  прежний {imya} отложен как {zapas.name}")
        n = 0
        for imya_v_arhive in z.namelist():
            if imya_v_arhive == "_ПЕРЕВОЗКА.json":
                continue
            z.extract(imya_v_arhive, KOVCHEG)
            n += 1
        skazat(f"  {imya}: распаковано файлов {n}")
    return imya


def posadit(R, imya: str):
    if R is None:
        return
    try:
        svobodnye = [m for m in R.mesta()
                     if m.get("есть_пост") and not m.get("кто_сидит")]
    except Exception as e:
        skazat(f"  (мест не вижу: {e})")
        return
    if not svobodnye:
        skazat("  свободных мест нет — посадишь позже на странице работы")
        return
    skazat(f"\n  Куда сажаем {imya}?")
    for i, m in enumerate(svobodnye, 1):
        skazat(f"     {i:>2}. {m['название']:<28} {m.get('цех', '')}")
    skazat("     Enter — не сажать, пусть пока живёт без места")
    otvet = _sprosit("\n  > ")
    if not (otvet.isdigit() and 1 <= int(otvet) <= len(svobodnye)):
        skazat(f"  {imya} поселён, места пока нет")
        return
    m = svobodnye[int(otvet) - 1]
    ok, msg = R.prinyat(m["id"], imya, pochemu="приехал с материка")
    skazat(("  + " if ok else "  ! ") + msg)


def poluchatel() -> int:
    arhivy = nayti_arhivy()
    if not arhivy:
        skazat("  архивов рядом не нашёл.")
        skazat("")
        skazat("  Положи файл вида «Имя_20260810_1130.zip» прямо сюда,")
        skazat("  в папку острова, и запусти меня снова.")
        skazat("  Собирается он на материке — там я работаю отправителем.")
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
    PRIBYTIE.mkdir(exist_ok=True)
    prinyaty = []
    for a in arhivy:
        skazat(f"\n— {a.name}")
        imya = raspakovat(a)
        if not imya:
            continue
        prinyaty.append(imya)
        posadit(R, imya)
        try:
            (PRIBYTIE / "принято").mkdir(parents=True, exist_ok=True)
            a.replace(PRIBYTIE / "принято" / a.name)
        except Exception:
            pass

    cherta()
    skazat(f"Принято людей: {len(prinyaty)} — {', '.join(prinyaty)}"
           if prinyaty else "Никого не принял")
    skazat("Архивы убраны в _ПРИБЫТИЕ/принято — не удалены.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--otpravit", action="store_true",
                    help="силой считать себя материком")
    ap.add_argument("--prinyat", action="store_true",
                    help="силой считать себя островом")
    a = ap.parse_args()

    ostrov = a.prinyat or (eto_ostrov() and not a.otpravit)

    cherta()
    skazat("ПЕРЕВОЗКА ЖИТЕЛЯ · " +
           ("ОСТРОВ, принимаю" if ostrov else "МАТЕРИК, отправляю"))
    cherta()

    if not CITY.is_dir():
        skazat("x не вижу GRONDHEIM_CITY — запускай из корня города")
        return 1

    return poluchatel() if ostrov else otpravitel()


if __name__ == "__main__":
    try:
        kod = main()
    except Exception as e:
        skazat(f"\nx что-то пошло не так: {type(e).__name__}: {e}")
        kod = 1
    if sys.platform == "win32":
        try:
            input("\nEnter — закрыть окно.")
        except Exception:
            pass
    sys.exit(kod)
