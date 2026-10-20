# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il runner dei test del progetto. Legge il fuso dell'azienda prima
#        della suite (vedi `setup_test_environment`). Spegne `ERROR_LOG_DB_ENABLED`,
#        cioe' impedisce alla suite di scrivere nel diario tecnico
#        `dbops.error_log`, il redirect HTTPS (`SECURE_SSL_REDIRECT`), che
#        manderebbe in 301 il client di test, e l'idempotenza forte, che
#        farebbe interrogare il DB a ogni POST. Lo stesso ambiente lo prepara
#        in ogni worker di `--parallel` (`_init_worker_zeroerp`).
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
from django.db import connection
from django.test.runner import DiscoverRunner, ParallelTestSuite

from apps.core.services.fuso_aziendale import fuso_aziendale


# Scopo: L'ambiente di progetto della suite, in un punto solo: lo chiama il
#        runner nel processo principale e `_init_worker_zeroerp` in ogni
#        worker di `--parallel`.
def _prepara_ambiente_test() -> None:
    settings.ERROR_LOG_DB_ENABLED = False
    # Il client di test parla HTTP per costruzione: col redirect HTTPS
    # acceso (default fuori da DEBUG) ogni richiesta sarebbe un 301. Stessa
    # ragione del diario: dal runner vale ovunque, senza configurare
    # niente. Chi prova il redirect lo riaccende con `override_settings`
    # (`apps/core/tests/api/test_https_header.py`).
    settings.SECURE_SSL_REDIRECT = False
    # Stessa natura: l'idempotenza forte (`DJANGO_API_STRONG_IDEMPOTENCY_ENABLED`,
    # accesa da `env.sh` e spenta da `.env.systemd` e in CI) fa scrivere a ogni
    # POST con `Idempotency-Key` in `dbops.idempotency_keys`, cioe' una query
    # dentro un `SimpleTestCase`: la suite cambiava esito secondo il file
    # d'ambiente caricato. Chi la prova la riaccende con `override_settings`
    # (`apps/vendite/tests/api/test_pipeline_api.py`).
    settings.API_STRONG_IDEMPOTENCY_ENABLED = False
    # Il fuso dell'azienda si legge QUI, una volta, dal database configurato
    # (BB `fuso_aziendale`, cache di processo). Dentro un `SimpleTestCase`
    # la prima lettura sarebbe un `DatabaseOperationForbidden`: il
    # middleware e ogni formattatore lo chiedono. Il valore e' quello vero
    # del parametro, cosi' l'«oggi» di Python e `fn_data_operativa()` dei
    # test sul DB vero coincidono. ⛔ Nessun ripiego: senza database la
    # suite si ferma qui, con il motivo. Un test che asserisce un'ora o un
    # giorno dichiara il proprio fuso con `fuso_aziendale_forzato`.
    fuso_aziendale()
    # ⚠️ E si richiude la connessione: la suite parte come prima, senza
    #    connessione aperta. I middleware che azzerano lo stato di una
    #    connessione RIUSATA (`JwtAuditMiddleware`) si accendono solo se ce
    #    n'e' una, e dentro un `SimpleTestCase` toccarla e' vietato.
    connection.close()


# Scopo: Inizializzazione di un worker di `--parallel`: quella di Django, poi
#        l'ambiente di progetto.
# ⛔ Senza, col metodo di avvio `forkserver` (il default di Python 3.14 su
#    Linux) o `spawn`, il worker rifa' `django.setup()` e il
#    `setup_test_environment` generico di Django, non quello del runner: il
#    redirect torna acceso (ogni richiesta del client e' un 301), il diario
#    `dbops.error_log` torna aperto ai test, e il fuso non e' in cache. Con
#    `fork` il worker eredita tutto e la chiamata e' innocua. Funzione di
#    modulo: il worker la riceve per nome.
def _init_worker_zeroerp(counter, *args, **kwargs) -> None:
    _INIT_WORKER_DJANGO(counter, *args, **kwargs)
    _prepara_ambiente_test()


# L'inizializzazione di Django, presa dalla classe e non per nome: la
# funzione di modulo e' privata, l'attributo e' il punto di estensione.
_INIT_WORKER_DJANGO = ParallelTestSuite.init_worker


class ZeroErpParallelTestSuite(ParallelTestSuite):
    init_worker = _init_worker_zeroerp


class ZeroErpTestRunner(DiscoverRunner):
    """Runner di progetto: chiude il diario `dbops.error_log` alla suite."""

    parallel_test_suite = ZeroErpParallelTestSuite

    # Scopo: hook standard di Django, chiamato una volta prima di tutti i test.
    #        Prepara l'ambiente di progetto (`_prepara_ambiente_test`).
    def setup_test_environment(self, **kwargs) -> None:
        super().setup_test_environment(**kwargs)
        _prepara_ambiente_test()
