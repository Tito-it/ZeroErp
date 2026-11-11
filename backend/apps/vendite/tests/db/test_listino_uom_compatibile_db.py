# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «l'unita' della riga di listino si converte per l'articolo in OGNI
#        giorno del periodo della versione» la dice il DB, sul database vero,
#        dalle porte del backend: BE22 di brief-db-revisione-catalogo (D25,
#        giro 2-bis, 2026-11-11). La regola si rompe da tre lati, e ognuno ha
#        il suo rifiuto:
#          1. la riga scritta (`vendite.trgfn_listini_righe_guard_uom_periodo`,
#             `E_LISTINO_UOM_NON_CONVERTIBILE`, campo `uom_id`);
#          2. il periodo della versione allungato
#             (`vendite.trgfn_listini_versioni_guard_uom_periodo`, campo
#             `valido_al`);
#          3. il catalogo che cambia sotto un listino ATTIVO
#             (`catalogo.trgfn_uom_guard_listini_attivi`, differito:
#             `E_UOM_CHIUSURA_CON_LISTINI_ATTIVI` a fine transazione).
# Note: ⛔ Fino al 2026-11-11 la regola stava nel backend
#       (`ListiniRepository.get_articolo_uom_validation`, BE17) e guardava la
#       sola DECORRENZA: una mappatura che finiva durante la versione passava
#       (caso 4). Ritirata: qui si prova il DB attraverso le porte.
#       ⭐ Il mondo si COSTRUISCE (unita', conversione, mappature, listino e
#       versioni), in una transazione annullata; le date dal giorno AZIENDALE.
#       Il giudizio differito si chiede con `SET CONSTRAINTS ALL IMMEDIATE`, come
#       `test_cliente_stessa_chiave_db`.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ListinoUomCompatibileDbTests.test_unita_base
2) ListinoUomCompatibileDbTests.test_unita_senza_conversione
3) ListinoUomCompatibileDbTests.test_conversione_generale_senza_fine
4) ListinoUomCompatibileDbTests.test_mappatura_che_finisce_dentro_la_versione
5) ListinoUomCompatibileDbTests.test_periodo_allungato_oltre_la_mappatura
6) ListinoUomCompatibileDbTests.test_mappatura_chiusa_sotto_un_listino_attivo
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta
from uuid import uuid4

from django.db import DatabaseError, connection, transaction

from apps.catalogo.services import catalogo_service
from apps.catalogo.tests.db._unita_di_prova import crea_unita_di_prova
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import (
    apri_operatore_con_aree,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)
from apps.vendite.services import listini_service
from apps.vendite.tests.db._listino_di_prova import crea_listino_di_prova


class ListinoUomCompatibileDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("vendite.trgfn_listini_righe_guard_uom_periodo()")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.sfx = uuid4().hex[:6].upper()
        with connection.cursor() as cur:
            apri_operatore_con_aree(
                cur, aree=("catalogo", "vendite"), motivo="test BE22: unita del listino",
            )
            cur.execute("SELECT script.fn_data_operativa()")
            self.oggi: date = cur.fetchone()[0]
            self.listino, tipologia = crea_listino_di_prova(
                cur, etichetta="py uom", valido_dal=self._giorni(-400), valido_al=self._giorni(-300),
            )
        self.base = crea_unita_di_prova("LB", self.sfx)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, p_uom_id => %s,"
                " p_listino_tipologia_id => %s::smallint)::text",
                [f"LUOM-{self.sfx}", self.base, tipologia],
            )
            self.articolo = cur.fetchone()[0]

    def _giorni(self, n: int) -> date:
        return self.oggi + timedelta(days=n)

    # Una mappatura dell'articolo da oggi, con la fine data (o senza).
    def _mappatura(self, uom_id: int, valido_al: date | None) -> int:
        riga = catalogo_service.fn_create_uom_operativa(self.articolo, {
            "uom_id": uom_id, "factor_to_base": "10", "valido_dal": self.oggi.isoformat(),
            "valido_al": valido_al.isoformat() if valido_al else None,
        })
        return int(riga["id"])

    # Una versione in BOZZA del listino, dal giorno dopo, con la fine data.
    def _versione(self, valido_al: date | None, n: int = 0) -> int:
        riga = listini_service.fn_create_versione(self.listino, {
            "codice_versione": f"PYU{self.sfx}{n}", "valido_dal": self._giorni(1).isoformat(),
            "valido_al": valido_al.isoformat() if valido_al else None,
        })
        return int(riga["id"])

    def _riga(self, versione: int, uom_id: int) -> dict:
        return listini_service.fn_create_riga(self.listino, versione, {
            "articolo_id": self.articolo, "uom_id": uom_id, "prezzo": "12.50",
        })

    # ⭐ Il rifiuto del guard risale come errore del database e lo rende il
    #    traduttore generale (`ErrorTranslator`, via middleware), con codice e
    #    campo: e' la strada della richiesta vera, e la si percorre qui.
    def _rifiuto_riga(self, versione: int, uom_id: int):
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self._riga(versione, uom_id)
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(ErrorTranslator.get_http_status(errore), 400)
        return errore

    # 1. L'unita' base vale sempre, anche per una versione senza fine.
    def test_unita_base(self) -> None:
        self.assertIsNotNone(self._riga(self._versione(None), self.base).get("id"))

    # 2. Un'unita' senza mappatura ne' conversione: il rifiuto, col campo.
    def test_unita_senza_conversione(self) -> None:
        errore = self._rifiuto_riga(self._versione(None), crea_unita_di_prova("LX", self.sfx))
        self.assertEqual(errore.code, "E_LISTINO_UOM_NON_CONVERTIBILE")
        self.assertIn("uom_id", errore.fields)

    # 3. Una conversione generale senza fine copre tutto il periodo.
    def test_conversione_generale_senza_fine(self) -> None:
        altra = crea_unita_di_prova("LK", self.sfx)
        catalogo_service.fn_create_conversione({
            "uom_from_id": altra, "uom_to_id": self.base, "fattore": "1000",
            "valido_dal": self.oggi.isoformat(),
        })
        self.assertIsNotNone(self._riga(self._versione(None), altra).get("id"))

    # 4. Una mappatura che finisce DENTRO la versione: rifiutata. ⭐ E' il caso
    #    che la copia del backend (alla sola decorrenza) lasciava passare.
    def test_mappatura_che_finisce_dentro_la_versione(self) -> None:
        cartone = crea_unita_di_prova("LC", self.sfx)
        self._mappatura(cartone, self._giorni(30))
        errore = self._rifiuto_riga(self._versione(self._giorni(60)), cartone)
        self.assertEqual(errore.code, "E_LISTINO_UOM_NON_CONVERTIBILE")
        self.assertIn("uom_id", errore.fields)

    # 5. Secondo lato: la riga sta dentro la mappatura, poi la versione si
    #    allunga oltre la sua fine.
    def test_periodo_allungato_oltre_la_mappatura(self) -> None:
        cartone = crea_unita_di_prova("LP", self.sfx)
        self._mappatura(cartone, self._giorni(30))
        versione = self._versione(self._giorni(20))
        self._riga(versione, cartone)
        # ⚠️ Qui il service traduce lui il rifiuto del DB
        #    (`_rifiuto_del_db_su_versione`): arriva un ServiceError, coi campi.
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            listini_service.fn_update_versione(
                self.listino, versione, {"valido_al": self._giorni(60).isoformat()},
            )
        errore = ctx.exception
        self.assertEqual(errore.code, "E_LISTINO_UOM_NON_CONVERTIBILE")
        self.assertIn("valido_al", errore.fields)

    # 6. Terzo lato: un listino ATTIVO usa la mappatura, e la mappatura si
    #    chiude prima della fine della versione. Il rifiuto e' a fine
    #    transazione: si chiede con `SET CONSTRAINTS ALL IMMEDIATE`.
    def test_mappatura_chiusa_sotto_un_listino_attivo(self) -> None:
        cartone = crea_unita_di_prova("LA", self.sfx)
        mappatura = self._mappatura(cartone, None)
        versione = self._versione(None)
        self._riga(versione, cartone)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, %s, 'ATTIVA')",
                [versione],
            )
            # ⭐ `ALL`, non il nome del trigger: il test giudica la REGOLA, e un
            #    nome scritto qui si romperebbe a ogni rinomina (o a un trigger
            #    gemello su INSERT/DELETE) senza che la regola sia cambiata.
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            catalogo_service.fn_update_uom_operativa(
                self.articolo, mappatura, {"valido_al": self._giorni(30).isoformat()},
            )
            with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(errore.code, "E_UOM_CHIUSURA_CON_LISTINI_ATTIVI")
