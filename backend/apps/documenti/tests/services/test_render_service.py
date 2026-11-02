# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `render_service` (Tranche I). Verifica:
#         - whitelist engine: solo `WEASYPRINT` ammesso in v1, case
#           insensitive; engine ignoto -> E_DOCUMENTI_RENDER_FAILED;
#         - guard versione minima: html_template vuoto/NULL o
#           render_engine_codice vuoto -> E_DOCUMENTI_RENDER_FAILED;
#         - integrazione Jinja2: rendering happy path (variabile +
#           ciclo {% for %}); StrictUndefined fail-fast su variabile
#           mancante; TemplateSyntaxError mappato;
#         - integrazione WeasyPrint: chiamata avviene con HTML rendered
#           + CSS opzionale; eccezione interna -> E_DOCUMENTI_RENDER_FAILED;
#           bytes vuoti -> errore parlante;
#         - css_template assente -> resta la sola regola della pagina;
#         - la PAGINA dalle colonne della versione (R-BE-V2, 2026-10-04):
#           regola composta, campi mancanti o non validi fermano il render,
#           e sulla libreria vera le colonne vincono sull'`@page` del
#           template (CSS e `<style>` dell'HTML).
#
# Indice test (0..N):
#   0. render_pdf_happy_path_jinja_e_weasyprint_invocati
#   1. render_pdf_engine_lowercase_normalized_to_uppercase
#   2. render_pdf_engine_non_whitelisted_raises
#   3. render_pdf_html_template_vuoto_raises
#   4. render_pdf_render_engine_codice_mancante_raises
#   5. render_pdf_jinja_strict_undefined_su_variabile_mancante
#   6. render_pdf_jinja_template_syntax_error_mapped
#   7. render_pdf_weasyprint_exception_mapped
#   8. render_pdf_weasyprint_empty_output_raises
#   9. render_pdf_jinja_supporta_for_loop
#  10. render_pdf_css_assente_resta_la_regola_della_pagina
#  11. render_pdf_weasyprint_native_dep_mancante_mapped
#  12. render_pdf_jinja_escapa_html_nei_valori_del_context
#  13. rifiuto_inghiottito_da_weasyprint_ferma_il_render
#  14. rifiuto_con_service_error_del_risolutore_ne_conserva_il_codice
#  Fetcher sulla libreria VERA (skip dichiarato se mancano le dipendenze
#  native), un test per ramo (brief-be-documenti-risorse-esterne-render-pdf):
#  15. asset_ammesso_e_letto_una_volta
#  16. data_uri_ammesso_senza_risolutore
#  17. asset_che_il_risolutore_non_ha_ne_conserva_l_errore
#  18. img_file_rifiutata
#  19. link_attachment_file_rifiutato
#  20. img_http_rifiutata
#  21. css_url_file_rifiutato
#  22. css_import_ciclico_fermato_dal_tetto
#  23. svg_annidato_che_punta_a_file_rifiutato
#  24. molte_immagini_data_non_toccano_il_tetto
#  La pagina dalle colonne della versione (R-BE-V2, 2026-10-04):
#  25. regola_pagina_dalle_colonne
#  26. campo_di_pagina_mancante_ferma_il_render
#  27. valore_di_pagina_non_identificatore_rifiutato
#  28. [libreria vera] a3_orizzontale_vince_sull_at_page_del_template (R-BE-V2b)
# ------------------------------------------------------------

from __future__ import annotations

import base64
import builtins
import re
import types
import zlib
from decimal import Decimal
from typing import Any
from unittest import TestCase, skipUnless
from unittest.mock import MagicMock, patch

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.documenti.services import render_service


# Scopo: Risolutore per i test che non richiamano asset: se venisse chiamato,
#        il test lo direbbe.
def _nessun_asset(codice_interno: str) -> tuple[bytes, str]:
    raise AssertionError(f"risolutore chiamato inatteso: {codice_interno!r}")


