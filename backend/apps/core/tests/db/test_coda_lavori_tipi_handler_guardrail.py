# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL CANCELLO DEI TIPI DI CODA — ogni tipo di lavoro ATTIVO in
#        `dbops.coda_lavori_tipi` deve avere, a valle, un handler Python
#        registrato che lo esegua.
#
#        PERCHE' ESISTE, e non e' un'ipotesi: e' lo stesso difetto gia' vissuto
#        sui task di pipeline (`test_pipeline_task_handler_guardrail`, 2026-08-18)
#        applicato a un altro paio di lati. Un tipo di coda nasce da DUE pezzi
#        che si applicano SEPARATAMENTE, ciascuno verde in se':
#          · il seed DB, che lo mette a catalogo con un `handler_code`;
#          · l'handler Python, registrato al boot di un `AppConfig.ready()`.
#        Il 2026-09-05 e' arrivato `CHIUSURA_SCADENZE` dal team DB con l'handler
#        ancora da scrivere: il produttore SQL accoda ogni notte, e il drenatore
#        avrebbe alzato `E_CODA_HANDLER_NON_REGISTRATO` su ogni riga.
#
#        ⚠️ E il guasto NON e' rumoroso come sembra: il lavoro fallisce nella
#        coda, non a video. Se nessuno guarda `dbops.vw_coda_lavori_da_guardare`,
#        «le scadenze non si chiudono» si manifesta come uno stato gestionale che
#        resta aperto — cioe' come ASSENZA.
#
#        ⚠️ SI LEGGE IL REGISTRY VIVO, non una copia di comodo: `registered_handlers()`
#        dopo il boot di Django. Uno specchio non prova che l'originale esista.
#
#        ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI):
#        il catalogo dei tipi vive nel database. NON SCRIVE NULLA.
# ------------------------------------------------------------

