# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo schema OpenAPI di UN indirizzo come lo ricevono le madri del DB
#        (`anagrafiche.fn_indirizzo_elemento`: `fn_crea_indirizzo_soggetto`,
#        `fn_crea_indirizzo_ruolo`, le plurali). Sede unica per gli endpoint
#        che creano un indirizzo (regola del 2, 2026-10-19): ognuno ne
#        dichiarava a mano un pezzo diverso, e nessuno la forma estera.
# Note: ⚠️ Una FACTORY, non un dizionario condiviso: un campo DRF si lega al
#       serializer che lo contiene, e la stessa istanza in due serializer e'
#       stato condiviso. Le chiavi ammesse sono quelle di `c_ammesse` nella
#       madre: una chiave estranea la rifiuta il DB (`E_CAMPO_NON_AMMESSO`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework import serializers


def _intero() -> serializers.IntegerField:
    return serializers.IntegerField(required=False)


def _testo() -> serializers.CharField:
    return serializers.CharField(required=False, allow_blank=True)


# Scopo: I campi di un indirizzo per `inline_serializer`: il tipo per codice,
#        poi una delle tre forme (libera, dettaglio gia' risolto, via da
#        risolvere). `extra` aggiunge i campi propri dell'endpoint.
def campi_indirizzo_madre(**extra: serializers.Field) -> dict[str, Any]:
    return {
        "tipo_indirizzo_codice_interno": serializers.CharField(help_text="Codice interno del tipo indirizzo (es. RES, FATT)"),
        # Forma libera: lo stato, poi comune e CAP del catalogo oppure, per uno
        # stato senza catalogo dei comuni, localita' e codice postale.
        "indirizzo_libero": _testo(),
        "stato_id": _intero(),
        "comune_id": _intero(),
        "codice_postale_id": _intero(),
        "administrative_area": _testo(),
        "locality": _testo(),
        "sublocality": _testo(),
        "postal_code": _testo(),
        # Dettaglio gia' risolto.
        "indirizzo_dettaglio_id": _intero(),
        # Via da risolvere: stradario esistente, o una via nuova.
        "stradario_id": _intero(),
        "toponomastica_id": _intero(),
        "descrizione_via": _testo(),
        "civico": _testo(),
        "estensione_civico": _testo(),
        "palazzina": _testo(),
        "scala": _testo(),
        "piano": _testo(),
        "interno": _testo(),
        **extra,
    }
