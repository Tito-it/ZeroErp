# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Insegnare a drf-spectacular che cos'e' `JwtAuditAuthentication`, cosi'
#        che lo schema OpenAPI dichiari lo schema di sicurezza `bearerAuth`
#        invece di descrivere l'intera API come anonima; e dare nomi distinti
#        a lista e dettaglio (`nomi_lista_dettaglio`, hook di post-processing).
# Note: ⛔ Il file non definisce comportamento: definisce cosa lo schema DICE.
#        E' registrato per IMPORT (vedi `apps/core/apps.py` → `ready()`), che e'
#        il meccanismo di drf-spectacular: una `OpenApiAuthenticationExtension`
#        si registra da sola alla definizione della sottoclasse.
# ------------------------------------------------------------

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension

# Un solo segmento finale che e' un parametro: `{id}/`. E' cio' che separa il
# dettaglio `/x/{id}/` dalla sua lista `/x/`.
_UN_PARAMETRO_FINALE = re.compile(r"\{[^{}/]+\}/?")


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


# Scopo: Hook di post-processing (`SPECTACULAR_SETTINGS["POSTPROCESSING_HOOKS"]`)
#        che dà alla LISTA il suffisso `_list` quando collide col suo dettaglio.
# Note: ⛔ PERCHE' ESISTE. drf-spectacular costruisce l'`operationId` dal
#       percorso SENZA i parametri, e per una `APIView` in GET l'azione e'
#       sempre `retrieve` (riconosce una lista solo da un serializer
#       `many=True`, che le nostre view non dichiarano). Quindi `/x/` e
#       `/x/{id}/` nascono entrambe `x_retrieve`, e la risoluzione di
#       drf-spectacular aggiunge `_2` al secondo in ordine ALFABETICO di
#       percorso: un nome che dice un numero invece di una cosa, e che si
#       sposta se un percorso nuovo si ordina in mezzo. Erano 51 coppie su 54
#       collisioni il 2026-09-26, 13 delle quali fabbricate da factory
#       (`make_note_views`, documenti) dove un `operation_id` a mano per view
#       non ha una sede.
#       ⭐ La regola e' la stessa di drf-spectacular per i ViewSet (`_list` /
#       `_retrieve`), applicata dove drf-spectacular non la sa vedere: SOLO fra
#       operazioni gia' in collisione, SOLO in GET, e SOLO se esiste lo stesso
#       percorso con UN parametro finale in piu'. Un `operationId` dichiarato a
#       mano che collide per altri motivi resta una collisione, e la segnala.
#       ⚠️ Se il nome nuovo esiste gia' o lo vorrebbero due operazioni
#       (`/tables/`, `/tables/{rel}/`, `/tables/{rel}/{id}/`), non si rinomina
#       niente: la collisione resta e la vede il registro
#       `test_schema_openapi_registro.py`. Un nome non si inventa.
def nomi_lista_dettaglio(result: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
    paths = result.get("paths", {})
    per_id: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for percorso, metodi in paths.items():
        for metodo, operazione in metodi.items():
            per_id[operazione["operationId"]].append((percorso, metodo))

    rinomine: dict[tuple[str, str], str] = {}
    for op_id, occorrenze in per_id.items():
        if len(occorrenze) < 2 or not op_id.endswith("_retrieve"):
            continue
        in_get = {percorso for percorso, metodo in occorrenze if metodo == "get"}
        for percorso in in_get:
            if any(
                altro.startswith(percorso) and _UN_PARAMETRO_FINALE.fullmatch(altro[len(percorso):])
                for altro in in_get
            ):
                rinomine[(percorso, "get")] = op_id.removesuffix("_retrieve") + "_list"

    # Un nome nuovo che esiste gia', o che vogliono in due, non si assegna.
    richiesti: dict[str, int] = defaultdict(int)
    for nuovo in rinomine.values():
        richiesti[nuovo] += 1
    for (percorso, metodo), nuovo in rinomine.items():
        if richiesti[nuovo] == 1 and nuovo not in per_id:
            paths[percorso][metodo]["operationId"] = nuovo
    return result
