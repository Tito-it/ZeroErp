# ⚙️ Funzione `trgfn_preset_data_update_contenuto`

```sql
CREATE FUNCTION trgfn_preset_data_update_contenuto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_preset_data_update_contenuto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: data_update di un preset (ui.lista_preset, ui.dashboard_preset)
--   e' la data dell'ultimo cambio del suo CONTENUTO, quella che il flag
--   preset_aggiornato confronta con lo snapshot della preferenza.
--   Quali colonne sono contenuto lo dice il WHEN del trigger, tabella
--   per tabella: qui si scrive soltanto la data.
-- ⚠️ Non e' l'audit: un UPDATE che riscrive la riga uguale (il seed
--   loadUpdateData lo fa a ogni giro) non sposta la data.
BEGIN
    NEW.data_update := now();
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preset_data_update_contenuto()
IS 'Trigger BEFORE UPDATE dei preset (ui.lista_preset, ui.dashboard_preset): data_update = now() quando cambia il CONTENUTO del preset. Le colonne di contenuto le dice il WHEN di ciascun trigger; la funzione scrive solo la data. Non e'' l''audit: una riscrittura uguale (il seed loadUpdateData riscrive ogni riga a ogni giro) non sposta la data, cosi'' il flag preset_aggiornato dei resolver si accende solo per un cambio vero. Le righe figlie la spostano col trigger ui.trgfn_preset_riga_tocca_preset. Richiesta BE/FE «preferenza di lista per chiave» (2026-11-01) §2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
