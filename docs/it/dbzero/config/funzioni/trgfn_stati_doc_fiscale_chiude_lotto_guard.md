{% include-markdown "it/dbzero/config/manual/trgfn_stati_doc_fiscale_chiude_lotto_guard.md" %}
# ⚙️ Funzione `trgfn_stati_doc_fiscale_chiude_lotto_guard`

```sql
CREATE FUNCTION trgfn_stati_doc_fiscale_chiude_lotto_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_stati_doc_fiscale_chiude_lotto_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_cnt_true INTEGER;
BEGIN
    -- Conteggio righe con chiude_lotto = true
    SELECT COUNT(*)
      INTO v_cnt_true
      FROM config.stati_doc_fiscale
     WHERE chiude_lotto IS TRUE;

    -- Vincolo singleton: esattamente 1 riga con chiude_lotto = true
    IF v_cnt_true <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            TG_NAME,
            'E_CHIUDE_LOTTO_SINGLETON',
            jsonb_build_object(
                'current_true_count', v_cnt_true
            ),
            NULL::uuid,
            v_cnt_true::text
        );
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION config.trgfn_stati_doc_fiscale_chiude_lotto_guard()
IS 'Guard singleton chiude_lotto: esattamente 1 riga TRUE in config.stati_doc_fiscale. Errore: E_CHIUDE_LOTTO_SINGLETON.';
```

</div>

---
{% include-markdown "signature-core.md" %}
