# Analisi — Simmetrie di orchestrazione del ciclo vendite (commesse → AF → fatturazione)

> ## ✅ CHIUSA — 2026-08-09
>
> Tutti e tre i temi sono stati risolti: (A) decisione tenuta, (B) BB fan-out estratto e
> difetto dell'esito parziale corretto, (C) `fn_available_actions_lotto` realizzata.
>
> 👉 **Resta solo la validazione in-app del §B**, che vive in
> [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md) **§13.1**
> — l'unico documento della linea rimasto aperto.
>
> Questo doc resta come **fonte del disegno**: è qui che è stata posta la domanda giusta
> («dove sono le simmetrie vere?») e qui che si legge perché commessa→AF **non** doveva
> diventare un dominio pipeline.

---

> **Tipo**: doc di analisi / promemoria di disegno. **NON è un brief DB né un piano
> esecutivo**: serve a fissare conclusioni e candidati emersi in sessione, per non
> perderli. Nessuna azione DB/BE parte da qui senza un brief/piano dedicato e l'ok di Tid.
>
> **Data**: 2026-06-18 · **Ultimo aggiornamento**: 2026-08-09 (§B eseguito) ·
> **Stato**: ✅ **TUTTI E TRE I TEMI CHIUSI** — pronto per `work-done` dopo la
> validazione in-app del §B
>
> **Origine**: discussione a valle del gap `tipo_doc_fiscale` nel batch fatturazione
> (vedi [brief-db-emittibili-lane-tipo-doc-fiscale.md](brief-db-emittibili-lane-tipo-doc-fiscale.md)).
> Tre temi: (A) quanto è generico il motore pipeline, (B) candidato BB "fan-out isolato"
> da non perdere, (C) avanzamento stati lotto AF→fatturazione innescato da UI.
>
> ## Stato dei tre temi al 2026-08-09
>
> | # | Tema | Stato |
> |---|---|---|
> | A | Non ricostruire commessa→AF come dominio pipeline | ✅ **decisione tenuta** — `dbops.domini_task` ha ancora i due domini seedati, nessun sottosistema ricomparso |
> | B | BB fan-out isolato + run log | ✅ **FATTO** (2026-08-09) — `apps/core/services/fan_out.py` + due call-site convertiti, **e** il difetto di esito parziale del pull corretto. Vedi §B.2 |
> | C | `fn_available_actions_lotto` + capability FE | ✅ **FATTO** (2026-08-04/06) — DB + BE + FE, vedi §C.5 |
>
> Chiuso anche il prerequisito che apriva la sintesi: il gap `tipo_doc_fiscale` è in
> work-done insieme ai due gemelli di corsia (`utility_id`, `fatturazione_immediata`).
>
> 👉 **Il §B è stato eseguito**: piano dei residui in
> [piano-residui-orchestrazione-e-cruscotti-vendite.md](piano-residui-orchestrazione-e-cruscotti-vendite.md) §1
> (R-1), brief esecutivo e consuntivo in
> [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md).
> Questo doc resta la fonte del **disegno**; quelli sono l'**esecuzione**.

---

## A. Stato del motore pipeline: già generico, e una lezione storica

**Il motore è già generico e multi-dominio per disegno:**

- Registry a DB pensato per N domini: `dbops.domini_task` (seedati **due** domini:
  `FATTURAZIONE` e `ATTIVITA_FATTURABILI`), `dbops.pipeline_task_registry`,
  `dbops.pipeline_task_registry_impl` (dispatch via `implementation_key`, niente eval
  dinamico). Funzioni `dbops.fn_check_pipeline_task_registered` /
  `fn_get_pipeline_task_implementation` + pgTAP.
- Runner/executor applicativi (`LottoPipelineRunner`, `PipelineStepExecutor`) con **logica
  di dominio ~zero**: risolvono gli step da tabella, fallback (utility/tipo_doc), tracing
  task-run, rollback. Unico accoppiamento: `VenditePipelineRepository.DOMINIO_CODE =
  "FATTURAZIONE"` come default + la `handler_registry` (10 handler di fatturazione).
- Visione documentata in [pipeline-domini-engine.md](pipeline-domini-engine.md):
  "pipeline DB separate per dominio, engine applicativo unico".

**Lezione storica decisiva** (`db/changelog/.../20260227-16-drop-attivita-pipeline-deprecated`):
fu costruito un **intero sottosistema pipeline stateful per le attività** (15 funzioni:
`fn_get_or_create_lotto_attivita`, `fn_set_attivita_lotto_stato`,
`fn_*_attivita_lotto_task_run`, branch policy…, + tabelle task-run dedicate) e poi
**droppato**. In parallelo `fn_emit_attivita_fatturabili_da_commessa` ha **perso**
`p_lotto_attivita_id`. Il processo **commessa→AF** è stato **collassato** in un singolo
task idempotente (`pull_attivita_da_commessa`), step 0 della pipeline FATTURAZIONE.

