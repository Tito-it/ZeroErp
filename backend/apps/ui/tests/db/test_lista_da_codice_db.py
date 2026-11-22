# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: U39 e BE31 di brief-db-revisione-ui sul DATABASE PROVVISTO.
#        U39: le due letture «lista accesa per codice» del backend
#        (`UiRepository.get_lista_id`, `fetch_flag_perimetro`) passano dal BB
#        del DB `ui.fn_lista_da_codice`: la lista accesa risponde, quella spenta
#        e quella inesistente sono 404 `E_UI_LISTA_NON_TROVATA` dal DB.
#        BE31: una GUC `app.current_user_id` che non e' un id utente e' una
#        chiamata fuori contesto, col codice del dominio che chiede
#        (`E_UI_CHIAMATA_NON_VALIDA`, `E_PAGAMENTI_CHIAMATA_NON_VALIDA`), mai il
#        22P02 del cast — ne' nel backend (`utente_di_sessione`) ne' nel DB
#        (`ui.fn_lista_colonne_ricerca_full`, via `ha_ricerca_full`).
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
7) UtenteDiSessioneDbTests.test_guc_non_intera_codice_del_dominio
8) UtenteDiSessioneDbTests.test_ricerca_full_con_guc_non_intera_codice_ui
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.db._helpers import utente_di_sessione
from apps.core.db.lista_catalogo_repository import fetch_flag_perimetro
from apps.core.services.error_manager import ServiceError
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.db.ui_repository import UiRepository

_ACCESA = "ui.test_u39_accesa"
_SPENTA = "ui.test_u39_spenta"
_INESISTENTE = "ui.test_u39_inesistente"

# Valori che non sono un id di `auth_user` (colonna integer): lettere, segno,
# spazi, oltre il tetto dell'integer.
_GUC_NON_INTERE = ("abc", "-5", " 42", "4.2", "2147483648", "99999999999")


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

    def _leggi(self, codice_errore: str = "E_PAGAMENTI_CHIAMATA_NON_VALIDA") -> int | None:
        return utente_di_sessione(codice_errore=codice_errore, function_name="test")

    def test_guc_vuota_e_nessun_utente(self) -> None:
        _scrivi_guc("")
        self.assertIsNone(self._leggi())

    def test_guc_intera_e_l_utente(self) -> None:
        _scrivi_guc("2147483647")
        self.assertEqual(self._leggi(), 2_147_483_647)

    # Il codice e' quello che il chiamante dichiara: e' del suo dominio.
    def test_guc_non_intera_codice_del_dominio(self) -> None:
        for codice in ("E_PAGAMENTI_CHIAMATA_NON_VALIDA", "E_UI_CHIAMATA_NON_VALIDA"):
            for valore in _GUC_NON_INTERE:
                with self.subTest(codice=codice, valore=valore):
                    _scrivi_guc(valore)
                    with self.assertRaises(ServiceError) as ctx:
                        self._leggi(codice)
                    self.assertEqual(_codice_e_status(ctx.exception), (codice, 500))
                    self.assertEqual(
                        ctx.exception.context["app_current_user_id"], valore,
                    )

    # U38: lo stesso caso lo rifiuta anche il DB, col codice di `ui`, e il
    # backend lo riceve com'e' (non un DataError del driver).
    def test_ricerca_full_con_guc_non_intera_codice_ui(self) -> None:
        UiAdminRepository().create_definizione({
            "codice": _ACCESA,
            "descrizione": "U38 lista accesa",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })
        _scrivi_guc("abc")
        with self.assertRaises(Exception) as ctx:
            with transaction.atomic():
                UiRepository().ha_ricerca_full(_ACCESA)
        self.assertEqual(
            _codice_e_status(ctx.exception), ("E_UI_CHIAMATA_NON_VALIDA", 500),
        )
