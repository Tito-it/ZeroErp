# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaDefinizioneAdminService.
#        Fase 1 (read-only): Select header + catalogo colonne grezzo.
#        Fase 2 — DEF-5b (CRUD SUPER_ADMIN): create/update/delete con
#        mapping IntegrityError per UNIQUE codice e FK RESTRICT (in uso).
#        CI senza DB reale (SimpleTestCase + repository mockato).
#
# Indice test (0..N):
#   Fase 1
#     0. list_definizioni_delegata_a_repo
#     1. list_colonne_lista_inesistente_raises
#     2. list_colonne_lista_happy_path
#   Fase 2 read
#     3. list_definizioni_admin_delegata_a_repo
#     3-bis. count_non_e_derivato_dalle_righe
#     4. get_definizione_inesistente_raises
#     5. get_definizione_happy_path_include_disattive
#   Fase 2 create
#     6. create_definizione_happy_path
#     7. create_definizione_chiavi_extra_raises
#     8. create_definizione_codice_obbligatorio
#     9. create_definizione_unique_codice_violato
#    10. create_definizione_vista_sql_e_note_strip_to_null
#    11. create_definizione_attivo_default_true
#   Fase 2 update
#    12. update_definizione_inesistente_raises
#    13. update_definizione_payload_vuoto_raises
#    14. update_definizione_happy_path
#    15. update_definizione_attivo_null_raises
#   Fase 2 delete
#    16. delete_definizione_inesistente_raises
#    17. delete_definizione_in_uso_raises_409
#    18. delete_definizione_happy_path
#   Perimetro emittente — `multi_emittente` fuori dalla scrittura (BE-3)
#    19. multi_emittente_fuori_dalle_whitelist
#    20. create_definizione_con_multi_emittente_rifiutata
#    21. update_definizione_con_multi_emittente_rifiutata
#    22. builder_create_non_produce_multi_emittente
#    23. builder_update_non_produce_multi_emittente
#    24. repository_insert_non_nomina_multi_emittente
#    25. repository_update_non_nomina_multi_emittente
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.services.lista_definizione_admin_service import (
    CREATE_KEYS,
    UPDATE_KEYS,
    E_DEFINIZIONE_IN_USE,
    E_DEFINIZIONE_NOT_FOUND,
    E_DEFINIZIONE_VALIDATION,
    E_LISTA_NOT_FOUND,
    ListaDefinizioneAdminService,
)


def _row_definizione_full(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": 7,
        "codice": "anagrafiche.clienti",
        "descrizione": "Clienti",
        "schema_dati": "anagrafiche",
        "vista_sql": "vw_clienti_lista",
        "note": None,
        "attivo": True,
        "data_insert": None,
        "user_insert": "tester",
        "data_update": None,
        "user_update": None,
    }
    base.update(overrides)
    return base


# ============================================================
# Fase 1 - Read (Select header + catalogo)
# ============================================================

class ListaDefinizioneFase1ReadTests(SimpleTestCase):
    def test_list_definizioni_delegata_a_repo(self) -> None:
        repo = MagicMock()
        repo.list_definizioni.return_value = [
            {"id": 1, "codice": "anagrafiche.clienti", "descrizione": "Clienti"},
        ]
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.list_definizioni()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["codice"], "anagrafiche.clienti")
        repo.list_definizioni.assert_called_once_with()

    def test_list_colonne_lista_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.list_colonne_lista(999)
        self.assertEqual(ctx.exception.code, E_LISTA_NOT_FOUND)
        repo.list_colonne_by_lista.assert_not_called()

    def test_list_colonne_lista_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_definizione.return_value = {"id": 1, "attivo": True}
        repo.list_colonne_by_lista.return_value = [
            {"id": 10, "codice": "ragione_sociale", "etichetta": "Ragione sociale"},
        ]
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.list_colonne_lista(1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["codice"], "ragione_sociale")
        repo.list_colonne_by_lista.assert_called_once_with(1)


# ============================================================
# Fase 2 - Read admin
# ============================================================

