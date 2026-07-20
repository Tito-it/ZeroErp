# Brief BE/FE — Cockpit processi fatturazione in Dashboard Competenza

> **Tipo**: brief operativo BE/FE (piano a step) · **Target**: `dev/backend-tid`
> · **Data**: 2026-07-19 · **Owner**: Tid · **Stato**: 🟡 **FASI A+B FATTE (2026-07-20,
> non committate) + revisione critica passata** — vedi §«Revisione critica 2026-07-20»
> dopo il gate B. Fase C da iniziare; validazione in-app A+B ancora aperta (DB dev vuoto).
>
> **Design-of-record**:
> [brief-design-gestione-processi-fatturazione.md](brief-design-gestione-processi-fatturazione.md)
> (decisioni **D-1..D-7**, chiuse 2026-07-19).
> **Prerequisito DB**:
> [brief-db-processi-fatturazione-cockpit.md](brief-db-processi-fatturazione-cockpit.md)
> (decisioni **B-1..B-5**, revisione outbox 2026-07-19) — **gate**: gli step che usano le
> azioni di processo e la coda stampa partono a oggetti DB **G1** applicati
> ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Stato prerequisito (2026-07-20)**: ✅ **G1 APPLICATO, COMMITTATO E PUSHATO** (commit
> `67d63cae9`; verificato sul DB vivo: azioni 26/27 attive, coda + `fn_accoda_stampe_lotto`
> esistono, task policy su pipeline 4/6, e G2 correttamente NON attivo — DEFINITIVA contiene
> solo `numera_fatture`). **Gate Fase A aperto.** Valori concreti in §5; la parte stampa
> (C-2*) ha le fondamenta pronte, l'attivazione G2 resta alla release BE (C-10).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]).
> **Parte da**: motore fatturazione completo e headless + le tre lenti vive.
>
> ⚠️ **Sequenza di rilascio vincolante (G1 → BE → G2)** — dal brief DB §2. La stampa entra
> in pipeline solo con l'append G2 ai `processi` DEFINITIVA, e **G2 va committato SOLO dopo**
> che questo BE ha (a) registrato l'handler `stampa_documenti_lotto_default` e (b) schedulato
> il worker drainer. Motivo: la corsia GIORNALIERO esegue la DEFINITIVA da cron ogni notte;
> se la stampa fosse accodata nei `processi` ma l'handler non esistesse, `numera_fatture`
> numererebbe e **poi lo step crasherebbe** (`E_TASK_IMPLEMENTATION_NOT_FOUND`). G1 (coda +
> funzione + seed, tutto inerte) è sicuro da subito; **G2 è l'interruttore**, lo si arma a
> BE deployato. Chi chiude la Fase C **coordina con il team DB** l'apply di G2.

---

## 0. Scopo in una riga

Rendere **azionabile** la Dashboard Competenza: i quattro verbi (**Approva → Fattura →
Rendi definitive → Invia**) più le due superfici di supporto (drawer commessa di governo,
lista/drawer lotti), riusando **le stesse primitive del batch** — mai una seconda
implementazione «da interfaccia».

## 1. Invarianti da non violare (valgono per ogni step)

| # | Invariante | Perché |
| --- | --- | --- |
| I-1 | **Un solo processo, due modi di avvio** | D-1: UI, cron e batch chiamano lo **stesso** core. Se ti trovi a scrivere una seconda logica «per la UI», fermati: va estratta e condivisa |
| I-2 | **Numerazione = numerazione + stampa** | D-1: lo step DEFINITIVA ha due task — `numera_fatture` (numera, atomico) + `stampa_documenti_lotto` (**accoda**, non renderizza). Non due chiamate del caller |
| I-3 | **La cardinalità decide sincrono o batch** | D-2/§2.5 design: **1 documento → sincrono** (calcolo o stampa di una fattura, azione su una commessa); **2+ → batch in background**, la pagina non resta mai bloccata. Criterio unico, per ogni processo di fatturazione |
| I-4 | **La stampa è stupida** | D-7: legge ciò che esiste e genera 1..N documenti. Zero logica di dominio, zero cambi di stato, zero calcoli. Chi la invoca decide *cosa*; lei sa solo *come* |
| I-4b | **Il render non tiene il lock fiscale** | B-1: lo step DEFINITIVA è una transazione atomica e `numera_fatture` tiene l'advisory lock sul registro fino al commit. La stampa **accoda dentro la transazione** (INSERT veloce) e **renderizza fuori** (worker). Mai I/O di rendering dentro la transazione di numerazione |
| I-5 | **Monitoraggio con l'esistente** | D-2: `maintenance.job_run_log` (run) + `vendite.fatturazione_lotti_task_runs` (step/tentativi) + `vendite.event_log` (timeline) + `vendite.fatture_stampa_coda` (stato/tentativi/esito per documento). Niente tabelle **nuove** di tracciamento oltre la coda stampa già decisa dal DB |
| I-6 | **Il read-side non si tocca** | Le viste `vw_dash_*` e i loro endpoint restano invariati: le azioni sono endpoint di comando accanto |
| I-7 | **Gate fiscale visibile** | Pre-fiscale e numerazione non stanno mai dietro lo stesso pulsante |

