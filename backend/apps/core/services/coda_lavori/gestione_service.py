# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service della UI di gestione code (brief-be-fe-gestione-code-lavori-
#        stampa, FASE BE): conteggi per il badge top bar (BE-4), liste
#        coda lavori / coda stampa (BE-5/BE-6), azioni annulla/requeue con
#        enforcement ownership (BE-7) e dettaglio job (BE-8). Regole portanti:
#         - scope OPERATORE = `scope_key` (coda lavori) / emittenti via JOIN
#           fatture (coda stampa) — nessuna seconda logica di scope (I-1);
#         - il salto a "tutti i job / job altrui" richiede SUPER_ADMIN o
#           l'azione di processo `code_manage` (D-A; seed area core, brief §6);
#         - l'enforcement delle azioni è SEMPRE a livello BE (I-3): il FE
#           nasconde, qui si blinda (0 righe fuori scope = 404, no leak).
#        La coda stampa è di area vendite: l'accesso al suo repository avviene
#        con import LAZY nel corpo (stesso precedente di views_parameters →
#        anagrafiche; il namespace API resta il tracciamento core, P-1).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.services.coda_lavori.repository import (
    DEFAULT_EXTRA_TENTATIVI,
    CodaLavoriRepository,
)
from apps.core.services.coda_lavori.scope import scope_key_da_emittenti
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver

# Azione di processo che sblocca la vista cross-utente e le azioni su job
# altrui (D-A). Seed a carico del team DB (brief §6, area core); finché non è
# seedata `check_azione` risponde False e resta il bypass SUPER_ADMIN.
AZIONE_CODE_MANAGE = "code_manage"

# Jobname dei worker drainer in maintenance.job_run_log (owner: i rispettivi
# management command). Base della liveness del badge (BE-4).
JOBNAME_WORKER_CODA_LAVORI = "draina_coda_lavori"
JOBNAME_WORKER_CODA_STAMPA = "draina_coda_stampa"

# Soglia di liveness: ultimo run del worker entro N minuti = "attivo". I timer
# girano a 1-2 minuti: 10 minuti assorbe ritardi/riavvii senza falsi allarmi.
WORKER_ATTIVO_SOGLIA_MINUTI = 10

# Stati "vivi" delle due code (vocabolario condiviso PENDING/IN_CORSO).
_STATI_VIVI = ("PENDING", "IN_CORSO")


# Scopo: Risolve le due chiavi di scope del chiamante: `caller_key` (la
#        scope_key canonica, per `is_mio` — "ALL" per l'admin globale) e
#        `owner_filter` (filtro righe/azioni: None = vede tutto, per whitelist
#        emittenti None; altrimenti la propria scope_key). Speculare al
#        polling `run/<job_id>/` di vendite (stessa semantica, stessa fonte
#        `scope_key_da_emittenti`).
def _resolve_scope_keys(user: Any) -> tuple[str, str | None]:
    emittente_ids = PermissionResolver.get_emittenti_ids(user)
    caller_key = scope_key_da_emittenti(emittente_ids)
    owner_filter = None if emittente_ids is None else caller_key
    return caller_key, owner_filter


# Scopo: Il chiamante può vedere/gestire i job di TUTTI gli scope? SUPER_ADMIN
#        bypassa; altrimenti serve l'azione di processo `code_manage` (D-A).
def puo_gestire_tutte_le_code(user: Any) -> bool:
    if PermissionResolver.is_super_admin(user):
        return True
    return PermissionResolver.check_azione(user, AZIONE_CODE_MANAGE)


# Scopo: Guard del parametro `ambito=tutti` delle liste: consentito solo a chi
#        può gestire tutte le code; altrimenti 403 parlante (l'operatore non
#        deve poter allargare la visibilità via query param).
def _guard_ambito_tutti(user: Any) -> None:
    ErrorManager.require(
        puo_gestire_tutte_le_code(user),
        code="E_PERMESSO_NEGATO",
        message="Vista di tutte le code riservata (permesso code_manage).",
        detail=f"azione richiesta: {AZIONE_CODE_MANAGE}",
    )


