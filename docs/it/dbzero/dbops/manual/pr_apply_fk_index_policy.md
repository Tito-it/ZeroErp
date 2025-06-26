## 📘 Documentazione Concettuale – Procedura `dbops.apply_fk_index_policy()`


> 👀 **Vedi anche**  
>
> Approfondimento Tabelle:   
> - [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)      

La procedura **`dbops.apply_fk_index_policy()`** incapsula la logica di creazione o rimozione dinamica degli indici sulle foreign key, in base alle policy definite in `dbops.fk_index_policy`.

---

### 🎯 Scopo Principale

* **Centralizzare la gestione degli indici FK**
  Evitare di duplicare script DDL e consentire modifiche runtime delle policy.
* **Allineare schema e policy**
  Creare solo gli indici consentiti e rimuovere quelli non più autorizzati.
* **Integrazione con Liquibase**
  Può essere richiamata in un changeSet `runAlways` per applicare le policy ad ogni deploy.

---

### 🔍 Parametri di Input

Questa procedura non richiede parametri: agisce su tutte le righe di `dbops.fk_index_policy`.

---

### ⚙️ Flusso Logico

1. **Iterazione su ogni policy**
   Scorre tutte le righe di `dbops.fk_index_policy`.
2. **Verifica flag `consentito`**

   * Se `TRUE`, esegue `CREATE INDEX IF NOT EXISTS` con nome coerente a `<table>_<constraint>`.
   * Se `FALSE`, esegue `DROP INDEX IF EXISTS` per rimuovere eventuale indice esistente.
3. **Naming uniforme**
   Gli indici sono denominati `ix_<table_name>_<constraint_name>`, garantendo predicibilità.

---

### 🔖 Procedura SQL

```sql
CREATE OR REPLACE PROCEDURE dbops.apply_fk_index_policy()
LANGUAGE plpgsql
AS $$
DECLARE
  rec RECORD;
BEGIN
  FOR rec IN SELECT * FROM dbops.fk_index_policy LOOP
    IF rec.consentito THEN
      EXECUTE format(
        'CREATE INDEX IF NOT EXISTS ix_%I_%I ON %I.%I (%I)',
        rec.table_name,
        rec.constraint_name,
        rec.schema_name,
        rec.table_name,
        rec.constraint_name
      );
    ELSE
      EXECUTE format(
        'DROP INDEX IF EXISTS ix_%I_%I',
        rec.table_name,
        rec.constraint_name
      );
    END IF;
  END LOOP;
END;
$$;

COMMENT ON PROCEDURE dbops.apply_fk_index_policy() IS
  'Applica le policy di indicizzazione definite in dbops.fk_index_policy: crea o rimuove gli indici sulle foreign key secondo il flag consentito.';
```

---

### 🚀 Utilizzo

* **Manuale**:

  ```sql
  CALL dbops.apply_fk_index_policy();
  ```
* **In Liquibase** (changeSet `runAlways: true`):

  ```yaml
  - changeSet:
      id: apply-fk-index-policy
      author: mctit
      runAlways: true
      sql:
        splitStatements: false
        sql: |
          CALL dbops.apply_fk_index_policy();
  ```

---

### 💡 Vantaggi Operativi

* **Flessibilità**: policy modificabili in tabella, senza toccare DDL statici.
* **Automazione**: supporto a deploy automatizzati con Liquibase.
* **Tracciabilità**: log delle modifiche in `fk_index_policy`, con `note` e timestamp.
* **Manutenibilità**: unico punto di gestione per tutti gli indici FK.

---

> 🧠 **“Encapsulando il DO-block in una procedura, rendiamo il processo di applicazione delle policy più leggibile, riutilizzabile e integrabile nei flussi CI/CD.”**
