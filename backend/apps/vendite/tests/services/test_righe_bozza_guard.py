# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `richiedi_righe_in_bozza` (apps/vendite/services/
#        _righe_bozza_guard.py): il pre-check Python di «le righe si toccano
#        solo in bozza» parla col codice, la frase e il context del trigger
#        `vendite.trgfn_doc_righe_lock_fuori_bozza`.
# rev 2026-10-19 (brief-db-grammatica-unica-documenti lotto 2a): il documento
#        si passa col codice di `config.sorgenti`, che e' il `documento` del
#        context come nel trigger; la parola dell'etichetta e' una tabella.
# ------------------------------------------------------------
"""
Indice test:

RigheBozzaGuardTests (unit, senza DB)
 1) test_bozza_passa                       — DRAFT: nessun errore
 2) test_fuori_bozza_frase_con_numero      — codice E_RIGA_DOC_NON_BOZZA, frase
                                             a catalogo coi tre valori
 3) test_fuori_bozza_ripiego_su_id         — `numero` NULL -> «DDT #7»
 4) test_context_come_il_trigger           — documento = codice della sorgente, testata_id,
                                             stato, operazione = TG_OP (non il verbo)
 5) test_operazione_per_ogni_verbo         — i tre verbi -> INSERT/UPDATE/DELETE
 6) test_verbo_fuori_catalogo              — ValueError, non un 409 storto
 7) test_testata_senza_stato               — KeyError: lettore rotto, non un
                                             409 con «(stato )»
 7-bis) test_documento_fuori_catalogo      — codice corto o ignoto: ValueError
 7-ter) test_preventivo_porta_la_revisione — «Preventivo 2026/00012 rev. 1», come il DB
 7-quater) test_parole_coprono_i_documenti — PAROLA_ETICHETTA == DocumentoRighe

RigheBozzaGuardCatalogoE2ETests (OPT-IN `ZEROERP_TEST_DB_E2E=1`)
 8) test_frase_uguale_al_catalogo          — FRASE_CATALOGO == config.messaggi_errore
 9) test_documenti_nella_grammatica_del_db — ogni DocumentoRighe e' accettato
                                             da script.fn_get_stato_testata_documento

RigheBozzaGuardEtichettaE2ETests (OPT-IN `ZEROERP_TEST_DB_E2E=1`)
10) test_etichetta_uguale_a_quella_del_db — su una testata COSTRUITA per ogni
                                             DocumentoRighe, la frase del guard
                                             ha l'etichetta del DB
"""

from __future__ import annotations

# `unittest.TestCase` per la classe e2e, di proposito: `django.test.TestCase`
# dichiarerebbe un database e farebbe creare al runner un DB usa-e-getta per
# TUTTA la suite (AGENTS.md §Regole test Django); `SimpleTestCase` vieta il
# DB, che qui e' proprio cio' che serve.
import json
from typing import get_args
from unittest import TestCase

from django.test import SimpleTestCase

from apps.config.sorgenti import (
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
    SORGENTE_RESO_VENDITA,
)

from apps.core.services.error_manager import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.services._righe_bozza_guard import (
    CODICE,
    FRASE_CATALOGO,
    OPERAZIONE_PER_VERBO,
    PAROLA_ETICHETTA,
    DocumentoRighe,
    richiedi_righe_in_bozza,
)

_FN = "test.righe_bozza_guard"


