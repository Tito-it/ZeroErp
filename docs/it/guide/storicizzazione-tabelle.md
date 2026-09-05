# Guida – Storicizzazione delle Tabelle

> (latest review 06-09-2026)
>
> Destinatari: sviluppatori database e backend
>
> Questa guida descrive il sistema di storicizzazione (versioning) delle tabelle
> in Zero ERP: come vengono registrate le modifiche, come si consultano gli
> snapshot storici e come funziona il provisioning automatico delle tabelle e dei
> trigger nello schema `storico`.
>
> Vedi anche
>
> * [Guida Automazione DB](/guide/automazione-db) — framework di automazione trigger e policy
> * [Linee Guida SQL](/linee-guida-sql) — convenzioni DDL e trigger
> * [Guida Transaction ID](/guide/tx_id_implementation_guide) — correlazione transazionale

---

## Introduzione

In un ERP che gestisce anagrafiche, contratti, fatture e documenti fiscali, poter ricostruire lo stato di un record a una data specifica e un requisito fondamentale. La storicizzazione in Zero ERP risponde a questa esigenza con un modello unificato basato su snapshot JSONB.

Ogni volta che un record viene modificato o cancellato, il trigger di storico cattura l'intero stato del record come oggetto JSONB e lo inserisce nella tabella corrispondente nello schema `storico`. Il risultato e una catena di snapshot con intervalli di validita (`valid_from` / `valid_to`) che permette di navigare la storia completa di qualsiasi entita.

Il modello e completamente automatizzato: il framework di automazione DB crea sia le tabelle di storico sia i trigger necessari, senza intervento manuale.

**Cosa troverai in questa guida:**

* La struttura standard delle tabelle di storico
* La colonna `storicizza` e il suo ciclo di vita
* Il trigger generico `trgfn_storico_generic` e il suo flusso dettagliato
* Le funzioni di consultazione snapshot
* Il provisioning automatico e le procedure di manutenzione
* La tabella di configurazione `storico_set_storicizza`

---

## Tabelle e funzioni coinvolte

**Schema `storico`:**

* `storico.<nome_tabella>` — una tabella di storico per ogni tabella operativa storicizzata

**Configurazione:**

* [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza) — registro delle tabelle con storicizzazione permanente

**Trigger function:**

