# Sviluppo — Push commessa di un singolo preventivo (BE+FE)

> **Branch BE+FE**: `dev/backend-tid`.
> **Branch DB gemello**: `dev/db-tid` (vedi
> [brief-db-fn-list-preventivi-push-singolo.md](brief-db-fn-list-preventivi-push-singolo.md)).
> **Trigger**: §3.4 del test plan
> [sviluppo-listini-v5-test-ui.md](../work-in-progress/sviluppo-listini-v5-test-ui.md)
> non eseguibile in stato attuale (BE-stub con TODO esplicito).
>
> **➡️ Stato (2026-06-20)**: **PR1 ✅ FATTA e in produzione** —
> `pr_run_commesse_push_one` (`commesse_service.py`) + `push_a_commessa` riscritto
> (`preventivi_service.py`); è la base del push usata anche dall'handler pratica
> `vendita.push_preventivo`. **PR2 "emissione immediata" (§9) NON implementata come
> scritta**: superata dal driver batch fatturazione (`run_fatturazione_batch`, corsie
> immediata `GIORNALIERO` / differita `MASSIVO`) — vedi
> [analisi-commesse-stato-e-sviluppi.md](analisi-commesse-stato-e-sviluppi.md).
> Doc spostato in `work-done/`. I **test del giro push→commessa→fatturazione**
> (preventivo + ordine) sono in
> [a-test-push-commesse-fatturazione.md](a-test-push-commesse-fatturazione.md).

## 1) Obiettivo

Completare il pulsante "Push commessa" del drawer preventivo: oggi e'
end-to-end **stub** (BE risponde 200 ma non scrive nulla), il modello
push-commesse esiste solo come **batch globale** invocato manualmente o
da scheduler. Vogliamo render-lo invocabile per **un singolo preventivo**
mantenendo l'invariante:
*ogni operazione di scrittura su `vendite.commesse_attivita` deve passare
dall'orchestrator e dal log `commesse_push_log`*
(no bypass diretto handler → repo).

## 1.bis) Scope di QUESTO sviluppo (PR1)

Decisione architetturale del 2026-05-10: sviluppo concentrico in 2 PR.
**PR1 (questa)** copre **solo la Fase 1 commesse** (push singolo
preventivo verso `commesse_attivita`). Il flag
`fatturazione_immediata=TRUE` viene **propagato** correttamente dalle
sorgenti alle righe commessa (gia' fatto da `BoMComponentExpander`/
`HandlerPreventivi` esistenti) ma **non scatena** l'emit immediato verso
`attivita_fatturabili`. Per quel pezzo (Fase 3 puntuale, "servizio
emissione immediata" elencato come "sviluppo necessario minimo" in
[fatturazione-attivita-progetto.md §"Emissione immediata"](../work-in-progress/fatturazione-attivita-progetto.md))
seguira' una **PR2** dedicata, che scrivera' lotto giornaliero APERTO,
emit puntuale, log su `fatturazione_lotti_log`. Vedi §9 in coda.

UX di PR1 per preventivi `fatturazione_immediata=TRUE`: dopo il push, il
toast informa l'utente che l'emit verso AF avverra' al prossimo run
pipeline lotto (oggi: batch). Niente bug, niente toast bugiardo.

## 2) Design — pattern concentrico

Il pattern push-commesse passa attraverso 4 layer:

```text
preventivi_service.push_a_commessa(preventivo_id)        ← entrypoint UI
   │
   └─► commesse_service.pr_run_commesse_push_one(*, sorgente_codice, sorgente_uid)
          │
          └─► CommessaPushOrchestrator.run(*, source_types, dry_run, sorgente_uid)
                 │
                 └─► BaseSourceHandler.run(*, dry_run, sorgente_uid)
                        │
                        └─► CommesseRepository.fetch_pushable_rows(*, sorgente_uid)
                               │
                               └─► vendite.fn_list_preventivi_da_pushare(..., p_preventivo_id)
```

Ogni layer espone `sorgente_uid: int | None = None` come keyword arg
opzionale. `None` = batch (comportamento attuale invariato), valore = push
singolo. Il filtro arriva fino alla DB function (vedi brief DB gemello).

Il flag `sorgente_uid` e' generico: vale per preventivi oggi, e per
ordini/DDT/contratti domani senza ulteriori cambi al pattern. Nome scelto
appositamente generico (`sorgente_uid` invece di `preventivo_id`) per
seguire il principio concentrico.

## 3) Modifiche file Python

### 3.1 `backend/apps/vendite/db/commesse_repository.py`

