# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test ddt_service (mock repository, no DB). Clone strutturale di
#        test_ordini_service: valida i guard di stato/not-found, il cliente (BA)
#        facoltativo e le sue copie lasciate al DB (brief-db-esecutivi-ba-coppia
#        §9.6), il gating eliminazione, il cambio stato data-driven (+ emetti),
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
 4) test_gestisci_riga_stato_non_draft     — E_RIGA_DOC_NON_BOZZA se != DRAFT (il codice del DB, frase a catalogo)
 4b) test_gestisci_riga_chiave_ignota_rifiutata — fuori whitelist: 400 prima di leggere (2026-10-19)
 4c) test_gestisci_riga_ammette_componenti_overrides — la mappa degli override non e' una colonna, ma e' ammessa
 4d) test_aggiorna_riga_chiave_ignota_rifiutata — fuori whitelist: 400 prima di leggere (2026-10-19)
 5) test_elimina_riga_stato_non_draft      — E_RIGA_DOC_NON_BOZZA se != DRAFT
 5b) test_update_componente_stato_non_draft — E_RIGA_DOC_NON_BOZZA; l'etichetta prende `numero` dallo scope del componente

DdtCreaTests
 6) test_crea_ddt_col_ba_lascia_le_copie_al_db — col BA destinatario None + DRAFT
 6a) test_crea_ddt_utility_rifiutata         — utility fuori whitelist: 400, non piu' scartata (2026-10-19)
 6b) test_crea_ddt_errore_del_default_sale   — slot di default dal DB: l'errore non si ingoia
 7) test_crea_ddt_destinatario_esplicito    — destinatario passato arriva al repo
 8) test_crea_ddt_senza_destinatario_ne_ba  — nessun guard Python: il NOT NULL lo dice il DB
 8b) test_crea_ddt_senza_ba_ammesso         — bolla senza cliente (terzista, deposito): BA None
 8e) test_crea_ddt_id_non_numerico          — E_DDT_VALIDAZIONE col campo (no 500)
 8c) test_crea_ddt_passa_emittente_payload  — emittente dallo user (payload) → repo kwargs
 8d) test_crea_ddt_emittente_omesso_none    — emittente assente → None (fallback DB dal BA)

DdtAggiornaTests
 9) test_aggiorna_ddt_cambio_ba_in_bozza    — il BA arriva al DB (D-2: si sceglie in bozza)
10) test_aggiorna_ddt_utility_rifiutata     — utility fuori whitelist: 400, non piu' scartata (2026-10-19)
10b) test_aggiorna_ddt_ba_tolto             — BA a None arriva al DB, destinatario intatto
11) test_aggiorna_ddt_ba_non_numerico       — E_DDT_VALIDAZIONE (no 500)

DdtEliminaTests
12) test_elimina_ddt_con_righe_rifiutato    — E_DDT_STATO_TRANSIZIONE
13) test_elimina_ddt_bozza_orfana_ok        — hard-delete ammesso (0 righe)

DdtCambiaStatoTests
14) test_cambia_stato_ok                    — valida il codice, poi il verbo col codice
15) test_cambia_stato_codice_vuoto          — E_DDT_VALIDAZIONE
16) test_cambia_stato_codice_inesistente    — E_DDT_VALIDAZIONE
16b) test_cambia_stato_emesso_rifiutato     — EMESSO solo da «Emetti» (M-2): 400, nessun verbo
17) test_emetti_transita_a_emesso_light      — la stessa transizione a EMESSO, ritorno light (no reload)

DdtCreaDaOrdineTests
18) test_crea_ddt_da_ordine_delega_e_ritorna — push_da_ordine + ritorno mappato
19) test_crea_ddt_da_ordine_default_dopo_la_cascata — slot di default chiesto dopo il verbo
19b) test_crea_ddt_da_ordine_errore_del_default_sale — verbo e default in una transazione

DdtPushCommessaTests
20) test_push_nessuna_riga_pushable          — E_DDT_NESSUNA_RIGA
21) test_push_ok_delega_e_mappa_report        — pr_run_commesse_push_one + report

DdtDbErrorsTests
22) test_integrity_error_fk_mappato          — E_VENDITE_FK
23) test_integrity_error_fallback            — E_VENDITE_VALIDATION
24) test_database_error_trigger_code_estratto — E_STATO_DDT_TRANSIZIONE_NON_VALIDA
24b) test_vincoli_della_coppia_col_campo       — fk_ddt_ba_cliente, chk_ddt_ba_utility_insieme → campo billing_account_id

DdtSatellitiTestataTests (2026-09-21, «leggi prima la testata»)
25) test_list_righe_ddt_non_trovato_e_404        — E_DDT_NOT_FOUND, repo righe non chiamato
26) test_list_riepilogo_iva_ddt_non_trovato_e_404 — idem sul riepilogo IVA
27) test_list_componenti_riga_di_altro_ddt_e_404 — riga di un altro DDT: id incrociato → 404
28) test_list_righe_con_testata_delega_al_repo    — caso felice: delega invariata

