# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «l'unita' della riga di listino vale per l'articolo» la dice il DB
#        (`catalogo.fn_get_uom_factor` alla decorrenza della versione), sul
#        database vero: BE17 di brief-db-revisione-catalogo (2026-11-09).
# Note: ⛔ Fino al 2026-11-09 `ListiniRepository.get_articolo_uom_validation`
#       ricopiava la regola (base o mappatura attiva): senza le conversioni
#       generali e senza la data. I casi che la copia sbagliava si COSTRUISCONO
#       (unita', conversione e mappature dalle porte dell'applicazione), in una
#       transazione annullata: niente dipende dalle unita' presenti.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ListinoUomCompatibileDbTests.test_unita_base
2) ListinoUomCompatibileDbTests.test_unita_senza_conversione
3) ListinoUomCompatibileDbTests.test_conversione_generale_alla_data
4) ListinoUomCompatibileDbTests.test_mappatura_chiusa_prima_della_decorrenza
"""
from __future__ import annotations

import unittest
from datetime import date
from uuid import uuid4

from django.db import connection

from apps.catalogo.services import catalogo_service
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.listini_repository import ListiniRepository

_DECORRENZA = date(2026, 6, 1)


class ListinoUomCompatibileDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("catalogo.fn_get_uom_factor(uuid,bigint,date)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.sfx = uuid4().hex[:6].upper()
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM catalogo.uom_tipi WHERE codice_interno = 'MASSA'")
            tipo = cur.fetchone()
        assert tipo is not None, "tipologia MASSA assente dal seed"
        self.tipo = tipo[0]
        self.base = self._unita("LB")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, p_uom_id => %s)::text",
                [f"LUOM-{self.sfx}", self.base],
            )
            self.articolo = cur.fetchone()[0]

    def _unita(self, sigla: str) -> int:
        riga = catalogo_service.fn_create_unita_misura(
            {"codice": f"{sigla}{self.sfx}", "descrizione": f"Prova {sigla}", "tipo_uom_id": self.tipo},
        )
        return int(riga["id"])

    def _compatibile(self, uom_id: int) -> bool:
        return ListiniRepository().get_articolo_uom_validation(
            self.articolo, uom_id, _DECORRENZA,
        )["uom_compatibile"]

    # 1. L'unita' base vale sempre.
    def test_unita_base(self) -> None:
        self.assertTrue(self._compatibile(self.base))

    # 2. Un'unita' qualunque, senza mappatura ne' conversione: non vale.
    def test_unita_senza_conversione(self) -> None:
        self.assertFalse(self._compatibile(self._unita("LX")))

    # 3. Una conversione generale in vigore alla decorrenza basta: la copia
    #    vecchia non la vedeva.
    def test_conversione_generale_alla_data(self) -> None:
        altra = self._unita("LK")
        catalogo_service.fn_create_conversione(
            {"uom_from_id": altra, "uom_to_id": self.base, "fattore": "1000", "valido_dal": "2026-01-01"},
        )
        self.assertTrue(self._compatibile(altra))

    # 4. Una mappatura chiusa prima della decorrenza non vale: la copia vecchia
    #    la ammetteva (non guardava la data).
    def test_mappatura_chiusa_prima_della_decorrenza(self) -> None:
        cartone = self._unita("LC")
        catalogo_service.fn_create_uom_operativa(self.articolo, {
            "uom_id": cartone, "factor_to_base": "10",
            "valido_dal": "2026-01-01", "valido_al": "2026-05-31",
        })
        self.assertFalse(self._compatibile(cartone))
