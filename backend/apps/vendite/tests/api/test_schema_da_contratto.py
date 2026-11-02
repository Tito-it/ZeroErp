# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I contratti di vendite e i loro schemi OpenAPI: ogni scrittura dei sei
#        documenti pubblica ESATTAMENTE le chiavi che il service accetta — ne'
#        una in piu' (un campo documentato che il service scarta in silenzio)
#        ne' una in meno.
# Note: Il meccanismo (`core/api/schema_da_contratto`) ha i suoi test in
#       `core/tests/api/test_schema_da_contratto.py`.
# ------------------------------------------------------------
"""
Indice test (0..N):
 0. test_ogni_schema_pubblica_il_suo_contratto
 1. test_la_riga_di_preventivo_non_pubblica_i_campi_ritirati
"""

from django.test import SimpleTestCase


class SchemaDaContrattoTest(SimpleTestCase):

    # Scopo: i contratti dei sei documenti (preventivi, contratti, offerte,
    #        ordini, ddt, resi) piu' la PATCH dei componenti: lo schema che la
    #        view dichiara ha le chiavi del contratto, e in piu' solo le
    #        speciali dichiarate.
    def test_ogni_schema_pubblica_il_suo_contratto(self):
        from apps.vendite.api import (
            _componenti_schema,
            preventivi_views,
            views_contratti,
            views_ddt,
            views_offerte,
            views_ordini,
            views_resi,
        )
        from apps.vendite.services import (
            contratti_service,
            ddt_service,
            offerte_service,
            ordini_service,
            preventivi_service,
            resi_service,
        )
        from apps.vendite.services._componenti_service_helpers import COMPONENTE_PATCH_OPERATORE

        casi = {
            "ordine create": (views_ordini._ORDINE_CREATE_REQUEST, ordini_service.CREATE_KEYS_ORDINE, set()),
            "ordine update": (views_ordini._ORDINE_UPDATE_REQUEST, ordini_service.UPDATE_KEYS_ORDINE, set()),
            "ordine riga create": (
                views_ordini._ORDINE_RIGA_CREATE_REQUEST, ordini_service.CREATE_KEYS_RIGA,
                {"componenti_overrides"},
            ),
            "ordine riga update": (views_ordini._ORDINE_RIGA_UPDATE_REQUEST, ordini_service.UPDATE_KEYS_RIGA, set()),
            "ddt create": (views_ddt._DDT_CREATE_REQUEST, ddt_service.CREATE_KEYS_DDT, set()),
            "ddt update": (views_ddt._DDT_UPDATE_REQUEST, ddt_service.UPDATE_KEYS_DDT, set()),
            "ddt riga create": (
                views_ddt._DDT_RIGA_CREATE_REQUEST, ddt_service.CREATE_KEYS_RIGA,
                {"componenti_overrides"},
            ),
            "ddt riga update": (views_ddt._DDT_RIGA_UPDATE_REQUEST, ddt_service.UPDATE_KEYS_RIGA, set()),
            "reso create": (views_resi._RESO_CREATE_REQUEST, resi_service.CREATE_KEYS_RESO, set()),
            "reso update": (views_resi._RESO_UPDATE_REQUEST, resi_service.UPDATE_KEYS_RESO, set()),
            "reso riga create": (views_resi._RESO_RIGA_CREATE_REQUEST, resi_service.CREATE_KEYS_RIGA, set()),
            "reso riga update": (views_resi._RESO_RIGA_UPDATE_REQUEST, resi_service.UPDATE_KEYS_RIGA, set()),
            "componente patch": (_componenti_schema.COMPONENTE_PATCH_REQUEST, COMPONENTE_PATCH_OPERATORE, set()),
            # ⭐ 2026-09-26: gli schemi scritti a mano di questi tre documenti
            #    divergevano TUTTI dal contratto (`iva_id` e `quantita` in piu',
            #    `codice_cig`, `richiesta_approvazione`, ... in meno).
            "preventivo create": (
                preventivi_views._PREVENTIVO_CREATE_REQUEST, preventivi_service.CREATE_KEYS_PREVENTIVO, set(),
            ),
            "preventivo update": (
                preventivi_views._PREVENTIVO_UPDATE_REQUEST, preventivi_service.UPDATE_KEYS_PREVENTIVO, set(),
            ),
            "preventivo riga create": (
                preventivi_views._PREVENTIVO_RIGA_CREATE_REQUEST, preventivi_service.CREATE_KEYS_RIGA, set(),
            ),
            "preventivo riga update": (
                preventivi_views._PREVENTIVO_RIGA_UPDATE_REQUEST, preventivi_service.UPDATE_KEYS_RIGA,
                set(preventivi_service.UPDATE_RIGA_LETTE_A_PARTE),
            ),
            "contratto create": (views_contratti._CONTRATTO_CREATE_REQUEST, contratti_service.CREATE_KEYS_TESTATA, set()),
            "contratto update": (views_contratti._CONTRATTO_PATCH_REQUEST, contratti_service.UPDATE_KEYS_CONTRATTO, set()),
            "contratto riga create": (views_contratti._RIGA_CREATE_REQUEST, contratti_service.CREATE_KEYS_RIGA, set()),
            "contratto riga update": (views_contratti._RIGA_PATCH_REQUEST, contratti_service.UPDATE_KEYS_RIGA, set()),
            "contratto utility create": (
                views_contratti._UTILITY_CREATE_REQUEST, contratti_service.UTILITY_CREATE_KEYS, set(),
            ),
            "contratto utility update": (
                views_contratti._UTILITY_UPDATE_REQUEST, contratti_service.UTILITY_UPDATE_KEYS, set(),
            ),
            "offerta create": (views_offerte._OFFERTA_CREATE_REQUEST, offerte_service.CREATE_KEYS_OFFERTA, set()),
            "offerta update": (views_offerte._OFFERTA_PATCH_REQUEST, offerte_service.UPDATE_KEYS_OFFERTA, set()),
            "eccezione create": (views_offerte._ECCEZIONE_CREATE_REQUEST, offerte_service.CREATE_KEYS_ECCEZIONE, set()),
            "eccezione update": (views_offerte._ECCEZIONE_PATCH_REQUEST, offerte_service.UPDATE_KEYS_ECCEZIONE, set()),
            "offerta utility create": (views_offerte._UTILITY_CREATE_REQUEST, offerte_service.CREATE_KEYS_UTILITY, set()),
            "offerta utility update": (views_offerte._UTILITY_PATCH_REQUEST, offerte_service.UPDATE_KEYS_UTILITY, set()),
        }
        for nome, (schema, contratto, speciali) in casi.items():
            with self.subTest(nome):
                self.assertEqual(set(schema.fields), set(contratto) | speciali)

    # Scopo: il difetto da cui il contratto di preventivi e' nato (2026-09-26):
    #        lo schema a mano pubblicava `iva_id` (chiuso da `I6`) e `quantita`
    #        (la calcola il trigger), che il service ignorava in silenzio.
    def test_la_riga_di_preventivo_non_pubblica_i_campi_ritirati(self):
        from apps.vendite.api import preventivi_views

        for schema in (
            preventivi_views._PREVENTIVO_RIGA_CREATE_REQUEST,
            preventivi_views._PREVENTIVO_RIGA_UPDATE_REQUEST,
        ):
            with self.subTest(type(schema).__name__):
                self.assertNotIn("iva_id", schema.fields)
                self.assertNotIn("quantita", schema.fields)
