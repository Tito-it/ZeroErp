# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Esegui ora» su una sveglia — il predicato, la capability, il verbo
#        del service e il CONTRATTO con il drawer (piano-be-fe-avvio-manuale
#        §5.5). Repository della coda MOCKATO: qui si prova cio' che il
#        backend decide e in che ORDINE, non cio' che il database contiene.
# Note: ⭐ Il pezzo che conta di piu' e' l'ultimo: i quattro nomi con cui la
#        capability viaggia (`can_esegui_ora*`) e le tre `reason_key` si
#        confrontano con il SORGENTE del drawer e con i locales. Un campo
#        emesso con un nome e letto con un altro non fallisce da nessuna
#        parte: spegne il tooltip, e basta (api.md §Capability di riga,
#        «verificare che il client la LEGGA»).
#        ⚠️ Le sveglie usate qui sono quelle VERE di `sveglie.json` (lette
#        con `sveglie_di_processo` / `prima_sveglia_candidata`), non
#        ricopiate: se il dichiarato cambia, cambia anche il caso — che e' il
#        verso giusto. Dove serve un caso che il dichiarato non ha (un servizio
#        con `avvio_manuale = true`), si COSTRUISCE una `Sveglia` a mano.
#        ⛔ `SimpleTestCase`, non `unittest.TestCase`: i repository sono
#        finti, e un mock dimenticato deve FALLIRE, non parlare col dbdev.
#
# Indice test:
#   Predicato (puro)
#    1. senza motivi -> ammesso (lista vuota) su un timer candidato e acceso
#    2. servizio -> motivo 1, anche se `avvio_manuale` fosse true (natura)
#    3. timer con `avvio_manuale = false` -> motivo 1
#    4. processo spento (`acceso` False, dal DB) -> motivo 2; non decidibile
#       (`acceso` None, ambiente non dichiarato) -> motivo 2-bis
#    5. lavoro vivo -> motivo 3 con `dettaglio = {job_id}`
#    6. tutti e tre insieme -> nell'ORDINE 1, 2, 3 (il primo si mostra)
#    7. `come_errore` porta codice, frase con la unit dentro e `context`
#   Capability
#    8. flag DERIVATO dal motivo: ammesso -> True e terna a None;
#       bloccato -> False, reason, reason_key, dettaglio
#    9. `riga_sveglia` porta dichiarato + capability, `comando` come lista
#   Service `esegui_ora`
#   10. `unit` assente / non stringa -> E_VALIDATION_INPUT campo `unit`,
#       PRIMA di leggere la coda e di accodare
#   11. processo inesistente -> E_PROCESSO_NON_TROVATO, niente accoda
#   12. unit non del processo -> E_VALIDATION_INPUT campo `unit`, niente accoda
#   13. motivo del predicato -> rifiuto col SUO codice PRIMA di accodare
#   14. gia' in coda -> E_PROCESSO_AVVIO_GIA_IN_CODA con job_id, niente accoda
#   15. ok -> `accoda` con job_type, run_as SISTEMA, chiave per unit, attore,
#       payload {processo_codice, unit}; risposta {job_id, stato, unit}
#   16. il dettaglio porta `sveglie[]` con la capability, UNA query per i vivi,
#       e `accensione` letta UNA volta e passata a ogni sveglia
#   16-bis. processo spento -> rifiuto E_PROCESSO_SVEGLIA_NON_ABILITATA PRIMA
#       di accodare (P-2)
#   Contratto FE/BE
#   17. i quattro nomi della capability sono quelli che il drawer legge
#   18. ogni reason_key esiste in it.json E in en.json
#   19. la copia di FORMA_TIMER nel drawer e' la costante del backend
# ------------------------------------------------------------

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services import avvio_manuale as am
from apps.core.services.avvio_manuale import (
    CAPABILITY_DETTAGLIO,
    CAPABILITY_FLAG,
    CAPABILITY_REASON,
    CAPABILITY_REASON_KEY,
    JOB_TYPE_ESEGUI_PROCESSO,
    REASON_KEY_PER_CODICE,
    capability_esegui_ora,
    chiave_idempotenza,
    motivi_esegui_ora,
    riga_sveglia,
)
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI, PROCESSO_DRAINA_CODA_LAVORI
from apps.core.services.processi_service import E_NOT_FOUND, E_VALIDATION_INPUT, ProcessiService
from apps.core.services.service_errors import ServiceError
from apps.core.services.sveglie import FORMA_SERVIZIO, FORMA_TIMER, Sveglia, sveglie_di_processo
from apps.core.tests._repo import repo_root
from apps.core.tests._sveglie import prima_sveglia_candidata

