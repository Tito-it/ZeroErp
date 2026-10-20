{% include-markdown "it/dbzero/script/manual/fn_guard_livello.md" %}
# ⚙️ Funzione `fn_guard_livello`

```sql
CREATE FUNCTION fn_guard_livello(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_livello_minimo config.livello_accesso)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_livello(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_livello_minimo config.livello_accesso)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: applicare un livello minimo su un oggetto nella prima riga di un verbo
--   di scrittura. La regola la decide script.fn_resolve_livello_oggetto (la
--   stessa del backend), con l'area di script.fn_area_di_oggetto.
-- Uso: PERFORM script.fn_guard_livello(
--          NULLIF(current_setting('app.current_user_id', true), '')::integer,
--          'magazzino', 'causali', 'TUTTO');
DECLARE
    v_area    config.aree_funzionali.schema_db%TYPE;
    v_livello config.user_override_oggetti.livello%TYPE;
BEGIN
    IF p_auth_user_id IS NOT NULL AND p_app_label IS NOT NULL
       AND p_model_name IS NOT NULL THEN
        v_area    := script.fn_area_di_oggetto(p_app_label, p_model_name);
        v_livello := script.fn_resolve_livello_oggetto(
                         p_auth_user_id, p_app_label, p_model_name, v_area);
    END IF;

    -- ⛔ L'enum e' TUTTO < LETTURA < BLOCCATO: sotto il minimo vuol dire
    --    livello > minimo. NULL da qualunque parte vale no (fail-closed).
    IF v_livello IS NULL OR p_livello_minimo IS NULL
       OR v_livello > p_livello_minimo THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_guard_livello', 'E_PERMESSO_NEGATO',
            jsonb_build_object('app_label',      p_app_label,
                               'model_name',     p_model_name,
                               'area',           v_area,
                               'livello',        v_livello,
                               'livello_minimo', p_livello_minimo,
                               'auth_user_id',   p_auth_user_id,
                               'senza_utente',   p_auth_user_id IS NULL),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_livello(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_livello_minimo config.livello_accesso)
IS 'Guard dei verbi di scrittura, forma «livello su un oggetto» (D-2, D-5 di brief-db-permesso-nel-verbo-di-scrittura; gemello di script.fn_guard_azione). Il verbo dichiara l''OGGETTO (app_label, model_name) e il livello minimo; l''area la ricava script.fn_area_di_oggetto e la regola la decide script.fn_resolve_livello_oggetto, la stessa del backend (gate di contesto, identita'' OPERATORE attiva, super admin, override utente sull''oggetto, poi l''area). Sotto il minimo -> E_PERMESSO_NEGATO (NON_PERMESSO, lo stesso codice del backend), anche a utente, oggetto o minimo NULL: fail-closed. ⛔ L''enum livello_accesso e'' ordinato TUTTO < LETTURA < BLOCCATO: il rifiuto e'' livello > minimo. INVOKER. Brief: brief-db-pannello-config-verbo-generico §3.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
