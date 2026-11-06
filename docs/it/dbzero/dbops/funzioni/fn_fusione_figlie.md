{% include-markdown "it/dbzero/dbops/manual/fn_fusione_figlie.md" %}
# ⚙️ Funzione `fn_fusione_figlie`

```sql
CREATE FUNCTION fn_fusione_figlie(p_padre regclass, p_porta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_fusione_figlie(p_padre regclass, p_porta text DEFAULT NULL::text)
 RETURNS TABLE(figlia regclass, vincolo name, colonne_fk name[], colonne_rif name[], chiave_padre name)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_chi    dbops.error_log.function_name%TYPE := COALESCE(p_porta, 'dbops.fn_fusione_figlie');
    v_chiave pg_catalog.pg_attribute.attname%TYPE;
    v_rls    regclass;
BEGIN
    IF p_padre IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_padre'),
            NULL::uuid,
            v_chi, 'manca la tabella da fondere');
    END IF;

    -- La chiave con cui si indicano origine e destinazione.
    SELECT a.attname
      INTO v_chiave
      FROM pg_catalog.pg_constraint c
      JOIN pg_catalog.pg_attribute a
        ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
     WHERE c.conrelid = p_padre
       AND c.contype = 'p'
       AND array_length(c.conkey, 1) = 1;
    IF v_chiave IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_padre', 'padre', dbops.fn_nome_qualificato(p_padre)),
            NULL::uuid,
            v_chi, format('%s non ha una chiave primaria di una colonna', dbops.fn_nome_qualificato(p_padre)));
    END IF;

    -- Una figlia che chi lancia vede solo in parte: ci si ferma prima.
    SELECT c.conrelid::regclass
      INTO v_rls
      FROM pg_catalog.pg_constraint c
     WHERE c.contype = 'f'
       AND c.confrelid = p_padre
       AND c.conparentid = 0
       AND row_security_active(c.conrelid)
     ORDER BY dbops.fn_nome_qualificato(c.conrelid::regclass)
     LIMIT 1;
    IF v_rls IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_MERGE_FIGLIA_SOTTO_RLS',
            jsonb_build_object('padre', dbops.fn_nome_qualificato(p_padre), 'figlia', dbops.fn_nome_qualificato(v_rls)),
            NULL::uuid,
            dbops.fn_nome_qualificato(v_rls));
    END IF;

    RETURN QUERY
    SELECT c.conrelid::regclass,
           c.conname,
           array_agg(af.attname ORDER BY k.ord),
           array_agg(ar.attname ORDER BY k.ord),
           v_chiave
      FROM pg_catalog.pg_constraint c
     CROSS JOIN LATERAL unnest(c.conkey, c.confkey) WITH ORDINALITY AS k(col, colrif, ord)
      JOIN pg_catalog.pg_attribute af
        ON af.attrelid = c.conrelid AND af.attnum = k.col
      JOIN pg_catalog.pg_attribute ar
        ON ar.attrelid = c.confrelid AND ar.attnum = k.colrif
     WHERE c.contype = 'f'
       AND c.confrelid = p_padre
       AND c.conparentid = 0
     GROUP BY c.conrelid, c.conname
     ORDER BY dbops.fn_nome_qualificato(c.conrelid::regclass), c.conname;
END;
$function$

COMMENT ON FUNCTION dbops.fn_fusione_figlie(p_padre regclass, p_porta text)
IS 'Le tabelle che riferiscono una riga della tabella data, lette dal catalogo: una riga per ogni chiave esterna dichiarata verso il padre (le copie sulle partizioni no), con le colonne della figlia e quelle del padre in coppia, nell''ordine del vincolo, e la chiave primaria del padre con cui si indicano origine e destinazione. E'' la sede unica di «chi va ripuntato» per le fusioni: la leggono dbops.fn_fusione_righe_doppie e dbops.fn_fusione_ripunta_figlie. Si ferma con E_DBOPS_CHIAMATA_NON_VALIDA se il padre manca o non ha una chiave primaria di una colonna, e con E_MERGE_FIGLIA_SOTTO_RLS se chi la lancia vede una figlia sotto RLS, perche'' la fusione lascerebbe sul padre le righe che non vede. p_porta e'' il nome della fusione che chiama, e compare nei messaggi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
