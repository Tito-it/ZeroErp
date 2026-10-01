# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le INSERT di clienti, billing account e fornitori migrate sul BB
#        `execute_dynamic_insert` (2026-09-26), sul DATABASE VERO: le
#        `espressioni` letterali (stato iniziale per codice, `CURRENT_DATE`)
#        finiscono davvero nel testo SQL e i None omessi lasciano lavorare i
#        DEFAULT del DB — cio' che i test di servizio, che mockano il
#        repository, non vedono.
# Note: ⚠️ Il mondo si COSTRUISCE (`dbops.fn_pgtap_crea_mondo_cliente`,
#       `fn_pgtap_crea_soggetto_pg`), in transazione ANNULLATA. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
#       ⛔ Il rifiuto delle chiavi fuori whitelist e' senza DB (classe 1).
# ------------------------------------------------------------
"""
Indice test eseguiti:
Rifiuto (senza DB):
1) RifiutoChiaviClientiFornitoriTests.test_chiave_estranea_e_runtime_error
Opt-in `ZEROERP_TEST_DB_E2E=1`:
2) ScritturaClientiFornitoriDbTests.test_billing_account_e_cliente
   BA: `fatturazione_ordini` None -> DEFAULT CONFERMATO, parent NULL.
   Cliente: stato AT e data di attivazione di oggi dalle espressioni.
3) ScritturaClientiFornitoriDbTests.test_fornitore_nasce_ve
   stato VE dall'espressione, opzionali None omessi, `note` scritta.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.anagrafiche.db.clienti_repository import ClientiRepository
from apps.anagrafiche.db.fornitori_repository import FornitoriRepository
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto


class _Annulla(Exception):
    """Esce dal blocco atomico annullandolo."""


class RifiutoChiaviClientiFornitoriTests(unittest.TestCase):
    """⛔ Una chiave fuori whitelist e' `RuntimeError`, mai uno scarto."""

    # 1. Il BB verifica le colonne PRIMA di aprire il cursore: niente DB.
    #    `stato_*_id` e' la chiave che collide con l'espressione dello stato
    #    iniziale: fino al 2026-09-26 veniva ignorata in silenzio.
    def test_chiave_estranea_e_runtime_error(self):
        cli, forn = ClientiRepository(), FornitoriRepository()
        casi = (
            ("create_cliente ignota", lambda: cli.create_cliente(
                istanza_utility_id=1, billing_account_id=1, soggetto_ruolo_id=1, iva_id=5)),
            ("create_cliente stato", lambda: cli.create_cliente(
                istanza_utility_id=1, billing_account_id=1, soggetto_ruolo_id=1,
                stato_cliente_id=3)),
            ("create_fornitore ignota", lambda: forn.create_fornitore(
                soggetto_ruolo_id=1, campo_ignoto="x")),
            ("create_fornitore stato", lambda: forn.create_fornitore(
                soggetto_ruolo_id=1, stato_fornitore_id=3)),
            ("update_cliente_atomico", lambda: cli.update_cliente_atomico(
                1, ba_categoria_cliente_id=None, cliente_fields={"stato_cliente_id": 3})),
        )
        for nome, chiama in casi:
            with self.subTest(nome), self.assertRaises(RuntimeError):
                chiama()


class ScritturaClientiFornitoriDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    # 2. Istanza -> BA -> cliente dal repository, come fa `crea_cliente`.
    def test_billing_account_e_cliente(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    "CREATE TEMP TABLE _mondo AS "
                    "SELECT m.* FROM dbops.fn_pgtap_crea_mondo_cliente('SCRCLI') m"
                )
                cur.execute(
                    "SELECT m.cliente_soggetto_id, m.cliente_soggetto_ruolo_id, m.utility_id,"
                    "       ba.categoria_cliente_id"
                    "  FROM _mondo m"
                    "  JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id"
                )
                soggetto_id, sr_id, _, categoria_id = cur.fetchone()
                # ⚠️ L'utility del cliente MANUALE: `richiede_pdp = false`, come
                #    pretende `crea_cliente` (e il trigger
                #    `trgfn_clienti_sync_utility_from_ba`, E_PDP_OBBLIGATORIO).
                cur.execute(
                    "SELECT id FROM config.utilities WHERE NOT richiede_pdp ORDER BY id LIMIT 1"
                )
                riga = cur.fetchone()
                if riga is None:
                    self.skipTest("nessuna utility senza PDP a catalogo")
                utility_id = riga[0]
                # La finestra differita: l'istanza vuole il suo satellite (il
                # BA) al COMMIT, e il BA si scrive un'istruzione dopo.
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                repo = ClientiRepository()
                istanza_id = repo.create_istanza_fittizia(soggetto_id=str(soggetto_id))
                ba_id = repo.create_billing_account(
                    istanza_utility_id=istanza_id, soggetto_ruolo_id=sr_id,
                    utility_id=utility_id, categoria_cliente_id=categoria_id,
                )
                cur.execute(
                    "SELECT fatturazione_ordini, parent_account_id, categoria_cliente_id"
                    "  FROM anagrafiche.billing_account WHERE id = %s",
                    [ba_id],
                )
                self.assertEqual(cur.fetchone(), ("CONFERMATO", None, categoria_id))

                cliente_id = repo.create_cliente(
                    istanza_utility_id=istanza_id, billing_account_id=ba_id,
                    soggetto_ruolo_id=sr_id, garanzia_tipo=None, garanzia_importo=None,
                    servizio_da_fatturare=False,
                )
                cur.execute(
                    """
                    SELECT sc.codice_interno, cl.data_attivazione, cl.garanzia_tipo,
                           cl.servizio_da_fatturare
                      FROM anagrafiche.clienti cl
                      JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
                     WHERE cl.id = %s
                    """,
                    [cliente_id],
                )
                stato, attivazione, garanzia_tipo, da_fatturare = cur.fetchone()
                self.assertEqual(stato, "AT")
                cur.execute("SELECT CURRENT_DATE")
                self.assertEqual(attivazione, cur.fetchone()[0])
                # None omesso -> DEFAULT 'D' della colonna, come prima.
                self.assertEqual(garanzia_tipo, "D")
                self.assertFalse(da_fatturare)
                raise _Annulla
        except _Annulla:
            pass

    # 3. Fornitore: nasce VE, gli opzionali None non si scrivono.
    def test_fornitore_nasce_ve(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore scrfor')")
                soggetto_id = str(cur.fetchone()[0])
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                repo = FornitoriRepository()
                sr_id = repo.get_or_create_ruolo_fornitore(soggetto_id)
                fornitore_id = repo.create_fornitore(
                    soggetto_ruolo_id=sr_id, note="Nota scrfor", rating=None,
                )
                cur.execute(
                    """
                    SELECT sf.codice_interno, f.note, f.rating, f.codice
                      FROM anagrafiche.fornitori f
                      JOIN config.stati_fornitore sf ON sf.id = f.stato_fornitore_id
                     WHERE f.id = %s
                    """,
                    [fornitore_id],
                )
                stato, note, rating, codice = cur.fetchone()
                self.assertEqual(stato, "VE")
                self.assertEqual(note, "Nota scrfor")
                self.assertIsNone(rating)
                self.assertTrue(codice)  # dal sistema_codici: la chiave e' stata omessa
                raise _Annulla
        except _Annulla:
            pass
