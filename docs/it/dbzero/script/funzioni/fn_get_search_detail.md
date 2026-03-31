{% include-markdown "it/dbzero/script/manual/fn_get_search_detail.md" %}
# ⚙️ Funzione `fn_get_search_detail`

```sql
CREATE FUNCTION fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer, p_emittente_ids bigint[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer DEFAULT NULL::integer, p_emittente_ids bigint[] DEFAULT NULL::bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    v_tipo_ruolo_codice  config.tipi_ruoli.codice_interno%TYPE;
    v_result             jsonb;
BEGIN
    -- Guard: soggetto obbligatorio
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_get_search_detail',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_soggetto_id',
                'valore', NULL
            ),
            NULL::uuid,
            'p_soggetto_id obbligatorio'
        );
    END IF;

    -- Guard: tipo ruolo obbligatorio e valido
    IF p_tipo_ruolo_id IS NULL OR p_tipo_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_get_search_detail',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_tipo_ruolo_id',
                'valore', p_tipo_ruolo_id
            ),
            NULL::uuid,
            'p_tipo_ruolo_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera codice_interno del tipo ruolo
    SELECT tr.codice_interno INTO v_tipo_ruolo_codice
      FROM config.tipi_ruoli tr
     WHERE tr.id = p_tipo_ruolo_id;

    IF v_tipo_ruolo_codice IS NULL THEN
        -- Fix: E_GENERICO → E_CODICE
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_get_search_detail',
            'E_CODICE',
            jsonb_build_object('p_tipo_ruolo_id', p_tipo_ruolo_id),
            NULL::uuid,
            p_tipo_ruolo_id::text, 'config.tipi_ruoli'
        );
    END IF;

    -- Costruisci dettaglio in base al codice_interno del tipo ruolo
    -- (codice_interno e' immutabile, protetto da trgfn_lock_columns)
    CASE v_tipo_ruolo_codice

    WHEN 'CL' THEN
        -- Righe cliente: per ogni cliente del soggetto_ruolo,
        -- istanza_utility + indirizzo + dati entita'.
        -- Indirizzo: da istanza_utility se presente, fallback fn_get_indirizzo RES.
        -- Filtro scope emittente: se p_emittente_ids IS NOT NULL,
        -- mostra solo clienti il cui billing_account e' collegato
        -- a un emittente autorizzato via emittenti_fiscali_billing_account.
        SELECT jsonb_build_object(
            'tipo_ruolo', v_tipo_ruolo_codice,
            'righe', COALESCE(jsonb_agg(row_detail ORDER BY row_detail->>'utility_codice', row_detail->>'stato_descrizione'), '[]'::jsonb)
        ) INTO v_result
        FROM (
            SELECT jsonb_build_object(
                'cliente_id',          cl.id,
                'soggetto_ruolo_id',   cl.soggetto_ruolo_id,
                'codice',              ba.codice,
                'istanza_codice',      iu.codice,
                'istanza_id',          iu.id,
                'utility_id',          u.id,
                'utility_codice',      u.codice_interno,
                'utility_descrizione', u.descrizione,
                'stato_cliente_id',    sc.id,
                'stato_codice',        sc.codice_interno,
                'stato_descrizione',   sc.descrizione_breve,
                'stato_macro',         sc.codice,
                'indirizzo',           COALESCE(
                                         idv.indirizzo_normalizzato,
                                         fb_ind.indirizzo_completo,
                                         ''
                                       ),
                'comune',              COALESCE(
                                         idv.descrizione_comune,
                                         fb_ind.comune_descrizione,
                                         ''
                                       ),
                'data_attivazione',    cl.data_attivazione,
                'data_sospensione',    cl.data_sospensione,
                'data_riattivazione',  cl.data_riattivazione,
                'data_chiusura',       cl.data_chiusura
            ) AS row_detail
            FROM anagrafiche.soggetti_ruoli sr
                JOIN anagrafiche.clienti cl
                  ON cl.soggetto_ruolo_id = sr.id
                JOIN config.stati_cliente sc
                  ON sc.id = cl.stato_cliente_id
                LEFT JOIN anagrafiche.billing_account ba
                  ON ba.id = cl.billing_account_id
                LEFT JOIN anagrafiche.istanze_utilities iu
                  ON iu.id = cl.istanza_utility_id
                LEFT JOIN config.utilities u
                  ON u.id = cl.utility_id
                LEFT JOIN anagrafiche.vw_indirizzi_dettaglio idv
                  ON idv.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
                -- Fallback indirizzo: fn_get_indirizzo(RES) con policy master/fallback
                LEFT JOIN LATERAL (
                    SELECT gi.indirizzo_completo, gi.comune_descrizione
                      FROM script.fn_get_indirizzo(sr.id, 'RES') gi
                     LIMIT 1
                ) fb_ind ON iu.indirizzo_dettaglio_id IS NULL
            WHERE sr.soggetto_id = p_soggetto_id
              AND sr.tipo_ruolo_id = p_tipo_ruolo_id
              AND (p_utility_id IS NULL OR cl.utility_id = p_utility_id)
              -- Filtro scope emittente
              AND (p_emittente_ids IS NULL OR EXISTS (
                  SELECT 1
                    FROM anagrafiche.emittenti_fiscali_billing_account efba
                   WHERE efba.billing_account_id = cl.billing_account_id
                     AND efba.emittente_soggetto_ruolo_id = ANY(p_emittente_ids)
              ))
        ) sub;

    WHEN 'FO' THEN
        -- Righe fornitore: stato da config.stati_fornitore + indirizzo sede operativa.
        SELECT jsonb_build_object(
            'tipo_ruolo', v_tipo_ruolo_codice,
            'righe', COALESCE(jsonb_agg(row_detail), '[]'::jsonb)
        ) INTO v_result
        FROM (
            SELECT jsonb_build_object(
                'fornitore_id',        f.id,
                'soggetto_ruolo_id',   f.soggetto_ruolo_id,
                'codice',              f.codice,
                'attivo',              f.attivo,
                'stato_fornitore_id',  sf.id,
                'stato_codice',        sf.codice_interno,
                'stato_descrizione',   sf.descrizione_breve,
                'stato_macro',         sf.codice,
                'blocca_ordini',       sf.blocca_ordini,
                'indirizzo',           COALESCE(fb_ind.indirizzo_completo, ''),
                'comune',              COALESCE(fb_ind.comune_descrizione, '')
            ) AS row_detail
            FROM anagrafiche.soggetti_ruoli sr
                JOIN anagrafiche.fornitori f
                  ON f.soggetto_ruolo_id = sr.id
                JOIN config.stati_fornitore sf
                  ON sf.id = f.stato_fornitore_id
                LEFT JOIN LATERAL (
                    SELECT gi.indirizzo_completo, gi.comune_descrizione
                      FROM script.fn_get_indirizzo(sr.id, 'SEDEOP') gi
                     LIMIT 1
                ) fb_ind ON true
            WHERE sr.soggetto_id = p_soggetto_id
              AND sr.tipo_ruolo_id = p_tipo_ruolo_id
        ) sub;

    ELSE
        -- Qualsiasi altro tipo ruolo: entita_detail + indirizzo residenza.
        SELECT jsonb_build_object(
            'tipo_ruolo', v_tipo_ruolo_codice,
            'entita_detail', script.fn_get_entita_ruolo_detail(sr.id, p_utility_id),
            'righe', jsonb_build_array(
                jsonb_build_object(
                    'soggetto_ruolo_id', sr.id,
                    'soggetto_id',       sr.soggetto_id,
                    'indirizzo',         COALESCE(fb_ind.indirizzo_completo, ''),
                    'comune',            COALESCE(fb_ind.comune_descrizione, '')
                )
            )
        ) INTO v_result
        FROM anagrafiche.soggetti_ruoli sr
            LEFT JOIN LATERAL (
                SELECT gi.indirizzo_completo, gi.comune_descrizione
                  FROM script.fn_get_indirizzo(sr.id, 'RES') gi
                 LIMIT 1
            ) fb_ind ON true
        WHERE sr.soggetto_id = p_soggetto_id
          AND sr.tipo_ruolo_id = p_tipo_ruolo_id;

    END CASE;

    RETURN COALESCE(v_result, jsonb_build_object('tipo_ruolo', v_tipo_ruolo_codice, 'righe', '[]'::jsonb));
END;
$function$

COMMENT ON FUNCTION script.fn_get_search_detail(p_soggetto_id uuid, p_tipo_ruolo_id integer, p_utility_id integer, p_emittente_ids bigint[])
IS 'Dettaglio soggetto per tipo ruolo (livello 2 ricerca universale). CL: istanza+utility+billing+stato+indirizzo+date+filtro emittente. FO: codice+stato_fornitore(config.stati_fornitore)+indirizzo SEDEOP. ELSE: entita_detail+indirizzo RES.';
```

---
{% include-markdown "signature-core.md" %}
