# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il runner dei test del progetto. Oggi fa una cosa sola: spegne
#        `ERROR_LOG_DB_ENABLED`, cioe' impedisce alla suite di scrivere nel
#        diario tecnico `dbops.error_log`.
#
#        PERCHE' SERVE, e perche' e' un recinto e non una preferenza.
#        I test di questa suite girano contro il DATABASE CONFIGURATO VERO:
#        nessun test dichiara un database, quindi Django non ne crea uno
#        usa-e-getta e la connessione resta quella di sviluppo (e' scritto anche
#        nel commento dello step «Django tests» di `ci-validate.yaml`). Un test
#        che esercita un service con `log_to_db=True` sostituisce il repository
#        con un mock, ma NON il logger: la riga finisce nel diario davvero, con
#        `area='backend'`, indistinguibile da un errore accaduto a un utente.
#
#        Il 2026-08-19 questo e' costato una diagnosi sbagliata: il team DB ha
#        letto 587 occorrenze di un codice che il database non puo' piu'
#        sollevare e ne ha dedotto un difetto del pricing. Erano le 587
#        esecuzioni di `test_pricing_service.py`
#        (work-in-progress/brief-be-pricing-codice-errore-fantasma.md §10).
#        Sullo stesso DB ci sono ~19.800 righe di `pricing_service` con contesti
#        come `uuid-art-1` o `cmp-X`: il diario e' una fonte su cui si prendono
#        decisioni, e non aveva un recinto fra test e produzione.
#
#        ⚠️ PERCHE' QUI E NON IN UNA VARIABILE D'AMBIENTE. Il precedente in casa
#        (`REQUEST_LOG_ENABLED`, spento in CI da `ci-validate.yaml`) protegge la
#        CI ma non chi lancia i test in locale — che e' esattamente chi ha
#        sporcato il diario per un mese. Spegnere dal runner e' l'unico modo che
#        non si puo' dimenticare: vale per `manage.py test`, per
#        `manage-test.sh`, per la CI e per l'IDE, senza che nessuno configuri
#        niente.
#
#        Un test che volesse verificare proprio la scrittura sul diario la
#        riaccende per se' con `@override_settings(ERROR_LOG_DB_ENABLED=True)` —
#        e a quel punto lo sta facendo apposta, che e' il punto.
# ------------------------------------------------------------

from __future__ import annotations

from django.conf import settings
from django.test.runner import DiscoverRunner


class ZeroErpTestRunner(DiscoverRunner):
    """Runner di progetto: chiude il diario `dbops.error_log` alla suite."""

    # Scopo: hook standard di Django, chiamato una volta prima di tutti i test.
    #        Spegne il logging su DB per l'intera esecuzione.
    def setup_test_environment(self, **kwargs) -> None:
        super().setup_test_environment(**kwargs)
        settings.ERROR_LOG_DB_ENABLED = False
