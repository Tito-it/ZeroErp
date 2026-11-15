{% include-markdown "it/dbzero/dbops/manual/fn_cleanup_at_regola.md" %}
# ⚙️ Funzione `fn_cleanup_at_regola`

```sql
CREATE FUNCTION fn_cleanup_at_regola(p_schema text, p_table text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_cleanup_at_regola(p_schema text, p_table text)
 RETURNS TABLE(regola_id bigint, ttl_days integer, base_ts_column text, apply_on_update boolean, motivo_salto text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_params dbops.automation_rules_tbl.params%TYPE;
    -- un nome di colonna, nessuna colonna lo porta
    v_base   text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La regola di scadenza di una tabella, una sola sede per i tre che la
    --   applicano: il trigger alla nascita (dbops.trgfn_cleanup_at_alla_nascita),
    --   il runner sul pregresso (dbops.fn_run_automations_cleanup) e chi ricalcola
    --   la scadenza da se' (script.fn_registra_tentativo_login).
    --
    -- Regole:
    --   - la regola e' la CLEANUP_AT abilitata piu' specifica che copre la tabella:
    --     priority, poi id; la *all vale se non c'e' niente di piu' specifico;
    --   - nessuna regola → nessuna riga: la tabella non scade;
    --   - una riga col motivo_salto valorizzato → la regola c'e' ma non si applica,
    --     e la tabella non scade:
    --       EXCLUDED               la tabella e' in automation_cleanup_exclusions;
    --       NO_CLEANUP_COLUMN      la tabella non ha la colonna cleanup_at;
    --       MISSING_BASE_TS_COLUMN la colonna base dichiarata non c'e', o non e'
    --                              dichiarata e la catena non ne trova nessuna;
    --   - la colonna base: base_ts_column della regola se dichiarata; se no la prima
    --     che la tabella ha fra data_insert, executed_at, occurred_at, created_at;
    --   - la scadenza si scrive in cleanup_at, nome fisso del framework.
    --
    -- ⚠️ Tutto qualificato: la chiama anche una funzione SECURITY DEFINER con
    --   search_path stretto (script.fn_registra_tentativo_login).
    -- =========================================================
    IF NULLIF(btrim(p_schema), '') IS NULL OR NULLIF(btrim(p_table), '') IS NULL THEN
        RETURN;
    END IF;

    SELECT r.id, r.params
      INTO regola_id, v_params
      FROM dbops.automation_rules_tbl r
     WHERE r.enabled
       AND r.rule_type = 'CLEANUP_AT'
       AND dbops.fn_schema_match(r.target_schema, p_schema)
       AND (r.target_table = '*all' OR p_table = r.target_table)
     ORDER BY r.priority, r.id
     LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- La forma dei params la garantisce chk_automation_rules_tbl_regola_valida:
    -- ttl_days intero >= 1, apply_on_update booleano.
    ttl_days        := (v_params ->> 'ttl_days')::integer;
    apply_on_update := COALESCE((v_params ->> 'apply_on_update')::boolean, false);
    v_base          := NULLIF(btrim(v_params ->> 'base_ts_column'), '');

    IF dbops.fn_cleanup_esclusa(p_schema, p_table) THEN
        motivo_salto := 'EXCLUDED';
    ELSIF NOT dbops.fn_col_exists(p_schema, p_table, 'cleanup_at') THEN
        motivo_salto := 'NO_CLEANUP_COLUMN';
    ELSIF v_base IS NOT NULL THEN
        base_ts_column := v_base;
        IF NOT dbops.fn_col_exists(p_schema, p_table, v_base) THEN
            motivo_salto := 'MISSING_BASE_TS_COLUMN';
        END IF;
    ELSE
        SELECT c.col
          INTO base_ts_column
          FROM unnest(ARRAY['data_insert', 'executed_at', 'occurred_at', 'created_at'])
               WITH ORDINALITY AS c(col, ord)
         WHERE dbops.fn_col_exists(p_schema, p_table, c.col)
         ORDER BY c.ord
         LIMIT 1;
        IF base_ts_column IS NULL THEN
            motivo_salto := 'MISSING_BASE_TS_COLUMN';
        END IF;
    END IF;

    RETURN NEXT;
END
$function$

COMMENT ON FUNCTION dbops.fn_cleanup_at_regola(p_schema text, p_table text)
IS 'La regola di scadenza (CLEANUP_AT) di una tabella, letta da chi scrive cleanup_at: dbops.trgfn_cleanup_at_alla_nascita all''INSERT, dbops.fn_run_automations_cleanup sul pregresso, script.fn_registra_tentativo_login a ogni fallimento. La regola e'' la CLEANUP_AT abilitata piu'' specifica di dbops.automation_rules_tbl (priority, poi id; la *all se non c''e'' altro). Nessuna riga = nessuna regola, la tabella non scade. Una riga con motivo_salto valorizzato = la regola c''e'' ma non si applica, e la tabella non scade: EXCLUDED (dbops.fn_cleanup_esclusa), NO_CLEANUP_COLUMN (manca cleanup_at), MISSING_BASE_TS_COLUMN (la colonna base dichiarata non c''e'', o non e'' dichiarata e la tabella non ha data_insert, executed_at, occurred_at ne'' created_at, la catena in quest''ordine). Colonne: regola_id, ttl_days, base_ts_column (quella dichiarata o quella della catena), apply_on_update (default false), motivo_salto. Schema o tabella vuoti: nessuna riga. La scadenza e'' base + ttl_days e sta in cleanup_at, nome fisso del framework.';
```

</div>

---
{% include-markdown "signature-core.md" %}
