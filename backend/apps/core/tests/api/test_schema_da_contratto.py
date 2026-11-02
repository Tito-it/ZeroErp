# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Contratto del building block `core/api/schema_da_contratto`: lo schema
#        OpenAPI di una scrittura pubblica ESATTAMENTE le chiavi del contratto
#        (piu' le speciali dichiarate), con il tipo del dizionario del dominio.
#        E i contratti email (bozze in core, template e account in
#        amm_software) confrontati con i loro schemi.
# Note: ⭐ Il test 0 nasce da un difetto trovato leggendo lo schema generato
#       (2026-09-26): le `speciali` fuori contratto sparivano. I confronti coi
#       contratti di vendite stanno in `vendite/tests/api/test_schema_da_contratto.py`.
# ------------------------------------------------------------
"""
Indice test (0..N):
 0. test_le_speciali_fuori_contratto_entrano_nello_schema
 1. test_una_chiave_senza_tipo_e_un_errore
 2. test_una_obbligatoria_fuori_contratto_e_un_errore
 3. test_obbligatorie_e_nullabili
 4. test_ogni_schema_email_pubblica_il_suo_contratto
"""

from django.test import SimpleTestCase
from rest_framework import serializers

from apps.core.api.schema_da_contratto import intero, schema_da_contratto, testo

# Un dizionario minimo, per provare il meccanismo senza un dominio vero.
_TIPI = {"a": (intero, False), "b": (testo, True), "c": (intero, False)}


class SchemaDaContrattoTest(SimpleTestCase):

    # Scopo: la chiave speciale non e' nel contratto, e deve esserci lo stesso.
    def test_le_speciali_fuori_contratto_entrano_nello_schema(self):
        schema = schema_da_contratto(
            "TestCoreSpeciali", {"a"}, tipi=_TIPI,
            speciali={"extra": serializers.DictField(required=False)},
        )
        self.assertEqual(set(schema.fields), {"a", "extra"})

    # Scopo: una chiave nuova nel contratto senza tipo ferma l'import.
    def test_una_chiave_senza_tipo_e_un_errore(self):
        with self.assertRaisesMessage(RuntimeError, "senza tipo ['nuova']"):
            schema_da_contratto("TestCoreSenzaTipo", {"a", "nuova"}, tipi=_TIPI)

    # Scopo: un'obbligatoria che il contratto non conosce e' un refuso.
    def test_una_obbligatoria_fuori_contratto_e_un_errore(self):
        with self.assertRaisesMessage(RuntimeError, "fuori contratto ['c']"):
            schema_da_contratto("TestCoreFuori", {"a"}, tipi=_TIPI, obbligatorie=("c",))

    # Scopo: obbligatoria = required senza null; le altre facoltative, null
    #        secondo il dizionario.
    def test_obbligatorie_e_nullabili(self):
        schema = schema_da_contratto(
            "TestCoreObbl", {"a", "b", "c"}, tipi=_TIPI, obbligatorie=("a",),
        )
        f = schema.fields
        self.assertTrue(f["a"].required)
        self.assertFalse(f["a"].allow_null)
        self.assertFalse(f["b"].required)
        self.assertTrue(f["b"].allow_null)
        self.assertFalse(f["c"].allow_null)

    # Scopo: i contratti email e i loro schemi non divergono.
    def test_ogni_schema_email_pubblica_il_suo_contratto(self):
        from apps.amm_software.api import email_views as amm
        from apps.core.api import email_views as core
        from apps.core.services.email_outbox_service import DRAFT_EDITABILI

        casi = {
            "bozza patch": (core._BOZZA_PATCH_REQUEST, DRAFT_EDITABILI),
            "account create": (amm._ACCOUNT_CREATE_REQUEST, amm._ACCOUNT_CREATE_KEYS),
            "account patch": (amm._ACCOUNT_PATCH_REQUEST, amm._ACCOUNT_PATCH_KEYS),
            "template create": (amm._TEMPLATE_CREATE_REQUEST, amm._TEMPLATE_CREATE_KEYS),
            "template patch": (amm._TEMPLATE_PATCH_REQUEST, amm._TEMPLATE_PATCH_KEYS),
        }
        for nome, (schema, contratto) in casi.items():
            with self.subTest(nome):
                self.assertEqual(set(schema.fields), set(contratto))
