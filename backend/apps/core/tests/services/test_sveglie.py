# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi sul DICHIARATO di deploy (`backend/deploy/sveglie.json`) — il
#        building block `apps.core.services.sveglie`.
# Note: ⭐ IL TEST 3 E' IL MOTIVO PER CUI QUESTO FILE ESISTE. Fino al
#        2026-09-06 tre processi su sei — `send_pending_emails`,
#        `sync_auth_user_active`, `listen_cambio_reparto` — non avevano NESSUN
#        artefatto di deploy: né template, né riga nell'installer. Su un host
#        nuovo non partivano mai, e nessun presidio poteva accorgersene:
#        `dbops.vw_processi_programmazione` li chiama FUORI_PORTATA, che
#        significa «il database non può saperlo». Chi può saperlo è questo lato,
#        e fino a ieri non guardava.
#        ⛔ Nessun accesso al database: sono file di progetto, e il test gira in
#        CI senza DB (regola `SimpleTestCase` di AGENTS.md).
#
# Indice test:
#   0. la cartella dei template esiste e non è vuota (anti verde-per-sottrazione)
#   1. il dichiarato si carica e ha la forma attesa
#   2. ogni sveglia dichiarata ha i suoi template su disco
#   3. ogni processo COMMAND del backend ha almeno una sveglia   ⭐
#   4. ogni template su disco è dichiarato (nessun unit orfano)
#   5. `tolleranza_minuti` nel JSON è RIFIUTATO: il contratto vive a catalogo
#   6. una forma non ammessa fa fallire il caricamento, non lo degrada
#   7. un timer senza cadenza fa fallire il caricamento
#   8. `abilita` è obbligatorio: il silenzio non vale «spento»
#   9. i worker del badge code hanno un contratto nel seed del catalogo
#  10. un nome di unit con una barra è rifiutato (finisce in un percorso)
#  11. `comando` è obbligatorio, per ogni forma, ed è una lista non vuota
#  12. un token con spazi o metacaratteri è rifiutato (systemd ≠ subprocess)
#  13. il primo token di ogni `comando` dichiarato è un management command
#      che esiste nel backend                                               ⭐
#
#  ⭐ Dal 2026-09-14 il JSON porta anche il `comando` (l'argv dopo
#     `run-command.sh`), reso nel template come `__COMANDO__`: è la riga che
#     «Esegui ora» lancia, e deve essere LA STESSA del timer. Che il template
#     non abbia più una riga cablata e che l'unit reso porti l'argv del JSON lo
#     prova `scripts/tests/test-install-timers.sh` (test 6 e 7): qui si prova
#     il CONTRATTO del campo, là il rendering.
#
#  ⭐ Dal 2026-09-11 la TOLLERANZA non sta più qui: è il contratto del processo
#     (`dbops.processi.tolleranza_minuti`, brief
#     `brief-db-quattro-processi-senza-presidio.md` D5). Il confronto fra la
#     cadenza di qui e quel contratto sta in `test_contratto_liveness_vs_deploy`.
# ------------------------------------------------------------

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services import processi, sveglie
from apps.core.services.coda_lavori.gestione_service import (
    JOBNAME_WORKER_CODA_LAVORI,
    JOBNAME_WORKER_CODA_STAMPA,
)
from apps.core.tests._contratto_processi import leggi_contratti_dal_seed

# ⛔ IL PERCORSO ARRIVA DAL MODULO, non ricalcolato qui. Una seconda aritmetica
#    che puntasse alla cartella sbagliata non farebbe fallire niente: troverebbe
#    zero file e i test 2 e 4 passerebbero **a vuoto**. Su un presidio che deve
#    accorgersi di ciò che MANCA, è il difetto peggiore possibile.
_TEMPLATE_DIR = sveglie.TEMPLATE_DIR

# La cartella `apps/` del backend, per il test 13: un management command vive
# in `apps/<app>/management/commands/<nome>.py`. Derivata dallo stesso layout
# del modulo (`DEPLOY_DIR` è `backend/deploy`), per la ragione scritta sopra.
_APPS_DIR = sveglie.DEPLOY_DIR.parent / "apps"


# Scopo: una voce VALIDA del dichiarato, con la possibilità di romperne un
#        pezzo. Ogni test negativo qui sotto rompe UNA cosa: una fixture rotta
#        in due modi proverebbe solo che il primo controllo in ordine di codice
#        scatta, non quello sotto prova.
_ASSENTE = object()


