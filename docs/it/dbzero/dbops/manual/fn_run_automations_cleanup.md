## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_cleanup`

---

### 👀 Vedi anche

>**Guide**
>
[Automazione DB](/guide/automazione-db)
>
>**Approfondimento tabelle**
>
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
>* [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions)   
>* [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)   
>
>**Approfondimento funzioni**
>
[dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at)   
>* [dbops.fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired)   
>
### 🎯 Scopo Principale
(latest review 07-02-26)
La funzione **`dbops.fn_run_automations_cleanup(p_exec_mode, p_schemas, p_dry_run)`** è l’orchestratore del framework di cleanup basato su `cleanup_at`.

Applica in modo coerente due regole dichiarative:

* **`CLEANUP_AT`**: calcolo di `cleanup_at` con TTL fisso.
* **`CLEANUP_PURGE`**: cancellazione dei record scaduti a batch.

---

### Parametri di input

| Parametro     | Tipo      | Descrizione                                              |
| ------------- | --------- | -------------------------------------------------------- |
| `p_exec_mode` | `text`    | Modalità di esecuzione (`AUTO`, `CI`, `SCHEDULED`).      |
| `p_schemas`   | `text[]`  | Schemi target. Se `NULL`, risolti da `fn_resolve_scope`. |
| `p_dry_run`   | `boolean` | Se `true`, non modifica i dati e registra audit DRYRUN.  |

---

### Flusso logico

1. Risolve l'**ambito** (`dbops.fn_resolve_scope`).
2. Scorre le tabelle nell'ambito (`dbops.fn_table_in_scope`).
3. Esclude le tabelle presenti in `dbops.automation_cleanup_exclusions`.
4. Applica le regole `CLEANUP_AT` e `CLEANUP_PURGE` compatibili con schema/tabella.
5. Registra l’esito in `dbops.audit_log` tramite `fn_audit_log_once`.

---

### 🧾 Parametri rule_type (JSON)

**CLEANUP_AT**

```json
{
  "ttl_days": 30,
  "cleanup_column": "cleanup_at",
  "base_ts_column": "data_insert",
  "apply_on_update": false
}
```

**CLEANUP_PURGE**

```json
{
  "cleanup_column": "cleanup_at",
  "batch_limit": 5000
}
```

---

### Note operative

* Se `cleanup_at` non esiste nella tabella target, la regola viene **ignorata**.
* `base_ts_column` è opzionale: se non indicata il runner tenta fallback su
  `data_insert`, `executed_at`, `occurred_at`, `created_at`.

  > ⭐ **E «opzionale» qui non vuol dire «dichiarala per sicurezza»: sulla riga
  > `*all`/`*all` NON va dichiarata.** È una proprietà **per tabella**, mentre
  > `params` è **per riga di regola**: un valore unico imposto a ogni tabella
  > del database sarebbe sbagliato per costruzione. Lì il fallback a catena
  > **è** il disegno.
  >
  > ⚠️ **Si dichiara solo dove il fallback sceglierebbe la colonna sbagliata**,
  > e oggi il caso è uno: **`vendite.event_log`** (`"base_ts_column":
  > "event_time"`, dal 2026-09-01). Quella tabella ha **sia** `data_insert`
  > **sia** `event_time`; il fallback prenderebbe la prima perché è in testa
  > alla catena, ma il trigger che scrive `cleanup_at` lo calcola da
  > `event_time`. Erano **due modi di derivare la stessa grandezza che non
  > concordavano** — indistinguibili sulle righe nate normalmente, divergenti
  > su un evento importato o ricostruito.
  >
  > 📌 Se la colonna dichiarata non esiste, la tabella viene **saltata** con un
  > audit `WARN` e `skip_reason = MISSING_BASE_TS_COLUMN`: non si rompe niente,
  > ma la pulizia di quella tabella non gira — un difetto silenzioso, da
  > cercare negli audit e non fra gli errori.
* Le esclusioni con `enabled=true` hanno priorità su qualunque regola.
