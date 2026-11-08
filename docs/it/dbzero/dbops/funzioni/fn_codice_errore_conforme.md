{% include-markdown "it/dbzero/dbops/manual/fn_codice_errore_conforme.md" %}
# ⚙️ Funzione `fn_codice_errore_conforme`

```sql
CREATE FUNCTION fn_codice_errore_conforme(p_codice text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_codice_errore_conforme(p_codice text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- Scopo: il codice segue la convenzione E_/W_ (lettere maiuscole, cifre,
    --   underscore)? La sola sede della regola.
    SELECT p_codice ~ '^[EW]_[A-Z0-9_]+$';
$function$

COMMENT ON FUNCTION dbops.fn_codice_errore_conforme(p_codice text)
IS 'La convenzione dei codici d''errore: true se il codice comincia con E_ (errore, si solleva) o W_ (avviso, si scrive solo nel log) e prosegue con lettere maiuscole, cifre e underscore. NULL per un codice NULL. E'' la sola sede della regola: la chiamano il CHECK chk_messaggi_errore_codici_legacy_non_conforme (il registro dei codici fuori convenzione accetta solo codici che non la rispettano) e il guardrail di CI scripts/sql/guardrail_codice_errore_strutturato.sql. IMMUTABLE: entra in un CHECK.';
```

</div>

---
{% include-markdown "signature-core.md" %}
