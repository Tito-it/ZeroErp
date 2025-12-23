## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_pdp_protect_cols`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)   
>

---

### 🎯 Scopo Principale
(latest update 16-12-25)
La trigger function **`anagrafiche.trgfn_pdp_protect_cols()`** protegge alcune colonne della tabella PDP da modifiche successive, applicando una regola di **immutabilità post-valorizzazione**.

Colonne protette:

* `pdp`
* `indirizzo_dettaglio_id`

Regola:

* se il valore **era già valorizzato** (OLD non NULL) allora **non può essere modificato** tramite UPDATE.

In caso di violazione, viene generato un **errore applicativo** tramite `script.fn_log_and_raise_error`.

---

### 🛠️ Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_pdp_protect_cols()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### 📥 Input (Record Trigger)

Usa:

* `TG_OP` (tipo operazione)
* `TG_NAME` (nome trigger, per logging)
* `OLD.id`
* `OLD.pdp`, `NEW.pdp`
* `OLD.indirizzo_dettaglio_id`, `NEW.indirizzo_dettaglio_id`

---

### 📤 Output

* Ritorna `NEW`.
* In caso di violazione: genera errore applicativo (bloccante).

---

### 🔄 Logica Operativa

La funzione agisce **solo** su UPDATE:

```plpgsql
IF TG_OP = 'UPDATE' THEN
  ...
END IF;
```

 **1) Protezione colonna `pdp`**

Condizione di blocco:

* `OLD.pdp IS NOT NULL`
* `NEW.pdp IS DISTINCT FROM OLD.pdp`

Se vera, genera errore applicativo:

* codice: `E_COLONNA_NON_MODIFICABILE`
* contesto trigger: `TG_NAME`
* payload:

  * `column = 'pdp'`
  * `id = OLD.id`
* parametro extra: `'pdp'`

> Nota: l’uso di `IS DISTINCT FROM` gestisce correttamente anche i casi con NULL, ma qui la guardia `OLD... IS NOT NULL` rende la semantica esplicita: *solo dopo valorizzazione*.

 **2) Protezione colonna `indirizzo_dettaglio_id`**

Condizione di blocco:

* `OLD.indirizzo_dettaglio_id IS NOT NULL`
* `NEW.indirizzo_dettaglio_id IS DISTINCT FROM OLD.indirizzo_dettaglio_id`

Se vera, genera errore applicativo:

* codice: `E_COLONNA_NON_MODIFICABILE`
* contesto trigger: `TG_NAME`
* payload:

  * `column = 'indirizzo_dettaglio_id'`
  * `id = OLD.id`
* parametro extra: `'indirizzo_dettaglio_id'`

---

### ⚠️ Error Handling

Tutte le violazioni vengono gestite con:

* `script.fn_log_and_raise_error('database', TG_NAME, 'E_COLONNA_NON_MODIFICABILE', ...)`

Caratteristiche:

* errori **applicativi** (coerenti col framework Zero ERP)
* log strutturato via JSONB
* messaggio non hardcoded in trigger (centralizzato)

---

### 🧩 Side Effects

* Nessun DML diretto.
* Effetto principale: blocco dell’UPDATE quando tenta di modificare colonne rese immutabili.

---

### 🔍 Esempi di Comportamento

 **Caso A – PDP già valorizzato, tentativo di modifica**

* `OLD.pdp = 'PDP-001'`
* `NEW.pdp = 'PDP-002'`

👉 Errore `E_COLONNA_NON_MODIFICABILE` (colonna `pdp`).

 **Caso B – PDP non ancora valorizzato, prima assegnazione consentita**

* `OLD.pdp = NULL`
* `NEW.pdp = 'PDP-001'`

👉 Consentito (nessun errore).

 **Caso C – Indirizzo già valorizzato, tentativo di cambio indirizzo**

* `OLD.indirizzo_dettaglio_id = 100`
* `NEW.indirizzo_dettaglio_id = 200`

👉 Errore `E_COLONNA_NON_MODIFICABILE` (colonna `indirizzo_dettaglio_id`).

---

### 🧪 Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. Update con `OLD.pdp NOT NULL` e cambio pdp → errore `E_COLONNA_NON_MODIFICABILE`.
2. Update con `OLD.pdp NULL` e assegnazione pdp → OK.
3. Update con `OLD.indirizzo_dettaglio_id NOT NULL` e cambio → errore.
4. Update con `OLD.indirizzo_dettaglio_id NULL` e assegnazione → OK.
5. Update che non cambia valori → OK.

---

### 📌 Best Practice

* ✅ Attaccare questa funzione a un trigger **BEFORE UPDATE** sulla tabella `anagrafiche.pdp`.
* ✅ Limitare l’attivazione alle colonne rilevanti (`BEFORE UPDATE OF pdp, indirizzo_dettaglio_id`) per ridurre overhead.
* ✅ Se in futuro si prevedono eccezioni (es. migrazioni/correzioni amministrative), gestirle con:

  * bypass controllato (GUC / ruolo tecnico)
  * funzione dedicata di “maintenance”

---

### 🗂️ Metadati

* **Schema:** `anagrafiche`
* **Tipo:** trigger function (protect/immutability)
* **Operazioni gestite:** `UPDATE`
* **Colonne protette:** `pdp`, `indirizzo_dettaglio_id`
* **Meccanismo errore:** `script.fn_log_and_raise_error`
