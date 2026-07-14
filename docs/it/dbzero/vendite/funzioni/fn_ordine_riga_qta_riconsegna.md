{% include-markdown "it/dbzero/vendite/manual/fn_ordine_riga_qta_riconsegna.md" %}
# ⚙️ Funzione `fn_ordine_riga_qta_riconsegna`

```sql
CREATE FUNCTION fn_ordine_riga_qta_riconsegna(p_ordine_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ordine_riga_qta_riconsegna(p_ordine_riga_id bigint)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: addendo reso del residuo per una riga ordine. Sigma
--   resi_righe.quantita (base) sui resi CONFERMATI di tipo
--   riapre_residuo=true collegati a quella riga ordine. Single
--   source per fn_ordine_ha_residuo_evasione e per il guard
--   fulfillment (coerenza formula residuo).
DECLARE
    v_qta numeric;
BEGIN
    IF p_ordine_riga_id IS NULL OR p_ordine_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_ordine_riga_qta_riconsegna','E_VALIDAZIONE',
            jsonb_build_object('p_ordine_riga_id', p_ordine_riga_id),
            NULL::uuid, 'p_ordine_riga_id deve essere > 0');
    END IF;

    SELECT COALESCE(SUM(rr.quantita), 0)
      INTO v_qta
      FROM vendite.resi_righe rr
      JOIN vendite.resi r          ON r.id = rr.reso_id
      JOIN config.stati_doc_reso s ON s.id = r.stato_doc_reso_id
      JOIN config.tipi_reso tr     ON tr.id = rr.tipo_reso_id
     WHERE rr.ordine_riga_id = p_ordine_riga_id
       AND s.codice_interno = 'CONFERMATO'
       AND tr.riapre_residuo IS TRUE;

    RETURN v_qta;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ordine_riga_qta_riconsegna(p_ordine_riga_id bigint)
IS 'Addendo reso del residuo per riga ordine: Sigma resi_righe.quantita (reso CONFERMATO, tipo riapre_residuo). Single source per fn_ordine_ha_residuo_evasione e trgfn_ordini_ful_guard_consistenza (coerenza formula). rev 2026-07-13.';
```

---
{% include-markdown "signature-core.md" %}
