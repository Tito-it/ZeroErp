# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del CRUD generico delle tabelle config (2026-09-21):
#        la lista e' UNA (`config.tabelle_gestibili`, dal 2026-09-25 a DB), la
#        scrittura passa dal verbo `config.fn_pannello_scrivi`, e un IntegrityError arriva
#        tradotto col vincolo e col campo — mappe lette dal catalogo della
#        tabella, non scritte a mano. Fino a quel giorno ogni IntegrityError
#        era «Record gia' esistente». Repository mockati: CI-safe.
# ------------------------------------------------------------
#
# Indice test:
#  1. rel fuori lista → E_CORE_VALIDATION (e `magazzino.lotti` NON e' piu' ammessa)
#  1b. rel nel lookup ma non nel pannello (le quattro con RLS, D-P2) → E_CORE_VALIDATION
#  1c. create e update passano dal verbo: rel, id (None per la nuova) e payload INTERO
#  2. _mappe_vincoli: unique a una colonna → duplicato col campo; a due colonne → senza campo
#  3. _mappe_vincoli: fk e check → E_CORE_VALIDATION, col campo se a una colonna
#  4. create: la violazione UNIQUE arriva come E_ANAG_DUPLICATO con `field` nel contesto
#  5. create: la violazione NOT NULL (nessun vincolo con nome) arriva col campo che PG dichiara
#  6. update: il P0001 di un trigger (lock colonna) arriva col SUO codice, non «duplicato»

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.db import DatabaseError, IntegrityError
from django.test import SimpleTestCase

from apps.core.services import config_crud_service as svc_mod
from apps.core.services.config_crud_service import (
    E_CONFIG_DUPLICATO,
    E_CONFIG_VALIDATION,
    ConfigCrudService,
    _mappe_vincoli,
)
from apps.core.services.service_errors import ServiceError

_VOCE = "apps.core.services.config_crud_service.TabelleGestibiliRepository.voce"


# Scopo: la riga di `config.tabelle_gestibili` di una rel, come la legge il repository.
def _voce(rel: str, *, pannello: bool = True) -> dict:
    schema, table = rel.split(".", 1)
    return {"rel": rel, "schema": schema, "table": table, "app_label": schema,
            "model_name": table, "lookup": True, "pannello": pannello}

_VINCOLI = [
    {"name": "uq_x_codice", "type": "unique", "columns": ["codice"]},
    {"name": "uq_x_coppia", "type": "unique", "columns": ["a", "b"]},
    {"name": "fk_x_tipo", "type": "fk", "columns": ["tipo_id"]},
    {"name": "chk_x_segno", "type": "check", "columns": ["segno"]},
]


# Scopo: un'eccezione DB col testo e la diagnostica psycopg che il BB legge.
def _db_exc(cls, testo: str, *, column_name: str | None = None, constraint_name: str | None = None,
            sqlstate: str = "23505"):
    causa = Exception(testo)
    causa.sqlstate = sqlstate  # type: ignore[attr-defined]
    causa.diag = SimpleNamespace(  # type: ignore[attr-defined]
        column_name=column_name, constraint_name=constraint_name, sqlstate=sqlstate,
        message_primary=testo, message_detail=None, message_hint=None, datatype_name=None,
    )
    exc = cls(testo)
    exc.__cause__ = causa
    return exc


class ParseRelTests(SimpleTestCase):
    # 1.
    @patch(_VOCE, return_value=None, autospec=True)
    def test_rel_fuori_whitelist_rifiutata(self, _voce_mock) -> None:
        with self.assertRaises(ServiceError) as cm:
            ConfigCrudService().get_metadata("magazzino.lotti")
        self.assertEqual(cm.exception.code, E_CONFIG_VALIDATION)

    # 1b. Nelle tendine si', nel pannello no: il verbo non sa rimettere la RLS.
    @patch(_VOCE, return_value=_voce("pagamenti.enti_incasso", pannello=False), autospec=True)
    def test_rel_del_solo_lookup_rifiutata(self, _voce_mock) -> None:
        with self.assertRaises(ServiceError) as cm:
            ConfigCrudService().get_metadata("pagamenti.enti_incasso")
        self.assertEqual(cm.exception.code, E_CONFIG_VALIDATION)


