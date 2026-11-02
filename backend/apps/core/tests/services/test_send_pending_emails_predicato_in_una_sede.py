# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello su «che cosa e' in coda» per le email: il predicato vive
#        UNA volta, in `config.vw_email_in_coda`, e il cron la LEGGE — non la
#        ricopia. Gira SENZA database: legge il sorgente del command.
# ------------------------------------------------------------

"""Indice test previsti.

1. test_il_cron_legge_la_vista_e_non_la_tabella
   `send_pending_emails` seleziona da `config.vw_email_in_coda`; nessuna
   `SELECT ... FROM config.email_log` nel corpo del giro.
2. test_il_cron_non_ricopia_il_predicato_dello_stato
   Nessun frammento del predicato di lettura (`stato = 'PENDING'`, `stato IN (`,
   `tentativi < max_tentativi`, `prossimo_tentativo IS NULL` / `<=`) nel
   sorgente: se ricompare, e' una seconda sede.

⛔ PERCHE' ESISTE. Fino al 2026-09-11 la `WHERE` stava nel command, e il
   presidio proposto al DB la ricopiava «PENDING o RETRY» omettendo i `FAILED`
   ripescabili — due sedi dello stesso predicato, divergenti prima di nascere
   (brief `brief-db-quattro-processi-senza-presidio.md` §10.1 D3). La vista e'
   la sede; questo test vieta che il command se ne faccia una propria.
⚠️ Il test guarda il TESTO del sorgente e non il comportamento, di proposito:
   il comportamento sotto le due forme e' identico oggi, ed e' proprio per
   questo che una copia non fallirebbe da nessuna parte.
"""

import re
from importlib.util import find_spec
from pathlib import Path
from unittest import TestCase

# ⚠️ Il percorso si chiede all'import system, non si conta a mano: un
#    `parents[N]` sbagliato non fallisce nel modo giusto (l'ha appena fatto).
_SPEC = find_spec("apps.core.management.commands.send_pending_emails")
assert _SPEC is not None and _SPEC.origin is not None
_COMMAND = Path(_SPEC.origin)

# I frammenti che compongono il predicato della vista. Uno solo di questi nel
# command basta a dire che qualcuno ha ricominciato a decidere qui.
# ⚠️ Stretti sul PREDICATO DI LETTURA, di proposito: `prossimo_tentativo` da
#    solo comparirebbe legittimamente in una scrittura (`SET prossimo_tentativo`
#    del backoff), e un cancello che boccia il caso legittimo viene spento.
_FRAMMENTI_VIETATI = (
    r"stato\s*=\s*'PENDING'",
    r"stato\s+IN\s*\(",
    r"tentativi\s*<\s*max_tentativi",
    r"prossimo_tentativo\s+IS\s+NULL",
    r"prossimo_tentativo\s*<=",
)


class SendPendingEmailsPredicatoInUnaSedeTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.sorgente = _COMMAND.read_text(encoding="utf-8")
        # Si guarda il solo CODICE: i commenti raccontano la storia del
        # predicato e devono poterlo nominare.
        cls.codice = "\n".join(
            riga for riga in cls.sorgente.splitlines()
            if not riga.lstrip().startswith("#")
            and not riga.lstrip().startswith("--")
        )

    # Scopo: la sede e' la vista; la tabella non compare in nessuna SELECT.
    def test_il_cron_legge_la_vista_e_non_la_tabella(self) -> None:
        self.assertIn("FROM config.vw_email_in_coda", self.codice)
        self.assertNotRegex(
            self.codice, r"FROM\s+config\.email_log\b",
            "il command seleziona dalla tabella: il predicato «in coda» torna "
            "ad avere due sedi (la vista e questa SELECT)",
        )

    # Scopo: nessun pezzo del predicato ricompare nel codice del command.
    def test_il_cron_non_ricopia_il_predicato_dello_stato(self) -> None:
        for frammento in _FRAMMENTI_VIETATI:
            with self.subTest(frammento=frammento):
                self.assertIsNone(
                    re.search(frammento, self.codice),
                    f"{frammento!r} nel codice di send_pending_emails: il "
                    f"predicato «in coda» e' di config.vw_email_in_coda",
                )
