{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_componenti_block_modifica_struttura.md" %}
# ⚙️ Funzione `trgfn_articoli_componenti_block_modifica_struttura`

```sql
CREATE FUNCTION trgfn_articoli_componenti_block_modifica_struttura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_componenti_block_modifica_struttura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_oggi    date := script.fn_data_operativa();
    v_min_al  catalogo.articoli_componenti.valido_al%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La distinta e' una storia: un legame non si cancella e la sua
    --   struttura non cambia (si chiude e se ne inserisce uno nuovo),
    --   e la sua fine non cambia i giorni gia' passati.
    -- Regole:
    --   1. DELETE -> E_BOM_MODIFICA_VIETATA, sempre.
    --   2. UPDATE di prodotto_id, componente_id, coeff_qta, obbligatorio,
    --      esposizione_in_fattura, valido_dal -> E_BOM_MODIFICA_VIETATA.
    --      validita e' generata: PostgreSQL rifiuta da se' la scrittura.
    --   3. UPDATE di valido_al:
    --      a. legame la cui fine e' gia' passata (valido_al < oggi): la
    --         fine non si cambia piu' -> E_BOM_LEGAME_CHIUSO. Rimettere
    --         il componente nella distinta e' un legame nuovo;
    --      b. altrimenti la fine nuova e' vuota oppure da ieri in avanti:
    --         prima di ieri toglierebbe al legame giorni gia' passati ->
    --         E_BOM_CHIUSURA_RETROATTIVA. Chiudere a ieri lascia la storia
    --         com'era, e permette a una versione nuova di valere da oggi.
    --      Una fine che precede valido_dal non si giudica qui: e' la regola
    --      del periodo (script.trgfn_guard_date_validita, E_DATA_AL_MINORE_DAL).
    --   4. UPDATE di attivo, note, meta, audit -> ammesso.
    -- =========================================================

    IF TG_OP = 'DELETE' THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo',
            TG_NAME::text,
            'E_BOM_MODIFICA_VIETATA',
            jsonb_build_object(
                'operazione',    'DELETE',
                'hint',          'Chiudi la riga impostando valido_al invece di eliminarla.',
                'prodotto_id',   OLD.prodotto_id,
                'componente_id', OLD.componente_id,
                'riga_id',       OLD.id
            ),
            OLD.tx_id,
            VARIADIC ARRAY[]::text[]
        );
    END IF;

    IF NEW.prodotto_id               IS DISTINCT FROM OLD.prodotto_id
       OR NEW.componente_id          IS DISTINCT FROM OLD.componente_id
       OR NEW.coeff_qta              IS DISTINCT FROM OLD.coeff_qta
       OR NEW.obbligatorio           IS DISTINCT FROM OLD.obbligatorio
       OR NEW.esposizione_in_fattura IS DISTINCT FROM OLD.esposizione_in_fattura
       OR NEW.valido_dal             IS DISTINCT FROM OLD.valido_dal
    THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo',
            TG_NAME::text,
            'E_BOM_MODIFICA_VIETATA',
            jsonb_build_object(
                'operazione',    'UPDATE_STRUTTURA',
                'hint',          'Chiudi questa riga (imposta valido_al) e inserisci una nuova riga con i valori aggiornati.',
                'prodotto_id',   OLD.prodotto_id,
                'componente_id', OLD.componente_id,
                'riga_id',       OLD.id
            ),
            NEW.tx_id,
            VARIADIC ARRAY[]::text[]
        );
    END IF;

    IF NEW.valido_al IS DISTINCT FROM OLD.valido_al
       AND (NEW.valido_al IS NULL OR NEW.valido_al >= NEW.valido_dal) THEN

        IF OLD.valido_al < v_oggi THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo',
                TG_NAME::text,
                'E_BOM_LEGAME_CHIUSO',
                jsonb_build_object(
                    'campo',         'valido_al',
                    'prodotto_id',   OLD.prodotto_id,
                    'componente_id', OLD.componente_id,
                    'riga_id',       OLD.id,
                    'valido_al',     OLD.valido_al
                ),
                NEW.tx_id,
                to_char(OLD.valido_al, 'DD/MM/YYYY')
            );
        END IF;

        v_min_al := v_oggi - 1;
        IF NEW.valido_al < v_min_al THEN
            PERFORM script.fn_log_and_raise_error(
                'catalogo',
                TG_NAME::text,
                'E_BOM_CHIUSURA_RETROATTIVA',
                jsonb_build_object(
                    'campo',         'valido_al',
                    'prodotto_id',   OLD.prodotto_id,
                    'componente_id', OLD.componente_id,
                    'riga_id',       OLD.id,
                    'valido_al',     NEW.valido_al,
                    'valido_al_min', v_min_al
                ),
                NEW.tx_id,
                to_char(v_min_al, 'DD/MM/YYYY')
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_componenti_block_modifica_struttura()
IS 'Guard d''immutabilita'' di catalogo.articoli_componenti, BEFORE DELETE OR UPDATE OF prodotto_id, componente_id, coeff_qta, obbligatorio, esposizione_in_fattura, valido_dal, valido_al. La distinta e'' una storia: un legame non si cancella (E_BOM_MODIFICA_VIETATA) e la sua struttura non cambia (prodotto_id, componente_id, coeff_qta, obbligatorio, esposizione_in_fattura, valido_dal: E_BOM_MODIFICA_VIETATA); per cambiarla si chiude il legame e se ne inserisce uno nuovo. La fine (valido_al) non cambia i giorni gia'' passati, al giorno aziendale (script.fn_data_operativa): un legame la cui fine e'' gia'' passata non si tocca piu'' (E_BOM_LEGAME_CHIUSO, campo valido_al: rimettere il componente e'' un legame nuovo); negli altri la fine nuova e'' vuota oppure da ieri in avanti (E_BOM_CHIUSURA_RETROATTIVA, campo valido_al, con la prima data ammessa). Chiudere a ieri permette a una versione nuova di valere da oggi. Una fine che precede valido_dal la giudica la regola del periodo (script.trgfn_guard_date_validita, E_DATA_AL_MINORE_DAL). validita e'' generata. attivo, note, meta e audit si cambiano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
