{% include-markdown "it/dbzero/vendite/manual/fn_get_registro_id.md" %}
# ⚙️ Funzione `fn_get_registro_id`

```sql
CREATE FUNCTION fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_registro_id vendite.registri_fatturazione.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve il registro dal mapping tipo_doc_fiscale -> registro
  --   considerando utility ed emittente (se presenti sul registro).
  --
  -- Regole (ordine):
  --   1) tipo_doc + utility + emittente
  --   2) tipo_doc + utility
  --   3) tipo_doc + emittente
  --   4) tipo_doc (generico)
  -- =========================================================

  IF p_tipo_doc_fiscale_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_registro_id', 'E_GENERICO',
      jsonb_build_object('detail','tipo_doc_fiscale_id obbligatorio'),
      NULL::uuid,
      'tipo_doc_fiscale_id obbligatorio'
    );
  END IF;

  SELECT r.id
    INTO v_registro_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN vendite.registri_fatturazione r
      ON r.id = m.registro_id
   WHERE m.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
     AND (r.utility_id IS NULL OR r.utility_id = p_utility_id)
     AND (r.emittente_soggetto_ruolo_id IS NULL OR r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
   ORDER BY
     CASE
       WHEN r.utility_id = p_utility_id AND r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id THEN 1
       WHEN r.utility_id = p_utility_id AND r.emittente_soggetto_ruolo_id IS NULL THEN 2
       WHEN r.utility_id IS NULL AND r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id THEN 3
       WHEN r.utility_id IS NULL AND r.emittente_soggetto_ruolo_id IS NULL THEN 4
       ELSE 9
     END,
     r.id
   LIMIT 1;

  IF v_registro_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_registro_id', 'E_GENERICO',
      jsonb_build_object(
        'detail','Registro non risolto (tipo_doc/utility/emittente)',
        'tipo_doc_fiscale_id', p_tipo_doc_fiscale_id,
        'utility_id', p_utility_id,
        'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id
      ),
      NULL::uuid,
      'Registro non risolto (tipo_doc/utility/emittente)'
    );
  END IF;

  RETURN v_registro_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
IS 'Risoluzione registro_id con combinazioni utility/emittente (fallback).';
```

---
{% include-markdown "signature-core.md" %}
