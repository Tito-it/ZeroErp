# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test ordini_service (mock repository, no DB). Valida i guard di
#        stato/not-found, il cliente (BA) obbligatorio con le sue copie lasciate
#        al DB (brief-db-esecutivi-ba-coppia, 2026-10-10), e la
#        traduzione errori DB di _db_errors (IntegrityError -> codice vincolo;
#        DatabaseError trigger -> estrazione codice E_*).
# ------------------------------------------------------------

from contextlib import nullcontext
from datetime import date
from unittest.mock import MagicMock, patch

from django.db import DatabaseError, IntegrityError
from django.test import SimpleTestCase

from apps.core.tests._helpers.modello_documento_mockato import ModelloDocumentoMockatoMixin
from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.vendite.services import ordini_service
from apps.vendite.services.ordini_service import _db_errors

_REPO = "apps.vendite.services.ordini_service.OrdiniRepository"
# Helper auto-completamento step pratica (CONFERMA_ORDINE/INVIO_COMMESSA): usa
# PraticheRepository reale → patchato a no-op nei test di transizione stato ordine
# (SimpleTestCase, DB vietato). L'auto-completamento e' testato a parte.
_COMPLETA_STEP = "apps.vendite.services.ordini_service._completa_flusso_ordine_pratica"


def _patch_atomic_noop(testcase) -> None:
    # conferma avvolge il verbo + completamento step in transaction.atomic:
    # no-op in SimpleTestCase (no connessione DB), come test_preventivi_service.
    patcher = patch("apps.vendite.services.ordini_service.transaction.atomic")
    mock_atomic = patcher.start()
    mock_atomic.return_value.__enter__ = MagicMock(return_value=None)
    mock_atomic.return_value.__exit__ = MagicMock(return_value=False)
    testcase.addCleanup(patcher.stop)


