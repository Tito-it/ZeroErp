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
17) PraticheServiceFlussiTests.test_crea_flusso_non_ripetibile_483
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
            pratiche_service.crea_flusso(pratica_id=0, template_flusso_id=10)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: workflow v2 — template_flusso_id obbligatorio (chiuso il path morto
    # del vecchio "flusso generico"). None o <= 0 → E_FLUSSO_VALIDATION fail-fast.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_flusso_errore_template_obbligatorio(self, MockRepo):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_flusso(pratica_id=1, template_flusso_id=None)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")
        with self.assertRaises(ServiceError) as ctx2:
            pratiche_service.crea_flusso(pratica_id=1, template_flusso_id=0)
        self.assertEqual(ctx2.exception.code, "E_FLUSSO_VALIDATION")
        # Nessun INSERT tentato quando il guard scatta.
        MockRepo.return_value.create_flusso.assert_not_called()

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

    # Scopo: Verifica completamento flusso con esito POSITIVO. Nessun binding
    # evento → dispatch_handler_eventi e' un no-op (get_handler_eventi → []).
    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(1)
        repo.get_handler_eventi.return_value = []

        pratiche_service.completa_flusso(1, esito="POSITIVO", note_esito="Tutto ok")

        repo.update_stato_flusso.assert_called_once_with(
            1, "COMPLETATO", esito="POSITIVO", note_esito="Tutto ok",
        )
        # Dispatch evento COMPLETATO interrogato con l'esito effettivo.
        repo.get_handler_eventi.assert_called_once_with(10, "COMPLETATO", "POSITIVO")

    # Scopo: completamento con binding evento COMPLETATO → l'handler di dominio
    # (es. accetta_preventivo) viene eseguito nella stessa transazione.
    @patch("apps.pratiche.services.handler_registry.get_handler")
    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_dispatch_evento_completato(self, MockRepo, mock_get_handler):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=9003)
        repo.get_handler_eventi.return_value = [("vendita.accetta_preventivo", {"k": "v"})]
        handler_instance = MagicMock()
        mock_get_handler.return_value = MagicMock(return_value=handler_instance)

        pratiche_service.completa_flusso(1, esito="POSITIVO", user="op1")

        repo.get_handler_eventi.assert_called_once_with(9003, "COMPLETATO", "POSITIVO")
        handler_instance.execute.assert_called_once()
        kwargs = handler_instance.execute.call_args.kwargs
        self.assertEqual(kwargs["flusso_id"], 1)
        self.assertEqual(kwargs["pratica_id"], 1)
        self.assertEqual(kwargs["handler_params"], {"k": "v"})
        self.assertEqual(kwargs["user"], "op1")

    # Scopo: binding seedato ma handler non in HANDLER_MAP → fail-fast (non si
    # completa un flusso saltando silenziosamente l'azione di dominio promessa).
    @patch("apps.pratiche.services.handler_registry.get_handler")
    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_handler_non_registrato(self, MockRepo, mock_get_handler):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=9003)
        repo.get_handler_eventi.return_value = [("vendita.ignoto", {})]
        mock_get_handler.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.completa_flusso(1, esito="POSITIVO")
        self.assertEqual(ctx.exception.code, "E_HANDLER_NON_REGISTRATO")

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

    # Scopo: D3 — guard DB ripetibilita' (messaggio 483) sulla creazione
    # flusso tradotto in ServiceError parlante via marker.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_flusso_non_ripetibile_483(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.resolve_stato_flusso.return_value = 1
        repo.create_flusso.side_effect = DatabaseError(
            "Il flusso CONFERMA non e' ripetibile in questa pratica (regola MAI; ultima istanza: COMPLETATO).",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_flusso(pratica_id=1, template_flusso_id=9004)
        self.assertEqual(ctx.exception.code, "PRATICHE_FLUSSO_NON_RIPETIBILE")

    # Scopo: guard pratica terminale (490) sulla creazione flusso → ServiceError
    # parlante via marker.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_flusso_pratica_terminale_490(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.resolve_stato_flusso.return_value = 1
        repo.create_flusso.side_effect = DatabaseError(
            "Impossibile creare un flusso: la pratica e' in stato terminale (ANNULLATA).",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_flusso(pratica_id=1, template_flusso_id=10)
        self.assertEqual(ctx.exception.code, "PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO")

    # Scopo: guard prerequisiti (flusso non ancora eseguibile) sulla creazione
    # flusso → ServiceError parlante invece di E_DATABASE generico.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_flusso_prerequisiti_non_soddisfatti(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.resolve_stato_flusso.return_value = 1
        repo.create_flusso.side_effect = DatabaseError(
            "Prerequisiti non soddisfatti per il template flusso. Mancanti: APPROVAZIONE_CLIENTE.",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_flusso(pratica_id=1, template_flusso_id=10)
        self.assertEqual(ctx.exception.code, "PRATICHE_PREREQUISITI_NON_SODDISFATTI")

    # Scopo: guard pratica terminale (491) sul cambio stato flusso (avvia/
    # completa/cambia_stato) → ServiceError parlante via marker.
    @patch(f"{_SVC}.PraticheRepository")
    def test_avvia_flusso_pratica_terminale_491(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.update_stato_flusso.side_effect = DatabaseError(
            "Impossibile modificare il flusso: la pratica e' in stato terminale (ANNULLATA).",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.avvia_flusso(1)
        self.assertEqual(ctx.exception.code, "PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE")

    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_pratica_terminale_491(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.update_stato_flusso.side_effect = DatabaseError(
            "Impossibile modificare il flusso: la pratica e' in stato terminale (CHIUSA).",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.completa_flusso(1, esito="POSITIVO")
        self.assertEqual(ctx.exception.code, "PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE")

    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_flusso_pratica_terminale_491(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.update_stato_flusso.side_effect = DatabaseError(
            "Impossibile modificare il flusso: la pratica e' in stato terminale (ANNULLATA).",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_flusso(1, "SOSPESO")
        self.assertEqual(ctx.exception.code, "PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE")

    # Scopo: guard chiusura workflow-driven — il flusso di chiusura non puo'
    # completarsi finche' restano obbligatori bloccanti → ServiceError parlante.
    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_chiusura_prematura(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.update_stato_flusso.side_effect = DatabaseError(
            "Impossibile completare il flusso di chiusura: restano altri flussi obbligatori da completare.",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.completa_flusso(1, esito="POSITIVO")
        self.assertEqual(ctx.exception.code, "PRATICHE_CHIUSURA_FLUSSO_PREMATURO")

    # Scopo: guard transizione flusso (matrice config) → ServiceError parlante
    # invece di E_DATABASE 500 (gap ① allineamento marker+policy 2026-06-14).
    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_flusso_transizione_non_ammessa(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.update_stato_flusso.side_effect = DatabaseError(
            "Transizione flusso non ammessa: DA_ESEGUIRE -> COMPLETATO",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_flusso(1, "COMPLETATO", esito="POSITIVO")
        self.assertEqual(ctx.exception.code, "FLUSSI_TRANSIZIONE_NON_AMMESSA")

    # Scopo: guard esito-aware — COMPLETATO senza esito → ServiceError parlante.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_flusso_esito_obbligatorio(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.update_stato_flusso.side_effect = DatabaseError(
            "Esito obbligatorio per completare il flusso 42.",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_flusso(1, "COMPLETATO")
        self.assertEqual(ctx.exception.code, "FLUSSI_ESITO_OBBLIGATORIO")

    # Scopo: guard transizione pratica (matrice config) → ServiceError parlante.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_pratica_transizione_non_ammessa(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.update_stato_pratica.side_effect = DatabaseError(
            "Transizione pratica non ammessa: CHIUSA -> APERTA",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_pratica(1, "APERTA")
        self.assertEqual(ctx.exception.code, "PRATICHE_TRANSIZIONE_NON_AMMESSA")

    # Scopo: i codici workflow guard devono avere policy 409 (conflitto regola
    # business), non finire nel default E_GENERICO (500). Regressione: codici
    # mappati via marker ma non registrati in ErrorPolicyRegistry.
    def test_workflow_guard_codes_hanno_policy_409(self):
        from apps.core.services.error_policies import ErrorPolicyRegistry

        for code in (
            "PRATICHE_PREREQUISITI_NON_SODDISFATTI",
            "PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO",
            "PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE",
            "PRATICHE_CHIUSURA_FLUSSO_PREMATURO",
            "PRATICHE_TRANSIZIONE_NON_AMMESSA",
            "FLUSSI_TRANSIZIONE_NON_AMMESSA",
            "FLUSSI_ESITO_OBBLIGATORIO",
        ):
            self.assertTrue(ErrorPolicyRegistry.has(code), f"{code} non registrato")
            self.assertEqual(ErrorPolicyRegistry.resolve(code).http_status, 409, code)

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
