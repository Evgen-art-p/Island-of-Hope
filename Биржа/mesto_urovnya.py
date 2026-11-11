# -*- coding: utf-8 -*-
# MESTO_DZHEMA_V1 (18.10) — места уровня «продвинутый новичок» и номера их семьи.
#
# Раньше семья места была таблицей в hooks.py: позиция 100003, тень
# 1100003, доливки 2200003. Второе место уровня «продвинутый новичок» (второй картридж)
# в эту таблицу не попадало — и у него не стоял бы стоп, не рождалась
# тень, не было доливок.
#
# Теперь: место уровня «продвинутый новичок» — то, у которого в паспорте цеха
# (manifest.json) стоит "уровень": "продвинутый новичок". Номер места — из маски
# жителя (nositel.magic_slota, Закон Пары). Тень и доливка — правилом
# от номера. Для места на A08 числа те же, что были.
#
# Номер, который однажды узнан как место уровня, помнится до конца
# работы программы: если житель переехал, его открытые позиции
# досиживают по своим правилам, а не по чужим.

import json
import time
from collections.abc import Mapping, Set
from pathlib import Path

TEN = 1_000_000          # тень (книга города): номер места + 1 000 000
DOLIVKA = 2_100_000      # доливка: номер места + 2 100 000
POLE = "уровень"
UROVEN = "продвинутый новичок"
UROVNI = (UROVEN, "компетентный трейдер")   # D03_KAK_D02_V2: третий уровень — тоже место уровня
ZAPAS = 100003           # на крайний случай: паспорта не прочлись — как было

_TSEHA = Path(__file__).resolve().parent.parent / "GRONDHEIM_CITY" / "Биржа" / "цеха"
_ZHIVET = 30.0           # сек: как часто перечитывать паспорта и маски
_kesh = {"t": -1e9, "mesta": []}
_videl = set()           # номера, узнанные за время работы (не забываются)


def mesta_urovnya() -> list:
    """[(цех, место), ...] — все места с пометкой «уровень: продвинутый новичок»."""
    out = []
    try:
        for d in sorted(_TSEHA.iterdir()):
            m = d / "manifest.json"
            if not m.is_file():
                continue
            try:
                man = json.loads(m.read_text(encoding="utf-8"))
            except Exception:
                continue
            for s in man.get("слоты") or []:
                if " ".join(str(s.get(POLE) or "").lower().split()) in UROVNI and s.get("слот"):
                    out.append((d.name, str(s["слот"])))
    except Exception as e:
        print(f"[МЕСТО УРОВНЯ] паспорта цехов не прочлись ({e})")
    return out


def eto_mesto_urovnya_ceha(ceh: str, slot: str) -> bool:
    return (str(ceh), str(slot)) in set(mesta_urovnya())


def _obnovit():
    now = time.monotonic()
    if now - _kesh["t"] < _ZHIVET:
        return
    _kesh["t"] = now
    mesta = mesta_urovnya()
    _kesh["mesta"] = mesta
    if not mesta:
        _videl.add(ZAPAS)          # пометок нет нигде — работаем как раньше
        return
    try:
        from nositel import magic_slota
    except Exception as e:
        print(f"[МЕСТО УРОВНЯ] мост к носителю не поднялся ({e})")
        return
    for ceh, slot in mesta:
        try:
            m = magic_slota(ceh, slot)
        except Exception:
            m = None
        if m is not None:
            try:
                _videl.add(int(m))
            except Exception:
                pass


def nomera() -> set:
    _obnovit()
    return set(_videl)


def nomer_teni(m):
    try:
        return int(m) + TEN
    except Exception:
        return ZAPAS + TEN


def nomer_dolivki(m):
    try:
        return int(m) + DOLIVKA
    except Exception:
        return ZAPAS + DOLIVKA


class _Nabor(Set):
    """Живой набор номеров: «x in НАБОР» смотрит в паспорта, а не в таблицу."""

    def __init__(self, fn):
        self._fn = fn

    @classmethod
    def _from_iterable(cls, it):      # «набор | {…}» даёт обычный набор
        return set(it)

    def __contains__(self, x):
        try:
            return int(x) in self._fn()
        except Exception:
            return False

    def __iter__(self):
        return iter(sorted(self._fn()))

    def __len__(self):
        return len(self._fn())

    def __repr__(self):
        return repr(set(self._fn()))


class _Dolivki(Mapping):
    """Номер места → номер его доливок (как прежний словарь {100003: 2200003})."""

    def __getitem__(self, k):
        if int(k) in nomera():
            return nomer_dolivki(k)
        raise KeyError(k)

    def __iter__(self):
        return iter(sorted(nomera()))

    def __len__(self):
        return len(nomera())

    def __repr__(self):
        return repr(dict(self))


NOMERA = _Nabor(nomera)                                    # позиции мест уровня
TENI = _Nabor(lambda: {nomer_teni(m) for m in nomera()})  # тени (книги города)
DOLIVKI = _Dolivki()                                       # место → доливка


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Места уровня «продвинутый новичок»:", mesta_urovnya())
    print("Номера:", sorted(nomera()))
    print("Тени:", sorted(TENI))
    print("Доливки:", dict(DOLIVKI))

# ══ MESTA_PO_POMETKE_V1 — чьё место, в каком цехе, под каким номером ══
# Остальной город (ход месяца, ведение, сверка, руки, отчёт) спрашивает
# отсюда, а не сверяет имя места с «A08» и цех с «торговый_хаос».
_POSTY = _TSEHA.parent.parent / "посты"
_k_sl = {"t": -1e9, "sloty": {}, "mesta": set()}
_k_nom = {}


