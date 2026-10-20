{% include-markdown "it/dbzero/pratiche/manual/fn_calcola_tempo_netto_da_a.md" %}
# ⚙️ Funzione `fn_calcola_tempo_netto_da_a`

```sql
CREATE FUNCTION fn_calcola_tempo_netto_da_a(p_pratica_id bigint, p_flusso_da_id bigint, p_flusso_a_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_calcola_tempo_netto_da_a(p_pratica_id bigint, p_flusso_da_id bigint, p_flusso_a_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: calcola i giorni netti tra il completamento di flusso_da e
--   il completamento di flusso_a, sottraendo i giorni di sospensione.
-- Input: pratica_id, flusso_da_id, flusso_a_id
-- Output: giorni netti (INTEGER)
-- Se flusso_a non e' ancora COMPLETATO, usa NOW() come punto di arrivo.
DECLARE
    v_data_da   TIMESTAMPTZ;
    v_data_a    TIMESTAMPTZ;
    v_giorni_lordi    INTEGER;
    v_giorni_sosp     INTEGER := 0;
BEGIN
    -- Recupera data_fine del flusso_da
    SELECT data_fine INTO v_data_da
    FROM pratiche.flussi WHERE id = p_flusso_da_id;

    IF v_data_da IS NULL THEN
        RETURN NULL;  -- flusso_da non ancora completato
    END IF;

    -- Recupera data_fine del flusso_a (se completato)
    SELECT data_fine INTO v_data_a
    FROM pratiche.flussi WHERE id = p_flusso_a_id;

    -- Se flusso_a non completato, usa NOW()
    v_data_a := COALESCE(v_data_a, NOW());

    -- Giorni lordi
    v_giorni_lordi := GREATEST(0, EXTRACT(DAY FROM v_data_a - v_data_da)::INTEGER);

    -- Giorni di sospensione nel periodo da/a
    -- Conta i giorni di sospensione della pratica che ricadono nel periodo
    SELECT COALESCE(SUM(
        GREATEST(0, EXTRACT(DAY FROM
            LEAST(COALESCE(s.data_fine, NOW()), v_data_a)
            - GREATEST(s.data_inizio, v_data_da)
        )::INTEGER)
    ), 0)
    INTO v_giorni_sosp
    FROM pratiche.sospensioni s
    WHERE s.pratica_id = p_pratica_id
      AND s.flusso_id IS NULL  -- solo sospensioni a livello pratica
      AND s.data_inizio < v_data_a
      AND COALESCE(s.data_fine, NOW()) > v_data_da;

    RETURN GREATEST(0, v_giorni_lordi - v_giorni_sosp);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_calcola_tempo_netto_da_a(p_pratica_id bigint, p_flusso_da_id bigint, p_flusso_a_id bigint)
IS 'Check pura STABLE: giorni netti tra completamento flusso_da e flusso_a, al netto delle sospensioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
