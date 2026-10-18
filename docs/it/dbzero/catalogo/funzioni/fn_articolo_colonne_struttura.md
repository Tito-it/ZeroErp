{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_colonne_struttura.md" %}
# ⚙️ Funzione `fn_articolo_colonne_struttura`

```sql
CREATE FUNCTION fn_articolo_colonne_struttura()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_colonne_struttura()
 RETURNS text[]
 LANGUAGE sql
 STABLE
AS $function$
    -- Le regole del form sul predicato dell'uso (seed 20261013-51):
    -- le colonne che l'uso spegne sono quelle che la correzione riapre.
    SELECT COALESCE(array_agg(l.column_name::text ORDER BY l.id), '{}'::text[])
      FROM dbops.lock_columns_conditional l
     WHERE l.schema_name    = 'catalogo'
       AND l.table_name     = 'articoli'
       AND l.condition_expr = 'catalogo.fn_articolo_usato($1::uuid)'
       AND l.enabled;
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_colonne_struttura()
IS 'Le colonne strutturali di un articolo (A-10 di brief-db-articoli-ammessi-per-documento): quelle che non cambiano quando l''articolo e'' usato e che il SUPER_ADMIN corregge con catalogo.fn_articolo_correggi_struttura. Lette, non scritte qui: sono le regole ACCESE del form in dbops.lock_columns_conditional su catalogo.articoli con condition_expr = ''catalogo.fn_articolo_usato($1::uuid)'' (seed 20261013-51), nell''ordine della dichiarazione (id). Array vuoto se il registro non ne ha. Lettori: il verbo catalogo.fn_articolo_correggi_struttura (colonne ammesse in p_campi) e il backend (i campi che la scheda articolo riapre in correzione, al posto della sua lista). Il guard catalogo.trgfn_articoli_guard_struttura_se_usato ha l''elenco scritto (UPDATE OF e CASE: non si derivano a runtime): lo confronta con questa il pgTAP catalogo/test-articolo-colonne-struttura-v1. INVOKER. Nasce il 2026-10-18 (R-DB-3, §9.7.3).';
```

---
{% include-markdown "signature-core.md" %}
