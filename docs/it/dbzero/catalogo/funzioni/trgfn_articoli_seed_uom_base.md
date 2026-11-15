{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_seed_uom_base.md" %}
# ⚙️ Funzione `trgfn_articoli_seed_uom_base`

```sql
CREATE FUNCTION trgfn_articoli_seed_uom_base()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_seed_uom_base()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- La riga dell'unita' base nasce con l'articolo: unita' dell'articolo,
    -- fattore 1, nessuna data, attiva. La base non ha stati: vale sempre,
    -- anche sotto un articolo spento (il legame ATTIVO con l'articolo e'
    -- fra le eccezioni). L'articolo e' nuovo, quindi la riga non c'e'
    -- ancora: niente ON CONFLICT.
    INSERT INTO catalogo.articoli_uom_operativa (
        articolo_id, uom_id, is_base, factor_to_base, attivo)
    VALUES (NEW.id, NEW.uom_id, TRUE, 1, TRUE);

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_seed_uom_base()
IS 'Trigger AFTER INSERT su catalogo.articoli: crea la riga dell''unita'' base in catalogo.articoli_uom_operativa (is_base, l''unita'' dell''articolo, factor_to_base = 1, senza date di validita''), sempre attiva, anche sotto un articolo spento. E'' la strada della riga base: catalogo.trgfn_articoli_uom_operativa_guard_base impedisce di spostarla, di toglierla, di spegnerla e di crearne una su un''altra unita''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
