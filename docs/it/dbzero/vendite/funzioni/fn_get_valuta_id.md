{% include-markdown "it/dbzero/vendite/manual/fn_get_valuta_id.md" %}
# ⚙️ Funzione `fn_get_valuta_id`

```sql
CREATE FUNCTION fn_get_valuta_id(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_valuta_id(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_valuta_id config.valute.id%TYPE;
BEGIN
    -- Risoluzione con fallback: BA → emittente → gestore
    IF p_billing_account_id IS NOT NULL THEN
        SELECT ba.valuta_id INTO v_valuta_id
          FROM anagrafiche.billing_account ba WHERE ba.id = p_billing_account_id;
    END IF;

    IF v_valuta_id IS NULL AND p_emittente_soggetto_ruolo_id IS NOT NULL THEN
        SELECT ef.valuta_id INTO v_valuta_id
          FROM anagrafiche.emittenti_fiscali ef WHERE ef.soggetto_ruolo_id = p_emittente_soggetto_ruolo_id;
    END IF;

    IF v_valuta_id IS NULL THEN
        SELECT g.valuta_id INTO v_valuta_id
          FROM anagrafiche.gestori g ORDER BY g.id LIMIT 1;
    END IF;

    IF v_valuta_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_valuta_id', 'E_CONFIG_MANCANTE',
            jsonb_build_object('billing_account_id', p_billing_account_id, 'emittente', p_emittente_soggetto_ruolo_id),
            NULL::uuid, 'valuta non risolta (BA/emittente/gestore)');
    END IF;

    RETURN v_valuta_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_valuta_id(p_billing_account_id bigint, p_emittente_soggetto_ruolo_id bigint)
IS 'Risoluzione valuta_id: BA → emittente → gestore (fallback).';
```

</div>

---
{% include-markdown "signature-core.md" %}
