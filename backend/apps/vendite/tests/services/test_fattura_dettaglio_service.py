# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service di dettaglio fattura
#        (get_fattura_dettaglio, mock repository) — drawer di consultazione.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FatturaDettaglioServiceTests.test_id_non_valido
2) FatturaDettaglioServiceTests.test_fattura_non_trovata_404
3) FatturaDettaglioServiceTests.test_fuori_scope_404_identico_a_inesistente
4) FatturaDettaglioServiceTests.test_satelliti_non_letti_se_testata_none  ← il cuore
5) FatturaDettaglioServiceTests.test_scope_propagato_alla_testata
6) FatturaDettaglioServiceTests.test_shape_risposta
7) FatturaDettaglioServiceTests.test_documento_vuoto_non_e_un_errore
8) FatturaDettaglioServiceTests.test_contatore_note_nel_payload
9) FatturaDettaglioServiceTests.test_contatore_note_zero_e_un_numero
10) FatturaDettaglioServiceTests.test_note_non_contate_se_testata_none  ← RLS assente
11) FatturaDettaglioServiceTests.test_errore_vivo_dal_giornale_della_fattura
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.vendite_service import get_fattura_dettaglio

_TESTATA = {
    "id": 7,
    "numero": 123,
    "serie": "A",
    "anno": 2026,
    "data": "2026-07-01",
    "stato_codice_interno": "DEFINITIVA",
    "ragione_sociale_completa": "Rossi Mario SRL",
    "totale_doc": "1220.00",
    "totale_a_pagare": "1220.00",
}
_RIGHE = [{"id": 1, "riga_nr": 1, "descrizione": "Canone", "importo_riga": "1000.00"}]
_RIEPILOGO = [{"iva_id": 1, "iva_aliquota": "22.00", "imponibile": "1000.00", "imposta": "220.00"}]
_SCADENZE = [{"numero_rata": 1, "data_scadenza": "2026-08-31", "importo": "1220.00"}]


