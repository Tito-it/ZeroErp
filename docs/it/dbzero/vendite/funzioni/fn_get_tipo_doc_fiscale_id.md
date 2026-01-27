{% include-markdown "it/dbzero/vendite/manual/fn_get_tipo_doc_fiscale_id.md" %}
# ⚙️ Funzione `fn_get_tipo_doc_fiscale_id`

```sql
CREATE FUNCTION fn_get_tipo_doc_fiscale_id(p_sorgente_tipo_id bigint, p_utility_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_tipo_doc_fiscale_id(p_sorgente_tipo_id bigint, p_utility_id integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_doc_id config.tipi_doc_fiscale.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve il tipo documento fiscale da sorgente o utility.
  --
  -- Regole:
  --   1) config.sorgenti.tipo_doc_fiscale_id
  --   2) config.utilities.tipo_doc_fiscale_id
  --   3) errore
  -- =========================================================

  IF p_sorgente_tipo_id IS NULL AND p_utility_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_tipo_doc_fiscale_id', 'E_GENERICO',
      jsonb_build_object('detail','Parametri obbligatori mancanti (sorgente/utility)'),
      NULL::uuid,
      'Parametri obbligatori mancanti (sorgente/utility)'
    );
  END IF;

  IF p_sorgente_tipo_id IS NOT NULL THEN
    SELECT s.tipo_doc_fiscale_id
      INTO v_tipo_doc_id
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id;
  END IF;

  IF v_tipo_doc_id IS NULL AND p_utility_id IS NOT NULL THEN
    SELECT u.tipo_doc_fiscale_id
      INTO v_tipo_doc_id
      FROM config.utilities u
     WHERE u.id = p_utility_id;
  END IF;

  IF v_tipo_doc_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_tipo_doc_fiscale_id', 'E_GENERICO',
      jsonb_build_object(
        'detail','Tipo documento fiscale non risolto (sorgente/utility)',
        'sorgente_tipo_id', p_sorgente_tipo_id,
        'utility_id', p_utility_id
      ),
      NULL::uuid,
      concat('Tipo documento fiscale non risolto (sorgente/utility)', ' lotto_id: ', p_lotto_id::text)
    );
  END IF;

  RETURN v_tipo_doc_id;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
