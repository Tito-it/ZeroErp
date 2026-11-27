# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I conti bancari dal service VERO sul DB vero, dopo il giro T8a di
#        brief-db-revisione-anagrafiche (§25.11, 2026-11-27): il backend non
#        ricopia piu' forma, formato e regole del predefinito, e ogni rifiuto
#        del DB deve arrivare al client col suo codice e col suo campo.
#        ⭐ Un test coi mock non vede niente di questo: la ricerca per IBAN
#        normalizzato e' un binding al BB `script.fn_normalizza_codice_bancario`,
#        e i rifiuti nascono da guard, EXCLUDE e REQUIRE del DB.
# Note: ⚠️ Il mondo si COSTRUISCE: emittente e operatore da
#       `dbops.fn_pgtap_crea_emittente_operatore` (col contesto aperto: i
#       soggetti sono sotto RLS), il cliente da `fn_pgtap_crea_cliente_ba`, la
#       filiale da `fn_pgtap_crea_filiale_bancaria` e l'IBAN coerente da
#       `fn_pgtap_iban`. Transazione SEMPRE annullata.
#       ⚠️ «Il conto del legame e' attivo» il DB lo controlla al COMMIT
#       (D-T8a-1 a). Qui la transazione non si chiude mai, quindi il test 5 lo
#       rende immediato (`SET CONSTRAINTS ALL IMMEDIATE`): prova che il codice
#       esce dal traduttore del service; che il traduttore stia FUORI dal
#       blocco atomico, dove il COMMIT vero lo solleva, lo dice il service.
#       Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) test_iban_scritto_a_gruppi_e_un_conto_solo — IBAN coi separatori: salvato
   normalizzato, ritrovato da una seconda nascita in un'altra forma e dalla
   ricerca con gli spazi
2) test_iban_incoerente_con_la_filiale — `E_CONTO_IBAN_FILIALE_INCOERENTE`,
   campo `bank_branch_id`
3) test_predefinito_per_periodo — un secondo predefinito sovrapposto e'
   `E_CONTO_PREDEFINITO_SOVRAPPOSTO`; uno programmato dopo la fine del primo
   nasce
4) test_predefinito_non_si_blocca — `E_CONTO_PREDEFINITO_BLOCCATO`
5) test_legame_su_conto_spento — `E_ATTIVO_PADRE_NON_ATTIVO`
6) test_la_lista_porta_i_campi_fermi — ogni legame porta `non_editable_fields`
   dal lucchetto vivo (conto, uso, possessore), la forma che il form legge
   con `campoFermo`
