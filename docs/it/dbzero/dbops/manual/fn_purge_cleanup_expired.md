## 📘 Documentazione Concettuale – Funzione `dbops.fn_purge_cleanup_expired`

---

### 👀 Vedi anche
>
>**Guide**
>
[Automazione DB](/guide/automazione-db)

> **Approfondimento funzioni**
>
[dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)   
> [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at)  

---

### 🎯 Scopo Principale

(latest review 07-02-26)
La funzione **`dbops.fn_purge_cleanup_expired`** elimina i record con **`cleanup_at` scaduto** usando una strategia a **batch**, per ridurre lock e impatti sulle tabelle più grandi.

---

### Parametri

| Parametro          | Tipo      | Descrizione                                            |
| ------------------ | --------- | ------------------------------------------------------ |
| `p_schema`         | `text`    | Schema della tabella target.                           |
| `p_table`          | `text`    | Tabella target.                                        |
| `p_cleanup_column` | `text`    | Colonna cleanup (default `cleanup_at`).                |
| `p_batch_limit`    | `integer` | Dimensione batch (default 5000).                       |
| `p_dry_run`        | `boolean` | Se `true`, non elimina e ritorna il numero eleggibile. |

---

### Regole Principali

* Se `cleanup_at` non esiste, la funzione **non agisce**.
* In **dry‑run**, ritorna il conteggio delle righe eleggibili.
* In modalità reale, elimina **a blocchi** finché non restano righe scadute.

---

### Output

Ritorna il **numero totale di righe eliminate** (o potenziali in dry‑run).
