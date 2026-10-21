# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per pratiche_service (CRUD pratiche).
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PraticheServiceTests.test_crea_pratica_ok
2) PraticheServiceTests.test_crea_pratica_con_contesto_anagrafico
3) PraticheServiceTests.test_crea_pratica_errore_emittente_zero
4) PraticheServiceTests.test_crea_pratica_errore_tipo_prestazione_zero
5) PraticheServiceTests.test_crea_pratica_errore_priorita_zero
5b) PraticheServiceTests.test_crea_pratica_priorita_default_normale
6) PraticheServiceTests.test_crea_pratica_istanza_senza_ruolo_ammessa
6c) PraticheServiceTests.test_crea_pratica_ba_porta_la_sua_istanza
6d) PraticheServiceTests.test_crea_pratica_errore_ba_di_altra_istanza
6b) PraticheServiceTests.test_crea_pratica_errore_istanza_senza_soggetto
7) PraticheServiceTests.test_crea_pratica_errore_ruolo_senza_soggetto
8) PraticheServiceTests.test_aggiorna_pratica_ok
9) PraticheServiceTests.test_aggiorna_pratica_non_trovata
10) PraticheServiceTests.test_aggiorna_pratica_errore_id_zero
10b) PraticheServiceTests.test_aggiorna_pratica_valori_dal_bb
10c) PraticheServiceTests.test_aggiorna_pratica_letture_coincidono_con_whitelist
11) PraticheServiceTests.test_cambia_stato_pratica_ok
12) PraticheServiceTests.test_cambia_stato_pratica_errore_id_zero
13) PraticheServiceTests.test_cambia_stato_pratica_errore_stato_vuoto
14) PraticheServiceTests.test_assegna_pratica_ok
15) PraticheServiceTests.test_assegna_pratica_nessun_dato
16) PraticheServiceTests.test_cerca_pratiche_ok
17) PraticheServiceTests.test_cerca_pratiche_con_search
18) PraticheServiceTests.test_get_giornale_ok
19) PraticheServiceTests.test_crea_pratica_guard_post_attivazione_ok
20) PraticheServiceTests.test_crea_pratica_guard_post_attivazione_rifiuto
21) PraticheServiceTests.test_crea_pratica_guard_pre_attivazione_rifiuto
21b) PraticheServiceTests.test_crea_pratica_guard_saltato_se_flag_uguali_false
22) PraticheServiceTests.test_crea_pratica_guard_universale_bypass
23) PraticheServiceTests.test_cerca_pratiche_lenti_contesto_esclusive
24) PraticheServiceTests.test_cerca_pratiche_lente_ruolo_passata_al_repo
25) PraticheServiceTests.test_cambia_stato_pratica_chiusura_bloccata_485
26) PraticheServiceTests.test_cerca_pratiche_filtri_priorita_risorsa
27) PraticheServiceTests.test_pratica_di_flusso_ok
28) PraticheServiceTests.test_pratica_di_flusso_non_visibile_o_inesistente
29) PraticheServiceTests.test_pratica_di_flusso_id_non_valido
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.tests.db_error_fakes import make_db_error
from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import pratiche_service

# Path base per i mock del servizio.
_SVC = "apps.pratiche.services.pratiche_service"
_ATOMIC = "django.db.transaction.Atomic"


def _mock_pratica_row(pratica_id: int = 1) -> dict:
    """Genera una PraticaRow fittizia per i test (v2 con display fields)."""
    return {
        "id": pratica_id,
        "emittente_fiscale_id": 10,
        "tipo_prestazione_id": 5,
        "soggetto_id": None,
        "soggetto_ruolo_id": None,
        "istanza_utility_id": None,
        "stato_id": 1,
        "priorita_id": 2,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "pratica_padre_id": None,
        "flusso_origine_id": None,
        "canale_origine_id": None,
        "codice": "PRA-0000001",
        "descrizione": "Test pratica",
        "data_apertura": None,
        "data_scadenza": None,
        "meta": {},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "test_user",
        "tipo_prestazione_codice": "MANUTENZIONE",
        "tipo_prestazione_descrizione": "Manutenzione ordinaria",
        "stato_codice_interno": "BOZZA",
        "stato_descrizione": "Bozza",
        "priorita_codice_interno": "NORMALE",
        "priorita_descrizione": "Normale",
        "soggetto_display": None,
        "risorsa_umana_display": None,
        "unita_organizzativa_descrizione": None,
    }


