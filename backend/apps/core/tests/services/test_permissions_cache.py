# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari permissions_cache — cache Redis L2 permessi.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_save_and_load_user_cache
 2) test_load_cache_miss_returns_none
 3) test_invalidate_user
 4) test_invalidate_department
 5) test_invalidate_all
 6) test_load_resiliente_a_errore_redis
 7) test_save_resiliente_a_errore_redis
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services import permissions_cache


_CACHE = "apps.core.services.permissions_cache.cache"
# Il legame reparto → utente passa dalla MADRE `identita_digitali` (per
# `soggetto_ruolo_id` verso `risorse_umane`). Fino al 2026-09-12 qui si
# mockava `RisorseUmaneAuthUser`, il model della vista col nome vecchio —
# ritirato (analisi-software-per-dati-morti §2.1).
_IDENTITA = "apps.anagrafiche.models.IdentitaDigitale"
_RISORSE_UMANE = "apps.anagrafiche.models.RisorseUmane"


class PermissionsCacheTests(TestCase):
    """Test per permissions_cache."""

    # Scopo: Salvare e ricaricare la cache per un utente.
    @patch(_CACHE)
    def test_save_and_load_user_cache(self, mock_cache):
        data = {"ruolo_sistema": "OPERATIVO", "area:vendite": "TUTTO"}
        mock_cache.get.return_value = data

        permissions_cache.save_user_cache(1, data)
        mock_cache.set.assert_called_once()

        result = permissions_cache.load_user_cache(1)
        self.assertEqual(result, data)

    # Scopo: Cache miss restituisce None.
    @patch(_CACHE)
    def test_load_cache_miss_returns_none(self, mock_cache):
        mock_cache.get.return_value = None
        result = permissions_cache.load_user_cache(1)
        self.assertIsNone(result)

    # Scopo: Invalidazione singolo utente cancella la chiave.
    @patch(_CACHE)
    def test_invalidate_user(self, mock_cache):
        permissions_cache.invalidate_user(42)
        mock_cache.delete.assert_called_once_with("perms:user:42")

    # Scopo: Invalidazione reparto cancella le chiavi di tutti gli utenti del reparto.
    @patch(_CACHE)
    @patch(_RISORSE_UMANE)
    @patch(_IDENTITA)
    def test_invalidate_department(self, mock_identita, mock_ru, mock_cache):
        mock_identita.objects.filter.return_value.values_list.return_value = [1, 2, 3]

        permissions_cache.invalidate_department(10)

        # Il reparto si cerca su `risorse_umane`, l'utente su `identita_digitali`.
        mock_ru.objects.filter.assert_called_once_with(unita_organizzativa_id=10)
        mock_identita.objects.filter.assert_called_once_with(
            soggetto_ruolo_id__in=mock_ru.objects.filter.return_value.values.return_value
        )
        mock_cache.delete_many.assert_called_once_with([
            "perms:user:1",
            "perms:user:2",
            "perms:user:3",
        ])

    # Scopo: Invalidazione globale usa delete_pattern.
    @patch("apps.core.services.permissions_cache.settings")
    @patch(_CACHE)
    def test_invalidate_all(self, mock_cache, mock_settings):
        mock_settings.CACHES = {"default": {"KEY_PREFIX": "zeroerp"}}

        permissions_cache.invalidate_all()

        mock_cache.delete_pattern.assert_called_once_with("zeroerp:perms:user:*")

    # Scopo: Errore Redis su load non propaga eccezione.
    @patch(_CACHE)
    def test_load_resiliente_a_errore_redis(self, mock_cache):
        mock_cache.get.side_effect = ConnectionError("Redis down")
        result = permissions_cache.load_user_cache(1)
        self.assertIsNone(result)

    # Scopo: Errore Redis su save non propaga eccezione.
    @patch(_CACHE)
    def test_save_resiliente_a_errore_redis(self, mock_cache):
        mock_cache.set.side_effect = ConnectionError("Redis down")
        # Non deve sollevare eccezione
        permissions_cache.save_user_cache(1, {"ruolo_sistema": "OPERATIVO"})
