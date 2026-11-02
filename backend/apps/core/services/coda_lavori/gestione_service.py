# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service della UI di gestione code (brief-be-fe-gestione-code-lavori-
#        stampa, FASE BE): conteggi per il badge top bar (BE-4), liste
#        coda lavori / coda stampa (BE-5/BE-6), azioni annulla/requeue con
#        enforcement ownership (BE-7), dettaglio job (BE-8) e — dal 2026-09-04
#        (brief-db-archiviazione-righe-code) — l'ARCHIVIAZIONE delle righe di
#        entrambe le code, che le toglie dall'ELENCO senza toccarne lo stato.
#        Regole portanti:
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

from collections.abc import Callable
from datetime import date
from typing import Any

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db.emittente_scope_helpers import fetch_emittenti_scope_ids
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.coda_lavori.repository import (
    DEFAULT_EXTRA_TENTATIVI,
    ELENCA_SORT_SQL,
    STATI_VIVI,
    CodaLavoriRepository,
)
from apps.core.services.coda_lavori.scope import scope_key_da_emittenti
from apps.core.services.error_manager import ErrorManager
from apps.core.services.fan_out import run_fan_out
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.payload_helpers import translate_db_errors
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.processi import (
    PROCESSO_DRAINA_CODA_LAVORI,
    PROCESSO_DRAINA_CODA_STAMPA,
)
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError

# Azione di processo che sblocca la vista cross-utente e le azioni su job
# altrui (D-A). Seed a carico del team DB (brief §6, area core); finché non è
# seedata `check_azione` risponde False e resta il bypass SUPER_ADMIN.
AZIONE_CODE_MANAGE = "code_manage"

# Jobname dei worker drainer in maintenance.job_run_log (owner: i rispettivi
# management command). Base della liveness del badge (BE-4).
# ⭐ NON sono letterali: sono le costanti dei processi. I due command si
#    registrano sul giornale col PROPRIO codice, quindi qui `jobname` e
#    `processo_codice` sono la stessa stringa — e scriverla due volte
#    significherebbe che `_liveness_worker`, che cerca la tolleranza PER
#    PROCESSO, smetterebbe di trovarla al primo rename senza che niente
#    fallisca: cadrebbe sul ripiego, e il pallino resterebbe verde con un
#    numero inventato.
JOBNAME_WORKER_CODA_LAVORI = PROCESSO_DRAINA_CODA_LAVORI
JOBNAME_WORKER_CODA_STAMPA = PROCESSO_DRAINA_CODA_STAMPA

# Ripiego della soglia di liveness, per un worker che a catalogo non ha un
# contratto (`dbops.processi.tolleranza_minuti` NULL, o codice non a catalogo).
# ⚠️ NON è «il valore giusto»: è il valore che non fa danno. Un worker senza
#    contratto è una riga di `processi.csv` incompleta, e il posto dove si
#    corregge è quella — non questa riga.
# ⛔ E non deve diventare la strada normale: `test_worker_del_badge_hanno_un_contratto`
#    fallisce in CI se uno dei due drainer arriva qui senza tolleranza nel seed.
#    Questo resta per il runtime, dove un badge che si spegne sarebbe peggio.
_SOGLIA_LIVENESS_RIPIEGO_MINUTI = 10

# Gli stati "vivi" delle due code sono `STATI_VIVI` del repository (dal
# 2026-09-15, accanto agli altri vocabolari della tabella): qui c'era la
# seconda copia, e un alias locale sarebbe un secondo nome per la stessa cosa.


# Scopo: Risolve le due chiavi di scope del chiamante: `caller_key` (la
#        scope_key canonica, per `is_mio` — "ALL" per l'admin globale) e
#        `owner_filter` (filtro righe/azioni: None = vede tutto, per whitelist
#        emittenti None; altrimenti la propria scope_key). Speculare al
#        polling `run/<job_id>/` di vendite (stessa semantica, stessa fonte
#        `scope_key_da_emittenti`).
def _resolve_scope_keys(user: Any) -> tuple[str, str | None]:
    emittente_ids = PermissionResolver.get_emittenti_pk_ids(user)
    caller_key = scope_key_da_emittenti(emittente_ids)
    owner_filter = None if emittente_ids is None else caller_key
    return caller_key, owner_filter


