## 📘 Documentazione Concettuale – Funzione `script.fn_valida_partita_iva(piva TEXT)`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
> - [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)      
>
> Approfondimento funzioni :    
> - [script.fn_valida_codice_fiscale](/dbzero/script/funzioni/fn_valida_codice_fiscale)    
> - [anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch)    
---
### 🎯 Scopo Principale

Verificare **formalmente** la correttezza di una Partita IVA italiana (11 cifre) calcolando il **check digit** con l’algoritmo di Luhn modificato, restituendo:

* `TRUE` se il carattere di controllo (ultima cifra) è corretto;
* `FALSE` altrimenti.

---

### 🔍 Parametro di Input

| Nome   | Tipo   | Descrizione                                                  |
| ------ | ------ | ------------------------------------------------------------ |
| `piva` | `TEXT` | Stringa di 11 cifre numeriche rappresentante la Partita IVA. |

---

### ⚙️ Flusso Operativo

1. **Controllo preliminare**

   * `piva` non `NULL`, lunghezza = 11, e contiene solo cifre (`0-9`).
   * Se fallisce, ritorna `FALSE` immediatamente.

2. **Calcolo della somma**
   Per le prime 10 cifre (posizioni 1–10):

   * **Posizioni dispari** (1,3,5,...,9): somma diretta della cifra.
   * **Posizioni pari** (2,4,6,...,10):

     * raddoppia la cifra;
     * se il risultato > 9, sottrae 9;
     * somma il valore ottenuto.

3. **Determinazione del check digit**

   ```plpgsql
   check_digit := (10 - (somma % 10)) % 10;
   ```

4. **Confronto finale**

   * Legge l’11ª cifra di `piva` e la confronta con `check_digit`.
   * Ritorna `TRUE` se coincidono, `FALSE` altrimenti.

---

### 🔒 Scelte di Design

* **Validazione formale**: limita il controllo al carattere di controllo per garantire efficienza e semplicità.
* **Algoritmo Luhn modificato**: conforme alle regole italiane di checksum per la Partita IVA.
* **Layer Applicativo**: eventuali controlli aggiuntivi (es. format avanzati, integrazione con servizi esterni) vanno delegati al backend per maggiore flessibilità.

---

### 💡 Vantaggi Operativi

* **Performance**: `IMMUTABLE` e semplice logica PL/pgSQL, eseguibile direttamente al DB.
* **Coerenza**: un’unica funzione di riferimento per la validazione di P.IVA nelle trigger, stored procedure e script.
* **Manutenibilità**: separazione tra validazione formale e logica di business nel backend.

---

> 🧠 **“Centralizzare il check digit della Partita IVA al livello database garantisce un unico punto di validazione, riduce ridondanza di codice e migliora l’affidabilità dei dati.”**
