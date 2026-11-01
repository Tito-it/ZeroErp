# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I PERCORSI TECNICI — sede unica. Sono le rotte fuori dal dominio
#        applicativo: la sonda di vita del processo, la documentazione delle
#        API, i file statici e caricati. Gli strati trasversali che servono il
#        dominio (fuso dell'azienda, giornale delle richieste) li saltano.
#
#          e_percorso_tecnico(path) -> True se la rotta e' tecnica
#
#        ⭐ `/health` e' la sonda di vita del PROCESSO: non deve dipendere dal
#        database. Lo smoke del container in CI gira senza Postgres, e un
#        `/health` che legge il DB e' rosso per un motivo che non e' suo.
#        ⚠️ ESATTI e PREFISSI sono separati: `startswith("/health")` prendeva
#        anche `/healthz` o `/health-qualcosa`, che tecnici non sono.
#        ⚠️ Terzo lettore, fuori di qui: `SECURE_REDIRECT_EXEMPT` in
#        `settings.py` esenta `/health` dal redirect HTTPS nel formato di
#        Django (regex senza `/`), e `settings` non importa dalle app. Se
#        cambia l'elenco, si guarda anche quello.
#        Lettori: `FusoAziendaleMiddleware`, `RequestLogMiddleware` (2026-11-01).
# ------------------------------------------------------------

from __future__ import annotations

PERCORSI_TECNICI_ESATTI: frozenset[str] = frozenset({"/health"})
PERCORSI_TECNICI_PREFISSI: tuple[str, ...] = ("/api/docs/", "/api/schema/", "/static/", "/media/")


# Scopo: Dice se la rotta e' tecnica: uguale a un percorso esatto, o sotto
#        uno dei prefissi.
def e_percorso_tecnico(path: str) -> bool:
    return path in PERCORSI_TECNICI_ESATTI or path.startswith(PERCORSI_TECNICI_PREFISSI)
