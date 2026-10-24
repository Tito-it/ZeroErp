{% include-markdown "it/dbzero/vendite/manual/fn_regime_fiscale_fattura.md" %}
# ⚙️ Funzione `fn_regime_fiscale_fattura`

```sql
CREATE FUNCTION fn_regime_fiscale_fattura(p_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_regime_fiscale_fattura(p_fattura_id bigint)
 RETURNS character varying
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il regime fiscale della fattura p_fattura_id: quello
--   congelato nello snapshot, se c'e', altrimenti quello vivo
--   dell'emittente (D-8).
DECLARE
    v_emittente_id  anagrafiche.emittenti_fiscali.id%TYPE;
    v_regime_snap   anagrafiche.emittenti_fiscali.regime_fiscale_rf%TYPE;
BEGIN
    SELECT ef.id,
           f.emittente_snapshot ->> 'regime_fiscale_rf'
      INTO v_emittente_id, v_regime_snap
      FROM vendite.fatture f
      LEFT JOIN anagrafiche.emittenti_fiscali ef
             ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
     WHERE f.id = p_fattura_id;

    RETURN script.fn_regime_fiscale_documento(v_emittente_id, v_regime_snap);
END;
$function$

COMMENT ON FUNCTION vendite.fn_regime_fiscale_fattura(p_fattura_id bigint)
IS 'Il regime fiscale di una fattura: quello congelato nello snapshot dell''intestazione (emittente_snapshot ->> regime_fiscale_rf) se c''e'', altrimenti quello vivo dell''emittente (emittente_soggetto_ruolo_id -> emittenti_fiscali); la regola e'' script.fn_regime_fiscale_documento. NULL se la fattura non c''e'' o non ha emittente. Una sede per i due lettori: l''esigibilita'' delle righe (vendite.fn_esigibilita_iva_fattura) e le annotazioni in stampa (vendite.fn_annotazioni_fattura). Brief: brief-db-esigibilita-iva-per-cassa-emittente (R-DB-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
