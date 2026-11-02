# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il contesto di stampa di ciascuno dei sei documenti di vendita non
#        porta JSON rimasto TESTO, sul DATABASE VERO: `meta` della testata e
#        delle righe, `utility.meta`, i `componenti` del contratto arrivano
#        come oggetti e liste. Fino al 2026-10-28 cinque builder su sei li
#        passavano come stringa (un `{% for %}` su `componenti` avrebbe
#        scorso i caratteri); ora li decodifica il lettore comune
#        (brief-modello-documento-vendita §15.17.3).
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1`. Ogni documento si COSTRUISCE con la
#       sua fixture, in un savepoint suo (un builder rotto non nasconde gli
#       altri). Transazione ANNULLATA. ⭐ Si guarda TUTTO il contesto, non le
#       chiavi note: una colonna jsonb nuova non deve poter tornare testo.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) JsonbContestiStampaDbTests.test_nessun_json_rimasto_testo
   un sotto-caso per builder: PREVENTIVO, OFFERTA_COMMERCIALE, CONTRATTO,
   ORDINE_VENDITA, DDT_VENDITA, FATTURA.
"""
from __future__ import annotations

import json
import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, apri_transazione_annullata, richiedi_db_provvisto

# Il documento di ciascun builder: SQL che torna il suo id (e apre il
# contesto del suo operatore, come ogni fixture).
_DOCUMENTI: dict[str, tuple[str, ...]] = {
    "PREVENTIVO": (
        "SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo_con_righe('jsonb stampa')",
    ),
    "ORDINE_VENDITA": (
        "SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine_con_righe('jsonb stampa')",
    ),
    "DDT_VENDITA": (
        "SELECT ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('jsonb stampa')",
    ),
    "CONTRATTO": (
        "SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('jsonb stampa')",
    ),
    "FATTURA": (
        "SELECT fattura_id FROM dbops.fn_pgtap_crea_fattura('jsonb stampa')",
    ),
    "OFFERTA_COMMERCIALE": (
        "CREATE TEMP TABLE _jm AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('JSONBST')",
        "CREATE TEMP TABLE _jl AS SELECT * FROM dbops.fn_pgtap_crea_listino("
        " (SELECT utility_id FROM _jm), 'JSONBST')",
        "INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,"
        " istanza_utility_id, utility_id, listino_id, validita_dal)"
        " SELECT m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id, m.utility_id,"
        " (SELECT listino_id FROM _jl), script.fn_data_operativa()"
        " FROM _jm m RETURNING id",
    ),
}


# Scopo: i percorsi delle stringhe che sono un oggetto o una lista JSON.
def _json_rimasto_testo(valore: Any, percorso: str = "") -> list[str]:
    if isinstance(valore, dict):
        return [p for k, v in valore.items() for p in _json_rimasto_testo(v, f"{percorso}.{k}")]
    if isinstance(valore, list):
        return [p for i, v in enumerate(valore) for p in _json_rimasto_testo(v, f"{percorso}[{i}]")]
    if isinstance(valore, str) and valore[:1] in "{[":
        try:
            json.loads(valore)
        except ValueError:
            return []
        return [percorso]
    return []


class JsonbContestiStampaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    def test_nessun_json_rimasto_testo(self) -> None:
        from apps.documenti.services.context_builders import get_builder

        for codice, passi in _DOCUMENTI.items():
            with self.subTest(builder=codice):
                try:
                    with transaction.atomic(), connection.cursor() as cur:
                        for passo in passi:
                            cur.execute(passo)
                        documento_id = cur.fetchone()[0]
                        contesto = get_builder(codice).build_context(documento_id)
                        self.assertEqual(_json_rimasto_testo(contesto), [])
                        raise Annulla
                except Annulla:
                    pass
