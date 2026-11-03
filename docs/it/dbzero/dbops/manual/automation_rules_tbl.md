## 📘 Documentazione Concettuale – Tabella `dbops.automation_rules_tbl`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle
> 
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)      
> [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols)
>       
Approfondimento funzioni:  
> 
[dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)      
> [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)      
> 
Orchestratori: 
> 
[dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations), 
> [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id),   
> [dbops.run_automations_audit_update](/dbzero/dbops/funzioni/fn_run_automations_audit_update),   
> [dbops.run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico),   
>  [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo)
>  [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)
### 🎯 Scopo Principale
**(latest review 13-01-26)**
Configurare **regole di automazione** per generare/applicare trigger e vincoli in modo dichiarativo. Ogni riga descrive **cosa** applicare (*rule_type*), **dove** (*target_schema/target_table*), **quando** (*exec_mode*), **come chiamarlo** (*name_template*), **come verificare l'esistenza** (*existence_strategy*), e **con quali parametri** (*params*).

Gli orchestratori leggono questa tabella e applicano le regole nell'ordine di **priority** (poi per `id`).

---

### Campi chiave e semantica

* **enabled** *(boolean)* – abilita la regola.
* **rule_type** *(text)* – tipo di automatismo:

  * `TX_ID` → trigger `BEFORE INSERT/UPDATE` con `dbops.trgfn_tx_id_managed()` su tabelle che hanno `tx_id uuid`.
  * `AUDIT_UPDATE` → trigger `BEFORE UPDATE` con `script.trgfn_audit_data_user_generic()`.
  * `STORICO` → trigger su `BEFORE UPDATE` e `BEFORE DELETE` verso `storico.<table>_storico` con `script.trgfn_storico_generic(...)`.
  * `LOCK_COLUMNS` → trigger `BEFORE UPDATE OF ...` con `script.trgfn_lock_columns(...)` su colonne critiche.
  * `CLEANUP_AT` → calcolo `cleanup_at` con TTL fisso per tabella.
  * `CLEANUP_PURGE` → cancellazione record scaduti (batch) su `cleanup_at`.
* `ATTIVO` → set di trigger basati su FK: **block** sul padre + **require** sul figlio (no cascade).
* **target_schema** *(text)* – schema di destinazione.
* **target_table** *(text, opzionale)* – nome tabella **o pattern LIKE** (`%`) per filtrare. Se **NULL**, tutte le tabelle dello schema per quel *rule_type*.
* **exec_mode** *(text)* – `AUTO` | `CI` | `SCHEDULED`. L'orchestratore applica le regole con `exec_mode=p_exec_mode` **o** `AUTO`.
* **name_template** *(text)* – template del **nome trigger**. Placeholders disponibili:

  * `{schema}` `{table}` `{parent}` `{child}` `{fk}` `{op}` (`op` ∈ `upd|dlt`).
  * Per `ATTIVO` è un **JSON** con le chiavi operative `block` e `require` (la chiave `cascade` resta legacy/non operativa).
  * Default consigliati:

    * `TX_ID`: `trg_{table}_ins_upd_gen_tx_id`
    * `AUDIT_UPDATE`: `trg_upd_{table}_audit_data_user`
    * `STORICO`: `trg_{table}_{op}_storico`
    * `ATTIVO/block`: `trg_{parent}_a10_{child}_block_deact_upd`
    * `ATTIVO/require`: `trg_{child}_a10_{parent}_require_attivo_ins_upd`
* **existence_strategy** *(text)* – come determinare se il trigger esiste già:

  * `BY_NAME` → cerca per nome (derivato dal template);
  * `BY_FUNCTION` → cerca per funzione invocata (schema.nome);
  * `BOTH` → vero se almeno uno dei due è trovato.

  ⚠️ **Per `LOCK_COLUMNS` non si legge più** (dal 2026-09-26): la convergenza
  riconosce un lock vivo **sempre** dalla funzione `script.trgfn_lock_columns`,
  qualunque nome abbia, altrimenti un lock scritto a mano resterebbe invisibile.
  Il nome serve solo a creare. Vedi `dbops.fn_lock_columns_divergenze`.
