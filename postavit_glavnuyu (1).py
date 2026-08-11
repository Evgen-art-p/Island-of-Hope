#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# GLAVNAYA_OSTROVA_V1
"""
ГЛАВНАЯ ОСТРОВА — фон, стеклянная плашка, две двери.

    python postavit_glavnuyu.py          посмотреть
    python postavit_glavnuyu.py --sdelat поставить

Запускать ИЗ КОРНЯ ОСТРОВА.

ЧТО СТАВИТ

    · `ui_ostrov.py` — сама страница;
    · папку `фон/` — сюда кладёшь свою картинку. Любую: jpg, png,
      webp. Берётся первая попавшаяся; хочешь другую — просто убери
      прежнюю. Пусто — будет тёмное небо, страница не сломается;
    · правит `ostrov_main.py`: корень «/» теперь открывает главную,
      а не кидает сразу в кабинет.

КАК ВЫГЛЯДИТ

    Во весь экран фон. Поверх — плашка из матового стекла: имя острова,
    строка состояния и три двери — МАЯК, РАБОТА, ЗАСТРОЙЩИК.

    Плашку можно взять мышью и перетащить куда удобно. Где оставил,
    там она и будет в следующий раз: положение запоминается в браузере.
    Сбить обратно на середину — двойной щелчок по плашке.
"""
import argparse
import ast
import py_compile
import shutil
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

KOREN = Path(__file__).resolve().parent
MAIN = KOREN / "ostrov_main.py"
STRANICA = KOREN / "ui_ostrov.py"
FON = KOREN / "фон"
BAK = ".bak_glavnaya"


