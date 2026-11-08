# ⚙️ Funzione `fn_ddt_muove_merce`

```sql
CREATE FUNCTION fn_ddt_muove_merce(p_ddt vendite.ddt)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_muove_merce(p_ddt vendite.ddt)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la bolla muove merce? La causale di trasporto e' mappata
--   (D-L3-g) E almeno una voce e' gestita (D-L3-f). E' la condizione
--   della porta del registro (D-L3-e, affinata da Tid il 28-09): solo
--   una bolla che muove merce deve passare dal verbo.
BEGIN
    RETURN vendite.fn_ddt_causale_magazzino(p_ddt) IS NOT NULL
       AND EXISTS (SELECT 1 FROM vendite.fn_ddt_merce_da_movimentare(p_ddt));
END;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_muove_merce(p_ddt vendite.ddt)
IS 'La bolla muove merce: la sua causale di trasporto e'' mappata su una causale di magazzino (fn_ddt_causale_magazzino) e almeno una voce e'' gestita (fn_ddt_merce_da_movimentare). Condizione della porta del registro: il verbo vendite.fn_cambia_stato_ddt, la sola strada dello stato (script.trgfn_doc_stato_solo_dal_verbo), scarica all''emissione e scrive gli arrivi alla consegna solo per una bolla che muove merce. La leggono anche la check della merce e i presidi dbops.vw_ddt_emessi_senza_scarico e dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo (D-L3-e). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt; rev 2026-11-09 la porta nominata (M22 di brief-db-revisione-dbops).';
```

</div>

---
{% include-markdown "signature-core.md" %}
