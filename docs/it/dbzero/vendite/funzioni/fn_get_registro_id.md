{% include-markdown "it/dbzero/vendite/manual/fn_get_registro_id.md" %}
# ⚙️ Funzione `fn_get_registro_id`

```sql
CREATE FUNCTION fn_get_registro_id(p_sorgente_tipo_id bigint, p_utility_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_registro_id(p_sorgente_tipo_id bigint, p_utility_id integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_registro_id vendite.registri_fatturazione.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve il registro di fatturazione con priorita' su:
  --   1) config.sorgenti.registro_id
  --   2) config.utilities.registro_id
  --   3) errore se ancora NULL
  -- =========================================================

  IF p_sorgente_tipo_id IS NOT NULL THEN
    SELECT s.registro_id
      INTO v_registro_id
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id;
  END IF;

  IF v_registro_id IS NULL AND p_utility_id IS NOT NULL THEN
    SELECT u.registro_id
      INTO v_registro_id
      FROM config.utilities u
     WHERE u.id = p_utility_id;
  END IF;

  IF v_registro_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_get_registro_id',
      'E_GENERICO',
      jsonb_build_object(
        'detail','Registro non risolto (sorgente/utility)',
        'sorgente_tipo_id', p_sorgente_tipo_id,
        'utility_id', p_utility_id
      ),
      NULL::uuid,
      concat('Registro non risolto (sorgente/utility)', 
      ' sorgente_tipo_id ', p_sorgente_tipo_id::text,
        ', utility_id ', p_utility_id::text
       )
    );
  END IF;

  RETURN v_registro_id;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