* **params** *(jsonb)* – parametri specifici del *rule_type* (vedi sotto).
* **priority** *(int)* – ordine di applicazione (più basso = prima). A parità, ordinamento per `id`.
* **note** *(text)* – libero.
* **Audit** – `user_insert/data_insert`, `user_update/data_update` gestiti da trigger di audit.

> ℹ️ **Lunghezza nome trigger**: PostgreSQL limita a **63** caratteri. Se usi template lunghi, prevedi abbreviazioni o hashing nel naming helper (`fn_name_from_template`).

---

### Parametri `params` per *rule_type*

* **TX_ID**: *(tipicamente vuoto)*
* **AUDIT_UPDATE**: `{ "audit_ts": "data_update", "audit_user": "user_update" }`
  (Sovrascrivibile anche via `automation_overrides_cols`)
* **STORICO**: *(tipicamente vuoto)*
  La FK dello storico può essere data da override `STORICO_FK` in `automation_overrides_cols`.
* **LOCK_COLUMNS**: *(tipicamente vuoto)*
  Usa `name_template` per il nome del trigger di lock. Le colonne stanno in
  `dbops.automation_lock_columns`; l'idempotenza viene dalla convergenza
  (`dbops.fn_lock_columns_divergenze`), non da `existence_strategy`.
* **ATTIVO**:

  * `reconcile_on_change` *(boolean, default `true`)* → **è l'unica chiave che
    l'orchestratore legge** (`dbops.fn_run_automations_attivo`), con un
    `COALESCE(..., true)`: vale `true` sia dichiarata sia assente.
    ✅ **Dichiarata esplicitamente dal 2026-09-01**: da quel giorno il `params`
    della riga `ATTIVO` è `{"reconcile_on_change": true}` — l'insieme delle
    chiavi **dichiarate** e quello delle chiavi **lette** coincidono, verificato
    nei due versi su `pg_proc`.
  * ~~`mode`, `include_no_action`, `cascade_children`, `require_active_parent`,
    `block_if_child_no_attivo`~~ ⛔ **RIMOSSE TUTTE E CINQUE il 2026-09-01**
    (decisione di Tid), e al loro posto è stata dichiarata l'unica chiave che
    il motore legge davvero.

  > 📌 **Perché sono uscite, e non era «non venivano lette».** La nota
  > precedente diceva che erano *«mantenute per retro-compatibilità»*: una
  > formula che le fa sembrare inerti e innocue. Non lo erano.
  >
  > * `block_if_child_no_attivo` e `include_no_action` erano dichiarate `true` e
  >   **descrivevano ciò che il motore già fa cablato**. Implementarle non
  >   avrebbe aggiunto un comportamento: avrebbe aggiunto la possibilità di
  >   metterle a `false`, cioè **interruttori per spegnere protezioni** — la
  >   seconda su **684 FK di 870**;
  > * `cascade_children` dichiarava l'**opposto** del motore (spegni i figli
  >   invece di rifiutare), ed è incompatibile con la prima: erano `true`
  >   entrambe. La funzione che l'avrebbe implementata,
  >   `dbops.trgfn_soft_delete_cascade`, è stata droppata il 2026-01-01 come
  >   *«legacy (ATTIVO old design)»*;
  > * `require_active_parent` è uscita con loro: **anche lei non è letta**. La
  >   sola occorrenza nel database è in un **commento** di
  >   `vendite.fn_genera_ddt_riconsegna`, che con questa regola non c'entra.
  >
  > ⚠️ **E `mode` era nello stesso stato**: dichiarata `"auto"`, letta da
  > nessuno — è uscita con le altre («se è nella stessa condizione, sì»).
  > ⭐ Il suo conteggio la faceva sembrare la più usata di tutte (**79
  > occorrenze**): erano `exec_mode`, `p_exec_mode`, `implementation_key`. La
  > misura giusta non cerca la **parola**, cerca la **lettura**
  > (`params ->> 'chiave'`).
  >
  > ⭐ **Il difetto speculare, che è quello che sorprende**: la chiave che il
  > motore legge davvero — `reconcile_on_change` — **non era dichiarata**. Il
  > pannello mostrava cinque manopole scollegate e nascondeva l'unica collegata.
  > ✅ **Sanato lo stesso giorno**, e nei due versi: le cinque finte sono uscite
  > e quella vera è entrata. ⚠️ *Un catalogo che dichiara più di quanto esegue
  > si scopre girando una manopola a vuoto; uno che dichiara meno non si scopre
  > affatto* — ed era il caso qui.
