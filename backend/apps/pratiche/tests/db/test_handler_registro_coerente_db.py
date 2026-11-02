# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I due registri degli handler di flusso dicono la stessa cosa. Ogni
#        handler ATTIVO nel registro del DB (`pratiche.handler_flussi`) deve
#        essere registrato nel backend (`HANDLER_MAP`), provato sul DATABASE
#        VERO.
# Note: ⭐ Perche' esiste (richiesta del team DB, 2026-10-13). Il backend aveva
#       ritirato `vendita.accetta_preventivo` dalla HANDLER_MAP, mentre a DB
#       l'handler e alcuni collegamenti restavano attivi: completare il flusso
#       APPROVAZIONE_CLIENTE rispondeva 500 E_HANDLER_NON_REGISTRATO. I guard
#       del DB (collegamento -> handler attivo e viceversa) hanno retto: si era
#       rotta la coerenza fra i due registri, che il DB non puo' vedere. L'ha
#       trovata uno smoke HTTP; questo test la vede prima.
#       ⚠️ Il verso e' uno solo: un handler registrato nel backend e assente a
#       DB e' innocuo (nessun collegamento puo' puntarlo), uno attivo a DB e
#       assente dal backend e' un 500 in attesa del primo flusso che lo usa.
#       Ordine per ritirare un handler (documentazione di
#       `pratiche.template_flussi_handler_eventi`): a DB i collegamenti in ogni
#       versione del workflow, poi l'handler, e solo dopo dalla HANDLER_MAP.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) HandlerRegistroCoerenteDbTests.test_ogni_handler_attivo_a_db_e_registrato_nel_backend
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.core.tests.db_e2e import richiedi_db_provvisto


class HandlerRegistroCoerenteDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # 1. Nessun handler attivo a DB manca dalla HANDLER_MAP. La mappa la
    #    popolano gli AppConfig.ready() al boot, gia' avvenuto nel runner.
    def test_ogni_handler_attivo_a_db_e_registrato_nel_backend(self):
        from apps.pratiche.services.handler_registry import HANDLER_MAP

        with connection.cursor() as cur:
            cur.execute(
                "SELECT handler_key, codice FROM pratiche.handler_flussi"
                " WHERE attivo ORDER BY handler_key"
            )
            attivi = cur.fetchall()

        mancanti = [f"{chiave} ({codice})" for chiave, codice in attivi if chiave not in HANDLER_MAP]
        self.assertEqual(
            mancanti, [],
            "Handler attivi in pratiche.handler_flussi ma non registrati nella "
            f"HANDLER_MAP del backend: {mancanti}. O li registra il backend, o "
            "il DB li spegne (prima i collegamenti in ogni versione del workflow).",
        )
