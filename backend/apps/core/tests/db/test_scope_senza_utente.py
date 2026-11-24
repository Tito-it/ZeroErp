# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Un perimetro emittente senza utente si RIFIUTA: `auth_user_id=None`
#        che arriva al filtro di scope solleva `E_SCOPE_SENZA_UTENTE`, prima
#        di qualunque query, su ogni strada che lo risolve.
# Note: mock su connection.cursor, nessun DB.
#
# 🔴 PERCHE' ESISTE (2026-11-24, verifica critica di D-J). Fino a quel giorno
#    `None` voleva dire «nessuna restrizione», la risposta voluta per il
#    superuser Django. Ritirato il bypass, `None` arrivava solo da un chiamante
#    che dimenticava l'argomento, e la lista mostrava tutti gli emittenti senza
#    errore (il tool AI di ricerca contratti). Tre strade lo saltavano da se',
#    con un loro `if auth_user_id is not None`: la coda stampa, le rate dei
#    pagamenti, l'archiviazione della coda stampa. Questo file le prova tutte.
#
# Indice test:
#   1) il BB `fetch_emittenti_scope_ids`
#   2) `add_emittente_scope_condition`
#   3) il conteggio della coda stampa
#   4) le rate dei pagamenti
#   5) l'archiviazione della coda stampa
#   6) le letture di vendite con perimetro e i builder dei contesti di stampa
#      non hanno default per `auth_user_id`; la testata fattura con `None`
#      rifiuta (D-K6 a)
#   7) nessun modulo tiene una copia importata di `fetch_emittenti_scope_ids`
#      (il BB di test `perimetro_admin_globale_di_prova` patcha il nome nel modulo
#      del BB: una copia ne resta fuori e va sul DB), salvo quelle dichiarate
#   8) nessun sorgente fuori dal BB interroga le due funzioni DB di scope
#      (il resolver lo faceva fino a D-K5 a)
# ------------------------------------------------------------

from __future__ import annotations

import inspect
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError

_CURSOR = "django.db.connection.cursor"
_CODICE = "E_SCOPE_SENZA_UTENTE"


class ScopeSenzaUtenteTests(unittest.TestCase):
    """`None` non apre il perimetro: solleva, senza toccare il database."""

    def _rifiuta(self, chiamata) -> None:
        with patch(_CURSOR) as cursor:
            with self.assertRaises(ServiceError) as ctx:
                chiamata()
        self.assertEqual(ctx.exception.code, _CODICE)
        cursor.assert_not_called()

    def test_fetch_senza_utente(self):
        from apps.core.db.emittente_scope_helpers import fetch_emittenti_scope_ids
        self._rifiuta(lambda: fetch_emittenti_scope_ids(None))

    def test_condizione_senza_utente(self):
        from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
        self._rifiuta(lambda: add_emittente_scope_condition(
            [], [], auth_user_id=None, column="x.emittente_fiscale_id",
        ))

    def test_coda_stampa_senza_utente(self):
        from apps.vendite.db.pipeline_repository import VenditePipelineRepository
        self._rifiuta(lambda: VenditePipelineRepository().count_coda_stampa_per_stato(
            auth_user_id=None,
        ))

    def test_rate_senza_utente(self):
        from apps.pagamenti.db.pagamenti_repository import PagamentiRepository
        with patch.object(PagamentiRepository, "_guard_canale_sistema", autospec=True):
            self._rifiuta(lambda: PagamentiRepository().list_rate_paginata(
                auth_user_id=None, limit=10,
            ))

    # D-K6 a (2026-11-24): la testata della fattura non ha piu' il ramo che
    # con `None` saltava il filtro applicativo per il motore documentale.
    def test_testata_fattura_senza_utente(self):
        from apps.vendite.db.vendite_repository import VenditeRepository
        self._rifiuta(lambda: VenditeRepository().get_fattura_testata(
            7, auth_user_id=None,
        ))

    def test_archiviazione_stampa_senza_utente(self):
        from apps.core.services.coda_lavori import gestione_service
        with patch.object(gestione_service, "_guard_archiviazione"):
            self._rifiuta(lambda: gestione_service.imposta_archiviazione_stampa(
                object(), [1], archiviato=True, auth_user_id=None,
            ))


