# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler flusso `vendita.push_preventivo` — orchestratore CONFERMA_VENDITA.
#        Al passaggio del flusso CONFERMA in IN_CORSO smista per natura le righe
#        del preventivo ACCETTATO verso le destinazioni operative:
#          - righe MERCE (natura destinazione_tipo='ORDINE') → nuovo ordine DRAFT
#            via vendite.fn_push_preventivo_a_ordine (idempotenza di riga, D8);
#          - righe SERVIZIO una-tantum (destinazione_tipo='COMMESSA') → commessa
#            diretta via pr_run_commesse_push_one, applicando la politica di
#            fatturazione (IMMEDIATA/DIFFERITA) presa dai handler_params (c7-2);
#          - righe RICORRENTI: non entrano nel preventivo (bloccate a DB, D9).
#        Poi porta la commessa a PRONTA_FATTURAZIONE ed evade il preventivo SOLO
#        se non resta residuo merce (gate EVASO, D6). Primo handler reale del motore.
#
#        Brief: docs/it/dev/work-in-progress/brief-be-pratica-preventivi.md +
#               docs/it/dev/work-in-progress/brief-preventivi-ordini.md (§2/§7, split).
#        - delega i due rami a orchestratori/fn esistenti (pr_run_commesse_push_one,
#          fn_push_preventivo_a_ordine), NON reimplementa (regola del 2);
#        - tutto il corpo in una sola transazione atomica (§8.1);
#        - idempotenza (§8.2.3 adattata allo split, Tid 2026-06-09): ancora vera =
#          ACCETTATO→EVASO terminale + idempotenza di riga DB; guard up-front
#          natura-completo solo nel caso "nulla da smistare" (artefatti già
#          presenti → E_VENDITA_PREVENTIVO_GIA_PUSHATO; preventivo vuoto →
#          E_PREV_NESSUNA_RIGA);
#        - policy applicata via UPDATE del preventivo pre-push commessa (c7-2, §8.6),
#          competenza DIFFERITA richiesta solo se il ramo commessa scatta.
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
        # rolla push ordine + push commessa + approvazione + cambio stato +
        # sorgenti + EVASO + giornale.
        with transaction.atomic():
            # 1. Politica di fatturazione (validazione param in codice, no lookup
            #    DB). La competenza per la DIFFERITA si valida piu' avanti, solo
            #    se il ramo commessa scatta (per la sola-merce e' irrilevante).
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
            #    Il guard ACCETTATO e' l'ANCORA DI IDEMPOTENZA del flusso: a
            #    CONFERMA completata il preventivo e' EVASO (terminale), quindi
            #    un ri-fire cade qui con E_VENDITA_PREVENTIVO_NON_ACCETTATO.
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

            # 3. Discovery per natura (modello split, fn DB natura-aware
            #    2026-06-09): quanta merce resta da smistare a ordine e quante
            #    righe servizio sono eleggibili al push commessa (la lista DB
            #    restituisce solo righe destinazione COMMESSA).
            ha_residuo_ordine = prev_repo.preventivo_ha_residuo_ordine(preventivo_id)
            righe_commessa = prev_repo.count_righe_pushable(preventivo_id)

            # 4. Guard idempotenza natura-completo (§8.2.3 adattata allo split,
            #    Tid 2026-06-09): se non resta NULLA da smistare distinguo
            #    "gia' smistato" (esistono ordine o commessa pregressi →
            #    E_VENDITA_PREVENTIVO_GIA_PUSHATO) da "preventivo vuoto"
            #    (nessuna riga smistabile → E_PREV_NESSUNA_RIGA). Nel caso
            #    normale di dispatch parziale precedente (D5) i rami sotto
            #    completano il residuo: niente blocco.
            if not ha_residuo_ordine and righe_commessa == 0:
                commessa_pregresso = commesse_repo.get_commessa_id_by_sorgente(
                    sorgente_codice=_SORGENTE_PREVENTIVO, sorgente_uid=preventivo_uid,
                )
                ordine_pregresso = prev_repo.exists_ordine_da_preventivo(preventivo_id)
                ErrorManager.require(
                    not (commessa_pregresso is not None or ordine_pregresso),
                    code="E_VENDITA_PREVENTIVO_GIA_PUSHATO",
                    message="Preventivo gia' smistato (ordine/commessa esistenti).",
                    detail=(
                        f"preventivo_id={preventivo_id}, "
                        f"commessa_id={commessa_pregresso}, ordine_pregresso={ordine_pregresso}"
                    ),
                    function_name=f"{_FN}.execute",
                )
                ErrorManager.require(
                    False,
                    code="E_PREV_NESSUNA_RIGA",
                    message="Nessuna riga smistabile sul preventivo.",
                    detail=f"preventivo_id={preventivo_id}",
                    function_name=f"{_FN}.execute",
                )

            ordine_id: int | None = None
            commessa_id: int | None = None
            competenza_mese: date | None = None

            # 5. Ramo MERCE → ordine (D8). Idempotenza di riga + aggancio
            #    pratiche_sorgenti (preventivo ROOT + ordine COLLEGATO, codice
            #    ORDINE_VENDITA) li esegue la fn DB quando passo p_pratica_id.
            if ha_residuo_ordine:
                ordine_id = prev_repo.push_a_ordine(
                    preventivo_id, pratica_id=pratica_id,
                )

            # 6. Ramo SERVIZIO una-tantum → commessa diretta. Qui vive la policy
            #    di fatturazione (c7-2): si applica alla commessa. La lista DB e'
            #    natura-aware → nessun rischio di doppio routing della merce.
            if righe_commessa > 0:
                if modalita == MODALITA_IMMEDIATA:
                    fatturazione_immediata = True
                    competenza_mese = date.today().replace(day=1)
                else:  # DIFFERITA
                    fatturazione_immediata = False
                    competenza_mese = _parse_competenza_mese(
                        meta.get("competenza_fatturazione"),
                    )
                    ErrorManager.require(
                        competenza_mese is not None,
                        code="E_VENDITA_COMPETENZA_RICHIESTA",
                        message="Competenza di fatturazione richiesta per la modalita DIFFERITA.",
                        detail=f"competenza_fatturazione={meta.get('competenza_fatturazione')!r}",
                        function_name=f"{_FN}.execute",
                    )

                # Applica la politica sul preventivo (c7-2) e delega il push.
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

                # Righe → APPROVATA, poi testata → PRONTA_FATTURAZIONE (ordine
                # vincolante: il guard DB richiede >=1 riga APPROVATA+NON_EMESSA).
                commesse_repo.approva_commessa_attivita(commessa_id=commessa_id, user=user)
                commesse_repo.cambia_stato_commessa(
                    commessa_id=commessa_id, nuovo_stato=_STATO_COMMESSA_PRONTA, user=user,
                )

                # Aggancio pratiche_sorgenti (idempotente): preventivo ROOT,
                # commessa COLLEGATO. sorgente_uid: preventivo→uid, commessa→id.
                prat_repo.upsert_pratica_sorgente(
                    pratica_id=pratica_id, sorgente_codice=_SORGENTE_PREVENTIVO,
                    sorgente_uid=preventivo_uid, ruolo_link="ROOT",
                )
                prat_repo.upsert_pratica_sorgente(
                    pratica_id=pratica_id, sorgente_codice=_SORGENTE_COMMESSA,
                    sorgente_uid=str(commessa_id), ruolo_link="COLLEGATO",
                )

            # 7. Gate EVASO (D6): evadi il preventivo SOLO se non resta residuo
            #    merce. Dopo il push ordine tutte le righe merce sono allocate →
            #    residuo False. Transizione ESPLICITA, senza swallow (a differenza
            #    di push_a_commessa: qui un errore deve rollbackare la CONFERMA).
            evaso = not prev_repo.preventivo_ha_residuo_ordine(preventivo_id)
            if evaso:
                prev_repo.cambia_stato(preventivo_id, _STATO_PREVENTIVO_EVASO, user or "handler")

            # 8. Giornale di dominio (canale fn_log_evento_dominio, origine
            #    HANDLER): un evento per artefatto effettivamente prodotto.
            competenza_iso = competenza_mese.isoformat() if competenza_mese else None
            if ordine_id is not None:
                prat_repo.log_evento_dominio(
                    pratica_id=pratica_id, flusso_id=flusso_id,
                    tipo_evento="DOMINIO_ORDINE_CREATO",
                    meta={"ordine_id": ordine_id, "preventivo_id": preventivo_id},
                )
            if commessa_id is not None:
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
            if evaso:
                prat_repo.log_evento_dominio(
                    pratica_id=pratica_id, flusso_id=flusso_id,
                    tipo_evento="DOMINIO_PREVENTIVO_EVASO",
                    meta={"preventivo_id": preventivo_id},
                )

        # 9. Risultato (consumato dal dispatch / esposto in giornale flusso).
        return {
            "preventivo_id": preventivo_id,
            "ordine_id": ordine_id,
            "commessa_id": commessa_id,
            "modalita_fatturazione": modalita,
            "competenza_mese": competenza_iso,
            "evaso": evaso,
        }
