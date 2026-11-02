# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dei BB `testata_o_not_found` («leggi prima la testata») e
#        `riga_del_padre_o_not_found` («la riga e' del documento dell'URL»).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1. test_ritorna_la_testata_quando_il_getter_la_trova
 2. test_solleva_il_codice_del_dominio_quando_il_getter_risponde_none
 3. test_il_detail_nomina_il_parametro_e_il_valore
 4. test_riga_del_padre_ritorna_la_riga_quando_appartiene
 5. test_riga_del_padre_404_se_inesistente
 6. test_riga_del_padre_404_se_di_un_altro_documento
 7. test_riga_del_padre_confronta_gli_id_come_interi
 8. test_o_not_found_ritorna_l_entita_o_solleva_senza_function_name
"""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.core.services.testata_guard import (
    o_not_found,
    riga_del_padre_o_not_found,
    testata_o_not_found,
)


class TestataGuardTests(SimpleTestCase):
    # Scopo: sul caso felice il guard e' trasparente: ritorna cio' che il
    #        getter ha letto e lo chiama una volta sola con l'id.
    def test_ritorna_la_testata_quando_il_getter_la_trova(self) -> None:
        getter = MagicMock(return_value={"id": 7, "stato": "DRAFT"})
        out = testata_o_not_found(
            getter, 7, code="E_X_NOT_FOUND", message="X non trovato.",
            id_name="x_id", function_name="test.caso_felice",
        )
        self.assertEqual(out, {"id": 7, "stato": "DRAFT"})
        getter.assert_called_once_with(7)

    # Scopo: `None` dal getter — id inesistente o fuori perimetro RLS — diventa
    #        il ServiceError col codice del dominio, non un `None` che scende.
    def test_solleva_il_codice_del_dominio_quando_il_getter_risponde_none(self) -> None:
        getter = MagicMock(return_value=None)
        with self.assertRaises(ServiceError) as cm:
            testata_o_not_found(
                getter, 99, code="E_X_NOT_FOUND", message="X non trovato.",
                id_name="x_id", function_name="test.non_trovato",
            )
        self.assertEqual(cm.exception.code, "E_X_NOT_FOUND")
        self.assertEqual(cm.exception.message, "X non trovato.")

    # Scopo: il `detail` e' la traccia che serve a chi legge il log: nomina il
    #        parametro e il valore chiesto.
    def test_il_detail_nomina_il_parametro_e_il_valore(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            testata_o_not_found(
                lambda _id: None, 42, code="E_X_NOT_FOUND", message="X non trovato.",
                id_name="ordine_id", function_name="test.detail",
            )
        self.assertEqual(cm.exception.detail, "ordine_id=42")


_KW = {
    "chiave_padre": "ordine_id", "code": "E_X_NOT_FOUND",
    "message": "Riga non trovata per questo X.", "function_name": "test.riga",
}


class RigaDelPadreGuardTests(SimpleTestCase):
    # Scopo: caso felice: la riga c'e' ed e' del padre chiesto — torna com'e'.
    def test_riga_del_padre_ritorna_la_riga_quando_appartiene(self) -> None:
        getter = MagicMock(return_value={"id": 31, "ordine_id": 7})
        out = riga_del_padre_o_not_found(getter, 31, padre_id=7, **_KW)
        self.assertEqual(out, {"id": 31, "ordine_id": 7})
        getter.assert_called_once_with(31)

    # Scopo: `None` dal getter (inesistente o fuori perimetro RLS) e' il 404
    #        del dominio.
    def test_riga_del_padre_404_se_inesistente(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            riga_del_padre_o_not_found(lambda _id: None, 31, padre_id=7, **_KW)
        self.assertEqual(cm.exception.code, "E_X_NOT_FOUND")
        self.assertEqual(cm.exception.detail, "ordine_id=7 riga_id=31")

    # Scopo: ⛔ id incrociato: la riga esiste ma e' di un altro documento — lo
    #        stesso 404, e il detail porta gli id CHIESTI, non il padre vero.
    def test_riga_del_padre_404_se_di_un_altro_documento(self) -> None:
        getter = MagicMock(return_value={"id": 31, "ordine_id": 8})
        with self.assertRaises(ServiceError) as cm:
            riga_del_padre_o_not_found(getter, 31, padre_id=7, **_KW)
        self.assertEqual(cm.exception.code, "E_X_NOT_FOUND")
        self.assertNotIn("8", cm.exception.detail or "")

    # Scopo: un padre arrivato come stringa (chiamante interno) non deve dare
    #        un 404 muto su una riga che esiste: si confrontano interi.
    def test_riga_del_padre_confronta_gli_id_come_interi(self) -> None:
        getter = MagicMock(return_value={"id": 31, "ordine_id": 7})
        out = riga_del_padre_o_not_found(getter, 31, padre_id="7", **_KW)  # type: ignore[arg-type]
        self.assertEqual(out["id"], 31)


class ONotFoundTests(SimpleTestCase):
    # Scopo: il nucleo su cui poggiano gli altri due (e `require_found` di
    #        anagrafiche): entita' gia' letta → torna com'e'; `None` → il codice
    #        del dominio, e senza `function_name` resta il default di
    #        ErrorManager, non un nome inventato.
    def test_o_not_found_ritorna_l_entita_o_solleva_senza_function_name(self) -> None:
        self.assertEqual(o_not_found({"id": 1}, code="E_X_NOT_FOUND", message="m"), {"id": 1})
        with self.assertRaises(ServiceError) as cm:
            o_not_found(None, code="E_X_NOT_FOUND", message="X non trovato.")
        self.assertEqual(cm.exception.code, "E_X_NOT_FOUND")
        self.assertIsNone(cm.exception.detail)
