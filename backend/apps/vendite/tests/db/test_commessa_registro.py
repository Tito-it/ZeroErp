# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il REGISTRO delle righe di commessa — lettura, scope e guard.
# Note: mock su connection.cursor — nessun DB (regola CI di AGENTS.md).
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Fino al 2026-08-28 `vendite.commesse_attivita_log` **si scriveva e non si
leggeva**: sei tipi di evento registrati fedelmente dal database e irraggiungibili
da qualunque schermata. Trovato in collaudo — una riga passata ad `ANNULLATA` da
se', e nessun modo di sapere perche'.

⛔ IL TEST CHE CONTA E' IL PRIMO: **lo scope sta sulla riga di commessa, non sul
log**. `commesse_attivita_log` non ha row level security, `commesse_attivita`
si'. Leggere il log da solo sarebbe **fail-open** — si vedrebbero i motivi di
commesse fuori perimetro. Il `JOIN` non e' una decorazione per prendere due
colonne: e' il cancello, ed e' la stessa lezione gia' pagata su
`attivita_fatturabili` col verbo «Riporta da emettere».

Indice test:

 1) test_lo_scope_passa_dal_join_su_commesse_attivita — 🔴 il cancello, su count E righe
 2) test_filtro_per_riga_quando_richiesto              — il caso d'uso del kebab
 3) test_senza_riga_prende_tutta_la_commessa           — nessun filtro di troppo
 4) test_ordine_cronologico_inverso                    — l'ultimo fatto in cima
 5) test_nessun_evento_e_nominato_nella_query          — vocabolario aperto
 6) test_jsonb_stringa_non_diventa_caratteri           — il ramo difensivo
 7) test_limite_di_pagina_rifiutato                    — guard del service
 8) test_offset_negativo_rifiutato                     — idem
"""

import json
import unittest
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.services.commesse_service import fn_commessa_registro
from apps.vendite.tests._helpers.mock_cursor import mock_cursor as _mock_cursor

_RIGA = (
    7, 148, "RIGA_RITIRATA_DA_SORGENTE",
    {"motivo": "Ritiro automatico", "stato_precedente": "NON_EMESSA"},
    "Ritiro automatico", None, "tid",
    "PREVENTIVO:abc:R:285", "ANNULLATA", "NORMALE", "ART-1", "Articolo uno",
)


def _esegui(**kwargs):
    """Ritorna (righe, totale, elenco degli SQL eseguiti)."""
    with patch("apps.vendite.db.commesse_repository.connection.cursor") as fab:
        fab.return_value = _mock_cursor(fetchone=(1,), fetchall=[_RIGA])
        righe, tot = CommesseRepository().list_registro_attivita(113, **kwargs)
        sql = [c[0][0] for c in fab.return_value.execute.call_args_list]
        return righe, tot, sql


class RegistroCommessaScopeTests(unittest.TestCase):

    # Scopo: 🔴 IL CANCELLO. Il log non ha RLS, `commesse_attivita` si': la
    #        lettura deve passare dal JOIN, e deve passarci ANCHE il conteggio —
    #        un totale calcolato senza cancello direbbe «12 eventi» mostrandone 3.
    def test_lo_scope_passa_dal_join_su_commesse_attivita(self):
        _righe, _tot, sql = _esegui(limit=100, offset=0)
        self.assertEqual(len(sql), 2, "attese due query: conteggio e pagina")
        for q in sql:
            self.assertIn("JOIN vendite.commesse_attivita ca", q)
            self.assertIn("ca.commessa_id = %s", q)

    # Scopo: il kebab di riga chiede UNA riga sola.
    def test_filtro_per_riga_quando_richiesto(self):
        _righe, _tot, sql = _esegui(commessa_attivita_id=148, limit=100, offset=0)
        for q in sql:
            self.assertIn("l.commessa_attivita_id = %s", q)

    # Scopo: senza quel parametro non si filtra per riga (tutta la commessa).
    def test_senza_riga_prende_tutta_la_commessa(self):
        _righe, _tot, sql = _esegui(limit=100, offset=0)
        for q in sql:
            self.assertNotIn("l.commessa_attivita_id = %s", q)

    # Scopo: l'ultimo fatto in cima — un registro in ordine diretto costringe a
    #        scorrere fino in fondo per sapere com'e' finita.
    def test_ordine_cronologico_inverso(self):
        _righe, _tot, sql = _esegui(limit=100, offset=0)
        self.assertIn("ORDER BY l.data_insert DESC, l.id DESC", sql[1])

    # Scopo: ⛔ Il vocabolario degli eventi e' del DATABASE ed e' APERTO. Se la
    #        query nominasse un evento, quelli nuovi sparirebbero in silenzio.
    def test_nessun_evento_e_nominato_nella_query(self):
        _righe, _tot, sql = _esegui(limit=100, offset=0)
        for nome in ("ONERE_AGGIUNTO", "RIGA_RITIRATA_DA_SORGENTE",
                     "RIGA_RIPORTATA_DA_EMETTERE", "ACCREDITO_RICHIESTO"):
            for q in sql:
                self.assertNotIn(nome, q)

    # Scopo: ⚠️ Il `jsonb` puo' arrivare come STRINGA su questa connessione.
    #        Senza il ramo difensivo il frontend riceverebbe una stringa dove
    #        aspetta un oggetto, e renderebbe caratteri invece di campi.
    def test_jsonb_stringa_non_diventa_caratteri(self):
        riga = list(_RIGA)
        riga[3] = json.dumps({"motivo": "x", "stato_precedente": "EMESSA"})
        with patch("apps.vendite.db.commesse_repository.connection.cursor") as fab:
            fab.return_value = _mock_cursor(fetchone=(1,), fetchall=[tuple(riga)])
            righe, _tot = CommesseRepository().list_registro_attivita(113)
        self.assertIsInstance(righe[0]["dettaglio"], dict)
        self.assertEqual(righe[0]["dettaglio"]["stato_precedente"], "EMESSA")


class RegistroCommessaGuardTests(unittest.TestCase):

    # Scopo: il tetto di pagina risponde 400 e DICE il limite.
    def test_limite_di_pagina_rifiutato(self):
        for cattivo in (0, 201, -5):
            with self.subTest(limit=cattivo), self.assertRaises(ServiceError) as exc:
                fn_commessa_registro(commessa_id=113, limit=cattivo)
            self.assertEqual(exc.exception.code, "E_COMMESSA_VALIDATION")

    # Scopo: offset negativo rifiutato.
    def test_offset_negativo_rifiutato(self):
        with self.assertRaises(ServiceError):
            fn_commessa_registro(commessa_id=113, offset=-1)
