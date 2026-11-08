{% include-markdown "it/dbzero/dbops/manual/fn_testo_senza_commenti.md" %}
# ⚙️ Funzione `fn_testo_senza_commenti`

```sql
CREATE FUNCTION fn_testo_senza_commenti(p_testo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_testo_senza_commenti(p_testo text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- Gruppo 1: un letterale E'…' (con \' e ''), '…' (con ''), o un
    -- identificatore "…": si rimette com'e'. Fuori dal gruppo: un
    -- commento di riga o a blocco, che si toglie.
    SELECT pg_catalog.regexp_replace(
               p_testo,
               '((?:[Ee]''(?:[^''\\]|\\.|'''')*''|''(?:[^'']|'''')*''|"(?:[^"]|"")*"))|--[^\n]*|/\*(?:[^*]|\*+[^*/])*\*+/',
               '\1',
               'g');
$function$

COMMENT ON FUNCTION dbops.fn_testo_senza_commenti(p_testo text)
IS 'Il testo SQL senza i commenti: toglie i commenti di riga (--) e quelli a blocco (/* */), e lascia intatti i letterali ''…'' ed E''…'' e gli identificatori "…", anche quando contengono -- o /*. Un''espressione sola, letta da sinistra: il primo carattere decide se comincia un letterale o un commento. Non riconosce come letterali le stringhe dollar-quoted interne ($q$…$q$) ne'' i commenti a blocco annidati. Senza un testo restituisce NULL. Da usare attraverso dbops.fn_corpo_funzione quando il testo e'' il corpo di una funzione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
