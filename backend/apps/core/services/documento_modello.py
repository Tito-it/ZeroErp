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
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.db.documento_modello_repository import DocumentoModelloRepository
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
