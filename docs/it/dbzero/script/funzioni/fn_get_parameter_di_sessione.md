{% include-markdown "it/dbzero/script/manual/fn_get_parameter_di_sessione.md" %}
# ⚙️ Funzione `fn_get_parameter_di_sessione`

```sql
CREATE FUNCTION fn_get_parameter_di_sessione(p_code character varying, p_chi text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_di_sessione(p_code character varying, p_chi text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_user_id    config.parameter_overrides.django_user_id%TYPE :=
        NULLIF(current_setting('app.current_user_id', true), '')::integer;
    v_emittente  config.parameter_overrides.emittente_fiscale_id%TYPE :=
        NULLIF(current_setting('app.current_emittente_id', true), '')::bigint;
    -- %TYPE[] non esiste: tipo esplicito, come in fn_get_parameter_full
    -- (django_group_id e' integer).
    v_group_ids  integer[];
    -- un interruttore calcolato qui: niente colonna da ancorare
    v_gruppi_leggibili boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il valore di p_code con la cascata degli override
    --   (utente, gruppo, emittente, funzione, default), col
    --   contesto preso dalla sessione. p_chi: chi lo chiede,
    --   per il livello «function» e per il log.
    --
    -- Regole:
    --   - GUC vuota o assente = NULL: il livello salta;
    --   - i gruppi si leggono solo se la tabella di Django
    --     c'e' e il ruolo la puo' leggere: altrimenti il
    --     livello resta spento, senza errore (e' una proposta);
    --   - nessuna validazione del valore: e' del lettore.
    -- =========================================================
    IF v_user_id IS NOT NULL THEN
        -- Per OID: un nome in uno schema senza USAGE solleva
        -- 42501 anche dentro to_regclass.
        SELECT has_schema_privilege(n.oid, 'USAGE')
               AND has_table_privilege(c.oid, 'SELECT')
          INTO v_gruppi_leggibili
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'django'
           AND c.relname = 'auth_user_groups';

        -- Zero righe (tabella assente) lascia NULL: IS TRUE.
        IF v_gruppi_leggibili IS TRUE THEN
            SELECT array_agg(ug.group_id ORDER BY ug.group_id)
              INTO v_group_ids
              FROM django.auth_user_groups ug
             WHERE ug.user_id = v_user_id;
        END IF;
    END IF;

    RETURN script.fn_get_parameter_full(
        p_code                 => p_code,
        p_emittente_fiscale_id => v_emittente,
        p_django_user_id       => v_user_id,
        p_group_ids            => v_group_ids,
        p_function_name        => p_chi);
END;
$function$

COMMENT ON FUNCTION script.fn_get_parameter_di_sessione(p_code character varying, p_chi text)
IS 'BB: il valore di un parametro con la cascata degli override di script.fn_get_parameter_full, col contesto preso dalla SESSIONE invece che dal chiamante. Per i lettori dentro il database (trigger, madri), che non ricevono utente, gruppi ed emittente: il backend li passa da se''. Utente da app.current_user_id (auth_user.id = parameter_overrides.django_user_id); gruppi da django.auth_user_groups, letti solo se la tabella esiste e il ruolo la legge (cercata per OID nel catalogo), altrimenti il livello gruppo resta spento senza errore: e'' una proposta, non apre accessi (zeroerp_job non ha USAGE su django; su un database senza le tabelle di Django la tabella non c''e''); emittente da app.current_emittente_id; funzione da p_chi (chi chiede). La categoria cliente non fa parte della sessione: resta NULL. Il livello «sessione» degli override non c''e'' piu'' (2026-11-09): la GUC app.session_key non si legge. GUC vuota o assente = livello saltato. Non valida il valore: e'' compito del lettore. Primo lettore: script.fn_stato_proposto_id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
