# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test ddt_service (mock repository, no DB). Clone strutturale di
#        test_ordini_service: valida i guard di stato/not-found, la derivazione
#        destinatario_soggetto_ruolo dal BA in create, l'immutabilita' cliente in
#        update, il gating eliminazione, il cambio stato data-driven (+ emetti),
#        l'evasione da ordine (delega alla fn madre, niente atomic extra), il push
#        singolo a commessa (sorgente DDT_VENDITA) e la traduzione errori DB di
#        _db_errors (IntegrityError -> codice vincolo; DatabaseError trigger ->
#        estrazione codice E_*).
# ------------------------------------------------------------

"""
Indice test eseguiti (classe :: metodo):

DdtServiceGuardsTests
 1) test_get_ddt_not_found                 — E_DDT_NOT_FOUND se testata None
 2) test_cambia_stato_ddt_not_found        — E_DDT_NOT_FOUND se stato None (guard leggero)
 3) test_aggiorna_ddt_stato_non_draft      — E_DDT_STATO_TRANSIZIONE se != DRAFT
 4) test_gestisci_riga_stato_non_draft     — E_DDT_STATO_TRANSIZIONE se != DRAFT
 5) test_elimina_riga_stato_non_draft      — E_DDT_STATO_TRANSIZIONE se != DRAFT

DdtCreaTests
 6) test_crea_ddt_deriva_destinatario_da_ba — deriva destinatario dal BA + DRAFT
 7) test_crea_ddt_destinatario_esplicito    — destinatario passato: no lookup BA
 8) test_crea_ddt_senza_destinatario_ne_ba  — E_DDT_VALIDAZIONE
 8b) test_crea_ddt_senza_ba_rifiutato       — E_DDT_VALIDAZIONE (BA obbligatorio: destinatario + fallback emittente)
 8c) test_crea_ddt_passa_emittente_payload  — emittente dallo user (payload) → repo kwargs
 8d) test_crea_ddt_emittente_omesso_none    — emittente assente → None (fallback DB dal BA)

DdtAggiornaTests
 9) test_aggiorna_ddt_cambio_ba_rifiutato   — E_DDT_CLIENTE_IMMUTABILE
10) test_aggiorna_ddt_ba_invariato_tollerato — BA uguale escluso dall'UPDATE
11) test_aggiorna_ddt_ba_non_numerico       — E_DDT_VALIDAZIONE (no 500)

DdtEliminaTests
12) test_elimina_ddt_con_righe_rifiutato    — E_DDT_STATO_TRANSIZIONE
13) test_elimina_ddt_bozza_orfana_ok        — hard-delete ammesso (0 righe)

DdtCambiaStatoTests
14) test_cambia_stato_ok                    — risolve id + update_stato
15) test_cambia_stato_codice_vuoto          — E_DDT_VALIDAZIONE
16) test_cambia_stato_codice_inesistente    — E_DDT_VALIDAZIONE
17) test_emetti_transita_a_emesso_light      — cambia_stato(EMESSO), ritorno light (no reload)

DdtCreaDaOrdineTests
18) test_crea_ddt_da_ordine_delega_e_ritorna — push_da_ordine + ritorno mappato
19) test_crea_ddt_da_ordine_no_atomic_extra  — nessun transaction.atomic extra

DdtPushCommessaTests
20) test_push_nessuna_riga_pushable          — E_DDT_NESSUNA_RIGA
21) test_push_ok_delega_e_mappa_report        — pr_run_commesse_push_one + report

DdtDbErrorsTests
22) test_integrity_error_fk_mappato          — E_VENDITE_FK
23) test_integrity_error_fallback            — E_VENDITE_VALIDATION
24) test_database_error_trigger_code_estratto — E_STATO_DDT_TRANSIZIONE_NON_VALIDA
"""

from contextlib import nullcontext
from unittest.mock import patch

from django.db import DatabaseError, IntegrityError
from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.vendite.services import ddt_service
from apps.vendite.services.ddt_service import _db_errors

