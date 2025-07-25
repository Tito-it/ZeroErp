## 📘 Documentazione Concettuale – Tabella `storico.stradario`

> 👀 **Vedi anche**
>
> Approfondimeto Tabelle:   
> - [config.stradario](/dbzero/config/tabelle/stradario)    
>
> Approfondimeto Funzioni:   
> - [config.trgfn_stradario_upd_dlt_storico_stradario](/dbzero/config/funzioni/trgfn_stradario_upd_dlt_storico_stradario)   
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)    

La tabella **`storico.stradario`** archivia la cronologia delle modifiche alle vie registrate in `config.stradario`, garantendo la tracciabilità di tutte le operazioni di update e delete.

---

### 🎯 Scopo Principale

* **Audit Trail**: Conservare una traccia completa di ogni modifica o cancellazione effettuata su `config.stradario`.
* **Versioning dei record**: Permettere la ricostruzione dello stato di una via in un dato momento, grazie ai campi `valid_from` e `valid_to`.
* **Riproduzione dello schema**: Utilizzare il campo **`snapshot`** (JSONB) per salvare tutti i dettagli di `config.stradario` al momento dell’operazione, anche a fronte di evoluzioni dello schema.
* **Classificazione delle operazioni**: Impiegare **`tipo_operazione_id`** (1=insert iniziale, 2=update, 3=delete) e **`change_type`** (A=Active, S=Suppressed, F=Fused, D=Divided) per distinguere rapidamente la natura del cambiamento.

---

### 🔄 Meccanismo di Popolamento

1. **Trigger di storicizzazione**
   La trigger function `config.trgfn_stradario_upd_dlt_storico_stradario()` si attiva **BEFORE UPDATE OR DELETE** su `config.stradario` quando il flag `storicizza = TRUE`.
2. **Replica dello stato iniziale**
   Al primo update o delete, viene creato automaticamente uno **snapshot iniziale** (tipo_operazione_id = 1) se non esisteva un record storico precedente.
3. **Chiusura e creazione nuovi snapshot**

   * **UPDATE**: chiude il record storico aperto impostando `valid_to = CURRENT_DATE`, poi inserisce un **snapshot aggiornato** (tipo_operazione_id = 2) con `valid_from = CURRENT_DATE` e `valid_to = NULL`.
   * **DELETE**: chiude eventuale snapshot aperto e inserisce un **snapshot finale** (tipo_operazione_id = 3) con `valid_from = valid_to = CURRENT_DATE`.
4. **Campo `snapshot`**

   * Memorizza in JSONB **tutti** i campi di `config.stradario` al momento dell’operazione, inclusi `descrizione_via`, riferimenti a `comune_id`, `codice_postale_id` e altri attributi.
   * **Vantaggio**: garantisce flessibilità e future-proof rispetto a modifiche di schema.
   * **Costo**: maggiore occupazione di spazio e impatto sulle performance di I/O.


---

### 🔖 Esempio di Trigger DDL

```sql
DROP TRIGGER IF EXISTS trg_stradario_upd_dlt_storico_stradario
  ON config.stradario;

CREATE TRIGGER trg_stradario_upd_dlt_storico_stradario
  BEFORE UPDATE OR DELETE
  ON config.stradario
  FOR EACH ROW
  WHEN (NEW.storicizza = TRUE OR OLD.storicizza = TRUE)
  EXECUTE FUNCTION config.trgfn_stradario_upd_dlt_storico_stradario();
```

---

### 💡 Vantaggi Operativi

* **Storico granulare**: ogni modifica è catturata integralmente grazie al JSONB `snapshot`, senza richiedere sincronizzazione manuale dello schema.
* **Filtro temporale**: i campi `valid_from`/`valid_to` consentono interrogazioni su periodi e versioni specifiche.
* **Analisi semplificata**: `tipo_operazione_id` e `change_type` agevolano reportistica e individuazione rapida degli eventi.
* **Resilienza**: in caso di errori di storicizzazione, il trigger logga l’eccezione senza bloccare l’operazione principale.

---

> 🧠 **“Con `storico.stradario`, Zero ERP offre un audit trail completo per le vie comunali, con flessibilità JSONB e controllo granulare tramite flag di storicizzazione.”**


