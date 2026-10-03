# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'area «Accessi» sul DB vero (brief-db-be-fe-area-accessi): la
#        partizione delle credenziali fra i tre tab, le due liste nuove con
#        OGNI filtro e OGNI chiave d'ordinamento attraversati, lo stato della
#        credenziale, blocco e sblocco coi verbi veri, e la porta degli
#        operatori chiusa a chi operatore non e'.
# Note: in transazione annullata. I casi si COSTRUISCONO (operatore, cliente
#       dello shop, credenziale senza vesti): i dati di oggi non decidono
#       niente. Il contesto e' quello di un SUPER_ADMIN costruito, perche' i
#       verbi del blocco lo pretendono (`fn_guard_super_admin`).
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_ogni_credenziale_sta_in_un_tab_solo
2. test_altri_accessi_ogni_filtro_e_ogni_ordinamento
3. test_accessi_sistema_ogni_filtro_e_ogni_ordinamento
4. test_gli_stati_del_filtro_sono_quelli_del_db
5. test_blocca_e_sblocca_coi_verbi_veri
6. test_il_blocco_vuole_il_motivo
7. test_la_porta_operatori_non_apre_altre_categorie
8. test_lo_stato_della_veste_della_scheda_cliente_viene_dal_db
9. test_la_credenziale_di_sistema_non_si_blocca
"""

from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.amm_software.db.accessi_repository import (
    ACCESSI_ALTRI_ORDER_COLUMNS,
    ACCESSI_SISTEMA_ORDER_COLUMNS,
    STATI_ACCESSO,
    AccessiRepository,
)
from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.amm_software.services.accessi_service import AccessiService
from apps.amm_software.services.amm_software_service import AmmSoftwareService
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.portale.db.portale_repository import PortaleRepository


class AccessiDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: Costruisce i tre casi di persona e apre il contesto di un
    #        SUPER_ADMIN costruito. ⚠️ I builder PRIMA del contesto, e ognuno
    #        in un'istruzione sua (scrivono una saga).
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.cur = connection.cursor()
        self.addCleanup(self.cur.close)
        cur = self.cur
        cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('accessi admin', true)")
        self.admin = cur.fetchone()[0]
        cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('accessi operatore')")
        self.operatore = cur.fetchone()[0]
        self.shop = self._credenziale("accessi_solo_shop")
        cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente accessi')")
        cliente = cur.fetchone()[0]
        cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'CL')", [cliente])
        self.ruolo_cliente = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, "
            "ruolo_applicativo, attivo) VALUES (%s, %s, 'SHOP_CUSTOMER', true)",
            [self.ruolo_cliente, self.shop],
        )
        self.nuda = self._credenziale("accessi_senza_vesti")
        cur.execute("SELECT m.auth_user_id FROM dbops.fn_pgtap_crea_emittente_operatore() m")
        self.macchina = cur.fetchone()[0]
        cur.execute("SET LOCAL app.ruolo_applicativo = 'OPERATORE'")
        cur.execute("SET LOCAL app.current_user_id = %s", [str(self.admin)])
        cur.execute("SELECT script.fn_is_super_admin(%s)", [self.admin])
        self.assertTrue(cur.fetchone()[0], "il contesto del test dev'essere un SUPER_ADMIN")

    def _credenziale(self, username: str) -> int:
        self.cur.execute(
            "INSERT INTO auth_user (username, password, is_superuser, first_name, last_name, "
            "email, is_staff, is_active, date_joined) "
            "VALUES (%s, '!', false, '', '', '', false, true, now()) RETURNING id",
            [username],
        )
        return self.cur.fetchone()[0]

    def test_ogni_credenziale_sta_in_un_tab_solo(self):
        repo = AmmSoftwareRepository()
        self.assertEqual(repo.get_categoria_accesso(self.operatore), "OPERATORE")
        self.assertEqual(repo.get_categoria_accesso(self.shop), "ALTRO")
        self.assertEqual(repo.get_categoria_accesso(self.nuda), "ALTRO")

        operatori, _ = repo.list_operatori(limit=200)
        altri, _ = AccessiRepository().list_accessi_altri(limit=200, offset=0)
        id_operatori = {r["auth_user_id"] for r in operatori}
        id_altri = {r["auth_user_id"] for r in altri}
        self.assertIn(self.operatore, id_operatori)
        self.assertNotIn(self.operatore, id_altri)
        self.assertIn(self.shop, id_altri)
        self.assertNotIn(self.shop, id_operatori)

        nuda = next(r for r in altri if r["auth_user_id"] == self.nuda)
        self.assertIs(nuda["nessun_accesso"], True)
        self.assertEqual(nuda["stato_accesso"], "NESSUNO")
        self.assertEqual(nuda["vesti"], [])
        shop = next(r for r in altri if r["auth_user_id"] == self.shop)
        # `vesti` arriva DECODIFICATO: una lista, non la stringa del driver.
        self.assertIsInstance(shop["vesti"], list)
        self.assertEqual([v["ruolo_applicativo"] for v in shop["vesti"]], ["SHOP_CUSTOMER"])
        self.assertEqual(shop["vesti"][0]["stato"], "ATTIVO")

    # Scopo: Ogni filtro e ogni chiave d'ordinamento si eseguono sul DB vero
    #        (una colonna sbagliata e' un 500, non un errore educato), e i
    #        filtri tengono dentro e fuori i casi costruiti.
    def test_altri_accessi_ogni_filtro_e_ogni_ordinamento(self):
        repo = AccessiRepository()
        for chiave in ACCESSI_ALTRI_ORDER_COLUMNS:
            for verso in ("asc", "desc"):
                with self.subTest(order_by=chiave, order_dir=verso):
                    repo.list_accessi_altri(limit=5, offset=0, order_by=chiave, order_dir=verso)

        def ids(**filtri) -> set[int]:
            righe, _ = repo.list_accessi_altri(limit=200, offset=0, **filtri)
            return {r["auth_user_id"] for r in righe}

        self.assertIn(self.shop, ids(ruolo_applicativo="SHOP_CUSTOMER"))
        self.assertNotIn(self.nuda, ids(ruolo_applicativo="SHOP_CUSTOMER"))
        self.assertIn(self.nuda, ids(nessun_accesso=True))
        self.assertNotIn(self.shop, ids(nessun_accesso=True))
        self.assertIn(self.nuda, ids(stato_accesso="NESSUNO"))
        self.assertIn(self.shop, ids(stato_accesso="ATTIVO"))
        self.assertIn(self.shop, ids(secondo_fattore_stato="ASSENTE"))
        self.assertIn(self.shop, ids(secondo_fattore_obbligatorio=False))
        self.assertIn(self.shop, ids(bloccata=False))
        self.assertIn(self.shop, ids(search="accessi_solo_shop"))
        self.assertNotIn(self.nuda, ids(search="accessi_solo_shop"))

    def test_accessi_sistema_ogni_filtro_e_ogni_ordinamento(self):
        repo = AccessiRepository()
        for chiave in ACCESSI_SISTEMA_ORDER_COLUMNS:
            for verso in ("asc", "desc"):
                with self.subTest(order_by=chiave, order_dir=verso):
                    repo.list_accessi_sistema(limit=5, offset=0, order_by=chiave, order_dir=verso)
        for filtri in ({"tipo": "PROCESSO"}, {"tipo": "API_CLIENT"}, {"emittente_fiscale_id": 1},
                       {"identita_attiva": True}, {"bloccata": False}, {"search": "draina"}):
            with self.subTest(**filtri):
                righe, _ = repo.list_accessi_sistema(limit=5, offset=0, **filtri)
                # Nessuna persona costruita qui e' una macchina.
                self.assertFalse({self.operatore, self.shop, self.nuda} & {r["auth_user_id"] for r in righe})

    # Scopo: Il vocabolario del filtro `stato_accesso` e' uno specchio del DB:
    #        i quattro stati di `script.fn_stato_veste` piu' NESSUNO, che dichiara
    #        la vista. Se il DB ne aggiunge uno, il filtro lo rifiuterebbe.
    def test_gli_stati_del_filtro_sono_quelli_del_db(self):
        # ⚠️ `pg_get_functiondef` e non `prosrc`: una funzione `BEGIN ATOMIC`
        #    ha il corpo gia' analizzato, e `prosrc` e' vuoto.
        self.cur.execute("SELECT pg_get_functiondef('script.fn_stato_veste(bigint)'::regprocedure)")
        corpo = self.cur.fetchone()[0]
        self.cur.execute("SELECT pg_get_viewdef('anagrafiche.vw_accessi_altri'::regclass)")
        vista = self.cur.fetchone()[0]
        for stato in STATI_ACCESSO:
            with self.subTest(stato=stato):
                self.assertIn(f"'{stato}'", vista if stato == "NESSUNO" else corpo)

    def test_blocca_e_sblocca_coi_verbi_veri(self):
        servizio = AccessiService()
        prima = servizio.get_credenziale(self.shop)
        self.assertIs(prima["bloccata"], False)
        self.assertIs(prima["can_block"], True)

        dopo = servizio.blocca_credenziale(self.shop, "prova del test")
        self.assertIs(dopo["bloccata"], True)
        self.assertEqual(dopo["motivo_blocco"], "prova del test")
        self.cur.execute("SELECT username FROM auth_user WHERE id = %s", [self.admin])
        self.assertEqual(dopo["bloccata_da"], self.cur.fetchone()[0])
        altri, _ = AccessiRepository().list_accessi_altri(limit=200, offset=0, bloccata=True)
        self.assertIn(self.shop, {r["auth_user_id"] for r in altri})

        sbloccata = servizio.sblocca_credenziale(self.shop)
        self.assertIs(sbloccata["bloccata"], False)
        self.assertIsNone(sbloccata["motivo_blocco"])

    # Scopo: La capability del blocco e il rifiuto del verbo vengono dalla
    #        stessa check del DB (`fn_check_credenziale_bloccabile`): su una
    #        credenziale di sistema «Blocca» e' spento col motivo del DB, e il
    #        verbo rifiuta con lo stesso. Lo sblocco resta aperto (l'uscita).
    def test_la_credenziale_di_sistema_non_si_blocca(self):
        servizio = AccessiService()
        cred = servizio.get_credenziale(self.macchina)
        self.assertEqual(cred["categoria"], "SISTEMA")
        self.assertIs(cred["can_block"], False)
        self.assertEqual(cred["block_reason"], "CREDENZIALE_DI_SISTEMA")
        self.assertEqual(
            cred["block_reason_key"], "amministrazione.accessi.blocca_reason.credenziale_di_sistema",
        )

        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            servizio.blocca_credenziale(self.macchina, "chiave sospetta")
        self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_DI_SISTEMA")
        self.assertIs(servizio.get_credenziale(self.macchina)["bloccata"], False)

        self.assertIs(servizio.sblocca_credenziale(self.macchina)["bloccata"], False)

    def test_il_blocco_vuole_il_motivo(self):
        with self.assertRaises(DatabaseError) as ctx:
            AccessiService().blocca_credenziale(self.shop, None)
        self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_MOTIVO_OBBLIGATORIO")

    # Scopo: Le rotte `/operatori/<id>/` valgono per la categoria OPERATORE:
    #        un cliente dello shop o una credenziale senza vesti rispondono 404,
    #        e niente si scrive sulle loro vesti.
    def test_la_porta_operatori_non_apre_altre_categorie(self):
        servizio = AmmSoftwareService()
        self.assertEqual(servizio.get_operatore(self.operatore)["auth_user_id"], self.operatore)
        for uid in (self.shop, self.nuda):
            with self.subTest(auth_user_id=uid), self.assertRaises(ServiceError) as ctx:
                servizio.disabilita_operatore(uid)
            self.assertEqual(ctx.exception.code, "E_AMM_OPERATORE_NOT_FOUND")
        self.cur.execute(
            "SELECT attivo FROM anagrafiche.identita_digitali WHERE auth_user_id = %s", [self.shop],
        )
        self.assertEqual(self.cur.fetchall(), [(True,)])

    def test_lo_stato_della_veste_della_scheda_cliente_viene_dal_db(self):
        stato = PortaleRepository().get_stato_identita(self.ruolo_cliente, "SHOP_CUSTOMER")
        self.assertEqual(stato["stato"], "ATTIVO")
        self.assertEqual(stato["auth_user_id"], self.shop)
        nessuna = PortaleRepository().get_stato_identita(self.ruolo_cliente, "CLIENTE_PORTALE")
        self.assertEqual(nessuna["stato"], "NESSUNO")
