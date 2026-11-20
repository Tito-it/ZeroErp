{% include-markdown "it/dbzero/ui/manual/trgfn_preset_contenuto_aggiornato.md" %}
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
--   contenuto, per chiave: quella che il banner del preset
--   aggiornato confronta con lo snapshot della preferenza.
--   La scrive solo questo trigger; composizione_impronta la scrive
--   solo il trigger differito della composizione, col valore vero.
-- Montaggio: BEFORE INSERT OR UPDATE FOR EACH ROW, senza WHEN, sulle
--   due tabelle dei preset; la famiglia si legge dalla tabella.
-- ⚠️ Non e' l'audit (data_update): una riscrittura uguale (il mirror
--   del seed lo fa a ogni giro) non sposta niente.
DECLARE
    -- text: 'lista' o 'dashboard', dalla tabella; non il riflesso di una colonna
    v_famiglia text;
    -- jsonb nudo: la mappa chiave -> colonna della famiglia, scritta qui
    v_chiavi   jsonb;
    -- jsonb nudi: la riga vecchia e la nuova, per confrontare le colonne per nome
    v_old      jsonb;
    v_new      jsonb;
    v_mappa    ui.lista_preset.contenuto_aggiornato_il%TYPE;
    -- jsonb nudo: l'ora del cambio, una per riga, come valore di chiave
    v_ora      jsonb := to_jsonb(clock_timestamp());
BEGIN
    v_famiglia := CASE TG_RELID
                      WHEN 'ui.lista_preset'::regclass     THEN 'lista'
                      WHEN 'ui.dashboard_preset'::regclass THEN 'dashboard'
                  END;
    IF v_famiglia IS NULL OR TG_WHEN <> 'BEFORE' OR TG_LEVEL <> 'ROW'
       OR TG_OP NOT IN ('INSERT', 'UPDATE') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'dettaglio', 'atteso BEFORE INSERT OR UPDATE FOR EACH ROW su ui.lista_preset o ui.dashboard_preset'),
            NULL::uuid,
            format('%s: atteso BEFORE INSERT OR UPDATE FOR EACH ROW su ui.lista_preset o ui.dashboard_preset',
                   TG_NAME));
    END IF;

    v_chiavi := CASE v_famiglia
        WHEN 'lista' THEN jsonb_build_object(
            'colonne',           'composizione_impronta',
            'ordinamento',       'ordinamento_default',
            'filtri',            'filtri_default',
            'pagina_dimensione', 'pagina_dimensione')
        ELSE jsonb_build_object(
            'widget',            'composizione_impronta',
            'dimensione_max',    'dimensione_max')
    END;

    IF TG_OP = 'INSERT' THEN
        IF NEW.contenuto_aggiornato_il IS NOT NULL OR NEW.composizione_impronta IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'ui', TG_NAME::text, 'E_UI_PRESET_CONTENUTO_DERIVATO',
                jsonb_build_object(
                    'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                    'id',    NEW.id),
                NULL::uuid,
                NEW.codice::text);
        END IF;
        NEW.composizione_impronta := ui.fn_preset_impronta(v_famiglia, NEW.id);
        SELECT jsonb_object_agg(k, v_ora) INTO v_mappa
          FROM jsonb_object_keys(v_chiavi) AS k;
        NEW.contenuto_aggiornato_il := v_mappa;
        RETURN NEW;
    END IF;

    -- UPDATE: il lucchetto, sui valori (una riscrittura uguale passa).
    IF NEW.contenuto_aggiornato_il IS DISTINCT FROM OLD.contenuto_aggiornato_il
       OR (NEW.composizione_impronta IS DISTINCT FROM OLD.composizione_impronta
           AND NEW.composizione_impronta IS DISTINCT FROM ui.fn_preset_impronta(v_famiglia, NEW.id)) THEN
        PERFORM script.fn_log_and_raise_error(
            'ui', TG_NAME::text, 'E_UI_PRESET_CONTENUTO_DERIVATO',
            jsonb_build_object(
                'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',    NEW.id),
            NULL::uuid,
            NEW.codice::text);
    END IF;

    -- Si sposta la chiave il cui contenuto e' cambiato; le altre restano.
    v_old := to_jsonb(OLD);
    v_new := to_jsonb(NEW);
    SELECT OLD.contenuto_aggiornato_il
           || COALESCE(jsonb_object_agg(e.key, v_ora), '{}'::jsonb)
      INTO v_mappa
      FROM jsonb_each_text(v_chiavi) AS e
     WHERE (v_new -> e.value) IS DISTINCT FROM (v_old -> e.value);
    NEW.contenuto_aggiornato_il := v_mappa;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preset_contenuto_aggiornato()
IS 'Sui due preset (ui.lista_preset, ui.dashboard_preset) contenuto_aggiornato_il lo scrive solo il database: un oggetto {chiave: data}, la data dell''ultimo cambio del contenuto per chiave. Liste: colonne (composizione_impronta), ordinamento (ordinamento_default), filtri (filtri_default), pagina_dimensione. Dashboard: widget (composizione_impronta), dimensione_max. All''INSERT tutte le chiavi all''ora dell''INSERT e l''impronta della composizione (ui.fn_preset_impronta); all''UPDATE si sposta la chiave la cui colonna e'' cambiata, e una riscrittura uguale non sposta niente. L''ora e'' clock_timestamp(), non quella della transazione: un cambio successivo a uno snapshot nella stessa transazione risulta piu'' recente. Chi scrive la data, o un''impronta diversa da quella della composizione di oggi, riceve E_UI_PRESET_CONTENUTO_DERIVATO: l''impronta la scrive il trigger differito della composizione (ui.trgfn_preset_riga_tocca_preset). Non e'' l''audit: data_update si sposta anche per i campi che non sono contenuto. BEFORE INSERT OR UPDATE FOR EACH ROW, fase a20; montata altrove: E_TRIGGER_ARGOMENTI_INVALIDI.';
```

</div>

---
{% include-markdown "signature-core.md" %}
