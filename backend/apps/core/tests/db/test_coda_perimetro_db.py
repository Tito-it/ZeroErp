# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «MIO» nella coda lavori, in SQL, sul DB vero: un lavoro è di chi l'ha
#        accodato (`_espr_accodato_da` del repository) — l'identità dello scope
#        per un lavoro OPERATORE, l'attore del payload (`richiesto_da`) per un
#        lavoro SISTEMA di «Esegui ora». E l'SQL di ogni lettura del
#        repository che lo usa, eseguito davvero.
# Note: ⭐ BE9 di brief-db-revisione-dbops (decisione di Tid, 2026-11-07): il
#        PERIMETRO d'azienda lo fa la RLS di `dbops.coda_lavori` (blocco 5b;
#        il suo presidio è il pgTAP `rls/test-rls-coda-lavori-perimetro-v1`),
#        e il filtro per azienda del repository è ritirato. Questo file era il
#        presidio di quel filtro (fino al 2026-11-07); ora lo è di ciò che il
#        backend scrive ancora: «mio».
#        ⛔ I casi si COSTRUISCONO (righe in `VALUES`, con le colonne della
#        coda), non si cercano fra i lavori presenti: un test che itera sulla
#        coda passa a vuoto su un DB ricostruito, e non sa produrre il lavoro
#        SISTEMA con l'attore né la chiave non numerica.
#        ⛔ I test coi mock vedono i kwargs, non l'SQL: un confronto fra testo e
#        numero, o un `is_mio` scritto al contrario, lo vede solo PostgreSQL.
# ------------------------------------------------------------
"""Indice test (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_accodato_da_per_tipo_di_lavoro
     OPERATORE = l'identità dello scope; SISTEMA = `payload.richiesto_da`;
     nessuna delle due chiavi vale per l'altro tipo di lavoro.
2. test_chiave_non_numerica_non_rompe
     uno scope con un `auth_user_id` non numerico è «non mio», non un errore.
3. test_senza_chiamante_niente_e_mio
     `None` (uso di sistema) = FALSE su ogni riga.
4. test_letture_del_repository_eseguono
     elenco, dettaglio, stato, conteggi e riepilogo con «miei» e `is_mio`
     girano sul DB vero (l'SQL composto regge).
"""

from __future__ import annotations

from datetime import date
from unittest import TestCase

from django.db import connection

from apps.core.services.coda_lavori.repository import (
    CodaLavoriRepository,
    _espr_accodato_da,
)
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_IO = 42
_COLLEGA = 7

# Le righe della prova: (id, run_as, scope, payload) con i tipi della coda.
_RIGHE = """
    (VALUES
        (1, 'OPERATORE', '{"auth_user_id": 42}'::jsonb, '{}'::jsonb),
        (2, 'OPERATORE', '{"auth_user_id": 7}'::jsonb,  '{}'::jsonb),
        (3, 'SISTEMA',   NULL::jsonb,                   '{"richiesto_da": 42}'::jsonb),
        (4, 'SISTEMA',   NULL::jsonb,                   '{"richiesto_da": 7}'::jsonb),
        (5, 'SISTEMA',   NULL::jsonb,                   '{}'::jsonb),
        (6, 'OPERATORE', '{"auth_user_id": 7}'::jsonb,  '{"richiesto_da": 42}'::jsonb),
        (7, 'OPERATORE', '{"auth_user_id": "x"}'::jsonb, '{}'::jsonb)
    ) AS t(id, run_as, scope, payload)
"""


def _miei(auth_user_id: int | None) -> set[int]:
    sql, params = _espr_accodato_da(auth_user_id)
    with connection.cursor() as cur:
        cur.execute(f"SELECT id FROM {_RIGHE} WHERE {sql} ORDER BY id", params)
        return {int(r[0]) for r in cur.fetchall()}


class CodaAccodatoDaDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    # 1. ⭐ La regola per tipo di lavoro. La riga 6 (OPERATORE del collega con
    #    un `richiesto_da` mio nel payload) NON è mia: l'attore del payload
    #    vale solo per i SISTEMA.
    def test_accodato_da_per_tipo_di_lavoro(self) -> None:
        self.assertEqual(_miei(_IO), {1, 3})
        self.assertEqual(_miei(_COLLEGA), {2, 4, 6})

    # 2. Una chiave non numerica nel jsonb: «non mio», e l'elenco non cade.
    def test_chiave_non_numerica_non_rompe(self) -> None:
        self.assertNotIn(7, _miei(_IO))

    # 3. Nessun chiamante: niente è mio.
    def test_senza_chiamante_niente_e_mio(self) -> None:
        self.assertEqual(_miei(None), set())

    # 4. L'SQL di ogni lettura che usa la regola, eseguito davvero. ⚠️ Non si
    #    guarda QUANTE righe tornano: sotto la RLS, senza identità a database,
    #    sono zero, e non è un dato. Si guarda che l'SQL composto (frammento,
    #    parametri, ordine dei parametri) regga.
    def test_letture_del_repository_eseguono(self) -> None:
        repo = CodaLavoriRepository()
        esito = repo.elenca(accodati_da=_IO, chiamante=_IO, limit=5)
        self.assertIn("items", esito)
        repo.elenca(accodati_da=None, chiamante=None, limit=5)
        self.assertIsNone(repo.get_dettaglio(-1, accodati_da=_IO, chiamante=_IO))
        self.assertIsNone(repo.get_stato(-1, accodati_da=_IO))
        self.assertIsInstance(repo.count_per_stato(), dict)
        self.assertIsInstance(
            repo.summary_per_job_type(
                job_types=["FATTURAZIONE_GIRO"], competenza_mese=date(2026, 6, 1),
                chiamante=_IO,
            ),
            list,
        )
        self.assertFalse(repo.annulla(-1, accodati_da=_IO))
        self.assertFalse(repo.requeue(-1, accodati_da=_IO))
