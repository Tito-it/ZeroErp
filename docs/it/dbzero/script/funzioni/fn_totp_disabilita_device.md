{% include-markdown "it/dbzero/script/manual/fn_totp_disabilita_device.md" %}
# ⚙️ Funzione `fn_totp_disabilita_device`

```sql
CREATE FUNCTION fn_totp_disabilita_device(p_auth_user_id integer, p_motivo text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_totp_disabilita_device(p_auth_user_id integer, p_motivo text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: cancellare il device del secondo fattore di una credenziale:
--   l'utente stesso, oppure un altro (migratore o SUPER_ADMIN) con
--   un motivo. Dal server lascia la traccia nell'audit degli accessi.
DECLARE
    v_utente     integer;
    v_device_id  config.auth_totp_device.id%TYPE;
    -- Esplicito: un flag calcolato, non una colonna.
    v_dal_server boolean := false;
BEGIN
    -- Prima riga: chi agisce. Se non e' la credenziale stessa deve
    -- essere la sessione del migratore o un SUPER_ADMIN, con un motivo.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    IF v_utente IS DISTINCT FROM p_auth_user_id THEN
        v_dal_server := dbops.fn_sessione_del_migratore();
        IF NOT v_dal_server THEN
            PERFORM script.fn_guard_super_admin(v_utente);
        END IF;

        IF p_motivo IS NULL OR btrim(p_motivo) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_totp_disabilita_device', 'E_TOTP_MOTIVO_OBBLIGATORIO',
                jsonb_build_object('campo', 'motivo', 'auth_user_id', p_auth_user_id),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]);
        END IF;
    END IF;

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_disabilita_device', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_totp_disabilita_device',
                           'credenziale assente o non valida']);
    END IF;

    DELETE FROM config.auth_totp_device d
     WHERE d.auth_user_id = p_auth_user_id
    RETURNING d.id INTO v_device_id;

    IF v_device_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_totp_disabilita_device', 'E_TOTP_DEVICE_ASSENTE',
            jsonb_build_object('auth_user_id', p_auth_user_id,
                               'chi_agisce',   v_utente,
                               'motivo',       btrim(p_motivo)),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- D-T5: dal server il backend non c'e', la traccia la scrive il
    -- verbo. session_user e non user_insert: dentro una DEFINER
    -- CURRENT_USER e' il proprietario.
    IF v_dal_server THEN
        INSERT INTO dbops.sessioni_utente (auth_user_id, evento, dettaglio)
        VALUES (p_auth_user_id, 'TOTP_DISABILITATO',
                jsonb_build_object('via',       'SERVER',
                                   'sessione',  session_user,
                                   'chi_agisce', v_utente,
                                   'motivo',    btrim(p_motivo)));
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_totp_disabilita_device(p_auth_user_id integer, p_motivo text)
IS 'Disabilita il secondo fattore (TOTP) di una credenziale CANCELLANDO il device: segreto e codici spariscono (D-T3). Chi agisce: la credenziale stessa (motivo facoltativo); oppure un ALTRO, con motivo obbligatorio (E_TOTP_MOTIVO_OBBLIGATORIO): la sessione del migratore (dbops.fn_sessione_del_migratore: il caso senza via d''uscita, l''unico super admin senza telefono e codici; D-T4, lo sblocco si fa dal server, l''app non raggiunge questo ramo) o un SUPER_ADMIN (script.fn_guard_super_admin, se no E_PERMESSO_NEGATO). La traccia: dall''applicazione la scrive il backend (D-T3); DAL SERVER la scrive il verbo, nella stessa istruzione, in dbops.sessioni_utente (evento TOTP_DISABILITATO, dettaglio: via SERVER, sessione = ruolo di login, chi_agisce, motivo — D-T5, 2026-09-29). Device assente -> E_TOTP_DEVICE_ASSENTE. Chi ha l''obbligo torna al setup al prossimo accesso (middleware del backend). SECURITY DEFINER del PROPRIETARIO, search_path bloccato. Brief: brief-db-secondo-fattore-totp §3, §9.6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
