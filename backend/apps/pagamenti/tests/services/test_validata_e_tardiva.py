# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del service `pagamenti` per il seguito del TERZO collaudo
#        in-app (D20, brief-db-validata-e-registrazione-tardiva §5): il verbo
#        «valida» col suo motivo nel dettaglio (BE-1), le scartate «non
#        nostre» in quadratura, e la registrazione TARDIVA per riga (BE-3).
# Note: ⚠️ A mock: qui si provano le regole che il BACKEND tiene — il cancello
#       della terna, la lettura del payload, la derivazione del cliente, la
#       forma della risposta. La madre e i suoi guard si provano sul DB
#       provvisto (`tests/db/test_validata_e_tardiva_db.py`) e in pgTAP.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  DettaglioTests.test_la_terna_viaggia_se_lo_stato_ammette_validata
2)  DettaglioTests.test_la_terna_si_azzera_dove_validata_non_e_fra_le_uscite
3)  DettaglioTests.test_le_scartate_in_quadratura_dalle_righe_per_stato
4)  DettaglioTests.test_senza_righe_per_stato_le_scartate_sono_zero
5)  TardivaTests.test_la_fattura_e_obbligatoria
6)  TardivaTests.test_il_cliente_assente_si_legge_dalla_fattura
7)  TardivaTests.test_il_cliente_passato_arriva_com_e
8)  TardivaTests.test_motivo_senza_forzatura_rifiutato
9)  TardivaTests.test_chiavi_fuori_contratto_rifiutate
10) TardivaTests.test_riga_inesistente_404_prima_della_madre
11) TardivaTests.test_la_risposta_porta_ricevuta_e_riga
12) TardivaTests.test_il_backend_non_decide_ne_stato_ne_capienza
"""

import inspect
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec, patch

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.services import pagamenti_service
from apps.pagamenti.db.pagamenti_repository import PagamentiRepository

_RIFERIMENTI = {
    "fattura_id": 2263, "billing_account_id": 41,
    "emittente_soggetto_ruolo_id": 32, "cliente_soggetto_ruolo_id": 9,
}

# La matrice della TESTATA come la legge il repository: da BOZZA si chiede
# VALIDATA, da CHIUSA non si chiede niente.
_GRAFO_DISTINTA = [("BOZZA", "VALIDATA"), ("BOZZA", "ANNULLATA"), ("VALIDATA", "BOZZA")]

_TERNA_BLOCCATA = {
    "validazione_blocco_reason": "RIGHE_NON_LAVORATE",
    "validazione_blocco_reason_key": "pagamenti.distinte.validazione_reason.righe_non_lavorate",
    "validazione_blocco_dettaglio": {"quante": 2, "contabile_righe_ids": [1, 2]},
    "can_validare": False,
}


def _distinta(**over):
    riga = {
        "id": 7, "codice": "DIS-0001", "stato_codice": "BOZZA", "origine": "MANUALE",
        "stato_info_key": None, "stato_is_registrabile": False,
        "righe_totali": 0, "righe_registrabili": 0,
        "totale_righe": Decimal("0"), "totale_registrabile": Decimal("0"),
        "importo_dichiarato": None, "scarto_dichiarato": None,
        "righe_per_stato": [],
        **_TERNA_BLOCCATA,
    }
    riga.update(over)
    return riga


def _repo() -> MagicMock:
    repo = create_autospec(PagamentiRepository, instance=True)
    repo.get_distinta.return_value = _distinta()
    repo.get_riga.return_value = {"id": 11, "contabile_id": 7, "attivo": True,
                                  "stato_codice": "SOSPESA"}
    repo.get_riferimenti_fattura.return_value = dict(_RIFERIMENTI)
    repo.list_stati_distinta.return_value = []
    repo.list_stati_riga.return_value = []
    repo.list_transizioni.return_value = (list(_GRAFO_DISTINTA), [])
    repo.posta_riga_tardiva.return_value = {
        "movimento_id": 501, "riga_id": 11, "importo": Decimal("60.00"), "esito": "POSTATA",
    }
    return repo


class _Base(SimpleTestCase):
    # Scopo: Sostituisce il repository con un doppio per ogni test.
    def setUp(self) -> None:
        self.repo = _repo()
        patcher = patch.object(
            pagamenti_service, "PagamentiRepository", autospec=True, return_value=self.repo
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class DettaglioTests(_Base):
    # Scopo: BE-1 — da uno stato che ammette VALIDATA la terna del verbo
    #        «valida» arriva com'e' dal repository (cioe' dalla check).
    def test_la_terna_viaggia_se_lo_stato_ammette_validata(self):
        d = pagamenti_service.get_distinta(7)["distinta"]
        self.assertIs(d["can_validare"], False)
        self.assertEqual(d["validazione_blocco_reason"], "RIGHE_NON_LAVORATE")
        self.assertEqual(
            d["validazione_blocco_reason_key"],
            "pagamenti.distinte.validazione_reason.righe_non_lavorate",
        )
        self.assertEqual(d["validazione_blocco_dettaglio"]["quante"], 2)

    # Scopo: ⚠️ Dove VALIDATA non e' fra le uscite (CHIUSA, ANNULLATA) la terna
    #        si AZZERA: un motivo su un verbo che non si propone e' rumore, e
    #        il frontend non deve nemmeno poterlo leggere per sbaglio.
    def test_la_terna_si_azzera_dove_validata_non_e_fra_le_uscite(self):
        self.repo.get_distinta.return_value = _distinta(stato_codice="CHIUSA")
        d = pagamenti_service.get_distinta(7)["distinta"]
        self.assertIsNone(d["can_validare"])
        self.assertIsNone(d["validazione_blocco_reason"])
        self.assertIsNone(d["validazione_blocco_reason_key"])
        self.assertIsNone(d["validazione_blocco_dettaglio"])

    # Scopo: ⭐ «Di cui non nostre» (D20-c): righe e importo delle SCARTATA si
    #        derivano dall'array per stato con lo STESSO codice con cui la
    #        lista le nasconde — una sede, non un secondo letterale.
    def test_le_scartate_in_quadratura_dalle_righe_per_stato(self):
        self.repo.get_distinta.return_value = _distinta(righe_per_stato=[
            {"stato_codice_interno": "ABBINATA", "stato_descrizione": "Abbinata",
             "righe": 3, "importo": Decimal("300.00")},
            {"stato_codice_interno": pagamenti_service.STATO_RIGA_SCARTATA,
             "stato_descrizione": "Scartata", "righe": 2, "importo": Decimal("15.50")},
        ])
        d = pagamenti_service.get_distinta(7)["distinta"]
        self.assertEqual(d["righe_scartate"], 2)
        self.assertEqual(d["totale_scartate"], Decimal("15.50"))
        # L'array resta intero accanto ai due numeri: e' cio' che il dialog di
        # validazione elenca.
        self.assertEqual(len(d["righe_per_stato"]), 2)

    def test_senza_righe_per_stato_le_scartate_sono_zero(self):
        self.repo.get_distinta.return_value = _distinta(righe_per_stato=None)
        d = pagamenti_service.get_distinta(7)["distinta"]
        self.assertEqual(d["righe_scartate"], 0)
        self.assertEqual(d["totale_scartate"], Decimal("0"))


class TardivaTests(_Base):
    # Scopo: Il payload e' quello di `abbina`: la fattura e' obbligatoria, e il
    #        rifiuto nomina il campo prima di qualunque lettura.
    def test_la_fattura_e_obbligatoria(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.registra_riga_tardiva(11, {"scadenza_id": 5})
        self.assertEqual(ctx.exception.context.get("field"), "fattura_id")
        self.repo.posta_riga_tardiva.assert_not_called()

    # Scopo: ⭐ Il cliente, se non lo dice chi chiama, e' quello della fattura —
    #        letto, non dedotto: la stessa regola della nascita e di `abbina`.
    def test_il_cliente_assente_si_legge_dalla_fattura(self):
        pagamenti_service.registra_riga_tardiva(11, {"fattura_id": 2263, "scadenza_id": 5})
        self.repo.get_riferimenti_fattura.assert_called_once_with(2263)
        kwargs = self.repo.posta_riga_tardiva.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 41)
        self.assertEqual(kwargs["fattura_id"], 2263)
        self.assertEqual(kwargs["scadenza_id"], 5)
        self.assertEqual(kwargs["riga_id"], 11)
        # Primo tentativo: SENZA forzatura, sempre.
        self.assertIs(kwargs["forzata"], False)
        self.assertIsNone(kwargs["motivo_forzatura"])

    def test_il_cliente_passato_arriva_com_e(self):
        pagamenti_service.registra_riga_tardiva(
            11, {"fattura_id": 2263, "billing_account_id": 99,
                 "forzata": True, "motivo_forzatura": "pagato doppio"},
        )
        self.repo.get_riferimenti_fattura.assert_not_called()
        kwargs = self.repo.posta_riga_tardiva.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 99)
        self.assertIs(kwargs["forzata"], True)
        self.assertEqual(kwargs["motivo_forzatura"], "pagato doppio")

    # Scopo: «Il motivo si scrive solo insieme alla forzatura», come ovunque.
    def test_motivo_senza_forzatura_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.registra_riga_tardiva(
                11, {"fattura_id": 2263, "motivo_forzatura": "senza forzare"}
            )
        self.assertEqual(ctx.exception.context.get("field"), "motivo_forzatura")
        self.repo.posta_riga_tardiva.assert_not_called()

    def test_chiavi_fuori_contratto_rifiutate(self):
        with self.assertRaises(ServiceError):
            pagamenti_service.registra_riga_tardiva(
                11, {"fattura_id": 2263, "nuovo_stato": "POSTATA"}
            )
        self.repo.posta_riga_tardiva.assert_not_called()

    # Scopo: Il 404 di dominio PRIMA della madre — «non esiste» e «non la vedi»
    #        restano indistinguibili, e la madre non viene svegliata.
    def test_riga_inesistente_404_prima_della_madre(self):
        self.repo.get_riga.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.registra_riga_tardiva(11, {"fattura_id": 2263})
        self.assertEqual(ctx.exception.code, pagamenti_service.E_RIGA_NON_TROVATA)
        self.repo.posta_riga_tardiva.assert_not_called()

    # Scopo: La risposta porta la RICEVUTA della madre (movimento, importo,
    #        esito) e la riga riletta — chi ha premuto vede il fatto.
    def test_la_risposta_porta_ricevuta_e_riga(self):
        esito = pagamenti_service.registra_riga_tardiva(11, {"fattura_id": 2263})
        self.assertEqual(esito["movimento_id"], 501)
        self.assertEqual(esito["esito"], "POSTATA")
        self.assertEqual(esito["importo"], Decimal("60.00"))
        self.assertEqual(esito["riga"]["id"], 11)
        # La riga si RILEGGE dopo la madre: due letture, non una.
        self.assertEqual(self.repo.get_riga.call_count, 2)

    # Scopo: ⛔ Presidio statico: il verbo non nomina ne' lo stato della riga
    #        («e' SOSPESA?»), ne' quello della distinta, ne' la capienza. Sono
    #        i guard della madre — riscriverli qui sarebbe la seconda sede.
    def test_il_backend_non_decide_ne_stato_ne_capienza(self):
        codice = "\n".join(
            riga for riga in inspect.getsource(pagamenti_service.registra_riga_tardiva).splitlines()
            if not riga.lstrip().startswith("#")
        )
        for parola in ("SOSPESA", "CHIUSA", "data_conferma", "capienza", "residuo"):
            self.assertNotIn(parola, codice)