class OrdiniServiceGuardsTests(ModelloDocumentoMockatoMixin, SimpleTestCase):
    """Guard di stato e not-found (mock repository)."""

    def setUp(self) -> None:
        super().setUp()
        _patch_atomic_noop(self)

    @patch(_REPO, autospec=True)
    def test_get_ordine_not_found(self, repo_cls) -> None:
        repo_cls.return_value.get_ordine.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.get_ordine(99)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")

    # Ordine gia' CONFERMATO: la seconda conferma la rifiuta il verbo, dalla
    # prima riga (brief-modello-documento-vendita §9.10); il service non la
    # pre-valida e non chiude lo step.
    @patch(_COMPLETA_STEP)
    @patch(_REPO, autospec=True)
    def test_conferma_due_volte_dal_verbo(self, repo_cls, mock_step) -> None:
        repo = repo_cls.return_value
        self.emissione_del_documento("CONFERMATO")
        repo.cambia_stato.side_effect = DatabaseError(
            "E_DOC_GIA_NELLO_STATO: Il documento è già nello stato CONFERMATO",
        )
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(7)
        self.assertEqual(cm.exception.code, "E_DOC_GIA_NELLO_STATO")
        repo.get_stato_codice.assert_not_called()
        mock_step.assert_not_called()

    # La conferma e' lo stato di emissione letto dal vocabolario, scritto dal
    # verbo (§9.6 C-1, C-2): nessun letterale, nessun UPDATE, e le righe le
    # conta il guard del DB (E_ORDINE_CONFERMA_SENZA_RIGHE), non il service.
    @patch(_COMPLETA_STEP)
    @patch(_REPO, autospec=True)
    def test_conferma_dal_verbo_con_lo_stato_di_emissione(self, repo_cls, _mock_step) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        self.emissione_del_documento("CONFERMATO")
        # Lo stato precedente lo dice il verbo.
        repo.cambia_stato.return_value = {
            "ordine_id": 7, "stato_precedente": "DRAFT", "stato_nuovo": "CONFERMATO",
        }
        out = ordini_service.conferma(7)
        self.assertEqual(out, {"ordine_id": 7, "stato_precedente": "DRAFT", "stato": "CONFERMATO"})
        self.modello_documento.stato_di_emissione.assert_called_once_with("vendite.ordini")
        repo.cambia_stato.assert_called_once_with(7, "CONFERMATO")
        repo.count_righe.assert_not_called()

    # Il rifiuto delle righe arriva dal guard del DB, tradotto col suo codice.
    @patch(_COMPLETA_STEP)
    @patch(_REPO, autospec=True)
    def test_conferma_senza_righe_dal_guard(self, repo_cls, mock_step) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        self.emissione_del_documento("CONFERMATO")
        repo.cambia_stato.side_effect = DatabaseError(
            "E_ORDINE_CONFERMA_SENZA_RIGHE: ordine senza righe attive",
        )
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(7)
        self.assertEqual(cm.exception.code, "E_ORDINE_CONFERMA_SENZA_RIGHE")
        mock_step.assert_not_called()

    # Un vocabolario senza stato di emissione e' un errore di cablaggio.
    @patch(_REPO, autospec=True)
    def test_conferma_senza_stato_di_emissione(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(7)
        self.assertEqual(cm.exception.code, "E_CONFIG_MANCANTE")
        repo.cambia_stato.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_ordine_lascia_le_copie_al_db(self, repo_cls) -> None:
        # Ruolo e utility sono copie del BA: li scrive `trgfn_ordini_normalize`
        # (BB `fn_cliente_dal_billing_account`), il service non li deriva ne'
        # li inoltra (brief-db-esecutivi-ba-coppia §10.2 domanda 2).
        repo = repo_cls.return_value
        repo.create_ordine.return_value = {"id": 7, "uid": "u", "numero": "ORD0007"}
        out = ordini_service.crea_ordine({"billing_account_id": 3})
        self.assertEqual(out["numero"], "ORD0007")
        kwargs = repo.create_ordine.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 3)
        self.assertNotIn("soggetto_ruolo_id", kwargs)
        self.assertNotIn("utility_id", kwargs)
        # Lo stato non si passa: lo mette il DB, lo stato iniziale del
        # vocabolario (brief-modello-documento-vendita P-2).
        self.assertNotIn("stato_doc_ordine_id", kwargs)
        # ⛔ E chi le manda riceve un 400, non uno scarto silenzioso (2026-10-20).
        for copia in ({"utility_id": 1}, {"soggetto_ruolo_id": 555}):
            with self.subTest(copia=copia), self.assertRaises(ServiceError) as cm:
                ordini_service.crea_ordine({"billing_account_id": 3, **copia})
            self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")

    @patch(_REPO, autospec=True)
    def test_crea_ordine_senza_cliente_errore(self, repo_cls) -> None:
        # D-1: l'ordine ha sempre il BA. Validazione del payload col campo.
        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine({})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "billing_account_id")
        repo_cls.return_value.create_ordine.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_aggiorna_ordine_ba_arriva_al_db(self, repo_cls) -> None:
        # Il cliente immutabile lo dice il DB (lock di colonna,
        # E_ORD_CLIENTE_IMMUTABILE): il service non ricopia il lock e passa
        # il BA, invariato o no. Fino al 2026-10-10 qui c'era la copia Python.
        repo = repo_cls.return_value
        ordini_service.aggiorna_ordine(7, {"billing_account_id": 99})
        self.assertEqual(repo.update_ordine.call_args.kwargs, {"billing_account_id": 99})

    @patch(_REPO, autospec=True)
    def test_aggiorna_ordine_utility_scartata(self, repo_cls) -> None:
        # La utility e' una copia del BA, che sull'ordine non cambia: fuori
        # whitelist. ⛔ Dal 2026-10-20 e' un 400, non uno scarto silenzioso.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_ordine(7, {"billing_account_id": 3, "utility_id": 9})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        repo.update_ordine.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_aggiorna_ordine_ba_non_numerico_rifiutato(self, repo_cls) -> None:
        # Input malformato: billing_account_id non numerico -> 400 parlante
        # (E_ORD_VALIDAZIONE) col campo, non 500 dal driver.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_ordine(7, {"billing_account_id": "abc"})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "billing_account_id")
        repo.update_ordine.assert_not_called()

    @patch("apps.vendite.services.ordini_service.contatori_documento", return_value={"note": 2})
    @patch(_REPO, autospec=True)
    def test_get_ordine_capabilities_annidate(self, repo_cls, contatori) -> None:
        # get_ordine trasporta le capability di fn_available_actions_ordine
        # (available_actions, can_edit_*, ...) SOTTO `capabilities`, senza
        # fonderle nella testata (api.md §«Il blob sta SOTTO `capabilities`»).
        # `can_conferma` non e' piu' un flag.
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        repo.count_righe.return_value = 1
        repo.get_capabilities.return_value = {
            "available_actions": [{"key": "conferma", "target_state": "CONFERMATO"}],
            "can_edit_testata": True,
            "can_push_commessa": False,
            "stato_codice": "DRAFT",
        }
        out = ordini_service.get_ordine(7)
        caps = out["capabilities"]
        self.assertEqual(caps, repo.get_capabilities.return_value)
        self.assertEqual(caps["available_actions"][0]["key"], "conferma")
        self.assertEqual(out["righe_count"], 1)
        # I badge del drawer (pulsante «Gestisci note»), dal BB dei contatori.
        self.assertEqual(out["contatori"], {"note": 2})
        self.assertEqual(contatori.call_args.args[1], 7)
        for chiave in caps:
            self.assertNotIn(chiave, out)
        self.assertNotIn("can_conferma", caps)

    @patch(_REPO, autospec=True)
    def test_cambia_stato_ok(self, repo_cls) -> None:
        # Transizione generica: delega al verbo DB.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "CONFERMATO"
        out = ordini_service.cambia_stato(7, "EVASO")
        self.assertEqual(out["stato"], "EVASO")
        self.assertEqual(out["stato_precedente"], "CONFERMATO")
        # Dal verbo, col codice (§9.6 C-3): passaggio di processo e matrice li
        # rifiuta il DB.
        repo.cambia_stato.assert_called_once_with(7, "EVASO")
        repo.annulla.assert_not_called()

    # M-2 (brief-modello-documento-vendita §8.7 punto 4, revoca l'opzione (i)
    # del 2026-06-05): lo stato di emissione, letto dal vocabolario, dal cambio
    # stato generico e' un 400 col campo; l'ordine si emette da «Emetti».
    @patch(_REPO, autospec=True)
    def test_cambia_stato_rifiuta_lo_stato_di_emissione(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        self.stato_chiesto_di_emissione()
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_stato(7, "CONFERMATO")
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "stato_codice")
        self.modello_documento.e_stato_di_emissione.assert_called_once_with(
            "vendite.ordini", "CONFERMATO",
        )
        repo.cambia_stato.assert_not_called()

    # brief-db-annullo-documento-con-legami: ANNULLATO passa SEMPRE dal verbo,
    # con la dichiarazione della conferma (assente al primo tentativo).
    @patch(_REPO, autospec=True)
    def test_annullo_passa_dal_verbo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        out = ordini_service.cambia_stato(7, "ANNULLATO")
        repo.annulla.assert_called_once_with(7, None)
        repo.cambia_stato.assert_not_called()
        self.assertEqual(out["stato"], "ANNULLATO")
        ordini_service.cambia_stato(7, "ANNULLATO", legami_confermati="3")
        repo.annulla.assert_called_with(7, 3)

    @patch(_REPO, autospec=True)
    def test_annullo_dichiarazione_non_numerica(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_stato(7, "ANNULLATO", legami_confermati="tre")
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "legami_confermati")
        repo.annulla.assert_not_called()

    @patch("apps.vendite.services.ordini_service.legami_del_documento", return_value={"legami": 0})
    @patch(_REPO, autospec=True)
    def test_get_legami_dopo_la_testata(self, repo_cls, bb) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.get_legami(99)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")
        bb.assert_not_called()
        repo.get_stato_codice.return_value = "CONFERMATO"
        ordini_service.get_legami(7)
        bb.assert_called_once_with("ORDINE_VENDITA", 7)

    # Uno stato che il vocabolario non ha lo rifiuta il verbo, col suo codice:
    # il service non ne ha piu' una copia (brief-modello-documento-vendita §9.9).
    @patch(_REPO, autospec=True)
    def test_cambia_stato_codice_inesistente(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.cambia_stato.side_effect = DatabaseError(
            "E_STATO_WORKFLOW_NON_TROVATO: INESISTENTE",
        )
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_stato(7, "INESISTENTE")
        self.assertEqual(cm.exception.code, "E_STATO_WORKFLOW_NON_TROVATO")
        repo.annulla.assert_not_called()

    # L'ordine che non c'e' (o fuori perimetro) lo rifiuta il verbo, col suo
    # codice (regola del 1, 2026-10-27): nessuna lettura della testata prima.
    @patch(_REPO, autospec=True)
    def test_cambia_stato_ordine_inesistente_dal_verbo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = None
        repo.cambia_stato.side_effect = DatabaseError("E_ORD_NOT_FOUND: ordine 99")
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_stato(99, "EVASO")
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")
        repo.get_ordine.assert_not_called()

    # Un numero nel JSON al posto del codice e' un 400 (stato mancante), non un
    # 500 da `.strip()` su un int (2026-10-09, trovato da mypy).
    @patch(_REPO, autospec=True)
    def test_cambia_stato_codice_non_testo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_stato(7, 5)  # type: ignore[arg-type]
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        repo.cambia_stato.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_elimina_ordine_con_righe_rifiutato(self, repo_cls) -> None:
        # Niente hard-delete di dati reali (allineato a preventivi): un ordine
        # in bozza CON righe non si cancella, si annulla.
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.count_righe.return_value = 1
        with self.assertRaises(ServiceError) as cm:
            ordini_service.elimina_ordine(7)
        self.assertEqual(cm.exception.code, "E_ORD_STATO_TRANSIZIONE")
        repo.delete_ordine.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_elimina_ordine_bozza_orfana_ok(self, repo_cls) -> None:
        # Bozza orfana (DRAFT, zero righe): hard-delete ammesso (cleanup
        # abbandono auto-save).
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.count_righe.return_value = 0
        repo.delete_ordine.return_value = True
        out = ordini_service.elimina_ordine(7)
        self.assertTrue(out["deleted"])
        repo.delete_ordine.assert_called_once_with(7)

    # ⭐ «Solo in bozza» lo dice il vocabolario (`e_stato_iniziale`), non un
    #    insieme di codici nel service: uno stato non iniziale si rifiuta
    #    prima di contare le righe.
    @patch(_REPO, autospec=True)
    def test_elimina_ordine_fuori_bozza_rifiutato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "CONFERMATO"
        with self.assertRaises(ServiceError) as cm:
            ordini_service.elimina_ordine(7)
        self.assertEqual(cm.exception.code, "E_ORD_STATO_TRANSIZIONE")
        repo.count_righe.assert_not_called()
        repo.delete_ordine.assert_not_called()


_SVC = "apps.vendite.services.ordini_service"


class OrdiniRigaComponentiOverrideTests(SimpleTestCase):
    """gestisci_riga: override prezzi componenti BoM pre-save (dialog).

    Simmetria con preventivi: gate autorizzazione + override normalizzati
    passati a init_componenti_riga per articolo composito.
    """

    # ⚠️ `_risolvi_iva_riga` mockato per la stessa ragione del repository:
    #    dal 2026-08-31 `gestisci_riga` interroga il risolutore IVA, e senza
    #    mock questi test — che parlano di componenti BoM — aprirebbero una
    #    connessione vera e in CI fallirebbero per un motivo che non c'entra.
    @patch(f"{_SVC}._risolvi_iva_riga", return_value=(None, {}))
    @patch(f"{_SVC}._data_riferimento", return_value=date(2026, 6, 5))
    @patch(f"{_SVC}._resolve_emittente_sr_id", return_value=99)
    @patch(f"{_SVC}.validate_componenti_overrides_authorization")
    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_gestisci_riga_composito_passa_overrides(
        self, repo_cls, mock_tx, mock_gate, _sr, _dr, _iva,
    ) -> None:
        mock_tx.atomic.return_value = nullcontext()
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        repo.is_articolo_composito.return_value = True
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 50}

        payload = {
            "articolo_id": "ART1", "qta_operativa": 2,
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

    # ⚠️ `_risolvi_iva_riga` mockato per la stessa ragione del repository:
    #    dal 2026-08-31 `gestisci_riga` interroga il risolutore IVA, e senza
    #    mock questi test — che parlano di componenti BoM — aprirebbero una
    #    connessione vera e in CI fallirebbero per un motivo che non c'entra.
    @patch(f"{_SVC}._risolvi_iva_riga", return_value=(None, {}))
    @patch(f"{_SVC}._data_riferimento", return_value=date(2026, 6, 5))
    @patch(f"{_SVC}._resolve_emittente_sr_id", return_value=99)
    @patch(f"{_SVC}.validate_componenti_overrides_authorization")
    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_gestisci_riga_composito_senza_overrides(
        self, repo_cls, mock_tx, mock_gate, _sr, _dr, _iva,
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
            7, {"articolo_id": "ART1", "qta_operativa": 1,
                "uom_operativa_id": 3},
            auth_user_id=42,
        )
        _, kwargs = repo.init_componenti_riga.call_args
        self.assertIsNone(kwargs["componenti_overrides"])


    # Scopo: ⛔ `I6` — LA CASELLA E' CHIUSA. Un client che manda ancora `iva_id`
    #        nel payload riceve un 400 (dal 2026-10-20; prima la chiave era
    #        SCARTATA in silenzio): a decidere e' il risolutore.
    # ⛔ E il risolutore va interrogato con `payload_iva_id=None`: passargli il
    #        valore del client lo farebbe scendere sul ramo di AUDIT, dove gli
    #        errori sono best-effort — cioe' una riga si salverebbe anche
    #        quando l'IVA non e' determinabile.
    @patch(f"{_SVC}._risolvi_iva_riga", return_value=(9, {"iva_origine": "TITOLO"}))
    @patch(f"{_SVC}._data_riferimento", return_value=date(2026, 6, 5))
    @patch(f"{_SVC}._resolve_emittente_sr_id", return_value=99)
    @patch(f"{_SVC}.validate_componenti_overrides_authorization")
    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_i6_iva_del_payload_ignorata(
        self, repo_cls, mock_tx, mock_gate, _sr, _dr, iva,
    ) -> None:
        mock_tx.atomic.return_value = nullcontext()
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        # ⚠️ Composito come i due casi vicini: sulla riga semplice il pricing
        #    pretende il billing account in testata, e qui non si sta provando
        #    il prezzo — si sta provando che l'IVA del payload non arriva.
        repo.is_articolo_composito.return_value = True
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 52}

        # ⛔ Dal 2026-10-20 `iva_id` nel payload e' un 400 (chiave fuori
        #    contratto), non piu' uno scarto: la riga non nasce.
        with self.assertRaises(ServiceError) as cm:
            ordini_service.gestisci_riga(
                7, {"articolo_id": "ART1", "qta_operativa": 1, "uom_operativa_id": 3,
                    "iva_id": 999},
                auth_user_id=42,
            )
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        repo.create_riga.assert_not_called()

        # ⭐ Senza la chiave decide il risolutore, interrogato con
        #    `payload_iva_id=None`.
        ordini_service.gestisci_riga(
            7, {"articolo_id": "ART1", "qta_operativa": 1, "uom_operativa_id": 3},
            auth_user_id=42,
        )
        self.assertIsNone(iva.call_args.kwargs["payload_iva_id"])
        self.assertNotIn("iva_id", ordini_service.CREATE_KEYS_RIGA)
        self.assertNotIn("iva_id", ordini_service.UPDATE_KEYS_RIGA)
        self.assertEqual(repo.create_riga.call_args.kwargs["iva_id"], 9)


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

    # Scopo: il CHECK di dominio sul trigger di fatturazione produce un
    #        messaggio PARLANTE, non il fallback generico. Diventa raggiungibile
    #        con i changeSet del 2026-08-17 (prima `trgfn_ordini_normalize`
    #        sovrascriveva il valore prima che il CHECK guardasse, quindi la
    #        colonna accettava qualunque stringa): senza la mappatura, dall'apply
    #        in poi il FE riceverebbe «Violazione vincolo DB su ordine» senza
    #        sapere quale campo né quali valori sono ammessi.
    def test_integrity_error_check_trigger_mappato(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError(
                    'new row for relation "ordini" violates check constraint '
                    '"chk_ordini_fatturazione_trigger"',
                )
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("CONFERMATO", cm.exception.message)
        self.assertIn("SPEDITO", cm.exception.message)

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
    primitiva DB + ritorno numero. Stato/righe sono validati dalla fn DB.
    Fix analisi-fix-transazioni #10: la transizione EVASO vive ora DENTRO
    vendite.fn_push_preventivo_a_ordine (atomica con la creazione ordine), non
    piu' come chiamata BE separata → il gate/atomicita' EVASO e' coperto dal
    pgTAP DB, non piu' mockabile qui."""

    def setUp(self) -> None:
        # transaction.atomic() a no-op (SimpleTestCase senza DB): il verbo e il
        # riempimento dello slot di default stanno in una transazione.
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_REPO, autospec=True)
    @patch(_PREV_REPO, autospec=True)
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
        # Dopo la cascata dal preventivo, lo slot di default sull'ordine nato
        # (il DB lo riempie solo se e' rimasto vuoto): R-BE-1.
        ord_cls.return_value.riempi_indirizzo_default.assert_called_once_with(7)

    @patch(_REPO, autospec=True)
    @patch(_PREV_REPO, autospec=True)
    def test_crea_ordine_da_preventivo_righe_selettive(self, prev_cls, ord_cls) -> None:
        # Smistamento selettivo: il sottoinsieme righe_ids arriva alla primitiva.
        prev_cls.return_value.push_a_ordine.return_value = 8
        ord_cls.return_value.get_ordine.return_value = {"id": 8, "numero": "ORD8"}

        ordini_service.crea_ordine_da_preventivo(99, righe_ids=[11, 12])

        prev_cls.return_value.push_a_ordine.assert_called_once_with(
            99, righe_ids=[11, 12], pratica_id=None,
        )

    # Scopo: i guard della fn DB (stato non ammesso, nessuna riga merce)
    #        arrivano al client col loro codice, non come 500 grezzo; e la
    #        catena si ferma prima dello slot di default.
    @patch(_REPO, autospec=True)
    @patch(_PREV_REPO, autospec=True)
    def test_crea_ordine_da_preventivo_errore_db_tradotto(self, prev_cls, ord_cls) -> None:
        prev_cls.return_value.push_a_ordine.side_effect = DatabaseError(
            "E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO: preventivo in BOZZA",
        )

        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_preventivo(99)

        self.assertEqual(cm.exception.code, "E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO")
        ord_cls.return_value.riempi_indirizzo_default.assert_not_called()

    # Scopo: un errore del building block dello slot di default sale tradotto
    #        (non e' best-effort: annulla anche l'ordine, nella transazione).
    @patch(_REPO, autospec=True)
    @patch(_PREV_REPO, autospec=True)
    def test_crea_ordine_da_preventivo_errore_default_tradotto(self, prev_cls, ord_cls) -> None:
        prev_cls.return_value.push_a_ordine.return_value = 7
        ord_cls.return_value.riempi_indirizzo_default.side_effect = DatabaseError(
            "E_INDIRIZZO_DOC_NON_DEL_CLIENTE: indirizzo d'altri",
        )

        with self.assertRaises(ServiceError) as cm:
            ordini_service.crea_ordine_da_preventivo(99)

        self.assertEqual(cm.exception.code, "E_INDIRIZZO_DOC_NON_DEL_CLIENTE")

    # Nota: i test che verificavano la transizione EVASO lato BE
    # (test_..._evade_senza_residui / _non_evade_con_residuo_commessa /
    # _evaso_db_error_non_solleva) sono stati rimossi col fix #10: la transizione
    # e il suo gate bi-ramo vivono ora DENTRO fn_push_preventivo_a_ordine e non
    # sono piu' osservabili via mock del repo. La correttezza (evade a residuo
    # nullo, non evade con residuo, atomicita' su errore) e' coperta dal pgTAP
    # db/pgtap/vendite/test-fn-push-preventivo-a-ordine-v1.sql.


