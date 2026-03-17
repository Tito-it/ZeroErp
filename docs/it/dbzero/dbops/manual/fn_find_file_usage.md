## 📘 Documentazione Concettuale – Funzione `dbops.fn_find_file_usage`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:   
>
[dbops.fn_search_column_usage](/dbzero/dbops/funzioni/fn_search_column_usage)     
> [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage)     


La funzione **`dbops.fn_find_file_usage(p_target_table regclass)`** individua tutte le constraint di tipo foreign key che puntano alla tabella specificata in input, restituendo per ciascuna:
- La tabella che contiene la FK
- La colonna FK stessa
- La tabella referenziata (che sarà sempre la stessa in tutti i record, ovvero `p_target_table`)
- La colonna PK referenziata

---

### 🎯 Scopo Principale

* **Analisi d’impatto**  
  Identificare rapidamente tutte le relazioni di FK verso una tabella, utile per valutare dipendenze e conseguenze di modifiche, cancellazioni o refactoring di schema.

* **Documentazione automatica**  
  Fornire un’elenco puntuale di constraint FK anziché esplorare manualmente il catalogo di sistema.

---

### Parametri

| Nome                | Tipo      | Descrizione                                                                 |
| ------------------- | --------- | --------------------------------------------------------------------------- |
| `p_target_table`    | `regclass`| Nome (con schema) della tabella di cui cercare le FK in ingresso.          |

---

### Struttura del risultato

| Colonna            | Tipo      | Descrizione                                                                 |
| ------------------ | --------- | --------------------------------------------------------------------------- |
| `table_with_fk`    | `regclass`| Schema e nome della tabella che definisce la foreign key.                  |
| `fk_column`        | `name`    | Nome della colonna all’interno di `table_with_fk` che è la foreign key.     |
| `referenced_table` | `regclass`| Tabella referenziata (identica a `p_target_table`).                         |
| `pk_column`        | `name`    | Nome della colonna PK di `referenced_table` a cui punta la FK.             |

---

### Dettaglio del flusso

1. La funzione interroga cataloghi di sistema (`pg_constraint`, `pg_class`, `pg_attribute`) filtrando `contype = 'f'` (foreign key).  
2. Converte gli OID in `regclass` per ottenere il nome schema.tabella.  
3. Estrae, per ogni FK rilevata, la colonna chiave nella tabella figlia e la colonna chiave primaria nella tabella padre.

---

### Esempi di utilizzo

```sql
-- Trova tutte le FK che puntano alla tabella config.iva
SELECT *
  FROM dbops.fn_find_file_usage('config.iva'::regclass);

-- Verifica dipendenze verso la tabella anagrafiche.contatti
SELECT table_with_fk, fk_column
  FROM dbops.fn_find_file_usage('anagrafiche.contatti'::regclass);

-- Usando direttamente OID o regclass senza cast esplicito:
SELECT * 
  FROM dbops.fn_find_file_usage(anagrafiche.contatti);

```
 

### ℹ️ Vantaggi Operativi

    Rapidità: un’unica query per esplorare tutte le FK in ingresso.

    Affidabilità: si basa su cataloghi di sistema ufficiali, aggiornati in tempo reale.

    Automazione: integrabile in script di migrazione o tool di analisi schema.

> “Con fn_find_file_usage puoi eseguire in pochi secondi un’analisi completa delle dipendenze tra tabelle, fondamentale per il refactoring e la gestione sicura delle migrazioni.”