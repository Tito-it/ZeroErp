# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la PARTENZA di una lista (ordinamento e misura del preset) su ogni
#        porta, e il cancello di perimetro solo su `DomainAPIView` (residuo di
#        BE25 (2) di brief-db-revisione-ui, ok Tid 2026-11-22). Fino a quel
#        giorno `lista_codice` accendeva tutte e due le cose dentro
#        `DomainAPIView`: le liste dell'amministrazione (`AdminAPIView`), esenti
#        dal cancello per decisione (brief perimetro-emittente, passo C-2),
#        restavano senza partenza, e il FE ne teneva le copie.
# Note: ⭐ Senza DB: le due letture (`ordinamento_risolto`, `misura_risolta`) e
#       il cancello sono finti, la base view gira davvero su una richiesta DRF
#       vera. La catena sul DB vero (le 29 rotte, 2026-11-22) e' nel brief.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) PartenzaSuOgniPortaTests.test_admin_riceve_la_partenza_senza_cancello
2) PartenzaSuOgniPortaTests.test_dominio_chiama_il_cancello_prima_della_partenza
3) PartenzaSuOgniPortaTests.test_un_cancello_che_rifiuta_non_legge_la_partenza
4) PartenzaSuOgniPortaTests.test_senza_lista_codice_nessuna_partenza
5) PartenzaSuOgniPortaTests.test_admin_rilegge_senza_la_chiave_rifiutata
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.api.base_views import AdminAPIView, DomainAPIView
from apps.core.api.payload_validators import pagina_da_query
from apps.core.db._helpers import colonna_ordinamento
from apps.core.services.request_context import get_ordinamento_applicato, set_request_context
from apps.core.services.service_errors import ServiceError

_ORDINAMENTO = "apps.core.services.ordinamento_di_partenza.ordinamento_risolto"
_MISURA = "apps.core.services.ordinamento_di_partenza.misura_risolta"
_CANCELLO = "apps.core.services.perimetro_emittente.guard_lista_per_codice"
_VOCE = {"col": "data", "dir": "desc", "campo_sorgente": "data_insert"}
_WHITELIST = {"data_insert": "t.data_insert", "codice": "t.codice"}


# Scopo: cio' che la view ha visto: la finestra, l'ordinamento, e l'ordine
#        delle letture (cancello, partenza).
def _lista(base: type) -> type:
    class _Vista(base):
        authentication_classes: list = []
        permission_classes: list = []
        lista_codice = "amm.x"
        area_funzionale = "core"

        def get(self, request):
            limit, _offset = pagina_da_query(request.query_params)
            colonna_ordinamento(request.query_params.get("order_by"), _WHITELIST)
            return Response({
                "limit": limit,
                "order_by": request.query_params.get("order_by"),
                "order_dir": request.query_params.get("order_dir"),
                "applicato": get_ordinamento_applicato(),
            })

    return _Vista


def _chiama(vista: type, query: str = "") -> Response:
    richiesta = APIRequestFactory().get(f"/api/v1/x/{query}")
    force_authenticate(richiesta, user=SimpleNamespace(id=7, is_authenticated=True))
    return vista.as_view()(richiesta)


class PartenzaSuOgniPortaTests(SimpleTestCase):
    def setUp(self) -> None:
        set_request_context(request_id=None, idempotency_key=None)
        self.addCleanup(set_request_context, request_id=None, idempotency_key=None)
        self.letture: list[str] = []
        for bersaglio, nome, valore in (
            (_ORDINAMENTO, "ordinamento", [_VOCE]),
            (_MISURA, "misura", 40),
        ):
            patcher = patch(bersaglio, side_effect=self._registra(nome, valore))
            setattr(self, f"m_{nome}", patcher.start())
            self.addCleanup(patcher.stop)

    def _registra(self, nome: str, valore):
        def lettura(*_a, **_k):
            self.letture.append(nome)
            return valore
        return lettura

    def test_admin_riceve_la_partenza_senza_cancello(self) -> None:
        with patch(_CANCELLO) as cancello:
            resp = _chiama(_lista(AdminAPIView))
        self.assertEqual(resp.status_code, 200)
        cancello.assert_not_called()
        self.assertEqual(
            (resp.data["order_by"], resp.data["order_dir"], resp.data["limit"]),
            ("data_insert", "desc", 40),
        )
        self.assertEqual(
            resp.data["applicato"],
            {"order_by": "data_insert", "order_dir": "desc", "col": "data"},
        )

    def test_dominio_chiama_il_cancello_prima_della_partenza(self) -> None:
        with patch(_CANCELLO, side_effect=lambda **_k: self.letture.append("cancello")) as cancello:
            resp = _chiama(_lista(DomainAPIView))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(cancello.call_args.kwargs["lista_codice"], "amm.x")
        self.assertEqual(self.letture[:2], ["cancello", "ordinamento"])
        self.assertEqual(resp.data["order_by"], "data_insert")

    # Una lista che non si puo' leggere non si ordina: la partenza non si
    # legge nemmeno.
    def test_un_cancello_che_rifiuta_non_legge_la_partenza(self) -> None:
        rifiuto = ServiceError(code="E_UI_LISTA_EMITTENTE_DA_SCEGLIERE", message="x")
        # Il rifiuto esce come `ServiceError`: lo traduce il middleware.
        with patch(_CANCELLO, side_effect=rifiuto), self.assertRaises(ServiceError):
            _chiama(_lista(DomainAPIView))
        self.assertEqual(self.letture, [])

    def test_senza_lista_codice_nessuna_partenza(self) -> None:
        vista = _lista(AdminAPIView)
        vista.lista_codice = None
        resp = _chiama(vista)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["order_by"])
        self.assertEqual(self.letture, [])

    # La rilettura dopo una chiave del preset che il repository rifiuta stava
    # su `DomainAPIView`: e' salita con la partenza.
    def test_admin_rilegge_senza_la_chiave_rifiutata(self) -> None:
        self.m_ordinamento.side_effect = lambda *_a, **_k: [
            {"col": "fuori", "dir": "desc", "campo_sorgente": "campo_fuori"},
        ]
        with self.assertLogs("apps.core.services.ordinamento_di_partenza", "WARNING"):
            resp = _chiama(_lista(AdminAPIView))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["order_by"])
        self.assertIsNone(resp.data["applicato"])
