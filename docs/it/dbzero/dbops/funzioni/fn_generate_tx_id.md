{% include-markdown "it/dbzero/dbops/manual/fn_generate_tx_id.md" %}
# ⚙️ Funzione `fn_generate_tx_id`

### 🎯 Scopo Principale
* **Unico punto di generazione**
  Evitare duplicazioni di logica ed errori creando sempre il `tx_id` tramite una function dedicata.
* **Contestualizzazione**
  Conservare il nome della funzione applicativa (`generating_function`) e dati di sessione JSON (
  `session_info`), per migliorare la tracciabilità.
* **Sicurezza**
  Impostando `SECURITY DEFINER`, la function può essere invocata da ruoli meno privilegiati mantenendo i permessi di inserimento.

---

```sql
CREATE FUNCTION fn_generate_tx_id(p_generating_function text, p_session_info jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_generate_tx_id(p_generating_function text, p_session_info jsonb DEFAULT '{}'::jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_tx UUID := gen_random_uuid();
BEGIN
    -- Genera un nuovo UUID e lo inserisce in dbops.transaction_ids
    INSERT INTO dbops.transaction_ids (
        id,
        generating_function,
        session_info
    ) VALUES (
        v_tx,
        p_generating_function,
        p_session_info
    );

    RETURN v_tx;
END;
$function$
```