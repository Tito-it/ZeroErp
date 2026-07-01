# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler flusso `vendita.post_smistamento` — azione di COMPLETAMENTO.
#        Dispatchato dal motore pratiche quando il flusso SMISTAMENTO passa a
#        COMPLETATO con esito POSITIVO (binding in
#        pratiche.template_flussi_handler_eventi). Lo smistamento vero e proprio
#        (merce→ordine, servizi→commessa) lo ha fatto l'operatore dal Pannello
#        Smistamento standalone; qui, SE e' nato un ordine merce, lo si aggancia
#        alla pratica e si creano on-demand i flussi a valle PERCORRIBILI (prereq
#        soddisfatti ora): alla chiusura di SMISTAMENTO e' CONFERMA_ORDINE;
#        INVIO_COMMESSA (prereq CONFERMA_ORDINE POSITIVO) nasce dopo, alla chiusura
#        di CONFERMA_ORDINE — operatore dal percorso, oppure ribindando questo
#        stesso handler su CONFERMA_ORDINE COMPLETATO (catalogo, futuro).
#        Se il preventivo era tutto-servizi (nessun ordine), non crea nulla: la
#        commessa diretta e' gia' nata dal push servizi.
#
#        Direzione anelli: l'handler vive in `vendite` (conosce ordine/merce) e
#        USA `pratiche` (crea_flusso / upsert sorgente); `pratiche` resta generico.
#        Idempotente: aggancio sorgente ON CONFLICT DO NOTHING; i flussi a valle
#        si creano solo se non gia' istanziati (percorso).
# ------------------------------------------------------------

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository

_SORGENTE_PREVENTIVO = "PREVENTIVO"
_SORGENTE_ORDINE = "ORDINE_VENDITA"
# Codici (config catalogo pratiche): risolti per codice sul percorso, mai per id.
_FLUSSI_POST_ORDINE = ("CONFERMA_ORDINE", "INVIO_COMMESSA")


class PostSmistamentoHandler:
    """Handler di completamento SMISTAMENTO: aggancia l'ordine e crea i flussi
    a valle (CONFERMA_ORDINE, INVIO_COMMESSA) se c'e' un ordine merce."""

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
        from apps.pratiche.services import pratiche_service

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
        #    Assente → preventivo tutto-servizi: nessun flusso ordine da creare
        #    (la commessa diretta e' gia' nata dal push servizi).
        #    NB 1:N: lo smistamento puo' produrre piu' ordini (consegne parziali);
        #    qui si aggancia il PRIMO (il caso pratica tipico e' un solo ordine).
        #    I flussi a valle 50/60 sono per-pratica, quindi una sola coppia basta.
        ordine = ord_repo.get_ordine_by_documento_origine(
            _SORGENTE_PREVENTIVO, preventivo_id,
        )
        if ordine is None:
            # Nessun ordine: due casi. (a) preventivo tutto-servizi → ok, la
            # commessa diretta e' gia' nata dal push servizi, niente flussi ordine.
            # (b) c'e' ancora MERCE non smistata → lo smistamento (genera ordine)
            # NON e' stato eseguito: blocca il completamento di SMISTAMENTO, l'
            # operatore deve smistare la merce dal pannello prima di completare.
            ErrorManager.require(
                not prev_repo.preventivo_ha_residuo_ordine(preventivo_id),
                code="E_VENDITA_SMISTAMENTO_NON_ESEGUITO",
                message="Esegui lo smistamento della merce (genera ordine) prima di "
                        "completare lo step SMISTAMENTO.",
                detail=f"preventivo_id={preventivo_id}: residuo merce non smistato",
                function_name="PostSmistamentoHandler.execute",
            )
            return {"ordine_id": None, "flussi_creati": []}

        ordine_id = int(ordine["id"])

        # 3. Aggancio dell'ordine alla pratica (COLLEGATO, idempotente).
        prat_repo.upsert_pratica_sorgente(
            pratica_id=pratica_id, sorgente_codice=_SORGENTE_ORDINE,
            sorgente_uid=str(ordine_id), ruolo_link="COLLEGATO",
        )

        # 4. Crea on-demand i flussi a valle, risolti per CODICE sul percorso
        #    (mai id hardcodati). Si creano SOLO gli step con prerequisiti gia'
        #    soddisfatti ADESSO (`percorribile`): il guard prerequisiti e' BEFORE
        #    INSERT, quindi creare uno step a prerequisito non ancora soddisfatto
        #    fallirebbe. Alla chiusura di SMISTAMENTO e' percorribile solo
        #    CONFERMA_ORDINE (prereq SMISTAMENTO POSITIVO); INVIO_COMMESSA
        #    (prereq CONFERMA_ORDINE POSITIVO) nasce dopo, alla chiusura di
        #    CONFERMA_ORDINE (operatore dal percorso, prereq allora soddisfatto).
        #    Idempotente: salta gli step gia' istanziati.
        percorso = prat_repo.get_percorso_pratica(pratica_id)
        per_codice = {s["template_flusso_codice"]: s for s in percorso}
        flussi_creati: list[int] = []
        for codice in _FLUSSI_POST_ORDINE:
            step = per_codice.get(codice)
            if step is None or step.get("flusso_id") is not None:
                continue  # step assente (difensivo) o gia' istanziato (idempotenza)
            if not step.get("percorribile"):
                continue  # prerequisiti non ancora soddisfatti (guard BEFORE INSERT)
            flussi_creati.append(
                pratiche_service.crea_flusso(
                    pratica_id=pratica_id,
                    template_flusso_id=step["template_flusso_id"],
                ),
            )

        return {"ordine_id": ordine_id, "flussi_creati": flussi_creati}
