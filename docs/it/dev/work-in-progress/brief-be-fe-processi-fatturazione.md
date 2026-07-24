# Brief BE/FE — Cockpit processi fatturazione in Dashboard Competenza

> **Tipo**: brief operativo BE/FE (piano a step) · **Target**: `dev/backend-tid`
> · **Data**: 2026-07-19 (agg. **2026-07-22**) · **Owner**: Tid · **Stato**: 🟢 **FASI A+B+C
> COMPLETE (2026-07-22)** — A+B committate; C-0..C-2d ✅ **committati**
> (#1032). In **working tree (non committato)**: **coda lavori generica** (BE core
> `apps/core/services/coda_lavori/` + command) + **C-3** (giro on-demand) + **C-4**
> (single-lotto **e** perimetro) + **C-5** + **C-6/C-7** (verbi FE «Fattura adesso» /
> «Rendi definitive» sulla Dashboard Competenza, polling non bloccante) + **C-8** (stampa
> singola **e** ristampa massiva). **Worker `zeroerp-coda-lavori` DEPLOYATO** (systemd
> timer, gira ogni minuto); **`zeroerp-coda-stampa` deployabile** (GRANT ruolo batch
> applicati, smoke ok). Suite BE verde + lint/build/i18n FE verdi. **C-9 ✅ CHIUSO
> (2026-07-22)**: smoke parte alta esercitato sul percorso reale (worker systemd) —
> catena approva→giro→numera→G2→stampa verde, fattura R2/2 numerata e PDF su disco;
> ha scoperto+corretto il bug jsonb-as-str del worker (dettaglio nella riga C-9).
> **C-10 ✅** (G2 applicato dal team DB, verificato live). **B-5 ✅ CHIUSO 2026-07-22**
> (atterraggio contestuale dal pannello errori E dal breakdown FATTURATA: prerequisito DB
> [brief-db-lotto-id-vista-competenza-attivita.md](../work-done/brief-db-lotto-id-vista-competenza-attivita.md)
> applicato). **Fase D ✅ CHIUSA 2026-07-22** (D-1 guida operativa + D-2 guida tecnica;
> nel farla è emerso che i verbi implementati sono **3, non 4**: l'invio SDI non è
> esposto dalla dashboard, ora documentato come tale).
> P-3 template fattura ✅
> (is_default=true, ⚠️ `file_name_pattern` da correggere in-app).
> **FASE E APERTA (2026-07-23)**: la validazione in-app di Tid su Lente 1 + drawer
> A-4 ha scoperto 3 buchi di modello sulla macchina a stati commessa (annulla con
> fatture emesse, chiudi con righe da fatturare, riapri = vicolo cieco), il bug FE
> sblocco-prezzo-senza-motivo e 4 decisioni di design (auto-chiusura, capabilities
> enabled/motivo, variazione vietata su bloccato, drill-down per commessa) —
> dettagli e step in **FASE E** (prerequisito DB E-DB-1..4 da passare al team DB).
>
> **Fix di merito lungo il cantiere (2026-07-21)**: (a) **RLS worker** — `operator_identity_context`
> setta i **5 GUC** (`set_jwt_gucs`, validazione identità attiva): senza, la discovery di
> C-3/C-4 sotto RLS vedeva 0 righe (verificato live sul DB). (b) **Reaper anti poison-job**
> su entrambe le code (recupero stantio consuma un tentativo → ERRORE oltre soglia). (c)
> **Ownership polling scope-based** (`scope->>'scope_key'`): due operatori con la stessa
> whitelist che condividono un giro via dedup ne seguono entrambi l'avanzamento (prima il
> 2° → 404). (d) **Alias canale sistema** fonte unica in `system_context`. (e) Dedup
> `parse_competenza_mese` + `_accoda_job_fatturazione` + `useVerboFatturazione` (regola del 2).
>
> **Design-of-record**:
> [brief-design-gestione-processi-fatturazione.md](../work-done/brief-design-gestione-processi-fatturazione.md)
> (decisioni **D-1..D-7**, chiuse 2026-07-19).
> **Prerequisito DB**:
> [brief-db-processi-fatturazione-cockpit.md](../work-done/brief-db-processi-fatturazione-cockpit.md)
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
| B-5 | **FE — raggiungibilità contestuale** | Dal pannello **errori** e dal breakdown `FATTURATA` della dashboard si atterra sul lotto già filtrato | ✅ **CHIUSO 2026-07-22** — **pannello ERRORI**: la vista `vw_dash_competenza_errori` espone già `lotto_id` (nessun delta BE), la colonna «Lotto» del pannello errori è un link (`<Button link>`, classe `app-cell-link` in main.css) → `apriLotto(lotto_id)` monta il `LottoDrawer` diagnostico filtrato (fatture/task-run/segnalazioni/ristampa); gate sul dato (una `FATTURA_CRITICA` senza lotto non è cliccabile), `@changed`→reload aggregata+errori. **Breakdown FATTURATA**: prerequisito DB [brief-db-lotto-id-vista-competenza-attivita.md](../work-done/brief-db-lotto-id-vista-competenza-attivita.md) **applicato dal team DB** (colonna `lotto_id` in vista, verificato live: security_invoker preservato, no moltiplicazione, 6/6 popolati); a valle: `lotto_id` in `DashCompetenzaAttivitaRow`+`list_dash_competenza_attivita` (SELECT+mapping, verificato che le posizioni combaciano coi lotti reali 117/151 del C-9), e cella «Lotto» cliccabile nel drill-down attività che riusa lo STESSO `apriLotto`/`LottoDrawer` del pannello errori (una sola superficie, un solo gate-sul-dato). i18n riusa `col_lotto`/`apri_lotto`, suite BE verde, lint+build FE verdi |
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
| C-0 | **BE — generazione documenti eseguibile in contesto sistema (chiude P-1)** | `DocumentGenerationService.genera_documento` usa `user` per **una sola** cosa autorizzazione-critica — calcolare lo scope emittente (`resolve_emittente_scope` → `get_emittenti_ids`); tutto il resto (`generato_da_user_id`, `evento.user_id`, `auth_user_id` nel context) è **audit e tollera già `None`**, e i context builder **non filtrano i dati per utente**. **Decisione (2026-07-19, vedi §4)**: separare *chi autorizza* da *cosa genera* — `genera_documento` accetta lo **scope emittente già risolto** oltre allo `user`. Path web invariato (deriva scope da `user`, i 5 domini non cambiano); path sistema (batch/pipeline) passa `emittente_scope=None` — vede tutto, gira già su canale `system_process_context` BYPASSRLS con emittente **autoritativo** dal lotto — e `audit_user_id=None` (l'attore è già in `app.jwt_user`). **Non-breaking, nessun DB** | ✅ 2026-07-20 — kwarg `emittente_scope` con **sentinel** `_SCOPE_DA_UTENTE` (default = path web invariato); scope esplicito = caller-resolved; combinazione `scope=None + user=None` ammessa SOLO su canale BYPASSRLS (guard fail-loud `_guard_canale_sistema`); override `template_documento_id` in path sistema via repo (il reader pretende auth). 4 test nuovi (32 verdi) |
| C-1 | **BE — estrazione core driver** | Da `run_fatturazione_batch` (management command) estrarre `fatturazione_driver_service` (nome indicativo): discovery coppie `(emittente, tipo_doc)` emittibili → lotto per coppia → pipeline per coppia, **best-effort** (una coppia in errore non blocca le altre) + esito strutturato. Nuovo parametro **`fino_a_stato`** (Python puro, nessun DB): il giro da UI e il massivo da cron si fermano a **EMESSA** (D-1). Il command diventa un **chiamante sottile** — comportamento invariato, coperto dai test esistenti | ✅ 2026-07-20 — `fatturazione_driver_service.esegui_giro_fatturazione` (core unico I-1, esito strutturato per terna + callback progresso); fermata `fino_a_stato` implementata nel runner (`LottoPipelineParams.fino_a_stato_doc_fiscale_id`, motivo `FERMATO_A_STATO`) + facade `run_lotto_pipeline_until_done(fino_a_stato=)` con risoluzione codice→id; **default di corsia in `_MODALITA`**: immediata=fino in fondo, **differita=EMESSA (D-1 — cambio di comportamento del cron differita, voluto)**; command sottile con `--fino-a-stato` override diagnostico. 8 test service nuovi + test runner fermata; suite 1438 verdi |
| C-2 | **BE — cablare la famiglia documentale su FATTURA** | La sorgente `FATTURA` esiste (`config.sorgenti` id 10, target `vendite.fatture`, `key_selector=id`) ma **non è istanziata** sulla factory `build_documenti_sorgente_views` (oggi: preventivi, offerte, contratti, ordini, DDT). Delta ~10 righe → `fatture_documenti_views.py` (genera / anteprima / lista / file / download) + context builder FATTURA + template fattura. **Sblocca la stampa singola sincrona** (I-3) e la ristampa on-demand | ✅ 2026-07-20 — factory `build_documenti_sorgente_views` istanziata SENZA emetti (`fatture_documenti_views.py`, closure `_get_entity` su `VenditeRepository.get_fattura_for_documento_generation` che risolve **PK emittente da SR** via JOIN `emittenti_fiscali`, 1:1 `uq_emittenti_fiscali_ruolo`); `FatturaDocumentContextBuilder` (CODE=`FATTURA`, registrato in `VenditeConfig.ready()`) clone strutturale del builder ordine, **riepilogo IVA dalla tabella reale** `fatture_riepiloghi_iva`; read testata/righe/riepilogo in `VenditeRepository`; rotte `documenti/` (genera/anteprima/lista/file/download, **niente emetti/**) in `urls_fatture.py`; FE whitelist (`documentiContextBuilders.js` + `SORGENTE_CODES.FATTURA`) + i18n it/en. Test: 6 builder (mock) + 4 API (mock, incl. **404 su emetti/**). **Suite vendite+documenti 1450 verdi, lint+build FE puliti.** ⚠️ **Aperto**: P-3 template fattura (configurazione in-app, non codice) → blocca lo smoke E2E; validazione in-app (DB dev vuoto) = Tid |
| C-2b | **BE — worker drainer della coda stampa** (sostituisce «processo massivo generico») | Management command su cron/systemd (canale `system_process_context`, come `run_fatturazione_batch`), avvolto in `registered_job` (`maintenance.job_run_log`). Drena `vendite.fatture_stampa_coda`: seleziona i `PENDING` con **`FOR UPDATE SKIP LOCKED`** (più worker non si pestano), per riga → **backstop numerazione** (C-2d) → `DocumentGenerationService.genera_documento` in contesto sistema (C-0) → aggiorna `stato`/`tentativi`/`ultimo_errore`/`documento_id`. **Resiliente per-riga** (un render fallito non ferma gli altri, incrementa `tentativi`, `stato=ERRORE` oltre soglia) e **idempotente** (l'indice unico parziale della coda impedisce doppioni vivi). Non conosce «lotto» o «fatturazione»: sa solo drenare la coda | ✅ 2026-07-20 — command `draina_coda_stampa` (chiamante sottile: `system_process_context` alias `system_fatturazione` + actor **`WORKER_STAMPA_DOCUMENTI`** + `registered_job` lock anti-overlap) su core `stampa_coda_drainer_service.draina_coda_stampa`. Repo in `VenditePipelineRepository` (owner coda): `claim_stampe_pending` (**`FOR UPDATE SKIP LOCKED`** + flip IN_CORSO in una `WITH … UPDATE … RETURNING`, indice `ix_..._da_lavorare`), `marca_stampa_fatto`/`marca_stampa_errore` (tentativi+1 → **ERRORE oltre soglia, altrimenti PENDING**), `reset_stale_stampe_in_corso` (reaper worker morto, soglia larga), `count_coda_stampa_per_stato` (per C-5). Batch unico per giro (niente re-claim delle fallite nello stesso run). Resilienza per-riga (best-effort). 9 test service + 4 command |
| C-2c | **BE — handler task `stampa_documenti_lotto_default`** | Registrato in `PipelineStepExecutor.handler_registry` (il seed DB lo dichiara). **È un adattatore, un one-liner**: `SELECT vendite.fn_accoda_stampe_lotto(<lotto_id>)` — **accoda e ritorna** (I-4b: nessun render dentro la transazione dello step). Non passa id a nessuno, non renderizza. `annullabile=t`, `resume_mode=RESUME_TASK` (seed DB). Ri-eseguibile: ri-accodare è idempotente | ✅ 2026-07-20 — handler nel registry + wrapper repo `accoda_stampe_lotto` (`fn_accoda_stampe_lotto`, ritorna n accodate loggato); 2 test executor (run + dry-run skip) |
| C-2d | **BE — backstop numerazione nel worker** (B-2) | Prima di generare il PDF, il worker verifica che la fattura sia numerata; se non lo è, la numera via `fn_numera_fattura_opz_emessa(p_fattura_id)` (per-fattura, **idempotente**: già numerata → no-op). **Vive nel worker / context-builder FATTURA, NON dentro `DocumentGenerationService`** (che resta generico e stupido — I-4). Rende **impossibile un PDF non numerato** → D-1 al livello più forte | ✅ 2026-07-20 — `VenditePipelineRepository.numera_fattura_backstop` (delega a `fn_numera_fattura_opz_emessa`, già **idempotente**: fattura numerata → no-op) chiamata dal drainer PRIMA di `genera_documento`. Vive nel worker, NON in `DocumentGenerationService` (I-4). Coperto dai test happy-path/fattura-sparita del drainer |
| C-3 | **BE — endpoint giro fatturazione** | `POST /vendite/fatturazione/run/` · body `{competenza_mese, fino_a_stato}` · corsia **differita**, perimetro `competenza ≤ M` (cumulativo come il batch), scope emittente dell'operatore via RLS. `post_permission = "genera_fatture_lotti"`, `Idempotency-Key`. **I-3**: multi-coppia → esecuzione in background con run registrato (`registered_job`), risposta = handle del run; la coppia singola resta sincrona | ✅ **BE FATTO 2026-07-21** — via **coda lavori generica** DB-native (no broker; design+DB brief coda). DB applicato (`20260720-07..10`, pgTAP `plan(57)`). **BE core** `apps/core/services/coda_lavori/` (`QueueDrainEngine`+`QueueBackend`+`CodaLavoriRepository`+registry+`operator_identity_context`+drainer) + command `apps/core/management/commands/draina_coda_lavori.py` (11 test). **Consumatore C-3**: endpoint `POST /vendite/fatturazione/run/` (`ApiFatturazioneRun`, permesso `genera_fatture_lotti`, Idempotency-Key HTTP + chiave **business** competenza-mese+scope) accoda `FATTURAZIONE_GIRO` run_as=OPERATORE con scope catturato → risponde `{job_id, PENDING}`; handler `fatturazione_giro_handler` (in `VenditeConfig.ready()`) esegue il core C-1 `esegui_giro_fatturazione` (differita→EMESSA) sotto RLS operatore; polling `GET run/<job_id>/` (`ApiFatturazioneRunStato`, ownership **scope-based** `scope->>'scope_key'`→404). `job_run_id` timbrato sui job (tracciabilità). 10 test. **Fix 2026-07-21**: `operator_identity_context` setta i **5 GUC** (`set_jwt_gucs`, non solo `app.jwt_user`) — verificato live che la RLS di `fatturazione_lotti`/commesse risolve; reaper anti poison-job; ownership polling scope-based (2 operatori stessa whitelist condividono il giro). **Worker `zeroerp-coda-lavori` DEPLOYATO** (systemd timer, ogni minuto, `job_run_log ok=True`). ✅ **CHIUSO** (resta validazione in-app). |
| C-4 | **BE — endpoint numerazione** | `POST /vendite/fatturazione/numera/` (o `lotti/<id>/numera/` per il singolo) → step DEFINITIVA sui lotti EMESSA del perimetro. `post_permission = "numera_fatture_lotti"`. **I-2**: esegue lo step, che contiene `numera_fatture` **e** `stampa_documenti_lotto` (che accoda) — l'endpoint non chiama la stampa per conto suo; la coda viene poi drenata dal worker | ✅ **CHIUSO (single + perimetro) 2026-07-20/21** — **single-lotto**: `POST /vendite/fatturazione/lotti/<id>/numera/` (`ApiFatturazioneNumeraLotto`) → `pipeline_service.numera_lotto` (guard scope 404 + guard **EMESSA** I-7 → `run_lotto_pipeline_until_done(DEFINITIVA)`); FE nel `LottoDrawer` «Rendi definitive» sostituisce «Avanza» su EMESSA. **PERIMETRO (2026-07-21)**: prerequisito DB **seed `FATTURAZIONE_NUMERA`** in `dbops.coda_lavori_tipi` (brief archiviato, verificato live); endpoint `POST /vendite/fatturazione/numera/` (`ApiFatturazioneNumera`, `numera_fatture_lotti`) accoda via `_accoda_job_fatturazione` (shared con C-3); handler `fatturazione_numera_handler` (`VenditeConfig.ready()`) scopre i lotti EMESSA del mese (`VenditeRepository.list_lotti_numerabili`, scope via RLS) + `numera_lotto` per-lotto best-effort. 11 test. |
| C-5 | **BE — esiti dei giri + stato coda stampa** | `GET /vendite/fatturazione/esiti/`: ultimi run per corsia da `maintenance.job_run_log`. **+ stato coda stampa** da `vendite.fatture_stampa_coda` (conteggi PENDING/IN_CORSO/FATTO/ERRORE, per lotto/emittente; RLS scope emittente già sulla tabella) — l'operatore vede se le stampe sono in coda, fatte o in errore. **I-5**: nessuna tabella nuova (la coda è già decisa dal DB) | ✅ 2026-07-20 — `GET /vendite/fatturazione/esiti/` (`ApiFatturazioneEsiti`, sola lettura) → service `pipeline_service.esiti_fatturazione`: (a) riassunto per corsia da `maintenance.job_run_log` via `MaintenanceRepository.list_job_summary` filtrato ai jobname `run_fatturazione_batch*`/`draina_coda_stampa`/`draina_coda_lavori`; (b) conteggi coda stampa per stato **scoped all'operatore** (`count_coda_stampa_per_stato(auth_user_id)` → JOIN fatture, brief §5). 1 test service (filtro jobname + coda scoped). **FE**: `FatturazioneEsitiPanel.vue` (badge stato coda per stato + ultimi giri per corsia con last_ok/last_run) montato in `LottiListView`, self-fetch `onActivated`. i18n it/en |
| C-6 | **FE — verbo «Fattura» del mese** | «Aggiorna commesse» (push, endpoint esistente — **D-5**) · «Fattura competenza M» (C-3) · «Rendi definitive» (C-4, azione **separata** e visivamente distinta — I-7) · pannello/chip «esito ultimo giro» + **badge stampe in coda/errore** (C-5) | ✅ **FATTO 2026-07-21** — «Fattura adesso» sulla card **DA_EMETTERE** della `DashboardCompetenzaView` (gate `genera_fatture_lotti`+readonly): conferma → `runFatturazione` (`POST run/`) → **polling non bloccante** (nuovo BB `core/composables/useJobPolling.js`: setTimeout ricorsivo, cleanup onUnmounted/onDeactivated, cap anti-loop se worker giù → «in coda») → toast esito (lane/falliti) + refresh. i18n it/en. Chip esito ultimo giro = già in `FatturazioneEsitiPanel` (lista lotti); «Aggiorna commesse» push = fuori questo giro (D-5) |
| C-7 | **FE — verbo «Rendi definitive» del mese** | «Fattura adesso» su `DA_EMETTERE`; «Rendi definitive» sulla card `EMESSA_NON_FATTURATA`; feedback di avanzamento per i giri in background + refresh a fine run | ✅ **FATTO 2026-07-21** — «Rendi definitive» sulla card **EMESSA_NON_FATTURATA** (gate `numera_fatture_lotti`+readonly, severity warn + `pi pi-lock` per distinguerlo dal pre-fiscale — I-7): `runNumerazione` (`POST numera/`) + stesso polling. Flusso conferma→accoda→polling→esito **estratto** in helper locale `useVerboFatturazione` condiviso coi due verbi (regola del 2). i18n it/en |
| C-8 | **FE — stampa e ristampa** | Da una fattura: «Stampa/Anteprima» **sincrona** (C-2, 1 documento → I-3; componenti documentali già esistenti nei 5 domini — si riusa il pattern); da lotto/selezione: «Ristampa» **massiva → accoda in coda** (C-2b la drena) con stato visibile (C-5). Il singolo passa da `genera_documento`, il massivo dalla coda: due percorsi per cardinalità, un solo render | ✅ **CHIUSO (singola + massiva) 2026-07-20/21** — **stampa SINGOLA**: client `fattureDocumenti` + azioni riga fattura nel `LottoDrawer` («Anteprima PDF» render sincrono + «Documenti» archivio); disponibili anche in sola lettura (I-4). P-3 template 77 `is_default=true` ✅. **Ristampa MASSIVA (2026-07-21)**: service `pipeline_service.ristampa_lotto` (guard scope 404 + **gate DEFINITIVA** → `accoda_stampe_lotto`; il gate impedisce che il backstop del worker numeri via ristampa — I-7), endpoint `POST /vendite/fatturazione/lotti/<id>/ristampa/` (`ApiFatturazioneRistampaLotto`, area vendite, **no post_permission** come la stampa singola), `E_LOTTO_NON_RISTAMPABILE`(409). FE: bottone «Ristampa documenti» nel `LottoDrawer` su lotto DEFINITIVA → toast «N accodati». 6 test (3 service + 3 API). |
| C-9 | **Test + doc + smoke** | Test service driver (fermata a stato, best-effort, perimetro) + worker drainer (SKIP LOCKED, resilienza per-riga, tentativi/ERRORE, idempotenza, **backstop numera-se-manca**) + accodatore; **smoke E2E** «approva → fattura → rendi definitive → drena coda» su dati veri, che verifica **PDF sempre numerato** e **nessun lock fiscale tenuto durante il render** (gli smoke scoprono i GRANT/scope che i test mock non vedono); doc `api_fatturazione.md` + `api_documenti_*` + `api.md` | ✅ **2026-07-22** — **smoke render E2E FATTO** (lotto DEFINITIVA reale → `ristampa_lotto` → `draina_coda_stampa`): ⚠️ **ha scoperto un bug bloccante** — la stampa FATTURA **non renderizzava affatto** (builder `FatturaDocumentContextBuilder` ↔ template id 77: motore Jinja `StrictUndefined`, il builder — clone dell'ordine — non forniva `emittente.{denominazione,piva,cf,sede}`, `scadenze`, `cliente.indirizzo`, `fattura.{totali.iva/sconto, agente_denominazione, origine, pagamento, utility}`; i 6 test builder erano mock → mai renderizzato). **Fix**: repo `get_fattura_testata` +JOIN emittente + `list_fattura_scadenze`; builder arricchito. **Verificato: PDF reale prodotto** (GENERATO), fattura numero INVARIATO (backstop no-op, no atto fiscale). **Campi arricchiti**: `cliente.indirizzo` (tipo FATT), `emittente.sede` (SEDELEG), `utility` (via BA→config.utilities), `pagamento` (modalita/termine via config); restano vuoti per modello/dati `origine`/`agente`/`sconto` (documentati: sorgente NULL/non-di-testata). **Doc `api_fatturazione.md` FATTA** (+ link in api.md). **1890 test verdi**. ⚠️ Nota operativa: durante lo smoke ho erroneamente cancellato le righe-indice `documenti_generati_file` (135 doc di test) contando su un conteggio RLS-mascherato — PDF nello storage intatti, dato di test, non recuperato (ok Tid). **SMOKE PARTE ALTA FATTO (2026-07-22, autorizzato Tid)** — approva (Tid in-app) → giro → numera → stampa su competenza 2026-06: ⚠️ **ha scoperto il 2° bug bloccante** — con Django+psycopg 3 i `jsonb` letti da cursor RAW arrivano come **str** (il backend Django non li decodifica fuori dall'ORM): il worker della coda generica riceveva payload/scope stringa → `AttributeError: 'str' object has no attribute 'get'` al primo job vero (il percorso non era mai stato esercitato con un job reale — i drain precedenti erano a vuoto, conferma [[feedback_audit_db_preventivo_smoke]]). **Fix**: BB `jsonb_out` (null-preserving, in `core/db/_helpers.py` accanto a `coerce_jsonb_dict`) applicato a claim/get_stato/elenca/get_dettaglio della coda + `elenca_coda_stampa` (il payload «quotato» nel drawer UI era lo stesso bug, versione cosmetica); 4 test regressione (`test_coda_lavori_repository.py`). **Catena poi VERDE end-to-end sul percorso reale** (worker systemd): giro→lotto 151/fattura 244→numera **R2/2 DEFINITIVA, zero duplicati**→**G2 ha accodato la stampa da solo in pipeline**→worker stampa→**PDF valido su disco** (doc 143, 18KB). Migliorie di merito emerse: (a) contatore `numerati` dell'handler ora conta la **transizione DEFINITIVA verificata** (prima contava «nessuna eccezione»: i lotti legacy 106/107, EMESSA pre-G1 con fatture DRAFT e pipeline senza step eseguibili, risultavano "numerati" no-op) + nuovo esito `saltati{,_dett}` con motivo_stop, toast FE allineato; (b) test HTTP POST resi deterministici con `override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)` (con `env.sh` sourcato il flag=1 faceva colpire il DB ai SimpleTestCase; `TestAzioniHttp` era perfino `unittest.TestCase` puro e ha SCRITTO 2 chiavi test su `dbops.idempotency_keys` dev — da ripulire, serve ok). **Residui segnalati (non della catena)**: template 77 `file_name_pattern='fattura-.pdf'` senza placeholder (fix in-app); 13 lotti giugno DRAFT-ERRORE da bonificare/annullare. **Ripasso smoke 2026-07-22**: i lotti legacy 106/107 (EMESSA con fatture rimaste DRAFT) facevano fallire la numerazione con un `motivo_stop: ERRORE` **muto**; diagnosi → il DB rifiuta — correttamente — il salto `DRAFT→DEFINITIVA` sulla fattura (non esiste in `stati_doc_fiscale_transizioni`, il percorso è `DRAFT→EMESSA→DEFINITIVA`); la stampa NON c'entrava (G2 accodava, era il rollback atomico dello step a svuotare la coda). **Fix**: (a) il runner conserva `errore {code,message,detail}` nell'esito e il handler numera lo espone in `saltati_dett` (errore non più muto); (b) smoke reso onesto — i lotti con dato storico incoerente sono `WARN` con causa in chiaro e la sezione stampa va in `SKIP` esplicito se non è stato numerato nulla (prima falliva anche con lista vuota, difetto dell'asserzione); (c) **bonifica eseguita** (ok Tid, dati di test) via `fn_sync_lotto_fatture_stato(<lotto>, EMESSA)` → 0 incoerenze su 27 lotti. Buco di modello segnalato al team DB: [brief-db-guard-coerenza-stato-lotto-fatture.md](../work-done/brief-db-guard-coerenza-stato-lotto-fatture.md) → **guard APPLICATO** (3 constraint trigger DEFERRED + vista + errore 556) e, grazie ad esso, **CAUSA RADICE TROVATA E CHIUSA (2026-07-22)**: in `_execute_pipeline_step` l'avanzamento dello stato lotto era **incondizionato** mentre la sync fatture stava sotto `if not dry_run`, entrambi nella `atomic()` di Fase 2 che **committa** → **ogni dry-run avanzava permanentemente il lotto lasciando indietro le fatture** (genesi di 106/107). Fix: (1) `transaction.set_rollback(True)` sull'intera Fase 2 in dry-run — rollback della fase invece di condizionare le singole scritture, e come ULTIMA istruzione del blocco (Django vieta query dopo il mark); (2) sync fatture resa **incondizionata**: la coppia stato-lotto/stato-fatture è ora indivisibile per costruzione, e il dry-run diventa fedele (esercita le stesse scritture → predice gli errori del run vero). Verificato sul DB reale: dry-run su lotto DRAFT → esegue gli step e lo lascia **identico**, 0 incoerenze. Test: coppia mirror run-vero/dry-run che differisce solo per il flag; harness `_fake_tx` (28 siti) che stuba `atomic` **e** `set_rollback` insieme. Suite BE verde, lint+build FE verdi |
| C-10 | **DB — attivazione G2** (coordinata) | A handler + worker deployati, dare l'ok al team DB per l'append G2 ai `processi` DEFINITIVA (brief DB §6). **Non prima** (vincolo di sequenza in testata). Verifica post-attivazione: un giro giornaliero notturno accoda e il worker drena, PDF numerati | ✅ **2026-07-21** — G2 applicato dal team DB (commit `12307d0bc`, PR #1040: CSV `fatturazione_pipeline` + pgTAP `20260721-16`). **Verificato live sul DB**: pipeline 4 (massiva) e 6 (giornaliera) DEFINITIVA = `numera_fatture` + `stampa_documenti_lotto` (impl `default`); handler `stampa_documenti_lotto_default` nel registry executor; timer `zeroerp-coda-lavori` (1 min) + `zeroerp-coda-stampa` (2 min) ATTIVI. Sequenza G1→BE→G2 rispettata. Resta l'esercizio end-to-end del giro notturno / numerazione in-app (validazione fiscale Tid) |

**Gate di uscita C**: un mese di competenza si chiude interamente dall'app, con la
numerazione come atto separato e consapevole; le stampe entrano in coda alla DEFINITIVA, il
worker le drena, ogni PDF è numerato, e l'operatore vede lo stato delle stampe. G2 attivato
in coordinamento col DB.

> **Stato gate (2026-07-21)**: 🟢 **codice completo e verificato** — tutti i verbi FE
> azionabili dalla Dashboard Competenza; worker `coda-lavori`+`coda-stampa` deployati e
> girano; **render PDF end-to-end verificato** (era rotto, C-9 l'ha scoperto e corretto).
> Restano solo: **C-10 attivazione G2** (team DB, ora sicura: handler+worker deployati) e
> la **validazione fiscale in-app di Tid** (approva→fattura→numera su dati reali = atto
> fiscale). Consolidamento: nulla committato, separare le modifiche FE non di questo
> cantiere con `git add` espliciti.

---

## FASE D — Guida utente

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| D-1 | **Guida** | Sezione «Gestire la fatturazione» nella [guida cruscotti](../../guide/cruscotti-fatturazione.md): i **quattro verbi** in linguaggio non tecnico, cosa fa il cron e cosa fa l'operatore, perché la numerazione è separata. Si salda con la Fase 4 del piano due-lenti | ✅ **2026-07-22** — nuova §7 «Gestire la fatturazione (agire dalla Lente 1)» in [cruscotti-fatturazione.md](../../guide/cruscotti-fatturazione.md), registro operativo: i verbi con card/permesso, **perché la numerazione è separata** (EMESSA reversibile vs DEFINITIVA irreversibile → «fatturare a lavoro finito, numerare a controlli finiti»), cosa fa il notturno vs l'operatore, lavoro non bloccante + badge/Code di lavoro, atterraggio sul lotto dal pannello errori. ⚠️ **Corretto il perimetro del brief**: i verbi implementati sono **3, non 4** — «Invia»/SDI NON esiste nella dashboard (verificato: 0 occorrenze), documentato esplicitamente come non disponibile invece di descriverlo |
| D-2 | **Guida fatturazione** | Aggiornare [fatturazione.md](../../guide/fatturazione.md) §«Dashboard operative» (oggi elenca 4 viste ipotetiche) con l'assetto reale | ✅ **2026-07-22** — §«Dashboard operative» riscritta con l'assetto REALE: tabella delle 5 superfici con rotte vere (verificate nel router), i 3 verbi con endpoint+permesso (verificati in `urls_v1.py`/`views.py`), gate fiscale I-7 e corollario sulla catena stati fattura + guard DEFERRED, modello asincrono (I-3) con i 3 processi e le loro cadenze, monitoraggio (badge, code, pannello errori). Rimosso l'elenco delle 4 viste ipotetiche |

---

## FASE E — Esiti validazione in-app 2026-07-23 (dashboard competenza + drawer commessa)

> Prima validazione in-app di Tid su Lente 1 + drawer A-4: emersi **3 buchi di
> modello sulla macchina a stati commessa**, 1 bug FE bloccante (sblocco prezzo),
> e 3 decisioni di design. Analisi verificata sul codice/DB vivo (doc auto-gen):
> matrice [transizioni_stati_commessa](/it/dbzero/vendite/tabelle/transizioni_stati_commessa.md),
> guard [trgfn_commesse_guard_transizione](/it/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione.md)
> (unico guard di dominio: ingresso in PRONTA_FATTURAZIONE),
> [fn_available_actions_commessa](/it/dbzero/script/funzioni/fn_available_actions_commessa.md)
> (nessun `enabled`/`reasons`),
> [fn_get_commessa_stato](/it/dbzero/vendite/funzioni/fn_get_commessa_stato.md)
> (non espone `codice` né cliente).
>
> **Stato (agg. 2026-07-24)**:
> - **Fetta indipendente dal DB** (committata `1e19b30b0`): **E-FE-1** ✅ (bug
>   sblocco prezzo: dialog motivo), **E-FE-3** ✅ (icona `pi-key` vs lucchetti),
>   **E-BE-1** ✅ (guard variazione su bloccato, DEC-3), **E-FE-2** 🟡 (gate
>   `canEditRighe` + `variazione` nascosta su bloccato).
> - **DB CONSEGNATO** dal team (`dev/db-tid`, migrato+pgTAP, brief
>   [brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md)):
>   **E-DB-1/3/4 fatti**, **E-DB-2 (auto-chiusura) SCARTATO** con analisi (D4, vedi
>   DEC-1 sotto). ⚠️ **Diverge dalla mia proposta** su 2 punti (D3, D4).
> - **Recepimento BE/FE (2026-07-24, questa sessione, non committato)**: filtro
>   `enabled` in `cambia_stato_commessa` (§6.1), codici 558/559 in `error_policies`,
>   `commessa_codice`/`cliente_display` in `CommessaStatoResult`+repo, **E-FE-4** ✅
>   (header drawer con codice+cliente), 2 chiavi i18n `azione_reason`. **469 test BE
>   + build/eslint FE verdi.**
> - **Ancora aperto**: **E-BE-2** (drill-down per commessa + esporre `fattura_riga_id`)
>   → sblocca coda **E-FE-2** e **E-FE-5**. + segnalazione §8 DB (permesso mancante
>   su chiudi/annulla) da decidere lato BE.

### Decisioni prese (Tid, 2026-07-23)

| # | Tema | Decisione |
| --- | --- | --- |
| DEC-1 | Commessa interamente fatturata | ~~**Chiusura automatica**~~ → **SUPERATA da D4 del brief DB (2026-07-24, ok Tid)**: l'auto-chiusura è **scartata**. Motivo: l'evento scatenante (`attivita_fatturabili.fattura_riga_id`) è **reversibile** (il reset lotto DRAFT lo azzera) ma CHIUSA è **terminale irreversibile** → una commessa si chiuderebbe da sola e poi, al reset lotto, resterebbe murata con righe di nuovo fatturabili. Al suo posto: il DB **espone la condizione** «non resta nulla da fatturare» via capabilities (`chiudi` diventa `enabled`), la UI la evidenzia, ma **a chiudere è una persona**. Il guard di uscita (E-DB-1b) impedisce comunque la chiusura con righe pendenti |
| DEC-2 | Pulsanti di stato sempre attivi | Pattern **guard-righe dei DDT**: `fn_available_actions_commessa` emette `enabled:false` + `reason_key` quando le precondizioni non passano; FE già pronto (`mapAvailableActionsToDrawerActions` → pulsante **disabilitato con tooltip del motivo, mai nascosto**) |
| DEC-3 | Variazione eccezionale su prezzo bloccato | **Vietata finché non si sblocca** (oggi ammessa come ri-override sia FE che BE; solo il riallineo è vietato su bloccato). Allineare BE (guard) + FE (kebab) |
| DEC-4 | Drill-down «da emettere» con commessa ripetuta | **Lista per commessa** (una riga totale: n attività, Σ valore, range date); il dettaglio a grana attività resta nel drawer. Deroga consapevole alla «grana attività» del due-lenti §2 per la **lista** — le card/contatori restano a grana attività |

### E-DB — Prerequisito DB (gate per E-BE/E-FE, [[feedback_be_fe_attende_prerequisiti_db]])

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| E-DB-1 | **Guard di uscita da PRONTA_FATTURAZIONE** (bug logici modello) | In `trgfn_commesse_guard_transizione`: (a) →ANNULLATA vietata con righe EMESSE; (b) →CHIUSA vietata con righe APPROVATE+NON_EMESSE; (c) il vicolo cieco «riapri» | ✅ **DB 2026-07-24** — (a)/(b) come **Regola 3** del guard, delegata a funzioni pure `script.fn_check_commessa_annullabile`/`_chiudibile` (sorgente unica condivisa con le capabilities); codici errore **558/559**. **DIVERGE su (c)**: il team NON vieta «riapri» — la causa è un **arco mancante nel dato**, quindi ha **aggiunto la transizione `IN_ESECUZIONE→CHIUSA`** in matrice (`transizioni_stati_commessa` id 12, meta = quello di `4→5`). Motivo (D3): «riapri» serve a togliere la commessa dal giro (IN_ESECUZIONE non è emittibile), vietarla toglie una leva; e lo stallo si raggiunge anche senza «riapri» (commessa nata in IN_ESEC con righe BOZZA). Con (b) attivo l'arco è sicuro |
| E-DB-2 | ~~**Auto-chiusura** (DEC-1)~~ | — | ❌ **SCARTATO (D4, ok Tid)** — vedi DEC-1: evento scatenante reversibile, stato prodotto no. Sostituito dall'esposizione della condizione via capabilities |
| E-DB-3 | **Capabilities con motivo** (DEC-2) | `fn_available_actions_commessa` → `enabled` + `reasons` per azione | ✅ **DB 2026-07-24** — `enabled`+`reasons` su `chiudi`/`annulla` dalle stesse `fn_check_commessa_*` del guard; `can_change_state` ricalcolato sulle sole azioni abilitate. Shape identica a `fn_available_actions_ddt` (contratto §5 del brief DB) |
| E-DB-4 | **Testata identificabile** | `fn_get_commessa_stato` + codice commessa e cliente | ✅ **DB 2026-07-24** — aggiunte in coda alla `RETURNS TABLE`: **`commessa_codice`** (`c.codice`; nome esplicito per non confonderlo con `stato_commessa`=codice dello STATO) e **`cliente_display`** (`ragione_sociale_completa` via BA→SR→soggetto, LEFT JOIN) |

### E-BE

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| E-BE-1 | **Guard variazione su bloccato** (DEC-3) | `fn_variazione_prezzo_eccezionale`: require `prezzo_bloccato=FALSE` (come già il riallineo N5) — percorso unico: sblocca (con motivo) → poi varia | ✅ **2026-07-23** — guard `require(not att["prezzo_bloccato"])` → `E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA` (già mappato in `error_policies`), prima del parse prezzo/motivo (nessuna scrittura); test `test_variazione_eccezionale_su_prezzo_bloccato_rifiutata`. Suite service 57 + API 29 verdi. Simmetrico a E-FE-2 (variazione nascosta su bloccato) |
| E-BE-2 | **Drill-down per commessa** (DEC-4) | Aggregazione per commessa sulla stessa vista (GROUP BY `commessa_id`); sort/paginazione sulla grana commessa | ✅ **2026-07-24** — nuovo endpoint `GET dashboard-competenza/commesse/` (`ApiDashboardCompetenzaCommesse` → `fn_dash_competenza_commesse` → `list_dash_competenza_commesse`): GROUP BY su `vw_dash_competenza_attivita` (n_attivita, n_in_ritardo, SUM valore/fatturato, MIN/MAX data); `count` = n commesse; whitelist ordinamento **aggregata** (`valore_tot` default); scope emittente DB-side invariato. Tipo `DashCompetenzaCommessaRow`, doc `api_dashboard_competenza.md`. **6 test service + 4 API**, suite vendite 1304 verde. NB: la lista NON è un oggetto DB nuovo — è una query GROUP BY nel repo, stesso layer delle query esistenti |
| E-BE-3 | **Recepimento contratto capabilities + testata** (impatti §6.1 brief DB) | Filtro `enabled` nella difesa applicativa di `cambia_stato_commessa`; codici 558/559 in `error_policies`; nuovi campi testata nel repo/type | ✅ **2026-07-24** — (1) `stati_ammessi = {… if a.get("enabled") is not False}` (senza, un'azione terminale vietata passava il gate e il DB rispondeva 558/559); (2) `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE`/`E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI` → 409 `show_error_banner`; (3) `commessa_codice`/`cliente_display` in `CommessaStatoResult` + SELECT/mapping `get_commessa_stato` (row[18]/[19]), propagati all'API via spread. Test: `test_cambia_stato_commessa_azione_disabilitata_rifiutata`, mock repo+service aggiornati. **469 test BE verdi** |

### E-FE

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| E-FE-1 | **BUG: sblocco prezzo fallisce sempre** | Il BE esige `motivo` obbligatorio (doc `api_commesse_pricing.md`, test API lo passano) ma `sbloccaPrezzoAttivita` invia `{}` e il drawer fa solo confirm → 400 «Motivo obbligatorio» garantito. Serve dialog motivo (come la variazione N7) | ✅ **2026-07-23** — `sbloccaPrezzoAttivita(commessaId, attId, {motivo})` invia il motivo; `sblocca()` apre un `AppDialog` (testo `sblocca_conferma` + `Textarea` motivo, `save-disabled` finché vuoto) con `salvaSblocco()`; i18n `sblocca_motivo`/`sblocca_salva` (it+en). Build+eslint verdi |
| E-FE-2 | **Congruità kebab prezzi** | Nascondere/disabilitare le azioni prezzo su righe con `fattura_riga_id` valorizzato e con `capabilities.can_edit_righe=false` (oggi su riga fatturata o commessa CHIUSA compaiono e falliscono); `variazione` invisibile su `prezzo_bloccato` (specchio E-BE-1) | 🟡 **PARZIALE 2026-07-23** — fatte le parti indipendenti: gate `canEditRighe` (`capabilities.can_edit_righe===true`, fail-closed) su tutto il kebab prezzi → su CHIUSA/ANNULLATA non compare; `variazione` `visible: !prezzo_bloccato` (specchio E-FE↔E-BE-1/DEC-3). **Resta**: il gate su riga fatturata — `fn_list_commessa_attivita` (funzione DB del drawer) **non espone** `fattura_riga_id` e `stato_emissione=EMESSA` **non** implica fatturata (il BE ammette il cambio prezzo su emesse-non-ancora-fatturate) → **brief DB pronto (2026-07-24)**: [brief-db-fattura-riga-id-lista-commessa-attivita.md](brief-db-fattura-riga-id-lista-commessa-attivita.md) (espone flag `fatturata` = EXISTS AF con `fattura_riga_id`; poi 1 riga BE in `_ATTIVITA_COLS` + gate FE `!row.fatturata`). **In attesa team DB** |
| E-FE-3 | **Semantica lucchetti** | La colonna prezzo usa il lucchetto chiuso come **stato**; l'azione «Sblocca» usa `pi-lock-open` come icona inline → si legge come stato «aperto». Distinguere icona-azione da icona-stato | ✅ **2026-07-23** — icona azione «Sblocca» = `pi-key` (chiave), distinta dai lucchetti-stato `pi-lock` della colonna prezzo |
| E-FE-4 | **Header drawer** | `DrawerEntityHeader`: etichetta + `codice` commessa + cliente (post E-DB-4) al posto del solo `#<commessa_id>` | ✅ **2026-07-24** — `DrawerEntityHeader` mostra `stato.commessa_codice \|\| #<id>` + `stato.cliente_display` (muted); il titolo drawer «Gestione commessa» c'era già. + 2 chiavi i18n `vendite.commesse.azione_reason.{righe_emesse,righe_da_emettere}` (it+en) per i tooltip dei pulsanti disabilitati (mapper FE già pronto, «zero modifiche» §6.2 del brief DB). Build+eslint+i18n verdi |
| E-FE-5 | **Lista per commessa** (post E-BE-2) | Drill-down a righe-commessa; kebab: «Apri commessa» + «Approva» (via `approva-competenza` scoped). Card/contatori invariati (grana attività) | ✅ **2026-07-24** — store `dashboardCompetenza` e `DashboardCompetenzaView` passati al drill-down per commessa (`listDashboardCompetenzaCommesse`; refs `commesse*`, default sort `valore_tot`). Colonne: commessa, cliente, n attività (tag), valore, fatturato, periodo (min–max), ritardi; kebab «Approva» (DA_APPROVARE → `approvaCompetenza(mese,{commessaIds:[id]})`, conferma con n+codice) + «Apri commessa» (drawer col dettaglio attività). Card/donut/totali/errori invariati; i18n it+en. Build+eslint verdi. **Risolve il reclamo utente** (commessa non più ripetuta). NB: persi dal drill-down i link fattura/lotto per-attività (B-5 resta nel pannello errori); il dettaglio è nel drawer |

### E-BE-4 — DECISIONE APERTA: permesso su chiudi/annulla commessa (§8 brief DB)

Il team DB ha segnalato (fuori dal loro perimetro) che `ApiCommessaStato`
([views.py:635](../../../../backend/apps/vendite/api/views.py#L635)) dichiara
`area_funzionale = "vendite"` **ma non ha `post_permission`**: chiunque abbia
accesso all'area vendite può portare una commessa a `CHIUSA`/`ANNULLATA` — atto
**irreversibile** — mentre le azioni molto meno gravi (prezzi N5/N7, porta oneri)
sono gated. I guard E-DB-1 riducono il **danno** ma non sostituiscono il
**permesso** (assi diversi: *cosa è lecito* vs *chi può*). Se si chiude, serve:
un codename in `config.azioni_processo` (micro-append CSV → team DB) +
`post_permission` sulla view + gate FE `useActionPermission`. **Da decidere Tid.**

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
| ~~P-3~~ | ✅ **CHIUSO 2026-07-21** — Template fattura id 77 (sorgente FATTURA, emittente 32), versione 48 PUBBLICATA + **`is_default=true`** applicato da Tid. Stampa/anteprima/ristampa risolvono il default. | — |
| P-4 | Soglia oltre cui un'operazione «singola» diventa background (I-3): il criterio è la cardinalità, ma se il documento singolo risultasse lento va tarato sull'evidenza | in C-3, con numeri veri |
| P-5 | Cadenza del worker drainer (cron) e numero di worker paralleli: `FOR UPDATE SKIP LOCKED` regge il parallelismo, ma la cadenza va tarata sul ritardo accettabile tra «Rendi definitive» e PDF disponibile | in C-2b, con volumi veri |
| ~~P-6~~ | ✅ **CHIUSO 2026-07-20**. Era: scritture famiglia commesse cross-emittente (nessuna RLS su `commesse`/`commesse_attivita`). **DB**: [brief-db-rls-commesse.md](../work-done/brief-db-rls-commesse.md) — P1–P4 applicati+pgTAP `plan(5)` verde+pushati su `dev/db-tid` (policy `rls_commesse_ef_whitelist` + `rls_commesse_attivita_ef_whitelist` via `fn_scope_ef_whitelist_via_sr`/`_via_commessa`, ENABLE NO FORCE). **BE gate verificati**: **G-1** (probe-first) già soddisfatto per costruzione — approva/stato/prezzi leggono con SELECT SECURITY INVOKER (`get_commessa_stato_codice`/`get_capabilities`/`get_attivita_pricing`) **prima** di ogni UPDATE → fuori scope = 404 identico a inesistente, nessun no-op silenzioso; regressione blindata (`test_prezzi_attivita_fuori_scope_o_inesistente_404`, doc `api_commesse_pricing.md` §Scope emittente). **G-2** (WITH CHECK push operatore): sicuro per costruzione — la commessa eredita l'emittente dal documento sorgente, già RLS-scoped, quindi in-whitelist. Resta lo **smoke end-to-end reale** = validazione in-app di Tid (DB dev vuoto, come A/B). **FORCE ROW LEVEL SECURITY** = ondata coordinata futura (fuori scope brief) |

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
