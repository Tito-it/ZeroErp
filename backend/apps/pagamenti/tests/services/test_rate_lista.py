# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del pezzo C di D19 — `GET /pagamenti/rate/`, la lista paginata
#        delle rate col saldo dalla base unica (la quarta lettura di
#        `saldi_service`), con il repository FINTO: si prova cio' che il
#        service decide (whitelist, ricerca, forma dell'envelope) e cio' che
#        passa intatto al repository.
# Note: ⚠️ Il caso «101 non porta 1010» e il saldo letto SULLA PAGINA si provano
#       sul database provvisto (`tests/db/test_rate_lista_db.py`): un mock non
#       sa dire se un `=` e' davvero un `=`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) RateListaTests.test_envelope_con_results_e_count
2) RateListaTests.test_ordinamento_fuori_whitelist_rifiutato
3) RateListaTests.test_senza_ordinamento_decide_il_repository
4) RateListaTests.test_direzione_normalizzata_in_minuscolo
5) RateListaTests.test_ricerca_corta_non_e_un_errore
6) RateListaTests.test_solo_aperte_arriva_come_booleano
6-bis) RateListaTests.test_solo_numerate_e_un_perimetro_non_un_filtro
7) RateListaTests.test_i_criteri_passano_intatti
8) RateListaTests.test_natura_normalizzata_in_maiuscolo
9) WhitelistTests.test_i_saldi_non_sono_ordinabili
10) WhitelistTests.test_le_date_hanno_il_verso_naturale_desc
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.db.pagamenti_repository import (
    RATE_SORT_COLONNE_DATA,
    RATE_SORT_COLUMNS,
)
from apps.pagamenti.services import saldi_service

_RIGA = {
    "scadenza_id": 1301,
    "fattura_id": 77,
    "numero_rata": 1,
    "data_scadenza": "2026-09-30",
    "importo": Decimal("610.00"),
    "numero_documento": "101 - A",
    "residuo": Decimal("400.00"),
    "in_lavorazione": Decimal("0.00"),
    "incassato": Decimal("210.00"),
    "has_movimenti": True,
}


