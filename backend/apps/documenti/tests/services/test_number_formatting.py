"""
Indice test previsti:
1) NumberFormattingTests.test_misura_pad_a_due_decimali
2) NumberFormattingTests.test_misura_non_perde_decimali_significativi
3) NumberFormattingTests.test_misura_tronca_oltre_sei_decimali
4) NumberFormattingTests.test_importo_sempre_due_decimali
5) NumberFormattingTests.test_separatore_migliaia_italiano
6) NumberFormattingTests.test_none_preserving_e_non_numerici_invariati
7) NumberFormattingTests.test_notazione_esponenziale_non_arriva_al_documento
8) NumberFormattingTests.test_formatta_campi_tocca_solo_le_chiavi_indicate
9) ValoreNonFinitoTests.test_misura_non_finita_ferma_la_generazione
10) ValoreNonFinitoTests.test_importo_non_finito_ferma_la_generazione
11) ValoreNonFinitoTests.test_formatta_campi_nomina_la_chiave
12) ValoreNonFinitoTests.test_numero_normale_invariato
"""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError

from apps.documenti.services.context_builders._number_formatting import (
    E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO,
    format_importo,
    format_misura,
    formatta_campi,
)


class NumberFormattingTests(TestCase):
    # Scopo: il caso che ha originato il lavoro — la scala della colonna
    #        (numeric a 6 decimali) non deve arrivare al documento.
    def test_misura_pad_a_due_decimali(self):
        self.assertEqual(format_misura("5.000000", campo="c"), "5,00")
        self.assertEqual(format_misura(Decimal("10"), campo="c"), "10,00")
        self.assertEqual(format_misura(0, campo="c"), "0,00")

    # Scopo: ⚠️ il presidio che conta. Troncare TUTTO a due decimali
    #        sembrerebbe piu' semplice, ma in un ERP di utilities perderebbe
    #        dato vero: 0,153 €/kWh non e' 0,15.
    def test_misura_non_perde_decimali_significativi(self):
        self.assertEqual(format_misura("0.153000", campo="c"), "0,153")
        self.assertEqual(format_misura("1.234567", campo="c"), "1,234567")

    # Scopo: oltre i 6 decimali si arrotonda (ROUND_HALF_UP, mai banker's:
    #        su un documento la meta' deve salire).
    def test_misura_tronca_oltre_sei_decimali(self):
        self.assertEqual(format_misura("1.0000005", campo="c"), "1,000001")
        self.assertEqual(format_misura("2.99999949", campo="c"), "2,999999")

    # Scopo: il denaro ha sempre due decimali, in piu' e in meno.
    def test_importo_sempre_due_decimali(self):
        self.assertEqual(format_importo("50", campo="c"), "50,00")
        self.assertEqual(format_importo("0.153000", campo="c"), "0,15")
        self.assertEqual(format_importo("1.235", campo="c"), "1,24")

    def test_separatore_migliaia_italiano(self):
        self.assertEqual(format_importo("1234.5", campo="c"), "1.234,50")
        self.assertEqual(format_importo("-1234567.891", campo="c"), "-1.234.567,89")
        self.assertEqual(format_misura("1234.5", campo="c"), "1.234,50")

    # Scopo: None resta None (il template distingue «assente» da «zero» e il
    #        context_hash non deve cambiare forma); un valore non numerico
    #        passa invariato invece di essere corrotto.
    def test_none_preserving_e_non_numerici_invariati(self):
        self.assertIsNone(format_misura(None, campo="c"))
        self.assertIsNone(format_importo(None, campo="c"))
        self.assertEqual(format_misura("CM", campo="c"), "CM")
        self.assertEqual(format_importo({"a": 1}, campo="c"), {"a": 1})

    # Scopo: `0E-32` e' cio' che il DB restituisce per un arrotondamento nullo
    #        a scala alta. Stampato grezzo finiva nel PDF cosi' com'e'.
    def test_notazione_esponenziale_non_arriva_al_documento(self):
        self.assertEqual(format_importo("0E-32", campo="c"), "0,00")
        self.assertEqual(format_misura("0E-32", campo="c"), "0,00")

    # Scopo: l'helper non deve toccare le chiavi non dichiarate — le
    #        proiezioni dei builder sono diverse fra loro.
    def test_formatta_campi_tocca_solo_le_chiavi_indicate(self):
        riga = {
            "quantita": "5.000000",
            "importo_riga": "50",
            "descrizione": "test x",
            "uom_codice": "CM",
        }
        out = formatta_campi(riga, misure=("quantita", "assente"), importi=("importo_riga",))
        self.assertEqual(out["quantita"], "5,00")
        self.assertEqual(out["importo_riga"], "50,00")
        self.assertEqual(out["descrizione"], "test x")
        self.assertEqual(out["uom_codice"], "CM")
        self.assertNotIn("assente", out)
        # L'originale non viene mutato: i builder riusano le righe del repo.
        self.assertEqual(riga["quantita"], "5.000000")


# NaN e infiniti in tutte le forme in cui arrivano al builder: Decimal dal
# driver, stringa dal `context_json` congelato (la ristampa), float da un
# calcolo fatto in Python. Anche `sNaN`, che `Decimal` accetta da stringa.
_NON_FINITI = (
    Decimal("NaN"),
    Decimal("Infinity"),
    Decimal("-Infinity"),
    "NaN",
    "Infinity",
    "-Infinity",
    "sNaN",
    float("nan"),
    float("inf"),
    float("-inf"),
)


# ⭐ Brief brief-db-valore-numerico-non-finito-nei-documenti (opzione C di Tid,
#    2026-10-09): un numero che non e' un numero ferma la generazione con un
#    errore che nomina il campo — non si stampa «NaN», non si nasconde. Prima
#    `format_misura` usciva con un TypeError anonimo (il segno meno sulla
#    stringa dell'esponente) e `format_importo` con un InvalidOperation.
#    Il log a DB e' spento: il test non ha database.
@patch("apps.core.services.error_manager.ErrorManager.log_error_only")
class ValoreNonFinitoTests(TestCase):
    def _assert_non_finito(self, fn, valore, campo):
        with self.assertRaises(ServiceError) as cm:
            fn(valore, campo=campo)
        e = cm.exception
        self.assertEqual(e.code, E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO)
        self.assertEqual(e.context["field"], campo)
        self.assertEqual(e.context["valore"], str(valore))
        self.assertIn(campo, e.detail or "")

    def test_misura_non_finita_ferma_la_generazione(self, _log):
        for valore in _NON_FINITI:
            with self.subTest(valore=valore):
                self._assert_non_finito(format_misura, valore, "quantita")

    def test_importo_non_finito_ferma_la_generazione(self, _log):
        for valore in _NON_FINITI:
            with self.subTest(valore=valore):
                self._assert_non_finito(format_importo, valore, "totale_doc")

    # Scopo: dal percorso delle righe il campo e' la chiave della proiezione.
    def test_formatta_campi_nomina_la_chiave(self, _log):
        with self.assertRaises(ServiceError) as cm:
            formatta_campi({"quantita": "5", "importo_riga": "NaN"}, misure=("quantita",), importi=("importo_riga",))
        self.assertEqual(cm.exception.context["field"], "importo_riga")

    # Scopo: il controllo non tocca i numeri normali, ne' i non numerici.
    def test_numero_normale_invariato(self, log):
        self.assertEqual(format_misura(Decimal("5.000000"), campo="q"), "5,00")
        self.assertEqual(format_importo(1234.5, campo="i"), "1.234,50")
        self.assertEqual(format_misura("CM", campo="u"), "CM")
        log.assert_not_called()
