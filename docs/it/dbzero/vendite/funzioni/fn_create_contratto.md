{% include-markdown "it/dbzero/vendite/manual/fn_create_contratto.md" %}
# ⚙️ Funzione `fn_create_contratto`

```sql
CREATE FUNCTION fn_create_contratto(p_testata jsonb, p_utility jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_create_contratto(p_testata jsonb, p_utility jsonb DEFAULT NULL::jsonb)
 RETURNS TABLE(contratto_id bigint, numero character varying)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_numero       vendite.contratti.numero%TYPE;
    v_stato_id     vendite.contratti.stato_doc_contratto_id%TYPE;
    v_contratto_id vendite.contratti.id%TYPE;
    v_cols         text[];
    v_insert_cols  text;
    v_select_cols  text;
    v_sql          text;
    -- rev 2026-07-27: aggiunta 'fatturazione_immediata' (corsia di
    -- instradamento, Fase B brief emissione mirata). Va decisa PRIMA
    -- del push in commessa: in create e' il momento naturale, e senza
    -- questa voce la chiave veniva scartata in silenzio.
    v_testata_allowed text[] := ARRAY[
        'billing_account_id', 'emittente_fiscale_id', 'istanza_utility_id',
        'utility_id', 'ambito', 'valido_dal', 'valido_al',
        'parent_contratto_id', 'data', 'listino_id',
        'tipo_variazione_globale', 'valore_variazione_globale',
        'categoria_cliente_id_snapshot', 'valuta_id',
        'fatturazione_immediata', 'meta'
    ];
    v_util_allowed text[] := ARRAY[
        'istanza_utility_id', 'utility_id', 'istanza_dati_precontrattuali_id',
        'tipo_utenza_id', 'classe_utenza_id', 'param_1_num',
        'param_2_txt', 'meta'
    ];
BEGIN
    -- ----------------------------------------------------
    -- 1) Numero contratto (consuma il contatore; rolla con
    --    la funzione se un qualsiasi step successivo fallisce).
    -- ----------------------------------------------------
    v_numero := script.fn_generate_codice('contratto');

    -- 2) Stato iniziale DRAFT.
    SELECT s.id
      INTO v_stato_id
      FROM config.stati_doc_contratti s
     WHERE s.codice_interno = 'DRAFT';
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'vendite.fn_create_contratto',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_contratti.DRAFT'),
            NULL::uuid,
            VARIADIC ARRAY['stato iniziale DRAFT (config.stati_doc_contratti)']
        );
    END IF;

    -- ----------------------------------------------------
    -- 3) INSERT testata: solo chiavi whitelisted presenti
    --    (le assenti ereditano default/trigger DB).
    -- ----------------------------------------------------
    SELECT array_agg(quote_ident(key) ORDER BY key)
      INTO v_cols
      FROM jsonb_object_keys(COALESCE(p_testata, '{}'::jsonb)) AS key
     WHERE key = ANY(v_testata_allowed);

    v_insert_cols := COALESCE(', ' || array_to_string(v_cols, ', '), '');
    v_select_cols := COALESCE(
        ', ' || (SELECT string_agg('r.' || c, ', ' ORDER BY n)
                   FROM unnest(v_cols) WITH ORDINALITY AS u(c, n)),
        '');

    v_sql := format(
        'INSERT INTO vendite.contratti (numero, stato_doc_contratto_id%s) '
        'SELECT $1, $2%s '
        '  FROM jsonb_populate_record(NULL::vendite.contratti, $3) AS r '
        'RETURNING id',
        v_insert_cols, v_select_cols);
    EXECUTE v_sql
       INTO v_contratto_id
      USING v_numero, v_stato_id, COALESCE(p_testata, '{}'::jsonb);

    -- ----------------------------------------------------
    -- 4) INSERT utility opzionale.
    -- ----------------------------------------------------
    IF p_utility IS NOT NULL AND p_utility <> '{}'::jsonb THEN
        SELECT array_agg(quote_ident(key) ORDER BY key)
          INTO v_cols
          FROM jsonb_object_keys(p_utility) AS key
         WHERE key = ANY(v_util_allowed);

        v_insert_cols := COALESCE(', ' || array_to_string(v_cols, ', '), '');
        v_select_cols := COALESCE(
            ', ' || (SELECT string_agg('r.' || c, ', ' ORDER BY n)
                       FROM unnest(v_cols) WITH ORDINALITY AS u(c, n)),
            '');

        v_sql := format(
            'INSERT INTO vendite.contratti_utilities (contratto_id%s) '
            'SELECT $1%s '
            '  FROM jsonb_populate_record(NULL::vendite.contratti_utilities, $2) AS r',
            v_insert_cols, v_select_cols);
        EXECUTE v_sql USING v_contratto_id, p_utility;
    END IF;

    RETURN QUERY
    SELECT v_contratto_id, v_numero;
END;
$function$

COMMENT ON FUNCTION vendite.fn_create_contratto(p_testata jsonb, p_utility jsonb)
IS 'Funzione madre atomica: genera il numero, crea la testata contratto (stato DRAFT) e l''eventuale riga utility in un''unica statement (o tutto o rollback, contatore numero incluso). INSERT dinamico delle sole chiavi whitelisted presenti (rispetta i default DB). SECURITY INVOKER. Ritorna (contratto_id, numero). rev 2026-07-27: ''fatturazione_immediata'' aggiunta a v_testata_allowed — la corsia di instradamento si decide PRIMA del push in commessa e la create e'' il momento naturale; senza questa voce la chiave veniva scartata in silenzio. Il filtro e'' sulla PRESENZA della chiave: chiave assente = DEFAULT false, chiave = null = NOT NULL violation (il BE deve omettere o mandare un booleano, mai null). Piano: analisi-fix-transazioni Classe A #2 + brief-db-fatturazione-immediata-create-contratto.';
```

---
{% include-markdown "signature-core.md" %}