Estendere [`fetch_pushable_rows`](../../../../backend/apps/vendite/db/commesse_repository.py):

```python
def fetch_pushable_rows(
    self,
    sorgente_codice: str,
    *,
    competenza_mese: date | None = None,
    billing_account_id: int | None = None,
    limit: int | None = None,
    sorgente_uid: int | None = None,   # NUOVO
) -> list[PushableRow]:
    ...
    cursor.execute(
        f"SELECT * FROM {fn_name}(%s, %s, %s, %s)",   # 4 args ora
        [competenza_mese, billing_account_id, limit, sorgente_uid],
    )
    ...
```

**Commento "Scopo"** sopra il metodo: aggiungere riga sul filtro
`sorgente_uid` (opzionale — filtra alla riga sorgente specifica del
documento, default NULL = lista globale).

### 3.2 `backend/apps/vendite/services/commesse_source_handlers.py`

Estendere [`BaseSourceHandler`](../../../../backend/apps/vendite/services/commesse_source_handlers.py):

* `run(*, dry_run: bool = False, sorgente_uid: int | None = None) -> HandlerResult`
* `_process_rows(*, dry_run, ..., sorgente_uid: int | None = None)`
  passa `sorgente_uid` a `self._repo.fetch_pushable_rows(...)`.

**Commento "Scopo"**: aggiungere riga "se `sorgente_uid` valorizzato,
processa solo la riga sorgente del documento corrispondente; `None` =
batch handler standard".

### 3.3 `backend/apps/vendite/services/commesse_push_orchestrator.py`

Estendere [`CommessaPushOrchestrator.run`](../../../../backend/apps/vendite/services/commesse_push_orchestrator.py):

```python
def run(
    self,
    *,
    source_types: list[str] | None = None,
    dry_run: bool = False,
    sorgente_uid: int | None = None,   # NUOVO
) -> PushReport:
```

In `_run_locked` propagare `sorgente_uid` a `handler.run(...)` per ogni
handler eseguito. Il log `commesse_push_log.risultato` deve includere
anche `sorgente_uid` per tracciabilita'.

