## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_clienti_set_periodo()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
> 
• [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)    
> • [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)   
>
**Approfondimento funzioni:**
>
• [`anagrafiche.trgfn_clienti_set_parent_istanza()`](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza)   
> • [`anagrafiche.trgfn_clienti_sync_pdp()`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_pdp)   
> • [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)   

---

### 🎯 Scopo Principale
(latest review 09-12-25)
La funzione `anagrafiche.trgfn_clienti_set_periodo()` è una **trigger function di dominio** che ha il compito di:

1. **Normalizzare l’intervallo temporale di validità commerciale** del cliente nella colonna `periodo` (tipo `daterange`).
2. **Imporre regole di coerenza** tra:

   * stato del cliente (`stato_cliente_id` → `config.stati_cliente.codice_interno`),
   * `data_attivazione`,
   * `data_chiusura`.
3. Gestire in modo specifico i casi di **cliente annullato** (`AN`) e **cliente chiuso** (`CH`).

La funzione viene eseguita da un trigger `BEFORE INSERT OR UPDATE` su `anagrafiche.clienti`.

---

### Contesto e campi interessati

**Tabella: `anagrafiche.clienti`**

Campi utilizzati dalla funzione:

* `stato_cliente_id`  → FK verso `config.stati_cliente(id)`.
* `data_attivazione`  → data di inizio validità commerciale.
* `data_chiusura`     → data di fine validità commerciale (inclusiva a livello di dominio).
* `periodo`           → intervallo normalizzato (`daterange`) usato per vincoli di **non sovrapposizione** sullo stesso `pdp_id` (`ex_clienti_no_overlap_stesso_pdp`).
* `tx_id`             → identificativo transazione, passato ai log in caso di errore.
* `id`                → identificativo cliente, usato nei messaggi di errore.

**Tabella: `config.stati_cliente`**

Campi rilevanti:

* `id`              → PK logica dello stato.
* `codice_interno`  → codice simbolico (es. `AT`, `CH`, `AN`, ...).

La funzione utilizza `codice_interno` per differenziare il comportamento in base allo stato.

---

### Regole di business implementate

  1️⃣ Stato `AN` – Cliente annullato

Quando `codice_interno = 'AN'`:

* Il record rappresenta un **cliente annullato**, che non deve generare periodi né partecipare ai vincoli di non sovrapposizione.
* La funzione **azzera completamente** le informazioni temporali:

  * `NEW.data_attivazione := NULL;`
  * `NEW.data_chiusura    := NULL;`
  * `NEW.periodo          := NULL;`
* Il record viene così escluso dalla catena temporale e dai vincoli sul `daterange`.

> Scelta progettuale
> Per i clienti annullati **non si vuole alcuna semantica temporale**: sono considerati
> tentativi/bozze non andati a buon fine, e quindi fuori dai controlli di periodo.

---

  2️⃣ Stato `CH` – Cliente chiuso

Quando `codice_interno = 'CH'` e `data_attivazione` è valorizzata:

* Il cliente ha concluso il proprio ciclo commerciale.
* La funzione richiede coerenza tra le date:

  * `data_chiusura` **deve essere valorizzata** (verifica implicita nella logica a monte).
  * `data_chiusura` **deve essere ≥ `data_attivazione`**.
* Se la condizione non è rispettata (`data_chiusura < data_attivazione`), la funzione invoca:

```sql
PERFORM script.fn_log_and_raise_error(
    'CLIENTI',
    'anagrafiche.trgfn_clienti_set_periodo',
    'E_DATA_CHIUSURA',
    jsonb_build_object(
        'data_chiusura',    NEW.data_chiusura,
        'data_attivazione', NEW.data_attivazione,
        'cliente_id',       NEW.id
    ),
    NEW.tx_id,
    NEW.data_chiusura::text,
    NEW.data_attivazione::text,
    NEW.id::text
);
```

* L’errore blocca l’operazione, impedendo periodi temporalmente invertiti.

> In questo modo i periodi restano sempre coerenti, evitando intersezioni
> "all’indietro" che andrebbero in conflitto con altri vincoli (es. esclusioni su PDP).

---

  3️⃣ Stato `AT` – Cliente attivo

Quando `codice_interno = 'AT'` (cliente attivo):

* La **data di attivazione è obbligatoria**.
* Se `NEW.data_attivazione IS NULL`, la funzione richiama `fn_log_and_raise_error` con codice `E_DATA_APERTURA`, ad esempio:

