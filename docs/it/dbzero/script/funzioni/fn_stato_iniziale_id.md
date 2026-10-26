# ⚙️ Funzione `fn_stato_iniziale_id`

```sql
CREATE FUNCTION fn_stato_iniziale_id(p_vocabolario regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_stato_iniziale_id(p_vocabolario regclass)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- l'id di uno stato di uno degli otto vocabolari: bigint in
    -- tutti, nessuna colonna comune a cui ancorarlo
    v_id bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'id dello stato in cui un documento nasce, letto dal
    --   suo vocabolario (colonna iniziale = true).
    --
    -- Regole:
    --   - vocabolario NULL o senza la colonna iniziale: il
    --     chiamante e' rotto, E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - nessuno stato iniziale dichiarato: NULL, decide il
    --     chiamante (al massimo uno lo garantisce l'indice
    --     unico parziale del vocabolario).
    -- =========================================================
    IF p_vocabolario IS NULL
       OR NOT EXISTS (SELECT 1
                        FROM pg_catalog.pg_attribute a
                       WHERE a.attrelid = p_vocabolario
                         AND a.attname = 'iniziale'
                         AND NOT a.attisdropped) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_stato_iniziale_id',
            'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('vocabolario', p_vocabolario::text),
            NULL::uuid,
            'script.fn_stato_iniziale_id',
            'il vocabolario degli stati e'' obbligatorio e deve dichiarare la colonna iniziale');
    END IF;

    EXECUTE format('SELECT s.id FROM %s s WHERE s.iniziale', p_vocabolario)
       INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_stato_iniziale_id(p_vocabolario regclass)
IS 'L''id dello stato in cui un documento nasce, letto dal suo vocabolario degli stati (colonna iniziale = true). Unica sede da cui leggerlo: nessuno scrive ''DRAFT'' o ''BOZZA'' per dire «lo stato in cui si nasce». NULL se il vocabolario non lo dichiara (decide il chiamante); vocabolario NULL o senza la colonna iniziale: E_SCRIPT_CHIAMATA_NON_VALIDA. Consumatori: script.trgfn_doc_stato_iniziale (il trigger della nascita), vendite.fn_push_preventivo_a_ordine (stato delle righe dell''ordine), dbops.fn_pgtap_porta_a_stato. Brief: brief-modello-documento-vendita §4-ter (N-1, P-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
