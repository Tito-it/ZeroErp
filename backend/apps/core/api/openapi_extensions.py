# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Insegnare a drf-spectacular che cos'e' `JwtAuditAuthentication`, cosi'
#        che lo schema OpenAPI dichiari lo schema di sicurezza `bearerAuth`
#        invece di descrivere l'intera API come anonima.
# Note: ⛔ Il file non definisce comportamento: definisce cosa lo schema DICE.
#        E' registrato per IMPORT (vedi `apps/core/apps.py` → `ready()`), che e'
#        il meccanismo di drf-spectacular: una `OpenApiAuthenticationExtension`
#        si registra da sola alla definizione della sottoclasse.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JwtAuditAuthenticationScheme(OpenApiAuthenticationExtension):
    """Dichiara `JwtAuditAuthentication` come Bearer JWT nello schema OpenAPI.

    ⛔ PERCHE' ESISTE, e cosa succedeva senza.
    `apps.core.api.jwt_audit_authentication.JwtAuditAuthentication` e' una
    sottoclasse nostra di `JWTAuthentication`: drf-spectacular riconosce la
    classe di SimpleJWT, non la nostra, e per ogni view che la dichiara emetteva
    l'avviso «could not resolve authenticator ... There was no
    OpenApiAuthenticationExtension registered for that class. Ignoring for now».

    ⇒ Ignorandola, `components.securitySchemes` NON veniva emesso affatto, e con
    esso spariva ogni `security:` dalle operazioni. Uno schema senza schema di
    sicurezza in OpenAPI significa **API anonima**: `/api/docs/` restava senza il
    pulsante *Authorize* (nessuna chiamata autenticata provabile dalla
    documentazione) e qualunque client generato dallo schema partiva senza header
    `Authorization`, prendendo 401 ovunque.

    ⚠️ Misurato il 2026-09-09 su `manage.py check --deploy`: erano **607 avvisi
    `drf_spectacular.W001`** su 673 totali — cioe' un solo pezzo mancante ripetuto
    una volta per view. La CI non li vedeva perche' lancia `manage.py check`
    liscio, e drf-spectacular aggancia i propri controlli al ramo `--deploy`.

    ⭐ La dichiarazione e' onesta rispetto al codice: il ramo di autenticazione
    e' quello di SimpleJWT (header `Authorization: Bearer <access>`); cio' che la
    nostra sottoclasse aggiunge — la propagazione dei GUC di identita' al
    database — non cambia il **protocollo**, quindi non cambia lo schema.
    """

    # Percorso della classe che questa estensione descrive: drf-spectacular la
    # usa come chiave del registro, quindi deve corrispondere esattamente
    # all'import path dichiarato nelle view (`DEFAULT_AUTHENTICATION_CLASSES`).
    target_class = "apps.core.api.jwt_audit_authentication.JwtAuditAuthentication"

    # Nome dello schema di sicurezza in `components.securitySchemes`.
    name = "bearerAuth"

    # Scopo: Restituisce l'oggetto `securityScheme` OpenAPI 3 per il JWT.
    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Access token JWT ottenuto da uno dei tre endpoint di login "
                "per veste (`/api/v1/admin/token/`, `/api/v1/portale/token/`, "
                "`/api/v1/shop/token/`). Va inviato come "
                "`Authorization: Bearer <access>`."
            ),
        }
