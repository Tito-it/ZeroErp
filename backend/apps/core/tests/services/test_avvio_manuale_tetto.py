# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il TETTO del sottoprocesso di «Esegui ora» contro i due limiti da cui
#        dipende, letti dal repo — non ricopiati.
# Note: ⭐ Perche' esiste (brief-db-avvio-manuale-di-un-processo §8.2.3). Il
#        drenatore e' un timer oneshot ogni minuto con `tolleranza_minuti = 10`
#        a catalogo; mentre aspetta il sottoprocesso non drena altro, e se
#        l'attesa supera la tolleranza il panorama dice `MUTO` su un sistema
#        che sta facendo cio' che gli e' stato chiesto. E `STALE_MINUTI_DEFAULT`
#        del reaper, con `max_tentativi = 1`, manderebbe in ERRORE un lavoro il
#        cui comando sta ancora finendo. Il tetto deve stare sotto entrambi, e
#        se uno dei due cambia questo test lo dice — un numero copiato accanto
#        a due numeri che si muovono invecchia in silenzio.
#        ⛔ Nessun database: la tolleranza si legge dal SEED nel repo
#        (`processi.csv`), come fa `test_contratto_liveness_vs_deploy`.
#
# Indice test:
#   1. il tetto sta sotto la META' della tolleranza del drenatore a catalogo
#   2. il tetto sta sotto la soglia del reaper (STALE_MINUTI_DEFAULT)
#   3. la chiave di idempotenza e' per unit
# ------------------------------------------------------------

from __future__ import annotations

from django.test import SimpleTestCase

from apps.core.services.avvio_manuale import (
    TETTO_SOTTOPROCESSO_SECONDI,
    chiave_idempotenza,
)
from apps.core.services.coda_lavori.repository import STALE_MINUTI_DEFAULT
from apps.core.services.processi import PROCESSO_DRAINA_CODA_LAVORI
from apps.core.tests._contratto_processi import leggi_contratti_dal_seed


class TettoSottoprocessoTests(SimpleTestCase):
    # 1. ⭐ Sotto la meta' della tolleranza del drenatore: una corsa che dura
    #    il tetto intero lascia comunque il segno di vita in tempo, e il
    #    badge in topbar non dice «worker fermo» su un worker che lavora.
    def test_sotto_la_meta_della_tolleranza_del_drenatore(self) -> None:
        contratto = leggi_contratti_dal_seed().get(PROCESSO_DRAINA_CODA_LAVORI)
        self.assertIsNotNone(contratto, "il drenatore non e' a catalogo in processi.csv")
        assert contratto is not None
        tolleranza = contratto["tolleranza_minuti"]
        self.assertIsNotNone(tolleranza, "il drenatore non ha un contratto di liveness")
        assert tolleranza is not None
        self.assertLessEqual(
            TETTO_SOTTOPROCESSO_SECONDI, tolleranza * 60 / 2,
            f"il tetto ({TETTO_SOTTOPROCESSO_SECONDI}s) supera la meta' della "
            f"tolleranza del drenatore ({tolleranza} min): un comando al limite "
            f"farebbe dire MUTO al panorama",
        )

    # 2. Sotto il reaper: con `max_tentativi = 1` un lavoro riconosciuto
    #    stantio va DIRETTAMENTE in ERRORE, mentre il comando magari sta
    #    finendo — l'allineamento che il brief §8.2.3 chiede di scrivere.
    def test_sotto_la_soglia_del_reaper(self) -> None:
        self.assertLess(
            TETTO_SOTTOPROCESSO_SECONDI, STALE_MINUTI_DEFAULT * 60,
            f"il tetto ({TETTO_SOTTOPROCESSO_SECONDI}s) non sta sotto il reaper "
            f"({STALE_MINUTI_DEFAULT} min): un lavoro vivo verrebbe chiuso in "
            f"ERRORE mentre il comando gira ancora",
        )

    # 3. Una chiave per unit: due click sulla stessa sveglia sono un lavoro,
    #    due sveglie dello stesso processo sono due.
    def test_chiave_per_unit(self) -> None:
        self.assertEqual(chiave_idempotenza("zeroerp-digest-presidi-settimanale"),
                         "esegui:zeroerp-digest-presidi-settimanale")
        self.assertNotEqual(chiave_idempotenza("a"), chiave_idempotenza("b"))
