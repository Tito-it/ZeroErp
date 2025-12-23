## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_iu_clone_catasto_from_parent`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)   
>
> **Approfondimento funzioni:**
>
> * [script.fn_clone_catasto_from_parent_by_istanza](/dbzero/script/funzioni/fn_clone_catasto_from_parent_by_istanza)   
>
> **Lookup sorgente:**
>
> * [script.fn_get_catasto_source_by_istanza](/dbzero/script/funzioni/fn_get_catasto_source_by_istanza)   
>
> **Trigger che la invoca (subentro):**
>
> * `anagrafiche.trg_iu_z50_clone_catasto_from_parent_aft_upd`   

---

### 🎯 Scopo Principale
(latest review 15-12-25)
La trigger function **`anagrafiche.trgfn_iu_clone_catasto_from_parent()`** è un wrapper minimale che, in risposta a un evento di modifica dell’istanza (tipicamente valorizzazione di `parent_istanza_id`), attiva la clonazione del catasto dalla parent verso l’istanza corrente.

✅ La logica applicativa (idempotenza, locking, error handling, INSERT/UPDATE) è interamente demandata alla funzione:

* `script.fn_clone_catasto_from_parent_by_istanza(NEW.id)`

Questa trigger function ha quindi il solo compito di:

* invocare la funzione core
* restituire `NEW`

---

### 🛠️ Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_iu_clone_catasto_from_parent()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### 📥 Input (Record Trigger)

Utilizza esclusivamente:

* `NEW.id` (istanza corrente)

Il resto delle condizioni (es. presenza parent, catasto già presente, ecc.) viene gestito dalla funzione core.

---

### 📤 Output

* Ritorna sempre `NEW`.

> Nota: essendo concepita per trigger `AFTER`, il valore ritornato non modifica la riga persistita, ma mantiene la forma standard delle trigger function.

---

### 🔄 Logica Operativa

Pseudo-flusso:

1. Invoca la funzione core:

   * `PERFORM script.fn_clone_catasto_from_parent_by_istanza(NEW.id);`
2. Ritorna `NEW`.

Non esegue controlli aggiuntivi: evita duplicazioni di logica e garantisce coerenza centrale nella funzione `script.fn_clone_catasto_from_parent_by_istanza`.

---

### 🧩 Side Effects

Direttamente: **nessuno** (non fa DML).

Indirettamente: tramite la funzione core invocata può avvenire:

* INSERT su `anagrafiche.catasto_unita_immobiliari`
* UPDATE su `anagrafiche.istanze_utilities` (aggancio `catasto_unita_immobiliare_id`)

---

### 🔗 Integrazione nel Trigger di Subentro

Questa funzione è progettata per essere collegata a un trigger `AFTER UPDATE OF parent_istanza_id` su `anagrafiche.istanze_utilities`.

Nel modello corrente (come da DDL fornito) il trigger tipico è:

* `trg_iu_z50_clone_catasto_from_parent_aft_upd`

con condizione (WHEN) che limita l’attivazione solo se:

* `new.parent_istanza_id IS NOT NULL`
* `new.catasto_unita_immobiliare_id IS NULL`
* `new.indirizzo_dettaglio_id IS NOT NULL`

In tal modo:

* la trigger function rimane pulita
* le condizioni di invocazione restano nel trigger (DDL)
* la logica transazionale sta nella funzione core

---

### ⚠️ Error Handling

La trigger function non gestisce errori: eventuali eccezioni propagate provengono dalla funzione core, in particolare:

* `ERRORE_PARAMETRI` se `NEW.id` fosse anomalo (caso teorico)
* `CATASTO_SOURCE_NOT_FOUND` se manca la sorgente catastale sulla parent

Questo garantisce logging e tracciabilità coerenti nel layer `script/dbops`.

---

### 🧪 Note per Test

Test consigliati (a livello trigger):

1. Aggiornamento `parent_istanza_id` che soddisfa la WHEN → deve valorizzare `catasto_unita_immobiliare_id` (via funzione core).
2. Aggiornamento `parent_istanza_id` ma `catasto_unita_immobiliare_id` già valorizzato → nessun duplicato (idempotenza nella core).
3. Aggiornamento `parent_istanza_id` con parent senza catasto → attesa eccezione `CATASTO_SOURCE_NOT_FOUND`.

---

### 📌 Best Practice

* ✅ Mantenere questa trigger function **minimal** (solo orchestrazione).
* ✅ Centralizzare qualunque variazione di regole nella funzione core (`fn_clone_*`).
* ✅ Gestire le condizioni di attivazione nel trigger (DDL) usando `WHEN` e `AFTER UPDATE OF ...`.

---

### 🗂️ Metadati

* **Schema:** `anagrafiche`
* **Tipo:** trigger function wrapper
* **Tabella target:** `anagrafiche.istanze_utilities`
* **Responsabilità:** orchestrazione clonazione catasto da parent per subentro
