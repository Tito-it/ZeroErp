# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Modelli managed=False per lo schema pratiche.
#        Usati solo se necessari per admin/serialization.
#        L'accesso DB primario avviene tramite repository (cursor raw).
# ------------------------------------------------------------

from django.db import models


# Add managed = False models only when needed for read/write helpers.