def _voce(**override: object) -> dict:
    base: dict = {
        "unit": "x", "processo_codice": "p", "forma": "timer",
        "comando": ["p"], "oncalendar": "*:0/1", "abilita": True,
    }
    base.update(override)
    return {k: v for k, v in base.items() if v is not _ASSENTE}


# Scopo: i codici dei processi che il BACKEND avvia, letti dal modulo che li
#        dichiara invece di essere riscritti qui.
# ⛔ Niente elenco a mano: sarebbe la terza sede dello stesso fatto, e la terza
#    è quella che nessuno aggiorna. Il giorno in cui nasce un command nuovo,
#    la costante entra in `processi.py` e il test 3 la vede da sé — che è
#    esattamente il comportamento voluto: il presidio deve accorgersi del
#    processo nuovo, non aspettare che qualcuno lo aggiunga anche qui.
def _processi_del_backend() -> set[str]:
    return {
        valore
        for nome, valore in vars(processi).items()
        if nome.startswith("PROCESSO_") and isinstance(valore, str)
    }


class SveglieDichiarateTests(SimpleTestCase):

    def setUp(self) -> None:
        sveglie.carica_sveglie.cache_clear()
        self.addCleanup(sveglie.carica_sveglie.cache_clear)

    # 0. ⛔ IL TEST CHE PROTEGGE GLI ALTRI. I test 2 e 4 confrontano il
    #    dichiarato con i file su disco: se la cartella non esistesse (modulo
    #    spostato, layout cambiato) entrambi passerebbero trovando zero file,
    #    cioè smetterebbero di verificare senza diventare rossi. Questo lo dice.
    def test_cartella_template_esiste_e_non_e_vuota(self) -> None:
        self.assertTrue(
            _TEMPLATE_DIR.is_dir(),
            f"la cartella dei template non esiste: {_TEMPLATE_DIR} — i test che "
            f"confrontano dichiarato e disco passerebbero a vuoto",
        )
        self.assertTrue(
            list(_TEMPLATE_DIR.glob("*.service")),
            f"nessun template .service in {_TEMPLATE_DIR}",
        )

    # 1. Il dichiarato si carica, non è vuoto, e ogni voce è coerente con la
    #    propria forma (un timer ha una cadenza, un servizio no).
    def test_dichiarato_si_carica_e_ha_forma_attesa(self) -> None:
        tutte = sveglie.carica_sveglie()
        self.assertTrue(tutte, "il dichiarato di deploy è vuoto")
        for s in tutte:
            with self.subTest(unit=s.unit):
                self.assertIn(s.forma, (sveglie.FORMA_TIMER, sveglie.FORMA_SERVIZIO))
                self.assertTrue(s.processo_codice)
                self.assertIsInstance(s.comando, tuple)
                self.assertTrue(s.comando, "una sveglia senza comando non sveglia niente")
                if s.e_timer:
                    self.assertTrue(s.oncalendar, "un timer senza cadenza non è un timer")
                else:
                    self.assertIsNone(s.oncalendar)

    # 2. Ogni sveglia dichiarata ha i template che l'installer si aspetta di
    #    trovare. Senza questo, una voce nuova nel JSON farebbe fallire
    #    l'installazione sull'HOST invece che in CI.
    def test_ogni_sveglia_ha_i_suoi_template(self) -> None:
        for s in sveglie.carica_sveglie():
            with self.subTest(unit=s.unit):
                self.assertTrue(
                    (_TEMPLATE_DIR / f"{s.unit}.service").is_file(),
                    f"manca il template {s.unit}.service",
                )
                timer = _TEMPLATE_DIR / f"{s.unit}.timer"
                if s.e_timer:
                    self.assertTrue(timer.is_file(), f"manca il template {s.unit}.timer")
                else:
                    # ⛔ Un servizio sempre acceso non deve avere un .timer: se
                    #    ce ne fosse uno, qualcuno lo accenderebbe credendo di
                    #    programmare un processo che non ha una cadenza.
                    self.assertFalse(
                        timer.is_file(),
                        f"{s.unit} è un servizio sempre acceso ma ha un .timer",
                    )

    # 3. ⭐ OGNI PROCESSO CHE IL BACKEND AVVIA HA ALMENO UNA SVEGLIA.
    #    È il presidio che mancava: un processo a catalogo, che si registra sul
    #    giornale dei run e che nessun artefatto di deploy fa partire, è un
    #    guasto che si manifesta come ASSENZA — e l'assenza non la nota nessuno.
    def test_ogni_processo_del_backend_ha_una_sveglia(self) -> None:
        senza_sveglia = sorted(
            codice
            for codice in _processi_del_backend()
            if not sveglie.sveglie_di_processo(codice)
        )
        self.assertEqual(
            senza_sveglia, [],
            "processi che il backend dichiara di eseguire ma che nessun unit "
            f"systemd fa partire: {senza_sveglia}. Serve una voce in "
            "backend/deploy/sveglie.json più la coppia di template.",
        )

    # 4. Il verso opposto: nessun template orfano. Un unit su disco che il
    #    dichiarato non nomina non viene installato da nessuno — sembra un
    #    deploy che c'è e non c'è.
    def test_nessun_template_orfano(self) -> None:
        dichiarati = {s.unit for s in sveglie.carica_sveglie()}
        su_disco = {p.stem for p in _TEMPLATE_DIR.glob("*.service")}
        self.assertEqual(
            sorted(su_disco - dichiarati), [],
            "template systemd presenti ma non dichiarati in sveglie.json",
        )

    # 5. ⛔ `tolleranza_minuti` nel JSON è RIFIUTATO, non ignorato. Dal
    #    2026-09-11 il contratto vive in `dbops.processi`: chi lo riscrive qui
    #    crede di aver dichiarato qualcosa, e un numero letto da nessuno è
    #    peggio di un errore — è la seconda sede che il cantiere ha tolto.
    def test_tolleranza_nel_json_e_rifiutata(self) -> None:
        self._assert_dichiarato_rifiutato(
            _voce(tolleranza_minuti=10),
            "dbops.processi",
        )
        # E vale anche a `null`: la chiave stessa è la seconda sede.
        self._assert_dichiarato_rifiutato(
            _voce(tolleranza_minuti=None),
            "dbops.processi",
        )

    # 6. Una forma non ammessa FERMA il caricamento. Un dichiarato letto «al
    #    meglio» darebbe una sveglia in meno senza dirlo.
    def test_forma_non_ammessa_solleva(self) -> None:
        self._assert_dichiarato_rifiutato(
            _voce(forma="cron"),
            "forma",
        )

    # 7. Un timer senza cadenza scriverebbe un unit che systemd rifiuta, e lo
    #    scoprirebbe l'host invece della CI.
    def test_timer_senza_cadenza_solleva(self) -> None:
        self._assert_dichiarato_rifiutato(
            _voce(oncalendar=None),
            "oncalendar",
        )

    # 8. ⛔ `abilita` omesso NON vale «spento». Con un default il silenzio
    #    produrrebbe un processo che non parte — il guasto-per-assenza che
    #    questo file esiste per togliere, reintrodotto dalla porta di servizio.
    def test_abilita_omesso_solleva(self) -> None:
        self._assert_dichiarato_rifiutato(
            _voce(forma="servizio", oncalendar=None, abilita=_ASSENTE),
            "abilita",
        )

    # 9. I due worker che alimentano il badge code DEVONO avere un contratto a
    #    catalogo: senza, `_liveness_worker` cade sul ripiego e il pallino verde
    #    poggia su un numero che nessuno ha deciso. Si legge il SEED nel repo
    #    (`processi.csv`), non il database: è la sede versionata del contratto.
    def test_worker_del_badge_hanno_un_contratto(self) -> None:
        contratti = leggi_contratti_dal_seed()
        for jobname in (JOBNAME_WORKER_CODA_LAVORI, JOBNAME_WORKER_CODA_STAMPA):
            with self.subTest(worker=jobname):
                contratto = contratti.get(jobname)
                self.assertIsNotNone(
                    contratto, f"{jobname} non è a catalogo in processi.csv",
                )
                assert contratto is not None
                self.assertIsNotNone(
                    contratto["tolleranza_minuti"],
                    f"{jobname} alimenta la liveness del badge code ma nel seed "
                    f"del catalogo ha tolleranza_minuti NULL",
                )

    # 10. Il nome dell'unit finisce interpolato in un percorso di file e passato
    #     a `systemctl`: un refuso con una barra scriverebbe fuori da
    #     `/etc/systemd/system` senza che niente lo dica.
    def test_unit_con_barra_solleva(self) -> None:
        self._assert_dichiarato_rifiutato(
            _voce(unit="../../etc/cattivo", forma="servizio", oncalendar=None),
            "non ammesso",
        )

    # 11. ⛔ `comando` è obbligatorio, ed è una LISTA non vuota — per ogni
    #     forma. Senza, l'installer scriverebbe `ExecStart=… run-command.sh ` e
    #     lo scoprirebbe l'host; e «Esegui ora» non avrebbe niente da lanciare.
    #     Una stringa è rifiutata anche se «sembra giusta»: come si spezza sugli
    #     spazi sarebbe una regola scritta due volte (qui e in systemd).
    def test_comando_obbligatorio_lista_non_vuota(self) -> None:
        self._assert_dichiarato_rifiutato(_voce(comando=_ASSENTE), "comando")
        self._assert_dichiarato_rifiutato(_voce(comando=[]), "comando")
        self._assert_dichiarato_rifiutato(_voce(comando="p --x"), "comando")
        # Vale anche per un servizio sempre acceso: ha un ExecStart pure lui.
        self._assert_dichiarato_rifiutato(
            _voce(forma="servizio", oncalendar=None, comando=_ASSENTE), "comando",
        )

    # 12. ⛔ Un token con uno spazio o un metacarattere è rifiutato. Lo stesso
    #     argv finisce in DUE lettori che lo trattano in modo diverso: systemd
    #     spezza l'`ExecStart` sugli spazi ed espande `%x`/`$VAR`, `subprocess`
    #     passa il token intero. Con `"--cadenza settimanale"` in un token il
    #     timer lancerebbe due argomenti e il pulsante uno — e nessuno dei due
    #     fallirebbe in modo parlante.
    def test_comando_con_spazi_o_metacaratteri_e_rifiutato(self) -> None:
        for cattivo in (
            ["p", "--cadenza settimanale"],   # spazio: systemd ≠ subprocess
            ["p", "%i"],                       # specifier systemd
            ["p", "$HOME"],                    # espansione d'ambiente
            ["p", "a|b"],                      # delimitatore del sed dell'installer
            ["p", "a&b"],                      # `&` nel replacement di sed
            ["p", "'x'"],                      # quote
            ["p", ""],                         # token vuoto
            ["Digest presidi"],                # il command non è un identificatore
            ["../manage"],                     # un percorso non è un command
        ):
            with self.subTest(comando=cattivo):
                self._assert_dichiarato_rifiutato(_voce(comando=cattivo), "comando")

    # 13. ⭐ IL PRIMO TOKEN È UN MANAGEMENT COMMAND CHE ESISTE. È la metà del
    #     contratto che il rendering non può provare: `test-install-timers.sh`
    #     dice che l'unit esegue l'argv del JSON, questo dice che quell'argv
    #     nomina un comando che il backend HA. Un refuso qui non fallisce in
    #     CI: fallisce sull'host, alla prima corsa del timer, con un
    #     `Unknown command` nel journal che nessuno legge.
    def test_il_comando_dichiarato_esiste_nel_backend(self) -> None:
        self.assertTrue(_APPS_DIR.is_dir(), f"layout inatteso: {_APPS_DIR}")
        comandi_esistenti = {
            p.stem for p in _APPS_DIR.glob("*/management/commands/*.py")
            if p.stem != "__init__"
        }
        self.assertTrue(comandi_esistenti, "nessun management command trovato: il test passerebbe a vuoto")
        for s in sveglie.carica_sveglie():
            with self.subTest(unit=s.unit):
                self.assertIn(
                    s.comando[0], comandi_esistenti,
                    f"{s.unit} dichiara il comando {s.comando[0]!r}, che non è un "
                    f"management command del backend",
                )

    # Scopo: scrive un dichiarato rotto in un file temporaneo, punta il modulo
    #        lì e verifica che il caricamento fallisca nominando il difetto.
    def _assert_dichiarato_rifiutato(self, voce: dict, atteso: str) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            percorso = Path(tmp) / "sveglie.json"
            percorso.write_text(json.dumps({"sveglie": [voce]}), encoding="utf-8")
            with patch.object(sveglie, "_PERCORSO_SVEGLIE", percorso):
                sveglie.carica_sveglie.cache_clear()
                with self.assertRaises(ValueError) as ctx:
                    sveglie.carica_sveglie()
        self.assertIn(atteso, str(ctx.exception))
