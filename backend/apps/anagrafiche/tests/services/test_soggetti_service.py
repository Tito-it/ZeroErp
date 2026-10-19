# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per SoggettiService — validazione, dedup, not found,
#        orchestrazione creazione PF. Mock repository, CI-compatible.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_soggetti_ok — happy path lista
 2) test_get_soggetto_ok — dettaglio con contatti, indirizzi, ruoli
 3) test_get_soggetto_not_found — id inesistente → E_ANAG_NOT_FOUND
 4) test_create_soggetto_pf_ok — creazione PF completa
 5) test_create_soggetto_missing_tipo — tipo mancante → E_ANAG_VALIDAZIONE
 6) test_create_soggetto_pf_missing_cognome — cognome vuoto → E_ANAG_VALIDAZIONE
 7) test_create_soggetto_pf_duplicate_cf — IntegrityError → E_ANAG_DUPLICATO
 8) test_create_soggetto_pg_ok — creazione PG completa (via _create_pg)
 9) test_update_soggetto_ok — aggiorna campi
10) test_update_soggetto_not_found — id inesistente → E_ANAG_NOT_FOUND
11) test_create_contatto_ok — crea contatto
12) test_create_contatto_incompleto — nominativo o tipo mancanti → E_CONTATTO_INCOMPLETO col campo
13) test_update_contatto_not_found — contatto inesistente → E_ANAG_NOT_FOUND
14) test_create_indirizzo_soggetto_ok — crea indirizzo
14-bis) test_create_indirizzo_libero_porta_comune_e_cap — comune e CAP arrivano alla madre
15) test_create_indirizzo_missing_tipo — tipo mancante → E_ANAG_VALIDAZIONE
16) test_assign_ruolo_ok — assegna ruolo
17) test_assign_ruolo_missing_codice — codice vuoto → E_ANAG_VALIDAZIONE
18) test_auto_clone_tipi_obbligatori — gli indirizzi alla madre plurale, copia degli obbligatori accesa di default (2026-10-19)
19) test_no_auto_clone_if_flag_false — auto_clone=False, la madre non copia
20) test_senza_indirizzi_la_madre_non_si_chiama — (era test_ogni_indirizzo_risolve_il_suo_dettaglio: la via e' della madre, pgTAP)
20b) test_via_nuova_incompleta_e_un_400_prima_della_madre — il pre-check resta nel backend
20c) test_auto_clone_non_booleano_e_un_400 — "false" stringa non accende la copia
20d) test_indirizzi_malformati_non_si_scartano — non lista / non oggetto → 400 (prima scartati)
20e) test_fk_dentro_la_madre_e_un_400 — l'integrita' violata nella plurale → E_ANAG_FK
21) test_resolve_filtri_export_label_completo — DEF-1 mapping con search+tipo
22) test_resolve_filtri_export_label_fallback_id — descrizione mancante → id=N
23) test_resolve_filtri_export_label_vuoto — nessun filtro → dict vuoto
24) test_search_ruoli_lookup_ok — happy path + normalizzazione tipo_ruolo upper
25) test_search_ruoli_lookup_q_troppo_corta — q < 2 char → E_ANAG_VALIDAZIONE
26) test_search_ruoli_lookup_limit_cap — limit oltre il max → cap a 50
26-bis) test_search_ruoli_lookup_con_ruolo — con_ruolo arriva al repo, tipo_ruolo resta None
27) test_by_id_ruolo_ok — restore riga ruolo via soggetto_ruolo_id
28) test_by_id_senza_ruolo_ok — restore riga "senza ruolo" via soggetto_id
29) test_by_id_chiavi_entrambe_o_nessuna — 0 o 2 chiavi → E_ANAG_VALIDAZIONE
30) test_by_id_uuid_malformato — soggetto_id non-UUID → E_ANAG_VALIDAZIONE
31) test_by_id_not_found — record inesistente → E_ANAG_NOT_FOUND
32) test_create_soggetto_pf_senza_sesso_non_lo_inventa — sesso assente → None al repository: lo giudica il guard DB
33) test_create_soggetto_pf_passa_dettaglio_e_piva — DI: dettaglio scelto e P.IVA arrivano al repository
34) test_genera_cf_con_sesso_x_rifiutato — il CF codifica solo M/F: con X niente calcolo
35) test_assign_ruolo_con_indirizzi_del_ruolo — gli indirizzi vanno al RUOLO, dalla madre del DB
35-bis) test_indirizzi_ruolo_pre_check_della_via_nuova — via nuova incompleta, non-oggetto, non-lista: 400 prima di scrivere
36) test_assign_ruolo_con_flusso_dedicato_rifiutato — CL/FO/EF/RIS_UMANA → E_ANAG_VALIDAZIONE, rimando al flusso
35) test_update_soggetto_sesso_stessa_forma_della_creazione — «x» → «X», vuoto → None
36) test_create_soggetto_pf_congruenza_cf_legge_il_sesso_normalizzato — « f » su CF maschile → E_ANAG_VALIDAZIONE
37) test_update_soggetto_dati_societari_al_verbo — `dati_societari` al verbo, stato intero; la natura all'UPDATE
38) test_update_soggetto_solo_dati_societari_non_tocca_il_soggetto — niente UPDATE vuoto, il «non trovato» e' del verbo
39) test_update_soggetto_dati_societari_contratto — sezione non oggetto, chiave ignota, tipo errato → E_ANAG_VALIDAZIONE
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.tests.db_error_fakes import SQLSTATE_UNICITA, make_integrity_error

