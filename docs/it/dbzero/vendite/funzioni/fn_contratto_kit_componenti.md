{% include-markdown "it/dbzero/vendite/manual/fn_contratto_kit_componenti.md" %}
# ⚙️ Funzione `fn_contratto_kit_componenti`

```sql
CREATE FUNCTION fn_contratto_kit_componenti(p_contratto_id bigint, p_articolo_padre_id uuid, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratto_kit_componenti(p_contratto_id bigint, p_articolo_padre_id uuid, p_data date)
 RETURNS TABLE(articolo_componente_id uuid, componente_id uuid, uom_operativa_id bigint, coeff_qta_snapshot numeric, prezzo_unitario numeric, esposizione_in_fattura character varying, origine_prezzo character varying, listino_versione_id bigint, listino_riga_id bigint, prezzo_resolver_context jsonb)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ac.id,
     af.id,
     af.uom_id,
     ac.coeff_qta,
     rp.prezzo_finale,
     ac.esposizione_in_fattura,
     rp.origine,
     rp.listino_versione_id,
     rp.listino_riga_id,
     rp.contesto
    FROM (((((vendite.contratti c
      CROSS JOIN LATERAL vendite.fn_documento_listino_operativo('CONTRATTO'::character varying, c.id) lo(listino_id, listino_versione_id, tipo_variazione_globale, valore_variazione_globale))
      JOIN vendite.listini_righe_componenti lrc ON (((lrc.listino_versione_id = lo.listino_versione_id) AND (lrc.articolo_padre_id = fn_contratto_kit_componenti.p_articolo_padre_id) AND (lrc.attivo IS TRUE) AND (lrc.validita @> fn_contratto_kit_componenti.p_data))))
      JOIN catalogo.articoli_componenti ac ON ((ac.id = lrc.articolo_componente_id)))
      JOIN catalogo.articoli af ON ((af.id = lrc.articolo_figlio_id)))
      LEFT JOIN LATERAL ( SELECT r.prezzo_finale,
             r.origine,
             r.listino_versione_id,
             r.listino_riga_id,
             vendite.fn_prezzo_resolver_contesto(to_jsonb(r.*)) AS contesto
            FROM vendite.fn_resolve_prezzo_listino_v2_esito(af.id, af.uom_id, fn_contratto_kit_componenti.p_data, c.billing_account_id, c.utility_id, anagrafiche.fn_get_emittente_fiscale_id(c.billing_account_id), NULL::integer, fn_contratto_kit_componenti.p_articolo_padre_id, lo.listino_versione_id) r(prezzo_finale, prezzo_base_snapshot, tipo_variazione_applicata, valore_variazione_applicata, origine, listino_id, listino_versione_id, listino_riga_id, contratto_id, promo_id, categoria_cliente_listino_id, categoria_cliente_id_snapshot, classe_utenza_id_snapshot, tipo_eccezione, esito_codice, esito_context, esito_valori)
           WHERE (r.esito_codice IS NULL)) rp ON (true))
   WHERE (c.id = fn_contratto_kit_componenti.p_contratto_id)
   ORDER BY lrc.id;
END

COMMENT ON FUNCTION vendite.fn_contratto_kit_componenti(p_contratto_id bigint, p_articolo_padre_id uuid, p_data date)
IS 'I componenti di un kit sulla versione di listino del contratto (vendite.fn_documento_listino_operativo), validi alla data, nella forma che l''espansore del backend legge dalle *_righe_componenti: componente, unita'' operativa (quella del componente), coefficiente della distinta, prezzo unitario, esposizione in fattura e la provenienza del prezzo (origine, versione e riga di listino, contesto del resolver). Prezzo e provenienza li dice il resolver (vendite.fn_resolve_prezzo_listino_v2_esito) sul componente nel contesto del padre: oggi il prezzo della riga del componente in vendite.listini_righe_componenti, senza variazione (LISTINO_BUNDLE), con la versione e senza riga di listino. Il contesto e'' quello che si salva sulle righe (vendite.fn_prezzo_resolver_contesto) e lo legge vendite.fn_provenienza_prezzo_esplosa. NULL = il componente non ha un prezzo alla data: prezzo e provenienza tutti NULL. Il prezzo del kit e'' la somma prezzo x coefficiente, che fa chi la usa (vendite.fn_contratti_addebiti_maturati_con_provenienza). Serve il kit che il contratto non negozia: la quota fissa del listino e l''ADESIONE. Contratto fuori perimetro o senza listino: nessuna riga. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
