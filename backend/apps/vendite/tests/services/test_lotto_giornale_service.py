# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service «storia del lotto» (get_lotto_giornale, mock
#        repository) — seconda meta' del Passo A del filone osservabilita'.
#
#        ⛔ Questo pannello non era scrivibile prima del 2026-08-24 19:33: sul
#        lotto i registri sono TRE, e con l'orario di TRANSAZIONE le righe di
#        una stessa transazione uscivano tutte con lo stesso istante — una
#        timeline che mostra una sequenza mai avvenuta e non sembra rotta (R-1).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottoGiornaleServiceTests.test_id_non_valido
2) LottoGiornaleServiceTests.test_lotto_non_trovato_404
3) LottoGiornaleServiceTests.test_fuori_scope_404_identico_a_inesistente
4) LottoGiornaleServiceTests.test_giornale_non_letto_se_lotto_none  ← il cuore
5) LottoGiornaleServiceTests.test_scope_propagato_al_cancello
6) LottoGiornaleServiceTests.test_info_nascoste_di_default_e_dichiarate
7) LottoGiornaleServiceTests.test_info_incluse_su_richiesta
8) LottoGiornaleServiceTests.test_ritirate_e_info_si_sommano_nel_totale
9) LottoGiornaleServiceTests.test_totale_non_va_sotto_zero
10) LottoGiornaleServiceTests.test_ordinamento_di_default_lo_decide_il_repository
11) LottoGiornaleServiceTests.test_giornale_vuoto_non_e_un_errore
12) LottoGiornaleServiceTests.test_riga_dichiara_di_chi_e
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.vendite_service import get_lotto_giornale

_LOTTO = {"id": 6260, "codice": "LTF-0006260"}
# ⭐ Due righe di DUE entita' diverse: e' tutto il punto del pannello del lotto.
#    Il lotto dice che e' andata male, la fattura dice perche' (rilievo R-3).
_RIGHE = [
    {
        "riga_key": "TASK_RUN:9",
        "registro": "TASK_RUN",
        "quando": "2026-08-24T19:20:00+02:00",
        "gravita": "ERROR",
        "cosa": "numera_fatture · ERRORE · E_FATTURA_RETTIFICATA_SENZA_NUMERO",
        "tx_id": None,
        "correlation_id": None,
        "auth_user_id": None,
        "user_insert": "tid",
        "ritirata": False,
        "entity_type": "LOTTO",
        "entity_id": 6260,
    },
    {
        "riga_key": "FATTURA_LOG:5",
        "registro": "FATTURA_LOG",
        "quando": "2026-08-24T19:20:01+02:00",
        "gravita": "ERROR",
        "cosa": "Non si puo' numerare il documento: rettifica righe da chiudere.",
        "tx_id": None,
        "correlation_id": None,
        "auth_user_id": None,
        "user_insert": "tid",
        "ritirata": False,
        "entity_type": "FATTURA",
        "entity_id": 20024,
    },
]