# Scopo: BE-4 — conteggi per il badge top bar + liveness worker. Ritorna
#        `{coda_lavori: {pending, in_corso}, coda_stampa: {pending, in_corso},
#        worker: {coda_lavori: {...}, coda_stampa: {...}}}`. I conteggi sono
#        SCOPED al chiamante (coda lavori per scope_key; coda stampa per
#        emittente via JOIN fatture — `auth_user_id` None = superuser, vede
#        tutto). La liveness confronta l'ultimo run dei drainer col clock DB;
#        un worker mai girato → {last_run_at: None, attivo: False} (fail-visible:
#        "worker giù", non un buco nel payload).
def conteggi_code(user: Any, *, auth_user_id: int | None) -> dict[str, Any]:
    _caller_key, owner_filter = _resolve_scope_keys(user)
    lavori = CodaLavoriRepository().count_per_stato(owner_scope_key=owner_filter)

    # Coda stampa: area vendite, satellite di fatture (import lazy — vedi header).
    from apps.vendite.db.pipeline_repository import VenditePipelineRepository

    stampa = VenditePipelineRepository().count_coda_stampa_per_stato(
        auth_user_id=auth_user_id,
    )

    liveness = MaintenanceRepository().job_liveness(
        [JOBNAME_WORKER_CODA_LAVORI, JOBNAME_WORKER_CODA_STAMPA],
        soglia_minuti=WORKER_ATTIVO_SOGLIA_MINUTI,
    )
    worker_giu = {"last_run_at": None, "attivo": False, "last_ok": None}

    return {
        "coda_lavori": {
            "pending": lavori.get("PENDING", 0),
            "in_corso": lavori.get("IN_CORSO", 0),
        },
        "coda_stampa": {
            "pending": stampa.get("PENDING", 0),
            "in_corso": stampa.get("IN_CORSO", 0),
        },
        "worker": {
            "coda_lavori": liveness.get(JOBNAME_WORKER_CODA_LAVORI, worker_giu),
            "coda_stampa": liveness.get(JOBNAME_WORKER_CODA_STAMPA, worker_giu),
        },
    }


# Scopo: BE-5 — lista paginata della coda lavori. Scope operatore di default;
#        `tutti=True` (query `?ambito=tutti`) consentito solo con `code_manage`/
#        SUPER_ADMIN → nessun filtro righe, `is_mio` continua a marcare i propri
#        (colonna proprietario per capire chi impegna la coda). `data_a` è
#        inclusiva a livello di GIORNO: convertita in esclusivo `+1 giorno`
#        (la colonna è timestamptz). Ritorna `{count, results}`.
def elenca_coda_lavori(
    user: Any,
    *,
    stato: str | None = None,
    job_type: str | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    solo_vivi: bool = False,
    limit: int = 50,
    offset: int = 0,
    tutti: bool = False,
) -> dict[str, Any]:
    caller_key, owner_filter = _resolve_scope_keys(user)
    if tutti:
        _guard_ambito_tutti(user)
        owner_filter = None
    esito = CodaLavoriRepository().elenca(
        owner_scope_key=owner_filter,
        caller_scope_key=caller_key,
        # `solo_vivi` → vocabolario _STATI_VIVI QUI (simmetrico alla coda
        # stampa: il repo riceve sempre `stati`, mai un secondo meccanismo).
        stati=list(_STATI_VIVI) if solo_vivi else ([stato] if stato else None),
        job_type=job_type,
        data_da=data_da,
        data_a=(data_a + timedelta(days=1)) if data_a else None,
        limit=limit,
        offset=offset,
    )
    return {"count": esito["total"], "results": esito["items"]}


# Scopo: BE-6 — lista paginata della coda stampa (outbox PDF). Scope emittente
#        dell'operatore via JOIN fatture (la coda non ha utente proprietario:
#        è per-emittente/lotto — asimmetria §1 del brief). `tutti=True` con
#        `code_manage` → nessuno scope (auth_user_id=None al repo). Ritorna
#        `{count, results}`.
def elenca_coda_stampa(
    user: Any,
    *,
    auth_user_id: int | None,
    stato: str | None = None,
    lotto_id: int | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    solo_vivi: bool = False,
    limit: int = 50,
    offset: int = 0,
    tutti: bool = False,
) -> dict[str, Any]:
    if tutti:
        _guard_ambito_tutti(user)
        auth_user_id = None

    from apps.vendite.db.pipeline_repository import VenditePipelineRepository

    esito = VenditePipelineRepository().elenca_coda_stampa(
        auth_user_id=auth_user_id,
        stati=list(_STATI_VIVI) if solo_vivi else ([stato] if stato else None),
        lotto_id=lotto_id,
        data_da=data_da,
        data_a=(data_a + timedelta(days=1)) if data_a else None,
        limit=limit,
        offset=offset,
    )
    return {"count": esito["total"], "results": esito["items"]}


