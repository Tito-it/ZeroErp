{% include-markdown "it/dbzero/ui/manual/trgfn_preset_riga_tocca_preset.md" %}
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
-- Scopo: una composizione cambiata e' un cambio del preset. A fine
--   transazione si calcola l'impronta della composizione e, se e'
--   diversa da quella salvata, la si scrive sul preset: il trigger del
--   preset sposta la chiave colonne (o widget) della data del
--   contenuto. Una riscrittura uguale, anche in piu' istruzioni (un
--   DELETE seguito dall'INSERT delle stesse righe), non sposta niente.
--   TG_ARGV[0] = la tabella del preset (ui.lista_preset,
--   ui.dashboard_preset); la riga figlia porta preset_id.
-- Montaggio: CONSTRAINT TRIGGER AFTER INSERT OR UPDATE OR DELETE,
--   DEFERRABLE INITIALLY DEFERRED, FOR EACH ROW.
DECLARE
    -- regclass nudo: la tabella dei preset, dall'argomento
    v_tabella_preset regclass;
    -- text: 'lista' o 'dashboard', dalla tabella del preset
    v_famiglia       text;
    -- gli id dei preset toccati (ui.lista_preset.id e ui.dashboard_preset.id,
    -- integer tutti e due)
    v_preset_ids     ui.lista_preset.id%TYPE[];
    v_preset_id      ui.lista_preset.id%TYPE;
    v_impronta       ui.lista_preset.composizione_impronta%TYPE;
BEGIN
    v_tabella_preset := to_regclass(TG_ARGV[0]);
    v_famiglia := CASE v_tabella_preset
                      WHEN 'ui.lista_preset'::regclass     THEN 'lista'
                      WHEN 'ui.dashboard_preset'::regclass THEN 'dashboard'
                  END;
    IF v_famiglia IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'tgargs',    to_jsonb(TG_ARGV),
                'dettaglio', 'atteso ui.lista_preset o ui.dashboard_preset'),
            NULL::uuid,
            format('%s: atteso ui.lista_preset o ui.dashboard_preset', TG_NAME));
    END IF;

    -- Una riga riscritta uguale non e' un cambio.
    IF TG_OP = 'UPDATE' AND OLD IS NOT DISTINCT FROM NEW THEN
        RETURN NULL;
    END IF;

    v_preset_ids := CASE TG_OP
                        WHEN 'INSERT' THEN ARRAY[NEW.preset_id]
                        WHEN 'DELETE' THEN ARRAY[OLD.preset_id]
                        -- spostata su un altro preset: si guardano tutti e due
                        ELSE ARRAY[OLD.preset_id, NEW.preset_id]
                    END;

    FOREACH v_preset_id IN ARRAY v_preset_ids LOOP
        v_impronta := ui.fn_preset_impronta(v_famiglia, v_preset_id);
        -- Il preset cancellato (CASCADE) non c'e' piu': zero righe.
        IF v_famiglia = 'lista' THEN
            UPDATE ui.lista_preset
               SET composizione_impronta = v_impronta
             WHERE id = v_preset_id
               AND composizione_impronta IS DISTINCT FROM v_impronta;
        ELSE
            UPDATE ui.dashboard_preset
               SET composizione_impronta = v_impronta
             WHERE id = v_preset_id
               AND composizione_impronta IS DISTINCT FROM v_impronta;
        END IF;
    END LOOP;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preset_riga_tocca_preset()
IS 'Sulla composizione dei preset (ui.lista_preset_colonna, ui.dashboard_preset_widget; TG_ARGV[0] = la tabella del preset, ui.lista_preset o ui.dashboard_preset): a fine transazione calcola l''impronta della composizione (ui.fn_preset_impronta) e, se e'' diversa da composizione_impronta del preset, la scrive. Il trigger del preset (ui.trgfn_preset_contenuto_aggiornato) sposta allora la chiave colonne, o widget, di contenuto_aggiornato_il. Una riscrittura uguale non sposta niente, anche quando passa da un DELETE e da un INSERT separati. Una riga spostata su un altro preset guarda tutti e due; un preset cancellato non si tocca. CONSTRAINT TRIGGER AFTER INSERT OR UPDATE OR DELETE, DEFERRABLE INITIALLY DEFERRED, FOR EACH ROW: con SET CONSTRAINTS IMMEDIATE scatta a fine istruzione. Argomento fuori dai due: E_TRIGGER_ARGOMENTI_INVALIDI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
