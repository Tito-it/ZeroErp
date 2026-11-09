# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#   8) «processo non trovato» è un 404 vero, non più il ripiego dichiarato
#   9) `CODA_AUTOMATICA` è un filtro legittimo: ometterlo darebbe 400 sul buono
#  10) i due verbi dell'utente tecnico pretendono entrambi gli argomenti
#  11) un presidio NON LETTO si conta a parte: `non_letti`, non `con_righe`
#  12) la testata del pallino e quella del pannello sono UNA funzione: stesso
#      elenco → stessi numeri, e la lettura leggera passa `con_righe=False`
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from apps.core.api.constants import MAX_LIMIT
from apps.core.services.processi_service import ProcessiService
from apps.core.services.service_errors import ServiceError


def _service(**metodi):
    repo = MagicMock()
    repo.list_processi.return_value = ([], 0)
    repo.list_run_processo.return_value = ([], 0)
    repo.emittenti_non_serviti.return_value = []
    # ⭐ Dal 2026-09-10 i presidi hanno un repository LORO: il pannello legge il
    #    catalogo `dbops.presidi`, non piu' una tupla di nomi nel repository dei
    #    processi. Qui restano due doppi, uno per lettore.
    presidi = MagicMock()
    presidi.stato_presidi.return_value = []
    for nome, valore in metodi.items():
        bersaglio = presidi if nome == "stato_presidi" else repo
        getattr(bersaglio, nome).return_value = valore
    return ProcessiService(repo=repo, presidi=presidi), repo


class ProcessiServiceVocabolarioTests(unittest.TestCase):
    # 8. ⭐ Il ripiego dichiarato e' rientrato: dal 2026-09-05 (DB-8) il codice
    #    esiste a catalogo con classe NON_TROVATO, quindi l'endpoint risponde
    #    404. ⛔ Il test guarda la COSTANTE e non il valore letterale sparso: se
    #    qualcuno rimettesse un codice di validazione, un «non esiste» tornerebbe
    #    a presentarsi come «hai sbagliato a scrivere».
    def test_il_codice_di_non_trovato_e_quello_di_dominio(self):
        from apps.core.services import processi_service

        self.assertEqual(processi_service.E_NOT_FOUND, "E_PROCESSO_NON_TROVATO")
        self.assertNotEqual(
            processi_service.E_NOT_FOUND, processi_service.E_VALIDATION,
        )

    # 9. Il quarto canale. ⚠️ Non e' un dettaglio di vocabolario: e' il canale
    #    dei processi svegliati da una macchina, e senza di lui il filtro della
    #    schermata rifiuterebbe con un 400 una richiesta perfettamente valida.
    def test_coda_automatica_e_un_filtro_ammesso(self):
        svc, repo = _service()
        svc.list_processi(canale="CODA_AUTOMATICA")
        self.assertEqual(
            repo.list_processi.call_args.kwargs["canale"], "CODA_AUTOMATICA",
        )


class ProcessiServiceUtenteTecnicoTests(unittest.TestCase):
    # 10. I due verbi sono simmetrici anche nel rifiuto: nessuno dei due prova a
    #     indovinare l'azienda. ⛔ Un verbo che si sceglie il perimetro da solo e'
    #     esattamente cio' che la decisione D-9 ha escluso.
    def test_entrambi_i_verbi_pretendono_processo_ed_emittente(self):
        svc, _repo = _service()
        for verbo in ("crea_utente_tecnico", "riattiva_utente_tecnico"):
            for processo, emittente in (("", "ACME"), ("x", "")):
                with self.subTest(verbo=verbo, processo=processo):
                    with self.assertRaises(ServiceError):
                        getattr(svc, verbo)(processo, emittente_codice=emittente)


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
        svc.list_processi(classe="DOMINIO", canale="COMMAND", vivo=True)
        kwargs = repo.list_processi.call_args.kwargs
        self.assertEqual(kwargs["classe"], "DOMINIO")
        self.assertEqual(kwargs["canale"], "COMMAND")
        self.assertIs(kwargs["vivo"], True)

    # 2-3. Il cap e il pavimento: un `limit` enorme non diventa una query che
    #      porta via il database, e un `offset` negativo non arriva all'SQL.
    def test_limit_e_offset_normalizzati(self):
        svc, repo = _service()
        svc.list_processi(limit=100_000, offset=-5)
        kwargs = repo.list_processi.call_args.kwargs
        self.assertEqual(kwargs["limit"], MAX_LIMIT)
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

    # 11. ⛔ Un presidio NON LETTO non e' «a posto» e non e' «acceso»: ha un
    #     conteggio `None` e un errore, e va contato a parte. Sommarlo agli
    #     accesi direbbe che c'e' un guasto dove c'e' una cecita'; ometterlo
    #     lascerebbe leggere «tutto verde» a chi non ha visto niente.
    def test_un_presidio_non_letto_si_conta_a_parte(self):
        svc, _repo = _service(stato_presidi=[
            {"vista": "a", "conteggio": 0, "righe": [], "descrizione": "d",
             "errore": None},
            {"vista": "b", "conteggio": None, "righe": [], "descrizione": "d",
             "errore": "connessione persa"},
        ])
        esito = svc.stato_presidi()
        self.assertEqual(esito["con_righe"], 0)
        self.assertEqual(esito["non_letti"], 1)

    # 12. ⭐ Regola del 2 (ok Tid 2026-09-18): `con_righe`/`non_letti` li calcola
    #     UNA funzione per il pannello e per il pallino. Il test pinna la parita'
    #     sullo stesso elenco — con un acceso, un non letto e uno a zero — e che
    #     la lettura del pallino sia quella LEGGERA (`con_righe=False`): se
    #     qualcuno ricopiasse i due `sum`, la parita' reggerebbe oggi e si
    #     romperebbe alla prima modifica, e questo test non lo vedrebbe; per
    #     questo pinna anche il callable, che deve essere lo stesso oggetto.
    def test_la_testata_e_una_sola_per_pannello_e_pallino(self):
        from apps.core.services import processi_service
        righe = [
            {"vista": "a", "conteggio": 0, "righe": [], "descrizione": "d",
             "errore": None},
            {"vista": "b", "conteggio": 3, "righe": [{}], "descrizione": "d",
             "errore": None},
            {"vista": "c", "conteggio": None, "righe": [], "descrizione": "d",
             "errore": "giu'"},
        ]
        svc, _repo = _service(stato_presidi=righe)
        pannello = svc.stato_presidi()
        pallino = svc.conteggi_presidi()
        self.assertEqual(pallino, {"totale": 3, "con_righe": 1, "non_letti": 1})
        self.assertEqual(
            {k: pannello[k] for k in ("totale", "con_righe", "non_letti")},
            pallino,
        )
        # La funzione e' UNA, ed e' quella di modulo.
        self.assertEqual(processi_service._testata_presidi(righe), pallino)
        # Il pallino legge LEGGERO: niente prime righe da ogni scheda aperta.
        svc._presidi.stato_presidi.assert_any_call(con_righe=False)

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
