# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler flusso `vendita.push_preventivo` — al passaggio del flusso
#        CONFERMA in IN_CORSO spinge il preventivo ACCETTATO in commessa diretta
#        applicando la politica di fatturazione (IMMEDIATA/DIFFERITA) presa dai
#        handler_params del template, e porta la commessa a PRONTA_FATTURAZIONE.
#        Primo handler reale del motore pratiche.
#
#        Brief: docs/it/dev/work-in-progress/brief-be-pratica-preventivi.md
#        - delega il push all'orchestratore esistente (pr_run_commesse_push_one),
#          NON reimplementa (regola del 2);
#        - tutto il corpo in una sola transazione atomica (§8.1);
#        - idempotente: una commessa gia' agganciata → E_VENDITA_PREVENTIVO_GIA_PUSHATO (§8.2);
#        - policy applicata via UPDATE del preventivo pre-push (c7-2, §8.6);
#        - destinazione FISSA = commessa diretta (no split natura in v1, §9).
# ------------------------------------------------------------

from datetime import date
from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository

_FN = "apps.vendite.handlers.push_preventivo_handler"

# Vocabolario politica fatturazione (validato in codice; nessuna tabella
# config.modalita_fatturazione — decisione modeling). Valore in handler_params.
MODALITA_IMMEDIATA = "IMMEDIATA"
MODALITA_DIFFERITA = "DIFFERITA"
_MODALITA_AMMESSE = frozenset({MODALITA_IMMEDIATA, MODALITA_DIFFERITA})

_STATO_PREVENTIVO_ACCETTATO = "ACCETTATO"
_STATO_PREVENTIVO_EVASO = "EVASO"
_STATO_COMMESSA_PRONTA = "PRONTA_FATTURAZIONE"

_SORGENTE_PREVENTIVO = "PREVENTIVO"
_SORGENTE_COMMESSA = "COMMESSA"


