# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test service vendite.promo_articoli. Mock repository (no DB).
#        Verifica validazione FK/UUID, enum variazione (PREZZO_FISSO ammesso),
#        coerenza date, immutabilita' codice/articolo/uom, mapping constraint,
#        guard data-driven Profilo A (no retroattiva, iniziata ristretta,
#        scaduta immutabile).
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
12) test_create_percentuale_zero_ko            — PERCENTUALE = 0 -> VALIDATION (no-op)
12b) test_create_percentuale_negativo_ok       — PERCENTUALE = -10 -> OK (sconto, regressione fix v5)
12c) test_create_valore_non_numerico_ko        — 2026-09-18: `NaN`/bool/testo/assente -> VALIDATION col campo (il punto che traduce il BB)
13) test_create_tipo_invalido                  — enum errato -> VALIDATION
14) test_create_missing_codice                 — codice mancante -> VALIDATION
15) test_create_missing_articolo               — articolo_id mancante -> VALIDATION
16) test_create_uuid_formato_invalido          — articolo_id non UUID -> VALIDATION
17) test_create_missing_uom                    — uom_id mancante -> VALIDATION
18) test_create_unknown_key                    — chiave extra -> VALIDATION
19) test_create_delega_ordine_date_al_db      — range date invertito arriva al DB (guard comune)
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
32) test_update_not_found                      — get_promo None pre-update -> NOT_FOUND
33) test_create_valido_dal_oggi_ko             — valido_dal=oggi -> E_PROMO_RETROATTIVA
34) test_create_valido_dal_passato_ko          — valido_dal<oggi -> E_PROMO_RETROATTIVA
35) test_create_valido_al_passato_ko           — valido_al<oggi -> E_PROMO_RETROATTIVA
36) test_update_promo_scaduta_immutabile       — PATCH su promo scaduta -> E_PROMO_SCADUTA_IMMUTABILE
37) test_update_promo_iniziata_descrizione_ok  — PATCH descrizione su iniziata OK
38) test_update_promo_iniziata_valido_al_ok    — PATCH valido_al >= oggi su iniziata OK
39) test_update_promo_iniziata_valido_al_passato_ko — valido_al < oggi -> E_PROMO_RETROATTIVA
40) test_update_promo_iniziata_tipo_ristretto_ko — PATCH tipo_variazione su iniziata -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
41) test_update_promo_iniziata_attivo_ristretto_ko — PATCH attivo su iniziata -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
42) test_update_promo_iniziata_valido_dal_ristretto_ko — PATCH valido_dal su iniziata -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
43) test_update_promo_futura_valido_dal_oggi_ko — valido_dal=oggi su futura -> E_PROMO_RETROATTIVA
44) test_update_no_op_idempotente              — PATCH coi valori correnti -> ritorna current
45) test_update_promo_iniziata_no_op_su_tipo_ammesso — PATCH tipo identico su iniziata e' no-op, OK
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.vendite.services.promo_articoli_service import PromoArticoliService


_REPO = "apps.vendite.services.promo_articoli_service.PromoArticoliRepository"
_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"


# Date dinamiche relative a oggi (le guard del service usano oggi_aziendale(),
# quindi date hardcoded diventano stale appena passa l'anno).
_TODAY = oggi_aziendale()
_TOMORROW = _TODAY + timedelta(days=1)
_FAR_FUTURE = _TODAY + timedelta(days=365)

# ⛔ «Oggi» e' UNO per il test e per il service. `_TODAY` si calcola all'IMPORT
#    del modulo, la guardia del service a ogni CHIAMATA: una suite che passa la
#    mezzanotte fra le due vedeva `_TOMORROW` diventare «oggi» per il service, e
#    otto casi uscivano `E_PROMO_RETROATTIVA` (visto il 2026-10-21 su una suite
#    partita prima delle 24). Il giorno del service si fissa a quello del test.
_oggi_fisso = patch(
    "apps.vendite.services.promo_articoli_service.oggi_aziendale", return_value=_TODAY,
)


