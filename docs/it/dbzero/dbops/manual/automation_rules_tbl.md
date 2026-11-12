## 📘 Documentazione Concettuale – Tabella `dbops.automation_rules_tbl`

> **Ultimo aggiornamento**: 12 novembre 2026
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
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id) — regola `TX_ID`
> * [dbops.fn_run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update) — regola `AUDIT_UPDATE`
> * [dbops.fn_run_automations_storico_provision](/dbzero/dbops/funzioni/fn_run_automations_storico_provision) — regola `STORICO_PROVISION`
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — regola `STORICO`
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — regola `ATTIVO`
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — regola `LOCK_COLUMNS`
> * [dbops.fn_run_automations_date_validita](/dbzero/dbops/funzioni/fn_run_automations_date_validita) — regola `DATE_VALIDITA`
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — regole `CLEANUP_AT` e `CLEANUP_PURGE`
> * [dbops.fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola) — la regola `CLEANUP_AT` di una tabella, letta da chi scrive la scadenza
> * [dbops.fn_regola_automazione_valida](/dbzero/dbops/funzioni/fn_regola_automazione_valida) — la forma di una regola, letta dal CHECK
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
con che nome (`name_template`) e con quali parametri (`params`). I runner `dbops.fn_run_automations_*` la leggono e montano i
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
con lo stesso modo (`CI` la convergenza del rilascio, `SCHEDULED` i job pgAgent). Le regole
`CLEANUP_AT` e `CLEANUP_PURGE` sono sempre `AUTO`: la scadenza la scrive anche il trigger alla
nascita della riga, che non è un giro.

Più regole dello stesso tipo possono coprire la stessa tabella: si applicano in ordine di
`priority` (più basso prima), poi di `id`. Per la scadenza no: di regole `CLEANUP_AT` su una
tabella ne vale **una sola**, la prima in quell'ordine
([fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola)). Il seed lo usa così: la
regola di una tabella (priorità 190) vince sulla generica su tutte (200), che vale solo dove non
c'è altro.

`rule_type` ed `exec_mode` sono vocabolari chiusi, nella forma canonica (maiuscolo, senza spazi):
CHECK `chk_automation_rules_tbl_rule_type` e `chk_automation_rules_tbl_exec_mode`. In più il CHECK
`chk_automation_rules_tbl_regola_valida` chiede a
[dbops.fn_regola_automazione_valida](/dbzero/dbops/funzioni/fn_regola_automazione_valida) se la
regola è ben formata (template dichiarato, parametri del tipo giusto). Una regola malformata non
entra nel registro, e i runner non devono difendersi da lei.

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
* `CODICE_MAIUSCOLO` — il trigger che porta in maiuscolo le colonne codice dell'ambito.

I vincoli di sovrapposizione, i guard di utility per tipo di ruolo, il blocco delle cancellazioni
e le chiusure delle scadenze hanno registri loro, non stanno qui.

---

### Il nome: il template

`name_template` è il modello del nome del trigger, con i segnaposto `{schema}`, `{table}`,
`{parent}`, `{child}`, `{fk}`, `{op}`, e `{fkhash6}` / `{fkhash6_if_long}` per un hash breve della
FK (il secondo solo se il nome supera i 63 caratteri; il runner ATTIVO lo rende sempre presente
quando due FK darebbero lo stesso nome sulla stessa tabella). Un nome che resta più lungo di 63 caratteri
si tronca e riceve un hash: il nome di un trigger generato si legge su `pg_trigger`, non si
deduce dal template.

Il nome del trigger sta solo qui: i runner non hanno nomi di ripiego. Per le regole che montano
un trigger (`TX_ID`, `AUDIT_UPDATE`, `STORICO`, `LOCK_COLUMNS`, `DATE_VALIDITA`,
`CODICE_MAIUSCOLO`) `name_template` è obbligatorio e non vuoto. Per `ATTIVO` il template è un
oggetto JSON con due modelli, `block` per il padre e `require` per il figlio, e ognuno contiene un
segnaposto `{fkhash6...}`: due FK della stessa coppia devono poter avere due nomi. Le regole
`CLEANUP_*` e `STORICO_PROVISION` non montano trigger e non hanno template: `name_template` è
`NULL`, mai la stringa vuota, che il `CHECK` `chk_automation_rules_tbl_name_template_non_vuoto`
rifiuta (anche di soli spazi). Nel CSV del seed la cella senza template porta il token `NULL`.

---

### Riconoscere un trigger già montato

Ogni runner riconosce il trigger del framework dalla **funzione** che esegue, qualunque nome
abbia ([dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function));
per `ATTIVO`, dagli **argomenti**, cioè dalla FK che il trigger difende. La regola non sceglie una
strategia: il template serve solo a dare il nome al trigger che il runner crea. Così un trigger
montato a mano, o con un nome troncato, non resta invisibile e non ne riceve un secondo.

---

### I parametri che i runner leggono

`params` vale per la riga di regola. Le chiavi che contano sono quelle che i runner **leggono**:

* `STORICO_PROVISION` — `create_gin_index`, se creare l'indice GIN sulla tabella di storico
  (default falso).
