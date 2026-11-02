# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lookup statici per enum di dominio vendite (Fase 2 refactor frontend
#        vendite). Single source of truth per i set whitelisted gia' usati
#        dai service e dai CHECK constraint DB; espone una rappresentazione
#        UI-friendly (codice + descrizione + ordering) per i wrapper Select
#        del frontend (TipoVariazioneSelect, AmbitoContrattoSelect,
#        ModalitaPricingSelect).
#
#        Pattern modello: catalogo_service.fn_list_uom_rounding_modes
#        (lookup statico dedicato, niente DB, non gestiti dall'admin).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any


# Whitelist enum gia' presenti nei service di dominio (single source of truth):
#   - contratti_service._TIPI_VARIAZIONE  -> qui rinominato per contesto
#   - promo_articoli_service._TIPI_VARIAZIONE  -> stessa enum + PREZZO_FISSO
#   - contratti_service._AMBITI_VALIDI
# I valori sono allineati ai CHECK constraint DB (vendite.contratti,
# vendite.promo_articoli, ecc.). Aggiungerli/cambiarli qui senza propagare
# al DB rompe il salvataggio: i lookup sono solo UI.

# Scopo: tipo_variazione ammesso sulla variazione GLOBALE della testata
#        contratto (contratti.tipo_variazione_globale).
#        Decisione 2026-05-18 (§3-bis-E refactor-contratti-modalita): solo
#        PERCENTUALE. VALORE_FISSO resta ammesso unicamente per OVERRIDE su
#        singola riga (semantica "prezzo fisso sostitutivo per quell'articolo"),
#        mai per la testata.
_TIPI_VARIAZIONE_CONTRATTO: tuple[tuple[str, str, int], ...] = (
    ("PERCENTUALE", "Percentuale (es. -10%)", 1),
)

# Scopo: tipo_variazione ammesso nelle promo articoli. Aggiunge PREZZO_FISSO
#        (prezzo assoluto sostitutivo): unico livello dove e' ammesso.
_TIPI_VARIAZIONE_PROMO: tuple[tuple[str, str, int], ...] = (
    ("PERCENTUALE", "Percentuale (es. -10%)", 1),
    ("VALORE_FISSO", "Valore fisso (es. -2,50 €)", 2),
    ("PREZZO_FISSO", "Prezzo fisso (sostituisce il prezzo)", 3),
)

# Scopo: ambito contratto (contratti.ambito).
_AMBITI_CONTRATTO: tuple[tuple[str, str, int], ...] = (
    ("COMMODITY", "Commodity (utility, materia prima)", 1),
    ("COMMERCIO", "Commercio (beni e servizi)", 2),
)

# Nota (refactor modalita 2026-05-15): la lookup `modalita-pricing-contratto`
# (A/B/C) e' stata rimossa. Nel modello unificato la "modalita" non e' piu'
# una scelta utente ma una forma derivata dai dati di testata
# (`listino_id` valorizzato vs NULL). Nessun endpoint la espone.


def _to_payload(rows: tuple[tuple[str, str, int], ...]) -> list[dict[str, Any]]:
    # Scopo: trasforma tuple (codice, descrizione, ordering) in dict pronti
    #        per success_response, allineato a fn_list_uom_rounding_modes.
    return [
        {"codice": codice, "descrizione": descrizione, "ordering": ordering}
        for codice, descrizione, ordering in rows
    ]


# Scopo: lista tipi_variazione ammessi per contratti.
def fn_list_tipi_variazione_contratto() -> list[dict[str, Any]]:
    return _to_payload(_TIPI_VARIAZIONE_CONTRATTO)


# Scopo: lista tipi_variazione ammessi per promo articoli (include PREZZO_FISSO).
def fn_list_tipi_variazione_promo() -> list[dict[str, Any]]:
    return _to_payload(_TIPI_VARIAZIONE_PROMO)


# Scopo: lista ambiti ammessi per contratti.
def fn_list_ambiti_contratto() -> list[dict[str, Any]]:
    return _to_payload(_AMBITI_CONTRATTO)


# Scopo: i listini che un contratto o un'offerta di questa utility e di questo
#        emittente (`emittente_fiscale_id`) puo' scegliere: la lettura del DB
#        (`vendite.fn_listini_selezionabili`), che usa lo stesso predicato del
#        guard del documento. Forma `{id, codice, descrizione}`. Delega al
#        repository. ⛔ Il filtro «almeno una versione ATTIVA» (§4.4 del
#        2026-05-18) e' ritirato: la regola vera e' «non si attiva/emette senza
#        una versione in vigore», del DB (D.4.3 di
#        brief-db-offerta-emissione-ed-erogazione).
def fn_list_listini_selezionabili(
    utility_id: int | None, emittente_fiscale_id: int | None,
) -> list[dict[str, Any]]:
    from apps.vendite.db.listini_repository import ListiniRepository

    return ListiniRepository().list_lookup_selezionabili(
        utility_id, emittente_fiscale_id,
    )
