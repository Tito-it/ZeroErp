# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per capability di riga + non_editable_fields
#        nel servizio emittenti_fiscali (Fase 4 — A7/A9).
#        Mock repo, no DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_emittente_include_non_editable_fields — testata arricchita
 2) test_list_records_capability_slot_vuoto_emittente_attivo — can_configure=true
 3) test_list_records_capability_slot_vuoto_emittente_disattivo — can_configure=false
 4) test_list_records_capability_record_configurato — can_update + can_remove
 5) test_list_records_capability_utility_disattiva_blocca_configure — can_configure=false
 6) test_list_mapping_can_remove_senza_motivo — nessun motivo => gesto ammesso
 6b) test_list_mapping_can_remove_con_motivo — motivo dal DB => gesto spento + chiave i18n
 6c) test_list_mapping_storia_arriva_intatta — l'elenco per famiglia passa senza
     essere toccato (il servizio trasporta, non compone la frase)
 6d) test_list_mapping_storia_assente_resta_none — riga senza storia (gestore
     globale): NULL non diventa `[]`
"""

from unittest import TestCase
from unittest.mock import patch


SVC_MOD = "apps.anagrafiche.services.emittenti_fiscali_service"


class TestGetEmittenteNonEditable(TestCase):
    """Detail testata emittente arricchito con non_editable_fields."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch("apps.core.services.non_editable_fields_helper.LockColumnsRepository.list_non_editable")
    def test_get_emittente_include_non_editable_fields(self, mock_list_locks, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )

        mock_list_locks.return_value = ()
        mock_repo_cls.return_value.get_emittente.return_value = {
            "id": 7, "codice": "EF001", "soggetto_id": "uuid-x",
        }

        result = EmittentiFiscaliService().get_emittente(7)

        self.assertEqual(result["id"], 7)
        self.assertIn("non_editable_fields", result)
        self.assertEqual(set(result["non_editable_fields"]), {"codice", "soggetto_id"})


