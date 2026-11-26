# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo scope emittenti dell'operatore sul DB vero (giro 10-ter di
#        brief-db-porte-aperte-dalla-sola-guc, D-AA a, 2026-11-26):
#        «tutti gli emittenti» vale solo per un SUPER_ADMIN. Il GET dice
#        SINGLE senza emittente a chi non lo e', e il PUT GLOBAL per lui lo
#        rifiuta il DB con un 409 parlante, tradotto dal codice strutturato.
#        I test dell'API mockano il repository e non vedono la regola.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: l'operatore e il
#    SUPER_ADMIN che agisce sono costruiti, mai presi dal DB.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1. un operatore senza emittente si legge SINGLE, senza emittente, e
#      GLOBAL non gli e' offerto
#   2. il PUT GLOBAL per lui e' un 409 E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN
#      col messaggio del catalogo
#   3. a un SUPER_ADMIN GLOBAL e' offerto
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.amm_software.services.amm_software_service import AmmSoftwareService
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import Annulla, apri_super_admin_costruito, richiedi_db_provvisto

_CODICE = "E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN"


class EmittentiScopeDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: Un operatore che non e' SUPER_ADMIN, senza emittente: il builder
    #        lo costruisce cosi', prima che il contesto si apra.
    @staticmethod
    def _operatore_senza_emittente(cur, etichetta: str) -> int:
        cur.execute(
            "SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano(%s, false)", [etichetta],
        )
        return int(cur.fetchone()[0])

    def test_l_operatore_senza_emittente_si_legge_single(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                operatore = self._operatore_senza_emittente(cur, "scope single")
                apri_super_admin_costruito(cur, etichetta="scope single admin")

                scope = AmmSoftwareService().get_emittenti_scope(operatore)
                self.assertEqual(scope["scope_mode"], "SINGLE")
                self.assertEqual(scope["emittenti_ids"], [])
                self.assertNotIn("GLOBAL", scope["allowed_scope_modes"])
                raise Annulla
        except Annulla:
            pass

    def test_global_per_chi_non_e_super_admin_e_un_409(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                operatore = self._operatore_senza_emittente(cur, "scope global")
                apri_super_admin_costruito(cur, etichetta="scope global admin")

                with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                    AmmSoftwareService().put_emittenti_scope(operatore, {"scope_mode": "GLOBAL"})
                errore = ErrorTranslator.to_api_error(ctx.exception)
                self.assertEqual(errore.code, _CODICE)
                self.assertEqual(ErrorPolicyRegistry.resolve(_CODICE).http_status, 409)
                raise Annulla
        except Annulla:
            pass

    def test_al_super_admin_global_e_offerto(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                admin = apri_super_admin_costruito(cur, etichetta="scope admin")

                scope = AmmSoftwareService().get_emittenti_scope(admin)
                self.assertIn("GLOBAL", scope["allowed_scope_modes"])
                raise Annulla
        except Annulla:
            pass
