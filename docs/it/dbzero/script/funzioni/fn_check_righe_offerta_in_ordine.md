# ⚙️ Funzione `fn_check_righe_offerta_in_ordine`

```sql
CREATE FUNCTION fn_check_righe_offerta_in_ordine(p_offerta_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_righe_offerta_in_ordine(p_offerta_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- =========================================================
-- Scopo:
--   Le righe di un'offerta che NON possono diventare righe d'ordine:
--   ogni riga espansa (vendite.fn_offerta_righe_espanse, quelle che
--   vendite.fn_genera_ordine_da_offerta copia) giudicata come riga di
--   ORDINE_VENDITA da script.fn_check_riga_documento_su_contesto (solo
--   merce, solo componente, kit senza componenti). Un motivo
--   E_DOC_RIGA_NON_AMMESSA per riga, nell'ordine delle righe espanse;
--   '[]' = l'ordine si puo' generare.
--
-- ⭐ Perche' (brief-db-offerta-emissione-ed-erogazione §I.2, I-D2 di Tid):
--   «Genera ordine» deve dire il motivo PRIMA del clic. E' la stessa
--   domanda che il guard delle righe d'ordine fara' all'INSERT
--   (script.trgfn_righe_guard_articolo_ammesso): la capability e il verbo
--   la leggono da qui, il guard resta la rete.
--
-- L'ordine non esiste ancora: il contesto e' quello di ORDINE_VENDITA
--   senza id (le regole dell'ordine non leggono la testata). La natura e'
--   quella dell'articolo, come la eredita la riga d'ordine.
-- Le righe espanse non hanno un id: nel dettaglio c'e' la posizione
--   (riga_nr, 1 = la prima), l'origine e il tipo d'eccezione.
-- =========================================================
DECLARE
    -- Nudi DICHIARATI: il contesto e i motivi sono jsonb composti;
    -- l'etichetta e' una frase per il messaggio.
    v_contesto  jsonb;
    v_motivi    jsonb;
    v_etichetta text;
BEGIN
    v_contesto := script.fn_articolo_riga_contesto('ORDINE_VENDITA', NULL);

    SELECT 'Ordine dall''offerta ' || COALESCE(o.codice, o.id::text)
      INTO v_etichetta
      FROM vendite.offerte_commerciali o
     WHERE o.id = p_offerta_id;

    SELECT COALESCE(jsonb_agg(
               jsonb_build_object(
                   'codice',     'E_DOC_RIGA_NON_AMMESSA',
                   'reason',     'RIGA_NON_AMMESSA',
                   'reason_key', 'common.azione_reason.riga_non_ammessa',
                   'valori',     jsonb_build_array(v_etichetta, g.articolo_codice),
                   'dettaglio',  jsonb_build_object(
                                     'campo',          'articolo_id',
                                     'documento',      'ORDINE_VENDITA',
                                     'offerta_id',     p_offerta_id,
                                     'riga_nr',        g.riga_nr,
                                     'origine',        g.origine,
                                     'tipo_eccezione', g.tipo_eccezione,
                                     'articolo_id',    g.articolo_id,
                                     'motivo_riga',    g.motivo))
               ORDER BY g.riga_nr), '[]'::jsonb)
      INTO v_motivi
      FROM (
          SELECT r.riga_nr, r.articolo_id, r.articolo_codice, r.origine, r.tipo_eccezione,
                 script.fn_check_riga_documento_su_contesto(
                     v_contesto, r.articolo_id, NULL, NULL, NULL) -> 0 AS motivo
            FROM vendite.fn_offerta_righe_espanse(p_offerta_id)
                 WITH ORDINALITY AS r(articolo_id, articolo_codice, descrizione, is_composito,
                                      quantita, uom_operativa_id, qta_operativa, factor_to_base,
                                      prezzo_unitario, sconto_percentuale, iva_id,
                                      tipo_eccezione, origine, componenti, riga_nr)
      ) g
     WHERE g.motivo IS NOT NULL;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_righe_offerta_in_ordine(p_offerta_id bigint)
IS 'Check (fn_check_*): le righe di un''offerta che non possono diventare righe d''ordine. Ogni riga di vendite.fn_offerta_righe_espanse (quelle che vendite.fn_genera_ordine_da_offerta copia) giudicata come riga di ORDINE_VENDITA da script.fn_check_riga_documento_su_contesto (contesto senza id: l''ordine non esiste ancora; natura dell''articolo). Un motivo per riga, nell''ordine delle righe espanse; ''[]'' = l''ordine si puo'' generare. Motivo: codice E_DOC_RIGA_NON_AMMESSA, reason RIGA_NON_AMMESSA, reason_key common.azione_reason.riga_non_ammessa, valori [''Ordine dall''''offerta <codice>'', codice dell''articolo], dettaglio {campo articolo_id, documento ORDINE_VENDITA, offerta_id, riga_nr (posizione, 1 = la prima), origine, tipo_eccezione, articolo_id, motivo_riga}. Lettori: script.fn_available_actions_offerta (can_genera_ordine) e vendite.fn_genera_ordine_da_offerta (rifiuta col primo motivo prima di scrivere); il guard delle righe d''ordine (script.trgfn_righe_guard_articolo_ammesso) resta la rete. STABLE, SECURITY INVOKER. Nasce il 2026-10-21 (20261021-54), brief-db-offerta-emissione-ed-erogazione §I.2, I-D2 di Tid.';
```

</div>

---
{% include-markdown "signature-core.md" %}
