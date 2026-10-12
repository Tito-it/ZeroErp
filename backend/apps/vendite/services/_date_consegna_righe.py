# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Aggiorna date di consegna»: UNA data scritta su piu' righe di un
#        documento di vendita, in una delle due modalita' — tutte le righe o
#        solo quelle senza data (brief-db-date-consegna-righe-in-blocco, D-2).
#        Condiviso da ordine e preventivo (regola del 2, ok Tid 2026-10-12).
# ------------------------------------------------------------

# ⭐ L'utility NON porta regole sue (brief §2). Quali colonne il documento ha
#    lo dichiara il suo repository (`colonne_date_consegna()`); se la colonna si
#    scrive in questo stato lo dicono i lock del DB, riga per riga, dentro lo
#    stesso UPDATE. Qui si controlla solo la FORMA della richiesta.
# ⛔ Nessun pre-check di stato: il motivo per spegnere l'azione arriva dalle
#    capability (D-3), il rifiuto vero dal lock delle righe (409). Un
#    `richiedi_righe_in_bozza` qui sarebbe sbagliato, non solo ridondante:
#    la data confermata si scrive anche fuori bozza.
# ⚠️ Le righe gia' spedite si SALTANO e si contano (BF-1): non fanno fallire
#    il gesto. Ogni altro rifiuto del DB (stato, approvazione prezzo in
#    attesa sul preventivo, BF-2) lo fa fallire per intero: e' un UPDATE solo.

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.vendite.db._righe_repo_mixin import RigheDocumentoRepositoryMixin

# Le due modalita' (D-2): tutte le righe, o solo quelle senza data.
MODALITA_TUTTE = "TUTTE"
MODALITA_SOLO_VUOTE = "SOLO_VUOTE"
MODALITA_DATE_CONSEGNA: frozenset[str] = frozenset({MODALITA_TUTTE, MODALITA_SOLO_VUOTE})

CHIAVI_DATE_CONSEGNA: frozenset[str] = frozenset({"colonna", "data", "modalita", "anteprima"})


# Scopo: valida la richiesta e scrive (o con `anteprima` conta) la data sulle
#        righe del documento. Il chiamante ha gia' letto la testata («leggi
#        prima la testata»: fuori perimetro e' un 404) e passa il SUO
#        codice di validazione, cosi' l'errore porta il codice del dominio.
# Ritorna: colonna, data, modalita', `aggiornate`, `saltate_spedite`, `anteprima`.
def aggiorna_date_consegna_righe(
    repo: RigheDocumentoRepositoryMixin,
    documento_id: int,
    payload: dict[str, Any],
    *,
    error_code: str,
    function_name: str,
) -> dict[str, Any]:
    validator = PayloadValidator(validation_code=error_code, function_name=function_name)
    validator.validate_allowed_keys(
        payload, allowed=CHIAVI_DATE_CONSEGNA, function_name=function_name,
    )
    # ⚠️ Non `require_enum`: porta il valore in maiuscolo, e qui e' il NOME
    #    di una colonna. La whitelist e' quella del repository.
    colonna = payload.get("colonna")
    ammesse = repo.colonne_date_consegna()
    ErrorManager.require(
        isinstance(colonna, str) and colonna in ammesse,
        code=error_code,
        message=f"Campo 'colonna' deve essere uno tra: {', '.join(ammesse)}.",
        context={"field": "colonna"},
        function_name=function_name,
    )
    assert isinstance(colonna, str)
    data = validator.require_date(payload, "data", function_name=function_name)
    modalita = validator.require_enum(
        payload, "modalita", allowed=sorted(MODALITA_DATE_CONSEGNA),
        function_name=function_name,
    )
    anteprima = validator.optional_bool(
        payload, "anteprima", function_name=function_name,
    ) is True
    esito = repo.scrivi_data_consegna(
        documento_id, colonna, data,
        solo_vuote=modalita == MODALITA_SOLO_VUOTE,
        anteprima=anteprima,
    )
    return {
        "documento_id": documento_id,
        "colonna": colonna,
        "data": data,
        "modalita": modalita,
        "anteprima": anteprima,
        "aggiornate": esito["aggiornate"],
        "saltate_spedite": esito["saltate"],
    }
