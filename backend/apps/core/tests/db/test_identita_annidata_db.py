# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I contesti d'identità della coda lavori, aperti DENTRO un'altra
#        identità, all'uscita rimettono quella di prima: sul DB vero, coi GUC
#        veri (BE10 di brief-db-revisione-dbops §5).
# Note: ⛔ Il difetto non dava errore. Il drenatore gira con l'utente tecnico
#        dell'azienda ed esegue ogni lavoro con l'identità del suo scope; il
#        contesto interno, uscendo, azzerava tutto, e la `mark_done` successiva
#        girava senza identità: sotto la RLS aggiorna zero righe, e il lavoro
#        resta IN_CORSO fino al reaper. I test coi mock vedono la query, non
#        che `current_setting`/`set_config` rimettano davvero i valori.
#        ⭐ L'identità interna è volutamente NON valida: il ramo del ripristino
#        è lo stesso (sta nel `finally`), e così il test non dipende da quali
#        utenti esistono su questa macchina.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_operatore_rimette_l_identita_esterna
     dopo un `operator_identity_context` fallito, i GUC sono quelli del badge.
2. test_senza_identita_azzera_e_rimette
     dentro `senza_identita_context` i GUC sono vuoti, fuori tornano.
3. test_senza_identita_esterna_resta_vuota
     senza un'identità prima, all'uscita non resta niente appiccicato.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.core.api.jwt_audit_authentication import (
    JWT_GUC_RESET_SQL,
    JWT_IDENTITY_GUCS,
)
from apps.core.services.coda_lavori.context import (
    E_IDENTITA_NON_ATTIVA,
    operator_identity_context,
    senza_identita_context,
)
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

# Un badge di fantasia: si provano i GUC, non chi sono.
_BADGE = ("badge@PROVA", "-71", "-701", "OPERATORE", "-7001", "-3")


def _gucs() -> tuple[str, ...]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT " + ", ".join(
                f"COALESCE(current_setting('{g}', true), '')" for g in JWT_IDENTITY_GUCS
            )
        )
        return tuple(cur.fetchone())


def _imposta(valori: tuple[str, ...]) -> None:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT " + ", ".join(
                f"set_config('{g}', %s, false)" for g in JWT_IDENTITY_GUCS
            ),
            list(valori),
        )


class IdentitaAnnidataDbTests(TestCase):
    """I contesti d'identità rimettono quella esterna, sul DB vero."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        self.assertEqual(len(_BADGE), len(JWT_IDENTITY_GUCS))
        # I GUC sono di SESSIONE: l'annullo della transazione li riporta
        # indietro, e il reset finale copre il caso in cui non bastasse.
        apri_transazione_annullata(self)
        self.addCleanup(lambda: connection.cursor().execute(JWT_GUC_RESET_SQL))

    # 1. ⛔ Il caso del drenatore: dentro il badge, l'identità del lavoro; fuori,
    #    di nuovo il badge — anche quando quella del lavoro non è più attiva.
    def test_operatore_rimette_l_identita_esterna(self) -> None:
        _imposta(_BADGE)
        with self.assertRaises(ServiceError) as cm:
            with operator_identity_context(-9, username="nessuno", identita_id=-5):
                pass  # pragma: no cover
        self.assertEqual(cm.exception.code, E_IDENTITA_NON_ATTIVA)
        self.assertEqual(_gucs(), _BADGE)

    # 2. Un lavoro SISTEMA nel giro di un badge: dentro nessuna identità,
    #    fuori il badge.
    def test_senza_identita_azzera_e_rimette(self) -> None:
        _imposta(_BADGE)
        with senza_identita_context():
            self.assertEqual(_gucs(), ("",) * len(JWT_IDENTITY_GUCS))
        self.assertEqual(_gucs(), _BADGE)

    # 3. Senza identità prima (il web, un command): all'uscita il vuoto, cioè
    #    il comportamento di sempre.
    def test_senza_identita_esterna_resta_vuota(self) -> None:
        with connection.cursor() as cur:
            cur.execute(JWT_GUC_RESET_SQL)
        with self.assertRaises(ServiceError):
            with operator_identity_context(-9, username="nessuno", identita_id=-5):
                pass  # pragma: no cover
        self.assertEqual(_gucs(), ("",) * len(JWT_IDENTITY_GUCS))
