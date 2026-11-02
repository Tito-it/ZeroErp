# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il patto fra una versione di template e la forma dei dati
#        (brief-db-documenti-versione-contesto-template, R-1/R-3) sul
#        DATABASE VERO: il guard chiesto prima del render e la pubblicazione
#        con la forma del builder del template. E, sulla stessa bozza, i tre
#        vocabolari della versione (brief-db-vocabolari-versione-template):
#        la FK che rifiuta, tradotta sul campo.
# Note: ⭐ Prova la GIUNTURA che i mock non vedono: il binding delle due
#       funzioni (`fn_guard_versione_contesto` a due parametri,
#       `fn_pubblica_template_documento_versione` a quattro, per nome) e la
#       traduzione del rifiuto P0001 in 409 col codice e con la frase a
#       catalogo che nomina le due forme.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, template e versioni dal
#       service. Le forme si fabbricano rispetto a quella del builder, non si
#       leggono da versioni esistenti. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) VersioneContestoDbTests.test_guard_prima_del_render
   la forma giusta passa; quella sbagliata e' un 409
   E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA con le due forme nella frase.
2) VersioneContestoDbTests.test_pubblicazione_con_la_forma_del_builder
   una bozza che legge una forma che il builder non produce non si pubblica
   (409, e resta BOZZA); cambiata la forma in bozza, si pubblica (D-C4).
3) VersioneContestoDbTests.test_vocabolari_della_versione
   i codici dei tre vocabolari si salvano; un valore che il vocabolario non
   ha e' un 400 E_DOCUMENTI_VALIDATION col campo, per ciascuna delle tre FK.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)

# Il builder vero del template: la pubblicazione lo risolve dal registry.
_BUILDER = "CONTRATTO"


class VersioneContestoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto(
            "documenti.fn_guard_versione_contesto(bigint, integer)"
        )

    # Scopo: costruisce il mondo, un template col builder `_BUILDER` e una
    #        versione BOZZA che legge la forma `forma`; torna
    #        (user, template_id, versione).
    def _bozza(self, cur, forma: int):
        from apps.documenti.services.template_admin_service import TemplateAdminService
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT emittente_fiscale_id, auth_user_id FROM _mondo")
        emittente, uid = cur.fetchone()
        cur.execute(
            """
            SELECT (SELECT id FROM documenti.tipi_documento_output ORDER BY id LIMIT 1),
                   (SELECT id FROM config.sorgenti WHERE attivo ORDER BY id LIMIT 1),
                   (SELECT id FROM documenti.render_engine_documento
                     WHERE codice_interno = 'WEASYPRINT')
            """
        )
        tipo_output, sorgente, engine = cur.fetchone()
        user = get_user_model().objects.get(pk=uid)
        template = TemplateAdminService().create_template(user, {
            "tipo_documento_output_id": tipo_output, "sorgente_tipo_id": sorgente,
            "emittente_fiscale_id": emittente,
            "codice": "BE-FORMA-TPL", "codice_interno": "BE_FORMA_TPL",
            "descrizione": "Template forma dei dati",
            "context_builder_code": _BUILDER,
        })
        versione = TemplateVersioniAdminService().create_versione(user, template["id"], {
            "titolo": "Bozza", "html_template": "<p>x</p>",
            "render_engine_id": engine, "versione_contesto": forma,
        })
        self.assertEqual(versione["versione_contesto"], forma)
        return user, template, versione

    # Scopo: il rifiuto di `fn`, com'esce dal traduttore del middleware.
    def _rifiuto(self, fn):
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            return ErrorTranslator.to_api_error(exc)
        self.fail("accettato: la forma dei dati era diversa")

    # 1. Il guard prima del render: la funzione del DB, tradotta dal service
    #    in un ServiceError col codice e con la frase del catalogo.
    def test_guard_prima_del_render(self):
        from apps.documenti.services.context_builders import get_builder
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )

        forma = get_builder(_BUILDER).CONTEXT_VERSION
        svc = DocumentGenerationService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _, template, versione = self._bozza(cur, forma)

                # La forma giusta passa (nessuna eccezione).
                svc._guard_versione_contesto(
                    versione, SimpleNamespace(CODE=_BUILDER, CONTEXT_VERSION=forma),
                )

                api = self._rifiuto(lambda: svc._guard_versione_contesto(
                    versione, SimpleNamespace(CODE=_BUILDER, CONTEXT_VERSION=forma + 1),
                ))
                self.assertEqual(api.code, "E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA")
                self.assertEqual(ErrorTranslator.get_http_status(api), 409)
                self.assertIn(f"nella forma {forma},", api.message)
                self.assertIn(f"nella forma {forma + 1}", api.message)
                self.assertIn(template["descrizione"], api.message)
                raise Annulla
        except Annulla:
            pass

    # 2. La pubblicazione passa al verbo la forma del builder del template:
    #    una bozza preparata per la forma successiva non si pubblica finche'
    #    il builder non la produce (D-C4); riportata alla forma di oggi, si'.
    def test_pubblicazione_con_la_forma_del_builder(self):
        from apps.documenti.services.context_builders import get_builder
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        forma = get_builder(_BUILDER).CONTEXT_VERSION
        svc = TemplateVersioniAdminService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, template, versione = self._bozza(cur, forma + 1)
                tid, vid = template["id"], versione["id"]
                payload = {"valido_dal": oggi_aziendale().isoformat()}

                api = self._rifiuto(lambda: svc.pubblica_versione(user, tid, vid, dict(payload)))
                self.assertEqual(api.code, "E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA")
                self.assertEqual(ErrorTranslator.get_http_status(api), 409)
                self.assertEqual(svc._reader.get_versione(user, tid, vid)["stato"], "BOZZA")

                svc.update_versione(user, tid, vid, {"versione_contesto": forma})
                pubblicata = svc.pubblica_versione(user, tid, vid, dict(payload))
                self.assertEqual(pubblicata["stato"], "PUBBLICATA")
                self.assertEqual(pubblicata["versione_contesto"], forma)
                raise Annulla
        except Annulla:
            pass

    # 3. Formato del sorgente, formato e orientamento della pagina: il
    #    giudice e' la FK sul vocabolario (R-BE-V1), e il suo NOME e' quello
    #    della mappa del service — su un nome sbagliato il rifiuto cadrebbe
    #    nel ripiego senza campo, e nessun mock se ne accorgerebbe. I valori
    #    accettati sono i codici fuori dal default della colonna.
    def test_vocabolari_della_versione(self):
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        svc = TemplateVersioniAdminService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, template, versione = self._bozza(cur, 1)
                tid, vid = template["id"], versione["id"]

                salvata = svc.update_versione(user, tid, vid, {
                    "formato_template": "HTML_MARKDOWN_BLOCKS",
                    "page_format": "A3",
                    "page_orientation": "LANDSCAPE",
                })
                self.assertEqual(
                    (salvata["formato_template"], salvata["page_format"],
                     salvata["page_orientation"]),
                    ("HTML_MARKDOWN_BLOCKS", "A3", "LANDSCAPE"),
                )

                for campo, valore in (
                    ("formato_template", "MARKDOWN"),
                    ("page_format", "A5"),
                    ("page_orientation", "OBLIQUO"),
                ):
                    with self.subTest(campo=campo):
                        api = self._rifiuto(
                            lambda c=campo, v=valore: svc.update_versione(
                                user, tid, vid, {c: v},
                            )
                        )
                        self.assertEqual(api.code, "E_DOCUMENTI_VALIDATION")
                        self.assertEqual(ErrorTranslator.get_http_status(api), 400)
                        self.assertEqual(tuple(api.fields or ()), (campo,))
                raise Annulla
        except Annulla:
            pass