class RateListaTests(SimpleTestCase):
    def setUp(self) -> None:
        self.repo = MagicMock()
        self.repo.list_rate_paginata.return_value = ([dict(_RIGA)], 1)
        patcher = patch.object(saldi_service, "PagamentiRepository", return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: ⭐ L'envelope e' `{count, results}` — la forma che `useListaStoreCore`
    #        legge. Un `count` che manca e' una lista senza paginator, senza
    #        errore (il difetto del lookup famiglie, api.md).
    def test_envelope_con_results_e_count(self):
        esito = saldi_service.list_rate(auth_user_id=5, limit=25)
        self.assertEqual(esito["count"], 1)
        self.assertEqual(esito["results"][0]["scadenza_id"], 1301)
        # I tre saldi col nome della base unica, non `saldo`.
        for campo in saldi_service.CAMPI_SALDO:
            self.assertIn(campo, esito["results"][0])

    def test_ordinamento_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            saldi_service.list_rate(auth_user_id=5, limit=25, order_by="residuo", order_dir="asc")
        self.assertEqual(ctx.exception.code, "E_PAGAMENTI_VALIDATION")
        self.repo.list_rate_paginata.assert_not_called()

    # Scopo: `order_by` assente e' legittimo: l'ordine lo decide il repository
    #        (il default a catalogo, `data_scadenza ASC`), e al repository
    #        arrivano `None`, non un default inventato qui.
    def test_senza_ordinamento_decide_il_repository(self):
        saldi_service.list_rate(auth_user_id=5, limit=25)
        kwargs = self.repo.list_rate_paginata.call_args.kwargs
        self.assertIsNone(kwargs["order_by"])
        self.assertIsNone(kwargs["order_dir"])

    def test_direzione_normalizzata_in_minuscolo(self):
        saldi_service.list_rate(auth_user_id=5, limit=25, order_by="importo", order_dir="DESC")
        kwargs = self.repo.list_rate_paginata.call_args.kwargs
        self.assertEqual(kwargs["order_dir"], "desc")

    # Scopo: la ricerca libera corta NON e' un errore: arriva al repository, e
    #        sotto la soglia del catalogo della lista la ignora il BB di ricerca
    #        (brief-db-be-fe-ricerca-soglia-per-lista §6 a, Tid 2026-09-26 —
    #        fino ad allora qui era un 400).
    def test_ricerca_corta_non_e_un_errore(self):
        saldi_service.list_rate(auth_user_id=5, limit=25, search="ro")
        self.assertEqual(self.repo.list_rate_paginata.call_args.kwargs["search"], "ro")

    # Scopo: `solo_aperte` e' SUPPORTATO (P-3 c'e'): al repository arriva un
    #        booleano, e `None` vale `False` — nessun 400 «non supportato».
    def test_solo_aperte_arriva_come_booleano(self):
        saldi_service.list_rate(auth_user_id=5, limit=25, solo_aperte=None)
        self.assertIs(self.repo.list_rate_paginata.call_args.kwargs["solo_aperte"], False)
        saldi_service.list_rate(auth_user_id=5, limit=25, solo_aperte=True)
        self.assertIs(self.repo.list_rate_paginata.call_args.kwargs["solo_aperte"], True)

    # Scopo: ⛔ `solo_numerate` NON segue la forma di `solo_aperte`, ed e' il
    #        test che tiene fermo il perche' (decisione di Tid, 23/09). E' un
    #        PERIMETRO di dominio — la rata di una bozza non e' un credito —
    #        quindi «assente» significa APPLICA LA REGOLA, non «falso»:
    #        `None` -> `True`. `solo_aperte`, che e' un filtro vero, resta
    #        `None` -> `False` (il test qui sopra).
    # ⚠️ Fino al 23/09 la regola la mandava il FRONTEND a ogni chiamata, cioe'
    #        era vera solo per il client che se la ricordava; questo test
    #        pinnava quel mondo (`None` -> `False`). Il predicato
    #        (`numero IS NOT NULL`) si prova sul DB provvisto, costruendo la
    #        bozza.
    def test_solo_numerate_e_un_perimetro_non_un_filtro(self):
        saldi_service.list_rate(auth_user_id=5, limit=25, solo_numerate=None)
        self.assertIs(self.repo.list_rate_paginata.call_args.kwargs["solo_numerate"], True)
        # La via d'uscita esiste, ma va CHIESTA.
        saldi_service.list_rate(auth_user_id=5, limit=25, solo_numerate=False)
        self.assertIs(self.repo.list_rate_paginata.call_args.kwargs["solo_numerate"], False)
        saldi_service.list_rate(auth_user_id=5, limit=25, solo_numerate=True)
        self.assertIs(self.repo.list_rate_paginata.call_args.kwargs["solo_numerate"], True)

    # Scopo: i criteri del picker (cliente, numero ESATTO, serie, anno) e lo
    #        scope dell'operatore passano intatti: il service non li interpreta.
    def test_i_criteri_passano_intatti(self):
        saldi_service.list_rate(
            auth_user_id=5, limit=10, offset=20,
            billing_account_id=3, fattura_numero=101, serie="A", anno=2026,
        )
        kwargs = self.repo.list_rate_paginata.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 5)
        self.assertEqual(kwargs["billing_account_id"], 3)
        self.assertEqual(kwargs["fattura_numero"], 101)
        self.assertEqual(kwargs["serie"], "A")
        self.assertEqual(kwargs["anno"], 2026)
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 20))

    def test_natura_normalizzata_in_maiuscolo(self):
        saldi_service.list_rate(auth_user_id=None, limit=25, natura_doc_codice="nota_credito")
        self.assertEqual(
            self.repo.list_rate_paginata.call_args.kwargs["natura_doc_codice"], "NOTA_CREDITO"
        )


class WhitelistTests(SimpleTestCase):
    # Scopo: ⛔ I tre saldi NON stanno nella whitelist: arrivano dal nucleo DOPO
    #        la pagina, e un `ORDER BY residuo` sarebbe un 500 sul primo click.
    #        Il seed li dichiara `ordinabile = f` per la stessa ragione.
    def test_i_saldi_non_sono_ordinabili(self):
        for campo in saldi_service.CAMPI_SALDO:
            self.assertNotIn(campo, RATE_SORT_COLUMNS)

    # Scopo: le colonne data della lista hanno il verso naturale DESC (regola di
    #        Tid del 2026-09-02) e sono chiavi della whitelist: un nome che non
    #        c'e' nella whitelist non ordinerebbe niente.
    def test_le_date_hanno_il_verso_naturale_desc(self):
        self.assertEqual(RATE_SORT_COLONNE_DATA, frozenset({"data", "data_scadenza"}))
        for campo in RATE_SORT_COLONNE_DATA:
            self.assertIn(campo, RATE_SORT_COLUMNS)