def setUpModule() -> None:
    _oggi_fisso.start()


def tearDownModule() -> None:
    _oggi_fisso.stop()


def _base_payload(**overrides):
    data = {
        "codice": "PROMO-SILV",
        "descrizione": "Promo silver",
        "articolo_id": _UUID,
        "uom_id": 3,
        "tipo_variazione": "PERCENTUALE",
        "valore_variazione": "10.0",
        # Default: domani -> +365gg (futuro, no-retroattiva).
        "valido_dal": _TOMORROW.isoformat(),
        "valido_al": _FAR_FUTURE.isoformat(),
    }
    data.update(overrides)
    return data


def _current_promo(*, dal: date, al: date, **overrides):
    """Stato attuale promo come ritornato da get_promo. Usato per
    mockare la pre-read del guard data-driven in update."""
    data = {
        "id": 1,
        "codice": "PROMO-SILV",
        "descrizione": "Promo silver",
        "articolo_id": _UUID,
        "uom_id": 3,
        "tipo_variazione": "PERCENTUALE",
        "valore_variazione": Decimal("10.0"),
        "valido_dal": dal,
        "valido_al": al,
        "attivo": True,
        "meta": None,
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
        mock_repo.return_value.get_capabilities.return_value = {}
        self.assertEqual(PromoArticoliService().get_promo(1), {"id": 1, "capabilities": {}})

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

    # Scopo: get_promo includa il blob capabilities (Fase 1.B3 refactor
    #        frontend vendite) — stato_temporale, can_update,
    #        min_valido_*, non_editable_fields — SOTTO `capabilities`, intatto
    #        (api.md §«Il blob sta SOTTO `capabilities`»).
    @patch(_REPO)
    def test_get_include_capabilities(self, mock_repo):
        mock_repo.return_value.get_promo.return_value = {"id": 1, "codice": "PR-1"}
        mock_repo.return_value.get_capabilities.return_value = {
            "stato_temporale": "INIZIATA",
            "can_update": True,
            "can_update_reason": None,
            "min_valido_dal": None,
            "min_valido_al": "2026-04-30",
            "non_editable_fields": ["codice", "articolo_id", "uom_id",
                                     "tipo_variazione", "valore_variazione",
                                     "valido_dal", "attivo"],
        }
        result = PromoArticoliService().get_promo(1)
        caps = result["capabilities"]
        self.assertEqual(caps, mock_repo.return_value.get_capabilities.return_value)
        self.assertEqual(caps["stato_temporale"], "INIZIATA")
        self.assertTrue(caps["can_update"])
        self.assertIn("codice", caps["non_editable_fields"])
        for chiave in caps:
            self.assertNotIn(chiave, result)
        mock_repo.return_value.get_capabilities.assert_called_once_with(1)


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

    # REGRESSIONE fix v5 2026-04-15: PERCENTUALE negativa = sconto, ammessa.
    # Il vincolo pre-v5 `> 0` bloccava gli sconti promo, incoerente col
    # resolver DB che applica `base * (1 + valore/100)`.
    @patch(_REPO)
    def test_create_percentuale_negativo_ok(self, mock_repo):
        mock_repo.return_value.create_promo.return_value = 1
        mock_repo.return_value.get_promo.return_value = {"id": 1}
        result = PromoArticoliService().create_promo(_base_payload(
            valore_variazione="-10",
        ))
        self.assertEqual(result["id"], 1)

    # Scopo: ⭐ Il punto che traduce (2026-09-18): la coercizione e' del BB
    #        `PayloadValidator`, ma che il codice del dominio e il CAMPO arrivino
    #        all'envelope resta scritto qui. `NaN` e' il valore che la copia
    #        locale lasciava passare: `Decimal("NaN") != 0` e' vero, quindi
    #        superava anche il guard di dominio e arrivava alla colonna.
    @patch(_REPO)
    def test_create_valore_non_numerico_ko(self, mock_repo):
        for raw in (None, "", "dieci", True, "NaN", "Infinity"):
            with self.subTest(raw=raw):
                with self.assertRaises(ServiceError) as ctx:
                    PromoArticoliService().create_promo(_base_payload(
                        valore_variazione=raw,
                    ))
                self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
                self.assertEqual(ctx.exception.context["field"], "valore_variazione")
        mock_repo.return_value.create_promo.assert_not_called()

    @patch(_REPO)
    def test_create_tipo_invalido(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                tipo_variazione="NON_VALIDO",
            ))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        # ⭐ Dal 2026-09-18 (BB `require_enum`) il rifiuto NOMINA il campo: la
        #    copia locale scriveva `{"tipo_variazione": tipo}` e il form non
        #    accendeva niente. E un tipo non-stringa e' un 400, non un 500.
        self.assertEqual(ctx.exception.context["field"], "tipo_variazione")
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(tipo_variazione=True))
        self.assertEqual(ctx.exception.context["field"], "tipo_variazione")

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

    # L'ordine delle date NON lo giudica il service: il guard comune del DB
    # risponde E_DATA_AL_MINORE_DAL col campo (provato sul DB vero in
    # apps/core/tests/db/test_date_validita_guard_comune_db).
    @patch(_REPO)
    def test_create_delega_ordine_date_al_db(self, mock_repo):
        mock_repo.return_value.create_promo.return_value = 1
        mock_repo.return_value.get_promo.return_value = {"id": 1}
        dal_late = _TODAY + timedelta(days=180)
        al_early = _TODAY + timedelta(days=30)
        PromoArticoliService().create_promo(_base_payload(
            valido_dal=dal_late.isoformat(), valido_al=al_early.isoformat(),
        ))
        data = mock_repo.return_value.create_promo.call_args.args[0]
        self.assertEqual((data["valido_dal"], data["valido_al"]), (dal_late, al_early))

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
    """
    Promo in stato FUTURA (valido_dal=domani, valido_al=+365gg) come
    default per non incrociare le guard data-driven nei test che
    verificano altre cose (validation, FK, immutabilita').
    """

    @staticmethod
    def _mock_promo_futura(mock_repo, *, after_update=None):
        """Configura get_promo per ritornare stato FUTURA prima e dopo
        l'update (tutti i test ne fanno la pre-read)."""
        current = _current_promo(dal=_TOMORROW, al=_FAR_FUTURE)
        mock_repo.return_value.get_promo.side_effect = [
            current,
            after_update or current,
        ]

    @patch(_REPO)
    def test_update_descrizione_ok(self, mock_repo):
        self._mock_promo_futura(mock_repo)
        mock_repo.return_value.update_promo.return_value = True
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
        self._mock_promo_futura(mock_repo)
        mock_repo.return_value.update_promo.return_value = True
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
        # NOT_FOUND ora viene dal pre-check get_promo (prima del guard
        # data-driven) - non dall'update_promo.
        mock_repo.return_value.get_promo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(999, {"descrizione": "X"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
        # update non deve essere chiamato se la promo non esiste.
        mock_repo.return_value.update_promo.assert_not_called()


class TestCreateRetroattiva(TestCase):
    """Guard create no-retroattiva: valido_dal > oggi, valido_al >= oggi."""

    @patch(_REPO)
    def test_create_valido_dal_oggi_ko(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                valido_dal=_TODAY.isoformat(),
                valido_al=_FAR_FUTURE.isoformat(),
            ))
        self.assertEqual(ctx.exception.code, "E_PROMO_RETROATTIVA")

    @patch(_REPO)
    def test_create_valido_dal_passato_ko(self, mock_repo):
        del mock_repo
        passato = (_TODAY - timedelta(days=10)).isoformat()
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                valido_dal=passato,
                valido_al=_FAR_FUTURE.isoformat(),
            ))
        self.assertEqual(ctx.exception.code, "E_PROMO_RETROATTIVA")

    @patch(_REPO)
    def test_create_valido_al_passato_ko(self, mock_repo):
        del mock_repo
        # Combinazione fully-retroattiva (entrambe le date passate, range
        # valido_al >= valido_dal rispettato): la guard sul valido_dal
        # blocca per prima. Il check valido_al < today separato non c'e'
        # piu' (ridondante con valido_dal > today + range >= dal, vedi
        # decisione DB nel trigger trgfn_promo_articoli_guard_data_driven).
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().create_promo(_base_payload(
                valido_dal=(_TODAY - timedelta(days=20)).isoformat(),
                valido_al=(_TODAY - timedelta(days=5)).isoformat(),
            ))
        self.assertEqual(ctx.exception.code, "E_PROMO_RETROATTIVA")