class VerboTests(SimpleTestCase):
    def setUp(self) -> None:
        self.svc = ConfigCrudService()
        for p in (
            patch(_VOCE, return_value=_voce("magazzino.causali"), autospec=True),
            patch.object(self.svc._meta, "get_table_constraints", return_value=[]),
        ):
            p.start()
            self.addCleanup(p.stop)

    # 1c. Il payload arriva INTERO al verbo: niente filtro sul posto, i campi
    #     che non si scrivono li rifiuta il DB (D-P3).
    def test_create_e_update_passano_dal_verbo(self) -> None:
        with patch.object(self.svc._repo, "scrivi_record", return_value={"id": 7}) as verbo:
            self.assertEqual(self.svc.create_record("magazzino.causali", {"codice": "X", "ignoto": 1}), {"id": 7})
            verbo.assert_called_once_with("magazzino.causali", None, {"codice": "X", "ignoto": 1})
            verbo.reset_mock()
            self.assertEqual(self.svc.update_record("magazzino.causali", 13, {"descrizione": "Y"}), {"updated": True})
            verbo.assert_called_once_with("magazzino.causali", 13, {"descrizione": "Y"})


class MappeVincoliTests(SimpleTestCase):
    # 2.
    def test_unique_col_campo_solo_se_una_colonna(self) -> None:
        m = _mappe_vincoli(_VINCOLI)
        self.assertEqual(m["unique"]["uq_x_codice"][0], E_CONFIG_DUPLICATO)
        self.assertEqual(m["unique"]["uq_x_codice"][2], "codice")
        self.assertEqual(len(m["unique"]["uq_x_coppia"]), 2, "un campo inventato accende l'input sbagliato")

    # 3.
    def test_fk_e_check_sono_dato_errato_col_campo(self) -> None:
        m = _mappe_vincoli(_VINCOLI)
        self.assertEqual(m["fk"]["fk_x_tipo"][0], E_CONFIG_VALIDATION)
        self.assertEqual(m["fk"]["fk_x_tipo"][2], "tipo_id")
        self.assertEqual(m["check"]["chk_x_segno"][0], E_CONFIG_VALIDATION)
        self.assertIn("chk_x_segno", m["check"]["chk_x_segno"][1])
        self.assertEqual(m["check"]["chk_x_segno"][2], "segno")


class ErroriTradottiTests(SimpleTestCase):
    def setUp(self) -> None:
        self.svc = ConfigCrudService()
        for p in (
            patch.object(self.svc._meta, "get_table_constraints", return_value=_VINCOLI),
            patch(_VOCE, return_value=_voce("magazzino.causali"), autospec=True),
        ):
            p.start()
            self.addCleanup(p.stop)

    # 4.
    def test_unique_arriva_come_duplicato_col_campo(self) -> None:
        exc = _db_exc(IntegrityError, 'duplicate key value violates unique constraint "uq_x_codice"')
        with patch.object(self.svc._repo, "scrivi_record", side_effect=exc):
            with self.assertRaises(ServiceError) as cm:
                self.svc.create_record("magazzino.causali", {"codice": "X"})
        self.assertEqual(cm.exception.code, E_CONFIG_DUPLICATO)
        self.assertEqual(cm.exception.context.get("field"), "codice")

    # 5.
    def test_not_null_arriva_col_campo_che_postgres_dichiara(self) -> None:
        exc = _db_exc(IntegrityError, 'null value in column "descrizione" violates not-null constraint',
                      column_name="descrizione", sqlstate="23502")
        with patch.object(self.svc._repo, "scrivi_record", side_effect=exc):
            with self.assertRaises(ServiceError) as cm:
                self.svc.create_record("magazzino.causali", {"codice": "X"})
        self.assertEqual(cm.exception.code, E_CONFIG_VALIDATION)
        self.assertEqual(cm.exception.fields, ("descrizione",))

    # 6.
    def test_p0001_del_trigger_porta_il_suo_codice(self) -> None:
        exc = _db_exc(DatabaseError, "Impossibile modificare il valore interno della colonna codice_interno",
                      constraint_name="E_CODICE_NON_MODIFICABILE", sqlstate="P0001")
        with patch.object(self.svc._repo, "scrivi_record", side_effect=exc):
            with self.assertRaises(ServiceError) as cm:
                self.svc.update_record("magazzino.causali", 13, {"codice_interno": "Y"})
        self.assertEqual(cm.exception.code, "E_CODICE_NON_MODIFICABILE")
        self.assertNotEqual(cm.exception.code, E_CONFIG_DUPLICATO)

    # Il modulo importa la whitelist, non un superset: e' il presidio di Q-6.
    def test_nessun_superset_della_whitelist(self) -> None:
        self.assertFalse(hasattr(svc_mod, "CONFIG_TABLES"))
