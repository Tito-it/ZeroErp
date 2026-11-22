# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BE20 e BE25 (2) di brief-db-revisione-ui sul DATABASE PROVVISTO: la
#        lettura dell'ordinamento di partenza (`fetch_ordinamento_lista`, su
#        `ui.fn_ordinamento_lista`) lega, e da' per ogni voce il CAMPO SORGENTE
#        con cui il repository ordina — non il codice della colonna, che e'
#        cio' che il preset dichiara (Q7, Q40 (b)).
# Note: ⭐ La giuntura, non la regola: quale preset vale, e quali voci cadono,
#       lo provano i pgTAP del resolver. Qui lista, colonne, preset e utente si
#       COSTRUISCONO, con un codice di colonna diverso dal suo campo sorgente,
#       che e' il caso che distingue le due convenzioni. Tutto in transazione
#       ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) OrdinamentoListaDbTests.test_la_voce_porta_il_campo_sorgente
2) OrdinamentoListaDbTests.test_colonna_non_ordinabile_cade
3) OrdinamentoListaDbTests.test_preset_col_campo_sorgente_al_posto_del_codice_400
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.db.lista_catalogo_repository import fetch_ordinamento_lista
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import Annulla, apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.services.lista_preset_admin_service import ListaPresetAdminService

_LISTA = "ui.test_be25_ordinamento"


class OrdinamentoListaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("ui.fn_ordinamento_lista(character varying,integer,bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        repo = UiAdminRepository()
        lista_id = repo.create_definizione({
            "codice": _LISTA,
            "descrizione": "BE25 ordinamento di partenza",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })

        def colonna(codice: str, campo: str, *, ordinabile: bool, ordine: int) -> int:
            return repo.create_colonna({
                "lista_id": lista_id,
                "codice": codice,
                "etichetta": codice,
                "campo_sorgente": campo,
                "tipo_colonna": "informazione",
                "tipo_dato": "string",
                "ordine_default": ordine,
                "ordinabile": ordinabile,
                "filtrabile": False,
                "esportabile": False,
                "attivo": True,
            })

        data_id = colonna("data", "data_documento", ordinabile=True, ordine=1)
        nota_id = colonna("nota", "nota_testo", ordinabile=False, ordine=2)
        self.preset_id = repo.create_preset({
            "lista_id": lista_id,
            "codice": "be25_sistema",
            "descrizione": "Preset di sistema BE25",
            "ambito": "sistema",
            "ordinamento_default": [
                {"col": "nota", "dir": "asc"},
                {"col": "data", "dir": "desc"},
            ],
            "attivo": True,
        })
        # Un preset vale come base solo con contenuto (U3).
        repo.replace_preset_colonne(self.preset_id, [
            {"colonna_id": data_id, "ordine": 1},
            {"colonna_id": nota_id, "ordine": 2},
        ])
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_user (password, is_superuser, username, first_name, "
                "last_name, email, is_staff, is_active, date_joined) "
                "VALUES ('!', false, 'test_be25_ordinamento', '', '', '', false, true, now()) "
                "RETURNING id",
            )
            self.auth_user_id = int(cur.fetchone()[0])

    def _voci(self) -> list[dict[str, str]]:
        return fetch_ordinamento_lista(
            _LISTA, auth_user_id=self.auth_user_id, emittente_fiscale_id=None,
        )

    def test_la_voce_porta_il_campo_sorgente(self) -> None:
        self.assertEqual(
            self._voci(),
            [{"col": "data", "dir": "desc", "campo_sorgente": "data_documento"}],
        )

    # La voce di una colonna che non si ordina la toglie il DB: il BB della
    # base view applica la prima voce che resta, che e' nella whitelist.
    def test_colonna_non_ordinabile_cade(self) -> None:
        self.assertNotIn("nota", [v["col"] for v in self._voci()])


    # BE20 (Q40 (b)): il preset nomina la colonna col CODICE. Il campo sorgente
    # al posto del codice lo rifiuta il guard del DB, e dal CRUD admin arriva
    # come 400 leggibile, sul campo `ordinamento_default`.
    def test_preset_col_campo_sorgente_al_posto_del_codice_400(self) -> None:
        with self.assertRaises(Annulla):
            with transaction.atomic():
                with self.assertRaises(Exception) as ctx:
                    with transaction.atomic():
                        ListaPresetAdminService().update_preset(
                            self.preset_id,
                            {"ordinamento_default": [{"col": "data_documento", "dir": "asc"}]},
                        )
                errore = ErrorTranslator.to_api_error(ctx.exception)
                self.assertEqual(errore.code, "E_UI_CONFIGURAZIONE_FORMA")
                self.assertEqual(ErrorTranslator.get_http_status(errore), 400)
                self.assertIn("ordinamento_default", errore.fields or ())
                raise Annulla
