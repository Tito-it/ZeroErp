# ⚙️ Funzione `fn_contratto_kit_componenti`

```sql
CREATE FUNCTION fn_contratto_kit_componenti(p_contratto_id bigint, p_articolo_padre_id uuid, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratto_kit_componenti(p_contratto_id bigint, p_articolo_padre_id uuid, p_data date)
 RETURNS TABLE(articolo_componente_id uuid, componente_id uuid, uom_operativa_id bigint, coeff_qta_snapshot numeric, prezzo_unitario numeric, esposizione_in_fattura character varying, origine_prezzo character varying)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ac.id,
     af.id,
     af.uom_id,
     ac.coeff_qta,
     rp.prezzo_finale,
     ac.esposizione_in_fattura,
     rp.origine
    FROM (((((vendite.contratti c
      CROSS JOIN LATERAL vendite.fn_documento_listino_operativo('CONTRATTO'::character varying, c.id) lo(listino_id, listino_versione_id, tipo_variazione_globale, valore_variazione_globale))
      JOIN vendite.listini_righe_componenti lrc ON (((lrc.listino_versione_id = lo.listino_versione_id) AND (lrc.articolo_padre_id = fn_contratto_kit_componenti.p_articolo_padre_id) AND (lrc.attivo IS TRUE) AND (lrc.validita @> fn_contratto_kit_componenti.p_data))))
      JOIN catalogo.articoli_componenti ac ON ((ac.id = lrc.articolo_componente_id)))
      JOIN catalogo.articoli af ON ((af.id = lrc.articolo_figlio_id)))
      LEFT JOIN LATERAL ( SELECT r.prezzo_finale,
             r.origine
            FROM vendite.fn_resolve_prezzo_listino_v2_esito(af.id, af.uom_id, fn_contratto_kit_componenti.p_data, c.billing_account_id, c.utility_id, anagrafiche.fn_get_emittente_fiscale_id(c.billing_account_id), NULL::integer, fn_contratto_kit_componenti.p_articolo_padre_id, lo.listino_versione_id) r(prezzo_finale, prezzo_base_snapshot, tipo_variazione_applicata, valore_variazione_applicata, origine, listino_id, listino_versione_id, listino_riga_id, contratto_id, promo_id, categoria_cliente_listino_id, categoria_cliente_id_snapshot, classe_utenza_id_snapshot, tipo_eccezione, esito_codice, esito_context, esito_valori)
           WHERE (r.esito_codice IS NULL)) rp ON (true))
   WHERE (c.id = fn_contratto_kit_componenti.p_contratto_id)
   ORDER BY lrc.id;
END

COMMENT ON FUNCTION vendite.fn_contratto_kit_componenti(p_contratto_id bigint, p_articolo_padre_id uuid, p_data date)
IS 'I componenti di un kit sulla versione di listino del contratto (vendite.fn_documento_listino_operativo), validi alla data, nella forma che l''espansore del backend legge dalle *_righe_componenti: componente, unita'' operativa (quella del componente), coefficiente della distinta, prezzo unitario, esposizione in fattura, origine del prezzo. Il prezzo lo dice il resolver (vendite.fn_resolve_prezzo_listino_v2_esito) sul componente nel contesto del padre: oggi il prezzo del listino senza variazione (LISTINO_BUNDLE), come l''anteprima. NULL = il componente non ha un prezzo alla data. Il prezzo del kit e'' la somma prezzo x coefficiente, che fa chi la usa (vendite.fn_contratti_addebiti_maturati). Serve il kit che il contratto non negozia: la quota fissa del listino e l''ADESIONE. Contratto fuori perimetro o senza listino: nessuna riga. SECURITY INVOKER. Nasce il 2026-10-31 (20261031-34), brief-db-contratto-righe-periodiche-in-commessa §7.2 (D-2, c).';
```

</div>

---
{% include-markdown "signature-core.md" %}
