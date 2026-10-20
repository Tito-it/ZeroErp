# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL PREZZO DI UNA RIGA DI COMMESSA DAL LISTINO — building block unico
#        (regola del 2, ok Tid 2026-10-08, L0 di piano-be-type-checker §4).
#        Due cose sole, e le stesse per chiunque dia un prezzo a una riga di
#        `vendite.commesse_attivita`:
#          * `argomenti_resolver` — COSA si chiede al resolver per quella riga;
#          * `provenienza_da_resolver` — COSA si scrive sulla riga di cio' che
#            il resolver risponde (la provenienza del prezzo, non il prezzo).
#        Consumatori: il push sorgente → commessa
#        (`BaseSourceHandler._resolve_pricing_audit`) e i tre percorsi di
#        prezzo della riga (`commesse_service.fn_riallinea_prezzo`,
#        `fn_sblocca_prezzo`, `fn_variazione_prezzo_eccezionale`).
#
# ⛔ PERCHE' ESISTE, ed e' il difetto da cui nasce: fino al 2026-10-08 i due
#    percorsi erano scritti due volte e avevano divergito su TRE punti —
#    riallinea e sblocca non passavano il contesto del kit (un componente
#    riprezzato come articolo sciolto), non ripiegavano su `competenza_mese`
#    quando manca `data_attivita`, e scrivevano il solo prezzo lasciando la
#    provenienza del prezzo vecchio. E il push non scriveva la versione di
#    listino, quindi il guard «versione cambiata» di riallinea non scattava
#    mai. Tutto questo dietro un 500 (`test_resolver`, metodo tolto il
#    2026-04-15) che un test mockato fabbricava da solo.
#
# ⚠️ IL PREZZO NON E' QUI: lo decide il chiamante. Il push tiene il prezzo
#    NEGOZIATO alla sorgente (autoritativo) e scrive la provenienza come audit;
#    riallinea e sblocca prendono `prezzo_finale` dal resolver. La provenienza
#    e' la stessa in entrambi i casi: da dove verrebbe, oggi, quel prezzo.
#
# ⭐ `listino_riga_id` E' fra i campi dal 2026-10-09
#    (brief-db-riga-listino-propagata-dalla-commessa): scriverla rende la riga
#    di listino «propagata», cioe' immutabile (`trgfn_listini_righe_guard_stato`).
#    La scrivono i percorsi che prendono DAVVERO il prezzo dal listino
#    (riallinea, sblocca). ⛔ Il push no (decisione B di Tid, 2026-10-09): li'
#    il prezzo e' del documento, e citare la riga che il resolver darebbe la
#    renderebbe «propagata» senza che nessuno ne porti il prezzo — vedi
#    brief-db-provenienza-prezzo-segue-il-prezzo. Nello stadio del kit il
#    resolver non la restituisce e resta NULL: il componente ha un guard suo,
#    piu' severo (D-2 del brief).
# ------------------------------------------------------------
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from apps.vendite.db.commesse_repository import COLONNE_PROVENIENZA_PREZZO
from apps.vendite.services import _kit_meta as kit_meta
# ⛔ L'origine «prezzo scritto a mano» ha una sede sola, il gate prezzi
#    (2026-10-20, regola del 2): qui era la terza copia della stessa stringa,
#    accanto a quelle della PATCH dei componenti e del gate di riga.
from apps.vendite.services._pricing_gate_helpers import ORIGINE_PREZZO_MANUALE

__all__ = [
    "CAMPI_PROVENIENZA",
    "ORIGINE_PREZZO_MANUALE",
    "ORIGINI_PREZZO_AMMESSE",
    "argomenti_resolver",
    "origine_ammessa",
    "provenienza_da_resolver",
    "provenienza_manuale",
]

