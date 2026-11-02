# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il percorso della bozza email sul DATABASE VERO, dal backend: una
#        bozza `OPERATORE` con un allegato si spedisce, si annulla, e dopo
#        l'invio il suo allegato non si toglie piu'.
# Note: ⭐ Prova la GIUNTURA, non la policy (quella la prova il pgTAP
#       `rls/test-rls-email-ambito-reparto-operatore`): che il backend scriva
#       sul log le due colonne che reggono il ramo OPERATORE — l'azienda e
#       l'AUTORE della bozza (brief-db-email-visibilita-per-ambito D-5) — e che
#       gli allegati si tolgano prima dell'annullo (§8.4.3). ⛔ Fino al
#       2026-09-25 l'INSERT del log non scriveva nessuna delle due: ogni mail
#       non di sistema veniva rifiutata, e i test col repository mockato erano
#       verdi.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, poi il contesto. Il canale d'invio
#       e' forzato a console: nessuna mail parte. Tutto in transazione
#       ANNULLATA, quindi i file degli allegati non esistono e non servono.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EmailBozzaInvioDbTests.test_la_mail_spedita_porta_autore_ed_emittente_della_bozza
   Il log nasce con `creato_da_user_id` e `emittente_fiscale_id` della bozza,
   l'autore lo rilegge sotto RLS, e l'allegato e' agganciato al log.
2) EmailBozzaInvioDbTests.test_annullare_la_bozza_toglie_gli_allegati
   Dopo l'annullo la bozza e' CANCELLED e non ha piu' righe di allegato.
3) EmailBozzaInvioDbTests.test_dopo_l_invio_l_allegato_non_si_toglie
   `remove_attachment` su una mail spedita: lo rifiuta il database con
   `E_EMAIL_ALLEGATO_NON_BOZZA`.
4) EmailLogDelCollegaDbTests.test_la_lista_del_log_non_mostra_la_mail_del_collega
   ⛔ La lista del log e' aperta a ogni operatore (skip d'area, 2026-09-26):
   la query della view (`list_logs`) da' la propria mail `OPERATORE` e non
   quella di un collega DELLO STESSO emittente. E' il caso che la sola
   whitelist emittente non sapeva escludere.
5) EmailBozzaInvioDbTests.test_modificare_la_bozza_scrive_i_cc_come_array
   `update_draft` scrive `destinatari_cc` come `text[]` (cast array del BB,
   2026-09-26) e rifiuta una chiave estranea con `E_OUTBOX`.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from django.db import DatabaseError, connection, transaction

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)