# Scopo: normalizza il valore competenza (string/date) al primo del mese.
# Accetta 'YYYY-MM-DD', 'YYYY-MM', o un date. None/invalido → None.
def _parse_competenza_mese(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.replace(day=1)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if len(raw) == 7:  # 'YYYY-MM'
            raw = f"{raw}-01"
        try:
            return date.fromisoformat(raw).replace(day=1)
        except ValueError:
            return None
    return None


class PushPreventivoHandler:
    """Implementa il Protocol pratiche.BaseFlussoHandler per
    handler_key='vendita.push_preventivo'."""

    def execute(
        self,
        flusso_id: int,
        pratica_id: int,
        meta: dict[str, Any],
        handler_params: dict[str, Any],
        user: str | None = None,
    ) -> dict[str, Any]:
        meta = meta or {}
        handler_params = handler_params or {}
        prev_repo = PreventiviRepository()
        commesse_repo = CommesseRepository()
        # Import locale: evita cicli e tiene l'handler sottile sopra il dominio.
        from apps.pratiche.db.pratiche_repository import PraticheRepository
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        prat_repo = PraticheRepository()

        # Tutto il corpo in UNA transazione atomica (§8.1): un fallimento a meta'
        # rolla push + approvazione + cambio stato + sorgenti + EVASO + giornale.
        with transaction.atomic():
            # 1. Politica di fatturazione (validazione in codice, no lookup DB).
            modalita = handler_params.get("modalita_fatturazione")
            ErrorManager.require(
                modalita in _MODALITA_AMMESSE,
                code="E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA",
                message="Modalita di fatturazione non valida.",
                detail=f"modalita_fatturazione={modalita!r} non in {sorted(_MODALITA_AMMESSE)}",
                function_name=f"{_FN}.execute",
            )

            # 2. Preventivo: risolto dal ROOT della pratica (pratiche_sorgenti,
            #    legame creato a PREVENTIVAZIONE) — non da meta schemaless.
            preventivo_id = prev_repo.get_preventivo_id_by_pratica_root(pratica_id)
            ErrorManager.require(
                preventivo_id is not None,
                code="E_VENDITA_PREVENTIVO_NON_COLLEGATO",
                message="Nessun preventivo ROOT collegato alla pratica.",
                detail=f"pratica_id={pratica_id}",
                function_name=f"{_FN}.execute",
            )
            assert preventivo_id is not None
            preventivo = prev_repo.get_preventivo(preventivo_id)
            ErrorManager.require(
                preventivo is not None,
                code="E_PREV_NOT_FOUND",
                message="Preventivo non trovato.",
                detail=f"preventivo_id={preventivo_id}",
                function_name=f"{_FN}.execute",
            )
            assert preventivo is not None
            ErrorManager.require(
                preventivo["stato_codice_interno"] == _STATO_PREVENTIVO_ACCETTATO,
                code="E_VENDITA_PREVENTIVO_NON_ACCETTATO",
                message="Solo un preventivo ACCETTATO puo' essere confermato.",
                detail=f"stato={preventivo['stato_codice_interno']}",
                function_name=f"{_FN}.execute",
            )
            preventivo_uid = preventivo["uid"]

            # 3. Risoluzione politica → (fatturazione_immediata, competenza_mese).
            if modalita == MODALITA_IMMEDIATA:
                fatturazione_immediata = True
                competenza_mese = date.today().replace(day=1)
            else:  # DIFFERITA
                fatturazione_immediata = False
                competenza_mese = _parse_competenza_mese(meta.get("competenza_fatturazione"))
                ErrorManager.require(
                    competenza_mese is not None,
                    code="E_VENDITA_COMPETENZA_RICHIESTA",
                    message="Competenza di fatturazione richiesta per la modalita DIFFERITA.",
                    detail=f"competenza_fatturazione={meta.get('competenza_fatturazione')!r}",
                    function_name=f"{_FN}.execute",
                )

            # 4. Idempotenza (§8.2): una commessa gia' agganciata = push gia' fatto.
            #    Grazie alla transazione unica, lo stato e' sempre "tutto o niente":
            #    se la commessa esiste, l'intera CONFERMA precedente e' committata.
            existing = commesse_repo.get_commessa_id_by_sorgente(
                sorgente_codice=_SORGENTE_PREVENTIVO, sorgente_uid=preventivo_uid,
            )
            ErrorManager.require(
                existing is None,
                code="E_VENDITA_PREVENTIVO_GIA_PUSHATO",
                message="Preventivo gia' pushato a commessa.",
                detail=f"preventivo_id={preventivo_id}, commessa_id={existing}",
                function_name=f"{_FN}.execute",
            )

            # 5. Applica la politica sul preventivo (c7-2) e delega il push.
            #    Sul percorso pratica la config e' autorevole: scrivo qui i due
            #    campi che la pipeline propaga a testata/righe commessa.
            prev_repo.update_preventivo(
                preventivo_id,
                fatturazione_immediata=fatturazione_immediata,
                competenza_mese=competenza_mese,
            )
            pr_run_commesse_push_one(
                sorgente_codice=_SORGENTE_PREVENTIVO,
                sorgente_uid=preventivo_id,
            )
            commessa_id = commesse_repo.get_commessa_id_by_sorgente(
                sorgente_codice=_SORGENTE_PREVENTIVO, sorgente_uid=preventivo_uid,
            )
            ErrorManager.require(
                commessa_id is not None,
                code="E_VENDITA_PUSH_COMMESSA_NON_CREATA",
                message="Push completato ma nessuna commessa risulta agganciata.",
                detail=f"preventivo_id={preventivo_id}",
                function_name=f"{_FN}.execute",
            )
            assert commessa_id is not None

            # 6-7. Righe → APPROVATA, poi testata → PRONTA_FATTURAZIONE (ordine
            #      vincolante: il guard DB richiede >=1 riga APPROVATA+NON_EMESSA).
            commesse_repo.approva_commessa_attivita(commessa_id=commessa_id, user=user)
            commesse_repo.cambia_stato_commessa(
                commessa_id=commessa_id, nuovo_stato=_STATO_COMMESSA_PRONTA, user=user,
            )

            # 8. Aggancio pratiche_sorgenti (idempotente): preventivo ROOT,
            #    commessa COLLEGATO. sorgente_uid: preventivo→uid, commessa→id.
            prat_repo.upsert_pratica_sorgente(
                pratica_id=pratica_id, sorgente_codice=_SORGENTE_PREVENTIVO,
                sorgente_uid=preventivo_uid, ruolo_link="ROOT",
            )
            prat_repo.upsert_pratica_sorgente(
                pratica_id=pratica_id, sorgente_codice=_SORGENTE_COMMESSA,
                sorgente_uid=str(commessa_id), ruolo_link="COLLEGATO",
            )

            # 9. Preventivo → EVASO (transizione ESPLICITA, senza swallow: a
            #    differenza di push_a_commessa, qui un errore deve rollbackare).
            prev_repo.cambia_stato(preventivo_id, _STATO_PREVENTIVO_EVASO, user or "handler")

            # 10. Giornale di dominio (canale fn_log_evento_dominio, origine HANDLER).
            competenza_iso = competenza_mese.isoformat() if competenza_mese else None
            prat_repo.log_evento_dominio(
                pratica_id=pratica_id, flusso_id=flusso_id,
                tipo_evento="DOMINIO_COMMESSA_CREATA",
                meta={
                    "commessa_id": commessa_id,
                    "preventivo_id": preventivo_id,
                    "modalita_fatturazione": modalita,
                    "competenza_mese": competenza_iso,
                },
            )
            prat_repo.log_evento_dominio(
                pratica_id=pratica_id, flusso_id=flusso_id,
                tipo_evento="DOMINIO_PREVENTIVO_EVASO",
                meta={"preventivo_id": preventivo_id},
            )

        # 11. Risultato (consumato dal dispatch / esposto in giornale flusso).
        return {
            "commessa_id": commessa_id,
            "preventivo_id": preventivo_id,
            "modalita_fatturazione": modalita,
            "competenza_mese": competenza_iso,
        }
