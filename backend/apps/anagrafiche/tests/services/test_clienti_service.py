# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per ClientiService — creazione manuale,
#        creazione con entita' pre-esistenti, validazioni, guard utility.
#        Mock repository, CI-compatible (no DB reale).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_clienti_ok — happy path lista paginata
 2) test_get_cliente_ok — dettaglio completo
 3) test_get_cliente_not_found — id inesistente → E_ANAG_NOT_FOUND
 3a) test_get_cliente_propagates_evento_stato_corrente — Fase 4: fn DB risolve sosp/riatt
 3b) test_get_cliente_evento_stato_null_when_no_dates — entrambe NULL → output NULL
 4) test_crea_cliente_manuale_ok — creazione manuale dalla madre (fn_crea_cliente: istanza + BA nuovi)
 5) test_crea_cliente_manuale_con_indirizzo — creazione manuale con indirizzo facoltativo
 6) test_crea_cliente_manuale_utility_pdp_bloccata — utility richiede_pdp=true → errore
 7) test_crea_cliente_con_istanza_preesistente — riusa istanza da pratiche
 8) test_crea_cliente_con_istanza_e_ba_preesistenti — riusa istanza + BA da pratiche
 8b) test_crea_cliente_con_ba_preesistente_senza_istanza — l'istanza e' quella del BA (2026-10-18)
 9) test_crea_cliente_istanza_soggetto_mismatch — istanza di altro soggetto → errore
10) test_crea_cliente_ba_istanza_mismatch — BA di altra istanza → errore
10b) test_crea_cliente_ba_altra_utility — BA di altra utility → errore
10c) test_crea_cliente_coppia_con_ba_esistente — la coppia ha gia' il BA → E_ANAG_DUPLICATO
11) test_crea_cliente_missing_soggetto — soggetto_id mancante → errore
12) test_crea_cliente_missing_utility — utility_id mancante → errore
13) test_crea_cliente_utility_non_trovata — utility inesistente → errore
14) test_crea_cliente_duplicato_billing_account — IntegrityError UNIQUE BA (un cliente per BA) → E_ANAG_DUPLICATO
15) test_update_cliente_ok — aggiorna campi editabili
16) test_update_cliente_not_found — id inesistente → E_ANAG_NOT_FOUND
17) test_update_cliente_no_fields — nessun campo → E_ANAG_VALIDAZIONE
17b) test_update_cliente_chiave_estranea_400 — chiave fuori contratto → 400 prima del repository (2026-09-26)
18) test_guard_admin_globale_blocca_creazione_ba — admin globale + emittenti → E_BA_ADMIN_GLOBALE_VIETATO
19) test_guard_skip_quando_auth_user_id_none — contesto sistema → no check
20) test_guard_skip_quando_ba_preesistente — riuso BA → no check (no nuovo INSERT)
21) test_guard_passa_per_operatore_di_emittente — operatore con emittente → ok
22) test_db_trigger_error_propaga_codice — errore trigger DB propagato come ServiceError
23) test_crea_cliente_con_ba_categoria — F2-BE-04: ba_categoria_cliente_id passato al repo
24) test_crea_cliente_senza_ba_categoria_errore — F3-FE-04: categoria obbligatoria, no default
25) test_update_cliente_solo_categoria — F2-BE-04: PATCH solo ba_categoria_cliente_id -> update BA
26) test_update_cliente_categoria_e_campi — F2-BE-04: PATCH misto BA + cliente
27) test_update_cliente_categoria_invalida_zero — F2-BE-04: ba_categoria_cliente_id=0 -> VALIDAZIONE
28) test_update_cliente_categoria_invalida_bool — F2-BE-04: ba_categoria_cliente_id=True -> VALIDAZIONE
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError


CLI_REPO = "apps.anagrafiche.services.clienti_service.ClientiRepository"

FAKE_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"

# --- Fixture helpers ---

def _utility_manifatturiero():
    return {"id": 10, "descrizione": "Manifatturiero", "codice": "MANIF", "richiede_pdp": False}

def _utility_gas():
    return {"id": 1, "descrizione": "Gas", "codice": "GAS", "richiede_pdp": True}

