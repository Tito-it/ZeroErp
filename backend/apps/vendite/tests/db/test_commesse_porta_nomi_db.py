# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I NOMI con cui il backend parla alla porta delle righe di commessa,
#        confrontati col DB vero: ogni `p_… =>` di `upsert_attivita` è un
#        parametro di `vendite.fn_upsert_commessa_attivita`, e ogni chiave che
#        `batch_upsert_attivita` mette in una riga è letta da
#        `vendite.fn_batch_upsert_commessa_attivita`.
# Note: ⛔ Sono i due punti di TRASPORTO del push, e un nome sbagliato si
#        comporta in due modi diversi: nella madre (argomenti per nome) è un
#        errore a runtime; nel batch è una chiave che nessuno legge, cioè un
#        NULL passato in silenzio. I test coi mock vedono il testo che il
#        backend scrive, non quello che il DB si aspetta: lo sa solo il
#        catalogo. Nato col giro K.1 di brief-db-sorgente-documento-e-riga
#        (2026-11-07), che ha rinominato `p_sorgente_uid` in
#        `p_sorgente_chiave` e la chiave del batch `sorgente_uid` in
#        `sorgente_chiave`.
# ------------------------------------------------------------
"""Indice test (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_parametri_della_madre
     ogni argomento per nome di `upsert_attivita` esiste nella firma.
2. test_chiavi_del_batch
     ogni chiave di una riga del batch è letta dal wrapper (`v_row ->> '…'`).
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import connection

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.commesse_repository import CommessaAttivitaInput, CommesseRepository

_MADRE = (
    "vendite.fn_upsert_commessa_attivita"
)
_BATCH = "vendite.fn_batch_upsert_commessa_attivita(jsonb)"

# Una riga qualsiasi: si guardano i NOMI, non i valori.
_INPUT = CommessaAttivitaInput(
    commessa_id=1, segment_key="K", quantita=Decimal("1"),
    competenza_mese=date(2026, 6, 1), articolo_id=None, prezzo_snapshot=None,
    sorgente_tipo_id=1, sorgente_chiave="1", sorgente_riga=1,
)


class CommessePortaNomiDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto(_BATCH)

    # 1. Gli argomenti per nome della chiamata alla madre, catturati dal
    #    repository vero con un cursore finto, contro `proargnames`.
    def test_parametri_della_madre(self) -> None:
        finto = MagicMock()
        cur = finto.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (1, True)
        with patch("apps.vendite.db.commesse_repository.connection", finto):
            CommesseRepository().upsert_attivita(_INPUT)
        sql = cur.execute.call_args[0][0]
        inviati = set(re.findall(r"\b(p_[a-z0-9_]+)\s*=>", sql))
        self.assertIn("p_sorgente_chiave", inviati)

        with connection.cursor() as c:
            c.execute(
                "SELECT DISTINCT unnest(p.proargnames) FROM pg_proc p"
                " WHERE p.oid = %s::regproc",
                [_MADRE],
            )
            firma = {r[0] for r in c.fetchall()}
        self.assertTrue(firma, "firma della madre vuota: il catalogo non risponde")
        self.assertEqual(inviati - firma, set(), "argomenti che la madre non ha")

    # 2. Le chiavi di una riga del batch contro le chiavi che il corpo del
    #    wrapper legge. ⛔ Una chiave inviata e non letta è il difetto che non
    #    dà errore. (Il contrario, una chiave letta e non inviata, è un default
    #    della madre, ed è ammesso.)
    def test_chiavi_del_batch(self) -> None:
        inviate = set(CommesseRepository()._inp_to_jsonb_row(_INPUT))
        self.assertIn("sorgente_chiave", inviate)

        with connection.cursor() as c:
            c.execute("SELECT pg_get_functiondef(%s::regprocedure)", [_BATCH])
            corpo = c.fetchone()[0]
        lette = set(re.findall(r"v_row\s*->>?\s*'([a-z0-9_]+)'", corpo))
        self.assertTrue(lette, "nessuna chiave letta: il corpo ha cambiato forma")
        self.assertEqual(inviate - lette, set(), "chiavi che il batch non legge")
