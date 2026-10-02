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
2. test_disabilitare_e_riattivare_non_toccano_la_veste_shop
3. test_il_super_admin_si_lega_alla_sola_veste_operatore
4. test_la_lista_legge_la_veste_operatore_anche_disabilitata
5. test_la_sola_veste_shop_non_e_un_operatore
6. test_spegnere_l_operatore_chiude_le_sessioni_della_sola_veste_operatore — e ne invalida gli inviti pendenti
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.amm_software.services.amm_software_service import AmmSoftwareService
from apps.core.services.invito_veste import PORTA_OPERATORE, PORTA_SHOP
from apps.core.services.token_service import TokenService
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto


class _Annulla(Exception):
    """Esce dal blocco atomico annullandolo."""


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
                repo.update_operatore(uid, first_name="Altre", attivo=True)

                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", True))
                self.assertEqual(self._veste(cur, shop), ("SHOP_CUSTOMER", True))
                raise _Annulla
        except _Annulla:
            pass

    def test_disabilitare_e_riattivare_non_toccano_la_veste_shop(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # I builder PRIMA del contesto operatore, come nei pgTAP.
                uid, operatore, shop = self._operatore_anche_cliente_shop(cur)
                apri_contesto_operatore(cur)

                repo.disabilita_operatore(uid)
                # ⭐ R-DB-1 (2026-10-02): spenta, la veste TIENE il tipo.
                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", False))
                # Il cliente non perde lo shop perche' lo si toglie come operatore.
                self.assertEqual(self._veste(cur, shop), ("SHOP_CUSTOMER", True))

                repo.riattiva_operatore(uid)
                self.assertEqual(self._veste(cur, operatore), ("OPERATORE", True))
                self.assertEqual(self._veste(cur, shop), ("SHOP_CUSTOMER", True))
                raise _Annulla
        except _Annulla:
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
                raise _Annulla
        except _Annulla:
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
                raise _Annulla
        except _Annulla:
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
                riepilogo = repo.get_permessi_riepilogo()
                self.assertNotIn(uid, [r["auth_user_id"] for r in riepilogo["operatori"]])
                raise _Annulla
        except _Annulla:
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
                        self.assertIsNone(inviti.validate(invito_operatore, PORTA_OPERATORE.token_invito))
                        self.assertIsNotNone(inviti.validate(invito_shop, PORTA_SHOP.token_invito))
                        raise _Annulla
                except _Annulla:
                    pass
