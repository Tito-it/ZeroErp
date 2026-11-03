## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_automazione_overlap`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)
>
Approfondimento tabelle:    
> [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap)    
>
Approfondimento funzioni:
> [dbops.fn_seed_automazione_overlap](/dbzero/dbops/funzioni/fn_seed_automazione_overlap)    
>
### 🎯 Scopo Principale
(latest review 02-06-26)
La funzione **`dbops.fn_apply_automazione_overlap(p_exec_mode, p_dry_run)`** applica
i vincoli `EXCLUDE USING gist` alle tabelle marcate `active=true` in
`dbops.automazione_overlap`. Dalla rev 2026-06-02 supporta anche vincoli
**parziali** (con clausola `WHERE`) tramite la colonna `where_predicate`.

---

### Parametri di input

| Parametro     | Tipo    | Descrizione                                  |
| ------------- | ------- | -------------------------------------------- |
| `p_exec_mode` | text    | Modalita' di esecuzione (AUTO/CI/SCHEDULED). |
| `p_dry_run`   | boolean | Se true non crea vincoli.                    |

---

### Logica operativa (sintesi)

1. Legge le righe `active=true` compatibili con `exec_mode`.
2. Salta, con il motivo `TABLE_NOT_FOUND` nell'audit, una riga che punta a una tabella che non
   esiste piu': il registro non ha una FK verso il catalogo, e una riga rimasta indietro non
   ferma il giro per le altre tabelle.
3. Verifica esistenza colonne chiave e colonne periodo.
4. Salta la tabella se trova gia' un `EXCLUDE` sulla colonna periodo o un temporal
   `UNIQUE ... WITHOUT OVERLAPS`.
5. Crea il vincolo `EXCLUDE` usando:
   * `key_columns` (colonne semplici, validate e quotate) con `WITH =`;
   * `key_expressions` (chiavi su espressione, es. `COALESCE(classe,-1)`, iniettate
     as-is) con `WITH =`, appese alle colonne;
   * `daterange(valido_dal, COALESCE(valido_al,'infinity'), bounds) WITH &&`;
   * se `where_predicate` e' valorizzato, aggiunge la coda `WHERE (<predicate>)`
     (vincolo **parziale**); se `NULL`, vincolo **totale** (comportamento storico).

---

### Vincoli parziali (`where_predicate`)

Per imporre "niente sovrapposizioni **solo tra le righe attive**" si valorizza
`where_predicate` con un'espressione booleana, es. `attivo IS TRUE`,
`NOT is_abortito_snapshot`, `stato = 'ATTIVA'`. La funzione produce:

```sql
ALTER TABLE schema.tabella
    ADD CONSTRAINT ex_tabella_no_overlap
    EXCLUDE USING gist (chiave WITH =, <range> WITH &&)
    WHERE (<where_predicate>);
```

> ⚠️ `where_predicate` e' un **frammento DDL di fiducia** (espressione iniettata
> as-is, non quotabile): va impostato **solo da un DBA**, mai da input applicativo.

---

### Esempi

**Applicazione reale:**

```sql
SELECT dbops.fn_apply_automazione_overlap('AUTO', false);
```

**Dry-run:**

```sql
SELECT dbops.fn_apply_automazione_overlap('AUTO', true);
```

---

### Note

* Serve almeno una chiave: se `key_columns` **e** `key_expressions` sono entrambe
  vuote, il vincolo non viene creato.
* `key_columns` = **colonne semplici** (validate, quotate); `key_expressions` =
  **espressioni** (es. `COALESCE(classe_utenza_id,-1)`), iniettate as-is (DDL di
  fiducia DBA-only). Le due liste si combinano nella chiave del constraint.
* `range_bounds` default `[]` (inclusivo).
* Per chiavi UUID e' richiesto `btree_gist`.
* **Idempotente:** salta se esiste gia' un `EXCLUDE` sulla colonna periodo (o un
  temporal `UNIQUE WITHOUT OVERLAPS`). Per **cambiare** un `where_predicate` serve
  prima il `DROP CONSTRAINT` manuale: la funzione non esegue `ALTER`.

---

{% include-markdown "signature-core.md" %}

---
