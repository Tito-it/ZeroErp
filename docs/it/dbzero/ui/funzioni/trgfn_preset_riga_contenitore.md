{% include-markdown "it/dbzero/ui/manual/trgfn_preset_riga_contenitore.md" %}
# ⚙️ Funzione `trgfn_preset_riga_contenitore`

```sql
CREATE FUNCTION trgfn_preset_riga_contenitore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_preset_riga_contenitore()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la lista (ui.lista_preset_colonna) o la dashboard
--   (ui.dashboard_preset_widget) di una riga di composizione e'
--   quella del suo preset.
-- Montaggio: BEFORE INSERT OR UPDATE FOR EACH ROW, fase a20.
BEGIN
    IF TG_WHEN <> 'BEFORE' OR TG_LEVEL <> 'ROW' OR TG_OP NOT IN ('INSERT', 'UPDATE')
       OR TG_RELID NOT IN ('ui.lista_preset_colonna'::regclass, 'ui.dashboard_preset_widget'::regclass) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'dettaglio', 'atteso BEFORE INSERT OR UPDATE FOR EACH ROW su ui.lista_preset_colonna o ui.dashboard_preset_widget'),
            NULL::uuid,
            format('%s: atteso BEFORE INSERT OR UPDATE FOR EACH ROW su ui.lista_preset_colonna o ui.dashboard_preset_widget',
                   TG_NAME));
    END IF;

    -- Un preset che non c'e' lascia NULL: risponde la FK del preset.
    IF TG_RELID = 'ui.lista_preset_colonna'::regclass THEN
        NEW.lista_id := (SELECT lp.lista_id FROM ui.lista_preset lp WHERE lp.id = NEW.preset_id);
    ELSE
        NEW.dashboard_id := (SELECT dp.dashboard_id FROM ui.dashboard_preset dp WHERE dp.id = NEW.preset_id);
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preset_riga_contenitore()
IS 'Scrive la lista (ui.lista_preset_colonna.lista_id) o la dashboard (ui.dashboard_preset_widget.dashboard_id) di una riga di composizione: quella del suo preset. Chi scrive la riga non la passa; un valore passato è sostituito. La coerenza fra il preset e la colonna nominata (o il widget del pool) la giudicano le FK composite che leggono la colonna. BEFORE INSERT OR UPDATE FOR EACH ROW, fase a20; montata altrove: E_TRIGGER_ARGOMENTI_INVALIDI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
