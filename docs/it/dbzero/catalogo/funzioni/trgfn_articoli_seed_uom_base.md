{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_seed_uom_base.md" %}
# ⚙️ Funzione `trgfn_articoli_seed_uom_base`

```sql
CREATE FUNCTION trgfn_articoli_seed_uom_base()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_seed_uom_base()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    INSERT INTO catalogo.articoli_uom_operativa (
        articolo_id,
        uom_id,
        is_base,
        factor_to_base,
        attivo
    )
    VALUES (
        NEW.id,
        NEW.uom_id,
        TRUE,
        1,
        TRUE
    )
    ON CONFLICT ON CONSTRAINT uq_artuomop_articolo_uom DO NOTHING;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_seed_uom_base()
IS 'Trigger AFTER INSERT su catalogo.articoli: crea automaticamente la riga is_base=true in articoli_uom_operativa con factor_to_base=1. Idempotente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
