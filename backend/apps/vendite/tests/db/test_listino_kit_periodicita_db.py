# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il KIT sulla versione di listino (`vendite.listini_kit`, D-2-bis (B) di
#        brief-db-contratto-righe-periodiche-in-commessa §7.2, §7.7 punto 2) dal
#        lato del backend, sul DATABASE PROVVISTO: la periodicita' del kit si
#        scrive, si cambia e si toglie dal service; la lista delle righe la
#        porta sulla riga del composito; l'eliminazione del bundle porta via
#        anche il kit; i rifiuti del DB arrivano col loro codice e col campo.
#        E' la giuntura Python↔PL/pgSQL che i test con i mock non vedono.
# Note: ⚠️ Le REGOLE (solo in bozza, solo su un composito, attivazione) le prova
#       il pgTAP `vendite/test-listino-kit-e-periodicita-v1`. Il mondo si
#       COSTRUISCE: `fn_pgtap_crea_listino` da' una versione ATTIVA; la BOZZA la
#       crea il test, col kit (due componenti) e un articolo semplice.
#       Transazione ANNULLATA, ogni rifiuto atteso in un SAVEPOINT.
#       Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ListinoKitPeriodicitaDbTests.test_scrive_cambia_e_toglie
2) ListinoKitPeriodicitaDbTests.test_la_lista_la_porta_sul_composito
3) ListinoKitPeriodicitaDbTests.test_eliminare_il_bundle_porta_via_il_kit
4) ListinoKitPeriodicitaDbTests.test_un_articolo_semplice_e_rifiutato
5) ListinoKitPeriodicitaDbTests.test_fuori_vocabolario_e_un_errore_sul_campo
6) ListinoKitPeriodicitaDbTests.test_fuori_bozza_e_rifiutato
7) ListinoKitPeriodicitaDbTests.test_il_lettore_dell_espansore_si_lega_alla_funzione
"""
from __future__ import annotations

import unittest
from datetime import timedelta
from typing import Any
from uuid import uuid4

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.db.listini_repository import ListiniRepository
from apps.vendite.services.listini_service import (
    fn_delete_bundle,
    fn_list_righe,
    fn_save_kit_periodicita,
)


class ListinoKitPeriodicitaDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sulla tabella del giro: un DB indietro si salta, non fallisce.
        richiedi_db_provvisto("vendite.fn_listino_periodicita_articolo(bigint, uuid)")

    # Scopo: un listino con la versione ATTIVA (V1) e una BOZZA (V2) con un kit
    #        a prezzi bundle (due componenti) e un articolo semplice.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        repo = ListiniRepository()
        sfx = uuid4().hex[:8].upper()
        with connection.cursor() as cur:
            cur.execute(
                "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente(%s)",
                [f"kit listino {sfx}"],
            )
            cur.execute(
                "SELECT l.listino_id, l.listino_versione_id, l.tipologia_id, script.fn_data_operativa() AS oggi"
                "  FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _mondo), %s) l",
                [f"kit listino {sfx}"],
            )
            mondo = row_to_dict(cur)
            assert mondo is not None
            articoli: dict[str, str] = {}
            for s in ("K", "F1", "F2", "S"):
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_articolo(%s, p_listino_tipologia_id => %s::smallint,"
                    " p_is_composito => %s)::text",
                    [f"LSKIT-{s}-{sfx}", mondo["tipologia_id"], s == "K"],
                )
                articoli[s] = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)"
                " VALUES (%s, %s, 2, '2020-01-01'), (%s, %s, 1, '2020-01-01')",
                [articoli["K"], articoli["F1"], articoli["K"], articoli["F2"]],
            )
        self.listino_id = int(mondo["listino_id"])
        self.v1 = int(mondo["listino_versione_id"])
        self.kit, self.semplice = articoli["K"], articoli["S"]
        v2_dal = mondo["oggi"] + timedelta(days=30)
        self.v2_dal = v2_dal
        self.v2 = repo.create_versione(
            self.listino_id, {"codice_versione": f"V2-{sfx}", "valido_dal": v2_dal},
        )
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,"
                "       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)"
                " SELECT %s, ac.id, ac.prodotto_id, ac.componente_id, 10, %s"
                "   FROM catalogo.articoli_componenti ac WHERE ac.prodotto_id = %s",
                [self.v2, v2_dal, self.kit],
            )

    def _periodicita_a_db(self, versione_id: int) -> str | None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT periodicita FROM vendite.listini_kit"
                " WHERE listino_versione_id = %s AND articolo_padre_id = %s",
                [versione_id, self.kit],
            )
            row = cur.fetchone()
        return row[0] if row else None

    def _rifiuto(self, chiamata: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            chiamata()
        return cm.exception

    # 1. Un codice la scrive (in maiuscolo), un altro la cambia, null la toglie.
    def test_scrive_cambia_e_toglie(self) -> None:
        esito = fn_save_kit_periodicita(self.listino_id, self.v2, self.kit, {"periodicita": "trimestrale"})
        self.assertEqual(esito["periodicita"], "TRIMESTRALE")
        self.assertEqual(self._periodicita_a_db(self.v2), "TRIMESTRALE")
        fn_save_kit_periodicita(self.listino_id, self.v2, self.kit, {"periodicita": "ANNUALE"})
        self.assertEqual(self._periodicita_a_db(self.v2), "ANNUALE")
        esito = fn_save_kit_periodicita(self.listino_id, self.v2, self.kit, {"periodicita": None})
        self.assertIsNone(esito["periodicita"])
        self.assertIsNone(self._periodicita_a_db(self.v2))

    # 2. La riga del composito nella lista porta la periodicita' del kit.
    def test_la_lista_la_porta_sul_composito(self) -> None:
        fn_save_kit_periodicita(self.listino_id, self.v2, self.kit, {"periodicita": "SEMESTRALE"})
        righe, _ = fn_list_righe(self.listino_id, self.v2)
        kit = [r for r in righe if r["is_composito"] and str(r["articolo_id"]) == self.kit]
        self.assertEqual(len(kit), 1)
        self.assertEqual(kit[0]["periodicita"], "SEMESTRALE")

    # 3. Eliminare i prezzi bundle toglie anche il kit dalla versione.
    def test_eliminare_il_bundle_porta_via_il_kit(self) -> None:
        fn_save_kit_periodicita(self.listino_id, self.v2, self.kit, {"periodicita": "MENSILE"})
        fn_delete_bundle(self.listino_id, self.v2, self.kit)
        self.assertIsNone(self._periodicita_a_db(self.v2))

    # 4. Un articolo semplice non ha un kit: la sua periodicita' e' sulla riga.
    def test_un_articolo_semplice_e_rifiutato(self) -> None:
        errore = self._rifiuto(lambda: fn_save_kit_periodicita(
            self.listino_id, self.v2, self.semplice, {"periodicita": "MENSILE"},
        ))
        self.assertEqual(errore.code, "E_LISTINO_KIT_NON_COMPOSITO")

    # 5. Un codice fuori vocabolario e' la FK, tradotta sul campo.
    def test_fuori_vocabolario_e_un_errore_sul_campo(self) -> None:
        errore = self._rifiuto(lambda: fn_save_kit_periodicita(
            self.listino_id, self.v2, self.kit, {"periodicita": "OGNI_TANTO"},
        ))
        self.assertEqual(errore.context.get("field"), "periodicita")

    # 6. Fuori dalla bozza il kit non si scrive: parla il guard del DB.
    def test_fuori_bozza_e_rifiutato(self) -> None:
        errore = self._rifiuto(lambda: fn_save_kit_periodicita(
            self.listino_id, self.v1, self.kit, {"periodicita": "MENSILE"},
        ))
        self.assertEqual(errore.code, "E_RIGA_LISTINO_VERSIONE_CHIUSA")

    # 7. Il lettore dell'espansore dei kit (D-2 (c)) chiama la funzione del DB
    #    con la sua firma: un contratto che non c'e' non da' componenti, senza
    #    errori. Il contenuto lo prova il pgTAP (componenti e prezzo del kit).
    def test_il_lettore_dell_espansore_si_lega_alla_funzione(self) -> None:
        righe = ContrattiRepository().list_componenti_kit_dal_listino(
            contratto_uid=str(uuid4()), articolo_padre_id=self.kit, data=self.v2_dal,
        )
        self.assertEqual(righe, [])
