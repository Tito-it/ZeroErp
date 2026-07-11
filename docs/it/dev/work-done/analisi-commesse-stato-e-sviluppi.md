# Analisi commesse — stato attuale e sviluppi necessari

> **Stato**: ✅ **CHIUSO (2026-06-18)** — roadmap §8 eseguita end-to-end (DB+BE). Restano
> solo **rinvii consapevoli** (UI commesse/monitor FE §4.2·§9, consumi utility tariffario
> §4.3#3, invio SDI reale §2.5) e **ops** (env/systemd + smoke a RLS *enforced*), che
> avranno documenti dedicati alla loro apertura. Spostato in `work-done`.
>
> **Data**: 15 giugno 2026
> **Tipo**: analisi di stato + piano sviluppi (base condivisa, pre-implementazione)
> **Metodo**: ricognizione codice/DB + workflow dinamico multi-agente (mappa stato
> reale → coerenza con guida/WIP → sintesi gap), con verifica diretta sui sorgenti
> dei punti critici. Le evidenze sono citate come `file:riga` o nome doc DB.
> **Destinatari**: Tid, sviluppatori BE/FE, team DB.
>
> **Vedi anche**:
> * [Guida tecnica API Commesse (DB layer)](/guide/gestione-commesse) — datata, da aggiornare (vedi §3)
> * [gestione-commesse-v2.md](gestione-commesse-v2.md) — piano v2 (feb 2026), in larga parte implementato ma fermo a febbraio
> * [sviluppo-fatturazione.md](../work-in-progress/sviluppo-fatturazione.md), [fatturazione-roadmap.md](../work-in-progress/fatturazione-roadmap.md), [fatturazione-attivita-progetto.md](fatturazione-attivita-progetto.md)
> * brief work-done: `brief-db-commesse-transizioni-stati.md`, `brief-db-commesse-multi-sorgente.md`, `brief-db-drop-uq-commesse-attivita-src-uid-partial.md`

---

## 1. Sintesi esecutiva

La catena **`sorgente → commessa → commesse_attivita → approvazione → PRONTA_FATTURAZIONE
→ attivita_fatturabili → lotto → fatture`** è **implementata e funzionante end-to-end
lato backend + DB** (fino alla generazione delle righe fattura e alla numerazione).

Il problema non è il motore, ma **la superficie e la rifinitura**:

- la commessa è oggi un'entità **headless**: nasce, si auto-approva e diventa
  fatturabile come **effetto collaterale del push**, senza alcun **frontend** che la
  renda consultabile o governabile;
- ~~esiste un **bug bloccante** sulle azioni prezzo (codice stale mai riallineato al
  refactor degli stati — §4.1)~~ → **✅ RISOLTO il 2026-06-15** (§4.1);
- la fatturazione **non è autonoma**: nessuno scheduler, pipeline "uno step per run";
- alcune funzionalità del modello (snapshot pricing, BoM/consumi multi-sorgente,
  transizioni manuali) sono **parziali o scaffolding**;
- le **fasi di lavorazione** a monte della commessa **non esistono** in alcun layer:
  per esse predisponiamo solo punti d'innesto non invasivi (§6).

---

## 2. Stato attuale (cosa è implementato)

### 2.1 Modello e macchina a stati

Lo stato della testata **non è una colonna testuale**: vive solo nella FK
`stato_commessa_id` verso `vendite.stati_commessa` (seed:
`BOZZA(1) → APERTA(2) → IN_ESECUZIONE(3) → PRONTA_FATTURAZIONE(4, emittibile) →
CHIUSA(5, terminale)`, più `ANNULLATA(6, terminale)`), con flag governance
`modificabile` / `emittibile` / `chiude_commessa`
([stati_commessa.csv](../../../../db/changelog/migrations_v2/80_data/sql/vendite/stati_commessa.csv)).

A giugno 2026 è stata aggiunta una **macchina di transizioni data-driven**
(IMPLEMENTATA 2026-06-08):
- matrice `vendite.transizioni_stati_commessa` (11 righe, tutte `meta.manuale=false`);
- trigger `trgfn_commesse_guard_transizione` (BEFORE UPDATE OF `stato_commessa_id`)
  che valida ogni UPDATE contro la matrice — errori
  `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` (472) e, per `→PRONTA_FATTURAZIONE`,
  precondizione "≥1 riga APPROVATA+NON_EMESSA" → `E_COMMESSA_NESSUNA_RIGA_APPROVATA` (473);
- entrypoint sottile `fn_cambia_stato_commessa` (risolve codice→id, fa l'UPDATE,
  **non** ri-valida: delega tutto al trigger).

Le **righe** (`commesse_attivita`) hanno **due assi di stato indipendenti**:
`stato_approvazione` (BOZZA→APPROVATA, RIFIUTATA prevista ma mai scritta) e
`stato_emissione` (NON_EMESSA→EMESSA, ANNULLATA prevista ma mai scritta).

### 2.2 Ingestione (push multi-sorgente)

Orchestratore stateless con 5 handler (preventivo/ordine/contratto/DDT/consumi):
- risoluzione commessa **dimensionale** (BA + utility + tipo + policy +
  fatturazione_immediata + emittente + competenza): documenti diversi dello stesso
  perimetro **convergono nella stessa commessa** (aggregazione voluta);
- link sorgente con **auto-ruolo ROOT/COLLEGATO** deciso a DB (2026-06-09); il
  vecchio modello mono-ROOT è superato;
- idempotenza a 2 livelli: link sorgente su `(sorgente_tipo, uid)`, righe via UPSERT
  `ON CONFLICT (commessa_id, segment_key)` (il `segment_key` incorpora il `sorgente_uid`);
- due semantiche transazionali: batch best-effort per-commessa
  (`pr_run_commesse_push`) vs push singolo all-or-nothing (`pr_run_commesse_push_one`,
  `E_COMMESSA_PUSH_PARZIALE_VIETATO`).

### 2.3 Il ponte di emittibilità (ciò che ha riattivato la catena)

Prima del 2026-06-08 la commessa nasceva BOZZA e **nulla** la portava a PRONTA: il
ramo commessa→fattura era **dormiente**. Oggi `_rendi_commessa_emittibile`
([commesse_service.py:73-104](../../../../backend/apps/vendite/services/commesse_service.py#L73))
dopo ogni push riuscito: `fn_approva_commessa_attivita` (BOZZA→APPROVATA) +
`fn_cambia_stato_commessa(PRONTA_FATTURAZIONE)` (skip idempotente se già pronta per
le commesse multi-sorgente).

**Filosofia "documento sorgente = autorizzazione"**: le viste `fn_list_*_da_pushare`
ammettono solo documenti già autorizzati (preventivo ACCETTATO, ordine CONFERMATO,
contratto ATTIVO), quindi il push stesso è l'autorizzazione e le righe nascono
auto-approvabili senza intervento manuale.

### 2.4 La pipeline lotto → fatture

- pull `attivita_fatturabili` da commesse emittibili (step 0,
  `fn_list_commesse_emittibili` + `fn_emit_attivita_fatturabili_da_commessa`, solo
  righe APPROVATA, idempotente, blocca su AF già fatturata);
- select+lock attività (`fn_select_attivita_fatturabili`, FOR UPDATE SKIP LOCKED);
- generazione testate/righe fattura + numerazione (`FattureRigheService`, batch CTE,
  mark `fatturato=TRUE` atomico);
- orchestrazione **in Python** (`LottoPipelineRunner` / `PipelineStepExecutor`): le fn
  SQL `fn_execute_pipeline_step` / `fn_group_attivita_fatturabili` sono **deprecate**;
- tracing completo (`fatturazione_lotti_task_runs`, `fatture_log`, `event_log`).

### 2.5 Catena verso la fatturazione — stato per step

| Step | Stato |
|---|---|
| Push multi-sorgente | 🟡 PARZIALE (BoM/consumi/snapshot — §4) |
| Risoluzione/creazione commessa + link sorgente | 🟢 IMPLEMENTATO |
| Materializzazione righe `commesse_attivita` | 🟢 IMPLEMENTATO |
| Approvazione righe (BOZZA→APPROVATA) | 🟢 IMPLEMENTATO (solo via ponte push) |
| Emittibilità testata (→PRONTA_FATTURAZIONE) | 🟢 IMPLEMENTATO |
| Pull → `attivita_fatturabili` | 🟢 IMPLEMENTATO |
| Lotto: select+lock | 🟢 IMPLEMENTATO |
| Generazione fatture + numerazione | 🟢 IMPLEMENTATO |
| Invio SDI | 🔴 solo scaffolding (prepare payload, nessun invio) |

---

## 3. Coerenza con la documentazione

Tutte e tre le fonti documentali sono **parzialmente allineate** ma **antecedenti a
giugno 2026** (transizioni, multi-sorgente, ponte emittibilità).

- **Guida [gestione-commesse.md](/guide/gestione-commesse)** (23 apr): manca del tutto
  la macchina di transizioni; parla di ruolo "CONTRIBUENTE" (inesistente: il modello
  reale è ROOT/COLLEGATO); descrive nomi di step pipeline inesistenti
  (`PULL_COMMESSA/RACCOLTA_INPUT/NORMALIZZAZIONE` vs reale
  `pull_attivita_da_commessa`); descrive `fn_resolve_commessa_prezzi` come
  "riallinea righe commessa" mentre è una **diagnostica su lotto**; condiziona
  l'espansione BoM a `esposto_in_fattura` mentre il padre è **sempre** espanso (il
  flag è solo di presentazione).
- **gestione-commesse-v2.md** (feb): le FASI 1-7 backend risultano in larga parte
  implementate, ma il doc descrive ancora la **colonna `stato` testuale** (rimossa),
  ignora la macchina transizioni (aggiunta dopo), e la **FASE 4.5 "rettifiche listino"
  NON è implementata** (i file `commesse_rettifiche_*.py` non esistono); il modello
  ricco AUTO/REALE + policy MISTA/conguaglio + lotto giornaliero è **scaffolding non
  attivato**.
- **WIP fatturazione**: il valle-commessa è realizzato; restano **intenzione** invio
  SDI reale, note di credito, scadenzario, multi-esercizio, dashboard, alerting,
  correlation_id, scheduler.

> L'allineamento delle doc è una raccomandazione **a bassa priorità**, da fare **dopo**
> i fix BE (per non documentare codice stale).

---

## 4. Gap per "predisporre le commesse alla fatturazione"

### 4.1 ✅ RISOLTO (2026-06-15) — Bug bloccante azioni prezzo N5/N7 (codice stale)

> **Stato: FATTO.** Fix applicato e validato (74 + 66 test verdi). Reso data-driven
> sul flag `stati_commessa.modificabile`:
> - `get_attivita_pricing` ([commesse_repository.py](../../../../backend/apps/vendite/db/commesse_repository.py)):
>   rimosso `c.stato` (inesistente), aggiunto `JOIN vendite.stati_commessa` che espone
>   `codice_interno AS commessa_stato` + `modificabile AS commessa_modificabile`;
> - rimossa la costante hardcoded `_STATI_COMMESSA_MODIFICABILI={"LIBERO","CONFERMATO"}`;
>   `_assert_commessa_modificabile` ([commesse_service.py](../../../../backend/apps/vendite/services/commesse_service.py))
>   ora controlla il flag booleano `commessa_modificabile`;
> - test aggiornati al modello reale (`BOZZA`/`commessa_modificabile`).

Diagnosi originale (per memoria). Verificato sui sorgenti. Le azioni prezzo sulle
attività commessa (riallinea / variazione eccezionale / sblocca) erano rotte contro
lo schema reale:

- [commesse_service.py:386](../../../../backend/apps/vendite/services/commesse_service.py#L386):
  `_STATI_COMMESSA_MODIFICABILI = frozenset({"LIBERO", "CONFERMATO"})` — stati che
  **non esistono** nel seed (`BOZZA/APERTA/IN_ESECUZIONE/PRONTA_FATTURAZIONE/CHIUSA/
  ANNULLATA`);
- [commesse_repository.py:1011](../../../../backend/apps/vendite/db/commesse_repository.py#L1011):
  `c.stato AS commessa_stato` su `vendite.commesse`, **colonna inesistente** (c'è solo
  `stato_commessa_id` FK).

→ I 3 endpoint prezzo ([views.py:595-655](../../../../backend/apps/vendite/api/views.py#L595))
**falliscono a runtime**. È codice pre-refactor mai riallineato alla macchina stati.
**Da bonificare per primo.**

**Fix proposto** (self-contained BE): leggere il flag `modificabile` direttamente da
`stati_commessa` invece di hardcodare un set di codici, e in `get_attivita_pricing`
sostituire `c.stato` con un JOIN su `stati_commessa` per derivare il codice
(coerente con `get_commessa_stato_codice`,
[commesse_repository.py:580-596](../../../../backend/apps/vendite/db/commesse_repository.py#L580)).

### 4.2 ⏸️ Frontend commesse assente — rinvio deliberato (decisione 2026-06-15)

`frontend/src/vendite` contiene solo offerte/ordini/preventivi (+ listini/contratti/
promo): **nessuna cartella commesse, nessuna route, nessun menu, nessun drawer**.
Esiste un set completo di endpoint BE (push run/log, stato, lista attività, 3 azioni
prezzo) **senza alcun consumer FE**. Unico aggancio: i pannelli di push da preventivo
(`PreventiviSmistamentoPanel`) e ordine (`OrdiniDrawer` "Invia a commessa"), che però
mostrano solo un toast con `push_log_id`, **senza link alla commessa risultante**.

> **Aggiornamento 2026-06-15**: l'assenza di FE commesse è ora un **rinvio
> deliberato** (§7.1 punto 4, §7.5), non un gap da chiudere subito. La priorità è
> l'automazione della fatturazione (§7.4). Eventuale superficie minima futura: un
> **monitor lotti/anomalie** a supporto del driver, non una gestione commessa piena.

### 4.3 🟡 Altri gap

| # | Gap | Area | Impatto |
|---|---|---|---|
| 1 | Nessuno scheduler/cron + pipeline "uno step per run" (`steps[:1]`) | TRASVERSALE | La fatturazione non è autonoma: serve un driver che concateni gli step (vedi §7) |
| 2 | ✅ **FATTO END-TO-END (2026-06-16)** — Snapshot pricing v5: il push popola gli 8 campi audit su `commesse_attivita` (`BaseSourceHandler._resolve_pricing_audit` via `PricingService`, senza sovrascrivere `prezzo_snapshot`; best-effort, cache per-run, whitelist `origine_prezzo` contro il CHECK, origine da meta prevale per i componenti). La **pull** `fn_emit_attivita_fatturabili_da_commessa` ora li **propaga 1:1** ad `attivita_fatturabili` (changeset DB `20260616-01`, brief [work-done/brief-db-propaga-snapshot-pricing-pull-commessa-af.md](brief-db-propaga-snapshot-pricing-pull-commessa-af.md)). | BE✅ + DB✅ | Audit prezzo completo: push → commessa → emissione |
| 3 | ✅ **COMPOSITI FATTI (2026-06-15)** — il fan-out BoM usa ora il **modello unico** `*_righe_componenti` per **tutti** i documenti: estratto `BaseSourceHandler._componenti_repo_factory` (staticmethod) → ordini/contratti/DDT leggono i componenti negoziati come preventivi (no DB, le tabelle + mixin esistevano già; nuovo `DdtRepository` minimale). 🛑 **Consumi utility (gas/energia/acqua/…) — RIMANDATO, NON si fa ora (decisione Tid 2026-06-16)**: `attivita_consumi` è un totale piatto senza `*_righe_componenti`; la decomposizione tariffaria (energia/trasporto/oneri/quota fissa/accise) è un **modello DB dedicato** da progettare quando la fatturazione utility per-voce diventerà priorità. Oggi un consumo entra in commessa come **riga singola** (`_fetch_componenti` resta stub documentato, nessun fan-out). | BE✅ compositi / 🛑 consumi rimandato | Compositi ok per ogni sorgente; decomposizione utility fuori scope ora |
| 4 | ✅ **FATTO END-TO-END (2026-06-16)** — Governance ciclo di vita commessa. **DB**: `script.fn_available_actions_commessa` + seed transizioni `manuale=true` (chiudi/riapri/annulla, con UI hints) — brief [work-done/brief-db-fn-available-actions-commessa.md](brief-db-fn-available-actions-commessa.md). **BE**: `CommesseRepository.get_capabilities`, `capabilities` in `ApiCommessaStato` GET, servizio `cambia_stato_commessa` con difesa applicativa (azione ∈ `available_actions`), endpoint `POST /commesse/<id>/stato/`, codice `E_COMMESSA_AZIONE_NON_AMMESSA` (409); 5 test (suite 958 verde). | DB✅ + BE✅ | CHIUSA/riapertura/ANNULLATA ora governabili da API |
| 5 | ✅ **RISOLTO (2026-06-15)** — `fn_get_commessa_stato` esponeva flag governance + molti contatori, ma il repo BE ne leggeva solo 3 | BE | Ora `ApiCommessaStato` propaga stato + flag + tutti i contatori (74 test verdi) |
| 6 | ✅ **RISOLTO (2026-06-16)** — Discrepanza nome codice errore: il nome reale è `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` (472); il placeholder `E_COMMESSA_TRANSIZIONE_NON_AMMESSA` **non esiste** in codice/DB/test (compariva solo nel brief storico `work-done/brief-db-commesse-transizioni-stati.md`, ora annotato). Nessun fix codice necessario. | DB/doc | Allineato |

---

## 5. Predisposizione alla fatturazione — sintesi

Decisione 2026-06-15 (vedi §7): la priorità **non** è una UI di gestione commesse, ma
**automatizzare** il movimento commessa → fatturazione con un **processo orchestrato**
(corsia immediata + batch differito per competenza), non con trigger. Prerequisiti:
(a) ✅ bug §4.1 bonificato; (b) ✅ flag/contatori propagati in `ApiCommessaStato`;
(c) **driver che concatena gli step del lotto** fino alle fatture numerate + scelta
dello scheduler (§7.4). Snapshot pricing, BoM/consumi e azioni di stato sono
miglioramenti incrementali successivi. La UI commesse è **rinviata** (porta aperta, §7.5).

---

## 6. Fasi di lavorazione — solo predisposizioni (scaffolding non invasivo)

Oggi **non esiste** alcun concetto di fase di lavorazione / produzione / work-order in
DB, BE o FE (grep `fasi_lavorazione/work_order/ordine_di_lavoro/produzione` = 0).
Coerentemente con la scelta di lasciare **solo predisposizioni** (sviluppo concentrico,
no YAGNI ma neppure over-build), si innestano **punti di estensione** senza alcuna
logica di produzione:

1. ✅ **FATTO (2026-06-15) — Hook no-op nel `BaseSourceHandler`** tra fetch righe e
   `get_or_create_commessa`: `_pre_commessa_hook(row) → row` (default identity, chiamato
   per riga dentro il savepoint di `_process_rows`, prima di espansione/creazione). È il
   punto naturale dove una fase di lavorazione precederebbe la creazione commessa; oggi
   nessuna logica di produzione. Override per sottoclasse, contratto puro
   `PushableRow → PushableRow`.
2. **Campo `meta` jsonb già esistente** su `commesse_attivita` come contenitore per un
   futuro `fase_lavorazione_id` / `work_order_id`: niente nuova tabella né colonna
   NOT NULL ora (se serve esplicitezza, al massimo una colonna `fase_lavorazione_id
   bigint NULL` **senza FK enforced** come minimo scaffolding DDL — via brief DB).
3. **`handler_registry` della pipeline** ([pipeline_step_executor.py](../../../../backend/apps/vendite/services/pipeline_step_executor.py))
   già dispatch per nome-task risolto da config DB: una fase futura si innesterebbe
   come task aggiuntivo — basta **non seedarlo** ora e documentare che il registry è il
   punto di estensione (stesso pattern dello step prezzi mai wired).
4. **Matrice stati già data-driven**: un eventuale stato pre-commessa si aggiunge come
   riga futura senza toccare il guard.

> Prima di scrivere qualunque astrazione (hook/colonna), dichiarare l'estrazione a Tid
> e attendere conferma (regola del 2 / mini-protocollo).

---

## 7. Fatturazione automatica — indirizzo deciso (2026-06-15)

### 7.1 Decisioni prese

A valle del confronto, l'orientamento è stabilito:

1. **Automatizzare il ponte commessa → fatturazione via processo orchestrato/
   schedulato, NON via trigger DB.** I trigger restano per guard, validazioni e
   normalizzazioni; il *movimento* commessa→AF→lotto→fattura vive in
   un'orchestrazione applicativa.
2. **`commesse_attivita` e `attivita_fatturabili` restano due livelli distinti**
   (accumulo/lavorazione vs emissione/immutabile): si automatizza il **ponte**, non
   si **fondono** i livelli. La loro somiglianza di forma giustifica l'automazione a
   basso attrito, non l'unificazione (vedi §7.3).
3. **`fatturazione_immediata`** (sulla testata commessa, ed elemento della chiave di
   deduplicazione in `fn_get_or_create_commessa`: immediate e differite non si
   mescolano mai nella stessa commessa) è il **discriminante** tra corsia veloce e
   batch differito.
4. **UI di gestione commesse rinviata** (porta aperta): la UI commessa è preziosa nei
   sistemi con **produzione** (la commessa innesca lavorazioni, avanzamenti, reparti),
   caso oggi assente. Oggi la commessa è un livello di **aggregazione contabile**
   headless verso la fatturazione: una UI dedicata aggiungerebbe poco *ora*. La porta
   resta aperta senza costo, perché il modello è già predisposto (vedi §7.5).

### 7.2 Perché processo e non trigger

| Criterio | Trigger DB | Processo orchestrato (scelto) |
|---|---|---|
| Competenza/policy-aware | Emette "appena approvato", a prescindere dal mese di competenza | Emette solo ciò che è dovuto (immediata subito, differita a competenza) |
| Criticità (soldi) | Invisibile, non simulabile, difficile da mettere in hold | dry-run, `task_runs`, `event_log`, hold su anomalie |
| Accoppiamento | Ri-accoppia l'emissione AF alla transazione di push (lock, peso) | Mantiene push (veloce, per-sorgente) e pull (batch) disaccoppiati |
| Reversibilità | Sposta righe rilevanti prima di poter controllare | Gate controllato prima di numerazione/invio |

→ I trigger restano per ciò che fanno bene (es. `trgfn_attivita_fatturabili_guard_commessa`
che impone "nessuna AF senza commessa"); l'**orchestrazione** guida il movimento.

### 7.3 Commessa ↔ attività da fatturare: automatizzare il ponte, non fondere

Le due entità **sembrano** simili (entrambe righe fatturabili con articolo, quantità,
prezzo snapshot, competenza), ma hanno **ruoli di ciclo di vita diversi**:

- `commesse_attivita` = **accumulo/lavorazione**: modificabile finché la commessa è
  `modificabile`, upsert idempotente per `segment_key`, prezzo riallineabile (N5/N7),
  **aggrega più sorgenti** in una commessa, **continua ad accumulare** nel tempo (es.
  canone mensile = nuove righe ogni mese sulla stessa commessa);
- `attivita_fatturabili` = **emissione/coda**: snapshot **congelato** al pull, lock per
  lotto (`lock_batch_id`, FOR UPDATE SKIP LOCKED), una volta `fatturato` **immutabile**
  (guard DB).

Fondere i due livelli perderebbe: la **finestra di aggiustamento** prima di fatturare,
l'**aggregazione multi-sorgente**, la **ri-emissione per competenza** delle forniture
ricorrenti e il **confine di audit/immutabilità**. Inoltre il guard
`trgfn_attivita_fatturabili_guard_commessa` rende `commessa → AF` **l'unica porta**
(nessun bypass): automatizzarla è la mossa naturale, non c'è percorso alternativo.

### 7.4 Disegno dell'orchestrazione

**Due corsie, stesso motore:**

- **Corsia IMMEDIATA** (`fatturazione_immediata = true`): cadenza ravvicinata (es.
  giornaliera) oppure on-demand. Le commesse immediate (già segregate dal dedup key) →
  pull AF → lotto → fatture, appena le righe sono approvate (il push le porta già a
  PRONTA_FATTURAZIONE).
- **Corsia DIFFERITA** (`fatturazione_immediata = false`): batch **mensile guidato
  dalla competenza** (`competenza_mese`). Emette solo le AF la cui competenza è dovuta;
  il resto resta ad accumulare sulla commessa.

**Passi del driver (riusano i mattoni già esistenti):**

1. **Discovery** — `fn_list_commesse_emittibili` (già presente) filtrata per
   competenza/perimetro (BA/utility/emittente).
2. **Pull** — `fn_emit_attivita_fatturabili_da_commessa` (già presente: idempotente,
   `only_approved`, blocca su AF già fatturata, propaga snapshot pricing).
3. **Concatenazione step lotto** — oggi la pipeline esegue `steps[:1]` (uno step per
   run): serve un **driver che porti il lotto dallo step 0 alle fatture numerate**
   (loop guidato o N invocazioni orchestrate). È il vero pezzo mancante.
4. **Gate sulle segnalazioni critical** (`blocks_next_step`) — se una fattura ha
   un'anomalia critica, il driver **si ferma su quel lotto** e segnala, senza
   proseguire a numerazione/invio.
5. **Idempotenza & concorrenza** — `fn_select_attivita_fatturabili` (FOR UPDATE SKIP
   LOCKED) + guard `fatturato` rendono run ripetuti/concorrenti sicuri.
6. **Osservabilità** — `fatturazione_lotti_task_runs`, `event_log`, `commesse_push_log`
   già presenti: il driver li popola (no nuova infrastruttura di logging).

**Dove vive lo scheduler — DECISO (2026-06-15)**: **timer di sistema (systemd/cron)**
che lanciano un **management command** applicativo. **pgAgent è riservato alla sola
manutenzione DB**, non alle attività gestionali. Deve restare la possibilità che un
**operatore avvii anche da interfaccia** (endpoint on-demand). La **corsia immediata è
near-real-time** (cadenza ravvicinata), la differita è batch mensile su competenza.
**Principio**: lo scheduler **innesca** il processo applicativo (che possiede la logica
competenza/policy + osservabilità), **non** esegue logica SQL monolitica. Push e pull
restano in Python orchestrato.

> **Nota dipendenze**: "near-real-time" via **timer frequente** (es. ogni 1-2 min) **non
> richiede nuove dipendenze**. Una coda asincrona (es. Celery) darebbe latenza minore ma
> **aggiungerebbe una dipendenza** in `requirements.txt` → richiede OK esplicito di Tid
> (memoria `feedback_autorizzazioni_esplicite`). Default proposto: timer frequente.

**Cosa resta manuale (controllo):**

- avvio on-demand di un lotto (già via API `pipeline/run`, `commesse/push/run`);
- hold/sblocco su anomalie critical;
- riallineo/variazione prezzo (N5/N7) **prima** dell'emissione.

**Confine di immutabilità:** una volta `fatturato`, la AF è immutabile (guard). Il
driver non torna indietro: le correzioni post-fattura sono NDC/NDD (fuori scope ora).

### 7.5 La "porta aperta" per il flusso produttivo (perché rinviare la UI non chiude nulla)

Predisposizioni **già nel modello**, nessuna da costruire ora: `tipo_commessa`
(AUTO/REALE), `policy_fatturazione`, `priorita_operativa`, campo `meta` sulla testata;
matrice transizioni data-driven (basta aggiungere righe); hook `_pre_commessa_hook` (§6).
Quando servirà un flusso REALE con gate operativi/produzione, l'innesto è pronto.

---

## 8. Roadmap proposta (prioritizzata)

1. **✅ FATTO (2026-06-15) — Fix bug pricing-ops N5/N7** (§4.1): reso data-driven sul
   flag `stati_commessa.modificabile`; 74 + 66 test verdi.
2. **✅ FATTO (2026-06-15) — Propagazione flag/contatori in `ApiCommessaStato`** (§4.3 #5):
   stato + governance + tutti i contatori esposti dall'endpoint; 74 test verdi.
3. **🟠 ALTA — Driver orchestrazione fatturazione** (§7.4, §10): avanzamento multi-step,
   driver fino a fattura, corsie immediata (near-real-time) e differita via **systemd
   timer/cron con management command** (no pgAgent), più endpoint on-demand. *Decisioni
   in §10.6.* Stato fasi (§10.4): **F1 ✅**, **F2 ✅**, **F3 ✅**, **F4 documentata**
   (ricetta timer + caveat RLS; attivazione = ops) (2026-06-15); **F5 ✅ soddisfatta dal
   riuso** (2026-06-15): osservabilità per-lotto già esposta (segnalazioni summary,
   task-runs, lista lotti, fatture lotto) + hold/sblocco (reset-draft) + report aggregato
   del batch; **driver committato+pushato** (`c4a9797f7`). ✅ **Contesto di SISTEMA per il
   batch (RLS Path A) COMPLETATO** (DB+BE, §9) e ✅ **persistenza esito run** in
   `maintenance.job_run_log` via `registered_job` (§10.4 F5) — chiusi entrambi i residui.
   Resta solo **ops** (password env + unit systemd) e lo **smoke live** a RLS *enforced*.
   **Monitor lotti FE rinviato** (§4.2).
4. **🟡 MEDIA — Popolare snapshot pricing v5 nel push** (§4.3 #2): ✅ **FATTO END-TO-END
   (2026-06-16)** — BE su `commesse_attivita` via `PricingService` + propagazione DB nella
   pull (changeset `20260616-01`, brief in
   [work-done](brief-db-propaga-snapshot-pricing-pull-commessa-af.md)).
5. **🟡 MEDIA — Completare BoM/fan-out per sorgenti ≠ preventivo** (§4.3 #3): ✅ **FATTO
   (2026-06-15)** per i **compositi** (ordini/contratti/DDT) riusando il modello unico
   `*_righe_componenti` — **solo BE, nessun brief DB** (le tabelle/mixin esistevano già).
   🛑 **Consumi utility (gas/energia/acqua/…): RIMANDATO, NON si fa ora** (decisione Tid
   2026-06-16). La decomposizione tariffaria è un modello DB dedicato, da avviare solo
   quando la fatturazione utility per-voce sarà priorità; oggi il consumo resta riga
   singola.
6. **🟡 MEDIA — Predisposizioni fasi di lavorazione** (§6): ✅ **FATTO (2026-06-15)** —
   hook BE no-op `BaseSourceHandler._pre_commessa_hook(row)→row` (identity) come punto
   d'innesto. Niente colonna DB / niente `meta` dedicato ora (decisione 2026-06-15).
7. **🟢 BASSA — `fn_available_actions_commessa` + azioni di stato utente** (§4.3 #4):
   ✅ **FATTO END-TO-END (2026-06-16)** — DB (fn capability + seed transizioni manuali) +
   BE (`get_capabilities`, `capabilities` in `ApiCommessaStato`, servizio
   `cambia_stato_commessa` con difesa applicativa, `POST /commesse/<id>/stato/`,
   `E_COMMESSA_AZIONE_NON_AMMESSA`). Brief in
   [work-done](brief-db-fn-available-actions-commessa.md).
8. **🟢 BASSA — Allineare la documentazione** (§3): ✅ **FATTO (2026-06-16)** — guida
   [gestione-commesse.md](/guide/gestione-commesse) allineata (transizioni, ROOT/COLLEGATO,
   step pipeline reali, BoM snapshot, audit end-to-end); banner storico su
   [gestione-commesse-v2.md](gestione-commesse-v2.md); naming codice errore (§4.3 #6) corretto.
9. **⏸️ RINVIATO (porta aperta) — UI gestione commesse** (§4.2, §7.4-7.5): non ora;
   utile per flussi con produzione. Eventuale **monitor lotti/anomalie** minimo potrà
   servire al driver §7.4 per hold/sblocco delle segnalazioni critical.

---

## 9. Azioni DB da passare al team (se confermate)

Brief al team DB (mai eseguite dal BE agent). Stato driver fatturazione:

- ✅ **FATTO** — seed pipeline pull commessa→AF + corsia GIORNALIERO + `chiude_lotto`:
  [brief-db-pipeline-pull-commessa-seed.md](brief-db-pipeline-pull-commessa-seed.md).
- ✅ **FATTO** — filtro `fatturazione_immediata` nella discovery emittibili
  (prerequisito Fase 3, §10.4):
  [brief-db-emittibili-filtro-fatturazione-immediata.md](brief-db-emittibili-filtro-fatturazione-immediata.md).

Altri (solo se le relative voci di roadmap vengono approvate):

- ✅ **PATH A — DB+BE COMPLETATO (2026-06-17)** — contesto di **sistema** per il batch
  fatturazione (cron) via **ruolo DB dedicato** `zeroerp_batch_fatturazione` (BYPASSRLS,
  SELECT ampio + DML scoped al perimetro fatturazione) + alias Django `system_fatturazione`.
  Brief [brief-db-contesto-sistema-batch-fatturazione-rls.md](brief-db-contesto-sistema-batch-fatturazione-rls.md).
  **⚠️ Opzione B (sentinel `app.ruolo_applicativo='SISTEMA'` + policy `_sistema`) REVISIONATA
  e ritirata**: non era break-proof (una policy per ogni tabella RLS futura). **DB (D1–D5)**:
  ruolo + provisioning + check postura + pgTAP `ok 1..11` + doc (commit `cc2bf3831`). **BE
  (D6–D9)**: alias + gateway `system_process_context` (routing A: redirect connessione
  `default`, repo invariati, fail-loud se non-BYPASSRLS) + guard runtime fail-open
  (`E_DB_ROLE_UNSAFE`) + check statico whitelist + ritiro Opzione B; suite verde (1347 test).
  **Residuo ops** (prima dell'attivazione RLS): password reale del ruolo in
  `DB_SYSTEM_FATTURAZIONE_PASSWORD` + smoke live "≥2 emittenti con RLS attiva".
- (eventuale) colonna `fase_lavorazione_id bigint NULL` senza FK su `commesse_attivita`
  — solo se si sceglie lo scaffolding esplicito invece del `meta` jsonb (§6.2);
- fn di lookup componenti per `HandlerConsumi` (§4.3 #3);
- verifica/allineamento nome codice errore transizioni (§4.3 #6).

I fix §4.1 (pricing-ops) e la propagazione contatori sono **solo BE**, nessuna azione DB.

---

## 10. Piano di sviluppo — Driver di orchestrazione fatturazione

> Aggiunto 2026-06-15 dopo approfondimento sul layer di esecuzione pipeline/lotto
> ([pipeline_runner.py](../../../../backend/apps/vendite/services/pipeline_runner.py),
> [pipeline_step_executor.py](../../../../backend/apps/vendite/services/pipeline_step_executor.py),
> [pipeline_repository.py](../../../../backend/apps/vendite/db/pipeline_repository.py)).

### 10.1 Obiettivo

Portare un lotto **dallo step 0 fino alle fatture numerate** in modo automatico
(corsia immediata + batch differito), riusando i mattoni esistenti, **senza trigger**
per il movimento (decisione §7.1) e **senza** una UI commesse (§7.5).

### 10.2 Approfondimento chiave (vincolo di partenza)

`run_pipeline` ([pipeline_runner.py:276](../../../../backend/apps/vendite/services/pipeline_runner.py#L276))
oggi:
- risolve/crea il lotto (`get_or_create_lotto`) ed esegue **un solo step**: nel
  percorso di **successo** prende sempre `steps[:1]` = il **primo** step del catalogo
  (riga 344). `list_pipeline_steps` ritorna l'**intero** catalogo ordinato, non filtrato
  sullo stato corrente del lotto;
- il **resume dallo stato corrente** (`_resolve_steps_for_rerun` → `steps[current_index:]`)
  scatta **solo** quando `is_massivo_error_rerun` (lotto in errore).

**Conseguenza**: un driver che chiama `run_pipeline` in loop **ri-eseguirebbe sempre lo
step 0** nel percorso di successo. Quindi il primo lavoro non è il loop, ma **abilitare
l'avanzamento multi-step in successo** (riprendere dallo step successivo a quello già
eseguito sul lotto). Il gate critical (`blocks_next_step`, righe 346-367) e la chiusura
da flag `chiude_lotto` (`_process_close_lotto_by_flag`, righe 233-252) sono già al posto
giusto e vanno riusati come, rispettivamente, condizione di stop e segnale di fine.

Catalogo task pipeline già registrati (handler_registry, executor righe 39-50):
`pull_attivita_da_commessa` → `select_attivita` → `generate_fatture_righe` →
`ricalcola_iva_lotto` → `genera_fondi`/`applica_fondi` → `prepare_sdi_payload_lotto` →
`numera_fatture` → `close_lotto` (l'ordine effettivo è dato dal seed
`fn_list_fatturazione_pipeline_steps`).

### 10.3 Scelte architetturali

- **Processo applicativo, non trigger** (§7.1). Lo scheduler **innesca** il processo.
- **Avanzamento guidato dallo stato del lotto**: la fonte di verità del "prossimo step"
  è `lotto.stato_doc_fiscale_id` confrontato col catalogo ordinato (estendere la logica
  di resume oggi limitata al rerun-errore).
- **Stop espliciti del loop**: (a) step con `chiude_lotto` eseguito → lotto chiuso/
  COMPLETATO; (b) nessuno step successivo; (c) `blocks_next_step` attivo → stop con esito
  "bloccato per criticità" (non errore); (d) errore step → stop con lotto ERRORE.
- **Idempotenza/concorrenza**: già garantite a valle (`fn_select_attivita_fatturabili`
  FOR UPDATE SKIP LOCKED, guard `fatturato`, pull idempotente). Il driver aggiunge un
  guard "lotto IN_ESECUZIONE" (già presente in `run_pipeline`).
- **Due corsie**: `fatturazione_immediata` (già nel dedup key delle commesse) →
  cadenza ravvicinata; differita → batch mensile per `competenza_mese`.

### 10.4 Fasi

**Fase 0 — ✅ ESEGUITA (2026-06-15): verifica seed pipeline.** Esito sui seed
([fatturazione_pipeline.csv](../../../../db/changelog/migrations_v2/80_data/sql/vendite/fatturazione_pipeline.csv),
`fatturazione_pipeline_task_policy.csv`, `config/stati_doc_fiscale.csv`) — **emergono
3 gap di seed che bloccano il driver** (richiedono brief DB, §10.5):

1. 🔴 **Lo step `pull_attivita_da_commessa` NON è seedato in alcuna pipeline.** Il
   handler esiste ([pipeline_step_executor.py:654](../../../../backend/apps/vendite/services/pipeline_step_executor.py#L654),
   mapping `pipeline_repository.py:126` → `fn_emit_attivita_fatturabili_da_commessa`),
   ma nessuno step `fatturazione_pipeline` lo invoca: la pipeline MASSIVO/DRAFT fa
   `select_attivita` + `generate_fatture_righe`, **assumendo le AF già esistenti**.
   `select_attivita` blocca AF esistenti, **non** le crea dalla commessa. → Oggi il
   ponte commessa → `attivita_fatturabili` **non è eseguito da nessun flusso** (solo via
   test/chiamata diretta). È il gap più grave: la catena è interrotta a questa giunzione.
2. 🟠 **Corsia GIORNALIERO incompleta.** Il seed ha `GIORNALIERO` per EMESSA (processi
   vuoti), DEFINITIVA (numera) e INVIATA (sdi), ma **manca lo step DRAFT** (select +
   generate, e il pull): la corsia near-real-time non ha il primo step.
3. 🟡 **Nessuno `stato_doc_fiscale` ha `chiude_lotto = true`** (DRAFT/EMESSA/DEFINITIVA/
   INVIATA tutti `f`): il `_process_close_lotto_by_flag` è inerte. Lo stop "fine catena"
   del driver non può basarsi sul flag → o si setta `chiude_lotto` sullo stato finale
   (INVIATA o DEFINITIVA), o lo stop si basa su "ultimo step del catalogo raggiunto".

Pipeline reali seedate (MASSIVO): DRAFT(select+generate) → EMESSA(fondi+iva) →
DEFINITIVA(numera) → INVIATA(prepare_sdi). Catalogo ordinato per `stato_doc_fiscale.ordine`.

**Fase 1 — ✅ FATTA (2026-06-15): avanzamento multi-step nel percorso di successo.**
- `_resolve_steps_for_rerun` → generalizzata in **`_resolve_steps_for_run`**
  ([pipeline_runner.py](../../../../backend/apps/vendite/services/pipeline_runner.py)):
  rerun-errore invariato (`steps[current_index:]`); su **lotto esistente in successo**
  avanza allo step **successivo** (`steps[current_index+1:]`); primo run / lotto appena
  creato (lotto_id non passato) → primo step. Discriminante: `is_existing_lotto_request`
  (l'errore-rerun resta su `job_stato==ERRORE`, indipendente).
- Test: **25 verdi** (`test_pipeline_runner` + `test_pipeline_service`), inclusi i 2
  nuovi (`..._success_advances_to_next_step`, `..._success_at_last_step_is_noop`) e tutti
  gli esistenti su rerun-errore/successo preservati.

**Fase 2 — ✅ FATTA (2026-06-15): driver "run fino a fine" + esito strutturato + endpoint.**
- `LottoPipelineRunner.run_lotto_until_done(params)`
  ([pipeline_runner.py](../../../../backend/apps/vendite/services/pipeline_runner.py)):
  chiama `run_pipeline` (1 step/chiamata) finché — step di **chiusura** (`chiude_lotto`,
  cioè DEFINITIVA per scelta D3, **prima** di SDI), **nessun avanzamento** residuo,
  **blocco critical** (`E_PIPELINE_LOTTO_CRITICAL`) o **errore**. Guard anti-loop
  (`_MAX_STEP_ITERATIONS=50`). **Non** chiude il lotto direttamente (lo fa
  `_process_close_lotto_by_flag` dentro `run_pipeline`) → niente doppia chiusura.
  Esito: `{lotto_id, stato_lotto, stato_doc_fiscale_id, step_eseguiti, motivo_stop}`
  (`COMPLETATO` / `BLOCCATO_CRITICITA` / `ERRORE` / `GUARD_MAX_ITER`); non solleva sui
  motivi di stop noti (solo errore al primo run su lotto nuovo propaga).
- Facade [pipeline_service.py](../../../../backend/apps/vendite/services/pipeline_service.py)
  `run_lotto_pipeline_until_done(...)` + estrazione `_validate_pipeline_lookups`/
  `_build_pipeline_params` (DRY con `run_lotto_pipeline`).
- Endpoint on-demand **`POST /api/v1/vendite/pipeline/run-until-done/`**
  (`ApiRunLottoPipelineUntilDone`), idempotency-key + `dry_run`, esito strutturato.
- Test: **43 verdi**, inclusi i 3 nuovi (avanzamento+stop su `chiude_lotto`; stop
  no-progress senza flag; `BLOCCATO_CRITICITA` su lotto esistente) + schema OpenAPI ok.

**Fase 3 — ✅ FATTA (2026-06-15): management command + filtro corsia.**
Prerequisito DB soddisfatto: `fn_list_commesse_emittibili` ora accetta
`p_fatturazione_immediata` (true/false/NULL) ed espone la colonna (pushato su
`dev/db-tid`, pgTAP verde — brief
[brief-db-emittibili-filtro-fatturazione-immediata.md](brief-db-emittibili-filtro-fatturazione-immediata.md)).
- **Propagazione filtro (come da consiglio team DB: decide il driver, non l'handler)**:
  il command mette `fatturazione_immediata` nel **`meta` del lotto**; `get_lotto_context`
  lo espone (`LottoContext.fatturazione_immediata`); il pull
  ([pipeline_step_executor.py](../../../../backend/apps/vendite/services/pipeline_step_executor.py))
  lo passa a `list_commesse_emittibili`. Nessuna mappatura `tipo_lotto→filtro` sparsa
  nell'handler.
- **Repo** ([commesse_repository.py](../../../../backend/apps/vendite/db/commesse_repository.py)):
  `list_commesse_emittibili(..., fatturazione_immediata=...)` + nuova
  `list_emittibili_emittenti(...)` (emittenti distinti per la corsia/perimetro).
- **Command** `run_fatturazione_batch`
  ([run_fatturazione_batch.py](../../../../backend/apps/vendite/management/commands/run_fatturazione_batch.py)):
  `--modalita immediata|differita` (→ GIORNALIERO+True / MASSIVO+False), `--competenza`
  (default 1° del mese), `--emittente-id`, `--utility-id`, `--dry-run`, `--limit`.
  Flusso: discovery emittenti → **un lotto per emittente** → `run_lotto_pipeline_until_done`,
  best-effort (un emittente in errore non blocca gli altri) + report aggregato.
  `--dry-run` = solo discovery/conteggio (nessun lotto creato).
- Test: **104 verdi** (repo filtro+emittenti, command immediata/differita/dry-run/best-effort,
  pull handler invariato via MagicMock, sweep commesse/pipeline).

> **Catch-up corsia immediata** (nota team DB): una commessa immediata il cui run
> giornaliero fallisce **non** è ripresa dalla differita (filtro stretto) → il **timer
> frequente** della corsia immediata (F4) fa da catch-up: al giro successivo la commessa,
> ancora emittibile, viene ripresa.

**Fase 4 — Scheduling (DOCUMENTATO 2026-06-15; esecuzione = ops sul server).**
Nel repo **non** ci sono artefatti systemd/cron committati (come `send_pending_emails`):
lo scheduling è config d'ambiente. F4 = ricetta + caveat RLS; l'attivazione la fa l'ops.
- **systemd timer/cron** che lancia `manage.py run_fatturazione_batch` (solo BE/infra,
  nessun DB). **pgAgent escluso** (riservato a manutenzione DB).
- **Due cadenze**:
  - immediata (near-real-time, es. `OnCalendar=*:0/2` ≈ ogni 2 min):
    `manage.py run_fatturazione_batch --modalita immediata` — il giro frequente fa anche
    da **catch-up** per i fallimenti transitori;
  - differita (mensile, es. `OnCalendar=*-*-01 02:00`):
    `manage.py run_fatturazione_batch --modalita differita`.
- In più: endpoint **on-demand** `pipeline/run-until-done/` per avvio da interfaccia
  operatore (Fase 2).

> **⚠️ Caveat RLS (verificato 2026-06-15)**: `zeroerp_app` è `NOBYPASSRLS`;
> `vendite.fatturazione_lotti` ha RLS `ENABLE` (no FORCE) con **una sola policy**
> `rls_fatturazione_lotti_ef_whitelist` che concede **solo** a sessioni
> `app.ruolo_applicativo='OPERATORE'` con emittente in whitelist. Oggi la RLS è
> **dry-run/dormiente** → il batch da cron (senza GUC) **funziona senza utente**.
> **Ma** quando la RLS operatori sarà *enforced*, il batch (processo di **sistema**, non
> operatore, deve vedere **tutti** gli emittenti) verrebbe **default-deny** → SELECT
> vuoti + INSERT lotto negato. **Prima dell'attivazione RLS** serve un **contesto di
> sistema** per il batch (ruolo dedicato `BYPASSRLS` **oppure** `ruolo_applicativo='SISTEMA'`
> + policy permissiva di sistema): decisione DB (brief) da fare insieme
> all'[attivazione RLS operatori](analisi-attivazione-rls-operatori-be-fe.md),
> **non ora**.
>
> ✅ **RISOLTO (2026-06-17) — Path A**: ruolo DB dedicato `zeroerp_batch_fatturazione`
> (BYPASSRLS + DML scoped) + alias `system_fatturazione` + gateway BE
> `system_process_context`. DB (D1–D5) e BE (D6–D9) completati — vedi §9 e
> [brief-db-contesto-sistema-batch-fatturazione-rls.md](brief-db-contesto-sistema-batch-fatturazione-rls.md).
> Residuo ops: password ruolo in env + smoke live con RLS *enforced*.

Esempio unit systemd (riferimento, da posizionare in ambiente, non committato):

```ini
# fatturazione-immediata.service  → ExecStart=.../manage.py run_fatturazione_batch --modalita immediata
# fatturazione-immediata.timer    → [Timer] OnCalendar=*:0/2  Persistent=true
# fatturazione-differita.service  → ExecStart=.../manage.py run_fatturazione_batch --modalita differita
# fatturazione-differita.timer    → [Timer] OnCalendar=*-*-01 02:00  Persistent=true
```

**Fase 5 — ✅ SODDISFATTA DAL RIUSO (2026-06-15). Osservabilità & hold.**
L'osservabilità minima del driver è coperta dagli endpoint **già esistenti**, senza
nuovo codice:
- `GET lotti/<id>/segnalazioni/` (`ApiLottoSegnalazioniSummary`): critical/warning/
  attention + `blocks_next_step` → la condizione di stop "criticità" del driver è
  ispezionabile.
- `GET lotti/<id>/task-runs/` (`ApiLottoTaskRuns`): runtime task del lotto.
- `GET lotti/` (`ApiLottiList`, filtri stato/competenza/emittente/area) +
  `GET lotti/<id>/fatture/` (`ApiLottoFattureList`).
- Hold/sblocco: `POST lotti/<id>/reset-draft/` + `…/fatture/<id>/reset-draft/`.
- Report aggregato per `motivo_stop` emesso dal command `run_fatturazione_batch`
  (stdout/stderr) + `event_log`/`fatturazione_lotti_task_runs` popolati dalla pipeline.

**Gap BE residuo — ✅ CHIUSO (2026-06-18, registrazione run-level)**: l'esito del *run del
batch* è ora **persistito** in `maintenance.job_run_log` (riga per esecuzione: start/end,
esito, `meta` = riepilogo emittenti/falliti/per_motivo, `run_uuid` correlabile ai log di
dominio in `vendite`). Building block generico `apps.core.services.job_run.registered_job`
(riusabile da ogni cron) + funzioni DB `script.fn_job_run_start/end` (SECURITY DEFINER,
anti-overlap advisory-lock per corsia). Brief DB
[brief-db-job-run-registrazione.md](brief-db-job-run-registrazione.md) + design
[brief-design-job-run-registrazione.md](brief-design-job-run-registrazione.md). *Eventuale
endpoint di lista dei run = solo se l'operatività lo richiede.*

Un **monitor lotti** FE resta **rinviato** (§4.2): valutarlo solo se l'operatività lo
richiede.

### 10.5 Cosa serve dal DB — brief NECESSARIO (confermato in Fase 0)

La verifica seed (§10.4 F0) ha trovato gap che bloccavano il driver: brief al team DB
(azioni di seed/config = DB, mai eseguite dal BE agent — memoria
`feedback_db_actions_passaggio_team`). → ✅ **IMPLEMENTATO dal team DB (2026-06-15)**,
pushato, pgTAP verde:
[brief-db-pipeline-pull-commessa-seed.md §0](brief-db-pipeline-pull-commessa-seed.md)
(contiene anche i **vincoli BE** per il driver: idempotenza `close_lotto_operativo` su
DEFINITIVA ora `chiude_lotto`, e perimetro del pull dal `LottoContext`). Il prerequisito
DB del driver (roadmap §8 #3) è **soddisfatto**. Contenuto richiesto (storico):

1. **Seed step `pull_attivita_da_commessa`** nella pipeline (es. nuovo step prima di
   `select_attivita` nel DRAFT, o step dedicato), per MASSIVO **e** GIORNALIERO. È il
   ponte commessa → `attivita_fatturabili`, oggi non eseguito da alcun flusso.
2. **Completare la corsia GIORNALIERO**: step DRAFT (select + generate + pull) oggi
   mancante.
3. **`chiude_lotto`**: decidere se settarlo sullo stato finale (INVIATA/DEFINITIVA) per
   abilitare la chiusura da flag, oppure lasciare lo stop "ultimo step del catalogo" lato
   driver (decisione di modello da concordare nel brief).

> **Scheduler**: nessuna azione DB (systemd timer/cron + management command, non pgAgent).
> Le Fasi 1-3 (avanzamento + driver + management command) restano **solo BE**.

### 10.6 Decisioni prese (2026-06-15)

1. **Scheduler**: ✅ **systemd timer/cron + management command**; pgAgent riservato alla
   manutenzione DB; resta l'avvio **on-demand da interfaccia** operatore.
2. **Cadenza corsia immediata**: ✅ **near-real-time** (timer frequente; coda asincrona
   solo con OK esplicito perché aggiunge dipendenza).
3. **Avanzamento**: ✅ **estendere `run_pipeline`** (generalizzare il resume al percorso
   di successo), niente orchestratore duplicato.

Resta una sola decisione di modello da concordare nel brief DB: `chiude_lotto` sullo
stato finale vs stop "ultimo step del catalogo" lato driver (§10.5 punto 3).

### 10.7 Rischi

- **Regressione sul rerun-errore** toccando la risoluzione step (Fase 1): mitigare con
  test sui due percorsi (successo/errore) prima del driver.
- **Seed pipeline incompleto** sull'ambiente reale: bloccherebbe `execute_step`
  (`E_PIPELINE_NOT_FOUND`) — da verificare in Fase 0 prima di tutto.
- **Loop infinito** se l'avanzamento non progredisce: il driver deve avere un guard di
  sicurezza (numero massimo di step = lunghezza catalogo) oltre alle condizioni di stop.
