# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le GET/HEAD delle API girano davvero in sola lettura, attraverso TUTTA
#        la catena dei middleware (brief-be-letture-in-transazione-sola-lettura
#        §4, presidi 1 e 3). Le view sono FABBRICATE qui, su un urlconf di
#        prova: il presidio non dipende da nessuna view vera.
#
# ⭐ PERCHE' SUL DB VERO: la garanzia e' di PostgreSQL. E perche' dalla catena
#    intera: se un middleware piu' esterno aprisse una transazione, il nostro
#    salterebbe (non si puo' impostare la sola lettura a transazione iniziata),
#    e solo una richiesta vera se ne accorge — il test 2 legge
#    `transaction_read_only` dalla view.
# ⚠️ Fuori da `transaction.atomic()`, e voluto: dentro una transazione gia'
#    aperta il middleware salta (e' il caso dei test che avvolgono il client).
#    La scrittura tentata non puo' entrare in nessun caso (`destinatario` NOT
#    NULL), come in `test_sola_lettura_db`.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_una_get_che_scrive_e_fermata   (presidio 1)
     500 `E_SCRITTURA_IN_LETTURA`, il nome della view nel log.
2. test_la_get_legge_in_sola_lettura_e_la_head_anche
     `transaction_read_only = on` dentro la view, dalla catena intera.
3. test_dopo_la_get_la_post_scrive   (presidio 3)
     stessa connessione: la POST non e' in sola lettura.
4. test_la_get_con_eccezione_dichiarata_non_e_in_sola_lettura
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection
from django.test import override_settings
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.core.tests.db_e2e import richiedi_db_provvisto

_INSERT_IMPOSSIBILE = "INSERT INTO config.email_log (destinatario) VALUES (NULL)"


def _sola_lettura() -> str:
    with connection.cursor() as cur:
        cur.execute("SHOW transaction_read_only")
        return cur.fetchone()[0]


class _Base(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]


class _VistaCheScrive(_Base):
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute(_INSERT_IMPOSSIBILE)
        return Response({"scritto": True})  # pragma: no cover


class _VistaCheLegge(_Base):
    def get(self, request):
        return Response({"sola_lettura": _sola_lettura()})

    def head(self, request):
        return Response(headers={"X-Sola-Lettura": _sola_lettura()})

    def post(self, request):
        return Response({"sola_lettura": _sola_lettura()})


class _VistaDichiarata(_Base):
    scrittura_in_get = "solo per il test: la GET dichiarata non e' in sola lettura"

    def get(self, request):
        return Response({"sola_lettura": _sola_lettura()})


urlpatterns = [
    path("api/test-sola-lettura/scrive/", _VistaCheScrive.as_view()),
    path("api/test-sola-lettura/legge/", _VistaCheLegge.as_view()),
    path("api/test-sola-lettura/dichiarata/", _VistaDichiarata.as_view()),
]


class SolaLetturaMiddlewareDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        self.enterContext(override_settings(ROOT_URLCONF=__name__, REQUEST_LOG_ENABLED=False))
        self.client = APIClient()
        self.assertFalse(connection.in_atomic_block, "il presidio gira fuori da una transazione")

    # 1.
    def test_una_get_che_scrive_e_fermata(self) -> None:
        with self.assertLogs("apps.core.db.sola_lettura", level="ERROR") as log:
            r = self.client.get("/api/test-sola-lettura/scrive/")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["error"]["code"], "E_SCRITTURA_IN_LETTURA")
        self.assertIn("_VistaCheScrive", "\n".join(log.output))
        # La transazione e' chiusa: la connessione non resta in sola lettura.
        self.assertFalse(connection.in_atomic_block)
        self.assertEqual(_sola_lettura(), "off")

    # 2.
    def test_la_get_legge_in_sola_lettura_e_la_head_anche(self) -> None:
        r = self.client.get("/api/test-sola-lettura/legge/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["sola_lettura"], "on")
        r = self.client.head("/api/test-sola-lettura/legge/")
        self.assertEqual(r["X-Sola-Lettura"], "on")

    # 3. ⛔ Il rischio del «per sessione»: con `CONN_MAX_AGE` la connessione
    #    passa alla richiesta dopo.
    def test_dopo_la_get_la_post_scrive(self) -> None:
        self.assertEqual(self.client.get("/api/test-sola-lettura/legge/").json()["sola_lettura"], "on")
        r = self.client.post("/api/test-sola-lettura/legge/", {}, format="json")
        self.assertEqual(r.json()["sola_lettura"], "off")

    # 4.
    def test_la_get_con_eccezione_dichiarata_non_e_in_sola_lettura(self) -> None:
        r = self.client.get("/api/test-sola-lettura/dichiarata/")
        self.assertEqual(r.json()["sola_lettura"], "off")