# Scopo: I moduli `weasyprint` e `weasyprint.urls` finti per i test che non
#        devono risolvere le dipendenze native. `weasyprint.urls` serve al
#        fetcher: le sue classi qui sono il minimo che `_crea_fetcher` usa.
class _FatalFinta(BaseException):
    pass


class _URLFetcherFinto:
    def __init__(self, **kwargs: Any) -> None:
        pass

    # Come `weasyprint.urls.URLFetcher`: WeasyPrint chiama il fetcher.
    def __call__(self, url: str) -> Any:
        return self.fetch(url)


def _weasyprint_finto(fake_html: Any, fake_css: Any) -> dict[str, Any]:
    urls = types.SimpleNamespace(
        FatalURLFetchingError=_FatalFinta,
        URLFetcher=_URLFetcherFinto,
        URLFetcherResponse=MagicMock(),
    )
    return {
        "weasyprint": MagicMock(HTML=fake_html, CSS=fake_css),
        "weasyprint.urls": urls,
    }


# Scopo: True se WeasyPrint si importa con le sue dipendenze native. I test
#        sulla libreria vera si saltano, DICHIARANDOLO, dove non c'e'.
def _weasyprint_disponibile() -> bool:
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


def _versione(
    *,
    html: str = "<html><body>Hello {{ nome }}</body></html>",
    css: str | None = "body { font-family: sans-serif; }",
    engine: str = "WEASYPRINT",
    versione_id: int = 99,
    **pagina: Any,
) -> dict[str, Any]:
    # I campi della pagina sono NOT NULL a DB: la versione finta li porta
    # tutti, coi default delle colonne; `pagina` li sovrascrive.
    return {
        "id": versione_id,
        "html_template": html,
        "css_template": css,
        "render_engine_codice_interno": engine,
        "page_format": "A4",
        "page_orientation": "PORTRAIT",
        "margin_top_mm": Decimal("10"),
        "margin_right_mm": Decimal("10"),
        "margin_bottom_mm": Decimal("10"),
        "margin_left_mm": Decimal("10"),
        **pagina,
    }


class RenderPdfHappyPathTests(TestCase):
    """Render happy path: jinja render -> weasyprint -> bytes."""

    # 0. happy path: jinja interpola variabile, weasyprint mocka chiamato
    #    con HTML rendered + CSS string.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_happy_path_jinja_e_weasyprint_invocati(
        self, mock_weasy
    ) -> None:
        mock_weasy.return_value = b"%PDF-1.4 fake"
        out = render_service.render_pdf(
            template_versione=_versione(),
            context={"nome": "Mario"},
            risolvi_asset=_nessun_asset,
        )
        self.assertEqual(out, b"%PDF-1.4 fake")
        mock_weasy.assert_called_once()
        html_arg, css_arg = mock_weasy.call_args.args
        self.assertIn("Hello Mario", html_arg)
        self.assertEqual(css_arg, "body { font-family: sans-serif; }")

    # 1. engine codice lowercase -> normalizzato a uppercase + match.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_engine_lowercase_normalized_to_uppercase(
        self, mock_weasy
    ) -> None:
        mock_weasy.return_value = b"PDF"
        out = render_service.render_pdf(
            template_versione=_versione(engine="weasyprint"),
            context={"nome": "x"},
            risolvi_asset=_nessun_asset,
        )
        self.assertEqual(out, b"PDF")
        mock_weasy.assert_called_once()


