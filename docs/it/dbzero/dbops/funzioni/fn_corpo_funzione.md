{% include-markdown "it/dbzero/dbops/manual/fn_corpo_funzione.md" %}
# ⚙️ Funzione `fn_corpo_funzione`

```sql
CREATE FUNCTION fn_corpo_funzione(p_funzione oid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_corpo_funzione(p_funzione oid)
 RETURNS text
 LANGUAGE sql
 STABLE PARALLEL SAFE
 SET search_path TO 'pg_catalog'
AS $function$
    -- prosrc e' vuoto per una BEGIN ATOMIC: il corpo sta in
    -- prosqlbody, e lo deparsa pg_get_function_sqlbody, coi nomi
    -- qualificati perche' il search_path qui e' pg_catalog.
    SELECT dbops.fn_testo_senza_commenti(
               CASE
                   WHEN p.prosqlbody IS NULL THEN p.prosrc
                   ELSE pg_catalog.pg_get_function_sqlbody(p.oid)
               END)
      FROM pg_catalog.pg_proc p
     WHERE p.oid = p_funzione;
$function$

COMMENT ON FUNCTION dbops.fn_corpo_funzione(p_funzione oid)
IS 'Il corpo di una funzione senza i commenti, come lo leggono i presidi e gli strumenti che cercano nei corpi un codice, una tabella o un valore. Per una funzione SQL BEGIN ATOMIC, dove pg_proc.prosrc e'' vuoto, il corpo viene da pg_get_function_sqlbody, deparsato coi nomi qualificati (search_path = pg_catalog sulla funzione); per le altre da prosrc. I commenti li toglie dbops.fn_testo_senza_commenti, rispettando i letterali. Un oid che non e'' una funzione restituisce NULL. ⚠️ Il risultato ha la collation di default, mentre pg_proc.prosrc ha quella del catalogo ("C"): chi deve dare colonne e regex uguali a quelle lette da prosrc scrive dbops.fn_corpo_funzione(p.oid) COLLATE "C" (senza, \w e ~* cambiano sui caratteri non ASCII, e un CREATE OR REPLACE VIEW rifiuta il cambio di collation di una colonna). ⛔ Chi cerca nei corpi passa da qui: togliere i commenti da prosrc con una regex propria e'' la copia che questa funzione ha ritirato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
