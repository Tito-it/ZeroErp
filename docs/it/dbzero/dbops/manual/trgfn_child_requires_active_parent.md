## 📘 Documentazione Funzione – `dbops.trgfn_child_requires_active_parent`

---

> 👀 **Vedi anche**
>
Approfondimento funzioni:
>
[`dbops.trgfn_prevent_deactivate_if_children`](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)
>
Approfondimento tabelle:
>
[`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl)

---
### 🎯 Scopo Principale
*(last review 13-11-26)*
La funzione **`trgfn_child_requires_active_parent`** è una **trigger function** che impedisce l’inserimento o l’aggiornamento di un record figlio quando il **padre collegato non è attivo**. Se la tabella figlia ha una colonna `attivo`, il controllo si applica **solo quando il figlio è attivo**.

---

### Dettagli

* **Firma**

  ```sql
  CREATE OR REPLACE FUNCTION dbops.trgfn_child_requires_active_parent()
  RETURNS trigger
  LANGUAGE plpgsql
  ```

* **Parametri (TG_ARGV)**

  1. `parent_schema` – schema della tabella padre
  2. `parent_table` – tabella padre
  3. `parent_attivo_col` – nome colonna `attivo` del padre (con override)
  4. `fk_col` – colonna FK del figlio verso il padre
  5. *(opzionale)* `parent_pk_col` – PK del padre (default `id`)

* **Logica interna**

  * Valida per `INSERT` e `UPDATE`.
  * Se il figlio ha `attivo`, il controllo vale **solo** quando `NEW.attivo = TRUE`.
  * Se la FK è `NULL` il controllo sul padre viene **bypassato** (FK opzionale).
  * Verifica che il padre esista e che `parent_attivo_col = TRUE`.
  * Se il padre non esiste o è disattivo → errore.

* **Ritorno**: `trigger` → `NEW` (se i controlli sono superati).

---

### Utilizzo tipico

Impedire che un record figlio punti a un padre disattivo:

```sql
CREATE CONSTRAINT TRIGGER trg_figlio_a10_padre_require_attivo_ins_upd
AFTER INSERT OR UPDATE OF fk_col
ON schema_figlio.tabella_figlio
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(
  'schema_padre',
  'tabella_padre',
  'attivo',
  'fk_col'
);
```

---

### Collegamento con automazione

* Viene generata da `dbops.fn_run_automations_attivo` come **trigger REQUIRE** sul figlio.
* Naming standard: `trg_{child}_a10_{parent}_require_attivo_ins_upd`.

---

> **In sintesi**: `trgfn_child_requires_active_parent` garantisce che un figlio **attivo** possa puntare **solo** a un padre attivo, rafforzando la coerenza tra relazioni padre‑figlio.