class OrdiniConversioneOffertaTests(SimpleTestCase):
    """crea_ordine_da_offerta: delega al verbo DB `fn_genera_ordine_da_offerta`.

    ⛔ Dal 2026-10-21 (brief-db-offerta-emissione-ed-erogazione I-D2) stato,
    documenti vivi, testata, provenienza e righe sono del verbo: qui non si
    prova nessuna di quelle regole (le prova il pgTAP
    `test-righe-ammesse-ai-passi-e-annullo-v1`, e la giuntura
    `tests/db/test_genera_ordine_da_offerta_db.py`). Si prova che il service
    deleghi senza leggere l'offerta da se', e che i rifiuti arrivino col loro
    codice.
    """

    def setUp(self) -> None:
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_REPO, autospec=True)
    @patch(_OFF_REPO, autospec=True)
    def test_crea_ordine_da_offerta_delega_al_verbo(self, off_cls, ord_cls) -> None:
        off_cls.return_value.genera_ordine.return_value = 7
        ord_cls.return_value.get_ordine.return_value = {"id": 7, "numero": "ORD7"}

        out = ordini_service.crea_ordine_da_offerta(55)

        off_cls.return_value.genera_ordine.assert_called_once_with(55)
        self.assertEqual(out, {
            "ordine_id": 7,
            "numero": "ORD7",
            "documento_origine": {"tipo": "OFFERTA_COMMERCIALE", "id": 55},
        })
        # Nessuno specchio: l'offerta non si legge, l'ordine non si scrive qui.
        off_cls.return_value.get_offerta.assert_not_called()
        ord_cls.return_value.create_ordine.assert_not_called()
        ord_cls.return_value.riempi_indirizzo_default.assert_not_called()

    @patch(_REPO, autospec=True)
    @patch(_OFF_REPO, autospec=True)
    def test_crea_ordine_da_offerta_rifiuto_col_codice_del_verbo(self, off_cls, ord_cls) -> None:
        for codice in (
            "E_OFFERTA_NON_TROVATA",
            "E_ORD_ORIGINE_NON_CONVERTIBILE",
            "E_ORD_OFFERTA_GIA_CONVERTITA",
            "E_OFFERTA_CONTRATTO_GIA_GENERATO",
            "E_DOC_RIGA_NON_AMMESSA",
        ):
            with self.subTest(codice):
                off_cls.return_value.genera_ordine.side_effect = DatabaseError(
                    f"{codice}: rifiuto del verbo",
                )
                with self.assertRaises(ServiceError) as cm:
                    ordini_service.crea_ordine_da_offerta(55)
                self.assertEqual(cm.exception.code, codice)
        ord_cls.return_value.get_ordine.assert_not_called()


