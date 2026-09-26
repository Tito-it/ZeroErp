## 📘 Documentazione Concettuale – Funzione `dbops.fn_lock_columns_divergenze`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)   
>
Approfondimento tabelle:  
> [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)   
> [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl)   
>
Approfondimento funzioni:    
> [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns)    
> [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti)    

---
### 🎯 Scopo Principale
(latest review 26-09-26)

Risponde a una domanda: **i lock di colonna vivi sono quelli che il registro
dichiara?** Per ogni tabella in cui la risposta è no, restituisce una riga con
l'azione che li riallinea. Non modifica niente.

È il **criterio unico** della convergenza. Lo usano:

* `dbops.fn_run_automations_lock_columns`, che esegue l'azione di ogni riga;
* il pgTAP `dbops/test-lock-columns-convergenza`, che ne pretende zero su tutto
  il database;
* `90_end/20260926-07`, che dopo la convergenza ne pretende zero.

Nessuno dei tre ricalcola il confronto per conto suo.

---

### Parametri di input

| Parametro     | Tipo   | Descrizione                                  |
| ------------- | ------ | -------------------------------------------- |
| `p_exec_mode` | text   | Modalita' di esecuzione (AUTO/CI/SCHEDULED). |
| `p_schemas`   | text[] | Schemi target (NULL = ambito risolto).       |

---

### Le colonne del risultato

| Colonna | Che cosa dice |
| --- | --- |
| `schema_name`, `table_name` | la tabella |
| `azione` | `CREA`, `RIGENERA` o `TOGLIE` (vedi il runner) |
| `trigger_atteso` | il nome da template della regola `LOCK_COLUMNS` |
| `colonne_attese` | `codice_interno` (se c'è) e poi le colonne del registro, in ordine |
| `argomenti_attesi` | le coppie *colonna, codice* nell'ordine del `CREATE TRIGGER` |
| `trigger_vivi` | tutti i trigger su `script.trgfn_lock_columns` della tabella |
| `colonne_perse` | ⭐ colonne bloccate dal vivo che il registro **non nomina affatto** |

Le tabelle allineate non escono. Una tabella che nessuna regola `LOCK_COLUMNS`
attiva copre non esce mai.

---

### Perché `colonne_perse` distingue fra «ignota» e «disattivata»

* una colonna che il registro **non nomina** è un lock nato fuori dal registro:
  toglierla lo cancellerebbe in silenzio, quindi il runner si ferma;
* una colonna con una riga `enabled = false` è una **decisione** di togliere il
  blocco: non esce qui, e il runner la toglie.

---

### Esempi di utilizzo

```sql
-- Che cosa farebbe la convergenza su tutto il database
SELECT * FROM dbops.fn_lock_columns_divergenze('SCHEDULED', NULL);

-- Solo le colonne che la fermerebbero
SELECT schema_name, table_name, colonne_perse
  FROM dbops.fn_lock_columns_divergenze('SCHEDULED', NULL)
 WHERE cardinality(colonne_perse) > 0;
```

Brief: `brief-db-lock-di-colonna-fuori-registro`.
