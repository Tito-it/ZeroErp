# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: i due rifiuti dell'articolo che il giro 3 di brief-db-revisione-catalogo
#        (2026-11-10) ha cambiato di forma, provati sul database vero fino alla
#        risposta che riceve il client (codice, status e campo da accendere).
#        BE20: `E_BOM_IVA_DISCORDANTE` arriva a FINE TRANSAZIONE (constraint
#        trigger differito, D4 + D21). BE4: `E_PARAMETRO_INVALIDO` della
#        correzione di struttura porta il `campo` (D19).
# Note: ⭐ Perche' un vincolo differito vuole un test suo. In produzione il
#       rifiuto esce all'uscita del `transaction.atomic()` di
#       `fn_update_articolo` (il COMMIT), FUORI dal `try` che traduce
#       l'IntegrityError: lo rende il traduttore generale (`ErrorTranslator`,
#       via middleware). Qui la transazione del test non fa mai COMMIT, quindi
#       il giudizio si chiede con `SET CONSTRAINTS … IMMEDIATE`, la stessa
#       strada del pgTAP `catalogo/test-iva-kit-a-fine-transazione-v1`.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ErroriArticoloGiro3DbTests.test_iva_kit_rifiutata_a_fine_transazione
2) ErroriArticoloGiro3DbTests.test_iva_kit_e_componente_insieme_passa
3) ErroriArticoloGiro3DbTests.test_correzione_struttura_valore_vuoto_accende_la_colonna
"""
from __future__ import annotations

import unittest
from uuid import uuid4

from django.db import DatabaseError, connection, transaction

from apps.catalogo.db.catalogo_repository import CatalogoRepository
from apps.catalogo.services.catalogo_service import fn_update_articolo
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

_VINCOLO_IVA = "catalogo.trg_articoli_a10_guard_iva_bom_attiva_upd"


class ErroriArticoloGiro3DbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("catalogo.fn_articolo_flag_etichetta(text)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.sfx = uuid4().hex[:6].upper()

    # Scopo: due aliquote IVA diverse. Sono dati di riferimento del seed
    #        (`config.iva`), non una popolazione: senza due aliquote il caso non
    #        si costruisce, e il test lo dichiara.
    def _due_aliquote(self, cur) -> tuple[int, int]:
        cur.execute(
            "SELECT id FROM config.iva WHERE attivo AND aliquota_iva > 0 ORDER BY id LIMIT 2"
        )
        righe = [r[0] for r in cur.fetchall()]
        if len(righe) < 2:
            raise unittest.SkipTest("servono due aliquote IVA attive in config.iva")
        return righe[0], righe[1]

    # Scopo: un kit e un suo componente, con la stessa IVA, legati da oggi.
    def _kit_e_componente(self, cur, iva: int) -> tuple[str, str]:
        ids = []
        for sigla, composito in (("K", True), ("C", False)):
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, p_is_composito => %s)::text",
                [f"PYIVK-{sigla}-{self.sfx}", composito],
            )
            ids.append(cur.fetchone()[0])
        cur.execute("UPDATE catalogo.articoli SET iva_id = %s WHERE id = ANY(%s::uuid[])", [iva, ids])
        cur.execute(
            "INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)"
            " VALUES (%s, %s, 1, script.fn_data_operativa())",
            ids,
        )
        return ids[0], ids[1]

    # 1. Il PATCH cambia l'IVA del solo kit: l'UPDATE passa, il rifiuto arriva
    #    al giudizio del vincolo, e il client riceve codice e campo `iva_id`.
    def test_iva_kit_rifiutata_a_fine_transazione(self) -> None:
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            iva_a, iva_b = self._due_aliquote(cur)
            kit, _ = self._kit_e_componente(cur, iva_a)
            cur.execute(f"SET CONSTRAINTS {_VINCOLO_IVA} DEFERRED")

            fn_update_articolo(kit, {"iva_id": iva_b})

            with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                cur.execute(f"SET CONSTRAINTS {_VINCOLO_IVA} IMMEDIATE")
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(errore.code, "E_BOM_IVA_DISCORDANTE")
        self.assertEqual(ErrorTranslator.get_http_status(errore), 400)
        self.assertEqual(errore.fields, ("iva_id",))

    # 2. Kit e componente cambiano IVA in due PATCH della stessa transazione:
    #    al giudizio coincidono, e passa. E' cio' che il vincolo differito
    #    rende possibile, e che prima il guard per istruzione rifiutava.
    def test_iva_kit_e_componente_insieme_passa(self) -> None:
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            iva_a, iva_b = self._due_aliquote(cur)
            kit, componente = self._kit_e_componente(cur, iva_a)
            cur.execute(f"SET CONSTRAINTS {_VINCOLO_IVA} DEFERRED")

            fn_update_articolo(kit, {"iva_id": iva_b})
            fn_update_articolo(componente, {"iva_id": iva_b})

            cur.execute(f"SET CONSTRAINTS {_VINCOLO_IVA} IMMEDIATE")

    # 3. BE4: un valore vuoto su una colonna strutturale NOT NULL lo rifiuta il
    #    verbo, e il campo da accendere e' la colonna, non `p_campi`.
    def test_correzione_struttura_valore_vuoto_accende_la_colonna(self) -> None:
        with connection.cursor() as cur:
            apri_contesto_operatore(cur, super_admin=True)
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s)::text", [f"PYSTR3-{self.sfx}"],
            )
            articolo = cur.fetchone()[0]
            with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                CatalogoRepository().correggi_struttura_articolo(articolo, {"requires_lotto": None})
        errore = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(errore.code, "E_PARAMETRO_INVALIDO")
        self.assertEqual(errore.fields, ("requires_lotto",))
