# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block stateless per risolvere la valuta_id di default
#        applicando una catena standard cross-dominio:
#
#          1) ba.valuta_id                         (BA presente e valorizzato)
#          2) emittente fiscale del BA → valuta_id (catena fn_get_emittente_fiscale_pk)
#          3) emittente fiscale dell'utente → valuta_id (con fallback gestore globale)
#          4) {} se nessuna sorgente
#
#        Composizione di BB esistenti (zero SQL nuovo):
#          - BillingAccountRepository.get_lookup_by_id    (livello 1)
#          - BillingAccountRepository.get_emittente_valuta(livello 2)
#          - ParameterService.get_emittente_fiscale_id_for_user (user → EF)
#          - EmittentiFiscaliRepository.get_emittente     (livello 3)
#
#        Single source of truth per i form-defaults vendite/acquisti che
#        devono proporre la valuta coerente con BA quando presente, con
#        fallback all'EF dell'utente loggato (gestore globale per admin
#        globale).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.anagrafiche.db.emittenti_fiscali_repository import EmittentiFiscaliRepository
from apps.core.services.parameter_service import ParameterService


# Scopo: Risolve la valuta_id di default applicando la catena
#        BA → EF-del-BA → EF-utente. Ritorna sempre lo stesso shape
#        del payload form-defaults: {valuta_id, valuta_codice,
#        valuta_descrizione} oppure dict vuoto se nessuna sorgente.
#
# Parametri:
#   billing_account_id: id BA selezionato (None = no BA, salta livelli 1+2)
#   ba_obj            : risultato di BillingAccountRepository.get_lookup_by_id
#                       gia' fetched dal caller (ottimizzazione: evita una
#                       seconda query). Se None e billing_account_id
#                       valorizzato, il resolver fa il lookup.
#   auth_user_id      : id utente loggato (None = no fallback user EF)
def resolve_valuta_default(
    *,
    billing_account_id: int | None = None,
    ba_obj: dict[str, Any] | None = None,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    # Livelli 1 + 2: BA-derived (richiede BA)
    if billing_account_id is not None:
        ba_repo = BillingAccountRepository()
        # Riusiamo il BA gia' fetched dal caller per non duplicare la query.
        if ba_obj is None:
            ba_obj = ba_repo.get_lookup_by_id(billing_account_id)
        # Livello 1: valuta direttamente sul BA.
        if ba_obj and ba_obj.get("valuta_id") is not None:
            return {
                "valuta_id": ba_obj["valuta_id"],
                "valuta_codice": ba_obj.get("valuta_codice"),
                "valuta_descrizione": ba_obj.get("valuta_descrizione"),
            }
        # Livello 2: fallback EF del BA (catena fn_get_emittente_fiscale_pk).
        emittente_ba = ba_repo.get_emittente_valuta(billing_account_id)
        if emittente_ba:
            return emittente_ba

    # Livello 3: EF dell'utente (con fallback gestore globale per admin globale).
    if auth_user_id is not None:
        ef_id = ParameterService().get_emittente_fiscale_id_for_user(auth_user_id)
        if ef_id is not None:
            ef = EmittentiFiscaliRepository().get_emittente(ef_id)
            if ef and ef.get("valuta_id") is not None:
                # get_emittente espone valuta_iso (v.iso_code), il payload
                # form-defaults usa valuta_codice (v.codice). Per le valute
                # standard (EUR, USD, ecc.) i due valori coincidono nel CSV
                # seed: mappiamo iso → codice per coerenza di shape.
                return {
                    "valuta_id": ef["valuta_id"],
                    "valuta_codice": ef.get("valuta_iso"),
                    "valuta_descrizione": ef.get("valuta_descrizione"),
                }

    return {}
