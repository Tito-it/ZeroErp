# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block condiviso per il gate EVASO bi-ramo dei preventivi
#        (D6 brief-preventivi-ordini.md + §5b brief-db-smistamento-preventivi.md).
#        EVASO = "nessun residuo smistabile su NESSUN ramo": merce→ordine
#        (fn_preventivo_ha_residuo_ordine) e servizi→commessa
#        (fn_preventivo_ha_residuo_commessa). Centralizza la logica usata dai
#        TRE percorsi di smistamento (regola del 2 superata, estrazione
#        2026-06-12): push commessa standalone (preventivi_service), genera
#        ordine standalone (ordini_service), orchestratore CONFERMA_VENDITA
#        (push_preventivo_handler). Un percorso di smistamento futuro (es.
#        DDT, import) DEVE passare da qui, non replicare il predicato.
# ------------------------------------------------------------

import logging

from django.db import DatabaseError

_STATO_PREVENTIVO_EVASO = "EVASO"


# Scopo: transita il preventivo ACCETTATO→EVASO se e solo se non resta residuo
#        smistabile su nessun ramo (gate bi-ramo, fn DB simmetriche). Ritorna
#        True se la transizione e' avvenuta, False altrimenti.
#
#        `swallow_db_error` governa la robustezza al deploy parziale:
#        - True (percorsi standalone, post-scrittura gia' committata): se la fn
#          DB rifiuta la transizione (es. seed non atterrato) logga warning e
#          ritorna False — lo smistamento e' gia' avvenuto, lo stato si
#          riallineera' al run successivo. La richiesta utente NON fallisce.
#        - False (orchestratore CONFERMA_VENDITA): l'errore PROPAGA e rollbacka
#          l'intera CONFERMA (transazione unica pratica+smistamento+stato).
#
#        `log_label` identifica il percorso chiamante nel warning (telemetria).
def transiziona_a_evaso_se_smistato(
    prev_repo,
    preventivo_id: int,
    *,
    user: str,
    swallow_db_error: bool,
    log_label: str,
) -> bool:
    if prev_repo.preventivo_ha_residuo_ordine(preventivo_id):
        return False
    if prev_repo.preventivo_ha_residuo_commessa(preventivo_id):
        return False
    try:
        prev_repo.cambia_stato(preventivo_id, _STATO_PREVENTIVO_EVASO, user)
    except DatabaseError as exc:
        if not swallow_db_error:
            raise
        logging.getLogger(__name__).warning(
            "%s.transizione_evaso_skipped preventivo_id=%s reason=%s",
            log_label, preventivo_id, str(exc),
        )
        return False
    return True
