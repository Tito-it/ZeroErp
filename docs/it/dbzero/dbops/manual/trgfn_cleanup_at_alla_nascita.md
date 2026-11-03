## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_cleanup_at_alla_nascita`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` da cui legge termine e colonna di base
> * [vendite.event_log](/dbzero/vendite/tabelle/event_log) — il primo registro su cui è montato
> * [dbops.error_log](/dbzero/dbops/tabelle/error_log) — un registro su cui di proposito non è montato
>
> Approfondimento funzioni:
>
> * [dbops.fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) — la regola che copre la tabella
> * [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — l'altra via, per il pregresso
> * [vendite.trgfn_logs_guard_delete](/dbzero/vendite/funzioni/trgfn_logs_guard_delete) — lascia cancellare le righe scadute dei log di fatturazione
> * [vendite.trgfn_event_log_append_only](/dbzero/vendite/funzioni/trgfn_event_log_append_only) — lo stesso, per il diario degli eventi
>
> Guide:
>
> * [Linee guida Trigger](/linee-guida-trigger) — le fasi, e perché questa è `m50`
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — §7, manutenzione e retention

---

### 🎯 Scopo Principale

Trigger `BEFORE INSERT` generico che scrive la scadenza (`cleanup_at`) di una riga quando nasce:
colonna di base più il termine della regola `CLEANUP_AT` che copre la tabella. Se nessuna regola
la copre, la scadenza resta vuota e la riga non scade mai: in dubbio si conserva.

---

### Dove è montato

Sui registri che devono scadere senza essere riscritti: il diario `vendite.event_log`, i log di
fatturazione (`fatture_log`, `fatturazione_lotti_log`, `fatturazione_lotti_task_runs`), il log
del push delle commesse, le chiavi di idempotenza e il registro delle richieste di `dbops`, e i
tre registri dei tentativi di login di `config`. L'elenco vivo è nella sezione trigger della scheda
di ogni tabella; il nome del trigger è `trg_<tabella>_m50_cleanup_at_ins`.

⛔ **Non è montato sui registri che si scrivono anche via dblink** — `dbops.error_log` e
`dbops.audit_log`: lì scrive una sessione con un ruolo che non legge il registro delle regole, e il
trigger farebbe fallire proprio la registrazione dell'errore. La loro scadenza la scrive il job.

---

### ⭐ Perché alla nascita e non con l'UPDATE del job

Il framework standard scrive la scadenza con un `UPDATE` periodico
([fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at)). Su un registro quell'`UPDATE`:

* riscrive data e utente di aggiornamento su ogni riga fresca — e su `fatture_log` l'utente di
  aggiornamento dice chi ha ammesso un critico;
* passa dai trigger di `UPDATE`, e su un registro append-only è vietato;
* lascia la scadenza modificabile dal job.

Alla nascita la riga sa già quando scade, e nessun trigger di `UPDATE` si sveglia. Il job resta
per il pregresso: con le regole che riempiono solo i vuoti tocca le righe nate prima del trigger,
una volta.

---

### La colonna di base si legge dalla regola

La base è la colonna che la regola dichiara, letta dalla riga in arrivo: la stessa che il job usa
sul pregresso, così righe nuove e righe vecchie hanno la scadenza calcolata sullo stesso orario.

Se la regola non dichiara la colonna, se la colonna non esiste sulla tabella o se sulla riga è
vuota, la base è l'istante della transazione.

⚠️ Su questo punto il job ragiona diversamente: senza una colonna dichiarata cerca la prima che
esiste fra `data_insert`, `executed_at`, `occurred_at`, `created_at`. Le due vie coincidono solo
quando quella colonna vale l'istante dell'inserimento.

⚠️ La colonna scritta è sempre `cleanup_at`, qualunque colonna di scadenza dichiari la regola.

---

### ⚠️ Sovrascrive, non completa

La funzione non guarda se il chiamante ha già passato una scadenza: un diario non lascia scegliere
a chi scrive quando la riga scade. Chi deve produrre una riga già scaduta — un pgTAP — retrodata la
colonna di base, e il trigger fa il resto.

Una scadenza scritta dopo la nascita, da chi ne ha il diritto, non passa di qui: il trigger scatta
solo all'`INSERT`. È il caso dei tentativi di login, la cui scadenza si sposta a ogni fallimento.

---

### Fase `m50`

È una derivazione, non un guard: va dopo i guard e le normalizzazioni `a…` — in particolare dopo
il trigger di `fatture_log` che riscrive l'orario della riga con quello reale — e prima degli
effetti finali `z…`. Un trigger in fase `a10` scatterebbe prima della riscrittura dell'orario
(`cleanup` viene prima di `orario` in ordine alfabetico) e calcolerebbe la scadenza su un orario
che la riga non avrà.

---

### Codici errore

La funzione non solleva codici suoi. Un termine nella regola che non è un numero intero fa fallire
l'`INSERT` con l'errore di conversione.

---

### Test

* `db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` — i registri di
  fatturazione e push nascono con la colonna di base più 750 giorni, una riga retrodatata nasce già
  scaduta, su `fatture_log` la scadenza segue l'orario riscritto.
* `db/pgtap/vendite/test-event-log-deriva-scope.sql` — sul diario degli eventi la scadenza è
  l'orario dell'evento più il termine della regola (test 4).
* `db/pgtap/dbops/test-idempotency-prenota-v1.sql` — il trigger è montato sulle chiavi di
  idempotenza e sul registro delle richieste, e scrive la scadenza della loro regola.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — il trigger c'è su chiavi di idempotenza e
  registro delle richieste, e non c'è su `error_log` e `audit_log` (test 4).
* `db/pgtap/config/test-credenziale-login-v1.sql` — una riga di provenienza nasce con l'ultimo
  fallimento più il termine.

---

### Note di migrazione

* 2026-09-18 — nasce per il diario degli eventi e i registri di fatturazione e push (passo D di
  `analisi-osservabilita-log.md`); la scadenza di `event_log` prima la calcolava
  `vendite.trgfn_event_log_deriva_scope`.
* 2026-09-25 — montato sui registri dei tentativi di login.
* 2026-10-23 — montato sulle chiavi di idempotenza e sul registro delle richieste.

---

{% include-markdown "signature-core.md" %}
