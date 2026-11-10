{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fattore_alla_data.md" %}
# ⚙️ Funzione `trgfn_attivita_fattore_alla_data`

```sql
CREATE FUNCTION trgfn_attivita_fattore_alla_data()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fattore_alla_data()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: un'attivita' senza fattore prende quello alla data
    --   dell'attivita', o si rifiuta (E_UOM_MISSING).
    -- Eventi: INSERT; UPDATE OF factor_to_base, uom_operativa_id, uom_id.
    -- =========================================================
    IF TG_OP = 'UPDATE'
       AND (NEW.uom_operativa_id IS DISTINCT FROM OLD.uom_operativa_id
            OR NEW.uom_id IS DISTINCT FROM OLD.uom_id)
       AND NEW.factor_to_base IS NOT DISTINCT FROM OLD.factor_to_base THEN
        NEW.factor_to_base := NULL;
    END IF;

    IF NEW.factor_to_base IS NULL THEN
        NEW.factor_to_base := script.fn_fattore_uom_alla_data(
            NEW.articolo_id,
            COALESCE(NEW.uom_operativa_id, NEW.uom_id, catalogo.fn_get_uom_base(NEW.articolo_id)),
            NEW.data_attivita,
            'vendite.trgfn_attivita_fattore_alla_data',
            CASE WHEN NEW.uom_operativa_id IS NULL THEN 'uom_id' ELSE 'uom_operativa_id' END,
            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME);
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fattore_alla_data()
IS 'Il fattore di un''attivita'' (vendite.commesse_attivita, vendite.attivita_fatturabili: factor_to_base), quante unita'' base vale un''unita'' dell''attivita''. Quello scritto e'' la fotografia (copiato da un documento sorgente, dalla riga che si rettifica, dall''attivita'' di commessa che si emette) e si rispetta; senza, il fattore alla data dell''attivita'' (data_attivita) dell''unita'' operativa, o dell''unita'' della riga se l''operativa non c''e'', o dell''unita'' base dell''articolo se non c''e'' nessuna delle due (script.fn_fattore_uom_alla_data): 1 per l''unita'' base, la mappatura o la conversione generale in vigore quel giorno per le altre; senza neanche quello, E_UOM_MISSING. Un UPDATE che cambia l''unita'' e non il fattore: il fattore era dell''altra unita'', e si rilegge. BEFORE INSERT e UPDATE OF factor_to_base, uom_operativa_id, uom_id. La quantita'' base (quantita) la porta chi scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
