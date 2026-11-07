# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `CodaLavoriRepository.lavori_vivi_per_chiave` sul database vero — la
#        lettura con cui «Esegui ora» sa se una sveglia ha GIA' un lavoro in
#        coda (capability nel dettaglio del processo, rifiuto dell'endpoint).
# Note: ⭐ «Vivo» e' `STATI_VIVI` (PENDING, IN_CORSO): la stessa definizione
#        dell'unique parziale `uq_coda_lavori_vivo_idem` con cui
#        `fn_accoda_lavoro` assorbe il doppione. Qui si prova che la lettura la
#        applichi per intero — un FATTO, un ERRORE o un ANNULLATO con la stessa
#        chiave NON sono «in coda» — e che il tipo faccia da perimetro: la
#        stessa chiave su un altro tipo e' un altro lavoro.
#        ⚠️ Le righe si scrivono direttamente sulla tabella con `run_as =
#        SISTEMA` (scope NULL, per il CHECK), in transazione ritirata, con
#        chiavi che nessun lavoro vero puo' avere (`test:vivi:*`).
#        ⛔ Il caso si COSTRUISCE: un test che leggesse le righe di oggi
#        passerebbe a vuoto su un database senza lavori.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_vivi_sono_pending_e_in_corso_e_gli_altri_no
     PENDING e IN_CORSO tornano, FATTO/ERRORE/ANNULLATO no, chiave ignota no.
2. test_il_tipo_e_un_perimetro
     la stessa chiave su un altro tipo non e' «in coda» per questo tipo.
3. test_senza_chiavi_non_si_interroga
     lista vuota -> dict vuoto, nessuna query (`= ANY('{}')` sarebbe un giro a vuoto).
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from django.db import connection, transaction

from apps.core.services.coda_lavori.repository import (
    STATI_VIVI,
    CodaLavoriRepository,
)
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto

# Due tipi a catalogo (FK dura): i due giri di fatturazione dall'app.
_TIPO = "FATTURAZIONE_GIRO"
_ALTRO_TIPO = "FATTURAZIONE_NUMERA"


class LavoriViviPerChiaveTests(TestCase):
    """La lettura dei lavori vivi per chiave, contro il database vero."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.repo = CodaLavoriRepository()

    # Scopo: scrive una riga della coda nello stato dato con la chiave data;
    #        torna l'id.
    def _scrivi(self, cur, *, tipo: str, chiave: str, stato: str) -> int:
        # ⛔ Come SUPER ADMIN (dal blocco 5b la coda e' sotto RLS: una riga
        #    SISTEMA la scrive e la legge solo lui o il drenatore). `SET LOCAL`:
        #    vale per la transazione del test, e ripeterlo e' innocuo.
        apri_contesto_operatore(cur, super_admin=True)
        cur.execute(
            """
            INSERT INTO dbops.coda_lavori
                   (job_type, payload, run_as, scope, origine, stato, idempotency_key)
            VALUES (%s, '{}'::jsonb, 'SISTEMA', NULL, 'COMMAND', %s, %s)
            RETURNING id
            """,
            [tipo, stato, chiave],
        )
        riga = cur.fetchone()
        assert riga is not None
        return int(riga[0])

    # 1. Solo PENDING e IN_CORSO sono «in coda». Ogni stato ha la sua chiave,
    #    perche' l'unique parziale ammette UN vivo per chiave; le chiavi dei
    #    non vivi si chiedono lo stesso, e devono restare fuori.
    def test_vivi_sono_pending_e_in_corso_e_gli_altri_no(self) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                attesi = {}
                for stato in STATI_VIVI:
                    chiave = f"test:vivi:{stato.lower()}"
                    attesi[chiave] = (self._scrivi(cur, tipo=_TIPO, chiave=chiave, stato=stato), stato)
                non_vivi = []
                for stato in ("FATTO", "ERRORE", "ANNULLATO"):
                    chiave = f"test:vivi:{stato.lower()}"
                    self._scrivi(cur, tipo=_TIPO, chiave=chiave, stato=stato)
                    non_vivi.append(chiave)
            vivi = self.repo.lavori_vivi_per_chiave(
                job_type=_TIPO, chiavi=[*attesi, *non_vivi, "test:vivi:ignota"],
            )
            self.assertEqual(set(vivi), set(attesi), "vivi = PENDING + IN_CORSO, nient'altro")
            for chiave, (item_id, stato) in attesi.items():
                self.assertEqual(vivi[chiave], {"id": item_id, "stato": stato})
            transaction.set_rollback(True)

    # 2. La chiave e' univoca PER TIPO (`uq_coda_lavori_vivo_idem` e' su
    #    job_type + idempotency_key): un lavoro vivo di un altro tipo con la
    #    stessa chiave non e' «in coda» per questo.
    def test_il_tipo_e_un_perimetro(self) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                self._scrivi(cur, tipo=_ALTRO_TIPO, chiave="test:vivi:altro", stato="PENDING")
            vivi = self.repo.lavori_vivi_per_chiave(job_type=_TIPO, chiavi=["test:vivi:altro"])
            self.assertEqual(vivi, {})
            transaction.set_rollback(True)

    # 3. Senza chiavi non c'e' niente da chiedere: nessun round-trip.
    def test_senza_chiavi_non_si_interroga(self) -> None:
        with patch("apps.core.services.coda_lavori.repository.connection") as conn:
            self.assertEqual(self.repo.lavori_vivi_per_chiave(job_type=_TIPO, chiavi=[]), {})
            conn.cursor.assert_not_called()
