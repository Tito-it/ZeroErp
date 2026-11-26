# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'identificativo fiscale del soggetto, dal service vero al DATABASE
#        VERO (passaggio al BE del giro 3, brief-db-revisione-anagrafiche
#        §20.7): il doppione in creazione arriva dalle due porte come
#        `E_ADMIN_CF_DUPLICATO` col campo, la ditta individuale di chi e' gia'
#        privato nasce, e CF e P.IVA li normalizza il DB anche in modifica.
# Note: ⛔ Il backend NON tiene nessuna delle tre regole. Fino al 2026-11-26 il
#       service traduceva un `23505` su `uq_soggetto_idstato_id_fiscale_univoco`
#       che le porte non mandano piu', e il repository svuotava CF e P.IVA: i
#       test col repository mockato lo davano per verde. Qui la strada e'
#       quella vera, tradotta da `ErrorTranslator.to_api_error` come dal
#       middleware.
#       ⚠️ Il mondo si COSTRUISCE (CF e P.IVA liberi dai builder
#       `dbops.fn_pgtap_*_libero/a`, la PG da `fn_pgtap_crea_soggetto_pg`), in
#       transazione ANNULLATA; ogni rifiuto in un SAVEPOINT.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SoggettiIdentificativoDoppioDbTests.test_privato_con_cf_gia_usato_accende_codice_fiscale
2) SoggettiIdentificativoDoppioDbTests.test_ditta_individuale_di_chi_e_gia_privato_nasce
3) SoggettiIdentificativoDoppioDbTests.test_pg_con_piva_gia_usata_accende_partita_iva
4) SoggettiIdentificativoDoppioDbTests.test_update_normalizza_cf_e_piva_dal_db
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import connection, transaction

from apps.anagrafiche.services.soggetti_service import SoggettiService
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

_CODICE = "E_ADMIN_CF_DUPLICATO"


class SoggettiIdentificativoDoppioDbTests(unittest.TestCase):
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
                "nominativo": "Identificativo doppio", "tipo_contatto_id": cur.fetchone()[0],
                "email": "identificativo.doppio@test.invalid",
            }

    @staticmethod
    def _libero(builder: str) -> str:
        with connection.cursor() as cur:
            cur.execute(f"SELECT dbops.{builder}()")  # builder: costante del test
            return str(cur.fetchone()[0])

    # Scopo: una persona fisica; il CF del builder e' maschile, e la congruenza
    #        CF/sesso la verifica il BE.
    def _pf(self, codice: str, codice_fiscale: str, **extra: Any) -> dict[str, Any]:
        return {
            "tipo_soggetto_dettaglio_id": self.tipo[codice],
            "cognome": "Doppio", "nome": "Identificativo",
            "codice_fiscale": codice_fiscale, "sesso": "M",
            "contatto": dict(self.contatto),
            **extra,
        }

    @staticmethod
    def _identificativo(soggetto_id: str) -> tuple:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT codice_fiscale, partita_iva FROM anagrafiche.soggetti WHERE id = %s",
                [soggetto_id],
            )
            return cur.fetchone()

    # Scopo: il rifiuto atteso, tradotto come lo traduce il middleware, col campo.
    def _rifiuto(self, fn: Callable[[], Any], campo: str) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, _CODICE, f"{api.message} — {exc!r}")
            self.assertEqual(list(api.fields or ()), [campo])
            return
        self.fail(f"atteso {_CODICE}, accettato")

    # 1. Due privati con lo stesso CF: il secondo lo rifiuta la porta, sul CF.
    def test_privato_con_cf_gia_usato_accende_codice_fiscale(self) -> None:
        cf = self._libero("fn_pgtap_cf_libero")
        SoggettiService().create_soggetto(self._pf("PR", cf))
        self._rifiuto(
            lambda: SoggettiService().create_soggetto(self._pf("PR", cf)), "codice_fiscale",
        )

    # 2. La chiave e' la coppia CF e P.IVA (S4): la ditta individuale di chi e'
    #    gia' privato ha la sua P.IVA, e nasce. Prima il DB la rifiutava.
    def test_ditta_individuale_di_chi_e_gia_privato_nasce(self) -> None:
        cf = self._libero("fn_pgtap_cf_libero")
        privato = SoggettiService().create_soggetto(self._pf("PR", cf))
        piva = self._libero("fn_pgtap_piva_libera")
        ditta = SoggettiService().create_soggetto(self._pf("DI", cf, partita_iva=piva))
        self.assertNotEqual(privato["id"], ditta["id"])
        self.assertEqual(self._identificativo(ditta["id"]), (cf, piva))

    # 3. Una PG con la P.IVA di un'altra, nello stesso stato: il rifiuto
    #    accende `partita_iva`, il campo passato.
    def test_pg_con_piva_gia_usata_accende_partita_iva(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('BE identificativo doppio')::text")
            esistente = cur.fetchone()[0]
            cur.execute(
                "SELECT s.tipo_soggetto_dettaglio_id, s.codice_fiscale, s.partita_iva, st.codice_iso2 "
                "  FROM anagrafiche.soggetti s JOIN config.stati st ON st.id = s.stato_id "
                " WHERE s.id = %s",
                [esistente],
            )
            tipo_id, cf, piva, iso2 = cur.fetchone()
        self.assertTrue(piva, "il builder della PG non ha scritto la P.IVA")
        payload = {
            "tipo_soggetto_dettaglio_id": tipo_id,
            "ragione_sociale": "BE identificativo doppio bis",
            "codice_fiscale": cf, "partita_iva": piva, "stato_iso2": iso2,
            "contatto": dict(self.contatto),
        }
        self._rifiuto(lambda: SoggettiService().create_soggetto(payload), "partita_iva")

    # 4. In modifica CF e P.IVA arrivano al DB come li manda il client: il vuoto
    #    diventa NULL e il CF va in maiuscolo senza spazi per il trigger
    #    `trgfn_soggetti_normalize`, non per il repository.
    def test_update_normalizza_cf_e_piva_dal_db(self) -> None:
        cf = self._libero("fn_pgtap_cf_libero")
        piva = self._libero("fn_pgtap_piva_libera")
        ditta = SoggettiService().create_soggetto(self._pf("DI", cf, partita_iva=piva))
        # Da operatore un dato scritto non cambia: si prova su un privato senza
        # P.IVA (il vuoto resta vuoto) e sul CF riscritto uguale, in minuscolo.
        privato = SoggettiService().create_soggetto(
            self._pf("PR", self._libero("fn_pgtap_cf_libero")),
        )
        SoggettiService().update_soggetto(privato["id"], {"partita_iva": "  "})
        self.assertIsNone(self._identificativo(privato["id"])[1])
        SoggettiService().update_soggetto(ditta["id"], {"codice_fiscale": f" {cf.lower()} "})
        self.assertEqual(self._identificativo(ditta["id"])[0], cf)
