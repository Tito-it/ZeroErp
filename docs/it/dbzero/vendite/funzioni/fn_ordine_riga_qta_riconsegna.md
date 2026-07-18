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
--   quantita (base) delle righe reso EFFETTIVE (vw_resi_righe_effettive:
--   CONFERMATE + attive) di tipo riapre_residuo=true collegate a quella
--   riga ordine. Single source per fn_ordine_ha_residuo_evasione e per
--   il guard fulfillment (coerenza formula residuo).
-- rev 2026-07-17 (step 2): legge l'helper unico invece di ripetere
--   la catena JOIN + filtro CONFERMATO; il filtro-tipo (riapre_residuo)
--   resta qui, "sopra" la vista (brief §3b).
DECLARE
    v_qta numeric;
BEGIN
    IF p_ordine_riga_id IS NULL OR p_ordine_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_ordine_riga_qta_riconsegna','E_VALIDAZIONE',
            jsonb_build_object('p_ordine_riga_id', p_ordine_riga_id),
            NULL::uuid, 'p_ordine_riga_id deve essere > 0');
    END IF;

    SELECT COALESCE(SUM(e.quantita), 0)
      INTO v_qta
      FROM vendite.vw_resi_righe_effettive e
     WHERE e.ordine_riga_id = p_ordine_riga_id
       AND e.riapre_residuo IS TRUE;

    RETURN v_qta;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ordine_riga_qta_riconsegna(p_ordine_riga_id bigint)
IS 'Addendo reso del residuo per riga ordine: Sigma quantita (base) delle righe reso EFFETTIVE (vw_resi_righe_effettive) di tipo riapre_residuo. Single source per fn_ordine_ha_residuo_evasione e trgfn_ordini_ful_guard_consistenza (coerenza formula). rev 2026-07-13. rev 2026-07-17 (step 2): legge l helper unico; ora filtra anche resi_righe.attivo (canonico CONFERMATI+attivi).';
```

---
{% include-markdown "signature-core.md" %}
