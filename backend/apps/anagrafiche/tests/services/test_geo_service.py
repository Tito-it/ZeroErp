# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per GeoService — validazione, dedup, not found,
#        orchestrazione. Mock repository, CI-compatible.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_create_toponomastica_ok — happy path
 2) test_create_toponomastica_empty — descrizione vuota → E_ANAG_VALIDAZIONE
 3) test_create_toponomastica_duplicate — IntegrityError → E_ANAG_DUPLICATO
 4) test_update_toponomastica_ok — aggiorna descrizione
 5) test_update_toponomastica_not_found — id inesistente → E_ANAG_NOT_FOUND
 6) test_update_toponomastica_empty_desc — descrizione vuota dopo strip → errore
 7) test_create_comune_ok — happy path
 8) test_create_comune_empty — descrizione vuota → errore
 9) test_create_provincia_ok — happy path
10) test_create_provincia_missing_sigla — sigla mancante → errore
11) test_create_provincia_duplicate — IntegrityError → E_ANAG_DUPLICATO
12) test_create_regione_ok — happy path
13) test_create_regione_duplicate — IntegrityError → E_ANAG_DUPLICATO
14) test_create_stato_ok — happy path
15) test_create_stato_empty — descrizione vuota → errore
16) test_create_indirizzo_via_esistente — con stradario_id
17) test_create_indirizzo_via_nuova — orchestrazione stradario + indirizzo
18) test_create_indirizzo_via_nuova_missing_fields — campi mancanti → errore
19) test_get_indirizzo_not_found — id inesistente → E_ANAG_NOT_FOUND
20) test_update_indirizzo_not_found — id inesistente → E_ANAG_NOT_FOUND
21) test_list_codici_postali_invalid — comune_id 0 → errore
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.tests.db_error_fakes import SQLSTATE_UNICITA, make_integrity_error

from apps.core.services.service_errors import ServiceError


# Patch entrambi i repository usati da GeoService
GEO_REPO = "apps.anagrafiche.services.geo_service.GeoRepository"
IND_REPO = "apps.anagrafiche.services.geo_service.IndirizziRepository"


class TestToponomasticaService(TestCase):
    """Test GeoService — metodi toponomastica."""

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_toponomastica_ok(self, mock_ind, mock_geo):
        """Happy path: crea tipo strada."""
        mock_geo.return_value.create_toponomastica.return_value = {"id": 1, "descrizione": "Viale", "attivo": True}
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().create_toponomastica({"descrizione": "Viale"})
        self.assertEqual(result["descrizione"], "Viale")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_toponomastica_empty(self, mock_ind, mock_geo):
        """Descrizione vuota → ServiceError E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_toponomastica({"descrizione": "  "})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_toponomastica_duplicate(self, mock_ind, mock_geo):
        """IntegrityError → ServiceError E_ANAG_DUPLICATO."""
        mock_geo.return_value.create_toponomastica.side_effect = make_integrity_error(SQLSTATE_UNICITA)
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_toponomastica({"descrizione": "Via"})
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_update_toponomastica_ok(self, mock_ind, mock_geo):
        """Aggiorna descrizione → True."""
        mock_geo.return_value.update_toponomastica.return_value = True
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().update_toponomastica(1, {"descrizione": "Corso"})
        self.assertEqual(result, {"updated": True})

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_update_toponomastica_not_found(self, mock_ind, mock_geo):
        """ID inesistente → ServiceError E_ANAG_NOT_FOUND."""
        mock_geo.return_value.update_toponomastica.return_value = False
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().update_toponomastica(999, {"descrizione": "Test"})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_update_toponomastica_empty_desc(self, mock_ind, mock_geo):
        """Descrizione vuota dopo strip → E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().update_toponomastica(1, {"descrizione": "   "})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestComuniService(TestCase):
    """Test GeoService — metodi comuni."""

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_comune_ok(self, mock_ind, mock_geo):
        mock_geo.return_value.create_comune.return_value = {"id": 1, "descrizione": "TestComune"}
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().create_comune({"descrizione": "TestComune"})
        self.assertEqual(result["descrizione"], "TestComune")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_comune_empty(self, mock_ind, mock_geo):
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_comune({"descrizione": ""})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestProvinceService(TestCase):
    """Test GeoService — metodi province."""

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_provincia_ok(self, mock_ind, mock_geo):
        mock_geo.return_value.create_provincia.return_value = {"id": 1, "descrizione": "Test", "sigla": "TS"}
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().create_provincia({"descrizione": "Test", "sigla": "TS"})
        self.assertEqual(result["sigla"], "TS")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_provincia_missing_sigla(self, mock_ind, mock_geo):
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_provincia({"descrizione": "Test", "sigla": ""})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_provincia_duplicate(self, mock_ind, mock_geo):
        mock_geo.return_value.create_provincia.side_effect = make_integrity_error(SQLSTATE_UNICITA)
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_provincia({"descrizione": "Test", "sigla": "TS"})
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")


