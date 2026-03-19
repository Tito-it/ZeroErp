## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_storico_provision`

> 👀 **Vedi anche**
>
Guide:
>
[Automazione DB](/guide/automazione-db)
>
Approfondimento tabelle:
>
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
>
Approfondimento funzioni:
>
[dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)   
> [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope)    
> [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col)   
> [dbops.fn_ensure_storico_table](/dbzero/dbops/funzioni/fn_ensure_storico_table)   
> [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico)   

---
### 🎯 Scopo Principale
(latest review 26-12-25)
La funzione **`dbops.fn_run_automations_storico_provision(p_exec_mode, p_schemas, p_dry_run)`** automatizza il **provisioning delle tabelle nello schema `storico`** per tutte le tabelle applicative che adottano la colonna di storicizzazione (es. `storicizza`). Per ogni tabella nell'ambito, verifica prerequisiti e demanda la creazione/adeguamento dell’omologa tabella storico a `fn_ensure_storico_table` (con eventuale indice GIN opzionale).

---

### Parametri di input

| Parametro     | Tipo    | Obbligatorio | Descrizione                                                                                                                |
| ------------- | ------- | :----------: | -------------------------------------------------------------------------------------------------------------------------- |
| `p_exec_mode` | text    |      ✔️       | Modalità di esecuzione (`AUTO`, `FORCE`, `CHECK`).                                                                         |
| `p_schemas`   | text[]  |      ❌       | Lista schemi da considerare; se `NULL`, risolta da `fn_resolve_scope`.                                                     |
| `p_dry_run`   | boolean |      ✔️       | Se `true`, esegue in modalità simulazione (la creazione effettiva è demandata all'helper che gestisce anche il `dry_run`). |

---

### Valore di ritorno

`void` – orchestration pura: cicla le tabelle nell'ambito e delega le operazioni all’helper `fn_ensure_storico_table`.

---

### Flusso logico

1. **Ambito**: determina gli schemi target tramite `fn_resolve_scope(p_schemas)`; esclude sempre lo schema `storico`.
2. **Enumerazione tabelle**: scorre tutte le tabelle "user" nell'ambito filtrate da `fn_table_in_scope`.
3. **Selezione regole**: per ciascuna tabella applica le regole abilitate in `automation_rules_tbl` con `rule_type='STORICO_PROVISION'`, in base a `exec_mode`, `target_schema` e `target_table` (supporto wildcard con `fn_schema_match`).
4. **Parametri regola**: legge da `params` l’opzione `create_gin_index` (boolean) per abilitare la creazione dell’indice GIN sul JSON di storico (se previsto dall’helper).
5. **Prerequisito flag**: risolve il nome della colonna storicizzazione con `fn_get_override_col(..., 'STORICIZZA_COL', 'storicizza')` e verifica esistenza con `fn_col_exists`.
6. **FK verso storico**: risolve il nome della FK con `fn_get_override_col(..., 'STORICO_FK', '{table}_id')`.
7. **Provisioning**: chiama `fn_ensure_storico_table(schema, table, fk_col, create_gin, p_dry_run)` che si occupa di creare/adeguare la tabella nello schema `storico` e gestire il `dry_run`/errori.

---

### Casi d’uso tipici

* **Bootstrap storicizzazione**: preparare automaticamente tutto il necessario nello schema `storico` per nuove tabelle applicative.
* **Migrazione**: adeguare l’ecosistema storico dopo refactoring di colonne chiave o convenzioni (`STORICIZZA_COL`, `STORICO_FK`).
* **Pre‑deploy analysis**: usare `p_dry_run` per verificare quali tabelle verrebbero create/aggiornate nello storico.

---

### Permessi e sicurezza

* Richiede privilegi DDL sullo schema `storico` e sui metadati delle tabelle applicative.
* La gestione degli errori operativi è effettuata all’interno dell’helper (`fn_ensure_storico_table`); in modalità `dry_run` non vengono applicate modifiche.

---

### Esempi di utilizzo

* **Simulazione**: `SELECT dbops.fn_run_automations_storico_provision('AUTO', ARRAY['anagrafiche','config'], true);`
* **Esecuzione reale**: `SELECT dbops.fn_run_automations_storico_provision('FORCE', NULL, false);`

---

### Considerazioni

* La presenza del flag di storicizzazione sulla tabella applicativa è requisito minimo; in caso contrario la tabella viene **saltata**.
* Gli override permettono di supportare naming legacy o specifico di dominio.
* La scelta di creare indici GIN dovrebbe essere valutata in base al volume/forma dei dati storico.

---

### Benefici

* **Automazione ripetibile**: provisioning standard e idempotente dello schema `storico`.
* **Coerenza**: riduce divergenze tra tabelle applicative e relative controparti storico.
* **Controllo**: `dry_run` e regole parametrizzabili forniscono visibilità e sicurezza prima del deploy.

---

> **In sintesi**: `fn_run_automations_storico_provision` prepara in modo sistematico l’infrastruttura di storicizzazione, assicurando che ogni tabella con `storicizza` abbia la propria omologa nello schema `storico`, con FK e (opzionalmente) indice GIN dove previsto.
