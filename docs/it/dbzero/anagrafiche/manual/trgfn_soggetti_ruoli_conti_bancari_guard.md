## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari)   
> [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari)   
>
**Approfondimento funzioni:**
>
`anagrafiche.trgfn_soggetti_conti_bancari_guard`   
>
### 🎯 Scopo Principale
(last review 16-12-25)
La trigger function **`anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()`** applica controlli di guardia sui legami tra **ruoli del soggetto** e **conti bancari**, impedendo:

1. legami verso conti bancari **disattivati**;
2. legami con **intervallo date di validità incoerente**.

In caso di violazione, viene generato un **errore applicativo** tramite `anagrafiche.fn_log_and_raise_error`.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### Input (Record Trigger)

Utilizza dal record `NEW` (tabella legame):

* `NEW.conto_bancario_id`
* `NEW.valido_dal`
* `NEW.valido_al`

E legge da:

* `anagrafiche.conti_bancari(attivo)`

> Nota: anche qui nel payload log compaiono `NEW.data_al` / `NEW.data_dal`, mentre il controllo usa `NEW.valido_al` / `NEW.valido_dal`. Vedi “Note di allineamento”.

---

### Output

* Ritorna `NEW`.
* In caso di violazione: errore applicativo (bloccante).

---

### Logica Operativa

 **1) Guardia: conto bancario deve essere attivo**

Lookup:

```sql
SELECT attivo INTO v_attivo
FROM anagrafiche.conti_bancari
WHERE id = NEW.conto_bancario_id;
```

Se `v_attivo IS NOT TRUE` (FALSE o NULL) → errore:

* codice: `E_CONTO_BANCARIO`

Payload JSONB include:

* `tabella = 'anagrafiche.conti_bancari'`
* `conto_bancario_id`
* `error = SQLERRM`

 **2) Guardia: coerenza date**

Se entrambe le date sono valorizzate e:

* `NEW.valido_al < NEW.valido_dal`

→ errore:

* codice: `E_DATA_AL_MINORE_DAL`

Payload include (come da codice):

* `tabella = 'anagrafiche.conti_bancari'` (nota: semanticamente potrebbe essere la tabella legame)
* `data_al`, `data_dal` (vedi nota sotto)
* `error = SQLERRM`

---

### ⚠️ Error Handling

| Codice                 | Scenario                       | Effetto                        |
| ---------------------- | ------------------------------ | ------------------------------ |
| `E_CONTO_BANCARIO`     | conto non attivo / non trovato | errore applicativo (bloccante) |
| `E_DATA_AL_MINORE_DAL` | intervallo date invertito      | errore applicativo (bloccante) |

Handler:

* `anagrafiche.fn_log_and_raise_error(...)`

---

### Side Effects

* Nessun DML diretto.
* Effetto: blocco INSERT/UPDATE sul legame soggetto_ruolo↔conto quando non conforme.

---

### Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. conto attivo + date coerenti → OK.
2. conto non attivo → errore `E_CONTO_BANCARIO`.
3. conto inesistente → `v_attivo NULL` → errore `E_CONTO_BANCARIO`.
4. date invertite (`valido_al < valido_dal`) → errore `E_DATA_AL_MINORE_DAL`.
5. una delle due date NULL → OK.

---

### Best Practice

* Trigger `BEFORE INSERT OR UPDATE` sulla tabella legame soggetti_ruoli↔conti.
* Centralizzare i codici errore e mantenere coerenza del “contesto” di log.
* Mantenere la guardia sul conto attivo nel DB per evitare bypass applicativi.

---

### Metadati

* **Schema:** `anagrafiche`
* **Tipo:** trigger function (guard/consistency)
* **Tabelle coinvolte:** conti bancari + tabella legame ruoli↔conti
* **Meccanismo errore:** `anagrafiche.fn_log_and_raise_error`
