# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del seguito del primo collaudo in-app (brief D16/D17/D18,
#        2026-09-14): la riga manuale nasce con la destinazione, si elimina in
#        bozza, e le transizioni offerte vengono dalla matrice.
# Note: ⚠️ Come per le altre slice: qui NON si riverificano i guard del
#       database (contenuto sotto VALIDATA, motivi dell'eliminazione, capienza
#       sull'INSERT). Si prova cio' che il backend decide da se' — lo stato di
#       nascita, la forma della destinazione, il 404 di una riga eliminata —
#       e cio' che il backend NON deve decidere.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  NascitaTests.test_con_la_fattura_nasce_abbinata_in_un_insert_solo
2)  NascitaTests.test_senza_fattura_nasce_da_abbinare
3)  NascitaTests.test_rata_senza_fattura_rifiutata
4)  NascitaTests.test_forzatura_senza_fattura_rifiutata
5)  NascitaTests.test_cliente_senza_fattura_rifiutato
6)  NascitaTests.test_motivo_senza_forzatura_rifiutato
7)  NascitaTests.test_cliente_derivato_dalla_fattura_se_assente
8)  NascitaTests.test_cliente_dichiarato_non_si_rilegge
9)  NascitaTests.test_fattura_inesistente_404_prima_dell_insert
10) NascitaTests.test_primo_tentativo_non_e_forzato
11) NascitaTests.test_il_backend_non_decide_la_capienza_nemmeno_alla_nascita
12) NascitaTests.test_i_fatti_restano_quelli_di_prima
13) EliminazioneTests.test_riga_assente_404_senza_scrivere
14) EliminazioneTests.test_elimina_disattiva_e_risponde
15) EliminazioneTests.test_eliminata_da_altri_nel_frattempo_404
16) EliminazioneTests.test_nessun_predicato_in_python
17) ContenutoModificabileTests.test_vero_solo_su_manuale_in_bozza
18) TransizioniTests.test_ristrette_ai_richiedibili_sull_arrivo
19) TransizioniTests.test_lo_stato_di_partenza_non_deve_essere_richiedibile
20) TransizioniTests.test_ordine_del_vocabolario_e_senza_doppioni
21) TransizioniTests.test_il_dettaglio_porta_le_due_mappe_e_non_il_vocabolario
22) TransizioniTests.test_stato_info_key_passa_intatta
23) ModificaTests.test_forzatura_e_motivo_passano_intatti_col_fatto
24) ModificaTests.test_motivo_senza_forzatura_rifiutato_anche_in_modifica
25) ModificaTests.test_senza_forzatura_nel_payload_non_si_scrive
26) ModificaTests.test_forzata_null_torna_al_default
27) ModificaTests.test_la_destinazione_resta_fuori_dal_patch
"""

import inspect
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.services import pagamenti_service

_FATTI = {"importo": "400.00", "data_pagamento": "2026-09-14", "riferimento_ente": "CRO 1"}
_DESTINAZIONE = {"fattura_id": 2263, "billing_account_id": 41, "scadenza_id": 900}
_RIFERIMENTI = {
    "fattura_id": 2263, "billing_account_id": 41,
    "emittente_soggetto_ruolo_id": 32, "cliente_soggetto_ruolo_id": 9,
}


def _distinta(**over):
    riga = {
        "id": 7, "codice": "CNT-0001", "stato_codice": "BOZZA", "origine": "MANUALE",
        "stato_info_key": None, "righe_totali": 0, "righe_registrabili": 0,
        "totale_righe": Decimal("0"), "totale_registrabile": Decimal("0"),
        "importo_dichiarato": None, "scarto_dichiarato": None,
    }
    riga.update(over)
    return riga


def _repo() -> MagicMock:
    repo = MagicMock()
    repo.get_distinta.return_value = _distinta()
    repo.get_riga.return_value = {"id": 11, "contabile_id": 7, "attivo": True}
    repo.create_riga.return_value = 11
    repo.disattiva_riga.return_value = 1
    repo.get_riferimenti_fattura.return_value = dict(_RIFERIMENTI)
    repo.list_righe.return_value = []
    repo.list_stati_distinta.return_value = []
    repo.list_stati_riga.return_value = []
    repo.list_transizioni.return_value = ([], [])
    return repo


class _Base(SimpleTestCase):
    # Scopo: Sostituisce il repository con un doppio per ogni test.
    def setUp(self) -> None:
        self.repo = _repo()
        patcher = patch.object(
            pagamenti_service, "PagamentiRepository", return_value=self.repo
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class NascitaTests(_Base):
    # Scopo: ⭐ D16 — con la fattura la riga nasce ABBINATA, e fattura, cliente,
    #        rata e forzatura entrano nello STESSO INSERT dei fatti: non c'e'
    #        nessun `abbina` dopo.
    def test_con_la_fattura_nasce_abbinata_in_un_insert_solo(self):
        pagamenti_service.crea_riga(7, {**_FATTI, **_DESTINAZIONE})
        kwargs = self.repo.create_riga.call_args.kwargs
        self.assertEqual(kwargs["codice_stato_interno"], "ABBINATA")
        self.assertEqual(kwargs["fattura_id"], 2263)
        self.assertEqual(kwargs["billing_account_id"], 41)
        self.assertEqual(kwargs["scadenza_id"], 900)
        self.repo.abbina_riga.assert_not_called()
        self.repo.update_riga.assert_not_called()

    # Scopo: Senza fattura la riga nasce DA_ABBINARE — l'eccezione che
    #        l'operatore dichiara — e i campi della destinazione sono vuoti.
    def test_senza_fattura_nasce_da_abbinare(self):
        pagamenti_service.crea_riga(7, dict(_FATTI))
        kwargs = self.repo.create_riga.call_args.kwargs
        self.assertEqual(kwargs["codice_stato_interno"], "DA_ABBINARE")
        self.assertIsNone(kwargs["fattura_id"])
        self.assertIsNone(kwargs["billing_account_id"])
        self.assertIsNone(kwargs["scadenza_id"])
        self.assertFalse(kwargs["forzata"])
        self.repo.get_riferimenti_fattura.assert_not_called()

    # Scopo: Una rata senza fattura non e' un'eccezione dichiarata: e' un
    #        payload rotto, e si dice quale campo.
    def test_rata_senza_fattura_rifiutata(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_riga(7, {**_FATTI, "scadenza_id": 900})
        self.assertEqual(ctx.exception.context.get("field"), "scadenza_id")
        self.repo.create_riga.assert_not_called()

    def test_forzatura_senza_fattura_rifiutata(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_riga(7, {**_FATTI, "forzata": True})
        self.assertEqual(ctx.exception.context.get("field"), "forzata")
        self.repo.create_riga.assert_not_called()

    def test_cliente_senza_fattura_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_riga(7, {**_FATTI, "billing_account_id": 41})
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")
        self.repo.create_riga.assert_not_called()

    # Scopo: La regola di `abbina` vale identica alla nascita: e' la stessa
    #        lettura (`_destinazione_da_payload`), non una copia.
    def test_motivo_senza_forzatura_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_riga(
                7, {**_FATTI, **_DESTINAZIONE, "motivo_forzatura": "perche' si'"}
            )
        self.assertEqual(ctx.exception.context.get("field"), "motivo_forzatura")
        self.repo.create_riga.assert_not_called()

    # Scopo: Il cliente, se non lo dice chi chiama, e' quello della fattura —
    #        LETTO dal documento, non dedotto.
    def test_cliente_derivato_dalla_fattura_se_assente(self):
        pagamenti_service.crea_riga(7, {**_FATTI, "fattura_id": 2263})
        self.repo.get_riferimenti_fattura.assert_called_once_with(2263)
        self.assertEqual(self.repo.create_riga.call_args.kwargs["billing_account_id"], 41)

    def test_cliente_dichiarato_non_si_rilegge(self):
        pagamenti_service.crea_riga(7, {**_FATTI, **_DESTINAZIONE})
        self.repo.get_riferimenti_fattura.assert_not_called()

    # Scopo: Una fattura che non c'e' (o che il perimetro non lascia vedere)
    #        ferma tutto PRIMA dell'INSERT, col codice di dominio e il campo.
    def test_fattura_inesistente_404_prima_dell_insert(self):
        self.repo.get_riferimenti_fattura.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_riga(7, {**_FATTI, "fattura_id": 999999})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_FATTURA_NON_TROVATA)
        self.assertEqual(ctx.exception.context.get("field"), "fattura_id")
        self.repo.create_riga.assert_not_called()

    # Scopo: Il PRIMO tentativo non e' forzato, anche alla nascita: e' il
    #        rifiuto che ne segue a far nascere la domanda all'operatore.
    def test_primo_tentativo_non_e_forzato(self):
        pagamenti_service.crea_riga(7, {**_FATTI, **_DESTINAZIONE})
        self.assertFalse(self.repo.create_riga.call_args.kwargs["forzata"])

    # Scopo: 🔴 Il backend NON sa che cosa sia forzabile: la capienza la giudica
    #        il guard del database sull'INSERT come sull'UPDATE. Una seconda
    #        sede della regola divergerebbe dalla prima al primo cambiamento.
    def test_il_backend_non_decide_la_capienza_nemmeno_alla_nascita(self):
        for funzione in (
            pagamenti_service.crea_riga,
            pagamenti_service.aggiorna_riga,
            pagamenti_service._destinazione_da_payload,
        ):
            sorgente = inspect.getsource(funzione)
            for parola in ("capienza", "saldo", "residuo", "importo <"):
                self.assertNotIn(
                    parola, sorgente,
                    f"{funzione.__name__} sta valutando la capienza ({parola}): la decide il DB",
                )

    # Scopo: I fatti passano come prima: la destinazione si AGGIUNGE, non
    #        sostituisce niente.
    def test_i_fatti_restano_quelli_di_prima(self):
        pagamenti_service.crea_riga(7, {**_FATTI, **_DESTINAZIONE})
        kwargs = self.repo.create_riga.call_args.kwargs
        self.assertEqual(kwargs["importo"], Decimal("400.00"))
        self.assertEqual(kwargs["riferimento_ente"], "CRO 1")
        self.assertEqual(str(kwargs["data_pagamento"]), "2026-09-14")


class EliminazioneTests(_Base):
    # Scopo: Una riga che non c'e' (o che e' gia' stata eliminata: `get_riga`
    #        filtra `attivo`) risponde 404 senza scrivere niente.
    def test_riga_assente_404_senza_scrivere(self):
        self.repo.get_riga.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.elimina_riga(11)
        self.assertEqual(ctx.exception.code, pagamenti_service.E_RIGA_NON_TROVATA)
        self.repo.disattiva_riga.assert_not_called()

    # Scopo: ⭐ D17 — eliminare e' `attivo = false`, e la risposta lo dice.
    def test_elimina_disattiva_e_risponde(self):
        esito = pagamenti_service.elimina_riga(11)
        self.repo.disattiva_riga.assert_called_once_with(11)
        self.assertEqual(esito, {"riga_id": 11, "eliminata": True})

    # Scopo: Letta attiva un istante fa e zero righe toccate = qualcun altro
    #        l'ha eliminata nel frattempo. Per chi chiede e' «non c'e'».
    def test_eliminata_da_altri_nel_frattempo_404(self):
        self.repo.disattiva_riga.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.elimina_riga(11)
        self.assertEqual(ctx.exception.code, pagamenti_service.E_RIGA_NON_TROVATA)

    # Scopo: ⛔ Chi puo' eliminare lo dice `script.fn_check_riga_contabile_eliminabile`
    #        attraverso il guard: il service non guarda ne' l'origine ne' lo
    #        stato della distinta. Se lo facesse, cestino e rifiuto avrebbero
    #        due sedi.
    def test_nessun_predicato_in_python(self):
        sorgente = inspect.getsource(pagamenti_service.elimina_riga)
        for parola in ("MANUALE", "BOZZA", "VALIDATA", "origine", "is_final"):
            self.assertNotIn(parola, sorgente, f"predicato copiato in Python: {parola}")


class ContenutoModificabileTests(_Base):
    # Scopo: D17/D18 — il contenuto si lavora solo su una MANUALE in BOZZA. Le
    #        quattro combinazioni, non una: e' una copia dichiarata del motivo 3
    #        della check, e va provata per intero.
    def test_vero_solo_su_manuale_in_bozza(self):
        casi = {
            ("BOZZA", "MANUALE"): True,
            ("VALIDATA", "MANUALE"): False,
            ("BOZZA", "GENERATA"): False,
            ("VALIDATA", "GENERATA"): False,
            ("CHIUSA", "MANUALE"): False,
        }
        for (stato, origine), atteso in casi.items():
            with self.subTest(stato=stato, origine=origine):
                self.repo.get_distinta.return_value = _distinta(
                    stato_codice=stato, origine=origine
                )
                dettaglio = pagamenti_service.get_distinta(7)
                self.assertIs(dettaglio["distinta"]["contenuto_modificabile"], atteso)


class TransizioniTests(_Base):
    _GRAFO_RIGA = [
        ("DA_ABBINARE", "ABBINATA"), ("DA_ABBINARE", "SOSPESA"), ("DA_ABBINARE", "SCARTATA"),
        ("ABBINATA", "POSTATA"), ("ABBINATA", "DA_ABBINARE"), ("ABBINATA", "SOSPESA"),
        ("SOSPESA", "ABBINATA"), ("SOSPESA", "DA_ABBINARE"), ("SOSPESA", "SCARTATA"),
        ("SCARTATA", "SOSPESA"),
        ("IMPORTATA", "DA_ABBINARE"),
    ]

    # Scopo: ⭐ BE-5 — cio' che si offre viene dalla MATRICE, ristretta sullo
    #        stato di ARRIVO a cio' che una persona puo' chiedere: `POSTATA` la
    #        scrive la registrazione e non compare mai fra le uscite.
    def test_ristrette_ai_richiedibili_sull_arrivo(self):
        ammesse = pagamenti_service._transizioni_richiedibili(
            self._GRAFO_RIGA, pagamenti_service.STATI_RIGA_RICHIEDIBILI
        )
        self.assertEqual(ammesse["ABBINATA"], ["DA_ABBINARE", "SOSPESA"])
        self.assertNotIn("POSTATA", ammesse["ABBINATA"])
        # Il difetto del collaudo: SCARTATA non si propone su ABBINATA.
        self.assertNotIn("SCARTATA", ammesse["ABBINATA"])
        self.assertEqual(ammesse["SCARTATA"], ["SOSPESA"])

    # Scopo: Lo stato di PARTENZA non e' filtrato: da `IMPORTATA` — che nessuno
    #        chiede — si esce eccome, e la mappa deve saperlo dire.
    def test_lo_stato_di_partenza_non_deve_essere_richiedibile(self):
        ammesse = pagamenti_service._transizioni_richiedibili(
            self._GRAFO_RIGA, pagamenti_service.STATI_RIGA_RICHIEDIBILI
        )
        self.assertEqual(ammesse["IMPORTATA"], ["DA_ABBINARE"])

    # Scopo: L'ordine e' quello del vocabolario (stabile fra una lettura e
    #        l'altra), e una coppia ripetuta non produce un doppione.
    def test_ordine_del_vocabolario_e_senza_doppioni(self):
        grafo = [("SOSPESA", "SCARTATA"), ("SOSPESA", "ABBINATA"), ("SOSPESA", "ABBINATA")]
        ammesse = pagamenti_service._transizioni_richiedibili(
            grafo, pagamenti_service.STATI_RIGA_RICHIEDIBILI
        )
        self.assertEqual(ammesse["SOSPESA"], ["ABBINATA", "SCARTATA"])

    # Scopo: Il dettaglio porta le DUE mappe — testata e riga — e NON porta piu'
    #        il vocabolario nudo: due liste per la stessa cosa divergono.
    def test_il_dettaglio_porta_le_due_mappe_e_non_il_vocabolario(self):
        self.repo.list_transizioni.return_value = (
            [("BOZZA", "VALIDATA"), ("BOZZA", "ANNULLATA"), ("VALIDATA", "CHIUSA"),
             ("VALIDATA", "BOZZA"), ("VALIDATA", "ANNULLATA")],
            self._GRAFO_RIGA,
        )
        dettaglio = pagamenti_service.get_distinta(7)
        self.assertEqual(dettaglio["transizioni"]["distinta"]["BOZZA"], ["VALIDATA", "ANNULLATA"])
        self.assertEqual(dettaglio["transizioni"]["distinta"]["VALIDATA"], ["BOZZA", "ANNULLATA"])
        self.assertNotIn("CHIUSA", dettaglio["transizioni"]["distinta"]["VALIDATA"])
        self.assertEqual(dettaglio["transizioni"]["riga"]["ABBINATA"], ["DA_ABBINARE", "SOSPESA"])
        self.assertNotIn("stati_richiedibili", dettaglio)

    # Scopo: La chiave della riga di stato (FE-9) viaggia INTATTA dal `meta`
    #        dello stato al dettaglio: il backend trasporta, non traduce.
    #        ⚠️ Non si asserisce che sia NULL: sarebbe il test che tiene fuori
    #        il dato il giorno in cui il seed arriva.
    def test_stato_info_key_passa_intatta(self):
        self.repo.get_distinta.return_value = _distinta(
            stato_info_key="pagamenti.distinte.stato_info.bozza"
        )
        dettaglio = pagamenti_service.get_distinta(7)
        self.assertEqual(
            dettaglio["distinta"]["stato_info_key"], "pagamenti.distinte.stato_info.bozza"
        )


class ModificaTests(_Base):
    # Scopo: ⭐ Q-H (decisione di Tid, 2026-09-15) — il SECONDO TEMPO vale anche
    #        in modifica: `forzata` e il motivo arrivano al repository INTATTI,
    #        nello stesso UPDATE del fatto che li ha resi necessari.
    def test_forzatura_e_motivo_passano_intatti_col_fatto(self):
        pagamenti_service.aggiorna_riga(
            11, {"importo": "900.00", "forzata": True, "motivo_forzatura": "pagato doppio"}
        )
        campi = self.repo.update_riga.call_args.args[1]
        self.assertEqual(campi["importo"], Decimal("900.00"))
        self.assertIs(campi["forzata"], True)
        self.assertEqual(campi["motivo_forzatura"], "pagato doppio")

    # Scopo: La regola della nascita vale identica: e' la stessa funzione
    #        (`_guard_motivo_con_forzatura`), non una copia.
    def test_motivo_senza_forzatura_rifiutato_anche_in_modifica(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.aggiorna_riga(
                11, {"importo": "900.00", "motivo_forzatura": "perche' si'"}
            )
        self.assertEqual(ctx.exception.context.get("field"), "motivo_forzatura")
        self.repo.update_riga.assert_not_called()

    # Scopo: Il primo tentativo non tocca la forzatura: se il payload non la
    #        nomina, non si scrive — e la riga resta com'era.
    def test_senza_forzatura_nel_payload_non_si_scrive(self):
        pagamenti_service.aggiorna_riga(11, {"importo": "900.00"})
        campi = self.repo.update_riga.call_args.args[1]
        self.assertNotIn("forzata", campi)
        self.assertNotIn("motivo_forzatura", campi)

    # Scopo: `null` su una colonna NOT NULL vale «torna al default»: falso, e
    #        il guard del database rivaluta da se'.
    def test_forzata_null_torna_al_default(self):
        pagamenti_service.aggiorna_riga(11, {"forzata": None})
        self.assertIs(self.repo.update_riga.call_args.args[1]["forzata"], False)

    # Scopo: ⛔ R-6 resta intero: la DESTINAZIONE non passa dal PATCH.
    def test_la_destinazione_resta_fuori_dal_patch(self):
        for campo in ("fattura_id", "billing_account_id", "scadenza_id"):
            with self.subTest(campo=campo), self.assertRaises(ServiceError):
                pagamenti_service.aggiorna_riga(11, {campo: 1})
        self.repo.update_riga.assert_not_called()
