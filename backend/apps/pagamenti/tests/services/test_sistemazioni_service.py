# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del giro delle sistemazioni — e soprattutto di cio' che il
#        backend NON decide.
# Note: ⚠️ Le tre destinazioni, la verifica dell'eccedenza e le transizioni le
#       tiene il database. Qui si prova che il backend registri la decisione
#       giusta, derivi cio' che va derivato, e non si metta in mezzo.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  CreaSistemazioneTests.test_cliente_ed_emittente_sono_derivati_non_dichiarati
2)  CreaSistemazioneTests.test_il_payload_non_accetta_cliente_ne_emittente
3)  CreaSistemazioneTests.test_riporto_pretende_il_documento_di_destinazione
4)  CreaSistemazioneTests.test_compensazione_pretende_il_documento_di_destinazione
5)  CreaSistemazioneTests.test_rimborso_vieta_il_documento_di_destinazione
6)  CreaSistemazioneTests.test_destinazione_inventata_rifiutata
7)  CreaSistemazioneTests.test_destinazione_normalizzata_maiuscola
8)  CreaSistemazioneTests.test_fattura_inesistente_404
9)  CreaSistemazioneTests.test_importo_obbligatorio
10) CreaSistemazioneTests.test_il_backend_non_verifica_l_eccedenza
11) VerbiTests.test_conferma_passa_il_canale_al_database
12) VerbiTests.test_conferma_senza_canale_passa_none
13) VerbiTests.test_conferma_restituisce_l_esito_intatto
14) VerbiTests.test_conferma_su_atto_inesistente_404
15) VerbiTests.test_annulla_passa_il_motivo
16) VerbiTests.test_annulla_senza_motivo_lascia_decidere_il_database
17) EccedenzeTests.test_default_per_cliente_non_per_documento
18) EccedenzeTests.test_chi_e_in_credito_fuori_vocabolario_rifiutato
19) EccedenzeTests.test_i_due_valori_passano
20) EccedenzeTests.test_ordinamento_fuori_whitelist_rifiutato
21) EccedenzeTests.test_il_backend_non_somma_le_eccedenze
"""

import inspect
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, create_autospec, patch

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.services import sistemazioni_service
from apps.pagamenti.db.pagamenti_repository import PagamentiRepository

_ATTO = {
    "id": 3,
    "destinazione": "RIMBORSO",
    "stato": "BOZZA",
    "importo": Decimal("200.00"),
    "contabile_id": None,
    "fondo_source_id": None,
}


def _repo() -> MagicMock:
    repo = create_autospec(PagamentiRepository, instance=True)
    repo.get_riferimenti_fattura.return_value = {
        "fattura_id": 2263,
        "emittente_soggetto_ruolo_id": 72,
        "billing_account_id": 41,
        "cliente_soggetto_ruolo_id": 900,
    }
    repo.create_sistemazione.return_value = 3
    repo.get_sistemazione.return_value = dict(_ATTO)
    repo.list_sistemazioni_fattura.return_value = ([], 0)
    repo.list_eccedenze.return_value = ([], 0)
    repo.conferma_sistemazione.return_value = {
        "contabile_id": 88,
        "fondo_source_id": None,
        "esito": "RIMBORSO",
    }
    repo.annulla_sistemazione.return_value = "ANNULLATA"
    return repo


class _Base(TestCase):
    # Scopo: Sostituisce il repository con un doppio.
    def setUp(self) -> None:
        self.repo = _repo()
        patcher = patch.object(
            sistemazioni_service, "PagamentiRepository", autospec=True, return_value=self.repo
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class CreaSistemazioneTests(_Base):
    _OK = {"fattura_origine_id": 2263, "destinazione": "RIMBORSO", "importo": "200.00"}

    # Scopo: 🔴 Cliente ed emittente si DERIVANO dalla fattura di origine. Il
    #        guard del database li verifica con un codice TECNICO apposta,
    #        perche' «non li sceglie una persona in un modulo, li deriva chi
    #        costruisce l'atto» — e chi legge quel messaggio non e' l'operatore.
    def test_cliente_ed_emittente_sono_derivati_non_dichiarati(self):
        sistemazioni_service.crea_sistemazione(dict(self._OK))
        kwargs = self.repo.create_sistemazione.call_args.kwargs
        self.assertEqual(kwargs["cliente_soggetto_ruolo_id"], 900)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 72)
        self.repo.get_riferimenti_fattura.assert_called_once_with(2263)

    # Scopo: E non si possono nemmeno dichiarare: il payload li rifiuta.
    def test_il_payload_non_accetta_cliente_ne_emittente(self):
        for chiave in ("cliente_soggetto_ruolo_id", "emittente_soggetto_ruolo_id"):
            with self.assertRaises(ServiceError):
                sistemazioni_service.crea_sistemazione({**self._OK, chiave: 1})
        self.repo.create_sistemazione.assert_not_called()

    # Scopo: Il credito va **da qualche parte**: riporto e compensazione
    #        vogliono il secondo documento.
    def test_riporto_pretende_il_documento_di_destinazione(self):
        with self.assertRaises(ServiceError):
            sistemazioni_service.crea_sistemazione(
                {**self._OK, "destinazione": "RIPORTO", "motivo": "credito residuo"}
            )

    def test_compensazione_pretende_il_documento_di_destinazione(self):
        with self.assertRaises(ServiceError):
            sistemazioni_service.crea_sistemazione(
                {**self._OK, "destinazione": "COMPENSAZIONE"}
            )

    # Scopo: ⛔ Sul rimborso e' VIETATO: il denaro esce dal sistema, e un secondo
    #        documento non esiste.
    def test_rimborso_vieta_il_documento_di_destinazione(self):
        with self.assertRaises(ServiceError):
            sistemazioni_service.crea_sistemazione(
                {**self._OK, "fattura_destinazione_id": 2264}
            )

    def test_destinazione_inventata_rifiutata(self):
        with self.assertRaises(ServiceError):
            sistemazioni_service.crea_sistemazione(
                {**self._OK, "destinazione": "SCONTO"}
            )
        self.repo.create_sistemazione.assert_not_called()

    def test_destinazione_normalizzata_maiuscola(self):
        sistemazioni_service.crea_sistemazione({**self._OK, "destinazione": "rimborso"})
        self.assertEqual(
            self.repo.create_sistemazione.call_args.kwargs["destinazione"], "RIMBORSO"
        )

    # Scopo: Documento inesistente (o fuori perimetro) -> 404, e i due casi
    #        restano indistinguibili.
    def test_fattura_inesistente_404(self):
        self.repo.get_riferimenti_fattura.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            sistemazioni_service.crea_sistemazione(dict(self._OK))
        self.assertEqual(ctx.exception.code, sistemazioni_service.E_FATTURA_NON_TROVATA)

    def test_importo_obbligatorio(self):
        payload = {k: v for k, v in self._OK.items() if k != "importo"}
        with self.assertRaises(ServiceError):
            sistemazioni_service.crea_sistemazione(payload)

    # Scopo: 🔴 **Registrare non e' eseguire.** Il controllo dell'eccedenza sta
    #        alla CONFERMA, perche' fra decidere e confermare puo' arrivare un
    #        altro incasso: verificarla qui darebbe una garanzia che scade.
    # ⚠️ Il presidio guarda le CHIAMATE, non le parole: la prima stesura cercava
    #    «eccedenza» nel sorgente e si accendeva sul MESSAGGIO all'operatore
    #    («il documento con l'eccedenza e' obbligatorio») — un falso positivo, e
    #    un presidio che ne da' lo disattiva il primo che ci sbatte.
    def test_il_backend_non_verifica_l_eccedenza(self):
        sorgente = inspect.getsource(sistemazioni_service.crea_sistemazione)
        for chiamata in ("get_saldo", "saldi_service", "list_eccedenze", "fn_get_saldo"):
            self.assertNotIn(
                chiamata,
                sorgente,
                f"il service interroga i saldi ({chiamata}): l'eccedenza la verifica la conferma",
            )
        # E non e' nemmeno il repository a farlo di nascosto per lui.
        self.repo.list_eccedenze.assert_not_called()
        self.repo.get_saldo_documento.assert_not_called()


class VerbiTests(_Base):
    # Scopo: ⚠️ Il canale del rimborso si chiede alla CONFERMA e non alla
    #        registrazione: da quale conto esce il bonifico e' una decisione del
    #        momento in cui si paga.
    def test_conferma_passa_il_canale_al_database(self):
        sistemazioni_service.conferma_sistemazione(3, {"ente_incasso_id": 4})
        self.assertEqual(
            self.repo.conferma_sistemazione.call_args.kwargs["ente_incasso_id"], 4
        )

    # Scopo: Su riporto e compensazione il canale non serve: il denaro non esce.
    def test_conferma_senza_canale_passa_none(self):
        sistemazioni_service.conferma_sistemazione(3, {})
        self.assertIsNone(
            self.repo.conferma_sistemazione.call_args.kwargs["ente_incasso_id"]
        )

    # Scopo: L'esito risale intatto — e sono DUE colonne, non una polimorfa:
    #        le tre destinazioni producono due specie diverse di oggetto.
    def test_conferma_restituisce_l_esito_intatto(self):
        esito = sistemazioni_service.conferma_sistemazione(3, {})["esito"]
        self.assertEqual(esito["contabile_id"], 88)
        self.assertIsNone(esito["fondo_source_id"])
        self.assertEqual(esito["esito"], "RIMBORSO")

    def test_conferma_su_atto_inesistente_404(self):
        self.repo.get_sistemazione.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            sistemazioni_service.conferma_sistemazione(999, {})
        self.assertEqual(
            ctx.exception.code, sistemazioni_service.E_SISTEMAZIONE_NON_TROVATA
        )
        self.repo.conferma_sistemazione.assert_not_called()

    def test_annulla_passa_il_motivo(self):
        sistemazioni_service.annulla_sistemazione(3, {"motivo": "deciso altrimenti"})
        self.assertEqual(
            self.repo.annulla_sistemazione.call_args.kwargs["motivo"],
            "deciso altrimenti",
        )

    # Scopo: ⚠️ Il motivo e' obbligatorio SE l'atto non ne aveva gia' uno, e a
    #        saperlo e' il database. Il backend non replica quella regola: la
    #        replicherebbe a meta', perche' non sa che cosa c'era scritto prima.
    def test_annulla_senza_motivo_lascia_decidere_il_database(self):
        sistemazioni_service.annulla_sistemazione(3, {})
        self.assertIsNone(self.repo.annulla_sistemazione.call_args.kwargs["motivo"])


class EccedenzeTests(_Base):
    # Scopo: ⭐ Il default e' per CLIENTE e non per documento: la decisione si
    #        prende guardando il cliente — compensare significa mettere insieme
    #        due documenti suoi, e un elenco per documento lo nasconde.
    def test_default_per_cliente_non_per_documento(self):
        sistemazioni_service.list_eccedenze()
        self.assertEqual(
            self.repo.list_eccedenze.call_args.kwargs["order_by"], "eccedenza_cliente"
        )

    def test_chi_e_in_credito_fuori_vocabolario_rifiutato(self):
        with self.assertRaises(ServiceError):
            sistemazioni_service.list_eccedenze(chi_e_in_credito="BANCA")
        self.repo.list_eccedenze.assert_not_called()

    # Scopo: I due versi esistono entrambi: il cliente che ha pagato di piu', e
    #        l'azienda su un documento a credito.
    def test_i_due_valori_passano(self):
        for valore in sistemazioni_service.CHI_E_IN_CREDITO:
            sistemazioni_service.list_eccedenze(chi_e_in_credito=valore)
            self.assertEqual(
                self.repo.list_eccedenze.call_args.kwargs["chi_e_in_credito"], valore
            )

    def test_ordinamento_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError):
            sistemazioni_service.list_eccedenze(order_by="eccedenza; DROP")
        self.repo.list_eccedenze.assert_not_called()

    # Scopo: ⭐ La vista porta gia' il raggruppamento per cliente in finestra:
    #        rifarlo in Python sarebbe una seconda aritmetica da tenere
    #        allineata alla prima.
    def test_il_backend_non_somma_le_eccedenze(self):
        sorgente = inspect.getsource(sistemazioni_service.list_eccedenze)
        for parola in ("sum(", "groupby", "defaultdict", "+="):
            self.assertNotIn(parola, sorgente)
