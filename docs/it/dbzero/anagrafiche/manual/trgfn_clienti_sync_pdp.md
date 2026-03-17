## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_clienti_sync_pdp()`

>
👀 **Vedi anche**
>
**Approfondimento tabelle:**
> • [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)  
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)  
> 
**Approfondimento funzioni:**
>
• [`anagrafiche.trgfn_clienti_sync_utility_from_ba()`](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_utility_from_ba)  
>
• [Guida – Gestione delle Istanze Utility e Collegamento con PDP & Clienti](/guide/gestione-delle-istanze-utility)  

---

### 🎯 Scopo Principale
(latest review 09-12-25)
La funzione `anagrafiche.trgfn_clienti_sync_pdp()` è una **trigger function di sincronizzazione** che ha il compito di mantenere allineato il campo `pdp_id` della tabella `anagrafiche.clienti` con il valore presente sull’istanza collegata (`anagrafiche.istanze_utilities`).

In altre parole:

* `clienti.pdp_id` **non è un campo "master"**, ma una **denormalizzazione controllata** del valore `istanze_utilities.pdp_id`.
* La funzione assicura che, quando viene impostata o modificata `NEW.istanza_utility_id`, il relativo `pdp_id` sul cliente sia sempre coerente.

---

### Contesto e tabelle coinvolte

**Tabella: `anagrafiche.clienti`**

Colonne rilevanti per la funzione:

* `istanza_utility_id` → FK verso `anagrafiche.istanze_utilities(id)`;
* `pdp_id`             → FK denormalizzata verso `anagrafiche.pdp(id)`.

**Tabella: `anagrafiche.istanze_utilities`**

Colonne rilevanti:

* `id`      → PK dell’istanza;
* `pdp_id`  → FK (parte di FK composita con `indirizzo_dettaglio_id`) verso `anagrafiche.pdp`.

L’istanza è l’**unica sorgente autorevole** del legame con il PDP; il cliente si limita a riflettere tale informazione.

---

### Logica di funzionamento

Passi principali:

1. **Verifica presenza istanza**
   Se `NEW.istanza_utility_id` è valorizzato, la funzione tenta di recuperare la relativa istanza.

2. **Sincronizzazione PDP**
   Esegue:

   ```sql
   SELECT iu.pdp_id
   INTO NEW.pdp_id
   FROM anagrafiche.istanze_utilities iu
   WHERE iu.id = NEW.istanza_utility_id;
   ```

   In questo modo `clienti.pdp_id` viene impostato esattamente al valore presente sull’istanza.

3. **Gestione del caso "istanza inesistente" (NOT FOUND)**
   Se la SELECT non trova nessuna riga:

   * `NEW.pdp_id` viene impostato a `NULL`.
   * Questo evita che rimanga valorizzato un `pdp_id` incoerente rispetto all’istanza.

4. **Restituzione della riga**
   La funzione termina con `RETURN NEW;`, come da convenzione per le trigger function `BEFORE`.

---

### Trigger associato (schema suggerito)

Tipicamente la funzione è collegata a un trigger del tipo:

```sql
CREATE OR REPLACE TRIGGER trg_clienti_sync_pdp_ins_upd
    BEFORE INSERT OR UPDATE OF istanza_utility_id
    ON anagrafiche.clienti
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trgfn_clienti_sync_pdp();
```

> ☝️ In questo modo, ogni volta che viene creato un cliente o cambiata
> l’istanza collegata, il `pdp_id` viene riallineato automaticamente.

---

### Regole di coerenza garantite

* **Single source of truth**: il PDP associato a un cliente è sempre quello definito sull’istanza (`istanze_utilities.pdp_id`).
* **Nessun valore "sporco"**: se per qualsiasi motivo l’istanza non esiste (errore di chiamata, incoerenza dati), il `pdp_id` del cliente viene forzato a `NULL`.
* **Supporto ai vincoli di dominio**: i vincoli come `ex_clienti_no_overlap_stesso_pdp` si appoggiano su un `pdp_id` coerente, alimentato dall’istanza.

---

### Esempi di comportamento

 Caso 1 – Creazione cliente con istanza valida

* `NEW.istanza_utility_id = 100`
* In `istanze_utilities(100)` → `pdp_id = 3`.

➡️ Dopo il trigger: `NEW.pdp_id = 3`.

---

 Caso 2 – Cambio istanza sul cliente

* Prima: `istanza_utility_id = 100` → `pdp_id = 3`.
* Update: `NEW.istanza_utility_id = 200` dove `istanze_utilities(200).pdp_id = 5`.

➡️ Dopo il trigger: `NEW.pdp_id = 5`.

---

 Caso 3 – Istanza non trovata (incoerenza)

* `NEW.istanza_utility_id` punta a un `id` che non esiste in `istanze_utilities`.

➡️ La SELECT non trova righe, `NOT FOUND` è true → `NEW.pdp_id := NULL`.

---

### Benefici del disegno

* Riduce il rischio di **disallineamento** tra cliente e istanza.
* Centralizza la logica di sincronizzazione in una singola funzione lato DB.
* Semplifica il codice applicativo: il frontend deve preoccuparsi solo di impostare correttamente `istanza_utility_id`, delegando al DB la propagazione del `pdp_id`.

In sintesi, `anagrafiche.trgfn_clienti_sync_pdp()` è un tassello fondamentale per garantire che tutte le logiche basate sul PDP (catene di istanze, vincoli di sovrapposizione, subentri) operino su dati coerenti e derivati da un’unica fonte autorevole: l’istanza di utility.
