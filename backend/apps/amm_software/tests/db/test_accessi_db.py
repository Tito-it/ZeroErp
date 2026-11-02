# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'area «Accessi» sul DB vero (brief-db-be-fe-area-accessi): la
#        partizione delle credenziali fra i tre tab, le due liste nuove con
#        OGNI filtro e OGNI chiave d'ordinamento attraversati, lo stato della
#        credenziale, blocco e sblocco coi verbi veri, l'eliminazione col verbo
#        vero (brief-db-elimina-credenziale-senza-veste) e la porta degli
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
10. test_la_capability_dell_eliminazione_viene_dalla_check
11. test_elimina_la_credenziale_senza_vesti
12. test_la_credenziale_con_vesti_non_si_elimina
13. test_la_credenziale_con_storia_non_si_elimina

⭐ 10, 11 e 13 provano DUE MONDI, come il pgTAP `test-elimina-credenziale-v1`:
dove le FK del ponte django esistono (dbdev) il verbo elimina; dove non ci sono
(CI: Liquibase prima di `manage.py migrate`) la check e' fail-closed e il verbo
rifiuta con `E_CREDENZIALE_STORIA_NON_VERIFICABILE`. Nessun ramo e' saltato.
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
from apps.core.tests._helpers.parametro_di_prova import crea_parametro_di_prova
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

    # Scopo: Il mondo in cui gira il test: la FK di `identita_digitali` verso
    #        `django.auth_user` c'e'? E' la stessa domanda della check (D-4).
    def _ponte_django(self) -> bool:
        self.cur.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.contype = 'f' "
            "AND c.conrelid = 'anagrafiche.identita_digitali'::regclass "
            "AND c.confrelid = to_regclass('django.auth_user'))"
        )
        return self.cur.fetchone()[0]

    # Scopo: Le righe di «Altri accessi» di UNA credenziale costruita dal test,
    #        cercata per username: `{auth_user_id: riga}`.
    # ⚠️ Non la prima pagina della lista intera: con piu' credenziali ALTRO
    #    della pagina la riga cercata sta oltre, e un `assertNotIn` passerebbe
    #    a vuoto — verde per sottrazione.
    def _righe_altri(self, username: str) -> dict[int, dict]:
        righe, _ = AccessiRepository().list_accessi_altri(search=username, limit=200, offset=0)
        return {r["auth_user_id"]: r for r in righe}

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

    # Scopo: La capability dell'eliminazione, sulla riga di lista e sul
    #        dettaglio, e' il primo motivo di `fn_check_credenziale_eliminabile`:
    #        una veste (anche accesa) la spegne con CON_VESTI; la credenziale
    #        senza vesti si elimina dove il ponte c'e', ed e' fail-closed dove
    #        manca.
    def test_la_capability_dell_eliminazione_viene_dalla_check(self):
        servizio = AccessiService()
        for fonte, shop, nuda in (
            ("lista", self._righe_altri("accessi_solo_shop")[self.shop],
             self._righe_altri("accessi_senza_vesti")[self.nuda]),
            ("dettaglio", servizio.get_credenziale(self.shop), servizio.get_credenziale(self.nuda)),
        ):
            with self.subTest(fonte=fonte):
                self.assertIs(shop["can_delete"], False)
                self.assertEqual(shop["delete_reason"], "CON_VESTI")
                self.assertEqual(shop["delete_reason_key"], "amministrazione.accessi.elimina_reason.con_vesti")
                # Il dettaglio arriva DECODIFICATO: un oggetto, non la stringa del driver.
                self.assertIsInstance(shop["delete_dettaglio"], dict)
                if self._ponte_django():
                    self.assertIs(nuda["can_delete"], True)
                    self.assertIsNone(nuda["delete_reason"])
                    self.assertIsNone(nuda["delete_dettaglio"])
                else:
                    self.assertIs(nuda["can_delete"], False)
                    self.assertEqual(nuda["delete_reason"], "STORIA_NON_VERIFICABILE")

    # Scopo: Il verbo vero: col ponte la credenziale senza vesti se ne va,
    #        esce dalla lista e lascia la traccia (chi l'ha eliminata, e il suo
    #        username); senza il ponte rifiuta e la credenziale resta.
    def test_elimina_la_credenziale_senza_vesti(self):
        servizio = AccessiService()
        if not self._ponte_django():
            with self.assertRaises(DatabaseError) as ctx:
                servizio.elimina_credenziale(self.nuda)
            self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_STORIA_NON_VERIFICABILE")
            self.assertEqual(servizio.get_credenziale(self.nuda)["auth_user_id"], self.nuda)
            return

        # La stessa ricerca la trova PRIMA: l'`assertNotIn` sotto non e' a vuoto.
        self.assertIn(self.nuda, self._righe_altri("accessi_senza_vesti"))
        self.assertEqual(servizio.elimina_credenziale(self.nuda), {"status": "ok", "auth_user_id": self.nuda})
        self.assertIsNone(AccessiRepository().get_credenziale(self.nuda))
        self.assertNotIn(self.nuda, self._righe_altri("accessi_senza_vesti"))
        self.cur.execute(
            "SELECT username, eliminata_da FROM config.credenziali_eliminate WHERE auth_user_id = %s",
            [self.nuda],
        )
        self.assertEqual(self.cur.fetchall(), [("accessi_senza_vesti", self.admin)])

    # Scopo: Una veste, accesa o spenta, ferma l'eliminazione col codice del
    #        primo motivo, in ogni mondo (le vesti si guardano per prime).
    def test_la_credenziale_con_vesti_non_si_elimina(self):
        self.cur.execute(
            "UPDATE anagrafiche.identita_digitali SET attivo = false WHERE auth_user_id = %s", [self.shop],
        )
        with self.assertRaises(DatabaseError) as ctx:
            AccessiService().elimina_credenziale(self.shop)
        self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_CON_VESTI")
        self.assertEqual(AccessiService().get_credenziale(self.shop)["auth_user_id"], self.shop)

    # Scopo: Una credenziale senza vesti ma con una storia (un override di
    #        parametro a suo nome, FK NO ACTION) non si elimina, e il rifiuto
    #        nomina la tabella; senza il ponte e' il fail-closed.
    def test_la_credenziale_con_storia_non_si_elimina(self):
        # Il parametro si costruisce: quello col primo id del seed vale per
        # tutti, e il guard ne rifiuta l'override (brief-db-parametri-senza-override).
        param_id, _ = crea_parametro_di_prova(self.cur, codice="ZZ_TEST_ACCESSI_STORIA")
        self.cur.execute(
            "INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id) "
            "VALUES (%s, 'test accessi', %s)",
            [param_id, self.nuda],
        )
        ponte = self._ponte_django()
        cred = AccessiService().get_credenziale(self.nuda)
        self.assertIs(cred["can_delete"], False)
        if ponte:
            self.assertEqual(cred["delete_reason"], "CON_STORIA")
            self.assertIn("config.parameter_overrides", cred["delete_dettaglio"]["dove"])

        with self.assertRaises(DatabaseError) as ctx:
            AccessiService().elimina_credenziale(self.nuda)
        if ponte:
            self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_CON_STORIA")
            self.assertIn("config.parameter_overrides", str(ctx.exception))
        else:
            self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_STORIA_NON_VERIFICABILE")
        self.assertEqual(AccessiService().get_credenziale(self.nuda)["auth_user_id"], self.nuda)

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
