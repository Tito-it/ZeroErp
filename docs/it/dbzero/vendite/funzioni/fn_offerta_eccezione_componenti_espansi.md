# ⚙️ Funzione `fn_offerta_eccezione_componenti_espansi`

```sql
CREATE FUNCTION fn_offerta_eccezione_componenti_espansi(p_eccezione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_eccezione_componenti_espansi(p_eccezione_id bigint)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT jsonb_agg(jsonb_build_object('articolo_componente_id', oecc_c.articolo_componente_id, 'componente_id', af.id, 'componente_codice', af.codice, 'componente_descrizione', af.descrizione, 'uom_id', af.uom_id, 'uom_codice', umf.codice, 'coeff_qta', oecc_c.coeff_qta_snapshot, 'prezzo', oecc_c.prezzo_unitario, 'qta_operativa', oecc_c.qta_operativa, 'uom_operativa_id', oecc_c.uom_operativa_id, 'factor_to_base', oecc_c.factor_to_base, 'origine_prezzo', oecc_c.origine_prezzo, 'listino_versione_id', oecc_c.listino_versione_id, 'listino_riga_id', oecc_c.listino_riga_id, 'prezzo_resolver_context', oecc_c.prezzo_resolver_context) ORDER BY oecc_c.ordine, oecc_c.id) AS jsonb_agg
    FROM ((vendite.offerte_commerciali_eccezioni_componenti oecc_c
      JOIN catalogo.articoli af ON ((af.id = oecc_c.componente_id)))
      JOIN catalogo.unita_misura umf ON ((umf.id = af.uom_id)))
   WHERE ((oecc_c.eccezione_offerta_id = fn_offerta_eccezione_componenti_espansi.p_eccezione_id) AND (oecc_c.attivo = true));
END

COMMENT ON FUNCTION vendite.fn_offerta_eccezione_componenti_espansi(p_eccezione_id bigint)
IS 'I componenti attivi di un''eccezione d''offerta composita (vendite.offerte_commerciali_eccezioni_componenti), nell''ordine della riga, come array jsonb: articolo_componente_id, componente (id, codice, descrizione), unita'' del componente (uom_id, uom_codice), coeff_qta (quello fotografato sulla riga), prezzo, qta_operativa, uom_operativa_id, factor_to_base e la provenienza del prezzo (origine_prezzo, listino_versione_id, listino_riga_id, prezzo_resolver_context). Un elemento e'' gia'' un override che vendite.fn_componente_override legge con la sua provenienza. NULL = l''eccezione non ha componenti attivi. La leggono le righe espanse dell''offerta (vendite.fn_offerta_righe_espanse) per il kit aggiunto e per il kit col prezzo forzato. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