_REPO = "apps.vendite.services.ddt_service.DdtRepository"
_SVC = "apps.vendite.services.ddt_service"
_ATOMIC = "apps.vendite.services.ddt_service.transaction.atomic"
# pr_run_commesse_push_one e' importato LOCALMENTE dentro push_a_commessa
# (import lazy per evitare cicli): si patcha nel modulo di origine.
_PUSH_ONE = "apps.vendite.services.commesse_service.pr_run_commesse_push_one"


class DdtServiceGuardsTests(SimpleTestCase):
    """Guard di stato (E_DDT_STATO_TRANSIZIONE) e not-found (E_DDT_NOT_FOUND)."""

    @patch(_REPO)
    def test_get_ddt_not_found(self, repo_cls) -> None:
        repo_cls.return_value.get_ddt.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.get_ddt(99)
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")

    @patch(_REPO)
    def test_cambia_stato_ddt_not_found(self, repo_cls) -> None:
        # Guard esistenza leggero: stato corrente None -> E_DDT_NOT_FOUND.
        repo_cls.return_value.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(99, "SPEDITO")
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")

    @patch(_REPO)
    def test_aggiorna_ddt_stato_non_draft(self, repo_cls) -> None:
        # DDT gia' EMESSO: la testata non e' piu' modificabile (guard su
        # testata unica: aggiorna_ddt legge get_ddt una sola volta).
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"id": 7, "stato_codice_interno": "EMESSO"}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.aggiorna_ddt(7, {"utility_id": 9})
        self.assertEqual(cm.exception.code, "E_DDT_STATO_TRANSIZIONE")
        repo.update_ddt.assert_not_called()

    @patch(_REPO)
    def test_gestisci_riga_stato_non_draft(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"stato_codice_interno": "EMESSO"}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.gestisci_riga(7, {"articolo_id": "ART1"})
        self.assertEqual(cm.exception.code, "E_DDT_STATO_TRANSIZIONE")
        repo.create_riga.assert_not_called()

    @patch(_REPO)
    def test_elimina_riga_stato_non_draft(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"stato_codice_interno": "SPEDITO"}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.elimina_riga(7, 3)
        self.assertEqual(cm.exception.code, "E_DDT_STATO_TRANSIZIONE")
        repo.delete_riga.assert_not_called()


