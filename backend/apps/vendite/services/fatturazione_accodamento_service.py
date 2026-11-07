# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accoda i lavori di fatturazione chiesti dall'applicazione — il giro
#        (C-3) e la numerazione di perimetro (C-4) — UNO PER AZIENDA (BE10 a di
#        brief-db-revisione-dbops, decisione di Tid del 2026-11-07).
# Note: ⛔ Un lavoro OPERATORE nasce dentro un'azienda: dal giro 5a la porta
#        `fn_accoda_lavoro` rifiuta lo scope senza emittente attivo
#        (`E_CODA_LAVORO_SENZA_EMITTENTE`), e un lavoro che copre più aziende
#        non esiste. Dalla modalità globale («Tutti gli emittenti») si accoda
#        quindi un lavoro per ciascuna azienda dell'operatore; con un'azienda
#        scelta, uno solo. È la stessa forma del giro notturno
#        (`accoda_giri_fatturazione`), e la stessa chiave di dedup.
#        ⭐ Una SELEZIONE (gruppi spuntati, lotti spuntati) si divide per
#        azienda: ogni lavoro porta le sole righe della sua. Una riga di cui
#        non si trova l'azienda è un 400 parlante QUI, non un lavoro che
#        fallisce un minuto dopo nel drenatore.
#        ⚠️ Tutto o niente: il chiamante gira in una transazione
#        (`handle_post_json`), quindi se il terzo accodamento fallisce i primi
#        due si annullano con lui. Un gesto solo, un esito solo.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from apps.core.services.coda_lavori.repository import (
    ORIGINE_API,
    RUN_AS_OPERATORE,
    CodaLavoriRepository,
)
from apps.core.services.coda_lavori.scope import (
    aziende_della_richiesta,
    scope_in_azienda,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import E_VALIDATION_INPUT
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.vendite.services._fatturazione_job_helpers import (
    chiave_idempotenza_giro,
    corsia_del_giro,
    insieme_digest,
)

# Quante righe non attribuite si nominano nel `detail`: il resto si conta.
_MAX_RIGHE_NEL_DETTAGLIO = 10


# Scopo: Assegna ogni riga della selezione all'azienda (PK) a cui appartiene.
#        `azienda_di` è `{riga: [soggetto_ruolo_id, ...]}` come lo dà il
#        repository; `pk_da_sr` traduce il ruolo nella PK delle aziende di chi
#        accoda. Ritorna `{pk: [righe nell'ordine chiesto]}`.
# ⛔ Una riga senza azienda (o col ruolo NULL), con più di un'azienda, o con un'azienda fuori da
#    quelle di chi accoda, NON si indovina: 400 con le righe nominate. Fuori
#    perimetro e inesistente si leggono uguali, come in ogni altro posto.
def _assegna(
    righe: Sequence[Any],
    azienda_di: Mapping[Any, Sequence[int | None]],
    pk_da_sr: Mapping[int, int],
    *,
    nome: str,
) -> dict[int, list[Any]]:
    per_azienda: dict[int, list[Any]] = {}
    orfane: list[Any] = []
    for riga in righe:
        srs = list(azienda_di.get(riga, ()))
        # Un ruolo None (riga senza azienda) e' orfana come una con due.
        unico = srs[0] if len(srs) == 1 else None
        pk = None if unico is None else pk_da_sr.get(unico)
        if pk is None:
            orfane.append(riga)
            continue
        per_azienda.setdefault(pk, []).append(riga)
    ErrorManager.require(
        not orfane,
        code=E_VALIDATION_INPUT,
        message=(
            f"{len(orfane)} {nome} della selezione non si trovano fra quelli che "
            "puoi lavorare in questa competenza: ricarica l'elenco e riprova."
        ),
        detail=", ".join(str(r) for r in orfane[:_MAX_RIGHE_NEL_DETTAGLIO]),
    )
    return per_azienda


# Scopo: La selezione divisa per azienda: una voce `(azienda, gruppi, lotti)`
#        per ogni azienda che ha lavoro, nell'ordine di `aziende`. Senza
#        selezione (atto di mese) ogni azienda ha il suo lavoro, con il
#        perimetro intero.
# ⚠️ Un'azienda senza righe nella selezione non riceve un lavoro: una
#    selezione è un perimetro NOMINALE, e accodare un giro vuoto per un'azienda
#    che nessuno ha toccato sarebbe un lavoro che non è stato chiesto.
def ripartisci_per_azienda(
    aziende: Sequence[Mapping[str, Any]],
    *,
    competenza: date,
    gruppi: Sequence[str] | None = None,
    lotti: Sequence[int] | None = None,
    repo: VenditeRepository | None = None,
) -> list[tuple[Mapping[str, Any], tuple[str, ...] | None, tuple[int, ...] | None]]:
    if not gruppi and not lotti:
        return [(azienda, None, None) for azienda in aziende]

    repo = repo or VenditeRepository()
    pk_da_sr = {
        int(a["soggetto_ruolo_id"]): int(a["emittente_fiscale_id"]) for a in aziende
    }
    if gruppi:
        per_azienda = _assegna(
            gruppi,
            repo.aziende_dei_gruppi(competenza_mese=competenza, chiavi=gruppi),
            pk_da_sr, nome="gruppi",
        )
    else:
        assert lotti is not None
        trovati = repo.aziende_dei_lotti(lotti_ids=lotti)
        per_azienda = _assegna(
            lotti, {k: [v] for k, v in trovati.items()}, pk_da_sr, nome="lotti",
        )

    ripartizione: list[
        tuple[Mapping[str, Any], tuple[str, ...] | None, tuple[int, ...] | None]
    ] = []
    for azienda in aziende:
        righe = per_azienda.get(int(azienda["emittente_fiscale_id"]))
        if not righe:
            continue
        if gruppi:
            ripartizione.append((azienda, tuple(righe), None))
        else:
            ripartizione.append((azienda, None, tuple(righe)))
    return ripartizione


# Scopo: Accoda un lavoro di fatturazione per ogni azienda della richiesta e
#        ritorna l'handle di ciascuno: `[{job_id, emittente_fiscale_id,
#        emittente_codice, gruppi?, lotti?, stato}]`, nell'ordine delle
#        aziende; `stato` è quello vero del lavoro (PENDING, o IN_CORSO se la
#        dedup ha restituito un lavoro già vivo).
#        `payload` è il payload comune già validato (competenza ed extra);
#        gruppi e lotti li aggiunge qui, per azienda.
# ⭐ Ogni lavoro ha la chiave di BUSINESS della sua azienda (competenza +
#    `scope_key` dell'azienda + corsia + digest della SUA parte di
#    selezione): due click sullo stesso atto e sulla stessa azienda danno un
#    lavoro solo, da qualunque modalità arrivino.
# ⭐ L'handle porta le righe di quel lavoro: il frontend marca «in corso» le
#    sole righe di ciascun giro e le smarca quando QUEL giro finisce.
def accoda_per_azienda(
    scope: Mapping[str, Any],
    *,
    job_type: str,
    competenza: date,
    payload: Mapping[str, Any],
    gruppi: Sequence[str] | None = None,
    lotti: Sequence[int] | None = None,
    coda_repo: CodaLavoriRepository | None = None,
    vendite_repo: VenditeRepository | None = None,
) -> list[dict[str, Any]]:
    aziende = aziende_della_richiesta(scope)
    ripartizione = ripartisci_per_azienda(
        aziende, competenza=competenza, gruppi=gruppi, lotti=lotti,
        repo=vendite_repo,
    )
    coda_repo = coda_repo or CodaLavoriRepository()

    lavori: list[dict[str, Any]] = []
    for azienda, gruppi_az, lotti_az in ripartizione:
        scope_az = scope_in_azienda(scope, int(azienda["emittente_fiscale_id"]))
        job_payload = dict(payload)
        if gruppi_az:
            job_payload["gruppi"] = list(gruppi_az)
        if lotti_az:
            job_payload["lotti"] = list(lotti_az)
        # ⛔ Il valore della corsia NON si ricalcola qui con un `if`: si chiede
        #    al modulo che possiede la regola (vedi `corsia_del_giro`).
        idempotency_key = chiave_idempotenza_giro(
            job_type=job_type,
            competenza=competenza,
            scope_key=str(scope_az["scope_key"]),
            corsia=corsia_del_giro(job_type, gruppi=gruppi_az),
            digest=insieme_digest(gruppi_az or lotti_az),
        )
        job_id = coda_repo.accoda(
            job_type=job_type,
            payload=job_payload,
            run_as=RUN_AS_OPERATORE,
            scope=scope_az,
            idempotency_key=idempotency_key,
            origine=ORIGINE_API,
        )
        voce: dict[str, Any] = {
            "job_id": job_id,
            "emittente_fiscale_id": int(azienda["emittente_fiscale_id"]),
            "emittente_codice": azienda["codice"],
        }
        if gruppi_az:
            voce["gruppi"] = list(gruppi_az)
        if lotti_az:
            voce["lotti"] = list(lotti_az)
        lavori.append(voce)

    # ⭐ Lo stato VERO di ciascun lavoro, letto dopo averli accodati tutti (una
    #    query): sulla dedup l'id è quello di un lavoro già vivo, che può
    #    essere IN_CORSO (`stati_dopo_accodamento`, che solleva su un id che
    #    chi accoda non vede).
    stati = coda_repo.stati_dopo_accodamento([v["job_id"] for v in lavori])
    for voce in lavori:
        voce["stato"] = stati[voce["job_id"]]
    return lavori
