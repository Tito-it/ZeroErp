{% include-markdown "it/dbzero/script/manual/fn_registra_tentativo_login.md" %}
# ⚙️ Funzione `fn_registra_tentativo_login`

```sql
CREATE FUNCTION fn_registra_tentativo_login(p_auth_user_id integer, p_nome_digest bytea, p_provenienza inet, p_successo boolean)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_registra_tentativo_login(p_auth_user_id integer, p_nome_digest bytea, p_provenienza inet, p_successo boolean)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: registrare l'esito di un tentativo di login. Successo: azzera.
--   Fallimento: conta sulla chiave (credenziale se c'e', nome tentato se
--   no) per l'attesa crescente, e sulla coppia chiave + provenienza per
--   il freno alla soglia.
DECLARE
    -- Esplicito: e' config.credenziali.id OPPURE config.nomi_tentati.id,
    -- secondo la chiave (entrambi bigint), non una colonna sola.
    v_chiave_id       bigint;
    v_fallimenti      config.credenziali.fallimenti_consecutivi%TYPE;
    v_tentativi       config.credenziali_provenienze.tentativi_falliti%TYPE;
    v_bloccato_fino_a config.credenziali_provenienze.bloccato_fino_a%TYPE;
    -- Espliciti: parametri da script.fn_login_parametri (testo in
    -- config.parameters), ttl della regola CLEANUP_AT (dbops.fn_cleanup_at_regola), e
    -- un flag calcolato.
    v_max_tentativi   integer;
    v_blocco_minuti   integer;
    v_tetto           integer;
    v_attesa_base     integer;
    v_attesa_max      integer;
    v_ttl_coppia      integer;
    v_ttl_nome        integer;
    v_bloccato        boolean;
BEGIN
    IF p_auth_user_id <= 0 OR p_provenienza IS NULL OR p_successo IS NULL
       OR p_nome_digest IS NULL OR octet_length(p_nome_digest) <> 32
       OR (p_successo AND p_auth_user_id IS NULL) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_registra_tentativo_login', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id',        p_auth_user_id,
                               'p_provenienza',         p_provenienza::text,
                               'p_successo',            p_successo,
                               'nome_digest_lunghezza', octet_length(p_nome_digest)),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_registra_tentativo_login',
                           'provenienza, esito e digest del nome (32 byte) obbligatori; un successo vuole la credenziale']);
    END IF;

    IF p_successo THEN
        PERFORM script.fn_azzera_tentativi_credenziale(p_auth_user_id, p_provenienza);
        RETURN jsonb_build_object('bloccato', false, 'minuti_rimanenti', 0,
                                  'tentativi', 0, 'attesa_secondi', 0);
    END IF;

    SELECT lp.max_tentativi, lp.blocco_minuti, lp.tetto_credenziale,
           lp.attesa_base_secondi, lp.attesa_max_secondi
      INTO v_max_tentativi, v_blocco_minuti, v_tetto, v_attesa_base, v_attesa_max
      FROM script.fn_login_parametri() lp;

    IF p_auth_user_id IS NOT NULL THEN
        -- La FK verso django.auth_user in CI non esiste: l'esistenza si
        -- controlla qui, o un id sbagliato aprirebbe una riga orfana.
        IF NOT EXISTS (SELECT 1 FROM django.auth_user au WHERE au.id = p_auth_user_id) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_registra_tentativo_login', 'E_CREDENZIALE_NON_TROVATA',
                jsonb_build_object('auth_user_id', p_auth_user_id),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]);
        END IF;

        -- 1. La credenziale: base dell'attesa crescente.
        INSERT INTO config.credenziali AS c
               (auth_user_id, fallimenti_consecutivi, ultimo_fallimento_at)
        VALUES (p_auth_user_id, 1, now())
        ON CONFLICT (auth_user_id) DO UPDATE
           SET fallimenti_consecutivi = c.fallimenti_consecutivi + 1,
               ultimo_fallimento_at   = now()
        RETURNING c.id, c.fallimenti_consecutivi
             INTO v_chiave_id, v_fallimenti;

        -- 2. La coppia credenziale + provenienza: il freno.
        -- La scadenza e' ultimo_fallimento_at + ttl, la base della regola:
        -- ultimo_fallimento_at si scrive now() qui sotto. Nessuna regola che
        -- si applica → NULL, la riga non scade.
        SELECT r.ttl_days INTO v_ttl_coppia
          FROM dbops.fn_cleanup_at_regola('config', 'credenziali_provenienze') r
         WHERE r.motivo_salto IS NULL;

        INSERT INTO config.credenziali_provenienze AS p
               (credenziale_id, provenienza, tentativi_falliti,
                bloccato_fino_a, ultimo_fallimento_at)
        SELECT v_chiave_id, p_provenienza, f.tentativi, f.bloccato_fino_a, now()
          FROM script.fn_login_freno_passo(0, NULL, now(),
                                           v_max_tentativi, v_blocco_minuti) f
        ON CONFLICT (credenziale_id, provenienza) DO UPDATE
           SET (tentativi_falliti, bloccato_fino_a) =
                   (SELECT f.tentativi, f.bloccato_fino_a
                      FROM script.fn_login_freno_passo(p.tentativi_falliti, p.bloccato_fino_a,
                                                       now(), v_max_tentativi,
                                                       v_blocco_minuti) f),
               ultimo_fallimento_at = now(),
               cleanup_at = CASE WHEN v_ttl_coppia IS NOT NULL
                                 THEN now() + make_interval(days => v_ttl_coppia) END
        RETURNING p.tentativi_falliti, p.bloccato_fino_a
             INTO v_tentativi, v_bloccato_fino_a;
    ELSE
        -- 1. Il nome tentato: base dell'attesa crescente. Scade.
        -- La scadenza e' ultimo_fallimento_at + ttl, la base della regola:
        -- ultimo_fallimento_at si scrive now() qui sotto. Nessuna regola che
        -- si applica → NULL, la riga non scade.
        SELECT r.ttl_days INTO v_ttl_nome
          FROM dbops.fn_cleanup_at_regola('config', 'nomi_tentati') r
         WHERE r.motivo_salto IS NULL;

        INSERT INTO config.nomi_tentati AS nt
               (nome_digest, fallimenti_consecutivi, ultimo_fallimento_at)
        VALUES (p_nome_digest, 1, now())
        ON CONFLICT (nome_digest) DO UPDATE
           SET fallimenti_consecutivi = nt.fallimenti_consecutivi + 1,
               ultimo_fallimento_at   = now(),
               cleanup_at = CASE WHEN v_ttl_nome IS NOT NULL
                                 THEN now() + make_interval(days => v_ttl_nome) END
        RETURNING nt.id, nt.fallimenti_consecutivi
             INTO v_chiave_id, v_fallimenti;

        -- 2. La coppia nome tentato + provenienza: il freno, stessa regola.
        -- La scadenza e' ultimo_fallimento_at + ttl, la base della regola:
        -- ultimo_fallimento_at si scrive now() qui sotto. Nessuna regola che
        -- si applica → NULL, la riga non scade.
        SELECT r.ttl_days INTO v_ttl_coppia
          FROM dbops.fn_cleanup_at_regola('config', 'nomi_tentati_provenienze') r
         WHERE r.motivo_salto IS NULL;

        INSERT INTO config.nomi_tentati_provenienze AS p
               (nome_tentato_id, provenienza, tentativi_falliti,
                bloccato_fino_a, ultimo_fallimento_at)
        SELECT v_chiave_id, p_provenienza, f.tentativi, f.bloccato_fino_a, now()
          FROM script.fn_login_freno_passo(0, NULL, now(),
                                           v_max_tentativi, v_blocco_minuti) f
        ON CONFLICT (nome_tentato_id, provenienza) DO UPDATE
           SET (tentativi_falliti, bloccato_fino_a) =
                   (SELECT f.tentativi, f.bloccato_fino_a
                      FROM script.fn_login_freno_passo(p.tentativi_falliti, p.bloccato_fino_a,
                                                       now(), v_max_tentativi,
                                                       v_blocco_minuti) f),
               ultimo_fallimento_at = now(),
               cleanup_at = CASE WHEN v_ttl_coppia IS NOT NULL
                                 THEN now() + make_interval(days => v_ttl_coppia) END
        RETURNING p.tentativi_falliti, p.bloccato_fino_a
             INTO v_tentativi, v_bloccato_fino_a;
    END IF;

    v_bloccato := v_bloccato_fino_a IS NOT NULL AND v_bloccato_fino_a > now();

    RETURN jsonb_build_object(
        'bloccato',         v_bloccato,
        'minuti_rimanenti', CASE WHEN v_bloccato THEN v_blocco_minuti ELSE 0 END,
        'tentativi',        v_tentativi,
        'attesa_secondi',   script.fn_login_attesa_secondi(
                                v_fallimenti, v_tetto, v_attesa_base, v_attesa_max));
END;
$function$

COMMENT ON FUNCTION script.fn_registra_tentativo_login(p_auth_user_id integer, p_nome_digest bytea, p_provenienza inet, p_successo boolean)
IS 'Registra l''esito di un tentativo di login per NOME TENTATO e PROVENIENZA. La chiave e'' la credenziale quando p_auth_user_id e'' valorizzato, ogni credenziale conta senza filtro sulla veste, il nome tentato (config.nomi_tentati, per digest) quando e'' NULL: stessa regola e stesso ritorno per le due, cosi'' la risposta non dice se il nome esiste. Successo (solo con la credenziale) -> script.fn_azzera_tentativi_credenziale(uid, provenienza). Fallimento, in upsert e in ordine fisso: (1) fallimenti consecutivi della chiave + ultimo_fallimento_at, base dell''attesa crescente; (2) la coppia chiave + provenienza col passo di script.fn_login_freno_passo (regola del 2): freno fino a now() + login_blocco_minuti alla soglia login_max_tentativi_falliti, un freno scaduto riparte da 1. cleanup_at delle righe che scadono ricalcolato a ogni fallimento come ultimo_fallimento_at + ttl_days, con la regola di dbops.fn_cleanup_at_regola (nessuna regola che si applica: NULL, non scade). Ritorna jsonb {bloccato, minuti_rimanenti, tentativi (della coppia), attesa_secondi (del prossimo tentativo)}. Credenziale data e inesistente -> E_CREDENZIALE_NON_TROVATA; provenienza, esito o digest (32 byte) mancanti, credenziale <= 0, successo senza credenziale -> E_AUTH_CHIAMATA_NON_VALIDA. SECURITY DEFINER del PROPRIETARIO, search_path bloccato; nessun guard di permesso, dichiarato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