_DRAWER = repo_root() / "frontend/src/amministrazione/components/ProcessoDrawer.vue"
_LOCALES = repo_root() / "frontend/src/locales"



# Scopo: una sveglia costruita a mano, per i casi che il dichiarato non ha.
def _sveglia(**override) -> Sveglia:
    base = {
        "unit": "zeroerp-test", "processo_codice": "test", "forma": FORMA_TIMER,
        "comando": ("test_cmd",), "oncalendar": "*:0/5",
        "avvio_manuale": True, "nota": "",
    }
    base.update(override)
    return Sveglia(**base)


# Scopo: il service con i tre repository finti; `coda` risponde «nessun vivo».
def _service(*, get_processo=None, vivi=None, acceso=True):
    repo = MagicMock()
    repo.get_processo.return_value = get_processo
    # Le due letture dello stesso stato: chi decide (`acceso_processo`) e
    # chi descrive (`accensione_processo`, il dettaglio).
    repo.acceso_processo.return_value = acceso
    repo.accensione_processo.return_value = {"acceso": acceso}
    repo.emittenti_non_serviti.return_value = []
    coda = MagicMock()
    coda.lavori_vivi_per_chiave.return_value = vivi or {}
    coda.accoda.return_value = 4321
    coda.stati_dopo_accodamento.return_value = {4321: "PENDING"}
    return ProcessiService(repo=repo, presidi=MagicMock(), coda=coda), coda


class PredicatoTests(SimpleTestCase):
    # 1. Un timer candidato, acceso, senza lavoro vivo: si puo'.
    def test_senza_motivi_e_ammesso(self) -> None:
        self.assertEqual(motivi_esegui_ora(prima_sveglia_candidata(), acceso=True, lavoro_vivo=None), [])

    # 2. Il servizio non e' un candidato per NATURA: anche con `avvio_manuale`
    #    a true (che il caricatore rifiuta, ma il predicato non deve contarci).
    def test_servizio_e_motivo_1(self) -> None:
        s = _sveglia(forma=FORMA_SERVIZIO, oncalendar=None, avvio_manuale=True)
        motivi = motivi_esegui_ora(s, acceso=True, lavoro_vivo=None)
        self.assertEqual([m.codice for m in motivi], [am.E_SVEGLIA_NON_AVVIABILE_A_MANO])

    # 3. Il timer dichiarato non candidato (il drenatore): motivo 1.
    def test_timer_non_candidato_e_motivo_1(self) -> None:
        drenatore = sveglie_di_processo(PROCESSO_DRAINA_CODA_LAVORI)
        self.assertTrue(drenatore, "il drenatore non e' in sveglie.json")
        motivi = motivi_esegui_ora(drenatore[0], acceso=True, lavoro_vivo=None)
        self.assertEqual([m.codice for m in motivi], [am.E_SVEGLIA_NON_AVVIABILE_A_MANO])

    # 4. Processo spento su questa installazione: motivo 2, e SOLO quello.
    #    Non decidibile (ambiente non dichiarato): il 2-bis, mai «acceso».
    def test_spenta_e_motivo_2(self) -> None:
        motivi = motivi_esegui_ora(_sveglia(), acceso=False, lavoro_vivo=None)
        self.assertEqual([m.codice for m in motivi], [am.E_PROCESSO_SPENTO])
        self.assertEqual(motivi[0].dettaglio, {"processo": "test"})
        motivi = motivi_esegui_ora(_sveglia(), acceso=None, lavoro_vivo=None)
        self.assertEqual([m.codice for m in motivi], [am.E_ACCENSIONE_NON_DECIDIBILE])

    # 5. Gia' in coda: motivo 3, con l'id del lavoro nel dettaglio (e' il
    #    parametro `{job_id}` della chiave i18n) e nella frase.
    def test_gia_in_coda_e_motivo_3_con_job_id(self) -> None:
        motivi = motivi_esegui_ora(_sveglia(), acceso=True, lavoro_vivo={"id": 77, "stato": "PENDING"})
        self.assertEqual(len(motivi), 1)
        self.assertEqual(motivi[0].codice, am.E_AVVIO_GIA_IN_CODA)
        self.assertEqual(motivi[0].dettaglio, {"job_id": 77})
        self.assertIn("77", motivi[0].messaggio)

    # 6. L'ordine e' quello del piano §2.2: il primo e' quello che si mostra.
    def test_ordine_dei_motivi(self) -> None:
        s = _sveglia(avvio_manuale=False)
        motivi = motivi_esegui_ora(s, acceso=False, lavoro_vivo={"id": 1, "stato": "IN_CORSO"})
        self.assertEqual(
            [m.codice for m in motivi],
            [am.E_SVEGLIA_NON_AVVIABILE_A_MANO, am.E_PROCESSO_SPENTO, am.E_AVVIO_GIA_IN_CODA],
        )

    # 7. Il rifiuto: codice, frase col PROCESSO dentro (mai il nome di un
    #    parametro), context = dettaglio + extra del chiamante.
    def test_come_errore(self) -> None:
        s = _sveglia(unit="zeroerp-x", processo_codice="proc_x")
        err = motivi_esegui_ora(s, acceso=False, lavoro_vivo=None)[0].come_errore(unit="zeroerp-x")
        self.assertIsInstance(err, ServiceError)
        self.assertEqual(err.code, am.E_PROCESSO_SPENTO)
        self.assertIn("proc_x", err.message)
        self.assertNotIn("p_processo", err.message)
        self.assertEqual(err.context, {"processo": "proc_x", "unit": "zeroerp-x"})


