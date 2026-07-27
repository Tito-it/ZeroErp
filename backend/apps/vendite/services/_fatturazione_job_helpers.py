# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi dei job handler della coda fatturazione
#        (FATTURAZIONE_GIRO C-3, FATTURAZIONE_NUMERA C-4). Estrazione regola
#        del 2 (ok Tid 2026-07-21): `_parse_competenza` era duplicata nei due
#        handler, identica salvo il codice errore — qui parametrizzato.
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any

from apps.core.services.error_manager import ErrorManager, ServiceError

# Job type dei lavori di fatturazione lanciati dall'app su `dbops.coda_lavori`
# (vocabolario seedato in `dbops.coda_lavori_tipi`). Costanti UNICHE
# (estrazione regola del 2, ok Tid 2026-07-23): prima i letterali vivevano
# duplicati tra l'enqueue delle view (C-3/C-4) e il registry degli esiti del
# cockpit — un refuso in uno dei punti avrebbe silenziosamente scollegato
# l'accodamento dal pannello che lo racconta.
JOB_TYPE_FATTURAZIONE_GIRO = "FATTURAZIONE_GIRO"
JOB_TYPE_FATTURAZIONE_NUMERA = "FATTURAZIONE_NUMERA"
JOB_TYPES_FATTURAZIONE_APP = (
    JOB_TYPE_FATTURAZIONE_GIRO,
    JOB_TYPE_FATTURAZIONE_NUMERA,
)


# Scopo: Normalizza `competenza_mese` (ISO YYYY-MM-DD) al 1° del mese. Errore
#        parlante col codice del job chiamante su valore mancante/invalido
#        (fallimento di dominio registrato in `ultimo_errore`, non eccezione
#        generica — guida Tracciamento).
def parse_competenza_mese(raw: Any, *, error_code: str) -> date:
    ErrorManager.require(
        bool(raw),
        code=error_code,
        message="Payload senza `competenza_mese`.",
    )
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date().replace(day=1)
    except ValueError as exc:
        raise ServiceError(
            code=error_code,
            message="`competenza_mese` non valida (atteso YYYY-MM-DD).",
            detail=str(raw),
        ) from exc


# Numero massimo di gruppi fatturabili selezionabili in una emissione mirata.
# Non e' una regola fiscale: e' il tetto oltre il quale «selezione mirata» non
# vuol piu' dire niente e conviene il giro di massa. Cap esplicito invece che
# silenziosamente illimitato (il payload finisce in un jsonb di coda).
MAX_GRUPPI_EMISSIONE_MIRATA = 200


# Scopo: Normalizza e valida la lista dei GRUPPI FATTURABILI di una emissione
#        mirata. Obiettivo: un perimetro sbagliato deve fallire con un 400
#        parlante, mai degenerare in un perimetro vuoto (= giro di massa) o in
#        chiavi spazzatura che filtrerebbero zero righe senza dirlo.
#        Deduplica preservando l'ordine (la chiave di dedup dei job dipende dal
#        contenuto, non dall'ordine in cui l'operatore ha spuntato le righe:
#        l'ordinamento avviene nel digest).
# Risultato: tupla di chiavi valide, oppure None se il chiamante non ha chiesto
#        alcun perimetro (assenza di criterio = comportamento odierno).
def parse_gruppi(raw: Any, *, error_code: str) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)):
        raise ServiceError(
            code=error_code,
            message="`gruppi` deve essere una lista di chiavi gruppo fatturabile.",
            detail=f"tipo ricevuto: {type(raw).__name__}",
        )
    chiavi: list[str] = []
    for elemento in raw:
        if not isinstance(elemento, str) or not elemento.strip():
            raise ServiceError(
                code=error_code,
                message="`gruppi` contiene una chiave non valida (attesa stringa non vuota).",
                detail=repr(elemento),
            )
        chiave = elemento.strip()
        if chiave not in chiavi:
            chiavi.append(chiave)
    # Lista presente ma vuota: e' una richiesta ambigua («fattura niente»
    # oppure «fattura tutto»?). Si rifiuta invece di indovinare.
    if not chiavi:
        raise ServiceError(
            code=error_code,
            message="`gruppi` non puo` essere una lista vuota: omettere il campo per il giro di massa.",
        )
    if len(chiavi) > MAX_GRUPPI_EMISSIONE_MIRATA:
        raise ServiceError(
            code=error_code,
            message=(
                "Troppi gruppi selezionati per una emissione mirata "
                f"(max {MAX_GRUPPI_EMISSIONE_MIRATA})."
            ),
            detail=f"ricevuti: {len(chiavi)}",
        )
    return tuple(chiavi)


# Scopo: Digest stabile dell'insieme dei gruppi, per la chiave di BUSINESS
#        della coda. Obiettivo: due emissioni mirate sullo stesso mese e scope
#        ma con gruppi DIVERSI devono produrre due job distinti — senza questo,
#        la dedup dei job vivi assorbirebbe la seconda in silenzio, ed e' il
#        difetto piu' insidioso della slice (l'operatore vede «accodato» e non
#        succede nulla). Ordinamento prima dell'hash: lo stesso insieme
#        selezionato in ordine diverso resta lo STESSO lavoro, quindi va
#        deduplicato davvero.
# Risultato: 12 esadecimali (collisione irrilevante: la chiave e' gia' scoped
#        per job_type + mese + scope operatore), o stringa vuota senza gruppi —
#        cosi' la chiave del giro di massa resta identica a prima.
def gruppi_digest(gruppi: tuple[str, ...] | None) -> str:
    if not gruppi:
        return ""
    canonico = "\x1f".join(sorted(gruppi))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:12]
