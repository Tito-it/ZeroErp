# ⚙️ Funzione `trgfn_doc_fornitura_segue_cliente`

```sql
CREATE FUNCTION trgfn_doc_fornitura_segue_cliente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_fornitura_segue_cliente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   La fornitura del documento e' cambiata: la scheda di
    --   prima descrive un'altra fornitura. Si rifa' dall'anagrafica
    --   della nuova. Il selettore lo valida il building block.
    -- =========================================================
    PERFORM vendite.fn_doc_fornitura_da_anagrafica(TG_ARGV[0], NEW.id);
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_fornitura_segue_cliente()
IS 'Building block AFTER UPDATE FOR EACH ROW sulle testate con scheda di fornitura (contratto, offerta), col WHEN sulla coppia istanza_utility_id/utility_id nel montaggio; TG_ARGV[0] = documento (CONTRATTO | OFFERTA). Rifa'' la scheda di fornitura dall''anagrafica della coppia nuova con vendite.fn_doc_fornitura_da_anagrafica (D-5 di Tid, 2026-10-12: la scheda descrive la fornitura; se cambia si rifa'', anche se prima non c''era, D-5-bis). Selettore ignoto: E_DOC_TIPO_NON_GESTITO dal building block. ⚠️ La coppia si cambia solo in bozza (lock di testata), quindi il lock dei satelliti lascia passare. Gemello di vendite.trgfn_doc_indirizzi_seguono_cliente, che sullo stesso cambio porta gli indirizzi. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§8.4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
