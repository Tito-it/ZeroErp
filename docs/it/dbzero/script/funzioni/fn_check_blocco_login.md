{% include-markdown "it/dbzero/script/manual/fn_check_blocco_login.md" %}
# ⚙️ Funzione `fn_check_blocco_login`

```sql
CREATE FUNCTION fn_check_blocco_login(p_auth_user_id integer, p_provenienza inet)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_blocco_login(p_auth_user_id integer, p_provenienza inet)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: prima della verifica della password, dire se questa credenziale
--   puo' provare da questa provenienza. Tre verifiche, il primo che
--   scatta vince: blocco dell'admin, freno sulla coppia, attesa crescente.
DECLARE
    v_credenziale_id    config.credenziali.id%TYPE;
    v_bloccata_at       config.credenziali.bloccata_at%TYPE;
    v_fallimenti        config.credenziali.fallimenti_consecutivi%TYPE;
    v_ultimo_fallimento config.credenziali.ultimo_fallimento_at%TYPE;
    v_bloccato_fino_a   config.credenziali_provenienze.bloccato_fino_a%TYPE;
    v_tetto             integer;
    v_attesa_base       integer;
    v_attesa_max        integer;
    v_attesa            integer;
    v_riprova_da        timestamptz;
    v_rimanenti         integer;
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 OR p_provenienza IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_blocco_login', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id,
                               'p_provenienza',  p_provenienza::text),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_check_blocco_login',
                           'credenziale e provenienza obbligatorie']);
    END IF;

    SELECT c.id, c.bloccata_at, c.fallimenti_consecutivi, c.ultimo_fallimento_at
      INTO v_credenziale_id, v_bloccata_at, v_fallimenti, v_ultimo_fallimento
      FROM config.credenziali c
     WHERE c.auth_user_id = p_auth_user_id;

    -- Nessuna riga: nessun tentativo, non bloccata.
    IF v_credenziale_id IS NULL THEN
        RETURN;
    END IF;

    -- 1. Blocco dell'admin: non scade.
    IF v_bloccata_at IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_blocco_login', 'E_CREDENZIALE_BLOCCATA',
            jsonb_build_object('auth_user_id', p_auth_user_id,
                               'bloccata_at',  v_bloccata_at),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Freno sulla coppia credenziale + provenienza.
    SELECT p.bloccato_fino_a
      INTO v_bloccato_fino_a
      FROM config.credenziali_provenienze p
     WHERE p.credenziale_id = v_credenziale_id
       AND p.provenienza    = p_provenienza;

    IF v_bloccato_fino_a IS NOT NULL THEN
        IF v_bloccato_fino_a <= now() THEN
            -- Freno scaduto: la coppia riparte da zero.
            DELETE FROM config.credenziali_provenienze p
             WHERE p.credenziale_id = v_credenziale_id
               AND p.provenienza    = p_provenienza;
        ELSE
            -- I minuti vanno nel messaggio (a chi prova) e nel contesto (al log).
            v_rimanenti := GREATEST(1,
                CEIL(EXTRACT(EPOCH FROM (v_bloccato_fino_a - now())) / 60)::integer);
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_check_blocco_login', 'E_UTENTE_BLOCCATO',
                jsonb_build_object('auth_user_id',     p_auth_user_id,
                                   'provenienza',      p_provenienza::text,
                                   'bloccato_fino_a',  v_bloccato_fino_a,
                                   'minuti_rimanenti', v_rimanenti),
                NULL::uuid,
                VARIADIC ARRAY[v_rimanenti::text]);
        END IF;
    END IF;

    -- 3. Attesa crescente sulla credenziale (da qualunque provenienza).
    IF v_fallimenti > 0 THEN
        SELECT lp.tetto_credenziale, lp.attesa_base_secondi, lp.attesa_max_secondi
          INTO v_tetto, v_attesa_base, v_attesa_max
          FROM script.fn_login_parametri() lp;

        v_attesa := script.fn_login_attesa_secondi(
            v_fallimenti, v_tetto, v_attesa_base, v_attesa_max);

        IF v_attesa > 0 THEN
            v_riprova_da := v_ultimo_fallimento + make_interval(secs => v_attesa);
            IF v_riprova_da > now() THEN
                v_rimanenti := GREATEST(1,
                    CEIL(EXTRACT(EPOCH FROM (v_riprova_da - now())))::integer);
                PERFORM script.fn_log_and_raise_error(
                    'database', 'script.fn_check_blocco_login', 'E_LOGIN_ATTESA',
                    jsonb_build_object('auth_user_id',      p_auth_user_id,
                                       'fallimenti',        v_fallimenti,
                                       'attesa_secondi',    v_attesa,
                                       'secondi_rimanenti', v_rimanenti),
                    NULL::uuid,
                    VARIADIC ARRAY[v_rimanenti::text]);
            END IF;
        END IF;
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_check_blocco_login(p_auth_user_id integer, p_provenienza inet)
IS 'Check del login, PRIMA della verifica della password, per CREDENZIALE e PROVENIENZA (M-4: nessun filtro su veste o ruolo). Nell''ordine, il primo che scatta vince: (1) blocco dell''admin -> E_CREDENZIALE_BLOCCATA, non scade; (2) freno sulla coppia credenziale + provenienza -> E_UTENTE_BLOCCATO con i minuti rimanenti nel messaggio e nel contesto, e un freno scaduto fa ripartire la coppia (riga cancellata); (3) attesa crescente sulla credenziale (fn_login_attesa_secondi) -> E_LOGIN_ATTESA con i secondi rimanenti. Nessuna riga in config.credenziali = passa. Credenziale NULL/<= 0 o provenienza NULL -> E_AUTH_CHIAMATA_NON_VALIDA. SECURITY DEFINER del PROPRIETARIO, non di un superuser, search_path bloccato; nessun guard di permesso, dichiarato (gira prima del login). Brief: brief-db-blocco-login-per-credenziale §2.4, §3.1, §12.8.';
```

---
{% include-markdown "signature-core.md" %}
