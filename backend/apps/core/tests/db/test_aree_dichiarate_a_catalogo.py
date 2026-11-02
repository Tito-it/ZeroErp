# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Ogni `area_funzionale` dichiarata da una view esiste nel catalogo
#        `config.aree_funzionali`, attiva (brief-db-area-funzionale-
#        assistente-ai §5.4 presidio 1; migliorie-generali-BE-FE D5).
#
# ⛔ PERCHE' ESISTE. Un'area fuori catalogo non da' errore: per
#    `script.fn_resolve_livello_area` e' `BLOCCATO` per tutti tranne il
#    SUPER_ADMIN, e nessun amministratore puo' concedere il permesso, perche'
#    non esiste la riga a cui appenderlo. Il 403 si legge come «non hai il
#    permesso». E' successo con `ai_assistant`, dal 2026-04 al 2026-09-25.
#
# ⭐ LA CHIAVE E' `schema_db`, NON `codice`: il resolver confronta l'area con
#    `af.schema_db` (brief §1.1). Confrontare col `codice` darebbe un verde
#    per la colonna sbagliata.
# ⭐ LE VIEW SI LEGGONO DAL PERCORSO REALE, comprese le rotte montate a
#    condizione (`apps.core.api.rotte`, `anche_condizionali=True`): in CI l'AI
#    e' spenta, e senza quelle il presidio non vedrebbe `AIQueryView` —
#    proprio il caso da cui nasce. Il test 0 lo pretende.
#    L'area e' letta con `ZeroERPPermission._resolve_area`, cioe' come la legge
#    la catena, solo sulle view che la catena valuta.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    Solo letture.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

0. test_la_scansione_vede_anche_le_rotte_condizionali
1. test_ogni_area_dichiarata_e_a_catalogo_e_attiva
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.ai_assistant.api.views import AIQueryView
from apps.core.api.permissions import ZeroERPPermission
from apps.core.api.rotte import classi_view
from apps.core.tests.db_e2e import richiedi_db_provvisto


# Scopo: area dichiarata -> view che la dichiarano, per le view valutate da
#        `ZeroERPPermission` (le altre permission class l'area non la leggono).
def _aree_dichiarate() -> dict[str, list[str]]:
    aree: dict[str, list[str]] = {}
    for cls in classi_view(anche_condizionali=True):
        if ZeroERPPermission not in getattr(cls, "permission_classes", ()):
            continue
        area = ZeroERPPermission._resolve_area(cls, cache={})
        if area is None:
            continue
        aree.setdefault(area, []).append(f"{cls.__module__}.{cls.__qualname__}")
    return aree


class AreeDichiarateACatalogoTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 0) Un presidio che non vede le view dell'assistente non presidia il
    #    caso per cui esiste: e' verde per sottrazione.
    def test_la_scansione_vede_anche_le_rotte_condizionali(self) -> None:
        self.assertIn(AIQueryView, classi_view(anche_condizionali=True))
        self.assertIn(AIQueryView.area_funzionale, _aree_dichiarate())

    def test_ogni_area_dichiarata_e_a_catalogo_e_attiva(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT schema_db FROM config.aree_funzionali WHERE attivo"
            )
            a_catalogo = {riga[0] for riga in cur.fetchall()}
        # Un catalogo letto vuoto (RLS, schema sbagliato) farebbe fallire
        # tutto per il motivo sbagliato: lo si dice prima.
        self.assertTrue(a_catalogo, "config.aree_funzionali letta vuota")

        dichiarate = _aree_dichiarate()
        self.assertTrue(dichiarate, "nessuna area dichiarata: la scansione non vede le view")

        fuori = {
            area: sorted(view)
            for area, view in dichiarate.items()
            if area not in a_catalogo
        }
        self.assertEqual(
            fuori, {},
            "aree dichiarate dalle view ma assenti (o non attive) in "
            "config.aree_funzionali.schema_db — per il resolver sono BLOCCATO "
            f"per tutti tranne il SUPER_ADMIN: {fuori}",
        )