class ListaDefinizioneFase2ReadTests(SimpleTestCase):
    def test_list_definizioni_admin_delegata_a_repo(self) -> None:
        repo = MagicMock()
        repo.list_definizioni_admin.return_value = [
            _row_definizione_full(),
            _row_definizione_full(id=8, codice="vendite.fatture", attivo=False),
        ]
        repo.count_definizioni_admin.return_value = 2
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.list_definizioni_admin()
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertFalse(result["results"][1]["attivo"])
        repo.list_definizioni_admin.assert_called_once_with()

    # Scopo: il `count` non e' `len(results)`. E' l'INVARIANTE che rende utile
    #        il guard anti-troncamento del frontend: se il conteggio si
    #        derivasse dalle righe direbbe sempre di si', e non presidierebbe
    #        niente. Qui il repo dichiara 57 e consegna 2 righe (il caso
    #        «qualcuno ha messo un LIMIT»): il service deve RIPORTARE la
    #        divergenza, non appianarla.
    def test_count_non_e_derivato_dalle_righe(self) -> None:
        repo = MagicMock()
        repo.list_definizioni_admin.return_value = [_row_definizione_full()]
        repo.count_definizioni_admin.return_value = 57
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.list_definizioni_admin()
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["count"], 57)
        repo.count_definizioni_admin.assert_called_once_with()

    def test_get_definizione_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.get_definizione(999)
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)

    def test_get_definizione_happy_path_include_disattive(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full(
            attivo=False
        )
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.get_definizione(7)
        self.assertEqual(result["id"], 7)
        self.assertFalse(result["attivo"])


# ============================================================
# Fase 2 - Create
# ============================================================

class ListaDefinizioneFase2CreateTests(SimpleTestCase):
    def test_create_definizione_happy_path(self) -> None:
        repo = MagicMock()
        repo.create_definizione.return_value = 42
        repo.get_definizione_admin.return_value = _row_definizione_full(id=42)
        svc = ListaDefinizioneAdminService(repo=repo)

        result = svc.create_definizione({
            "codice": "anagrafiche.fornitori",
            "descrizione": "Fornitori",
            "schema_dati": "anagrafiche",
            "vista_sql": "vw_fornitori_lista",
            "attivo": True,
        })

        self.assertEqual(result["id"], 42)
        repo.create_definizione.assert_called_once()
        data = repo.create_definizione.call_args.args[0]
        self.assertEqual(data["codice"], "anagrafiche.fornitori")
        self.assertEqual(data["vista_sql"], "vw_fornitori_lista")
        self.assertTrue(data["attivo"])

    def test_create_definizione_chiavi_extra_raises(self) -> None:
        repo = MagicMock()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_definizione({
                "codice": "x.y",
                "descrizione": "X",
                "schema_dati": "x",
                "campo_inventato": True,
            })
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.create_definizione.assert_not_called()

    def test_create_definizione_codice_obbligatorio(self) -> None:
        repo = MagicMock()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_definizione({
                "descrizione": "X",
                "schema_dati": "x",
            })
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.create_definizione.assert_not_called()

    def test_create_definizione_unique_codice_violato(self) -> None:
        repo = MagicMock()
        # IntegrityError con marker del vincolo UNIQUE sul codice.
        repo.create_definizione.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_ui_lista_definizione_codice"'
        )
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_definizione({
                "codice": "duplicate.code",
                "descrizione": "Dup",
                "schema_dati": "x",
            })
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)

    def test_create_definizione_vista_sql_e_note_strip_to_null(self) -> None:
        repo = MagicMock()
        repo.create_definizione.return_value = 1
        repo.get_definizione_admin.return_value = _row_definizione_full(id=1)
        svc = ListaDefinizioneAdminService(repo=repo)
        # Stringa vuota -> None (pattern null_vs_empty).
        svc.create_definizione({
            "codice": "x.y",
            "descrizione": "X",
            "schema_dati": "x",
            "vista_sql": "   ",
            "note": "",
        })
        data = repo.create_definizione.call_args.args[0]
        self.assertIsNone(data["vista_sql"])
        self.assertIsNone(data["note"])

    def test_create_definizione_attivo_default_true(self) -> None:
        repo = MagicMock()
        repo.create_definizione.return_value = 1
        repo.get_definizione_admin.return_value = _row_definizione_full(id=1)
        svc = ListaDefinizioneAdminService(repo=repo)
        # `attivo` omesso -> True applicativo (workflow standard, non
        # draft).
        svc.create_definizione({
            "codice": "x.y",
            "descrizione": "X",
            "schema_dati": "x",
        })
        data = repo.create_definizione.call_args.args[0]
        self.assertTrue(data["attivo"])


# ============================================================
# Fase 2 - Update
# ============================================================

