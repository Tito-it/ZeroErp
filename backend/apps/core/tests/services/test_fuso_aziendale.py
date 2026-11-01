# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del BB `core/services/fuso_aziendale`, di
#        `FusoAziendaleMiddleware` e di `ComandoAziendale`: il fuso dell'azienda
#        e' un dato del DB, si legge una volta, non ha ripieghi, e il fuso del
#        processo non cambia nessun risultato.
#        Repository mockato: nessun accesso al DB (la giuntura col DB vero sta
#        in `apps/core/tests/db/test_fuso_aziendale_db.py`).
# ------------------------------------------------------------
"""Indice test.

FusoAziendaleLetturaTests
 1. test_si_legge_una_volta_per_processo
 2. test_nome_sconosciuto_a_python_e_un_errore_di_configurazione
 3. test_errore_del_db_si_propaga_senza_ripiego
 4. test_forzato_rimette_il_valore_precedente_anche_su_errore
OggiAziendaleTests
 5. test_le_23_30_utc_sono_gia_domani_a_roma
 6. test_a_new_york_lo_stesso_istante_e_ancora_ieri
 7. test_il_fuso_del_processo_non_conta
AttivazioneTests
 8. test_il_middleware_attiva_il_fuso_e_lo_ritira
 9. test_il_middleware_ritira_il_fuso_anche_su_errore
10. test_il_comando_gira_nel_fuso_dell_azienda
PercorsiTecniciTests
11. test_health_risponde_col_db_irraggiungibile
12. test_un_api_col_db_irraggiungibile_fallisce_ancora
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest import TestCase
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone

from apps.core.management.comando_aziendale import ComandoAziendale
from apps.core.middleware.fuso_aziendale_middleware import FusoAziendaleMiddleware
from apps.core.services import fuso_aziendale as modulo
from apps.core.services.fuso_aziendale import (
    fuso_aziendale,
    fuso_aziendale_forzato,
    oggi_aziendale,
)
from apps.core.services.service_errors import ServiceError

_REPO = "apps.core.services.fuso_aziendale.CoreRepository"


class FusoAziendaleLetturaTests(SimpleTestCase):
    """La lettura: una per processo, dal DB, senza ripieghi."""

    # Scopo: svuota la cache del modulo per il test e la rimette com'era (il
    #        runner l'ha scaldata col valore vero: gli altri test la usano).
    def setUp(self) -> None:
        precedente = modulo._fuso
        modulo._fuso = None
        self.addCleanup(setattr, modulo, "_fuso", precedente)

    # 1. Due chiamate, una sola domanda al DB: il fuso si legge al primo uso
    #    e non si invalida (T-6).
    def test_si_legge_una_volta_per_processo(self) -> None:
        with patch(_REPO) as repo:
            repo.return_value.get_fuso_operativo.return_value = "Asia/Tokyo"
            self.assertEqual(fuso_aziendale().key, "Asia/Tokyo")
            self.assertEqual(fuso_aziendale().key, "Asia/Tokyo")
        repo.return_value.get_fuso_operativo.assert_called_once_with()

    # 2. Un nome che il DB ha accettato ma Python non conosce (tzdata
    #    dell'host diversa da quella del server PG) ferma tutto: nessun UTC.
    def test_nome_sconosciuto_a_python_e_un_errore_di_configurazione(self) -> None:
        with patch(_REPO) as repo:
            repo.return_value.get_fuso_operativo.return_value = "Marte/Olympus"
            with self.assertRaises(ImproperlyConfigured):
                fuso_aziendale()
        self.assertIsNone(modulo._fuso)

    # 3. Il fail-loud del DB (E_CONFIG_MANCANTE) arriva al chiamante, e la
    #    cache resta vuota: la domanda successiva riprova.
    def test_errore_del_db_si_propaga_senza_ripiego(self) -> None:
        with patch(_REPO) as repo:
            repo.return_value.get_fuso_operativo.side_effect = ServiceError(
                code="E_CONFIG_MANCANTE", message="SYSTEM_FUSO_ORARIO",
            )
            with self.assertRaises(ServiceError):
                fuso_aziendale()
        self.assertIsNone(modulo._fuso)

    # 4. Il forzato dei test rimette il valore di prima, anche se il blocco
    #    solleva.
    def test_forzato_rimette_il_valore_precedente_anche_su_errore(self) -> None:
        with fuso_aziendale_forzato("Europe/Rome"):
            with self.assertRaises(RuntimeError), fuso_aziendale_forzato("Asia/Tokyo"):
                self.assertEqual(fuso_aziendale().key, "Asia/Tokyo")
                raise RuntimeError
            self.assertEqual(fuso_aziendale().key, "Europe/Rome")


class OggiAziendaleTests(SimpleTestCase):
    """L'«oggi» di Python e' il giorno dell'azienda, non del processo."""

    _A_CAVALLO = datetime(2026, 9, 14, 23, 30, tzinfo=UTC)

    # 5. Le 23:30 UTC del 14 settembre sono le 01:30 del 15 a Roma (+02:00).
    #    E' la finestra in cui `date.today()` di un processo UTC sbaglia.
    @fuso_aziendale_forzato("Europe/Rome")
    def test_le_23_30_utc_sono_gia_domani_a_roma(self) -> None:
        with patch("django.utils.timezone.now", return_value=self._A_CAVALLO):
            self.assertEqual(oggi_aziendale().isoformat(), "2026-09-15")

    # 6. Il verso opposto: a New York (−04:00 a settembre) le 02:00 UTC del
    #    15 sono ancora il 14.
    @fuso_aziendale_forzato("America/New_York")
    def test_a_new_york_lo_stesso_istante_e_ancora_ieri(self) -> None:
        istante = datetime(2026, 9, 15, 2, 0, tzinfo=UTC)
        with patch("django.utils.timezone.now", return_value=istante):
            self.assertEqual(oggi_aziendale().isoformat(), "2026-09-14")

    # 7. ⭐ Ne' `TIME_ZONE` ne' il fuso attivato cambiano la risposta: il BB
    #    dichiara il proprio fuso.
    @fuso_aziendale_forzato("Europe/Rome")
    @override_settings(TIME_ZONE="Pacific/Pago_Pago")
    def test_il_fuso_del_processo_non_conta(self) -> None:
        with patch("django.utils.timezone.now", return_value=self._A_CAVALLO), \
                timezone.override("Pacific/Pago_Pago"):
            self.assertEqual(oggi_aziendale().isoformat(), "2026-09-15")


