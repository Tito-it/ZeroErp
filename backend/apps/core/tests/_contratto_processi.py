# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Supporto ai test che confrontano il DICHIARATO di deploy
#        (`backend/deploy/sveglie.json`) con il CONTRATTO di liveness dei
#        processi (`dbops.processi.tolleranza_minuti` / `segno_di_vita`).
#        Due cose: la lettura del contratto dal SEED nel repo, e la lettura di
#        un `OnCalendar` di systemd come «intervallo massimo fra due corse».
# Note: ⛔ SI LEGGE IL SEED, NON IL DATABASE. I test Django di questo repo non
#        parlano con un DB reale (regola `SimpleTestCase`, AGENTS.md), e il
#        contratto ha una sede nel repo: `80_data/sql/dbops/processi.csv`, il
#        mirror `loadUpdateData` da cui il catalogo vivo viene ricaricato a ogni
#        migrate. Confrontare due file del repo e' esattamente il presidio che
#        serve: se il deploy viola il contratto, lo dice la CI, non l'host.
#        ⚠️ Il parser di `OnCalendar` copre le SOLE forme in uso nel progetto, e
#        su una forma che non conosce SOLLEVA. Un parser «generoso» che
#        restituisse un numero a caso passerebbe verde su un timer che nessuno
#        ha capito — il verde per sottrazione, di nuovo.
# ------------------------------------------------------------

from __future__ import annotations

import re
from typing import TypedDict

from apps.core.services.sveglie import Dovuto
from apps.core.tests._seed_csv import SEED_DIR, RigaSeed, seed_csv


SEED_PROCESSI = SEED_DIR / "dbops/processi.csv"

# Vocabolario del seed (mirror dei CHECK `chk_processi_canale` / `chk_processi_segno_di_vita`).
CANALE_COMMAND = "COMMAND"
SEGNO_GIORNALE = "GIORNALE"
SEGNO_SESSIONE = "SESSIONE"


# Scopo: una riga del contratto come sta nel seed. `tolleranza_minuti` e'
#        `None` dove il CSV dice `NULL` («non si presidia»).
class ContrattoSeed(TypedDict):
    codice: str
    canale: str
    attivo: bool
    tolleranza_minuti: int | None
    segno_di_vita: str


# Scopo: i contratti di liveness per codice, letti dal seed del catalogo.
# ⛔ FAIL-LOUD sulla forma: se una colonna sparisce dal CSV il test che ci
#    poggia deve diventare rosso, non leggere `None` ovunque e passare.
# ⭐ Il seed si legge dal BB `seed_csv`, che da' `None` dove il caricatore
#    scrive NULL (il token `NULL` della cella): niente token riconosciuto a mano. Una
#    cella VUOTA resta `''`, come la scriverebbe il loader, e su una colonna
#    intera fa rosso in `int()` invece di passare per «non si presidia».
def leggi_contratti_dal_seed() -> dict[str, ContrattoSeed]:
    righe = seed_csv(SEED_PROCESSI)
    if not righe:
        raise AssertionError(f"{SEED_PROCESSI}: seed vuoto")
    attese = {"codice", "canale", "attivo", "tolleranza_minuti", "segno_di_vita"}
    mancanti = attese - set(righe[0])
    if mancanti:
        raise AssertionError(
            f"{SEED_PROCESSI}: colonne mancanti nel seed: {sorted(mancanti)}"
        )
    contratti: dict[str, ContrattoSeed] = {}
    for riga in righe:
        codice = _obbligatoria(riga, "codice")
        tolleranza = riga["tolleranza_minuti"]
        contratti[codice] = ContrattoSeed(
            codice=codice,
            canale=_obbligatoria(riga, "canale"),
            attivo=_obbligatoria(riga, "attivo").strip().lower() in ("t", "true", "1"),
            tolleranza_minuti=None if tolleranza is None else int(tolleranza),
            segno_di_vita=_obbligatoria(riga, "segno_di_vita").strip(),
        )
    return contratti


# Scopo: una colonna NOT NULL del seed: NULL qui e' un seed sbagliato, non un
#        valore da leggere.
def _obbligatoria(riga: RigaSeed, campo: str) -> str:
    valore = riga[campo]
    if valore is None:
        raise AssertionError(f"{SEED_PROCESSI}: `{campo}` NULL nella riga {riga}")
    return valore


