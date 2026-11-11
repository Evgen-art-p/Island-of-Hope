# -*- coding: utf-8 -*-
# MESTO_BEZ_IMENI_V1 — прежнее имя модуля, мостик. Весь код — в mesto_urovnya.py.
# Кто ещё зовёт модуль по старому имени, попадает в новый: те же функции,
# те же данные. Новое писать сюда не нужно.
from mesto_urovnya import *   # noqa: F401,F403
import mesto_urovnya as _mu_m
from mesto_urovnya import mesta_urovnya as mesta_dzhema          # noqa: F401
from mesto_urovnya import eto_mesto_urovnya as eto_dzhem         # noqa: F401
from mesto_urovnya import eto_mesto_urovnya_ceha as eto_mesto_dzhema  # noqa: F401
try:
    from mesto_urovnya import UROVEN as DZHEM                    # noqa: F401
except ImportError:
    pass


def __getattr__(imya):
    return getattr(_mu_m, imya)

# MESTA_PO_POMETKE_V1 - marker
# MESTO_DZHEMA_V1 - marker
# SVOY_CEH_U_RABOTY_V1 - marker
# MESTO_BEZ_IMENI_V1 - marker