**Conclusione A**: i due processi *non sono simmetrici nell'essenza*:

| Processo | Natura | Ha bisogno del motore pipeline? |
|---|---|---|
| AF → fatturazione | ciclo di vita **fiscale stateful** (stati DRAFT→EMESSA→DEFINITIVA→INVIATA, numerazione, rollback) | **Sì** — giustamente è un dominio pipeline pieno |
| commessa → AF | **promozione idempotente stateless** (scopri → emetti → marca EMESSA) | **No** — è un fan-out; la macchina pesante fu provata e ritirata |

→ **Non** ricostruire commessa→AF come dominio pipeline: re-litiga la deprecazione
`20260227-16`. Decisione confermata con Tid (2026-06-18).

---

## B. Candidato BB da NON perdere — "fan-out con isolamento + run log"

La simmetria *reale e utile* è più in basso. Due processi condividono la stessa forma:

| Fase | `sorgenti → commessa` (`CommessaPushOrchestrator._run_locked`) | `commessa → AF` (`PipelineStepExecutor._handle_pull_attivita_da_commessa_task`) |
|---|---|---|
| discovery | `_resolve_handlers(source_types)` | `commesse_repository.list_commesse_emittibili(...)` |
| fan-out isolato | `for handler: try/except → HandlerResult` | `for commessa: transaction.atomic (savepoint) + try/except → errors[]` |
| aggregazione esito | `_compute_stato(results)` | "se tutte falliscono → raise; altrimenti prosegui" |
| log del run | `PUSH_STARTED` / `log_push_run` + `event_log` | `event_log` + `PipelineErrorLogger` |

Entrambi reimplementano a mano: **"scopri item → per ognuno isola l'errore (savepoint) →
aggrega esiti → logga il run"**.

**Candidato** ([feedback_regola_del_2_estrai_bb]): estrarre un BB generico di fan-out, es.
`apps/core/services/` — concettualmente:

```text
risultato = run_fan_out(
    items=<iterabile discovery>,
    process=<callable per-item>,        # eseguito in savepoint
    on_error=<policy: skip+log | abort>,
    aggregate=<callable esiti → stato>, # es. ALL_OK / PARTIAL / ALL_FAIL
    run_logger=<start/end run + event_log>,
)
```

**Stato**: ✅ **ESEGUITO il 2026-08-09** (ok Tid). Mini-protocollo regola del 2 rispettato per
intero: candidato dichiarato a chat il 2026-06-18, ok ricevuto, ed estrazione fatta toccando
**due call-site nello stesso intervento**. Esito in **§B.2**.

**Quando**: dopo la chiusura del gap `tipo_doc_fiscale` — prerequisito soddisfatto, poi
eseguito. Vedi conclusione condivisa "punto 2" della sessione 2026-06-18.

### B.1 — Due fatti nuovi, da leggere prima di estrarre (2026-08-09)

**Il terzo occorrente è arrivato, ed è già generico.**
`QueueDrainEngine` (`apps/core/services/coda_lavori/drain_engine.py`, luglio 2026) è
esattamente «claim item → per-item best-effort → tally → retry con backoff», costruito UNA
volta e parametrizzato da un `QueueBackend` + una callback `per_item`. **Non** sostituisce
il candidato — lavora su una coda a DB con claim e ritentativi, non su una lista scoperta
in memoria da consumare una volta sola — ma cambia il disegno del task: prima di estrarre un
secondo motore va deciso **se i due convergono** (il fan-out come backend "lista effimera"
del drain engine) o se restano due astrazioni distinte con confini dichiarati. Estrarne un
terzo in parallelo, senza rispondere a questa domanda, è il modo di avere tre motori.

**L'aggregazione esito diverge già dentro lo stesso file.** Il pull da commessa solleva solo
se falliscono **tutte** le commesse (`E_PULL_COMMESSA_ALL_FAILED`): un rifiuto **parziale**
chiude il `task_run` come COMPLETATO, e al rilancio dello step il resolver dà SKIP. Il
fratello `snapshot_indirizzi_lotto`, poche righe sotto nello stesso
`pipeline_step_executor.py`, usa invece `TaskEsitoParziale` (task_run in ERRORE **senza**
sollevare) proprio per evitare quel buco. È la riga "aggregazione esito" della tabella qui
sopra: la policy va **decisa una volta** nel BB, non lasciata divergere per handler.

### B.2 — Esito (2026-08-09)

Entrambi i fatti del §B.1 hanno trovato risposta, e il secondo si è rivelato la ragione
principale per fare il lavoro.

