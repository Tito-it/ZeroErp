# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I picker dei tipi di indirizzo (R-2 di brief-db-copia-indirizzo-
#        soggetto, 2026-11-15) provati sul DATABASE VERO: il binding delle
#        quattro funzioni `anagrafiche.fn_tipi_indirizzo_proponibili_*` (firma,
#        cast, colonne del `RETURNS TABLE` sotto `WITH ORDINALITY`) e il loro
#        contratto letto dal backend: un tipo gia' presente resta nell'elenco,
#        spento col motivo della check che la madre di creazione solleva.
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il caso «tipo gia'
#       presente» si COSTRUISCE: si sceglie un tipo che il picker ammette, lo si
#       crea dalla porta dell'applicazione e si rilegge. Nessun test dipende da
#       quali tipi ha la matrice di oggi.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SoggettoPickerDbTests.test_il_tipo_creato_si_spegne_col_motivo — prima ammesso, dopo la
   creazione `ammesso` falso con `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE`, la chiave i18n e il tipo
2) SoggettoPickerDbTests.test_soggetto_e_natura_differiscono_solo_per_i_tipi_presenti — il soggetto
   e la sua natura propongono gli stessi tipi, salvo quelli che il soggetto ha gia' (spenti col
   motivo del tipo presente, ammessi dalla natura)
3) SoggettoPickerDbTests.test_prima_gli_ammessi — l'ordine della funzione arriva al client
4) RuoloPickerDbTests.test_il_tipo_creato_si_spegne_col_motivo — lo stesso sul ruolo,
   `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`
5) RuoloPickerDbTests.test_il_tipo_di_ruolo_marca_gli_obbligatori — il picker del tipo di ruolo
   segna obbligatori le righe obbligatorie della matrice (seed: contratto) e le ammette
