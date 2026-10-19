# ⚙️ Funzione `trgfn_template_documenti_versioni_guard_derivata_da`

```sql
CREATE FUNCTION trgfn_template_documenti_versioni_guard_derivata_da()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_template_documenti_versioni_guard_derivata_da()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la versione di origine di una copia personalizzata
--   (derivata_da_versione_id) e' una versione di un modello standard
--   dello stesso tipo e della stessa sorgente, e non cambia fuori
--   dalla bozza.
DECLARE
    v_tipo           documenti.template_documenti.tipo_documento_output_id%TYPE;
    v_sorgente       documenti.template_documenti.sorgente_tipo_id%TYPE;
    v_standard       documenti.template_documenti.standard%TYPE;
    v_orig_tipo      documenti.template_documenti.tipo_documento_output_id%TYPE;
    v_orig_sorgente  documenti.template_documenti.sorgente_tipo_id%TYPE;
    v_orig_standard  documenti.template_documenti.standard%TYPE;
BEGIN
    -- 2) Fuori dalla bozza l'origine non cambia.
    IF TG_OP = 'UPDATE' THEN
        IF NEW.derivata_da_versione_id IS NOT DISTINCT FROM OLD.derivata_da_versione_id
           AND NEW.template_documento_id IS NOT DISTINCT FROM OLD.template_documento_id THEN
            RETURN NEW;
        END IF;
        IF NEW.derivata_da_versione_id IS DISTINCT FROM OLD.derivata_da_versione_id
           AND OLD.stato IS DISTINCT FROM 'BOZZA' THEN
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'trgfn_template_documenti_versioni_guard_derivata_da',
                'E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE',
                jsonb_build_object(
                    'template_documento_id', OLD.template_documento_id,
                    'versione',              OLD.versione,
                    'stato',                 OLD.stato,
                    'column',                'derivata_da_versione_id'),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]);
        END IF;
    END IF;

    IF NEW.derivata_da_versione_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- 1) L'origine e' di uno standard dello stesso documento, e chi
    --    la porta non e' uno standard.
    SELECT t.tipo_documento_output_id, t.sorgente_tipo_id, t.standard
      INTO v_tipo, v_sorgente, v_standard
      FROM documenti.template_documenti t
     WHERE t.id = NEW.template_documento_id;

    SELECT t.tipo_documento_output_id, t.sorgente_tipo_id, t.standard
      INTO v_orig_tipo, v_orig_sorgente, v_orig_standard
      FROM documenti.template_documenti_versioni v
      JOIN documenti.template_documenti t ON t.id = v.template_documento_id
     WHERE v.id = NEW.derivata_da_versione_id;

    IF v_orig_standard IS NOT TRUE
       OR v_standard IS NOT FALSE
       OR v_orig_tipo IS DISTINCT FROM v_tipo
       OR v_orig_sorgente IS DISTINCT FROM v_sorgente THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'trgfn_template_documenti_versioni_guard_derivata_da',
            'E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA',
            jsonb_build_object(
                'template_documento_id',   NEW.template_documento_id,
                'derivata_da_versione_id', NEW.derivata_da_versione_id,
                'origine_standard',        v_orig_standard,
                'copia_standard',          v_standard,
                'stesso_tipo',             v_orig_tipo IS NOT DISTINCT FROM v_tipo,
                'stessa_sorgente',         v_orig_sorgente IS NOT DISTINCT FROM v_sorgente),
            NULL::uuid,
            NEW.derivata_da_versione_id::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_template_documenti_versioni_guard_derivata_da()
IS 'Guard BEFORE INSERT/UPDATE OF derivata_da_versione_id, template_documento_id su documenti.template_documenti_versioni (2026-10-20, brief-db-modelli-documento-standard §4.1 Q-5). L''origine di una copia personalizzata e'' una versione di un modello standard con lo stesso tipo di documento e la stessa sorgente, e la versione che la porta non e'' di uno standard -> E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA (TECNICO: la scrive l''azione «personalizza»). Fuori dalla bozza l''origine non cambia -> E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE (la colonna non e'' nell''elenco di trgfn_template_documenti_versioni_protect_pubblicata).';
```

---
{% include-markdown "signature-core.md" %}
