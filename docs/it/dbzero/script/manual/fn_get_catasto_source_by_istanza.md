## 📘 Documentazione Concettuale – Funzione `script.fn_get_dati_catastali_by_istanza`

> 👀 **Vedi anche**
>
> Approfondimento tabelle: 
>
> * [anagrafiche.dati_catastali](/dbzero/anagrafiche/tabelle/dati_catastali)
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)

---

### 🎯 Scopo Principale

La funzione `script.fn_get_dati_catastali_by_istanza(p_istanza_utilities_id)` fornisce un **meccanismo di fallback** per recuperare i dati catastali di un punto di erogazione a partire da un’istanza di servizio. In particolare:

1. Tenta di ottenere i dati specifici legati all’istanza (`istanza_utilities_id`).
2. Se non trova nulla, ricava l’`indirizzo_dettaglio_id` associato all’istanza e cerca i dati catastali generici per quell’indirizzo (istanze null).
3. Restituisce il record `anagrafiche.dati_catastali` corrispondente o `NULL` se non esistono dati.

---

### 🛠️ Firma della Funzione

```sql
CREATE OR REPLACE FUNCTION script.fn_get_dati_catastali_by_istanza(
  p_istanza_utilities_id INTEGER
)
RETURNS anagrafiche.dati_catastali
LANGUAGE plpgsql
AS $function$
-- body...
$function$;
```

---

### 📥 Parametri

| Parametro                | Tipo    | Descrizione                                                              |
| ------------------------ | ------- | ------------------------------------------------------------------------ |
| `p_istanza_utilities_id` | INTEGER | Identificativo dell’istanza di servizio di cui cercare i dati catastali. |

---

### 📤 Valore di Ritorno

* Un record di tipo `anagrafiche.dati_catastali` contenente i campi catastali.
* **`NULL`** se non esistono né dati specifici per l’istanza né dati generici per l’indirizzo.

---

### 🔄 Logica Operativa

1. **Recupero diretto per istanza**

   ```sql
   SELECT *
     INTO v_result
   FROM anagrafiche.dati_catastali
   WHERE istanza_utilities_id = p_istanza_utilities_id
   LIMIT 1;
   ```

   Se esiste un record, `FOUND = true` e la funzione restituisce immediatamente `v_result`.

2. **Ricerca indirizzo associato**

   ```sql
   SELECT indirizzo_dettaglio_id
     INTO v_indirizzo_id
   FROM anagrafiche.istanze_utilities
   WHERE id = p_istanza_utilities_id;
   ```

3. **Fallback per indirizzo**

   ```sql
   SELECT *
     INTO v_result
   FROM anagrafiche.dati_catastali
   WHERE istanza_utilities_id IS NULL
     AND indirizzo_dettaglio_id = v_indirizzo_id
   LIMIT 1;
   ```

   Se trova un record, restituisce `v_result`.

4. **Default**

   * Se nessuno dei due SELECT ha prodotto risultati, la funzione esegue `RETURN NULL;`.

---

### 🔍 Esempi di Utilizzo

* **Ottenere dati catastali specifici o generici**:

  ```sql
  SELECT *
    FROM script.fn_get_dati_catastali_by_istanza(123);
  ```

* **Usare in JOIN**:

  ```sql
  SELECT iu.id,
         dc.particella,
         dc.subalterno
    FROM anagrafiche.istanze_utilities iu
    LEFT JOIN LATERAL script.fn_get_dati_catastali_by_istanza(iu.id) AS dc
      ON true;
  ```

---

### ⚠️ Gestione Errori e Performance

* La funzione restituisce `NULL` anziché sollevare eccezioni se non trova dati.
* Entrambe le query usano `LIMIT 1` per *stop* precoce.
* Indici su `anagrafiche.dati_catastali(istanza_utilities_id)` e `(indirizzo_dettaglio_id, istanza_utilities_id)` sono fondamentali per performance.

---

### 📌 Best Practice

* Assicurarsi che esistano indici sui campi di ricerca nella tabella `dati_catastali`.
* Evitare di chiamare la funzione in cicli riga-per-riga senza necessità (prediligere JOIN LATERAL).
* In caso di import massivo, eseguire *batch* di aggiornamento con query dirette per backfill dei dati catastali.

---