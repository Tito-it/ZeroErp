{% include-markdown "it/dbzero/anagrafiche/manual/fn_search_indirizzi_dettaglio.md" %}
# ⚙️ Funzione `fn_search_indirizzi_dettaglio`

```sql
CREATE FUNCTION fn_search_indirizzi_dettaglio(p_stradario_id integer, p_civico integer, p_estensione_civico text, p_palazzina text, p_scala text, p_piano text, p_interno text, p_indirizzo_norm text, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_search_indirizzi_dettaglio(p_stradario_id integer DEFAULT NULL::integer, p_civico integer DEFAULT NULL::integer, p_estensione_civico text DEFAULT NULL::text, p_palazzina text DEFAULT NULL::text, p_scala text DEFAULT NULL::text, p_piano text DEFAULT NULL::text, p_interno text DEFAULT NULL::text, p_indirizzo_norm text DEFAULT NULL::text, p_limit integer DEFAULT 50)
 RETURNS SETOF anagrafiche.vw_indirizzi_dettaglio
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    v_limit integer := COALESCE(p_limit, 50);
    v_pattern text;
    v_stradario_id integer;
BEGIN

-- ============================================================
-- Funzione: anagrafiche.fn_search_indirizzi_dettaglio(...)
--
-- Parametri:
--   p_stradario_id      :: integer  (obbligatorio in alternativa a p_indirizzo_norm)
--   p_civico            :: integer  (opzionale, usato solo se p_stradario_id non null)
--   p_estensione_civico :: text     (opzionale)
--   p_palazzina         :: text     (opzionale)
--   p_scala             :: text     (opzionale)
--   p_piano             :: text     (opzionale)
--   p_interno           :: text     (opzionale)
--   p_indirizzo_norm    :: text     (opzionale, pattern fuzzy su indirizzo_normalizzato)
--   p_limit             :: integer  (limite massimo righe restituite, default 50)
--
-- Ritorno:
--   SETOF anagrafiche.vw_indirizzi_dettaglio
--
-- Regole:
--   - È obbligatorio valorizzare almeno uno tra:
--       * p_stradario_id
--       * p_indirizzo_norm (non vuoto)
--
--   - Se p_stradario_id è valorizzato:
--       * Filtra sempre per stradario_id
--       * Se specificati, restringe ulteriormente per:
--           civico, estensione_civico, palazzina, scala, piano, interno
--       
--
--   - Se p_stradario_id è NULL:
--       * Richiede p_indirizzo_norm non null/blank
--       * Esegue ricerca fuzzy solo su indirizzo_normalizzato
--
--   - Vengono restituiti solo indirizzi attivi (attivo = TRUE).
--   - Ordinamento predefinito per indirizzo_normalizzato, indirizzo_dettaglio_id.
-- ============================================================
    
    v_stradario_id := NULLIF(p_stradario_id, 0);

    -- Normalizzo il pattern (blank → NULL)
    IF p_indirizzo_norm IS NOT NULL and 
       v_stradario_id IS NULL  THEN
        v_pattern := NULLIF(btrim(p_indirizzo_norm), '');
    ELSE
        v_pattern := NULL;
    END IF;

    -- Almeno UNO tra v_stradario_id e v_pattern deve essere valorizzato
    IF v_stradario_id IS NULL AND v_pattern IS NULL THEN

        PERFORM script.fn_log_and_raise_error(
                         'database',
                         'fn_search_indirizzi_dettaglio',
                         'ERRORE_PARAMETRI',
                         jsonb_build_object(
                         'La funzione richiede parametri obbligatori. Indicare o p_stradario_id o p_indirizzo_norm '
                          , v_stradario_id), 
                          NULL,
                         'La funzione richiede parametri obbligatori. Indicare o p_stradario_id o p_indirizzo_norm '
                             );
    END IF;

    -- =======================================================
    -- Caso 1: v_stradario_id valorizzato
    --   → ricerca per indirizzo "fisico", con eventuale filtro fuzzy
    -- =======================================================
    IF v_stradario_id IS NOT NULL THEN
        RETURN QUERY
        SELECT *
        FROM anagrafiche.vw_indirizzi_dettaglio v
        WHERE
            v.attivo = TRUE
            AND v.stradario_id = p_stradario_id
            AND (p_civico IS NULL OR v.civico = p_civico)
            AND (p_estensione_civico IS NULL OR COALESCE(v.estensione_civico, '') = COALESCE(p_estensione_civico, ''))
            AND (p_palazzina IS NULL         OR COALESCE(v.palazzina,        '') = COALESCE(p_palazzina,        ''))
            AND (p_scala IS NULL             OR COALESCE(v.scala,            '') = COALESCE(p_scala,            ''))
            AND (p_piano IS NULL             OR COALESCE(v.piano,            '') = COALESCE(p_piano,            ''))
            AND (p_interno IS NULL           OR COALESCE(v.interno,          '') = COALESCE(p_interno,          ''))
            AND (
                v_pattern IS NULL
                OR UPPER(v.indirizzo_normalizzato) LIKE UPPER('%' || v_pattern || '%')
            )
        ORDER BY
            v.indirizzo_normalizzato,
            v.indirizzo_dettaglio_id
        LIMIT v_limit;

        RETURN;
    END IF;

    -- =======================================================
    -- Caso 2: v_stradario_id NULL, pattern valorizzato
    --   → ricerca SOLO per indirizzo_normalizzato (fuzzy)
    -- =======================================================
    RETURN QUERY
    SELECT *
    FROM anagrafiche.vw_indirizzi_dettaglio v
    WHERE
        v.attivo = TRUE
        AND UPPER(v.indirizzo_normalizzato) LIKE UPPER('%' || v_pattern || '%')
    ORDER BY
        v.indirizzo_normalizzato,
        v.indirizzo_dettaglio_id
    LIMIT v_limit;

    RETURN;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
