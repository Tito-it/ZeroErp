# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli override di `config.parameter_overrides` scritti e cancellati dal
#        backend: uno per ambito, un upsert ripetuto aggiorna la stessa riga,
#        la delete non tocca l'override di un altro, e un parametro inesistente
#        non arriva all'INSERT. Sul DATABASE PROVVISTO, in una transazione
#        sempre annullata.
# Note: ⭐ Il caso che conta si COSTRUISCE: una riga MISTA (utente +
#        categoria), un secondo utente, una riga SPENTA (`attivo` false o
#        NULL, che il modello ammette). Dal 2026-10-07 le righe miste non
#        nascono (`chk_parameter_overrides_un_ambito`, decisione di Tid) e
#        l'unicita' d'ambito e' vera (`uq_overrides_full_scope_v5`, NULLS NOT
#        DISTINCT): l'upsert ci si appoggia con `ON CONFLICT`. Prima il
#        perimetro «puro» lo teneva il repository (F-5, 2026-09-28), e due
#        upsert concorrenti potevano creare un doppione. Un codice inesistente
#        era un `E_DATABASE` (E-9). La SQL e' la stessa per ogni livello: la
#        prova per livello e' `test_parameter_repository_dimensioni`.
#        ⭐ Anche il PARAMETRO si costruisce, con la sua famiglia (BB di test
#        `crea_parametro_di_prova`, brief-db-parametri-senza-override BE-3).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ParameterOverridesDbTests.test_parametro_inesistente_non_scrive_niente (E-9)
2) ParameterOverridesDbTests.test_riga_mista_non_nasce
3) ParameterOverridesDbTests.test_upsert_ripetuto_aggiorna_la_stessa_riga
4) ParameterOverridesDbTests.test_delete_non_tocca_l_override_di_un_altro
5) ParameterOverridesDbTests.test_upsert_riattiva_la_riga_spenta
6) ParameterOverridesDbTests.test_lettura_facoltativa_di_un_codice_non_dichiarato
7) ParameterOverridesDbTests.test_parametro_per_tutti_non_si_personalizza
8) ParameterOverridesDbTests.test_valore_fuori_forma_non_si_salva
"""

from __future__ import annotations

import unittest

from django.contrib.auth.models import User
from django.db import DatabaseError, IntegrityError, connection, transaction

from apps.core.db.parameter_repository import ParameterRepository
from apps.core.services.db_error_fields import db_error_code, diagnostica_db
from apps.core.tests._helpers.parametro_di_prova import crea_parametro_di_prova
from apps.core.tests.db_e2e import richiedi_db_provvisto

_CODICE_INESISTENTE = "ZZ_PARAMETRO_CHE_NON_ESISTE_TEST"
_CODICE_DI_PROVA = "ZZ_TEST_PARAMETRI_PURI"
_SQLSTATE_CHECK = "23514"


class ParameterOverridesDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: esegue `azione(cur, param_id, codice, uid)` in una transazione
    # SEMPRE annullata, con un parametro e un utente creati qui. Il parametro
    # dichiara la sua famiglia: `ammette_override` (default: si personalizza).
    def _nel_mondo(self, azione, *, ammette_override: bool = True, **parametro) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    param_id, codice = crea_parametro_di_prova(
                        cur, codice=_CODICE_DI_PROVA, ammette_override=ammette_override,
                        **parametro,
                    )
                    uid = User.objects.create(username="zz_test_parametri_puri").id
                    azione(cur, param_id, codice, uid)
            finally:
                transaction.set_rollback(True)

    # Scopo: ⭐ E-9 — codice inesistente: il repository torna None e non
    # scrive niente (prima: INSERT con `parameter_id` NULL → violazione).
    def test_parametro_inesistente_non_scrive_niente(self):
        def azione(cur, _param_id, _code, uid):
            esito = ParameterRepository().upsert_user_override(_CODICE_INESISTENTE, uid, "v")
            self.assertIsNone(esito)
            cur.execute(
                "SELECT count(*) FROM config.parameter_overrides WHERE django_user_id = %s",
                [uid],
            )
            self.assertEqual(cur.fetchone()[0], 0)
        self._nel_mondo(azione)

    # Scopo: ⭐ La premessa su cui il repository si appoggia: un override vale
    # per UN ambito. Una riga utente + categoria la rifiuta il DB (`23514`),
    # quindi la delete per id + scope non ha bisogno di filtrare le altre
    # dimensioni. Fino al 2026-10-07 la riga nasceva, e i test 2-3 di allora
    # provavano che upsert e delete non la toccassero (F-5).
    def test_riga_mista_non_nasce(self):
        def azione(cur, param_id, _code, uid):
            cur.execute(
                "INSERT INTO anagrafiche.categorie_clienti (codice, descrizione, codice_interno) "
                "VALUES ('ZZ_TEST_PAR', 'Categoria di test', 'ZZ_TEST_PAR') RETURNING id"
            )
            categoria_id = cur.fetchone()[0]
            with self.assertRaises(IntegrityError) as ctx, transaction.atomic():
                cur.execute(
                    "INSERT INTO config.parameter_overrides "
                    "(parameter_id, django_user_id, categoria_cliente_id, overridden_value) "
                    "VALUES (%s, %s, %s, 'misto')",
                    [param_id, uid, categoria_id],
                )
            self.assertEqual(getattr(ctx.exception.__cause__, "sqlstate", None), _SQLSTATE_CHECK)
        self._nel_mondo(azione)

    # Scopo: ⭐ Un upsert ripetuto sullo stesso ambito aggiorna la riga che
    # c'e': stesso id, valore nuovo, una riga sola. E' il vincolo d'ambito a
    # trovarla (`ON CONFLICT`), non un match scritto nel repository.
    def test_upsert_ripetuto_aggiorna_la_stessa_riga(self):
        def azione(cur, param_id, code, uid):
            primo = ParameterRepository().upsert_user_override(code, uid, "uno")
            secondo = ParameterRepository().upsert_user_override(code, uid, "due")

            self.assertIsNotNone(primo)
            self.assertEqual(secondo, primo)
            cur.execute(
                "SELECT count(*), max(overridden_value) FROM config.parameter_overrides "
                "WHERE parameter_id = %s AND django_user_id = %s",
                [param_id, uid],
            )
            self.assertEqual(cur.fetchone(), (1, "due"))
        self._nel_mondo(azione)

    # Scopo: La delete dell'override personale cancella per id E utente: l'id
    # dell'override di un altro utente non basta.
    def test_delete_non_tocca_l_override_di_un_altro(self):
        def azione(cur, _param_id, code, uid):
            altro = User.objects.create(username="zz_test_parametri_altro").id
            id_altrui = ParameterRepository().upsert_user_override(code, altro, "suo")

            self.assertFalse(ParameterRepository().delete_user_override(id_altrui, uid))
            cur.execute("SELECT 1 FROM config.parameter_overrides WHERE id = %s", [id_altrui])
            self.assertIsNotNone(cur.fetchone())
            self.assertTrue(ParameterRepository().delete_user_override(id_altrui, altro))
        self._nel_mondo(azione)

    # Scopo: ⭐ L'upsert su una riga SPENTA la riattiva (ok Tid
    # 2026-09-28): stesso id, valore nuovo, `attivo = true`. Prima rispondeva
    # con l'id e la riga restava spenta, cioe' invisibile alla lista e
    # ignorata dalla risoluzione. Anche `attivo` NULL: il modello lo ammette.
    def test_upsert_riattiva_la_riga_spenta(self):
        for spento in (False, None):
            with self.subTest(attivo=spento):
                def azione(cur, param_id, code, uid, spento=spento):
                    cur.execute(
                        "INSERT INTO config.parameter_overrides "
                        "(parameter_id, django_user_id, overridden_value, attivo) "
                        "VALUES (%s, %s, 'vecchio', %s) RETURNING id",
                        [param_id, uid, spento],
                    )
                    id_spento = cur.fetchone()[0]

                    esito = ParameterRepository().upsert_user_override(code, uid, "nuovo")

                    self.assertEqual(esito, id_spento)
                    cur.execute(
                        "SELECT overridden_value, attivo FROM config.parameter_overrides "
                        "WHERE id = %s",
                        [id_spento],
                    )
                    self.assertEqual(cur.fetchone(), ("nuovo", True))
                self._nel_mondo(azione)

    # Scopo: ⭐ BB `get_parameter_se_dichiarato` (2026-10-11): un codice non
    # dichiarato e' None, non `E_ERRORE_PARAMETRI_TABELLA`; un codice
    # dichiarato vale quanto la cascata. `get_parameters` lo esclude invece di
    # far fallire la richiesta. `get_parameter` resta rigido: e' il contratto
    # dei parametri obbligatori.
    def test_lettura_facoltativa_di_un_codice_non_dichiarato(self):
        def azione(_cur, _param_id, code, _uid):
            repo = ParameterRepository()
            self.assertIsNone(repo.get_parameter_se_dichiarato(_CODICE_INESISTENTE))
            self.assertEqual(repo.get_parameter_se_dichiarato(code), repo.get_parameter(code))
            risolti = repo.get_parameters([_CODICE_INESISTENTE, code])
            self.assertNotIn(_CODICE_INESISTENTE, risolti)
            if repo.get_parameter(code) is not None:
                self.assertIn(code, risolti)
            # Il rifiuto e' quello del catalogo, non un errore qualunque.
            with self.assertRaises(DatabaseError) as ctx:
                with transaction.atomic():
                    repo.get_parameter(_CODICE_INESISTENTE)
            self.assertEqual(db_error_code(ctx.exception), "E_ERRORE_PARAMETRI_TABELLA")
        self._nel_mondo(azione)

    # Scopo: ⭐ Un parametro che vale per tutti (`ammette_override` false) non
    # si personalizza: l'upsert del repository riceve il rifiuto del guard
    # (`E_PARAMETER_OVERRIDE_NON_AMMESSO`, DATO_ERRATO → 400) e non nasce
    # nessuna riga. Prima del 2026-10-25 l'override nasceva e il lettore del
    # default lo ignorava in silenzio.
    def test_parametro_per_tutti_non_si_personalizza(self):
        def azione(cur, param_id, code, uid):
            with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                ParameterRepository().upsert_user_override(code, uid, "mio")
            self.assertEqual(db_error_code(ctx.exception), "E_PARAMETER_OVERRIDE_NON_AMMESSO")
            cur.execute(
                "SELECT count(*) FROM config.parameter_overrides WHERE parameter_id = %s",
                [param_id],
            )
            self.assertEqual(cur.fetchone()[0], 0)
        self._nel_mondo(azione, ammette_override=False)

    # Scopo: ⭐ Il valore di un override ha la forma che il parametro dichiara
    # (`tipo_valore`, D-5 di brief-db-liste-datatable-grezze-secondo-giro,
    # 2026-10-31). Un `'0'` su un INTERO_POSITIVO lo rifiuta il guard a07
    # (`E_PARAMETER_VALORE_NON_CONFORME`, DATO_ERRATO), col campo `value` nel
    # canale strutturato: e' il campo del form che il FE evidenzia. Prima
    # l'override si salvava, e l'errore arrivava in lettura come TECNICO (500)
    # su ogni lista che legge il parametro. ⛔ Il BE non ricopia la regola:
    # la prova e' che il rifiuto arriva dal DB attraverso il repository.
    def test_valore_fuori_forma_non_si_salva(self):
        def azione(cur, param_id, code, uid):
            with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                ParameterRepository().upsert_user_override(code, uid, "0")
            diagnostica = diagnostica_db(ctx.exception)
            self.assertEqual(diagnostica.codice, "E_PARAMETER_VALORE_NON_CONFORME")
            self.assertEqual(diagnostica.campo, "value")
            cur.execute(
                "SELECT count(*) FROM config.parameter_overrides WHERE parameter_id = %s",
                [param_id],
            )
            self.assertEqual(cur.fetchone()[0], 0)
            # Lo stesso parametro accetta il valore nella forma giusta.
            self.assertIsNotNone(ParameterRepository().upsert_user_override(code, uid, "7"))
        self._nel_mondo(azione, tipo_valore="INTERO_POSITIVO", default_value="15")
