# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'assegnazione di un ruolo con indirizzi obbligatori
#        (`POST /soggetti/{id}/ruoli/`, `SoggettiService.assign_ruolo`) sul
#        DATABASE VERO: gli indirizzi del payload diventano indirizzi DEL
#        RUOLO, e il guard differito
#        `trgfn_soggetti_ruoli_guard_indirizzi_required` e' soddisfatto.
# Note: ⛔ Fino al 2026-10-09 l'endpoint non accettava indirizzi: per CL, FO e
#       GE (matrice `config.tipi_ruolo_tipi_indirizzo` con obbligatori)
#       rispondeva sempre E_INDIRIZZO_OBBLIGATORIO_MANCANTE — lo smoke soggetti
#       lo «saltava» come configurazione. I test mockati non vedono il guard.
#       Si prova sul GESTORE (SEDELEG + FATT su una societa'): CL, FO, EF e
#       RIS_UMANA hanno un flusso dedicato e da qui si rifiutano.
#       ⚠️ Il guard e' DIFFERITO al COMMIT, e la transazione del test si
#       annulla: lo si fa scattare con `SET CONSTRAINTS ALL IMMEDIATE`.
#       ⚠️ Il mondo si COSTRUISCE (`fn_pgtap_crea_soggetto_pg`,
#       `fn_pgtap_crea_indirizzo_dettaglio`), in transazione ANNULLATA.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) AssegnaRuoloIndirizziDbTests.test_gestore_con_un_indirizzo_nasce_con_quelli_obbligatori
2) AssegnaRuoloIndirizziDbTests.test_gestore_senza_indirizzi_rifiutato_dal_guard
3) AssegnaRuoloIndirizziDbTests.test_cliente_rimanda_al_flusso_clienti
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto


class AssegnaRuoloIndirizziDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto ruolo indirizzi')")
            self.soggetto_id = str(cur.fetchone()[0])
            cur.execute("SELECT dbops.fn_pgtap_crea_indirizzo_dettaglio('ruolo indirizzi')")
            self.dettaglio_id = cur.fetchone()[0]
            # I builder escono coi vincoli IMMEDIATE: si torna a quelli di una
            # transazione nuova, col guard degli indirizzi rimandato al COMMIT.
            cur.execute("SET CONSTRAINTS ALL DEFERRED")

    # Scopo: i vincoli differiti, controllati adesso (al posto del COMMIT).
    @staticmethod
    def _commit_simulato() -> None:
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    # 1. Un indirizzo solo (SEDELEG): l'obbligatorio FATT e' clonato, sul RUOLO.
    def test_gestore_con_un_indirizzo_nasce_con_quelli_obbligatori(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        ruolo = SoggettiService().assign_ruolo(self.soggetto_id, {
            "codice_ruolo": "GESTORE",
            "indirizzi": [{"tipo_indirizzo_codice_interno": "SEDELEG", "indirizzo_dettaglio_id": self.dettaglio_id}],
        })
        self._commit_simulato()
        with connection.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(ti.codice_interno, ti.codice) "
                "  FROM anagrafiche.indirizzi i "
                "  JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id "
                " WHERE i.soggetto_ruolo_id = %s ORDER BY 1",
                [ruolo["id"]],
            )
            self.assertEqual([r[0] for r in cur.fetchall()], ["FATT", "SEDELEG"])

    # 2. Senza indirizzi il ruolo non puo' nascere: lo dice il guard, al commit.
    def test_gestore_senza_indirizzi_rifiutato_dal_guard(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        try:
            with transaction.atomic():
                SoggettiService().assign_ruolo(self.soggetto_id, {"codice_ruolo": "GESTORE"})
                self._commit_simulato()
        except Exception as exc:  # la strada e' cio' che si prova
            self.assertEqual(ErrorTranslator.to_api_error(exc).code, "E_INDIRIZZO_OBBLIGATORIO_MANCANTE")
            return
        self.fail("ruolo GESTORE senza indirizzi accettato")

    # 3. Il cliente ha il suo flusso: da qui rifiuto sul campo, senza scritture.
    def test_cliente_rimanda_al_flusso_clienti(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        try:
            SoggettiService().assign_ruolo(self.soggetto_id, {"codice_ruolo": "CLIENTE"})
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual((api.code, api.fields), ("E_ANAG_VALIDAZIONE", ("codice_ruolo",)))
            # La descrizione viene da `config.tipi_ruoli`, non dal codice Python.
            self.assertIn("Cliente", api.message)
        else:
            self.fail("ruolo CLIENTE assegnato dall'endpoint generico")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM anagrafiche.soggetti_ruoli sr "
                "  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id "
                " WHERE sr.soggetto_id = %s AND tr.codice_interno = 'CL'",
                [self.soggetto_id],
            )
            self.assertEqual(cur.fetchone()[0], 0)
