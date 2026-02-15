## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_clienti_sync_utility_from_ba`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle :**
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)    
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)   
> * [config.utilities](/dbzero/config/tabelle/utilities)   
>
> **Logging/Error handling:**
>
> * `script.fn_log_and_raise_error` (standard Zero ERP per errore applicativo DB)    

---

### 🎯 Scopo Principale
(latest review 15-02-26)
La trigger function **`anagrafiche.trgfn_clienti_sync_utility_from_ba()`** garantisce la **coerenza** tra:

* `anagrafiche.clienti.utility_id`
* `anagrafiche.billing_account.utility_id`

quando sul cliente è presente un riferimento a `billing_account_id`.

Regola principale:

1. Se `clienti.utility_id` è **NULL**, viene **ereditato** da `billing_account.utility_id`.
2. Se `clienti.utility_id` è valorizzato ma **diverso** da quello del billing account, viene generato un **errore applicativo**.
3. Se `config.utilities.richiede_pdp = true` per l’utility risolta dal billing account, `clienti.pdp_id` deve essere valorizzato.
4. Se `clienti.pdp_id` è valorizzato, la utility del PDP deve coincidere con la utility del billing account.

---

### 🧭 Contesto e Motivazione

Nel modello Zero ERP, il `billing_account` identifica un codice cliente (definitivo) per una specifica utility.

Di conseguenza:

* se un cliente punta a un `billing_account`, l’utility del cliente deve essere coerente con quella del `billing_account`.

Questa trigger function rende la regola:

* **automatica** (auto-compilazione quando mancante)
* **bloccante** (errore se incoerente)

---

### 🛠️ Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### 📥 Input (Record Trigger)

Usa i seguenti campi di `NEW` (tabella `anagrafiche.clienti`):

* `NEW.billing_account_id`
* `NEW.utility_id`
* `NEW.tx_id`

---

### 📤 Output

* Ritorna `NEW`.
* Può modificare `NEW.utility_id` **solo** quando è `NULL` (ereditarietà dal BA).

> Tipicamente va usata su trigger `BEFORE INSERT OR UPDATE` (o `BEFORE INSERT OR UPDATE OF billing_account_id, utility_id`) perché modifica `NEW`.

---

### 🔄 Logica Operativa

 **1) Guardia: assenza di billing account**

Se `NEW.billing_account_id IS NULL`:

* la funzione **non** applica regole
* ritorna `NEW`

 **2) Lettura `utility_id` dal billing account**

Esegue:

* `SELECT ba.utility_id FROM anagrafiche.billing_account ba WHERE ba.id = NEW.billing_account_id`

Salva in `v_utility_id`.

 **3) Gestione BA senza utility**

Se `v_utility_id IS NULL`:

* genera errore applicativo con codice:

  * `E_BILLING_ACCOUNT_UTILITY_NULL`

Payload log (minimo):

* `billing_account_id`

Tx context:

* `NEW.tx_id`

> Nota: la funzione utilizza `script.fn_log_and_raise_error(...)` e non un `RAISE EXCEPTION` diretto (commentato), coerente con lo standard Zero ERP.

 **4) Sync/Coerenza su `clienti.utility_id`**

* Se `NEW.utility_id IS NULL` → assegna:

  * `NEW.utility_id := v_utility_id`

* Se `NEW.utility_id <> v_utility_id` → genera errore applicativo con codice:

  * `E_CLIENTE_UTILITY_MISMATCH_BA`

 **5) Policy PDP da configurazione utility**

* Legge `config.utilities.richiede_pdp` per `v_utility_id`.
* Se la utility non è trovata in configurazione -> errore applicativo (`E_GENERICO` con dettaglio).
* Se `richiede_pdp = true` e `NEW.pdp_id IS NULL` -> errore applicativo (`E_GENERICO` con dettaglio).

 **6) Coerenza utility tra PDP e billing account**

* Se `NEW.pdp_id IS NOT NULL`, legge `anagrafiche.pdp.utilities_id`.
* Se diversa da `v_utility_id` -> errore applicativo (`E_GENERICO` con dettaglio mismatch).

Payload log include:

* `billing_account_id`
* `utility_da_cliente`
* `utility_da_billing`

Tx context:

* `NEW.tx_id`

---

### ⚠️ Error Handling

Errori gestiti (hard):

| Codice                           | Scenario                              | Effetto                        |
| -------------------------------- | ------------------------------------- | ------------------------------ |
| `E_BILLING_ACCOUNT_UTILITY_NULL` | BA senza `utility_id`                 | errore applicativo (bloccante) |
| `E_CLIENTE_UTILITY_MISMATCH_BA`  | utility cliente diversa da utility BA | errore applicativo (bloccante) |
| `E_GENERICO`                     | utility non configurata / PDP richiesto mancante / mismatch utility BA↔PDP | errore applicativo (bloccante) |

> I `RAISE EXCEPTION` sono presenti ma commentati: l’implementazione adotta la strategia centralizzata `fn_log_and_raise_error`.

---

### 🧩 Side Effects

* Non fa DML diretto.
* Modifica `NEW.utility_id` quando assente.

---

### ⚙️ Considerazioni di Performance

* 1 lookup puntuale su `billing_account(id)`.
* Con PK standard, costo O(1) e trascurabile.

---

### 🔍 Esempi d’Uso (comportamento atteso)

 **Caso A: cliente senza utility → eredita dal BA**

* Input:

  * `NEW.billing_account_id = 10`
  * `NEW.utility_id = NULL`
  * `billing_account.utility_id = 3`

* Output:

  * `NEW.utility_id = 3`

**Caso B: cliente già coerente**

* `NEW.utility_id = 3` e `billing_account.utility_id = 3`

* Output:

  * nessuna modifica

 **Caso C: mismatch**

* `NEW.utility_id = 2` e `billing_account.utility_id = 3`

* Output:

  * errore `E_CLIENTE_UTILITY_MISMATCH_BA`

---

### 🧪 Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. `billing_account_id NULL` → `NEW` invariato.
2. `billing_account_id` valido con `ba.utility_id` non null + `NEW.utility_id NULL` → utility valorizzata automaticamente.
3. `billing_account_id` valido con `ba.utility_id NULL` → errore `E_BILLING_ACCOUNT_UTILITY_NULL`.
4. `billing_account_id` valido con mismatch → errore `E_CLIENTE_UTILITY_MISMATCH_BA`.
5. Utility con `richiede_pdp=true` e `pdp_id` assente -> errore applicativo.
6. `pdp_id` presente con `pdp.utilities_id` diverso da utility BA -> errore applicativo.

---

### 📌 Best Practice

* ✅ Collegare questa trigger function a un trigger **BEFORE** su `anagrafiche.clienti`.
* ✅ Limitare l’attivazione ai campi rilevanti (`billing_account_id`, `utility_id`) per evitare overhead.
* ✅ Mantenere il BA come “source of truth” per l’utility quando il legame è presente.

---

### 🗂️ Metadati

* **Schema:** `anagrafiche`
* **Tipo:** trigger function di coerenza / auto-sync
* **Tabella target:** `anagrafiche.clienti`
* **Owner:** `titodb`
* **Commento DB:**

  * “Garantisce coerenza tra clienti.utility_id e billing_account.utility_id; se utility_id è NULL eredita dal BA, se diversa solleva errore applicativo.”
