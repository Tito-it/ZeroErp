## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_by_function`

> 👀 **Vedi anche**
>
Guide:
>
[Automazioni – Overview del Modulo](/guide/automazione-db/)
>
Approfondimento funzioni:
>
[dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name)
> [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args)

---
### 🎯 Scopo Principale
(latest review 10-01-26)
La funzione **`dbops.fn_trigger_exists_by_function(p_rel, p_fn_schema, p_fn_name)`** verifica l’esistenza di un trigger su una tabella specifica, identificandolo in base alla **funzione associata**. È pensata come utility per le automazioni, per evitare la duplicazione di trigger già creati.

---

### Parametri di input

| Parametro     | Tipo     | Obbligatorio | Descrizione                                    |
| ------------- | -------- | :----------: | ---------------------------------------------- |
| `p_rel`       | regclass |      ✔️       | Tabella (relazione) su cui cercare il trigger. |
| `p_fn_schema` | text     |      ✔️       | Schema della funzione eseguita dal trigger.    |
| `p_fn_name`   | text     |      ✔️       | Nome della funzione eseguita dal trigger.      |

---

### Valore di ritorno

`boolean` – `true` se esiste almeno un trigger attivo sulla tabella che invoca la funzione specificata, `false` altrimenti.

---

### Flusso logico

1. Interroga `pg_trigger` per i trigger definiti sulla tabella `p_rel`.
2. Joina `pg_proc` e `pg_namespace` per verificare che la funzione associata corrisponda a `p_fn_schema.p_fn_name`.
3. Esclude i trigger **interni** (`NOT t.tgisinternal`).
4. Restituisce `true` se viene trovato almeno un match.

---

### Casi d’uso tipici

* **Automazioni TX_ID/AUDIT/ATTIVO**: verificare l’esistenza di trigger già associati a funzioni standard (es. `trgfn_tx_id_managed`).
* **Idempotenza**: evitare creazione ridondante di trigger durante l’orchestrazione di `fn_run_automations`.
* **Validazione**: audit della coerenza tra regole definite e trigger effettivamente presenti.

---

### Permessi e sicurezza

* Richiede accesso in lettura a `pg_trigger`, `pg_proc`, `pg_namespace`.
* Funzione **STABLE**, priva di effetti collaterali.

---

### Esempi di utilizzo

* `SELECT dbops.fn_trigger_exists_by_function('anagrafiche.clienti','dbops','trgfn_tx_id_managed');`
* `SELECT dbops.fn_trigger_exists_by_function('vendite.fatture','script','trgfn_audit_data_user_generic');`

---

### Considerazioni

* Controllo basato su **funzione**, non sul nome del trigger: utile in contesti con naming legacy.
* Può restituire `true` anche se il nome del trigger differisce, purché la funzione coincida.

---

### Benefici

* **Affidabilità**: rileva l’esistenza reale di trigger funzionali, indipendentemente dal naming.
* **Flessibilità**: utile quando il naming non è standardizzato ma le funzioni sono note.
* **Integrazione**: pensata per lavorare in tandem con `fn_trigger_exists_by_name`.

---

> **In sintesi**: `fn_trigger_exists_by_function` è un’utility per verificare la presenza di trigger basati su una determinata funzione, assicurando idempotenza e consistenza nell’applicazione delle automazioni.
