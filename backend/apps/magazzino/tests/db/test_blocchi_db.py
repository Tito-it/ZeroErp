# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I BLOCCHI manuali dal service sul DATABASE PROVVISTO (Lotto 3 R-5,
#        piano-be-fe-magazzino-lotto-3 C1): `magazzino_service.apri_blocco` e
#        `libera_blocco` arrivano ai verbi `magazzino.fn_apri_blocco` /
#        `fn_libera_blocco` (firma, uuid dell'articolo, ritorno), il blocco
#        compare nella lettura del drill-down e ne esce liberato, e la seconda
#        liberazione arriva al client col codice del DB.
# Note: ⚠️ Le regole dei verbi (permesso, perimetro, posizione) le prova il
#       pgTAP `magazzino/test-blocco-manuale-e-porta-lotto3-v1`. Il mondo si
#       costruisce (azienda, operatore, contesto, azione concessa, magazzino,
#       articolo gestito). Transazione SEMPRE annullata; rifiuti in SAVEPOINT.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) BlocchiDbTests.test_apri_leggi_libera
2) BlocchiDbTests.test_liberare_due_volte_ha_il_codice_del_db
3) BlocchiDbTests.test_un_blocco_senza_per_chi_e_un_400_col_campo
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.magazzino.services import consultazione_service, magazzino_service
from apps.magazzino.services._helpers import E_VALIDAZIONE

_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _mondo AS SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m",
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
    "SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'blocca_merce')",
    """
    CREATE TEMP TABLE _fix AS
    SELECT dbops.fn_pgtap_crea_magazzino('BE-BLK-MAG', false)               AS mag,
           dbops.fn_pgtap_crea_articolo('BE-BLK-ART', true, false, false)   AS art
    """,
)


class BlocchiDbTests(unittest.TestCase):
    """Apertura e liberazione di un blocco, dal service al verbo."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            for passo in _FIXTURE:
                cur.execute(passo)
            cur.execute("SELECT mag, art::text FROM _fix")
            self.mag, self.art = cur.fetchone()

    def _blocchi(self) -> list:
        return consultazione_service.list_blocchi(articolo_id=self.art, magazzino_id=self.mag)["results"]

    def test_apri_leggi_libera(self) -> None:
        out = magazzino_service.apri_blocco({
            "magazzino_id": self.mag, "articolo_id": self.art, "qta": "5", "nota": "fiera",
        })
        blocco_id = out["blocco_id"]
        self.assertEqual([b["id"] for b in self._blocchi()], [blocco_id])

        magazzino_service.libera_blocco(blocco_id, {"nota": "fiera annullata"})

        self.assertEqual(self._blocchi(), [])
        with connection.cursor() as cur:
            cur.execute(
                "SELECT stato, meta ->> 'nota_liberazione' FROM magazzino.movimenti_attesi WHERE id = %s",
                [blocco_id],
            )
            self.assertEqual(cur.fetchone(), ("CHIUSA", "fiera annullata"))

    def test_liberare_due_volte_ha_il_codice_del_db(self) -> None:
        blocco_id = magazzino_service.apri_blocco({
            "magazzino_id": self.mag, "articolo_id": self.art, "qta": "1", "nota": "prova",
        })["blocco_id"]
        magazzino_service.libera_blocco(blocco_id, {})
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            magazzino_service.libera_blocco(blocco_id, {})
        self.assertEqual(cm.exception.code, "E_MAG_BLOCCO_GIA_CHIUSO")

    # Un blocco senza soggetto ne' nota: il CHECK `per_chi` del DB, tradotto
    # dal service in un errore col campo (non il testo crudo del vincolo).
    def test_un_blocco_senza_per_chi_e_un_400_col_campo(self) -> None:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            magazzino_service.apri_blocco({"magazzino_id": self.mag, "articolo_id": self.art, "qta": "1"})
        self.assertEqual(cm.exception.code, E_VALIDAZIONE)
        self.assertIn("per chi", cm.exception.message)
