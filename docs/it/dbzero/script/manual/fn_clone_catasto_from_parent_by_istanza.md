## 📘 Documentazione Tecnica – Funzione `script.fn_clone_catasto_from_parent_by_istanza`

> 👀 **Vedi anche**
>
> **Approfondimenti tabelle:**
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)    
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari)    
>
> **Approfondimenti funzioni:**
>
> * [script.fn_get_catasto_source_by_istanza](/dbzero/script/funzioni/fn_get_catasto_source_by_istanza)    
>
>
> **Automazioni collegate:**
>
> * Trigger: `anagrafiche.trg_iu_z50_clone_catasto_from_parent_aft_upd` (subentro: clonazione catasto)     
> * Trigger: `anagrafiche.trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd` (sync tabella ponte catasto↔indirizzi)    

---

### 🎯 Scopo Principale
(latest review 15-12-25)
La funzione **`script.fn_clone_catasto_from_parent_by_istanza(p_istanza_utilities_id)`** gestisce la **clonazione** di un record catastale (`anagrafiche.catasto_unita_immobiliari`) dalla **parent_istanza** verso l’istanza corrente, tipicamente nel flusso di **subentro**.

✅ La sorgente viene determinata **esclusivamente** da:

* `anagrafiche.istanze_utilities.parent_istanza_id`

✅ Il legame ufficiale **istanza → catasto** viene mantenuto solo attraverso:

* `anagrafiche.istanze_utilities.catasto_unita_immobiliare_id`

---

### 🧭 Contesto di Modellazione

Dopo il refactor del modello:

* `anagrafiche.catasto_unita_immobiliari` **non** contiene più riferimenti diretti all’istanza.
* La clonazione produce un **nuovo record** catasto con **ID distinto**, ma **contenuto equivalente** alla sorgente.

La funzione:

* **clona** (INSERT) la riga catastale
* **aggancia** (UPDATE) l’istanza al nuovo catasto

La gestione del legame **catasto ↔ indirizzo** è **fuori** da questa funzione ed è demandata al trigger dedicato.

---

