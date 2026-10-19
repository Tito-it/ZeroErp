# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I comandi dell'operatore toccano la SOLA veste operatore della
#        credenziale, non le altre (cliente dello shop, del portale). Dal
#        riuso della credenziale (D-6) una persona ha una credenziale sola
#        con piu' vesti; fino al 2026-10-02 aggiornare, disabilitare,
#        riattivare e il binding SUPER_ADMIN lavoravano su TUTTE: salvare
#        `pochi`, che e' anche cliente dello shop, falliva con
#        E_SOGGETTI_RUOLI (la veste shop trasformata in OPERATORE, fermata
#        dal trigger di coerenza), e disabilitarlo toglieva lo shop al cliente.
# Note: sul DB vero, in transazione annullata. Il caso si COSTRUISCE: un
#       operatore dal percorso di produzione e una veste SHOP_CUSTOMER sul
#       ruolo cliente di un altro soggetto — come quella di `pochi`.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_salvare_l_operatore_non_tocca_la_veste_shop
2. test_disabilitare_e_riattivare_non_toccano_la_veste_shop — D-3: disabilita, l'invito riapre il rapporto, l'attivazione la veste
2a. test_l_interruttore_non_riaccende_e_il_salvataggio_non_richiude — D-3
2b. test_riaprire_il_rapporto_tiene_una_fine_futura — azzera solo la `valido_al` arrivata
3. test_il_super_admin_si_lega_alla_sola_veste_operatore
3-bis. test_togliere_il_super_admin_slega_la_veste — dalla madre `fn_slega_profilo_identita` (2026-10-19)
3a. test_super_admin_su_un_accesso_con_un_altro_profilo_e_un_400 — il vincolo, non piu' il silenzio (2026-10-18)
3b. test_due_profili_super_admin_attivi_non_si_sceglie — E_CONFIG_MANCANTE dal lettore del DB (2026-10-18; dal DB il 2026-10-19)
4. test_la_lista_legge_la_veste_operatore_anche_disabilitata
5. test_la_sola_veste_shop_non_e_un_operatore
6. test_spegnere_l_operatore_chiude_le_sessioni_della_sola_veste_operatore — e ne invalida gli inviti pendenti; le due strade chiudono il rapporto a oggi
"""

from __future__ import annotations

from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.amm_software.services.amm_software_service import AmmSoftwareService
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.risorse_umane_core_repository import RisorseUmaneCoreRepository
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.service_errors import ServiceError
from apps.core.services.invito_veste import PORTA_OPERATORE, PORTA_SHOP
from apps.core.services.token_service import TokenService
from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class OperatoreAltreVestiDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: Operatore + veste shop sulla stessa credenziale. Ritorna
    #        (auth_user_id, identita operatore, identita shop).
    @staticmethod
    def _operatore_anche_cliente_shop(cur) -> tuple[int, int, int]:
        # ⚠️ Ogni builder in un'istruzione sua (scrive una saga).
        cur.execute(
            "SELECT auth_user_id, identita_id FROM dbops.fn_pgtap_crea_operatore_umano('altre vesti')"
        )
        auth_user_id, identita_operatore = cur.fetchone()
        # Il ruolo cliente (CL) di un'azienda: e' cio' su cui sta una veste
        # shop. Il billing account non serve (e ha la sua RLS).
        cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente shop altre vesti')")
        cliente = cur.fetchone()[0]
        cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'CL')", [cliente])
        ruolo_cliente = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo) "
            "VALUES (%s, %s, 'SHOP_CUSTOMER', true) RETURNING id",
            [ruolo_cliente, auth_user_id],
        )
        return auth_user_id, identita_operatore, cur.fetchone()[0]

    @staticmethod
    def _veste(cur, identita_id: int) -> tuple[str, bool]:
        cur.execute(
            "SELECT ruolo_applicativo::text, attivo FROM anagrafiche.identita_digitali WHERE id = %s",
            [identita_id],
        )
        return cur.fetchone()

    def test_salvare_l_operatore_non_tocca_la_veste_shop(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # I builder PRIMA del contesto operatore, come nei pgTAP.
                uid, operatore, shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)

                # Il salvataggio del drawer: prima E_SOGGETTI_RUOLI.
                repo.update_operatore(uid, first_name="Altre")

                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", True))
                self.assertEqual(self._veste(cur, shop), ("SHOP_CUSTOMER", True))
                raise Annulla
        except Annulla:
            pass

    @staticmethod
    def _rapporto(cur, identita_id: int) -> tuple[bool, object, object]:
        cur.execute(
            "SELECT ru.attivo, ru.valido_dal, ru.valido_al "
            "  FROM anagrafiche.risorse_umane ru "
            "  JOIN anagrafiche.identita_digitali id ON id.soggetto_ruolo_id = ru.soggetto_ruolo_id "
            " WHERE id.id = %s",
            [identita_id],
        )
        return cur.fetchone()

    # ⭐ D-3 (2026-10-04): il giro intero, senza riattivazione diretta.
    #    Disabilitare chiude veste e rapporto; l'invito riapre il SOLO rapporto
    #    (la veste resta spenta), e la veste la accende l'attivazione. Lo shop
    #    della stessa credenziale non si muove mai.
    def test_disabilitare_e_riattivare_non_toccano_la_veste_shop(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # I builder PRIMA del contesto operatore, come nei pgTAP.
                uid, operatore, shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)
                _, valido_dal, _ = self._rapporto(cur, operatore)

                repo.disabilita_operatore(uid)
                # ⭐ R-DB-1 (2026-10-02): spenta, la veste TIENE il tipo.
                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", False))
                self.assertFalse(self._rapporto(cur, operatore)[0])
                # Il cliente non perde lo shop perche' lo si toglie come operatore.
                self.assertEqual(self._veste(cur, shop), ("SHOP_CUSTOMER", True))

                # L'invito: riapre il rapporto, non la porta.
                self.assertEqual(RisorseUmaneCoreRepository().riapri_risorsa_umana_della_veste(operatore), 1)
                self.assertEqual(self._rapporto(cur, operatore), (True, valido_dal, None))
                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", False))
                # Un secondo invito non riscrive niente.
                self.assertEqual(RisorseUmaneCoreRepository().riapri_risorsa_umana_della_veste(operatore), 0)

                # L'attivazione della persona accende la veste.
                self.assertTrue(AuthRepository().attiva_identita(
                    operatore, auth_user_id=uid, ruoli_applicativi=PORTA_OPERATORE.ruoli,
                ))
                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", True))
                self.assertEqual(self._veste(cur, shop), ("SHOP_CUSTOMER", True))
                raise Annulla
        except Annulla:
            pass

    # Scopo: D-3 — l'interruttore non riaccende un operatore spento (400 sul
    #        campo `attivo`), e salvare un operatore spento non richiude il
    #        rapporto che l'invito ha riaperto.
    def test_l_interruttore_non_riaccende_e_il_salvataggio_non_richiude(self):
        service = AmmSoftwareService()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid, operatore, _shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)

                AmmSoftwareRepository().disabilita_operatore(uid)
                RisorseUmaneCoreRepository().riapri_risorsa_umana_della_veste(operatore)

                with self.assertRaises(ServiceError) as ctx:
                    service.update_operatore(uid, {"attivo": True})
                self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", False))

                # Il salvataggio del drawer: `attivo: false` invariato.
                service.update_operatore(uid, {"attivo": False, "first_name": "Altre"})
                self.assertTrue(self._rapporto(cur, operatore)[0])
                raise Annulla
        except Annulla:
            pass

    # Scopo: Riaprire il rapporto azzera la `valido_al` arrivata (oggi o
    #        prima), non una FUTURA: quella e' una fine rapporto prevista
    #        dall'amministratore (Tid, 2026-10-04).
    def test_riaprire_il_rapporto_tiene_una_fine_futura(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid, operatore, _shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)
                _, valido_dal, _ = self._rapporto(cur, operatore)
                AmmSoftwareRepository().disabilita_operatore(uid)
                cur.execute(
                    "UPDATE anagrafiche.risorse_umane ru SET valido_al = script.fn_data_operativa() + 30 "
                    "  FROM anagrafiche.identita_digitali id "
                    " WHERE id.id = %s AND id.soggetto_ruolo_id = ru.soggetto_ruolo_id",
                    [operatore],
                )
                cur.execute("SELECT script.fn_data_operativa() + 30")
                fine = cur.fetchone()[0]

                self.assertEqual(RisorseUmaneCoreRepository().riapri_risorsa_umana_della_veste(operatore), 1)
                self.assertEqual(self._rapporto(cur, operatore), (True, valido_dal, fine))
                raise Annulla
        except Annulla:
            pass

    def test_il_super_admin_si_lega_alla_sola_veste_operatore(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # I builder PRIMA del contesto operatore, come nei pgTAP.
                uid, operatore, shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)

                repo.update_operatore(uid, is_super_admin=True)
                cur.execute(
                    "SELECT pab.identita_digitale_id FROM config.profili_accesso_bindings pab "
                    "JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id "
                    "WHERE pa.tipo = 'SUPER_ADMIN' AND pab.identita_digitale_id IN (%s, %s)",
                    [operatore, shop],
                )
                self.assertEqual([r[0] for r in cur.fetchall()], [operatore])
                raise Annulla
        except Annulla:
            pass

    # Scopo: Togliere il SUPER_ADMIN slega la veste operatore dalla madre
    #        `config.fn_slega_profilo_identita`, sul profilo del lettore
    #        (R-DB-16a, 2026-10-19; prima un DELETE del backend verso ogni
    #        profilo di quel tipo). Ripetuto non e' un errore.
    def test_togliere_il_super_admin_slega_la_veste(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid, operatore, _shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)

                repo.update_operatore(uid, is_super_admin=True)
                repo.update_operatore(uid, is_super_admin=False)
                repo.update_operatore(uid, is_super_admin=False)
                cur.execute(
                    "SELECT count(*) FROM config.profili_accesso_bindings WHERE identita_digitale_id = %s",
                    [operatore],
                )
                self.assertEqual(cur.fetchone()[0], 0)
                raise Annulla
        except Annulla:
            pass

    # Scopo: Il profilo SUPER_ADMIN si risolve come lo risolve il DB: fra gli
    #        ATTIVI, ed esattamente uno. Il modello non vieta un secondo profilo
    #        di quel tipo: con due il legame non sceglie, solleva
    #        E_CONFIG_MANCANTE prima di scrivere (era «more than one row», 500).
    #        Dal 2026-10-19 la regola e' del lettore `config.fn_profilo_super_admin_id`
    #        (R-DB-11a): l'errore sale come `DatabaseError` e lo traduce il
    #        middleware, qui si legge come lo legge lui.
    def test_due_profili_super_admin_attivi_non_si_sceglie(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid, operatore, _shop = self._operatore_anche_cliente_shop(cur)
                cur.execute(
                    "SELECT config.fn_scrivi_profilo_accesso('SUPER_ADMIN'::config.tipo_profilo_accesso,"
                    " 'E2E_SECONDO_SA', 'Secondo SA e2e', NULL, NULL,"
                    " '{\"richiede_secondo_fattore\": true}'::jsonb)"
                )
                apri_contesto_operatore(cur)

                with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                    AmmSoftwareRepository().update_operatore(uid, is_super_admin=True)
                self.assertEqual(structured_db_error_code(ctx.exception), "E_CONFIG_MANCANTE")
                cur.execute(
                    "SELECT count(*) FROM config.profili_accesso_bindings WHERE identita_digitale_id = %s",
                    [operatore],
                )
                self.assertEqual(cur.fetchone()[0], 0)
                raise Annulla
        except Annulla:
            pass

    # Scopo: SUPER_ADMIN su un accesso che ha gia' un ALTRO profilo legato:
    #        il vincolo «un profilo per identita'» lo rifiuta, e il service lo
    #        dice sul campo. Fino al 2026-10-18 la INSERT era `ON CONFLICT DO
    #        NOTHING`: la richiesta spariva e il salvataggio rispondeva ok.
    def test_super_admin_su_un_accesso_con_un_altro_profilo_e_un_400(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid, operatore, _shop = self._operatore_anche_cliente_shop(cur)
                cur.execute(
                    "SELECT config.fn_scrivi_profilo_accesso('AD_HOC'::config.tipo_profilo_accesso,"
                    " 'E2E_ALTRO_PROFILO', 'Profilo e2e', NULL, NULL, '{}'::jsonb)"
                )
                profilo = cur.fetchone()[0]
                cur.execute("SELECT config.fn_lega_profilo_identita(%s, %s)", [profilo, operatore])
                apri_contesto_operatore(cur)

                with self.assertRaises(ServiceError) as ctx:
                    AmmSoftwareService().update_operatore(uid, {"is_super_admin": True})
                self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
                self.assertEqual(ctx.exception.context.get("field"), "is_super_admin")
                raise Annulla
        except Annulla:
            pass

    # Scopo: La lista operatori legge la veste con la stessa definizione dei
    #        comandi (`_VESTE_OPERATORE`, la veste di riferimento del DB):
    #        disabilitato, l'operatore resta in elenco con la sua risorsa umana,
    #        il tipo OPERATORE e `veste_attiva = false` (R-DB-1: «disabilitato»
    #        si legge dallo stato, non dal ruolo); la veste shop della stessa
    #        credenziale non entra nella join (una riga sola).
    def test_la_lista_legge_la_veste_operatore_anche_disabilitata(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # I builder PRIMA del contesto operatore, come nei pgTAP.
                uid, _operatore, _shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)
                cur.execute("SELECT username FROM auth_user WHERE id = %s", [uid])
                username = cur.fetchone()[0]

                repo.disabilita_operatore(uid)
                righe, _totale = repo.list_operatori(search=username, limit=50)

                mie = [r for r in righe if r["auth_user_id"] == uid]
                self.assertEqual(len(mie), 1)
                self.assertEqual(mie[0]["ruolo_applicativo"], "OPERATORE")
                self.assertIs(mie[0]["veste_attiva"], False)
                self.assertIsNotNone(mie[0]["risorsa_umana_id"])
                self.assertIs(mie[0]["attivo"], False)
                # L'altra veste attiva e' un'informazione della riga (D-6).
                self.assertEqual(mie[0]["altre_vesti"], ["SHOP_CUSTOMER"])
                raise Annulla
        except Annulla:
            pass

    # Scopo: Una credenziale con la SOLA veste shop non e' un operatore: non
    #        compare ne' nella lista ne' nel riepilogo permessi (2026-10-02).
    #        Prima compariva in lista con veste e risorsa umana vuote.
    def test_la_sola_veste_shop_non_e_un_operatore(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # I builder PRIMA del contesto operatore, come nei pgTAP.
                cur.execute(
                    "INSERT INTO auth_user (username, password, is_superuser, first_name, "
                    "last_name, email, is_staff, is_active, date_joined) "
                    "VALUES ('solo_shop_altre_vesti', '!', false, '', '', '', false, true, now()) "
                    "RETURNING id"
                )
                uid = cur.fetchone()[0]
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Solo shop altre vesti')")
                cliente = cur.fetchone()[0]
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'CL')", [cliente])
                ruolo_cliente = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO anagrafiche.identita_digitali (soggetto_ruolo_id, auth_user_id, "
                    "ruolo_applicativo, attivo) VALUES (%s, %s, 'SHOP_CUSTOMER', true)",
                    [ruolo_cliente, uid],
                )
                apri_contesto_operatore(cur)

                righe, _totale = repo.list_operatori(search="solo_shop_altre_vesti", limit=50)
                self.assertNotIn(uid, [r["auth_user_id"] for r in righe])
                # Chiesto APPOSTA: il riepilogo deve scartare chi non e' operatore.
                riepilogo = repo.get_permessi_riepilogo([uid])
                self.assertNotIn(uid, [r["auth_user_id"] for r in riepilogo])
                raise Annulla
        except Annulla:
            pass

    # Scopo: Una sessione aperta in una veste: un OutstandingToken con il claim
    #        `identita_id` di quella veste, come lo scrive il login. Ritorna l'id.
    @staticmethod
    def _sessione(auth_user_id: int, identita_id: int) -> int:
        import uuid
        from datetime import timedelta

        import jwt
        from django.utils import timezone
        from rest_framework_simplejwt.settings import api_settings as simplejwt_settings
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        from apps.core.services.auth_constants import JWT_CLAIM_IDENTITA_ID, JWT_CLAIM_SID

        jti = uuid.uuid4().hex
        token = jwt.encode(
            {"token_type": "refresh", simplejwt_settings.USER_ID_CLAIM: auth_user_id, "jti": jti,
             JWT_CLAIM_IDENTITA_ID: identita_id, JWT_CLAIM_SID: uuid.uuid4().hex},
            "solo-per-il-test-la-firma-non-si-legge-xxxxxxxxxxxx", algorithm="HS256",
        )
        return OutstandingToken.objects.create(
            user_id=auth_user_id, jti=jti, token=token,
            created_at=timezone.now(), expires_at=timezone.now() + timedelta(days=1),
        ).id

    # Scopo: D-5 (2026-10-02) — «Disabilita» e l'interruttore «Accesso attivo»
    #        chiudono le sessioni della SOLA veste operatore: il cliente dello
    #        shop con la stessa credenziale resta connesso. Fino a quel giorno
    #        «Disabilita» le chiudeva tutte, e l'interruttore nessuna.
    #        A-5 (stesso giorno): anche l'invito operatore pendente smette di
    #        valere, e quello della veste shop no.
    def test_spegnere_l_operatore_chiude_le_sessioni_della_sola_veste_operatore(self):
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        for nome, spegni in (
            ("disabilita", lambda servizio, uid: servizio.disabilita_operatore(uid)),
            ("interruttore", lambda servizio, uid: servizio.update_operatore(uid, {"attivo": False})),
        ):
            with self.subTest(strada=nome):
                try:
                    with transaction.atomic(), connection.cursor() as cur:
                        # I builder PRIMA del contesto operatore, come nei pgTAP.
                        uid, operatore, shop = self._operatore_anche_cliente_shop(cur)
                        apri_contesto_operatore(cur)
                        s_operatore = self._sessione(uid, operatore)
                        s_shop = self._sessione(uid, shop)
                        inviti = TokenService()
                        invito_operatore = inviti.create(
                            tipo=PORTA_OPERATORE.token_invito, auth_user_id=uid,
                            meta={"identita_id": operatore},
                        )
                        invito_shop = inviti.create(
                            tipo=PORTA_SHOP.token_invito, auth_user_id=uid,
                            meta={"identita_id": shop},
                        )

                        spegni(AmmSoftwareService(), uid)

                        bloccati = set(
                            BlacklistedToken.objects.filter(token__user_id=uid)
                            .values_list("token_id", flat=True)
                        )
                        self.assertIn(s_operatore, bloccati)
                        self.assertNotIn(s_shop, bloccati)
                        self.assertEqual(self._veste(cur, shop), ("SHOP_CUSTOMER", True))
                        # 2026-10-04: le due strade scrivono lo stesso spegnimento,
                        # rapporto chiuso a oggi compreso.
                        attivo, _, valido_al = self._rapporto(cur, operatore)
                        cur.execute("SELECT script.fn_data_operativa()")
                        self.assertEqual((attivo, valido_al), (False, cur.fetchone()[0]))
                        self.assertIsNone(inviti.validate(invito_operatore, PORTA_OPERATORE.token_invito))
                        self.assertIsNotNone(inviti.validate(invito_shop, PORTA_SHOP.token_invito))
                        raise Annulla
                except Annulla:
                    pass
