# Brief BE/FE — Cockpit processi fatturazione in Dashboard Competenza

> **Tipo**: brief operativo BE/FE (piano a step) · **Target**: `dev/backend-tid`
> · **Data**: 2026-07-19 · **Owner**: Tid · **Stato**: ⬜ **DA INIZIARE**
>
> **Design-of-record**:
> [brief-design-gestione-processi-fatturazione.md](brief-design-gestione-processi-fatturazione.md)
> (decisioni **D-1..D-7**, chiuse 2026-07-19).
> **Prerequisito DB**:
> [brief-db-processi-fatturazione-cockpit.md](brief-db-processi-fatturazione-cockpit.md)
> — **gate**: gli step che usano le azioni di processo e il task stampa partono a oggetti
> DB applicati ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]).
> **Parte da**: motore fatturazione completo e headless + le tre lenti vive.

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
| I-2 | **Numerazione = numerazione + stampa** | D-1: è uno step di pipeline con due task (seed DB), non due chiamate del caller |
| I-3 | **La cardinalità decide sincrono o batch** | D-2/§2.5 design: **1 documento → sincrono** (calcolo o stampa di una fattura, azione su una commessa); **2+ → batch in background**, la pagina non resta mai bloccata. Criterio unico, per ogni processo di fatturazione |
| I-4 | **La stampa è stupida** | D-7: legge ciò che esiste e genera 1..N documenti. Zero logica di dominio, zero cambi di stato, zero calcoli. Chi la invoca decide *cosa*; lei sa solo *come* |
| I-5 | **Monitoraggio con l'esistente** | D-2: `maintenance.job_run_log` + `vendite.fatturazione_lotti_task_runs` + `vendite.event_log`. Niente tabelle nuove di tracciamento |
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

## FASE C — I verbi «Fattura» e «Rendi definitive»

> Obiettivo: il cuore del cockpit. Qui vive il vincolo I-1: si **estrae** il core del driver
> batch, non lo si riscrive.