# ⚠️ La forma di `ClientiRepository.get_istanza`: niente `utility_id`, che su
#    `istanze_utilities` non esiste (la utility e' del BA). Fino al 2026-10-08 il
#    mock la portava e il repository la chiedeva al DB: 500 vero, test verde.
def _istanza(soggetto_id=FAKE_UUID):
    return {"id": 100, "soggetto_id": soggetto_id,
            "fittizia": True, "indirizzo_dettaglio_id": None}

def _billing_account(istanza_utility_id=100, utility_id=10):
    return {"id": 200, "istanza_utility_id": istanza_utility_id,
            "soggetto_ruolo_id": 50, "utility_id": utility_id, "codice": "BA-001"}

def _base_payload(**overrides):
    # F3-FE-04: ba_categoria_cliente_id obbligatorio quando si crea un nuovo
    # BA (no default implicito). Le fixture includono un valore fittizio;
    # i test che riusano un BA pre-esistente possono ometterlo via override.
    payload = {
        "soggetto_id": FAKE_UUID,
        "utility_id": 10,
        "ba_categoria_cliente_id": 1,
    }
    payload.update(overrides)
    return payload


# =================================================================
# Lista e dettaglio
# =================================================================

class TestClientiListDetail(TestCase):

    @patch(CLI_REPO)
    def test_list_clienti_ok(self, mock_repo):
        """Happy path: lista paginata clienti."""
        mock_repo.return_value.list_clienti.return_value = (
            [{"id": 1, "ragione_sociale_completa": "Rossi Mario", "codice": "BA-001"}], 1
        )
        from apps.anagrafiche.services.clienti_service import ClientiService
        results, total = ClientiService().list_clienti()
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["codice"], "BA-001")

    @patch(CLI_REPO)
    def test_list_clienti_propaga_scope_emittente(self, mock_repo):
        """Refactor operatore-emittenti BE-3.5: il param emittente_ids
        passato al service deve raggiungere il repository senza
        modifiche (lista bigint[] o None)."""
        mock_repo.return_value.list_clienti.return_value = ([], 0)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().list_clienti(emittente_ids=[10, 20])
        kwargs = mock_repo.return_value.list_clienti.call_args.kwargs
        self.assertEqual(kwargs["emittente_ids"], [10, 20])

    @patch(CLI_REPO)
    def test_list_clienti_scope_none_bypass(self, mock_repo):
        """Superuser/admin globale: emittente_ids=None passa intatto
        e il repository non applica filtro scope."""
        mock_repo.return_value.list_clienti.return_value = ([], 0)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().list_clienti(emittente_ids=None)
        kwargs = mock_repo.return_value.list_clienti.call_args.kwargs
        self.assertIsNone(kwargs["emittente_ids"])

    @patch(CLI_REPO)
    def test_get_cliente_ok(self, mock_repo):
        """Dettaglio cliente completo."""
        mock_repo.return_value.get_cliente.return_value = {
            "id": 1, "soggetto_id": FAKE_UUID, "ragione_sociale_completa": "Rossi",
            "ba_codice": "BA-001", "stato_codice_interno": "AT", "stato_codice": "AT",
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().get_cliente(1)
        self.assertEqual(result["ba_codice"], "BA-001")

    @patch(CLI_REPO)
    def test_get_cliente_not_found(self, mock_repo):
        """Cliente inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_cliente.return_value = None
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().get_cliente(999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(CLI_REPO)
    def test_get_cliente_propagates_evento_stato_corrente(self, mock_repo):
        """Fase 4: i campi data_evento_stato/tipo_evento_stato risolti dalla
        fn DB anagrafiche.fn_get_evento_stato_corrente_cliente devono
        arrivare al frontend nel detail (sostituiscono il computed FE
        sosp vs riatt)."""
        mock_repo.return_value.get_cliente.return_value = {
            "id": 1,
            "data_sospensione": "2026-03-10",
            "data_riattivazione": "2026-04-05",
            # Campi risolti dal LATERAL JOIN sulla fn DB:
            "data_evento_stato": "2026-04-05",
            "tipo_evento_stato": "RIATTIVAZIONE",
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().get_cliente(1)
        self.assertEqual(result["data_evento_stato"], "2026-04-05")
        self.assertEqual(result["tipo_evento_stato"], "RIATTIVAZIONE")

    @patch(CLI_REPO)
    def test_get_cliente_evento_stato_null_when_no_dates(self, mock_repo):
        """Cliente senza sosp/riatt → fn DB ritorna (NULL, NULL)."""
        mock_repo.return_value.get_cliente.return_value = {
            "id": 1,
            "data_sospensione": None,
            "data_riattivazione": None,
            "data_evento_stato": None,
            "tipo_evento_stato": None,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().get_cliente(1)
        self.assertIsNone(result["data_evento_stato"])
        self.assertIsNone(result["tipo_evento_stato"])


# =================================================================
# Creazione manuale (genera istanza + BA)
# =================================================================

class TestCreaClienteManuale(TestCase):

    def _setup_repo(self, mock_repo):
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.crea_cliente.return_value = (1, 200, 100, 50)
        return repo

    @patch(CLI_REPO)
    def test_crea_cliente_manuale_ok(self, mock_repo):
        """Creazione manuale: genera istanza fittizia + BA + cliente."""
        repo = self._setup_repo(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(_base_payload())
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["istanza_utility_id"], 100)
        self.assertEqual(result["billing_account_id"], 200)
        # Tutto nuovo: niente BA ne' istanza indicati, i campi del BA nuovo.
        kwargs = repo.crea_cliente.call_args.kwargs
        self.assertIsNone(kwargs["billing_account_id"])
        self.assertIsNone(kwargs["istanza_utility_id"])
        self.assertEqual(kwargs["billing_account"], {"categoria_cliente_id": 1})
        self.assertEqual(kwargs["istanza"], {})
        self.assertIsNone(kwargs["contatto"])
        self.assertEqual(kwargs["indirizzi"], [])

    @patch(CLI_REPO)
    def test_crea_cliente_manuale_con_indirizzo(self, mock_repo):
        """Creazione manuale con indirizzo facoltativo."""
        repo = self._setup_repo(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().crea_cliente(_base_payload(indirizzo_dettaglio_id=42))
        # L'indirizzo va all'istanza fittizia NUOVA, l'unica che lo porta.
        self.assertEqual(repo.crea_cliente.call_args.kwargs["istanza"], {"indirizzo_dettaglio_id": 42})

    @patch(CLI_REPO)
    def test_crea_cliente_senza_iva_id_non_inietta_default(self, mock_repo):
        """I0/D7-bis: il payload senza `iva_id` crea il cliente, e nessuno
        inietta piu' il parametro DEFAULT_IVA_ID.

        ⭐ E' il caso che il difetto rendeva impossibile, ed e' proprio quello
        che il payload NON porta: fino al 2026-08-29 il service riempiva
        `iva_id` da solo perche' la colonna era NOT NULL senza default DB —
        quindi ogni cliente nasceva con un codice IVA che nessuno aveva scelto,
        e dopo il DROP della colonna l'INSERT falliva. Un test che passasse
        `iva_id` esplicito non si accorgerebbe di niente.
        """
        repo = self._setup_repo(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        payload = _base_payload()
        self.assertNotIn("iva_id", payload)
        ClientiService().crea_cliente(payload)
        repo.crea_cliente.assert_called_once()
        kwargs = repo.crea_cliente.call_args.kwargs["campi"]
        for chiave in ("iva_id", "cliente_pa", "split_payment",
                       "codice_cig", "codice_cup", "codice_commessa"):
            self.assertNotIn(chiave, kwargs)
        # Il lettore del parametro non esiste piu': se qualcuno lo reintroduce
        # senza la colonna, l'INSERT torna a fallire.
        # ⚠️ `assert_not_called` e non un `hasattr`: su un MagicMock `hasattr` e'
        #    sempre vero, quindi la clausola sarebbe stata logica morta.
        repo.get_default_iva_id.assert_not_called()

    @patch(CLI_REPO)
    def test_crea_cliente_scarta_le_sei_chiavi_migrate(self, mock_repo):
        """Le sei chiavi di I0/I8 nel payload sono rifiutate (400), non arrivano alla madre.

        ⚠️ Non sono chiavi ignote: sono quelle che il FE ha spedito per mesi.
        Se rientrassero, l'INSERT nominerebbe colonne che non esistono piu' —
        cioe' una 500 su ogni creazione cliente, che e' esattamente il difetto
        che questa slice ha chiuso.
        """
        repo = self._setup_repo(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        # ⛔ Dal 2026-10-20 non sono piu' scartate: sono un 400, come in
        #    modifica. La madre non viene chiamata.
        for chiave, valore in (("iva_id", 5), ("cliente_pa", "S"), ("split_payment", "S"),
                               ("codice_cig", "A1"), ("codice_cup", "B2"), ("codice_commessa", "C3")):
            with self.subTest(chiave=chiave), self.assertRaises(ServiceError) as ctx:
                ClientiService().crea_cliente(_base_payload(**{chiave: valore}))
            self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        repo.crea_cliente.assert_not_called()

    @patch(CLI_REPO)
    def test_crea_cliente_manuale_utility_pdp_bloccata(self, mock_repo):
        """Utility con richiede_pdp=true → creazione manuale bloccata."""
        mock_repo.return_value.get_utility.return_value = _utility_gas()
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload(utility_id=1))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("PDP", ctx.exception.message)


# =================================================================
# Creazione con entita' pre-esistenti (da pratiche)
# =================================================================

class TestCreaClientePreesistenti(TestCase):

    @patch(CLI_REPO)
    def test_crea_cliente_con_istanza_preesistente(self, mock_repo):
        """Riusa istanza da pratiche, genera solo BA + cliente."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_istanza.return_value = _istanza()
        repo.crea_cliente.return_value = (1, 200, 100, 50)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(
            _base_payload(utility_id=1, istanza_utility_id=100))
        self.assertEqual(result["istanza_utility_id"], 100)
        # L'istanza indicata e un BA nuovo su di lei.
        kwargs = repo.crea_cliente.call_args.kwargs
        self.assertEqual(kwargs["istanza_utility_id"], 100)
        self.assertEqual(kwargs["istanza"], {})
        self.assertIsNone(kwargs["billing_account_id"])

    @patch(CLI_REPO)
    def test_crea_cliente_con_istanza_e_ba_preesistenti(self, mock_repo):
        """Riusa istanza + BA da pratiche, genera solo cliente."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_istanza.return_value = _istanza()
        repo.get_billing_account.return_value = _billing_account(utility_id=1)
        repo.crea_cliente.return_value = (1, 200, 100, 50)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(
            _base_payload(utility_id=1, istanza_utility_id=100, billing_account_id=200))
        # BA e istanza indicati: niente campi di un BA nuovo.
        kwargs = repo.crea_cliente.call_args.kwargs
        self.assertEqual((kwargs["billing_account_id"], kwargs["istanza_utility_id"]), (200, 100))
        self.assertEqual((kwargs["billing_account"], kwargs["istanza"]), ({}, {}))
        self.assertEqual(result["id"], 1)

    @patch(CLI_REPO)
    def test_crea_cliente_con_ba_preesistente_senza_istanza(self, mock_repo):
        """BA indicato senza istanza: l'istanza e' quella del BA (la legge la madre).

        Fino al 2026-10-18 il confronto con un'istanza mai indicata (None) lo
        rifiutava come «BA di un'altra istanza», e la utility col PDP come
        «creazione manuale»: il contratto di `fn_crea_cliente` lo ammette.
        """
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_billing_account.return_value = _billing_account(utility_id=1)
        repo.crea_cliente.return_value = (1, 200, 100, 50)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(
            _base_payload(utility_id=1, billing_account_id=200))
        kwargs = repo.crea_cliente.call_args.kwargs
        self.assertEqual((kwargs["billing_account_id"], kwargs["istanza_utility_id"]), (200, None))
        self.assertEqual((kwargs["billing_account"], kwargs["istanza"]), ({}, {}))
        repo.get_istanza.assert_not_called()
        self.assertEqual(result["istanza_utility_id"], 100)


# =================================================================
# Validazione entita' pre-esistenti
# =================================================================

class TestCreaClienteValidazione(TestCase):

    @patch(CLI_REPO)
    def test_crea_cliente_istanza_soggetto_mismatch(self, mock_repo):
        """Istanza di altro soggetto → errore."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_istanza.return_value = _istanza(soggetto_id="altro-uuid")
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(
                _base_payload(utility_id=1, istanza_utility_id=100))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("soggetto", ctx.exception.message)

    @patch(CLI_REPO)
    def test_crea_cliente_ba_istanza_mismatch(self, mock_repo):
        """BA di altra istanza → errore."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_istanza.return_value = _istanza()
        repo.get_billing_account.return_value = _billing_account(istanza_utility_id=999)
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(
                _base_payload(utility_id=1, istanza_utility_id=100, billing_account_id=200))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("billing account", ctx.exception.message)


    @patch(CLI_REPO)
    def test_crea_cliente_ba_altra_utility(self, mock_repo):
        """BA della stessa istanza ma di un'altra utility → errore: la coppia
        (istanza, utility) e' l'identita' del BA."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_istanza.return_value = _istanza()
        repo.get_billing_account.return_value = _billing_account(utility_id=7)
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(
                _base_payload(utility_id=1, istanza_utility_id=100, billing_account_id=200))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("utility", ctx.exception.message)
        repo.crea_cliente.assert_not_called()

    @patch(CLI_REPO)
    def test_crea_cliente_coppia_con_ba_esistente(self, mock_repo):
        """Istanza esistente la cui utility ha gia' il suo BA, senza indicarlo:
        uq_billing_instance_utility → E_ANAG_DUPLICATO, non un 500."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_istanza.return_value = _istanza()
        repo.crea_cliente.side_effect = IntegrityError("uq_billing_instance_utility")
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(
                _base_payload(utility_id=1, istanza_utility_id=100))
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")


# =================================================================
# Validazione input obbligatori
# =================================================================

class TestCreaClienteInputMancanti(TestCase):

    @patch(CLI_REPO)
    def test_crea_cliente_missing_soggetto(self, mock_repo):
        """soggetto_id mancante → errore."""
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente({"utility_id": 10})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(CLI_REPO)
    def test_crea_cliente_missing_utility(self, mock_repo):
        """utility_id mancante → errore."""
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente({"soggetto_id": FAKE_UUID})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(CLI_REPO)
    def test_crea_cliente_utility_non_trovata(self, mock_repo):
        """Utility inesistente → errore."""
        mock_repo.return_value.get_utility.return_value = None
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("Utility", ctx.exception.message)


# =================================================================
# Duplicato
# =================================================================

class TestCreaClienteDuplicato(TestCase):

    @patch(CLI_REPO)
    def test_crea_cliente_duplicato_billing_account(self, mock_repo):
        """UNIQUE billing account violato (un cliente per BA, R-8) → E_ANAG_DUPLICATO."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.crea_cliente.side_effect = IntegrityError("uq_clienti_billing_account")
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")


# =================================================================
# Update cliente
# =================================================================

class TestUpdateCliente(TestCase):

    @patch(CLI_REPO)
    def test_update_cliente_ok(self, mock_repo):
        """Aggiorna campi editabili — happy path (una sola fn madre atomica)."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "utility_id": 10}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": False, "campi_aggiornati": True,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().update_cliente(1, {
            "modalita_pagamento_id": 5, "garanzia_tipo": "F", "garanzia_importo": 500,
        })
        self.assertTrue(result["updated"])
        repo.update_cliente_atomico.assert_called_once_with(
            1,
            ba_categoria_cliente_id=None,
            cliente_fields={
                "modalita_pagamento_id": 5, "garanzia_tipo": "F",
                "garanzia_importo": 500,
            },
        )

    @patch(CLI_REPO)
    def test_update_cliente_not_found(self, mock_repo):
        """Cliente inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_cliente.return_value = None
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(999, {"modalita_pagamento_id": 5})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(CLI_REPO)
    def test_update_cliente_no_fields(self, mock_repo):
        """Nessun campo valido → E_ANAG_VALIDAZIONE (400): il cliente esiste (guard
        get_cliente), quindi 'niente da aggiornare' e' validazione, non not-found."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "utility_id": 10}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": False, "campi_aggiornati": False,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(1, {})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    # ⛔ Dal 2026-09-26 una chiave fuori contratto e' un 400 PARLANTE, prima di
    #    toccare il database: fino a quel giorno il repository la scartava in
    #    silenzio. `stato_cliente_id` e' il caso vero: `ClienteDrawer.vue` lo
    #    spedisce in ogni PATCH, ma non e' un campo editabile (non e' nella
    #    whitelist della fn madre `fn_update_cliente`).
    @patch(CLI_REPO)
    def test_update_cliente_chiave_estranea_400(self, mock_repo):
        """Chiave fuori contratto → E_ANAG_VALIDAZIONE con le chiavi ignote nel contesto."""
        repo = mock_repo.return_value
        from apps.anagrafiche.services.clienti_service import ClientiService
        for chiave in ("campo_ignoto", "stato_cliente_id", "iva_id"):
            with self.subTest(chiave=chiave):
                with self.assertRaises(ServiceError) as ctx:
                    ClientiService().update_cliente(1, {
                        "modalita_pagamento_id": 5, chiave: 1,
                    })
                self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
                self.assertEqual(ctx.exception.context["unknown_keys"], [chiave])
        repo.get_cliente.assert_not_called()
        repo.update_cliente_atomico.assert_not_called()


# =================================================================
# F2-BE-04 — ba_categoria_cliente_id (pricing v5 STADIO 2)
# =================================================================


class TestBaCategoriaF2BE04(TestCase):

    def _setup_crea(self, mock_repo):
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.crea_cliente.return_value = (1, 200, 100, 50)
        return repo

    @patch(CLI_REPO)
    def test_crea_cliente_con_ba_categoria(self, mock_repo):
        """F2-BE-04: ba_categoria_cliente_id del payload passato al repo."""
        repo = self._setup_crea(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().crea_cliente(_base_payload(ba_categoria_cliente_id=7))
        self.assertEqual(
            repo.crea_cliente.call_args.kwargs["billing_account"], {"categoria_cliente_id": 7},
        )

    @patch(CLI_REPO)
    def test_crea_cliente_senza_ba_categoria_errore(self, mock_repo):
        """F3-FE-04: ba_categoria_cliente_id omesso -> E_ANAG_VALIDAZIONE.
        Nessun default implicito: la categoria cliente e' dimensione
        commerciale e deve essere scelta esplicitamente."""
        self._setup_crea(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        payload = {"soggetto_id": FAKE_UUID, "utility_id": 10}
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(payload)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("ba_categoria_cliente_id", ctx.exception.message)

    @patch(CLI_REPO)
    def test_update_cliente_solo_categoria(self, mock_repo):
        """PATCH con solo ba_categoria_cliente_id -> fn madre con categoria, campi vuoti."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": True, "campi_aggiornati": False,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().update_cliente(1, {"ba_categoria_cliente_id": 9})
        self.assertTrue(result["updated"])
        repo.update_cliente_atomico.assert_called_once_with(
            1, ba_categoria_cliente_id=9, cliente_fields={},
        )

    @patch(CLI_REPO)
    def test_update_cliente_categoria_e_campi(self, mock_repo):
        """PATCH misto: categoria BA + campi cliente in un'unica fn madre atomica."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": True, "campi_aggiornati": True,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().update_cliente(1, {
            "ba_categoria_cliente_id": 9,
            "modalita_pagamento_id": 5,
        })
        repo.update_cliente_atomico.assert_called_once()
        kwargs = repo.update_cliente_atomico.call_args.kwargs
        self.assertEqual(kwargs["ba_categoria_cliente_id"], 9)
        # ba_categoria_cliente_id NON deve finire tra i campi cliente.
        self.assertNotIn("ba_categoria_cliente_id", kwargs["cliente_fields"])
        self.assertEqual(kwargs["cliente_fields"]["modalita_pagamento_id"], 5)

    @patch(CLI_REPO)
    def test_update_cliente_categoria_invalida_zero(self, mock_repo):
        """ba_categoria_cliente_id=0 -> E_ANAG_VALIDAZIONE."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(1, {"ba_categoria_cliente_id": 0})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(CLI_REPO)
    def test_update_cliente_categoria_invalida_bool(self, mock_repo):
        """ba_categoria_cliente_id=True rifiutato (bool trap)."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(1, {"ba_categoria_cliente_id": True})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


# =================================================================
# Refactor operatore-emittenti — guard E_BA_ADMIN_GLOBALE_VIETATO
# =================================================================

class TestCreaClienteGuardEmittente(TestCase):
    """Test guard refactor operatore-emittenti (Q6): admin globale
    non puo' creare BA quando esistono emittenti fiscali."""

    def _setup_repo(self, mock_repo, can_create_ba: bool = True):
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.crea_cliente.return_value = (1, 200, 100, 50)
        repo.check_user_can_create_ba.return_value = can_create_ba
        return repo

    @patch(CLI_REPO)
    def test_guard_admin_globale_blocca_creazione_ba(self, mock_repo):
        """Admin globale + emittenti presenti → E_BA_ADMIN_GLOBALE_VIETATO,
        nessuna chiamata alla madre del DB."""
        repo = self._setup_repo(mock_repo, can_create_ba=False)
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload(), auth_user_id=42)
        self.assertEqual(ctx.exception.code, "E_BA_ADMIN_GLOBALE_VIETATO")
        repo.check_user_can_create_ba.assert_called_once_with(42)
        # Early reject: nessuna scrittura DB
        repo.crea_cliente.assert_not_called()

    @patch(CLI_REPO)
    def test_guard_skip_quando_auth_user_id_none(self, mock_repo):
        """Contesto di sistema (auth_user_id=None) → guard skippato,
        creazione procede (defense-in-depth via trigger DB)."""
        repo = self._setup_repo(mock_repo, can_create_ba=False)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(_base_payload(), auth_user_id=None)
        self.assertEqual(result["id"], 1)
        repo.check_user_can_create_ba.assert_not_called()
        repo.crea_cliente.assert_called_once()

    @patch(CLI_REPO)
    def test_guard_skip_quando_ba_preesistente(self, mock_repo):
        """Se billing_account_id e' fornito (riuso da pratiche),
        non si crea un nuovo BA → niente guard."""
        repo = self._setup_repo(mock_repo, can_create_ba=False)
        repo.get_billing_account.return_value = _billing_account()
        repo.get_istanza.return_value = _istanza()
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().crea_cliente(
            _base_payload(istanza_utility_id=100, billing_account_id=200),
            auth_user_id=42,
        )
        # Guard NON deve essere chiamato perche' non si crea nuovo BA
        repo.check_user_can_create_ba.assert_not_called()
        # E nessun BA nuovo perche' si riusa quello fornito
        self.assertEqual(repo.crea_cliente.call_args.kwargs["billing_account"], {})

    @patch(CLI_REPO)
    def test_guard_passa_per_operatore_di_emittente(self, mock_repo):
        """Operatore con riga in user_emittenti_fiscali → check_user_can_create_ba
        ritorna True → creazione BA procede."""
        repo = self._setup_repo(mock_repo, can_create_ba=True)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(_base_payload(), auth_user_id=99)
        self.assertEqual(result["id"], 1)
        repo.check_user_can_create_ba.assert_called_once_with(99)
        repo.crea_cliente.assert_called_once()

    @patch(CLI_REPO)
    def test_db_trigger_error_propaga_codice(self, mock_repo):
        """Se il trigger DB solleva un'eccezione (defense-in-depth oltre
        il guard applicativo), la repository la propaga e il service
        lascia salire al middleware (ApiExceptionMiddleware) che la
        traduce via ErrorTranslator. Test: il side_effect del repo
        viene rilanciato senza essere mascherato."""
        repo = self._setup_repo(mock_repo, can_create_ba=True)
        # Simula il trigger DB che blocca con un'eccezione applicativa
        repo.crea_cliente.side_effect = RuntimeError(
            "ERROR: E_BA_ADMIN_GLOBALE_VIETATO ..."
        )
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(RuntimeError) as ctx:
            ClientiService().crea_cliente(_base_payload(), auth_user_id=99)
        # L'eccezione DB sale invariata; il middleware/translator la
        # estrae come E_BA_ADMIN_GLOBALE_VIETATO via _APP_ERROR_CODE_RE.
        self.assertIn("E_BA_ADMIN_GLOBALE_VIETATO", str(ctx.exception))