---

## FASE A — Sbloccare gli stadi (approvazione + drawer commessa)

> Obiettivo: l'operatore svuota `DA_APPROVARE` senza uscire dalla dashboard, e ha finalmente
> un drawer dove **governare** la commessa (oggi esiste solo quello lineage read-only).

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| A-1 | **BE — endpoint approvazione righe commessa** | `POST /vendite/commesse/<id>/attivita/approva/` · body `{righe_ids?: int[]}` (assente = tutte le NON_EMESSA) → `fn_approva_commessa_attivita(p_commessa_id, p_righe_ids, p_user)`. `post_permission = "approva_attivita_commessa"`, `Idempotency-Key` (la fn è già idempotente: 2ª chiamata = 0 righe). Ritorna `{approvate: N}` | ✅ 2026-07-20 — view `ApiCommessaAttivitaApprova` + service `approva_commessa_attivita` (guard input, 404 parlante); repo wrapper già esistente riusato |
| A-2 | **BE — approvazione massiva per competenza** | `POST /vendite/fatturazione/approva-competenza/` · body `{competenza_mese, commessa_ids?}` → popolazione da `vw_dash_competenza_attivita` (`stadio=DA_APPROVARE`, **WYSIWYG con la card**, scope emittente in-vista) e ciclo per commessa in **una** `transaction.atomic()` (all-or-nothing; retry innocuo, fn idempotente); esito `{commesse: N, approvate: M}`. Stesso permesso di A-1 | ✅ 2026-07-20 — view `ApiFatturazioneApprovaCompetenza` + service `approva_attivita_competenza` + repo `list_da_approvare_per_competenza` |
| A-3 | **BE — lista/dettaglio commessa per il drawer** | `GET /vendite/commesse/` (lista minima) + `GET /vendite/commesse/<id>/` | ✅ **NON SERVE** (2026-07-20): il drawer si apre dal drill-down che porta già `commessa_id`, e `GET /commesse/<id>/stato/` (contatori + `capabilities`) + `GET /commesse/<id>/attivita/` (righe) coprono tutto. Nessuna lista commesse necessaria in Fase A |
| A-4 | **FE — `CommessaGestioneDrawer`** | Drawer **autonomo** ([[feedback_drawer_autonomi]]): testata+stato+contatori da `fn_get_commessa_stato`; azioni di stato da `available_actions` via `useDrawerActions`+`DrawerActionsBar`; righe da `GET /commesse/<id>/attivita/` con **selezione multipla** → «Approva selezionate» (A-1); azioni prezzo per riga (N5/N7/sblocco, endpoint esistenti); Passaggi (lineage riusato). Readonly-aware ([[feedback_drawer_readonly]]) | ✅ 2026-07-20 — `src/vendite/components/CommessaGestioneDrawer.vue`: contatori funnel, `DrawerActionsBar` da capabilities, righe con `useSelezioneToggle` (checkbox custom sulle sole BOZZA+NON_EMESSA) + «Approva selezionate/tutte», kebab prezzi N5/N7/sblocco (dialog variazione), `LineagePassaggiPanel`, `content-ready`+`loadDetailOrClose`, gate `useActionPermission` |
| A-5 | **FE — azioni nella Dashboard Competenza** | Card `DA_APPROVARE` → «Approva tutto il mese» con `useConfirmAction` (conferma con **contatore + valore**); kebab `RowActionsMenu` sul drill-down → Approva riga · Apri commessa (apre A-4). Action-gate `action: 'approva_attivita_commessa'`; refresh aggregata + drill-down dopo l'azione | ✅ 2026-07-20 — bottone «Approva mese» sul card DA_APPROVARE (`@click.stop`, conferma con n+valore+mese), colonna kebab nel drill-down (Approva riga solo su DA_APPROVARE + Apri commessa), drawer A-4 montato con `@saved`→refresh. Gate permesso+readonly |
| A-6 | **Test + doc** | Test service A-1/A-2, test API, doc; cataloghi BB se emergono estrazioni | ✅ 2026-07-20 — BE: 10 test service + 8 test API (permission allowed/denied), suite **vendite 1196 + core 604 verdi**, doc `api_commessa_attivita.md` (2 sezioni). FE: **build Vite verde**, **lint pulito**, i18n it+en completa (parity verificata). Nessuna estrazione BB nuova (riusati `useSelezioneToggle`, `mapAvailableActionsToDrawerActions`, `RowActionsMenu`, `useConfirmAction`, `useActionPermission`) |