# Scopo: Chiave di scope che IDENTIFICA il chiamante sui job di coda ('ALL'
#        per l'admin globale, altrimenti gli emittenti ordinati). È la stessa
#        identità con cui `elenca` calcola `is_mio`. Esposta come API pubblica
#        del modulo perché serve anche fuori dalla gestione code: il cockpit
#        fatturazione spezza i conteggi dei giri in «miei / di altri» e deve
#        usare la STESSA identità, non una seconda copia che può divergere.
def scope_key_operatore(user: Any) -> str:
    return _resolve_scope_keys(user)[0]


# Scopo: Il chiamante può vedere/gestire i job di TUTTI gli scope? SUPER_ADMIN
#        bypassa; altrimenti serve l'azione di processo `code_manage` (D-A).
def puo_gestire_tutte_le_code(user: Any) -> bool:
    if PermissionResolver.is_super_admin(user):
        return True
    return PermissionResolver.check_azione(user, AZIONE_CODE_MANAGE)


# Scopo: valida `sort_by`/`sort_dir` delle liste code contro la whitelist del
#        chiamante e applica i default (2026-07-23, richiesta Tid: lavori →
#        `started_at DESC`, stampa → `data_update DESC`). Valori fuori
#        whitelist → E_SEARCH_VALIDATION parlante; il repo ha comunque il suo
#        assert di defense-in-depth. Ritorna la coppia normalizzata.
def _valida_ordinamento(
    sort_by: str | None,
    sort_dir: str | None,
    *,
    allowed: tuple[str, ...],
    default: str,
    function_name: str,
) -> tuple[str, str]:
    # ⛔ Il BB `validate_order_params` (2026-09-26), non due `validate_enum_param`
    #    con un insieme `("ASC", "DESC")` scritto qui: la direzione la giudica
    #    `order_dir_ammessa`, la stessa regola del repository e di ogni lista.
    #    `nullable`: l'assenza prende i default di Tid qui sotto.
    sort_by, sort_dir_norm = validate_order_params(
        sort_by, sort_dir, allowed_columns=allowed, nullable=True,
        error_code="E_SEARCH_VALIDATION", function_name=function_name,
    )
    return sort_by or default, (sort_dir_norm or "desc").upper()


