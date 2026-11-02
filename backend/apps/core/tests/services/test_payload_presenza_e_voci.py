# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari dei due BB di `PayloadValidator` nati il 2026-10-21
#        (regola del 2, ok Tid): `campi_per_presenza` (la PATCH letta per
#        presenza) e `voci` (una lista di voci, ogni voce un oggetto).
#        Nessun accesso DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_presenza_assente_non_si_tocca        — chiave assente: fuori dal dict
 2) test_presenza_null_svuota_il_nullable     — testo/intero nullable: `null` e "" -> None
 3) test_presenza_not_null_rifiuta_null       — testo NOT NULL, id obbligatorio, flag: `null` -> 400 col campo
 4) test_presenza_max_len_e_maiuscoli         — oltre il tetto -> 400; i maiuscoli si scrivono maiuscoli
 5) test_presenza_flag_rigoroso               — "true" non e' un booleano
 6) test_presenza_altri_lettori               — il lettore del dominio e' chiamato solo se la chiave c'e'
 7) test_presenza_chiave_fuori_contratto      — 400 col messaggio del dominio
 8) test_presenza_patch_vuota                 — 400 con message/detail/context del dominio
 9) test_presenza_ammesse_coerente            — `ammesse` uguale alle dichiarate passa
10) test_presenza_dichiarazione_incoerente    — doppia chiave, maiuscolo non testo, ammesse divergenti -> RuntimeError
11) test_presenza_codice_e_function_name      — codice dell'istanza, function_name per-chiamata
12) test_voci_ok_con_indice                   — ogni voce passa dal lettore, con l'indice
13) test_voci_non_lista                       — None, dict, stringa -> 400 col campo
14) test_voci_voce_non_oggetto                — 400 col campo e l'indice nel detail/context
15) test_voci_message_del_dominio             — `message` sostituisce le frasi, il detail resta
16) test_voci_lista_vuota                     — [] e' una lista: nessuna voce, nessun errore
"""

from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.service_errors import ServiceError

_CODE = "E_TEST_VALIDATION"


class TestCampiPerPresenza(TestCase):
    """La PATCH letta per presenza: presente si scrive, assente non si tocca."""

    def setUp(self) -> None:
        self.v = PayloadValidator(validation_code=_CODE)

    def _leggi(self, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        dichiarazione: dict[str, Any] = {
            "testi": {"codice": (False, 5), "nota": (True, 10), "sigla": (True, 3)},
            "maiuscoli": frozenset({"sigla"}),
            "interi": {"tipo_id": False, "parent_id": True},
            "flag": frozenset({"attivo"}),
        }
        dichiarazione.update(kwargs)
        return self.v.campi_per_presenza(payload, **dichiarazione)

    def _rifiuto(self, payload: dict[str, Any], **kwargs: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as ctx:
            self._leggi(payload, **kwargs)
        self.assertEqual(ctx.exception.code, _CODE)
        return ctx.exception

    # 1) Scopo: una chiave assente non entra nel dict da scrivere.
    def test_presenza_assente_non_si_tocca(self) -> None:
        self.assertEqual(self._leggi({"codice": " A1 "}), {"codice": "A1"})

    # 2) Scopo: sui nullable `null` (e "" sul testo) AZZERA: la chiave c'e', col None.
    def test_presenza_null_svuota_il_nullable(self) -> None:
        self.assertEqual(
            self._leggi({"nota": None, "sigla": "  ", "parent_id": None}),
            {"nota": None, "sigla": None, "parent_id": None},
        )

    # 3) Scopo: sui NOT NULL un `null` e' un 400 che nomina il campo, mai un reset.
    def test_presenza_not_null_rifiuta_null(self) -> None:
        for chiave in ("codice", "tipo_id", "attivo"):
            with self.subTest(chiave=chiave):
                errore = self._rifiuto({chiave: None})
                self.assertEqual(errore.context.get("field"), chiave)
        self.assertEqual(self._rifiuto({"codice": "  "}).context.get("field"), "codice")

    # 4) Scopo: il tetto della colonna e' un 400; i maiuscoli si scrivono maiuscoli.
    def test_presenza_max_len_e_maiuscoli(self) -> None:
        self.assertEqual(self._rifiuto({"codice": "ABCDEF"}).context.get("field"), "codice")
        self.assertEqual(self._leggi({"sigla": " it "}), {"sigla": "IT"})
        self.assertEqual(self._leggi({"nota": " it "}), {"nota": "it"})

    # 5) Scopo: un flag e' un booleano JSON; e un id positivo, non 0 ne' True.
    def test_presenza_flag_rigoroso(self) -> None:
        self.assertEqual(self._leggi({"attivo": False}), {"attivo": False})
        self.assertEqual(self._rifiuto({"attivo": "true"}).context.get("field"), "attivo")
        for valore in (0, True, "x"):
            with self.subTest(valore=valore):
                self.assertEqual(self._rifiuto({"parent_id": valore}).context.get("field"), "parent_id")
        self.assertEqual(self._leggi({"tipo_id": "7"}), {"tipo_id": 7})

    # 6) Scopo: un lettore del dominio riceve (payload, chiave), solo se la chiave c'e'.
    def test_presenza_altri_lettori(self) -> None:
        lettore = MagicMock(return_value={"x": 1})
        self.assertEqual(self._leggi({"meta": "grezzo"}, altri={"meta": lettore}), {"meta": {"x": 1}})
        lettore.assert_called_once_with({"meta": "grezzo"}, "meta")
        lettore.reset_mock()
        self._leggi({"codice": "A"}, altri={"meta": lettore})
        lettore.assert_not_called()

    # 7) Scopo: una chiave fuori contratto e' un 400, col messaggio del dominio.
    def test_presenza_chiave_fuori_contratto(self) -> None:
        errore = self._rifiuto({"codice": "A", "ignota": 1}, message="Campi non modificabili.")
        self.assertEqual(errore.message, "Campi non modificabili.")
        self.assertEqual(errore.context.get("unknown_keys"), ["ignota"])

    # 8) Scopo: una PATCH senza campi e' un 400, con le frasi del dominio.
    def test_presenza_patch_vuota(self) -> None:
        errore = self._rifiuto(
            {}, message_vuoto="Payload UoM non valido.", detail_vuoto="Nessun campo.", context_vuoto={"op": "x"},
        )
        self.assertEqual(errore.message, "Payload UoM non valido.")
        self.assertEqual(errore.detail, "Nessun campo.")
        self.assertEqual(errore.context.get("op"), "x")
        self.assertEqual(self._rifiuto({}).message, "Nessun campo aggiornabile presente nel payload.")

    # 9) Scopo: il contratto pubblicato coincide con le chiavi lette: passa.
    def test_presenza_ammesse_coerente(self) -> None:
        ammesse = frozenset({"codice", "nota", "sigla", "tipo_id", "parent_id", "attivo"})
        self.assertEqual(self._leggi({"attivo": True}, ammesse=ammesse), {"attivo": True})

    # 10) Scopo: ⛔ una dichiarazione incoerente e' un errore di chi scrive il
    #     service (RuntimeError, 500), non un 400 dell'operatore.
    def test_presenza_dichiarazione_incoerente(self) -> None:
        casi: dict[str, dict[str, Any]] = {
            "doppia": {"interi": {"codice": False}},
            "maiuscolo_non_testo": {"maiuscoli": frozenset({"tipo_id"})},
            "ammessa_non_letta": {"ammesse": frozenset({"codice", "nota", "sigla", "tipo_id", "parent_id", "attivo", "meta"})},
            "letta_non_ammessa": {"ammesse": frozenset({"codice"})},
        }
        for nome, kwargs in casi.items():
            with self.subTest(nome), self.assertRaises(RuntimeError):
                self._leggi({"codice": "A"}, **kwargs)

    # 11) Scopo: il codice e' quello dell'istanza; log_to_db e function_name
    #     per-chiamata arrivano al log dell'errore.
    def test_presenza_codice_e_function_name(self) -> None:
        with patch("apps.core.services.error_manager.ErrorManager.log_error_only") as mock_log:
            self._rifiuto({"attivo": None}, log_to_db=True, function_name="dominio.fn")
        self.assertEqual(mock_log.call_args.kwargs.get("function_name"), "dominio.fn")


class TestVoci(TestCase):
    """Una lista di voci, ogni voce un oggetto, ogni voce letta dal dominio."""

    def setUp(self) -> None:
        self.v = PayloadValidator(validation_code=_CODE)

    # 12) Scopo: ogni voce passa dal lettore, con il suo indice; l'ordine resta.
    def test_voci_ok_con_indice(self) -> None:
        lette = self.v.voci([{"a": 1}, {"a": 2}], lambda voce, indice: (indice, voce["a"]), campo="aree")
        self.assertEqual(lette, [(0, 1), (1, 2)])

    # 13) Scopo: ⛔ None NON e' una lista vuota: e' un 400 col campo.
    def test_voci_non_lista(self) -> None:
        for valore in (None, {"a": 1}, "[]", 3):
            with self.subTest(valore=valore), self.assertRaises(ServiceError) as ctx:
                self.v.voci(valore, lambda voce, _i: voce, campo="aree")
            self.assertEqual(ctx.exception.code, _CODE)
            self.assertEqual(ctx.exception.context.get("field"), "aree")
            self.assertEqual(ctx.exception.message, "'aree' deve essere una lista.")

    # 14) Scopo: una voce che non e' un oggetto e' un 400 (era un AttributeError/KeyError, 500).
    def test_voci_voce_non_oggetto(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.v.voci([{"a": 1}, "x"], lambda voce, _i: voce, campo="righe")
        self.assertEqual(ctx.exception.context.get("field"), "righe")
        self.assertEqual(ctx.exception.context.get("indice"), 1)
        self.assertEqual(ctx.exception.detail, "righe[1] deve essere un oggetto.")
        self.assertEqual(ctx.exception.message, "Ogni voce di 'righe' deve essere un oggetto.")

    # 15) Scopo: `message` del dominio sostituisce le due frasi; il detail resta.
    def test_voci_message_del_dominio(self) -> None:
        for valore, detail in ((None, "Il campo 'colonne' deve essere una lista."), ([1], "colonne[0] deve essere un oggetto.")):
            with self.subTest(valore=valore), self.assertRaises(ServiceError) as ctx:
                self.v.voci(valore, lambda voce, _i: voce, campo="colonne", message="Preferenza lista non valida.")
            self.assertEqual(ctx.exception.message, "Preferenza lista non valida.")
            self.assertEqual(ctx.exception.detail, detail)

    # 16) Scopo: la lista vuota ESPLICITA e' una lista (il modo di togliere tutto).
    def test_voci_lista_vuota(self) -> None:
        self.assertEqual(self.v.voci([], lambda voce, _i: voce, campo="aree"), [])
