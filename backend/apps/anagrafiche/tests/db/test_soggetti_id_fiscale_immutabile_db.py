# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: CF e P.IVA gia' scritti di un soggetto, dal service vero al DATABASE
#        VERO (S-BE-3 di brief-db-revisione-dbops §32): la lista dei campi non
#        modificabili del dettaglio li porta dal DB (`fn_non_editable_fields`
#        sul record), e la PATCH che li cambia riceve
#        `E_SOGGETTO_ID_FISCALE_IMMUTABILE` col campo acceso.
# Note: ⛔ Il backend NON tiene la regola: fino al 2026-11-09 era un gap del
#       service («valorizzato → bloccato»), che bloccava anche il SUPER_ADMIN.
#       La sede e' `anagrafiche.fn_soggetto_id_fiscale_bloccato`: scritto e chi
#       agisce non e' SUPER_ADMIN. Per questo i due ruoli si COSTRUISCONO
#       (`dbops.fn_pgtap_crea_operatore_umano`): l'helper `apri_contesto_operatore`
#       sceglie un `is_superuser`, che puo' essere anche SUPER_ADMIN, e allora
#       niente risulterebbe bloccato — verde a vuoto.
#       Transazione ANNULLATA, ogni rifiuto in un SAVEPOINT.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SoggettiIdFiscaleImmutabileDbTests.test_operatore_vede_bloccati_i_dati_scritti
2) SoggettiIdFiscaleImmutabileDbTests.test_super_admin_li_puo_correggere
3) SoggettiIdFiscaleImmutabileDbTests.test_patch_che_cambia_un_dato_scritto_accende_il_campo
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.anagrafiche.services.soggetti_service import SoggettiService
from apps.core.db.lock_columns_repository import LockColumnsRepository
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_COLONNE = ("codice_fiscale", "partita_iva")


class SoggettiIdFiscaleImmutabileDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("anagrafiche.fn_soggetto_id_fiscale_bloccato(uuid,text)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        LockColumnsRepository.cache_clear()
        self.addCleanup(LockColumnsRepository.cache_clear)
        with connection.cursor() as cur:
            cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('BE-idfisc-SA', true)")
            self.super_admin = cur.fetchone()[0]
            cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('BE-idfisc-OP', false)")
            self.operatore = cur.fetchone()[0]
            self._agisci(cur, self.operatore)
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('BE id fiscale immutabile')::text")
            self.soggetto = cur.fetchone()[0]
            cur.execute(
                "SELECT codice_fiscale, partita_iva FROM anagrafiche.soggetti WHERE id = %s",
                [self.soggetto],
            )
            valori = dict(zip(_COLONNE, cur.fetchone(), strict=True))
        # Il builder scrive almeno uno dei due: e' quello che si prova.
        self.scritte = [c for c in _COLONNE if (valori[c] or "").strip()]
        self.assertTrue(self.scritte, "il builder della PG non ha scritto ne' CF ne' P.IVA")

    @staticmethod
    def _agisci(cur: Any, auth_user_id: int) -> None:
        cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [auth_user_id])

    def _non_editabili(self) -> list[str]:
        return SoggettiService._compute_non_editable_fields({"id": self.soggetto})

    # 1. Da operatore i dati scritti sono nella lista, insieme a `codice`.
    def test_operatore_vede_bloccati_i_dati_scritti(self) -> None:
        campi = self._non_editabili()
        self.assertIn("codice", campi)
        for colonna in self.scritte:
            self.assertIn(colonna, campi)

    # 2. Il SUPER_ADMIN li corregge: la lista non li spegne.
    def test_super_admin_li_puo_correggere(self) -> None:
        with connection.cursor() as cur:
            self._agisci(cur, self.super_admin)
        campi = self._non_editabili()
        for colonna in self.scritte:
            self.assertNotIn(colonna, campi)

    # 3. La PATCH dell'operatore che cambia un dato scritto con un altro valido
    #    e libero: il rifiuto del guard arriva tradotto come dal middleware,
    #    col campo. (Svuotarlo lo rifiuta prima l'obbligatorieta' della natura,
    #    `E_CF_OBBLIGATORIO`: un'altra regola.)
    def test_patch_che_cambia_un_dato_scritto_accende_il_campo(self) -> None:
        colonna = self.scritte[0]
        builder = "fn_pgtap_cf_libero" if colonna == "codice_fiscale" else "fn_pgtap_piva_libera"
        with connection.cursor() as cur:
            cur.execute(f"SELECT dbops.{builder}()")  # builder: costante del test
            nuovo = str(cur.fetchone()[0])
        try:
            with transaction.atomic():
                SoggettiService().update_soggetto(self.soggetto, {colonna: nuovo})
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, "E_SOGGETTO_ID_FISCALE_IMMUTABILE", f"{api.message} — {exc!r}")
            self.assertIn(colonna, api.fields or ())
            return
        self.fail("cambiare un dato fiscale scritto e' stato accettato")
