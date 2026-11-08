## 📘 Documentazione Concettuale – Tabella `storico.indirizzi_dettaglio`
 
> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**  
>
Approfondimento tabelle:   
>
[anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)    
>
Approfondimento funzioni:   
>
[script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic)    
### 🎯 Scopo Principale
* **Audit Trail**: tracciare ogni modifica ai dettagli degli indirizzi consentendo la ricostruzione dello stato storico.
* **Versioning temporale**: supportare query basate su periodi di validità tramite `valid_from` e `valid_to`.
* **Schema futuro‑proof**: salvare l’intero stato del record in JSONB senza richiedere aggiornamenti di schema a ogni nuova colonna.

---

### Struttura Standard delle Tabelle di Storico

Tutte le tabelle di storico in Zero ERP, incluso `storico.indirizzi_dettaglio`, adottano uno **schema di colonne standard**:

* `id`
* `valid_from` / `valid_to`
* `change_type`
* `data_insert`
* `user_insert`
* `<entità>_id` (foreign key verso la tabella originale)
* `snapshot` (JSONB dello stato del record)
* `tipo_operazione`
* `tx_id`

---

### Meccanismo di Popolamento

La popolazione degli snapshot avviene tramite la trigger function generica `script.trgfn_storico_generic()` applicata sulla tabella sorgente, che:

1. Chiude eventuali snapshot precedenti (`valid_to = CURRENT_DATE`).
2. Inserisce uno snapshot iniziale (se non esiste) con `valid_from` impostato a una data fissa (1950-01-01).
3. Crea sempre uno snapshot finale con `valid_from = CURRENT_DATE` e `valid_to = NULL`, serializzando lo stato tramite `to_jsonb(NEW/OLD)`.
4. Popola `tx_id` tramite `dbops.trgfn_tx_id_managed()` per contestualizzare le transazioni.

---

### Vantaggi Operativi

* **Storicizzazione automatica**: nessuna logica custom su ogni tabella; il pattern JSONB consente evoluzioni senza migrazione di schema.
* **Coerenza transazionale**: associando `tx_id`, si raggruppano snapshot multipli nella stessa operazione di business.
* **Query efficienti**: reporting storico semplificato tramite campi temporali e codici operazione.

---

> **“`storico.indirizzi_dettaglio` segue lo standard storico di Zero ERP: semplici regole per uno storico completo e affidabile, con flessibilità JSONB e robustezza transazionale.”**
