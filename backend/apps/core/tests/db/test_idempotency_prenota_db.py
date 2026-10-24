# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `handle_post_json` in modalita' forte sul DATABASE PROVVISTO, dopo
#        BE-1 e BE-2 di brief-be-verifica-documentazione-api (2026-10-24): la
#        prenotazione passa da `dbops.fn_idempotency_prenota`, e un'operazione
#        ATOMICA scrive l'esito nella sua stessa transazione. Presidia cio' che
#        un mock non vede:
#          · la firma a cinque argomenti, con la ripresa dichiarata;
#          · i tre esiti (ESEGUI, REPLAY, IN_CORSO) e il rifiuto 400
#            `E_IDEMPOTENCY_KEY_RIUSATA` su un altro endpoint (D7);
#          · la ripresa di una key orfana oltre la soglia: si' per ATOMICA, no
#            per A_PASSI (D6, §I.7.5);
#          · un fallimento ATOMICA non lascia niente dell'operazione, e la key
#            e' `failed` (scritta FUORI dall'atomic);
#          · il diario dopo un errore DB catturato si scrive a transazione
#            chiusa, non dentro quella abortita;
#          · la soglia letta da `dbops.fn_idempotency_soglia_secondi` (§I.11),
#            con la chiamata vera: un mock non vede firma e nome.
# Note: ⚠️ Il caso si COSTRUISCE (regola zero): key generate dal test,
#       `prenotata_at` retrodatato per la ripresa. Il diario vero non si
#       scrive: `_scrivi_diario` e' sostituito da una sonda che interroga la
#       connessione e dice se la transazione era sana.
#       Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) PrenotaDbTests.test_prima_esegue_poi_rimanda_la_risposta
2) PrenotaDbTests.test_la_key_su_un_altro_endpoint_e_400
3) PrenotaDbTests.test_in_corso_entro_la_soglia_e_409
4) PrenotaDbTests.test_orfana_oltre_la_soglia_si_riprende_solo_se_atomica
5) PrenotaDbTests.test_fallimento_atomica_annulla_tutto_e_la_key_e_failed
6) PrenotaDbTests.test_il_diario_si_scrive_a_transazione_chiusa
7) PrenotaDbTests.test_la_soglia_si_legge_dalla_funzione
"""
from __future__ import annotations

import json
import unittest
from collections.abc import Callable
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import AnonymousUser
from django.db import connection, transaction
from django.http import JsonResponse
from django.test import RequestFactory, override_settings

from apps.core.api.endpoint_helpers import UnitaDiLavoro, handle_post_json
from apps.core.services.error_manager import ErrorManager
from apps.core.services.idempotency_store import IdempotencyStore
from apps.core.services.request_context import clear_request_context, set_request_context
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto


class _Annulla(Exception):
    """Porta fuori dall'atomic del test, che cosi' si annulla sempre."""


class PrenotaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("dbops.fn_idempotency_prenota(text,integer,text,uuid,boolean)")
        richiedi_db_provvisto("dbops.fn_idempotency_soglia_secondi()")
        super().setUpClass()

    def setUp(self) -> None:
        # `override_settings` decora solo le classi di Django: qui il test e'
        # un `unittest.TestCase`, per non far creare al runner un DB usa-e-getta.
        self.enterContext(override_settings(API_STRONG_IDEMPOTENCY_ENABLED=True))
        self.key = f"betest-idem-{uuid4()}"

    def tearDown(self) -> None:
        clear_request_context()

    # Scopo: esegue `azione()` in una transazione SEMPRE annullata.
    def _annullato(self, azione: Callable[[], None]) -> None:
        try:
            with transaction.atomic():
                azione()
                raise _Annulla
        except _Annulla:
            pass

    def _post(
        self,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        path: str = "/api/v1/betest/idem/",
        unita: UnitaDiLavoro = UnitaDiLavoro.ATOMICA,
    ) -> JsonResponse:
        request = RequestFactory().post(path, data=json.dumps({}), content_type="application/json")
        request.user = AnonymousUser()
        set_request_context(request_id=str(uuid4()), idempotency_key=self.key)
        return handle_post_json(
            request, handler=handler, require_idempotency_key=True, unita_di_lavoro=unita,
        )

    def _riga(self) -> tuple[str, str, Any]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT status, endpoint, auth_user_id FROM dbops.idempotency_keys"
                " WHERE idempotency_key = %s",
                [self.key],
            )
            return cur.fetchone()

    # ⚠️ Oltre la soglia VERA, non un intervallo fisso: la funzione ammette
    #    soglie fino a 999999 s, e `1 day` sotto una soglia lecita non
    #    retrodaterebbe niente.
    def _retrodata(self) -> None:
        oltre = IdempotencyStore.soglia_ripresa_secondi() + 1
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE dbops.idempotency_keys"
                " SET prenotata_at = now() - make_interval(secs => %s)"
                " WHERE idempotency_key = %s",
                [oltre, self.key],
            )

    def test_prima_esegue_poi_rimanda_la_risposta(self) -> None:
        def azione() -> None:
            chiamate: list[int] = []
            prima = self._post(lambda _p: chiamate.append(1) or {"n": len(chiamate)})
            seconda = self._post(lambda _p: chiamate.append(1) or {"n": len(chiamate)})
            self.assertEqual(prima.status_code, 200)
            self.assertEqual(seconda.status_code, 200)
            self.assertEqual(seconda["X-Idempotency-Replayed"], "1")
            self.assertEqual(json.loads(seconda.content)["data"], {"n": 1})
            self.assertEqual(chiamate, [1])
            self.assertEqual(self._riga(), ("completed", "POST /api/v1/betest/idem/", None))

        self._annullato(azione)

    def test_la_key_su_un_altro_endpoint_e_400(self) -> None:
        def azione() -> None:
            self.assertEqual(self._post(lambda _p: {}).status_code, 200)
            altra = self._post(lambda _p: {}, path="/api/v1/betest/altro/")
            self.assertEqual(altra.status_code, 400)
            self.assertEqual(json.loads(altra.content)["error"]["code"], "E_IDEMPOTENCY_KEY_RIUSATA")

        self._annullato(azione)

    def test_in_corso_entro_la_soglia_e_409(self) -> None:
        def azione() -> None:
            # La prima richiesta e' ancora dentro l'handler quando arriva la seconda.
            def handler(_p: dict[str, Any]) -> dict[str, Any]:
                seconda = self._post(lambda _q: {})
                self.assertEqual(seconda.status_code, 409)
                self.assertEqual(
                    json.loads(seconda.content)["error"]["code"], "E_IDEMPOTENCY_IN_PROGRESS",
                )
                return {}

            self.assertEqual(self._post(handler).status_code, 200)

        self._annullato(azione)

    def test_orfana_oltre_la_soglia_si_riprende_solo_se_atomica(self) -> None:
        for unita, atteso in ((UnitaDiLavoro.A_PASSI, 409), (UnitaDiLavoro.ATOMICA, 200)):
            with self.subTest(unita=unita):
                self.key = f"betest-idem-{uuid4()}"

                def azione(unita: UnitaDiLavoro = unita, atteso: int = atteso) -> None:
                    # Il worker che l'aveva prenotata e' morto senza esito.
                    IdempotencyStore.claim_or_replay(
                        idempotency_key=self.key, request_id=str(uuid4()), auth_user_id=None,
                        endpoint="POST /api/v1/betest/idem/", ripresa_ammessa=True,
                    )
                    self._retrodata()
                    self.assertEqual(self._post(lambda _p: {}, unita=unita).status_code, atteso)

                self._annullato(azione)

    def test_fallimento_atomica_annulla_tutto_e_la_key_e_failed(self) -> None:
        def azione() -> None:
            def scrive_e_fallisce(_p: dict[str, Any]) -> dict[str, Any]:
                with connection.cursor() as cur:
                    cur.execute("CREATE TEMP TABLE _betest_idem (x int) ON COMMIT DROP")
                    cur.execute("INSERT INTO _betest_idem VALUES (1)")
                raise ServiceError(code="E_VALIDATION_INPUT", message="no")

            risposta = self._post(scrive_e_fallisce)
            self.assertEqual(risposta.status_code, 400)
            with connection.cursor() as cur:
                cur.execute("SELECT to_regclass('pg_temp._betest_idem')")
                self.assertIsNone(cur.fetchone()[0])
            self.assertEqual(self._riga()[0], "failed")

        self._annullato(azione)

    @override_settings(ERROR_LOG_DB_ENABLED=True)
    def test_il_diario_si_scrive_a_transazione_chiusa(self) -> None:
        sane: list[bool] = []

        # La sonda al posto della scrittura vera: la stessa connessione deve
        # rispondere, cioe' la transazione abortita deve essere gia' chiusa.
        def sonda(riga: tuple[str, str, str, str]) -> None:
            if riga[2] != "E_BETEST_DIARIO":
                return
            try:
                with transaction.atomic(), connection.cursor() as cur:
                    cur.execute("SELECT 1")
                sane.append(True)
            except Exception:
                sane.append(False)

        def azione() -> None:
            def errore_catturato(_p: dict[str, Any]) -> dict[str, Any]:
                try:
                    with connection.cursor() as cur:
                        cur.execute("SELECT 1/0")
                except Exception:
                    ErrorManager.log_error_only(code="E_BETEST_DIARIO", context={})
                raise ServiceError(code="E_VALIDATION_INPUT", message="no")

            with patch.object(ErrorManager, "_scrivi_diario", side_effect=sonda):
                self.assertEqual(self._post(errore_catturato).status_code, 400)

        self._annullato(azione)
        self.assertEqual(sane, [True])

    # ⭐ Il valore e' del seed: qui si prova il legame, non il numero — un
    #    intero positivo, cioe' una soglia che la funzione ha validato.
    def test_la_soglia_si_legge_dalla_funzione(self) -> None:
        soglia = IdempotencyStore.soglia_ripresa_secondi()
        self.assertIsInstance(soglia, int)
        self.assertGreater(soglia, 0)
