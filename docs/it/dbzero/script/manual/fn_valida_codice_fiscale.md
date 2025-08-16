##  📘 Documentazione Concettuale – Funzione `script.fn_valida_codice_fiscale(cf TEXT)`

> 👀 **Vedi anche**
>
> Approfondimento Tabelle:   
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)      
>
> Approfondimento funzioni :    
>
> * [script.fn_valida_partita_iva](/dbzero/script/funzioni/fn_valida_partita_iva)    
> * [anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch)    
---

### 🎯 Scopo Principale

* **Validazione formale** del Codice Fiscale (CF) calcolando e confrontando il carattere di controllo.
* **Supporto omocodici**, garantendo validità anche per CF derivati con omolettere.
* **Delegare al backend** i controlli di congruenza con data di nascita, sesso e luogo di nascita per mantenere flessibilità applicativa.

---

### 🔍 Parametri di Input

| Nome | Tipo   | Descrizione                                             |
| ---- | ------ | ------------------------------------------------------- |
| `cf` | `TEXT` | Codice Fiscale da validare (16 caratteri alfanumerici). |

---

### ⚙️ Flusso Operativo

1. **Verifica preliminare**

   * `cf` non `NULL`, lunghezza = 16, e solo caratteri `A-Z` o `0-9`.
   * Se fallisce, ritorna `FALSE`.
2. **Calcolo somma parziale**

   * Ciclo su posizioni 1..15:

     * **Posizioni dispari**: mappatura “strana” per numeri e lettere.
     * **Posizioni pari**: numeri trasformati in valore numerico, lettere `A→0`, …, `Z→25`.
   * Accumula i valori in `somma`.
3. **Determinazione carattere di controllo**

   * `check_char := CHR(65 + (somma % 26))`.
4. **Confronto finale**

   * Ritorna `TRUE` se `check_char` = sedicesimo carattere di `cf`, altrimenti `FALSE`.

---

### 🔒 Limiti e Scelte di Design

* **Solo Check Digit**: non verifica congruenza con data di nascita, sesso, luogo di nascita.
* **Omocodici**: supporta CF omocodici (stessa data, sesso, luogo, nome e cognome).
* **Layer Applicativo**: controlli avanzati demandati a backend (es. Django/FastAPI) o servizi esterni per facilitare aggiornamenti e regole di business.

---

### 💡 Vantaggi Operativi

* **Efficienza**: logica SQL compatta e `IMMUTABLE`, ottimizzata per database-level validation.
* **Affidabilità**: garantisce uniformità del controllo formale in tutta l’applicazione.
* **Manutenibilità**: separazione netta tra validazione formale al DB e logica di business nel backend.

---

> 🧠 **“Una validazione del CF snella e centralizzata al DB accelera i controlli di input, lasciando al backend la gestione delle regole di contesto e di business.”**
