# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le scritture dinamiche di `DocumentiRepository` sul DATABASE VERO,
#        dopo la migrazione sui BB `execute_dynamic_insert` /
#        `execute_dynamic_update` (2026-09-26): testata template, versione
#        (col suo clone), asset, documento generato + file + evento.
# Note: ⭐ Prova la GIUNTURA con psycopg, che i mock non vedono: fino al
#       2026-09-26 `meta` (dict) arrivava nudo al cursor di create/update
#       template e asset — psycopg non adatta un dict, quindi ogni scrittura
#       con `meta` era un 500, e i test col cursor mockato erano verdi.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, poi il contesto. Tipi output,
#       sorgenti, tipi asset/file e motori di render sono seed (`80_data`):
#       contratto, non popolazione. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ScrittureDinamicheDocumentiDbTests.test_template_create_update_con_meta
   create/update della testata con `meta` dict: la riga porta il jsonb, le
   stringhe arrivano strippate.
2) ScrittureDinamicheDocumentiDbTests.test_asset_create_update_con_meta
   create/update metadati asset con `meta` dict.
3) ScrittureDinamicheDocumentiDbTests.test_documento_generato_file_evento
   INSERT documento generato (RETURNING id, uid), file ed evento: i jsonb
   (`context_json`, `detail`, `meta`) sono oggetti, non scalari stringa.
4) ScrittureDinamicheDocumentiDbTests.test_versione_create_update_clone
   create/update versione con `meta`/`context_schema` dict (500 fino al
   2026-09-26) e corpo del template con spazi ai bordi CONSERVATI; poi il
   clone del service, che ripassa il jsonb letto dal DB come testo JSON.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

# ⭐ Il mondo è un PREVENTIVO vero (giro D.1 di brief-db-sorgente-documento-e-riga,
#    2026-11-07): una stampa cita un documento che esiste, e il guard unico
#    rifiuta una chiave inventata. Il preventivo porta azienda e operatore.
_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT p.preventivo_id, p.preventivo_uid, p.emittente_fiscale_id, p.auth_user_id,
           (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')
               AS sorgente_tipo_id
      FROM dbops.fn_pgtap_crea_preventivo('scritture dinamiche documenti') p
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)


class ScrittureDinamicheDocumentiDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto()

    # Scopo: costruisce il mondo e una testata template via repository;
    #        torna (repo, emittente, template_id).
    def _template(self, cur):
        from apps.documenti.db.documenti_repository import DocumentiRepository

        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT emittente_fiscale_id FROM _mondo")
        emittente = cur.fetchone()[0]
        cur.execute("SELECT id FROM documenti.tipi_documento_output ORDER BY id LIMIT 1")
        tipo_output = cur.fetchone()[0]
        cur.execute("SELECT sorgente_tipo_id FROM _mondo")
        sorgente = cur.fetchone()[0]
        repo = DocumentiRepository()
        template_id = repo.create_template({
            "tipo_documento_output_id": tipo_output,
            "sorgente_tipo_id": sorgente,
            "emittente_fiscale_id": emittente,
            "codice": "  SCRDINTPL  ",
            "codice_interno": "SCRDINTPL",
            "descrizione": "Template scritture dinamiche",
            "context_builder_code": "scritture",
            "is_default": False,
            "attivo": True,
            "meta": {"origine": "test", "n": 1},
        })
        return repo, emittente, template_id

    # Scopo: l'uid del preventivo del mondo, la chiave della sua stampa.
    def _preventivo_uid(self, cur) -> str:
        cur.execute("SELECT preventivo_uid::text FROM _mondo")
        return cur.fetchone()[0]

    # 1. Testata template: create + update con `meta` dict.
    def test_template_create_update_con_meta(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                repo, _, template_id = self._template(cur)
                cur.execute(
                    "SELECT codice, meta = %s::jsonb FROM documenti.template_documenti WHERE id = %s",
                    ['{"origine": "test", "n": 1}', template_id],
                )
                self.assertEqual(cur.fetchone(), ("SCRDINTPL", True))

                self.assertTrue(repo.update_template(
                    template_id, {"descrizione": "Aggiornata", "meta": {"n": 2}},
                ))
                cur.execute(
                    "SELECT descrizione, meta = '{\"n\": 2}'::jsonb "
                    "FROM documenti.template_documenti WHERE id = %s",
                    [template_id],
                )
                self.assertEqual(cur.fetchone(), ("Aggiornata", True))
                raise Annulla
        except Annulla:
            pass

    # 2. Asset: create + update metadati con `meta` dict.
    def test_asset_create_update_con_meta(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                repo, emittente, _ = self._template(cur)
                cur.execute("SELECT id FROM documenti.tipi_asset_documento WHERE attivo ORDER BY id LIMIT 1")
                asset_tipo = cur.fetchone()[0]
                asset_id = repo.create_asset({
                    "codice": "SCRDINAST",
                    "codice_interno": "SCRDINAST",
                    "descrizione": "Asset scritture dinamiche",
                    "asset_tipo_id": asset_tipo,
                    "mime_type": "image/png",
                    "file_name": "logo.png",
                    "file_size_bytes": 10,
                    "storage_key": f"assets/{emittente}/{'a' * 64}.png",
                    "sha256": "a" * 64,
                    "emittente_fiscale_id": emittente,
                    "attivo": True,
                    "meta": {"k": "v"},
                })
                self.assertTrue(repo.update_asset_metadati(
                    asset_id, {"descrizione": "Asset aggiornato", "meta": {"k": "w"}},
                ))
                cur.execute(
                    "SELECT descrizione, meta = '{\"k\": \"w\"}'::jsonb, sha256 "
                    "FROM documenti.template_asset WHERE id = %s",
                    [asset_id],
                )
                self.assertEqual(cur.fetchone(), ("Asset aggiornato", True, "a" * 64))
                raise Annulla
        except Annulla:
            pass

    # 3. Documento generato + file + evento: RETURNING id, uid e jsonb oggetto.
    def test_documento_generato_file_evento(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                repo, emittente, template_id = self._template(cur)
                cur.execute(
                    "SELECT tipo_documento_output_id, sorgente_tipo_id "
                    "FROM documenti.template_documenti WHERE id = %s",
                    [template_id],
                )
                tipo_output, sorgente = cur.fetchone()
                cur.execute(
                    "SELECT id FROM documenti.render_engine_documento WHERE attivo ORDER BY id LIMIT 1"
                )
                engine = cur.fetchone()[0]
                versione_id = repo.create_versione({
                    "template_documento_id": template_id,
                    "versione": 1,
                    "stato": "BOZZA",
                    "titolo": "v1",
                    "html_template": "<p>x</p>",
                    "render_engine_id": engine,
                    # NOT NULL senza default dal 20260930-16.
                    "versione_contesto": 1,
                })
                documento_id, uid = repo.create_documento_generato({
                    "tipo_documento_output_id": tipo_output,
                    "template_documento_id": template_id,
                    "template_versione_id": versione_id,
                    "sorgente_tipo_id": sorgente,
                    # Il preventivo del mondo: tipo a chiave uid (D.1).
                    "sorgente_id": None,
                    "sorgente_uid": self._preventivo_uid(cur),
                    "sorgente_riga": None,
                    "progressivo_sorgente": 1,
                    "stato": "GENERATO",
                    "titolo": "Documento",
                    "nome_file": "documento.pdf",
                    # La forma dei dati deve essere quella della versione:
                    # il trigger sull'INSERT la confronta (20260930-20).
                    "context_json": {"cliente": "x", "_meta": {"context_version": 1}},
                    "context_hash": "b" * 64,
                    "template_hash": "c" * 64,
                    "pdf_hash": "d" * 64,
                    "generato_da_user_id": None,
                    "emittente_fiscale_id": emittente,
                    "meta": {},
                })
                self.assertIsInstance(documento_id, int)
                self.assertEqual(len(uid), 36)

                tipo_file = repo.get_tipo_file_documento_by_codice("PDF_FINALE")
                self.assertIsNotNone(tipo_file)
                file_id = repo.create_documento_generato_file({
                    "documento_generato_id": documento_id,
                    "file_tipo_id": tipo_file["id"],
                    "mime_type": "application/pdf",
                    "file_name": "documento.pdf",
                    "file_size_bytes": 10,
                    "storage_key": f"documenti/{emittente}/{'d' * 64}.pdf",
                    "sha256": "d" * 64,
                    "ordinamento": 1,
                    "is_principale": True,
                    "meta": {},
                })
                self.assertIsInstance(file_id, int)
                evento_id = repo.emit_evento_documento({
                    "documento_generato_id": documento_id,
                    "evento_tipo": "GENERATO",
                    "user_id": None,
                    "esito": "OK",
                    "messaggio": None,
                    "detail": {"size_bytes": 10},
                    "meta": {},
                })

                cur.execute(
                    "SELECT jsonb_typeof(context_json), context_json ->> 'cliente' "
                    "FROM documenti.documenti_generati WHERE id = %s",
                    [documento_id],
                )
                self.assertEqual(cur.fetchone(), ("object", "x"))
                cur.execute(
                    "SELECT jsonb_typeof(detail), (detail ->> 'size_bytes')::int "
                    "FROM documenti.documenti_generati_eventi WHERE id = %s",
                    [evento_id],
                )
                self.assertEqual(cur.fetchone(), ("object", 10))
                raise Annulla
        except Annulla:
            pass

    # 4. Versione: create/update con jsonb dict e corpo non strippato, poi
    #    clone dal service sul DB vero.
    def test_versione_create_update_clone(self):
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        html = "  <pre>\n  riga indentata\n</pre>\n"
        css = "\n  p { margin: 0 }\n"
        try:
            with transaction.atomic(), connection.cursor() as cur:
                repo, _, template_id = self._template(cur)
                cur.execute(
                    "SELECT id FROM documenti.render_engine_documento WHERE attivo ORDER BY id LIMIT 1"
                )
                engine = cur.fetchone()[0]
                versione_id = repo.create_versione({
                    "template_documento_id": template_id,
                    "versione": 1,
                    "stato": "BOZZA",
                    "titolo": "  v1  ",
                    "html_template": html,
                    "css_template": css,
                    "render_engine_id": engine,
                    "versione_contesto": 1,
                    "context_schema": {"type": "object"},
                    "meta": {"k": "v"},
                })
                self.assertTrue(repo.update_versione(
                    versione_id,
                    {"markdown_template": "  # titolo\n", "context_schema": {"type": "array"}},
                ))
                cur.execute(
                    "SELECT titolo, html_template, css_template, markdown_template, "
                    "context_schema ->> 'type', meta ->> 'k' "
                    "FROM documenti.template_documenti_versioni WHERE id = %s",
                    [versione_id],
                )
                self.assertEqual(
                    cur.fetchone(),
                    ("v1", html, css, "  # titolo\n", "array", "v"),
                )

                # Il clone vero del service: il reader (scope operatore) e'
                # sostituito da uno che legge dal repository senza scope — qui
                # si prova la scrittura, non il perimetro.
                class _Reader:
                    def get_template(self, _user, _template_id):
                        return {}

                    def get_versione(self, _user, tpl_id, ver_id):
                        return repo.get_versione(tpl_id, ver_id)

                clone = TemplateVersioniAdminService(repo=repo, reader=_Reader()).clone_versione(
                    None, template_id, versione_id, {"titolo": "v2"},
                )
                cur.execute(
                    "SELECT versione, stato, html_template, css_template, "
                    "context_schema = '{\"type\": \"array\"}'::jsonb, "
                    "meta = '{\"k\": \"v\"}'::jsonb "
                    "FROM documenti.template_documenti_versioni WHERE id = %s",
                    [clone["id"]],
                )
                self.assertEqual(cur.fetchone(), (2, "BOZZA", html, css, True, True))
                raise Annulla
        except Annulla:
            pass
