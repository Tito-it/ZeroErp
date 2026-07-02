# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test ordini_service (mock repository, no DB). Valida i guard di
#        stato/not-found, la derivazione soggetto_ruolo dal BA in create, e la
#        traduzione errori DB di _db_errors (IntegrityError -> codice vincolo;
#        DatabaseError trigger -> estrazione codice E_*).
# ------------------------------------------------------------

from contextlib import nullcontext
from datetime import date
from unittest.mock import MagicMock, patch

from django.db import DatabaseError, IntegrityError
from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.vendite.services import ordini_service
from apps.vendite.services.ordini_service import _db_errors

_REPO = "apps.vendite.services.ordini_service.OrdiniRepository"
# Helper auto-completamento step pratica (CONFERMA_ORDINE/INVIO_COMMESSA): usa
# PraticheRepository reale → patchato a no-op nei test di transizione stato ordine
# (SimpleTestCase, DB vietato). L'auto-completamento e' testato a parte.
_COMPLETA_STEP = "apps.vendite.services.ordini_service._completa_flusso_ordine_pratica"


def _patch_atomic_noop(testcase) -> None:
    # conferma avvolge update_stato + completamento step in transaction.atomic:
    # no-op in SimpleTestCase (no connessione DB), come test_preventivi_service.
    patcher = patch("apps.vendite.services.ordini_service.transaction.atomic")
    mock_atomic = patcher.start()
    mock_atomic.return_value.__enter__ = MagicMock(return_value=None)
    mock_atomic.return_value.__exit__ = MagicMock(return_value=False)
    testcase.addCleanup(patcher.stop)


