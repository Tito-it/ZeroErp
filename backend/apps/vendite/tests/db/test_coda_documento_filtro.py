# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test del BB `filtro_coda_per_documento` (funzione pura, no DB).
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_ddt_usa_la_colonna_della_vista
2) test_ordine_passa_dal_fulfillment_non_da_ordine_riga_id
3) test_nessun_documento_non_e_una_condizione_sempre_vera
4) test_ddt_prevale_se_arrivano_entrambi
5) test_id_sempre_castato_a_intero
6) test_alias_v_su_entrambi_i_rami
"""

from django.test import SimpleTestCase

from apps.vendite.db._coda_documento_filtro import filtro_coda_per_documento


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
