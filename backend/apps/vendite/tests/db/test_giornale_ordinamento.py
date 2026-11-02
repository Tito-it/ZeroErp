# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test della clausola ORDER BY del giornale di un'entita'
#        (`_giornale_order_clause`, funzione pura, no DB) — la scheda «Storia»
#        del drawer fattura, Passo A del filone osservabilita'.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_default_ordina_per_tempo_dal_piu_recente
2) test_colonna_fuori_whitelist_e_rifiutata
3) test_dentro_la_gravita_il_tempo_resta_dal_piu_recente
4) test_quando_ordina_col_tiebreak_allineato
5) test_quando_ascendente_porta_con_se_il_tiebreak
6) test_nessun_nulls_incollato_alla_direzione
"""

from django.test import SimpleTestCase

from apps.vendite.db.vendite_repository import GIORNALE_ORDINE_DEFAULT, _giornale_order_clause


class GiornaleOrdinamentoTests(SimpleTestCase):
    """L'ordine della storia di un documento.

    ⛔ Perche' esiste questo file: un ordinamento sbagliato **non solleva
    niente**. A video un elenco ordinato male e uno ordinato bene si somigliano,
    e l'unico modo di accorgersene sarebbe che qualcuno noti una riga fuori
    posto — cioe' mai.
    """

    # Scopo: ⭐ Il default e' il TEMPO dal piu' recente — il preset della lista
    # a catalogo `vendite.giornale`, che dal 2026-09-27 e' la stessa per il
    # trasversale e per le due Storie (brief-db-liste-datatable-grezze §3.1).
    # Fino a quel giorno la Storia partiva dalla gravita' (Tid, 2026-08-24): la
    # domanda «c'e' qualcosa che non va?» ha ora il banner della fattura, con
    # una fonte sua (`get_giornale_errore_vivo`).
    def test_default_ordina_per_tempo_dal_piu_recente(self) -> None:
        clausola = _giornale_order_clause(None, None)
        self.assertTrue(clausola.startswith("t.quando DESC"))
        self.assertEqual(clausola, _giornale_order_clause(GIORNALE_ORDINE_DEFAULT, "desc"))

    # Scopo: ⛔ Una colonna che non esiste e' un 400 (`order_by_invalid`), non
    # il default: dal 2026-10-20 nessuna lista risponde ordinata diversamente
    # da come e' stato chiesto (brief-be-verifica-documentazione-api §A1). Assente = il default.
    def test_colonna_fuori_whitelist_e_rifiutata(self) -> None:
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            _giornale_order_clause("cosa", "desc")
        self.assertEqual(
            _giornale_order_clause(None, "desc"),
            _giornale_order_clause(GIORNALE_ORDINE_DEFAULT, "desc"),
        )

    # Scopo: 🔴 Il test che protegge la scelta meno ovvia. Dentro la stessa
    # gravita' il tempo resta DISCENDENTE anche chiedendo l'ordine ascendente:
    # «i meno gravi prima» non vuol dire «i piu' vecchi prima». Se il verso si
    # propagasse al secondo criterio, ordinando per gravita' crescente si
    # otterrebbe la storia piu' vecchia in cima senza averla chiesta.
    def test_dentro_la_gravita_il_tempo_resta_dal_piu_recente(self) -> None:
        clausola = _giornale_order_clause("gravita", "asc")
        self.assertIn("t.rango_gravita ASC", clausola)
        self.assertIn("t.quando DESC", clausola)
        self.assertTrue(clausola.endswith("t.riga_id DESC"))

    # Scopo: sul tempo il tiebreak `riga_id` segue la direzione — e' il rimedio
    # al rilievo R-1 (il default `now()` e' il timestamp di TRANSAZIONE, quindi
    # piu' righe condividono l'istante: a ordinare dentro l'istante e' l'ordine
    # di scrittura).
    def test_quando_ordina_col_tiebreak_allineato(self) -> None:
        clausola = _giornale_order_clause("quando", "desc")
        self.assertIn("t.quando DESC", clausola)
        self.assertTrue(clausola.endswith("t.riga_id DESC"))

    def test_quando_ascendente_porta_con_se_il_tiebreak(self) -> None:
        clausola = _giornale_order_clause("quando", "asc")
        self.assertIn("t.quando ASC", clausola)
        self.assertTrue(clausola.endswith("t.riga_id ASC"))

    # Scopo: ⛔ Presidio locale del difetto gia' pagato altrove: `NULLS ...`
    # incollato DOPO la direzione, che `sql_order_direction` porta gia' con se'.
    # Il risultato sarebbe `DESC NULLS LAST NULLS LAST`, SQL invalido — cioe' un
    # 500 su ogni ordinamento.
    def test_nessun_nulls_incollato_alla_direzione(self) -> None:
        for colonna in (None, "gravita", "quando"):
            for verso in ("asc", "desc"):
                with self.subTest(colonna=colonna, verso=verso):
                    self.assertEqual(
                        _giornale_order_clause(colonna, verso).count("NULLS"),
                        1,
                    )
