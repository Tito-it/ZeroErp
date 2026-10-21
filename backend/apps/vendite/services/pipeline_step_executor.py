# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Esecuzione step pipeline vendite.
# ------------------------------------------------------------


import logging
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

from apps.core.services.db_error_fields import db_error_code, diagnostica_db
from apps.core.services.error_manager import ErrorManager
from apps.core.services.fan_out import FanOutRunLogger, messaggio_eccezione, run_fan_out
from apps.core.services.service_errors import ServiceError
from apps.core.api.payload_validators import optional_bool
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import LottoContext, VenditePipelineRepository
# Il vocabolario dell'esito di esecuzione dentro un lotto — specchio del CHECK
# di tabella. Vive con le altre liste chiuse del dominio (`DASH_COMPETENZA_STADI`,
# `TIPO_GRUPPO_ONERI`, …): una sede sola, e chi scrive e chi legge la usano
# entrambi. ⛔ Riscrivere le stringhe qui sarebbe la seconda sede.
from apps.vendite.db.vendite_repository import (
    STATO_ESECUZIONE_COMPLETED,
    STATO_ESECUZIONE_ERRORE,
)
from apps.vendite.services.pipeline_error_logger import PipelineErrorLogger
from apps.vendite.services.fatture_righe_service import FattureRigheService

# Esecutore di singolo step pipeline con mapping task JSON -> azioni applicative.

# Task che NON hanno (e non devono avere) un handler: segnaposto di
# configurazione che l'esecutore attraversa senza fare niente. ⚠️ Costante e non
# literal inline perche' la legge anche il cancello
# `tests/db/test_pipeline_task_handler_guardrail.py`: con due copie, aggiungerne
# un terzo qui renderebbe il cancello rosso su un task che invece e' legittimo —
# e la reazione naturale sarebbe allentare il cancello.
TASK_SENZA_HANDLER = frozenset({"noop", "log_only"})


# Scopo: Esito di un task che ha COMPLETATO il proprio giro ma con una parte
#        delle fatture in errore (D-Q p.3). Un handler che lo ritorna NON
#        interrompe lo step — le fatture sane hanno ricevuto il loro lavoro e la
#        transazione deve committare (i log 'C' per-fattura li ha gia' scritti
#        il DB) — ma il task_run va chiuso in ERRORE e non in COMPLETATO:
#        `fn_resolve_lotto_task_execution_mode` risolve COMPLETATO → SKIP, e al
#        rilancio dello step il task verrebbe SALTATO — la correzione
#        dell'anagrafica non verrebbe mai riletta. Con ERRORE risolve RESUME
#        (policy RESUME_TASK) e il rilancio ripete davvero il task.
#        ⚠️ NON sollevare al suo posto: un raise farebbe rollback dell'intero
#        step, cancellando anche il lavoro delle fatture sane E la marcatura
#        di quelle rotte — il rilancio ripartirebbe da zero, identico, per sempre.
@dataclass(frozen=True)
class TaskEsitoParziale:
    error_code: str
    error_message: str
    meta: dict[str, Any] = field(default_factory=dict)


# Scopo: Esito di un task RIUSCITO che ha comunque qualcosa da dichiarare nel
#        diario. Il task_run si chiude in COMPLETATO come sempre: cambia solo
#        che il `meta` porta i contatori del giro invece di restare muto.
# ⭐ Serve perche' una promessa va verificata anche quando REGGE. Fino al
#        2026-09-04 il pull scriveva `totale`/`ok`/`falliti` solo quando
#        qualcuno falliva: un giro riuscito e un giro che non ha nemmeno
#        provato producevano lo stesso diario vuoto, cioe' proprio il caso che
#        il perimetro consegnato (D1+D2) rende possibile — marchio assente,
#        zero righe, nessun errore. Con i contatori sempre scritti, «ok: 0 su
#        3» si legge invece di doverlo dedurre.
# ⚠️ Il `meta` viene FUSO con quello scritto all'avvio del run
#        (`fn_set_runtime_task_run_esito` fa `meta || v_meta`), quindi non
#        travolge `rollback`.
@dataclass(frozen=True)
class TaskEsitoOk:
    meta: dict[str, Any] = field(default_factory=dict)


# Scopo: Messaggio TECNICO per-commessa del pull, con l'id davanti al tipo di
#        errore. Sede unica del formato: lo stesso testo va nel
#        `context.dettaglio_tecnico` del log di lotto e nel `context.errors`
#        del raise all-fail — due copie che divergerebbero.
#        La normalizzazione dell'eccezione NON e' rifatta qui: e' quella del BB
#        (`messaggio_eccezione` / `FanOutItemErrore.messaggio`).
# ⚠️ DAL 2026-09-04 QUESTO NON E' PIU' IL `detail` DEL LOG, e la differenza e'
#        voluta: `detail` porta il motivo di DOMINIO (`_motivo_dominio`), che e'
#        cio' che l'operatore legge in `vw_dash_commesse_respinte`; questo resta
#        la stringa per chi diagnostica. Le due superfici hanno lettori diversi,
#        e prima erano la stessa cosa solo perche' la seconda non esisteva.
def _messaggio_pull(commessa_id: Any, messaggio: str) -> str:
    return f"Errore emit commessa_id={commessa_id}: {messaggio}"


# Scopo: IL MOTIVO DI DOMINIO, separato dal dump tecnico.
#        `vendite.vw_dash_commesse_respinte` mostra a video `meta->>'detail'`
#        di ogni riga respinta, e la promessa di Tid — «ognuna mostra il
#        problema, per poter cercare di risolvere» — e' vera solo se li' dentro
#        c'e' *«ROOT source mancante per commessa 34137»* e non un impasto di
#        eccezione Python, DETAIL, HINT, CONTEXT e stack PL/pgSQL.
# ⭐ La lettura NON e' fatta a mano: `diagnostica_db` e' la sede unica dei campi
#        strutturati di un errore DB (`apps/core/services/db_error_fields`), la
#        stessa che il resto della pipeline usa per il codice.
# 🔴 L'ORDINE E' `messaggio` PRIMA DI `detail`, ed e' il contrario di quello che
#        sembra. Misurato sul database vero il 2026-09-04, facendo fallire
#        davvero il pull sulla commessa 34137:
#
#          message_primary -> «Indicare un valore per ROOT source mancante
#                              per commessa 34137. Dato obbligatorio.»
#          message_detail  -> «Non e' stato assegnato un valore
#                              all'informazione richiesta.»
#
#        `fn_log_and_raise_error` compone il MESSAGGIO con il dettaglio di
#        dominio che la funzione madre gli passa, mentre `DETAIL` e `HINT`
#        portano il testo generico della POLICY dell'errore — identico per ogni
#        `E_VALORE_MANCANTE` del sistema. Preferire `detail` metteva a video una
#        frase vera e inutile al posto del motivo.
# ⛔ La prima stesura lo faceva, e i test erano VERDI: il finto
#        (`make_db_error(detail=...)`) metteva il motivo in DETAIL, cioe' in un
#        posto in cui il sistema non lo mette. E' esattamente la trappola che
#        `apps/core/tests/db_error_fakes` dichiara nel proprio docstring.
# ⚠️ Il ripiego finale e' il messaggio normalizzato del BB: un errore nato in
#        Python (non un `DatabaseError`) non ha nessun campo diag, e restare
#        senza motivo sarebbe peggio di un motivo tecnico.
def _motivo_dominio(exc: BaseException, *, ripiego: str) -> str:
    diag = diagnostica_db(exc)
    return (diag.messaggio or diag.detail or ripiego).strip()


# Scopo: Diario per-commessa del pull da commessa — l'unica parte di DOMINIO del
#        fan-out: scrive il motivo del singolo fallimento sui log di lotto, dove
#        il cockpit lo legge. Il BB sa quando chiamarlo, questo sa dove scrivere:
#        `apps.core` resta senza dipendenze verso `vendite`.
#        Eredita i no-op di `FanOutRunLogger` e sovrascrive solo `item_failed`:
#        inizio e fine giro sono gia' tracciati dal task_run della pipeline.
@dataclass(frozen=True)
class _PullCommesseRunLogger(FanOutRunLogger):
    error_logger: PipelineErrorLogger
    task: str
    lotto_id: int
    stato_doc_fiscale_id: int
    # ⚠️ Serve a chiedere di CHI e' il fallimento: la conversione commessa →
    #    documenti vive a database (`script.fn_gruppi_di_commessa_nel_lotto`) e
    #    non si riscrive qui.
    repository: Any

    # Scopo: Registra sui log di lotto la commessa che non e' passata.
    # ⭐ `detail` porta il MOTIVO DI DOMINIO e non piu' il dump: e' il campo che
    #    `vw_dash_commesse_respinte` mostra a video come `dettaglio`, cioe' cio'
    #    che l'operatore legge per capire su cosa agire. Il dump non si perde —
    #    va nel `context` sotto `dettaglio_tecnico`, dove serve a chi diagnostica
    #    e non a chi lavora.
    def item_failed(self, *, item: Any, indice: int, exc: Exception) -> None:
        tecnico = _messaggio_pull(item, messaggio_eccezione(exc))
        motivo = _motivo_dominio(exc, ripiego=tecnico)
        # ⭐ LA SEGNALAZIONE DICHIARA DI QUALE DOCUMENTO PARLA (§6.1 del brief
        #    `brief-db-uscita-documento-dal-giro`, 2026-09-08).
        #
        # 🔴 IL DIFETTO CHE QUESTA RIGA CHIUDE, misurato sul lotto LTF-0010003:
        #    la segnalazione nasceva senza proprietario, quindi valeva «e' del
        #    giro» — e una segnalazione del giro ferma il giro per costruzione.
        #    Risultato: si poteva togliere il documento rotto dal giro e il lotto
        #    restava fermo lo stesso, perche' cio' che lo bloccava non era
        #    attribuito a nessuno. Il verbo c'era e non sbloccava niente.
        #
        # ⛔ UNA RIGA PER DOCUMENTO, e non una sola con una chiave scelta fra le
        #    tante: una commessa puo' alimentarne piu' d'uno. Dichiararne uno
        #    lascerebbe gli altri a bloccare il lotto **per sempre** — non
        #    sarebbero togliibili, perche' niente li nomina.
        #
        # ⚠️ `[]` E' UNA RISPOSTA e va letta: «questo fallimento non ha un
        #    proprietario in questo lotto» ⇒ UNA riga senza `gruppo_key`, che
        #    torna a valere «e' del giro» e ferma il giro. ⛔ Non zero righe: un
        #    fallimento che non blocca niente e' un fallimento perso.
        gruppi = self.repository.gruppi_di_commessa_nel_lotto(self.lotto_id, item)
        for gruppo_key in gruppi or [None]:
            self.error_logger.log_error(
                scope="LOTTO",
                severity="C",
                code="E_PULL_COMMESSA",
                message=f"Errore emissione commessa {item}",
                detail=motivo,
                lotto_id=self.lotto_id,
                stato_doc_fiscale_id=self.stato_doc_fiscale_id,
                context={
                    "commessa_id": item,
                    "task": self.task,
                    "dettaglio_tecnico": tecnico,
                },
                function_name=(
                    "vendite.pipeline_step_executor."
                    "_handle_pull_attivita_da_commessa_task"
                ),
                gruppo_key=gruppo_key,
            )


