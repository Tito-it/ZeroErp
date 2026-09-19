## 📘 Documentazione Concettuale – Funzione `dbops.fn_cleanup_at_params`

---

### 👀 Vedi anche

**Guide**

* [Audit e tracciabilità §7 — Manutenzione e retention](/guide/audit-e-tracciabilita)

**Approfondimento funzioni**

* [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) — il consumatore
* [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — lo stesso criterio di scelta
* [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — il job, per il pregresso

---
### 🎯 Scopo Principale
(rev 2026-09-18 — Passo D di `analisi-osservabilita-log.md`)

Risponde **con quale regola `CLEANUP_AT`** una tabella scade: i `params` (`ttl_days`,
`base_ts_column`, `cleanup_column`, `apply_on_update`) della regola **più specifica** di
[`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl) che la copre —
per `priority`, poi `id`, con fallback alla regola `*all`. È **lo stesso criterio** con cui
`fn_run_automations_cleanup` sceglie la regola da applicare.

⭐ Esiste perché **il termine sta in una sede sola**: il trigger che scrive `cleanup_at`
alla nascita e il job che lo applica al pregresso devono leggere lo stesso numero.
Generalizza `vendite.fn_event_log_ttl_days()`, che faceva la stessa cosa con schema e
tabella cablati ed è stata **ritirata** (20260918-31).

---

### Parametri

| Parametro  | Tipo   | Descrizione |
| ---------- | ------ | ----------- |
| `p_schema` | `text` | schema della tabella |
| `p_table`  | `text` | nome della tabella |

### Output

`jsonb` — i `params` della regola vincente. **`NULL`** in due casi:

* nessuna regola `CLEANUP_AT` abilitata con `ttl_days` copre la tabella;
* `p_schema` o `p_table` vuoti — ⚠️ **non un errore**: la funzione è `STABLE` (un lookup,
  chiamato per riga da un trigger) e `fn_log_and_raise_error` *scrive* una riga di log.
  Senza questo ramo la regola `*all` coprirebbe anche una tabella senza nome e la risposta
  sarebbe il default: qui invece «non so di che tabella parli» vale «non scade mai» — in
  dubbio si conserva.

---

### Verifica

`db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` (test 4-6).

---

{% include-markdown "signature-core.md" %}
