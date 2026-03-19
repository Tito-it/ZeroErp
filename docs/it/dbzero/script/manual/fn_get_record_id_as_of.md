## 📘 Documentazione Concettuale – Funzione `script.fn_get_record_id_as_of`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
[script.fn_get_snapshot_as_of](/dbzero/script/funzioni/fn_get_snapshot_as_of) *(snapshot completo)*

La funzione **`script.fn_get_record_id_as_of(p_schema TEXT, p_table TEXT, p_id TEXT, p_fk_col TEXT, p_as_of TIMESTAMP)`** restituisce il **testo dell’ID** (`TEXT`) del record valido in un dato istante, **cercando esclusivamente nella tabella di storico**. In assenza di uno snapshot valido, restituisce `NULL` senza eseguire alcun fallback sulla tabella operativa.

---
### 🎯 Scopo Principale
* **Recupero rapido dell’ID in uno snapshot**: ottenere solo l’identificativo del record (`id`) valido alla data/ora specificata, senza dover deserializzare tutto il JSON.
* **Ottimizzazione delle query**: operazione leggera nel caso serva solo l’ID, utile per controlli o join condizionali su storico.

---

### Collegamenti e Dipendenze

* **Tabella di storico**: `storico.<p_table>` deve esistere e seguire lo schema di storicizzazione unificato.
* **Log errori**: utilizza `script.fn_log_and_raise_error` per trattare ogni errore SQL imprevisto con un log dettagliato e abort.

---

### Parametri di Input

| Nome       | Tipo        | Descrizione                                                                                  |
| ---------- | ----------- | -------------------------------------------------------------------------------------------- |
| `p_schema` | `TEXT`      | Schema della tabella operativa (non usato nel lookup, ma valido per contesto ed errori).     |
| `p_table`  | `TEXT`      | Nome della tabella operativa (e della corrispondente tabella `storico.<p_table>`).           |
| `p_id`     | `TEXT`      | Valore della chiave primaria del record originario, passato come testo.                      |
| `p_fk_col` | `TEXT`      | Nome della colonna FK in `storico.<p_table>` che punta a `p_table.id` (es. `'soggetto_id'`). |
| `p_as_of`  | `TIMESTAMP` | Istante di validità (UTC), determina quale snapshot considerare.                             |

---

### Flusso Logico

1. **Verifica metadati**

   * Ricava dinamicamente il tipo di `p_fk_col` in `storico.<p_table>` da `pg_attribute`.
   * Se non trovato, chiama `fn_log_and_raise_error` e abortisce.

2. **Query dello storico**

   ```plpgsql
   BEGIN
     EXECUTE format(
       'SELECT %I::text
        FROM %I.%I
        WHERE %I = $1::%s
          AND valid_from <= $2
          AND (valid_to > $2 OR valid_to IS NULL)
        ORDER BY valid_from DESC
        LIMIT 1',
       'id', v_hist_schema, v_hist_table, p_fk_col, v_pk_type
     ) INTO v_id
     USING p_id, p_as_of::timestamptz;
   EXCEPTION WHEN OTHERS THEN
     PERFORM script.fn_log_and_raise_error(...);
   END;
   ```

   * Se la query genera errori, esegue log + abort.
   * Se nessun errore ma nessun risultato, `v_id` rimane `NULL`.

3. **Restituzione**

   * Restituisce `v_id` (il testo dell’ID dello snapshot) o `NULL`.

---

### Vantaggi Operativi

* **Performance**: evita la deserializzazione JSONB quando serve solo l’ID.
* **Semplicità**: non crea dipendenze da dati operativi attuali, è self‑contained nello storico.
* **Tracciabilità**: ogni errore di query è tracciato con contesto completo grazie a `fn_log_and_raise_error`.

---

> **“`fn_get_record_id_as_of` è la scorciatoia ideale per recuperare solo l’ID di uno snapshot, mantenendo alta performance e tracciabilità.”**

---