class RigheBozzaGuardTests(SimpleTestCase):
    """Il guard, da solo: codice, frase, context."""

    # Scopo: Verifica il caso `test_bozza_passa`.
    def test_bozza_passa(self) -> None:
        richiedi_righe_in_bozza(
            {"stato_codice_interno": "DRAFT", "numero": None},
            documento=SORGENTE_DDT_VENDITA, documento_id=7, verbo="aggiungere", function_name=_FN,
        )

    # Scopo: Verifica il caso `test_fuori_bozza_frase_con_numero`.
    def test_fuori_bozza_frase_con_numero(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "EMESSO", "numero": "2026/00012"},
                documento=SORGENTE_DDT_VENDITA, documento_id=7, verbo="modificare", function_name=_FN,
            )
        self.assertEqual(cm.exception.code, CODICE)
        self.assertEqual(
            cm.exception.message,
            "DDT 2026/00012 non e' piu' in bozza (stato EMESSO): le sue righe si "
            "possono modificare solo finche' e' in bozza.",
        )
        self.assertEqual(cm.exception.detail, "stato=EMESSO")

    # Scopo: Verifica il caso `test_fuori_bozza_ripiego_su_id`.
    def test_fuori_bozza_ripiego_su_id(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "SPEDITO"},
                documento=SORGENTE_DDT_VENDITA, documento_id=7, verbo="togliere", function_name=_FN,
            )
        self.assertTrue(cm.exception.message.startswith("DDT #7 non e' piu' in bozza"))

    # Scopo: Verifica il caso `test_context_come_il_trigger`: le chiavi E i
    #        valori sono quelli che scrive `trgfn_doc_righe_lock_fuori_bozza`
    #        (`operazione` = TG_OP), cosi' il diario legge una lingua sola;
    #        niente `field`, su un conflitto di stato non c'e' un input.
    def test_context_come_il_trigger(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "CONFERMATO", "numero": "2026/00003"},
                documento=SORGENTE_ORDINE_VENDITA, documento_id=31, verbo="togliere", function_name=_FN,
            )
        self.assertEqual(
            cm.exception.context,
            {"documento": "ORDINE_VENDITA", "testata_id": 31, "stato": "CONFERMATO",
             "operazione": "DELETE"},
        )

    # Scopo: Verifica il caso `test_operazione_per_ogni_verbo`: la tabella
    #        e' quella del trigger letta al contrario, e copre i tre verbi.
    def test_operazione_per_ogni_verbo(self) -> None:
        self.assertEqual(
            OPERAZIONE_PER_VERBO,
            {"aggiungere": "INSERT", "modificare": "UPDATE", "togliere": "DELETE"},
        )
        for verbo, operazione in OPERAZIONE_PER_VERBO.items():
            with self.assertRaises(ServiceError) as cm:
                richiedi_righe_in_bozza(
                    {"stato_codice_interno": "EMESSO", "rev": 0},
                    documento=SORGENTE_PREVENTIVO, documento_id=1, verbo=verbo,  # type: ignore[arg-type]
                    function_name=_FN,
                )
            self.assertEqual(cm.exception.context["operazione"], operazione)
            self.assertIn(f" {verbo} ", cm.exception.message)

    # Scopo: Verifica il caso `test_verbo_fuori_catalogo`: e' un errore del
    #        chiamante e non deve diventare un 409 con un verbo inventato.
    def test_verbo_fuori_catalogo(self) -> None:
        with self.assertRaises(ValueError):
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "EMESSO"},
                documento=SORGENTE_DDT_VENDITA, documento_id=7, verbo="cancellare",  # type: ignore[arg-type]
                function_name=_FN,
            )

    # Scopo: Verifica il caso `test_testata_senza_stato`: una lettura che non
    #        porta lo stato e' un lettore rotto (500), non un documento fuori
    #        bozza con «(stato )» nella frase.
    def test_testata_senza_stato(self) -> None:
        with self.assertRaises(KeyError):
            richiedi_righe_in_bozza(
                {"numero": "2026/00012"},
                documento=SORGENTE_DDT_VENDITA, documento_id=7, verbo="aggiungere", function_name=_FN,
            )

    # Scopo: Verifica il caso `test_documento_fuori_catalogo`: un codice corto
    #        (la grammatica di prima del 2a) o ignoto e' un errore del
    #        chiamante, non un 409 con un'etichetta inventata.
    def test_documento_fuori_catalogo(self) -> None:
        for documento in ("DDT", "Ordine", "FATTURA"):
            with self.subTest(documento=documento), self.assertRaises(ValueError):
                richiedi_righe_in_bozza(
                    {"stato_codice_interno": "EMESSO"},
                    documento=documento,  # type: ignore[arg-type]
                    documento_id=7, verbo="aggiungere", function_name=_FN,
                )

    # Scopo: Verifica il caso `test_preventivo_porta_la_revisione`: le
    #        revisioni condividono il numero, e l'etichetta del DB porta la
    #        revisione per dire quale e' ferma. Senza `rev` e' un lettore rotto.
    def test_preventivo_porta_la_revisione(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "EMESSO", "numero": "2026/00012", "rev": 1},
                documento=SORGENTE_PREVENTIVO, documento_id=9, verbo="modificare",
                function_name=_FN,
            )
        self.assertTrue(
            cm.exception.message.startswith("Preventivo 2026/00012 rev. 1 non e' piu' in bozza"),
        )
        with self.assertRaises(KeyError):
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "EMESSO", "numero": "2026/00012"},
                documento=SORGENTE_PREVENTIVO, documento_id=9, verbo="modificare",
                function_name=_FN,
            )

    # Scopo: Verifica il caso `test_parole_coprono_i_documenti`: il `Literal`
    #        e la tabella delle parole sono due elenchi degli stessi codici;
    #        se divergono, un documento ammesso dal tipo solleverebbe qui.
    def test_parole_coprono_i_documenti(self) -> None:
        self.assertEqual(set(PAROLA_ETICHETTA), set(get_args(DocumentoRighe)))