### 🛠️ Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_clone_catasto_from_parent_by_istanza(
  p_istanza_utilities_id bigint
)
RETURNS bigint
LANGUAGE plpgsql;
```

---

### 📥 Parametri

| Parametro                |     Tipo | Obbligatorio | Descrizione                                                                          |
| ------------------------ | -------: | :----------: | ------------------------------------------------------------------------------------ |
| `p_istanza_utilities_id` | `bigint` |      ✅       | Identificativo dell’istanza da aggiornare con un nuovo catasto clonato dalla parent. |

---

### 📤 Valore di Ritorno

* ✅ `bigint` = **id** del record appena creato in `anagrafiche.catasto_unita_immobiliari`.
* ✅ `bigint` = **id già presente** se l’istanza ha già `catasto_unita_immobiliare_id` valorizzato (idempotenza).
* ⚠️ `NULL` se l’istanza non ha `parent_istanza_id` (nessuna sorgente disponibile).

---

### 🔐 Comportamento su Parametri Non Validi

Se `p_istanza_utilities_id` è `NULL`, la funzione genera un errore applicativo tramite logging centralizzato:

* invoca `script.fn_log_and_raise_error(...)`
* codice: `ERRORE_PARAMETRI`
* contesto: `script.fn_clone_catasto_from_parent_by_istanza`

---

### 🧱 Dipendenze e Assunzioni

Per la clonazione completa servono:

1. `anagrafiche.istanze_utilities.id = p_istanza_utilities_id`
2. `anagrafiche.istanze_utilities.parent_istanza_id IS NOT NULL`
3. La **parent** deve avere `catasto_unita_immobiliare_id IS NOT NULL`.

Se (3) non è vero, la funzione considera la sorgente assente e attiva un errore specifico (vedi gestione errori).

---

### 🔄 Logica Operativa

 **1) Validazione parametro**

* Se parametro `NULL` → log + raise.

**2) Lock riga istanza (anti-race)**

La funzione blocca la riga di `istanze_utilities` con:

* `SELECT ... FOR UPDATE`

Questo evita condizioni di race durante:

* creazione catasto (INSERT)
* aggiornamento aggancio (UPDATE)

**3) Idempotenza (caso 1)**

Se l’istanza ha già `catasto_unita_immobiliare_id` valorizzato:

* `RETURN v_curr_catasto_id`

✅ Garantisce che chiamate ripetute non creino duplicati.

**4) Assenza parent**

Se `parent_istanza_id IS NULL`:

* `RETURN NULL`

**5) Lookup sorgente (funzione dedicata)**

La sorgente viene cercata tramite:

* `script.fn_get_catasto_source_by_istanza(p_istanza_utilities_id)`

Se la sorgente risulta assente (`v_src.id IS NULL`), la funzione invoca `script.fn_log_and_raise_error` con codice:

* `CATASTO_SOURCE_NOT_FOUND`

Nel payload vengono loggati:

* `istanza_id`
* `parent_istanza_id`

> Nota: in implementazione la log è pensata come errore “hard” perché l’operazione di subentro richiede una sorgente catastale coerente.

**6) Clone del record catasto (INSERT)**

Viene inserita una nuova riga in `anagrafiche.catasto_unita_immobiliari` copiando i campi rilevanti dal record sorgente:

* sezione/foglio/particella/subalterno
* categoria/classe/rendita
* consistenza
* tipo_accatastamento / rurale / destinazione
* anno_protocollo / superficie
* `storicizza` con fallback `COALESCE(..., true)`

L’`id` generato viene salvato in `v_new_catasto_id`.

**7) Aggancio istanza → nuovo catasto (UPDATE)**

La funzione aggiorna:

* `anagrafiche.istanze_utilities.catasto_unita_immobiliare_id = v_new_catasto_id`

con guardia idempotente:

* `AND iu.catasto_unita_immobiliare_id IS NULL`

Infine:

* `RETURN v_new_catasto_id`

---

### 🧩 Side Effects

✅ La funzione **modifica dati**:

* INSERT su `anagrafiche.catasto_unita_immobiliari`
* UPDATE su `anagrafiche.istanze_utilities`

❌ Non gestisce direttamente:

* legame catasto↔indirizzo (tabella ponte)
* clienti/PDP

---

### 🔗 Integrazione con i Trigger

Nel flusso previsto:

1. si valorizza `parent_istanza_id` sull’istanza (subentro)
2. trigger `trg_iu_z50_clone_catasto_from_parent_aft_upd` esegue la clonazione (tipicamente invocando questa funzione, direttamente o via `trgfn_*` wrapper)
3. trigger `trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd` garantisce la presenza del legame nella tabella ponte `catasto_unita_immobiliari_indirizzi` quando sono presenti **entrambi** i riferimenti (istanza ha catasto + indirizzo)

Questa funzione copre il cuore del punto 2: **crea e aggancia** il catasto clonato.

---

### ⚙️ Considerazioni di Concorrenza

* L’uso di `FOR UPDATE` è intenzionale per evitare che due transazioni concorrenti clonino due catasti distinti per la stessa istanza.
* L’UPDATE finale con condizione `... IS NULL` aggiunge una seconda barriera idempotente.

---

### ⚠️ Gestione Errori

| Scenario                        | Comportamento                                           |
| ------------------------------- | ------------------------------------------------------- |
| `p_istanza_utilities_id` NULL   | `fn_log_and_raise_error` con `ERRORE_PARAMETRI`         |
| istanza senza parent            | ritorna `NULL`                                          |
| parent senza catasto agganciato | `fn_log_and_raise_error` con `CATASTO_SOURCE_NOT_FOUND` |

---

### 🔍 Esempi d’Uso

**Clonazione esplicita (manuale)**

```sql
SELECT script.fn_clone_catasto_from_parent_by_istanza(12345);
```

**Verifica risultato e aggancio**

```sql
WITH c AS (
  SELECT script.fn_clone_catasto_from_parent_by_istanza(12345) AS new_catasto_id
)
SELECT iu.id, iu.catasto_unita_immobiliare_id, c.new_catasto_id
FROM anagrafiche.istanze_utilities iu
JOIN c ON true
WHERE iu.id = 12345;
```

---

### 🧪 Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. **Parametro NULL** → attesa eccezione `ERRORE_PARAMETRI`.
2. Istanza senza parent → ritorno `NULL`.
3. Istanza con parent ma parent senza catasto → attesa eccezione `CATASTO_SOURCE_NOT_FOUND`.
4. Istanza con parent con catasto → ritorno `id` nuovo, e colonna `istanze_utilities.catasto_unita_immobiliare_id` valorizzata.
5. **Idempotenza:** richiamo ripetuto → ritorna lo stesso id senza creare nuove righe.
6. **Concorrenza:** due transazioni parallele → solo una crea riga; l’altra ritorna l’id già agganciato (verificabile con test di integrazione).

---

### 📌 Best Practice

* ✅ Usare questa funzione nel solo contesto di **subentro** (parent come sorgente).
* ✅ Lasciare al trigger di sync la gestione della tabella ponte catasto↔indirizzi.
* ✅ Mantenere separati:

  * lookup sorgente (`fn_get_catasto_source_by_istanza`)
  * clonazione + aggancio (`fn_clone_catasto_from_parent_by_istanza`)

---

### 🗂️ Metadati

* **Schema:** `script`
* **Ritorno:** `bigint` (id catasto creato o già esistente)
* **Volatilità dichiarata:** `VOLATILE`
* **Owner:** `titodb`
* **Commento DB:**

  * “Clona i dati da catasto_unita_immobiliari associati alla parent_istanza verso una nuova riga catastale per l’istanza corrente (subentro).”
