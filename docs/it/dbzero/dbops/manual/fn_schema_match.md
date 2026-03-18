## 📘 Documentazione Concettuale – Funzione `dbops.fn_schema_match`

> 👀 **Vedi anche**
>
Guida:
>
[Automazioni – Overview del Modulo](/guide/automazione-db)   
>
Approfondimento funzioni:
>
[dbops.fn_schema_in_scope](/dbzero/dbops/funzioni/fn_schema_in_scope)   
> [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope)   

---
### 🎯 Scopo Principale
(latest review 10-01-26)
La funzione **`dbops.fn_schema_match(p_rule_target, p_schema)`** è un **helper booleano** che verifica se uno schema specifico (`p_schema`) corrisponde al target di una regola (`p_rule_target`). Gestisce anche la keyword speciale `*all` per indicare corrispondenza universale.

---

### Parametri di input

| Parametro       | Tipo | Obbligatorio | Descrizione                                        |
| --------------- | ---- | :----------: | -------------------------------------------------- |
| `p_rule_target` | text |      ✔️       | Schema target della regola (può includere `*all`). |
| `p_schema`      | text |      ✔️       | Nome dello schema da verificare.                   |

---

### Valore di ritorno

`boolean` – `true` se `p_schema` corrisponde al target o se `p_rule_target='*all'`; altrimenti `false`.

---

### Flusso logico

1. Se `p_rule_target` è `NULL` → ritorna `false` (gestione difensiva).
2. Se `p_rule_target='*all'` (case insensitive) → ritorna `true`.
3. Altrimenti confronta `p_rule_target` e `p_schema` in modalità case insensitive.

---

### Casi d’uso tipici

* **Applicazione regole automazioni**: decidere se applicare una regola ad un determinato schema.
* **Wildcard globale**: usare `*all` per indicare che la regola è valida su qualsiasi schema.
* **Verifica singola**: quando serve un match diretto su uno schema specifico.

---

### Permessi e sicurezza

* Funzione **IMMUTABLE**, non dipende da cataloghi esterni.
* Sicura, priva di side‑effect.

---

### Esempi di utilizzo

* `SELECT dbops.fn_schema_match('anagrafiche', 'anagrafiche');` → `true`.
* `SELECT dbops.fn_schema_match('config', 'anagrafiche');` → `false`.
* `SELECT dbops.fn_schema_match('*all', 'vendite');` → `true`.

---

### Considerazioni

* È la versione più semplice e atomica rispetto a `fn_schema_in_scope` (che lavora su array).
* Spesso usata nelle `WHERE` dei cicli di automazione per decidere se includere parent/child schema di una FK.

---

### Benefici

* **Semplicità**: logica minimale e leggibile.
* **Affidabilità**: comportamento prevedibile con gestione difensiva di `NULL`.
* **Flessibilità**: supporta wildcard `*all`.

---

> **In sintesi**: `fn_schema_match` è un **helper elementare ma cruciale** per verificare in modo uniforme se uno schema soddisfa una regola di automazione, con supporto al caso speciale `*all`.