class CapabilityTests(SimpleTestCase):
    # 8. Il flag si DERIVA dal motivo: e' l'unica cosa che rende impossibile
    #    un pulsante acceso su un gesto che l'endpoint rifiuta.
    def test_flag_derivato_dal_motivo(self) -> None:
        ok = capability_esegui_ora(_sveglia(), acceso=True, lavoro_vivo=None)
        self.assertEqual(ok, {
            CAPABILITY_FLAG: True, CAPABILITY_REASON: None,
            CAPABILITY_REASON_KEY: None, CAPABILITY_DETTAGLIO: None,
        })
        ko = capability_esegui_ora(_sveglia(), acceso=True, lavoro_vivo={"id": 5, "stato": "PENDING"})
        self.assertEqual(ko, {
            CAPABILITY_FLAG: False,
            CAPABILITY_REASON: am.E_AVVIO_GIA_IN_CODA,
            CAPABILITY_REASON_KEY: REASON_KEY_PER_CODICE[am.E_AVVIO_GIA_IN_CODA],
            CAPABILITY_DETTAGLIO: {"job_id": 5},
        })

    # 9-bis. Una sveglia calendariale porta `dovuto` (la cadenza del LAVORO, nel
    #        fuso dell'azienda): `oncalendar` e' solo la sveglia oraria.
    def test_riga_sveglia_calendariale_porta_dovuto(self) -> None:
        from datetime import time

        from apps.core.services.sveglie import Dovuto

        s = _sveglia(oncalendar="*:00", dovuto=Dovuto("settimana", time(7, 30), 0, "p:c"))
        riga = riga_sveglia(s, acceso=True, lavoro_vivo=None)
        self.assertEqual(riga["dovuto"], {"ogni": "settimana", "giorno": 0, "dalle": "07:30"})

    # 9. La riga: il dichiarato (da mostrare) + la capability (su cui decidere).
    def test_riga_sveglia(self) -> None:
        s = _sveglia(unit="zeroerp-r", comando=("cmd", "--a", "b"), nota="n")
        riga = riga_sveglia(s, acceso=True, lavoro_vivo=None)
        self.assertEqual(riga["unit"], "zeroerp-r")
        self.assertEqual(riga["forma"], FORMA_TIMER)
        self.assertEqual(riga["comando"], ["cmd", "--a", "b"])
        self.assertEqual(riga["oncalendar"], "*:0/5")
        self.assertIsNone(riga["dovuto"])
        self.assertNotIn("abilita", riga)
        self.assertTrue(riga["avvio_manuale"])
        self.assertEqual(riga["nota"], "n")
        self.assertTrue(riga[CAPABILITY_FLAG])


