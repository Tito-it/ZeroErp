# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi del modulo che ricava il CONTESTO del risolutore IVA dalla
#        testata di un documento — la sede unica che serve sia l'anteprima del
#        form sia il salvataggio.
#
#        ⭐ Questi test sono arrivati QUI perche' la logica si e' spostata qui:
#        prima vivevano (in parte) nei tre service, ognuno con la sua copia.
#        Un'estrazione che lascia i presidi dov'erano li rende muti.
#
# Indice test:
#   1. contesto: l'emittente e' la PK della TESTATA, non si va a cercarlo altrove
#   2. contesto: senza emittente in testata si ripiega sull'operatore
#   3. contesto: ⛔ P3 — senza emittente da nessuna fonte CI SI FERMA
#   4. contesto: ⛔ senza `auth_user_id` NON si ripiega (DDT e ordini)
#   5. contesto: senza data ci si ferma, con errore di dominio
#   6. contesto: la data ISO diventa `date`, una `date` resta com'e'
#   7. normalizza_iva_id: ⛔ lo ZERO e' un errore, non un'assenza
#   8. normalizza_iva_id: assenza e stringa vuota valgono «nessuna scelta»
#   9. normalizza_iva_id: la stringa numerica passa
#  10. carica_testata: un tipo fuori whitelist e' rifiutato
#  11. ⭐ whitelist e registry sono UNA SOLA sorgente
#  12. ⭐ i tipi sono i codici di `config.sorgenti`: `ORDINE`/`DDT` rifiutati
#      (rev 2026-10-19, brief-db-grammatica-unica-documenti lotto 2a)
# ------------------------------------------------------------

import unittest
import unittest.mock
from datetime import date
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import _iva_contesto_documento as mod

_COD = "E_VENDITE_VALIDATION"
_FN = "test"


def _ctx(testata, **kw):
    return mod.contesto_da_testata(testata, error_code=_COD, function_name=_FN, **kw)


class ContestoDaTestataTests(unittest.TestCase):
    def _testata(self, **over):
        base = {
            "emittente_fiscale_id": 3, "billing_account_id": 100,
            "utility_id": 5, "data": "2026-08-31",
        }
        base.update(over)
        return base

    # Scopo: ⛔ la PK, e la si prende dalla testata. Con il `soggetto_ruolo_id`
    #        al suo posto il risolutore non troverebbe l'emittente, quindi non
    #        i suoi titoli, e risponderebbe con l'aliquota ordinaria SENZA
    #        sollevare — la trappola `feedback_emittente_pk_vs_soggetto_ruolo`.
    def test_emittente_dalla_testata(self):
        ctx = _ctx(self._testata())
        self.assertEqual(ctx["emittente_fiscale_id"], 3)
        self.assertEqual(ctx["billing_account_id"], 100)
        self.assertEqual(ctx["utility_id"], 5)
        self.assertEqual(ctx["data_riferimento"], date(2026, 8, 31))

    # Scopo: il ripiego sull'operatore — il caso dell'admin globale che non ha
    #        scelto l'emittente sul preventivo.
    @patch.object(mod, "ParameterService")
    def test_ripiego_sull_operatore(self, param_cls):
        param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = 44
        ctx = _ctx(self._testata(emittente_fiscale_id=None), auth_user_id=7)
        self.assertEqual(ctx["emittente_fiscale_id"], 44)

    # Scopo: ⛔ P3 (decisione di Tid) — «un operatore ha sempre un emittente; se
    #        non lo ha, il calcolo si ferma e segnala». Il difetto che previene
    #        non ha sintomi: zero titoli letti sotto RLS e aliquota ordinaria.
    @patch.object(mod, "ParameterService")
    def test_senza_emittente_da_nessuna_fonte_si_ferma(self, param_cls):
        param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = None
        with self.assertRaises(ServiceError) as c:
            _ctx(self._testata(emittente_fiscale_id=None), auth_user_id=7)
        self.assertEqual(c.exception.code, _COD)

    # Scopo: ⚠️ il gemello negativo, e non e' ornamentale. DDT e ordini NON
    #        passano `auth_user_id` — la loro testata l'emittente ce l'ha
    #        sempre. Se il ripiego scattasse comunque, un documento con la
    #        testata rotta prenderebbe l'emittente di CHI STA GUARDANDO.
    @patch.object(mod, "ParameterService")
    def test_senza_auth_user_non_si_ripiega(self, param_cls):
        with self.assertRaises(ServiceError):
            _ctx(self._testata(emittente_fiscale_id=None))
        param_cls.return_value.get_emittente_fiscale_id_for_user.assert_not_called()

    # Scopo: il risolutore prende una data e non legge mai `CURRENT_DATE` (D14):
    #        senza, errore di dominio e non un `ValueError` da `fromisoformat`.
    def test_senza_data_si_ferma(self):
        with self.assertRaises(ServiceError) as c:
            _ctx(self._testata(data=None))
        self.assertEqual(c.exception.code, _COD)

    def test_data_gia_date_resta(self):
        d = date(2026, 1, 2)
        self.assertEqual(_ctx(self._testata(data=d))["data_riferimento"], d)


