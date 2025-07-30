# 📗 Guida Tecnica – Implementazione di un Unico Transaction ID in Zero ERP


> 📋 ***Destinatari***: sviluppatori database, sviluppatori backend

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids)      
> - [config.parameters](/dbzero/config/tabelle/parameters)      

>
> Approfondimento funzioni :    
> - [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id)    
> - [dbops.fn_generate_tx_id](/dbzero/dbops/funzioni/fn_generate_tx_id)   
> - [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)   
>     **Esempio di utilizzo :**      
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)    


## 1. Introduzione

In Zero ERP è essenziale poter **correlare** tutte le operazioni legate a una singola transazione (inserimenti, aggiornamenti, cancellazioni) attraverso diverse tabelle e componenti. Questa guida spiega:

* Il **perché** della scelta di un identificativo di transazione centralizzato (`tx_id`).
* L’**architettura** e i **componenti** coinvolti.
* Le **modalità di integrazione** sia lato database (trigger, function) sia lato backend.
* Le **linee guida** per implementazione, test e manutenzione.

---

## 2. Motivazioni e Obiettivi

1. **Tracciabilità completa**: poter ricostruire il flusso di una transazione in un’unica vista cronologica.
2. **Coerenza cross-tabella**: garantire che ogni riga coinvolta in un’operazione condivida lo stesso `tx_id`.
3. **Supporto audit e debugging**: semplificare ricerca di errori e analisi delle performance.
4. **Flessibilità**: permettere bypass o personalizzazione in fase di test, migrazione o debug.

---

## 3. Architettura e Componenti

### 3.1 Tabella Centrale

* **`dbops.transaction_ids`**: registro master di tutti i `tx_id`. Ogni record memorizza UUID, timestamp, contesto di generazione.

### 3.2 Funzioni PL/pgSQL

* **`fn_generate_tx_id(...)`**: genera e inserisce un nuovo `tx_id`, restituendolo.
* **`fn_get_or_create_session_tx_id()`**: recupera o crea, se mancante, il `tx_id` di sessione tramite GUC e dblink.
* **`fn_get_or_create_session_tx_id`** è consigliata per uso lato backend.

### 3.3 Trigger e Trigger Functions

* **`trgfn_tx_id_managed()`**: centralizza logica di controllo, bypass, validazione e assegnazione `NEW.tx_id`. È attaccata via trigger **`BEFORE INSERT OR UPDATE`** su tabelle che contengono il campo `tx_id`.
* **Pro**: garantisce coerenza automatica senza dipendere dal client.
* **Contro**: può limitare rapidità di sviluppo e complicare rollback di test.

---

## 4. Modalità di Integrazione

### 4.1 Lato Database con Trigger

1. **DDL**: aggiungere colonna `tx_id UUID NOT NULL` in ogni tabella.
2. **Trigger**:

   ```sql
   CREATE TRIGGER trg_assign_tx_id ON schema.my_table
     BEFORE INSERT OR UPDATE
     FOR EACH ROW
     EXECUTE FUNCTION dbops.trgfn_tx_id_managed();
   ```
3. **Vantaggi**: operazioni garantite lato DB, nessun intervento lato client.
4. **Svantaggi**: potenziali errori mascherati, dipendenze DB forti.

### 4.2 Lato Backend con Function

1. **Colonna DDL**: `tx_id UUID NOT NULL` su tabelle.
2. **Chiamata esplicita**: prima di operazioni SQL, backend esegue:

   ```sql
   SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id;
   ```
3. **Iniezione**: popola il campo `tx_id` nelle istruzioni `INSERT/UPDATE`.
4. **Vantaggi**: completa visibilità e controllo lato applicazione; facile debugging.
5. **Svantaggi**: responsabilità di implementazione distribuita tra team.

> **Scelta consigliata**: per ambienti di sviluppo/test o architetture microservizi, preferire la gestione da backend; in contesti monolitici DB-centrici, adottare trigger.

---

## 5. Linee Guida per l’Implementazione

1. **Estensione DDL**: aggiungere colonna `tx_id` e trigger o documentare chiamata function.
2. **Configurazione Bypass**: utilizzare parametro `tx_id_bypass_enabled` e GUC `app.bypass_tx_id_check` per disabilitare logica in contesti speciali.
3. **Test & QA**:

   * Verificare che ogni operazione in una sessione condivida lo stesso `tx_id`.
   * Simulare errori `dblink` e controllare fallback a `uuid_nil()`.
4. **Documentazione**: includere esempi di codice lato backend (es. repository, servizi) e script SQL di verifica.

---

## 6. Esempi di Codice Backend (Pseudo)

```js
// Node.js + pg
async function withTxId(client, callback) {
  // Recupera o crea tx_id
  const res = await client.query(`SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id`);
  const txId = res.rows[0].tx_id;

  // Esegui operazioni con tx_id
  await callback(txId);
}

await withTxId(dbClient, async (txId) => {
  await dbClient.query(
    `INSERT INTO orders (customer_id, total, tx_id) VALUES ($1,$2,$3)`,
    [custId, total, txId]
  );
  // Altre query...
});
```

---

## 7. Conclusioni e Raccomandazioni

* **Coerenza**: definire uno standard di implementazione (trigger vs function) e applicarlo su tutte le tabelle.
* **Collaborazione**: condividere la guida con team backend e DB per evitare disallineamenti.
* **Manutenzione**: tenere aggiornate le trigger functions e le funzioni helper in caso di nuovi requisiti.

> 🧠 **“Scegliere il giusto compromesso tra automazione DB e controllo applicativo è fondamentale: questa guida aiuta a definire policy chiare e processi replicabili in Zero ERP.”**

---


---
{% include-markdown "signature-core.md" %}
