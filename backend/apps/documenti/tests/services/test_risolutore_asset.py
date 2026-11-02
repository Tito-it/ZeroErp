# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit del risolutore degli asset che l'orchestratore passa al
#        render (`DocumentGenerationService._risolutore_asset`, brief
#        brief-be-documenti-risorse-esterne-render-pdf §4). Il perimetro dei
#        tre percorsi (genera, anteprima, ristampa) e' provato nei loro test;
#        qui si prova cosa fa il risolutore con quel perimetro.
#
# Indice test (0..N):
#   0. risolve_dallo_storage_nel_perimetro_dell_emittente
#   1. perimetro_ristampa_passa_solo_validi_false
#   2. stesso_asset_letto_una_volta_per_render
#   3. due_render_non_condividono_la_cache
#   4. asset_assente_errore_parlante
#   5. file_diverso_dall_impronta_registrata_raises
#   6. errore_io_dello_storage_tradotto
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)

_LOGO = b"\x89PNG logo"


def _asset(contenuto: bytes = _LOGO, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 31,
        "storage_key": "assets/11/abc.png",
        "mime_type": "image/png",
        "sha256": hashlib.sha256(contenuto).hexdigest(),
    }
    base.update(overrides)
    return base


def _service(
    *, asset: dict[str, Any] | None, contenuto: bytes = _LOGO,
) -> tuple[DocumentGenerationService, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.get_asset_per_render.return_value = asset
    storage = MagicMock()
    storage.build_storage_uri.side_effect = lambda key: f"filesystem:{key}"
    storage.read.return_value = contenuto
    svc = DocumentGenerationService(repo=repo, reader=MagicMock(), storage=storage)
    return svc, repo, storage


class RisolutoreAssetTests(SimpleTestCase):

    # 0. `asset:LOGO` -> riga dell'emittente del template, file dallo storage.
    def test_risolve_dallo_storage_nel_perimetro_dell_emittente(self) -> None:
        svc, repo, storage = _service(asset=_asset())
        risolvi = svc._risolutore_asset(11, solo_validi=True)

        self.assertEqual(risolvi("LOGO"), (_LOGO, "image/png"))
        repo.get_asset_per_render.assert_called_once_with(11, "LOGO", solo_validi=True)
        storage.read.assert_called_once_with("filesystem:assets/11/abc.png")

    # 1. La ristampa chiede anche gli asset non piu' validi: il flag arriva
    #    alla query cosi' com'e'.
    def test_perimetro_ristampa_passa_solo_validi_false(self) -> None:
        svc, repo, _ = _service(asset=_asset())
        svc._risolutore_asset(11, solo_validi=False)("LOGO")
        repo.get_asset_per_render.assert_called_once_with(11, "LOGO", solo_validi=False)

    # 2. Lo stesso asset richiamato due volte nello stesso render (CSS e
    #    HTML, o un `@import` ripetuto) si legge una volta sola.
    def test_stesso_asset_letto_una_volta_per_render(self) -> None:
        svc, repo, storage = _service(asset=_asset())
        risolvi = svc._risolutore_asset(11, solo_validi=True)
        risolvi("LOGO")
        risolvi("LOGO")
        repo.get_asset_per_render.assert_called_once()
        storage.read.assert_called_once()

    # 3. La cache e' del render, non del servizio: un secondo render rilegge
    #    (l'asset puo' essere scaduto nel frattempo).
    def test_due_render_non_condividono_la_cache(self) -> None:
        svc, repo, _ = _service(asset=_asset())
        svc._risolutore_asset(11, solo_validi=True)("LOGO")
        svc._risolutore_asset(11, solo_validi=True)("LOGO")
        self.assertEqual(repo.get_asset_per_render.call_count, 2)

    # 4. Nessun ripiego (§4.3): un asset che l'emittente non ha e' un errore
    #    che nomina l'asset e l'emittente, non un PDF senza logo.
    def test_asset_assente_errore_parlante(self) -> None:
        svc, _, storage = _service(asset=None)
        with self.assertRaises(ServiceError) as ctx:
            svc._risolutore_asset(11, solo_validi=True)("LOGO")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("asset:LOGO", ctx.exception.detail)
        self.assertIn("emittente_fiscale_id=11", ctx.exception.detail)
        storage.read.assert_not_called()

    # 5. La riga e' immutabile a DB, il file sul disco no: se i byte non sono
    #    quelli registrati, la ristampa non sarebbe fedele e il render si ferma.
    def test_file_diverso_dall_impronta_registrata_raises(self) -> None:
        svc, _, _ = _service(asset=_asset(), contenuto=b"file sostituito")
        with self.assertRaises(ServiceError) as ctx:
            svc._risolutore_asset(11, solo_validi=False)("LOGO")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_STORAGE_FAILED")
        self.assertIn("asset_id=31", ctx.exception.detail)

    # 6. Un errore di IO dello storage esce come E_DOCUMENTI_STORAGE_FAILED
    #    col nome dell'asset: dal fetcher, un'eccezione grezza diventerebbe
    #    «risorsa non ammessa» e indicherebbe il template invece del disco.
    def test_errore_io_dello_storage_tradotto(self) -> None:
        svc, _, storage = _service(asset=_asset())
        storage.read.side_effect = PermissionError("permesso negato")
        with self.assertRaises(ServiceError) as ctx:
            svc._risolutore_asset(11, solo_validi=True)("LOGO")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_STORAGE_FAILED")
        self.assertIn("asset:LOGO", ctx.exception.detail)
