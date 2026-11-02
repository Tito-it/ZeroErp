# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il codice errore di dominio dal campo strutturato dell'eccezione DB
#        (`CONSTRAINT` su SQLSTATE P0001) fino allo status HTTP della policy.
#        Risposta al brief `brief-db-codice-errore-strutturato.md` §6.
# ------------------------------------------------------------

"""Indice test previsti.

Unitari (senza DB — la forma dell'eccezione e' riprodotta fedelmente):
 1) test_campo_strutturato_vince_sul_testo
 2) test_campo_vuoto_ripiega_sul_testo          (codice da espressione NULL)
 3) test_campo_assente_ripiega_sul_testo        (RAISE diretto senza USING)
 4) test_sqlstate_non_p0001_ignora_il_campo     (violazione di vincolo vera)
 5) test_codice_legacy_senza_prefisso_arriva_e_ha_la_sua_policy
 6) test_nessun_codice_ripiega_su_e_database
 7) test_raise_from_database_error_usa_il_campo_se_dichiarato
 8) test_raise_from_database_error_codice_del_catalogo_vince_anche_non_dichiarato

End-to-end su DB reale (OPT-IN `ZEROERP_TEST_DB_E2E=1`, vedi la classe):
 9) test_e2e_helper_db_codice_e_status
10) test_e2e_codice_da_variabile_gruppo_c    (il caso che il testo non copriva)
11) test_e2e_il_codice_non_finisce_nel_messaggio
"""

from __future__ import annotations

from unittest import TestCase

from django.db import DatabaseError

from apps.core.services.db_error_fields import db_error_code, structured_db_error_code
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.core.tests.db_error_fakes import make_db_error


