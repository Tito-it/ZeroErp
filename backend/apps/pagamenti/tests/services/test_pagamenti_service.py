# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del service `pagamenti` — le regole che il BACKEND tiene, non
#        quelle del database.
# Note: ⚠️ Qui NON si riverificano i guard di PostgreSQL (transizioni,
#       quadratura, capienza): sono provati da 14 file pgTAP e replicarli
#       significherebbe avere due sedi che divergono. Si prova cio' che il
#       backend decide da se': il vocabolario di cio' che una persona puo'
#       chiedere, l'integrita' della dichiarazione, e il fatto che l'esito
#       della registrazione risalga INTATTO.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  CreaDistintaTests.test_origine_manuale_e_bozza_forzate
2)  CreaDistintaTests.test_operatore_non_viene_passato
3)  CreaDistintaTests.test_importo_dichiarato_scritto_a_parte
4)  CreaDistintaTests.test_gia_popolata_quando_la_distinta_ha_righe
5)  CreaDistintaTests.test_centro_obbligatorio
6)  CreaDistintaTests.test_data_contabile_obbligatoria
6a) CreaDistintaTests.test_emittente_scelto_viene_trasportato
6b) CreaDistintaTests.test_senza_emittente_passa_none_e_non_deduce
6c) CreaDistintaTests.test_emittente_non_positivo_rifiutato
7)  StatoDistintaTests.test_chiusa_non_e_richiedibile
8)  StatoDistintaTests.test_annullata_e_richiedibile
9)  StatoDistintaTests.test_distinta_inesistente_404
10) StatoRigaTests.test_postata_non_e_richiedibile
11) StatoRigaTests.test_motivo_sospeso_scritto_prima_dello_stato
12) RegistrazioneTests.test_mezza_dichiarazione_rifiutata_solo_righe
13) RegistrazioneTests.test_mezza_dichiarazione_rifiutata_solo_totale
14) RegistrazioneTests.test_dichiarazione_intera_passa_al_database
15) RegistrazioneTests.test_senza_dichiarazione_passa_none
16) RegistrazioneTests.test_nulla_da_postare_non_e_un_errore
16a) RegistrazioneTests.test_dichiarazione_zero_e_legittima
16b) StatoNonConfiguratoTests.test_distinta_stato_non_a_catalogo
16c) StatoNonConfiguratoTests.test_riga_stato_non_a_catalogo
16d) ImportiTests.test_nan_rifiutato
16e) ImportiTests.test_infinito_rifiutato
16f) AtomicitaTests.test_crea_distinta_e_una_transazione_sola
17) ImportiTests.test_float_non_perde_precisione
18) ImportiTests.test_stringa_non_numerica_rifiutata
19) ImportiTests.test_booleano_rifiutato
20) PatchTests.test_riga_non_accetta_abbinamento
21) PatchTests.test_patch_vuoto_rifiutato
22) ListaTests.test_ordinamento_fuori_whitelist_rifiutato
23) ListaTests.test_righe_della_distinta_ordinamento_fuori_whitelist_rifiutato
24) ListaTests.test_righe_della_distinta_senza_ordinamento_e_un_none_e_un_conteggio_vero
24a) ListaTests.test_le_scartate_sono_fuori_di_default_e_contate
25) ListaTests.test_il_dettaglio_non_porta_piu_le_righe
"""

from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.services import pagamenti_service


# Distinta minima: il service legge `righe_totali` per `gia_popolata` e i
# totali per l'anteprima.
def _distinta(**over):
    riga = {
        "id": 7,
        "codice": "CNT-0001",
        "stato_codice": "BOZZA",
        "righe_totali": 0,
        "righe_registrabili": 0,
        "totale_righe": Decimal("0"),
        "totale_registrabile": Decimal("0"),
        "importo_dichiarato": None,
        "scarto_dichiarato": None,
    }
    riga.update(over)
    return riga


def _riga_contabile(**over):
    riga = {
        "id": 11,
        "contabile_id": 7,
        "importo": Decimal("100.00"),
        "stato_codice": "DA_ABBINARE",
        "stato_descrizione": "Riga da abbinare manualmente",
        "stato_is_postabile": False,
    }
    riga.update(over)
    return riga


# Scopo: Repository finto con i ritorni che il service si aspetta.
def _repo(**over) -> MagicMock:
    repo = MagicMock()
    repo.get_distinta.return_value = _distinta()
    repo.get_riga.return_value = _riga_contabile()
    repo.list_righe.return_value = []
    repo.list_stati_distinta.return_value = []
    repo.list_stati_riga.return_value = []
    repo.get_or_create_distinta.return_value = 7
    # ⚠️ Le scritture rispondono il NUMERO DI RIGHE TOCCATE, e il service lo
    # guarda: un doppio che rispondesse un `MagicMock` farebbe passare per
    # riuscito un aggiornamento che non e' avvenuto — ed e' esattamente il caso
    # che questi test devono poter vedere.
    repo.set_stato_distinta.return_value = 1
    repo.set_stato_riga.return_value = 1
    repo.update_distinta.return_value = 1
    repo.update_riga.return_value = 1
    repo.disattiva_riga.return_value = 1
    # Le due matrici, come coppie di codici: vuote qui, la forma e' provata in
    # `test_riga_nasce_abbinata_ed_elimina`.
    repo.list_transizioni.return_value = ([], [])
    repo.get_riferimenti_fattura.return_value = {
        "fattura_id": 2263, "billing_account_id": 41,
        "emittente_soggetto_ruolo_id": 32, "cliente_soggetto_ruolo_id": 9,
    }
    for chiave, valore in over.items():
        getattr(repo, chiave).return_value = valore
    return repo


class _ServiceTestCase(TestCase):
    # Scopo: Sostituisce il repository con un doppio per ogni test.
    def setUp(self) -> None:
        self.repo = _repo()
        patcher = patch.object(
            pagamenti_service, "PagamentiRepository", return_value=self.repo
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        # ⚠️ `transaction.atomic` neutralizzato: aprire una transazione e' una
        # query vera e qui non c'e' database. E' la convenzione del progetto.
        # ⭐ Che il blocco atomico ci sia DAVVERO lo prova
        #    `AtomicitaTests.test_crea_distinta_e_una_transazione_sola`, che lo
        #    sostituisce con un doppio e ne verifica la chiamata: neutralizzare
        #    senza quel test spegnerebbe il presidio invece di aggirarlo.
        atomic_patcher = patch.object(
            pagamenti_service.transaction, "atomic", new=lambda *a, **k: nullcontext()
        )
        atomic_patcher.start()
        self.addCleanup(atomic_patcher.stop)


class CreaDistintaTests(_ServiceTestCase):
    _PAYLOAD = {"centro_riscossione_id": 39, "data_contabile": "2026-08-24"}

    # Scopo: Il backend crea SOLO distinte manuali in bozza: `GENERATA` la
    #        scrive il giro dei fondi, `AUTOMATICA` l'import.
    def test_origine_manuale_e_bozza_forzate(self):
        pagamenti_service.crea_distinta(dict(self._PAYLOAD))
        kwargs = self.repo.get_or_create_distinta.call_args.kwargs
        self.assertEqual(kwargs["origine"], "MANUALE")
        self.assertEqual(kwargs["codice_stato_interno"], "BOZZA")
        self.assertEqual(kwargs["centro_riscossione_id"], 39)
        self.assertEqual(kwargs["data_contabile"], date(2026, 8, 24))

    # Scopo: ⭐ L'operatore NON si passa: lo mette la funzione madre
    #        dall'identita' della connessione. Passarlo dal backend sarebbe una
    #        seconda verita' su chi sta lavorando.
    def test_operatore_non_viene_passato(self):
        pagamenti_service.crea_distinta(dict(self._PAYLOAD))
        kwargs = self.repo.get_or_create_distinta.call_args.kwargs
        self.assertNotIn("operatore", kwargs)
        self.assertNotIn("user_insert", kwargs)

    # Scopo: Il totale dichiarato non e' un parametro della funzione madre: si
    #        scrive dopo, come qualunque campo che una persona compila.
    def test_importo_dichiarato_scritto_a_parte(self):
        pagamenti_service.crea_distinta(
            {**self._PAYLOAD, "importo_dichiarato": "1250.50"}
        )
        self.repo.update_distinta.assert_called_once_with(
            7, {"importo_dichiarato": Decimal("1250.50")}
        )

    # Scopo: ⚠️ Il *get or create* puo' aver restituito la distinta di
    #        stamattina: se ha gia' righe la schermata deve dirlo, perche'
    #        entrarci in silenzio e' il modo in cui si registra due volte
    #        credendo di cominciare.
    def test_gia_popolata_quando_la_distinta_ha_righe(self):
        self.repo.get_distinta.return_value = _distinta(righe_totali=3)
        esito = pagamenti_service.crea_distinta(dict(self._PAYLOAD))
        self.assertTrue(esito["gia_popolata"])

    # Scopo: Senza centro non esiste una distinta — lo pretende il database, e
    #        il messaggio deve arrivare a chi compila, non al log.
    def test_centro_obbligatorio(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_distinta({"data_contabile": "2026-08-24"})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_VALIDAZIONE)

    # Scopo: Idem per la data contabile.
    def test_data_contabile_obbligatoria(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.crea_distinta({"centro_riscossione_id": 39})

    # Scopo: ⭐ L'emittente scelto nel form arriva alla madre COM'E' (D4 del
    #        brief distinta-numerata-sul-registro): e' la PK, cio' che il
    #        frontend conosce; la traduzione in soggetto-ruolo e' del database.
    def test_emittente_scelto_viene_trasportato(self):
        pagamenti_service.crea_distinta({**self._PAYLOAD, "emittente_fiscale_id": 32})
        kwargs = self.repo.get_or_create_distinta.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 32)

    # Scopo: ⛔ Senza emittente nel payload il backend passa `None` e NON lo
    #        deduce dal profilo: i quattro livelli (canale → sessione →
    #        rifiuto) vivono in `fn_get_emittente_distinta`, e un secondo
    #        risolutore qui sarebbe la seconda sede della stessa regola.
    def test_senza_emittente_passa_none_e_non_deduce(self):
        pagamenti_service.crea_distinta(dict(self._PAYLOAD))
        kwargs = self.repo.get_or_create_distinta.call_args.kwargs
        self.assertIn("emittente_fiscale_id", kwargs)
        self.assertIsNone(kwargs["emittente_fiscale_id"])

    # Scopo: Un emittente non positivo e' un dato sbagliato, e lo dice il
    #        backend prima di chiamare il database.
    def test_emittente_non_positivo_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_distinta({**self._PAYLOAD, "emittente_fiscale_id": 0})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_VALIDAZIONE)
        self.repo.get_or_create_distinta.assert_not_called()


class StatoDistintaTests(_ServiceTestCase):
    # Scopo: 🔴 `CHIUSA` non e' un gesto: la chiusura e' una CONSEGUENZA del
    #        registrare, e la scrive la funzione madre. Un pulsante «chiudi»
    #        rimetterebbe in mano a qualcuno una decisione che il database
    #        prende da se'.
    def test_chiusa_non_e_richiedibile(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.cambia_stato_distinta(7, {"nuovo_stato": "CHIUSA"})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_VALIDAZIONE)
        self.repo.set_stato_distinta.assert_not_called()

    # Scopo: I tre stati che una persona chiede davvero passano.
    def test_annullata_e_richiedibile(self):
        pagamenti_service.cambia_stato_distinta(7, {"nuovo_stato": "annullata"})
        self.repo.set_stato_distinta.assert_called_once_with(7, "ANNULLATA")

    # Scopo: Distinta inesistente (o fuori perimetro) -> 404 di dominio, e i
    #        due casi restano indistinguibili.
    def test_distinta_inesistente_404(self):
        self.repo.get_distinta.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.cambia_stato_distinta(999, {"nuovo_stato": "VALIDATA"})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_DISTINTA_NON_TROVATA)


class StatoRigaTests(_ServiceTestCase):
    # Scopo: `POSTATA` la scrive il posting, non una persona.
    def test_postata_non_e_richiedibile(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.cambia_stato_riga(11, {"nuovo_stato": "POSTATA"})
        self.repo.set_stato_riga.assert_not_called()

    # Scopo: Il motivo accompagna la sospensione NELLO STESSO GIRO e prima del
    #        cambio di stato: sospendere senza dire perche' lascia la riga in
    #        una coda dove il prossimo non sa che cosa si era gia' capito.
    def test_motivo_sospeso_scritto_prima_dello_stato(self):
        chiamate: list[str] = []
        self.repo.update_riga.side_effect = (
            lambda *a, **k: (chiamate.append("motivo"), 1)[1]
        )
        self.repo.set_stato_riga.side_effect = (
            lambda *a, **k: (chiamate.append("stato"), 1)[1]
        )
        pagamenti_service.cambia_stato_riga(
            11, {"nuovo_stato": "SOSPESA", "motivo_sospeso": "cliente non chiaro"}
        )
        self.assertEqual(chiamate, ["motivo", "stato"])


class AtomicitaTests(_ServiceTestCase):
    # Scopo: 🔴 Aprire una distinta con un totale dichiarato sono DUE scritture
    #        (la funzione madre non prende quel parametro), e devono essere UNA
    #        unita'. Una distinta nata senza il suo dichiarato e' una distinta
    #        la cui quadratura non scatta mai: il controllo esisterebbe e non
    #        direbbe niente.
    # ⚠️ `ATOMIC_REQUESTS` non e' attivo nel progetto: senza il blocco esplicito
    #    sarebbero due transazioni separate.
    def test_crea_distinta_e_una_transazione_sola(self):
        with patch.object(pagamenti_service.transaction, "atomic") as atomic:
            atomic.return_value = nullcontext()
            pagamenti_service.crea_distinta(
                {
                    "centro_riscossione_id": 39,
                    "data_contabile": "2026-08-24",
                    "importo_dichiarato": "1250.50",
                }
            )
        atomic.assert_called_once()


class StatoNonConfiguratoTests(_ServiceTestCase):
    # Scopo: 🔴 Zero righe toccate NON e' un successo silenzioso. La distinta
    #        esiste (appena letta), quindi a non risolvere e' il CODICE DI
    #        STATO: senza questo controllo la risposta sarebbe un 200 con lo
    #        stato invariato, e l'operatore leggerebbe «fatto» su un gesto che
    #        non e' avvenuto.
    def test_distinta_stato_non_a_catalogo(self):
        self.repo.set_stato_distinta.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.cambia_stato_distinta(7, {"nuovo_stato": "VALIDATA"})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_STATO_NON_CONFIGURATO)

    # Scopo: Stessa regola sulla riga.
    def test_riga_stato_non_a_catalogo(self):
        self.repo.set_stato_riga.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.cambia_stato_riga(11, {"nuovo_stato": "SCARTATA"})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_STATO_NON_CONFIGURATO)


class RegistrazioneTests(_ServiceTestCase):
    _RICEVUTA = {
        "movimenti_creati": 2,
        "righe_postate": 2,
        "righe_saltate": 1,
        "totale_postato": Decimal("300.00"),
        "esito": "POSTATA",
    }

    # Scopo: ⚠️ La dichiarazione e' facoltativa ma LEGATA. Mezza dichiarazione
    #        non si puo' verificare, e accettarla in silenzio significherebbe
    #        registrare senza controllo CREDENDO di averlo fatto.
    def test_mezza_dichiarazione_rifiutata_solo_righe(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.registra_distinta(7, {"righe_attese": 3})
        self.repo.posta_contabile.assert_not_called()

    # Scopo: L'altro verso della stessa regola.
    def test_mezza_dichiarazione_rifiutata_solo_totale(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.registra_distinta(7, {"totale_atteso": "300.00"})
        self.repo.posta_contabile.assert_not_called()

    # Scopo: La dichiarazione intera arriva al database COM'E'.
    def test_dichiarazione_intera_passa_al_database(self):
        self.repo.posta_contabile.return_value = dict(self._RICEVUTA)
        pagamenti_service.registra_distinta(
            7, {"righe_attese": 2, "totale_atteso": "300.00"}
        )
        kwargs = self.repo.posta_contabile.call_args.kwargs
        self.assertEqual(kwargs["righe_attese"], 2)
        self.assertEqual(kwargs["totale_atteso"], Decimal("300.00"))

    # Scopo: ⭐ **Zero e' una dichiarazione legittima**: l'anteprima puo'
    #        mostrare zero righe registrabili, e la coppia (0, 0) e' esattamente
    #        cio' che l'operatore ha davanti. Il database risponde
    #        `NULLA_DA_POSTARE`, che e' un esito — rifiutarla qui trasformerebbe
    #        una risposta vera in un 400 con una frase falsa.
    def test_dichiarazione_zero_e_legittima(self):
        self.repo.posta_contabile.return_value = dict(self._RICEVUTA)
        pagamenti_service.registra_distinta(
            7, {"righe_attese": 0, "totale_atteso": "0"}
        )
        kwargs = self.repo.posta_contabile.call_args.kwargs
        self.assertEqual(kwargs["righe_attese"], 0)
        self.assertEqual(kwargs["totale_atteso"], Decimal("0"))

    # Scopo: Senza dichiarazione si registra cio' che c'e' — e' la strada dei
    #        processi automatici, che non hanno un operatore che guarda.
    def test_senza_dichiarazione_passa_none(self):
        self.repo.posta_contabile.return_value = dict(self._RICEVUTA)
        pagamenti_service.registra_distinta(7, {})
        kwargs = self.repo.posta_contabile.call_args.kwargs
        self.assertIsNone(kwargs["righe_attese"])
        self.assertIsNone(kwargs["totale_atteso"])

    # Scopo: 🔴 «Niente da registrare» NON e' un errore. Se il backend lo
    #        trasformasse in uno, il database scriverebbe nel registro degli
    #        errori un errore che non e' un errore — ed e' la ragione esatta
    #        per cui la funzione madre non solleva.
    def test_nulla_da_postare_non_e_un_errore(self):
        self.repo.posta_contabile.return_value = {
            **self._RICEVUTA,
            "movimenti_creati": 0,
            "righe_postate": 0,
            "totale_postato": Decimal("0"),
            "esito": "NULLA_DA_POSTARE",
        }
        ricevuta = pagamenti_service.registra_distinta(7, {})
        self.assertEqual(ricevuta["esito"], "NULLA_DA_POSTARE")


class CorrezioneGuidataTests(_ServiceTestCase):
    """Q-7 — la correzione guidata: da una distinta registrata ne nasce una
    nuova, con le righe di segno opposto gia' compilate."""

    _CREATA = {
        "contabile_id": 42,
        "righe_create": 3,
        "righe_saltate": 1,
        "esito": "CREATA",
    }
    _NULLA = {
        "contabile_id": None,
        "righe_create": 0,
        "righe_saltate": 2,
        "esito": "NULLA_DA_CORREGGERE",
    }

    # Scopo: Il gesto arriva alla madre con i suoi parametri, e basta.
    # ⭐ Le tre regole (solo il registrato, una correzione per documento, le
    #    righe non postate si saltano) stanno TUTTE nella funzione: il service
    #    che le ricopiasse sarebbe una seconda sede che diverge al primo cambio.
    def test_chiama_la_madre_coi_parametri(self):
        self.repo.crea_distinta_correzione.return_value = dict(self._CREATA)
        pagamenti_service.correggi_distinta(
            7, {"data_contabile": "2026-09-01", "motivo": "importo digitato male"}
        )
        kwargs = self.repo.crea_distinta_correzione.call_args.kwargs
        self.assertEqual(kwargs["contabile_id"], 7)
        self.assertEqual(kwargs["data_contabile"], date(2026, 9, 1))
        self.assertEqual(kwargs["motivo"], "importo digitato male")

    # ⚠️ Senza data non si inventa un default QUI: lo mette la madre
    #    (`CURRENT_DATE`). Due default sulla stessa cosa divergono al primo
    #    cambio, e il secondo nessuno lo va a cercare.
    def test_senza_data_non_si_inventa_un_default(self):
        self.repo.crea_distinta_correzione.return_value = dict(self._CREATA)
        pagamenti_service.correggi_distinta(7, {})
        self.assertIsNone(self.repo.crea_distinta_correzione.call_args.kwargs["data_contabile"])

    # Scopo: Creata -> si rilegge la distinta NUOVA, non quella di partenza:
    #        e' quella che l'operatore deve aprire per lavorarci.
    def test_creata_rilegge_la_distinta_nuova(self):
        self.repo.crea_distinta_correzione.return_value = dict(self._CREATA)
        esito = pagamenti_service.correggi_distinta(7, {})
        self.assertEqual(esito["esito"]["esito"], "CREATA")
        self.assertIsNotNone(esito["distinta"])
        self.repo.get_distinta.assert_called_with(42)

    # Scopo: 🔴 «Niente da correggere» NON e' un errore, ed e' la stessa regola
    #        di `NULLA_DA_POSTARE`: e' un esito, e risale intatto.
    # ⛔ E non si rilegge nessun dettaglio: `contabile_id` e' NULL perche' non e'
    #    stata creata nessuna distinta — cercarla sarebbe un 404 su un esito
    #    legittimo, cioe' un errore inventato dal backend.
    def test_nulla_da_correggere_non_e_un_errore(self):
        self.repo.crea_distinta_correzione.return_value = dict(self._NULLA)
        esito = pagamenti_service.correggi_distinta(7, {})
        self.assertEqual(esito["esito"]["esito"], "NULLA_DA_CORREGGERE")
        self.assertIsNone(esito["distinta"])
        # ⚠️ `get_distinta` viene chiamata UNA volta sola: il 404 di dominio
        #    sulla distinta di partenza. Mai una seconda su un id che non c'e'.
        self.assertEqual(self.repo.get_distinta.call_count, 1)

    # ⚠️ Le righe SALTATE risalgono: una riga non postata non ha prodotto
    #    movimenti e non c'e' niente da correggere — ma il silenzio lascia
    #    l'operatore a chiedersi dove sia finita.
    def test_le_righe_saltate_risalgono(self):
        self.repo.crea_distinta_correzione.return_value = dict(self._CREATA)
        esito = pagamenti_service.correggi_distinta(7, {})
        self.assertEqual(esito["esito"]["righe_saltate"], 1)

    # ⛔ Vocabolario chiuso: una chiave inventata e' un rifiuto, non un campo
    #    ignorato in silenzio.
    def test_chiave_estranea_rifiutata(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.correggi_distinta(7, {"forzata": True})
        self.repo.crea_distinta_correzione.assert_not_called()


class ImportiTests(_ServiceTestCase):
    _PAYLOAD = {"centro_riscossione_id": 39, "data_contabile": "2026-08-24"}

    # Scopo: ⚠️ Un importo passa sempre da `str`: `Decimal(0.1)` porterebbe
    #        dentro l'errore del float, e su del denaro quell'errore poi si
    #        somma.
    def test_float_non_perde_precisione(self):
        pagamenti_service.crea_distinta({**self._PAYLOAD, "importo_dichiarato": 0.1})
        campi = self.repo.update_distinta.call_args.args[1]
        self.assertEqual(campi["importo_dichiarato"], Decimal("0.1"))

    # Scopo: Una stringa che non e' un numero e' un errore di chi compila.
    def test_stringa_non_numerica_rifiutata(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.crea_distinta(
                {**self._PAYLOAD, "importo_dichiarato": "mille"}
            )

    # Scopo: ⚠️ `NaN` si costruisce senza protestare e arriverebbe fino alla
    #        colonna numeric, dove ogni somma che lo incontra diventa NaN — e un
    #        totale NaN non si vede: si legge come un campo vuoto.
    def test_nan_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.crea_distinta(
                {**self._PAYLOAD, "importo_dichiarato": "NaN"}
            )

    # Scopo: Idem per l'infinito.
    def test_infinito_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.crea_distinta(
                {**self._PAYLOAD, "importo_dichiarato": float("inf")}
            )

    # Scopo: `True` non e' un importo, anche se Python lo sommerebbe.
    def test_booleano_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.crea_distinta(
                {**self._PAYLOAD, "importo_dichiarato": True}
            )


class PatchTests(_ServiceTestCase):
    # Scopo: ⛔ Il PATCH della riga porta i FATTI, non l'abbinamento: quello e'
    #        un verbo, perche' porta con se' la rata e la forzatura ed e' una
    #        decisione — non la correzione di un dato digitato male.
    def test_riga_non_accetta_abbinamento(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.aggiorna_riga(11, {"fattura_id": 2263})
        self.repo.update_riga.assert_not_called()

    # Scopo: ⛔ Un PATCH che non nomina nessun campo e' un 400 (Tid,
    #        2026-10-20, §A2), e non scrive niente.
    def test_patch_vuoto_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.aggiorna_riga(11, {})
        self.repo.update_riga.assert_not_called()


class ListaTests(_ServiceTestCase):
    # Scopo: ⛔ L'ordinamento entra in una clausola SQL: solo la whitelist
    #        passa, e cio' che non c'e' e' un 400, non un default silenzioso.
    def test_ordinamento_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.list_distinte(order_by="importo_dichiarato; DROP")
        self.repo.list_distinte.assert_not_called()

    # Scopo: Stessa regola sulle righe di una distinta (lista
    #        `pagamenti.distinta_righe`, 2026-09-18): fuori whitelist e' un 400
    #        col campo, non un default silenzioso — e non un 500 sull'ORDER BY.
    def test_righe_della_distinta_ordinamento_fuori_whitelist_rifiutato(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.list_righe(7, limit=25, order_by="meta; DROP")
        self.repo.list_righe_distinta.assert_not_called()

    # Scopo: «non specificato» e' legittimo e arriva al repository come `None`
    #        (che apre `id DESC`), e il `count` e' il totale che il repository
    #        dichiara — non `len(results)`, che fino al 18/09 era un'eco.
    def test_righe_della_distinta_senza_ordinamento_e_un_none_e_un_conteggio_vero(self):
        self.repo.list_righe_distinta.return_value = ([{"id": 91}], 340)
        self.repo.count_righe_in_stato.return_value = 2
        esito = pagamenti_service.list_righe(7, limit=1, offset=0)
        self.assertEqual(
            esito, {"count": 340, "results": [{"id": 91}], "scartate_count": 2}
        )
        kwargs = self.repo.list_righe_distinta.call_args.kwargs
        self.assertIsNone(kwargs["order_by"])
        self.assertIsNone(kwargs["order_dir"])
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (1, 0))

    # Scopo: ⭐ BE-2 (D20-c): di default le SCARTATA restano FUORI dalla lista —
    #        il repository riceve lo stato da escludere — e la risposta dichiara
    #        quante ne nasconde, contate sullo stesso perimetro. A interruttore
    #        acceso non si esclude niente e il conteggio non si paga.
    def test_le_scartate_sono_fuori_di_default_e_contate(self):
        self.repo.list_righe_distinta.return_value = ([], 0)
        self.repo.count_righe_in_stato.return_value = 3
        esito = pagamenti_service.list_righe(7, limit=25)
        self.assertEqual(
            self.repo.list_righe_distinta.call_args.kwargs["escludi_stato_codice"],
            pagamenti_service.STATO_RIGA_SCARTATA,
        )
        self.repo.count_righe_in_stato.assert_called_once_with(
            7, pagamenti_service.STATO_RIGA_SCARTATA
        )
        self.assertEqual(esito["scartate_count"], 3)

        self.repo.reset_mock()
        self.repo.list_righe_distinta.return_value = ([], 0)
        esito = pagamenti_service.list_righe(7, limit=25, scartate=True)
        self.assertIsNone(
            self.repo.list_righe_distinta.call_args.kwargs["escludi_stato_codice"]
        )
        self.repo.count_righe_in_stato.assert_not_called()
        self.assertEqual(esito["scartate_count"], 0)

    # Scopo: ⛔ Il dettaglio NON legge piu' le righe (dal 2026-09-18): sono la
    #        lista paginata. Leggerle qui sarebbe la LATERAL per riga due volte
    #        a ogni apertura del drawer, per un campo che nessuno legge.
    def test_il_dettaglio_non_porta_piu_le_righe(self):
        dettaglio = pagamenti_service.get_distinta(7)
        self.assertNotIn("righe", dettaglio)
        self.repo.list_righe.assert_not_called()
