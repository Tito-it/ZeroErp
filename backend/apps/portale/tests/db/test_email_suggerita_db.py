# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'email suggerita dell'invito al portale sul DATABASE VERO:
#        `PortaleRepository.get_email_contatto_suggerita` sopra il BB
#        `script.fn_get_contatti` (contatto del ruolo prima di quello del
#        soggetto) e la scelta tra i tipi (PRINCIPALE, poi `is_default`).
#        I test di servizio mockano il repository e non vedono la SQL.
# Note: ⚠️ Il mondo si COSTRUISCE (`dbops.fn_pgtap_crea_soggetto_pg`, che
#       porta un contatto PRINCIPALE di default del soggetto, email
#       `pgtap@example.com`), in transazione ANNULLATA. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EmailSuggeritaDbTests.test_principale_poi_default_ruolo_prima_del_soggetto
   a) senza contatti del ruolo: il PRINCIPALE del soggetto;
   b) un REFERENTE di default del ruolo non lo scavalca: vince PRINCIPALE;
   c) un PRINCIPALE del ruolo senza email prende il posto di quello del
      soggetto (regola del BB) e si scarta: resta il contatto di default;
   d) il PRINCIPALE del ruolo con email vince su tutto.
"""
from __future__ import annotations

import json
import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class EmailSuggeritaDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_soggetto_pg(text,integer,integer,text)")

    def test_principale_poi_default_ruolo_prima_del_soggetto(self):
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        from apps.portale.db.portale_repository import PortaleRepository

        repo = PortaleRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore email suggerita')")
                soggetto_id = str(cur.fetchone()[0])
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                sr_id = FornitoriService().crea_fornitore({"soggetto_id": soggetto_id})["soggetto_ruolo_id"]

                def crea_contatto(tipo: str, **campi) -> int:
                    cur.execute("SELECT id FROM config.tipi_contatti WHERE codice = %s", [tipo])
                    campi = {"tipo_contatto_id": cur.fetchone()[0], "nominativo": f"Prova {tipo}", **campi}
                    cur.execute(
                        "SELECT (anagrafiche.fn_crea_contatto(%s::uuid, %s, %s::jsonb) ->> 'id')::bigint",
                        [soggetto_id, sr_id, json.dumps(campi)],
                    )
                    return cur.fetchone()[0]

                # a) Solo il contatto del soggetto (dal builder).
                self.assertEqual(repo.get_email_contatto_suggerita(soggetto_id, sr_id), "pgtap@example.com")

                # b) Un REFERENTE di default del ruolo: PRINCIPALE vince comunque.
                crea_contatto("REFERENTE", email="referente@prova.test", is_default=True)
                self.assertEqual(repo.get_email_contatto_suggerita(soggetto_id, sr_id), "pgtap@example.com")

                # c) Un PRINCIPALE del ruolo senza email: e' il PRINCIPALE che il BB
                #    sceglie, non ha email, e si ripiega sul contatto di default.
                principale_ruolo = crea_contatto("PRINCIPALE", telefono="0123456789")
                self.assertEqual(repo.get_email_contatto_suggerita(soggetto_id, sr_id), "referente@prova.test")

                # d) Il PRINCIPALE del ruolo con email vince.
                cur.execute(
                    "UPDATE anagrafiche.contatti SET email = 'ruolo@prova.test' WHERE id = %s",
                    [principale_ruolo],
                )
                self.assertEqual(repo.get_email_contatto_suggerita(soggetto_id, sr_id), "ruolo@prova.test")
                raise Annulla
        except Annulla:
            pass
