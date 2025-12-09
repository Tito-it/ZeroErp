## 📘 Documentazione Concettuale – Funzione `script.fn_get_or_create_soggetto_ruolo`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**  
>
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)   
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
> • [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)   
>
> **Approfondimento funzioni / log & sicurezza:**
>
> • [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)    
> • [`script.fn_guard_soggetto_ruolo`](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)    

---

### 🎯 Scopo Principale
(latest review 09-12-25)
La funzione **`script.fn_get_or_create_soggetto_ruolo`** è una **factory di dominio** per garantire l’esistenza di un legame tra:

* un **soggetto** (`anagrafiche.soggetti.id`) e
* un **ruolo** (`config.tipi_ruoli.codice_interno` → `config.tipi_ruoli.id`),

all’interno della tabella **`anagrafiche.soggetti_ruoli`**.

Comportamento:

1. **Valida** i parametri in ingresso (soggetto e codice interno del ruolo).
2. **Risolive** l’ID del ruolo partendo da `config.tipi_ruoli.codice_interno`.
3. **Ricerca** un legame esistente in `anagrafiche.soggetti_ruoli`.
4. Se il legame **esiste già**, restituisce l’`id`.
5. Se il legame **non esiste**, lo **crea** in modo **concorrenza-safe** (gestendo `unique_violation`) e restituisce l’`id` definitivo.

In questo modo, qualunque processo (es. creazione cliente, fornitore, gestore, ecc.) può chiamare una sola funzione per assicurarsi che il soggetto abbia il ruolo necessario, senza duplicare logica né gestire manualmente le race condition.

---

### 🧩 Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id   uuid,
    p_cd_int_ruolo  varchar
)
RETURNS integer
LANGUAGE plpgsql;
```

> 🔎 Ritorna sempre l’**`id` del record in `anagrafiche.soggetti_ruoli`** che rappresenta la coppia `(soggetto, ruolo)`.

---

### 🧠 Parametri di input

| Nome             | Tipo      | Obbl. | Descrizione                                                                                                    |
| ---------------- | --------- | :---: | -------------------------------------------------------------------------------------------------------------- |
| `p_soggetto_id`  | `uuid`    |  Sì   | Identificativo del soggetto in `anagrafiche.soggetti`. Non può essere `NULL`.                                  |
| `p_cd_int_ruolo` | `varchar` |  Sì   | **Codice interno del ruolo** (campo `config.tipi_ruoli.codice_interno`, es. `CL`, `FO`, `GE`, `BANK_B`, ecc.). |

---

### 📤 Valore restituito

La funzione restituisce:

| Tipo      | Descrizione                                                                                                                                 |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `integer` | L’`id` del record in `anagrafiche.soggetti_ruoli` che rappresenta la coppia `(p_soggetto_id, ruolo)` risolta a partire da `p_cd_int_ruolo`. |

* Se il legame **esiste già**, viene restituito l’`id` esistente.
* Se il legame **non esiste**, viene **inserito** un nuovo record e viene restituito il nuovo `id`.
* In caso di problemi di validazione o race condition anomale, la funzione **logga** tramite `script.fn_log_and_raise_error` e solleva eccezione.

---


### 🚨 Gestione errori & codici logici

La funzione **non usa `RAISE EXCEPTION` diretto**, ma delega a `script.fn_log_and_raise_error` la gestione centralizzata di log ed eccezioni.

Sono previsti almeno i seguenti codici logici:

* `E_SOGGETTO_NULL`
  ➜ `p_soggetto_id` non valorizzato. La funzione non può procedere.

* `E_COD_INT_RUOLO`
  ➜ il codice interno di ruolo `p_cd_int_ruolo` **non esiste** in `config.tipi_ruoli`.

* `E_SOGGETTI_RUOLI_RACE`
  ➜ situazione anomala: si è verificata una `unique_violation` in inserimento, ma il successivo `SELECT` non trova il record. Indica un potenziale problema di concorrenza/consistenza più profondo.

Questi codici possono essere mappati su messaggi utente più leggibili tramite il framework di messaggistica centralizzata (`config.messaggi_errore`, `fn_get_messaggio`, ecc.).

---

### 🧱 Dipendenze

**Tabelle:**

* `config.tipi_ruoli`

  * usata per risolvere `v_tipo_ruolo_id` a partire da `p_cd_int_ruolo`.

* `anagrafiche.soggetti_ruoli`

  * tabella di relazione che contiene i legami soggetto ↔ ruolo.
  * la funzione presuppone l’esistenza di un vincolo univoco logico tra `(soggetto_id, tipo_ruolo_id)` (es. indice/constraint `UNIQUE`).

**Funzioni:**

* `script.fn_log_and_raise_error(...)`

  * per log applicativo e sollevamento eccezioni standardizzato.

Eventuali altre funzioni di dominio (es. check sui ruoli) possono essere costruite **a valle**, riutilizzando l’ID restituito.

---

### 🧪 Esempi d’uso

#### 1) Assicurare che un soggetto diventi Cliente (`CL`)

```sql
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  => 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'::uuid,
    p_cd_int_ruolo => 'CL'
);
```

* Se il soggetto ha già il ruolo **Cliente**, viene restituito l’`id` esistente.
* Se non ce l’ha, viene creato un nuovo record in `anagrafiche.soggetti_ruoli`.

---

#### 2) Ottenere/creare il ruolo Gestore (`GE`) per un soggetto

```sql
SELECT sr_id := script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  => 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff'::uuid,
    p_cd_int_ruolo => 'GE'
);
```

L’`sr_id` restituito può essere usato immediatamente per creare record in tabelle dipendenti, ad esempio:

```sql
INSERT INTO anagrafiche.gestori (soggetto_ruolo_id, ...)
VALUES (sr_id, ...);
```

---

#### 3) Uso in procedure più complesse (pseudo-codice)

```plpgsql
DECLARE
    v_sr_cliente_id integer;
