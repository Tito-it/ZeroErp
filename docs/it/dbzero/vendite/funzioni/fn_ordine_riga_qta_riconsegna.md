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
-- rev 2026-07-26 (brief-db-chiusura-riconsegna-reso-definitivo §4.2):
--   sottrae la quota RINUNCIATA (resi_righe_rinunce). Una quota
--   dichiarata definitiva non tornera' al cliente, quindi non e' piu'
--   merce "da evadere": togliendola dall'addendo il residuo si chiude
--   e l'ordine passa a EVASO.
--   La sottrazione sta QUI e NON in vw_resi_righe_effettive: quella
--   vista alimenta anche vw_contatore_merce (che somma senza filtro
--   tipo), e toccarla farebbe uscire la riga dalla coda accrediti,
--   cioe' l'accredito dovuto sparirebbe. Vedi §4.2 del brief.
--   Si sottraggono SOLO le rinunce, non le ri-consegne: quelle sono
--   gia' contate come `evaso` dal fulfillment.
DECLARE
    v_qta numeric;
BEGIN
    IF p_ordine_riga_id IS NULL OR p_ordine_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_ordine_riga_qta_riconsegna','E_VALIDAZIONE',
            jsonb_build_object('p_ordine_riga_id', p_ordine_riga_id),
            NULL::uuid, 'p_ordine_riga_id deve essere > 0');
    END IF;

    SELECT COALESCE(SUM(GREATEST(0::numeric, e.quantita - COALESCE(rin.tot, 0))), 0)
      INTO v_qta
      FROM vendite.vw_resi_righe_effettive e
      LEFT JOIN LATERAL (
          SELECT SUM(r.qta) AS tot
            FROM vendite.resi_righe_rinunce r
           WHERE r.resi_riga_id = e.resi_riga_id
      ) rin ON TRUE
     WHERE e.ordine_riga_id = p_ordine_riga_id
       AND e.riapre_residuo IS TRUE;

    RETURN v_qta;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ordine_riga_qta_riconsegna(p_ordine_riga_id bigint)
IS 'Addendo reso del residuo per riga ordine: Sigma quantita (base) delle righe reso EFFETTIVE (vw_resi_righe_effettive) di tipo riapre_residuo, AL NETTO della quota rinunciata (vendite.resi_righe_rinunce). Single source per fn_ordine_ha_residuo_evasione e trgfn_ordini_ful_guard_consistenza (coerenza formula). rev 2026-07-13. rev 2026-07-17 (step 2): legge l helper unico; ora filtra anche resi_righe.attivo (canonico CONFERMATI+attivi). rev 2026-07-26 (brief-db-chiusura-riconsegna-reso-definitivo S4.2): sottrae le RINUNCE, cosi'' una quota dichiarata definitiva smette di pesare sul residuo e l''ordine passa a EVASO. La sottrazione sta QUI e NON in vw_resi_righe_effettive, che alimenta anche vw_contatore_merce: toccarla farebbe sparire l''accredito dalla coda. Si sottraggono solo le rinunce, non le ri-consegne (quelle sono gia'' contate come evaso dal fulfillment).';
```

---
{% include-markdown "signature-core.md" %}