UI_OSTROV = '''# -*- coding: utf-8 -*-
# GLAVNAYA_OSTROVA_V2
"""
ГЛАВНАЯ ОСТРОВА — то, что видишь, когда заходишь.

Фон во весь экран, поверх — плашка матового стекла с тремя дверями:
Маяк, Работа и Застройщик. Плашку можно таскать мышью; где оставил, там и будет
в следующий раз.

ПОЧЕМУ ВТОРАЯ ВЕРСИЯ

    Первая рисовала плашку наклейкой поверх страницы, чужой разметкой.
    NiceGUI монтирует своё дерево после и накрывает всё своим слоем —
    плашку было видно, а мышь до неё не доходила: ни потащить, ни
    нажать. Слои и z-index спор не решили.

    Теперь плашка — обычный элемент САМОЙ страницы, а кнопки — обычные
    кнопки NiceGUI. Спорить не с кем: события приходят туда, куда и
    должны.
"""
from pathlib import Path

from nicegui import app, ui

KOREN = Path(__file__).resolve().parent
FON = KOREN / "фон"
KARTINKI = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")

_podklyucheno = False


def _fon_url():
    """Первая картинка из папки фон. Пусто — None, и это не беда."""
    global _podklyucheno
    if not FON.is_dir():
        return None
    faily = sorted(p for p in FON.iterdir()
                   if p.is_file() and p.suffix.lower() in KARTINKI)
    if not faily:
        return None
    if not _podklyucheno:
        try:
            app.add_static_files("/фон", str(FON))
            _podklyucheno = True
        except Exception:
            pass
    return f"/фон/{faily[0].name}"


def page_ostrov():
    fon = _fon_url()
    nebo = (f"background:#05080d url('{fon}') center/cover no-repeat fixed;"
            if fon else
            "background:radial-gradient(120% 90% at 50% 10%,"
            "#12202e 0%,#070b11 60%,#04060a 100%);")

    ui.add_head_html(f"""
<style>
  html, body {{ margin:0; padding:0; height:100%;
                font-family:'Inter',system-ui,sans-serif; }}
  body {{ {nebo} }}
  /* вуаль: картинка не должна спорить с текстом */
  body::before {{ content:''; position:fixed; inset:0; pointer-events:none;
      background:linear-gradient(180deg,rgba(4,6,10,0.35),rgba(4,6,10,0.68)); }}
  .nicegui-content {{ padding:0 !important; }}
  .plashka {{
      position:fixed; left:50%; top:50%; transform:translate(-50%,-50%);
      min-width:430px; padding:26px 28px 22px; border-radius:20px;
      background:rgba(255,255,255,0.07);
      border:1px solid rgba(255,255,255,0.18);
      box-shadow:0 18px 60px rgba(0,0,0,0.55);
      backdrop-filter:blur(16px) saturate(140%);
      -webkit-backdrop-filter:blur(16px) saturate(140%);
      color:#e9f1f8; cursor:grab; user-select:none; }}
  .plashka.tashchim {{ cursor:grabbing;
      box-shadow:0 26px 80px rgba(0,0,0,0.72); }}
</style>
""")

    # плашка — обычный элемент страницы, а не наклейка поверх неё
    # класс, а не атрибут: NiceGUI строит дерево на клиенте,
    # и класс доезжает до DOM надёжнее всего
    with ui.element("div").classes("plashka"):
        ui.label("ОСТРОВ НАДЕЖДЫ").style(
            "font-size:1.15rem; font-weight:800; letter-spacing:0.22em;")
        ui.label("рабочий берег · вахта идёт, пока открыт кабинет").style(
            "font-size:0.72rem; letter-spacing:0.10em; "
            "color:rgba(233,241,248,0.5); margin:6px 0 20px;")
        with ui.row().style("gap:10px; width:100%; flex-wrap:nowrap;"):
            for nadpis, kuda in (("МАЯК", "/mayak"), ("РАБОТА", "/rabota"),
                                 ("ЗАСТРОЙЩИК", "/zastroyshchik")):
                ui.button(nadpis,
                          on_click=lambda k=kuda: ui.navigate.to(k)).props(
                    "flat no-caps").style(
                    "flex:1; padding:11px 12px; border-radius:11px; "
                    "font-size:0.74rem; font-weight:700; white-space:nowrap; "
                    "letter-spacing:0.06em; color:#eaf6ff; "
                    "background:linear-gradient(135deg,"
                    "rgba(120,190,230,0.26),rgba(120,190,230,0.12)); "
                    "border:1px solid rgba(140,200,240,0.42);")

    # таскаем за плашку, но не за кнопки
    ui.add_body_html("""
<script>
(function () {
  const KL = 'ostrov_plashka';
  function zavesti() {
    const p = document.querySelector('.plashka');
    if (!p) { setTimeout(zavesti, 200); return; }
    if (p.dataset.tashchit) return;
    p.dataset.tashchit = '1';

    try {
      const s = JSON.parse(localStorage.getItem(KL) || 'null');
      if (s && typeof s.x === 'number') {
        p.style.left = s.x + 'px'; p.style.top = s.y + 'px';
        p.style.transform = 'none';
      }
    } catch (e) {}

    let tashchim = false, dx = 0, dy = 0;

    p.addEventListener('mousedown', function (e) {
      if (e.target.closest('button')) return;   // по двери — не таскаем
      const r = p.getBoundingClientRect();
      dx = e.clientX - r.left; dy = e.clientY - r.top;
      tashchim = true; p.classList.add('tashchim');
      p.style.transform = 'none';
      p.style.left = r.left + 'px'; p.style.top = r.top + 'px';
      e.preventDefault();
    });

    document.addEventListener('mousemove', function (e) {
      if (!tashchim) return;
      const r = p.getBoundingClientRect();
      let x = e.clientX - dx, y = e.clientY - dy;
      x = Math.max(8, Math.min(x, window.innerWidth - r.width - 8));
      y = Math.max(8, Math.min(y, window.innerHeight - r.height - 8));
      p.style.left = x + 'px'; p.style.top = y + 'px';
    });

    document.addEventListener('mouseup', function () {
      if (!tashchim) return;
      tashchim = false; p.classList.remove('tashchim');
      try {
        localStorage.setItem(KL, JSON.stringify(
          {x: parseInt(p.style.left), y: parseInt(p.style.top)}));
      } catch (e) {}
    });

    p.addEventListener('dblclick', function (e) {
      if (e.target.closest('button')) return;
      p.style.left = '50%'; p.style.top = '50%';
      p.style.transform = 'translate(-50%,-50%)';
      try { localStorage.removeItem(KL); } catch (e) {}
    });
  }
  zavesti();
})();
</script>
""")
'''

