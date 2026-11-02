# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I modelli di documento standard (brief-db-modelli-documento-standard
#        §6) sul DATABASE VERO: la risoluzione a due livelli chiesta alla
#        funzione DB, la lettura dello standard dentro il perimetro di un
#        operatore e il rifiuto della scrittura sullo standard.
# Note: ⭐ Prova la GIUNTURA che i mock non vedono: il binding della porta
#       unica `documenti.fn_risolvi_template_applicabile` a QUATTRO argomenti
#       (anche col modello indicato), la traduzione dei suoi codici in
#       ServiceError, il LEFT JOIN sull'emittente (un JOIN interno toglie lo
#       standard da ogni lettura, senza errore), il guard `a05` che rifiuta
#       all'applicazione e le due funzioni madri di «personalizza» e del clone.
#       ⛔ La sonda e' la FIRMA: fino al 2026-10-21 cercava quella a tre
#       argomenti, che dall'apply di K-2 non esiste piu', e l'intera classe si
#       saltava da sola — verde senza verificare niente (brief §11.2 B-1).
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
5) TemplateStandardDbTests.test_personalizza_dichiara_l_origine_e_stampa_da_pubblicata
   «personalizza» (la madre del DB) crea il modello dell'emittente, predefinito
   perche' l'emittente non ne ha (D-6), con la versione 1 in BOZZA che dichiara
   `derivata_da_versione_id`; finche' e' bozza la stampa resta sullo standard,
   pubblicata stampa la copia, e la vista dello scarto la da' ALLINEATA.
6) TemplateStandardDbTests.test_modello_indicato_verificato_dalla_porta
   il modello indicato passa dalla porta: lo standard va bene per l'emittente
   nuovo (livello INDICATO, la sua versione); il modello di un'altra azienda,
   letto da chi la vede, e' E_DOCUMENTI_TEMPLATE_NON_COERENTE (400); il
   modello suo con la sola bozza, e poi spento, e' E_DOCUMENTI_TEMPLATE_NON_STAMPABILE
   (409), col motivo nella frase.
7) TemplateStandardDbTests.test_clone_numera_e_copia_il_db
   il clone di una versione passa da `fn_crea_bozza_da_versione`: BOZZA col
   numero successivo, corpo e forma dell'origine, senza date, col titolo
   sostituito.