# Le forme di `OnCalendar` in uso nel progetto, e quanto puo' passare AL
# MASSIMO fra due corse consecutive. Ordine: dalla piu' specifica alla piu'
# generale, e OGNI regex e' ancorata: `*:0/5` non deve combaciare con una forma
# che non e' la sua.
_GIORNI_SETTIMANA = "Mon|Tue|Wed|Thu|Fri|Sat|Sun"
_MINUTI_ORA = 60
_MINUTI_GIORNO = 24 * _MINUTI_ORA
# ⚠️ Il giorno del mese si accetta solo fino al 28: `*-*-29`, `-30`, `-31` in
#    systemd SALTANO i mesi che quel giorno non ce l'hanno, e l'intervallo
#    massimo non e' piu' «un mese» — e' quanti mesi corti si mettono in fila.
#    Meglio non capire che rispondere un numero sbagliato.
_ULTIMO_GIORNO_SICURO = 28
_FORME: tuple[tuple[re.Pattern[str], int | None], ...] = (
    # `*:0/N`  → ogni N minuti, dentro l'ora.
    (re.compile(r"^\*:0/(\d+)$"), None),
    # `*:MM`   → una volta all'ora, al minuto MM (la sveglia delle sveglie
    #           calendariali con `dovuto`, dal 2026-10-09).
    (re.compile(r"^\*:[0-5]\d$"), _MINUTI_ORA),
    # `Mon *-*-* HH:MM` → una volta a settimana.
    # ⚠️ Gruppo NON catturante: l'unico gruppo che il parser legge e' quello
    #    del passo (`*:0/N`) o del giorno del mese (`*-*-DD`).
    (re.compile(rf"^(?:{_GIORNI_SETTIMANA}) \*-\*-\* \d{{2}}:\d{{2}}$"), 7 * _MINUTI_GIORNO),
    # `*-*-* HH:MM` → una volta al giorno.
    (re.compile(r"^\*-\*-\* \d{2}:\d{2}$"), _MINUTI_GIORNO),
    # `*-*-DD HH:MM` → una volta al mese; il gap massimo e' 31 giorni (lug→ago).
    (re.compile(r"^\*-\*-(\d{2}) \d{2}:\d{2}$"), 31 * _MINUTI_GIORNO),
)


# Scopo: l'intervallo MASSIMO, in minuti, fra due corse consecutive di un
#        timer con questo `OnCalendar`. E' il numero da confrontare con la
#        tolleranza: se e' piu' grande, il deploy promette meno del contratto.
# ⛔ Solleva su una forma sconosciuta: e' il contratto di questo helper.
# ⚠️ `*:0/N` vuol dire «i minuti 0, N, 2N… DENTRO l'ora», poi si ricomincia
#    al minuto 0 dell'ora dopo: con N che non divide 60 l'ultimo gap e' piu'
#    corto, e il massimo resta N.
# ⛔ Con N >= 60 systemd RIFIUTA la specifica («Failed to parse calendar
#    specification», verificato su systemd 257 il 2026-10-09): il timer non
#    parte affatto. Fino a quel giorno questo parser rispondeva «ogni ora»
#    (`min(N, 60)`) e il suo test lo fissava: un presidio che avrebbe dato
#    verde a un unit che sull'host non si carica. La sveglia oraria si scrive
#    `*:MM` (forma sopra).
def intervallo_massimo_minuti(oncalendar: str) -> int:
    espressione = oncalendar.strip()
    for regex, minuti in _FORME:
        m = regex.match(espressione)
        if not m:
            continue
        if minuti is None:
            passo = int(m.group(1))
            if passo <= 0:
                raise ValueError(f"OnCalendar con passo non positivo: {oncalendar!r}")
            if passo >= _MINUTI_ORA:
                raise ValueError(
                    f"OnCalendar {oncalendar!r}: systemd rifiuta un passo dei minuti "
                    f">= {_MINUTI_ORA} (il timer non partirebbe); ogni ora si scrive '*:MM'"
                )
            return passo
        if m.groups() and int(m.group(1)) > _ULTIMO_GIORNO_SICURO:
            raise ValueError(
                f"OnCalendar mensile oltre il giorno {_ULTIMO_GIORNO_SICURO}: "
                f"{oncalendar!r} salta i mesi corti e l'intervallo non e' piu' un mese"
            )
        return minuti
    raise ValueError(
        f"forma di OnCalendar non conosciuta da questo parser: {oncalendar!r} — "
        f"insegnargliela in _FORME (con il suo intervallo), non allargare una regex"
    )


# I minuti di un periodo di `dovuto` (sveglie calendariali): il mese al suo
# massimo, come per gli OnCalendar mensili.
_MINUTI_PERIODO_DOVUTO = {
    "giorno": _MINUTI_GIORNO,
    "settimana": 7 * _MINUTI_GIORNO,
    "mese": 31 * _MINUTI_GIORNO,
}


# Scopo: l'intervallo MASSIMO fra due corse di una SVEGLIA. Senza `dovuto` e'
#        quello del suo `OnCalendar`; con `dovuto` (brief un-solo-fuso-aziendale
#        T-9) il timer si sveglia spesso ma il lavoro si fa una volta per
#        periodo aziendale: il periodo piu' il passo della sveglia.
# ⛔ Leggere il solo `OnCalendar` di una sveglia calendariale direbbe «ogni
#    ora» a un digest settimanale: il confronto col contratto passerebbe
#    raccontando una cosa falsa.
def intervallo_massimo_sveglia(oncalendar: str, dovuto: Dovuto | None) -> int:
    passo = intervallo_massimo_minuti(oncalendar)
    if dovuto is None:
        return passo
    return _MINUTI_PERIODO_DOVUTO[dovuto.ogni] + passo
