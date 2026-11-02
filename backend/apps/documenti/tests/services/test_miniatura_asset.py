# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `TemplateService.miniatura_asset` — la miniatura che l'editor dei
#        template mostra accanto a ogni asset immagine. Repository e storage
#        finti, Pillow VERO: le immagini si costruiscono nel test, non si
#        cercano fra i file che ci sono.
# Indice test (0..N):
#   0. raster_ridotto_al_lato_massimo_con_proporzioni
#   1. trasparenza_conservata
#   2. immagine_piccola_non_ingrandita
#   3. svg_restituito_com_e
#   4. non_immagine_rifiutata_senza_leggere_il_file
#   5. etag_uguale_non_legge_il_file
#   6. fuori_scope_404_prima_dell_etag
#   7. file_illeggibile_errore_parlante
# ------------------------------------------------------------
from __future__ import annotations

from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from PIL import Image

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.template_service import LATO_MINIATURA, TemplateService

_SHA = "a" * 64


def _png(larghezza: int, altezza: int, modo: str = "RGB") -> bytes:
    colore = (200, 10, 10, 0) if modo == "RGBA" else (200, 10, 10)
    uscita = BytesIO()
    Image.new(modo, (larghezza, altezza), colore).save(uscita, format="PNG")
    return uscita.getvalue()


def _service(
    *, mime_type: str = "image/png", contenuto: bytes = b"", asset: Any = "default",
) -> tuple[TemplateService, MagicMock]:
    repo = MagicMock()
    repo.get_asset.return_value = (
        {"id": 50, "mime_type": mime_type, "sha256": _SHA, "storage_key": "assets/11/x"}
        if asset == "default" else asset
    )
    storage = MagicMock()
    storage.build_storage_uri.side_effect = lambda key: f"filesystem:{key}"
    storage.read.return_value = contenuto
    return TemplateService(repo=repo, storage=storage), storage


@patch(
    "apps.documenti.services.template_service.PermissionResolver.get_emittenti_pk_ids",
    return_value=[11],
)
class MiniaturaAssetTests(SimpleTestCase):

    def _apri(self, dati: bytes) -> Image.Image:
        return Image.open(BytesIO(dati))

    # 0. Un'immagine grande torna PNG col lato lungo = LATO_MINIATURA, e le
    #    proporzioni restano quelle (4:1).
    def test_raster_ridotto_al_lato_massimo_con_proporzioni(self, _scope) -> None:
        svc, _ = _service(contenuto=_png(1600, 400), mime_type="image/png")
        out = svc.miniatura_asset(MagicMock(), 50)
        self.assertEqual(out["mime_type"], "image/png")
        self.assertEqual(out["etag"], f'"{_SHA}-{LATO_MINIATURA}"')
        immagine = self._apri(out["file_bytes"])
        self.assertEqual(immagine.format, "PNG")
        self.assertEqual(immagine.size, (LATO_MINIATURA, LATO_MINIATURA // 4))

    # 1. I loghi usano la trasparenza: la miniatura la conserva.
    def test_trasparenza_conservata(self, _scope) -> None:
        svc, _ = _service(contenuto=_png(400, 400, "RGBA"))
        immagine = self._apri(svc.miniatura_asset(MagicMock(), 50)["file_bytes"])
        self.assertEqual(immagine.mode, "RGBA")
        self.assertEqual(immagine.getpixel((0, 0))[3], 0)

    # 2. Un'immagine gia' piccola non si ingrandisce.
    def test_immagine_piccola_non_ingrandita(self, _scope) -> None:
        svc, _ = _service(contenuto=_png(20, 10))
        immagine = self._apri(svc.miniatura_asset(MagicMock(), 50)["file_bytes"])
        self.assertEqual(immagine.size, (20, 10))

    # 3. SVG: vettoriale, lo rimpicciolisce il browser; torna com'e'.
    def test_svg_restituito_com_e(self, _scope) -> None:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="900"/>'
        svc, _ = _service(mime_type="image/svg+xml", contenuto=svg)
        out = svc.miniatura_asset(MagicMock(), 50)
        self.assertEqual(out["file_bytes"], svg)
        self.assertEqual(out["mime_type"], "image/svg+xml")

    # 4. Un PDF o un CSS non hanno miniatura: 400, e il file non si legge.
    def test_non_immagine_rifiutata_senza_leggere_il_file(self, _scope) -> None:
        svc, storage = _service(mime_type="application/pdf")
        with self.assertRaises(ServiceError) as ctx:
            svc.miniatura_asset(MagicMock(), 50)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        storage.read.assert_not_called()

    # 5. Il client ha gia' questa miniatura (stesso ETag): niente lettura,
    #    niente Pillow, `file_bytes` None (la view risponde 304).
    def test_etag_uguale_non_legge_il_file(self, _scope) -> None:
        svc, storage = _service(contenuto=_png(400, 400))
        etag = f'"{_SHA}-{LATO_MINIATURA}"'
        out = svc.miniatura_asset(MagicMock(), 50, etag_noti=['"altro"', etag])
        self.assertIsNone(out["file_bytes"])
        self.assertEqual(out["etag"], etag)
        storage.read.assert_not_called()

    # 6. Fuori scope: 404 anche se il client porta l'ETag giusto. Un 304
    #    dato prima del controllo confermerebbe che l'asset esiste.
    def test_fuori_scope_404_prima_dell_etag(self, _scope) -> None:
        svc, _ = _service(asset=None)
        with self.assertRaises(ServiceError) as ctx:
            svc.miniatura_asset(
                MagicMock(), 50, etag_noti=[f'"{_SHA}-{LATO_MINIATURA}"'],
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")

    # 7. File che si dichiara PNG ma non lo e': errore che nomina l'asset.
    def test_file_illeggibile_errore_parlante(self, _scope) -> None:
        svc, _ = _service(contenuto=b"non sono un png")
        with self.assertRaises(ServiceError) as ctx:
            svc.miniatura_asset(MagicMock(), 50)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("asset_id=50", ctx.exception.detail)
