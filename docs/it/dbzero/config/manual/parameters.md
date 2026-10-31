## 📚 Documentazione Concettuale – Tabella `config.parameters`  

> 👀 **Vedi anche**  
>
Approfondimento Tabelle:   
>
[config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)      
>
Approfondimento funzioni :    
>
[script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)    
>
Approfondimento parametri tabellari Vs GUC   
>
[parametri-personalizzati-(GUC)](/postgresql/parametri-personalizzati-(GUC))   
> All'interno del documento viene spiegata la differenza tra parametri GUC e parametri tabellari

---
### 🎯 Scopo Principale

(ultima revisione 31-10-2026)

La tabella **`config.parameters`** implementa un’**architettura a due livelli** per la configurazione dinamica dell’applicazione:

1. **Parametri di sistema (global defaults)**

   * Archiviati in una single source of truth: `config.parameters` contiene tutti i valori di default e i metadati (descrizione, audit).
2. **Parametri di contesto (override)**

   * Vengono gestiti in `config.parameter_overrides` (vedi sezione dedicata).

---

### Campi principali

| Colonna         | Tipo                        | Nullable | Default             | Descrizione                                   |
| --------------- | --------------------------- | -------- | ------------------- | --------------------------------------------- |
| `id`            | BIGINT                      | NO       | `nextval(...)`      | Chiave primaria univoca.                      |
| `code`          | VARCHAR(100)                | NO       | —                   | Codice univoco del parametro (es. `TIMEOUT`). |
| `default_value` | TEXT                        | NO       | —                   | Valore di default del parametro.              |
| `description`   | TEXT                        | SÌ       | —                   | Descrizione estesa.                           |
| `ammette_override` | BOOLEAN                  | NO       | —                   | La famiglia: `true` con override, `false` uguale per tutti. Nessun default: un parametro nuovo la dichiara. |
| `tipo_valore`   | TEXT (CHECK)                | NO       | —                   | La forma del valore (default e override). Nessun default: un parametro nuovo la dichiara. |
| `data_insert`   | TIMESTAMP WITHOUT TIME ZONE | NO       | `CURRENT_TIMESTAMP` | Data di creazione del record.                 |
| `user_insert`   | VARCHAR(80)                 | NO       | `CURRENT_USER`      | Utente creazione.                             |
| `data_update`   | TIMESTAMP WITHOUT TIME ZONE | NO       | `CURRENT_TIMESTAMP` | Data ultima modifica.                         |
| `user_update`   | VARCHAR(80)                 | NO       | `CURRENT_USER`      | Utente ultima modifica.                       |

---

### La famiglia del parametro

`ammette_override` dice se il valore può cambiare per chi lavora (`true`, letto con la cascata di
`script.fn_get_parameter_full`) o deve valere per tutti (`false`, letto dal default dalla funzione
che possiede la regola). Il database la fa rispettare:

* su `config.parameter_overrides`, un override su un parametro `false` si rifiuta
  (`E_PARAMETER_OVERRIDE_NON_AMMESSO`);
* qui, il passaggio `true` → `false` si rifiuta finché il parametro ha override
  (`E_PARAMETER_OVERRIDE_PRESENTI`, trigger `trg_parameters_a10_guard_ammette_override_upd`,
  [la funzione](/dbzero/config/funzioni/trgfn_parameters_guard_ammette_override)).

### La forma del valore

`tipo_valore` dice che forma ha il valore, per il default e per ogni override: `BOOLEANO`,
`INTERO_POSITIVO`, `INTERO_NON_NEGATIVO`, `DECIMALE_POSITIVO`, `DECIMALE_NON_NEGATIVO`,
`DECIMALE_NON_NEGATIVO_O_VUOTO`, `DATA`, `TESTO` (vincolo `chk_parameters_tipo_valore`). La regola
di ogni forma sta in [script.fn_valore_parametro_non_conforme](/dbzero/script/funzioni/fn_valore_parametro_non_conforme).
Il database la fa rispettare quando si scrive:

* qui, il default (`E_PARAMETER_VALORE_NON_CONFORME`); cambiando il tipo, anche ogni override
  esistente, acceso o spento (`E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO`). Trigger
  `trg_parameters_a07_guard_tipo_valore_ins_upd`,
  [la funzione](/dbzero/config/funzioni/trgfn_parameters_guard_tipo_valore);
* su `config.parameter_overrides`, il valore dell'override
  ([la funzione](/dbzero/config/funzioni/trgfn_parameter_overrides_guard_tipo_valore)).

Il quadro, con le regole di lettura: [Configurazione e gestione parametri](/guide/configurazione-e-gestione-parametri).
I valori si seminano da `80_data/sql/config/parameters.csv`; i parametri di sistema da
`parameters_sistema.csv`, caricato da `70_dati_sistema` perché il codice li legge prima dei seed.

