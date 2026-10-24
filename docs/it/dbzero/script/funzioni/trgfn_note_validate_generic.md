{% include-markdown "it/dbzero/script/manual/trgfn_note_validate_generic.md" %}
# ⚙️ Funzione `trgfn_note_validate_generic`

```sql
CREATE FUNCTION trgfn_note_validate_generic()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_note_validate_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_child_table text := TG_ARGV[0];   
  v_child_fk    text := TG_ARGV[1];   

  v_domain      text := COALESCE(TG_ARGV[2], TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME);

  v_found_parent_id bigint;
  v_reg regclass;
  v_area text := TG_TABLE_SCHEMA;     
BEGIN

  IF NEW.anchor_tipo <> 'RIGA' THEN
    RETURN NEW;
  END IF;


  IF NEW.target_riga_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      v_area, TG_TABLE_NAME, 'E_NOTE_TARGET_ID',
      jsonb_build_object('anchor_tipo', NEW.anchor_tipo,
                        'target_id', NEW.target_id,
                        'target_riga_id', NEW.target_riga_id,
                        'detail','target_riga_id mancante'),
      NULL::uuid,
      NEW.anchor_tipo, NEW.target_id::text
    );
  END IF;


  v_reg := to_regclass(v_child_table);
  IF v_reg IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      v_area, TG_TABLE_NAME, 'E_NOTE_CONFIG',
      jsonb_build_object('child_table', v_child_table,
                        'child_fk', v_child_fk,
                        'detail','tabella righe non trovata'),
      NULL::uuid,
      v_child_table
    );
  END IF;


  EXECUTE format('SELECT %I FROM %s WHERE id = $1', v_child_fk, v_reg)
    INTO v_found_parent_id
    USING NEW.target_riga_id;


  IF v_found_parent_id IS NULL OR v_found_parent_id IS DISTINCT FROM NEW.target_id THEN
    PERFORM script.fn_log_and_raise_error(
      v_area, TG_TABLE_NAME, 'E_NOTE_RIGA_MISMATCH',
      jsonb_build_object('dominio', v_domain,
                        'target_id', NEW.target_id,
                        'target_riga_id', NEW.target_riga_id,
                        'child_table', v_child_table,
                        'child_fk', v_child_fk,
                        'fk_value', v_found_parent_id),
      NULL::uuid,
      -- rev 2026-08-04 (bonifica F3): NEW.target_riga_id e' bigint e il
      --   parametro e' VARIADIC text[]: senza ::text la chiamata non si
      --   risolve. Gli altri due valori erano gia' testuali.
      NEW.target_riga_id::text, v_domain, NEW.target_id::text
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION script.trgfn_note_validate_generic()
IS 'Validazione generica per note ancorate a RIGA: verifica appartenenza target_riga_id→target_id via tabella righe (schema.qualificata) e FK passate in TG_ARGV.';
```

</div>

---
{% include-markdown "signature-core.md" %}
