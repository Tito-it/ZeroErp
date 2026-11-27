# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Account e template di posta sul DATABASE VERO dopo il seed di primo
#        impianto (brief-db-seed-primo-impianto-non-si-riscrive §16.14, R-test):
#        il repository espone il segno «nata dal seed» e i campi del software,
#        account e template non si cancellano, e un account che ha spedito si
#        spegne.
# Note: ⭐ Prova la GIUNTURA con le due viste `config.vw_email_*_seed`, che i
#       mock non vedono: il `LEFT JOIN` per id, il `text[]` che arriva come
#       lista, la riga creata dall'installazione che NON porta il segno.
#       ⚠️ Le righe di seed non si nominano per id né per codice: si prendono
#       dalla vista (`nata_dal_seed`), così il test non dipende dal CSV.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE: azienda e operatore da `fn_pgtap_crea_emittente_operatore`.
#       Tutto in transazione ANNULLATA; ogni rifiuto atteso in un savepoint.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EmailSeedPrimoImpiantoDbTests.test_il_template_di_seed_porta_segno_e_campi
   lista e dettaglio: la riga di seed ha `nata_dal_seed` e i campi del
   software; quella creata dal test no, e la lista e' vuota (mai NULL).
2) EmailSeedPrimoImpiantoDbTests.test_l_account_di_seed_porta_il_segno
   stesso contratto sugli account: `campi_del_software` vuoto anche sul seed.
3) EmailSeedPrimoImpiantoDbTests.test_un_campo_del_software_non_si_modifica
   `update_template` del codice su una riga di seed: E_SEED_COLONNA_DEL_SOFTWARE;
   l'oggetto invece si modifica.
4) EmailSeedPrimoImpiantoDbTests.test_account_e_template_non_si_cancellano
   la riga di seed: E_SEED_RIGA_NON_CANCELLABILE; quella dell'installazione:
   E_DELETE_NOT_ALLOWED. E' la ragione per cui il backend non ha DELETE.
5) EmailSeedPrimoImpiantoDbTests.test_un_account_che_ha_spedito_si_spegne
   con una riga di log che lo nomina, `attivo = false` passa (Q24).
