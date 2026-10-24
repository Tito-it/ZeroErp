{% include-markdown "it/dbzero/dbops/manual/fn_generate_tx_id.md" %}
# ⚙️ Funzione `fn_generate_tx_id`

```sql
CREATE FUNCTION fn_generate_tx_id(p_generating_function text, p_session_info jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_generate_tx_id(p_generating_function text, p_session_info jsonb DEFAULT '{}'::jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
  DECLARE

      v_tx dbops.transaction_ids.id%TYPE := uuidv7();
  BEGIN

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

COMMENT ON FUNCTION dbops.fn_generate_tx_id(p_generating_function text, p_session_info jsonb)
IS 'Genera un nuovo tx_id UUID, lo inserisce in dbops.transaction_ids con generating_function e session_info, e lo restituisce. SECURITY DEFINER di postgres: dal 2026-09-12 (D6) con search_path pinnato a pg_catalog, public, pg_temp — il pin sta nella definizione, un CREATE OR REPLACE che lo dimentica lo azzera.';
```

</div>

---
{% include-markdown "signature-core.md" %}
