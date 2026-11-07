# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le colonne jsonb che `DocumentiRepository` consegna alle API e alla
#        stampa arrivano come OGGETTI, non come testo, sul DATABASE VERO: i
#        cinque lettori di dettaglio (template, versione per template e per
#        id, asset, documento generato). Fino al 2026-10-28 le servivano come
#        stringa: lo fa ora il lettore comune (brief-modello-documento-vendita
#        §15.17.3), e qui se ne prova un punto per lettore.
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1`. Il mondo si COSTRUISCE
#       (`fn_pgtap_crea_preventivo_con_righe`); il modello e la versione sono
#       quelli che la porta unica sceglie, lo storage e' finto. Transazione
#       ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) JsonbDocumentiDbTests.test_template_meta_oggetto
2) JsonbDocumentiDbTests.test_versione_meta_e_schema_oggetti_nelle_due_letture
3) JsonbDocumentiDbTests.test_asset_meta_oggetto
4) JsonbDocumentiDbTests.test_documento_generato_meta_oggetto
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class JsonbDocumentiDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: il mondo di un preventivo e il suo documento generato. Lascia in
    #        `self` il repository, l'emittente e la riga del generato.
    def setUp(self) -> None:
        from apps.documenti.db.documenti_repository import DocumentiRepository
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )

        apri_transazione_annullata(self)
        self.repo = DocumentiRepository()
        storage = MagicMock()
        storage.write.return_value = "fake://documento.pdf"
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT p.preventivo_id, p.emittente_fiscale_id,
                       p.auth_user_id,
                       (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')
                  FROM dbops.fn_pgtap_crea_preventivo_con_righe('jsonb documenti be') p
                """
            )
            preventivo_id, self.emittente, uid, sorgente = cur.fetchone()
        self.generato = DocumentGenerationService(storage=storage).genera_documento(
            get_user_model().objects.get(pk=uid),
            emittente_fiscale_id=self.emittente,
            sorgente_tipo_id=sorgente,
            sorgente_id=preventivo_id,
                    )

    def test_template_meta_oggetto(self) -> None:
        t = self.repo.get_template(self.generato["template_documento_id"], emittente_ids_scope=None)
        assert t is not None
        self.assertIsInstance(t["meta"], dict)

    def test_versione_meta_e_schema_oggetti_nelle_due_letture(self) -> None:
        letture = {
            "get_versione": self.repo.get_versione(
                self.generato["template_documento_id"], self.generato["template_versione_id"],
            ),
            "get_versione_by_id": self.repo.get_versione_by_id(self.generato["template_versione_id"]),
        }
        for nome, v in letture.items():
            with self.subTest(lettura=nome):
                assert v is not None
                self.assertIsInstance(v["meta"], dict)
                # NULL ammesso (nessuno schema dichiarato), testo mai.
                self.assertNotIsInstance(v["context_schema"], str)

    def test_asset_meta_oggetto(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM documenti.tipi_asset_documento WHERE attivo ORDER BY id LIMIT 1")
            asset_tipo = cur.fetchone()[0]
        asset_id = self.repo.create_asset({
            "codice": "JSONB_BE", "codice_interno": "JSONBBE", "descrizione": "Asset jsonb",
            "asset_tipo_id": asset_tipo, "mime_type": "image/png", "file_name": "a.png",
            "file_size_bytes": 10, "storage_key": f"assets/{self.emittente}/jsonbbe.png",
            "sha256": "f" * 64, "emittente_fiscale_id": self.emittente, "attivo": True,
            "meta": {"origine": "test"},
        })
        a = self.repo.get_asset(asset_id, emittente_ids_scope=None)
        assert a is not None
        self.assertEqual(a["meta"], {"origine": "test"})

    def test_documento_generato_meta_oggetto(self) -> None:
        d = self.repo.get_documento_generato(self.generato["id"], emittente_ids_scope=None)
        assert d is not None
        self.assertIsInstance(d["meta"], dict)
