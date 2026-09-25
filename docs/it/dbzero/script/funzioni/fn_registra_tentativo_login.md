{% include-markdown "it/dbzero/script/manual/fn_registra_tentativo_login.md" %}
# ⚙️ Funzione `fn_registra_tentativo_login`

```sql
CREATE FUNCTION fn_registra_tentativo_login(p_auth_user_id integer, p_provenienza inet, p_successo boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_registra_tentativo_login(p_auth_user_id integer, p_provenienza inet, p_successo boolean)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: registrare l'esito di un tentativo di login. Successo: azzera.
--   Fallimento: conta sulla credenziale (attesa crescente) e sulla coppia
--   credenziale + provenienza (freno alla soglia).
DECLARE
    v_credenziale_id  config.credenziali.id%TYPE;
    v_fallimenti      config.credenziali.fallimenti_consecutivi%TYPE;
    v_tentativi       config.credenziali_provenienze.tentativi_falliti%TYPE;
    v_bloccato_fino_a config.credenziali_provenienze.bloccato_fino_a%TYPE;
    v_max_tentativi   integer;
    v_blocco_minuti   integer;
    v_tetto           integer;
    v_attesa_base     integer;
    v_attesa_max      integer;
    v_ttl_days        integer;
    v_bloccato        boolean;
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0
       OR p_provenienza IS NULL OR p_successo IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_registra_tentativo_login', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id', p_auth_user_id,
                               'p_provenienza',  p_provenienza::text,
                               'p_successo',     p_successo),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_registra_tentativo_login',
                           'credenziale, provenienza ed esito obbligatori']);
    END IF;

    IF p_successo THEN
        PERFORM script.fn_azzera_tentativi_credenziale(p_auth_user_id, p_provenienza);
        RETURN jsonb_build_object('bloccato', false, 'minuti_rimanenti', 0,
                                  'tentativi', 0, 'attesa_secondi', 0);
    END IF;

    -- La FK verso django.auth_user in CI non esiste: l'esistenza si
    -- controlla qui, o un id sbagliato aprirebbe una riga orfana.
    IF NOT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_registra_tentativo_login', 'E_CREDENZIALE_NON_TROVATA',
            jsonb_build_object('auth_user_id', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    SELECT lp.max_tentativi, lp.blocco_minuti, lp.tetto_credenziale,
           lp.attesa_base_secondi, lp.attesa_max_secondi
      INTO v_max_tentativi, v_blocco_minuti, v_tetto, v_attesa_base, v_attesa_max
      FROM script.fn_login_parametri() lp;

    -- 1. La credenziale: base dell'attesa crescente.
    INSERT INTO config.credenziali AS c
           (auth_user_id, fallimenti_consecutivi, ultimo_fallimento_at)
    VALUES (p_auth_user_id, 1, now())
    ON CONFLICT (auth_user_id) DO UPDATE
       SET fallimenti_consecutivi = c.fallimenti_consecutivi + 1,
           ultimo_fallimento_at   = now()
    RETURNING c.id, c.fallimenti_consecutivi
         INTO v_credenziale_id, v_fallimenti;

    -- 2. La coppia credenziale + provenienza: il freno.
    --    ⚠️ Un freno scaduto riparte da 1 (questo fallimento), non somma.
    v_ttl_days := (dbops.fn_cleanup_at_params('config', 'credenziali_provenienze')
                   ->> 'ttl_days')::integer;

    INSERT INTO config.credenziali_provenienze AS p
           (credenziale_id, provenienza, tentativi_falliti,
            bloccato_fino_a, ultimo_fallimento_at)
    VALUES (v_credenziale_id, p_provenienza, 1,
            CASE WHEN 1 >= v_max_tentativi
                 THEN now() + make_interval(mins => v_blocco_minuti) END,
            now())
    ON CONFLICT (credenziale_id, provenienza) DO UPDATE
       SET tentativi_falliti =
               CASE WHEN p.bloccato_fino_a IS NOT NULL AND p.bloccato_fino_a <= now()
                    THEN 1
                    ELSE p.tentativi_falliti + 1 END,
           bloccato_fino_a =
               CASE WHEN (CASE WHEN p.bloccato_fino_a IS NOT NULL AND p.bloccato_fino_a <= now()
                               THEN 1
                               ELSE p.tentativi_falliti + 1 END) >= v_max_tentativi
                    THEN now() + make_interval(mins => v_blocco_minuti) END,
           ultimo_fallimento_at = now(),
           cleanup_at = CASE WHEN v_ttl_days IS NOT NULL
                             THEN now() + make_interval(days => v_ttl_days) END
    RETURNING p.tentativi_falliti, p.bloccato_fino_a
         INTO v_tentativi, v_bloccato_fino_a;

    v_bloccato := v_bloccato_fino_a IS NOT NULL AND v_bloccato_fino_a > now();

    RETURN jsonb_build_object(
        'bloccato',         v_bloccato,
        'minuti_rimanenti', CASE WHEN v_bloccato THEN v_blocco_minuti ELSE 0 END,
        'tentativi',        v_tentativi,
        'attesa_secondi',   script.fn_login_attesa_secondi(
                                v_fallimenti, v_tetto, v_attesa_base, v_attesa_max));
END;
$function$

COMMENT ON FUNCTION script.fn_registra_tentativo_login(p_auth_user_id integer, p_provenienza inet, p_successo boolean)
IS 'Registra l''esito di un tentativo di login per CREDENZIALE e PROVENIENZA (M-4: ogni credenziale conta, anche senza identita'', nessun filtro su veste). Successo -> script.fn_azzera_tentativi_credenziale(uid, provenienza): la stessa regola del reset (D-2) sul perimetro dell''accesso, cioe'' i fallimenti della credenziale e la sola coppia da cui si e'' entrati (il freno sulle altre provenienze resta). Fallimento, in upsert e in ordine fisso: (1) fallimenti consecutivi della credenziale + ultimo_fallimento_at, base dell''attesa crescente; (2) tentativi della coppia credenziale + provenienza, con freno fino a now() + login_blocco_minuti alla soglia login_max_tentativi_falliti — un freno scaduto riparte da 1. cleanup_at della coppia ricalcolato dalla regola CLEANUP_AT (dbops.fn_cleanup_at_params). Ritorna jsonb {bloccato, minuti_rimanenti, tentativi (della coppia), attesa_secondi (del prossimo tentativo)}. Credenziale inesistente -> E_CREDENZIALE_NON_TROVATA; parametri mancanti -> E_AUTH_CHIAMATA_NON_VALIDA. SECURITY DEFINER del PROPRIETARIO, non di un superuser, search_path bloccato; nessun guard di permesso, dichiarato. Brief: brief-db-blocco-login-per-credenziale §2.4-2.5, §3.1.';
```

---
{% include-markdown "signature-core.md" %}
