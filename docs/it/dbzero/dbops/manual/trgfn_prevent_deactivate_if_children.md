## 📘 Documentazione Funzione –  `dbops.trgfn_prevent_deactivate_if_children`

---

> 👀 **Vedi anche**
>
Approfondimento funzioni:
>
[`dbops.trgfn_child_requires_active_parent`](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)
>
Approfondimento tabelle:
>
[`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl)

---
### 🎯 Scopo Principale
*(last review 13-11-26)*
La funzione **`trgfn_prevent_deactivate_if_children`** è un **trigger function** che impedisce la disattivazione (`attivo = FALSE`) di un record padre se esistono record figli **attivi** associati tramite una FK. Se la tabella figlia **non** ha la colonna `attivo`, il blocco scatta alla semplice presenza di figli collegati. Garantisce integrità logica tra entità padre e figlio, preservando la coerenza dei dati.

---

### Dettagli

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
  4. *(opzionale)* `pk_col` – colonna PK del padre (default `id`)

* **Logica interna**

  * Valida solo per operazioni `UPDATE`.
  * Se `OLD.attivo = TRUE` e `NEW.attivo = FALSE` → controllo blocca disattivazione.
  * Se la tabella figlia ha una colonna `attivo` (con override), cerca **solo figli attivi** (`attivo IS DISTINCT FROM FALSE`).
  * Se la tabella figlia non ha `attivo`, verifica la semplice presenza di figli correlati (`EXISTS`).
  * Se esistono figli che soddisfano il criterio → solleva `RAISE EXCEPTION` con `ERRCODE 23503` (*foreign_key_violation*).

* **Ritorno**: `trigger` → `NEW` (se i controlli sono superati).

---

### Utilizzo tipico

1. Evitare che un padre con figli **attivi** venga disattivato impropriamente.
2. Applicabile su entità di dominio con attributo booleano `attivo`.
3. Utile in scenari multi‑tabella (es. `gestori` → `soggetti`).

---

### Collegamento con automazione

* Inseribile tramite `automation_rules_tbl` come regola di consistenza.
* Complementare a `trgfn_child_requires_active_parent`: insieme rafforzano la gestione coerente dello stato `attivo`.

---

### Esempio pratico

Impedire la disattivazione di un record in `config.gestori` se esistono soggetti **attivi** collegati (o qualsiasi soggetto se la tabella figlia non ha `attivo`):

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

➡️ Se un `gestore` ha ancora `soggetti` attivi collegati, l’operazione viene bloccata con errore.

---

> **In sintesi**: `trgfn_prevent_deactivate_if_children` impedisce che un padre venga disattivato mentre esistono figli **attivi** associati (o figli in generale se manca `attivo` sul figlio), rafforzando la coerenza dei dati e prevenendo stati incoerenti nel database.
