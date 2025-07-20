## 📘 Documentazione Concettuale – Trigger Function `config.trgfn_comuni_upd_dlt_storico_comuni()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> * [anagrafiche.comuni](/dbzero/anagrafiche/tabelle/comuni)    
> * [storico.comuni](/dbzero/anagrafiche/tabelle/comuni)   
>
> Approfondimento funzioni:   
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

### 🎯 Scopo Principale

La trigger function **`config.trgfn_comuni_upd_dlt_storico_comuni()`** gestisce la **storicizzazione** delle modifiche e cancellazioni sui record della tabella **`anagrafiche.comuni`**, garantendo:

* Tracciatura completa degli snapshot storici delle righe.
* Chiusura dei snapshot aperti prima di eventuali nuove versioni.
* Creazione di record storico iniziali e finali con dettagli operativi.

---

### ⚙️ Obiettivi e Ruolo

1. **Chiusura snapshot esistenti**

   * In `UPDATE` o `DELETE` con flag `storicizza = TRUE`, chiude eventuali record in `storico.comuni` con `valid_to IS NULL` aggiornando `valid_to` alla data corrente.
2. **Creazione snapshot iniziale**

   * Se non esisteva uno snapshot aperto per quel record, inserisce il primo snapshot con i valori originali (`OLD`) e `tipo_operazione_id = 1`.
3. **Snapshot aggiornato o finale**

   * Per `UPDATE`, aggiunge un nuovo snapshot con i valori aggiornati (`NEW`) e `tipo_operazione_id = 2`.
   * Per `DELETE`, registra un snapshot finale con `tipo_operazione_id = 3`.
4. **Gestione errori**

   * In caso di eccezioni, invoca `script.fn_log_and_raise_error` per loggare l’errore garantendo comunque la prosecuzione dell’operazione.
5. **Pass-through**

   * Se `storicizza` non è `TRUE` o l’operazione è un `INSERT`, restituisce semplicemente il record senza storicizzazione.

---

### 🔍 Flusso di Esecuzione Dettagliato

1. **Inizializzazione variabili**

   ```plpgsql
   v_snapshot_aperto BOOLEAN := FALSE;
   v_current_date DATE := CURRENT_DATE;
   v_rowcount INTEGER := 0;
   ```
2. **Branch UPDATE**

   ```plpgsql
   IF TG_OP = 'UPDATE' AND NEW.storicizza IS TRUE THEN
   ```

   * **Fase 1**: chiude snapshot aperto (`valid_to IS NULL`) per `OLD.id`.
   * **Fase 2**: se nessuno era chiuso (`v_snapshot_aperto = FALSE`), inserisce snapshot iniziale con `OLD` e `tipo_operazione_id = 1`.
   * **Fase 3**: inserisce snapshot aggiornato con `NEW` e `tipo_operazione_id = 2`.
   * Reset flag `NEW.storicizza := FALSE` e `RETURN NEW`.
3. **Branch DELETE**

   ```plpgsql
   ELSIF TG_OP = 'DELETE' AND OLD.storicizza IS TRUE THEN
   ```

   * **Fase 1**: chiude snapshot aperto per `OLD.id`.
   * **Fase 2**: se non chiuso, inserisce snapshot iniziale con `OLD` e `tipo_operazione_id = 1`.
   * **Fase 3**: inserisce snapshot di cancellazione con `OLD` e `tipo_operazione_id = 3`.
   * `RETURN OLD`.
4. **Default**

   ```plpgsql
   RETURN COALESCE(NEW, OLD);
   ```

   * Per `INSERT` o operazioni senza `storicizza`, restituisce il record senza storicizzazione.
5. **Gestione eccezioni**

   * Ogni blocco di storicizzazione cattura `EXCEPTION WHEN OTHERS`, logga l’errore e prosegue restituendo il record originale.

---

### 🔖 Esempio di Trigger DDL

```sql
DROP TRIGGER IF EXISTS trg_comuni_upd_dlt_storico_comuni
  ON anagrafiche.comuni;

CREATE TRIGGER trg_comuni_upd_dlt_storico_comuni
  BEFORE UPDATE OR DELETE
  ON anagrafiche.comuni
  FOR EACH ROW
  EXECUTE FUNCTION config.trgfn_comuni_upd_dlt_storico_comuni();
```

---

### 💡 Vantaggi Operativi

* **Storico completo**: registra ogni modifica e cancellazione con timestamp e snapshot dettagliati.
* **Integrità dei dati**: evita sovrapposizioni di snapshot grazie al controllo e chiusura preventiva.
* **Audit e troubleshooting**: in caso di errori di storicizzazione, logga dettagliatamente senza bloccare le operazioni DML.
* **Flessibilità**: permette estensioni per ulteriori tipi di operazioni o condizioni di storicizzazione.

---

> 🧠 **“`trgfn_comuni_upd_dlt_storico_comuni` offre una soluzione robusta di versioning dei dati anagrafici, garantendo audit trail e consistenza storica senza interrompere il normale flusso applicativo.”**