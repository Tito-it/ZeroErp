# Brief Design — Gestione dei processi di fatturazione dalla Dashboard Competenza

> **Tipo**: brief di design (modello + decisioni da prendere → poi brief operativi per fase)
> · **Data**: 2026-07-19 · **Owner**: Tid · **Stato**: 🟢 **DECISO (Tid, 2026-07-19)** —
> le 6 decisioni §8 sono chiuse; prossimo passo: derivare i brief operativi per fase (§9),
> a partire dal brief DB-1 (seed azioni processo) per la Fase A.
>
> **Scopo in una riga**: dare all'operatore la **guida dei processi di fatturazione**
> (approvazione → emissione → lotto → numerazione) **dentro la Dashboard Competenza**,
> riducendo l'esecuzione a pochi verbi ad alto livello — oggi il motore è completo ma si
> pilota solo via cron/curl.
>
> **Brief operativi derivati** (2026-07-19):
> [brief-db-processi-fatturazione-cockpit.md](brief-db-processi-fatturazione-cockpit.md)
> (solo seed: 2 azioni processo + task stampa nello step DEFINITIVA) →
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)
> (piano a step, Fasi A→D).
>
> **Documenti collegati**:
> [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> (design-of-record del read-side: le tre lenti; questo brief è il suo complemento
> **write-side**) · [Guida fatturazione](../../guide/fatturazione.md) (pipeline end-to-end)
> · [Guida gestione commesse](../../guide/gestione-commesse.md) ·
> [Guida cruscotti fatturazione](../../guide/cruscotti-fatturazione.md) ·
> [fatturazione-roadmap.md](fatturazione-roadmap.md) (§5 «la dashboard non è un report,
> è uno strumento di governo» — questo brief realizza quel punto).

---

## 1. Fotografia — il motore c'è tutto, la guida non c'è

Verifica sul codice vivo (2026-07-19):

**Esecuzione (motore) — COMPLETA, headless:**

| Pezzo | Stato | Come si invoca oggi |
|---|---|---|
| Push sorgenti → commesse (`CommessaPushOrchestrator`, handler per sorgente, advisory lock) | ✅ | `POST /vendite/commesse/push/run/` o batch |
| Governo commessa (stati data-driven, `fn_available_actions_commessa`, approvazione righe `fn_approva_commessa_attivita`, azioni prezzo N5/N7) | ✅ DB | stato: `POST /commesse/<id>/stato/` · **approvazione righe: fn DB senza endpoint** |
| Pull commessa → AF (`pull_attivita_da_commessa`, primo step del lotto) | ✅ | dentro la pipeline lotto |
| Pipeline lotti a step (DRAFT→EMESSA→DEFINITIVA→INVIATA, task-run, rollback, segnalazioni) | ✅ | `POST /pipeline/run/` (UN step) · `POST /pipeline/run-until-done/` (fino in fondo) |
| Diagnostica lotto (fatture, task-runs, segnalazioni, reset draft lotto/fattura) | ✅ | 5 endpoint `lotti/<id>/...` |
| **Driver batch a due corsie** (`run_fatturazione_batch --modalita immediata|differita`): scopre le coppie (emittente, tipo_doc) emittibili e completa la pipeline per coppia; canale sistema RLS + `job_run_log` | ✅ | cron/systemd, **non dall'app** |

**Osservazione (read-side) — COMPLETA:** le tre lenti (Competenza `/vendite/dashboard-competenza`,
Backlog, Situazione aperta) + slice 3-ter DDT/resi (in validazione).

**Guida (write-side in app) — ASSENTE:**

* nel FE **non esiste** alcuna vista per commesse, lotti, pipeline o push: l'unico
  `CommessaDrawer` è quello **read-only** del lineage;
* la Lente 1 mostra gli stadi `DA_APPROVARE → DA_EMETTERE → EMESSA_NON_FATTURATA →
  FATTURATA` ma **nessuno stadio è azionabile**: l'operatore vede il fermo e non può
  sbloccarlo;
* l'approvazione righe commessa (`fn_approva_commessa_attivita`) non ha endpoint;
* il batch gira da solo fino in fondo (numerazione inclusa) senza che l'app mostri né
  governi i suoi esiti (i log stanno in `maintenance.job_run_log` / `event_log`, non in UI).

**Conclusione**: non serve un nuovo motore, serve il **cockpit**. Il costo è quasi tutto
BE-endpoint sottili + FE; il DB è già pronto (salvo seed azioni processo, §7).

---

## 2. Principio di design — quattro regole

1. **La Lente 1 è il cockpit.** La Dashboard Competenza risponde già a *«cosa manca per
   chiudere il mese?»*; ogni stadio del funnel acquisisce **l'azione che lo fa avanzare**.
   Non si crea una "pagina processi" separata: il punto dove si vede il fermo è il punto
   dove lo si sblocca. (Le viste `vw_dash_competenza_*` restano read-only: le azioni sono
   endpoint di comando accanto, additivi — zero impatti sul read-side.)
2. **Una sola via di esecuzione.** La UI invoca **le stesse primitive del batch**
   (`run_lotto_pipeline`, `run_lotto_pipeline_until_done`, push orchestrator, fn DB).
   Nessuna seconda implementazione "da interfaccia": cambia solo chi preme il bottone e
   con quale perimetro.
3. **Automatico di default, manuale per governo.** La corsia **immediata** (GIORNALIERO) e
   il push ricorrente girano da cron; l'operatore governa la corsia **differita** (il
   "chiudi mese"), le approvazioni e le **eccezioni** (errori, reset, recuperi). La UI
   mostra sempre gli esiti dell'automatico (job_run_log) perché il silenzio non è governo.
