# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `vuole_identita` — «questo processo vuole un utente tecnico per ogni
#        azienda» — detto UGUALE dalla lista e dal dettaglio di
#        `ProcessiRepository`, sul database vero.
# Note: ⛔ Perche' esiste (2026-09-15). La lista proiettava `vuole_identita`
#        dal backend, il drawer lo RICALCOLAVA da se' con `['PGAGENT',
#        'COMMAND']` — cioe' senza `CODA_AUTOMATICA`, entrato il 05-09 — e
#        nessun test guardava quella copia: sul drawer di
#        `chiusura_scadenze_daily` si leggeva «non gli serve un utente tecnico»
#        mentre ne usa uno per azienda, con l'avviso delle aziende scoperte
#        nascosto. Ora il dettaglio porta lo stesso campo della lista, dalla
#        stessa espressione, e il client lo legge: questo test pinna che le
#        due sedi non possano dire cose diverse, e fissa il caso che il client
#        sbagliava COSTRUENDOLO per nome (contratto del seed), non contando
#        la popolazione di oggi.
#        ⚠️ Il mirror `_CANALI_CON_IDENTITA` contro la regola del DB lo prova
#        gia' `test_coda_lavori_tipi_handler_guardrail` (test 3): qui non si
#        ripete, si prova che le DUE proiezioni lo applichino entrambe.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_lista_e_dettaglio_dicono_lo_stesso_per_ogni_processo
     le due proiezioni di `vuole_identita` non possono divergere.
2. test_i_tre_casi_del_contratto_nel_dettaglio
     ⭐ il caso che il client sbagliava (`CODA_AUTOMATICA` → si') piu' i due
     confinanti (`CODA` → no, `MANUTENZIONE` → no), letti dal dettaglio.
"""

from __future__ import annotations

from unittest import TestCase

from apps.core.db.processi_repository import ProcessiRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto

# Tre processi del SEED (contratto, non fotografia): uno per ogni risposta che
# il modello ammette. Il primo e' quello su cui la copia del client sbagliava.
_CASI_DEL_CONTRATTO = (
    ("chiusura_scadenze_daily", True),   # DOMINIO / CODA_AUTOMATICA: lo sveglia una macchina
    ("FATTURAZIONE_GIRO", False),        # DOMINIO / CODA: lo accoda una persona
    ("digest_presidi", False),           # MANUTENZIONE / COMMAND: nessuna azienda
)


class VuoleIdentitaListaEDettaglioTests(TestCase):
    """Lista e dettaglio dei processi: una sola risposta a «vuole un'identita'?»."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.repo = ProcessiRepository()

    # 1. Per OGNI processo a catalogo il dettaglio dice cio' che dice la lista.
    #    ⚠️ Si asserisce che la lista non sia vuota: su un database senza seed
    #    il confronto passerebbe a vuoto, e un verde per sottrazione non prova
    #    niente.
    def test_lista_e_dettaglio_dicono_lo_stesso_per_ogni_processo(self) -> None:
        righe, totale = self.repo.list_processi(limit=500, offset=0)
        self.assertTrue(righe, "nessun processo a catalogo: il confronto sarebbe vuoto")
        self.assertEqual(len(righe), totale, "la pagina non copre il catalogo intero")
        divergenti = []
        for riga in righe:
            dettaglio = self.repo.get_processo(riga["codice"])
            self.assertIsNotNone(dettaglio, f"dettaglio assente per {riga['codice']}")
            assert dettaglio is not None
            self.assertIn("vuole_identita", dettaglio, riga["codice"])
            if bool(dettaglio["vuole_identita"]) != bool(riga["vuole_identita"]):
                divergenti.append(riga["codice"])
        self.assertEqual(
            divergenti, [],
            "processi per cui lista e dettaglio rispondono diversamente a "
            "«vuole un utente tecnico?»: le due proiezioni devono venire dalla "
            "stessa espressione (`_SQL_VUOLE_IDENTITA`).",
        )

    # 2. ⭐ I tre casi del contratto, per nome. Un codice assente e' un difetto
    #    (schema presente, riga di seed assente), non una condizione d'ambiente.
    def test_i_tre_casi_del_contratto_nel_dettaglio(self) -> None:
        for codice, atteso in _CASI_DEL_CONTRATTO:
            with self.subTest(processo=codice):
                dettaglio = self.repo.get_processo(codice)
                self.assertIsNotNone(dettaglio, f"processo di seed assente: {codice}")
                assert dettaglio is not None
                self.assertIs(
                    bool(dettaglio["vuole_identita"]), atteso,
                    f"{codice} ({dettaglio['classe']}/{dettaglio['canale']}): "
                    f"vuole_identita atteso {atteso}",
                )
