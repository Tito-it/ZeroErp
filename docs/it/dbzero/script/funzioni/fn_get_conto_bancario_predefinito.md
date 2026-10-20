{% include-markdown "it/dbzero/script/manual/fn_get_conto_bancario_predefinito.md" %}
# ⚙️ Funzione `fn_get_conto_bancario_predefinito`

```sql
CREATE FUNCTION fn_get_conto_bancario_predefinito(p_soggetto_ruolo_id bigint, p_uso character varying, p_istanza_utility_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_conto_bancario_predefinito(p_soggetto_ruolo_id bigint, p_uso character varying, p_istanza_utility_id bigint DEFAULT NULL::bigint)
 RETURNS anagrafiche.vw_conti_bancari_per_ruolo
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_res  anagrafiche.vw_conti_bancari_per_ruolo%ROWTYPE;
    v_uso  anagrafiche.soggetti_ruoli_conti_bancari.uso%TYPE
           := UPPER(TRIM(COALESCE(p_uso, 'GENERICO')));
BEGIN
    -- FASE A: uso richiesto

    -- 1) Ruolo + istanza specifica + uso richiesto
    IF p_istanza_utility_id IS NOT NULL THEN
        SELECT * INTO v_res
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
          AND v.uso = v_uso AND v.fonte = 'RUOLO'
          AND v.istanza_utility_id = p_istanza_utility_id
        ORDER BY v.predefinito DESC, v.data_update DESC
        LIMIT 1;
        IF v_res.soggetto_ruolo_id IS NOT NULL THEN RETURN v_res; END IF;
    END IF;

    -- 2) Ruolo + istanza NULL + uso richiesto
    SELECT * INTO v_res
    FROM anagrafiche.vw_conti_bancari_per_ruolo v
    WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
      AND v.uso = v_uso AND v.fonte = 'RUOLO'
      AND v.istanza_utility_id IS NULL
    ORDER BY v.predefinito DESC, v.data_update DESC
    LIMIT 1;
    IF v_res.soggetto_ruolo_id IS NOT NULL THEN RETURN v_res; END IF;

    -- 3) Soggetto + uso richiesto
    SELECT * INTO v_res
    FROM anagrafiche.vw_conti_bancari_per_ruolo v
    WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
      AND v.uso = v_uso AND v.fonte = 'SOGGETTO'
    ORDER BY v.predefinito DESC, v.data_update DESC
    LIMIT 1;
    IF v_res.soggetto_ruolo_id IS NOT NULL THEN RETURN v_res; END IF;

    -- FASE B: fallback a uso GENERICO
    IF v_uso <> 'GENERICO' THEN

        -- 4) Ruolo + istanza specifica + GENERICO
        IF p_istanza_utility_id IS NOT NULL THEN
            SELECT * INTO v_res
            FROM anagrafiche.vw_conti_bancari_per_ruolo v
            WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
              AND v.uso = 'GENERICO' AND v.fonte = 'RUOLO'
              AND v.istanza_utility_id = p_istanza_utility_id
            ORDER BY v.predefinito DESC, v.data_update DESC
            LIMIT 1;
            IF v_res.soggetto_ruolo_id IS NOT NULL THEN RETURN v_res; END IF;
        END IF;

        -- 5) Ruolo + istanza NULL + GENERICO
        SELECT * INTO v_res
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
          AND v.uso = 'GENERICO' AND v.fonte = 'RUOLO'
          AND v.istanza_utility_id IS NULL
        ORDER BY v.predefinito DESC, v.data_update DESC
        LIMIT 1;
        IF v_res.soggetto_ruolo_id IS NOT NULL THEN RETURN v_res; END IF;

        -- 6) Soggetto + GENERICO
        SELECT * INTO v_res
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
          AND v.uso = 'GENERICO' AND v.fonte = 'SOGGETTO'
        ORDER BY v.predefinito DESC, v.data_update DESC
        LIMIT 1;
        IF v_res.soggetto_ruolo_id IS NOT NULL THEN RETURN v_res; END IF;
    END IF;

    -- 7) Nessun conto trovato
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION script.fn_get_conto_bancario_predefinito(p_soggetto_ruolo_id bigint, p_uso character varying, p_istanza_utility_id bigint)
IS 'Selezione conto bancario con cascata 7 livelli (istanza_utility_id): ruolo+istanza+uso, ruolo+generico+uso, soggetto+uso, poi fallback GENERICO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
