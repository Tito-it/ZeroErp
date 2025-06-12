## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_stradario_upd_dlt_storico_stradario()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:  
>  - [storico.stradario](/dbzero/storico/tabelle/stradario)
>  - [config.stradario](/dbzero/config/tabelle/stradario)  
>  - [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)
>
> Approfondimenti funzioni:   
> - [config.trg_stradario_upd_dlt_storico_stradario](/dbzero/config/manual/trg_stradario_upd_dlt_storico_stradario)


La trigger function **`config.trgfn_stradario_upd_dlt_storico_stradario()`** gestisce la storicizzazione automatica dei record di **`config.stradario`** su operazioni di **UPDATE** (quando il flag `storicizza` è impostato) e **DELETE**, garantendo la creazione di snapshot storici con validità temporale.

---

### 🎯 Scopo Principale

* **Storicizzazione automatica**
  Creare snapshot storici dei dati di `stradario` su modifiche e cancellazioni, mantenendo traccia delle variazioni nel tempo.
* **Centralizzare la logica di versioning**
  Evitare duplicazione di codice e garantire coerenza nella gestione dello storico.

---

### 🔍 Parametri e Contesto

* **Nessun parametro**: opera direttamente sui record `OLD` e `NEW` forniti dal trigger.

* **Trigger associati**: va utilizzata con `BEFORE UPDATE OR DELETE` sulla tabella:

  ```sql
  CREATE TRIGGER trg_stradario_upd_dlt_storico
    BEFORE UPDATE OR DELETE ON config.stradario
    FOR EACH ROW
    EXECUTE FUNCTION config.trgfn_stradario_upd_dlt_storico_stradario();
  ```

* **Campi interessati nella tabella `config.stradario`**:

  * `id`
  * `stradario_generale_id`
  * `comune_id`
  * `codice_postale_id`
  * `descrizione_via` (ricavata da `config.stradario_generale`)
  * `geoloc`
  * `extra_info`
  * `storicizza` (boolean)

---

### ⚙️ Comportamento

#### 1. UPDATE (con `NEW.storicizza = true`)

1. **Chiusura snapshot aperto o creazione**

   ```plpgsql
   IF EXISTS (
     SELECT 1
       FROM storico.stradario
      WHERE stradario_id = OLD.id
        AND valid_to IS NULL
   ) THEN
     -- Chiude lo snapshot aperto
     UPDATE storico.stradario
        SET valid_to = CURRENT_DATE
      WHERE stradario_id = OLD.id
        AND valid_to IS NULL;
   ELSE
     -- Crea uno snapshot da OLD
     INSERT INTO storico.stradario (
       stradario_id, stradario_generale_id, comune_id, codice_postale_id,
       descrizione_via, geoloc, extra_info, valid_to,
       data_insert, user_insert
     ) VALUES (... OLD ..., CURRENT_DATE, NOW(), CURRENT_USER);
   END IF;
   ```
2. **Inserimento snapshot del nuovo stato**

   ```plpgsql
   INSERT INTO storico.stradario (
     stradario_id, stradario_generale_id, comune_id, codice_postale_id,
     descrizione_via, geoloc, extra_info, valid_from,
     data_insert, user_insert
   ) VALUES (... NEW ..., CURRENT_DATE, NOW(), CURRENT_USER);
   ```
3. **Reset del flag di storicizzazione**

   ```plpgsql
   NEW.storicizza := false;
   ```
4. **Ritorno**

   ```plpgsql
   RETURN NEW;
   ```

#### 2. DELETE

1. **Chiusura snapshot aperto o creazione di uno "finale"**

   ```plpgsql
   IF EXISTS (...) THEN
     -- Chiude lo snapshot aperto
   ELSE
     -- Crea uno snapshot finale da OLD con `valid_to = CURRENT_DATE`
   END IF;
   ```
2. **Ritorno**

   ```plpgsql
   RETURN OLD;
   ```

#### 3. Altre operazioni (`UPDATE` senza flag, `INSERT`, ecc.)

* **UPDATE senza `storicizza`**: restituisce `NEW` senza modifiche allo storico.
* **INSERT**: restituisce `NEW` (nessuna storicizzazione automatica).

---

### 🔒 Valore di Ritorno

* **`trigger`**
  Restituisce il record modificato (`NEW` o `OLD`) in base all'operazione, dopo aver eventualmente gestito la storicizzazione.

---

### 💡 Vantaggi Operativi

* **Tracciabilità storica**
  Mantiene un audit completo delle variazioni sui dati di `stradario`.
* **Riduzione del boilerplate**
  Logica di versioning unificata in una sola funzione.
* **Coerenza**
  Comportamento uniforme su UPDATE e DELETE.
* **Facilità di manutenzione**
  Estendibile ad altre tabelle modificando solo trigger e schema di destinazione.

---

> 🧠 **“Utilizzare una trigger function unica per la storicizzazione semplifica gestione e manutenzione, migliorando la governance dei dati.”**