def _sloty_cehov() -> dict:
    """{цех: {МЕСТО, ...}} по паспортам цехов (кэш на 30 с)."""
    now = time.monotonic()
    if now - _k_sl["t"] < _ZHIVET:
        return _k_sl["sloty"]
    out = {}
    try:
        for d in sorted(_TSEHA.iterdir()):
            m = d / "manifest.json"
            if not m.is_file():
                continue
            try:
                man = json.loads(m.read_text(encoding="utf-8"))
            except Exception:
                continue
            out[d.name] = {str(s.get("слот")).strip().upper()
                           for s in (man.get("слоты") or []) if s.get("слот")}
    except Exception:
        pass
    _k_sl["sloty"] = out
    _k_sl["mesta"] = {(c, str(s).strip().upper()) for c, s in mesta_urovnya()}
    _k_sl["t"] = now
    return out


def ceh_seychas() -> str:
    """Цех, который Совет назвал на этот прогон (hooks.postavit_ceh)."""
    import sys as _s
    h = _s.modules.get("hooks")
    if h is not None and hasattr(h, "ceh_seychas"):   # SVOY_CEH_U_RABOTY_V1
        return str(h.ceh_seychas() or "")
    return str(getattr(h, "_TEKUSHCHIY_CEH", "") or "") if h else ""


def ceh_mesta(slot, ceh=None) -> str:
    """В каком цехе стоит место. Названный цех главнее; потом — цех
    прогона, если место в нём есть; потом — единственный цех с таким
    местом; не нашлось — торговый_хаос (как было)."""
    if ceh:
        return str(ceh)
    s = str(slot or "").strip().upper()
    sl = _sloty_cehov()
    cur = ceh_seychas()
    if cur and s in sl.get(cur, set()):
        return cur
    est = [c for c, mm in sl.items() if s in mm]
    if "торговый_хаос" in est or not est:
        return "торговый_хаос"
    return est[0]


def eto_mesto_urovnya(slot, ceh=None) -> bool:
    """Место уровня «продвинутый новичок»? По пометке в паспорте его цеха."""
    s = str(slot or "").strip().upper()
    _sloty_cehov()
    if not _k_sl["mesta"]:
        return s == "A08"          # паспорта не прочлись — как было
    return (ceh_mesta(s, ceh), s) in _k_sl["mesta"]


def _nomer_iz_posta(ceh, slot):
    s = str(slot or "").strip().upper()
    try:
        for d in sorted(_POSTY.iterdir()):
            p = d / "пост.json"
            if not p.is_file():
                continue
            try:
                post = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if (str(post.get("цех") or "") == str(ceh)
                    and str(post.get("слот") or "").strip().upper() == s
                    and isinstance(post.get("magic"), int)):
                return post["magic"]
    except Exception:
        pass
    return None


def nomer_mesta(slot, ceh=None):
    """Номер счёта места: из маски жителя (Закон Пары), нет жителя — из
    поста, нет поста — старая таблица только для торговый_хаос."""
    c = ceh_mesta(slot, ceh)
    s = str(slot or "").strip().upper()
    now = time.monotonic()
    k = _k_nom.get((c, s))
    if k and now - k[0] < _ZHIVET:
        return k[1]
    m = None
    try:
        from nositel import magic_slota
        m = magic_slota(c, s)
    except Exception:
        m = None
    if m is None:
        m = _nomer_iz_posta(c, s)
    if m is None and c == "торговый_хаос":
        m = {"A06": 100001, "A07": 100002, "A08": 100003}.get(s)
    _k_nom[(c, s)] = (now, m)
    return m


class _Lyuboy:
    """«x == ЛЮБОЙ» — x среди номеров семьи. Для старых сравнений вида
    z.get("magic") == NOMER_MESTA: подставили этот предмет — и сравнение само
    стало смотреть в паспорта, а не в одно число."""

    def __init__(self, fn, imya):
        self._fn, self._imya = fn, imya

    def __eq__(self, x):
        try:
            return int(x) in self._fn()
        except Exception:
            return False

    def __ne__(self, x):
        return not self.__eq__(x)

    __hash__ = object.__hash__

    def __repr__(self):
        return f"<{self._imya}: {sorted(self._fn())}>"


LYUBOY_MESTO = _Lyuboy(nomera, "места уровня")
LYUBAYA_TEN = _Lyuboy(lambda: {nomer_teni(m) for m in nomera()}, "тени")
LYUBAYA_DOLIVKA = _Lyuboy(lambda: {nomer_dolivki(m) for m in nomera()}, "доливки")


# MESTA_PO_POMETKE_V1 - marker

# MESTO_DZHEMA_V1 - marker

# SVOY_CEH_U_RABOTY_V1 - marker


# ══ MESTO_BEZ_IMENI_V1 — как это называлось в старых записях ══
# Новое пишется под нейтральными именами. Записи прошлых сделок и столов
# (до 20.10) хранят поля под прежними именами — город читает и их. Это
# единственное место, где прежние имена остались: чтобы история читалась.
_STARYE_POLYA = {"нога_места": "нога_джема", "доливка_места": "доливка_джема"}


def pole(d, imya):
    """Значение поля места: по новому имени, а нет — по прежнему."""
    d = d or {}
    v = d.get(imya)
    if v is None and imya in _STARYE_POLYA:
        v = d.get(_STARYE_POLYA[imya])
    return v


# MESTO_BEZ_IMENI_V1 - marker


# D03_KAK_D02_V2 - marker