**Gate di uscita A**: da `/vendite/dashboard-competenza` si porta `DA_APPROVARE` a zero senza
toccare curl, e ogni commessa è ispezionabile/governabile dal drawer. 🟢 **Codice completo,
build+test verdi. Aperto: validazione in-app** (⚠️ su questo DB di sviluppo la vista
`vw_dash_competenza_attivita` è **vuota anche per admin globale** — nessuna riga `DA_APPROVARE`
proiettata — quindi il flusso `Approva mese` non è stato esercitabile end-to-end con dati
reali: da verificare in app con uno scope/dati che popolano la Lente 1).

---

## FASE B — Lotti visibili e governabili

> Obiettivo: il registro dei giri. Serve per le **eccezioni** (errori, reset, recuperi) e per
> il gate fiscale. Endpoint quasi tutti esistenti: è soprattutto FE.

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| B-1 | **BE — dettaglio lotto** | `GET /vendite/lotti/<id>/` (testata + step corrente). Le sotto-risorse esistono già: `fatture/`, `task-runs/`, `segnalazioni/`. ⚠️ Verificato: **nessuna vista DB nuova serve** | ✅ 2026-07-20 — `VenditeRepository.get_lotto` (proiezione+JOIN+mapping condivisi con `list_lotti` via `_LOTTO_SELECT_COLS`/`_LOTTO_JOINS`/`_map_lotto_row`, no duplicazione) + `fn_get_lotto` (scope emittente → 404 `E_LOTTO_NON_TROVATO` su fuori-scope/inesistente) + `ApiLottoDetail` + route `lotti/<id>/`. 4 test API |
| B-2 | **FE — `LottiListView`** | Rotta `/vendite/lotti` + voce di menu vendite (**D-4**): filtri competenza/stato, semaforo stato lotto, kebab → apri drawer | ✅ 2026-07-20 — `src/vendite/views/LottiListView.vue` + `api/lotti.js`; rotta `vendite-lotti` + voce menu (icona `pi pi-server`); filtri mese+stato, `statoLottoSeverity`, row-click e kebab aprono il drawer |
| B-3 | **FE — `LottoDrawer` diagnostico** | Step corrente + fatture + task-run (tentativi/esiti) + segnalazioni. Tab, contenuto deferito (`@after-show`) | ✅ 2026-07-20 — `src/vendite/components/LottoDrawer.vue`: testata + step corrente, 3 tab (Fatture / Task-run con tentativi+esito+errore / Segnalazioni con contatori), banner segnalazioni critiche, `content-ready`+`loadDetailOrClose`. Timeline eventi omessa (nessun endpoint `event_log`; i task-run coprono la traccia operativa) |
| B-4 | **FE+BE — azioni sul lotto** | «Avanza step» · «Rerun» su ERRORE · «Riporta a bozza» (conferma forte e onesta: *demolisce le fatture pre-fiscali; le attività restano libere*) · reset singola fattura DRAFT. Action-gate sui permessi esistenti | ✅ 2026-07-20 — Avanza/Rerun (`pipeline/run/`, stesso endpoint, un step) gated `genera_fatture_lotti` (Rerun solo su ERRORE, Avanza bloccato da segnalazioni critiche); «Riporta a bozza» `danger`+label «Demolisci» + messaggio esplicito, gated `reset_lotto_draft`; reset fattura DRAFT dal kebab, gated `reset_lotto_fattura_draft` |
| B-5 | **FE — raggiungibilità contestuale** | Dal pannello **errori** e dal breakdown `FATTURATA` della dashboard si atterra sul lotto già filtrato | 🟡 **parziale** 2026-07-20 — il `LottoDrawer` è un componente riusabile: montabile dalla dashboard con lo stesso pattern. **Rinviato** l'aggancio dai pannelli errori/breakdown della Dashboard Competenza (richiede il `lotto_id` sulle righe errore/attività — da verificare nel payload; non bloccante per il gate B) |
| B-6 | **Test + doc** | Test API dettaglio lotto; doc; catalogo BB FE | ✅ 2026-07-20 — 4 test API (`VenditeLottoDetailApiTests`: ok/jwt/404/scope), suite vendite verde; **build Vite + lint puliti**; i18n it+en `vendite.lotti` (parity verificata) + nav label; doc dettaglio in `api_lotti_list.md`. Nessuna estrazione BB nuova |

