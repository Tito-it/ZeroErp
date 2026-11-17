# ⚙️ Funzione `fn_nomi_tipo_indirizzo_richiesto`

```sql
CREATE FUNCTION fn_nomi_tipo_indirizzo_richiesto(p_tipo_indirizzo_id integer, p_fallback_tipo_indirizzo_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_nomi_tipo_indirizzo_richiesto(p_tipo_indirizzo_id integer, p_fallback_tipo_indirizzo_id integer)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT string_agg((('«'::text || ti.descrizione) || '»'::text), ' / '::text ORDER BY x.ord) AS string_agg
    FROM (unnest(ARRAY[fn_nomi_tipo_indirizzo_richiesto.p_tipo_indirizzo_id, fn_nomi_tipo_indirizzo_richiesto.p_fallback_tipo_indirizzo_id]) WITH ORDINALITY x(id, ord)
      JOIN config.tipi_indirizzi ti ON ((ti.id = x.id)))
   WHERE ((x.ord = 1) OR (x.id IS DISTINCT FROM fn_nomi_tipo_indirizzo_richiesto.p_tipo_indirizzo_id));
END

COMMENT ON FUNCTION anagrafiche.fn_nomi_tipo_indirizzo_richiesto(p_tipo_indirizzo_id integer, p_fallback_tipo_indirizzo_id integer)
IS 'I nomi di un tipo di indirizzo richiesto e del suo ripiego, come li legge l''operatore: ogni descrizione di config.tipi_indirizzi fra caporali, nell''ordine tipo e ripiego, separate da '' / '' («Sede legale» / «Domicilio fiscale»). Ripiego NULL o uguale al tipo: il solo tipo. Un id assente dal catalogo non compare; nessuno dei due presente: NULL. E'' il valore della frase di E_INDIRIZZO_OBBLIGATORIO_MANCANTE (anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required) e di E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO (anagrafiche.trgfn_soggetti_guard_indirizzi_required). STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
