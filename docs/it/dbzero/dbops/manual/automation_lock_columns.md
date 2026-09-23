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
* **`exec_mode`** *(text)* – `AUTO` | `CI` | `SCHEDULED`. Il runner applica la riga se `exec_mode='AUTO'`
  oppure `exec_mode = p_exec_mode`.
* **`enabled`** *(boolean)* – abilita/disabilita la riga.
* **`note`** *(text)* – note descrittive.
* **Audit** – `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Comportamento del runner

`dbops.fn_run_automations_lock_columns`:

1. individua le tabelle nell'ambito;
2. aggiunge `codice_interno` se presente;
3. aggiunge le colonne definite in `automation_lock_columns` (solo se esistono fisicamente);
4. crea **un unico trigger** per tabella con `UPDATE OF` sulle colonne effettive.

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

### ⛔ Cambiare una riga NON cambia il trigger che c'è già

Il runner crea un trigger **solo se manca**: non confronta mai gli argomenti di uno
che esiste. Quindi modificare `error_code` o aggiungere una colonna a una tabella
**già lockata** non produce nessun effetto finché il trigger non viene **droppato e
rigenerato**. È la stessa regola delle colonne extra, e vale identica per il codice.

⚠️ Il costo di non saperlo è misurato: il 2026-08-05 la rinomina dei codici `*` →
`E_*` corresse il runner ma non i trigger già generati, e il 2026-09-23 erano **69
trigger su 68 tabelle in 8 schemi** a sollevare `CODICE_NON_MODIFICABILE`, ritirato da
quarantanove giorni. Il presidio non li vedeva perché guardava i **corpi** delle
funzioni, e qui il codice viaggia come `TG_ARGV`. Bonifica e forma da riusare:
`90_end/20260923-02`, che droppa, richiama il runner e poi **verifica che nessuna
colonna prima lockata sia rimasta scoperta**.

⛔ E non si riscrive il `CREATE TRIGGER` a mano sostituendo l'argomento: sarebbe un
secondo posto che calcola l'elenco delle colonne, accanto al runner — cioè il difetto
che questo registro esiste per chiudere.

---

### Best practice

* Inserisci qui solo le colonne **extra** non standard.
* Mantieni `exec_mode='AUTO'` salvo esigenze di rilascio controllato.
* Verifica che la colonna esista davvero, altrimenti il runner la ignora.
* Un lock che esiste come trigger **scritto a mano** va portato qui: `catalogo.articoli.codice`
  e `config.sorgenti.categoria` ci sono entrati il 2026-09-23 dopo essere stati in vigore
  per anni fuori dal registro — un oggetto che *sembra* governato dall'automazione e non
  lo è. Finché la riga manca, la prima rigenerazione fa **sparire** quel lock.
  Lo stesso giorno sono entrati anche i lock di `config.iva.assoggettamento_id` e
  di `config.iva_stati` (`aliquota_override`, `assoggettamento_id_override`), scritti
  a mano nel 2025 e rimasti fuori dal registro.
* ⛔ **I lock scritti a mano si cercano nei changelog, non sul database di sviluppo.**
  Su quello di sviluppo i due trigger IVA non c'erano più, perché qualcuno li aveva
  tolti fuori da Liquibase. Il censimento fatto lì non li ha visti, mentre il
  database ricostruito da zero li ha ancora: la bonifica è passata in sviluppo ed
  è andata rossa in CI.

