{% include-markdown "it/dbzero/vendite/manual/fn_ordine_ha_residuo_evasione.md" %}
# ⚙️ Funzione `fn_ordine_ha_residuo_evasione`

```sql
CREATE FUNCTION fn_ordine_ha_residuo_evasione(p_ordine_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ordine_ha_residuo_evasione(p_ordine_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: TRUE se l'ordine ha ancora quantita da evadere su almeno
--   una riga MERCE. RESO-AWARE:
--     residuo = quantita - Sigma qta_evasa
--               + fn_ordine_riga_qta_riconsegna(riga)
--   L'addendo reso (helper unico 20260713-28) e' 0 se non ci sono
--   resi per ri-consegna confermati. Gate per la proiezione stato
--   ordine in fn_genera_ddt_da_ordine / fn_conferma_reso.
-- rev 2026-11-03 (20261103-22, brief-db-addebito-trasporto-ordine
--   §8.1): la riga-onere non ha residuo (l'onere non si evade).
--   Il predicato e' script.fn_natura_e_merce sulla natura
--   CONGELATA della riga.
DECLARE
    -- boolean nudo: e' la risposta, nessuna colonna ne e' il riflesso.
    v_ha_residuo boolean;
BEGIN
    IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_ordine_ha_residuo_evasione', 'E_VALIDAZIONE',
            jsonb_build_object('p_ordine_id', p_ordine_id),
            NULL::uuid, 'p_ordine_id deve essere > 0');
    END IF;

    SELECT EXISTS (
        SELECT 1
          FROM vendite.ordini_righe orr
         WHERE orr.ordine_id = p_ordine_id
           AND orr.attivo IS TRUE
           -- ⭐ L'onere non si evade: conta solo la merce.
           AND script.fn_natura_e_merce(orr.natura_vendita_id)
           AND orr.quantita
               - COALESCE((
                   SELECT SUM(f.qta_evasa)
                     FROM vendite.ordini_righe_fulfillment f
                    WHERE f.ordine_riga_id = orr.id
                 ), 0)
               + vendite.fn_ordine_riga_qta_riconsegna(orr.id)
               > 0
    ) INTO v_ha_residuo;

    RETURN v_ha_residuo;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ordine_ha_residuo_evasione(p_ordine_id bigint)
IS 'TRUE se l''ordine ha residuo di evasione su almeno una riga MERCE (quantita - SUM qta_evasa + addendo reso via fn_ordine_riga_qta_riconsegna, unita base). Reso-aware. Gate stato ordine per fn_genera_ddt_da_ordine e fn_conferma_reso (via vendite.fn_ordine_proietta_stato_evasione). rev 2026-07-13. rev 2026-11-03 (20261103-22, brief-db-addebito-trasporto-ordine §8.1): la riga-onere non ha residuo — l''onere non si evade e non tiene aperto l''ordine; il predicato e'' script.fn_natura_e_merce sulla natura congelata della riga (su ordine «non merce» = onere, lo garantisce l''ammissione).';
```

</div>

---
{% include-markdown "signature-core.md" %}