class TestUtilitiesCapability(TestCase):
    """Capability di riga matrice utility (slot/override pattern)."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_slot_vuoto_emittente_attivo(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Slot vuoto (record_id=None) + emittente attivo + utility attiva
        # -> can_configure=True, can_update/remove=False.
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": True,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": None, "utility_attiva": True},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["can_configure"])
        self.assertFalse(row["can_update"])
        self.assertFalse(row["can_remove"])

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_slot_vuoto_emittente_disattivo(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Slot vuoto + emittente disattivo -> can_configure=False (trigger DB
        # bloccherebbe child_requires_active_parent).
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": False,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": None, "utility_attiva": True},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        self.assertFalse(rows[0]["can_configure"])

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_record_configurato(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Record configurato (record_id valorizzato) -> can_update + can_remove,
        # can_configure=False (lo slot non e' piu' vuoto).
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": True,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": 99, "utility_attiva": True},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        row = rows[0]
        self.assertFalse(row["can_configure"])
        self.assertTrue(row["can_update"])
        self.assertTrue(row["can_remove"])

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_utility_disattiva_blocca_configure(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Slot vuoto + emittente attivo ma utility globalmente disattivata
        # -> can_configure=False.
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": True,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": None, "utility_attiva": False},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        self.assertFalse(rows[0]["can_configure"])


class TestBillingAccountMappingCapability(TestCase):
    """BA mapping: `can_remove` deriva dal motivo che arriva dalla riga.

    ⚠️ Le righe del fixture portano `rimozione_blocco_reason` perche' e' cio'
    che il repository produce dal 2026-08-27 (`LEFT JOIN LATERAL` su
    `script.fn_check_ba_cambio_emittente`).

    ⛔ E LA RIGA `is_default` NON PUO' AVERE MOTIVO NULLO, dal `20260827-03`:
    il gestore globale deve sempre esistere, quindi quella riga porta SEMPRE
    `DEFAULT_SINGLETON`. Un fixture che la costruisce senza motivo riproduce
    una forma che il repository non produce piu' — passa, e conferma un
    comportamento che non esiste. E' lo stesso difetto che questi test sono
    nati per chiudere, un livello piu' in su.
    """

    # Scopo: motivo assente (`NULL` dal database) => il gesto resta ammesso.
    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_mapping_can_remove_senza_motivo(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.list_by_emittente.return_value = (
            [
                {"id": 1, "billing_account_id": 100, "is_default": False,
                 "rimozione_blocco_reason": None, "rimozione_blocco_reason_key": None,
                 "rimozione_blocco_storia": None},
                {"id": 2, "billing_account_id": 101, "is_default": False,
                 "rimozione_blocco_reason": None, "rimozione_blocco_reason_key": None,
                 "rimozione_blocco_storia": None},
            ],
            2,
        )

        rows, total = EmittentiFiscaliBillingAccountService().list_mapping(7)

        self.assertEqual(total, 2)
        self.assertTrue(rows[0]["can_remove"])
        self.assertTrue(rows[1]["can_remove"])

    # Scopo: ⭐ IL RAMO CHE CONTA — con un motivo il gesto si spegne, e il
    #        motivo con la sua chiave i18n RESTANO nel payload: senza quelli
    #        il frontend avrebbe un pulsante grigio che non dice perche',
    #        che e' la stessa cosa di un'azione sparita.
    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_mapping_can_remove_con_motivo(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.list_by_emittente.return_value = (
            [
                {"id": 1, "billing_account_id": 100, "is_default": False,
                 "rimozione_blocco_reason": "BA_CON_STORIA",
                 "rimozione_blocco_reason_key":
                     "amministrazione.emittenti_fiscali.ba_blocco.con_storia",
                 "rimozione_blocco_storia": [
                     {"famiglia": "FATTURA", "descrizione": "Fattura di vendita", "n": 3},
                 ]},
                # ⛔ Il gestore globale e' bloccato dal SINGLETON, non dalla
                #    storia: il suo `dettaglio` non porta la chiave `storia`.
                #    Un fixture che gliela desse riprodurrebbe una forma che il
                #    database non produce.
                {"id": 2, "billing_account_id": None, "is_default": True,
                 "rimozione_blocco_reason": "DEFAULT_SINGLETON",
                 "rimozione_blocco_reason_key":
                     "amministrazione.emittenti_fiscali.ba_blocco.default_singleton",
                 "rimozione_blocco_storia": None},
            ],
            2,
        )

        rows, _ = EmittentiFiscaliBillingAccountService().list_mapping(7)

        # Entrambi i motivi a contratto spengono il gesto, e il servizio non
        # guarda QUALE sia: trasporta, non deduce.
        self.assertEqual([r["can_remove"] for r in rows], [False, False])
        self.assertEqual(
            [(r["rimozione_blocco_reason"], r["rimozione_blocco_reason_key"]) for r in rows],
            [
                ("BA_CON_STORIA",
                 "amministrazione.emittenti_fiscali.ba_blocco.con_storia"),
                ("DEFAULT_SINGLETON",
                 "amministrazione.emittenti_fiscali.ba_blocco.default_singleton"),
            ],
        )

    # Scopo: ⭐ L'ELENCO PER FAMIGLIA ARRIVA INTATTO — e' cio' che permette al
    #        tooltip di dire quanto dice il rifiuto. Il servizio TRASPORTA: non
    #        compone la frase (che vive nei `locales`), non riordina, non
    #        somma. Se un giorno qualcuno ci mettesse una `join()` qui, la
    #        traduzione uscirebbe dai `locales` senza che niente fallisca.
    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_mapping_storia_arriva_intatta(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )

        storia = [
            {"famiglia": "FATTURA", "descrizione": "Fattura di vendita", "n": 3},
            {"famiglia": "DDT", "descrizione": "Documento di trasporto", "n": 1},
        ]
        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.list_by_emittente.return_value = (
            [
                {"id": 1, "billing_account_id": 100, "is_default": False,
                 "rimozione_blocco_reason": "BA_CON_STORIA",
                 "rimozione_blocco_reason_key":
                     "amministrazione.emittenti_fiscali.ba_blocco.con_storia",
                 "rimozione_blocco_storia": storia},
            ],
            1,
        )

        rows, _ = EmittentiFiscaliBillingAccountService().list_mapping(7)

        self.assertFalse(rows[0]["can_remove"])
        # ⚠️ L'ORDINE E' IL CONTRATTO: la funzione DB usa `WITH ORDINALITY` per
        #    tenere l'ordine del catalogo (la fattura per prima). Un riordino
        #    qui farebbe leggere all'operatore un elenco diverso da quello del
        #    messaggio d'errore, sulla stessa condizione.
        self.assertEqual(rows[0]["rimozione_blocco_storia"], storia)

    # Scopo: ⛔ IL GEMELLO NEGATIVO — senza il quale il test sopra non
    #        distingue «trasporta la storia» da «inventa una lista». La riga del
    #        gestore globale non ha storia: `None` deve restare `None`, perche'
    #        `[]` direbbe «nessun documento» dove la risposta e' «questa
    #        domanda non si applica» (li' blocca il singleton).
    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_mapping_storia_assente_resta_none(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.list_by_emittente.return_value = (
            [
                {"id": 2, "billing_account_id": None, "is_default": True,
                 "rimozione_blocco_reason": "DEFAULT_SINGLETON",
                 "rimozione_blocco_reason_key":
                     "amministrazione.emittenti_fiscali.ba_blocco.default_singleton",
                 "rimozione_blocco_storia": None},
            ],
            1,
        )

        rows, _ = EmittentiFiscaliBillingAccountService().list_mapping(7)

        self.assertFalse(rows[0]["can_remove"])
        self.assertIsNone(rows[0]["rimozione_blocco_storia"])
