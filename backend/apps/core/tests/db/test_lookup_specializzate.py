# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `_LOOKUP_SPECIALIZZATE` — il lookup generico con UNA colonna in piu'.
#        Due meta': la COMPOSIZIONE della query con cursore mockato (il flag
#        `has_attivo`, che decide se `t.attivo` entra nell'SQL) e UNA lettura
#        vera di OGNI relazione dichiarata, sul DB provvisto — il contratto
#        dichiarato si prova per intero (`feedback_contratto_dichiarato_
#        provalo_intero`): fino al 2026-09-19 nessun test attraversava le
#        specializzate sul database, e la prima senza `attivo`
#        (`config.registri_giornale`) sarebbe stata un 500 con la rel in
#        whitelist.
#
# Indice test:
#   1. `has_attivo` assente = True: `t.attivo` in proiezione e nel predicato
#   2. `has_attivo: False`: `NULL::boolean AS attivo`, nessun predicato su
#      `attivo`, e `attivo_only=True` (il DEFAULT dell'API) non filtra niente
#   3. [DB vero] ogni rel specializzata e' anche nel lookup della lista a DB
#      (`config.tabelle_gestibili.lookup`): fuori lista non si raggiunge, e
#      sarebbe una riga di config morta
#   4. [DB vero] ogni rel specializzata risponde: la colonna extra c'e', il
#      contratto generico e' intero, e su `config.registri_giornale`
#      `etichetta_key` e' nel namespace del catalogo e `attivo` e' NULL
# ------------------------------------------------------------
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import transaction
from django.test import SimpleTestCase

from apps.core.db.dbops_repository import (
    _LOOKUP_SPECIALIZZATE,
    DbopsRepository,
)
from apps.core.db.tabelle_gestibili_repository import TabelleGestibiliRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto

# ⚠️ La query parte dal BB `fetch_paged_with_total` (F-8, 2026-09-28): e' la
#    `connection` di `_helpers` quella da fingere, non quella del repository.
_CONN = "apps.core.db._helpers.connection"
# La lista delle rel ammesse sta a DB: nei test di composizione dell'SQL si
# ammette tutto, il controllo vero lo prova il test 3.
_AMMESSA = "apps.core.db.dbops_repository._richiedi_rel_lookup"
_CONTRATTO = {"id", "codice", "codice_interno", "descrizione", "attivo", "codice_stabile"}


def _cursore_vuoto(conn: MagicMock) -> MagicMock:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchall.return_value = []
    conn.cursor.return_value = cursor
    return cursor


def _leggi(rel: str, **kw) -> tuple[list[dict], int]:
    return DbopsRepository().list_lookup_codici(rel=rel, **kw)


@patch(_AMMESSA)
class LookupSpecializzateComposizioneTests(SimpleTestCase):
    # 1. Senza il flag la tabella ha `attivo`: proiezione e predicato come sempre.
    @patch(_CONN)
    def test_senza_flag_attivo_entra_nell_sql(self, conn, _ammessa) -> None:
        cursor = _cursore_vuoto(conn)
        _leggi("catalogo.unita_misura", attivo_only=True)
        sql = cursor.execute.call_args.args[0]
        self.assertIn("t.attivo AS attivo,", sql)
        self.assertIn("OR t.attivo = true", sql)

    # 2. Col flag a False `attivo` non esiste: NULL in proiezione, niente
    #    predicato — e il default `attivo_only=True` non deve svuotare la lista.
    @patch(_CONN)
    def test_has_attivo_false_non_nomina_la_colonna(self, conn, _ammessa) -> None:
        cursor = _cursore_vuoto(conn)
        _leggi("config.registri_giornale", attivo_only=True, includi_obsoleti=False)
        sql, params = cursor.execute.call_args.args
        self.assertIn("NULL::boolean AS attivo", sql)
        self.assertNotIn("t.attivo", sql)
        self.assertIn("t.etichetta_key AS etichetta_key", sql)
        self.assertIn("t.obsoleto_dal", sql)
        self.assertIn("t.codice_interno ILIKE", sql)
        self.assertFalse(params["includi_obsoleti"])



class LookupSpecializzateDbTests(TestCase):
    """Ogni rel dichiarata risponde sul database vero."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 3. Una specializzata si raggiunge solo dalla lista a DB.
    def test_ogni_specializzata_e_nella_lista(self) -> None:
        fuori = sorted(set(_LOOKUP_SPECIALIZZATE) - TabelleGestibiliRepository().rel_lookup())
        self.assertEqual(fuori, [], f"specializzate non raggiungibili: {fuori}")

    # 4. Il contratto si attraversa per intero: ogni rel, coi default dell'API
    #    (`attivo_only=True`, `includi_obsoleti=True`) e con la ricerca.
    def test_ogni_rel_specializzata_risponde(self) -> None:
        with transaction.atomic():
            for rel, spec in sorted(_LOOKUP_SPECIALIZZATE.items()):
                righe, totale = _leggi(rel, limit=5)
                self.assertIsInstance(totale, int, rel)
                _leggi(rel, search="a", includi_obsoleti=False, limit=1)
                for riga in righe:
                    self.assertEqual(set(riga), _CONTRATTO | {spec["extra_col"]}, rel)
            # Il catalogo dei registri: seminato, con l'indirizzo i18n del DB.
            righe, totale = _leggi("config.registri_giornale", limit=50)
            transaction.set_rollback(True)
        self.assertGreater(totale, 0, "config.registri_giornale vuota: il seed 20260919-09 manca")
        for riga in righe:
            self.assertIsNone(riga["attivo"])
            self.assertEqual(
                riga["etichetta_key"],
                f"config.registri_giornale.{riga['codice_interno'].lower()}",
            )
