# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'annullo di un documento con legami, lato backend: la lettura dei
#        legami per la finestra di conferma e la dichiarazione che la conferma
#        porta al verbo. Per bolla, ordine, preventivo, contratto,
#        commessa e offerta.
# ------------------------------------------------------------

# PERCHE' ESISTE (brief-db-annullo-documento-con-legami, D-4 di Tid, 2026-10-11).
# Annullare un documento che ha consumato qualcosa di altri documenti (la merce
# di un ordine o di un reso, le righe di un preventivo, righe di commessa da
# emettere) o che nasce da un'offerta riapre quelle cose, e non in silenzio:
#   1. l'annullo diretto e' RIFIUTATO dal DB con E_DOC_ANNULLO_CON_LEGAMI
#      (`confirm_and_retry`), su ogni strada che cambia lo stato;
#   2. la finestra elenca i legami (`legami_del_documento`, qui);
#   3. la conferma DICHIARA quanti legami ha visto (`legami_confermati`) al verbo
#      del documento (`vendite.fn_annulla_<documento>`), che li ritira e cambia
#      lo stato. Se nel frattempo sono cambiati, il DB chiede di nuovo.
# ⭐ Regola del 2: era nato per la sola bolla (`ddt_service.get_legami`, D-8 di
#    brief-db-ddt-righe-evase-dall-ordine); alla seconda finestra la prima e'
#    diventata questo modulo, e la copia della bolla si e' ritirata.
# ⭐ La commessa e' entrata nella forma con brief-db-annullo-a-valle-riapre-a-
#    monte (D-2 di Tid, 2026-10-12): e' a valle di tutto cio' che la riempie,
#    e annullarla riapre a monte (il documento o il consumo tornano da mandare,
#    il reso da accreditare) o annulla (gli oneri). Stesso lettore, stesso
#    avviso, stessa finestra: un meccanismo solo.
# ⭐ L'offerta e' entrata con brief-modello-documento-vendita §13 (O-4 di Tid,
#    2026-10-26): il suo legame e' la revisione precedente, superata, che torna
#    emessa quando si annulla l'ultima revisione viva (Regola 6: un annullo che
#    riapre altro si conferma). ⚠️ La revisione precedente non e' un nodo del
#    lineage (nessun arco offerta -> offerta): il suo nome resta None, e la
#    finestra mostra il solo tipo, senza link — com'e' scritto qui sotto per
#    ogni legame che il lineage non vede.
# ⛔ La regola non sta qui: che cosa e' un legame, quanti sono, se la conferma
#    corrisponde lo dice il DB (`vendite.fn_documento_legami`, lo stesso lettore
#    di avviso e verbo). Qui si legge e si trasporta.

from typing import Any, Literal

from apps.config.sorgenti import (
    SORGENTE_COMMESSA,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
    SORGENTE_RESO_VENDITA,
)
from apps.core.services.payload_helpers import PayloadValidator

# ⭐ Il documento che si annulla si nomina col codice di `config.sorgenti`
#    (costanti `SORGENTE_*`): dal 2026-10-19 il `p_documento` di
#    `vendite.fn_documento_legami` e' quel vocabolario
#    (brief-db-grammatica-unica-documenti, lotto 2a). Le costanti `DOCUMENTO_*`
#    di prima, coi codici corti `DDT`/`ORDINE`, e la loro traduzione verso il
#    tipo del lineage sono ritirate: il codice e' lo stesso nei due posti.
# ⭐ Quali documenti il lettore conosce resta scritto, come tipo: le costanti
#    `SORGENTE_*` sono `Final`, e mypy rifiuta al chiamante un codice fuori
#    elenco o un codice corto (che il DB rifiuterebbe solo a runtime).
DocumentoLegami = Literal[
    "DDT_VENDITA", "ORDINE_VENDITA", "PREVENTIVO", "CONTRATTO", "COMMESSA",
    "OFFERTA_COMMERCIALE",
]

# ⛔ Lo stato di destinazione dei verbi di annullo NON si scrive qui: fino al
#    2026-10-25 c'erano `STATO_ANNULLATO` / `STATO_ANNULLATA`, letterali con cui
#    i service riconoscevano l'annullo. Quale stato sia l'annullo lo dice il
#    vocabolario (`is_abortito`, uno solo e attivo, Z-3), letto dal BB
#    `core/services/documento_modello.e_stato_di_annullo`
#    (brief-modello-documento-vendita §9.8).

