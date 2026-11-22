{% include-markdown "it/dbzero/dbops/manual/fn_seed_elenco_colonne.md" %}
# ⚙️ Funzione `fn_seed_elenco_colonne`

```sql
CREATE FUNCTION fn_seed_elenco_colonne(p_elenco text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_elenco_colonne(p_elenco text)
 RETURNS text[]
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- Scopo: i nomi di colonna di un elenco del montaggio, separati da
    --   virgola: spazi tolti, voci vuote tolte, l'ordine dell'elenco.
    --   NULL e '' danno l'elenco vuoto.
    SELECT array_remove(
               string_to_array(regexp_replace(COALESCE(p_elenco, ''), '\s', '', 'g'), ','),
               '');
$function$

COMMENT ON FUNCTION dbops.fn_seed_elenco_colonne(p_elenco text)
IS 'Un elenco di colonne di un argomento del trigger del seed di primo impianto (script.trgfn_seed_primo_impianto, forma COLONNA): i nomi separati da virgola, con gli spazi tolti e le voci vuote tolte, nell''ordine in cui sono scritti. Un elenco assente (NULL) o vuoto da'' l''array vuoto, mai NULL: decide il chiamante se l''elenco vuoto e'' ammesso. La leggono dbops.fn_seed_primo_impianto_argomenti, per le colonne del software, dell''installazione e derivate, e il trigger, per le derivate che legge da TG_ARGV dopo la validazione: una lettura sola, perche'' il trigger scarti le colonne che la grammatica ha validato. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