**Il BB c'è**: `apps/core/services/fan_out.py` — `run_fan_out` (savepoint per item, cattura,
stack loggato una volta per tutte), `FanOutEsito` con le **tre parole**
`COMPLETATO`/`PARZIALE`/`ERRORE`, `FanOutRunLogger` a metodi opzionali. Le tre parole non
sono nuove: `CommessaPushOrchestrator._compute_stato` le usava già — il BB le ha rese
disponibili a tutti invece di lasciare che ogni chiamante ne reinventasse due.

**I call-site convertiti sono due**, come imponeva il caveat: il pull da commessa e
`BaseSourceHandler._process_rows`. La coda batch di quest'ultimo è rimasta **fuori** dal BB.

**Il difetto è chiuso**: il pull restituisce `TaskEsitoParziale` sul rifiuto parziale, quindi
il `task_run` va in ERRORE senza sollevare e al rilancio il resolver dà RESUME. Le commesse
rimaste indietro vengono davvero ritentate. Codice errore **riusato** (`E_PULL_COMMESSA`,
già seedato): nessuna azione DB.

**Tre correzioni al §B.1 e al disegno iniziale**, emerse leggendo il codice:

1. **I siti erano tre, non due, e l'accoppiamento originale era al livello sbagliato.** Il
   gemello vero del pull è `_process_rows` (righe sorgente), non `_run_locked`. Quest'ultimo
   itera su handler che sono *essi stessi* fan-out: è un **aggregatore**, e infatti non isola
   in transazione.
2. **`_run_locked` è stato valutato e SCARTATO** (§F5 del brief): lì «fallito» significa «il
   report contiene errori», non «ha sollevato», e sulla lista vuota risponde ERRORE mentre un
   fan-out risponde COMPLETATO. Due semantiche corrette ciascuna nel proprio contesto: la
   motivazione è scritta nel docstring di `_compute_stato` perché nessuno le appiani.
3. **La convergenza col `QueueDrainEngine` è stata scartata** (D-1, ok Tid): due astrazioni,
   con il **confine scritto in entrambi i file** — se l'item deve essere ritrovato *dopo* il
   run è roba della coda, se basta riscoprirlo è `run_fan_out`.

Resta la **validazione in-app** (Tid) e il commit. Consuntivo completo, scostamenti e residui
noti: §11 del [brief](brief-be-fan-out-isolato-e-esito-parziale.md).

---

## C. Avanzamento stati lotto AF→fatturazione da UI — ✅ FATTO (2026-08-04/06)

> ⚠️ **Il §C.2 qui sotto descrive un gap che NON esiste più.** È conservato come traccia
> del ragionamento; per lo stato reale vedere **§C.5** in fondo.

**Contesto (Tid)**: l'avanzamento degli stati del lotto (DRAFT→EMESSA→DEFINITIVA→…)
sarà **quasi sempre innescato da UI** (operatore), non da schedulazione. Serve capire il
collegamento con quanto fatto sul driver commesse.

### C.1 Cosa esiste GIÀ (più di quanto sembri)

L'orchestrazione di avanzamento è già a due velocità, **entrambe già esposte**:

- **Single-step** — `LottoPipelineRunner.run_pipeline()` esegue **UN solo step per
  chiamata** (avanzamento incrementale; resume/rollback gestiti). Endpoint UI:
  `POST /api/v1/vendite/pipeline/run/` (`ApiRunLottoPipeline`).
- **Run-until-done** — `run_lotto_until_done()` cicla `run_pipeline` finché la catena si
  esaurisce o lo stato `chiude_lotto`. Endpoint UI:
  `POST /api/v1/vendite/pipeline/run-until-done/`.
- **Reset/rollback** — endpoint reset lotto (DRAFT) + rollback step già presenti.

Lo **stesso orchestratore** serve due trigger diversi: il **cron**
(`run_fatturazione_batch`) è solo un *wrapper sottile* attorno a `run_until_done`, sotto
**contesto SISTEMA** (RLS Path A, `system_process_context`) + registrazione in
`job_run_log`. La UI usa gli stessi entrypoint sotto **scope OPERATORE** (JWT normale).

> **Link forte con le commesse**: la logica di avanzamento è **context-agnostica**; è il
> *trigger* a scegliere il regime DB. Cron → contesto sistema + job_run_log; UI → scope
> operatore + event_log. Nessun ramo di codice duplicato per i due mondi.

### C.2 Il vero GAP da predisporre — "azioni disponibili del lotto" data-driven

Oggi **non esiste** un `fn_available_actions_lotto` (esistono i gemelli per
`commessa`/`offerta`/`contratto`). Per una UI pulita, l'operatore deve sapere **quale
transizione è ammessa ORA** su QUESTO lotto, senza che il FE conosca la macchina di stati.

Pattern da replicare (simmetria con `fn_available_actions_commessa` +
`POST /commesse/<id>/stato/`):

