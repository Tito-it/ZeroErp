# Brief DB — Modello azioni/transizioni data-driven per gli ordini di vendita

> **✅ ESEGUITO (2026-06-05).** DB: matrice
> `config.transizioni_stati_ordini`, `script.fn_available_actions_ordine`, guard
> `vendite.trgfn_ordini_guard_transizione`, seed/errori e pgTAP creati. BE:
> `get_ordine` legge le capability dal DB e `can_conferma` è sostituito da
> `available_actions[]`. FE: `OrdiniDrawer` consuma `useEntityCapabilities` +
> `mapAvailableActionsToDrawerActions`. La stampa ordini può quindi appoggiarsi
> all'azione data-driven `conferma`.
>
> **Origine**: richiesta Tid 2026-06-05, emersa mentre si pianificava la stampa
> documentale ordini (`brief-ordini-stampa.md` §6). Leggendo il piano si è notato
> che gli ordini, a differenza degli altri documenti vendite, **non hanno un
> modello azioni data-driven**.
>
> **Natura del brief**: descrive **cosa serve e perché** (la logica e la
> motivazione), **non il come**. La strada implementativa (oggetti DB, struttura,
> seed, test) la sceglie il team DB nel rispetto dei pattern già rodati sugli altri
> documenti (`feedback_db_actions_passaggio_team`). BE/FE partono a consegna
> avvenuta (`feedback_be_fe_attende_prerequisiti_db`).
>
> **Sequenza ratificata (Tid)**: **prima** questo modello, **poi** la stampa §6 —
> così l'azione di emissione/conferma nasce già come azione data-driven invece di
> essere cablata a mano e poi rifatta.

---

## 1. Cosa è stato riscontrato

Tutti i documenti commerciali vendite **tranne l'ordine** espongono le azioni di
stato in modo **data-driven**: una funzione di dominio, dato l'id del documento,
ritorna le azioni disponibili nel suo stato corrente (con i metadati per la UI:
etichetta, severità, icona, se richiede conferma) più le capacità di editing.

- **Preventivi**: `script.fn_available_actions_preventivo` + matrice transizioni
  `config.transizioni_stati_preventivi`.
- **Offerte**: `script.fn_available_actions_offerta` + `config.stati_doc_offerte_transizioni`.
- **Contratti**: `script.fn_available_actions_contratto` (variante con metadati di
  stato).

Gli **ordini** invece:

- hanno **solo** la lista degli stati (`config.stati_doc_ordini`), **senza alcuna
  matrice di transizioni** né funzione di azioni disponibili;
- le azioni e le capacità (può confermare, può fare push, può modificare testata/
  righe) sono **calcolate a mano nel backend Python**, con stati cablati nel codice;
- di conseguenza il frontend **ricostruisce i pulsanti a mano**, mentre per gli
  altri documenti li deriva automaticamente dai metadati dell'API.

In sintesi: l'ordine è l'**unico outlier** della famiglia. Funziona, ma con una
logica parallela e duplicata rispetto agli altri tre.

## 2. Perché conviene chiuderlo (motivazione)

- **Simmetria di modello**: alla quarta occorrenza dello stesso schema, mantenere
  l'ordine fuori dal modello è un debito che costa duplicazione e divergenze
  (`feedback_simmetria_modello_no_meta_scope`). I tre domini gemelli sono la prova
  che il pattern è quello giusto e stabile.
- **Single source of truth**: le transizioni ammesse e i metadati delle azioni
  vivono in un solo posto (configurazione), non sparsi tra codice BE e FE. Le
  azioni diventano configurabili senza toccare il software.
- **Coerenza dell'esperienza**: stesse etichette, severità, icone, conferme e
  stessa logica di abilitazione/disabilitazione (con motivo) di tutti gli altri
  documenti vendite.
- **Abilita la stampa §6 in modo pulito**: l'emissione/conferma dell'ordine (che
  genera il documento) diventa **una delle azioni data-driven**, esattamente come
  l'`emetti` di preventivi/offerte — invece di un caso speciale cablato a mano.