class EseguiOraServiceTests(SimpleTestCase):
    # 10. `unit` obbligatoria e stringa: il rifiuto sta PRIMA di ogni lettura.
    def test_unit_obbligatoria(self) -> None:
        for unit in (None, "", "   ", 7):
            with self.subTest(unit=unit):
                svc, coda = _service(get_processo={"codice": "x"})
                with self.assertRaises(ServiceError) as cm:
                    svc.esegui_ora("x", unit=unit, richiesto_da=9)
                self.assertEqual(cm.exception.code, E_VALIDATION_INPUT)
                self.assertEqual(cm.exception.context.get("field"), "unit")
                coda.lavori_vivi_per_chiave.assert_not_called()
                coda.accoda.assert_not_called()

    # 11. Processo inesistente: 404 di dominio, niente accoda.
    def test_processo_inesistente(self) -> None:
        svc, coda = _service(get_processo=None)
        with self.assertRaises(ServiceError) as cm:
            svc.esegui_ora("non_esiste", unit="zeroerp-x", richiesto_da=9)
        self.assertEqual(cm.exception.code, E_NOT_FOUND)
        coda.accoda.assert_not_called()

    # 12. La unit deve essere fra le sveglie DI QUEL processo: il client manda
    #     una unit, mai un comando, e il backend la risolve dal dichiarato.
    def test_unit_non_del_processo(self) -> None:
        candidata = prima_sveglia_candidata()
        svc, coda = _service(get_processo={"codice": PROCESSO_DRAINA_CODA_LAVORI})
        with self.assertRaises(ServiceError) as cm:
            # La unit del digest, chiesta sul processo del drenatore.
            svc.esegui_ora(PROCESSO_DRAINA_CODA_LAVORI, unit=candidata.unit, richiesto_da=9)
        self.assertEqual(cm.exception.code, E_VALIDATION_INPUT)
        self.assertEqual(cm.exception.context.get("field"), "unit")
        coda.accoda.assert_not_called()

    # 13. Un motivo del predicato rifiuta col SUO codice, prima di accodare.
    def test_motivo_rifiuta_prima_di_accodare(self) -> None:
        drenatore = sveglie_di_processo(PROCESSO_DRAINA_CODA_LAVORI)[0]
        svc, coda = _service(get_processo={"codice": PROCESSO_DRAINA_CODA_LAVORI})
        with self.assertRaises(ServiceError) as cm:
            svc.esegui_ora(PROCESSO_DRAINA_CODA_LAVORI, unit=drenatore.unit, richiesto_da=9)
        self.assertEqual(cm.exception.code, am.E_SVEGLIA_NON_AVVIABILE_A_MANO)
        coda.accoda.assert_not_called()

    # 14. Gia' in coda: 409 col job_id, letto dal repository con la chiave
    #     per unit — la stessa che `accoda` scriverebbe.
    def test_gia_in_coda_rifiuta(self) -> None:
        s = prima_sveglia_candidata()
        chiave = chiave_idempotenza(s.unit)
        svc, coda = _service(
            get_processo={"codice": PROCESSO_DIGEST_PRESIDI},
            vivi={chiave: {"id": 88, "stato": "PENDING"}},
        )
        with self.assertRaises(ServiceError) as cm:
            svc.esegui_ora(PROCESSO_DIGEST_PRESIDI, unit=s.unit, richiesto_da=9)
        self.assertEqual(cm.exception.code, am.E_AVVIO_GIA_IN_CODA)
        self.assertEqual(cm.exception.context.get("job_id"), 88)
        coda.lavori_vivi_per_chiave.assert_called_once_with(
            job_type=JOB_TYPE_ESEGUI_PROCESSO, chiavi=[chiave],
        )
        coda.accoda.assert_not_called()

    # 15. Il caso buono: `accoda` con tutto cio' che il drenatore e la UI code
    #     si aspettano, e la risposta nella forma del giro di fatturazione.
    def test_ok_accoda(self) -> None:
        s = prima_sveglia_candidata()
        svc, coda = _service(get_processo={"codice": PROCESSO_DIGEST_PRESIDI})
        esito = svc.esegui_ora(PROCESSO_DIGEST_PRESIDI, unit=f"  {s.unit} ", richiesto_da=9)
        self.assertEqual(esito, {"job_id": 4321, "stato": "PENDING", "unit": s.unit})
        kwargs = coda.accoda.call_args.kwargs
        self.assertEqual(kwargs["job_type"], JOB_TYPE_ESEGUI_PROCESSO)
        # ⭐ SISTEMA dal 2026-11-07 (BE10): processo di MANUTENZIONE, e un
        #    lavoro per azienda sarebbe stato falso. Chi preme e' l'attore.
        self.assertEqual(kwargs["run_as"], "SISTEMA")
        self.assertIsNone(kwargs["scope"])
        self.assertEqual(kwargs["idempotency_key"], chiave_idempotenza(s.unit))
        self.assertEqual(kwargs["payload"], {
            "processo_codice": PROCESSO_DIGEST_PRESIDI, "unit": s.unit, "richiesto_da": 9,
        })
        self.assertEqual(kwargs["origine"], "API")

    # 16-bis. ⭐ P-2: su un processo spento «Esegui ora» e' rifiutato PRIMA di
    #         accodare, col codice del motivo 2 — la stessa lettura del DB con
    #         cui il dettaglio spegne il pulsante.
    def test_processo_spento_rifiuta_prima_di_accodare(self) -> None:
        s = prima_sveglia_candidata()
        svc, coda = _service(get_processo={"codice": PROCESSO_DIGEST_PRESIDI}, acceso=False)
        with self.assertRaises(ServiceError) as cm:
            svc.esegui_ora(PROCESSO_DIGEST_PRESIDI, unit=s.unit, richiesto_da=9)
        self.assertEqual(cm.exception.code, am.E_PROCESSO_SPENTO)
        coda.accoda.assert_not_called()

    # 16. Il dettaglio porta `sveglie[]` con la capability per riga, e i vivi
    #     si leggono con UNA query per tutte le unit del processo.
    def test_dettaglio_porta_le_sveglie_con_capability(self) -> None:
        sveglie = sveglie_di_processo(PROCESSO_DIGEST_PRESIDI)
        self.assertGreaterEqual(len(sveglie), 2, "il digest ha due corsie in sveglie.json")
        viva = sveglie[0]
        svc, coda = _service(
            get_processo={"codice": PROCESSO_DIGEST_PRESIDI, "bersagli": [], "identita": []},
            vivi={chiave_idempotenza(viva.unit): {"id": 12, "stato": "PENDING"}},
        )
        dettaglio = svc.get_processo(PROCESSO_DIGEST_PRESIDI)
        righe = {r["unit"]: r for r in dettaglio["sveglie"]}
        self.assertEqual(set(righe), {s.unit for s in sveglie})
        self.assertFalse(righe[viva.unit][CAPABILITY_FLAG])
        self.assertEqual(righe[viva.unit][CAPABILITY_DETTAGLIO], {"job_id": 12})
        coda.lavori_vivi_per_chiave.assert_called_once()
        chiavi = coda.lavori_vivi_per_chiave.call_args.kwargs["chiavi"]
        self.assertEqual(sorted(chiavi), sorted(chiave_idempotenza(s.unit) for s in sveglie))
        # L'accensione: letta UNA volta e passata al dettaglio com'e'.
        self.assertIs(dettaglio["accensione"]["acceso"], True)
        # Un processo senza sveglie (pgAgent): lista vuota, nessuna query.
        svc2, coda2 = _service(get_processo={"codice": "x", "bersagli": [], "identita": []})
        self.assertEqual(svc2.get_processo("x")["sveglie"], [])
        coda2.lavori_vivi_per_chiave.assert_not_called()


