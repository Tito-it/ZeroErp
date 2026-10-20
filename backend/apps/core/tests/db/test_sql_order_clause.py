# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio del BB `sql_order_clause`, estratto il 2026-09-02 (ok Tid)
#        dalle **46 ripetizioni** della stessa espressione nel backend.
#
#        ⚠️ PERCHE' UN BB VUOLE PIU' PRESIDIO DEI SUOI CALL-SITE, non meno: un
#        difetto qui non sbaglia una lista, le sbaglia tutte insieme — e nel
#        verso peggiore, perche' ogni chiamante lo eredita senza averlo scritto.
#
# ⛔ NON SERVE IL DATABASE: qui si guarda la STRINGA prodotta. Le query vere le
#    prova gia' `test_lista_proiezione_campo_sorgente` contro il database, colonna
#    per colonna e in entrambi i versi; questo modulo prova la REGOLA, che li'
#    non si vedrebbe (una clausola sbagliata nel verso e' SQL validissimo).
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_senza_ordinamento_usa_il_default
1. test_ordinamento_esplicito_vince_sul_default
2. test_colonna_fuori_whitelist_ricade_sul_default
3. test_il_tiebreak_segue_la_direzione_primaria
4. test_il_tiebreak_non_si_ripete_quando_e_gia_la_colonna
5. test_le_colonne_data_partono_desc          (regola Tid 2026-09-02)
6. test_una_direzione_esplicita_vince_anche_su_una_colonna_data
7. test_default_clause_non_prende_una_seconda_direzione
8. test_default_e_default_clause_si_escludono
9. test_rigido_rifiuta_una_colonna_fuori_whitelist   (estensione 2026-09-26)
10. test_rigido_rifiuta_una_direzione_estranea
11. test_rigido_ammette_i_valori_validi_e_il_non_indicato
12. test_una_direzione_estranea_e_rifiutata_anche_nel_modo_storico (2026-09-26)
13. test_la_direzione_assente_prende_il_default_su_ogni_ramo
14. test_la_colonna_di_default_indicata_prende_il_verso_del_default (2026-10-20)
15. test_una_colonna_data_per_nome_parte_desc (2026-10-20, inferenza dal nome)
16. test_la_coda_resta_crescente_sul_suo_default
17. test_e_chiave_data_riconosce_la_convenzione_e_non_i_falsi_amici
18. test_direzione_lista_inferisce_solo_dentro_la_whitelist (BB `sql_order_direction_lista`)
19. test_direzione_lista_default_per_chiave_o_espressione
20. test_direzione_lista_e_la_stessa_regola_di_sql_order_clause
"""

from __future__ import annotations

import unittest

from apps.core.db._helpers import e_chiave_data, sql_order_clause, sql_order_direction_lista

_COLONNE = {
    "codice": "t.codice",
    "data_evento": "t.data_evento",
}


class SqlOrderClauseTests(unittest.TestCase):
    def test_senza_ordinamento_usa_il_default(self) -> None:
        clausola = sql_order_clause(
            None, None, colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
        )
        self.assertEqual(clausola, "t.creato_il ASC NULLS FIRST, t.id ASC")

    def test_ordinamento_esplicito_vince_sul_default(self) -> None:
        clausola = sql_order_clause(
            "codice", "desc", colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
        )
        self.assertEqual(clausola, "t.codice DESC NULLS LAST, t.id DESC")

    def test_colonna_fuori_whitelist_ricade_sul_default(self) -> None:
        # ⚠️ Ricade in SILENZIO, ed e' il comportamento storico di tutti i
        #    repository: il 400 su un `order_by` sconosciuto lo dà, dove serve,
        #    `validate_order_params` a monte. Qui si fissa che il ripiego sia il
        #    DEFAULT e non la prima colonna della whitelist, che sarebbe un
        #    ordine deciso dall'ordine di scrittura di un dizionario.
        clausola = sql_order_clause(
            "colonna_inventata", None,
            colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
        )
        self.assertTrue(clausola.startswith("t.creato_il "), clausola)

    def test_il_tiebreak_segue_la_direzione_primaria(self) -> None:
        # ⛔ Decisione Tid 2026-08-03: a parita' di valore l'elenco non deve
        #    andare al contrario di come e' stato chiesto.
        for direzione, atteso in (("asc", "t.id ASC"), ("desc", "t.id DESC")):
            with self.subTest(direzione=direzione):
                clausola = sql_order_clause(
                    "codice", direzione,
                    colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
                )
                self.assertTrue(clausola.endswith(atteso), clausola)

    def test_il_tiebreak_non_si_ripete_quando_e_gia_la_colonna(self) -> None:
        # ⛔ Il caso reale: una lista il cui ordinamento di partenza E' `id`
        #    produceva `ORDER BY s.id ASC, s.id ASC` — la colonna e il suo
        #    stesso spareggio. Non sbaglia il risultato, ma e' una clausola che
        #    dice due volte la stessa cosa.
        clausola = sql_order_clause(
            None, None, colonne=_COLONNE, default="s.id", tiebreak="s.id",
        )
        self.assertEqual(clausola, "s.id ASC NULLS FIRST")

    def test_le_colonne_data_partono_desc(self) -> None:
        # ⭐ Regola di Tid del 2026-09-02: «gli ordinamenti per data hanno sempre
        #    default DESC». Una data si legge dalla piu' recente.
        clausola = sql_order_clause(
            "data_evento", None,
            colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            colonne_desc={"data_evento"},
        )
        self.assertEqual(clausola, "t.data_evento DESC NULLS LAST, t.id DESC")
        # E una colonna NON data resta ASC: la regola vale per le date, non per
        # tutto — altrimenti sarebbe `default_desc` con un altro nome.
        clausola_codice = sql_order_clause(
            "codice", None,
            colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            colonne_desc={"data_evento"},
        )
        self.assertEqual(clausola_codice, "t.codice ASC NULLS FIRST, t.id ASC")

    def test_una_direzione_esplicita_vince_anche_su_una_colonna_data(self) -> None:
        # ⚠️ Senza questo, l'operatore non potrebbe INVERTIRE l'ordine di una
        #    colonna data: il secondo click resterebbe DESC come il primo.
        clausola = sql_order_clause(
            "data_evento", "asc",
            colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            colonne_desc={"data_evento"},
        )
        self.assertEqual(clausola, "t.data_evento ASC NULLS FIRST, t.id ASC")

    def test_default_clause_non_prende_una_seconda_direzione(self) -> None:
        # 🔴 Difetto reale della prima stesura del BB, trovato in giornata: un
        #    ordinamento di partenza a piu' criteri porta le direzioni DENTRO di
        #    se', e trattarlo come una colonna gli appiccicava una seconda
        #    direzione in coda — `... DESC DESC NULLS LAST`, che PostgreSQL
        #    rifiuta. Da qui i due parametri distinti.
        clausola = sql_order_clause(
            None, None,
            colonne=_COLONNE,
            default_clause="COALESCE(t.fine, 'infinity'::date) DESC, t.inizio DESC",
            tiebreak="t.id",
            default_desc=True,
        )
        self.assertEqual(
            clausola,
            "COALESCE(t.fine, 'infinity'::date) DESC, t.inizio DESC, t.id DESC",
        )
        self.assertNotIn("DESC DESC", clausola)

    def test_default_e_default_clause_si_escludono(self) -> None:
        # ⛔ Solleva invece di scegliere: passarli entrambi significa che chi
        #    scrive non sa quale dei due sta usando, e un BB che decide al posto
        #    suo trasforma un dubbio in un ordinamento sbagliato silenzioso.
        with self.assertRaises(RuntimeError):
            sql_order_clause(
                None, None, colonne=_COLONNE,
                default="t.codice", default_clause="t.codice DESC", tiebreak="t.id",
            )
        with self.assertRaises(RuntimeError):
            sql_order_clause(None, None, colonne=_COLONNE, tiebreak="t.id")

    # 9-11. `rifiuta_fuori_whitelist=True` (2026-09-26): per i repository il cui
    #       service ha GIA' validato — li' un valore estraneo e' un errore di
    #       programmazione, e il ripiego sul default lo nasconderebbe.
    def test_rigido_rifiuta_una_colonna_fuori_whitelist(self) -> None:
        with self.assertRaises(RuntimeError):
            sql_order_clause(
                "t.codice; DROP", "asc", colonne=_COLONNE,
                default="t.codice", tiebreak="t.id", rifiuta_fuori_whitelist=True,
            )

    def test_rigido_rifiuta_una_direzione_estranea(self) -> None:
        for grezzo in ("ASC NULLS LAST", "sideways", "desc;"):
            with self.subTest(valore=grezzo), self.assertRaises(ValueError):
                sql_order_clause(
                    "codice", grezzo, colonne=_COLONNE,
                    default="t.codice", tiebreak="t.id", rifiuta_fuori_whitelist=True,
                )

    def test_rigido_ammette_i_valori_validi_e_il_non_indicato(self) -> None:
        self.assertEqual(
            sql_order_clause(
                "data_evento", " DESC ", colonne=_COLONNE,
                default="t.codice", tiebreak="t.id", rifiuta_fuori_whitelist=True,
            ),
            "t.data_evento DESC NULLS LAST, t.id DESC",
        )
        # Non indicato: il default, come nel modo storico.
        self.assertEqual(
            sql_order_clause(
                None, None, colonne=_COLONNE, default="t.codice",
                default_desc=True, tiebreak="t.id", rifiuta_fuori_whitelist=True,
            ),
            "t.codice DESC NULLS LAST, t.id DESC",
        )
        # ⚠️ Il modo storico NON e' cambiato sulla COLONNA: fuori whitelist
        #    ripiega ancora (la direzione, indicata e valida, resta rispettata).
        self.assertEqual(
            sql_order_clause(
                "boh", "desc", colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            ),
            "t.codice DESC NULLS LAST, t.id DESC",
        )

    # 12. ⛔ Decisione Tid 2026-09-26: la DIREZIONE estranea e' rifiutata anche
    #     senza `rifiuta_fuori_whitelist`, e su ogni ramo — colonna scelta,
    #     colonna fuori whitelist che ripiega sul default, `default_clause`.
    #     Prima diventava ASC in silenzio. Il flag resta per la sola colonna.
    def test_una_direzione_estranea_e_rifiutata_anche_nel_modo_storico(self) -> None:
        rami = {
            "colonna": {"order_by": "codice", "default": "t.codice"},
            "fuori_whitelist": {"order_by": "boh", "default": "t.codice"},
            "assente": {"order_by": None, "default": "t.codice"},
            "default_clause": {"order_by": None, "default_clause": "t.a DESC, t.b ASC"},
        }
        for nome, kw in rami.items():
            order_by = kw.pop("order_by")
            with self.subTest(ramo=nome), self.assertRaisesRegex(ValueError, "order_dir_invalid"):
                sql_order_clause(
                    order_by, "giu", colonne=_COLONNE, tiebreak="t.id", **kw,
                )

    # 13. L'ASSENZA resta ammessa e prende il default del ramo.
    def test_la_direzione_assente_prende_il_default_su_ogni_ramo(self) -> None:
        for assente in (None, "", "  "):
            with self.subTest(valore=assente):
                self.assertEqual(
                    sql_order_clause(
                        "data_evento", assente, colonne=_COLONNE, default="t.codice",
                        tiebreak="t.id", colonne_desc=("data_evento",),
                    ),
                    "t.data_evento DESC NULLS LAST, t.id DESC",
                )
                self.assertEqual(
                    sql_order_clause(
                        None, assente, colonne=_COLONNE,
                        default_clause="t.a DESC, t.b ASC", tiebreak="t.id",
                    ),
                    "t.a DESC, t.b ASC, t.id ASC",
                )

    # 14. ⛔ `parse_list_params(default_order=...)` RIEMPIE `order_by` quando il
    #     client non chiede niente: la colonna indicata e' allora proprio quella
    #     di default, e deve prenderne il verso. Fino al 2026-10-20 questo ramo
    #     ignorava `default_desc`, e le liste «dal piu' recente» partivano dal
    #     piu' vecchio. Una colonna DIVERSA dal default non lo eredita, e una
    #     direzione esplicita vince sempre.
    def test_la_colonna_di_default_indicata_prende_il_verso_del_default(self) -> None:
        self.assertEqual(
            sql_order_clause(
                "data_evento", None, colonne=_COLONNE, default="t.data_evento",
                tiebreak="t.id", default_desc=True,
            ),
            "t.data_evento DESC NULLS LAST, t.id DESC",
        )
        self.assertEqual(
            sql_order_clause(
                "codice", None, colonne=_COLONNE, default="t.data_evento",
                tiebreak="t.id", default_desc=True,
            ),
            "t.codice ASC NULLS FIRST, t.id ASC",
        )
        self.assertEqual(
            sql_order_clause(
                "data_evento", "asc", colonne=_COLONNE, default="t.data_evento",
                tiebreak="t.id", default_desc=True,
            ),
            "t.data_evento ASC NULLS FIRST, t.id ASC",
        )

    # 15. ⭐ La data si riconosce dal NOME: senza `colonne_desc` una chiave
    #     `data_*`, `*_at`, `valido_*`... parte DESC; una non-data resta ASC.
    def test_una_colonna_data_per_nome_parte_desc(self) -> None:
        colonne = {"codice": "t.codice", "data_insert": "t.data_insert",
                   "inviato_at": "t.inviato_at", "valido_al": "t.valido_al"}
        for chiave in ("data_insert", "inviato_at", "valido_al"):
            with self.subTest(chiave=chiave):
                self.assertEqual(
                    sql_order_clause(chiave, None, colonne=colonne, default="t.codice", tiebreak="t.id"),
                    f"{colonne[chiave]} DESC NULLS LAST, t.id DESC",
                )
        self.assertEqual(
            sql_order_clause("codice", None, colonne=colonne, default="t.data_insert", tiebreak="t.id"),
            "t.codice ASC NULLS FIRST, t.id ASC",
        )

    # 16. Una CODA si apre crescente sulla sua data di default (`default_desc`
    #     False), anche quando `order_by` la nomina; un'altra data parte DESC.
    def test_la_coda_resta_crescente_sul_suo_default(self) -> None:
        colonne = {"data_scadenza": "v.data_scadenza", "data": "v.data"}
        self.assertEqual(
            sql_order_clause("data_scadenza", None, colonne=colonne, default="v.data_scadenza",
                             tiebreak="v.id", colonne_desc=("data", "data_scadenza")),
            "v.data_scadenza ASC NULLS FIRST, v.id ASC",
        )
        self.assertEqual(
            sql_order_clause("data", None, colonne=colonne, default="v.data_scadenza", tiebreak="v.id"),
            "v.data DESC NULLS LAST, v.id DESC",
        )

    # 17. La convenzione dei nomi data, e i nomi che le somigliano senza esserlo
    #     (trovati nell'inventario del 2026-10-20).
    def test_e_chiave_data_riconosce_la_convenzione_e_non_i_falsi_amici(self) -> None:
        for chiave in ("data", "data_insert", "data_scadenza", "generato_at", "valido_dal",
                       "valido_al", "validita_al", "competenza_mese"):
            with self.subTest(data=chiave):
                self.assertTrue(e_chiave_data(chiave))
        for chiave in ("codice", "user_insert", "presidia_data_documento",
                       "scadenza_numero_rata", "originale", "totale", ""):
            with self.subTest(non_data=chiave):
                self.assertFalse(e_chiave_data(chiave))

    # 18. ⛔ Una chiave FUORI whitelist ripiega sul default: la direzione e'
    #     quella del default, non quella del nome chiesto (le copie a mano
    #     facevano partire DESC `?order_by=data_x` su una lista ordinata per codice).
    def test_direzione_lista_inferisce_solo_dentro_la_whitelist(self) -> None:
        colonne = {"codice": "t.codice", "data": "t.data"}
        self.assertEqual(sql_order_direction_lista("data_x", None, colonne=colonne), "ASC NULLS FIRST")
        self.assertEqual(sql_order_direction_lista(None, None, colonne=colonne), "ASC NULLS FIRST")
        self.assertEqual(
            sql_order_direction_lista(None, None, colonne=colonne, default_desc=True), "DESC NULLS LAST",
        )
        self.assertEqual(sql_order_direction_lista("data", None, colonne=colonne), "DESC NULLS LAST")
        self.assertEqual(sql_order_direction_lista("codice", None, colonne=colonne), "ASC NULLS FIRST")
        # La direzione esplicita vince, e una estranea e' rifiutata su ogni ramo.
        self.assertEqual(sql_order_direction_lista("data", "asc", colonne=colonne), "ASC NULLS FIRST")
        for chiave in (None, "data_x", "data"):
            with self.subTest(chiave=chiave), self.assertRaises(ValueError):
                sql_order_direction_lista(chiave, "giu", colonne=colonne)

    # 19. La colonna di default segue `default_desc`, riconosciuta sia
    #     dall'espressione sia dalla chiave.
    def test_direzione_lista_default_per_chiave_o_espressione(self) -> None:
        colonne = {"data_scadenza": "v.data_scadenza"}
        for default in ("v.data_scadenza", "data_scadenza"):
            with self.subTest(default=default):
                self.assertEqual(
                    sql_order_direction_lista("data_scadenza", None, colonne=colonne, default=default),
                    "ASC NULLS FIRST",
                )

    # 20. `sql_order_clause` passa dal BB: stessa direzione su ogni ramo.
    def test_direzione_lista_e_la_stessa_regola_di_sql_order_clause(self) -> None:
        colonne = {"codice": "t.codice", "data": "t.data", "valido_dal": "t.valido_dal"}
        for order_by in (None, "codice", "data", "valido_dal", "fuori"):
            for order_dir in (None, "asc", "desc"):
                for default_desc in (False, True):
                    with self.subTest(order_by=order_by, order_dir=order_dir, default_desc=default_desc):
                        attesa = sql_order_direction_lista(
                            order_by, order_dir, colonne=colonne, default="t.valido_dal",
                            default_desc=default_desc,
                        )
                        clausola = sql_order_clause(
                            order_by, order_dir, colonne=colonne, default="t.valido_dal",
                            default_desc=default_desc, tiebreak="t.id",
                        )
                        self.assertIn(f" {attesa}, t.id ", clausola + " ")
