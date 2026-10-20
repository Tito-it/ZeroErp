{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_emittenti_fiscali_default_guard.md" %}
# ⚙️ Funzione `trgfn_emittenti_fiscali_default_guard`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_default_guard()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_count     INTEGER;
    v_emittenti INTEGER;
BEGIN
    -- Conteggio emittenti fiscali totali
    SELECT count(*)
      INTO v_emittenti
      FROM anagrafiche.emittenti_fiscali;

    -- Conteggio default attivi
    SELECT count(*)
      INTO v_count
      FROM anagrafiche.emittenti_fiscali_billing_account
     WHERE is_default = true;

    -- Setup iniziale: nessun emittente e nessun default → noop
    IF v_emittenti = 0 AND v_count = 0 THEN
        RETURN NULL;
    END IF;

    -- Vincolo singleton: deve esistere esattamente 1 default
    IF v_count <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            TG_TABLE_SCHEMA,
            TG_NAME,
            'E_EMITTENTE_DEFAULT_SINGLETON',
            jsonb_build_object(
                'found', v_count,
                'emittenti_fiscali', v_emittenti
            ),
            NULL::uuid,
            v_count::text
        );
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()
IS 'Vincolo singleton: deve esistere esattamente un emittente fiscale di default. Errore: E_EMITTENTE_DEFAULT_SINGLETON.';
```

</div>

---
{% include-markdown "signature-core.md" %}
