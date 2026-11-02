# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del building block `prezzo_riga_commessa` (L0 di
#        piano-be-type-checker §4): cosa si chiede al resolver per una riga di
#        commessa e cosa se ne scrive. Funzioni pure, nessun database.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) ArgomentiResolverTests.test_riga_completa
2) ArgomentiResolverTests.test_senza_data_attivita_ripiega_sulla_competenza
3) ArgomentiResolverTests.test_un_dato_mancante_da_none
4) ProvenienzaTests.test_da_resolver_ha_le_colonne_del_repository
5) ProvenienzaTests.test_origine_fuori_check_diventa_none
6) ProvenienzaTests.test_manuale
"""
from __future__ import annotations

from datetime import date
from typing import Any
from unittest import TestCase

from apps.vendite.db.commesse_repository import COLONNE_PROVENIENZA_PREZZO
from apps.vendite.services.prezzo_riga_commessa import (
    argomenti_resolver,
    provenienza_da_resolver,
    provenienza_manuale,
)

_RIGA: dict[str, Any] = {
    "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
    "uom_id": 1,
    "data_attivita": date(2026, 4, 3),
    "competenza_mese": date(2026, 4, 1),
    "billing_account_id": 7,
    "utility_id": 3,
    "emittente_soggetto_ruolo_id": 11,
    "meta": {"componente_di": "019bbee2-0000-7000-8000-00000000aaaa"},
}


class ArgomentiResolverTests(TestCase):
    # 1. Tutto c'e': la data e' quella dell'attivita', il kit e' il padre in meta.
    def test_riga_completa(self):
        self.assertEqual(
            argomenti_resolver(**_RIGA),
            {
                "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                "uom_id": 1,
                "data_riferimento": date(2026, 4, 3),
                "ba_id": 7,
                "utility_id": 3,
                "emittente_soggetto_ruolo_id": 11,
                "articolo_padre_contesto": "019bbee2-0000-7000-8000-00000000aaaa",
            },
        )

    # 2. Senza data dell'attivita' la data e' la competenza; senza meta, nessun kit.
    def test_senza_data_attivita_ripiega_sulla_competenza(self):
        argomenti = argomenti_resolver(**{**_RIGA, "data_attivita": None, "meta": None})
        assert argomenti is not None
        self.assertEqual(argomenti["data_riferimento"], date(2026, 4, 1))
        self.assertIsNone(argomenti["articolo_padre_contesto"])

    # 3. Ognuno dei dati che il listino chiede, se manca, toglie la domanda.
    def test_un_dato_mancante_da_none(self):
        for campo in (
            "articolo_id", "uom_id", "billing_account_id", "utility_id",
            "emittente_soggetto_ruolo_id",
        ):
            with self.subTest(campo=campo):
                self.assertIsNone(argomenti_resolver(**{**_RIGA, campo: None}))
        self.assertIsNone(
            argomenti_resolver(**{**_RIGA, "data_attivita": None, "competenza_mese": None})
        )


class ProvenienzaTests(TestCase):
    # 4. La provenienza ha esattamente le colonne che il repository scrive:
    #    `update_attivita_prezzo` rifiuta un insieme diverso.
    def test_da_resolver_ha_le_colonne_del_repository(self):
        provenienza = provenienza_da_resolver({
            "prezzo_finale": 46, "origine": "CATEGORIA", "listino_versione_id": 101,
            "listino_riga_id": 301,
        })
        self.assertEqual(set(provenienza), set(COLONNE_PROVENIENZA_PREZZO))
        self.assertEqual(provenienza["origine_prezzo"], "CATEGORIA")
        self.assertEqual(provenienza["listino_versione_id"], 101)
        # ⭐ 2026-10-09: anche la riga di listino, che la rende «propagata».
        self.assertEqual(provenienza["listino_riga_id"], 301)

    # 5. L'origine dello stadio kit non e' fra quelle che il CHECK ammette.
    def test_origine_fuori_check_diventa_none(self):
        self.assertIsNone(provenienza_da_resolver({"origine": "LISTINO_BUNDLE"})["origine_prezzo"])

    # 6. Il prezzo a mano: origine MANUALE, nient'altro.
    def test_manuale(self):
        provenienza = provenienza_manuale()
        self.assertEqual(set(provenienza), set(COLONNE_PROVENIENZA_PREZZO))
        self.assertEqual(provenienza["origine_prezzo"], "MANUALE")
        self.assertEqual(
            [k for k, v in provenienza.items() if v is not None], ["origine_prezzo"],
        )
