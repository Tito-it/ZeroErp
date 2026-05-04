# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
#         - css_template assente -> stylesheets None (no CSS).
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
#  10. render_pdf_css_opzionale_none_quando_assente
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.documenti.services import render_service


def _versione(
    *,
    html: str = "<html><body>Hello {{ nome }}</body></html>",
    css: str | None = "body { font-family: sans-serif; }",
    engine: str = "WEASYPRINT",
    versione_id: int = 99,
) -> dict[str, Any]:
    return {
        "id": versione_id,
        "html_template": html,
        "css_template": css,
        "render_engine_codice": engine,
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
        )
        html_arg, _ = mock_weasy.call_args.args
        self.assertIn("<li>a</li>", html_arg)
        self.assertIn("<li>b</li>", html_arg)


class RenderPdfWeasyPrintTests(TestCase):
    """Render WeasyPrint: eccezione interna + output vuoto."""

    # 7. WeasyPrint solleva -> mappato a E_DOCUMENTI_RENDER_FAILED.
    def test_render_pdf_weasyprint_exception_mapped(self) -> None:
        # Patcho weasyprint.HTML in modo che write_pdf sollevi.
        fake_html = MagicMock()
        fake_html.return_value.write_pdf.side_effect = RuntimeError("font missing")
        fake_css = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "weasyprint": MagicMock(HTML=fake_html, CSS=fake_css),
            },
        ):
            with self.assertRaises(ServiceError) as ctx:
                render_service.render_pdf(
                    template_versione=_versione(),
                    context={"nome": "x"},
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
            {
                "weasyprint": MagicMock(HTML=fake_html, CSS=fake_css),
            },
        ):
            with self.assertRaises(ServiceError) as ctx:
                render_service.render_pdf(
                    template_versione=_versione(),
                    context={"nome": "x"},
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("vuoto", ctx.exception.message.lower())

    # 10. css_template None/vuoto -> stylesheets=None passato a write_pdf.
    def test_render_pdf_css_opzionale_none_quando_assente(self) -> None:
        fake_html_instance = MagicMock()
        fake_html_instance.write_pdf.return_value = b"PDF"
        fake_html = MagicMock(return_value=fake_html_instance)
        fake_css = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "weasyprint": MagicMock(HTML=fake_html, CSS=fake_css),
            },
        ):
            render_service.render_pdf(
                template_versione=_versione(css=None),
                context={"nome": "x"},
            )
        # write_pdf invocato con stylesheets=None (no CSS).
        kwargs = fake_html_instance.write_pdf.call_args.kwargs
        self.assertIsNone(kwargs.get("stylesheets"))