FON_README = """Сюда кладёшь фоновую картинку острова.

Любую: jpg, png, webp. Берётся первая по алфавиту — хочешь другую,
просто убери прежнюю или назови новую так, чтобы шла раньше.

Пусто — главная поднимется с тёмным небом, ничего не сломается.
"""

STAROE_MAIN = '''@ui.page("/")
def _dom():
    ui.navigate.to("/torg")
'''
NOVOE_MAIN = '''from ui_ostrov import page_ostrov   # noqa: E402  GLAVNAYA_OSTROVA_V1


@ui.page("/")
def _dom():
    page_ostrov()
'''


def proverit_python(tekst: str, imya: str) -> bool:
    try:
        ast.parse(tekst)
    except SyntaxError as e:
        print(f"  x {imya}: синтаксис сломан ({e}) — НЕ пишу")
        return False
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(tekst)
        vrem = f.name
    try:
        py_compile.compile(vrem, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"  x {imya}: не компилируется ({e}) — НЕ пишу")
        return False
    finally:
        Path(vrem).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdelat", action="store_true")
    a = ap.parse_args()

    print("=" * 58)
    print("ГЛАВНАЯ ОСТРОВА" + ("" if a.sdelat else "   [СУХОЙ ПРОГОН]"))
    print("=" * 58)

    if not MAIN.exists():
        print("x не вижу ostrov_main.py — запускай из корня ОСТРОВА")
        print("  (его кладёт переселенец)")
        return 1

    if not proverit_python(UI_OSTROV, "ui_ostrov.py"):
        return 1

    tekst = MAIN.read_text(encoding="utf-8")
    uzhe = "page_ostrov" in tekst
    if uzhe:
        print("  ostrov_main.py: главная уже подключена")
    elif tekst.count(STAROE_MAIN) != 1:
        print("  x ostrov_main.py: не нашёл, где корень «/» — не трогаю")
        return 1

    print(f"  ui_ostrov.py: {'обновится' if STRANICA.exists() else 'ляжет'}")
    print(f"  фон/: {'есть' if FON.is_dir() else 'заведу'}")
    if FON.is_dir():
        est = [p.name for p in FON.iterdir()
               if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
        print(f"     картинок внутри: {len(est)}"
              + (f" — возьму «{sorted(est)[0]}»" if est else " — будет тёмное небо"))

    if not a.sdelat:
        print("\nЭто был показ. Ставить: python postavit_glavnuyu.py --sdelat")
        return 0

    STRANICA.write_text(UI_OSTROV, encoding="utf-8")
    FON.mkdir(exist_ok=True)
    (FON / "СЮДА_КАРТИНКУ.txt").write_text(FON_README, encoding="utf-8")

    if not uzhe:
        shutil.copy2(MAIN, MAIN.with_suffix(MAIN.suffix + BAK))
        novy = tekst.replace(STAROE_MAIN, NOVOE_MAIN, 1)
        if not proverit_python(novy, "ostrov_main.py"):
            return 1
        MAIN.write_text(novy, encoding="utf-8")

    print("\n+ готово")
    print("  1. кинь картинку в папку фон/")
    print("  2. python ostrov_main.py")
    print("  3. открой http://localhost:8080/ — это главная")
    print("\nПлашку таскай мышью, двойной щелчок вернёт её на середину.")
    return 0


if __name__ == "__main__":
    _kod = main()
    if sys.platform == "win32" and len(sys.argv) == 1:
        try:
            input("\nготово. Enter — закрыть окно.")
        except Exception:
            pass
    sys.exit(_kod)