"""
from __future__ import annotations

import unittest
import uuid
from datetime import timedelta

from django.db import connection, transaction

from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.tests.db_e2e import (
    ContestoSu,
    apri_transazione_annullata,
    esegui_fixture,
    richiedi_db_provvisto,
)

_FIXTURE: tuple[str | ContestoSu, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    ContestoSu("_mondo"),
    """
    CREATE TEMP TABLE _cliente AS
    SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba(
        'conti forma e legami', NULL, (SELECT soggetto_ruolo_id FROM _mondo)) c
    """,
    """
    CREATE TEMP TABLE _banca AS
    SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('conti forma e legami')
    """,
)


class ContiBancariFormaELegamiDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("script.fn_normalizza_codice_bancario(text)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            esegui_fixture(cur, _FIXTURE)
            cur.execute("SELECT soggetto_id::text FROM _cliente")
            self.soggetto = cur.fetchone()[0]
            cur.execute("SELECT bank_branch_id FROM _banca")
            self.filiale = int(cur.fetchone()[0])
        self.svc = ContiBancariService()

    # Scopo: un IBAN coerente con la filiale del mondo, diverso a ogni chiamata.
    def _iban(self) -> str:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_iban(%s, %s)", [self.filiale, uuid.uuid4().hex[:12]])
            return cur.fetchone()[0]

    # Scopo: il rifiuto di `fn`, in un savepoint, come lo vede il client.
    def _rifiuto(self, fn):
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            return ErrorTranslator.to_api_error(exc)
        self.fail("la scrittura doveva essere rifiutata")

    def test_iban_scritto_a_gruppi_e_un_conto_solo(self) -> None:
        iban = self._iban()
        a_gruppi = "-".join(iban[i:i + 4] for i in range(0, len(iban), 4)).lower()
        primo = self.svc.create_conto_soggetto(self.soggetto, {
            "iban": a_gruppi, "bank_branch_id": self.filiale, "uso": "INCASSO",
        })
        con_spazi = " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))
        secondo = self.svc.create_conto_soggetto(self.soggetto, {
            "iban": con_spazi, "bank_branch_id": self.filiale, "uso": "PAGAMENTO",
        })
        self.assertEqual(primo["conto_bancario_id"], secondo["conto_bancario_id"])
        with connection.cursor() as cur:
            cur.execute(
                "SELECT iban, paese FROM anagrafiche.conti_bancari WHERE id = %s",
                [primo["conto_bancario_id"]],
            )
            self.assertEqual(cur.fetchone(), (iban, "IT"))
        trovati = self.svc.search_conti_bancari(con_spazi[:14])
        self.assertIn(primo["conto_bancario_id"], [r["id"] for r in trovati])

    def test_iban_incoerente_con_la_filiale(self) -> None:
        iban = self._iban()
        sbagliato = iban[:5] + "99999" + iban[10:]  # un altro ABI
        api = self._rifiuto(lambda: self.svc.create_conto_soggetto(self.soggetto, {
            "iban": sbagliato, "bank_branch_id": self.filiale,
        }))
        self.assertEqual(api.code, "E_CONTO_IBAN_FILIALE_INCOERENTE")
        self.assertIn("bank_branch_id", api.fields or ())

    def test_predefinito_per_periodo(self) -> None:
        oggi = oggi_aziendale()
        fine = oggi + timedelta(days=30)
        self.svc.create_conto_soggetto(self.soggetto, {
            "iban": self._iban(), "bank_branch_id": self.filiale, "uso": "INCASSO",
            "predefinito": True, "valido_al": fine.isoformat(),
        })
        api = self._rifiuto(lambda: self.svc.create_conto_soggetto(self.soggetto, {
            "iban": self._iban(), "bank_branch_id": self.filiale, "uso": "INCASSO",
            "predefinito": True, "valido_dal": fine.isoformat(),
        }))
        self.assertEqual(api.code, "E_CONTO_PREDEFINITO_SOVRAPPOSTO")
        # Il cambio programmato marca il nuovo legame dal suo primo giorno.
        nuovo = self.svc.create_conto_soggetto(self.soggetto, {
            "iban": self._iban(), "bank_branch_id": self.filiale, "uso": "INCASSO",
            "predefinito": True, "valido_dal": (fine + timedelta(days=1)).isoformat(),
        })
        self.assertTrue(nuovo["predefinito"])

    def test_predefinito_non_si_blocca(self) -> None:
        legame = self.svc.create_conto_soggetto(self.soggetto, {
            "iban": self._iban(), "bank_branch_id": self.filiale, "predefinito": True,
        })
        api = self._rifiuto(lambda: self.svc.update_conto_soggetto(
            self.soggetto, legame["id"], {"bloccato": True},
        ))
        self.assertEqual(api.code, "E_CONTO_PREDEFINITO_BLOCCATO")
        self.assertIn("bloccato", api.fields or ())

    def test_legame_su_conto_spento(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo) "
                "VALUES (%s, %s, false) RETURNING id",
                [self._iban(), self.filiale],
            )
            conto = int(cur.fetchone()[0])
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
        api = self._rifiuto(lambda: self.svc.create_conto_soggetto(self.soggetto, {
            "conto_bancario_id": conto,
        }))
        self.assertEqual(api.code, "E_ATTIVO_PADRE_NON_ATTIVO")

    def test_la_lista_porta_i_campi_fermi(self) -> None:
        self.svc.create_conto_soggetto(self.soggetto, {
            "iban": self._iban(), "bank_branch_id": self.filiale,
        })
        (riga,) = self.svc.list_conti_soggetto(self.soggetto)
        self.assertTrue(
            {"conto_bancario_id", "uso", "soggetto_id"} <= set(riga["non_editable_fields"]),
            riga["non_editable_fields"],
        )
