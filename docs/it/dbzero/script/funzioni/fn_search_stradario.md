{% include-markdown "it/dbzero/script/manual/fn_search_stradario.md" %}
# ⚙️ Funzione `fn_search_stradario`

```sql
CREATE FUNCTION fn_search_stradario(p_comune_id integer, p_search text, p_limit integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_search_stradario(p_comune_id integer DEFAULT NULL::integer, p_search text DEFAULT NULL::text, p_limit integer DEFAULT 30)
 RETURNS TABLE(stradario_id integer, toponimo character varying, denominazione character varying, indirizzo_normalizzato text, comune_id integer, comune_descrizione character varying, provincia_sigla text, codice_postale_id integer, cap text)
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    v_search  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Ricerca vie (stradario) per autocomplete.
    --   L'utente seleziona un comune, poi cerca una via
    --   nel comune selezionato.
    --
    -- Parametri:
    --   p_comune_id: filtra per comune (caso principale)
    --   p_search:    testo ILIKE su indirizzo_normalizzato
    --   p_limit:     max righe (default 30)
    --
    -- Almeno uno tra p_comune_id e p_search obbligatorio.
    --
    -- JOIN:
    --   stradario -> stradario_generale -> toponomastica
    --   stradario -> comuni -> province
    --   stradario -> codici_postali
    --
    -- Performance:
    --   stradario_generale.indirizzo_normalizzato ha indice
    --   GIN trigram (ix_stradario_generale_norm_trgm).
    --   stradario.comune_id ha indice btree.
    -- =========================================================

    -- =============================================================
    -- Normalizzazione parametro ricerca
    -- =============================================================

    v_search := NULLIF(BTRIM(p_search), '');

    -- =============================================================
    -- Guard: almeno un criterio
    -- =============================================================

    IF p_comune_id IS NULL AND v_search IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_search_stradario',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_comune_id', p_comune_id,
                              'p_search', p_search),
            NULL::uuid,
            'Valorizzare almeno p_comune_id o p_search (non vuoto).'
        );
    END IF;

    -- =============================================================
    -- Guard: p_comune_id valido se fornito
    -- =============================================================

    IF p_comune_id IS NOT NULL AND p_comune_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_search_stradario',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_comune_id',
                              'valore', p_comune_id),
            NULL::uuid,
            'p_comune_id deve essere > 0.'
        );
    END IF;

    -- =============================================================
    -- Query principale
    -- Filtro toponomastica.attivo = true per escludere
    -- toponimi disattivati.
    --
    -- ⚠️ I due ::text non sono cosmetici: allineano il tipo
    --    della query a quello dichiarato in RETURNS TABLE.
    --    RETURN QUERY pretende corrispondenza esatta, non
    --    accetta la conversione implicita.
    -- =============================================================

    RETURN QUERY
    SELECT
        s.id                    AS stradario_id,
        t.descrizione           AS toponimo,
        sg.descrizione          AS denominazione,
        sg.indirizzo_normalizzato AS indirizzo_normalizzato,
        c.id                    AS comune_id,
        c.descrizione           AS comune_descrizione,
        p.sigla::text           AS provincia_sigla,
        cp.id                   AS codice_postale_id,
        cp.codice::text         AS cap
    FROM config.stradario s
    JOIN config.stradario_generale sg ON sg.id = s.stradario_generale_id
    JOIN config.toponomastica t       ON t.id  = sg.toponomastica_id
    JOIN config.comuni c              ON c.id  = s.comune_id
    LEFT JOIN config.province p       ON p.id  = c.provincia_id
    JOIN config.codici_postali cp     ON cp.id = s.codice_postale_id
    WHERE t.attivo = TRUE
      AND s.obsoleto_dal IS NULL          -- una via soppressa non si sceglie
      AND (p_comune_id IS NULL OR s.comune_id = p_comune_id)
      AND (v_search IS NULL
           OR sg.indirizzo_normalizzato ILIKE '%' || v_search || '%')
    ORDER BY sg.indirizzo_normalizzato, s.id
    LIMIT p_limit;

END;
$function$

COMMENT ON FUNCTION script.fn_search_stradario(p_comune_id integer, p_search text, p_limit integer)
IS 'Ricerca delle vie (config.stradario) per l''autocompletamento: per comune, per testo, o per entrambi. Restituisce solo le vie vive di una toponomastica attiva: una via soppressa (obsoleto_dal valorizzata, fusa in un''altra) non si sceglie per il nuovo. provincia_sigla e cap sono text esplicito, perche'' una firma a %TYPE si congelerebbe al tipo del giorno della CREATE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