**Gate di uscita B**: un lotto in ERRORE si diagnostica e si sblocca dall'app, senza psql.
🟢 **Codice completo, build+test verdi. Aperto: validazione in-app** (⚠️ su questo DB di
sviluppo `vendite.fatturazione_lotti` e `vendite.fatture` sono **vuote** — 0 lotti — quindi
lista/drawer/azioni non sono stati esercitabili end-to-end con dati reali; `fn_get_lotto`
verificato su 404, `fn_list_lotti` gira). B-5 (aggancio contestuale da dashboard) rinviato,
non bloccante.

---

## Revisione critica 2026-07-20 (pre-commit, tutto il codice A+B)

Review a 8 angoli (3 correttezza + riuso/semplificazione/efficienza + altitudine +
convenzioni) con passo di verifica: 24 candidati → 10 finding confermati → **9 corretti**,
1 segnalato (P-6). Post-fix: **suite vendite 1200 test verdi, lint pulito, build Vite
verde, check i18n verde**.

**Fix funzionali:**

* **Reset-fattura era una feature morta** (B-3/B-4): il gate FE usava
  `descrizione.includes('DRAFT')` ma il seed ha descrizione «Bozza» → l'azione non
  compariva mai. `list_lotto_fatture` ora proietta **`stato_doc_fiscale_codice`**
  (`codice_interno` stabile) e il FE gate su `=== 'DRAFT'` (doc
  `api_lotto_fatture_list.md` aggiornata: i gate FE usano SEMPRE il codice, mai la
  descrizione display).
* **`LottoDrawer` ignorava il readonly d'area**: in LETTURA restavano cliccabili le azioni
  distruttive (incluso «Riporta a bozza»). Ora prop `readonly` + `useInjectReadonly` con
  azioni/kebab nascosti, simmetrico al drawer commessa.
* **Errori silenziosi**: `loadRighe`/`loadTabs` senza catch → tabella vuota
  indistinguibile da «nessun dato». Ora toast fail-visible (`extractApiError`).
* **A-2**: la SELECT della popolazione DA_APPROVARE è stata spostata **dentro** la
  `transaction.atomic()` (snapshot e scritture nella stessa transazione).

**Fix riuso/convenzioni/efficienza:**

* `LottiListView` rifatta su **`usePagedDashFetch`** (prima paginazione hand-rolled senza
  guard anti-race) + eliminato il doppio fetch iniziale (solo `onActivated` sotto
  KeepAlive).
* 6 mappe severity inline (una duplicata byte-identica in 2 file) centralizzate in
  `core/utils/severity.js` (`statoLottoSeverity`, `statoTaskRunSeverity`,
  `statoEsecuzioneFatturaSeverity`, `statoApprovazioneAttivitaSeverity`,
  `statoEmissioneAttivitaSeverity`).
* Dialog N7 → **`AppDialog width="sm"`** (era `<Dialog>` grezzo con width hardcoded).
* Letterale SQL `'DA_APPROVARE'` → costante **`DASH_STADIO_DA_APPROVARE`**
  (vendite_repository, unico owner del vocabolario stadi) passata come parametro; gate
  approvazione deduplicato in un solo computed `canApprova` (dashboard + drawer);
  `prezzo_snapshot != null`; reload mirato post reset-fattura (testata+fatture, non 4
  richieste).

**Scartati in verifica** (falsi positivi o per-spec): loop per-commessa in A-2 (design del
brief), `assert` dopo `require` (AGENTS.md li richiede), array vuoto→400 (fail-safe
corretto), «Avanza» su lotto COMPLETATO (intenzionale: COMPLETATO a EMESSA avanza a
DEFINITIVA), doppia normalizzazione mese (defense-in-depth). Rinviate a Fase C come
migliorie candidate: capabilities BE sul dettaglio lotto (oggi il gating rerun/avanza è su
letterali stato FE) e flag `approvabile` calcolato dal BE sulle righe attività.

---

## FASE C — I verbi «Fattura» e «Rendi definitive» (+ stampa outbox)

