{% include-markdown "it/dbzero/script/manual/fn_guard_azione.md" %}
# ⚙️ Funzione `fn_guard_azione`

```sql
CREATE FUNCTION fn_guard_azione(p_auth_user_id integer, p_permission_codename character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_azione(p_auth_user_id integer, p_permission_codename character varying)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: applicare un'azione di processo nella prima riga di un verbo di
--   scrittura. La regola la decide script.fn_check_azione_processo (la stessa
--   del backend); qui si solleva quando la risposta e' no.
-- Uso: PERFORM script.fn_guard_azione(
--          NULLIF(current_setting('app.current_user_id', true), '')::integer,
--          'registra_magazzino');
DECLARE
    v_azione_id config.azioni_processo.id%TYPE;
BEGIN
    -- 1. L'azione esiste? Un codename sbagliato e' un chiamante rotto, e
    --    diventerebbe un «non hai i permessi» per tutti.
    SELECT ap.id
      INTO v_azione_id
      FROM config.azioni_processo ap
     WHERE ap.permission_codename = p_permission_codename;

    IF v_azione_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_guard_azione', 'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.azioni_processo',
                               'azione', p_permission_codename),
            NULL::uuid,
            VARIADIC ARRAY[format('azione di processo %s',
                                  COALESCE(p_permission_codename, '(nessuna)'))]);
    END IF;

    -- 2. La risposta della regola. NULL (utente NULL) vale no: fail-closed.
    IF NOT COALESCE(script.fn_check_azione_processo(p_auth_user_id, p_permission_codename), false) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_guard_azione', 'E_PERMESSO_NEGATO',
            jsonb_build_object('azione',       p_permission_codename,
                               'auth_user_id', p_auth_user_id,
                               'senza_utente', p_auth_user_id IS NULL),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_azione(p_auth_user_id integer, p_permission_codename character varying)
IS 'Guard dei verbi di scrittura (modello «una scrittura = un verbo», D-1/D-2 di brief-db-permesso-nel-verbo-di-scrittura): applica un''azione di processo nella prima riga del verbo. La regola NON e'' qui: la decide script.fn_check_azione_processo, la stessa funzione che usa il backend (gate di contesto, identita'' OPERATORE attiva, super admin, override utente, profili). Risposta no -> E_PERMESSO_NEGATO (NON_PERMESSO, lo stesso codice del backend), anche a utente NULL: fail-closed, con senza_utente nel contesto. Azione inesistente -> E_CONFIG_MANCANTE: e'' un chiamante rotto, non un rifiuto (si controlla l''esistenza, non attivo, come fa la regola). L''utente arriva come parametro: il chiamante legge app.current_user_id con l''espressione delle policy (linee-guida-sql §10.4). INVOKER. Brief: brief-db-magazzino-verbi-con-permesso §2.1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