class ContrattoConIlDrawerTests(SimpleTestCase):
    # 17. ⭐ I nomi emessi sono quelli LETTI. Il drawer passa il prefisso
    #     `can_esegui_ora` a `bloccoAttivo`/`motivoBloccoRiga`, che da li'
    #     derivano `_reason`, `_reason_key`, `_dettaglio` (bloccoMotivo.js):
    #     quindi si pinna il prefisso e la derivazione, e che i tre nomi
    #     emessi siano esattamente prefisso + suffisso.
    def test_i_nomi_della_capability_sono_quelli_del_drawer(self) -> None:
        sorgente = _DRAWER.read_text(encoding="utf-8")
        self.assertIn(
            f"bloccoAttivo(sveglia, '{CAPABILITY_FLAG}', '{CAPABILITY_FLAG}')", sorgente,
            "il drawer non legge il flag con il prefisso emesso dal backend",
        )
        self.assertIn(
            f"motivoBloccoRiga(t, te, sveglia, '{CAPABILITY_FLAG}')", sorgente,
            "il drawer non legge il motivo con il prefisso emesso dal backend",
        )
        self.assertEqual(CAPABILITY_REASON, f"{CAPABILITY_FLAG}_reason")
        self.assertEqual(CAPABILITY_REASON_KEY, f"{CAPABILITY_FLAG}_reason_key")
        self.assertEqual(CAPABILITY_DETTAGLIO, f"{CAPABILITY_FLAG}_dettaglio")
        # E il drawer legge `dettaglio.sveglie`, il nome con cui il service le mette.
        self.assertRegex(sorgente, re.compile(r"dettaglio\.value\?\.sveglie"))

    # 18. Le tre chiavi i18n esistono, in ENTRAMBE le lingue: una chiave
    #     mancante non fallisce, mostra il codice macchina.
    def test_le_reason_key_esistono_nei_locales(self) -> None:
        for lingua in ("it", "en"):
            with (_LOCALES / f"{lingua}.json").open(encoding="utf-8") as fh:
                locale = json.load(fh)
            for codice, chiave in REASON_KEY_PER_CODICE.items():
                with self.subTest(lingua=lingua, codice=codice):
                    nodo = locale
                    for segmento in chiave.split("."):
                        self.assertIn(segmento, nodo, f"{chiave} assente da {lingua}.json")
                        nodo = nodo[segmento]
                    self.assertIsInstance(nodo, str)
                    self.assertTrue(nodo.strip(), f"{chiave} vuota in {lingua}.json")
        # La chiave di «gia' in coda» porta il segnaposto che il dettaglio riempie.
        gia_in_coda = REASON_KEY_PER_CODICE[am.E_AVVIO_GIA_IN_CODA]
        with (_LOCALES / "it.json").open(encoding="utf-8") as fh:
            nodo = json.load(fh)
        for segmento in gia_in_coda.split("."):
            nodo = nodo[segmento]
        self.assertIn("{job_id}", nodo)

    # 19. ⭐ Il drawer decide «pulsante sì/no» sulla FORMA (`v-if` su
    #     `s.forma === FORMA_TIMER`), ed e' l'unica ramificazione del client sul
    #     vocabolario del backend (piano §4.3). Quel vocabolario e' una copia
    #     locale nel drawer: se il backend rinominasse il valore, il pulsante
    #     sparirebbe da TUTTI i timer senza nessun errore. Si pinna la copia
    #     alla costante di `sveglie.py`.
    def test_la_forma_timer_del_drawer_e_quella_del_backend(self) -> None:
        sorgente = _DRAWER.read_text(encoding="utf-8")
        trovato = re.search(r"const FORMA_TIMER = '([^']+)'", sorgente)
        self.assertIsNotNone(trovato, "il drawer non dichiara piu' FORMA_TIMER")
        assert trovato is not None
        self.assertEqual(
            trovato.group(1), FORMA_TIMER,
            "la forma «timer» del drawer non e' quella del backend: il pulsante "
            "«Esegui ora» non comparirebbe su nessuna sveglia",
        )
