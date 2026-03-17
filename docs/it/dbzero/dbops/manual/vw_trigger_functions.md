## 📘 Documentazione Concettuale – View `dbops.vw_trigger_functions`

> 👀 **Vedi anche**
>
Catalogo trigger PostgreSQL (`pg_trigger`, `pg_class`, `pg_proc`, `pg_namespace`)
>
Altre view di catalogazione:  
>
[dbops.vw_catalogo_oggetti](/dbzero/dbops/views/vw_catalogo_oggetti)  
> [dbops.vw_function_list](/dbzero/dbops/views/vw_function_list)  

La view **`dbops.vw_trigger_functions`** elenca tutti i trigger definiti negli schemi del database, indicando la tabella di appartenenza, il nome del trigger, la funzione associata e la definizione completa della funzione. Filtra i trigger interni di sistema lasciando solo quelli utente.

---

### 🎯 Scopo Principale

* Fornire una panoramica centralizzata dei trigger utente presenti in ogni tabella del database.
* Rendere immediatamente accessibili:

  * Schema e tabella di appartenenza
  * Nome del trigger
  * Funzione richiamata dal trigger
  * Testo completo della definizione della funzione trigger (utile per review e debugging)

---

### Definizione (DDL)

```sql
CREATE OR REPLACE VIEW dbops.vw_trigger_functions AS
SELECT
  n.nspname                     AS schema,
  cls.relname                   AS tabella,
  trg.tgname                    AS nome_trigger,
  p.proname                     AS nome_funzione,
  pg_get_functiondef(p.oid)     AS definizione_funzione
FROM pg_trigger trg
JOIN pg_class cls ON trg.tgrelid = cls.oid
JOIN pg_proc p   ON trg.tgfoid = p.oid
JOIN pg_namespace n ON n.oid = cls.relnamespace
WHERE NOT trg.tgisinternal
ORDER BY n.nspname, cls.relname, trg.tgname;
```

**Owner**: `postgres`

**Commento**: Vista dei trigger utente con dettagli sulla funzione invocata e definizione del codice della funzione.

---

### Colonne e Significato

| Colonna                | Descrizione                                                                       |
| ---------------------- | --------------------------------------------------------------------------------- |
| `schema`               | Schema in cui risiede la tabella (owner del trigger)                              |
| `tabella`              | Nome della tabella associata al trigger                                           |
| `nome_trigger`         | Nome del trigger così come definito nel catalogo                                  |
| `nome_funzione`        | Nome della funzione eseguita dal trigger                                          |
| `definizione_funzione` | Testo completo della definizione PL/pgSQL della funzione (inclusi header e corpo) |

---

### Esempi di Utilizzo

1. **Elencare tutti i trigger di una specifica tabella**:

   ```sql
   SELECT nome_trigger, nome_funzione
     FROM dbops.vw_trigger_functions
    WHERE tabella = 'config.iva';
   ```

2. **Visualizzare la definizione di un trigger particolare**:

   ```sql
   SELECT definizione_funzione
     FROM dbops.vw_trigger_functions
    WHERE nome_trigger = 'trg_upd_iva_audit_data_user';
   ```

3. **Contare i trigger per schema**:

   ```sql
   SELECT schema, COUNT(*) AS tot_trigger
     FROM dbops.vw_trigger_functions
    GROUP BY schema;
   ```

---

### Vantaggi Operativi

* **Code review**: facilita l’ispezione del codice PL/pgSQL associato ai trigger.
* **Manutenzione**: consente di individuare rapidamente trigger obsoleti o duplicati.
* **Documentazione**: serve come riferimento unico per tutti i trigger definiti nel database.

---

> **“Una view centralizzata dei trigger migliora la governabilità e semplifica il controllo della logica di business implementata a livello di database.”**
