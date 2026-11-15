# Helper condivisi per repository anagrafiche.

from __future__ import annotations

from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND


# `extract_paginated` e' stato PROMOSSO a BB core (regola del 2, 2026-07-18):
# vive in `apps.core.db._helpers` insieme a `fetch_paged_with_total` (variante
# con fallback pagina-stantia) e `query_paged_view` (variante clamp). I
# repository anagrafiche lo importano direttamente dal core.


def resolve_soggetto_id(cursor, soggetto_ruolo_id: int) -> str:
    """Risolve soggetto_id dal ruolo. Solleva E_ANAG_NOT_FOUND se non trovato.

    Usato da views contatti_ruolo e indirizzi_ruolo per evitare duplicazione.
    """
    cursor.execute(
        "SELECT soggetto_id FROM anagrafiche.soggetti_ruoli WHERE id = %s",
        [soggetto_ruolo_id],
    )
    row = cursor.fetchone()
    ErrorManager.require(
        row is not None, code=E_ANAG_NOT_FOUND,
        message="Ruolo non trovato.",
    )
    assert row is not None
    return str(row[0])


# Scopo: LA RIGA DI UN INDIRIZZO COME LA LEGGONO LE LISTE (regola del 2, ok Tid
#        2026-11-15, R-3 di brief-db-copia-indirizzo-soggetto): le colonne delle
#        viste `anagrafiche.vw_indirizzi_resolved_soggetto` / `_ruolo`, alias `v`,
#        con gli alias che il drawer degli indirizzi legge (`id`,
#        `det_comune_id`, `descrizione_comune`, `stradario_display`). Una forma
#        sola per la lista del soggetto e per i tre livelli della cascata del
#        ruolo: la stessa riga si vede uguale nei due contesti.
#        Prima la lista del soggetto era SQL scritto nel BE su
#        `indirizzi_soggetti` + dettaglio + stradario, e non portava la forma
#        estera (localita', codice postale, regione).
COLONNE_INDIRIZZO_RESOLVED = """v.indirizzo_id AS id,
           v.soggetto_id,
           v.soggetto_ruolo_id,
           v.istanza_utility_id,
           v.tipo_indirizzo_id,
           v.tipo_indirizzo_codice,
           v.tipo_indirizzo_codice_interno,
           v.tipo_indirizzo_descrizione,
           v.is_normalizzato,
           v.indirizzo_dettaglio_id,
           v.indirizzo_display,
           v.indirizzo_libero,
           v.administrative_area,
           v.locality,
           v.sublocality,
           v.postal_code,
           v.comune_id,
           v.comune_id AS det_comune_id,
           v.comune_descrizione,
           v.comune_descrizione AS descrizione_comune,
           v.cap,
           v.provincia_sigla,
           v.stato_id,
           v.stato_descrizione,
           v.stato_iso2,
           v.codice_postale_id,
           v.cap_codice,
           v.stradario_id,
           v.via_norm AS stradario_display,
           v.civico,
           v.estensione_civico,
           v.palazzina,
           v.scala,
           v.piano,
           v.interno"""

# Scopo: Il motivo di riga di «Copia come…», dalla vista di azioni del layer
#        della riga (alias `a`): e' la superficie dell'azione nel registro
#        `config.azioni_riga` (COPIA_INDIRIZZO_SOGGETTO / COPIA_INDIRIZZO_RUOLO).
#        NULL = la copia si puo' proporre. Una riga della cascata del ruolo che
#        viene dal soggetto si copia col verbo del soggetto: il suo motivo e'
#        quello della vista del soggetto.
COLONNE_COPIA = "a.copia_blocco_reason, a.copia_blocco_reason_key"
JOIN_COPIA_RUOLO = (
    "LEFT JOIN anagrafiche.vw_indirizzi_ruolo_azioni a ON a.indirizzo_id = v.indirizzo_id"
)
JOIN_COPIA_SOGGETTO = (
    "LEFT JOIN anagrafiche.vw_indirizzi_soggetti_azioni a ON a.indirizzo_soggetto_id = v.indirizzo_id"
)
