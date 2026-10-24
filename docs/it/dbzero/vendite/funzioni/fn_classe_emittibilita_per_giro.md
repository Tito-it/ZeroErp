{% include-markdown "it/dbzero/vendite/manual/fn_classe_emittibilita_per_giro.md" %}
# ⚙️ Funzione `fn_classe_emittibilita_per_giro`

```sql
CREATE FUNCTION fn_classe_emittibilita_per_giro(p_classe text, p_trattenuta_da_lotti bigint[], p_lotto_corrente bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_classe_emittibilita_per_giro(p_classe text, p_trattenuta_da_lotti bigint[], p_lotto_corrente bigint)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
RETURN CASE WHEN ((p_classe = 'TRATTENUTA'::text) AND (p_lotto_corrente IS NOT NULL) AND (p_trattenuta_da_lotti <@ ARRAY[p_lotto_corrente])) THEN 'PRONTA'::text ELSE p_classe END

COMMENT ON FUNCTION vendite.fn_classe_emittibilita_per_giro(p_classe text, p_trattenuta_da_lotti bigint[], p_lotto_corrente bigint)
IS 'La classe di emittibilita'' di una riga (vendite.vw_commesse_attivita_emittibilita.classe_emittibilita) VISTA DAL GIRO che la chiede: una riga TRATTENUTA soltanto dal lotto corrente e'', per quel lotto, PRONTA — e'' il proprio documento di un tentativo precedente, da riprendere al rilancio. Ogni altra classe torna com''e''. `<@` e non `= ANY`: si libera solo se TUTTI i lotti che la tengono sono il mio. Lotto NULL = chiamante fuori pipeline = nessuna auto-esclusione. SEDE UNICA dell''auto-esclusione: la leggono fn_list_commesse_emittibili (quali commesse visitare) e fn_emit_attivita_fatturabili_da_commessa (quali righe emettere), ognuna con la propria whitelist sopra. Poggia sull''ordine del CASE della vista (RIFIUTATA/NON_APPROVATA prima di TRATTENUTA): asserito dal pgTAP test-pull-non-prende-trattenuti-v1. SQL IMMUTABLE, inlinata dal planner. Brief: brief-db-rilancio-step-non-rivede-le-proprie-commesse (D1), 2026-09-12.';
```

</div>

---
{% include-markdown "signature-core.md" %}