# Valori ammessi per `commesse_attivita.origine_prezzo` (CHECK
# `chk_commesse_attivita_origine_prezzo`, speculare ad `attivita_fatturabili`).
# Il resolver puo' restituire un'origine fuori da questo set ('LISTINO_BUNDLE'
# nello stadio del kit): li' l'origine resta NULL, che il CHECK ammette, invece
# di far fallire la scrittura. Allineare al DB se il modello aggiunge valori.
ORIGINI_PREZZO_AMMESSE = frozenset(
    {"PROMO", "CONTRATTO_OVERRIDE", "CONTRATTO_LISTINO", "CATEGORIA", ORIGINE_PREZZO_MANUALE}
)

# Le colonne di provenienza di una riga di commessa: la sede e' il repository
# che le scrive (`update_attivita_prezzo`), qui se ne prende il nome.
CAMPI_PROVENIENZA = COLONNE_PROVENIENZA_PREZZO


# Scopo: l'origine se il CHECK la ammette, altrimenti None.
def origine_ammessa(origine: object) -> str | None:
    return origine if isinstance(origine, str) and origine in ORIGINI_PREZZO_AMMESSE else None


# Scopo: gli argomenti di `PricingService.resolve_prezzo` per una riga di
#        commessa, o None se la riga non ha cio' che serve per chiederlo
#        (consumi senza articolo, righe senza unita' di misura, commessa senza
#        utility). Il chiamante decide se None e' un errore (riallinea,
#        sblocca) o un audit che resta vuoto (push).
#        ⭐ La data e' `data_attivita` e, in sua assenza, `competenza_mese`; il
#        contesto del kit e' il padre scritto nel `meta` dall'espansione BoM
#        (`componente_di`), che porta il resolver allo stadio BUNDLE.
def argomenti_resolver(
    *,
    articolo_id: Any,
    uom_id: int | None,
    data_attivita: date | None,
    competenza_mese: date | None,
    billing_account_id: int | None,
    utility_id: int | None,
    emittente_soggetto_ruolo_id: int | None,
    meta: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    data_riferimento = data_attivita or competenza_mese
    if (
        articolo_id is None
        or uom_id is None
        or data_riferimento is None
        or billing_account_id is None
        or utility_id is None
        or emittente_soggetto_ruolo_id is None
    ):
        return None
    return {
        "articolo_id": articolo_id,
        "uom_id": uom_id,
        "data_riferimento": data_riferimento,
        "ba_id": billing_account_id,
        "utility_id": utility_id,
        "emittente_soggetto_ruolo_id": emittente_soggetto_ruolo_id,
        "articolo_padre_contesto": (meta or {}).get(kit_meta.META_KEY_COMPONENTE_DI),
    }


# Scopo: la provenienza del prezzo, cioe' i CAMPI_PROVENIENZA, dalla riga che
#        il resolver restituisce. L'origine passa per `origine_ammessa`.
def provenienza_da_resolver(risultato: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "prezzo_base_snapshot": risultato.get("prezzo_base_snapshot"),
        "origine_prezzo": origine_ammessa(risultato.get("origine")),
        "tipo_variazione_applicata": risultato.get("tipo_variazione_applicata"),
        "valore_variazione_applicata": risultato.get("valore_variazione_applicata"),
        "promo_id": risultato.get("promo_id"),
        "contratto_id": risultato.get("contratto_id"),
        "categoria_cliente_id_snapshot": risultato.get("categoria_cliente_id_snapshot"),
        "classe_utenza_id_snapshot": risultato.get("classe_utenza_id_snapshot"),
        "listino_riga_id": risultato.get("listino_riga_id"),
        "listino_versione_id": risultato.get("listino_versione_id"),
    }


# Scopo: la provenienza di un prezzo scritto A MANO (variazione eccezionale,
#        decisione di Tid 2026-10-08): origine `MANUALE`, e niente della
#        provenienza da listino — un prezzo che il listino non ha dato non ha
#        ne' una base ne' una riga ne' una versione di listino. Lo sblocco la
#        riscrive dal resolver.
def provenienza_manuale() -> dict[str, Any]:
    provenienza: dict[str, Any] = dict.fromkeys(CAMPI_PROVENIENZA)
    provenienza["origine_prezzo"] = ORIGINE_PREZZO_MANUALE
    return provenienza
