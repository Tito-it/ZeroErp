## 📘 Documentazione Funzione –  `dbops.trgfn_prevent_deactivate_if_children`

---

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`dbops.trgfn_child_requires_active_parent`](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)
>
> Approfondimento tabelle:
>
> * [`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl)

---

### 🎯 Scopo Principale

*(last review 31-12-25)*
La funzione **`trgfn_prevent_deactivate_if_children`** è un **trigger function** che impedisce la disattivazione (`attivo = FALSE`) di un record padre se esistono ancora record figli associati tramite una FK. Garantisce integrità logica tra entità padre e figlio, preservando la coerenza dei dati.

---

### 📝 Dettagli

* **Firma**

  ```sql
  CREATE OR REPLACE FUNCTION dbops.trgfn_prevent_deactivate_if_children()
  RETURNS trigger
  LANGUAGE plpgsql
  ```

* **Parametri (TG_ARGV)**

  1. `child_schema` – schema della tabella figlia
  2. `child_table` – tabella figlia
  3. `fk_col` – colonna di FK che collega la tabella figlia alla PK della tabella padre

* **Logica interna**

  * Valida solo per operazioni `UPDATE`.
  * Se `OLD.attivo = TRUE` e `NEW.attivo = FALSE` → controllo blocca disattivazione.
  * Costruisce query dinamica per verificare la presenza di righe figlio correlate (`EXISTS`).
  * Se esistono record figli → solleva `RAISE EXCEPTION` con `ERRCODE 23503` (*foreign_key_violation*).

* **Ritorno**: `trigger` → `NEW` (se i controlli sono superati).

---

### 🔧 Utilizzo tipico

1. Evitare che un padre con figli attivi venga disattivato impropriamente.
2. Applicabile su entità di dominio con attributo booleano `attivo`.
3. Utile in scenari multi‑tabella (es. `gestori` → `soggetti`).

---

### 📊 Collegamento con automazione

* Inseribile tramite `automation_rules_tbl` come regola di consistenza.
* Complementare a `trgfn_child_requires_active_parent`: insieme rafforzano la gestione coerente dello stato `attivo`.

---

### 💡 Esempio pratico

Impedire la disattivazione di un record in `config.gestori` se esistono soggetti collegati:

```sql
CREATE TRIGGER trg_prevent_gestore_deactivate
BEFORE UPDATE ON config.gestori
FOR EACH ROW
EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(
  'anagrafiche',
  'soggetti',
  'gestore_id'
);
```

➡️ Se un `gestore` ha ancora `soggetti` collegati, l’operazione viene bloccata con errore.

---

> 🧠 **In sintesi**: `trgfn_prevent_deactivate_if_children` impedisce che un padre venga disattivato mentre esistono figli associati, rafforzando la coerenza dei dati e prevenendo stati incoerenti nel database.
