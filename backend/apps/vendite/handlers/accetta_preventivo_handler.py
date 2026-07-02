# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler flusso `vendita.accetta_preventivo` — azione di COMPLETAMENTO.
#        Dispatchato dal motore pratiche quando il flusso APPROVAZIONE_CLIENTE
#        passa a COMPLETATO con esito POSITIVO (binding data-driven in
#        pratiche.template_flussi_handler_eventi). Accetta il preventivo ROOT
#        collegato alla pratica con politica di fatturazione neutra (l'autorita'
#        sulla politica e' l'handler push a CONFERMA, c7-2).
#        Sostituisce il routing M2 hardcoded lato FE (endpoint approvazione-flusso):
#        ora la FE chiama il completamento generico del flusso e il motore esegue
#        questo handler nella STESSA transazione (completamento + accept atomici).
#        Riusa il service di dominio esistente (preventivi_service.cambia_stato),
#        non reimplementa l'accettazione (regola del 2).
# ------------------------------------------------------------

from datetime import date
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.handlers._handler_helpers import parse_competenza_mese


class AccettaPreventivoHandler:
    """Handler di completamento: accetta il preventivo ROOT della pratica."""

    # Scopo: Accetta il preventivo collegato (ROOT) alla pratica.
    # Obiettivo: su COMPLETATO+POSITIVO di APPROVAZIONE_CLIENTE porta il preventivo
    #   ad ACCETTATO con la modalita di fatturazione scelta dall'operatore nel
    #   dialog di accettazione (uniforme al programma standalone): i valori
    #   arrivano in `meta` dal completamento flusso e si persistono SUL PREVENTIVO
    #   (single source of truth), non piu' cablati sul template CONFERMA.
    #   Gira nella transazione del completamento (atomicita'). Fallback retro-compat:
    #   senza `meta` (chiamata legacy) accetta con politica neutra differita/mese corrente.
    def execute(
        self,
        flusso_id: int,
        pratica_id: int,
        meta: dict[str, Any],
        handler_params: dict[str, Any],
        user: str | None = None,
    ) -> dict[str, Any]:
        # Import locale: il service vive nello stesso dominio, lazy per coerenza
        # col resto del pattern handler (nessun import a livello modulo verso il
        # service per evitare cicli).
        from apps.vendite.services import preventivi_service

        meta = meta or {}
        preventivo_id = PreventiviRepository().get_preventivo_id_by_pratica_root(pratica_id)
        ErrorManager.require(
            preventivo_id is not None,
            code="E_VENDITA_PREVENTIVO_NON_COLLEGATO",
            message="Nessun preventivo ROOT collegato alla pratica.",
            detail=f"pratica_id={pratica_id}, flusso_id={flusso_id}",
            function_name="AccettaPreventivoHandler.execute",
        )
        assert preventivo_id is not None

        # Modalita di fatturazione scelta all'accettazione (dialog FE → meta):
        #   - immediata=True  → competenza forzata al primo del mese corrente;
        #   - immediata=False → competenza obbligatoria (parsata dal meta);
        #   - assente (legacy) → neutra differita/mese corrente (retro-compat).
        if "fatturazione_immediata" in meta:
            fatturazione_immediata = bool(meta.get("fatturazione_immediata"))
            if fatturazione_immediata:
                competenza_mese = date.today().replace(day=1)
            else:
                competenza_mese = parse_competenza_mese(meta.get("competenza_mese"))
                ErrorManager.require(
                    competenza_mese is not None,
                    code="E_VENDITA_COMPETENZA_RICHIESTA",
                    message="Competenza di fatturazione richiesta per la modalita differita.",
                    detail=f"competenza_mese={meta.get('competenza_mese')!r}",
                    function_name="AccettaPreventivoHandler.execute",
                )
        else:
            fatturazione_immediata = False
            competenza_mese = date.today().replace(day=1)

        result = preventivi_service.cambia_stato(
            preventivo_id,
            "ACCETTATO",
            fatturazione_immediata=fatturazione_immediata,
            competenza_mese=competenza_mese,
            user=user,
        )
        return {"preventivo_id": preventivo_id, "preventivo": result}
