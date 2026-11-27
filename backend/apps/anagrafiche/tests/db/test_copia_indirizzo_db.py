# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Copia come…» (R-1 di brief-db-copia-indirizzo-soggetto, 2026-11-15;
#        R-1 di brief-db-copia-indirizzo-destinazione, 2026-11-20) sul
#        DATABASE VERO: il binding dei tre verbi
#        `anagrafiche.fn_copia_indirizzo_soggetto` (uuid, bigint, text[]),
#        `fn_copia_indirizzo_ruolo` e `fn_copia_indirizzo_soggetto_su_ruolo`
#        (bigint, bigint, text[], bigint: la chiave di destinazione) e la
#        traduzione dei loro rifiuti nell'envelope: codice, status e campo,
#        come li vede il client.
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
5) CopiaRuoloDbTests.test_senza_destinazione_la_copia_va_sul_ruolo — corpo senza `istanza_utility_id`:
   la riga nuova nasce sul ruolo (istanza NULL)
5b) CopiaRuoloDbTests.test_la_copia_va_sull_istanza_di_destinazione — la sorgente e' del ruolo, la
   riga nuova nasce sull'istanza del corpo (D-1)
5c) CopiaRuoloDbTests.test_l_istanza_di_un_altro_soggetto — 400 `E_ISTANZA_ALTRO_SOGGETTO`, dal guard
   della tabella
5d) CopiaRuoloDbTests.test_destinazione_non_intera — 400 `E_ANAG_VALIDAZIONE`, senza chiamare il DB
   (anche un intero oltre bigint)
6) CopiaRuoloDbTests.test_l_indirizzo_di_un_altro_ruolo — 404 `E_INDIRIZZO_RUOLO_NON_TROVATO`
7) CopiaRuoloDbTests.test_la_lista_del_ruolo_non_porta_il_motivo_della_copia — D-4: la lista del ruolo
   si legge (la vista di azioni ritirata non c'e' piu') e nessuna riga della cascata porta
   `copia_blocco_reason` / `_key`
8) CopiaSoggettoSuRuoloDbTests.test_dal_soggetto_al_ruolo_e_alla_sua_istanza — il gemello (D-2): la
   riga del soggetto copiata sul ruolo e su una sua istanza
