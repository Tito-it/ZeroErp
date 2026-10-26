{% include-markdown "it/dbzero/script/manual/fn_elimina_credenziale.md" %}
# ⚙️ Funzione `fn_elimina_credenziale`

```sql
CREATE FUNCTION fn_elimina_credenziale(p_auth_user_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_elimina_credenziale(p_auth_user_id integer)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: eliminare una credenziale che non ha mai avuto una veste
--   ne' lasciato storia, per decisione di un SUPER_ADMIN, e
--   lasciarne traccia.
DECLARE
    v_utente   config.credenziali_eliminate.eliminata_da%TYPE;
    -- Nudi: colonne di django.auth_user, niente %TYPE su django.*.
    v_username text;
    v_email    text;
    -- Nudo: l'array dei motivi di fn_check_credenziale_eliminabile.
    v_motivi   jsonb;
BEGIN
    -- Prima riga: chi agisce dev'essere SUPER_ADMIN (D-3).
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_super_admin(v_utente);

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_elimina_credenziale', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_elimina_credenziale',
                           'credenziale assente o non valida']);
    END IF;

    -- Il lock PRIMA della check: una veste che nasce adesso o e'
    -- gia' scritta, o aspetta questa transazione (vedi testata).
    SELECT au.username, au.email
      INTO v_username, v_email
      FROM django.auth_user au
     WHERE au.id = p_auth_user_id
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_elimina_credenziale', 'E_CREDENZIALE_NON_TROVATA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- La regola sta nella check: qui la si chiama, non la si riscrive
    -- (linee-guida-sql §12.5.2).
    v_motivi := script.fn_check_credenziale_eliminabile(p_auth_user_id);
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'database', 'script.fn_elimina_credenziale', v_motivi,
        p_context_extra => jsonb_build_object('auth_user_id', p_auth_user_id,
                                              'chi_agisce',   v_utente));

    -- La traccia: la riga di django.auth_user sta per sparire.
    INSERT INTO config.credenziali_eliminate
           (auth_user_id, username, email, eliminata_da)
    VALUES (p_auth_user_id, v_username, v_email, v_utente);

    BEGIN
        DELETE FROM django.auth_user au WHERE au.id = p_auth_user_id;
    EXCEPTION WHEN foreign_key_violation THEN
        -- La rete: la regola si rilegge, non si indovina.
        v_motivi := script.fn_check_credenziale_eliminabile(p_auth_user_id);
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', 'script.fn_elimina_credenziale', v_motivi,
            p_context_extra => jsonb_build_object('auth_user_id', p_auth_user_id,
                                                  'chi_agisce',   v_utente,
                                                  'rete',         true));
        -- Nessun motivo lo spiega: e' un difetto della check, e
        -- l'errore originale e' la diagnosi giusta.
        RAISE;
    END;
END;
$function$

COMMENT ON FUNCTION script.fn_elimina_credenziale(p_auth_user_id integer)
IS 'Elimina una CREDENZIALE (django.auth_user) che non ha nessuna veste ne'' storia: il gesto che il presidio dbops.vw_credenziali_da_sanare (NESSUNA_VESTE) chiede all''amministratore. Prima riga script.fn_guard_super_admin(app.current_user_id) (D-3). Id NULL o <= 0 -> E_AUTH_CHIAMATA_NON_VALIDA; credenziale inesistente -> E_CREDENZIALE_NON_TROVATA. Blocca la riga di django.auth_user (FOR UPDATE) PRIMA di leggere la check: una veste concorrente o e'' gia'' scritta o aspetta e muore sulla FK. Poi solleva il primo motivo di script.fn_check_credenziale_eliminabile, la stessa regola che spegne il pulsante (§12.5.2): CON_VESTI, STORIA_NON_VERIFICABILE (senza il ponte django, fail-closed), CON_STORIA. Scrive la traccia in config.credenziali_eliminate (id, username, email, chi, quando), poi il DELETE: le tabelle CASCADE (config.credenziali, preferenze, TOTP, token, override) seguono. Un 23503 dal DELETE si rilegge dalla check e ne solleva il primo motivo; se la check non lo spiega si rilancia l''originale. Le FK differite di Django si verificano al commit. SECURITY DEFINER del PROPRIETARIO, search_path bloccato: all''app niente DELETE diretto su django.auth_user. Brief: brief-db-elimina-credenziale-senza-veste §4.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