class RigheBozzaGuardCatalogoE2ETests(TestCase):
    """La copia della frase e' voluta (niente round-trip a DB per un 409), e
    una copia senza presidio diverge in silenzio: qui si confronta col
    catalogo vivo. Opt-in `ZEROERP_TEST_DB_E2E=1` (in CI e' acceso), stesso
    prerequisito di `test_db_error_fields`."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: Verifica il caso `test_frase_uguale_al_catalogo`.
    def test_frase_uguale_al_catalogo(self) -> None:
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                "SELECT messaggio FROM config.messaggi_errore "
                "WHERE codice = %s AND lingua = 'it'",
                [CODICE],
            )
            row = cur.fetchone()
        self.assertIsNotNone(row, f"{CODICE} non e' a catalogo in lingua it")
        assert row is not None
        self.assertEqual(row[0], FRASE_CATALOGO)

    # Scopo: Verifica il caso `test_documenti_nella_grammatica_del_db`: ogni
    #        codice che il guard accetta e' un `p_documento` che il lettore
    #        delle testate (lo stesso del trigger) conosce. Un id inesistente
    #        da' zero righe; un codice ignoto solleverebbe.
    def test_documenti_nella_grammatica_del_db(self) -> None:
        from django.db import connection, transaction

        for documento in get_args(DocumentoRighe):
            with self.subTest(documento=documento), transaction.atomic():
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT count(*) FROM script.fn_get_stato_testata_documento(%s, %s)",
                        [documento, 999_999_999],
                    )
                    row = cur.fetchone()
                assert row is not None
                self.assertEqual(row[0], 0)
                transaction.set_rollback(True)


class RigheBozzaGuardEtichettaE2ETests(TestCase):
    """L'etichetta e' una COPIA dichiarata di quella del DB: la parola di
    `PAROLA_ETICHETTA`, il ripiego `#id`, la revisione del preventivo. Il
    confronto con la frase a catalogo non la vede (l'etichetta e' un `%s`), e
    `test_documenti_nella_grammatica_del_db` prova solo che il codice e'
    accettato. Qui si confronta, riga per riga, la frase del guard con
    l'`etichetta` di `script.fn_get_stato_testata_documento` sulla STESSA
    testata. ⚠️ Le testate si COSTRUISCONO (stampi `dbops.fn_pgtap_crea_*`,
    service del DDT, INSERT come nei pgTAP per il contratto, il reso sulla
    bolla consegnata di `_ddt_consegnato`): un test che
    leggesse le righe esistenti passerebbe a vuoto sul DB della CI.
    Transazione sempre annullata; opt-in `ZEROERP_TEST_DB_E2E=1`."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    def setUp(self) -> None:
        from django.db import connection

        from apps.core.db._helpers import row_to_dict
        from apps.core.tests.db_e2e import apri_transazione_annullata

        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('etichetta guard righe')")
            mondo = row_to_dict(cur)
        assert mondo is not None
        self.mondo = mondo

    def _scalare(self, sql: str, params: list | None = None):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(sql, params or [])
            row = cur.fetchone()
        assert row is not None, sql
        return row[0]

    def _crea_ddt(self) -> int:
        from apps.vendite.services import ddt_service

        return int(ddt_service.crea_ddt({
            "billing_account_id": self.mondo["billing_account_id"],
            "emittente_fiscale_id": self.mondo["emittente_fiscale_id"],
        })["id"])

    def _crea_contratto(self) -> int:
        return int(self._scalare(
            """
            INSERT INTO vendite.contratti (
                numero, billing_account_id, istanza_utility_id, utility_id,
                emittente_fiscale_id, stato_doc_contratto_id)
            SELECT 'E2E_ETICHETTA', %s, %s, %s, %s, s.id
              FROM config.stati_doc_contratti s WHERE s.codice_interno = 'DRAFT'
            RETURNING id
            """,
            [self.mondo["billing_account_id"], self.mondo["istanza_utility_id"],
             self.mondo["utility_id"], self.mondo["emittente_fiscale_id"]],
        ))

    # Il reso nasce solo da un DDT CONSEGNATO: la bolla dallo stampo condiviso.
    def _crea_reso(self) -> int:
        from django.db import connection

        from apps.vendite.tests.db._ddt_consegnato import crea_ddt_consegnato

        with connection.cursor() as cur:
            ddt = crea_ddt_consegnato(cur, etichetta="etichetta guard righe reso")
        self.assertEqual(ddt["stato"], "CONSEGNATO")
        # Dal percorso di produzione: la provenienza la sceglie il BB del DB
        # (`script.fn_sorgente_provenienza`), non un INSERT a mano con l'uid
        # della bolla, che il guard unico rifiuta dal giro T.2.
        from apps.vendite.db.resi_repository import ResiRepository

        return int(ResiRepository().create_reso(ddt_id=int(ddt["id"]))["id"])

    # Per documento: come nasce la testata, e la tabella da cui il lettore del
    # backend prende `numero` (e `rev`, che c'e' solo sul preventivo).
    def _stampi(self) -> dict[str, tuple[object, str]]:
        return {
            SORGENTE_DDT_VENDITA: (self._crea_ddt, "vendite.ddt"),
            SORGENTE_ORDINE_VENDITA: (
                lambda: self._scalare("SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine('etichetta')"),
                "vendite.ordini",
            ),
            SORGENTE_PREVENTIVO: (
                lambda: self._scalare(
                    "SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo('etichetta')",
                ),
                "vendite.preventivi",
            ),
            SORGENTE_CONTRATTO: (self._crea_contratto, "vendite.contratti"),
            SORGENTE_RESO_VENDITA: (self._crea_reso, "vendite.resi"),
        }

    # Scopo: Verifica il caso `test_etichetta_uguale_a_quella_del_db`.
    def test_etichetta_uguale_a_quella_del_db(self) -> None:
        from django.db import connection

        stampi = self._stampi()
        # Un documento nuovo nel `Literal` senza stampo qui e' rosso, non saltato.
        self.assertEqual(set(stampi), set(get_args(DocumentoRighe)))
        for documento, (crea, tabella) in stampi.items():
            with self.subTest(documento=documento):
                testata_id = int(crea())  # type: ignore[operator]
                with connection.cursor() as cur:
                    cur.execute(
                        f"SELECT to_jsonb(t) FROM {tabella} t WHERE t.id = %s", [testata_id],
                    )
                    riga = cur.fetchone()
                    cur.execute(
                        "SELECT etichetta FROM script.fn_get_stato_testata_documento(%s, %s)",
                        [documento, testata_id],
                    )
                    dal_db = cur.fetchone()
                assert riga is not None and dal_db is not None
                testata = riga[0] if isinstance(riga[0], dict) else json.loads(riga[0])
                # Lo stato e' fittizio: serve solo ad aprire il ramo del rifiuto.
                testata["stato_codice_interno"] = "EMESSO"
                with self.assertRaises(ServiceError) as cm:
                    richiedi_righe_in_bozza(
                        testata, documento=documento, documento_id=testata_id,  # type: ignore[arg-type]
                        verbo="modificare", function_name=_FN,
                    )
                self.assertEqual(
                    cm.exception.message, FRASE_CATALOGO % (dal_db[0], "EMESSO", "modificare"),
                )