class DbErrorFieldsUnitTests(TestCase):
    """Lettura del codice: campo strutturato per primo, testo come ripiego."""

    # Scopo: Verifica il caso `test_campo_strutturato_vince_sul_testo`.
    def test_campo_strutturato_vince_sul_testo(self):
        # Nel testo c'e' un codice DIVERSO (e' il caso reale: la regex pescava
        # dallo statement chiamante). Deve vincere il campo.
        exc = make_db_error(
            "Messaggio.\nQUERY: SELECT script.fn_log_and_raise_error('a','b','E_DAL_TESTO',...)",
            sqlstate="P0001",
            codice="E_DAL_CAMPO",
        )
        self.assertEqual(structured_db_error_code(exc), "E_DAL_CAMPO")
        self.assertEqual(db_error_code(exc), "E_DAL_CAMPO")

    # Scopo: Verifica il caso `test_campo_vuoto_ripiega_sul_testo`.
    def test_campo_vuoto_ripiega_sul_testo(self):
        # Quando il codice viene da un'espressione che vale NULL il campo arriva
        # STRINGA VUOTA, non None: senza `or None` si propagherebbe un codice
        # vuoto invece di ripiegare.
        exc = make_db_error("Messaggio E_DAL_TESTO qui.", sqlstate="P0001", codice="")
        self.assertIsNone(structured_db_error_code(exc))
        self.assertEqual(db_error_code(exc), "E_DAL_TESTO")

    # Scopo: Verifica il caso `test_campo_assente_ripiega_sul_testo`.
    def test_campo_assente_ripiega_sul_testo(self):
        # I ~135 RAISE diretti che non passano dall'helper: il campo non c'e'.
        exc = make_db_error("Errore E_RAISE_DIRETTO.", sqlstate="P0001")
        self.assertIsNone(structured_db_error_code(exc))
        self.assertEqual(db_error_code(exc), "E_RAISE_DIRETTO")

    # Scopo: Verifica il caso `test_sqlstate_non_p0001_ignora_il_campo`.
    def test_sqlstate_non_p0001_ignora_il_campo(self):
        # Violazione UNIQUE vera: `constraint_name` e' il nome del vincolo DB.
        # Prenderlo per un codice applicativo scavalcherebbe map_integrity_error
        # e darebbe un 500 al posto di un 409 parlante.
        exc = make_db_error(
            'duplicate key value violates unique constraint "uq_soggetti_cf"',
            sqlstate="23505",
            codice="uq_soggetti_cf",
        )
        self.assertIsNone(structured_db_error_code(exc))
        self.assertIsNone(db_error_code(exc))

    # Scopo: Verifica il caso `test_codice_legacy_senza_prefisso_arriva_e_ha_la_sua_policy`.
    def test_codice_legacy_senza_prefisso_arriva_e_ha_la_sua_policy(self):
        # E' il punto del §7 del brief: questi codici la regex non li vedeva
        # (nessun prefisso E_), quindi si ripiegava su E_DATABASE -> 400. Ora
        # arrivano: senza una voce in error_policies finirebbero su E_GENERICO
        # -> 500. La registrazione e' un prerequisito di questa lettura.
        exc = make_db_error(
            "Transizione pratica non ammessa: CHIUSA -> APERTA",
            sqlstate="P0001",
            codice="PRATICHE_TRANSIZIONE_NON_AMMESSA",
        )
        api = ErrorTranslator.to_api_error(exc)
        self.assertEqual(api.code, "PRATICHE_TRANSIZIONE_NON_AMMESSA")
        self.assertEqual(ErrorTranslator.get_http_status(api), 409)
        self.assertNotEqual(ErrorTranslator.get_http_status(api), 500)

    # Scopo: Verifica il caso `test_nessun_codice_ripiega_su_e_database`.
    def test_nessun_codice_ripiega_su_e_database(self):
        exc = make_db_error("Errore generico senza codice.", sqlstate="P0001")
        api = ErrorTranslator.to_api_error(exc)
        self.assertEqual(api.code, "E_DATABASE")

    # Scopo: Verifica il caso `test_raise_from_database_error_usa_il_campo_se_dichiarato`.
    def test_raise_from_database_error_usa_il_campo_se_dichiarato(self):
        # Il testo NON contiene il marker: prima del campo strutturato questo
        # caso ricadeva sul fallback_code.
        exc = make_db_error(
            "Testo che non nomina il codice.",
            sqlstate="P0001",
            codice="E_UI_LISTA_NON_TROVATA",
        )
        with self.assertRaises(ServiceError) as ctx:
            ErrorManager.raise_from_database_error(
                exc,
                known_markers=(("E_UI_LISTA_NON_TROVATA", ("E_UI_LISTA_NON_TROVATA",)),),
                fallback_code="E_UI_GENERIC_FAILED",
                message="Errore risoluzione lista.",
                log_to_db=False,
            )
        self.assertEqual(ctx.exception.code, "E_UI_LISTA_NON_TROVATA")
        # La frase e' quella del DB, non il `message` del chiamante.
        self.assertEqual(ctx.exception.message, "Testo che non nomina il codice.")

    # Scopo: Verifica il caso `test_raise_from_database_error_codice_del_catalogo_vince_anche_non_dichiarato`.
    def test_raise_from_database_error_codice_del_catalogo_vince_anche_non_dichiarato(self):
        # ⭐ Decisione di Tid, 2026-09-23 (brief-db-guard-date-validita §13).
        # Fino ad allora un codice non in `known_markers` cadeva sul fallback:
        # un guard comune — le date di validita', su 25 tabelle — diventava il
        # codice generico del service che lo attraversava. Ora il codice del
        # catalogo vince sempre, con la sua frase.
        exc = make_db_error("Testo qualunque.", sqlstate="P0001", codice="E_ALTRO_DOMINIO")
        with self.assertRaises(ServiceError) as ctx:
            ErrorManager.raise_from_database_error(
                exc,
                known_markers=(("E_UI_LISTA_NON_TROVATA", ("E_UI_LISTA_NON_TROVATA",)),),
                fallback_code="E_UI_GENERIC_FAILED",
                message="Errore risoluzione lista.",
                log_to_db=False,
            )
        self.assertEqual(ctx.exception.code, "E_ALTRO_DOMINIO")
        self.assertEqual(ctx.exception.message, "Testo qualunque.")