* **STORICO**: ⛔ **nessun parametro** — `params` è `{}` dal 2026-09-01.
  ~~`apply_triggers`~~ era dichiarata `true` e **mai letta**;
  ~~`drop_legacy_ud`~~ era letta e **mai dichiarata**, ed è uscita con il suo
  ramo di codice (`20260901-01`).

  > ⛔ **E non era una migrazione finita: era una pulizia puntata sul nome
  > sbagliato.** Il ramo cancellava `trg_{table}_upd_storico` e
  > `trg_{table}_dlt_storico`, mentre i trigger legacy davvero creati dai
  > changelog storici si chiamano `trg_<tab>_upd_dlt_storico_<tab>` e quelli di
  > oggi `trg_z90_{table}_storico_upd_dlt`. **Tre forme diverse**: il
  > `DROP TRIGGER IF EXISTS` non ha mai potuto agganciare le altre due.
  > ⚠️ Il flag era `COALESCE(..., false)`, quindi il ramo non è mai stato
  > eseguito nemmeno per sbaglio — si è tolta una **leva che prometteva una
  > pulizia impossibile**, non un comportamento.

* **CLEANUP_AT**:
  * ⚠️ `base_ts_column` *(opzionale)* → la colonna su cui si calcola la scadenza.
    **Va lasciata assente sulla riga `*all`/`*all`**: è una proprietà *per
    tabella*, mentre `params` è *per riga di regola* — un solo valore imposto a
    tutte le tabelle sarebbe sbagliato per costruzione. Se manca, il motore la
    deduce a catena (`data_insert` → `executed_at` → `occurred_at` →
    `created_at`), e se non trova niente **salta la tabella** con un audit
    `WARN` e `skip_reason = MISSING_BASE_TS_COLUMN`.
  * ⭐ **Va invece dichiarata su `vendite.event_log`** (dal 2026-09-01,
    `event_time`): quella tabella ha **sia** `data_insert` **sia** `event_time`,
    il fallback prenderebbe la prima, ma il trigger che scrive `cleanup_at`
    calcola da `event_time`. Erano due modi di derivare la stessa grandezza che
    non concordavano — coincidono sulle righe nate normalmente, non su un evento
    importato o ricostruito.


  * `ttl_days` *(int, obbligatorio)* → giorni di retention.
  * `cleanup_column` *(text, default cleanup_at)* → colonna target.
  * `base_ts_column` *(text, opzionale)* → colonna timestamp base (fallback: data_insert/executed_at/occurred_at/created_at).
  * `apply_on_update` *(boolean, default false)* → ricalcola anche su righe già valorizzate.
* **CLEANUP_PURGE**:

  * `cleanup_column` *(text, default cleanup_at)* → colonna target.
  * `batch_limit` *(int, default 5000)* → dimensione batch.

---

### Interazione con le altre tabelle

* **`automation_overrides_cols`** → risolve nomi di colonne non standard: `ATTIVO_COL`, `AUDIT_TS`, `AUDIT_USER`, `STORICO_FK`.
* ~~**`automation_fk_exclusions`**~~ ⛔ **NON ESISTE PIÙ.** *(Storicamente)* escludeva specifiche coppie *parent/child* dalla regola `ATTIVO`. Il filtro era stato disattivato in `20260113-01` (commento "non più utilizzato") e non re-introdotto nel rewrite `20260408-06`; la **tabella** è stata poi **droppata** il 2026-01-01 da `20260101-01-drop-attivo-legacy-objects`.
  ⚠️ **Rettifica del 2026-08-31**: questa riga diceva *«la tabella esiste ma è inerte»* — falso, e la differenza conta. «Inerte» invita a riempirla; «non esiste» dice che il meccanismo va **ricostruito**. Qualcuno ci si è appoggiato per proporre una soluzione, deducendo l'esistenza della tabella dalla presenza del suo vecchio CSV di seed (poi cancellato).
  ⇒ Oggi **non c'è nessun meccanismo di esclusione FK**: per ritirare configurazione senza toccare il guard si usa `obsoleto_dal`, o si restringe l'`automation_scope`.
