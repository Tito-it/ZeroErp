{% include-markdown "it/dbzero/ui/manual/trgfn_preferenza_preset_base_snapshot.md" %}
# ⚙️ Funzione `trgfn_preferenza_preset_base_snapshot`

```sql
CREATE FUNCTION trgfn_preferenza_preset_base_snapshot()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_preferenza_preset_base_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: lo snapshot del preset di base della preferenza lo scrive
--   il DB: la copia della data del contenuto per chiave del preset di
--   base ({chiave: data}), letta dalla tabella dei preset
--   (TG_ARGV[0]). Il valore che arriva da chi scrive non conta: ogni
--   scrittura che nomina preset_base_id o lo snapshot riallinea, ed e'
--   cosi' che si chiude il banner del preset aggiornato.
-- Montaggio: BEFORE INSERT OR UPDATE OF preset_base_id,
--   preset_base_contenuto_aggiornato_il FOR EACH ROW.
DECLARE
    -- regclass nudo: la tabella dei preset, dall'argomento
    v_tabella_preset regclass;
    v_contenuto      ui.lista_preset.contenuto_aggiornato_il%TYPE;
BEGIN
    v_tabella_preset := to_regclass(TG_ARGV[0]);
    IF v_tabella_preset IS NULL
       OR v_tabella_preset NOT IN ('ui.lista_preset'::regclass, 'ui.dashboard_preset'::regclass) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'tgargs',    to_jsonb(TG_ARGV),
                'dettaglio', 'atteso ui.lista_preset o ui.dashboard_preset'),
            NULL::uuid,
            format('%s: atteso ui.lista_preset o ui.dashboard_preset', TG_NAME));
    END IF;

    IF NEW.preset_base_id IS NULL THEN
        v_contenuto := NULL;
    ELSIF v_tabella_preset = 'ui.lista_preset'::regclass THEN
        SELECT lp.contenuto_aggiornato_il INTO v_contenuto
          FROM ui.lista_preset lp WHERE lp.id = NEW.preset_base_id;
    ELSE
        SELECT dp.contenuto_aggiornato_il INTO v_contenuto
          FROM ui.dashboard_preset dp WHERE dp.id = NEW.preset_base_id;
    END IF;

    NEW.preset_base_contenuto_aggiornato_il := v_contenuto;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preferenza_preset_base_snapshot()
IS 'Sulle due preferenze (ui.lista_preferenza_utente, ui.dashboard_preferenza_utente) lo snapshot del preset di base lo scrive il DB: preset_base_contenuto_aggiornato_il = la copia di contenuto_aggiornato_il del preset preset_base_id, un oggetto {chiave: data}, letta dalla tabella dei preset TG_ARGV[0] (ui.lista_preset o ui.dashboard_preset); NULL senza base. Il valore che arriva da chi scrive non conta: ogni scrittura che nomina preset_base_id o lo snapshot e'' un riallineamento, e riscrivere lo stesso preset_base_id e'' il modo di chiudere il banner del preset aggiornato (ui.fn_preset_aggiornato). BEFORE INSERT OR UPDATE OF preset_base_id, preset_base_contenuto_aggiornato_il FOR EACH ROW. Argomento fuori dai due: E_TRIGGER_ARGOMENTI_INVALIDI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
