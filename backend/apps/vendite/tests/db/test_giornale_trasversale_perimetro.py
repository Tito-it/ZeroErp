# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: R-4 del piano BE/FE dell'osservabilita' — IL PERIMETRO DEL GIORNALE
#        TRASVERSALE SI PROVA, NON SI DEDUCE. Sul DB provvisto si COSTRUISCONO
#        due aziende con i builder pgTAP (`dbops.fn_pgtap_crea_emittente_
#        operatore`), un lotto e una riga di diario ERROR per ciascuna, e si
#        legge col contesto del solo primo operatore: la seconda NON compare, e
#        il conteggio dice il numero VISTO, non il totale. E' il presidio che il
#        Passo A non ha mai avuto: la vista e' `security_invoker` e senza questo
#        test il perimetro sarebbe verificato solo dal pgTAP, non dall'uso.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI), e la
#    connessione dell'APPLICAZIONE (`zeroerp_app`, non owner e NOBYPASSRLS):
#    `richiedi_ruolo_soggetto_a_rls` lo pretende, o il test non proverebbe
#    che qualcosa resti nascosto. NON LASCIA NIENTE: tutto in transazione
#    annullata.
#
# Indice test:
#   1. test_il_giornale_mostra_solo_l_emittente_di_chi_legge
#   2. test_il_filtro_per_filo_trova_la_riga_costruita
#   3. test_ogni_filtro_della_whitelist_si_attraversa (+ i quattro indici per
#      tempo di P-3 esistono; il PIANO non si asserisce: e' del planner)
#   4. test_i_registri_del_filtro_vengono_dal_catalogo: il vocabolario di
#      `registro` e' `config.registri_giornale` letto dal DB, ogni registro
#      del catalogo attraversa il service, uno ignoto e' un rifiuto
# ------------------------------------------------------------
from __future__ import annotations

from unittest import TestCase
from uuid import uuid4

from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto, richiedi_ruolo_soggetto_a_rls
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.vendite.services.vendite_service import get_giornale_trasversale


class _Mondo:
    """Un'azienda costruita: emittente, operatore, un lotto e una riga ERROR."""

    def __init__(self, cur, sigla: str) -> None:
        cur.execute("SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore(%s)", [sigla])
        riga = cur.fetchone()
        assert riga is not None
        self.ef_id, self.ef_codice, self.sr_id, self.auth_user_id, self.identita_id = riga
        self.lotto_id: int | None = None
        self.correlation_id = str(uuid4())

    # Scopo: il lotto e la riga di diario, scritti COL CONTESTO del proprio
    #        operatore (le tabelle hanno la RLS anche in scrittura).
    def scrivi(self, cur) -> None:
        cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [self.auth_user_id])
        cur.execute(
            """
            INSERT INTO vendite.fatturazione_lotti
                (codice, tipo_doc_fiscale_id, competenza_mese,
                 emittente_soggetto_ruolo_id, stato_doc_fiscale_id, meta)
            VALUES ('E2E-GIORNALE-' || %s,
                    (SELECT id FROM config.tipi_doc_fiscale WHERE codice_interno = 'BACKOFFICE'),
                    date_trunc('month', script.fn_data_operativa())::date, %s,
                    (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'),
                    '{"test_scope": "e2e_giornale_trasversale"}'::jsonb)
            RETURNING id
            """,
            [self.sr_id, self.sr_id],
        )
        riga = cur.fetchone()
        assert riga is not None
        self.lotto_id = int(riga[0])
        # ⭐ La riga del diario: l'emittente la DERIVA il trigger dal lotto.
        cur.execute(
            """
            INSERT INTO vendite.event_log (entity_type, entity_id, event_code, severity, correlation_id, payload)
            VALUES ('LOTTO', %s, 'E2E_GIORNALE_PROVA', 'ERROR', %s::uuid, '{}'::jsonb)
            """,
            [self.lotto_id, self.correlation_id],
        )


class GiornaleTrasversalePerimetroTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        richiedi_ruolo_soggetto_a_rls("vendite.event_log")

    # Scopo: due mondi, scritti ciascuno dal proprio operatore.
    def _due_mondi(self, cur) -> tuple[_Mondo, _Mondo]:
        # ⛔ I builder vogliono la finestra DIFFERITA (la saga dell'utente
        #    tecnico); le scritture di dominio dopo vogliono IMMEDIATE, come nel
        #    pgTAP che questo test ricalca.
        cur.execute("SET CONSTRAINTS ALL DEFERRED")
        a, b = _Mondo(cur, "GA"), _Mondo(cur, "GB")
        cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
        a.scrivi(cur)
        b.scrivi(cur)
        return a, b

    # 1. Col contesto del primo operatore la riga del secondo NON c'e', e il
    #    totale e' quello visto.
    def test_il_giornale_mostra_solo_l_emittente_di_chi_legge(self) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                a, b = self._due_mondi(cur)
                cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [a.auth_user_id])
            # Il giorno della riga appena scritta e' quello dell'AZIENDA: il
            # filtro lo calcola cosi' (BB), e cosi' lo chiede il test.
            oggi = oggi_aziendale()
            data = get_giornale_trasversale(
                gravita=["ERROR"], registri=["EVENT_LOG"], entity_type="LOTTO",
                data_da=oggi, data_a=oggi, limit=200, offset=0,
            )
            transaction.set_rollback(True)
        visti = {(r["entity_type"], r["entity_id"]) for r in data["results"]}
        self.assertIn(("LOTTO", a.lotto_id), visti, "la riga del PROPRIO emittente deve esserci")
        self.assertNotIn(("LOTTO", b.lotto_id), visti, "la riga dell'ALTRO emittente non deve esserci")
        # Il conteggio e' quello VISTO: l'operatore A e' nato oggi con un solo
        # lotto, quindi fra le righe ERROR di oggi su LOTTO ne vede una.
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        # E il display arriva dal backend, dalla tabella in RLS del suo lotto.
        self.assertEqual(data["results"][0]["entita_display"], f"E2E-GIORNALE-{a.sr_id}")

    # 2. Il filo trova la riga costruita, e solo quella.
    def test_il_filtro_per_filo_trova_la_riga_costruita(self) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                a, _b = self._due_mondi(cur)
                cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [a.auth_user_id])
            data = get_giornale_trasversale(gravita=["ERROR", "WARN", "INFO"], filo=a.correlation_id, limit=50)
            transaction.set_rollback(True)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["correlation_id"], a.correlation_id)

    # 3. Ogni filtro dichiarato si attraversa senza errore SQL (il contratto si
    #    prova per intero), e i QUATTRO indici per tempo di P-3 esistono.
    # ⛔ Non si asserisce sul PIANO: e' una scelta del planner sulla popolazione
    #    (sul DB di sviluppo i registri hanno poche centinaia di righe e il
    #    seq scan e' la risposta giusta), e un test che pretendesse l'indice
    #    sarebbe rosso sul DB piccolo e verde su quello grande — cioe' il
    #    contrario di un presidio. Il piano si guarda con EXPLAIN e si scrive
    #    nel registro del piano, come fatto datato.
    def test_ogni_filtro_della_whitelist_si_attraversa(self) -> None:
        repo = VenditeRepository()
        oggi = oggi_aziendale()
        with transaction.atomic():
            with connection.cursor() as cur:
                a, _b = self._due_mondi(cur)
                cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [a.auth_user_id])
            for filtro in (
                {"gravita": ["ERROR"]},
                {"gravita": ["WARN", "INFO"], "registri": ["LOTTO_LOG", "FATTURA_LOG"]},
                {"gravita": ["ERROR"], "entity_type": "FATTURA"},
                {"gravita": ["ERROR"], "data_da": oggi, "data_a": oggi},
                {"gravita": ["ERROR"], "filo": a.correlation_id},
                {"gravita": ["ERROR"], "solo_vive": False, "sort_by": "gravita", "sort_dir": "asc"},
                # Un `entity_type` che il catalogo non conosce: zero righe, non un 500.
                {"gravita": ["ERROR"], "entity_type": "NON_ESISTE"},
            ):
                righe, vive, ritirate, info_vive = repo.list_giornale_trasversale(limit=5, **filtro)
                self.assertIsInstance(vive, int)
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT indexname FROM pg_indexes
                     WHERE schemaname = 'vendite'
                       AND indexname IN ('ix_event_log_event_time', 'ix_fatture_log_data_ora',
                                         'ix_fatturazione_lotti_log_data_ora',
                                         'ix_fatturazione_lotti_task_runs_started_at')
                    """
                )
                indici = {r[0] for r in cur.fetchall()}
            transaction.set_rollback(True)
        self.assertEqual(len(indici), 4, f"indici per tempo di P-3 (20260919-05) mancanti: {indici}")

    # 4. Il vocabolario del filtro `registro` e' il CATALOGO, letto dal DB
    #    (brief-db-registri-giornale-catalogo, 2026-09-19): il lettore risponde
    #    esattamente i `codice_interno` di `config.registri_giornale`, ogni
    #    registro del catalogo attraversa il service senza errore SQL, e un
    #    registro che il catalogo non conosce e' un rifiuto (400), non
    #    «zero righe». ⚠️ Non si pretende un elenco preciso: il giorno del
    #    quinto registro questo test deve restare verde da solo — e' la
    #    ragione per cui la costante e' uscita dal backend.
    def test_i_registri_del_filtro_vengono_dal_catalogo(self) -> None:
        repo = VenditeRepository()
        with transaction.atomic():
            with connection.cursor() as cur:
                a, _b = self._due_mondi(cur)
                cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [a.auth_user_id])
                cur.execute("SELECT codice_interno FROM config.registri_giornale")
                catalogo = {r[0] for r in cur.fetchall()}
            ammessi = repo.registri_giornale_ammessi()
            self.assertTrue(ammessi, "config.registri_giornale vuota: il seed 20260919-09 manca")
            self.assertEqual(ammessi, frozenset(catalogo))
            for registro in sorted(ammessi):
                data = get_giornale_trasversale(gravita=["ERROR", "WARN", "INFO"], registri=[registro], limit=1)
                self.assertIsInstance(data["count"], int)
            with self.assertRaises(ServiceError) as ctx:
                get_giornale_trasversale(registri=["NON_A_CATALOGO"], limit=1)
            transaction.set_rollback(True)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        # Filtro di query: il parametro nominato nel context, mai `field`.
        self.assertEqual(ctx.exception.context.get("parametro"), "registro")
        self.assertNotIn("field", ctx.exception.context)
