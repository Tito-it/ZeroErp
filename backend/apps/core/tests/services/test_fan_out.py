# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `run_fan_out` (fan-out isolato): esito a tre stati,
#        savepoint per item, diario opzionale e aggancio `on_success`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FanOutEsitoTests.test_lista_vuota_e_completato
2) FanOutEsitoTests.test_tutti_ok_e_completato
3) FanOutEsitoTests.test_misto_e_parziale
4) FanOutEsitoTests.test_tutti_falliti_e_errore
5) RunFanOutTests.test_processa_ogni_item_nell_ordine
6) RunFanOutTests.test_raccoglie_i_risultati_degli_item_riusciti
7) RunFanOutTests.test_un_item_fallito_non_ferma_gli_altri
8) RunFanOutTests.test_errore_porta_indice_item_e_messaggio_normalizzato
8-bis) RunFanOutTests.test_errore_porta_l_eccezione_intera_anche_dal_savepoint
9) RunFanOutTests.test_savepoint_aperto_per_ogni_item
10) RunFanOutTests.test_nessun_savepoint_se_isolamento_disattivato
11) RunFanOutTests.test_run_logger_riceve_start_item_failed_end
12) RunFanOutTests.test_run_logger_parziale_non_richiede_tutti_i_metodi
13) RunFanOutTests.test_run_logger_rotto_non_affonda_il_giro
14) RunFanOutTests.test_items_generatore_materializzato_una_sola_volta
15) OnSuccessTests.test_chiamato_solo_per_gli_item_riusciti
16) OnSuccessTests.test_chiamato_dopo_il_rilascio_del_savepoint
17) OnSuccessTests.test_effetto_visibile_all_item_successivo
18) OnSuccessTests.test_eccezione_interrompe_il_giro_e_non_diventa_item_fallito
"""

import unittest
from unittest.mock import MagicMock, patch

from apps.core.services.fan_out import (
    ESITO_COMPLETATO,
    ESITO_ERRORE,
    ESITO_PARZIALE,
    FanOutEsito,
    FanOutItemErrore,
    run_fan_out,
)


class FanOutEsitoTests(unittest.TestCase):
    # Scopo: Costruisce un esito con N successi e M errori, per i soli test
    #        delle proprieta' aggregate (senza passare dal giro).
    def _esito(self, ok=0, ko=0):
        return FanOutEsito(
            totale=ok + ko,
            risultati=[None] * ok,
            errori=[
                FanOutItemErrore(indice=i, item=i, messaggio="boom", eccezione=RuntimeError("boom"))
                for i in range(ko)
            ],
        )

    # Scopo: ⚠️ La lista vuota e' un SUCCESSO — "niente da fare" non e' un
    #        errore. E' la differenza dichiarata rispetto a `_compute_stato`
    #        del push, che sulla lista vuota risponde ERRORE perche' li' vuol
    #        dire "nessun handler risolto", cioe' configurazione sbagliata.
    def test_lista_vuota_e_completato(self):
        esito = self._esito()
        self.assertEqual(esito.esito, ESITO_COMPLETATO)
        self.assertFalse(esito.parziale)

    # Scopo: Verifica il caso `test_tutti_ok_e_completato`.
    def test_tutti_ok_e_completato(self):
        esito = self._esito(ok=3)
        self.assertEqual(esito.esito, ESITO_COMPLETATO)
        self.assertEqual(esito.ok, 3)
        self.assertEqual(esito.falliti, 0)

    # Scopo: ⚠️ IL CASO CHE CONTA — alcuni passano, altri no: e' PARZIALE, che
    #        non e' ne' successo ne' fallimento. Il difetto storico del pull era
    #        proprio non avere questa terza parola.
    def test_misto_e_parziale(self):
        esito = self._esito(ok=2, ko=1)
        self.assertEqual(esito.esito, ESITO_PARZIALE)
        self.assertTrue(esito.parziale)
        self.assertEqual(esito.totale, 3)

    # Scopo: nessun item passato = ERRORE, e NON parziale. ⚠️ Si asserisce
    #        `esito`, non un alias: l'accessore `tutti_falliti` e' stato tolto il
    #        2026-09-07 insieme al suo unico lettore (P-5 di
    #        brief-db-esito-gruppo-lotto). Il fatto e' rimasto dov'era.
    def test_tutti_falliti_e_errore(self):
        esito = self._esito(ko=2)
        self.assertEqual(esito.esito, ESITO_ERRORE)
        self.assertFalse(esito.parziale)
        self.assertEqual(esito.messaggi_errore(), ["boom", "boom"])


@patch("apps.core.services.fan_out.transaction")
class RunFanOutTests(unittest.TestCase):
    # Scopo: Verifica il caso `test_processa_ogni_item_nell_ordine`.
    def test_processa_ogni_item_nell_ordine(self, _mock_txn):
        visti = []
        esito = run_fan_out([1, 2, 3], visti.append)
        self.assertEqual(visti, [1, 2, 3])
        self.assertEqual(esito.esito, ESITO_COMPLETATO)

    # Scopo: I valori restituiti da `process` sono raccolti in ordine: e' cio'
    #        che permette al chiamante di applicare gli effetti "solo se e'
    #        andata bene" FUORI dal savepoint.
    def test_raccoglie_i_risultati_degli_item_riusciti(self, _mock_txn):
        esito = run_fan_out([1, 2, 3], lambda x: x * 10)
        self.assertEqual(esito.risultati, [10, 20, 30])

    # Scopo: ⚠️ L'isolamento — l'item rotto non impedisce ai successivi di
    #        girare, e i precedenti restano validi.
    def test_un_item_fallito_non_ferma_gli_altri(self, _mock_txn):
        def process(x):
            if x == 2:
                raise RuntimeError("ko")
            return x

        esito = run_fan_out([1, 2, 3], process)
        self.assertEqual(esito.risultati, [1, 3])
        self.assertEqual(esito.falliti, 1)
        self.assertEqual(esito.esito, ESITO_PARZIALE)

    # Scopo: L'errore porta con se' POSIZIONE e ITEM originale, non solo il
    #        testo: senza, il chiamante non puo' dire QUALE entita' e' rimasta
    #        indietro — che e' l'unica informazione che serve per ritentarla.
    def test_errore_porta_indice_item_e_messaggio_normalizzato(self, _mock_txn):
        def process(x):
            raise ValueError("dettaglio")

        esito = run_fan_out(["a"], process)
        errore = esito.errori[0]
        self.assertEqual(errore.indice, 0)
        self.assertEqual(errore.item, "a")
        self.assertEqual(errore.messaggio, "ValueError: dettaglio")

    # Scopo: ⭐ L'errore porta l'ECCEZIONE INTERA, la stessa istanza sollevata
    #        (regola del 2, 2026-09-17): chi risponde un esito per riga vuole il
    #        `ServiceError` com'e' — codice, campo, `ui_action` — non la stringa.
    #        E la porta ANCHE quando nasce fuori da `process`, dal savepoint
    #        stesso: e' il caso che i dizionari laterali dei consumatori non
    #        vedevano, e la ragione per cui il campo sta nel BB.
    def test_errore_porta_l_eccezione_intera_anche_dal_savepoint(self, mock_txn):
        sollevata = ValueError("dettaglio")

        def process(x):
            raise sollevata

        esito = run_fan_out(["a"], process)
        self.assertIs(esito.errori[0].eccezione, sollevata)

        # Il savepoint che non si apre: `process` non parte, l'eccezione e'
        # quella del contesto — e arriva lo stesso, intera.
        dal_savepoint = RuntimeError("savepoint rotto")
        mock_txn.atomic.side_effect = dal_savepoint
        mai = MagicMock()
        esito = run_fan_out(["b"], mai)
        mai.assert_not_called()
        self.assertIs(esito.errori[0].eccezione, dal_savepoint)
        self.assertEqual(esito.esito, "ERRORE")

    # Scopo: Un savepoint PER ITEM (default), non uno per giro: e' la ragione
    #        per cui il fallimento di uno non corrompe le scritture degli altri.
    def test_savepoint_aperto_per_ogni_item(self, mock_txn):
        run_fan_out([1, 2, 3], lambda x: x)
        self.assertEqual(mock_txn.atomic.call_count, 3)

    # Scopo: Chi isola per conto proprio disattiva il savepoint — annidarlo
    #        aggiungerebbe un livello inutile a ogni giro.
    def test_nessun_savepoint_se_isolamento_disattivato(self, mock_txn):
        esito = run_fan_out([1, 2], lambda x: x, isola_in_transazione=False)
        mock_txn.atomic.assert_not_called()
        self.assertEqual(esito.ok, 2)

    # Scopo: Il diario riceve start, un item_failed per ciascun fallimento e
    #        end con l'esito aggregato — nell'ordine.
    def test_run_logger_riceve_start_item_failed_end(self, _mock_txn):
        run_logger = MagicMock()

        def process(x):
            if x == 2:
                raise RuntimeError("ko")
            return x

        esito = run_fan_out([1, 2], process, run_logger=run_logger)

        run_logger.start.assert_called_once_with(totale=2)
        run_logger.item_failed.assert_called_once()
        kwargs = run_logger.item_failed.call_args.kwargs
        self.assertEqual(kwargs["item"], 2)
        self.assertEqual(kwargs["indice"], 1)
        self.assertIsInstance(kwargs["exc"], RuntimeError)
        run_logger.end.assert_called_once_with(esito=esito)

    # Scopo: I tre metodi sono OPZIONALI — chi ne implementa uno solo passa
    #        comunque. Obbligarli tutti spingerebbe i chiamanti a scrivere
    #        no-op per riempire il contratto.
    def test_run_logger_parziale_non_richiede_tutti_i_metodi(self, _mock_txn):
        class SoloFine:
            def __init__(self):
                self.visto = None

            def end(self, *, esito):
                self.visto = esito.esito

        run_logger = SoloFine()
        run_fan_out([1], lambda x: x, run_logger=run_logger)
        self.assertEqual(run_logger.visto, ESITO_COMPLETATO)

    # Scopo: ⚠️ Un difetto del DIARIO non deve affondare il LAVORO: se il
    #        logger solleva, il giro prosegue e l'esito resta quello vero.
    def test_run_logger_rotto_non_affonda_il_giro(self, _mock_txn):
        run_logger = MagicMock()
        run_logger.start.side_effect = RuntimeError("logger ko")
        run_logger.item_failed.side_effect = RuntimeError("logger ko")
        run_logger.end.side_effect = RuntimeError("logger ko")

        def process(x):
            if x == 2:
                raise RuntimeError("ko")
            return x

        esito = run_fan_out([1, 2], process, run_logger=run_logger)
        self.assertEqual(esito.esito, ESITO_PARZIALE)
        self.assertEqual(esito.ok, 1)

    # Scopo: `items` viene materializzato una volta sola: serve `totale` prima
    #        di partire, e un generatore consumato a meta' renderebbe l'esito
    #        irriproducibile.
    def test_items_generatore_materializzato_una_sola_volta(self, _mock_txn):
        def gen():
            yield from (1, 2, 3)

        run_logger = MagicMock()
        esito = run_fan_out(gen(), lambda x: x, run_logger=run_logger)
        run_logger.start.assert_called_once_with(totale=3)
        self.assertEqual(esito.totale, 3)
        self.assertEqual(esito.ok, 3)


@patch("apps.core.services.fan_out.transaction")
class OnSuccessTests(unittest.TestCase):
    # Scopo: `on_success` è l'aggancio degli effetti collaterali che valgono
    #        solo se l'item è atterrato: non deve vedere gli item falliti.
    def test_chiamato_solo_per_gli_item_riusciti(self, _mock_txn):
        visti = []

        def process(x):
            if x == 2:
                raise RuntimeError("ko")
            return x * 10

        run_fan_out([1, 2, 3], process, on_success=lambda item, ris: visti.append((item, ris)))
        self.assertEqual(visti, [(1, 10), (3, 30)])

    # Scopo: ⚠️ IL PUNTO DEL MECCANISMO — `on_success` gira a savepoint GIÀ
    #        RILASCIATO. Se girasse dentro, scriverebbe strutture Python che un
    #        rollback non annullerebbe: è esattamente il difetto che il push
    #        aveva sulla sua cache di lookup.
    def test_chiamato_dopo_il_rilascio_del_savepoint(self, mock_txn):
        ordine = []
        ctx = mock_txn.atomic.return_value
        ctx.__enter__.side_effect = lambda: ordine.append("savepoint-aperto")
        ctx.__exit__.side_effect = lambda *a: ordine.append("savepoint-rilasciato")

        run_fan_out(
            [1],
            lambda x: ordine.append("lavoro"),
            on_success=lambda item, ris: ordine.append("registrazione"),
        )

        self.assertEqual(
            ordine,
            ["savepoint-aperto", "lavoro", "savepoint-rilasciato", "registrazione"],
        )

    # Scopo: l'effetto di `on_success` è visibile all'item SUCCESSIVO — è la
    #        ragione per cui l'aggancio esiste (una cache condivisa fra item
    #        servirebbe a nulla se si popolasse a fine giro).
    def test_effetto_visibile_all_item_successivo(self, _mock_txn):
        cache = {}
        letture = []

        def process(x):
            letture.append(cache.get("chiave"))
            return x

        run_fan_out([1, 2], process, on_success=lambda item, ris: cache.setdefault("chiave", ris))
        self.assertEqual(letture, [None, 1])

    # Scopo: ⚠️ `on_success` NON è protetto, ed è voluto: il lavoro dell'item è
    #        già committato e non è più annullabile, quindi trattare l'errore
    #        come "item fallito" direbbe una bugia. Deve rompere, forte.
    def test_eccezione_interrompe_il_giro_e_non_diventa_item_fallito(self, _mock_txn):
        lavorati = []

        def esplodi(item, ris):
            raise RuntimeError("registrazione ko")

        with self.assertRaises(RuntimeError):
            run_fan_out([1, 2, 3], lavorati.append, on_success=esplodi)

        # Si è fermato al primo: nessun tentativo sugli item successivi.
        self.assertEqual(lavorati, [1])
