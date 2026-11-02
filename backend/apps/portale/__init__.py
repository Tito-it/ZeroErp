# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: App dominio Portale — endpoint e service per gli accessi esterni
#        (clienti + fornitori) al portale self-service. Namespace API:
#        /api/v1/portale/*. Gli endpoint lato admin (invita-portale) restano
#        sotto /api/v1/anagrafiche/clienti|fornitori per coerenza con il
#        CRUD esistente, ma delegano alla service app portale.
# ------------------------------------------------------------
