# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le scritture dinamiche di `EmailRepository.update_account` e di
#        `PartitionedNoteRepository` (create/update) sul DATABASE VERO, dopo
#        la migrazione sui BB `execute_dynamic_*` / `sql_set_clause`
#        (2026-09-26).
# Note: ⭐ Prova la GIUNTURA con psycopg, che i mock non vedono:
#       - la password SMTP passa cifrata, e la password in chiaro NON viene
#         strippata (lo strip del BB tocca solo il cifrato);
#       - la nota con `meta` (dict da `optional_meta`): fino al 2026-09-26
#         arrivava nuda al cursor, che non sa adattare un dict — 500.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, la fattura da
#       `fn_pgtap_crea_fattura`. Stili e lingue delle note sono seed
#       (`80_data`). Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ScrittureEmailAccountDbTests.test_update_account_cifra_la_password_e_strippa_i_campi
   `codice` strippato, password ri-cifrata INTATTA (spazi compresi);
   una chiave estranea e' RuntimeError.
2) ScrittureNotePartizionateDbTests.test_nota_con_meta_create_e_update
   Dal service (percorso reale) una nota di fattura con `meta` nasce e si
   aggiorna; `target_*` restano quelli del repository.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

_FIXTURE_OPERATORE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)

_FIXTURE_FATTURA: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _fattura AS
    SELECT f.* FROM dbops.fn_pgtap_crea_fattura('scritture note') f
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _fattura))",
)


class ScrittureEmailAccountDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto()

    # 1. update_account: strip dei campi, password cifrata intatta, whitelist rigida.
    def test_update_account_cifra_la_password_e_strippa_i_campi(self):
        from apps.core.db.email_repository import EmailRepository
        from apps.core.services import crypto_service

        try:
            with transaction.atomic(), connection.cursor() as cur:
                for passo in _FIXTURE_OPERATORE:
                    cur.execute(passo)
                repo = EmailRepository()
                account_id = repo.create_account(
                    codice="SCRDINACC", descrizione="Account scritture",
                    smtp_host="smtp.invalid", smtp_port=587,
                    smtp_use_tls=True, smtp_use_ssl=False,
                    smtp_username="utente", smtp_password="vecchia",
                    email_from="scrdin@esempio.test",
                )
                # ⚠️ `data_update` non si prova qui (2026-11-08): la scrive il
                #    trigger di audit, non il repository, e dentro la stessa
                #    transazione nessun controllo distingue chi l'ha scritta —
                #    portarla indietro con un UPDATE passa dallo stesso trigger,
                #    che la rimette a now(): il controllo di prima era verde a
                #    vuoto. La regola sta nel trigger (pgTAP).

                self.assertTrue(repo.update_account(
                    account_id, codice="  SCRDINACC2  ", smtp_password=" nuova segreta ",
                ))
                cur.execute(
                    "SELECT codice, codice_interno, smtp_password_encrypted "
                    "FROM config.email_account WHERE id = %s",
                    [account_id],
                )
                codice, codice_interno, cifrata = cur.fetchone()
                self.assertEqual(codice, "SCRDINACC2")
                self.assertEqual(codice_interno, "SCRDINACC")
                # ⛔ La password in chiaro non passa dallo strip del BB.
                self.assertEqual(crypto_service.decrypt(cifrata), " nuova segreta ")

                # ⛔ Whitelist rigida: niente scarto silenzioso.
                with self.assertRaises(RuntimeError):
                    repo.update_account(account_id, smtp_password_encrypted="x")
                with self.assertRaises(RuntimeError):
                    repo.update_account(account_id, colonna_estranea=1)
                raise Annulla
        except Annulla:
            pass


class ScrittureNotePartizionateDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_fattura(text,character varying,bigint,boolean,boolean,boolean,numeric,bigint,boolean)")

    # 2. Nota di fattura con `meta`: create e update dal service.
    def test_nota_con_meta_create_e_update(self):
        from apps.core.services.partitioned_note_service import PartitionedNoteService
        from apps.vendite.db.note_repositories import NOTE_REPO_FATTURA

        try:
            with transaction.atomic(), connection.cursor() as cur:
                for passo in _FIXTURE_FATTURA:
                    cur.execute(passo)
                cur.execute("SELECT fattura_id FROM _fattura")
                fattura_id = cur.fetchone()[0]
                cur.execute("SELECT id FROM config.note_stili WHERE attivo ORDER BY id LIMIT 1")
                stile = cur.fetchone()[0]
                cur.execute("SELECT id FROM config.lingue WHERE attivo ORDER BY id LIMIT 1")
                lingua = cur.fetchone()[0]

                svc = PartitionedNoteService(repo=NOTE_REPO_FATTURA)
                nota = svc.crea_nota(target_id=fattura_id, payload={
                    "testo": "  Nota di prova  ",
                    "id_stile": stile,
                    "id_lingua": lingua,
                    "meta": {"k": "v"},
                })
                note_id = nota["id"]
                svc.aggiorna_nota(
                    note_id=note_id, target_id=fattura_id,
                    patch={"testo": "Aggiornata", "meta": {"k": "w"}, "seq": 20},
                )

                cur.execute(
                    "SELECT target_tipo, target_id, testo, seq, meta ->> 'k' "
                    "FROM vendite.note_fatture WHERE id = %s",
                    [note_id],
                )
                self.assertEqual(
                    cur.fetchone(), ("FATTURA", fattura_id, "Aggiornata", 20, "w"),
                )
                raise Annulla
        except Annulla:
            pass
