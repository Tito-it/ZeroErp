# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I SETTE lettori che leggono un `jsonb` da un cursor RAW devono
#        decodificarlo quando arriva come STRINGA — che e' la forma in cui il
#        driver lo consegna davvero (psycopg 3 non decodifica i jsonb fuori
#        dall'ORM). Database MOCKATO: qui si prova la lettura, non la query.
# Note: ⛔ PERCHE' ESISTE. Il 2026-09-09 questi punti (otto allora, sette dal
#        2026-10-31; il nome del file e' quello di allora) sono passati dalla
#        coercizione scritta a mano al building block `jsonb_out`. Una
#        MUTAZIONE (spegnere `jsonb_out`) ha fatto cadere otto test — e
#        **nessuno dei quali toccava questi punti**: erano tutti
#        consumatori storici del BB. Cioe' la conversione era CIECA.
#        ⭐ Un cambiamento che nessun test vede non e' verificato dal fatto che
#        la suite resti verde: e' verificato dal fatto che qualcosa diventi
#        rosso se lo si sbaglia.
#        ⚠️ Il gemello statico e' `apps/core/tests/test_coercizione_jsonb_dal_bb`,
#        che vieta di riscrivere il BB a mano. Quello presidia la FORMA, questo
#        il COMPORTAMENTO: nessuno dei due copre l'altro.
# ------------------------------------------------------------

"""Indice test previsti.

1. test_ogni_lettore_decodifica_il_jsonb_stringa
   I sette punti, uno per sotto-prova: la stringa entra, un dict esce.
2. test_i_sette_punti_sono_ancora_sette
   Il verso opposto: se un lettore sparisse o cambiasse nome, la sotto-prova
   svanirebbe in silenzio e il test resterebbe verde su sei.
"""

from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch


# Scopo: un `connection` finto il cui cursore risponde sempre `riga`.
def _connection(riga, *, molte: bool = False):
    cursore = MagicMock()
    cursore.fetchone.return_value = riga
    cursore.fetchall.return_value = [riga] if molte else []
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursore
    return conn


# La forma che il driver consegna: un jsonb come TESTO.
_PAYLOAD = {"bloccato": True, "minuti_rimanenti": 5, "tentativi": 9, "chiave": "valore"}
_STRINGA = json.dumps(_PAYLOAD)


# Scopo: (etichetta, modulo da patchare, chiamata) per ciascuno dei sette.
#        ⚠️ La chiamata riceve il `connection` finto gia' attivo: costruisce il
#        repository e invoca il metodo con argomenti qualunque — la query e'
#        mockata, contano solo il valore che torna e come viene letto.
def _lettori():
    from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
    from apps.core.db.auth_repository import AuthRepository
    from apps.core.db.email_repository import EmailRepository
    from apps.core.db.search_repository import SearchRepository
    from apps.ui.db.dashboard_repository import DashboardRepository
    from apps.ui.db.ui_repository import UiRepository

    return (
        (
            "auth_repository.registra_tentativo_login",
            "apps.core.db.auth_repository.connection",
            lambda: AuthRepository().registra_tentativo_login(
                1, nome_digest=bytes(32), provenienza="203.0.113.7", successo=False,
            ),
        ),
        # ⛔ `search_repository.search_soggetti` non c'e' piu' (2026-10-31): la
        #    ricerca universale e' diventata la lista `anagrafiche.ricerca_soggetti`
        #    e legge la funzione per COLONNE (`SELECT r.*`), non piu' come un
        #    `row_to_json` da decodificare. Nessun jsonb da leggere, nessun
        #    lettore: gli otto sono sette.
        (
            "search_repository.get_search_detail",
            "apps.core.db.search_repository.connection",
            lambda: SearchRepository().get_search_detail(
                soggetto_id="00000000-0000-0000-0000-000000000000", tipo_ruolo_id=1
            ),
        ),
        (
            "email_repository.resolve_account",
            "apps.core.db.email_repository.connection",
            lambda: EmailRepository().resolve_account(),
        ),
        (
            "email_repository.resolve_template",
            "apps.core.db.email_repository.connection",
            lambda: EmailRepository().resolve_template("INVITO"),
        ),
        (
            "invito_operatore_service._check_invitabile",
            "apps.anagrafiche.services.invito_operatore_service.connection",
            lambda: InvitoOperatoreService()._check_invitabile(1),
        ),
        (
            "ui_repository.resolve_lista_config",
            "apps.ui.db.ui_repository.connection",
            lambda: UiRepository().resolve_lista_config(
                lista_codice="clienti", auth_user_id=1, emittente_fiscale_id=None
            ),
        ),
        (
            "dashboard_repository.resolve_dashboard_config",
            "apps.ui.db.dashboard_repository.connection",
            lambda: DashboardRepository().resolve_dashboard_config(
                dashboard_codice="home", auth_user_id=1, emittente_fiscale_id=None
            ),
        ),
    )


class JsonbStringaNeiSetteLettoriTests(TestCase):

    # 1. La stringa entra, un dict esce. ⛔ Senza `jsonb_out` da qui uscirebbe la
    #    STRINGA, e il difetto si vedrebbe piu' a valle — al primo `.get`, o
    #    peggio in un `if not config` che direbbe «non trovato» su una cosa che
    #    c'e'.
    def test_ogni_lettore_decodifica_il_jsonb_stringa(self):
        for etichetta, modulo_connection, chiama in _lettori():
            with self.subTest(lettore=etichetta):
                with patch(modulo_connection, _connection((_STRINGA,), molte=True)):
                    esito = chiama()
                self.assertIsInstance(
                    esito, dict, f"{etichetta}: il jsonb stringa non e' stato decodificato"
                )
                self.assertEqual(esito.get("chiave"), "valore")

    # 2. ⚠️ Se un lettore sparisse o cambiasse nome, la sua sotto-prova
    #    svanirebbe **in silenzio** e il test resterebbe verde su sei: e' la
    #    forma di «verde per sottrazione» che il progetto insegue.
    def test_i_sette_punti_sono_ancora_sette(self):
        # Sette dal 2026-10-31 (la ricerca universale, vedi `_lettori`).
        self.assertEqual(len(_lettori()), 7)
