{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_padre_di_distinta_in_vigore.md" %}
# ⚙️ Funzione `fn_articolo_padre_di_distinta_in_vigore`

```sql
CREATE FUNCTION fn_articolo_padre_di_distinta_in_vigore(p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_padre_di_distinta_in_vigore(p_articolo_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT (EXISTS ( SELECT 1
            FROM catalogo.articoli_componenti ac
           WHERE ((ac.prodotto_id = fn_articolo_padre_di_distinta_in_vigore.p_articolo_id) AND (ac.attivo IS TRUE) AND (ac.validita @> script.fn_data_operativa())))) AS "exists";
END

COMMENT ON FUNCTION catalogo.fn_articolo_padre_di_distinta_in_vigore(p_articolo_id uuid)
IS 'true se l''articolo e'' il PADRE di una distinta in vigore: un legame attivo di catalogo.articoli_componenti con prodotto_id = l''articolo e validita che contiene il giorno aziendale (script.fn_data_operativa). NULL -> false. Predicato unico del check 1 di catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva (is_composito e requires_serial non si cambiano) e delle sue regole gemelle per il form in dbops.lock_columns_conditional.';
```

</div>

---
{% include-markdown "signature-core.md" %}
