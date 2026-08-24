# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service «storia del documento»
#        (get_fattura_giornale, mock repository) — Passo A del filone
#        osservabilita', primo consumatore di script.vw_giornale_entita.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FatturaGiornaleServiceTests.test_id_non_valido
2) FatturaGiornaleServiceTests.test_fattura_non_trovata_404
3) FatturaGiornaleServiceTests.test_fuori_scope_404_identico_a_inesistente
4) FatturaGiornaleServiceTests.test_giornale_non_letto_se_testata_none  ← il cuore
5) FatturaGiornaleServiceTests.test_scope_propagato_alla_testata
6) FatturaGiornaleServiceTests.test_shape_risposta_e_paginazione
7) FatturaGiornaleServiceTests.test_giornale_vuoto_non_e_un_errore
8) FatturaGiornaleServiceTests.test_entity_type_e_fattura
9) FatturaGiornaleServiceTests.test_ritirate_nascoste_di_default
10) FatturaGiornaleServiceTests.test_ritirate_incluse_su_richiesta
11) FatturaGiornaleServiceTests.test_ordinamento_di_default_e_la_gravita
12) FatturaGiornaleServiceTests.test_ordinamento_chiesto_arriva_al_repository
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.vendite_service import get_fattura_giornale

_TESTATA = {"id": 7, "numero": 123}
_RIGHE = [
    {
        "riga_key": "FATTURA_LOG:5",
        "registro": "FATTURA_LOG",
        "quando": "2026-08-24T11:57:09+02:00",
        "gravita": "ERROR",
        "cosa": "Non si puo' numerare il documento 19563.",
        "tx_id": None,
        "correlation_id": None,
        "auth_user_id": None,
        "user_insert": "tid",
    }
]


