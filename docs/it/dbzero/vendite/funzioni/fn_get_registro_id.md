{% include-markdown "it/dbzero/vendite/manual/fn_get_registro_id.md" %}
# ⚙️ Funzione `fn_get_registro_id`

```sql
CREATE FUNCTION fn_get_registro_id(p_tipo_doc_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_registro_id(p_tipo_doc_fiscale_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_registro_id vendite.registri_fatturazione.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve il registro dal mapping tipo_doc_fiscale -> registro.
  --
  -- Regole:
  --   1) vendite.tipi_doc_fiscale_registri
  --   2) errore
  -- =========================================================

  IF p_tipo_doc_fiscale_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_registro_id', 'E_GENERICO',
      jsonb_build_object('detail','tipo_doc_fiscale_id obbligatorio'),
      NULL::uuid,
      'tipo_doc_fiscale_id obbligatorio'
    );
  END IF;

  SELECT m.registro_id
    INTO v_registro_id
    FROM vendite.tipi_doc_fiscale_registri m
   WHERE m.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id;

  IF v_registro_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_registro_id', 'E_GENERICO',
      jsonb_build_object(
        'detail','Registro non risolto (tipo_doc_fiscale)',
        'tipo_doc_fiscale_id', p_tipo_doc_fiscale_id
      ),
      NULL::uuid,
      'Registro non risolto (tipo_doc_fiscale)'
    );
  END IF;

  RETURN v_registro_id;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
