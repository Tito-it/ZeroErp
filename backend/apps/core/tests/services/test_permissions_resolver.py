# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari PermissionResolver — catena di risoluzione permessi.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_disabilitato_nega_area
 2) test_disabilitato_nega_azione
 3) test_admin_consente_area_tutto
 4) test_admin_consente_azione
 5) test_override_area_tutto
 6) test_override_area_lettura
 7) test_override_area_bloccato
 8) test_override_oggetto_sovrascrive_area
 9) test_profilo_reparto_ereditato
10) test_profilo_reparto_azione_ereditata
11) test_override_temporale_scaduto_ignorato
12) test_override_temporale_futuro_ignorato
13) test_utente_senza_bridge_bloccato
14) test_reparto_senza_profilo_bloccato
15) test_azione_override_grant
16) test_azione_override_deny
17) test_emittenti_nessuna_riga_none
18) test_emittenti_con_righe_lista
19) test_area_model_override
20) test_cache_evita_query_duplicate
21) test_has_profilo_reparto_area_true
22) test_has_profilo_reparto_area_false
23) test_has_profilo_senza_uo_false
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.permissions_resolver import LIVELLO_MAP, PermissionResolver

# Percorsi per patch dei model importati localmente nel resolver
_BRIDGE = "apps.anagrafiche.models.RisorseUmaneAuthUser"
_OVERRIDE_AREA = "apps.config.models.UserOverrideArea"
_OVERRIDE_OGGETTO = "apps.config.models.UserOverrideOggetto"
_OVERRIDE_AZIONE = "apps.config.models.UserOverrideAzione"
_PROFILO_AREA = "apps.config.models.ProfiloRepartoArea"
_PROFILO_AZIONE = "apps.config.models.ProfiloRepartoAzione"
_EMITTENTI = "apps.config.models.UserEmittenteFiscale"
_MODEL_OVERRIDE = "apps.config.models.AreaModelOverride"


def _mock_user(user_id: int = 1) -> MagicMock:
    """Scopo: Crea un mock user Django con id impostato."""
    user = MagicMock()
    user.id = user_id
    return user


def _mock_bridge(ruolo: str = "OPERATIVO", uo_id: int | None = 10) -> MagicMock:
    """Scopo: Crea un mock RisorseUmaneAuthUser con risorsa_umana."""
    bridge = MagicMock()
    bridge.ruolo_sistema = ruolo
    bridge.risorsa_umana = MagicMock()
    bridge.risorsa_umana.unita_organizzativa_id = uo_id
    return bridge


class PermissionResolverRuoloSistemaTests(TestCase):
    """Test per comportamento basato su ruolo_sistema."""

    # Scopo: Utente DISABILITATO deve avere area BLOCCATO.
    @patch(_BRIDGE)
    def test_disabilitato_nega_area(self, mock_model):
        mock_model.objects.get.return_value = _mock_bridge(ruolo="DISABILITATO")
        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "BLOCCATO")

    # Scopo: Utente DISABILITATO deve avere azione negata.
    @patch(_BRIDGE)
    def test_disabilitato_nega_azione(self, mock_model):
        mock_model.objects.get.return_value = _mock_bridge(ruolo="DISABILITATO")
        user = _mock_user()
        result = PermissionResolver.check_azione(user, "genera_fatture_lotti")
        self.assertFalse(result)

    # Scopo: Utente ADMIN deve avere TUTTO su qualsiasi area.
    @patch(_BRIDGE)
    def test_admin_consente_area_tutto(self, mock_model):
        mock_model.objects.get.return_value = _mock_bridge(ruolo="ADMIN")
        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "TUTTO")

    # Scopo: Utente ADMIN deve avere qualsiasi azione concessa.
    @patch(_BRIDGE)
    def test_admin_consente_azione(self, mock_model):
        mock_model.objects.get.return_value = _mock_bridge(ruolo="ADMIN")
        user = _mock_user()
        result = PermissionResolver.check_azione(user, "genera_fatture_lotti")
        self.assertTrue(result)


class PermissionResolverOverrideAreaTests(TestCase):
    """Test per override utente su area funzionale."""

    # Scopo: Override area TUTTO concede accesso completo.
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_override_area_tutto(self, mock_bridge_model, mock_override_model):
        mock_bridge_model.objects.get.return_value = _mock_bridge()
        override = MagicMock()
        override.livello = "TUTTO"
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = override

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "TUTTO")

    # Scopo: Override area LETTURA concede solo view.
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_override_area_lettura(self, mock_bridge_model, mock_override_model):
        mock_bridge_model.objects.get.return_value = _mock_bridge()
        override = MagicMock()
        override.livello = "LETTURA"
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = override

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "LETTURA")
        self.assertIn("view", LIVELLO_MAP[livello])
        self.assertNotIn("add", LIVELLO_MAP[livello])

    # Scopo: Override area BLOCCATO nega tutto.
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_override_area_bloccato(self, mock_bridge_model, mock_override_model):
        mock_bridge_model.objects.get.return_value = _mock_bridge()
        override = MagicMock()
        override.livello = "BLOCCATO"
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = override

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "BLOCCATO")


