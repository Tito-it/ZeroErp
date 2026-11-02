# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La conferma del regime fiscale dell'emittente (R-1/R-2 di
#        brief-db-esigibilita-iva-per-cassa-emittente), provata sul DATABASE
#        VERO: cio' che i test di servizio, che mockano il repository, non
#        possono vedere. Dal §10 (applicato il 2026-10-02) la conferma la
#        DERIVA il trigger `trgfn_emittenti_fiscali_regime_conferma` da ogni
#        UPDATE che nomina il regime: si prova che il repository la ottenga
#        solo nominandolo, che l'autore sia l'operatore della GUC
#        `app.jwt_user`, che la creazione col regime nasca confermata (INSERT
#        + UPDATE), che chi scrive le colonne di conferma sia rifiutato dal
#        guard, e che la FK al catalogo arrivi al client come 400 sul campo.
# Note: ⚠️ Il mondo si COSTRUISCE (builder `dbops.fn_pgtap_crea_*`), in
#       transazione ANNULLATA. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
#       ⚠️ I regimi usati (RF01, RF17) sono SEED di `config.regimi_fiscali`
#       (`80_data`): contratto, non popolazione.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RegimeFiscaleConfermaDbTests.test_update_col_regime_scrive_la_conferma
2) RegimeFiscaleConfermaDbTests.test_update_senza_regime_non_tocca_la_conferma
3) RegimeFiscaleConfermaDbTests.test_update_regime_invariato_conferma_lo_stesso
4) RegimeFiscaleConfermaDbTests.test_create_col_regime_nasce_confermato
5) RegimeFiscaleConfermaDbTests.test_create_senza_regime_nasce_rf01_non_confermato
6) RegimeFiscaleConfermaDbTests.test_regime_fuori_catalogo_400_sul_campo
7) RegimeFiscaleConfermaDbTests.test_create_regime_fuori_catalogo_400_sul_campo
8) RegimeFiscaleConfermaDbTests.test_scrittura_diretta_della_conferma_rifiutata
9) RegimeFiscaleConfermaDbTests.test_insert_col_regime_non_conferma
"""
from __future__ import annotations

import unittest
import uuid

from django.db import DatabaseError, connection, transaction

from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)

_OPERATORE = "test-regime-conferma@e2e"


class RegimeFiscaleConfermaDbTests(unittest.TestCase):

    def setUp(self):
        apri_transazione_annullata(self)
        richiedi_db_provvisto()
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute("SET LOCAL app.jwt_user = %s", [_OPERATORE])

    # Scopo: un emittente nuovo dal builder: nasce RF01 (default), non confermato.
    def _emittente(self) -> int:
        with connection.cursor() as cur:
            cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
            return int(cur.fetchone()[0])

    def _stato(self, emittente_id: int) -> tuple:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT regime_fiscale_rf, regime_fiscale_confermato_il IS NOT NULL,"
                "       regime_fiscale_confermato_da"
                "  FROM anagrafiche.emittenti_fiscali WHERE id = %s",
                [emittente_id],
            )
            return cur.fetchone()

    def _repo(self):
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository()

    # 1. Una UPDATE che nomina il regime: data e autore li scrive il trigger,
    #    e l'autore e' l'operatore.
    def test_update_col_regime_scrive_la_conferma(self):
        emittente_id = self._emittente()
        self.assertEqual(("RF01", False, None), self._stato(emittente_id))

        self.assertTrue(self._repo().update_emittente(
            emittente_id, {"regime_fiscale_rf": "RF17"},
        ))
        self.assertEqual(("RF17", True, _OPERATORE), self._stato(emittente_id))

    # 2. Una PATCH che non porta il regime non conferma e non azzera niente.
    def test_update_senza_regime_non_tocca_la_conferma(self):
        emittente_id = self._emittente()
        repo = self._repo()
        repo.update_emittente(emittente_id, {"regime_fiscale_rf": "RF17"})

        self.assertTrue(repo.update_emittente(emittente_id, {"bollo_auto": True}))
        self.assertEqual(("RF17", True, _OPERATORE), self._stato(emittente_id))

    # 3. Il regime riscritto uguale e' la conferma di un regime che nessuno
    #    aveva dichiarato: e' il percorso con cui l'operatore svuota il presidio.
    def test_update_regime_invariato_conferma_lo_stesso(self):
        emittente_id = self._emittente()
        self._repo().update_emittente(emittente_id, {"regime_fiscale_rf": "RF01"})
        self.assertEqual(("RF01", True, _OPERATORE), self._stato(emittente_id))
        with connection.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM dbops.vw_emittenti_regime_non_confermato"
                " WHERE emittente_fiscale_id = %s",
                [emittente_id],
            )
            self.assertEqual(0, cur.fetchone()[0])

    # P.IVA libera dal builder (`fn_pgtap_piva_libera`): una fissa collide col
    # residuo di un'altra corsa o coi dati.
    def _soggetto_pg(self, nome: str) -> str:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg(%s)", [nome])
            return str(cur.fetchone()[0])

    def _soggetto_ruolo_ef(self) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_soggetto_ruolo("
                "  dbops.fn_pgtap_crea_soggetto_pg('Emittente e2e regime'), 'EF')"
            )
            return int(cur.fetchone()[0])

    # Sigla libera nella forma di `chk_emittenti_fiscali_codice_forma`.
    @staticmethod
    def _codice() -> str:
        return "RC" + uuid.uuid4().hex[:8].upper()

    # 4. Creare dichiarando il regime = nascere confermati. Passa dal SERVICE,
    #    che chiama la madre `fn_crea_emittente_fiscale` (dal 2026-10-18 e' lei
    #    a far seguire alla INSERT la UPDATE del regime).
    def test_create_col_regime_nasce_confermato(self):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )

        risultato = EmittentiFiscaliService().crea_emittente({
            "soggetto_id": self._soggetto_pg("Emittente e2e regime"),
            "codice": self._codice(), "regime_fiscale_rf": "RF17",
        })
        self.assertEqual(("RF17", True, _OPERATORE), self._stato(risultato["id"]))

    # 5. Senza regime vale il default del DB, e nessuno l'ha confermato.
    def test_create_senza_regime_nasce_rf01_non_confermato(self):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )

        risultato = EmittentiFiscaliService().crea_emittente({
            "soggetto_id": self._soggetto_pg("Emittente e2e senza regime"),
            "codice": self._codice(),
        })
        self.assertEqual(("RF01", False, None), self._stato(risultato["id"]))

    # 6. Un codice fuori catalogo e' la FK: il service lo da' come 400 sul
    #    campo, non come 500. Savepoint: la FK abortisce la sola sotto-transazione.
    def test_regime_fuori_catalogo_400_sul_campo(self):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )
        from apps.core.services.service_errors import ServiceError

        emittente_id = self._emittente()
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            EmittentiFiscaliService().update_emittente(
                emittente_id, {"regime_fiscale_rf": "RF99"},
            )
        self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)
        self.assertEqual("regime_fiscale_rf", ctx.exception.context.get("field"))

    # 7. Lo stesso in creazione, dove la FK attraversa `create_with_constraint_
    #    mapping`: deve RILANCIARLA (nessuna UNIQUE in causa) e non mascherarla
    #    da duplicato, e la traduzione esterna deve darla come 400 sul campo.
    def test_create_regime_fuori_catalogo_400_sul_campo(self):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )
        from apps.core.services.service_errors import ServiceError

        soggetto_id = self._soggetto_pg("Emittente e2e regime FK")
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            EmittentiFiscaliService().crea_emittente({
                "soggetto_id": soggetto_id, "codice": self._codice(),
                "regime_fiscale_rf": "RF99",
            })
        self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)
        self.assertEqual("regime_fiscale_rf", ctx.exception.context.get("field"))

    # 8. ⛔ Le colonne di conferma non si scrivono da fuori: il guard
    #    `trgfn_emittenti_fiscali_guard_regime_conferma` rifiuta, non
    #    sovrascrive. Il repository non puo' nemmeno provarci (whitelist del
    #    BB): si scrive in SQL, come farebbe un altro scrittore.
    def test_scrittura_diretta_della_conferma_rifiutata(self):
        emittente_id = self._emittente()
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic(), \
                connection.cursor() as cur:
            cur.execute(
                "UPDATE anagrafiche.emittenti_fiscali"
                "   SET regime_fiscale_confermato_il = now(),"
                "       regime_fiscale_confermato_da = 'qualcuno'"
                " WHERE id = %s",
                [emittente_id],
            )
        self.assertIn("E_EMITTENTE_REGIME_CONFERMA_DERIVATA", str(ctx.exception))
        self.assertEqual(("RF01", False, None), self._stato(emittente_id))

    # 9. La INSERT non conferma mai, nemmeno con un regime esplicito: un RF01
    #    scelto e uno di default sono indistinguibili. La conferma in
    #    creazione e' solo quella della UPDATE che la madre fa seguire (4).
    #    Il backend non ha piu' una INSERT sua (2026-10-18): si scrive in SQL,
    #    come farebbe un altro scrittore.
    def test_insert_col_regime_non_conferma(self):
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO anagrafiche.emittenti_fiscali"
                "  (soggetto_ruolo_id, codice, regime_fiscale_rf)"
                " VALUES (%s, %s, 'RF17') RETURNING id",
                [self._soggetto_ruolo_ef(), self._codice()],
            )
            emittente_id = int(cur.fetchone()[0])
        self.assertEqual(("RF17", False, None), self._stato(emittente_id))
