# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaPreferenzaService — il corpo arriva intatto al DB, snapshot
#        preset di base, UPSERT/DELETE preferenza utente. CI senza DB
#        reale (SimpleTestCase + repository mockato).
#
# Indice test (0..N):
#   0. upsert_happy_path
#   1. (ritirato: la lista inesistente la rifiuta il DB, test_lista_da_codice_db)
#   2. upsert_pagina_dimensione_la_decide_il_db
#   3. upsert_una_chiave_sola_arriva_da_sola
#   4. upsert_senza_chiavi_raises
#   5. upsert_la_forma_arriva_intatta_al_db (BE8, giro 2: la forma la giudica il DB)
#   6. upsert_payload_non_dict_raises
#   7. upsert_snapshot_preset_none_quando_nessun_preset
#   8. delete_happy_path
#   9. (ritirato, come l'1)
#  10. delete_idempotente_se_pref_assente
#  11. ignore_preset_update_happy_path (DEF-2)
#  12. (ritirato, come l'1)
#  13. ignore_preset_update_senza_preferenza_raises (DEF-2)
#  14. ignore_preset_update_pref_senza_preset_base_id (DEF-2 — edge)
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_preferenza_service import (
    E_UI_PREFERENZA_NON_TROVATA,
    E_UI_PREFERENZA_VALIDAZIONE,
    ListaPreferenzaService,
)


