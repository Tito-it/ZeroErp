# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BE10 di brief-db-revisione-ui sul DATABASE PROVVISTO: la lettura della
#        misura di partenza (`fetch_misura_lista`, su `ui.fn_misura_lista`) lega,
#        e da' lo STESSO numero che la configurazione della lista mostra
#        all'utente (`pagina_dimensione` di `ui.fn_resolve_lista_config`): la
#        regola e' una.
# Note: ⭐ La giuntura, non la regola: la cascata (preferenza, preset, default
#       dell'uso) la provano i pgTAP. Qui lista, colonna, preset e utente si
#       COSTRUISCONO, con una misura del preset diversa dal default, che e' il
#       caso che distingue la lettura dalla costante. Transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) MisuraListaDbTests.test_la_misura_e_quella_del_preset
2) MisuraListaDbTests.test_uguale_alla_configurazione_della_lista
3) MisuraListaDbTests.test_lista_inesistente_404
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.db.lista_catalogo_repository import fetch_misura_lista
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.db.ui_repository import UiRepository

_LISTA = "ui.test_be10_misura"
_MISURA_DEL_PRESET = 50


class MisuraListaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("ui.fn_misura_lista(character varying,integer,bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        repo = UiAdminRepository()
        lista_id = repo.create_definizione({
            "codice": _LISTA,
            "descrizione": "BE10 misura di partenza",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })
        colonna_id = repo.create_colonna({
            "lista_id": lista_id,
            "codice": "data",
            "etichetta": "data",
            "campo_sorgente": "data_documento",
            "tipo_colonna": "informazione",
            "tipo_dato": "string",
            "ordine_default": 1,
            "ordinabile": True,
            "filtrabile": False,
            "esportabile": False,
            "attivo": True,
        })
        preset_id = repo.create_preset({
            "lista_id": lista_id,
            "codice": "be10_sistema",
            "descrizione": "Preset di sistema BE10",
            "ambito": "sistema",
            "pagina_dimensione": _MISURA_DEL_PRESET,
            "attivo": True,
        })
        # Un preset vale come base solo con contenuto (U3).
        repo.replace_preset_colonne(preset_id, [{"colonna_id": colonna_id, "ordine": 1}])
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_user (password, is_superuser, username, first_name, "
                "last_name, email, is_staff, is_active, date_joined) "
                "VALUES ('!', false, 'test_be10_misura', '', '', '', false, true, now()) "
                "RETURNING id",
            )
            self.auth_user_id = int(cur.fetchone()[0])

    def _misura(self, lista_codice: str = _LISTA) -> int:
        return fetch_misura_lista(
            lista_codice, auth_user_id=self.auth_user_id, emittente_fiscale_id=None,
        )

    def test_la_misura_e_quella_del_preset(self) -> None:
        self.assertEqual(self._misura(), _MISURA_DEL_PRESET)

    def test_uguale_alla_configurazione_della_lista(self) -> None:
        config = UiRepository().resolve_lista_config(
            lista_codice=_LISTA, auth_user_id=self.auth_user_id, emittente_fiscale_id=None,
        )
        self.assertEqual(self._misura(), config["pagina_dimensione"])

    def test_lista_inesistente_404(self) -> None:
        with self.assertRaises(Exception) as ctx:
            with transaction.atomic():
                self._misura("ui.test_be10_inesistente")
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(
            (errore.code, ErrorTranslator.get_http_status(errore)),
            ("E_UI_LISTA_NON_TROVATA", 404),
        )