> Obiettivo: il cuore del cockpit. Due vincoli reggono la fase: I-1 (si **estrae** il core
> del driver batch, non lo si riscrive) e I-4b (la stampa **accoda dentro** la transazione e
> **renderizza fuori**, in un worker — mai I/O di rendering col lock fiscale tenuto). La
> stampa massiva è quindi un **worker che drena la coda** `vendite.fatture_stampa_coda`, non
> un job che cicla in-linea. ⚠️ Chiudere la fase **coordinando l'attivazione G2** con il team
> DB (C-10) — vedi vincolo di sequenza in testata.

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| C-0 | **BE — generazione documenti eseguibile in contesto sistema (chiude P-1)** | `DocumentGenerationService.genera_documento` usa `user` per **una sola** cosa autorizzazione-critica — calcolare lo scope emittente (`resolve_emittente_scope` → `get_emittenti_ids`); tutto il resto (`generato_da_user_id`, `evento.user_id`, `auth_user_id` nel context) è **audit e tollera già `None`**, e i context builder **non filtrano i dati per utente**. **Decisione (2026-07-19, vedi §4)**: separare *chi autorizza* da *cosa genera* — `genera_documento` accetta lo **scope emittente già risolto** oltre allo `user`. Path web invariato (deriva scope da `user`, i 5 domini non cambiano); path sistema (batch/pipeline) passa `emittente_scope=None` — vede tutto, gira già su canale `system_process_context` BYPASSRLS con emittente **autoritativo** dal lotto — e `audit_user_id=None` (l'attore è già in `app.jwt_user`). **Non-breaking, nessun DB** | ⬜ |
| C-1 | **BE — estrazione core driver** | Da `run_fatturazione_batch` (management command) estrarre `fatturazione_driver_service` (nome indicativo): discovery coppie `(emittente, tipo_doc)` emittibili → lotto per coppia → pipeline per coppia, **best-effort** (una coppia in errore non blocca le altre) + esito strutturato. Nuovo parametro **`fino_a_stato`** (Python puro, nessun DB): il giro da UI e il massivo da cron si fermano a **EMESSA** (D-1). Il command diventa un **chiamante sottile** — comportamento invariato, coperto dai test esistenti | ⬜ |
| C-2 | **BE — cablare la famiglia documentale su FATTURA** | La sorgente `FATTURA` esiste (`config.sorgenti` id 10, target `vendite.fatture`, `key_selector=id`) ma **non è istanziata** sulla factory `build_documenti_sorgente_views` (oggi: preventivi, offerte, contratti, ordini, DDT). Delta ~10 righe → `fatture_documenti_views.py` (genera / anteprima / lista / file / download) + context builder FATTURA + template fattura. **Sblocca la stampa singola sincrona** (I-3) e la ristampa on-demand | ⬜ |
| C-2b | **BE — worker drainer della coda stampa** (sostituisce «processo massivo generico») | Management command su cron/systemd (canale `system_process_context`, come `run_fatturazione_batch`), avvolto in `registered_job` (`maintenance.job_run_log`). Drena `vendite.fatture_stampa_coda`: seleziona i `PENDING` con **`FOR UPDATE SKIP LOCKED`** (più worker non si pestano), per riga → **backstop numerazione** (C-2d) → `DocumentGenerationService.genera_documento` in contesto sistema (C-0) → aggiorna `stato`/`tentativi`/`ultimo_errore`/`documento_id`. **Resiliente per-riga** (un render fallito non ferma gli altri, incrementa `tentativi`, `stato=ERRORE` oltre soglia) e **idempotente** (l'indice unico parziale della coda impedisce doppioni vivi). Non conosce «lotto» o «fatturazione»: sa solo drenare la coda | ⬜ |
| C-2c | **BE — handler task `stampa_documenti_lotto_default`** | Registrato in `PipelineStepExecutor.handler_registry` (il seed DB lo dichiara). **È un adattatore, un one-liner**: `SELECT vendite.fn_accoda_stampe_lotto(<lotto_id>)` — **accoda e ritorna** (I-4b: nessun render dentro la transazione dello step). Non passa id a nessuno, non renderizza. `annullabile=t`, `resume_mode=RESUME_TASK` (seed DB). Ri-eseguibile: ri-accodare è idempotente | ⬜ |
| C-2d | **BE — backstop numerazione nel worker** (B-2) | Prima di generare il PDF, il worker verifica che la fattura sia numerata; se non lo è, la numera via `fn_numera_fattura_opz_emessa(p_fattura_id)` (per-fattura, **idempotente**: già numerata → no-op). **Vive nel worker / context-builder FATTURA, NON dentro `DocumentGenerationService`** (che resta generico e stupido — I-4). Rende **impossibile un PDF non numerato** → D-1 al livello più forte | ⬜ |
| C-3 | **BE — endpoint giro fatturazione** | `POST /vendite/fatturazione/run/` · body `{competenza_mese, fino_a_stato}` · corsia **differita**, perimetro `competenza ≤ M` (cumulativo come il batch), scope emittente dell'operatore via RLS. `post_permission = "genera_fatture_lotti"`, `Idempotency-Key`. **I-3**: multi-coppia → esecuzione in background con run registrato (`registered_job`), risposta = handle del run; la coppia singola resta sincrona | ⬜ |
| C-4 | **BE — endpoint numerazione** | `POST /vendite/fatturazione/numera/` (o `lotti/<id>/numera/` per il singolo) → step DEFINITIVA sui lotti EMESSA del perimetro. `post_permission = "numera_fatture_lotti"`. **I-2**: esegue lo step, che contiene `numera_fatture` **e** `stampa_documenti_lotto` (che accoda) — l'endpoint non chiama la stampa per conto suo; la coda viene poi drenata dal worker | ⬜ |
| C-5 | **BE — esiti dei giri + stato coda stampa** | `GET /vendite/fatturazione/esiti/`: ultimi run per corsia da `maintenance.job_run_log`. **+ stato coda stampa** da `vendite.fatture_stampa_coda` (conteggi PENDING/IN_CORSO/FATTO/ERRORE, per lotto/emittente; RLS scope emittente già sulla tabella) — l'operatore vede se le stampe sono in coda, fatte o in errore. **I-5**: nessuna tabella nuova (la coda è già decisa dal DB) | ⬜ |
| C-6 | **FE — PageActionsBar del mese** | «Aggiorna commesse» (push, endpoint esistente — **D-5**) · «Fattura competenza M» (C-3) · «Rendi definitive» (C-4, azione **separata** e visivamente distinta — I-7) · pannello/chip «esito ultimo giro» + **badge stampe in coda/errore** (C-5) | ⬜ |
| C-7 | **FE — azioni sulle card stadio** | «Fattura adesso» su `DA_EMETTERE` / `EMESSA_NON_FATTURATA`; «Rendi definitive» sul breakdown `FATTURATA/EMESSA`; feedback di avanzamento per i giri in background + refresh a fine run | ⬜ |
| C-8 | **FE — stampa e ristampa** | Da una fattura: «Stampa/Anteprima» **sincrona** (C-2, 1 documento → I-3; componenti documentali già esistenti nei 5 domini — si riusa il pattern); da lotto/selezione: «Ristampa» **massiva → accoda in coda** (C-2b la drena) con stato visibile (C-5). Il singolo passa da `genera_documento`, il massivo dalla coda: due percorsi per cardinalità, un solo render | ⬜ |
| C-9 | **Test + doc + smoke** | Test service driver (fermata a stato, best-effort, perimetro) + worker drainer (SKIP LOCKED, resilienza per-riga, tentativi/ERRORE, idempotenza, **backstop numera-se-manca**) + accodatore; **smoke E2E** «approva → fattura → rendi definitive → drena coda» su dati veri, che verifica **PDF sempre numerato** e **nessun lock fiscale tenuto durante il render** (gli smoke scoprono i GRANT/scope che i test mock non vedono); doc `api_fatturazione.md` + `api_documenti_*` + `api.md` | ⬜ |
| C-10 | **DB — attivazione G2** (coordinata) | A handler + worker deployati, dare l'ok al team DB per l'append G2 ai `processi` DEFINITIVA (brief DB §6). **Non prima** (vincolo di sequenza in testata). Verifica post-attivazione: un giro giornaliero notturno accoda e il worker drena, PDF numerati | ⬜ |

**Gate di uscita C**: un mese di competenza si chiude interamente dall'app, con la
numerazione come atto separato e consapevole; le stampe entrano in coda alla DEFINITIVA, il
worker le drena, ogni PDF è numerato, e l'operatore vede lo stato delle stampe. G2 attivato
in coordinamento col DB.

---

## FASE D — Guida utente

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| D-1 | **Guida** | Sezione «Gestire la fatturazione» nella [guida cruscotti](../../guide/cruscotti-fatturazione.md): i **quattro verbi** in linguaggio non tecnico, cosa fa il cron e cosa fa l'operatore, perché la numerazione è separata. Si salda con la Fase 4 del piano due-lenti | ⬜ |
| D-2 | **Guida fatturazione** | Aggiornare [fatturazione.md](../../guide/fatturazione.md) §«Dashboard operative» (oggi elenca 4 viste ipotetiche) con l'assetto reale | ⬜ |

---

## 2. Fuori perimetro

* **«Invia»/SDI**: predisposto (D-6) ma **spento** finché non esiste il builder XML FatturaPA.
* **Note di credito** (slice NC), integrazione contabile, multi-esercizio, alerting.
* **Push ricorrente contratti** (canoni): indipendente da questo cantiere.
* **Modifiche alle tre lenti**: invariate (I-5).

## 3. Punti aperti da chiudere strada facendo

| # | Punto | Quando |
| --- | --- | --- |
| ~~P-1~~ | ✅ **RISOLTO in design (2026-07-19)** — `genera_documento` in contesto sistema: separare scope-authorization dal generatore. Diventa lo step **C-0**; analisi completa in §4 | — |
| ~~P-2~~ | ✅ **SUPERATO** dal modello outbox (brief DB §0): con lo step che committa veloce (solo INSERT in coda) il fallimento di render vive nei **tentativi della coda**, disaccoppiato dalla numerazione. Nessuno stato «numerata ma non stampata» da gestire nella pipeline. Resta come parametro del worker la **soglia tentativi → ERRORE** (default sensato, tarabile) | — |
| P-3 | Template fattura: non esiste ancora (i template sono dato di configurazione, non seed). Senza, la stampa non ha cosa renderizzare | prima di C-2 in-app |
| P-4 | Soglia oltre cui un'operazione «singola» diventa background (I-3): il criterio è la cardinalità, ma se il documento singolo risultasse lento va tarato sull'evidenza | in C-3, con numeri veri |
| P-5 | Cadenza del worker drainer (cron) e numero di worker paralleli: `FOR UPDATE SKIP LOCKED` regge il parallelismo, ma la cadenza va tarata sul ritardo accettabile tra «Rendi definitive» e PDF disponibile | in C-2b, con volumi veri |
| P-6 | ⚠️ **Scritture famiglia commesse senza scope emittente** (revisione 2026-07-20, CONFERMATO): il nuovo `attivita/approva/` **e** gli endpoint pre-esistenti stato + prezzi N5/N7 non verificano che la commessa appartenga all'emittente dell'operatore, e `commesse`/`commesse_attivita` **non hanno RLS** (analisi RLS: «NO in prima battuta», asimmetria lettura/scrittura già segnalata lì). Un operatore con permesso azione ma scope X può scrivere su commesse di Y per id. Gap **sistemico pre-esistente**, non introdotto dalla Fase A → niente toppa asimmetrica sul solo endpoint nuovo: la soluzione è **RLS su `commesse`/`commesse_attivita`** via brief al team DB ([[feedback_db_actions_passaggio_team]]) | decisione Tid: brief DB dedicato (consigliato prima della release C) |

---

## 4. P-1 risolto — generazione documenti in contesto sistema (design)

**Il problema.** `documenti.DocumentGenerationService.genera_documento` pretende un
`user` autenticato (`guard_user_authenticated`) e ne deriva lo scope emittente
(`resolve_emittente_scope` → `PermissionResolver.get_emittenti_ids`). In un ciclo web c'è il
request user; in un **cron/batch/pipeline** no. Senza fix la stampa funzionerebbe da UI e
**fallirebbe da cron** — proprio la modalità del massivo (D-1).

**Cosa fa davvero `user` dentro `genera_documento`** (verifica sul codice 2026-07-19):

| Uso | Natura | In contesto sistema |
| --- | --- | --- |
| `resolve_emittente_scope(user)` → whitelist emittenti | **autorizzazione** (l'unico critico) | l'emittente è **input autoritativo** del lotto; il canale è già BYPASSRLS |
| `_resolve_template(user, scope=...)` | usa lo **scope** (già risolto); `user` solo per il path `template_documento_id` esplicito, che il batch non usa | scope=None → nessun filtro |
| `_build_context_for_sorgente(user, ...)` → `auth_user_id` nel context | **audit**: i builder **non filtrano i dati per utente** | `None` accettato |
| `generato_da_user_id`, `evento.user_id` | **audit** | `getattr(user, "id", None)` → `None` già tollerato |

Conclusione: **l'unico concern autorizzazione è lo scope emittente**, e in contesto sistema
lo scope non va *derivato* — l'emittente è già noto e il canale è di sistema.

**La decisione.** Separare *chi autorizza* da *cosa genera* (coerente con D-7: la stampa è
stupida, l'autorizzazione è del chiamante). `genera_documento` accetta lo **scope emittente
già risolto** oltre allo `user`:

* **path web** (i 5 domini esistenti + il nuovo FATTURA) — **invariato**: passa `user`, il
  service deriva scope e audit come oggi. Nessuna regressione;
* **path sistema** (batch, pipeline, cron) — passa `emittente_scope=None` (vede tutto — è
  già sotto `system_process_context` su ruolo BYPASSRLS, con l'emittente autoritativo dal
  lotto) e `audit_user_id=None` (l'attore di sistema è già in `app.jwt_user`, impostato dal
  gateway `system_process_context`).

**Perché questa e non le alternative:**

* *Costruire un finto "system user" Django* (`is_authenticated=True`, scope tutto): fa
  passare lo stesso oggetto per due scopi diversi (auth + audit) e reintroduce un utente
  fittizio dove non serve. Scartata: nasconde il concern invece di separarlo.
* *Un secondo metodo `genera_documento_sistema` clonato*: violerebbe I-1 (mai duplicare) e
  D-7 (la logica di generazione deve restare una sola). Scartata.

**Proprietà**: **non-breaking** (i chiamanti web non cambiano), **nessun DB**, **nessuna
dipendenza dal team DB**. È interamente lavoro BE dello step **C-0**, prerequisito di
C-2b/C-2c/C-2d. Il guard di scope resta pieno sul path web (defense-in-depth invariata); sul
path sistema l'autorizzazione è il canale stesso (`system_process_context` fail-loud se il
ruolo non è BYPASSRLS). Il **consumatore reale** del path sistema è il **worker drainer**
(C-2b): il brief DB conferma lo stesso pattern — scrittura del worker in canale sistema,
come `run_fatturazione_batch`.

---

## 5. Fondamenta DB G1 — cosa il BE trova già pronto (valori reali, 2026-07-20)

Scritto dal team DB (commit `67d63cae9`, in attesa di apply). Il BE si aggancia a **questi**
nomi/firme — niente da indovinare:

**Azioni di processo** (`config.azioni_processo`): `26 approva_attivita_commessa` (`pericolosa=f`),
`27 numera_fatture_lotti` (`pericolosa=t`), area `2` (vendite) → per i `post_permission` di A-1/A-2 e C-4.

**Task pipeline** (`dbops.pipeline_task_registry` id 18 / `_impl` id 18): `task_code =
stampa_documenti_lotto`, `handler_code = stampa_documenti_lotto_default` → la chiave che C-2c
registra in `PipelineStepExecutor.handler_registry`. Policy (`fatturazione_pipeline_task_policy`
id 15/16, pipeline 4 e 6): `annullabile=t`, `resume_mode=RESUME_TASK`.

**Funzione accodamento** — firma reale per l'handler C-2c:
`vendite.fn_accoda_stampe_lotto(p_lotto_id bigint) RETURNS integer` (righe accodate). Accoda
**una riga PENDING per ogni fattura non esclusa** del lotto (`fatturazione_lotti_fatture` con
`esclusa IS NOT TRUE`), `sorgente_tipo_id = FATTURA` (risolto da `config.sorgenti`, no
hardcode), **`sorgente_uid = fattura.id::text`** (key_selector FATTURA), idempotente
(`ON CONFLICT … DO NOTHING` sull'indice parziale). L'handler è quindi davvero
`SELECT vendite.fn_accoda_stampe_lotto(<lotto_id>)`.

**Coda** `vendite.fatture_stampa_coda` — colonne per il worker (C-2b) e il monitoraggio (C-5):
`id`, `sorgente_tipo_id`, `sorgente_id` (= `fatture.id`, FK), `sorgente_uid`, `lotto_id` (FK,
NULL per ristampa on-demand), `template_documento_id` (override opz.), `stato`
(`PENDING/IN_CORSO/FATTO/ERRORE`), `tentativi`, `ultimo_errore` (jsonb), `documento_id`
(esito). Indice **`ix_fatture_stampa_coda_da_lavorare`** su `id WHERE stato IN (PENDING,
IN_CORSO)` → è la corsia del `SELECT … FOR UPDATE SKIP LOCKED` del worker. Unico parziale
`uq_fatture_stampa_coda_vivo (sorgente_tipo_id, sorgente_id) WHERE stato IN (PENDING,
IN_CORSO)` → anti-doppione vivo.

> ⚠️ **Scelta di modello del team DB (rispetto alla specifica): la coda NON ha
> `emittente_fiscale_id`.** È un **satellite di `vendite.fatture`** (`sorgente_id = fatture.id`)
> e lo **scope emittente si deriva via JOIN alla fattura**, non da una colonna denormalizzata.
> Conseguenze per il BE:
>
> * **C-2b worker**: gira in canale sistema (BYPASSRLS) → vede tutto, nessun impatto;
> * **C-5 monitoraggio (lettura operatore)**: il filtro scope emittente va fatto **JOIN
>   `fatture`** (o via la RLS già attiva su `vendite.fatture`), non su una colonna della coda.
>   Da tenere presente scrivendo la query di stato coda: l'operatore vede solo le stampe delle
>   proprie fatture per emittente, coerente con le altre liste vendite;
> * **C-2 cablaggio FATTURA**: `genera_documento` riceve `emittente_fiscale_id` — nel worker si
>   ricava dalla fattura (`sorgente_id`), non dalla riga di coda.

---

*Brief vivo: chiudere gli step aggiornando la colonna **Stato** (⬜ → ✅ con data) mano a
mano che avanzano; a fine cantiere il documento passa in `work-done/` con il consuntivo.*
