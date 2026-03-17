## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_pdp_set_default_stato`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)    
> [config.stati_pdp](/dbzero/config/tabelle/stati_pdp)    
>

🎯 Scopo Principale
(latest review 16-12-25)
La trigger function **`anagrafiche.trgfn_pdp_set_default_stato()`** imposta automaticamente lo **stato tecnico** di un PDP a **DISP** (*Disponibile*) quando il campo `stato_pdp_id` non è stato valorizzato.

Regola:

* Se `NEW.stato_pdp_id` è `NULL` → assegna lo stato con `config.stati_pdp.codice_interno = 'DISP'`.
* Se `NEW.stato_pdp_id` è già valorizzato → non modifica nulla.

---

### Contesto

Il PDP deve avere sempre uno stato tecnico coerente:

* il default iniziale è **DISP** (Disponibile)
* altri stati (es. ATT, DTEC, DISM, ecc.) vengono gestiti da processi e regole specifiche

Questa trigger function garantisce che l’inserimento non lasci PDP “senza stato”.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_pdp_set_default_stato()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### Input (Record Trigger)

Utilizza:

* `NEW.stato_pdp_id`
* `NEW.tx_id`

E legge da:

* `config.stati_pdp` filtrando `codice_interno = 'DISP'`

---

### Output

* Ritorna `NEW`.
* Può modificare `NEW.stato_pdp_id` quando è `NULL`.

> Tipicamente si aggancia a un trigger `BEFORE INSERT` (o `BEFORE INSERT OR UPDATE`) perché modifica `NEW`.

---

### Logica Operativa

 **1) Guardia: stato già impostato**

Se `NEW.stato_pdp_id IS NOT NULL`:

* `RETURN NEW;`

 **2) Lookup stato DISP**

Recupera l’id dello stato tecnico DISPONIBILE:

```sql
SELECT id
INTO v_stato_disp_id
FROM config.stati_pdp
WHERE codice_interno = 'DISP';
```

 **3) Gestione anomalia: stato DISP mancante in config**

Se lo stato non è presente (`v_stato_disp_id IS NULL`), la funzione genera errore applicativo con `script.fn_log_and_raise_error`.

Caratteristiche:

* codice errore: `E_CODICE`
* contesto: `anagrafiche.trgfn_pdp_set_default_stato`
* payload JSONB include un messaggio descrittivo e il valore (NULL) di `v_stato_disp_id`
* tx context: `NEW.tx_id`
* parametri extra: `'DISP'`, `'config.stati_pdp'`

> Questo scenario è considerato **bloccante**: senza un record DISP in configurazione, il default non può essere applicato.

 **4) Assegnazione default**

Se il lookup ha successo:

* `NEW.stato_pdp_id := v_stato_disp_id;`
* `RETURN NEW;`

---

### ⚠️ Error Handling

Errore gestito:

| Codice     | Scenario                                               | Effetto                        |
| ---------- | ------------------------------------------------------ | ------------------------------ |
| `E_CODICE` | manca `config.stati_pdp` con `codice_interno = 'DISP'` | errore applicativo (bloccante) |

---

### Side Effects

* Nessun DML diretto.
* Modifica del record `NEW` (assegnazione default), quindi la funzione è **BEFORE-oriented**.

---

### Considerazioni di Performance

* 1 lookup su tabella di configurazione (`config.stati_pdp`) per ogni evento.

Consigliato:

* indice/unique su `config.stati_pdp.codice_interno` (o vincolo unico) per garantire lookup veloce e deterministico.

---

### Esempi di Comportamento

 **Caso A – Stato già presente**

* `NEW.stato_pdp_id = 5`

👉 nessuna modifica.

 **Caso B – Stato mancante**

* `NEW.stato_pdp_id = NULL`
* `config.stati_pdp` contiene `DISP` con `id = 2`

👉 `NEW.stato_pdp_id := 2`.

 **Caso C – Config incompleta**

* `NEW.stato_pdp_id = NULL`
* nessun record `codice_interno='DISP'`

👉 errore `E_CODICE` (bloccante).

---

### Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. Inserimento PDP con `stato_pdp_id` valorizzato → invariato.
2. Inserimento PDP con `stato_pdp_id NULL` e config DISP presente → default valorizzato.
3. Inserimento PDP con `stato_pdp_id NULL` e config DISP assente → errore `E_CODICE`.

---

### Best Practice

* Assicurare un record di configurazione con `codice_interno='DISP'` (meglio con vincolo UNIQUE su `codice_interno`).
* Collegare questa function a un trigger `BEFORE INSERT` sulla tabella `anagrafiche.pdp`.
* Limit
