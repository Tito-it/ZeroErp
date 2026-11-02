# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: ⏳ TEST DI PARITA' TRANSITORIO (pezzo V del piano
#        `piano-be-fe-osservabilita-pallino-e-superfici`, §5): il verdetto
#        «lotto fermo» che il DB scrive in `fermo` (`20260919-01/-02`) dice la
#        stessa cosa dei tre addendi che `LottoSegnalazioniService` calcolava
#        in Python fino al 2026-09-19.
#
# ⛔ NON E' UN PRESIDIO: E' IL COLLAUDO DELLA MIGRAZIONE DI SEDE, e si toglie
#    con la PR successiva a quella che lo introduce. Confronta il risultato
#    nuovo con la POPOLAZIONE del database di sviluppo, cioe' prova i soli
#    casi che quella popolazione per caso contiene (AGENTS.md, corollario sui
#    test); i tre addendi, caso per caso e COSTRUITI, li prova il pgTAP
#    `db/pgtap/vendite/test-lotti-fermi-verdetto-a-db-v1.sql`. Su un database
#    ricostruito da zero — la CI — questo file passa a vuoto, e lo DICHIARA
#    con uno `skipTest`.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1`. NON LASCIA NIENTE:
#    tutto in transazione annullata.
#
# Indice test:
#   1. test_il_verdetto_a_db_coincide_con_i_tre_addendi
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.db.pipeline_repository import VenditePipelineRepository

# Quanti lotti si confrontano: i piu' recenti, che sono quelli con gli esiti
# del modello di oggi. E' un tetto di costo, non un criterio.
_LOTTI_DA_CONFRONTARE = 100


class ParitaVerdettoLottoFermoTransitorio(TestCase):
    """`fermo` a DB ⇔ la vecchia somma Python, sui lotti che il DB di sviluppo ha."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: per ogni lotto visibile nel contesto operatore, il `fermo` letto
    #        dal repository e' identico alla formula che il service applicava:
    #        (critiche fattura + critiche lotto) > 0, o fatture in ERRORE sul
    #        ponte > 0, o esiti ERRORE > 0.
    def test_il_verdetto_a_db_coincide_con_i_tre_addendi(self):
        repo = VenditePipelineRepository()
        divergenti: list[tuple[int, bool, bool]] = []
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "SELECT id FROM vendite.fatturazione_lotti ORDER BY id DESC LIMIT %s",
                    [_LOTTI_DA_CONFRONTARE],
                )
                lotto_ids = [int(r[0]) for r in cur.fetchall()]
            if not lotto_ids:
                transaction.set_rollback(True)
                self.skipTest(
                    "nessun lotto nel perimetro: collaudo transitorio senza materia "
                    "(i casi costruiti stanno nel pgTAP test-lotti-fermi-verdetto-a-db-v1)"
                )
            for lotto_id in lotto_ids:
                s = repo.get_lotto_segnalazioni_summary(lotto_id)
                atteso = (
                    (s["fatture_critical_count"] + s["lotto_critical_count"]) > 0
                    or s["fatture_stato_esecuzione_errore_count"] > 0
                    or s["esiti_stato_esecuzione_errore_count"] > 0
                )
                if s["fermo"] is not atteso:
                    divergenti.append((lotto_id, s["fermo"], atteso))
            transaction.set_rollback(True)
        self.assertEqual(divergenti, [], f"lotti su cui DB e Python divergono: {divergenti}")
