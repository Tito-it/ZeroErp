# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `/me/` sul DB vero dopo `20261124-14` (brief-db-emittente-del-super-
#        admin §4.4, R-DB-2): il blocco `emittente` del profilo porta solo la
#        riga di `config.user_emittenti_fiscali`, mai il gestore globale. Tre
#        utenti: il super admin senza riga (resta admin globale), l'operatore
#        configurato (il blocco e' la sua azienda), l'operatore senza riga
#        (nessun emittente, ne' di permesso ne' attivo: il FE non ha niente da
#        proporre come emittente di scrittura).
# Note: ⭐ CASI COSTRUITI, in transazione annullata, coi builder del pgTAP
#       `test-fn-get-soggetto-dati-and-user-profile` (casi 28-31). Il gestore
#       globale si costruisce se manca: senza di lui i casi senza riga sarebbero
#       verdi anche col ripiego, che non avrebbe niente da restituire.
#       ⚠️ Il claim dell'emittente attivo e' quello che il login emetterebbe
#       (`EmittenteAttivoService.risolvi_per_login`): il FE ricava l'emittente di
#       scrittura da `emittente` E da `emittente_attivo`, e vanno vuoti tutti e due.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_esiste_il_gestore_globale — il presupposto: il ripiego avrebbe da restituire
2. test_super_admin_senza_riga — admin globale, blocco NULL, sceglie l'emittente
3. test_operatore_configurato — il blocco e' la sua azienda, il login la attiva
4. test_operatore_senza_riga — blocco NULL, nessun emittente attivo, non sceglie
"""

from __future__ import annotations

import unittest

from django.contrib.auth.models import User
from django.db import connection
from rest_framework.test import APIClient

from apps.core.services.auth_constants import JWT_CLAIM_EMITTENTE_ATTIVO_ID
from apps.core.services.emittente_attivo_service import EmittenteAttivoService
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_URL = "/api/v1/core/me/"


class MeEmittenteSenzaGestoreGlobaleDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            # Il gestore globale: quello che c'e', o uno nuovo (come il pgTAP).
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account g"
                "                WHERE g.billing_account_id IS NULL AND g.is_default)"
            )
            if not cur.fetchone()[0]:
                cur.execute("SELECT soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente()")
                ruolo = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO anagrafiche.emittenti_fiscali_billing_account"
                    "       (emittente_soggetto_ruolo_id, billing_account_id, is_default)"
                    " VALUES (%s, NULL, true)",
                    [ruolo],
                )
            # ⚠️ Ogni builder in un'istruzione sua: la lettura viene dopo.
            self.configurato = self._operatore(cur, "me con azienda", False)
            cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
            self.azienda = int(cur.fetchone()[0])
            cur.execute(
                "SELECT dbops.fn_pgtap_sposta_scope_operatore(%s, %s)",
                [self.configurato, self.azienda],
            )
            self.senza_riga = self._operatore(cur, "me senza azienda", False)
            self.super_admin = self._operatore(cur, "me SA senza azienda", True)
            # Il builder esce coi vincoli IMMEDIATE: si torna a quelli di una
            # transazione nuova.
            cur.execute("SET CONSTRAINTS ALL DEFERRED")

    @staticmethod
    def _operatore(cur, etichetta: str, super_admin: bool) -> int:
        cur.execute(
            "SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano(%s, %s)",
            [etichetta, super_admin],
        )
        return int(cur.fetchone()[0])

    # Scopo: `/me/` come dopo il login: il contesto della richiesta e il claim
    #        dell'emittente attivo che il login avrebbe emesso.
    def _me(self, auth_user_id: int) -> tuple[dict, int | None]:
        attivo = EmittenteAttivoService().risolvi_per_login(auth_user_id)
        with connection.cursor() as cur:
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [auth_user_id])
        client = APIClient()
        client.force_authenticate(
            User.objects.get(id=auth_user_id),
            token={JWT_CLAIM_EMITTENTE_ATTIVO_ID: attivo},
        )
        risposta = client.get(_URL)
        self.assertEqual(risposta.status_code, 200, risposta.content)
        return risposta.json()["data"], attivo

    def test_esiste_il_gestore_globale(self):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1"
                "                 FROM anagrafiche.emittenti_fiscali_billing_account g"
                "                 JOIN anagrafiche.emittenti_fiscali ef"
                "                   ON ef.soggetto_ruolo_id = g.emittente_soggetto_ruolo_id"
                "                WHERE g.billing_account_id IS NULL AND g.is_default AND ef.attivo)"
            )
            self.assertTrue(cur.fetchone()[0])

    def test_super_admin_senza_riga(self):
        profilo, attivo = self._me(self.super_admin)
        self.assertIsNone(profilo["emittente"])
        self.assertTrue(profilo["is_admin_globale"])
        self.assertIsNone(attivo)
        self.assertIsNone(profilo["emittente_attivo"]["emittente_fiscale_id"])
        self.assertTrue(profilo["emittente_attivo"]["puo_scegliere"])

    def test_operatore_configurato(self):
        profilo, attivo = self._me(self.configurato)
        self.assertEqual(profilo["emittente"]["emittente_fiscale_id"], self.azienda)
        self.assertIsNotNone(profilo["emittente"]["user_emittente_fiscale_id"])
        self.assertFalse(profilo["is_admin_globale"])
        self.assertEqual(attivo, self.azienda)
        self.assertEqual(profilo["emittente_attivo"]["emittente_fiscale_id"], self.azienda)
        self.assertFalse(profilo["emittente_attivo"]["puo_scegliere"])

    # ⭐ Il caso che cambia: prima il blocco era il gestore globale, e il FE lo
    #    proponeva come emittente di scrittura di un'azienda non sua.
    def test_operatore_senza_riga(self):
        profilo, attivo = self._me(self.senza_riga)
        self.assertIsNone(profilo["emittente"])
        self.assertFalse(profilo["is_admin_globale"])
        self.assertIsNone(attivo)
        self.assertIsNone(profilo["emittente_attivo"]["emittente_fiscale_id"])
        self.assertFalse(profilo["emittente_attivo"]["puo_scegliere"])
        self.assertFalse(profilo["emittente_attivo"]["deve_scegliere"])
