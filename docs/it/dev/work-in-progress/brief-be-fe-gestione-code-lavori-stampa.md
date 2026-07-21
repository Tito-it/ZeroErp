# Brief BE/FE — UI di gestione code (coda lavori generica + coda stampa)

> **Tipo**: brief operativo BE/FE (piano a step) · **Target**: `dev/backend-tid`
> · **Data**: 2026-07-21 · **Owner**: Tid · **Priorità**: media (osservabilità/governo
> delle code async; non blocca funzionalità).
> **Stato**: 🟡 **PROPOSTA** — analisi su documentazione esistente fatta (§0), decisioni
> di design chiuse (§2) e **tutti i punti P-1..P-5 risolti** (§7). **Scoperta chiave**: esiste
> già il layer core **tracciamento (Anello 0)** senza FE → questo brief lo estende e ne fa
> la prima FE, invece di creare un namespace nuovo (§0). Da approvare gli step prima di
> implementare.
>
> **Contesto**: la Fase C ha reso le code async il motore del cockpit fatturazione —
> `dbops.coda_lavori` (giri on-demand, [brief-design-coda-lavori-generica.md](../work-done/brief-design-coda-lavori-generica.md))
> e `vendite.fatture_stampa_coda` (outbox PDF,
> [brief-db-processi-fatturazione-cockpit.md](brief-db-processi-fatturazione-cockpit.md) §3).
> Oggi il FE vede solo **l'esito del proprio giro** (polling `run/<job_id>/`) e i **conteggi
> coda stampa** (C-5); manca una **superficie di gestione/monitoraggio** delle code in quanto
> tali. Questo brief la costruisce.
>
> **Prerequisito worker**: i drainer `draina_coda_lavori`/`draina_coda_stampa` (systemd
> timer, [brief-deploy-worker-riproducibilita-ci.md](brief-deploy-worker-riproducibilita-ci.md)).
> **Non** siamo in produzione ([[project_no_produzione_solo_sviluppo]]).

---

## 0. Cosa esiste già (verificato — NON si reimplementa)

| Già fatto | Dove | Il brief… |
| --- | --- | --- |
| Conteggi coda stampa per stato + esiti giri | `FatturazioneEsitiPanel.vue` (C-5), `GET /vendite/fatturazione/esiti/` | riusa il pattern card |
| Polling non bloccante di **un** giro | `useJobPolling.js` (C-6/C-7), `GET /vendite/fatturazione/run/<job_id>/` | riusa per il dettaglio job; **serve** un polling di *lista* (nuovo) |
| Ristampa massiva → accoda | C-8, `POST …/lotti/<id>/ristampa/` | fuori scope (già fatto) |
| Verbi Approva/Fattura/Rendi definitive/Invia | C-1..C-8 dashboard | fuori scope (già fatto) |

**Metodi BE già pronti nel repository ma NON esposti** (`apps/core/services/coda_lavori/repository.py`):
`count_per_stato` (scope-agnostico), `annulla` (solo PENDING), `requeue` (IN_CORSO/ERRORE),
`reap_stale`. **Manca**: un metodo `list`/`elenco`, gli endpoint, e l'enforcement di
ownership sulle azioni (`annulla`/`requeue` **non** accettano `owner_scope_key`, a differenza
di `get_stato`).

**⭐ Superficie esistente da riusare (Anello 0)** — `apps/core/api/views_tracciamento.py`:
un layer core di **tracciamento processi/job** già c'è, gated per **area `core`** via
`DomainAPIView`, con endpoint `tracciamento/job-runs/` (`ApiJobRuns`, lista `job_run_log`),
`tracciamento/job-summary/` (`ApiJobSummary`), `tracciamento/audit-log/`,
`tracciamento/task-registry/`, `tracciamento/task-implementations/`, `tracciamento/domini-task/`.
**Ha zero FE.** Quindi questo brief NON crea un namespace nuovo: **estende `tracciamento/`**
con `coda-lavori/` e `coda-stampa/` (fratelli di `job-runs/`) e ne costruisce la **prima FE**
(UI grouping "Processi"). Il worker-liveness del badge riusa `ApiJobSummary`/`fn_list_job_summary`.
La convenzione permessi admin è già fissata: `post_permission = "<oggetto>_manage"`
(`documenti_template_manage`, `ui_preset_manage`) — la si segue, non si inventa (§6).