| # | Step | Dettaglio | Stato |
| --- | --- | --- | --- |
| C-1 | **BE — estrazione core driver** | Da `run_fatturazione_batch` (management command) estrarre `fatturazione_driver_service` (nome indicativo): discovery coppie `(emittente, tipo_doc)` emittibili → lotto per coppia → pipeline per coppia, **best-effort** (una coppia in errore non blocca le altre) + esito strutturato. Nuovo parametro **`fino_a_stato`** (Python puro, nessun DB): il giro da UI e il massivo da cron si fermano a **EMESSA** (D-1). Il command diventa un **chiamante sottile** — comportamento invariato, coperto dai test esistenti | ⬜ |
| C-2 | **BE — cablare la famiglia documentale su FATTURA** | La sorgente `FATTURA` esiste (`config.sorgenti` id 10, target `vendite.fatture`, `key_selector=id`) ma **non è istanziata** sulla factory `build_documenti_sorgente_views` (oggi: preventivi, offerte, contratti, ordini, DDT). Delta ~10 righe → `fatture_documenti_views.py` (genera / anteprima / lista / file / download) + template fattura. **Sblocca la stampa singola sincrona** (I-3) e la ristampa on-demand | ⬜ |
| C-2b | **BE — processo stampa massivo** | Il pezzo che manca davvero (D-7 §5-bis, buco B-b): un processo che genera **N** documenti — input `(sorgente_tipo, ids[])`, output N documenti — eseguito **in background** (I-3) con `registered_job`, per-documento resiliente (un render fallito non ferma gli altri) e **idempotente**. **Stupido per contratto** (I-4): nessuna conoscenza di lotti, fatture o fatturazione; internamente cicla `DocumentGenerationService.genera_documento`. Riusabile da qualunque dominio | ⬜ |
| C-2c | **BE — handler task `stampa_documenti_lotto_default`** | Registrato in `PipelineStepExecutor.handler_registry` (il seed DB lo dichiara). **È un adattatore, non un generatore**: risolve gli id delle fatture del lotto e li passa al processo C-2b. Nessuna logica di rendering nella pipeline (I-4). Ri-eseguibile con rerun del solo task. ⚠️ **P-1**: `genera_documento` pretende un `user` autenticato e da lì risolve lo scope emittente — in contesto batch/sistema non c'è request user. Da chiudere **prima** di C-2b/C-2c (variante che accetta lo scope già risolto, o attore di sistema): oggi la stampa funzionerebbe da UI e fallirebbe da cron | ⬜ |
| C-3 | **BE — endpoint giro fatturazione** | `POST /vendite/fatturazione/run/` · body `{competenza_mese, fino_a_stato}` · corsia **differita**, perimetro `competenza ≤ M` (cumulativo come il batch), scope emittente dell'operatore via RLS. `post_permission = "genera_fatture_lotti"`, `Idempotency-Key`. **I-3**: multi-coppia → esecuzione in background con run registrato (`registered_job`), risposta = handle del run; la coppia singola resta sincrona | ⬜ |
| C-4 | **BE — endpoint numerazione** | `POST /vendite/fatturazione/numera/` (o `lotti/<id>/numera/` per il singolo) → step DEFINITIVA sui lotti EMESSA del perimetro. `post_permission = "numera_fatture_lotti"`. **I-2**: esegue lo step, che contiene numerazione **e** stampa — l'endpoint non chiama la stampa per conto suo | ⬜ |
| C-5 | **BE — esiti dei giri** | `GET /vendite/fatturazione/esiti/`: ultimi run per corsia da `maintenance.job_run_log` (quando, esito, coppie ok/errore, messaggio) — **I-4**, nessuna tabella nuova | ⬜ |
| C-6 | **FE — PageActionsBar del mese** | «Aggiorna commesse» (push, endpoint esistente — **D-5**) · «Fattura competenza M» (C-3) · «Rendi definitive» (C-4, azione **separata** e visivamente distinta — I-6) · pannello/chip «esito ultimo giro» (C-5) | ⬜ |
| C-7 | **FE — azioni sulle card stadio** | «Fattura adesso» su `DA_EMETTERE` / `EMESSA_NON_FATTURATA`; «Rendi definitive» sul breakdown `FATTURATA/EMESSA`; feedback di avanzamento per i giri in background + refresh a fine run | ⬜ |
| C-8 | **FE — stampa e ristampa** | Da una fattura: «Stampa/Anteprima» sincrona (C-2, componenti documentali già esistenti nei 5 domini — si riusa il pattern, non si inventa); da lotto/selezione: «Ristampa» massiva in background (C-2b) con esito nel pannello giri | ⬜ |
| C-9 | **Test + doc + smoke** | Test service driver (fermata a stato, best-effort, perimetro) + stampa massiva (resilienza per-documento, idempotenza) e API; **smoke E2E** «approva → fattura → rendi definitive» su dati veri, che verifica anche **numerazione e stampa nello stesso atto** (gli smoke scoprono i GRANT/scope che i test mock non vedono); doc `api_fatturazione.md` + `api_documenti_*` + `api.md` | ⬜ |

**Gate di uscita C**: un mese di competenza si chiude interamente dall'app, con la
numerazione come atto separato e consapevole.

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
| P-1 | `genera_documento` in contesto batch/sistema (nessun request user, scope emittente risolto dall'utente) — vedi C-2c. **Oggi la stampa funzionerebbe da UI e fallirebbe da cron** | prima di C-2b/C-2c |
| P-2 | Stampa best-effort vs bloccante sul fallimento render | risposta del team DB al §3.4 del brief DB |
| P-3 | Template fattura: non esiste ancora (i template sono dato di configurazione, non seed). Senza, la stampa non ha cosa renderizzare | prima di C-2 in-app |
| P-4 | Soglia oltre cui un'operazione «singola» diventa background (I-3): il criterio è la cardinalità, ma se il documento singolo risultasse lento va tarato sull'evidenza | in C-3, con numeri veri |

---

*Brief vivo: chiudere gli step aggiornando la colonna **Stato** (⬜ → ✅ con data) mano a
mano che avanzano; a fine cantiere il documento passa in `work-done/` con il consuntivo.*