**Pattern dell'evento `event_log`**: aggiungere `sorgente_uid` al payload
JSON di `PUSH_STARTED` e `PUSH_COMPLETED` (gia' contiene `source_types`).

### 3.4 `backend/apps/vendite/services/commesse_service.py`

Aggiungere nuovo entrypoint accanto a `pr_run_commesse_push`:

```python
# Scopo: variante puntuale del push commesse — esegue UN solo handler con
# filtro sulla sorgente identificata da `sorgente_uid`. Riusa orchestrator,
# advisory lock e log: differisce dal batch solo per perimetro (1 riga).
def pr_run_commesse_push_one(
    *,
    sorgente_codice: str,
    sorgente_uid: int,
    dry_run: bool = False,
) -> dict:
    repo = CommesseRepository()
    handlers = _build_handlers(repo)
    valid_codes = {h.sorgente_codice for h in handlers}
    ErrorManager.require(
        sorgente_codice in valid_codes,
        code="E_COMMESSA_VALIDATION",
        message="Codice sorgente non valido per push singolo.",
        detail=f"sorgente_codice={sorgente_codice} non in {sorted(valid_codes)}",
        function_name="vendite.commesse_service.pr_run_commesse_push_one",
    )
    orch = CommessaPushOrchestrator(repo, handlers)
    report = orch.run(
        source_types=[sorgente_codice],
        dry_run=dry_run,
        sorgente_uid=sorgente_uid,
    )
    return {
        "stato": report.stato,
        "dry_run": report.dry_run,
        "push_log_id": report.push_log_id,
        "durata_ms": report.durata_ms,
        "handlers": [r.as_dict() | {"handler_name": r.handler_name} for r in report.handlers],
    }
```

**Note**:

* Validazione `sorgente_codice` evita run vuoti se l'invocazione sbaglia
  il codice (in dev tipico durante refactor).
* `dry_run` esposto: utile per smoke test "vediamo cosa succederebbe se
  pushassi" senza scrivere — non chiamato dal FE oggi ma utile in futuro.

### 3.5 `backend/apps/vendite/services/preventivi_service.py`

Riscrivere [`push_a_commessa`](../../../../backend/apps/vendite/services/preventivi_service.py):

```python
# Scopo: Push preventivo accettato in commessa per pipeline fatturazione.
# Strategia: guard stato + chiamata orchestrator filtrato su preventivo_id.
# Atomicita': l'orchestrator ha advisory lock + savepoint per riga.
def push_a_commessa(preventivo_id: int) -> dict[str, Any]:
    repo = PreventiviRepository()
    testata = repo.get_preventivo(preventivo_id)
    ErrorManager.require(testata is not None, code="E_PREV_NOT_FOUND", ...)
    assert testata is not None
    ErrorManager.require(
        testata["stato_codice_interno"] in _STATI_FATTURABILI,
        code="E_PREV_STATO_TRANSIZIONE",
        message="Solo preventivi ACCETTATI possono essere inviati a fatturazione.",
        ...
    )
    righe_count = repo.count_righe_pushable(preventivo_id)
    ErrorManager.require(
        righe_count > 0,
        code="E_PREV_NESSUNA_RIGA",
        message="Nessuna riga eleggibile per fatturazione.",
        ...
    )
    # Esegue il push effettivo via orchestrator: write su commesse_attivita
    # + log su commesse_push_log + event_log. Idempotente via segment_key.
    from apps.vendite.services.commesse_service import pr_run_commesse_push_one
    report = pr_run_commesse_push_one(
        sorgente_codice="PREVENTIVO",
        sorgente_uid=preventivo_id,
    )
    return {
        "preventivo_id": preventivo_id,
        "stato": report["stato"],
        "push_log_id": report["push_log_id"],
        "durata_ms": report["durata_ms"],
        "handlers": report["handlers"],
        "righe_pushable": righe_count,   # diagnostico, allineato al pre-push
    }
```

**Nota errori**: se l'orchestrator ritorna `stato="ERRORE"` o `"PARZIALE"`,
il payload contiene comunque i dettagli per ogni handler (es. errori sulla
singola riga). Il client FE deve esaminare `stato`/`handlers[i].errors`
per mostrare warning/error e non solo "tutto bene". Vedi §5 FE.

### 3.6 `backend/apps/vendite/api/preventivi_views.py`

Riga 482 (endpoint `push_a_commessa`):
nessuna modifica strutturale, solo aggiornare il `extend_schema(responses=...)`
con il nuovo payload (`stato`, `push_log_id`, `handlers`).

### 3.7 Test BE da aggiungere

* `apps/vendite/tests/services/test_preventivi_service.py`:
  * `test_push_a_commessa_ok_orchestrator_called`: mock di
    `pr_run_commesse_push_one`, verifica chiamata con `sorgente_codice="PREVENTIVO"`,
    `sorgente_uid=preventivo_id`. Verifica payload ritorno.
  * `test_push_a_commessa_stato_non_accettato_raises`: gia' presente,
    da preservare.
  * `test_push_a_commessa_nessuna_riga_eleggibile_raises`: gia' presente,
    da preservare.
* `apps/vendite/tests/services/test_commesse_service.py` (o nuovo file):
  * `test_pr_run_commesse_push_one_ok_passa_sorgente_uid`: mock orchestrator,
    verifica `source_types=['PREVENTIVO']`, `sorgente_uid=42`.
  * `test_pr_run_commesse_push_one_codice_sorgente_invalido`: ServiceError
    `E_COMMESSA_VALIDATION`.
* `apps/vendite/tests/services/test_commesse_push_orchestrator.py`:
  * `test_run_with_sorgente_uid_propagated_to_handlers`: mock handler,
    verifica `handler.run(dry_run=..., sorgente_uid=42)` chiamato.
* Smoke test pgTAP coperto dal brief DB gemello (modifica fn).

## 4) Modifiche FE

### 4.1 `frontend/src/vendite/preventivi/api/preventiviApi.js`

`pushCommessa` gia' fixato per `Idempotency-Key`. Nessuna modifica.

### 4.2 `frontend/src/vendite/preventivi/components/PreventiviIntegrazione.vue`

Oggi il `successMessage` e' generico `t('preventivi.push_commessa_ok')`.
Estendere per leggere il payload e:

* mostrare in toast `t('preventivi.push_commessa_ok_dettaglio', { stato, push_log_id })`
  se `stato === 'COMPLETATO'`;
* mostrare `notify.warn` se `stato === 'PARZIALE'` con conteggio errori;
* mostrare `notify.error` se `stato === 'ERRORE'` con primo errore di handler.

Dopo il push refresh-are il badge `stato_fatturazione` (chiamando
`statoFatturazione(preventivoId)`) cosi' che il pulsante "Invia
fatturazione" si **disabiliti** correttamente quando il preventivo non
e' piu' pushable. Senza questo refresh il pulsante resta cliccabile e
l'utente ne lancia un altro (idempotente sul DB ma confusing UX).

### 4.3 i18n nuove chiavi

* `preventivi.push_commessa_ok_dettaglio`:
  IT: "Push completato (log #{push_log_id})."
  EN: "Push completed (log #{push_log_id})."
* `preventivi.push_commessa_parziale`:
  IT: "Push parziale: alcune righe non sono state inviate. Controllare il log #{push_log_id}."
* `preventivi.push_commessa_errore`:
  IT: "Push fallito. Dettaglio: {primo_errore}."

## 5) Test plan UI §3.4

Dopo il deploy DB+BE+FE, riabilitare lo scenario §3.4 in
[sviluppo-listini-v5-test-ui.md](../work-in-progress/sviluppo-listini-v5-test-ui.md):

* Push preventivo con riga articolo composito → verifica creazione N
  attivita' in `vendite.commesse_attivita` (1 per componente esposto in
  fattura).