class DdtCreaTests(SimpleTestCase):
    """crea_ddt standalone: derivazione destinatario dal BA + stato DRAFT."""

    @patch(_REPO)
    def test_crea_ddt_deriva_destinatario_da_ba(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_soggetto_ruolo_id_by_ba.return_value = 555
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_ddt.return_value = {"id": 7, "uid": "u", "numero": None}

        out = ddt_service.crea_ddt({"billing_account_id": 3, "utility_id": 1})

        self.assertEqual(out["id"], 7)
        # destinatario derivato dal billing_account (cliente=BA, come ordini).
        repo.get_soggetto_ruolo_id_by_ba.assert_called_once_with(3)
        self.assertEqual(
            repo.create_ddt.call_args.kwargs["destinatario_soggetto_ruolo_id"], 555,
        )
        # stato risolto via codice interno DRAFT.
        repo.get_stato_id_by_codice.assert_called_once_with("DRAFT")
        self.assertEqual(
            repo.create_ddt.call_args.kwargs["stato_doc_ddt_id"], 1,
        )

    @patch(_REPO)
    def test_crea_ddt_destinatario_esplicito(self, repo_cls) -> None:
        # destinatario passato esplicito: nessun lookup dal BA.
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_ddt.return_value = {"id": 8, "uid": "u", "numero": None}

        ddt_service.crea_ddt(
            {"destinatario_soggetto_ruolo_id": 777, "billing_account_id": 3},
        )
        repo.get_soggetto_ruolo_id_by_ba.assert_not_called()
        self.assertEqual(
            repo.create_ddt.call_args.kwargs["destinatario_soggetto_ruolo_id"], 777,
        )

    @patch(_REPO)
    def test_crea_ddt_senza_destinatario_ne_ba(self, repo_cls) -> None:
        # Ne' destinatario esplicito ne' billing_account -> validazione parlante.
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            ddt_service.crea_ddt({"utility_id": 1})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.create_ddt.assert_not_called()

    @patch(_REPO)
    def test_crea_ddt_senza_ba_rifiutato(self, repo_cls) -> None:
        # Cliente obbligatorio anche con destinatario esplicito: il BA deriva
        # il destinatario e ancora il fallback DB dell'emittente
        # (trgfn_ddt_normalize) -> guard parlante prima dell'INSERT.
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            ddt_service.crea_ddt({"destinatario_soggetto_ruolo_id": 777})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.create_ddt.assert_not_called()

    @patch(_REPO)
    def test_crea_ddt_passa_emittente_payload(self, repo_cls) -> None:
        # Emittente dallo USER (uniformazione 2026-07-13, mirror ordini): il
        # payload create lo porta (prefill FE dal profilo) e arriva al repo.
        repo = repo_cls.return_value
        repo.get_soggetto_ruolo_id_by_ba.return_value = 555
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_ddt.return_value = {"id": 9, "uid": "u", "numero": None}

        ddt_service.crea_ddt({"billing_account_id": 3, "emittente_fiscale_id": 32})
        self.assertEqual(
            repo.create_ddt.call_args.kwargs["emittente_fiscale_id"], 32,
        )

    @patch(_REPO)
    def test_crea_ddt_emittente_omesso_none(self, repo_cls) -> None:
        # Emittente assente dal payload (es. admin globale che non sceglie):
        # None al repo, che omette la colonna -> fallback dal BA nel trigger.
        repo = repo_cls.return_value
        repo.get_soggetto_ruolo_id_by_ba.return_value = 555
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_ddt.return_value = {"id": 10, "uid": "u", "numero": None}

        ddt_service.crea_ddt({"billing_account_id": 3})
        self.assertIsNone(
            repo.create_ddt.call_args.kwargs["emittente_fiscale_id"],
        )


class DdtAggiornaTests(SimpleTestCase):
    """aggiorna_ddt: cliente immutabile post-creazione."""

    @patch(_REPO)
    def test_aggiorna_ddt_cambio_ba_rifiutato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {
            "id": 7, "stato_codice_interno": "DRAFT", "billing_account_id": 3,
        }
        with self.assertRaises(ServiceError) as cm:
            ddt_service.aggiorna_ddt(7, {"billing_account_id": 99})
        self.assertEqual(cm.exception.code, "E_DDT_CLIENTE_IMMUTABILE")
        repo.update_ddt.assert_not_called()

    @patch(_REPO)
    def test_aggiorna_ddt_ba_invariato_tollerato(self, repo_cls) -> None:
        # BA reinviato invariato dal form: tollerato ma escluso dall'UPDATE
        # (non in whitelist _UPDATE_KEYS_DDT). Aggiorna solo gli altri campi.
        # Lettura singola: guard stato + confronto BA dalla stessa testata.
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {
            "id": 7, "stato_codice_interno": "DRAFT", "billing_account_id": 3,
        }
        ddt_service.aggiorna_ddt(7, {"billing_account_id": 3, "utility_id": 9})
        repo.get_ddt.assert_called_once_with(7)
        kwargs = repo.update_ddt.call_args.kwargs
        self.assertNotIn("billing_account_id", kwargs)
        self.assertEqual(kwargs["utility_id"], 9)

    @patch(_REPO)
    def test_aggiorna_ddt_ba_non_numerico(self, repo_cls) -> None:
        # billing_account_id non numerico -> 4xx parlante, non 500 da int().
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {
            "id": 7, "stato_codice_interno": "DRAFT", "billing_account_id": 3,
        }
        with self.assertRaises(ServiceError) as cm:
            ddt_service.aggiorna_ddt(7, {"billing_account_id": "abc"})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.update_ddt.assert_not_called()


class DdtEliminaTests(SimpleTestCase):
    """elimina_ddt: hard-delete solo per bozza orfana (0 righe)."""

    @patch(_REPO)
    def test_elimina_ddt_con_righe_rifiutato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = [{"id": 1}]
        with self.assertRaises(ServiceError) as cm:
            ddt_service.elimina_ddt(7)
        self.assertEqual(cm.exception.code, "E_DDT_STATO_TRANSIZIONE")
        repo.delete_ddt.assert_not_called()

    @patch(_REPO)
    def test_elimina_ddt_bozza_orfana_ok(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = []
        repo.delete_ddt.return_value = True
        out = ddt_service.elimina_ddt(7)
        self.assertTrue(out["deleted"])
        repo.delete_ddt.assert_called_once_with(7)


class DdtCambiaStatoTests(SimpleTestCase):
    """cambia_stato data-driven + emetti (DRAFT->EMESSO)."""

    @patch(_REPO)
    def test_cambia_stato_ok(self, repo_cls) -> None:
        # Guard esistenza leggero: cambia_stato legge SOLO lo stato corrente
        # (get_stato_codice), non la testata completa.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 6
        out = ddt_service.cambia_stato(7, "SPEDITO")
        self.assertEqual(out["stato"], "SPEDITO")
        self.assertEqual(out["stato_precedente"], "DRAFT")
        repo.get_ddt.assert_not_called()
        repo.get_stato_id_by_codice.assert_called_once_with("SPEDITO")
        repo.update_stato.assert_called_once_with(7, 6)

    @patch(_REPO)
    def test_cambia_stato_codice_vuoto(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, "   ")
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.update_stato.assert_not_called()

    @patch(_REPO)
    def test_cambia_stato_codice_inesistente(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, "INESISTENTE")
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.update_stato.assert_not_called()

    @patch(_REPO)
    def test_emetti_transita_a_emesso_light(self, repo_cls) -> None:
        # emetti = cambia_stato(EMESSO, guard leggero get_stato_codice) con
        # ritorno LIGHT {ddt_id, stato_precedente, stato} — parita' con
        # ordini_service.conferma: NIENTE reload del detail pesante (vista +
        # capabilities + count) dentro la sezione atomica dell'emissione
        # documentale; il FE ricarica il detail dopo.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 2

        out = ddt_service.emetti(7)

        repo.get_stato_id_by_codice.assert_called_once_with("EMESSO")
        repo.update_stato.assert_called_once_with(7, 2)
        repo.get_ddt.assert_not_called()
        repo.get_capabilities.assert_not_called()
        self.assertEqual(out["ddt_id"], 7)
        self.assertEqual(out["stato_precedente"], "DRAFT")
        self.assertEqual(out["stato"], "EMESSO")


class DdtCreaDaOrdineTests(SimpleTestCase):
    """crea_ddt_da_ordine: delega alla primitiva DB madre (evasione)."""

    @patch(_REPO)
    def test_crea_ddt_da_ordine_delega_e_ritorna(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.push_da_ordine.return_value = 42

        righe = [{"ordine_riga_id": 11, "qta_da_evadere": "2"}]
        out = ddt_service.crea_ddt_da_ordine(99, righe)

        repo.push_da_ordine.assert_called_once_with(99, righe)
        # numero deterministicamente None (DDT in DRAFT): nessun re-read.
        repo.get_ddt.assert_not_called()
        self.assertEqual(out, {"ddt_id": 42, "numero": None, "ordine_id": 99})

    @patch(f"{_SVC}.transaction")
    @patch(_REPO)
    def test_crea_ddt_da_ordine_no_atomic_extra(self, repo_cls, mock_tx) -> None:
        # L'atomicita' vive DENTRO la fn madre DB: il service NON deve aprire un
        # transaction.atomic() extra (gemello crea_ordine_da_preventivo).
        repo = repo_cls.return_value
        repo.push_da_ordine.return_value = 42
        ddt_service.crea_ddt_da_ordine(99)
        mock_tx.atomic.assert_not_called()


class DdtPushCommessaTests(SimpleTestCase):
    """push_a_commessa: push singolo con sorgente DDT_VENDITA."""

    def setUp(self) -> None:
        # transaction.atomic() a no-op (SimpleTestCase senza DB); riusabile su
        # piu' `with` (nullcontext stateless).
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_REPO)
    def test_push_nessuna_riga_pushable(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"stato_codice_interno": "SPEDITO"}
        repo.count_righe_pushable.return_value = 0
        with self.assertRaises(ServiceError) as cm:
            ddt_service.push_a_commessa(55)
        self.assertEqual(cm.exception.code, "E_DDT_NESSUNA_RIGA")

    @patch(_PUSH_ONE)
    @patch(_REPO)
    def test_push_ok_delega_e_mappa_report(self, repo_cls, mock_push_one) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"stato_codice_interno": "SPEDITO"}
        repo.count_righe_pushable.return_value = 3
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 7, "durata_ms": 5,
            "handlers": [], "commesse_ids": [10],
        }

        out = ddt_service.push_a_commessa(55, user="op")

        mock_push_one.assert_called_once_with(
            sorgente_codice="DDT_VENDITA", sorgente_uid=55, user="op",
        )
        self.assertEqual(out["ddt_id"], 55)
        self.assertEqual(out["stato"], "COMPLETATO")
        self.assertEqual(out["push_log_id"], 7)
        self.assertEqual(out["commesse_ids"], [10])
        self.assertEqual(out["righe_pushable"], 3)


