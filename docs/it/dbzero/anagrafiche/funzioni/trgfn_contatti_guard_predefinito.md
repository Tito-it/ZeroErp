{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_contatti_guard_predefinito.md" %}
# ⚙️ Funzione `trgfn_contatti_guard_predefinito`

```sql
CREATE FUNCTION trgfn_contatti_guard_predefinito()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_contatti_guard_predefinito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi CONSTANT text := 'anagrafiche.trgfn_contatti_guard_predefinito';
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un contesto (soggetto, ruolo, istanza) che ha contatti
    --   ha il suo predefinito: chi lo cambia ne marca un altro.
    --
    -- Regole:
    --   - riga non predefinita, o scritta da un altro trigger
    --     (pg_trigger_depth() > 1: il segno tolto da
    --     trgfn_contatti_set_default_contatto, la cascata del
    --     soggetto): niente da giudicare;
    --   1. UPDATE che resta nel contesto e toglie il segno:
    --      E_CONTATTO_PREDEFINITO_OBBLIGATORIO;
    --   2. DELETE, o UPDATE che porta la riga in un altro
    --      contesto, con altri contatti nel contesto di prima:
    --      E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE.
    -- =========================================================
    IF NOT OLD.is_default OR pg_trigger_depth() > 1 THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;

    -- 1) Il segno tolto, nello stesso contesto.
    IF TG_OP = 'UPDATE'
       AND (OLD.soggetto_id, OLD.soggetto_ruolo_id, OLD.istanza_utility_id)
           IS NOT DISTINCT FROM
           (NEW.soggetto_id, NEW.soggetto_ruolo_id, NEW.istanza_utility_id)
    THEN
        IF NOT NEW.is_default THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', v_chi, 'E_CONTATTO_PREDEFINITO_OBBLIGATORIO',
                jsonb_build_object('campo',              'is_default',
                                   'tabella',            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                                   'contatto_id',        OLD.id,
                                   'soggetto_id',        OLD.soggetto_id,
                                   'soggetto_ruolo_id',  OLD.soggetto_ruolo_id,
                                   'istanza_utility_id', OLD.istanza_utility_id),
                OLD.tx_id,
                OLD.nominativo::text);
        END IF;
        RETURN NEW;
    END IF;

    -- 2) Il predefinito che esce dal contesto: cancellato o spostato.
    IF EXISTS (
        SELECT 1
          FROM anagrafiche.contatti c
         WHERE c.soggetto_id = OLD.soggetto_id
           AND c.soggetto_ruolo_id  IS NOT DISTINCT FROM OLD.soggetto_ruolo_id
           AND c.istanza_utility_id IS NOT DISTINCT FROM OLD.istanza_utility_id
           AND c.id <> OLD.id)
    THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', v_chi, 'E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE',
            jsonb_build_object('campo',              'is_default',
                               'tabella',            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'operazione',         TG_OP,
                               'contatto_id',        OLD.id,
                               'soggetto_id',        OLD.soggetto_id,
                               'soggetto_ruolo_id',  OLD.soggetto_ruolo_id,
                               'istanza_utility_id', OLD.istanza_utility_id),
            OLD.tx_id,
            OLD.nominativo::text);
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_contatti_guard_predefinito()
IS 'Trigger BEFORE UPDATE OR DELETE su anagrafiche.contatti (fase a10): un contesto (soggetto, ruolo, istanza) che ha contatti ha il suo predefinito, e chi lo cambia ne marca un altro. Togliere il segno al predefinito restando nel contesto: E_CONTATTO_PREDEFINITO_OBBLIGATORIO (campo is_default). Cancellare il predefinito, o portarlo in un altro contesto, quando nel suo restano altri contatti: E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE (campo is_default). L''ultimo contatto del contesto si cancella. Una scrittura fatta da un altro trigger (pg_trigger_depth() > 1) non si giudica: e'' il segno tolto da anagrafiche.trgfn_contatti_set_default_contatto quando un altro contatto diventa predefinito, e la cascata della cancellazione del soggetto. Il gemello che mette il segno e'' anagrafiche.trgfn_contatti_set_default_contatto; la regola sta nella nota _contatto-predefinito.';
```

</div>

---
{% include-markdown "signature-core.md" %}
