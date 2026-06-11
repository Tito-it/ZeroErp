# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per pratiche_service (flussi, prerequisiti,
#        handler dispatch, canali).
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PraticheServiceFlussiTests.test_crea_flusso_ok
2) PraticheServiceFlussiTests.test_crea_flusso_errore_pratica_id_zero
3) PraticheServiceFlussiTests.test_avvia_flusso_ok
4) PraticheServiceFlussiTests.test_avvia_flusso_errore_id_zero
5) PraticheServiceFlussiTests.test_completa_flusso_ok
6) PraticheServiceFlussiTests.test_completa_flusso_errore_esito_non_valido
7) PraticheServiceFlussiTests.test_cambia_stato_flusso_ok
8) PraticheServiceFlussiTests.test_cambia_stato_flusso_errore_stato_vuoto
9) PraticheServiceFlussiTests.test_verifica_prerequisiti_ok
10) PraticheServiceFlussiTests.test_dispatch_handler_ok
11) PraticheServiceFlussiTests.test_dispatch_handler_template_none
12) PraticheServiceFlussiTests.test_dispatch_handler_info_none
13) PraticheServiceFlussiTests.test_dispatch_handler_key_non_trovata
14) PraticheServiceFlussiTests.test_get_canali_disponibili_ok
15) PraticheServiceFlussiTests.test_dispatch_handler_meta_jsonb_str
16) PraticheServiceFlussiTests.test_coerce_jsonb_dict
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import pratiche_service

_SVC = "apps.pratiche.services.pratiche_service"
_ATOMIC = "django.db.transaction.Atomic"


def _mock_flusso_row(flusso_id: int = 1, *, template_flusso_id: int | None = 10) -> dict:
    """Genera una FlussoRow fittizia per i test."""
    return {
        "id": flusso_id,
        "pratica_id": 1,
        "template_flusso_id": template_flusso_id,
        "stato_id": 1,
        "flusso_padre_id": None,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "sequenza": 0,
        "esito": None,
        "note_esito": None,
        "data_scadenza": None,
        "meta": {"chiave": "valore"},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "test_user",
    }


