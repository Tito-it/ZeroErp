# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La GIUNTURA fra le tre righe di catalogo di «Esegui ora»
#        (brief-db-avvio-manuale-di-un-processo §4) e il backend che le legge —
#        su database provvisto, in transazione ritirata (piano §5.4).
# Note: ⭐ E' il test che ne' i pgTAP ne' gli unit vedono: il pgTAP fissa le
#        righe come le legge il DATABASE, gli unit fissano cio' che il backend
#        DECIDE, e nessuno dei due prova che il `handler_code` del CSV sia la
#        stringa con cui `CoreConfig.ready()` registra l'handler. Un refuso da
#        una parte sola non fallisce da nessuna parte: il drenatore trova un
#        lavoro e non trova chi lo esegue.
#        ⚠️ L'accodamento vero si prova nei DUE stati del tipo, e quello che
#        vale dipende da come e' seminato ADESSO: a tipo spento il rifiuto
#        `E_JOB_TYPE_NON_ATTIVO` e' il cancello voluto (e il caso «acceso» si
#        DICHIARA con `skipTest`, non si tace); a tipo acceso l'id e la dedup
#        sulla stessa chiave (e il caso «spento» e' storia). Cosi' il test non
#        va riscritto il giorno dell'accensione: cambia da solo il ramo che gira.
#
# Indice test (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`):
#   1. il tipo ESEGUI_PROCESSO ha l'handler_code con cui il backend registra,
#      run_as OPERATORE, max_tentativi 1, sotto il processo avvio_manuale
#   2. il processo avvio_manuale e' MANUTENZIONE/CODA, senza contratto
#   3. l'azione processo_avvia e' a catalogo, pericolosa
#   4. fn_accoda_lavoro: a tipo spento rifiuta con E_JOB_TYPE_NON_ATTIVO;
#      a tipo acceso torna l'id e la stessa chiave torna lo STESSO id
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.core.services.avvio_manuale import (
    HANDLER_CODE,
    JOB_TYPE_ESEGUI_PROCESSO,
    chiave_idempotenza,
)
from apps.core.services.coda_lavori.handler_registry import get_handler
from apps.core.services.coda_lavori.repository import (
    ORIGINE_API,
    RUN_AS_OPERATORE,
    CodaLavoriRepository,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto

# Le tre righe del brief, come chiavi di catalogo (non id: gli id sono un fatto
# del CSV, i codici sono il contratto).
_PROCESSO = "avvio_manuale"
_AZIONE = "processo_avvia"
# Una chiave che nessun lavoro vero puo' avere.
_UNIT_DI_PROVA = "zeroerp-test-avvio-manuale"


class AvvioManualeCatalogoTests(TestCase):
    """Le tre righe di catalogo come le legge il backend."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: una riga dal catalogo, o None.
    @staticmethod
    def _riga(sql: str, params: list) -> tuple | None:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    # 1. Il binding seed <-> Python: il `handler_code` del CSV e' la stringa
    #    registrata al boot, e risolve a un handler. Piu' i due default che
    #    il brief ha chiesto (OPERATORE, un tentativo) e il processo padre.
    def test_tipo_esegui_processo(self) -> None:
        riga = self._riga(
            """
            SELECT handler_code, run_as_default, max_tentativi_default, processo_codice
              FROM dbops.coda_lavori_tipi WHERE codice = %s
            """,
            [JOB_TYPE_ESEGUI_PROCESSO],
        )
        self.assertIsNotNone(riga, f"{JOB_TYPE_ESEGUI_PROCESSO} non e' in coda_lavori_tipi")
        assert riga is not None
        handler_code, run_as, max_tentativi, processo = riga
        self.assertEqual(handler_code, HANDLER_CODE)
        get_handler(handler_code)  # solleva se il boot non l'ha registrato
        self.assertEqual(run_as, RUN_AS_OPERATORE)
        self.assertEqual(max_tentativi, 1)
        self.assertEqual(processo, _PROCESSO)

    # 2. Il processo sotto cui il lavoro si registra: MANUTENZIONE (nessun
    #    utente tecnico), CODA (lo accoda una persona), senza contratto di
    #    liveness (gira quando qualcuno preme).
    def test_processo_avvio_manuale(self) -> None:
        riga = self._riga(
            "SELECT classe, canale, tolleranza_minuti FROM dbops.processi WHERE codice = %s",
            [_PROCESSO],
        )
        self.assertIsNotNone(riga, f"{_PROCESSO} non e' in dbops.processi")
        assert riga is not None
        self.assertEqual(riga[0], "MANUTENZIONE")
        self.assertEqual(riga[1], "CODA")
        self.assertIsNone(riga[2])

    # 3. L'azione di processo esiste ed e' pericolosa (la conferma a video e'
    #    il minimo). ⚠️ In v1 e' DECORATIVA per scelta (brief §10.2, punto 3):
    #    nessuna view la valuta, e questo test lo sa.
    def test_azione_processo_avvia(self) -> None:
        riga = self._riga(
            "SELECT pericolosa FROM config.azioni_processo WHERE permission_codename = %s",
            [_AZIONE],
        )
        self.assertIsNotNone(riga, f"{_AZIONE} non e' in config.azioni_processo")
        assert riga is not None
        self.assertTrue(riga[0])

    # 4. L'accodamento vero, in transazione ritirata, nel ramo che vale ADESSO.
    def test_accodamento_reale(self) -> None:
        attivo = self._riga(
            "SELECT attivo FROM dbops.coda_lavori_tipi WHERE codice = %s",
            [JOB_TYPE_ESEGUI_PROCESSO],
        )
        assert attivo is not None
        repo = CodaLavoriRepository()
        scope = {"auth_user_id": 1, "username": "test", "identita_id": 1, "scope_key": "ALL"}
        chiave = chiave_idempotenza(_UNIT_DI_PROVA)

        def _accoda() -> int:
            return repo.accoda(
                job_type=JOB_TYPE_ESEGUI_PROCESSO,
                payload={"processo_codice": _PROCESSO, "unit": _UNIT_DI_PROVA},
                run_as=RUN_AS_OPERATORE,
                scope=scope,
                idempotency_key=chiave,
                origine=ORIGINE_API,
            )

        if not attivo[0]:
            # Tipo SPENTO (regola del binding): il rifiuto e' il cancello voluto.
            with transaction.atomic():
                with self.assertRaises(DatabaseError) as cm:
                    _accoda()
                transaction.set_rollback(True)
            self.assertIn("E_JOB_TYPE_NON_ATTIVO", str(cm.exception))
            self.skipTest(
                f"{JOB_TYPE_ESEGUI_PROCESSO} e' ancora attivo=false a catalogo: il "
                f"rifiuto e' provato, l'accodamento vero si prova all'accensione "
                f"(brief §10.4)"
            )

        # Tipo ACCESO: l'id, e la stessa chiave assorbita dalla dedup.
        with transaction.atomic():
            primo = _accoda()
            secondo = _accoda()
            self.assertGreater(primo, 0)
            self.assertEqual(secondo, primo, "la dedup sui vivi deve tornare lo stesso lavoro")
            vivi = repo.lavori_vivi_per_chiave(job_type=JOB_TYPE_ESEGUI_PROCESSO, chiavi=[chiave])
            self.assertEqual(vivi, {chiave: {"id": primo, "stato": "PENDING"}})
            transaction.set_rollback(True)