class TestRegioniService(TestCase):
    """Test GeoService — metodi regioni."""

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_regione_ok(self, mock_ind, mock_geo):
        mock_geo.return_value.create_regione.return_value = {"id": 1, "descrizione": "Lombardia"}
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().create_regione({"descrizione": "Lombardia"})
        self.assertEqual(result["descrizione"], "Lombardia")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_regione_duplicate(self, mock_ind, mock_geo):
        mock_geo.return_value.create_regione.side_effect = make_integrity_error(SQLSTATE_UNICITA)
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_regione({"descrizione": "Lombardia"})
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")


class TestStatiService(TestCase):
    """Test GeoService — metodi stati."""

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_stato_ok(self, mock_ind, mock_geo):
        mock_geo.return_value.create_stato.return_value = {"id": 1, "descrizione": "Italia", "codice_iso2": "IT"}
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().create_stato({"descrizione": "Italia", "codice_iso2": "IT"})
        self.assertEqual(result["codice_iso2"], "IT")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_stato_empty(self, mock_ind, mock_geo):
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_stato({"descrizione": ""})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestIndirizziService(TestCase):
    """Test GeoService — metodi indirizzi (orchestrazione)."""

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_indirizzo_via_esistente(self, mock_ind, mock_geo):
        """Con stradario_id → una sola fn madre create_indirizzo_atomico (fix #13);
        l'upsert stradario e' saltato dalla fn (stradario_id valorizzato)."""
        mock_ind.return_value.create_indirizzo_atomico.return_value = 42
        mock_ind.return_value.get_indirizzo_dettaglio.return_value = {"indirizzo_dettaglio_id": 42, "indirizzo_normalizzato": "Via Roma 1"}
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().create_indirizzo({"stradario_id": 10, "civico": 1})
        self.assertEqual(result["indirizzo_dettaglio_id"], 42)
        kwargs = mock_ind.return_value.create_indirizzo_atomico.call_args.kwargs
        self.assertEqual(kwargs["stradario_id"], 10)
        self.assertEqual(kwargs["civico"], 1)
        # I metodi separati non sono piu' invocati: la composizione e' nella fn.
        # Non esistono piu' tutti e due (mock `autospec`: `hasattr` legge la
        # classe vera), quindi il servizio non li puo' chiamare.
        for separato in ("get_or_create_stradario", "create_indirizzo_dettaglio"):
            self.assertFalse(hasattr(mock_ind.return_value, separato), separato)

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_indirizzo_via_nuova(self, mock_ind, mock_geo):
        """Senza stradario_id → una sola fn madre create_indirizzo_atomico coi
        campi 'via nuova' (upsert stradario ×2 + dettaglio, atomici nel DB)."""
        mock_ind.return_value.create_indirizzo_atomico.return_value = 42
        mock_ind.return_value.get_indirizzo_dettaglio.return_value = {"indirizzo_dettaglio_id": 42}
        from apps.anagrafiche.services.geo_service import GeoService
        result = GeoService().create_indirizzo({
            "toponomastica_id": 1, "descrizione_via": "Roma",
            "comune_id": 10, "codice_postale_id": 20, "civico": 15,
        })
        self.assertEqual(result["indirizzo_dettaglio_id"], 42)
        kwargs = mock_ind.return_value.create_indirizzo_atomico.call_args.kwargs
        self.assertIsNone(kwargs["stradario_id"])
        self.assertEqual(kwargs["toponomastica_id"], 1)
        self.assertEqual(kwargs["descrizione_via"], "Roma")
        self.assertEqual(kwargs["comune_id"], 10)
        self.assertEqual(kwargs["codice_postale_id"], 20)
        self.assertEqual(kwargs["civico"], 15)
        self.assertFalse(hasattr(mock_ind.return_value, "get_or_create_stradario"))

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_create_indirizzo_via_nuova_missing_fields(self, mock_ind, mock_geo):
        """Via nuova senza toponomastica_id → E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().create_indirizzo({"descrizione_via": "Roma", "comune_id": 10, "codice_postale_id": 20})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_get_indirizzo_not_found(self, mock_ind, mock_geo):
        """ID inesistente → E_ANAG_NOT_FOUND."""
        mock_ind.return_value.get_indirizzo_dettaglio.return_value = None
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().get_indirizzo(999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_update_indirizzo_not_found(self, mock_ind, mock_geo):
        """Update id inesistente → E_ANAG_NOT_FOUND."""
        mock_ind.return_value.update_indirizzo_dettaglio.return_value = False
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().update_indirizzo(999, {"civico": 10})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(GEO_REPO, autospec=True)
    @patch(IND_REPO, autospec=True)
    def test_list_codici_postali_invalid(self, mock_ind, mock_geo):
        """comune_id 0 → E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.geo_service import GeoService
        with self.assertRaises(ServiceError) as ctx:
            GeoService().list_codici_postali(0)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