class PraticheServiceTests(SimpleTestCase):

    # Scopo: Disabilita transaction.atomic per tutti i test (no DB reale).
    def setUp(self) -> None:
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    # Scopo: ⭐ «Dove vive questo flusso», dal solo id. Serve al deep-link della
    #        dashboard quando il flusso e' nominato DA FUORI — il bersaglio di
    #        un errore (`E_FLUSSI_*`) porta l'id del flusso e nient'altro.
    @patch(f"{_SVC}.PraticheRepository")
    def test_pratica_di_flusso_ok(self, MockRepo):
        MockRepo.return_value.get_pratica_di_flusso.return_value = 185
        self.assertEqual(pratiche_service.pratica_di_flusso(166), 185)
        MockRepo.return_value.get_pratica_di_flusso.assert_called_once_with(166)

    # Scopo: ⛔ FAIL-CLOSED, ed e' il ramo che conta. La lettura e' agganciata a
    #        `pratiche.pratiche` (che ha la RLS) e non al solo `flussi` (che non
    #        ce l'ha): un flusso fuori perimetro torna None ed e'
    #        indistinguibile da uno che non esiste — che per chi opera e' la
    #        stessa cosa, e per chi non deve vederlo anche.
    @patch(f"{_SVC}.PraticheRepository")
    def test_pratica_di_flusso_non_visibile_o_inesistente(self, MockRepo):
        MockRepo.return_value.get_pratica_di_flusso.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.pratica_di_flusso(999)
        self.assertEqual(ctx.exception.code, "E_FLUSSO_NOT_FOUND")

    # Scopo: Guard sull'id, come ogni altro punto d'ingresso del service.
    @patch(f"{_SVC}.PraticheRepository")
    def test_pratica_di_flusso_id_non_valido(self, MockRepo):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.pratica_di_flusso(0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")
        MockRepo.return_value.get_pratica_di_flusso.assert_not_called()

    # Scopo: Verifica creazione pratica base con tutti i campi obbligatori.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {"pre_attivazione": True, "post_attivazione": True}
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 42

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
            priorita_id=2,
        )
        self.assertEqual(result, 42)
        repo.resolve_stato_pratica.assert_called_once_with("APERTA")
        repo.create_pratica.assert_called_once()

    # Scopo: Verifica errore se emittente_fiscale_id <= 0.
    def test_crea_pratica_errore_emittente_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=0,
                tipo_prestazione_id=5,
                priorita_id=2,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica errore se tipo_prestazione_id <= 0.
    def test_crea_pratica_errore_tipo_prestazione_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=0,
                priorita_id=2,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica errore se priorita_id <= 0.
    def test_crea_pratica_errore_priorita_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=5,
                priorita_id=0,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: priorita_id assente → default NORMALE risolto per codice_interno
    #        (mai id hardcodato).
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_priorita_default_normale(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {"pre_attivazione": True, "post_attivazione": True}
        repo.resolve_stato_pratica.return_value = 1
        repo.resolve_priorita_pratica.return_value = 2
        repo.create_pratica.return_value = 62

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
        )
        self.assertEqual(result, 62)
        repo.resolve_priorita_pratica.assert_called_once_with("NORMALE")
        call_data = repo.create_pratica.call_args[0][0]
        self.assertEqual(call_data["priorita_id"], 2)

    # Scopo: Verifica creazione con contesto anagrafico completo (soggetto + ruolo + istanza).
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_con_contesto_anagrafico(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {"pre_attivazione": True, "post_attivazione": True}
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 50

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
            priorita_id=2,
            soggetto_id="aaa-bbb-ccc",
            soggetto_ruolo_id=100,
            istanza_utility_id=200,
        )
        self.assertEqual(result, 50)
        call_data = repo.create_pratica.call_args[0][0]
        self.assertEqual(call_data["soggetto_ruolo_id"], 100)
        self.assertEqual(call_data["istanza_utility_id"], 200)

    # Scopo: soggetto + istanza senza ruolo → ammesso: il trigger
    #        (trgfn_pratiche_guard_contesto, regole 2 e 4) non pretende il ruolo
    #        accanto all'istanza, e il service non aggiunge regole sue. ⚠️ Non e'
    #        piu' il «prospect puro»: l'istanza nasce col BA e il ruolo CLIENTE
    #        con lei (brief-db-istanza-nasce-col-ba, D-3).
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_istanza_senza_ruolo_ammessa(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {"pre_attivazione": True, "post_attivazione": True}
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 51

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
            priorita_id=2,
            soggetto_id="aaa-bbb-ccc",
            istanza_utility_id=200,
        )
        self.assertEqual(result, 51)
        call_data = repo.create_pratica.call_args[0][0]
        self.assertIsNone(call_data["soggetto_ruolo_id"])
        self.assertEqual(call_data["istanza_utility_id"], 200)

    # Scopo: con il solo BA (il cliente a grana fine, D-9 di
    #        brief-db-istanza-nasce-col-ba) l'istanza della pratica e' la sua, e
    #        il BA arriva all'INSERT.
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository")
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_ba_porta_la_sua_istanza(self, MockRepo, MockBa):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {"pre_attivazione": True, "post_attivazione": True}
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 52
        MockBa.return_value.get_istanza_utility_id.return_value = 200

        pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
            priorita_id=2,
            soggetto_id="aaa-bbb-ccc",
            soggetto_ruolo_id=7,
            billing_account_id=33,
        )
        MockBa.return_value.get_istanza_utility_id.assert_called_once_with(33)
        call_data = repo.create_pratica.call_args[0][0]
        self.assertEqual(call_data["billing_account_id"], 33)
        self.assertEqual(call_data["istanza_utility_id"], 200)

    # Scopo: BA e istanza che non stanno insieme → 400 sul campo del BA, prima
    #        della FK composta fk_pratiche_billing_account_istanza (un 23503).
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository")
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_errore_ba_di_altra_istanza(self, MockRepo, MockBa):
        MockBa.return_value.get_istanza_utility_id.return_value = 200
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=5,
                priorita_id=2,
                soggetto_id="aaa-bbb-ccc",
                soggetto_ruolo_id=7,
                istanza_utility_id=999,
                billing_account_id=33,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")
        MockRepo.return_value.create_pratica.assert_not_called()

    # Scopo: Verifica errore se istanza_utility_id presente senza soggetto_id
    #        (regola sostitutiva del modello a due rami).
    def test_crea_pratica_errore_istanza_senza_soggetto(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=5,
                priorita_id=2,
                istanza_utility_id=200,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica errore se soggetto_ruolo_id presente senza soggetto_id.
    def test_crea_pratica_errore_ruolo_senza_soggetto(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=5,
                priorita_id=2,
                soggetto_ruolo_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica aggiornamento pratica con campi validi.
    @patch(f"{_SVC}.PraticheRepository")
    def test_aggiorna_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = _mock_pratica_row(1)

        pratiche_service.aggiorna_pratica(1, {"descrizione": "Nuova desc"})

        repo.get_pratica.assert_called_once_with(1)
        repo.update_pratica.assert_called_once_with(1, {"descrizione": "Nuova desc"})

    # Scopo: Verifica errore quando la pratica non esiste.
    @patch(f"{_SVC}.PraticheRepository")
    def test_aggiorna_pratica_non_trovata(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.aggiorna_pratica(99, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, "E_PRATICA_NOT_FOUND")

    # Scopo: Verifica errore se pratica_id <= 0 in aggiornamento.
    def test_aggiorna_pratica_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.aggiorna_pratica(0, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: i VALORI della PATCH passano dal BB: illeggibile -> 400 sul campo
    #        senza scrivere, `""` -> NULL, `meta` solo oggetto.
    @patch(f"{_SVC}.PraticheRepository")
    def test_aggiorna_pratica_valori_dal_bb(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = _mock_pratica_row(1)
        for campo, valore in (
            ("data_scadenza", "banana"), ("soggetto_id", "non-uuid"),
            ("risorsa_umana_id", "x"), ("meta", "x"), ("descrizione", 5),
        ):
            with self.subTest(campo=campo), self.assertRaises(ServiceError) as ctx:
                pratiche_service.aggiorna_pratica(1, {campo: valore})
            self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")
            self.assertEqual(ctx.exception.context.get("field"), campo)
        repo.update_pratica.assert_not_called()

        pratiche_service.aggiorna_pratica(1, {"descrizione": "  ", "data_scadenza": None})
        repo.update_pratica.assert_called_once_with(1, {"descrizione": None, "data_scadenza": None})

    # Scopo: ⛔ un campo ammesso dalla whitelist ma senza lettura sparirebbe
    #        dalla PATCH in silenzio: le due mappe devono coincidere.
    def test_aggiorna_pratica_letture_coincidono_con_whitelist(self):
        from apps.pratiche.db.pratiche_repository import PRATICA_UPDATE_SET

        self.assertEqual(set(pratiche_service._LETTURE_PATCH_PRATICA), set(PRATICA_UPDATE_SET))

    # Scopo: Verifica cambio stato pratica con esito positivo.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.cambia_stato_pratica(1, "APERTA")

        # Lo stato l'ha scelto il client: se non esiste e' un 400 sul campo.
        repo.update_stato_pratica.assert_called_once_with(
            1, "APERTA", codice_errore="E_PRATICA_VALIDATION", campo="nuovo_stato",
        )

    # Scopo: D1 — al massimo UNA lente di contesto (ruolo/istanza/interne):
    # due lenti insieme → ServiceError col codice catalogo DB 484.
    def test_cerca_pratiche_lenti_contesto_esclusive(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cerca_pratiche(
                emittente_fiscale_id=1,
                soggetto_ruolo_id=10,
                istanza_utility_id=20,
            )
        # Il codice VIVO, lo stesso del guard DB `fn_lista_pratiche_per_contesto`:
        # fino al 2026-10-21 qui si sollevava la forma senza `E_`, ritirata il
        # 2026-08-05 (brief-be-verifica-documentazione-api §B7).
        self.assertEqual(
            ctx.exception.code, "E_PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI",
        )

    # Scopo: D1 — la lente ruolo viene inoltrata al repository (la verita' del
    # filtro vive nella fn DB fn_lista_pratiche_per_contesto, composta dal repo).
    @patch(f"{_SVC}.PraticheRepository")
    def test_cerca_pratiche_lente_ruolo_passata_al_repo(self, MockRepo):
        repo = MockRepo.return_value
        repo.list_pratiche.return_value = ([], 0)

        pratiche_service.cerca_pratiche(emittente_fiscale_id=1, soggetto_ruolo_id=10)

        kwargs = repo.list_pratiche.call_args.kwargs
        self.assertEqual(kwargs["soggetto_ruolo_id"], 10)
        self.assertIsNone(kwargs["istanza_utility_id"])
        self.assertFalse(kwargs["solo_interne"])

    # Scopo: Fix 2026-06-12 — priorita_id e risorsa_umana_id inoltrati al repo
    # (prima la dashboard li inviava ma view/repo li ignoravano in silenzio).
    @patch(f"{_SVC}.PraticheRepository")
    def test_cerca_pratiche_filtri_priorita_risorsa(self, MockRepo):
        repo = MockRepo.return_value
        repo.list_pratiche.return_value = ([], 0)

        pratiche_service.cerca_pratiche(
            emittente_fiscale_id=1, priorita_id=3, risorsa_umana_id=7,
        )

        kwargs = repo.list_pratiche.call_args.kwargs
        self.assertEqual(kwargs["priorita_id"], 3)
        self.assertEqual(kwargs["risorsa_umana_id"], 7)

    # Scopo: D4 — guard DB chiusura (messaggio 485) tradotto in ServiceError
    # parlante via marker, non E_DATABASE generico.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_pratica_chiusura_bloccata_485(self, MockRepo):

        repo = MockRepo.return_value
        repo.update_stato_pratica.side_effect = make_db_error(
            "Impossibile chiudere la pratica: flussi obbligatori non completati (APPUNTAMENTO).",
            codice="E_PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI",
 )

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_pratica(1, "CHIUSA")
        self.assertEqual(
            ctx.exception.code, "E_PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI",
        )

    # Scopo: Verifica errore se pratica_id <= 0 in cambio stato.
    def test_cambia_stato_pratica_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_pratica(0, "APERTA")
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica errore se nuovo_stato e' vuoto.
    def test_cambia_stato_pratica_errore_stato_vuoto(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_pratica(1, "")
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica assegnazione pratica con risorsa e UO.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_pratica(1, risorsa_umana_id=10, unita_organizzativa_id=20)

        repo.update_pratica.assert_called_once()
        call_data = repo.update_pratica.call_args[0][1]
        self.assertEqual(call_data["risorsa_umana_id"], 10)
        self.assertEqual(call_data["unita_organizzativa_id"], 20)

    # Scopo: Verifica che senza dati di assegnazione non viene chiamato update.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_pratica_nessun_dato(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_pratica(1)

        repo.update_pratica.assert_not_called()

    # Scopo: Verifica delega a repository per ricerca pratiche.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cerca_pratiche_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.list_pratiche.return_value = ([_mock_pratica_row()], 1)

        items, total = pratiche_service.cerca_pratiche(emittente_fiscale_id=10)

        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        repo.list_pratiche.assert_called_once()

    # Scopo: Verifica che il parametro search venga passato al repository.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cerca_pratiche_con_search(self, MockRepo):
        repo = MockRepo.return_value
        repo.list_pratiche.return_value = ([_mock_pratica_row()], 1)

        pratiche_service.cerca_pratiche(emittente_fiscale_id=10, search="PRA-000")

        call_kwargs = repo.list_pratiche.call_args[1]
        self.assertEqual(call_kwargs["search"], "PRA-000")

    # Scopo: Verifica delega a repository per giornale pratica.
    @patch(f"{_SVC}.PraticheRepository")
    def test_get_giornale_ok(self, MockRepo):
        repo = MockRepo.return_value
        giornale_row = {
            "id": 1, "pratica_id": 1, "flusso_id": None,
            "azione": "PRATICA_CREATA", "origine": "SISTEMA",
            "dettaglio": {}, "tx_id": "abc-123",
            "data_insert": "2026-03-04T10:00:00+00:00", "user_insert": "sys",
        }
        repo.get_giornale_pratica.return_value = ([giornale_row], 1)

        items, total = pratiche_service.get_giornale(1, limit=50, offset=0)

        self.assertEqual(total, 1)
        self.assertEqual(items[0]["tx_id"], "abc-123")

    # --- Guard pre/post-attivazione ---

    # Scopo: Tipo con pre/post ENTRAMBI false (es. PREVENTIVI_*) = ammesso
    #        indipendentemente dallo stato BA (anello3 §11.1.3): il guard
    #        viene SALTATO (ha_ba_attivo mai chiamato). Bug 2026-06-11: la
    #        vecchia condizione trattava false/false come "mai ammessa".
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_guard_saltato_se_flag_uguali_false(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {
            "pre_attivazione": False, "post_attivazione": False
        }
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 61

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=9003,
            priorita_id=2,
            soggetto_id="aaa-bbb-ccc",
            soggetto_ruolo_id=64,
        )
        self.assertEqual(result, 61)
        repo.ha_ba_attivo.assert_not_called()

    # Scopo: Tipo post-attivazione + soggetto con BA attivo → OK.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_guard_post_attivazione_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {
            "pre_attivazione": False, "post_attivazione": True
        }
        repo.ha_ba_attivo.return_value = True
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 60

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
            priorita_id=2,
            soggetto_id="aaa-bbb-ccc",
        )
        self.assertEqual(result, 60)

    # Scopo: Tipo post-attivazione + soggetto SENZA BA attivo → errore.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_guard_post_attivazione_rifiuto(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {
            "pre_attivazione": False, "post_attivazione": True
        }
        repo.ha_ba_attivo.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=5,
                priorita_id=2,
                soggetto_id="aaa-bbb-ccc",
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")
        self.assertIn("post-attivazione", ctx.exception.message)

    # Scopo: Tipo pre-attivazione + soggetto CON BA attivo → errore.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_guard_pre_attivazione_rifiuto(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {
            "pre_attivazione": True, "post_attivazione": False
        }
        repo.ha_ba_attivo.return_value = True

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=5,
                priorita_id=2,
                soggetto_id="aaa-bbb-ccc",
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")
        self.assertIn("pre-attivazione", ctx.exception.message)

    # Scopo: Tipo universale (pre=true, post=true) → bypass check BA (niente query).
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_guard_universale_bypass(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_tipo_prestazione_attivazione.return_value = {
            "pre_attivazione": True, "post_attivazione": True
        }
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 70

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
            priorita_id=2,
            soggetto_id="aaa-bbb-ccc",
        )
        self.assertEqual(result, 70)
        # ha_ba_attivo non deve essere chiamato (bypass)
        repo.ha_ba_attivo.assert_not_called()