class OrdiniPushCommessaTests(SimpleTestCase):
    """push_a_commessa: l'invio in commessa NON cambia lo stato dell'ordine
    (D-6 di brief-db-annullo-a-valle-riapre-a-monte, 2026-10-12: «Evaso» = la
    merce e' partita, lo dicono solo le bolle). Fino a quel giorno qui c'era la
    transizione CONFERMATO→EVASO «best-effort» su un savepoint: un ordine
    PARZIALMENTE_EVASO mandato in commessa diventava EVASO con meta' merce in
    magazzino. Push + chiusura step pratica restano in un transaction.atomic()
    (fix analisi-fix-transazioni #4), qui mockato a no-op."""

    _PUSH_ONE = "apps.vendite.services.commesse_service.pr_run_commesse_push_one"

    def setUp(self) -> None:
        # transaction.atomic() a no-op per i test mock-only. Lo stesso
        # nullcontext e' riusabile su piu' `with` (stateless).
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_COMPLETA_STEP)
    @patch(_PUSH_ONE)
    @patch(_REPO, autospec=True)
    def test_push_completato_non_cambia_stato(self, ord_cls, mock_push_one, _mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }
        out = ordini_service.push_a_commessa(55)
        self.assertEqual(out["stato"], "COMPLETATO")
        repo.cambia_stato.assert_not_called()

    @patch(_COMPLETA_STEP)
    @patch(_PUSH_ONE)
    @patch(_REPO, autospec=True)
    def test_push_da_parzialmente_evaso_resta_tale(self, ord_cls, mock_push_one, _mock_step) -> None:
        # ⭐ Il difetto che D-6 corregge: meta' merce spedita, l'invio in
        #    commessa non la fa diventare tutta partita.
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "PARZIALMENTE_EVASO"}
        repo.count_righe_pushable.return_value = 1
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 8, "durata_ms": 5, "handlers": [],
        }
        ordini_service.push_a_commessa(56)
        repo.cambia_stato.assert_not_called()

    @patch(_COMPLETA_STEP)
    @patch(_PUSH_ONE)
    @patch(_REPO, autospec=True)
    def test_push_ammesso_da_evaso_fix_orfano(self, ord_cls, mock_push_one, _mock_step) -> None:
        # Fix orfano (brief DB §16, 2026-07-10): per trigger CONFERMATO
        # l'eleggibilita' al push sopravvive all'evasione in DDT — il guard
        # ammette anche PARZIALMENTE_EVASO/EVASO. La fonte unica resta
        # fn_list_ordini_da_pushare (count_righe_pushable).
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "EVASO"}
        repo.count_righe_pushable.return_value = 1
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "push_log_id": 9, "durata_ms": 5, "handlers": [],
        }
        out = ordini_service.push_a_commessa(174)
        self.assertEqual(out["stato"], "COMPLETATO")

    @patch(_PUSH_ONE)
    @patch(_REPO, autospec=True)
    def test_push_rifiutato_da_draft(self, ord_cls, mock_push_one) -> None:
        # DRAFT resta mai pushabile: fail-fast parlante E_ORD_STATO_TRANSIZIONE.
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        with self.assertRaises(ServiceError) as cm:
            ordini_service.push_a_commessa(55)
        self.assertEqual(cm.exception.code, "E_ORD_STATO_TRANSIZIONE")
        mock_push_one.assert_not_called()

    @patch(_PUSH_ONE)
    @patch(_REPO, autospec=True)
    def test_push_parziale_non_transita(self, ord_cls, mock_push_one) -> None:
        # PARZIALE → ordine resta com'era (ri-push per completare).
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        mock_push_one.return_value = {
            "stato": "PARZIALE", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }
        ordini_service.push_a_commessa(55)
        repo.cambia_stato.assert_not_called()


