{% include-markdown "it/dbzero/catalogo/manual/trgfn_uom_conversioni_guard_tipo.md" %}
# ⚙️ Funzione `trgfn_uom_conversioni_guard_tipo`

```sql
CREATE FUNCTION trgfn_uom_conversioni_guard_tipo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_from_tipo_id catalogo.uom_tipi.id%TYPE;
  v_to_tipo_id   catalogo.uom_tipi.id%TYPE;
  v_from_tipo    catalogo.uom_tipi.codice%TYPE;
  v_to_tipo      catalogo.uom_tipi.codice%TYPE;
BEGIN
  -- ==========================================================
  -- Scopo:
  --   Bloccare conversioni globali tra UoM di tipologia diversa.
  --
  -- Regole:
  --   - packaging e conversioni articolo-specifiche restano in
  --     catalogo.articoli_uom_operativa
  --   - qui si ammettono solo conversioni globali same-type
  -- ==========================================================
  SELECT ut.id, ut.codice
    INTO v_from_tipo_id, v_from_tipo
    FROM catalogo.unita_misura u
    JOIN catalogo.uom_tipi ut
      ON ut.id = u.tipo_uom_id
   WHERE u.id = NEW.uom_from_id;

  SELECT ut.id, ut.codice
    INTO v_to_tipo_id, v_to_tipo
    FROM catalogo.unita_misura u
    JOIN catalogo.uom_tipi ut
      ON ut.id = u.tipo_uom_id
   WHERE u.id = NEW.uom_to_id;

  IF v_from_tipo_id IS NULL OR v_to_tipo_id IS NULL THEN
    RETURN NEW;
  END IF;

  IF v_from_tipo_id IS DISTINCT FROM v_to_tipo_id THEN
    PERFORM script.fn_log_and_raise_error(
      'catalogo',
      TG_NAME,
      'E_GENERICO',
      jsonb_build_object(
        'uom_from_id', NEW.uom_from_id,
        'uom_to_id', NEW.uom_to_id,
        'tipo_from', v_from_tipo,
        'tipo_to', v_to_tipo,
        'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
      ),
      NULL::uuid,
      'Conversione globale non ammessa tra UoM di tipologia diversa.'
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_uom_conversioni_guard_tipo()
IS 'Blocca conversioni globali tra UoM di tipologia diversa in catalogo.unita_misura_conversioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
