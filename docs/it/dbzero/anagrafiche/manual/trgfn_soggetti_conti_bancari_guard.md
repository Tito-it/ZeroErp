## 📘 Documentazione Tecnica – Trigger Function `anagrafiche.trgfn_soggetti_conti_bancari_guard`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari)   
> * [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari)    
>


---

### 🎯 Scopo Principale
(latest review 16-12-25)
La trigger function **`anagrafiche.trgfn_soggetti_conti_bancari_guard()`** applica controlli di guardia (coerenza e ammissibilità) sui legami tra soggetti e conti bancari, con due obiettivi principali:

1. **Impedire** la creazione/modifica di un legame verso un conto bancario **non attivo**.
2. **Bloccare** incoerenze sulle date di validità, assicurando che l’intervallo temporale sia corretto.

In caso di violazione, la funzione genera un **errore applicativo** tramite `anagrafiche.fn_log_and_raise_error`.

---

### 🛠️ Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()
RETURNS trigger
LANGUAGE plpgsql;
```

---

### 📥 Input (Record Trigger)

Utilizza questi campi del record `NEW` (tabella legame):

* `NEW.conto_bancario_id`
* `NEW.valido_dal`
* `NEW.valido_al`

> Nota: nel codice sono presenti riferimenti a `NEW.data_al` / `NEW.data_dal` nel payload log: verificare la coerenza con i nomi effettivi delle colonne della tabella (probabile refuso; vedi sezione “Note di Allineamento”).

E legge dalla tabella conti:

* `anagrafiche.conti_bancari(attivo)`

---

### 📤 Output

* Ritorna `NEW`.
* In caso di violazione: errore applicativo (bloccante).

---

### 🔄 Logica Operativa

 **1) Guardia: conto bancario deve essere attivo**

La funzione legge lo stato del conto:

```sql
SELECT attivo INTO v_attivo
FROM anagrafiche.conti_bancari
WHERE id = NEW.conto_bancario_id;
```

Se `v_attivo IS NOT TRUE` (cioè `FALSE` o `NULL`):

* genera errore applicativo con codice:

  * `E_CONTO_BANCARIO`

Payload log include:

* `tabella = 'anagrafiche.conti_bancari'`
* `conto_bancario_id`
* `error = SQLERRM`

> Nota: in questa sezione l’uso di `SQLERRM` è informativo, ma non rappresenta necessariamente un errore SQL in corso (siamo in un controllo logico). È coerente se si usa come campo “note”, ma non è indispensabile.

 **2) Guardia: coerenza date di validità**

Se entrambe le date sono valorizzate e l’intervallo è invertito:

* `NEW.valido_al < NEW.valido_dal`

allora viene generato errore applicativo con codice:

* `E_DATA_AL_MINORE_DAL`

Payload log include (come da codice):

* `tabella = 'anagrafiche.conti_bancari'` (nota: qui semanticamente sarebbe più corretto indicare la tabella legame)
* `data_al`, `data_dal` (vedi nota allineamento sotto)
* `error = SQLERRM`

---

### ⚠️ Error Handling

Errori gestiti:

| Codice                 | Scenario                                  | Effetto                        |
| ---------------------- | ----------------------------------------- | ------------------------------ |
| `E_CONTO_BANCARIO`     | conto bancario non attivo (o non trovato) | errore applicativo (bloccante) |
| `E_DATA_AL_MINORE_DAL` | intervallo date invertito                 | errore applicativo (bloccante) |

Handler utilizzato:

* `anagrafiche.fn_log_and_raise_error(...)`

---

### 🧩 Side Effects

* Nessun DML diretto.
* Effetto principale: blocco INSERT/UPDATE sul legame se le regole non sono rispettate.

---

### 🔍 Considerazioni di Modellazione

* La regola “conto attivo” evita collegamenti verso conti bancari dismessi/disattivati, preservando integrità funzionale (oltre alla sola FK).
* Il controllo date è coerente con un CHECK constraint, ma qui viene reso **bloccante** con un messaggio applicativo centralizzato.

---

### 🧪 Note per Test (pgTAP / SQL)

Casi minimi consigliati:

1. `conto_bancario_id` riferisce un conto con `attivo = true` → OK.
2. `conto_bancario_id` riferisce un conto con `attivo = false` → errore `E_CONTO_BANCARIO`.
3. `conto_bancario_id` non esiste → `v_attivo` resta NULL → errore `E_CONTO_BANCARIO`.
4. `valido_dal` e `valido_al` valorizzate con `valido_al < valido_dal` → errore `E_DATA_AL_MINORE_DAL`.
5. date coerenti o una delle due NULL → OK.

---

### 🧩 Note di Allineamento (da verificare nel refactor)

Nel corpo del trigger, il controllo usa:

* `NEW.valido_dal` / `NEW.valido_al`

ma nel payload log vengono referenziati:

* `NEW.data_al` / `NEW.data_dal`

📌 **Azione consigliata:** allineare i nomi nel payload a quelli effettivi della tabella (probabile sostituzione corretta: `NEW.valido_al` e `NEW.valido_dal`).

Inoltre, nel payload della violazione date la chiave `tabella` è impostata a `anagrafiche.conti_bancari`: valutare se sia più corretto indicare la tabella legame (es. `anagrafiche.soggetti_conti_bancari`).

---

### 📌 Best Practice

* ✅ Collegare questa function a un trigger `BEFORE INSERT OR UPDATE` sulla tabella legame soggetto↔conto.
* ✅ Mantenere la regola “conto attivo” nel layer DB per evitare bypass applicativi.
* ✅ Allineare il payload dei log ai nomi colonna reali (importante per troubleshooting e dashboard).

---

### 🗂️ Metadati

* **Schema:** `anagrafiche`
* **Tipo:** trigger function (guard/consistency)
* **Tabelle coinvolte:** conti bancari + tabella legame
* **Meccanismo errore:** `anagrafiche.fn_log_and_raise_error`