class NormalizzaIvaIdTests(unittest.TestCase):
    # Scopo: ⛔ IL DIFETTO CHE QUESTA FUNZIONE ESISTE PER CHIUDERE. La forma
    #        precedente — `int(x) if x else None`, scritta in tre service — su
    #        uno ZERO esplicito rispondeva `None`, cioe' «nessuna scelta»: il
    #        risolutore diventava autoritativo su un payload che un valore ce
    #        l'aveva, solo invalido. Uno zero non e' un'assenza.
    def test_zero_e_un_errore_non_un_assenza(self):
        for valore in (0, "0", -1):
            with self.subTest(valore=valore):
                with self.assertRaises(ServiceError):
                    mod.normalizza_iva_id(valore, error_code=_COD, function_name=_FN)

    def test_assenza_e_stringa_vuota_sono_nessuna_scelta(self):
        for valore in (None, "", "   "):
            with self.subTest(valore=valore):
                self.assertIsNone(
                    mod.normalizza_iva_id(valore, error_code=_COD, function_name=_FN)
                )

    def test_stringa_numerica_passa(self):
        self.assertEqual(
            mod.normalizza_iva_id("5", error_code=_COD, function_name=_FN), 5
        )

    # Scopo: un valore spazzatura non deve passare per «assente».
    def test_spazzatura_e_un_errore(self):
        with self.assertRaises(ServiceError):
            mod.normalizza_iva_id("banana", error_code=_COD, function_name=_FN)


class CaricaTestataTests(unittest.TestCase):
    def test_tipo_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError) as c:
            mod.carica_testata(
                documento_tipo="FATTURA", documento_id=1,
                error_code=_COD, function_name=_FN,
            )
        self.assertEqual(c.exception.code, _COD)

    # Scopo: ⭐ UNA SORGENTE SOLA. La costante pubblica e le chiavi del registry
    #        devono coincidere: se divergono, un tipo dichiarato ammesso passa
    #        il guard e poi solleva un `KeyError` grezzo nella lettura — un
    #        errore tecnico al posto di un rifiuto parlante, per un dominio che
    #        il codice dice di conoscere.
    def test_whitelist_e_registry_coincidono(self):
        self.assertEqual(
            set(mod.TIPI_DOCUMENTO_AMMESSI), set(mod._LOADER)
        )

    # Scopo: ⭐ UNA GRAMMATICA SOLA per i tipi di documento (lotto 2a della
    #        grammatica unica, 2026-10-19). I tipi ammessi sono i codici di
    #        `config.sorgenti`, gli stessi delle costanti `SORGENTE_*`; i codici
    #        corti di prima sono un rifiuto parlante, non un sinonimo.
    def test_tipi_sono_i_codici_delle_sorgenti(self):
        from apps.config.sorgenti import (
            SORGENTE_DDT_VENDITA,
            SORGENTE_ORDINE_VENDITA,
            SORGENTE_PREVENTIVO,
        )

        self.assertEqual(
            set(mod.TIPI_DOCUMENTO_AMMESSI),
            {SORGENTE_PREVENTIVO, SORGENTE_ORDINE_VENDITA, SORGENTE_DDT_VENDITA},
        )
        for corto in ("ORDINE", "DDT"):
            with self.subTest(corto=corto), self.assertRaises(ServiceError) as c:
                mod.carica_testata(
                    documento_tipo=corto, documento_id=1,
                    error_code=_COD, function_name=_FN,
                )
            self.assertEqual(c.exception.context.get("field"), "documento_tipo")


class PayloadIvaChiusoTests(unittest.TestCase):
    """`I6`: la riga di documento non porta piu' un'IVA scelta a mano."""

    # Scopo: ⛔ IL SILENZIO CHE DIVENTA RIFIUTO. Dopo `I6` `payload_iva_id` vale
    #        sempre `None` sui tre domini. Se qualcuno gli passasse di nuovo un
    #        valore NON otterrebbe un errore: `applica_riga_documento`
    #        scivolerebbe sul ramo di AUDIT, che e' best-effort dentro un
    #        savepoint — gli errori si INGHIOTTONO e a vincere e' il payload.
    #        Cioe' una riga si salverebbe anche quando l'IVA non e'
    #        determinabile, su un documento che diventera' fiscale.
    # ⚠️ Il guard non e' ridondante con le whitelist di riga: quelle fermano il
    #        CLIENT, questo ferma il CHIAMANTE — un service che un giorno
    #        rileggesse il valore da un'altra strada.
    def test_un_payload_iva_viene_rifiutato(self):
        risolvi = mod.make_risolvi_iva_riga(error_code=_COD, function_name=_FN)
        with self.assertRaises(ServiceError) as c:
            risolvi({}, articolo_id="art-1", payload_iva_id=22)
        self.assertEqual(c.exception.code, _COD)
        self.assertIn("iva_id", (c.exception.context or {}).get("field", ""))

    # Scopo: ⭐ il gemello — senza `payload_iva_id` il guard NON scatta e si
    #        arriva alla risoluzione. Senza questo caso, un guard che rifiuta
    #        sempre passerebbe quello sopra e spegnerebbe l'intera scrittura di
    #        righe sui tre domini.
    def test_senza_payload_iva_si_prosegue(self):
        risolvi = mod.make_risolvi_iva_riga(error_code=_COD, function_name=_FN)
        with unittest.mock.patch(
            "apps.vendite.services.iva_resolver_service.IvaResolverService"
        ) as resolver_cls:
            resolver_cls.return_value.applica_riga_documento.return_value = (9, {})
            with unittest.mock.patch.object(
                mod, "contesto_da_testata", return_value={
                    "emittente_fiscale_id": 3, "billing_account_id": 1,
                    "utility_id": None, "data_riferimento": date(2026, 1, 1),
                },
            ):
                esito = risolvi({}, articolo_id="art-1")
        self.assertEqual(esito, (9, {}))