9) CopiaSoggettoSuRuoloDbTests.test_l_indirizzo_di_un_altro_soggetto — 404 `E_INDIRIZZO_SOGGETTO_NON_TROVATO`
"""

from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    apri_operatore_con_aree,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)


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


class _MondoRuolo(_Mondo):

    # ⚠️ Un operatore COSTRUITO col suo emittente (BB `apri_operatore_con_aree`):
    #    il cliente di prova nasce col billing account, e il BA vuole un
    #    emittente su cui lavorare, letto dal contesto.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_operatore_con_aree(cur, aree=("anagrafiche",))

    # Un cliente col suo ruolo e la sua istanza (col billing account), dal
    # builder dei pgTAP: `(soggetto_ruolo_id, istanza_utility_id, soggetto_id)`.
    @staticmethod
    def _cliente(nome: str) -> tuple[int, int, str]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT soggetto_ruolo_id, istanza_utility_id, soggetto_id"
                "  FROM dbops.fn_pgtap_crea_cliente_ba(%s)",
                [nome],
            )
            sr_id, istanza_id, soggetto_id = cur.fetchone()
        return int(sr_id), int(istanza_id), str(soggetto_id)

    # Il tipo ammesso su TUTTE le chiavi date (ruolo, istanza): quello che la
    # copia puo' scrivere ovunque il test la mandi. La sorgente e' una riga
    # che c'e' gia' sul ruolo (il builder crea gli obbligatori).
    def _tipo_libero(self, sr_id: int, *istanze: int | None) -> str:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        servizio = SoggettiService()
        ammessi: set[str] | None = None
        for istanza in istanze:
            suoi = {
                r["codice_interno"]
                for r in servizio.get_tipi_indirizzo_proponibili_ruolo(sr_id, istanza) if r["ammesso"]
            }
            ammessi = suoi if ammessi is None else ammessi & suoi
        if not ammessi:
            self.skipTest("Serve un tipo di indirizzo ammesso sulle chiavi di destinazione.")
        return sorted(ammessi)[0]

    def _riga_del_ruolo(self, sr_id: int) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM anagrafiche.indirizzi"
                " WHERE soggetto_ruolo_id = %s AND istanza_utility_id IS NULL ORDER BY id LIMIT 1",
                [sr_id],
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("Il ruolo di prova non ha un indirizzo da copiare.")
        return int(riga[0])

    def _chiavi(self, ids: list[int]) -> list[tuple]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT i.soggetto_ruolo_id, i.istanza_utility_id, ti.codice_interno"
                "  FROM anagrafiche.indirizzi i JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id"
                " WHERE i.id = ANY(%s)",
                [ids],
            )
            return cur.fetchall()


class CopiaRuoloDbTests(_MondoRuolo):

    def test_senza_destinazione_la_copia_va_sul_ruolo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id, _, _ = self._cliente("Copia ruolo e2e")
        src, tipo = self._riga_del_ruolo(sr_id), self._tipo_libero(sr_id, None)
        ids = SoggettiService().copia_indirizzo_ruolo(
            sr_id, src, {"tipi_indirizzo_codice_interno": [tipo]},
        )["ids"]
        self.assertEqual([(sr_id, None, tipo)], self._chiavi(ids))

    def test_la_copia_va_sull_istanza_di_destinazione(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id, istanza_id, _ = self._cliente("Copia ruolo su istanza e2e")
        src, tipo = self._riga_del_ruolo(sr_id), self._tipo_libero(sr_id, istanza_id)
        ids = SoggettiService().copia_indirizzo_ruolo(
            sr_id, src, {"tipi_indirizzo_codice_interno": [tipo], "istanza_utility_id": istanza_id},
        )["ids"]
        self.assertEqual([(sr_id, istanza_id, tipo)], self._chiavi(ids))

    def test_l_istanza_di_un_altro_soggetto(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id, istanza_id, _ = self._cliente("Copia ruolo istanza altrui e2e A")
        _, istanza_altrui, _ = self._cliente("Copia ruolo istanza altrui e2e B")
        src, tipo = self._riga_del_ruolo(sr_id), self._tipo_libero(sr_id, istanza_id)
        self.assertEqual(
            ("E_ISTANZA_ALTRO_SOGGETTO", 400),
            self._rifiuto_db(lambda: SoggettiService().copia_indirizzo_ruolo(
                sr_id, src, {"tipi_indirizzo_codice_interno": [tipo], "istanza_utility_id": istanza_altrui},
            )),
        )

    def test_destinazione_non_intera(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        for destinazione in ("abc", 0, -3, True, 1.5, 10**30):
            corpo = {"tipi_indirizzo_codice_interno": ["FATT"], "istanza_utility_id": destinazione}
            for verbo in ("copia_indirizzo_ruolo", "copia_indirizzo_soggetto_su_ruolo"):
                with self.subTest(destinazione=destinazione, verbo=verbo), \
                        self.assertRaises(ServiceError) as ctx:
                    getattr(SoggettiService(), verbo)(1, 1, corpo)
                self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)

    def test_l_indirizzo_di_un_altro_ruolo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id, _, _ = self._cliente("Copia ruolo altrui e2e A")
        altro, _, _ = self._cliente("Copia ruolo altrui e2e B")
        src, tipo = self._riga_del_ruolo(sr_id), self._tipo_libero(altro, None)
        self.assertEqual(
            ("E_INDIRIZZO_RUOLO_NON_TROVATO", 404),
            self._rifiuto_db(lambda: SoggettiService().copia_indirizzo_ruolo(
                altro, src, {"tipi_indirizzo_codice_interno": [tipo]},
            )),
        )

    def test_la_lista_del_ruolo_non_porta_il_motivo_della_copia(self):
        import json
        from types import SimpleNamespace

        from apps.anagrafiche.api.views_indirizzi_ruolo import RuoloIndirizziView

        sr_id, istanza_id, _ = self._cliente("Copia ruolo lista e2e")
        for query in ({}, {"istanza_utility_id": str(istanza_id)}):
            with self.subTest(query=query):
                dati = json.loads(
                    RuoloIndirizziView().get(SimpleNamespace(query_params=query), sr_id).content,
                )["data"]
                righe = dati["indirizzi_ruolo"] + dati["indirizzi_soggetto"]
                self.assertTrue(righe)
                for r in righe:
                    self.assertNotIn("copia_blocco_reason", r)
                    self.assertNotIn("copia_blocco_reason_key", r)


class CopiaSoggettoSuRuoloDbTests(_MondoRuolo):

    def _riga_del_soggetto(self, soggetto_id: str) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM anagrafiche.indirizzi_soggetti WHERE soggetto_id = %s::uuid ORDER BY id LIMIT 1",
                [soggetto_id],
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("Il soggetto di prova non ha un indirizzo da copiare.")
        return int(riga[0])

    def test_dal_soggetto_al_ruolo_e_alla_sua_istanza(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id, istanza_id, soggetto_id = self._cliente("Copia soggetto su ruolo e2e")
        src, tipo = self._riga_del_soggetto(soggetto_id), self._tipo_libero(sr_id, None, istanza_id)
        servizio = SoggettiService()
        sul_ruolo = servizio.copia_indirizzo_soggetto_su_ruolo(
            sr_id, src, {"tipi_indirizzo_codice_interno": [tipo], "istanza_utility_id": None},
        )["ids"]
        sull_istanza = servizio.copia_indirizzo_soggetto_su_ruolo(
            sr_id, src, {"tipi_indirizzo_codice_interno": [tipo], "istanza_utility_id": istanza_id},
        )["ids"]
        self.assertEqual([(sr_id, None, tipo)], self._chiavi(sul_ruolo))
        self.assertEqual([(sr_id, istanza_id, tipo)], self._chiavi(sull_istanza))

    def test_l_indirizzo_di_un_altro_soggetto(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        sr_id, _, _ = self._cliente("Copia soggetto su ruolo altrui e2e A")
        _, _, altro_soggetto = self._cliente("Copia soggetto su ruolo altrui e2e B")
        src, tipo = self._riga_del_soggetto(altro_soggetto), self._tipo_libero(sr_id, None)
        self.assertEqual(
            ("E_INDIRIZZO_SOGGETTO_NON_TROVATO", 404),
            self._rifiuto_db(lambda: SoggettiService().copia_indirizzo_soggetto_su_ruolo(
                sr_id, src, {"tipi_indirizzo_codice_interno": [tipo]},
            )),
        )
