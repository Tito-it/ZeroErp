# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: U39, BE31 e BE34 di brief-db-revisione-ui sul DATABASE PROVVISTO.
#        U39: le due letture «lista accesa per codice» del backend
#        (`UiRepository.get_lista_id`, `fetch_flag_perimetro`) passano dal BB
#        del DB `ui.fn_lista_da_codice`: la lista accesa risponde, quella spenta
#        e quella inesistente sono 404 `E_UI_LISTA_NON_TROVATA` dal DB.
#        BE34: l'utente di sessione (GUC `app.current_user_id`) ha una regola
#        sola, il BB DB `script.fn_utente_di_sessione`, che legge anche il BB
#        backend `utente_di_sessione`. Un valore che non e' l'id di un utente e'
#        `E_SCRIPT_CHIAMATA_NON_VALIDA` (500), mai il 22P02 del cast: dal BB
#        backend, da `ui.fn_lista_colonne_ricerca_full` (via `ha_ricerca_full`)
#        e da una lettura sotto RLS (giro 8b, le policy).
# Note: ⭐ La giuntura, non la regola: la regola di `fn_lista_da_codice` la
#       provano i pgTAP. Qui la lista si COSTRUISCE (accesa e spenta), e la GUC
#       si scrive con `set_config(…, true)`: tutto in transazione ANNULLATA.
#       Col mock il binding non si vede: e' il motivo di questo file.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) ListaDaCodiceDbTests.test_get_lista_id_lista_accesa
2) ListaDaCodiceDbTests.test_get_lista_id_spenta_o_inesistente_404
3) ListaDaCodiceDbTests.test_flag_perimetro_lista_accesa
4) ListaDaCodiceDbTests.test_flag_perimetro_spenta_o_inesistente_404
5) UtenteDiSessioneDbTests.test_guc_vuota_e_nessun_utente
6) UtenteDiSessioneDbTests.test_guc_intera_e_l_utente
7) UtenteDiSessioneDbTests.test_guc_non_valida_codice_del_bb_db
8) UtenteDiSessioneDbTests.test_ricerca_full_con_guc_non_valida
9) UtenteDiSessioneDbTests.test_lettura_rls_con_guc_non_valida
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.db._helpers import utente_di_sessione
from apps.core.db.lista_catalogo_repository import fetch_flag_perimetro
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.db.ui_repository import UiRepository

_ACCESA = "ui.test_u39_accesa"
_SPENTA = "ui.test_u39_spenta"
_INESISTENTE = "ui.test_u39_inesistente"

# Valori che non sono un id di `auth_user` (colonna integer): lettere, segno,
# spazi, zero, zeri in testa, oltre il tetto dell'integer. `0` e `007` sono i
# due che la copia Python di prima accettava e il DB rifiuta (BE34).
_GUC_NON_VALIDE = (
    "abc", "-5", " 42", "4.2", "0", "007", "2147483648", "99999999999",
)
_E_GUC = ("E_SCRIPT_CHIAMATA_NON_VALIDA", 500)


# Scopo: il codice e lo status che il client vede per un'eccezione — quella
#        Python del backend o quella del DB tradotta dall'envelope.
def _codice_e_status(exc: BaseException) -> tuple[str, int]:
    errore = ErrorTranslator.to_api_error(exc)
    return errore.code, ErrorTranslator.get_http_status(errore)


def _scrivi_guc(valore: str) -> None:
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.current_user_id', %s, true)", [valore])


class ListaDaCodiceDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("ui.fn_lista_da_codice(character varying)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        repo = UiAdminRepository()
        self.lista_id = repo.create_definizione({
            "codice": _ACCESA,
            "descrizione": "U39 lista accesa",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })
        repo.create_definizione({
            "codice": _SPENTA,
            "descrizione": "U39 lista spenta",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": False,
        })

    # Scopo: la lettura fallisce con `E_UI_LISTA_NON_TROVATA` 404, in un
    #        savepoint: l'errore del DB interrompe la transazione.
    def _assert_404(self, leggi) -> None:
        for codice in (_SPENTA, _INESISTENTE):
            with self.subTest(codice=codice):
                with self.assertRaises(Exception) as ctx:
                    with transaction.atomic():
                        leggi(codice)
                self.assertEqual(
                    _codice_e_status(ctx.exception), ("E_UI_LISTA_NON_TROVATA", 404),
                )

    def test_get_lista_id_lista_accesa(self) -> None:
        self.assertEqual(UiRepository().get_lista_id(_ACCESA), self.lista_id)

    def test_get_lista_id_spenta_o_inesistente_404(self) -> None:
        self._assert_404(UiRepository().get_lista_id)

    def test_flag_perimetro_lista_accesa(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT multi_emittente, perimetro_emittente "
                "FROM ui.lista_definizione WHERE id = %s",
                [self.lista_id],
            )
            multi, perimetro = cur.fetchone()
        flag = fetch_flag_perimetro(_ACCESA)
        self.assertEqual(
            (flag.multi_emittente, flag.perimetro_emittente), (multi, perimetro),
        )

    def test_flag_perimetro_spenta_o_inesistente_404(self) -> None:
        self._assert_404(fetch_flag_perimetro)


class UtenteDiSessioneDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    def _leggi(self) -> int | None:
        return utente_di_sessione(function_name="test")

    # Scopo: `leggi` fallisce col codice del BB DB, in un savepoint: l'errore
    #        del DB interrompe la transazione.
    def _assert_guc_rifiutata(self, valore: str, leggi) -> None:
        _scrivi_guc(valore)
        with self.assertRaises(Exception) as ctx:
            with transaction.atomic():
                leggi()
        self.assertEqual(_codice_e_status(ctx.exception), _E_GUC)

    def test_guc_vuota_e_nessun_utente(self) -> None:
        _scrivi_guc("")
        self.assertIsNone(self._leggi())

    def test_guc_intera_e_l_utente(self) -> None:
        _scrivi_guc("2147483647")
        self.assertEqual(self._leggi(), 2_147_483_647)

    # Il BB backend non ha piu' una regola sua: il rifiuto e' quello del DB.
    def test_guc_non_valida_codice_del_bb_db(self) -> None:
        for valore in _GUC_NON_VALIDE:
            with self.subTest(valore=valore):
                self._assert_guc_rifiutata(valore, self._leggi)

    # U38: lo stesso caso dalla ricerca della lista, e il backend lo riceve
    # com'e' (non un DataError del driver).
    def test_ricerca_full_con_guc_non_valida(self) -> None:
        UiAdminRepository().create_definizione({
            "codice": _ACCESA,
            "descrizione": "U38 lista accesa",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })
        self._assert_guc_rifiutata(
            "abc", lambda: UiRepository().ha_ricerca_full(_ACCESA),
        )

    # Giro 8b: le policy RLS leggono l'utente dal BB. Una SELECT su una tabella
    # protetta, da operatore con la GUC sporca, da' il codice invece del 22P02.
    # ⚠️ `app.ruolo_applicativo` = OPERATORE: e' il ramo della policy che legge
    #    l'utente. Solo SELECT, in transazione annullata.
    # ⛔ Il cliente si FABBRICA: la policy si valuta riga per riga, e su una
    #    tabella vuota (il DB della CI nasce dal solo seed) la SELECT non la
    #    chiama mai e il rifiuto atteso non arriva. Il builder va PRIMA del
    #    ruolo operatore, come nei pgTAP: senza contesto si sceglie l'azienda
    #    da se'.
    # ⛔ Il mondo da solo NON basta: porta billing account, istanza e ruolo, ma
    #    nessuna riga di `anagrafiche.clienti` (rosso in CI il 2026-11-26,
    #    verde su dbdev per i clienti che c'erano). La riga la scrive
    #    `fn_pgtap_crea_cliente` sull'emittente del mondo, come in
    #    `anagrafiche/tests/db/test_ricerca_liste_db`. E la lettura va sulla
    #    riga COSTRUITA: le altre righe del DB non devono poter tenere in piedi
    #    il test.
    def test_lettura_rls_con_guc_non_valida(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT emittente_soggetto_ruolo_id"
                "  FROM dbops.fn_pgtap_crea_mondo_cliente('GUC NON VALIDA', 'GNV')"
            )
            emittente_sr = cur.fetchone()[0]
            cur.execute(
                "SELECT cliente_id FROM dbops.fn_pgtap_crea_cliente('GUC NON VALIDA', NULL, %s)",
                [emittente_sr],
            )
            riga = cur.fetchone()
            self.assertIsNotNone(riga, "il builder non ha scritto il cliente")
            cliente_id = riga[0]
            cur.execute("SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true)")

        def leggi() -> None:
            with connection.cursor() as cur:
                cur.execute("SELECT count(*) FROM anagrafiche.clienti WHERE id = %s", [cliente_id])
                cur.fetchone()

        self._assert_guc_rifiutata("abc", leggi)