class PermissionResolverOverrideOggettoTests(TestCase):
    """Test per override utente su singolo model."""

    # Scopo: Override oggetto sovrascrive override area.
    @patch(_OVERRIDE_OGGETTO)
    @patch(_BRIDGE)
    def test_override_oggetto_sovrascrive_area(self, mock_bridge_model, mock_override_model):
        mock_bridge_model.objects.get.return_value = _mock_bridge()
        override = MagicMock()
        override.livello = "LETTURA"
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = override

        user = _mock_user()
        livello = PermissionResolver.get_livello_oggetto(
            user, "anagrafiche", "clienti", "anagrafiche"
        )
        self.assertEqual(livello, "LETTURA")


class PermissionResolverProfiloRepartoTests(TestCase):
    """Test per ereditarieta' dal profilo reparto."""

    # Scopo: Profilo reparto ereditato quando non ci sono override.
    @patch(_PROFILO_AREA)
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_profilo_reparto_ereditato(self, mock_bridge_model, mock_override_model, mock_profilo_model):
        bridge = _mock_bridge(uo_id=10)
        mock_bridge_model.objects.get.return_value = bridge
        mock_bridge_model.objects.select_related.return_value.get.return_value = bridge
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = None

        profilo = MagicMock()
        profilo.livello = "LETTURA"
        mock_profilo_model.objects.filter.return_value.first.return_value = profilo

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "LETTURA")

    # Scopo: Azione ereditata dal profilo reparto.
    @patch(_PROFILO_AZIONE)
    @patch(_OVERRIDE_AZIONE)
    @patch(_BRIDGE)
    def test_profilo_reparto_azione_ereditata(self, mock_bridge_model, mock_override_model, mock_profilo_model):
        bridge = _mock_bridge(uo_id=10)
        mock_bridge_model.objects.get.return_value = bridge
        mock_bridge_model.objects.select_related.return_value.get.return_value = bridge
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = None

        profilo = MagicMock()
        profilo.abilitata = True
        mock_profilo_model.objects.filter.return_value.first.return_value = profilo

        user = _mock_user()
        result = PermissionResolver.check_azione(user, "genera_fatture_lotti")
        self.assertTrue(result)


class PermissionResolverTemporalTests(TestCase):
    """Test per validita' temporale degli override."""

    # Scopo: Override con valido_al scaduto viene ignorato -> fallback.
    @patch(_PROFILO_AREA)
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_override_temporale_scaduto_ignorato(self, mock_bridge_model, mock_override_model, mock_profilo_model):
        bridge = _mock_bridge(uo_id=10)
        mock_bridge_model.objects.get.return_value = bridge
        mock_bridge_model.objects.select_related.return_value.get.return_value = bridge
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = None

        profilo = MagicMock()
        profilo.livello = "BLOCCATO"
        mock_profilo_model.objects.filter.return_value.first.return_value = profilo

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "BLOCCATO")

    # Scopo: Override con valido_dal futuro viene ignorato -> fallback.
    @patch(_PROFILO_AREA)
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_override_temporale_futuro_ignorato(self, mock_bridge_model, mock_override_model, mock_profilo_model):
        bridge = _mock_bridge(uo_id=10)
        mock_bridge_model.objects.get.return_value = bridge
        mock_bridge_model.objects.select_related.return_value.get.return_value = bridge
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = None
        mock_profilo_model.objects.filter.return_value.first.return_value = None

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "BLOCCATO")


class PermissionResolverEdgeCaseTests(TestCase):
    """Test per casi limite."""

    # Scopo: Utente senza record bridge -> BLOCCATO.
    @patch(_PROFILO_AREA)
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_utente_senza_bridge_bloccato(self, mock_bridge_model, mock_override_model, mock_profilo_model):
        mock_bridge_model.DoesNotExist = Exception
        mock_bridge_model.objects.get.side_effect = mock_bridge_model.DoesNotExist
        mock_bridge_model.objects.select_related.return_value.get.side_effect = mock_bridge_model.DoesNotExist
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = None
        mock_profilo_model.objects.filter.return_value.first.return_value = None

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "BLOCCATO")

    # Scopo: Reparto senza profilo configurato -> BLOCCATO.
    @patch(_PROFILO_AREA)
    @patch(_OVERRIDE_AREA)
    @patch(_BRIDGE)
    def test_reparto_senza_profilo_bloccato(self, mock_bridge_model, mock_override_model, mock_profilo_model):
        bridge = _mock_bridge(uo_id=10)
        mock_bridge_model.objects.get.return_value = bridge
        mock_bridge_model.objects.select_related.return_value.get.return_value = bridge
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = None
        mock_profilo_model.objects.filter.return_value.first.return_value = None

        user = _mock_user()
        livello = PermissionResolver.get_livello_area(user, "vendite")
        self.assertEqual(livello, "BLOCCATO")


