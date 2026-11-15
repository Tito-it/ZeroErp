# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Copia come…» (R-1 di brief-db-copia-indirizzo-soggetto, 2026-11-15)
#        sul DATABASE VERO: il binding dei due verbi
#        `anagrafiche.fn_copia_indirizzo_soggetto` / `_ruolo` (uuid, bigint,
#        text[] → bigint[]) e la traduzione dei loro rifiuti nell'envelope:
#        codice, status e campo, come li vede il client.
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). I tipi si scelgono dal
#       picker (quelli che ammette oggi), la sorgente si crea dalla porta
#       dell'applicazione: nessun test dipende dalla matrice di oggi.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) CopiaSoggettoDbTests.test_la_copia_scrive_il_tipo_e_lo_spegne — gli id nuovi, il tipo
   copiato poi «gia' presente» nel picker
2) CopiaSoggettoDbTests.test_copiare_in_un_tipo_presente — 400 `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE`
3) CopiaSoggettoDbTests.test_l_indirizzo_di_un_altro_soggetto — 404 `E_INDIRIZZO_SOGGETTO_NON_TROVATO`
4) CopiaSoggettoDbTests.test_corpo_sbagliato — 400 `E_ANAG_VALIDAZIONE`, senza chiamare il DB
4b) CopiaSoggettoDbTests.test_la_lista_del_soggetto_porta_motivo_e_forma_estera — R-3: la lista legge la
   vista risolta (la forma estera arriva) e il motivo di «Copia come…» uguale alla check
5) CopiaRuoloDbTests.test_la_copia_resta_nel_ruolo — gli id nuovi sullo stesso ruolo, istanza della sorgente
6) CopiaRuoloDbTests.test_l_indirizzo_di_un_altro_ruolo — 404 `E_INDIRIZZO_RUOLO_NON_TROVATO`
7) CopiaRuoloDbTests.test_la_lista_del_ruolo_porta_il_motivo_della_copia — R-3: ogni riga della
   cascata porta `copia_blocco_reason` / `_key`, dalla vista di azioni del suo layer, uguale alla check