class LottoGiornaleServiceTests(TestCase):
    # Scopo: un id non positivo e' un chiamante rotto, non un dato dell'utente.
    def test_id_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            get_lotto_giornale(lotto_id=0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: lotto inesistente -> 404 di dominio.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_lotto_non_trovato_404(self, repo_cls):
        repo_cls.return_value.get_lotto.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            get_lotto_giornale(lotto_id=6260)
        self.assertEqual(ctx.exception.code, "E_LOTTO_NON_TROVATO")

    # Scopo: fuori scope e inesistente devono dare la STESSA risposta — un
    #        errore che li distinguesse confermerebbe l'esistenza del lotto di
    #        un altro emittente.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_fuori_scope_404_identico_a_inesistente(self, repo_cls):
        repo_cls.return_value.get_lotto.return_value = None
        with self.assertRaises(ServiceError) as fuori:
            get_lotto_giornale(lotto_id=6260, auth_user_id=42)
        with self.assertRaises(ServiceError) as inesistente:
            get_lotto_giornale(lotto_id=6260)
        self.assertEqual(fuori.exception.code, inesistente.exception.code)

    # ⭐ IL CUORE. Il cancello non e' ridondante con la RLS: la vista non ha un
    #    perimetro proprio per le righe di entita' FATTURA, e senza questo
    #    passaggio un lotto altrui riceverebbe «zero righe» — che si legge come
    #    «lotto senza storia», non come «non lo puoi vedere».
    #    ⛔ Se il giornale venisse letto lo stesso, il difetto sarebbe muto.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_giornale_non_letto_se_lotto_none(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = None
        with self.assertRaises(ServiceError):
            get_lotto_giornale(lotto_id=6260)
        repo.list_giornale_lotto.assert_not_called()

    # Scopo: lo scope arriva al cancello — non applicarlo lo aprirebbe.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_scope_propagato_al_cancello(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = (_RIGHE, 2, 0, 0)
        get_lotto_giornale(lotto_id=6260, auth_user_id=42)
        self.assertEqual(repo.get_lotto.call_args.kwargs["auth_user_id"], 42)

    # ⭐ Le INFO si nascondono ma si CONTANO: un elenco filtrato e uno completo
    #    si leggono uguali, e «tre problemi» vs «tre problemi e 173 passi andati
    #    bene» sono due schermate diverse.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_info_nascoste_di_default_e_dichiarate(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = (_RIGHE, 286, 2, 173)
        out = get_lotto_giornale(lotto_id=6260)
        self.assertTrue(repo.list_giornale_lotto.call_args.kwargs["escludi_info"])
        self.assertEqual(out["count"], 113)
        self.assertEqual(out["info_count"], 173)

    # Scopo: chiedendole, le INFO entrano nel totale e non c'e' piu' niente da
    #        dichiarare.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_info_incluse_su_richiesta(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = (_RIGHE, 286, 2, 173)
        out = get_lotto_giornale(lotto_id=6260, includi_info=True)
        self.assertFalse(repo.list_giornale_lotto.call_args.kwargs["escludi_info"])
        self.assertEqual(out["count"], 286)
        self.assertEqual(out["info_count"], 0)

    # Scopo: i due filtri sono indipendenti e si sommano sul totale — e' il caso
    #        in cui un errore di segno passa inosservato.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_ritirate_e_info_si_sommano_nel_totale(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = (_RIGHE, 286, 2, 173)
        out = get_lotto_giornale(lotto_id=6260, includi_info=True, includi_ritirate=True)
        self.assertEqual(out["count"], 288)
        self.assertEqual(out["info_count"], 0)
        self.assertEqual(out["ritirate_count"], 0)

    # ⚠️ Il totale e' una sottrazione, e una sottrazione puo' andare sotto zero
    #    se i conteggi arrivassero incoerenti. Un `count` negativo romperebbe il
    #    paginatore del client senza nessun errore lato server.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_totale_non_va_sotto_zero(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = ([], 5, 0, 99)
        out = get_lotto_giornale(lotto_id=6260)
        self.assertEqual(out["count"], 0)

    # Scopo: il default dell'ordine ha UNA sede (`GIORNALE_ORDINE_DEFAULT`, il
    #        preset di `vendite.giornale`, dal 2026-09-27): il service passa
    #        l'assenza, non ne scrive un secondo — fino a quel giorno qui era
    #        la gravita', e la stessa lista partiva in due modi.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_ordinamento_di_default_lo_decide_il_repository(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = (_RIGHE, 2, 0, 0)
        get_lotto_giornale(lotto_id=6260)
        self.assertIsNone(repo.list_giornale_lotto.call_args.kwargs["sort_by"])

    # Scopo: un lotto senza storia e' una risposta, non un errore.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_giornale_vuoto_non_e_un_errore(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = ([], 0, 0, 0)
        out = get_lotto_giornale(lotto_id=6260)
        self.assertEqual(out["count"], 0)
        self.assertEqual(out["results"], [])

    # ⭐ Ogni riga dichiara DI CHI e': senza, «il lotto dice che e' andata male»
    #    e «la fattura dice perche'» diventano due frasi indistinguibili nello
    #    stesso elenco — che e' la ragione per cui il pannello include le
    #    fatture.
    @patch("apps.vendite.services.vendite_service.VenditeRepository")
    def test_riga_dichiara_di_chi_e(self, repo_cls):
        repo = repo_cls.return_value
        repo.get_lotto.return_value = _LOTTO
        repo.list_giornale_lotto.return_value = (_RIGHE, 2, 0, 0)
        out = get_lotto_giornale(lotto_id=6260)
        entita = {(r["entity_type"], r["entity_id"]) for r in out["results"]}
        self.assertEqual(entita, {("LOTTO", 6260), ("FATTURA", 20024)})
