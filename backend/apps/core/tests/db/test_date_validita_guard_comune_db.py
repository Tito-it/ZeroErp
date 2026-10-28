# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La regola del PERIODO — valido_al non precede valido_dal — sul
#        DATABASE PROVVISTO, attraverso ogni service che fino al 2026-09-23 la
#        ripeteva in Python. Da quel giorno la giudica solo il guard comune
#        `script.trgfn_guard_date_validita` (brief-db-guard-date-validita), e
#        le copie del backend sono state ritirate: questo file prova che, al
#        loro posto, l'operatore riceve lo stesso rifiuto da OGNI punto —
#        codice `E_DATA_AL_MINORE_DAL`, campo `valido_al`, status 400.
# Note: ⭐ La giuntura, non la regola. La regola la provano i pgTAP del guard;
#       qui si prova il TRASPORTO, che e' diverso per ogni service: chi cattura
#       il solo `IntegrityError` lascia arrivare il `P0001` nudo al middleware,
#       chi usa `raise_from_database_error` (i contratti) fino al 2026-09-23
#       lo riconosceva solo se in `known_markers`, e col `message` del service
#       («Violazione vincolo contrattuale.»): da allora il BB fa vincere sempre
#       il codice del catalogo, con la sua frase. Ogni rifiuto passa percio' da
#       `ErrorTranslator.to_api_error`, lo stesso punto del middleware.
#       ⚠️ Un file solo e non uno per app: la regola e' una, e l'asserzione e'
#       la stessa per tutti — tre copie dell'helper sarebbero la regola del 2.
#       ⚠️ Il mondo si COSTRUISCE (azienda + operatore, cliente, articolo,
#       filiale dai BB `dbops.fn_pgtap_crea_*`; listino e template sui
#       vocabolari di seed), in transazione ANNULLATA; ogni rifiuto in un
#       SAVEPOINT.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) DateValiditaGuardComuneDbTests.test_contratti_create_update_e_cessazione
2) DateValiditaGuardComuneDbTests.test_promo_create_e_update
3) DateValiditaGuardComuneDbTests.test_categorie_clienti_listini_create_e_update
4) DateValiditaGuardComuneDbTests.test_conti_bancari_soggetto_e_ruolo
5) DateValiditaGuardComuneDbTests.test_template_versioni_create_clone_update_pubblica
6) DateValiditaGuardComuneDbTests.test_template_asset_upload_e_update
7) DateValiditaGuardComuneDbTests.test_catalogo_uom_operativa_componenti_conversioni
"""
from __future__ import annotations

import unittest
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import richiedi_db_provvisto

_OGGI = oggi_aziendale()
_DAL = _OGGI + timedelta(days=30)
_AL_PRIMA = _OGGI + timedelta(days=10)  # futura, ma prima di _DAL
_AL_DOPO = _OGGI + timedelta(days=60)

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
    """
    CREATE TEMP TABLE _cliente AS
    SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba(
        'date validita', NULL, (SELECT soggetto_ruolo_id FROM _mondo)) c
    """,
)


class _Mondo:
    """Gli id del mondo costruito."""

    def __init__(self, cur) -> None:
        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT emittente_fiscale_id, soggetto_ruolo_id, auth_user_id FROM _mondo")
        self.emittente_id, self.emittente_sr, self.uid = (int(x) for x in cur.fetchone())
        cur.execute(
            "SELECT billing_account_id, istanza_utility_id, soggetto_ruolo_id, "
            "soggetto_id, utility_id FROM _cliente"
        )
        ba, iu, sr, sogg, util = cur.fetchone()
        self.ba, self.istanza, self.cliente_sr = int(ba), int(iu), int(sr)
        self.cliente_soggetto, self.utility = str(sogg), int(util)
        self.user = get_user_model().objects.get(pk=self.uid)


class DateValiditaGuardComuneDbTests(unittest.TestCase):
    """Ogni service che scrive un periodo riceve il rifiuto del guard comune."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("script.trgfn_guard_date_validita()")

    # Scopo: esegue `azione(cur, mondo)` in una transazione SEMPRE annullata.
    def _nel_mondo(self, azione) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    azione(cur, _Mondo(cur))
            finally:
                transaction.set_rollback(True)

    # Scopo: l'unica asserzione del file. `fn` deve essere rifiutata, in un
    #        savepoint, e il rifiuto — qualunque strada abbia fatto nel service,
    #        ServiceError tradotto o DatabaseError nudo — deve uscire dal
    #        traduttore del middleware come il guard comune lo ha sollevato.
    #        ⚠️ Niente eccezioni per codice: dal 2026-09-24 il DB non ha piu'
    #        copie della regola (brief-db-guard-date-validita §14), e un
    #        parametro per dichiararne una sarebbe la porta per rimetterla.
    def _rifiuto_del_periodo(self, punto: str, fn) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            with self.subTest(punto=punto):
                self.assertEqual(
                    api.code, "E_DATA_AL_MINORE_DAL",
                    f"{punto}: rifiutato con {api.code} ({api.message}) — {exc!r}",
                )
                self.assertIn("valido_al", api.fields or (), f"{punto}: campo assente")
                self.assertEqual(ErrorTranslator.get_http_status(api), 400, punto)
                self.assertEqual(api.ui_action, "highlight_form_fields", punto)
                # La frase e' quella del catalogo, con le DUE date — non
                # quella del service (i contratti, fino alla decisione A
                # del 2026-09-23, dicevano «Violazione vincolo contrattuale.»).
                for data in (_AL_PRIMA, _DAL):
                    self.assertIn(data.isoformat(), api.message, f"{punto}: {api.message!r}")
            return
        self.fail(f"{punto}: date invertite accettate")

    # 1. Contratti: tre punti, e il traduttore che riconosce solo i codici in
    #    lista. La cessazione e' PROGRAMMATA (data futura): scrive solo valido_al.
    #    ⚠️ Si cessa un contratto ATTIVO: dal 2026-10-26 la cessazione passa da
    #    `vendite.fn_cessa_contratto`, che prima della data guarda la strada
    #    dalla matrice — da bozza a CESSATO non c'e' (brief-modello-documento-
    #    vendita §11.6). L'attivazione chiede `emetti_contratto` e un listino.
    def test_contratti_create_update_e_cessazione(self):
        from apps.vendite.services.contratti_service import ContrattiService

        def _prova(cur, m):
            svc = ContrattiService()
            base = {
                "billing_account_id": m.ba,
                "istanza_utility_id": m.istanza,
                "utility_id": m.utility,
                "valido_dal": _DAL.isoformat(),
            }
            self._rifiuto_del_periodo(
                "contratti.create",
                lambda: svc.create_contratto({**base, "valido_al": _AL_PRIMA.isoformat()}),
            )
            contratto = svc.create_contratto(base)
            self._rifiuto_del_periodo(
                "contratti.update",
                lambda: svc.update_contratto(contratto["id"], {
                    "valido_dal": _DAL.isoformat(), "valido_al": _AL_PRIMA.isoformat(),
                }),
            )
            cur.execute(
                "SELECT listino_id FROM dbops.fn_pgtap_crea_listino(%s, 'date validita')",
                [m.utility],
            )
            listino_id = int(cur.fetchone()[0])
            cur.execute("SELECT dbops.fn_pgtap_concedi_azione(%s, 'emetti_contratto')", [m.uid])
            attivo = svc.create_contratto({**base, "listino_id": listino_id})
            svc.emetti(attivo["id"])
            self._rifiuto_del_periodo(
                "contratti.cambia_stato(CESSATO)",
                lambda: svc.cambia_stato(
                    attivo["id"], codice_interno="CESSATO", valido_al=_AL_PRIMA,
                ),
            )
        self._nel_mondo(_prova)

    # 2. Promo: create e update (promo FUTURA, si sposta solo valido_al).
    def test_promo_create_e_update(self):
        from apps.vendite.services.promo_articoli_service import PromoArticoliService

        def _prova(cur, m):
            cur.execute("SELECT dbops.fn_pgtap_crea_articolo('BE-DATE-PROMO')")
            articolo = str(cur.fetchone()[0])
            cur.execute("SELECT uom_id FROM catalogo.articoli WHERE id = %s", [articolo])
            uom = int(cur.fetchone()[0])
            svc = PromoArticoliService()
            base = {
                "codice": "BE-DATE-PROMO", "descrizione": "Promo date",
                "articolo_id": articolo, "uom_id": uom,
                "tipo_variazione": "PERCENTUALE", "valore_variazione": "-10",
                "valido_dal": _DAL.isoformat(),
            }
            self._rifiuto_del_periodo(
                "promo.create",
                lambda: svc.create_promo({**base, "valido_al": _AL_PRIMA.isoformat()}),
            )
            promo = svc.create_promo({**base, "valido_al": _AL_DOPO.isoformat()})
            self._rifiuto_del_periodo(
                "promo.update",
                lambda: svc.update_promo(promo["id"], {"valido_al": _AL_PRIMA.isoformat()}),
            )
        self._nel_mondo(_prova)

    # 3. Matrice categoria cliente/listino: create e update.
    def test_categorie_clienti_listini_create_e_update(self):
        from apps.anagrafiche.services.categorie_clienti_listini_service import (
            CategorieClientiListiniService,
        )

        def _prova(cur, m):
            cur.execute(
                """
                INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id,
                                             emittente_soggetto_ruolo_id)
                SELECT 'BE-DATE-' || substr(gen_random_uuid()::text, 1, 8), 'Listino date',
                       %s, tu.tipologia_id, %s
                  FROM config.listini_tipologie_utilities tu
                 WHERE tu.utility_id = %s AND tu.attivo
                 ORDER BY tu.id LIMIT 1
                RETURNING id
                """,
                [m.utility, m.emittente_sr, m.utility],
            )
            listino = int(cur.fetchone()[0])
            cur.execute("SELECT id FROM anagrafiche.categorie_clienti ORDER BY id LIMIT 1")
            categoria = int(cur.fetchone()[0])
            svc = CategorieClientiListiniService()
            base = {
                "categoria_cliente_id": categoria, "utility_id": m.utility,
                "emittente_soggetto_ruolo_id": m.emittente_sr, "listino_id": listino,
                "valido_dal": _DAL.isoformat(),
            }
            self._rifiuto_del_periodo(
                "categorie_clienti_listini.create",
                lambda: svc.create_matrice({**base, "valido_al": _AL_PRIMA.isoformat()}),
            )
            riga = svc.create_matrice(base)
            self._rifiuto_del_periodo(
                "categorie_clienti_listini.update",
                lambda: svc.update_matrice(riga["id"], {"valido_al": _AL_PRIMA.isoformat()}),
            )
        self._nel_mondo(_prova)

    # 4. Conti bancari del soggetto e del ruolo: la copia stava nel FRONTEND
    #    (useContoBancarioForm), il service non cattura niente — P0001 nudo.
    def test_conti_bancari_soggetto_e_ruolo(self):
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService

        def _prova(cur, m):
            cur.execute("SELECT bank_branch_id FROM dbops.fn_pgtap_crea_filiale_bancaria('date')")
            filiale = int(cur.fetchone()[0])
            iban = "IT" + uuid.uuid4().hex[:25].upper()
            svc = ContiBancariService()
            payload = {
                "iban": iban, "bank_branch_id": filiale, "uso": "GENERICO",
                "valido_dal": _DAL.isoformat(), "valido_al": _AL_PRIMA.isoformat(),
            }
            self._rifiuto_del_periodo(
                "conti_bancari.create_soggetto",
                lambda: svc.create_conto_soggetto(m.cliente_soggetto, dict(payload)),
            )
            self._rifiuto_del_periodo(
                "conti_bancari.create_ruolo",
                lambda: svc.create_conto_ruolo(m.cliente_sr, dict(payload)),
            )
        self._nel_mondo(_prova)

    # 5. Versioni dei template: create, clone, update e pubblicazione.
    def test_template_versioni_create_clone_update_pubblica(self):
        from apps.documenti.services.context_builders import get_builder
        from apps.documenti.services.template_admin_service import TemplateAdminService
        from apps.documenti.services.template_versioni_admin_service import (
            TemplateVersioniAdminService,
        )

        def _prova(cur, m):
            cur.execute(
                """
                SELECT (SELECT id FROM documenti.tipi_documento_output WHERE codice_interno = 'CONTRATTO'),
                       (SELECT id FROM config.sorgenti ORDER BY id LIMIT 1),
                       (SELECT id FROM documenti.render_engine_documento WHERE codice_interno = 'WEASYPRINT')
                """
            )
            tipo_output, sorgente, engine = (int(x) for x in cur.fetchone())
            # Un builder vero: la pubblicazione ne legge la forma.
            builder = "CONTRATTO"
            template = TemplateAdminService().create_template(m.user, {
                "tipo_documento_output_id": tipo_output, "sorgente_tipo_id": sorgente,
                "emittente_fiscale_id": m.emittente_id,
                "codice": "BE-DATE-TPL", "codice_interno": "BE_DATE_TPL",
                "descrizione": "Template date", "context_builder_code": builder,
            })
            tid = template["id"]
            svc = TemplateVersioniAdminService()
            # Il builder vero del template e la sua forma: la pubblicazione
            # passa dal patto versione/forma dei dati PRIMA del guard delle
            # date, e con una forma diversa si fermerebbe li'.
            forma = get_builder(builder).CONTEXT_VERSION
            base = {
                "titolo": "V", "html_template": "<p>x</p>", "render_engine_id": engine,
                "versione_contesto": forma,
            }
            date_invertite = {"valido_dal": _DAL.isoformat(), "valido_al": _AL_PRIMA.isoformat()}
            self._rifiuto_del_periodo(
                "template_versioni.create",
                lambda: svc.create_versione(m.user, tid, {**base, **date_invertite}),
            )
            versione = svc.create_versione(m.user, tid, base)
            self._rifiuto_del_periodo(
                "template_versioni.clone",
                lambda: svc.clone_versione(m.user, tid, versione["id"], dict(date_invertite)),
            )
            self._rifiuto_del_periodo(
                "template_versioni.update",
                lambda: svc.update_versione(m.user, tid, versione["id"], dict(date_invertite)),
            )
            self._rifiuto_del_periodo(
                "template_versioni.pubblica",
                lambda: svc.pubblica_versione(m.user, tid, versione["id"], dict(date_invertite)),
            )
        self._nel_mondo(_prova)

    # 6. Asset dei template: upload (l'INSERT precede la scrittura del file,
    #    quindi il rifiuto non lascia file) e update dei metadati.
    def test_template_asset_upload_e_update(self):
        from apps.documenti.services.template_asset_admin_service import (
            TemplateAssetAdminService,
        )

        def _prova(cur, m):
            cur.execute("SELECT id FROM documenti.tipi_asset_documento WHERE codice_interno = 'LOGO'")
            tipo_logo = int(cur.fetchone()[0])
            svc = TemplateAssetAdminService()
            metadati = {
                "codice": "BE-DATE-LOGO", "codice_interno": "BE_DATE_LOGO",
                "descrizione": "Logo date", "asset_tipo_id": tipo_logo,
                "emittente_fiscale_id": m.emittente_id,
                "valido_dal": _DAL.isoformat(), "valido_al": _AL_PRIMA.isoformat(),
            }
            png = b"\x89PNG\r\n\x1a\n" + uuid.uuid4().bytes
            self._rifiuto_del_periodo(
                "template_asset.upload",
                lambda: svc.upload_asset(m.user, dict(metadati), png, "image/png", "logo.png"),
            )
            # L'asset da aggiornare si scrive a mano: un upload valido
            # lascerebbe un file vero nello storage.
            cur.execute(
                """
                INSERT INTO documenti.template_asset (codice, codice_interno, descrizione,
                       asset_tipo_id, mime_type, file_name, file_size_bytes, storage_key,
                       sha256, emittente_fiscale_id, valido_dal)
                VALUES ('BE-DATE-LOGO2', 'BE_DATE_LOGO2', 'Logo date 2', %s, 'image/png',
                        'logo.png', 16, 'assets/be-date/logo.png', %s, %s, %s)
                RETURNING id
                """,
                [tipo_logo, uuid.uuid4().hex * 2, m.emittente_id, _DAL],
            )
            asset = int(cur.fetchone()[0])
            self._rifiuto_del_periodo(
                "template_asset.update",
                lambda: svc.update_asset_metadati(
                    m.user, asset, {"valido_al": _AL_PRIMA.isoformat()},
                ),
            )
        self._nel_mondo(_prova)

    # 7. Catalogo: UoM operativa, componente di distinta, conversione UoM. La
    #    copia stava in `catalogo_service._validate_date_interval`, ritirata il
    #    2026-10-09 — ed era DIVERGENTE: pretendeva `valido_al > valido_dal`,
    #    quindi rifiutava il periodo di UN GIORNO SOLO che il DB ammette. Per
    #    questo, oltre al rifiuto, qui si prova anche che quel periodo passa.
    #    ⚠️ Le due UoM della conversione si costruiscono: il vincolo di non
    #    sovrapposizione per coppia non deve dipendere dalle conversioni che il
    #    database ha gia'.
    def test_catalogo_uom_operativa_componenti_conversioni(self):
        from apps.catalogo.services import catalogo_service as svc

        def _prova(cur, m):
            def _articolo(sigla: str, composito: bool = False) -> str:
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_articolo(%s, false, p_is_composito => %s)",
                    [f"BE-DATE-{sigla}-{uuid.uuid4().hex[:8]}", composito],
                )
                return str(cur.fetchone()[0])

            def _uom() -> int:
                cur.execute(
                    """
                    INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id)
                    SELECT 'BD' || substr(md5(random()::text), 1, 8), 'UoM date validita',
                           u.tipo_uom_id
                      FROM catalogo.unita_misura u ORDER BY u.id LIMIT 1
                    RETURNING id
                    """
                )
                return int(cur.fetchone()[0])

            giorno = {"valido_dal": _DAL.isoformat(), "valido_al": _DAL.isoformat()}

            # UoM operativa: la riga base che il DB semina alla nascita dell'articolo.
            # Il padre della distinta nasce composito: e' struttura (guard A-10).
            padre = _articolo("P", composito=True)
            cur.execute(
                "SELECT id FROM catalogo.articoli_uom_operativa WHERE articolo_id = %s",
                [padre],
            )
            uom_op = int(cur.fetchone()[0])
            svc.fn_update_uom_operativa(padre, uom_op, {"valido_dal": _DAL.isoformat()})
            self._rifiuto_del_periodo(
                "catalogo.uom_operativa.update",
                lambda: svc.fn_update_uom_operativa(
                    padre, uom_op, {"valido_al": _AL_PRIMA.isoformat()},
                ),
            )
            svc.fn_update_uom_operativa(padre, uom_op, {"valido_al": _DAL.isoformat()})

            # Componente di distinta: il padre e' nato composito.
            figlio = _articolo("F")
            base_comp = {"componente_id": figlio, "coeff_qta": "1"}
            self._rifiuto_del_periodo(
                "catalogo.componente.create",
                lambda: svc.fn_create_componente(padre, {
                    **base_comp, "valido_dal": _DAL.isoformat(),
                    "valido_al": _AL_PRIMA.isoformat(),
                }),
            )
            comp = svc.fn_create_componente(padre, {**base_comp, **giorno})
            self._rifiuto_del_periodo(
                "catalogo.componente.update",
                lambda: svc.fn_update_componente(
                    padre, comp["id"], {"valido_al": _AL_PRIMA.isoformat()},
                ),
            )

            # Conversione UoM.
            base_conv = {"uom_from_id": _uom(), "uom_to_id": _uom(), "fattore": "2"}
            self._rifiuto_del_periodo(
                "catalogo.conversione.create",
                lambda: svc.fn_create_conversione({
                    **base_conv, "valido_dal": _DAL.isoformat(),
                    "valido_al": _AL_PRIMA.isoformat(),
                }),
            )
            conv = svc.fn_create_conversione({**base_conv, **giorno})
            self._rifiuto_del_periodo(
                "catalogo.conversione.update",
                lambda: svc.fn_update_conversione(
                    int(conv["id"]), {"valido_al": _AL_PRIMA.isoformat()},
                ),
            )
        self._nel_mondo(_prova)
