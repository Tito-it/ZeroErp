## 📚 Documentazione Funzione: `dbops.fn_foreign_keys_info`

> 👀 **Vedi anche:**
>
[information_schema.table_constraints](https://www.postgresql.org/docs/current/infoschema-table-constraints.html)
> [information_schema.key_column_usage](https://www.postgresql.org/docs/current/infoschema-key-column-usage.html)
> [information_schema.constraint_column\_usage](https://www.postgresql.org/docs/current/infoschema-constraint-column-usage.html)

---
### 🎯 Scopo Principale
`dbops.fn_foreign_keys_info(tabella)` restituisce una vista unificata di **tutte le relazioni tramite chiavi esterne** (
foreign key) che coinvolgono la tabella specificata, distinguendo tra:

* **Incoming FK** → altre tabelle che puntano alla tabella indicata.
* **Outgoing FK** → chiavi esterne definite nella tabella stessa verso altre tabelle.

---

### Firma

```sql
FUNCTION dbops.fn_foreign_keys_info(tabella text)
RETURNS TABLE (
  relazione       text,           -- 'incoming' o 'outgoing'
  constraint_name text,           -- nome del vincolo
  source_table    text,           -- tabella sorgente
  source_column   text,           -- colonna sorgente
  target_table    text,           -- tabella di destinazione
  target_column   text            -- colonna di destinazione
)
```

---

### Comportamento

1. **Incoming FK**

   * Interroga `information_schema` per trovare tutte le FK in cui la tabella indicata è la **destinazione** (`ccu.table_name = tabella`).
   * Restituisce `relazione = 'incoming'` con nome del vincolo, tabella/colonna sorgente e tabella/colonna di destinazione.

2. **Outgoing FK**

   * Interroga `information_schema` per trovare tutte le FK definite **nella tabella specificata** (`tc.table_name = tabella`).
   * Restituisce `relazione = 'outgoing'` con nome del vincolo, tabella/colonna sorgente e tabella/colonna di destinazione.

3. Unisce i risultati delle due query con `RETURN QUERY` in un'unica tabella di output.

---

### Esempio di utilizzo

```sql
-- Trova tutte le FK in cui è coinvolta la tabella 'clienti'
SELECT *
FROM dbops.fn_foreign_keys_info('clienti');
```

**Output di esempio:**

```
 relazione | constraint_name             | source_table | source_column | target_table | target_column
-----------+-----------------------------+--------------+---------------+--------------+--------------
 incoming  | fk_ordini_clienti           | ordini       | cliente_id    | clienti      | id
 outgoing  | fk_clienti_comuni           | clienti      | comune_id     | comuni       | id
```

---

### Note operative

* La funzione lavora su `information_schema`, quindi è indipendente dallo schema logico (funziona su tutte le tabelle visibili all'utente).
* I nomi delle tabelle/colonne restituiti sono in formato semplice (senza schema). Per distinguere tabelle con lo stesso nome in schemi diversi, può essere utile estendere la funzione includendo `table_schema`.
* Utile per **documentazione automatica**, **analisi di impatto** (impact analysis) e **reverse engineering** del modello dati.

---

{% include-markdown "signature-core.md" %}
