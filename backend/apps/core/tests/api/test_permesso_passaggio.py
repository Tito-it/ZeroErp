# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del BB `PassaggioDocumento` e del suo ramo in
#        `ZeroERPPermission.valuta`: l'azione di un cambio di stato letta dalla
#        riga del passaggio (M-3, brief-modello-documento-vendita §7.6).
#        Repository e resolver mockati: la lettura vera e' provata in
#        `core/tests/db/test_documento_modello_repository_db`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_azione_concessa_consente_senza_livello  — decide l'azione, il livello non si guarda
 2) test_azione_negata                           — AZIONE_NEGATA con l'azione della riga
 3) test_riga_senza_azione_ricade_sul_livello     — None: livello sul documento
 4) test_sulla_classe_nega                        — senza richiesta, PASSAGGIO_SENZA_RICHIESTA
 5) test_stato_dal_corpo                          — `stato_codice` del corpo, ripulito
 6) test_stato_dal_corpo_non_testo                — niente stato: None, nessuna lettura
 7) test_stato_fisso_ignora_il_corpo              — la rotta di un verbo ha il suo stato
 8) test_campo_stato_dichiarato                   — il corpo del preventivo porta `nuovo_stato`
 9) test_documento_risolto_dal_parametro          — la rotta porta la pratica, l'azione e' del preventivo
10) test_documento_non_risolto                    — nessun documento: None, nessuna lettura
11) test_emissione_letta_a_ogni_richiesta         — «Emetti»: lo stato dal vocabolario, il corpo no
12) test_emissione_assente                        — documento che non si emette: None
13) test_emissione_esclusiva_con_stato_fisso      — due fonti dello stato: errore di cablaggio
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.api.permissions import MotivoDiniego, PassaggioDocumento, ZeroERPPermission
from apps.core.db.documento_modello_repository import StatoDocumento
from apps.core.tests.api.test_permissions import _mock_view

_REPO = "apps.core.api.permissions.DocumentoModelloRepository"
_RESOLVER = "apps.core.api.permissions.PermissionResolver"


def _utente() -> MagicMock:
    user = MagicMock()
    user.id = 7
    user.is_superuser = False
    return user


# Scopo: una view finta che dichiara il passaggio sulla POST, con l'id nel
#        percorso e il corpo dato. Il parametro ha un nome neutro
#        (`documento_id`): i test lo usano con testate diverse.
def _view(passaggio: PassaggioDocumento, corpo: object | None = None) -> MagicMock:
    view = _mock_view(area="vendite")
    view.model_permission = ("vendite", "ddt")
    view.post_passaggio = passaggio
    view.kwargs = {"documento_id": 42}
    view.request.data = corpo if corpo is not None else {}
    return view


_CAMBIO = PassaggioDocumento(testata="vendite.ddt", documento_kwarg="documento_id")


