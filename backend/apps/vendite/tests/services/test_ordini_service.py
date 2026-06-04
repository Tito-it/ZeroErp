# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test ordini_service (mock repository, no DB). Valida i guard di
#        stato/not-found, la derivazione soggetto_ruolo dal BA in create, e la
#        traduzione errori DB di _db_errors (IntegrityError -> codice vincolo;
#        DatabaseError trigger -> estrazione codice E_*).
# ------------------------------------------------------------

from contextlib import nullcontext
from unittest.mock import patch

from django.db import DatabaseError, IntegrityError
from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.vendite.services import ordini_service
from apps.vendite.services.ordini_service import _db_errors

_REPO = "apps.vendite.services.ordini_service.OrdiniRepository"


class OrdiniServiceGuardsTests(SimpleTestCase):
    """Guard di stato e not-found (mock repository)."""

    @patch(_REPO)
    def test_get_ordine_not_found(self, repo_cls) -> None:
        repo_cls.return_value.get_ordine.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.get_ordine(99)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")

    @patch(_REPO)
    def test_conferma_stato_errato(self, repo_cls) -> None:
        # Ordine gia' CONFERMATO: la conferma non e' ammessa.
        repo_cls.return_value.get_stato_codice.return_value = "CONFERMATO"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(7)
        self.assertEqual(cm.exception.code, "E_ORD_STATO_TRANSIZIONE")

    @patch(_REPO)
    def test_conferma_senza_righe(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = []
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(7)
        self.assertEqual(cm.exception.code, "E_ORD_NESSUNA_RIGA")

    @patch(_REPO)
    def test_conferma_ok_deriva_stato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = [{"id": 1}]
        repo.get_stato_id_by_codice.return_value = 2
        out = ordini_service.conferma(7)
        self.assertEqual(out["stato"], "CONFERMATO")
        repo.update_stato.assert_called_once_with(7, 2)

    @patch(_REPO)
    def test_crea_ordine_deriva_soggetto_ruolo_da_ba(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_soggetto_ruolo_id_by_ba.return_value = 555
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_ordine.return_value = {"id": 7, "uid": "u", "numero": "ORD0007"}
        out = ordini_service.crea_ordine({"billing_account_id": 3, "utility_id": 1})
        self.assertEqual(out["numero"], "ORD0007")
        repo.get_soggetto_ruolo_id_by_ba.assert_called_once_with(3)
        # soggetto_ruolo_id derivato passato a create_ordine
        self.assertEqual(repo.create_ordine.call_args.kwargs["soggetto_ruolo_id"], 555)

    @patch(_REPO)
    def test_crea_ordine_senza_cliente_errore(self, repo_cls) -> None:
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine({"utility_id": 1})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")

    @patch(_REPO)
    def test_aggiorna_ordine_cambio_ba_rifiutato(self, repo_cls) -> None:
        # Cliente immutabile: cambiare billing_account_id su un ordine esistente
        # e' rifiutato (lascerebbe soggetto_ruolo_id stantio).
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_ordine.return_value = {"id": 7, "billing_account_id": 3}
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_ordine(7, {"billing_account_id": 99})
        # Codice dedicato, allineato alla difesa DB lock-columns (DB-ORD-LOCK).
        self.assertEqual(cm.exception.code, "E_ORD_CLIENTE_IMMUTABILE")
        repo.update_ordine.assert_not_called()

    @patch(_REPO)
    def test_aggiorna_ordine_ba_invariato_tollerato(self, repo_cls) -> None:
        # Il form FE puo' reinviare il BA invariato: tollerato, ma escluso
        # dall'UPDATE (non e' nella whitelist). Aggiorna solo gli altri campi.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_ordine.return_value = {"id": 7, "billing_account_id": 3}
        ordini_service.aggiorna_ordine(7, {"billing_account_id": 3, "utility_id": 9})
        kwargs = repo.update_ordine.call_args.kwargs
        self.assertNotIn("billing_account_id", kwargs)
        self.assertEqual(kwargs["utility_id"], 9)

    @patch(_REPO)
    def test_aggiorna_ordine_ba_non_numerico_rifiutato(self, repo_cls) -> None:
        # Input malformato: billing_account_id non numerico -> 422 parlante
        # (E_ORD_VALIDAZIONE), non 500 da int() non gestito.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_ordine(7, {"billing_account_id": "abc"})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        repo.update_ordine.assert_not_called()

    @patch(_REPO)
    def test_aggiorna_ordine_senza_ba_aggiorna(self, repo_cls) -> None:
        # Payload senza billing_account_id: nessun confronto, update diretto.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        ordini_service.aggiorna_ordine(7, {"utility_id": 9})
        repo.get_ordine.assert_not_called()
        repo.update_ordine.assert_called_once()


class OrdiniDbErrorsTests(SimpleTestCase):
    """Traduzione errori DB di _db_errors (il bug originale crashava qui)."""

    def test_integrity_error_unique_mappato(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError(
                    'duplicate key value violates unique constraint '
                    '"uq_ordrig_riga_nr"',
                )
        self.assertEqual(cm.exception.code, "E_VENDITE_DUPLICATO")

    def test_integrity_error_fallback(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError("vincolo sconosciuto xyz")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    def test_database_error_trigger_code_estratto(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise DatabaseError("E_ORDINE_TRANSIZIONE_NON_AMMESSA: dettaglio")
        self.assertEqual(cm.exception.code, "E_ORDINE_TRANSIZIONE_NON_AMMESSA")


_PREV_REPO = "apps.vendite.db.preventivi_repository.PreventiviRepository"
_ATOMIC = "apps.vendite.services.ordini_service.transaction.atomic"


class OrdiniConversioneUpstreamTests(SimpleTestCase):
    """crea_ordine_da_preventivo (§7.4): orchestrazione, mapping, guard."""

    @patch("apps.vendite.services.ordini_service.gestisci_riga")
    @patch("apps.vendite.services.ordini_service.crea_ordine")
    @patch(_REPO)
    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_ok(
        self, prev_cls, ord_cls, crea_mock, gestisci_mock,
    ) -> None:
        prev_cls.return_value.get_preventivo.return_value = {
            "stato_codice_interno": "ACCETTATO",
            "billing_account_id": 10, "utility_id": 5,
            "emittente_fiscale_id": 3, "valuta_id": 1, "termine_pagamento_id": 2,
        }
        prev_cls.return_value.list_righe.return_value = [
            {"attivo": True, "articolo_id": "A1", "quantita": "2",
             "prezzo_unitario": "10", "sconto_percentuale": "5", "iva_id": 1},
            {"attivo": False, "articolo_id": "A2"},  # riga inattiva → saltata
        ]
        crea_mock.return_value = {"id": 7, "uid": "u", "numero": "ORD7"}

        with patch(_ATOMIC, return_value=nullcontext()):
            out = ordini_service.crea_ordine_da_preventivo(99)

        self.assertEqual(out["ordine_id"], 7)
        self.assertEqual(out["numero"], "ORD7")
        self.assertEqual(out["righe_create"], 1)
        self.assertEqual(out["documento_origine"], {"tipo": "PREVENTIVO", "id": 99})
        # header mappato da preventivo
        header = crea_mock.call_args.args[0]
        self.assertEqual(header["billing_account_id"], 10)
        self.assertEqual(header["termine_pagamento_id"], 2)
        # provenienza valorizzata
        ord_cls.return_value.set_documento_origine.assert_called_once_with(
            7, "PREVENTIVO", 99,
        )
        # solo la riga attiva → 1 gestisci_riga; sconto_percentuale → sconto_perc
        self.assertEqual(gestisci_mock.call_count, 1)
        riga_payload = gestisci_mock.call_args.args[1]
        self.assertEqual(riga_payload["articolo_id"], "A1")
        self.assertEqual(riga_payload["sconto_perc"], "5")

    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_stato_non_convertibile(self, prev_cls) -> None:
        prev_cls.return_value.get_preventivo.return_value = {
            "stato_codice_interno": "EMESSO",
        }
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_preventivo(99)
        self.assertEqual(cm.exception.code, "E_ORD_ORIGINE_NON_CONVERTIBILE")

    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_non_trovato(self, prev_cls) -> None:
        prev_cls.return_value.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_preventivo(99)
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