* `ATTIVO` — `reconcile_on_change`, la sola chiave letta (default vero). Il seed la dichiara
  esplicitamente.
* `CLEANUP_AT`:
  * `ttl_days` — i giorni di conservazione, obbligatorio, intero ≥ 1 (il CHECK rifiuta una
    regola senza, o con un valore di altro tipo);
  * `base_ts_column` — la colonna da cui contare. Se manca, vale la prima che la tabella ha fra
    `data_insert`, `executed_at`, `occurred_at`, `created_at`; se non ne ha nessuna, la tabella
    non scade (il runner lo dice con un audit `WARN`). ⚠️ Va dichiarata sulla regola della tabella,
    mai su una regola `*all`: è una proprietà della tabella, e un solo valore per tutte sarebbe
    sbagliato per costruzione. Si dichiara dove la tabella ha più colonne candidate e quella
    giusta non è la prima della catena;
  * `apply_on_update` — booleano, se ricalcolare anche le righe che una scadenza ce l'hanno già
    (default falso: si riempiono solo quelle vuote).
* `CLEANUP_PURGE` — `batch_limit`, la dimensione del lotto, intero ≥ 1 (default 5000).

Le chiavi delle regole di scadenza sono un **elenco chiuso**: il CHECK rifiuta una regola
`CLEANUP_AT` con una chiave diversa da `ttl_days`, `apply_on_update`, `base_ts_column`, e una
`CLEANUP_PURGE` con una chiave diversa da `batch_limit`.

`TX_ID`, `AUDIT_UPDATE`, `STORICO`, `LOCK_COLUMNS`, `DATE_VALIDITA` e `CODICE_MAIUSCOLO` non
leggono parametri: `params` è `{}`. In ogni regola `params` è un oggetto JSON. Le colonne di
audit (`data_update`, `user_update`) e quella della scadenza (`cleanup_at`) hanno nome fisso per
contratto: non si configurano.

⭐ Una chiave che nessuno legge non si dichiara: una manopola scollegata invita a girarla e non fa
niente. E una chiave letta si dichiara anche quando vale il suo default, perché chi legge il
registro veda tutte le leve.

---

### Una sola lettura della regola `CLEANUP_AT`

La scadenza di una riga la scrivono in tre: il trigger `dbops.trgfn_cleanup_at_alla_nascita`
all'inserimento, il giro di cleanup sul pregresso e il login sulle tabelle dei tentativi. Tutti e
tre leggono la regola da [fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola): stessa
regola, stessa colonna base, stesse esclusioni. Una riga riceve la stessa scadenza chiunque la
scriva.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — le regole `CLEANUP_AT` e `CLEANUP_PURGE` applicate
  dal giro, con e senza esclusione.
* `db/pgtap/dbops/test-cleanup-at-regola-unica-v1.sql` — una regola `CLEANUP_AT` sola per tabella,
  la stessa per trigger, giro e login; nessuna regola porta `cleanup_column`.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql`,
  `db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` — le regole `CLEANUP_AT`
  per tabella e la scadenza scritta alla nascita.
* `db/pgtap/maintenance/test-cleanup-job-ambito-registro-v1.sql` — il job di cleanup prende
  l'ambito dal registro.
* `db/pgtap/dbops/test-storico-nome-funzione-ritirato-v1.sql`,
  `db/pgtap/dbops/test-storico-salto-trigger-presente-v1.sql` — la regola `STORICO`: il trigger
  si riconosce dalla funzione, e la colonna `existence_strategy` non c'è.
* `db/pgtap/dbops/test-registro-regole-vincoli-v1.sql` — i CHECK del registro (vocabolari e forma
  della regola), l'ambito senza doppi, nessuna funzione che legga `existence_strategy`.
* `db/pgtap/dbops/test-attivo-due-fk-stessa-coppia-v1.sql` — due FK della stessa coppia: due
  trigger con nomi diversi.

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
* 2026-11-08 — esce `existence_strategy`: ogni runner riconosce il trigger dalla funzione (ATTIVO
  dagli argomenti) (`20261109-74`). `params` di `AUDIT_UPDATE` diventa `{}`: `audit_ts` e
  `audit_user` escono, le colonne di audit hanno nome fisso. Entrano i CHECK su `rule_type`,
  `exec_mode` e sulla forma della regola, con `dbops.fn_regola_automazione_valida`
  (`20261109-66`, `20261109-75`); `name_template` è obbligatorio per le regole che montano un
  trigger (brief-db-revisione-dbops D17, D20, D27, D17-bis).
* 2026-11-08 — esce la chiave `cleanup_column` dai `params` delle regole `CLEANUP_*`: la scadenza
  sta sempre in `cleanup_at`. Le chiavi delle regole di scadenza diventano un elenco chiuso, e il
  CHECK della forma ricontrolla le righe (`20261109-92`, `20261109-93`). La regola `CLEANUP_AT`
  che vale su una tabella è una sola, letta da `dbops.fn_cleanup_at_regola` (brief-db-revisione-dbops,
  giro 10b).

---

{% include-markdown "signature-core.md" %}