```sql
PERFORM script.fn_log_and_raise_error(
    'CLIENTI',
    'anagrafiche.trgfn_clienti_set_periodo',
    'E_DATA_APERTURA',
    jsonb_build_object(
        'cliente_id', NEW.id
    ),
    NEW.tx_id,
    NEW.id::text
);
```

* Questo impedisce la creazione di clienti attivi senza data di inizio, condizione indispensabile per il calcolo del `periodo` e dei controlli di sovrapposizione.

---

### Normalizzazione del campo `periodo`

Al netto delle regole di stato, la funzione calcola il campo `periodo` secondo la seguente logica:

1. Determina l’estremo superiore **esclusivo** dell’intervallo:

```sql
fine_esclusiva := CASE
    WHEN NEW.data_chiusura IS NULL THEN 'infinity'::date
    ELSE NEW.data_chiusura
END;
```

2. Assegna il `daterange` solo se `data_attivazione` è valorizzata:

```sql
IF NEW.data_attivazione IS NOT NULL THEN
    NEW.periodo := daterange(NEW.data_attivazione, fine_esclusiva, '[)');
ELSE
    NEW.periodo := NULL;
END IF;
```

In questo modo otteniamo:

* **Intervallo chiuso/aperto** `[data_attivazione, data_chiusura)`
  (coerente con le convenzioni di PostgreSQL e con i vincoli di esclusione);
* Se `data_chiusura` è NULL → `periodo = [data_attivazione, infinity)`;
* Se lo stato è `AN` → `periodo = NULL` (già gestito prima).

> Nota: la scelta di usare `[)` consente di concatenare periodi adiacenti senza
> sovrapposizioni logiche (es. `[2025-01-01, 2025-06-01)` seguito da
> `[2025-06-01, infinity)`).

---

### Flusso logico riassunto

1. Recupera `codice_interno` dallo stato cliente (`config.stati_cliente`).
2. Se stato = `AN` → azzera date e periodo, **RETURN NEW**.
3. Se stato = `CH` e `data_attivazione` non NULL → verifica `data_chiusura ≥ data_attivazione`, altrimenti log+errore.
4. Se stato = `AT` → richiede `data_attivazione` non NULL, altrimenti log+errore.
5. Calcola `fine_esclusiva` (`data_chiusura` oppure `infinity`).
6. Se `data_attivazione` non NULL → imposta `periodo = daterange(…)`; altrimenti `periodo := NULL`.
7. `RETURN NEW`.

---

### Esempi di comportamento

  ✅ Cliente attivo senza chiusura

* Stato: `AT`
* `data_attivazione = '2025-01-01'`
* `data_chiusura = NULL`

➡️ `periodo = ['2025-01-01', 'infinity')`

---

  ✅ Cliente chiuso correttamente

* Stato: `CH`
* `data_attivazione = '2025-01-01'`
* `data_chiusura    = '2025-06-30'`

➡️ `periodo = ['2025-01-01', '2025-06-30')`

---

  ✅ Cliente annullato

* Stato: `AN`
* Qualsiasi valore precedente di `data_attivazione` / `data_chiusura` viene **azzerato**.

➡️ `data_attivazione = NULL`
➡️ `data_chiusura    = NULL`
➡️ `periodo          = NULL`

---

 ❌ Errore: cliente chiuso con data_chiusura < data_attivazione

* Stato: `CH`
* `data_attivazione = '2025-06-01'`
* `data_chiusura    = '2025-05-31'`

➡️ La funzione chiama `fn_log_and_raise_error('E_DATA_CHIUSURA', …)` e blocca l’operazione.

---

 ❌ Errore: cliente attivo senza data_attivazione

* Stato: `AT`
* `data_attivazione = NULL`

➡️ La funzione chiama `fn_log_and_raise_error('E_DATA_APERTURA', …)` e blocca l’operazione.

---

### Benefici del disegno

* Centralizza in un unico punto la logica di **validazione temporale** dei clienti.
* Mantiene coerente il campo `periodo`, usato dai vincoli di esclusione sul PDP.
* Evita la propagazione di logiche ridondanti lato applicativo.
* Supporta in modo esplicito il caso dei clienti **annullati**, che non devono interferire con i controlli di sovrapposizione.

In sintesi, `anagrafiche.trgfn_clienti_set_periodo()` è la "guardia" temporale del dominio clienti, garantendo che ogni stato corrisponda a una configurazione di date e periodi **consistente e compatibile** con il resto del modello Zero ERP.
