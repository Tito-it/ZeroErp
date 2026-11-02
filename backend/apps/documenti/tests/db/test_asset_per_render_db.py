# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `DocumentiRepository.get_asset_per_render` sul DATABASE VERO: la
#        query con cui il render risolve `asset:<codice_interno>`
#        (brief-be-documenti-risorse-esterne-render-pdf). Perimetro
#        `(emittente, codice_interno)`, e il filtro «attivo e valido oggi»
#        letto dalla colonna generata `validita`, acceso o spento.
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, l'asset lo crea il test, e i
#       casi «disattivato» e «scaduto» si fabbricano sulla riga, non si
#       cercano fra quelle che ci sono. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) AssetPerRenderDbTests.test_perimetro_emittente_e_codice_interno
   l'asset si trova per (emittente, codice_interno); non per il `codice`
   (etichetta), non con un altro emittente.
2) AssetPerRenderDbTests.test_disattivato_visto_solo_dalla_ristampa
   `attivo = false`: invisibile con `solo_validi`, visibile senza.
3) AssetPerRenderDbTests.test_scaduto_visto_solo_dalla_ristampa
   `valido_al` ieri: invisibile con `solo_validi`, visibile senza.
   In 1-3 il filtro `utilizzabili` della lista (quello dell'editor dei
   template) dice la STESSA cosa del render: e' la prova che le due letture
   non divergono.
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)


class AssetPerRenderDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    # Scopo: crea un asset attivo e valido oggi, con `codice` diverso da
    #        `codice_interno`; torna il suo id.
    def _crea_asset(self, cur, repo, emittente: int, impronta: str) -> int:
        cur.execute("SELECT id FROM documenti.tipi_asset_documento WHERE attivo ORDER BY id LIMIT 1")
        asset_tipo = cur.fetchone()[0]
        return repo.create_asset({
            "codice": "LOGO_ETICHETTA",
            "codice_interno": "RENDERLOGO",
            "descrizione": "Logo per il render",
            "asset_tipo_id": asset_tipo,
            "mime_type": "image/png",
            "file_name": "logo.png",
            "file_size_bytes": 10,
            "storage_key": f"assets/{emittente}/{impronta}.png",
            "sha256": impronta,
            "emittente_fiscale_id": emittente,
            "attivo": True,
        })

    # Scopo: costruisce il mondo e l'asset dell'emittente dell'operatore;
    #        torna (repo, emittente, id).
    def _asset(self, cur):
        from apps.documenti.db.documenti_repository import DocumentiRepository

        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT emittente_fiscale_id FROM _mondo")
        emittente = cur.fetchone()[0]
        repo = DocumentiRepository()
        return repo, emittente, self._crea_asset(cur, repo, emittente, "b" * 64)

    # Scopo: la lista con `utilizzabili` deve vedere l'asset esattamente quando
    #        lo vede il render con `solo_validi=True`.
    def _lista_concorda_col_render(self, repo, emittente, asset_id):
        visto_dal_render = repo.get_asset_per_render(
            emittente, "RENDERLOGO", solo_validi=True,
        ) is not None
        for utilizzabili, atteso in ((True, visto_dal_render), (False, not visto_dal_render)):
            righe, _ = repo.list_asset(
                attivo=None, asset_tipo_id=None, emittente_fiscale_id=emittente,
                search=None, emittente_ids_scope=None, utilizzabili=utilizzabili,
                order_by="codice", order_dir="asc", limit=50, offset=0,
            )
            self.assertEqual(
                asset_id in [r["id"] for r in righe], atteso,
                f"utilizzabili={utilizzabili}",
            )

    # 1. La chiave e' (emittente, codice_interno): il `codice` e' un'etichetta
    #    modificabile e non regge il riferimento. Un SECONDO emittente con lo
    #    stesso `codice_interno` esiste davvero: ognuno vede il proprio.
    def test_perimetro_emittente_e_codice_interno(self):
        with connection.cursor() as cur:
            repo, emittente, asset_id = self._asset(cur)

            riga = repo.get_asset_per_render(emittente, "RENDERLOGO", solo_validi=True)
            self.assertIsNotNone(riga)
            self.assertEqual(riga["id"], asset_id)
            self.assertEqual(riga["storage_key"], f"assets/{emittente}/{'b' * 64}.png")
            self.assertEqual(riga["mime_type"], "image/png")
            self.assertEqual(riga["sha256"], "b" * 64)

            self.assertIsNone(
                repo.get_asset_per_render(emittente, "LOGO_ETICHETTA", solo_validi=True),
            )

            cur.execute("SELECT emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente()")
            altro_emittente = cur.fetchone()[0]
            altro_asset_id = self._crea_asset(cur, repo, altro_emittente, "c" * 64)
            self.assertEqual(
                repo.get_asset_per_render(emittente, "RENDERLOGO", solo_validi=False)["id"],
                asset_id,
            )
            self.assertEqual(
                repo.get_asset_per_render(altro_emittente, "RENDERLOGO", solo_validi=False)["id"],
                altro_asset_id,
            )
            self._lista_concorda_col_render(repo, emittente, asset_id)

    # 2. Disattivato: la generazione non lo vede, la ristampa si'.
    def test_disattivato_visto_solo_dalla_ristampa(self):
        with connection.cursor() as cur:
            repo, emittente, asset_id = self._asset(cur)
            cur.execute(
                "UPDATE documenti.template_asset SET attivo = false WHERE id = %s",
                [asset_id],
            )
            self.assertIsNone(
                repo.get_asset_per_render(emittente, "RENDERLOGO", solo_validi=True),
            )
            riga = repo.get_asset_per_render(emittente, "RENDERLOGO", solo_validi=False)
            self.assertEqual(riga["id"], asset_id)
            self._lista_concorda_col_render(repo, emittente, asset_id)

    # 3. Scaduto ieri: la validita' si legge da `validita`, colonna generata.
    def test_scaduto_visto_solo_dalla_ristampa(self):
        with connection.cursor() as cur:
            repo, emittente, asset_id = self._asset(cur)
            cur.execute(
                "UPDATE documenti.template_asset "
                "SET valido_dal = script.fn_data_operativa() - 10, valido_al = script.fn_data_operativa() - 1 "
                "WHERE id = %s",
                [asset_id],
            )
            self.assertIsNone(
                repo.get_asset_per_render(emittente, "RENDERLOGO", solo_validi=True),
            )
            riga = repo.get_asset_per_render(emittente, "RENDERLOGO", solo_validi=False)
            self.assertEqual(riga["id"], asset_id)
            self._lista_concorda_col_render(repo, emittente, asset_id)
