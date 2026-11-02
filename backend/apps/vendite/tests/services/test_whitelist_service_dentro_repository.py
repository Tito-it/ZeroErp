# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della coppia di whitelist di ogni UPDATE dei documenti di
#        vendita: le chiavi che il SERVICE fa arrivare al repository devono
#        stare tutte nelle colonne che il REPOSITORY sa scrivere.
# Note: ⭐ Due insiemi, due domande, ed e' voluto (2026-09-26): il service dice
#       cosa l'OPERATORE puo' mandare, il repository cosa il METODO scrive. Non
#       sono la stessa cosa — il caso dei componenti lo prova: il repository
#       scrive anche `stato_approvazione_prezzo`, che l'operatore non deve
#       poter mandare. Per questo non c'e' una sede unica ma un'INCLUSIONE.
#       ⛔ Senza questo test la divergenza si vedeva solo a runtime: la
#       whitelist rigida del BB `execute_dynamic_update` solleva
#       `RuntimeError` (500) alla prima PATCH che porta la chiave nuova.
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_whitelist_service_dentro_repository   (un subTest per coppia)
1. test_whitelist_create_dentro_repository    (INSERT di contratti/offerte)
"""

from __future__ import annotations

from unittest import TestCase

from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.db.resi_repository import ResiRepository
from apps.vendite.services import (
    contratti_service,
    ddt_service,
    offerte_service,
    ordini_service,
    preventivi_service,
    resi_service,
)
from apps.vendite.services.approvazioni_prezzo_service import CAMPI_RIGA_WORKFLOW_L3


class WhitelistServiceDentroRepositoryTests(TestCase):

    # 0. Per ogni UPDATE: chiavi del service (+ quelle che il service deriva,
    #    + il workflow L3 sulle righe che lo conoscono) ⊆ colonne del repository.
    def test_whitelist_service_dentro_repository(self) -> None:
        coppie = {
            "ddt testata": (ddt_service.UPDATE_KEYS_DDT, DdtRepository.TESTATA_UPDATE_COLUMNS),
            "ddt riga": (ddt_service.UPDATE_KEYS_RIGA, DdtRepository.RIGA_UPDATE_COLUMNS),
            "ordini testata": (
                ordini_service.UPDATE_KEYS_ORDINE, OrdiniRepository.TESTATA_UPDATE_COLUMNS,
            ),
            "ordini riga": (ordini_service.UPDATE_KEYS_RIGA, OrdiniRepository.RIGA_UPDATE_COLUMNS),
            "resi testata": (resi_service.UPDATE_KEYS_RESO, ResiRepository.TESTATA_UPDATE_COLUMNS),
            "resi riga": (resi_service.UPDATE_KEYS_RIGA, ResiRepository.RIGA_UPDATE_COLUMNS),
            "preventivi testata": (
                preventivi_service.UPDATE_KEYS_PREVENTIVO,
                PreventiviRepository.TESTATA_UPDATE_COLUMNS,
            ),
            # La data di consegna il service la aggiunge a parte (normalizzata
            # da `_data_consegna_da_payload`); i campi L3 li scrive il workflow.
            "preventivi riga": (
                preventivi_service.UPDATE_KEYS_RIGA
                | {preventivi_service._CHIAVE_DATA_CONSEGNA}
                | CAMPI_RIGA_WORKFLOW_L3,
                PreventiviRepository.RIGA_UPDATE_COLUMNS,
            ),
            # Contratti e offerte (2026-09-26, migrazione sul BB). Le chiavi che
            # il service CONSUMA prima del repository non ci arrivano e si
            # tolgono: `richiesta_approvazione` (flag del gate L3) e il
            # sotto-oggetto `utility` (va alla sua tabella). Sulle righe i
            # campi L3 li scrive il workflow approvazioni.
            "contratti testata": (
                contratti_service.UPDATE_KEYS_TESTATA,
                ContrattiRepository.TESTATA_UPDATE_COLUMNS,
            ),
            "contratti riga": (
                (contratti_service.UPDATE_KEYS_RIGA - {"richiesta_approvazione"})
                | CAMPI_RIGA_WORKFLOW_L3,
                ContrattiRepository.RIGA_UPDATE_COLUMNS,
            ),
            "contratti utility": (
                contratti_service.UTILITY_UPDATE_KEYS,
                ContrattiRepository.UTILITY_UPDATE_COLUMNS,
            ),
            "offerte testata": (
                offerte_service.UPDATE_KEYS_OFFERTA - {"utility"},
                OfferteRepository.TESTATA_UPDATE_COLUMNS,
            ),
            "offerte eccezione": (
                (offerte_service.UPDATE_KEYS_ECCEZIONE - {"richiesta_approvazione"})
                | CAMPI_RIGA_WORKFLOW_L3,
                OfferteRepository.ECCEZIONE_UPDATE_COLUMNS,
            ),
            "offerte utility": (
                offerte_service.UPDATE_KEYS_UTILITY,
                OfferteRepository.UTILITY_UPDATE_COLUMNS,
            ),
        }
        for nome, (service, repository) in coppie.items():
            with self.subTest(update=nome):
                self.assertEqual(
                    set(), set(service) - set(repository),
                    f"{nome}: chiavi che il service manda e il repository non sa scrivere",
                )

    # 1. Stessa domanda per gli INSERT dinamici di contratti e offerte (sul BB
    #    `execute_dynamic_insert` dal 2026-09-26, whitelist rigida anche li').
    #    Si tolgono le chiavi che il service consuma (`componenti_overrides`,
    #    `richiesta_approvazione`, `utility`) e si aggiungono quelle che deriva
    #    (gli id utility dalla testata, i campi del gate L3). Lo stato no: lo
    #    mette il DB alla nascita (brief-modello-documento-vendita P-2).
    def test_whitelist_create_dentro_repository(self) -> None:
        consumate = {"componenti_overrides", "richiesta_approvazione", "utility"}
        coppie = {
            "contratti riga": (
                (contratti_service.CREATE_KEYS_RIGA - consumate) | CAMPI_RIGA_WORKFLOW_L3,
                ContrattiRepository.RIGA_CREATE_COLUMNS,
            ),
            "contratti utility": (
                contratti_service.UTILITY_CREATE_KEYS | {"istanza_utility_id", "utility_id"},
                ContrattiRepository.UTILITY_CREATE_COLUMNS,
            ),
            "offerte testata": (
                offerte_service.CREATE_KEYS_OFFERTA - consumate,
                OfferteRepository.TESTATA_CREATE_COLUMNS,
            ),
            "offerte eccezione": (
                (offerte_service.CREATE_KEYS_ECCEZIONE - consumate) | CAMPI_RIGA_WORKFLOW_L3,
                OfferteRepository.ECCEZIONE_CREATE_COLUMNS,
            ),
            "offerte utility": (
                offerte_service.CREATE_KEYS_UTILITY,
                OfferteRepository.UTILITY_CREATE_COLUMNS,
            ),
        }
        for nome, (service, repository) in coppie.items():
            with self.subTest(create=nome):
                self.assertEqual(
                    set(), set(service) - set(repository),
                    f"{nome}: chiavi che il service manda e il repository non sa scrivere",
                )
