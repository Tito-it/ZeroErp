## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_by_name`

> 👀 **Vedi anche**
>
Guide:
>
[Automazioni – Overview del Modulo](/guide/automazione-db/)
>
Approfondimento funzioni:
>
[dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function)   
> [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args)   
>
🎯 Scopo Principale

(latest review 10-01-26)
La funzione **`dbops.fn_trigger_exists_by_name(p_rel, p_trigger_name)`** verifica l’esistenza di un **trigger non interno** su una tabella specifica **in base al nome** del trigger.

---

## Parametri di input

| Parametro        | Tipo     | Obbligatorio | Descrizione                                        |
| ---------------- | -------- | :----------: | -------------------------------------------------- |
| `p_rel`          | regclass |      ✔️       | Tabella (relazione) su cui controllare il trigger. |
| `p_trigger_name` | text     |      ✔️       | Nome del trigger da verificare.                    |

---

### Valore di ritorno

`boolean` – `true` se esiste un trigger con quel nome su `p_rel` (ed è **non interno**), `false` altrimenti.

---

### Flusso logico

1. Interroga `pg_trigger` filtrando per `tgrelid = p_rel` e `tgname = p_trigger_name`.
2. Esclude i trigger **interni** (`NOT t.tgisinternal`).
3. Ritorna `EXISTS(...)` come booleano.

---

### Casi d’uso tipici

* **Idempotenza nelle automazioni**: verificare se un trigger con uno **specifico nome** è già presente prima di crearlo.
* **Verifica naming policy**: audit della coerenza dei nomi dei trigger rispetto a `name_template`.
* **Manutenzione**: controlli rapidi durante migrazioni o refactoring.

---

### Permessi e sicurezza

* Richiede permessi di lettura su `pg_trigger`.
* È una funzione **STABLE** e non altera dati o schema.

---

### Esempi di utilizzo

* `SELECT dbops.fn_trigger_exists_by_name('anagrafiche.clienti','trg_clienti_ins_upd_gen_tx_id');`
* `SELECT dbops.fn_trigger_exists_by_name('catalogo.articoli','trg_articoli_a10_componenti_block_deact_upd');`

---

### Considerazioni

* Sensibile al **nome esatto** del trigger: se il naming non è standard, può fallire il match pur esistendo un trigger equivalente.
* Da usare in combinazione con `fn_trigger_exists_by_function` per una verifica più robusta.

---

### Benefici

* **Semplicità**: controllo diretto e veloce per nome.
* **Integrazione**: si combina con altre utility di esistenza per strategie `BY_NAME|BY_FUNCTION|BOTH`.
* **Affidabilità**: evita duplicazioni quando il naming è normato.

---

> **In sintesi**: `fn_trigger_exists_by_name` è l’utility più immediata per verificare la presenza di un trigger identificato dal **nome**, ideale per automazioni basate su naming template standardizzati.