* **`automation_cleanup_exclusions`** → esclude tabelle dal cleanup (rule_type CLEANUP_*).

---

### Comportamento degli orchestratori (riassunto)

* Scopo schemi: da `p_schemas` o tabella `dbops.automation_scope` (se presente), altrimenti tutti gli schemi *user* escluso `storico`.
* Per **TX_ID / AUDIT_UPDATE / STORICO**: loop per tabelle che matchano la regola (schema + table/pattern), valutano pre‑requisiti (colonne, storico presente), costruiscono nome via template, verificano esistenza secondo `existence_strategy`, **creano il trigger** se mancante (o **DRYRUN** se `p_dry_run=true`).
* Per **ATTIVO**: loop su **tutte** le FK nell'ambito (indipendentemente da `confdeltype`), risolve colonne `attivo` su parent/child via overrides, poi applica (NB: il filtro `automation_fk_exclusions` **non è più applicato**, vedi sopra):

  * **BLOCK** sul padre: impedisce `attivo=true -> false` se esistono figli **attivi** (o figli in generale se la colonna `attivo` sul figlio non esiste).
  * **REQUIRE** sul figlio: impedisce insert/update verso un padre non attivo. Se il figlio ha `attivo`, il controllo vale solo quando `attivo=true`.

**Nota**: **l’automazione ATTIVO viene applicata solo alle FK con colonna che termina in `_id`**; in caso contrario la regola viene saltata (per evitare riferimenti a codici testuali o chiavi non id).

Tutti i passaggi loggati in `dbops.audit_log` (`DRYRUN`/`OK`/`ERROR`).

---

### Esempi d'uso (seed minimal)

* Regola **TX_ID** per tutte le tabelle di `anagrafiche`:

```sql
INSERT INTO dbops.automation_rules_tbl(enabled, rule_type, target_schema, exec_mode, name_template, existence_strategy, params, priority, note)
VALUES (true, 'TX_ID', 'anagrafiche', 'AUTO', 'trg_{table}_ins_upd_gen_tx_id', 'BY_NAME', '{}'::jsonb, 100, 'txid di default');
```

* Regola **ATTIVO** per `vendite.%` (policy block):

```sql
INSERT INTO dbops.automation_rules_tbl(enabled, rule_type, target_schema, target_table, exec_mode, name_template, existence_strategy, params, priority)
VALUES (
  true, 'ATTIVO', 'vendite', '%%', 'AUTO',
  '{"block":"trg_{parent}_a10_{child}_block_deact_upd",
    "require":"trg_{child}_a10_{parent}_require_attivo_ins_upd"}',
  'BY_NAME', '{}'::jsonb, 100
);
```

---

### Troubleshooting

* Nessun trigger creato? Controlla: `enabled=true`, *ambito* schemi corretto, `exec_mode` compatibile, `existence_strategy`, e pre‑requisiti (colonne/ storico/ FK).
* Conflitti di naming? Verifica la lunghezza (63 char) e l’univocità del template in combinazione con schema/tabella/FK.
* Debug rapido: guarda `dbops.audit_log` (filtra per `function_name='run_automations'` e `status IN ('DRYRUN','ERROR')`).

---


### Vincoli & comportamento

* Ordinamento applicazione: `ORDER BY priority, id`.
* *exec_mode* filtro: la regola è valida se `exec_mode = p_exec_mode` **o** `exec_mode='AUTO'`.
* *target_table* può essere `NULL` → tutte le tabelle dello schema per quel *rule_type*.
* Per `ATTIVO`, `name_template` è JSON con i modelli `block` e `require`.

### Best practice

* Mantieni template corti (<63 char finali) e coerenti con lo standard di progetto.
* Usa `params` per comportamenti opzionali specifici dei rule_type.
* Se servono eccezioni di naming, preferisci `automation_overrides_cols`.
* Tieni le regole **specifiche** (per schema e, se possibile, tabella) per evitare sorprese.

---

{% include-markdown "signature-core.md" %}