class OrdiniServiceGuardsTests(SimpleTestCase):
    """Guard di stato e not-found (mock repository)."""

    def setUp(self) -> None:
        _patch_atomic_noop(self)

    @patch(_REPO)
    def test_get_ordine_not_found(self, repo_cls) -> None:
        repo_cls.return_value.get_ordine.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.get_ordine(99)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")

    @patch(_REPO)
    def test_conferma_stato_errato(self, repo_cls) -> None:
        # Ordine gia' CONFERMATO: la conferma non e' ammessa.
        repo_cls.return_value.get_stato_codice.return_value = "CONFERMATO"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(7)
        self.assertEqual(cm.exception.code, "E_ORD_STATO_TRANSIZIONE")

    @patch(_REPO)
    def test_conferma_senza_righe(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = []
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(7)
        self.assertEqual(cm.exception.code, "E_ORD_NESSUNA_RIGA")

    @patch(_COMPLETA_STEP)
    @patch(_REPO)
    def test_conferma_ok_deriva_stato(self, repo_cls, _mock_step) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = [{"id": 1}]
        repo.get_stato_id_by_codice.return_value = 2
        out = ordini_service.conferma(7)
        self.assertEqual(out["stato"], "CONFERMATO")
        repo.update_stato.assert_called_once_with(7, 2)

    @patch(_REPO)
    def test_crea_ordine_deriva_soggetto_ruolo_da_ba(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_soggetto_ruolo_id_by_ba.return_value = 555
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_ordine.return_value = {"id": 7, "uid": "u", "numero": "ORD0007"}
        out = ordini_service.crea_ordine({"billing_account_id": 3, "utility_id": 1})
        self.assertEqual(out["numero"], "ORD0007")
        repo.get_soggetto_ruolo_id_by_ba.assert_called_once_with(3)
        # soggetto_ruolo_id derivato passato a create_ordine
        self.assertEqual(repo.create_ordine.call_args.kwargs["soggetto_ruolo_id"], 555)

    @patch(_REPO)
    def test_crea_ordine_senza_cliente_errore(self, repo_cls) -> None:
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine({"utility_id": 1})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")

    @patch(_REPO)
    def test_aggiorna_ordine_cambio_ba_rifiutato(self, repo_cls) -> None:
        # Cliente immutabile: cambiare billing_account_id su un ordine esistente
        # e' rifiutato (lascerebbe soggetto_ruolo_id stantio).
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_ordine.return_value = {"id": 7, "billing_account_id": 3}
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_ordine(7, {"billing_account_id": 99})
        # Codice dedicato, allineato alla difesa DB lock-columns (DB-ORD-LOCK).
        self.assertEqual(cm.exception.code, "E_ORD_CLIENTE_IMMUTABILE")
        repo.update_ordine.assert_not_called()

    @patch(_REPO)
    def test_aggiorna_ordine_ba_invariato_tollerato(self, repo_cls) -> None:
        # Il form FE puo' reinviare il BA invariato: tollerato, ma escluso
        # dall'UPDATE (non e' nella whitelist). Aggiorna solo gli altri campi.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_ordine.return_value = {"id": 7, "billing_account_id": 3}
        ordini_service.aggiorna_ordine(7, {"billing_account_id": 3, "utility_id": 9})
        kwargs = repo.update_ordine.call_args.kwargs
        self.assertNotIn("billing_account_id", kwargs)
        self.assertEqual(kwargs["utility_id"], 9)

    @patch(_REPO)
    def test_aggiorna_ordine_ba_non_numerico_rifiutato(self, repo_cls) -> None:
        # Input malformato: billing_account_id non numerico -> 422 parlante
        # (E_ORD_VALIDAZIONE), non 500 da int() non gestito.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_ordine(7, {"billing_account_id": "abc"})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        repo.update_ordine.assert_not_called()

    @patch(_REPO)
    def test_aggiorna_ordine_senza_ba_aggiorna(self, repo_cls) -> None:
        # Payload senza billing_account_id: nessun confronto, update diretto.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        ordini_service.aggiorna_ordine(7, {"utility_id": 9})
        repo.get_ordine.assert_not_called()
        repo.update_ordine.assert_called_once()

    @patch(_REPO)
    def test_get_ordine_merge_capabilities_data_driven(self, repo_cls) -> None:
        # get_ordine fonde le capability da fn_available_actions_ordine
        # (available_actions, can_edit_*, ...). `can_conferma` non e' piu' un flag.
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        repo.list_righe.return_value = [{"id": 1}]
        repo.get_capabilities.return_value = {
            "available_actions": [{"key": "conferma", "target_state": "CONFERMATO"}],
            "can_edit_testata": True,
            "can_push_commessa": False,
            "stato_codice": "DRAFT",
        }
        out = ordini_service.get_ordine(7)
        self.assertEqual(out["available_actions"][0]["key"], "conferma")
        self.assertEqual(out["righe_count"], 1)
        self.assertEqual(out["stato_codice"], "DRAFT")
        self.assertNotIn("can_conferma", out)

    @patch(_REPO)
    def test_cambia_stato_ok(self, repo_cls) -> None:
        # Transizione generica (es. annulla): risolve il codice stato e delega
        # l'enforcement al trigger DB.
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        repo.get_stato_id_by_codice.return_value = 6
        out = ordini_service.cambia_stato(7, "ANNULLATO")
        self.assertEqual(out["stato"], "ANNULLATO")
        self.assertEqual(out["stato_precedente"], "DRAFT")
        repo.update_stato.assert_called_once_with(7, 6)

    @patch(_REPO)
    def test_cambia_stato_codice_inesistente(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        repo.get_stato_id_by_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_stato(7, "INESISTENTE")
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        repo.update_stato.assert_not_called()

    @patch(_REPO)
    def test_elimina_ordine_con_righe_rifiutato(self, repo_cls) -> None:
        # Niente hard-delete di dati reali (allineato a preventivi): un ordine
        # in bozza CON righe non si cancella, si annulla.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = [{"id": 1}]
        with self.assertRaises(ServiceError) as cm:
            ordini_service.elimina_ordine(7)
        self.assertEqual(cm.exception.code, "E_ORD_STATO_TRANSIZIONE")
        repo.delete_ordine.assert_not_called()

    @patch(_REPO)
    def test_elimina_ordine_bozza_orfana_ok(self, repo_cls) -> None:
        # Bozza orfana (DRAFT, zero righe): hard-delete ammesso (cleanup
        # abbandono auto-save).
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = []
        repo.delete_ordine.return_value = True
        out = ordini_service.elimina_ordine(7)
        self.assertTrue(out["deleted"])
        repo.delete_ordine.assert_called_once_with(7)


_SVC = "apps.vendite.services.ordini_service"


class OrdiniRigaComponentiOverrideTests(SimpleTestCase):
    """gestisci_riga: override prezzi componenti BoM pre-save (dialog).

    Simmetria con preventivi: gate autorizzazione + override normalizzati
    passati a init_componenti_riga per articolo composito.
    """

    @patch(f"{_SVC}._data_riferimento", return_value=date(2026, 6, 5))
    @patch(f"{_SVC}._resolve_emittente_sr_id", return_value=99)
    @patch(f"{_SVC}.validate_componenti_overrides_authorization")
    @patch(f"{_SVC}.transaction")
    @patch(_REPO)
    def test_gestisci_riga_composito_passa_overrides(
        self, repo_cls, mock_tx, mock_gate, _sr, _dr,
    ) -> None:
        mock_tx.atomic.return_value = nullcontext()
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        repo.is_articolo_composito.return_value = True
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 50}

        payload = {
            "articolo_id": "ART1", "qta_operativa": 2, "iva_id": 1,
            "uom_operativa_id": 3,
            "componenti_overrides": {"10": "5.50"},
        }
        out = ordini_service.gestisci_riga(7, payload, auth_user_id=42)

        # Gate L1 autorizzazione invocato col payload + utente.
        mock_gate.assert_called_once()
        # Override normalizzati passati all'init componenti (articolo composito).
        _, kwargs = repo.init_componenti_riga.call_args
        self.assertEqual(kwargs["componenti_overrides"], {"10": "5.50"})
        self.assertTrue(out["is_composito"])

    @patch(f"{_SVC}._data_riferimento", return_value=date(2026, 6, 5))
    @patch(f"{_SVC}._resolve_emittente_sr_id", return_value=99)
    @patch(f"{_SVC}.validate_componenti_overrides_authorization")
    @patch(f"{_SVC}.transaction")
    @patch(_REPO)
    def test_gestisci_riga_composito_senza_overrides(
        self, repo_cls, mock_tx, mock_gate, _sr, _dr,
    ) -> None:
        # Articolo composito senza override: init con componenti_overrides=None
        # (la fn DB risolve i prezzi dal pricing corrente).
        mock_tx.atomic.return_value = nullcontext()
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        repo.is_articolo_composito.return_value = True
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 51}

        ordini_service.gestisci_riga(
            7, {"articolo_id": "ART1", "qta_operativa": 1, "iva_id": 1,
                "uom_operativa_id": 3},
            auth_user_id=42,
        )
        _, kwargs = repo.init_componenti_riga.call_args
        self.assertIsNone(kwargs["componenti_overrides"])


class OrdiniDbErrorsTests(SimpleTestCase):
    """Traduzione errori DB di _db_errors (il bug originale crashava qui)."""

    def test_integrity_error_unique_mappato(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError(
                    'duplicate key value violates unique constraint '
                    '"uq_ordrig_riga_nr"',
                )
        self.assertEqual(cm.exception.code, "E_VENDITE_DUPLICATO")

    def test_integrity_error_fallback(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError("vincolo sconosciuto xyz")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    def test_database_error_trigger_code_estratto(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise DatabaseError("E_ORDINE_TRANSIZIONE_NON_AMMESSA: dettaglio")
        self.assertEqual(cm.exception.code, "E_ORDINE_TRANSIZIONE_NON_AMMESSA")


_PREV_REPO = "apps.vendite.db.preventivi_repository.PreventiviRepository"
_OFF_REPO = "apps.vendite.db.offerte_repository.OfferteRepository"
_ATOMIC = "apps.vendite.services.ordini_service.transaction.atomic"
_SVC = "apps.vendite.services.ordini_service"


class OrdiniConversioneUpstreamTests(SimpleTestCase):
    """crea_ordine_da_preventivo (modello split D8): delega solo-merce alla
    primitiva DB + ritorno numero. Stato/righe sono validati dalla fn DB."""

    @patch(_REPO)
    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_ok(self, prev_cls, ord_cls) -> None:
        # La primitiva DB ritorna l'id ordine; la testata fornisce il numero.
        prev_cls.return_value.push_a_ordine.return_value = 7
        ord_cls.return_value.get_ordine.return_value = {"id": 7, "numero": "ORD7"}

        out = ordini_service.crea_ordine_da_preventivo(99)

        # Delega solo-merce: nessuna pratica (standalone), nessun sottoinsieme.
        prev_cls.return_value.push_a_ordine.assert_called_once_with(
            99, righe_ids=None, pratica_id=None,
        )
        self.assertEqual(out["ordine_id"], 7)
        self.assertEqual(out["numero"], "ORD7")
        self.assertEqual(out["documento_origine"], {"tipo": "PREVENTIVO", "id": 99})

    @patch(_REPO)
    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_righe_selettive(self, prev_cls, ord_cls) -> None:
        # Smistamento selettivo: il sottoinsieme righe_ids arriva alla primitiva.
        prev_cls.return_value.push_a_ordine.return_value = 8
        ord_cls.return_value.get_ordine.return_value = {"id": 8, "numero": "ORD8"}

        ordini_service.crea_ordine_da_preventivo(99, righe_ids=[11, 12])

        prev_cls.return_value.push_a_ordine.assert_called_once_with(
            99, righe_ids=[11, 12], pratica_id=None,
        )

    @patch(_REPO)
    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_evade_senza_residui(self, prev_cls, ord_cls) -> None:
        # Gate EVASO bi-ramo (§5b brief smistamento): smistata l'ultima merce e
        # senza residuo servizi, il ramo ordine porta il preventivo a EVASO
        # (prima lo faceva solo il push commessa: solo-merce restava ACCETTATO).
        prev = prev_cls.return_value
        prev.push_a_ordine.return_value = 7
        prev.preventivo_ha_residuo_ordine.return_value = False
        prev.preventivo_ha_residuo_commessa.return_value = False
        ord_cls.return_value.get_ordine.return_value = {"id": 7, "numero": "ORD7"}

        ordini_service.crea_ordine_da_preventivo(99)

        prev.cambia_stato.assert_called_once_with(99, "EVASO", "django_api")

    @patch(_REPO)
    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_non_evade_con_residuo_commessa(self, prev_cls, ord_cls) -> None:
        # Preventivo misto smistato solo sul ramo merce: restano servizi da
        # pushare → niente EVASO, resta ACCETTATO.
        prev = prev_cls.return_value
        prev.push_a_ordine.return_value = 7
        prev.preventivo_ha_residuo_ordine.return_value = False
        prev.preventivo_ha_residuo_commessa.return_value = True
        ord_cls.return_value.get_ordine.return_value = {"id": 7, "numero": "ORD7"}

        ordini_service.crea_ordine_da_preventivo(99)

        prev.cambia_stato.assert_not_called()

    @patch(_REPO)
    @patch(_PREV_REPO)
    def test_crea_ordine_da_preventivo_evaso_db_error_non_solleva(self, prev_cls, ord_cls) -> None:
        # Robustezza al deploy parziale (stesso pattern di push_a_commessa):
        # se la fn DB rifiuta la transizione, l'ordine e' gia' creato → warning
        # loggato, la richiesta utente NON fallisce.
        from django.db import DatabaseError

        prev = prev_cls.return_value
        prev.push_a_ordine.return_value = 7
        prev.preventivo_ha_residuo_ordine.return_value = False
        prev.preventivo_ha_residuo_commessa.return_value = False
        prev.cambia_stato.side_effect = DatabaseError("transizione non ammessa")
        ord_cls.return_value.get_ordine.return_value = {"id": 7, "numero": "ORD7"}

        out = ordini_service.crea_ordine_da_preventivo(99)

        self.assertEqual(out["ordine_id"], 7)


class OrdiniConversioneOffertaTests(SimpleTestCase):
    """crea_ordine_da_offerta (§7.4): orchestrazione, override componenti, guard."""

    @patch(f"{_SVC}._copia_riga_offerta_espansa")
    @patch(f"{_SVC}._data_riferimento", return_value=date(2026, 6, 4))
    @patch(f"{_SVC}._resolve_emittente_sr_id", return_value=99)
    @patch(f"{_SVC}._get_testata_or_raise",
           return_value={"id": 7, "emittente_fiscale_id": 3})
    @patch(f"{_SVC}._crea_testata_ordine_da_origine", return_value=(7, "ORD7"))
    @patch(_REPO)
    @patch(_OFF_REPO)
    def test_crea_ordine_da_offerta_ok(
        self, off_cls, ord_cls, crea_testata, get_testata, resolve_em,
        data_rif, copia_riga,
    ) -> None:
        off_cls.return_value.get_offerta.return_value = {
            "stato_codice_interno": "ACCETTATA",
            "billing_account_id": 10, "utility_id": 5,
            "emittente_fiscale_id": 3, "valuta_id": 1,
        }
        off_cls.return_value.list_righe_espanse.return_value = [
            {"articolo_id": "A1"}, {"articolo_id": "A2"},
        ]
        # Guard idempotenza 1:1: nessun ordine già nato da questa offerta.
        ord_cls.return_value.get_ordine_by_documento_origine.return_value = None

        with patch(_ATOMIC, return_value=nullcontext()):
            out = ordini_service.crea_ordine_da_offerta(55)

        self.assertEqual(out["ordine_id"], 7)
        self.assertEqual(out["numero"], "ORD7")
        self.assertEqual(out["righe_create"], 2)
        self.assertEqual(out["documento_origine"], {"tipo": "OFFERTA", "id": 55})
        # testata creata via helper condiviso con tipo/origine corretti
        header, tipo, origine_id = crea_testata.call_args.args
        self.assertEqual(tipo, "OFFERTA")
        self.assertEqual(origine_id, 55)
        self.assertEqual(header["billing_account_id"], 10)
        # offerta non ha termine/modalita pagamento → non nel header
        self.assertNotIn("termine_pagamento_id", header)
        # una copia riga per riga espansa
        self.assertEqual(copia_riga.call_count, 2)

    @patch(_OFF_REPO)
    def test_crea_ordine_da_offerta_stato_non_convertibile(self, off_cls) -> None:
        off_cls.return_value.get_offerta.return_value = {
            "stato_codice_interno": "EMESSA",
        }
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_offerta(55)
        self.assertEqual(cm.exception.code, "E_ORD_ORIGINE_NON_CONVERTIBILE")

    @patch(_OFF_REPO)
    def test_crea_ordine_da_offerta_non_trovata(self, off_cls) -> None:
        off_cls.return_value.get_offerta.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_offerta(55)
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")

    @patch(_REPO)
    @patch(_OFF_REPO)
    def test_crea_ordine_da_offerta_gia_convertita(self, off_cls, ord_cls) -> None:
        # Offerta ACCETTATA ma esiste già un ordine da questa offerta → guard
        # fail-fast 1:1 (univocità offerta→ordine), prima di espandere le righe.
        off_cls.return_value.get_offerta.return_value = {
            "stato_codice_interno": "ACCETTATA",
            "billing_account_id": 10, "utility_id": 5,
            "emittente_fiscale_id": 3, "valuta_id": 1,
        }
        ord_cls.return_value.get_ordine_by_documento_origine.return_value = {
            "id": 7, "numero": "ORD7",
        }
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_offerta(55)
        self.assertEqual(cm.exception.code, "E_ORD_OFFERTA_GIA_CONVERTITA")
        # Guard prima del lavoro: nessuna espansione righe.
        off_cls.return_value.list_righe_espanse.assert_not_called()

    @patch(_REPO)
    @patch(_OFF_REPO)
    def test_crea_ordine_da_offerta_con_contratto_bloccato(
        self, off_cls, ord_cls,
    ) -> None:
        # Mutua esclusività XOR: offerta ACCETTATA che ha già generato un
        # contratto non può generare un ordine → E_OFFERTA_CONTRATTO_GIA_GENERATO.
        off_cls.return_value.get_offerta.return_value = {
            "stato_codice_interno": "ACCETTATA",
            "billing_account_id": 10, "utility_id": 5,
            "emittente_fiscale_id": 3, "valuta_id": 1,
            "contratto_id": 42,
        }
        # Nessun ordine ancora: il blocco arriva dal contratto, non dall'idempotenza.
        ord_cls.return_value.get_ordine_by_documento_origine.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_offerta(55)
        self.assertEqual(cm.exception.code, "E_OFFERTA_CONTRATTO_GIA_GENERATO")
        off_cls.return_value.list_righe_espanse.assert_not_called()

    def test_overrides_da_componenti_coercion(self) -> None:
        from apps.vendite.services.ordini_service import _overrides_da_componenti
        # lista di dict (jsonb già parsato da psycopg)
        self.assertEqual(
            _overrides_da_componenti(
                [{"componente_id": "u1", "prezzo": "5"},
                 {"componente_id": "u2", "prezzo": "3"}],
            ),
            {"u1": "5", "u2": "3"},
        )
        # stringa jsonb (psycopg non parsato) → coerce
        self.assertEqual(
            _overrides_da_componenti('[{"componente_id": "u1", "prezzo": "5"}]'),
            {"u1": "5"},
        )
        # None / json invalido / non-lista → {}
        self.assertEqual(_overrides_da_componenti(None), {})
        self.assertEqual(_overrides_da_componenti("non-json-{"), {})
        # entry senza id o senza prezzo → saltate
        self.assertEqual(
            _overrides_da_componenti(
                [{"componente_id": "u1"}, {"prezzo": "5"}],
            ),
            {},
        )
        # prezzo 0 escluso (la fn DB rifiuta override 0 → ricade sul resolver);
        # prezzo non numerico escluso
        self.assertEqual(
            _overrides_da_componenti(
                [{"componente_id": "u1", "prezzo": "0"},
                 {"componente_id": "u2", "prezzo": "0.00"},
                 {"componente_id": "u3", "prezzo": "xx"},
                 {"componente_id": "u4", "prezzo": "7"}],
            ),
            {"u4": "7"},
        )


class OrdiniPushCommessaTests(SimpleTestCase):
    """push_a_commessa: transizione automatica CONFERMATO→EVASO (invio unico)."""

    _PUSH_ONE = "apps.vendite.services.commesse_service.pr_run_commesse_push_one"

    @patch(_COMPLETA_STEP)
    @patch(_PUSH_ONE)
    @patch(_REPO)
    def test_push_completato_transita_a_evaso(self, ord_cls, mock_push_one, _mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        repo.get_stato_id_by_codice.return_value = 8  # id EVASO
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }
        out = ordini_service.push_a_commessa(55)
        self.assertEqual(out["stato"], "COMPLETATO")
        repo.get_stato_id_by_codice.assert_called_once_with("EVASO")
        repo.update_stato.assert_called_once_with(55, 8)

    @patch(_PUSH_ONE)
    @patch(_REPO)
    def test_push_parziale_non_transita(self, ord_cls, mock_push_one) -> None:
        # PARZIALE → ordine resta CONFERMATO (ri-push per completare): no EVASO.
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        mock_push_one.return_value = {
            "stato": "PARZIALE", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }
        ordini_service.push_a_commessa(55)
        repo.update_stato.assert_not_called()

    @patch(_COMPLETA_STEP)
    @patch(_PUSH_ONE)
    @patch(_REPO)
    def test_push_seed_evaso_assente_soft(self, ord_cls, mock_push_one, _mock_step) -> None:
        # Robustezza deploy parziale: EVASO non seedato → niente raise, niente update.
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        repo.get_stato_id_by_codice.return_value = None
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }
        out = ordini_service.push_a_commessa(55)  # non solleva
        self.assertEqual(out["stato"], "COMPLETATO")
        repo.update_stato.assert_not_called()

    @patch(_COMPLETA_STEP)
    @patch(_PUSH_ONE)
    @patch(_REPO)
    def test_push_transizione_db_error_soft(self, ord_cls, mock_push_one, _mock_step) -> None:
        # Se il trigger DB rifiuta la transizione → warning, non fa fallire il push.
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        repo.get_stato_id_by_codice.return_value = 8
        repo.update_stato.side_effect = DatabaseError("transizione non ammessa")
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }
        out = ordini_service.push_a_commessa(55)  # non solleva
        self.assertEqual(out["stato"], "COMPLETATO")


class OrdiniStepPraticaTests(SimpleTestCase):
    """Auto-completamento step pratica CONFERMA_ORDINE/INVIO_COMMESSA all'azione
    standalone del programma base (conferma / push a commessa) — bivio rev.3."""

    def setUp(self) -> None:
        _patch_atomic_noop(self)

    # L'auto-completamento delega al BB motore completa_step_pratica (mockato qui,
    # testato in pratiche): questi test verificano il CABLAGGIO — risoluzione
    # pratica dall'ordine + template_codice + esito corretti + gating.
    _PRAT_REPO = "apps.pratiche.db.pratiche_repository.PraticheRepository"
    _STEP = "apps.pratiche.services.pratiche_service.completa_step_pratica"
    _PUSH_ONE = "apps.vendite.services.commesse_service.pr_run_commesse_push_one"

    # Scopo: conferma ordine collegato a pratica → completa CONFERMA_ORDINE POSITIVO.
    @patch(_STEP)
    @patch(_PRAT_REPO)
    @patch(_REPO)
    def test_conferma_completa_step_conferma_ordine(self, ord_cls, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = [{"id": 1}]
        repo.get_stato_id_by_codice.return_value = 2
        MockPrat.return_value.get_pratica_id_by_sorgente.return_value = 290

        ordini_service.conferma(7, user="op")

        mock_step.assert_called_once_with(
            290, template_codice="CONFERMA_ORDINE", esito="POSITIVO", user="op",
        )

    # Scopo: ordine non in pratica → no-op (BB non chiamato).
    @patch(_STEP)
    @patch(_PRAT_REPO)
    @patch(_REPO)
    def test_conferma_senza_pratica_noop(self, ord_cls, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.list_righe.return_value = [{"id": 1}]
        repo.get_stato_id_by_codice.return_value = 2
        MockPrat.return_value.get_pratica_id_by_sorgente.return_value = None

        ordini_service.conferma(7)

        mock_step.assert_not_called()

    # Scopo: push a commessa (COMPLETATO) di ordine in pratica → completa
    # INVIO_COMMESSA POSITIVO (step terminale → sblocca la chiusura pratica).
    @patch(_STEP)
    @patch(_PRAT_REPO)
    @patch(_PUSH_ONE)
    @patch(_REPO)
    def test_push_completa_step_invio_commessa(self, ord_cls, mock_push_one, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        repo.get_stato_id_by_codice.return_value = 8
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }
        MockPrat.return_value.get_pratica_id_by_sorgente.return_value = 290

        ordini_service.push_a_commessa(55, user="op")

        mock_step.assert_called_once_with(
            290, template_codice="INVIO_COMMESSA", esito="POSITIVO", user="op",
        )

    # Scopo: push PARZIALE → non completa lo step (gated su COMPLETATO).
    @patch(_STEP)
    @patch(_PRAT_REPO)
    @patch(_PUSH_ONE)
    @patch(_REPO)
    def test_push_parziale_non_completa_step(self, ord_cls, mock_push_one, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        mock_push_one.return_value = {
            "stato": "PARZIALE", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }

        ordini_service.push_a_commessa(55)

        mock_step.assert_not_called()
