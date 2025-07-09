{% include-markdown "it/dbzero/script/manual/trgfn_upd_audit_data_user_generic.md" %}
# ⚙️ Funzione `trgfn_upd_audit_data_user_generic`

### 🎯 Scopo Principale
* **Audit automatico**
  Assicurare che ogni modifica a una riga di tabella sia registrata con timestamp (`data_update`) e utente (`user_update`) correnti.
* **Centralizzare la logica di update audit**
  Evitare di replicare manualmente la medesima assegnazione in ogni trigger `BEFORE UPDATE` delle varie tabelle.

---

```sql
CREATE FUNCTION trgfn_upd_audit_data_user_generic()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_upd_audit_data_user_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.data_update := CURRENT_TIMESTAMP;
  NEW.user_update := CURRENT_USER;
  RETURN NEW;
END;
$function$
```