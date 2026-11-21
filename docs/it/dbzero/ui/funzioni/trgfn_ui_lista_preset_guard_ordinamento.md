{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_preset_guard_ordinamento.md" %}
# ⚙️ Funzione `trgfn_ui_lista_preset_guard_ordinamento`

```sql
CREATE FUNCTION trgfn_ui_lista_preset_guard_ordinamento()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_preset_guard_ordinamento()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: ordinamento_default del preset e' un elenco di {col, dir}, col il
--   codice di una colonna della lista, dir asc o desc.
DECLARE
    v_ord    ui.lista_preset.ordinamento_default%TYPE := NEW.ordinamento_default;
    -- jsonb: una voce dell'elenco, nel ciclo
    v_e      jsonb;
    -- text: il motivo del rifiuto, o NULL
    v_motivo text;
    -- i col gia' visti
    v_col    ui.lista_colonna.codice%TYPE;
    v_cols   ui.lista_colonna.codice%TYPE[] := ARRAY[]::varchar[];
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.ordinamento_default IS NOT DISTINCT FROM OLD.ordinamento_default
       AND NEW.lista_id IS NOT DISTINCT FROM OLD.lista_id THEN
        RETURN NEW;
    END IF;
    IF v_ord IS NULL THEN
        RETURN NEW;
    END IF;

    IF jsonb_typeof(v_ord) <> 'array' THEN
        v_motivo := 'non è un elenco';
    ELSE
        FOR v_e IN SELECT a.value FROM jsonb_array_elements(v_ord) AS a LOOP
            IF jsonb_typeof(v_e) <> 'object' THEN
                v_motivo := 'una voce non è un oggetto';
            ELSIF EXISTS (SELECT 1 FROM jsonb_object_keys(v_e) AS f(k)
                           WHERE f.k NOT IN ('col', 'dir')) THEN
                v_motivo := 'una voce ha chiavi diverse da col e dir';
            ELSIF jsonb_typeof(v_e -> 'col') IS DISTINCT FROM 'string' THEN
                v_motivo := 'una voce non ha col';
            ELSE
                v_col := v_e ->> 'col';
                IF v_col = ANY (v_cols) THEN
                    v_motivo := format('la colonna %s è ripetuta', v_col);
                ELSIF NOT EXISTS (SELECT 1 FROM ui.lista_colonna lc
                                   WHERE lc.lista_id = NEW.lista_id
                                     AND lc.codice   = v_col) THEN
                    v_motivo := format('%s non è il codice di una colonna della lista', v_col);
                ELSIF (v_e ->> 'dir') IS DISTINCT FROM 'asc'
                      AND (v_e ->> 'dir') IS DISTINCT FROM 'desc' THEN
                    v_motivo := format('la direzione di %s non è asc o desc', v_col);
                END IF;
                v_cols := array_append(v_cols, v_col);
            END IF;
            EXIT WHEN v_motivo IS NOT NULL;
        END LOOP;
    END IF;

    IF v_motivo IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'ui', TG_NAME::text, 'E_UI_CONFIGURAZIONE_FORMA',
            jsonb_build_object(
                'campo',  'ordinamento_default',
                'table',  TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',     NEW.id,
                'chiave', 'ordinamento_default',
                'motivo', v_motivo),
            NULL::uuid,
            VARIADIC ARRAY['ordinamento_default', v_motivo]);
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_preset_guard_ordinamento()
IS 'Il guard di ui.lista_preset.ordinamento_default: NULL passa; altrimenti un elenco di oggetti con le sole chiavi col e dir, col il codice di una colonna della lista (in qualsiasi stato) mai ripetuto, dir asc o desc. Un campo sorgente al posto del codice è rifiutato: nessuno lo traduce. Il rifiuto è E_UI_CONFIGURAZIONE_FORMA (DATO_ERRATO), campo = ordinamento_default, col motivo nella frase. Un UPDATE che non cambia né l''ordinamento né la lista passa senza giudizio. Montata BEFORE INSERT OR UPDATE OF ordinamento_default, lista_id, fase a10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
