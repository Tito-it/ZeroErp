## 📚 Documentazione concettuale - Tabella `dbops.fk_index_policy`

### 🎯 Scopo Principale

La tabella **`dbops.fk_index_policy`** definisce una **policy centralizzata** per la gestione degli index sulle foreign key, consentendo di abilitare o disabilitare la creazione/uso di indici per specifici vincoli referenziali.

---


---

### 🔒 Vincoli

| Tipo        | Nome                   | Colonne                                    | Descrizione                                                        |
| ----------- | ---------------------- | ------------------------------------------ | ------------------------------------------------------------------ |
| PRIMARY KEY | `fk_index_policy_pkey` | `schema_name, table_name, constraint_name` | Chiave primaria composita per identificare univocamente la policy. |

---

### 💡 Uso e Casi d’Oro

* **Controllo centralizzato**: gestire in un unico punto l’abilitazione o meno degli indici sui vincoli referenziali, evitando di creare indici non necessari o ridondanti.
* **Ottimizzazione delle performance**: disabilitare index su FK poco usati per ridurre overhead in scrittura, o forzare index su FK critici per migliorare le join.
* **Audit e documentazione**: con la colonna `dll_command` si tiene traccia delle motivazioni alla base delle scelte, facilitando review e manutenzione.
* **Integrazione con script di DBOps**: gli script di deployment possono leggere questa tabella e generare dinamicamente DDL `CREATE INDEX` o `DROP INDEX` per applicare la policy.

---

### 🔧 Esempio di Utilizzo

1. **Disabilitare index su un vincolo**

   ```sql
   INSERT INTO dbops.fk_index_policy(
     schema_name,
     table_name,
     constraint_name,
     consentito,
     dll_command
   ) VALUES (
     'anagrafiche',
     'soggetti_ruoli',
     'fk_soggetti_anagrafiche',
     false,
     'FK su soggetti_ruoli non usata frequentemente, evita overhead in insert'
   );
   ```

2. **Abilitare index su un vincolo critico**

   ```sql
   INSERT INTO dbops.fk_index_policy(
     schema_name,
     table_name,
     constraint_name,
     consentito
   ) VALUES (
     'dbops',
     'audit_logs',
     'fk_logs_user_id',
     true
   );
   ```

3. **Script di applicazione policy**

   ```sql
   -- Pseudocodice PL/pgSQL per applicare la policy:
   DO $$
   DECLARE
     rec RECORD;
   BEGIN
     FOR rec IN SELECT * FROM dbops.fk_index_policy LOOP
       IF rec.consentito THEN
         EXECUTE format('CREATE INDEX IF NOT EXISTS ix_%I_%I ON %I.%I USING btree ((%I))',
           rec.table_name, rec.constraint_name, rec.schema_name, rec.table_name, rec.constraint_name);
       ELSE
         EXECUTE format('DROP INDEX IF EXISTS ix_%I_%I', rec.table_name, rec.constraint_name);
       END IF;
     END LOOP;
   END$$;
   ```

> 🧠 **“Utilizzare `fk_index_policy` consente di adattare dinamicamente la presenza di indici su foreign key per ottimizzare scritture e letture, centralizzando le decisioni e mantenendo tracciabilità.”**