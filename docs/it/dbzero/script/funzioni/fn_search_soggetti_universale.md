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
  -- Frammento SQL filtro emittente (vuoto se non CL o scope aperto)
  v_emittente_clause  text := '';
  -- Scope emittente EFFETTIVO (rev 2026-08-18, vedi sotto)
  v_scope             bigint[];
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

  -- =========================================================
  -- Scope emittente EFFETTIVO (rev 2026-08-18, brief §11.6).
  --
  -- ⚠️ PRIMA questa funzione si fidava di p_emittente_ids: il
  --   filtro si accendeva su `p_emittente_ids IS NOT NULL`,
  --   quindi NULL voleva dire «nessuna restrizione». E NULL e'
  --   esattamente cio' in cui Python appiattisce la lista
  --   vuota — che nella convenzione significa l'opposto,
  --   «nessun accesso». I due estremi collassavano, e
  --   collassavano dalla parte che apre.
  --
  --   Ora lo scope lo risolve il database, dalla GUC, e
  --   p_emittente_ids puo' solo RESTRINGERE. Nessun valore
  --   passato dal chiamante puo' piu' allargare.
  --
  -- ⚠️ Il perimetro CL-only NON cambia ed e' preesistente: il
  --   filtro si applica solo al tipo ruolo CL, perche' e'
  --   l'unico che ha un billing account da cui derivare
  --   l'emittente. Non e' un difetto chiuso qui — e' un
  --   residuo dichiarato nel brief.
  -- =========================================================
  v_scope := script.fn_get_emittenti_scope_sr_effettivo(
               NULLIF(current_setting('app.current_user_id', true), '')::integer,
               p_emittente_ids
             );

  -- Costruisci frammento filtro scope emittente.
  -- Delega la logica a 3 livelli (mapping specifico, fallback
  -- default, non visibile) a script.fn_check_ba_visible_for_emittenti
  -- per evitare duplicazione con fn_get_search_detail.
  -- ⚠️ La condizione e' su v_scope, non su p_emittente_ids: con
  --   scope '{}' (nessun accesso) il filtro si ACCENDE e
  --   fn_check_ba_visible_for_emittenti risponde false per ogni
  --   BA -> zero risultati. Fail-closed.
  -- $5 = v_scope (passato via USING)
  IF v_tipo_ruolo_codice = 'CL' AND v_scope IS NOT NULL THEN
    v_emittente_clause := '
        AND EXISTS (
          SELECT 1
            FROM anagrafiche.clienti cl_scope
           WHERE cl_scope.soggetto_ruolo_id = sr.id
             AND script.fn_check_ba_visible_for_emittenti(
                   cl_scope.billing_account_id, $5
                 )
        )';
  END IF;

  -- Query principale con paginazione e conteggio totale.
  -- $1 = p_tipo_ruolo_id, $2 = v_search_pattern,
  -- $3 = v_limit, $4 = v_offset, $5 = v_scope
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
        LEFT JOIN anagrafiche.clienti cl
          ON cl.soggetto_ruolo_id = f.soggetto_ruolo_id
        LEFT JOIN config.utilities u
          ON u.id = cl.utility_id
        -- ⚠️ Il filtro sullo scope sta QUI, nella ON, e non e''
        --   ridondante col filtro di riga: la riga si vede se e''
        --   visibile per ALMENO un emittente autorizzato, ma la
        --   colonna deve elencare SOLO quelli autorizzati. Senza
        --   questa riga, un soggetto cliente di A e di B
        --   mostrerebbe «A, B» anche a chi ha in whitelist il
        --   solo A — rivelando l''esistenza di B. Con scope NULL
        --   (super admin) il filtro non morde: e'' il caso per
        --   cui la colonna e'' stata chiesta.
        LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
          ON sr_ef.id = script.fn_get_ba_emittente_sr_id(cl.billing_account_id)
         AND ($5::bigint[] IS NULL OR sr_ef.id = ANY($5::bigint[]))
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
  ', v_exists_clause, v_emittente_clause, c_hard_cap, v_order_clause)
  USING p_tipo_ruolo_id, v_search_pattern, v_limit, v_offset, v_scope;
END;
$function$

COMMENT ON FUNCTION script.fn_search_soggetti_universale(p_search_term text, p_tipo_ruolo_id integer, p_emittente_ids bigint[], p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
IS 'Ricerca universale soggetti per tipo ruolo (livello 1). Cerca su ragione_sociale_completa, id_fiscale_univoco_cf_piva, codice soggetto e codice entita'' dinamico. Ordinamento dinamico: p_order_by (whitelist), p_order_dir (ASC/DESC). Paginazione LIMIT/OFFSET + COUNT(*) OVER(). Hard cap 10.000. Rev 2026-08-18 (brief perimetro-emittente Q2/C): lo scope emittente si risolve QUI, dalla GUC app.current_user_id via fn_get_emittenti_scope_sr_effettivo. p_emittente_ids resta in firma ma puo'' solo RESTRINGERE: nessun valore passato dal chiamante puo'' allargare cio'' che la funzione mostra. Prima il filtro si accendeva su p_emittente_ids IS NOT NULL, quindi lo scope vuoto — in cui Python appiattisce [] — valeva «nessuna restrizione». Filtro applicato solo per tipo ruolo CL (unico con billing account): perimetro preesistente, non ampliato qui. PARALLEL SAFE rimosso: la catena dello scope e'' STABLE e basta. ⭐ Rev 2026-08-18 (R-5, Fase E): espone `emittente_ragione_sociale` in coda. AGGREGATA (string_agg), non moltiplicata: la riga resta UNA per soggetto perche'' un soggetto NON ha un emittente — il legame e'' transitivo via billing account (guide/soggetti-e-ruoli-anagrafici §5a-bis). Una riga per emittente spezzerebbe anche total_count, che conta soggetti. ⚠️ La colonna e'' FILTRATA dallo scope effettivo: chi ha in whitelist il solo A, su un soggetto cliente di A e di B legge «A», non «A, B» — una colonna nata per disambiguare non deve rivelare emittenti fuori perimetro. ⚠️ NULL sui rami non-CL: un fornitore non ha billing account, quindi non ha emittente. E'' la risposta giusta, non un buco. ⚠️ NON ordinabile: e'' un aggregato, ordinarci sopra ordinerebbe per la stringa concatenata.';
```

---
{% include-markdown "signature-core.md" %}
