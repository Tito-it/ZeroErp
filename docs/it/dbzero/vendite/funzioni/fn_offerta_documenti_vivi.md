# ⚙️ Funzione `fn_offerta_documenti_vivi`

```sql
CREATE FUNCTION fn_offerta_documenti_vivi(p_offerta_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_documenti_vivi(p_offerta_id bigint)
 RETURNS TABLE(tipo text, documento_id bigint)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT 'CONTRATTO'::text, c.id
      FROM vendite.contratti c
     WHERE c.offerta_id = p_offerta_id
       AND NOT c.is_abortito_snapshot
    UNION ALL
    SELECT 'ORDINE_VENDITA'::text, o.id
      FROM vendite.ordini o
     WHERE o.documento_origine_tipo = 'OFFERTA_COMMERCIALE'
       AND o.documento_origine_id   = p_offerta_id
       AND NOT o.is_abortito_snapshot
     ORDER BY 1, 2;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_documenti_vivi(p_offerta_id bigint)
IS 'I contratti e gli ordini VIVI (non abortiti) nati da un''offerta (2026-10-11, brief-db-annullo-documento-con-legami D-3/D-6): risponde a «l''offerta e'' gia'' trasformata?». Un documento annullato conserva la provenienza ma non consuma l''offerta. tipo = codice di config.tipi_entita (CONTRATTO, ORDINE_VENDITA), lo stesso del bersaglio dell''errore. Vivi da is_abortito_snapshot, la colonna dei due indici unici parziali (uq_contratti_offerta_id, uq_ordini_v_documento_origine_offerta). Sede unica per vendite.fn_push_offerta_a_contratto, script.fn_available_actions_offerta e il backend (crea ordine da offerta). documento_id polimorfo: tipo nudo dichiarato. SECURITY INVOKER. ⭐ rev 2026-10-19 (20261019-97, brief-db-grammatica-unica-documenti lotto 2b): l''ordine nato dall''offerta si riconosce da documento_origine_tipo = OFFERTA_COMMERCIALE, il codice della sorgente (era OFFERTA).';
```

---
{% include-markdown "signature-core.md" %}
