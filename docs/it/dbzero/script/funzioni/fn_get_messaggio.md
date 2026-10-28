{% include-markdown "it/dbzero/script/manual/fn_get_messaggio.md" %}
# ⚙️ Funzione `fn_get_messaggio`

```sql
CREATE FUNCTION fn_get_messaggio(p_codice text, p_valore text, p_lingua text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_messaggio(p_codice text, p_valore text DEFAULT NULL::text, p_lingua text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    tmpl       text;
    lingua_eff text;
BEGIN
    -- =========================================================
    -- Scopo (post 23-04-2026, i18n incrementale):
    --   Ritorna il template messaggio per (codice, lingua).
    --   Se la lingua richiesta non ha riga, fallback su 'it'
    --   (codice ISO default progetto). Se nemmeno 'it' ha
    --   riga -> placeholder "[MESSAGGIO NON DEFINITO: ...]"
    --   (comportamento legacy, nessuna regressione).
    --
    -- Risoluzione lingua:
    --   1. parametro p_lingua (priorita' max, override
    --      esplicito)
    --   2. GUC myapp.user_language (impostata dal middleware
    --      BE per-request)
    --   3. 'it' (fallback finale)
    --
    -- Volatilita': STABLE (legge tabella, IMMUTABLE sarebbe
    -- bug di caching. Post-fix 23-04-2026).
    -- =========================================================

    lingua_eff := coalesce(
        p_lingua,
        current_setting('myapp.user_language', true),
        'it'
    );

    -- Single-query con preferenza per lingua_eff, fallback 'it'.
    -- ORDER BY booleano: la riga con lingua = lingua_eff ha
    -- valore TRUE (ordinato prima di FALSE in DESC), quindi
    -- vince. Se lingua_eff = 'it' la IN degenera, LIMIT 1 OK.
    SELECT messaggio
      INTO tmpl
      FROM config.messaggi_errore
     WHERE codice = p_codice
       AND lingua IN (lingua_eff, 'it')
     ORDER BY (lingua = lingua_eff) DESC
     LIMIT 1;

    IF tmpl IS NULL THEN
        RETURN '[MESSAGGIO NON DEFINITO: ' || p_codice || ']';
    END IF;

    IF p_valore IS NOT NULL THEN
        RETURN format(tmpl, p_valore);
    ELSE
        RETURN tmpl;
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_get_messaggio(p_codice text, p_valore text, p_lingua text)
IS 'Restituisce il messaggio formattato per (codice, lingua). Post 23-04-2026: fallback su lingua=''it'' se la lingua richiesta non ha riga (supporta rollout incrementale traduzioni EN). Se nemmeno ''it'' ha riga -> placeholder "[MESSAGGIO NON DEFINITO: <codice>]". Volatilita'' STABLE (era IMMUTABLE per errore, corretto).';
```

</div>

---
{% include-markdown "signature-core.md" %}
