# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del BB `core/services/percorsi_tecnici`: quali rotte
#        sono fuori dal dominio, con gli esatti separati dai prefissi.
# ------------------------------------------------------------
"""Indice test.

PercorsiTecniciTests
 1. test_la_sonda_di_vita_e_tecnica
 2. test_i_prefissi_coprono_cio_che_sta_sotto
 3. test_un_nome_che_comincia_come_health_non_e_tecnico
 4. test_le_api_del_dominio_non_sono_tecniche
"""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.core.services.percorsi_tecnici import e_percorso_tecnico


class PercorsiTecniciTests(SimpleTestCase):
    """L'elenco dei percorsi tecnici: sede unica dei middleware trasversali."""

    # 1. `/health`, la sonda di vita del processo.
    def test_la_sonda_di_vita_e_tecnica(self) -> None:
        self.assertTrue(e_percorso_tecnico("/health"))

    # 2. Documentazione delle API, statici e caricati: tutto cio' che sta sotto.
    def test_i_prefissi_coprono_cio_che_sta_sotto(self) -> None:
        for path in ("/api/docs/", "/api/schema/?format=json", "/static/app.css", "/media/a/b.png"):
            with self.subTest(path=path):
                self.assertTrue(e_percorso_tecnico(path))

    # 3. ⚠️ `/health` e' un percorso ESATTO: con `startswith` questi erano
    #    tecnici per sbaglio.
    def test_un_nome_che_comincia_come_health_non_e_tecnico(self) -> None:
        for path in ("/healthz", "/health-check", "/health/", "/api/healthcare/"):
            with self.subTest(path=path):
                self.assertFalse(e_percorso_tecnico(path))

    # 4. Il dominio, e i prefissi senza la barra finale (`/api/docs` non e'
    #    `/api/docs/`, `/staticx` non e' `/static/`).
    def test_le_api_del_dominio_non_sono_tecniche(self) -> None:
        for path in ("/api/v1/vendite/preventivi/", "/api/docsx", "/staticx/a", "/", ""):
            with self.subTest(path=path):
                self.assertFalse(e_percorso_tecnico(path))
