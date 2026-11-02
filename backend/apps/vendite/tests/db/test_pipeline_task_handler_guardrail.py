# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL CANCELLO DEI TASK DI PIPELINE — ogni task che una pipeline VIVA
#        elenca deve avere, a valle, un handler Python che lo esegua.
#
#        PERCHE' ESISTE, e non e' un'ipotesi. Un task nasce da CINQUE pezzi
#        (vedi `docs/it/backend/vendite/manual/api_pipeline_task.md`), e due di
#        essi stanno da parti opposte: il seed DB che lo mette nel JSON
#        `processi`, e l'handler Python che lo esegue. I due si possono
#        applicare SEPARATAMENTE, ciascuno verde e corretto in se'.
#
#        Il 2026-08-18 e' successo: `popola_fatture_rettifiche` e' entrato nelle
#        pipeline 4 e 6 (step DEFINITIVA) con l'handler ancora da scrivere.
#        L'esecutore avrebbe sollevato `E_TASK_IMPLEMENTATION_NOT_FOUND`
#        severita' C — ma DOPO `numera_fatture`, cioe' a documenti gia'
#        numerati, che e' irreversibile. Nessun test lo vedeva: i test
#        dell'esecutore mockano il repository, e la configurazione vive nel
#        database.
#
#        ⚠️ SI LEGGONO GLI OGGETTI REALI. Il confronto e' fra il DATABASE (cosa
#        le pipeline chiedono) e il DIZIONARIO PYTHON vivo
#        (`PipelineStepExecutor.handler_registry`), non fra due copie di
#        comodo: uno specchio non prova che l'originale esista — ed e'
#        esattamente il modo in cui il difetto era passato.
#
#        ⚠️ RICHIEDE IL DB VERO: stessa opt-in `ZEROERP_TEST_DB_E2E=1` del
#        cancello del terzo lato (accesa in CI da `ci-validate.yaml`), stesso
#        guard sullo schema in `setUpClass`. NON SCRIVE NULLA: qui si legge
#        soltanto.
# ------------------------------------------------------------

"""Indice test previsti (tutti opt-in `ZEROERP_TEST_DB_E2E=1`).

 1) test_ogni_task_in_pipeline_ha_un_handler
       il cancello vero: un task elencato da una pipeline attiva la cui
       implementazione non e' nel registry dell'esecutore. Rosso.
 2) test_ogni_task_in_pipeline_e_a_registro
       il gradino prima: senza riga a `dbops.pipeline_task_registry` non c'e'
       nemmeno un `handler_code` da risolvere.
 3) test_ogni_task_in_pipeline_ha_una_task_policy
       senza policy il task gira CIECO: niente task_run, niente resume — un
       fallimento non lascia traccia e il rilancio non riprende.
 4) test_debito_dormiente_non_cresce
       verso 1 del registro del debito: un task a registro SENZA handler e
       fuori da ogni pipeline e' una trappola gia' armata a meta'. Uno nuovo
       va dichiarato qui (o gli si scrive l'handler).
 5) test_debito_dormiente_non_contiene_task_risolti
       verso 2: un task del registro che ha OTTENUTO il suo handler — la riga
       va tolta da qui, o il debito non cala mai.
 6) test_debito_dormiente_non_contiene_task_ritirati
       verso 3: un task del registro che non esiste piu' a catalogo — riga
       orfana.
 7) test_la_misura_non_e_degradata
       sanity. Senza, una query che smette di misurare rende il cancello
       silenziosamente verde — e un cancello verde per sottrazione e' peggio
       di nessun cancello.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock

from django.db import connection

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.services.pipeline_step_executor import (
    TASK_SENZA_HANDLER,
    PipelineStepExecutor,
)

# I task che il DATABASE elenca in una pipeline attiva, con la chiave di
# implementazione che la voce JSON dichiara (default se assente) — cioe'
# ESATTAMENTE la coppia con cui l'esecutore risolve l'handler.
# `processi` e `rollback` insieme: anche la catena di annullamento esegue task.
SQL_TASK_IN_PIPELINE = """
    SELECT DISTINCT
           p.id                                        AS pipeline_id,
           t->>'task'                                  AS task_code,
           COALESCE(t->'params'->>'implementation_key', 'default') AS impl_key
      FROM vendite.fatturazione_pipeline p,
           LATERAL jsonb_array_elements(
               COALESCE(NULLIF(p.processi::text, '')::jsonb, '[]'::jsonb)) t
     WHERE p.attivo IS TRUE
    UNION
    SELECT DISTINCT
           p.id,
           t->>'task',
           COALESCE(t->'params'->>'implementation_key', 'default')
      FROM vendite.fatturazione_pipeline p,
           LATERAL jsonb_array_elements(
               COALESCE(NULLIF(p.rollback::text, '')::jsonb, '[]'::jsonb)) t
     WHERE p.attivo IS TRUE
