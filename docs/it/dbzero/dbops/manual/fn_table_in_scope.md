## 📘 Documentazione Concettuale – Funzione `dbops.fn_table_in_scope`

> 👀 **Vedi anche**
>
> Guide:
>
> * [Automazioni – Overview del Modulo](/dbzero/dbops/manual/automazioni_overview)
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope)   
>
> Approfondimento funzioni:
>
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope)   
> * [dbops.fn_schema_in_scope](/dbzero/dbops/funzioni/fn_schema_in_scope)   
> * [dbops.fn_schema_match](/dbzero/dbops/funzioni/fn_schema_match)   

---

### 🎯 Scopo Principale

(latest review 10-01-26)
La funzione **`dbops.fn_table_in_scope(p_schema, p_table)`** è un **helper di filtro tabellare** che determina se una specifica tabella appartiene allo scope di automazione, basandosi sulle regole definite in `dbops.automation_scope`. In questo modo, le automazioni possono applicarsi solo alle tabelle consentite.

---

### 🔍 Parametri di input

| Parametro  | Tipo | Obbligatorio | Descrizione                                    |
| ---------- | ---- | :----------: | ---------------------------------------------- |
| `p_schema` | text |      ✔️       | Nome dello schema della tabella da verificare. |
| `p_table`  | text |      ✔️       | Nome della tabella da verificare.              |

---

## 📤 Valore di ritorno

`boolean` – `true` se la tabella rientra nello scope secondo le regole in `automation_scope`, `false` altrimenti.

---

### ⚙️ Flusso logico

1. **Assenza tabella `automation_scope`** → ritorna `true` (nessun filtro attivo).
2. **Tabella `automation_scope` vuota** → ritorna `true` (nessun filtro attivo).
3. **Righe per schema specifico**:

   * Se **nessuna riga per lo schema** → tutte le tabelle dello schema sono in scope.
   * Se presente almeno una riga con `table_like='*all'` → tutte le tabelle dello schema sono in scope.
   * Altrimenti → valuta se `p_table` corrisponde a `table_like` usando `LIKE`.
4. Ritorna `true` solo se esiste almeno un match.

---

## 🧩 Casi d’uso tipici

* **Filtrare automazioni**: applicare trigger e policy solo su tabelle ammesse.
* **Gestione granularità**: permettere di definire scope per schema intero (`*all`) o singole tabelle/pattern.
* **Test selettivi**: limitare le automazioni a un sottoinsieme di tabelle in ambiente di sviluppo.

---

###🛡️ Permessi e sicurezza

* Richiede accesso in lettura alla tabella `dbops.automation_scope`.
* È una funzione **STABLE**, senza effetti collaterali sui dati.

---

### 🚀 Esempi di utilizzo

* `SELECT dbops.fn_table_in_scope('anagrafiche','clienti');` → `true` se la regola lo consente.
* `SELECT dbops.fn_table_in_scope('config','valute');` → `true/false` secondo le regole impostate.
* `SELECT dbops.fn_table_in_scope('vendite','*');` → utile con `table_like='*all'`.

---

### 📌 Considerazioni

* La funzione centralizza la logica di inclusione/esclusione a livello tabellare.
* L’uso di `LIKE` permette di definire pattern (`pref%`, `%log`).
* Garantisce che le automazioni rispettino sempre i confini definiti in `automation_scope`.

---

### ✅ Benefici

* **Controllo granulare**: consente regole precise fino al livello di singola tabella.
* **Coerenza**: unica fonte autorevole per la logica di inclusione.
* **Flessibilità**: supporto wildcard e fallback sensati.

---

> 🧠 **In sintesi**: `fn_table_in_scope` è l’helper che assicura che ogni automazione venga applicata **solo alle tabelle autorizzate**, rispettando le regole di `automation_scope` e permettendo configurazioni granulari o globali.
