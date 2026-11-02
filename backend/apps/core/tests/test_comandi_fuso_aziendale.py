# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: PRESIDIO — ogni management command del progetto eredita da
#        `ComandoAziendale`, cioe' gira nel fuso dell'azienda. Un comando nuovo
#        scritto su `BaseCommand` girerebbe in 'UTC' (`settings.TIME_ZONE`),
#        e un timer systemd lo lancerebbe senza che niente lo dica.
#        I comandi si TROVANO sul disco, non si elencano: un elenco scritto a
#        mano non vede il comando che manca.
# ------------------------------------------------------------
"""Indice test.

1. test_ogni_comando_eredita_da_comando_aziendale
2. test_la_scansione_vede_i_comandi (controprova: non passa a vuoto)
"""

from __future__ import annotations

import importlib
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from apps.core.management.comando_aziendale import ComandoAziendale


# Scopo: i moduli dei comandi del progetto, trovati in `apps/*/management/commands/`.
def _moduli_comandi() -> list[str]:
    radice = Path(settings.BASE_DIR) / "apps"
    return sorted(
        ".".join(p.relative_to(radice.parent).with_suffix("").parts)
        for p in radice.glob("*/management/commands/*.py")
        if p.name != "__init__.py"
    )


class ComandiNelFusoAziendaleTests(SimpleTestCase):
    """Nessun comando gira fuori dal fuso dell'azienda."""

    # 1. Ogni `Command` e' una sottoclasse di `ComandoAziendale`.
    def test_ogni_comando_eredita_da_comando_aziendale(self) -> None:
        fuori = [
            nome for nome in _moduli_comandi()
            if not issubclass(importlib.import_module(nome).Command, ComandoAziendale)
        ]
        self.assertEqual(fuori, [], "comandi che non girano nel fuso dell'azienda")

    # 2. Controprova: la scansione trova i comandi che sappiamo esistere.
    def test_la_scansione_vede_i_comandi(self) -> None:
        moduli = _moduli_comandi()
        self.assertIn("apps.core.management.commands.draina_coda_lavori", moduli)
        self.assertIn("apps.vendite.management.commands.run_fatturazione_batch", moduli)