class TestUpdateDataDriven(TestCase):
    """Guard data-driven Profilo A in update (SCADUTA / INIZIATA / FUTURA)."""

    # ──── SCADUTA ────
    @patch(_REPO)
    def test_update_promo_scaduta_immutabile(self, mock_repo):
        scaduta = _current_promo(
            dal=_TODAY - timedelta(days=60),
            al=_TODAY - timedelta(days=10),
        )
        mock_repo.return_value.get_promo.return_value = scaduta
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"descrizione": "X"})
        self.assertEqual(ctx.exception.code, "E_PROMO_SCADUTA_IMMUTABILE")
        mock_repo.return_value.update_promo.assert_not_called()

    # ──── INIZIATA ────
    @patch(_REPO)
    def test_update_promo_iniziata_descrizione_ok(self, mock_repo):
        iniziata = _current_promo(
            dal=_TODAY - timedelta(days=10),
            al=_TODAY + timedelta(days=20),
        )
        mock_repo.return_value.get_promo.side_effect = [iniziata, iniziata]
        mock_repo.return_value.update_promo.return_value = True
        PromoArticoliService().update_promo(1, {"descrizione": "Nuova"})
        data = mock_repo.return_value.update_promo.call_args.args[1]
        self.assertEqual(data, {"descrizione": "Nuova"})

    @patch(_REPO)
    def test_update_promo_iniziata_valido_al_ok(self, mock_repo):
        iniziata = _current_promo(
            dal=_TODAY - timedelta(days=10),
            al=_TODAY + timedelta(days=20),
        )
        mock_repo.return_value.get_promo.side_effect = [iniziata, iniziata]
        mock_repo.return_value.update_promo.return_value = True
        new_al = (_TODAY + timedelta(days=40)).isoformat()
        PromoArticoliService().update_promo(1, {"valido_al": new_al})
        data = mock_repo.return_value.update_promo.call_args.args[1]
        self.assertEqual(data["valido_al"], _TODAY + timedelta(days=40))

    @patch(_REPO)
    def test_update_promo_iniziata_valido_al_passato_ko(self, mock_repo):
        iniziata = _current_promo(
            dal=_TODAY - timedelta(days=10),
            al=_TODAY + timedelta(days=20),
        )
        mock_repo.return_value.get_promo.return_value = iniziata
        # valido_al ieri: in iniziata e' bloccato (deve essere >= oggi).
        new_al = (_TODAY - timedelta(days=1)).isoformat()
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"valido_al": new_al})
        self.assertEqual(ctx.exception.code, "E_PROMO_RETROATTIVA")
        mock_repo.return_value.update_promo.assert_not_called()

    @patch(_REPO)
    def test_update_promo_iniziata_tipo_ristretto_ko(self, mock_repo):
        iniziata = _current_promo(
            dal=_TODAY - timedelta(days=10),
            al=_TODAY + timedelta(days=20),
            tipo_variazione="PERCENTUALE",
        )
        mock_repo.return_value.get_promo.return_value = iniziata
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {
                "tipo_variazione": "VALORE_FISSO",
                "valore_variazione": "5",
            })
        self.assertEqual(ctx.exception.code, "E_PROMO_INIZIATA_CAMPI_RISTRETTI")
        mock_repo.return_value.update_promo.assert_not_called()

    @patch(_REPO)
    def test_update_promo_iniziata_attivo_ristretto_ko(self, mock_repo):
        iniziata = _current_promo(
            dal=_TODAY - timedelta(days=10),
            al=_TODAY + timedelta(days=20),
            attivo=True,
        )
        mock_repo.return_value.get_promo.return_value = iniziata
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"attivo": False})
        self.assertEqual(ctx.exception.code, "E_PROMO_INIZIATA_CAMPI_RISTRETTI")
        mock_repo.return_value.update_promo.assert_not_called()

    @patch(_REPO)
    def test_update_promo_iniziata_valido_dal_ristretto_ko(self, mock_repo):
        iniziata = _current_promo(
            dal=_TODAY - timedelta(days=10),
            al=_TODAY + timedelta(days=20),
        )
        mock_repo.return_value.get_promo.return_value = iniziata
        new_dal = (_TODAY + timedelta(days=2)).isoformat()
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {"valido_dal": new_dal})
        self.assertEqual(ctx.exception.code, "E_PROMO_INIZIATA_CAMPI_RISTRETTI")
        mock_repo.return_value.update_promo.assert_not_called()

    # ──── FUTURA ────
    @patch(_REPO)
    def test_update_promo_futura_valido_dal_oggi_ko(self, mock_repo):
        futura = _current_promo(
            dal=_TODAY + timedelta(days=10),
            al=_TODAY + timedelta(days=30),
        )
        mock_repo.return_value.get_promo.return_value = futura
        with self.assertRaises(ServiceError) as ctx:
            PromoArticoliService().update_promo(1, {
                "valido_dal": _TODAY.isoformat(),
            })
        self.assertEqual(ctx.exception.code, "E_PROMO_RETROATTIVA")
        mock_repo.return_value.update_promo.assert_not_called()

    # ──── No-op idempotenza ────
    @patch(_REPO)
    def test_update_no_op_idempotente(self, mock_repo):
        # FE invia tutti i campi del form anche se l'utente non ha cambiato
        # nulla. Risultato atteso: ritorna current senza chiamare update_promo
        # (drop dei no-op svuota completamente data).
        futura = _current_promo(
            dal=_TODAY + timedelta(days=10),
            al=_TODAY + timedelta(days=30),
            descrizione="X",
            tipo_variazione="PERCENTUALE",
            valore_variazione=Decimal("10.0"),
        )
        mock_repo.return_value.get_promo.return_value = futura
        PromoArticoliService().update_promo(1, {
            "descrizione": "X",
            "tipo_variazione": "PERCENTUALE",
            "valore_variazione": "10.0",
            "valido_dal": (_TODAY + timedelta(days=10)).isoformat(),
            "valido_al": (_TODAY + timedelta(days=30)).isoformat(),
            "attivo": True,
        })
        mock_repo.return_value.update_promo.assert_not_called()

    @patch(_REPO)
    def test_update_promo_iniziata_no_op_su_tipo_ammesso(self, mock_repo):
        # In iniziata, anche se l'utente invia tipo_variazione (campo
        # non whitelist), se uguale al corrente e' no-op droppato prima
        # del guard -> non solleva CAMPI_RISTRETTI.
        iniziata = _current_promo(
            dal=_TODAY - timedelta(days=10),
            al=_TODAY + timedelta(days=20),
            tipo_variazione="PERCENTUALE",
            valore_variazione=Decimal("10.0"),
        )
        mock_repo.return_value.get_promo.side_effect = [iniziata, iniziata]
        mock_repo.return_value.update_promo.return_value = True
        PromoArticoliService().update_promo(1, {
            "descrizione": "Nuova",
            "tipo_variazione": "PERCENTUALE",
            "valore_variazione": "10.0",
        })
        data = mock_repo.return_value.update_promo.call_args.args[1]
        self.assertEqual(data, {"descrizione": "Nuova"})
