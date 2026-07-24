## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_or_create_session_tx_id()`

> 👀 **Vedi anche**
>
Approfondimento Tabelle:   
>
[dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids)      
>
Approfondimento funzioni :    
>
[dbops.fn_generate_tx_id](/dbzero/dbops/funzioni/fn_generate_tx_id)    
> [script.uuid_nil](/dbzero/script/funzioni/uuid_nil)    
> [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn)    

La funzione **`dbops.fn_get_or_create_session_tx_id()`** fornisce un **UUID di transazione**, generandone uno nuovo solo se non già impostato. Tutte le operazioni della **stessa transazione** condividono così lo stesso **`tx_id`**, semplificando log, tracciabilità e correlazione.

---
### 🎯 Scopo Principale
(latest review 22-07-2026)
* **Unicità per transazione**: restituisce un `tx_id` costante per la durata della transazione. La GUC è impostata con `set_config(..., TRUE)`, quindi **locale**: ogni nuova transazione ottiene il proprio identificativo. È coerente col nome — un identificativo *di transazione* non deve sopravvivere alla transazione.
* **Fallback sicuro**: se il canale di log non è disponibile, restituisce l’UUID “nil” per non bloccare i processi.
* **Contesto centralizzato**: memorizza il `tx_id` nella GUC `dbops.tx_id` per gli accessi successivi.

> ### ⚖️ La regola che regge tutto: mai pubblicare un `tx_id` non registrato
>
> La validazione di [dbops.trgfn_tx_id_managed](/dbzero/dbops/manual/trgfn_tx_id_managed)
> scatta **solo sull’id pubblicato nella GUC**. Questa funzione pubblica quindi
> **esclusivamente** id che provengono dal registro `dbops.transaction_ids`; nei
> ripieghi restituisce la sentinella `script.uuid_nil()` **senza impostare la GUC**.
>
> Così l’invariante verificato dal trigger è vero **per costruzione** e il ramo
> «id non registrato» resta irraggiungibile in condizioni normali. Pubblicare un id
> assente dal registro significherebbe far fallire *ogni* scrittura tracciata
> successiva — vedi la nota di manutenzione in fondo.

---

### Parametri di Input

Questa funzione **non** richiede parametri. Tutta la logica utilizza variabili di sessione e la funzione di generazione:

| Parametro | Tipo | Default | Descrizione                                                   |
| --------- | ---- | ------- | ------------------------------------------------------------- |
| *nessuno* | –    | –       | La funzione auto-determina se creare o restituire il `tx_id`. |

---

### Flusso di Esecuzione Dettagliato

1. **Verifica connessione di logging**

   ```plpgsql
   PERFORM script.fn_ensure_logconn();
   ```

   Garantisce che il database sia pronto per eventuali chiamate `dblink` di audit o generazione remota.

2. **Lettura `dbops.tx_id` dalla sessione**

   ```plpgsql
   v_tx_id := current_setting('dbops.tx_id', TRUE)::UUID;
   ```

   * Se esiste e vale un UUID, lo restituisce subito.
   * In caso di eccezione (non settato), `v_tx_id` rimane `NULL`.

3. **Generazione on‑demand tramite `dblink`**

   ```plpgsql
   SELECT tx_id
     INTO v_tx_id
     FROM dblink(
       current_setting('dblink.log_connection', TRUE),
       $gen$
         SELECT dbops.fn_generate_tx_id(
           'dbops.fn_get_or_create_session_tx_id',
           jsonb_build_object('source','fn_get_or_create')
         )
       $gen$
     ) AS t(tx_id UUID);
   ```

   * La chiamata `dblink` esegue la function remota per creare e registrare un nuovo `tx_id`.
   * Imposta la GUC di sessione:

     ```plpgsql
     PERFORM set_config('dbops.tx_id', v_tx_id::text, TRUE);
     ```
   * **Casistiche di fallimento**: su qualunque eccezione di `dblink`, cattura l’errore e assegna:

     ```plpgsql
     v_tx_id := script.uuid_nil();
     ```

     restituendo un UUID “nil” (`00000000-0000-0000-0000-000000000000`).

4. **Restituzione del `tx_id`**

   ```plpgsql
   RETURN v_tx_id;
   ```

