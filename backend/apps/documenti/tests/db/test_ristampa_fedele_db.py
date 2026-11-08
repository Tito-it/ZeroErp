# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ristampa fedele sul DATABASE VERO: un documento generato si
#        ristampa dalla sua versione e dal contesto congelato letto da
#        `documenti_generati.context_json`.
# Note: ⭐ Prova la GIUNTURA che i test del service non vedono: il cursore RAW
#       di psycopg 3 consegna il jsonb come `str`, e i finti del service lo
#       passavano gia' decodificato. Fino al 2026-10-28 la ristampa fedele
#       rifiutava cosi' OGNI documento («senza contesto congelato»).
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1`. Il mondo si COSTRUISCE
#       (`fn_pgtap_crea_preventivo_con_righe`), il modello e' quello che la
#       porta unica sceglie; lo storage e' finto (il file non conta qui).
#       Transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RistampaFedeleDbTests.test_documento_generato_si_ristampa
   il contesto congelato arriva come dizionario, e la ristampa da' il PDF con
   la stessa versione e lo stesso contenuto (template_hash).
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto


class RistampaFedeleDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("documenti.fn_risolvi_template_applicabile(bigint, bigint, bigint, bigint)")

    def test_documento_generato_si_ristampa(self) -> None:
        from apps.documenti.db.documenti_repository import DocumentiRepository
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )

        storage = MagicMock()
        storage.write.return_value = "fake://documento.pdf"
        svc = DocumentGenerationService(storage=storage)
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.preventivo_id, p.emittente_fiscale_id,
                           p.auth_user_id,
                           (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')
                      FROM dbops.fn_pgtap_crea_preventivo_con_righe('ristampa fedele be') p
                    """
                )
                preventivo_id, emittente, uid, sorgente = cur.fetchone()
                user = get_user_model().objects.get(pk=uid)

                generato = svc.genera_documento(
                    user,
                    emittente_fiscale_id=emittente,
                    sorgente_tipo_id=sorgente,
                    sorgente_id=preventivo_id,
                                    )

                # La giuntura: il contesto congelato e' un dizionario.
                snapshot = DocumentiRepository().get_documento_generato_snapshot(
                    generato["id"], emittente_ids_scope=None,
                )
                assert snapshot is not None
                self.assertIsInstance(snapshot["context_json"], dict)

                ristampa = svc.ristampa_fedele(user, generato["id"])
                self.assertTrue(ristampa["pdf_bytes"].startswith(b"%PDF"))
                self.assertEqual(ristampa["template_versione_id"], generato["template_versione_id"])
                self.assertIs(ristampa["template_hash_match"], True)
                raise Annulla
        except Annulla:
            pass
