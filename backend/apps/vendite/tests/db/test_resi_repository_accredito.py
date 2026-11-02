# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test di `ResiRepository.accredita_riga_reso` (mock cursor, no DB):
#        la madre `vendite.fn_accredita_riga_reso` e' `RETURNS TABLE` e il
#        repository deve leggerla con fetchall, non con fetchone.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_tutte_le_rettifiche_lette_con_fetchall — N righe, fetchone MAI chiamato
2) test_select_star_dalla_madre_non_select_scalare — la forma dell'SQL
3) test_id_castato_a_intero_nei_parametri — nessuna stringa al driver
4) test_annullo_letto_con_fetchall — anche l'annullo e' RETURNS TABLE
5) test_list_righe_legge_la_vista_e_non_ricostruisce — il dettaglio ha una
   sede a DB (`vw_resi_righe_dettaglio`, 20260825-25) e il repository non
   la ricompone. ⭐ Era «la formula non si riscrive»: la garanzia si e'
   spostata nella vista, e il presidio l'ha seguita invece di sparire.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

# Le cinque colonne della `RETURNS TABLE` della madre (brief §20.4).
_COLS = [
    "accredito_id",
    "commessa_attivita_id",
    "fattura_riga_rettificata_id",
    "qta",
    "qta_partita",
]


# Scopo: cursor mockato con `description` leggibile (rows_to_list legge `.name`).
def _mock_cursor(rows: list[tuple]) -> MagicMock:
    cursor = MagicMock()
    cursor.description = [MagicMock() for _ in _COLS]
    for descr, nome in zip(cursor.description, _COLS, strict=True):
        descr.name = nome
    cursor.fetchall.return_value = rows
    return cursor


# Scopo: aggancia il cursor mockato al context manager di `connection.cursor()`.
def _mock_connection(mock_conn: MagicMock, cursor: MagicMock) -> None:
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)


class ResiRepositoryAccreditoTests(TestCase):
    """La lettura della madre dell'accredito."""

    # Scopo: 🔴 il test che protegge la scelta meno ovvia. La madre restituisce
    # UNA riga per rettifica creata: su un kit una per componente, e se
    # l'accredito dovuto consuma due righe di fattura a prezzi diversi due.
    # Un `fetchone()` qui sarebbe verde su ogni riga semplice e perderebbe in
    # silenzio le rettifiche successive alla prima — con il ponte a DB scritto
    # per tutte. Per questo l'asserzione forte e' che fetchone NON venga
    # chiamato: senza, un fetchone + loop passerebbe il conteggio.
    @patch("apps.vendite.db.resi_repository.connection")
    def test_tutte_le_rettifiche_lette_con_fetchall(self, mock_conn) -> None:
        rows = [
            (901, 5501, 7101, "-3.000000", "-3.000000"),
            (902, 5502, 7102, "-1.000000", "-1.000000"),
            (903, 5503, 7103, "-2.000000", "-2.000000"),
        ]
        cursor = _mock_cursor(rows)
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.resi_repository import ResiRepository

        out = ResiRepository().accredita_riga_reso(5797)

        cursor.fetchone.assert_not_called()
        self.assertEqual(len(out), 3)
        self.assertEqual(
            [r["accredito_id"] for r in out], [901, 902, 903],
        )
        # Le due quantita' restano DISTINTE: `qta` e' in unita' di riga di
        # fattura, `qta_partita` in unita' di merce (su un kit non coincidono).
        self.assertEqual(sorted(out[0].keys()), sorted(_COLS))

    # Scopo: una `RETURNS TABLE` si legge `SELECT * FROM fn(...)`. La forma
    # scalare `SELECT vendite.fn_...(%s)` compilerebbe e restituirebbe una sola
    # colonna composita per riga: il mapping colonna->chiave si perderebbe, e i
    # test che mockano il cursor non lo vedrebbero.
    @patch("apps.vendite.db.resi_repository.connection")
    def test_select_star_dalla_madre_non_select_scalare(self, mock_conn) -> None:
        cursor = _mock_cursor([(901, 5501, 7101, "-3.000000", "-3.000000")])
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.resi_repository import ResiRepository

        ResiRepository().accredita_riga_reso(5797)

        cursor.execute.assert_called_once()
        sql = " ".join(cursor.execute.call_args[0][0].split())
        self.assertEqual(
            sql, "SELECT * FROM vendite.fn_accredita_riga_reso(%s)",
        )

    # Scopo: il confine SQL casta l'id (parita' con le altre madri del modulo).
    # La validazione di merito (NULL / <= 0) e' nella madre, non qui.
    @patch("apps.vendite.db.resi_repository.connection")
    def test_id_castato_a_intero_nei_parametri(self, mock_conn) -> None:
        cursor = _mock_cursor([(901, 5501, 7101, "-3.000000", "-3.000000")])
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.resi_repository import ResiRepository

        ResiRepository().accredita_riga_reso("5797")

        self.assertEqual(cursor.execute.call_args[0][1], [5797])

    # Scopo: l'annullo e' `RETURNS TABLE` come la madre che crea — ritorna le
    # coppie RIMOSSE, che su un kit sono N. Stessa trappola del fetchone.
    @patch("apps.vendite.db.resi_repository.connection")
    def test_annullo_letto_con_fetchall(self, mock_conn) -> None:
        cursor = _mock_cursor([
            (901, 5501, 7101, "-3.000000", "-3.000000"),
            (902, 5502, 7102, "-1.000000", "-1.000000"),
        ])
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.resi_repository import ResiRepository

        out = ResiRepository().annulla_accredito_riga_reso(5797, "riga sbagliata")

        cursor.fetchone.assert_not_called()
        self.assertEqual(len(out), 2)
        sql = " ".join(cursor.execute.call_args[0][0].split())
        self.assertEqual(
            sql, "SELECT * FROM vendite.fn_annulla_accredito_riga_reso(%s, %s)",
        )
        self.assertEqual(cursor.execute.call_args[0][1], [5797, "riga sbagliata"])


