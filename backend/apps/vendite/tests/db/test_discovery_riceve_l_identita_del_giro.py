# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: D1 + D2 del brief `brief-db-rilancio-step-non-rivede-le-proprie-commesse`
#        (§9.2, test su DB provvisto) — il PYTHON ARRIVA alle funzioni nuove:
#        la discovery lega sulla firma a OTTO argomenti con l'identita' del
#        giro, e il riepilogo legge il decimo numero dalla funzione vera.
#
# ⭐ PERCHE' UN TEST SU DB VERO, accanto ai 13 pgTAP di P-5 e ai mock del
#    service: i pgTAP provano che discovery ed emit, con la stessa identita',
#    riprendono la riga — il lato DB. I test unit provano che il Python passa
#    l'argomento — il lato Python. NESSUNO DEI DUE VEDE LA GIUNTURA: che la
#    chiamata per nome `p_emit_batch_id => %s::uuid` LEGHI sulla funzione che
#    c'e' davvero, e che la colonna `esiti_stato_esecuzione_errore_count`
#    ESISTA con quel nome. Un mock lega su qualunque cosa
#    ([[feedback_rinomina_db_binding_mockato]]).
#
# ⛔ IL CASO CHE QUESTO FILE DEVE VEDERE: `20260912-15` ha fatto `DROP` della
#    firma a 7 e `CREATE` a 8 con default. Se un giorno le due firme vivessero
#    insieme, la chiamata a 7 argomenti sarebbe «function is not unique» e la
#    chiamata a 8 legherebbe lo stesso — cioe' il repository funzionerebbe e i
#    chiamanti storici no. Per questo si asserisce anche che la firma sia UNA.
#
# ⚠️ Non ripete P-5-bis/ter: non costruisce lotti, commesse ed esiti (lo fanno i
#    pgTAP, dove il caso si fabbrica). Qui si chiama con un'identita' casuale —
#    che la funzione risolve a NULL, la risposta prudente — e si guarda che
#    LEGHI e RISPONDA, non che cosa risponda.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    NON LASCIA NIENTE: tutto in transazione annullata.
#
# Indice test:
#   1. test_la_discovery_lega_sulla_firma_a_otto_con_l_identita
#   2. test_la_firma_della_discovery_e_una_sola
#   3. test_il_riepilogo_legge_il_decimo_numero_dalla_funzione_vera
#   4. test_il_riepilogo_legge_il_verdetto_dalla_funzione_vera (D-V1, 2026-09-19)
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from uuid import uuid4

from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.types import LottoSegnalazioniSummary


class DiscoveryRiceveLIdentitaDelGiro(TestCase):
    """Il repository arriva alle funzioni di D1 e D2 cosi' come sono a DB."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: la chiamata per nome con `p_emit_batch_id` LEGA e risponde una
    #        lista. Un'identita' casuale risolve a NULL lato DB (nessun lotto
    #        la porta): la risposta e' quella «senza auto-esclusione», e qui
    #        conta che arrivi, non quante righe abbia.
    def test_la_discovery_lega_sulla_firma_a_otto_con_l_identita(self):
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
            # Una competenza qualunque: qui si prova il BINDING, non il filtro.
            # Il primo del mese corrente, e non una data scritta: un test con
            # una data cablata invecchia senza che nessuno se ne accorga.
            commesse = CommesseRepository().list_commesse_emittibili(
                competenza_mese=oggi_aziendale().replace(day=1),
                emit_batch_id=str(uuid4()),
                limit=5,
            )
            self.assertIsInstance(commesse, list)
            transaction.set_rollback(True)

    # Scopo: ⛔ UNA firma sola. Con due (7 e 8 argomenti, la seconda col
    #        default) la chiamata storica a 7 sarebbe ambigua — e l'ambiguita'
    #        non si vede da questo repository, che ne passa sempre 8.
    def test_la_firma_della_discovery_e_una_sola(self):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT pg_get_function_identity_arguments(p.oid)
                      FROM pg_proc p
                      JOIN pg_namespace n ON n.oid = p.pronamespace
                     WHERE n.nspname = 'vendite'
                       AND p.proname = 'fn_list_commesse_emittibili'
                    """
                )
                firme = [r[0] for r in cur.fetchall()]
            transaction.set_rollback(True)
        self.assertEqual(len(firme), 1, firme)
        self.assertIn("p_emit_batch_id", firme[0])

    # Scopo: il riepilogo chiede la decima colonna PER NOME alla funzione vera.
    #        Se la colonna non esistesse o si chiamasse diversamente la SELECT
    #        fallirebbe qui — e' il verso che il mock del repository non sa
    #        dare. ⭐ Il lotto NON si cerca: la funzione non solleva su un id
    #        inesistente (risponde una riga di zeri), quindi si chiede un id che
    #        per costruzione non c'e' — `max(id) + 1` nella stessa transazione.
    #        La prima stesura cercava «un lotto qualunque» e saltava se non lo
    #        trovava: su un database ricostruito da zero — la CI — sarebbe
    #        stata verde per sottrazione (AGENTS.md, corollario sui test).
    #        Il valore non e' il soggetto, la chiave si': e con un lotto
    #        inesistente si asserisce anche lo ZERO, cioe' che il ripiego non
    #        e' stato scambiato per un dato.
    def test_il_riepilogo_legge_il_decimo_numero_dalla_funzione_vera(self):
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT COALESCE(max(id), 0) + 1 FROM vendite.fatturazione_lotti")
                riga = cur.fetchone()
            assert riga is not None
            summary = VenditePipelineRepository().get_lotto_segnalazioni_summary(int(riga[0]))
            transaction.set_rollback(True)
        self.assertIn("esiti_stato_esecuzione_errore_count", summary)
        self.assertEqual(summary["esiti_stato_esecuzione_errore_count"], 0)
        # E le undici chiavi del contratto Python sono TUTTE nella risposta
        # della funzione vera: e' la giuntura che ne' il pgTAP ne' il mock
        # vedono.
        self.assertEqual(set(summary), set(LottoSegnalazioniSummary.__annotations__))

    # Scopo: ⭐ D-V1 (2026-09-19, `20260919-02`) — l'UNDICESIMA colonna `fermo`
    #        c'e' davvero, con quel nome, ed e' un BOOLEANO: su un lotto che
    #        non esiste la funzione risponde `false` (il ripiego «zeri e
    #        fermo=false» della sua COMMENT), e il repository lo consegna come
    #        `False`, non come `0`. Stessa forma del test 3: l'id e' quello che
    #        per costruzione non c'e'.
    def test_il_riepilogo_legge_il_verdetto_dalla_funzione_vera(self):
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT COALESCE(max(id), 0) + 1 FROM vendite.fatturazione_lotti")
                riga = cur.fetchone()
            assert riga is not None
            summary = VenditePipelineRepository().get_lotto_segnalazioni_summary(int(riga[0]))
            transaction.set_rollback(True)
        self.assertIn("fermo", summary)
        self.assertIs(summary["fermo"], False)
