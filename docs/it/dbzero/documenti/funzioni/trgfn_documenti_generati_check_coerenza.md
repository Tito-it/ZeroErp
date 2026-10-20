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
--   2-4. il modello va bene per il documento: stessa sorgente,
--      stesso tipo di output, e lo stesso emittente OPPURE il
--      modello e' standard. La regola e' del BB
--      documenti.fn_template_motivo_non_coerente (rev
--      20261021-06, brief-db-modelli-documento-standard §10.3
--      K-4): la stessa domanda che la risoluzione fa sul modello
--      indicato prima del render.
--
-- Se una di queste fallisce il record nasce inconsistente,
-- rendendo inaffidabile l'audit tramite context_json snapshot.
--
-- Errore:
--   E_DOCUMENTI_GENERATO_COERENZA
DECLARE
  v_tv_template_id documenti.template_documenti_versioni.template_documento_id%TYPE;
  -- tipo esplicito: il motivo del BB, non una colonna
  v_motivo         text;
BEGIN
  SELECT v.template_documento_id
    INTO v_tv_template_id
    FROM documenti.template_documenti_versioni v
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

  v_motivo := documenti.fn_template_motivo_non_coerente(
      NEW.template_documento_id, NEW.sorgente_tipo_id,
      NEW.emittente_fiscale_id, NEW.tipo_documento_output_id);

  IF v_motivo IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'documenti', 'trgfn_documenti_generati_check_coerenza',
      'E_DOCUMENTI_GENERATO_COERENZA',
      jsonb_build_object(
        'template_documento_id', NEW.template_documento_id,
        'motivo', v_motivo,
        'sorgente_tipo_id', NEW.sorgente_tipo_id,
        'tipo_documento_output_id', NEW.tipo_documento_output_id,
        'emittente_fiscale_id', NEW.emittente_fiscale_id
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_check_coerenza()
IS 'Guard A6: valida coerenza referenziale tra template_versione_id, template_documento_id, tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id. Regola 1 (la versione e'' di quel modello) qui; regole 2-4 (stessa sorgente, stesso tipo, stesso emittente oppure modello standard) dal BB documenti.fn_template_motivo_non_coerente, la stessa domanda che la risoluzione fa sul modello indicato prima del render (rev 2026-10-21, 20261021-06, brief-db-modelli-documento-standard §10.3 K-4). Il contesto porta il motivo per nome. Storia: regola 4 «oppure standard» dal 20261020-08 (§4.1 Q-3).';
```

---
{% include-markdown "signature-core.md" %}
