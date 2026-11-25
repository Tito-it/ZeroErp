{% include-markdown "it/dbzero/script/manual/fn_guard_livello_area.md" %}
# ⚙️ Funzione `fn_guard_livello_area`

```sql
CREATE FUNCTION fn_guard_livello_area(p_auth_user_id integer, p_area_schema_db character varying, p_livello_minimo config.livello_accesso)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_livello_area(p_auth_user_id integer, p_area_schema_db character varying, p_livello_minimo config.livello_accesso)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: applicare un livello minimo su un'AREA, senza oggetto, nella prima
--   riga di un verbo di scrittura. E' il gate del backend sulle view che non
--   dichiarano un modello: decide il livello sull'area. La regola la decide
--   script.fn_resolve_livello_area (la stessa del backend: gate di contesto,
--   SUPER_ADMIN, override, profilo).
-- Uso: PERFORM script.fn_guard_livello_area(v_utente, 'vendite', 'TUTTO');
-- Gemella di script.fn_guard_livello (oggetto, con la ricaduta sull'area):
--   stesso codice e stessa forma del rifiuto.
DECLARE
    v_livello config.user_override_aree.livello%TYPE;
BEGIN
    IF p_auth_user_id IS NOT NULL AND p_area_schema_db IS NOT NULL THEN
        v_livello := script.fn_resolve_livello_area(p_auth_user_id, p_area_schema_db);
    END IF;

    -- ⛔ L'enum e' TUTTO < LETTURA < BLOCCATO: sotto il minimo vuol dire
    --    livello > minimo. NULL da qualunque parte vale no (fail-closed).
    IF v_livello IS NULL OR p_livello_minimo IS NULL
       OR v_livello > p_livello_minimo THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_guard_livello_area', 'E_PERMESSO_NEGATO',
            jsonb_build_object('area',           p_area_schema_db,
                               'livello',        v_livello,
                               'livello_minimo', p_livello_minimo,
                               'auth_user_id',   p_auth_user_id,
                               'senza_utente',   p_auth_user_id IS NULL),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_livello_area(p_auth_user_id integer, p_area_schema_db character varying, p_livello_minimo config.livello_accesso)
IS 'Guard di prima riga di un verbo: il livello minimo su un''AREA funzionale, senza oggetto (script.fn_resolve_livello_area: gate di contesto, SUPER_ADMIN, override, profilo). Sotto il minimo, o senza utente, E_PERMESSO_NEGATO, con la stessa forma di script.fn_guard_livello, che decide sull''oggetto con la ricaduta sull''area. E'' il gate del backend sulle view senza modello. Lo chiamano pagamenti.fn_annulla_sistemazione (area pagamenti) e i due verbi del passaggio del lotto, vendite.fn_annulla_lotto_da_draft e vendite.fn_riporta_lotto_a_draft, quando la riga del passaggio non ha azione (area vendite).';
```

</div>

---
{% include-markdown "signature-core.md" %}
