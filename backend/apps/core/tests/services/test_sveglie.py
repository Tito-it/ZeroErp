# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#   8. `abilita` è RIFIUTATO (dal 2026-10-16): l'accensione sta nel DB
#   9. i worker del badge code hanno un contratto nel seed del catalogo
#  10. un nome di unit con una barra è rifiutato (finisce in un percorso)
#  11. `comando` è obbligatorio, per ogni forma, ed è una lista non vuota
#  12. un token con spazi o metacaratteri è rifiutato (systemd ≠ subprocess)
#  13. il primo token di ogni `comando` dichiarato è un management command
#      che esiste nel backend                                               ⭐
#  14. `avvio_manuale` è obbligatorio e booleano: il silenzio non decide
#  15. un servizio sempre acceso non può dichiararsi avviabile a mano
#  16. il drenatore NON è candidato a «Esegui ora» (letto dal JSON per
#      processo, non ricopiato) — e almeno un timer lo è
#  17. `dovuto` si valida: vocabolario, orario, giorno, jobname, solo sui timer
#  18. l'inizio del periodo dovuto, nel fuso dell'azienda (giorno, settimana,
#      mese; prima delle `dalle` niente; il periodo precedente non si recupera)
#  19. OGNI template porta l'`ExecCondition` della SUA unit (accensione dal
#      DB, e il periodo per le calendariali) — e nessun `comando` contiene
#      il controllo                                                         ⭐
#  20. il `jobname` dichiarato è quello che il comando scrive
#  21. almeno le tre sveglie calendariali dichiarano `dovuto` (anti vuoto)
#  22. ogni sveglia `oneshot` ha il suo `TimeoutStartSec`: sotto la tolleranza
#      del processo, se ha un contratto, e sotto l'ora dopo cui il giornale
#      dice «presa e mai chiusa»; e sopra il tetto di «Esegui ora» per il
#      drenatore che lo aspetta                                            ⭐
#
#  ⭐ Dal 2026-10-09 il JSON porta `dovuto` sulle sveglie calendariali (brief
#     un-solo-fuso-aziendale T-4/T-9): il timer si sveglia ogni ora e
#     l'`ExecCondition` `e_dovuto` decide nel fuso dell'azienda.
#
#  ⭐ Dal 2026-09-15 il JSON porta `avvio_manuale`: la sede in cui si dice
#     quali sveglie hanno il pulsante «Esegui ora» (solo comandi brevi —
#     decisione 2a del brief §8.5, piano §3.2). Non è l'accensione del
#     processo, che dal 2026-10-16 sta nel DB.
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
        "comando": ["p"], "oncalendar": "*:0/1",
        "avvio_manuale": True,
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

    # 8. ⛔ `abilita` non e' piu' un campo (dal 2026-10-16): se un processo
    #    lavora lo decide il DB (`maintenance.fn_sveglia_accesa`). Riscritto
    #    qui farebbe credere a chi lo scrive di aver spento un processo che
    #    invece parte: si rifiuta, con tutti e due i valori.
    def test_abilita_e_rifiutato(self) -> None:
        for valore in (True, False):
            with self.subTest(abilita=valore):
                self._assert_dichiarato_rifiutato(_voce(abilita=valore), "abilita")

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
            _voce(unit="../../etc/cattivo", forma="servizio", oncalendar=None, avvio_manuale=False),
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

    # 14. ⛔ `avvio_manuale` SI DICHIARA. Con un default a `false` una sveglia
    #     nuova non avrebbe mai il pulsante senza che nessuno l'abbia deciso;
    #     con un default a `true` un comando lungo lo avrebbe. Nessun silenzio
    #     è una decisione — la stessa ragione del test 8.
    def test_avvio_manuale_omesso_o_non_booleano_solleva(self) -> None:
        self._assert_dichiarato_rifiutato(_voce(avvio_manuale=_ASSENTE), "avvio_manuale")
        self._assert_dichiarato_rifiutato(_voce(avvio_manuale="si"), "avvio_manuale")
        self._assert_dichiarato_rifiutato(_voce(avvio_manuale=None), "avvio_manuale")

    # 15. Un servizio sempre acceso non ha una corsa da lanciare: dichiararlo
    #     avviabile a mano è una contraddizione, e si ferma qui, non nel drawer.
    def test_servizio_avviabile_a_mano_solleva(self) -> None:
        self._assert_dichiarato_rifiutato(
            _voce(forma="servizio", oncalendar=None, avvio_manuale=True),
            "servizio sempre acceso",
        )

    # 16. ⭐ Il drenatore NON è candidato: «Esegui ora» lo esegue lui, e un
    #     lavoro che lancia il drenatore dal drenatore non ha senso (brief
    #     §8.2.3). L'unit si legge dal dichiarato PER PROCESSO, non ricopiata
    #     qui: il nome è un fatto del JSON. E almeno un timer deve essere
    #     candidato, o il pulsante non comparirebbe mai e il cantiere sarebbe
    #     verde a vuoto.
    def test_il_drenatore_non_e_candidato_e_almeno_un_timer_lo_e(self) -> None:
        drenatore = sveglie.sveglie_di_processo(processi.PROCESSO_DRAINA_CODA_LAVORI)
        self.assertTrue(drenatore, "il drenatore non ha una sveglia dichiarata")
        for s in drenatore:
            with self.subTest(unit=s.unit):
                self.assertFalse(
                    s.avvio_manuale,
                    f"{s.unit}: «Esegui ora» dal drenatore non ha senso — avvio_manuale dev'essere false",
                )
        candidati = [s.unit for s in sveglie.carica_sveglie() if s.avvio_manuale]
        self.assertTrue(candidati, "nessuna sveglia candidata a «Esegui ora»: il pulsante non comparirebbe mai")
        for s in sveglie.carica_sveglie():
            with self.subTest(unit=s.unit):
                if not s.e_timer:
                    self.assertFalse(s.avvio_manuale, f"{s.unit}: un servizio non si avvia a mano")

    # 17. `dovuto` si valida per intero, e solo un timer lo porta.
    def test_dovuto_si_valida(self) -> None:
        buono = {"ogni": "giorno", "dalle": "07:00", "jobname": "p:corsia"}
        casi = (
            ({**buono, "ogni": "anno"}, "'ogni'"),
            ({**buono, "dalle": "7:00"}, "'dalle'"),
            ({**buono, "dalle": "24:00"}, "'dalle'"),
            ({**buono, "giorno": 1}, "'giorno' non ha senso"),
            ({**buono, "ogni": "settimana"}, "'giorno' fra"),
            ({**buono, "ogni": "settimana", "giorno": "monday"}, "'giorno' fra"),
            ({**buono, "ogni": "mese", "giorno": 29}, "'giorno' del mese"),
            ({**buono, "ogni": "mese", "giorno": True}, "'giorno' del mese"),
            ({**buono, "jobname": "senza_corsia"}, "'jobname'"),
            ({**buono, "basta_una_corsa": "si"}, "'basta_una_corsa'"),
            ("ogni giorno", "oggetto"),
        )
        for dovuto, atteso in casi:
            with self.subTest(dovuto=dovuto):
                self._assert_dichiarato_rifiutato(_voce(dovuto=dovuto), atteso)
        self._assert_dichiarato_rifiutato(
            _voce(forma="servizio", oncalendar=None, avvio_manuale=False, dovuto=buono),
            "vale solo per un timer",
        )

    # 18. L'inizio del periodo dovuto. Il fuso e' un'ipotesi del test (Roma,
    #     +02:00 a settembre); `adesso` e' un istante UTC.
    def test_inizio_periodo_dovuto(self) -> None:
        from datetime import UTC, datetime, time
        from zoneinfo import ZoneInfo

        roma = ZoneInfo("Europe/Rome")
        giorno = sveglie.Dovuto("giorno", time(7, 0), None, "p:c")
        settimana = sveglie.Dovuto("settimana", time(7, 30), 0, "p:c")
        mese = sveglie.Dovuto("mese", time(0, 0), 1, "p:c")

        def utc(*a: int) -> datetime:
            return datetime(*a, tzinfo=UTC)

        def roma_alle(*a: int) -> datetime:
            return datetime(*a, tzinfo=roma)

        casi = (
            # 04:59 UTC = 06:59 a Roma: non ancora; 05:00 UTC = 07:00: dovuto da oggi.
            (giorno, utc(2026, 9, 14, 4, 59), None),
            (giorno, utc(2026, 9, 14, 5, 0), roma_alle(2026, 9, 14, 7, 0)),
            # 23:30 UTC del 14 = 01:30 del 15 a Roma: il periodo del 15 non e' cominciato.
            (giorno, utc(2026, 9, 14, 23, 30), None),
            # Lunedi' 14/09 alle 07:29 di Roma: non ancora (e la settimana prima e' finita).
            (settimana, utc(2026, 9, 14, 5, 29), None),
            (settimana, utc(2026, 9, 14, 5, 30), roma_alle(2026, 9, 14, 7, 30)),
            # Domenica 20/09: ancora la settimana di lunedi' 14 (si recupera dentro il periodo).
            (settimana, utc(2026, 9, 20, 12, 0), roma_alle(2026, 9, 14, 7, 30)),
            # Il 1° alle 00:00 di Roma e' il 30 alle 22:00 UTC.
            (mese, utc(2026, 9, 30, 21, 59), roma_alle(2026, 9, 1, 0, 0)),
            (mese, utc(2026, 9, 30, 22, 0), roma_alle(2026, 10, 1, 0, 0)),
            (mese, utc(2026, 10, 18, 9, 0), roma_alle(2026, 10, 1, 0, 0)),
        )
        for dovuto, adesso, atteso in casi:
            with self.subTest(ogni=dovuto.ogni, adesso=adesso.isoformat()):
                self.assertEqual(sveglie.inizio_periodo_dovuto(dovuto, adesso, roma), atteso)
        # Un mese col giorno dichiarato dopo oggi: il periodo non e' cominciato.
        il_15 = sveglie.Dovuto("mese", time(0, 0), 15, "p:c")
        self.assertIsNone(sveglie.inizio_periodo_dovuto(il_15, utc(2026, 10, 10, 9, 0), roma))

    # 19. ⭐ L'`ExecCondition` sta in OGNI template, con la SUA unit: dal
    #     2026-10-16 `e_dovuto` chiede prima al DB se il processo e' acceso
    #     (l'installer accende tutto), poi il periodo per le calendariali. Una
    #     sveglia senza cancello lavorerebbe a processo spento. E il controllo
    #     non sta nel `comando`, che e' la riga di «Esegui ora» (T-9).
    def test_ogni_template_porta_il_suo_execcondition(self) -> None:
        for s in sveglie.carica_sveglie():
            with self.subTest(unit=s.unit):
                testo = (_TEMPLATE_DIR / f"{s.unit}.service").read_text(encoding="utf-8")
                righe = [r for r in testo.splitlines() if r.startswith("ExecCondition=")]
                self.assertEqual(
                    righe, [f"ExecCondition=__APP_DIR__/bin/run-command.sh e_dovuto {s.unit}"],
                )
                self.assertNotIn("e_dovuto", s.comando)

    # 20. Il `jobname` dichiarato e' la corsia che il comando SCRIVE: se
    #     divergessero, `e_dovuto` non troverebbe mai la corsa e il lavoro
    #     ripartirebbe a ogni sveglia.
    def test_il_jobname_dichiarato_e_quello_che_il_comando_scrive(self) -> None:
        from apps.core.services.presidi_digest import jobname_corsia as corsia_digest
        from apps.core.management.commands.smoke_notturno import JOB_NAME as jobname_smoke
        from apps.vendite.management.commands.run_fatturazione_batch import (
            jobname_corsia as corsia_fatturazione,
        )

        def opzione(comando: tuple[str, ...], nome: str) -> str:
            return comando[comando.index(nome) + 1]

        # ⚠️ Un processo nuovo con `dovuto` va insegnato qui: meglio un rosso
        #    che un jobname non verificato.
        corsia_per_processo = {
            processi.PROCESSO_DIGEST_PRESIDI: lambda c: corsia_digest(opzione(c, "--cadenza")),
            processi.PROCESSO_RUN_FATTURAZIONE_BATCH: lambda c: corsia_fatturazione(opzione(c, "--modalita")),
            processi.PROCESSO_SMOKE_NOTTURNO: lambda c: jobname_smoke,   # una corsia sola
        }
        for s in sveglie.carica_sveglie():
            if s.dovuto is None:
                continue
            with self.subTest(unit=s.unit):
                self.assertIn(s.processo_codice, corsia_per_processo, "insegnami la corsia di questo processo")
                self.assertEqual(s.dovuto.jobname, corsia_per_processo[s.processo_codice](s.comando))

    # 21. Le sveglie calendariali di oggi dichiarano `dovuto`: senza, i test 19
    #     e 20 passerebbero a vuoto.
    def test_le_sveglie_calendariali_dichiarano_dovuto(self) -> None:
        calendariali = {s.unit for s in sveglie.carica_sveglie() if s.dovuto is not None}
        self.assertGreaterEqual(len(calendariali), 3)

    # 22. ⭐ Il TETTO della corsa (dal 2026-10-17). Un `oneshot` senza
    #     `TimeoutStartSec` resta «in avvio» per sempre se si appende, e il
    #     timer non ne lancia un'altra: il 2026-10-16 due sveglie sono rimaste
    #     ferme oltre un'ora su una connessione al DB caduta a meta'. Il tetto
    #     sta SOTTO la tolleranza del processo (la corsa appesa libera il timer
    #     prima che il panorama dica MUTO) e sotto l'ora dopo cui la corsa
    #     risulta «presa e mai chiusa» (lo stesso limite di
    #     `smoke_notturno.TIMEOUT_GIRO_S`). Il drenatore della coda lavori
    #     aspetta il sottoprocesso di «Esegui ora»: il suo tetto sta sopra.
    def test_ogni_oneshot_ha_il_suo_tetto(self) -> None:
        import re

        from apps.core.services.avvio_manuale import TETTO_SOTTOPROCESSO_SECONDI

        ora_della_corsa_aperta = 60
        contratti = leggi_contratti_dal_seed()
        controllate = 0
        for s in sveglie.carica_sveglie():
            testo = (_TEMPLATE_DIR / f"{s.unit}.service").read_text(encoding="utf-8")
            if "Type=oneshot" not in testo.splitlines():
                continue
            controllate += 1
            with self.subTest(unit=s.unit):
                tetti = re.findall(r"^TimeoutStartSec=(\d+)min$", testo, re.MULTILINE)
                self.assertEqual(len(tetti), 1, f"{s.unit}: un TimeoutStartSec=<N>min, uno solo")
                minuti = int(tetti[0])
                self.assertLess(minuti, ora_della_corsa_aperta)
                contratto = contratti.get(s.processo_codice)
                if contratto is not None and contratto["tolleranza_minuti"] is not None:
                    self.assertLess(minuti, contratto["tolleranza_minuti"])
                if s.processo_codice == processi.PROCESSO_DRAINA_CODA_LAVORI:
                    self.assertGreater(minuti * 60, TETTO_SOTTOPROCESSO_SECONDI)
        self.assertGreater(controllate, 0, "nessuna sveglia oneshot: la prova non prova niente")
