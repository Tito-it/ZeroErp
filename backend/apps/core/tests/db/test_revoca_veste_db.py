# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La revoca di una veste sul DB vero, dai punti del backend che la
#        usano (passo 3b del brief-db-accessi-area-clienti §4.1, R2-a e R2-b):
#        `AuthRepository.revoca_veste` e `togli_revoca_veste` coi verbi veri,
#        il nuovo invito di `InvitoVeste.emetti` che toglie il segno, la
#        disattivazione di portale e shop e «Disabilita» dell'operatore che
#        lasciano il segno, l'accensione rifiutata su una veste revocata.
# Note: in transazione annullata. I casi si COSTRUISCONO (un SUPER_ADMIN di
#       contesto, una credenziale con una veste shop, un operatore): i dati di
#       oggi non decidono niente. I mock dei test di service non vedono il
#       binding dei verbi: e' per questo che il percorso si prova qui.
# ------------------------------------------------------------
"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_la_revoca_di_una_veste_accesa_la_spegne_col_segno
2. test_la_revoca_di_una_veste_spenta_mette_il_segno
3. test_la_veste_revocata_non_si_riaccende
4. test_il_nuovo_invito_toglie_il_segno
5. test_la_disattivazione_della_veste_portale_e_una_revoca
6. test_disabilita_operatore_lascia_il_segno
"""

from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.invito_veste import PORTA_SHOP, InvitoVeste
from apps.core.tests.db_e2e import (
    apri_super_admin_costruito,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)
from apps.portale.services.invito_portale_service import InvitoPortaleService


class RevocaVesteDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: Costruisce un SUPER_ADMIN di contesto, una credenziale con una
    #        veste SHOP_CUSTOMER accesa su un cliente e un operatore. ⚠️ I
    #        builder PRIMA del contesto, ognuno in un'istruzione sua.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.cur = connection.cursor()
        self.addCleanup(self.cur.close)
        cur = self.cur

        cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('revoca operatore')")
        self.operatore = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO auth_user (username, password, is_superuser, first_name, last_name, "
            "email, is_staff, is_active, date_joined) "
            "VALUES ('revoca_shop', '!', false, '', '', '', false, true, now()) RETURNING id"
        )
        self.shop = cur.fetchone()[0]
        cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente revoca')")
        cliente = cur.fetchone()[0]
        cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'CL')", [cliente])
        self.ruolo_cliente = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, "
            "ruolo_applicativo, attivo) VALUES (%s, %s, 'SHOP_CUSTOMER', true) RETURNING id",
            [self.ruolo_cliente, self.shop],
        )
        self.veste_shop = cur.fetchone()[0]

        self.admin = apri_super_admin_costruito(cur, etichetta="revoca admin")

    # Scopo: Lo stato di una veste (`script.fn_stato_veste`), il suo `attivo`
    #        e chi l'ha revocata.
    def _veste(self, identita_id: int) -> tuple[str, bool, int | None]:
        self.cur.execute(
            "SELECT sv.stato, idg.attivo, idg.revocata_da_user_id "
            "FROM anagrafiche.identita_digitali idg "
            "CROSS JOIN LATERAL script.fn_stato_veste(idg.id) sv WHERE idg.id = %s",
            [identita_id],
        )
        return self.cur.fetchone()

    def test_la_revoca_di_una_veste_accesa_la_spegne_col_segno(self):
        self.assertIs(AuthRepository().revoca_veste(self.veste_shop), True)
        self.assertEqual(self._veste(self.veste_shop), ("REVOCATA", False, self.admin))
        # Idempotente: la seconda dice «era spenta» e tiene il segno.
        self.assertIs(AuthRepository().revoca_veste(self.veste_shop), False)
        self.assertEqual(self._veste(self.veste_shop)[0], "REVOCATA")

    def test_la_revoca_di_una_veste_spenta_mette_il_segno(self):
        self.cur.execute(
            "UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = %s",
            [self.veste_shop],
        )
        self.assertEqual(self._veste(self.veste_shop)[0], "DISATTIVO")
        self.assertIs(AuthRepository().revoca_veste(self.veste_shop), False)
        self.assertEqual(self._veste(self.veste_shop)[0], "REVOCATA")

    def test_la_veste_revocata_non_si_riaccende(self):
        AuthRepository().revoca_veste(self.veste_shop)
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            AuthRepository().attiva_identita(
                self.veste_shop, auth_user_id=self.shop, ruoli_applicativi=("SHOP_CUSTOMER",),
            )
        self.assertEqual(structured_db_error_code(ctx.exception), "E_VESTE_REVOCATA")

    # Il nuovo invito toglie il segno nella transazione del token, e la veste
    # resta spenta finche' il link non la accende.
    def test_il_nuovo_invito_toglie_il_segno(self):
        AuthRepository().revoca_veste(self.veste_shop)
        InvitoVeste().emetti(
            PORTA_SHOP,
            auth_user_id=self.shop,
            identita_id=self.veste_shop,
            ruolo_applicativo="SHOP_CUSTOMER",
            invitato_da_user_id=self.admin,
        )
        stato, attivo, revocata_da = self._veste(self.veste_shop)
        self.assertNotEqual(stato, "REVOCATA")
        self.assertIs(attivo, False)
        self.assertIsNone(revocata_da)
        self.assertIs(
            AuthRepository().attiva_identita(
                self.veste_shop, auth_user_id=self.shop, ruoli_applicativi=("SHOP_CUSTOMER",),
            ),
            True,
        )

    # «Disattiva» di portale e shop revoca SEMPRE: anche la veste gia' spenta.
    def test_la_disattivazione_della_veste_portale_e_una_revoca(self):
        esito = InvitoPortaleService()._disattiva_veste_common(
            soggetto_ruolo_id=self.ruolo_cliente,
            ruolo_applicativo="SHOP_CUSTOMER",
            disattivato_da_user_id=self.admin,
        )
        self.assertEqual(esito["stato"], "REVOCATA")
        self.assertIs(esito["disattivato"], True)
        self.assertEqual(self._veste(self.veste_shop)[0], "REVOCATA")
        di_nuovo = InvitoPortaleService()._disattiva_veste_common(
            soggetto_ruolo_id=self.ruolo_cliente,
            ruolo_applicativo="SHOP_CUSTOMER",
            disattivato_da_user_id=self.admin,
        )
        self.assertIs(di_nuovo["disattivato"], False)

    def test_disabilita_operatore_lascia_il_segno(self):
        repo = AmmSoftwareRepository()
        veste = repo.get_veste_operatore_id(self.operatore)
        self.assertIsNotNone(veste)
        assert veste is not None
        self.cur.execute(
            "UPDATE anagrafiche.identita_digitali SET attivo = true WHERE id = %s", [veste],
        )
        repo.disabilita_operatore(self.operatore)
        self.assertEqual(self._veste(veste), ("REVOCATA", False, self.admin))
