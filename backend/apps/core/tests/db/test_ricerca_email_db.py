# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera delle tre liste email (account, template, log) sul
#        DATABASE VERO: `EmailRepository` cerca col BB
#        `add_ricerca_full_condition`, e le colonne le accende il catalogo
#        (`config.email_account`, `config.email_template`, `config.email_log`).
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero, .codex/AGENTS.md): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, poi il CONTESTO, poi un account,
#       un template e un'email della PROPRIA azienda (la RLS di
#       `config.email_log` vede solo il perimetro dell'operatore). Tutto in
#       transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RicercaEmailDbTests.test_la_ricerca_trova_ogni_colonna_accesa
   Per account, template e log costruiti, ogni colonna che il catalogo accende
   trova la riga (`verifica_ricerca_colonna_per_colonna`); un termine
   inesistente no.
2) RicercaEmailDbTests.test_le_soglie_delle_tre_liste
   Account e template sono configurazione: cercano da un carattere. Il log e'
   un registro: sotto soglia il termine non filtra (brief §6).
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import (
    Annulla,
    richiedi_db_provvisto,
    verifica_ricerca_colonna_per_colonna,
)

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)


# Scopo: costruisce mondo e righe; torna gli id di account, template e log.
def _costruisci(cur) -> tuple[int, int, int]:
    for passo in _FIXTURE:
        cur.execute(passo)
    cur.execute("SELECT emittente_fiscale_id, auth_user_id FROM _mondo")
    emittente, operatore = cur.fetchone()
    cur.execute(
        """
        INSERT INTO config.email_account
               (codice, codice_interno, descrizione, smtp_host, smtp_username,
                smtp_password_encrypted, email_from)
        VALUES ('RICCODACC', 'RICINTACC', 'Account ricdescacc', 'smtp.invalid',
                'utente', 'x', 'ricfromacc@esempio.test')
        RETURNING id
        """
    )
    account = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO config.email_template (codice, oggetto, corpo_html)
        VALUES ('RICCODTPL', 'Oggetto ricoggtpl', '<p>x</p>')
        RETURNING id
        """
    )
    template = cur.fetchone()[0]
    # ⚠️ Una mail `OPERATORE` nomina il suo autore (`creato_da_user_id`,
    #    brief-db-email-visibilita-per-ambito D-5): senza, la ferma il `WITH
    #    CHECK` della policy. L'autore e' l'operatore del contesto, che cosi' la
    #    rilegge dal ramo OPERATORE di `script.fn_scope_email_ambito`.
    cur.execute(
        """
        INSERT INTO config.email_log
               (destinatario, oggetto, stato, ambito, emittente_fiscale_id,
                creato_da_user_id, contesto_json)
        VALUES ('ricdestlog@esempio.test', 'Oggetto ricogglog', 'PENDING', 'OPERATORE',
                %s, %s, '{}'::jsonb)
        RETURNING id
        """,
        [emittente, operatore],
    )
    log = cur.fetchone()[0]
    return account, template, log


class RicercaEmailDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    # 1. Ogni colonna accesa a catalogo trova la sua riga, in tutte e tre.
    def test_la_ricerca_trova_ogni_colonna_accesa(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                account, template, log = _costruisci(cur)
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "config.email_account", account,
                    {"codice": "riccodacc", "descrizione": "ricdescacc", "email_from": "ricfromacc"},
                    lambda t: EmailRepository().list_accounts(search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "config.email_template", template,
                    {"codice": "riccodtpl", "oggetto": "ricoggtpl"},
                    lambda t: EmailRepository().list_templates(search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "config.email_log", log,
                    {"destinatario": "ricdestlog", "oggetto": "ricogglog"},
                    lambda t: EmailRepository().list_logs(search=t, limit=200)[0],
                )
                raise Annulla
        except Annulla:
            pass

    # 2. Le soglie: da un carattere la configurazione, di default il registro.
    def test_le_soglie_delle_tre_liste(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                _costruisci(cur)
                # Un carattere che nessuna riga costruita contiene: filtra (e
                # svuota) solo dove la soglia e' uno.
                self.assertEqual(EmailRepository().list_accounts(search="§", limit=200)[1], 0)
                self.assertEqual(EmailRepository().list_templates(search="§", limit=200)[1], 0)
                # Il log ignora il termine corto: esce almeno la riga costruita.
                self.assertGreater(EmailRepository().list_logs(search="§", limit=200)[1], 0)
                raise Annulla
        except Annulla:
            pass
