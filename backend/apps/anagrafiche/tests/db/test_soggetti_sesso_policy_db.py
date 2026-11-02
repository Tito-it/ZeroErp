# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il sesso di una persona fisica e la natura di dettaglio, dal service
#        vero al DATABASE VERO (brief-db-sesso-senza-default §6): cio' che i
#        test di servizio, col repository mockato, non possono vedere — il
#        binding della firma nuova di `fn_crea_soggetto_pf` (dettaglio e P.IVA
#        in coda) e il guard `trgfn_soggetti_guard_sesso_policy` che arriva
#        al client col campo da accendere.
# Note: ⛔ Il backend NON controlla il sesso: la regola ha una sede sola, il
#       guard, che legge `config.tipi_soggetto_dettaglio.sesso_policy`. Qui si
#       prova che il rifiuto arriva comunque, col codice del catalogo e
#       `fields = sesso`, passando da `ErrorTranslator.to_api_error` (lo stesso
#       punto del middleware).
#       ⚠️ Il mondo si COSTRUISCE (CF e P.IVA liberi dai builder
#       `dbops.fn_pgtap_*_libero/a`, la PG da `fn_pgtap_crea_soggetto_pg`), in
#       transazione ANNULLATA; ogni rifiuto in un SAVEPOINT.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SoggettiSessoPolicyDbTests.test_privato_senza_sesso_rifiutato_col_campo
2) SoggettiSessoPolicyDbTests.test_privato_con_x_accettato
3) SoggettiSessoPolicyDbTests.test_ditta_individuale_nasce_di_con_piva_e_senza_sesso
4) SoggettiSessoPolicyDbTests.test_societa_con_sesso_rifiutata_in_update
5) SoggettiSessoPolicyDbTests.test_update_sesso_vuoto_diventa_null
6) SoggettiSessoPolicyDbTests.test_lookup_tipi_espone_sesso_policy
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto


class SoggettiSessoPolicyDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute(
                "SELECT codice_interno, id FROM config.tipi_soggetto_dettaglio "
                " WHERE codice_interno IN ('PR', 'DI')"
            )
            self.tipo = dict(cur.fetchall())
            cur.execute("SELECT id FROM config.tipi_contatti ORDER BY id LIMIT 1")
            self.contatto = {
                "nominativo": "Sesso policy", "tipo_contatto_id": cur.fetchone()[0],
                "email": "sesso.policy@test.invalid",
            }

    # Scopo: un codice fiscale (o una P.IVA) valido e non ancora usato.
    @staticmethod
    def _libero(builder: str) -> str:
        with connection.cursor() as cur:
            cur.execute(f"SELECT dbops.{builder}()")
            return str(cur.fetchone()[0])

    def _pf(self, codice: str, **extra: Any) -> dict[str, Any]:
        return {
            "tipo_soggetto_dettaglio_id": self.tipo[codice],
            "cognome": "Policy", "nome": "Sesso",
            "codice_fiscale": self._libero("fn_pgtap_cf_libero"),
            "contatto": dict(self.contatto),
            **extra,
        }

    @staticmethod
    def _soggetto(soggetto_id: str) -> tuple:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT tsd.codice_interno, s.sesso, s.partita_iva "
                "  FROM anagrafiche.soggetti s "
                "  JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id "
                " WHERE s.id = %s",
                [soggetto_id],
            )
            return cur.fetchone()

    # Scopo: il rifiuto atteso, tradotto come lo traduce il middleware.
    def _rifiuto(self, fn: Callable[[], Any], codice: str) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, codice, f"{api.message} — {exc!r}")
            self.assertIn("sesso", api.fields or (), "campo sesso non acceso")
            self.assertEqual(ErrorTranslator.get_http_status(api), 400)
            return
        self.fail(f"atteso {codice}, accettato")

    # 1. Privato (REQUIRED) senza sesso: lo rifiuta il guard, non il backend.
    def test_privato_senza_sesso_rifiutato_col_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        payload = self._pf("PR")
        self._rifiuto(lambda: SoggettiService().create_soggetto(payload), "E_SESSO_OBBLIGATORIO")

    # 2. `X` («serve, ma non si puo' stabilire») e' un valore, non un rifiuto.
    def test_privato_con_x_accettato(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        creato = SoggettiService().create_soggetto(self._pf("PR", sesso="x"))
        self.assertEqual(self._soggetto(creato["id"])[:2], ("PR", "X"))

    # 3. Il difetto «la DI nasce PR»: il dettaglio scelto e la P.IVA arrivano
    #    alla funzione; il sesso, facoltativo, resta NULL.
    def test_ditta_individuale_nasce_di_con_piva_e_senza_sesso(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        piva = self._libero("fn_pgtap_piva_libera")
        creato = SoggettiService().create_soggetto(self._pf("DI", partita_iva=piva, sesso=""))
        self.assertEqual(self._soggetto(creato["id"]), ("DI", None, piva))

    # 4. Societa' (NONE): un sesso e' rifiutato, anche dall'update.
    def test_societa_con_sesso_rifiutata_in_update(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto sesso policy')")
            pg_id = str(cur.fetchone()[0])
        self._rifiuto(
            lambda: SoggettiService().update_soggetto(pg_id, {"sesso": "M"}),
            "E_SESSO_NON_AMMESSO",
        )

    # 5. Il vuoto e' «non indicato» (NULL): per la DI e' ammesso, e `''` lo
    #    rifiuterebbe il CHECK `chk_soggetti_sesso`.
    def test_update_sesso_vuoto_diventa_null(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        piva = self._libero("fn_pgtap_piva_libera")
        # `M`: il CF del builder e' maschile, e la congruenza CF/sesso la verifica il BE.
        creato = SoggettiService().create_soggetto(self._pf("DI", partita_iva=piva, sesso="M"))
        SoggettiService().update_soggetto(creato["id"], {"sesso": ""})
        self.assertEqual(self._soggetto(creato["id"])[1], None)

    # 6. Il form legge la policy dal lookup: la colonna c'e', coi valori del seed.
    def test_lookup_tipi_espone_sesso_policy(self):
        from apps.core.db.lookup_repository import LookupRepository

        policy = {
            t["codice_interno"]: t["sesso_policy"]
            for t in LookupRepository().list_tipi_soggetto_dettaglio()
        }
        self.assertEqual((policy["PR"], policy["DI"]), ("REQUIRED", "OPTIONAL"))
