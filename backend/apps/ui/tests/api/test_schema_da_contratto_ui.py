# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I contratti dell'amministrazione liste (definizioni, colonne, preset)
#        e i loro schemi OpenAPI: ogni scrittura pubblica ESATTAMENTE le chiavi
#        che il service accetta.
# Note: ⚠️ Il preset in creazione pubblica il contratto MENO `lista_id`, che la
#       view prende dal percorso: e' l'unica differenza ammessa, e sta scritta.
# ------------------------------------------------------------
"""
Indice test (0..N):
 0. test_ogni_schema_ui_pubblica_il_suo_contratto
"""

from django.test import SimpleTestCase


class SchemaDaContrattoUiTest(SimpleTestCase):

    # Scopo: sei schemi, sei contratti; nessuna chiave in piu' o in meno.
    def test_ogni_schema_ui_pubblica_il_suo_contratto(self):
        from apps.ui.api import views_admin as v
        from apps.ui.services import (
            lista_colonna_admin_service as colonna,
            lista_definizione_admin_service as definizione,
            lista_preset_admin_service as preset,
        )

        casi = {
            "preset create": (v._PRESET_CREATE_REQUEST, preset.CREATE_KEYS - {"lista_id"}),
            "preset update": (v._PRESET_UPDATE_REQUEST, preset.UPDATE_KEYS),
            "definizione create": (v._DEFINIZIONE_CREATE_REQUEST, definizione.CREATE_KEYS),
            "definizione update": (v._DEFINIZIONE_UPDATE_REQUEST, definizione.UPDATE_KEYS),
            "colonna create": (v._COLONNA_CREATE_REQUEST, colonna.CREATE_KEYS),
            "colonna update": (v._COLONNA_UPDATE_REQUEST, colonna.UPDATE_KEYS),
        }
        for nome, (schema, contratto) in casi.items():
            with self.subTest(nome):
                self.assertEqual(set(schema.fields), set(contratto))
