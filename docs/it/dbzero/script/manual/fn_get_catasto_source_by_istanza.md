## 📘 Documentazione Tecnica – Funzione `script.fn_get_catasto_source_by_istanza`

> 👀 **Vedi anche**
>
**Approfondimeto tabelle:**
>
[anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)   
> [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari)    
>
**Automazioni collegate (subentro/catasto):**
>
Trigger: `anagrafiche.trg_iu_z50_clone_catasto_from_parent_aft_upd` (clonazione catasto da parent)     
> Trigger: `anagrafiche.trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd` (sync tabella ponte catasto↔indirizzi)    

---
### 🎯 Scopo Principale
La funzione **`script.fn_get_catasto_source_by_istanza(p_istanza_utilities_id)`** recupera il record catastale **"sorgente"** da utilizzare come base per una **clonazione** in caso di **subentro**.

✅ La sorgente è determinata **esclusivamente** dalla relazione:

* `anagrafiche.istanze_utilities.parent_istanza_id`

In altre parole: **solo la parent_istanza può fornire il catasto sorgente**.

---

### Contesto di Modellazione

A valle del refactor del dominio catasto:

* Il legame **ufficiale** tra istanza e catasto è:

  * `anagrafiche.istanze_utilities.catasto_unita_immobiliare_id`
* La tabella `anagrafiche.catasto_unita_immobiliari` **non contiene più** il riferimento diretto all’istanza (es. `istanza_utility_id` rimosso).

Questa funzione implementa quindi un **lookup puro** basato sul modello corrente.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION script.fn_get_catasto_source_by_istanza(
  p_istanza_utilities_id bigint
)
RETURNS anagrafiche.catasto_unita_immobiliari
LANGUAGE plpgsql;
```

---

### Parametri

| Parametro                |     Tipo | Obbligatorio | Descrizione                                                                                   |
| ------------------------ | -------: | :----------: | --------------------------------------------------------------------------------------------- |
| `p_istanza_utilities_id` | `bigint` |      ✅       | Identificativo dell’istanza per la quale si vuole determinare il catasto sorgente (subentro). |

---

### Valore di Ritorno

* **Record** di tipo `anagrafiche.catasto_unita_immobiliari` (catasto sorgente della parent).
* ⚠️ **`NULL`** se:

  * l’istanza non ha una `parent_istanza_id`, oppure
  * la parent non ha valorizzato `catasto_unita_immobiliare_id`.

---

### Comportamento su Parametri Non Validi

Se `p_istanza_utilities_id` è `NULL`, la funzione **non** ritorna `NULL`: viene generato un errore applicativo tramite logging centralizzato:

* invoca `script.fn_log_and_raise_error(...)`
* codice errore: `ERRORE_PARAMETRI`
* contesto: funzione `script.fn_get_catasto_source_by_istanza`

Questo garantisce:

* tracciabilità in `error_log` (o equivalente)
* blocco immediato dell’esecuzione per uso errato dell’API DB

---

### Logica Operativa

La funzione è volutamente **minimale** e **deterministica**.

#### 1) Validazione parametro

* Se `p_istanza_utilities_id IS NULL` → errore (log + raise).

#### 2) Lettura della parent

Recupera `parent_istanza_id` dalla riga di `anagrafiche.istanze_utilities`.

* Se `parent_istanza_id IS NULL` → `RETURN NULL`.

#### 3) Recupero catasto dalla parent

Legge il record catastale collegato alla parent:

* join `istanze_utilities` (parent) → `catasto_unita_immobiliari`

* tramite `iu_parent.catasto_unita_immobiliare_id = c.id`

* Se il join non produce righe (`NOT FOUND`) → `RETURN NULL`.

#### 4) Ritorno del record

Ritorna il record `anagrafiche.catasto_unita_immobiliari` individuato.

---

### Dipendenze Dati

**Input minimi necessari per ottenere una sorgente:**

1. `anagrafiche.istanze_utilities.id = p_istanza_utilities_id`
2. `anagrafiche.istanze_utilities.parent_istanza_id IS NOT NULL`
3. `anagrafiche.istanze_utilities (parent).catasto_unita_immobiliare_id IS NOT NULL`

---

### Esempi d’Uso

#### Caso standard: recupero sorgente per subentro

```sql
SELECT *
FROM script.fn_get_catasto_source_by_istanza(12345);
```

#### Uso in `LATERAL` per lista istanze (debug / audit)

```sql
SELECT iu.id,
       iu.parent_istanza_id,
       src.foglio_catastale,
       src.particella,
       src.subalterno
FROM anagrafiche.istanze_utilities iu
LEFT JOIN LATERAL script.fn_get_catasto_source_by_istanza(iu.id) AS src
  ON true;
```

---

### Considerazioni di Performance

* La funzione esegue **2 lookup** puntuali su PK/FK:

  * 1 SELECT su `istanze_utilities(id)`
  * 1 SELECT join su `istanze_utilities(id)` + `catasto_unita_immobiliari(id)`
* Con indici standard su PK, il costo è **O(1)** e adeguato anche in chiamate ripetute.

**Nota:** l’uso di `LIMIT 1` rende esplicito lo stop precoce, anche se il join su PK dovrebbe già garantire una sola riga.

---

### Integrazione nel Flusso “Subentro”

Questa funzione è pensata per essere usata come **building-block** dalla logica di clonazione, tipicamente:

1. l’istanza riceve `parent_istanza_id`
2. un trigger AFTER (`trg_iu_z50_clone_catasto_from_parent_aft_upd`) clona e valorizza `catasto_unita_immobiliare_id`
3. un trigger di sync (`trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd`) crea/garantisce la relazione catasto↔indirizzo nella tabella ponte

La funzione qui documentata copre **solo** il punto 2.a: *determinare il record sorgente*.

---

### ⚠️ Best Practice e Vincoli di Utilizzo

* Usare la funzione **solo** in contesti dove la parent è la sorgente ufficiale (subentro).
* Non usare come fallback “generico” su indirizzo o PDP: questa funzione **non** implementa altre strategie.
* In caso si voglia introdurre un fallback alternativo, farlo con **funzioni distinte** (per non rompere la semantica di questa).

---

### Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. **Parametro NULL** → attesa eccezione `ERRORE_PARAMETRI`.
2. Istanza senza parent → ritorno `NULL`.
3. Istanza con parent ma parent senza catasto agganciato → ritorno `NULL`.
4. Istanza con parent e parent con `catasto_unita_immobiliare_id` → ritorno record coerente.

---

### Metadati

* **Schema:** `script`
* **Tipo:** lookup puro (nessun side-effect)
* **Volatilità dichiarata:** `VOLATILE` (nota: la logica è deterministica rispetto ai dati correnti; la dichiarazione è coerente con funzioni che leggono tabelle)
* **Owner:** `titodb`

---

### 🔖 Commento DB (per coerenza)

La funzione è commentata in DB come:

> Recupera il record catastale "sorgente" da clonare per una istanza_utilities.
> La sorgente è determinata ESCLUSIVAMENTE da: istanze_utilities.parent_istanza_id