# Scopo: BE-8 — dettaglio completo di un job per il drawer (payload, timeline,
#        tentativi/errore, esito, proprietario, is_mio). Ownership scope-based
#        come il polling: fuori scope/inesistente → 404 unificato (no leak);
#        chi può gestire tutte le code vede ogni job.
def dettaglio_job(user: Any, job_id: int) -> dict[str, Any]:
    caller_key, owner_filter = _resolve_scope_keys(user)
    if owner_filter is not None and puo_gestire_tutte_le_code(user):
        owner_filter = None
    dettaglio = CodaLavoriRepository().get_dettaglio(
        int(job_id),
        owner_scope_key=owner_filter,
        caller_scope_key=caller_key,
    )
    ErrorManager.require(
        dettaglio is not None,
        code="E_JOB_NON_TROVATO",
        message="Job non trovato.",
        detail=f"job_id={job_id}",
    )
    assert dettaglio is not None
    return dettaglio


# Scopo: Ownership per le AZIONI (annulla/requeue): un operatore agisce solo
#        sui job della propria scope_key; chi può gestire tutte le code agisce
#        su qualunque job (owner filter None). Ritorna il filtro da passare
#        al repository.
def _owner_filter_per_azione(user: Any) -> str | None:
    _caller_key, owner_filter = _resolve_scope_keys(user)
    if owner_filter is not None and puo_gestire_tutte_le_code(user):
        return None
    return owner_filter


# Scopo: BE-7 — annulla un job PENDING (→ ANNULLATO). Sequenza: esistenza in
#        scope (404 unificato, no leak) → UPDATE condizionato allo stato (0
#        righe = non più PENDING → 409 parlante; l'UPDATE ri-verifica stato E
#        scope, quindi nessuna race col worker: un claim concorrente vince e
#        l'annullo fallisce onestamente). Ritorna `{job_id, stato: ANNULLATO}`.
def annulla_job(user: Any, job_id: int) -> dict[str, Any]:
    owner_filter = _owner_filter_per_azione(user)
    repo = CodaLavoriRepository()
    stato = repo.get_stato(int(job_id), owner_scope_key=owner_filter)
    ErrorManager.require(
        stato is not None,
        code="E_JOB_NON_TROVATO",
        message="Job non trovato.",
        detail=f"job_id={job_id}",
    )
    annullato = repo.annulla(int(job_id), owner_scope_key=owner_filter)
    ErrorManager.require(
        annullato,
        code="E_JOB_NON_ANNULLABILE",
        message="Il job non è più in attesa: solo i job PENDING si annullano.",
        detail=f"job_id={job_id} stato={stato['stato'] if stato else None}",
    )
    return {"job_id": int(job_id), "stato": "ANNULLATO"}


# Scopo: BE-7 — requeue/sblocco di un job IN_CORSO (bloccato) o ERRORE
#        (terminale) → PENDING con `max_tentativi += extra_tentativi` (la
#        storia dei tentativi si preserva, brief DB §3a). Stessa sequenza
#        404/409 dell'annullo. Ritorna `{job_id, stato: PENDING}`.
def requeue_job(
    user: Any, job_id: int, *, extra_tentativi: int = DEFAULT_EXTRA_TENTATIVI,
) -> dict[str, Any]:
    ErrorManager.require(
        1 <= int(extra_tentativi) <= 10,
        code="E_VALIDATION_INPUT",
        message="`extra_tentativi` deve essere tra 1 e 10.",
        detail=f"extra_tentativi={extra_tentativi}",
    )
    owner_filter = _owner_filter_per_azione(user)
    repo = CodaLavoriRepository()
    stato = repo.get_stato(int(job_id), owner_scope_key=owner_filter)
    ErrorManager.require(
        stato is not None,
        code="E_JOB_NON_TROVATO",
        message="Job non trovato.",
        detail=f"job_id={job_id}",
    )
    riaccodato = repo.requeue(
        int(job_id),
        extra_tentativi=int(extra_tentativi),
        owner_scope_key=owner_filter,
    )
    ErrorManager.require(
        riaccodato,
        code="E_JOB_NON_RIACCODABILE",
        message=(
            "Il job non è riaccodabile: il requeue vale solo per job in "
            "ERRORE o IN_CORSO davvero bloccati (esecuzione ferma oltre "
            "soglia) — un job in esecuzione va lasciato finire."
        ),
        detail=f"job_id={job_id} stato={stato['stato'] if stato else None}",
    )
    return {"job_id": int(job_id), "stato": "PENDING"}
