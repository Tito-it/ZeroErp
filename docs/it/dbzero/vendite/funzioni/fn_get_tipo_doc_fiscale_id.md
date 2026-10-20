{% include-markdown "it/dbzero/vendite/manual/fn_get_tipo_doc_fiscale_id.md" %}
# ⚙️ Funzione `fn_get_tipo_doc_fiscale_id`

```sql
CREATE FUNCTION fn_get_tipo_doc_fiscale_id(p_sorgente_tipo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_tipo_doc_fiscale_id(p_sorgente_tipo_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_doc_id config.tipi_doc_fiscale.id%TYPE;
BEGIN
    IF p_sorgente_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_tipo_doc_fiscale_id', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_sorgente_tipo_id', 'valore', NULL), NULL::uuid, 'p_sorgente_tipo_id obbligatorio');
    END IF;

    SELECT s.tipo_doc_fiscale_id INTO v_tipo_doc_id
      FROM config.sorgenti s WHERE s.id = p_sorgente_tipo_id;

    IF v_tipo_doc_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_tipo_doc_fiscale_id', 'E_CODICE',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id), NULL::uuid, p_sorgente_tipo_id::text, 'config.sorgenti');
    END IF;

    RETURN v_tipo_doc_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_tipo_doc_fiscale_id(p_sorgente_tipo_id bigint)
IS 'Risoluzione tipo_doc_fiscale_id dalla sorgente (no fallback).';
```

</div>

---
{% include-markdown "signature-core.md" %}
