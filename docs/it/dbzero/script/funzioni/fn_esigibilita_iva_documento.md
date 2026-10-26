{% include-markdown "it/dbzero/script/manual/fn_esigibilita_iva_documento.md" %}
# ⚙️ Funzione `fn_esigibilita_iva_documento`

```sql
CREATE FUNCTION fn_esigibilita_iva_documento(p_emittente_fiscale_id bigint, p_billing_account_id bigint, p_iva_id integer, p_regime_fiscale_rf character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_esigibilita_iva_documento(p_emittente_fiscale_id bigint, p_billing_account_id bigint, p_iva_id integer, p_regime_fiscale_rf character varying DEFAULT NULL::character varying)
 RETURNS TABLE(esigibilita character, split_payment boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: le parti di un documento di vendita per
--   script.fn_esigibilita_iva. p_regime_fiscale_rf = il regime
--   congelato del documento, se c'e' (la fattura); altrimenti
--   quello vivo dell'emittente (script.fn_regime_fiscale_documento).
DECLARE
    v_regime     anagrafiche.emittenti_fiscali.regime_fiscale_rf%TYPE;
    v_per_cassa  config.regimi_fiscali.iva_per_cassa%TYPE;
    v_split      anagrafiche.soggetti.split_payment%TYPE;
    v_piva       anagrafiche.soggetti.partita_iva%TYPE;
BEGIN
    v_regime := script.fn_regime_fiscale_documento(
                    p_emittente_fiscale_id, p_regime_fiscale_rf);

    -- Un codice fuori catalogo resta «regime non noto» (NULL): la FK
    -- lo impedisce sulla colonna viva, ma uno snapshot e' un testo.
    IF v_regime IS NOT NULL THEN
        SELECT rf.iva_per_cassa
          INTO v_per_cassa
          FROM config.regimi_fiscali rf
         WHERE rf.codice_interno = v_regime;
    END IF;

    -- Il cliente: lo stesso percorso che il trigger di riga
    -- usava per la scissione (billing account -> ruolo -> soggetto).
    IF p_billing_account_id IS NOT NULL THEN
        SELECT s.split_payment, s.partita_iva
          INTO v_split, v_piva
          FROM anagrafiche.billing_account ba
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
          JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
         WHERE ba.id = p_billing_account_id;
    END IF;

    RETURN QUERY
    SELECT e.esigibilita, e.split_payment
      FROM script.fn_esigibilita_iva(v_per_cassa, v_split, v_piva, p_iva_id) e;
END;
$function$

COMMENT ON FUNCTION script.fn_esigibilita_iva_documento(p_emittente_fiscale_id bigint, p_billing_account_id bigint, p_iva_id integer, p_regime_fiscale_rf character varying)
IS 'Le parti di un documento di vendita per la regola dell''esigibilita'' (script.fn_esigibilita_iva): il regime per cassa dell''emittente (o quello CONGELATO che il chiamante passa in p_regime_fiscale_rf: la fattura lo prende dallo snapshot dell''intestazione, cosi'' righe e testata dicono lo stesso regime, D-8; quale regime vale lo decide script.fn_regime_fiscale_documento) e scissione e partita IVA del cliente dal billing account. Una catena sola per fattura, preventivi, ordini e DDT (regola del 2). SECURITY INVOKER: un cliente che chi chiama non vede diventa «non noto» e la coppia esce NULL/NULL. Brief: brief-db-esigibilita-iva-per-cassa-emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