* [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — trigger generico BEFORE UPDATE/DELETE

**Funzioni di consultazione:**

* [script.fn_get_snapshot_as_of](/dbzero/script/funzioni/fn_get_snapshot_as_of) — snapshot JSONB a una data
* [script.fn_get_record_id_as_of](/dbzero/script/funzioni/fn_get_record_id_as_of) — ID record storico a una data

**Automazione:**

* [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — creazione trigger di storico
* [dbops.fn_run_automations_storico_provision](/dbzero/dbops/funzioni/fn_run_automations_storico_provision) — creazione tabelle di storico
* [dbops.fn_ensure_storico_table](/dbzero/dbops/funzioni/fn_ensure_storico_table) — provisioning idempotente di una tabella

**Manutenzione:**

* [maintenance.proc_sync_storico_set_storicizza](/dbzero/maintenance/funzioni/proc_sync_storico_set_storicizza) — sincronizzazione catalogo
* [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — il registro dei lavori a orario, e perché uno di questi è rimasto rotto sei mesi
* [maintenance.proc_apply_storicizza_defaults](/dbzero/maintenance/funzioni/proc_apply_storicizza_defaults) — applicazione default settimanale

---

## Il modello in sintesi

```text
Schema operativo (es. anagrafiche)
└── soggetti                        -- tabella operativa
    ├── colonna storicizza BOOLEAN  -- flag per-record (default true se configurato)
    └── trigger trg_soggetti_z90_storico_upd_dlt
        └── BEFORE UPDATE OR DELETE → script.trgfn_storico_generic('soggetto_id')

Schema storico
└── soggetti                        -- tabella di storico (stesso nome, schema diverso)
    ├── id BIGSERIAL PK             -- PK indipendente dalla tabella operativa
    ├── soggetto_id (FK logica)     -- riferimento al record operativo
    ├── valid_from / valid_to       -- intervallo di validita dello snapshot
    ├── snapshot JSONB              -- stato completo del record al momento dell'evento
    ├── tipo_operazione SMALLINT    -- 1=iniziale, 2=UPDATE, 3=DELETE
    ├── change_type CHAR(1)         -- classificazione rapida A/U/D
    └── tx_id UUID                  -- correlazione transazionale

config
└── storico_set_storicizza          -- registro tabelle con storicizza permanente

dbops
├── automation_rules_tbl            -- regole STORICO e STORICO_PROVISION
├── fn_run_automations_storico()    -- provisioning trigger
├── fn_run_automations_storico_provision()  -- provisioning tabelle
└── fn_ensure_storico_table()       -- creazione DDL idempotente
```

---

## Struttura standard delle tabelle di storico

Ogni tabella nello schema `storico` segue una struttura rigida, creata automaticamente da `fn_ensure_storico_table`. Il campo `snapshot` JSONB contiene l'intero record serializzato, rendendo la tabella di storico indipendente dalle evoluzioni di schema della tabella operativa.

Da un punto di vista tecnico:

| Colonna | Tipo | Nullable | Default | Descrizione |
| --- | --- | :---: | --- | --- |
| `id` | BIGSERIAL, PK | no | auto | PK indipendente dalla tabella operativa |
| `<entita>_id` | stesso tipo della PK operativa | no | — | Riferimento al record originale (FK logica, senza constraint) |
| `valid_from` | TIMESTAMPTZ | no | `now()` | Inizio validita dello snapshot |
| `valid_to` | TIMESTAMPTZ | si | — | Fine validita (NULL = snapshot corrente aperto) |
| `snapshot` | JSONB | si | — | Stato completo del record al momento dell'evento |
| `tipo_operazione` | SMALLINT | si | — | 1=snapshot iniziale, 2=UPDATE, 3=DELETE |
| `change_type` | CHAR(1) | si | `'A'` | Classificazione rapida: A (add), U (update), D (delete) |
| `user_insert` | TEXT | no | `CURRENT_USER` | Utente che ha generato lo snapshot |
| `data_insert` | TIMESTAMPTZ | no | `now()` | Timestamp di creazione dello snapshot |
| `tx_id` | UUID | si | — | Transaction ID (gestito da `trgfn_tx_id_managed`) |

**Indici creati automaticamente:**

* `ix_<tabella>_<fk_col>_fk` — indice sulla colonna FK per ricerche per record operativo
* `ix_<tabella>_snapshot_gin` — indice GIN su snapshot (opzionale, se `create_gin_index=true`)

**FK non creata intenzionalmente:** la colonna `<entita>_id` non ha un vincolo FOREIGN KEY verso la tabella operativa. Questa scelta e deliberata per evitare che le operazioni di DELETE sulla tabella operativa vengano bloccate o richiedano CASCADE sulla tabella di storico.

---

## Perche JSONB per il campo `snapshot`

La scelta di usare JSONB per memorizzare lo stato del record, invece di replicare tutte le colonne della tabella operativa, ha tre motivazioni:

1. **Evoluzione dello schema**: aggiunta o rimozione di colonne nella tabella sorgente non richiede modifiche alla tabella di storico. Lo snapshot cattura sempre tutti i campi presenti al momento dell'evento.

2. **Integrita dei dati**: garantisce che ogni snapshot rifletta esattamente lo stato dell'intero record, senza omissioni ne disallineamenti.

3. **Query ad hoc**: permette estrazioni puntuali con funzioni JSON SQL (es. `snapshot->>'codice_fiscale'`).

**Trade-off:**

* Maggiore occupazione di spazio rispetto a colonne tipizzate
* Possibili impatti di performance per query su JSONB, mitigabili con indice GIN

---

## La colonna `storicizza`

Ogni tabella operativa che partecipa alla storicizzazione ha una colonna `storicizza` di tipo `BOOLEAN`. Questa colonna controlla se il singolo record deve essere storicizzato al prossimo UPDATE o DELETE.

Il comportamento dipende dalla registrazione della tabella in `config.storico_set_storicizza`:

### Tabelle registrate (storicizzazione permanente)

Se la tabella e presente in `storico_set_storicizza`, il flag `storicizza` non viene resettato dopo l'UPDATE. Il record continua a essere storicizzato a ogni modifica successiva. Questo e il comportamento standard per le tabelle anagrafiche e di configurazione.

### Tabelle non registrate (storicizzazione one-shot)

Se la tabella non e presente in `storico_set_storicizza`, dopo ogni UPDATE il trigger resetta `storicizza = FALSE`. Il record viene storicizzato una sola volta, poi richiede un'impostazione esplicita per essere storicizzato di nuovo. Utile per tabelle ad alto volume dove si vuole storicizzare solo su richiesta.

### Controllo per-record

Se `storicizza = FALSE` al momento dell'UPDATE o DELETE, il trigger non genera alcuno snapshot e restituisce il record senza modifiche. Questo permette di escludere singoli record dalla storicizzazione.

---

## Tabella di configurazione: `storico_set_storicizza`

Questa tabella nello schema `config` registra le tabelle operative che devono mantenere il flag `storicizza` sempre attivo (non resettato dal trigger).

Da un punto di vista tecnico:

| Colonna | Tipo | Nullable | Default | Descrizione |
| --- | --- | :---: | --- | --- |
| `table_name` | TEXT, PK | no | — | Nome della tabella operativa (senza schema) |
| `insert_manuale` | BOOLEAN | no | true | `true` = inserita manualmente, `false` = rilevata automaticamente |
| `data_insert` | TIMESTAMPTZ | no | `now()` | Timestamp inserimento |
| `user_insert` | TEXT | no | `CURRENT_USER` | Utente inserimento |

La procedura `proc_sync_storico_set_storicizza` popola automaticamente questa tabella rilevando dal catalogo PostgreSQL tutte le tabelle con colonna `storicizza` che hanno DEFAULT `true`. I record inseriti automaticamente hanno `insert_manuale = false`.

> Documentazione dettagliata: [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza)

---

## Trigger function: `trgfn_storico_generic`

Questa e la trigger function centrale del sistema di storicizzazione. Viene eseguita `BEFORE UPDATE OR DELETE` su ogni tabella storicizzata. Gestisce la chiusura degli snapshot precedenti, la creazione di nuovi snapshot e il reset opzionale del flag `storicizza`.

Da un punto di vista tecnico:

**Parametri (via `TG_ARGV`):**

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `TG_ARGV[0]` | TEXT | Nome della colonna FK nella tabella storica (es. `'soggetto_id'`) |

**Flusso di esecuzione completo:**

### Fase 0 — Configurazione e controllo flag

1. Verifica se la tabella e registrata in `config.storico_set_storicizza`
    * Se presente: `v_should_reset = FALSE` (non resettare il flag)
    * Se assente: `v_should_reset = TRUE` (resettare dopo l'UPDATE)
2. Rileva il tipo della colonna PK nella tabella operativa (introspezione catalogo)
3. Controlla il valore di `storicizza`:
    * UPDATE con `NEW.storicizza = FALSE` → restituisce `NEW` senza storicizzare
    * DELETE con `OLD.storicizza = FALSE` → restituisce `OLD` senza storicizzare

### Fase 1 — Recupero ID record

Ottiene l'ID del record: `OLD.id` per DELETE, `NEW.id` per UPDATE.

### Fase 2 — Creazione snapshot

Serializza il record come JSONB:

* UPDATE: `to_jsonb(NEW)` con `tipo_operazione = 2`
* DELETE: `to_jsonb(OLD)` con `tipo_operazione = 3`

### Fase 3 — Chiusura snapshot aperti

Aggiorna in `storico.<tabella>` tutti gli snapshot con `valid_to IS NULL` per lo stesso ID, impostando `valid_to = CURRENT_TIMESTAMP`. Usa SQL dinamico per la risoluzione tipo-sicura della colonna FK.

### Fase 4 — Inserimento nuovi snapshot

**4.1 — Snapshot iniziale (solo se non esistevano snapshot aperti):**

Se nessuno snapshot era aperto (prima storicizzazione del record), inserisce un record con `valid_from = '1950-01-01'` e `valid_to = CURRENT_TIMESTAMP`, `tipo_operazione = 1`. Questo rappresenta lo stato "originale" del record prima della modifica corrente, con `to_jsonb(OLD)`.

**4.2 — Snapshot finale (sempre):**

Inserisce il nuovo stato con `valid_from = CURRENT_TIMESTAMP` e `valid_to = NULL`. Per UPDATE contiene `to_jsonb(NEW)`, per DELETE contiene `to_jsonb(OLD)`.

### Fase 5 — Reset flag storicizza

Se `v_should_reset = TRUE` e l'operazione e UPDATE: imposta `NEW.storicizza = FALSE`.

### Gestione errori

Ogni sezione ha un blocco EXCEPTION dedicato che logga via `script.fn_log_and_raise_error` con codici specifici:

* `E_SNAPSHOT_ID_NOT_FOUND` — errore nel recupero dell'ID
* `E_SNAPSHOT_CLOSE_ERROR` — errore nella chiusura degli snapshot aperti
* `E_SNAPSHOT_INIT_INSERT_ERROR` — errore nell'inserimento dello snapshot iniziale
* `E_SNAPSHOT_FINAL_INSERT_ERROR` — errore nell'inserimento dello snapshot finale

> Documentazione dettagliata: [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)

---

## Funzioni di consultazione

### `fn_get_snapshot_as_of` — snapshot a una data

Restituisce lo snapshot JSONB di un record a un dato istante temporale. Se non trova snapshot nello storico, serializza la riga corrente dalla tabella operativa come fallback.

Da un punto di vista tecnico:

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_schema` | TEXT | Schema della tabella originaria |
| `p_table` | TEXT | Nome della tabella (uguale in operativo e storico) |
| `p_id` | TEXT | PK del record originario (passato come TEXT) |
| `p_fk_col` | TEXT | Nome della colonna FK in storico (es. `'soggetto_id'`) |
| `p_as_of` | TIMESTAMP | Data/ora di validita desiderata |

**Restituisce:** `JSONB` — lo snapshot del record, o NULL se non trovato.

**Logica:**

1. Verifica l'esistenza della tabella storica e rileva il tipo della colonna FK
2. Cerca in `storico.<tabella>` lo snapshot valido: `valid_from <= p_as_of AND (valid_to > p_as_of OR valid_to IS NULL)`
3. Se trovato: restituisce lo snapshot
4. Se non trovato: serializza la riga corrente dalla tabella operativa (`to_jsonb(t)`)

**Esempio:**

```sql
SELECT script.fn_get_snapshot_as_of(
  'anagrafiche', 'soggetti', '123', 'soggetto_id', '2025-06-15'::timestamp
);
-- Restituisce il JSONB del soggetto 123 come era il 15 giugno 2025
```

> Documentazione dettagliata: [script.fn_get_snapshot_as_of](/dbzero/script/funzioni/fn_get_snapshot_as_of)

---

### `fn_get_record_id_as_of` — ID record storico a una data

Restituisce solo l'ID (come TEXT) del record di storico valido a un dato istante. A differenza di `fn_get_snapshot_as_of`, non ha fallback sulla tabella operativa: cerca esclusivamente nello storico.

Da un punto di vista tecnico:

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_schema` | TEXT | Schema della tabella originaria |
| `p_table` | TEXT | Nome della tabella |
| `p_id` | TEXT | PK del record originario |
| `p_fk_col` | TEXT | Nome della colonna FK in storico |
| `p_as_of` | TIMESTAMP | Data/ora di validita desiderata |

**Restituisce:** `TEXT` — l'ID del record storico, o NULL se nessuno snapshot valido.

> Documentazione dettagliata: [script.fn_get_record_id_as_of](/dbzero/script/funzioni/fn_get_record_id_as_of)

---

## Provisioning automatico

Il sistema di storicizzazione si integra con il framework di automazione DB tramite due tipi di regole in `dbops.automation_rules_tbl`.

### Provisioning tabelle: `fn_run_automations_storico_provision`

Questa funzione scorre tutte le tabelle nell'ambito che hanno una colonna `storicizza` e crea automaticamente la corrispondente tabella nello schema `storico`.

Da un punto di vista tecnico:

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_exec_mode` | TEXT | Modalita: `AUTO`, `SCHEDULED`, `FORCE` |
| `p_schemas` | TEXT[] | Schemi da processare (NULL = tutti) |
| `p_dry_run` | BOOLEAN | Simulazione senza DDL |

**Flusso:**

1. Risolve l'ambito (esclude lo schema `storico`)
2. Filtra tabelle con colonna `storicizza` (nome configurabile via override `STORICIZZA_COL`)
3. Applica regole `STORICO_PROVISION` da `automation_rules_tbl`
4. Per ogni tabella idonea: chiama `fn_ensure_storico_table`

### Creazione DDL: `fn_ensure_storico_table`

Funzione idempotente che crea la tabella di storico con la struttura standard se non esiste gia.

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_schema_base` | TEXT | Schema della tabella operativa |
| `p_table_base` | TEXT | Nome della tabella operativa |
| `p_fk_col` | TEXT | Nome colonna FK nello storico |
| `p_create_gin_index` | BOOLEAN | Creare indice GIN su snapshot |
| `p_dry_run` | BOOLEAN | Simulazione |

**Azioni:**

* Rileva la PK mono-colonna della tabella operativa e il suo tipo
* Crea `storico.<tabella>` con la struttura standard
* Crea indice su FK e opzionalmente indice GIN su snapshot
* Se la tabella esiste gia: return immediato (idempotente)
* Non crea FOREIGN KEY (scelta deliberata)

### Provisioning trigger: `fn_run_automations_storico`

Crea il trigger `BEFORE UPDATE OR DELETE` su tutte le tabelle operative che hanno una corrispondente tabella in `storico`.

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_exec_mode` | TEXT | Modalita: `AUTO`, `SCHEDULED`, `FORCE` |
| `p_schemas` | TEXT[] | Schemi da processare (NULL = tutti) |
| `p_dry_run` | BOOLEAN | Simulazione senza DDL |

**Flusso:**

1. Risolve l'ambito (esclude `storico`)
2. Per ogni tabella: verifica che `storico.<tabella>` esista
3. Risolve la colonna FK (default `<tabella>_id`, override via `STORICO_FK`)
4. Genera il nome trigger dal template (default: `trg_{table}_z90_storico_upd_dlt`)
5. Verifica esistenza per strategia (`BY_NAME`, `BY_FUNCTION`, `BOTH`)
6. Se non esiste: crea il trigger
~~7. Opzionalmente rimuove trigger legacy separati (`drop_legacy_ud=true` in params)~~

⛔ **Il passo 7 non esiste più (rev 2026-09-01).** Il ramo `drop_legacy_ud` è
stato rimosso dal motore (`20260901-01`), e non perché la migrazione fosse
finita: **cancellava un nome che non è mai esistito**. Puntava a
`trg_{table}_upd_storico` / `trg_{table}_dlt_storico`, mentre i trigger legacy
davvero creati si chiamavano `trg_<tab>_upd_dlt_storico_<tab>` e quelli di oggi
`trg_<tab>_z90_storico_upd_dlt` — tre forme diverse, e il `DROP TRIGGER IF
EXISTS` non poteva agganciare le altre due. Il flag era per giunta
`COALESCE(..., false)`: il ramo non è mai stato eseguito nemmeno per sbaglio.

**Naming convention del trigger:** la forma è `trg_<tabella>_z90_storico_upd_dlt`,
e l'infisso `_z90_` garantisce che il trigger di storico venga eseguito per
ultimo nell'ordine alfabetico PostgreSQL, dopo tutti i trigger di guard e
validazione.

> 📌 **Rettifica del 2026-09-01**: questa riga diceva *«il prefisso `trgx_z90_`»*.
> Nel database non esiste **nessun** trigger che cominci per `trgx_` — i 118
> trigger di storicizzazione usano tutti la forma qui sopra. ⚠️ E la differenza
> non è cosmetica: chi cercasse i trigger di storico per prefisso non ne
> troverebbe **nemmeno uno**.

---

## Procedure di manutenzione

### Sincronizzazione catalogo: `proc_sync_storico_set_storicizza`

Scansiona il catalogo PostgreSQL per rilevare automaticamente tutte le tabelle con colonna `storicizza` il cui DEFAULT e `true`, e le registra in `config.storico_set_storicizza` con `insert_manuale = false`.

> ⭐ **Dal 06-09-2026 la sincronizzazione fa anche il contrario: POTA.**
> Prima sapeva solo aggiungere. Quando una tabella veniva ritirata, la sua riga
> restava — a puntare a niente, per sempre, finché qualcuno non la notava.
>
> ⛔ E non era un dettaglio: tre righe rimaste così hanno fatto fallire il lavoro
> notturno **ogni sabato per sei mesi**, senza che nessuno lo sapesse.
>
> ⚠️ Si pota **solo** ciò che la scansione ha smesso di produrre. Le righe
> inserite a mano (`insert_manuale = true`) non si toccano: quelle non sono un
> risultato della derivazione, sono una decisione di qualcuno.

**Job wrapper:** `proc_sync_storico_set_storicizza_job` — esecuzione schedulata con advisory lock e logging via `fn_run_and_log`.

### Applicazione default: `proc_apply_storicizza_defaults`

Itera tutte le tabelle registrate in `config.storico_set_storicizza` e applica `ALTER TABLE ... ALTER COLUMN storicizza SET DEFAULT true`.

> ⭐ **Dal 06-09-2026 una riga guasta non ferma più le altre.**
> Prima bastava una riga che puntava a una tabella inesistente per interrompere
> il giro per tutte le altre cento.
>
> ⚠️ E non è la conseguenza della potatura qui sopra: chi produce l'elenco e chi
> lo consuma sono **due lavori distinti su due orari diversi**. Se l'applicazione
> gira prima della sincronizzazione — e prima o poi capita — la riga vecchia c'è
> ancora. Chi consuma un elenco costruito da altri non può morire perché una
> riga non è ancora stata ripulita.

**Scheduling:** ogni sabato alle 07:00 UTC tramite pgAgent job `apply_storicizza_weekly`.

**Job wrapper:** `proc_apply_storicizza_defaults_job` — esecuzione schedulata con advisory lock e logging.

---

## Flusso operativo completo

```mermaid
flowchart TD
    A[Tabella operativa con colonna storicizza] --> B{Regola STORICO_PROVISION?}
    B -->|Si| C[fn_ensure_storico_table<br/>crea storico.tabella]
    B -->|No| D[Creazione manuale DDL]
    C --> E{Regola STORICO?}
    D --> E
    E -->|Si| F[fn_run_automations_storico<br/>crea trigger BEFORE UPDATE/DELETE]
    E -->|No| G[Creazione manuale trigger]
    F --> H[Trigger attivo]
    G --> H
    H --> I[UPDATE o DELETE su record]
    I --> J{storicizza = TRUE?}
    J -->|No| K[Skip - nessuno snapshot]
    J -->|Si| L[trgfn_storico_generic]
    L --> M[Chiude snapshot aperti<br/>valid_to = CURRENT_TIMESTAMP]
    M --> N{Primo snapshot?}
    N -->|Si| O[INSERT snapshot iniziale<br/>1950-01-01 a now]
    N -->|No| P[Continua]
    O --> P
    P --> Q[INSERT snapshot finale<br/>now a NULL]
    Q --> R{Tabella in storico_set_storicizza?}
    R -->|Si| S[Mantieni storicizza = TRUE]
    R -->|No| T[Reset storicizza = FALSE]
```

---

## Regole di dominio

1. **Una tabella di storico per ogni tabella operativa**: la tabella ha lo stesso nome ma vive nello schema `storico`. La PK e indipendente (BIGSERIAL), non collegata alla PK operativa.

2. **Nessuna FK esplicita**: la colonna `<entita>_id` nello storico non ha vincolo FOREIGN KEY verso la tabella operativa. Questo evita blocchi su DELETE e CASCADE indesiderati.

3. **Snapshot immutabili**: i record nello storico non vengono mai aggiornati nel contenuto. L'unica modifica e la chiusura dell'intervallo di validita (`valid_to`).

4. **Trigger BEFORE, non AFTER**: il trigger deve essere `BEFORE UPDATE OR DELETE` perche modifica `NEW.storicizza`. L'uso di AFTER impedirebbe il reset del flag.

5. **Infisso `_z90_`** (forma `trg_<tabella>_z90_storico_upd_dlt`): garantisce l'esecuzione per ultima nell'ordine alfabetico, dopo tutti i trigger di guard e validazione.

6. **Colonna `storicizza` obbligatoria**: la tabella operativa deve avere la colonna `storicizza BOOLEAN` per poter usare il trigger generico. Se il flag e `FALSE`, il record non viene storicizzato.

7. **Comportamento reset dipende dalla configurazione**: tabelle registrate in `storico_set_storicizza` mantengono `storicizza = TRUE` dopo ogni UPDATE (storicizzazione permanente). Tabelle non registrate resettano a `FALSE` (one-shot).

8. **Idempotenza del provisioning**: sia `fn_ensure_storico_table` sia `fn_run_automations_storico` sono idempotenti — sicure da rieseguire.

9. **Snapshot iniziale retrodatato**: alla prima storicizzazione, viene creato un record con `valid_from = '1950-01-01'` che rappresenta lo stato "originale" del record prima di qualsiasi modifica tracciata.

---

## Best practice

* **Usare il provisioning automatico** — non creare tabelle di storico e trigger manualmente. Le regole `STORICO_PROVISION` e `STORICO` in `automation_rules_tbl` garantiscono struttura e naming coerenti
* **Registrare le tabelle anagrafiche** in `config.storico_set_storicizza` per garantire storicizzazione permanente (soggetti, indirizzi, contratti, ruoli)
* **Usare `fn_get_snapshot_as_of` per le query storiche** — non interrogare direttamente le tabelle di storico salvo per analisi massive
* **Valutare l'indice GIN** per tabelle con molti record storici e necessita di query su campi specifici dello snapshot (`snapshot->>'campo'`)
* **Eseguire `proc_sync_storico_set_storicizza` dopo il deploy** per aggiornare il registro di configurazione
* **Non creare FK tra storico e tabella operativa** — la scelta e deliberata e non deve essere aggirata
* **Verificare con dry-run** prima di applicare il provisioning in produzione: `SELECT dbops.fn_run_automations_storico_provision('AUTO', NULL, true);`

---

## Diagrammi ER

### Modello di storicizzazione

```mermaid
erDiagram
    tabella_operativa {
        bigint id PK
        boolean storicizza
        text campo_1
        text campo_N
    }

    storico_tabella {
        bigserial id PK
        bigint entita_id
        timestamptz valid_from
        timestamptz valid_to
        jsonb snapshot
        smallint tipo_operazione
        char change_type
        text user_insert
        timestamptz data_insert
        uuid tx_id
    }

    storico_set_storicizza {
        text table_name PK
        boolean insert_manuale
    }

    tabella_operativa ||--o{ storico_tabella : "storicizzato in"
    storico_set_storicizza ||--|| tabella_operativa : "configurazione reset"
```

### Framework di automazione

```mermaid
erDiagram
    automation_rules_tbl {
        bigint id PK
        text rule_type
        text target_schema
        text target_table
        text name_template
        text existence_strategy
        jsonb params
    }

    fn_run_automations_storico_provision {
        text crea_tabelle_storico
    }

    fn_run_automations_storico {
        text crea_trigger_storico
    }

    fn_ensure_storico_table {
        text DDL_idempotente
    }

    automation_rules_tbl ||--|{ fn_run_automations_storico_provision : "regole STORICO_PROVISION"
    automation_rules_tbl ||--|{ fn_run_automations_storico : "regole STORICO"
    fn_run_automations_storico_provision ||--|{ fn_ensure_storico_table : "chiama per ogni tabella"
```

---

## Note finali

Questa guida copre il sistema completo di storicizzazione in Zero ERP. Per approfondimenti sulle componenti collegate:

* [Guida Automazione DB](/guide/automazione-db) — framework generale (STORICO, FK_INDEX, TX_ID, AUDIT)
* [Guida Transaction ID](/guide/tx_id_implementation_guide) — il tx_id usato per correlare gli snapshot
* [Guida Messaggi Audit](/guide/messaggi-audit) — audit log complementare alla storicizzazione
* [Linee Guida SQL](/linee-guida-sql) — convenzioni per DDL, trigger e naming

Per il dettaglio delle singole funzioni e tabelle:

* [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — trigger function
* [script.fn_get_snapshot_as_of](/dbzero/script/funzioni/fn_get_snapshot_as_of) — consultazione snapshot
* [script.fn_get_record_id_as_of](/dbzero/script/funzioni/fn_get_record_id_as_of) — ID storico
* [dbops.fn_ensure_storico_table](/dbzero/dbops/funzioni/fn_ensure_storico_table) — provisioning tabella
* [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza) — configurazione reset

---

{% include-markdown "signature-core.md" %}
