# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler flusso `vendita.post_smistamento` — azione di COMPLETAMENTO,
#        MERCE-ONLY. Dispatchato dal motore pratiche quando SMISTAMENTO passa a
#        COMPLETATO con esito **MERCE_PRESENTE** (binding per-ramo in
#        pratiche.template_flussi_handler_eventi — bivio-per-esito rev.3,
#        brief-db-chiusura-pratica-nessun-lavoro-pendente). Sul ramo SOLO_SERVIZI
#        l'handler NON scatta (per-ramo, non NULL): la commessa-servizi la aggancia
#        il push standalone (`preventivi_service._aggancia_commessa_servizi_a_pratica`).
#
#        Lo smistamento vero e proprio (merce→ordine, servizi→commessa) lo ha fatto
#        l'operatore dal Pannello Smistamento standalone; qui si esegue SOLO il
#        retro-aggancio dell'ordine merce alla pratica come `pratiche_sorgenti`
#        COLLEGATO. **Niente creazione di flussi a valle**: con 9013/9014
#        obbligatori-su-ramo (bivio), CONFERMA_ORDINE/INVIO_COMMESSA compaiono da
#        soli via roadmap/prerequisiti — non li crea un handler (cade il vecchio
#        step 4 / chaining D3).
#
#        Direzione anelli: l'handler vive in `vendite` (conosce ordine/merce) e
#        USA `pratiche` (upsert sorgente); `pratiche` resta generico.
#        Idempotente: aggancio sorgente ON CONFLICT DO NOTHING.
# ------------------------------------------------------------

from typing import Any

from apps.config.sorgenti import SORGENTE_ORDINE_VENDITA, SORGENTE_PREVENTIVO
from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository



class PostSmistamentoHandler:
    """Handler di completamento SMISTAMENTO (ramo MERCE): aggancia l'ordine
    generato dallo smistamento alla pratica come sorgente COLLEGATO."""

    def execute(
        self,
        flusso_id: int,
        pratica_id: int,
        meta: dict[str, Any],
        handler_params: dict[str, Any],
        user: str | None = None,
    ) -> dict[str, Any]:
        # Import locale: il service pratiche e' a valle, lazy per coerenza col
        # pattern handler (vendite→pratiche solo a runtime).
        from apps.pratiche.db.pratiche_repository import PraticheRepository

        prev_repo = PreventiviRepository()
        ord_repo = OrdiniRepository()
        prat_repo = PraticheRepository()

        # 1. Preventivo ROOT della pratica (agganciato a monte da PREVENTIVAZIONE).
        preventivo_id = prev_repo.get_preventivo_id_by_pratica_root(pratica_id)
        ErrorManager.require(
            preventivo_id is not None,
            code="E_VENDITA_PREVENTIVO_NON_COLLEGATO",
            message="Nessun preventivo ROOT collegato alla pratica.",
            detail=f"pratica_id={pratica_id}, flusso_id={flusso_id}",
            function_name="PostSmistamentoHandler.execute",
        )
        assert preventivo_id is not None

        # 2. Ordine generato dallo smistamento merce (documento_origine PREVENTIVO).
        #    L'handler e' bindato su esito MERCE_PRESENTE → un ordine DEVE esistere
        #    (l'esito e' calcolato in completa_smistamento da exists_ordine_da_
        #    preventivo). Ordine assente qui = incoerenza esito/artefatti: fallisce
        #    rumoroso (fail-safe, non silenzioso).
        #    NB 1:N: lo smistamento puo' produrre piu' ordini (consegne parziali);
        #    si aggancia il PRIMO (il caso pratica tipico e' un solo ordine).
        ordine = ord_repo.get_ordine_by_documento_origine(
            SORGENTE_PREVENTIVO, preventivo_id,
        )
        ErrorManager.require(
            ordine is not None,
            code="E_VENDITA_SMISTAMENTO_NON_ESEGUITO",
            message="Esito MERCE_PRESENTE ma nessun ordine risulta generato dal preventivo.",
            detail=f"preventivo_id={preventivo_id}, flusso_id={flusso_id}",
            function_name="PostSmistamentoHandler.execute",
        )
        assert ordine is not None
        ordine_id = int(ordine["id"])

        # 3. Aggancio dell'ordine alla pratica (COLLEGATO, idempotente).
        prat_repo.upsert_pratica_sorgente(
            pratica_id=pratica_id, sorgente_codice=SORGENTE_ORDINE_VENDITA,
            sorgente_uid=str(ordine_id), ruolo_link="COLLEGATO",
        )

        return {"ordine_id": ordine_id}