- **`fn_available_actions_lotto(lotto_id)`** (DB, data-driven): legge stato lotto +
  `config.stati_doc_fiscale_transizioni` + eventuali segnalazioni bloccanti
  (`LottoSegnalazioniService`) e ritorna le azioni ammesse: `avanza` (→ prossimo stato),
  `avanza_fino_a_fine`, `reset_a_draft`, `rollback_step`, ciascuna con capability/abilitato
  e motivo se disabilitata.
- **FE**: bottoni guidati dalle capability (niente stato cablato lato client), come già
  fatto per commesse/offerte/contratti.
- **Endpoint**: riusare gli esistenti `pipeline/run/` (= "avanza"), `run-until-done/`,
  reset. Eventuale endpoint unico `POST /lotti/<id>/azione/` solo se serve uniformare.

### C.3 Cosa NON serve

- **Niente nuovo motore**: l'avanzamento c'è già (single-step + until-done).
- **Niente schedulazione obbligatoria**: per AF→fatturazione il path primario è UI; il
  cron/sistema resta opzionale (corsia immediata/differita). Il `job_run_log` è per i run
  *headless*; un avanzamento da UI **non** va in `job_run_log` (è tracciato da `event_log`:
  `PIPELINE_STARTED`/`STEP_COMPLETED`/`PIPELINE_COMPLETED`).

### C.4 Conclusione C

Il "processo gemello" che serve **non è un nuovo orchestratore**: l'avanzamento stati è
già pronto e UI-esposto. Ciò che va **predisposto** è il layer **data-driven di azioni
disponibili del lotto** (`fn_available_actions_lotto` + capability FE), per dare
all'operatore la stessa esperienza guidata già presente su commesse. È un incremento
**piccolo e simmetrico**, non un nuovo sottosistema.

### C.5 Esito — ✅ realizzato (2026-08-04/06)

La previsione ha retto, ed è stata eseguita — **non da qui**, ma dal filone *cockpit
fatturazione*, che è arrivato allo stesso punto per la via della UI:

- **DB** — `script.fn_available_actions_lotto` esiste (`20260804-06`, raffinata da
  `20260806-08` con target-state e descrizione), con le tre check dedicate che le due fn di
  mutazione **condividono**: `fn_check_lotto_annullabile`,
  `fn_check_lotto_riportabile_a_draft`, `fn_check_lotto_fatture_pre_fiscali`. È l'ottava
  della famiglia `fn_available_actions_*` (commessa, contratto, ddt, offerta, ordine,
  preventivo, reso). Brief: [brief-db-azioni-disponibili-lotto.md](brief-db-azioni-disponibili-lotto.md)
  e [risposta-db-azioni-lista-lotto.md](risposta-db-azioni-lista-lotto.md).
- **BE** — `VenditeRepository.get_available_actions_lotto` + merge del blob nella testata
  lotto, **dopo** `get_lotto` (unico cancello di scope: la fn non filtra per emittente).
- **FE** — `useLottoAzioni.js`, estratto alla seconda occorrenza (drawer + kebab lista).

**La lezione che il §C.2 non poteva prevedere**: il gap non era teorico. Fino al 2026-07-31
le precondizioni fiscali vivevano come **cinque `computed` in `LottoDrawer.vue`** e avevano
già prodotto un **pulsante-vicolo-cieco** trovato in-app — abilitato lato client, rifiutato
dal DB. Il valore della fn non è stato "una UI più pulita" ma **una sola sorgente di
verità** fra chi mostra il verbo e chi lo esegue.

**Due deroghe dichiarate**: `avanza_step` e `rilancia_step` **non** sono esposte dal DB, di
proposito — il loro verdetto (step successivo, criticità, distinzione avanza/rilancio) vive
per intero nel runner Python. Finché resta lì, quelle due sono gate del frontend.

---

## Sintesi operativa (ordine consigliato) — stato al 2026-08-09

1. ✅ **Gap `tipo_doc_fiscale`**: brief DB → BE driver. **Chiuso**, brief in work-done
   insieme ai due gemelli di corsia (`utility_id`, `fatturazione_immediata`).
2. ✅ **`fn_available_actions_lotto` + capability FE** (conclusione C): **fatto** il
   2026-08-04/06 per la via del cockpit fatturazione — vedi §C.5.
3. ✅ **BB fan-out isolato** (conclusione B): **eseguito** il 2026-08-09 — BB in
   `apps/core/services/fan_out.py`, due call-site convertiti, **e** il difetto di esito
   parziale del pull corretto (che era la ragione vera del lavoro). Vedi §B.2.

> **Tutti e tre i temi sono chiusi.** Questo doc va in `work-done` dopo la validazione in-app
> del §B — l'unica cosa che resta aperta, insieme al commit.
