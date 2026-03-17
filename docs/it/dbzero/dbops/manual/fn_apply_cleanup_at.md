## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_cleanup_at`

---

### 👀 Vedi anche

**Guide**

* [Automazione DB](/guide/automazione-db)

**Approfondimento funzioni**

* [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)
* [dbops.fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired)

---

### 🎯 Scopo Principale

(latest review 07-02-26)
La funzione **`dbops.fn_apply_cleanup_at`** calcola il valore di **`cleanup_at`** per una tabella target, applicando un **TTL fisso** a partire da una colonna timestamp di base (es. `data_insert`, `executed_at`, `occurred_at`).

---

### Parametri

| Parametro           | Tipo      | Descrizione |
| ------------------- | --------- | ----------- |
| `p_schema`          | `text`    | Schema della tabella target. |
| `p_table`           | `text`    | Tabella target. |
| `p_cleanup_column`  | `text`    | Colonna cleanup (default `cleanup_at`). |
| `p_base_ts_column`  | `text`    | Colonna timestamp base per il calcolo. |
| `p_ttl_days`        | `integer` | Giorni di retention (TTL). |
| `p_apply_on_update` | `boolean` | Se `true`, ricalcola anche su righe già valorizzate. |
| `p_dry_run`         | `boolean` | Se `true`, non aggiorna e ritorna il numero righe potenziali. |

---

### Regole Principali

* `p_ttl_days` deve essere **>= 0**.
* Se la colonna `cleanup_at` o la colonna base non esistono, la funzione **non agisce**.
* In **dry‑run**, ritorna il conteggio delle righe che verrebbero aggiornate.

---

### Output

Ritorna il **numero di righe aggiornate** (o potenziali in dry‑run).
