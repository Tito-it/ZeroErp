## 📘 Documentazione Concettuale – Funzione `dbops.trgfn_cleanup_at_alla_nascita`

---

### 👀 Vedi anche

**Guide**

* [Audit e tracciabilità §7 — Manutenzione e retention](/guide/audit-e-tracciabilita)

**Approfondimento funzioni**

* [dbops.fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) — da dove legge termine e colonna base
* [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — l'altra via, per il pregresso
* [vendite.trgfn_logs_guard_delete](/dbzero/vendite/funzioni/trgfn_logs_guard_delete) e
  [vendite.trgfn_event_log_append_only](/dbzero/vendite/funzioni/trgfn_event_log_append_only) — chi lascia passare il purge

---
### 🎯 Scopo Principale
(rev 2026-09-18 — Passo D di `analisi-osservabilita-log.md`)

Trigger **`BEFORE INSERT`** generico: scrive `NEW.cleanup_at = <colonna base> + ttl_days`,
leggendo termine e colonna base dalla regola `CLEANUP_AT` che copre la tabella
(`dbops.fn_cleanup_at_params`). **Nessuna regola → `cleanup_at` resta `NULL`**: la riga non
scade mai, in dubbio si conserva.

---

### Aggancio

`trg_<tabella>_m50_cleanup_at_ins` — `BEFORE INSERT … FOR EACH ROW` — su:

| Tabella | Colonna base (dalla regola) | Regola |
| --- | --- | --- |
| `vendite.event_log` | `event_time` | 15 |
| `vendite.fatturazione_lotti_log` | `data_ora` | 16 |
| `vendite.fatture_log` | `data_ora` | 17 |
| `vendite.fatturazione_lotti_task_runs` | `started_at` | 18 |
| `vendite.commesse_push_log` | `run_at` | 19 |

Tutte a **750 giorni** (due chiusure annuali): i quattro registri che
`script.vw_giornale_entita` legge insieme scadono insieme, e il registro di giro del push
— a cui punta il `correlation_id` di `event_log` — con loro.

---

### ⭐ Perché alla nascita e non con l'UPDATE del job

Il framework standard valorizza `cleanup_at` con un **UPDATE** notturno
(`fn_apply_cleanup_at`). Su un **registro** quell'UPDATE:

* riscrive `data_update`/`user_update` su ogni riga fresca — e su `fatture_log`
  `user_update` dice *chi* ha ammesso un critico;
* passa dai trigger di `UPDATE` (su `fatture_log` il resync di `critical`);
* lascia la scadenza modificabile dal job.

Alla nascita la riga sa già quando scade, e nessun trigger di `UPDATE` si sveglia. Il job
resta per il **pregresso** (le righe nate prima del trigger, a `NULL`):
`apply_on_update = false` tocca solo quelle, una volta.

### ⚠️ La colonna base si legge dalla regola, non si indovina

`fn_apply_cleanup_at` usa `base_ts_column` della regola. Se il trigger usasse un'altra
colonna, pregresso e righe nuove avrebbero due scadenze calcolate su due orari diversi per
la stessa regola. Si legge `($1).<colonna>` con `EXECUTE … USING NEW`; se la regola non la
dichiara, o sulla riga è `NULL`, la base è `now()`.

### ⚠️ Sovrascrive, non completa

Non c'è `IF NEW.cleanup_at IS NULL`: un diario non lascia scegliere al chiamante quando
scade (parità con quello che faceva `trgfn_event_log_deriva_scope`). Chi deve produrre una
riga già scaduta — un pgTAP — **retrodata la colonna base**, e il trigger fa il resto.

### Fase `_m50_`

È una derivazione, non un guard: va **dopo** gli `_a10_` — in particolare
`trg_fatture_log_a10_orario_reale_ins`, che riscrive un `data_ora` `NULL` o `= now()` con
`clock_timestamp()` — e prima degli `_z90_`. Un `_a10_cleanup_at_ins` scatterebbe prima
(`'c' < 'o'`) e calcolerebbe la scadenza su un orario che la riga non avrà.

---

### Verifica

`db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql`;
`db/pgtap/vendite/test-event-log-deriva-scope.sql` (test 4).

---

{% include-markdown "signature-core.md" %}