class EmailBozzaInvioDbTests(unittest.TestCase):
    def setUp(self):
        # La sonda e' la sede della regola: senza, il database e' precedente
        # al brief e questi test non hanno materia.
        richiedi_db_provvisto(
            "script.fn_scope_email_ambito(integer,character varying,bigint,integer,integer,text)"
        )

    # Scopo: costruisce mondo, account e template; torna (emittente, operatore).
    def _costruisci(self, cur) -> tuple[int, int]:
        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT emittente_fiscale_id, auth_user_id FROM _mondo")
        emittente, operatore = cur.fetchone()
        cur.execute(
            """
            INSERT INTO config.email_account
                   (codice, codice_interno, descrizione, smtp_host, smtp_username,
                    smtp_password_encrypted, email_from)
            VALUES ('BOZINVACC', 'BOZINVACC', 'Account bozza invio', 'smtp.invalid',
                    'utente', 'x', 'bozza@esempio.test')
            RETURNING id
            """
        )
        self._account = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO config.email_template (codice, oggetto, corpo_html)
            VALUES ('BOZINVTPL', 'Oggetto bozza', '<p>x</p>')
            RETURNING id
            """
        )
        self._template = cur.fetchone()[0]
        return emittente, operatore

    # Scopo: una bozza OPERATORE dell'operatore del contesto, con un allegato.
    #        Torna (outbox_id, allegato_id).
    def _bozza_con_allegato(self, emittente: int, operatore: int) -> tuple[int, int]:
        from apps.core.db.email_repository import EmailRepository

        repo = EmailRepository()
        outbox_id = repo.create_outbox(
            destinatario="cliente@esempio.test", oggetto="Offerta", corpo_html="<p>x</p>",
            email_account_id=self._account, email_template_id=self._template,
            ambito="OPERATORE", emittente_fiscale_id=emittente, creato_da_user_id=operatore,
        )
        allegato_id = repo.create_allegato(
            email_outbox_id=outbox_id, nome_file="offerta.pdf", mime_type="application/pdf",
            dimensione_bytes=3, file_path="2026/09/inesistente.pdf",
        )
        return outbox_id, allegato_id

    # Scopo: spedisce la bozza dal service vero, col canale forzato a console.
    def _spedisci(self, outbox_id: int) -> dict:
        from apps.core.services.email_outbox_service import EmailOutboxService
        from apps.core.services.email_service import CANALE_CONSOLE, EmailDispatchService

        with patch.object(EmailDispatchService, "canale_invio", return_value=CANALE_CONSOLE):
            return EmailOutboxService().confirm_and_send(outbox_id)

    # 1. Il log porta autore ed emittente della bozza, e l'allegato.
    def test_la_mail_spedita_porta_autore_ed_emittente_della_bozza(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                emittente, operatore = self._costruisci(cur)
                outbox_id, allegato_id = self._bozza_con_allegato(emittente, operatore)

                esito = self._spedisci(outbox_id)

                self.assertEqual(esito["stato"], "SIMULATA")
                log_id = esito["email_log_id"]
                self.assertIsNotNone(log_id)
                # ⭐ Letta SOTTO RLS, dall'autore: se la riga c'e' e' perche' il
                #    ramo OPERATORE la da' a lui.
                cur.execute(
                    "SELECT creato_da_user_id, emittente_fiscale_id "
                    "  FROM config.email_log WHERE id = %s",
                    [log_id],
                )
                self.assertEqual(cur.fetchone(), (operatore, emittente))
                self.assertEqual(
                    [a["id"] for a in EmailRepository().list_allegati_by_log(log_id)],
                    [allegato_id],
                )
                raise Annulla
        except Annulla:
            pass

    # 2. L'annullo toglie le righe degli allegati prima di chiudere la bozza.
    def test_annullare_la_bozza_toglie_gli_allegati(self):
        from apps.core.db.email_repository import EmailRepository
        from apps.core.services.email_outbox_service import EmailOutboxService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                emittente, operatore = self._costruisci(cur)
                outbox_id, _ = self._bozza_con_allegato(emittente, operatore)

                esito = EmailOutboxService().cancel_draft(outbox_id)

                self.assertEqual(esito["stato"], "CANCELLED")
                self.assertEqual(EmailRepository().list_allegati_by_outbox(outbox_id), [])
                raise Annulla
        except Annulla:
            pass

    # 3. Dopo l'invio l'allegato e' storia: il database rifiuta di toglierlo.
    def test_dopo_l_invio_l_allegato_non_si_toglie(self):
        from apps.core.services.db_error_fields import db_error_code
        from apps.core.services.email_outbox_service import EmailOutboxService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                emittente, operatore = self._costruisci(cur)
                outbox_id, allegato_id = self._bozza_con_allegato(emittente, operatore)
                self._spedisci(outbox_id)

                # ⚠️ Savepoint: il rifiuto interrompe la transazione.
                with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                    EmailOutboxService().remove_attachment(allegato_id)
                self.assertEqual(db_error_code(ctx.exception), "E_EMAIL_ALLEGATO_NON_BOZZA")
                raise Annulla
        except Annulla:
            pass

    # 5. La modifica della bozza dal service: `destinatari_cc` arriva come
    #    `text[]` (cast array del BB `sql_set_clause`, 2026-09-26), le
    #    stringhe strippate; una chiave estranea e' un 400 `E_OUTBOX`.
    def test_modificare_la_bozza_scrive_i_cc_come_array(self):
        from apps.core.services.email_outbox_service import EmailOutboxService
        from apps.core.services.service_errors import ServiceError

        try:
            with transaction.atomic(), connection.cursor() as cur:
                emittente, operatore = self._costruisci(cur)
                outbox_id, _ = self._bozza_con_allegato(emittente, operatore)

                EmailOutboxService().update_draft(
                    outbox_id, oggetto="  Offerta rivista  ",
                    destinatari_cc=["uno@esempio.test", "due@esempio.test"],
                )
                cur.execute(
                    "SELECT oggetto, destinatari_cc FROM config.email_outbox WHERE id = %s",
                    [outbox_id],
                )
                self.assertEqual(
                    cur.fetchone(),
                    ("Offerta rivista", ["uno@esempio.test", "due@esempio.test"]),
                )

                with self.assertRaises(ServiceError) as ctx:
                    EmailOutboxService().update_draft(outbox_id, stato="SENT")
                self.assertEqual(ctx.exception.code, "E_OUTBOX")
                raise Annulla
        except Annulla:
            pass


class EmailLogDelCollegaDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto(
            "script.fn_scope_email_ambito(integer,character varying,bigint,integer,integer,text)"
        )
        # ⛔ Un no-leak provato da un ruolo che salta la RLS non prova niente.
        from apps.core.tests.db_e2e import richiedi_ruolo_soggetto_a_rls

        richiedi_ruolo_soggetto_a_rls("config.email_log")

    # Scopo: scrive una mail OPERATORE come `autore`, attraverso la policy.
    def _mail_di(self, cur, autore: int, emittente: int, oggetto: str) -> int:
        cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [autore])
        cur.execute(
            """
            INSERT INTO config.email_log
                   (destinatario, oggetto, stato, ambito, emittente_fiscale_id, creato_da_user_id)
            VALUES ('x@esempio.test', %s, 'SENT', 'OPERATORE', %s, %s)
            RETURNING id
            """,
            [oggetto, emittente, autore],
        )
        return cur.fetchone()[0]

    # 4. Stesso emittente, due autori: ciascuno vede solo la sua.
    def test_la_lista_del_log_non_mostra_la_mail_del_collega(self):
        from apps.core.db.email_repository import EmailRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                # ⚠️ Ogni builder in un'istruzione sua: scrive una saga.
                cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
                emittente = cur.fetchone()[0]
                cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('email io')")
                io = cur.fetchone()[0]
                cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('email collega')")
                collega = cur.fetchone()[0]
                cur.execute(
                    "SELECT script.fn_change_user_emittenti_scope(u, ARRAY[%s]::bigint[]) "
                    "  FROM unnest(ARRAY[%s, %s]) AS u",
                    [emittente, io, collega],
                )
                mia = self._mail_di(cur, io, emittente, "mail mia")
                sua = self._mail_di(cur, collega, emittente, "mail del collega")

                cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [io])
                visti = {r["id"] for r in EmailRepository().list_logs(limit=200)[0]}

                self.assertIn(mia, visti)
                self.assertNotIn(
                    sua, visti,
                    "la lista del log mostra la mail OPERATORE di un collega dello "
                    "stesso emittente: aperta a ogni operatore, sarebbe una fuga",
                )
                raise Annulla
        except Annulla:
            pass
