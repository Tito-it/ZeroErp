## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_cleanup`

> **Ultimo aggiornamento**: 13 novembre 2026
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
> * [dbops.fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola) — la regola di scadenza della tabella, la stessa del trigger alla nascita
> * [dbops.fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa) — la tabella è esclusa dal cleanup?
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — gli schemi del giro
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — le tabelle del giro
> * [maintenance.proc_automations_cleanup_job](/dbzero/maintenance/funzioni/proc_automations_cleanup_job) — il wrapper che la lancia
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — chi legge il riepilogo e decide il colore della corsa
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — §7, manutenzione e retention

---

### 🎯 Scopo Principale

Il runner del cleanup: per ogni tabella dell'ambito prima scrive la scadenza `cleanup_at` delle
righe che non l'hanno (regola `CLEANUP_AT`), poi cancella a lotti le righe scadute (regole
`CLEANUP_PURGE`), e lascia una riga di esito in `dbops.audit_log` per ogni tabella e regola. Lo lancia il
processo `automations_cleanup`, la domenica su pgAgent e nella convergenza in CI.

---

### Quali tabelle e quali regole

L'ambito sono gli schemi che il chiamante passa o, se non ne passa, quelli del registro
`dbops.automation_scope`; dentro gli schemi, le tabelle semplici che l'ambito ammette. Una tabella
partizionata non si tratta come padre: si trattano le sue partizioni, che sono tabelle semplici.

Su ogni tabella, nell'ordine:

1. **L'esclusione.** Se la tabella ha un'esclusione attiva
   ([fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa)), la salta intera: né
   scadenza né purge.
2. **La scadenza, con una regola sola.** La regola `CLEANUP_AT` è quella di
   [fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola): la più specifica, la
   stessa che il trigger alla nascita applica alle righe nuove. Se la regola c'è ma non si
   applica, il motivo del risolutore è il motivo del salto.
3. **Il purge.** Le regole `CLEANUP_PURGE` abilitate che coprono la tabella, in ordine di priorità
   e poi di `id`.

Le regole `CLEANUP_*` valgono in ogni giro: il CHECK del registro le vuole `AUTO`. La modalità
del giro finisce solo nell'audit.

---

### I parametri di una regola

* **`CLEANUP_AT`**: il termine in giorni, la colonna di base e se ricalcolare anche le scadenze
  già scritte (di default no). Li legge [fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola),
  che sceglie anche la colonna base quando la regola non la dichiara.
* **`CLEANUP_PURGE`**: la dimensione del lotto (di default 5000).

La colonna della scadenza non è un parametro: è sempre `cleanup_at`, e nemmeno i due passi la
ricevono.

⭐ **La colonna di base si dichiara solo dove serve.** È una proprietà della tabella, mentre i
parametri sono della regola: sulla regola generica, che copre ogni tabella, un valore unico sarebbe
sbagliato per costruzione. Si dichiara sulle regole di tabella dove la catena di ripiego
sceglierebbe la colonna sbagliata: `vendite.event_log`, per esempio, ha sia `data_insert` sia
`event_time`, e la sua scadenza si calcola dal secondo.

La forma dei parametri la garantisce il CHECK del registro
([fn_regola_automazione_valida](/dbzero/dbops/funzioni/fn_regola_automazione_valida)): il runner
non converte valori del tipo sbagliato.

---

### ⭐ Ogni salto lascia una riga, e i salti dichiarati sono `WARN`

Il runner non tace su una tabella che non pulisce. Ogni salto ha la sua riga di audit, con il
motivo nella chiave `skip_reason`:

| Motivo | Quando | Esito |
| --- | --- | --- |
| `EXCLUDED` | la tabella è in `automation_cleanup_exclusions` con l'esclusione attiva, che prevale su ogni regola | `WARN` |
| `NO_CLEANUP_COLUMN` | la tabella non ha la colonna `cleanup_at` | `WARN` |
| `MISSING_BASE_TS_COLUMN` | la colonna di base dichiarata non esiste, o la catena di ripiego non ne trova nessuna | `WARN` |
| `BLOCKED_BY_TABLE` | la tabella si è opposta: un trigger append-only, un guard sul `DELETE` | `ERROR` |

⚠️ `MISSING_BASE_TS_COLUMN` non rompe niente, ma la tabella non riceve scadenze: è un difetto
silenzioso, da cercare negli audit e non fra gli errori.

Le righe con la colonna base vuota non si toccano: non ricevono scadenza finché la base non c'è.

Una regola applicata lascia una riga `OK` (`DRYRUN` in simulazione) con le righe toccate.

---

### Una tabella che rifiuta non ferma il giro

