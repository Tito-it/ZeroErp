# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La variazione percentuale dei prezzi di una versione di listino sul
#        DATABASE PROVVISTO, dal lato del backend (BE-L7, 2026-11-15): il
#        service chiama UNA volta il verbo `vendite.fn_varia_prezzi_versione_listino`
#        e ne riporta le righe coi nomi del verbo. E' la giuntura Python↔PL/pgSQL
#        (firma, tipi, nomi delle colonne, codici) che i test del service, coi
#        mock, non vedono.
# Note: ⚠️ Le REGOLE (bozza anche a righe zero, intervalli, perimetro, traccia)
#       le prova il pgTAP `vendite/test-listino-variazione-percentuale-v1`.
#       Il mondo come in `test_listino_versione_modello_db.py`: V1 ATTIVA da
#       `fn_pgtap_crea_listino`, V2 in BOZZA creata qui con un prezzo.
#       Transazione ANNULLATA, ogni rifiuto atteso in un SAVEPOINT. Opt-in
#       `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) VariazionePercentualeDbTests.test_l_anteprima_porta_i_nomi_del_verbo_e_non_scrive
2) VariazionePercentualeDbTests.test_il_gesto_scrive_prezzi_e_traccia
3) VariazionePercentualeDbTests.test_fuori_dalla_bozza_rifiuta_anche_a_righe_zero
4) VariazionePercentualeDbTests.test_l_intervallo_e_del_verbo_col_suo_campo
"""
from __future__ import annotations

import unittest
from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.listini_repository import ListiniRepository
from apps.vendite.services.listini_service import fn_applica_variazione_percentuale


class VariazionePercentualeDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sul verbo: un DB indietro fallisce sull'oggetto mancante.
        richiedi_db_provvisto(
            "vendite.fn_varia_prezzi_versione_listino(bigint, numeric, integer, uuid[], boolean)",
        )

    # Scopo: il listino con la versione ATTIVA (V1) e una BOZZA (V2) con un
    #        prezzo di 10, che decorre fra 30 giorni.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = ListiniRepository()
        sfx = uuid4().hex[:8].upper()
        with connection.cursor() as cur:
            cur.execute(
                "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente(%s)",
                [f"variazione listino {sfx}"],
            )
            cur.execute(
                "SELECT l.listino_id, l.listino_versione_id, l.tipologia_id, script.fn_data_operativa() AS oggi"
                "  FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _mondo), %s) l",
                [f"variazione listino {sfx}"],
            )
            mondo = row_to_dict(cur)
            assert mondo is not None
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, false, p_listino_tipologia_id => %s::smallint)",
                [f"LSVAR-{sfx}", mondo["tipologia_id"]],
            )
            articolo = cur.fetchone()[0]
            cur.execute("SELECT id::text, uom_id FROM catalogo.articoli WHERE id = %s", [articolo])
            self.articolo_id, uom_id = cur.fetchone()
        self.listino_id = int(mondo["listino_id"])
        self.v1 = int(mondo["listino_versione_id"])
        self.v2 = self.repo.create_versione(self.listino_id, {
            "codice_versione": f"V2-{sfx}", "valido_dal": mondo["oggi"] + timedelta(days=30),
        })
        self.repo.create_riga(self.v2, {
            "articolo_id": self.articolo_id, "uom_id": uom_id, "prezzo": Decimal("10"),
        })

    def _prezzo(self, versione_id: int) -> Decimal:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT prezzo FROM vendite.listini_righe"
                " WHERE listino_versione_id = %s AND attivo IS TRUE",
                [versione_id],
            )
            return cur.fetchone()[0]

    def _rifiuto(self, versione_id: int, corpo: dict[str, Any]) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            fn_applica_variazione_percentuale(self.listino_id, versione_id, corpo)
        return cm.exception

    # 1. L'anteprima: una riga coi nomi del verbo, il prezzo calcolato, e il
    #    prezzo salvato che non cambia.
    def test_l_anteprima_porta_i_nomi_del_verbo_e_non_scrive(self) -> None:
        esito = fn_applica_variazione_percentuale(self.listino_id, self.v2, {
            "variazione_percentuale": 10, "arrotondamento_decimali": 2, "dry_run": True,
        })
        self.assertTrue(esito["dry_run"])
        self.assertEqual(esito["righe_coinvolte"], 1)
        riga = esito["preview"][0]
        self.assertEqual(
            set(riga),
            {"listino_riga_id", "articolo_id", "articolo_codice", "articolo_descrizione",
             "prezzo_precedente", "prezzo_nuovo"},
        )
        self.assertEqual(str(riga["articolo_id"]), self.articolo_id)
        self.assertEqual(Decimal(riga["prezzo_precedente"]), Decimal("10"))
        self.assertEqual(Decimal(riga["prezzo_nuovo"]), Decimal("11"))
        self.assertEqual(self._prezzo(self.v2), Decimal("10"))

    # 2. Il gesto: il prezzo salvato e' quello nuovo, e la traccia sta in
    #    `meta.variazioni_percentuali[]` della versione (la scrive il verbo).
    def test_il_gesto_scrive_prezzi_e_traccia(self) -> None:
        esito = fn_applica_variazione_percentuale(self.listino_id, self.v2, {
            "variazione_percentuale": -50, "arrotondamento_decimali": 2,
        })
        self.assertEqual(esito["righe_aggiornate"], 1)
        self.assertEqual(self._prezzo(self.v2), Decimal("5"))
        versione = self.repo.get_versione(self.listino_id, self.v2)
        assert versione is not None
        traccia = (versione.get("meta") or {}).get("variazioni_percentuali") or []
        self.assertEqual(len(traccia), 1)
        self.assertEqual(traccia[0]["righe_aggiornate"], 1)

    # 3. Fuori dalla bozza rifiuta la VERSIONE, anche quando il filtro non
    #    prende nessuna riga e in anteprima. Fino al 2026-11-15 l'anteprima a
    #    righe zero passava e il gesto cadeva sulla traccia in meta, col codice
    #    del campo non modificabile.
    def test_fuori_dalla_bozza_rifiuta_anche_a_righe_zero(self) -> None:
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run):
                errore = self._rifiuto(self.v1, {
                    "variazione_percentuale": 3, "filtro_articoli": [], "dry_run": dry_run,
                })
                self.assertEqual(errore.code, "E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA")

    # 4. L'intervallo e' del verbo: il codice suo, col campo che lo viola.
    def test_l_intervallo_e_del_verbo_col_suo_campo(self) -> None:
        for corpo, campo in (
            ({"variazione_percentuale": 1500}, "variazione_percentuale"),
            ({"variazione_percentuale": 3, "arrotondamento_decimali": 11}, "arrotondamento_decimali"),
        ):
            with self.subTest(campo=campo):
                errore = self._rifiuto(self.v2, {**corpo, "dry_run": True})
                self.assertEqual(errore.code, "E_LISTINO_VARIAZIONE_FUORI_INTERVALLO")
                self.assertIn(campo, errore.fields or ())
        self.assertEqual(self._prezzo(self.v2), Decimal("10"))
