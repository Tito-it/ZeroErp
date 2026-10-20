{% include-markdown "it/dbzero/script/manual/fn_current_identita_context.md" %}
# ⚙️ Funzione `fn_current_identita_context`

```sql
CREATE FUNCTION fn_current_identita_context()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_current_identita_context()
 RETURNS TABLE(current_identita_id bigint, ruolo_applicativo config.ruolo_applicativo, soggetto_ruolo_id bigint)
 LANGUAGE sql
 STABLE
AS $function$
    -- Lettura tipizzata dei tre GUC di sessione del contesto
    -- identita (§4.7 WIP multi-face-auth). Fail-soft: ogni
    -- campo ritorna NULL se il GUC non e' settato o e' vuoto.
    -- Invariante "tutto o niente": il middleware deve
    -- popolare i tre GUC insieme. Se UNO e' NULL le policy
    -- fn_scope_* falliscono fail-closed.
    SELECT
        NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
        NULLIF(current_setting('app.ruolo_applicativo',   true), '')::config.ruolo_applicativo,
        NULLIF(current_setting('app.soggetto_ruolo_id',   true), '')::bigint;
$function$

COMMENT ON FUNCTION script.fn_current_identita_context()
IS 'Restituisce il contesto identita della sessione corrente (app.current_identita_id, app.ruolo_applicativo, app.soggetto_ruolo_id) come record tipato. Fail-soft su GUC mancanti (NULL). §4.7 WIP multi-face-auth.';
```

</div>

---
{% include-markdown "signature-core.md" %}
