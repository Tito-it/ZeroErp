# Piano DB — ritorno del lotto a DRAFT

> **Cos'è.** Il cantiere che realizza il disegno di Tid — *EMESSA = documento non
> modificabile; per correggere si riporta a DRAFT e si ricalcola* — che oggi è
> **dichiarato a metà e non implementato**.
>
> **Estratto il 2026-08-03** da [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md)
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

---

## 1-bis. Decisioni di questo cantiere

| # | Decisione | Esito |
|---|---|---|
| **RD-1** ⭐ | **Perché un lotto può tornare a DRAFT** | ✅ **DECISA (Tid, 2026-08-03): per QUALSIASI motivo.** Che contenga fatture in errore o fatture semplicemente **da correggere**, non fa differenza: *«l'operatore sa perché lo deve portare indietro e noi dobbiamo solo permetterlo»*. **Conseguenze dirette**: (1) la funzione **non chiede il motivo** e non ha rami condizionati alla causa — nessun guard «solo se in errore», nessun guard «solo se ha criticità»; (2) il **punto B entra in 6-A** e si risolve **sempre**, non «quando serve»: se il ritorno lasciasse i log critici attivi, il lotto riaperto non ripartirebbe — e siccome il ritorno è ammesso per qualsiasi motivo, non esiste un caso in cui possiamo permetterci di non ripulirli; (3) il presidio si sposta **a valle**: ciò che deve restare vietato è numerare un documento incoerente (D-K, già in piedi), non riaprire un lotto |
| **RD-2** | **Come fa il rilancio a sapere che deve rifare il passo** (ex punto C) | 🟡 **istruita, in attesa di conferma**: strada **B**, una **colonna DATA** sul lotto (non un booleano — intuizione di Tid 2026-08-03, e stesso pattern di `obsoleto_dal`). La strada A è **caduta sulla misura**: `stato_lotto` ha una macchina a stati cablata in Python che accetta esattamente 3 valori. Vedi §4.4 e §4.6 |
| **RD-3** | **Non si bonificano dati esistenti** | ✅ **DECISA (Tid, 2026-08-03): siamo in test.** Fatture e lotti già sbagliati **non si correggono**, né a mano né con codice: non è tempo speso bene. La **2263 resta com'è** — vale come caso di prova, non come lavoro da chiudere. Coerente con [[project_no_produzione_solo_sviluppo]] e con D-G del piano satelliti |

## 2. Perimetro — 6-A adesso, 6-B dopo

Il cantiere si consegna in **due slice**, e solo la prima serve al caso reale.

| Slice | Cosa | Serve alla 2263? |
|---|---|---|
| **6-A** ⭐ | seed transizione · `fn_riporta_lotto_a_draft` · pulizia satelliti · ripartenza del rerun (BE) · pgTAP | **sì** |
| **6-B** | estrazione per-fattura (D-N-bis) · eliminazione flag `esclusa` (D-M) · verbo nel `LottoDrawer` + lista «estratte» (FE) | no |

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

---

## 5. I passi — **da scrivere dopo la §4**

> 🔴 Volutamente vuoto. La bozza che stava in §3.6 del piano satelliti (vecchi
> 6.1-6.8) **non è un piano esecutivo**: è un'intenzione scritta prima
> dell'analisi, e va riscritta, non adattata.

Quello che si sa già di dover produrre, come promemoria e non come specifica:

- il **seed** della transizione mancante lato **fattura** (§1.1: quella lato lotto
  c'è già — sono due righe diverse, e vanno contate separatamente prima di
  scrivere il CSV);
- `vendite.fn_riporta_lotto_a_draft(p_lotto_id)`, che riporta **insieme** lotto e
  fatture nella stessa transazione;
- la **pulizia** di ciò che è stato prodotto in EMESSA (scadenze, riepiloghi,
  totali, fondi). Gli **indirizzi si lasciano**: sono prodotti in DRAFT e si
  rigenerano da soli (upsert idempotente);
- i due **guard** del punto F;
- i **pgTAP**, scritti **insieme** alla funzione e non dopo — correzione d'ordine
  decisa chiudendo la 3b.

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
>
> ⚠️ **Da dove si copia cosa**: il **corpo** di una funzione esistente dalla doc
> auto-gen `docs/it/dbzero/` (riflette l'oggetto vivo); la **firma + `RETURNS`**
> dall'**ultimo YAML** che la definisce (l'auto-gen scioglie i `%TYPE`); il
> `COMMENT ON FUNCTION` con i tipi **risolti**.

### Consuntivo

| | |
|---|---|
| **Stato** | 🟡 **aperto**. Estratto dal piano satelliti il 2026-08-03. Nessun changeSet scritto |
| **Slice** | **6-A** ⬜ · **6-B** ⏭️ (§2) |
| **Prossimo passo** | **§4 — analisi preliminare obbligatoria** |

### Slice 6-A

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| **§4 Analisi preliminare** | ⬜ | — | 🔴 **obbligatoria**: 6 punti (A-F) + 7 misure sul lotto 1200 |
| §5 Passi esecutivi | ⏭️ | — | si scrivono dopo la §4 |
| §6 Brief al BE | ⏭️ | — | esce dalla §4 |

### Slice 6-B

| Passo | Stato | changeSet | Note |
|---|---|---|---|
| Estrazione per-fattura (D-N-bis) | ⏭️ | — | prerequisito D-L.3/C-22 **fatto** (§1.6) |
| Eliminazione flag `esclusa` (D-M) | ⏭️ | — | dipende dall'estrazione |
| Verbo `LottoDrawer` + lista «estratte» | ⏭️ | — | FE — [piano BE/FE §4-bis](piano-be-fe-satelliti-fattura.md) |

### Debito documentale ereditato

Due righe del [§4-bis del piano satelliti](piano-db-satelliti-fattura.md) sono
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
| Da dove viene questo documento | [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md) §3.6 (chiuso col puntatore qui) |
| Le decisioni D-* citate in §1 | [piano-db-satelliti-fattura.md §2.1](piano-db-satelliti-fattura.md) |
| I rilievi C-18 / C-19 / C-22 / C-23 | [piano-db-satelliti-fattura.md §1.2](piano-db-satelliti-fattura.md) |
| Lato applicativo di 6-B | [piano-be-fe-satelliti-fattura.md §4-bis](piano-be-fe-satelliti-fattura.md) |
| Cosa viene **dopo** questo cantiere | [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md) — incassi → `2.4 DatiPagamento` → SDI |
