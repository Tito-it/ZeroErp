## 📘 Documentazione Concettuale – Tabella `dbops.automation_rules_tbl`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito: una regola agisce solo sulle tabelle che vi rientrano
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — i nomi di colonna non standard che le regole usano
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — le colonne della regola `LOCK_COLUMNS`
> * [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions) — le tabelle sottratte alle regole `CLEANUP_*`
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove i runner scrivono che cosa hanno fatto
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations) — l'orchestratore a mano
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id) — regola `TX_ID`
> * [dbops.fn_run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update) — regola `AUDIT_UPDATE`
> * [dbops.fn_run_automations_storico_provision](/dbzero/dbops/funzioni/fn_run_automations_storico_provision) — regola `STORICO_PROVISION`
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — regola `STORICO`
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — regola `ATTIVO`
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — regola `LOCK_COLUMNS`
> * [dbops.fn_run_automations_date_validita](/dbzero/dbops/funzioni/fn_run_automations_date_validita) — regola `DATE_VALIDITA`
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — regole `CLEANUP_AT` e `CLEANUP_PURGE`
> * [dbops.fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) — la regola `CLEANUP_AT` letta alla nascita della riga
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — costruisce il nome del trigger dal template
> * [dbops.fn_schema_match](/dbzero/dbops/funzioni/fn_schema_match) — il confronto fra lo schema della regola e quello della tabella
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Il registro delle **regole di automazione**: ogni riga dice quale automatismo applicare
(`rule_type`), su quali tabelle (`target_schema`, `target_table`), in quale giro (`exec_mode`),
con che nome (`name_template`), come riconoscere un trigger già montato (`existence_strategy`) e
con quali parametri (`params`). I runner `dbops.fn_run_automations_*` la leggono e montano i
trigger che le regole dichiarano.

Un automatismo che il database genera dalla struttura delle tabelle — audit, `tx_id`, storico,
ATTIVO, lucchetti di colonna, regola del periodo, scadenza dei registri — si accende o si spegne
qui, non scrivendo trigger a mano.

---

### Su quali tabelle agisce una regola

* `target_schema` — uno schema, o `*all` per tutti. Il confronto non distingue maiuscole e
  minuscole.
* `target_table` — una tabella, un modello con `%` (confrontato senza distinguere maiuscole), o
  `*all` per tutte. Non è mai vuoto: il default è `*all`.

In ogni caso la regola agisce solo sulle tabelle dell'**ambito** (`dbops.automation_scope`):
una regola su uno schema fuori ambito non ha effetto, e niente lo segnala.

`exec_mode` dice in quale giro la regola vale: `AUTO` in ogni giro, altrimenti solo nel giro
con lo stesso modo (`CI` la convergenza del rilascio, `SCHEDULED` i job pgAgent).

Più regole dello stesso tipo possono coprire la stessa tabella: si applicano in ordine di
`priority` (più basso prima), poi di `id`. Il seed usa questo ordine per le scadenze: le regole
`CLEANUP_AT` di una tabella (priorità 190) vengono prima di quella generica su tutte (200).

⚠️ `rule_type`, `exec_mode` ed `existence_strategy` sono testo libero, senza vincolo: un valore
scritto male non solleva niente, e la regola resta inerte.

---

### I tipi di regola

* `TX_ID` — il trigger che genera `tx_id` sulle tabelle che hanno la colonna.
* `AUDIT_UPDATE` — il trigger che scrive `data_update` e `user_update` a ogni modifica.
* `STORICO_PROVISION` — prepara la tabella di storico in `storico`.
* `STORICO` — il trigger di storico, su modifica e cancellazione.
* `ATTIVO` — per ogni FK la coppia di guard: sul padre il **blocco** della disattivazione se ha
  figli attivi, sul figlio il **requisito** di un padre attivo. Solo per le FK la cui colonna
  finisce in `_id`.
* `LOCK_COLUMNS` — il lucchetto di colonna: `codice_interno` più le colonne di
  `dbops.automation_lock_columns`.
* `DATE_VALIDITA` — il guard della regola del periodo sulle tabelle che hanno `valido_dal` e
  `valido_al`.
* `CLEANUP_AT` — la scadenza `cleanup_at` delle righe di un registro, con un numero di giorni.
* `CLEANUP_PURGE` — la cancellazione, a lotti, delle righe scadute.

I vincoli di sovrapposizione, i guard di utility per tipo di ruolo, il blocco delle cancellazioni
e le chiusure delle scadenze hanno registri loro, non stanno qui.

---

### Il nome: il template

`name_template` è il modello del nome del trigger, con i segnaposto `{schema}`, `{table}`,
`{parent}`, `{child}`, `{fk}`, `{op}`, e `{fkhash6}` / `{fkhash6_if_long}` per un hash breve della
FK (il secondo solo se il nome supera i 63 caratteri). Un nome che resta più lungo di 63 caratteri
si tronca e riceve un hash: il nome di un trigger generato si legge su `pg_trigger`, non si
deduce dal template.

Per `ATTIVO` il template è un oggetto con due modelli, `block` per il padre e `require` per il
figlio. Le regole `CLEANUP_*` non montano trigger e non hanno template.

