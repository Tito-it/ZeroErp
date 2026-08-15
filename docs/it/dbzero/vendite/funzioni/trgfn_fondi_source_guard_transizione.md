{% include-markdown "it/dbzero/vendite/manual/trgfn_fondi_source_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_fondi_source_guard_transizione`

```sql
CREATE FUNCTION trgfn_fondi_source_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fondi_source_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: far rispettare la matrice degli stati del fondo.
--        ANNULLATO e' terminale: riaprirlo rimetterebbe in gioco
--        denaro che qualcuno aveva tolto dal tavolo. Se serve di
--        nuovo, si compie un atto NUOVO.
-- Uso:   BEFORE UPDATE OF stato FOR EACH ROW
DECLARE
    v_ammessa BOOLEAN;
BEGIN
    -- Nessun movimento di stato: niente da verificare.
    IF NEW.stato IS NOT DISTINCT FROM OLD.stato THEN
        RETURN NEW;
    END IF;

    v_ammessa := CASE OLD.stato
        WHEN 'DISPONIBILE' THEN NEW.stato IN ('ASSEGNATO', 'ANNULLATO')
        WHEN 'ASSEGNATO'   THEN NEW.stato IN ('DISPONIBILE', 'ANNULLATO')
        WHEN 'ANNULLATO'   THEN FALSE
        ELSE FALSE
    END;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_fondi_source_guard_transizione',
            'E_FONDO_STATO_NON_AMMESSO',
            jsonb_build_object(
                'fondo_source_id',     NEW.id,
                'fattura_sorgente_id', NEW.fattura_sorgente_id,
                'stato_da',            OLD.stato,
                'stato_a',             NEW.stato),
            NULL::uuid,
            OLD.stato, NEW.stato);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fondi_source_guard_transizione()
IS 'Matrice degli stati del fondo fattura: DISPONIBILE -> ASSEGNATO|ANNULLATO, ASSEGNATO -> DISPONIBILE|ANNULLATO, ANNULLATO terminale. Tre stati e non quattro: REVOCATO e'' caduto insieme al meccanismo di revoca+riemissione, inutile da quando il fondo non si ricalcola. ⚠️ ASSEGNATO -> DISPONIBILE resta ammesso ed e'' il RESET TECNICO della figlia (ritorno del lotto in bozza), non una reazione ai pagamenti. ⚠️ ANNULLATO e'' terminale di proposito: riaprire un fondo annullato rimetterebbe in gioco denaro che una persona o una regola aveva tolto dal tavolo — se serve di nuovo si compie un atto NUOVO, con la stessa logica per cui un atto non si modifica ma si annulla con un altro atto. Guard e non lookup di transizioni: sono tre valori interni senza etichette ne'' azioni di UI. D-7 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

---
{% include-markdown "signature-core.md" %}
