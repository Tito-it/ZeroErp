# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il `codice` delle famiglie di documento modificabile dal CRUD, sul
#        DATABASE VERO: il service scrive il codice e traduce il vincolo
#        `uq_famiglie_documento_codice` col campo giusto. I test unitari
#        mockano il repository e l'IntegrityError: qui si prova che il nome del
#        vincolo che il service riconosce e' quello che PostgreSQL solleva.
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Le famiglie sono
#       SEED (contratto, non fotografia): se ne ritoccano due, in transazione
#       ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) FamiglieCodiceDbTests.test_il_codice_si_cambia_e_resta_unico
   Il PATCH del service cambia il `codice` (la vista lo rilegge); un codice
   gia' di un'altra famiglia e' `E_VENDITE_DUPLICATO` col campo `codice`, non
   una violazione generica.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class FamiglieCodiceDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("vendite.trgfn_famiglie_documento_default_codice()")

    def test_il_codice_si_cambia_e_resta_unico(self):
        from apps.vendite.services.famiglie_service import FamiglieDocumentoService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT id, codice FROM vendite.famiglie_documento ORDER BY id LIMIT 2")
                (prima, _), (seconda, codice_seconda) = cur.fetchall()
                svc = FamiglieDocumentoService()

                famiglia = svc.update_famiglia(prima, {"codice": "RICCODFAM"})
                self.assertEqual(famiglia["codice"], "RICCODFAM")

                with self.assertRaises(ServiceError) as ctx:
                    # Un savepoint: il rifiuto non deve spezzare la transazione
                    # del test, che resta da annullare in blocco.
                    with transaction.atomic():
                        svc.update_famiglia(prima, {"codice": codice_seconda})
                self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")
                self.assertEqual(ctx.exception.context.get("field"), "codice")
                self.assertNotEqual(prima, seconda)
                raise Annulla
        except Annulla:
            pass