class RenderPdfGuardTests(TestCase):
    """Guard input: engine non whitelisted, html vuoto, ecc."""

    # 2. engine non whitelisted -> E_DOCUMENTI_RENDER_FAILED, no weasy call.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_engine_non_whitelisted_raises(self, mock_weasy) -> None:
        with self.assertRaises(ServiceError) as ctx:
            render_service.render_pdf(
                template_versione=_versione(engine="PDFKIT"),
                context={"nome": "x"},
                risolvi_asset=_nessun_asset,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("PDFKIT", ctx.exception.message)
        mock_weasy.assert_not_called()

    # 3. html_template vuoto -> errore "Versione template incompleta".
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_html_template_vuoto_raises(
        self, mock_weasy
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            render_service.render_pdf(
                template_versione=_versione(html=""),
                context={"nome": "x"},
                risolvi_asset=_nessun_asset,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("html_template", ctx.exception.message)
        mock_weasy.assert_not_called()

    # 4. render_engine_codice mancante (None/'') -> stessa categoria.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_render_engine_codice_mancante_raises(
        self, mock_weasy
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            render_service.render_pdf(
                template_versione=_versione(engine=""),
                context={"nome": "x"},
                risolvi_asset=_nessun_asset,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        mock_weasy.assert_not_called()


class RenderPdfJinjaTests(TestCase):
    """Render Jinja: StrictUndefined + sintassi malformata + cicli."""

    # 5. variabile mancante -> StrictUndefined solleva -> errore mappato.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_jinja_strict_undefined_su_variabile_mancante(
        self, mock_weasy
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            render_service.render_pdf(
                template_versione=_versione(html="<p>{{ inesistente }}</p>"),
                context={"nome": "x"},  # 'inesistente' assente
                risolvi_asset=_nessun_asset,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("Jinja", ctx.exception.message)
        mock_weasy.assert_not_called()

    # 6. sintassi Jinja malformata -> TemplateSyntaxError mappato.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_jinja_template_syntax_error_mapped(
        self, mock_weasy
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            render_service.render_pdf(
                # `{% for %}` senza `endfor`.
                template_versione=_versione(html="<ul>{% for x in xs %}<li>{{ x }}</ul>"),
                context={"xs": [1, 2]},
                risolvi_asset=_nessun_asset,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        mock_weasy.assert_not_called()

    # 9. ciclo {% for %} renderizzato correttamente.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_jinja_supporta_for_loop(self, mock_weasy) -> None:
        mock_weasy.return_value = b"PDF"
        render_service.render_pdf(
            template_versione=_versione(
                html="<ul>{% for x in xs %}<li>{{ x }}</li>{% endfor %}</ul>",
            ),
            context={"xs": ["a", "b"]},
            risolvi_asset=_nessun_asset,
        )
        html_arg, _ = mock_weasy.call_args.args
        self.assertIn("<li>a</li>", html_arg)
        self.assertIn("<li>b</li>", html_arg)


    # 12. Un valore del context che contiene HTML arriva a WeasyPrint come
    #     TESTO: un campo anagrafica non deve poter iniettare tag (es. un
    #     `<link rel="attachment">` che allega un file del server al PDF).
    #     L'HTML scritto nel template, invece, resta intatto.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_render_pdf_jinja_escapa_html_nei_valori_del_context(
        self, mock_weasy
    ) -> None:
        mock_weasy.return_value = b"PDF"
        render_service.render_pdf(
            template_versione=_versione(html="<p>{{ nome }}</p>"),
            context={"nome": '<link rel="attachment" href="file:///etc/passwd">'},
            risolvi_asset=_nessun_asset,
        )
        html_arg, _ = mock_weasy.call_args.args
        self.assertNotIn("<link", html_arg)
        self.assertIn("&lt;link rel=&#34;attachment&#34;", html_arg)
        self.assertTrue(html_arg.startswith("<p>"))


class RenderPdfWeasyPrintTests(TestCase):
    """Render WeasyPrint: eccezione interna + output vuoto."""

    # 11. Import WeasyPrint fallisce per dipendenza nativa mancante
    #     (es. libpango) -> non deve diventare E_GENERICO.
    def test_render_pdf_weasyprint_native_dep_mancante_mapped(self) -> None:
        real_import = builtins.__import__

        # ⚠️ `globals`/`locals` ombreggiano due builtin, e qui NON si
        #    rinominano: questa funzione imita la firma di
        #    `builtins.__import__`, che quei nomi li ha per contratto — un
        #    chiamante che passasse per parola chiave non troverebbe piu'
        #    l'argomento.
        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
            if name == "weasyprint":
                raise OSError("cannot load library 'libpango-1.0-0'")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(ServiceError) as ctx:
                render_service.render_pdf(
                    template_versione=_versione(),
                    context={"nome": "x"},
                    risolvi_asset=_nessun_asset,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("WeasyPrint", ctx.exception.message)

    # 7. WeasyPrint solleva -> mappato a E_DOCUMENTI_RENDER_FAILED.
    def test_render_pdf_weasyprint_exception_mapped(self) -> None:
        # Patcho weasyprint.HTML in modo che write_pdf sollevi.
        fake_html = MagicMock()
        fake_html.return_value.write_pdf.side_effect = RuntimeError("font missing")
        fake_css = MagicMock()
        with patch.dict(
            "sys.modules",
            _weasyprint_finto(fake_html, fake_css),
        ):
            with self.assertRaises(ServiceError) as ctx:
                render_service.render_pdf(
                    template_versione=_versione(),
                    context={"nome": "x"},
                    risolvi_asset=_nessun_asset,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("WeasyPrint", ctx.exception.message)

    # 8. WeasyPrint ritorna bytes vuoti -> errore parlante.
    def test_render_pdf_weasyprint_empty_output_raises(self) -> None:
        fake_html = MagicMock()
        fake_html.return_value.write_pdf.return_value = b""
        fake_css = MagicMock()
        with patch.dict(
            "sys.modules",
            _weasyprint_finto(fake_html, fake_css),
        ):
            with self.assertRaises(ServiceError) as ctx:
                render_service.render_pdf(
                    template_versione=_versione(),
                    context={"nome": "x"},
                    risolvi_asset=_nessun_asset,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("vuoto", ctx.exception.message.lower())

    # 10. css_template None/vuoto: nessun foglio del template, resta la sola
    #     regola della pagina composta dalle colonne.
    def test_render_pdf_css_assente_resta_la_regola_della_pagina(self) -> None:
        fake_html_instance = MagicMock()
        fake_html_instance.write_pdf.return_value = b"PDF"
        fake_html = MagicMock(return_value=fake_html_instance)
        fake_css = MagicMock()
        with patch.dict(
            "sys.modules",
            _weasyprint_finto(fake_html, fake_css),
        ):
            render_service.render_pdf(
                template_versione=_versione(css=None),
                context={"nome": "x"},
                risolvi_asset=_nessun_asset,
            )
        kwargs = fake_html_instance.write_pdf.call_args.kwargs
        self.assertEqual(len(kwargs.get("stylesheets")), 1)
        fake_css.assert_called_once()
        self.assertIn("@page", fake_css.call_args.kwargs["string"])

    # 13. WeasyPrint in qualche punto inghiotte il rifiuto anche con
    #     `fail_on_errors` (es. `SVGImage.draw` cattura BaseException): il PDF
    #     esce, ma il render deve fermarsi lo stesso, perche' il fetcher ha
    #     registrato il rifiuto.
    def test_rifiuto_inghiottito_da_weasyprint_ferma_il_render(self) -> None:
        fake_html = MagicMock()

        def write_pdf_che_inghiotte(**_kwargs: Any) -> bytes:
            fetcher = fake_html.call_args.kwargs["url_fetcher"]
            try:
                fetcher("file:///etc/passwd")
            except BaseException:
                pass
            return b"PDF"

        fake_html.return_value.write_pdf.side_effect = write_pdf_che_inghiotte
        with patch.dict("sys.modules", _weasyprint_finto(fake_html, MagicMock())):
            with self.assertRaises(ServiceError) as ctx:
                render_service.render_pdf(
                    template_versione=_versione(css=None),
                    context={"nome": "x"},
                    risolvi_asset=_nessun_asset,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("file:///etc/passwd", ctx.exception.detail)

    # 14. Il risolutore solleva un ServiceError (es. storage): WeasyPrint lo
    #     avvolge in FatalURLFetchingError, e il render lo riporta fuori col
    #     SUO codice, non con un generico errore di render.
    def test_rifiuto_con_service_error_del_risolutore_ne_conserva_il_codice(
        self,
    ) -> None:
        fake_html = MagicMock()

        def write_pdf_che_si_ferma(**_kwargs: Any) -> bytes:
            fetcher = fake_html.call_args.kwargs["url_fetcher"]
            try:
                fetcher("asset:LOGO")
            except Exception as exc:
                raise _FatalFinta("fetch fallito") from exc
            return b"PDF"

        def risolvi(_codice: str) -> tuple[bytes, str]:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_STORAGE_FAILED", message="storage giu'",
            )

        fake_html.return_value.write_pdf.side_effect = write_pdf_che_si_ferma
        with patch.dict("sys.modules", _weasyprint_finto(fake_html, MagicMock())):
            with self.assertRaises(ServiceError) as ctx:
                render_service.render_pdf(
                    template_versione=_versione(css=None),
                    context={"nome": "x"},
                    risolvi_asset=risolvi,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_STORAGE_FAILED")


_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@skipUnless(
    _weasyprint_disponibile(),
    "WeasyPrint o le sue dipendenze native (Pango) non sono installate: "
    "il fetcher sulla libreria vera non e' provato in questo ambiente.",
)
class RenderPdfFetcherLibreriaVeraTests(TestCase):
    """Il fetcher chiuso, ramo per ramo, sulla libreria vera: i mock non
    vedono dove WeasyPrint inghiotte gli errori (vedi il test 23)."""

    def setUp(self) -> None:
        self.chiamate: list[str] = []
        self.asset: dict[str, tuple[bytes, str]] = {
            "LOGO": (_PNG_1PX, "image/png"),
        }

    def _risolvi(self, codice_interno: str) -> tuple[bytes, str]:
        self.chiamate.append(codice_interno)
        if codice_interno not in self.asset:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_RENDER_FAILED",
                message="asset assente",
                detail=f"asset:{codice_interno}",
            )
        return self.asset[codice_interno]

    def _render(self, html: str, css: str | None = None) -> bytes:
        return render_service.render_pdf(
            template_versione=_versione(html=html, css=css),
            context={},
            risolvi_asset=self._risolvi,
        )

    def _rifiutato(self, html: str, css: str | None = None) -> ServiceError:
        with self.assertRaises(ServiceError) as ctx:
            self._render(html, css)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        return ctx.exception

    # 15. `asset:` passa dal risolutore; lo stesso logo due volte si legge
    #     una volta (cache immagini di WeasyPrint per URL).
    def test_asset_ammesso_e_letto_una_volta(self) -> None:
        pdf = self._render('<img src="asset:LOGO"><img src="asset:LOGO">')
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(self.chiamate, ["LOGO"])

    # 16. `data:` non accede a niente: ammesso, risolutore mai chiamato.
    def test_data_uri_ammesso_senza_risolutore(self) -> None:
        data = base64.b64encode(_PNG_1PX).decode()
        pdf = self._render(f'<img src="data:image/png;base64,{data}">')
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(self.chiamate, [])

    # 17. Un asset che il risolutore non ha: il SUO errore, non un PDF
    #     senza immagine.
    def test_asset_che_il_risolutore_non_ha_ne_conserva_l_errore(self) -> None:
        exc = self._rifiutato('<img src="asset:NON_ESISTE">')
        self.assertEqual(exc.detail, "asset:NON_ESISTE")

    # 18. `file:` in un'immagine: il filesystem del backend resta chiuso.
    def test_img_file_rifiutata(self) -> None:
        exc = self._rifiutato('<img src="file:///etc/hostname">')
        self.assertIn("file:///etc/hostname", exc.detail)

    # 19. Il caso che ha aperto il brief: un file del server allegato al PDF.
    def test_link_attachment_file_rifiutato(self) -> None:
        exc = self._rifiutato('<link rel="attachment" href="file:///etc/hostname">')
        self.assertIn("file:///etc/hostname", exc.detail)

    # 20. `http:` verso la rete interna (SSRF): nessuna richiesta in uscita.
    def test_img_http_rifiutata(self) -> None:
        exc = self._rifiutato('<img src="http://169.254.169.254/latest">')
        self.assertIn("http://169.254.169.254/latest", exc.detail)

    # 21. Il CSS del template passa dallo stesso fetcher.
    def test_css_url_file_rifiutato(self) -> None:
        exc = self._rifiutato("<p>x</p>", "body { background: url(file:///etc/hostname) }")
        self.assertIn("file:///etc/hostname", exc.detail)

    # 22. Un asset CSS che importa se stesso: WeasyPrint non ha guardie sui
    #     cicli, lo ferma il tetto di risorse per render (§4.4).
    def test_css_import_ciclico_fermato_dal_tetto(self) -> None:
        self.asset["CICLO"] = (b'@import url("asset:CICLO"); p { color: red }', "text/css")
        exc = self._rifiutato('<link rel="stylesheet" href="asset:CICLO"><p>x</p>')
        self.assertIn("tetto", exc.detail)
        self.assertEqual(
            len(self.chiamate), render_service._MAX_RISORSE_PER_RENDER,
        )

    # 23. Un SVG che richiama `file://`. WeasyPrint qui il rifiuto lo
    #     inghiotte (`SVGImage.draw` cattura BaseException) e il PDF esce:
    #     senza il registro del fetcher, questo test sarebbe verde su un PDF
    #     con l'immagine monca.
    def test_svg_annidato_che_punta_a_file_rifiutato(self) -> None:
        self.asset["SVG"] = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            b'<image href="file:///etc/hostname" width="10" height="10"/></svg>',
            "image/svg+xml",
        )
        exc = self._rifiutato('<img src="asset:SVG">')
        self.assertIn("file:///etc/hostname", exc.detail)

    # 24. Il tetto conta solo `asset:` (Tid, 2026-10-01): oltre 50 immagini
    #     `data:` distinte non fermano il render, perche' un `data:` porta
    #     il contenuto nell'URL e non puo' aprire un ciclo.
    def test_molte_immagini_data_non_toccano_il_tetto(self) -> None:
        immagini = "".join(
            '<img src="data:image/svg+xml;base64,{}">'.format(
                base64.b64encode(
                    f'<svg xmlns="http://www.w3.org/2000/svg" width="{i + 1}" '
                    f'height="1"/>'.encode()
                ).decode()
            )
            for i in range(render_service._MAX_RISORSE_PER_RENDER + 10)
        )
        pdf = self._render(immagini)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(self.chiamate, [])


# Scopo: le dimensioni (in punti) della prima pagina di un PDF di WeasyPrint.
#        Le pagine stanno in object stream compressi: si decomprimono gli
#        stream (stdlib) e si legge il primo `/MediaBox`.
def _mediabox(pdf: bytes) -> tuple[float, float]:
    testi = [pdf]
    for flusso in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        try:
            testi.append(zlib.decompress(flusso))
        except zlib.error:
            continue
    for testo in testi:
        m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", testo)
        if m:
            x0, y0, x1, y1 = (float(v) for v in m.groups())
            return x1 - x0, y1 - y0
    raise AssertionError("MediaBox non trovato nel PDF")


class RenderPdfPaginaTests(TestCase):
    """La pagina la decidono le colonne della versione (R-BE-V2, D-1 strada A,
    R-BE-V2a di Tid del 2026-10-04)."""

    # 25. La regola composta: formato e orientamento dai codici del
    #     vocabolario, margini in mm nell'ordine CSS (top right bottom left),
    #     tutto `!important` (vedi `_regola_pagina`).
    def test_regola_pagina_dalle_colonne(self) -> None:
        regola = render_service._regola_pagina(_versione(
            page_format="A3", page_orientation="LANDSCAPE",
            margin_top_mm=Decimal("15.00"), margin_right_mm=Decimal("16.5"),
            margin_bottom_mm=0, margin_left_mm="18",
        ))
        self.assertEqual(
            regola,
            "@page { size: A3 LANDSCAPE !important;"
            " margin: 15.00mm 16.5mm 0mm 18mm !important; }",
        )

    # 26. Un campo della pagina assente e' una proiezione rotta: niente A4 di
    #     ripiego, il render si ferma e WeasyPrint non parte.
    @patch("apps.documenti.services.render_service._render_with_weasyprint")
    def test_campo_di_pagina_mancante_ferma_il_render(self, mock_weasy) -> None:
        for campo in render_service._CAMPI_PAGINA:
            with self.subTest(campo=campo):
                with self.assertRaises(ServiceError) as ctx:
                    render_service.render_pdf(
                        template_versione=_versione(**{campo: None}),
                        context={"nome": "x"},
                        risolvi_asset=_nessun_asset,
                    )
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
                self.assertIn(campo, ctx.exception.detail)
        mock_weasy.assert_not_called()

    # 27. Il codice finisce in un foglio CSS: un valore che non e' un
    #     identificatore (qui una regola in piu') si rifiuta, come un margine
    #     negativo o non numerico.
    def test_valore_di_pagina_non_identificatore_rifiutato(self) -> None:
        for pagina in (
            {"page_format": "A4; } body { display: none"},
            {"page_orientation": "LANDSCAPE !important"},
            {"margin_top_mm": Decimal("-1")},
            {"margin_left_mm": "dieci"},
        ):
            with self.subTest(pagina=pagina):
                with self.assertRaises(ServiceError) as ctx:
                    render_service._regola_pagina(_versione(**pagina))
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")

    # 28. R-BE-V2b, sulla libreria vera: una versione A3 orizzontale esce A3
    #     orizzontale anche se il template dichiara `@page { size: A4 }` sia
    #     nel CSS sia in uno `<style>` dell'HTML — il caso che fino al
    #     2026-10-04 usciva A4 verticale senza errore. Lo `<style>` e' il
    #     caso duro: e' origine author, e senza `!important` vincerebbe.
    @skipUnless(_weasyprint_disponibile(), "WeasyPrint o le dipendenze native mancano")
    def test_a3_orizzontale_vince_sull_at_page_del_template(self) -> None:
        html = (
            "<html><head><style>@page { size: A4 portrait; margin: 18mm }</style>"
            "</head><body><p>{{ nome }}</p></body></html>"
        )
        css = "@page { size: A4 portrait; margin: 18mm 16mm; }"
        pdf = render_service.render_pdf(
            template_versione=_versione(
                html=html, css=css, page_format="A3", page_orientation="LANDSCAPE",
            ),
            context={"nome": "x"},
            risolvi_asset=_nessun_asset,
        )
        larghezza, altezza = _mediabox(pdf)
        mm = 25.4 / 72
        self.assertAlmostEqual(larghezza * mm, 420, delta=0.5)
        self.assertAlmostEqual(altezza * mm, 297, delta=0.5)

        # E la versione A4 verticale resta A4 verticale.
        pdf = render_service.render_pdf(
            template_versione=_versione(html=html, css=css),
            context={"nome": "x"},
            risolvi_asset=_nessun_asset,
        )
        larghezza, altezza = _mediabox(pdf)
        self.assertAlmostEqual(larghezza * mm, 210, delta=0.5)
        self.assertAlmostEqual(altezza * mm, 297, delta=0.5)

