# ⚙️ Funzione `trgfn_preset_riga_tocca_preset`

```sql
CREATE FUNCTION trgfn_preset_riga_tocca_preset()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_preset_riga_tocca_preset()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una riga di un preset aggiunta, tolta o cambiata e' un cambio
--   del preset: ne sposta data_update, la data che il flag
--   preset_aggiornato confronta con lo snapshot della preferenza.
--   TG_ARGV[0] = la tabella del preset (ui.lista_preset,
--   ui.dashboard_preset); la riga figlia porta preset_id.
-- ⚠️ Confronto sulla riga intera: le tabelle figlie non hanno audit.
DECLARE
    -- Tipo esplicito: %TYPE[] non e' sintassi PostgreSQL, e l'id viene da
    -- due tabelle (ui.lista_preset.id, ui.dashboard_preset.id, integer).
    v_preset_ids integer[];
BEGIN
    -- Una riscrittura uguale (il seed loadUpdateData lo fa a ogni giro)
    -- non e' un cambio.
    IF TG_OP = 'UPDATE' AND OLD IS NOT DISTINCT FROM NEW THEN
        RETURN NULL;
    END IF;

    v_preset_ids := CASE TG_OP
                        WHEN 'INSERT' THEN ARRAY[NEW.preset_id]
                        WHEN 'DELETE' THEN ARRAY[OLD.preset_id]
                        -- spostata su un altro preset: cambiano tutti e due
                        ELSE ARRAY[OLD.preset_id, NEW.preset_id]
                    END;

    -- Il padre cancellato (CASCADE) non c'e' piu': zero righe.
    EXECUTE format('UPDATE %s SET data_update = now() WHERE id = ANY ($1)',
                   TG_ARGV[0]::regclass)
      USING v_preset_ids;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preset_riga_tocca_preset()
IS 'Trigger AFTER INSERT OR UPDATE OR DELETE delle righe di un preset (ui.lista_preset_colonna, ui.dashboard_preset_widget): la riga aggiunta, tolta o cambiata sposta data_update del preset, la data che il flag preset_aggiornato dei resolver confronta con lo snapshot della preferenza. TG_ARGV[0] = la tabella del preset. Una riscrittura uguale (il seed loadUpdateData riscrive ogni riga a ogni giro) non tocca niente; una riga spostata su un altro preset tocca entrambi. Confronto sulla riga intera: le tabelle figlie non hanno colonne di audit. Richiesta BE/FE «preferenza di lista per chiave» (2026-11-01) §2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
