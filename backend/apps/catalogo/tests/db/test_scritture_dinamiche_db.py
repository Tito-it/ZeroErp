# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LE SCRITTURE DINAMICHE del catalogo sul DATABASE VERO, dopo la
#        migrazione ai BB core `execute_dynamic_insert`/`execute_dynamic_update`/
#        `sql_set_clause` (2026-09-26) — e il rifiuto delle chiavi fuori lista.
#
# 🔴 PERCHE' SUL DB VERO. I test del service mockano il repository: vedono che
#    il service CHIAMA `create_articolo`, non che l'INSERT composto dal BB si
#    leghi davvero alle colonne (nomi, `::jsonb`, UUID/Decimal/date come
#    parametri). Una rinomina o un cast sbagliato qui sono un 500 che nessun
#    mock vede.
#
# ⭐ Il mondo si COSTRUISCE (regola zero): azienda e operatore da
#    `fn_pgtap_crea_emittente_operatore`, il contesto, gli articoli da
#    `fn_pgtap_crea_articolo` o dal repository stesso. Unica lettura dal seed:
#    uno stile nota attivo (`config.note_stili`, FK NOT NULL della nota) — e'
#    configurazione di sistema, come la UoM che sceglie la fixture articolo.
#    Tutto in transazione ANNULLATA.
#
# ⛔ IL RIFIUTO (classe senza DB). Una chiave fuori whitelist in una scrittura
#    e' `RuntimeError` PRIMA di toccare il database: fino al 2026-09-26 veniva
#    SCARTATA in silenzio — un salvataggio che «riesce» senza aver scritto il
#    campo. Il 400 educato lo da' il service (test 57 in test_catalogo_service).
# ------------------------------------------------------------
"""
Indice test eseguiti:
Rifiuto (senza DB):
1) RifiutoChiaviFuoriListaTests.test_ogni_scrittura_rifiuta_la_chiave_estranea
Opt-in `ZEROERP_TEST_DB_E2E=1`:
2) ScrittureDinamicheCatalogoDbTests.test_articolo_create_e_update
   meta dict -> oggetto jsonb (non uno scalare stringa), stringhe strippate,
   None -> NULL, payload vuoto in update -> False senza SQL.
3) ScrittureDinamicheCatalogoDbTests.test_componente_bom_create
   padre dal path, UUID/Decimal/date come parametri.
4) ScrittureDinamicheCatalogoDbTests.test_nota_articolo_create_e_update
   partizione e padre dal repository, meta jsonb.
5) ScrittureDinamicheCatalogoDbTests.test_uom_operativa_update
   SET su riga seminata dal trigger (UoM base), ownership nel WHERE.
6) ScrittureDinamicheCatalogoDbTests.test_uom_tipo_unita_conversione_update
   le tre UPDATE che erano SET da tuple letterali.
"""
from __future__ import annotations

import json
import unittest
from datetime import date
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.catalogo.db.catalogo_bom_repository import CatalogoBomRepository
from apps.catalogo.db.catalogo_repository import CatalogoRepository
from apps.catalogo.db.catalogo_uom_repository import CatalogoUomRepository
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)


# Scopo: costruisce il mondo (azienda, operatore, contesto) sul cursore.
def _apri_mondo(cur) -> None:
    for passo in _FIXTURE:
        cur.execute(passo)


# Scopo: una riga come dict, per le verifiche.
def _riga(cur, sql: str, params: list) -> dict:
    cur.execute(sql, params)
    colonne = [c[0] for c in cur.description]
    valori = cur.fetchone()
    assert valori is not None, f"nessuna riga: {sql}"
    return dict(zip(colonne, valori, strict=True))


# Scopo: jsonb letto dal driver (dict, o testo se il driver non decodifica).
def _json(valore):
    return json.loads(valore) if isinstance(valore, str) else valore


