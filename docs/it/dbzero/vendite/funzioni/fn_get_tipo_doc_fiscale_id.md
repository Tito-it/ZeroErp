{% include-markdown "it/dbzero/vendite/manual/fn_get_tipo_doc_fiscale_id.md" %}
# ⚙️ Funzione `fn_get_tipo_doc_fiscale_id`

```sql
CREATE FUNCTION fn_get_tipo_doc_fiscale_id(p_sorgente_tipo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_tipo_doc_fiscale_id(p_sorgente_tipo_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_doc_id config.tipi_doc_fiscale.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve il tipo documento fiscale dalla sorgente.
  --
  -- Regole:
  --   1) config.sorgenti.tipo_doc_fiscale_id
  --   2) errore
  -- =========================================================

  IF p_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_tipo_doc_fiscale_id', 'E_GENERICO',
      jsonb_build_object('detail','sorgente_tipo_id obbligatorio'),
      NULL::uuid,
      'sorgente_tipo_id obbligatorio'
    );
  END IF;

  SELECT s.tipo_doc_fiscale_id
    INTO v_tipo_doc_id
    FROM config.sorgenti s
   WHERE s.id = p_sorgente_tipo_id;

  IF v_tipo_doc_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_tipo_doc_fiscale_id', 'E_GENERICO',
      jsonb_build_object(
        'detail','Tipo documento fiscale non risolto (sorgente)',
        'sorgente_tipo_id', p_sorgente_tipo_id
      ),
      NULL::uuid,
      'Tipo documento fiscale non risolto (sorgente)'
    );
  END IF;

  RETURN v_tipo_doc_id;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
