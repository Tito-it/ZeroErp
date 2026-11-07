# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'handler `esegui_processo_default` del drenatore, con il
#        sottoprocesso FINTO (`subprocess.Popen` sostituito): che cosa lancia,
#        con quale ambiente, e come traduce ogni esito
#        (piano-be-fe-avvio-manuale §5.3).
# Note: ⛔ Nessun sottoprocesso vero e nessun database: si prova che l'handler
#        non lanci NIENTE fuori dal dichiarato e che non ritenti MAI — ogni
#        esito negativo porta il marcatore `terminale`, perche' ripetere un
#        payload rotto, una sveglia non candidata o un comando gia' fallito
#        riproduce lo stesso esito tenendo il lavoro «in corso» a video.
#        ⚠️ L'ambiente si controlla in due versi: le due variabili sono nel
#        dizionario passato al FIGLIO, e `os.environ` del padre NON le ha
#        dopo — il drenatore lavora piu' item per giro, e un attore lasciato
#        nell'ambiente passerebbe al lavoro successivo.
#        ⛔ Sul tetto si prova che il colpo vada al GRUPPO (`os.killpg`), non
#        al solo figlio: e' la differenza fra «interrotto» scritto nel lavoro
#        e un nipote che continua a girare. La prova sul processo VERO
#        (`bash -c 'sleep & wait'` che muore intero) e' stata fatta a mano il
#        2026-09-15: qui il figlio e' finto, e finto resta.
#        ⛔ `SimpleTestCase`: un mock dimenticato deve FALLIRE, non parlare
#        col dbdev.
#
# Indice test:
#    1. argv = [run-command.sh, *comando] dal dichiarato, senza shell, in
#       sessione propria, con l'output catturato e il tetto sull'attesa
#    2. l'env del figlio porta origine COMMAND e l'attore; os.environ no
#    3. exit 0 -> result con unit, comando, exit_code, durata, coda output
#    4. exit != 0 -> E_PROCESSO_AVVIO_FALLITO terminale, exit code nel context
#    5. tetto superato -> SIGKILL al GRUPPO, output parziale raccolto,
#       E_PROCESSO_AVVIO_TROPPO_LUNGO terminale, tetto nel context
#    6. unit ignota per il processo -> E_VALIDATION_INPUT terminale, campo unit,
#       e il sottoprocesso NON parte
#    7. sveglia non candidata / processo spento / accensione non decidibile
#       -> il codice del predicato, terminale, niente sottoprocesso
#    8. payload senza attore -> E_VALIDATION_INPUT terminale
#    9. run-command.sh assente -> E_CONFIG_MANCANTE terminale
#   10. `coda_output` tiene le ultime righe, accetta bytes e None, non solleva
#   11. l'handler e' registrato con il codice del seed (CoreConfig.ready)
#   12. il drenatore interrotto mentre aspetta -> il gruppo muore lo stesso
#   13. processo non piu' nel registro -> E_PROCESSO_NON_TROVATO terminale,
#       non «accensione non decidibile»
# ------------------------------------------------------------

from __future__ import annotations

import os
import signal
import subprocess
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.avvio_manuale import (
    E_ACCENSIONE_NON_DECIDIBILE,
    E_AVVIO_FALLITO,
    E_AVVIO_TROPPO_LUNGO,
    E_PROCESSO_SPENTO,
    E_SVEGLIA_NON_AVVIABILE_A_MANO,
    HANDLER_CODE,
    TETTO_SOTTOPROCESSO_SECONDI,
)
from apps.core.services.coda_lavori import esegui_processo_handler as mod
from apps.core.services.coda_lavori.drain_engine import CONTEXT_KEY_TERMINALE
from apps.core.services.coda_lavori.handler_registry import get_handler
from apps.core.services.job_run import ENV_JOB_AUTH_USER_ID, ENV_JOB_ORIGINE, ORIGINE_COMMAND
from apps.core.services.processi import PROCESSO_DRAINA_CODA_LAVORI
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError
from apps.core.services.sveglie import RUN_COMMAND, sveglie_di_processo
from apps.core.tests._sveglie import prima_sveglia_candidata

_POPEN = "apps.core.services.sottoprocesso.subprocess.Popen"   # il lancio sta nel BB
_KILLPG = "apps.core.services.sottoprocesso.os.killpg"
_IS_FILE = f"{mod.__name__}._wrapper_presente"
_PID = 4242


