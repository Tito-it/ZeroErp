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
--      emittente_fiscale_id, OPPURE il modello e' standard
--      (template_documenti.standard: vale per ogni emittente).
--
-- ⛔ IS DISTINCT FROM e non !=: l'emittente del modello e' NULL
--   sullo standard, e un confronto nudo con un NULL passa in
--   silenzio. Lo standard si esclude per nome, non per effetto
--   del NULL.
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
  v_tv_standard documenti.template_documenti.standard%TYPE;
BEGIN
  SELECT v.template_documento_id,
         t.tipo_documento_output_id,
         t.sorgente_tipo_id,
         t.emittente_fiscale_id,
         t.standard
    INTO v_tv_template_id, v_tv_tipo_id, v_tv_sorgente_id,
         v_tv_emittente_id, v_tv_standard
    FROM documenti.template_documenti_versioni v
    LEFT JOIN documenti.template_documenti t ON t.id = v.template_documento_id
   WHERE v.id = NEW.template_versione_id;

  IF v_tv_template_id IS DISTINCT FROM NEW.template_documento_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_versione_id', NEW.template_versione_id,
        'template_documento_id_atteso', v_tv_template_id,
        'template_documento_id_fornito', NEW.template_documento_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  IF v_tv_tipo_id IS DISTINCT FROM NEW.tipo_documento_output_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'tipo_documento_output_id_atteso', v_tv_tipo_id,
        'tipo_documento_output_id_fornito', NEW.tipo_documento_output_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  IF v_tv_sorgente_id IS DISTINCT FROM NEW.sorgente_tipo_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'sorgente_tipo_id_atteso', v_tv_sorgente_id,
        'sorgente_tipo_id_fornito', NEW.sorgente_tipo_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  IF v_tv_standard IS NOT TRUE
     AND v_tv_emittente_id IS DISTINCT FROM NEW.emittente_fiscale_id THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'emittente_fiscale_id_atteso', v_tv_emittente_id,
        'emittente_fiscale_id_fornito', NEW.emittente_fiscale_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_check_coerenza()
IS 'Guard A6: valida coerenza referenziale tra template_versione_id, template_documento_id, tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id. Regola 4: l''emittente del modello e'' quello del documento, oppure il modello e'' standard (rev 2026-10-20, 20261020-08, brief-db-modelli-documento-standard §4.1 Q-3). Confronti in IS DISTINCT FROM: l''emittente del modello e'' NULL sullo standard, e un != lascerebbe passare tutto.';
```

---
{% include-markdown "signature-core.md" %}