* `segment_key` differenziato con suffix `#CMP:{componente_id}`.
* `quantita = quantita_padre × coeff_qta` (no rounding).
* Pulsante "Invia fatturazione" disabilitato post-push (badge stato
  fatturazione aggiornato).
* Toast informa esito + push_log_id.

## 6) Ordine di esecuzione

1. **DB team** atterra brief `brief-db-fn-list-preventivi-push-singolo.md`
   su `dev/db-tid`. Test pgTAP verdi.
2. **BE agent** atterra modifiche §3.1→§3.7 su `dev/backend-tid`.
   Test Django verdi (`apps.vendite.tests`).
3. **FE agent** (stesso branch) atterra modifiche §4.x. Build vite verde.
4. Smoke manuale §3.4 dal browser come da test plan.
5. Spostare questo doc + brief DB in `work-done/` quando smoke verde.

## 7) Bloccanti / dipendenze

* Brief DB gemello deve atterrare PRIMA del BE (signature DB nuova).
* Nessuna dipendenza FE su BE (FE oggi gia' invia idempotency-key OK,
  le modifiche §4.2 sono pure UX/i18n).

## 8) Riferimenti

* Memoria progetto: `feedback_concentrico_no_yagni` — estensione
  generica progettata per altre sorgenti future.
* Memoria progetto: `feedback_db_actions_passaggio_team` — DDL/fn DB via
  brief al team DB.
* Guida: [fatturazione.md §Fase 1](../../guide/fatturazione.md#fase-1---push-sorgenti-su-commesse).
* Guida: [gestione-commesse.md §Flusso push](../../guide/gestione-commesse.md).
* WIP architetturale: [gestione-commesse-v2.md §6.3](../work-in-progress/gestione-commesse-v2.md).

## 9) Prossimo step — PR2: servizio "emissione immediata" (Fase 3 puntuale)

Out of scope per questa PR1, traccia per il task successivo.

**Trigger**: dopo che PR1 e' atterrata, i preventivi con
`fatturazione_immediata=TRUE` producono `commesse_attivita` che riportano
correttamente il flag, ma nessuno scatena l'emit verso AF al di fuori del
batch pipeline lotto. PR2 chiude il gap.

**Componenti da realizzare** (sintesi da
[fatturazione-attivita-progetto.md §"Sviluppi necessari (minimo)"](../work-in-progress/fatturazione-attivita-progetto.md)):

* Servizio Django `emissione_immediata_service.emetti_da_commessa(commessa_id)`:
  * risolve/crea lotto giornaliero APERTO per emittente e data corrente;
  * lock e selezione `commesse_attivita` con `fatturazione_immediata=TRUE`
    sulla commessa;
  * chiama `fn_emit_attivita_fatturabili_da_commessa` con filtro idoneo;
  * collega le AF al lotto giornaliero;
  * logga su `fatturazione_lotti_log`.
* Endpoint API: `POST /preventivi/{id}/emetti-immediato/` oppure
  estensione di `push-commessa` per fare push+emit in un colpo se il
  flag e' attivo (decisione di disegno da prendere a inizio PR2).
* Test BE: orchestrazione + idempotenza + log.
* Test pgTAP: filtro `only_immediate` su
  `fn_emit_attivita_fatturabili_da_commessa` se non gia' presente
  (verifica DB team).
* UX FE: post-push, se `fatturazione_immediata=TRUE` chiama anche
  `emetti-immediato`. Toast informa "Push + emit completati. Lotto
  giornaliero #N aperto."

**Gating**: PR2 si apre solo dopo conferma che PR1 funziona end-to-end
(commesse create, segment_key correto, BoM espansa). Niente sovrapposizione
di scope.
