# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il ritiro di un articolo (`catalogo.articoli.obsoleto_dal`) dal
#        backend, sul database vero: la data si scrive e si toglie dalla PATCH
#        dell'articolo, e il dettaglio e il picker portano `obsoleto_dal` ed
#        `e_obsoleto` della vista `catalogo.vw_articoli_dettaglio`
#        (brief-db-articoli-obsoleto-dal §8).
#
# 🔴 PERCHE' SUL DB VERO. Il repository proietta le colonne della vista PER
#    NOME (`ARTICOLI_DETAIL_COLUMNS`, `_LOOKUP_ARTICOLI_COLONNE`): una colonna
#    che la vista non ha e' un 500 che i test col repository finto non vedono,
#    e una colonna non nominata e' una cella vuota senza nessun rosso.
#    `e_obsoleto` e' il predicato del DB (`script.fn_e_obsoleto`, alla data
#    operativa): il backend lo trasporta e non confronta date.
#
# ⭐ I CASI SI COSTRUISCONO (`dbops.fn_pgtap_crea_articolo`), in una
#    transazione annullata: niente dipende dai dati presenti.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1) l'articolo nuovo non e' ritirato: data vuota, `e_obsoleto` falso
#   2) la data di oggi (operativa) lo ritira; una data futura e' un ritiro
#      programmato (`e_obsoleto` ancora falso); null la toglie
#   3) il picker libero porta le due colonne dell'articolo ritirato
#   4) una data che non e' una data -> 400 col campo
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from datetime import timedelta
from typing import Any
from uuid import uuid4

from django.db import connection, transaction

from apps.catalogo.services import catalogo_service
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class ArticoloObsoletoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("dbops.fn_pgtap_crea_articolo(varchar, boolean, boolean, boolean,"
                              " bigint, smallint, boolean, boolean, bigint, bigint)")
        richiedi_db_provvisto("script.fn_e_obsoleto(date)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.codice = f"OBS-{uuid4().hex[:8].upper()}"
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_articolo(%s)::text", [self.codice])
            self.articolo = cur.fetchone()[0]
            cur.execute("SELECT script.fn_data_operativa()")
            self.oggi = cur.fetchone()[0]

    def _stato(self, dettaglio: dict[str, Any]) -> tuple[Any, Any]:
        return dettaglio["obsoleto_dal"], dettaglio["e_obsoleto"]

    # 1. L'articolo nuovo si sceglie.
    def test_l_articolo_nuovo_non_e_ritirato(self) -> None:
        self.assertEqual(self._stato(catalogo_service.fn_get_articolo(self.articolo)), (None, False))

    # 2. La data si scrive e si toglie dalla PATCH; quando vale lo dice il DB.
    def test_la_data_ritira_programma_e_riattiva(self) -> None:
        ritirato = catalogo_service.fn_update_articolo(
            self.articolo, {"obsoleto_dal": self.oggi.isoformat()},
        )
        self.assertEqual(self._stato(ritirato), (self.oggi, True))

        domani = self.oggi + timedelta(days=1)
        programmato = catalogo_service.fn_update_articolo(
            self.articolo, {"obsoleto_dal": domani.isoformat()},
        )
        self.assertEqual(self._stato(programmato), (domani, False))

        riattivato = catalogo_service.fn_update_articolo(self.articolo, {"obsoleto_dal": None})
        self.assertEqual(self._stato(riattivato), (None, False))

    # 3. Il picker libero porta le due colonne: chi sceglie vede il ritiro.
    def test_il_picker_porta_il_ritiro(self) -> None:
        catalogo_service.fn_update_articolo(self.articolo, {"obsoleto_dal": self.oggi.isoformat()})
        trovati = catalogo_service.fn_lookup_articoli(search=self.codice)["results"]
        riga = next(r for r in trovati if r["codice"] == self.codice)
        self.assertEqual((riga["obsoleto_dal"], riga["e_obsoleto"]), (self.oggi, True))

    # 4. Una data scritta male e' un 400 sul campo, non un errore del DB.
    def test_una_data_non_valida_e_rifiutata_sul_campo(self) -> None:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            catalogo_service.fn_update_articolo(self.articolo, {"obsoleto_dal": "31-12-2026"})
        self.assertEqual(cm.exception.code, "E_CATALOGO_VALIDATION")
        self.assertEqual(cm.exception.context.get("field"), "obsoleto_dal")
