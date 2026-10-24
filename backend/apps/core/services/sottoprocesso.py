# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BB — lanciare un sottoprocesso con un TETTO di tempo, senza lasciare
#        orfani: `lancia_con_tetto(argv, tetto_s, env=None, cwd=None)`.
# Note: ⭐ Regola del 2 (2026-10-13, ok Tid). La stessa logica era scritta in
#        `coda_lavori/esegui_processo_handler.py` («Esegui ora»), e serviva
#        identica al giro notturno degli smoke (`smoke_notturno`).
#
#        ⛔ SI UCCIDE IL GRUPPO, NON IL SOLO FIGLIO. Il sottoprocesso parte in
#        una sessione sua (`start_new_session`) e sul tetto si manda `SIGKILL`
#        al suo gruppo: `subprocess.run(timeout=…)` ucciderebbe solo il figlio
#        diretto, e un comando che avesse avviato a sua volta altri processi
#        (un management command, uno script che lancia gli smoke) li lascerebbe
#        orfani e vivi — con «e' stato interrotto» scritto da chi aspettava.
#        Lo stesso colpo parte se e' il CHIAMANTE a essere interrotto mentre
#        aspetta (`KeyboardInterrupt`, segnale): un figlio in sessione propria
#        non lo riceve da solo.
#        ⛔ `argv` e' una LISTA, mai una stringa per la shell: chi chiama
#        risponde di cosa ci mette (S603 dichiarato sulla riga).
# ------------------------------------------------------------
from __future__ import annotations

import os
import signal
import subprocess


# Scopo: manda `SIGKILL` al GRUPPO del sottoprocesso (e' il capo della sua
#        sessione: il gruppo e' lui piu' tutto cio' che ha avviato). Gia'
#        morto = niente da fare.
def _uccidi_gruppo(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


# Scopo: lancia `argv` (LISTA, mai shell) e aspetta al piu' `tetto_s`,
#        catturando stdout e stderr. Torna il processo completato; sul tetto
#        uccide il gruppo, raccoglie l'output arrivato fino a li' e rilancia
#        `TimeoutExpired` con quell'output dentro. Su QUALUNQUE altra
#        interruzione dell'attesa uccide lo stesso il gruppo prima di propagare.
def lancia_con_tetto(
    argv: list[str],
    tetto_s: float,
    *,
    env: dict[str, str] | None = None,
    cwd: str | os.PathLike[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.Popen(  # noqa: S603 — argv in lista, mai shell: lo risponde il chiamante
        argv,
        env=env,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=tetto_s)
    except BaseException as exc:
        _uccidi_gruppo(proc)
        if isinstance(exc, subprocess.TimeoutExpired):
            # Ripresa dopo l'uccisione: `communicate` non perde l'output gia'
            # letto, chiude i pipe e raccoglie il figlio.
            # Lo stub tipizza i campi come `bytes`; con `text=True` sono `str`.
            exc.stdout, exc.stderr = proc.communicate()  # type: ignore[assignment]
        else:
            proc.wait()
        raise
    return subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)
