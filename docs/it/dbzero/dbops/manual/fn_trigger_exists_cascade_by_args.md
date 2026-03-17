# 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_cascade_by_args`

> 👀 **Vedi anche**
>
Guide:
>
[Automazioni – Overview del Modulo](/guide/automazione-db)
>
Approfondimeti funzioni e trigger:
>
[dbops.trgfn_soft_delete_cascade](/dbzero/dbops/funzioni/trgfn_soft_delete_cascade)
> [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args)
> [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name)
> [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function)

---

### 🎯 Scopo Principale

La funzione **`dbops.fn_trigger_exists_cascade_by_args(p_parent_rel, p_child_schema, p_child_table, p_fk_col)`** verifica l’esistenza di un **trigger di cascata** basato sulla funzione `trgfn_soft_delete_cascade`, definito sulla tabella padre e parametrizzato con *schema*, *tabella figlia* e *colonna FK* specifici.

---

### Parametri di input

| Parametro        | Tipo     | Obbligatorio | Descrizione                                               |
| ---------------- | -------- | :----------: | --------------------------------------------------------- |
| `p_parent_rel`   | regclass |      ✔️       | Nome completo della tabella padre (es. `schema.tabella`). |
| `p_child_schema` | text     |      ✔️       | Schema della tabella figlia.                              |
| `p_child_table`  | text     |      ✔️       | Nome della tabella figlia.                                |
| `p_fk_col`       | text     |      ✔️       | Nome della colonna FK nella tabella figlia.               |

---

### Valore di ritorno

`boolean` – `true` se esiste un trigger non interno sulla tabella padre che invoca `dbops.trgfn_soft_delete_cascade(p_child_schema, p_child_table, p_fk_col)`, `false` altrimenti.

---

### Flusso logico

1. Interroga `pg_trigger` per i trigger definiti su `p_parent_rel`, escludendo quelli **interni** (`NOT t.tgisinternal`).
2. Joina con `pg_proc` per selezionare quelli che chiamano la funzione `trgfn_soft_delete_cascade`.
3. Verifica che la **definizione del trigger** (`pg_get_triggerdef(t.oid)`) contenga la chiamata con gli **argomenti attesi** (schema, tabella figlia, colonna FK) usando `ILIKE` + `format(...)`.
4. Ritorna `EXISTS(...)` come booleano.

---

### Casi d’uso tipici

* **Automazioni ATTIVO – CASCATA**: prima di creare il trigger di cascata, verificare se è già presente con esatti argomenti.
* **Idempotenza**: prevenire duplicazioni quando si rilanciano automazioni su più schemi/tabelle.
* **Audit di configurazione**: controllo di coerenza rispetto alle FK effettive.

---

### Permessi e sicurezza

* Richiede privilegi di lettura su cataloghi `pg_trigger`, `pg_proc`.
* Funzione **STABLE**, senza effetti collaterali su dati o schema.

---

### Esempi di utilizzo

* `SELECT dbops.fn_trigger_exists_cascade_by_args('catalogo.articoli','vendite','righe_ordine','articolo_id');`
* `SELECT dbops.fn_trigger_exists_cascade_by_args('anagrafiche.clienti','fatture','testate','cliente_id');`

---

### Considerazioni

* Il match avviene su **stringa** della definizione trigger: robusto ma sensibile a varianti non canoniche di formattazione.
* Complementare a `fn_trigger_exists_by_name`/`by_function` per strategie `BY_NAME|BY_FUNCTION|BOTH`.

---

### Benefici

* **Sicurezza operativa**: evita la creazione multipla dello stesso trigger parametrico.
* **Manutenibilità**: facilita verifiche e reportistica sulle policy di soft‑delete a cascata.
* **Integrazione**: pensata per il modulo automazioni **ATTIVO**.

---

> **In sintesi**: `fn_trigger_exists_cascade_by_args` è l’utility che consente di verificare, in modo preciso e parametrizzato, la presenza del trigger di **soft‑delete a cascata** tra padre e figlio.
