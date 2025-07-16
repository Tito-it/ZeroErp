## 📚 Documentazione Concettuale – Tabella `config.parameter_overrides`

> 👀 **Vedi anche** 
>
> Approfondimento Tabelle:    
> - [config.parameters](/dbzero/config/tabelle/parameters)      
>
> Approfondimento funzioni :    
> - [script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)    

---
### 🎯 Scopo Principale

La tabella **`config.parameter_overrides`** permette di creare **override dinamici** dei parametri definiti in `config.parameters` su diversi livelli di contesto (tenant, user, session, function), garantendo che ogni combinazione `(parameter_id, scope_type, scope_id)` sia unica e tracciata per audit.

---

### 🗂️ Campi principali

| Colonna            | Tipo                        | Nullable | Default        | Descrizione                                                              |
| ------------------ | --------------------------- | -------- | -------------- | ------------------------------------------------------------------------ |
| `id`               | BIGINT                      | NO       | IDENTITY       | Chiave primaria univoca dell’override.                                   |
| `parameter_id`     | BIGINT                      | NO       | —              | FK a `config.parameters(id)`: parametro di cui si esegue l’override.     |
| `scope_type`       | VARCHAR(20)                 | NO       | —              | Tipo di ambito (`tenant`,`user`,`session`,`function`, …).                |
| `scope_id`         | TEXT                        | NO       | —              | Identificativo dell’ambito (ID numerico, session key, nome funzione, …). |
| `overridden_value` | TEXT                        | NO       | —              | Valore che sostituisce `default_value` per questo ambito.                |
| `data_insert`      | TIMESTAMP WITHOUT TIME ZONE | NO       | `NOW()`        | Timestamp di creazione dell’override.                                    |
| `user_insert`      | VARCHAR(80)                 | NO       | `CURRENT_USER` | Utente che ha creato l’override.                                         |
| `data_update`      | TIMESTAMP WITHOUT TIME ZONE | NO       | `NOW()`        | Timestamp dell’ultima modifica.                                          |
| `user_update`      | VARCHAR(80)                 | NO       | `CURRENT_USER` | Utente che ha eseguito l’ultima modifica.                                |

---

### 🔒 Vincoli

| Tipo        | Nome                       | Colonne                              | Descrizione                                                                           |
| ----------- | -------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------- |
| PRIMARY KEY | `parameter_overrides_pkey` | `id`                                 | Chiave primaria.                                                                      |
| UNIQUE      | `uq_overrides_param_scope` | `parameter_id, scope_type, scope_id` | Un solo override per combinazione parametro–ambito.                                   |
| FOREIGN KEY | `fk_overrides_parameter`   | `parameter_id`                       | Riferimento a `config.parameters(id)` con `ON UPDATE CASCADE` e `ON DELETE RESTRICT`. |

---

### 🚨 Trigger

| Nome                                | Timing | Evento | Azione                                       |
| ----------------------------------- | ------ | ------ | -------------------------------------------- |
| `trg_upd_overrides_audit_data_user` | BEFORE | UPDATE | `script.trgfn_upd_audit_data_user_generic()` |

---

### 📝 Esempi di Override

#### 1. Override Parametro “Valuta”

Override del parametro `DEFAULT_CURRENCY` per un tenant (tenant\_id = 100) e un user specifico (user\_id = 42):

```sql
-- Tenant override
INSERT INTO config.parameter_overrides
  (parameter_id, scope_type, scope_id, overridden_value)
VALUES
  ((SELECT id FROM config.parameters WHERE code = 'DEFAULT_CURRENCY'),
   'tenant', '100', 'USD');

-- User override (Django user_id = 42)
INSERT INTO config.parameter_overrides
  (parameter_id, scope_type, scope_id, overridden_value)
VALUES
  ((SELECT id FROM config.parameters WHERE code = 'DEFAULT_CURRENCY'),
   'user', '42', 'GBP');
```

#### 2. Override Parametro “Stato”

Override del parametro `INITIAL_STATE` all’interno della funzione `invoice_process`:

```sql
INSERT INTO config.parameter_overrides
  (parameter_id, scope_type, scope_id, overridden_value)
VALUES
  ((SELECT id FROM config.parameters WHERE code = 'INITIAL_STATE'),
   'function', 'invoice_process', 'PENDING_APPROVAL');
```

---

> 🧠 **Questa tabella è il cuore della personalizzazione runtime dei parametri: ogni override è unico per contesto e tracciato per audit, senza duplicare logica nell’applicazione.**
