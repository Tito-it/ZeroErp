# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La lista `core.sessioni_attive` sul DB VERO: l'esclusione della
#        sessione corrente nella SQL, il conteggio che la segue, lo spareggio
#        dell'ultimo evento e l'ordinamento della whitelist.
#
# ⭐ PERCHE' SUL DB VERO. Il motivo del cambio del 2026-09-27 (la corrente tolta
#    nella SQL e non in Python) sta tutto nei parametri posizionali della CTE:
#    i test col mock di `fetch_paged_with_total` guardano la stringa, non la
#    riga che sparisce ne' il totale che ne tiene conto.
# ⭐ CASI COSTRUITI: un utente fabbricato dal test e le sue sessioni, in una
#    transazione sempre annullata. Nessuna riga di sviluppo letta come dato.
# ------------------------------------------------------------
"""Indice test (1..4) — opt-in `ZEROERP_TEST_DB_E2E=1`:

1. test_la_corrente_esce_dalla_pagina_e_dal_totale
2. test_senza_sid_non_si_esclude_niente
3. test_stesso_istante_vince_l_ultimo_evento_scritto
4. test_data_inizio_ordina_in_entrambi_i_versi
"""

from __future__ import annotations

import unittest
import uuid

from django.contrib.auth.models import User
from django.db import connection, transaction

from apps.core.db.session_audit_repository import SessionAuditRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto


# ⚠️ `unittest.TestCase` e non un TestCase Django: la connessione resta quella
#    configurata (vedi `db_e2e`), e ogni test annulla la sua transazione.
class SessioniAttiveDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: esegue `corpo(utente_id, sid)` dentro una transazione annullata,
    #        con un utente nuovo e tre sessioni: `a` (la piu' vecchia), `b`
    #        (la piu' recente), `chiusa` (LOGIN poi LOGOUT: non attiva).
    def _con_sessioni(self, corpo) -> None:
        with transaction.atomic():
            utente = User.objects.create(username=f"sess-db-{uuid.uuid4().hex[:12]}")
            sid = {k: f"{k}-{uuid.uuid4().hex}" for k in ("a", "b", "chiusa")}
            with connection.cursor() as cur:
                for chiave, evento, minuti_fa in (
                    ("a", "LOGIN", 30),
                    ("b", "LOGIN", 10),
                    ("chiusa", "LOGIN", 20),
                    ("chiusa", "LOGOUT", 5),
                ):
                    cur.execute(
                        "INSERT INTO dbops.sessioni_utente "
                        "       (auth_user_id, evento, jti, ip_address, user_agent, data_insert) "
                        "VALUES (%s, %s, %s, '10.1.2.3', 'SessDb/1.0', "
                        "        now() - make_interval(mins => %s))",
                        [utente.id, evento, sid[chiave], minuti_fa],
                    )
            try:
                corpo(utente.id, sid)
            finally:
                transaction.set_rollback(True)

    # 1. La corrente non c'e' nella pagina e non la conta ne' il totale della
    #    pagina ne' `conta_sessioni_attive` (il badge).
    def test_la_corrente_esce_dalla_pagina_e_dal_totale(self) -> None:
        def corpo(utente_id, sid):
            repo = SessionAuditRepository()
            righe, totale = repo.list_sessioni_attive_paginata(utente_id, escludi_jti=sid["a"])
            self.assertEqual([r["jti"] for r in righe], [sid["b"]])
            self.assertEqual(totale, 1)
            self.assertEqual(repo.conta_sessioni_attive(utente_id, escludi_jti=sid["a"]), 1)
        self._con_sessioni(corpo)

    # 2. Senza sid (`None`) si vedono tutte le attive: `IS DISTINCT FROM`, non
    #    `<>`, che con NULL avrebbe tolto tutto.
    def test_senza_sid_non_si_esclude_niente(self) -> None:
        def corpo(utente_id, sid):
            repo = SessionAuditRepository()
            righe, totale = repo.list_sessioni_attive_paginata(utente_id, escludi_jti=None)
            self.assertEqual({r["jti"] for r in righe}, {sid["a"], sid["b"]})
            self.assertEqual(totale, 2)
            self.assertEqual(repo.conta_sessioni_attive(utente_id, escludi_jti=None), 2)
        self._con_sessioni(corpo)

    # 3. Due eventi dello stesso sid nello STESSO istante: decide l'ultimo
    #    scritto (`id DESC`), non il caso. Un LOGOUT scritto dopo un REFRESH
    #    con lo stesso timestamp chiude la sessione.
    def test_stesso_istante_vince_l_ultimo_evento_scritto(self) -> None:
        def corpo(utente_id, sid):
            with connection.cursor() as cur:
                for evento in ("REFRESH", "LOGOUT"):
                    cur.execute(
                        "INSERT INTO dbops.sessioni_utente "
                        "       (auth_user_id, evento, jti, data_insert) "
                        "VALUES (%s, %s, %s, date_trunc('second', now()))",
                        [utente_id, evento, sid["b"]],
                    )
            repo = SessionAuditRepository()
            righe, totale = repo.list_sessioni_attive_paginata(utente_id, escludi_jti=None)
            self.assertEqual([r["jti"] for r in righe], [sid["a"]])
            self.assertEqual(totale, 1)
        self._con_sessioni(corpo)

    # 4. La whitelist ordina davvero sul DB: `data_inizio` in ASC e in DESC.
    def test_data_inizio_ordina_in_entrambi_i_versi(self) -> None:
        def corpo(utente_id, sid):
            repo = SessionAuditRepository()
            for verso, attese in (("asc", [sid["a"], sid["b"]]), ("desc", [sid["b"], sid["a"]])):
                righe, _ = repo.list_sessioni_attive_paginata(
                    utente_id, escludi_jti=None, order_by="data_inizio", order_dir=verso,
                )
                self.assertEqual([r["jti"] for r in righe], attese, verso)
        self._con_sessioni(corpo)
