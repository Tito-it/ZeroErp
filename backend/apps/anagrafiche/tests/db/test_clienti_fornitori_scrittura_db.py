# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La creazione di clienti (con billing account) e fornitori sul
#        DATABASE VERO. Dal 2026-10-18 (2b-2 di
#        brief-db-processi-accensione-per-ambiente) la fanno le madri del DB
#        `anagrafiche.fn_crea_cliente` e `fn_crea_fornitore`, chiamate dai
#        service: lo stato di nascita, la data operativa e i DEFAULT delle
#        chiavi assenti sono regole della madre, e qui si prova che arrivino —
#        cio' che i test di servizio, che mockano il repository, non vedono.
# Note: ⚠️ Il mondo si COSTRUISCE (`dbops.fn_pgtap_crea_mondo_cliente`,
#       `fn_pgtap_crea_soggetto_pg`), in transazione ANNULLATA. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
#       ⛔ Fino al 2026-10-18 il file provava le INSERT del repository
#       (`execute_dynamic_insert`) e il rifiuto delle chiavi fuori whitelist
#       senza DB: quelle INSERT sono ritirate, e la chiave estranea la
#       rifiuta la madre (`E_CAMPO_NON_AMMESSO`, pgTAP delle madri).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ScritturaClientiFornitoriDbTests.test_billing_account_e_cliente
   BA nuovo: `fatturazione_ordini` assente -> DEFAULT CONFERMATO, parent NULL.
   Cliente: stato AT e data di attivazione di oggi dalla madre, garanzia al DEFAULT.
2) ScritturaClientiFornitoriDbTests.test_fornitore_nasce_ve
   stato VE dalla madre, opzionali assenti al DEFAULT, `note` scritta, codice generato.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class ScritturaClientiFornitoriDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    # 1. Un cliente manuale dal service, cioe' dalla madre: istanza fittizia,
    #    BA nuovo e cliente in un'istruzione.
    def test_billing_account_e_cliente(self):
        from apps.anagrafiche.services.clienti_service import ClientiService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                # Il contesto dell'operatore pgTAP (con un emittente): la madre
                # rilegge BA e cliente sotto la RLS, e il legame BA → emittente
                # lo scrive il trigger da chi agisce.
                cur.execute("SELECT script.fn_pgtap_set_contesto_operatore()")
                cur.execute(
                    "CREATE TEMP TABLE _mondo AS "
                    "SELECT m.* FROM dbops.fn_pgtap_crea_mondo_cliente('SCRCLI') m"
                )
                cur.execute(
                    "SELECT ba.categoria_cliente_id"
                    "  FROM _mondo m"
                    "  JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id"
                )
                (categoria_id,) = cur.fetchone()
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
                # Un soggetto NUOVO: «un cliente manuale per soggetto, utility e
                # azienda» (D33) rifiuterebbe un secondo cliente sul mondo.
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente scrcli')")
                soggetto_id = str(cur.fetchone()[0])
                # La finestra differita: istanza e indirizzi del ruolo li
                # pretendono i guard al COMMIT, che qui non arriva.
                cur.execute("SET CONSTRAINTS ALL DEFERRED")

                esito = ClientiService().crea_cliente({
                    "soggetto_id": soggetto_id, "utility_id": utility_id,
                    "ba_categoria_cliente_id": categoria_id, "servizio_da_fatturare": False,
                })
                cur.execute(
                    "SELECT fatturazione_ordini, parent_account_id, categoria_cliente_id,"
                    "       istanza_utility_id"
                    "  FROM anagrafiche.billing_account WHERE id = %s",
                    [esito["billing_account_id"]],
                )
                self.assertEqual(
                    cur.fetchone(),
                    ("CONFERMATO", None, categoria_id, esito["istanza_utility_id"]),
                )
                cur.execute(
                    """
                    SELECT sc.codice_interno, cl.data_attivazione, cl.garanzia_tipo,
                           cl.servizio_da_fatturare, cl.soggetto_ruolo_id
                      FROM anagrafiche.clienti cl
                      JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
                     WHERE cl.id = %s
                    """,
                    [esito["id"]],
                )
                stato, attivazione, garanzia_tipo, da_fatturare, sr_id = cur.fetchone()
                self.assertEqual(stato, "AT")
                self.assertEqual(sr_id, esito["soggetto_ruolo_id"])
                cur.execute("SELECT script.fn_data_operativa()")
                self.assertEqual(attivazione, cur.fetchone()[0])
                # Chiave assente -> DEFAULT 'D' della colonna, come prima.
                self.assertEqual(garanzia_tipo, "D")
                self.assertFalse(da_fatturare)
                raise Annulla
        except Annulla:
            pass

    # 2. Fornitore dal service, cioe' dalla madre: nasce VE, gli opzionali
    #    assenti non si scrivono, il codice lo genera `sistema_codici`.
    def test_fornitore_nasce_ve(self):
        from apps.anagrafiche.services.fornitori_service import FornitoriService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore scrfor')")
                soggetto_id = str(cur.fetchone()[0])
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                esito = FornitoriService().crea_fornitore({
                    "soggetto_id": soggetto_id, "note": "Nota scrfor", "rating": None,
                })
                cur.execute(
                    """
                    SELECT sf.codice_interno, f.note, f.rating, f.codice, f.soggetto_ruolo_id
                      FROM anagrafiche.fornitori f
                      JOIN config.stati_fornitore sf ON sf.id = f.stato_fornitore_id
                     WHERE f.id = %s
                    """,
                    [esito["id"]],
                )
                stato, note, rating, codice, sr_id = cur.fetchone()
                self.assertEqual(stato, "VE")
                self.assertEqual(note, "Nota scrfor")
                self.assertIsNone(rating)
                self.assertTrue(codice)  # dal sistema_codici: la chiave e' stata omessa
                self.assertEqual(sr_id, esito["soggetto_ruolo_id"])
                raise Annulla
        except Annulla:
            pass