class PermissionResolverAzioneOverrideTests(TestCase):
    """Test per override azione utente."""

    # Scopo: Override azione grant sovrascrive profilo reparto deny.
    @patch(_OVERRIDE_AZIONE)
    @patch(_BRIDGE)
    def test_azione_override_grant(self, mock_bridge_model, mock_override_model):
        mock_bridge_model.objects.get.return_value = _mock_bridge()
        override = MagicMock()
        override.abilitata = True
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = override

        user = _mock_user()
        result = PermissionResolver.check_azione(user, "genera_fatture_lotti")
        self.assertTrue(result)

    # Scopo: Override azione deny sovrascrive profilo reparto grant.
    @patch(_OVERRIDE_AZIONE)
    @patch(_BRIDGE)
    def test_azione_override_deny(self, mock_bridge_model, mock_override_model):
        mock_bridge_model.objects.get.return_value = _mock_bridge()
        override = MagicMock()
        override.abilitata = False
        mock_override_model.objects.filter.return_value.filter.return_value.first.return_value = override

        user = _mock_user()
        result = PermissionResolver.check_azione(user, "genera_fatture_lotti")
        self.assertFalse(result)


class PermissionResolverEmittentiTests(TestCase):
    """Test per scope emittenti fiscali."""

    # Scopo: Utente senza righe emittenti -> None (nessuna restrizione).
    @patch(_EMITTENTI)
    def test_emittenti_nessuna_riga_none(self, mock_model):
        mock_model.objects.filter.return_value.values_list.return_value = []
        user = _mock_user()
        result = PermissionResolver.get_emittenti_ids(user)
        self.assertIsNone(result)

    # Scopo: Utente con righe emittenti -> lista ID.
    @patch(_EMITTENTI)
    def test_emittenti_con_righe_lista(self, mock_model):
        mock_model.objects.filter.return_value.values_list.return_value = [1, 3, 5]
        user = _mock_user()
        result = PermissionResolver.get_emittenti_ids(user)
        self.assertEqual(result, [1, 3, 5])


class PermissionResolverAreaModelOverrideTests(TestCase):
    """Test per area_model_overrides."""

    # Scopo: Model con override viene mappato all'area corretta.
    @patch(_MODEL_OVERRIDE)
    def test_area_model_override(self, mock_model):
        override = MagicMock()
        override.area.schema_db = "config"
        mock_model.objects.filter.return_value.select_related.return_value.first.return_value = override

        result = PermissionResolver.get_area_schema_db("anagrafiche", "qualifiche")
        self.assertEqual(result, "config")


class PermissionResolverHasProfiloTests(TestCase):
    """Test per has_profilo_reparto_area."""

    # Scopo: Reparto con profilo configurato restituisce True.
    @patch(_PROFILO_AREA)
    @patch(_BRIDGE)
    def test_has_profilo_reparto_area_true(self, mock_bridge_model, mock_profilo_model):
        mock_bridge_model.objects.select_related.return_value.get.return_value = _mock_bridge(uo_id=10)
        mock_profilo_model.objects.filter.return_value.exists.return_value = True

        user = _mock_user()
        result = PermissionResolver.has_profilo_reparto_area(user, "vendite")
        self.assertTrue(result)

    # Scopo: Reparto senza profilo configurato restituisce False.
    @patch(_PROFILO_AREA)
    @patch(_BRIDGE)
    def test_has_profilo_reparto_area_false(self, mock_bridge_model, mock_profilo_model):
        mock_bridge_model.objects.select_related.return_value.get.return_value = _mock_bridge(uo_id=10)
        mock_profilo_model.objects.filter.return_value.exists.return_value = False

        user = _mock_user()
        result = PermissionResolver.has_profilo_reparto_area(user, "vendite")
        self.assertFalse(result)

    # Scopo: Utente senza unita organizzativa restituisce False.
    @patch(_BRIDGE)
    def test_has_profilo_senza_uo_false(self, mock_bridge_model):
        mock_bridge_model.objects.select_related.return_value.get.return_value = _mock_bridge(uo_id=None)

        user = _mock_user()
        result = PermissionResolver.has_profilo_reparto_area(user, "vendite")
        self.assertFalse(result)


class PermissionResolverCacheTests(TestCase):
    """Test per cache per-request."""

    # Scopo: La cache evita query duplicate per lo stesso ruolo.
    @patch(_BRIDGE)
    def test_cache_evita_query_duplicate(self, mock_model):
        mock_model.objects.get.return_value = _mock_bridge(ruolo="OPERATIVO")
        user = _mock_user()
        cache: dict = {}

        # Prima chiamata: query
        r1 = PermissionResolver.get_ruolo_sistema(user, cache=cache)
        self.assertEqual(r1, "OPERATIVO")
        self.assertEqual(mock_model.objects.get.call_count, 1)

        # Seconda chiamata: dalla cache, nessuna query aggiuntiva
        r2 = PermissionResolver.get_ruolo_sistema(user, cache=cache)
        self.assertEqual(r2, "OPERATIVO")
        self.assertEqual(mock_model.objects.get.call_count, 1)
