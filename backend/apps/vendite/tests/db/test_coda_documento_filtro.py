# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test dei BB di `_coda_documento_filtro` (funzioni pure, no DB):
#        il predicato `filtro_coda_per_documento`, dal 2026-09-21 la sorgente
#        `sorgente_per_documento` per le funzioni con la chiusura dentro e, dal
#        2026-09-22, la scelta fra le due per le code (`lettura_coda_per_documento`
#        sulla mappa `FUNZIONE_PER_CODA`).
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_ddt_usa_la_colonna_della_vista
2) test_ordine_passa_dal_fulfillment_non_da_ordine_riga_id
3) test_nessun_documento_non_e_una_condizione_sempre_vera
4) test_ddt_prevale_se_arrivano_entrambi
5) test_id_sempre_castato_a_intero
6) test_alias_v_su_entrambi_i_rami
— sorgente_per_documento —
7) test_sorgente_ddt_riempie_il_primo_array
8) test_sorgente_ordine_riempie_il_secondo_array
9) test_sorgente_senza_documento_solleva_non_ripiega_su_tutte
10) test_sorgente_con_entrambi_solleva
11) test_sorgente_id_sempre_castato_a_intero
— lettura_coda_per_documento —
12) test_la_mappa_conosce_ogni_coda_e_solo_gli_accrediti_hanno_la_funzione
13) test_coda_con_funzione_legge_la_funzione_senza_condizione
14) test_coda_senza_funzione_legge_la_vista_col_predicato
15) test_senza_documento_e_la_vista_intera_per_ogni_coda
16) test_con_entrambi_gli_id_solleva_per_ogni_coda
17) test_coda_ignota_e_un_chiamante_rotto
"""

from django.test import SimpleTestCase

from apps.vendite.db._coda_documento_filtro import (
    FUNZIONE_PER_CODA,
    LetturaCoda,
    filtro_coda_per_documento,
    lettura_coda_per_documento,
    sorgente_per_documento,
)

_ACCREDITI = "vendite.vw_resi_da_accreditare"
_RICONSEGNE = "vendite.vw_resi_da_riconsegnare"


class CodaDocumentoFiltroTests(SimpleTestCase):
    """Il predicato condiviso fra pannello situazione merce e code di lavoro."""

    # Scopo: lato DDT il legame è la colonna che la coda espone già — il DDT
    # della riga resa, che per costruzione è quello della partita.
    def test_ddt_usa_la_colonna_della_vista(self) -> None:
        condizione, params = filtro_coda_per_documento(ddt_id=140)
        self.assertEqual(condizione, "v.ddt_id = %s")
        self.assertEqual(params, [140])

    # Scopo: 🔴 il test che protegge la scelta meno ovvia. Lato ordine NON si
    # passa da `v.ordine_riga_id`, che pure esiste sulla vista: con la partita
    # generalizzata quella colonna è NULLABLE — vuota sulla merce senza origine
    # ordine (riga di DDT aggiunta a mano, DDT standalone). Usarla come chiave
    # farebbe sparire dal filtro proprio le righe che il cantiere della partita
    # ha appena portato dentro il conto, e l'elenco corto sembrerebbe corretto.
    def test_ordine_passa_dal_fulfillment_non_da_ordine_riga_id(self) -> None:
        condizione, params = filtro_coda_per_documento(ordine_id=240)
        assert condizione is not None
        self.assertIn("ordini_righe_fulfillment", condizione)
        self.assertIn("f.ddt_riga_id = v.ddt_riga_id", condizione)
        self.assertNotIn("v.ordine_riga_id", condizione)
        self.assertEqual(params, [240])

    # Scopo: senza documento il BB non deve restituire una condizione vera —
    # deve restituire NIENTE, e lasciare al chiamante il significato «nessuna
    # restrizione». Un `1=1` funzionerebbe e sarebbe più difficile da leggere.
    def test_nessun_documento_non_e_una_condizione_sempre_vera(self) -> None:
        condizione, params = filtro_coda_per_documento()
        self.assertIsNone(condizione)
        self.assertEqual(params, [])

    # Scopo: se arrivano entrambi vince il DDT, deterministicamente. Il divieto
    # vero è a monte (guard nel service): qui conta solo che il comportamento
    # non dipenda dall'ordine dei kwargs.
    def test_ddt_prevale_se_arrivano_entrambi(self) -> None:
        condizione, params = filtro_coda_per_documento(ddt_id=1, ordine_id=2)
        self.assertEqual(condizione, "v.ddt_id = %s")
        self.assertEqual(params, [1])

    # Scopo: l'id arriva dalla query string. Il cast a intero è la difesa che
    # resta anche se un chiamante futuro salta `qp_int_optional`.
    def test_id_sempre_castato_a_intero(self) -> None:
        _, params = filtro_coda_per_documento(ddt_id="140")  # type: ignore[arg-type]
        self.assertEqual(params, [140])
        self.assertIsInstance(params[0], int)
        _, params = filtro_coda_per_documento(ordine_id="240")  # type: ignore[arg-type]
        self.assertEqual(params, [240])

    # Scopo: entrambi i rami assumono l'alias `v` sulla vista-coda. È la
    # convenzione dei due chiamanti, e cambiarla da un lato solo romperebbe
    # l'altro senza che nessun test lo dica — questo lo dice.
    def test_alias_v_su_entrambi_i_rami(self) -> None:
        for kwargs in ({"ddt_id": 1}, {"ordine_id": 1}):
            with self.subTest(**kwargs):
                condizione, _ = filtro_coda_per_documento(**kwargs)
                assert condizione is not None
                self.assertIn("v.", condizione)


class SorgentePerDocumentoTests(SimpleTestCase):
    """La sorgente nel FROM per le funzioni `(p_ddt_ids, p_ordine_ids)`."""

    # Scopo: per DDT si riempie il PRIMO array, l'altro resta NULL — e il cast
    # `::bigint[]` e' esplicito, come chiede il brief (§8.4).
    def test_sorgente_ddt_riempie_il_primo_array(self) -> None:
        sql, params = sorgente_per_documento("vendite.fn_partite_merce", ddt_id=140)
        self.assertEqual(sql, "vendite.fn_partite_merce(ARRAY[%s]::bigint[], NULL)")
        self.assertEqual(params, [140])

    # Scopo: per ordine il SECONDO. Sbagliare array non da' errore: da' le
    # partite di un altro documento, con la stessa forma di risposta.
    def test_sorgente_ordine_riempie_il_secondo_array(self) -> None:
        sql, params = sorgente_per_documento("vendite.fn_partite_merce", ordine_id=240)
        self.assertEqual(sql, "vendite.fn_partite_merce(NULL, ARRAY[%s]::bigint[])")
        self.assertEqual(params, [240])

    # Scopo: 🔴 senza documento NON si ripiega su `fn(NULL, NULL)`: quella e'
    # «tutte le righe del database», e un chiamante che non passa nessun id e'
    # rotto — il predicato gemello risponde `None` perche' per la coda aperta
    # «nessuna restrizione» e' un significato; qui non lo e'.
    def test_sorgente_senza_documento_solleva_non_ripiega_su_tutte(self) -> None:
        with self.assertRaises(ValueError):
            sorgente_per_documento("vendite.fn_partite_merce")

    # Scopo: con entrambi si solleva, non si sceglie: la funzione farebbe
    # l'UNIONE dei due documenti, che nessun lettore chiede.
    def test_sorgente_con_entrambi_solleva(self) -> None:
        with self.assertRaises(ValueError):
            sorgente_per_documento("vendite.fn_partite_merce", ddt_id=1, ordine_id=2)

    # Scopo: l'id arriva al driver come intero, mai come stringa.
    def test_sorgente_id_sempre_castato_a_intero(self) -> None:
        _, params = sorgente_per_documento("vendite.fn_x", ddt_id="7")  # type: ignore[arg-type]
        self.assertEqual(params, [7])
        self.assertIsInstance(params[0], int)



class LetturaCodaPerDocumentoTests(SimpleTestCase):
    """La scelta fra le due forme, decisa dalla mappa e non dal chiamante."""

    # Scopo: la sede unica. Le code sono due, e oggi solo gli accrediti hanno la
    #        funzione con la chiusura dentro: il giorno in cui la mappa cambia,
    #        questo test cambia CON lei — e' la riga che i quattro punti seguono.
    def test_la_mappa_conosce_ogni_coda_e_solo_gli_accrediti_hanno_la_funzione(self) -> None:
        self.assertEqual(
            FUNZIONE_PER_CODA,
            {_ACCREDITI: "vendite.fn_resi_da_accreditare", _RICONSEGNE: None},
        )

    # Scopo: coda con funzione + documento -> la funzione nel FROM, nessun
    #        predicato: la chiusura e' dentro. Stessa forma di
    #        `sorgente_per_documento`, per costruzione.
    def test_coda_con_funzione_legge_la_funzione_senza_condizione(self) -> None:
        for kwargs, atteso in (
            ({"ddt_id": 140}, "vendite.fn_resi_da_accreditare(ARRAY[%s]::bigint[], NULL)"),
            ({"ordine_id": 240}, "vendite.fn_resi_da_accreditare(NULL, ARRAY[%s]::bigint[])"),
        ):
            with self.subTest(**kwargs):
                lettura = lettura_coda_per_documento(_ACCREDITI, **kwargs)
                self.assertEqual(
                    lettura,
                    LetturaCoda(atteso, [next(iter(kwargs.values()))], None, []),
                )
                self.assertEqual(
                    (lettura.sorgente, lettura.params_sorgente),
                    sorgente_per_documento("vendite.fn_resi_da_accreditare", **kwargs),
                )

    # Scopo: coda senza funzione + documento -> la vista nel FROM e il predicato
    #        del BB gemello nel WHERE, coi parametri dalla parte del WHERE.
    def test_coda_senza_funzione_legge_la_vista_col_predicato(self) -> None:
        for kwargs in ({"ddt_id": 140}, {"ordine_id": 240}):
            with self.subTest(**kwargs):
                lettura = lettura_coda_per_documento(_RICONSEGNE, **kwargs)
                condizione, params = filtro_coda_per_documento(**kwargs)
                self.assertEqual(lettura, LetturaCoda(_RICONSEGNE, [], condizione, params))

    # Scopo: senza documento la risposta e' la vista intera per ENTRAMBE le
    #        code — la coda aperta a mano — e mai `fn(NULL, NULL)`: la vista lo
    #        e' gia', per costruzione.
    def test_senza_documento_e_la_vista_intera_per_ogni_coda(self) -> None:
        for vista in (_ACCREDITI, _RICONSEGNE):
            with self.subTest(vista=vista):
                self.assertEqual(
                    lettura_coda_per_documento(vista), LetturaCoda(vista, [], None, [])
                )

    # Scopo: 🔴 con entrambi gli id si solleva per OGNI coda, anche per quella
    #        col predicato (che da solo sceglierebbe il DDT): le due forme
    #        devono rispondere la stessa cosa alla stessa domanda, e «due id»
    #        e' una domanda che il service rifiuta prima.
    def test_con_entrambi_gli_id_solleva_per_ogni_coda(self) -> None:
        for vista in (_ACCREDITI, _RICONSEGNE):
            with self.subTest(vista=vista), self.assertRaises(ValueError):
                lettura_coda_per_documento(vista, ddt_id=1, ordine_id=2)

    # Scopo: una coda che la mappa non conosce non ripiega sulla vista: e' un
    #        chiamante rotto, e l'aggiunta di una coda e' una riga scritta qui.
    def test_coda_ignota_e_un_chiamante_rotto(self) -> None:
        with self.assertRaises(KeyError):
            lettura_coda_per_documento("vendite.vw_resi_lista", ddt_id=1)