class PipelineStepExecutor:
    """Controparte Django della funzione SQL vendite.fn_execute_pipeline_step."""

    # Dipendenze d'ORDINE fra task dello STESSO step: `task -> task che deve
    # precederlo`. Non e' una dipendenza logica generica (quella e' la sequenza
    # degli step): e' il sottoinsieme in cui invertire l'ordine dentro un solo
    # step produce un risultato SBAGLIATO invece che un errore.
    #
    # `genera_scadenze_lotto` dopo `ricalcola_iva_lotto`: la base di
    # ripartizione del piano rate e' `fatture.totale_a_pagare`, che nasce dal
    # ricalcolo. Con l'ordine invertito la base non e' pronta e il generatore
    # solleva `E_SCADENZE_BASE_NON_PRONTA` per OGNI fattura del lotto (D-D
    # caso NULL) — cioe' un giro interamente rosso che sembra un difetto dei
    # dati mentre e' una riga di configurazione girata. La verifica sta qui e
    # non nel solo CSV perche' la configurazione la scrive un altro team, e
    # un ordine sbagliato deve fermarsi PRIMA di scrivere, non dopo.
    _TASK_ORDER_DEPENDENCIES: dict[str, tuple[str, ...]] = {
        "genera_scadenze_lotto": ("ricalcola_iva_lotto",),
        # Il legame documentale si scrive DOPO la numerazione: prima, un reset
        # di lotto puo' ancora arrivare, e `fn_cleanup_fatture_by_ids` non
        # cancella `vendite.fatture_rettifiche` (FK non ON DELETE CASCADE).
        # Il seed lo mette gia' nell'ordine giusto: questa riga fa in modo che
        # una configurazione girata si fermi PRIMA che il primo task scriva,
        # invece di scoprirsi a documenti numerati.
        "popola_fatture_rettifiche": ("numera_fatture",),
        # ⛔ Il consumo del plafond va PRIMA della numerazione, e la ragione e'
        # lo stato: `numera_fatture` porta il documento oltre la soglia di
        # congelamento, e `trgfn_fattura_satellite_guard_congelamento` legge lo
        # stato VIVO al momento della scrittura. Con l'ordine invertito la
        # spezzatura delle righe verrebbe RIFIUTATA — non in silenzio, ma con un
        # errore che parla d'altro, in un punto dove nessuno lo cerca.
        # ⚠️ Finche' `consuma_plafond_lotto` non e' nel seed della pipeline
        # questa riga non fa nulla: il predecessore assente e' una
        # configurazione valida (puo' vivere in uno step precedente). Sta qui
        # PRIMA del seed apposta — cosi' il giorno che la configurazione arriva,
        # se arriva girata si ferma prima di scrivere invece di scoprirsi a
        # documenti gia' numerati.
        "numera_fatture": ("consuma_plafond_lotto",),
    }

    # Scopo: Inizializza la istanza.
    def __init__(
        self,
        repository: VenditePipelineRepository | None = None,
        fatture_righe_service: FattureRigheService | None = None,
        error_logger: PipelineErrorLogger | None = None,
        commesse_repository: CommesseRepository | None = None,
    ) -> None:
        self.repository = repository or VenditePipelineRepository()
        self.fatture_righe_service = fatture_righe_service or FattureRigheService(self.repository)
        self.error_logger = error_logger or PipelineErrorLogger(self.repository)
        self.commesse_repository = commesse_repository or CommesseRepository()
        self.handler_registry = {
            "select_attivita_default": self._handle_select_attivita_task,
            "generate_fatture_righe_default": self._handle_generate_fatture_righe_task,
            "genera_fondi_source_lotto_default": self._handle_genera_fondi_source_lotto_task,
            "applica_fondi_lotto_default": self._handle_applica_fondi_lotto_task,
            "ricalcola_iva_lotto_default": self._handle_ricalcola_iva_lotto_task,
            "prepare_sdi_payload_lotto_default": self._handle_prepare_sdi_payload_lotto_task,
            "numera_fatture_default": self._handle_numera_fatture_task,
            "stampa_documenti_lotto_default": self._handle_stampa_documenti_lotto_task,
            "close_lotto_default": self._handle_close_lotto_task,
            "reset_lotto_draft_default": self._handle_reset_lotto_draft_task,
            "pull_attivita_da_commessa_default": self._handle_pull_attivita_da_commessa_task,
            "snapshot_indirizzi_lotto_default": self._handle_snapshot_indirizzi_lotto_task,
            "genera_scadenze_lotto_default": self._handle_genera_scadenze_lotto_task,
            "popola_fatture_rettifiche_default": self._handle_popola_fatture_rettifiche_task,
            "consuma_plafond_lotto_default": self._handle_consuma_plafond_lotto_task,
        }

    # Scopo: Gestisce uno step pipeline validando input, risolvendo processi da configurazione DB e dispatch dei task
    # ⚠️ `correlation_id` e' l'identita' del GIRO (D-7), non del lotto: la
    #    genera il runner a ogni corsa e attraversa di qui per finire sulla riga
    #    del tentativo. Facoltativa per disegno — chi esegue uno step fuori da
    #    un giro (rollback puntuale, rilancio manuale) non ne ha uno, e un uuid
    #    coniato qui sarebbe un filo che non lega niente.
    def execute_step(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        tipo_lotto: str,
        *,
        rollback: bool = False,
        dry_run: bool = False,
        correlation_id: str | None = None,
    ) -> None:
        ErrorManager.require(
            bool(lotto_id and stato_doc_fiscale_id and tipo_lotto and tipo_lotto.strip()),
            code="E_PIPELINE_VALIDATION",
            message="Parametri pipeline non validi.",
            detail="lotto_id, stato_doc_fiscale_id e tipo_lotto sono obbligatori",
            context={
                "lotto_id": lotto_id,
                "stato_doc_fiscale_id": stato_doc_fiscale_id,
                "tipo_lotto": tipo_lotto,
            },
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )

        context = self.repository.get_lotto_context(lotto_id)
        ErrorManager.require(
            context is not None and context.competenza_mese is not None,
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            message="Lotto pipeline non trovato.",
            detail=f"Lotto non trovato: {lotto_id}",
            context={"lotto_id": lotto_id},
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )
        assert context is not None

        processi = self.repository.get_step_processes(
            stato_doc_fiscale_id,
            tipo_lotto=tipo_lotto,
            utility_id=context.utility_id,
            tipo_doc_fiscale_id=context.tipo_doc_fiscale_id,
            rollback=rollback,
        )
        ErrorManager.require(
            bool(processi),
            code="E_PIPELINE_NOT_FOUND",
            message="Configurazione pipeline non trovata.",
            detail=(
                "Pipeline non trovata o processi vuoti per "
                f"stato_doc_fiscale_id={stato_doc_fiscale_id}, tipo_lotto={tipo_lotto}"
            ),
            context={
                "stato_doc_fiscale_id": stato_doc_fiscale_id,
                "tipo_lotto": tipo_lotto,
                "rollback": rollback,
            },
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )

        self._validate_task_order(
            processi,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            tipo_lotto=tipo_lotto,
            rollback=rollback,
        )

        pipeline_id = self.repository.get_pipeline_id_for_step(
            tipo_lotto,
            stato_doc_fiscale_id,
            utility_id=context.utility_id,
            tipo_doc_fiscale_id=context.tipo_doc_fiscale_id,
        )

        # Esegue in ordine i task definiti nel JSON processi/rollback.
        #
        # ⭐ I TASK DI UNO STEP SONO UNA CATENA, e il rilancio la deve percorrere
        #    da dove riparte (2026-09-12, LTF-0010973 / lotto 13338). Il resolver
        #    DB (`fn_resolve_lotto_task_execution_mode`) decide PER TASK guardando
        #    la sola ultima corsa di quel task: `COMPLETATO → SKIP`. Ma un task
        #    che oggi viene RIESEGUITO cambia l'input di quelli che lo seguono:
        #    al primo giro il pull era fallito, `select_attivita`,
        #    `generate_fatture_righe` e `snapshot_indirizzi` erano girati A
        #    VUOTO e chiusi COMPLETATO; al rilancio il pull ha ripreso le due
        #    commesse (`totale 2 · ok 2`) e i tre a valle sono stati SALTATI
        #    come «gia' fatti» — le attivita' emesse non sono mai diventate
        #    fatture, e il lotto e' uscito COMPLETATO con zero documenti.
        # ⇒ REGOLA: a valle di un task eseguito in QUESTO giro nessun task si
        #    salta. Il `COMPLETATO` di un task a valle vale finche' tutto cio'
        #    che lo precede e' stato saltato; il primo task eseguito lo rende
        #    stantio. E' un fatto del giro in corso, che solo l'orchestratore
        #    conosce: per questo la regola sta qui e non nel resolver, che
        #    risponde su un task alla volta senza sapere dell'ordine.
        # ⚠️ Rieseguire i task a valle e' SICURO perche' sono idempotenti per
        #    costruzione: `fn_select_attivita_fatturabili` prende solo le AF non
        #    ancora lockate, `generate_fatture_righe` solo le AF non ancora
        #    fatturate con testate get-or-create, lo snapshot indirizzi salta le
        #    fatture gia' servite. Un task a valle NON idempotente sarebbe un
        #    difetto suo, non una ragione per saltarlo.
        a_valle_di_task_eseguito = False
        for process in processi:
            eseguito = self._run_task(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                process=process,
                context=context,
                rollback=rollback,
                dry_run=dry_run,
                pipeline_id=pipeline_id,
                correlation_id=correlation_id,
                a_valle_di_task_eseguito=a_valle_di_task_eseguito,
            )
            a_valle_di_task_eseguito = a_valle_di_task_eseguito or eseguito

    # Scopo: Verifica le dipendenze d'ordine di `_TASK_ORDER_DEPENDENCIES` sulla
    #        sequenza di task dello step, PRIMA che il primo task scriva.
    #        Perimetro deliberatamente stretto, e le due esclusioni sono
    #        entrambe casi legittimi, non scorciatoie:
    #        - se il predecessore NON e' in questo step non si fallisce: puo'
    #          vivere in uno step precedente, ed e' una configurazione valida
    #          (fallire li' vieterebbe di spezzare la catena su piu' step);
    #        - in ROLLBACK non si verifica: la catena di annullamento percorre
    #          i passi a ritroso, quindi l'ordine richiesto e' l'opposto.
    #        Risultato atteso: `E_PIPELINE_VALIDATION` con i due task nel detail
    #        — una configurazione girata si legge dal messaggio, senza dover
    #        risalire da N fatture rosse alla riga di CSV che le ha prodotte.
    def _validate_task_order(
        self,
        processi: list[dict[str, Any]],
        *,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        tipo_lotto: str,
        rollback: bool,
    ) -> None:
        if rollback:
            return
        sequenza = [str(p.get("task", "")).strip() for p in processi]
        for posizione, task in enumerate(sequenza):
            for predecessore in self._TASK_ORDER_DEPENDENCIES.get(task, ()):
                if predecessore not in sequenza:
                    continue  # vive in uno step precedente: configurazione valida
                if sequenza.index(predecessore) > posizione:
                    ErrorManager.raise_error(
                        code="E_PIPELINE_VALIDATION",
                        message="Ordine dei task della pipeline non valido.",
                        detail=(
                            f"Il task '{task}' deve seguire '{predecessore}' "
                            f"nello stesso step, ma lo precede: {' > '.join(sequenza)}"
                        ),
                        context={
                            "lotto_id": lotto_id,
                            "stato_doc_fiscale_id": stato_doc_fiscale_id,
                            "tipo_lotto": tipo_lotto,
                            "task": task,
                            "predecessore": predecessore,
                            "sequenza": sequenza,
                        },
                        function_name="vendite.pipeline_step_executor._validate_task_order",
                        log_to_db=True,
                    )

    # Scopo: Gestisce il task di step con logging fase, risoluzione handler via registry e gestione errori applicativi.
    #        Ritorna `True` se il task e' stato ESEGUITO (handler invocato), `False`
    #        se e' stato saltato o non ha un handler: e' il segnale con cui
    #        `execute_step` sa che i task a valle non possono piu' essere saltati.
    # ⚠️ `a_valle_di_task_eseguito`: se vero, uno `SKIP` del resolver NON si onora
    #        — il `COMPLETATO` che lo motiva e' precedente a un task a monte
    #        rieseguito in questo giro, quindi e' stantio (vedi `execute_step`).
    def _run_task(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        process: dict[str, Any],
        context: LottoContext,
        rollback: bool,
        dry_run: bool,
        pipeline_id: int | None = None,
        correlation_id: str | None = None,
        a_valle_di_task_eseguito: bool = False,
    ) -> bool:
        task = str(process.get("task", "")).strip()
        fase = process.get("fase") or "Esecuzione step"
        params = process.get("params") or {}
        fn_name = params.get("fn")
        implementation_key = params.get("implementation_key")

        self.repository.log_pipeline_fase(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            fase=fase,
            status="I",
            messaggio=None,
            meta={
                "task": task,
                "params": params,
                "rollback": rollback,
                "dry_run": dry_run,
            },
        )

        if task in TASK_SENZA_HANDLER:
            return False

        handler_code = self.repository.get_task_handler_code(
            task_code=task,
            implementation_key=implementation_key,
        )

        if dry_run:
            return False

        task_handler = self.handler_registry.get(handler_code)
        if task_handler is None:
            self.error_logger.log_error(
                scope="LOTTO",
                severity="C",
                code="E_TASK_IMPLEMENTATION_NOT_FOUND",
                message="Implementazione task pipeline non trovata.",
                detail=f"Implementazione task non trovata: {task} ({handler_code})",
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                context={
                    "task": task,
                    "fase": fase,
                    "implementation_key": implementation_key,
                    "handler_code": handler_code,
                    "rollback": rollback,
                },
                function_name="vendite.pipeline_step_executor._run_task",
            )
            ErrorManager.raise_error(
                code="E_TASK_IMPLEMENTATION_NOT_FOUND",
                message="Implementazione task pipeline non trovata.",
                detail=f"Implementazione task non trovata: {task} ({handler_code})",
                context={
                    "task": task,
                    "fase": fase,
                    "implementation_key": implementation_key,
                    "handler_code": handler_code,
                },
                function_name="vendite.pipeline_step_executor._run_task",
                log_to_db=True,
            )

        # Tracing: risolve modalità esecuzione task e apre run se policy attiva.
        task_run_id: int | None = None
        if pipeline_id is not None and self.repository.task_policy_exists(pipeline_id, task):
            exec_mode = self.repository.resolve_lotto_task_execution_mode(
                lotto_id, pipeline_id, stato_doc_fiscale_id, task
            )
            # ⛔ Lo SKIP vale solo se NIENTE a monte e' stato eseguito in questo
            #    giro: altrimenti il COMPLETATO che lo motiva e' stantio e il
            #    task si rifa' (nuovo tentativo), come se il resolver avesse
            #    detto RUN. Regola e motivo in `execute_step`.
            if exec_mode.execution_mode == "SKIP" and not a_valle_di_task_eseguito:
                return False
            if exec_mode.execution_mode == "RESET_REQUIRED":
                self.error_logger.log_error(
                    scope="LOTTO",
                    severity="C",
                    code="E_TASK_RESET_REQUIRED",
                    message="Task richiede reset prima dell'esecuzione.",
                    detail=f"Reset richiesto per task {task}, lotto_id={lotto_id}",
                    lotto_id=lotto_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    context={
                        "task": task,
                        "pipeline_id": pipeline_id,
                        "last_task_stato": exec_mode.last_task_stato,
                        "last_tentativo": exec_mode.last_tentativo,
                    },
                    function_name="vendite.pipeline_step_executor._run_task",
                )
                ErrorManager.raise_error(
                    code="E_TASK_RESET_REQUIRED",
                    message="Task richiede reset prima dell'esecuzione.",
                    detail=f"Reset richiesto per task {task}, lotto_id={lotto_id}",
                    context={
                        "task": task,
                        "pipeline_id": pipeline_id,
                        "lotto_id": lotto_id,
                    },
                    function_name="vendite.pipeline_step_executor._run_task",
                    log_to_db=True,
                )
            task_run_result = self.repository.start_lotto_task_run(
                lotto_id=lotto_id,
                pipeline_id=pipeline_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                task_code=task,
                fase=fase,
                meta={"rollback": rollback},
                correlation_id=correlation_id,
            )
            task_run_id = task_run_result.task_run_id

        try:
            handler_result = task_handler(
                task=task,
                fn_name=fn_name,
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                context=context,
                params=params,
                dry_run=dry_run,
            )
        except Exception as exc:
            self._fail_task_run_safely(task_run_id, exc)
            # 🔴 IL TASK RUN IN ERRORE NON SOPRAVVIVE ALLA RIGA SOPRA, e non e'
            # colpa sua: `fn_fail_lotto_task_run` scrive DENTRO la transazione
            # dello step, che il rilancio annulla. Il diario dei task registrava
            # quindi solo cio' che era andato bene — misurato il 2026-08-21:
            # 128 COMPLETATO, 56 ANNULLATO, **zero ERRORE** su 184 run, mentre
            # i fallimenti c'erano eccome.
            # Qui si appendono all'eccezione le coordinate per RISCRIVERLO dopo
            # il rollback: lo fa il runner, che e' l'unico punto FUORI dalla
            # transazione (`_persist_task_run_error_safely`).
            # ⚠️ Attributo sull'eccezione e non `context` del ServiceError: la
            # riscrittura serve anche per le eccezioni NON di dominio, che un
            # `context` non ce l'hanno.
            # ⚠️ Solo se il tracing e' attivo (`task_run_id`): dove non c'e'
            # policy non c'e' diario, ed e' una scelta di configurazione — non
            # va aggirata scrivendo righe che il giro riuscito non scriverebbe.
            # ⚠️ `try` sull'ASSEGNAZIONE, non un di piu': non tutte le
            # eccezioni accettano attributi nuovi (una classe con `__slots__`
            # solleva `AttributeError`), e qui siamo dentro la gestione di un
            # fallimento — un secondo errore prenderebbe il posto del primo,
            # che e' l'unico che l'operatore sta aspettando. Perdere la riga di
            # diario e' accettabile; perdere il messaggio no.
            if task_run_id is not None and pipeline_id is not None:
                try:
                    # Attributo DINAMICO sull'eccezione: lo legge il runner con
                    # `getattr(exc, "zeroerp_task_run_fallito", None)`.
                    setattr(exc, "zeroerp_task_run_fallito", {  # noqa: B010 — attributo dinamico: assegnato col punto, mypy lo rifiuta (il tipo non lo dichiara)
                        "lotto_id": lotto_id,
                        "pipeline_id": pipeline_id,
                        "stato_doc_fiscale_id": stato_doc_fiscale_id,
                        "task_code": task,
                        "fase": fase,
                        # Il filo del giro viaggia con l'eccezione: chi riscrive
                        # la riga fuori dalla transazione (il telaio best-effort
                        # del runner) non ha altro modo di conoscerlo, e senza
                        # il tentativo fallito resterebbe l'unico del giro
                        # senza `correlation_id` — cioe' l'unico che la
                        # diagnostica non ritroverebbe.
                        "correlation_id": correlation_id,
                        "error_code": (
                            exc.code
                            if isinstance(exc, ServiceError)
                            else db_error_code(exc) or "E_TASK"
                        ),
                        "error_message": messaggio_eccezione(exc),
                    })
                except Exception:  # noqa: S110 - vedi commento sopra
                    pass
            raise
        if task_run_id is not None:
            # D-Q p.3: un esito PARZIALE (giro completato, alcune fatture in
            # errore) chiude il run in ERRORE senza interrompere lo step: e' cio'
            # che al rilancio produce RESUME invece di SKIP. Vedi TaskEsitoParziale.
            if isinstance(handler_result, TaskEsitoParziale):
                self.repository.fail_lotto_task_run(
                    task_run_id,
                    handler_result.error_code,
                    handler_result.error_message,
                    meta=handler_result.meta,
                )
            elif isinstance(handler_result, TaskEsitoOk):
                # Giro riuscito CHE HA QUALCOSA DA DIRE: stesso esito
                # COMPLETATO di sempre, ma il diario porta i contatori.
                self.repository.complete_lotto_task_run(
                    task_run_id, meta=handler_result.meta
                )
            else:
                self.repository.complete_lotto_task_run(task_run_id)
        # Eseguito: da qui in poi, nello step, nessuno SKIP e' piu' onorabile.
        return True

    # Scopo: Tenta di marcare il task run in errore senza mascherare l'eccezione originale.
    # ⚠️ Il codice si legge da DUE sorgenti, e la seconda non e' un di piu':
    # `ServiceError` copre gli errori nati in Python, ma un task che delega a una
    # funzione madre DB solleva un `DatabaseError` che porta il suo codice nel
    # campo strutturato (`diag.constraint_name` su P0001). Senza leggerlo, il
    # diario registra `E_TASK` su un errore che il database aveva gia' nominato.
    # 🔴 Difetto reale, comparso con R-3 (2026-08-15): i tre errori del giro
    # fondi (`E_LOTTO_NON_TROVATO`, `E_PIPELINE_SCOPE_INCOMPLETE`,
    # `E_TIPO_FONDO_NOT_FOUND`) nascevano in Python e sono passati al DB quando
    # scope e lookup sono entrati nella madre — e con loro sarebbe sparita la
    # loro attribuzione. Vale per ogni task che chiama una funzione DB, non solo
    # per i fondi.
    def _fail_task_run_safely(self, task_run_id: int | None, exc: BaseException) -> None:
        if task_run_id is None:
            return
        try:
            error_code = (
                exc.code
                if isinstance(exc, ServiceError)
                # Lettura unica del codice di dominio da un'eccezione DB: mai
                # `diag.constraint_name` a mano (apps/core/services/db_error_fields).
                else db_error_code(exc) or "E_TASK"
            )
            self.repository.fail_lotto_task_run(
                task_run_id,
                error_code,
                str(exc),
            )
        except Exception:
            # Mai mascherare l'eccezione originale: si ingoia la seconda, ma la
            # si scrive — senza traccia il task_run resterebbe IN CORSO e
            # nessuno saprebbe perche'.
            logging.getLogger(__name__).exception(
                "fail_lotto_task_run fallito: task_run_id=%s", task_run_id,
            )

    # Scopo: Valida la funzione legacy `fn` del task contro whitelist consentita per evitare override non ammessi.
    def _validate_task_function_name(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int | None = None,
        stato_doc_fiscale_id: int | None = None,
    ) -> None:
        # `fn` resta un token di compatibilita` SQL nella configurazione processi.
        # Task fuori mappa: nessun vincolo dichiarato qui (il dispatch fallisce
        # altrove se il task non esiste). Diverso dal valore `None` IN mappa:
        # quello significa task Python-only, e un `fn` dichiarato in config per
        # un task Python-only e' per definizione stale (es. la rimossa
        # `vendite.fn_generate_fatture_righe`) → deve fallire, non passare.
        functions = self.repository.ALLOWED_TASK_FUNCTIONS
        if task not in functions:
            return
        allowed = functions[task]
        if fn_name and fn_name != allowed:
            if lotto_id is not None:
                self.error_logger.log_error(
                    scope="LOTTO",
                    severity="C",
                    code="E_TASK_NOT_ALLOWED",
                    message="Funzione task non ammessa.",
                    detail=f"Funzione non ammessa per task {task}: {fn_name}",
                    lotto_id=lotto_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    context={"task": task, "fn": fn_name, "allowed": allowed},
                    function_name="vendite.pipeline_step_executor._validate_task_function_name",
                )
            ErrorManager.raise_error(
                code="E_TASK_NOT_ALLOWED",
                message="Funzione task non ammessa.",
                detail=f"Funzione non ammessa per task {task}: {fn_name}",
                context={"task": task, "fn": fn_name},
                function_name="vendite.pipeline_step_executor._validate_task_function_name",
                log_to_db=True,
            )

    # Scopo: Gestisce un'azione per ogni fattura del lotto con logging errori scope FATTURA e fail-fast
    def _run_per_fattura_task(
        self,
        *,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        task: str,
        fattura_ids: list[int],
        action: Any,
    ) -> None:
        # Helper riusabile: esecuzione task per-fattura con logging scope FATTURA.
        for fattura_id in fattura_ids:
            try:
                # 🔴 SAVEPOINT PER FATTURA — SENZA, IL PERCORSO D'ERRORE SI
                # DISTRUGGE DA SOLO. Quando una madre DB solleva, la
                # transazione PostgreSQL entra in stato ABORTITO: da quel
                # momento QUALUNQUE istruzione risponde «la transazione
                # corrente e' interrotta». Le due righe sotto — il log di scope
                # FATTURA e la scrittura del diario — sono istruzioni SQL:
                # fallivano entrambe, e il loro fallimento SOSTITUIVA l'errore
                # di dominio. L'operatore riceveva `E_PIPELINE`, «Errore nella
                # pipeline di fatturazione», e il codice vero non arrivava
                # nemmeno al diario del lotto.
                #
                # 🔴 Misurato in-app il 2026-08-21 (collaudo nota di credito,
                # lotto 6034): il DB aveva scritto la sua riga con tutto —
                # «Non si puo' numerare il documento 15353: la fattura che
                # rettifica non e' ancora numerata (documento 835)» — e a video
                # non arrivava niente. In cascata fallivano anche il marcatore
                # di errore del lotto (`_mark_lotto_error_safely`) e il
                # passaggio di stato a ERRORE: il lotto restava COMPLETATO,
                # cioe' raccontava il contrario di quello che era successo.
                #
                # Con il savepoint, `ROLLBACK TO SAVEPOINT` riporta la
                # transazione in stato utilizzabile: l'errore resta, ma si puo'
                # ancora scrivere. E' la stessa disciplina del BB `run_fan_out`
                # (`isola_in_transazione=True`), che qui non si puo' riusare
                # perche' quello raccoglie tutti gli esiti e questo giro e'
                # FAIL-FAST: si ferma al primo che cade.
                #
                # ⚠️ Non cambia cosa viene scritto: il rilancio propaga e la
                # transazione dello step viene comunque annullata a monte. Il
                # savepoint serve alla LEGGIBILITA' del fallimento, non a
                # salvarne il lavoro.
                with transaction.atomic():
                    action(fattura_id)
            except ServiceError as exc:
                self._log_fattura_task_error(
                    task=task,
                    lotto_id=lotto_id,
                    fattura_id=fattura_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    code=exc.code,
                    detail=exc.detail or str(exc),
                )
                raise
            except Exception as exc:
                # ⭐ IL CODICE DEL DATABASE NON SI PERDE QUI. E' lo stesso
                # difetto gia' corretto in `_fail_task_run_safely` per il
                # diario dei task run (vedi il suo commento), e restava aperto
                # sulla strada che l'OPERATORE vede: un task che delega a una
                # madre DB solleva un `DatabaseError` che porta il suo codice di
                # dominio nel campo strutturato, e appiattirlo su
                # `E_TASK_FATTURA` sostituisce una frase che dice cosa fare con
                # una che dice solo «errore».
                # 🔴 Misurato sul caso che l'ha fatto emergere (nota di credito,
                # 2026-08-21): `E_FATTURA_RETTIFICATA_SENZA_NUMERO` — «numera
                # prima la fattura NNN» — arrivava a video come «Errore su
                # singola fattura durante task pipeline». La guardia nuova del
                # DB c'era e funzionava; era illeggibile.
                # ⚠️ Vale per OGNI task per-fattura, non solo per la
                # numerazione: scadenze, snapshot indirizzi e proiezione
                # rettifiche passano tutti di qui.
                # Letto UNA volta: la stessa risposta decide codice, messaggio
                # e `log_to_db` — tre letture separate dello stesso fatto sono
                # tre punti in cui divergere per errore.
                # ⭐ UNA lettura sola (BB `diagnostica_db`, 2026-08-24): prima
                # erano tre chiamate separate sullo stesso fatto, piu' un quarto
                # `db_diag` qui sotto — e il campo da correggere e il bersaglio
                # non li leggeva nessuno.
                diag_dominio = diagnostica_db(exc)
                codice_strutturato = diag_dominio.codice_strutturato
                code = diag_dominio.codice or "E_TASK_FATTURA"
                # `message_primary` e' il solo RAISE, senza lo stack PL/pgSQL:
                # e' cio' che si mostra. Senza codice di dominio non c'e' niente
                # da mostrare di meglio della frase generica — un `str(exc)`
                # tecnico a video non aiuterebbe nessuno.
                message = (
                    (diag_dominio.messaggio if diag_dominio.codice else None)
                    or "Errore su singola fattura durante task pipeline."
                )
                self._log_fattura_task_error(
                    task=task,
                    lotto_id=lotto_id,
                    fattura_id=fattura_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    code=code,
                    detail=str(exc),
                )
                # ⭐ IL BERSAGLIO PASSA DI QUI, ed e' la ragione per cui questo
                # punto conta piu' degli altri tre: il messaggio pilota del
                # cantiere — `E_FATTURA_RETTIFICATA_SENZA_NUMERO`, «numera prima
                # il documento 820» — nasce dentro un task per-fattura, quindi
                # e' QUESTA la strada che deve portarlo. Insieme al bersaglio
                # passano il campo da correggere e la soluzione a catalogo, che
                # da qui non erano mai usciti.
                ErrorManager.raise_error(
                    code=code,
                    message=message,
                    hint=diag_dominio.hint,
                    fields=diag_dominio.fields,
                    targets=diag_dominio.bersagli or None,
                    detail=f"Task {task} fallito su fattura_id={fattura_id}: {exc}",
                    context={
                        "lotto_id": lotto_id,
                        "fattura_id": fattura_id,
                        "stato_doc_fiscale_id": stato_doc_fiscale_id,
                        "task": task,
                    },
                    function_name="vendite.pipeline_step_executor._run_per_fattura_task",
                    # ⛔ Niente doppia riga nel diario: quando il codice arriva
                    # dal campo strutturato, `script.fn_log_and_raise_error` ha
                    # gia' scritto la sua (decisione DB+BE del 2026-08-19, vedi
                    # `ErrorManager.raise_from_database_error`). Il ripiego
                    # testuale e gli errori Python la riga non ce l'hanno.
                    log_to_db=codice_strutturato is None,
                    cause=exc,
                )

    # Scopo: Scrive un errore task a livello fattura con metadati di contesto pipeline.
    def _log_fattura_task_error(
        self,
        *,
        task: str,
        lotto_id: int,
        fattura_id: int,
        stato_doc_fiscale_id: int,
        code: str,
        detail: str,
    ) -> None:
        self.error_logger.log_error(
            scope="FATTURA",
            severity="C",
            code=code,
            message=f"Errore task {task} su fattura {fattura_id}",
            detail=detail,
            lotto_id=lotto_id,
            fattura_id=fattura_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            context={"task": task},
            function_name="vendite.pipeline_step_executor._run_per_fattura_task",
        )

    # Scopo: Applica validazione task e gate dry-run prima di eseguire l'azione
    #        reale. Ritorna il risultato dell'azione (None in dry-run): serve
    #        agli handler che leggono i contatori della funzione DB (es.
    #        `failed_rows` dello snapshot indirizzi, D-Q p.3).
    def _run_validated_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        dry_run: bool,
        action: Any,
    ) -> Any:
        self._validate_task_function_name(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
        )
        if dry_run:
            return None
        return action()

    # Scopo: Seleziona e opzionalmente locka le attivita fatturabili eleggibili per il lotto.
    def _handle_select_attivita_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_select_attivita_task(
                context=context,
                params=params,
            ),
        )

    # Scopo: Genera le righe fattura per il lotto usando il servizio di dominio.
    def _handle_generate_fatture_righe_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.fatture_righe_service.generate_fatture_righe(
                lotto_id,
                dry_run=dry_run,
            ),
        )

    # Scopo: Numera fiscalmente le fatture del lotto (idempotente, errori per-fattura).
    # L'allineamento dello stato documentale (es. → DEFINITIVA/8) NON e' piu' qui: e'
    # centralizzato nella finalizzazione di step del runner (sync per-step parametrico).
    def _handle_numera_fatture_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Solo numerazione: il sync stato fatture allo stato dello step lo esegue ora
        # _execute_pipeline_step (runner) dopo i task. Cosi' la fattura passa per EMESSA(2)
        # prima della numerazione, evitando il salto 1→8 vietato dalla matrice transizioni.
        def _action() -> None:
            # ⭐ L'ORDINE QUI E' UN REQUISITO, NON UNA COMODITA' (DB 2026-08-21,
            # brief note credito §44.2). Dal 2026-08-21
            # `fn_numera_fattura_opz_emessa` RIFIUTA
            # (`E_FATTURA_RETTIFICATA_SENZA_NUMERO`) di numerare un documento le
            # cui righe rettificano righe di una fattura ancora senza numero: una
            # nota di credito deve poter citare numero e data del documento
            # corretto nel blocco `DatiFattureCollegate` della TD04. Il giro e'
            # FAIL-FAST per fattura, quindi una nota incontrata prima della sua
            # fattura fermerebbe l'INTERO step.
            #
            # L'id crescente E' l'ordine di dipendenza, e non per caso: perche'
            # un accredito sia possibile la merce dev'essere gia' stata
            # fatturata, quindi la fattura rettificata nasce SEMPRE prima della
            # nota che la corregge.
            #
            # ⚠️ Il `sorted` non ripete l'`ORDER BY` del repository: lo rende
            # indipendente da esso. Quella query ha due chiamanti e il suo
            # ordinamento e' li' per la stabilita' del risultato — chi un giorno
            # lo cambiasse per un'altra ragione non ha modo di sapere che qui
            # dentro ci si appoggia, e il guasto sarebbe uno step che si ferma a
            # meta' lotto con un codice che parla d'altro.
            #
            # ⛔ Il caso CROSS-LOTTO non e' coperto da nessun ordinamento e non
            # deve esserlo: se la fattura rettificata sta in un lotto ancora in
            # bozza, il rifiuto della madre DB e' la risposta giusta.
            fattura_ids = sorted(self.repository.list_fatture_by_lotto(lotto_id))
            self._run_per_fattura_task(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                task=task,
                fattura_ids=fattura_ids,
                action=self.repository.numera_fattura_opz_emessa,
            )

        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=_action,
        )

    # Scopo: Genera o aggiorna le source fondi per tutte le fatture del lotto.
    def _handle_genera_fondi_source_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Genera/aggiorna source fondi su tutte le fatture del lotto.
        tipo_fondo = str(params.get("tipo_fondo_codice_interno") or "F_F_ADD_ACC")
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_genera_fondi_source_lotto_task(
                lotto_id=lotto_id,
                tipo_fondo_codice_interno=tipo_fondo,
            ),
        )

    # Scopo: Applica i fondi source alle fatture del lotto secondo il tipo fondo configurato.
    def _handle_applica_fondi_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Applica i fondi source alle fatture del lotto.
        tipo_fondo = str(params.get("tipo_fondo_codice_interno") or "F_F_ADD_ACC")
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_applica_fondi_lotto_task(
                lotto_id=lotto_id,
                tipo_fondo_codice_interno=tipo_fondo,
            ),
        )

    # Scopo: Ricalcola i riepiloghi IVA del lotto applicando batch size configurabile.
    def _handle_ricalcola_iva_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Ricalcolo IVA lotto; include aggiornamento totali testata.
        batch_size_raw = params.get("batch_size")
        batch_size = int(batch_size_raw) if batch_size_raw is not None else 1000
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_ricalcola_iva_lotto_task(
                lotto_id=lotto_id,
                batch_size=batch_size,
            ),
        )

    # Scopo: Prepara payload SDI del lotto con parametri stato/tentativo normalizzati.
    def _handle_prepare_sdi_payload_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Preparazione dataset SDI e apertura tentativi per le fatture del lotto.
        stato_sdi_codice_interno = str(params.get("stato_sdi_codice_interno") or "DA_INVIARE")
        force_new_tentativo = optional_bool(params, "force_new_tentativo", default=False)
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_prepare_sdi_payload_lotto_task(
                lotto_id=lotto_id,
                stato_sdi_codice_interno=stato_sdi_codice_interno,
                force_new_tentativo=force_new_tentativo,
            ),
        )

    # Scopo: Chiude operativamente il lotto impostando lo stato operativo a CHIUSO.
    def _handle_close_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Chiusura operativa lotto: stato_operativo=CHIUSO.
        def _action() -> None:
            if not self.repository.is_stato_doc_chiude_lotto(stato_doc_fiscale_id):
                return
            self.repository.close_lotto_operativo(lotto_id)

        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=_action,
        )

    # Scopo: Task stampa dello step DEFINITIVA (C-2c, outbox D-7/B-1): ADATTATORE
    #        STUPIDO che ACCODA i documenti del lotto nella coda stampa e ritorna
    #        subito — one-liner `SELECT vendite.fn_accoda_stampe_lotto(lotto_id)`.
    #        NESSUN render qui (invariante I-4b: lo step e' una transazione
    #        atomica col lock del registro fiscale tenuto — l'I/O di rendering
    #        vive nel worker drainer, fuori transazione). Ri-eseguibile:
    #        l'accodamento e' idempotente (ex_fatture_stampa_coda_vivo).
    #        Il tipo di documento non lo passa: il task non lo conosce, e la
    #        risoluzione lo deduce al drenaggio (C-1).
    def _handle_stampa_documenti_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        def _action() -> None:
            accodate = self.repository.accoda_stampe_lotto(lotto_id)
            logging.getLogger(__name__).info(
                "vendite.pipeline.stampa_documenti_lotto accodate=%s lotto_id=%s",
                accodate, lotto_id,
            )

        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=_action,
        )

    # Scopo: Task di ROLLBACK `reset_lotto_draft`: annulla il lotto in DRAFT.
    #        ⚠️ Il nome dell'handler segue il `task_code` (immutabile, vive nel
    #        seed CSV dei `rollback`), non la funzione SQL — che dopo D-L si
    #        chiama `fn_annulla_lotto_da_draft` perche' e' un annullamento e
    #        non un ritorno in bozza.
    def _handle_reset_lotto_draft_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Reset tecnico completo del lotto massivo in bozza.
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.annulla_lotto_da_draft(lotto_id),
        )

    # Scopo: Pull commesse → attivita fatturabili (step 0 pipeline fatturazione).
    #        Isola gli errori per commessa (savepoint): un fallimento su una
    #        commessa non blocca le altre.
    #        Esito a TRE stati, non due (D-Q p.3, allineato a snapshot indirizzi
    #        e genera scadenze):
    #          - nessuna commessa fallita  → `None` → task_run COMPLETATO;
    #          - alcune fallite, altre no  → `TaskEsitoParziale` → task_run
    #            ERRORE **senza sollevare**: le commesse emesse restano, lo step
    #            prosegue, e al rilancio il resolver da' RESUME invece di SKIP —
    #            cioe' le commesse rimaste indietro vengono davvero ritentate.
    #            ⚠️ Prima del 2026-08-09 questo caso chiudeva in COMPLETATO: il
    #            rilancio le SALTAVA per sempre, in silenzio. Era il difetto che
    #            questo handler condivideva coi due gemelli prima che loro lo
    #            correggessero.
    #          - tutte fallite             → `TaskEsitoParziale` come sopra, dal
    #            2026-09-07 (P-5). ⛔ Prima SOLLEVAVA, e il rollback si portava
    #            via i segni sui documenti caduti: il caso peggiore era l'unico
    #            senza traccia. A fermare la catena non serve l'eccezione — ci
    #            pensa il blocco per segnalazioni critiche al giro successivo.
    def _handle_pull_attivita_da_commessa_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> TaskEsitoParziale | TaskEsitoOk | None:
        self._validate_task_function_name(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
        )

        # ⛔ SENZA L'IDENTITA' DEL GIRO SI FERMA QUI, e non e' difensivo.
        # L'identita' la consumano DUE cancelli, e per tutti e due il difetto
        # e' lo stesso: silenzioso.
        #   - la DISCOVERY (`fn_list_commesse_emittibili`, `20260912-15`): senza
        #     identita' scarta i PROPRI documenti — al rilancio di un pull
        #     fallito risultano `TRATTENUTA` dal lotto che sta riprovando — e
        #     il giro visita zero commesse, chiude `COMPLETATO` e ritira le
        #     proprie segnalazioni senza aver emesso niente (LTF-0010972,
        #     2026-09-12, brief `brief-db-rilancio-step-non-rivede-le-proprie-
        #     commesse`);
        #   - l'EMIT: firmerebbe NULL, `fn_select_attivita_fatturabili`
        #     filtrerebbe su un marchio che nessuna riga porta, e il lotto
        #     nascerebbe VUOTO senza un errore.
        # In entrambi i casi il risultato e' indistinguibile, a video, da un
        # mese senza lavoro. Fra un giro che non parte e un giro che non emette
        # niente in silenzio, il primo e' l'unico recuperabile.
        # ⚠️ Il guard sta PRIMA della discovery e PRIMA del dry-run — fino al
        # 2026-09-12 stava dopo entrambi. Con la discovery che legge l'identita'
        # un guard a valle non fermerebbe niente: la discovery chiamata con NULL
        # non fallisce, risponde a un'ALTRA domanda («cosa vedrebbe un chiamante
        # fuori pipeline»), e un dry-run senza identita' conterebbe MENO
        # commesse del giro vero.
        # ℹ️ `lock_batch_id` e' NOT NULL sulla tabella: se qui e' None il
        # contesto non e' stato caricato, che e' un difetto di programma e non
        # un dato mancante. Codice riusato (`E_PIPELINE_SCOPE_INCOMPLETE`, gia'
        # a policy DATO_ERRATO) invece di uno nuovo: dice esattamente questo.
        if not context.lock_batch_id:
            ErrorManager.raise_error(
                code="E_PIPELINE_SCOPE_INCOMPLETE",
                message="Contesto lotto senza identita' del giro.",
                detail=(
                    "lock_batch_id assente sul lotto "
                    f"{lotto_id}: la discovery scarterebbe i propri documenti, "
                    "il pull non potrebbe firmare le righe e il giro "
                    "emetterebbe zero fatture senza errore."
                ),
                context={"lotto_id": lotto_id, "task": task},
                function_name=(
                    "vendite.pipeline_step_executor."
                    "_handle_pull_attivita_da_commessa_task"
                ),
                log_to_db=True,
            )

        commessa_ids = self.commesse_repository.list_commesse_emittibili(
            competenza_mese=context.competenza_mese,
            utility_id=context.utility_id,
            billing_account_id=context.billing_account_id,
            emittente_soggetto_ruolo_id=context.emittente_soggetto_ruolo_id,
            # Corsia: filtro propagato dal lotto (meta), non re-derivato qui dal
            # tipo_lotto (separazione immediata/differita decisa dal driver).
            fatturazione_immediata=context.fatturazione_immediata,
            # Perimetro mirato: visita solo le commesse che contengono almeno
            # uno dei gruppi richiesti (persistito sul lotto, non passato qui
            # dal chiamante — vedi LottoContext.gruppi).
            gruppi=context.gruppi,
            # ⭐ LA STESSA IDENTITA' CHE RICEVE L'EMIT, qui sotto: UN dato a DUE
            # funzioni (D1). Con l'identita' la discovery vede i PROPRI
            # documenti trattenuti come `PRONTA` e visita la commessa; senza,
            # l'auto-esclusione dell'emit restava corretta e irraggiungibile,
            # perche' chi l'avrebbe chiamata non arrivava mai a farlo.
            emit_batch_id=context.lock_batch_id,
        )
        if dry_run:
            # ⚠️ Il ritorno anticipato precede il giro: in dry-run non esiste
            # ne' esito parziale ne' errore, perche' non e' stato tentato nulla.
            # (Seconda cintura: `_run_task` esce gia' prima di invocare questo
            # handler — vedi il test dedicato.)
            return None

        # Isolamento per commessa: il BB apre un savepoint per ogni emit, cattura
        # l'errore e prosegue. Il diario per-commessa (log di lotto) e' l'unica
        # parte di dominio, e sta nel run logger.
        esito = run_fan_out(
            commessa_ids,
            lambda commessa_id: self.commesse_repository.emit_attivita_fatturabili(
                commessa_id,
                dry_run=dry_run,
                # Stesso perimetro anche DENTRO la commessa: senza, le righe
                # degli altri gruppi passerebbero a EMESSA pur non essendo
                # state chieste (A2.3 del brief DB).
                gruppi=context.gruppi,
                # ⭐ IL PERIMETRO SI CONSEGNA (D1+D2): il pull firma con
                # l'identita' di QUESTO giro le righe che accetta, e la select
                # a valle fatturera' solo quelle. Senza questa riga il marchio
                # resta NULL, `fn_select_attivita_fatturabili` non trova nulla,
                # e il giro emette zero fatture SENZA errore — il caso che il
                # presidio `dbops.vw_af_senza_giro` esiste per rendere visibile.
                emit_batch_id=context.lock_batch_id,
            ),
            run_logger=_PullCommesseRunLogger(
                error_logger=self.error_logger,
                task=task,
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                repository=self.repository,
            ),
        )

        # ⭐ L'ESITO SI APPENDE AI DOCUMENTI, e si fa QUI: prima dei rami, non
        #    dentro ciascuno. Le uscite sono DUE — tutto riuscito e con errori —
        #    e la marcatura serve in entrambe: scriverla nei rami vorrebbe dire
        #    scriverla due volte e dimenticarla una.
        # ⚠️ E il `dry_run` non arriva mai fin qui: esce molto prima con `None`.
        #
        # ✅ IL LIMITE DEL 2026-09-06 NON C'E' PIU', e sono cadute due cose
        #    insieme. Allora le uscite erano TRE e la terza SOLLEVAVA: il
        #    `transaction.atomic()` che `run_pipeline` tiene attorno al ciclo
        #    degli step faceva rollback e si portava via i segni appena scritti
        #    — misurato, non supposto. ⇒ Il ramo che sollevava e' stato tolto
        #    (P-5), quindi non c'e' piu' niente che annulli questa scrittura.
        # ⭐ E la casa dell'esito e' cambiata sotto (DB, 2026-09-07): la riga si
        #    CREA in `vendite.fatturazione_lotti_esiti` invece di aggiornare una
        #    colonna del perimetro. Percio' la stessa identica chiamata funziona
        #    anche sui giri di massa, che un perimetro non lo dichiarano: prima
        #    li' tornava `0` e il documento restava muto.
        self._marca_esito_gruppi(lotto_id, commessa_ids, esito)

        # ⭐ Giro riuscito: il diario porta comunque i contatori. La promessa
        # del perimetro consegnato dev'essere verificabile anche quando regge —
        # e «ok: 0 su 3» e' esattamente il segnale che un marchio non arrivato
        # produrrebbe, che senza contatori resterebbe un COMPLETATO muto.
        if not esito.errori:
            return TaskEsitoOk(
                meta={
                    "task": task,
                    "totale": esito.totale,
                    "ok": esito.ok,
                    "falliti": esito.falliti,
                }
            )

        # ⭐ UN RAMO SOLO PER TUTTI I FALLIMENTI (P-5, decisione di Tid
        #    2026-09-06: «trattiamoli tutti come quando ne capita 2 su 3»).
        #
        # 🔴 QUI C'ERA UN `raise E_PULL_COMMESSA_ALL_FAILED` quando fallivano
        #    TUTTE, e sollevare faceva rollback dell'intero step: si portava via
        #    anche i segni appena scritti sui documenti caduti. Il caso PEGGIORE
        #    era l'unico che non lasciava traccia — il paradosso classico:
        #    funziona quando va male a meta' e tace quando va male del tutto.
        #    ⚠️ Ed era gia' il difetto diagnosticato due righe sopra
        #    `TaskEsitoParziale`, un ramo piu' in la'.
        #
        # ⭐ La differenza fra i due casi era UN NUMERO, e adesso non c'e' piu'
        #    nessun ramo: il comportamento del «tutte fallite» non va dimostrato
        #    a parte, perche' e' lo STESSO CODICE del parziale, che e' in
        #    esercizio da agosto.
        #
        # ⛔ E LA CATENA SI FERMA LO STESSO — questa era la domanda vera, non il
        #    rollback. Il passo scrive una segnalazione CRITICA per ogni commessa
        #    caduta *prima* di arrivare qui (`_PullCommesseRunLogger.item_failed`,
        #    `severity="C"`), quindi al giro successivo `evaluate_lotto_status`
        #    risponde `blocks_next_step` e `run_pipeline` rifiuta di avanzare con
        #    `E_PIPELINE_LOTTO_CRITICAL`; il driver esce con `BLOCCATO_CRITICITA`
        #    e il lotto va in ERRORE. Fermarsi e strappare gli appunti erano due
        #    cose che faceva lo stesso gesto: adesso si ferma TENENDO.
        # ⚠️ Il rilancio dello STESSO step resta ammesso: e' la via d'uscita —
        #    correggo la commessa, rieseguo, il task ritira le sue segnalazioni.
        #
        # 📌 `E_PULL_COMMESSA_ALL_FAILED` non lo solleva piu' nessuno: la
        #    deprecazione a catalogo (`obsoleto_dal`) e' P-6, e tocca al DB.
        #
        # Rifiuto PARZIALE: il giro e' finito, alcune commesse no.
        # Codice riusato e non sintetico: `E_PULL_COMMESSA` e' gia' il motivo
        # per-commessa scritto qui sopra sui log di lotto — e' il criterio dello
        # snapshot indirizzi, che riusa `E_INDIRIZZO_FATTURA_MANCANTE` invece di
        # inventare un codice che nessuno saprebbe interpretare.
        return TaskEsitoParziale(
            error_code="E_PULL_COMMESSA",
            error_message=(
                f"Pull attivita' completato con {esito.falliti} commesse su "
                f"{esito.totale} in errore (dettaglio sui log di lotto)."
            ),
            meta={
                "task": task,
                "totale": esito.totale,
                "ok": esito.ok,
                "falliti": esito.falliti,
                # Troncata come nel raise all-fail: il meta e' una traccia per
                # il cockpit, il dettaglio completo sta sui log di lotto.
                "commesse_fallite": [e.item for e in esito.errori][:5],
            },
        )

    # Scopo: Appende a ogni gruppo del lotto l'esito della sua commessa —
    #        `ERRORE` col motivo per quelle fallite, `COMPLETED` per le altre.
    #
    # ⭐ PERCHE' ANCHE LE RIUSCITE. Senza, un gruppo andato bene resta a `NULL` e
    #    non si distingue da uno mai lavorato: la colonna direbbe solo dove e'
    #    andata male, e non si potrebbe MAI dire «il lotto e' a posto».
    # ⚠️ Il valore di ritorno della funzione si GUARDA: `0` vuol dire che
    #    l'esito non e' stato appeso a nessun documento — il lotto continuerebbe
    #    a raccontare un errore su qualcosa che non mostra. Non solleva (sta
    #    annotando un fallimento gia' avvenuto, e un errore su di se' coprirebbe
    #    quello vero): lo si scrive nel log, che e' il solo posto in cui quel
    #    silenzio si vede.
    # ⛔ Nessun `UPDATE` diretto: quale riga marcare, avendo in mano una commessa
    #    e non un gruppo, e' l'unica regola non banale del cantiere e sta nella
    #    funzione DB. Rifarla qui sarebbe la seconda sede.
    def _marca_esito_gruppi(self, lotto_id: int, commessa_ids, esito) -> None:
        messaggi = {e.item: _messaggio_pull(e.item, e.messaggio) for e in esito.errori}
        for commessa_id in commessa_ids:
            fallita = commessa_id in messaggi
            # ⛔ LO STATO SI DECIDE UNA VOLTA SOLA. La stessa ternaria era
            #    scritta DUE volte — qui e nel log poco sotto — e una copia che
            #    esiste solo per raccontare l'altra e' la forma in cui un
            #    verbale finisce a dire una cosa diversa da quella accaduta.
            # ⚠️ E i due valori vengono dallo SPECCHIO del CHECK di tabella
            #    (`STATI_ESECUZIONE_LOTTO`), non da stringhe scritte a mano:
            #    un typo qui non fallisce, fa scrivere un esito che il vincolo
            #    rifiuta — dentro un gestore d'eccezione, cioe' proprio dove
            #    l'errore vero verrebbe coperto.
            stato = STATO_ESECUZIONE_ERRORE if fallita else STATO_ESECUZIONE_COMPLETED
            esito_marcatura = self.repository.segna_esito_gruppo_lotto(
                lotto_id,
                stato,
                commessa_id=commessa_id,
                errore_codice="E_PULL_COMMESSA" if fallita else None,
                errore_messaggio=messaggi.get(commessa_id),
            )
            # ⭐ LO ZERO DEL MARCATORE AVEVA TRE CAUSE E NE RACCONTAVA UNA, e
            #    dal changeSet `20260909-20` le distingue. L'avviso vale per due
            #    di esse, e la terza e' il caso NORMALE del verbo «togli dal
            #    giro»:
            #      · tutto a zero        → nessun documento appeso a questa
            #        commessa: e' il difetto che l'avviso e' nato per dire;
            #      · `fuori_perimetro>0` → i documenti ci sono ma non sono di
            #        questo lotto — sospetto, e c'era gia' prima di questo giro;
            #      · `usciti>0`          → sono stati tolti dal giro, apposta.
            #
            # 🔴 SENZA LA DISTINZIONE L'AVVISO DIVENTAVA RUMORE su un caso
            #    legittimo — e un avviso che suona quando va tutto bene e' un
            #    avviso che si smette di leggere, cioe' peggio di nessun avviso.
            #    ⚠️ E' la ragione per cui i tre conteggi sono stati chiesti
            #    NELLO STESSO giro del filtro, non dopo
            #    (`brief-db-il-marcatore-scrive-su-un-documento-uscito` §4.1).
            # ⚠️ I tre si NOMINANO invece di sommare `.values()`: quel dict e'
            #    un `EsitoMarcaturaGruppi`, e il giorno che guadagna un campo
            #    che conteggio non e' — una bandiera, un messaggio — `any()` lo
            #    leggerebbe insieme agli altri e l'avviso cambierebbe
            #    significato senza che niente fallisca.
            muto = not (
                esito_marcatura["marcati"]
                or esito_marcatura["usciti"]
                or esito_marcatura["fuori_perimetro"]
            )
            if muto or esito_marcatura["fuori_perimetro"]:
                # ⚠️ `logging.getLogger(__name__)` in linea: e' l'idioma di
                #    questo modulo, che non tiene un logger di modulo.
                logging.getLogger(__name__).warning(
                    "pull_commesse.esito_non_appeso lotto_id=%s commessa_id=%s "
                    "stato=%s marcati=%s usciti=%s fuori_perimetro=%s — il "
                    "lotto raccontera' un esito su un documento che non mostra",
                    lotto_id, commessa_id, stato,
                    esito_marcatura["marcati"], esito_marcatura["usciti"],
                    esito_marcatura["fuori_perimetro"],
                )

    # Scopo: Task `snapshot_indirizzi_lotto` (step DRAFT, piano DB satelliti
    #        Fase 2): congela i satelliti di intestazione delle fatture del
    #        lotto — indirizzi in `vendite.fatture_indirizzi` e intestazione
    #        fiscale delle due parti in `fatture.emittente_snapshot` /
    #        `cliente_snapshot` — via `fn_snapshot_fattura_lotto`.
    #        La funzione DB applica D-Q da sola: la fattura senza indirizzo
    #        `FATT` viene marcata 'C' su fatture_log (→ `stato_esecuzione`
    #        ERRORE sulla ponte) e le ALTRE ricevono il loro snapshot — il giro
    #        non si ferma e questo handler NON solleva. Se pero' `failed_rows`
    #        e' > 0 il task_run va chiuso in ERRORE (`TaskEsitoParziale`):
    #        altrimenti al rilancio dello step il resolver darebbe SKIP e la
    #        correzione dell'anagrafica non verrebbe mai riletta (D-Q p.3).
    def _handle_snapshot_indirizzi_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> TaskEsitoParziale | None:
        batch_size_raw = params.get("batch_size")
        batch_size = int(batch_size_raw) if batch_size_raw is not None else 1000
        esito = self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_snapshot_indirizzi_lotto_task(
                lotto_id=lotto_id, batch_size=batch_size,
            ),
        )
        if esito is None:  # dry-run: nessuna esecuzione, nessun esito.
            return None
        failed_rows = int(esito.get("failed_rows") or 0)
        if failed_rows > 0:
            # Codice gia' seedato dal team DB (Fase 1.3): e' il motivo dominante
            # reale del fallimento per-fattura, non un codice sintetico nuovo.
            return TaskEsitoParziale(
                error_code="E_INDIRIZZO_FATTURA_MANCANTE",
                error_message=(
                    f"Snapshot indirizzi completato con {failed_rows} fatture "
                    "in errore (dettaglio sui log fattura)."
                ),
                meta={"task": task, **esito},
            )
        return None

    # Scopo: Task `genera_scadenze_lotto` (step EMESSA, piano DB satelliti
    #        Fase 4): genera il piano rate delle fatture del lotto via
    #        `fn_genera_scadenze_lotto`.
    #        Perimetro: le fatture lavorabili del lotto; il DB applica D-Q da
    #        solo (la fattura difettosa e' marcata 'C' su fatture_log e le
    #        ALTRE ricevono le loro rate), quindi questo handler NON solleva.
    #        Risultato atteso: `failed_rows == 0` → task_run COMPLETATO;
    #        `failed_rows > 0` → `TaskEsitoParziale`, cioe' task_run ERRORE
    #        senza raise — con COMPLETATO il resolver darebbe SKIP al rilancio
    #        e la correzione non verrebbe mai riletta (D-Q p.3), con un raise
    #        il rollback cancellerebbe anche le rate delle fatture sane.
    #        ⚠️ Il codice d'errore NON e' uno dei quattro `E_SCADENZE_*` di
    #        dominio: le cause per-fattura sono quattro (termine mancante,
    #        base non pronta, termine inconciliabile, fattura bloccata) e
    #        nessuna domina — sceglierne una qui farebbe raccontare al cockpit
    #        una diagnosi che il wrapper non ha misurato. Il dettaglio vero sta
    #        sui log fattura, dove il DB scrive il messaggio originale.
    def _handle_genera_scadenze_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> TaskEsitoParziale | None:
        batch_size_raw = params.get("batch_size")
        batch_size = int(batch_size_raw) if batch_size_raw is not None else 1000
        esito = self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_genera_scadenze_lotto_task(
                lotto_id=lotto_id, batch_size=batch_size,
            ),
        )
        if esito is None:  # dry-run: nessuna esecuzione, nessun esito.
            return None
        failed_rows = int(esito.get("failed_rows") or 0)
        if failed_rows > 0:
            return TaskEsitoParziale(
                error_code="E_SCADENZE_LOTTO_PARZIALE",
                error_message=(
                    f"Generazione scadenze completata con {failed_rows} fatture "
                    "in errore (dettaglio sui log fattura)."
                ),
                meta={"task": task, **esito},
            )
        return None

    # Scopo: Task `popola_fatture_rettifiche` (step DEFINITIVA, N10 + BE-8):
    #        proietta il legame documento-a-documento delle note di credito
    #        chiamando `fn_popola_fatture_rettifiche` per ogni fattura del lotto.
    #        La proiezione e' idempotente e non cancella mai: le righe sono il
    #        FATTO, `vendite.fatture_rettifiche` e' il loro INDICE.
    #        Perimetro: tutte le fatture del lotto — una fattura senza righe di
    #        rettifica aggiunge zero coppie, non e' un caso da filtrare a monte.
    # ⚠️ FAIL-FAST per fattura (`_run_per_fattura_task`), NON esito parziale — ed
    #    e' la scelta opposta a quella di `genera_scadenze_lotto` e
    #    `snapshot_indirizzi_lotto`, quindi va motivata: quei due non hanno
    #    nessuno a valle nello stesso step, qui invece `stampa_documenti_lotto`
    #    viene subito dopo e CONSUMA questo legame (`DatiFattureCollegate` di una
    #    TD04 vuole numero e data del documento rettificato). Proseguire con una
    #    coppia mancante non lascerebbe una riga da rilavorare: stamperebbe un
    #    documento fiscale incompleto. Meglio fermare lo step — le fatture sono
    #    gia' numerate e la proiezione delle sane e' committata, quindi il
    #    rilancio (task_policy `RESUME_TASK`) riprende da qui e l'idempotenza
    #    rende innocuo il secondo giro.
    # Scopo: Task `consuma_plafond_lotto` (step DEFINITIVA, `I4` / `P5`):
    #        consuma il plafond dei titoli IVA sulle fatture del lotto e spezza
    #        le righe che il titolo copre solo in parte.
    #
    # ⛔ VA PRIMA DI `numera_fatture`, e non e' una preferenza: li' la fattura e'
    #    ancora `EMESSA`, e il guard di congelamento legge lo stato VIVO. Dopo,
    #    la spezzatura verrebbe rifiutata. La dipendenza e' dichiarata in
    #    `_TASK_ORDER_DEPENDENCIES`, cosi' una configurazione girata si ferma
    #    PRIMA che il primo task scriva.
    #
    # ⚠️ NON e' un giro per-fattura come i suoi vicini, ed e' voluto: l'ordine
    #    fra le fatture (`data documento, numero`) e' parte del requisito, e
    #    `_run_per_fattura_task` isola gli errori per documento ma non promette
    #    niente sull'ordine. Il servizio lo impone dal repository.
    def _handle_consuma_plafond_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        def _action() -> None:
            from apps.vendite.services.plafond_fattura_service import (
                PlafondFatturaService,
            )

            esito = PlafondFatturaService(self.repository).consuma_lotto(lotto_id)
            # ⚠️ I conteggi sono l'unica traccia del giro: un lotto senza titoli
            #    IVA scrive zero movimenti, ed e' l'esito CORRETTO — senza
            #    questa riga sarebbe indistinguibile da un task che non ha
            #    lavorato affatto.
            logging.getLogger(__name__).info(
                "pipeline.consuma_plafond_lotto lotto_id=%s fatture=%s "
                "righe_spezzate=%s movimenti=%s",
                lotto_id, esito["fatture"], esito["righe_spezzate"],
                esito["movimenti"],
            )

        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=_action,
        )

    def _handle_popola_fatture_rettifiche_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        def _action() -> None:
            fattura_ids = self.repository.list_fatture_by_lotto(lotto_id)
            # Il conteggio delle coppie e' l'unica traccia del giro: la tabella
            # di proiezione non ha un log suo, e senza questa riga un lotto
            # senza note di credito (zero coppie, esito corretto) sarebbe
            # indistinguibile da un task che non ha lavorato.
            coppie = 0

            def _proietta(fattura_id: int) -> None:
                nonlocal coppie
                coppie += self.repository.popola_fatture_rettifiche(fattura_id)

            self._run_per_fattura_task(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                task=task,
                fattura_ids=fattura_ids,
                action=_proietta,
            )
            logging.getLogger(__name__).info(
                "pipeline.popola_fatture_rettifiche lotto_id=%s fatture=%s coppie=%s",
                lotto_id, len(fattura_ids), coppie,
            )

        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=_action,
        )