class DdtDbErrorsTests(SimpleTestCase):
    """Traduzione errori DB di _db_errors (gemello OrdiniDbErrorsTests)."""

    def test_integrity_error_fk_mappato(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError(
                    'insert or update on table "ddt" violates foreign key '
                    'constraint "fk_ddt_v_billing_account"',
                )
        self.assertEqual(cm.exception.code, "E_VENDITE_FK")

    def test_integrity_error_fallback(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError("vincolo sconosciuto xyz")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    def test_database_error_trigger_code_estratto(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise DatabaseError(
                    "E_STATO_DDT_TRANSIZIONE_NON_VALIDA: transizione non ammessa",
                )
        self.assertEqual(
            cm.exception.code, "E_STATO_DDT_TRANSIZIONE_NON_VALIDA",
        )


class DdtFatturazioneImmediataTests(SimpleTestCase):
    """Corsia di instradamento `fatturazione_immediata` sul DDT.

    Gemello di `OrdiniFatturazioneImmediataTests`: qui la whitelist basta
    (mapper generico), ma il comportamento va bloccato — il difetto del
    2026-07-27 sui contratti e' nato proprio dal dare per scontato che il gesto
    fosse identico sui tre domini.
    """

    @patch(_REPO)
    def test_crea_ddt_porta_il_flag(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_destinatario_soggetto_ruolo_id_by_ba.return_value = 555
        repo.get_soggetto_ruolo_id_by_ba.return_value = 555
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_ddt.return_value = {"id": 9, "uid": "u", "numero": None}
        ddt_service.crea_ddt({
            "billing_account_id": 3, "utility_id": 1, "fatturazione_immediata": True,
        })
        self.assertIs(
            repo.create_ddt.call_args.kwargs["fatturazione_immediata"], True,
        )

    @patch(_REPO)
    def test_aggiorna_ddt_persiste_il_flag(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {
            "id": 9, "billing_account_id": 3, "stato_codice_interno": "DRAFT",
        }
        ddt_service.aggiorna_ddt(9, {"fatturazione_immediata": True})
        self.assertIs(
            repo.update_ddt.call_args.kwargs["fatturazione_immediata"], True,
        )


# ══════════════════════════════════════════════════════════
#  BE-B6 — il DDT ammette righe senza prezzo
# ══════════════════════════════════════════════════════════
# Scopo: presidiare il cuore del brief-ddt-righe-senza-prezzo — una riga il cui
#        prezzo non e' risolvibile si SALVA, col prezzo a `None` e il motivo
#        riportato. Fino al 2026-08-19 diventava `"0"`, e uno zero e' un prezzo:
#        la riga entrava in fattura a valore nullo invece di essere fermata.
class DdtRigaSenzaPrezzoTests(SimpleTestCase):
    _PRICING = "apps.vendite.services.pricing_service.PricingService"
    _IVA = "apps.vendite.services.ddt_service._risolvi_iva_riga"

    def setUp(self) -> None:
        # `transaction.atomic()` a no-op: qui non c'e' DB, e quel che si prova
        # sono gli argomenti con cui il repository viene chiamato.
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)
        # ⭐ Il risolutore IVA e' un collaboratore NUOVO di `gestisci_riga`
        #    (I3, 2026-08-31), e va mockato per la stessa ragione del
        #    repository: senza, questi test aprirebbero una connessione vera e
        #    in CI — dove il DB non c'e' — fallirebbero per un motivo che non
        #    c'entra con cio' che verificano.
        # ⚠️ Il default risponde «nessun `iva_id`, nessun meta»: cosi' i casi
        #    che qui non parlano di IVA restano identici a prima.
        # ⚠️ Si patcha `_risolvi_iva_riga` e non il BB: dal 2026-08-31 e'
        #    costruito da una FACTORY, quindi il service non nomina piu'
        #    `IvaResolverService` e patchare quello non intercetterebbe niente —
        #    il test sarebbe verde senza mockare nulla.
        iva_patcher = patch(self._IVA)
        self.iva = iva_patcher.start()
        self.addCleanup(iva_patcher.stop)
        self.iva.return_value = (None, {})

    # Scopo: testata minima in DRAFT con quel che serve al pricing.
    def _testata(self):
        return {
            "id": 7,
            "stato_codice_interno": "DRAFT",
            "billing_account_id": 100,
            "utility_id": 5,
            "data": "2026-08-19",
            "emittente_fiscale_id": 3,
        }

    # Scopo: ⭐ IL CABLAGGIO E' VISIBILE. Con il risolutore mockato il resto
    #        della suite non si accorgerebbe se qualcuno lo staccasse: qui si
    #        prova che `gestisci_riga` lo interroga col contesto della TESTATA
    #        e scrive il suo esito sulla riga.
    # ⛔ `emittente_fiscale_id` e' la PK (3), non il `soggetto_ruolo_id` (42)
    #    che il pricing usa: e' la trappola che il progetto ha gia' pagato, e
    #    con quello sbagliato il risolutore non troverebbe i titoli e
    #    risponderebbe con l'aliquota ordinaria SENZA sollevare.
    @patch(_PRICING)
    @patch(_REPO)
    def test_iva_di_riga_viene_dal_risolutore(self, repo_cls, pricing_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = self._testata()
        repo.is_articolo_composito.return_value = False
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 31}
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 42
        self.iva.return_value = (9, {"iva_origine": "TITOLO", "iva_titolo_id": 4})

        ddt_service.gestisci_riga(7, {
            "articolo_id": "ART1", "uom_operativa_id": 5, "prezzo_unitario": "10",
            "meta": {"origine_import": "XYZ"},
        })

        # ⭐ Qui si prova il CABLAGGIO: la testata arriva al risolutore e il suo
        #    esito finisce sulla riga. Che dalla testata si ricavi la PK giusta
        #    dell'emittente e' provato dove quella logica ora vive —
        #    `test_iva_contesto_documento.py`.
        self.assertIs(self.iva.call_args.args[0], repo.get_ddt.return_value)
        self.assertEqual(self.iva.call_args.kwargs["articolo_id"], "ART1")

        scritta = repo.create_riga.call_args.kwargs
        self.assertEqual(scritta["iva_id"], 9)
        # ⚠️ Il meta del client non si perde: il patch dell'IVA si FONDE.
        self.assertEqual(scritta["meta"]["origine_import"], "XYZ")
        self.assertEqual(scritta["meta"]["iva_origine"], "TITOLO")

    @patch(_PRICING)
    @patch(_REPO)
    def test_riga_semplice_senza_prezzo_si_salva(self, repo_cls, pricing_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = self._testata()
        repo.is_articolo_composito.return_value = False
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 31}
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 42
        pricing_cls.return_value.resolve_prezzo_esito.return_value = {
            "prezzo_finale": None,
            "esito_codice": "E_CATEGORIA_LISTINO_NON_MAPPATA",
        }

        out = ddt_service.gestisci_riga(7, {"articolo_id": "ART1", "uom_operativa_id": 5})

        # 1. la riga si salva, e si salva SENZA prezzo (non con "0")
        self.assertIsNone(repo.create_riga.call_args.kwargs["prezzo_unitario"])
        # 2. il chiamante riceve il motivo, con un testo gia' pronto (DEC-4)
        self.assertEqual(out["prezzo_esito"]["codice"], "E_CATEGORIA_LISTINO_NON_MAPPATA")
        self.assertTrue(out["prezzo_esito"]["messaggio"])
        # 3. F-7/DEC-8: il motivo e' persistito, non solo restituito
        meta = repo.create_riga.call_args.kwargs["meta"]
        self.assertEqual(
            meta["prezzo_resolver_context"]["esito_codice"],
            "E_CATEGORIA_LISTINO_NON_MAPPATA",
        )

    @patch(_PRICING)
    @patch(_REPO)
    def test_riga_semplice_col_prezzo_invariata(self, repo_cls, pricing_cls) -> None:
        # Controprova: quando il prezzo si risolve non cambia niente rispetto a
        # prima, e in `meta` non compare nessuna chiave nuova.
        repo = repo_cls.return_value
        repo.get_ddt.return_value = self._testata()
        repo.is_articolo_composito.return_value = False
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 32}
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 42
        pricing_cls.return_value.resolve_prezzo_esito.return_value = {
            "prezzo_finale": "12.50", "esito_codice": None,
        }

        out = ddt_service.gestisci_riga(7, {"articolo_id": "ART1", "uom_operativa_id": 5})

        self.assertEqual(repo.create_riga.call_args.kwargs["prezzo_unitario"], "12.50")
        self.assertIsNone(out["prezzo_esito"])
        self.assertIsNone(repo.create_riga.call_args.kwargs["meta"])

    @patch(_PRICING)
    @patch(_REPO)
    def test_meta_del_client_non_viene_sovrascritto(self, repo_cls, pricing_cls) -> None:
        # DEC-8, confine 2: `meta` e' del client, il motivo ci si FONDE.
        repo = repo_cls.return_value
        repo.get_ddt.return_value = self._testata()
        repo.is_articolo_composito.return_value = False
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 33}
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 42
        pricing_cls.return_value.resolve_prezzo_esito.return_value = {
            "prezzo_finale": None, "esito_codice": "E_PREZZO_LISTINO_RIGA_NON_TROVATA",
        }

        ddt_service.gestisci_riga(7, {
            "articolo_id": "ART1", "uom_operativa_id": 5,
            "meta": {"origine_import": "XYZ"},
        })

        meta = repo.create_riga.call_args.kwargs["meta"]
        self.assertEqual(meta["origine_import"], "XYZ")
        self.assertIn("prezzo_resolver_context", meta)

    @patch(_REPO)
    def test_riga_composita_niente_zero(self, repo_cls) -> None:
        # V-6: il padre composito si inserisce con NULL. Il ricalcolo DB mette
        # NULL se anche un solo figlio e' scoperto: partire da "0" dichiarerebbe
        # un prezzo che nessuno ha deciso.
        repo = repo_cls.return_value
        repo.get_ddt.return_value = self._testata()
        repo.is_articolo_composito.return_value = True
        repo.next_riga_nr.return_value = 2
        repo.create_riga.return_value = {"id": 34}
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 42

        out = ddt_service.gestisci_riga(7, {"articolo_id": "KIT1", "uom_operativa_id": 5})

        self.assertIsNone(repo.create_riga.call_args.kwargs["prezzo_unitario"])
        self.assertTrue(out["is_composito"])
        self.assertIsNone(out["prezzo_esito"])

    @patch(_REPO)
    def test_patch_prezzo_vuoto_cancella_il_prezzo(self, repo_cls) -> None:
        # V-7: `aggiorna_riga` non e' stata toccata — cancellare il prezzo a
        # mano funzionava gia'. Ma nessun test lo provava, e da oggi il FE ci si
        # appoggia: la stringa vuota deve arrivare al repository come `None`,
        # non come `""` (che il DB rifiuterebbe) e non come `0`.
        repo = repo_cls.return_value
        repo.get_ddt.return_value = self._testata()
        repo.get_riga.return_value = {"id": 31, "ddt_id": 7}
        repo.update_riga.return_value = {"id": 31}

        ddt_service.aggiorna_riga(7, 31, {"prezzo_unitario": ""})

        self.assertIsNone(repo.update_riga.call_args.kwargs["prezzo_unitario"])