# Scopo: un processo finto con l'esito dato. `scade=True` fa sollevare
#        `TimeoutExpired` alla PRIMA `communicate` (quella col tetto) e
#        rispondere l'output parziale alla seconda (dopo l'uccisione), come fa
#        `Popen` vero; `interrompi` fa sollevare quell'eccezione al posto del
#        tetto (il drenatore fermato mentre aspetta).
class _ProcessoFinto:
    def __init__(
        self, *, returncode: int = 0, stdout: str = "ok\n", stderr: str = "",
        scade: bool = False, interrompi: BaseException | None = None,
    ) -> None:
        self.pid = _PID
        self.returncode = returncode
        self._stdout, self._stderr = stdout, stderr
        self._scade, self._interrompi = scade, interrompi
        self.communicate_calls: list[dict] = []
        self.waited = False

    def communicate(self, timeout=None):
        self.communicate_calls.append({"timeout": timeout})
        if self._interrompi is not None:
            exc, self._interrompi = self._interrompi, None
            raise exc
        if self._scade:
            self._scade = False
            raise subprocess.TimeoutExpired(cmd=["x"], timeout=timeout)
        return self._stdout, self._stderr

    def wait(self):
        self.waited = True
        return self.returncode


# Scopo: patcha `Popen` perche' torni il processo finto; ritorna il mock (per
#        leggere argv e kwargs) — il processo lo tiene chi lo ha costruito.
def _popen(proc: _ProcessoFinto):
    return patch(_POPEN, return_value=proc)