"""

from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto


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
            "tipo_indirizzo_codice_interno": tipo, "indirizzo_libero": "Via copia 1",
            "stato_id": int(riga[0]), "locality": "Prova", "postal_code": "CP1",
        }

    def _due_ammessi(self, righe: list[dict]) -> tuple[str, str]:
        ammessi = [r["codice_interno"] for r in righe if r["ammesso"]]
        if len(ammessi) < 2:
            self.skipTest("Servono due tipi ammessi: uno per la sorgente, uno per la copia.")
        return ammessi[0], ammessi[1]

    def _rifiuto_db(self, azione) -> tuple[str, int]:
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            azione()
        errore = ErrorTranslator.to_api_error(ctx.exception)
        return errore.code, ErrorTranslator.get_http_status(errore)


class CopiaSoggettoDbTests(_Mondo):

    def _sorgente(self) -> tuple[str, int, str, str]:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        servizio = SoggettiService()
        soggetto_id = self._soggetto_pg("Copia soggetto e2e")
        tipo_src, tipo_dst = self._due_ammessi(servizio.get_tipi_indirizzo_proponibili_soggetto(soggetto_id))
        src = servizio.create_indirizzo_soggetto(soggetto_id, self._payload(tipo_src))["id"]
        return soggetto_id, int(src), tipo_src, tipo_dst

    def test_la_copia_scrive_il_tipo_e_lo_spegne(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        servizio = SoggettiService()
        soggetto_id, src, _, tipo_dst = self._sorgente()
        esito = servizio.copia_indirizzo_soggetto(
            soggetto_id, src, {"tipi_indirizzo_codice_interno": [tipo_dst]},
        )
        self.assertEqual(1, len(esito["ids"]))
        riga = next(
            r for r in servizio.get_tipi_indirizzo_proponibili_soggetto(soggetto_id)
            if r["codice_interno"] == tipo_dst
        )
        self.assertEqual((False, "E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE"), (riga["ammesso"], riga["motivo_codice"]))

    def test_copiare_in_un_tipo_presente(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        soggetto_id, src, tipo_src, _ = self._sorgente()
        self.assertEqual(
            ("E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE", 400),
            self._rifiuto_db(lambda: SoggettiService().copia_indirizzo_soggetto(
                soggetto_id, src, {"tipi_indirizzo_codice_interno": [tipo_src]},
            )),
        )

    def test_l_indirizzo_di_un_altro_soggetto(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        _, src, _, tipo_dst = self._sorgente()
        altro = self._soggetto_pg("Copia altro soggetto e2e")
        self.assertEqual(
            ("E_INDIRIZZO_SOGGETTO_NON_TROVATO", 404),
            self._rifiuto_db(lambda: SoggettiService().copia_indirizzo_soggetto(
                altro, src, {"tipi_indirizzo_codice_interno": [tipo_dst]},
            )),
        )

    def test_corpo_sbagliato(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        for corpo in ({}, {"tipi_indirizzo_codice_interno": []}, {"tipi_indirizzo_codice_interno": "FATT"},
                      {"tipi_indirizzo_codice_interno": [""]}, {"tipi": ["FATT"]}):
            with self.subTest(corpo=corpo), self.assertRaises(ServiceError) as ctx:
                SoggettiService().copia_indirizzo_soggetto("00000000-0000-0000-0000-000000000000", 1, corpo)
            self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)


    def test_la_lista_del_soggetto_porta_motivo_e_forma_estera(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        soggetto_id, src, _, _ = self._sorgente()
        righe = SoggettiService().get_soggetto_indirizzi(soggetto_id)
        riga = next(r for r in righe if r["id"] == src)
        self.assertEqual(("Prova", "CP1"), (riga["locality"], riga["postal_code"]))
        for r in righe:
            with self.subTest(id=r["id"]), connection.cursor() as cur:
                cur.execute(
                    "SELECT anagrafiche.fn_check_copia_indirizzo_soggetto(%s) -> 0 ->> 'reason_key'", [r["id"]],
                )
                self.assertEqual(cur.fetchone()[0], r["copia_blocco_reason_key"])


class CopiaRuoloDbTests(_Mondo):

    # I soggetti TUTTI PRIMA della finestra differita: il builder chiude con
    # `SET CONSTRAINTS ALL IMMEDIATE`, e un ruolo gia' aperto senza i suoi
    # obbligatori verrebbe giudicato li'. Il guard giudica al COMMIT.
    def _ruoli_fornitore(self, quanti: int = 1) -> list[int]:
        soggetti = [self._soggetto_pg(f"Copia ruolo e2e {n}") for n in range(quanti)]
        ruoli = []
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            for soggetto_id in soggetti:
                cur.execute(
                    "SELECT script.fn_get_or_create_soggetto_ruolo(%s::uuid, 'FO')", [soggetto_id],
                )
                ruoli.append(int(cur.fetchone()[0]))
        return ruoli

    def _sorgente(self, sr_id: int) -> tuple[int, str]:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        servizio = SoggettiService()
        tipo_src, tipo_dst = self._due_ammessi(servizio.get_tipi_indirizzo_proponibili_ruolo(sr_id, None))
        src = servizio.create_indirizzo_ruolo(sr_id, self._payload(tipo_src))["id"]
        return int(src), tipo_dst

    def test_la_copia_resta_nel_ruolo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        (sr_id,) = self._ruoli_fornitore()
        src, tipo_dst = self._sorgente(sr_id)
        ids = SoggettiService().copia_indirizzo_ruolo(
            sr_id, src, {"tipi_indirizzo_codice_interno": [tipo_dst]},
        )["ids"]
        with connection.cursor() as cur:
            cur.execute(
                "SELECT i.soggetto_ruolo_id, i.istanza_utility_id, ti.codice_interno"
                "  FROM anagrafiche.indirizzi i JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id"
                " WHERE i.id = ANY(%s)",
                [ids],
            )
            self.assertEqual([(sr_id, None, tipo_dst)], cur.fetchall())

    def test_l_indirizzo_di_un_altro_ruolo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id, altro = self._ruoli_fornitore(2)
        src, tipo_dst = self._sorgente(sr_id)
        self.assertEqual(
            ("E_INDIRIZZO_RUOLO_NON_TROVATO", 404),
            self._rifiuto_db(lambda: SoggettiService().copia_indirizzo_ruolo(
                altro, src, {"tipi_indirizzo_codice_interno": [tipo_dst]},
            )),
        )

    def test_la_lista_del_ruolo_porta_il_motivo_della_copia(self):
        import json
        from types import SimpleNamespace

        from apps.anagrafiche.api.views_indirizzi_ruolo import RuoloIndirizziView

        (sr_id,) = self._ruoli_fornitore()
        self._sorgente(sr_id)
        dati = json.loads(
            RuoloIndirizziView().get(SimpleNamespace(query_params={}), sr_id).content,
        )["data"]
        righe = [("ruolo", r) for r in dati["indirizzi_ruolo"]] + [("soggetto", r) for r in dati["indirizzi_soggetto"]]
        self.assertTrue(dati["indirizzi_ruolo"])
        for layer, r in righe:
            with self.subTest(layer=layer, id=r["id"]), connection.cursor() as cur:
                cur.execute(
                    f"SELECT anagrafiche.fn_check_copia_indirizzo_{layer}(%s) -> 0 ->> 'reason_key'",  # layer da due letterali
                    [r["id"]],
                )
                self.assertEqual(cur.fetchone()[0], r["copia_blocco_reason_key"])
                self.assertIn("copia_blocco_reason", r)
