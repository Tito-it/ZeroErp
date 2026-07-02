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
18) PraticheServiceFlussiTests.test_assegna_flusso_operatore_ok
19) PraticheServiceFlussiTests.test_assegna_flusso_reparto_ok
20) PraticheServiceFlussiTests.test_assegna_flusso_de_assegna_null
21) PraticheServiceFlussiTests.test_assegna_flusso_nessun_flag_no_update
22) PraticheServiceFlussiTests.test_assegna_flusso_errore_id_zero
23) PraticheServiceFlussiTests.test_prendi_in_carico_competenza_mancante
24) PraticheServiceFlussiTests.test_prendi_in_carico_non_eligibile
25) PraticheServiceFlussiTests.test_list_operatori_reparto_ok
26) PraticheServiceFlussiTests.test_list_operatori_reparto_errore_id_zero
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import pratiche_service

_SVC = "apps.pratiche.services.pratiche_service"
_ATOMIC = "django.db.transaction.Atomic"


def _mock_flusso_row(
    flusso_id: int = 1,
    *,
    template_flusso_id: int | None = 10,
    modalita_esito: str = "MANUALE",
    esito_default: str | None = None,
) -> dict:
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
        "template_modalita_esito": modalita_esito,
        "template_esito_default": esito_default,
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
        repo.get_flusso_esito_config.return_value = ("MANUALE", None)
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=None)

        pratiche_service.avvia_flusso(1)

        repo.update_stato_flusso.assert_called_once_with(1, "IN_CORSO")

    # Scopo: Verifica errore se flusso_id <= 0 in avvio.
    def test_avvia_flusso_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.avvia_flusso(0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: modalita AUTOMATICO senza handler — avvia+completa con esito_default
    # in un colpo (DA_ESEGUIRE → IN_CORSO → COMPLETATO), senza scelta umana.
    @patch(f"{_SVC}.PraticheRepository")
    def test_avvia_flusso_automatico_senza_handler(self, MockRepo):
        from unittest.mock import call

        repo = MockRepo.return_value
        repo.get_flusso_esito_config.return_value = ("AUTOMATICO", "POSITIVO")
        # dispatch_handler/eventi: nessun handler (template None) → no-op.
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=None)

        pratiche_service.avvia_flusso(1)

        repo.update_stato_flusso.assert_has_calls([
            call(1, "IN_CORSO"),
            call(1, "COMPLETATO", esito="POSITIVO"),
        ])

    # Scopo: AUTOMATICO con handler — la auto-chiusura usa esito_default (NON il
    # vecchio POSITIVO cablato): qui esito_default=PARZIALE → COMPLETATO+PARZIALE.
    @patch("apps.pratiche.services.handler_registry.get_handler")
    @patch(f"{_SVC}.PraticheRepository")
    def test_avvia_flusso_automatico_handler_usa_esito_default(self, MockRepo, mock_get_handler):
        from unittest.mock import call

        repo = MockRepo.return_value
        repo.get_flusso_esito_config.return_value = ("AUTOMATICO", "PARZIALE")
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=9004)
        repo.get_handler_info.return_value = ("vendita.post_smistamento", {})
        repo.get_handler_eventi.return_value = []
        handler_instance = MagicMock()
        handler_instance.execute.return_value = {"risultato": "ok"}
        mock_get_handler.return_value = MagicMock(return_value=handler_instance)

        pratiche_service.avvia_flusso(1)

        repo.update_stato_flusso.assert_has_calls([
            call(1, "IN_CORSO"),
            call(1, "COMPLETATO", esito="PARZIALE"),
        ])
        repo.get_handler_eventi.assert_called_once_with(9004, "COMPLETATO", "PARZIALE")

    # Scopo: MANUALE senza handler — solo IN_CORSO, nessuna auto-chiusura
    # (l'esito lo registra l'operatore dopo). Regressione del comportamento odierno.
    @patch(f"{_SVC}.PraticheRepository")
    def test_avvia_flusso_manuale_non_completa(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso_esito_config.return_value = ("MANUALE", None)
        repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=None)

        pratiche_service.avvia_flusso(1)

        repo.update_stato_flusso.assert_called_once_with(1, "IN_CORSO")

    # Scopo: modalita CONTESTUALE — avvia_e_completa_flusso porta DA_ESEGUIRE →
    # IN_CORSO → COMPLETATO con l'esito scelto dall'operatore, stessa transazione.
    @patch(f"{_SVC}.PraticheRepository")
    def test_avvia_e_completa_flusso_ok(self, MockRepo):
        from unittest.mock import call

        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(
            1, template_flusso_id=None, modalita_esito="CONTESTUALE", esito_default="POSITIVO",
        )
        repo.get_handler_eventi.return_value = []

        pratiche_service.avvia_e_completa_flusso(1, esito="POSITIVO", note_esito="ok", user="op1")

        repo.update_stato_flusso.assert_has_calls([
            call(1, "IN_CORSO"),
            call(1, "COMPLETATO", esito="POSITIVO", note_esito="ok"),
        ])

    # Scopo: CONTESTUALE — esito fuori vocabolario (voce assente a DB) →
    # E_FLUSSO_VALIDATION fail-fast, prima di qualsiasi scrittura.
    @patch(f"{_SVC}.PraticheRepository")
    def test_avvia_e_completa_flusso_esito_non_valido(self, MockRepo):
        MockRepo.return_value.get_esito_flusso_vocabolario.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.avvia_e_completa_flusso(1, esito="INVALIDO")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

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

    # Scopo: Verifica errore con esito fuori vocabolario (voce assente a DB).
    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_errore_esito_non_valido(self, MockRepo):
        MockRepo.return_value.get_esito_flusso_vocabolario.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.completa_flusso(1, esito="INVALIDO")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

    # Scopo: esito disattivato a vocabolario (attivo=false) → non valido.
    @patch(f"{_SVC}.PraticheRepository")
    def test_completa_flusso_errore_esito_disattivato(self, MockRepo):
        MockRepo.return_value.get_esito_flusso_vocabolario.return_value = (False, True)
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.completa_flusso(1, esito="POSITIVO")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

    # Scopo: guard percorso operatore — esito di ramo (is_verdetto=false) →
    # respinto con errore parlante; un verdetto passa.
    @patch(f"{_SVC}.PraticheRepository")
    def test_require_esito_selezionabile_operatore(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_esito_flusso_vocabolario.return_value = (True, False)
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.require_esito_selezionabile_operatore("MERCE_PRESENTE")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")
        repo.get_esito_flusso_vocabolario.return_value = (True, True)
        pratiche_service.require_esito_selezionabile_operatore("POSITIVO")  # nessun errore

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
        repo.get_flusso_esito_config.return_value = ("MANUALE", None)
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
            "vendita.post_smistamento", {"modalita_fatturazione": "IMMEDIATA"},
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

    # -- Assegnazione flusso a operatore/reparto -------------------------

    # Scopo: Assegna un flusso a un operatore (set_risorsa) → update_flusso.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_flusso_operatore_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_flusso(5, risorsa_umana_id=10, set_risorsa=True)

        repo.update_flusso.assert_called_once()
        flusso_id, data = repo.update_flusso.call_args[0]
        self.assertEqual(flusso_id, 5)
        self.assertEqual(data, {"risorsa_umana_id": 10})

    # Scopo: Assegna un flusso a un reparto (set_unita) → update_flusso.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_flusso_reparto_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_flusso(5, unita_organizzativa_id=3, set_unita=True)

        repo.update_flusso.assert_called_once()
        _, data = repo.update_flusso.call_args[0]
        self.assertEqual(data, {"unita_organizzativa_id": 3})

    # Scopo: De-assegnazione esplicita (set_* True con valore None) azzera i campi.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_flusso_de_assegna_null(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_flusso(
            5, risorsa_umana_id=None, set_risorsa=True,
            unita_organizzativa_id=None, set_unita=True,
        )

        _, data = repo.update_flusso.call_args[0]
        self.assertIsNone(data["risorsa_umana_id"])
        self.assertIsNone(data["unita_organizzativa_id"])

    # Scopo: Senza flag set_* (chiave assente nel payload) non si chiama update.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_flusso_nessun_flag_no_update(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_flusso(5, risorsa_umana_id=10)

        repo.update_flusso.assert_not_called()

    # Scopo: Guard flusso_id <= 0.
    def test_assegna_flusso_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.assegna_flusso(0, risorsa_umana_id=10, set_risorsa=True)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: prendi_in_carico — competenza mancante (caso A/D) tradotta via marker.
    @patch(f"{_SVC}.PraticheRepository")
    def test_prendi_in_carico_competenza_mancante(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.prendi_in_carico_flusso.side_effect = DatabaseError(
            "Operatore 10 non abilitato per il flusso 5.",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.prendi_in_carico(5, 10)
        self.assertEqual(ctx.exception.code, "FLUSSI_COMPETENZA_MANCANTE")

    # Scopo: prendi_in_carico — operatore fuori reparto (caso B) → 496 via marker.
    @patch(f"{_SVC}.PraticheRepository")
    def test_prendi_in_carico_non_eligibile(self, MockRepo):
        from django.db import DatabaseError

        repo = MockRepo.return_value
        repo.prendi_in_carico_flusso.side_effect = DatabaseError(
            "Presa in carico non consentita del flusso 5 per l'operatore 10.",
        )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.prendi_in_carico(5, 10)
        self.assertEqual(ctx.exception.code, "FLUSSI_PRESA_NON_ELIGIBILE")

    # Scopo: lista operatori del reparto delegata al repository.
    @patch(f"{_SVC}.PraticheRepository")
    def test_list_operatori_reparto_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.list_operatori_reparto.return_value = [{"id": 1, "display": "Rossi Mario"}]

        result = pratiche_service.list_operatori_reparto(3)

        repo.list_operatori_reparto.assert_called_once_with(3)
        self.assertEqual(result[0]["display"], "Rossi Mario")

    # Scopo: Guard unita_organizzativa_id <= 0 sul lookup operatori.
    def test_list_operatori_reparto_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.list_operatori_reparto(0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")


class CompletaStepPraticaTests(SimpleTestCase):
    """BB motore completa_step_pratica: idempotenza + scelta transizione, guidata
    dal percorso (bivio rev.3, de-dup preventivi/ordini)."""

    @staticmethod
    def _percorso(codice, stato="IN_CORSO", flusso_id=700):
        return [{"template_flusso_codice": codice, "flusso_id": flusso_id,
                 "stato_codice_interno": stato}]

    # Scopo: step non istanziato (assente dal percorso) → flusso_id None, no-op.
    @patch(f"{_SVC}.completa_flusso")
    @patch(f"{_SVC}.PraticheRepository")
    def test_step_non_istanziato(self, MockRepo, mock_completa):
        MockRepo.return_value.get_percorso_pratica.return_value = []
        out = pratiche_service.completa_step_pratica(1, template_codice="SMISTAMENTO", esito="POSITIVO")
        self.assertIsNone(out["flusso_id"])
        self.assertFalse(out["completato"])
        mock_completa.assert_not_called()

    # Scopo: step presente ma non istanziato (flusso_id None) → no-op.
    @patch(f"{_SVC}.completa_flusso")
    @patch(f"{_SVC}.PraticheRepository")
    def test_step_percorribile_non_istanziato(self, MockRepo, mock_completa):
        MockRepo.return_value.get_percorso_pratica.return_value = self._percorso(
            "SMISTAMENTO", flusso_id=None,
        )
        out = pratiche_service.completa_step_pratica(1, template_codice="SMISTAMENTO", esito="POSITIVO")
        self.assertIsNone(out["flusso_id"])
        self.assertFalse(out["completato"])
        mock_completa.assert_not_called()

    # Scopo: step gia' terminale → completato False, nessuna transizione.
    @patch(f"{_SVC}.completa_flusso")
    @patch(f"{_SVC}.PraticheRepository")
    def test_step_terminale_idempotente(self, MockRepo, mock_completa):
        MockRepo.return_value.get_percorso_pratica.return_value = self._percorso(
            "SMISTAMENTO", stato="COMPLETATO",
        )
        out = pratiche_service.completa_step_pratica(1, template_codice="SMISTAMENTO", esito="POSITIVO")
        self.assertEqual(out["flusso_id"], 700)
        self.assertFalse(out["completato"])
        mock_completa.assert_not_called()

    # Scopo: step IN_CORSO → completa_flusso, completato True.
    @patch(f"{_SVC}.completa_flusso")
    @patch(f"{_SVC}.PraticheRepository")
    def test_step_in_corso_completa(self, MockRepo, mock_completa):
        MockRepo.return_value.get_percorso_pratica.return_value = self._percorso(
            "CONFERMA_ORDINE", stato="IN_CORSO",
        )
        out = pratiche_service.completa_step_pratica(
            1, template_codice="CONFERMA_ORDINE", esito="POSITIVO", user="op",
        )
        self.assertTrue(out["completato"])
        mock_completa.assert_called_once_with(700, esito="POSITIVO", user="op")

    # Scopo: step DA_ESEGUIRE → avvia+completa (CONTESTUALE).
    @patch(f"{_SVC}.avvia_e_completa_flusso")
    @patch(f"{_SVC}.completa_flusso")
    @patch(f"{_SVC}.PraticheRepository")
    def test_step_da_eseguire_avvia_e_completa(self, MockRepo, mock_completa, mock_avvia):
        MockRepo.return_value.get_percorso_pratica.return_value = self._percorso(
            "SMISTAMENTO", stato="DA_ESEGUIRE",
        )
        out = pratiche_service.completa_step_pratica(1, template_codice="SMISTAMENTO", esito="MERCE_PRESENTE")
        self.assertTrue(out["completato"])
        mock_avvia.assert_called_once_with(700, esito="MERCE_PRESENTE", user=None)
        mock_completa.assert_not_called()
