# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test service vendite.promo_articoli. Mock repository (no DB).
#        Verifica validazione FK/UUID, enum variazione (PREZZO_FISSO ammesso),
#        coerenza date, immutabilita' codice/articolo/uom, mapping constraint.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_default_params                   — order_by default valido_dal desc
 2) test_list_invalid_order_by                 — order non whitelisted -> VALIDATION
 3) test_list_tipo_variazione_invalido         — filtro tipo non whitelisted -> VALIDATION
 4) test_list_uuid_invalido                    — articolo_id non UUID -> VALIDATION
 5) test_list_propaga_filtri                   — filtri passati al repo
 6) test_get_ok                                — delega repo
 7) test_get_not_found                         — repo None -> NOT_FOUND
 8) test_get_id_non_positivo                   — id <= 0 -> VALIDATION
 9) test_create_percentuale_ok                 — PERCENTUALE con valore > 0 OK
10) test_create_prezzo_fisso_ok                — PREZZO_FISSO con valore 0 ammesso
11) test_create_prezzo_fisso_negativo_ko       — PREZZO_FISSO < 0 -> VALIDATION
12) test_create_percentuale_zero_ko            — PERCENTUALE = 0 -> VALIDATION (deve essere > 0)
13) test_create_tipo_invalido                  — enum errato -> VALIDATION
14) test_create_missing_codice                 — codice mancante -> VALIDATION
15) test_create_missing_articolo               — articolo_id mancante -> VALIDATION
16) test_create_uuid_formato_invalido          — articolo_id non UUID -> VALIDATION
17) test_create_missing_uom                    — uom_id mancante -> VALIDATION
18) test_create_unknown_key                    — chiave extra -> VALIDATION
19) test_create_valido_al_prima_dal            — range date invalido -> VALIDATION
20) test_create_valido_al_required             — valido_al mancante -> VALIDATION
21) test_create_duplicate_codice               — UNIQUE codice -> DUPLICATO
22) test_create_overlap                        — ExclusionViolation -> PROMO_OVERLAP
23) test_create_fk_articolo                    — FK articolo -> VENDITE_FK
24) test_create_fk_uom                         — FK uom -> VENDITE_FK
25) test_update_descrizione_ok                 — PATCH descrizione OK
26) test_update_codice_rifiutato               — PATCH codice -> VALIDATION (immutabile)
27) test_update_articolo_rifiutato             — PATCH articolo_id -> VALIDATION
28) test_update_uom_rifiutato                  — PATCH uom_id -> VALIDATION
29) test_update_variazione_solo_tipo_ko        — PATCH solo tipo senza valore -> VALIDATION
30) test_update_variazione_coppia_ok           — PATCH tipo+valore coerenti -> OK
31) test_update_payload_vuoto                  — PATCH vuoto -> VALIDATION
32) test_update_not_found                      — repo False -> NOT_FOUND
"""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.promo_articoli_service import PromoArticoliService


_REPO = "apps.vendite.services.promo_articoli_service.PromoArticoliRepository"
_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"


def _base_payload(**overrides):
    data = {
        "codice": "PROMO-SILV",
        "descrizione": "Promo silver 2026",
        "articolo_id": _UUID,
        "uom_id": 3,
        "tipo_variazione": "PERCENTUALE",
        "valore_variazione": "10.0",
        "valido_dal": "2026-01-01",
        "valido_al": "2026-12-31",
    }
    data.update(overrides)
    return data


class TestList(TestCase):
    @patch(_REPO)
    def test_list_default_params(self, mock_repo):
        mock_repo.return_value.list_promo.return_value = ([], 0)
        svc = PromoArticoliService()
        svc.list_promo()
        kwargs = mock_repo.return_value.list_promo.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "valido_dal")
        self.assertEqual(kwargs["order_dir"], "desc")

    @patch(_REPO)
    def test_list_invalid_order_by(self, mock_repo):
        del mock_repo
        svc = PromoArticoliService()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_promo(order_by="bad")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_list_tipo_variazione_invalido(self, mock_repo):
        del mock_repo
        svc = PromoArticoliService()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_promo(tipo_variazione="SCONTO")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_list_uuid_invalido(self, mock_repo):
        del mock_repo
        svc = PromoArticoliService()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_promo(articolo_id="not-a-uuid")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_list_propaga_filtri(self, mock_repo):
        mock_repo.return_value.list_promo.return_value = ([], 0)
        svc = PromoArticoliService()
        svc.list_promo(articolo_id=_UUID, uom_id=5, tipo_variazione="PREZZO_FISSO")
        kwargs = mock_repo.return_value.list_promo.call_args.kwargs
        self.assertEqual(kwargs["articolo_id"], _UUID)
        self.assertEqual(kwargs["uom_id"], 5)
        self.assertEqual(kwargs["tipo_variazione"], "PREZZO_FISSO")


class TestGet(TestCase):
    @patch(_REPO)
    def test_get_ok(self, mock_repo):
        mock_repo.return_value.get_promo.return_value = {"id": 1}
        self.assertEqual(PromoArticoliService().get_promo(1), {"id": 1})

    @patch(_REPO)
    def test_get_not_found(self, mock_repo):
        mock_repo.return_value.get_promo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().get_promo(999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch(_REPO)
    def test_get_id_non_positivo(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().get_promo(0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class TestCreate(TestCase):
    @patch(_REPO)
    def test_create_percentuale_ok(self, mock_repo):
        mock_repo.return_value.create_promo.return_value = 1
        mock_repo.return_value.get_promo.return_value = {"id": 1}
        PromoArticoliService().create_promo(_base_payload())
        data = mock_repo.return_value.create_promo.call_args.args[0]
        self.assertEqual(data["tipo_variazione"], "PERCENTUALE")
        self.assertEqual(data["valore_variazione"], Decimal("10.0"))

    @patch(_REPO)
    def test_create_prezzo_fisso_ok(self, mock_repo):
        mock_repo.return_value.create_promo.return_value = 1
        mock_repo.return_value.get_promo.return_value = {"id": 1}
        PromoArticoliService().create_promo(_base_payload(
            tipo_variazione="PREZZO_FISSO", valore_variazione="0",
        ))
        data = mock_repo.return_value.create_promo.call_args.args[0]
        self.assertEqual(data["tipo_variazione"], "PREZZO_FISSO")
        self.assertEqual(data["valore_variazione"], Decimal("0"))

    @patch(_REPO)
    def test_create_prezzo_fisso_negativo_ko(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                tipo_variazione="PREZZO_FISSO", valore_variazione="-5",
            ))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_percentuale_zero_ko(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                valore_variazione="0",
            ))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_tipo_invalido(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                tipo_variazione="NON_VALIDO",
            ))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_missing_codice(self, mock_repo):
        del mock_repo
        payload = _base_payload()
        del payload["codice"]
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(payload)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_missing_articolo(self, mock_repo):
        del mock_repo
        payload = _base_payload()
        del payload["articolo_id"]
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(payload)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_uuid_formato_invalido(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(articolo_id="xxx"))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_missing_uom(self, mock_repo):
        del mock_repo
        payload = _base_payload()
        del payload["uom_id"]
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(payload)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_unknown_key(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(colonna_ignota=1))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_valido_al_prima_dal(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                valido_dal="2026-06-01", valido_al="2026-01-01",
            ))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_valido_al_required(self, mock_repo):
        del mock_repo
        payload = _base_payload()
        del payload["valido_al"]
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(payload)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_create_duplicate_codice(self, mock_repo):
        mock_repo.return_value.create_promo.side_effect = IntegrityError(
            'duplicate key value violates unique constraint "uq_promo_articoli_codice"'
        )
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload())
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")

    @patch(_REPO)
    def test_create_overlap(self, mock_repo):
        mock_repo.return_value.create_promo.side_effect = IntegrityError(
            'conflicting key value violates exclusion constraint '
            '"ex_promo_articoli_no_overlap"'
        )
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload())
        self.assertEqual(ctx.exception.code, "E_VENDITE_PROMO_OVERLAP")

    @patch(_REPO)
    def test_create_fk_articolo(self, mock_repo):
        mock_repo.return_value.create_promo.side_effect = IntegrityError(
            'foreign key constraint "fk_promo_articoli_articolo"'
        )
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload())
        self.assertEqual(ctx.exception.code, "E_VENDITE_FK")

    @patch(_REPO)
    def test_create_fk_uom(self, mock_repo):
        mock_repo.return_value.create_promo.side_effect = IntegrityError(
            'foreign key constraint "fk_promo_articoli_uom"'
        )
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload())
        self.assertEqual(ctx.exception.code, "E_VENDITE_FK")


class TestUpdate(TestCase):
    @patch(_REPO)
    def test_update_descrizione_ok(self, mock_repo):
        mock_repo.return_value.update_promo.return_value = True
        mock_repo.return_value.get_promo.return_value = {"id": 1}
        PromoArticoliService().update_promo(1, {"descrizione": "Nuova descr"})
        data = mock_repo.return_value.update_promo.call_args.args[1]
        self.assertEqual(data["descrizione"], "Nuova descr")

    @patch(_REPO)
    def test_update_codice_rifiutato(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"codice": "X"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_update_articolo_rifiutato(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"articolo_id": _UUID})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_update_uom_rifiutato(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"uom_id": 5})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_update_variazione_solo_tipo_ko(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"tipo_variazione": "PERCENTUALE"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_update_variazione_coppia_ok(self, mock_repo):
        mock_repo.return_value.update_promo.return_value = True
        mock_repo.return_value.get_promo.return_value = {"id": 1}
        PromoArticoliService().update_promo(1, {
            "tipo_variazione": "VALORE_FISSO",
            "valore_variazione": "2.5",
        })
        data = mock_repo.return_value.update_promo.call_args.args[1]
        self.assertEqual(data["tipo_variazione"], "VALORE_FISSO")
        self.assertEqual(data["valore_variazione"], Decimal("2.5"))

    @patch(_REPO)
    def test_update_payload_vuoto(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO)
    def test_update_not_found(self, mock_repo):
        mock_repo.return_value.update_promo.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(999, {"descrizione": "X"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
