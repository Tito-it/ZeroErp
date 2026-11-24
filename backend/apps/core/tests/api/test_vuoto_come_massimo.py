# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: DOVE VA IL VUOTO quando una lista ordina, dichiarato nel catalogo
#        (`ui.lista_colonna.vuoto_ordinato_come_massimo`,
#        brief-db-lista-colonna-vuoto-in-ordine, decisioni di Tid del
#        2026-11-24): la regola del BB (`sql_order_direction`,
#        `sql_order_direction_lista`, `sql_order_clause`) e la base view che
#        registra la lettura della sua lista.
# Note: ⭐ Senza DB: la lettura (`vuoti_come_massimo_risolti`) e' finta, il BB
#       e la base view girano davvero. La catena sul DB vero (catalogo -> BB
#       -> righe ordinate) e' in `core/tests/db/test_vuoto_come_massimo_db.py`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) DirezioneTests.test_il_vuoto_come_il_massimo_nei_due_versi
2) DirezioneTests.test_senza_dichiarazione_il_vuoto_resta_il_minimo
3) ClausolaTests.test_la_colonna_dichiarata_ordina_il_vuoto_come_il_massimo
4) ClausolaTests.test_le_altre_colonne_della_lista_restano_sulla_regola_generale
5) ClausolaTests.test_il_default_dichiarato_porta_la_dichiarazione
6) ClausolaTests.test_fuori_da_una_lista_vale_la_regola_generale
7) ClausolaTests.test_la_lettura_e_una_per_richiesta
8) ClausolaTests.test_senza_ordinare_una_colonna_non_si_legge_niente
8a) ClausolaTests.test_default_ambiguo_fra_chiavi_dichiarate_in_modo_diverso
9) BaseViewTests.test_la_view_registra_la_lettura_della_sua_lista
10) BaseViewTests.test_senza_lista_codice_nessuna_lettura
11) BaseViewTests.test_anche_l_anonimo_riceve_la_dichiarazione
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.api.base_views import AdminAPIView
from apps.core.db._helpers import sql_order_clause, sql_order_direction
from apps.core.services.request_context import imposta_vuoti_come_massimo, set_request_context

_LETTURA = "apps.core.services.ordinamento_di_partenza.vuoti_come_massimo_risolti"
_ORDINAMENTO = "apps.core.services.ordinamento_di_partenza.ordinamento_risolto"
_MISURA = "apps.core.services.ordinamento_di_partenza.misura_risolta"
_COLONNE = {"valido_al": "t.valido_al", "codice": "t.codice"}


class DirezioneTests(SimpleTestCase):
    def test_il_vuoto_come_il_massimo_nei_due_versi(self) -> None:
        self.assertEqual(sql_order_direction("asc", vuoto_massimo=True), "ASC NULLS LAST")
        self.assertEqual(sql_order_direction("desc", vuoto_massimo=True), "DESC NULLS FIRST")
        self.assertEqual(
            sql_order_direction(None, default_desc=True, vuoto_massimo=True), "DESC NULLS FIRST",
        )

    def test_senza_dichiarazione_il_vuoto_resta_il_minimo(self) -> None:
        # La regola generale del 2026-07-19 non cambia.
        self.assertEqual(sql_order_direction("asc"), "ASC NULLS FIRST")
        self.assertEqual(sql_order_direction("desc"), "DESC NULLS LAST")


