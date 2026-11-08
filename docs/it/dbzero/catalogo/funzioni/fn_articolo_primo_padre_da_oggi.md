{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_primo_padre_da_oggi.md" %}
# ⚙️ Funzione `fn_articolo_primo_padre_da_oggi`

```sql
CREATE FUNCTION fn_articolo_primo_padre_da_oggi(p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_primo_padre_da_oggi(p_articolo_id uuid)
 RETURNS character varying
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT a_padre.codice
    FROM (catalogo.articoli_componenti ac
      JOIN catalogo.articoli a_padre ON ((a_padre.id = ac.prodotto_id)))
   WHERE ((ac.componente_id = fn_articolo_primo_padre_da_oggi.p_articolo_id) AND (ac.attivo IS TRUE) AND (ac.validita && daterange(script.fn_data_operativa(), NULL::date, '[)'::text)))
   ORDER BY a_padre.codice
  LIMIT 1;
END

COMMENT ON FUNCTION catalogo.fn_articolo_primo_padre_da_oggi(p_articolo_id uuid)
IS 'Il codice del primo padre, per codice, di una distinta in vigore o futura di cui l''articolo e'' componente: un legame attivo di catalogo.articoli_componenti con componente_id = l''articolo e validita che interseca [giorno aziendale, infinito). NULL se non ce n''e'' nessuno, o se l''articolo e'' NULL. Predicato unico del check 3 di catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva (un componente non diventa composito: la distinta ha un livello solo), che usa il codice nel messaggio, e della sua regola gemella per il form in dbops.lock_columns_conditional (IS NOT NULL).';
```

</div>

---
{% include-markdown "signature-core.md" %}