class DbErrorFieldsEndToEndTests(TestCase):
    """Giro completo su DB reale: RAISE -> psycopg -> ApiError -> status.

    ⚠️ **Opt-in esplicito** (`ZEROERP_TEST_DB_E2E=1`), e il perche' vale la pena
    saperlo perche' e' un errore facile da rifare. La prima versione decideva se
    saltare con una `@skipUnless(_db_raggiungibile(), ...)`: l'argomento del
    decoratore si valuta **all'import**, quindi il probe apriva una connessione
    al DB di sviluppo durante la *discovery*, prima che il test runner
    predisponesse i database. Effetto: **469 test di altre app diventavano rossi**
    (middleware che rispondeva 500 al posto di 404/400), e la suite mirata delle
    stesse app senza questo file era verde. Un test che rompe i test degli altri
    e' peggio di un test che manca.

    Quindi: nessun contatto col DB a import time, controllo dentro
    `setUpClass`, e comunque **spento di default** — in CI i test Django girano
    senza DB reale (AGENTS.md). La verita' sul DB e' gia' asserita dai pgTAP
    lato DB (13/13); questi tre casi sono l'unico posto in cui si vede il pezzo
    che il pgTAP non puo' vedere — che i campi diag sopravvivano al giro
    libpq/psycopg fino a `django.db.DatabaseError`.

    ⚠️ **Perche' FUNZIONANO, che non e' il motivo che sembra.** Non c'e' nessuna
    fixture che provveda lo schema: la connessione e' quella **configurata**,
    cioe' il database di sviluppo con lo schema Liquibase completo. Django crea
    il database di test usa-e-getta **solo se almeno un test dichiara di averne
    bisogno** (`django.test.TestCase`, `TransactionTestCase`, o
    `databases = [...]`), e in `backend/apps` oggi **nessuno lo dichiara** — da
    cui la riga «Skipping setup of unused database(s)» nell'output. Il giorno in
    cui un test qualsiasi, in una app qualsiasi, dichiarera' un database, il
    runner ne creera' uno per tutta la suite: li' ci sono solo le migration
    Django, **non** Liquibase, quindi le funzioni PL/pgSQL non esistono. Il
    guard in `setUpClass` verifica lo **schema**, non la raggiungibilita', ed e'
    li' per quello: senza, questi tre fallirebbero addosso a chi ha scritto quel
    `TestCase`, in una PR che col codice errore strutturato non c'entra niente.
    Vedi `brief-be-e2e-db-error-fields-skip-schema.md` e la nota in AGENTS.md.
    Il guard vive in `apps/core/tests/db_e2e.py`: e' lo stesso prerequisito del
    cancello `test_error_codes_db_policy_guardrail`, e quando quella dipendenza
    implicita cadra' va sanato in un posto solo.

    ⚠️ **Non aggiungere qui test che SCRIVONO.** Per lo stesso motivo — la
    connessione e' quella vera — un test che scrive scrive sul database di
    sviluppo. I tre attuali no: provocano un errore dentro un
    `transaction.atomic()` che viene annullato, e non lasciano niente.

    Esecuzione:
        ZEROERP_TEST_DB_E2E=1 ./manage-test.sh \\
            apps.core.tests.services.test_db_error_fields -v 2

    In CI girano a ogni PR: `ci-validate.yaml` esporta `ZEROERP_TEST_DB_E2E=1`
    sullo step «Django tests», dove il database e' appena stato provvisto da
    Liquibase.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # Flag spenta, DB irraggiungibile, oppure schema Liquibase assente
        # (database usa-e-getta creato dal runner) -> skip. Il guard sta in
        # `apps/core/tests/db_e2e.py` perche' e' lo stesso prerequisito del
        # cancello `test_error_codes_db_policy_guardrail`, e il giorno in cui la
        # dipendenza implicita cadra' va sanato in un posto solo.
        richiedi_db_provvisto()

    # Scopo: Esegue SQL che solleva e restituisce l'eccezione catturata.
    def _solleva(self, sql: str) -> DatabaseError:
        from django.db import connection, transaction

        try:
            with transaction.atomic():
                with connection.cursor() as cur:
                    cur.execute(sql)
        except DatabaseError as exc:
            return exc
        raise AssertionError("l'SQL non ha sollevato")

    # Scopo: Verifica il caso `test_e2e_helper_db_codice_e_status`.
    def test_e2e_helper_db_codice_e_status(self):
        exc = self._solleva(
            """
            DO $$
            BEGIN
                PERFORM script.fn_log_and_raise_error(
                    'test'::text, 'test_db_error_fields'::text,
                    'E_ADMIN_USERNAME_DUPLICATO'::text, NULL::jsonb, NULL::uuid,
                    VARIADIC ARRAY[]::text[]);
            END $$;
            """
        )
        self.assertEqual(structured_db_error_code(exc), "E_ADMIN_USERNAME_DUPLICATO")
        api = ErrorTranslator.to_api_error(exc)
        self.assertEqual(api.code, "E_ADMIN_USERNAME_DUPLICATO")
        self.assertEqual(
            ErrorTranslator.get_http_status(api),
            ErrorPolicyRegistry.resolve("E_ADMIN_USERNAME_DUPLICATO").http_status,
        )

    # Scopo: Verifica il caso `test_e2e_codice_da_variabile_gruppo_c`.
    def test_e2e_codice_da_variabile_gruppo_c(self):
        # E' la forma delle 9 guard di cambio stato: il codice arriva da
        # un'espressione, quindi nel testo dell'eccezione c'e' il nome della
        # variabile. Prima del campo strutturato qui il codice si perdeva e si
        # ripiegava su E_DATABASE (tecnico: messaggio scartato, 400 generico).
        exc = self._solleva(
            """
            DO $$
            DECLARE v_code text := 'E_ADMIN_USERNAME_DUPLICATO';
            BEGIN
                PERFORM script.fn_log_and_raise_error(
                    'test'::text, 'test_db_error_fields'::text,
                    v_code, NULL::jsonb, NULL::uuid, VARIADIC ARRAY[]::text[]);
            END $$;
            """
        )
        self.assertIsNone(
            ErrorTranslator._extract_app_error_code(str(exc)),
            "il ripiego a regex non deve trovare nulla: e' il punto del test",
        )
        self.assertEqual(structured_db_error_code(exc), "E_ADMIN_USERNAME_DUPLICATO")
        self.assertEqual(ErrorTranslator.to_api_error(exc).code, "E_ADMIN_USERNAME_DUPLICATO")

    # Scopo: Verifica il caso `test_e2e_il_codice_non_finisce_nel_messaggio`.
    def test_e2e_il_codice_non_finisce_nel_messaggio(self):
        # Contratto negativo, gemello del pgTAP lato DB: il messaggio e' per
        # l'operatore, il codice viaggia nel campo. Se un giorno qualcuno lo
        # rimette nel testo "per farlo trovare piu' facilmente", questo diventa
        # rosso invece di lasciar morire la scelta in silenzio.
        exc = self._solleva(
            """
            DO $$
            BEGIN
                PERFORM script.fn_log_and_raise_error(
                    'test'::text, 'test_db_error_fields'::text,
                    'E_ADMIN_USERNAME_DUPLICATO'::text, NULL::jsonb, NULL::uuid,
                    VARIADIC ARRAY[]::text[]);
            END $$;
            """
        )
        diag = getattr(getattr(exc, "__cause__", None), "diag", None)
        self.assertIsNotNone(diag)
        self.assertNotIn("E_ADMIN_USERNAME_DUPLICATO", diag.message_primary or "")