---

### Riconoscere un trigger già montato

`existence_strategy` dice come il runner decide che il trigger c'è già: `BY_NAME` per nome,
`BY_FUNCTION` per la funzione che il trigger chiama, `BOTH` se basta uno dei due. Il seed usa
`BOTH`.

⚠️ Per `LOCK_COLUMNS` non conta: la convergenza riconosce un lock vivo sempre dalla funzione,
qualunque nome abbia, perché un lock scritto a mano non resti invisibile. Il template lì serve
solo a dare il nome al trigger che crea.

---

### I parametri che i runner leggono

`params` vale per la riga di regola. Le chiavi che contano sono quelle che i runner **leggono**:

* `AUDIT_UPDATE` — `audit_ts` e `audit_user`, i nomi delle due colonne (default `data_update` e
  `user_update`); un override per tabella in `dbops.automation_overrides_cols` vince.
* `STORICO_PROVISION` — `create_gin_index`, se creare l'indice GIN sulla tabella di storico
  (default falso).
* `ATTIVO` — `reconcile_on_change`, la sola chiave letta (default vero). Il seed la dichiara
  esplicitamente.
* `CLEANUP_AT`:
  * `ttl_days` — i giorni di conservazione, obbligatorio: senza, la regola si salta con un audit
    `WARN`;
  * `cleanup_column` — la colonna della scadenza (default `cleanup_at`);
  * `base_ts_column` — la colonna da cui contare. Se manca, il runner prende la prima che la
    tabella ha fra `data_insert`, `executed_at`, `occurred_at`, `created_at`, e se non ne ha
    nessuna salta la tabella con un audit `WARN`. ⚠️ Va dichiarata sulla regola della tabella,
    mai su una regola `*all`: è una proprietà della tabella, e un solo valore per tutte sarebbe
    sbagliato per costruzione. Si dichiara dove la tabella ha più colonne candidate e quella
    giusta non è la prima della catena;
  * `apply_on_update` — se ricalcolare anche le righe che una scadenza ce l'hanno già (default
    falso: si riempiono solo quelle vuote).
* `CLEANUP_PURGE` — `cleanup_column` (default `cleanup_at`) e `batch_limit`, la dimensione del
  lotto (default 5000).

`TX_ID`, `STORICO`, `LOCK_COLUMNS` e `DATE_VALIDITA` non leggono parametri.

⭐ Una chiave che nessuno legge non si dichiara: una manopola scollegata invita a girarla e non fa
niente. E una chiave letta si dichiara anche quando vale il suo default, perché chi legge il
registro veda tutte le leve.

---

### ⚠️ Due lettori della regola `CLEANUP_AT`

La scadenza di una riga si calcola in due posti: il giro di cleanup per le righe che non ce l'hanno,
e il trigger `dbops.trgfn_cleanup_at_alla_nascita`, che la scrive all'inserimento leggendo la regola
con [fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params). Il trigger prende la
prima regola `CLEANUP_AT` attiva che copre la tabella e dichiara `ttl_days`, senza guardare
`exec_mode` né le esclusioni di `dbops.automation_cleanup_exclusions`.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — le regole `CLEANUP_AT` e `CLEANUP_PURGE` applicate
  dal giro, con e senza esclusione.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql`,
  `db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` — le regole `CLEANUP_AT`
  per tabella e la scadenza scritta alla nascita.
* `db/pgtap/maintenance/test-cleanup-job-ambito-registro-v1.sql` — il job di cleanup prende
  l'ambito dal registro.
* `db/pgtap/dbops/test-storico-nome-funzione-ritirato-v1.sql`,
  `db/pgtap/dbops/test-storico-salto-trigger-presente-v1.sql` — la regola `STORICO` con
  `BY_FUNCTION` e `BOTH`.

---

### Note di migrazione

* 2026-01-01 — la tabella `automation_fk_exclusions`, che escludeva coppie padre/figlio dalla
  regola `ATTIVO`, è ritirata (il filtro era già spento). Oggi non c'è un'esclusione per FK: per
  ritirare configurazione senza toccare il guard si usa `obsoleto_dal`, o si restringe l'ambito.
* 2026-09-01 — `params` di `ATTIVO`: escono `mode`, `include_no_action`, `cascade_children`,
  `require_active_parent`, `block_if_child_no_attivo`, dichiarate e mai lette (`cascade_children`
  diceva perfino l'opposto del motore), ed entra `reconcile_on_change`, l'unica letta e fino ad
  allora non dichiarata. `params` di `STORICO` diventa vuoto: `apply_triggers` era dichiarata e
  mai letta; `drop_legacy_ud` era letta e mai dichiarata, ed è uscita col suo ramo, che cercava
  nomi di trigger che non sono mai esistiti. Dallo stesso giorno la regola di `vendite.event_log`
  dichiara `base_ts_column` = `event_time`, la colonna da cui conta anche il trigger.
* 2026-09-26 — `existence_strategy` non si legge più per `LOCK_COLUMNS`
  (`brief-db-lock-di-colonna-fuori-registro`).

---

{% include-markdown "signature-core.md" %}
