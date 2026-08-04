# Piano DB — ritorno del lotto a DRAFT

> 🟢 **CANTIERE CHIUSO — 2026-08-04.** Entrambe le slice sono in esercizio, DB e
> lato applicativo:
>
> * **6-A** (ritorno del lotto in bozza) — DB il 2026-08-03, BE/FE il 2026-08-04,
>   verificata dallo smoke `smoke-ritorno-lotto-a-draft.py`: **9/9 verdi** sul
>   percorso reale. Brief archiviato in
>   [brief-be-ritorno-lotto-a-draft.md](brief-be-ritorno-lotto-a-draft.md).
> * **6-B** (eliminazione per-fattura + via il flag `esclusa`) — DB il 2026-08-04,
>   BE/FE lo stesso giorno. Il **brief B5 non è stato scritto**: le quattro
>   rotture erano già elencate nel §7 di questo piano, e riscriverle altrove
>   sarebbe stato un giro in più. Consuntivo del lato applicativo qui sotto.
>
> **Cosa ha fatto il BE/FE per la 6-B** (tutte e quattro le rotture del §7):
>
> 1. **nome della funzione** — `fn_elimina_fattura_da_lotto` propagata su
>    repository, service, view e test. ⚠️ URL (`reset-draft/`) e permesso
>    (`reset_lotto_draft`) **non** seguono la rinomina: sono contratti verso il
>    client e verso il catalogo permessi;
> 2. **quarto contatore** `riemesse_attivita` — repository, `types.py`, schema
>    OpenAPI e messaggio d'esito, che ora distingue le attività sbloccate da
>    quelle rimesse in coda;
> 3. **filtro `esclusa`** — era rotto *adesso*: via da query, parametro OpenAPI,
>    `types.py`, service, client FE e dai due test dedicati (spariscono: il
>    filtro non esiste più, non è stato «adattato»);
> 4. **codici 831-834** registrati in `error_policies.py` come **409**, coerenti
>    coi gemelli sul lotto intero.
>
> Testi del drawer riscritti: la conferma dice ora che la fattura **viene
> eliminata** e che righe, note e log spariscono con lei — con RD-7 «estratta dal
> lotto» sarebbe stato fuorviante. Binding provato con chiamata **reale**
> (transazione + rollback), non sui mock.
>
> **Un difetto trovato proprio da quella prova**, e che non riguardava la 6-B: il
> ruolo dei worker non aveva `DELETE` su `vendite.note`, quindi il rollback
> automatico della pipeline massiva falliva **solo** dal canale batch. Chiuso lo
> stesso giorno →
> [brief-db-grant-batch-cleanup-note.md](brief-db-grant-batch-cleanup-note.md).
>
> **Il debito del consuntivo è stato raccolto** lo stesso giorno, e meglio di
> come lo avevamo immaginato: non una vista fatta in casa ma l'estensione
> `plpgsql_check`, che valida i corpi per davvero — colonne comprese, rami mai
> eseguiti inclusi. Cantiere suo:
> [brief-db-bonifica-riferimenti-morti](../work-in-progress/brief-db-bonifica-riferimenti-morti.md).
> **M6** (PDF orfani) resta una segnalazione: rischio basso, la stampa si accoda
> alla numerazione, cioè fuori dal perimetro pre-fiscale.
>
> ---
>
> **Cos'è.** Il cantiere che realizza il disegno di Tid — *EMESSA = documento non
> modificabile; per correggere si riporta a DRAFT e si ricalcola* — che oggi è
> **dichiarato a metà e non implementato**.
>
> **Estratto il 2026-08-03** da [piano-db-satelliti-fattura.md](../work-in-progress/piano-db-satelliti-fattura.md)
> §3.6, dove era la «Fase 6». Ci stava per un vincolo d'ordine (§3.7 punto 6:
> *«satelliti completi → poi ritorno a DRAFT, che deve saper ripulire ciò che
> quelle fasi producono»*), non per parentela di tema. **Quel vincolo è
> soddisfatto**: le Fasi 2 e 4 sono chiuse. Da qui in avanti il registro di
> avanzamento è il **§7 di questo documento**, non il §9 di quello.
>
> 🔴 **Si apre con la [§4 — analisi preliminare obbligatoria](#4-analisi-preliminare-obbligatoria-ex-60).**
> I passi esecutivi (§5) sono **volutamente vuoti**: si scrivono dopo, non
> durante l'implementazione.

---

## 0. Il movente

Non è un cantiere teorico. Il **2026-08-03** è arrivato dal campo il primo caso
d'uso reale, documentato in
[brief-db-termine-dal-documento-alla-commessa.md §6](brief-db-termine-dal-documento-alla-commessa.md):

```
fattura 2263 — EMESSA, NON numerata, piano rate sbagliato
matrice: EMESSA -> DRAFT  AMMESSA (solo_lotto, tipo_lotto MASSIVO)
fn_elimina_fattura_da_lotto_draft(1200, 2263) -> RIFIUTATO: "solo se il lotto e DRAFT"
fn_annulla_lotto_da_draft(1200)               -> RIFIUTATO: "rollback solo se DRAFT"
```

**La matrice ammette il ritorno, la funzione che lo esegue non esiste.** Il
documento non si può disfare, e non va numerato: oltre DEFINITIVA i satelliti si
congelano e il piano rate si corregge solo con una nota di variazione.

⚠️ **La 2263 si ripara a mano, subito e separatamente** ([[project_no_produzione_solo_sviluppo]],
AGENTS.md §Workflow Safety). Questo cantiere costruisce la **capacità**, non
rincorre il caso: sganciare le due cose toglie la fretta dal disegno, che è come
sono nati i difetti peggiori del cantiere fratello (il padding `char(10)`
congelato in uno snapshot fiscale era un rinvio, non un errore di analisi).

---

## 1. Eredità — quello che è già stato deciso o misurato

Questi punti sono **già chiusi altrove** e vengono qui perché sono portanti: senza,
la §4 li ri-deduce da zero.

### 1.1 C-18 — perché la riga 2 della matrice è inerte

Misurato nel piano satelliti §1.2 (C-18):

- `config.stati_doc_fiscale_transizioni` **contiene** `EMESSA → DRAFT` (riga id **2**,
  `ammesso = t`) ma con **`solo_lotto = t`** e `meta {"tipo_lotto":"MASSIVO"}` →
  vale **solo per il lotto**;
- per la **fattura** la transizione **non è dichiarata**: `trgfn_fatture_guard_stato`
  cerca le righe con `solo_lotto = FALSE`, che sono `1→2`, `2→3`, `2→8`, `8→3`,
  `3→6`. Nessun `2→1` → una fattura che prova a tornare in DRAFT viene respinta
  con `E_LOTTO_PARAMETRO_NON_COERENTE`;
- **nessuna funzione esegue mai quella transizione**;
- e un ritorno del **solo** lotto lascerebbe le fatture a EMESSA → al commit
  scatterebbe `fn_guard_lotto_fatture_stato_coerente`
  (`E_LOTTO_FATTURE_STATO_INCOERENTE`).

### 1.2 C-19 — il presupposto: a EMESSA la fattura non è numerata

Il numero si assegna nella tappa **DEFINITIVA**, mentre la fattura è ancora
EMESSA, e solo a fine tappa il sync la porta a DEFINITIVA — tutto in una
transazione.

**Conseguenza**: tornare da EMESSA a DRAFT **non annulla mai un numero fiscale**.
Il punto di non ritorno è DEFINITIVA, e dalla `8` la matrice non prevede ritorni.

### 1.3 D-Q — la via d'uscita è rilanciare lo *stesso* step

Davanti a una fattura difettosa: **lo step si completa sempre**, la fattura resta
marcata (log `'C'` su `fatture_log` → `fn_sync_fatture_log_critical_lotto` →
`fn_resolve_stato_esecuzione` → `ERRORE` su `fatturazione_lotti_fatture`), **il
lotto non avanza**, e si esce **rilanciando lo stesso step** (o estraendo il
documento, → 6-B).

Perché il rilancio funzioni, **ogni task ritira le proprie segnalazioni** al
successo — filtrando su `meta->>'task'`, mai quelle altrui.

🔴 **Il punto (3) di D-Q è già il punto B di questa analisi, e morde prima**:
`lotto_segnalazioni_service` blocca *qualunque* esecuzione in presenza di
criticità, quindi vieta anche il rilancio dello stesso step. Va distinto **«non
avanzare»** da **«non ripartire»**.

### 1.4 La correzione di 4.2 — non filtrare su `stato_esecuzione = 'ERRORE'`

Trovata collaudando `fn_genera_scadenze_lotto`, e vale identica qui:

> Quella colonna **non** dice «rotta a monte», dice «esiste un log critico
> attivo», **di qualunque task**. Filtrarci sopra fa sì che lo step che marca una
> fattura la escluda da sé stesso per sempre: la sua bandiera non può più essere
> abbassata da chi l'ha alzata, e «rilanciare lo stesso step» smette di
> funzionare.

Il criterio corretto guarda **di chi è** la segnalazione: si salta se c'è un
critico attivo di un **altro** task. Un critico senza `meta->>'task'` conta come
altrui — una bandiera che non sappiamo chi abbia alzato non è nostra da abbassare.

### 1.5 D-L.2 — un lotto che torna a DRAFT si lascia dietro le fatture critiche

Non è un dettaglio marginale: è **la misura che ha dimostrato** che il ramo EMESSA
delle funzioni di reset non era morto, ed è esattamente lo scenario di questo
cantiere.

Misurato il 2026-08-02: `lotto 489 DRAFT · fattura 632 EMESSA critical` → il guard
di coerenza è soddisfatto (tollera la fattura disallineata quando è `critical`) e
`fn_sync_lotto_fatture_stato` le salta apposta. Perimetro attuale di **entrambe**
le funzioni dopo `20260802-01`: fatture **pre-fiscali** (DRAFT o EMESSA), lotti
**MASSIVO o GIORNALIERO**.

⚠️ **Semantica da non sbagliare**: un log critico porta subito
`vendite.fatture.critical = true`, ma `fatturazione_lotti_fatture.stato_esecuzione`
resta **PENDING** finché il runner non risincronizza. E le due funzioni di sync
**non sono intercambiabili** — `fn_sync_fatture_log_critical_lotto(bigint[])`
allinea il flag `critical`, **non** lo stato di esecuzione;
`fn_sync_lotto_fatture_stato(lotto)` **non è un ricalcolo**, porta le fatture allo
stato fiscale del LOTTO. In un pgTAP la condizione «fattura in errore» si scrive a
mano.

### 1.6 D-L.3 / C-22 — l'over-free del `lock_batch_id` è già corretto

`20260801-07` applicato: la funzione per-fattura passa **`NULL`** come
`p_lock_batch_id`. Misurato: cancellando **una** fattura col `lock_batch_id` del
lotto si liberavano **15 attività** — tutto il batch — contro **0** passando NULL.

Era il **prerequisito di 6-B** (estrazione): senza, «tolgo una fattura sbagliata»
diventa «smonto il lotto». È fatto.

### 1.7 D-M e D-N-bis — le due decisioni che riguardano 6-B

- **D-M**: il flag `fatturazione_lotti_fatture.esclusa` **si elimina**. È dormiente
  (nessuno la valorizza, cinque punti la interrogano). Perimetro DB:
  `fn_lotto_emittente_stati_lf`, `fn_lotto_stato_esecuzione_v2`,
  `fn_guard_lotto_fatture_stato_coerente` (resta la sola eccezione `critical`),
  outbox di stampa, colonna.
- **D-N-bis**: estrazione di una fattura da lotto EMESSA, **modello «reperto»** —
  si stacca il collegamento, la fattura passa ad **ANNULLATA** (non DRAFT: quello
  stato ha già la semantica esatta, `is_abortito = true`, fase `CHIUSO`, mentre una
  DRAFT staccata sembrerebbe lavorabile ed entrerebbe nei conteggi delle bozze), le
  sue attività tornano libere. Serve l'append della transizione `EMESSA → ANNULLATA`
  per la **fattura**.
  > 🔴 **SUPERATA il 2026-08-04 — vedi [RD-7](#1-bis-decisioni-di-questo-cantiere).**
  > Il modello «reperto» è stato abbandonato: la fattura si **cancella**. Cade con
  > esso l'append `EMESSA → ANNULLATA`, che non serve più. Il testo qui sopra resta
  > per la storia della decisione, non come istruzione di lavoro.

---

## 1-bis. Decisioni di questo cantiere

| # | Decisione | Esito |
|---|---|---|
| **RD-1** ⭐ | **Perché un lotto può tornare a DRAFT** | ✅ **DECISA (Tid, 2026-08-03): per QUALSIASI motivo.** Che contenga fatture in errore o fatture semplicemente **da correggere**, non fa differenza: *«l'operatore sa perché lo deve portare indietro e noi dobbiamo solo permetterlo»*. **Conseguenze dirette**: (1) la funzione **non chiede il motivo** e non ha rami condizionati alla causa — nessun guard «solo se in errore», nessun guard «solo se ha criticità»; (2) il **punto B entra in 6-A** e si risolve **sempre**, non «quando serve»: se il ritorno lasciasse i log critici attivi, il lotto riaperto non ripartirebbe — e siccome il ritorno è ammesso per qualsiasi motivo, non esiste un caso in cui possiamo permetterci di non ripulirli; (3) il presidio si sposta **a valle**: ciò che deve restare vietato è numerare un documento incoerente (D-K, già in piedi), non riaprire un lotto |
| **RD-2** | **Come fa il rilancio a sapere che deve rifare il passo** (ex punto C) | ✅ **DECISA (Tid, 2026-08-03): strada B, una colonna DATA** sul lotto (`riaperto_il`), non un booleano — stesso pattern di `obsoleto_dal` ([[reference_deprecabilita_catalogo_obsoleto_dal]]): una data si spiega da sola, si ordina, e non chiede a nessuno di ricordarsi di spegnere un flag. La strada **A è caduta sulla misura**: `stato_lotto` ha una macchina a stati cablata in Python che accetta esattamente 3 valori e rifiuta il resto. La strada **C** (dedurlo dai `task_runs`) è caduta con il punto A, §4.9. Vedi §4.4 e §4.6 |
| **RD-4** ⭐ | **Chi possiede il ripristino** (rilievo di Tid, 2026-08-03) | ✅ **DECISA: una funzione sola.** Il reset di *tutte* le tabelle vive in **`fn_cleanup_fatture_by_ids`** e in nessun altro posto; lo **stato del lotto** è un'altra cosa e appartiene all'operazione che chiama. La prima stesura di `fn_riporta_lotto_a_draft` aveva messo il reset delle `commesse_attivita` **dentro di sé** — cioè aveva duplicato la pulizia in due grafie, completa in una funzione e incompleta nelle altre due che chiamano la stessa primitiva. 🔴 **Conseguenza misurata**: `fn_annulla_lotto_da_draft` e `fn_elimina_fattura_da_lotto_draft` lasciavano le attività a `EMESSA` — righe **emesse senza fattura**, che nessun giro futuro può riprendere. Orfane oggi **0**: il difetto era **latente**, si armava al primo annullamento. `20260803-10` sposta il passo nella primitiva; le tre chiamanti non contengono più **nessuna riga** di pulizia |
| **RD-3** | **Non si bonificano dati esistenti** | ✅ **DECISA (Tid, 2026-08-03): siamo in test.** Fatture e lotti già sbagliati **non si correggono**, né a mano né con codice: non è tempo speso bene. La **2263 resta com'è** — vale come caso di prova, non come lavoro da chiudere. Coerente con [[project_no_produzione_solo_sviluppo]] e con D-G del piano satelliti |
| **RD-7** ⭐ | **Il «reperto» cade: la fattura tolta dal lotto si CANCELLA** (sostituisce D-N-bis, §1.7) | ✅ **DECISA (Tid, 2026-08-04): si cancella, testata compresa.** Motivazione di Tid: *«non serve a nulla sapere cosa era scritto su un documento che qualcuno ha deciso di rieseguire»*. **L'argomento che ha deciso**: riportare in bozza un lotto **intero** già cancella le sue fatture EMESSA, testata compresa — è ciò che `fn_riporta_lotto_a_draft` fa dal 2026-08-03 via `fn_cleanup_fatture_by_ids`. Sarebbe incoerente che la stessa operazione su **una** riga lasciasse un fantasma. **Il prezzo, misurato e accettato**: `vendite.fatture.storicizza` ha default **`false`** e nessuno lo accende (`fn_get_or_create_fattura_header` non nomina la colonna), quindi la cancellazione **non lascia traccia** del contenuto — l'unica riga che resta è quella del ponte, storicizzato (default `true`), che dice «la fattura X era in questo lotto ed è uscita» puntando a un id che non esiste più. Alzare `storicizza` sulle fatture è una decisione **separata e più grande** (storicizzerebbe ogni UPDATE di ogni fattura) e **non entra qui**. **Conseguenze dirette**: (1) niente append `EMESSA → ANNULLATA` per la fattura — il test 6 di `test-annulla-lotto-vuoto-v1.sql`, che oggi presidia proprio l'assenza di quella riga, **resta valido e non si tocca**; (2) niente scomposizione di `fn_cleanup_fatture_by_ids` — la strada (a) concordata il 2026-08-04 **decade**, RD-4 resta intatta senza lavoro; (3) niente funzione nuova: si **allarga la funzione che esiste**; (4) **un solo verbo** nel kebab, quindi cade anche il problema delle due voci omonime |

## 2. Perimetro — 6-A adesso, 6-B dopo

Il cantiere si consegna in **due slice**, e solo la prima serve al caso reale.

| Slice | Cosa | Serve alla 2263? |
|---|---|---|
| **6-A** ⭐ | seed transizione · `fn_riporta_lotto_a_draft` · pulizia satelliti · ripartenza del rerun (BE) · pgTAP | **sì** |
| **6-B** | eliminazione per-fattura da lotto pre-fiscale (~~D-N-bis~~ **RD-7**) · eliminazione flag `esclusa` (D-M) · etichette e gate nel `LottoDrawer` (FE) | no |

> ⚠️ **La 6-B si è ridotta** con RD-7 (2026-08-04). Non c'è più un'«estrazione» da
> costruire accanto all'eliminazione: sono **la stessa operazione**, e quella
> esiste già — va solo allargato il perimetro. Cade anche la «lista estratte»: se
> la fattura è cancellata non c'è niente da elencare. Vedi §7 → Slice 6-B.

**Sono separabili — verificato**: 6-B dipende da D-L.3/C-22 (§1.6, **fatto**) e non
dipende da nessun passo di 6-A. Al contrario, D-M dipende da D-N-bis («l'estrazione
è ciò che rende il flag definitivamente inutile»), quindi le due voci di 6-B stanno
insieme fra loro.

Sono **due verbi diversi**: «riapri il lotto» e «togli questa fattura dal giro».
Senza produzione non c'è nessuna ragione di consegnarli insieme, e consegnare 6-A
da sola dimezza la superficie di rischio.

---

## 3. Divisione DB | BE — misurata

Qui si scrive **solo DB** (`dev/db-tid`). Ma per decidere il DB bisogna **leggere**
il BE, perché su tre punti su sei il pezzo che *usa* il nostro dato sta in Python.

### 3.1 Nostro (DB)

| Oggetto | Ruolo nel cantiere |
|---|---|
| `vendite.fatturazione_lotti_task_runs` | punto **A** — vedi §3.3 |
| `fn_start` / `fn_complete` / `fn_fail` / `fn_cancel_lotto_task_run`, `fn_list_lotto_task_runs`, `fn_set_runtime_task_run_esito` | punto **A** |
| `vendite.fatture_log` + `fn_sync_fatture_log_critical_lotto` | punto **B**, lato pulizia |
| `fatturazione_lotti.stato_lotto` / `stato_operativo` / `lotto_job_stato` | punto **C**, lato dato |
| `attivita_fatturabili.lock_batch_id`, `fatturazione_lotti_fatture.stato_esecuzione` | punto **D** |
| `config.stati_doc_fiscale_transizioni` | seed |
| `vendite.fn_riporta_lotto_a_draft` (**da creare**) | il cuore |
| guard su fattura numerata + perimetro | punto **F** |
| pgTAP | tutto |

### 3.2 Loro (BE, `dev/backend-tid`)

| Punto di intervento | Perché ci riguarda |
|---|---|
| [`pipeline_runner.py:144-167`](../../../../backend/apps/vendite/services/pipeline_runner.py#L144-L167) — `_resolve_steps_for_run` | `steps[current_index:]` se rerun in errore, `steps[current_index + 1:]` altrimenti. **Da dove riparte il rilancio è deciso qui, in Python.** Il vecchio passo 6.4 è **interamente BE** |
| [`pipeline_repository.py:289`](../../../../backend/apps/vendite/db/pipeline_repository.py#L289) — `is_lotto_in_errore` | legge `fatturazione_lotti.stato_lotto = 'ERRORE'`. Il **dato** è nostro, la **decisione** è loro |
| [`pipeline_runner.py:422-423`](../../../../backend/apps/vendite/services/pipeline_runner.py#L422-L423) — `blocks_next_step` / `is_rilancio_stesso_step` | il gate «criticità attive» del punto **B** |
| `pipeline_runner.py` — `E_PIPELINE_LOTTO_IN_ESECUZIONE` | punto **E**: il runner ce l'ha, la funzione DB no |
| `pipeline_step_executor.py` | interpreta `RESUME_STEP`/`RESUME_TASK`. La **policy** è dato DB (`fatturazione_pipeline_task_policy` + CSV), l'**interpretazione** è Python |

### 3.3 🔎 Una scoperta che riformula il punto A

`vendite.fatturazione_lotti_task_runs` ha già **due assi** che nessuno usa per
questo scopo:

```
attivo   boolean NOT NULL DEFAULT true
UNIQUE  (lotto_id, stato_doc_fiscale_id, task_code, tentativo)
```

Le due opzioni decise da Tid — *«o si generano task_run nuovi, o si resettano»* —
sono **entrambe già cablate nella struttura**: «nuovi» = incrementare `tentativo`,
«reset» = `attivo = false`.

⚠️ **Da verificare come primo lavoro della §4**: `fn_cancel_lotto_task_run` mette
`task_stato = 'ANNULLATO'` (via `fn_set_runtime_task_run_esito`) e **non tocca
`attivo`**; la lettura del repository filtra su `WHERE attivo IS TRUE`
(`pipeline_repository.py:360`). Non ho trovato **nessuno scrittore** di
`attivo = false`. È una leva **dormiente**, e capire perché lo è viene prima di
scegliere fra le due opzioni.

### 3.4 La condizione che va concordata prima che qualcuno scriva

Il punto **C** — la condizione di ripartenza di un lotto riaperto *di proposito* —
è un **contratto fra i due lati**: il DB la scrive, il BE la legge. Se la
inventiamo noi e loro non la leggono è una colonna morta; se la inventano loro e
noi non la scriviamo è un `if` che non scatta mai.

**Esce dalla §4 come decisione dichiarata nel brief (§6), non come
implementazione.** Ordine di accensione, lo stesso già usato per 2.3 e 4.3:

```
DB scrive (inerte dove tocca la pipeline) → BE allinea e legge → armiamo
```

Non l'inverso: il BE oggi **non ha niente da chiamare**, e toccare
`_resolve_steps_for_run` per primi significa modificare un runner **funzionante**
contro un'ipotesi su un comportamento DB che non esiste ancora.

---

## 4. Analisi preliminare **obbligatoria** (ex 6.0)

> 🔴 **~mezza giornata.** I passi della §5 si scrivono **dopo** questa, non
> durante l'implementazione. Non si parte dal codice della funzione nuova.

### 4.1 Metodo: si misura, non si deduce

Non esiste produzione: l'analisi può essere **sperimentale**. Il lotto **1200** e
la fattura **2263** sono il banco di prova vero — si apre una transazione, si prova,
si guarda cosa succede davvero, si fa `ROLLBACK`.

Le sei domande sono domande su **come si comporta la macchina**, non su come è
scritta: misurarle costa meno che dedurle e non mente. È il metodo che ha già
pagato tre volte nel cantiere fratello (*«riprodotto prima di correggere»*,
*«misurato in transazione»*, la prova di mutazione al contrario di 4.3-bis).

### 4.2 I sei punti

| # | Da chiarire | Stato |
|---|---|---|
| **A** | **`fatturazione_lotti_task_runs`**: non vengono **mai** cancellati, solo aggiornati d'esito. Tornando a DRAFT restano i record dei task già eseguiti in EMESSA, e `RESUME_STEP`/`RESUME_TASK` si basano su quelli: se li considera completati, il rilancio **salta i task che devono rigirare** | 🔴 **decisione presa (Tid)**: o si **generano task_run nuovi**, o si **resettano**. Lasciarli com'è non è un'opzione. Quale delle due, lo dice l'analisi — partendo da §3.3 |
| **B** | **Log critici della fattura**: `fatture_log` non viene toccato dal ritorno, e il runner blocca l'avanzamento *«con almeno una criticità attiva»*. Un lotto riportato a DRAFT con i log vecchi ancora lì **non riparte mai** | 🟡 rinviato (Tid: «vedremo»), **ma va risolto prima che il cantiere sia dichiarabile finito**. Vincoli: §1.3 (D-Q) e §1.4 (di chi è la segnalazione) |
| **C** | **Stati non fiscali del lotto** (`stato_operativo`, `stato_lotto`, `lotto_job_stato`): quali valori dopo il ritorno? E per ripartire da DRAFT servirebbe `is_lotto_in_errore = true`, che è **semanticamente sbagliato** su un lotto riaperto di proposito: serve un **terzo meccanismo** di ripartenza, non il riuso di quello dell'errore | 🟠 da verificare. ⚠️ **È il contratto col BE** — §3.4 |
| **D** | **Lock sulle attività**: restano bloccate col `lock_batch_id` del lotto? Se sì, `select_attivita` le ritrova prese e va verificata l'idempotenza; se no, vanno sbloccate. E `stato_esecuzione` va riportato a NULL | 🟠 da verificare |
| **E** | **Concorrenza**: il runner ha `E_PIPELINE_LOTTO_IN_ESECUZIONE`, la funzione DB del ritorno non controlla nulla | 🟠 da verificare. Cfr. [[reference_advisory_lock_2_arg_namespace]] |
| **F** | **Due guard dichiarati solo nei test**: il rifiuto su fattura numerata e il perimetro «solo MASSIVO» stanno nel pgTAP ma non nei passi come guard **espliciti** | 🟠 da verificare. ⚠️ Il perimetro va riletto alla luce di §1.5: dopo `20260802-01` entrambe le funzioni di reset accettano **MASSIVO o GIORNALIERO** — «solo MASSIVO» potrebbe essere già superato |

| **G** ⭐ | 🔴 **NUOVO (Tid, 2026-08-03, da una domanda sul cruscotto)** — **le attività non tornano emittibili.** Il ritorno a DRAFT non è solo un fatto del lotto e della fattura: finché `commesse_attivita.stato_emissione` resta `EMESSA`, **il giro successivo non ha niente da riemettere** e il cruscotto competenza continua a contarle come lavorate | 🔴 **da risolvere in 6-A, è la condizione perché il ritorno serva a qualcosa** — vedi §4.5 |

> ✅ Il punto emerso in origine come settimo — il **saldo d'arrotondamento orfano** —
> è uscito da qui: è un difetto autonomo, ed è diventato **D-N pezzo 3** in Fase 3b
> (C-23). **Applicato** con `20260801-07`.

### 4.3 Le misure da fare sul lotto 1200

Da eseguire in transazione, con `ROLLBACK`, prima di scrivere qualunque passo:

| # | Misura | Serve a |
|---|---|---|
| M1 | Stato completo del lotto 1200 e delle sue fatture: stati fiscali, `stato_lotto`, `stato_operativo`, `lotto_job_stato`, `stato_esecuzione` per fattura | C, D |
| M2 | I `task_runs` del lotto: quanti, con che `task_stato`, `tentativo`, `attivo` | A |
| M3 | I `fatture_log` critici attivi: quanti, di quale `meta->>'task'`, quali `disabilitato` | B |
| M4 | Le attività agganciate: `lock_batch_id`, `lock_in_fatturazione`, `fatturato` | D |
| M5 | I satelliti prodotti in EMESSA: `fatture_scadenze`, `fatture_riepiloghi_iva`, fondi, totali | pulizia |
| M6 | Che cosa succede forzando a mano `EMESSA → DRAFT` sul lotto lasciando le fatture indietro: quale guard scatta, con quale codice | C-18, §1.1 |
| M7 | Chi scrive `attivo` su `task_runs`, sull'intero repo (DB **e** Python) | A, §3.3 |

⚠️ [[feedback_conteggi_rls_zero_non_errore]] — `vendite.fatture` e
`fatturazione_lotti` **hanno la RLS**: un conteggio senza GUC operatore dà **zero**,
e lo zero somiglia a un dato. Misurare con il canale giusto.

### 4.4 RD-2 — come fa il rilancio a sapere che deve rifare il passo

**Il problema, in parole semplici.** Quando riportiamo il lotto indietro, il lotto
torna in bozza. Ma il programma che rilancia il lavoro deve sapere una cosa in
più: *deve rifare il lavoro della bozza, oppure può saltare avanti?*

Oggi ha **un solo modo** per capirlo: guarda se il lotto è andato **in errore**.
Se sì rifà il passo, altrimenti passa al successivo. Un lotto riaperto
dall'operatore però **non è andato in errore**: ha funzionato benissimo, è il
risultato che non va bene. Se per farlo ripartire lo marchiamo «in errore»,
diciamo una **bugia** — e la bugia si vede: il cruscotto lo mostra rosso, i
conteggi dei lotti falliti lo contano, e chi guarda pensa che si sia rotto
qualcosa.

Serve quindi un modo di dire **«questo lotto è stato riaperto»** che non sia
«questo lotto è rotto».

**Le tre strade, e perché una cade da sola.**

| | Strada | Esito |
|---|---|---|
| **A** | Aggiungere un valore alle liste che già esistiamo (`stato_lotto` o `stato_operativo`) | ❌ **cade sulla misura**: `stato_lotto` ha una **macchina a stati scritta in Python** (`pipeline_repository.py:530-600`) che accetta **esattamente tre valori** e rifiuta tutto il resto, con tre transizioni cablate a mano. Un quarto valore vuol dire riscrivere quella macchina: costo sul BE, e breaking |
| **B** ⭐ | Una **colonna nuova** sul lotto che dice «riaperto il …» | ✅ **raccomandata**: nessuno di chi legge le colonne di oggi se ne accorge, e al BE serve **una condizione in più**, non un ripensamento. ⚠️ Va detto **quando si spegne**, o il lotto rifà lo stesso passo per sempre |
| **C** | Nessuna colonna: il ritorno **disattiva i `task_runs`** dei passi da rifare, e «devo rifare?» diventa «esistono ancora esecuzioni attive per questo passo?» | 💡 più elegante — **unifica RD-2 col punto A** — ma chiede al BE di cambiare **come** decide, non solo cosa legge. Più coordinamento, dentro un cantiere che deve solo permettere un ritorno |

**Raccomandazione: B.** È il cambiamento più piccolo che non dice bugie. La C è più
bella e la teniamo scritta, ma ridisegnerebbe il meccanismo di resume dentro un
cantiere che ha un altro scopo.

### 4.5 Punto G — il cruscotto non si corregge da solo, e non è un problema di conteggio

**Come conta oggi il cruscotto competenza** (`vw_dash_competenza_attivita`, misurato
sul sorgente vivo):

```sql
stato_emissione <> 'EMESSA' AND stato_approvazione <> 'APPROVATA' → DA_APPROVARE
stato_emissione <> 'EMESSA'                                       → DA_EMETTERE
af.fattura_riga_id IS NULL                                        → EMESSA_NON_FATTURATA
altrimenti                                                        → FATTURATA
```

🔴 **Lo stadio non guarda MAI lo stato fiscale della fattura.** Riportare la
fattura a DRAFT non sposta il conteggio di un millimetro. Guarda **due cose sole**:
`commesse_attivita.stato_emissione` e `attivita_fatturabili.fattura_riga_id`.

**Il vocabolario**: `stato_emissione ∈ {NON_EMESSA, EMESSA, ANNULLATA}` (oggi
52 / 37 / 2). Per tornare a `DA_EMETTERE` serve **`NON_EMESSA`**.

**Cosa fa oggi la pulizia**: `fn_cleanup_fatture_by_ids` — la primitiva usata da
entrambe le funzioni di reset — **tocca `fattura_riga_id`**, ma **non nomina mai
`commesse_attivita`** e **non tocca `stato_emissione`**. Misurato.

Quindi, riportando oggi il lotto a DRAFT: pulendo `fattura_riga_id` lo stadio
diventerebbe `EMESSA_NON_FATTURATA`, non pulendolo resterebbe `FATTURATA`.
**`DA_EMETTERE` non si raggiunge in nessun caso.**

🔴 **Ma il problema non è di conteggio, è funzionale — ed è più grave.**
`fn_emit_attivita_fatturabili_da_commessa` (quella che produce le attività da
fatturare) **filtra su `stato_emissione = 'EMESSA'`**. Un'attività lasciata a
`EMESSA` su un lotto riaperto **non viene ripresa dal giro successivo**: il lotto
riparte e **non ha niente da emettere**. Il cruscotto direbbe una bugia, ma
soprattutto il ritorno a DRAFT non servirebbe a niente.

➡️ **Il ritorno deve riportare `commesse_attivita.stato_emissione` a `NON_EMESSA`.**
Non è una rifinitura del cruscotto: è la condizione perché il ritorno funzioni.

### 4.6 Perché la data qui NON aiuta (e dove invece sì)

L'alternativa era insegnare al cruscotto a confrontare delle date (*«se è stato
riaperto dopo essere stato emesso, contalo come da emettere»*).

**Non conviene**, e il motivo è misurato: il dato sbagliato non lo legge solo il
cruscotto — lo legge anche chi **sceglie cosa emettere**. Sistemando il **dato**,
il cruscotto conta giusto **senza cambiare una riga della vista** *e* il giro
successivo riprende le attività. Sistemando la **vista**, avremmo un cruscotto che
conta giusto sopra un dato che impedisce al lotto di ripartire.

> **Regola generale**: si sistema il dato, non il lettore. Se il lettore deve
> imparare un'eccezione, di solito è il dato che sta mentendo.

✅ **Dove la data ha invece ragione: RD-2.** Come marcatore del «riaperto» una
**data** è meglio di un booleano — è autodescrittiva, ordinabile, e non richiede a
nessuno di ricordarsi di spegnere un flag. È lo stesso pattern già scelto dal
progetto per la deprecabilità di catalogo (`obsoleto_dal`,
[[reference_deprecabilita_catalogo_obsoleto_dal]]): una **DATA come asse separato**
invece di un flag booleano.

### 4.7 Esiti — le misure, fatte il 2026-08-03

**Canale**: `titodb` ha `rolbypassrls = false` **ma è owner** delle tabelle e
`relforcerowsecurity = false` → l'owner bypassa la RLS. I conteggi sotto sono
reali, non fail-closed ([[feedback_conteggi_rls_zero_non_errore]] disinnescata).

**Il caso** — lotto **1200** `LTF-0001225` MASSIVO, `EMESSA` / `stato_lotto =
COMPLETATO` / `stato_operativo = APERTO` · fattura **2263** **senza numero**
(C-19 confermato **sul dato**, non sulla teoria), `critical = f`,
`stato_esecuzione = COMPLETED` · 1 attività · satelliti: 1 scadenza, 1 riepilogo
IVA, 1 riga, 2 indirizzi · `fatture_log`: **zero righe**.

| # | Esito |
|---|---|
| **M1** | vedi sopra. 🔴 **`lotto_job_stato` non esiste**: non è colonna di nessuna tabella del DB — è il nome di un **metodo Python** (`set_lotto_job_stato`) che scrive `stato_lotto`. Gli stati non fiscali sono **due**, non tre |
| **M2** | 8 `task_runs` (4 DRAFT + 4 EMESSA), **tutti** `tentativo = 1`, `COMPLETATO`, `attivo = t` |
| **M3** | **zero** righe in `fatture_log` per la 2263 → il punto B **non morde su questo caso** (morde sul caso generale) |
| **M4** | 1 attività, `lock_in_fatturazione = t`, `fatturato = t` |
| **M5** | 1 scadenza · 1 riepilogo IVA · 1 riga · 2 indirizzi |
| **M6** | vedi §4.8 |
| **M7** | 🔴 **100 `task_runs` in tutta la tabella, 100 con `attivo = true`**. Nessuno scrittore di `attivo = false`, mai |

### 4.8 M6 — la prova in transazione (`ROLLBACK`), e l'ordine di lavoro che ne esce

| Passo | Esito misurato |
|---|---|
| sposto **solo il lotto** `EMESSA → DRAFT` | ✅ **passa senza obiezioni** (`UPDATE 1`) — la riga 2 della matrice lo permette |
| sposto **solo la fattura** `EMESSA → DRAFT` | ❌ **respinta**: `E_LOTTO_PARAMETRO_NON_COERENTE`, *«transizione 2→1»*, da `trgfn_fatture_guard_stato()` |
| `SET CONSTRAINTS ALL IMMEDIATE` con lotto DRAFT e fattura EMESSA | ❌ `E_LOTTO_FATTURE_STATO_INCOERENTE` — il guard differito **scatta**, come previsto da C-18 |

➡️ **Il seed della transizione lato fattura è il prerequisito assoluto**: senza
quella riga in matrice **niente** funziona, nemmeno `fn_sync_lotto_fatture_stato`.

ℹ️ Il messaggio d'errore del guard consiglia `fn_sync_lotto_fatture_stato` come
rimedio. ⚠️ **Non è sufficiente qui**: quella funzione **salta le fatture
`critical`** (D-L.2, §1.5), e RD-1 dice che il ritorno vale **per qualsiasi
motivo** — quindi anche per i lotti che di critiche ne hanno.

### 4.9 🔴 Il punto A cade: la sua premessa è falsa

Il punto A poggiava su *«`RESUME_STEP`/`RESUME_TASK` si basano sui `task_runs`: se
li considera completati, il rilancio salta i task che devono rigirare»*.
**Misurato: nessuno li consulta per decidere.** Catena di prove:

1. `fn_start_lotto_task_run` calcola
   `tentativo = COALESCE(MAX(tentativo), 0) + 1` e fa **sempre INSERT**. Non
   filtra su `attivo`, non riusa nulla: **ogni rilancio crea già una riga nuova**;
2. `attivo` non è mai stato scritto a `false` da nessuno (M7);
3. `resume_mode` è letto **una volta sola**, da `get_task_policy`
   (`pipeline_repository.py:708`) — e quel metodo ha **zero chiamanti**. In
   `services/` e `api/` la parola «resume» non compare;
4. 🔴 **`fn_pipeline_task_runtime_support` non esiste come funzione**: è il nome di
   un **changeSet** (`20260218-07`), che crea 9 funzioni con altri nomi. La stima
   originale «mezza giornata di lettura su `fn_pipeline_task_runtime_support`»
   puntava a un oggetto inesistente.

➡️ **Il ritorno a DRAFT non deve toccare i `task_runs`.** Sono un registro di
esecuzione, non una macchina di stato: nessuno decide su di essi.

⚠️ **Questo contraddice una decisione presa** (*«o si generano nuovi o si
resettano; lasciarli com'è non è un'opzione»*). La decisione era corretta **data la
premessa**; la premessa non regge alla misura, e la terza strada allora esclusa —
**lasciarli** — è quella giusta. `RESUME_*` è una **policy dormiente**, come lo era
`attivo`: seminata, trasportata, mai consumata.

### 4.10 Riepilogo: i sette punti, chiusi

| # | Esito |
|---|---|
| **A** | ❌ **cade** (§4.9): non si tocca nulla dei `task_runs` |
| **B** | ✅ **risolto da RD-1**: il ritorno **spegne sempre** i log critici (`disabilitato = true`, non DELETE: restano come storia) |
| **C** | ✅ **RD-2 strada B**: colonna **data** sul lotto (§4.4, §4.6) |
| **D** | ✅ **assorbito dal punto G**: le attività si sganciano e si sbloccano |
| **E** | ✅ advisory lock a 2 argomenti nella funzione ([[reference_advisory_lock_2_arg_namespace]]) |
| **F** | ✅ i due guard diventano **espliciti** nella funzione, non solo nei test |
| **G** | ✅ **il livello attività**, §4.5 — è la condizione perché il ritorno serva a qualcosa |

---

## 5. I passi

> ✅ Scritti dopo la §4, come previsto. I pgTAP nascono **insieme** alla funzione,
> non dopo — correzione d'ordine decisa chiudendo la Fase 3b del cantiere fratello.
>
> ⚠️ **Numerazione contesa il 2026-08-03**: un altro lavoro (`documenti`, ristampa
> fedele) occupava lo stesso `NN` e qualcosa ha rinumerato i file **dopo** la
> scrittura. I numeri definitivi sono **`20260803-07`** (colonna) e **`-08`**
> (funzione), scelti fuori dalla zona contesa. L'ordine fra i due **non è
> estetico**: `changelog-autogen.yaml` interleava `00_schema` e `20_code` in ordine
> temporale globale per nome file, quindi la colonna **deve** avere il numero più
> basso o su DB vergine la funzione girerebbe prima della colonna che la
> `preCondition` pretende.

### 5.1 Ordine, e perché non è negoziabile

```
A1 seed transizione fattura   ← senza, NIENTE passa (provato in M6)
   └─ A2 colonna riaperto_il  ← RD-2, indipendente da A1
        └─ A3 la funzione     ← usa entrambe
             └─ A4 pgTAP
                  └─ A5 brief al BE
```

### 5.2 I passi

| # | Cosa | Note |
|---|---|---|
| **A1** | **Seed**: la riga **2** di `stati_doc_fiscale_transizioni.csv` passa da `meta {"tipo_lotto":"MASSIVO"}` a **`{}`** | 🔴 **CORRETTO in corsa** — la prima stesura aggiungeva una riga `solo_fattura = t`, giusta per il disegno **(i)** e **sbagliata per il (ii)**: se le fatture si **cancellano** non transitano mai, quindi quella riga sarebbe stata una transizione **dichiarata legale e mai eseguita** — cioè lo stesso difetto che C-18 denuncia. Rimossa. Serve invece il lato **lotto**: `trgfn_fatturazione_lotti_guard_stato` **legge il `meta`** e ne applica `tipo_lotto`, quindi con `MASSIVO` un lotto GIORNALIERO non potrebbe tornare indietro. `{}` allinea il perimetro a D-L.2 e D-T. ✅ **Punto F verificato vero**: la retrocessione dei GIORNALIERO resta comunque presidiata da `trgfn_fatture_guard_stato`, che confronta `ordine`. Nessun changeSet: loader `runOnChange` |
| **A2** | **Colonna** `vendite.fatturazione_lotti.riaperto_il timestamptz NULL` — `20260803-07` | RD-2 strada B. Nessun default, nessun backfill: `NULL` = mai riaperto. Si accende al ritorno, **si spegne quando il lotto avanza** oltre DRAFT — altrimenti rifà lo stesso passo per sempre |
| **A3** | **`vendite.fn_riporta_lotto_a_draft(p_lotto_id bigint)`** — `20260803-08` | il cuore — vedi §5.3 |
| **A4** | **pgTAP** — `db/pgtap/vendite/test-riporta-lotto-a-draft-v1.sql` `plan(10)` | vedi §5.4 |
| **A5** | **Brief al BE** | §6 |

### 5.3 A3 — l'ordine interno della funzione

**Tre livelli**, non due. È la correzione che il punto G impone.

| | Cosa | Perché lì |
|---|---|---|
| 1 | `pg_advisory_xact_lock` a **2 argomenti** (namespace + `lotto_id`) | punto E. Mai la forma a 1 argomento ([[reference_advisory_lock_2_arg_namespace]]) |
| 2 | **Guard**: lotto esiste · **nessuna fattura numerata** · perimetro | punto F, espliciti e non solo nei test. ⚠️ Il guard su `numero` è quello che protegge da C-19 al contrario: a EMESSA non è numerata, ma la funzione non deve fidarsi dello stato — deve **guardare il numero** |
| 3 | **Fatture → DRAFT**, tutte, **anche le `critical`** | RD-1. Con `UPDATE` diretto e **non** `fn_sync_lotto_fatture_stato`, che le critiche le salta (§4.8) |
| 4 | **Lotto → DRAFT** + `riaperto_il = now()` | il guard di coerenza è DEFERRED: 3 e 4 possono stare in qualsiasi ordine, purché entrambi dentro la transazione |
| 5 | **Pulizia satelliti**: `fatture_scadenze` DELETE · riepiloghi IVA e totali azzerati · fondi via `fn_reset_fondi_fattura` | ⚠️ Gli **indirizzi si lasciano**: nascono in DRAFT e si rigenerano da soli (upsert idempotente) |
| 6 | **Attività**: `commesse_attivita.stato_emissione → NON_EMESSA` · `attivita_fatturabili` sganciate (`fattura_riga_id = NULL`, `fatturato = false`, `lock_in_fatturazione = false`) | 🔴 **punto G** — senza, il giro successivo non ha niente da riemettere |
| 7 | **Log critici**: `fatture_log.disabilitato = true` sulle fatture del lotto | RD-1 / punto B. **Non DELETE**: restano come storia |
| — | **`task_runs`: non si toccano** | §4.9 |

⚠️ **Da verificare scrivendo**: se `generate_fatture_righe` è `DELETE+INSERT`
(come `fn_genera_scadenze_fattura`) allora le righe le rigenera lui e al passo 6
basta sganciare; se è solo `INSERT`, il ritorno deve cancellarle o il rilancio
duplica. È l'unico punto ancora aperto, e si chiude leggendo quella funzione
**prima** di scrivere la nostra.

### 5.4 A4 — cosa devono mordere i pgTAP

- transizione `EMESSA → DRAFT` **ammessa per la fattura** (oggi respinta — è il
  test che diventa verde con A1);
- lotto e fatture **allineati al commit** (il guard differito non protesta);
- scadenze e riepiloghi **azzerati**, indirizzi **rimasti**;
- 🔴 **le attività tornano `NON_EMESSA` e sganciate** — punto G, ed è il test che
  vale di più perché presidia la *ragione* del ritorno, non la sua forma;
- ritorno **rifiutato se una sola fattura è numerata**;
- una fattura **`critical` torna indietro anche lei** (RD-1) — è il test che
  distingue questa funzione da `fn_sync_lotto_fatture_stato`;
- i log critici risultano **spenti ma presenti** (`disabilitato = true`, conteggio
  invariato);
- **idempotenza**: rieseguire il ritorno su un lotto già in DRAFT non rompe nulla.

⚠️ Le fixture: la condizione «fattura in errore» **si scrive a mano** — nessuna
delle due `fn_sync_*` serve a forzarla (§1.5).

### 5.5 A5 — l'invariante di copertura (RD-5)

**Il problema, posto da Tid**: oggi ripristiniamo *n* tabelle, ma domani ne nasce
una nuova collegata alla fatturazione — e la pulizia non se ne accorge.

Misurato: il fallimento sarebbe di **due tipi opposti**, e nessuno dei due è
«continua a funzionare».

| la figlia nasce con… | cosa succede |
|---|---|
| `ON DELETE CASCADE` | viene cancellata **in silenzio**, anche se doveva sopravvivere |
| `NO ACTION` | la `DELETE` **esplode** con una violazione di FK grezza, davanti all'operatore |

**RD-5 — non si costruisce una lista, si legge il catalogo.** Un registro dei
«satelliti della fattura» sarebbe una cosa in più da ricordarsi di aggiornare, e
dimenticarla non farebbe rumore. **Le FK sono già il registro**: dichiarano la
verità e sono aggiornate per costruzione.

`db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` `plan(5)` legge
da `pg_constraint` **ogni** figlia di `vendite.fatture` e pretende che sia
classificata in una di quattro categorie, **con la motivazione scritta**:

| categoria | significato |
|---|---|
| `GESTITA` | la pulizia la nomina e la tratta (verificato dal test 3, non dichiarato) |
| `CASCADE_DB` | ci pensa la FK, ed è giusto così |
| `BLOCCO_VOLUTO` | `NO ACTION` di proposito: quel documento **non si deve** poter disfare (incasso, invio SDI) |
| `SCOPERTA_NOTA` | tabella non ancora in uso: **eccezione a tempo**, valida finché resta vuota |

Le 15 figlie di oggi sono tutte classificate. ⚠️ **Un rosso non si spegne
aggiungendo la voce**: si decide a quale categoria appartiene. Il rosso non è il
problema, è la domanda.

Quattro scelte che valgono più della lista:

- si asserisce la **copertura** (quante classificate su quante esistono) e non un
  confronto fra elenchi: un confronto **passerebbe** anche se una figlia sparisse
  dal catalogo, uscendo dal paragone invece di violarlo;
- il test **2** guarda nel verso opposto — una voce rimasta dopo che la tabella è
  stata tolta è rumore che rende l'inventario poco credibile;
- il test **4** presidia i `BLOCCO_VOLUTO`: se qualcuno degradasse
  `pagamenti.vendite_movimenti` a `CASCADE`, **gli incassi verrebbero cancellati
  in silenzio**. È il modo peggiore di perdere una difesa, perché sembra una
  semplificazione;
- il test **5** fa **scadere** l'eccezione: `attivita_consumi` è fuori copertura
  perché nessuno la popola (0 righe, `fattura_id` **nullable**, unico lettore
  `fn_list_consumi_da_pushare`). Il giorno che il flusso si accende il test
  diventa rosso — cioè esattamente quando serve saperlo.

✅ **Prova di mutazione fatta, due volte**: togliendo una voce dall'inventario
(che simula una tabella nuova) fallisce **solo** il test 1 e **ne fa il nome**
(`vendite.fatture_scadenze`); dichiarando `GESTITA` una tabella che la pulizia
non nomina falliscono 1, 2 e 3, ognuno col nome giusto.

ℹ️ **Cosa NON copre**: le figlie di `vendite.fatturazione_lotti`. Il perimetro qui
è la fattura, che è ciò che la pulizia cancella. L'estensione al lotto è la stessa
forma e si scrive quando serve.

---

## 6. Contratto verso il BE — **da scrivere dopo la §4**

> 🔴 Volutamente vuoto. Esce dalla §4 e diventa un brief separato in
> `work-in-progress/`, indirizzato a `dev/backend-tid`.

Conterrà almeno:

1. la **condizione di ripartenza** del punto C (§3.4) — che cosa scriviamo noi e
   dove la leggono loro;
2. `_resolve_steps_for_run` (§3.2): un lotto riaperto deve ripartire da **DRAFT**,
   non da `steps[current_index + 1]`;
3. la distinzione **«non avanzare» / «non ripartire»** del punto B, che è il pezzo
   (3) di D-Q rimasto aperto lato BE;
4. se la funzione nuova va in `ALLOWED_TASK_FUNCTIONS` o resta chiamata da
   endpoint come le due di reset — **da decidere nella §4**.

---

## 7. Registro di avanzamento

> **Come si usa.** Ogni passo ha uno stato: ⬜ da fare · 🟡 in corso · ✅ fatto e
> testato · ⛔ bloccato · ⏭️ rinviato. Si aggiorna **qui**.
>
> **Uno step si dichiara ✅ solo quando**: changeSet **applicato** + pgTAP del
> passo **verdi** + `pgtap-baseline.sh vendite` senza regressioni + doc auto-gen
> **rigenerata**. Scritto ma non applicato resta 🟡.
>
> **Convenzioni di changeSet** — `db/changelog/migrations_v2/`, naming
> `YYYYMMDD-NN-<tipo>-<descrizione>-mctit.yaml`, **un changeSet per file**, sempre
> `logicalFilePath`, `runOnChange: false` nello stato committato. La numerazione
> `NN` è una **sequenza globale per data fra tutte le cartelle**.
> Ultimo occupato al momento dell'estrazione: **20260802-27**.
> Aggiornato al **2026-08-04**: l'ultimo occupato è **20260804-16** (cantiere
> impersonazione scope emittente). ⚠️ Nella stessa giornata possono correre due
> cantieri: prima di prendere un numero si guarda cosa c'è **già nel working tree**,
> anche non committato, e si accoda al massimo — non si riempiono i buchi.
>
> ⚠️ **Da dove si copia cosa**: il **corpo** di una funzione esistente dalla doc
> auto-gen `docs/it/dbzero/` (riflette l'oggetto vivo); la **firma + `RETURNS`**
> dall'**ultimo YAML** che la definisce (l'auto-gen scioglie i `%TYPE`); il
> `COMMENT ON FUNCTION` con i tipi **risolti**.

### Consuntivo

| | |
|---|---|
| **Stato** | ✅ **CHIUSA lato DB (2026-08-03)** — analisi, A1-A5 **applicati**, pgTAP **verdi**, doc e brief scritti. 5 changeSet: `20260803-07`…`-10` + seed CSV |
| **Slice** | **6-A** ✅ **CHIUSA** (DB 08-03 · BE/FE 08-04, smoke 9/9) · **6-B** ✅ **CHIUSA** (DB e BE/FE il 08-04) — ridotta da [RD-7](#1-bis-decisioni-di-questo-cantiere) |
| **Prossimo passo** | — **nessuno**: il cantiere è chiuso (2026-08-04). Le quattro rotture del B5 sono state lavorate dal BE/FE leggendo questo §7, senza passare da un brief separato; vedi il box in testa al documento. **M6** (PDF orfani) resta una segnalazione a rischio basso |
| **Debito lasciato aperto** | ✅ **Raccolto il 2026-08-04**: il presidio non è una vista fatta in casa ma l'estensione **`plpgsql_check`** (changeSet `20260804-36`), che valida davvero i corpi — colonne comprese, rami mai eseguiti inclusi. Primo giro: **27 difetti su 21 funzioni** + 6 trigger function orfane, fra cui una **quarta** funzione della famiglia «attivita pipeline» che il grep per nome non aveva visto. Cantiere e lista di lavoro: [brief-db-bonifica-riferimenti-morti](../work-in-progress/brief-db-bonifica-riferimenti-morti.md) |

### Slice 6-A

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| **§4 Analisi preliminare** | ✅ **CHIUSA** (2026-08-03) | — | 7 punti con risposta + 7 misure + prova in transazione. 🔴 **A cade** (§4.9), 🔴 **G è nuovo** (§4.5). Esiti in §4.7-§4.10 |
| **A1** Seed transizione lotto | ✅ **applicato** | — (solo CSV) | riga **2** di `stati_doc_fiscale_transizioni.csv`: `meta` da `{"tipo_lotto":"MASSIVO"}` a `{}`. ⚠️ **corretto in corsa**, vedi §5.2 |
| **A2** Colonna `riaperto_il` | ✅ **applicata** | `20260803-07` | inerte finché A3 non la scrive |
| **A3** `fn_riporta_lotto_a_draft` | ✅ **applicata** | `20260803-08` + fix `20260803-09` | 5 contatori, **3 livelli**, sorella di `fn_annulla_lotto_da_draft`. 🔴 **Il `-08` era rotto e il pgTAP l'ha preso al primo giro**: `pg_advisory_xact_lock(integer, bigint)` **non esiste** — gli overload sono `(bigint)` e `(integer, integer)`, quindi la forma a due argomenti vuole **due int4**. Rimedio `hashtext(p_lotto_id::text)` e **non** `::int`: il cast esploderebbe oltre i 2 miliardi, mentre una collisione di hash serializza due lotti diversi e basta — sbaglia dalla parte prudente. Nello stesso fix: firma ancorata con **`%TYPE`** (rilievo di Tid; `linee-guida-sql` §funzione madre: parametri, DECLARE, RETURNS/RETURNS TABLE, COMMENT), **`SECURITY INVOKER`** esplicito, e **`DROP` davanti alla `CREATE`** perché `CREATE OR REPLACE` non può cambiare un `RETURNS TABLE`. ⚠️ Nel `COMMENT ON FUNCTION` i tipi vanno **risolti**: `%TYPE` lì non è ammesso |
| **A4** pgTAP | ✅ **VERDE 10/10** (2026-08-03) | `test-riporta-lotto-a-draft-v1.sql` `plan(10)` | ⚠️ i test 4-10 si **saltano** se il DB non ha lotti pre-fiscali con fatture: dichiarato nel file, non nascosto. Il primo giro ha trovato il bug del lock in A3 — **i test sono nati con la funzione ed e` servito** |
| **A5** Invariante copertura figlie | ✅ **APPLICATO e VERDE 5/5** (2026-08-03) | `20260803-10` · `test-cleanup-fattura-copertura-figlie-v1.sql` `plan(5)` | **RD-4 + RD-5**, §5.5. Il `-10` fa di `fn_cleanup_fatture_by_ids` il **proprietario unico** del ripristino (assorbe il reset `commesse_attivita`, +1 contatore `riemesse_attivita`, `DROP` obbligatoria perché cambia il `RETURNS TABLE`) e sana un difetto **latente**: le due sorelle lasciavano attività **emesse senza fattura**, irrecuperabili — 0 orfane oggi, si armava al primo annullamento. Il test legge le figlie da `pg_constraint` e ne pretende la classificazione: **15/15** classificate, mutazione provata due volte, il rosso **fa il nome** della tabella. 🔴 **Rettifica a un mio allarme**: avevo annunciato un secondo bug su `fatture_fondi_fattura_source` — **non esiste**. Cercavo una `DELETE` e non l'ho trovata, ma `fn_reset_fondi_fattura` la tratta con una **UPDATE** che azzera `fattura_figlia_id` e rimette il fondo `DISPONIBILE`: è il trattamento giusto, quei crediti devono sopravvivere |
| **§6 Brief al BE** | ✅ **scritto** (2026-08-03) | — | [brief-be-ritorno-lotto-a-draft.md](brief-be-ritorno-lotto-a-draft.md). Due richieste sole, entrambe nel runner: **leggere** `riaperto_il` come terzo motivo per rifare lo step corrente, e **azzerarla** quando il lotto avanza. ✅ Verificato che i 3 codici errore sollevati sono **già** in `error_policies.py`: nessuna registrazione da chiedere |
| Doc | ✅ **scritta** (2026-08-03) | — | manuale nuovo `manual/fn_riporta_lotto_a_draft.md` · colonna `riaperto_il` aggiunta a `manual/fatturazione_lotti.md` · ⚠️ **rettificato il manuale della sorella** `fn_annulla_lotto_da_draft`, stale su due punti che D-L.2 aveva cambiato (diceva «solo MASSIVO» e «tutte le fatture in DRAFT»): le due pagine si contraddicevano. Rigenerazione auto-gen a cura di Tid |

### Slice 6-B

> **Riaperta il 2026-08-04** con [RD-7](#1-bis-decisioni-di-questo-cantiere), che la
> **riduce**: niente estrazione da costruire, niente lista «estratte», niente
> scomposizione della primitiva. Resta l'allargamento di una funzione che esiste e
> la rimozione di un flag dormiente.

#### Le misure, fatte prima di scrivere (2026-08-04)

| # | Misura | Esito |
|---|---|---|
| **M1** | La funzione da allargare esiste già | `fn_elimina_fattura_da_lotto_draft` pretende **la fattura** pre-fiscale (DRAFT **o** EMESSA — già allargata da D-L pt.2 il 2026-08-02) e **il lotto** in DRAFT. L'unico pezzo da cambiare è il perimetro del **lotto** |
| **M2** 🔴 | Il FE è già scritto come se il perimetro fosse quello nuovo | `LottoDrawer.vue` gate la voce di riga sul solo stato della **fattura** (`preFiscale`) e **non guarda lo stato del lotto**: su un lotto EMESSA la voce compare e la chiamata **fallisce**. È la **terza** occorrenza dello stesso difetto (dopo «Annulla lotto» il 07-31 e «Riporta a bozza»). L'allargamento non aggiunge una funzionalità: **chiude un bug vivo**, e lo chiude dalla parte giusta — allineando il DB al FE invece di aggiungere l'ennesimo gate in Vue |
| **M3** | Dopo l'allargamento il nome mente | `_da_lotto_draft`: il «draft» è riferito al **lotto**, che non sarà più obbligatorio. Due precedenti identici in questo stesso cantiere — `fn_elimina_fattura_draft_da_lotto` → `_da_lotto_draft` (02-08) e `fn_reset_lotto_draft` → `fn_annulla_lotto_da_draft` (01-08, D-L pt.1). Si rinomina in **`fn_elimina_fattura_da_lotto`** |
| **M4** ⚠️ | Il perimetro di `esclusa` è più largo del §1.7 | Il §1.7 dice «cinque punti la interrogano». Sono **nove** in DB — `fn_prepare_sdi_payload`, `fn_accoda_stampe_lotto`, `fn_sync_lotto_fatture_stato`, `fn_get_or_create_fattura_header`, `fn_guard_lotto_fatture_stato_coerente`, `fn_sync_fatture_log_critical_lotto`, `fn_set_fatturazione_lotto_stato`, `fn_resolve_stato_esecuzione`, `vw_lotti_fatture_incoerenti` — più un **parametro di firma** (`p_esclusa` di `fn_resolve_stato_esecuzione`) e **quattro** punti BE (filtro query, parametro OpenAPI, `types.py`, un test API). ✅ Confermato che **nessuno la valorizza**: l'unico INSERT che la nomina passa `FALSE` letterale |
| **M4-bis** 🔴 | Il perimetro della **colonna** non è quello della **firma** | Censendo per colonna si trovano **tre** chiamanti di `fn_resolve_stato_esecuzione`. Ce n'è un **quarto** — `fn_sync_attivita_stato_esecuzione` — che passa `p_esclusa => false` **costante** e non tocca mai il ponte: invisibile a un grep sulla colonna. ⚠️ Regola che ne esce: quando si toglie un parametro, si censisce la **funzione**, non il dato |
| **M4-quater** 🔴 | Il quarto chiamante è una **funzione morta**, e il migrate l'ha scoperta | Provando ad aggiornarlo, il migrate del 2026-08-04 è **fallito**: `vendite.attivita_fatturabili_lotti` **non esiste**. La funzione è morta due volte — nomina quella tabella e filtra su `attivita_fatturabili.lotto_attivita_id`, che non è più una colonna — e non ha chiamanti. Sopravvive solo perché PostgreSQL **non ri-valida** le funzioni già create quando si droppa una tabella. **Il meccanismo che l'ha smascherata**: un `%TYPE` nel `DECLARE` si risolve alla *prima esecuzione* (che non arriva mai), uno in **firma** si risolve alla `CREATE` — ed è lì che ha ceduto. ⚠️ Non è sola, ma il perimetro è **tre** e non cinque (le altre due erano falsi positivi del grep): vedi M4-quinquies. **Decisione**: D-M non le adotta. ✅ **Chiuse comunque il 2026-08-04**, vedi M4-octies |
| **M4-quinquies** 🔴 | Il perimetro vero dei riferimenti fantasma, e come sono nati | La tabella non è andata persa: è stata **droppata di proposito** il 2026-02-27 (`20260227-16-drop-attivita-pipeline-deprecated`), insieme ad altre cinque, con `CASCADE`. Il `CASCADE` porta via viste e vincoli ma **non i corpi plpgsql**, che PostgreSQL non traccia come dipendenze: da lì i fantasmi. Triage: 🔴 **`fn_set_runtime_task_run_esito`** è **viva** — la chiamano `fn_complete_`/`fn_cancel_`/`fn_fail_lotto_task_run`, e la `fn_cancel_` è quella cablata in `fn_riporta_lotto_a_draft` da RD-6 — ma il riferimento sta in un **ramo `ELSE` mai preso**: plpgsql pianifica *per statement* alla prima esecuzione di quello statement, quindi il ramo morto non esplode mai, ed è il motivo per cui i pgTAP sono verdi · 🔴 `fn_resolve_commessa_prezzi` (`%ROWTYPE` + due `%TYPE` + `FROM`) e 🔴 `fn_sync_attivita_stato_esecuzione`: entrambe **senza chiamanti**, la prima è quella che inganna di più perché il nome suona vivo · ⚪ `trgfn_attivita_fatturabili_lotti_gen_codice` ha solo il **nome** che ricorda la tabella, corpo pulito · ⚪ `trgfn_config_sistema_codici_sync_gen_codice` fa solo `DROP TRIGGER IF EXISTS … ON <tabella>` in SQL dinamico |
| **M4-ter** | Il flag muore, e con lui un secondo parametro | Tolto `p_esclusa`, `p_current_stato_esecuzione` resta **usato da nessuno**: serviva solo dentro il ramo `IF esclusa THEN RETURN corrente`. Esce anche lui — un parametro che nessun chiamante può più influenzare è una bugia nella firma. Da sei parametri a quattro |
| **M5** | La traccia della cancellazione | Ponte `fatturazione_lotti_fatture`: `storicizza` default **`true`** → la DELETE finisce nello storico. `vendite.fatture`: default **`false`** e nessuno lo accende → la testata sparisce senza lasciare contenuto. Accettato in RD-7 |
| **M4-sexies** 🔴 | Le dipendenze registrate su una colonna sono **due famiglie**, non una | La vista era prevista. Il **constraint trigger** no: `AFTER INSERT OR UPDATE OF lotto_id, fattura_id, esclusa OR DELETE` — una colonna nominata in una lista `UPDATE OF` trattiene il `DROP` esattamente come una vista. Migrate rosso il 2026-08-04. ⚠️ PostgreSQL suggerisce `DROP … CASCADE`: **non si usa**, porterebbe via il trigger in silenzio lasciando l'invariante scoperto — un presidio che sparisce senza rumore è peggio di uno che non c'è mai stato. Si tolgono a mano e si rimettono (`-30`). ℹ️ Il nome del trigger nel DB è **troncato a 63 caratteri** (`…_coerente_ins_upd`): il suffisso `_dlt` che documenta il DELETE esiste solo nel changeSet, ed è perché l'errore nominava un trigger che nei file non si trova |
| **M4-septies** 🔴 | `changelog-autogen.yaml` ordina per **NN**, non per fase | Secondo migrate rosso, e assunzione mia sbagliata: `00_schema` e `20_code` stanno nella **stessa sequenza ordinata per numero**. Quindi `20_code/-20` (che ricreava la vista) girava **prima** di `00_schema/-21` (che la droppava): vista sparita, migrate verde, scoperto da un pgTAP. La fase conta solo per `80_data`, che è `includeAll` nel master dopo l'autogen — di lì l'equivoco. **Regola**: chi ricrea una dipendenza deve avere `NN` **più alto** di chi la droppa, non semplicemente stare in `20_code` |
| **M4-octies** ✅ | Le tre funzioni fantasma sono **chiuse** (2026-08-04) | 🔴 `fn_set_runtime_task_run_esito` era **viva** (tre wrapper, uno dei quali è quello di RD-6) con il fantasma in un ramo `ELSE` mai preso — plpgsql pianifica *per statement*, quindi il ramo morto non è mai stato nemmeno pianificato: ecco perché i pgTAP erano verdi. `20260804-29` toglie il ramo e con esso `p_scope`, che restava con **un solo valore lecito**. · Le altre due (`fn_resolve_commessa_prezzi`, `fn_sync_attivita_stato_esecuzione`) **droppate** da `20260804-32` dopo verifica dei consumatori in **sei** sedi (BE, FE, seed/registry, pgTAP, altre funzioni, repo intero): **zero**. ⚠️ Erano già state riconosciute morte il **2026-03-31** — esiste un changeSet che serve solo a dirlo (`20260331-26`: «Da verificare se la funzione va rimossa dal DB») — e sono rimaste lì cinque mesi. Una segnalazione in un commento non è un presidio |
| **M6** | PDF orfani | `documenti.documenti_generati` si aggancia alla sorgente per `sorgente_uid` **testuale, senza FK**: cancellare la fattura lascia l'eventuale record del PDF a puntare nel vuoto. Rischio basso — la stampa si accoda alla **numerazione**, cioè fuori dal perimetro pre-fiscale — ma va detto al BE |

#### I passi

| Passo | Stato | changeSet | Cosa |
|---|---|---|---|
| **B1** Codici parlanti + `script.fn_check_fattura_eliminabile_da_lotto` | ✅ **applicato e verde** | `20260804-17` + CSV **831-834** | Funzione **pura**, quattro motivi in ordine: lotto oltre il pre-fiscale · fattura non collegata · fattura oltre il pre-fiscale · fattura già numerata. Stesso schema di `fn_check_lotto_annullabile`: la leggono **sia** la mutazione (che solleva il primo motivo) **sia** il BE, per spiegare invece di far fallire |
| **B2** `fn_elimina_fattura_da_lotto` | ✅ **applicato e verde** | `20260804-18` | `DROP` del vecchio nome + `CREATE` del nuovo, perimetro del **lotto** allargato a pre-fiscale, precondizioni lette da B1. Corpo operativo invariato: `fn_cleanup_fatture_by_ids(ARRAY[id], NULL)` — il `NULL` resta il punto C-22. ➕ **quarto contatore `riemesse_attivita`**, coerente con le sorelle: il nome cambia comunque, quindi si paga una rottura sola invece di due |
| **B3** pgTAP | ✅ **VERDE**, baseline `vendite` senza regressioni | `test-elimina-fattura-da-lotto-v1.sql` `plan(11)` | Caso lecito + un motivo per volta + **equivalenza** check ↔ mutazione (test 10) + **il perimetro allargato provato su un lotto EMESSA** (test 11, il bug M2). Aggiornati i **due** file che nominavano la funzione, con nota in chiaro sulla trappola 1 |
| **B4** D-M — via il flag `esclusa` | ✅ **applicato e verde** | `20260804-19` · `-20` · `-21` · `-30` · `-31` | Tre changeSet, divisi per **natura** e non per comodità: `-19` la **firma** (helper + i **quattro** chiamanti, insieme perché una firma non si cambia a metà) · `-20` i **cinque lettori della colonna** (con la vista che ri-specifica `security_invoker=on`) · `-21` in **00_schema** il `DROP VIEW` + `DROP COLUMN`. 🔴 **Due sorprese, entrambe pagate con un migrate rosso** — vedi M4-sexies e M4-septies: il trigger dell'invariante nomina `esclusa` in `UPDATE OF` (seconda dipendenza registrata, oltre alla vista) e l'autogen **ordina per numero, non per fase**, quindi le ricreazioni sono dovute salire a `-30` (trigger) e `-31` (vista). Mai `CASCADE`: avrebbe portato via il trigger in silenzio |
| **B+** Bonifica fuori perimetro | ✅ **applicato e verde** | `20260804-29` · `-32` | Non era in 6-B: è emersa da M4-quater. `-29` toglie il ramo morto e `p_scope` da `fn_set_runtime_task_run_esito` (viva); `-32` droppa le due funzioni orfane. Rimossi i due manuali e **la riga della guida utente** `gestione-commesse.md`, che linkava `fn_resolve_commessa_prezzi` in una tabella di funzioni |
| **B++** pgTAP di terzi adeguati | ✅ **verde** | — | Rossi **non nostri**, dal cantiere *emittibilità*: `test-fn-available-actions-commessa-v1` (da BOZZA le azioni sono due, non una) e `test-guard-uscita-commessa-v1` (da IN_ESECUZIONE sono tre). ⚠️ Nel secondo lo scenario «tutte disabilitate» non era più raggiungibile **sulle righe** — `chiudi` è spento ⟺ esiste una riga pendente, che è la condizione che **accende** `rendi_pronta` — e si è dovuto passare dalla **testata** (emittente NULL, secondo motivo del check). In entrambi si asserisce ora l'**insieme delle chiavi** e non il conteggio: `= 2` sarebbe passato anche con due azioni sbagliate |
| **B5** Doc + brief BE | 🟡 **doc fatta, brief da scrivere** | — | ✅ manuali di entrambe le funzioni (il vecchio `fn_elimina_fattura_da_lotto_draft.md` **rimosso**, era stale su due punti già superati da D-L pt.2) · ✅ `guide/fatturazione.md` §reset aggiornata — evade **una** delle due righe del debito documentale ereditato · ⬜ brief BE, da scrivere **dopo B4** per pagare una comunicazione sola: il **nome** della funzione (repository), il **quarto contatore**, il filtro `esclusa` dell'API + `types.py`, e i PDF orfani di M6 |

#### ⚠️ Trappole note

1. **Il test 12 di `test-arrotondamento-ambito-idempotenza-v1.sql` cerca la funzione
   per nome** (`p.proname = 'fn_elimina_fattura_da_lotto_draft'`) per verificare che
   il corpo passi `NULL` come `lock_batch_id`. Con la rinomina la sottoquery non
   trova più niente e il test diventa rosso **per il motivo sbagliato** — non «il
   corpo è cambiato» ma «la funzione non esiste». Va aggiornato nello stesso passo.
2. **`test-fatturazione-reset-lotto-draft.sql` la chiama per nome**: stessa cosa.
3. **Il test 6 di `test-annulla-lotto-vuoto-v1.sql` NON si tocca.** Presidia
   l'assenza della transizione `→ ANNULLATA` per la fattura ed è ancora corretto:
   con RD-7 quella riga non serve più. Era il rischio principale della vecchia
   D-N-bis ed è rientrato da solo.

### Debito documentale ereditato

Due righe del [§4-bis del piano satelliti](../work-in-progress/piano-db-satelliti-fattura.md) sono
agganciate a questo cantiere e si evadono **qui**, non lì:

| Guida | Cosa cambia |
|---|---|
| `guide/fatturazione.md` | la **semantica del reset**, che cambia con questo cantiere |
| `guide/cruscotti-fatturazione.md` | il verbo nuovo nel drawer lotto (6-B) |

---

## 8. Riferimenti

| Cosa | Dove |
|---|---|
| Il caso reale che ha aperto il cantiere | [brief-db-termine-dal-documento-alla-commessa.md §6](brief-db-termine-dal-documento-alla-commessa.md) |
| Da dove viene questo documento | [piano-db-satelliti-fattura.md](../work-in-progress/piano-db-satelliti-fattura.md) §3.6 (chiuso col puntatore qui) |
| Le decisioni D-* citate in §1 | [piano-db-satelliti-fattura.md §2.1](../work-in-progress/piano-db-satelliti-fattura.md) |
| I rilievi C-18 / C-19 / C-22 / C-23 | [piano-db-satelliti-fattura.md §1.2](../work-in-progress/piano-db-satelliti-fattura.md) |
| Lato applicativo di 6-B | [piano-be-fe-satelliti-fattura.md §4-bis](../work-in-progress/piano-be-fe-satelliti-fattura.md) |
| Cosa viene **dopo** questo cantiere | [brief-incassi-riconciliazione-rate-promemoria.md](../work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md) — incassi → `2.4 DatiPagamento` → SDI |
