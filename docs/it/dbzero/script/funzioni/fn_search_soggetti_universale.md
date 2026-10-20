{% include-markdown "it/dbzero/script/manual/fn_search_soggetti_universale.md" %}
# ⚙️ Funzione `fn_search_soggetti_universale`

```sql
CREATE FUNCTION fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0, p_order_by text DEFAULT NULL::text, p_order_dir text DEFAULT 'ASC'::text)
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
  -- Riferimento tabella entita' da tipi_ruoli (nullable)
  v_entita_tabella    config.tipi_ruoli.entita_tabella%TYPE;
  -- Colonna codice nella tabella entita' (default 'codice')
  v_entita_colonna    config.tipi_ruoli.entita_colonna_codice%TYPE;
  -- Frammento SQL EXISTS dinamico (vuoto se nessuna tabella)
  v_exists_clause     text := '';
  -- Predicato della regola unica (fn_predicato_soggetto_ruolo_visibile)
  v_predicato         text;
  -- Colonne ordinabili (whitelist). ⚠️ Solo colonne SEMPLICI del
  --   soggetto: l'ordine e la pagina si decidono prima degli aggregati
  --   (rev 2026-10-10, D-2): utility_list non e' piu' ordinabile.
  c_allowed_order_cols constant text[] := ARRAY[
    'ragione_sociale_completa',
    'soggetto_codice',
    'id_fiscale_univoco'
  ];
  -- Colonna e direzione ordinamento effettivi
  v_order_col         text;
  v_order_dir         text;
  -- Frammento ORDER BY dinamico
  v_order_clause      text;
BEGIN
  -- =========================================================
  -- Il tipo ruolo e «chi si vede» (rev 2026-10-10, R-6, Q-2).
  --
  -- Il BB valida il tipo ruolo (NULL o <= 0, inesistente, non
  -- ricercabile) e rende il predicato della regola unica, lo
  -- stesso della verifica d'esistenza di fn_get_search_detail.
  -- ⚠️ Prima della guardia sul termine: l'ordine dei rifiuti
  --   resta quello di prima (ruolo, poi termine).
  -- =========================================================
  v_predicato := script.fn_predicato_soggetto_ruolo_visibile(p_tipo_ruolo_id, 'sr');

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
  -- ⚠️ `utility_list` ed `emittente_ragione_sociale` NON sono nella
  --   whitelist, ed e' voluto: sono aggregati che si calcolano solo
  --   per le righe della pagina (rev 2026-10-10). Ordinare per un
  --   aggregato vorrebbe calcolarlo su TUTTE le corrispondenze,
  --   cioe' il costo da cui il vecchio tetto di 10.000 proteggeva.
  --   utility_list era ordinabile fino al 2026-10-10: tolta per
  --   decisione di Tid (D-2), l'ordine di una lista concatenata di
  --   forniture dice poco e la fornitura si filtra nel dettaglio.
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
  -- Tie-breaker su soggetto_ruolo_id per ordinamento stabile: e' cio'
  -- che rende le pagine contigue (nessun soggetto ripetuto o saltato).
  -- Alias generico `r`: lo stesso ordine si applica alla pagina e al
  -- risultato finale.
  v_order_clause := format(
    'ORDER BY r.%I %s, r.soggetto_ruolo_id ASC',
    v_order_col, v_order_dir
  );

  -- Prepara pattern ILIKE con wildcards
  v_search_pattern := '%' || btrim(p_search_term) || '%';

  -- Recupera il riferimento alla tabella entita' per il tipo
  -- ruolo (ricerca sul codice dell'entita'). ⚠️ E' entita_tabella,
  -- non entita_esistenza: questa serve solo a cercare il codice.
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
  -- Query principale (rev 2026-10-10, brief-db-ricerca-universale-
  -- tetto-10000, strada B di Tid).
  --
  -- Prima: raccolta di AL MASSIMO 10.000 corrispondenze con un LIMIT
  -- senza ORDER BY, aggregati su tutte, poi conteggio, ordine e
  -- pagina su quelle. Oltre il tetto il totale era falso, la prima
  -- pagina non era la prima vera e le pagine potevano ripetere o
  -- saltare soggetti.
  -- Ora: conteggio, ordine e pagina sulle colonne SEMPLICI del
  -- soggetto (nessuna join pesante), su TUTTE le corrispondenze; gli
  -- aggregati (utility, emittenti) solo per le righe della pagina.
  -- La parte costosa non cresce con il numero di corrispondenze, e il
  -- tetto non ha piu' niente da proteggere: e' tolto.
  --
  -- $1 = p_tipo_ruolo_id, $2 = v_search_pattern,
  -- $3 = v_limit, $4 = v_offset
  -- =========================================================
  RETURN QUERY EXECUTE format('
    WITH r AS (
      -- Soggetti con il ruolo richiesto e il termine trovato.
      -- Cerca su ragione_sociale, id_fiscale, codice soggetto
      -- e codice entita'' (dinamico da tipi_ruoli.entita_tabella).
      -- Chi si vede: il predicato della regola unica
      -- (fn_predicato_soggetto_ruolo_visibile), lo stesso del
      -- dettaglio. Nessun tetto: qui ci sono solo colonne semplici.
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
        AND (
          s.ragione_sociale_completa ILIKE $2
          OR s.id_fiscale_univoco_cf_piva ILIKE $2
          OR s.codice ILIKE $2
          %s
        )
        AND %s
    ),
    paged AS (
      -- Conteggio di TUTTE le corrispondenze (la window si calcola
      -- prima del LIMIT), ordine e pagina. total_count conta soggetti.
      SELECT
        COUNT(*) OVER()  AS total_count,
        r.*
      FROM r
      %s
      LIMIT $3
      OFFSET $4
    )
    SELECT
      r.total_count,
      r.soggetto_id,
      r.soggetto_ruolo_id,
      r.tipo_ruolo_id,
      r.soggetto_codice,
      r.ragione_sociale_completa,
      r.id_fiscale_univoco,
      agg.utility_list,
      agg.emittente_ragione_sociale
    FROM paged r
      -- Gli aggregati, SOLO per le righe della pagina.
      -- ⭐ Un soggetto puo'' avere piu'' righe cliente (una per
      --   billing account), quindi piu'' emittenti: string_agg tiene
      --   la riga UNA e li elenca. La riga e'' un soggetto, e un
      --   soggetto non ha un emittente: il legame e'' transitivo via BA.
      -- ⚠️ La RLS di anagrafiche.clienti filtra QUI: un cliente fuori
      --   perimetro non entra, e quindi nemmeno il suo emittente. Chi
      --   ha in whitelist il solo A, su un soggetto cliente di A e di
      --   B, legge «A» e non «A, B».
      -- Nessuna riga cliente (ruoli non CL): i due aggregati sono NULL.
      LEFT JOIN LATERAL (
        SELECT
          string_agg(DISTINCT u.codice_interno, '', '' ORDER BY u.codice_interno)
            AS utility_list,
          string_agg(DISTINCT s_ef.ragione_sociale_completa::text, '', ''
                     ORDER BY s_ef.ragione_sociale_completa::text)
            AS emittente_ragione_sociale
        FROM anagrafiche.clienti cl
          LEFT JOIN config.utilities u
            ON u.id = cl.utility_id
          LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
            ON sr_ef.id = script.fn_get_ba_emittente_sr_id(cl.billing_account_id)
          LEFT JOIN anagrafiche.soggetti s_ef
            ON s_ef.id = sr_ef.soggetto_id
        WHERE cl.soggetto_ruolo_id = r.soggetto_ruolo_id
      ) agg ON true
    -- La join laterale non garantisce l''ordine: lo si riapplica.
    %s
  ', v_exists_clause, v_predicato, v_order_clause, v_order_clause)
  USING p_tipo_ruolo_id, v_search_pattern, v_limit, v_offset;
END;
$function$

COMMENT ON FUNCTION script.fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
IS 'Ricerca universale soggetti per tipo ruolo (livello 1). Cerca su ragione_sociale_completa, id_fiscale_univoco_cf_piva, codice soggetto e codice entita'' (config.tipi_ruoli.entita_tabella, che serve solo a questo). ⭐ Conteggio, ordine e pagina (rev 2026-10-10, brief-db-ricerca-universale-tetto-10000, strada B di Tid) si fanno sulle colonne semplici del soggetto, su TUTTE le corrispondenze: total_count e'' il totale vero e le pagine sono contigue (tie-breaker soggetto_ruolo_id). Gli aggregati utility_list ed emittente_ragione_sociale si calcolano solo per le righe della pagina. Nessun tetto: fino al 2026-10-10 un LIMIT 10000 senza ORDER BY rendeva falsi totale e pagine oltre il tetto. Ordinamento: p_order_by in whitelist (ragione_sociale_completa, soggetto_codice, id_fiscale_univoco; utility_list tolta il 2026-10-10, D-2: gli aggregati non sono ordinabili), p_order_dir ASC/DESC. Paginazione LIMIT/OFFSET, p_limit al massimo 200. ⭐ Chi si vede (rev 2026-10-10, brief-db-codici-non-trovato-email-e-permessi R-6): il filtro di riga e'' il predicato della regola unica script.fn_predicato_soggetto_ruolo_visibile, lo stesso della verifica d''esistenza di fn_get_search_detail — almeno una riga visibile della entita_esistenza del ruolo (CL clienti sotto la RLS, FO fornitori, VT vettori, BANK_B bank_branches), o il solo soggetto-ruolo per i ruoli che non ne hanno. Lo stato dell''entita'' non conta; nessun filtro su soggetti.attivo (il modello non ammette un soggetto-ruolo col soggetto spento). Tipo ruolo validato dal BB: NULL o <= 0 E_PARAMETRO_INVALIDO, inesistente E_TIPO_RUOLO_NON_TROVATO, non ricercabile E_TIPO_RUOLO_NON_RICERCABILE. ⭐ emittente_ragione_sociale: AGGREGATA (string_agg), una riga per soggetto, perche'' un soggetto non ha un emittente — il legame e'' transitivo via billing account. ⚠️ Elenca solo gli emittenti dei clienti che la RLS restituisce: chi ha in whitelist il solo A, su un soggetto cliente di A e di B, legge «A». NULL sui rami non-CL. SECURITY INVOKER: la RLS vale con l''identita'' di chi chiama.';
```

</div>

---
{% include-markdown "signature-core.md" %}
