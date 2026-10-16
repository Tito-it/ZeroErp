# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le sveglie VERE del dichiarato di deploy (`sveglie.json`) come
#        fixture dei test di «Esegui ora»: si leggono, non si ricopiano, cosi'
#        se il dichiarato cambia cambia anche il caso — che e' il verso giusto.
# Note: ⭐ Estratto il 2026-09-15 alla terza occorrenza (regola del 2): lo
#        stesso selettore stava in tre file di test — predicato/service,
#        handler, API — e tre copie della stessa condizione divergono alla
#        prima che si tocca. ⚠️ La condizione e' scritta PER ESTESO qui
#        (timer, candidato) e non delegata al predicato
#        `motivi_esegui_ora`: il predicato e' cio' che quei test provano, e un
#        fixture scelto dal predicato renderebbe tautologico il caso
#        «senza motivi -> ammesso».
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI
from apps.core.services.sveglie import Sveglia, sveglie_di_processo


# Scopo: la prima sveglia del processo che e' un TIMER, dichiarata candidata a
#        «Esegui ora» — il caso buono. Il digest ne ha due, entrambe cosi'.
#        Che il PROCESSO sia acceso non e' piu' del dichiarato (dal
#        2026-10-16 e' del DB): il test lo passa al predicato come `acceso`. AssertionError se il dichiarato non
#        ne ha nessuna: un test che partisse da un fixture assente passerebbe
#        a vuoto.
def prima_sveglia_candidata(processo_codice: str = PROCESSO_DIGEST_PRESIDI) -> Sveglia:
    for sveglia in sveglie_di_processo(processo_codice):
        if sveglia.e_timer and sveglia.avvio_manuale:
            return sveglia
    raise AssertionError(
        f"nessuna sveglia candidata per {processo_codice} in sveglie.json"
    )
