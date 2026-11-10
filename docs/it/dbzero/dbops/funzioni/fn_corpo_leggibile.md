{% include-markdown "it/dbzero/dbops/manual/fn_corpo_leggibile.md" %}
# ⚙️ Funzione `fn_corpo_leggibile`

```sql
CREATE FUNCTION fn_corpo_leggibile(p_prolang oid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_corpo_leggibile(p_prolang oid)
 RETURNS boolean
 LANGUAGE sql
 STABLE PARALLEL SAFE
AS $function$
  SELECT COALESCE(p_prolang = ANY (ARRAY(SELECT l.oid
                                           FROM pg_catalog.pg_language l
                                          WHERE l.lanname IN ('plpgsql', 'sql'))),
                  false);
$function$

COMMENT ON FUNCTION dbops.fn_corpo_leggibile(p_prolang oid)
IS 'Vero se le funzioni di quel linguaggio (pg_proc.prolang) hanno un corpo che i presidi sanno leggere: plpgsql e sql, comprese le sql BEGIN ATOMIC, cioe'' i corpi che dbops.fn_corpo_funzione restituisce come testo. Falso per c e internal, il cui prosrc e'' il nome di un simbolo, e per un NULL. E'' il perimetro dei presidi sul corpo: dbops.vw_codici_errore_da_dichiarare, dbops.vw_punti_canale_campo, dbops.vw_funzioni_check_codici, dbops.vw_punti_primo_motivo, dbops.vw_bersagli_non_dichiarati, dbops.vw_stati_check_scrittori. Il perimetro e'' il modello, non il linguaggio: una funzione sql puo'' sollevare un codice come una plpgsql. Un linguaggio nuovo con un corpo leggibile si aggiunge qui, e solo qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