class FatturaGiornaleServiceTests(TestCase):
    # Scopo: un id non positivo e' un chiamante rotto, non un dato dell'utente.
    def test_id_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            get_fattura_giornale(fattura_id=0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: fattura inesistente -> 404 di dominio.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_fattura_non_trovata_404(self, repo_cls):
        repo_cls.return_value.get_fattura_testata.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            get_fattura_giornale(fattura_id=7)
        self.assertEqual(ctx.exception.code, "E_FATTURA_NON_TROVATA")

    # Scopo: fuori scope e inesistente devono dare la STESSA risposta — un
    #        errore che li distinguesse confermerebbe l'esistenza di una fattura
    #        di un altro emittente.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_fuori_scope_404_identico_a_inesistente(self, repo_cls):
        repo_cls.return_value.get_fattura_testata.return_value = None
        with self.assertRaises(ServiceError) as fuori:
            get_fattura_giornale(fattura_id=7, auth_user_id=42)
        with self.assertRaises(ServiceError) as inesistente:
            get_fattura_giornale(fattura_id=7, auth_user_id=None)
        self.assertEqual(fuori.exception.code, inesistente.exception.code)
        self.assertEqual(fuori.exception.message, inesistente.exception.message)

    # ⭐ IL CUORE. La vista e' `security_invoker`: su una fattura fuori scope
    #    risponderebbe ZERO RIGHE, cioe' «non e' successo niente» invece di
    #    «non la vedi». Il cancello e' la TESTATA, e il giornale non si legge
    #    affatto se quella non ha autorizzato.
    # ⛔ Senza questo test la regressione sarebbe silenziosa: la risposta
    #    sbagliata e' un 200 con un elenco vuoto, che non somiglia a un difetto.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_giornale_non_letto_se_testata_none(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = None
        with self.assertRaises(ServiceError):
            get_fattura_giornale(fattura_id=7)
        repo.list_giornale_entita.assert_not_called()

    # Scopo: lo scope applicativo arriva alla testata — si SOMMA alla RLS, non
    #        la sostituisce.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_scope_propagato_alla_testata(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = (_RIGHE, 1, 0)
        get_fattura_giornale(fattura_id=7, auth_user_id=99)
        repo.get_fattura_testata.assert_called_once_with(7, auth_user_id=99)

    # Scopo: envelope paginato standard, con l'offset calcolato dalla pagina.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_shape_risposta_e_paginazione(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = (_RIGHE, 7, 0)
        data = get_fattura_giornale(fattura_id=7, page=2, page_size=3)
        self.assertEqual(data["fattura_id"], 7)
        self.assertEqual(data["count"], 7)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 3)
        self.assertEqual(data["total_pages"], 3)
        self.assertEqual(data["results"], _RIGHE)
        self.assertEqual(repo.list_giornale_entita.call_args.kwargs["offset"], 3)

    # Scopo: un documento a cui non e' successo niente NON e' un errore — e'
    #        l'esito normale. ⚠️ Misurato il 2026-08-24: 15 fatture su 17 non
    #        hanno nessuna riga di giornale.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_giornale_vuoto_non_e_un_errore(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = ([], 0, 0)
        data = get_fattura_giornale(fattura_id=7)
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    # Scopo: la vista e' POLIMORFA — il tipo di entita' non e' un dettaglio ma
    #        cio' che seleziona il ramo. Un `entity_type` sbagliato darebbe un
    #        elenco vuoto plausibile, non un errore.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_entity_type_e_fattura(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = ([], 0, 0)
        get_fattura_giornale(fattura_id=7)
        chiamata = repo.list_giornale_entita.call_args.kwargs
        self.assertEqual(chiamata["entity_type"], "FATTURA")
        self.assertEqual(chiamata["entity_id"], 7)

    # ⭐ Le ritirate si nascondono di DEFAULT, e il conteggio le dichiara.
    # ⛔ Senza il conteggio, «nessun evento» e «tre eventi tutti superati» si
    #    leggerebbero uguali — che e' proprio il caso in cui la differenza conta.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_ritirate_nascoste_di_default(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = (_RIGHE, 2, 1)
        data = get_fattura_giornale(fattura_id=7)
        self.assertTrue(repo.list_giornale_entita.call_args.kwargs["escludi_ritirate"])
        # `count` e' cio' che si VEDE, non cio' che esiste.
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["ritirate_count"], 1)

    # Scopo: chiedendole esplicitamente entrano nel conto e non c'e' piu' niente
    #        di nascosto da dichiarare.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_ritirate_incluse_su_richiesta(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = (_RIGHE, 2, 1)
        data = get_fattura_giornale(fattura_id=7, includi_ritirate=True)
        self.assertFalse(repo.list_giornale_entita.call_args.kwargs["escludi_ritirate"])
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["ritirate_count"], 0)

    # Scopo: ⭐ L'ORDINE DI DEFAULT E' LA GRAVITA' (Tid, 2026-08-24, dopo la
    #        validazione in-app): davanti a un documento la prima domanda e'
    #        «c'e' qualcosa che non va?», non «cosa e' successo per primo».
    # ⛔ E l'ordinamento e' del SERVER: la lista e' paginata, quindi riordinare
    #    nel client riordinerebbe la sola pagina caricata — «il piu' grave»
    #    diventerebbe «il piu' grave fra i primi 50», senza dirlo. Questo test
    #    presidia che il default non si perda per strada fino al repository.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_ordinamento_di_default_e_la_gravita(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = (_RIGHE, 2, 1)
        get_fattura_giornale(fattura_id=7)
        chiamata = repo.list_giornale_entita.call_args.kwargs
        self.assertEqual(chiamata["sort_by"], "gravita")
        self.assertEqual(chiamata["sort_dir"], "desc")

    # Scopo: la cronologia resta a un clic — la colonna «quando» chiesta dal
    #        pannello arriva intatta al repository, verso compreso.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_ordinamento_chiesto_arriva_al_repository(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = _TESTATA
        repo.list_giornale_entita.return_value = (_RIGHE, 2, 1)
        get_fattura_giornale(fattura_id=7, sort_by="quando", sort_dir="asc")
        chiamata = repo.list_giornale_entita.call_args.kwargs
        self.assertEqual(chiamata["sort_by"], "quando")
        self.assertEqual(chiamata["sort_dir"], "asc")
