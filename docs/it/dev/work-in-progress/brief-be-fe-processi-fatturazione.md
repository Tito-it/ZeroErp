# Brief BE/FE — Cockpit processi fatturazione in Dashboard Competenza

> **Tipo**: brief operativo BE/FE (piano a step) · **Target**: `dev/backend-tid`
> · **Data**: 2026-07-19 · **Owner**: Tid · **Stato**: ⬜ **DA INIZIARE**
>
> **Design-of-record**:
> [brief-design-gestione-processi-fatturazione.md](brief-design-gestione-processi-fatturazione.md)
> (decisioni **D-1..D-7**, chiuse 2026-07-19).
> **Prerequisito DB**:
> [brief-db-processi-fatturazione-cockpit.md](brief-db-processi-fatturazione-cockpit.md)
> (decisioni **B-1..B-5**, revisione outbox 2026-07-19) — **gate**: gli step che usano le
> azioni di processo e la coda stampa partono a oggetti DB **G1** applicati
> ([[feedback_be_fe_attende_prerequisiti_db]]).
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
| A-1 | **BE — endpoint approvazione righe commessa** | `POST /vendite/commesse/<id>/attivita/approva/` · body `{righe_ids?: int[]}` (assente = tutte le NON_EMESSA) → `fn_approva_commessa_attivita(p_commessa_id, p_righe_ids, p_user)`. `post_permission = "approva_attivita_commessa"`, `Idempotency-Key` (la fn è già idempotente: 2ª chiamata = 0 righe). Ritorna `{approvate: N}` | ⬜ |
| A-2 | **BE — approvazione massiva per competenza** | `POST /vendite/fatturazione/approva-competenza/` · body `{competenza_mese, commessa_ids?}` → risolve le commesse del perimetro (scope emittente RLS) e cicla A-1 per commessa in **una** `transaction.atomic()`; esito `{commesse: N, approvate: M, errori: [...]}`. Stesso permesso di A-1 | ⬜ |
| A-3 | **BE — lista/dettaglio commessa per il drawer** | `GET /vendite/commesse/` (lista minima filtrabile per competenza/BA/stato, paginata) + `GET /vendite/commesse/<id>/` se `fn_get_commessa_stato` non basta da solo (già espone contatori + `capabilities`) | ⬜ |
| A-4 | **FE — `CommessaGestioneDrawer`** | Drawer **autonomo** ([[feedback_drawer_autonomi]]): testata+stato+contatori da `fn_get_commessa_stato`; azioni di stato da `available_actions` via `useDrawerActions`+`DrawerActionsBar`; righe da `GET /commesse/<id>/attivita/` con **selezione multipla** → «Approva selezionate» (A-1); azioni prezzo per riga (N5/N7/sblocco, endpoint esistenti); tab Passaggi (lineage riusato). Readonly-aware ([[feedback_drawer_readonly]]) | ⬜ |
| A-5 | **FE — azioni nella Dashboard Competenza** | Card `DA_APPROVARE` → «Approva tutto il mese» con `useConfirmAction` (conferma con **contatore + valore**); kebab `RowActionsMenu` sul drill-down → Approva riga · Apri commessa (apre A-4). Action-gate `action: 'approva_attivita_commessa'`; refresh aggregata + drill-down dopo l'azione | ⬜ |
| A-6 | **Test + doc** | Test service A-1/A-2 (validazione, idempotenza, perimetro, 0-righe), test API (permesso, 404, envelope); doc `api_commessa_attivita.md` aggiornata + `api.md`; cataloghi BB se emergono estrazioni | ⬜ |

**Gate di uscita A**: da `/vendite/dashboard-competenza` si porta `DA_APPROVARE` a zero senza
toccare curl, e ogni commessa è ispezionabile/governabile dal drawer.

---

## FASE B — Lotti visibili e governabili

> Obiettivo: il registro dei giri. Serve per le **eccezioni** (errori, reset, recuperi) e per
> il gate fiscale. Endpoint quasi tutti esistenti: è soprattutto FE.

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| B-1 | **BE — dettaglio lotto** | `GET /vendite/lotti/<id>/` (testata + step corrente + contatori). Le sotto-risorse esistono già: `fatture/`, `task-runs/`, `segnalazioni/`. ⚠️ Verificato: **nessuna vista DB nuova serve** (la lista filtra già per competenza/stato/emittente/tipo_doc con scope) | ⬜ |
| B-2 | **FE — `LottiListView`** | Rotta `/vendite/lotti` + voce di menu vendite (**D-4**), pattern lista standard ([[feedback_lista_pattern_standard]]): filtri competenza/stato/tipo_doc/emittente, `statoDocFiscaleSeverity`, kebab → apri drawer | ⬜ |
| B-3 | **FE — `LottoDrawer` diagnostico** | Step corrente + fatture + task-run (tentativi/esiti) + segnalazioni + timeline eventi. Tab, contenuto deferito (`@after-show`) | ⬜ |
| B-4 | **FE+BE — azioni sul lotto** | «Avanza step» (`pipeline/run/`, un step per click — com'è il motore) · «Rerun» su ERRORE · «Riporta a bozza» (`reset-draft/`) con **conferma forte e linguaggio onesto**: *demolisce le fatture pre-fiscali del lotto; le attività restano libere per un lotto nuovo* · reset singola fattura DRAFT. Action-gate sui permessi esistenti (`genera_fatture_lotti`, `reset_lotto_draft`, `reset_lotto_fattura_draft`) | ⬜ |
| B-5 | **FE — raggiungibilità contestuale** | Dal pannello **errori** e dal breakdown `FATTURATA` della dashboard si atterra sul lotto già filtrato (D-4: stesso drawer nei due percorsi) | ⬜ |
| B-6 | **Test + doc** | Test API dettaglio lotto; doc `api_lotti.md`/`api.md`; catalogo BB FE per i componenti nuovi | ⬜ |

**Gate di uscita B**: un lotto in ERRORE si diagnostica e si sblocca dall'app, senza psql.

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
(C-2b): il brief DB (§3, RLS della coda) conferma lo stesso pattern — scrittura del worker in
canale sistema, come `run_fatturazione_batch`.

---

*Brief vivo: chiudere gli step aggiornando la colonna **Stato** (⬜ → ✅ con data) mano a
mano che avanzano; a fine cantiere il documento passa in `work-done/` con il consuntivo.*
