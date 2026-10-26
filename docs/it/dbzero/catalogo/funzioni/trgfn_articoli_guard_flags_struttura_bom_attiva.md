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
-- Tre IF distinti per semantiche diverse:
--   - is_composito / requires_serial: cerca su prodotto_id (padre)
--   - is_solo_componente: cerca su componente_id (figlio)
--   - is_composito false -> true: cerca su componente_id (figlio),
--     distinta in vigore o futura: la distinta ha un livello solo
-- Se il valore non cambia (IS NOT DISTINCT FROM) la query EXISTS non viene eseguita.
DECLARE
    v_ha_figli_attivi  boolean;
    v_e_figlio_attivo  boolean;
    v_codice_padre     catalogo.articoli.codice%TYPE;
BEGIN
    -- Check 1: is_composito e/o requires_serial cambiano.
    -- Blocca se l'articolo e' padre di una BoM attiva.
    IF OLD.is_composito IS DISTINCT FROM NEW.is_composito
       OR OLD.requires_serial IS DISTINCT FROM NEW.requires_serial THEN

        SELECT EXISTS (
            SELECT 1 FROM catalogo.articoli_componenti
             WHERE prodotto_id = NEW.id
               AND attivo IS TRUE
               AND validita @> (SELECT script.fn_data_operativa())
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
               AND validita @> (SELECT script.fn_data_operativa())
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

    -- Check 3: l'articolo diventa composito (false -> true).
    -- Blocca se e' componente di una distinta in vigore o futura: la
    -- distinta ha un livello solo (20261013-01 lo giudica sul legame).
    -- Il padre nel messaggio e' il primo per codice: uno basta a dire
    -- dove guardare.
    IF COALESCE(NEW.is_composito, FALSE)
       AND NOT COALESCE(OLD.is_composito, FALSE) THEN

        SELECT a_padre.codice
          INTO v_codice_padre
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a_padre ON a_padre.id = ac.prodotto_id
         WHERE ac.componente_id = NEW.id
           AND ac.attivo IS TRUE
           AND ac.validita && daterange((SELECT script.fn_data_operativa()), NULL, '[)')
         ORDER BY a_padre.codice
         LIMIT 1;

        IF FOUND THEN
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
IS 'Guard BEFORE UPDATE OF is_composito, is_solo_componente, requires_serial: blocca is_composito/requires_serial se articolo e'' padre di BoM attiva (prodotto_id); blocca is_solo_componente se articolo e'' figlio in BoM attiva (componente_id). Codice: E_BOM_MODIFICA_VIETATA (387). rev 2026-05-22. ⭐ rev 2026-10-13 (20261013-03, brief-db-articoli-ammessi-per-documento D-4): check 3, un articolo che e'' componente di una distinta in vigore o futura (legame attivo, validita && [oggi, inf)) non diventa composito, perche'' la distinta ha un livello solo: E_BOM_COMPONENTE_DIVENTA_COMPOSITO, campo is_composito, col primo padre per codice nel messaggio. E'' il lato articolo di catalogo.trgfn_articoli_componenti_guard_un_livello; il gemello per il form e'' la regola condizionale su is_composito in dbops.lock_columns_conditional.';
```

</div>

---
{% include-markdown "signature-core.md" %}
