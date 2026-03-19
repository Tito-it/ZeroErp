## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_conti_bancari_normalize`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
> 
[anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari)     
>
**Nota**: questa funzione è pensata per essere agganciata a un trigger `BEFORE INSERT OR UPDATE` sulla tabella conti bancari (o equivalente).

---
### 🎯 Scopo Principale
(latest review 15-12-26)
La trigger function **`anagrafiche.trgfn_conti_bancari_normalize()`** normalizza i campi bancari principali prima della persistenza, applicando regole semplici e deterministicamente ripetibili:

* **IBAN**: rimozione spazi + uppercase
* **Paese**: valorizzazione automatica dai primi 2 caratteri dell’IBAN (se mancante)
* **BIC/SWIFT**: rimozione spazi + uppercase

Obiettivo:

* evitare differenze di formattazione (`it 60 x...` vs `IT60X...`)
* ridurre errori in confronti/unique-check/ricerche
* derivare automaticamente il paese quando possibile

---

### Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_conti_bancari_normalize()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### Input (Record Trigger)

Utilizza (quando presenti) i campi del record `NEW`:

* `NEW.iban`
* `NEW.paese`
* `NEW.bic_swift`

---

### Output

* Ritorna `NEW`.
* Può modificare:

  * `NEW.iban`
  * `NEW.paese`
  * `NEW.bic_swift`

---

### Logica Operativa

 **1) Normalizzazione IBAN**

Se `NEW.iban IS NOT NULL`:

* rimuove tutti gli spazi (`\s+`) con `regexp_replace(..., '', 'g')`
* converte in maiuscolo (`upper(...)`)

Esempio:

* `"it 60 x054 2811"` → `"IT60X0542811"`

 **2) Derivazione automatica del paese**

Sempre nel ramo IBAN:

* se `NEW.paese IS NULL` **e** `length(NEW.iban) >= 2`
* imposta `NEW.paese := substr(NEW.iban, 1, 2)`

Quindi il paese viene derivato dai primi due caratteri dell’IBAN.

> Nota: la funzione non valida che i due caratteri siano effettivamente un codice ISO; si limita a derivarlo.

 **3) Normalizzazione BIC/SWIFT**

Se `NEW.bic_swift IS NOT NULL`:

* rimuove gli spazi
* converte in maiuscolo

Esempio:

* `"deut de ff"` → `"DEUTDEFF"`

---

### Side Effects

* Nessun DML diretto.
* Modifica del record `NEW` (normalizzazione), quindi va usata su trigger **BEFORE**.

---

### ⚠️ Error Handling

* Nessun logging e nessuna eccezione.
* Non esegue controlli di validità formale (lunghezza IBAN, checksum, pattern BIC, ecc.).

> Se sono previsti vincoli di validazione, vanno implementati con:
>
CHECK constraint / funzione di validazione dedicata
> trigger separato (es. `trgfn_conti_bancari_validate_*`)

---

### Esempi di Comportamento

 **Caso A – IBAN con spazi e paese mancante**

Input:

* `NEW.iban = 'it 60 x054 2811 1010 0000 0123 456'`
* `NEW.paese = NULL`

Output:

* `NEW.iban = 'IT60X0542811101000000123456'`
* `NEW.paese = 'IT'`

 **Caso B – Paese già valorizzato**

Input:

* `NEW.iban = 'IT60X0542811101000000123456'`
* `NEW.paese = 'IT'`

Output:

* `NEW.paese` resta invariato.

 **Caso C – BIC con spazi**

Input:

* `NEW.bic_swift = 'deut de ff'`

Output:

* `NEW.bic_swift = 'DEUTDEFF'`

---

### Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. IBAN NULL → nessuna modifica a iban/paese.
2. IBAN con spazi → spazi rimossi e uppercase.
3. IBAN valido con `paese NULL` → paese valorizzato con `substr(iban,1,2)`.
4. IBAN con `paese` già valorizzato → paese invariato.
5. BIC NULL → nessuna modifica.
6. BIC con spazi → spazi rimossi e uppercase.

---

### Best Practice

* Trigger `BEFORE INSERT OR UPDATE` su `anagrafiche.conti_bancari`.
* Affiancare una validazione formale separata se necessaria (IBAN/BIC).
* Evitare validazioni pesanti in normalize: questa funzione deve restare *fast* e ripetibile.

---

### Metadati

* **Schema:** `anagrafiche`
* **Tipo:** trigger function (normalize)
* **Output:** `NEW`
* **Responsabilità:** normalizzazione formale (spazi/maiuscole) + derivazione paese da IBAN
