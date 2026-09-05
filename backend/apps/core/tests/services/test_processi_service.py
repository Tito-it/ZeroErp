# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test di `ProcessiService` — la facade del registro dei processi
#        automatici. Repository MOCKATO: qui si prova cio' che il service
#        decide, non cio' che il database contiene.
#
# ⚠️ `unittest.TestCase`, non `django.test.TestCase`: senza database, come
#    prescrive AGENTS.md. Le letture vere sono provate altrove (la schermata e
#    i due comandi girano sul DB di sviluppo).
#
# Indice test:
#   1) un filtro fuori vocabolario è un 400 parlante, non una lista vuota
#   2) il `limit` è tagliato al cap di progetto e non scende sotto 1
#   3) `offset` negativo non diventa un OFFSET negativo (SQL lo rifiuterebbe)
#   4) processo inesistente → errore, non `None` che il chiamante deve indovinare
#   5) il dettaglio porta le aziende NON servite: è il numero che rompe il
#      silenzio della D-9
#   6) `con_righe` conta i presidi accesi, non le righe
#   7) ⛔ la natura di un presidio NON è decisa qui: la descrizione arriva dal DB
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from apps.core.db._helpers import LIST_MAX_LIMIT
from apps.core.services.processi_service import ProcessiService
from apps.core.services.service_errors import ServiceError


def _service(**metodi):
    repo = MagicMock()
    repo.list_processi.return_value = ([], 0)
    repo.list_run_processo.return_value = ([], 0)
    repo.emittenti_non_serviti.return_value = []
    repo.stato_presidi.return_value = []
    for nome, valore in metodi.items():
        getattr(repo, nome).return_value = valore
    return ProcessiService(repo=repo), repo


class ProcessiServiceFiltriTests(unittest.TestCase):
    # 1. Un filtro che non esiste deve FALLIRE, non consegnare zero righe: una
    #    lista vuota si legge come «non c'è niente», che è un'altra cosa.
    def test_filtro_fuori_vocabolario_solleva(self):
        svc, repo = _service()
        for campo, valore in (("classe", "PIPPO"), ("canale", "SMTP")):
            with self.subTest(campo=campo):
                with self.assertRaises(ServiceError) as ctx:
                    svc.list_processi(**{campo: valore})
                self.assertEqual(ctx.exception.code, "E_CORE_VALIDATION")
        repo.list_processi.assert_not_called()

    def test_filtri_validi_arrivano_al_repository(self):
        svc, repo = _service()
        svc.list_processi(classe="DOMINIO", canale="COMMAND", attivo=True)
        kwargs = repo.list_processi.call_args.kwargs
        self.assertEqual(kwargs["classe"], "DOMINIO")
        self.assertEqual(kwargs["canale"], "COMMAND")
        self.assertIs(kwargs["attivo"], True)

    # 2-3. Il cap e il pavimento: un `limit` enorme non diventa una query che
    #      porta via il database, e un `offset` negativo non arriva all'SQL.
    def test_limit_e_offset_normalizzati(self):
        svc, repo = _service()
        svc.list_processi(limit=100_000, offset=-5)
        kwargs = repo.list_processi.call_args.kwargs
        self.assertEqual(kwargs["limit"], LIST_MAX_LIMIT)
        self.assertEqual(kwargs["offset"], 0)

        svc.list_processi(limit=0)
        self.assertEqual(repo.list_processi.call_args.kwargs["limit"], 1)


class ProcessiServiceDettaglioTests(unittest.TestCase):
    # 4. Il repository risponde `None` per «non trovato» (idioma dei lookup):
    #    il service lo trasforma in un errore, così il chiamante non deve
    #    indovinare se il `None` è «non c'è» o «non ho guardato».
    def test_processo_inesistente_solleva(self):
        svc, _repo = _service(get_processo=None)
        with self.assertRaises(ServiceError):
            svc.get_processo("non_esiste")

    # 5. ⭐ Le aziende scoperte viaggiano COL dettaglio. Senza, «due identità»
    #    si legge come «tutto a posto» anche quando la terza azienda non viene
    #    servita e il suo lavoro non parte — il guasto silenzioso della D-9.
    def test_dettaglio_porta_le_aziende_non_servite(self):
        svc, repo = _service(
            get_processo={"codice": "x", "bersagli": [], "identita": []},
        )
        repo.emittenti_non_serviti.return_value = [
            {"emittente_fiscale_id": 3, "emittente_codice": "ACME"},
        ]
        dettaglio = svc.get_processo("x")
        self.assertEqual(
            [e["emittente_codice"] for e in dettaglio["emittenti_non_serviti"]],
            ["ACME"],
        )


class ProcessiServicePresidiTests(unittest.TestCase):
    # 6. `con_righe` conta i PRESIDI accesi, non le righe: è il numero che si
    #    guarda per primo, e sommare le righe direbbe un'altra cosa.
    def test_con_righe_conta_i_presidi_non_le_righe(self):
        svc, _repo = _service(stato_presidi=[
            {"vista": "a", "conteggio": 0, "righe": [], "descrizione": "d"},
            {"vista": "b", "conteggio": 7, "righe": [{}], "descrizione": "d"},
            {"vista": "c", "conteggio": 2, "righe": [{}], "descrizione": "d"},
        ])
        self.assertEqual(svc.stato_presidi()["con_righe"], 2)

    # 7. ⛔ Il service NON classifica i presidi. La differenza fra «deve restare
    #    vuota» e «registro di debito che deve calare» la dichiara il database
    #    nel commento della vista, e passa di qui intatta: un elenco di nature
    #    scritto nel backend sarebbe la seconda sede della stessa decisione.
    def test_la_natura_del_presidio_arriva_dal_database(self):
        svc, _repo = _service(stato_presidi=[
            {"vista": "a", "conteggio": 1, "righe": [{}],
             "descrizione": "E' un registro di DEBITO: deve CALARE."},
        ])
        presidio = svc.stato_presidi()["presidi"][0]
        self.assertIn("DEBITO", presidio["descrizione"])
