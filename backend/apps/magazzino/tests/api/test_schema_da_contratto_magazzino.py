# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I contratti delle anagrafiche di magazzino (magazzini, ubicazioni,
#        lotti) e i loro schemi OpenAPI: ogni scrittura pubblica ESATTAMENTE le
#        chiavi che il service accetta.
# Note: I contratti sono le costanti `CREATE_KEYS_*` / `UPDATE_KEYS_*` che il
#       service passa a `validate_allowed_keys`: una sola sede per i due usi.
# ------------------------------------------------------------
"""
Indice test (0..N):
 0. test_ogni_schema_magazzino_pubblica_il_suo_contratto
"""

from django.test import SimpleTestCase


class SchemaDaContrattoMagazzinoTest(SimpleTestCase):

    # Scopo: sei schemi, sei contratti; nessuna chiave in piu' o in meno.
    def test_ogni_schema_magazzino_pubblica_il_suo_contratto(self):
        from apps.magazzino.api import views_anagrafiche as v
        from apps.magazzino.services import anagrafiche_magazzino_service as svc

        casi = {
            "magazzino create": (v._MAGAZZINO_CREATE_REQUEST, svc.CREATE_KEYS_MAGAZZINO),
            "magazzino update": (v._MAGAZZINO_UPDATE_REQUEST, svc.UPDATE_KEYS_MAGAZZINO),
            "ubicazione create": (v._UBICAZIONE_CREATE_REQUEST, svc.CREATE_KEYS_UBICAZIONE),
            "ubicazione update": (v._UBICAZIONE_UPDATE_REQUEST, svc.UPDATE_KEYS_UBICAZIONE),
            "lotto create": (v._LOTTO_CREATE_REQUEST, svc.CREATE_KEYS_LOTTO),
            "lotto update": (v._LOTTO_UPDATE_REQUEST, svc.UPDATE_KEYS_LOTTO),
        }
        for nome, (schema, contratto) in casi.items():
            with self.subTest(nome):
                self.assertEqual(set(schema.fields), set(contratto))