- **Riuso lato applicativo**: i building block frontend per consumare le azioni
  data-driven **esistono già** (sono usati dagli altri domini); allineare l'ordine
  **rimuove** codice manuale invece di aggiungerne.

## 3. Cosa deve fornire il modello (logica, non implementazione)

Il modello ordini deve offrire, in modo data-driven e coerente con gli altri
documenti, la possibilità — dato un ordine — di sapere:

1. **quali azioni di stato sono disponibili** nel suo stato corrente, ciascuna con
   i metadati necessari alla UI (etichetta, severità, icona, eventuale conferma,
   stato di destinazione);
2. **quali transizioni di stato sono ammesse** e quali sono **manuali** (azione da
   interfaccia) rispetto a quelle **automatiche/di processo** (guidate da eventi a
   valle, non da un pulsante);
3. **quali capacità di editing** valgono nello stato (modifica testata/righe) e
   quali campi sono eventualmente bloccati;
4. dove un'azione non è disponibile, **il motivo** (per il tooltip), come già fanno
   gli altri documenti.

Come questo venga realizzato (matrice transizioni, funzione di dominio, metadati,
seed, test) è **scelta del team DB**, allineata al pattern di
preventivi/offerte/contratti.

## 4. Punto di dominio da chiudere — quali transizioni sono *manuali*

Questo è l'unico nodo che **non** è una scelta implementativa ma di **dominio**, e
va deciso prima del seed. La proposta (da ratificare):

- **`DRAFT → CONFERMATO`**: azione manuale di conferma/emissione (con la §6,
  genera anche il documento). **Sì, manuale.**
- **`DRAFT → ANNULLATO`**: annullo di una bozza. **Sì, manuale.**
- **`CONFERMATO → ANNULLATO`**: **da decidere** — un ordine confermato è
  annullabile da interfaccia? Presumibilmente solo se non già evaso/fatturato a
  valle. Serve la regola di dominio.
- **`CONFERMATO → ALLOCATO → SPEDITO → CONSEGNATO → FATTURATO`**: questi stati
  rappresentano l'avanzamento **a valle** (magazzino/DDT/fatturazione). **Non sono
  azioni manuali** dell'interfaccia ordine: sono guidati dai processi a valle. Non
  entrano nel grafo delle azioni manuali (al più come transizioni automatiche).

Inoltre: il **push a commessa** non è una transizione di stato ma un'azione
applicativa a sé (come il `push_commessa` dei preventivi); resta gestita come tale,
non come passaggio di stato.

> Esito atteso del confronto: un piccolo grafo di transizioni **manuali**
> (essenzialmente conferma/emissione e annullo) + la chiarezza su cosa è invece
> automatico/di processo.

## 5. Confini

- **Indipendente** dalle altre estensioni ordini già in corso (riepilogo IVA,
  stampa): è il **prerequisito** della stampa §6 ma non la include.
- **Fuori da questo brief**: il "come" DB (oggetti, struttura, seed, pgTAP) e
  l'adeguamento BE/FE (lettura del modello data-driven al posto del calcolo
  hardcoded, riuso dei building block frontend esistenti). Quest'ultimo parte a
  consegna DB avvenuta.
- **Riferimenti** (evidenza del pattern da replicare, non prescrizione): le
  funzioni `fn_available_actions_*` e le matrici `transizioni_stati_*` /
  `stati_doc_offerte_transizioni` dei tre domini gemelli.

## 6. Seguito

A modello consegnato: ordine BE legge le azioni/capacità dal modello (eliminando il
calcolo hardcoded), FE consuma le azioni con i building block già esistenti, e si
procede con la stampa §6 (`brief-ordini-stampa.md`) appoggiando l'emissione sul
nuovo modello.

---

# Analisi critica e piano di sviluppo (addendum DB+BE+FE, 2026-06-05)

