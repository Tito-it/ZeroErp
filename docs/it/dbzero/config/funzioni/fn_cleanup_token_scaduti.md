{% include-markdown "it/dbzero/config/manual/fn_cleanup_token_scaduti.md" %}
# ⚙️ Funzione `fn_cleanup_token_scaduti`

```sql
CREATE FUNCTION fn_cleanup_token_scaduti(p_giorni_retention integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_cleanup_token_scaduti(p_giorni_retention integer DEFAULT 30)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_deleted integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elimina i token monouso che sono:
    --   - scaduti da piu' di p_giorni_retention giorni, oppure
    --   - utilizzati da piu' di p_giorni_retention giorni.
    --   Pensato per esecuzione periodica (job pgAgent notturno).
    --
    -- Parametri:
    --   p_giorni_retention: giorni di retention dopo scadenza/utilizzo
    --                      (default 30)
    --
    -- Restituisce:
    --   Numero di record eliminati.
    -- =========================================================

    IF p_giorni_retention IS NULL OR p_giorni_retention < 0 THEN
        p_giorni_retention := 30;
    END IF;

    DELETE FROM config.token_monouso
    WHERE
        -- Token scaduti da piu' di N giorni
        (scadenza < now() - make_interval(days => p_giorni_retention))
        OR
        -- Token utilizzati da piu' di N giorni
        (utilizzato = true
         AND utilizzato_at < now() - make_interval(days => p_giorni_retention));

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$function$

COMMENT ON FUNCTION config.fn_cleanup_token_scaduti(p_giorni_retention integer)
IS 'Pulizia periodica token monouso scaduti/utilizzati. Default retention 30 giorni. Ritorna numero record eliminati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
