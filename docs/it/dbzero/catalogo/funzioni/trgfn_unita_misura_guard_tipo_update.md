{% include-markdown "it/dbzero/catalogo/manual/trgfn_unita_misura_guard_tipo_update.md" %}
# ⚙️ Funzione `trgfn_unita_misura_guard_tipo_update`

```sql
CREATE FUNCTION trgfn_unita_misura_guard_tipo_update()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_unita_misura_guard_tipo_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_count bigint;
BEGIN
  -- ==========================================================
  -- Scopo:
  --   Evitare che il cambio di tipo su una UoM gia' usata in
  --   conversioni globali aggiri il vincolo same-type.
  -- ==========================================================
  SELECT COUNT(*)
    INTO v_count
    FROM catalogo.unita_misura_conversioni c
   WHERE c.uom_from_id = NEW.id
      OR c.uom_to_id   = NEW.id;

  IF COALESCE(v_count, 0) > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'catalogo',
      TG_NAME,
      'E_GENERICO',
      jsonb_build_object(
        'uom_id', NEW.id,
        'tipo_uom_old_id', OLD.tipo_uom_id,
        'tipo_uom_new_id', NEW.tipo_uom_id,
        'conversioni_collegate', v_count,
        'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
      ),
      NULL::uuid,
      'Cambio tipo UoM non ammesso: la UoM partecipa a conversioni globali.'
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_unita_misura_guard_tipo_update()
IS 'Blocca il cambio di tipo_uom_id su UoM gia'' coinvolte in conversioni globali.';
```

</div>

---
{% include-markdown "signature-core.md" %}
