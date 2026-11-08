# ⚙️ Funzione `fn_offerta_documenti_vivi`

```sql
CREATE FUNCTION fn_offerta_documenti_vivi(p_offerta_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_documenti_vivi(p_offerta_id bigint)
 RETURNS TABLE(tipo text, documento_id bigint)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT 'CONTRATTO'::text, c.id
      FROM vendite.offerte_commerciali oc
      JOIN config.sorgenti s ON s.codice_interno = 'OFFERTA_COMMERCIALE'
      JOIN vendite.contratti c
        ON c.sorgente_tipo_id = s.id
       AND (c.sorgente_id = oc.id OR c.sorgente_uid = oc.uid)
     WHERE oc.id = p_offerta_id
       AND NOT c.is_abortito_snapshot
    UNION ALL
    SELECT 'ORDINE_VENDITA'::text, o.id
      FROM vendite.offerte_commerciali oc
      JOIN config.sorgenti s ON s.codice_interno = 'OFFERTA_COMMERCIALE'
      JOIN vendite.ordini o
        ON o.sorgente_tipo_id = s.id
       AND (o.sorgente_id = oc.id OR o.sorgente_uid = oc.uid)
     WHERE oc.id = p_offerta_id
       AND NOT o.is_abortito_snapshot
     ORDER BY 1, 2;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_documenti_vivi(p_offerta_id bigint)
IS 'I contratti e gli ordini vivi (non annullati) nati da un''offerta: risponde a «l''offerta e'' gia'' trasformata?». Il documento nato dall''offerta e'' quello che la dichiara come provenienza (sorgente_tipo_id OFFERTA_COMMERCIALE, con la chiave dell''offerta in sorgente_uid o sorgente_id). Un documento annullato conserva la provenienza ma non consuma l''offerta: vivi da is_abortito_snapshot, la colonna dei due indici unici parziali uq_contratti_sorgente_offerta e uq_ordini_v_sorgente_offerta. tipo = codice di config.tipi_entita (CONTRATTO, ORDINE_VENDITA), lo stesso del bersaglio dell''errore; documento_id polimorfo, tipo nudo. L''offerta si legge sotto la RLS di chi chiama: un''offerta che non vede non ha documenti vivi. Sede unica per vendite.fn_push_offerta_a_contratto, vendite.fn_genera_ordine_da_offerta e script.fn_available_actions_offerta. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
