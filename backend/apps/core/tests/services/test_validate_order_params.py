# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I due `validate_order_params` (service e ricerca universale) giudicano
#        la direzione con il predicato unico `order_dir_ammessa`.
# Note: nessun DB; il log a DB lo spegne il runner dei test (ERROR_LOG_DB_ENABLED).
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Fino al 2026-09-26 `list_helpers.validate_order_params` confrontava la direzione
con un suo insieme `{asc, desc}`, CASE-SENSITIVE: `DESC` era un 400 sulle liste
validate li' e passava su tutte le altre (dove giudica `sql_order_direction`).
Meta' dei chiamanti rimediava con un `.lower()` scritto a mano. Ora la regola
e' una, `order_dir_ammessa`, e il valore torna normalizzato.

Indice test:

 1) test_desc_maiuscolo_ammesso_e_normalizzato
 2) test_spazi_ai_lati_ammessi
 3) test_direzione_estranea_rifiutata_col_codice_di_dominio
 4) test_assenza_rifiutata_senza_nullable
 5) test_assenza_ammessa_con_nullable_torna_none
 6) test_colonna_fuori_whitelist_invariata
 7) test_ricerca_desc_minuscolo_torna_maiuscolo
 8) test_ricerca_direzione_estranea_rifiutata_anche_senza_colonna
 9) test_ricerca_senza_colonna_ne_direzione
"""

import unittest

from apps.core.api.search_validators import validate_order_params as validate_ricerca
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.service_errors import ServiceError

_COLONNE = frozenset({"codice", "descrizione"})


def _valida(order_by, order_dir, *, nullable=False):
    return validate_order_params(
        order_by, order_dir,
        allowed_columns=_COLONNE, error_code="E_TEST_VALIDATION",
        function_name="test", nullable=nullable,
    )


class ValidateOrderParamsServiceTests(unittest.TestCase):

    # Scopo: `DESC` e' la stessa cosa di `desc`, e torna in forma canonica.
    def test_desc_maiuscolo_ammesso_e_normalizzato(self):
        self.assertEqual(_valida("codice", "DESC"), ("codice", "desc"))
        self.assertEqual(_valida("codice", "Asc"), ("codice", "asc"))

    # Scopo: come `sql_order_direction`: gli spazi ai lati non contano.
    def test_spazi_ai_lati_ammessi(self):
        self.assertEqual(_valida("codice", " desc "), ("codice", "desc"))

    # Scopo: ⛔ un valore estraneo e' il 400 del dominio.
    def test_direzione_estranea_rifiutata_col_codice_di_dominio(self):
        for estranea in ("giu", "descending", "ASC NULLS LAST"):
            with self.subTest(order_dir=estranea):
                with self.assertRaises(ServiceError) as ctx:
                    _valida("codice", estranea)
                self.assertEqual(ctx.exception.code, "E_TEST_VALIDATION")

    # Scopo: senza `nullable` la direzione e' obbligatoria, come prima.
    def test_assenza_rifiutata_senza_nullable(self):
        for assente in (None, "", "  "):
            with self.subTest(order_dir=assente):
                with self.assertRaises(ServiceError):
                    _valida("codice", assente)

    # Scopo: con `nullable` l'assenza (anche vuota) e' `None`: decide il
    #        default del repository.
    def test_assenza_ammessa_con_nullable_torna_none(self):
        self.assertEqual(_valida(None, None, nullable=True), (None, None))
        self.assertEqual(_valida("codice", "", nullable=True), ("codice", None))

    # Scopo: il contratto della COLONNA non cambia: resta esatto.
    def test_colonna_fuori_whitelist_invariata(self):
        for colonna in ("CODICE", "prezzo", ""):
            with self.subTest(order_by=colonna):
                with self.assertRaises(ServiceError):
                    _valida(colonna, "asc")


class ValidateOrderParamsRicercaTests(unittest.TestCase):

    # Scopo: la ricerca universale vuole la forma maiuscola.
    def test_ricerca_desc_minuscolo_torna_maiuscolo(self):
        self.assertEqual(
            validate_ricerca("soggetto_codice", " desc "), ("soggetto_codice", "DESC"),
        )
        self.assertEqual(validate_ricerca("soggetto_codice", None), ("soggetto_codice", "ASC"))

    # Scopo: ⛔ la direzione si giudica anche quando la colonna manca: prima
    #        `?order_dir=giu` da solo passava muto.
    def test_ricerca_direzione_estranea_rifiutata_anche_senza_colonna(self):
        for colonna in ("soggetto_codice", None):
            with self.subTest(order_by=colonna):
                with self.assertRaises(ServiceError) as ctx:
                    validate_ricerca(colonna, "giu")
                self.assertEqual(ctx.exception.code, "E_SEARCH_VALIDATION")

    # Scopo: nessun parametro = nessun ordinamento richiesto.
    def test_ricerca_senza_colonna_ne_direzione(self):
        self.assertEqual(validate_ricerca(None, None), (None, None))
