# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA PORTA DI SISTEMA delle email — che si apra per chi deve, e che non si
#        apra per altro.
#
# ⛔ PERCHE' ESISTE, e non e' teoria: il 2026-09-05, accesa la RLS su
#    `config.email_log`, DUE percorsi veri si sono rotti in silenzio —
#    il reset password (endpoint NON autenticato: nessuna sessione, nessuna GUC)
#    e gli inviti fatti da un admin che super admin non e'. Misurato allora:
#    entrambi RIFIUTATI dalla policy. Il rimedio sono le due funzioni
#    `SECURITY DEFINER` del team DB, e questo test prova che il backend le usi.
#
# ⭐ LA PROPRIETA' CHE CONTA E' LA TERZA. Una porta che scrive senza sessione e'
#    utile e pericolosa alla stessa maniera: il suo pregio e' che sappia scrivere
#    UNA COSA SOLA. Se `fn_chiudi_email_sistema` accettasse anche l'email di
#    un'azienda, sarebbe la porta di servizio che tutta la policy esiste per
#    chiudere — e nessun altro test se ne accorgerebbe.
#
# ⚠️ SI PASSA DAL REPOSITORY VERO (`insert_log`, `update_log_stato`), non da SQL
#    scritto qui: la cosa da provare e' che il BACKEND scelga la porta giusta,
#    non che le funzioni esistano — quelle le prova il pgTAP del team DB.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    Scrive, ma in transazione ANNULLATA.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_una_email_di_sistema_si_scrive_e_si_chiude_senza_sessione
     il percorso del reset password: nessuna GUC, deve funzionare.
2. test_la_porta_di_sistema_rifiuta_l_email_di_un_azienda
     ⛔ la proprieta' di sicurezza: la porta sa scrivere una cosa sola.
3. test_il_rilancio_riparte_da_un_account_acceso_e_il_log_lo_dice
     R5: account del log spento → account acceso risolto, scritto con l'esito
     sulle due porte (SISTEMA e UPDATE diretto).
4. test_un_esito_senza_account_lascia_l_account_com_e
     `email_account_id=None` non tocca la colonna, sulle due porte.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_constants import AMBITO_OPERATORE, AMBITO_SISTEMA
from apps.core.tests.db_e2e import richiedi_db_provvisto

_INVIATO_AT = "2026-09-06T10:00:00+02:00"


class EmailPortaDiSistemaTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        self.repo = EmailRepository()

    # Scopo: azzera le GUC dell'identita' — il contesto di un endpoint non
    #        autenticato, che e' esattamente dove nasce un reset password.
    def _senza_sessione(self, cur) -> None:
        cur.execute(
            "SELECT set_config('app.ruolo_applicativo', '', true),"
            "       set_config('app.current_user_id', '', true)"
        )

    # 1. Il percorso rotto del 2026-09-05: scrivere E chiudere senza sessione.
    #    ⭐ Le due cose insieme, perche' separarle era il difetto: instradare il
    #    solo INSERT avrebbe spostato la rottura di due righe, sull'UPDATE.
    def test_una_email_di_sistema_si_scrive_e_si_chiude_senza_sessione(self) -> None:
        with transaction.atomic(), connection.cursor() as cur:
            self._senza_sessione(cur)
            log_id = self.repo.insert_log(
                email_account_id=None, email_template_id=None,
                destinatario="reset@esempio.test", oggetto="Reimposta la password",
                corpo_inviato_html="<p>link</p>", stato="PENDING",
                ambito=AMBITO_SISTEMA,
            )
            self.assertIsNotNone(log_id)
            self.assertTrue(
                self.repo.update_log_stato(
                    log_id, "SENT", ambito=AMBITO_SISTEMA, inviato_at=_INVIATO_AT,
                ),
                "l'esito dell'invio non e' stato scritto: la mail risulterebbe "
                "ancora da spedire e il worker la rimanderebbe",
            )
            transaction.set_rollback(True)

    # 2. ⛔ LA PROPRIETA' DI SICUREZZA. La porta di sistema non deve poter
    #    toccare l'email di un'azienda: sarebbe il modo per aggirare la policy
    #    scrivendo «SISTEMA» su una riga che non lo e'.
    # ⚠️ Il caso si COSTRUISCE: righe non-SISTEMA sul database di sviluppo non ce
    #    ne sono, e un test che non trova materia sarebbe verde per sottrazione.
    # Scopo: il contesto del processo `send_pending_emails`, l'utente tecnico
    #         del roster: e' l'identita' con cui il rilancio legge la coda e
    #         scrive gli esiti. Ritorna `(auth_user_id, emittente_fiscale_id)`.
    # ⚠️ Salta se il roster non ha l'utente: senza un perimetro non si
    #    costruisce l'email di un'azienda.
    def _contesto_del_processo(self, cur) -> tuple[int, int]:
        cur.execute(
            "SELECT auth_user_id, identita_id, emittente_fiscale_id "
            "  FROM dbops.vw_processi_roster "
            " WHERE processo_codice = 'send_pending_emails' LIMIT 1"
        )
        riga = cur.fetchone()
        if riga is None:
            self.skipTest(
                "nessun utente tecnico per send_pending_emails: senza un "
                "perimetro non si puo' costruire l'email di un'azienda"
            )
        auth_user_id, identita_id, emittente_id = riga
        cur.execute(
            """
            SELECT set_config('app.jwt_user', 'test', true),
                   set_config('app.current_user_id', %s, true),
                   set_config('app.current_identita_id', %s, true),
                   set_config('app.ruolo_applicativo', 'OPERATORE', true),
                   set_config('app.soggetto_ruolo_id',
                              (SELECT soggetto_ruolo_id::text
                                 FROM anagrafiche.identita_digitali
                                WHERE id = %s), true)
            """,
            [str(auth_user_id), str(identita_id), str(identita_id)],
        )
        return auth_user_id, emittente_id

    def test_la_porta_di_sistema_rifiuta_l_email_di_un_azienda(self) -> None:
        with transaction.atomic(), connection.cursor() as cur:
            auth_user_id, emittente_id = self._contesto_del_processo(cur)
            # ⚠️ Una mail `OPERATORE` nomina il suo autore (D-5 di
            #    brief-db-email-visibilita-per-ambito): qui e' l'utente del
            #    contesto, che la scrive e la chiude.
            cur.execute(
                """
                INSERT INTO config.email_log
                    (destinatario, oggetto, corpo_inviato_html, stato,
                     ambito, emittente_fiscale_id, creato_da_user_id)
                VALUES ('azienda@esempio.test', 'fattura', '<p>x</p>', 'PENDING',
                        %s, %s, %s)
                RETURNING id
                """,
                [AMBITO_OPERATORE, emittente_id, auth_user_id],
            )
            log_id = cur.fetchone()[0]

            # ⚠️ Savepoint PRIMA del tentativo: il rifiuto interrompe la
            #    transazione, e senza si perderebbe anche la controprova.
            cur.execute("SAVEPOINT abuso")
            with self.assertRaises(Exception) as ctx:
                self.repo.update_log_stato(log_id, "SENT", ambito=AMBITO_SISTEMA)
            self.assertIn("SISTEMA", str(ctx.exception))
            cur.execute("ROLLBACK TO SAVEPOINT abuso")

            # ⭐ La controprova: dalla porta giusta la stessa riga si chiude. Senza,
            #    «rifiutata» potrebbe voler dire «rotta per un'altra ragione».
            self.assertTrue(
                self.repo.update_log_stato(
                    log_id, "SENT", ambito=AMBITO_OPERATORE, inviato_at=_INVIATO_AT,
                )
            )
            transaction.set_rollback(True)

    # Scopo: le due mail del rilancio, una per porta, accodate su un account
    #        costruito e poi SPENTO (Q24: un account che ha spedito si spegne e
    #        non si cancella). Ritorna `(account_spento, {ambito: log_id})`.
    # ⚠️ L'account lo crea l'operatore del mondo costruito; le mail nascono gia'
    #    nel contesto del processo, che e' quello che le deve vedere in coda.
    def _mail_su_account_spento(self, cur) -> tuple[int, dict[str, int]]:
        cur.execute(
            "CREATE TEMP TABLE _mondo AS "
            "SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m"
        )
        cur.execute(
            "SELECT script.fn_pgtap_set_contesto_operatore("
            "(SELECT auth_user_id FROM _mondo))"
        )
        spento = self.repo.create_account(
            codice="R5RILANCIO", descrizione="Account spento del test R5",
            smtp_host="smtp.invalid", smtp_port=587,
            smtp_use_tls=True, smtp_use_ssl=False,
            smtp_username="utente", smtp_password="segreta",
            email_from="r5@esempio.test",
        )
        self.assertTrue(self.repo.update_account(spento, attivo=False))

        processo, emittente_id = self._contesto_del_processo(cur)
        comuni = {
            "email_account_id": spento, "email_template_id": None,
            "oggetto": "Rilancio", "corpo_inviato_html": "<p>x</p>",
            "stato": "PENDING",
        }
        mail = {
            AMBITO_SISTEMA: self.repo.insert_log(
                destinatario="sistema@esempio.test", ambito=AMBITO_SISTEMA, **comuni,
            ),
            AMBITO_OPERATORE: self.repo.insert_log(
                destinatario="azienda@esempio.test", ambito=AMBITO_OPERATORE,
                emittente_fiscale_id=emittente_id, creato_da_user_id=processo,
                **comuni,
            ),
        }
        return spento, mail

    def _account_sul_log(self, cur, log_id: int) -> int | None:
        cur.execute("SELECT email_account_id FROM config.email_log WHERE id = %s", [log_id])
        riga = cur.fetchone()
        self.assertIsNotNone(riga, f"il processo non vede la mail {log_id}")
        return riga[0]

    # 3. ⭐ R5 (brief-db-seed-primo-impianto-non-si-riscrive §16.16): una mail
    #    in coda su un account spento riparte da un account ACCESO, e il log
    #    dice quello — sulle due porte, la funzione di sistema e l'UPDATE diretto.
    # ⛔ Prima ripartiva dall'account spento, e il log continuava a nominarlo.
    def test_il_rilancio_riparte_da_un_account_acceso_e_il_log_lo_dice(self) -> None:
        from apps.core.management.commands.send_pending_emails import (
            _account_del_rilancio,
        )

        with transaction.atomic(), connection.cursor() as cur:
            spento, mail = self._mail_su_account_spento(cur)
            for ambito, log_id in mail.items():
                with self.subTest(ambito=ambito):
                    log_detail = self.repo.get_log(log_id)
                    self.assertIsNotNone(log_detail)
                    assert log_detail is not None
                    account = _account_del_rilancio(
                        self.repo, {"email_account_id": spento}, log_detail,
                    )
                    if account is None:
                        self.skipTest("nessun account acceso a cui ripiegare")
                    assert account is not None
                    self.assertNotEqual(account["id"], spento)
                    self.assertIs(self.repo.get_account(account["id"])["attivo"], True)

                    self.assertTrue(self.repo.update_log_stato(
                        log_id, "RETRY", ambito=ambito, errore="tentativo",
                        email_account_id=account["id"],
                    ))
                    self.assertEqual(self._account_sul_log(cur, log_id), account["id"])
            transaction.set_rollback(True)

    # 4. L'esito senza account lascia la colonna com'e', sulle due porte: e' il
    #    ramo «nessun account configurato» del giro, che non ne ha uno da dire.
    def test_un_esito_senza_account_lascia_l_account_com_e(self) -> None:
        with transaction.atomic(), connection.cursor() as cur:
            spento, mail = self._mail_su_account_spento(cur)
            for ambito, log_id in mail.items():
                with self.subTest(ambito=ambito):
                    self.assertTrue(self.repo.update_log_stato(
                        log_id, "FAILED", ambito=ambito, errore="nessun account",
                    ))
                    self.assertEqual(self._account_sul_log(cur, log_id), spento)
            transaction.set_rollback(True)
