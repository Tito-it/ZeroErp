{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts.md" %}
# ⚙️ Funzione `trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts`

```sql
CREATE FUNCTION trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: mantiene la coerenza tra preset_base_id e preset_base_data_update.
-- Quando preset_base_id diventa NULL (ON DELETE SET NULL o UPDATE diretto),
-- azzera anche preset_base_data_update: il timestamp e' relativo al preset
-- referenziato, senza preset non ha senso conservarlo.
BEGIN
  IF NEW.preset_base_id IS NULL AND OLD.preset_base_id IS NOT NULL THEN
    NEW.preset_base_data_update := NULL;
  END IF;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts()
IS 'Azzera preset_base_data_update quando preset_base_id -> NULL (ON DELETE SET NULL o UPDATE). Impedisce badge FE "preset aggiornato" su preset eliminato.';
```

---
{% include-markdown "signature-core.md" %}
