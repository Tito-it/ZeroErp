# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
5) test_gia_accreditato_dalla_fn_condivisa — la formula non si riscrive
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
    for descr, nome in zip(cursor.description, _COLS):
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

    # Scopo: 🔴 la quota accreditata si legge dalla fn del DB, che e' il punto
    # UNICO della formula (la usa anche `vw_resi_da_accreditare`). Rifarla qui
    # con un SUM sul ponte darebbe una seconda verita' — e sbagliata: su un kit
    # N righe di ponte portano la STESSA quota padre, e sommarle la
    # moltiplicherebbe. Se questo test diventa rosso perche' qualcuno ha
    # scritto un SUM inline, il difetto e' quello, non il test.
    @patch("apps.vendite.db.resi_repository.connection")
    def test_gia_accreditato_dalla_fn_condivisa(self, mock_conn) -> None:
        cursor = MagicMock()
        cursor.description = []
        cursor.fetchall.return_value = []
        _mock_connection(mock_conn, cursor)

        from apps.vendite.db.resi_repository import ResiRepository

        ResiRepository().list_righe(7)

        sql = cursor.execute.call_args[0][0]
        self.assertIn("vendite.fn_resi_riga_accreditato_partita(rr.id)", sql)
        self.assertIn("AS gia_accreditato", sql)
        self.assertNotIn("SUM(qta_partita)", sql)