"""Indice test previsti (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_ogni_tipo_attivo_ha_un_handler
     il cancello vero: un tipo di coda che nessuno sa eseguire.
2. test_nessun_handler_orfano
     il verso opposto: un handler registrato che nessun tipo nomina piu'.
3. test_il_mirror_dei_canali_con_identita_segue_il_database
     ⭐ `_CANALI_CON_IDENTITA` e' un mirror dichiarato di una regola del DB.
     Qui si prova contro la regola vera, non contro se stesso.
4. test_i_vocabolari_dei_filtri_coincidono_con_i_check
     `_CLASSI` e `_CANALI` del service servono a rifiutare un filtro con un 400
     parlante. Un valore in meno e' un 400 su una richiesta buona; uno in piu'
     e' una lista vuota che sembra un dato.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.core.db.processi_repository import (
    _CANALI_CON_IDENTITA,
    _CLASSE_CON_IDENTITA,
)
from apps.core.services.coda_lavori.handler_registry import registered_handlers
from apps.core.services.processi_service import _CANALI, _CLASSI
from apps.core.tests.db_e2e import richiedi_db_provvisto, valori_check


# Scopo: le righe di una query, senza cerimonie (qui si legge soltanto).
def _righe(sql: str) -> list[tuple]:
    with connection.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


# Scopo: i valori ammessi da un CHECK di `dbops.processi`. ⭐ La lettura sta nel
#        building block condiviso (`db_e2e.valori_check`): i due CHECK del
#        progetto scrivono i letterali con cast diversi, e due letture separate
#        ne coprirebbero una ciascuna.
def _valori_check(conname: str) -> set[str]:
    return valori_check("dbops.processi", conname)


class CodaLavoriTipiHandlerGuardrail(TestCase):
    """Il cancello fra il catalogo dei tipi di coda e gli handler Python."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.tipi = _righe(
            "SELECT codice, handler_code FROM dbops.coda_lavori_tipi "
            "WHERE attivo ORDER BY codice"
        )
        cls.registrati = registered_handlers()

    # 1. Il cancello: un tipo attivo che nessuno sa eseguire.
    def test_ogni_tipo_attivo_ha_un_handler(self) -> None:
        self.assertTrue(self.tipi, "nessun tipo attivo: il confronto sarebbe vuoto")
        scoperti = sorted(
            f"{codice} (handler_code={handler!r})"
            for codice, handler in self.tipi
            if handler not in self.registrati
        )
        self.assertEqual(
            scoperti,
            [],
            "tipi di coda ATTIVI senza handler registrato: chi li accoda non lo "
            "sa, e il lavoro fallisce nella coda — dove il fallimento si legge "
            "solo guardando `dbops.vw_coda_lavori_da_guardare`. Registrare "
            "l'handler nel `ready()` dell'app che possiede quel lavoro.",
        )

    # 2. Il verso opposto: un handler vivo che nessun tipo nomina piu'. Non
    #    rompe niente — non lo chiama nessuno — ed e' esattamente per questo che
    #    marcisce senza che nessuno se ne accorga.
    def test_nessun_handler_orfano(self) -> None:
        a_catalogo = {handler for _codice, handler in _righe(
            "SELECT codice, handler_code FROM dbops.coda_lavori_tipi"
        )}
        orfani = sorted(h for h in self.registrati if h not in a_catalogo)
        self.assertEqual(
            orfani,
            [],
            "handler registrati che nessun tipo di coda nomina: o manca il seed, "
            "o l'handler e' un residuo da ritirare.",
        )

    # 3. ⭐ Il mirror contro l'originale. `_CANALI_CON_IDENTITA` serve a mostrare
    #    tre stati invece di due («non ne vuole» non e' «gliene manca uno»), ma
    #    la regola e' del database. Se il DB ne aggiunge un quarto e questo
    #    elenco resta indietro, la schermata dice che un processo non vuole
    #    l'identita' proprio mentre ne sta usando una: un difetto che non da'
    #    errore, e che si vede solo guardando la riga giusta.
    # ⚠️ Si legge dal PRESIDIO, che e' il verso autoritativo: la vista elenca i
    #    canali per cui un processo di dominio senza utente tecnico e' un
    #    problema — cioe' esattamente quelli che l'identita' la vogliono.
    def test_il_mirror_dei_canali_con_identita_segue_il_database(self) -> None:
        definizione = _righe(
            "SELECT pg_get_viewdef("
            "'dbops.vw_processi_dominio_senza_identita'::regclass, true)"
        )[0][0]
        self.assertIn(_CLASSE_CON_IDENTITA, definizione)
        mancanti = [c for c in _CANALI_CON_IDENTITA if f"'{c}'" not in definizione]
        self.assertEqual(
            mancanti,
            [],
            "il mirror nomina canali che il presidio DB non considera: uno dei "
            "due e' invecchiato.",
        )
        # ⛔ E il verso che conta di piu': un canale che il DB pretende e il
        #    mirror non ha. I canali possibili si leggono dal `CHECK` della
        #    tabella, non si riscrivono qui.
        dimenticati = sorted(
            c for c in _valori_check("chk_processi_canale")
            if f"'{c}'" in definizione and c not in _CANALI_CON_IDENTITA
        )
        self.assertEqual(
            dimenticati,
            [],
            "il database pretende l'utente tecnico su un canale che il mirror "
            "non elenca: la schermata mostrerebbe quei processi come «non ne "
            "vuole» mentre ne usano uno.",
        )

    # 4. I due vocabolari con cui il service valida i FILTRI della schermata.
    #    Sono una copia dichiarata dei CHECK: qui si prova che la copia sia
    #    intera. ⚠️ E' gia' successo: `CODA_AUTOMATICA` e' entrato nel CHECK il
    #    2026-09-05 e `_CANALI` ne aveva tre — un filtro legittimo avrebbe
    #    preso un 400.
    def test_i_vocabolari_dei_filtri_coincidono_con_i_check(self) -> None:
        for nome, copia, vincolo in (
            ("_CLASSI", _CLASSI, "chk_processi_classe"),
            ("_CANALI", _CANALI, "chk_processi_canale"),
        ):
            with self.subTest(vocabolario=nome):
                self.assertEqual(
                    set(copia), _valori_check(vincolo),
                    f"{nome} nel service non coincide col CHECK a database",
                )