class ClausolaTests(SimpleTestCase):
    def setUp(self) -> None:
        set_request_context(request_id=None, idempotency_key=None)
        self.addCleanup(set_request_context, request_id=None, idempotency_key=None)
        self.letture = 0

    def _dichiara(self, *colonne: str) -> None:
        def lettura() -> frozenset[str]:
            self.letture += 1
            return frozenset(colonne)

        imposta_vuoti_come_massimo(lettura)

    def _clausola(self, order_by: str | None, order_dir: str | None, **kw) -> str:
        kw.setdefault("default", "t.codice")
        return sql_order_clause(order_by, order_dir, colonne=_COLONNE, tiebreak="t.id", **kw)

    def test_la_colonna_dichiarata_ordina_il_vuoto_come_il_massimo(self) -> None:
        self._dichiara("valido_al")
        self.assertEqual(
            self._clausola("valido_al", "asc"), "t.valido_al ASC NULLS LAST, t.id ASC",
        )
        self.assertEqual(
            self._clausola("valido_al", "desc"), "t.valido_al DESC NULLS FIRST, t.id DESC",
        )

    def test_le_altre_colonne_della_lista_restano_sulla_regola_generale(self) -> None:
        self._dichiara("valido_al")
        self.assertEqual(self._clausola("codice", "asc"), "t.codice ASC NULLS FIRST, t.id ASC")

    def test_il_default_dichiarato_porta_la_dichiarazione(self) -> None:
        # La richiesta non ordina, e il default della lista e' la colonna
        # dichiarata: per espressione o per chiave, come il suo verso.
        self._dichiara("valido_al")
        for default in ("t.valido_al", "valido_al"):
            with self.subTest(default=default):
                self.assertEqual(
                    self._clausola(None, None, default=default, default_desc=True),
                    f"{default} DESC NULLS FIRST, t.id DESC",
                )

    def test_default_ambiguo_fra_chiavi_dichiarate_in_modo_diverso(self) -> None:
        # Due chiavi con la stessa espressione del default, una sola
        # dichiarata: la direzione non puo' dipendere dall'ordine del
        # dizionario. Con le due dichiarate allo stesso modo, nessun dubbio.
        colonne = {"numero": "t.d", "valido_al": "t.d"}
        self._dichiara("valido_al")
        with self.assertRaises(RuntimeError):
            sql_order_clause(None, None, colonne=colonne, tiebreak="t.id", default="t.d")
        self._dichiara("valido_al", "numero")
        self.assertEqual(
            sql_order_clause(None, None, colonne=colonne, tiebreak="t.id", default="t.d"),
            "t.d ASC NULLS LAST, t.id ASC",
        )

    def test_fuori_da_una_lista_vale_la_regola_generale(self) -> None:
        # Nessuna lettura registrata: un servizio interno, un tool, un test.
        self.assertEqual(
            self._clausola("valido_al", "asc"), "t.valido_al ASC NULLS FIRST, t.id ASC",
        )

    def test_la_lettura_e_una_per_richiesta(self) -> None:
        self._dichiara("valido_al")
        self._clausola("valido_al", "asc")
        self._clausola("codice", "desc")
        self.assertEqual(self.letture, 1)

    def test_senza_ordinare_una_colonna_non_si_legge_niente(self) -> None:
        # Il default non e' una colonna della whitelist (`s.id`): niente da
        # chiedere al catalogo.
        self._dichiara("valido_al")
        self.assertEqual(self._clausola(None, None, default="t.id"), "t.id ASC NULLS FIRST")
        self.assertEqual(self.letture, 0)


def _vista(codice: str | None) -> type:
    class _Vista(AdminAPIView):
        authentication_classes: list = []
        permission_classes: list = []
        lista_codice = codice

        def get(self, request):
            return Response({"clausola": sql_order_clause(
                request.query_params.get("order_by"), request.query_params.get("order_dir"),
                colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            )})

    return _Vista


def _chiama(vista: type, query: str, *, anonimo: bool = False) -> Response:
    richiesta = APIRequestFactory().get(f"/api/v1/x/{query}")
    if not anonimo:
        force_authenticate(richiesta, user=SimpleNamespace(id=7, is_authenticated=True))
    return vista.as_view()(richiesta)


class BaseViewTests(SimpleTestCase):
    def setUp(self) -> None:
        set_request_context(request_id=None, idempotency_key=None)
        self.addCleanup(set_request_context, request_id=None, idempotency_key=None)
        self.partenza = {}
        for bersaglio, valore in ((_ORDINAMENTO, []), (_MISURA, 25)):
            patcher = patch(bersaglio, return_value=valore)
            self.partenza[bersaglio] = patcher.start()
            self.addCleanup(patcher.stop)

    def test_la_view_registra_la_lettura_della_sua_lista(self) -> None:
        with patch(_LETTURA, return_value=frozenset({"valido_al"})) as lettura:
            risposta = _chiama(_vista("amm.x"), "?order_by=valido_al&order_dir=asc")
        self.assertEqual(risposta.data["clausola"], "t.valido_al ASC NULLS LAST, t.id ASC")
        lettura.assert_called_once_with("amm.x")

    def test_senza_lista_codice_nessuna_lettura(self) -> None:
        with patch(_LETTURA, return_value=frozenset({"valido_al"})) as lettura:
            risposta = _chiama(_vista(None), "?order_by=valido_al&order_dir=asc")
        self.assertEqual(risposta.data["clausola"], "t.valido_al ASC NULLS FIRST, t.id ASC")
        lettura.assert_not_called()

    # ⭐ Dove va il vuoto e' un fatto del CATALOGO, uguale per ogni utente: lo
    #    riceve anche la lista letta da un anonimo (lo shop). Ordinamento e
    #    misura di partenza no: dipendono da chi legge (Tid, 2026-11-24).
    def test_anche_l_anonimo_riceve_la_dichiarazione(self) -> None:
        with patch(_LETTURA, return_value=frozenset({"valido_al"})) as lettura:
            risposta = _chiama(_vista("shop.x"), "?order_by=valido_al&order_dir=asc", anonimo=True)
        self.assertEqual(risposta.data["clausola"], "t.valido_al ASC NULLS LAST, t.id ASC")
        lettura.assert_called_once_with("shop.x")
        for lettore in self.partenza.values():
            lettore.assert_not_called()
