# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'annullo di un documento con legami, lato backend: la lettura dei
#        legami per la finestra di conferma e la dichiarazione che la conferma
#        porta al verbo. Per bolla, ordine, preventivo e contratto.
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
# ⛔ La regola non sta qui: che cosa e' un legame, quanti sono, se la conferma
#    corrisponde lo dice il DB (`vendite.fn_documento_legami`, lo stesso lettore
#    di avviso e verbo). Qui si legge e si trasporta.

from typing import Any

from apps.core.services.payload_helpers import PayloadValidator

# I documenti che il lettore dei legami e i verbi di annullo conoscono (i codici
# del DB, `p_documento` di `vendite.fn_documento_legami`).
DOCUMENTO_DDT = "DDT"
DOCUMENTO_ORDINE = "ORDINE"
DOCUMENTO_PREVENTIVO = "PREVENTIVO"
DOCUMENTO_CONTRATTO = "CONTRATTO"

# Lo stato di destinazione dei quattro verbi di annullo. ⚠️ L'avviso del DB
# scatta entrando in uno stato ABORTITO del vocabolario (`is_abortito`), e oggi
# in tutti e quattro i documenti l'unico e' ANNULLATO, che e' anche dove portano
# i verbi. Uno stato abortito nuovo vorrebbe il suo verbo, a DB.
STATO_ANNULLATO = "ANNULLATO"

# Il tipo del lineage (`config.sorgenti.codice_interno`) del documento che si
# annulla: e' la chiave per leggere il nome dei documenti collegati.
_TIPO_LINEAGE_DEL_DOCUMENTO: dict[str, str] = {
    DOCUMENTO_DDT: "DDT_VENDITA",
    DOCUMENTO_ORDINE: "ORDINE_VENDITA",
    DOCUMENTO_PREVENTIVO: "PREVENTIVO",
    DOCUMENTO_CONTRATTO: "CONTRATTO",
}
# Il tipo del lineage dell'ORIGINE di un legame (`origine` del lettore). Serve
# al gesto «vai al documento»: il lettore porta l'id della testata dall'altra
# parte ma, per decisione di Tid, non il nome, che lo da' il lineage.
_TIPO_LINEAGE_DELL_ORIGINE: dict[str, str] = {
    "ORDINE": "ORDINE_VENDITA",
    "RESO": "RESO_VENDITA",
    "PREVENTIVO": "PREVENTIVO",
    "OFFERTA": "OFFERTA_COMMERCIALE",
    "COMMESSA": "COMMESSA",
}

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
def legami_del_documento(documento: str, documento_id: int) -> dict[str, Any]:
    # Import locale: il repository trasversale del dominio, come per
    # `vendite_service` qui sotto.
    from apps.vendite.db.vendite_repository import VenditeRepository

    righe = VenditeRepository().list_documento_legami(documento, documento_id)
    nomi = _nomi_dal_lineage(documento, documento_id) if righe else {}
    for riga in righe:
        tipo = _TIPO_LINEAGE_DELL_ORIGINE.get(riga["origine"])
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
#        preventivo, offerta), la commessa «avanti».
def _nomi_dal_lineage(documento: str, documento_id: int) -> dict[tuple[str | None, Any], Any]:
    from apps.vendite.services import vendite_service

    passaggi = vendite_service.get_documento_passaggi(
        _TIPO_LINEAGE_DEL_DOCUMENTO[documento], documento_id,
    )
    nomi: dict[tuple[str | None, Any], Any] = {}
    for p in passaggi["indietro"]:
        nomi[(p["from_tipo_codice_interno"], p["from_doc_id"])] = p["from_codice"]
    for p in passaggi["avanti"]:
        nomi[(p["to_tipo_codice_interno"], p["to_doc_id"])] = p["to_codice"]
    return nomi
