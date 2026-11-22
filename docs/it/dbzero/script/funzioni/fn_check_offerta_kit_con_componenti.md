# ⚙️ Funzione `fn_check_offerta_kit_con_componenti`

```sql
CREATE FUNCTION fn_check_offerta_kit_con_componenti(p_offerta_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_offerta_kit_con_componenti(p_offerta_id bigint)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT COALESCE(jsonb_agg(jsonb_build_object('codice', 'E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI', 'reason', 'KIT_SENZA_COMPONENTI', 'reason_key', 'vendite.offerte.azione_reason.kit_senza_componenti', 'valori', jsonb_build_array(COALESCE(o.codice, (o.id)::text), a.codice), 'dettaglio', jsonb_build_object('campo', 'componenti', 'offerta_id', o.id, 'eccezione_id', e.id, 'articolo_id', e.articolo_id, 'tipo_eccezione', e.tipo_eccezione)) ORDER BY e.ordine, e.id), '[]'::jsonb) AS "coalesce"
    FROM ((vendite.offerte_commerciali o
      JOIN vendite.offerte_commerciali_eccezioni e ON ((e.offerta_id = o.id)))
      JOIN catalogo.articoli a ON ((a.id = e.articolo_id)))
   WHERE ((o.id = fn_check_offerta_kit_con_componenti.p_offerta_id) AND e.attivo AND a.is_composito AND (e.tipo_eccezione = ANY (ARRAY['OVERRIDE'::vendite.tipo_eccezione_contratto, 'AGGIUNTA'::vendite.tipo_eccezione_contratto])) AND (e.quantita IS NOT NULL) AND (NOT (EXISTS ( SELECT 1
            FROM vendite.offerte_commerciali_eccezioni_componenti c
           WHERE ((c.eccezione_offerta_id = e.id) AND c.attivo)))));
END

COMMENT ON FUNCTION script.fn_check_offerta_kit_con_componenti(p_offerta_id bigint)
IS 'Check (fn_check_*): i kit col prezzo negoziato di un''offerta che non hanno componenti attivi. Un kit in OVERRIDE o in AGGIUNTA vale la somma dei suoi componenti (vendite.offerte_commerciali_eccezioni_componenti): senza, il prezzo negoziato non ha da dove ricomporsi, e l''ordine o il contratto generati dall''offerta non lo ritroverebbero. Esente il kit a consumo (quantita'' NULL, una fonte diversa da FISSA), che i componenti non li ha per costruzione. Un motivo per eccezione, nell''ordine delle righe; ''[]'' = nessuno. Motivo: codice E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI, reason KIT_SENZA_COMPONENTI, reason_key vendite.offerte.azione_reason.kit_senza_componenti, valori [codice dell''offerta, codice dell''articolo], dettaglio {campo componenti, offerta_id, eccezione_id, articolo_id, tipo_eccezione}. Lettori: vendite.trgfn_offerte_commerciali_guard_transizione all''emissione dallo stato iniziale e script.fn_available_actions_offerta, che spegne «Emetti» con lo stesso motivo. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
