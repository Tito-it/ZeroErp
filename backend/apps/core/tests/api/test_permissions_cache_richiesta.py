# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test della cache permessi sul percorso della richiesta —
#        `ZeroERPPermission._get_cache` / `_save_cache_to_redis` (M-1).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_senza_contesto_niente_l2 — senza contesto di sessione si lavora in L1
2) test_contesti_diversi_voci_diverse — due emittenti, due voci
3) test_voce_letta_e_invariata_non_si_riscrive — il TTL non si rinnova da se'
4) test_voce_arricchita_si_salva — una voce nuova nella richiesta si salva
5) test_si_salva_nel_contesto_del_caricamento — GUC riaperte a meta' richiesta
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.core.cache.backends.locmem import LocMemCache

from apps.core.api.permissions import ZeroERPPermission
from apps.core.services import permissions_cache
from apps.core.services.permissions_cache import contesto_sessione

_CACHE = "apps.core.services.permissions_cache.cache"


def _richiesta(contesto: str | None = None) -> SimpleNamespace:
    """Scopo: Richiesta minima: un oggetto vero, non un MagicMock, perche'
    qui conta proprio quali attributi esistono."""
    req = SimpleNamespace(user=SimpleNamespace(id=5, is_authenticated=True))
    if contesto is not None:
        req._zeroerp_perms_contesto = contesto
    return req


class CachePermessiRichiestaTests(TestCase):
    def setUp(self) -> None:
        self.backend = LocMemCache(f"perms-req-{id(self)}", {})
        patcher = patch(_CACHE, self.backend)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.backend.clear)

    def _giro(self, contesto: str | None, nuove: dict | None = None) -> dict:
        req = _richiesta(contesto)
        cache = ZeroERPPermission._get_cache(req)  # type: ignore[arg-type]
        letto = dict(cache)
        cache.update(nuove or {})
        ZeroERPPermission._save_cache_to_redis(req)  # type: ignore[arg-type]
        return letto

    # Scopo: senza il contesto segnato da set_jwt_gucs la L2 non si legge ne'
    # si scrive: una voce «per utente» servirebbe una veste con l'altra.
    def test_senza_contesto_niente_l2(self):
        self._giro(None, {"area:vendite": "TUTTO"})
        self.assertEqual(self._giro(None), {})

    # Scopo: M-1 — lo stesso utente in due emittenti ha due voci.
    def test_contesti_diversi_voci_diverse(self):
        ef1, ef2 = contesto_sessione(9, 1), contesto_sessione(9, 2)
        self._giro(ef1, {"emittenti_pk_ids": [1]})
        self.assertEqual(self._giro(ef1), {"emittenti_pk_ids": [1]})
        self.assertEqual(self._giro(ef2), {})

    # Scopo: una richiesta che non aggiunge voci non riscrive la L2 (prima
    # la riscriveva sempre e il TTL si rinnovava all'infinito).
    def test_voce_letta_e_invariata_non_si_riscrive(self):
        ctx = contesto_sessione(9, 1)
        self._giro(ctx, {"a": 1})
        with patch.object(permissions_cache, "save_user_cache") as salva, patch(
            "apps.core.api.permissions.save_user_cache", salva
        ):
            self._giro(ctx)
        salva.assert_not_called()

    # Scopo: una voce nuova calcolata nella richiesta si aggiunge alla L2.
    def test_voce_arricchita_si_salva(self):
        ctx = contesto_sessione(9, 1)
        self._giro(ctx, {"a": 1})
        self._giro(ctx, {"b": 2})
        self.assertEqual(self._giro(ctx), {"a": 1, "b": 2})

    # Scopo: se a meta' richiesta le GUC si riaprono in un altro contesto, i
    # valori della L1 (calcolati nel primo) si salvano sotto il primo, mai
    # sotto la chiave nuova.
    def test_si_salva_nel_contesto_del_caricamento(self):
        ef1, ef2 = contesto_sessione(9, 1), contesto_sessione(9, 2)
        req = _richiesta(ef1)
        ZeroERPPermission._get_cache(req)["a"] = 1  # type: ignore[arg-type]
        req._zeroerp_perms_contesto = ef2
        ZeroERPPermission._save_cache_to_redis(req)  # type: ignore[arg-type]
        self.assertEqual(self._giro(ef1), {"a": 1})
        self.assertEqual(self._giro(ef2), {})
