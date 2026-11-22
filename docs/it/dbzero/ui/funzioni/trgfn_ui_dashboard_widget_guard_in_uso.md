{% include-markdown "it/dbzero/ui/manual/trgfn_ui_dashboard_widget_guard_in_uso.md" %}
# ⚙️ Funzione `trgfn_ui_dashboard_widget_guard_in_uso`

```sql
CREATE FUNCTION trgfn_ui_dashboard_widget_guard_in_uso()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_dashboard_widget_guard_in_uso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare il DELETE dal pool di un widget che un preset della
--   stessa dashboard propone, nominando i preset.
DECLARE
    v_widget ui.widget.codice%TYPE;
    -- text: i codici dei preset, per la frase; non il riflesso di una colonna
    v_preset text;
BEGIN
    SELECT string_agg(dp.codice, ', ' ORDER BY dp.codice)
      INTO v_preset
      FROM ui.dashboard_preset_widget pw
      JOIN ui.dashboard_preset dp ON dp.id = pw.preset_id
     WHERE pw.dashboard_id = OLD.dashboard_id
       AND pw.widget_id    = OLD.widget_id;

    IF v_preset IS NOT NULL THEN
        SELECT w.codice INTO v_widget FROM ui.widget w WHERE w.id = OLD.widget_id;
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_UI_WIDGET_IN_USO',
            jsonb_build_object(
                'table',        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'dashboard_id', OLD.dashboard_id,
                'widget_id',    OLD.widget_id,
                'preset',       v_preset),
            NULL::uuid,
            VARIADIC ARRAY[COALESCE(v_widget::text, OLD.widget_id::text), v_preset]);
    END IF;
    RETURN OLD;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_dashboard_widget_guard_in_uso()
IS 'Rifiuta il DELETE dal pool di una dashboard (ui.dashboard_widget) di un widget che un preset di quella dashboard propone: E_UI_WIDGET_IN_USO (CONFLITTO_STATO), con il codice del widget e quelli dei preset nella frase. Si toglie prima il widget dai preset (o si cancella il preset). La FK composita fk_ui_dashboard_preset_widget_pool resta la rete. BEFORE DELETE FOR EACH ROW, fase a10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
