# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test ordini_service (mock repository, no DB). Valida i guard di
#        stato/not-found, la derivazione soggetto_ruolo dal BA in create, e la
#        traduzione errori DB di _db_errors (IntegrityError -> codice vincolo;
#        DatabaseError trigger -> estrazione codice E_*).
# ------------------------------------------------------------

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