8) TemplateStandardDbTests.test_lista_dice_standard_scarto_e_risoluzione
   la lista filtra gli standard; la copia pubblicata porta `stato_scarto`
   ALLINEATA (dalla vista del DB); la risoluzione per azienda dice STANDARD
   per l'emittente nuovo, EMITTENTE dopo la copia, SENZA_PREDEFINITO con un
   modello suo non predefinito che stampa.
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
from apps.documenti.db.documenti_repository import DocumentiRepository

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
            "documenti.fn_risolvi_template_applicabile(bigint, bigint, bigint, bigint)"
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
                template, versione = svc._resolve_template(
                    user, scope=[emittente], emittente_fiscale_id=emittente,
                    sorgente_tipo_id=standard["sorgente"],
                    tipo_documento_output_id=None, template_documento_id=None,
                )
                self.assertEqual(template["id"], standard["id"])
                # Modello e versione li dice la porta; la versione e' di QUESTO
                # modello e stampa oggi.
                self.assertEqual(versione["template_documento_id"], standard["id"])
                self.assertEqual(versione["stato"], "PUBBLICATA")
                self.assertTrue(template["standard"])
                self.assertIsNone(template["emittente_fiscale_id"])
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
                    svc._resolve_template(user, **risolvi)[0]["id"], standard["id"],
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

    # 5. «Personalizza»: la copia dichiara l'origine, stampa solo da pubblicata.
    def test_personalizza_dichiara_l_origine_e_stampa_da_pubblicata(self):
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )
        from apps.documenti.services.template_admin_service import TemplateAdminService
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        svc = DocumentGenerationService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, emittente, standard = self._mondo(cur)
                risolvi = {
                    "scope": [emittente], "emittente_fiscale_id": emittente,
                    "sorgente_tipo_id": standard["sorgente"],
                    "tipo_documento_output_id": standard["tipo_output"],
                    "template_documento_id": None,
                }
                copia = TemplateAdminService().personalizza_template(
                    user, standard["id"], {"emittente_fiscale_id": emittente},
                )
                self.assertFalse(copia["standard"])
                self.assertEqual(copia["emittente_fiscale_id"], emittente)
                self.assertTrue(copia["is_default"])

                cur.execute(
                    """
                    SELECT v.id, v.stato, o.template_documento_id
                      FROM documenti.template_documenti_versioni v
                      JOIN documenti.template_documenti_versioni o
                        ON o.id = v.derivata_da_versione_id
                     WHERE v.template_documento_id = %s
                    """,
                    [copia["id"]],
                )
                righe = cur.fetchall()
                self.assertEqual(len(righe), 1)
                bozza_id, stato, origine_template = righe[0]
                self.assertEqual(stato, "BOZZA")
                self.assertEqual(origine_template, standard["id"])

                # Con la sola bozza la copia non puo' stampare: resta lo standard.
                self.assertEqual(
                    svc._resolve_template(user, **risolvi)[0]["id"], standard["id"],
                )
                TemplateVersioniAdminService().pubblica_versione(
                    user, copia["id"], bozza_id,
                    {"valido_dal": oggi_aziendale().isoformat()},
                )
                template, versione = svc._resolve_template(user, **risolvi)
                self.assertEqual(template["id"], copia["id"])
                self.assertEqual(versione["id"], bozza_id)

                cur.execute(
                    "SELECT stato FROM documenti.vw_template_personalizzati_scarto"
                    " WHERE template_documento_id = %s",
                    [copia["id"]],
                )
                self.assertEqual(cur.fetchone(), ("ALLINEATA",))
                raise Annulla
        except Annulla:
            pass

    # 6. Il modello indicato: lo verifica la porta, e i rifiuti hanno i codici
    #    del DB (prima: una copia BE della coerenza, e la versione cercata dal
    #    BE anche su un modello spento).
    def test_modello_indicato_verificato_dalla_porta(self):
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )
        from apps.documenti.services.template_admin_service import TemplateAdminService
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        svc = DocumentGenerationService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, emittente, standard = self._mondo(cur)
                # Un secondo emittente, con la sua copia dello standard.
                cur.execute(
                    "SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente_operatore()"
                )
                altro = cur.fetchone()[0]
                indica = {
                    "emittente_fiscale_id": emittente,
                    "sorgente_tipo_id": standard["sorgente"],
                    "tipo_documento_output_id": standard["tipo_output"],
                }

                # a) lo standard indicato va bene per chiunque: livello INDICATO.
                template, versione = svc._resolve_template(
                    user, scope=None, template_documento_id=standard["id"], **indica,
                )
                self.assertEqual(template["id"], standard["id"])
                self.assertEqual(versione["template_documento_id"], standard["id"])

                # b) il modello di un'altra azienda (chi stampa la vede: scope
                #    None) non e' adatto: NON_COERENTE, 400. La copia la scrive
                #    la madre del DB: l'operatore del test non ha quell'azienda.
                copia_altro = DocumentiRepository().personalizza_template_standard(
                    standard["id"], emittente_fiscale_id=altro, codice=None,
                    codice_interno=None, descrizione=None, is_default=None,
                )
                with self.assertRaises(ServiceError) as ctx:
                    with transaction.atomic():
                        svc._resolve_template(
                            user, scope=None,
                            template_documento_id=copia_altro, **indica,
                        )
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_TEMPLATE_NON_COERENTE")
                api = ErrorTranslator.to_api_error(ctx.exception)
                self.assertEqual(ErrorTranslator.get_http_status(api), 400)

                # c) il modello suo che oggi non stampa: NON_STAMPABILE, 409.
                #    Prima con la sola bozza (nessuna versione valida), poi
                #    spento — figli prima del padre, li spegne il DB in
                #    quest'ordine. Fino al 2026-10-21 il BE cercava la versione
                #    da se', e il modello spento stampava ancora.
                copia = TemplateAdminService().personalizza_template(
                    user, standard["id"], {"emittente_fiscale_id": emittente},
                )
                cur.execute(
                    "SELECT id FROM documenti.template_documenti_versioni"
                    " WHERE template_documento_id = %s",
                    [copia["id"]],
                )
                bozza_id = cur.fetchone()[0]
                for motivo in ("non ha una versione", "disattivato"):
                    if motivo == "disattivato":
                        TemplateVersioniAdminService().update_versione(
                            user, copia["id"], bozza_id, {"attivo": False},
                        )
                        TemplateAdminService().update_template(
                            user, copia["id"], {"attivo": False},
                        )
                    with self.subTest(motivo=motivo):
                        with self.assertRaises(ServiceError) as ctx:
                            with transaction.atomic():
                                svc._resolve_template(
                                    user, scope=None,
                                    template_documento_id=copia["id"], **indica,
                                )
                        self.assertEqual(
                            ctx.exception.code, "E_DOCUMENTI_TEMPLATE_NON_STAMPABILE",
                        )
                        self.assertIn(motivo, ctx.exception.message)
                        api = ErrorTranslator.to_api_error(ctx.exception)
                        self.assertEqual(ErrorTranslator.get_http_status(api), 409)
                raise Annulla
        except Annulla:
            pass

    # 7. Il clone di una versione lo fa il DB: numero, corpo e forma suoi.
    def test_clone_numera_e_copia_il_db(self):
        from apps.documenti.services.template_admin_service import TemplateAdminService
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        versioni = TemplateVersioniAdminService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, emittente, standard = self._mondo(cur)
                copia = TemplateAdminService().personalizza_template(
                    user, standard["id"], {"emittente_fiscale_id": emittente},
                )
                cur.execute(
                    "SELECT id, versione, html_template, versione_contesto"
                    "  FROM documenti.template_documenti_versioni"
                    " WHERE template_documento_id = %s",
                    [copia["id"]],
                )
                origine_id, numero, html, forma = cur.fetchone()
                clone = versioni.clone_versione(
                    user, copia["id"], origine_id, {"titolo": "Clone di prova"},
                )
                self.assertEqual(clone["versione"], numero + 1)
                self.assertEqual(clone["stato"], "BOZZA")
                self.assertEqual(clone["titolo"], "Clone di prova")
                self.assertEqual(clone["html_template"], html)
                self.assertEqual(clone["versione_contesto"], forma)
                self.assertIsNone(clone["valido_dal"])
                raise Annulla
        except Annulla:
            pass

    # 8. La lista: «Standard» filtra, «Allineamento allo standard» e «con che
    #    cosa stampa ogni azienda» sono letture del DB.
    def test_lista_dice_standard_scarto_e_risoluzione(self):
        from apps.documenti.services.template_admin_service import TemplateAdminService
        from apps.documenti.services.template_service import TemplateService
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        reader = TemplateService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                user, emittente, standard = self._mondo(cur)

                def esito() -> str:
                    righe = reader.list_risoluzione_emittenti(
                        user, emittente_fiscale_id=emittente,
                    )["results"]
                    mie = [
                        r for r in righe
                        if r["tipo_documento_output_id"] == standard["tipo_output"]
                        and r["sorgente_tipo_id"] == standard["sorgente"]
                    ]
                    self.assertEqual(len(mie), 1, righe)
                    return mie[0]["esito"]

                solo_standard = reader.list_templates(
                    user, standard=True, attivo=None, limit=100,
                )["results"]
                self.assertTrue(solo_standard)
                self.assertTrue(all(r["standard"] for r in solo_standard))
                self.assertIn("stato_scarto", solo_standard[0])
                self.assertEqual(esito(), "STANDARD")

                copia = TemplateAdminService().personalizza_template(
                    user, standard["id"], {"emittente_fiscale_id": emittente},
                )
                cur.execute(
                    "SELECT id FROM documenti.template_documenti_versioni"
                    " WHERE template_documento_id = %s",
                    [copia["id"]],
                )
                TemplateVersioniAdminService().pubblica_versione(
                    user, copia["id"], cur.fetchone()[0],
                    {"valido_dal": oggi_aziendale().isoformat()},
                )
                righe = reader.list_templates(
                    user, standard=False, emittente_fiscale_id=emittente, limit=100,
                )["results"]
                self.assertEqual([r["stato_scarto"] for r in righe if r["id"] == copia["id"]], ["ALLINEATA"])
                self.assertEqual(esito(), "EMITTENTE")

                # La copia non piu' predefinita, ma stampa: strada B.
                TemplateAdminService().update_template(user, copia["id"], {"is_default": False})
                self.assertEqual(esito(), "SENZA_PREDEFINITO")
                raise Annulla
        except Annulla:
            pass
