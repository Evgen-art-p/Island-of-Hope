# -*- coding: utf-8 -*-
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
      min-width:520px; padding:26px 28px 22px; border-radius:20px;
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
                                 ("ЗАСТРОЙЩИК", "/zastroyshchik"),
                                 ("ПЕРЕВОЗКА", "/perevozka")):
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
