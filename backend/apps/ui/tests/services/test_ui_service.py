# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit UiService (lettura schema `ui`). Mock repository +
#        PermissionResolver. CI senza DB reale (SimpleTestCase).
#
# Indice test (0..N):
#   0. get_lista_config_happy_path
#   1. get_lista_config_admin_globale_passa_emittente_none
#   2. get_lista_config_lista_inesistente_raises
#   3. get_lista_config_database_error_marker_riconosciuto
#   4. get_lista_config_database_error_fallback_generic
#   5. get_catalogo_happy_path_filtra_bloccate
#   6. get_catalogo_lista_inesistente_raises
#   Perimetro emittente (P-2b) — chiave derivata `richiede_scelta_emittente`
#   7. richiede_scelta_emittente_falso_con_un_solo_emittente
#   8. richiede_scelta_emittente_vero_con_scope_multiplo
#   9. richiede_scelta_emittente_falso_se_la_lista_e_certificata
#  10. flag_di_catalogo_assente_vale_come_non_certificata
#  11. perimetro_risolto_una_volta_sola_per_istanza
#   Guardrail multilingua colonne (2026-08-22)
#  12. sql_del_catalogo_seleziona_la_chiave_i18n
#  13. catalogo_reale_porta_la_chiave_valorizzata (e2e, opt-in)
#   Guardia di contesto della schermata (brief ricerca full §12)
#  14. guc_vuota_e_un_errore_tecnico
#  15. guc_di_un_altro_utente_e_un_errore_tecnico
#  16. guc_dello_stesso_utente_legge_ricerca_full
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from unittest import TestCase as UnittestTestCase

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.ui.services.ui_service import (
    E_UI_CHIAMATA_NON_VALIDA,
    E_UI_GENERIC_FAILED,
    E_UI_LISTA_NON_TROVATA,
    UiService,
)