"""
from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.core.services.db_error_fields import db_error_code
from apps.core.tests.db_e2e import Annulla, ContestoSu, esegui_fixture, richiedi_db_provvisto

_FIXTURE_OPERATORE: tuple[str | ContestoSu, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    ContestoSu("_mondo"),
)


class EmailSeedPrimoImpiantoDbTests(unittest.TestCase):
    def setUp(self):
        # La sonda e' la sede della regola: senza, il database e' precedente al
        # giro 2 del brief e questi test non hanno materia.
        richiedi_db_provvisto("dbops.fn_seed_riga(regclass,text)")

    # Scopo: il mondo dell'operatore, nella transazione del test.
    def _costruisci(self, cur) -> None:
        esegui_fixture(cur, _FIXTURE_OPERATORE)

    # Scopo: l'id di una riga nata dal seed, letto dalla vista; il test salta
    #        se l'installazione non ne ha.
    def _una_riga_di_seed(self, cur, vista: str, colonna_id: str) -> int:
        cur.execute(
            f"SELECT {colonna_id} FROM {vista} WHERE nata_dal_seed ORDER BY 1 LIMIT 1"
        )
        row = cur.fetchone()
        if row is None:
            self.skipTest(f"nessuna riga nata dal seed in {vista}")
        return row[0]

    def _nuovo_account(self, repo) -> int:
        return repo.create_account(
            codice="SEEDPIACC", descrizione="Account del test seed",
            smtp_host="smtp.invalid", smtp_port=587,
            smtp_use_tls=True, smtp_use_ssl=False,
            smtp_username="utente", smtp_password="segreta",
            email_from="seedpi@esempio.test",
        )

    # 1. Il template di seed porta il segno e i campi; quello del test no.
    def test_il_template_di_seed_porta_segno_e_campi(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                self._costruisci(cur)
                repo = EmailRepository()
                seed_id = self._una_riga_di_seed(cur, "config.vw_email_template_seed", "email_template_id")
                mio_id = repo.create_template(
                    codice="SEEDPITPL", oggetto="Oggetto", corpo_html="<p>x</p>",
                )

                seed = repo.get_template(seed_id)
                self.assertIs(seed["nata_dal_seed"], True)
                # ⚠️ Non si confronta con un elenco scritto qui: e' proprio
                #    l'elenco che il backend non deve tenere. Si prova che c'e'
                #    il campo che il guard ferma di sicuro (la chiave di ricerca).
                self.assertIsInstance(seed["campi_del_software"], list)
                self.assertIn("codice", seed["campi_del_software"])

                mio = repo.get_template(mio_id)
                self.assertIs(mio["nata_dal_seed"], False)
                self.assertEqual(mio["campi_del_software"], [])

                # ⚠️ Le due righe si cercano per codice, non scorrendo la
                #    prima pagina: quante righe ha l'installazione non deve
                #    decidere se il test le trova.
                per_id = {
                    r["id"]: r
                    for codice in (seed["codice"], mio["codice"])
                    for r in repo.list_templates(codice=codice, attivo_only=False)[0]
                }
                self.assertEqual(per_id[seed_id]["campi_del_software"], seed["campi_del_software"])
                self.assertIs(per_id[mio_id]["nata_dal_seed"], False)
                self.assertEqual(per_id[mio_id]["campi_del_software"], [])
                raise Annulla
        except Annulla:
            pass

    # 2. Sugli account lo stesso contratto; i campi del software sono vuoti.
    def test_l_account_di_seed_porta_il_segno(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                self._costruisci(cur)
                repo = EmailRepository()
                seed_id = self._una_riga_di_seed(cur, "config.vw_email_account_seed", "email_account_id")
                mio_id = self._nuovo_account(repo)

                seed = repo.get_account(seed_id)
                self.assertIs(seed["nata_dal_seed"], True)
                self.assertIsInstance(seed["campi_del_software"], list)
                mio = repo.get_account(mio_id)
                self.assertIs(mio["nata_dal_seed"], False)
                self.assertEqual(mio["campi_del_software"], [])

                # ⚠️ Per codice, come sui template: non la prima pagina.
                per_id = {
                    r["id"]: r
                    for codice in (seed["codice"], mio["codice"])
                    for r in repo.list_accounts(search=codice, attivo_only=False)[0]
                }
                self.assertIs(per_id[seed_id]["nata_dal_seed"], True)
                self.assertIs(per_id[mio_id]["nata_dal_seed"], False)
                raise Annulla
        except Annulla:
            pass

    # 3. Il codice di un template di seed non si cambia; l'oggetto si'.
    def test_un_campo_del_software_non_si_modifica(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                self._costruisci(cur)
                repo = EmailRepository()
                seed_id = self._una_riga_di_seed(cur, "config.vw_email_template_seed", "email_template_id")

                with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                    repo.update_template(seed_id, codice="SEEDPIALTRO")
                self.assertEqual(db_error_code(ctx.exception), "E_SEED_COLONNA_DEL_SOFTWARE")

                self.assertTrue(repo.update_template(seed_id, oggetto="Oggetto dell'azienda"))
                self.assertEqual(repo.get_template(seed_id)["oggetto"], "Oggetto dell'azienda")
                raise Annulla
        except Annulla:
            pass

    # 4. Nessuna riga si cancella: col codice del seed o con quello del blocco.
    def test_account_e_template_non_si_cancellano(self):
        from apps.core.db.email_repository import EmailRepository

        casi = (
            ("config.email_template", "config.vw_email_template_seed", "email_template_id"),
            ("config.email_account", "config.vw_email_account_seed", "email_account_id"),
        )
        try:
            with transaction.atomic(), connection.cursor() as cur:
                self._costruisci(cur)
                repo = EmailRepository()
                miei = {
                    "config.email_template": repo.create_template(
                        codice="SEEDPITPL", oggetto="Oggetto", corpo_html="<p>x</p>",
                    ),
                    "config.email_account": self._nuovo_account(repo),
                }
                for tabella, vista, colonna_id in casi:
                    seed_id = self._una_riga_di_seed(cur, vista, colonna_id)
                    for riga_id, atteso in (
                        (seed_id, "E_SEED_RIGA_NON_CANCELLABILE"),
                        (miei[tabella], "E_DELETE_NOT_ALLOWED"),
                    ):
                        with self.subTest(tabella=tabella, atteso=atteso):
                            with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                                cur.execute(f"DELETE FROM {tabella} WHERE id = %s", [riga_id])
                            self.assertEqual(db_error_code(ctx.exception), atteso)
                raise Annulla
        except Annulla:
            pass

    # 5. Un account che ha spedito si spegne (Q24: prima lo storico lo teneva acceso).
    def test_un_account_che_ha_spedito_si_spegne(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                self._costruisci(cur)
                cur.execute("SELECT emittente_fiscale_id, auth_user_id FROM _mondo")
                emittente, operatore = cur.fetchone()
                repo = EmailRepository()
                account_id = self._nuovo_account(repo)
                repo.insert_log(
                    email_account_id=account_id, email_template_id=None,
                    destinatario="cliente@esempio.test", oggetto="Spedita",
                    stato="SENT", ambito="OPERATORE",
                    emittente_fiscale_id=emittente, creato_da_user_id=operatore,
                )

                self.assertTrue(repo.update_account(account_id, attivo=False))
                self.assertIs(repo.get_account(account_id)["attivo"], False)
                raise Annulla
        except Annulla:
            pass
