{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_flags_struttura_bom_attiva`

```sql
CREATE FUNCTION trgfn_articoli_guard_flags_struttura_bom_attiva()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca modifiche ai flag di struttura (is_composito,
-- is_solo_componente, requires_serial) quando esiste una BoM attiva
-- che renderebbe il cambio semanticamente incoerente.
--
-- Tre IF distinti per semantiche diverse, ognuno col SUO predicato
-- catalogo.fn_* (lo stesso che chiama la regola gemella del form in
-- dbops.lock_columns_conditional):
--   - is_composito / requires_serial: fn_articolo_padre_di_distinta_in_vigore
--   - is_solo_componente: fn_articolo_componente_di_distinta_in_vigore
--   - is_composito false -> true: fn_articolo_primo_padre_da_oggi
--     (distinta in vigore o futura: la distinta ha un livello solo)
-- Se il valore non cambia (IS NOT DISTINCT FROM) il predicato non si chiama.
DECLARE
    v_codice_padre     catalogo.articoli.codice%TYPE;
BEGIN
    -- Check 1: is_composito e/o requires_serial cambiano.
    -- Blocca se l'articolo e' padre di una BoM attiva.
    IF OLD.is_composito IS DISTINCT FROM NEW.is_composito
       OR OLD.requires_serial IS DISTINCT FROM NEW.requires_serial THEN

        IF catalogo.fn_articolo_padre_di_distinta_in_vigore(NEW.id) THEN
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

        IF catalogo.fn_articolo_componente_di_distinta_in_vigore(NEW.id) THEN
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

    -- Check 3: l'articolo diventa composito (false -> true).
    -- Blocca se e' componente di una distinta in vigore o futura: la
    -- distinta ha un livello solo (20261013-01 lo giudica sul legame).
    -- Il padre nel messaggio e' il primo per codice: uno basta a dire
    -- dove guardare.
    IF COALESCE(NEW.is_composito, FALSE)
       AND NOT COALESCE(OLD.is_composito, FALSE) THEN

        v_codice_padre := catalogo.fn_articolo_primo_padre_da_oggi(NEW.id);

        IF v_codice_padre IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo',
                TG_NAME::text,
                'E_BOM_COMPONENTE_DIVENTA_COMPOSITO',
                jsonb_build_object(
                    'campo',        'is_composito',
                    'articolo_id',  NEW.id,
                    'codice_padre', v_codice_padre),
                NEW.tx_id,
                NEW.codice,
                v_codice_padre
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva()
IS 'Guard BEFORE UPDATE OF is_composito, is_solo_componente, requires_serial di catalogo.articoli. Check 1: is_composito e requires_serial non si cambiano se l''articolo e'' padre di una distinta in vigore (catalogo.fn_articolo_padre_di_distinta_in_vigore). Check 2: is_solo_componente non si cambia se l''articolo e'' componente di una distinta in vigore (catalogo.fn_articolo_componente_di_distinta_in_vigore). Codice dei due: E_BOM_MODIFICA_VIETATA. Check 3: un articolo che e'' componente di una distinta in vigore o futura non diventa composito (is_composito da false a true), perche'' la distinta ha un livello solo: E_BOM_COMPONENTE_DIVENTA_COMPOSITO, campo is_composito, col primo padre per codice nel messaggio (catalogo.fn_articolo_primo_padre_da_oggi). E'' il lato articolo di catalogo.trgfn_articoli_componenti_guard_un_livello. I tre predicati sono gli stessi delle regole gemelle per il form in dbops.lock_columns_conditional: guard e form rispondono uguale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