Ogni passo — la scadenza, ogni purge — gira in una sottotransazione. Se la tabella rifiuta, il
suo lavoro si annulla, il rifiuto finisce nell'audit con SQLSTATE e contesto, e il giro passa al
passo e alla tabella successivi. L'esito è `ERROR` e non `WARN` di proposito: i `WARN` sono salti dichiarati, questo è
una tabella che si è opposta, e va distinta a colpo d'occhio.

⛔ Un annullamento resta un annullamento: se qualcuno ferma il giro, il giro si ferma.

---

### ⭐ Il riepilogo: una tabella bloccata rende rossa la corsa

Il runner restituisce un riepilogo del giro:

| Chiave | Che cosa conta |
| --- | --- |
| `_applicate` | le regole applicate (`OK`, o `DRYRUN` in simulazione) |
| `_saltate` | i salti dichiarati, i `WARN` della tabella sopra |
| `_saltate_motivi` | gli stessi salti, contati per motivo |
| `_falliti` | le tabelle che si sono opposte (`BLOCKED_BY_TABLE`) |
| `_righe` | le righe toccate dalle regole applicate |
| `_dettaglio` | i rifiuti, uno per uno: tabella, regola, SQLSTATE e messaggio |

Il job lo lancia dentro [fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log), che legge
il riepilogo: con `_falliti` maggiore di zero la corsa è **rossa** (`E_JOB_ESITO_CON_SCARTI`,
«riuscita con scarti») e compare fra le corse da guardare, ma le tabelle pulite restano pulite.

⚠️ I salti dichiarati si contano e non si elencano. Una regola che copre ogni tabella ne produce
uno per ogni tabella senza la colonna di scadenza, e il loro elenco finirebbe a ogni corsa nel
giornale del job. Il dettaglio è riservato a ciò che va guardato; il motivo di un salto si legge
nell'audit.

---

### Codici errore

Il runner non solleva codici suoi. I rifiuti dei passi finiscono nell'audit; esce soltanto
l'annullamento.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — un'esclusione attiva impedisce la cancellazione e
  una disattivata la lascia fare (test 11-12); una tabella che rifiuta non ferma il giro, resta
  com'era, il purge della stessa tabella, che viene dopo, gira, e il rifiuto lascia una riga `ERROR` con
  lo SQLSTATE (test 13-16); il riepilogo della stessa chiamata conta il rifiuto in `_falliti`, con
  la tabella nel dettaglio, e la regola passata in `_applicate` (test 17-18); l'app esegue ancora
  il runner (test 19).
* `db/pgtap/maintenance/test-cleanup-job-ambito-registro-v1.sql` — il wrapper passa l'ambito del
  registro, ogni regola `CLEANUP_*` attiva punta a uno schema dell'ambito, e il runner gira in
  simulazione con quell'ambito.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — i quattro registri di `dbops` sono
  nell'ambito, hanno la loro regola, e la colonna di base di ogni regola esiste.
* `db/pgtap/dbops/test-cleanup-at-regola-unica-v1.sql` — sulla stessa riga il runner scrive la
  scadenza che il trigger alla nascita aveva scritto; non tocca una riga con la base vuota né una
  tabella esclusa.

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
* 2026-11-04 — il runner restituisce il riepilogo invece di niente, e una tabella bloccata rende
  rossa la corsa del job (D40 di `brief-db-revisione-dbops`). Prima il rifiuto stava solo
  nell'audit e la corsa era verde. Il cambio del tipo restituito ha richiesto di ricreare la
  funzione; le righe di audit sono le stesse di prima.
* 2026-11-08 — la scadenza viene da `dbops.fn_cleanup_at_regola`, una regola sola per tabella, e
  l'esclusione da `dbops.fn_cleanup_esclusa` (`20261109-89`, brief-db-revisione-dbops, giro 10b).
  Prima il runner applicava in ordine tutte le regole `CLEANUP_AT` che coprivano la tabella,
  compresa la generica, e una regola successiva che ricalcolava le scadenze sovrascriveva quella
  più specifica. Escono il parametro `cleanup_column` (la colonna è sempre `cleanup_at`) e il salto
  `MISSING_TTL_DAYS`, che il CHECK del registro rende impossibile.
* 2026-11-09 — chiama `fn_apply_cleanup_at` e `fn_purge_cleanup_expired` con le firme nuove,
  senza la colonna della scadenza (`20261110-36`, brief-db-revisione-dbops, giro 10c). Il
  comportamento del giro non cambia.
* 2026-11-13 — la regola vale per la tabella che nomina: `target_table` si confronta con `=`,
  non più con `ILIKE`, che faceva del `_` di un nome un jolly (una regola su `event_log` copriva
  anche una `eventXlog`). `*all` ha una forma sola, garantita dal CHECK
  `chk_automation_rules_tbl_target_table_nome_esatto` (`90_end/20261112-66`). Testata ri-ancorata
  con `%TYPE`, firma invariata (`20261112-73`).

---

{% include-markdown "signature-core.md" %}
