{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_righe_vive_non_ammesse.md" %}
# ⚙️ Funzione `fn_articolo_righe_vive_non_ammesse`

```sql
CREATE FUNCTION fn_articolo_righe_vive_non_ammesse(p_articolo_id uuid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_righe_vive_non_ammesse(p_articolo_id uuid)
 RETURNS TABLE(documento text, documento_id bigint, riga_id bigint, motivo jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Le righe VIVE dell'articolo che la check dei guard di
    --   riga non ammette, col primo motivo. Viva = attiva, e il
    --   documento non e' chiuso. Le sette tabelle sono quelle di
    --   script.trgfn_righe_guard_articolo_ammesso.
    -- =========================================================
    RETURN QUERY
    SELECT g.documento, g.documento_id, g.riga_id, g.motivo
      FROM (
          SELECT v.documento, v.documento_id, v.riga_id,
                 script.fn_check_articolo_riga(
                     v.documento, v.documento_id, p_articolo_id,
                     v.natura_vendita_id, v.tipo_eccezione) -> 0 AS motivo
            FROM (
                SELECT 'PREVENTIVO'::text, r.preventivo_id, r.id, r.natura_vendita_id,
                       NULL::vendite.tipo_eccezione_contratto
                  FROM vendite.preventivi_righe r
                  JOIN vendite.preventivi t ON t.id = r.preventivo_id
                  JOIN config.stati_doc_preventivi s ON s.id = t.stato_doc_preventivo_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'ORDINE_VENDITA', r.ordine_id, r.id, r.natura_vendita_id, NULL
                  FROM vendite.ordini_righe r
                  JOIN vendite.ordini t ON t.id = r.ordine_id
                  JOIN config.stati_doc_ordini s ON s.id = t.stato_doc_ordine_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'DDT_VENDITA', r.ddt_id, r.id, r.natura_vendita_id, NULL
                  FROM vendite.ddt_righe r
                  JOIN vendite.ddt t ON t.id = r.ddt_id
                  JOIN config.stati_doc_ddt s ON s.id = t.stato_doc_ddt_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'OFFERTA_COMMERCIALE', r.offerta_id, r.id, NULL, r.tipo_eccezione
                  FROM vendite.offerte_commerciali_eccezioni r
                  JOIN vendite.offerte_commerciali t ON t.id = r.offerta_id
                  JOIN config.stati_doc_offerte s ON s.id = t.stato_doc_offerta_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'CONTRATTO', r.contratto_id, r.id, NULL, r.tipo_eccezione
                  FROM vendite.contratti_righe r
                  JOIN vendite.contratti t ON t.id = r.contratto_id
                  JOIN config.stati_doc_contratti s ON s.id = t.stato_doc_contratto_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'LISTINO_VERSIONE', r.listino_versione_id, r.id, NULL, NULL
                  FROM vendite.listini_righe r
                  JOIN vendite.listini_versioni lv ON lv.id = r.listino_versione_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND lv.stato <> 'CHIUSA'
                UNION ALL
                SELECT 'PROMO_ARTICOLO', p.id, p.id, NULL, NULL
                  FROM vendite.promo_articoli p
                 WHERE p.articolo_id = p_articolo_id AND p.attivo
                   AND (upper_inf(p.validita)
                        OR upper(p.validita) > script.fn_data_operativa())
            ) v(documento, documento_id, riga_id, natura_vendita_id, tipo_eccezione)
      ) g
     WHERE g.motivo IS NOT NULL;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_righe_vive_non_ammesse(p_articolo_id uuid)
IS 'Le righe VIVE di un articolo che la check dei guard di riga non ammette: {documento (codice di config.tipi_entita), documento_id, riga_id, motivo = il primo motivo di script.fn_check_articolo_riga, con la natura e il tipo d''eccezione della riga}; solo le righe con un motivo. Viva = attiva, e il documento non e'' chiuso: fase dello stato diversa da CHIUSO per preventivo, ordine, bolla, offerta e contratto; versione di listino non CHIUSA; promo col periodo non finito alla data operativa (script.fn_data_operativa). Le sette tabelle sono quelle dove e'' montato script.trgfn_righe_guard_articolo_ammesso (per la promo documento_id = riga_id = id della promo). SECURITY INVOKER: sotto RLS chi la chiama vede le sue righe; il verbo catalogo.fn_articolo_correggi_struttura (SECURITY DEFINER) la chiama su tutte le aziende, prima e dopo la correzione, e rifiuta solo le righe che la correzione rende non ammesse (A-11 di brief-db-articoli-ammessi-per-documento). Nasce il 2026-10-18 (§9.8.6).';
```

---
{% include-markdown "signature-core.md" %}