---

## 1. Le due code — modello e asimmetria di scope (regge tutto il resto)

| | `dbops.coda_lavori` (generica) | `vendite.fatture_stampa_coda` (outbox PDF) |
| --- | --- | --- |
| **Cos'è** | coda job generici (oggi `FATTURAZIONE_GIRO`) | outbox di documenti tipizzato |
| **Stati** | PENDING/IN_CORSO/**FATTO**/ERRORE/**ANNULLATO** | PENDING/IN_CORSO/FATTO/ERRORE (no ANNULLATO) |
| **Scope** | **per-utente** via `scope->>'scope_key'` (whitelist emittenti + `auth_user_id`) | **per-emittente** via JOIN a `vendite.fatture` |
| **Proprietario** | `scope.auth_user_id`/`username` → concetto "job dell'utente" netto | nessun utente proprietario: è del lotto/emittente |
| **Worker** | `draina_coda_lavori`, canale app (RLS operatore), no lock, SKIP LOCKED | `draina_coda_stampa`, canale sistema BYPASSRLS, advisory-lock singolo |
| **Campi UI utili** | `job_type, stato, priorita, tentativi/max_tentativi, ultimo_errore, run_after, claimed/started/ended_at, job_run_id, result, scope.username` | `sorgente_id(=fattura), lotto_id, stato, tentativi, ultimo_errore, documento_id` |

> ⚠️ **Conseguenza portante**: il "mie vs altrui" è **netto per la coda lavori** (ha
> `auth_user_id`), **sfumato per la stampa** (è per-emittente/lotto, non per-utente). Perciò
> il badge è a **due segmenti** (§2 D-C) e le due liste hanno colonne/azioni distinte.

---

## 2. Decisioni di design — CHIUSE (Tid, 2026-07-21)

| # | Decisione | Contenuto |
| --- | --- | --- |
| **D-A** | **Visibilità: lista cross-utente admin-only** | Operatore normale: vede/agisce **solo sui propri** (scope_key per coda lavori; emittenti per coda stampa). Con un **permesso admin dedicato** (§6 prereq DB): vede **tutti** i job con colonna **proprietario**, in sola lettura sui non-propri (le azioni restano scoped al proprietario, l'admin le esegue su tutti). Serve *«capire perché non escono / la coda è impegnata»* senza leak cross-emittente. |
| **D-B** | **Accesso: top bar badge → drawer rapido + link** | Pulsante badge in top bar apre un **drawer rapido** (conteggi + ultimi job propri + stato worker "coda impegnata/worker giù"); da lì un link alla **vista completa a due tab**. Coerente con search/AI drawer (`stores/ui.js`). |
| **D-C** | **Badge: due segmenti** (lavori · stampa) | Due numeri/pallini distinti, perché lo scope delle due code è diverso (per-utente vs per-emittente). Conteggio = job **in corso** (PENDING+IN_CORSO) dell'operatore per ciascuna coda. |

**Invarianti** (dal cockpit, valgono anche qui):
- **I-1** — nessuna seconda logica di scope: si riusa `scope_key`/`add_emittente_scope_condition` esistenti.
- **I-2** — gate stato dalle **codici** stabili (mai la descrizione display), come `LottoDrawer`.
- **I-3** — enforcement ownership sulle **azioni** sempre a livello BE (il FE nasconde, il BE blinda). L'admin bypassa via permesso, non via FE.
- **I-4** — il read-side esistente (C-5 esiti, C-3 polling) **non si tocca**: le nuove liste sono superfici accanto.

---

## 3. FASE BE — endpoint di lista, dettaglio, azioni, conteggi

> Namespace: **estende il tracciamento core esistente** (area `core`, aree_funzionali id 10) —
> `core/api/views_tracciamento.py`. Nuovi endpoint `tracciamento/coda-lavori/` e
> `tracciamento/coda-stampa/`, fratelli di `tracciamento/job-runs/`. `DomainAPIView`
> (`area_funzionale = core`) come le altre view di tracciamento; lo scope per-operatore è
> applicativo (§BE-1). UI grouping utente = **"Processi"** (P-1 chiuso).

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| BE-1 | **`CodaLavoriRepository.list(...)`** | Nuovo metodo: proietta `id, job_type, stato, priorita, tentativi, max_tentativi, ultimo_errore, run_after, claimed_at, started_at, ended_at, job_run_id, result, scope->>'username' AS proprietario, scope->>'scope_key'`, **+ `is_mio` (bool: `scope->>'scope_key' = :caller_key`)** — calcolato dal BE, il FE non confronta id (P-5, come `PraticheCodaLavoro`). Filtri: `stato IN (...)`, `job_type`, intervallo data (`data_insert`), `solo_vivi`. Scoping: `owner_scope_key` (operatore → `WHERE scope->>'scope_key' = :key`; con `code_manage` → nessun filtro). Paginato (`usePagedDashFetch`-friendly: `LIMIT/OFFSET`, `ORDER BY priorita, id`), `total` via `COUNT(*) OVER()`. | ✅ 2026-07-21 — `CodaLavoriRepository.elenca(...)`, smoke DB verde (is_mio/scope/total/paginazione) |
| BE-2 | **`count_per_stato` scoped** | Aggiungere `owner_scope_key` a `count_per_stato` (oggi scope-agnostico) → conteggi per stato filtrati per operatore, o totali per admin. Base del badge (§4). | ✅ 2026-07-21 — param `owner_scope_key`, smoke verde |
| BE-3 | **Ownership su azioni** | `annulla`/`requeue` accettano `owner_scope_key` (mirror di `get_stato`): l'`UPDATE` filtra anche `scope->>'scope_key' = :key` → un operatore agisce **solo sui propri** (0 righe = 404, indistinguibile). Con `code_manage` (§6) → `owner_scope_key=None` = qualunque job. | ✅ 2026-07-21 — `annulla`/`requeue` con `owner_scope_key`, smoke: scope errato→False, giusto→True |
| BE-4 | **Endpoint conteggi badge** | `GET tracciamento/code/conteggi/` → `{coda_lavori:{pending,in_corso}, coda_stampa:{pending,in_corso}, worker:{coda_lavori:{ultimo_run,attivo}, coda_stampa:{...}}}`, scope operatore. Riusa BE-2 + `count_coda_stampa_per_stato(auth_user_id=...)` (già scoped) + **`fn_list_job_summary`** (worker-liveness, riuso `ApiJobSummary`). | ⬜ |
| BE-5 | **Endpoint lista coda lavori** | `GET tracciamento/coda-lavori/` (paginato, filtri §BE-1). Scope operatore di default; `?ambito=tutti` consentito **solo** con `code_manage` (§6) → colonna proprietario popolata. | ⬜ |
| BE-6 | **Endpoint lista coda stampa** | `GET tracciamento/coda-stampa/` — riusa `pipeline_repository` (JOIN `fatture`: numero/emittente, `lotto_id`, stato, tentativi, ultimo_errore, documento_id). Scope emittente operatore; `?ambito=tutti` con `code_manage`. | ⬜ |
| BE-7 | **Azioni coda lavori** | `POST tracciamento/coda-lavori/<id>/annulla/` (solo PENDING) · `POST …/<id>/requeue/` (IN_CORSO/ERRORE, `extra_tentativi`). Own-job: ammesso a chi l'ha accodato (ownership BE-3). Job altrui: richiede `code_manage`. Idempotenti (0 righe = no-op parlante). | ⬜ |
| BE-8 | **Dettaglio job (drawer)** | `GET tracciamento/coda-lavori/<id>/` → `get_stato` esteso: `payload, scope(proprietario), tentativi, ultimo_errore, result, timeline(claimed/started/ended), job_run_id`. Scoped/`code_manage` come le liste. | ⬜ |
| BE-9 | **Test + doc** | Test service/API (scope operatore, admin `ambito=tutti` con `code_manage`, ownership su annulla/requeue = 404 fuori scope, conteggi, worker-liveness). Doc `api_*`. Nessun DDL nuovo (i campi ci sono già). | ⬜ |
| — | *(rimosso)* | Ritenta manuale coda stampa: **non in scope** (P-4) — il drainer ritenta già in automatico; uno sblocco manuale si aggiungerà solo se emergerà un caso di ERRORE terminale ricorrente. | — |

**Nessuna RLS DB nuova**: l'enforcement resta **applicativo e centralizzato** (scope_key per la
coda lavori, JOIN emittente per la stampa), coerente con come sono scoped oggi `run/<id>/` ed
`esiti/`. (RLS su `dbops.coda_lavori` = eventuale ondata futura, fuori scope.)

---

## 4. FASE FE — badge, drawer rapido, vista a due tab

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| FE-1 | **Composable polling conteggi** | Nuovo BB `useQueueCountsPolling` (o modalità "poll periodico" affiancata a `useJobPolling`): fetch ricorrente di BE-4 (setTimeout ricorsivo, no accavallamento), espone `{lavori, stampa, workerOk}` reattivi. **Cadenza 60 s** (il worker drena ~1 min → 30 s raddoppierebbe le richieste per lo stesso numero); **sospeso quando la tab è nascosta** (`document.visibilitychange`), riprende al ritorno (P-3 chiuso). | ⬜ |
| FE-2 | **Badge in top bar** | `.topbar-icon-btn` in `AppTopbar.vue` (icona `pi pi-inbox`/`pi pi-server`) con **due segmenti** `Badge` (lavori · stampa), pattern overlay di `AlertScadenzeWidget.vue`. Click → apre drawer via `stores/ui.js` (nuovo `codeDrawerVisible/openCodeDrawer`). Responsive: promozione nel kebab su mobile. | ⬜ |
| FE-3 | **Drawer rapido** | Conteggi (2 card, clone `FatturazioneEsitiPanel`) + **ultimi N job propri** (stato/tipo) + banner **"coda impegnata"** (worker attivo, ultimo drain Xs fa) o **"worker giù"** (nessun run recente in `job_run_log`). Footer link **«Apri gestione completa →»** (rotta §FE-4). | ⬜ |
| FE-4 | **Vista completa a due tab** | Rotta area **core** (grouping "Processi"; è la prima FE del tracciamento core — un domani ci sta anche un tab "Giri/Job" su `tracciamento/job-runs/`) con `Tabs`: **Coda lavori** \| **Coda stampa**. Ogni tab = lista pattern `LottiListView` (`DataTable` lazy + `usePagedDashFetch` + toolbar filtri **stato**(`Select`)/**tipo**/**data**(`DatePicker`) + `RowActionsMenu`). Toggle **«Tutti / Solo i miei»** visibile **solo** con `code_manage` (`useActionPermission`), passa `?ambito=tutti`. | ⬜ |
| FE-5 | **Righe mie=azionabili / altrui=readonly** | Pattern `PraticheCodaLavoro.vue`: flag per-riga `is_mio` (dal BE: `scope_key` combacia con quello dell'operatore) → azioni riga solo se `is_mio` (o admin); altrui = sola lettura con colonna **proprietario**, per *capire perché la coda è impegnata*. Azioni: **Annulla** (solo PENDING), **Requeue/Sblocca** (IN_CORSO/ERRORE), **Dettaglio**. Gate combinato readonly-area + permesso + stato (codici stabili). | ⬜ |
| FE-6 | **Drawer dettaglio job** | Shell `LottoDrawer.vue`: testata `Tag` stato (severity da §FE-7), tab **Dati** (payload, proprietario, priorità, timeline claimed/started/ended, `job_run_id`), tab **Tentativi/Errore** (tentativi/max, `ultimo_errore`), tab **Esito** (`result`). Coda stampa: dettaglio fattura/lotto/documento_id. | ⬜ |
| FE-7 | **Severity + i18n + icone + CSS** | Centralizzare `statoCodaLavoriSeverity` (PENDING=warn, IN_CORSO=info, FATTO=success, ERRORE=danger, ANNULLATO=secondary) e `statoCodaStampaSeverity` in `core/utils/severity.js` (oggi inline in `FatturazioneEsitiPanel`). i18n sotto radice **area globale/core** (es. `processi.code.*`), chiavi esplicite. Icone in `NAV_ICONS`/`MANAGE_ICONS`. Classi `app-*`. | ⬜ |
| FE-8 | **Test + doc** | build/lint/i18n parity; catalogo BB FE se emergono estrazioni (il composable conteggi è un candidato BB). | ⬜ |

**Gate di uscita**: dall'app un operatore vede a colpo d'occhio (badge) quanti suoi processi
sono in corso, apre il drawer per capire se **la coda è impegnata** o il **worker è giù**, e
dalla vista completa governa (annulla/requeue) **i propri** job; l'admin vede e governa
**tutti**, con proprietario visibile.

---

## 5. Fuori scope (per non cercarlo)

- **C-5/C-6/C-7/C-8** (esiti, verbi con polling, ristampa): già fatti, si riusano.
- **RLS DB** su `dbops.coda_lavori` / attivazione su `fatture_stampa_coda`: enforcement resta
  applicativo (decisione §3). Eventuale ondata RLS = futura.
- **Deploy worker** (systemd timer): [brief-deploy-worker-riproducibilita-ci.md](brief-deploy-worker-riproducibilita-ci.md).
- **Attivazione G2** stampa in pipeline: [brief-db-processi-fatturazione-cockpit.md](brief-db-processi-fatturazione-cockpit.md) §6 (C-10).
- **LISTEN/NOTIFY** presa in carico istantanea del worker: futuro (design coda §7).
- Nuovi `job_type` (PEC/report/export): si aggiungono con seed+handler, questa UI li mostra
  **da sola** (è generica sul `job_type`) — nessuna modifica FE per tipo.

## 6. Prerequisiti DB (al team DB — [[feedback_db_actions_passaggio_team]])

- **Seed UNA azione di processo** `code_manage` (**area 10 `core`**, `pericolosa=f`) — segue
  la convenzione `<oggetto>_manage` già in uso (`documenti_template_manage` area 11,
  `ui_preset_manage` area 9). Sblocca: la vista cross-utente (`?ambito=tutti`) **e** le azioni
  su job altrui (annulla/requeue). Append a `config/azioni_processo.csv` (prossimo id: **28**;
  loader `runOnChange`, nessun nuovo loader). **Nessun DDL** — i campi delle code esistono già.
  - *Read base e own-job actions*: NON richiedono `code_manage` — bastano l'accesso all'area
    `core` (come le altre view di `tracciamento/`) + l'ownership (`scope_key`). `code_manage`
    è solo per il salto a "tutti / job altrui".
- (Opzionale, futuro) vista cross-utente **senza** `code_manage` → policy RLS di lettura
  globale a campi ridotti su `dbops.coda_lavori`. **Non** in questo brief (D-A la evita).

## 7. Punti — stato

| # | Punto | Esito |
| --- | --- | --- |
| P-1 | Area/rotta della vista | ✅ **CHIUSO**: area `core`, estende `tracciamento/` (Anello 0), UI grouping "Processi". Voce menu secondaria opzionale; accesso primario = badge top bar (D-B). |
| P-2 | Permesso admin | ✅ **CHIUSO**: `code_manage` (area 10 `core`, convenzione `_manage`). Read base + own-job = accesso area `core` + ownership, no permesso extra. §6. |
| P-4 | «Ritenta» coda stampa | ✅ **CHIUSO**: fuori scope — il drainer ritenta già in automatico. |
| P-5 | `is_mio` calcolato dal BE | ✅ **CHIUSO**: flag `is_mio` dal BE (confronto `scope_key`), come `PraticheCodaLavoro`. Vedi BE-1/FE-5. |
| P-3 | Cadenza polling badge | ✅ **CHIUSO**: 60 s, sospeso quando la tab è nascosta (FE-1). |

---

*Brief vivo: chiudere gli step aggiornando la colonna Stato (⬜ → ✅ con data); a fine cantiere
il documento passa in `work-done/` con il consuntivo. Nessuna azione DB dall'agent: il seed
del permesso (§6) passa al team DB.*
