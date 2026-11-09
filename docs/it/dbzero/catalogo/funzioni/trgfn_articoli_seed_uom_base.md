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
    -- fattore 1, nessuna data (vale sempre), attiva o spenta come l'articolo.
    -- Un articolo che nasce spento ha la riga base spenta: una figlia attiva
    -- sotto un padre spento la rifiuterebbe il vincolo generato
    -- ..._articoli_require_attivo. L'articolo e' nuovo, quindi la riga non c'e'
    -- ancora: niente ON CONFLICT.
    INSERT INTO catalogo.articoli_uom_operativa (
        articolo_id, uom_id, is_base, factor_to_base, attivo)
    VALUES (NEW.id, NEW.uom_id, TRUE, 1, NEW.attivo);

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_seed_uom_base()
IS 'Trigger AFTER INSERT su catalogo.articoli: crea la riga dell''unita'' base in catalogo.articoli_uom_operativa (is_base, l''unita'' dell''articolo, factor_to_base = 1, senza date di validita''), attiva o spenta come l''articolo. E'' la strada della riga base: catalogo.trgfn_articoli_uom_operativa_guard_base impedisce di spostarla, di toglierla e di crearne una su un''altra unita''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