> Addendum redatto dopo ricognizione del codice attuale (funzioni `fn_available_actions_*`,
> matrici `transizioni_stati_*` / `stati_doc_offerte_transizioni`, servizio
> `ordini_service.py`, building block FE `useEntityCapabilities` / `useDrawerActions` /
> `DrawerActionsBar`). Verifica i riferimenti contro il codice prima di implementare:
> sono snapshot al 2026-06-05.

## 7. Analisi critica del brief

Il brief è corretto nella diagnosi (l'ordine è l'unico outlier) e nella separazione
*cosa/perché* vs *come*. La ricognizione del codice fa però emergere **sei punti** che
vanno chiusi prima/insieme al seed, alcuni dei quali correggono assunzioni del brief.

### 7.1 Lato lettura e lato scrittura sono due metà — il brief copre solo la lettura

Il brief parla di **azioni disponibili** (`fn_available_actions_*`, lato lettura per la
UI). Ma il vero *single source of truth* lo dà la coppia **lettura + enforcement**:

- **Preventivi** validano la transizione in una **funzione** applicativa
  (`vendite.fn_cambia_stato_preventivo`, [20260403-08](../../../../db/changelog/migrations_v2/20_code/vendite/20260403-08-create-fn-cambia-stato-preventivo-mctit.yaml)).
- **Offerte** e **contratti** validano la transizione in un **trigger guard**
  (`trgfn_offerte_commerciali_guard_transizione`, `trgfn_contratti_guard_transizione_stato`).
