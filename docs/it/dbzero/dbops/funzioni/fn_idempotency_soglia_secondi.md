# ⚙️ Funzione `fn_idempotency_soglia_secondi`

```sql
CREATE FUNCTION fn_idempotency_soglia_secondi()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_idempotency_soglia_secondi()
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- il valore grezzo del parametro, prima della validazione
    v_soglia_testo config.parameters.default_value%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La soglia oltre cui una Idempotency-Key in_progress conta
    --   come abbandonata (D6). Default nudo, senza override.
    --   Zero righe lasciano NULL: la validazione lo rifiuta come
    --   parametro mancante.
    -- =========================================================
    SELECT p.default_value INTO v_soglia_testo
      FROM config.parameters p
     WHERE p.code = 'SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI';

    RETURN script.fn_intero_positivo_da_testo(
        v_soglia_testo,
        'SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI',
        'dbops.fn_idempotency_soglia_secondi');
END;
$function$

COMMENT ON FUNCTION dbops.fn_idempotency_soglia_secondi()
IS 'La soglia in secondi oltre cui una Idempotency-Key rimasta in_progress conta come abbandonata e si puo'' riprendere (D6): il default nudo di SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI, senza override, validato da script.fn_intero_positivo_da_testo (E_CONFIG_MANCANTE se assente, vuoto o non intero positivo). La sede unica della lettura: la usano dbops.fn_idempotency_prenota e il presidio di BE-5 all''avvio del backend, che rifiuta di partire se la soglia non supera il timeout di gunicorn. SECURITY INVOKER. Brief: brief-be-verifica-documentazione-api §I.11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
