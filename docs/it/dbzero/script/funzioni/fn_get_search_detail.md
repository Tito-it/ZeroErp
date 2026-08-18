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
 STABLE
AS $function$
DECLARE
  v_tipo_ruolo_codice  config.tipi_ruoli.codice_interno%TYPE;
  v_result             jsonb;
  -- Scope emittente EFFETTIVO (rev 2026-08-18, vedi sotto)
  v_scope              bigint[];
BEGIN
  IF p_soggetto_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'script.fn_get_search_detail', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_soggetto_id', 'valore', NULL),
      NULL::uuid, 'p_soggetto_id obbligatorio'
    );
  END IF;

  IF p_tipo_ruolo_id IS NULL OR p_tipo_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'script.fn_get_search_detail', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'p_tipo_ruolo_id', 'valore', p_tipo_ruolo_id),
      NULL::uuid, 'p_tipo_ruolo_id obbligatorio e > 0'
    );
  END IF;

  SELECT tr.codice_interno INTO v_tipo_ruolo_codice
  FROM config.tipi_ruoli tr
  WHERE tr.id = p_tipo_ruolo_id;

  IF v_tipo_ruolo_codice IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'script.fn_get_search_detail', 'E_TIPO_RUOLO_NON_TROVATO',
      jsonb_build_object('detail', 'tipo_ruolo_id non trovato in config.tipi_ruoli', 'p_tipo_ruolo_id', p_tipo_ruolo_id),
      NULL::uuid, p_tipo_ruolo_id::text
    );
  END IF;

  -- =========================================================
  -- Scope emittente EFFETTIVO (rev 2026-08-18, brief §11.6).
  --
  -- ⚠️ PRIMA il ramo CL scriveva:
  --     (p_emittente_ids IS NULL OR fn_check_ba_visible_...)
  --   cioe' NULL = passa tutto. E NULL e' cio' in cui Python
  --   appiattisce la lista vuota, che nella convenzione
  --   significa l'opposto: nessun accesso.
  --
  --   Ora lo scope lo risolve il database, dalla GUC, e
  --   p_emittente_ids puo' solo RESTRINGERE.
  --
  -- ⚠️ Il perimetro CL-only NON cambia ed e' preesistente: i
  --   rami FO e ELSE non hanno mai avuto un filtro emittente,
  --   perche' non hanno un billing account da cui derivarlo.
  --   Residuo dichiarato nel brief, non chiuso qui.
  -- =========================================================
  v_scope := script.fn_get_emittenti_scope_sr_effettivo(
               NULLIF(current_setting('app.current_user_id', true), '')::integer,
               p_emittente_ids
             );

  -- Dettaglio per codice_interno del tipo ruolo (immutabile).
  CASE v_tipo_ruolo_codice

  WHEN 'CL' THEN
    SELECT jsonb_build_object(
      'tipo_ruolo', v_tipo_ruolo_codice,
      'righe', COALESCE(jsonb_agg(row_detail ORDER BY row_detail->>'utility_codice_interno', row_detail->>'stato_descrizione'), '[]'::jsonb)
    ) INTO v_result
    FROM (
      SELECT jsonb_build_object(
        'cliente_id',             cl.id,
        'soggetto_ruolo_id',      cl.soggetto_ruolo_id,
        'codice',                 ba.codice,
        'istanza_codice',         iu.codice,
        'istanza_id',             iu.id,
        'utility_id',             u.id,
        'utility_codice_interno', u.codice_interno,
        'utility_codice',         u.codice,
        'utility_descrizione',    u.descrizione,
        'stato_cliente_id',       sc.id,
        'stato_codice_interno',   sc.codice_interno,
        'stato_descrizione',      sc.descrizione_breve,
        'stato_macro',            sc.codice,
        'indirizzo',              COALESCE(idv.indirizzo_normalizzato, fb_ind.indirizzo_completo, ''),
        'comune',                 COALESCE(idv.descrizione_comune, fb_ind.comune_descrizione, ''),
        'data_attivazione',       cl.data_attivazione,
        'data_sospensione',       cl.data_sospensione,
        'data_riattivazione',     cl.data_riattivazione,
        'data_chiusura',          cl.data_chiusura
      ) AS row_detail
      FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.clienti cl ON cl.soggetto_ruolo_id = sr.id
        JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
        LEFT JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
        LEFT JOIN anagrafiche.istanze_utilities iu ON iu.id = cl.istanza_utility_id
        LEFT JOIN config.utilities u ON u.id = cl.utility_id
        LEFT JOIN anagrafiche.vw_indirizzi_dettaglio idv ON idv.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
        LEFT JOIN LATERAL (
          SELECT gi.indirizzo_completo, gi.comune_descrizione
          FROM script.fn_get_indirizzo(sr.id, 'RES') gi
          LIMIT 1
        ) fb_ind ON iu.indirizzo_dettaglio_id IS NULL
      WHERE sr.soggetto_id = p_soggetto_id
        AND sr.tipo_ruolo_id = p_tipo_ruolo_id
        AND (p_utility_id IS NULL OR cl.utility_id = p_utility_id)
        AND (v_scope IS NULL
             OR script.fn_check_ba_visible_for_emittenti(cl.billing_account_id, v_scope))
    ) sub;

  WHEN 'FO' THEN
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
        'stato_descrizione',   CASE WHEN f.attivo THEN 'ATTIVO' ELSE 'INATTIVO' END,
        'indirizzo',           COALESCE(fb_ind.indirizzo_completo, ''),
        'comune',              COALESCE(fb_ind.comune_descrizione, '')
      ) AS row_detail
      FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.fornitori f ON f.soggetto_ruolo_id = sr.id
        LEFT JOIN LATERAL (
          SELECT gi.indirizzo_completo, gi.comune_descrizione
          FROM script.fn_get_indirizzo(sr.id, 'SEDEOP') gi
          LIMIT 1
        ) fb_ind ON true
      WHERE sr.soggetto_id = p_soggetto_id
        AND sr.tipo_ruolo_id = p_tipo_ruolo_id
    ) sub;

  ELSE
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
IS 'Dettaglio ricerca per tipo_ruolo (CASE su codice_interno). Branch CL: espone utility_codice_interno (codice_interno, logica) + utility_codice (codice, display) e stato_codice_interno (codice_interno); stato_macro = stati_cliente.codice. rev 2026-06-28 (naming stato). Rev 2026-08-18 (brief perimetro-emittente Q2/C): lo scope emittente si risolve QUI, dalla GUC app.current_user_id via fn_get_emittenti_scope_sr_effettivo. p_emittente_ids resta in firma ma puo'' solo RESTRINGERE. Prima il ramo CL scriveva «p_emittente_ids IS NULL OR ...», cioe'' NULL = passa tutto: e NULL e'' cio'' in cui Python appiattisce la lista vuota, che significa l''opposto. Rami FO/ELSE senza filtro emittente (perimetro preesistente: non hanno billing account). PARALLEL SAFE rimosso: la catena dello scope e'' STABLE e basta.';
```

---
{% include-markdown "signature-core.md" %}
