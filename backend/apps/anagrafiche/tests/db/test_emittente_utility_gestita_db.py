# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le utility che un'azienda gestisce, dal service VERO sul DB vero
#        (brief-db-utility-gestite-dall-emittente §10 R-2, R-3, R-4): la lista
#        del drawer «Gestisci utilities» letta dal BB `fn_utilities_emittente`,
#        l'attivazione senza parametri, i parametri riportati a NULL, la
#        cancellazione rifiutata finche' un billing account usa la coppia.
# Note: ⭐ PERCHE' SUL DB. Il rifiuto della cancellazione e' una FK composta
#       DIFFERITA sul figlio: un mock non vede ne' il nome del vincolo che
#       arriva, ne' QUANDO arriva (a fine istruzione in autocommit; al COMMIT
#       dentro un `atomic`, fuori dalla traduzione del service). Qui la
#       transazione del test e' annullata, quindi la cancellazione gira con
#       `SET CONSTRAINTS ALL IMMEDIATE`, come la vedrebbe l'autocommit.
#       Il mondo si COSTRUISCE: azienda da `dbops.fn_pgtap_crea_emittente_operatore`
#       (gestisce ogni utility ammessa per EF), cliente da
#       `dbops.fn_pgtap_crea_cliente_ba` col contesto del suo operatore, SUPER_ADMIN col contesto aperto per
#       ultimo. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EmittenteUtilityGestitaDbTests.test_lista_dal_bb — ogni utility ammessa per EF, gestita
   con la sua riga; i valori scritti NULL accanto agli effettivi
2) EmittenteUtilityGestitaDbTests.test_attiva_senza_parametri_e_toglie — tolta la riga
   inutilizzata, l'utility torna attivabile; riattivata con il solo `utility_id`
3) EmittenteUtilityGestitaDbTests.test_parametri_a_null — i parametri scritti e riportati a
   NULL: `personalizzata` segue
4) EmittenteUtilityGestitaDbTests.test_in_uso_non_si_toglie — con un billing account sulla
   coppia la cancellazione e' `E_ANAG_FK` col messaggio parlante, la riga resta
5) EmittenteUtilityGestitaDbTests.test_attivo_rifiutato — `attivo` in una PATCH e' un 400
   che lo nomina, prima del DB
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.anagrafiche.services.emittenti_fiscali_service import (
    EmittentiFiscaliUtilitiesService,
)
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import (
    apri_contesto_su,
    apri_super_admin_costruito,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)


class EmittenteUtilityGestitaDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("anagrafiche.fn_utilities_emittente(bigint, varchar)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT emittente_fiscale_id, soggetto_ruolo_id, auth_user_id"
                "  FROM dbops.fn_pgtap_crea_emittente_operatore('UTG')"
            )
            emittente_id, sr_id, operatore = cur.fetchone()
            self.emittente_id, self.sr_id = int(emittente_id), int(sr_id)
            self.operatore = int(operatore)
        self.svc = EmittentiFiscaliUtilitiesService()

    # Scopo: il SUPER_ADMIN col contesto aperto, PER ULTIMO: un cliente si
    #        costruisce prima (il legame del BA lo scriverebbe il trigger verso
    #        l'emittente di chi agisce, e il SUPER_ADMIN non ne ha uno).
    @staticmethod
    def _apri_admin() -> None:
        with connection.cursor() as cur:
            apri_super_admin_costruito(cur, etichetta="utility gestite admin")

    def _righe(self) -> dict[int, dict]:
        return {r["utility_id"]: r for r in self.svc.list_records(self.emittente_id)}

    def _una_gestita(self) -> dict:
        gestite = [r for r in self._righe().values() if r["gestita"]]
        if not gestite:
            self.skipTest("la matrice non ammette nessuna utility per EF su questo DB")
        return gestite[0]

    # Scopo: l'utility della prima riga dell'azienda, letta prima del contesto.
    def _prima_utility(self) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT min(utility_id) FROM anagrafiche.emittenti_fiscali_utilities"
                " WHERE emittente_soggetto_ruolo_id = %s",
                [self.sr_id],
            )
            utility_id = cur.fetchone()[0]
        if utility_id is None:
            self.skipTest("la matrice non ammette nessuna utility per EF su questo DB")
        return int(utility_id)

    def test_lista_dal_bb(self) -> None:
        self._apri_admin()
        elenco = self.svc.list_records(self.emittente_id)
        # L'ordine lo fissa la query del repository (per descrizione), non il BB.
        chiavi = [(r["utility_descrizione"], r["utility_id"]) for r in elenco]
        self.assertEqual(sorted(chiavi), chiavi)
        righe = self._righe()
        self.assertTrue(righe, "la matrice ammette almeno un'utility per EF")
        for r in righe.values():
            with self.subTest(utility=r["utility_codice"]):
                # L'azienda di prova gestisce ogni utility ammessa, senza parametri.
                self.assertTrue(r["gestita"])
                self.assertIsNotNone(r["record_id"])
                self.assertFalse(r["personalizzata"])
                self.assertIsNone(r["arrotondamento_importi_dec"])
                # Il BB da' comunque i parametri effettivi (azienda, poi sistema).
                self.assertIsNotNone(r["effettivo_arrotondamento_importi_dec"])
                self.assertIsNotNone(r["effettivo_metodo_arrotondamento_importi"])
                self.assertFalse(r["can_attivare"])
                self.assertTrue(r["can_remove"])

    def test_attiva_senza_parametri_e_toglie(self) -> None:
        self._apri_admin()
        riga = self._una_gestita()
        self.assertEqual(
            {"deleted": True}, self.svc.elimina_record(self.emittente_id, riga["record_id"]),
        )
        tolta = self._righe()[riga["utility_id"]]
        self.assertFalse(tolta["gestita"])
        self.assertIsNone(tolta["record_id"])
        self.assertTrue(tolta["can_attivare"])

        nuovo = self.svc.crea_record(self.emittente_id, {"utility_id": riga["utility_id"]})
        riattivata = self._righe()[riga["utility_id"]]
        self.assertEqual(nuovo["id"], riattivata["record_id"])
        self.assertTrue(riattivata["gestita"])

    def test_parametri_a_null(self) -> None:
        self._apri_admin()
        riga = self._una_gestita()
        self.svc.aggiorna_record(
            self.emittente_id, riga["record_id"],
            {"arrotondamento_importi_dec": 0, "metodo_arrotondamento_importi": "HALF_DOWN"},
        )
        scritta = self._righe()[riga["utility_id"]]
        self.assertTrue(scritta["personalizzata"])
        self.assertTrue(scritta["can_reset"])
        self.assertEqual(0, scritta["effettivo_arrotondamento_importi_dec"])

        self.svc.aggiorna_record(
            self.emittente_id, riga["record_id"],
            {"arrotondamento_importi_dec": None, "metodo_arrotondamento_importi": None},
        )
        tornata = self._righe()[riga["utility_id"]]
        self.assertFalse(tornata["personalizzata"])
        self.assertIsNone(tornata["arrotondamento_importi_dec"])
        self.assertTrue(tornata["gestita"], "i parametri a NULL non tolgono l'utility")

    def test_in_uso_non_si_toglie(self) -> None:
        utility_id = self._prima_utility()
        with connection.cursor() as cur:
            # Il cliente lo crea l'operatore dell'azienda (RLS del billing
            # account): il legame lo scrive il trigger verso il suo emittente.
            apri_contesto_su(cur, self.operatore)
            cur.execute(
                "SELECT billing_account_id FROM dbops.fn_pgtap_crea_cliente_ba('UTG uso', %s)",
                [utility_id],
            )
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self._apri_admin()
        riga = self._righe()[utility_id]
        # Il savepoint tiene viva la transazione del test dopo il rifiuto.
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            self.svc.elimina_record(self.emittente_id, riga["record_id"])
        self.assertEqual("E_ANAG_FK", ctx.exception.code)
        self.assertIn("non si puo' togliere", ctx.exception.message)
        self.assertTrue(self._righe()[riga["utility_id"]]["gestita"])

    def test_attivo_rifiutato(self) -> None:
        self._apri_admin()
        riga = self._una_gestita()
        with self.assertRaises(ServiceError) as ctx:
            self.svc.aggiorna_record(self.emittente_id, riga["record_id"], {"attivo": False})
        self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)
