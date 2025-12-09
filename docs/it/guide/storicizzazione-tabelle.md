# 📗 Guida Tecnica – Storicizzazione delle Tabelle in Zero ERP
> (latest review 08-12-25)
> 
> 📋 **Destinatari:** sviluppatori database, sviluppatori backend
>
> 👀 **Vedi anche:**
>
> Per come applicare queste best practice nelle migrazioni, consulta il documento:
>
> * [Linee Guida SQL](/linee-guida-sql)
>
> Approfondimento funzioni:
>
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)
> * [script.fn_get_snapshot_as_of](/dbzero/script/funzioni/fn_get_snapshot_as_of) *(restituisce lo snapshot JSONB a un dato istante)*
> * [script.fn_get_record_id_as_of ](/dbzero/script/funzioni/fn_get_record_id_as_of ) *(restituisce solo l’ID del record storico a un dato istante)*


---

Ogni entità che richiede **versioning** e **audit trail** in Zero ERP utilizza un modello di storico **unificato**. Questo approccio facilita la gestione delle modifiche e garantisce consistenza tra le tabelle operative e quelle di storico.

---

## 🎯 Scopo Principale

* **Tracciabilità completa** delle operazioni di **INSERT**, **UPDATE** e **DELETE** su tabelle chiave.
* **Flessibilità di schema**: supportare evoluzioni future senza dover modificare la struttura dello storico.
* **Centralizzazione della logica** di storicizzazione in una funzione generic (`trgfn_storico_generic`).

---

## 🛠️ Colonne Standard per le Tabelle di Storico

Tutte le tabelle di storico in Zero ERP devono avere:

* **`id`**: chiave primaria autonumerica (BIGINT).
* **`valid_from` / `valid_to`**: date che definiscono l’intervallo di validità dello snapshot.
* **`snapshot` (JSONB)**: contiene una copia di tutti i campi del record originale al momento dell’evento.
* **`tipo_operazione`** (SMALLINT): 1=Snapshot iniziale, 2=UPDATE, 3=DELETE.
* **`change_type`** (CHAR): classificazione rapida `A/U/D`.
* **`data_insert` / `user_insert`**: timestamp e utente che hanno creato lo snapshot.
* **`tx_id`** (UUID): identifica la transazione di business che ha generato lo snapshot.
* **`<entita>_id`**: FK verso la tabella originale.

---

## 🔍 Perché JSONB per il campo `snapshot`

1. **Evoluzione dello schema**: aggiunta o rimozione di colonne nella tabella sorgente non richiede modifiche alle colonne di storico.
2. **Integrità dei dati**: garantisce che ogni snapshot rifletta esattamente lo stato dell’intero record, senza omissioni.
3. **Query ad hoc**: permette estrazioni puntuali di attributi storici con funzioni JSON SQL (es. `snapshot->>'campo'`).

> **Trade‑off**:
>
> * Maggiore occupazione di spazio.
> * Possibili impatti di performance per query su JSONB (ottimizzabili con GIN index).

---

## 🔄 Trigger Generic di Storico

La funzione **`script.trgfn_storico_generic(fk_column)`** gestisce:

1. **Chiusura** di eventuali snapshot aperti (`valid_to = CURRENT_DATE`).
2. **Inserimento snapshot iniziale** (solo se non esisteva) con `valid_from = '1950-01-01'`.
3. **Inserimento snapshot finale** con `valid_from = CURRENT_DATE` e `tipo_operazione` appropriato.
4. **Logging degli errori** con `script.fn_log_and_raise_error`, senza bloccare la DML.

**Esempio DDL**:

```sql
CREATE TRIGGER trg_storico_<entita>
  AFTER UPDATE OR DELETE ON <schema>.<entita>
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_storico_generic('<entita>_id');
```

> **Importante Naming Convention**: il trigger di storico deve chiamarsi con prefisso `trg_Z90_<tabella>_storico_upd_dlt` (es. `trg_Z90_stradario_storico_upd_dlt`). Questo garantisce:
>
> * Esecuzione per ultima, grazie all’ordinamento alfabetico.
> * Compatibilità con gli altri trigger precedenti nell’ordine di firing.

---

## 💡 Vantaggi per lo Sviluppatore

* **Rapidità di adozione**: per attivare lo storico su una nuova tabella basta definire la tabella di storico con lo schema standard e creare il trigger generic rispettando la convenzione di naming.
* **Manutenibilità**: la logica di storicizzazione evolve in un solo punto (la funzione generic), senza dover modificare ogni trigger function.
* **Controllo degli errori**: la funzione generic cattura e logga le eccezioni, rendendo più semplice il debug.
* **Reporting**: il campo `snapshot` e i date range consentono costruire report storici avanzati senza join complessi.

---

> 🧠 **“Adottando il modello di storico unificato, Zero ERP semplifica la gestione della storia dei dati, riduce la duplicazione di logica e garantisce uno sviluppo rapido e sicuro.”**

---

{% include-markdown "signature-core.md" %}