class LettureConPerimetroSenzaDefaultTests(unittest.TestCase):
    """6) Chi dimentica l'utente riceve un `TypeError`, non un `None` muto.

    🔴 Le tre letture della fattura passano da
    `VenditeRepository.get_fattura_testata`, dove fino a D-K6 a (2026-11-24)
    `None` era il ramo dichiarato del motore documentale e **saltava** il
    filtro applicativo: con il default `None` sul service, un chiamante che
    dimenticava l'argomento ci arrivava senza errore. Ritirato il ramo, `None`
    solleva dal BB come altrove (test `test_testata_fattura_senza_utente`); la
    firma lo dice gia', come per i repository. Lo stesso per i builder dei
    contesti di stampa, il cui default `None` era quel ramo.
    """

    def _senza_default(self, funzione) -> None:
        parametro = inspect.signature(funzione).parameters["auth_user_id"]
        self.assertIs(
            parametro.default, inspect.Parameter.empty,
            f"{funzione.__qualname__}: `auth_user_id` non deve avere default",
        )

    def test_letture_fattura(self):
        from apps.vendite.services import vendite_service
        for funzione in (
            vendite_service.get_fattura_dettaglio,
            vendite_service.get_fattura_giornale,
            vendite_service.list_fattura_righe_pagina,
        ):
            with self.subTest(funzione=funzione.__name__):
                self._senza_default(funzione)

    def test_builder_dei_contesti_di_stampa(self):
        from apps.documenti.services.context_builders.base import DocumentContextBuilder
        from apps.vendite.services import (
            contratto_document_context_builder as contratto,
            ddt_document_context_builder as ddt,
            fattura_document_context_builder as fattura,
            offerta_document_context_builder as offerta,
            ordine_document_context_builder as ordine,
            preventivo_document_context_builder as preventivo,
        )
        builder = [DocumentContextBuilder] + [
            classe
            for modulo in (contratto, ddt, fattura, offerta, ordine, preventivo)
            for classe in vars(modulo).values()
            if isinstance(classe, type)
            and issubclass(classe, DocumentContextBuilder)
            and classe is not DocumentContextBuilder
            and classe.__module__ == modulo.__name__
        ]
        self.assertEqual(len(builder), 7)
        for classe in builder:
            with self.subTest(builder=classe.__name__):
                self._senza_default(classe.build_context)

    def test_lista_mensile_dei_lotti(self):
        from apps.vendite.services import vendite_service
        self._senza_default(vendite_service.fn_lotti_mensile)

    def test_code_dei_resi(self):
        from apps.vendite.services import resi_service
        for funzione in (resi_service.list_da_accreditare, resi_service.list_da_riconsegnare):
            with self.subTest(funzione=funzione.__name__):
                self._senza_default(funzione)


# Scopo: (7) una copia importata con `from ... import` sfugge al patch del BB
#        di test e interroga il DB: il test resta verde, ma per un'altra
#        ragione (`pagamenti_repository` fino alla `/verifica` del 2026-11-24).
class NessunaCopiaDelRisolutoreTests(unittest.TestCase):
    # Dichiarate: chi le ha si patcha a parte, col suo percorso.
    _COPIE_DICHIARATE = {"apps.core.services.coda_lavori.gestione_service"}

    def test_nessuna_copia_importata(self):
        import importlib
        import pkgutil

        import apps
        from apps.core.db import emittente_scope_helpers

        originale = emittente_scope_helpers.fetch_emittenti_scope_ids
        copie: list[str] = []
        for info in pkgutil.walk_packages(apps.__path__, prefix="apps."):
            nome = info.name
            if ".tests" in nome or ".migrations" in nome or nome == emittente_scope_helpers.__name__:
                continue
            if not nome.endswith(("_repository", "_service")):
                continue
            try:
                modulo = importlib.import_module(nome)
            except Exception:
                continue  # un modulo che non si importa non e' il caso di qui
            if getattr(modulo, "fetch_emittenti_scope_ids", None) is originale:
                copie.append(nome)
        self.assertEqual(
            sorted(set(copie) - self._COPIE_DICHIARATE), [],
            "moduli con una copia importata di `fetch_emittenti_scope_ids`: "
            "chiamala dal modulo (`emittente_scope_helpers.fetch_emittenti_scope_ids`) "
            "o dichiarala qui col suo patch",
        )


# 8) Le due funzioni DB del perimetro le interroga SOLO il BB. Fino al
#    2026-11-24 `PermissionResolver.get_emittenti_*_ids` lo faceva per conto
#    suo: seconda sede della stessa domanda, e con `user=None` un 500 generico
#    invece di `E_SCOPE_SENZA_UTENTE` (D-K5 a, brief-db-porte-aperte-dalla-sola-guc
#    §4.7). Una chiamata SQL nuova, anche dentro una query composta, salta il
#    rifiuto del BB: si legge il sorgente, non i moduli importati.
_CHIAMATA_SQL_SCOPE = re.compile(r"fn_get_emittenti_scope_(?:pk|sr)_ids\(")


class NessunaSecondaSedeSqlTests(unittest.TestCase):
    def test_solo_il_bb_interroga_le_funzioni_di_scope(self):
        from apps.core.db import emittente_scope_helpers

        radice = Path(emittente_scope_helpers.__file__).resolve().parents[2]
        sede = Path(emittente_scope_helpers.__file__).resolve()
        fuori: list[str] = []
        for path in radice.rglob("*.py"):
            rel = path.relative_to(radice).as_posix()
            if "/tests/" in rel or "/migrations/" in rel or path.resolve() == sede:
                continue
            for n, riga in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _CHIAMATA_SQL_SCOPE.search(riga) and not riga.lstrip().startswith("#"):
                    fuori.append(f"{rel}:{n}")
        self.assertEqual(
            fuori, [],
            "chiamate dirette alle funzioni di scope: passa da "
            "`emittente_scope_helpers.fetch_emittenti_scope_ids`",
        )

    # Il controllo della regex: senza, un presidio con la regex sbagliata e'
    # verde per sempre.
    def test_la_regex_riconosce_la_chiamata(self):
        self.assertTrue(_CHIAMATA_SQL_SCOPE.search(
            'cursor.execute("SELECT script.fn_get_emittenti_scope_sr_ids(%s)", [1])'))
        self.assertTrue(_CHIAMATA_SQL_SCOPE.search(
            "col = ANY(script.fn_get_emittenti_scope_pk_ids(%s))"))
        self.assertFalse(_CHIAMATA_SQL_SCOPE.search(
            "Wrapper su fn_get_emittenti_scope_pk_ids (canonica"))