class FatturaDettaglioServiceTests(TestCase):
    """Dettaglio fattura per il drawer di consultazione
    (brief-be-fe-drawer-fattura §5).

    Il service è sottile per costruzione: guard sull'id, il cancello di testata
    e la composizione dei quattro lettori. Le decodifiche (cliente, emittente,
    IVA, kit) vivono nelle query del repository e NON sono testate qui.
    """

    # Il conteggio note passa dal BB `contatori_documento`, che chiama il
    # service del BB note (`count_per_target`): si patcha la classe nel modulo
    # del BB, dove la si risolve, così nessun test tocca il DB reale per il
    # contatore del badge.
    def setUp(self):
        patcher = patch(
            "apps.core.services.partitioned_note_service.PartitionedNoteService",
        )
        note_svc_cls = patcher.start()
        self.addCleanup(patcher.stop)
        self.note_svc = note_svc_cls.return_value
        self.note_svc.count_per_target.return_value = 0
        # ⭐ Le righe vengono dalla vista di LISTA (`FattureRepository.
        #    list_righe`, lotto C del brief-db-liste-righe-documento), non piu'
        #    dalla query del `VenditeRepository`.
        patcher = patch("apps.vendite.services.vendite_service.FattureRepository")
        self.righe_repo = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self.righe_repo.list_righe.return_value = list(_RIGHE)

    def _repo(self, mock_repo_cls, *, testata=_TESTATA):
        repo = mock_repo_cls.return_value
        repo.get_fattura_testata.return_value = dict(testata) if testata else None
        repo.list_fattura_riepilogo_iva.return_value = list(_RIEPILOGO)
        repo.list_fattura_scadenze.return_value = list(_SCADENZE)
        repo.get_giornale_errore_vivo.return_value = None
        return repo

    # Scopo: id non positivo → 400 prima di qualunque round-trip.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_id_non_valido(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls)
        for bad in (0, -1, None):
            with self.subTest(fattura_id=bad):
                with self.assertRaises(ServiceError) as ctx:
                    get_fattura_dettaglio(fattura_id=bad)
                self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.get_fattura_testata.assert_not_called()

    # Scopo: fattura inesistente → 404 col codice di dominio.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_fattura_non_trovata_404(self, mock_repo_cls):
        self._repo(mock_repo_cls, testata=None)

        with self.assertRaises(ServiceError) as ctx:
            get_fattura_dettaglio(fattura_id=7)
        self.assertEqual(ctx.exception.code, "E_FATTURA_NON_TROVATA")

    # Scopo: fuori scope emittente → la testata torna None (RLS + filtro
    #        applicativo) e la risposta è IDENTICA a quella di un id
    #        inesistente. Un errore che distinguesse i due casi confermerebbe
    #        l'esistenza di una fattura di un altro emittente.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_fuori_scope_404_identico_a_inesistente(self, mock_repo_cls):
        self._repo(mock_repo_cls, testata=None)

        with self.assertRaises(ServiceError) as ctx_scope:
            get_fattura_dettaglio(fattura_id=7, auth_user_id=42)
        with self.assertRaises(ServiceError) as ctx_inesistente:
            get_fattura_dettaglio(fattura_id=999999)

        self.assertEqual(ctx_scope.exception.code, ctx_inesistente.exception.code)
        self.assertEqual(ctx_scope.exception.message, ctx_inesistente.exception.message)

    # Scopo: ⚠️ IL TEST CHE CONTA — testata-first. Se la testata non autorizza,
    #        i satelliti non devono essere sfiorati.
    #        Dal 2026-07-29 `fatture_righe` e `fatture_riepiloghi_iva` hanno la
    #        loro RLS (changeset satelliti), quindi il caso non e' piu' un leak
    #        su QUELLE due tabelle; l'ordine resta pero' vincolante perche' e'
    #        cio' che produce il 404 unificato invece di un documento a meta',
    #        e perche' gli altri satelliti della fattura (note, indirizzi,
    #        fondi, SDI) restano senza policy. Regressione silenziosa se
    #        qualcuno riordina le chiamate.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_satelliti_non_letti_se_testata_none(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls, testata=None)

        with self.assertRaises(ServiceError):
            get_fattura_dettaglio(fattura_id=7, auth_user_id=42)

        self.righe_repo.list_righe.assert_not_called()
        repo.list_fattura_riepilogo_iva.assert_not_called()
        repo.list_fattura_scadenze.assert_not_called()
        # ⚠️ E il legame documentale meno che mai (B7): `vendite.fatture` ha la
        # RLS, `vendite.fatture_rettifiche` NO. Leggerlo prima del cancello
        # esporrebbe NUMERO e DATA di un documento di un altro emittente — cioe'
        # il leak che le policy sui satelliti hanno chiuso altrove.
        repo.get_fattura_rettifiche.assert_not_called()
        # Il giornale e' una vista `security_invoker`: fuori scope risponderebbe
        # «nessun errore» — ma la domanda non va nemmeno fatta.
        repo.get_giornale_errore_vivo.assert_not_called()

    # Scopo: lo scope dell'utente arriva al cancello (difesa applicativa che si
    #        somma alla RLS), non si ferma nel service.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_scope_propagato_alla_testata(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls)

        get_fattura_dettaglio(fattura_id=7, auth_user_id=42)

        repo.get_fattura_testata.assert_called_once_with(7, auth_user_id=42)

    # Scopo: shape della risposta — quattro chiavi stabili, quelle che il
    #        drawer si aspetta.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_shape_risposta(self, mock_repo_cls):
        self._repo(mock_repo_cls)

        result = get_fattura_dettaglio(fattura_id=7)

        self.assertEqual(
            set(result.keys()),
            {"fattura", "righe", "riepilogo_iva", "scadenze", "contatori",
             "rettifiche", "errore_vivo"},
        )
        self.assertEqual(result["fattura"]["numero"], 123)
        self.assertEqual(result["righe"], _RIGHE)
        self.assertEqual(result["riepilogo_iva"], _RIEPILOGO)
        self.assertEqual(result["scadenze"], _SCADENZE)

    # Scopo: una fattura senza righe/rate NON è un errore — è lo stato di una
    #        DRAFT appena creata dalla pipeline. Il drawer deve poterla aprire
    #        e mostrarla vuota, non ricevere un 404.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_documento_vuoto_non_e_un_errore(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls)
        self.righe_repo.list_righe.return_value = []
        repo.list_fattura_riepilogo_iva.return_value = []
        repo.list_fattura_scadenze.return_value = []

        result = get_fattura_dettaglio(fattura_id=7)

        self.assertEqual(result["righe"], [])
        self.assertEqual(result["scadenze"], [])
        self.assertIsNotNone(result["fattura"])

    # Scopo: il contatore note arriva nel payload — è quello che alimenta il
    #        badge della barra azioni senza un secondo round-trip.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_contatore_note_nel_payload(self, mock_repo_cls):
        self._repo(mock_repo_cls)
        self.note_svc.count_per_target.return_value = 3

        result = get_fattura_dettaglio(fattura_id=7)

        self.assertEqual(result["contatori"], {"note": 3})
        self.note_svc.count_per_target.assert_called_once_with(target_id=7)

    # Scopo: zero note è un NUMERO, non None e non chiave assente: il FE
    #        distingue "nessuna nota" (nessun badge) da "non lo so".
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_contatore_note_zero_e_un_numero(self, mock_repo_cls):
        self._repo(mock_repo_cls)
        self.note_svc.count_per_target.return_value = 0

        result = get_fattura_dettaglio(fattura_id=7)

        self.assertEqual(result["contatori"]["note"], 0)

    # Scopo: ⚠️ `vendite.note_fatture` NON ha policy RLS — a differenza di
    #        `fatture`/`fatture_righe`/`fatture_riepiloghi_iva`. Un COUNT su una
    #        fattura fuori scope risponderebbe (leak: "questa fattura esiste e
    #        ha N note"). L'unica difesa è l'ordine: il cancello di testata
    #        chiude con 404 PRIMA. Regressione silenziosa se qualcuno sposta il
    #        conteggio sopra il guard.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_note_non_contate_se_testata_none(self, mock_repo_cls):
        self._repo(mock_repo_cls, testata=None)

        with self.assertRaises(ServiceError):
            get_fattura_dettaglio(fattura_id=7, auth_user_id=42)

        self.note_svc.count_per_target.assert_not_called()

    # ⭐ Il banner d'errore del drawer ha una FONTE SUA nel dettaglio (2026-09-27):
    #    la Storia e' ora la lista a catalogo `vendite.giornale`, ordinata dal
    #    preset o dall'operatore, e «il primo ERROR della pagina» avrebbe taciuto
    #    appena l'errore fosse uscito dalla pagina. Qui si presidia che la
    #    domanda si faccia sull'entita' giusta e che la risposta arrivi intera.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_errore_vivo_dal_giornale_della_fattura(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls)
        riga = {"riga_key": "FATTURA_LOG:5", "gravita": "ERROR", "cosa": "Non numerabile"}
        repo.get_giornale_errore_vivo.return_value = riga

        result = get_fattura_dettaglio(fattura_id=7)

        repo.get_giornale_errore_vivo.assert_called_once_with(
            entity_type="FATTURA", entity_id=7,
        )
        self.assertEqual(result["errore_vivo"], riga)
