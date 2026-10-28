{% include-markdown "it/dbzero/script/manual/trgfn_note_validate_generic.md" %}
# ⚙️ Funzione `trgfn_note_validate_generic`

```sql
CREATE FUNCTION trgfn_note_validate_generic()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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

  -- La parola che l'operatore legge nella frase d'errore: l'etichetta della
  --   sorgente del tipo della nota (si legge solo nel ramo d'errore).
  v_etichetta   config.sorgenti.etichetta%TYPE;

  -- ⚠️ `bigint` esplicito: e' l'id della testata letto dalla tabella delle righe
  --   che arriva in TG_ARGV, diversa per ogni montaggio.
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
    -- rev 2026-10-25 (grammatica unica, lotto 3, L3-4): il dominio e' il tipo della
    --   riga, non piu' il terzo argomento del trigger (che lo ripeteva a mano).
    SELECT s.etichetta INTO v_etichetta
      FROM config.sorgenti s
     WHERE s.codice_interno = NEW.target_tipo;

    PERFORM script.fn_log_and_raise_error(
      v_area, TG_TABLE_NAME, 'E_NOTE_RIGA_MISMATCH',
      jsonb_build_object('dominio', NEW.target_tipo,
                        'target_id', NEW.target_id,
                        'target_riga_id', NEW.target_riga_id,
                        'child_table', v_child_table,
                        'child_fk', v_child_fk,
                        'fk_value', v_found_parent_id),
      NULL::uuid,
      -- rev 2026-08-04 (bonifica F3): NEW.target_riga_id e' bigint e il
      --   parametro e' VARIADIC text[]: senza ::text la chiamata non si
      --   risolve.
      NEW.target_riga_id::text,
      COALESCE(v_etichetta, NEW.target_tipo)::text,
      NEW.target_id::text
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION script.trgfn_note_validate_generic()
IS 'Validazione generica per note ancorate a RIGA: verifica appartenenza target_riga_id→target_id via tabella righe (schema.qualificata) e FK passate in TG_ARGV[0] e TG_ARGV[1]. Rev 2026-10-25 (20261025-66, brief-db-grammatica-unica-documenti lotto 3, L3-4): il dominio dell''errore E_NOTE_RIGA_MISMATCH e'' NEW.target_tipo nel payload e l''etichetta della sorgente nella frase per l''operatore; il terzo argomento del trigger, che ripeteva il confine della partizione, non si legge piu''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