class PassaggioNellaCatenaTests(TestCase):

    def _valuta(self, view: object) -> object:
        return ZeroERPPermission.valuta(_utente(), view, method="POST", cache={})

    @patch(_RESOLVER)
    @patch(_REPO)
    def test_azione_concessa_consente_senza_livello(self, repo_cls, resolver) -> None:
        resolver.is_super_admin.return_value = False
        repo_cls.return_value.azione_del_passaggio.return_value = "emetti_ddt"
        resolver.check_azione.return_value = True

        esito = self._valuta(_view(_CAMBIO, {"stato_codice": "ANNULLATO"}))

        self.assertTrue(esito.consentito)
        repo_cls.return_value.azione_del_passaggio.assert_called_once_with(
            "vendite.ddt", 42, "ANNULLATO",
        )
        resolver.check_azione.assert_called_once()
        self.assertEqual(resolver.check_azione.call_args.args[1], "emetti_ddt")
        resolver.get_livello_oggetto.assert_not_called()

    @patch(_RESOLVER)
    @patch(_REPO)
    def test_azione_negata(self, repo_cls, resolver) -> None:
        resolver.is_super_admin.return_value = False
        repo_cls.return_value.azione_del_passaggio.return_value = "emetti_ddt"
        resolver.check_azione.return_value = False

        esito = self._valuta(_view(_CAMBIO, {"stato_codice": "ANNULLATO"}))

        self.assertFalse(esito.consentito)
        self.assertIs(esito.motivo, MotivoDiniego.AZIONE_NEGATA)
        self.assertEqual(esito.azione, "emetti_ddt")

    @patch(_RESOLVER)
    @patch(_REPO)
    def test_riga_senza_azione_ricade_sul_livello(self, repo_cls, resolver) -> None:
        resolver.is_super_admin.return_value = False
        repo_cls.return_value.azione_del_passaggio.return_value = None
        resolver.get_area_schema_db.return_value = "vendite"
        resolver.get_livello_oggetto.return_value = "LETTURA"

        esito = self._valuta(_view(_CAMBIO, {"stato_codice": "SPEDITO"}))

        self.assertFalse(esito.consentito)
        self.assertIs(esito.motivo, MotivoDiniego.LIVELLO_INSUFFICIENTE)
        resolver.check_azione.assert_not_called()
        resolver.get_livello_oggetto.assert_called_once()

    @patch(_RESOLVER)
    @patch(_REPO)
    def test_sulla_classe_nega(self, repo_cls, resolver) -> None:
        resolver.is_super_admin.return_value = False

        class _ViewCambio:
            area_funzionale = "vendite"
            model_permission = ("vendite", "ddt")
            post_passaggio = _CAMBIO

        esito = self._valuta(_ViewCambio)

        self.assertFalse(esito.consentito)
        self.assertIs(esito.motivo, MotivoDiniego.PASSAGGIO_SENZA_RICHIESTA)
        repo_cls.assert_not_called()


