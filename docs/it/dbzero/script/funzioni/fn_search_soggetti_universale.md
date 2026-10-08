{% include-markdown "it/dbzero/script/manual/fn_search_soggetti_universale.md" %}
# ⚙️ Funzione `fn_search_soggetti_universale`

```sql
CREATE FUNCTION fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_emittente_ids bigint[], p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_emittente_ids bigint[] DEFAULT NULL::bigint[], p_limit integer DEFAULT 50, p_offset integer DEFAULT 0, p_order_by text DEFAULT NULL::text, p_order_dir text DEFAULT 'ASC'::text)
 RETURNS TABLE(total_count bigint, soggetto_id uuid, soggetto_ruolo_id bigint, tipo_ruolo_id integer, soggetto_codice text, ragione_sociale_completa text, id_fiscale_univoco text, utility_list text, emittente_ragione_sociale text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  -- ⚠️ Tipi espliciti DICHIARATI: pattern, paginazione e frammenti
  --   di SQL dinamico sono valori di lavoro, nessuna colonna di cui
  --   siano il riflesso. Ancorate le due che leggono tipi_ruoli.
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
  v_entita_colonna    config.tipi_ruoli.entita_colonna_codice%TYPE;
  -- Frammento SQL EXISTS dinamico (vuoto se nessuna tabella)
  v_exists_clause     text := '';
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
  -- ⚠️ `emittente_ragione_sociale` NON e' nella whitelist, ed e'
  --   voluto: e' un aggregato (string_agg su piu' billing
  --   account) e ordinarci sopra ordinerebbe per la stringa
  --   concatenata, non per emittente. Se un giorno servira'
  --   ordinare, sara' una decisione di merito — non un'aggiunta
  --   meccanica alla lista.
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

  -- Recupera il riferimento alla tabella entita' per il tipo
  -- ruolo (ricerca sul codice dell'entita').
  SELECT tr.entita_tabella,
         COALESCE(tr.entita_colonna_codice, 'codice')
    INTO v_entita_tabella, v_entita_colonna
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

  -- =========================================================
  -- Perimetro (rev 2026-10-08, R-4).
  --
  -- Il filtro di riga e' script.fn_check_soggetto_ruolo_visibile,
  -- la STESSA check della verifica d'esistenza di
  -- fn_get_search_detail: per CL almeno un cliente restituito
  -- dalla RLS di anagrafiche.clienti, per gli altri ruoli vera.
  -- ⚠️ Fino al 2026-10-08 qui c'era un filtro a mano sullo scope
  --   emittente (fn_get_emittenti_scope_sr_effettivo +
  --   fn_check_ba_visible_for_emittenti, rev 2026-08-18), scritto
  --   quando clienti non aveva RLS: una seconda copia della
  --   regola della policy. p_emittente_ids, che poteva solo
  --   restringere, non e' piu' letto.
  -- =========================================================

  -- Query principale con paginazione e conteggio totale.
  -- $1 = p_tipo_ruolo_id, $2 = v_search_pattern,
  -- $3 = v_limit, $4 = v_offset
  RETURN QUERY EXECUTE format('
    WITH filtered AS (
      -- CTE 1: soggetti con ruolo richiesto e match sul termine.
      -- Cerca su ragione_sociale, id_fiscale, codice soggetto
      -- e codice entita'' (dinamico da tipi_ruoli.entita_tabella).
      -- Perimetro: fn_check_soggetto_ruolo_visibile (RLS per CL).
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
        AND script.fn_check_soggetto_ruolo_visibile(sr.id)
      LIMIT %s
    ),
    with_utility AS (
      -- CTE 2: aggrega utility (codice_interno) per soggetti trovati.
      -- LEFT JOIN leggero, produce NULL per ruoli non-cliente.
      --
      -- ⭐ R-5: nello STESSO giro si aggrega anche l''emittente.
      --   Un soggetto puo'' avere piu'' righe cliente (una per
      --   billing account), quindi piu'' emittenti: string_agg
      --   tiene la riga UNA e li elenca. E'' l''opzione A del
      --   brief — la riga e'' un soggetto, e un soggetto non ha
      --   un emittente: il legame e'' transitivo via BA.
      SELECT
        f.*,
        string_agg(DISTINCT u.codice_interno, '', '' ORDER BY u.codice_interno)
          AS utility_list,
        string_agg(DISTINCT s_ef.ragione_sociale_completa::text, '', ''
                   ORDER BY s_ef.ragione_sociale_completa::text)
          AS emittente_ragione_sociale
      FROM filtered f
        -- ⚠️ La RLS di anagrafiche.clienti filtra QUI la join
        --   (rev 2026-10-08): un cliente fuori perimetro non entra,
        --   e quindi nemmeno il suo emittente. Chi ha in whitelist
        --   il solo A, su un soggetto cliente di A e di B, legge
        --   «A» e non «A, B»: la colonna non rivela emittenti fuori
        --   perimetro. Fino al 2026-10-08 lo diceva una condizione
        --   sullo scope nella ON di sr_ef, seconda copia della
        --   policy; e'' caduta.
        LEFT JOIN anagrafiche.clienti cl
          ON cl.soggetto_ruolo_id = f.soggetto_ruolo_id
        LEFT JOIN config.utilities u
          ON u.id = cl.utility_id
        LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
          ON sr_ef.id = script.fn_get_ba_emittente_sr_id(cl.billing_account_id)
        LEFT JOIN anagrafiche.soggetti s_ef
          ON s_ef.id = sr_ef.soggetto_id
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
      p.utility_list,
      p.emittente_ragione_sociale
    FROM paged p
  ', v_exists_clause, c_hard_cap, v_order_clause)
  USING p_tipo_ruolo_id, v_search_pattern, v_limit, v_offset;
END;
$function$

COMMENT ON FUNCTION script.fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_emittente_ids bigint[], p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
IS 'Ricerca universale soggetti per tipo ruolo (livello 1). Cerca su ragione_sociale_completa, id_fiscale_univoco_cf_piva, codice soggetto e codice entita'' dinamico. Ordinamento dinamico: p_order_by (whitelist), p_order_dir (ASC/DESC). Paginazione LIMIT/OFFSET + COUNT(*) OVER(). Hard cap 10.000. ⭐ Perimetro (rev 2026-10-08, brief-db-codici-non-trovato-email-e-permessi R-4): il filtro di riga e'' script.fn_check_soggetto_ruolo_visibile, la stessa check della verifica d''esistenza di fn_get_search_detail — per CL almeno un cliente restituito dalla RLS di anagrafiche.clienti, per gli altri ruoli nessun perimetro (soggetti, soggetti_ruoli e fornitori non portano un emittente nel modello: scelta di modello). Lista e dettaglio non possono dissentire su chi si vede; un soggetto-ruolo CL senza nessun cliente non compare a nessuno. Fino al 2026-10-08 un filtro a mano sullo scope emittente (rev 2026-08-18), seconda copia della policy, scritto quando clienti non aveva RLS. ⚠️ p_emittente_ids SUPERATO dal 2026-10-08: resta in firma e non e'' letto, il ritiro lo decide Tid col backend. ⭐ emittente_ragione_sociale in coda (R-5, 2026-08-18): AGGREGATA (string_agg), una riga per soggetto, perche'' un soggetto non ha un emittente — il legame e'' transitivo via billing account; total_count conta soggetti. ⚠️ La colonna elenca solo gli emittenti dei clienti che la RLS restituisce: chi ha in whitelist il solo A, su un soggetto cliente di A e di B, legge «A». NULL sui rami non-CL (un fornitore non ha billing account). NON ordinabile: e'' un aggregato. SECURITY INVOKER: la RLS vale con l''identita'' di chi chiama.';
```

---
{% include-markdown "signature-core.md" %}