4. **Gate fiscale esplicito.** Tutto ciò che è pre-fiscale (DRAFT/EMESSA) è ripetibile e
   demolibile (`reset_lotto_draft`); la **numerazione** (DEFINITIVA) è irreversibile. In
   UI i due mondi non stanno mai dietro lo stesso pulsante: «Fattura» porta a EMESSA,
   «Rendi definitive» è un'azione separata e consapevole (vedi D-1).
5. **La cardinalità decide sincrono o batch** (regola di Tid, 2026-07-19). Il criterio non
   è il tipo di processo ma **quanti documenti tocca**: *un solo documento* (calcolo di una
   fattura, stampa di una fattura, azione su una commessa) → **sincrono**, risposta
   immediata; *da due in su* → **batch in background**, la pagina non resta mai bloccata.
   Vale per ogni processo di fatturazione — approvazione, giro, numerazione, stampa — senza
   eccezioni e senza doverlo decidere caso per caso.
6. **La stampa è un processo separato e "stupido"** (regola di Tid, 2026-07-19). Non
   contiene logica di fatturazione: **legge le informazioni che già esistono e produce
   1..N documenti**, punto. Non calcola, non decide, non cambia stati. È il *frontend* di
   ciò che gli altri processi hanno già scritto — e per questo è ri-eseguibile a piacere e
   riusabile da qualunque dominio (vedi §5-bis).

---

## 3. Il vocabolario dell'operatore — quattro verbi