class PraticheServiceFlussiTests(SimpleTestCase):

    # Scopo: Disabilita transaction.atomic per tutti i test (no DB reale).
    def setUp(self) -> None:
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    # Scopo: Verifica creazione flusso con stato iniziale DA_ESEGUIRE.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_flusso_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.resolve_stato_flusso.return_value = 2
        repo.create_flusso.return_value = 99

        result = pratiche_service.crea_flusso(pratica_id=1, template_flusso_id=10)

        self.assertEqual(result, 99)
        repo.resolve_stato_flusso.assert_called_once_with("DA_ESEGUIRE")
        repo.create_flusso.assert_called_once()

    # Scopo: Verifica errore se pratica_id <= 0.
    def test_crea_flusso_errore_pratica_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_flusso(pratica_id=0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica transizione flusso DA_ESEGUIRE → IN_CORSO.
    @patch(f"{_SVC}.PraticheRepository")
    def test_avvia_flusso_ok(self, MockRepo):
        repo = MockRepo.return_value
        # Flusso senza handler (template None): avvia esegue solo IN_CORSO;
        # dispatch_handler ritorna None e non completa il flusso.
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=None)

        pratiche_service.avvia_flusso(1)

        repo.update_stato_flusso.assert_called_once_with(1, "IN_CORSO")

    # Scopo: Verifica errore se flusso_id <= 0 in avvio.
    def test_avvia_flusso_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.avvia_flusso(0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica completamento flusso con esito POSITIVO.
    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.completa_flusso(1, esito="POSITIVO", note_esito="Tutto ok")

        repo.update_stato_flusso.assert_called_once_with(
            1, "COMPLETATO", esito="POSITIVO", note_esito="Tutto ok",
        )

    # Scopo: Verifica errore con esito non valido.
    def test_completa_flusso_errore_esito_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.completa_flusso(1, esito="INVALIDO")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

    # Scopo: Verifica transizione generica di stato flusso.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_flusso_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.cambia_stato_flusso(1, "SOSPESO")

        repo.update_stato_flusso.assert_called_once_with(
            1, "SOSPESO", esito=None, note_esito=None,
        )

    # Scopo: Verifica errore se nuovo_stato e' vuoto.
    def test_cambia_stato_flusso_errore_stato_vuoto(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_flusso(1, "")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

    # Scopo: Verifica check prerequisiti delegato al repository.
    @patch(f"{_SVC}.PraticheRepository")
    def test_verifica_prerequisiti_ok(self, MockRepo):
        repo = MockRepo.return_value
        prerequisiti = [
            {"prerequisito_id": 1, "codice": "DOC_IDENTITA", "descrizione": "Doc", "soddisfatto": True},
        ]
        repo.check_prerequisiti.return_value = prerequisiti

        result = pratiche_service.verifica_prerequisiti(1, 10)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["soddisfatto"])

    # Scopo: Verifica dispatch handler con handler trovato e eseguito.
    @patch("apps.pratiche.services.handler_registry.get_handler")
    @patch(f"{_SVC}.PraticheRepository")
    def test_dispatch_handler_ok(self, MockRepo, mock_get_handler):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=10)
        repo.get_handler_info.return_value = ("APPUNTAMENTO", {"invio_sms": True})

        handler_instance = MagicMock()
        handler_instance.execute.return_value = {"risultato": "ok"}
        handler_class = MagicMock(return_value=handler_instance)
        mock_get_handler.return_value = handler_class

        result = pratiche_service.dispatch_handler(1)

        self.assertEqual(result, {"risultato": "ok"})
        handler_instance.execute.assert_called_once_with(
            flusso_id=1, pratica_id=1, meta={"chiave": "valore"},
            handler_params={"invio_sms": True}, user=None,
        )

    # Scopo: Regressione bug smoke 2026-06-11 — psycopg puo' restituire i
    # jsonb come str: meta del flusso str deve arrivare all'handler come dict
    # (l'handler fa meta.get). Il coerce di handler_params vive nel repo
    # (get_handler_info), quello del meta nel dispatch.
    @patch("apps.pratiche.services.handler_registry.get_handler")
    @patch(f"{_SVC}.PraticheRepository")
    def test_dispatch_handler_meta_jsonb_str(self, MockRepo, mock_get_handler):
        repo = MockRepo.return_value
        flusso = _mock_flusso_row(1, template_flusso_id=10)
        flusso["meta"] = '{"competenza_fatturazione": "2026-09-01"}'
        repo.get_flusso.return_value = flusso
        repo.get_handler_info.return_value = (
            "vendita.push_preventivo", {"modalita_fatturazione": "IMMEDIATA"},
        )

        handler_instance = MagicMock()
        handler_instance.execute.return_value = {"risultato": "ok"}
        mock_get_handler.return_value = MagicMock(return_value=handler_instance)

        pratiche_service.dispatch_handler(1)

        handler_instance.execute.assert_called_once_with(
            flusso_id=1, pratica_id=1,
            meta={"competenza_fatturazione": "2026-09-01"},
            handler_params={"modalita_fatturazione": "IMMEDIATA"}, user=None,
        )

    # Scopo: Coercion jsonb difensiva — str valida -> dict; str invalida,
    # None, list -> {} (mai scartare un dict, mai propagare non-dict).
    def test_coerce_jsonb_dict(self):
        from apps.pratiche.db.pratiche_repository import coerce_jsonb_dict

        self.assertEqual(coerce_jsonb_dict('{"a": 1}'), {"a": 1})
        self.assertEqual(coerce_jsonb_dict({"a": 1}), {"a": 1})
        self.assertEqual(coerce_jsonb_dict("non-json"), {})
        self.assertEqual(coerce_jsonb_dict(None), {})
        self.assertEqual(coerce_jsonb_dict([1, 2]), {})

    # Scopo: Verifica dispatch con template_flusso_id None → ritorna None.
    @patch(f"{_SVC}.PraticheRepository")
    def test_dispatch_handler_template_none(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=None)

        result = pratiche_service.dispatch_handler(1)

        self.assertIsNone(result)

    # Scopo: Verifica dispatch con handler_info None (handler non configurato/inattivo).
    @patch(f"{_SVC}.PraticheRepository")
    def test_dispatch_handler_info_none(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=10)
        repo.get_handler_info.return_value = None

        result = pratiche_service.dispatch_handler(1)

        self.assertIsNone(result)

    # Scopo: Verifica dispatch con handler_key non registrata → ritorna None.
    @patch("apps.pratiche.services.handler_registry.get_handler", return_value=None)
    @patch(f"{_SVC}.PraticheRepository")
    def test_dispatch_handler_key_non_trovata(self, MockRepo, mock_get_handler):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=10)
        repo.get_handler_info.return_value = ("HANDLER_INESISTENTE", {})

        result = pratiche_service.dispatch_handler(1)

        self.assertIsNone(result)

    # Scopo: Verifica lista canali delegata al repository.
    @patch(f"{_SVC}.PraticheRepository")
    def test_get_canali_disponibili_ok(self, MockRepo):
        repo = MockRepo.return_value
        canali = [
            {"id": 1, "codice": "WEB_CLIENTI", "descrizione": "Web", "codice_interno": "WEB_CLIENTI"},
        ]
        repo.get_canali_flusso.return_value = canali

        result = pratiche_service.get_canali_disponibili(10)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["codice"], "WEB_CLIENTI")