class AttivazioneTests(SimpleTestCase):
    """Middleware e comandi attivano il fuso dell'azienda, e lo ritirano."""

    # 8. Durante la richiesta il fuso attivo e' quello dell'azienda; dopo, si
    #    torna al default (`TIME_ZONE`).
    @fuso_aziendale_forzato("Asia/Tokyo")
    def test_il_middleware_attiva_il_fuso_e_lo_ritira(self) -> None:
        visto: list[str] = []

        def vista(_request: HttpRequest) -> HttpResponse:
            visto.append(timezone.get_current_timezone_name())
            return HttpResponse()

        timezone.deactivate()
        FusoAziendaleMiddleware(vista)(HttpRequest())
        self.assertEqual(visto, ["Asia/Tokyo"])
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")

    # 9. Una vista che solleva non lascia il fuso attivo sul thread.
    @fuso_aziendale_forzato("Asia/Tokyo")
    def test_il_middleware_ritira_il_fuso_anche_su_errore(self) -> None:
        def vista(_request: HttpRequest) -> HttpResponse:
            raise RuntimeError

        timezone.deactivate()
        with self.assertRaises(RuntimeError):
            FusoAziendaleMiddleware(vista)(HttpRequest())
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")

    # 10. `handle` di un comando gira nel fuso dell'azienda.
    @fuso_aziendale_forzato("Asia/Tokyo")
    def test_il_comando_gira_nel_fuso_dell_azienda(self) -> None:
        visto: list[str] = []

        class Comando(ComandoAziendale):
            def handle(self, *args, **options):
                visto.append(timezone.get_current_timezone_name())

        timezone.deactivate()
        Comando().execute(no_color=True, force_color=False, skip_checks=True)
        self.assertEqual(visto, ["Asia/Tokyo"])
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")


class PercorsiTecniciTests(TestCase):
    """I percorsi tecnici non leggono il fuso: `/health` vive senza DB."""

    # ⚠️ `unittest.TestCase`, non `SimpleTestCase`: deve essere il DB a
    #    rifiutare (`ensure_connection` patchata). Col recinto di
    #    `SimpleTestCase` la query cadrebbe prima, con
    #    `DatabaseOperationForbidden`, e il test 11 senza la correzione sarebbe
    #    rosso per il motivo sbagliato. Nessun database dichiarato: il runner
    #    non ne crea (vedi `zeroerp_backend/test_runner.py`).

    # Scopo: cache del fuso VUOTA (altrimenti il middleware non toccherebbe il
    #        DB e il test sarebbe verde per sottrazione) e DB che rifiuta ogni
    #        connessione, come nel job `docker` della CI senza Postgres.
    def setUp(self) -> None:
        precedente = modulo._fuso
        modulo._fuso = None
        self.addCleanup(setattr, modulo, "_fuso", precedente)
        for conn in connections.all():
            conn.close()

        def db_giu(_self: BaseDatabaseWrapper) -> None:
            raise OperationalError("connection refused (simulato)")

        patcher = patch.object(BaseDatabaseWrapper, "ensure_connection", db_giu)
        patcher.start()
        self.addCleanup(patcher.stop)

    # 11. ⭐ La sonda di vita del processo, con TUTTA la catena dei middleware:
    #     200 col DB irraggiungibile. Fino al 2026-11-01 il fuso la leggeva e
    #     rispondeva 500 (CI `docker`, «Run container and smoke-test»).
    def test_health_risponde_col_db_irraggiungibile(self) -> None:
        risposta = Client().get("/health", secure=True)
        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(risposta.json(), {"status": "ok"})
        self.assertIsNone(modulo._fuso)

    # 12. Controprova: fuori dai percorsi tecnici il fail-loud resta. Un'API
    #     col DB irraggiungibile non riceve un fuso di ripiego.
    def test_un_api_col_db_irraggiungibile_fallisce_ancora(self) -> None:
        richiesta = RequestFactory().get("/api/v1/core/qualsiasi/")
        with self.assertRaises(OperationalError):
            FusoAziendaleMiddleware(lambda _r: HttpResponse())(richiesta)
        self.assertIsNone(modulo._fuso)
