{% include-markdown "it/dbzero/vendite/manual/fn_esigibilita_iva_fattura.md" %}
# ⚙️ Funzione `fn_esigibilita_iva_fattura`

```sql
CREATE FUNCTION fn_esigibilita_iva_fattura(p_fattura_id bigint, p_iva_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_esigibilita_iva_fattura(p_fattura_id bigint, p_iva_id integer)
 RETURNS TABLE(esigibilita character, split_payment boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la coppia (esigibilita, split_payment) di una riga della
--   fattura p_fattura_id con codice IVA p_iva_id. Regime: quello
--   congelato nello snapshot, se c'e', altrimenti quello vivo (D-8).
DECLARE
    v_emittente_id  anagrafiche.emittenti_fiscali.id%TYPE;
    v_ba_id         vendite.fatture.billing_account_id%TYPE;
    v_regime_snap   anagrafiche.emittenti_fiscali.regime_fiscale_rf%TYPE;
BEGIN
    SELECT ef.id,
           f.billing_account_id,
           f.emittente_snapshot ->> 'regime_fiscale_rf'
      INTO v_emittente_id, v_ba_id, v_regime_snap
      FROM vendite.fatture f
      LEFT JOIN anagrafiche.emittenti_fiscali ef
             ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
     WHERE f.id = p_fattura_id;

    RETURN QUERY
    SELECT e.esigibilita, e.split_payment
      FROM script.fn_esigibilita_iva_documento(
               v_emittente_id, v_ba_id, p_iva_id, v_regime_snap) e;
END;
$function$

COMMENT ON FUNCTION vendite.fn_esigibilita_iva_fattura(p_fattura_id bigint, p_iva_id integer)
IS 'La coppia (esigibilita, split_payment) di una riga di fattura: emittente dalla testata (emittente_soggetto_ruolo_id -> emittenti_fiscali), cliente dal billing account, e il REGIME congelato nello snapshot dell''intestazione se c''e'' (emittente_snapshot ->> regime_fiscale_rf), quello vivo altrimenti: righe e testata dicono lo stesso regime (D-8). La regola e'' script.fn_esigibilita_iva, la catena delle parti script.fn_esigibilita_iva_documento. La chiamano vendite.trgfn_fatture_righe_guard_normalize e vendite.fn_ricalcola_riepilogo_iva_fattura. Brief: brief-db-esigibilita-iva-per-cassa-emittente.';
```

---
{% include-markdown "signature-core.md" %}
