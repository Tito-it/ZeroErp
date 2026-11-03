## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_cleanup`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` e `CLEANUP_PURGE`
> * [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions) — le tabelle che il giro salta comunque
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito: quali tabelle il giro guarda
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove ogni tabella lascia il suo esito
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — il passo che scrive la scadenza
> * [dbops.fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired) — il passo che cancella le righe scadute
> * [dbops.fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) — la stessa regola, letta da chi scrive la scadenza alla nascita
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — gli schemi del giro
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — le tabelle del giro
> * [maintenance.proc_automations_cleanup_job](/dbzero/maintenance/funzioni/proc_automations_cleanup_job) — il wrapper che la lancia
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — §7, manutenzione e retention

---

### 🎯 Scopo Principale

Il runner del cleanup: per ogni tabella dell'ambito applica le regole `CLEANUP_AT` (scrive la
scadenza `cleanup_at` delle righe) e `CLEANUP_PURGE` (cancella a lotti le righe scadute) che la
coprono, e lascia una riga di esito in `dbops.audit_log` per ogni tabella e regola. Lo lancia il
processo `automations_cleanup`, la domenica su pgAgent e nella convergenza in CI; la chiama anche
l'orchestratore `dbops.fn_run_automations` quando gli si chiede la parte `CLEANUP`.

---

### Quali tabelle e quali regole

L'ambito sono gli schemi che il chiamante passa o, se non ne passa, quelli del registro
`dbops.automation_scope`; dentro gli schemi, le tabelle semplici che l'ambito ammette. Una tabella
partizionata non si tratta come padre: si trattano le sue partizioni, che sono tabelle semplici.

Per ogni tabella il runner applica, in ordine di priorità e poi di `id`, **tutte** le regole
abilitate che la coprono — per schema, e per nome o con il carattere jolly — e la cui modalità è
`AUTO` o quella del giro. Con le regole del seed, che riempiono solo le scadenze vuote, la prima
regola `CLEANUP_AT` che si applica decide la scadenza, e le successive non trovano più niente da
riempire: per questo la regola di una tabella ha una priorità più bassa della generica.

⚠️ Una regola successiva che ricalcola anche le scadenze già scritte sovrascrive quella della
regola più specifica: il «vince la più specifica» di
[fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) qui vale solo per le regole
che riempiono i vuoti.

---

### I parametri di una regola

* **`CLEANUP_AT`** legge il termine in giorni, che è obbligatorio, la colonna di base, la colonna di
  scadenza (di default `cleanup_at`) e se ricalcolare anche le scadenze già scritte (di default no).
* **`CLEANUP_PURGE`** legge la colonna di scadenza e la dimensione del lotto (di default 5000).

⭐ **La colonna di base si dichiara solo dove serve.** È una proprietà della tabella, mentre i
parametri sono della regola: sulla regola generica, che copre ogni tabella, un valore unico sarebbe
sbagliato per costruzione. Senza colonna dichiarata il runner prende la prima che esiste fra
`data_insert`, `executed_at`, `occurred_at`, `created_at`. Si dichiara sulle regole di tabella
dove quella catena sceglierebbe la colonna sbagliata, o dove la scadenza la scrive anche il trigger
alla nascita, che legge solo la colonna dichiarata: `vendite.event_log`, per esempio, ha sia
`data_insert` sia `event_time`, e la sua scadenza si calcola dal secondo.

⚠️ I parametri si convertono prima di entrare nella rete che protegge il giro: un termine o una
dimensione del lotto che non sono numeri interi, o un ricalcolo che non è un booleano, fermano il
giro intero, non solo la tabella.

---

### ⭐ Ogni salto lascia una riga, e i salti dichiarati sono `WARN`

Il runner non tace su una tabella che non pulisce. Ogni salto ha la sua riga di audit, con il
motivo nella chiave `skip_reason`:

| Motivo | Quando | Esito |
| --- | --- | --- |
| `EXCLUDED` | la tabella è in `automation_cleanup_exclusions` con l'esclusione attiva, che prevale su ogni regola | `WARN` |
| `NO_CLEANUP_COLUMN` | la colonna di scadenza della regola non esiste sulla tabella | `WARN` |
| `MISSING_TTL_DAYS` | una regola `CLEANUP_AT` senza termine | `WARN` |
| `MISSING_BASE_TS_COLUMN` | la colonna di base dichiarata non esiste, o la catena di ripiego non ne trova nessuna | `WARN` |
| `BLOCKED_BY_TABLE` | la tabella si è opposta: un trigger append-only, un guard sul `DELETE`, un termine negativo | `ERROR` |

⚠️ `MISSING_BASE_TS_COLUMN` non rompe niente, ma la tabella non riceve scadenze: è un difetto
silenzioso, da cercare negli audit e non fra gli errori.

Una regola applicata lascia una riga `OK` (`DRYRUN` in simulazione) con le righe toccate.

---

### Una tabella che rifiuta non ferma il giro

Ogni regola gira in una sottotransazione. Se la tabella rifiuta, il suo lavoro si annulla, il
rifiuto finisce nell'audit con SQLSTATE e contesto, e il giro passa alla regola e alla tabella
successive. L'esito è `ERROR` e non `WARN` di proposito: i `WARN` sono salti dichiarati, questo è
una tabella che si è opposta, e va distinta a colpo d'occhio.

⛔ Un annullamento resta un annullamento: se qualcuno ferma il giro, il giro si ferma.

Il runner non restituisce niente: l'esito per tabella sta solo nell'audit, e la corsa del job
risulta verde anche quando una tabella è stata bloccata.

---

### Codici errore

Il runner non solleva codici suoi. I rifiuti dei passi finiscono nell'audit; escono soltanto
l'annullamento e gli errori di conversione dei parametri di una regola.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — un'esclusione attiva impedisce la cancellazione e
  una disattivata la lascia fare (test 11-12); una tabella che rifiuta non ferma il giro, resta
  com'era, la regola successiva sulla stessa tabella gira, e il rifiuto lascia una riga `ERROR` con
  lo SQLSTATE (test 13-16).
* `db/pgtap/maintenance/test-cleanup-job-ambito-registro-v1.sql` — il wrapper passa l'ambito del
  registro, ogni regola `CLEANUP_*` attiva punta a uno schema dell'ambito, e il runner gira in
  simulazione con quell'ambito.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — i quattro registri di `dbops` sono
  nell'ambito, hanno la loro regola, e la colonna di base di ogni regola esiste.

---

### Note di migrazione

* 2026-08-23 — una tabella che rifiuta non ferma più il giro: prima non c'era nessuna rete, e un
  solo veto fermava l'intera passata senza che nessuno lo sapesse. Nasce il salto
  `BLOCKED_BY_TABLE`.
* 2026-09-01 — la regola di `vendite.event_log` dichiara la colonna di base `event_time`: il
  ripiego avrebbe preso `data_insert`, e pregresso e righe nuove avrebbero avuto due scadenze
  calcolate su orari diversi.
* 2026-11-03 — il wrapper non fissa più lo schema `dbops`: l'ambito si legge dal registro
  (`brief-db-revisione-maintenance` D4).

---

{% include-markdown "signature-core.md" %}