def _make_user(user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


_VALID_PAYLOAD: dict[str, Any] = {
    "colonne": [
        {
            "codice": "ragione_sociale",
            "ordine": 1,
            "larghezza": 240,
            "visibile": True,
            "fissata": True,
        },
        {"codice": "partita_iva", "ordine": 2, "visibile": True},
    ],
    "pagina_dimensione": 50,
}


# Scopo: La risoluzione con un preset di base, nella forma del resolver DB.
def _risoluzione_con_base(preset_id: int) -> dict[str, Any]:
    return {
        "preset_base": {
            "id": preset_id,
            "ambito": "sistema",
            "contenuto_aggiornato_il": "2026-05-06T00:00:00+00:00",
        },
    }


class ListaPreferenzaUpsertTests(SimpleTestCase):
    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_happy_path(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.resolve_lista_config.return_value = _risoluzione_con_base(5)
        repo.upsert_preferenza.return_value = 99
        svc = ListaPreferenzaService(repository=repo)

        result = svc.upsert(_make_user(), "anagrafiche.clienti", dict(_VALID_PAYLOAD))

        self.assertEqual(result["id"], 99)
        self.assertEqual(result["preset_base_id"], 5)
        repo.upsert_preferenza.assert_called_once()
        kwargs = repo.upsert_preferenza.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 42)
        self.assertEqual(kwargs["lista_id"], 1)
        self.assertEqual(kwargs["preset_base_id"], 5)
        # ⭐ Lo snapshot lo scrive il trigger del DB (BE6): il service non lo passa.
        self.assertNotIn("preset_base_contenuto_aggiornato_il", kwargs)
        # La base viene dalla risoluzione, con l'emittente dell'utente (BE5).
        repo.resolve_lista_config.assert_called_once_with(
            lista_codice="anagrafiche.clienti", auth_user_id=42, emittente_fiscale_id=11,
        )
        # Configurazione propagata cosi' com'e'.
        cfg = kwargs["configurazione"]
        self.assertEqual(cfg["pagina_dimensione"], 50)
        self.assertEqual(len(cfg["colonne"]), 2)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    # ⭐ Dal 2026-09-30 il service NON giudica la misura: quali sono ammesse lo
    #    dice il catalogo `ui.misure_pagina`, e il rifiuto lo da' il guard a DB
    #    (`E_UI_MISURA_PAGINA_NON_AMMESSA`, provato sul DB vero in
    #    `tests/db/test_misure_pagina_db`). Qui si prova che la misura arriva
    #    intatta al repository: un tetto rimasto nel service sarebbe una
    #    seconda regola, diversa dal catalogo.
    def test_upsert_pagina_dimensione_la_decide_il_db(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.resolve_lista_config.return_value = {"preset_base": None}
        repo.upsert_preferenza.return_value = 7
        svc = ListaPreferenzaService(repository=repo)

        svc.upsert(_make_user(), "anagrafiche.clienti", {"pagina_dimensione": 5000})
        cfg = repo.upsert_preferenza.call_args.kwargs["configurazione"]
        self.assertEqual(cfg["pagina_dimensione"], 5000)

    # ⭐ Preferenza per chiave (2026-11-01): ogni chiave e' facoltativa, quella
    #    assente vale «come lo standard». Arriva al repository la sola chiave
    #    mandata, senza le altre riempite.
    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_una_chiave_sola_arriva_da_sola(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.resolve_lista_config.return_value = _risoluzione_con_base(5)
        repo.upsert_preferenza.return_value = 7
        svc = ListaPreferenzaService(repository=repo)

        svc.upsert(_make_user(), "anagrafiche.clienti", {"colonne": _VALID_PAYLOAD["colonne"]})
        cfg = repo.upsert_preferenza.call_args.kwargs["configurazione"]
        self.assertEqual(set(cfg), {"colonne"})

    # ⛔ Una preferenza senza chiavi si toglie col DELETE: il PUT vuoto, o con
    #    le sole chiavi a null, e' un 400 e non scrive niente.
    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_senza_chiavi_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", {})
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)
        repo.upsert_preferenza.assert_not_called()

    # ⛔ La forma la giudica il guard del DB (BE8 di brief-db-revisione-ui,
    #    giro 2): il service non toglie, non converte e non rifiuta niente. Un
    #    corpo sbagliato in ogni modo arriva INTATTO al repository; il rifiuto
    #    (`E_UI_CONFIGURAZIONE_FORMA`, 400) lo prova `tests/db/test_forma_preferenza_db`.
    #    Un controllo rimasto nel service sarebbe una seconda regola.
    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_la_forma_arriva_intatta_al_db(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.resolve_lista_config.return_value = {"preset_base": None}
        repo.upsert_preferenza.return_value = 7
        svc = ListaPreferenzaService(repository=repo)

        payload = {
            "colonne": [{"codice": "x", "larghezza": None, "ordine": "3", "extra": 1}],
            "ordinamento": [{"col": "x", "dir": "asc"}],
            "pagina_dimensione": "venti",
        }
        svc.upsert(_make_user(), "anagrafiche.clienti", payload)
        self.assertEqual(repo.upsert_preferenza.call_args.kwargs["configurazione"], payload)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=11,
    )
    def test_upsert_payload_non_dict_raises(self, _mock_em) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.upsert(_make_user(), "anagrafiche.clienti", ["not", "a", "dict"])  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_VALIDAZIONE)

    @patch(
        "apps.ui.services.lista_preferenza_service.PermissionResolver"
        ".get_emittente_for_user",
        return_value=None,  # admin globale
    )
    def test_upsert_snapshot_preset_none_quando_nessun_preset(
        self, _mock_em
    ) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.resolve_lista_config.return_value = {"preset_base": None}
        repo.upsert_preferenza.return_value = 99
        svc = ListaPreferenzaService(repository=repo)

        result = svc.upsert(_make_user(), "anagrafiche.clienti", dict(_VALID_PAYLOAD))

        self.assertIsNone(result["preset_base_id"])
        kwargs = repo.upsert_preferenza.call_args.kwargs
        self.assertIsNone(kwargs["preset_base_id"])


class ListaPreferenzaDeleteTests(SimpleTestCase):
    def test_delete_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.delete_preferenza.return_value = True
        svc = ListaPreferenzaService(repository=repo)

        result = svc.delete(_make_user(), "anagrafiche.clienti")

        self.assertTrue(result["deleted"])
        repo.delete_preferenza.assert_called_once_with(
            auth_user_id=42, lista_id=1,
        )

    def test_delete_idempotente_se_pref_assente(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.delete_preferenza.return_value = False  # nessuna riga eliminata
        svc = ListaPreferenzaService(repository=repo)

        result = svc.delete(_make_user(), "anagrafiche.clienti")

        # Non solleva — solo `deleted=False`.
        self.assertFalse(result["deleted"])


class ListaPreferenzaIgnorePresetUpdateTests(SimpleTestCase):
    """DEF-2: tombstone 'ignora banner preset aggiornato'."""

    def test_ignore_preset_update_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.riallinea_snapshot_base.return_value = True
        svc = ListaPreferenzaService(repository=repo)

        result = svc.ignore_preset_update(_make_user(), "anagrafiche.clienti")

        self.assertTrue(result["ignored"])
        repo.riallinea_snapshot_base.assert_called_once_with(
            auth_user_id=42, lista_id=1,
        )

    def test_ignore_preset_update_senza_preferenza_raises(self) -> None:
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.riallinea_snapshot_base.return_value = False  # no riga
        svc = ListaPreferenzaService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.ignore_preset_update(_make_user(), "anagrafiche.clienti")
        self.assertEqual(ctx.exception.code, E_UI_PREFERENZA_NON_TROVATA)

    def test_ignore_preset_update_pref_senza_preset_base_id(self) -> None:
        # Edge: preferenza esiste ma `preset_base_id` e' NULL (utente ha
        # salvato senza preset applicabile). L'UPDATE riscrive comunque
        # `preset_base_id` (NULL): il trigger DB porta lo snapshot a NULL e
        # la fn DB ritorna preset_aggiornato=false. Il service non deve
        # sollevare: dal suo punto di vista la riga esiste e l'UPDATE e'
        # atomico.
        repo = MagicMock()
        repo.get_lista_id.return_value = 1
        repo.riallinea_snapshot_base.return_value = True
        svc = ListaPreferenzaService(repository=repo)

        result = svc.ignore_preset_update(_make_user(), "anagrafiche.clienti")

        self.assertTrue(result["ignored"])
