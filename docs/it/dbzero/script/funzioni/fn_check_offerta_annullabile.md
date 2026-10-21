# ⚙️ Funzione `fn_check_offerta_annullabile`

```sql
CREATE FUNCTION fn_check_offerta_annullabile(p_offerta_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_offerta_annullabile(p_offerta_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- =========================================================
-- Scopo:
--   Si puo' annullare l'offerta? No se ha generato un contratto o un
--   ordine ancora VIVO (vendite.fn_offerta_documenti_vivi, la sede
--   unica che leggono anche il push e la capability). '[]' = si'.
--
-- ⭐ Perche' (brief-db-offerta-emissione-ed-erogazione §H.3 H-R3):
--   da ACCETTATA si esce anche annullando, non solo trasformando. Ma
--   un'offerta che vive in un contratto o in un ordine non si annulla
--   sotto i piedi di quel documento: prima si annulla lui (che non
--   consuma piu' l'offerta, D-3 di brief-db-annullo-documento-con-
--   legami). Lo stesso predicato nel guard di transizione e nella
--   capability.
--
-- Motivo: {codice E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI, reason
--   DOCUMENTI_VIVI, reason_key vendite.offerte.azione_reason.documenti_vivi,
--   valori [codice dell'offerta], dettaglio {offerta_id, bersaglio =
--   [{tipo, id}] dei documenti vivi}}: il bersaglio e' dove l'operatore
--   deve andare, come nei guard d'idempotenza del push.
-- =========================================================
DECLARE
    -- Nudo DICHIARATO: l'array {tipo, id} dei documenti, un frammento
    -- del contesto, non il valore di una colonna.
    v_bersagli jsonb;
    v_codice   vendite.offerte_commerciali.codice%TYPE;
BEGIN
    SELECT jsonb_agg(jsonb_build_object('tipo', d.tipo, 'id', d.documento_id::text)
                     ORDER BY d.tipo, d.documento_id)
      INTO v_bersagli
      FROM vendite.fn_offerta_documenti_vivi(p_offerta_id) AS d;

    IF v_bersagli IS NULL THEN
        RETURN '[]'::jsonb;
    END IF;

    SELECT o.codice INTO v_codice
      FROM vendite.offerte_commerciali o
     WHERE o.id = p_offerta_id;

    RETURN jsonb_build_array(jsonb_build_object(
        'codice',     'E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI',
        'reason',     'DOCUMENTI_VIVI',
        'reason_key', 'vendite.offerte.azione_reason.documenti_vivi',
        'valori',     jsonb_build_array(COALESCE(v_codice, p_offerta_id::text)),
        'dettaglio',  jsonb_build_object(
                          'offerta_id', p_offerta_id,
                          'bersaglio',  v_bersagli)));
END;
$function$

COMMENT ON FUNCTION script.fn_check_offerta_annullabile(p_offerta_id bigint)
IS 'Check (fn_check_*): si puo'' annullare l''offerta? ''[]'' = si''; altrimenti un motivo E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI (reason DOCUMENTI_VIVI, reason_key vendite.offerte.azione_reason.documenti_vivi, debito verso il frontend; valori [codice dell''offerta]; dettaglio {offerta_id, bersaglio = [{tipo, id}]}) se l''offerta ha generato un contratto o un ordine ancora vivo, letto da vendite.fn_offerta_documenti_vivi (la sede unica del push e della capability). Lettori: vendite.trgfn_offerte_commerciali_guard_transizione (verso ANNULLATA) e script.fn_available_actions_offerta (l''azione annulla). STABLE, SECURITY INVOKER. Nasce il 2026-10-21 (20261021-56), brief-db-offerta-emissione-ed-erogazione §H.3 (H-R3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
