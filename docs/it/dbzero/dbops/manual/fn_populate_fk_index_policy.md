## 📘 Documentazione Concettuale – Funzione `dbops.fn_populate_fk_index_policy()`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)      
>
> Approfondimento view:   
> - [dbops.vw_fk_senza_indice](/dbzero/dbops/manual/vw_fk_senza_indice) 

La funzione **`dbops.fn_populate_fk_index_policy()`** esegue il popolamento automatico di `dbops.fk_index_policy` aggiungendo tutte le foreign key presenti in `dbops.vw_fk_senza_indice` che non hanno ancora un record in policy, impostando per ciascuna `consentito = false`.

---

### 🎯 Scopo Principale

* **Coerenza iniziale**
  Garantire che ogni FK rilevata nella view senza indice abbia la propria entry di policy, evitando omissioni.
* **Popolamento “a freddo”**
  Tutti i nuovi record vengono creati con `consentito = false`, lasciando in carico all’operatore la decisione di abilitare o meno l’indice.
* **Automazione**
  Riduce il lavoro manuale di inserimento di policy per nuove FKs.

---

### 🔍 Flusso Logico

1. **Lettura FKs senza policy**
   Seleziona dalla view `dbops.vw_fk_senza_indice` tutte le tuple `(schema_name, table_name, constraint_name)` non ancora presenti in `dbops.fk_index_policy`.
2. **Inserimento in `fk_index_policy`**
   Per ciascuna riga, esegue:

   ```sql
   INSERT INTO dbops.fk_index_policy(
     schema_name,
     table_name,
     constraint_name,
     consentito,
     note
   ) VALUES (
     rec.schema_name,
     rec.table_name,
     rec.constraint_name,
     false,
     'Popolamento automatico: indice ix_<table>_<constraint> non ancora presente'
   );
   ```

---

### 🔖 Funzione SQL

```sql
CREATE OR REPLACE FUNCTION dbops.fn_populate_fk_index_policy()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT schema_name, table_name, constraint_name
      FROM dbops.vw_fk_senza_indice
     WHERE (schema_name, table_name, constraint_name)
       NOT IN (
         SELECT schema_name, table_name, constraint_name
           FROM dbops.fk_index_policy
       )
  LOOP
    INSERT INTO dbops.fk_index_policy(
      schema_name,
      table_name,
      constraint_name,
      consentito,
      note
    ) VALUES (
      rec.schema_name,
      rec.table_name,
      rec.constraint_name,
      false,
      format(
        'Autopopulated: missing ix_%s_%s index',
        rec.table_name,
        rec.constraint_name
      )
    );
  END LOOP;
END;
$$;

COMMENT ON FUNCTION dbops.fn_populate_fk_index_policy() IS
  'Popola automaticamente dbops.fk_index_policy per tutte le FK senza indice, con consentito=false.';
```

---

### 🚀 Utilizzo

Essendo una **funzione** che restituisce `void`, puoi eseguirla direttamente con:

```sql
SELECT dbops.fn_populate_fk_index_policy();
```

In alternativa, in un contesto PL/pgSQL o in un DO block:

```plpgsql
DO $$
BEGIN
  PERFORM dbops.fn_populate_fk_index_policy();
END;
$$;
```

> **Nota:** non usare `SELECT * FROM dbops.fn_populate_fk_index_policy()`, poiché la funzione non restituisce righe tabellari. Se preferisci invocarla con `CALL`, puoi convertirla in **procedura**:

```sql
CREATE PROCEDURE dbops.apply_population()
LANGUAGE plpgsql AS $$
BEGIN
  PERFORM dbops.fn_populate_fk_index_policy();
END;
$$;
```

E poi eseguire:

```sql
CALL dbops.apply_population();
```

> 🧠 **“Esegui la funzione con `SELECT` o `PERFORM`: non è necessario usare `SELECT * FROM`. Converti in procedura se vuoi chiamare con `CALL`.”**
