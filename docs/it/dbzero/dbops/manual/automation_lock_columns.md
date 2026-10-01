## 📘 Documentazione Concettuale – Tabella `dbops.automation_lock_columns`

> 👀 **Vedi anche**
>
Approfondimento tabelle:  
> 
[dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)    
> [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)   
>
Approfondimento funzioni:
> 
[dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns)   
>
Approfondimento trigger:
> 
[script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)   
### 🎯 Scopo Principale
(latest review 10-01-26)
Centralizzare la configurazione delle **colonne extra** da bloccare con `script.trgfn_lock_columns`.

La colonna **`codice_interno` non si configura qui**: se presente nella tabella target,
il runner la include automaticamente nel trigger.

---

### Campi chiave e semantica

* **`target_schema`** *(text)* – schema di destinazione.
* **`target_table`** *(text)* – tabella di destinazione.
* **`column_name`** *(text)* – colonna da bloccare.
* **`error_code`** *(text)* – codice errore (default `E_CODICE_NON_MODIFICABILE`).
  ⛔ Dev'essere un codice **vivo** a catalogo: non assente da `config.codici_errore`,
  e senza `obsoleto_dal` scaduta. Una riga qui è un **call site differito** — il
  codice non solleva niente finché l'automazione non genera il trigger, e da quel
  momento lo solleva per sempre. Lo presidia il controllo (H) di
  `scripts/sql/guardrail_codice_errore_strutturato.sql`, che gira in CI.
* **`exec_mode`** *(text)* – `AUTO` | `CI` | `SCHEDULED`: in quale giro il lock **nasce**. Il
  runner fa nascere la riga se `exec_mode='AUTO'` oppure `exec_mode = p_exec_mode`; una
  colonna già bloccata da un altro giro resta, non si toglie.
* **`enabled`** *(boolean)* – `true`: la colonna si blocca. `false`: è una **decisione** di
  togliere il blocco, e la convergenza lo toglie. ⚠️ Non è la stessa cosa di una riga che
  **manca**: una colonna bloccata dal vivo che il registro non nomina affatto ferma il runner.
* **`note`** *(text)* – note descrittive.
* **Audit** – `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Comportamento del runner

`dbops.fn_run_automations_lock_columns` **converge** (dal 2026-09-26):

1. per ogni tabella nell'ambito calcola il lock **atteso**: `codice_interno` se presente,
   poi le colonne di questo registro che esistono fisicamente;
2. lo confronta con i lock **vivi**, cioè tutti i trigger su `script.trgfn_lock_columns`
   della tabella, qualunque nome abbiano (`dbops.fn_lock_columns_divergenze`);
3. crea, rigenera o toglie finché resta **un unico trigger** per tabella, col nome da
   template, `UPDATE OF` sulle colonne attese e gli argomenti attesi;
4. ⛔ se un lock vivo blocca una colonna che questo registro non nomina, **si ferma** prima
   di qualunque DDL e nomina tutte le colonne in quella situazione.

---

### Esempi

**Bloccare una colonna extra con codice errore custom:**

```sql
INSERT INTO dbops.automation_lock_columns
  (target_schema, target_table, column_name, error_code, exec_mode, enabled, note)
VALUES
  ('config','utilities','categoria','E_CODICE_NON_MODIFICABILE','AUTO',true,'blocco categoria');
```

**Solo `codice_interno` (nessuna riga necessaria):**

> Se la tabella ha `codice_interno`, il trigger viene applicato automaticamente.

---

### Cambiare una riga cambia il trigger al giro successivo

Modificare `error_code`, aggiungere una colonna o disattivare una riga arriva nel
trigger vivo alla prossima convergenza: a ogni migrazione (`ci_apply` in CI), ogni
sera alle 21:10 (job `automations_lock_columns`), oppure subito con
`SELECT dbops.fn_run_automations_lock_columns('AUTO', NULL, false);`.
Non serve più un changeSet che droppa e rigenera a mano.

⚠️ **Fino al 2026-09-26 non era così**: il runner creava il trigger solo se mancava, e
non confrontava mai gli argomenti di uno esistente. Il 2026-09-23 erano **69 trigger
su 68 tabelle** a sollevare `CODICE_NON_MODIFICABILE`, ritirato quarantanove giorni
prima, e ci sono voluti sei changeSet `90_end/*provision-lock*` scritti a mano per
riallineare perimetri fissi. Brief: `brief-db-codici-ritirati-negli-argomenti-dei-trigger`,
`brief-db-lock-di-colonna-fuori-registro`.

⛔ E non si riscrive il `CREATE TRIGGER` a mano: sarebbe un secondo posto che calcola
l'elenco delle colonne, accanto al runner — cioè il difetto che questo registro esiste
per chiudere. La prima convergenza lo riassorbirebbe comunque.

---

### Best practice

* Inserisci qui solo le colonne **extra** non standard.
* Mantieni `exec_mode='AUTO'` salvo esigenze di rilascio controllato.
* Verifica che la colonna esista davvero, altrimenti il runner la ignora.
* ⛔ **Un lock di colonna si dichiara qui, non si scrive a mano** in un changeSet.
* Un lock che esiste come trigger **scritto a mano** va portato qui: `catalogo.articoli.codice`
  e `config.sorgenti.categoria` ci sono entrati il 2026-09-23 dopo essere stati in vigore
  per anni fuori dal registro — un oggetto che *sembra* governato dall'automazione e non
  lo è. Finché la riga manca, la prima rigenerazione fa **sparire** quel lock.
  Lo stesso giorno sono entrati anche i lock di `config.iva.assoggettamento_id` e
  di `config.iva_stati` (`aliquota_override`, `assoggettamento_id_override`), scritti
  a mano nel 2025 e rimasti fuori dal registro; il 2026-09-26 quello di
  `vendite.fatture.natura_doc_id`.
* ⛔ **I lock scritti a mano si cercano nei changelog, non sul database di sviluppo.**
  Su quello di sviluppo i lock di `config.iva_stati` e di `vendite.fatture` non c'erano
  più: li cancellava ogni sera `fn_run_automations_drop_lock_trg` (ritirata il 2026-09-26),
  che in CI non gira perché `85_pgagent` è `MARK_RAN`. Il censimento fatto su dev non li
  ha visti, mentre il database ricostruito da zero li ha ancora.