---

### Vincoli

| Tipo        | Nome                 | Colonne | Descrizione                    |
| ----------- | -------------------- | ------- | ------------------------------ |
| PRIMARY KEY | `pk_parameters`      | `id`    | Chiave primaria.               |
| UNIQUE      | `uq_parameters_code` | `code`  | Garantisce unicità del codice. |

---

### Vantaggi Operativi

1. **Override multi-livello** (tenant → user → session → function → default) garantito dallo schema.
2. **Nessuna ripetizione di logica**: l’applicazione chiama una funzione centralizzata (es. `get_parameter_full`) che applica la catena di priorità.
3. **Config runtime**: il tenant o utente può cambiare comportamenti senza toccare file YAML.
4. **Audit**: possibili trigger su overrides per tracciare chi modifica cosa.
5. **Best practice**: separare i secrets (es. password) in un Vault, usare Liquibase e caching lato applicazione per performance.

---

## Approfondimenti e Esempi Avanzati

### Esempio: Override Parametro “Valuta”

Supponiamo di avere un parametro globale per la valuta di default:

```sql
INSERT INTO config.parameters(code, default_value, description)
VALUES ('DEFAULT_CURRENCY', 'EUR', 'Valuta di default per le transazioni');
```

Un tenant specifico (tenant\_id = 100) vuole usare USD:

```sql
INSERT INTO config.parameter_overrides
  (parameter_id, scope_type, scope_id, overridden_value)
VALUES
  ((SELECT id FROM config.parameters WHERE code='DEFAULT_CURRENCY'),
   'tenant', '100', 'USD');
```

Per un utente VIP (user\_id = 42) si preferisce GBP:

```sql
INSERT INTO config.parameter_overrides
  (parameter_id, scope_type, scope_id, overridden_value)
VALUES
  ((SELECT id FROM config.parameters WHERE code='DEFAULT_CURRENCY'),
   'user', '42', 'GBP');
```

Chiamando:

```sql
SELECT config.get_parameter_full(
  'DEFAULT_CURRENCY',
  p_tenant_id   := 100,
  p_user_id     := 42,
  p_session_key := NULL,
  p_function    := NULL
);
```

otterremo **’GBP’**, in quanto l’override utente ha priorità su quello tenant.

### Esempio: Override Parametro “Stato”

Un parametro che definisce lo stato iniziale di un workflow:

```sql
INSERT INTO config.parameters(code, default_value, description)
VALUES ('INITIAL_STATE', 'NEW', 'Stato iniziale del documento');
```

Durante l’elaborazione di una particolare funzione `invoice_process`, vogliamo impostare un override:

```sql
INSERT INTO config.parameter_overrides
  (parameter_id, scope_type, scope_id, overridden_value)
VALUES
  ((SELECT id FROM config.parameters WHERE code='INITIAL_STATE'),
   'function', 'invoice_process', 'PENDING_APPROVAL');
```

La chiamata:

```sql
SELECT config.get_parameter_full(
  'INITIAL_STATE',
  p_tenant_id   := NULL,
  p_user_id     := NULL,
  p_session_key := NULL,
  p_function    := 'invoice_process'
);
```

restituirà **’PENDING\_APPROVAL’**, senza impattare la configurazione globale.


### Confronto: GUC vs Modello a Tabelle

| Caratteristica              | GUC PostgreSQL                                      | Tabella Override (`config.parameters` + `config.parameter_overrides`)              |
| --------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Livelli di applicazione** | `database`, `role`, `session`, **statici**          | `global → tenant → user → session → function` (dinamici)                           |
| **Flessibilità**            | Rigido (solo livelli predefiniti)                   | Altamente estendibile a nuovi ambiti (es. ruolo, feature, modulo)                  |
| **Versioning**              | No (config file o DDL)                              | Sì (versionato con Liquibase in script SQL)                                        |
| **Audit**                   | Limitato (no audit built‑in)                        | Sì (campi `data_insert`, `user_insert`, trigger di audit)                          |
| **Accesso runtime**         | Solo `SET` o `current_setting`                      | API/Query dirette a database, integrabili in endpoint REST                         |
| **Use case ideale**         | Parametri **DB‑centrici** (work\_mem, search\_path) | Parametri **business‑centrici** (timeout, currency, workflow, feature flags, etc.) |

> **Quando scegliere...**
>
**GUC PostgreSQL**: per configurazioni strettamente tecniche o performance‑oriented, con requisiti statici o legati al ruolo DB.
> **Tabella Override**: per impostazioni dinamiche, multi‑tenant e variabili in base a user/session/function, con tracciamento e versioning completo.

---



> **“Questi esempi mostrano come il modello a due tabelle gestisca override precisi per valuta, stato o qualunque parametro, mantenendo la scalabilità e la manutenibilità.”**