BEGIN
    v_sr_cliente_id := script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id  => v_soggetto_id,
        p_cd_int_ruolo => 'CL'
    );

    -- A valle posso creare un cliente, contatti, indirizzi, ecc.
    PERFORM anagrafiche.fn_create_cliente_from_soggetto_ruolo(v_sr_cliente_id, ...);
END;
```

---

### ✅ Best practice e note

* **Single source of truth per i legami soggetto ↔ ruolo**:
  usare sempre questa funzione nei flussi di creazione ruoli (Cliente, Fornitore, Gestore, ecc.) per evitare duplicazioni di logica e problemi di concorrenza.

* **Concorrenza**:
  la gestione di `unique_violation` con rilettura del record rende la funzione **safe in scenari multi-sessione**, a patto che esista un vincolo univoco coerente su `(soggetto_id, tipo_ruolo_id)`.

* **Validazione del dominio dei ruoli**:
  l’utilizzo di `config.tipi_ruoli.codice_interno` come ingresso rende più leggibile il codice applicativo, ma richiede che i codici interni siano **stabili e ben documentati**.

* **Log centralizzato**:
  tutte le anomalie sono convogliate in `script.fn_log_and_raise_error`, semplificando debug, auditing e generazione di messaggi utente.

---

### 💬 Commento catalogo suggerito

```sql
COMMENT ON FUNCTION script.fn_get_or_create_soggetto_ruolo(uuid, varchar) IS
  'Factory di dominio per ottenere o creare il legame soggetto↔ruolo in anagrafiche.soggetti_ruoli a partire da config.tipi_ruoli.codice_interno. Gestisce validazione parametri, risoluzione ruolo, concorrenza (unique_violation) e logging centralizzato tramite script.fn_log_and_raise_error.';
```

---

{% include-markdown "signature-core.md" %}