from apps.core.services.service_errors import ServiceError


SOGG_REPO = "apps.anagrafiche.services.soggetti_service.SoggettiRepository"
IND_REPO = "apps.anagrafiche.services.soggetti_service.IndirizziRepository"

FAKE_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"


class TestSoggettiListDetail(TestCase):
    """Test lista e dettaglio soggetti."""

    @patch(SOGG_REPO)
    def test_list_soggetti_ok(self, mock_repo):
        """Happy path: lista soggetti."""
        mock_repo.return_value.list_soggetti.return_value = (
            [{"id": FAKE_UUID, "ragione_sociale_completa": "Rossi Mario"}], 1
        )
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        results, total = SoggettiService().list_soggetti()
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["ragione_sociale_completa"], "Rossi Mario")

    @patch(SOGG_REPO)
    def test_get_soggetto_ok(self, mock_repo):
        """Dettaglio soggetto con contatti, indirizzi, ruoli."""
        repo = mock_repo.return_value
        repo.get_soggetto.return_value = {"id": FAKE_UUID, "cognome": "Rossi"}
        repo.get_soggetto_contatti.return_value = [{"id": 1, "nominativo": "Mario Rossi"}]
        repo.get_soggetto_indirizzi.return_value = []
        repo.get_soggetto_ruoli.return_value = []
        repo.get_dati_societari.return_value = None
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().get_soggetto(FAKE_UUID)
        self.assertEqual(result["cognome"], "Rossi")
        self.assertEqual(len(result["contatti"]), 1)
        # Fase 6 B4: campo non_editable_fields presente, vuoto se senza CF/PIVA
        self.assertEqual(result["non_editable_fields"], [])

    @patch(SOGG_REPO)
    def test_get_soggetto_non_editable_fields_with_cf_and_piva(self, mock_repo):
        """Fase 6 B4: CF e PIVA valorizzati → entrambi non editabili."""
        repo = mock_repo.return_value
        repo.get_soggetto.return_value = {
            "id": FAKE_UUID, "codice_fiscale": "RSSMRA80A01H501Z",
            "partita_iva": "12345678901",
        }
        repo.get_soggetto_contatti.return_value = []
        repo.get_soggetto_indirizzi.return_value = []
        repo.get_soggetto_ruoli.return_value = []
        repo.get_dati_societari.return_value = None
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().get_soggetto(FAKE_UUID)
        self.assertEqual(
            sorted(result["non_editable_fields"]),
            ["codice_fiscale", "partita_iva"],
        )

    @patch(SOGG_REPO)
    def test_get_soggetto_non_editable_fields_only_piva(self, mock_repo):
        """Solo PIVA valorizzata → solo PIVA non editabile (CF resta editable)."""
        repo = mock_repo.return_value
        repo.get_soggetto.return_value = {
            "id": FAKE_UUID, "codice_fiscale": "  ",  # whitespace = non valorizzato
            "partita_iva": "12345678901",
        }
        repo.get_soggetto_contatti.return_value = []
        repo.get_soggetto_indirizzi.return_value = []
        repo.get_soggetto_ruoli.return_value = []
        repo.get_dati_societari.return_value = None
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().get_soggetto(FAKE_UUID)
        self.assertEqual(result["non_editable_fields"], ["partita_iva"])

    @patch(SOGG_REPO)
    def test_get_soggetto_not_found(self, mock_repo):
        """Soggetto inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_soggetto.return_value = None
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().get_soggetto(FAKE_UUID)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestSoggettiCreate(TestCase):
    """Test creazione soggetti."""

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_ok(self, mock_repo):
        """Happy path: crea soggetto PF."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 1,
            "cognome": "Rossi",
            "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
            "sesso": "M",
            "contatto": {"nominativo": "Mario Rossi", "tipo_contatto_id": 1, "email": "m@r.it"},
        })
        self.assertEqual(result["id"], FAKE_UUID)
        repo.crea_soggetto_pf.assert_called_once()
        kwargs = repo.crea_soggetto_pf.call_args.kwargs
        self.assertEqual((kwargs["sesso"], kwargs["tipo_soggetto_dettaglio_id"]), ("M", 1))

    @patch(SOGG_REPO)
    def test_create_soggetto_missing_tipo(self, mock_repo):
        """Tipo mancante → E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({"cognome": "Rossi"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_missing_cognome(self, mock_repo):
        """Cognome vuoto → E_ANAG_VALIDAZIONE."""
        mock_repo.return_value.get_natura_by_tipo_id.return_value = "PF"
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({
                "tipo_soggetto_dettaglio_id": 1,
                "cognome": "",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
                "sesso": "M",
                "contatto": {"nominativo": "Mario Rossi", "tipo_contatto_id": 1},
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_duplicate_cf(self, mock_repo):
        """CF duplicato → E_ANAG_DUPLICATO."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.side_effect = make_integrity_error(SQLSTATE_UNICITA)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({
                "tipo_soggetto_dettaglio_id": 1,
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
                "sesso": "M",
                "contatto": {"nominativo": "Mario Rossi", "tipo_contatto_id": 1},
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_senza_sesso_non_lo_inventa(self, mock_repo):
        """Sesso assente (o vuoto) → None al repository, nessun default e nessun
        controllo: QUANDO serve lo dice la natura, e lo giudica il guard DB
        `trgfn_soggetti_guard_sesso_policy` (brief-db-sesso-senza-default §6).
        Il rifiuto vero lo prova `tests/db/test_soggetti_sesso_policy_db`."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        for sesso in (None, "", "  "):
            with self.subTest(sesso=sesso):
                repo.crea_soggetto_pf.reset_mock()
                SoggettiService().create_soggetto({
                    "tipo_soggetto_dettaglio_id": 1,
                    "cognome": "Rossi",
                    "nome": "Mario",
                    "codice_fiscale": "RSSMRA80A01H501Z",
                    "sesso": sesso,
                    "contatto": {"nominativo": "Mario Rossi", "tipo_contatto_id": 1, "email": "m@r.it"},
                })
                self.assertIsNone(repo.crea_soggetto_pf.call_args.kwargs["sesso"])

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_passa_dettaglio_e_piva(self, mock_repo):
        """Ditta individuale: il dettaglio scelto e la P.IVA arrivano al
        repository. Fino al 2026-10-09 la funzione DB cablava PR e la P.IVA si
        perdeva: la DI nasceva privato."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 2,
            "cognome": "Rossi",
            "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
            "partita_iva": " 01234567890 ",
            "sesso": "x",
            "contatto": {"nominativo": "Mario Rossi", "tipo_contatto_id": 1, "email": "m@r.it"},
        })
        kwargs = repo.crea_soggetto_pf.call_args.kwargs
        self.assertEqual(
            (kwargs["tipo_soggetto_dettaglio_id"], kwargs["partita_iva"], kwargs["sesso"]),
            (2, "01234567890", "X"),
        )

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_congruenza_cf_legge_il_sesso_normalizzato(self, mock_repo):
        """« f » e' F: su un CF maschile la congruenza lo rifiuta. Prima la
        verifica rileggeva il sesso grezzo, « F » non era ne' M ne' F e il
        controllo si saltava in silenzio."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({
                "tipo_soggetto_dettaglio_id": 1,
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
                "sesso": " f ",
                "contatto": {"nominativo": "Mario Rossi", "tipo_contatto_id": 1, "email": "m@r.it"},
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        repo.crea_soggetto_pf.assert_not_called()

    @patch(SOGG_REPO)
    def test_genera_cf_con_sesso_x_rifiutato(self, mock_repo):
        """Il CF codifica solo M e F: con X un calcolo darebbe il CF di un
        uomo, cioe' un sesso inventato."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().genera_cf({
                "cognome": "Rossi", "nome": "Mario", "sesso": "X",
                "comune_nascita_id": 1, "data_nascita": "1980-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_codice_catastale.assert_not_called()

    @patch(SOGG_REPO)
    def test_create_soggetto_pg_ok(self, mock_repo):
        """Happy path: crea soggetto PG."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PG"
        repo.crea_soggetto_pg.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 3,
            "ragione_sociale": "Test SRL",
            "codice_fiscale": "12345678901",
            "contatto": {"nominativo": "Admin", "tipo_contatto_id": 1, "email": "admin@test.it"},
            "dati_societari": {
                "forma_giuridica_id": 4,
                "id_prov_iscri_rea": 1,
                "iscrizione_rea": "MI-123456",
                "capitale_sociale": 10000.00,
            },
        })
        self.assertEqual(result["id"], FAKE_UUID)
        repo.crea_soggetto_pg.assert_called_once()


class TestSoggettiUpdate(TestCase):
    """Test aggiornamento soggetti."""

    @patch(SOGG_REPO)
    def test_update_soggetto_ok(self, mock_repo):
        """Aggiorna campi soggetto."""
        mock_repo.return_value.update_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().update_soggetto(FAKE_UUID, {"cognome": "Bianchi"})
        self.assertTrue(result["updated"])

    @patch(SOGG_REPO)
    def test_update_soggetto_not_found(self, mock_repo):
        """Soggetto inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.update_soggetto.return_value = False
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_soggetto(FAKE_UUID, {"cognome": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(SOGG_REPO)
    def test_update_soggetto_sesso_stessa_forma_della_creazione(self, mock_repo):
        """Il sesso in modifica ha la forma della creazione: «x» e' «X», il
        vuoto e' None. Prima la creazione normalizzava e l'update no: «x»
        finiva nel CHECK `chk_soggetti_sesso` come rifiuto d'integrita'."""
        mock_repo.return_value.update_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        for sesso, atteso in ((" x ", "X"), ("f", "F"), ("  ", None), (None, None)):
            with self.subTest(sesso=sesso):
                SoggettiService().update_soggetto(FAKE_UUID, {"sesso": sesso})
                payload = mock_repo.return_value.update_soggetto.call_args.args[1]
                self.assertEqual(payload["sesso"], atteso)

    @patch(SOGG_REPO)
    def test_update_soggetto_flag_fiscali_ok(self, mock_repo):
        """I0/D8: `split_payment` e `cliente_pa` arrivano al repository.

        ⭐ La sede e' il SOGGETTO e non il ruolo: un ente E' o NON E' una
        Pubblica Amministrazione, e non lo e' per il gas e non per l'acqua.
        Prima stavano su `anagrafiche.clienti`, che e' una riga per fornitura.
        """
        mock_repo.return_value.update_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().update_soggetto(
            FAKE_UUID, {"split_payment": "S", "cliente_pa": "S"},
        )
        self.assertTrue(result["updated"])
        payload = mock_repo.return_value.update_soggetto.call_args.args[1]
        self.assertEqual(payload["split_payment"], "S")
        self.assertEqual(payload["cliente_pa"], "S")

    @patch(SOGG_REPO)
    def test_update_soggetto_flag_fiscali_normalizza(self, mock_repo):
        """Minuscole e spazi sono normalizzati prima dell'UPDATE.

        ⚠️ La colonna e' `character(1)` con CHECK ('S','N'): senza normalizzare,
        una 's' finirebbe a DB come violazione di vincolo invece che come
        valore valido.
        """
        mock_repo.return_value.update_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        originale = {"split_payment": " s "}
        SoggettiService().update_soggetto(FAKE_UUID, originale)
        payload = mock_repo.return_value.update_soggetto.call_args.args[1]
        self.assertEqual(payload["split_payment"], "S")
        # ⭐ Il payload del chiamante NON viene mutato: qui arriva `request.data`
        #   della view, e normalizzarlo sul posto sarebbe un effetto collaterale
        #   che il nome della funzione non annuncia. Su un `QueryDict`
        #   immutabile l'assegnamento avrebbe anche sollevato.
        self.assertEqual(originale, {"split_payment": " s "})

    @patch(SOGG_REPO)
    def test_update_soggetto_flag_fiscali_valore_ignoto(self, mock_repo):
        """Un valore fuori da ('S','N') e' respinto con la SUA classe.

        ⛔ Il guard non e' ridondante rispetto al CHECK a DB: dice quale campo
        e quali valori. Senza, il CHECK uscirebbe come validazione generica
        (`rifiuto_integrita`, dal 2026-10-07; prima `update_with_dedup` lo
        traduceva in «Codice fiscale o partita IVA duplicata», il falso).
        ⭐ E il valore sbagliato non e' innocuo: 'Y' si comporterebbe come «non
        applicare lo split» al primo `= 'S'`, cioe' un errore fiscale silenzioso
        nella direzione peggiore.
        """
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_soggetto(FAKE_UUID, {"split_payment": "Y"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.update_soggetto.assert_not_called()

    @patch(SOGG_REPO)
    def test_update_soggetto_dati_societari_al_verbo(self, mock_repo):
        """Parte B (brief-db-dati-fiscali-e-societari-del-soggetto): la chiave
        `dati_societari` va al verbo DB, STATO INTERO — una chiave assente
        arriva come None — e DOPO l'update del soggetto.

        ⚠️ Che l'ordine sia giusto lo prova il test sul DB vero (natura e forma
        nella stessa PATCH); qui si prova che la natura NON finisce nel verbo
        e i dati societari NON finiscono nell'UPDATE di `soggetti`.
        """
        mock_repo.return_value.update_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().update_soggetto(FAKE_UUID, {
            "tipo_soggetto_dettaglio_id": "4",
            "dati_societari": {
                "forma_giuridica_id": 7, "codice_sdi": " ABC1234 ",
                "destinatario_fe": "c", "capitale_sociale": 1000.5,
                "data_costituzione": "2020-03-15",
            },
        })
        payload = mock_repo.return_value.update_soggetto.call_args.args[1]
        self.assertEqual(payload, {"tipo_soggetto_dettaglio_id": 4})
        kwargs = mock_repo.return_value.scrivi_dati_societari.call_args.kwargs
        self.assertEqual(kwargs["forma_giuridica_id"], 7)
        self.assertEqual(kwargs["codice_sdi"], "ABC1234")
        self.assertEqual(kwargs["destinatario_fe"], "C")
        self.assertEqual(str(kwargs["capitale_sociale"]), "1000.5")
        self.assertEqual(str(kwargs["data_costituzione"]), "2020-03-15")
        # Stato intero: cio' che non c'e' e' None, non «non toccare».
        self.assertIsNone(kwargs["pec_fatturazione"])
        self.assertIsNone(kwargs["iscrizione_rea"])

    @patch(SOGG_REPO)
    def test_update_soggetto_solo_dati_societari_non_tocca_il_soggetto(self, mock_repo):
        """Con i soli dati societari non c'e' un UPDATE vuoto (che direbbe «non
        trovato»): il soggetto inesistente lo dice il verbo."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().update_soggetto(
            FAKE_UUID, {"dati_societari": {"forma_giuridica_id": 7}},
        )
        self.assertTrue(result["updated"])
        mock_repo.return_value.update_soggetto.assert_not_called()
        mock_repo.return_value.scrivi_dati_societari.assert_called_once()

    @patch(SOGG_REPO)
    def test_update_soggetto_dati_societari_contratto(self, mock_repo):
        """Il contratto della sezione: un oggetto, con le sole chiavi del verbo.
        Fuori contratto → 400 E_ANAG_VALIDAZIONE, e niente scrive."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        for sezione in (None, [], "x", {"soggetto_id": FAKE_UUID}, {"forma_giuridica_id": "abc"}):
            with self.subTest(sezione=sezione):
                with self.assertRaises(ServiceError) as ctx:
                    SoggettiService().update_soggetto(FAKE_UUID, {"dati_societari": sezione})
                self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.update_soggetto.assert_not_called()
        mock_repo.return_value.scrivi_dati_societari.assert_not_called()


class TestSoggettiContatti(TestCase):
    """Test contatti soggetto."""

    @patch(SOGG_REPO)
    def test_create_contatto_ok(self, mock_repo):
        """Crea contatto."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.crea_contatto.return_value = {"id": 10, "nominativo": "Luigi Verdi"}
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_contatto(
            FAKE_UUID, {"nominativo": "Luigi Verdi", "tipo_contatto_id": 2},
        )
        self.assertEqual(result["nominativo"], "Luigi Verdi")
        self.assertEqual(repo.crea_contatto.call_args.kwargs["tipo_contatto_id"], 2)

    @patch(SOGG_REPO)
    def test_create_contatto_incompleto(self, mock_repo):
        """Nominativo o tipo mancanti → E_CONTATTO_INCOMPLETO col campo da
        accendere, prima del DB (fino al 2026-10-09 il tipo mancante arrivava
        al NOT NULL e usciva `E_DATABASE`)."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        for payload, campo in (
            ({"nominativo": "", "tipo_contatto_id": 2}, "nominativo"),
            ({"nominativo": "Luigi Verdi"}, "tipo_contatto_id"),
        ):
            with self.subTest(campo=campo):
                with self.assertRaises(ServiceError) as ctx:
                    SoggettiService().create_contatto(FAKE_UUID, payload)
                self.assertEqual(ctx.exception.code, "E_CONTATTO_INCOMPLETO")
                self.assertIn(campo, ctx.exception.fields)
        repo.crea_contatto.assert_not_called()

    @patch(SOGG_REPO)
    def test_update_contatto_not_found(self, mock_repo):
        """Contatto inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.update_contatto.return_value = False
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_contatto(999, {"nominativo": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestSoggettiIndirizzi(TestCase):
    """Test indirizzi soggetto."""

    @patch(SOGG_REPO)
    def test_create_indirizzo_soggetto_ok(self, mock_repo):
        """Crea indirizzo soggetto."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.crea_indirizzo_soggetto.return_value = 42
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_indirizzo_soggetto(FAKE_UUID, {
            "tipo_indirizzo_codice": "RES",
            "indirizzo_dettaglio_id": 100,
        })
        self.assertEqual(result["id"], 42)

    @patch(SOGG_REPO)
    def test_create_indirizzo_libero_porta_comune_e_cap(self, mock_repo):
        """L'indirizzo libero del soggetto arriva alla madre com'e', nell'oggetto
        della firma nuova (2026-10-18): la forma estera compresa, vuoti tolti.
        La sua completezza la giudica il guard della tabella."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.crea_indirizzo_soggetto.return_value = 43
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_indirizzo_soggetto(FAKE_UUID, {
            "tipo_indirizzo_codice": "RES", "indirizzo_libero": "Hauptstrasse 5",
            "stato_id": 1, "locality": "Berlin", "postal_code": "10115", "administrative_area": "",
        })
        repo.crea_indirizzo_soggetto.assert_called_once_with(FAKE_UUID, {
            "tipo_indirizzo_codice": "RES", "indirizzo_libero": "Hauptstrasse 5",
            "stato_id": 1, "locality": "Berlin", "postal_code": "10115",
        })

    @patch(SOGG_REPO)
    def test_create_indirizzo_missing_tipo(self, mock_repo):
        """Tipo mancante → E_ANAG_VALIDAZIONE."""
        mock_repo.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_indirizzo_soggetto(FAKE_UUID, {
                "indirizzo_dettaglio_id": 100,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestSoggettiRuoli(TestCase):
    """Test ruoli soggetto."""

    @patch(SOGG_REPO)
    def test_assign_ruolo_ok(self, mock_repo):
        """Assegna ruolo."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.assign_ruolo.return_value = 5
        repo.resolve_tipo_ruolo.return_value = {
            "codice_interno": "VT", "codice": "VETTORE", "descrizione": "Vettore",
        }
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().assign_ruolo(FAKE_UUID, {"codice_ruolo": "VETTORE"})
        self.assertEqual(result["id"], 5)
        # Al DB arriva il codice interno gia' risolto: la risoluzione ha una sede sola.
        repo.assign_ruolo.assert_called_once_with(FAKE_UUID, "VT")
        repo.crea_indirizzo_ruolo.assert_not_called()

    @patch(SOGG_REPO)
    def test_assign_ruolo_con_flusso_dedicato_rifiutato(self, mock_repo):
        """I ruoli con un flusso dedicato non nascono dall'endpoint generico
        (decisione di Tid, 2026-10-09): rifiuto sul campo, nessuna scrittura."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        for codice in ("CL", "FO", "EF", "RIS_UMANA"):
            with self.subTest(codice=codice):
                # Codice e descrizione finti e diversi dal codice interno: il
                # messaggio mostra cio' che viene dal DB, non la chiave.
                repo.resolve_tipo_ruolo.return_value = {
                    "codice_interno": codice, "codice": f"COD_{codice}",
                    "descrizione": f"Descr {codice}",
                }
                with self.assertRaises(ServiceError) as ctx:
                    SoggettiService().assign_ruolo(FAKE_UUID, {"codice_ruolo": codice})
                self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
                self.assertEqual(ctx.exception.context.get("field"), "codice_ruolo")
                self.assertEqual(ctx.exception.context.get("codice_ruolo"), f"COD_{codice}")
                self.assertIn(f"Descr {codice}", ctx.exception.message)
        repo.assign_ruolo.assert_not_called()

    @patch(SOGG_REPO)
    def test_assign_ruolo_con_indirizzi_del_ruolo(self, mock_repo):
        """Gli indirizzi del payload diventano indirizzi DEL RUOLO, scritti dalla
        madre del DB (`fn_crea_indirizzi_ruolo`, che legge il tipo di ruolo e
        clona gli obbligatori mancanti). Fino al 2026-10-09 l'endpoint non li
        accettava; dal 2026-10-18 la matrice non si legge piu' qui."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.assign_ruolo.return_value = 5
        repo.resolve_tipo_ruolo.return_value = {
            "codice_interno": "GE", "codice": "GESTORE", "descrizione": "Gestore",
        }
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().assign_ruolo(FAKE_UUID, {
            "codice_ruolo": "GESTORE",
            "indirizzi": [{"tipo_indirizzo_codice": "SEDELEG", "indirizzo_dettaglio_id": 77, "scala": " "}],
        })
        repo.crea_indirizzi_ruolo.assert_called_once_with(
            5, [{"tipo_indirizzo_codice": "SEDELEG", "indirizzo_dettaglio_id": 77}],
        )

    @patch(SOGG_REPO)
    def test_indirizzi_ruolo_pre_check_della_via_nuova(self, mock_repo):
        """Una via nuova senza comune si ferma prima di scrivere, col messaggio
        per l'operatore; un elemento che non e' un oggetto pure, e un elenco
        che non e' una lista (era un TypeError, cioe' un 500)."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        for indirizzi in (
            [{"tipo_indirizzo_codice": "FATT", "toponomastica_id": 1, "descrizione_via": "Roma", "codice_postale_id": 3}],
            ["FATT"],
            5,
            {"tipo_indirizzo_codice": "FATT"},
        ):
            with self.subTest(indirizzi=indirizzi), self.assertRaises(ServiceError) as ctx:
                SoggettiService().create_indirizzi_ruolo(5, indirizzi)
            self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.crea_indirizzi_ruolo.assert_not_called()

    @patch(SOGG_REPO)
    def test_assign_ruolo_missing_codice(self, mock_repo):
        """Codice vuoto → E_ANAG_VALIDAZIONE."""
        mock_repo.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().assign_ruolo(FAKE_UUID, {"codice_ruolo": ""})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestAutoCloneIndirizzi(TestCase):
    """Gli indirizzi della creazione vanno alla madre plurale del DB
    (`fn_crea_indirizzi_soggetto`): copia degli obbligatori, salto dei tipi
    presenti e via di ogni elemento sono regole sue, provate dal pgTAP
    `anagrafiche/test-indirizzi-singolare-e-plurale-v1`. Qui: che cosa le
    arriva. Dal 2026-10-19 (R-DB-16b); fino ad allora la copia la faceva il
    backend con la matrice letta da `LookupRepository`."""

    _PAYLOAD = {
        "tipo_soggetto_dettaglio_id": 1,
        "cognome": "Rossi", "nome": "Mario",
        "codice_fiscale": "RSSMRA80A01H501Z",
        "sesso": "M",
        "contatto": {"nominativo": "Mario Rossi", "tipo_contatto_id": 1},
    }

    def _repo(self, mock_sogg):
        repo = mock_sogg.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        repo.crea_indirizzi_soggetto.return_value = 2
        return repo

    @patch(SOGG_REPO)
    def test_auto_clone_tipi_obbligatori(self, mock_sogg):
        """auto_clone assente vale vero: la madre copia gli obbligatori. Ogni
        elemento le arriva con la SUA via, le stringhe vuote tolte."""
        repo = self._repo(mock_sogg)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_soggetto({
            **self._PAYLOAD,
            "indirizzi": [
                {"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1, "scala": ""},
                {"tipo_indirizzo_codice": "FATT", "stradario_id": 200, "civico": 9},
            ],
        })
        repo.crea_indirizzi_soggetto.assert_called_once_with(
            FAKE_UUID,
            [
                {"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1},
                {"tipo_indirizzo_codice": "FATT", "stradario_id": 200, "civico": 9},
            ],
            copia_obbligatori=True,
        )
        repo.crea_indirizzo_soggetto.assert_not_called()

    @patch(SOGG_REPO)
    def test_no_auto_clone_if_flag_false(self, mock_sogg):
        """auto_clone=False: la madre non copia."""
        repo = self._repo(mock_sogg)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_soggetto({
            **self._PAYLOAD,
            "indirizzi": [{"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1}],
            "auto_clone": False,
        })
        self.assertIs(repo.crea_indirizzi_soggetto.call_args.kwargs["copia_obbligatori"], False)

    @patch(SOGG_REPO)
    def test_senza_indirizzi_la_madre_non_si_chiama(self, mock_sogg):
        repo = self._repo(mock_sogg)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_soggetto(dict(self._PAYLOAD))
        repo.crea_indirizzi_soggetto.assert_not_called()

    @patch(SOGG_REPO)
    def test_via_nuova_incompleta_e_un_400_prima_della_madre(self, mock_sogg):
        """Il pre-check per l'operatore (`indirizzo_per_madre`) resta: una via
        nuova senza i suoi campi non arriva al DB."""
        repo = self._repo(mock_sogg)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError):
            SoggettiService().create_soggetto({
                **self._PAYLOAD,
                "indirizzi": [{"tipo_indirizzo_codice": "RESID", "civico": 1}],
            })
        repo.crea_indirizzi_soggetto.assert_not_called()

    @patch(SOGG_REPO)
    def test_auto_clone_non_booleano_e_un_400(self, mock_sogg):
        """La stringa "false" non e' un booleano: con `bool(...)` accendeva la copia."""
        repo = self._repo(mock_sogg)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({
                **self._PAYLOAD,
                "indirizzi": [{"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1}],
                "auto_clone": "false",
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        repo.crea_soggetto_pf.assert_not_called()

    @patch(SOGG_REPO)
    def test_indirizzi_malformati_non_si_scartano(self, mock_sogg):
        """Un elenco che non e' una lista, o un elemento che non e' un oggetto, e'
        un 400: fino al 2026-10-19 si scartavano e il soggetto nasceva senza."""
        repo = self._repo(mock_sogg)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        for indirizzi in ({"tipo_indirizzo_codice": "RESID"}, ["RESID"]):
            with self.subTest(indirizzi=indirizzi), self.assertRaises(ServiceError) as ctx:
                SoggettiService().create_soggetto({**self._PAYLOAD, "indirizzi": indirizzi})
            self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        repo.crea_soggetto_pf.assert_not_called()

    @patch(SOGG_REPO)
    def test_fk_dentro_la_madre_e_un_400(self, mock_sogg):
        """Una FK violata dentro la madre plurale e' `E_ANAG_FK`, non un 500."""
        from apps.core.tests.db_error_fakes import SQLSTATE_FK, make_integrity_error
        repo = self._repo(mock_sogg)
        repo.crea_indirizzi_soggetto.side_effect = make_integrity_error(
            SQLSTATE_FK, vincolo="fk_indirizzi_soggetti_stato",
        )
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({
                **self._PAYLOAD,
                "indirizzi": [{"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1}],
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_FK")


class TestResolveFiltriExportLabel(TestCase):
    """DEF-1: traduzione filtri attivi in label leggibili per header export."""

    @patch(SOGG_REPO)
    def test_resolve_filtri_export_label_completo(self, mock_repo):
        """Mapping completo (la ricerca la dichiara `filtri_export_con_ricerca`): tipo_soggetto_dettaglio_id."""
        repo = mock_repo.return_value
        repo.get_tipo_soggetto_dettaglio_descrizione.return_value = "Persona Fisica"

        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().resolve_filtri_export_label(
            tipo_soggetto_dettaglio_id=3,
        )

        self.assertEqual(result, {"Tipo": "Persona Fisica"})
        repo.get_tipo_soggetto_dettaglio_descrizione.assert_called_once_with(3)

    @patch(SOGG_REPO)
    def test_resolve_filtri_export_label_fallback_id(self, mock_repo):
        """Lookup descrizione mancante (id obsoleto): fallback 'id=N'."""
        repo = mock_repo.return_value
        repo.get_tipo_soggetto_dettaglio_descrizione.return_value = None

        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().resolve_filtri_export_label(
            tipo_soggetto_dettaglio_id=999,
        )

        self.assertEqual(result, {"Tipo": "id=999"})

    @patch(SOGG_REPO)
    def test_resolve_filtri_export_label_vuoto(self, mock_repo):
        """Nessun filtro attivo: dict vuoto."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().resolve_filtri_export_label()

        self.assertEqual(result, {})
        mock_repo.return_value.get_tipo_soggetto_dettaglio_descrizione.assert_not_called()


class TestSearchRuoliLookup(TestCase):
    """Test lookup ricco soggetti-ruoli (selezione contesto pratica)."""

    @patch(SOGG_REPO)
    def test_search_ruoli_lookup_ok(self, mock_repo):
        """Happy path: delega al repo con tipo_ruolo normalizzato upper."""
        repo = mock_repo.return_value
        repo.search_ruoli_lookup.return_value = (
            [{
                "soggetto_id": FAKE_UUID, "soggetto_ruolo_id": 7,
                "ruolo_codice": "CL", "ruolo_descrizione": "Cliente",
                "ragione_sociale_completa": "Rossi Mario",
                "id_fiscale": "RSSMRA80A01H501U", "soggetto_codice": "SOG-1",
                "n_billing_account": 2,
            }],
            1,
        )
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().search_ruoli_lookup(
            q="  rossi ", tipo_ruolo="cl", emittente_ids=[5],
        )
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["results"][0]["ruolo_codice"], "CL")
        self.assertEqual(result["limit"], 20)
        repo.search_ruoli_lookup.assert_called_once_with(
            q="rossi", tipo_ruolo="CL", emittente_ids=[5], limit=20,
            con_ruolo=False,
        )

    @patch(SOGG_REPO)
    def test_search_ruoli_lookup_q_troppo_corta(self, mock_repo):
        """q < 2 char solleva E_ANAG_VALIDAZIONE senza chiamare il repo."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().search_ruoli_lookup(q="r")
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.search_ruoli_lookup.assert_not_called()

    @patch(SOGG_REPO)
    def test_search_ruoli_lookup_limit_cap(self, mock_repo):
        """limit oltre il massimo viene cappato a 50."""
        repo = mock_repo.return_value
        repo.search_ruoli_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().search_ruoli_lookup(q="rossi", limit=999)
        self.assertEqual(result["limit"], 50)
        _, kwargs = repo.search_ruoli_lookup.call_args
        self.assertEqual(kwargs["limit"], 50)

    @patch(SOGG_REPO)
    def test_search_ruoli_lookup_con_ruolo(self, mock_repo):
        """con_ruolo arriva al repo, senza restringere il tipo di ruolo."""
        repo = mock_repo.return_value
        repo.search_ruoli_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().search_ruoli_lookup(q="rossi", con_ruolo=True)
        _, kwargs = repo.search_ruoli_lookup.call_args
        self.assertTrue(kwargs["con_ruolo"])
        self.assertIsNone(kwargs["tipo_ruolo"])


class TestGetRuoliLookupById(TestCase):
    """Test restore by-id del lookup contesto pratica."""

    @patch(SOGG_REPO)
    def test_by_id_ruolo_ok(self, mock_repo):
        """Restore riga ruolo via soggetto_ruolo_id."""
        repo = mock_repo.return_value
        repo.get_ruolo_lookup_by_id.return_value = {
            "soggetto_id": FAKE_UUID, "soggetto_ruolo_id": 165,
            "ruolo_codice": "CL", "n_billing_account": 1,
        }
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().get_ruoli_lookup_by_id(soggetto_ruolo_id=165, emittente_ids=[7])
        self.assertEqual(result["ruolo_codice"], "CL")
        # Lo scope arriva al repository: e' li' che decide (D10-bis).
        repo.get_ruolo_lookup_by_id.assert_called_once_with(
            soggetto_ruolo_id=165, soggetto_id=None, emittente_ids=[7],
        )

    @patch(SOGG_REPO)
    def test_by_id_senza_ruolo_ok(self, mock_repo):
        """Restore riga 'senza ruolo' via soggetto_id (UUID)."""
        repo = mock_repo.return_value
        repo.get_ruolo_lookup_by_id.return_value = {
            "soggetto_id": FAKE_UUID, "soggetto_ruolo_id": None,
            "ruolo_codice": None, "n_billing_account": 0,
        }
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().get_ruoli_lookup_by_id(soggetto_id=FAKE_UUID, emittente_ids=None)
        self.assertIsNone(result["soggetto_ruolo_id"])

    @patch(SOGG_REPO)
    def test_by_id_chiavi_entrambe_o_nessuna(self, mock_repo):
        """Zero o due chiavi → E_ANAG_VALIDAZIONE (esattamente una richiesta)."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().get_ruoli_lookup_by_id(emittente_ids=None)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        with self.assertRaises(ServiceError):
            SoggettiService().get_ruoli_lookup_by_id(
                soggetto_ruolo_id=1, soggetto_id=FAKE_UUID, emittente_ids=None,
            )
        mock_repo.return_value.get_ruolo_lookup_by_id.assert_not_called()

    @patch(SOGG_REPO)
    def test_by_id_uuid_malformato(self, mock_repo):
        """soggetto_id non-UUID → E_ANAG_VALIDAZIONE prima del repo."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().get_ruoli_lookup_by_id(soggetto_id="non-un-uuid", emittente_ids=None)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_ruolo_lookup_by_id.assert_not_called()

    @patch(SOGG_REPO)
    def test_by_id_not_found(self, mock_repo):
        """Record inesistente o fuori scope → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_ruolo_lookup_by_id.return_value = None
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().get_ruoli_lookup_by_id(soggetto_ruolo_id=999, emittente_ids=[7])
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")
