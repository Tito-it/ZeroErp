# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Base class per test API che usano Django test client +
#        SimpleTestCase. Mocka il side effect `_set_gucs` di
#        JwtAuditAuthentication per evitare cursor.execute (vietato
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

from unittest.mock import patch

from django.test import SimpleTestCase


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
    """

    def setUp(self) -> None:
        super().setUp()
        patcher = patch(
            "apps.core.api.jwt_audit_authentication.JwtAuditAuthentication._set_gucs",
            return_value=None,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

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
