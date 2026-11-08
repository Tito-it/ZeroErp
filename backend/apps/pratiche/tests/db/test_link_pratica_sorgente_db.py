# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il LINK documento → pratica (`pratiche.pratiche_sorgenti`) sul DB
#        vero: chi lo scrive (`PraticheRepository.upsert_pratica_sorgente`) e
#        chi lo legge (il reverse per sorgente, i lettori del preventivo ROOT e
#        dell'ordine COLLEGATO, la LATERAL per-flusso del percorso).
# Note: ⭐ Giro P.1 di brief-db-sorgente-documento-e-riga (2026-11-08): la
#        chiave del documento sta in `sorgente_id` (ordine, commessa) oppure in
#        `sorgente_uid uuid` (preventivo), mai tutte e due; la sceglie il BB DB
#        `script.fn_sorgente_provenienza`. I due rami si COSTRUISCONO qui: un
#        preventivo (uid) e un ordine (id), ciascuno citato sia con l'id sia
#        con l'uid.
#        ⛔ I test coi mock vedono il nome del parametro, non se la colonna
#        esiste, se il cast regge o se l'ON CONFLICT trova il suo vincolo: lo
#        sa solo PostgreSQL (BE-P.1-a … -c del §8.16).
# ------------------------------------------------------------
"""Indice test (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_preventivo_root_a_chiave_uid
     il ROOT del preventivo sta in `sorgente_uid`; riscritto dall'id è lo
     stesso link (ON CONFLICT); i lettori del preventivo lo trovano.
2. test_ordine_collegato_a_chiave_id
     il COLLEGATO dell'ordine sta in `sorgente_id`; il reverse lo trova
     dall'id e dall'uid; `get_ordine_id_by_pratica` dà l'ordine.
3. test_codice_che_non_e_un_tipo
     un codice fuori catalogo è `E_SORG_CONF` dal BB, non un link muto.
4. test_percorso_esegue
     la LATERAL per-flusso del percorso legge le colonne native e regge.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.config.sorgenti import SORGENTE_ORDINE_VENDITA, SORGENTE_PREVENTIVO
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.pratiche.db.pratiche_repository import PraticheRepository
from apps.pratiche.types import RUOLO_LINK_COLLEGATO, RUOLO_LINK_ROOT
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository


_TIPO_PRESTAZIONE = "PREVENTIVI"


class LinkPraticaSorgenteDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("script.fn_sorgente_provenienza(character varying,text)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = PraticheRepository()
        with connection.cursor() as cur:
            cur.execute(
                "SELECT preventivo_id, preventivo_uid::text"
                "  FROM dbops.fn_pgtap_crea_preventivo('link pratica preventivo')"
            )
            self.preventivo_id, self.preventivo_uid = cur.fetchone()
            # Il tipo PER CODICE, quello del percorso pratica dei preventivi
            # (seed `pratiche/tipi_prestazione.csv`), mai «il primo per id».
            cur.execute(
                "SELECT id FROM pratiche.tipi_prestazione"
                " WHERE codice = %s AND attivo",
                [_TIPO_PRESTAZIONE],
            )
            tipo_prestazione = cur.fetchone()
        self.assertIsNotNone(tipo_prestazione, f"tipo di prestazione {_TIPO_PRESTAZIONE} assente")
        # La pratica nasce dal verbo DB, che scrive il ROOT del preventivo.
        self.pratica_id = PreventiviRepository().genera_pratica_da_preventivo(
            preventivo_id=self.preventivo_id,
            tipo_prestazione_id=int(tipo_prestazione[0]),
        )

    # Scopo: i link della pratica per tipo, con le due chiavi come stanno.
    def _link(self, codice: str) -> list[tuple[int | None, str | None, str]]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ps.sorgente_id, ps.sorgente_uid::text, ps.ruolo_link"
                "  FROM pratiche.pratiche_sorgenti ps"
                "  JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id"
                " WHERE ps.pratica_id = %s AND s.codice_interno = %s"
                " ORDER BY ps.id",
                [self.pratica_id, codice],
            )
            return [tuple(r) for r in cur.fetchall()]

    # 1. Il preventivo: chiave uid.
    def test_preventivo_root_a_chiave_uid(self) -> None:
        atteso = [(None, self.preventivo_uid, RUOLO_LINK_ROOT)]
        self.assertEqual(self._link(SORGENTE_PREVENTIVO), atteso)
        # Riscritto dall'uid e dall'id: la stessa coppia, lo stesso link.
        for chiave in (self.preventivo_uid, str(self.preventivo_id)):
            self.repo.upsert_pratica_sorgente(
                pratica_id=self.pratica_id, sorgente_codice=SORGENTE_PREVENTIVO,
                sorgente_chiave=chiave, ruolo_link=RUOLO_LINK_ROOT,
            )
        self.assertEqual(self._link(SORGENTE_PREVENTIVO), atteso)

        prev_repo = PreventiviRepository()
        self.assertEqual(
            prev_repo.get_pratica_id_by_preventivo_root(self.preventivo_id), self.pratica_id,
        )
        self.assertEqual(
            prev_repo.get_preventivo_id_by_pratica_root(self.pratica_id), self.preventivo_id,
        )
        # Senza flusso il reverse per-flusso non trova niente, ma esegue.
        self.assertIsNone(prev_repo.get_flusso_id_by_preventivo_root(self.preventivo_id))
        self.assertEqual(
            self.repo.get_pratica_id_by_sorgente(
                sorgente_codice=SORGENTE_PREVENTIVO, sorgente_chiave=str(self.preventivo_id),
            ),
            self.pratica_id,
        )

    # 2. L'ordine: chiave id.
    def test_ordine_collegato_a_chiave_id(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ordine_id, ordine_uid::text"
                "  FROM dbops.fn_pgtap_crea_ordine('link pratica ordine')"
            )
            ordine_id, ordine_uid = cur.fetchone()
        self.repo.upsert_pratica_sorgente(
            pratica_id=self.pratica_id, sorgente_codice=SORGENTE_ORDINE_VENDITA,
            sorgente_chiave=str(ordine_id), ruolo_link=RUOLO_LINK_COLLEGATO,
        )
        self.assertEqual(
            self._link(SORGENTE_ORDINE_VENDITA), [(int(ordine_id), None, RUOLO_LINK_COLLEGATO)],
        )
        for chiave in (str(ordine_id), ordine_uid):
            self.assertEqual(
                self.repo.get_pratica_id_by_sorgente(
                    sorgente_codice=SORGENTE_ORDINE_VENDITA, sorgente_chiave=chiave,
                    ruolo_link=RUOLO_LINK_COLLEGATO,
                ),
                self.pratica_id,
            )
        # Il ruolo filtra: l'ordine non è ROOT.
        self.assertIsNone(
            self.repo.get_pratica_id_by_sorgente(
                sorgente_codice=SORGENTE_ORDINE_VENDITA, sorgente_chiave=str(ordine_id),
                ruolo_link=RUOLO_LINK_ROOT,
            ),
        )
        self.assertEqual(
            OrdiniRepository().get_ordine_id_by_pratica(self.pratica_id), int(ordine_id),
        )

    # 3. Un codice che non è un tipo: lo ferma il BB, con il suo codice.
    def test_codice_che_non_e_un_tipo(self) -> None:
        # Savepoint: l'errore del DB non deve abortire la transazione del test.
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self.repo.upsert_pratica_sorgente(
                pratica_id=self.pratica_id, sorgente_codice="NON_UN_TIPO",
                sorgente_chiave=self.preventivo_uid,
            )
        self.assertIn("E_SORG_CONF", str(ctx.exception))
        # Nessun link muto: la pratica ha ancora il solo ROOT del preventivo.
        self.assertEqual(self._link(SORGENTE_PREVENTIVO), [(None, self.preventivo_uid, RUOLO_LINK_ROOT)])

    # 4. Il percorso: la LATERAL per-flusso, eseguita davvero.
    def test_percorso_esegue(self) -> None:
        self.assertIsInstance(self.repo.get_percorso_pratica(self.pratica_id), list)
