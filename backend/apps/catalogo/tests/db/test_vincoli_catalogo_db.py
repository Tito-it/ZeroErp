# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le mappe dei vincoli del service catalogo (`_ARTICOLO_CHECK`,
#        `_COMPONENTE_UNIQUE`, `_UOM_OPERATIVA_UNIQUE`) provate contro il
#        database vero: ogni nome di vincolo che il service traduce esiste e
#        scatta davvero, con la frase del dominio e non col ripiego generico.
#
# 🔴 PERCHE' SUL DB VERO. La mappa riconosce il vincolo dal NOME: se il DB lo
#    rinomina, il service cade sul ripiego («Violazione vincoli …») senza
#    nessun rosso, e i test con l'IntegrityError finto restano verdi. Il caso
#    composito + solo componente ha anche una copia nel form
#    (`ArticoloDrawer.vue`, `ESCLUSI`): questo test e' il presidio che il CHECK
#    che quella copia ripete c'e' ancora, col nome che il service conosce.
#
# ⭐ I CASI SI COSTRUISCONO (`dbops.fn_pgtap_crea_articolo`), in una
#    transazione annullata: niente dipende dai dati presenti.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1) composito e solo componente insieme -> la frase del CHECK
#      `chk_articoli_composito_non_solo_componente`, senza campo
#   2) un legame che si sovrappone a uno in vigore -> la frase di
#      `uq_articoli_componenti_no_overlap`, senza campo
#   3) la UoM base aggiunta di nuovo come operativa -> la frase di
#      `uq_artuomop_articolo_uom`, campo `uom_id`
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from typing import Any
from uuid import uuid4

from django.db import connection, transaction

from apps.catalogo.services import catalogo_service
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class VincoliCatalogoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("dbops.fn_pgtap_crea_articolo(varchar, boolean, boolean, boolean,"
                              " bigint, smallint, boolean, boolean, bigint, bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.sfx = uuid4().hex[:8].upper()

    def _articolo(self, sigla: str, *, composito: bool = False) -> str:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, p_is_composito => %s)::text",
                [f"VINC-{sigla}-{self.sfx}", composito],
            )
            return cur.fetchone()[0]

    # Il rifiuto in un savepoint: la transazione del test resta usabile.
    def _rifiuto(self, chiamata: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            chiamata()
        return cm.exception

    # 1. Composito e solo componente insieme.
    def test_composito_e_solo_componente(self) -> None:
        semplice = self._articolo("S")
        err = self._rifiuto(lambda: catalogo_service.fn_update_articolo(
            semplice, {"is_composito": True, "is_solo_componente": True},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("solo componente", err.message)
        self.assertNotIn("field", err.context)

    # 2. Un secondo legame dello stesso componente in un periodo che si
    #    sovrappone al primo.
    def test_legame_sovrapposto(self) -> None:
        kit = self._articolo("K", composito=True)
        figlio = self._articolo("F")
        catalogo_service.fn_create_componente(
            kit, {"componente_id": figlio, "coeff_qta": "1", "valido_dal": "2020-01-01"},
        )
        err = self._rifiuto(lambda: catalogo_service.fn_create_componente(
            kit, {"componente_id": figlio, "coeff_qta": "2", "valido_dal": "2021-01-01"},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("periodo che si sovrappone", err.message)
        self.assertNotIn("field", err.context)

    # 3. La UoM base ha gia' la sua operativa (seed del trigger): aggiungerla
    #    di nuovo e' il doppione.
    def test_uom_operativa_doppia(self) -> None:
        articolo = self._articolo("U")
        with connection.cursor() as cur:
            cur.execute("SELECT uom_id FROM catalogo.articoli WHERE id = %s", [articolo])
            uom_base = cur.fetchone()[0]
        err = self._rifiuto(lambda: catalogo_service.fn_create_uom_operativa(
            articolo, {"uom_id": uom_base, "factor_to_base": "1"},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("gia' questa unita'", err.message)
        self.assertEqual(err.context.get("field"), "uom_id")
