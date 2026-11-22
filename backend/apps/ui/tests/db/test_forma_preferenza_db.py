# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BE8 e BE11 di brief-db-revisione-ui (giro 2), e BE21 (giro 5), sul
#        DATABASE PROVVISTO:
#        la forma della preferenza (liste e dashboard) la giudica il guard
#        del DB, `ui.trgfn_preferenza_guard_forma`, e il BE ne ha ritirato la
#        copia. Una configurazione di forma sbagliata, mandata al service com'e'
#        in produzione, deve tornare all'operatore come `E_UI_CONFIGURAZIONE_FORMA`
#        con status 400, passando da `ErrorTranslator.to_api_error`, lo stesso
#        punto del middleware: non un 500, non un salvataggio.
# Note: ⭐ La giuntura, non la regola. La regola caso per caso la provano i
#       pgTAP di `ui`; qui si prova che, tolta la copia, ogni forma che il BE
#       rifiutava arriva al DB e torna come 400. Fra i casi ci sono i due
#       trovati leggendo (§3.2-bis, «Per BE8»): la chiave a null, che il BE
#       toglieva (deciso da Tid il 2026-11-22: la toglie il FE, non il BE), e
#       la stringa di sole cifre, che il BE convertiva.
#       La lista, la colonna e l'utente si COSTRUISCONO nel test. La dashboard
#       no: dal giro 5 (U31) l'app non scrive il catalogo delle dashboard, e
#       il guard di forma giudica chiavi, voci, null e codici doppi prima di
#       guardare il pool, quindi basta una dashboard accesa qualsiasi; senza,
#       i casi della dashboard si saltano col motivo. Tutto in transazione
#       ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) FormaPreferenzaDbTests.test_lista_forma_buona_si_salva
2) FormaPreferenzaDbTests.test_lista_forma_sbagliata_400
3) FormaPreferenzaDbTests.test_dashboard_forma_sbagliata_400
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import Annulla, apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.services.dashboard_preferenza_service import DashboardPreferenzaService
from apps.ui.services.lista_preferenza_service import ListaPreferenzaService

_CODICE = "E_UI_CONFIGURAZIONE_FORMA"
_LISTA = "ui.test_be8_forma"
_COLONNA = "be8_info"

# Il service chiede l'emittente dell'utente per la risoluzione: qui nessuno
# (admin globale), la forma non ne dipende.
_SENZA_EMITTENTE = patch(
    "apps.core.services.permissions_resolver.PermissionResolver.get_emittente_for_user",
    return_value=None,
)

# Le forme che il BE rifiutava da se' prima del giro 2, piu' i due casi che
# convertiva. Ognuna da sola, sopra una configurazione altrimenti buona.
_LISTA_SBAGLIATE: dict[str, dict[str, Any]] = {
    "chiave non ammessa": {"iniettata": True},
    "ordinamento ritirato": {"ordinamento": [{"col": _COLONNA, "dir": "asc"}]},
    "filtri ritirati": {"filtri": {"attivo": True}},
    "colonne non elenco": {"colonne": {"codice": _COLONNA}},
    "voce non oggetto": {"colonne": ["stringa"]},
    "voce senza codice": {"colonne": [{"ordine": 1}]},
    "voce con chiave extra": {"colonne": [{"codice": _COLONNA, "extra": 1}]},
    "larghezza null": {"colonne": [{"codice": _COLONNA, "larghezza": None}]},
    "larghezza stringa di cifre": {"colonne": [{"codice": _COLONNA, "larghezza": "120"}]},
    "ordine zero": {"colonne": [{"codice": _COLONNA, "ordine": 0}]},
    "visibile non booleano": {"colonne": [{"codice": _COLONNA, "visibile": "si"}]},
    "codice ripetuto": {"colonne": [{"codice": _COLONNA}, {"codice": _COLONNA}]},
    "colonna di un'altra lista": {"colonne": [{"codice": "be8_non_esiste"}]},
    "pagina_dimensione null": {"pagina_dimensione": None},
}

