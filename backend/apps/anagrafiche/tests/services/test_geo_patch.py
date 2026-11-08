# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio delle sei PATCH di geo (toponomastica, CAP, province,
#        regioni, stati, indirizzi): i campi si leggono per PRESENZA.
#        Fino al 2026-10-20 tutte passavano da `dynamic_update` (None = «non
#        toccare»): il drawer manda `null` per un campo svuotato, e svuotarlo
#        rispondeva «salvato» senza scrivere; una chiave ignota si scartava;
#        un PATCH vuoto rispondeva 404 su un record che esiste; e
#        `{"attivo": null}` spegneva l'indirizzo
#        (brief-be-verifica-documentazione-api §A2, §B2, §B3).
#        Test senza DB: si guarda cosa arriva al repository.
# ------------------------------------------------------------
"""Indice test:
1. test_null_svuota_un_campo_nullable
2. test_chiave_assente_non_si_tocca
3. test_chiave_fuori_contratto_e_400
4. test_patch_vuota_e_400_non_404
5. test_null_su_un_campo_not_null_e_400
6. test_attivo_null_e_400_non_spegne
7. test_sigle_in_maiuscolo
8. test_id_obbligatorio_non_si_svuota
9. test_oltre_la_lunghezza_della_colonna_e_400
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from apps.anagrafiche.error_codes import E_ANAG_VALIDAZIONE
from apps.anagrafiche.services.geo_service import GeoService
from apps.core.services.service_errors import ServiceError

_GEO = "apps.anagrafiche.services.geo_service.GeoRepository"
_IND = "apps.anagrafiche.services.geo_service.IndirizziRepository"


class GeoPatchTests(TestCase):
    def setUp(self) -> None:
        self.geo = patch(_GEO, autospec=True).start().return_value
        self.ind = patch(_IND, autospec=True).start().return_value
        self.addCleanup(patch.stopall)
        self.svc = GeoService()

    def _rifiuto(self, chiamata) -> ServiceError:
        with self.assertRaises(ServiceError) as ctx:
            chiamata()
        return ctx.exception

    def test_null_svuota_un_campo_nullable(self) -> None:
        self.ind.update_indirizzo_dettaglio.return_value = True
        self.svc.update_indirizzo(5, {"palazzina": None, "scala": "  ", "civico": 12})
        self.ind.update_indirizzo_dettaglio.assert_called_once_with(
            5, {"palazzina": None, "scala": None, "civico": 12},
        )
        self.geo.update_stato.return_value = True
        self.svc.update_stato(3, {"codice_iso2": None})
        self.geo.update_stato.assert_called_once_with(3, {"codice_iso2": None})

    def test_chiave_assente_non_si_tocca(self) -> None:
        self.geo.update_regione.return_value = True
        self.svc.update_regione(2, {"descrizione": "Lazio"})
        self.geo.update_regione.assert_called_once_with(2, {"descrizione": "Lazio"})

    def test_chiave_fuori_contratto_e_400(self) -> None:
        for chiamata in (
            lambda: self.svc.update_toponomastica(1, {"descrizione": "Via", "id": 1}),
            lambda: self.svc.update_codice_postale(1, {"codice": "00100", "comune": 3}),
            lambda: self.svc.update_provincia(1, {"sigla": "RM", "attivo": True}),
            lambda: self.svc.update_indirizzo(1, {"civico": 3, "via": "Roma"}),
        ):
            with self.subTest():
                self.assertEqual(self._rifiuto(chiamata).code, E_ANAG_VALIDAZIONE)
        self.geo.update_toponomastica.assert_not_called()
        self.ind.update_indirizzo_dettaglio.assert_not_called()

    def test_patch_vuota_e_400_non_404(self) -> None:
        for nome, chiamata in (
            ("toponomastica", lambda: self.svc.update_toponomastica(1, {})),
            ("cap", lambda: self.svc.update_codice_postale(1, {})),
            ("provincia", lambda: self.svc.update_provincia(1, {})),
            ("regione", lambda: self.svc.update_regione(1, {})),
            ("stato", lambda: self.svc.update_stato(1, {})),
            ("indirizzo", lambda: self.svc.update_indirizzo(1, {})),
        ):
            with self.subTest(patch=nome):
                self.assertEqual(self._rifiuto(chiamata).code, E_ANAG_VALIDAZIONE)

    def test_null_su_un_campo_not_null_e_400(self) -> None:
        for chiamata in (
            lambda: self.svc.update_stato(1, {"descrizione": None}),
            lambda: self.svc.update_provincia(1, {"sigla": ""}),
            lambda: self.svc.update_codice_postale(1, {"codice": "   "}),
        ):
            with self.subTest():
                self.assertEqual(self._rifiuto(chiamata).code, E_ANAG_VALIDAZIONE)

    def test_attivo_null_e_400_non_spegne(self) -> None:
        e = self._rifiuto(lambda: self.svc.update_indirizzo(1, {"attivo": None}))
        self.assertEqual(e.code, E_ANAG_VALIDAZIONE)
        self.ind.update_indirizzo_dettaglio.assert_not_called()
        self._rifiuto(lambda: self.svc.update_toponomastica(1, {"attivo": None}))
        self.geo.update_toponomastica.assert_not_called()

    def test_sigle_in_maiuscolo(self) -> None:
        self.geo.update_provincia.return_value = True
        self.svc.update_provincia(1, {"sigla": " rm "})
        self.geo.update_provincia.assert_called_once_with(1, {"sigla": "RM"})
        self.geo.update_stato.return_value = True
        self.svc.update_stato(1, {"codice_iso3": "ita", "continente": "Europa"})
        self.geo.update_stato.assert_called_once_with(
            1, {"codice_iso3": "ITA", "continente": "Europa"},
        )

    def test_id_obbligatorio_non_si_svuota(self) -> None:
        self._rifiuto(lambda: self.svc.update_regione(1, {"stato_id": None}))
        self._rifiuto(lambda: self.svc.update_codice_postale(1, {"comune_id": None}))
        self.geo.update_provincia.return_value = True
        self.svc.update_provincia(1, {"regione_id": None})
        self.geo.update_provincia.assert_called_once_with(1, {"regione_id": None})

    # ⛔ Oltre la lunghezza della colonna il DB risponde 22001, che arrivava
    #    nudo: un 500. Ora e' un 400 sul campo, e il repository non parte.
    def test_oltre_la_lunghezza_della_colonna_e_400(self) -> None:
        for chiamata, campo in (
            (lambda: self.svc.update_stato(3, {"codice_iso2": "ITA"}), "codice_iso2"),
            (lambda: self.svc.update_provincia(3, {"sigla": "X" * 11}), "sigla"),
            (lambda: self.svc.update_indirizzo(5, {"interno": "X" * 11}), "interno"),
        ):
            with self.subTest(campo=campo):
                errore = self._rifiuto(chiamata)
                self.assertEqual(errore.code, E_ANAG_VALIDAZIONE)
                self.assertEqual(errore.context.get("field"), campo)
        self.geo.update_stato.assert_not_called()
        self.geo.update_provincia.assert_not_called()
        self.ind.update_indirizzo_dettaglio.assert_not_called()
