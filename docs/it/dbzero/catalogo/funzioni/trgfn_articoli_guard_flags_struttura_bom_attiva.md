{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_flags_struttura_bom_attiva`

```sql
CREATE FUNCTION trgfn_articoli_guard_flags_struttura_bom_attiva()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca modifiche ai flag di struttura (is_composito,
-- is_solo_componente, requires_serial) quando esiste una BoM attiva
-- che renderebbe il cambio semanticamente incoerente.
--
-- Due IF distinti per semantiche diverse:
--   - is_composito / requires_serial: cerca su prodotto_id (padre)
--   - is_solo_componente: cerca su componente_id (figlio)
-- Se il valore non cambia (IS NOT DISTINCT FROM) la query EXISTS non viene eseguita.
DECLARE
    v_ha_figli_attivi  boolean;
    v_e_figlio_attivo  boolean;
BEGIN
    -- Check 1: is_composito e/o requires_serial cambiano.
    -- Blocca se l'articolo e' padre di una BoM attiva.
    IF OLD.is_composito IS DISTINCT FROM NEW.is_composito
       OR OLD.requires_serial IS DISTINCT FROM NEW.requires_serial THEN

        SELECT EXISTS (
            SELECT 1 FROM catalogo.articoli_componenti
             WHERE prodotto_id = NEW.id
               AND attivo IS TRUE
               AND validita @> CURRENT_DATE
        ) INTO v_ha_figli_attivi;

        IF v_ha_figli_attivi THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_BOM_MODIFICA_VIETATA',
                jsonb_build_object(
                    'articolo_id', NEW.id,
                    'hint', 'is_composito e requires_serial non modificabili: '
                         || 'articolo padre di una BoM attiva.'
                ),
                NEW.tx_id,
                NEW.id::text
            );
        END IF;
    END IF;

    -- Check 2: is_solo_componente cambia.
    -- Blocca se l'articolo e' figlio in una BoM attiva.
    IF OLD.is_solo_componente IS DISTINCT FROM NEW.is_solo_componente THEN

        SELECT EXISTS (
            SELECT 1 FROM catalogo.articoli_componenti
             WHERE componente_id = NEW.id
               AND attivo IS TRUE
               AND validita @> CURRENT_DATE
        ) INTO v_e_figlio_attivo;

        IF v_e_figlio_attivo THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME::text,
                'E_BOM_MODIFICA_VIETATA',
                jsonb_build_object(
                    'articolo_id', NEW.id,
                    'hint', 'is_solo_componente non modificabile: '
                         || 'articolo figlio in una BoM attiva.'
                ),
                NEW.tx_id,
                NEW.id::text
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva()
IS 'Guard BEFORE UPDATE OF is_composito, is_solo_componente, requires_serial: blocca is_composito/requires_serial se articolo e'' padre di BoM attiva (prodotto_id); blocca is_solo_componente se articolo e'' figlio in BoM attiva (componente_id). Codice: E_BOM_MODIFICA_VIETATA (387). rev 2026-05-22.';
```

---
{% include-markdown "signature-core.md" %}
