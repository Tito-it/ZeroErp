# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La giuntura fra i template d'invito del DB (`config.email_template`) e
#        le variabili che il backend passa (brief-db-blocco-login-per-credenziale
#        §15, B-15/B-16).
#
# ⛔ PERCHE' SUL DB VERO. Il motore dei template sostituisce `{{chiave}}` e
#    lascia LETTERALE un segnaposto senza valore: se il DB aggiunge una
#    variabile al testo e il backend non la passa, l'email parte con
#    «{{username}}» dentro, senza nessun errore. I test col mock vedono solo il
#    lato Python, il pgTAP solo il lato DB; la giuntura si vede solo qui.
#
# ⚠️ Le variabili COMUNI si leggono dal BB vero (`InvitoVeste.spedisci` con
#    l'email finta), non si ricopiano. Quelle della veste le passa il servizio
#    della veste: stanno in `_VARIABILI_DELLA_VESTE`, e i test unitari dei
#    servizi provano che le passino davvero (test_invito_operatore,
#    test_invito_portale_service).
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_ogni_porta_ha_i_suoi_due_template
2. test_ogni_segnaposto_riceve_un_valore_dal_backend
"""

from __future__ import annotations

import re
from unittest import TestCase
from unittest.mock import MagicMock

from django.db import connection
from django.test import override_settings

from apps.core.services.invito_veste import (
    PORTA_OPERATORE,
    PORTA_PORTALE,
    PORTA_SHOP,
    EmissioneInvito,
    InvitoVeste,
    PortaInvito,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto

_PORTE: tuple[PortaInvito, ...] = (PORTA_OPERATORE, PORTA_PORTALE, PORTA_SHOP)

# Le variabili che il servizio di ciascuna veste passa a `spedisci`.
_VARIABILI_DELLA_VESTE: dict[str, frozenset[str]] = {
    PORTA_OPERATORE.nome: frozenset({"nome", "cognome", "username"}),
    PORTA_PORTALE.nome: frozenset({"nome", "entita", "ruolo_applicativo"}),
    PORTA_SHOP.nome: frozenset({"nome", "entita", "ruolo_applicativo"}),
}

_SEGNAPOSTO = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


# Scopo: Le variabili che il BB aggiunge da se', lette da una spedizione vera
# con l'email e il repository finti.
def _variabili_comuni(porta: PortaInvito) -> frozenset[str]:
    email, repo = MagicMock(), MagicMock()
    email.send_email.return_value = (1, True)
    repo.get_nomi_credenziale.return_value = {"first_name": "A", "last_name": "B", "username": "c"}
    invito = InvitoVeste(auth_repo=repo, token_service=MagicMock(), email_service=email)
    with override_settings(FRONTEND_URL="https://erp.example"):
        invito.spedisci(
            porta, EmissioneInvito(token="t", is_cross=False),
            auth_user_id=1, identita_id=1, destinatario="x@example.invalid",
            invitato_da_user_id=1, variabili={},
        )
    return frozenset(email.send_email.call_args.kwargs["variabili"])


# Scopo: Le righe attive di un template (base e override), coi tre testi.
def _righe(codice: str) -> list[tuple[str, str, str | None]]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT oggetto, corpo_html, corpo_testo FROM config.email_template "
            "WHERE codice = %s AND attivo",
            [codice],
        )
        return list(cur.fetchall())


class TemplateInvitoDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 1. Ogni porta nomina due template (flusso nuovo e con un clic), e il DB
    #    li ha tutti e due: un codice che non c'e' e' un invito che non parte.
    def test_ogni_porta_ha_i_suoi_due_template(self) -> None:
        for porta in _PORTE:
            for codice in (porta.template, porta.template_cross):
                with self.subTest(porta=porta.nome, codice=codice):
                    self.assertTrue(_righe(codice), f"template {codice} assente o spento")

    # 2. ⭐ La giuntura: ogni `{{segnaposto}}` dei testi riceve un valore,
    #    comune (dal BB) o della veste. Altrimenti resta letterale nell'email.
    def test_ogni_segnaposto_riceve_un_valore_dal_backend(self) -> None:
        for porta in _PORTE:
            passate = _variabili_comuni(porta) | _VARIABILI_DELLA_VESTE[porta.nome]
            for codice in (porta.template, porta.template_cross):
                for testi in _righe(codice):
                    usate = {m for t in testi if t for m in _SEGNAPOSTO.findall(t)}
                    with self.subTest(porta=porta.nome, codice=codice):
                        self.assertEqual(usate - passate, set())
