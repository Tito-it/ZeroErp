 ## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_require_by_args`

> 👀 **Vedi anche**
>
Guide:
>
[Automazioni – Overview del Modulo](/guide/automazione-db)
>
Approfondimento funzioni e trigger correlati:
>
[dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)
> [dbops.fn_trigger_exists_cascade_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_cascade_by_args)
> [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args)
> [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name)
> [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function)


---
### 🎯 Scopo Principale
La funzione **`dbops.fn_trigger_exists_require_by_args(p_child_rel, p_parent_schema, p_parent_table, p_parent_attivo_col, p_fk_col)`** verifica l’esistenza, sulla **tabella figlia**, di un **constraint trigger deferrable** basato sulla funzione `trgfn_child_requires_active_parent`, parametrizzato con schema/tabella padre, colonna `attivo` del padre e colonna FK del figlio. Serve a garantire idempotenza nelle automazioni della policy **ATTIVO → REQUIRE**.

---

### Parametri di input

| Parametro             | Tipo     | Obbligatorio | Descrizione                                                      |
| --------------------- | -------- | :----------: | ---------------------------------------------------------------- |
| `p_child_rel`         | regclass |      ✔️       | Tabella figlia su cui verificare il trigger.                     |
| `p_parent_schema`     | text     |      ✔️       | Schema della tabella padre.                                      |
| `p_parent_table`      | text     |      ✔️       | Nome della tabella padre.                                        |
| `p_parent_attivo_col` | text     |      ✔️       | Nome della **colonna `attivo`** nella tabella padre.             |
| `p_fk_col`            | text     |      ✔️       | Nome della colonna FK nella tabella figlia che rimanda al padre. |

---

### Valore di ritorno

`boolean` – `true` se esiste un trigger non interno sulla tabella figlia che invoca `dbops.trgfn_child_requires_active_parent(...)` con **esatti argomenti**; `false` altrimenti.

---

### Flusso logico

1. Legge da `pg_trigger` i trigger definiti su `p_child_rel` ed esclude quelli **interni**.
2. Joina `pg_proc` per selezionare quelli che chiamano la funzione `trgfn_child_requires_active_parent`.
3. Usa `pg_get_triggerdef(t.oid)` con `ILIKE` + `format(...)` per verificare che la chiamata riporti **esattamente** `p_parent_schema`, `p_parent_table`, `p_parent_attivo_col`, `p_fk_col`.
4. Restituisce `EXISTS(...)` come booleano.

---

### Casi d’uso tipici

* **Automazioni ATTIVO – REQUIRE**: prima di creare il constraint trigger, controllare se è già presente con i parametri attesi.
* **Idempotenza**: evitare duplicazioni quando si rieseguono automazioni su più schemi/tabelloni.
* **Audit di consistenza**: generare report sulla corretta presenza dei trigger `REQUIRE` per ciascuna FK.

---

### Permessi e sicurezza

* Richiede permessi di lettura su `pg_trigger` e `pg_proc`.
* Funzione **STABLE**: non modifica schema o dati.

---

### Esempi di utilizzo

* `SELECT dbops.fn_trigger_exists_require_by_args('vendite.righe_ordine','catalogo','articoli','attivo','articolo_id');`
* `SELECT dbops.fn_trigger_exists_require_by_args('fatture.testate','anagrafiche','clienti','attivo','cliente_id');`

---

### Considerazioni

* Il match si basa sulla **stringa della definizione** del trigger: robusto ma sensibile a formattazioni non canoniche.
* Complementare a `fn_trigger_exists_by_name`/`by_function` per strategie `BY_NAME|BY_FUNCTION|BOTH` e alle verifiche `BLOCK`/`CASCADE`.

---

### Benefici

* **Sicurezza operativa**: impedisce creazioni duplicate del trigger `REQUIRE`.
* **Manutenibilità**: facilita controlli e report sugli schemi complessi.
* **Integrazione**: progettata per il modulo automazioni **ATTIVO** con gestione `REQUIRE` dei figli.

---

> **In sintesi**: `fn_trigger_exists_require_by_args` è l’utility di verifica per i trigger **constraint** `REQUIRE` sul figlio, indispensabile per mantenere idempotenza e coerenza nelle automazioni del campo `attivo`.
