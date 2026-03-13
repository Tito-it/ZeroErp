{% include-markdown "it/dbzero/script/manual/fn_search_soggetti_universale.md" %}
# ⚙️ Funzione `fn_search_soggetti_universale`

```sql
CREATE FUNCTION fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_emittente_ids bigint[], p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_emittente_ids bigint[] DEFAULT NULL::bigint[], p_limit integer DEFAULT 50, p_offset integer DEFAULT 0, p_order_by text DEFAULT NULL::text, p_order_dir text DEFAULT 'ASC'::text)
 RETURNS TABLE(total_count bigint, soggetto_id uuid, soggetto_ruolo_id bigint, tipo_ruolo_id integer, soggetto_codice text, ragione_sociale_completa text, id_fiscale_univoco text, utility_list text)
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
  -- Pattern ILIKE costruito dal termine di ricerca
  v_search_pattern    text;
  -- Limiti paginazione normalizzati
  v_limit             integer := LEAST(COALESCE(p_limit, 50), 200);
  v_offset            integer := GREATEST(COALESCE(p_offset, 0), 0);
  -- Hard cap protegge da query troppo larghe
  c_hard_cap          constant integer := 10000;
  -- Riferimento tabella entita' da tipi_ruoli (nullable)
  v_entita_tabella    config.tipi_ruoli.entita_tabella%TYPE;
  -- Colonna codice nella tabella entita' (default 'codice')
  v_entita_colonna    text;
  -- Codice interno tipo ruolo (CL, FO, EF, ...)
  v_tipo_ruolo_codice config.tipi_ruoli.codice_interno%TYPE;
  -- Frammento SQL EXISTS dinamico (vuoto se nessuna tabella)
  v_exists_clause     text := '';
  -- Frammento SQL filtro emittente (vuoto se non CL o NULL)
  v_emittente_clause  text := '';
  -- Colonne ordinabili (whitelist)
  c_allowed_order_cols constant text[] := ARRAY[
    'ragione_sociale_completa',
    'soggetto_codice',
    'id_fiscale_univoco',
    'utility_list'
  ];
  -- Colonna e direzione ordinamento effettivi
  v_order_col         text;
  v_order_dir         text;
  -- Frammento ORDER BY dinamico
  v_order_clause      text;
BEGIN
  -- Guard: tipo ruolo obbligatorio e valido
  IF p_tipo_ruolo_id IS NULL OR p_tipo_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_search_soggetti_universale',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object(
        'parametro', 'p_tipo_ruolo_id',
        'valore', p_tipo_ruolo_id
      ),
      NULL::uuid,
      'p_tipo_ruolo_id obbligatorio e > 0'
    );
  END IF;

  -- Guard: termine ricerca minimo 3 caratteri
  IF p_search_term IS NULL OR length(btrim(p_search_term)) < 3 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_search_soggetti_universale',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object(
        'parametro', 'p_search_term',
        'valore', p_search_term,
        'minimo_caratteri', 3
      ),
      NULL::uuid,
      'p_search_term obbligatorio (minimo 3 caratteri)'
    );
  END IF;

  -- Validazione e normalizzazione ordinamento.
  -- p_order_by: se NULL usa default, se valorizzato deve essere
  -- nella whitelist c_allowed_order_cols.
  v_order_col := COALESCE(btrim(p_order_by), 'ragione_sociale_completa');

  IF NOT (v_order_col = ANY(c_allowed_order_cols)) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_search_soggetti_universale',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object(
        'parametro', 'p_order_by',
        'valore', p_order_by,
        'colonne_ammesse', to_jsonb(c_allowed_order_cols)
      ),
      NULL::uuid,
      concat('p_order_by non valido: ', p_order_by)
    );
  END IF;

  -- p_order_dir: normalizza a ASC o DESC, default ASC
  v_order_dir := CASE upper(btrim(COALESCE(p_order_dir, 'ASC')))
    WHEN 'DESC' THEN 'DESC'
    ELSE 'ASC'
  END;

  -- Costruisci frammento ORDER BY.
  -- %I quota il nome colonna (safe), direzione validata sopra.
  -- Tie-breaker su soggetto_ruolo_id per ordinamento stabile.
  v_order_clause := format(
    'ORDER BY wu.%I %s, wu.soggetto_ruolo_id ASC',
    v_order_col, v_order_dir
  );

  -- Prepara pattern ILIKE con wildcards
  v_search_pattern := '%' || btrim(p_search_term) || '%';

  -- Recupera codice_interno e riferimento tabella entita'
  -- per il tipo ruolo. codice_interno serve per sapere se
  -- applicare il filtro emittente (solo CL).
  SELECT tr.codice_interno,
         tr.entita_tabella,
         COALESCE(tr.entita_colonna_codice, 'codice')
    INTO v_tipo_ruolo_codice, v_entita_tabella, v_entita_colonna
  FROM config.tipi_ruoli tr
  WHERE tr.id = p_tipo_ruolo_id;

  -- Costruisci frammento EXISTS dinamico per ricerca codice.
  -- La tabella e' gia' validata dal trigger guard su tipi_ruoli
  -- (regclass valido, ha soggetto_ruolo_id, ha colonna codice).
  -- Usa %s per il nome tabella (validato) e %I per la colonna.
  IF v_entita_tabella IS NOT NULL THEN
    v_exists_clause := format(
      'OR EXISTS (SELECT 1 FROM %s e WHERE e.soggetto_ruolo_id = sr.id AND e.%I ILIKE $2)',
      v_entita_tabella::regclass,
      v_entita_colonna
    );
  END IF;

  -- Costruisci frammento filtro scope emittente.
  -- Si applica SOLO per tipo ruolo CL e SOLO se p_emittente_ids
  -- non e' NULL. La catena e':
  --   soggetti_ruoli.id → clienti.soggetto_ruolo_id
  --   → clienti.billing_account_id
  --   → emittenti_fiscali_billing_account.billing_account_id
  --   → emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id
  -- $5 = p_emittente_ids (passato via USING)
  IF v_tipo_ruolo_codice = 'CL' AND p_emittente_ids IS NOT NULL THEN
    v_emittente_clause := '
        AND EXISTS (
          SELECT 1
          FROM anagrafiche.clienti cl_scope
            JOIN anagrafiche.emittenti_fiscali_billing_account efba
              ON efba.billing_account_id = cl_scope.billing_account_id
          WHERE cl_scope.soggetto_ruolo_id = sr.id
            AND efba.emittente_soggetto_ruolo_id = ANY($5)
        )';
  END IF;

  -- Query principale con paginazione e conteggio totale.
  -- $1 = p_tipo_ruolo_id, $2 = v_search_pattern,
  -- $3 = v_limit, $4 = v_offset, $5 = p_emittente_ids
  RETURN QUERY EXECUTE format('
    WITH filtered AS (
      -- CTE 1: soggetti con ruolo richiesto e match sul termine.
      -- Cerca su ragione_sociale, id_fiscale, codice soggetto
      -- e codice entita'' (dinamico da tipi_ruoli.entita_tabella).
      -- Filtro scope emittente applicato solo per CL.
      SELECT
        s.id                             AS soggetto_id,
        sr.id                            AS soggetto_ruolo_id,
        sr.tipo_ruolo_id                 AS tipo_ruolo_id,
        s.codice                         AS soggetto_codice,
        s.ragione_sociale_completa       AS ragione_sociale_completa,
        s.id_fiscale_univoco_cf_piva     AS id_fiscale_univoco
      FROM anagrafiche.soggetti_ruoli sr
        JOIN anagrafiche.soggetti s
          ON s.id = sr.soggetto_id
      WHERE sr.tipo_ruolo_id = $1
        AND s.attivo = true
        AND (
          s.ragione_sociale_completa ILIKE $2
          OR s.id_fiscale_univoco_cf_piva ILIKE $2
          OR s.codice ILIKE $2
          %s
        )
        %s
      LIMIT %s
    ),
    with_utility AS (
      -- CTE 2: aggrega utility (codice_interno) per soggetti trovati.
      -- LEFT JOIN leggero, produce NULL per ruoli non-cliente.
      SELECT
        f.*,
        string_agg(DISTINCT u.codice_interno, '', '' ORDER BY u.codice_interno)
          AS utility_list
      FROM filtered f
        LEFT JOIN anagrafiche.clienti cl
          ON cl.soggetto_ruolo_id = f.soggetto_ruolo_id
        LEFT JOIN config.utilities u
          ON u.id = cl.utility_id
      GROUP BY
        f.soggetto_id, f.soggetto_ruolo_id, f.tipo_ruolo_id,
        f.soggetto_codice, f.ragione_sociale_completa,
        f.id_fiscale_univoco
    ),
    paged AS (
      -- CTE 3: paginazione con conteggio totale via window function.
      -- Ordinamento dinamico da v_order_clause.
      SELECT
        COUNT(*) OVER()  AS total_count,
        wu.*
      FROM with_utility wu
      %s
      LIMIT $3
      OFFSET $4
    )
    SELECT
      p.total_count,
      p.soggetto_id,
      p.soggetto_ruolo_id,
      p.tipo_ruolo_id,
      p.soggetto_codice,
      p.ragione_sociale_completa,
      p.id_fiscale_univoco,
      p.utility_list
    FROM paged p
  ', v_exists_clause, v_emittente_clause, c_hard_cap, v_order_clause)
  USING p_tipo_ruolo_id, v_search_pattern, v_limit, v_offset, p_emittente_ids;
END;
$function$

COMMENT ON FUNCTION script.fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_emittente_ids bigint[], p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
IS 'Ricerca universale soggetti per tipo ruolo (livello 1). Cerca su ragione_sociale_completa, id_fiscale_univoco_cf_piva, codice soggetto e codice entita'' dinamico. Filtro scope emittente (solo CL) via emittenti_fiscali_billing_account. Ordinamento dinamico: p_order_by (whitelist), p_order_dir (ASC/DESC). Paginazione LIMIT/OFFSET + COUNT(*) OVER(). Hard cap 10.000.';
```

---
{% include-markdown "signature-core.md" %}