- **Ordini** oggi **non validano nulla**: `ordini_service.conferma()` fa una
  `repo.update_stato()` diretta ([ordini_service.py:611](../../../../backend/apps/vendite/services/ordini_service.py#L611)),
  e l'unico trigger esistente
  ([20260512-19](../../../../db/changelog/migrations_v2/20_code/vendite/20260512-19-create-trgfn-ordini-guard-transizione-approvazione-mctit.yaml))
  blocca CONFERMATO solo per componenti BoM PENDING — non valida il *grafo* delle transizioni.

Se introduciamo la matrice ma non un guard, la matrice resta **consultiva** (FE/BE
disegnano i pulsanti) ma nulla impedisce un UPDATE illegale dello stato. **Raccomandazione:**
adottare il pattern **trigger guard** (offerte/contratti), il più robusto e DB-first
perché intercetta *ogni* chiamante, non solo `conferma()`. Questo va dichiarato nel piano:
non è "fuori scope" come lascia intendere il brief al §3.

### 7.2 Il grafo a valle del brief (§4) è in parte fittizio — DA NON seedare

Il brief (§4) descrive `CONFERMATO → ALLOCATO → SPEDITO → CONSEGNATO → FATTURATO` come
transizioni "automatiche/di processo a valle". La ricognizione mostra che **questi stati
ordine non vengono raggiunti da nessun processo**: le stringhe `ALLOCATO/SPEDITO/CONSEGNATO/
FATTURATO` compaiono solo negli **stati DDT** (`config.stati_doc_ddt`) e nel
`fatturazione_trigger` (config che dice *quando* fatturare in base allo stato del **DDT**,
non dell'ordine). Il push a commessa crea entità DDT/commessa separate; **l'ordine resta
CONFERMATO**. I 4 stati a valle in `config.stati_doc_ordini` sono oggi **dormienti**.

Differenza con preventivi: lì gli stati automatici seedati (SCADUTO via job notturno, EVASO
via evasione) **hanno un driver reale**, quindi è corretto averli in matrice `manuale=false`.
Per gli ordini il driver **non esiste**. **Raccomandazione:** seedare **solo il grafo reale**
(DRAFT→CONFERMATO, DRAFT→ANNULLATO, e l'eventuale CONFERMATO→ANNULLATO del §7.3). Gli stati a
valle restano fuori dalla matrice finché magazzino/DDT non li attiveranno (allora aggiungeranno
le proprie transizioni). Questo evita due errori: (a) un guard trigger che rifiuterebbe la
futura transizione legittima del magazzino se la seedassimo `attivo=true` senza driver;
(b) fabbricare un grafo che documenta un comportamento inesistente.

### 7.3 `CONFERMATO → ANNULLATO`: il brief la lascia aperta — proposta concreta

È l'unico vero nodo di dominio. Il pattern dei gemelli è coerente e suggerisce la risposta:

- **Preventivi**: EMESSO→ANNULLATO e ACCETTATO→ANNULLATO sono in matrice ma **`attivo=false`**
  (disattivate 2026-05-22); l'annullo "a valle" è bloccato se il preventivo ha righe già spinte.
- **Contratti**: ATTIVO→ANNULLATO **deliberatamente assente**; un contratto attivo si *cessa*, non si annulla.

Pattern comune: **un documento già "uscito dalla bozza" non si annulla con un click**.
**Raccomandazione:** seedare `CONFERMATO → ANNULLATO` con **`attivo=false`** (riga presente
per documentare il grafo, ma disabilitata), abilitabile in futuro solo con la regola di dominio
"annullabile se non evaso/fatturato a valle" (verificabile via `count` righe spinte / assenza DDT,
analogo al cross-domain check di `fn_cambia_stato_preventivo`). Decisione da **ratificare Tid**
prima del seed.

### 7.4 `can_conferma` deve sparire come flag — diventa un'azione

Oggi il BE espone `can_conferma` come flag booleano separato
([ordini_service.py:214](../../../../backend/apps/vendite/services/ordini_service.py#L214)) e
il FE costruisce il pulsante "Conferma" a mano
([OrdiniDrawer.vue:445](../../../../frontend/src/vendite/ordini/components/OrdiniDrawer.vue#L445)).
Nei gemelli `emetti`/`conferma` **è una entry di `available_actions[]`** (transizione di stato),
non un flag. La migrazione deve **eliminare `can_conferma`** e farlo emergere come azione
`key="conferma"` (DRAFT→CONFERMATO). Restano flag solo le capability non-transizione
(`can_edit_testata`, `can_edit_righe`, `can_push_commessa`).

### 7.5 Le precondizioni di conferma vanno spostate in DB

Oggi la regola "ordine non confermabile senza righe" (`E_ORD_NESSUNA_RIGA`) vive in Python
([ordini_service.py:598](../../../../backend/apps/vendite/services/ordini_service.py#L598)).
Preventivi la mette nel DB (`fn_cambia_stato_preventivo` esige ≥1 riga attiva con qty>0).
Per restare DB-first la precondizione va nel **guard trigger** (insieme al check approvazione
BoM già esistente del 20260512-19, da non duplicare ma da affiancare con fase `_a10_`
distinta o da consolidare). Così la regola vale per ogni chiamante e il BE smette di
calcolarla.

### 7.6 Parità di "motivo" e naming

- **Motivo (tooltip)**: gli ordini espongono `can_push_commessa` **senza** reason. I gemelli
  espongono `can_push_*_reason` + `can_push_*_reason_key`. La nuova `fn_available_actions_ordine`
  deve aggiungere `can_push_commessa_reason` / `_reason_key` (es. `ORDINE_NON_CONFERMATO`,
  `ORDINE_NESSUNA_RIGA_PUSHABILE`) per il §3.4 del brief.
- **Naming tabella**: i gemelli sono **incoerenti** — `config.transizioni_stati_preventivi`
  e `config.transizioni_stati_contratti` vs `config.stati_doc_offerte_transizioni` (l'outlier).
  Adottare la convenzione **`config.transizioni_stati_ordini`** (2 gemelli su 3, e più recente:
  contratti 2026-05-28). Funzione: `script.fn_available_actions_ordine`. Guard:
  `vendite.trgfn_ordini_<fase>_guard_transizione`.

### 7.7 Cosa il brief azzecca (da mantenere)

Push a commessa **non è** una transizione di stato (§4, ultimo capoverso): corretto, resta
azione applicativa hardcoded nella funzione (come `push_commessa`/`push_contratto` dei gemelli),
con la sua reason. La separazione *manuale vs automatico* via `meta.manuale` è il pattern giusto.

---

## 8. Piano di sviluppo

Sequenza a tre fasi con la **DB prerequisito** (memoria `feedback_be_fe_attende_prerequisiti_db`):
BE e FE partono a consegna DB avvenuta. Numerazione changeSet `YYYYMMDD-NN` da assegnare
**globalmente per data** al momento dell'implementazione (memoria
`feedback_liquibase_numerazione_globale_per_data`), qui indicata come `NN` segnaposto.

### Fase 0 — Ratifica di dominio (bloccante, prima del seed)

- [x] **D-1** `CONFERMATO → ANNULLATO`: **RATIFICATO 2026-06-05** — seed `attivo=false`
      (riga in matrice ma disabilitata), riabilitazione futura con regola "non evaso/fatturato" (§7.3).
- [x] **D-3** Enforcement via **trigger guard** (non solo lettura): **RATIFICATO 2026-06-05** (§7.1).
- [x] **D-2** Stati a valle (ALLOCATO/SPEDITO/CONSEGNATO/FATTURATO) **fuori matrice**
      finché privi di driver: **RATIFICATO 2026-06-05** (§7.2).

### Fase 1 — DB (prerequisito unico) — ✅ EVASA 2026-06-05

> **Stato:** tutti i file della Fase 1 sono stati scritti (numerazione globale
> `20260605-08..12`), validati e integrati nel flusso DB. Error code registrati
> (id 470-471), pgTAP creati e guard safe rispetto ai test esistenti su
> `stato_doc_ordine_id`.
>
> File creati:
>
> - DDL: [20260605-08-create-transizioni-stati-ordini](../../../../db/changelog/migrations_v2/00_schema/config/20260605-08-create-transizioni-stati-ordini-mctit.yaml)
> - Fn lettura: [20260605-09-create-fn-available-actions-ordine](../../../../db/changelog/migrations_v2/20_code/script/20260605-09-create-fn-available-actions-ordine-mctit.yaml)
> - Guard: [20260605-10-create-trgfn-ordini-guard-transizione](../../../../db/changelog/migrations_v2/20_code/vendite/20260605-10-create-trgfn-ordini-guard-transizione-mctit.yaml)
> - Seed: [CSV](../../../../db/changelog/migrations_v2/80_data/sql/config/transizioni_stati_ordini.csv) + [loader 20260605-11](../../../../db/changelog/migrations_v2/80_data/changelog/20260605-11-seed-transizioni-stati-ordini-mctit.yaml)
> - Error code: [20260605-12-upsert-messaggi-errore-ordini-transizione](../../../../db/changelog/migrations_v2/80_data/changelog/20260605-12-upsert-messaggi-errore-ordini-transizione-mctit.yaml) (E_ORDINE_TRANSIZIONE_NON_AMMESSA, E_ORDINE_CONFERMA_SENZA_RIGHE)
> - pgTAP: [test-fn-available-actions-ordine-v1](../../../../db/pgtap/script/test-fn-available-actions-ordine-v1.sql) (10 test) + [test-ordini-guard-transizione-v1](../../../../db/pgtap/vendite/test-ordini-guard-transizione-v1.sql) (6 test)
>
> **Scelte implementative degne di nota:**
>
> - Il guard legge il **grafo dalla matrice** (`EXISTS` in `transizioni_stati_ordini`), non
>   hardcodato come nei gemelli — coerente con lo scopo SSOT del brief.
> - Convivenza col guard approvazione (20260512-20): entrambi `_a10_ BEFORE UPDATE OF
>   stato_doc_ordine_id`, concern distinti, nessuna regola duplicata.
> - `can_change_state` calcolato sulle **sole** transizioni di stato (escluso `push_commessa`).
> - `push_commessa` riusa `fn_list_ordini_da_pushare` per l'eleggibilità (no logica duplicata).

Ordine di atterraggio (rispetta `00_schema` → `20_code` → `80_data`, e le precondition
Liquibase, memoria `feedback_liquibase_phase_ordering_preconditions`):

1. [x] **`00_schema/config/`** — DDL `config.transizioni_stati_ordini`
   (gemella di [transizioni_stati_contratti](../../../../db/changelog/migrations_v2/00_schema/config/20260528-04-create-transizioni-stati-contratti-mctit.yaml)):
   colonne `id` (IDENTITY, non SERIAL), `stato_da_id`/`stato_a_id` (FK→`stati_doc_ordini`),
   `attivo`, `meta jsonb`, audit. Vincoli: `uq(stato_da_id, stato_a_id)`, `ck` da≠a,
   `ck` meta-ui (manuali con `action_key`+`label_key`). **Niente indici FK manuali**
   (`dbops.apply_fk_index_policy`).
2. [x] **`20_code/script/`** — `script.fn_available_actions_ordine(p_ordine_id) RETURNS jsonb STABLE`,
   ricalcata su [fn_available_actions_contratto v2](../../../../db/changelog/migrations_v2/20_code/script/20260528-05-update-fn-available-actions-contratto-mctit.yaml)
   (è il riferimento più aggiornato e già data-driven). Output:
   `available_actions[]` (da matrice, filtro `attivo` + `manuale` + guard meta keys),
   `can_edit_testata`/`can_edit_righe` (true solo DRAFT), `can_push_commessa` +
   `can_push_commessa_reason`/`_reason_key` (§7.6), `non_editable_fields`, `stato_codice`.
   `push_commessa` appesa come azione hardcoded (non in matrice). Fallback `NULL` se ordine assente.
3. [x] **`20_code/vendite/`** — guard transizione `vendite.trgfn_ordini_guard_transizione` (trigger `trg_ordini_a10_guard_transizione_upd`) +
   trigger `BEFORE UPDATE OF stato_doc_ordine_id`, fase `_a10_`. Valida che la coppia
   (da,a) esista in matrice con `attivo=true`; integra la precondizione "≥1 riga"
   (§7.5). **Verificare interazione** con il guard approvazione esistente
   ([20260512-19](../../../../db/changelog/migrations_v2/20_code/vendite/20260512-19-create-trgfn-ordini-guard-transizione-approvazione-mctit.yaml)):
   o consolidare o tenere fasi `_a10_` distinte ordinate. Codici errore registrati, no
   `E_GENERICO` (memoria `feedback_error_codes_messaggi_errore`); grep pgTAP esistenti prima
   di toccare i trigger BEFORE UPDATE (memoria `feedback_guard_breaks_existing_tests`).
4. [x] **`80_data/`** — seed CSV `transizioni_stati_ordini.csv` (memoria `feedback_seed_80_data_csv`)
   + changelog upsert con `meta` (action_key, label_key, severity, icon, requires_confirm, manuale).
   Righe da seedare (post-D1/D2):
   - `DRAFT → CONFERMATO` — `action_key=conferma`, severity `info`, icon `pi pi-check`,
     `requires_confirm=true`, `manuale=true`, `attivo=true`.
   - `DRAFT → ANNULLATO` — `action_key=annulla`, severity `danger`, icon `pi pi-times`,
     `outlined=true`, `manuale=true`, `attivo=true`.
   - `CONFERMATO → ANNULLATO` — `action_key=annulla`, **`attivo=false`** (documenta il grafo).
   - i18n: aggiungere chiavi `vendite.ordini.azione_conferma` / `azione_annulla` + reason keys.
5. [x] **pgTAP** — `db/pgtap/script/test-fn-available-actions-ordine-v1.sql` (gemello di
   [test-fn-available-actions-contratto](../../../../db/pgtap/script/) / preventivo / offerta):
   DRAFT→2 azioni (conferma+annulla), CONFERMATO→push disponibile + reason null, ordine senza
   righe→conferma assente o bloccata, ordine inesistente→NULL, `label_key` valorizzati.
   + test guard transizione (transizione non ammessa → errore; conferma senza righe → errore).
   Pattern fixture da memoria `feedback_pgtap_patterns`.

> Fase 1 chiusa: il modello DB è disponibile per BE/FE e per la stampa §6.

### Fase 2 — Backend — ✅ EVASA 2026-06-05

File: [ordini_service.py](../../../../backend/apps/vendite/services/ordini_service.py),
[ordini_repository.py](../../../../backend/apps/vendite/db/ordini_repository.py),
[views_ordini.py](../../../../backend/apps/vendite/api/views_ordini.py).

- [x] **B-1** `get_ordine()`: sostituire il blocco capability hardcoded
   ([righe 204-216](../../../../backend/apps/vendite/services/ordini_service.py#L204)) con la lettura
   di `script.fn_available_actions_ordine` (pattern di `contratti_repository.call_jsonb_fn`).
   Rimuovere le costanti `_STATI_MODIFICABILI`/`_STATI_PUSHABILI`/`_STATO_*` ora che la verità è in DB.
- [x] **B-2** Eliminare il flag `can_conferma` dal payload (§7.4): l'azione conferma arriva in
   `available_actions[]`. Verificare che il serializer/contratto API esponga `available_actions`,
   `non_editable_fields`, `stato_codice` come per i gemelli.
- [x] **B-3** `conferma()`/`push_a_commessa()`/`elimina_ordine()`/`aggiorna_*`/`gestisci_riga()`:
   togliere i guard di stato calcolati in Python dove ora li garantisce il trigger DB (mantenere
   solo la gestione errori `_db_errors` + mappatura codici). La precondizione "righe>0" non va più
   duplicata in `conferma()` (§7.5).
- [x] **B-4** Test BE su detail capabilities e su conferma/annulla/push per stato.

### Fase 3 — Frontend — ✅ EVASA 2026-06-05

File: [OrdiniDrawer.vue](../../../../frontend/src/vendite/ordini/components/OrdiniDrawer.vue).
I building block **esistono già** — la modifica *rimuove* codice:

- [x] **F-1** Adottare `useEntityCapabilities(detail)` per `availableActions` / `nonEditableFields` /
   `canEdit` / `flag(...)` (come PreventiviDrawer/ContrattoDrawer), eliminando i computed manuali
   `canConferma`/`canEditTestata`/`canEditRighe`
   ([OrdiniDrawer.vue:104-118](../../../../frontend/src/vendite/ordini/components/OrdiniDrawer.vue#L104)).
- [x] **F-2** Costruire le azioni con `mapAvailableActionsToDrawerActions({availableActions, t, onAction, readonly})`
   + `DrawerActionsBar`, eliminando il `drawerActions.push({key:'conferma'...})` /
   `push({key:'push'...})` cablato a mano ([OrdiniDrawer.vue:438-464](../../../../frontend/src/vendite/ordini/components/OrdiniDrawer.vue#L438)).
   L'handler `onAction(action)` smista per `action.key` (conferma/annulla) i dialog di conferma
   già presenti; `push_commessa` resta azione applicativa dedicata (con la sua reason→tooltip).
- [x] **F-3** i18n: chiavi azioni/reason. Verifica readonly "puro" (split/LETTURA) per la barra azioni.

### Fase 4 — Sblocco stampa §6 — ✅ EVASA 2026-06-05

A modello consegnato e BE/FE migrati, l'emissione/conferma è un'azione
data-driven: la generazione documento è stata agganciata all'azione `conferma`
(`DRAFT→CONFERMATO`) tramite il flusso documentale descritto in
`brief-ordini-stampa.md` §6.

### Dipendenze e parallelizzabilità

```
Fase 0 (ratifica) ──▶ Fase 1 (DB) ──▶ Fase 2 (BE) ──▶ Fase 3 (FE) ──▶ Fase 4 (stampa §6)
   D-1,D-2,D-3          schema→code→data→pgTAP
```

Fase 1 è il **collo di bottiglia** e il prerequisito. BE e FE sono sequenziali (FE consuma il
contratto API di BE). La stampa §6 è esplicitamente a valle (sequenza ratificata Tid: prima il
modello, poi la stampa).
