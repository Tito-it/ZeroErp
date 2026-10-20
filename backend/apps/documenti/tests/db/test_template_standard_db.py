# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I modelli di documento standard (brief-db-modelli-documento-standard
#        §6) sul DATABASE VERO: la risoluzione a due livelli chiesta alla
#        funzione DB, la lettura dello standard dentro il perimetro di un
#        operatore e il rifiuto della scrittura sullo standard.
# Note: ⭐ Prova la GIUNTURA che i mock non vedono: il binding di
#       `documenti.fn_risolvi_template_applicabile` a tre argomenti, la
#       traduzione dei suoi codici in ServiceError, il LEFT JOIN
#       sull'emittente (un JOIN interno toglie lo standard da ogni lettura,
#       senza errore) e il guard `a05` che rifiuta all'applicazione.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero): l'emittente nasce da
#       `fn_pgtap_crea_emittente_operatore`, quindi senza modelli suoi. Lo
#       standard e' quello del seed (`80_data`, cioe' il contratto), cercato
#       per la sua chiave. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) TemplateStandardDbTests.test_emittente_nuovo_usa_lo_standard
   un emittente senza modelli risolve lo standard del preventivo; la riga ha
   `standard` vero e l'emittente nullo, e passa la coerenza della stampa.
2) TemplateStandardDbTests.test_standard_nel_perimetro_dell_operatore
   la lista e il dettaglio dell'operatore mostrano lo standard, che non e'
   di nessuno dei suoi emittenti.
3) TemplateStandardDbTests.test_modello_suo_senza_predefinito_non_usa_lo_standard
   strada B: un modello dell'emittente che PUO' STAMPARE (attivo, con una
   versione pubblicata valida oggi) e non e' predefinito ferma la stampa con
   E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO (409), senza ripiegare. Finche' ha
   la sola bozza non conta, e la stampa resta sullo standard (`20261020-26`).
4) TemplateStandardDbTests.test_standard_in_sola_lettura
   l'applicazione non modifica lo standard:
   E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA (403). Saltato se il test gira
   col proprietario della tabella, che il guard lascia passare per costruzione.
