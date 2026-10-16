# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il deploy non puo' VIOLARE il contratto di liveness in silenzio.
#        Il contratto (`dbops.processi.tolleranza_minuti`, «se sto bene lascio
#        un segno almeno ogni N minuti») e la cadenza (`OnCalendar` in
#        `deploy/sveglie.json`, «come il deploy lo onora») sono due sedi per
#        due fatti — e proprio per questo vanno confrontate: un timer piu' lento
#        della tolleranza fa suonare `MUTO` a ogni giro su un processo sano, che
#        e' il modo piu' rapido di far smettere di guardare un presidio.
#        Gira SENZA database: due file del repo (brief
#        `brief-db-quattro-processi-senza-presidio.md` §10.7 punto 3).
# ------------------------------------------------------------

"""Indice test previsti.

1. test_ogni_timer_rispetta_il_contratto_del_suo_processo
   Per ogni sveglia di forma `timer` il cui processo ha un contratto nel seed,
   l'intervallo massimo fra due corse e' ≤ `tolleranza_minuti`: quello
   dell'`OnCalendar`, o — per le sveglie calendariali (`dovuto`, dal
   2026-10-09) — il periodo aziendale piu' il passo della sveglia.
2. test_segno_di_vita_sessione_e_forma_servizio_si_implicano
   Un processo con `segno_di_vita = SESSIONE` ha SOLO sveglie di forma
   `servizio`, e un `servizio` sempre acceso ha SOLO contratti `SESSIONE`: il
   segno di vita di chi non ha una cadenza non puo' essere il giornale.
3. test_ogni_command_con_contratto_ha_almeno_una_sveglia
   Un contratto senza nessuna sveglia e' una promessa che nessun host onora:
   il panorama direbbe `MAI_PARTITO` su ogni installazione. (Fino al
   2026-10-16 si chiedeva una sveglia `abilita: true`; oggi l'installer
   accende ogni sveglia, e se il processo lavora lo dice il DB — un processo
   spento il panorama lo chiama `SPENTO`, non `MAI_PARTITO`.)
4. test_il_parser_conosce_ogni_oncalendar_del_dichiarato
   Ogni `OnCalendar` in uso e' una forma che il parser sa leggere — se il
   test 1 salta una sveglia perche' non la capisce, e' qui che si vede.
5. test_il_parser_fa_i_conti_giusti_e_rifiuta_cio_che_non_sa
   L'aritmetica del parser sui casi che ingannano: `*:0/90` systemd lo
   RIFIUTA (passo dei minuti >= 60: il timer non parte — fino al 2026-10-09
   qui si diceva «gira ogni ora»); `*-*-31` salta i mesi corti e non e' «un
   mese»; una forma ignota solleva, non stima.

⚠️ SUL LIMITE che il test 1 NON copre, e va detto: il contratto ha la grana
   del PROCESSO, la sveglia quella della CORSIA. Su `digest_presidi` (due
   corsie, 24h e 7g) il contratto e' 11520 e la corsia giornaliera lo rispetta
   con otto giorni di margine — cioe' il test non puo' dire che la giornaliera
   sia «in ritardo» prima di otto giorni. E' il limite accettato da Tid il
   2026-09-11 (brief §11.2), non una dimenticanza del test.
"""

from django.test import SimpleTestCase

from apps.core.services import sveglie
from apps.core.tests._contratto_processi import (
    CANALE_COMMAND,
    SEGNO_SESSIONE,
    intervallo_massimo_minuti,
    intervallo_massimo_sveglia,
    leggi_contratti_dal_seed,
)


class ContrattoLivenessVsDeployTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        sveglie.carica_sveglie.cache_clear()
        cls.sveglie = sveglie.carica_sveglie()
        cls.contratti = leggi_contratti_dal_seed()

    # 1. ⭐ IL CONFRONTO. Solo dove c'e' un contratto: un processo con
    #    tolleranza NULL non promette niente, e non c'e' nulla da violare.
    def test_ogni_timer_rispetta_il_contratto_del_suo_processo(self) -> None:
        confrontate = 0
        for s in self.sveglie:
            if not s.e_timer:
                continue
            contratto = self.contratti.get(s.processo_codice)
            if contratto is None or contratto["tolleranza_minuti"] is None:
                continue
            assert s.oncalendar is not None  # e_timer lo garantisce
            with self.subTest(unit=s.unit):
                intervallo = intervallo_massimo_sveglia(s.oncalendar, s.dovuto)
                self.assertLessEqual(
                    intervallo, contratto["tolleranza_minuti"],
                    f"{s.unit}: OnCalendar {s.oncalendar!r} lascia passare fino "
                    f"a {intervallo} minuti fra due corse, ma il contratto di "
                    f"{s.processo_codice} e' {contratto['tolleranza_minuti']}: "
                    f"il panorama direbbe MUTO su un processo sano",
                )
            confrontate += 1
        # ⛔ Anti verde-per-sottrazione: se nessuna sveglia arriva al confronto,
        #    il test sopra passa senza aver verificato niente.
        self.assertGreater(confrontate, 0, "nessun timer con contratto: il test gira a vuoto")

    # 2. Il segno di vita segue la forma della sveglia, nei due versi.
    def test_segno_di_vita_sessione_e_forma_servizio_si_implicano(self) -> None:
        for s in self.sveglie:
            contratto = self.contratti.get(s.processo_codice)
            if contratto is None:
                continue
            with self.subTest(unit=s.unit):
                e_sessione = contratto["segno_di_vita"] == SEGNO_SESSIONE
                e_servizio = s.forma == sveglie.FORMA_SERVIZIO
                self.assertEqual(
                    e_sessione, e_servizio,
                    f"{s.unit}: forma {s.forma!r} ma segno_di_vita "
                    f"{contratto['segno_di_vita']!r} a catalogo — un servizio "
                    f"sempre acceso non ha corse da lasciare sul giornale, e un "
                    f"timer non ha una sessione da tenere aperta",
                )

    # 3. Un contratto che nessuna sveglia onora e' `MAI_PARTITO` ovunque.
    def test_ogni_command_con_contratto_ha_almeno_una_sveglia(self) -> None:
        for codice, contratto in self.contratti.items():
            if contratto["canale"] != CANALE_COMMAND or contratto["tolleranza_minuti"] is None:
                continue
            with self.subTest(processo=codice):
                self.assertTrue(
                    sveglie.sveglie_di_processo(codice),
                    f"{codice} ha un contratto di {contratto['tolleranza_minuti']} "
                    f"minuti ma nessuna sveglia in sveglie.json",
                )

    # 4. Ogni cadenza in uso e' leggibile: il parser solleva su cio' che non
    #    conosce, e qui lo si fa sollevare PRIMA che il test 1 salti qualcosa.
    def test_il_parser_conosce_ogni_oncalendar_del_dichiarato(self) -> None:
        for s in self.sveglie:
            if s.oncalendar is None:
                continue
            with self.subTest(unit=s.unit, oncalendar=s.oncalendar):
                self.assertGreater(intervallo_massimo_minuti(s.oncalendar), 0)

    # 5. ⛔ IL PARSER SI PROVA SUI CASI CHE INGANNANO, non solo su quelli in uso:
    #    un helper di presidio che non ha mai visto rosso non e' ancora un
    #    presidio. `*:0/90` e `*-*-31` sono i due errori che un parser
    #    «ragionevole» farebbe in silenzio.
    def test_il_parser_fa_i_conti_giusti_e_rifiuta_cio_che_non_sa(self) -> None:
        casi = {
            "*:0/1": 1,
            "*:0/7": 7,            # non divide 60: il gap massimo resta 7
            "*:0/45": 45,          # minuti 0 e 45: gap 45 e 15
            "*:00": 60,            # la sveglia oraria delle sveglie calendariali
            "*:30": 60,
            "*-*-* 07:00": 1440,
            "Mon *-*-* 07:30": 10080,
            "*-*-01 02:00": 44640, # lug→ago: 31 giorni
            "*-*-28 02:00": 44640,
        }
        for oncalendar, atteso in casi.items():
            with self.subTest(oncalendar=oncalendar):
                self.assertEqual(intervallo_massimo_minuti(oncalendar), atteso)
        # ⛔ `*:0/60` e `*:0/90`: systemd li rifiuta (verificato su systemd 257),
        #    quindi il parser pure — non «ogni ora».
        for ignota in ("*-*-29 02:00", "*-*-31 02:00", "*:0/0", "*:0/60", "*:0/90", "*:0/5,30",
                       "*:60", "Mon 07:30", ""):
            with self.subTest(oncalendar=ignota):
                with self.assertRaises(ValueError):
                    intervallo_massimo_minuti(ignota)
