{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_check_coerenza.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_check_coerenza`

```sql
CREATE FUNCTION trgfn_documenti_generati_check_coerenza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_check_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Valida la coerenza referenziale del documento generato.
--
-- Regole:
--   1. template_versione_id.template_documento_id ==
--      template_documento_id
--   2. template_documento_id.tipo_documento_output_id ==
--      tipo_documento_output_id
--   3. template_documento_id.sorgente_tipo_id ==
--      sorgente_tipo_id
--   4. template_documento_id.emittente_fiscale_id ==
--      emittente_fiscale_id
--
-- Se una di queste fallisce il record nasce inconsistente,
-- rendendo inaffidabile l'audit tramite context_json snapshot.
--
-- Errore:
--   E_DOCUMENTI_GENERATO_COERENZA
DECLARE
  v_tv_template_id documenti.template_documenti_versioni.template_documento_id%TYPE;
  v_tv_tipo_id documenti.template_documenti.tipo_documento_output_id%TYPE;
  v_tv_sorgente_id documenti.template_documenti.sorgente_tipo_id%TYPE;
  v_tv_emittente_id documenti.template_documenti.emittente_fiscale_id%TYPE;
BEGIN
  SELECT
    template_documento_id,
    (SELECT tipo_documento_output_id
       FROM documenti.template_documenti
      WHERE id = template_documento_id) AS tipo_id,
    (SELECT sorgente_tipo_id
       FROM documenti.template_documenti
      WHERE id = template_documento_id) AS sorgente_id,
    (SELECT emittente_fiscale_id
       FROM documenti.template_documenti
      WHERE id = template_documento_id) AS emittente_id
    INTO v_tv_template_id, v_tv_tipo_id, v_tv_sorgente_id, v_tv_emittente_id
    FROM documenti.template_documenti_versioni
   WHERE id = NEW.template_versione_id;

  IF v_tv_template_id != NEW.template_documento_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_versione_id', NEW.template_versione_id,
        'template_documento_id_atteso', v_tv_template_id,
        'template_documento_id_fornito', NEW.template_documento_id
      ),
      NULL::uuid
    );
  END IF;

  IF v_tv_tipo_id != NEW.tipo_documento_output_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'tipo_documento_output_id_atteso', v_tv_tipo_id,
        'tipo_documento_output_id_fornito', NEW.tipo_documento_output_id
      ),
      NULL::uuid
    );
  END IF;

  IF v_tv_sorgente_id != NEW.sorgente_tipo_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'sorgente_tipo_id_atteso', v_tv_sorgente_id,
        'sorgente_tipo_id_fornito', NEW.sorgente_tipo_id
      ),
      NULL::uuid
    );
  END IF;

  IF v_tv_emittente_id != NEW.emittente_fiscale_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'emittente_fiscale_id_atteso', v_tv_emittente_id,
        'emittente_fiscale_id_fornito', NEW.emittente_fiscale_id
      ),
      NULL::uuid
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_check_coerenza()
IS 'Guard A6: valida coerenza referenziale tra template_versione_id, template_documento_id, tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id.';
```

---
{% include-markdown "signature-core.md" %}
