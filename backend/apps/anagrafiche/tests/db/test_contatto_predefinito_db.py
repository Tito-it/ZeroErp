# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Rendi predefinito» un contatto sul DATABASE VERO:
#        `SoggettiService.rendi_predefinito_contatto` e
#        `rendi_predefinito_contatto_ruolo` sopra i trigger del predefinito
#        (`trgfn_contatti_set_default_contatto`, `trgfn_contatti_guard_predefinito`,
#        brief-db-revisione-anagrafiche §22). I test di servizio mockano il
#        repository e non vedono il trigger che toglie il segno al vecchio.
# Note: ⚠️ Il mondo si COSTRUISCE (`dbops.fn_pgtap_crea_soggetto_pg`, col
#       contatto PRINCIPALE predefinito del soggetto), in transazione
#       ANNULLATA. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ContattoPredefinitoDbTests.test_soggetto_il_segno_passa_al_nuovo
   il secondo contatto nasce senza segno; reso predefinito, il primo lo perde
   e `soggetti.default_contatto_id` lo segue; rifarlo e' una riscrittura uguale;
   il predefinito con un altro accanto non si cancella
   (E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE).
2) ContattoPredefinitoDbTests.test_ruolo_contesto_suo_e_ownership
   il predefinito del ruolo cambia senza toccare quello del soggetto; un
   contatto del soggetto passato dalla rotta del ruolo e' E_ANAG_NOT_FOUND, e
   uno del ruolo dalle rotte del soggetto pure; la lista del soggetto porta i
   soli contatti del soggetto, quella del ruolo anche quelli del soggetto con
   la loro `fonte`.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.error_manager import ServiceError
from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class ContattoPredefinitoDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_soggetto_pg(text,integer,integer,text)")

    @staticmethod
    def _tipo(cur, codice: str) -> int:
        cur.execute("SELECT id FROM config.tipi_contatti WHERE codice = %s", [codice])
        return cur.fetchone()[0]

    @staticmethod
    def _predefiniti(cur, ids: list[int]) -> dict[int, bool]:
        cur.execute("SELECT id, is_default FROM anagrafiche.contatti WHERE id = ANY(%s)", [ids])
        return dict(cur.fetchall())

    def test_soggetto_il_segno_passa_al_nuovo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        svc = SoggettiService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto rendi predefinito')")
                soggetto_id = str(cur.fetchone()[0])
                cur.execute(
                    "SELECT id FROM anagrafiche.contatti WHERE soggetto_id = %s::uuid AND is_default",
                    [soggetto_id],
                )
                primo = cur.fetchone()[0]

                secondo = svc.create_contatto(soggetto_id, {
                    "nominativo": "Referente", "tipo_contatto_id": self._tipo(cur, "REFERENTE"),
                })["id"]
                self.assertEqual(self._predefiniti(cur, [primo, secondo]), {primo: True, secondo: False})

                self.assertEqual(svc.rendi_predefinito_contatto(soggetto_id, secondo), {"is_default": True})
                self.assertEqual(self._predefiniti(cur, [primo, secondo]), {primo: False, secondo: True})
                cur.execute("SELECT default_contatto_id FROM anagrafiche.soggetti WHERE id = %s::uuid", [soggetto_id])
                self.assertEqual(cur.fetchone()[0], secondo)

                # Rifarlo sul predefinito e' una riscrittura uguale, non un rifiuto.
                svc.rendi_predefinito_contatto(soggetto_id, secondo)
                self.assertEqual(self._predefiniti(cur, [primo, secondo]), {primo: False, secondo: True})

                # Il predefinito con un altro contatto accanto non si cancella.
                with self.assertRaises(Exception) as ctx, transaction.atomic():
                    svc.delete_contatto(soggetto_id, secondo)
                self.assertEqual(
                    structured_db_error_code(ctx.exception), "E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE",
                )
                raise Annulla
        except Annulla:
            pass

    def test_ruolo_contesto_suo_e_ownership(self):
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        svc = SoggettiService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore rendi predefinito')")
                soggetto_id = str(cur.fetchone()[0])
                cur.execute(
                    "SELECT id FROM anagrafiche.contatti WHERE soggetto_id = %s::uuid AND is_default",
                    [soggetto_id],
                )
                del_soggetto = cur.fetchone()[0]
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                sr_id = FornitoriService().crea_fornitore({"soggetto_id": soggetto_id})["soggetto_ruolo_id"]

                r1 = svc.create_contatto_ruolo(sr_id, {
                    "nominativo": "Referente ruolo", "tipo_contatto_id": self._tipo(cur, "REFERENTE"),
                })["id"]
                r2 = svc.create_contatto_ruolo(sr_id, {
                    "nominativo": "Principale ruolo", "tipo_contatto_id": self._tipo(cur, "PRINCIPALE"),
                })["id"]
                self.assertEqual(self._predefiniti(cur, [r1, r2]), {r1: True, r2: False})

                svc.rendi_predefinito_contatto_ruolo(sr_id, r2)
                self.assertEqual(
                    self._predefiniti(cur, [del_soggetto, r1, r2]),
                    {del_soggetto: True, r1: False, r2: True},
                )

                # Il contatto del soggetto non e' del ruolo: 404, nessuna scrittura.
                with self.assertRaises(ServiceError) as ctx:
                    svc.rendi_predefinito_contatto_ruolo(sr_id, del_soggetto)
                self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

                # E al contrario: dalle rotte del soggetto un contatto del ruolo non c'e'.
                for gesto in (
                    lambda: svc.rendi_predefinito_contatto(soggetto_id, r1),
                    lambda: svc.update_contatto(r1, {"note": "x"}, soggetto_id=soggetto_id),
                    lambda: svc.delete_contatto(soggetto_id, r1),
                ):
                    with self.subTest(gesto=gesto), self.assertRaises(ServiceError) as ctx:
                        gesto()
                    self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")
                self.assertEqual(
                    [c["id"] for c in svc.get_soggetto_contatti(soggetto_id)], [del_soggetto],
                )
                cur.execute("SELECT count(*) FROM anagrafiche.contatti WHERE id = ANY(%s)", [[r1, r2]])
                self.assertEqual(cur.fetchone()[0], 2)
                raise Annulla
        except Annulla:
            pass
