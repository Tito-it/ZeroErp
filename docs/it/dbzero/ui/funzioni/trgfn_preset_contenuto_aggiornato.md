# ⚙️ Funzione `trgfn_preset_contenuto_aggiornato`

```sql
CREATE FUNCTION trgfn_preset_contenuto_aggiornato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_preset_contenuto_aggiornato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: contenuto_aggiornato_il di un preset (ui.lista_preset,
--   ui.dashboard_preset) e' la data dell'ultimo cambio del suo
--   CONTENUTO, quella che il flag preset_aggiornato confronta con lo
--   snapshot della preferenza.
--   Quali colonne sono contenuto lo dice il WHEN del trigger, tabella
--   per tabella: qui si scrive soltanto la data.
-- ⚠️ Non e' l'audit (data_update, trigger del framework): un UPDATE
--   che riscrive la riga uguale (il seed loadUpdateData lo fa a ogni
--   giro) non sposta la data.
BEGIN
    NEW.contenuto_aggiornato_il := now();
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preset_contenuto_aggiornato()
IS 'Trigger BEFORE UPDATE dei preset (ui.lista_preset, ui.dashboard_preset): contenuto_aggiornato_il = now() quando cambia il CONTENUTO del preset. Le colonne di contenuto le dice il WHEN di ciascun trigger (a20). Non e'' l''audit: data_update la scrive il trigger del framework.';
```

</div>

---
{% include-markdown "signature-core.md" %}
