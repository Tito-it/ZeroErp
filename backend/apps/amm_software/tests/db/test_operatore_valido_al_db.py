# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La data di fine del RAPPORTO dell'operatore, dal drawer, sul DB vero
#        (brief-db-veste-utilizzabile §10): il dettaglio dice prima se si puo'
#        mettere (`can_set_valido_al` e il suo motivo, `20261007-27`), il PATCH
#        la mette, la toglie con `null` e non la tocca se assente; l'ultimo
#        SUPER_ADMIN senza scadenza e' rifiutato dal guard del DB (409).
# Note: in transazione annullata. L'ultimo SUPER_ADMIN senza scadenza si
#       COSTRUISCE, come nel pgTAP `test-super-admin-senza-scadenza-v1`: due
#       amministratori dalla madre, e agli altri SUPER_ADMIN del database una
#       data di fine lontana sulla veste. Vale su qualunque database.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_l_ultimo_super_admin_senza_scadenza_ha_la_data_spenta_e_il_409
2. test_la_data_di_fine_si_mette_si_toglie_e_un_salvataggio_senza_non_la_tocca
3. test_data_non_valida_o_prima_dell_inizio_rifiutata
"""

from __future__ import annotations

import unittest

from django.contrib.auth.models import User
from django.db import connection, transaction
from rest_framework.test import APIClient

from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

_URL = "/api/v1/amm-software/operatori/{}/"
_CHIAVE = "amministrazione.operatori.valido_al_reason.ultimo_super_admin"


class OperatoreValidoAlDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            # ⚠️ Ogni builder in un'istruzione sua, PRIMA del contesto
            #    operatore (scrive una saga).
            self.a = self._operatore(cur, "valido al SA A", True)
            self.b = self._operatore(cur, "valido al SA B", True)
            self.c = self._operatore(cur, "valido al non SA", False)
            # Il builder esce coi vincoli IMMEDIATE: si torna a quelli di una
            # transazione nuova.
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            self.admin_id = apri_contesto_operatore(cur)
            # Gli altri SUPER_ADMIN: una data di fine lontana sulla veste
            # (permesso: A e B non scadono). «Senza scadenza» restano A e B.
            cur.execute(
                """UPDATE anagrafiche.identita_digitali idg
                      SET valido_al = script.fn_data_operativa() + 3650
                    WHERE idg.valido_al IS NULL
                      AND idg.id NOT IN (%s, %s)
                      AND EXISTS (SELECT 1
                                    FROM config.profili_accesso_bindings pab
                                    JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
                                   WHERE pab.identita_digitale_id = idg.id
                                     AND pab.attivo AND pa.attivo
                                     AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)""",
                [self.a["identita_id"], self.b["identita_id"]],
            )
            # I rapporti partono indietro di dieci giorni: le date di fine di
            # prova cadono dentro la finestra.
            cur.execute(
                "UPDATE anagrafiche.risorse_umane SET valido_dal = script.fn_data_operativa() - 10 WHERE id IN (%s, %s, %s)",
                [self.a["risorsa_umana_id"], self.b["risorsa_umana_id"], self.c["risorsa_umana_id"]],
            )
            cur.execute("SELECT (script.fn_data_operativa() + 30)::text, (script.fn_data_operativa() - 11)::text")
            self.fra_un_mese, self.prima_dell_inizio = cur.fetchone()

    @staticmethod
    def _operatore(cur, etichetta: str, super_admin: bool) -> dict:
        cur.execute(
            "SELECT auth_user_id, identita_id, risorsa_umana_id "
            "  FROM dbops.fn_pgtap_crea_operatore_umano(%s, %s)",
            [etichetta, super_admin],
        )
        uid, identita, rapporto = cur.fetchone()
        return {"auth_user_id": uid, "identita_id": identita, "risorsa_umana_id": rapporto}

    # Scopo: Chiamata dell'amministratore a una view vera. Un rifiuto annulla
    #        il suo savepoint: la transazione resta usabile.
    def _admin(self, metodo: str, url: str, dati: dict | None = None):
        client = APIClient()
        client.force_authenticate(User.objects.get(id=self.admin_id))
        sid = transaction.savepoint_create()
        risposta = getattr(client, metodo)(url, dati, format="json")
        if risposta.status_code == 200:
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)
        return risposta

    def _dettaglio(self, operatore: dict) -> dict:
        r = self._admin("get", _URL.format(operatore["auth_user_id"]))
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["data"]

    @staticmethod
    def _terna(dettaglio: dict) -> tuple:
        return (dettaglio["can_set_valido_al"], dettaglio["valido_al_reason"], dettaglio["valido_al_reason_key"])

    def _patch(self, operatore: dict, dati: dict):
        return self._admin("patch", _URL.format(operatore["auth_user_id"]), dati)

    @staticmethod
    def _fine_rapporto(operatore: dict) -> str | None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT valido_al::text FROM anagrafiche.risorse_umane WHERE id = %s",
                [operatore["risorsa_umana_id"]],
            )
            return cur.fetchone()[0]

    # ⭐ Il 409 non provato al §9.3 (serviva un solo amministratore senza date):
    #    qui lo si costruisce.
    def test_l_ultimo_super_admin_senza_scadenza_ha_la_data_spenta_e_il_409(self):
        # Due amministratori senza scadenza: la data si mette, a tutti e due.
        self.assertEqual(self._terna(self._dettaglio(self.a)), (True, None, None))
        self.assertEqual(self._terna(self._dettaglio(self.b)), (True, None, None))

        r = self._patch(self.a, {"valido_al": self.fra_un_mese})
        self.assertEqual(r.status_code, 200, r.content)

        # B e' l'ultimo senza scadenza: campo spento col motivo e la chiave.
        self.assertEqual(self._terna(self._dettaglio(self.b)), (False, "ULTIMO_SUPER_ADMIN", _CHIAVE))
        # A ha gia' una data di fine: la puo' cambiare o togliere.
        self.assertEqual(self._terna(self._dettaglio(self.a)), (True, None, None))

        # La rete per la corsa fra due sessioni: il guard del DB.
        r = self._patch(self.b, {"valido_al": self.fra_un_mese})
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(r.json()["error"]["code"], "E_PROFILO_ULTIMO_SUPER_ADMIN")
        self.assertIsNone(self._fine_rapporto(self.b))

    def test_la_data_di_fine_si_mette_si_toglie_e_un_salvataggio_senza_non_la_tocca(self):
        r = self._patch(self.c, {"valido_al": self.fra_un_mese})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._fine_rapporto(self.c), self.fra_un_mese)

        # Chiave assente: la data resta.
        r = self._patch(self.c, {"first_name": "Altro"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._fine_rapporto(self.c), self.fra_un_mese)

        # `null`: la data si toglie (fino al 2026-10-07 voleva dire «non toccare»).
        r = self._patch(self.c, {"valido_al": None})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNone(self._fine_rapporto(self.c))

    def test_data_non_valida_o_prima_dell_inizio_rifiutata(self):
        r = self._patch(self.c, {"valido_al": "non-una-data"})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["error"]["code"], "E_AMM_VALIDAZIONE")

        # L'ordine delle date lo giudica il DB (`trgfn_guard_date_validita`).
        r = self._patch(self.c, {"valido_al": self.prima_dell_inizio})
        self.assertEqual(r.json()["error"]["code"], "E_DATA_AL_MINORE_DAL", r.content)
        self.assertIsNone(self._fine_rapporto(self.c))
