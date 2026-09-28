# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli override di `config.parameter_overrides` scritti e cancellati dal
#        backend sono «di livello puro» (una dimensione valorizzata, tutte le
#        altre NULL), e un parametro inesistente non arriva all'INSERT. Sul
#        DATABASE PROVVISTO, in una transazione sempre annullata.
# Note: ⭐ Il caso che conta si COSTRUISCE: una riga MISTA (utente +
#        categoria, utente + sessione) accanto a quella pura, o una riga pura
#        SPENTA (`attivo = false`). Il modello le ammette (l'unicita' e' su
#        tutte le dimensioni insieme, nessun CHECK, `attivo` nullable). Fino al
#        2026-09-28 gli upsert non azzeravano tutte le dimensioni e la delete
#        emittente guardava solo utente e gruppo (F-5); un codice inesistente
#        era un `E_DATABASE` (E-9). La SQL e' la stessa per ogni livello
#        (`_altre_dimensioni_nulle`): il perimetro per livello lo prova
#        `test_parameter_repository_dimensioni`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ParameterOverridesDbTests.test_parametro_inesistente_non_scrive_niente (E-9)
2) ParameterOverridesDbTests.test_upsert_utente_non_tocca_la_riga_mista (F-5)
3) ParameterOverridesDbTests.test_delete_utente_non_cancella_la_riga_mista (F-5)
4) ParameterOverridesDbTests.test_upsert_riattiva_la_riga_spenta
"""

from __future__ import annotations

import unittest

from django.contrib.auth.models import User
from django.db import connection, transaction

from apps.core.db.parameter_repository import ParameterRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto

_CODICE_INESISTENTE = "ZZ_PARAMETRO_CHE_NON_ESISTE_TEST"


class ParameterOverridesDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: esegue `azione(cur, codice, uid)` in una transazione SEMPRE
    # annullata, con un parametro del seed e un utente creato qui.
    def _nel_mondo(self, azione) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT id, code FROM config.parameters ORDER BY id LIMIT 1")
                    riga = cur.fetchone()
                    self.assertIsNotNone(riga, "config.parameters vuota: il seed manca")
                    assert riga is not None
                    uid = User.objects.create(username="zz_test_parametri_puri").id
                    azione(cur, riga[0], riga[1], uid)
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

    # Scopo: ⭐ F-5 — l'upsert dell'override personale aggiorna solo la riga
    # PURA dell'utente: una riga mista (utente + categoria cliente) non e'
    # «sua». E' esattamente la dimensione che l'upsert non azzerava fino al
    # 2026-09-28: col codice vecchio questa riga veniva sovrascritta.
    def test_upsert_utente_non_tocca_la_riga_mista(self):
        def azione(cur, param_id, code, uid):
            cur.execute(
                "INSERT INTO anagrafiche.categorie_clienti (codice, descrizione, codice_interno) "
                "VALUES ('ZZ_TEST_PAR', 'Categoria di test', 'ZZ_TEST_PAR') RETURNING id"
            )
            categoria_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO config.parameter_overrides "
                "(parameter_id, django_user_id, categoria_cliente_id, overridden_value) "
                "VALUES (%s, %s, %s, 'misto') RETURNING id",
                [param_id, uid, categoria_id],
            )
            id_misto = cur.fetchone()[0]

            id_puro = ParameterRepository().upsert_user_override(code, uid, "puro")

            self.assertIsNotNone(id_puro)
            self.assertNotEqual(id_puro, id_misto)
            cur.execute(
                "SELECT overridden_value FROM config.parameter_overrides WHERE id = %s",
                [id_misto],
            )
            self.assertEqual(cur.fetchone()[0], "misto")
            # E un secondo upsert aggiorna la riga pura, non ne crea un'altra.
            self.assertEqual(ParameterRepository().upsert_user_override(code, uid, "bis"), id_puro)
        self._nel_mondo(azione)

    # Scopo: ⭐ F-5 — la delete dell'override personale non cancella una
    # riga mista, anche se ne conosce l'id.
    def test_delete_utente_non_cancella_la_riga_mista(self):
        def azione(cur, param_id, _code, uid):
            cur.execute(
                "INSERT INTO config.parameter_overrides "
                "(parameter_id, django_user_id, session_key, overridden_value) "
                "VALUES (%s, %s, 'sessione-test', 'misto') RETURNING id",
                [param_id, uid],
            )
            id_misto = cur.fetchone()[0]

            self.assertFalse(ParameterRepository().delete_user_override(id_misto, uid))
            cur.execute("SELECT 1 FROM config.parameter_overrides WHERE id = %s", [id_misto])
            self.assertIsNotNone(cur.fetchone())
        self._nel_mondo(azione)

    # Scopo: ⭐ L'upsert su una riga pura SPENTA la riattiva (ok Tid
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