class OrdiniStepPraticaTests(ModelloDocumentoMockatoMixin, SimpleTestCase):
    """Auto-completamento step pratica CONFERMA_ORDINE/INVIO_COMMESSA all'azione
    standalone del programma base (conferma / push a commessa) — bivio rev.3."""

    def setUp(self) -> None:
        super().setUp()
        _patch_atomic_noop(self)
        self.emissione_del_documento("CONFERMATO")

    # L'auto-completamento delega al BB motore completa_step_pratica (mockato qui,
    # testato in pratiche): questi test verificano il CABLAGGIO — risoluzione
    # pratica dall'ordine + template_codice + esito corretti + gating.
    _PRAT_REPO = "apps.pratiche.db.pratiche_repository.PraticheRepository"
    _STEP = "apps.pratiche.services.pratiche_service.completa_step_pratica"
    _PUSH_ONE = "apps.vendite.services.commesse_service.pr_run_commesse_push_one"

    # Scopo: conferma ordine collegato a pratica → completa CONFERMA_ORDINE POSITIVO.
    @patch(_STEP)
    @patch(_PRAT_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_conferma_completa_step_conferma_ordine(self, ord_cls, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        MockPrat.return_value.get_pratica_id_by_sorgente.return_value = 290

        ordini_service.conferma(7, user="op")

        mock_step.assert_called_once_with(
            290, template_codice="CONFERMA_ORDINE", esito="POSITIVO", user="op",
        )

    # Scopo: ordine non in pratica → no-op (BB non chiamato).
    @patch(_STEP)
    @patch(_PRAT_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_conferma_senza_pratica_noop(self, ord_cls, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        MockPrat.return_value.get_pratica_id_by_sorgente.return_value = None

        ordini_service.conferma(7)

        mock_step.assert_not_called()

    # Scopo: push a commessa (COMPLETATO) di ordine in pratica → completa
    # INVIO_COMMESSA POSITIVO (step terminale → sblocca la chiusura pratica).
    @patch(_STEP)
    @patch(_PRAT_REPO, autospec=True)
    @patch(_PUSH_ONE)
    @patch(_REPO, autospec=True)
    def test_push_completa_step_invio_commessa(self, ord_cls, mock_push_one, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
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
    @patch(_PRAT_REPO, autospec=True)
    @patch(_PUSH_ONE)
    @patch(_REPO, autospec=True)
    def test_push_parziale_non_completa_step(self, ord_cls, mock_push_one, MockPrat, mock_step) -> None:
        repo = ord_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "CONFERMATO"}
        repo.count_righe_pushable.return_value = 2
        mock_push_one.return_value = {
            "stato": "PARZIALE", "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }

        ordini_service.push_a_commessa(55)

        mock_step.assert_not_called()


class OrdiniFatturazioneImmediataTests(SimpleTestCase):
    """Corsia di instradamento `fatturazione_immediata` sull'ordine.

    Su ordini e DDT la whitelist BASTA (i mapper sono dict-comprehension sul
    payload), a differenza del contratto che copia campo per campo — ed e'
    esattamente per questo che lo stesso gesto sui tre domini aveva prodotto due
    successi e un no-op silenzioso. Qui si blocca il comportamento, cosi' un
    futuro refactor verso un mapper esplicito non lo perde in silenzio.
    """

    def setUp(self) -> None:
        # transaction.atomic() a no-op (SimpleTestCase senza DB): il verbo e il
        # riempimento dello slot di default stanno in una transazione.
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_REPO, autospec=True)
    def test_crea_ordine_porta_il_flag(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.create_ordine.return_value = {"id": 7, "uid": "u", "numero": "ORD0007"}
        ordini_service.crea_ordine({
            "billing_account_id": 3, "fatturazione_immediata": True,
        })
        self.assertIs(
            repo.create_ordine.call_args.kwargs["fatturazione_immediata"], True,
        )
        # Lo slot di default lo riempie il DB, sull'ordine appena nato (R-BE-1).
        repo.riempi_indirizzo_default.assert_called_once_with(7)

    # Senza la chiave si passa None: il repository omette la colonna e resta il
    # DEFAULT false del DB (corsia differita).
    @patch(_REPO, autospec=True)
    def test_crea_ordine_senza_flag_lascia_il_default(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.create_ordine.return_value = {"id": 7, "uid": "u", "numero": "ORD0007"}
        ordini_service.crea_ordine({"billing_account_id": 3})
        self.assertIsNone(
            repo.create_ordine.call_args.kwargs["fatturazione_immediata"],
        )

    @patch(_REPO, autospec=True)
    def test_aggiorna_ordine_persiste_il_flag(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_ordine.return_value = {"id": 7, "billing_account_id": 3}
        ordini_service.aggiorna_ordine(7, {"fatturazione_immediata": True})
        self.assertIs(
            repo.update_ordine.call_args.kwargs["fatturazione_immediata"], True,
        )


# ══════════════════════════════════════════════════════════
#  BE-B6 §5 — controprova: gli ordini NON cambiano
# ══════════════════════════════════════════════════════════
# Scopo: il brief-ddt-righe-senza-prezzo cambia il comportamento del **solo**
#        DDT. Qui si prova che gli ordini continuano a chiamare il GUSCIO
#        (`resolve_prezzo`, che solleva) e non il nucleo, e che l'eccezione
#        arriva al chiamante invece di diventare una riga senza prezzo.
#
#        ⭐ E' una **controprova a test, non una lettura del codice**: che
#        `ordini_service` non sia stato toccato lo si vede col diff oggi, ma il
#        giorno in cui qualcuno «uniformera' i due domini» il diff non ci sara'
#        piu' — questo test si'.
class OrdiniPrezzoInvariatoTests(SimpleTestCase):
    _PRICING = "apps.vendite.services.pricing_service.PricingService"

    @patch(_PRICING)
    @patch(_REPO, autospec=True)
    def test_ordini_usano_il_guscio_e_propagano(self, repo_cls, pricing_cls) -> None:
        repo = repo_cls.return_value
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 42
        pricing = pricing_cls.return_value
        pricing.resolve_prezzo.side_effect = ServiceError(
            code="E_CATEGORIA_LISTINO_NON_MAPPATA",
            message="Nessuna mappa categoria -> listino.",
        )
        testata = {
            "billing_account_id": 100, "utility_id": 5,
            "data": "2026-08-19", "emittente_fiscale_id": 3,
        }

        with self.assertRaises(ServiceError) as cm:
            ordini_service._resolve_prezzo_riga(
                repo, testata, articolo_id="ART1", uom_id=5,
            )

        # 1. l'errore risale, non diventa un prezzo assente
        self.assertEqual(cm.exception.code, "E_CATEGORIA_LISTINO_NON_MAPPATA")
        # 2. e la strada e' il guscio, non il nucleo del DDT
        pricing.resolve_prezzo.assert_called_once()
        pricing.resolve_prezzo_esito.assert_not_called()


# Scopo: Le DUE DATE DI CONSEGNA della riga (Blocco A di brief-db-modifiche-
#        certe-ciclo-vendita-e-articolo): richiesta dal cliente e confermata da
#        noi. Tre cose che il contratto dichiara e che vanno provate per intero:
#        la data arriva a `create_riga` come `date`; una malformata e' un 400
#        col CAMPO acceso (non un 500 dal DB); in PATCH `null` esplicito azzera.
#
# Indice:
#  1. test_le_date_di_consegna_arrivano_a_create_riga_come_date
#  2. test_data_di_consegna_malformata_e_400_col_campo
#  3. test_in_patch_null_esplicito_azzera_la_data
class OrdiniRigaDateConsegnaTests(SimpleTestCase):
    def _riga_composita(self, repo_cls):
        # Composita come i test vicini: sulla riga semplice il pricing pretende
        # il billing account in testata, e qui si prova il trasporto delle date.
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        repo.is_articolo_composito.return_value = True
        repo.next_riga_nr.return_value = 1
        repo.create_riga.return_value = {"id": 60}
        return repo

    @patch(f"{_SVC}._risolvi_iva_riga", return_value=(None, {}))
    @patch(f"{_SVC}._data_riferimento", return_value=date(2026, 6, 5))
    @patch(f"{_SVC}._resolve_emittente_sr_id", return_value=99)
    @patch(f"{_SVC}.validate_componenti_overrides_authorization")
    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_le_date_di_consegna_arrivano_a_create_riga_come_date(
        self, repo_cls, mock_tx, _gate, _sr, _dr, _iva,
    ) -> None:
        mock_tx.atomic.return_value = nullcontext()
        repo = self._riga_composita(repo_cls)

        ordini_service.gestisci_riga(
            7, {"articolo_id": "ART1", "qta_operativa": 1, "uom_operativa_id": 3,
                "data_consegna_richiesta_cliente": "2026-10-01",
                # La stringa vuota e' un'assenza (il form la manda cosi').
                "data_consegna_confermata": ""},
            auth_user_id=42,
        )
        _, kwargs = repo.create_riga.call_args
        self.assertEqual(kwargs["data_consegna_richiesta_cliente"], date(2026, 10, 1))
        self.assertIsNone(kwargs["data_consegna_confermata"])

    @patch(f"{_SVC}._risolvi_iva_riga", return_value=(None, {}))
    @patch(f"{_SVC}.validate_componenti_overrides_authorization")
    @patch(_REPO, autospec=True)
    def test_data_di_consegna_malformata_e_400_col_campo(self, repo_cls, _gate, _iva) -> None:
        repo = self._riga_composita(repo_cls)
        with self.assertRaises(ServiceError) as cm:
            ordini_service.gestisci_riga(
                7, {"articolo_id": "ART1", "qta_operativa": 1, "uom_operativa_id": 3,
                    "data_consegna_confermata": "domani"},
                auth_user_id=42,
            )
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "data_consegna_confermata")
        # E si ferma PRIMA di scrivere: niente riga con una data inventata.
        repo.create_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_in_patch_null_esplicito_azzera_la_data(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"stato_codice_interno": "DRAFT"}
        repo.get_riga.return_value = {"id": 60, "ordine_id": 7}
        repo.update_riga.return_value = True

        ordini_service.aggiorna_riga(
            7, 60, {"data_consegna_confermata": None,
                    "data_consegna_richiesta_cliente": "2026-10-02"},
        )
        _, kwargs = repo.update_riga.call_args
        self.assertIsNone(kwargs["data_consegna_confermata"])
        self.assertEqual(kwargs["data_consegna_richiesta_cliente"], date(2026, 10, 2))


# Scopo: Il verbo della promessa di consegna dopo la conferma
#        (`cambia_data_consegna_confermata`, brief-db-testata-dopo-emissione
#        fase 1, R-BE-1): scrive la sola colonna, nessun pre-check di stato
#        (lo decide il lock delle righe del DB).
#
# Indice:
#  1. test_ordine_confermato_scrive_la_sola_data
#  2. test_null_toglie_la_promessa
#  3. test_chiave_estranea_rifiutata_senza_scrivere
#  4. test_data_assente_e_400_col_campo
#  5. test_riga_di_un_altro_ordine_e_404
#  6. test_il_rifiuto_del_lock_passa_col_suo_codice
#  7. test_riga_spedita_passa_col_codice_del_guard
class OrdiniDataConsegnaConfermataTests(SimpleTestCase):
    def _repo(self, repo_cls, stato: str = "CONFERMATO"):
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"id": 7, "stato_codice_interno": stato}
        repo.get_riga.return_value = {"id": 60, "ordine_id": 7}
        repo.scrivi_data_consegna.return_value = {"aggiornate": 1, "saltate": 0}
        return repo

    @patch(_REPO, autospec=True)
    def test_ordine_confermato_scrive_la_sola_data(self, repo_cls) -> None:
        repo = self._repo(repo_cls)
        out = ordini_service.cambia_data_consegna_confermata(
            7, 60, {"data_consegna_confermata": "2026-11-03"},
        )
        # La scrittura e' quella dell'utility in blocco, ristretta alla riga.
        repo.scrivi_data_consegna.assert_called_once_with(
            7, "data_consegna_confermata", date(2026, 11, 3), riga_id=60,
        )
        self.assertEqual(out["data_consegna_confermata"], date(2026, 11, 3))
        # Nessun guard di stato in Python: lo stato non si chiede.
        repo.get_stato_codice.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_null_toglie_la_promessa(self, repo_cls) -> None:
        repo = self._repo(repo_cls)
        ordini_service.cambia_data_consegna_confermata(
            7, 60, {"data_consegna_confermata": None},
        )
        repo.scrivi_data_consegna.assert_called_once_with(
            7, "data_consegna_confermata", None, riga_id=60,
        )

    @patch(_REPO, autospec=True)
    def test_chiave_estranea_rifiutata_senza_scrivere(self, repo_cls) -> None:
        repo = self._repo(repo_cls)
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_data_consegna_confermata(
                7, 60, {"data_consegna_confermata": "2026-11-03", "qta_operativa": 5},
            )
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        repo.scrivi_data_consegna.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_data_assente_e_400_col_campo(self, repo_cls) -> None:
        repo = self._repo(repo_cls)
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_data_consegna_confermata(7, 60, {})
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "data_consegna_confermata")
        repo.scrivi_data_consegna.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_riga_di_un_altro_ordine_e_404(self, repo_cls) -> None:
        repo = self._repo(repo_cls)
        repo.get_riga.return_value = {"id": 60, "ordine_id": 8}
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_data_consegna_confermata(
                7, 60, {"data_consegna_confermata": "2026-11-03"},
            )
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")
        repo.scrivi_data_consegna.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_il_rifiuto_del_lock_passa_col_suo_codice(self, repo_cls) -> None:
        # Ordine EVASO: il lock delle righe rifiuta, e il codice del DB arriva
        # al client com'e' (nessuna traduzione in un codice del dominio).
        repo = self._repo(repo_cls, stato="EVASO")
        repo.scrivi_data_consegna.side_effect = DatabaseError(
            "E_RIGA_DOC_NON_BOZZA: Ordine in stato EVASO, la riga non si modifica",
        )
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_data_consegna_confermata(
                7, 60, {"data_consegna_confermata": "2026-11-03"},
            )
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")

    @patch(_REPO, autospec=True)
    def test_riga_spedita_passa_col_codice_del_guard(self, repo_cls) -> None:
        # D-7 (brief-db-date-consegna-righe-in-blocco): sulla riga singola la
        # riga spedita NON si salta, la rifiuta il guard di riga col suo 409.
        repo = self._repo(repo_cls, stato="PARZIALMENTE_EVASO")
        repo.scrivi_data_consegna.side_effect = DatabaseError(
            "E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA: Ordine 12, riga 1: la merce e' gia' partita",
        )
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_data_consegna_confermata(
                7, 60, {"data_consegna_confermata": "2026-11-03"},
            )
        self.assertEqual(cm.exception.code, "E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA")
        self.assertEqual(
            ErrorPolicyRegistry.resolve("E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA").http_status, 409,
        )


# Scopo: I satelliti «leggono prima la testata» (2026-09-21, allineamento a
#        api.md §Scope emittente): un ordine fuori perimetro RLS — che il
#        repository vede come `None`, identico a un id inesistente — deve
#        essere un 404, non un 200 con lista vuota. Prova i tre satelliti e
#        il caso felice (la testata trovata non cambia la delega).
#
# Indice:
#  1. test_list_righe_ordine_non_trovato_e_404
#  2. test_list_riepilogo_iva_ordine_non_trovato_e_404
#  3. test_list_componenti_riga_di_altro_ordine_e_404
#  4. test_list_righe_con_testata_delega_al_repo
class OrdiniSatellitiTestataTests(SimpleTestCase):
    @patch(_REPO, autospec=True)
    def test_list_righe_ordine_non_trovato_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ordine.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.list_righe(99)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")
        repo.list_righe.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_list_riepilogo_iva_ordine_non_trovato_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ordine.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.list_riepilogo_iva(99)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")
        repo.list_riepilogo_iva.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_list_componenti_riga_di_altro_ordine_e_404(self, repo_cls) -> None:
        # La riga esiste ma appartiene a un altro ordine: l'id incrociato
        # nell'URL non deve aprire i componenti di nessuno.
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 31, "ordine_id": 8}
        with self.assertRaises(ServiceError) as cm:
            ordini_service.list_componenti_riga(7, 31)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")
        repo.list_componenti_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_list_righe_con_testata_delega_al_repo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ordine.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        repo.list_righe.return_value = [{"id": 31}]
        self.assertEqual(ordini_service.list_righe(7), [{"id": 31}])
        repo.list_righe.assert_called_once_with(7)
