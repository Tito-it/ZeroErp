{% include-markdown "it/dbzero/script/manual/fn_get_entita_ruolo_detail.md" %}
# ⚙️ Funzione `fn_get_entita_ruolo_detail`

```sql
CREATE FUNCTION fn_get_entita_ruolo_detail(p_soggetto_ruolo_id bigint, p_utility_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_entita_ruolo_detail(p_soggetto_ruolo_id bigint, p_utility_id integer DEFAULT NULL::integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    v_tipo_ruolo_codice  config.tipi_ruoli.codice_interno%TYPE;
    v_entita_tabella     config.tipi_ruoli.entita_tabella%TYPE;
    v_rel_oid            oid;
    v_result             jsonb;
    -- Colonne di sistema da escludere dal JSONB output.
    -- id viene escluso e reinserito come entita_id.
    -- soggetto_ruolo_id e' il filtro, non serve nell'output.
    c_exclude_cols       CONSTANT TEXT[] := ARRAY[
        'id', 'soggetto_ruolo_id',
        'data_insert', 'user_insert',
        'data_update', 'user_update',
        'tx_id', 'storicizza'
    ];
    -- Frammento SQL per filtro utility_id (vuoto se non applicabile)
    v_utility_filter     TEXT := '';
BEGIN
    -- Guard: parametro obbligatorio
    IF p_soggetto_ruolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_get_entita_ruolo_detail',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_soggetto_ruolo_id',
                'valore', NULL
            ),
            NULL::uuid,
            'p_soggetto_ruolo_id obbligatorio'
        );
    END IF;

    -- Recupera codice_interno e entita_tabella dal tipo ruolo
    SELECT tr.codice_interno, tr.entita_tabella
      INTO v_tipo_ruolo_codice, v_entita_tabella
      FROM anagrafiche.soggetti_ruoli sr
      JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
     WHERE sr.id = p_soggetto_ruolo_id;

    -- Guard: soggetto_ruolo_id deve esistere
    IF v_tipo_ruolo_codice IS NULL THEN
        -- Fix: E_GENERICO → E_CODICE
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_get_entita_ruolo_detail',
            'E_CODICE',
            jsonb_build_object('p_soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            p_soggetto_ruolo_id::text, 'anagrafiche.soggetti_ruoli'
        );
    END IF;

    IF v_entita_tabella IS NOT NULL THEN
        -- Query dinamica sulla tabella/vista entita'.
        -- to_jsonb(e.*) converte tutta la riga in JSONB,
        -- poi si strippano le colonne di sistema e id,
        -- e si aggiunge entita_id (= e.id originale).
        v_rel_oid := v_entita_tabella::regclass;

        -- Filtro opzionale per utility_id: attivo solo se
        -- la tabella ha la colonna utility_id e il parametro
        -- e' fornito (evita errore su tabelle senza utility_id)
        IF p_utility_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM pg_catalog.pg_attribute a
             WHERE a.attrelid = v_rel_oid
               AND a.attname  = 'utility_id'
               AND a.attnum   > 0
               AND NOT a.attisdropped
        ) THEN
            v_utility_filter := format(' AND e.utility_id = %s', p_utility_id);
        END IF;

        -- $1 = p_soggetto_ruolo_id
        -- $2 = v_tipo_ruolo_codice
        -- $3 = c_exclude_cols (text[] colonne da strippare)
        EXECUTE format('
            SELECT jsonb_build_object(
                ''tipo_ruolo'', $2,
                ''righe'', COALESCE(jsonb_agg(
                    (to_jsonb(e.*) - $3)
                    || jsonb_build_object(''entita_id'', e.id)
                ), ''[]''::jsonb)
            )
            FROM %s e
            WHERE e.soggetto_ruolo_id = $1
            %s
        ', v_rel_oid::regclass, v_utility_filter)
        INTO v_result
        USING p_soggetto_ruolo_id, v_tipo_ruolo_codice, c_exclude_cols;

    ELSE
        -- Nessuna tabella entita' per questo tipo ruolo:
        -- restituisce meta da soggetti_ruoli
        SELECT jsonb_build_object(
            'tipo_ruolo', v_tipo_ruolo_codice,
            'righe', jsonb_build_array(
                jsonb_build_object(
                    'soggetto_ruolo_id', sr.id,
                    'meta', COALESCE(sr.meta, '{}'::jsonb)
                )
            )
        ) INTO v_result
        FROM anagrafiche.soggetti_ruoli sr
        WHERE sr.id = p_soggetto_ruolo_id;

    END IF;

    RETURN COALESCE(v_result, jsonb_build_object('tipo_ruolo', v_tipo_ruolo_codice, 'righe', '[]'::jsonb));
END;
$function$

COMMENT ON FUNCTION script.fn_get_entita_ruolo_detail(p_soggetto_ruolo_id bigint, p_utility_id integer)
IS 'Dati entita'' per tipo ruolo in JSONB (query dinamica su entita_tabella). Strip colonne sistema, filtro utility_id opzionale. Se entita_tabella IS NULL → meta da soggetti_ruoli.';
```

</div>

---
{% include-markdown "signature-core.md" %}
