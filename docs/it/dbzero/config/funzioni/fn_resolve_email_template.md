{% include-markdown "it/dbzero/config/manual/fn_resolve_email_template.md" %}
# ⚙️ Funzione `fn_resolve_email_template`

```sql
CREATE FUNCTION fn_resolve_email_template(p_codice character varying, p_unita_organizzativa_id integer, p_tipo_prestazione_id integer, p_lingua character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_resolve_email_template(p_codice character varying, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_tipo_prestazione_id integer DEFAULT NULL::integer, p_lingua character varying DEFAULT 'it'::character varying)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_result jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve il template email dato codice, reparto,
    --   tipo prestazione e lingua.
    --   Catena di fallback (primo trovato attivo):
    --     1. Reparto + tipo prestazione + lingua
    --     2. Reparto + lingua (senza tipo prestazione)
    --     3. Sistema + tipo prestazione + lingua
    --     4. Sistema + lingua
    --     5. Sistema + lingua 'it' (fallback finale)
    --
    -- Parametri:
    --   p_codice: codice tipo template (es. COMUNICAZIONE_PRATICA)
    --   p_unita_organizzativa_id: ID reparto (NULL = solo sistema)
    --   p_tipo_prestazione_id: ID tipo prestazione (NULL = generico)
    --   p_lingua: codice lingua ISO (default 'it')
    --
    -- Restituisce:
    --   JSONB con: id, codice, oggetto, corpo_html, corpo_testo,
    --   variabili_disponibili, lingua.
    --   NULL se nessun template attivo trovato.
    -- =========================================================

    IF p_codice IS NULL THEN
        RETURN NULL;
    END IF;

    -- 1. Reparto + tipo prestazione + lingua
    IF p_unita_organizzativa_id IS NOT NULL AND p_tipo_prestazione_id IS NOT NULL THEN
        SELECT jsonb_build_object(
            'id',                     et.id,
            'codice',                 et.codice,
            'oggetto',                et.oggetto,
            'corpo_html',             et.corpo_html,
            'corpo_testo',            et.corpo_testo,
            'variabili_disponibili',  et.variabili_disponibili,
            'lingua',                 et.lingua
        )
        INTO v_result
        FROM config.email_template et
        WHERE et.codice = p_codice
          AND et.unita_organizzativa_id = p_unita_organizzativa_id
          AND et.tipo_prestazione_id = p_tipo_prestazione_id
          AND et.lingua = p_lingua
          AND et.attivo = true;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;
    END IF;

    -- 2. Reparto + lingua (senza tipo prestazione)
    IF p_unita_organizzativa_id IS NOT NULL THEN
        SELECT jsonb_build_object(
            'id',                     et.id,
            'codice',                 et.codice,
            'oggetto',                et.oggetto,
            'corpo_html',             et.corpo_html,
            'corpo_testo',            et.corpo_testo,
            'variabili_disponibili',  et.variabili_disponibili,
            'lingua',                 et.lingua
        )
        INTO v_result
        FROM config.email_template et
        WHERE et.codice = p_codice
          AND et.unita_organizzativa_id = p_unita_organizzativa_id
          AND et.tipo_prestazione_id IS NULL
          AND et.lingua = p_lingua
          AND et.attivo = true;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;
    END IF;

    -- 3. Sistema + tipo prestazione + lingua
    IF p_tipo_prestazione_id IS NOT NULL THEN
        SELECT jsonb_build_object(
            'id',                     et.id,
            'codice',                 et.codice,
            'oggetto',                et.oggetto,
            'corpo_html',             et.corpo_html,
            'corpo_testo',            et.corpo_testo,
            'variabili_disponibili',  et.variabili_disponibili,
            'lingua',                 et.lingua
        )
        INTO v_result
        FROM config.email_template et
        WHERE et.codice = p_codice
          AND et.unita_organizzativa_id IS NULL
          AND et.tipo_prestazione_id = p_tipo_prestazione_id
          AND et.lingua = p_lingua
          AND et.attivo = true;

        IF v_result IS NOT NULL THEN
            RETURN v_result;
        END IF;
    END IF;

    -- 4. Sistema + lingua richiesta (senza tipo prestazione)
    SELECT jsonb_build_object(
        'id',                     et.id,
        'codice',                 et.codice,
        'oggetto',                et.oggetto,
        'corpo_html',             et.corpo_html,
        'corpo_testo',            et.corpo_testo,
        'variabili_disponibili',  et.variabili_disponibili,
        'lingua',                 et.lingua
    )
    INTO v_result
    FROM config.email_template et
    WHERE et.codice = p_codice
      AND et.unita_organizzativa_id IS NULL
      AND et.tipo_prestazione_id IS NULL
      AND et.lingua = p_lingua
      AND et.attivo = true;

    IF v_result IS NOT NULL THEN
        RETURN v_result;
    END IF;

    -- 5. Fallback finale: sistema + lingua 'it'
    IF p_lingua <> 'it' THEN
        SELECT jsonb_build_object(
            'id',                     et.id,
            'codice',                 et.codice,
            'oggetto',                et.oggetto,
            'corpo_html',             et.corpo_html,
            'corpo_testo',            et.corpo_testo,
            'variabili_disponibili',  et.variabili_disponibili,
            'lingua',                 et.lingua
        )
        INTO v_result
        FROM config.email_template et
        WHERE et.codice = p_codice
          AND et.unita_organizzativa_id IS NULL
          AND et.tipo_prestazione_id IS NULL
          AND et.lingua = 'it'
          AND et.attivo = true;
    END IF;

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION config.fn_resolve_email_template(p_codice character varying, p_unita_organizzativa_id integer, p_tipo_prestazione_id integer, p_lingua character varying)
IS 'Risolve template email. Fallback a 5 livelli: reparto+tipo_prestazione+lingua -> reparto+lingua -> sistema+tipo_prestazione+lingua -> sistema+lingua -> sistema+it.';
```

</div>

---
{% include-markdown "signature-core.md" %}
