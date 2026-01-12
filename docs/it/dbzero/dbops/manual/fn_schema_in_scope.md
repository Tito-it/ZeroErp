## 📘 Documentazione Concettuale – Funzione `dbops.fn_schema_in_scope`

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope)
> * [dbops.fn_schema_match](/dbzero/dbops/funzioni/fn_schema_match)
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope)
>
> Guide:
>
> * [Automazioni – Overview del Modulo](/guide/automazione-db)

---

### 🎯 Scopo Principale

(latest review 10-01-26)
La funzione **`dbops.fn_schema_in_scope(p_rule_target, p_schemas)`** è un **helper booleano** utilizzato dalle automazioni per verificare se uno schema specificato da una regola (`p_rule_target`) appartiene all’insieme di schemi effettivamente in scope (`p_schemas`).

---

### 🔍 Parametri di input

| Parametro       | Tipo   | Obbligatorio | Descrizione                                                         |
| --------------- | ------ | :----------: | ------------------------------------------------------------------- |
| `p_rule_target` | text   |      ✔️       | Schema target della regola (può includere keyword speciale `*all`). |
| `p_schemas`     | text[] |      ✔️       | Array di schemi da considerare come scope.                          |

---

### 📤 Valore di ritorno

`boolean` – `true` se lo schema target è incluso nello scope o se `p_rule_target='*all'`; altrimenti `false`.

---

### ⚙️ Flusso logico

1. Se `p_rule_target` è `NULL` → ritorna `false`.
2. Se `p_rule_target='*all'` (case insensitive) → ritorna `true`.
3. Se `p_schemas` è nullo o vuoto → ritorna `false`.
4. Altrimenti confronta ogni schema in `p_schemas` con `p_rule_target` (case insensitive). Se c’è match → ritorna `true`.
5. In assenza di match → ritorna `false`.

---

### 🧩 Casi d’uso tipici

* **Filtro regole automazioni**: applicare una regola solo se lo schema target della regola è incluso nello scope.
* **Wildcard `*all`**: consentire di definire regole valide per tutti gli schemi senza doverli elencare.
* **Validazione**: semplificare la logica condizionale in funzioni come `fn_run_automations_*`.

---

### 🛡️ Permessi e sicurezza

* È una funzione **IMMUTABLE** e non accede a cataloghi o dati esterni.
* Sicura e senza effetti collaterali.

---

### 🚀 Esempi di utilizzo

* `SELECT dbops.fn_schema_in_scope('anagrafiche', ARRAY['anagrafiche','config']);` → `true`.
* `SELECT dbops.fn_schema_in_scope('vendite', ARRAY['anagrafiche','config']);` → `false`.
* `SELECT dbops.fn_schema_in_scope('*all', ARRAY['anagrafiche']);` → `true`.

---

### 📌 Considerazioni

* Pensata come building‑block: viene usata in condizioni `WHERE` di `fn_run_automations_*`.
* Gestisce esplicitamente i casi limite (`NULL`, array vuoti).

---

### ✅ Benefici

* **Semplicità**: incapsula la logica di confronto schema/scope.
* **Riutilizzabilità**: usata trasversalmente in più moduli di automazione.
* **Flessibilità**: supporta keyword `*all` per regole globali.

---

> 🧠 **In sintesi**: `fn_schema_in_scope` è un **helper fondamentale** che permette di verificare in modo uniforme se uno schema rientra nello scope delle automazioni, gestendo anche il caso speciale `*all`.
