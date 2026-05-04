{% include-markdown "it/dbzero/script/manual/fn_check_parameter_fk_surrogate.md" %}
# ⚙️ Funzione `fn_check_parameter_fk_surrogate`

```sql
CREATE FUNCTION fn_check_parameter_fk_surrogate(p_code text, p_value text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_parameter_fk_surrogate(p_code text, p_value text)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: check FK-surrogata generico per parametri.
-- Cerca un pattern abilitato in config.parameter_fk_surrogate
-- che matchi p_code (EXACT prioritario su LIKE), poi verifica
-- che p_value esista in <target_schema>.<target_table>.
-- <target_column> via SQL dinamico.
-- Ritorna true (passa) se: p_value NULL, o nessun pattern
-- matcha, o lookup trova il valore. Ritorna false solo se
-- pattern matcha E valore non esiste.
DECLARE
    v_target_schema text;
    v_target_table  text;
    v_target_column text;
    v_lookup_sql    text;
    v_found         boolean;
BEGIN
    IF p_value IS NULL THEN
        RETURN true;
    END IF;

    SELECT pfs.target_schema, pfs.target_table, pfs.target_column
      INTO v_target_schema, v_target_table, v_target_column
      FROM config.parameter_fk_surrogate pfs
     WHERE pfs.enabled
       AND (
              (pfs.match_mode = 'EXACT' AND pfs.code_pattern = p_code)
           OR (pfs.match_mode = 'LIKE'  AND p_code LIKE pfs.code_pattern)
       )
     ORDER BY (pfs.match_mode = 'EXACT') DESC, length(pfs.code_pattern) DESC
     LIMIT 1;

    IF v_target_schema IS NULL THEN
        -- Nessuna regola: code non soggetto a guard.
        RETURN true;
    END IF;

    v_lookup_sql := format(
        'SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = $1)',
        v_target_schema, v_target_table, v_target_column
    );
    EXECUTE v_lookup_sql INTO v_found USING p_value;
    RETURN v_found;
END;
$function$

COMMENT ON FUNCTION script.fn_check_parameter_fk_surrogate(p_code text, p_value text)
IS 'Check FK-surrogata generico per parametri. Lookup registry config.parameter_fk_surrogate (EXACT > LIKE), poi lookup dinamico sul target. Ritorna boolean. Usata dai dispatcher config.trgfn_parameters_fk_surrogate_dispatch e config.trgfn_parameter_overrides_fk_surrogate_dispatch.';
```

---
{% include-markdown "signature-core.md" %}
