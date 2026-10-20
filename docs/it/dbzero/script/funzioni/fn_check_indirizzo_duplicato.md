{% include-markdown "it/dbzero/script/manual/fn_check_indirizzo_duplicato.md" %}
# ⚙️ Funzione `fn_check_indirizzo_duplicato`

```sql
CREATE FUNCTION fn_check_indirizzo_duplicato(p_stradario_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying, p_stradario_generale_id integer, p_comune_id integer, p_codice_postale_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_indirizzo_duplicato(p_stradario_id integer DEFAULT NULL::integer, p_civico integer DEFAULT NULL::integer, p_estensione_civico character varying DEFAULT NULL::character varying, p_palazzina character varying DEFAULT NULL::character varying, p_scala character varying DEFAULT NULL::character varying, p_piano character varying DEFAULT NULL::character varying, p_interno character varying DEFAULT NULL::character varying, p_stradario_generale_id integer DEFAULT NULL::integer, p_comune_id integer DEFAULT NULL::integer, p_codice_postale_id integer DEFAULT NULL::integer)
 RETURNS TABLE(indirizzo_dettaglio_id bigint, indirizzo_normalizzato text, descrizione_comune character varying, exact_match boolean)
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    v_stradario_id  config.stradario.id%TYPE;
    v_via_norm      anagrafiche.indirizzi_dettaglio.via_norm%TYPE;
    v_norm          anagrafiche.indirizzi_dettaglio.indirizzo_normalizzato%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica esistenza indirizzo duplicato o simile.
    --   Due flussi di ingresso:
    --     A) p_stradario_id valorizzato: usa direttamente
    --     B) p_stradario_id NULL + p_stradario_generale_id
    --        + p_comune_id (+ opz. p_codice_postale_id):
    --        risolve stradario_id dalla tabella config.stradario
    --
    --   Costruisce la stringa normalizzata di ricerca tramite
    --   fn_build_indirizzo_normalizzato (unica source of truth),
    --   poi cerca match prefix su indirizzi_dettaglio.
    --
    -- Parametri civico (opzionali, entrambi i flussi):
    --   p_civico, p_estensione_civico, p_palazzina,
    --   p_scala, p_piano, p_interno
    --
    -- Parametri risoluzione (flusso B, se p_stradario_id NULL):
    --   p_stradario_generale_id: ID stradario_generale
    --   p_comune_id:             ID comune
    --   p_codice_postale_id:     ID codice postale (opzionale)
    --
    -- Ritorna:
    --   - indirizzo_dettaglio_id: ID del match trovato
    --   - indirizzo_normalizzato: stringa normalizzata del match
    --   - descrizione_comune: comune del match
    --   - exact_match: true se match esatto, false se solo prefix
    --
    -- Logica:
    --   1. Risolve stradario_id (diretto o da combinazione)
    --   2. Costruisce stringa normalizzata via fn_build_...
    --   3. Se civico fornito: cerca LIKE norm% (match civico)
    --   4. Se civico null: cerca LIKE via_norm% (qualsiasi civico)
    --   5. Ordina: exact_match DESC (esatti prima), max 5 righe
    -- =========================================================

    -- =============================================================
    -- Step 1: Risolvere stradario_id
    -- =============================================================

    IF p_stradario_id IS NOT NULL AND p_stradario_id > 0 THEN
        -- Flusso A: stradario_id fornito direttamente
        v_stradario_id := p_stradario_id;

    ELSIF p_stradario_generale_id IS NOT NULL AND p_comune_id IS NOT NULL THEN
        -- Flusso B: risolvi dalla combinazione
        IF p_codice_postale_id IS NOT NULL THEN
            -- Ricerca esatta: stradario_generale + comune + CAP
            SELECT s.id
              INTO v_stradario_id
              FROM config.stradario s
             WHERE s.stradario_generale_id = p_stradario_generale_id
               AND s.comune_id             = p_comune_id
               AND s.codice_postale_id     = p_codice_postale_id;
        ELSE
            -- Senza CAP: prendi il primo stradario per la combinazione
            SELECT s.id
              INTO v_stradario_id
              FROM config.stradario s
             WHERE s.stradario_generale_id = p_stradario_generale_id
               AND s.comune_id             = p_comune_id
             ORDER BY s.id
             LIMIT 1;
        END IF;

        -- Se non trovato: la via non esiste come stradario locale,
        -- nessun duplicato possibile
        IF v_stradario_id IS NULL THEN
            RETURN;
        END IF;

    ELSE
        -- Nessun criterio sufficiente: guard
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_indirizzo_duplicato',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_stradario_id', p_stradario_id,
                              'p_stradario_generale_id', p_stradario_generale_id,
                              'p_comune_id', p_comune_id),
            NULL::uuid,
            'Fornire p_stradario_id oppure p_stradario_generale_id + p_comune_id.'
        );
    END IF;

    -- =============================================================
    -- Step 2: Costruire stringa normalizzata di ricerca
    -- =============================================================

    SELECT (r).o_via_norm, (r).o_indirizzo_normalizzato
      INTO v_via_norm, v_norm
      FROM (SELECT anagrafiche.fn_build_indirizzo_normalizzato(
                v_stradario_id, p_civico, p_estensione_civico,
                p_palazzina, p_scala, p_piano, p_interno) AS r) x;

    -- Guard: stradario non trovato in vw_indirizzo_completo
    IF v_via_norm IS NULL THEN
        RETURN;
    END IF;

    -- =============================================================
    -- Step 3: Cerca match prefix su vw_indirizzi_dettaglio
    -- =============================================================

    RETURN QUERY
    SELECT
        vid.indirizzo_dettaglio_id,
        vid.indirizzo_normalizzato,
        vid.descrizione_comune,
        (vid.indirizzo_normalizzato = v_norm) AS exact_match
    FROM anagrafiche.vw_indirizzi_dettaglio vid
    WHERE vid.stradario_id = v_stradario_id
      AND vid.indirizzo_normalizzato LIKE
          CASE WHEN p_civico IS NOT NULL
               THEN v_norm
               ELSE v_via_norm
          END || '%'
    ORDER BY (vid.indirizzo_normalizzato = v_norm) DESC,
             vid.indirizzo_dettaglio_id
    LIMIT 5;

END;
$function$

COMMENT ON FUNCTION script.fn_check_indirizzo_duplicato(p_stradario_id integer, p_civico integer, p_estensione_civico character varying, p_palazzina character varying, p_scala character varying, p_piano character varying, p_interno character varying, p_stradario_generale_id integer, p_comune_id integer, p_codice_postale_id integer)
IS 'Check duplicato indirizzo con risoluzione stradario. Flusso A: p_stradario_id diretto. Flusso B: risolve da stradario_generale_id + comune_id + codice_postale_id. Usa fn_build_indirizzo_normalizzato, cerca match prefix con exact_match. STABLE, PARALLEL SAFE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
