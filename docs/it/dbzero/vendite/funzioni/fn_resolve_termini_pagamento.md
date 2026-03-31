# ⚙️ Funzione `fn_resolve_termini_pagamento`

```sql
CREATE FUNCTION fn_resolve_termini_pagamento(p_fattura_id bigint, p_billing_account_id bigint, p_attivita_ids bigint[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_termini_pagamento(p_fattura_id bigint DEFAULT NULL::bigint, p_billing_account_id bigint DEFAULT NULL::bigint, p_attivita_ids bigint[] DEFAULT NULL::bigint[])
 RETURNS TABLE(termini_pagamento_id bigint, termini_distinti bigint[])
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tp_fattura config.termini_pagamento.id%TYPE;
    v_tp_cliente config.termini_pagamento.id%TYPE;
    v_tp_default config.termini_pagamento.id%TYPE;
BEGIN
    -- Guard
    IF p_fattura_id IS NOT NULL AND p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_resolve_termini_pagamento', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id se fornito deve essere > 0');
    END IF;

    -- 1) Termine dalla fattura
    IF p_fattura_id IS NOT NULL THEN
        SELECT f.termini_pagamento_id INTO v_tp_fattura FROM vendite.fatture f WHERE f.id = p_fattura_id;
        IF v_tp_fattura IS NOT NULL THEN
            RETURN QUERY SELECT v_tp_fattura, ARRAY[v_tp_fattura]::BIGINT[];
            RETURN;
        END IF;
    END IF;

    -- 2) Termine dalla sorgente attivita'
    IF p_attivita_ids IS NOT NULL AND array_length(p_attivita_ids, 1) > 0 THEN
        RETURN QUERY
        WITH sorg AS (
            SELECT a.id, s.codice_interno AS src_code, a.sorgente_uid
              FROM vendite.attivita_fatturabili a
              JOIN config.sorgenti s ON s.id = a.sorgente_tipo_id
             WHERE a.id = ANY(p_attivita_ids)
        ), terms AS (
            SELECT DISTINCT CASE
                WHEN src.src_code = 'ORDINE_VENDITA' THEN o.termini_pagamento_id
                WHEN src.src_code = 'PREVENTIVO'     THEN p.termini_pagamento_id
                WHEN src.src_code = 'CONTRATTO'      THEN c.termini_pagamento_id
                ELSE NULL END AS tp_id
              FROM sorg src
              LEFT JOIN vendite.ordini     o ON (src.src_code='ORDINE_VENDITA' AND src.sorgente_uid = o.uid)
              LEFT JOIN vendite.preventivi p ON (src.src_code='PREVENTIVO'     AND src.sorgente_uid = p.uid)
              LEFT JOIN vendite.contratti  c ON (src.src_code='CONTRATTO'      AND src.sorgente_uid = c.uid)
        ), agg AS (
            SELECT ARRAY_REMOVE(ARRAY_AGG(DISTINCT tp_id), NULL) AS termini FROM terms
        )
        SELECT CASE WHEN array_length(agg.termini, 1) = 1 THEN agg.termini[1] ELSE NULL END, agg.termini FROM agg;
        RETURN;
    END IF;

    -- 3) Termine dal cliente (billing account)
    IF p_billing_account_id IS NOT NULL THEN
        SELECT cl.termine_pagamento_id INTO v_tp_cliente
          FROM anagrafiche.clienti cl
          JOIN anagrafiche.billing_account ba ON ba.id = p_billing_account_id
         WHERE cl.billing_account_id = ba.id LIMIT 1;
        IF v_tp_cliente IS NOT NULL THEN
            RETURN QUERY SELECT v_tp_cliente, ARRAY[v_tp_cliente]::BIGINT[];
            RETURN;
        END IF;
    END IF;

    -- 4) Default TP_1RATA
    SELECT tp.id INTO v_tp_default FROM config.termini_pagamento tp WHERE tp.codice_interno = 'TP_1RATA' AND tp.attivo IS TRUE LIMIT 1;
    RETURN QUERY SELECT v_tp_default, ARRAY_REMOVE(ARRAY[v_tp_default], NULL)::BIGINT[];
END;
$function$

COMMENT ON FUNCTION vendite.fn_resolve_termini_pagamento(p_fattura_id bigint, p_billing_account_id bigint, p_attivita_ids bigint[])
IS 'Risolve termini_pagamento: fattura → sorgente attivita → cliente → default TP_1RATA.';
```

---
{% include-markdown "signature-core.md" %}
