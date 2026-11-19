## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_event_log_append_only()`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.event_log](/dbzero/vendite/tabelle/event_log) — lo stream che protegge
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_logs_guard_delete](/dbzero/vendite/funzioni/trgfn_logs_guard_delete) — il gemello sui log dei processi di fatturazione
> * [script.fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta) — la porta di manutenzione, solo per il migratore
> * [dbops.fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired) — il purge che ritira le righe scadute
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — come registra il rifiuto

---

### 🎯 Scopo Principale

Rende `vendite.event_log` **append-only**: la storia non si modifica e non si cancella, ma ciò che è
scaduto si ritira.

`event_log` è lo stream temporale degli eventi tecnici e funzionali dei domini vendite: pipeline,
commesse, SDI, fatture. Il suo valore sta nel fatto che sia **immodificabile**: un registro che si
può riscrivere non racconta cosa è successo, racconta cosa qualcuno preferisce che risulti.

---

### Aggancio

Trigger `trg_event_log_append_only_ud` — `BEFORE UPDATE OR DELETE` su `vendite.event_log`, `FOR EACH
ROW`. `INSERT` non è agganciato: l'inserimento passa senza costi.

---

### Regole applicate

| Operazione | Riga | Esito |
| --- | --- | --- |
| `UPDATE` | qualunque | rifiutato, `E_UPDATE_NOT_ALLOWED` |
| `DELETE` | scaduta (`cleanup_at` passato) | ammesso: è la retention |
| `DELETE` | viva, porta di manutenzione aperta | ammesso, con la riga nel diario delle porte |
| `DELETE` | viva | rifiutato, `E_DELETE_NOT_ALLOWED` |

* ⭐ **Il criterio della retention non è chi cancella ma cosa.** Il purge
  (`dbops.fn_purge_cleanup_expired`) cancella senza accendere GUC né farsi riconoscere: la riga
  passa perché è scaduta, non perché a cancellarla è il job.
* `cleanup_at` `NULL` vuol dire riga senza scadenza: non si cancella. In dubbio si conserva.
* ⭐ **Il veto sull'`UPDATE` rende `cleanup_at` immutabile**: nessuno può anticipare la scadenza di
  una riga scomoda.
* La porta di manutenzione è `zeroerp.maintenance_allow_delete_logs`, la stessa dei log gemelli. Si
  apre solo se la GUC è accesa (`on`, `true` o `1`) **e** la sessione è del migratore
  ([fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta)). Per
  l'applicazione la GUC accesa non apre niente. Si chiede dopo la retention, così il diario registra
  solo le righe vive cancellate.

---

### Codici errore

* `E_UPDATE_NOT_ALLOWED` — modifica di una riga: la storia non si modifica.
* `E_DELETE_NOT_ALLOWED` — cancellazione di una riga non scaduta, a porta chiusa. Nel contesto la
  tabella, l'`id` e `cleanup_at`.

Tutti e due passano da `script.fn_log_and_raise_error`, quindi restano in `error_log` e il backend li
mappa dalla tassonomia.

---

### Test

* `db/pgtap/vendite/test-event-log-append-only.sql` — l'`UPDATE` rifiutato, la riga viva rifiutata
  anche con la porta di manutenzione accesa dall'applicazione.

---

### Note di migrazione

* fino al 2026-08-22 — append-only senza eccezioni, con una `RAISE EXCEPTION` diretta: nessun codice,
  nessuna traccia in `error_log`.
* 2026-08-22 — la riga scaduta si cancella (retention), la porta di manutenzione dei log gemelli
  vale anche qui, e i rifiuti passano da `fn_log_and_raise_error` con un codice
  (`brief-db-event-log-scope-e-riga-parlante`).
* 2026-11-17 — la porta di manutenzione passa da `script.fn_porta_manutenzione_aperta`: solo il
  migratore la apre, con la riga nel diario (`brief-db-seed-primo-impianto-non-si-riscrive`). La
  pagina descriveva ancora il corpo di prima del 2026-08-22: riscritta sul corpo vivo.

---

{% include-markdown "signature-core.md" %}
