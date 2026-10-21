# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Base class per test API che usano Django test client +
#        SimpleTestCase. Mocka i side effect sul DB di ogni chiamata: `_set_gucs` di
#        JwtAuditAuthentication, il log delle richieste e la lingua, per evitare cursor.execute (vietato
#        in SimpleTestCase via DatabaseOperationForbidden).
#
#        I test esistenti continuano a mockare
#        rest_framework_simplejwt.authentication.JWTAuthentication.authenticate
#        per ritornare un user fittizio: il super().authenticate() della
#        nostra subclass viene cosi' interceptato. Senza questa base
#        class, il side effect `_set_gucs` proverebbe a chiamare
#        cursor.execute sul db reale e fallirebbe in SimpleTestCase.
#
#        Vedi guida: docs/it/guide/risorse-umane-e-accessi.md
#        sezione "Propagazione identita utente al database (GUC)".
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from uuid import uuid4

from django.test import Client, SimpleTestCase


class ClientApi(Client):
    """Il client di test che si comporta come il frontend: ogni POST porta
    un'`Idempotency-Key` nuova, se la chiamata non ne dichiara una sua.

    ⭐ Dal 2026-10-20 una POST che scrive senza key e' un 400 per costruzione
    (`_ApiViewBase.initial`, brief-be-verifica-documentazione-api §A5), e il
    frontend la mette su ogni POST nell'interceptor di `api.js`. Un test che
    chiama l'API deve fare lo stesso, o prova un client che non esiste.
    ⚠️ Chi vuole provare proprio l'ASSENZA della key usa `Client` semplice.
    """

    def post(self, path: str, data: Any = None, *args: Any, **extra: Any) -> Any:  # type: ignore[override]
        headers = dict(extra.pop("headers", None) or {})
        # I due nomi che il backend accetta (`get_idempotency_key`): una key
        # dichiarata col nome alternativo resta sua, e una prova di replay non
        # diventa muta per una key casuale che vince sulla sua.
        if not {"HTTP_IDEMPOTENCY_KEY", "HTTP_X_IDEMPOTENCY_KEY"} & extra.keys() and not any(
            k.lower() in ("idempotency-key", "x-idempotency-key") for k in headers
        ):
            headers["Idempotency-Key"] = f"test-{uuid4()}"
        return super().post(path, data, *args, headers=headers, **extra)


class JwtMockedApiTest(SimpleTestCase):
    """SimpleTestCase con mock automatico di JwtAuditAuthentication._set_gucs.

    Da usare al posto di SimpleTestCase per tutti i test API che
    chiamano il Django test client su endpoint `/api/*`. Tipico:

        class TestEmittentiFiscaliGetApi(JwtMockedApiTest):
            def setUp(self):
                super().setUp()
                self.client = Client()
            ...

    Il mock di `_set_gucs` impedisce che la auth class chiami
    `cursor.execute('SELECT set_config(...)')` durante l'auth dei
    test, evitando `DatabaseOperationForbidden`.

    I test che vogliono verificare il side effect (es. unit test
    di JwtAuditAuthentication stesso) non devono usare questa base
    class — patchano `_set_gucs` esplicitamente.

    ⭐ `self.client` e' un `ClientApi`: ogni POST porta l'`Idempotency-Key`,
    come dal frontend (§A5 del brief-be-verifica-documentazione-api).
    """

    client_class = ClientApi

    def setUp(self) -> None:
        super().setUp()
        patcher = patch(
            "apps.core.api.jwt_audit_authentication.JwtAuditAuthentication._set_gucs",
            return_value=None,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        # Il log delle richieste (`RequestLogMiddleware._insert_log`): e' il
        # SECONDO effetto sul database di ogni chiamata `/api/*`, dopo i GUC.
        # ⚠️ Non fallisce il test: il middleware cattura l'errore e lo LOGGA,
        #    quindi senza questo mock ogni chiamata stampava un traceback
        #    `DatabaseOperationForbidden` nell'output della suite, a decine per
        #    file. ⭐ Sede unica dal 2026-09-29: era ricopiato nel `setUp` di
        #    quindici classi figlie, e le altre facevano rumore (regola del 2).
        #    Il middleware ha i suoi test in
        #    `apps/core/tests/middleware/test_request_log_middleware.py`.
        log_patcher = patch(
            "apps.core.middleware.request_log_middleware.RequestLogMiddleware._insert_log",
            return_value=None,
        )
        log_patcher.start()
        self.addCleanup(log_patcher.stop)

        # La lingua dell'operatore sulla connessione (`UserLanguageMiddleware`,
        # GUC `myapp.user_language`): il TERZO effetto sul database, stesso
        # caso del log — catturato e loggato con il traceback, mai rosso.
        # Spento a monte, il middleware non marca la richiesta e il reset in
        # `process_response` non parte. Test suoi in
        # `apps/core/tests/middleware/test_user_language_middleware.py`.
        lingua_patcher = patch(
            "apps.core.middleware.user_language_middleware.UserLanguageMiddleware.process_request",
            return_value=None,
        )
        lingua_patcher.start()
        self.addCleanup(lingua_patcher.stop)

        # Gli obblighi della credenziale (`cancello_obblighi`, T-0 del brief
        # sicurezza): il QUARTO effetto sul database, a ogni richiesta col
        # Bearer che arriva in fondo all'autenticazione. ⭐ Come per lo scope
        # qui sotto, si mocka la LETTURA dei fatti («nessun obbligo»), non il
        # cancello: il suo codice gira in ogni test API. I test del cancello
        # sovrascrivono questo mock (`apps/core/tests/api/test_cancello_obblighi.py`).
        obblighi_patcher = patch(
            "apps.core.db.auth_repository.AuthRepository.get_fatti_obblighi",
            return_value={
                "deve_cambiare_password": False,
                "totp_obbligatorio": False,
                "totp_motivo": None,
                "totp_stato": "ASSENTE",
            },
        )
        obblighi_patcher.start()
        self.addCleanup(obblighi_patcher.stop)

        # Scope emittente dell'utente finto: UN emittente, cioe' l'operatore
        # configurato — lo scenario normale.
        #
        # ⚠️ Serve perche' dal 2026-08-18 `DomainAPIView.initial()` applica il
        #    cancello di perimetro emittente alle view che dichiarano
        #    `lista_codice`, e quel cancello interroga il database: senza
        #    questo mock ogni test API di lista chiederebbe lo scope a un DB
        #    che in `SimpleTestCase` non c'e'.
        #
        # ⭐ Si mocka la RISOLUZIONE DELLO SCOPE, non il guard: cosi' il codice
        #    del cancello viene eseguito davvero in ogni test API, e se un
        #    giorno rifiutasse a sproposito i test diventerebbero rossi. Un
        #    `patch` sul guard lo spegnerebbe e basta — e un presidio spento
        #    nei test e' un presidio che si scopre rotto in esercizio.
        #    Chi vuole verificare il cancello ATTIVO (scope multiplo) sovrascrive
        #    questo mock nel proprio test; il meccanismo ha comunque i suoi in
        #    `apps/core/tests/api/test_base_view_perimetro_emittente.py`.
        scope_patcher = patch(
            "apps.core.services.perimetro_emittente.PermissionResolver"
            ".get_emittenti_pk_ids",
            return_value=[1],
        )
        scope_patcher.start()
        self.addCleanup(scope_patcher.stop)
