{% include-markdown "it/dbzero/catalogo/manual/trgfn_unita_misura_guard_tipo.md" %}
# ⚙️ Funzione `trgfn_unita_misura_guard_tipo`

```sql
CREATE FUNCTION trgfn_unita_misura_guard_tipo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_unita_misura_guard_tipo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_codice catalogo.uom_tipi.codice_interno%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: la tipologia di un'unita' di misura.
    --   1) non cambia se l'unita' compare in una conversione generale:
    --      la conversione vale solo fra unita' della stessa tipologia
    --      (catalogo.trgfn_uom_conversioni_guard_tipo, che legge le
    --      unita' FOR SHARE contro questo cambio);
    --   2) un'unita' che si conta dal calendario (conta_dal_calendario)
    --      e' di tipologia TEMPO.
    -- =========================================================
    IF TG_OP = 'UPDATE'
       AND NEW.tipo_uom_id IS DISTINCT FROM OLD.tipo_uom_id
       AND EXISTS (SELECT 1
                     FROM catalogo.unita_misura_conversioni c
                    WHERE c.uom_from_id = NEW.id
                       OR c.uom_to_id   = NEW.id) THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.trgfn_unita_misura_guard_tipo',
            'E_UOM_TIPO_IN_USO',
            jsonb_build_object(
                'campo',           'tipo_uom_id',
                'uom_id',          NEW.id,
                'tipo_uom_old_id', OLD.tipo_uom_id,
                'tipo_uom_new_id', NEW.tipo_uom_id),
            NULL::uuid,
            NEW.codice);
    END IF;

    IF NEW.conta_dal_calendario IS NOT NULL THEN
        SELECT t.codice_interno INTO v_tipo_codice
          FROM catalogo.uom_tipi t
         WHERE t.id = NEW.tipo_uom_id;
        -- Tipologia inesistente: parla la FK.
        IF FOUND AND v_tipo_codice IS DISTINCT FROM 'TEMPO' THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.trgfn_unita_misura_guard_tipo',
                'E_UOM_CALENDARIO_NON_TEMPO',
                jsonb_build_object(
                    'campo',                'conta_dal_calendario',
                    'uom_id',               NEW.id,
                    'tipo_uom_id',          NEW.tipo_uom_id,
                    'conta_dal_calendario', NEW.conta_dal_calendario),
                NULL::uuid,
                NEW.codice);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_unita_misura_guard_tipo()
IS 'Guard BEFORE INSERT e UPDATE OF tipo_uom_id, conta_dal_calendario su catalogo.unita_misura. La tipologia non cambia se l''unita'' compare in una conversione generale di catalogo.unita_misura_conversioni (E_UOM_TIPO_IN_USO): la conversione vale solo fra unita'' della stessa tipologia, e il guard delle conversioni legge le unita'' FOR SHARE contro questo cambio. Un''unita'' che si conta dal calendario (conta_dal_calendario GIORNO o MESE) e'' di tipologia TEMPO (codice_interno di catalogo.uom_tipi), altrimenti E_UOM_CALENDARIO_NON_TEMPO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
