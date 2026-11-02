# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: App dominio Shop B2C — MVP in arrivo con PR-C. Namespace API:
#        /api/v1/shop/*. Accesso anonimo per catalogo pubblico + autenticato
#        per ruolo_applicativo=SHOP_CUSTOMER. In PR-B (§8.4.4/§8.4.5) sono
#        registrati solo stub 501 per gli endpoint di attivazione/
#        registrazione, cosi' FE e smoke e2e possono gia' cablare le
#        rotte senza aspettare PR-C.
#
# Django 4+ autodiscover fa picking della ShopConfig via apps.py senza
# `default_app_config` (deprecato).
# ------------------------------------------------------------
