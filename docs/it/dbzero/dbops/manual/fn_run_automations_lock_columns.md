## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_lock_columns`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)   
>
Approfondimento tabelle:  
> [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
> [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)   
>
Approfondimento funzioni:    
> [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze)    
> [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti)    
> [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations)    
> [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)    

---
### 🎯 Scopo Principale
(latest review 26-09-26)

La funzione **`dbops.fn_run_automations_lock_columns(p_exec_mode, p_schemas, p_dry_run)`**
porta i **lock di colonna** delle tabelle nell'ambito allo stato che il registro
dichiara. Un lock di colonna è un trigger su `script.trgfn_lock_columns` che
impedisce di cambiare il valore di una colonna dopo che la riga è nata.

⭐ **Converge, non si limita a creare.** Fino al 2026-09-26 creava il trigger solo
se sulla tabella non ce n'era già uno: un lock nato una volta non si riallineava
più al registro (codici ritirati rimasti negli argomenti, colonne aggiunte al
registro che non arrivavano mai). E una seconda funzione,
`fn_run_automations_drop_lock_trg`, ogni notte cancellava i lock che il registro
non nominava, **anche quelli scritti a mano**. Ora il lavoro è uno solo, e sta qui.

---

### Parametri di input

| Parametro     | Tipo    | Descrizione                                  |
| ------------- | ------- | -------------------------------------------- |
| `p_exec_mode` | text    | Modalita' di esecuzione (AUTO/CI/SCHEDULED). |
| `p_schemas`   | text[]  | Schemi target (NULL = ambito risolto).       |
| `p_dry_run`   | boolean | Se true non esegue DDL e registra l'audit.   |

---

### Che cosa è atteso e che cosa è vivo

Il confronto non lo fa questa funzione: lo fa
[`dbops.fn_lock_columns_divergenze`](/dbzero/dbops/funzioni/fn_lock_columns_divergenze),
che è anche il criterio del presidio pgTAP `dbops/test-lock-columns-convergenza`.
Un criterio, due utenti.

* **Atteso**: `codice_interno`, se la tabella ce l'ha (implicito, linee guida SQL
  §6b), più le righe attive di `dbops.automation_lock_columns` per quel modo di
  esecuzione, solo se la colonna esiste. Il nome è quello del `name_template`
  della regola `LOCK_COLUMNS` in `dbops.automation_rules_tbl`.
* **Vivo**: **ogni** trigger su `script.trgfn_lock_columns` della tabella,
  qualunque nome abbia. Le colonne che presidia sono gli argomenti in posizione
  dispari (coppie *colonna, codice*) più quelle del suo `UPDATE OF`.

⚠️ `existence_strategy` per `LOCK_COLUMNS` **non si legge più**: un lock vivo si
riconosce sempre dalla funzione, altrimenti uno scritto a mano resterebbe
invisibile.

---

### Le azioni

| Azione | Quando | Che cosa fa |
| --- | --- | --- |
| `CREA` | c'è qualcosa da bloccare e nessun lock vivo | crea il trigger col nome da template |
| `RIGENERA` | i lock vivi non sono **esattamente un** trigger col nome da template, gli argomenti attesi, `UPDATE OF` sulle colonne attese e la forma `BEFORE UPDATE … FOR EACH ROW` | toglie tutti i lock vivi della tabella e crea quello atteso |
| `TOGLIE` | niente da bloccare, qualche lock vivo | toglie tutti i lock vivi della tabella |

Una tabella già allineata non si tocca: un secondo giro non ricrea niente.

---

### ⭐ Quando si ferma

Se una colonna è bloccata da un trigger vivo e il registro **non la nomina
affatto**, la funzione solleva `E_LOCK_COLUMNS` **prima di qualunque DDL**, e
nomina in un solo errore tutte le tabelle e le colonne in quella situazione.
Convergere cancellerebbe quel lock in silenzio, che è il difetto che questa
revisione chiude.

Il rimedio è una riga nel CSV del registro (`80_data/sql/dbops/automation_lock_columns.csv`):

* con `enabled = true` se il lock va tenuto;
* con `enabled = false` se va tolto: una riga disattivata è una **decisione**, e
  quella colonna si toglie senza fermarsi.

In `p_dry_run = true` non si ferma: registra nell'audit l'azione e le colonne
fuori dal registro.

---

### `exec_mode`: quando un lock nasce, non quando esiste

Una riga del registro con un `exec_mode` diverso da quello del giro non fa
nascere il lock in quel giro. Ma se la colonna è **già** bloccata, resta attesa:
altrimenti il giro notturno (`SCHEDULED`) toglierebbe ogni sera ciò che il giro
di migrazione (`CI`) ha messo, e viceversa.

---

### Chi la chiama

* `90_end/ci_apply` in CI, a ogni migrazione (`'CI'`);
* il job pgAgent `automations_lock_columns` alle 21:10, tramite
  [`maintenance.proc_automations_lock_columns_job`](/dbzero/maintenance/funzioni/proc_automations_lock_columns_job) (`'SCHEDULED'`);
* i changeSet `90_end/*provision-lock*` e `90_end/20260926-07`, una volta.

---

### Esempi di utilizzo

* **Simulazione**:
  `SELECT dbops.fn_run_automations_lock_columns('AUTO', ARRAY['config'], true);`

* **Che cosa farebbe, senza audit**:
  `SELECT * FROM dbops.fn_lock_columns_divergenze('SCHEDULED', NULL);`

* **Esecuzione reale**:
  `SELECT dbops.fn_run_automations_lock_columns('AUTO', NULL, false);`

---

### Note

* Un lock di colonna **non si scrive a mano** in un changeSet: si dichiara con
  una riga del registro. Un `CREATE TRIGGER … trgfn_lock_columns(...)` scritto a
  mano viene riassorbito (e rinominato) alla prima convergenza.
* Un errore DDL a metà annulla tutto il giro: la funzione gira in una sola
  istruzione, quindi nessuna tabella resta a metà.
* Brief: `brief-db-lock-di-colonna-fuori-registro`.