"""
from __future__ import annotations

import unittest

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.config.sorgenti import SORGENTE_PREVENTIVO
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)

# La chiave dello standard del preventivo (seed `20261020-13`): i changeSet di
# evoluzione lo cercano cosi', e cosi' lo cerca il test.
_CODICE_INTERNO_STANDARD = "preventivo"


class TemplateStandardDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto(
            "documenti.fn_risolvi_template_applicabile(bigint, bigint, bigint)"
        )

    # Scopo: costruisce il mondo e legge lo standard del preventivo; torna
    #        (user, emittente_id, sorgente_id, standard).
    def _mondo(self, cur):
        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT emittente_fiscale_id, auth_user_id FROM _mondo")
        emittente, uid = cur.fetchone()
        cur.execute(
            """
            SELECT t.id, t.sorgente_tipo_id, t.tipo_documento_output_id,
                   t.context_builder_code
              FROM documenti.template_documenti t
              JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
             WHERE t.standard
               AND s.codice_interno = %s
               AND t.codice_interno = %s
            """,
            [SORGENTE_PREVENTIVO, _CODICE_INTERNO_STANDARD],
        )
        riga = cur.fetchone()
        self.assertIsNotNone(riga, "lo standard del preventivo manca dal seed")
        standard = dict(zip(("id", "sorgente", "tipo_output", "builder"), riga, strict=True))
        user = get_user_model().objects.get(pk=uid)
        return user, emittente, standard

    # 1. Un emittente nuovo non ha modelli: la stampa risolve lo standard.
    def test_emittente_nuovo_usa_lo_standard(self):
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )

        svc = DocumentGenerationService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, emittente, standard = self._mondo(cur)
                template = svc._resolve_template(
                    user, scope=[emittente], emittente_fiscale_id=emittente,
                    sorgente_tipo_id=standard["sorgente"],
                    tipo_documento_output_id=None, template_documento_id=None,
                )
                self.assertEqual(template["id"], standard["id"])
                self.assertTrue(template["standard"])
                self.assertIsNone(template["emittente_fiscale_id"])
                # La coerenza della stampa ammette lo standard (nessuna eccezione).
                svc._guard_template_coerente(
                    template, emittente_fiscale_id=emittente,
                    sorgente_tipo_id=standard["sorgente"],
                )
                raise Annulla
        except Annulla:
            pass

    # 2. Lo standard si legge da tutti: lista e dettaglio dell'operatore.
    def test_standard_nel_perimetro_dell_operatore(self):
        from apps.documenti.services.template_service import TemplateService

        reader = TemplateService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, _emittente, standard = self._mondo(cur)
                lista = reader.list_templates(
                    user, sorgente_tipo_id=standard["sorgente"], limit=100,
                )
                ids = {r["id"] for r in lista["results"]}
                self.assertIn(standard["id"], ids)
                dettaglio = reader.get_template(user, standard["id"])
                self.assertTrue(dettaglio["standard"])
                self.assertIsNone(dettaglio["emittente_ragione_sociale"])
                raise Annulla
        except Annulla:
            pass

    # 3. Strada B: un modello suo che puo' stampare e non e' predefinito ferma
    #    la stampa, e lo standard NON entra. Con la sola bozza non conta.
    def test_modello_suo_senza_predefinito_non_usa_lo_standard(self):
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )
        from apps.documenti.services.context_builders import get_builder
        from apps.documenti.services.template_admin_service import TemplateAdminService
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        svc = DocumentGenerationService()
        versioni = TemplateVersioniAdminService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, emittente, standard = self._mondo(cur)
                risolvi = {
                    "scope": [emittente], "emittente_fiscale_id": emittente,
                    "sorgente_tipo_id": standard["sorgente"],
                    "tipo_documento_output_id": standard["tipo_output"],
                    "template_documento_id": None,
                }
                suo = TemplateAdminService().create_template(user, {
                    "tipo_documento_output_id": standard["tipo_output"],
                    "sorgente_tipo_id": standard["sorgente"],
                    "emittente_fiscale_id": emittente,
                    "codice": "BE-STD-NODEF", "codice_interno": "be_std_nodef",
                    "descrizione": "Modello suo non predefinito",
                    "context_builder_code": standard["builder"],
                    "is_default": False,
                })
                cur.execute(
                    "SELECT id FROM documenti.render_engine_documento"
                    " WHERE codice_interno = 'WEASYPRINT'"
                )
                bozza = versioni.create_versione(user, suo["id"], {
                    "titolo": "Bozza", "html_template": "<p>x</p>",
                    "render_engine_id": cur.fetchone()[0],
                    "versione_contesto": get_builder(standard["builder"]).CONTEXT_VERSION,
                })
                # Con la sola bozza il modello non puo' stampare: non conta, e
                # lo standard resta (il difetto della copia appena creata da
                # «personalizza», che fermava ogni stampa dell'emittente).
                self.assertEqual(
                    svc._resolve_template(user, **risolvi)["id"], standard["id"],
                )
                versioni.pubblica_versione(
                    user, suo["id"], bozza["id"],
                    {"valido_dal": oggi_aziendale().isoformat()},
                )
                with self.assertRaises(ServiceError) as ctx:
                    with transaction.atomic():
                        svc._resolve_template(user, **risolvi)
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO")
                api = ErrorTranslator.to_api_error(ctx.exception)
                self.assertEqual(ErrorTranslator.get_http_status(api), 409)
                raise Annulla
        except Annulla:
            pass

    # 4. Lo standard non si scrive dall'applicazione: il rifiuto e' del DB.
    def test_standard_in_sola_lettura(self):
        from apps.documenti.services.template_admin_service import TemplateAdminService

        with connection.cursor() as cur:
            cur.execute(
                "SELECT script.fn_is_proprietario_tabella('documenti.template_documenti'::regclass)"
            )
            if cur.fetchone()[0]:
                self.skipTest(
                    "connessione col proprietario della tabella: il guard lo lascia "
                    "passare per costruzione (seed e changeSet)"
                )
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, _emittente, standard = self._mondo(cur)
                try:
                    with transaction.atomic():
                        TemplateAdminService().update_template(
                            user, standard["id"], {"descrizione": "Ritoccato"},
                        )
                except Exception as exc:  # la strada e' cio' che si prova
                    api = ErrorTranslator.to_api_error(exc)
                else:
                    self.fail("lo standard e' stato modificato dall'applicazione")
                self.assertEqual(api.code, "E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA")
                self.assertEqual(ErrorTranslator.get_http_status(api), 403)
                raise Annulla
        except Annulla:
            pass
