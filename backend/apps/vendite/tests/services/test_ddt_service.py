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
 2) test_cambia_stato_ddt_not_found        — E_DDT_NOT_FOUND se testata None
 3) test_aggiorna_ddt_stato_non_draft      — E_DDT_STATO_TRANSIZIONE se != DRAFT
 4) test_gestisci_riga_stato_non_draft     — E_DDT_STATO_TRANSIZIONE se != DRAFT
 5) test_elimina_riga_stato_non_draft      — E_DDT_STATO_TRANSIZIONE se != DRAFT

DdtCreaTests
 6) test_crea_ddt_deriva_destinatario_da_ba — deriva destinatario dal BA + DRAFT
 7) test_crea_ddt_destinatario_esplicito    — destinatario passato: no lookup BA
 8) test_crea_ddt_senza_destinatario_ne_ba  — E_DDT_VALIDAZIONE

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
17) test_emetti_transita_a_emesso_e_ricarica — cambia_stato(EMESSO) + get_ddt

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
    def test_emetti_transita_a_emesso_e_ricarica(self, repo_cls) -> None:
        # emetti = cambia_stato(EMESSO, guard leggero get_stato_codice) +
        # get_ddt ricaricato UNA volta (numero valorizzato dal trigger DB
        # all'emissione); capabilities/righe_count risolte dal reload.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_ddt.return_value = {
            "stato_codice_interno": "EMESSO", "numero": "DDT0001",
        }
        repo.get_stato_id_by_codice.return_value = 2
        repo.count_righe.return_value = 0
        repo.get_capabilities.return_value = {"stato_codice": "EMESSO"}

        out = ddt_service.emetti(7)

        repo.get_stato_id_by_codice.assert_called_once_with("EMESSO")
        repo.update_stato.assert_called_once_with(7, 2)
        repo.get_ddt.assert_called_once_with(7)
        self.assertEqual(out["numero"], "DDT0001")
        self.assertEqual(out["stato_codice"], "EMESSO")


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
