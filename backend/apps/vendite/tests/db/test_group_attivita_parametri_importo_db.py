# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il gruppo delle attivita' fatturabili (`_GROUP_ATTIVITA_SELECT` di
#        `VenditePipelineRepository`) legge decimali e metodo dell'IMPORTO dal
#        BB del DB `vendite.fn_parametri_importo_riga` (brief-db-modelli-
#        documento-standard §10.9 R-3, voce B-7), col DB vero.
# Note: ⭐ PERCHE' SUL DB. La catena (regola dell'articolo, poi i parametri
#       effettivi dell'emittente per l'utility della fattura, poi il sistema)
#       e' tutta nel database, e un mock del repository non la vede: fino al
#       2026-10-21 qui c'erano i letterali `COALESCE(…, 2)` / `'HALF_UP'`, e un
#       emittente con parametri suoi raggruppava a 2 decimali mentre il trigger
#       della riga arrotondava coi suoi.
#       ⚠️ Il mondo si COSTRUISCE (regola zero): azienda, cliente e commessa
#       dagli helper `dbops.fn_pgtap_*`, un articolo senza regole, l'override
#       dell'emittente scritto dal test. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso
#       in CI); tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) GroupAttivitaParametriImportoDbTests.test_override_dell_emittente_arriva_al_gruppo
   senza regole dell'articolo, l'attivita' prende 0 decimali e HALF_DOWN
   dall'override dell'emittente per l'utility; tolto l'override, i parametri
   di sistema — in entrambi i casi quelli del BB del DB, non un letterale.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto
from apps.vendite.db.pipeline_repository import VenditePipelineRepository


class GroupAttivitaParametriImportoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("vendite.fn_parametri_importo_riga(uuid, bigint, integer)")

    # Scopo: costruisce commessa, riga e attivita' fatturabile; torna
    #        (attivita_id, articolo_id, emittente_sr_id, utility_id).
    def _attivita(self, cur) -> tuple[int, str, int, int]:
        cur.execute("CREATE TEMP TABLE _c AS SELECT * FROM dbops.fn_pgtap_crea_commessa('BE-R3')")
        cur.execute(
            "CREATE TEMP TABLE _a AS SELECT a.* FROM _c,"
            " dbops.fn_pgtap_crea_commessa_attivita(_c.commessa_id) a"
        )
        # Nessuna regola dell'articolo: e' il ramo che leggeva il letterale.
        cur.execute(
            "DELETE FROM vendite.articolo_regole_fatturazione r USING _a"
            " WHERE r.articolo_id = _a.articolo_id"
        )
        cur.execute(
            """
            INSERT INTO vendite.attivita_fatturabili (
                articolo_id, istanza_utility_id, billing_account_id, data_attivita,
                competenza_mese, competenza_dal, competenza_al, quantita,
                commessa_id, commessa_attivita_id, uom_id, prezzo_unitario)
            SELECT _a.articolo_id, _c.istanza_utility_id, _c.billing_account_id,
                   _a.competenza_dal, date_trunc('month', _a.competenza_dal)::date,
                   _a.competenza_dal, _a.competenza_al, 1,
                   _c.commessa_id, _a.attivita_id, _a.uom_id, 10
              FROM _c, _a
            RETURNING id
            """
        )
        attivita_id = cur.fetchone()[0]
        cur.execute(
            "SELECT _a.articolo_id::text, _c.emittente_soggetto_ruolo_id, _c.utility_id"
            "  FROM _c, _a"
        )
        articolo_id, emittente_sr_id, utility_id = cur.fetchone()
        return int(attivita_id), articolo_id, int(emittente_sr_id), int(utility_id)

    # 1. L'override dell'emittente arriva al gruppo; senza, il sistema.
    def test_override_dell_emittente_arriva_al_gruppo(self):
        repo = VenditePipelineRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                attivita_id, articolo_id, emittente_sr_id, utility_id = self._attivita(cur)
                # La matrice ruoli-utility si costruisce (sullo scratch, come in
                # CI, e' vuota): l'utility ammessa per cliente ed emittente.
                cur.execute(
                    """
                    INSERT INTO config.utilities_tipi_ruolo (utility_id, tipo_ruolo_id)
                    SELECT %s, tr.id FROM config.tipi_ruoli tr
                     WHERE tr.codice_interno IN ('CL', 'EF')
                       AND NOT EXISTS (SELECT 1 FROM config.utilities_tipi_ruolo x
                                        WHERE x.utility_id = %s AND x.tipo_ruolo_id = tr.id
                                          AND x.attivo)
                    """,
                    [utility_id, utility_id],
                )
                cur.execute(
                    "DELETE FROM anagrafiche.emittenti_fiscali_utilities"
                    " WHERE emittente_soggetto_ruolo_id = %s AND utility_id = %s",
                    [emittente_sr_id, utility_id],
                )

                # a) senza override: i parametri di sistema, letti dal BB.
                cur.execute(
                    "SELECT arrotondamento_importi_dec, metodo_arrotondamento_importi"
                    "  FROM vendite.fn_parametri_importo_riga(%s::uuid, %s, %s)",
                    [articolo_id, emittente_sr_id, utility_id],
                )
                atteso_sistema = cur.fetchone()
                gi = repo.batch_get_group_attivita_inputs([attivita_id])[attivita_id]
                self.assertEqual(
                    (gi.arrotondamento_importi_dec, gi.metodo_arrotondamento_importi),
                    (int(atteso_sistema[0]), atteso_sistema[1]),
                )

                # b) l'emittente arrotonda a 0 decimali, HALF_DOWN: il gruppo lo
                #    vede (col letterale di prima sarebbe stato 2 / HALF_UP).
                cur.execute(
                    """
                    INSERT INTO anagrafiche.emittenti_fiscali_utilities
                        (emittente_soggetto_ruolo_id, utility_id, arrotondamento_importi_dec,
                         metodo_arrotondamento_importi, attivo)
                    VALUES (%s, %s, 0, 'HALF_DOWN', true)
                    """,
                    [emittente_sr_id, utility_id],
                )
                gi = repo.batch_get_group_attivita_inputs([attivita_id])[attivita_id]
                self.assertEqual(gi.arrotondamento_importi_dec, 0)
                self.assertEqual(gi.metodo_arrotondamento_importi, "HALF_DOWN")
                # Le quantita' restano della copia unica del BE.
                self.assertEqual(gi.arrotondamento_quantita_dec, 3)
                # La lettura singola passa dalla stessa proiezione.
                singola = repo.get_group_attivita_input(attivita_id)
                assert singola is not None
                self.assertEqual(singola.arrotondamento_importi_dec, 0)
                raise Annulla
        except Annulla:
            pass