6) RuoloPickerDbTests.test_codice_di_ruolo_sconosciuto — elenco vuoto, non «tutti ammessi»
7) RuoloPickerDbTests.test_ruolo_inesistente — 404 `E_ANAG_NOT_FOUND`
"""

from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

_CHIAVI = {
    "tipo_indirizzo_id", "codice", "codice_interno", "descrizione", "obbligatorio",
    "ammesso", "motivo_codice", "reason", "reason_key", "reason_valori", "motivi",
}


class _Mondo(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)

    @staticmethod
    def _soggetto_pg(nome: str) -> str:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg(%s)", [nome])
            return str(cur.fetchone()[0])

    # La forma estera: la sola che non chiede comune, CAP o via del catalogo.
    def _payload(self, tipo: str) -> dict:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM config.stati WHERE NOT catalogo_comuni_completo ORDER BY id LIMIT 1"
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("Nessuno stato senza catalogo dei comuni.")
        return {
            "tipo_indirizzo_codice_interno": tipo, "indirizzo_libero": "Via picker 1",
            "stato_id": int(riga[0]), "locality": "Prova", "postal_code": "PK1",
        }

    def _primo_ammesso(self, righe: list[dict]) -> dict:
        ammessi = [r for r in righe if r["ammesso"]]
        if not ammessi:
            self.skipTest("Nessun tipo di indirizzo ammesso: niente da creare.")
        return ammessi[0]

    def _verifica_spento(self, righe: list[dict], tipo: dict, codice: str) -> None:
        riga = next(r for r in righe if r["codice_interno"] == tipo["codice_interno"])
        self.assertEqual(
            (False, codice, "anagrafiche.indirizzi.tipo_blocco.gia_presente", [tipo["descrizione"]]),
            (riga["ammesso"], riga["motivo_codice"], riga["reason_key"], riga["reason_valori"]),
        )


class SoggettoPickerDbTests(_Mondo):

    def test_il_tipo_creato_si_spegne_col_motivo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        servizio = SoggettiService()
        soggetto_id = self._soggetto_pg("Picker soggetto e2e")
        prima = servizio.get_tipi_indirizzo_proponibili_soggetto(soggetto_id)
        self.assertTrue(prima)
        self.assertEqual(_CHIAVI, set(prima[0]))
        tipo = self._primo_ammesso(prima)

        servizio.create_indirizzo_soggetto(soggetto_id, self._payload(tipo["codice_interno"]))

        self._verifica_spento(
            servizio.get_tipi_indirizzo_proponibili_soggetto(soggetto_id), tipo,
            "E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE",
        )

    # ⚠️ Il builder crea il soggetto con gli indirizzi che la sua natura pretende
    #    (la sede legale di una PG): il soggetto non e' vuoto, e le due proposte
    #    divergono proprio su quei tipi.
    def test_soggetto_e_natura_differiscono_solo_per_i_tipi_presenti(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        from apps.core.db.lookup_repository import LookupRepository

        soggetto_id = self._soggetto_pg("Picker natura e2e")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT tipo_soggetto_dettaglio_id FROM anagrafiche.soggetti WHERE id = %s::uuid",
                [soggetto_id],
            )
            natura_id = cur.fetchone()[0]
            cur.execute(
                "SELECT ti.codice_interno FROM anagrafiche.indirizzi_soggetti i"
                "  JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id"
                " WHERE i.soggetto_id = %s::uuid",
                [soggetto_id],
            )
            presenti = {r[0] for r in cur.fetchall()}
        dal_soggetto = {
            r["codice_interno"]: r
            for r in SoggettiService().get_tipi_indirizzo_proponibili_soggetto(soggetto_id)
        }
        dalla_natura = {
            r["codice_interno"]: r
            for r in LookupRepository().list_tipi_indirizzo_proponibili("natura", natura_id)
        }
        self.assertEqual(set(dal_soggetto), set(dalla_natura))
        for codice, r in dal_soggetto.items():
            with self.subTest(tipo=codice):
                n = dalla_natura[codice]
                self.assertEqual(r["obbligatorio"], n["obbligatorio"])
                if codice in presenti:
                    self.assertEqual(
                        (False, "E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE", True),
                        (r["ammesso"], r["motivo_codice"], n["ammesso"]),
                    )
                else:
                    self.assertEqual((n["ammesso"], n["motivo_codice"]), (r["ammesso"], r["motivo_codice"]))

    def test_prima_gli_ammessi(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        righe = SoggettiService().get_tipi_indirizzo_proponibili_soggetto(
            self._soggetto_pg("Picker ordine e2e"),
        )
        ammessi = [r["ammesso"] for r in righe]
        self.assertEqual(sorted(ammessi, reverse=True), ammessi)


class RuoloPickerDbTests(_Mondo):

    # Il soggetto PRIMA della finestra differita: il builder chiude con
    # `SET CONSTRAINTS ALL IMMEDIATE`; il guard degli obbligatori giudica al COMMIT.
    def _ruolo_fornitore(self) -> int:
        soggetto_id = self._soggetto_pg("Picker ruolo e2e")
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            cur.execute(
                "SELECT script.fn_get_or_create_soggetto_ruolo(%s::uuid, 'FO')", [soggetto_id],
            )
            return int(cur.fetchone()[0])

    def test_il_tipo_creato_si_spegne_col_motivo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        servizio = SoggettiService()
        sr_id = self._ruolo_fornitore()
        tipo = self._primo_ammesso(servizio.get_tipi_indirizzo_proponibili_ruolo(sr_id, None))

        servizio.create_indirizzo_ruolo(sr_id, self._payload(tipo["codice_interno"]))

        self._verifica_spento(
            servizio.get_tipi_indirizzo_proponibili_ruolo(sr_id, None), tipo,
            "E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE",
        )

    def test_il_tipo_di_ruolo_marca_gli_obbligatori(self):
        from apps.core.db.lookup_repository import LookupRepository

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT ti.codice_interno
                  FROM config.tipi_ruolo_tipi_indirizzo m
                  JOIN config.tipi_ruoli tr ON tr.id = m.tipo_ruolo_id
                  JOIN config.tipi_indirizzi ti ON ti.id = m.tipo_indirizzo_id
                 WHERE tr.codice_interno = 'FO' AND m.attivo AND m.obbligatorio
                   AND (m.validita IS NULL OR m.validita @> script.fn_data_operativa())
                """
            )
            obbligatori = {r[0] for r in cur.fetchall()}
        if not obbligatori:
            self.skipTest("La matrice del ruolo FO non ha tipi obbligatori.")
        righe = LookupRepository().list_tipi_indirizzo_proponibili_tipo_ruolo("FO")
        self.assertEqual(obbligatori, {r["codice_interno"] for r in righe if r["obbligatorio"]})
        self.assertTrue(all(r["ammesso"] for r in righe if r["obbligatorio"]))

    def test_codice_di_ruolo_sconosciuto(self):
        from apps.core.db.lookup_repository import LookupRepository

        self.assertEqual([], LookupRepository().list_tipi_indirizzo_proponibili_tipo_ruolo("ZZ-NESSUNO"))

    def test_ruolo_inesistente(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            SoggettiService().get_tipi_indirizzo_proponibili_ruolo(-1, None)
        self.assertEqual("E_ANAG_NOT_FOUND", ctx.exception.code)
