{% include-markdown "it/dbzero/vendite/manual/fn_get_lotto_segnalazioni_summary.md" %}
# ⚙️ Funzione `fn_get_lotto_segnalazioni_summary`

```sql
CREATE FUNCTION fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
 RETURNS TABLE(fatture_critical_count bigint, fatture_warning_count bigint, lotto_critical_count bigint, lotto_warning_count bigint, lotto_info_count bigint, fatture_stato_esecuzione_errore_count bigint)
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Guard: parametro obbligatorio
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_lotto_segnalazioni_summary', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0'
        );
    END IF;

    RETURN QUERY
    WITH fatture_agg AS (
        SELECT COUNT(*) FILTER (WHERE fl.status = 'C') AS fc,
               COUNT(*) FILTER (WHERE fl.status = 'W') AS fw
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture_log fl ON fl.fattura_id = lf.fattura_id
         WHERE lf.lotto_id = p_lotto_id AND fl.disabilitato IS FALSE
    ),
    lotto_agg AS (
        SELECT COUNT(*) FILTER (WHERE ll.status = 'C') AS lc,
               COUNT(*) FILTER (WHERE ll.status = 'W') AS lw,
               COUNT(*) FILTER (WHERE ll.status = 'I') AS li
          FROM vendite.fatturazione_lotti_log ll
         WHERE ll.lotto_id = p_lotto_id AND ll.disabilitato IS FALSE
    ),
    ponte_agg AS (
        SELECT COUNT(*) FILTER (WHERE lf.stato_esecuzione = 'ERRORE') AS pe
          FROM vendite.fatturazione_lotti_fatture lf
         WHERE lf.lotto_id = p_lotto_id
    )
    SELECT COALESCE(fa.fc, 0), COALESCE(fa.fw, 0),
           COALESCE(la.lc, 0), COALESCE(la.lw, 0), COALESCE(la.li, 0),
           COALESCE(pa.pe, 0)
      FROM fatture_agg fa CROSS JOIN lotto_agg la CROSS JOIN ponte_agg pa;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
IS 'Riepilogo segnalazioni lotto attive (log fatture/lotto) + conteggio ponte errore.';
```

---
{% include-markdown "signature-core.md" %}
