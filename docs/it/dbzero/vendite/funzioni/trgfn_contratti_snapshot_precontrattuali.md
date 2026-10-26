{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_snapshot_precontrattuali.md" %}
# ⚙️ Funzione `trgfn_contratti_snapshot_precontrattuali`

```sql
CREATE FUNCTION trgfn_contratti_snapshot_precontrattuali()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_snapshot_precontrattuali()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Alla nascita del contratto, la scheda di fornitura
    --   dall'anagrafica della sua coppia (istanza, utility).
    --   La regola sta nel building block: e' la stessa del cambio
    --   di cliente in bozza.
    -- =========================================================
    PERFORM vendite.fn_doc_fornitura_da_anagrafica('CONTRATTO', NEW.id);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_snapshot_precontrattuali()
IS 'AFTER INSERT su vendite.contratti: la scheda di fornitura (vendite.contratti_utilities) dai dati precontrattuali della coppia (istanza, utility) del contratto, con vendite.fn_doc_fornitura_da_anagrafica(''CONTRATTO'', id). Se la coppia non ne ha, il contratto nasce senza scheda. Le chiavi dell''operatore la correggono subito dopo dentro vendite.fn_create_contratto (D-7), e il push dall''offerta la sovrascrive con la scheda dell''offerta. rev 2026-10-12 (brief-db-indirizzi-documento-seguono-il-cliente, D-5): la regola, che prima era scritta qui (con la derivazione del tipo d''uso dalla classe, pricing v5), sta nel building block, che la applica anche al cambio di cliente in bozza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