# Scopo: Costruisce un MagicMock user con id stabile.
def _make_user(user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


class UiServiceGetListaConfigTests(SimpleTestCase):
    @patch(
        "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_happy_path(self, _mock_em, _mock_scope) -> None:
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {
            "colonne": [
                {"codice": "ragione_sociale", "ordine": 1, "visibile": True},
            ],
            "ordinamento": [],
            "filtri": {},
            "pagina_dimensione": 25,
            "colonne_nuove": 0,
        }
        svc = UiService(repository=repo)

        config = svc.get_lista_config(_make_user(), "anagrafiche.clienti")

        self.assertEqual(config["pagina_dimensione"], 25)
        repo.resolve_lista_config.assert_called_once_with(
            lista_codice="anagrafiche.clienti",
            auth_user_id=42,
            emittente_fiscale_id=11,
        )
        # ⚠️ La configurazione «nuda» (export, modale) non paga la lettura
        #    della ricerca: `ricerca_full` e' solo della schermata.
        self.assertNotIn("ricerca_full", config)
        repo.ha_ricerca_full.assert_not_called()
        # La schermata: la casella dalla stessa lettura del BB di ricerca.
        repo.utente_di_sessione.return_value = 42
        repo.ha_ricerca_full.return_value = False
        self.assertFalse(
            svc.get_lista_config_per_video(_make_user(), "anagrafiche.clienti")["ricerca_full"]
        )
        repo.ha_ricerca_full.assert_called_once_with("anagrafiche.clienti")

    @patch(
        "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=None,
    )
    def test_get_lista_config_admin_globale_passa_emittente_none(
        self, _mock_em, _mock_scope
    ) -> None:
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {
            "colonne": [], "ordinamento": [], "filtri": {},
            "pagina_dimensione": 25, "colonne_nuove": 0,
        }
        svc = UiService(repository=repo)

        svc.get_lista_config(_make_user(), "anagrafiche.clienti")

        # Admin globale -> emittente_fiscale_id=None propagato alla fn DB.
        repo.resolve_lista_config.assert_called_once_with(
            lista_codice="anagrafiche.clienti",
            auth_user_id=42,
            emittente_fiscale_id=None,
        )

    @patch(
        "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_lista_inesistente_raises(self, _mock_em, _mock_scope) -> None:
        # Caso difensivo: la fn ritorna dict vuoto invece di raise.
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {}
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)

    @patch(
        "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_db_error_marker_riconosciuto(
        self, _mock_em, _mock_scope
    ) -> None:
        repo = MagicMock()
        # MESSAGE che contiene il marker E_UI_LISTA_NON_TROVATA.
        repo.resolve_lista_config.side_effect = DatabaseError(
            "ERROR: E_UI_LISTA_NON_TROVATA: codice lista 'foo'"
        )
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config(_make_user(), "foo")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)

    @patch(
        "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_db_error_fallback_generic(self, _mock_em, _mock_scope) -> None:
        repo = MagicMock()
        repo.resolve_lista_config.side_effect = DatabaseError(
            "ERROR: connection lost"
        )
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config(_make_user(), "anagrafiche.clienti")
        self.assertEqual(ctx.exception.code, E_UI_GENERIC_FAILED)


class UiServiceGetCatalogoTests(SimpleTestCase):
    @patch(
        "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_catalogo_happy_path_filtra_bloccate(self, _mock_em, _mock_scope) -> None:
        repo = MagicMock()
        # 'iban' simulata BLOCCATA: presente nel catalogo grezzo ma assente
        # dal risultato di resolve_lista_config (la fn DB la rimuove).
        repo.list_colonne_by_codice.return_value = [
            {"codice": "ragione_sociale", "tipo_colonna": "identificatore"},
            {"codice": "partita_iva", "tipo_colonna": "informazione"},
            {"codice": "iban", "tipo_colonna": "informazione"},
        ]
        repo.resolve_lista_config.return_value = {
            "colonne": [
                {"codice": "ragione_sociale"},
                {"codice": "partita_iva"},
                # iban filtrata via permessi (non presente)
            ],
            "ordinamento": [], "filtri": {}, "pagina_dimensione": 25,
            "colonne_nuove": 0,
        }
        svc = UiService(repository=repo)

        result = svc.get_catalogo(_make_user(), "anagrafiche.clienti")

        codici = {c["codice"] for c in result["colonne"]}
        self.assertEqual(codici, {"ragione_sociale", "partita_iva"})
        self.assertNotIn("iban", codici)

    @patch(
        "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_catalogo_lista_inesistente_raises(self, _mock_em, _mock_scope) -> None:
        repo = MagicMock()
        # La fn DB ritorna dict vuoto per lista inesistente -> get_lista_config
        # solleva E_UI_LISTA_NON_TROVATA. Il catalogo non viene mai chiesto.
        repo.resolve_lista_config.return_value = {}
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_catalogo(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)
        repo.list_colonne_by_codice.assert_not_called()


# ============================================================
# Perimetro emittente (P-2b) — la chiave derivata dell'envelope
# ============================================================

class UiServicePerimetroEmittenteTests(SimpleTestCase):
    """`richiede_scelta_emittente` e' una CONCLUSIONE, non un dato.

    ⚠️ La deriva il backend e non il frontend: e' l'unico che conosce la
    cardinalita' dello scope. Farla ricalcolare a video creerebbe una seconda
    sede della stessa verita' — la duplicazione che poi diverge.
    """

    _CONFIG_BASE = {
        "colonne": [], "ordinamento": [], "filtri": {},
        "pagina_dimensione": 25, "colonne_nuove": 0,
    }

    # Scopo: risolve la config con scope e flag di catalogo dati.
    def _config(self, *, scope, multi_emittente):
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {
            **self._CONFIG_BASE, "multi_emittente": multi_emittente,
        }
        with patch(
            "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
            return_value=11,
        ), patch(
            "apps.core.services.perimetro_emittente.PermissionResolver"
            ".get_emittenti_pk_ids",
            return_value=scope,
        ):
            return UiService(repository=repo).get_lista_config(
                _make_user(), "vendite.dash_competenza_gruppi",
            )

    def test_richiede_scelta_emittente_falso_con_un_solo_emittente(self) -> None:
        """Il caso del 99% degli utenti: nessun cancello, mai."""
        config = self._config(scope=[72], multi_emittente=False)
        self.assertFalse(config["richiede_scelta_emittente"])

    def test_richiede_scelta_emittente_vero_con_scope_multiplo(self) -> None:
        """Universo + lista non certificata = l'unico caso in cui si sbarra."""
        config = self._config(scope=None, multi_emittente=False)
        self.assertTrue(config["richiede_scelta_emittente"])

    def test_richiede_scelta_emittente_falso_se_la_lista_e_certificata(self) -> None:
        """Una lista che dichiara l'emittente nella riga si apre a tutti."""
        config = self._config(scope=None, multi_emittente=True)
        self.assertFalse(config["richiede_scelta_emittente"])

    def test_flag_di_catalogo_assente_vale_come_non_certificata(self) -> None:
        """Envelope senza `multi_emittente` (DB non ancora allineato): fail-closed.

        ⚠️ La chiave e' additiva e un envelope vecchio non ce l'ha. Trattare
        l'assenza come «certificata» aprirebbe esattamente la finestra che il
        flag esiste per chiudere: una lista che mescola emittenti senza dirlo.
        """
        repo = MagicMock()
        repo.resolve_lista_config.return_value = dict(self._CONFIG_BASE)
        with patch(
            "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
            return_value=11,
        ), patch(
            "apps.core.services.perimetro_emittente.PermissionResolver"
            ".get_emittenti_pk_ids",
            return_value=None,
        ):
            config = UiService(repository=repo).get_lista_config(
                _make_user(), "vendite.x",
            )
        self.assertTrue(config["richiede_scelta_emittente"])

    def test_perimetro_risolto_una_volta_sola_per_istanza(self) -> None:
        """`get_catalogo` chiama `get_lista_config`: la domanda si fa UNA volta.

        Senza la cache per-istanza, una sola apertura della modale colonne
        interrogherebbe il database due volte per sapere la stessa cosa.
        """
        repo = MagicMock()
        # ⚠️ `multi_emittente: False` non e' un dettaglio della fixture: con la
        # lista CERTIFICATA il cortocircuito impedirebbe del tutto la
        # risoluzione dello scope, e il test misurerebbe zero chiamate senza
        # aver provato niente sulla cache.
        repo.resolve_lista_config.return_value = {
            **self._CONFIG_BASE, "multi_emittente": False,
        }
        repo.list_colonne_by_codice.return_value = []
        with patch(
            "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
            return_value=11,
        ), patch(
            "apps.core.services.perimetro_emittente.PermissionResolver"
            ".get_emittenti_pk_ids",
            return_value=[72],
        ) as mock_scope:
            UiService(repository=repo).get_catalogo(_make_user(), "vendite.x")
        self.assertEqual(mock_scope.call_count, 1)


# ══════════════════════════════════════════════════════════════════
#  Guardrail multilingua delle colonne (2026-08-22)
# ══════════════════════════════════════════════════════════════════
class CatalogoColonneI18nGuardrailTests(UnittestTestCase):
    """⭐ Il catalogo colonne deve portare `etichetta_i18n_key`.

    ⚠️ NASCE DA UN DIFETTO REALE, e da uno che i mock non potevano vedere.
    `list_colonne_by_codice` selezionava 19 colonne e NON quella: il frontend
    cercava li' la chiave i18n, non la trovava, e ripiegava sull'etichetta
    italiana del seed — per OGNI colonna di OGNI lista, in qualunque lingua.
    I test di servizio qui sopra passavano tutti: girano su un repository
    MagicMock, che risponde quello che gli si dice.

    Per questo il presidio e' su DUE piani e non su uno:
      1. il TESTO dell'SQL — deterministico, gira sempre, e cade il giorno in
         cui qualcuno riscrive la SELECT dimenticando la colonna;
      2. il DATO vero (opt-in `ZEROERP_TEST_DB_E2E=1`) — perche' una colonna
         puo' esistere nella SELECT e arrivare comunque vuota se il seed non
         la valorizza.
    """

    # Scopo: la SELECT del catalogo cita `etichetta_i18n_key`.
    def test_sql_del_catalogo_seleziona_la_chiave_i18n(self) -> None:
        import inspect

        from apps.ui.db.ui_repository import UiRepository

        sorgente = inspect.getsource(UiRepository.list_colonne_by_codice)
        self.assertIn(
            "etichetta_i18n_key",
            sorgente,
            "Il catalogo colonne non espone `etichetta_i18n_key`: le "
            "intestazioni tornerebbero all'etichetta italiana del seed in "
            "qualunque lingua, e in silenzio (il guard `te` del frontend "
            "ripiega senza dire niente).",
        )

    # Scopo: sul DB vero la chiave arriva VALORIZZATA (non solo selezionata).
    def test_catalogo_reale_porta_la_chiave_valorizzata(self) -> None:
        richiedi_db_provvisto()
        from apps.ui.db.ui_repository import UiRepository

        colonne = UiRepository().list_colonne_by_codice("vendite.lotti")
        self.assertTrue(colonne, "catalogo vuoto: lista di prova non seedata?")
        self.assertIn("etichetta_i18n_key", colonne[0])
        senza_chiave = [c["codice"] for c in colonne if not c.get("etichetta_i18n_key")]
        self.assertEqual(
            senza_chiave, [],
            f"colonne senza chiave i18n su vendite.lotti: {senza_chiave}",
        )


# ⭐ La configurazione risponde per `user.id`, la ricerca per l'utente della
#    GUC: se i due non coincidono la casella e la ricerca direbbero cose
#    diverse. La guardia fa rumore invece di scegliere una delle due fonti.
@patch(
    "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids",
    return_value=[11],
)
@patch(
    "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
    return_value=11,
)
@patch("apps.core.services.error_manager.ErrorManager.log_error_only")
class UiServiceGuardiaContestoTests(SimpleTestCase):
    # Scopo: un repository con una configurazione valida e la GUC data.
    def _svc(self, utente_guc: int | None) -> tuple[UiService, MagicMock]:
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {
            "colonne": [], "ordinamento": [], "filtri": {},
            "pagina_dimensione": 25, "colonne_nuove": 0,
        }
        repo.utente_di_sessione.return_value = utente_guc
        repo.ha_ricerca_full.return_value = True
        return UiService(repository=repo), repo

    def test_guc_vuota_e_un_errore_tecnico(self, log, *_mocks) -> None:
        svc, repo = self._svc(None)
        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config_per_video(_make_user(42), "anagrafiche.clienti")
        self.assertEqual(ctx.exception.code, E_UI_CHIAMATA_NON_VALIDA)
        self.assertEqual(
            ctx.exception.context,
            {"lista_codice": "anagrafiche.clienti", "auth_user_id": 42, "utente_di_sessione": None},
        )
        # La ricerca non si legge per nessuno dei due, e il guasto va al diario.
        repo.ha_ricerca_full.assert_not_called()
        log.assert_called_once()

    def test_guc_di_un_altro_utente_e_un_errore_tecnico(self, log, *_mocks) -> None:
        svc, repo = self._svc(7)
        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config_per_video(_make_user(42), "anagrafiche.clienti")
        self.assertEqual(ctx.exception.code, E_UI_CHIAMATA_NON_VALIDA)
        self.assertEqual(ctx.exception.context["utente_di_sessione"], 7)
        repo.ha_ricerca_full.assert_not_called()

    def test_guc_dello_stesso_utente_legge_ricerca_full(self, log, *_mocks) -> None:
        svc, repo = self._svc(42)
        config = svc.get_lista_config_per_video(_make_user(42), "anagrafiche.clienti")
        self.assertTrue(config["ricerca_full"])
        repo.ha_ricerca_full.assert_called_once_with("anagrafiche.clienti")
        log.assert_not_called()
