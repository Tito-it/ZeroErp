# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL PASSO B-6 — `error_policies_generated.py` non deve divergere dal
#        catalogo. E' il terzo mestiere di questa famiglia di presidi: prima si
#        controllava che ogni codice del DB avesse una policy scritta a mano
#        (`test_error_codes_db_policy_guardrail`), ora che il file GENERATO sia
#        quello che il database produrrebbe adesso.
#
#        COSA PRESIDIA DAVVERO, ed e' piu' stretto di «le classi coincidono»:
#        confronta il TESTO INTERO, quindi vede anche una `note` cambiata, un
#        codice ritirato, un riordino. Un file generato che nessuno rigenera e'
#        un file che torna a essere scritto a mano senza che nessuno lo decida.
#
#        ⚠️ NON SOSTITUISCE il cancello del terzo lato, e i due non misurano la
#        stessa cosa. Quello confronta i codici che le FUNZIONI VIVE possono
#        nominare col registro; questo confronta il registro col CATALOGO. Un
#        codice sollevato da una funzione e mai messo a catalogo passerebbe qui e
#        verrebbe preso di la'. Il piano diceva «cambia mestiere»: sono due
#        mestieri, e servono entrambi.
#
#        ⚠️ RICHIEDE IL DB VERO, stessa opt-in dei tre e2e e del cancello del
#        terzo lato (`ZEROERP_TEST_DB_E2E=1`, accesa in CI da `ci-validate.yaml`).
#        Sola lettura: interroga una vista.
# ------------------------------------------------------------

"""Indice test previsti (opt-in `ZEROERP_TEST_DB_E2E=1`).

 1) test_il_file_generato_e_allineato_al_catalogo
       il testo del modulo committato == quello reso dalla vista, ora.
 2) test_la_vista_di_identita_ha_una_riga_per_codice
       la sorgente e' quella giusta: `vw_codici_errore_identita`, non la vista di
       revisione che ha una riga per (codice, lingua).
"""

from __future__ import annotations

import difflib
from unittest import TestCase

from apps.core.management.commands.genera_error_policies import (
    DESTINAZIONE,
    leggi_identita,
    rendi_modulo,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto

_VISTA = "config.vw_codici_errore_identita"


class ErrorPoliciesDivergenzaDb(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

        from django.db import connection

        with connection.cursor() as cur:
            # Schema presente ma vista assente = il D-9 non e' stato applicato:
            # e' un difetto, non una condizione d'ambiente. Si fallisce.
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", [_VISTA])
            row = cur.fetchone()
            assert row is not None
            if not row[0]:
                raise AssertionError(
                    f"schema Liquibase presente ma {_VISTA} no: applicare il "
                    "changeSet 20260807-16 (piano DB, D-9)."
                )

    # Scopo: il file committato e' quello che il generatore produrrebbe adesso.
    #        ⚠️ Il confronto e' sul testo, non sui dizionari: un file generato si
    #        rilegge nei diff, e un diff che non corrisponde al database e' il
    #        primo passo verso un file che nessuno rilegge piu'.
    def test_il_file_generato_e_allineato_al_catalogo(self):
        atteso = rendi_modulo(leggi_identita())
        attuale = DESTINAZIONE.read_text(encoding="utf-8")
        if atteso == attuale:
            return
        differenze = list(
            difflib.unified_diff(
                attuale.splitlines(),
                atteso.splitlines(),
                fromfile="error_policies_generated.py (nel repo)",
                tofile=f"{_VISTA} (nel database)",
                lineterm="",
                n=1,
            )
        )
        # Un diff di 700 righe in un messaggio di test non lo legge nessuno.
        estratto = "\n".join(differenze[:40])
        self.fail(
            f"error_policies_generated.py diverge dal catalogo "
            f"({len(differenze)} righe di differenza). Prime righe:\n{estratto}\n\n"
            "Rigenerare con `manage.py genera_error_policies` e committare. "
            "Se la divergenza non era attesa, guardare PRIMA cosa e' cambiato a "
            "catalogo: una classe che si muove cambia lo status di una risposta."
        )

    # Scopo: la sorgente giusta e' quella di IDENTITA'. La vista di revisione ha
    #        una riga per (codice, lingua) e, essendo un LEFT JOIN, un codice
    #        senza messaggio ci compare con `lingua IS NULL`: filtrarla per
    #        lingua perderebbe proprio quei codici, in silenzio. Il test tiene
    #        ferma la distinzione, che e' l'unica cosa che separa le due viste.
    def test_la_vista_di_identita_ha_una_riga_per_codice(self):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(f"SELECT count(*), count(DISTINCT codice) FROM {_VISTA}")
            row = cur.fetchone()
        assert row is not None
        righe, distinti = row
        self.assertGreater(distinti, 600, f"{_VISTA} sospetta: la misura sembra degradata")
        self.assertEqual(
            righe, distinti, f"{_VISTA} ha piu' di una riga per codice: sorgente sbagliata"
        )