class EseguiProcessoHandlerTests(SimpleTestCase):
    def setUp(self) -> None:
        self.sveglia = prima_sveglia_candidata()
        self.payload = {
            "processo_codice": self.sveglia.processo_codice, "unit": self.sveglia.unit,
            "richiesto_da": 9,
        }
        # Il wrapper «esiste» per default: il caso in cui manca e' il test 9.
        patcher = patch(_IS_FILE, return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Il processo e' acceso per default (nessun DB): spento e non
        # decidibile sono il test 7.
        self._patch_acceso = patch(f"{mod.__name__}._acceso", return_value=True)
        self.acceso = self._patch_acceso.start()
        self.addCleanup(self._patch_acceso.stop)
        # Nessun colpo vero a nessun gruppo: si registra e basta.
        killpg = patch(_KILLPG)
        self.killpg = killpg.start()
        self.addCleanup(killpg.stop)

    # 1. Che cosa si lancia: il wrapper + l'argv del dichiarato, come LISTA
    #    (mai una stringa, mai shell), in una sessione sua, con l'output
    #    catturato; il tetto sta sull'attesa.
    def test_argv_dal_dichiarato_senza_shell(self) -> None:
        proc = _ProcessoFinto()
        with _popen(proc) as popen:
            mod.esegui_processo_handler(self.payload, scope=None)
        args, kwargs = popen.call_args
        self.assertEqual(args[0], [str(RUN_COMMAND), *self.sveglia.comando])
        self.assertIsInstance(args[0], list)
        self.assertNotIn("shell", kwargs)
        self.assertTrue(kwargs["start_new_session"])
        self.assertIs(kwargs["stdout"], subprocess.PIPE)
        self.assertIs(kwargs["stderr"], subprocess.PIPE)
        self.assertTrue(kwargs["text"])
        self.assertEqual(proc.communicate_calls, [{"timeout": TETTO_SOTTOPROCESSO_SECONDI}])
        self.killpg.assert_not_called()

    # 2. L'ambiente: le due variabili nel dizionario del FIGLIO, il resto
    #    ereditato; e il padre non le ha, ne' prima ne' dopo.
    def test_env_del_figlio_non_del_padre(self) -> None:
        self.assertNotIn(ENV_JOB_ORIGINE, os.environ)
        self.assertNotIn(ENV_JOB_AUTH_USER_ID, os.environ)
        with patch.dict(os.environ, {"ZEROERP_TEST_EREDITATA": "si"}), _popen(_ProcessoFinto()) as popen:
            mod.esegui_processo_handler(self.payload, scope=None)
            env = popen.call_args.kwargs["env"]
            self.assertEqual(env[ENV_JOB_ORIGINE], ORIGINE_COMMAND)
            self.assertEqual(env[ENV_JOB_AUTH_USER_ID], "9")
            self.assertEqual(env["ZEROERP_TEST_EREDITATA"], "si")
            self.assertIsNot(env, os.environ)
            self.assertNotIn(ENV_JOB_ORIGINE, os.environ)
            self.assertNotIn(ENV_JOB_AUTH_USER_ID, os.environ)

    # 3. Exit 0: il result del lavoro, con la coda dell'output.
    def test_exit_zero_e_fatto(self) -> None:
        with _popen(_ProcessoFinto(stdout="riga1\nriga2\n", stderr="avviso\n")):
            esito = mod.esegui_processo_handler(self.payload, scope=None)
        self.assertEqual(esito["unit"], self.sveglia.unit)
        self.assertEqual(esito["comando"], list(self.sveglia.comando))
        self.assertEqual(esito["exit_code"], 0)
        self.assertIsInstance(esito["durata_ms"], int)
        self.assertEqual(esito["coda_output"], "riga1\nriga2\navviso")

    # 4. Exit != 0: fallito, terminale, con l'exit code (un valore, non un
    #    nome di parametro) nella frase e nel context.
    def test_exit_non_zero_e_fallito_terminale(self) -> None:
        with _popen(_ProcessoFinto(returncode=3, stdout="", stderr="boom\n")):
            with self.assertRaises(ServiceError) as cm:
                mod.esegui_processo_handler(self.payload, scope=None)
        err = cm.exception
        self.assertEqual(err.code, E_AVVIO_FALLITO)
        self.assertTrue(err.context[CONTEXT_KEY_TERMINALE])
        self.assertEqual(err.context["exit_code"], 3)
        self.assertEqual(err.context["coda_output"], "boom")
        self.assertIn(self.sveglia.unit, err.message)
        self.assertIn("3", err.message)

    # 5. ⛔ Oltre il tetto: SIGKILL al GRUPPO del figlio (non al solo pid),
    #    poi la seconda `communicate` raccoglie l'output arrivato fino a li';
    #    l'handler traduce in TROPPO_LUNGO, terminale, con quella coda.
    def test_timeout_uccide_il_gruppo_e_troppo_lungo_terminale(self) -> None:
        proc = _ProcessoFinto(scade=True, stdout="parziale\n")
        with _popen(proc):
            with self.assertRaises(ServiceError) as cm:
                mod.esegui_processo_handler(self.payload, scope=None)
        self.killpg.assert_called_once_with(_PID, signal.SIGKILL)
        self.assertEqual(
            [c["timeout"] for c in proc.communicate_calls],
            [TETTO_SOTTOPROCESSO_SECONDI, None],
            "dopo l'uccisione si raccoglie l'output senza tetto",
        )
        err = cm.exception
        self.assertEqual(err.code, E_AVVIO_TROPPO_LUNGO)
        self.assertTrue(err.context[CONTEXT_KEY_TERMINALE])
        self.assertEqual(err.context["tetto_secondi"], TETTO_SOTTOPROCESSO_SECONDI)
        self.assertEqual(err.context["coda_output"], "parziale")
        self.assertIn(str(TETTO_SOTTOPROCESSO_SECONDI), err.message)

    # 6. Una unit che il deploy non ha per quel processo: payload rotto,
    #    terminale, e NIENTE parte.
    def test_unit_ignota_e_terminale_senza_lanciare(self) -> None:
        casi = (
            {"processo_codice": self.sveglia.processo_codice, "unit": "zeroerp-non-esiste"},
            {"processo_codice": "processo_ignoto", "unit": self.sveglia.unit},
            {},
            None,
        )
        with _popen(_ProcessoFinto()) as popen:
            for payload in casi:
                with self.subTest(payload=payload):
                    with self.assertRaises(ServiceError) as cm:
                        mod.esegui_processo_handler(payload, scope=None)
                    self.assertEqual(cm.exception.code, mod.E_PAYLOAD)
                    self.assertTrue(cm.exception.context[CONTEXT_KEY_TERMINALE])
                    self.assertEqual(cm.exception.context["field"], "unit")
            popen.assert_not_called()

    # 7. Il predicato si RICONTROLLA dove si esegue: una sveglia non candidata
    #    (il drenatore) o un processo spento non parte, col codice del
    #    predicato. ⭐ P-2: spento fra l'accodamento e il lancio vale lo stesso
    #    — l'accensione si rilegge qui, col codice del PROCESSO del payload.
    def test_predicato_ricontrollato(self) -> None:
        drenatore = sveglie_di_processo(PROCESSO_DRAINA_CODA_LAVORI)[0]
        with _popen(_ProcessoFinto()) as popen:
            with self.assertRaises(ServiceError) as cm:
                mod.esegui_processo_handler(
                    {"processo_codice": drenatore.processo_codice, "unit": drenatore.unit}, scope=None,
                )
            self.assertEqual(cm.exception.code, E_SVEGLIA_NON_AVVIABILE_A_MANO)
            self.assertTrue(cm.exception.context[CONTEXT_KEY_TERMINALE])

            for acceso, codice in ((False, E_PROCESSO_SPENTO), (None, E_ACCENSIONE_NON_DECIDIBILE)):
                with self.subTest(acceso=acceso):
                    self.acceso.reset_mock()
                    self.acceso.return_value = acceso
                    with self.assertRaises(ServiceError) as cm:
                        mod.esegui_processo_handler(self.payload, scope=None)
                    self.assertEqual(cm.exception.code, codice)
                    self.assertTrue(cm.exception.context[CONTEXT_KEY_TERMINALE])
                    self.acceso.assert_called_once_with(self.sveglia.processo_codice, self.sveglia.unit)
            popen.assert_not_called()

    # 8. Senza l'attore nel payload (`richiesto_da`, BE10) il comando non si
    #    lancia: scriverlo come CRON sarebbe il contrario di cio' per cui la
    #    variabile esiste. Terminale: riprovare non lo fa comparire.
    def test_payload_senza_attore(self) -> None:
        with _popen(_ProcessoFinto()) as popen:
            for attore in (None, "9", True):
                with self.subTest(attore=attore):
                    payload = {**self.payload, "richiesto_da": attore}
                    with self.assertRaises(ServiceError) as cm:
                        mod.esegui_processo_handler(payload, scope=None)
                    self.assertEqual(cm.exception.code, E_VALIDATION_INPUT)
                    self.assertTrue(cm.exception.context[CONTEXT_KEY_TERMINALE])
            popen.assert_not_called()

    # 9. Il wrapper non c'e': deploy rotto, terminale, niente parte.
    def test_wrapper_assente(self) -> None:
        with patch(_IS_FILE, return_value=False), _popen(_ProcessoFinto()) as popen:
            with self.assertRaises(ServiceError) as cm:
                mod.esegui_processo_handler(self.payload, scope=None)
            popen.assert_not_called()
        self.assertEqual(cm.exception.code, mod.E_CONFIG_MANCANTE)
        self.assertTrue(cm.exception.context[CONTEXT_KEY_TERMINALE])

    # 13. Il processo della sveglia non c'e' piu' nel registro: il SUO
    #     rifiuto, terminale — non None, che si leggerebbe «ambiente non
    #     dichiarato».
    def test_processo_inesistente_e_non_trovato(self) -> None:
        # Qui si prova `_acceso` VERO, col solo repository finto.
        self._patch_acceso.stop()
        with patch(f"{mod.__name__}.ProcessiRepository") as repo_cls, \
                _popen(_ProcessoFinto()) as popen:
            repo_cls.return_value.acceso_processo.side_effect = LookupError("x")
            with self.assertRaises(ServiceError) as cm:
                mod.esegui_processo_handler(self.payload, scope=None)
            popen.assert_not_called()
        self.assertEqual(cm.exception.code, mod.E_NOT_FOUND)
        self.assertTrue(cm.exception.context[CONTEXT_KEY_TERMINALE])

    # 10. La coda dell'output: ultime righe, cappata, bytes e None ammessi.
    def test_coda_output(self) -> None:
        righe = "\n".join(f"r{i}" for i in range(100))
        coda = mod.coda_output(righe, None)
        self.assertEqual(coda.splitlines()[0], f"r{100 - mod.CODA_OUTPUT_RIGHE}")
        self.assertEqual(coda.splitlines()[-1], "r99")
        self.assertEqual(mod.coda_output(b"a\n", b"b"), "a\nb")
        self.assertEqual(mod.coda_output(None, ""), "")
        lunga = "x" * (mod.CODA_OUTPUT_CARATTERI + 50)
        self.assertEqual(len(mod.coda_output(lunga, None)), mod.CODA_OUTPUT_CARATTERI)

    # 11. Il binding seed <-> Python: il codice del CSV risolve a QUESTO handler
    #     (registrato da CoreConfig.ready al boot dei test).
    def test_handler_registrato(self) -> None:
        self.assertIs(get_handler(HANDLER_CODE), mod.esegui_processo_handler)

    # 12. ⛔ Il DRENATORE interrotto mentre aspetta (Ctrl+C, segnale): il
    #     gruppo muore lo stesso e l'interruzione propaga intera — un figlio
    #     in sessione propria non la riceverebbe da solo, e resterebbe a
    #     girare sotto un drenatore che non c'e' piu'.
    def test_drenatore_interrotto_uccide_il_gruppo(self) -> None:
        proc = _ProcessoFinto(interrompi=KeyboardInterrupt())
        with _popen(proc):
            with self.assertRaises(KeyboardInterrupt):
                mod.esegui_processo_handler(self.payload, scope=None)
        self.killpg.assert_called_once_with(_PID, signal.SIGKILL)
        self.assertTrue(proc.waited, "il figlio ucciso va raccolto")
        # E un gruppo gia' morto non e' un errore: il colpo a vuoto si ignora.
        self.killpg.side_effect = ProcessLookupError()
        with _popen(_ProcessoFinto(interrompi=KeyboardInterrupt())):
            with self.assertRaises(KeyboardInterrupt):
                mod.esegui_processo_handler(self.payload, scope=None)
