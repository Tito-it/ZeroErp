{% include-markdown "it/dbzero/script/manual/fn_doc_passaggio.md" %}
# ⚙️ Funzione `fn_doc_passaggio`

```sql
CREATE FUNCTION fn_doc_passaggio(p_testata regclass, p_stato_da_id bigint, p_stato_a_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_passaggio(p_testata regclass, p_stato_da_id bigint, p_stato_a_id bigint)
 RETURNS TABLE(manuale boolean, azione_processo_codename character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Gli stati arrivano da uno qualunque dei vocabolari della
    -- mappa: bigint in tutti, nessuna colonna comune a cui
    -- ancorarli. I nomi vengono dalla mappa.
    v_matrice regclass;
    v_col_da  text;
    v_col_a   text;
    v_vivo    text;
    v_filtro  text;
BEGIN
    -- =========================================================
    -- Scopo: la riga viva della matrice per il passaggio
    --   (da, a) di una testata. Zero righe: il passaggio non e'
    --   nella matrice. manuale = false: passaggio di processo.
    -- =========================================================
    SELECT m.matrice, m.colonna_da, m.colonna_a, m.colonna_vivo, m.filtro
      INTO v_matrice, v_col_da, v_col_a, v_vivo, v_filtro
      FROM script.fn_doc_stato_modello(p_testata) m;

    IF v_matrice IS NULL
       OR NOT EXISTS (SELECT 1
                        FROM pg_catalog.pg_attribute a
                       WHERE a.attrelid = v_matrice
                         AND a.attname  = 'azione_processo_codename'
                         AND a.attnum   > 0
                         AND NOT a.attisdropped) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_doc_passaggio', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('testata', p_testata::text,
                               'matrice', v_matrice::text),
            NULL::uuid,
            'script.fn_doc_passaggio',
            'p_testata: una testata portata al modello del documento (matrice con azione_processo_codename)');
    END IF;

    RETURN QUERY EXECUTE format(
        'SELECT COALESCE((t.meta ->> ''manuale'')::boolean, true),'
        '       t.azione_processo_codename'
        '  FROM %s t'
        ' WHERE t.%I = $1 AND t.%I = $2 AND t.%I IS TRUE %s',
        v_matrice, v_col_da, v_col_a, v_vivo, v_filtro)
      USING p_stato_da_id, p_stato_a_id;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_passaggio(p_testata regclass, p_stato_da_id bigint, p_stato_a_id bigint)
IS 'BB del modello del documento: la riga VIVA della matrice di una testata per il passaggio (stato da, stato a), con manuale (false = passaggio di processo, lo fa un altro verbo: non si chiede a mano) e azione_processo_codename (l''azione che il passaggio chiede, NULL = basta il permesso sul documento). Zero righe: il passaggio non e'' nella matrice. Lettore unico per il verbo (script.fn_guard_passaggio), le capability (fn_available_actions_ddt / _reso) e il backend (403 prima della transazione). Testata fuori mappa o matrice senza la colonna dell''azione (documento non ancora portato al modello): E_SCRIPT_CHIAMATA_NON_VALIDA. Brief: brief-modello-documento-vendita §7 (M-3, S-2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
