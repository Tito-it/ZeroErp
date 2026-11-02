# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera delle liste dei template documenti e degli asset
#        sul DATABASE VERO: il repository cerca col BB
#        `add_ricerca_full_condition`, e le colonne le accende il catalogo
#        (`documenti.template_documenti`, `documenti.template_asset`, e dal
#        2026-09-27 `documenti.template_versioni` e
#        `documenti.documenti_sorgente`).
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero, .codex/AGENTS.md): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, poi il CONTESTO, poi un template e
#       un asset di quell'azienda. Tutto in transazione ANNULLATA.
#       ⛔ Il `codice_interno` NON si cerca (Tid, 2026-09-23): il test lo
#       prova anche in negativo, perche' fino al 2026-09-24 lo si cercava.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RicercaListeDocumentiDbTests.test_la_ricerca_trova_ogni_colonna_accesa
   Per template e asset costruiti, ogni colonna che il catalogo accende trova
   la riga (`verifica_ricerca_colonna_per_colonna`); un termine inesistente
   no; il `codice_interno` non trova niente; un termine di un carattere
   filtra (tabelle di configurazione, da un carattere).
2) RicercaListeDocumentiDbTests.test_versioni_e_documenti_sorgente_trovano_ogni_colonna_accesa
   Le due liste nate il 2026-09-27 (88 e 84): una versione di un template e
   un documento generato di una sorgente, costruiti; ogni colonna accesa a
   catalogo trova la riga, un termine inesistente no.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import (
    Annulla,
    richiedi_db_provvisto,
    verifica_ricerca_colonna_per_colonna,
)

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)


class RicercaListeDocumentiDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    # 1. Template e asset: ogni colonna accesa a catalogo trova la sua riga.
    def test_la_ricerca_trova_ogni_colonna_accesa(self):
        from apps.documenti.db.documenti_repository import DocumentiRepository

        # `emittente_ids_scope=None` = nessun filtro di perimetro: qui si prova
        # la ricerca, non lo scope.
        _filtri = {
            "attivo": None, "emittente_fiscale_id": None, "emittente_ids_scope": None,
            "order_by": "codice", "order_dir": "asc", "limit": 200, "offset": 0,
        }
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for passo in _FIXTURE:
                    cur.execute(passo)
                cur.execute("SELECT emittente_fiscale_id FROM _mondo")
                emittente = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO documenti.template_documenti
                           (tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id,
                            codice, codice_interno, descrizione, context_builder_code)
                    VALUES ((SELECT id FROM documenti.tipi_documento_output ORDER BY id LIMIT 1),
                            (SELECT id FROM config.sorgenti ORDER BY id LIMIT 1),
                            %s, 'RICCODTPL', 'RICINTTPL', 'Template ricdesctpl', 'ricerca')
                    RETURNING id
                    """,
                    [emittente],
                )
                template = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO documenti.template_asset
                           (codice, codice_interno, descrizione, asset_tipo_id, mime_type,
                            file_name, file_size_bytes, storage_key, sha256, emittente_fiscale_id)
                    VALUES ('RICCODAST', 'RICINTAST', 'Asset ricdescast',
                            (SELECT id FROM documenti.tipi_asset_documento ORDER BY id LIMIT 1),
                            'image/png', 'ricfileast.png', 16, 'assets/ricerca/ricfileast.png',
                            repeat('b', 64), %s)
                    RETURNING id
                    """,
                    [emittente],
                )
                asset = cur.fetchone()[0]

                # Scopo: le righe della lista template per il termine `t`.
                def cerca_template(t):
                    return DocumentiRepository().list_templates(
                        search=t, tipo_documento_output_id=None, sorgente_tipo_id=None, **_filtri,
                    )[0]

                # Scopo: le righe della lista asset per il termine `t`.
                def cerca_asset(t):
                    return DocumentiRepository().list_asset(search=t, asset_tipo_id=None, **_filtri)[0]

                verifica_ricerca_colonna_per_colonna(
                    self, cur, "documenti.template_documenti", template,
                    {"codice": "riccodtpl", "descrizione": "ricdesctpl"},
                    cerca_template,
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "documenti.template_asset", asset,
                    {"codice": "riccodast", "descrizione": "ricdescast", "file_name": "ricfileast"},
                    cerca_asset,
                )
                # ⛔ Il codice interno non si cerca (Tid, 2026-09-23).
                self.assertEqual(cerca_template("ricinttpl"), [])
                self.assertEqual(cerca_asset("ricintast"), [])
                # ⭐ Da un carattere (configurazione, Tid 2026-09-24): un termine
                #    di un carattere FILTRA — con la soglia di default sarebbe
                #    ignorato e uscirebbe almeno la riga costruita.
                self.assertEqual(cerca_template("§"), [])
                self.assertEqual(cerca_asset("§"), [])
                raise Annulla
        except Annulla:
            pass

    # 2. Versioni di un template e documenti generati di una sorgente (liste
    #    88 e 84, 2026-09-27): ogni colonna accesa a catalogo trova la riga.
    def test_versioni_e_documenti_sorgente_trovano_ogni_colonna_accesa(self):
        from apps.documenti.db.documenti_repository import DocumentiRepository

        sorgente_uid = "00000000-0000-0000-0000-00000000c0de"
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for passo in _FIXTURE:
                    cur.execute(passo)
                cur.execute("SELECT emittente_fiscale_id FROM _mondo")
                emittente = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO documenti.template_documenti
                           (tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id,
                            codice, codice_interno, descrizione, context_builder_code)
                    VALUES ((SELECT id FROM documenti.tipi_documento_output ORDER BY id LIMIT 1),
                            (SELECT id FROM config.sorgenti ORDER BY id LIMIT 1),
                            %s, 'RICVERTPL', 'RICVERINT', 'Template versioni', 'ricerca')
                    RETURNING id, tipo_documento_output_id, sorgente_tipo_id
                    """,
                    [emittente],
                )
                template, tipo_output, sorgente_tipo = cur.fetchone()
                cur.execute(
                    """
                    INSERT INTO documenti.template_documenti_versioni
                           (template_documento_id, versione, titolo, html_template,
                            render_engine_id, versione_contesto)
                    VALUES (%s, 1, 'Versione rictitver', '<p></p>',
                            (SELECT id FROM documenti.render_engine_documento ORDER BY id LIMIT 1),
                            1)
                    RETURNING id
                    """,
                    [template],
                )
                versione = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO documenti.documenti_generati
                           (tipo_documento_output_id, template_documento_id,
                            template_versione_id, sorgente_tipo_id, sorgente_uid,
                            progressivo_sorgente, titolo, nome_file, context_json,
                            context_hash, template_hash, pdf_hash, emittente_fiscale_id)
                    VALUES (%s, %s, %s, %s, %s, 1, 'Documento rictitdoc',
                            'ricfiledoc.pdf', '{"_meta": {"context_version": 1}}'::jsonb,
                            repeat('a', 64),
                            repeat('b', 64), repeat('c', 64), %s)
                    RETURNING id
                    """,
                    [tipo_output, template, versione, sorgente_tipo, sorgente_uid, emittente],
                )
                documento = cur.fetchone()[0]

                # Scopo: le righe della lista versioni per il termine `t`.
                def cerca_versioni(t):
                    return DocumentiRepository().list_versioni(
                        template, attivo=None, stato=None, search=t, limit=200, offset=0,
                    )[0]

                # Scopo: le righe della lista documenti della sorgente per `t`.
                def cerca_documenti(t):
                    return DocumentiRepository().list_documenti_per_sorgente(
                        sorgente_tipo_id=sorgente_tipo, sorgente_uid=sorgente_uid,
                        sorgente_riga=None, emittente_ids_scope=None,
                        search=t, limit=200, offset=0,
                    )[0]

                verifica_ricerca_colonna_per_colonna(
                    self, cur, "documenti.template_versioni", versione,
                    {"titolo": "rictitver"},
                    cerca_versioni,
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "documenti.documenti_sorgente", documento,
                    {"titolo": "rictitdoc", "nome_file": "ricfiledoc"},
                    cerca_documenti,
                )
                raise Annulla
        except Annulla:
            pass
