{% include-markdown "it/dbzero/vendite/manual/fn_esigibilita_iva_fattura.md" %}
# ⚙️ Funzione `fn_esigibilita_iva_fattura`

```sql
CREATE FUNCTION fn_esigibilita_iva_fattura(p_fattura_id bigint, p_iva_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_esigibilita_iva_fattura(p_fattura_id bigint, p_iva_id integer)
 RETURNS TABLE(esigibilita character, split_payment boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la coppia (esigibilita, split_payment) di una riga della
--   fattura p_fattura_id con codice IVA p_iva_id. Regime: quello
--   della fattura (vendite.fn_regime_fiscale_fattura: lo snapshot,
--   se c'e', altrimenti quello vivo, D-8).
DECLARE
    v_emittente_id  anagrafiche.emittenti_fiscali.id%TYPE;
    v_ba_id         vendite.fatture.billing_account_id%TYPE;
BEGIN
    SELECT ef.id,
           f.billing_account_id
      INTO v_emittente_id, v_ba_id
      FROM vendite.fatture f
      LEFT JOIN anagrafiche.emittenti_fiscali ef
             ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
     WHERE f.id = p_fattura_id;

    RETURN QUERY
    SELECT e.esigibilita, e.split_payment
      FROM script.fn_esigibilita_iva_documento(
               v_emittente_id, v_ba_id, p_iva_id,
               vendite.fn_regime_fiscale_fattura(p_fattura_id)) e;
END;
$function$

COMMENT ON FUNCTION vendite.fn_esigibilita_iva_fattura(p_fattura_id bigint, p_iva_id integer)
IS 'La coppia (esigibilita, split_payment) di una riga di fattura: emittente dalla testata (emittente_soggetto_ruolo_id -> emittenti_fiscali), cliente dal billing account, e il REGIME della fattura da vendite.fn_regime_fiscale_fattura (quello congelato nello snapshot dell''intestazione se c''e'', quello vivo altrimenti): righe, testata e annotazioni in stampa dicono lo stesso regime (D-8). La regola e'' script.fn_esigibilita_iva, la catena delle parti script.fn_esigibilita_iva_documento. La chiamano vendite.trgfn_fatture_righe_guard_normalize e vendite.fn_ricalcola_riepilogo_iva_fattura. Brief: brief-db-esigibilita-iva-per-cassa-emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
