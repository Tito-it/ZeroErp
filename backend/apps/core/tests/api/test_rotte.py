# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il building block `apps.core.api.rotte`: le rotte dal percorso reale,
#        comprese su richiesta quelle montate a condizione, e mai due volte.
# Note: Nessun DB: l'URLconf e' gia' importato dai system check del runner.
# ------------------------------------------------------------

"""
Indice test (0..N):
 0. test_ogni_rotta_condizionale_dichiarata_ha_un_urlconf_che_si_carica
 1. test_con_le_condizionali_si_vedono_le_view_dell_assistente
 2. test_nessuna_rotta_contata_due_volte
 3. test_la_rotta_porta_la_classe_della_view
"""

import importlib

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import get_resolver

from apps.ai_assistant.api.views import AIQueryView, AIStatusView
from apps.core.api.rotte import classi_view, rotte_servite


class RotteServiteTests(SimpleTestCase):

    def test_ogni_rotta_condizionale_dichiarata_ha_un_urlconf_che_si_carica(self) -> None:
        radice = importlib.import_module(settings.ROOT_URLCONF)
        condizionali = getattr(radice, "ROTTE_CONDIZIONALI", ())
        self.assertTrue(condizionali)
        for prefisso, urlconf, flag in condizionali:
            with self.subTest(urlconf=urlconf):
                self.assertTrue(prefisso.endswith("/"))
                self.assertTrue(hasattr(settings, flag), f"flag {flag} non in settings")
                self.assertTrue(get_resolver(urlconf).url_patterns)

    # Vale con la flag accesa (montate dall'URLconf) E spenta (lette a parte):
    # e' il punto del parametro.
    def test_con_le_condizionali_si_vedono_le_view_dell_assistente(self) -> None:
        classi = classi_view(anche_condizionali=True)
        self.assertIn(AIQueryView, classi)
        self.assertIn(AIStatusView, classi)

    # Con la flag accesa le rotte sono gia' nell'URLconf: non si aggiungono.
    def test_nessuna_rotta_contata_due_volte(self) -> None:
        percorsi = [r.percorso for r in rotte_servite(anche_condizionali=True)]
        doppi = sorted({p for p in percorsi if percorsi.count(p) > 1})
        self.assertEqual(doppi, [])

    def test_la_rotta_porta_la_classe_della_view(self) -> None:
        rotte = {r.percorso: r.view for r in rotte_servite(anche_condizionali=True)}
        self.assertIs(rotte.get("api/v1/ai-assistant/query/"), AIQueryView)