---


---

### Esempio di Utilizzo

```sql
-- Prima invocazione in sessione nuova:
SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id;
-- Restituisce e memorizza un nuovo UUID.

-- Invocazione successiva nella medesima sessione:
SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id;
-- Restituisce lo stesso UUID senza creare nuovi record.
```

---

### Vantaggi e Considerazioni

* **Tracciabilità coerente**: tutte le chiamate della stessa transazione condividono lo stesso `tx_id`, semplificando log e correlazione.
* **Performance**: riduce chiamate ridondanti a `fn_generate_tx_id`.
* **Fallback controllato**: restituisce `uuid_nil()` in caso di errori, utile in test o migrazioni dove non si desidera popolare la tabella `transaction_ids`.
* **Estendibilità**: può essere temporaneamente disattivata impostando manualmente `dbops.tx_id` su un valore predefinito o `000...0`, evitando side‑effect in contesti speciali.

---

### 🛠️ Nota di manutenzione — 22-07-2026

**Cosa è stato fatto.** Ripristinata la disciplina originale della funzione, persa
in una riscrittura del 22-11-2025. Migration `20260722-10`.

**Perché.** I tre rami di ripiego (canale non configurato, `dblink` che risponde
`NULL`, `dblink` in errore) generavano un `uuidv7()` **non registrato** in
`dbops.transaction_ids` e lo **pubblicavano** nella GUC, per di più con scope di
**sessione** anziché di transazione. Il trigger
[dbops.trgfn_tx_id_managed](/dbzero/dbops/manual/trgfn_tx_id_managed) non trovava
quell’id nel registro e **bloccava**: poiché Liquibase usa una sola connessione,
la prima scrittura tracciata avvelenava l’intera migrazione. Il sintomo osservato
era il fallimento di un seed su `dbops.coda_lavori_tipi` in un ambiente **senza
canale di log** (CI «standard, no provision»), ma il changeset colpito era
arbitrario: era semplicemente il primo a scrivere su una tabella tracciata.

**Le tre correzioni**, tutte con precedente nella versione originale:

| | prima (22-11-2025) | ora |
| --- | --- | --- |
| `script.fn_ensure_logconn()` in testa | rimossa: `myapp.log_with_dblink` ignorato | ripristinata |
| Ripiego senza canale | `uuidv7()` non registrato, **pubblicato** | `script.uuid_nil()`, **non pubblicato** |
| Scope della GUC | `set_config(..., false)` = sessione | `set_config(..., TRUE)` = transazione |

**Cosa si perde, e perché va bene.** Senza canale non c’è correlazione
per-transazione: tutte le righe portano `uuid_nil`. È il prezzo del disegno
originale. L’alternativa — un id registrato in locale — inquinerebbe in modo
permanente un registro dichiarato **immutabile**; e l’autonomia (una
registrazione che sopravvive al rollback) **non è ottenibile** senza un secondo
canale: il `dblink` punta allo stesso database, serve la connessione separata,
non la remotezza.

**Effetto collaterale da conoscere.** Con lo scope di nuovo locale, ogni
transazione genera un `tx_id` proprio: dove il canale è attivo, le righe in
`dbops.transaction_ids` crescono più di prima (una per transazione, non una per
connessione). È il comportamento corretto e quello originale.

**Nota per chi deve modificarla.** La funzione è iscritta in
`dbops.sec_functions_owner` con `required_owner = postgres`: un
`CREATE OR REPLACE` dal ruolo di migrazione fallisce con *«bisogna essere
proprietari della funzione»*. Il changeset `20260722-10` mostra il procedimento:
si dichiara temporaneamente nel registro il ruolo corrente, si invoca
[dbops.fn_sync_functions_owner](/dbzero/dbops/manual/fn_sync_functions_owner),
si sostituisce, si ripristina il registro e si risincronizza — tutto in un solo
changeSet, quindi in un’unica transazione.

Verifiche: `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql` (7 test).
Approfondimento: `brief-db-coerenza-tx-id-non-registrato.md`.

---

> **“`fn_get_or_create_session_tx_id` garantisce un unico punto di controllo per il transaction ID di transazione: non pubblica mai un id che non sia registrato.”**
