# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test della slice 3 — il verbo dell'abbinamento, le due code, l'elenco
#        delle rate fuori capienza e la base dei saldi.
# Note: ⚠️ Come per la slice 1: qui NON si riverificano i guard del database
#       (coerenza rata/fattura, capienza). Si prova cio' che decide il backend —
#       e soprattutto cio' che il backend NON deve decidere.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  AbbinamentoTests.test_fattura_obbligatoria_cliente_derivato
1a) AbbinamentoTests.test_cliente_dichiarato_non_si_rilegge
2)  AbbinamentoTests.test_la_rata_resta_facoltativa
3)  AbbinamentoTests.test_porta_la_riga_ad_abbinata
4)  AbbinamentoTests.test_forzatura_passa_intatta_al_database
5)  AbbinamentoTests.test_primo_tentativo_non_e_forzato
6)  AbbinamentoTests.test_motivo_senza_forzatura_rifiutato
7)  AbbinamentoTests.test_stato_non_a_catalogo
8)  AbbinamentoTests.test_il_backend_non_decide_la_capienza
9)  CodeTests.test_da_abbinare_filtra_un_solo_stato
10) CodeTests.test_sospese_filtra_un_solo_stato
11) CodeTests.test_tutte_le_prende_entrambe
11a) CodeTests.test_la_coda_porta_catalogo_e_matrice_di_riga
12) CodeTests.test_coda_inventata_rifiutata
13) CodeTests.test_ordinamento_fuori_whitelist_rifiutato
14) RateFuoriCapienzaTests.test_motivo_fuori_vocabolario_rifiutato
15) RateFuoriCapienzaTests.test_i_due_motivi_passano
16) SaldiTests.test_forma_unica_sulla_rata
17) SaldiTests.test_sul_documento_i_tre_numeri_arrivano_dal_database
17a) SaldiTests.test_documento_e_rata_hanno_la_stessa_forma
18) SaldiTests.test_documento_inesistente_404
19) SaldiTests.test_rata_inesistente_404
20) SaldiTests.test_escludi_riga_arriva_al_database
20b) SaldiTests.test_escludi_riga_arriva_al_database_anche_sul_documento
20a) SaldiTests.test_i_numeri_del_documento_da_una_lettura_sola
21) RifiutoConfermabileTests.test_la_capienza_ha_la_sua_ui_action
"""

import inspect
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.error_manager import ServiceError
from apps.core.services.error_ui_overrides import UI_ACTION_OVERRIDE
from apps.pagamenti.services import pagamenti_service, saldi_service

_RIGA = {
    "id": 11,
    "contabile_id": 7,
    "importo": Decimal("1200.00"),
    "stato_codice": "DA_ABBINARE",
    "stato_is_postabile": False,
}


def _repo() -> MagicMock:
    repo = MagicMock()
    repo.get_riga.return_value = dict(_RIGA)
    repo.abbina_riga.return_value = 1
    repo.list_righe_coda.return_value = ([], 0)
    # ⭐ La coda porta catalogo e matrice di riga accanto alle righe (FE-4):
    #    il finto risponde la forma, vuota.
    repo.list_transizioni.return_value = ([], [])
    repo.list_stati_riga.return_value = []
    repo.list_rate_fuori_capienza.return_value = ([], 0)
    repo.get_saldo_rata.return_value = {
        "saldo": Decimal("1000.00"),
        "in_lavorazione": Decimal("200.00"),
        "incassato": Decimal("800.00"),
        "has_movimenti": True,
    }
    # ⭐ I TRE numeri del documento arrivano da UNA lettura sola: letture separate
    # leggerebbero due istanti diversi. ⚠️ Le chiavi sono quelle che
    # `fn_get_saldo_fattura` ha DAVVERO dal 25/08 (DB-10): `in_lavorazione` e
    # `incassato` in colonna, non piu' `saldo_contabile` preso dalla funzione
    # accanto.
    repo.get_saldo_documento.return_value = {
        "saldo": Decimal("500.00"),
        "in_lavorazione": Decimal("100.00"),
        "incassato": Decimal("300.00"),
        "has_movimenti": True,
    }
    repo.list_rate_con_saldo.return_value = []
    # Il cliente della fattura, per quando il chiamante non lo passa.
    repo.get_riferimenti_fattura.return_value = {
        "fattura_id": 2263, "billing_account_id": 41,
        "emittente_soggetto_ruolo_id": 32, "cliente_soggetto_ruolo_id": 9,
    }
    return repo


class _Base(TestCase):
    # Scopo: Sostituisce il repository nei DUE service che lo usano.
    def setUp(self) -> None:
        self.repo = _repo()
        for modulo in (pagamenti_service, saldi_service):
            patcher = patch.object(
                modulo, "PagamentiRepository", return_value=self.repo
            )
            patcher.start()
            self.addCleanup(patcher.stop)


class AbbinamentoTests(_Base):
    _OK = {"fattura_id": 2263, "billing_account_id": 41}

    # Scopo: Senza fattura non c'e' abbinamento — e lo stesso lo pretende il
    #        guard sui dati, che parla dopo di noi. ⭐ Il cliente invece si puo'
    #        omettere (dal 14/09, stessa regola della nascita della riga): e'
    #        quello della fattura, LETTO dal documento e passato al database —
    #        il guard lo pretende comunque su ABBINATA.
    def test_fattura_obbligatoria_cliente_derivato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.abbina_riga(11, {"billing_account_id": 41})
        self.repo.abbina_riga.assert_not_called()
        pagamenti_service.abbina_riga(11, {"fattura_id": 2263})
        self.repo.get_riferimenti_fattura.assert_called_once_with(2263)
        self.assertEqual(self.repo.abbina_riga.call_args.kwargs["billing_account_id"], 41)

    # Scopo: Se il cliente arriva dal chiamante, non si rilegge dalla fattura:
    #        e' un dato dichiarato, e il database lo verifichera'.
    def test_cliente_dichiarato_non_si_rilegge(self):
        pagamenti_service.abbina_riga(11, dict(self._OK))
        self.repo.get_riferimenti_fattura.assert_not_called()
        self.assertEqual(self.repo.abbina_riga.call_args.kwargs["billing_account_id"], 41)

    # Scopo: ⚠️ La rata resta FACOLTATIVA anche su una riga abbinata: la riga
    #        del fondo fattura ha fattura si' e rata no, ed e' un caso normale.
    def test_la_rata_resta_facoltativa(self):
        pagamenti_service.abbina_riga(11, dict(self._OK))
        self.assertIsNone(self.repo.abbina_riga.call_args.kwargs["scadenza_id"])

    # Scopo: ⭐ Dati e stato viaggiano insieme: e' lo stesso gesto.
    def test_porta_la_riga_ad_abbinata(self):
        pagamenti_service.abbina_riga(11, {**self._OK, "scadenza_id": 900})
        kwargs = self.repo.abbina_riga.call_args.kwargs
        self.assertEqual(kwargs["codice_stato_interno"], "ABBINATA")
        self.assertEqual(kwargs["scadenza_id"], 900)

    # Scopo: 🔴 Il SECONDO TEMPO della capienza: la conferma dell'operatore
    #        arriva come `forzata = true` e resta SCRITTA sulla riga — e' cio'
    #        che l'elenco a valle legge.
    def test_forzatura_passa_intatta_al_database(self):
        pagamenti_service.abbina_riga(
            11,
            {**self._OK, "forzata": True, "motivo_forzatura": "il cliente ha pagato due volte"},
        )
        kwargs = self.repo.abbina_riga.call_args.kwargs
        self.assertTrue(kwargs["forzata"])
        self.assertEqual(kwargs["motivo_forzatura"], "il cliente ha pagato due volte")

    # Scopo: Il PRIMO tentativo non e' forzato: e' il default, e il rifiuto che
    #        ne segue e' quello che fa nascere la domanda all'operatore.
    def test_primo_tentativo_non_e_forzato(self):
        pagamenti_service.abbina_riga(11, dict(self._OK))
        self.assertFalse(self.repo.abbina_riga.call_args.kwargs["forzata"])

    # Scopo: ⚠️ Un motivo senza forzatura e' una spiegazione di un gesto mai
    #        fatto, che resta a registro a confondere chi legge.
    def test_motivo_senza_forzatura_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.abbina_riga(
                11, {**self._OK, "motivo_forzatura": "perche' si'"}
            )
        self.repo.abbina_riga.assert_not_called()

    # Scopo: Zero righe toccate = lo stato non risolve a catalogo, e non e' un
    #        successo silenzioso.
    def test_stato_non_a_catalogo(self):
        self.repo.abbina_riga.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.abbina_riga(11, dict(self._OK))
        self.assertEqual(ctx.exception.code, pagamenti_service.E_STATO_NON_CONFIGURATO)

    # Scopo: 🔴 Il backend NON sa che cosa sia forzabile e non deve saperlo: la
    #        capienza la giudica il guard del database, e una seconda sede della
    #        regola divergerebbe dalla prima al primo cambiamento.
    def test_il_backend_non_decide_la_capienza(self):
        sorgente = inspect.getsource(pagamenti_service.abbina_riga)
        for parola in ("capienza", "saldo", "residuo", "importo <"):
            self.assertNotIn(
                parola,
                sorgente,
                f"il service sta valutando la capienza ({parola}): la decide il DB",
            )


class CodeTests(_Base):
    # Scopo: «Da abbinare» e «sospese» sono due mestieri (D12-f): il filtro
    #        cambia, la lista no.
    def test_da_abbinare_filtra_un_solo_stato(self):
        pagamenti_service.list_coda_righe(coda="DA_ABBINARE")
        self.assertEqual(
            self.repo.list_righe_coda.call_args.kwargs["stati"], ("DA_ABBINARE",)
        )

    def test_sospese_filtra_un_solo_stato(self):
        pagamenti_service.list_coda_righe(coda="SOSPESE")
        self.assertEqual(
            self.repo.list_righe_coda.call_args.kwargs["stati"], ("SOSPESA",)
        )

    def test_tutte_le_prende_entrambe(self):
        pagamenti_service.list_coda_righe()
        self.assertEqual(
            self.repo.list_righe_coda.call_args.kwargs["stati"],
            ("DA_ABBINARE", "SOSPESA"),
        )

    # Scopo: ⭐ La coda porta ACCANTO alle righe il catalogo degli stati di riga
    #        e le uscite richiedibili da ogni stato (FE-4): le voci del kebab
    #        si costruiscono dalla MATRICE anche qui, come nel drawer — e dalla
    #        stessa lettura delle righe, non da un endpoint suo.
    def test_la_coda_porta_catalogo_e_matrice_di_riga(self):
        self.repo.list_transizioni.return_value = (
            [("BOZZA", "VALIDATA")],
            [("SOSPESA", "SCARTATA"), ("SOSPESA", "ABBINATA"), ("SOSPESA", "DA_ABBINARE")],
        )
        self.repo.list_stati_riga.return_value = [{"codice_interno": "SOSPESA"}]
        esito = pagamenti_service.list_coda_righe(coda="SOSPESE")
        self.assertEqual(esito["stati_riga"], [{"codice_interno": "SOSPESA"}])
        # L'ordine di offerta e' quello del vocabolario dei richiedibili, e la
        # matrice della TESTATA non ci finisce dentro.
        self.assertEqual(
            esito["transizioni_riga"],
            {"SOSPESA": ["DA_ABBINARE", "ABBINATA", "SCARTATA"]},
        )
        self.assertNotIn("BOZZA", esito["transizioni_riga"])

    # Scopo: Una coda inventata e' un 400, non una lista vuota: su un
    #        vocabolario chiuso «nessun risultato» e' indistinguibile da
    #        «non c'e' niente da fare».
    def test_coda_inventata_rifiutata(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.list_coda_righe(coda="ARRETRATE")
        self.repo.list_righe_coda.assert_not_called()

    def test_ordinamento_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.list_coda_righe(order_by="importo; DROP")
        self.repo.list_righe_coda.assert_not_called()


class RateFuoriCapienzaTests(_Base):
    # Scopo: Stessa ragione delle code, e qui pesa di piu': i motivi sono DUE,
    #        e una lista vuota per un motivo scritto male direbbe che non c'e'
    #        denaro fuori capienza — la risposta piu' rassicurante.
    def test_motivo_fuori_vocabolario_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.list_rate_fuori_capienza(motivo="TROPPO_ALTA")
        self.repo.list_rate_fuori_capienza.assert_not_called()

    # Scopo: ⭐ Sono due popolazioni diverse in un elenco solo: il sovra-incasso
    #        e il rimborso dove non era entrato niente.
    def test_i_due_motivi_passano(self):
        for motivo in pagamenti_service.MOTIVI_FUORI_CAPIENZA:
            pagamenti_service.list_rate_fuori_capienza(motivo=motivo)
            self.assertEqual(
                self.repo.list_rate_fuori_capienza.call_args.kwargs["motivo"], motivo
            )


class SaldiTests(_Base):
    # Scopo: ⭐ La forma e' UNA sola a ogni livello: `residuo`, `in_lavorazione`,
    #        `incassato`. Una schermata sceglie quali accendere, ⛔ nessuna li
    #        rinomina.
    def test_forma_unica_sulla_rata(self):
        saldo = saldi_service.saldo_rata(900)
        for campo in saldi_service.CAMPI_SALDO:
            self.assertIn(campo, saldo)
        self.assertEqual(saldo["livello"], "RATA")
        self.assertEqual(saldo["residuo"], Decimal("1000.00"))
        self.assertEqual(saldo["incassato"], Decimal("800.00"))

    # Scopo: ⭐ Anche il DOCUMENTO risponde tutti e tre i numeri, dal 2026-08-29.
    #        Questo test asseriva il contrario — `incassato is None` — ed era
    #        verde: ⚠️ *codificava l'ipotesi «il database ne da' due», vera fino
    #        al 25/08 e falsa da allora.* Un test che asserisce un'assenza la
    #        difende anche dopo che e' stata colmata.
    # ⛔ Resta il divieto vero, che non scade: l'`incassato` del documento non si
    #        somma dalle rate — una riga puo' avere fattura SENZA rata (il fondo
    #        fattura e' cosi') e quel denaro non comparirebbe in nessuna somma.
    def test_sul_documento_i_tre_numeri_arrivano_dal_database(self):
        saldo = saldi_service.saldo_documento(2263)
        self.assertEqual(saldo["residuo"], Decimal("500.00"))
        self.assertEqual(saldo["in_lavorazione"], Decimal("100.00"))
        self.assertEqual(saldo["incassato"], Decimal("300.00"))
        self.repo.list_rate_con_saldo.assert_not_called()

    # Scopo: ⛔ La forma e' la STESSA a tutti i livelli, ed e' il vincolo «una
    #        sede sola per i saldi»: se un giorno il documento tornasse a
    #        rispondere meno numeri della rata, la base non sarebbe piu' unica.
    def test_documento_e_rata_hanno_la_stessa_forma(self):
        doc = saldi_service.saldo_documento(2263)
        rata = saldi_service.saldo_rata(900)
        self.assertEqual(set(doc), set(rata))
        for campo in saldi_service.CAMPI_SALDO:
            self.assertIsNotNone(doc[campo], f"{campo} spento sul documento")
            self.assertIsNotNone(rata[campo], f"{campo} spento sulla rata")

    # Scopo: ⭐ Una lettura sola per tutti e tre i numeri: separate
    #        leggerebbero DUE ISTANTI diversi, e se una registrazione atterra
    #        fra l'una e l'altra il pannello mostra un residuo di prima accanto
    #        a un «in lavorazione» di dopo — due numeri veri che insieme
    #        raccontano una cosa falsa.
    def test_i_numeri_del_documento_da_una_lettura_sola(self):
        saldi_service.saldo_documento(2263)
        self.repo.get_saldo_documento.assert_called_once()

    def test_documento_inesistente_404(self):
        self.repo.get_saldo_documento.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            saldi_service.saldo_documento(999)
        self.assertEqual(ctx.exception.code, saldi_service.E_FATTURA_NON_TROVATA)

    def test_rata_inesistente_404(self):
        self.repo.get_saldo_rata.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            saldi_service.saldo_rata(999)
        self.assertEqual(ctx.exception.code, saldi_service.E_RATA_NON_TROVATA)

    # Scopo: ⚠️ Chiedere lo spazio PRIMA DI SE': serve a sapere se una riga ci
    #        sta senza contarsi addosso.
    def test_escludi_riga_arriva_al_database(self):
        saldi_service.saldo_rata(900, escludi_riga_id=11)
        self.assertEqual(
            self.repo.get_saldo_rata.call_args.kwargs["escludi_riga_id"], 11
        )

    # Scopo: ⭐ P-6 (2026-09-18): lo stesso «prima di se'» sul DOCUMENTO, con lo
    #        stesso nome — chi corregge una riga senza rata (il fondo fattura)
    #        legge il saldo senza contarsi addosso. Fino a quel giorno il
    #        pannello lo dichiarava come non applicato.
    def test_escludi_riga_arriva_al_database_anche_sul_documento(self):
        saldi_service.saldo_documento(2263, escludi_riga_id=11)
        self.assertEqual(
            self.repo.get_saldo_documento.call_args.kwargs["escludi_riga_id"], 11
        )
        # E senza opzione il repository riceve `None`, non un'assenza: la
        # firma e' una sola nei due versi.
        saldi_service.saldo_documento(2263)
        self.assertIsNone(
            self.repo.get_saldo_documento.call_args.kwargs["escludi_riga_id"]
        )


class RifiutoConfermabileTests(TestCase):
    # Scopo: 🔴 Il presidio della decisione Q-1. Senza questa voce il rifiuto
    #        della capienza arriva al frontend come un 409 qualunque: banner
    #        rosso, e l'operatore BLOCCATO su un caso che il dominio dichiara
    #        ammesso. ⚠️ E' una riga sola in un file di 176: si toglie senza
    #        accorgersene, e questo test e' cio' che se ne accorge.
    def test_la_capienza_ha_la_sua_ui_action(self):
        self.assertEqual(
            UI_ACTION_OVERRIDE.get("E_RIGA_CONTABILE_CAPIENZA_SUPERATA"),
            "confirm_and_retry",
        )
