{% include-markdown "it/dbzero/script/manual/fn_sorgente_chiave_id.md" %}
# ⚙️ Funzione `fn_sorgente_chiave_id`

```sql
CREATE FUNCTION fn_sorgente_chiave_id(p_sorgente_uid text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_chiave_id(p_sorgente_uid text)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
-- Scopo: gemella di script.fn_sorgente_chiave_uuid per i tipi a
--   key_selector = id: la chiave testuale nel suo tipo bigint, per cercarla
--   su sorgente_chiave_id. NULL se il testo non e' un intero in forma
--   CANONICA (identica a bigint::text: niente zeri davanti, spazi, '+').
--   Stesse ragioni e stesse cautele della gemella (vedi la sua testata).
DECLARE
    v_chiave script.vw_stato_sorgente.sorgente_chiave_id%TYPE;
BEGIN
    IF NOT pg_input_is_valid(p_sorgente_uid, 'bigint') THEN
        RETURN NULL;
    END IF;
    v_chiave := p_sorgente_uid::bigint;
    IF v_chiave::text <> p_sorgente_uid THEN
        RETURN NULL;
    END IF;
    RETURN v_chiave;
END;
$function$

COMMENT ON FUNCTION script.fn_sorgente_chiave_id(p_sorgente_uid text)
IS 'Building block della sorgente polimorfa (20261005-24), gemella di script.fn_sorgente_chiave_uuid per i tipi a key_selector = id: la chiave testuale nel suo tipo bigint, per cercarla su script.vw_stato_sorgente.sorgente_chiave_id. NULL se il testo non e'' un intero in forma CANONICA (identica a bigint::text: niente zeri davanti, spazi, segno). Mai un errore. Stesse ragioni della gemella. Consumatori: pratiche.fn_stato_sorgente, script.vw_pratica_doc_sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