DdtRigheEvaseTests (2026-10-11, brief-db-ddt-righe-evase-dall-ordine)
29) test_annullo_passa_dal_verbo_senza_dichiarazione — ANNULLATO → repo.annulla(id, None), mai cambia_stato
30) test_annullo_con_dichiarazione                    — legami_confermati arriva al verbo come int
31) test_annullo_dichiarazione_non_numerica           — E_DDT_VALIDAZIONE col campo (no 500)
32) test_annullo_con_legami_codice_del_db             — E_DOC_ANNULLO_CON_LEGAMI tradotto, confirm_and_retry
33) test_correggi_qta_evasa_delega_al_verbo           — Decimal al repo, qta_evasa nella risposta
34) test_correggi_qta_evasa_qta_mancante              — E_DDT_VALIDAZIONE, verbo non chiamato
35) test_correggi_qta_evasa_riga_di_altro_ddt_e_404   — E_DDT_NOT_FOUND, verbo non chiamato
36) test_get_legami_delega_al_bb                       — testata, poi il BB comune col codice DDT
37) test_get_legami_ddt_non_trovato_e_404             — E_DDT_NOT_FOUND, legami non letti
38) test_get_prelievi_raggruppa_per_voce              — prelievi sotto riga o componente giusti (B1)
39) test_crea_prelievo_porta_la_riga_e_coerce         — riga dall'URL, id interi, qta decimale
40) test_prelievo_di_altra_riga_e_404                 — E_DDT_NOT_FOUND, niente scrittura
"""

from contextlib import nullcontext
from decimal import Decimal
from unittest.mock import patch

from django.db import DatabaseError, IntegrityError
from django.test import SimpleTestCase

from apps.core.tests._helpers.modello_documento_mockato import ModelloDocumentoMockatoMixin
from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.vendite.services import ddt_service
from apps.vendite.services.ddt_service import _db_errors

_REPO = "apps.vendite.services.ddt_service.DdtRepository"
_SVC = "apps.vendite.services.ddt_service"
_ATOMIC = "apps.vendite.services.ddt_service.transaction.atomic"
# pr_run_commesse_push_one e' importato LOCALMENTE dentro push_a_commessa
# (import lazy per evitare cicli): si patcha nel modulo di origine.
_PUSH_ONE = "apps.vendite.services.commesse_service.pr_run_commesse_push_one"


class DdtServiceGuardsTests(SimpleTestCase):
    """Guard di stato (E_DDT_STATO_TRANSIZIONE sulla testata, E_RIGA_DOC_NON_BOZZA
    sulle righe — lo stesso codice del BB a DB, decisione B del 2026-09-22) e
    not-found (E_DDT_NOT_FOUND)."""

    @patch(_REPO)
    def test_get_ddt_not_found(self, repo_cls) -> None:
        repo_cls.return_value.get_ddt.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.get_ddt(99)
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")

    # Scopo: il blob di fn_available_actions_ddt viaggia intatto SOTTO
    #        `capabilities`, e nessuna sua chiave sale nella testata (api.md
    #        §«Il blob sta SOTTO `capabilities`», 2026-09-23). Fino a quel
    #        giorno nessun test del DDT guardava la forma del dettaglio.
    @patch(_REPO)
    def test_get_ddt_capabilities_annidate(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        repo.get_capabilities.return_value = {
            "available_actions": [{"key": "emetti", "target_state": "EMESSO"}],
            "can_edit_testata": True,
            "can_push_commessa": False,
            "can_push_commessa_reason_key": "vendite.ddt.push_commessa_reason.x",
            "stato_codice": "DRAFT",
        }
        repo.count_righe.return_value = 3
        out = ddt_service.get_ddt(7)
        self.assertEqual(out["capabilities"], repo.get_capabilities.return_value)
        for chiave in repo.get_capabilities.return_value:
            self.assertNotIn(chiave, out)
        self.assertEqual(out["righe_count"], 3)

    @patch(_REPO)
    def test_cambia_stato_ddt_not_found(self, repo_cls) -> None:
        # Guard esistenza leggero: stato corrente None -> E_DDT_NOT_FOUND.
        repo_cls.return_value.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(99, "SPEDITO")
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")

    @patch(_REPO)
    def test_aggiorna_ddt_fuori_bozza_decide_il_db(self, repo_cls) -> None:
        # DDT gia' EMESSO: quali colonne si cambiano lo dice il lock di testata
        # del DB, colonna per colonna (brief-db-testata-dopo-emissione, D-0):
        # il service non ha piu' un «solo in DRAFT» e passa la scrittura.
        repo = repo_cls.return_value
        # L'esistenza si legge col lettore leggero; lo stato non ferma niente.
        repo.get_stato_codice.return_value = "EMESSO"
        ddt_service.aggiorna_ddt(7, {"tracking_code": "TRK-1"})
        repo.get_ddt.assert_not_called()
        self.assertEqual(repo.update_ddt.call_args.kwargs, {"tracking_code": "TRK-1"})

    @patch(_REPO)
    def test_gestisci_riga_stato_non_draft(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"numero": "2026/00007", "stato_codice_interno": "EMESSO"}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.gestisci_riga(7, {"articolo_id": "ART1"})
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")
        # La frase e' quella del catalogo, coi tre valori: etichetta, stato, verbo.
        self.assertEqual(
            cm.exception.message,
            "DDT 2026/00007 non e' piu' in bozza (stato EMESSO): le sue righe si "
            "possono aggiungere solo finche' e' in bozza.",
        )
        repo.create_riga.assert_not_called()

    # Scopo: dal 2026-10-19 (scelta di Tid, la regola della testata) una chiave
    #        fuori whitelist della riga e' un 400 con le chiavi ignote, prima di
    #        qualunque lettura; fino ad allora si scartava in silenzio.
    @patch(_REPO)
    def test_gestisci_riga_chiave_ignota_rifiutata(self, repo_cls) -> None:
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            ddt_service.gestisci_riga(7, {"articolo_id": "ART1", "iva_id": 3})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("unknown_keys"), ["iva_id"])
        repo.get_ddt.assert_not_called()
        repo.create_riga.assert_not_called()

    # Scopo: `componenti_overrides` non e' una colonna (si legge a parte) ma e'
    #        ammessa: la validazione la lascia passare, e la chiamata arriva al
    #        guard della bozza.
    @patch(_REPO)
    def test_gestisci_riga_ammette_componenti_overrides(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"numero": "2026/00007", "stato_codice_interno": "EMESSO"}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.gestisci_riga(7, {"articolo_id": "KIT1", "componenti_overrides": {}})
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")

    @patch(_REPO)
    def test_aggiorna_riga_chiave_ignota_rifiutata(self, repo_cls) -> None:
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            ddt_service.aggiorna_riga(7, 3, {"quantita": 2, "articolo_id": "ART2"})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("unknown_keys"), ["articolo_id"])
        repo.get_ddt.assert_not_called()
        repo.update_riga.assert_not_called()

    @patch(_REPO)
    def test_elimina_riga_stato_non_draft(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"stato_codice_interno": "SPEDITO"}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.elimina_riga(7, 3)
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")
        # Senza `numero` (bozza mai numerata, o lettura che non lo porta)
        # l'etichetta ripiega su `#id`, come `fn_get_stato_testata_documento`.
        self.assertTrue(cm.exception.message.startswith("DDT #7 non e' piu' in bozza (stato SPEDITO)"))
        self.assertIn("togliere", cm.exception.message)
        repo.delete_riga.assert_not_called()

    @patch(_REPO)
    def test_update_componente_stato_non_draft(self, repo_cls) -> None:
        # Sui componenti la testata e' lo scope del JOIN, non `get_ddt`: deve
        # portare `numero`, o l'etichetta ripiega su `#id` proprio su un DDT
        # emesso, che il numero ce l'ha sempre — e nessun errore lo direbbe.
        repo = repo_cls.return_value
        repo.load_componente_with_scope.return_value = {
            "componente_id": 50, "riga_ddt_id": 3, "ddt_id": 7,
            "stato_codice_interno": "EMESSO", "numero": "2026/00007",
        }
        with self.assertRaises(ServiceError) as cm:
            ddt_service.update_componente(7, 3, 50, {"prezzo_unitario": "1"})
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")
        self.assertTrue(cm.exception.message.startswith("DDT 2026/00007 non e' piu' in bozza (stato EMESSO)"))
        self.assertEqual(cm.exception.context["operazione"], "UPDATE")
        repo.update_componente.assert_not_called()


class DdtCreaTests(SimpleTestCase):
    """crea_ddt standalone: BA facoltativo, copie del BA lasciate al DB, DRAFT."""

    def setUp(self) -> None:
        # transaction.atomic() a no-op (SimpleTestCase senza DB): la creazione
        # e il riempimento dello slot di default stanno in una transazione.
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_REPO)
    def test_crea_ddt_col_ba_lascia_le_copie_al_db(self, repo_cls) -> None:
        # Col BA, destinatario e utility li scrive `trgfn_ddt_normalize` (BB
        # `fn_cliente_dal_billing_account`): il service non li deriva e non
        # inoltra una utility, che e' una copia del BA.
        repo = repo_cls.return_value
        repo.create_ddt.return_value = {"id": 7, "uid": "u", "numero": None}

        out = ddt_service.crea_ddt({"billing_account_id": 3})

        self.assertEqual(out["id"], 7)
        kwargs = repo.create_ddt.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 3)
        self.assertIsNone(kwargs["destinatario_soggetto_ruolo_id"])
        self.assertNotIn("utility_id", kwargs)
        # Lo stato non si passa: lo mette il DB, lo stato iniziale del
        # vocabolario (brief-modello-documento-vendita P-2).
        self.assertNotIn("stato_doc_ddt_id", kwargs)
        repo.get_stato_id_by_codice.assert_not_called()
        # Lo slot di default lo riempie il DB, sul DDT appena nato (R-BE-1).
        repo.riempi_indirizzo_default.assert_called_once_with(7)

    @patch(_REPO)
    def test_crea_ddt_utility_rifiutata(self, repo_cls) -> None:
        # La utility e' una copia del BA (la scrive il DB): fuori whitelist. Dal
        # 2026-10-19 e' un 400 con le chiavi ignote, prima di qualunque lettura;
        # fino ad allora si scartava in silenzio.
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            ddt_service.crea_ddt({"billing_account_id": 3, "utility_id": 1})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("unknown_keys"), ["utility_id"])
        repo.get_stato_id_by_codice.assert_not_called()
        repo.create_ddt.assert_not_called()

    @patch(_REPO)
    def test_crea_ddt_errore_del_default_sale(self, repo_cls) -> None:
        # Non e' piu' best-effort: l'errore sale, e la transaction.atomic()
        # annulla anche la testata.
        repo = repo_cls.return_value
        repo.create_ddt.return_value = {"id": 7, "uid": "u", "numero": None}
        repo.riempi_indirizzo_default.side_effect = RuntimeError("DB")
        with self.assertRaises(RuntimeError):
            ddt_service.crea_ddt({"billing_account_id": 3})

    @patch(_REPO)
    def test_crea_ddt_destinatario_esplicito(self, repo_cls) -> None:
        # destinatario passato esplicito: arriva al repo (col BA il DB lo
        # confronta con quello del BA, senza BA e' il terzista o il deposito).
        repo = repo_cls.return_value
        repo.create_ddt.return_value = {"id": 8, "uid": "u", "numero": None}

        ddt_service.crea_ddt(
            {"destinatario_soggetto_ruolo_id": 777, "billing_account_id": 3},
        )
        self.assertEqual(
            repo.create_ddt.call_args.kwargs["destinatario_soggetto_ruolo_id"], 777,
        )

    @patch(_REPO)
    def test_crea_ddt_senza_destinatario_ne_ba(self, repo_cls) -> None:
        # Ne' destinatario ne' BA: nessun guard Python ricopia il NOT NULL del
        # destinatario. Lo dice il DB (23502), e la traduzione porta il campo.
        repo = repo_cls.return_value
        repo.create_ddt.return_value = {"id": 8, "uid": "u", "numero": None}
        ddt_service.crea_ddt({"causale_trasporto_id": 5})
        kwargs = repo.create_ddt.call_args.kwargs
        self.assertIsNone(kwargs["billing_account_id"])
        self.assertIsNone(kwargs["destinatario_soggetto_ruolo_id"])

    @patch(_REPO)
    def test_crea_ddt_senza_ba_ammesso(self, repo_cls) -> None:
        # D-2: trasferimento, conto lavoro, riparazione non vanno a un cliente.
        # La bolla nasce senza BA; se la causale lo vuole, lo dira' l'emissione
        # (E_DDT_CLIENTE_OBBLIGATORIO, capability CLIENTE_MANCANTE).
        repo = repo_cls.return_value
        repo.create_ddt.return_value = {"id": 8, "uid": "u", "numero": None}
        ddt_service.crea_ddt({"destinatario_soggetto_ruolo_id": 777})
        kwargs = repo.create_ddt.call_args.kwargs
        self.assertIsNone(kwargs["billing_account_id"])
        self.assertEqual(kwargs["destinatario_soggetto_ruolo_id"], 777)

    @patch(_REPO)
    def test_crea_ddt_id_non_numerico(self, repo_cls) -> None:
        # Un id non numerico e' un 400 col campo, non un 500 da `int()`.
        repo = repo_cls.return_value
        for chiave in ("billing_account_id", "destinatario_soggetto_ruolo_id"):
            with self.subTest(chiave=chiave):
                with self.assertRaises(ServiceError) as cm:
                    ddt_service.crea_ddt({chiave: "abc"})
                self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
                self.assertEqual(cm.exception.context.get("field"), chiave)
        repo.create_ddt.assert_not_called()

    @patch(_REPO)
    def test_crea_ddt_passa_emittente_payload(self, repo_cls) -> None:
        # Emittente dallo USER (uniformazione 2026-07-13, mirror ordini): il
        # payload create lo porta (prefill FE dal profilo) e arriva al repo.
        repo = repo_cls.return_value
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
        repo.create_ddt.return_value = {"id": 10, "uid": "u", "numero": None}

        ddt_service.crea_ddt({"billing_account_id": 3})
        self.assertIsNone(
            repo.create_ddt.call_args.kwargs["emittente_fiscale_id"],
        )


class DdtAggiornaTests(SimpleTestCase):
    """aggiorna_ddt: in bozza cliente e destinatario si scelgono; il DB decide le copie."""

    @patch(_REPO)
    def test_aggiorna_ddt_cambio_ba_in_bozza(self, repo_cls) -> None:
        # D-2: la bolla puo' ricevere (o cambiare) il cliente in bozza. Fino al
        # 2026-10-10 il service lo rifiutava con E_DDT_CLIENTE_IMMUTABILE.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        ddt_service.aggiorna_ddt(7, {"billing_account_id": 99})
        self.assertEqual(repo.update_ddt.call_args.kwargs, {"billing_account_id": 99})

    @patch(_REPO)
    def test_aggiorna_ddt_utility_rifiutata(self, repo_cls) -> None:
        # La utility e' una copia del BA (la scrive il DB): fuori whitelist. Dal
        # 2026-10-19 una chiave fuori whitelist e' un 400 con le chiavi ignote,
        # prima di leggere la testata; fino ad allora si scartava in silenzio.
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            ddt_service.aggiorna_ddt(7, {"billing_account_id": 3, "utility_id": 9})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("unknown_keys"), ["utility_id"])
        repo.get_stato_codice.assert_not_called()
        repo.update_ddt.assert_not_called()

    @patch(_REPO)
    def test_aggiorna_ddt_ba_tolto(self, repo_cls) -> None:
        # BA tolto in bozza: None arriva al DB, che toglie la utility e lascia
        # il destinatario (`trgfn_ddt_normalize`).
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        ddt_service.aggiorna_ddt(7, {"billing_account_id": "", "destinatario_soggetto_ruolo_id": 12})
        self.assertEqual(
            repo.update_ddt.call_args.kwargs,
            {"billing_account_id": None, "destinatario_soggetto_ruolo_id": 12},
        )

    @patch(_REPO)
    def test_aggiorna_ddt_ba_non_numerico(self, repo_cls) -> None:
        # billing_account_id non numerico -> 4xx parlante col campo, non 500.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ddt_service.aggiorna_ddt(7, {"billing_account_id": "abc"})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "billing_account_id")
        repo.update_ddt.assert_not_called()


class DdtEliminaTests(SimpleTestCase):
    """elimina_ddt: hard-delete solo per bozza orfana (0 righe)."""

    @patch(_REPO)
    def test_elimina_ddt_con_righe_rifiutato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.count_righe.return_value = 1
        with self.assertRaises(ServiceError) as cm:
            ddt_service.elimina_ddt(7)
        self.assertEqual(cm.exception.code, "E_DDT_STATO_TRANSIZIONE")
        repo.delete_ddt.assert_not_called()

    @patch(_REPO)
    def test_elimina_ddt_bozza_orfana_ok(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.count_righe.return_value = 0
        repo.delete_ddt.return_value = True
        out = ddt_service.elimina_ddt(7)
        self.assertTrue(out["deleted"])
        repo.delete_ddt.assert_called_once_with(7)


class DdtCambiaStatoTests(ModelloDocumentoMockatoMixin, SimpleTestCase):
    """cambia_stato data-driven + emetti (DRAFT->EMESSO)."""

    @patch(_REPO)
    def test_cambia_stato_ok(self, repo_cls) -> None:
        # Guard esistenza leggero: cambia_stato legge SOLO lo stato corrente
        # (get_stato_codice), non la testata completa.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 6
        repo.cambia_stato.return_value = []
        out = ddt_service.cambia_stato(7, "SPEDITO")
        self.assertEqual(out["stato"], "SPEDITO")
        self.assertEqual(out["stato_precedente"], "DRAFT")
        self.assertEqual(out["movimenti_scritti"], 0)
        repo.get_ddt.assert_not_called()
        repo.get_stato_id_by_codice.assert_called_once_with("SPEDITO")
        # Il verbo prende il CODICE dello stato (Lotto 3 R-1), non l'id.
        repo.cambia_stato.assert_called_once_with(7, "SPEDITO")

    # Un numero nel JSON al posto del codice e' un 400, non un 500 (2026-10-09).
    @patch(_REPO)
    def test_cambia_stato_codice_non_testo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, 5)  # type: ignore[arg-type]
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.cambia_stato.assert_not_called()

    @patch(_REPO)
    def test_cambia_stato_codice_vuoto(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, "   ")
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.cambia_stato.assert_not_called()

    @patch(_REPO)
    def test_cambia_stato_codice_inesistente(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, "INESISTENTE")
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.cambia_stato.assert_not_called()

    # M-2 (brief-modello-documento-vendita §7.6): la bolla si emette solo da
    # «Emetti», che produce numero e PDF insieme. Dal cambio stato generico
    # lo stato di emissione (letto dal vocabolario, §8.7) e' un 400 col campo,
    # e il verbo non parte.
    @patch(_REPO)
    def test_cambia_stato_emesso_rifiutato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 2
        self.stato_chiesto_di_emissione()
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, "EMESSO")
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "stato_codice")
        self.modello_documento.e_stato_di_emissione.assert_called_once_with(
            "vendite.ddt", "EMESSO",
        )
        repo.cambia_stato.assert_not_called()

    # «Emetti» e' l'unica strada: la domanda sull'emissione non si fa.
    @patch(_REPO)
    def test_emetti_non_chiede_il_rifiuto(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 2
        repo.cambia_stato.return_value = []
        ddt_service.emetti(7)
        self.modello_documento.e_stato_di_emissione.assert_not_called()
        repo.cambia_stato.assert_called_once_with(7, "EMESSO")

    @patch(_REPO)
    def test_emetti_transita_a_emesso_light(self, repo_cls) -> None:
        # emetti = la transizione a EMESSO (guard leggero get_stato_codice) con
        # ritorno LIGHT {ddt_id, stato_precedente, stato} — parita' con
        # ordini_service.conferma: NIENTE reload del detail pesante (vista +
        # capabilities + count) dentro la sezione atomica dell'emissione
        # documentale; il FE ricarica il detail dopo.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 2
        # Una bolla che muove merce: il verbo ritorna le uscite scritte.
        repo.cambia_stato.return_value = [
            {"movimento_id": 501, "prelievo_id": 11, "qta": 3},
        ]

        out = ddt_service.emetti(7)

        repo.get_stato_id_by_codice.assert_called_once_with("EMESSO")
        repo.cambia_stato.assert_called_once_with(7, "EMESSO")
        self.assertEqual(out["movimenti_scritti"], 1)
        repo.get_ddt.assert_not_called()
        repo.get_capabilities.assert_not_called()
        self.assertEqual(out["ddt_id"], 7)
        self.assertEqual(out["stato_precedente"], "DRAFT")
        self.assertEqual(out["stato"], "EMESSO")


class DdtCreaDaOrdineTests(SimpleTestCase):
    """crea_ddt_da_ordine: delega alla primitiva DB madre (evasione)."""

    def setUp(self) -> None:
        # transaction.atomic() a no-op (SimpleTestCase senza DB): la creazione
        # e il riempimento dello slot di default stanno in una transazione.
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

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

    @patch(_REPO)
    def test_crea_ddt_da_ordine_default_dopo_la_cascata(self, repo_cls) -> None:
        # Il default si chiede DOPO il verbo (la cascata dall'ordine vince: il
        # DB riempie lo slot solo se e' rimasto vuoto), sul DDT appena nato
        # (brief-db-indirizzi-documento-seguono-il-cliente, R-BE-1).
        repo = repo_cls.return_value
        repo.push_da_ordine.return_value = 42
        ddt_service.crea_ddt_da_ordine(99)
        self.assertEqual(
            [c[0] for c in repo.method_calls if c[0] != "push_da_ordine"],
            ["riempi_indirizzo_default"],
        )
        repo.riempi_indirizzo_default.assert_called_once_with(42)
        self.assertEqual(repo.method_calls[0][0], "push_da_ordine")

    @patch(_REPO)
    def test_crea_ddt_da_ordine_errore_del_default_sale(self, repo_cls) -> None:
        # Non e' piu' best-effort: l'errore sale, e la transaction.atomic()
        # annulla anche il DDT appena creato.
        repo = repo_cls.return_value
        repo.push_da_ordine.return_value = 42
        repo.riempi_indirizzo_default.side_effect = RuntimeError("DB")
        with self.assertRaises(RuntimeError):
            ddt_service.crea_ddt_da_ordine(99)


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

    def test_vincoli_della_coppia_col_campo(self) -> None:
        # La rete sotto il BB del cliente (brief-db-esecutivi-ba-coppia §7):
        # chi scrive senza passare dai trigger riceve un codice parlante e il
        # campo da accendere, non il messaggio generico.
        casi = {
            "fk_ddt_ba_cliente": "E_DOC_CLIENTE_DIVERSO_DA_BA",
            "chk_ddt_ba_utility_insieme": "E_VENDITE_VALIDATION",
        }
        for vincolo, codice in casi.items():
            with self.subTest(vincolo=vincolo):
                with self.assertRaises(ServiceError) as cm:
                    with _db_errors("test"):
                        raise IntegrityError(f'violates constraint "{vincolo}"')
                self.assertEqual(cm.exception.code, codice)
                self.assertEqual(cm.exception.context.get("field"), "billing_account_id")


class DdtFatturazioneImmediataTests(SimpleTestCase):
    """Corsia di instradamento `fatturazione_immediata` sul DDT.

    Gemello di `OrdiniFatturazioneImmediataTests`: qui la whitelist basta
    (mapper generico), ma il comportamento va bloccato — il difetto del
    2026-07-27 sui contratti e' nato proprio dal dare per scontato che il gesto
    fosse identico sui tre domini.
    """

    def setUp(self) -> None:
        # transaction.atomic() a no-op (SimpleTestCase senza DB): la creazione
        # e il riempimento dello slot di default stanno in una transazione.
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_REPO)
    def test_crea_ddt_porta_il_flag(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.create_ddt.return_value = {"id": 9, "uid": "u", "numero": None}
        ddt_service.crea_ddt({
            "billing_account_id": 3, "fatturazione_immediata": True,
        })
        self.assertIs(
            repo.create_ddt.call_args.kwargs["fatturazione_immediata"], True,
        )

    @patch(_REPO)
    def test_aggiorna_ddt_persiste_il_flag(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
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


    # Scopo: ⛔ `I6` — LA CASELLA E' CHIUSA. A decidere l'aliquota e' il
    #        risolutore, e la scelta manuale non esiste piu'. Un client che manda
    #        ancora `iva_id` nel payload riceve un 400 con la chiave ignota (dal
    #        2026-10-19, scelta di Tid: la whitelist della riga respinge, come
    #        quella della testata). Fino ad allora la chiave si SCARTAVA in
    #        silenzio.
    # ⛔ E il risolutore va interrogato con `payload_iva_id=None`: passargli il
    #        valore del client lo farebbe scendere sul ramo di AUDIT, dove gli
    #        errori sono best-effort — cioe' una riga si salverebbe anche
    #        quando l'IVA non e' determinabile.
    @patch(_PRICING)
    @patch(_REPO)
    def test_i6_iva_del_payload_respinta(self, repo_cls, pricing_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = self._testata()
        repo.is_articolo_composito.return_value = False
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 31}
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 42
        self.iva.return_value = (9, {"iva_origine": "TITOLO", "iva_titolo_id": 4})

        riga = {"articolo_id": "ART1", "uom_operativa_id": 5, "prezzo_unitario": "10"}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.gestisci_riga(7, {**riga, "iva_id": 999})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("unknown_keys"), ["iva_id"])
        self.iva.assert_not_called()
        repo.create_riga.assert_not_called()
        self.assertNotIn("iva_id", ddt_service.CREATE_PAYLOAD_RIGA)
        self.assertNotIn("iva_id", ddt_service.UPDATE_KEYS_RIGA)

        # Senza la chiave la riga si salva, e l'aliquota e' del risolutore.
        ddt_service.gestisci_riga(7, riga)
        self.assertIsNone(self.iva.call_args.kwargs["payload_iva_id"])
        self.assertEqual(repo.create_riga.call_args.kwargs["iva_id"], 9)


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


# Scopo: I satelliti «leggono prima la testata» (2026-09-21, allineamento a
#        api.md §Scope emittente): un DDT fuori perimetro RLS — `None` dal
#        repository, come un id inesistente — e' un 404, non un 200 vuoto.
#
# Indice:
# 25) test_list_righe_ddt_non_trovato_e_404
# 26) test_list_riepilogo_iva_ddt_non_trovato_e_404
# 27) test_list_componenti_riga_di_altro_ddt_e_404
# 28) test_list_righe_con_testata_delega_al_repo
class DdtSatellitiTestataTests(SimpleTestCase):
    @patch(_REPO)
    def test_list_righe_ddt_non_trovato_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.list_righe(99)
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")
        repo.list_righe.assert_not_called()

    @patch(_REPO)
    def test_list_riepilogo_iva_ddt_non_trovato_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.list_riepilogo_iva(99)
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")
        repo.list_riepilogo_iva.assert_not_called()

    @patch(_REPO)
    def test_list_componenti_riga_di_altro_ddt_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 31, "ddt_id": 8}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.list_componenti_riga(7, 31)
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")
        repo.list_componenti_riga.assert_not_called()

    @patch(_REPO)
    def test_list_righe_con_testata_delega_al_repo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        repo.list_righe.return_value = [{"id": 31}]
        self.assertEqual(ddt_service.list_righe(7), [{"id": 31}])
        repo.list_righe.assert_called_once_with(7)


# Le righe evase dall'ordine o dal reso (brief-db-ddt-righe-evase-dall-ordine,
# 2026-10-11): il verbo della quantita' evasa, l'annullo con conferma (D-8) e la
# lettura dei legami per la finestra. ⚠️ Le regole (bozza, riga evasa, residuo,
# conteggio della conferma) sono del DB e qui sono mockate: questi test provano
# il trasporto, non la regola.
class DdtRigheEvaseTests(ModelloDocumentoMockatoMixin, SimpleTestCase):
    @patch(_REPO)
    def test_annullo_passa_dal_verbo_senza_dichiarazione(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSO"
        repo.get_stato_id_by_codice.return_value = 9
        out = ddt_service.cambia_stato(7, "ANNULLATO")
        repo.annulla.assert_called_once_with(7, None)
        repo.cambia_stato.assert_not_called()
        self.assertEqual(out["stato"], "ANNULLATO")
        self.assertEqual(out["stato_precedente"], "EMESSO")

    @patch(_REPO)
    def test_annullo_con_dichiarazione(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 9
        ddt_service.cambia_stato(7, "ANNULLATO", legami_confermati="2")
        repo.annulla.assert_called_once_with(7, 2)

    @patch(_REPO)
    def test_annullo_dichiarazione_non_numerica(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_stato_id_by_codice.return_value = 9
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, "ANNULLATO", legami_confermati="due")
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "legami_confermati")
        repo.annulla.assert_not_called()

    @patch(_REPO)
    def test_annullo_con_legami_codice_del_db(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSO"
        repo.get_stato_id_by_codice.return_value = 9
        repo.annulla.side_effect = DatabaseError(
            "E_DOC_ANNULLO_CON_LEGAMI: annullando DDT 12 si riaprono 2 legami",
        )
        with self.assertRaises(ServiceError) as cm:
            ddt_service.cambia_stato(7, "ANNULLATO")
        self.assertEqual(cm.exception.code, "E_DOC_ANNULLO_CON_LEGAMI")
        # Il comportamento che la finestra riconosce (`useForzaturaConfermata`).
        policy = ErrorPolicyRegistry.resolve("E_DOC_ANNULLO_CON_LEGAMI")
        self.assertEqual(policy.http_status, 409)
        self.assertEqual(policy.ui_action, "confirm_and_retry")

    @patch(_REPO)
    def test_correggi_qta_evasa_delega_al_verbo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_riga.return_value = {"id": 31, "ddt_id": 7}
        repo.correggi_qta_evasa.return_value = Decimal("6")
        out = ddt_service.correggi_qta_evasa(7, 31, {"qta_operativa": "6"})
        repo.correggi_qta_evasa.assert_called_once_with(31, Decimal("6"))
        self.assertEqual(out, {"ddt_id": 7, "riga_id": 31, "qta_evasa": Decimal("6")})

    @patch(_REPO)
    def test_correggi_qta_evasa_qta_mancante(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_riga.return_value = {"id": 31, "ddt_id": 7}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.correggi_qta_evasa(7, 31, {})
        self.assertEqual(cm.exception.code, "E_DDT_VALIDAZIONE")
        repo.correggi_qta_evasa.assert_not_called()

    @patch(_REPO)
    def test_correggi_qta_evasa_riga_di_altro_ddt_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_riga.return_value = {"id": 31, "ddt_id": 8}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.correggi_qta_evasa(7, 31, {"qta_operativa": "6"})
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")
        repo.correggi_qta_evasa.assert_not_called()

    @patch(f"{_SVC}.legami_del_documento")
    @patch(_REPO)
    def test_get_legami_delega_al_bb(self, repo_cls, bb) -> None:
        # Il conteggio e i nomi sono del BB comune (test_annullo_con_legami):
        # qui la testata prima, poi la delega col codice del documento.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSO"
        bb.return_value = {"documento": "DDT_VENDITA", "id": 7, "legami": 2, "righe": []}
        self.assertEqual(ddt_service.get_legami(7)["legami"], 2)
        bb.assert_called_once_with("DDT_VENDITA", 7)

    @patch(f"{_SVC}.legami_del_documento")
    @patch(_REPO)
    def test_get_legami_ddt_non_trovato_e_404(self, repo_cls, bb) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ddt_service.get_legami(99)
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")
        bb.assert_not_called()


# B1 (Lotto 3 R-2b, piano-be-fe-magazzino-lotto-3): il trasporto dei prelievi.
# ⚠️ Le regole (bozza, kit, ubicazioni, somma) sono dei trigger DB e qui sono
# assenti: lo prova `tests/db/test_ddt_cambia_stato_db`.
class DdtPrelieviTests(SimpleTestCase):
    @patch(_REPO)
    def test_get_prelievi_raggruppa_per_voce(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_testata_prelievi.return_value = {"ddt_id": 7, "muove_merce": True}
        # Un kit composto al momento: due componenti della stessa riga.
        repo.list_merce_da_movimentare.return_value = [
            {"ddt_riga_id": 1, "ddt_riga_componente_id": 10, "qta": 2},
            {"ddt_riga_id": 1, "ddt_riga_componente_id": 11, "qta": 3},
            {"ddt_riga_id": 2, "ddt_riga_componente_id": None, "qta": 1},
        ]
        repo.list_prelievi.return_value = [
            {"id": 100, "ddt_riga_id": 1, "ddt_riga_componente_id": 11},
            {"id": 101, "ddt_riga_id": 2, "ddt_riga_componente_id": None},
            {"id": 102, "ddt_riga_id": 1, "ddt_riga_componente_id": 11},
        ]
        out = ddt_service.get_prelievi(7)
        self.assertTrue(out["muove_merce"])
        self.assertEqual(
            [[p["id"] for p in v["prelievi"]] for v in out["voci"]],
            [[], [100, 102], [101]],
        )

    @patch(_REPO)
    def test_crea_prelievo_porta_la_riga_e_coerce(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_riga.return_value = {"id": 5, "ddt_id": 7}
        repo.create_prelievo.return_value = {"id": 99}
        out = ddt_service.crea_prelievo(
            7, 5, {"qta": "2.5", "lotto_id": "3", "ubicazione_id": ""},
        )
        self.assertEqual(out["prelievo_id"], 99)
        valori = repo.create_prelievo.call_args[0][0]
        self.assertEqual(
            valori,
            {"ddt_riga_id": 5, "qta": Decimal("2.5"), "lotto_id": 3, "ubicazione_id": None},
        )
        # ⛔ Una chiave estranea e' un 400 (2026-10-20), non uno scarto.
        repo.create_prelievo.reset_mock()
        with self.assertRaises(ServiceError) as ctx:
            ddt_service.crea_prelievo(7, 5, {"qta": "2.5", "estranea": 1})
        self.assertEqual(ctx.exception.code, "E_DDT_VALIDAZIONE")
        repo.create_prelievo.assert_not_called()

    @patch(_REPO)
    def test_prelievo_di_altra_riga_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_riga.return_value = {"id": 5, "ddt_id": 7}
        repo.get_prelievo.return_value = {"id": 9, "ddt_riga_id": 6}
        with self.assertRaises(ServiceError) as cm:
            ddt_service.aggiorna_prelievo(7, 5, 9, {"qta": "1"})
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")
        repo.update_prelievo.assert_not_called()