_DASHBOARD_SBAGLIATE: dict[str, dict[str, Any]] = {
    "chiave non ammessa": {"iniettata": True},
    "widget non elenco": {"widget": {"codice": "x"}},
    "voce non oggetto": {"widget": ["stringa"]},
    "voce senza codice": {"widget": [{"ordine": 1}]},
    "voce con chiave extra": {"widget": [{"codice": "x", "deep_link": {"path": "/x"}}]},
    "visibile null": {"widget": [{"codice": "x", "visibile": None}]},
    "codice ripetuto": {"widget": [{"codice": "x"}, {"codice": "x"}]},
    "dimensione_max zero": {"dimensione_max": 0},
    "dimensione_max oltre il tetto": {"dimensione_max": 101},
    "dimensione_max stringa di cifre": {"dimensione_max": "8"},
}


class FormaPreferenzaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # La sonda sul guard del giro 2: un DB indietro fallirebbe
        # sull'attesa invece che sul prerequisito.
        richiedi_db_provvisto("ui.fn_check_forma_configurazione(text,integer,jsonb)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        _SENZA_EMITTENTE.start()
        self.addCleanup(_SENZA_EMITTENTE.stop)
        repo = UiAdminRepository()
        lista_id = repo.create_definizione({
            "codice": _LISTA,
            "descrizione": "BE8 forma della preferenza",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })
        repo.create_colonna({
            "lista_id": lista_id,
            "codice": _COLONNA,
            "etichetta": "Info",
            "tipo_colonna": "informazione",
            "tipo_dato": "string",
            "ordine_default": 1,
            # Senza campo sorgente non si esporta (U25, giro 4).
            "esportabile": False,
            "attivo": True,
        })
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_user (password, is_superuser, username, first_name, "
                "last_name, email, is_staff, is_active, date_joined) "
                "VALUES ('!', false, 'test_be8_forma', '', '', '', false, true, now()) "
                "RETURNING id",
            )
            self.user = SimpleNamespace(id=int(cur.fetchone()[0]))

    def _rifiuto(self, esegui: Any) -> None:
        with self.assertRaises(Annulla):
            with transaction.atomic():
                with self.assertRaises(Exception) as ctx:
                    with transaction.atomic():
                        esegui()
                api_error = ErrorTranslator.to_api_error(ctx.exception)
                self.assertEqual(api_error.code, _CODICE)
                self.assertEqual(ErrorTranslator.get_http_status(api_error), 400)
                raise Annulla

    # Il controllo positivo: senza, i rifiuti qui sotto passerebbero anche se
    # il DB rifiutasse tutto, per un motivo diverso dalla forma.
    def test_lista_forma_buona_si_salva(self) -> None:
        esito = ListaPreferenzaService().upsert(
            self.user, _LISTA,
            {"colonne": [{"codice": _COLONNA, "ordine": 1, "larghezza": 120,
                          "visibile": True, "fissata": False}]},
        )
        self.assertIsNotNone(esito["id"])
        # BE21 (giro 5): il secondo salvataggio e' un UPDATE, e `data_update`
        # la scrive il trigger del DB (`ui.trgfn_preferenza_data_update`):
        # il repository non la nomina piu'.
        ListaPreferenzaService().upsert(self.user, _LISTA, {"colonne": [{"codice": _COLONNA}]})
        with connection.cursor() as cur:
            cur.execute(
                "SELECT data_update FROM ui.lista_preferenza_utente WHERE id = %s",
                [esito["id"]],
            )
            self.assertIsNotNone(cur.fetchone()[0])

    def test_lista_forma_sbagliata_400(self) -> None:
        for caso, payload in _LISTA_SBAGLIATE.items():
            with self.subTest(caso=caso):
                self._rifiuto(
                    lambda payload=payload: ListaPreferenzaService().upsert(
                        self.user, _LISTA, payload,
                    )
                )

    def test_dashboard_forma_sbagliata_400(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT codice FROM ui.dashboard_definizione WHERE attivo ORDER BY id LIMIT 1"
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest(
                "nessuna ui.dashboard_definizione accesa: l'app non la puo' "
                "fabbricare (U31, giro 5)"
            )
        codice = str(riga[0])
        for caso, payload in _DASHBOARD_SBAGLIATE.items():
            with self.subTest(caso=caso):
                self._rifiuto(
                    lambda payload=payload: DashboardPreferenzaService().upsert(
                        self.user, codice, payload,
                    )
                )