# Le ORIGINI di un legame che sono un documento del lineage: per queste
# l'`origine` del lettore e' anche il tipo del lineage, e serve al gesto «vai al
# documento» (il lettore porta l'id della testata dall'altra parte ma, per
# decisione di Tid, non il nome, che lo da' il lineage). CONTRATTO e DDT sono
# origini dei soli legami della commessa (i documenti che le hanno spinto
# righe).
# ⭐ Dal 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b) l'`origine`
#    E' il codice della sorgente, ancorato a `config.sorgenti.codice_interno`:
#    la traduzione dai codici corti (`ORDINE`, `RESO`, `OFFERTA`, `DDT`) e'
#    ritirata. Resta da dire QUALI origini si aprono.
# ⚠️ Fuori, di proposito: ATTIVITA_CONSUMI (il consumo non e' un nodo del
#    lineage) e ONERE (non e' una sorgente: e' l'assenza di un documento a
#    monte, detta con un nome). Fuori anche ogni sorgente nuova che il lettore
#    imparasse a dare: senza tipo la finestra mostra la sola origine, senza
#    link, finche' qui non si dichiara che e' un documento da aprire.
_ORIGINI_DOCUMENTO: frozenset[str] = frozenset({
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_RESO_VENDITA,
    SORGENTE_PREVENTIVO,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_COMMESSA,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
})

_CAMPO_DICHIARAZIONE = "legami_confermati"


# Scopo: La dichiarazione della conferma, dal corpo della richiesta: quanti
#        legami l'operatore ha visto. Assente al primo tentativo (None). Un
#        valore non intero e' un 400 col campo, non un 500 dal cast del DB.
def legami_confermati(
    valore: Any, *, validation_code: str, function_name: str,
) -> int | None:
    return PayloadValidator(validation_code=validation_code).optional_positive_int(
        {_CAMPO_DICHIARAZIONE: valore}, _CAMPO_DICHIARAZIONE,
        function_name=function_name,
    )


# Scopo: I legami di un documento per la finestra di conferma: le righe del
#        lettore del DB, il loro numero (`legami`: e' cio' che la conferma
#        dichiara, `count(*)` del lettore, non le righe distinte del documento)
#        e, per ogni legame, il tipo e il nome del documento dall'altra parte,
#        dal lineage. Il nome manca (None) se il lineage non lo vede.
# ⛔ Il chiamante deve aver gia' letto la testata del documento col suo
#    lettore: `vendite.fn_documento_legami` e' SECURITY DEFINER e non applica
#    il perimetro. Il lineage lo applica, ma qui serve solo per i nomi.
def legami_del_documento(documento: DocumentoLegami, documento_id: int) -> dict[str, Any]:
    # Import locale: il repository trasversale del dominio, come per
    # `vendite_service` qui sotto.
    from apps.vendite.db.vendite_repository import VenditeRepository

    righe = VenditeRepository().list_documento_legami(documento, documento_id)
    nomi = _nomi_dal_lineage(documento, documento_id) if righe else {}
    for riga in righe:
        tipo = riga["origine"] if riga["origine"] in _ORIGINI_DOCUMENTO else None
        riga["origine_tipo_codice_interno"] = tipo
        riga["origine_codice"] = nomi.get((tipo, riga["origine_id"]))
    return {
        "documento": documento,
        "id": documento_id,
        "legami": len(righe),
        "righe": righe,
    }


# Scopo: (tipo, id) -> codice dei documenti collegati, dai passaggi del lineage
#        nelle due direzioni: le origini stanno «indietro» (ordine, reso,
#        preventivo, offerta; per la commessa anche contratto e bolla), la
#        commessa «avanti».
def _nomi_dal_lineage(documento: str, documento_id: int) -> dict[tuple[str | None, Any], Any]:
    from apps.vendite.services import vendite_service

    passaggi = vendite_service.get_documento_passaggi(documento, documento_id)
    nomi: dict[tuple[str | None, Any], Any] = {}
    for p in passaggi["indietro"]:
        nomi[(p["from_tipo_codice_interno"], p["from_doc_id"])] = p["from_codice"]
    for p in passaggi["avanti"]:
        nomi[(p["to_tipo_codice_interno"], p["to_doc_id"])] = p["to_codice"]
    return nomi