class ResiRigheGiaAccreditatoTests(TestCase):
    """Il fatto «quanto e' gia' stato accreditato» sulle righe del reso."""

    # Scopo: ⭐ LA GARANZIA SI E' SPOSTATA, E IL PRESIDIO CON LEI (2026-08-26).
    # Questo test asseriva che `list_righe` chiamasse
    # `vendite.fn_resi_riga_accreditato_partita(rr.id)` invece di rifare la
    # somma sul ponte — su un kit N righe portano la STESSA quota padre, e
    # sommarle la moltiplicherebbe.
    # Dal changeSet `20260825-25` quella query non esiste piu': la sede e'
    # `vendite.vw_resi_righe_dettaglio`, e la fn la chiama la vista. Cancellare
    # il test avrebbe tolto il presidio insieme al codice; riscriverlo
    # sull'invariante NUOVA lo tiene vivo dov'e' finita la garanzia.
    # ⛔ L'invariante e' «il repository non ricostruisce il dettaglio»: nessuna
    #    tabella di base, nessuna aggregazione, nessuna chiamata a funzione.
    #    Il lato DB (la fn e la coerenza con la sede unica del predicato) e'
    #    presidiato dal pgTAP `test-vw-resi-righe-dettaglio-v1`.
    # ⚠️ La query nasce nel BB core `RigheListaCompletaMixin` (2026-10-04):
    #    la connessione si sostituisce la', non nel modulo del repository.
    @patch("apps.core.db.righe_lista_mixin.connection")
    def test_list_righe_legge_la_vista_e_non_ricostruisce(self, mock_conn) -> None:
        cursor = MagicMock()
        cursor.description = []
        cursor.fetchall.return_value = []
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.resi_repository import ResiRepository

        ResiRepository().list_righe(7)

        sql = cursor.execute.call_args[0][0]
        self.assertIn("vendite.vw_resi_righe_dettaglio", sql)
        # Il dettaglio non si ricompone qui: ne' dalle tabelle di base...
        self.assertNotIn("vendite.resi_righe_riconsegne", sql)
        self.assertNotIn("vendite.resi_righe_rinunce", sql)
        # ...ne' rifacendo le formule che la vista possiede.
        self.assertNotIn("SUM(qta_partita)", sql)
        self.assertNotIn("fn_resi_riga_accreditato_partita", sql)
        self.assertNotIn("fn_resi_riga_residuo_riconsegna", sql)
        # ⚠️ `attivo` resta un filtro del CHIAMANTE: la vista proietta la
        #    colonna e non nasconde righe (pgTAP 5 della vista).
        self.assertIn("attivo IS TRUE", sql)


class FatturaNaturaELegameTests(TestCase):
    """B5 + B7: la natura del documento e il legame della nota di credito."""

    # Scopo: 🔴 B5 — la natura DEVE uscire decodificata dal backend, non essere
    # risolta dal client (display field via JOIN, memoria
    # feedback_display_fields_backend). Prima del 2026-08-19 `natura_doc_id` non
    # era nominata da nessun punto di `backend/apps/`: il drawer del lotto non
    # «assumeva» che fossero tutte fatture — non aveva il dato.
    @patch("apps.vendite.db.vendite_repository.connection")
    def test_testata_fattura_decodifica_la_natura(self, mock_conn) -> None:
        cursor = MagicMock()
        cursor.description = []
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.vendite_repository import VenditeRepository

        VenditeRepository().get_fattura_testata(7, auth_user_id=1)

        sql = cursor.execute.call_args[0][0]
        self.assertIn("config.nature_doc_fiscale ndf", sql)
        self.assertIn("AS natura_doc_codice", sql)
        self.assertIn("AS natura_doc_descrizione", sql)

    # Scopo: B7 — il legame DOCUMENTALE si legge nei due versi con la stessa
    # query, e il verso e' un PARAMETRO, non due SQL copiate.
    @patch("apps.vendite.db.vendite_repository.connection")
    def test_legame_documentale_nei_due_versi(self, mock_conn) -> None:
        cursor = MagicMock()
        cursor.description = []
        cursor.fetchall.return_value = []
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.vendite_repository import VenditeRepository

        out = VenditeRepository().get_fattura_rettifiche(7)

        self.assertEqual(sorted(out.keys()), ["rettifica", "rettificata_da"])
        chiamate = cursor.execute.call_args_list
        self.assertEqual([c.args[1][0] for c in chiamate],
                         ["rettifica", "rettificata_da"])
        self.assertEqual([c.args[1][1] for c in chiamate], [7, 7])
        # 🔴 Il test che conta: nei due versi le colonne del ponte si SCAMBIANO,
        # e le due metà della stessa query (JOIN e WHERE) devono restare
        # concordi. Se un giorno divergessero, il drawer mostrerebbe il numero
        # di un altro documento senza sollevare niente.
        sql_rettifica, sql_rettificata_da = (c.args[0] for c in chiamate)
        self.assertIn("f.id = fr.rettificata_id", sql_rettifica)
        self.assertIn("WHERE fr.fattura_id =", sql_rettifica)
        self.assertIn("f.id = fr.fattura_id", sql_rettificata_da)
        self.assertIn("WHERE fr.rettificata_id =", sql_rettificata_da)
