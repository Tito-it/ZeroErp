{% include-markdown "it/dbzero/script/manual/fn_regime_fiscale_documento.md" %}
# ⚙️ Funzione `fn_regime_fiscale_documento`

```sql
CREATE FUNCTION fn_regime_fiscale_documento(p_emittente_fiscale_id bigint, p_regime_fiscale_rf character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_regime_fiscale_documento(p_emittente_fiscale_id bigint, p_regime_fiscale_rf character varying DEFAULT NULL::character varying)
 RETURNS character varying
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il regime fiscale di un documento. p_regime_fiscale_rf =
--   il regime congelato del documento, se c'e' (la fattura lo
--   prende dallo snapshot); altrimenti quello vivo dell'emittente.
DECLARE
    v_regime  anagrafiche.emittenti_fiscali.regime_fiscale_rf%TYPE;
BEGIN
    v_regime := NULLIF(btrim(p_regime_fiscale_rf), '');

    IF v_regime IS NULL AND p_emittente_fiscale_id IS NOT NULL THEN
        SELECT ef.regime_fiscale_rf
          INTO v_regime
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.id = p_emittente_fiscale_id;
    END IF;

    RETURN v_regime;
END;
$function$

COMMENT ON FUNCTION script.fn_regime_fiscale_documento(p_emittente_fiscale_id bigint, p_regime_fiscale_rf character varying)
IS 'Il regime fiscale di un documento: quello CONGELATO che il chiamante passa in p_regime_fiscale_rf, se non e'' vuoto (la fattura lo prende dallo snapshot dell''intestazione, D-8), altrimenti quello vivo dell''emittente; NULL se non ci sono ne'' l''uno ne'' l''altro. Un congelato fuori catalogo esce com''e'': che cosa significa lo dice chi legge config.regimi_fiscali. Una regola sola per l''esigibilita'' delle righe (script.fn_esigibilita_iva_documento) e per le annotazioni della fattura (vendite.fn_regime_fiscale_fattura). Brief: brief-db-esigibilita-iva-per-cassa-emittente (R-DB-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
