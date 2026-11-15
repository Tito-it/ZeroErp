# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cambio di natura del soggetto lato BE, sul DB vero
#        (brief-db-cambio-natura-soggetto §6.0, K-3 … K-5): le nature
#        proponibili nel dettaglio, l'endpoint dei motivi, l'eliminazione
#        manuale dei dati societari e il rifiuto del PATCH.
# ⭐ Sul DB vero perche' i tre binding sono funzioni chiamate per nome e
#    posizione: un mock non vedrebbe un argomento spostato.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) CambioNaturaSoggettoDbTests.test_dettaglio_porta_le_nature_proponibili
2) CambioNaturaSoggettoDbTests.test_motivi_ditta_verso_privato_tutti_in_ordine
3) CambioNaturaSoggettoDbTests.test_motivi_leggono_i_valori_proposti_per_presenza
4) CambioNaturaSoggettoDbTests.test_motivi_natura_obbligatoria_e_chiavi_chiuse
5) CambioNaturaSoggettoDbTests.test_elimina_dati_societari_della_ditta
6) CambioNaturaSoggettoDbTests.test_elimina_dati_societari_rifiutato_se_la_natura_li_richiede
7) CambioNaturaSoggettoDbTests.test_patch_fra_famiglie_rifiutato_col_campo
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto


class CambioNaturaSoggettoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute("SELECT codice_interno, id FROM config.tipi_soggetto_dettaglio")
            self.tipo = dict(cur.fetchall())
            cur.execute("SELECT codice, id FROM config.forme_giuridiche")
            self.forma = dict(cur.fetchall())
            cur.execute("SELECT id FROM config.tipi_contatti ORDER BY id LIMIT 1")
            self.tipo_contatto = cur.fetchone()[0]

    @staticmethod
    def _service():
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        return SoggettiService()

    @staticmethod
    def _libero(funzione: str) -> str:
        with connection.cursor() as cur:
            cur.execute(f"SELECT dbops.{funzione}()")
            return str(cur.fetchone()[0])

    def _crea(self, **campi: Any) -> str:
        creato = self._service().create_soggetto({
            **campi,
            "contatto": {
                "nominativo": "Natura", "tipo_contatto_id": self.tipo_contatto,
                "email": "cambio.natura@test.invalid",
            },
        })
        return str(creato["id"])

    # Una ditta individuale con P.IVA e dati societari (policy OPTIONAL).
    def _ditta(self) -> str:
        return self._crea(
            tipo_soggetto_dettaglio_id=self.tipo["DI"], cognome="Natura", nome="Ditta",
            codice_fiscale=self._libero("fn_pgtap_cf_libero"),
            partita_iva=self._libero("fn_pgtap_piva_libera"),
            dati_societari={
                "forma_giuridica_id": self.forma["DI"], "destinatario_fe": "P",
                "pec_fatturazione": "ditta.natura@pec.test.invalid",
            },
        )

    # Una societa' di capitali (dati societari REQUIRED).
    def _societa(self) -> str:
        piva = self._libero("fn_pgtap_piva_libera")
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM config.province ORDER BY id LIMIT 1")
            provincia = cur.fetchone()[0]
        return self._crea(
            tipo_soggetto_dettaglio_id=self.tipo["SC"], ragione_sociale="Natura SRL",
            codice_fiscale=piva, partita_iva=piva,
            dati_societari={
                "forma_giuridica_id": self.forma["SRL"], "capitale_sociale": "10000",
                "id_prov_iscri_rea": provincia, "iscrizione_rea": "REA-NATURA-1",
            },
        )

    def _rifiuto(
        self, fn: Callable[[], Any], codice: str, campo: str | None, status: int,
    ) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, codice, f"{api.message} — {exc!r}")
            if campo:
                self.assertIn(campo, api.fields or (), f"campo {campo} non acceso")
            self.assertEqual(ErrorTranslator.get_http_status(api), status)
            return
        self.fail(f"atteso {codice}, accettato")

    @staticmethod
    def _codici(motivi: list[dict[str, Any]]) -> list[str]:
        return [m["codice"] for m in motivi]

    # 1. Il dettaglio porta TUTTE le nature, l'attuale ammessa, ognuna coi suoi
    #    motivi; la regola di prima (`tipi_modificabili_ids`) non c'e' piu'. E
    #    la terna di «Elimina i dati societari», accesa per la ditta.
    def test_dettaglio_porta_le_nature_proponibili(self):
        di = self._ditta()
        det = self._service().get_soggetto(di)
        self.assertNotIn("tipi_modificabili_ids", det)
        nature = {n["tipo_soggetto_dettaglio_id"]: n for n in det["nature_proponibili"]}
        self.assertEqual(set(nature), set(self.tipo.values()))
        self.assertTrue(nature[self.tipo["DI"]]["ammessa"])
        self.assertEqual(nature[self.tipo["DI"]]["motivi"], [])
        sc = nature[self.tipo["SC"]]
        self.assertFalse(sc["ammessa"])
        self.assertEqual(sc["motivo_codice"], "E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA")
        self.assertIsInstance(sc["motivi"], list)
        self.assertIs(det["can_elimina_dati_societari"], True)
        self.assertIsNone(det["can_elimina_dati_societari_reason"])

    # 2. Ditta → privato: tutti i motivi, nell'ordine della check (la P.IVA,
    #    poi i dati societari). Il PATCH ne porterebbe solo il primo.
    def test_motivi_ditta_verso_privato_tutti_in_ordine(self):
        di = self._ditta()
        esito = self._service().motivi_cambio_natura(di, {"tipo_soggetto_dettaglio_id": self.tipo["PR"]})
        self.assertEqual(
            self._codici(esito["motivi"]),
            ["E_CAMBIO_NATURA_PIVA_NON_APPLICABILE", "E_CAMBIO_NATURA_CON_DATI_SOCIETARI"],
        )
        piva = esito["motivi"][0]
        self.assertEqual(piva["dettaglio"]["campo"], "partita_iva")
        self.assertEqual(
            piva["reason_key"], "anagrafiche.soggetti.cambio_natura_blocco.piva_non_applicabile",
        )

    # 3. Chiave presente = il valore proposto (anche null), chiave assente = il
    #    salvato: senza P.IVA nel corpo resta il motivo della P.IVA salvata,
    #    con `partita_iva: null` sparisce.
    def test_motivi_leggono_i_valori_proposti_per_presenza(self):
        di = self._ditta()
        svc = self._service()
        senza = svc.motivi_cambio_natura(di, {"tipo_soggetto_dettaglio_id": self.tipo["PR"]})
        vuota = svc.motivi_cambio_natura(
            di, {"tipo_soggetto_dettaglio_id": self.tipo["PR"], "partita_iva": None},
        )
        self.assertIn("E_CAMBIO_NATURA_PIVA_NON_APPLICABILE", self._codici(senza["motivi"]))
        self.assertEqual(self._codici(vuota["motivi"]), ["E_CAMBIO_NATURA_CON_DATI_SOCIETARI"])
        stessa = svc.motivi_cambio_natura(di, {"tipo_soggetto_dettaglio_id": self.tipo["DI"]})
        self.assertEqual(stessa["motivi"], [])

    # 4. La natura proposta e' obbligatoria, e il corpo ha le sole chiavi che
    #    la check legge: un flag fuori vocabolario e' un 400 come nel PATCH.
    def test_motivi_natura_obbligatoria_e_chiavi_chiuse(self):
        di = self._ditta()
        svc = self._service()
        self._rifiuto(lambda: svc.motivi_cambio_natura(di, {}), "E_ANAG_VALIDAZIONE", None, 400)
        self._rifiuto(
            lambda: svc.motivi_cambio_natura(
                di, {"tipo_soggetto_dettaglio_id": self.tipo["PR"], "sesso": "M"},
            ),
            "E_ANAG_VALIDAZIONE", None, 400,
        )
        self._rifiuto(
            lambda: svc.motivi_cambio_natura(
                di, {"tipo_soggetto_dettaglio_id": self.tipo["PR"], "cliente_pa": "X"},
            ),
            "E_ANAG_VALIDAZIONE", None, 400,
        )
        # Una natura che non esiste non «passa»: la check direbbe `[]`.
        with connection.cursor() as cur:
            cur.execute("SELECT COALESCE(max(id), 0) + 1000 FROM config.tipi_soggetto_dettaglio")
            inesistente = cur.fetchone()[0]
        self._rifiuto(
            lambda: svc.motivi_cambio_natura(di, {"tipo_soggetto_dettaglio_id": inesistente}),
            "E_ANAG_VALIDAZIONE", "tipo_soggetto_dettaglio_id", 400,
        )

    # 5. La ditta li elimina (vero), la seconda volta non c'e' niente (falso);
    #    dopo, il motivo dei dati societari sparisce dal cambio verso privato.
    def test_elimina_dati_societari_della_ditta(self):
        di = self._ditta()
        svc = self._service()
        self.assertEqual(svc.elimina_dati_societari(di), {"eliminati": True})
        self.assertEqual(svc.elimina_dati_societari(di), {"eliminati": False})
        dopo = svc.motivi_cambio_natura(
            di, {"tipo_soggetto_dettaglio_id": self.tipo["PR"], "partita_iva": None},
        )
        self.assertEqual(dopo["motivi"], [])

    # 6. Una societa' di capitali li pretende: la capability e' spenta col
    #    motivo, e il verbo rifiuta col 409 dello stesso codice.
    def test_elimina_dati_societari_rifiutato_se_la_natura_li_richiede(self):
        sc = self._societa()
        svc = self._service()
        det = svc.get_soggetto(sc)
        self.assertIs(det["can_elimina_dati_societari"], False)
        self.assertEqual(det["can_elimina_dati_societari_reason"], "E_DATI_SOCIETARI_NON_ELIMINABILI")
        self.assertEqual(
            det["can_elimina_dati_societari_reason_key"],
            "anagrafiche.soggetti.dati_societari_elimina_blocco.natura_li_richiede",
        )
        self._rifiuto(
            lambda: svc.elimina_dati_societari(sc), "E_DATI_SOCIETARI_NON_ELIMINABILI", None, 409,
        )

    # 7. Il PATCH resta un UPDATE diretto e lo giudica il guard: fra due
    #    famiglie il rifiuto ha il codice del primo motivo e accende la natura.
    def test_patch_fra_famiglie_rifiutato_col_campo(self):
        sc = self._societa()
        self._rifiuto(
            lambda: self._service().update_soggetto(sc, {"tipo_soggetto_dettaglio_id": self.tipo["DI"]}),
            "E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA", "tipo_soggetto_dettaglio_id", 400,
        )
