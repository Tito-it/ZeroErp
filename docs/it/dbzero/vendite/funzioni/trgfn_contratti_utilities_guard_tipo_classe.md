{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_utilities_guard_tipo_classe.md" %}
# ⚙️ Funzione `trgfn_contratti_utilities_guard_tipo_classe`

```sql
CREATE FUNCTION trgfn_contratti_utilities_guard_tipo_classe()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_utilities_guard_tipo_classe()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_utility_has_tipi    boolean;
    v_classe_tipo_utenza  config.classi_utenze.tipo_utenza_id%TYPE;
BEGIN
    -- Ottimizzazione: un'unica CTE risolve sia il flag "utility con
    -- dimensione tipo/classe" (EXISTS in config.tipi_utenze) sia
    -- il tipo_utenza della classe dichiarata dal contratto.
    -- Se classe_utenza_id e' NULL, v_classe_tipo_utenza resta NULL
    -- e verra' segnalato dal guard piu' sotto.
    SELECT
        EXISTS (SELECT 1 FROM config.tipi_utenze tu
                 WHERE tu.utility_id = NEW.utility_id),
        (SELECT cl.tipo_utenza_id FROM config.classi_utenze cl
          WHERE cl.id = NEW.classe_utenza_id)
      INTO v_utility_has_tipi, v_classe_tipo_utenza;

    IF v_utility_has_tipi THEN
        -- Utility con dimensione: tipo e classe obbligatori e coerenti.
        IF NEW.tipo_utenza_id IS NULL OR NEW.classe_utenza_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                TG_NAME,
                'E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI',
                jsonb_build_object(
                    'campo', CASE WHEN NEW.tipo_utenza_id IS NULL THEN 'tipo_utenza_id' ELSE 'classe_utenza_id' END,
                    'contratto_id', NEW.contratto_id,
                    'utility_id', NEW.utility_id,
                    'tipo_utenza_id', NEW.tipo_utenza_id,
                    'classe_utenza_id', NEW.classe_utenza_id
                ),
                NULL::uuid,
                NEW.utility_id::text
            );
        END IF;

        -- Coerenza: la classe deve appartenere al tipo dichiarato.
        IF v_classe_tipo_utenza IS DISTINCT FROM NEW.tipo_utenza_id THEN
            -- Valori per %s: classe_utenza_id, classe.tipo_utenza_id, contratto.tipo_utenza_id.
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                TG_NAME,
                'E_CONTRATTO_CLASSE_TIPO_INCOERENTE',
                jsonb_build_object(
                    'campo', 'classe_utenza_id',
                    'contratto_id', NEW.contratto_id,
                    'utility_id', NEW.utility_id,
                    'tipo_utenza_id_atteso', NEW.tipo_utenza_id,
                    'tipo_utenza_id_classe', v_classe_tipo_utenza,
                    'classe_utenza_id', NEW.classe_utenza_id
                ),
                NULL::uuid,
                NEW.classe_utenza_id::text,
                v_classe_tipo_utenza::text,
                NEW.tipo_utenza_id::text
            );
        END IF;
    ELSE
        -- Utility senza dimensione (es. Base / commercio):
        -- entrambi i campi devono essere NULL.
        IF NEW.tipo_utenza_id IS NOT NULL OR NEW.classe_utenza_id IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite',
                TG_NAME,
                'E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI',
                jsonb_build_object(
                    'campo', CASE WHEN NEW.tipo_utenza_id IS NOT NULL THEN 'tipo_utenza_id' ELSE 'classe_utenza_id' END,
                    'contratto_id', NEW.contratto_id,
                    'utility_id', NEW.utility_id,
                    'tipo_utenza_id', NEW.tipo_utenza_id,
                    'classe_utenza_id', NEW.classe_utenza_id
                ),
                NULL::uuid,
                NEW.utility_id::text
            );
        END IF;
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_utilities_guard_tipo_classe()
IS 'Guard BEFORE INS/UPD su vendite.contratti_utilities: coerenza tipo_utenza_id, classe_utenza_id e utility. Pricing v5.';
```

</div>

---
{% include-markdown "signature-core.md" %}
