## 📘 Documentazione Funzione –  `dbops.trgfn_soft_delete_cascade`

---

> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [`dbops.trgfn_prevent_deactivate_if_children`](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)
> * [`dbops.trgfn_child_requires_active_parent`](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)
>
> Approfondimento tabelle:
>
> * [`dbops.error_log`](/dbzero/dbops/tabelle/error_log)

---

### 🎯 Scopo Principale

La funzione **`trgfn_soft_delete_cascade`** è un **trigger function** che implementa la logica di **soft-delete a cascata**: quando un record padre viene disattivato (`attivo = FALSE`), tutti i record figli correlati vengono automaticamente disattivati.

---

### 📝 Dettagli

* **Firma**

  ```sql
  CREATE OR REPLACE FUNCTION dbops.trgfn_soft_delete_cascade()
  RETURNS trigger
  LANGUAGE plpgsql
  ```

* **Parametri (TG_ARGV)**

  1. `child_schema` – schema della tabella figlia
  2. `child_table` – tabella figlia
  3. `fk_col` – colonna di FK verso il padre
  4. `[pk_col]` – colonna PK del padre (default = `id`)

* **Logica interna**

  * Controlla operazioni `UPDATE` dove `OLD.attivo = TRUE` e `NEW.attivo = FALSE`.
  * Estrae il valore della PK del padre da `OLD`.
  * Se la PK è nulla → log warning (`fn_log_error_only`) e termina senza aggiornare figli.
  * Aggiorna i record figli eseguendo:

    ```sql
    UPDATE <child_schema>.<child_table>
    SET attivo = FALSE
    WHERE <fk_col> = parent_pk_val;
    ```
  * Gestione errori: in caso di errore durante l’`UPDATE`, viene richiamata `fn_log_and_raise_error` con dettagli su SQLSTATE, messaggio ed istruzione generata.

* **Ritorno**: `trigger` → `NEW` (record padre aggiornato).

---

### 🔧 Utilizzo tipico

1. **Soft-delete cascata** in gerarchie (es. cliente → contratti, gestore → soggetti).
2. Riduzione della necessità di cancellazioni fisiche: lo stato `attivo` governa la visibilità.
3. Automazione della consistenza: nessun figlio resta attivo se il padre viene disattivato.

---

### 📊 Collegamento con automazione

* Può essere generata automaticamente tramite `automation_rules_tbl`.
* Integra il sistema di **logging/error handling** standard (`error_log`).
* Complementa altri trigger come `trgfn_prevent_deactivate_if_children` e `trgfn_child_requires_active_parent`.

---

### 💡 Esempio pratico

Applicare soft-delete a cascata da `config.gestori` verso `anagrafiche.soggetti`:

```sql
CREATE TRIGGER trg_soft_delete_cascade_gestore
BEFORE UPDATE ON config.gestori
FOR EACH ROW
EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade(
  'anagrafiche',
  'soggetti',
  'gestore_id'
);
```

➡️ Quando un `gestore` viene disattivato (`attivo=false`), anche tutti i `soggetti` collegati con `gestore_id` vengono automaticamente marcati come non attivi.

---

> 🧠 **In sintesi**: `trgfn_soft_delete_cascade` realizza una **soft-delete automatica a cascata**, semplificando la gestione della gerarchia padre-figlio e garantendo coerenza dei dati senza cancellazioni fisiche.