class ListaDefinizioneFase2UpdateTests(SimpleTestCase):
    def test_update_definizione_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_definizione(999, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)
        repo.update_definizione.assert_not_called()

    def test_update_definizione_payload_vuoto_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_definizione(7, {})
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.update_definizione.assert_not_called()

    def test_update_definizione_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        repo.update_definizione.return_value = True
        svc = ListaDefinizioneAdminService(repo=repo)
        svc.update_definizione(7, {
            "descrizione": "Clienti rinominati",
            "attivo": False,
        })
        repo.update_definizione.assert_called_once()
        data = repo.update_definizione.call_args.args[1]
        self.assertEqual(data["descrizione"], "Clienti rinominati")
        self.assertFalse(data["attivo"])

    def test_update_definizione_attivo_null_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_definizione(7, {"attivo": None})
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)


# ============================================================
# Fase 2 - Delete
# ============================================================

class ListaDefinizioneFase2DeleteTests(SimpleTestCase):
    def test_delete_definizione_inesistente_raises(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = None
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_definizione(999)
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_NOT_FOUND)
        repo.delete_definizione.assert_not_called()

    def test_delete_definizione_in_uso_raises_409(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        # FK RESTRICT su lista_preferenza_utente.
        repo.delete_definizione.side_effect = IntegrityError(
            'update or delete on table "lista_definizione" violates '
            'foreign key constraint "fk_lista_preferenza_utente_lista_definizione"'
        )
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_definizione(7)
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_IN_USE)

    def test_delete_definizione_happy_path(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        repo.delete_definizione.return_value = True
        svc = ListaDefinizioneAdminService(repo=repo)
        result = svc.delete_definizione(7)
        self.assertTrue(result["deleted"])
        self.assertEqual(result["id"], 7)


# ============================================================
# Perimetro emittente — `multi_emittente` fuori dalla scrittura
# ============================================================

class ListaDefinizioneMultiEmittenteFuoriScritturaTests(SimpleTestCase):
    """`ui.lista_definizione.multi_emittente` non si scrive dall'applicazione.

    ⚠️ Perche' questo presidio esiste, ed e' piu' largo di quanto sembri.
    Il flag dichiara una CAPACITA' DEL SOFTWARE — «questa lista sa dire da
    quale emittente arriva ogni riga» — e si accende SOLO dal seed, insieme
    al lavoro che la rende vera. Un interruttore in interfaccia lo
    trasformerebbe da registro di debito che cala in elenco di eccezioni che
    cresce (decisione Tid 2026-08-17, brief perimetro-emittente §7/3).

    ⚠️ E il perimetro NON e' la sola whitelist. In questo file e nel
    repository ci sono QUATTRO punti che elencano campi scrivibili — le due
    `frozenset`, i due `_build_*_data`, l'INSERT e il tuple dell'UPDATE — e
    presidiarne uno solo lascerebbe scoperti gli altri tre. E' la stessa
    regola per cui una funzione con gemelle si corregge in famiglia: chi
    aggiunge il campo lo aggiunge dove serve a lui, non dove sta il test.

    ⚠️ Il presidio FORTE resta il trigger DB
    (`E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE`): questo qui e' lo strato che
    avverte in CI **il giorno del refactor**, quando qualcuno riallinea le
    whitelist in buona fede e il rosso arriva prima dell'esercizio.
    """

    _MOTIVO = (
        "`multi_emittente` si accende SOLO dal seed lista_definizione.csv: "
        "e' una capacita' del software, non una preferenza. Vedi il commento "
        "accanto a CREATE_KEYS e il trigger DB "
        "ui.trgfn_lista_definizione_guard_multi_emittente."
    )

    # 19) Le due whitelist del payload.
    def test_multi_emittente_fuori_dalle_whitelist(self) -> None:
        self.assertNotIn("multi_emittente", CREATE_KEYS, self._MOTIVO)
        self.assertNotIn("multi_emittente", UPDATE_KEYS, self._MOTIVO)

    # 20) Il COMPORTAMENTO, non solo la struttura: un payload che lo contiene
    #     viene rifiutato, e il repository non viene nemmeno chiamato.
    def test_create_definizione_con_multi_emittente_rifiutata(self) -> None:
        repo = MagicMock()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.create_definizione(
                {
                    "codice": "vendite.lotti",
                    "descrizione": "Lotti",
                    "schema_dati": "vendite",
                    "multi_emittente": True,
                },
            )
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.create_definizione.assert_not_called()

    # 21) Idem in update.
    def test_update_definizione_con_multi_emittente_rifiutata(self) -> None:
        repo = MagicMock()
        repo.get_definizione_admin.return_value = _row_definizione_full()
        svc = ListaDefinizioneAdminService(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            svc.update_definizione(7, {"multi_emittente": True})
        self.assertEqual(ctx.exception.code, E_DEFINIZIONE_VALIDATION)
        repo.update_definizione.assert_not_called()

    # 22-23) I due builder: anche chiamati DIRETTAMENTE con la chiave dentro
    #     (cioe' saltando la whitelist, che e' come ci si arriva per sbaglio in
    #     un refactor), non devono produrla nel `data` che va al repository.
    def test_builder_create_non_produce_multi_emittente(self) -> None:
        svc = ListaDefinizioneAdminService(repo=MagicMock())
        data = svc._build_create_data({
            "codice": "vendite.lotti",
            "descrizione": "Lotti",
            "schema_dati": "vendite",
            "multi_emittente": True,
        })
        self.assertNotIn("multi_emittente", data, self._MOTIVO)

    def test_builder_update_non_produce_multi_emittente(self) -> None:
        svc = ListaDefinizioneAdminService(repo=MagicMock())
        data = svc._build_update_data({"multi_emittente": True})
        self.assertNotIn("multi_emittente", data, self._MOTIVO)

    # 24-25) L'ultimo miglio: l'SQL. Anche se un `data` contaminato arrivasse
    #     fin qui, le due query non devono nominare la colonna — altrimenti
    #     l'applicazione chiederebbe al database una cosa che il database le
    #     vieta, e il rifiuto arriverebbe come errore invece che come niente.
    def test_repository_insert_non_nomina_multi_emittente(self) -> None:
        sql = self._sql_di(
            lambda repo: repo.create_definizione(
                {
                    "codice": "vendite.lotti",
                    "descrizione": "Lotti",
                    "schema_dati": "vendite",
                    "multi_emittente": True,
                },
            ),
            fetchone=[1],
        )
        self.assertNotIn("multi_emittente", sql, self._MOTIVO)

    # ⛔ Dal 2026-09-26 la whitelist del BB `execute_dynamic_update` e'
    #    RIGIDA: `multi_emittente` non e' piu' «non nominato», e' RIFIUTATO
    #    (RuntimeError) e nessuna query parte. Presidio piu' forte di prima.
    def test_repository_update_non_nomina_multi_emittente(self) -> None:
        with patch("apps.core.db.sql_write_helpers.connection") as mock_conn:
            with self.assertRaises(RuntimeError) as ctx:
                UiAdminRepository().update_definizione(
                    7, {"descrizione": "Lotti", "multi_emittente": True},
                )
            mock_conn.cursor.assert_not_called()
        self.assertIn("multi_emittente", str(ctx.exception), self._MOTIVO)

    # Scopo: esegue una scrittura del repository con la connessione mockata e
    #        restituisce l'SQL che ha provato a eseguire.
    # ⚠️ L'SQL si legge da `call_args` accettando ENTRAMBE le forme di chiamata
    #        (posizionale o `sql=`): un test che legge solo `args[0]` diventa un
    #        IndexError incomprensibile il giorno in cui il repository passa il
    #        parametro per nome — e un IndexError non dice a nessuno che cosa
    #        stava presidiando.
    # ⚠️ Si patcha la connessione di ENTRAMBI i moduli: l'INSERT e' nel
    #        repository, l'UPDATE passa dal BB `execute_dynamic_update`
    #        (`apps.core.db.sql_write_helpers`). Patchare solo il repository
    #        farebbe arrivare l'UPDATE al DB vero (o a nessuno).
    def _sql_di(self, azione, *, fetchone=None) -> str:
        with patch("apps.ui.db.ui_admin_repository.connection") as mock_conn, \
             patch("apps.core.db.sql_write_helpers.connection", mock_conn):
            cursor = MagicMock()
            cursor.fetchone.return_value = fetchone
            cursor.rowcount = 1
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            azione(UiAdminRepository())
            self.assertTrue(
                cursor.execute.called,
                "il repository non ha eseguito nessuna query: il test non "
                "starebbe verificando niente.",
            )
            args, kwargs = cursor.execute.call_args
            return args[0] if args else kwargs["sql"]