"""

# Il registro dei task con la loro implementazione attiva.
SQL_REGISTRO = """
    SELECT r.task_code, i.implementation_key, i.handler_code
      FROM dbops.pipeline_task_registry r
      LEFT JOIN dbops.pipeline_task_registry_impl i
             ON i.task_registry_id = r.id AND i.attivo IS TRUE
"""

SQL_POLICY = """
    SELECT pipeline_id, task_code
      FROM vendite.fatturazione_pipeline_task_policy
     WHERE attivo IS TRUE
"""

# ⚠️ REGISTRO DEL DEBITO — task a catalogo con un `handler_code` dichiarato e
# NESSUN handler Python. Oggi non sono in nessuna pipeline, quindi dormono e non
# fanno danno: sono i resti di una fase di disegno in cui l'acquisizione delle
# sorgenti era pensata come catena di task.
#
# ⛔ NON E' UNA LISTA DI ECCEZIONI: e' debito, e puo' solo CALARE. Ogni voce e'
# una trappola armata a meta' — il giorno in cui qualcuno la mette in un JSON
# `processi`, il giro muore dopo che i task precedenti hanno scritto.
# Chi ne usa uno: scriva l'handler e tolga la riga da qui. Chi lo ritira: tolga
# la riga di registro e la riga da qui.
DEBITO_TASK_SENZA_HANDLER = frozenset({
    "acquisisci_preventivi",
    "acquisisci_contratti",
    "acquisisci_ordini",
    "acquisisci_attivita_consumi",
    "normalizza_attivita",
    "valida_attivita",
    "deduplica_attivita",
})


# Scopo: le righe di una query, senza cerimonie (qui si legge soltanto).
def _righe(sql: str) -> list[tuple]:
    with connection.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


class PipelineTaskHandlerGuardrail(TestCase):
    """Il cancello fra la configurazione DB e gli handler Python."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.in_pipeline = _righe(SQL_TASK_IN_PIPELINE)
        cls.registro = _righe(SQL_REGISTRO)
        cls.policy = {(int(p), t) for p, t in _righe(SQL_POLICY)}
        # Il dizionario VIVO dell'esecutore. I mock sono solo per costruirlo
        # senza toccare il database: il registry e' un attributo di istanza.
        cls.handler_registry = PipelineStepExecutor(
            repository=MagicMock(),
            fatture_righe_service=MagicMock(),
            error_logger=MagicMock(),
        ).handler_registry
        # (task_code, implementation_key) -> handler_code
        cls.handler_code_per_task = {
            (task, impl): handler
            for task, impl, handler in cls.registro
            if impl is not None
        }
        cls.task_a_registro = {task for task, _impl, _h in cls.registro}

    # Scopo: 🔴 IL CANCELLO. Un task che una pipeline attiva elenca deve
    #        risolvere un handler presente nel registry dell'esecutore.
    def test_ogni_task_in_pipeline_ha_un_handler(self) -> None:
        mancanti = []
        for pipeline_id, task, impl in self.in_pipeline:
            if task in TASK_SENZA_HANDLER:
                continue
            handler_code = self.handler_code_per_task.get((task, impl))
            if handler_code is None or handler_code not in self.handler_registry:
                mancanti.append(
                    f"  - pipeline {pipeline_id}: {task} "
                    f"(implementation_key={impl}, handler_code={handler_code})"
                )
        if mancanti:
            self.fail(
                f"{len(mancanti)} task sono in una pipeline VIVA e non hanno un "
                "handler in PipelineStepExecutor.handler_registry:\n"
                + "\n".join(sorted(mancanti))
                + "\n\nIl prossimo giro di quello step morira' con "
                "E_TASK_IMPLEMENTATION_NOT_FOUND **dopo** che i task precedenti "
                "hanno scritto. Scrivere l'handler, oppure togliere il task dal "
                "JSON `processi`. Vedi api_pipeline_task.md §I cinque pezzi."
            )

    # Scopo: il gradino prima — senza riga di registro non c'e' nemmeno un
    #        `handler_code` da risolvere, e `get_task_handler_code` non trova
    #        niente.
    def test_ogni_task_in_pipeline_e_a_registro(self) -> None:
        orfani = sorted({
            f"pipeline {pipeline_id}: {task}"
            for pipeline_id, task, _impl in self.in_pipeline
            if task not in TASK_SENZA_HANDLER and task not in self.task_a_registro
        })
        self.assertEqual(
            orfani, [],
            "task elencati da una pipeline e assenti da "
            "dbops.pipeline_task_registry",
        )

    # Scopo: senza `task_policy` il task gira CIECO — nessun `task_run` aperto,
    #        quindi un fallimento non lascia traccia nel cockpit e il rilancio
    #        non riprende da lui (l'esecutore traccia solo se la policy esiste).
    def test_ogni_task_in_pipeline_ha_una_task_policy(self) -> None:
        senza = sorted({
            f"pipeline {pipeline_id}: {task}"
            for pipeline_id, task, _impl in self.in_pipeline
            if task not in TASK_SENZA_HANDLER
            and (int(pipeline_id), task) not in self.policy
        })
        self.assertEqual(
            senza, [],
            "task in pipeline senza riga attiva in "
            "vendite.fatturazione_pipeline_task_policy: girerebbero senza "
            "tracing ne' resume",
        )

    # Scopo: verso 1 del debito — un task a registro senza handler che nessuno
    #        ha dichiarato. E' il 22esimo, quello nuovo.
    def test_debito_dormiente_non_cresce(self) -> None:
        senza_handler = {
            task
            for (task, _impl), handler in self.handler_code_per_task.items()
            if handler not in self.handler_registry
        }
        nuovi = sorted(senza_handler - DEBITO_TASK_SENZA_HANDLER)
        self.assertEqual(
            nuovi, [],
            "task a registro con un handler_code che nessun handler Python "
            "implementa. Se serve, scrivere l'handler; se e' un segnaposto, "
            "dichiararlo in DEBITO_TASK_SENZA_HANDLER spiegando perche'.",
        )

    # Scopo: verso 2 — un task del debito che ha ottenuto il suo handler. Senza
    #        questo verso il registro puo' solo allungarsi.
    def test_debito_dormiente_non_contiene_task_risolti(self) -> None:
        risolti = sorted({
            task
            for (task, _impl), handler in self.handler_code_per_task.items()
            if task in DEBITO_TASK_SENZA_HANDLER and handler in self.handler_registry
        })
        self.assertEqual(
            risolti, [],
            "questi task hanno ora un handler: togliere la riga da "
            "DEBITO_TASK_SENZA_HANDLER",
        )

    # Scopo: verso 3 — una voce del debito che a registro non esiste piu'.
    def test_debito_dormiente_non_contiene_task_ritirati(self) -> None:
        ritirati = sorted(DEBITO_TASK_SENZA_HANDLER - self.task_a_registro)
        self.assertEqual(
            ritirati, [],
            "questi task non sono piu' a registro: togliere la riga da "
            "DEBITO_TASK_SENZA_HANDLER",
        )

    # Scopo: 🔴 sanity. Se una delle tre misure si azzera — una vista rinominata,
    #        una colonna che cambia nome, la RLS che nasconde le righe — tutti i
    #        test qui sopra diventano verdi PER SOTTRAZIONE, e il cancello smette
    #        di presidiare senza dirlo.
    def test_la_misura_non_e_degradata(self) -> None:
        self.assertGreaterEqual(
            len(self.in_pipeline), 12,
            "le pipeline attive elencano meno task del previsto: la misura e' "
            "degradata, non il sistema migliorato",
        )
        self.assertGreaterEqual(len(self.task_a_registro), 20, "registro task vuoto o dimezzato")
        self.assertGreaterEqual(len(self.handler_registry), 14, "handler_registry dimezzato")
        self.assertGreaterEqual(len(self.policy), 20, "task_policy vuota o dimezzata")
