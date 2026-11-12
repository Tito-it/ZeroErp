{% include-markdown "it/dbzero/script/manual/fn_codice_dominio.md" %}
# ⚙️ Funzione `fn_codice_dominio`

```sql
CREATE FUNCTION fn_codice_dominio(p_sqlstate text, p_vincolo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_codice_dominio(p_sqlstate text, p_vincolo text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- Per un 23505 o un 23514 il CONSTRAINT e' il nome di un vincolo,
    -- non un codice: conta solo col P0001 di fn_log_and_raise_error.
    SELECT CASE
             WHEN p_sqlstate = 'P0001' AND NULLIF(p_vincolo, '') IS NOT NULL
               THEN p_vincolo
           END;
$function$

COMMENT ON FUNCTION script.fn_codice_dominio(p_sqlstate text, p_vincolo text)
IS 'Il codice di dominio di un errore catturato, letto dalla sua diagnostica (RETURNED_SQLSTATE, CONSTRAINT_NAME): il CONSTRAINT quando lo SQLSTATE e'' P0001 e il CONSTRAINT non e'' vuoto, il contratto di script.fn_log_and_raise_error; NULL altrimenti. Per un errore che non e'' di dominio (un 23505, un 23514) il CONSTRAINT e'' il nome di un vincolo, non un codice, e la risposta e'' NULL. Non sceglie un ripiego: chi la legge decide che cosa scrivere quando non c''e'' un codice. La leggono vendite.fn_batch_upsert_commessa_attivita e maintenance.fn_run_and_log.';
```

</div>

---
{% include-markdown "signature-core.md" %}
