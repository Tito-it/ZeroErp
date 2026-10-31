# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Regole del modello del documento (guida
#        `modello-documento-di-vendita.md`) che il backend applica per tutti i
#        documenti, lette dal DB invece che scritte per documento.
# Note: ⭐ Regola del 2 (brief-modello-documento-vendita §8.7 punto 4): il
#       rifiuto dell'emissione dal cambio stato generico era scritto quattro
#       volte con un letterale per documento (`EMESSO` di bolla e preventivo,
#       `ATTIVO` del contratto; l'ordine non lo aveva). Lo stato di emissione
#       lo dice il vocabolario (colonna `emissione`).
#       ⭐ Lo stesso per «Emetti» (B-3/B-4 del §8.11): lo stato che l'emissione
#       scrive si legge dal vocabolario, non da un letterale per documento
#       (`STATO_EMESSO` di bolla e preventivo, `_STATO_CONFERMATO`
#       dell'ordine, `"ATTIVO"` del contratto, `StatoOfferta.EMESSA`).
#       ⭐ E per l'annullo (brief-modello-documento-vendita §9.8): quale stato
#       sia l'annullo lo dice il vocabolario (`is_abortito`), non i letterali
#       `STATO_ANNULLATO` / `STATO_ANNULLATA` di `_annullo_con_legami`.
#       ⭐ E per cessazione e accettazione (brief-modello-documento-vendita
#       §17.6): le colonne `cessazione` e `accettazione` del vocabolario, non
#       `STATO_CESSATO` dei contratti ne' gli `"ACCETTATO"` / `ACCETTATA` di
#       preventivo e offerta.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.db.documento_modello_repository import (
    DocumentoModelloRepository,
    StatoDocumento,
)
from apps.core.services.error_manager import ErrorManager


# Scopo: M-2 — un documento che si stampa si emette solo da «Emetti», che
#        assegna il numero e genera il PDF nella stessa transazione: il cambio
#        stato generico rifiuta lo stato di emissione con un 400 del dominio.
#        Per un documento che non si emette (vocabolario senza la colonna) non
#        rifiuta niente.
# Parametri: testata — la testata nella mappa del modello (`vendite.ddt`);
#            stato_codice — lo stato chiesto; campo — il campo del corpo che lo
#            porta (il `field` del 400); validation_code — il DATO_ERRATO del
#            dominio.
def rifiuta_stato_di_emissione(
    testata: str,
    stato_codice: str,
    *,
    campo: str,
    validation_code: str,
    function_name: str,
) -> None:
    ErrorManager.require(
        not DocumentoModelloRepository().e_stato_di_emissione(testata, stato_codice),
        code=validation_code,
        message=(
            "Questo stato si raggiunge solo dall'emissione del documento, che "
            "assegna il numero e genera il PDF."
        ),
        context={"field": campo},
        function_name=function_name,
    )


# Scopo: Lo stato che «Emetti» scrive, letto dal vocabolario della testata
#        (id e codice: il verbo prende il codice, chi scrive ancora la colonna
#        l'id). Un documento senza stato di emissione che arriva qui e' un
#        errore di cablaggio, non di dati: la factory monta «Emetti» solo dove
#        l'emissione esiste, e il CHECK del vocabolario la vuole attiva.
def stato_di_emissione(testata: str, *, function_name: str) -> StatoDocumento:
    return _stato_del_vocabolario(
        DocumentoModelloRepository().stato_di_emissione(testata),
        testata=testata, ruolo="emissione", function_name=function_name,
    )


# Scopo: Lo stato che l'accettazione scrive, letto dal vocabolario della
#        testata. Gemello di `stato_di_emissione`: un documento senza stato di
#        accettazione che arriva qui e' un errore di cablaggio.
def stato_di_accettazione(testata: str, *, function_name: str) -> StatoDocumento:
    return _stato_del_vocabolario(
        DocumentoModelloRepository().stato_di_accettazione(testata),
        testata=testata, ruolo="accettazione", function_name=function_name,
    )


# Scopo: Lo stato di un ruolo (emissione, accettazione) gia' letto dal
#        vocabolario, o l'errore di cablaggio `E_CONFIG_MANCANTE` se manca: la
#        stessa regola dei due lettori qui sopra, scritta una volta.
def _stato_del_vocabolario(
    stato: StatoDocumento | None, *, testata: str, ruolo: str, function_name: str,
) -> StatoDocumento:
    ErrorManager.require(
        stato is not None,
        code="E_CONFIG_MANCANTE",
        message=f"Il documento non ha uno stato di {ruolo} nel suo vocabolario.",
        detail=f"testata={testata}",
        function_name=function_name,
    )
    assert stato is not None
    return stato


# Scopo: Lo stato (codice) e' l'emissione del documento? Per chi decide su uno
#        stato gia' letto (lo stato corrente), non sullo stato chiesto: per
#        quello c'e' `rifiuta_stato_di_emissione`.
def e_stato_di_emissione(testata: str, stato_codice: str) -> bool:
    return DocumentoModelloRepository().e_stato_di_emissione(testata, stato_codice)


# Scopo: Lo stato chiesto e' l'annullo del documento? Il cambio stato generico
#        lo instrada al verbo d'annullo (i legami da dichiarare). Lo dice il
#        vocabolario (`script.fn_stato_abortito_id`): un documento ha un solo
#        stato d'annullo, e il suo nome (ANNULLATO, ANNULLATA) non e' scritto
#        nel codice.
def e_stato_di_annullo(testata: str, stato_codice: str) -> bool:
    return DocumentoModelloRepository().e_stato_di_annullo(testata, stato_codice)


# Scopo: Lo stato chiesto e' la cessazione del documento (colonna `cessazione`
#        del vocabolario)? Il cambio stato del contratto la instrada al verbo
#        della cessazione, con la sua data.
def e_stato_di_cessazione(testata: str, stato_codice: str) -> bool:
    return DocumentoModelloRepository().e_stato_di_cessazione(testata, stato_codice)


# Scopo: Lo stato e' quello in cui il documento nasce (colonna `iniziale` del
#        vocabolario, la bozza)? Lo leggono le regole che valgono «solo in
#        bozza» (l'eliminazione del preventivo orfano): mai `'DRAFT'` scritto
#        nel service.
def e_stato_iniziale(testata: str, stato_codice: str) -> bool:
    return DocumentoModelloRepository().e_stato_iniziale(testata, stato_codice)


# Scopo: Lo stato e' l'accettazione del documento (colonna `accettazione` del
#        vocabolario)? Lo leggono le regole che valgono «da accettato»
#        (fatturazione, pratica del preventivo).
def e_stato_di_accettazione(testata: str, stato_codice: str) -> bool:
    return DocumentoModelloRepository().e_stato_di_accettazione(testata, stato_codice)
