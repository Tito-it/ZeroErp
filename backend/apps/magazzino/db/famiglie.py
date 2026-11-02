# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LE DUE FAMIGLIE DEL DOCUMENTO INTERNO di magazzino — inventario e
#        rettifica — come UNA configurazione letta da repository, service e
#        view. Q-1 del piano (decisa da Tid il 2026-09-18): una implementazione
#        parametrica, non due copie.
# Note: ⭐ Il database le ha gia' fatte una famiglia: un guard di transizione
#       parametrico (`trgfn_documento_interno_guard_transizione`, TG_ARGV), un
#       guard di righe parametrico, due `fn_posta_*` con la stessa forma, la
#       stessa matrice `DRAFT → CONFIRM → POSTED | CANCEL`. Le differenze sono
#       TRE, tutte di dato: la riga porta `qta_contata >= 0` (inventario) o
#       `qta_delta <> 0` + `motivo` (rettifica); l'inventario ha il PIANO; la
#       sorgente si chiama `INVENTARIO_RIGA` / `RETTIFICA_RIGA`. Sono i campi di
#       questo dataclass, e null'altro.
#
#       ⛔ Vive in `db/` e non in `services/`: i nomi di tabella e di colonna
#       sono un fatto di ACCESSO AI DATI (stampo `vendite.db.note_repositories`),
#       e un service non puo' importare da `api/` ne' un repository da
#       `services/` senza invertire gli anelli.
#
#       ⚠️ Gli identificatori finiscono INTERPOLATI nell'SQL del repository:
#       passano tutti dalla regex di `__post_init__` (stampo
#       `PartitionedNoteRepository`), cosi' un refuso da refactor si ferma
#       all'import e non a runtime, in una query.
# ------------------------------------------------------------

from __future__ import annotations

import re
from dataclasses import dataclass

from apps.config.sorgenti import SORGENTE_INVENTARIO_RIGA, SORGENTE_RETTIFICA_RIGA

_IDENT = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?$")


# Scopo: la configurazione di UNA famiglia di documento interno.
@dataclass(frozen=True)
class FamigliaDocumentoInterno:
    codice: str                    # "inventari" | "rettifiche" — il segmento di URL
    singolare: str                 # "inventario" | "rettifica" — per messaggi e chiavi
    tabella: str                   # "magazzino.inventari"
    tabella_righe: str             # "magazzino.inventari_righe"
    fk_riga: str                   # "inventario_id" — la colonna di riga verso la testata
    col_stato: str                 # "stato_mag_inventario"
    fn_posta: str                  # "magazzino.fn_posta_inventario"
    # La capability del dettaglio (R-1 del brief 2-bis): l'INVOLUCRO della
    # famiglia, non il corpo parametrico — `script.fn_available_actions_
    # documento_interno(p_famiglia, id)` vuole il nome della famiglia come
    # valore, e un valore in piu' da passare e' un valore in piu' da
    # sbagliare. L'involucro lo sa gia' (doc: «i due involucri, che sono
    # cio' che il backend chiama»).
    fn_capability: str             # "script.fn_available_actions_inventario"
    sorgente_codice_interno: str   # "INVENTARIO_RIGA" — `config.sorgenti`
    lista_codice: str              # "magazzino.inventari" — `ui.lista_definizione`
    lista_righe_codice: str        # "magazzino.inventario_righe"
    col_qta: str                   # "qta_contata" | "qta_delta"
    ha_piano: bool                 # solo l'inventario ha `fn_inventario_piano`
    ha_descrizione: bool           # solo `inventari` ha la colonna `descrizione`
    con_motivo: bool               # solo la riga di rettifica porta `motivo`
    guard_riga_uniq: str | None    # UNIQUE di posizione (R-2), solo inventari

    def __post_init__(self) -> None:
        for nome in (
            "tabella", "tabella_righe", "fk_riga", "col_stato", "fn_posta", "col_qta",
            "fn_capability",
        ):
            valore = getattr(self, nome)
            if not _IDENT.match(valore):
                raise ValueError(f"FamigliaDocumentoInterno.{nome}: identificatore non valido {valore!r}")


INVENTARI = FamigliaDocumentoInterno(
    codice="inventari",
    singolare="inventario",
    tabella="magazzino.inventari",
    tabella_righe="magazzino.inventari_righe",
    fk_riga="inventario_id",
    col_stato="stato_mag_inventario",
    fn_posta="magazzino.fn_posta_inventario",
    fn_capability="script.fn_available_actions_inventario",
    sorgente_codice_interno=SORGENTE_INVENTARIO_RIGA,
    lista_codice="magazzino.inventari",
    lista_righe_codice="magazzino.inventario_righe",
    col_qta="qta_contata",
    ha_piano=True,
    ha_descrizione=True,
    con_motivo=False,
    guard_riga_uniq="uq_mag_inventari_righe_posizione",
)

RETTIFICHE = FamigliaDocumentoInterno(
    codice="rettifiche",
    singolare="rettifica",
    tabella="magazzino.rettifiche",
    tabella_righe="magazzino.rettifiche_righe",
    fk_riga="rettifica_id",
    col_stato="stato_mag_rettifiche",
    fn_posta="magazzino.fn_posta_rettifica",
    fn_capability="script.fn_available_actions_rettifica",
    sorgente_codice_interno=SORGENTE_RETTIFICA_RIGA,
    lista_codice="magazzino.rettifiche",
    lista_righe_codice="magazzino.rettifica_righe",
    col_qta="qta_delta",
    ha_piano=False,
    ha_descrizione=False,
    con_motivo=True,
    # C14: due delta dati NON sono due letture — nessun UNIQUE di posizione.
    guard_riga_uniq=None,
)

# Le famiglie, per codice di URL. ⛔ Chiuso: una terza famiglia (il
# trasferimento) e' una riga qui e la sua config, non un `if` altrove.
FAMIGLIE: dict[str, FamigliaDocumentoInterno] = {
    INVENTARI.codice: INVENTARI,
    RETTIFICHE.codice: RETTIFICHE,
}
