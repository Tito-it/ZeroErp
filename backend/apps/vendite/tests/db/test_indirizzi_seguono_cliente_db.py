# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli indirizzi del documento seguono il cliente, dal service vero al
#        DATABASE VERO (brief-db-indirizzi-documento-seguono-il-cliente, §6):
#        cio' che i test di servizio, col repository mockato, non vedono.
#          · R-BE-1: il binding di `vendite.fn_doc_indirizzo_default` (selettore
#            del documento, id) e che la creazione lo chiami davvero;
#          · R-BE-2: senza i due `require` Python, un indirizzo d'altri lo
#            rifiuta il guard DB, e il rifiuto arriva col codice e col campo
#            (`tipo_indirizzo_id`) da accendere;
#          · il cambio di cliente in bozza (trigger), su cui conta il FE per
#            ricaricare il pannello (R-FE-2).
# Note: ⛔ Il backend NON controlla le regole: stanno nel DB (guard d'origine,
#       slot di default come dato, trigger del cambio di cliente).
#       ⚠️ Il mondo si COSTRUISCE: azienda, operatore e cliente A da
#       `dbops.fn_pgtap_crea_mondo_cliente` (che apre il contesto operatore), il
#       cliente B da `fn_pgtap_crea_cliente_ba` sulla stessa azienda. Ogni
#       cliente nasce col suo indirizzo di Fatturazione di ruolo, generico: e'
#       la fonte del ripiego dello slot CON. Transazione SEMPRE annullata, ogni
#       rifiuto atteso in un savepoint. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso
#       in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) IndirizziSeguonoClienteDbTests.test_crea_ddt_riempie_lo_slot_di_default_dal_cliente
2) IndirizziSeguonoClienteDbTests.test_slot_pieno_il_building_block_non_scrive
3) IndirizziSeguonoClienteDbTests.test_cambio_cliente_in_bozza_lo_slot_segue_il_cliente
4) IndirizziSeguonoClienteDbTests.test_picker_indirizzo_di_un_altro_cliente_rifiutato_col_campo
5) IndirizziSeguonoClienteDbTests.test_origine_soggetto_di_un_altro_cliente_rifiutata_col_campo
6) IndirizziSeguonoClienteDbTests.test_una_tantum_si_scrive
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.services import ddt_service

_CODICE = "E_INDIRIZZO_DOC_NON_DEL_CLIENTE"


class IndirizziSeguonoClienteDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda e' il building block: senza, il test non ha materia.
        # ⚠️ Dal 2026-10-19 (20261019-47, grammatica unica lotto 2a) la firma
        #    e' `character varying`: `p_documento` e' ancorato a
        #    `config.sorgenti.codice_interno%TYPE`.
        richiedi_db_provvisto("vendite.fn_doc_indirizzo_default(character varying,bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('indirizzi seguono A')")
            mondo = row_to_dict(cur)
            assert mondo is not None
            cur.execute(
                "SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('indirizzi seguono B', NULL, %s)",
                [mondo["emittente_soggetto_ruolo_id"]],
            )
            cliente_b = row_to_dict(cur)
            assert cliente_b is not None
            cur.execute("SELECT codice_interno, id FROM config.tipi_indirizzi")
            self.tipo: dict[str, int] = dict(cur.fetchall())
        self.mondo: dict[str, Any] = mondo
        self.ruolo_a: int = mondo["cliente_soggetto_ruolo_id"]
        self.ruolo_b: int = cliente_b["soggetto_ruolo_id"]
        self.ba_b: int = cliente_b["billing_account_id"]

    # L'indirizzo di Fatturazione di ruolo, generico, del cliente.
    def _fatt(self, soggetto_ruolo_id: int) -> int:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM anagrafiche.indirizzi
                 WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s
                   AND istanza_utility_id IS NULL
                 ORDER BY id LIMIT 1
                """,
                [soggetto_ruolo_id, self.tipo["FATT"]],
            )
            riga = cur.fetchone()
        assert riga is not None, "il cliente della fixture non ha la Fatturazione di ruolo"
        return int(riga[0])

    def _ddt_del_cliente_a(self) -> int:
        return int(ddt_service.crea_ddt({
            "billing_account_id": self.mondo["billing_account_id"],
            "emittente_fiscale_id": self.mondo["emittente_fiscale_id"],
        })["id"])

    # Gli slot del documento, per codice di tipo: {codice: origine_soggetto_ruolo_id}.
    @staticmethod
    def _slot(ddt_id: int) -> dict[str, Any]:
        righe = ddt_service.list_indirizzi(ddt_id)["indirizzi"]
        return {r["tipo_indirizzo_codice_interno"]: r["origine_soggetto_ruolo_id"] for r in righe}

    def _rifiuto(self, fn: Callable[[], Any]) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, _CODICE, f"{api.message} — {exc!r}")
            self.assertIn("tipo_indirizzo_id", api.fields or (), "campo non acceso")
            self.assertEqual(ErrorTranslator.get_http_status(api), 400)
            return
        self.fail(f"atteso {_CODICE}, accettato")

    # 1. R-BE-1: la creazione chiama il building block, che riempie lo slot CON
    #    dal ripiego FATT del cliente (slot e ripiego sono dati del seed).
    def test_crea_ddt_riempie_lo_slot_di_default_dal_cliente(self) -> None:
        ddt_id = self._ddt_del_cliente_a()
        self.assertEqual(self._slot(ddt_id), {"CON": self.ruolo_a})

    # 2. A slot pieno il building block non scrive, e lo dice (False): la
    #    cascata dalla sorgente e la scelta dell'operatore vincono.
    def test_slot_pieno_il_building_block_non_scrive(self) -> None:
        ddt_id = self._ddt_del_cliente_a()
        self.assertFalse(DdtRepository().riempi_indirizzo_default(ddt_id))
        self.assertEqual(self._slot(ddt_id), {"CON": self.ruolo_a})

    # 3. Il cliente cambia in bozza: la CON di A se ne va, c'e' quella di B.
    #    E' il motivo per cui il FE ricarica il pannello dopo il salvataggio.
    def test_cambio_cliente_in_bozza_lo_slot_segue_il_cliente(self) -> None:
        ddt_id = self._ddt_del_cliente_a()
        ddt_service.aggiorna_ddt(ddt_id, {"billing_account_id": self.ba_b})
        self.assertEqual(self._slot(ddt_id), {"CON": self.ruolo_b})

    # 4. R-BE-2, flusso picker: un indirizzo d'anagrafica di un altro cliente.
    #    Fino al 2026-10-12 lo fermava un `require` Python; ora il guard DB.
    def test_picker_indirizzo_di_un_altro_cliente_rifiutato_col_campo(self) -> None:
        ddt_id = self._ddt_del_cliente_a()
        self._rifiuto(lambda: ddt_service.upsert_indirizzo(ddt_id, {
            "tipo_indirizzo_id": self.tipo["CON"],
            "origine_indirizzo_id": self._fatt(self.ruolo_b),
        }))

    # 5. R-BE-2, flusso «anagrafica soggetto»: il client dichiara un'origine
    #    soggetto che non e' il cliente del documento.
    def test_origine_soggetto_di_un_altro_cliente_rifiutata_col_campo(self) -> None:
        ddt_id = self._ddt_del_cliente_a()
        self._rifiuto(lambda: ddt_service.upsert_indirizzo(ddt_id, {
            "tipo_indirizzo_id": self.tipo["CON"],
            "origine_soggetto_ruolo_id": self.ruolo_b,
            "snapshot": {"via": "Via Altrui 1", "citta": "Altrove"},
        }))

    # 6. Un una-tantum (nessuna origine) e' sempre del documento.
    def test_una_tantum_si_scrive(self) -> None:
        ddt_id = self._ddt_del_cliente_a()
        ddt_service.upsert_indirizzo(ddt_id, {
            "tipo_indirizzo_id": self.tipo["CON"],
            "snapshot": {"via": "Via Terzi 3", "citta": "Consegna"},
        })
        self.assertEqual(self._slot(ddt_id), {"CON": None})
