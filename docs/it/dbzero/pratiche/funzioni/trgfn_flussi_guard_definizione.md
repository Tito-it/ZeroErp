{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_guard_definizione.md" %}
# ⚙️ Funzione `trgfn_flussi_guard_definizione`

```sql
CREATE FUNCTION trgfn_flussi_guard_definizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_definizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: un flusso appartiene a una pratica; il suo template deve
--        stare nella STESSA edizione di workflow che la pratica ha
--        pinnato alla nascita. Difesa a DB della coerenza pin<->step.
DECLARE
  v_pratica_definizione_id  pratiche.pratiche.definizione_id%TYPE;
  v_template_definizione_id pratiche.template_flussi.definizione_id%TYPE;
  v_template_codice         pratiche.template_flussi.codice%TYPE;
BEGIN
  SELECT p.definizione_id
    INTO v_pratica_definizione_id
    FROM pratiche.pratiche p
   WHERE p.id = NEW.pratica_id;

  SELECT tf.definizione_id, tf.codice
    INTO v_template_definizione_id, v_template_codice
    FROM pratiche.template_flussi tf
   WHERE tf.id = NEW.template_flusso_id;

  IF v_template_definizione_id IS DISTINCT FROM v_pratica_definizione_id THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_flussi_guard_definizione',
      'E_FLUSSI_TEMPLATE_FUORI_DEFINIZIONE',
      jsonb_build_object(
        'flusso_pratica_id',       NEW.pratica_id,
        'template_flusso_id',      NEW.template_flusso_id,
        'template_codice',         v_template_codice,
        'template_definizione_id', v_template_definizione_id,
        'pratica_definizione_id',  v_pratica_definizione_id
      ),
      NEW.tx_id,
      COALESCE(v_template_codice, NEW.template_flusso_id::text),
      COALESCE(v_pratica_definizione_id::text, 'NULL'),
      NEW.pratica_id::text
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_guard_definizione()
IS 'BEFORE INSERT su pratiche.flussi: il template del flusso deve appartenere alla definizione (edizione di workflow) pinnata dalla pratica -> FLUSSI_TEMPLATE_FUORI_DEFINIZIONE (508). Difesa a DB della coerenza pin<->step (V6/versionamento).';
```

</div>

---
{% include-markdown "signature-core.md" %}