class PassaggioDocumentoTests(TestCase):

    @patch(_REPO)
    def test_stato_dal_corpo(self, repo_cls) -> None:
        repo_cls.return_value.azione_del_passaggio.return_value = "emetti_ddt"

        azione = _CAMBIO.azione(_view(_CAMBIO, {"stato_codice": "  ANNULLATO "}))

        self.assertEqual(azione, "emetti_ddt")
        repo_cls.return_value.azione_del_passaggio.assert_called_once_with(
            "vendite.ddt", 42, "ANNULLATO",
        )

    # Un numero o un vuoto non sono uno stato: decide il livello, e il 400 col
    # campo lo da' il service.
    @patch(_REPO)
    def test_stato_dal_corpo_non_testo(self, repo_cls) -> None:
        for corpo in ({"stato_codice": 5}, {"stato_codice": "  "}, {}):
            with self.subTest(corpo=corpo):
                self.assertIsNone(_CAMBIO.azione(_view(_CAMBIO, corpo)))
        repo_cls.assert_not_called()

    @patch(_REPO)
    def test_stato_fisso_ignora_il_corpo(self, repo_cls) -> None:
        conferma = PassaggioDocumento(
            testata="vendite.resi", documento_kwarg="documento_id", stato_chiesto="CONFERMATO",
        )
        repo_cls.return_value.azione_del_passaggio.return_value = "conferma_reso"

        azione = conferma.azione(_view(conferma, {"stato_codice": "ANNULLATO"}))

        self.assertEqual(azione, "conferma_reso")
        repo_cls.return_value.azione_del_passaggio.assert_called_once_with(
            "vendite.resi", 42, "CONFERMATO",
        )

    # Il preventivo porta lo stato chiesto in `nuovo_stato`: il campo lo
    # dichiara la view, `stato_codice` non si guarda.
    @patch(_REPO)
    def test_campo_stato_dichiarato(self, repo_cls) -> None:
        stato = PassaggioDocumento(
            testata="vendite.preventivi", documento_kwarg="documento_id", campo_stato="nuovo_stato",
        )
        repo_cls.return_value.azione_del_passaggio.return_value = "emetti_preventivo"

        azione = stato.azione(_view(stato, {"nuovo_stato": "ANNULLATO", "stato_codice": "X"}))

        self.assertEqual(azione, "emetti_preventivo")
        repo_cls.return_value.azione_del_passaggio.assert_called_once_with(
            "vendite.preventivi", 42, "ANNULLATO",
        )

    # La rotta porta un altro id (la pratica): il documento lo ricava la
    # funzione dichiarata, e l'azione si legge sul documento risolto.
    @patch(_REPO)
    def test_documento_risolto_dal_parametro(self, repo_cls) -> None:
        risolvi = MagicMock(return_value=900)
        stato = PassaggioDocumento(
            testata="vendite.preventivi", documento_kwarg="documento_id", campo_stato="nuovo_stato",
            risolvi_documento=risolvi,
        )
        repo_cls.return_value.azione_del_passaggio.return_value = "emetti_preventivo"

        self.assertEqual(stato.azione(_view(stato, {"nuovo_stato": "ANNULLATO"})), "emetti_preventivo")
        risolvi.assert_called_once_with(42)
        repo_cls.return_value.azione_del_passaggio.assert_called_once_with(
            "vendite.preventivi", 900, "ANNULLATO",
        )

    # Nessun documento dietro il parametro: decide il livello, e il 4xx lo da'
    # il service.
    @patch(_REPO)
    def test_documento_non_risolto(self, repo_cls) -> None:
        stato = PassaggioDocumento(
            testata="vendite.preventivi", documento_kwarg="documento_id", campo_stato="nuovo_stato",
            risolvi_documento=MagicMock(return_value=None),
        )

        self.assertIsNone(stato.azione(_view(stato, {"nuovo_stato": "ANNULLATO"})))
        repo_cls.assert_not_called()

    # «Emetti» (B-2, brief-modello-documento-vendita §8.11): lo stato chiesto
    # e' lo stato di emissione, chiesto al DB a OGNI richiesta, non fissato
    # alla definizione della view; il corpo multipart non porta uno stato.
    @patch(_REPO)
    def test_emissione_letta_a_ogni_richiesta(self, repo_cls) -> None:
        emetti = PassaggioDocumento(
            testata="vendite.ordini", documento_kwarg="documento_id", stato_del_modello="emissione",
        )
        repo = repo_cls.return_value
        repo.stato_di_emissione.return_value = StatoDocumento(id=2, codice="CONFERMATO")
        repo.azione_del_passaggio.return_value = "emetti_ordine"

        for _ in range(2):
            self.assertEqual(emetti.azione(_view(emetti, {"stato_codice": "X"})), "emetti_ordine")
        self.assertEqual(repo.stato_di_emissione.call_count, 2)
        repo.stato_di_emissione.assert_called_with("vendite.ordini")
        repo.azione_del_passaggio.assert_called_with("vendite.ordini", 42, "CONFERMATO")

    # Il documento non si emette: nessun passaggio, decide il livello (e il
    # service risponde E_CONFIG_MANCANTE).
    @patch(_REPO)
    def test_emissione_assente(self, repo_cls) -> None:
        emetti = PassaggioDocumento(
            testata="vendite.resi", documento_kwarg="documento_id", stato_del_modello="emissione",
        )
        repo_cls.return_value.stato_di_emissione.return_value = None

        self.assertIsNone(emetti.azione(_view(emetti)))
        repo_cls.return_value.azione_del_passaggio.assert_not_called()

    def test_emissione_esclusiva_con_stato_fisso(self) -> None:
        with self.assertRaises(ValueError):
            PassaggioDocumento(
                testata="vendite.ddt", documento_kwarg="documento_id",
                stato_chiesto="EMESSO", stato_del_modello="emissione",
            )
