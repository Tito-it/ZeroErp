# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block stateless per risolvere la valuta_id di default
#        applicando la STESSA catena della fn DB `vendite.fn_get_valuta_id`
#        (single source of truth cross-layer, decisione team DB 2026-05-29):
#
#          1) ba.valuta_id                         (BA presente e valorizzato)
#          2) emittente fiscale del BA → valuta_id (catena fn_get_emittente_fiscale_pk)
#          3) emittente fiscale dell'utente → valuta_id (con fallback gestore globale)
#          4) anagrafiche.gestori.valuta_id        (primo gestore per id)
#          5) {} se nessuna sorgente
#
#        Composizione di BB esistenti + lookup diretto anagrafiche.gestori
#        per il livello 4:
#          - BillingAccountRepository.get_lookup_by_id    (livello 1)
#          - BillingAccountRepository.get_emittente_valuta(livello 2)
#          - ParameterService.get_emittente_fiscale_id_for_user (user → EF)
#          - EmittentiFiscaliRepository.get_emittente     (livello 3)
#          - SELECT primo gestore per id                  (livello 4)
#
#        NOTA: catena BE leggermente più ricca di quella DB (livello 3 = EF
#        utente, assente in `fn_get_valuta_id` che riceve l'emittente come
#        parametro esplicito): il BE form-defaults non ha un emittente del
#        documento perché il documento non esiste ancora, quindi usa l'EF
#        utente come proxy. Allineamento al DB sul livello 4 (gestore)
#        deciso 2026-05-29 dopo handoff team DB su dev/db-tid (vedi brief
#        work-done/brief-db-valuta-offerte-contratti.md).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.anagrafiche.db.emittenti_fiscali_repository import EmittentiFiscaliRepository
from apps.core.services.parameter_service import ParameterService


# Scopo: Risolve la valuta_id di default applicando la catena
#        BA → EF-del-BA → EF-utente → gestore.
#        Ritorna sempre lo stesso shape del payload form-defaults:
#        {valuta_id, valuta_codice, valuta_descrizione} oppure dict vuoto
#        se nessuna sorgente.
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

    # Livello 4: anagrafiche.gestori → valuta_id (primo per id).
    # Stesso pattern di `vendite.fn_get_valuta_id` (SELECT g.valuta_id FROM
    # anagrafiche.gestori g ORDER BY g.id LIMIT 1). Single source of truth
    # cross-layer: la catena BE è allineata alla catena DB. Copre il caso
    # "nessun BA + utente senza EF" che prima lasciava la UI con la valuta
    # vuota (bug 2026-05-29). Niente raise se nessun gestore esiste: lo
    # scenario è un caso lecito (resolver opzionale per form-defaults), il
    # caller decide cosa fare con `{}`.
    return _resolve_da_gestore() or {}


# Scopo: Lookup del primo gestore di `anagrafiche.gestori` (ordine per id)
#        e restituzione del payload `{valuta_id, valuta_codice,
#        valuta_descrizione}` con JOIN su config.valute. Ritorna None se
#        nessun gestore configurato (caso lecito, no raise).
#        Allineato alla query del livello 3 di `vendite.fn_get_valuta_id`.
def _resolve_da_gestore() -> dict[str, Any] | None:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT v.id, v.codice, v.descrizione
              FROM anagrafiche.gestori g
              JOIN config.valute    v ON v.id = g.valuta_id
             ORDER BY g.id
             LIMIT 1
            """,
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "valuta_id": row[0],
        "valuta_codice": row[1],
        "valuta_descrizione": row[2],
    }