La semplificazione chiesta («semplificare molto l'esecuzione dei passaggi») è prima di
tutto di **vocabolario**: push, pull, lotto, step, task-run sono meccanica interna. Per
l'operatore il mese di competenza si lavora con **quattro verbi**, nell'ordine del funnel:

| # | Verbo | Cosa fa sotto | Stadio che svuota |
|---|---|---|---|
| 1 | **Approva** | `fn_approva_commessa_attivita` (per riga, per commessa o per tutto il mese) | `DA_APPROVARE` |
| 2 | **Fattura** | discovery emittibili + lotto per coppia (emittente, tipo_doc) + pipeline **fino a EMESSA** | `DA_EMETTERE` + `EMESSA_NON_FATTURATA` |
| 3 | **Rendi definitive** | step DEFINITIVA sui lotti EMESSA del mese — **numerazione + stampa in un processo unico** (D-1) | `FATTURATA/EMESSA` → `FATTURATA/DEFINITIVA` |
| 4 | **Invia** | step INVIATA (SDI) — predisposto, si accende quando esiste il builder XML | `FATTURATA/DEFINITIVA` → `INVIATA` |

Note di modello:

* il **pull commessa→AF non è un verbo**: è il primo step del lotto, l'operatore non lo
  vede mai (già così nel motore);
* il passaggio commessa → `PRONTA_FATTURAZIONE` di norma lo fa il push (transizioni
  automatiche); quando serve la mano (`meta.manuale`) l'azione è **nel drawer commessa**
  via `available_actions`, non un quinto verbo di dashboard;
* «Fattura» è **cumulativo come il batch** (competenza ≤ M: include gli arretrati) — la
  stessa semantica di `--competenza` del driver, nessuna divergenza;
* la **coppia (emittente, tipo_doc)** resta l'unità tecnica del giro: il verbo la nasconde
  ma l'esito la mostra (N coppie riuscite / M in errore).

---

## 4. Mappa stadio → azione nella Dashboard Competenza

Il cuore del design: ogni elemento della Lente 1 diventa azionabile.

### 4.1 Card stadio + drill-down attività

| Stadio | Azione in card | Azione per riga (kebab, `RowActionsMenu`) |
|---|---|---|
| `DA_APPROVARE` | **Approva tutto il mese** (conferma con contatore: «Approvi N attività per M?») | Approva · Apri commessa |
| `DA_EMETTERE` | — (informativa: «verranno emesse dal prossimo giro») + **Fattura adesso** | Apri commessa (lì: rendi pronta / prezzi N5-N7) |
| `EMESSA_NON_FATTURATA` | **Fattura adesso** (stesso comando del verbo 2) | Apri commessa |
| `FATTURATA` (breakdown per stato) | **Rendi definitive** (sui lotti EMESSA) · «Inviate» quando ci sarà SDI | Apri fattura/lotto |
| Pannello **errori** | — | Apri lotto (drawer diagnostico con rerun/reset) |

Il drill-down attività ha già `commessa_id`/`stadio` per riga (`vw_dash_competenza_attivita`):
il kebab si aggancia senza toccare le viste.

### 4.2 Barra azioni pagina (`PageActionsBar`, mese selezionato)

* **Aggiorna commesse** — `POST /commesse/push/run/` (esiste): porta in commessa le
  sorgenti mature; esito a toast + refresh aggregata.
* **Fattura competenza M** — il verbo 2 (endpoint nuovo, §6): corsia differita sul
  perimetro ≤ M dell'operatore.
* **Esito ultimo giro** — chip/pannellino con l'ultimo run per corsia da
  `maintenance.job_run_log` (immediata notturna + differita manuale): quando, esito,
  coppie ok/errore. Regola 3 del §2: l'automatico si vede.

### 4.3 Drawer Commessa operativo (nuovo)

Oggi esiste solo il drawer **lineage** (read-only). Serve il drawer autonomo di **governo**
(pattern `feedback_drawer_autonomi`, richiamabile da drill-down, backlog e lineage):

* testata + stato + contatori: già tutto in `fn_get_commessa_stato` (che espone anche
  `capabilities`/`available_actions` — il telaio azioni è `useDrawerActions` +
  `DrawerActionsBar`, pattern preventivi/contratti);
* righe (`GET /commesse/<id>/attivita/`, esiste) con selezione multipla → **Approva
  selezionate** (nuovo endpoint, la fn accetta `p_righe_ids`);
* azioni prezzo per riga: riallinea N5 / variazione eccezionale N7 / sblocca (endpoint
  esistenti) — qui si smaltisce anche `total_prezzo_da_riallineare`;
* cambio stato via `available_actions` (`POST /commesse/<id>/stato/`, esiste);
* pannello Passaggi (lineage) riusato come tab.

### 4.4 Lotti — lista + drawer diagnostico (nuovo FE, endpoint già completi)

I lotti sono il **registro dei giri**: servono quando qualcosa va male o per il gate
fiscale, non come percorso quotidiano.

* Lista `/vendite/lotti` (endpoint esiste): filtro competenza/stato, pattern
  `ListaConfigurabile`;
* drawer lotto: step corrente + fatture (`lotti/<id>/fatture/`), task-run con tentativi
  (`task-runs/`), segnalazioni (`segnalazioni/`), timeline eventi;
* azioni: **Avanza step** (`pipeline/run/` sul lotto — un step per click, com'è il
  motore), **Rerun** su ERRORE, **Riporta a bozza** (`reset-draft/` — conferma forte con
  linguaggio onesto: *demolisce le fatture pre-fiscali del lotto, le attività restano
  pronte per un lotto nuovo*), reset singola fattura DRAFT.
* Raggiungibilità: dal breakdown 3a, dal pannello errori, dal menu vendite (D-4).

---

## 5. Il verbo «Fattura» — riusare il driver batch, non reinventarlo

`run_fatturazione_batch` fa già esattamente il lavoro del verbo 2: discovery coppie
emittibili → lotto per coppia → pipeline per coppia, best-effort (una coppia in errore
non blocca le altre), registrazione run. La proposta è **estrarne il core** in un service
riusabile (`fatturazione_driver_service`, nome indicativo) con due chiamanti:

| Chiamante | Contesto RLS | Corsia | Trigger |
|---|---|---|---|
| Management command (invariato) | canale sistema (`system_process_context`) | immediata (cron notturno) + differita (cron opzionale) | schedulato |
| **Endpoint nuovo** `POST /vendite/fatturazione/run/` | **operatore** (scope emittente RLS: fattura solo il suo perimetro — corretto per costruzione) | differita, `competenza ≤ M` | pulsante «Fattura competenza M» |

Punti fermi:

* **fermata a EMESSA** per il giro lanciato da UI (gate fiscale §2.4): il driver oggi va
  fino in fondo — serve il parametro «fino a stato X» sul core estratto (Python puro,
  niente DB). La numerazione è il verbo 3, azione separata;
* esecuzione secondo D-2: **sincrona sulle azioni a documento singolo** (una commessa, un
  lotto, una fattura), **in background sui giri multipli** (multi-coppia) — mai schermo
  bloccato a lungo; l'esito strutturato per coppia (il dict del driver) finisce nel
  monitoraggio esistente (`job_run_log` + `fatturazione_lotti_task_runs` + `event_log`)
  letto dal pannello «esito giri»;
* la **numerazione include la stampa** ed è un **processo unico** (vincolo D-1): stesso
  core per corsia immediata (inline) e massivo (pulsante umano, eventualmente cron) —
  il modo di avvio non genera software duplicato;
* idempotenza: `Idempotency-Key` obbligatoria + i lock già esistenti (lotto
  `IN_ESECUZIONE`, advisory lock push) rendono innocuo il doppio click.

---

## 5-bis. La stampa — processo separato, stupido, già quasi tutto in casa

**La regola (§2.6)**: la stampa non sa nulla di fatturazione. Riceve *quali* documenti
produrre, li legge e li genera. Nessuna logica di dominio, nessun cambio di stato.

**Il riscontro nel codice (2026-07-19)**: quel processo **esiste già ed è esattamente così**.
`documenti.DocumentGenerationService.genera_documento` è sorgente-agnostico — riceve
`(sorgente_tipo_id, sorgente_id, sorgente_uid, emittente)`, risolve il template e produce
il PDF persistito; la famiglia di endpoint documentali (genera / anteprima / lista / file /
download) è una **factory condivisa** (`build_documenti_sorgente_views`) già cablata su 5
domini (preventivi, offerte, contratti, ordini, DDT). Non c'è nulla da riprogettare: c'è da
**riusare**.

Restano due buchi, entrambi piccoli:

| Buco | Cosa manca | Nota |
|---|---|---|
| **B-a — FATTURA non è cablata** | La famiglia documentale non è istanziata su `FATTURA` (`config.sorgenti` id 10, target `vendite.fatture` — la sorgente c'è già) | ~10 righe di delta sulla factory + un template fattura |
| **B-b — non esiste il massivo** | Oggi si genera **un** documento per chiamata; manca il processo che ne produce **N** (le fatture di un lotto, una selezione) come job in background | è il §2.5 applicato alla stampa |

**Come si concilia con D-1** («numerazione e stampa = processo unico»): i due requisiti
vivono su assi diversi e non si contraddicono.

* **Asse orchestrazione (D-1)**: per l'operatore «Rendi definitive» è **un atto solo** che
  produce fatture numerate *e* stampate. Lo si ottiene mettendo la stampa come **secondo
  task dello stesso step DEFINITIVA**, dopo `numera_fatture`: chiunque avvii quello step —
  pulsante, cron, batch — esegue necessariamente entrambi, e non esiste un chiamante che
  possa "dimenticarsi" la stampa.
* **Asse componente (§2.6)**: il task di stampa è un **adattatore sottile** che si limita a
  dire *«questi sono i documenti, generali»* e delega al processo stampa generico. La
  logica di rendering non entra mai nella pipeline, e il processo stampa resta invocabile
  **da solo** — ristampa di una fattura, stampa on-demand, ristampa massiva — senza passare
  dalla fatturazione.

Detto altrimenti: **un solo atto per l'utente, un solo componente per il codice**. La
pipeline decide *quando* e *su cosa*; la stampa sa solo *come*.

> Perché non uno step di pipeline dedicato alla stampa: gli step del lotto sono **stati
> fiscali** (`config.stati_doc_fiscale`: DRAFT → EMESSA → DEFINITIVA → INVIATA). «Stampata»
> non è uno stato fiscale e inventarlo sporcherebbe la macchina a stati. Un task dentro lo
> step è la collocazione corretta: ha già il suo `task_run` con tentativi ed esito, ed è
> ri-eseguibile da solo.

## 6. Gap da colmare (concentrico: contratto completo da subito, consegna a fasi)

### DB (→ eventuali brief al team su `dev/db-tid` — nulla di strutturale)

| # | Cosa | Note |
|---|---|---|
| DB-1 | Seed `config.azioni_processo`: `approva_attivita_commessa`, `numera_fatture_lotti` (la numerazione merita permesso proprio, distinto da `genera_fatture_lotti`) | solo seed; pattern action-gate |
| DB-2 | **Task stampa nello step DEFINITIVA** (D-1 + D-7): registry `dbops.pipeline_task_registry(_impl)` + append ai `processi` dei due step DEFINITIVA (MASSIVO id 4, GIORNALIERO id 6). Il task è un **adattatore**: la logica di stampa resta nel processo generico | verificato: la stampa **non è** oggi un task del motore |
| DB-3 | ~~Riepilogo lotti per competenza~~ — ✅ **verificato 2026-07-19: nessuna vista nuova**. `list_lotti` filtra già competenza/stato/tipo_doc/emittente/utility con display fields e scope | voce chiusa |

### Backend

| # | Endpoint/Service | Verbo/superficie |
|---|---|---|
| BE-1 | `POST /vendite/commesse/<id>/attivita/approva/` (body: `righe_ids` opz. = tutte) → `fn_approva_commessa_attivita` | Approva (drawer) |
| BE-2 | `POST /vendite/fatturazione/approva-competenza/` (mese → approvazione massiva sulle commesse del perimetro; loop BE sulla fn per commessa) | Approva (card stadio) |
| BE-3 | Estrazione core driver + `POST /vendite/fatturazione/run/` (corsia differita, `fino_a_stato`, esito per coppia) | Fattura · Rendi definitive |
| BE-4 | `GET /vendite/fatturazione/esiti/` (ultimi run per corsia da `job_run_log`) | Esito ultimo giro |
| BE-5 | `GET /vendite/lotti/<id>/` (dettaglio testata; le sotto-risorse esistono già) | Drawer lotto |
| BE-6 | `GET /vendite/commesse/` (lista minima per lookup/da-drill; il dettaglio è `fn_get_commessa_stato`) | Drawer commessa |

### Frontend

| # | Cosa | BB riusati |
|---|---|---|
| FE-1 | Azioni card/kebab/PageActionsBar in `DashboardCompetenzaView` | `RowActionsMenu`, `PageActionsBar`, action-gate, `useConfirmAction` |
| FE-2 | `CommessaGestioneDrawer` (drawer autonomo di governo) | `useDrawerActions`, `DrawerActionsBar`, `useDrawerContentReady`, master-detail inline, `useApiHandler` |
| FE-3 | `LottiListView` + `LottoDrawer` diagnostico | `ListaConfigurabile`/`useListaConfigurabilePage`, `usePagedDashFetch`, `statoDocFiscaleSeverity` |
| FE-4 | Pannello «esito giri» in dashboard | `DashEmptyState`, `labelOrCode`, i18n `dash_comune` |

---

## 7. Perché NON passa dalle pratiche (collocazione rispetto a GUIDA)

Il meccanismo GUIDA (avanzamento milestone su proiezione) governa le **pratiche** sui
documenti a monte (preventivi, poi offerta/contratto/ordine). La fatturazione a valle
della commessa è un **processo massivo e ciclico**, non una pratica per documento: farne
flussi-pratica moltiplicherebbe entità senza valore. Il punto di contatto resta quello già
disegnato: le sorgenti arrivano in commessa guidate dalle pratiche/GUIDA; **da lì in poi
governa la dashboard**. (La «Fase 4 — Guida» del piano due-lenti è documentazione utente e
recepirà anche questo brief.)

---

## 8. Decisioni da prendere con Tid

| # | Domanda | Proposta |
|---|---|---|
| D-1 | **Gate fiscale**: il giro da UI si ferma a EMESSA con «Rendi definitive» separato. E il **batch notturno**? (oggi completa tutto, numerazione inclusa) | ✅ **DECISA (Tid, 2026-07-19)**: corsia **immediata completa** (numera da sola); corsia **differita si ferma a EMESSA** — la numerazione è un **processo separato avviato da umano** per il massivo. ⚠️ Vincoli di Tid: (a) il processo di numerazione **include la stampa** ed è **un processo unico** numerazione+stampa; (b) **mai duplicare i processi** — immediata e massivo eseguono **lo stesso core**, cambia solo il modo di avvio (inline nel giro immediato · pulsante umano o eventualmente cron nel massivo). Il modo di esecuzione non genera software duplicato |
| D-2 | **Forma dell'esecuzione da UI**: sincrona con esito per coppia vs job registrato + polling | ✅ **DECISA (Tid, 2026-07-19)**: decide la **cardinalità** (§2.5) — **un solo documento → sincrono**, **due o più → batch in background**, mai schermo bloccato a lungo. Vale per ogni processo di fatturazione (approvazione, giro, numerazione, stampa), nessuna eccezione. Il monitoraggio **riusa l'infrastruttura esistente**: `maintenance.job_run_log` (run, via `registered_job`), `vendite.fatturazione_lotti_task_runs` (step/tentativi per lotto), `vendite.event_log` (timeline con correlation_id) → il pannello «esito giri» (§4.2/BE-4) legge da lì |
| D-7 | **Natura del processo di stampa** (Tid, 2026-07-19) | ✅ **DECISA**: processo **separato da tutti gli altri e "stupido"** — nessuna logica di dominio: legge le informazioni esistenti e genera 1..N documenti (§2.6). Concilia con D-1 su assi diversi: **un atto solo per l'utente** (task accodato allo step DEFINITIVA) + **un componente solo per il codice** (adattatore sottile → processo stampa generico, invocabile anche da solo per ristampe). Riusa `DocumentGenerationService` + la factory documentale esistenti; da colmare solo il cablaggio FATTURA e la variante massiva (§5-bis) |
| D-3 | **Approvazione massiva** dal card stadio (tutto il mese in un click) oltre a quella per commessa/righe | ✅ **DECISA (Tid, 2026-07-19)**: **tutte e tre le grane** — per riga/selezione e per commessa nel drawer, massiva «tutto il mese» dal card con dialogo di conferma (contatore + valore totale); il drill-down resta a un click per chi vuole scorrere prima le righe |
| D-4 | **Collocazione Lotti**: voce di menu vendite vs solo drawer da dashboard | ✅ **DECISA (Tid, 2026-07-19)**: **voce di menu dedicata** (`/vendite/lotti`, lista con filtri competenza/stato) **+ accesso contestuale dalla dashboard** (pannello errori e breakdown atterrano sul lotto già filtrato); il drawer lotto è lo stesso componente nei due percorsi |
| D-5 | **Push sorgenti**: schedulato + pulsante manuale «Aggiorna commesse» | ✅ **DECISA (Tid, 2026-07-19)**: **entrambi** — cron ad alta frequenza per l'allineamento continuo + pulsante «Aggiorna commesse» in dashboard per il refresh immediato a richiesta. Stesso processo, due modi di avvio (vincolo D-1: mai duplicare); l'advisory lock rende innocua la sovrapposizione |
| D-6 | **Stop-lista v1** del §6 (BE-1..6, FE-1..4): tutto in v1 o si taglia? | ✅ **DECISA (Tid, 2026-07-19)**: **tutto il contratto** disegnato ora (concentrico, nessun v1.1 da ricucire); «Invia»/SDI predisposto ma spento fino al builder XML; consegna secondo le fasi A→D del §9 |

## 9. Piano di consegna (dopo la chiusura di §8)

Dettaglio operativo e avanzamento step-by-step:
[brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md).

| Fase | Contenuto | Prerequisiti |
|---|---|---|
| A — Sbloccare gli stadi | BE-1/2 + FE-1 (approvazioni da dashboard) + FE-2 (drawer commessa) | brief DB **D1** (seed azioni) |
| B — Lotti visibili e governabili | BE-5 + FE-3 (lista+drawer lotto, avanza/rerun/reset) | nessuno DB (DB-3 chiusa) |
| C — I verbi Fattura / Rendi definitive | estrazione core driver + BE-3/4 + handler stampa + PageActionsBar + esiti giri (FE-4) | Fase A+B; brief DB **D2** (task stampa) |
| D — Guida utente | sezione nella guida cruscotti (linguaggio non tecnico, i 4 verbi) | si salda alla Fase 4 due-lenti |

## 10. Non-obiettivi

* Note di credito / slice NC (la coda accrediti resta com'è, slice 3-ter);
* builder XML SDI e invio (il verbo 4 è predisposto, si accende dopo);
* integrazione contabile, multi-esercizio, alerting (roadmap §2/§3/§6);
* agenda/coda lavoro operatori (documento dedicato, ortogonale);
* modifiche alle viste `vw_dash_*` o alla semantica delle tre lenti.

---

*Brief vivo: a chiusura delle decisioni §8 aggiornare lo stato in testata e derivare i
brief operativi per fase (eventuali brief DB al team su `dev/db-tid`, BE/FE su
`dev/backend-tid`).*