# Scopo: liveness dei worker, con la soglia PRESA DAL CONTRATTO A CATALOGO
#        (`dbops.processi.tolleranza_minuti`, via
#        `ProcessiRepository.contratti_liveness`) invece che da una costante
#        scritta qui.
#
# ⛔ PERCHE' NON E' PIU' UN NUMERO IN QUESTO FILE. Fino al 2026-09-06 c'era
#    `WORKER_ATTIVO_SOGLIA_MINUTI = 10`, con il commento «i timer girano a 1-2
#    minuti». Quel commento è la prova del difetto: per sapere se 10 fosse
#    ancora giusto bisognava andare a leggere l'`OnCalendar` in un altro file,
#    che nessuno rileggeva. Lo stesso fatto scritto in due posti — e il giorno
#    in cui una cadenza fosse passata a 15 minuti, il pallino sarebbe diventato
#    rosso su un worker sano, che è il modo più rapido di far smettere di
#    guardare un presidio.
# ⭐ E dal 2026-09-11 non sta nemmeno in `sveglie.json`: la tolleranza è il
#    CONTRATTO del processo e la legge anche il database (il panorama dice
#    `MUTO` con lo stesso numero). Qui e là si confronta lo stesso contratto
#    con lo stesso giornale: se i due dissentissero, uno dei due avrebbe un
#    orologio storto — ed è per questo che `job_liveness` confronta col clock
#    del database, non con quello di Python.
#
# ⚠️ SI RAGGRUPPA PER SOGLIA, e non è generalità gratuita: `job_liveness`
#    accetta UNA soglia per chiamata, e nulla nel modello dice che due worker
#    debbano avere la stessa. Oggi le due coincidono e la chiamata resta una
#    sola; il giorno in cui divergono questo codice fa la cosa giusta invece di
#    applicarne una alle due.
def _liveness_worker(jobnames: list[str]) -> dict[str, dict]:
    # ⚠️ Il jobname dei drainer È il `processo_codice`: sono i command che si
    #    registrano col proprio nome, e le costanti qui sopra vengono da
    #    `processi.py` apposta. Dove i due non coincidessero (le corsie di
    #    `run_fatturazione_batch`, che attaccano la corsia al jobname) la
    #    liveness non si fa da qui. Una lettura sola per tutti i worker.
    contratti = ProcessiRepository().contratti_liveness(jobnames)
    per_soglia: dict[int, list[str]] = {}
    for jobname in jobnames:
        # ⛔ `is None` e NON `or`: sono due domande diverse. `or` direbbe
        #    «ripiega» anche su uno zero, e soprattutto confonde «non a
        #    catalogo» con «a catalogo senza contratto» — che nel modello sono
        #    due cose diverse (`NULL` = «non si presidia»). Qui entrambe cadono
        #    sul ripiego, e il test sul seed impedisce che ci arrivino i drainer.
        contratto = contratti.get(jobname)
        dichiarata = contratto["tolleranza_minuti"] if contratto else None
        soglia = _SOGLIA_LIVENESS_RIPIEGO_MINUTI if dichiarata is None else dichiarata
        per_soglia.setdefault(soglia, []).append(jobname)

    repo = MaintenanceRepository()
    esito: dict[str, dict] = {}
    for soglia, gruppo in per_soglia.items():
        esito.update(repo.job_liveness(gruppo, soglia_minuti=soglia))
    return esito


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

    liveness = _liveness_worker(
        [JOBNAME_WORKER_CODA_LAVORI, JOBNAME_WORKER_CODA_STAMPA],
    )
    # ⚠️ Stessa forma di `job_liveness` (2026-09-14): la riga piu' recente come
    #    segno di vita e l'ultima conclusa a parte, con la sua data — un worker
    #    mai girato non ha ne' l'una ne' l'altra.
    worker_giu = {
        "last_run_at": None, "attivo": False, "in_corso": False,
        "ultima_conclusa": None,
    }

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
#        `tutti=True` (query `?ambito=tutti`) è VISIBILITÀ, non gestione, ed è
#        aperto a ogni operatore (decisione Tid 2026-07-23): la coda è una
#        risorsa condivisa e chi aspetta deve poter vedere il lavoro altrui che
#        la impegna — proprietario e tipo attività non sono segreti tra
#        colleghi. Restano gated da `code_manage`: le AZIONI sui job altrui
#        (`_owner_filter_per_azione`) e il DETTAGLIO (payload/errori possono
#        contenere dati dell'attività altrui — vedi `dettaglio_job`).
#        `is_mio` continua a marcare i propri. `data_a` è inclusiva a livello
#        di GIORNO, e i giorni sono quelli dell'azienda: li traduce in confini
#        il repository (BB `predicato_giorno_operativo`; fino al 2026-10-09 il
#        `+1 giorno` si calcolava qui e il confine era la mezzanotte della
#        sessione). Ritorna `{count, results}`.
def elenca_coda_lavori(
    user: Any,
    *,
    stato: str | None = None,
    job_type: str | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    solo_vivi: bool = False,
    includi_archiviate: bool = False,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    tutti: bool = False,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    caller_key, owner_filter = _resolve_scope_keys(user)
    if tutti:
        owner_filter = None
    # `allowed` DERIVATO dalla whitelist del repository, mai ricopiato: era una
    # copia a mano di 4 nomi e sarebbe divergita alla prima estensione (che
    # infatti e' arrivata il 2026-08-02 con `stato`/`proprietario`).
    sort_by, sort_dir = _valida_ordinamento(
        sort_by, sort_dir,
        allowed=tuple(ELENCA_SORT_SQL),
        # ⭐ `data_insert`, non `started_at` (2026-09-07). Un lavoro in ATTESA
        #    `started_at` non ce l'ha — lo scrive il worker — quindi col vecchio
        #    default finiva in fondo alla lista, dopo ogni lavoro mai avviato:
        #    non filtrato, SEPOLTO. `data_insert` e' NOT NULL, quindi ogni
        #    lavoro ha una posizione dal momento in cui entra in coda.
        # ⚠️ Questo default e' scritto in TRE sedi che devono concordare: qui,
        #    `ordinamento_default` del preset in `ui.lista_preset`, e `orderBy`
        #    dello store FE.
        # ⛔ E NESSUN PRESIDIO LE TIENE INSIEME — verificato il 2026-09-08:
        #    `test_liste_configurabili_seed` confronta le colonne ORDINABILI del
        #    seed con questa whitelist, non i DEFAULT; e in `backend/apps` niente
        #    legge `ordinamento_default`. ⇒ Una divergenza non fa rosso niente:
        #    fa una lista che arriva ordinata in un modo e si riordina in un
        #    altro appena l'operatore tocca una colonna. Si controlla a mano.
        default="data_insert",
        function_name="core.gestione_code.elenca_coda_lavori",
    )
    esito = CodaLavoriRepository().elenca(
        owner_scope_key=owner_filter,
        caller_scope_key=caller_key,
        # `solo_vivi` → vocabolario STATI_VIVI QUI (simmetrico alla coda
        # stampa: il repo riceve sempre `stati`, mai un secondo meccanismo).
        stati=list(STATI_VIVI) if solo_vivi else ([stato] if stato else None),
        job_type=job_type,
        data_da=data_da,
        data_a=data_a,
        includi_archiviate=includi_archiviate,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return {
        "count": esito["total"],
        "results": esito["items"],
        # Quante righe l'archiviazione lascia fuori dall'elenco. ⚠️ Non è un
        # accessorio: senza, «coda pulita» e «tre righe messe via» si leggono
        # uguali — stessa lezione di `ritirate_count` sul giornale della fattura.
        "archiviate_count": esito["archiviate"],
    }


# Scopo: BE-6 — lista paginata della coda stampa (outbox PDF). Ambito
#        PER-OPERATORE come la coda lavori (2026-07-23, decisione Tid — una
#        semantica diversa per coda si leggeva come filtro rotto): «miei» =
#        righe innescate dal chiamante (`user_insert`, identità GUC), `tutti`
#        = tutte (visibilità aperta a ogni operatore). Il `caller_username`
#        marca comunque `is_mio` anche in vista «Tutti», come la coda lavori.
#        Ritorna `{count, results}`.
def elenca_coda_stampa(
    user: Any,
    *,
    stato: str | None = None,
    lotto_id: int | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    solo_vivi: bool = False,
    includi_archiviate: bool = False,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    tutti: bool = False,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any]:
    caller_username = getattr(user, "username", None)

    # Import lazy come sotto (la coda stampa e' satellite di vendite, vedi
    # header): serve QUI perche' `allowed` e' DERIVATO dalla whitelist del
    # repository invece di essere ricopiato a mano.
    from apps.vendite.db.pipeline_repository import (
        CODA_STAMPA_SORT_SQL,
        VenditePipelineRepository,
    )

    sort_by, sort_dir = _valida_ordinamento(
        sort_by, sort_dir,
        allowed=tuple(CODA_STAMPA_SORT_SQL),
        # ⭐ Allineata alla coda lavori il 2026-09-07: le due code hanno una
        #    semantica sola per decisione (Tid, 2026-07-23), e due default
        #    diversi erano una simmetria che reggeva per caso.
        default="data_insert",
        function_name="core.gestione_code.elenca_coda_stampa",
    )

    esito = VenditePipelineRepository().elenca_coda_stampa(
        operatore=None if tutti else caller_username,
        caller_username=caller_username,
        stati=list(STATI_VIVI) if solo_vivi else ([stato] if stato else None),
        lotto_id=lotto_id,
        data_da=data_da,
        data_a=data_a,
        includi_archiviate=includi_archiviate,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return {
        "count": esito["total"],
        "results": esito["items"],
        "archiviate_count": esito["archiviate"],
    }


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
        code=E_VALIDATION_INPUT,
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


# ══════════════════════════════════════════════════════════════
#  ARCHIVIAZIONE — togliere una riga dall'ELENCO, non dal lavoro
#  (brief-db-archiviazione-righe-code, 2026-09-04)
# ══════════════════════════════════════════════════════════════
#
# ⛔ IL VERBO È GLOBALE, E QUINDI LO È IL PERMESSO. Annulla e requeue sono
#    owner-scoped — un operatore agisce sui PROPRI job senza `code_manage`, che
#    serve solo ad allargare agli altrui. L'archiviazione no: chi archivia
#    toglie la riga dall'elenco ANCHE all'amministratore. Un verbo con effetto
#    globale in un modello di permessi per-proprietario non compone: sarebbe un
#    operatore che nasconde righe a chi deve vederle tutte.
#    ⇒ Effetto globale, permesso globale: `code_manage` (decisione di Tid,
#    2026-09-04, brief §7.2).
#
# ⛔ IL GATE STA QUI E NON IN `post_permission` SULLA VIEW, e la differenza NON
#    è stilistica: `ZeroERPPermission` che trova un `<metodo>_permission`
#    RITORNA l'esito dell'azione di processo e **salta il controllo di area**.
#    Un operatore con `code_manage` e area `strumenti` in sola LETTURA
#    passerebbe — mentre gli altri due verbi della stessa pagina, che quel
#    permesso non lo dichiarano, cadono su `METHOD_REQUIRES['POST'] = 'add'` e
#    quindi pretendono `TUTTO`. Due POST adiacenti nella stessa schermata con
#    due contratti di area diversi sono la forma in cui un permesso «funziona»
#    finché qualcuno non lo restringe e non capisce perché non ha effetto.
#    ⇒ La view NON dichiara `post_permission`: l'area la verifica la catena
#    standard, `code_manage` lo verifica questo service — esattamente come
#    `_owner_filter_per_azione` fa per annulla/requeue. Un controllo per
#    ciascuna delle due cose, nessuna delle due saltata.
# ⛔ NESSUN controllo di stato in Python. «Solo una riga non viva si archivia»
#    ha UNA sede — il trigger `_a10_archiviazione_upd` più il `CHECK` — e da lì
#    arriva `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` (CONFLITTO_STATO → 409) con la
#    sua frase a catalogo. Ricopiare l'elenco degli stati qui creerebbe un
#    secondo criterio destinato a sfilarsi dal primo.
# ⛔ E la bandiera NON entra nel `WHERE` di claim, drainer, reaper, `mark_*` e
#    `count_*`: è la cosa che distingue l'archiviazione da un annullamento
#    silenzioso (brief §3, il contratto del cantiere).

# Messaggio di ripiego dei due verbi: vale solo se il database non ha parlato
# (un `DatabaseError` senza codice a catalogo). Quando parla — ed è il caso
# normale del rifiuto sulla riga viva — vince il suo.
_ARCHIVIAZIONE_FALLBACK = (
    "Archiviazione della riga di coda non riuscita."
)

# Quante righe può portare una sola chiamata. ⚠️ Non è una soglia di
# prestazione: è che oltre un certo punto «metti via N righe» smette di essere
# un gesto che una persona ha guardato. Le liste code paginano a 200, ed è lo
# stesso tetto — stessa scelta e stessa ragione di `MAX_ATTIVITA_RIPORTO`.
MAX_RIGHE_ARCHIVIAZIONE = 200


# Scopo: il cancello dei due verbi — `code_manage` (SUPER_ADMIN bypassa),
#        stessa funzione che apre le azioni sui job altrui. ⚠️ Si somma al
#        livello di area, che la catena dei permessi verifica per conto suo:
#        vedi la nota qui sopra sul perché non è un `post_permission`.
def _guard_archiviazione(user: Any) -> None:
    ErrorManager.require(
        puo_gestire_tutte_le_code(user),
        code="E_PERMESSO_NEGATO",
        message=(
            "Per archiviare o ripristinare righe di coda serve la gestione "
            "delle code: l'archiviazione toglie la riga dall'elenco di tutti, "
            "non solo dal proprio."
        ),
        detail="azione richiesta: code_manage",
    )


# Scopo: valida l'elenco di righe di una chiamata di archiviazione: lista non
#        vuota, interi positivi, sotto il tetto. Ritorna gli id DEDUPLICATI
#        con l'ordine preservato.
# ⚠️ Il dedup non è cosmetico: il database tratterebbe due volte lo stesso id
#    come una riga sola, ma il conteggio che torna a video direbbe un numero
#    diverso da quello che l'operatore ha spuntato.
def _valida_ids_archiviazione(ids: object, *, function_name: str) -> list[int]:
    ErrorManager.require(
        isinstance(ids, list) and len(ids) > 0,
        code=E_VALIDATION_INPUT,
        message="Selezionare almeno una riga.",
        detail="`ids` deve essere una lista non vuota.",
        context={"field": "ids"},
        function_name=function_name,
    )
    assert isinstance(ids, list)
    ErrorManager.require(
        all(isinstance(i, int) and not isinstance(i, bool) and i > 0 for i in ids),
        code=E_VALIDATION_INPUT,
        message="Elenco di righe non valido.",
        detail="Ogni elemento di `ids` deve essere un intero positivo.",
        context={"field": "ids"},
        function_name=function_name,
    )
    ErrorManager.require(
        len(ids) <= MAX_RIGHE_ARCHIVIAZIONE,
        code=E_VALIDATION_INPUT,
        message=f"Troppe righe selezionate (massimo {MAX_RIGHE_ARCHIVIAZIONE}).",
        detail=f"Ricevute {len(ids)} righe.",
        context={"field": "ids"},
        function_name=function_name,
    )
    # Dedup con ordine preservato: le chiavi di un dict tengono l'ordine.
    return list(dict.fromkeys(ids))


# Scopo: il giro di archiviazione su N righe, comune alle due code — l'unica
#        cosa che cambia è `applica`, cioè quale repository tocca la bandiera.
#        Ritorna `{esito, archiviato, richieste, riuscite, falliti[]}`.
#
# ⭐ ESITO PARZIALE, non tutto-o-niente. Il rifiuto è PER RIGA (una riga tornata
#    al lavoro nel frattempo), quindi un'unica transazione farebbe fallire venti
#    archiviazioni buone per una riga sola — e l'operatore non saprebbe quale.
#    Il telaio è `run_fan_out`: un savepoint per riga, l'errore isolato,
#    l'esito aggregato a tre stati. ⛔ È anche la ragione per cui NON si fa un
#    solo `UPDATE ... WHERE id = ANY(...)` con il predicato di stato nella
#    `WHERE`: quello sarebbe veloce, ma scriverebbe la SECONDA copia di «riga
#    viva» — che ha una sede sola, il trigger, e che questo cantiere ha
#    deliberatamente lasciato lì (brief §7.4).
#
# ⭐ L'eccezione di ogni riga la porta il BB (`FanOutItemErrore.eccezione`, dal
#    2026-09-17): fino a quel giorno questo sito la tratteneva in un dizionario
#    laterale popolato con un `try/except/raise` dentro `_process` — la prima
#    delle due copie che hanno fatto nascere il campo (la seconda: «righe da
#    rate» in `pagamenti`). Un rollback annulla le righe di database, non un
#    oggetto in memoria: l'eccezione sopravvive al savepoint anche da lì.
def _esegui_archiviazione(
    ids: object,
    *,
    archiviato: bool,
    applica: Callable[[int], bool],
    function_name: str,
) -> dict[str, Any]:
    righe = _valida_ids_archiviazione(ids, function_name=function_name)

    # Scopo: la bandiera su UNA riga. Solleva su rifiuto: è così che il fan-out
    #        distingue riuscite e fallite.
    def _process(riga_id: int) -> int:
        with translate_db_errors(
            context={"op": function_name, "riga_id": riga_id},
            fallback_code="E_CODA_ARCHIVIAZIONE_NON_AMMESSA",
            fallback_message=_ARCHIVIAZIONE_FALLBACK,
        ):
            trovata = applica(riga_id)
        ErrorManager.require(
            trovata,
            code="E_JOB_NON_TROVATO",
            message="Riga di coda non trovata.",
            detail=f"riga_id={riga_id}",
        )
        return riga_id

    # Scopo: il motivo di UNA riga fallita, nella forma che il client legge.
    # ⛔ Il ripiego copre l'eccezione che NON è un `ServiceError` — cioè un
    #    GUASTO — e lì NON si rimanda la stringa normalizzata del BB:
    #    sarebbe un `TypeError: ...` letto da un operatore, che non è un
    #    messaggio business-safe e non gli dice niente di azionabile. La
    #    diagnostica vera sta nel log, che `run_fan_out` scrive con lo
    #    stack e l'identità della riga. Il `code` resta `None`: inventarne
    #    uno di dominio direbbe una cosa falsa.
    def _motivo(exc: Exception) -> dict[str, Any]:
        if isinstance(exc, ServiceError):
            return {"code": exc.code, "message": exc.message}
        return {"code": None, "message": _ARCHIVIAZIONE_FALLBACK}

    esito = run_fan_out(righe, _process)
    return {
        "esito": esito.esito,
        "archiviato": bool(archiviato),
        "richieste": esito.totale,
        "riuscite": esito.ok,
        "falliti": [{"id": e.item, **_motivo(e.eccezione)} for e in esito.errori],
    }


# Scopo: alza/abbassa la bandiera `archiviato` su N job di `dbops.coda_lavori`.
#        `archiviato=True` = «Archivia» (togli dall'elenco), `False` =
#        «Ripristina» (rimettile). Riga inesistente → conta come fallita
#        (`E_JOB_NON_TROVATO`); riga ancora VIVA → il database la rifiuta con
#        `E_CODA_ARCHIVIAZIONE_NON_AMMESSA`. Le altre passano lo stesso.
#        ⚠️ Prende sempre un ELENCO, anche quando l'operatore agisce su una
#        riga sola dal menu: un verbo di massa e uno singolo sarebbero due
#        contratti da tenere allineati per lo stesso identico rifiuto.
def imposta_archiviazione_job(
    user: Any, ids: object, *, archiviato: bool,
) -> dict[str, Any]:
    _guard_archiviazione(user)
    repo = CodaLavoriRepository()
    return _esegui_archiviazione(
        ids,
        archiviato=archiviato,
        applica=lambda riga_id: repo.imposta_archiviato(
            riga_id, archiviato=bool(archiviato),
        ),
        function_name="core.gestione_code.imposta_archiviazione_job",
    )

# Scopo: gemello per `vendite.fatture_stampa_coda`. Stessa bandiera, stesso
#        trigger, stesso codice errore — la simmetria fra le due code è del
#        modello, non una promessa.
#        ⚠️ È la PRIMA scrittura dell'operatore su quella tabella: oltre alla
#        policy RLS armata il 2026-09-04, il repository applica anche il filtro
#        applicativo di emittente (`auth_user_id`) — la RLS si SOMMA ai filtri,
#        non li sostituisce. Fuori perimetro → 0 righe → la riga conta come
#        non trovata, indistinguibile da inesistente (no leak).
def imposta_archiviazione_stampa(
    user: Any, ids: object, *, archiviato: bool, auth_user_id: int | None,
) -> dict[str, Any]:
    _guard_archiviazione(user)
    # Import lazy: la coda stampa è satellite di vendite (vedi header).
    from apps.vendite.db.pipeline_repository import VenditePipelineRepository

    repo = VenditePipelineRepository()
    # ⭐ Il perimetro emittente si risolve UNA volta per la richiesta, non per
    #    riga: dentro una richiesta non cambia, e il giro puo' avere 200 righe.
    #    `None` (superuser) resta `None` = nessuna restrizione.
    emittenti_sr_ids = (
        None if auth_user_id is None
        else fetch_emittenti_scope_ids(auth_user_id, convention="sr")
    )
    return _esegui_archiviazione(
        ids,
        archiviato=archiviato,
        applica=lambda riga_id: repo.imposta_archiviato_stampa(
            riga_id, archiviato=bool(archiviato), emittenti_sr_ids=emittenti_sr_ids,
        ),
        function_name="core.gestione_code.imposta_archiviazione_stampa",
    )
