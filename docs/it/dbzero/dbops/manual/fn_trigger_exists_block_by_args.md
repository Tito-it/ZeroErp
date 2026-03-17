## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_block_by_args`

> 👀 **Vedi anche**
>
Guide:
>
[Automazioni – Overview del Modulo](/guide/automazione-db/)
>
Approfondimento funzioni e trigger:
>
[dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)
> [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name)
> [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function)

---

### 🎯 Scopo Principale

(last review 31-12-25)
La funzione **`dbops.fn_trigger_exists_block_by_args(p_parent_rel, p_child_schema, p_child_table, p_fk_col)`** verifica l’esistenza di un **trigger di blocco** basato sulla funzione `trgfn_prevent_deactivate_if_children`, applicato ad una tabella padre per impedire la disattivazione se esistono righe figlio attive.

---

### Parametri di input

| Parametro        | Tipo     | Obbligatorio | Descrizione                                 |
| ---------------- | -------- | :----------: | ------------------------------------------- |
| `p_parent_rel`   | regclass |      ✔️       | Tabella padre su cui verificare il trigger. |
| `p_child_schema` | text     |      ✔️       | Schema della tabella figlia.                |
| `p_child_table`  | text     |      ✔️       | Nome della tabella figlia.                  |
| `p_fk_col`       | text     |      ✔️       | Nome della colonna FK nella tabella figlia. |

---

### Valore di ritorno

`boolean` – `true` se esiste un trigger con firma coerente alla configurazione attesa, `false` altrimenti.

---

### Flusso logico

1. Interroga `pg_trigger` filtrando solo i trigger **non interni** definiti sulla tabella padre (`p_parent_rel`).
2. Joina con `pg_proc` per identificare i trigger basati sulla funzione `trgfn_prevent_deactivate_if_children`.
3. Analizza la definizione del trigger (`pg_get_triggerdef`) cercando la stringa di chiamata con gli argomenti specificati (`p_child_schema`, `p_child_table`, `p_fk_col`).
4. Restituisce `true` se almeno un match è trovato.

---

### Casi d’uso tipici

* **Automazioni ATTIVO**: verificare se il trigger di protezione (padre con figli attivi) è già presente prima di crearne uno nuovo.
* **Idempotenza**: evitare duplicazioni di trigger quando si rilanciano le automazioni.
* **Audit/validazione**: produrre report sulla coerenza dei trigger rispetto alle FK configurate.

---

### Permessi e sicurezza

* Necessita permessi di lettura su `pg_trigger`, `pg_proc` e sull’oggetto tabella padre.
* È una funzione **STABLE**: non modifica dati o schema.

---

### Esempi di utilizzo

* `SELECT dbops.fn_trigger_exists_block_by_args('catalogo.articoli', 'vendite', 'righe_ordine', 'articolo_id');`
* `SELECT dbops.fn_trigger_exists_block_by_args('anagrafiche.clienti', 'fatture', 'testate', 'cliente_id');`

---

### Considerazioni

* La funzione si basa su un confronto testuale (`ILIKE`) della definizione trigger: robusta, ma potenzialmente sensibile a variazioni non standard di formattazione.
* È progettata come supporto alle automazioni: non deve essere usata per logica applicativa runtime.

---

### Benefici

* **Sicurezza**: assicura che i trigger di protezione non vengano duplicati.
* **Manutenibilità**: facilita report e controlli di coerenza.
* **Integrazione**: si integra nel framework di automazione ATTIVO.

---

> **In sintesi**: `fn_trigger_exists_block_by_args` è un utility che consente di verificare l’esistenza di un trigger di blocco tra tabelle padre e figlio, supportando le automazioni che applicano policy di consistenza sul campo `attivo`.
