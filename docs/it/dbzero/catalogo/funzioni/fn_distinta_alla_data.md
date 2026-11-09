{% include-markdown "it/dbzero/catalogo/manual/fn_distinta_alla_data.md" %}
# ⚙️ Funzione `fn_distinta_alla_data`

```sql
CREATE FUNCTION fn_distinta_alla_data(p_prodotto_id uuid, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_distinta_alla_data(p_prodotto_id uuid, p_data date)
 RETURNS TABLE(id uuid, componente_id uuid, coeff_qta numeric, obbligatorio boolean, esposizione_in_fattura character varying)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ac.id,
     ac.componente_id,
     ac.coeff_qta,
     ac.obbligatorio,
     ac.esposizione_in_fattura
    FROM catalogo.articoli_componenti ac
   WHERE ((ac.prodotto_id = fn_distinta_alla_data.p_prodotto_id) AND (ac.attivo IS TRUE) AND (ac.validita @> fn_distinta_alla_data.p_data));
END

COMMENT ON FUNCTION catalogo.fn_distinta_alla_data(p_prodotto_id uuid, p_data date)
IS 'I legami della distinta del padre p_prodotto_id alla data p_data: le righe attive di catalogo.articoli_componenti con quel prodotto_id e una validita che contiene p_data (i due estremi compresi). p_data NULL -> nessuna riga: la data non si sottintende, e per oggi si passa script.fn_data_operativa(). Sede unica della domanda «di quali componenti e'' fatto il kit a quella data»: la chiamano gli init e i preview dei componenti dei documenti di vendita (vendite.fn_*_riga_componenti_init, vendite.fn_*_riga_componenti_preview, vendite.fn_offerta_eccezione_componenti_init e _preview), il guard script.trgfn_componenti_guard_coerenza_bom e la colonna has_componenti_alla_data di catalogo.vw_articoli_dettaglio. «Il kit ha una distinta da oggi in poi» e'' un''altra domanda: catalogo.fn_articolo_padre_di_distinta_da_oggi. Le colonne sono quelle della struttura del legame; il resto si legge da catalogo.articoli_componenti per id. Il planner la espande nel chiamante quando p_data e'' una colonna, un parametro o una chiamata diretta, non una sottoquery: chi la chiama per riga calcola la data una volta sola. SECURITY INVOKER: catalogo.articoli_componenti non ha RLS.';
```

</div>

---
{% include-markdown "signature-core.md" %}
