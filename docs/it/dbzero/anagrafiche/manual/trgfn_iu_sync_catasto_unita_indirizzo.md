## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)    
> [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari)     
> [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)    
> [anagrafiche.catasto_unita_immobiliari_indirizzi](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari_indirizzi)    
>
**Trigger che la invoca (sync):**
>
`anagrafiche.trg_iu_z40_sync_catasto_unita_indirizzo_aft_ins_upd`   

---

### 🎯 Scopo Principale
(latest review 15-12-25)
La trigger function **`anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()`** garantisce che, quando una istanza (`anagrafiche.istanze_utilities`) dispone di:

* `catasto_unita_immobiliare_id` (unità catastale)
* `indirizzo_dettaglio_id` (indirizzo civico)

…esista il relativo legame nella tabella ponte:

* `anagrafiche.catasto_unita_immobiliari_indirizzi`

In pratica, assicura la **coerenza** tra:

* legame **istanza → catasto** (FK su istanze_utilities)
* legame **istanza → indirizzo** (FK su istanze_utilities)
* legame **catasto ↔ indirizzo** (tabella ponte)

---

### Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### Input (Record Trigger)

Utilizza questi campi del record `NEW`:

* `NEW.catasto_unita_immobiliare_id`
* `NEW.indirizzo_dettaglio_id`

---

### Output

* Ritorna sempre `NEW`.

---

### Logica Operativa

 **1) Guardia sui dati minimi**

Se manca uno dei due riferimenti, la funzione non può creare il legame in tabella ponte:

* se `NEW.catasto_unita_immobiliare_id IS NULL` **oppure**
* se `NEW.indirizzo_dettaglio_id IS NULL`

👉 allora **non fa nulla** e ritorna `NEW`.

 **2) Inserimento idempotente in tabella ponte**

Se entrambi i riferimenti sono presenti, inserisce la coppia:

* `catasto_unita_id = NEW.catasto_unita_immobiliare_id`
* `indirizzo_dettaglio_id = NEW.indirizzo_dettaglio_id`

in `anagrafiche.catasto_unita_immobiliari_indirizzi`.

L’inserimento è **idempotente** grazie a:

* `ON CONFLICT ON CONSTRAINT uq_catunitaindir DO NOTHING`

Questo implica che la tabella ponte ha un vincolo unico (atteso) sulle due colonne della relazione.

---

### Side Effects

✅ DML eseguito:

* INSERT su `anagrafiche.catasto_unita_immobiliari_indirizzi` (con `DO NOTHING` su duplicato)

❌ Nessuna modifica diretta a `anagrafiche.istanze_utilities`.

---

### Integrazione con Trigger su `istanze_utilities`

Questa funzione è pensata per essere richiamata da un trigger `AFTER INSERT OR UPDATE OF ...` su `anagrafiche.istanze_utilities`, tipicamente:

* `AFTER INSERT OR UPDATE OF indirizzo_dettaglio_id, catasto_unita_immobiliare_id`

Perché proprio questi campi?

* il legame catasto↔indirizzo diventa determinabile *solo* quando entrambi sono valorizzati
* aggiornamenti ad altri campi non devono generare side-effect

---

### Concorrenza e Robustezza

* L’operazione è safe in concorrenza: l’unicità è garantita dal vincolo `uq_catunitaindir` + `ON CONFLICT ... DO NOTHING`.
* L’assenza di lock espliciti è coerente: si tratta di un inserimento “best effort” idempotente.

---

### ⚠️ Error Handling

La funzione non logga e non solleva eccezioni.

* Se il vincolo `uq_catunitaindir` non esistesse o non fosse coerente con le colonne, l’errore emergerebbe come errore SQL a runtime (scenario di configurazione errata).

---

### Esempi (uso indiretto)

 **Caso tipico**

1. viene valorizzato `catasto_unita_immobiliare_id` (per clonazione o assegnazione manuale)
2. l’istanza ha già `indirizzo_dettaglio_id`
3. il trigger `z40` richiama questa function e crea/garantisce il link in tabella ponte

 **Verifica legame creato**

```sql
SELECT *
FROM anagrafiche.catasto_unita_immobiliari_indirizzi
WHERE catasto_unita_id = <catasto_id>
  AND indirizzo_dettaglio_id = <indirizzo_id>;
```

---

### Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. `catasto_unita_immobiliare_id` NULL → nessuna riga inserita in tabella ponte.
2. `indirizzo_dettaglio_id` NULL → nessuna riga inserita in tabella ponte.
3. Entrambi presenti → riga inserita.
4. Richiamo ripetuto (stessi valori) → nessun duplicato (verifica che conteggio righe resti 1).
5. Aggiornamento indirizzo (o catasto) → inserisce la nuova coppia (se ammesso dal modello; utile per capire se si vuole gestire anche “cleanup” di coppie vecchie: **non** gestito qui).

---

### Best Practice

* Mantenere la funzione **semplice e idempotente**.
* Usare un vincolo unico (es. `(catasto_unita_id, indirizzo_dettaglio_id)`) come base di consistenza.
* Delegare eventuali regole di cleanup/ri-allineamento a funzioni dedicate (questa non cancella né aggiorna legami esistenti).

---

### Metadati

* **Schema:** `anagrafiche`
* **Tipo:** trigger function (sync tabella ponte)
* **Tabella target trigger:** `anagrafiche.istanze_utilities`
* **Dipendenza vincolo:** `anagrafiche.catasto_unita_immobiliari_indirizzi.uq_catunitaindir`