class RifiutoChiaviFuoriListaTests(unittest.TestCase):
    """⛔ Una chiave fuori whitelist e' `RuntimeError`, mai uno scarto."""

    # 1. Ogni scrittura dinamica del catalogo: il BB verifica le colonne
    #    PRIMA di aprire il cursore, quindi il test non tocca il DB.
    def test_ogni_scrittura_rifiuta_la_chiave_estranea(self):
        repo, bom, uom = CatalogoRepository(), CatalogoBomRepository(), CatalogoUomRepository()
        casi = (
            ("create_articolo", lambda: repo.create_articolo({"codice": "X", "estranea": 1})),
            ("update_articolo", lambda: repo.update_articolo("a", {"descrizione": "x", "codice": "Y"})),
            ("update_uom_tipo", lambda: repo.update_uom_tipo(1, {"descrizione": "x", "codice": "Y"})),
            ("update_unita_misura", lambda: repo.update_unita_misura(1, {"codice": "Y"})),
            ("update_conversione", lambda: repo.update_conversione(1, {"uom_from_id": 2})),
            ("create_componente", lambda: bom.create_componente("a", {"coeff_qta": 1, "estranea": 1})),
            ("create_nota", lambda: bom.create_nota("ARTICOLO", "a", {"testo": "t", "estranea": 1})),
            ("update_nota", lambda: bom.update_nota(1, "ARTICOLO", {"target_id": "b"})),
            ("create_uom_operativa", lambda: uom.create_uom_operativa("a", {"uom_id": 1, "estranea": 1})),
            ("update_uom_operativa", lambda: uom.update_uom_operativa("a", 1, {"articolo_id": "b"})),
        )
        for nome, chiama in casi:
            with self.subTest(nome), self.assertRaises(RuntimeError) as ctx:
                chiama()
            self.assertIn("colonne non ammesse", str(ctx.exception), nome)


class ScrittureDinamicheCatalogoDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_articolo(character varying,boolean,boolean,boolean,bigint,smallint,boolean,boolean,bigint,bigint)")

    # 2. Articolo: INSERT e UPDATE dal BB, con jsonb, strip e NULL.
    def test_articolo_create_e_update(self):
        repo = CatalogoRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _apri_mondo(cur)
                cur.execute("SELECT id FROM catalogo.unita_misura WHERE attivo ORDER BY id LIMIT 1")
                uom = cur.fetchone()[0]

                art = repo.create_articolo({
                    "codice": "SCRDYN-A1",
                    "descrizione": "  Articolo scritture  ",
                    "descrizione_breve": None,
                    "uom_id": uom,
                    "lead_time_giorni": 3,
                    "meta": {"origine": "test", "tag": [1, 2]},
                })
                riga = _riga(cur, """
                    SELECT descrizione, descrizione_breve, lead_time_giorni,
                           meta, jsonb_typeof(meta) AS tipo_meta
                    FROM catalogo.articoli WHERE id = %s
                """, [art])
                self.assertEqual(riga["descrizione"], "Articolo scritture")
                self.assertIsNone(riga["descrizione_breve"])
                self.assertEqual(riga["lead_time_giorni"], 3)
                # ⭐ Un dict e' un OGGETTO jsonb, non la sua stringa.
                self.assertEqual(riga["tipo_meta"], "object")
                self.assertEqual(_json(riga["meta"]), {"origine": "test", "tag": [1, 2]})

                self.assertTrue(repo.update_articolo(art, {
                    "descrizione_breve": "Breve",
                    "lead_time_giorni": None,
                    "meta": {"v": 2},
                }))
                riga = _riga(cur, """
                    SELECT descrizione_breve, lead_time_giorni, meta
                    FROM catalogo.articoli WHERE id = %s
                """, [art])
                self.assertEqual(riga["descrizione_breve"], "Breve")
                # None in PATCH AZZERA (nessun skip_none): come prima.
                self.assertIsNone(riga["lead_time_giorni"])
                self.assertEqual(_json(riga["meta"]), {"v": 2})

                self.assertFalse(repo.update_articolo(art, {}))
                raise Annulla
        except Annulla:
            pass

    # 3. Componente BoM: il padre dal path.
    def test_componente_bom_create(self):
        repo, bom = CatalogoRepository(), CatalogoBomRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _apri_mondo(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_articolo('SCRDYN-PADRE', false)")
                padre = cur.fetchone()[0]
                repo.update_articolo(padre, {"is_composito": True})
                cur.execute("SELECT dbops.fn_pgtap_crea_articolo('SCRDYN-FIGLIO', false)")
                figlio = cur.fetchone()[0]

                riga_id = bom.create_componente(padre, {
                    "componente_id": figlio,
                    "coeff_qta": Decimal("2.5"),
                    "valido_dal": oggi_aziendale(),
                    "meta": {"k": "v"},
                })
                riga = _riga(cur, """
                    SELECT prodotto_id, componente_id, coeff_qta, jsonb_typeof(meta) AS tipo_meta
                    FROM catalogo.articoli_componenti WHERE id = %s
                """, [riga_id])
                self.assertEqual(riga["prodotto_id"], padre)
                self.assertEqual(riga["componente_id"], figlio)
                self.assertEqual(riga["coeff_qta"], Decimal("2.5"))
                self.assertEqual(riga["tipo_meta"], "object")

                # ⛔ Nessun UPDATE: dal 2026-11-10 un legame non si aggiorna
                #    dal repository (la fine passa dal verbo, provata in
                #    `test_chiusura_legame_prezzi_db`).
                raise Annulla
        except Annulla:
            pass

    # 4. Nota articolo: partizione e padre dal repository.
    def test_nota_articolo_create_e_update(self):
        bom = CatalogoBomRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _apri_mondo(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_articolo('SCRDYN-NOTA', false)")
                art = cur.fetchone()[0]
                cur.execute("SELECT id FROM config.note_stili ORDER BY id LIMIT 1")
                stile = cur.fetchone()
                self.assertIsNotNone(stile, "config.note_stili vuota: e' un seed")

                nota_id = bom.create_nota("ARTICOLO", art, {
                    "anchor_tipo": "DOCUMENTO",
                    "posizione": "HEADER",
                    "testo": "Nota di prova",
                    "id_stile": stile[0],
                    "meta": {"n": 1},
                })
                riga = _riga(cur, """
                    SELECT target_tipo, target_id, testo, jsonb_typeof(meta) AS tipo_meta
                    FROM catalogo.note WHERE target_tipo = 'ARTICOLO' AND id = %s
                """, [nota_id])
                self.assertEqual(riga["target_tipo"], "ARTICOLO")
                self.assertEqual(str(riga["target_id"]), str(art))
                self.assertEqual(riga["tipo_meta"], "object")

                self.assertTrue(bom.update_nota(nota_id, "ARTICOLO", {"testo": "Aggiornata", "seq": 2}))
                self.assertFalse(bom.update_nota(nota_id, "ARTICOLO_COMPONENTE", {"testo": "no"}))
                riga = _riga(cur, "SELECT testo, seq FROM catalogo.note WHERE target_tipo = 'ARTICOLO' AND id = %s", [nota_id])
                self.assertEqual((riga["testo"], riga["seq"]), ("Aggiornata", 2))
                raise Annulla
        except Annulla:
            pass

    # 5. UoM operativa: SET sulla riga base che il trigger ha seminato.
    def test_uom_operativa_update(self):
        uom = CatalogoUomRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _apri_mondo(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_articolo('SCRDYN-UOM', false)")
                art = cur.fetchone()[0]
                cur.execute(
                    "SELECT id FROM catalogo.articoli_uom_operativa WHERE articolo_id = %s AND is_base",
                    [art],
                )
                base = cur.fetchone()
                self.assertIsNotNone(base, "il trigger seed della UoM base non ha seminato")

                self.assertTrue(uom.update_uom_operativa(art, base[0], {"gtin": " 8001234567895 ", "meta": {"g": True}}))
                riga = _riga(cur, """
                    SELECT gtin, jsonb_typeof(meta) AS tipo_meta
                    FROM catalogo.articoli_uom_operativa WHERE id = %s
                """, [base[0]])
                self.assertEqual(riga["gtin"], "8001234567895")
                self.assertEqual(riga["tipo_meta"], "object")
                self.assertFalse(uom.update_uom_operativa(art, base[0], {}))
                raise Annulla
        except Annulla:
            pass

    # 6. Le tre UPDATE che erano SET da tuple letterali (uom_tipi,
    #    unita_misura, conversioni): mondo costruito dai metodi create.
    def test_uom_tipo_unita_conversione_update(self):
        repo = CatalogoRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _apri_mondo(cur)
                tipo = repo.create_uom_tipo({
                    "codice": "SCRDYN-T", "codice_interno": "SCRDYN_T", "descrizione": "Tipo prova",
                })
                self.assertTrue(repo.update_uom_tipo(tipo, {"descrizione": "Tipo aggiornato"}))
                self.assertEqual(repo.get_uom_tipo(tipo)["descrizione"], "Tipo aggiornato")

                u1 = repo.create_unita_misura({"codice": "SCRDYN-U1", "descrizione": "U1", "tipo_uom_id": tipo})
                u2 = repo.create_unita_misura({"codice": "SCRDYN-U2", "descrizione": "U2", "tipo_uom_id": tipo})
                self.assertTrue(repo.update_unita_misura(u1, {"descrizione_fattura": "Fatt", "descrizione": "U1 bis"}))
                riga = repo.get_unita_misura(u1)
                self.assertEqual((riga["descrizione"], riga["descrizione_fattura"]), ("U1 bis", "Fatt"))

                conv = repo.create_conversione({
                    "uom_from_id": u1, "uom_to_id": u2, "fattore": Decimal("10"),
                    "valido_dal": date(2026, 1, 1),
                })
                self.assertTrue(repo.update_conversione(conv, {
                    "fattore": Decimal("12"), "valido_al": date(2026, 12, 31),
                }))
                riga = repo.get_conversione(conv)
                self.assertEqual(riga["fattore"], Decimal("12"))
                self.assertEqual(riga["valido_al"], date(2026, 12, 31))
                self.assertFalse(repo.update_conversione(conv, {}))
                raise Annulla
        except Annulla:
            pass
