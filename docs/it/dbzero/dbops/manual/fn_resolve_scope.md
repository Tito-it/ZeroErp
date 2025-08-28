## 📘 Documentazione Concettuale – Funzione `dbops.fn_resolve_scope`

> 👀 **Vedi anche**
>
> Approfondimeto tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)
>
> Approfondimento funzioni :
>
> * [dbops.fn_schema_in_scope](/dbzero/dbops/funzioni/fn_schema_in_scope)
> * [dbops.fn_schema_match](/dbzero/dbops/funzioni/fn_schema_match)
>
> Guide:
>
> * [Automatione DB](/guide/automazione-db)

---

### 🎯 Scopo Principale

La funzione **`dbops.fn_resolve_scope(p_schemas text[])`** restituisce la lista effettiva di schemi da considerare come *scope* per l’esecuzione delle automazioni. Serve a normalizzare e centralizzare la logica di determinazione dello scope operativo, evitando duplicazioni e incoerenze.

---

### 🔍 Parametri di input

| Parametro   | Tipo    | Obbligatorio | Descrizione                                                                                               |
| ----------- | ------- | :----------: | --------------------------------------------------------------------------------------------------------- |
| `p_schemas` | text\[] |       ❌      | Lista opzionale di schemi. Se assente o vuota, la funzione ricorre a fonti alternative di configurazione. |

---

### 📤 Valore di ritorno

`text[]` – Array di schemi effettivamente in scope, già puliti e normalizzati.

---

### ⚙️ Flusso logico

1. **Input esplicito**: se `p_schemas` è valorizzato, la funzione rimuove spazi, valori nulli o vuoti, ed esclude la keyword `*all`. Se rimane una lista valida, la ritorna direttamente.
2. **Configurazione persistente**: se non c’è input valido, prova a leggere dalla tabella `dbops.automation_scope` (se presente).
3. **Fallback automatico**: se la tabella è vuota o non esiste, ritorna tutti gli schemi “utente” (escludendo `pg_%`, `information_schema`, `storico`).

---

### 🧩 Casi d’uso tipici

* **Automazioni batch**: risolvere quali schemi analizzare in base a input espliciti o configurazioni centrali.
* **Test/Dev vs Prod**: gestire scope diversi (es. su ambienti di test si può limitare lo scope a schemi specifici).
* **Fallback universale**: garantire che in assenza di configurazioni esplicite, venga comunque restituito un insieme sensato di schemi.

---

### 🛡️ Permessi e sicurezza

* Necessita di accesso in lettura ai cataloghi di sistema (`pg_namespace`) e, se presente, alla tabella `dbops.automation_scope`.
* È **read-only**: non modifica né metadati né dati applicativi.

---

### 🚀 Esempi di utilizzo

* Chiamata diretta con parametro: `fn_resolve_scope(ARRAY['anagrafiche','config'])` → restituisce solo i due schemi indicati.
* Chiamata senza parametro: `fn_resolve_scope(NULL)` → legge da `automation_scope` oppure restituisce tutti gli schemi utente.
* Automazione generica: uno script che deve analizzare FK o naming policy invoca questa funzione per sapere quali schemi considerare.

---

### 📌 Considerazioni

* L’uso della keyword `*all` come placeholder viene filtrato: chiama esplicitamente la logica di fallback.
* La funzione garantisce un comportamento consistente anche se `automation_scope` non è popolata o non esiste.
* È pensata come funzione “foundation” richiamata da altre utilità (`fn_schema_in_scope`, `fn_run_automations`).

---

### ✅ Benefici

* **Centralizzazione**: logica di determinazione scope in un solo punto.
* **Robustezza**: fallback garantiti in assenza di configurazioni.
* **Flessibilità**: supporta input espliciti, configurazioni persistenti e fallback automatici.

---

> 🧠 **In sintesi**: `fn_resolve_scope` è la funzione che permette a tutte le automazioni di capire **quali schemi considerare**, adattandosi in modo dinamico al contesto e riducendo rischi di configurazioni incoerenti.
