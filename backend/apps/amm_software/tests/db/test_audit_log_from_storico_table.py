# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello fra le DUE identita' di una sorgente di audit — il `code`
#        LOGICO e la `storico_table` FISICA — nell'unico punto in cui il
#        backend le confonde volentieri: la `FROM` dell'`UNION ALL` di
#        `list_audit_log`.
#
#        PERCHE' ESISTE. Per un anno le due hanno COINCISO su tutte e nove le
#        sorgenti, e finche' coincidono dedurre la seconda dalla prima sembra
#        funzionare — non c'e' nessun caso che smentisca. Poi
#        `anagrafiche.risorse_umane_auth_user` e' diventata una VISTA (la
#        tabella e' `_legacy_risorse_umane_auth_user`): su un database
#        RICOSTRUITO `storico.risorse_umane_auth_user` non nasce piu', e la CI
#        e' andata rossa con 9 errori tutti uguali.
#
#        🔴 IL DATABASE DI SVILUPPO NON LO VEDEVA, ed e' la parte che conta: si
#        portava dietro la storico vecchia dalla propria storia, quindi il
#        difetto era invisibile esattamente dove si lavora e visibile solo a
#        chi ricostruisce. Un test che girasse «contro il database di turno»
#        sarebbe stato verde per la stessa ragione per cui lo era il dev.
#
#        ⭐ PER QUESTO QUI NON SI TOCCA IL DATABASE. Si sostituisce l'elenco
#        delle sorgenti con una in cui `code` e `storico_table` DIVERGONO — il
#        caso che il catalogo reale oggi non contiene — e si legge l'SQL
#        GENERATO. E' l'unico modo di provare la regola: sul catalogo di oggi
#        entrambe le implementazioni, quella giusta e quella sbagliata,
#        producono la stessa stringa.
#
# ⚠️ NON serve il database: `connection.cursor` e' un doppio. E' voluto — la
#    domanda e' «che SQL scrivi», non «quel SQL gira».
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_il_from_usa_storico_table_non_il_code
   La `FROM` nomina `storico_table`, e il nome costruito da `code` NON compare.

1. test_fn_audit_summary_usa_il_code_non_la_tabella
   Il verso opposto, ed e' altrettanto importante: la chiave di dispatch di
   `fn_audit_summary` e' l'identita' LOGICA. Sostituirla con la tabella
   «uniformando» romperebbe il lookup nel catalogo.

2. test_il_payload_pubblico_non_espone_storico_table
   `list_audit_sources` e' il contratto della tendina del drawer: il nome
   fisico di una tabella non e' un dato che il frontend debba ricevere.

3. test_sorgente_con_storico_table_malformata_viene_saltata
   La rete di sicurezza sull'interpolazione: la `storico_table` e'
   QUALIFICATA, quindi ha una regex sua — con quella del `code` (che non
   ammette il punto) verrebbero scartate TUTTE le righe, cioe' un audit log
   vuoto invece di un errore.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

# Una sorgente in cui i due nomi DIVERGONO. ⭐ E' il cuore del test: sul
# catalogo vero non ne esiste nessuna, quindi senza inventarla qui non c'e'
# niente che possa distinguere l'implementazione giusta da quella sbagliata.
_CODE = "risorse_umane_auth_user"
_TABELLA = "storico._legacy_risorse_umane_auth_user"
_SORGENTE = (_CODE, "amm.audit_tabella_ruolo", "AUTH", _TABELLA)


# Scopo: esegue `list_audit_log` con un elenco di sorgenti dato e restituisce
#        l'SQL che il repository ha scritto.
# ⚠️ `fetchall` torna vuoto: al metodo basta per uscire, e qui le righe non
#    servono — si guarda la query, non il risultato.
def _sql_generato(sorgenti: tuple[tuple[str, str, str, str], ...], **kwargs: Any) -> str:
    cursore = MagicMock()
    cursore.fetchall.return_value = []
    contesto = MagicMock()
    contesto.__enter__.return_value = cursore
    with (
        patch.object(
            AmmSoftwareRepository, "_list_audit_sources_cached", return_value=sorgenti
        ),
        patch(
            "apps.amm_software.db.amm_software_repository.connection.cursor",
            return_value=contesto,
        ),
    ):
        AmmSoftwareRepository().list_audit_log(**kwargs)
    # `execute(sql, params)` — il primo posizionale e' la query.
    assert cursore.execute.called, (
        "nessuna query eseguita: il metodo e' uscito prima di scrivere l'SQL, "
        "e il test starebbe guardando il nulla"
    )
    return cursore.execute.call_args[0][0]


class AuditLogFromStoricoTableTests(unittest.TestCase):
    """Il `FROM` dell'audit log si costruisce dal nome FISICO."""

    def test_il_from_usa_storico_table_non_il_code(self) -> None:
        sql = _sql_generato((_SORGENTE,))
        self.assertIn(
            f"FROM {_TABELLA} s",
            sql,
            "la FROM non nomina `storico_table`: il backend sta ancora "
            "deducendo il nome fisico da un'altra colonna",
        )
        # ⛔ La meta' che conta davvero. Il nome costruito da `code` e' quello
        #    che su un database ricostruito NON ESISTE: se compare, il difetto
        #    e' tornato — e non fallirebbe da nessuna parte fino al giorno in
        #    cui qualcuno ricostruisce.
        self.assertNotIn(
            f"FROM storico.{_CODE} s",
            sql,
            "la FROM e' costruita concatenando `code`: e' il difetto del "
            "2026-09-02, invisibile sul database di sviluppo e rosso in CI",
        )

    def test_fn_audit_summary_usa_il_code_non_la_tabella(self) -> None:
        sql = _sql_generato((_SORGENTE,))
        # ⭐ `fn_audit_summary` fa il dispatch LEGGENDO `dbops.audit_sources`
        #    per `code`: passarle la tabella «per uniformita'» la manderebbe a
        #    cercare una riga che non c'e'. Le due interpolazioni sono diverse
        #    apposta, e questo test esiste perche' non vengano «allineate».
        self.assertIn(f"script.fn_audit_summary('{_CODE}', s.id)", sql)
        self.assertNotIn(f"script.fn_audit_summary('{_TABELLA}'", sql)

    def test_il_payload_pubblico_non_espone_storico_table(self) -> None:
        with patch.object(
            AmmSoftwareRepository,
            "_list_audit_sources_cached",
            return_value=(_SORGENTE,),
        ):
            righe = AmmSoftwareRepository().list_audit_sources()
        self.assertEqual(
            [sorted(r) for r in righe],
            [["area_funzionale", "code", "label_key"]],
            "`list_audit_sources` e' il contratto API della tendina del drawer "
            "e l'insieme dei codici ammessi: il nome fisico di una tabella non "
            "e' un dato che il frontend debba ricevere",
        )

    def test_sorgente_con_storico_table_malformata_viene_saltata(self) -> None:
        buona = _SORGENTE
        # Non qualificata: la regex la rifiuta, e la riga esce dall'UNION.
        cattiva = ("altra", "amm.x", "PERMESSI", "senza_schema")
        sql = _sql_generato((buona, cattiva))
        self.assertIn(f"FROM {_TABELLA} s", sql)
        self.assertNotIn("FROM senza_schema s", sql)
        # ⛔ E la buona DEVE restare: il difetto da cui questa regex protegge e'
        #    quello di riusare `_AUDIT_CODE_RE`, che non ammette il punto e
        #    scarterebbe OGNI riga — un audit log vuoto, che non e' un errore e
        #    non si lamenta.
        self.assertIn(f"'{_CODE}' AS code", sql)
