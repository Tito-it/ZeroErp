# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per sanitize_email_html (Fase 6 amm-software).
#        Whitelist tag/attr/protocol — defense-in-depth con iframe sandbox FE.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_empty_input_returns_empty — None, '' → ''
 2) test_safe_html_preserved — HTML innocuo passa invariato (p, a, strong)
 3) test_script_tag_stripped — <script> rimosso completamente
 4) test_event_handler_stripped — onclick, onerror, onload rimossi
 5) test_javascript_protocol_stripped — href="javascript:..." rimosso
 6) test_data_protocol_stripped — src="data:..." rimosso (non in whitelist)
 7) test_iframe_object_embed_stripped — tag pericolosi rimossi
 8) test_style_attribute_stripped — style globale non whitelisted
 9) test_html_comment_stripped — commenti HTML rimossi
10) test_table_tags_preserved — table/tr/td/th preservati
11) test_mailto_protocol_allowed — href="mailto:..." passa
"""

from unittest import TestCase

from apps.core.services.html_sanitizer_service import sanitize_email_html


class TestSanitizeEmailHtml(TestCase):
    """Whitelist sanitization per anteprime template email."""

    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(sanitize_email_html(None), "")
        self.assertEqual(sanitize_email_html(""), "")

    def test_safe_html_preserved(self) -> None:
        # Scopo: HTML coerente con whitelist passa invariato.
        html = '<p>Ciao <strong>mondo</strong>, vai a <a href="https://example.com">ex</a></p>'
        self.assertEqual(sanitize_email_html(html), html)

    def test_script_tag_stripped(self) -> None:
        # Scopo: <script> non e' nella whitelist → rimosso (strip=True).
        html = '<p>Hello</p><script>alert("xss")</script>'
        result = sanitize_email_html(html)
        self.assertNotIn("<script>", result)
        self.assertNotIn("alert", result)
        self.assertIn("<p>Hello</p>", result)

    def test_event_handler_stripped(self) -> None:
        # Scopo: onclick/onerror/onload non sono nella whitelist attributi → rimossi.
        html = '<p onclick="bad()">click</p><img src="x.png" onerror="bad()">'
        result = sanitize_email_html(html)
        self.assertNotIn("onclick", result)
        self.assertNotIn("onerror", result)
        self.assertNotIn("bad()", result)

    def test_javascript_protocol_stripped(self) -> None:
        # Scopo: javascript: non e' tra i protocols ammessi → href rimosso.
        html = '<a href="javascript:alert(1)">link</a>'
        result = sanitize_email_html(html)
        self.assertNotIn("javascript:", result)

    def test_data_protocol_stripped(self) -> None:
        # Scopo: data: URI non e' tra i protocols ammessi → src rimosso.
        html = '<img src="data:image/png;base64,AAA">'
        result = sanitize_email_html(html)
        self.assertNotIn("data:", result)

    def test_iframe_object_embed_stripped(self) -> None:
        # Scopo: tag fuori whitelist rimossi (strip=True elimina tag, mantiene contenuto).
        html = '<iframe src="https://evil.test"></iframe><object></object><embed>'
        result = sanitize_email_html(html)
        self.assertNotIn("<iframe", result)
        self.assertNotIn("<object", result)
        self.assertNotIn("<embed", result)

    def test_style_attribute_stripped(self) -> None:
        # Scopo: style globale non e' nella whitelist attributi → rimosso.
        html = '<p style="color:red">x</p>'
        result = sanitize_email_html(html)
        self.assertNotIn("style=", result)
        self.assertIn("<p>", result)

    def test_html_comment_stripped(self) -> None:
        # Scopo: i commenti HTML possono nascondere payload IE-conditional → rimossi.
        html = '<p>x</p><!-- pippo -->'
        result = sanitize_email_html(html)
        self.assertNotIn("<!--", result)

    def test_table_tags_preserved(self) -> None:
        # Scopo: i template email usano spesso <table> per layout → whitelistati.
        html = '<table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>'
        result = sanitize_email_html(html)
        self.assertIn("<table>", result)
        self.assertIn("<thead>", result)
        self.assertIn("<th>A</th>", result)
        self.assertIn("<td>1</td>", result)

    def test_mailto_protocol_allowed(self) -> None:
        # Scopo: mailto e' nella whitelist protocols → href preservato.
        html = '<a href="mailto:a@b.it">scrivici</a>'
        result = sanitize_email_html(html)
        self.assertIn('href="mailto:a@b.it"', result)
